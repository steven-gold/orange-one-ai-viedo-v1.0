import { previewQaAction, QA_UI_LOCAL_ACTIONS } from "./qaActionPreview";
import { QA_VISIBLE_CONTROLS, QA_CONTROL_ACTIONS, QA_PERMISSIONS } from "../server/domain/qa";
import {
  QA_STATE_CORRECTION_UID,
  QA_STATE_FINDINGS_UID,
  QA_STATE_MANUAL_UID,
  QA_STATE_QUEUE_UID,
  QA_STATE_RELEASE_UID,
  QA_STATE_SCORECARD_UID,
} from "./qaState";
import { QA_DIMENSIONS, QA_THRESHOLD } from "./qaCriteria";
import type { QaCorrectionState, QaFinding, QaManualState, QaQueueState, QaReleaseState, QaScorecard } from "./qaState";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

{
  assert(QA_VISIBLE_CONTROLS.length === 87, `QA stays at the 87 authoritative visible controls (got ${QA_VISIBLE_CONTROLS.length})`);
  assert(new Set(QA_VISIBLE_CONTROLS).size === 87, "no duplicate control uids");
  for (const [controlUid, actionUid] of Object.entries(QA_CONTROL_ACTIONS)) {
    assert(QA_VISIBLE_CONTROLS.includes(controlUid as (typeof QA_VISIBLE_CONTROLS)[number]), `action map control ${controlUid} is visible`);
    assert(actionUid.startsWith("QA-01-ACT-"), `action uid shape for ${controlUid}`);
  }
  assert(QA_CONTROL_ACTIONS["QA-01-BTN-START-REVIEW"] === "QA-01-ACT-START-REVIEW", "START-REVIEW binding");
  assert(QA_CONTROL_ACTIONS["QA-01-BTN-RELEASE-CREATE"] === "QA-01-ACT-RELEASE-CREATE", "RELEASE-CREATE binding");
  assert(QA_PERMISSIONS.use === "qa.task.read", "QA_USE permission uid");
  assert(QA_PERMISSIONS.gate === "qa.gate.decide", "gate permission uid");
}

function context(extra: Record<string, string> = {}): Map<string, string> {
  const base: Record<string, string> = {
    "QA-01-FLD-PROJECT": "PRJ-001",
    "QA-01-FLD-TOPIC": "TPC-001",
    "QA-01-FLD-QA-TASK": "TASK-001",
    "QA-01-FLD-TARGET-OUTPUT": "VER-1",
    "QA-01-FLD-QA-SCRIPT": "SCRIPT-1",
    "QA-01-FLD-SCRIPT-HASH": "HASH-1",
    "QA-01-FLD-CRITERIA-VERSION": "CRIT-1",
    "QA-01-FLD-CHECKSUM": "SHA-1",
    "QA-01-FLD-PROVENANCE": "EDIT-01",
    "QA-01-FLD-RIGHTS": "CLEARED",
    "QA-01-FLD-POLICY": "QA-GATE-V1",
    "QA-01-FLD-REQUIRED-CHECKS": "RECHECK",
    "QA-01-FLD-REVIEW-STATE": "NOT_STARTED",
    "QA-01-FLD-GATE-STATUS": "OPEN",
  };
  return new Map(Object.entries({ ...base, ...extra }));
}

function run(
  store: Map<string, string>,
  actionUid: string,
  nextValue?: string,
  controlUid = "QA-01-BTN-START-REVIEW",
): Record<string, string> {
  return previewQaAction(controlUid, actionUid, (uid) => store.get(uid) ?? null, nextValue);
}

function emptyStore(): Map<string, string> {
  return new Map();
}

{
  const patch = run(emptyStore(), "QA-01-ACT-START-REVIEW");
  assert(patch[QA_STATE_SCORECARD_UID] === undefined, "context gate blocks scorecard generation");
  const error = JSON.parse(patch["QA-01-STATE-ERROR"]) as { code: string };
  assert(error.code === "QA-01-ERR-CONTEXT-001", "missing context names the contract error");
}

