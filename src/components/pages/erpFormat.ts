import { displayBoundValue } from "./displayValue";

export function displayErpValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}

export interface ErpPageStateInput {
  loading: boolean;
  authorized: boolean;
  errorCode: string | null;
  connectorStatus: string | null;
  syncJobsRaw: string | null;
  snapshotRaw: string | null;
  completenessRaw: string | null;
}

interface ErpSyncJobShape {
  status?: string;
  at?: string;
}

// ACPOS ERP-01 state_model vocabulary: the visible page state always
// resolves to one registered vocabulary value (10 common + 9 erp_specific);
// unlisted values never render. Connector FAILED maps to CONNECTOR_DEGRADED
// at page level (no CONNECTOR_FAILED vocab entry) while the status field
// keeps the exact runtime text.
export function deriveErpPageState(input: ErpPageStateInput): string {
  if (input.loading) return "LOADING";
  if (input.errorCode === "ERP-01-ERR-VERSION") return "VERSION_CONFLICT";
  if (input.errorCode) return "ERROR";
  if (!input.authorized) return "POLICY_BLOCKED";
  const status = (input.connectorStatus ?? "").toUpperCase();
  if (status === "VALIDATING") return "CONNECTOR_VALIDATING";
  if (status === "CONFIGURING") return "CONNECTOR_CONFIGURING";
  let jobs: ErpSyncJobShape[] = [];
  try {
    const parsed = input.syncJobsRaw ? (JSON.parse(input.syncJobsRaw) as ErpSyncJobShape[]) : [];
    if (Array.isArray(parsed)) jobs = parsed;
  } catch {
    jobs = [];
  }
  const last = jobs[jobs.length - 1];
  const lastStatus = (last?.status ?? "").toUpperCase();
  if (lastStatus === "RUNNING") return "SNAPSHOT_SYNCING";
  if (lastStatus === "FAILED") return "SNAPSHOT_FAILED";
  if (status === "DEGRADED" || status === "FAILED") return "CONNECTOR_DEGRADED";
  let snapshotAt: string | null = null;
  try {
    const parsed = input.snapshotRaw ? (JSON.parse(input.snapshotRaw) as { at?: string }) : null;
    snapshotAt = parsed?.at ?? null;
  } catch {
    snapshotAt = null;
  }
  if (snapshotAt && last?.at && last.at > snapshotAt) return "SNAPSHOT_STALE";
  const completeness = Number.parseInt((input.completenessRaw ?? "").replace("%", ""), 10);
  const hasSnapshot = Boolean(input.snapshotRaw);
  if (hasSnapshot && Number.isFinite(completeness) && completeness < 100) return "DATA_INCOMPLETE";
  if (status === "READY" && hasSnapshot && (!Number.isFinite(completeness) || completeness >= 100)) return "READY";
  if (hasSnapshot) return "CONNECTOR_UNCONFIGURED";
  return status ? "CONNECTOR_CONFIGURING" : "CONNECTOR_UNCONFIGURED";
}
