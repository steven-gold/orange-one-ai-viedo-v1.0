import type { CoreActionUid } from "./coreRuntimeContract";

export type CoreAiMode = "SINGLE" | "MULTI";

export type CoreExactRefs = {
  project_id: string | null;
  project_version_ref: string | null;
  topic_id: string | null;
  topic_version_ref: string | null;
  blueprint_version_ref: string | null;
  conversation_id: string | null;
  candidate_ref: string | null;
};

export type CoreClientState = CoreExactRefs & {
  /** Compatibility view only. Runtime operations must use project_id/project_version_ref explicitly. */
  project_ref: string | null;
  /** Compatibility view only. Runtime operations must use topic_id/topic_version_ref explicitly. */
  topic_ref: string | null;
  work_item: string | null;
  thread_ref: string | null;
  ai_mode: CoreAiMode;
  assistant_record_open: boolean;
  composer_message_refs: string[];
  decision_evidence_refs: string[];
  attachment_refs: string[];
  reference_refs: string[];
};

export const EMPTY_CORE_EXACT_REFS: CoreExactRefs = {
  project_id: null,
  project_version_ref: null,
  topic_id: null,
  topic_version_ref: null,
  blueprint_version_ref: null,
  conversation_id: null,
  candidate_ref: null,
};

export const INITIAL_CORE_CLIENT_STATE: CoreClientState = {
  ...EMPTY_CORE_EXACT_REFS,
  project_ref: null,
  topic_ref: null,
  work_item: null,
  thread_ref: null,
  ai_mode: "SINGLE",
  assistant_record_open: false,
  composer_message_refs: [],
  decision_evidence_refs: [],
  attachment_refs: [],
  reference_refs: [],
};

export type CoreClientAction =
  | { action_uid: "CORE-01-ACT-PROJECT-SELECT"; project_ref: string | null; project_id?: string | null; project_version_ref?: string | null }
  | { action_uid: "CORE-01-ACT-TOPIC-SELECT"; topic_ref: string | null; topic_id?: string | null; topic_version_ref?: string | null }
  | { action_uid: "CORE-01-ACT-WORK-ITEM-SELECT"; work_item: string | null }
  | { action_uid: "CORE-01-ACT-THREAD-SELECT"; thread_ref: string | null; conversation_id?: string | null }
  | { action_uid: "CORE-01-ACT-AI-MODE-SINGLE" }
  | { action_uid: "CORE-01-ACT-AI-MODE-MULTI" }
  | { action_uid: "CORE-01-ACT-ASSISTANT-RECORD"; open: boolean }
  | { action_uid: "CORE-01-ACT-MSG-QUOTE"; message_ref: string }
  | { action_uid: "CORE-01-ACT-MSG-CONTINUE"; message_ref: string }
  | { action_uid: "CORE-01-ACT-MSG-DECISION"; message_ref: string }
  | { action_uid: "CORE-01-ACT-ATTACHMENT"; attachment_ref: string }
  | { action_uid: "CORE-01-ACT-REFERENCE-ATTACH"; reference_ref: string };

function appendUnique(values: string[], value: string): string[] {
  return values.includes(value) ? values : [...values, value];
}

export function mergeCoreExactRefs(state: CoreClientState, refs: Partial<CoreExactRefs>): CoreClientState {
  const next: CoreClientState = { ...state, ...refs };
  if (refs.project_id !== undefined) next.project_ref = refs.project_id;
  if (refs.topic_id !== undefined) next.topic_ref = refs.topic_id;
  if (refs.conversation_id !== undefined) next.thread_ref = refs.conversation_id;
  return next;
}

export function reduceCoreClientState(state: CoreClientState, action: CoreClientAction): CoreClientState {
  switch (action.action_uid) {
    case "CORE-01-ACT-PROJECT-SELECT": {
      const project_id = action.project_id ?? action.project_ref;
      return {
        ...state,
        project_id,
        project_version_ref: action.project_version_ref ?? null,
        project_ref: project_id,
        topic_id: null,
        topic_version_ref: null,
        topic_ref: null,
        blueprint_version_ref: null,
        work_item: null,
        conversation_id: null,
        thread_ref: null,
        candidate_ref: null,
        composer_message_refs: [],
        decision_evidence_refs: [],
      };
    }
    case "CORE-01-ACT-TOPIC-SELECT": {
      const topic_id = action.topic_id ?? action.topic_ref;
      return {
        ...state,
        topic_id,
        topic_version_ref: action.topic_version_ref ?? null,
        topic_ref: topic_id,
        blueprint_version_ref: null,
        work_item: null,
        conversation_id: null,
        thread_ref: null,
        candidate_ref: null,
        composer_message_refs: [],
        decision_evidence_refs: [],
      };
    }
    case "CORE-01-ACT-WORK-ITEM-SELECT":
      return { ...state, work_item: action.work_item, conversation_id: null, thread_ref: null, composer_message_refs: [], decision_evidence_refs: [] };
    case "CORE-01-ACT-THREAD-SELECT": {
      const conversation_id = action.conversation_id ?? action.thread_ref;
      return { ...state, conversation_id, thread_ref: conversation_id, composer_message_refs: [], decision_evidence_refs: [] };
    }
    case "CORE-01-ACT-AI-MODE-SINGLE": return { ...state, ai_mode: "SINGLE" };
    case "CORE-01-ACT-AI-MODE-MULTI": return { ...state, ai_mode: "MULTI" };
    case "CORE-01-ACT-ASSISTANT-RECORD": return { ...state, assistant_record_open: action.open };
    case "CORE-01-ACT-MSG-QUOTE":
    case "CORE-01-ACT-MSG-CONTINUE": return { ...state, composer_message_refs: appendUnique(state.composer_message_refs, action.message_ref) };
    case "CORE-01-ACT-MSG-DECISION": return { ...state, decision_evidence_refs: appendUnique(state.decision_evidence_refs, action.message_ref) };
    case "CORE-01-ACT-ATTACHMENT": return { ...state, attachment_refs: appendUnique(state.attachment_refs, action.attachment_ref) };
    case "CORE-01-ACT-REFERENCE-ATTACH": return { ...state, reference_refs: appendUnique(state.reference_refs, action.reference_ref) };
  }
}

export const CORE_CLIENT_STATE_ACTIONS: readonly CoreActionUid[] = [
  "CORE-01-ACT-PROJECT-SELECT","CORE-01-ACT-TOPIC-SELECT","CORE-01-ACT-WORK-ITEM-SELECT","CORE-01-ACT-THREAD-SELECT",
  "CORE-01-ACT-AI-MODE-SINGLE","CORE-01-ACT-AI-MODE-MULTI","CORE-01-ACT-ASSISTANT-RECORD","CORE-01-ACT-MSG-QUOTE",
  "CORE-01-ACT-MSG-CONTINUE","CORE-01-ACT-MSG-DECISION","CORE-01-ACT-ATTACHMENT","CORE-01-ACT-REFERENCE-ATTACH"
] as const;
