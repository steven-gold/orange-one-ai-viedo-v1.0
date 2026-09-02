import { isControlledTestMode } from "@/domain/testing/controlledTestData";

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

export type AiApiProjectionTestMetadata = {
  data_classification: "TEST_ONLY";
  synthetic: true;
  test_dataset_id: string;
  test_run_id: string;
  created_for_validation: true;
  production_eligible: false;
};

export type AiApiProviderRow = {
  provider_id: string;
  provider_name: string;
  model_id: string;
  model_name: string;
  capability: string;
  adapter: string;
  base_url: string;
  endpoint: string;
  timeout: string;
  enabled: string;
  credential_status: string;
  last_test: string;
};

export type AiApiProjection = {
  page_state: AiApiPageState | null;
  values: Readonly<Record<string, string>>;
  control_enabled: Readonly<Record<string, boolean>>;
  provider_rows: readonly AiApiProviderRow[];
  selected_resource_id: string | null;
  test_metadata?: AiApiProjectionTestMetadata;
};

export type AiApiProjectionResolver = {
  resolve: (raw: unknown) => AiApiProjection | Promise<AiApiProjection>;
};

const ALLOWED_PAGE_STATES = new Set<AiApiPageState>([
  "LOADING","READY","EMPTY","ERROR","POLICY_BLOCKED","VERSION_CONFLICT","EXTERNAL_PENDING","READ_ONLY","ARCHIVED",
]);

let resolver: AiApiProjectionResolver | null = null;
export function configureAiApiProjectionResolver(next: AiApiProjectionResolver) { resolver = next; }

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function normalizeTestMetadata(value: unknown): AiApiProjectionTestMetadata | undefined {
  const metadata = asRecord(value);
  if (!metadata) return undefined;
  if (!isControlledTestMode()) throw new Error("AIAPI01_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION");
  if (
    metadata.data_classification !== "TEST_ONLY" || metadata.synthetic !== true ||
    metadata.created_for_validation !== true || metadata.production_eligible !== false ||
    typeof metadata.test_dataset_id !== "string" || typeof metadata.test_run_id !== "string"
  ) throw new Error("AIAPI01_TEST_PROJECTION_METADATA_INVALID");
  return metadata as unknown as AiApiProjectionTestMetadata;
}

function normalizeProviderRows(value: unknown): AiApiProviderRow[] {
  if (!Array.isArray(value)) return [];
  const rows: AiApiProviderRow[] = [];
  const keys: (keyof AiApiProviderRow)[] = ["provider_id","provider_name","model_id","model_name","capability","adapter","base_url","endpoint","timeout","enabled","credential_status","last_test"];
  for (const raw of value) {
    const row = asRecord(raw); if (!row) continue;
    const normalized = {} as AiApiProviderRow;
    let valid = true;
    for (const key of keys) { const field = row[key]; if (typeof field !== "string") { valid = false; break; } normalized[key] = field; }
    if (valid) rows.push(normalized);
  }
  return rows;
}

function normalize(raw: unknown): AiApiProjection {
  const record = asRecord(raw);
  if (!record) throw new Error("AIAPI01_PROJECTION_NOT_OBJECT");
  const valuesRaw = asRecord(record.values) ?? {};
  const controlRaw = asRecord(record.control_enabled) ?? asRecord(record.action_enabled) ?? {};
  const values: Record<string, string> = {};
  const control_enabled: Record<string, boolean> = {};
  for (const [key, value] of Object.entries(valuesRaw)) if (typeof value === "string") values[key] = value;
  for (const [key, value] of Object.entries(controlRaw)) if (typeof value === "boolean") control_enabled[key] = value;
  let page_state: AiApiPageState | null = null;
  if (record.page_state !== null && record.page_state !== undefined) {
    if (typeof record.page_state !== "string" || !ALLOWED_PAGE_STATES.has(record.page_state as AiApiPageState)) throw new Error("AIAPI01_PROJECTION_STATE_UNREGISTERED");
    page_state = record.page_state as AiApiPageState;
  }
  return {
    page_state,
    values,
    control_enabled,
    provider_rows: normalizeProviderRows(record.provider_rows),
    selected_resource_id: typeof record.selected_resource_id === "string" ? record.selected_resource_id : null,
    ...(record.test_metadata ? { test_metadata: normalizeTestMetadata(record.test_metadata) } : {}),
  };
}

export async function readAiApiProjection(signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/admin%3AAIAPI-01", { method: "GET", cache: "no-store", signal });
  } catch {
    return { ok: false as const, reason_code: "AIAPI01_PROJECTION_REQUEST_FAILED", correlation_id: "unresolved" };
  }
  const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
  const raw: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const body = asRecord(raw);
    return {
      ok: false as const,
      reason_code: typeof body?.reason_code === "string" ? body.reason_code : "AIAPI01_PROJECTION_READ_FAILED",
      correlation_id: typeof body?.correlation_id === "string" ? body.correlation_id : correlation_id,
    };
  }
  try {
    return { ok: true as const, projection: resolver ? await resolver.resolve(raw) : normalize(raw), correlation_id };
  } catch {
    return { ok: false as const, reason_code: "AIAPI01_PROJECTION_ADAPTER_REJECTED", correlation_id };
  }
}
