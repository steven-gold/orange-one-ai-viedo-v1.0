import { displayBoundValue } from "./displayValue";

export function displayStrValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}

export interface StrPageStateInput {
  authorized: boolean;
  sending: boolean;
  mode: string | null;
  topic: string | null;
  candidates: string | null;
  reviewState: string | null;
  decisionResult: string | null;
  feedbackActual: string | null;
  feedbackLearning: string | null;
  error: string | null;
}

// Contract page states (STR-01 page_states): the visible state always
// resolves to one registered display value; unlisted values never render.
export function deriveStrPageState(input: StrPageStateInput): string {
  if (input.error || !input.authorized) return "ERROR/BLOCKED";
  if (input.sending) {
    if (input.mode === "MULTI" && input.topic) return "ANALYZING";
    return "RESPONDING";
  }
  if (!input.topic) return "EMPTY";
  if (input.decisionResult === "ADOPTED_CONTEXT") {
    return input.feedbackActual || input.feedbackLearning ? "FEEDBACK_AVAILABLE" : "ADOPTED_CONTEXT";
  }
  if (input.reviewState === "REVIEW_REQUIRED") return "REVIEW_REQUIRED";
  if (input.candidates) return "CANDIDATE_READY";
  return "READY";
}
