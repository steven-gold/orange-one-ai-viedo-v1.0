import { createControlledTestMetadata, isControlledTestMode } from "../testing/controlledTestData";

export type CoreCandidateCreateContext = {
  human_decision: string;
  evidence_refs: readonly string[];
  project_id: string | null;
  topic_id: string | null;
  work_item: string | null;
};

export type CoreCandidateDecisionKind = "ACCEPT" | "RETURN";

export type CoreCandidateDecisionContext = {
  candidate_ref: string;
  decision: CoreCandidateDecisionKind;
  reason_text: string;
  evidence_refs: readonly string[];
};

export type CoreCandidatePayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; reason_code: string };

export type CoreCandidatePayloadAdapter = {
  buildCreatePayload: (context: CoreCandidateCreateContext) => Promise<CoreCandidatePayloadResult> | CoreCandidatePayloadResult;
  buildDecisionPayload: (context: CoreCandidateDecisionContext) => Promise<CoreCandidatePayloadResult> | CoreCandidatePayloadResult;
};

let adapter: CoreCandidatePayloadAdapter | null = null;

export function configureCoreCandidatePayloadAdapter(next: CoreCandidatePayloadAdapter) {
  adapter = next;
}

function valid(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) && Object.keys(value).length > 0;
}

function controlledTestPayload(kind: "CREATE" | "DECISION", context: CoreCandidateCreateContext | CoreCandidateDecisionContext): CoreCandidatePayloadResult {
  return {
    ok: true,
    payload: {
      ...createControlledTestMetadata(`CORE-CANDIDATE-${kind}`),
      ...context,
    },
  };
}

async function normalize(
  kind: "CREATE" | "DECISION",
  context: CoreCandidateCreateContext | CoreCandidateDecisionContext,
  build: (current: CoreCandidatePayloadAdapter) => Promise<CoreCandidatePayloadResult> | CoreCandidatePayloadResult,
): Promise<CoreCandidatePayloadResult> {
  const current = adapter;
  if (!current) {
    if (isControlledTestMode()) return controlledTestPayload(kind, context);
    return { ok: false, reason_code: `CANDIDATE_${kind}_REGISTERED_SCHEMA_ADAPTER_NOT_BOUND` };
  }
  try {
    const result = await build(current);
    if (!result.ok) return result;
    if (!valid(result.payload)) return { ok: false, reason_code: `CANDIDATE_${kind}_REGISTERED_SCHEMA_PAYLOAD_EMPTY` };
    return result;
  } catch {
    return { ok: false, reason_code: `CANDIDATE_${kind}_REGISTERED_SCHEMA_ADAPTER_FAILED` };
  }
}

export function requestCoreCandidateCreatePayload(context: CoreCandidateCreateContext) {
  return normalize("CREATE", context, (current) => current.buildCreatePayload(context));
}

export function requestCoreCandidateDecisionPayload(context: CoreCandidateDecisionContext) {
  return normalize("DECISION", context, (current) => current.buildDecisionPayload(context));
}
