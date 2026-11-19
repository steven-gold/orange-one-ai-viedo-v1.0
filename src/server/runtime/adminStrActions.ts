import { getSqlClient } from "../db/client";
import {
  ADMIN_STR_ACTION_SCOPES,
  ADMIN_STR_STATE_AUDIT_UID,
  ADMIN_STR_STATE_CANDIDATES_UID,
  ADMIN_STR_STATE_COMPARE_UID,
  ADMIN_STR_STATE_DRAFT_UID,
  ADMIN_STR_STATE_ERROR_UID,
  ADMIN_STR_STATE_EXPORTS_UID,
  ADMIN_STR_STATE_REFRESH_UID,
  ADMIN_STR_STATE_RESOURCE_UID,
  ADMIN_STR_STATE_SEARCH_UID,
  ADMIN_STR_VISIBLE_CONTROLS,
} from "../domain/adminStr";

// ACPOS admin:STR-01 FINAL_LOCKED_ENCODING · operation_policy
// (known_operations_by_view, reuse_existing_operations, invent FORBIDDEN).
// data_and_truth_rules: candidate != approved decision; Decision Lab never
// writes canon lock/task/budget/publish; confidence never invented.
const TABLE = "ghsn_admin_str_field_projection";

interface AdminStrResource {
  resourceType: string;
  resourceId: string;
  version: number;
  status: "DRAFT" | "REVIEW" | "APPROVED";
  configPatch: string;
  updatedAt: string;
}

interface AdminStrCandidate {
  candidateId: string;
  title: string;
  summary: string;
  sourceOpportunity: string;
  status: "CANDIDATE" | "REJECTED" | "ADOPTED_AS_CONTEXT";
  createdAt: string;
  decidedAt: string | null;
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
  await writeField(ADMIN_STR_STATE_ERROR_UID, JSON.stringify(error));
}

async function clearError(): Promise<void> {
  await writeField(ADMIN_STR_STATE_ERROR_UID, null);
}

async function appendAudit(entry: string): Promise<void> {
  const existing = await readField(ADMIN_STR_STATE_AUDIT_UID);
  const lines = existing ? existing.split("\n") : [];
  lines.unshift(entry);
  await writeField(ADMIN_STR_STATE_AUDIT_UID, lines.slice(0, 12).join("\n"));
}

