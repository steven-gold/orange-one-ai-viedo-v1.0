import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { configureDevCommandAdapter, type DevCommandResult } from "./devCommandPort";
import { DEV_CONTROL_BINDINGS } from "./devControlBindings";
import {
  configureDevProjectionResolver,
  readDevProjection,
  type DevNormalizedProjection,
} from "./devProjectionPort";

const PRODUCTION_BOUND_ACTIONS = new Set([
  "DEV-01-ACT-DISCOVERY-START",
  "DEV-01-ACT-DISCOVERY-PAUSE",
  "DEV-01-ACT-DISCOVERY-RESUME",
  "DEV-01-ACT-DISCOVERY-STOP",
]);

let configured = false;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function normalizeProductionProjection(raw: unknown): DevNormalizedProjection {
  const root = asRecord(raw);
  if (!root) throw new Error("DEV_PRODUCTION_PROJECTION_INVALID");
  const candidate = asRecord(root.value) ?? root;
  if (candidate.test_metadata !== undefined) {
    throw new Error("DEV_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION");
  }
  return candidate as unknown as DevNormalizedProjection;
}

function newCorrelationId() {
  try {
    return crypto.randomUUID();
  } catch {
    return `dev-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
}

function clientErrorUid(status: number) {
  return status === 401 || status === 403 ? "DEV-01-ERR-AUTH" as const : "DEV-01-ERR-UNDEFINED" as const;
}

function currentDiscoveryJobRef(projection: DevNormalizedProjection): string | null {
  const value = projection.values["DEV-01-FLD-JOB-REF"]?.trim();
  return value && value !== "—" ? value : null;
}

async function callDevCommand(
  url: string,
  method: "POST",
  body: unknown,
  correlationId: string,
): Promise<{ ok: true; correlation_id: string } | { ok: false; status: number; reason_code: string; correlation_id: string }> {
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      credentials: "include",
      cache: "no-store",
      headers: {
        "content-type": "application/json",
        "x-correlation-id": correlationId,
      },
      body: JSON.stringify(body),
    });
  } catch {
    return {
      ok: false,
      status: 503,
      reason_code: "DEV_COMMAND_REQUEST_FAILED",
      correlation_id: correlationId,
    };
  }

  const raw: unknown = await response.json().catch(() => null);
  const record = asRecord(raw);
  const serverCorrelation =
    (typeof record?.correlation_id === "string" && record.correlation_id.trim())
      ? record.correlation_id
      : response.headers.get("x-correlation-id") ?? correlationId;

  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      reason_code:
        typeof record?.reason_code === "string"
          ? record.reason_code
          : "DEV_COMMAND_REJECTED",
      correlation_id: serverCorrelation,
    };
  }
  return { ok: true, correlation_id: serverCorrelation };
}

async function invokeProductionCommand(
  actionUid: string,
  projection: DevNormalizedProjection | null,
): Promise<DevCommandResult> {
  if (!projection) {
    return {
      ok: false,
      error_uid: "DEV-01-ERR-UNDEFINED",
      reason_code: "DEV_COMMAND_PROJECTION_NOT_READY",
      correlation_id: "unresolved",
    };
  }
  if (!PRODUCTION_BOUND_ACTIONS.has(actionUid)) {
    return {
      ok: false,
      error_uid: "DEV-01-ERR-UNDEFINED",
      reason_code: "DEV_COMMAND_RUNTIME_NOT_BOUND",
      correlation_id: "unresolved",
    };
  }

  const correlationId = newCorrelationId();
  let url: string;
  switch (actionUid) {
    case "DEV-01-ACT-DISCOVERY-START":
      url = "/v1/outreach/discovery-jobs";
      break;
    case "DEV-01-ACT-DISCOVERY-PAUSE":
    case "DEV-01-ACT-DISCOVERY-RESUME":
    case "DEV-01-ACT-DISCOVERY-STOP": {
      const jobRef = currentDiscoveryJobRef(projection);
      if (!jobRef) {
        return {
          ok: false,
          error_uid: "DEV-01-ERR-UNDEFINED",
          reason_code: "DEV_DISCOVERY_JOB_ID_REQUIRED",
          correlation_id: correlationId,
        };
      }
      const suffix = actionUid === "DEV-01-ACT-DISCOVERY-PAUSE"
        ? "pause"
        : actionUid === "DEV-01-ACT-DISCOVERY-RESUME"
          ? "resume"
          : "stop";
      url = `/v1/outreach/discovery-jobs/${encodeURIComponent(jobRef)}/${suffix}`;
      break;
    }
    default:
      return {
        ok: false,
        error_uid: "DEV-01-ERR-UNDEFINED",
        reason_code: "DEV_COMMAND_RUNTIME_NOT_BOUND",
        correlation_id: correlationId,
      };
  }

  const result = await callDevCommand(url, "POST", {}, correlationId);
  if (!result.ok) {
    return {
      ok: false,
      error_uid: clientErrorUid(result.status),
      reason_code: result.reason_code,
      correlation_id: result.correlation_id,
    };
  }

  const refreshed = await readDevProjection();
  if (!refreshed.ok) {
    return {
      ok: false,
      error_uid: refreshed.error_uid,
      reason_code: `DEV_PROJECTION_REFRESH_AFTER_COMMAND_FAILED:${refreshed.reason_code}`,
      correlation_id: result.correlation_id,
    };
  }
  return {
    ok: true,
    projection: refreshed.projection,
    correlation_id: result.correlation_id,
  };
}

export function isDevClientActionBound(actionUid: string) {
  return isControlledTestMode() || PRODUCTION_BOUND_ACTIONS.has(actionUid);
}

export function isDevEffectfulCoverageComplete() {
  if (isControlledTestMode()) return true;
  const effectful = Object.values(DEV_CONTROL_BINDINGS).filter(
    (binding) => binding.effect_type !== "UI_CONTEXT_STATE",
  );
  return effectful.every((binding) => PRODUCTION_BOUND_ACTIONS.has(binding.action_uid));
}

export function ensureProductionDevClientRuntime() {
  if (configured || isControlledTestMode()) return;
  configureDevProjectionResolver({ resolve: normalizeProductionProjection });
  configureDevCommandAdapter({
    invoke: async ({ action_uid, projection }) => invokeProductionCommand(action_uid, projection),
  });
  configured = true;
}
