import type { SysAiMode, SysCouncilMode } from "./systemRuntimeContract";

export type SystemClientState = {
  system_change_id: string | null;
  conversation_id: string | null;
  thread_id: string | null;
  branch_id: string | null;
  ai_mode: SysAiMode;
  council_mode: SysCouncilMode;
  draft: string;
  attachment_refs: string[];
  selected_reference_ref: string | null;
};

export const INITIAL_SYSTEM_CLIENT_STATE: SystemClientState = {
  system_change_id: null,
  conversation_id: null,
  thread_id: null,
  branch_id: null,
  ai_mode: "SINGLE_AI",
  council_mode: "DISCUSSION",
  draft: "",
  attachment_refs: [],
  selected_reference_ref: null,
};

export type SystemClientAction =
  | { type: "BIND_CONTEXT"; system_change_id: string | null; conversation_id: string | null; thread_id: string | null; branch_id: string | null }
  | { type: "AI_MODE_SINGLE" }
  | { type: "AI_MODE_MULTI" }
  | { type: "COUNCIL_DISCUSSION" }
  | { type: "COUNCIL_PARALLEL" }
  | { type: "DRAFT"; value: string }
  | { type: "ATTACHMENT_REF"; value: string }
  | { type: "REFERENCE_SELECT"; value: string | null };

export function reduceSystemClientState(state: SystemClientState, action: SystemClientAction): SystemClientState {
  switch (action.type) {
    case "BIND_CONTEXT":
      return { ...state, system_change_id: action.system_change_id, conversation_id: action.conversation_id, thread_id: action.thread_id, branch_id: action.branch_id };
    case "AI_MODE_SINGLE":
      return { ...state, ai_mode: "SINGLE_AI", council_mode: "DISCUSSION" };
    case "AI_MODE_MULTI":
      return { ...state, ai_mode: "MULTI_AI", council_mode: state.council_mode === "PARALLEL" ? "PARALLEL" : "DISCUSSION" };
    case "COUNCIL_DISCUSSION":
      return state.ai_mode === "MULTI_AI" ? { ...state, council_mode: "DISCUSSION" } : state;
    case "COUNCIL_PARALLEL":
      return state.ai_mode === "MULTI_AI" ? { ...state, council_mode: "PARALLEL" } : state;
    case "DRAFT":
      return { ...state, draft: action.value };
    case "ATTACHMENT_REF":
      return { ...state, attachment_refs: state.attachment_refs.includes(action.value) ? state.attachment_refs : [...state.attachment_refs, action.value] };
    case "REFERENCE_SELECT":
      return { ...state, selected_reference_ref: action.value };
  }
}
