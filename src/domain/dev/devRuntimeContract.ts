export const DEV_AUTHORITY_STATUS = "FINAL_LOCKED" as const;
export const DEV_SYSTEM_IMPLEMENTATION_STATUS = "NOT_EXECUTED" as const;
export const DEV_SECTION_COUNT = 9 as const;
export const DEV_COMPONENT_COUNT = 15 as const;
export const DEV_CONTROL_COUNT = 22 as const;
export const DEV_ACTION_COUNT = 22 as const;
export const DEV_GATE_COUNT = 15 as const;
export const DEV_ERROR_COUNT = 12 as const;

export const DEV_PAGE_STATES = [
  "LOADING",
  "READY",
  "EMPTY",
  "ERROR",
  "POLICY_BLOCKED",
  "VERSION_CONFLICT",
  "REVIEW_REQUIRED",
  "EXTERNAL_PENDING",
  "READ_ONLY",
  "ARCHIVED",
] as const;

export type DevPageState = (typeof DEV_PAGE_STATES)[number];

export const DEV_RUNTIME_STATES = [
  ...DEV_PAGE_STATES,
  "RUNNING",
  "PAUSED",
  "STOPPED",
  "REVIEW",
  "APPROVED",
  "QUEUED",
] as const;

export type DevRuntimeState = (typeof DEV_RUNTIME_STATES)[number];

export const DEV_GATE_UIDS = [
  "DEV-01-GATE-PAGE",
  "DEV-01-GATE-DISCOVERY-START",
  "DEV-01-GATE-DISCOVERY-RUNNING",
  "DEV-01-GATE-DISCOVERY-PAUSED",
  "DEV-01-GATE-DIRECTORY-READ",
  "DEV-01-GATE-MERGE",
  "DEV-01-GATE-MERGE-CONFIRM",
  "DEV-01-GATE-EXPORT",
  "DEV-01-GATE-MESSAGE-WRITE",
  "DEV-01-GATE-MESSAGE-REVIEW",
  "DEV-01-GATE-CAMPAIGN",
  "DEV-01-GATE-CAMPAIGN-APPROVAL",
  "DEV-01-GATE-DELIVERY-READ",
  "DEV-01-GATE-DISPATCH",
  "DEV-01-GATE-KILL-SWITCH",
] as const;

export type DevGateUid = (typeof DEV_GATE_UIDS)[number];

export const DEV_ERROR_UIDS = [
  "DEV-01-ERR-AUTH",
  "DEV-01-ERR-SOURCE",
  "DEV-01-ERR-CONNECTOR",
  "DEV-01-ERR-IDENTITY",
  "DEV-01-ERR-MERGE",
  "DEV-01-ERR-MESSAGE-POLICY",
  "DEV-01-ERR-SUPPRESSION",
  "DEV-01-ERR-CAMPAIGN",
  "DEV-01-ERR-DELIVERY",
  "DEV-01-ERR-KILL",
  "DEV-01-ERR-PARTIAL",
  "DEV-01-ERR-UNDEFINED",
] as const;

export type DevErrorUid = (typeof DEV_ERROR_UIDS)[number];

export function isDevPageState(value: unknown): value is DevPageState {
  return typeof value === "string" && (DEV_PAGE_STATES as readonly string[]).includes(value);
}

export function isDevRuntimeState(value: unknown): value is DevRuntimeState {
  return typeof value === "string" && (DEV_RUNTIME_STATES as readonly string[]).includes(value);
}

export function isDevGateUid(value: string): value is DevGateUid {
  return (DEV_GATE_UIDS as readonly string[]).includes(value);
}
