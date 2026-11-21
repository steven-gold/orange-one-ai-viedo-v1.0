import { getSqlClient } from "../db/client";
import {
  INFO_ACTION_SCOPES,
  INFO_STATE_AUDIT_UID,
  INFO_STATE_CANDIDATES_UID,
  INFO_STATE_ERROR_UID,
  INFO_STATE_EXPORTS_UID,
  INFO_STATE_IDEMPOTENCY_UID,
  INFO_STATE_REFRESH_UID,
  INFO_STATE_SEARCH_UID,
} from "../domain/info";
import { INFO_CONTROL_ACTIONS } from "@/components/pages/infoControls";

// ACPOS INFO-01 FINAL_LOCKED_ENCODING · registered actions. Effectful ops:
// refreshProjection / searchProjection / exportProjection / adoptContextCandidate
// / decideCandidate. Truth rules: never fabricate source/export file; adoption
// records governed context only (no Canon/Lock/Task/Publish mutation);
// decision state event CANDIDATE->ACCEPTED|REJECTED.
const TABLE = "ghsn_info_field_projection";

interface InfoCandidate {
  candidateId: string;
  scope: string;
  status: "CANDIDATE" | "ACCEPTED" | "REJECTED" | "ADOPTED";
  decidedAt: string | null;
  version: number;
}

function err(code: string, detail: string, recovery: string): { code: string; detail: string; recovery: string; at: string } {
  return { code, detail, recovery, at: new Date().toISOString() };
}

async function readField(uid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(`SELECT value_text FROM ${TABLE} WHERE control_uid = ?`, [uid]);
  return rows[0]?.value_text === "" ? null : (rows[0]?.value_text ?? null);
}

async function writeField(uid: string, value: string | null): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ${TABLE} (control_uid, value_text) VALUES (?, ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [uid, value],
  );
}

async function writeError(error: ReturnType<typeof err>): Promise<void> {
  await writeField(INFO_STATE_ERROR_UID, JSON.stringify(error));
}

async function clearError(): Promise<void> {
  await writeField(INFO_STATE_ERROR_UID, null);
}

// INFO-01-OBJ-AUDIT required content: actor + operation/event +
// correlation/idempotency + scope + timestamp + result.
async function appendAudit(input: { actor: string; op: string; scope: string; key?: string; result: string; detail?: string }): Promise<void> {
  const existing = await readField(INFO_STATE_AUDIT_UID);
  const lines = existing ? existing.split("\n") : [];
  const entry = [new Date().toISOString(), `actor=${input.actor}`, `op=${input.op}`, `scope=${input.scope}`, input.key ? `key=${input.key}` : "key=-", `result=${input.result}`, input.detail ?? ""].filter(Boolean).join(" | ");
  lines.unshift(entry);
  await writeField(INFO_STATE_AUDIT_UID, lines.slice(0, 12).join("\n"));
}

async function readCandidates(): Promise<InfoCandidate[]> {
  const raw = await readField(INFO_STATE_CANDIDATES_UID);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as InfoCandidate[];
  } catch {
    return [];
  }
}

async function hasScope(accountUid: string | undefined, scope: string): Promise<boolean> {
  if (!accountUid) return false;
  const { seedScope } = await import("../db/seed");
  await seedScope("info");
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_info_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, scope],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

