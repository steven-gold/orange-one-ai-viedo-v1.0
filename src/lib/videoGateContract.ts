import { nowStamp } from "./coreActionPreview";
import { QGP_POLICY_VERSION, resolveApprovedCriteria } from "./qcpRegistry";

export type VideoScoreDimension = {
  uid: string;
  label: string;
  weight: number;
  score: number | null;
  hard_block: boolean;
  evidence: string;
};

export type VideoScorecard = {
  kind: "VIDEO_SCORECARD";
  criteria_version: string;
  profile: "QCP-VIDEO-BASELINE-V1";
  quality_gate_policy_version: string;
  candidate_ref: string;
  dimensions: VideoScoreDimension[];
  weighted_total: number;
  overall: "PASS" | "BLOCKED" | "REVIEW_PENDING";
  issues: string[];
  evaluated_at: string;
};

type VideoDimensionSpec = { uid: string; label: string; weight: number; hard_block: boolean };

export const QCP_VIDEO_PROFILE: VideoDimensionSpec[] =
  resolveApprovedCriteria("QCP-VIDEO-BASELINE-V1")?.dimensions ?? [];

const REVIEW_PENDING = "評審待輸入";

function videoHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function videoHashOf(parts: string[]): string {
  return videoHash(parts);
}

export type VideoGateContext = {
  project: string | null;
  topic: string | null;
  blueprint: string | null;
  dna: string | null;
  script: string | null;
  assetVersion: string | null;
  layerComposite: string | null;
  checksum: string | null;
  rights: string | null;
  outputVersion: string | null;
  candidateVersion: string | null;
  confirmed: string | null;
  locked: string | null;
  handoff: string | null;
  executing: string | null;
  correctionOpen: string | null;
  scorecard: VideoScorecard | null;
  manifest: VideoHandoffManifest | null;
};

export function parseVideoScorecard(raw: string | null | undefined): VideoScorecard | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as VideoScorecard;
    return parsed?.kind === "VIDEO_SCORECARD" && Array.isArray(parsed.dimensions) ? parsed : null;
  } catch {
    return null;
  }
}

export type VideoHandoffManifest = {
  kind: "EXACT_VIDEO_HANDOFF_MANIFEST";
  manifest_id: string;
  video_version: string;
  shot_versions: string[];
  layer_versions: string[];
  script_hash: string;
  asset_fingerprint: string;
  output_uri: string;
  checksum: string;
  scorecard: string;
  evidence: string;
  handoff_contract: string;
};

export function parseVideoHandoffManifest(raw: string | null | undefined): VideoHandoffManifest | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as VideoHandoffManifest;
    return parsed?.kind === "EXACT_VIDEO_HANDOFF_MANIFEST" ? parsed : null;
  } catch {
    return null;
  }
}

export type VideoQaScoreInput = { uid: string; score: number; evidence?: string };

// Merge reviewer (LLM QA) scores into a scorecard and re-aggregate honestly:
// unscored dimensions stay null, totals/overall are recomputed from evidence.
export function applyVideoQaScores(card: VideoScorecard, scores: VideoQaScoreInput[]): VideoScorecard {
  const dimensions = card.dimensions.map((row) => {
    if (row.score !== null) return row;
    const hit = scores.find((item) => item.uid === row.uid);
    if (!hit || !Number.isFinite(hit.score)) return row;
    const score = Math.max(0, Math.min(100, Math.round(hit.score)));
    return { ...row, score, evidence: hit.evidence?.trim().slice(0, 140) || "QA 評審評分" };
  });
  const issues = dimensions.filter((row) => row.score === 0).map((row) => `${row.uid}: ${row.hard_block ? row.evidence : `${row.label} — ${row.evidence}`}`);
  const scored = dimensions.filter((row) => typeof row.score === "number");
  const weightedTotal = Math.round(scored.reduce((sum, row) => sum + ((row.score as number) * row.weight) / 100, 0));
  const hardBlockFailed = dimensions.some((row) => row.hard_block && row.score === 0);
  const pendingDims = dimensions.filter((row) => row.score === null).map((row) => row.uid);
  const allScored = pendingDims.length === 0;
  const nextIssues = [...issues];
  if (allScored && weightedTotal < 95 && !hardBlockFailed) {
    nextIssues.push(`QA-WEIGHTED-TOTAL: ${weightedTotal} < 95`);
  }
  return {
    ...card,
    dimensions,
    weighted_total: weightedTotal,
    overall: hardBlockFailed ? "BLOCKED" : allScored ? (weightedTotal >= 95 ? "PASS" : "BLOCKED") : "REVIEW_PENDING",
    issues: nextIssues,
  };
}

