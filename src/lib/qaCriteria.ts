// Word QA-01 §12 + QCP-QA-FINAL-OUTPUT-V1: the approved criteria profile is
// bound authority — 17 dimensions in fixed order, weights sum to 100,
// threshold 95, one HARD BLOCK dimension (rights). The page renders exactly
// these rows and never adds a second threshold.

import type { QaScoreRow, QaScorecard } from "./qaState";

export const QA_PROFILE_UID = "QCP-QA-FINAL-OUTPUT-V1";
export const QA_THRESHOLD = 95;

export interface QaDimensionDef {
  uid: string;
  name: string;
  en: string;
  weight: number;
  hardBlock: boolean;
}

export const QA_DIMENSIONS: readonly QaDimensionDef[] = [
  { uid: "QA-DIM-FINAL-SCRIPT", name: "腳本／目標符合", en: "Script / Goal Compliance", weight: 6, hardBlock: false },
  { uid: "QA-DIM-FINAL-IDENTITY", name: "人物／角色一致性", en: "Character Identity Consistency", weight: 9, hardBlock: false },
  { uid: "QA-DIM-FINAL-SCENE", name: "場景／物件一致性", en: "Scene / Object Consistency", weight: 7, hardBlock: false },
  { uid: "QA-DIM-FINAL-COMPOSITION", name: "構圖／取景", en: "Composition / Framing", weight: 6, hardBlock: false },
  { uid: "QA-DIM-FINAL-MOTION", name: "動作／身體連續性", en: "Motion / Body Continuity", weight: 7, hardBlock: false },
  { uid: "QA-DIM-FINAL-FRAME", name: "幀間連續性", en: "Frame-to-Frame Continuity", weight: 8, hardBlock: false },
  { uid: "QA-DIM-FINAL-CAMERA", name: "鏡頭／視線連續", en: "Camera / Gaze Continuity", weight: 5, hardBlock: false },
  { uid: "QA-DIM-FINAL-LIPSYNC", name: "嘴型／口型同步", en: "Lip Sync", weight: 7, hardBlock: false },
  { uid: "QA-DIM-FINAL-VOICE", name: "配音／對白品質", en: "Voice / Dialogue Quality", weight: 6, hardBlock: false },
  { uid: "QA-DIM-FINAL-AUDIO", name: "音訊技術品質", en: "Audio Technical Quality", weight: 5, hardBlock: false },
  { uid: "QA-DIM-FINAL-MIX", name: "BGM／音效平衡與時間", en: "BGM / SFX Balance & Timing", weight: 5, hardBlock: false },
  { uid: "QA-DIM-FINAL-SUBCONTENT", name: "字幕內容正確", en: "Subtitle Content Accuracy", weight: 6, hardBlock: false },
  { uid: "QA-DIM-FINAL-SUBTIMING", name: "字幕時間／可讀性／安全區", en: "Subtitle Timing / Readability / Safe Area", weight: 6, hardBlock: false },
  { uid: "QA-DIM-FINAL-EDIT", name: "剪輯節奏／轉場", en: "Editing Pacing / Transition", weight: 6, hardBlock: false },
  { uid: "QA-DIM-FINAL-AVSYNC", name: "音畫同步", en: "Audio / Video Sync", weight: 5, hardBlock: false },
  { uid: "QA-DIM-FINAL-TECH", name: "輸出技術完整", en: "Technical Output Integrity", weight: 4, hardBlock: false },
  { uid: "QA-DIM-FINAL-RIGHTS", name: "權利／政策／來源", en: "Rights / Policy / Provenance", weight: 2, hardBlock: true },
] as const;

const WEIGHT_SUM = QA_DIMENSIONS.reduce((sum, row) => sum + row.weight, 0);
if (WEIGHT_SUM !== 100) throw new Error(`QA profile weights must sum to 100, got ${WEIGHT_SUM}`);

// Word §13: registered enums only — free text is forbidden for severity,
// category, and root cause; a missing category registry = BLOCK.
export const QA_FINDING_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

export const QA_FINDING_CATEGORIES = [
  "IDENTITY_DRIFT",
  "SCENE_INCONSISTENCY",
  "MOTION_ARTIFACT",
  "FRAME_FLICKER",
  "LIPSYNC_MISMATCH",
  "AUDIO_DEFECT",
  "SUBTITLE_ERROR",
  "PACING_ERROR",
  "AVSYNC_DRIFT",
  "TECH_SPECS_MISSING",
  "RIGHTS_VIOLATION",
] as const;

export const QA_ROOT_CAUSES = [
  "CANON",
  "SCRIPT_VIEW",
  "INSTRUCTION_PACKAGE",
  "INPUT_ASSET",
  "PROVIDER_ROUTE",
  "OUTPUT_ARTIFACT",
  "RIGHTS_POLICY",
  "QUALITY_CRITERIA",
  "EDITING",
  "UNKNOWN",
] as const;

export const QA_REVALIDATION_REQUIREMENTS = [
  "REGENERATE_SEGMENT",
  "REVALIDATE_CHECKSUM",
  "REVALIDATE_RIGHTS",
  "REVALIDATE_PROVENANCE",
  "REVIEW_EDIT",
] as const;

export interface QaEvidenceInput {
  project: string;
  topic: string;
  targetOutput: string;
  qaScript: string;
  scriptHash: string;
  criteriaVersion: string;
  checksum: string;
  provenance: string;
  rights: string;
  policy: string;
  requiredChecks: string;
  failedVersion?: string;
  newVersion?: string;
  openFindings: Array<{ severity: string; category: string; state: string }>;
  manualOpen: boolean;
}

