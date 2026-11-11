export const QA_COMPONENTS = [
  "QA-01-CMP-CONTEXT",
  "QA-01-CMP-QUEUE",
  "QA-01-CMP-VIEWER",
  "QA-01-CMP-COMPARE",
  "QA-01-CMP-SCRIPT",
  "QA-01-CMP-CRITERIA",
  "QA-01-CMP-EVIDENCE",
  "QA-01-CMP-SCORE",
  "QA-01-CMP-GATE",
  "QA-01-CMP-FINDING-LIST",
  "QA-01-CMP-FINDING-FORM",
  "QA-01-CMP-MANUAL",
  "QA-01-CMP-CORRECTION",
  "QA-01-CMP-RECHECK",
  "QA-01-CMP-RELEASE-READY",
  "QA-01-CMP-RELEASE",
  "QA-01-CMP-STATUS",
  "QA-01-CMP-REVIEW-MODE",
  "QA-01-CMP-AUTO-PROGRESS",
  "QA-01-CMP-EVIDENCE-CAPTURE",
  "QA-01-CMP-MANUAL-DECISION",
] as const;

// Word QA-01 :356-1061: the authoritative control/action matrices live in
// the domain module; this client module re-exports them so the page, the
// preview and the server can never drift apart.
export {
  QA_VISIBLE_CONTROLS,
  QA_CONTROL_ACTIONS,
  QA_PERMISSIONS,
} from "@/server/domain/qa";
export { QA_UI_LOCAL_ACTIONS } from "@/lib/qaActionPreview";
