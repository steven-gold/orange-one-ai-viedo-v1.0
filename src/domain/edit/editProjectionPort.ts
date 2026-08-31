import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import type { EditListItem, EditResolvedContext } from "./editClientState";

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

export function isEditProjectionResolverBound() { return resolver !== null; }

function textOrNull(value: unknown) { return value === null || typeof value === "string"; }
function validLists(value: unknown) {
  if (!value || typeof value !== "object") return false;
  return Object.values(value as Record<string, unknown>).every((items) => Array.isArray(items) && items.every((item) => item && typeof item === "object" && typeof (item as EditListItem).ref === "string" && typeof (item as EditListItem).label === "string"));
}
function validProjection(value: unknown): value is EditResolvedContext {
  if (!value || typeof value !== "object") return false;
  const p = value as Partial<EditResolvedContext>;
  const nullable = [p.project_id,p.topic_id,p.task_id,p.locked_blueprint_ref,p.production_package_ref,p.input_manifest_ref,p.input_fingerprint,p.working_draft_ref,p.editing_run_id,p.voice_run_id,p.saved_edit_version_id,p.output_version_id,p.dialogue_timing_binding_ref,p.page_state_uid,p.current_stage_uid,p.current_stage_phase,p.current_error_uid,p.preview_uri,p.final_preview_uri];
  if (nullable.some((item) => !textOrNull(item))) return false;
  if (!(p.current_stage_score === null || typeof p.current_stage_score === "number")) return false;
  if (!p.values || typeof p.values !== "object" || Object.values(p.values).some((item) => typeof item !== "string")) return false;
  if (!validLists(p.lists)) return false;
  if (!p.gate_state || typeof p.gate_state !== "object" || Object.values(p.gate_state).some((item) => typeof item !== "boolean")) return false;
  return true;
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
    if (isControlledTestMode() && validProjection(payload)) return { ok:true, context:payload, correlation_id };
    return { ok:false, error_uid:"EDIT-01-ERR-CONTEXT-001", reason_code:"EDIT_PROJECTION_ADAPTER_NOT_BOUND", correlation_id };
  }

  try {
    const context = await current.resolve(payload);
    if (!validProjection(context)) throw new Error("EDIT_PROJECTION_SCHEMA_REJECTED");
    return { ok:true, context, correlation_id };
  } catch {
    return { ok:false, error_uid:"EDIT-01-ERR-CONTEXT-001", reason_code:"EDIT_PROJECTION_ADAPTER_REJECTED", correlation_id };
  }
}
