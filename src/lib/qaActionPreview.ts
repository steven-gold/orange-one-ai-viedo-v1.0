// Word QA-01 §8-14: server-authoritative action layer. Only EFFECTFUL
// mutations produce server writes; UI_LOCAL_EXACT/CLIENT actions (viewer
// transport, evidence capture drafts, queue filters, surface navigation,
// compare, read-only views) stay session-local and never touch the
// projection (§2747 invariant). Refusals name the contract error code.

import { exactName } from "./coreActionPreview";
import {
  QA_FINDING_CATEGORIES,
  QA_FINDING_SEVERITIES,
  QA_ROOT_CAUSES,
  QA_REVALIDATION_REQUIREMENTS,
  deriveQaScorecard,
  evaluateReleaseReadiness,
  type QaEvidenceInput,
} from "./qaCriteria";
import {
  QA_STATE_CORRECTION_UID,
  QA_STATE_ERROR_UID,
  QA_STATE_FINDINGS_UID,
  QA_STATE_GATE_UID,
  QA_STATE_MANUAL_UID,
  QA_STATE_RELEASE_UID,
  QA_STATE_SCORECARD_UID,
  QA_STATE_SURFACE_UID,
  type QaCorrectionState,
  type QaErrorState,
  type QaFinding,
  type QaManualState,
  type QaReleaseState,
  type QaScorecard,
} from "./qaState";

function named(value: string | null | undefined): string {
  return exactName(value);
}

