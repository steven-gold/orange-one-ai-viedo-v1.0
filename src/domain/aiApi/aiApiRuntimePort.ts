export type AiApiPageState =
  | "LOADING"
  | "READY"
  | "EMPTY"
  | "ERROR"
  | "POLICY_BLOCKED"
  | "VERSION_CONFLICT"
  | "EXTERNAL_PENDING"
  | "READ_ONLY"
  | "ARCHIVED";

export type AiApiProjection = {
  page_state: AiApiPageState | null;
  values: Readonly<Record<string, string>>;
  control_enabled: Readonly<Record<string, boolean>>;
};

export type AiApiProjectionResolver = {
  resolve: (raw: unknown) => AiApiProjection | Promise<AiApiProjection>;
};

const ALLOWED_PAGE_STATES = new Set<AiApiPageState>([
  "LOADING",
  "READY",
  "EMPTY",
  "ERROR",
  "POLICY_BLOCKED",
  "VERSION_CONFLICT",
  "EXTERNAL_PENDING",
  "READ_ONLY",
  "ARCHIVED",
]);

let resolver: AiApiProjectionResolver | null = null;

export function configureAiApiProjectionResolver(next: AiApiProjectionResolver) {
  resolver = next;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function normalize(raw: unknown): AiApiProjection {
  const record = asRecord(raw);
  if (!record) throw new Error("AIAPI01_PROJECTION_NOT_OBJECT");

  const valuesRaw = asRecord(record.values) ?? {};
  const controlRaw = asRecord(record.control_enabled) ?? {};
  const values: Record<string, string> = {};
  const control_enabled: Record<string, boolean> = {};

  for (const [key, value] of Object.entries(valuesRaw)) {
    if (typeof value === "string") values[key] = value;
  }
  for (const [key, value] of Object.entries(controlRaw)) {
    if (typeof value === "boolean") control_enabled[key] = value;
  }

  let page_state: AiApiPageState | null = null;
  if (record.page_state !== null && record.page_state !== undefined) {
    if (typeof record.page_state !== "string" || !ALLOWED_PAGE_STATES.has(record.page_state as AiApiPageState)) {
      throw new Error("AIAPI01_PROJECTION_STATE_UNREGISTERED");
    }
    page_state = record.page_state as AiApiPageState;
  }

  return { page_state, values, control_enabled };
}

export async function readAiApiProjection(signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/admin%3AAIAPI-01", {
      method: "GET",
      cache: "no-store",
      signal,
    });
  } catch {
    return {
      ok: false as const,
      reason_code: "AIAPI01_PROJECTION_REQUEST_FAILED",
      correlation_id: "unresolved",
    };
  }

  const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
  const raw: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const body = asRecord(raw);
    return {
      ok: false as const,
      reason_code:
        typeof body?.reason_code === "string"
          ? body.reason_code
          : "AIAPI01_PROJECTION_READ_FAILED",
      correlation_id:
        typeof body?.correlation_id === "string"
          ? body.correlation_id
          : correlation_id,
    };
  }

  try {
    return {
      ok: true as const,
      projection: resolver ? await resolver.resolve(raw) : normalize(raw),
      correlation_id,
    };
  } catch {
    return {
      ok: false as const,
      reason_code: "AIAPI01_PROJECTION_ADAPTER_REJECTED",
      correlation_id,
    };
  }
}