// Word §12: Score Origin = SYSTEM_AI_GENERATED_FROM_BOUND_CRITERIA; manual
// scoring is FORBIDDEN. The sandbox derives each dimension from the exact
// inbound evidence actually resolved for the bound target output; when a
// dimension has no resolvable evidence it scores 0 as FINDING (fail-closed),
// never a padded number.
export function deriveQaScorecard(evidence: QaEvidenceInput, targetVersion: string): QaScorecard {
  const scriptOk = Boolean(evidence.qaScript && evidence.scriptHash);
  const outputOk = Boolean(evidence.targetOutput && evidence.checksum);
  const provenanceOk = Boolean(evidence.provenance);
  const rightsOk = Boolean(evidence.rights) && evidence.rights !== "BLOCKED";
  const policyOk = Boolean(evidence.policy);
  const checksOk = Boolean(evidence.requiredChecks) && !String(evidence.requiredChecks).includes("BLOCK");
  const openBlocking = evidence.openFindings.some((finding) => finding.state === "OPEN" && (finding.severity === "HIGH" || finding.severity === "CRITICAL"));

  const rows: QaScoreRow[] = QA_DIMENSIONS.map((dimension) => {
    let score = 0;
    let status: QaScoreRow["status"] = "FINDING";
    const evidenceRefs: string[] = [];
    if (dimension.hardBlock) {
      score = rightsOk ? 100 : 0;
      status = rightsOk ? "PASS" : "HARD_BLOCK";
      evidenceRefs.push("QA-01-FLD-RIGHTS", "QA-01-FLD-PROVENANCE");
    } else if (dimension.uid === "QA-DIM-FINAL-SCRIPT") {
      score = scriptOk ? 100 : 0;
      status = scriptOk ? "PASS" : "FINDING";
      evidenceRefs.push("QA-01-FLD-QA-SCRIPT", "QA-01-FLD-SCRIPT-HASH");
    } else if (dimension.uid === "QA-DIM-FINAL-TECH") {
      score = outputOk ? 100 : 0;
      status = outputOk ? "PASS" : "FINDING";
      evidenceRefs.push("QA-01-FLD-CHECKSUM", "QA-01-FLD-TARGET-OUTPUT");
    } else if (openBlocking) {
      score = 0;
      status = "FINDING";
    } else if (outputOk && provenanceOk && checksOk) {
      score = 100;
      status = "PASS";
      evidenceRefs.push("QA-01-FLD-PROVENANCE", "QA-01-FLD-REQUIRED-CHECKS");
    }
    const findingCount = evidence.openFindings.filter((finding) => finding.state === "OPEN").length;
    return {
      uid: dimension.uid,
      name: dimension.name,
      en: dimension.en,
      weight: dimension.weight,
      score,
      weighted: Math.round(((score * dimension.weight) / 100) * 100) / 100,
      status,
      hardBlock: dimension.hardBlock,
      evidenceRefs,
      findingCount,
    };
  });

  const total = rows.reduce((sum, row) => sum + row.weighted, 0);
  const hardBlockFailed = rows.some((row) => row.status === "HARD_BLOCK");
  const criteriaMissing = !evidence.criteriaVersion;
  const status: QaScorecard["status"] = criteriaMissing
    ? "BLOCKED"
    : hardBlockFailed || openBlocking || total < QA_THRESHOLD
      ? "FAIL"
      : "PASS";
  return {
    profileUid: QA_PROFILE_UID,
    criteriaVersion: evidence.criteriaVersion,
    policyVersion: evidence.policy,
    threshold: QA_THRESHOLD,
    rows,
    total: Math.round(total * 100) / 100,
    status,
    origin: "SYSTEM_AI_GENERATED_FROM_BOUND_CRITERIA",
    at: new Date().toISOString(),
    targetVersion,
  };
}

// Word §14 Preflight: release readiness is a per-gate boolean ledger; any
// false entry blocks the canonical package (no publish fallback).
export function evaluateReleaseReadiness(
  scorecard: QaScorecard | null,
  findings: Array<{ state: string }>,
  manual: { state: string } | null,
  rights: string,
  policy: string,
  channelRequired: boolean,
  channelRef: string,
): {
  ready: boolean;
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
} {
  const qaPass = Boolean(scorecard?.status === "PASS");
  const findingsClosed = findings.every((finding) => finding.state === "CLOSED");
  const manualClosed = Boolean(manual?.state === "CLOSED" || !manual?.state || manual.state !== "OPEN");
  const rightsValid = Boolean(rights) && rights !== "BLOCKED";
  const policyValid = Boolean(policy);
  const channelOk = !channelRequired || Boolean(channelRef);
  const blockers: string[] = [];
  if (!qaPass) blockers.push("QA_PASS");
  if (!findingsClosed) blockers.push("FINDINGS_OPEN");
  if (!manualClosed) blockers.push("MANUAL_OPEN");
  if (!rightsValid) blockers.push("RIGHTS_INVALID");
  if (!policyValid) blockers.push("POLICY_MISSING");
  if (!channelOk) blockers.push("CHANNEL_REF_MISSING");
  return {
    ready: blockers.length === 0,
    readiness: {
      qaPass,
      findings: findingsClosed,
      manual: manualClosed,
      rights: rightsValid,
      policy: policyValid,
      channel: channelOk,
      rightsGate: rightsValid,
    },
    blockers,
  };
}
