import { displayBoundValue } from "./displayValue";

export function displaySg02Value(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}

export interface Sg02PageStateInput {
  loading: boolean;
  fetchError: string | null;
  authorized: boolean;
  configureAuthorized: boolean;
  errorCode: string | null;
  resourceStatus: string | null;
  hasRuntimeState: boolean;
}

// Contract state_contract.allowed_states vocabulary (10 states). Same
// derivation precedent as deriveAdminStrPageState.
export function deriveSg02PageState(input: Sg02PageStateInput): string {
  if (input.loading) return "LOADING";
  if (input.fetchError) return "ERROR";
  if (!input.authorized) return "POLICY_BLOCKED";
  if (input.errorCode === "SG-02-ERR-VERSION") return "VERSION_CONFLICT";
  if (input.errorCode === "SG-02-ERR-STATE") return "REVIEW_REQUIRED";
  if (input.errorCode) return "POLICY_BLOCKED";
  if (input.resourceStatus === "REVIEW") return "REVIEW_REQUIRED";
  if (input.resourceStatus === "RETIRED") return "ARCHIVED";
  if (!input.configureAuthorized) return "READ_ONLY";
  if (!input.hasRuntimeState) return "EMPTY";
  return "READY";
}