function parseJson<T>(text: string | null, fallback: T): T {
  const raw = (text ?? "").trim();
  if (!raw.startsWith("{") && !raw.startsWith("[")) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function now(): string {
  return new Date().toISOString();
}

function fail(code: string, detail: string): Record<string, string> {
  const error: QaErrorState = { code, detail, at: now() };
  return { [QA_STATE_ERROR_UID]: JSON.stringify(error) };
}

// UI_LOCAL_EXACT/CLIENT actions per the word action matrix: these are
// registered so the runtime can ignore them cleanly (no projection write).
export const QA_UI_LOCAL_ACTIONS = new Set([
  "QA-01-ACT-VIEWER-PLAY",
  "QA-01-ACT-VIEWER-SEEK",
  "QA-01-ACT-VIEWER-PREV-FRAME",
  "QA-01-ACT-VIEWER-NEXT-FRAME",
  "QA-01-ACT-VIEWER-FULLSCREEN",
  "QA-01-ACT-VIEWER-VOLUME",
  "QA-01-ACT-QUEUE-SEARCH",
  "QA-01-ACT-QUEUE-FILTER",
  "QA-01-ACT-REVIEW-SELECT",
  "QA-01-ACT-REVIEW-MODE-SET",
  "QA-01-ACT-COMPARE-TOGGLE",
  "QA-01-ACT-MANUAL-VIEW",
  "QA-01-ACT-EVIDENCE-VIEW",
  "QA-01-ACT-EVIDENCE-POINT",
  "QA-01-ACT-EVIDENCE-RANGE-IN",
  "QA-01-ACT-EVIDENCE-RANGE-OUT",
  "QA-01-ACT-SCRIPT-VIEW",
  "QA-01-ACT-AUDIT-VIEW",
  "QA-01-ACT-FINDING-SELECT",
]);

function outputResolved(checksum: string, provenance: string, targetOutput: string): boolean {
  return Boolean(targetOutput && checksum && provenance);
}

function rightsValid(rights: string): boolean {
  return Boolean(rights) && rights !== "BLOCKED";
}

// Word §9 GATE-PASS: bound criteria/policy PASS + no hard block + blocking
// findings closed + required manual review closed + rights/policy valid.
function gatePassBlockers(
  scorecard: QaScorecard | null,
  findings: QaFinding[],
  manual: QaManualState | null,
  rights: string,
  policy: string,
): string[] {
  const blockers: string[] = [];
  if (scorecard?.status !== "PASS") blockers.push("SCORECARD_NOT_PASS");
  const openBlocking = findings.filter((row) => row.state === "OPEN" && (row.severity === "HIGH" || row.severity === "CRITICAL"));
  if (openBlocking.length) blockers.push(`BLOCKING_FINDINGS_OPEN:${openBlocking[0].uid}`);
  if (manual && (manual.state === "OPEN" || manual.state === "REQUIRED")) blockers.push("MANUAL_REVIEW_OPEN");
  if (!rightsValid(rights)) blockers.push("RIGHTS_INVALID");
  if (!policy) blockers.push("POLICY_MISSING");
  return blockers;
}

export function previewQaAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  if (QA_UI_LOCAL_ACTIONS.has(actionUid)) return {};

  const payload = parseJson<Record<string, unknown>>(nextValue ?? "{}", {});
  const project = named(current("QA-01-FLD-PROJECT"));
  const topic = named(current("QA-01-FLD-TOPIC"));
  const targetOutput = named(current("QA-01-FLD-TARGET-OUTPUT"));
  const qaScript = named(current("QA-01-FLD-QA-SCRIPT"));
  const scriptHash = named(current("QA-01-FLD-SCRIPT-HASH"));
  const criteriaVersion = named(current("QA-01-FLD-CRITERIA-VERSION"));
  const checksum = named(current("QA-01-FLD-CHECKSUM"));
  const provenance = named(current("QA-01-FLD-PROVENANCE"));
  const rights = named(current("QA-01-FLD-RIGHTS"));
  const policy = named(current("QA-01-FLD-POLICY"));
  const requiredChecks = named(current("QA-01-FLD-REQUIRED-CHECKS"));
  const reviewState = named(current("QA-01-FLD-REVIEW-STATE"));

  const findings = parseJson<QaFinding[]>(current(QA_STATE_FINDINGS_UID), []);
  const manual = parseJson<QaManualState>(current(QA_STATE_MANUAL_UID), null as unknown as QaManualState);
  const correction = parseJson<QaCorrectionState>(current(QA_STATE_CORRECTION_UID), null as unknown as QaCorrectionState);
  const scorecard = parseJson<QaScorecard>(current(QA_STATE_SCORECARD_UID), null as unknown as QaScorecard);

  const evidence: QaEvidenceInput = {
    project,
    topic,
    targetOutput,
    qaScript,
    scriptHash,
    criteriaVersion,
    checksum,
    provenance,
    rights,
    policy,
    requiredChecks,
    openFindings: findings,
    manualOpen: Boolean(manual?.state === "OPEN" || manual?.state === "REQUIRED"),
  };

  // Word §Gate-CONTEXT: without an exact context everything effectful blocks.
  if (!(project && topic && targetOutput && qaScript && criteriaVersion)) {
    return fail("QA-01-ERR-CONTEXT-001", "Project/Topic/QATask/TargetOutputVersion missing, stale or mismatched");
  }

  if (actionUid === "QA-01-ACT-START-REVIEW") {
    if (rights === "BLOCKED") return fail("QA-01-ERR-RIGHTS-001", "Rights/Policy invalid; HARD BLOCK cannot be overridden");
    // Review start also performs the SCORE_MUTATION the contract binds to an
    // active review: the system derives the scorecard from bound criteria.
    const card = deriveQaScorecard(evidence, targetOutput);
    return {
      "QA-01-FLD-REVIEW-STATE": "IN_REVIEW",
      "QA-01-FLD-QA-TASK": named(current("QA-01-FLD-QA-TASK")) || `${project} / ${topic}`,
      "QA-01-FLD-TOTAL-SCORE": String(card.total),
      [QA_STATE_SCORECARD_UID]: JSON.stringify(card),
      [QA_STATE_SURFACE_UID]: "REVIEW",
    };
  }

  if (actionUid === "QA-01-ACT-SCORECARD-SUBMIT") {
    if (!criteriaVersion) return fail("QA-01-ERR-CRITERIA-001", "QA CriteriaVersion/QualityGatePolicy missing or unapproved");
    if (!qaScript) return fail("QA-01-ERR-SCRIPT-001", "QAValidationScriptView missing; scoring blocked");
    if (!outputResolved(checksum, provenance, targetOutput)) return fail("QA-01-ERR-OUTPUT-001", "Output artifact/version/checksum/provenance invalid");
    const card = deriveQaScorecard(evidence, targetOutput);
    return {
      [QA_STATE_SCORECARD_UID]: JSON.stringify(card),
      "QA-01-FLD-TOTAL-SCORE": String(card.total),
      "QA-01-FLD-CRITERIA-VERSION": criteriaVersion,
      "QA-01-FLD-POLICY": policy || "QA-GATE-V1",
    };
  }

  if (actionUid === "QA-01-ACT-GATE-PASS" || actionUid === "QA-01-ACT-GATE-FAIL") {
    const decision = actionUid === "QA-01-ACT-GATE-PASS" ? "PASS" : "FAIL";
    if (decision === "FAIL") {
      if (reviewState !== "IN_REVIEW" && reviewState !== "RECHECK") {
        return fail("QA-01-ERR-GATE-001", "FAIL decision requires an active review or recheck");
      }
      if (!outputResolved(checksum, provenance, targetOutput)) {
        return fail("QA-01-ERR-GATE-001", "FAIL decision lacks sufficient exact evidence");
      }
      return {
        [QA_STATE_GATE_UID]: JSON.stringify({ status: "FAIL", decidedBy: "qa.gate.decide", at: now(), blockers: [], reason: "governed FAIL decision" }),
        "QA-01-FLD-GATE-STATUS": "FAIL",
        "QA-01-FLD-REVIEW-STATE": "CORRECTION_REQUIRED",
      };
    }
    const blockers = gatePassBlockers(scorecard, findings, manual, rights, policy);
    if (blockers.length) return fail("QA-01-ERR-GATE-001", `PASS prerequisites unmet: ${blockers.join(", ")}`);
    return {
      [QA_STATE_GATE_UID]: JSON.stringify({ status: "PASS", decidedBy: "qa.gate.decide", at: now(), blockers: [], reason: "bound criteria PASS" }),
      "QA-01-FLD-GATE-STATUS": "PASS",
      "QA-01-FLD-REVIEW-STATE": "GATE_PASS",
    };
  }

  if (actionUid === "QA-01-ACT-FINDING-CREATE") {
    if (reviewState !== "IN_REVIEW" && reviewState !== "RECHECK") {
      return fail("QA-01-ERR-FINDING-001", "Finding create requires an active QA review");
    }
    const severity = String(payload.severity ?? "").trim();
    const category = String(payload.category ?? "").trim();
    const scope = String(payload.scope ?? "").trim();
    const evidenceRefs = Array.isArray(payload.evidenceRefs) ? (payload.evidenceRefs as string[]).map(String) : [];
    if (!QA_FINDING_SEVERITIES.includes(severity as (typeof QA_FINDING_SEVERITIES)[number])) {
      return fail("QA-01-ERR-FINDING-001", `severity must be one of ${QA_FINDING_SEVERITIES.join("/")}`);
    }
    if (!QA_FINDING_CATEGORIES.includes(category as (typeof QA_FINDING_CATEGORIES)[number])) {
      return fail("QA-01-ERR-FINDING-001", "missing or unregistered category = BLOCK + REPORT_AUTHORITY_GAP");
    }
    const finding: QaFinding = {
      uid: `QA-FND-${Date.now().toString(36).toUpperCase()}`,
      severity,
      category,
      scope: scope || targetOutput,
      evidenceRefs,
      state: "OPEN",
      createdAt: now(),
    };
    const nextFindings = [...findings, finding];
    return {
      [QA_STATE_FINDINGS_UID]: JSON.stringify(nextFindings),
      "QA-01-FLD-OPEN-FINDINGS": String(nextFindings.filter((row) => row.state === "OPEN").length),
      "QA-01-FLD-REVIEW-STATE": "FINDING_OPEN",
    };
  }

  if (actionUid === "QA-01-ACT-CORRECTION-REQUEST") {
    const rootCause = String(payload.rootCause ?? "").trim();
    const action = String(payload.action ?? "").trim();
    const scope = String(payload.scope ?? "").trim();
    const target = String(payload.target ?? "").trim();
    const instruction = String(payload.instruction ?? "").trim();
    const revalidate = Array.isArray(payload.revalidate) ? (payload.revalidate as string[]).map(String) : [];
    const openFindings = findings.filter((row) => row.state === "OPEN");
    if (!openFindings.length && !scorecard) {
      return fail("QA-01-ERR-CORRECTION-001", "correction requires an open finding or a scorecard");
    }
    if (!targetOutput) {
      return fail("QA-01-ERR-CORRECTION-001", "correction lacks the failed version");
    }
    if (!QA_ROOT_CAUSES.includes(rootCause as (typeof QA_ROOT_CAUSES)[number])) {
      return fail("QA-01-ERR-CORRECTION-001", `root cause must be a canonical enum value (${QA_ROOT_CAUSES.join("/")})`);
    }
    if (!action || !target) {
      return fail("QA-01-ERR-CORRECTION-001", "correction lacks required action or original owner");
    }
    const invalidRevalidate = revalidate.filter((item) => !QA_REVALIDATION_REQUIREMENTS.includes(item as (typeof QA_REVALIDATION_REQUIREMENTS)[number]));
    if (invalidRevalidate.length) {
      return fail("QA-01-ERR-CORRECTION-001", `unregistered revalidation requirement: ${invalidRevalidate[0]}`);
    }
    const request: QaCorrectionState = {
      requestUid: `QA-COR-${Date.now().toString(36).toUpperCase()}`,
      status: "REQUESTED",
      findings: openFindings.map((row) => row.uid),
      scorecards: scorecard ? [scorecard.profileUid] : [],
      instruction,
      scope: scope || targetOutput,
      rootCause,
      action,
      target,
      revalidate,
      failedVersion: targetOutput,
      newVersion: "",
      at: now(),
    };
    return {
      [QA_STATE_CORRECTION_UID]: JSON.stringify(request),
      "QA-01-FLD-FAILED-VERSION": targetOutput,
      "QA-01-FLD-REVIEW-STATE": "CORRECTION_REQUIRED",
      "QA-01-FLD-RECHECK-STATUS": `root=${rootCause} owner=${target}`,
      "QA-01-FLD-DISABLED": target,
      "QA-01-FLD-REQUIRED-CHECKS": action,
    };
  }

  if (actionUid === "QA-01-ACT-RECHECK-START") {
    // Word §9 GATE-RECHECK + ERR-RECHECK-001: the new version must be a
    // verified upstream delivery recorded on the correction request, and it
    // must differ from the failed version.
    if (reviewState !== "CORRECTION_REQUIRED" && reviewState !== "RECHECK") {
      return fail("QA-01-ERR-RECHECK-001", "recheck requires CORRECTION_REQUIRED review state");
    }
    const failedVersion = correction?.failedVersion || targetOutput;
    const newVersion = String(correction?.newVersion ?? "").trim();
    if (!newVersion || newVersion === failedVersion) {
      return fail("QA-01-ERR-RECHECK-001", "new output absent or same as failed version; wait verified new exact version");
    }
    return {
      "QA-01-FLD-NEW-VERSION": newVersion,
      "QA-01-FLD-FAILED-VERSION": failedVersion,
      "QA-01-FLD-RECHECK-STATUS": "RECHECK_IN_PROGRESS",
      "QA-01-FLD-REVIEW-STATE": "RECHECK",
    };
  }

  if (actionUid === "QA-01-ACT-MANUAL-MODIFY" || actionUid === "QA-01-ACT-MANUAL-PASS") {
    if (!manual?.caseUid || !(manual.state === "REQUIRED" || manual.state === "OPEN")) {
      return fail("QA-01-ERR-MANUAL-ACTION-001", "governed ManualReviewCase required/open missing; do not invent the mutation");
    }
    const note = String(payload.note ?? "").trim();
    if (actionUid === "QA-01-ACT-MANUAL-MODIFY") {
      const next: QaManualState = {
        ...manual,
        state: "OPEN",
        blocker: note || manual.blocker,
        history: [...(manual.history ?? []), { at: now(), actor: "qa.gate.decide", action: "MODIFY", note }],
      };
      return {
        [QA_STATE_MANUAL_UID]: JSON.stringify(next),
        "QA-01-FLD-MANUAL-STATE": next.state,
        "QA-01-FLD-MANUAL-BLOCKER": next.blocker,
        "QA-01-FLD-MANUAL-DECISION": "MODIFY",
        "QA-01-FLD-MANUAL-OWNER": next.owner,
        "QA-01-FLD-MANUAL-CASE": next.caseUid,
        [QA_STATE_SURFACE_UID]: "MANUAL",
      };
    }
    // Manual PASS closes the manual requirement and re-evaluates the normal
    // QA gate; it is never a direct QA PASS.
    const closed: QaManualState = {
      ...manual,
      state: "CLOSED",
      decision: "PASS",
      history: [...(manual.history ?? []), { at: now(), actor: "qa.gate.decide", action: "PASS", note }],
    };
    const blockers = gatePassBlockers(scorecard, findings, closed, rights, policy);
    return {
      [QA_STATE_MANUAL_UID]: JSON.stringify(closed),
      "QA-01-FLD-MANUAL-STATE": "CLOSED",
      "QA-01-FLD-MANUAL-DECISION": "PASS",
      "QA-01-FLD-MANUAL-OWNER": closed.owner,
      "QA-01-FLD-MANUAL-CASE": closed.caseUid,
      "QA-01-FLD-GATE-STATUS": blockers.length ? "OPEN" : "PASS",
      ...(blockers.length
        ? {}
        : {
            [QA_STATE_GATE_UID]: JSON.stringify({ status: "PASS", decidedBy: "qa.gate.decide", at: now(), blockers: [], reason: "manual closed, gate re-evaluated" }),
            "QA-01-FLD-REVIEW-STATE": "GATE_PASS",
          }),
    };
  }

  if (actionUid === "QA-01-ACT-RELEASE-CREATE") {
    const channelRequired = payload.channelRequired === true;
    const channelRef = String(payload.channelRef ?? "").trim();
    const { ready: releaseReady, readiness, blockers } = evaluateReleaseReadiness(
      scorecard,
      findings,
      manual,
      rights,
      policy || "QA-GATE-V1",
      channelRequired,
      channelRef,
    );
    // Word §14: one QA review creates at most one canonical package; a
    // repeat with the same eligibility refs returns the same candidate.
    const idempotencyKey = `${scorecard?.targetVersion ?? targetOutput}:${criteriaVersion}`;
    if (scorecard?.status !== "PASS") {
      return fail("QA-01-ERR-RELEASE-001", "release requires an exact PASS scorecard for the bound output");
    }
    const existing = parseJson<QaReleaseState>(current(QA_STATE_RELEASE_UID), null as unknown as QaReleaseState);
    if (existing?.status === "CREATED" && existing.candidateUid === idempotencyKey) {
      return { [QA_STATE_RELEASE_UID]: JSON.stringify(existing), "QA-01-FLD-REL-PACKAGE": existing.candidateUid };
    }
    if (!releaseReady) {
      return fail("QA-01-ERR-RELEASE-001", `release candidate eligibility refs invalid: ${blockers.join(", ")}`);
    }
    const release: QaReleaseState = {
      status: "CREATED",
      candidateUid: idempotencyKey,
      at: now(),
      readiness: { ...readiness, rightsGate: rightsValid(rights) },
      blockers: [],
    };
    return {
      [QA_STATE_RELEASE_UID]: JSON.stringify(release),
      "QA-01-FLD-REL-OUTPUTS": targetOutput,
      "QA-01-FLD-REL-PACKAGE": idempotencyKey,
      "QA-01-FLD-REL-QA-GATE": "PASS",
      "QA-01-FLD-REL-FINDINGS": "closed",
      "QA-01-FLD-REL-MANUAL": "closed",
      "QA-01-FLD-REL-RIGHTS": rights || "valid",
      "QA-01-FLD-REL-POLICY": policy || "QA-GATE-V1",
      "QA-01-FLD-REL-CHANNEL": channelRequired ? channelRef || "n/a" : "not-required",
      "QA-01-FLD-REL-RIGHTS-GATE": "PASS",
    };
  }

  if (actionUid === "QA-01-ACT-AUTO-START") {
    // Orchestration runs server-side (runQaAuto): the preview only verifies
    // the queue has a next task and flips the state to RUNNING.
    const queue = parseJson<{ reviews?: Array<{ taskUid?: string }>; selected?: string }>(current("QA-01-STATE-QUEUE"), {});
    const reviews = queue.reviews ?? [];
    if (!reviews.length) {
      return fail("QA-01-ERR-AUTO-001", "AUTO cannot resolve the Topic QA queue; no reorder/create/skip");
    }
    return {
      [QA_STATE_SURFACE_UID]: "REVIEW",
      "QA-01-FLD-AUTO-PROGRESS": "running",
    };
  }

  if (actionUid === "QA-01-ACT-NOOP-VIEW") {
    const existing = named(current(controlUid));
    return existing ? { [controlUid]: existing } : {};
  }

  const inboundOnly = new Set([
    "QA-01-FLD-PROJECT",
    "QA-01-FLD-TOPIC",
    "QA-01-FLD-TARGET-OUTPUT",
    "QA-01-FLD-QA-SCRIPT",
    "QA-01-FLD-SCRIPT-HASH",
    "QA-01-FLD-CRITERIA-VERSION",
    "QA-01-FLD-CHECKSUM",
    "QA-01-FLD-RIGHTS",
    "QA-01-FLD-PROVENANCE",
  ]);
  if (inboundOnly.has(controlUid)) {
    const existing = named(current(controlUid));
    return existing ? { [controlUid]: existing } : {};
  }
  return {};
}