async function parseJson<T>(raw: string | null): Promise<T | null> {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

async function readCandidates(): Promise<AdminStrCandidate[]> {
  return (await parseJson<AdminStrCandidate[]>(await readField(ADMIN_STR_STATE_CANDIDATES_UID))) ?? [];
}

async function writeCandidates(candidates: AdminStrCandidate[]): Promise<void> {
  await writeField(ADMIN_STR_STATE_CANDIDATES_UID, JSON.stringify(candidates));
}

async function hasScope(accountUid: string | undefined, scope: string): Promise<boolean> {
  if (!accountUid) return false;
  const { seedScope } = await import("../db/seed");
  await seedScope("adminStr");
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_admin_str_permission WHERE account_uid = ? AND permission_uid = ?",
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

export async function applyAdminStrAction(
  accountUid: string | undefined,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<void> {
  const requiredScope = ADMIN_STR_ACTION_SCOPES[actionUid];
  if (!requiredScope) {
    await writeError(err("ADMIN-STR-ERR-UNDEFINED", `Unregistered operation requested: ${actionUid}`, "DO_NOT_INFER; resolve from registered operation registry or BLOCK"));
    return;
  }
  if (!(await hasScope(accountUid, requiredScope))) {
    await writeError(err("ADMIN-STR-ERR-AUTH", `${requiredScope} required for ${actionUid}`, "Hide/deny protected surface; never infer allow"));
    return;
  }

  switch (actionUid) {
    case "getUiProjection": {
      await clearError();
      return;
    }

    // OVERVIEW / INTELLIGENCE-FACT: search registered projection rows only
    // (real projection values; never synthesized rows).
    case "searchProjection": {
      const payload = parsePayload(nextValue);
      if (payload === null) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", "searchProjection payload must be a JSON object", "Use {\"query\": \"...\"}"));
        return;
      }
      const query = String(payload.query ?? "").trim().toLowerCase();
      const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(`SELECT control_uid, value_text FROM ${TABLE}`);
      const matched = rows
        .filter((row) => !query || row.control_uid.toLowerCase().includes(query) || (row.value_text ?? "").toLowerCase().includes(query))
        .map((row) => ({ controlUid: row.control_uid, hasValue: row.value_text !== null && row.value_text !== "" }));
      await writeField(ADMIN_STR_STATE_SEARCH_UID, JSON.stringify({ query, matchedCount: matched.length, matched: matched.slice(0, 20), searchedAt: new Date().toISOString() }));
      await appendAudit(`SEARCH "${query}" → ${matched.length} rows`);
      await clearError();
      return;
    }

    // OVERVIEW: refresh = recompute a real projection stamp (rows read /
    // with-value counts); no manual health marking (source_health_rule).
    case "refreshProjection": {
      const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(`SELECT control_uid, value_text FROM ${TABLE}`);
      const withValue = rows.filter((row) => row.value_text !== null && row.value_text !== "").length;
      await writeField(ADMIN_STR_STATE_REFRESH_UID, JSON.stringify({ refreshedAt: new Date().toISOString(), rowsRead: rows.length, rowsWithValue: withValue, registeredControls: ADMIN_STR_VISIBLE_CONTROLS.length }));
      await appendAudit(`REFRESH · ${rows.length} rows · ${withValue} with value`);
      await clearError();
      return;
    }

    // INTELLIGENCE-FACT: export = registered audit record of exported rows.
    case "exportProjection": {
      const payload = parsePayload(nextValue);
      const scope = String(payload?.export_scope ?? "full_projection");
      const rows = await getSqlClient().all<{ control_uid: string }>(`SELECT control_uid FROM ${TABLE}`);
      const exports = (await parseJson<Array<Record<string, unknown>>>(await readField(ADMIN_STR_STATE_EXPORTS_UID))) ?? [];
      exports.unshift({ exportId: `EXP-${Date.now()}`, exportScope: scope, rowCount: rows.length, exportedAt: new Date().toISOString() });
      await writeField(ADMIN_STR_STATE_EXPORTS_UID, JSON.stringify(exports.slice(0, 10)));
      await appendAudit(`EXPORT ${scope} · ${rows.length} rows`);
      await clearError();
      return;
    }

    // Exact governed-resource configure (same registered operation as SG-02);
    // DRAFT -> DRAFT with version bump.
    case "configureGovernedResource": {
      const payload = parsePayload(nextValue);
      const required = ["resource_type", "resource_id", "config_patch_json", "reason"];
      const missing = payload === null ? required : required.filter((key) => !String(payload[key] ?? "").trim());
      if (payload === null || missing.length > 0) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", `ConfigureGovernedResourceRequest missing fields: ${missing.join(", ")}`, "Complete the registered form schema"));
        return;
      }
      let configPatch = String(payload.config_patch_json);
      try {
        configPatch = JSON.stringify(JSON.parse(configPatch));
      } catch {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", "config_patch_json must be valid JSON", "Provide a JSON patch object"));
        return;
      }
      const existing = await parseJson<AdminStrResource>(await readField(ADMIN_STR_STATE_RESOURCE_UID));
      const sameResource = existing && existing.resourceType === String(payload.resource_type) && existing.resourceId === String(payload.resource_id);
      const resource: AdminStrResource = {
        resourceType: String(payload.resource_type),
        resourceId: String(payload.resource_id),
        version: sameResource ? existing.version + 1 : 1,
        status: "DRAFT",
        configPatch,
        updatedAt: new Date().toISOString(),
      };
      await writeField(ADMIN_STR_STATE_RESOURCE_UID, JSON.stringify(resource));
      await appendAudit(`CONFIGURE ${resource.resourceType}/${resource.resourceId} v${resource.version} · DRAFT`);
      await clearError();
      return;
    }

    // Exact governed-resource approve; REVIEW -> APPROVED only.
    case "approveGovernedResource": {
      const payload = parsePayload(nextValue);
      const missing = payload === null ? ["resource_type", "resource_id", "rationale"] : ["resource_type", "resource_id", "rationale"].filter((key) => !String(payload[key] ?? "").trim());
      if (payload === null || missing.length > 0) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", `ApproveGovernedResourceRequest missing fields: ${missing.join(", ")}`, "Complete the registered form schema"));
        return;
      }
      const resource = await parseJson<AdminStrResource>(await readField(ADMIN_STR_STATE_RESOURCE_UID));
      if (!resource || resource.resourceType !== String(payload.resource_type) || resource.resourceId !== String(payload.resource_id)) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", "No registered resource matches resource_type/resource_id", "Configure the governed resource first"));
        return;
      }
      const expected = String(payload.expected_resource_version ?? "").trim();
      if (expected && Number(expected) !== resource.version) {
        await writeError(err("ADMIN-STR-ERR-VERSION", `Expected resource version ${expected}, current ${resource.version}`, "Return VERSION_CONFLICT; reload exact projection"));
        return;
      }
      if (resource.status !== "REVIEW") {
        await writeError(err("ADMIN-STR-ERR-STATE", `Resource state ${resource.status}; approval requires REVIEW (REVIEW->APPROVED)`, "Keep exact state; the governed review flow must place the resource in REVIEW first"));
        return;
      }
      const next: AdminStrResource = { ...resource, status: "APPROVED", version: resource.version + 1, updatedAt: new Date().toISOString() };
      await writeField(ADMIN_STR_STATE_RESOURCE_UID, JSON.stringify(next));
      await appendAudit(`APPROVE ${next.resourceType}/${next.resourceId} v${next.version} · APPROVED`);
      await clearError();
      return;
    }

    // PLAYBOOK: draft persists to the strategy administration projection only
    // (playbook_rule: draft is never a direct publish command).
    case "saveDraft": {
      const payload = parsePayload(nextValue);
      const missing = payload === null ? ["draft_id", "playbook_content"] : ["draft_id", "playbook_content"].filter((key) => !String(payload[key] ?? "").trim());
      if (payload === null || missing.length > 0) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", `SaveDraftRequest missing fields: ${missing.join(", ")}`, "Complete draft_id and playbook_content"));
        return;
      }
      const previous = await parseJson<{ draftId: string; version: number }>(await readField(ADMIN_STR_STATE_DRAFT_UID));
      const draft = {
        draftId: String(payload.draft_id),
        playbookContent: String(payload.playbook_content),
        version: previous && previous.draftId === String(payload.draft_id) ? previous.version + 1 : 1,
        savedAt: new Date().toISOString(),
        publishState: "DRAFT_ONLY",
      };
      await writeField(ADMIN_STR_STATE_DRAFT_UID, JSON.stringify(draft));
      await appendAudit(`SAVE_DRAFT ${draft.draftId} v${draft.version} · DRAFT_ONLY`);
      await clearError();
      return;
    }

    // OPPORTUNITY: candidate creation stays CANDIDATE (candidate_rule).
    case "createCandidate": {
      const payload = parsePayload(nextValue);
      const missing = payload === null ? ["candidate_title", "candidate_summary"] : ["candidate_title", "candidate_summary"].filter((key) => !String(payload[key] ?? "").trim());
      if (payload === null || missing.length > 0) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", `CreateCandidateRequest missing fields: ${missing.join(", ")}`, "Complete candidate_title and candidate_summary"));
        return;
      }
      const candidates = await readCandidates();
      const candidate: AdminStrCandidate = {
        candidateId: `cand-${Date.now()}-${candidates.length + 1}`,
        title: String(payload.candidate_title),
        summary: String(payload.candidate_summary),
        sourceOpportunity: String(payload.source_opportunity ?? ""),
        status: "CANDIDATE",
        createdAt: new Date().toISOString(),
        decidedAt: null,
      };
      candidates.push(candidate);
      await writeCandidates(candidates);
      await appendAudit(`CREATE_CANDIDATE ${candidate.candidateId} · CANDIDATE`);
      await clearError();
      return;
    }

    // DECISION: comparison is factual side-by-side of registered candidates;
    // no invented score (confidence_rule), no winner write (decision_rule).
    case "compareCandidates": {
      const payload = parsePayload(nextValue);
      const requested = payload && Array.isArray(payload.candidate_ids) ? (payload.candidate_ids as string[]).map(String) : [];
      const candidates = await readCandidates();
      const selected = requested.length ? candidates.filter((candidate) => requested.includes(candidate.candidateId)) : candidates.filter((candidate) => candidate.status !== "REJECTED");
      if (selected.length < 2) {
        await writeError(err("ADMIN-STR-ERR-STATE", `compareCandidates requires at least 2 registered candidates; found ${selected.length}`, "Create candidates before comparing"));
        return;
      }
      await writeField(ADMIN_STR_STATE_COMPARE_UID, JSON.stringify({
        comparedAt: new Date().toISOString(),
        comparedCount: selected.length,
        candidates: selected.map((candidate) => ({ candidateId: candidate.candidateId, title: candidate.title, status: candidate.status, sourceOpportunity: candidate.sourceOpportunity })),
        decision: null,
      }));
      await appendAudit(`COMPARE ${selected.length} candidates`);
      await clearError();
      return;
    }

    // DECISION: reject with required rationale; exact-state preservation.
    case "rejectStrategyCandidate": {
      const payload = parsePayload(nextValue);
      const missing = payload === null ? ["candidate_id", "rationale"] : ["candidate_id", "rationale"].filter((key) => !String(payload[key] ?? "").trim());
      if (payload === null || missing.length > 0) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", `RejectStrategyCandidateRequest missing fields: ${missing.join(", ")}`, "Complete candidate_id and rationale"));
        return;
      }
      const candidates = await readCandidates();
      const candidate = candidates.find((item) => item.candidateId === String(payload.candidate_id));
      if (!candidate) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", `No registered candidate ${String(payload.candidate_id)}`, "Create the candidate first"));
        return;
      }
      if (candidate.status !== "CANDIDATE") {
        await writeError(err("ADMIN-STR-ERR-STATE", `Candidate ${candidate.candidateId} state ${candidate.status}; rejection requires CANDIDATE`, "Keep exact state"));
        return;
      }
      candidate.status = "REJECTED";
      candidate.decidedAt = new Date().toISOString();
      await writeCandidates(candidates);
      await appendAudit(`REJECT ${candidate.candidateId}`);
      await clearError();
      return;
    }

    // DECISION: adoption marks the candidate as context candidate only —
    // Decision Lab cannot write canon lock/task/budget/publish (decision_rule).
    case "adoptAsContextCandidate": {
      const payload = parsePayload(nextValue);
      const missing = payload === null ? ["candidate_id", "rationale"] : ["candidate_id", "rationale"].filter((key) => !String(payload[key] ?? "").trim());
      if (payload === null || missing.length > 0) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", `AdoptAsContextCandidateRequest missing fields: ${missing.join(", ")}`, "Complete candidate_id and rationale"));
        return;
      }
      const candidates = await readCandidates();
      const candidate = candidates.find((item) => item.candidateId === String(payload.candidate_id));
      if (!candidate) {
        await writeError(err("ADMIN-STR-ERR-UNDEFINED", `No registered candidate ${String(payload.candidate_id)}`, "Create the candidate first"));
        return;
      }
      if (candidate.status !== "CANDIDATE") {
        await writeError(err("ADMIN-STR-ERR-STATE", `Candidate ${candidate.candidateId} state ${candidate.status}; adoption requires CANDIDATE`, "Keep exact state"));
        return;
      }
      candidate.status = "ADOPTED_AS_CONTEXT";
      candidate.decidedAt = new Date().toISOString();
      await writeCandidates(candidates);
      await appendAudit(`ADOPT_CONTEXT ${candidate.candidateId} · ADOPTED_AS_CONTEXT`);
      await clearError();
      return;
    }

    default:
      await writeError(err("ADMIN-STR-ERR-UNDEFINED", `Unregistered control/action requested: ${controlUid}/${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
      return;
  }
}
