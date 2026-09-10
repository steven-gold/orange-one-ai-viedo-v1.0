import { createControlledTestMetadata, isControlledTestMode } from "../testing/controlledTestData";

export type CoreLockCommandKind = "DNA_LOCK" | "CORE_REVIEW" | "MOTHER_LOCK" | "CHILD_LOCK";

export type CoreLockCommandContext = {
  kind: CoreLockCommandKind;
  project_id: string | null;
  project_version_ref: string | null;
  dna_version_ref: string | null;
  blueprint_version_ref: string | null;
  topic_id: string | null;
  evidence_refs: readonly string[];
  workspace_id?: string | null;
  target_ref?: string | null;
  expected_version_no?: number | null;
  request_reason?: string | null;
  criteria_version_id?: string | null;
  correlation_id?: string | null;
  idempotency_key?: string | null;
};

export type CoreLockCommandPayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; reason_code: string };

export type CoreLockCommandPayloadAdapter = {
  buildPayload: (context: CoreLockCommandContext) => Promise<CoreLockCommandPayloadResult> | CoreLockCommandPayloadResult;
};

let adapter: CoreLockCommandPayloadAdapter | null = null;

export function configureCoreLockCommandPayloadAdapter(next: CoreLockCommandPayloadAdapter) {
  adapter = next;
}

function valid(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) && Object.keys(value).length > 0;
}

function controlledTestPayload(context: CoreLockCommandContext): CoreLockCommandPayloadResult {
  return {
    ok: true,
    payload: {
      ...createControlledTestMetadata(`CORE-${context.kind}`),
      ...context,
    },
  };
}

export async function requestCoreLockCommandPayload(context: CoreLockCommandContext): Promise<CoreLockCommandPayloadResult> {
  if (context.kind === "MOTHER_LOCK" || context.kind === "CHILD_LOCK") {
    const workspace_id=context.workspace_id?.trim()||null;
    const project_id=context.project_id?.trim()||null;
    const topic_id=context.topic_id?.trim()||null;
    const target_ref=context.target_ref?.trim()||null;
    const version_no=context.expected_version_no??null;
    const request_reason=context.request_reason?.trim()||null;
    const criteria_version_id=context.criteria_version_id?.trim()||null;
    const correlation_id=context.correlation_id?.trim()||null;
    const idempotency_key=context.idempotency_key?.trim()||null;
    if(!workspace_id||!project_id)return{ok:false,reason_code:"R9_CONTEXT_REQUIRED"};
    if(context.kind==="CHILD_LOCK"&&!topic_id)return{ok:false,reason_code:"R9_CONTEXT_REQUIRED"};
    if(!target_ref)return{ok:false,reason_code:"TARGET_REF_INVALID"};
    if(!Number.isInteger(version_no)||Number(version_no)<1)return{ok:false,reason_code:"EXPECTED_VERSION_INVALID"};
    if(!request_reason)return{ok:false,reason_code:"REQUEST_REASON_INVALID"};
    if(!criteria_version_id)return{ok:false,reason_code:"LOCK_CRITERIA_VERSION_REQUIRED"};
    if(!correlation_id||!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(correlation_id))return{ok:false,reason_code:"CORRELATION_ID_INVALID"};
    if(!idempotency_key||idempotency_key.length<16||idempotency_key.length>128)return{ok:false,reason_code:"IDEMPOTENCY_KEY_INVALID"};
    const evidence_refs=Array.from(new Set(context.evidence_refs.map(ref=>ref.trim()).filter(Boolean)));
    if(evidence_refs.length<1)return{ok:false,reason_code:"LOCK_EVIDENCE_REQUIRED"};
    return{
      ok:true,
      payload:{
        scope:context.kind==="CHILD_LOCK"?{workspace_id,project_id,topic_id}:{workspace_id,project_id},
        expected_version:`v${version_no}`,
        correlation_id,
        idempotency_key,
        target_ref,
        request_reason,
        requested_scope_refs:[criteria_version_id,...evidence_refs],
      },
    };
  }
  const current = adapter;
  if (!current) {
    if (isControlledTestMode()) return controlledTestPayload(context);
    return { ok: false, reason_code: `${context.kind}_REGISTERED_COMMAND_SCHEMA_ADAPTER_NOT_BOUND` };
  }
  try {
    const result = await current.buildPayload(context);
    if (!result.ok) return result;
    if (!valid(result.payload)) return { ok: false, reason_code: `${context.kind}_REGISTERED_COMMAND_SCHEMA_PAYLOAD_EMPTY` };
    return result;
  } catch {
    return { ok: false, reason_code: `${context.kind}_REGISTERED_COMMAND_SCHEMA_ADAPTER_FAILED` };
  }
}