{
  for (const actionUid of QA_UI_LOCAL_ACTIONS) {
    assert(Object.keys(run(context(), actionUid)).length === 0, `${actionUid} produces no server write`);
  }
}

{
  const store = context();
  const patch = run(store, "QA-01-ACT-START-REVIEW");
  assert(patch["QA-01-FLD-REVIEW-STATE"] === "IN_REVIEW", "review start flips the review state");
  const card = JSON.parse(patch[QA_STATE_SCORECARD_UID]) as QaScorecard;
  assert(card.rows.length === 17, `scorecard derives all 17 dimensions (got ${card.rows.length})`);
  const weightSum = QA_DIMENSIONS.reduce((sum, dim) => sum + dim.weight, 0);
  assert(weightSum === 100, `dimension weights sum to 100 (got ${weightSum})`);
  assert(card.threshold === QA_THRESHOLD, "scorecard threshold follows the profile");
  assert(card.status === "PASS", "complete exact evidence derives a PASS scorecard");
  assert(card.total >= QA_THRESHOLD, `total meets the threshold (got ${card.total})`);
  const rightsRow = card.rows.find((row) => row.uid.includes("RIGHTS"));
  assert(rightsRow && rightsRow.hardBlock, "rights dimension is a hard gate row");

  const blocked = context({ "QA-01-FLD-RIGHTS": "BLOCKED" });
  const denied = run(blocked, "QA-01-ACT-START-REVIEW");
  const blockedError = JSON.parse(denied["QA-01-STATE-ERROR"]) as { code: string };
  assert(blockedError.code === "QA-01-ERR-RIGHTS-001", "BLOCKED rights refuse review start");

  const noChecksum = context({ "QA-01-FLD-CHECKSUM": "" });
  const degraded = run(noChecksum, "QA-01-ACT-START-REVIEW");
  const degradedCard = JSON.parse(degraded[QA_STATE_SCORECARD_UID]) as QaScorecard;
  assert(degradedCard.status === "FAIL" && degradedCard.total < QA_THRESHOLD, "missing output evidence scores fail-closed");
}

