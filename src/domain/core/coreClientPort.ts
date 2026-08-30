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

export async function invokeCoreAction(input: CoreClientInvokeInput): Promise<CoreClientInvokeResult> {
  const port_uid = CORE_ACTION_PORT[input.action_uid];
  if (!port_uid) {
    return { ok: false, error_uid: "CORE-01-ERR-UNDEFINED-001", reason_code: "ACTION_HAS_NO_SERVER_PORT", correlation_id: "unresolved" };
  }
  const contract = CORE_PORT_METHOD_PATH[port_uid];
  const path = resolvePath(contract.path, input.path_params ?? {});
  if (!path) {
    return { ok: false, error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "REQUIRED_PATH_REFERENCE_MISSING", correlation_id: "unresolved" };
  }
  const query = new URLSearchParams(input.query ?? {}).toString();
  const url = query ? `${path}?${query}` : path;
  try {
    const response = await fetch(url, {
      method: contract.method,
      cache: "no-store",
      signal: input.signal,
      headers: contract.method === "POST" ? { "content-type": "application/json" } : undefined,
      body: contract.method === "POST" ? JSON.stringify(input.payload ?? null) : undefined,
    });
    const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
    const value: unknown = await response.json().catch(() => null);
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
