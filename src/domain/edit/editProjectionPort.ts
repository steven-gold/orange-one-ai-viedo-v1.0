import type { EditResolvedContext } from "./editClientState";

export type EditProjectionResolver = {
  resolve: (rawProjection: unknown) => Promise<EditResolvedContext> | EditResolvedContext;
};

export type EditProjectionReadResult =
  | { ok: true; context: EditResolvedContext; correlation_id: string }
  | { ok: false; error_uid: string; reason_code: string; correlation_id: string };

let resolver: EditProjectionResolver | null = null;

export function configureEditProjectionResolver(next: EditProjectionResolver) {
  resolver = next;
}

export async function readEditProjection(signal?: AbortSignal): Promise<EditProjectionReadResult> {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/EDIT-01", { method: "GET", cache: "no-store", signal });
  } catch {
    return { ok:false, error_uid:"EDIT-01-ERR-CONTEXT-001", reason_code:"EDIT_PROJECTION_REQUEST_FAILED", correlation_id:"unresolved" };
  }

  const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const body = typeof payload === "object" && payload !== null ? payload as Record<string, unknown> : null;
    return {
      ok:false,
      error_uid:"EDIT-01-ERR-CONTEXT-001",
      reason_code:typeof body?.reason_code === "string" ? body.reason_code : "EDIT_PROJECTION_READ_FAILED",
      correlation_id:typeof body?.correlation_id === "string" ? body.correlation_id : correlation_id,
    };
  }

  const current = resolver;
  if (!current) {
    return { ok:false, error_uid:"EDIT-01-ERR-CONTEXT-001", reason_code:"EDIT_PROJECTION_ADAPTER_NOT_BOUND", correlation_id };
  }

  try {
    const context = await current.resolve(payload);
    return { ok:true, context, correlation_id };
  } catch {
    return { ok:false, error_uid:"EDIT-01-ERR-CONTEXT-001", reason_code:"EDIT_PROJECTION_ADAPTER_REJECTED", correlation_id };
  }
}