function parsePayload(nextValue: string | undefined): Record<string, unknown> | null {
  const raw = (nextValue ?? "").trim();
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

// Hard lock: Refresh/Search/Export/Adopt/Decide run through exact
// scope/version/correlation/idempotency gates (common_effectful_context).
const SIDE_EFFECT_OPERATIONS = new Set([
  "INFO-01-ACT-REFRESH",
  "INFO-01-ACT-SEARCH",
  "INFO-01-ACT-EXPORT",
  "INFO-01-ACT-ADOPT-CONTEXT",
  "INFO-01-ACT-CANDIDATE-DECIDE",
]);

type IdempotencyOutcome = "missing" | "replay" | "accepted";

async function checkIdempotency(actionUid: string, payload: Record<string, unknown>): Promise<IdempotencyOutcome> {
  const idempotencyKey = String(payload.idempotency_key ?? "").trim();
  if (!idempotencyKey) return "missing";
  const raw = await readField(INFO_STATE_IDEMPOTENCY_UID);
  const registry = raw ? ((JSON.parse(raw) as Record<string, string>) ?? {}) : {};
  const fingerprint = `${actionUid}:${idempotencyKey}`;
  if (registry[fingerprint]) return "replay";
  registry[fingerprint] = new Date().toISOString();
  const entries = Object.entries(registry);
  await writeField(INFO_STATE_IDEMPOTENCY_UID, JSON.stringify(Object.fromEntries(entries.slice(-50))));
  return "accepted";
}

export async function applyInfoAction(
  accountUid: string | undefined,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<void> {
  // Control binding gate: registered controls only; a known action fired
  // from an unknown control is still an authority gap (undefined_behavior).
  const boundAction = INFO_CONTROL_ACTIONS[controlUid];
  if (!boundAction || boundAction !== actionUid) {
    await writeError(err("INFO-01-ERR-UNDEFINED-001", `Unregistered control/action requested: ${controlUid}/${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
    return;
  }
  const requiredScope = INFO_ACTION_SCOPES[actionUid];
  if (!requiredScope) {
    await writeError(err("INFO-01-ERR-UNDEFINED-001", `Unregistered action requested: ${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
    return;
  }
  if (!(await hasScope(accountUid, requiredScope))) {
    await writeError(err("INFO-01-ERR-PERM-001", `${requiredScope} required for ${actionUid}`, "Hide/deny protected surface; never infer allow"));
    return;
  }

  switch (actionUid) {
    // In-memory / read-model actions: no mutation, preserve context.
    case "INFO-01-ACT-NOOP":
    case "INFO-01-ACT-FILTER":
    case "INFO-01-ACT-SOURCE-SELECT":
    case "INFO-01-ACT-ALERT-SELECT":
    case "INFO-01-ACT-FACTPACK-SELECT":
    case "INFO-01-ACT-FACT-TYPE":
    case "INFO-01-ACT-EVIDENCE-SELECT":
    case "INFO-01-ACT-RESEARCH-SELECT":
    case "INFO-01-ACT-CANDIDATE-SELECT":
    case "INFO-01-ACT-CITATION-OPEN":
    case "INFO-01-ACT-AUDIT-OPEN":
    case "INFO-01-ACT-PROJECTION-READ":
      await clearError();
      return;

    // POST /v1/projections/refresh · RefreshProjectionRequest · preserve page
    // context; write a real refresh stamp (source_health_rule: no manual mark).
    case "INFO-01-ACT-REFRESH": {
      const payload = parsePayload(nextValue);
      if (payload === null) {
        await writeError(err("INFO-01-ERR-CONTEXT-001", "RefreshProjectionRequest must be a JSON object", "BLOCK dependent panels; show actual server reason"));
        return;
      }
      const idem = await checkIdempotency(actionUid, payload);
      if (idem === "missing") {
        await writeError(err("INFO-01-ERR-CONTEXT-001", "refreshProjection requires idempotency_key per common_effectful_context", "Resend with idempotency key"));
        return;
      }
      if (idem === "replay") {
        await appendAudit({ actor: accountUid ?? "unknown", op: "REFRESH-REPLAY", scope: requiredScope, key: String(payload.idempotency_key), result: "IDEMPOTENT-REPLAY" });
        await clearError();
        return;
      }
      const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(`SELECT control_uid, value_text FROM ${TABLE}`);
      const withValue = rows.filter((row) => row.value_text !== null && row.value_text !== "").length;
      const refreshedAt = new Date().toISOString();
      await writeField(INFO_STATE_REFRESH_UID, JSON.stringify({ refreshedAt, rowsRead: rows.length, rowsWithValue: withValue }));
      await writeField("INFO-01-FLD-LAST-REFRESH", refreshedAt);
      // Header context fields (contract controls default "—" until first refresh).
      const priorVersion = Number((await readField("INFO-01-FLD-PROJECTION-VERSION")) ?? "0") || 0;
      await writeField("INFO-01-FLD-PROJECTION-VERSION", String(priorVersion + 1));
      const scopeRows = await getSqlClient().all<{ permission_uid: string }>("SELECT permission_uid FROM ghsn_account_info_permission WHERE account_uid = ?", [accountUid ?? ""]);
      await writeField("INFO-01-FLD-SCOPE", [...new Set(scopeRows.map((row) => row.permission_uid))].sort().join(","));
      await writeField("INFO-01-FLD-PAGE-STATE", withValue > 0 ? "READY" : "EMPTY");
      await appendAudit({ actor: accountUid ?? "unknown", op: "REFRESH", scope: requiredScope, key: String(payload.idempotency_key), result: "OK", detail: `${rows.length} rows · ${withValue} with value` });
      await clearError();
      return;
    }

    // POST /v1/search · SearchProjectionRequest {query} · authorized registered
    // projection rows only.
    case "INFO-01-ACT-SEARCH": {
      const payload = parsePayload(nextValue);
      const query = String(payload?.query ?? "").trim().toLowerCase();
      if (payload === null || !query) {
        await writeError(err("INFO-01-ERR-SEARCH-001", "SearchProjectionRequest requires a non-empty query", "Show registered error + retry eligibility"));
        return;
      }
      const idem = await checkIdempotency(actionUid, payload);
      if (idem === "missing") {
        await writeError(err("INFO-01-ERR-SEARCH-001", "searchProjection requires idempotency_key per common_effectful_context", "Show registered error + retry eligibility"));
        return;
      }
      if (idem === "replay") {
        await appendAudit({ actor: accountUid ?? "unknown", op: "SEARCH-REPLAY", scope: requiredScope, key: String(payload.idempotency_key), result: "IDEMPOTENT-REPLAY" });
        await clearError();
        return;
      }
      const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(`SELECT control_uid, value_text FROM ${TABLE}`);
      const matched = rows
        .filter((row) => row.control_uid.toLowerCase().includes(query) || (row.value_text ?? "").toLowerCase().includes(query))
        .map((row) => ({ controlUid: row.control_uid, hasValue: row.value_text !== null && row.value_text !== "" }));
      await writeField(INFO_STATE_SEARCH_UID, JSON.stringify({ query, matchedCount: matched.length, matched: matched.slice(0, 20), searchedAt: new Date().toISOString() }));
      await appendAudit({ actor: accountUid ?? "unknown", op: "SEARCH", scope: requiredScope, key: String(payload.idempotency_key), result: "OK", detail: `"${query}" → ${matched.length} rows` });
      await clearError();
      return;
    }

    // POST /v1/exports · ExportProjectionRequest · registered export record;
    // no local file fabrication.
    case "INFO-01-ACT-EXPORT": {
      const payload = parsePayload(nextValue);
      if (payload === null) {
        await writeError(err("INFO-01-ERR-EXPORT-001", "ExportProjectionRequest must be a JSON object", "Show registered error; no local file fabrication"));
        return;
      }
      // Exact ExportProjectionRequest additional_fields.
      const missing = ["projection_type", "scope_ref", "format"].filter((key) => !String(payload[key] ?? "").trim());
      if (missing.length > 0) {
        await writeError(err("INFO-01-ERR-EXPORT-001", `ExportProjectionRequest missing fields: ${missing.join(", ")}`, "Show registered error; no local file fabrication"));
        return;
      }
      const idem = await checkIdempotency(actionUid, payload);
      if (idem === "missing") {
        await writeError(err("INFO-01-ERR-EXPORT-001", "exportProjection requires idempotency_key per common_effectful_context", "Show registered error; no local file fabrication"));
        return;
      }
      if (idem === "replay") {
        await appendAudit({ actor: accountUid ?? "unknown", op: "EXPORT-REPLAY", scope: requiredScope, key: String(payload.idempotency_key), result: "IDEMPOTENT-REPLAY" });
        await clearError();
        return;
      }
      const rows = await getSqlClient().all<{ control_uid: string }>(`SELECT control_uid FROM ${TABLE}`);
      const raw = await readField(INFO_STATE_EXPORTS_UID);
      const exports = raw ? (JSON.parse(raw) as Array<Record<string, unknown>>) : [];
      const exportScope = `${payload.projection_type}/${payload.scope_ref}/${payload.format}`;
      exports.unshift({ exportId: `INFO-EXP-${Date.now()}`, projectionType: String(payload.projection_type), scopeRef: String(payload.scope_ref), format: String(payload.format), rowCount: rows.length, exportedAt: new Date().toISOString() });
      await writeField(INFO_STATE_EXPORTS_UID, JSON.stringify(exports.slice(0, 10)));
      await appendAudit({ actor: accountUid ?? "unknown", op: "EXPORT", scope: requiredScope, key: String(payload.idempotency_key), result: "OK", detail: `${exportScope} · ${rows.length} rows` });
      await clearError();
      return;
    }

    // POST /v1/context-candidates/{id}/adopt · AdoptContextCandidateRequest ·
    // CANDIDATE->ADOPTED; no direct Canon/Lock/Task/Publish mutation.
    case "INFO-01-ACT-ADOPT-CONTEXT": {
      const payload = parsePayload(nextValue);
      const missing = payload === null ? ["context_candidate_id", "decision_reason"] : ["context_candidate_id", "decision_reason"].filter((key) => !String(payload[key] ?? "").trim());
      if (payload === null || missing.length > 0) {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `AdoptContextCandidateRequest missing fields: ${missing.join(", ")}`, "BLOCK candidate action; preserve candidate projection"));
        return;
      }
      const idem = await checkIdempotency(actionUid, payload);
      if (idem === "missing") {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", "adoptContextCandidate requires idempotency_key per common_effectful_context", "BLOCK candidate action; resend with idempotency key"));
        return;
      }
      if (idem === "replay") {
        await appendAudit({ actor: accountUid ?? "unknown", op: "ADOPT-REPLAY", scope: requiredScope, key: String(payload.idempotency_key), result: "IDEMPOTENT-REPLAY" });
        await clearError();
        return;
      }
      const candidates = await readCandidates();
      const candidate = candidates.find((item) => item.candidateId === String(payload.context_candidate_id));
      if (!candidate) {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `No registered Context Candidate ${String(payload.context_candidate_id)}`, "BLOCK candidate action; preserve candidate projection"));
        return;
      }
      // server state/version gate: expected_version must match the
      // registered candidate version.
      const expectedVersion = String(payload.expected_version ?? "").trim();
      if (!expectedVersion || Number(expectedVersion) !== candidate.version) {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `Candidate ${candidate.candidateId} version mismatch: expected ${expectedVersion || "-"}, registered ${candidate.version}`, "Reload the exact candidate projection and resend expected_version"));
        return;
      }
      if (candidate.status !== "CANDIDATE") {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `Candidate ${candidate.candidateId} state ${candidate.status}; adoption requires CANDIDATE`, "Keep exact state"));
        return;
      }
      candidate.status = "ADOPTED";
      candidate.decidedAt = new Date().toISOString();
      await writeField(INFO_STATE_CANDIDATES_UID, JSON.stringify(candidates));
      await appendAudit({ actor: accountUid ?? "unknown", op: "ADOPT_CONTEXT", scope: requiredScope, key: String(payload.idempotency_key), result: "OK", detail: `${candidate.candidateId} · ADOPTED` });
      await clearError();
      return;
    }

    // POST /v1/candidates/{id}/decision · DecideCandidateRequest ·
    // CANDIDATE->ACCEPTED|REJECTED only.
    case "INFO-01-ACT-CANDIDATE-DECIDE": {
      const payload = parsePayload(nextValue);
      const missing = payload === null ? ["candidate_id", "decision"] : ["candidate_id", "decision"].filter((key) => !String(payload[key] ?? "").trim());
      if (payload === null || missing.length > 0) {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `DecideCandidateRequest missing fields: ${missing.join(", ")}`, "BLOCK candidate action; preserve candidate projection"));
        return;
      }
      const idem = await checkIdempotency(actionUid, payload);
      if (idem === "missing") {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", "decideCandidate requires idempotency_key per common_effectful_context", "BLOCK candidate action; resend with idempotency key"));
        return;
      }
      if (idem === "replay") {
        await appendAudit({ actor: accountUid ?? "unknown", op: "DECIDE-REPLAY", scope: requiredScope, key: String(payload.idempotency_key), result: "IDEMPOTENT-REPLAY" });
        await clearError();
        return;
      }
      const decision = String(payload.decision).toUpperCase();
      if (decision !== "ACCEPTED" && decision !== "REJECTED") {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `decision must be ACCEPTED or REJECTED; got ${decision}`, "Registered decision vocabulary only"));
        return;
      }
      const candidates = await readCandidates();
      const candidate = candidates.find((item) => item.candidateId === String(payload.candidate_id));
      if (!candidate) {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `No registered Candidate ${String(payload.candidate_id)}`, "BLOCK candidate action; preserve candidate projection"));
        return;
      }
      const expectedVersion = String(payload.expected_version ?? "").trim();
      if (!expectedVersion || Number(expectedVersion) !== candidate.version) {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `Candidate ${candidate.candidateId} version mismatch: expected ${expectedVersion || "-"}, registered ${candidate.version}`, "Reload the exact candidate projection and resend expected_version"));
        return;
      }
      if (candidate.status !== "CANDIDATE") {
        await writeError(err("INFO-01-ERR-CANDIDATE-001", `Candidate ${candidate.candidateId} state ${candidate.status}; decision requires CANDIDATE`, "Keep exact state"));
        return;
      }
      candidate.status = decision;
      candidate.decidedAt = new Date().toISOString();
      await writeField(INFO_STATE_CANDIDATES_UID, JSON.stringify(candidates));
      await appendAudit({ actor: accountUid ?? "unknown", op: "DECIDE", scope: requiredScope, key: String(payload.idempotency_key), result: "OK", detail: `${candidate.candidateId} · ${decision}` });
      await clearError();
      return;
    }

    default:
      await writeError(err("INFO-01-ERR-UNDEFINED-001", `Unregistered control/action requested: ${controlUid}/${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
      return;
  }
}