{
  const store = context();
  const missingScript = run(context({ "QA-01-FLD-QA-SCRIPT": "" }), "QA-01-ACT-SCORECARD-SUBMIT");
  assert((JSON.parse(missingScript["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-CONTEXT-001", "scoring without the script context stays fail-closed");
  const missingOutput = run(context({ "QA-01-FLD-CHECKSUM": "" }), "QA-01-ACT-SCORECARD-SUBMIT");
  assert((JSON.parse(missingOutput["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-OUTPUT-001", "scoring without output resolution is refused");
  const ok = run(store, "QA-01-ACT-SCORECARD-SUBMIT");
  const card = JSON.parse(ok[QA_STATE_SCORECARD_UID]) as QaScorecard;
  assert(card.profileUid.startsWith("QCP-"), "scorecard stamps the bound criteria profile");
}

{
  const card = JSON.stringify({ profileUid: "QCP-X", targetVersion: "VER-1", status: "FAIL", total: 40, rows: [], threshold: 95, criteriaVersion: "CRIT-1", policyVersion: "QA-GATE-V1", origin: "X", at: "t" });
  const failing = context({ [QA_STATE_SCORECARD_UID]: card });
  const refused = run(failing, "QA-01-ACT-GATE-PASS");
  assert((JSON.parse(refused["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-GATE-001", "gate PASS requires an exact PASS scorecard");
  const failedGate = run(context({ "QA-01-FLD-REVIEW-STATE": "IN_REVIEW" }), "QA-01-ACT-GATE-FAIL");
  const gate = JSON.parse(failedGate["QA-01-STATE-GATE"]) as { status: string };
  assert(gate.status === "FAIL", "governed FAIL decision writes the gate");
  const noReview = run(context(), "QA-01-ACT-GATE-FAIL");
  assert((JSON.parse(noReview["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-GATE-001", "FAIL without active review is refused");
}

{
  const idle = run(context(), "QA-01-ACT-FINDING-CREATE");
  assert((JSON.parse(idle["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-FINDING-001", "finding create outside a review is refused");
  const inReview = context({ "QA-01-FLD-REVIEW-STATE": "IN_REVIEW" });
  const badSeverity = run(inReview, "QA-01-ACT-FINDING-CREATE", JSON.stringify({ severity: "HUGE", category: "LIPSYNC_MISMATCH" }));
  assert((JSON.parse(badSeverity["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-FINDING-001", "severity must use the canonical enum");
  const badCategory = run(inReview, "QA-01-ACT-FINDING-CREATE", JSON.stringify({ severity: "HIGH", category: "MADE_UP" }));
  assert((JSON.parse(badCategory["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-FINDING-001", "unregistered category = BLOCK");
  const ok = run(inReview, "QA-01-ACT-FINDING-CREATE", JSON.stringify({ severity: "HIGH", category: "LIPSYNC_MISMATCH", evidenceRefs: ["PT1:00:10"] }));
  const findings = JSON.parse(ok[QA_STATE_FINDINGS_UID]) as QaFinding[];
  assert(findings.length === 1 && findings[0].state === "OPEN", "finding lands OPEN");
  assert(ok["QA-01-FLD-OPEN-FINDINGS"] === "1", "open finding counter updates");
}

{
  const inReview = context({ "QA-01-FLD-REVIEW-STATE": "IN_REVIEW" });
  const finding: QaFinding = { uid: "QA-FND-1", severity: "HIGH", category: "LIPSYNC_MISMATCH", scope: "VER-1", evidenceRefs: ["PT1"], state: "OPEN", createdAt: "t" };
  const seeded = new Map(inReview);
  seeded.set(QA_STATE_FINDINGS_UID, JSON.stringify([finding]));
  const noCause = run(seeded, "QA-01-ACT-CORRECTION-REQUEST", JSON.stringify({ rootCause: "VIBES" }));
  assert((JSON.parse(noCause["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-CORRECTION-001", "root cause must be canonical");
  const ok = run(seeded, "QA-01-ACT-CORRECTION-REQUEST", JSON.stringify({ rootCause: "PROVIDER_ROUTE", action: "REGENERATE", target: "EDIT-01", revalidate: ["REVIEW_EDIT"] }));
  const correction = JSON.parse(ok[QA_STATE_CORRECTION_UID]) as QaCorrectionState;
  assert(correction.status === "REQUESTED" && correction.failedVersion === "VER-1", "correction records the failed version");
  assert(ok["QA-01-FLD-REVIEW-STATE"] === "CORRECTION_REQUIRED", "correction flips the review state");

  const withoutNew = run(context({ "QA-01-FLD-REVIEW-STATE": "CORRECTION_REQUIRED" }), "QA-01-ACT-RECHECK-START");
  assert((JSON.parse(withoutNew["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-RECHECK-001", "recheck without verified new version is refused");
  const delivered = context({
    "QA-01-FLD-REVIEW-STATE": "CORRECTION_REQUIRED",
    [QA_STATE_CORRECTION_UID]: JSON.stringify({ requestUid: "QA-COR-1", failedVersion: "VER-1", newVersion: "VER-2", status: "UPSTREAM_DONE", findings: [], scorecards: [], instruction: "", scope: "", rootCause: "PROVIDER_ROUTE", action: "REGENERATE", target: "EDIT-01", revalidate: [], at: "t" }),
  });
  const recheck = run(delivered, "QA-01-ACT-RECHECK-START");
  assert(recheck["QA-01-FLD-RECHECK-STATUS"] === "RECHECK_IN_PROGRESS", "delivered new version enables recheck");
}

{
  const withoutCase = run(context(), "QA-01-ACT-MANUAL-MODIFY");
  assert((JSON.parse(withoutCase["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-MANUAL-ACTION-001", "manual actions require a governed case");
  const manual: QaManualState = {
    caseUid: "QA-MAN-1",
    state: "REQUIRED",
    blocker: "",
    owner: "EDIT-01",
    decision: "",
    required: true,
    history: [],
  };
  const withCase = context({ [QA_STATE_MANUAL_UID]: JSON.stringify(manual), "QA-01-FLD-REVIEW-STATE": "IN_REVIEW" });
  const modified = run(withCase, "QA-01-ACT-MANUAL-MODIFY", JSON.stringify({ note: "needs re-export" }));
  const manualState = JSON.parse(modified[QA_STATE_MANUAL_UID]) as QaManualState;
  assert(manualState.state === "OPEN" && manualState.history.length === 1, "manual modify records history");
  const passed = run(withCase, "QA-01-ACT-MANUAL-PASS", "{}");
  const closed = JSON.parse(passed[QA_STATE_MANUAL_UID]) as QaManualState;
  assert(closed.state === "CLOSED" && closed.decision === "PASS", "manual pass closes the case");
  assert(passed["QA-01-FLD-GATE-STATUS"] === "OPEN", "manual pass alone does not force the gate PASS");
}

{
  const refused = run(context(), "QA-01-ACT-RELEASE-CREATE");
  assert((JSON.parse(refused["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-RELEASE-001", "release without PASS scorecard is refused");
  const card = JSON.stringify({
    profileUid: "QCP-QA-FINAL-OUTPUT-V1",
    criteriaVersion: "CRIT-1",
    policyVersion: "QA-GATE-V1",
    threshold: 95,
    rows: [],
    total: 97,
    status: "PASS",
    origin: "SYSTEM_AI_GENERATED_FROM_BOUND_CRITERIA",
    at: "t",
    targetVersion: "VER-1",
  });
  const ready = context({ [QA_STATE_SCORECARD_UID]: card });
  const created = run(ready, "QA-01-ACT-RELEASE-CREATE");
  const release = JSON.parse(created[QA_STATE_RELEASE_UID]) as QaReleaseState;
  assert(release.status === "CREATED", "eligible release creates the canonical package");
  assert(release.readiness.rightsGate === true, "rights gate records the ledger entry");
  const again = run(ready, "QA-01-ACT-RELEASE-CREATE");
  const repeat = JSON.parse(again[QA_STATE_RELEASE_UID]) as QaReleaseState;
  assert(repeat.candidateUid === release.candidateUid, "repeat release returns the same candidate (idempotency)");
  assert(again["QA-01-FLD-REL-PACKAGE"] === release.candidateUid, "repeat echoes the package uid");
}

{
  const emptyQueue: QaQueueState = { filters: { state: "", severity: "", sourceDept: "" }, search: "", reviews: [], selected: "" };
  const blocked = context({ [QA_STATE_QUEUE_UID]: JSON.stringify(emptyQueue) });
  const refused = run(blocked, "QA-01-ACT-AUTO-START", "{}", "QA-01-BTN-AUTO-START");
  assert((JSON.parse(refused["QA-01-STATE-ERROR"]) as { code: string }).code === "QA-01-ERR-AUTO-001", "AUTO with empty queue is fail-closed");
  const queued = context({
    [QA_STATE_QUEUE_UID]: JSON.stringify({ ...emptyQueue, reviews: [{ taskUid: "qa-task-1", project: "P", topic: "T", sourceDept: "EDIT-01", severity: "", state: "PENDING" }] }),
  });
  const started = run(queued, "QA-01-ACT-AUTO-START", "{}", "QA-01-BTN-AUTO-START");
  assert(started["QA-01-FLD-AUTO-PROGRESS"] === "running", "AUTO flips the progress state");
}

console.log("qaActionPreview.test.ts: all assertions passed");