export function buildVideoScorecard(ctx: VideoGateContext, at = nowStamp()): VideoScorecard | null {
  const candidateRef = ctx.outputVersion || ctx.candidateVersion;
  if (!candidateRef) return null;
  const upstreamOk = Boolean(ctx.project && ctx.topic && ctx.blueprint && ctx.dna && ctx.script);
  const scriptEvidence = `${upstreamOk ? "PASS" : "FAIL"}: ${ctx.blueprint || "BP?"} / ${ctx.dna || "DNA?"} / ${ctx.script || "CS?"}`;
  const assetOk = Boolean(ctx.assetVersion);
  const assetEvidence = assetOk ? `asset version ${ctx.assetVersion}` : "exact asset version binding absent";
  const dimensions: VideoScoreDimension[] = QCP_VIDEO_PROFILE.map((spec) => {
    if (spec.hard_block) {
      return { uid: spec.uid, label: spec.label, weight: spec.weight, score: ctx.rights ? 100 : 0, hard_block: true, evidence: ctx.rights ? ctx.rights : "rights basis not resolved" };
    }
    if (spec.uid === "QA-DIM-VIDEO-SCRIPT") {
      return { uid: spec.uid, label: spec.label, weight: spec.weight, score: upstreamOk ? 100 : 0, hard_block: false, evidence: scriptEvidence };
    }
    if (spec.uid === "QA-DIM-VIDEO-ASSET") {
      return { uid: spec.uid, label: spec.label, weight: spec.weight, score: assetOk ? 100 : 0, hard_block: false, evidence: assetEvidence };
    }
    if (spec.uid === "QA-DIM-VIDEO-TECH") {
      return { uid: spec.uid, label: spec.label, weight: spec.weight, score: ctx.checksum ? 100 : null, hard_block: false, evidence: ctx.checksum ? `checksum ${ctx.checksum}` : "checksum pending lock" };
    }
    return { uid: spec.uid, label: spec.label, weight: spec.weight, score: null, hard_block: false, evidence: REVIEW_PENDING };
  });
  const issues = dimensions.filter((row) => row.score === 0).map((row) => `${row.uid}: ${row.hard_block ? row.evidence : `${row.label} — ${row.evidence}`}`);
  const scored = dimensions.filter((row) => typeof row.score === "number");
  const weightedTotal = Math.round(scored.reduce((sum, row) => sum + ((row.score as number) * row.weight) / 100, 0));
  const hardBlockFailed = dimensions.some((row) => row.hard_block && row.score === 0);
  const pendingDims = dimensions.filter((row) => row.score === null).map((row) => row.uid);
  const allScored = pendingDims.length === 0;
  if (allScored && weightedTotal < 95 && !hardBlockFailed) {
    issues.push(`QA-WEIGHTED-TOTAL: ${weightedTotal} < 95`);
  }
  return {
    kind: "VIDEO_SCORECARD",
    criteria_version: `VIDEO-CRITERIA-${videoHash([ctx.project ?? "", ctx.topic ?? "", ctx.script ?? ""])}`,
    profile: "QCP-VIDEO-BASELINE-V1",
    quality_gate_policy_version: QGP_POLICY_VERSION,
    candidate_ref: candidateRef,
    dimensions,
    weighted_total: weightedTotal,
    overall: hardBlockFailed ? "BLOCKED" : allScored ? (weightedTotal >= 95 ? "PASS" : "BLOCKED") : "REVIEW_PENDING",
    issues,
    evaluated_at: at,
  };
}

export type VideoGateState = { gate: string; state: "PASS" | "BLOCK"; reason: string };

