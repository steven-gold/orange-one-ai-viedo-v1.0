import type { CanonicalScriptProjection } from "./coreActionPreview";
import { parseBaseDna, type BaseDnaVersion } from "./dnaDocument";

export const QCP_CORE_PROFILE = "QCP-CORE-BASELINE-V1";
export const QCP_CORE_PASS_THRESHOLD = 95;

export type QcpDimension = {
  item: string;
  score: number;
  result: string;
  weight: number;
};

export type CoreScorecard = {
  kind: "CORE_EVALUATION";
  criteria_version: string;
  criteria_profile: string;
  pass_threshold: number;
  total_score: number;
  hard_block: string;
  evidence: Array<{ item: string; score: number; result: string }>;
  verdict: "pass" | "blocked";
};

function scoreRow(pass: boolean, value: string, item: string, weight: number): QcpDimension {
  return { item, score: pass ? 100 : 0, result: pass ? `pass:${value}` : `fail:${value}`, weight };
}

export function evaluateCoreCandidate(input: {
  candidate: string;
  projection: CanonicalScriptProjection | null | undefined;
  blueprint: string | null;
  dnaRaw: string | null;
  namingAuthority: string | null;
  at: string;
  note?: string;
}): CoreScorecard {  const projection = input.projection;
  const dnaDoc: BaseDnaVersion | undefined = parseBaseDna(input.dnaRaw);
  const dnaRef = dnaDoc?.version ?? input.dnaRaw;
  const boundary = projection?.structure?.boundary;
  const continuity = projection?.continuity;
  const sceneCount = projection?.structure?.scenes?.length ?? 0;
  const coverageGaps = projection?.coverage_gaps ?? [];
  const rows: QcpDimension[] = [
    scoreRow(Boolean(input.blueprint), input.blueprint || "missing", "goal_blueprint_intent", 12.5),
    scoreRow(sceneCount > 0, `scenes=${sceneCount}`, "logic_structure", 12.5),
    scoreRow(
      Boolean(dnaRef) && ["STORY", "CHARACTER"].every((name) => !dnaDoc?.missing[name]?.length),
      dnaRef || "missing",
      "character_dna_plan",
      12.5,
    ),
    scoreRow(
      Boolean(continuity?.starting_state && continuity?.ending_state),
      continuity ? `${continuity.starting_state}→${continuity.ending_state}` : "missing",
      "scene_continuity_plan",
      12.5,
    ),
    scoreRow(
      (projection?.views?.views ?? []).some((view) => view.items.length > 0),
      `views=${projection?.views?.views?.length ?? 0}`,
      "production_requirements",
      12.5,
    ),
    scoreRow(coverageGaps.length === 0, coverageGaps.length ? coverageGaps.join(";").slice(0, 60) : "no gaps", "ambiguity_control", 12.5),
    scoreRow(
      Boolean(projection?.audit?.human_decision && projection?.audit?.candidate_ref && projection?.dna_ref),
      `${projection?.audit?.human_decision ?? "none"}/${projection?.dna_ref ?? "none"}`,
      "evidence_provenance",
      12.5,
    ),
    scoreRow(Boolean(input.namingAuthority), input.namingAuthority || "missing", "rights_policy", 12.5),
  ];
  const total = rows.reduce((sum, row) => sum + row.score * (row.weight / 100), 0);
  const hardBlocked = !rows.find((row) => row.item === "rights_policy")!.result.startsWith("pass");
  return {
    kind: "CORE_EVALUATION",
    criteria_version: QCP_CORE_PROFILE,
    criteria_profile: QCP_CORE_PROFILE,
    pass_threshold: QCP_CORE_PASS_THRESHOLD,
    total_score: Math.round(total * 10) / 10,
    hard_block: hardBlocked ? "rights_policy" : "",
    evidence: rows.map((row) => ({ item: row.item, score: row.score, result: row.result })),
    verdict: !hardBlocked && total >= QCP_CORE_PASS_THRESHOLD ? "pass" : "blocked",
  };
}

export function markScorecardStale(
  evaluationRaw: string | null | undefined,
  priorVersion: string,
  nextVersion: string,
  at: string,
): string | null {
  try {
    const parsed = evaluationRaw ? (JSON.parse(evaluationRaw) as { kind?: unknown; scorecard_stale?: unknown } | null) : null;
    if (!parsed || parsed.kind !== "CORE_EVALUATION" || parsed.scorecard_stale === true) return null;
    return JSON.stringify({
      ...parsed,
      scorecard_stale: true,
      stale_reason: `canonical changed ${priorVersion}→${nextVersion}; resolve a fresh evaluation (QCP change impact)`,
      stale_at: at,
    });
  } catch {
    return null;
  }
}
