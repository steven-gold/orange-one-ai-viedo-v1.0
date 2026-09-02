import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import {
  isDevGateUid,
  isDevPageState,
  isDevRuntimeState,
  type DevGateUid,
  type DevPageState,
  type DevRuntimeState,
} from "./devRuntimeContract";

export type DevProjectionTestMetadata = {
  data_classification: "TEST_ONLY";
  synthetic: true;
  test_dataset_id: string;
  test_run_id: string;
  created_for_validation: true;
  production_eligible: false;
};

export type DevNormalizedProjection = {
  page_state: DevPageState;
  authorized_scope: string | null;
  run_status: DevRuntimeState | null;
  values: Readonly<Record<string, string>>;
  gate_state: Readonly<Partial<Record<DevGateUid, boolean>>>;
  test_metadata?: DevProjectionTestMetadata;
};

export type DevProjectionResolver = {
  resolve: (raw: unknown) => DevNormalizedProjection | Promise<DevNormalizedProjection>;
};

export type DevProjectionResult =
  | { ok: true; projection: DevNormalizedProjection; correlation_id: string }
  | { ok: false; error_uid: "DEV-01-ERR-AUTH" | "DEV-01-ERR-UNDEFINED"; reason_code: string; correlation_id: string };

let resolver: DevProjectionResolver | null = null;

export function configureDevProjectionResolver(next: DevProjectionResolver) {
  resolver = next;
}

export function isDevProjectionResolverBound() {
  return resolver !== null;
}

function isAuthorizationFailure(status: number, reasonCode: string) {
  return status === 401 || status === 403 || /AUTH|PERMISSION|SCOPE|DENIED/.test(reasonCode);
}

function validateProjection(candidate: DevNormalizedProjection): DevNormalizedProjection {
  if (!isDevPageState(candidate.page_state)) throw new Error("DEV_PROJECTION_PAGE_STATE_UNREGISTERED");
  if (candidate.run_status !== null && !isDevRuntimeState(candidate.run_status)) throw new Error("DEV_PROJECTION_RUN_STATUS_UNREGISTERED");
  if (candidate.authorized_scope !== null && typeof candidate.authorized_scope !== "string") throw new Error("DEV_PROJECTION_SCOPE_INVALID");
  if (!candidate.values || typeof candidate.values !== "object" || Array.isArray(candidate.values)) throw new Error("DEV_PROJECTION_VALUES_INVALID");
  for (const [key, value] of Object.entries(candidate.values)) if (typeof key !== "string" || typeof value !== "string") throw new Error("DEV_PROJECTION_VALUE_INVALID");
  if (!candidate.gate_state || typeof candidate.gate_state !== "object" || Array.isArray(candidate.gate_state)) throw new Error("DEV_PROJECTION_GATES_INVALID");
  for (const [gateUid, value] of Object.entries(candidate.gate_state)) if (!isDevGateUid(gateUid) || typeof value !== "boolean") throw new Error("DEV_PROJECTION_GATE_UNREGISTERED");
  if (candidate.test_metadata !== undefined) {
    const metadata = candidate.test_metadata;
    if (!isControlledTestMode() || metadata.data_classification !== "TEST_ONLY" || metadata.synthetic !== true || metadata.created_for_validation !== true || metadata.production_eligible !== false || !metadata.test_dataset_id || !metadata.test_run_id) {
      throw new Error("DEV_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION");
    }
  }
  return candidate;
}

export async function readDevProjection(signal?: AbortSignal): Promise<DevProjectionResult> {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/admin%3ADEV-01", { method: "GET", cache: "no-store", signal });
  } catch {
    return { ok: false, error_uid: "DEV-01-ERR-UNDEFINED", reason_code: "DEV_PROJECTION_REQUEST_FAILED", correlation_id: "unresolved" };
  }

  const headerCorrelationId = response.headers.get("x-correlation-id") ?? "unresolved";
  const raw: unknown = await response.json().catch(() => null);
  const body = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : null;
  const correlation_id = typeof body?.correlation_id === "string" ? body.correlation_id : headerCorrelationId;

  if (!response.ok) {
    const reason_code = typeof body?.reason_code === "string" ? body.reason_code : "DEV_PROJECTION_READ_FAILED";
    return { ok: false, error_uid: isAuthorizationFailure(response.status, reason_code) ? "DEV-01-ERR-AUTH" : "DEV-01-ERR-UNDEFINED", reason_code, correlation_id };
  }

  if (!resolver) return { ok: false, error_uid: "DEV-01-ERR-UNDEFINED", reason_code: "DEV_PROJECTION_ADAPTER_NOT_BOUND", correlation_id };

  try {
    return { ok: true, projection: validateProjection(await resolver.resolve(raw)), correlation_id };
  } catch (error) {
    const reason_code = error instanceof Error && error.message === "DEV_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION" ? error.message : "DEV_PROJECTION_ADAPTER_REJECTED";
    return { ok: false, error_uid: "DEV-01-ERR-UNDEFINED", reason_code, correlation_id };
  }
}
