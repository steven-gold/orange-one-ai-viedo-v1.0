import { displayBoundValue } from "./displayValue";

export function displayInfoValue(value: unknown, loading: boolean): string {
  // Contract hard lock: missing = —; loading = 載入中.
  if (loading && (value === null || value === undefined || value === "")) return "載入中";
  return displayBoundValue(value, loading);
}

export interface InfoPageStateInput {
  loading: boolean;
  fetchError: string | null;
  authorized: boolean;
  errorCode: string | null;
  stale: boolean;
  incomplete: boolean;
  hasOpenCandidates: boolean;
  hasRuntimeState: boolean;
}

// Contract page_states (8): LOADING READY EMPTY STALE INCOMPLETE ERROR
// POLICY_BLOCKED CONTEXT_CANDIDATE. DENIED maps to POLICY_BLOCKED (DENIED is
// an unlisted state).
export function deriveInfoPageState(input: InfoPageStateInput): string {
  if (input.loading) return "LOADING";
  if (input.fetchError) return "ERROR";
  if (!input.authorized) return "POLICY_BLOCKED";
  const code = (input.errorCode ?? "").toUpperCase();
  if (code === "INFO-01-ERR-PERM-001") return "POLICY_BLOCKED";
  if (code === "INFO-01-ERR-UNDEFINED-001") return "ERROR";
  if (code) return "ERROR";
  if (input.incomplete) return "INCOMPLETE";
  if (input.stale) return "STALE";
  if (input.hasOpenCandidates) return "CONTEXT_CANDIDATE";
  if (!input.hasRuntimeState) return "EMPTY";
  return "READY";
}
