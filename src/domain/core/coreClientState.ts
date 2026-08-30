import type { CoreActionUid } from "./coreRuntimeContract";

export type CoreAiMode = "SINGLE" | "MULTI";

export type CoreClientState = {
  project_ref: string | null;
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

export const INITIAL_CORE_CLIENT_STATE: CoreClientState = {
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
  | { action_uid: "CORE-01-ACT-PROJECT-SELECT"; project_ref: string | null }
  | { action_uid: "CORE-01-ACT-TOPIC-SELECT"; topic_ref: string | null }
  | { action_uid: "CORE-01-ACT-WORK-ITEM-SELECT"; work_item: string | null }
  | { action_uid: "CORE-01-ACT-THREAD-SELECT"; thread_ref: string | null }
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

export function reduceCoreClientState(state: CoreClientState, action: CoreClientAction): CoreClientState {
  switch (action.action_uid) {
    case "CORE-01-ACT-PROJECT-SELECT":
      return { ...state, project_ref: action.project_ref, topic_ref: null, work_item: null, thread_ref: null, composer_message_refs: [], decision_evidence_refs: [] };
    case "CORE-01-ACT-TOPIC-SELECT":
      return { ...state, topic_ref: action.topic_ref, work_item: null, thread_ref: null, composer_message_refs: [], decision_evidence_refs: [] };
    case "CORE-01-ACT-WORK-ITEM-SELECT":
      return { ...state, work_item: action.work_item, thread_ref: null, composer_message_refs: [], decision_evidence_refs: [] };
    case "CORE-01-ACT-THREAD-SELECT":
      return { ...state, thread_ref: action.thread_ref, composer_message_refs: [], decision_evidence_refs: [] };
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
