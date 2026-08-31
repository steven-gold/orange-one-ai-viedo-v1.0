import { CORE_ACTION_PORT, CORE_PORT_METHOD_PATH, type CoreActionUid, type CoreRuntimeErrorUid } from "./coreRuntimeContract";

export type CoreClientInvokeInput = {
  action_uid: CoreActionUid;
  path_params?: Record<string, string>;
  query?: Record<string, string>;
  payload?: unknown;
  signal?: AbortSignal;
};

export type CoreClientInvokeResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; error_uid: CoreRuntimeErrorUid; reason_code: string; correlation_id: string };

function resolvePath(template: string, params: Record<string, string>): string | null {
  let path = template;
  for (const token of template.match(/\{[^}]+\}/g) ?? []) {
    const key = token.slice(1, -1);
    const value = params[key];
    if (!value) return null;
    path = path.replace(token, encodeURIComponent(value));
  }
  return path;
}

function hasRegisteredPayload(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) && Object.keys(value).length > 0;
}

async function readJson(response: Response): Promise<unknown> {
  return response.json().catch(() => null);
}

export async function readCoreProjection(signal?: AbortSignal): Promise<CoreClientInvokeResult> {
  try {
    const response = await fetch("/v1/ui-projections/CORE-01", { method: "GET", cache: "no-store", signal });
    const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
    const value = await readJson(response);
    if (!response.ok) {
      const error = value as Partial<{ error_uid: CoreRuntimeErrorUid; reason_code: string; correlation_id: string }> | null;
      return {
        ok: false,
        error_uid: error?.error_uid ?? (response.status === 403 ? "CORE-01-ERR-PERM-001" : "CORE-01-ERR-CONTEXT-001"),
        reason_code: error?.reason_code ?? "CORE_PROJECTION_REQUEST_FAILED",
        correlation_id: error?.correlation_id ?? correlation_id,
      };
    }
    return { ok: true, value, correlation_id };
  } catch {
    return { ok: false, error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "CORE_PROJECTION_REQUEST_FAILED", correlation_id: "unresolved" };
  }
}

export async function invokeCoreAction(input: CoreClientInvokeInput): Promise<CoreClientInvokeResult> {
  const port_uid = CORE_ACTION_PORT[input.action_uid];
  if (!port_uid) {
    return { ok: false, error_uid: "CORE-01-ERR-UNDEFINED-001", reason_code: "ACTION_HAS_NO_SERVER_PORT", correlation_id: "unresolved" };
  }

  const payloadRequiredReason: Partial<Record<CoreActionUid, { error_uid: CoreRuntimeErrorUid; reason_code: string }>> = {
    "CORE-01-ACT-PROJECT-CREATE": { error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "PROJECT_DRAFT_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-TOPIC-CREATE": { error_uid: "CORE-01-ERR-TOPIC-LINEAGE-001", reason_code: "TOPIC_DRAFT_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-THREAD-CREATE": { error_uid: "CORE-01-ERR-THREAD-001", reason_code: "CONVERSATION_THREAD_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-MSG-BRANCH": { error_uid: "CORE-01-ERR-THREAD-001", reason_code: "CONVERSATION_BRANCH_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-SEND": { error_uid: "CORE-01-ERR-CONVERSATION-001", reason_code: "CONVERSATION_MESSAGE_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-MSG-ANALYZE": { error_uid: "CORE-01-ERR-CONVERSATION-001", reason_code: "CONVERSATION_ANALYZE_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-CANDIDATE-CREATE": { error_uid: "CORE-01-ERR-CANDIDATE-001", reason_code: "CANDIDATE_CREATE_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-CANDIDATE-ACCEPT": { error_uid: "CORE-01-ERR-DECISION-001", reason_code: "CANDIDATE_DECISION_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-CANDIDATE-RETURN": { error_uid: "CORE-01-ERR-DECISION-001", reason_code: "CANDIDATE_DECISION_REGISTERED_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-DNA-LOCK-REQUEST": { error_uid: "CORE-01-ERR-DNA-LOCK-001", reason_code: "DNA_LOCK_REGISTERED_COMMAND_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-CORE-REVIEW-SUBMIT": { error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "CORE_REVIEW_REGISTERED_COMMAND_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-MOTHER-LOCK-REQUEST": { error_uid: "CORE-01-ERR-LOCK-CONTRACT-001", reason_code: "MOTHER_LOCK_REGISTERED_COMMAND_SCHEMA_PAYLOAD_REQUIRED" },
    "CORE-01-ACT-CHILD-LOCK-REQUEST": { error_uid: "CORE-01-ERR-LOCK-CONTRACT-001", reason_code: "CHILD_LOCK_REGISTERED_COMMAND_SCHEMA_PAYLOAD_REQUIRED" },
  };
  const required = payloadRequiredReason[input.action_uid];
  if (required && !hasRegisteredPayload(input.payload)) {
    return { ok: false, ...required, correlation_id: "unresolved" };
  }

  const contract = CORE_PORT_METHOD_PATH[port_uid];
  const path = resolvePath(contract.path, input.path_params ?? {});
  if (!path) {
    return { ok: false, error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "REQUIRED_PATH_REFERENCE_MISSING", correlation_id: "unresolved" };
  }
  const query = new URLSearchParams(input.query ?? {}).toString();
  const url = query ? `${path}?${query}` : path;
  try {
    const headers: Record<string, string> = { "x-core-action-uid": input.action_uid };
    if (contract.method === "POST") headers["content-type"] = "application/json";
    const response = await fetch(url, {
      method: contract.method,
      cache: "no-store",
      signal: input.signal,
      headers,
      body: contract.method === "POST" ? JSON.stringify(input.payload ?? null) : undefined,
    });
    const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
    const value = await readJson(response);
    if (!response.ok) {
      const error = value as Partial<{ error_uid: CoreRuntimeErrorUid; reason_code: string; correlation_id: string }> | null;
      return {
        ok: false,
        error_uid: error?.error_uid ?? "CORE-01-ERR-CONTEXT-001",
        reason_code: error?.reason_code ?? "CORE_PORT_REQUEST_FAILED",
        correlation_id: error?.correlation_id ?? correlation_id,
      };
    }
    return { ok: true, value, correlation_id };
  } catch {
    return { ok: false, error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "CORE_PORT_REQUEST_FAILED", correlation_id: "unresolved" };
  }
}