export function buildVideoGates(ctx: VideoGateContext): VideoGateState[] {
  const state = (gate: string, ok: boolean, reason: string): VideoGateState => ({ gate, state: ok ? "PASS" : "BLOCK", reason });
  const ready = Boolean(ctx.project && ctx.topic && ctx.blueprint && ctx.dna && ctx.script);
  const candidate = Boolean(ctx.outputVersion || ctx.candidateVersion);
  const evaluatedPass = ctx.scorecard?.overall === "PASS";
  const scorecardOverall = ctx.scorecard?.overall;
  const gatePendingDims = (ctx.scorecard?.dimensions ?? []).filter((row) => row.score === null).map((row) => row.uid);
  const lockComplete = Boolean(ctx.checksum && ctx.outputVersion);
  const handoffComplete = Boolean(ctx.manifest && ctx.locked === "locked");
  return [
    state("VIDEO-01-GATE-PAGE", true, "workspace loaded"),
    state("VIDEO-01-GATE-CHILD-LOCK", Boolean(ctx.blueprint), ctx.blueprint ? `blueprint binding ${ctx.blueprint}` : "locked blueprint binding required"),
    state("VIDEO-01-GATE-SCRIPT", Boolean(ctx.script), ctx.script || "canonical script section required"),
    state("VIDEO-01-GATE-ASSET-BIND", Boolean(ctx.assetVersion), ctx.assetVersion ? `asset version ${ctx.assetVersion}` : "exact asset version from ASSET handoff required"),
    state("VIDEO-01-GATE-TASK-READY", ready && Boolean(ctx.assetVersion), ready ? (ctx.assetVersion ? "task inputs resolved" : "asset binding missing") : "project/topic/blueprint/DNA/script required"),
    state("VIDEO-01-GATE-EXECUTE", ready && Boolean(ctx.assetVersion), ready ? "inputs resolved" : "upstream context/asset binding required"),
    state("VIDEO-01-GATE-CANDIDATE", candidate, candidate ? (ctx.outputVersion || ctx.candidateVersion || "candidate") : "no candidate output"),
    state("VIDEO-01-GATE-EVALUATION", Boolean(ctx.scorecard), ctx.scorecard ? `scorecard ${ctx.scorecard.overall}` : "evaluation pending"),
    state("VIDEO-01-GATE-CONFIRM", evaluatedPass && ctx.confirmed !== "confirmed", scorecardOverall === "REVIEW_PENDING" ? `reviewer scores pending: ${gatePendingDims.join(", ")}` : evaluatedPass ? "ready to confirm" : "evaluation must PASS per bound criteria"),
    state("VIDEO-01-GATE-CORRECTION", ctx.correctionOpen === "open", ctx.correctionOpen === "open" ? "correction open" : "correction not opened"),
    state("VIDEO-01-GATE-LOCK", ctx.confirmed === "confirmed" && ctx.locked !== "locked" && lockComplete, ctx.confirmed === "confirmed" ? (lockComplete ? "ready to lock exact version" : "checksum/output version missing") : "confirmation required"),
    state("VIDEO-01-GATE-HANDOFF", handoffComplete, ctx.locked === "locked" ? (handoffComplete ? "handoff manifest complete" : "handoff manifest incomplete") : "lock exact version first"),
    state("VIDEO-01-GATE-RETRY", false, "no failed provider job"),
  ];
}

export function deriveVideoPageState(ctx: VideoGateContext): string {
  if (ctx.handoff === "sent") return "HANDOFF";
  if (ctx.locked === "locked") return "LOCKED";
  if (ctx.confirmed === "confirmed") return "CONFIRMED";
  if (ctx.correctionOpen === "open") return "CORRECTION_REQUIRED";
  if (ctx.scorecard && ctx.confirmed !== "confirmed") {
    return ctx.scorecard.overall === "PASS" || ctx.scorecard.overall === "REVIEW_PENDING" ? "WAIT_CONFIRMATION" : "ERROR";
  }
  if (ctx.executing === "running" && !ctx.candidateVersion && !ctx.outputVersion) return "EXECUTING";
  if (ctx.candidateVersion || ctx.outputVersion) return "CANDIDATE_OUTPUT";
  if (ctx.project && ctx.topic && ctx.blueprint && ctx.dna && ctx.script) return "READY";
  return "LOADING";
}

export function videoGateContextFrom(current: (uid: string) => string | null): VideoGateContext {
  const val = (uid: string): string | null => {
    const text = current(uid);
    return text && text.trim() ? text.trim() : null;
  };
  const named = (uid: string): string | null => {
    const text = val(uid);
    return text && text !== "—" && text !== "null" ? text : null;
  };
  return {
    project: named("VIDEO-01-FLD-PROJECT"),
    topic: named("VIDEO-01-FLD-TOPIC"),
    blueprint: named("VIDEO-01-FLD-BLUEPRINT-REF"),
    dna: named("VIDEO-01-FLD-DNA-REFS"),
    script: named("VIDEO-01-FLD-SCRIPT-SECTION"),
    assetVersion: named("VIDEO-01-FLD-ASSET-REFS"),
    layerComposite: named("VIDEO-01-FLD-LAYER-VERSIONS"),
    checksum: named("VIDEO-01-FLD-CHECKSUM"),
    rights: named("VIDEO-01-FLD-RIGHTS"),
    outputVersion: named("VIDEO-01-FLD-VIDEO-VERSION"),
    candidateVersion: named("VIDEO-01-FLD-CANDIDATE-VERSION"),
    confirmed: val("VIDEO-01-BTN-CONFIRM"),
    locked: val("VIDEO-01-BTN-LOCK"),
    handoff: val("VIDEO-01-BTN-HANDOFF"),
    executing: val("VIDEO-01-BTN-EXECUTE"),
    correctionOpen: val("VIDEO-01-BTN-MODIFY"),
    scorecard: parseVideoScorecard(current("VIDEO-01-FLD-SCORECARD")),
    manifest: parseVideoHandoffManifest(current("VIDEO-01-FLD-HANDOFF-CONTRACT")),
  };
}
