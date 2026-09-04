import { isControlledTestMode } from "@/domain/testing/controlledTestData";

export type QaCriteriaPageState =
  | "LOADING"
  | "READY"
  | "EMPTY"
  | "ERROR"
  | "POLICY_BLOCKED"
  | "VERSION_CONFLICT"
  | "REVIEW_REQUIRED"
  | "EXTERNAL_PENDING"
  | "READ_ONLY"
  | "ARCHIVED";

export type QaCriteriaProjectionTestMetadata = {
  data_classification: "TEST_ONLY";
  synthetic: true;
  test_dataset_id: string;
  test_run_id: string;
  created_for_validation: true;
  production_eligible: false;
};

export type QaCriteriaProjection = {
  page_state: QaCriteriaPageState | null;
  values: Readonly<Record<string, unknown>>;
  control_enabled: Readonly<Record<string, boolean>>;
  test_metadata?: QaCriteriaProjectionTestMetadata;
};

export type QaCriteriaProjectionResolver = {
  resolve: (raw: unknown) => QaCriteriaProjection | Promise<QaCriteriaProjection>;
};

const ALLOWED_PAGE_STATES = new Set<QaCriteriaPageState>([
  "LOADING",
  "READY",
  "EMPTY",
  "ERROR",
  "POLICY_BLOCKED",
  "VERSION_CONFLICT",
  "REVIEW_REQUIRED",
  "EXTERNAL_PENDING",
  "READ_ONLY",
  "ARCHIVED",
]);

let resolver: QaCriteriaProjectionResolver | null = null;

export function configureQaCriteriaProjectionResolver(next: QaCriteriaProjectionResolver) {
  resolver = next;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function normalizeMetadata(value: unknown): QaCriteriaProjectionTestMetadata | undefined {
  const metadata = asRecord(value);
  if (!metadata) return undefined;
  if (!isControlledTestMode()) {
    throw new Error("SG02_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION");
  }
  if (
    metadata.data_classification !== "TEST_ONLY" ||
    metadata.synthetic !== true ||
    metadata.created_for_validation !== true ||
    metadata.production_eligible !== false ||
    typeof metadata.test_dataset_id !== "string" ||
    typeof metadata.test_run_id !== "string"
  ) {
    throw new Error("SG02_TEST_PROJECTION_METADATA_INVALID");
  }
  return metadata as unknown as QaCriteriaProjectionTestMetadata;
}

function normalize(raw: unknown): QaCriteriaProjection {
  const record = asRecord(raw);
  if (!record) throw new Error("SG02_PROJECTION_NOT_OBJECT");

  const valuesRaw = asRecord(record.values) ?? {};
  const controlRaw = asRecord(record.control_enabled) ?? {};
  const values: Record<string, unknown> = {};
  const control_enabled: Record<string, boolean> = {};

  for (const [key, value] of Object.entries(valuesRaw)) {
    values[key] = value;
  }
  for (const [key, value] of Object.entries(controlRaw)) {
    if (typeof value === "boolean") control_enabled[key] = value;
  }

  let page_state: QaCriteriaPageState | null = null;
  if (record.page_state !== null && record.page_state !== undefined) {
    if (
      typeof record.page_state !== "string" ||
      !ALLOWED_PAGE_STATES.has(record.page_state as QaCriteriaPageState)
    ) {
      throw new Error("SG02_PROJECTION_STATE_UNREGISTERED");
    }
    page_state = record.page_state as QaCriteriaPageState;
  }

  return {
    page_state,
    values,
    control_enabled,
    ...(record.test_metadata
      ? { test_metadata: normalizeMetadata(record.test_metadata) }
      : {}),
  };
}

export async function readQaCriteriaProjection(signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/admin%3ASG-02", {
      method: "GET",
      cache: "no-store",
      signal,
    });
  } catch {
    return {
      ok: false as const,
      reason_code: "SG02_PROJECTION_REQUEST_FAILED",
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
          : "SG02_PROJECTION_READ_FAILED",
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
      reason_code: "SG02_PROJECTION_ADAPTER_REJECTED",
      correlation_id,
    };
  }
}

export type ConfigureGovernedResourceRequest = {
  resource_type: string;
  resource_id: string;
  config_patch_json: unknown;
  reason: string;
};

export type ApproveGovernedResourceRequest = {
  resource_type: string;
  resource_id: string;
  rationale: string;
  expected_resource_version?: string;
};

export async function configureQaCriteriaResource(
  payload: ConfigureGovernedResourceRequest,
) {
  const id = encodeURIComponent(payload.resource_id);
  return command(`/v1/governance/resources/${id}`, "PATCH", payload);
}

export async function approveQaCriteriaResource(
  payload: ApproveGovernedResourceRequest,
) {
  const id = encodeURIComponent(payload.resource_id);
  return command(`/v1/governance/resources/${id}/approve`, "POST", payload);
}

async function command(
  path: string,
  method: "PATCH" | "POST",
  payload: unknown,
) {
  const correlation_id = crypto.randomUUID();
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: {
        "content-type": "application/json",
        "x-correlation-id": correlation_id,
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
  } catch {
    return {
      ok: false as const,
      reason_code: "SG02_COMMAND_REQUEST_FAILED",
      correlation_id,
    };
  }

  const raw: unknown = await response.json().catch(() => null);
  const body = asRecord(raw);
  return response.ok
    ? {
        ok: true as const,
        value: raw,
        correlation_id:
          typeof body?.correlation_id === "string"
            ? body.correlation_id
            : correlation_id,
      }
    : {
        ok: false as const,
        reason_code:
          typeof body?.reason_code === "string"
            ? body.reason_code
            : "SG02_COMMAND_FAILED",
        correlation_id:
          typeof body?.correlation_id === "string"
            ? body.correlation_id
            : correlation_id,
      };
}
