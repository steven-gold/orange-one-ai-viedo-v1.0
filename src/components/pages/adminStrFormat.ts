import { displayBoundValue } from "./displayValue";

export function displayAdminStrValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}

export interface AdminStrPageStateInput {
  loading: boolean;
  fetchError: string | null;
  authorized: boolean;
  writeAuthorized: boolean;
  errorCode: string | null;
  resourceStatus: string | null;
  hasRuntimeState: boolean;
}

// Contract state_contract.allowed_states for admin:STR-01:
// LOADING READY EMPTY ERROR POLICY_BLOCKED VERSION_CONFLICT REVIEW_REQUIRED
// EXTERNAL_PENDING READ_ONLY ARCHIVED. DENIED maps to POLICY_BLOCKED per
// server_gate_order (account_permission); unregistered/undefined refusals
// map to POLICY_BLOCKED (BLOCK + REPORT_AUTHORITY_GAP).
export function deriveAdminStrPageState(input: AdminStrPageStateInput): string {
  if (input.loading) return "LOADING";
  if (input.fetchError) return "ERROR";
  if (!input.authorized) return "POLICY_BLOCKED";
  const code = (input.errorCode ?? "").toUpperCase();
  if (code === "ADMIN-STR-ERR-VERSION") return "VERSION_CONFLICT";
  if (code === "ADMIN-STR-ERR-STATE" || code === "ADMIN-STR-ERR-AUTH" || code === "ADMIN-STR-ERR-UNDEFINED") return "POLICY_BLOCKED";
  if (input.errorCode) return "ERROR";
  if (!input.writeAuthorized) return "READ_ONLY";
  const resourceStatus = (input.resourceStatus ?? "").toUpperCase();
  if (resourceStatus === "RETIRED") return "ARCHIVED";
  if (resourceStatus === "REVIEW") return "REVIEW_REQUIRED";
  if (resourceStatus === "PENDING_EXTERNAL") return "EXTERNAL_PENDING";
  if (!input.hasRuntimeState) return "EMPTY";
  return "READY";
}
