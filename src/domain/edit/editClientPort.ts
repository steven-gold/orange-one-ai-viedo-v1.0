import { EDIT_PORT_METHOD_PATH, type EditIntegrationPortUid } from "./editRuntimeContract";

export type EditPortInvokeInput = {
  port_uid: EditIntegrationPortUid;
  path_params?: Record<string, string>;
  payload?: unknown;
  signal?: AbortSignal;
};

export type EditPortInvokeResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; error_uid: string; reason_code: string; correlation_id: string };

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

function defaultError(portUid: EditIntegrationPortUid): string {
  if (portUid === "EDIT-01-PORT-VOICE-QA-HANDOFF") return "EDIT-01-ERR-STAGE-001";
  if (portUid === "EDIT-01-PORT-AUDIO-MIX-COMPLETE") return "EDIT-01-ERR-MIX-001";
  if (portUid === "EDIT-01-PORT-LIPSYNC-COMPLETE") return "EDIT-01-ERR-LIPSYNC-001";
  if (portUid === "EDIT-01-PORT-SUBTITLE-COMPLETE") return "EDIT-01-ERR-SUB-001";
  if (portUid === "EDIT-01-PORT-ASSEMBLY-SCORECARD" || portUid === "EDIT-01-PORT-VOICE-SCORECARD") return "EDIT-01-ERR-EVALUATION-001";
  return "EDIT-01-ERR-CONTEXT-001";
}

export async function invokeEditIntegrationPort(input: EditPortInvokeInput): Promise<EditPortInvokeResult> {
  const contract = EDIT_PORT_METHOD_PATH[input.port_uid];
  const path = resolvePath(contract.path, input.path_params ?? {});
  if (!path) {
    return {
      ok: false,
      error_uid: defaultError(input.port_uid),
      reason_code: "REQUIRED_EXACT_PATH_REFERENCE_MISSING",
      correlation_id: "unresolved",
    };
  }

  try {
    const response = await fetch(path, {
      method: contract.method,
      cache: "no-store",
      signal: input.signal,
      headers: contract.method === "POST" ? { "content-type": "application/json" } : undefined,
      body: contract.method === "POST" ? JSON.stringify(input.payload ?? null) : undefined,
    });
    const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
    const value: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const body = typeof value === "object" && value !== null ? value as Record<string, unknown> : null;
      return {
        ok: false,
        error_uid: typeof body?.error_uid === "string" ? body.error_uid : defaultError(input.port_uid),
        reason_code: typeof body?.reason_code === "string" ? body.reason_code : "EDIT_INTEGRATION_PORT_REQUEST_FAILED",
        correlation_id: typeof body?.correlation_id === "string" ? body.correlation_id : correlation_id,
      };
    }
    return { ok: true, value, correlation_id };
  } catch {
    return {
      ok: false,
      error_uid: defaultError(input.port_uid),
      reason_code: "EDIT_INTEGRATION_PORT_REQUEST_FAILED",
      correlation_id: "unresolved",
    };
  }
}
