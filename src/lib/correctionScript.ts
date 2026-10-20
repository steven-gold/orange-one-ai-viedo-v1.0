export const CORRECTION_KIND = "CORRECTION_SCRIPT_CANDIDATE";

export type CorrectionDepartment = "ASSET" | "VIDEO" | "EDIT";
export type CorrectionCandidateStatus = "CANDIDATE" | "APPROVED" | "EXECUTED";

export type CorrectionScriptCandidate = {
  kind: typeof CORRECTION_KIND;
  candidate_id: string;
  status: CorrectionCandidateStatus;
  department: CorrectionDepartment;
  exact_source_version: string;
  target_scope: string;
  requested_delta: string;
  preserve_constraints: string;
  allowed_side_effects: string;
  acceptance_checks: string;
  fallback_policy: "BLOCK";
  reason: string;
  actor: string;
  expected_output_kind: string;
  script_body: string;
  hash: string;
};

const STATUS_SET = new Set<CorrectionCandidateStatus>(["CANDIDATE", "APPROVED", "EXECUTED"]);
const DEPARTMENT_SET = new Set<CorrectionDepartment>(["ASSET", "VIDEO", "EDIT"]);

function sourceHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function textOf(rec: Record<string, unknown>, key: string): string {
  return typeof rec[key] === "string" ? String(rec[key]).trim() : "";
}

export function parseCorrectionScript(raw: string | null | undefined): CorrectionScriptCandidate | undefined {
  if (!raw) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;
    const rec = parsed as Record<string, unknown>;
    if (rec.kind !== CORRECTION_KIND) return undefined;
    const status = textOf(rec, "status");
    const department = textOf(rec, "department");
    const candidateId = textOf(rec, "candidate_id");
    const source = textOf(rec, "exact_source_version");
    const delta = textOf(rec, "requested_delta");
    const hash = textOf(rec, "hash");
    if (!STATUS_SET.has(status as CorrectionCandidateStatus)) return undefined;
    if (!DEPARTMENT_SET.has(department as CorrectionDepartment)) return undefined;
    if (!candidateId || !source || !delta || !hash) return undefined;
    return {
      kind: CORRECTION_KIND,
      candidate_id: candidateId,
      status: status as CorrectionCandidateStatus,
      department: department as CorrectionDepartment,
      exact_source_version: source,
      target_scope: textOf(rec, "target_scope") || source,
      requested_delta: delta,
      preserve_constraints: textOf(rec, "preserve_constraints") || "未指明內容預設保留",
      allowed_side_effects: textOf(rec, "allowed_side_effects"),
      acceptance_checks: textOf(rec, "acceptance_checks"),
      fallback_policy: "BLOCK",
      reason: textOf(rec, "reason") || delta,
      actor: textOf(rec, "actor") || "人工",
      expected_output_kind: textOf(rec, "expected_output_kind"),
      script_body: textOf(rec, "script_body"),
      hash,
    };
  } catch {
    return undefined;
  }
}

export function serializeCorrectionScript(candidate: CorrectionScriptCandidate): string {
  return JSON.stringify(candidate);
}

export function buildCorrectionCandidate(input: {
  department: CorrectionDepartment;
  exact_source_version: string;
  target_scope: string;
  requested_delta: string;
  expected_output_kind: string;
}): CorrectionScriptCandidate | undefined {
  const source = input.exact_source_version.trim();
  const delta = input.requested_delta.trim();
  if (!source || !delta) return undefined;
  const scope = input.target_scope.trim() || source;
  const hash = sourceHash([input.department, source, scope, delta, input.expected_output_kind]);
  return {
    kind: CORRECTION_KIND,
    candidate_id: `CSC-${hash}`,
    status: "CANDIDATE",
    department: input.department,
    exact_source_version: source,
    target_scope: scope,
    requested_delta: delta.slice(0, 4000),
    preserve_constraints: "未指明內容預設保留",
    allowed_side_effects: "",
    acceptance_checks: "",
    fallback_policy: "BLOCK",
    reason: delta.slice(0, 4000),
    actor: "人工",
    expected_output_kind: input.expected_output_kind,
    script_body: "",
    hash,
  };
}

export function sourceMatches(candidate: CorrectionScriptCandidate | undefined, source: string): boolean {
  return Boolean(candidate && source && candidate.exact_source_version === source);
}

export function withCorrectionStatus(
  candidate: CorrectionScriptCandidate,
  status: CorrectionCandidateStatus,
): CorrectionScriptCandidate {
  return { ...candidate, status };
}

export function withCorrectionBody(
  candidate: CorrectionScriptCandidate,
  scriptBody: string,
): CorrectionScriptCandidate {
  return { ...candidate, script_body: scriptBody.trim().slice(0, 4000) };
}
