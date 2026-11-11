// Word QA-01 §State: server-authoritative workbench state projections.
// Every field here is derived from exact inbound evidence or explicit human
// actions; the page never invents scores, evidence, versions, or states.

export const QA_STATE_SCORECARD_UID = "QA-01-STATE-SCORECARD";
export const QA_STATE_GATE_UID = "QA-01-STATE-GATE";
export const QA_STATE_RELEASE_UID = "QA-01-STATE-RELEASE";
export const QA_STATE_FINDINGS_UID = "QA-01-STATE-FINDINGS";
export const QA_STATE_MANUAL_UID = "QA-01-STATE-MANUAL";
export const QA_STATE_CORRECTION_UID = "QA-01-STATE-CORRECTION";
export const QA_STATE_EVIDENCE_UID = "QA-01-STATE-EVIDENCE";
export const QA_STATE_QUEUE_UID = "QA-01-STATE-QUEUE";
export const QA_STATE_AUTO_UID = "QA-01-STATE-AUTO";
export const QA_STATE_AUDIT_UID = "QA-01-STATE-AUDIT";
export const QA_STATE_ERROR_UID = "QA-01-STATE-ERROR";
export const QA_STATE_SURFACE_UID = "QA-01-STATE-SURFACE";
export const QA_STATE_REVIEW_STATE_UID = "QA-01-STATE-REVIEW-STATE";
export const QA_STATE_TASK_UID = "QA-01-STATE-TASK";

export type QaDimensionStatus = "PASS" | "FINDING" | "HARD_BLOCK" | "N/A";

export interface QaScoreRow {
  uid: string;
  name: string;
  en: string;
  weight: number;
  score: number;
  weighted: number;
  status: QaDimensionStatus;
  hardBlock: boolean;
  evidenceRefs: string[];
  findingCount: number;
}

export interface QaScorecard {
  profileUid: string;
  criteriaVersion: string;
  policyVersion: string;
  threshold: number;
  rows: QaScoreRow[];
  total: number;
  status: "PASS" | "FAIL" | "BLOCKED";
  origin: string;
  at: string;
  targetVersion: string;
}

export interface QaGateState {
  status: "OPEN" | "PASS" | "FAIL";
  decidedBy: string;
  at: string;
  blockers: string[];
  reason: string;
}

export interface QaReleaseState {
  status: "IDLE" | "READY" | "CREATED" | "BLOCKED";
  candidateUid: string;
  at: string;
  readiness: {
    qaPass: boolean;
    findings: boolean;
    manual: boolean;
    rights: boolean;
    policy: boolean;
    channel: boolean;
    rightsGate: boolean;
  };
  blockers: string[];
}

export interface QaFinding {
  uid: string;
  severity: string;
  category: string;
  scope: string;
  evidenceRefs: string[];
  state: "OPEN" | "CLOSED";
  createdAt: string;
  closedAt?: string;
}

export interface QaManualState {
  caseUid: string;
  required: boolean;
  state: "REQUIRED" | "OPEN" | "CLOSED";
  decision: string;
  owner: string;
  blocker: string;
  history: Array<{ at: string; actor: string; action: string; note: string }>;
}

export interface QaCorrectionState {
  requestUid: string;
  status: "DRAFT" | "REQUESTED" | "UPSTREAM_DONE" | "BLOCKED";
  findings: string[];
  scorecards: string[];
  instruction: string;
  scope: string;
  rootCause: string;
  action: string;
  target: string;
  revalidate: string[];
  failedVersion: string;
  newVersion: string;
  at: string;
}

export interface QaEvidenceState {
  outputRef: string;
  checksum: string;
  timecode: string;
  points: string[];
  rangeIn: string;
  rangeOut: string;
  refs: string[];
}

export interface QaQueueReview {
  taskUid: string;
  project: string;
  topic: string;
  sourceDept: string;
  severity: string;
  state: string;
}

export interface QaQueueState {
  filters: { state: string; severity: string; sourceDept: string };
  search: string;
  reviews: QaQueueReview[];
  selected: string;
}

export interface QaAutoState {
  status: "IDLE" | "RUNNING" | "DONE" | "BLOCKED";
  processed: number;
  total: number;
  currentTask: string;
  at: string;
  blocker: string;
}

export interface QaErrorState {
  code: string;
  detail: string;
  at: string;
}

export interface QaAuditState {
  events: Array<{ at: string; actor: string; action: string; correlationId: string }>;
}
