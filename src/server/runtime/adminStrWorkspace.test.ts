import { bootstrapDatabase } from "../db/migrate";
import { seedScope } from "../db/seed";
import { persistListAdminStrFields, persistRecordAdminStrAction } from "../db/persist";
import { getSqlClient } from "../db/client";
import { ADMIN_STR_STATE_ERROR_UID, ADMIN_STR_STATE_RESOURCE_UID, ADMIN_STR_STATE_CANDIDATES_UID } from "../domain/adminStr";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

const DEMO = "ACC-DEMO";
const READONLY = "ACC-ADMINSTR-READONLY";

const ACT_SEARCH = "CTRL-ADMIN-STR-01-ACT-SEARCH";
const ACT_REFRESH = "CTRL-ADMIN-STR-01-ACT-REFRESH";
const ACT_CONFIGURE = "CTRL-ADMIN-STR-01-ACT-CONFIGURE";
const ACT_APPROVE = "CTRL-ADMIN-STR-01-ACT-APPROVE";
const ACT_EXPORT = "CTRL-ADMIN-STR-01-ACT-EXPORT";
const ACT_DRAFT = "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE";
const ACT_CREATE = "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE";
const ACT_COMPARE = "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE";
const ACT_DECIDE = "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE";
const ACT_ADOPT = "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT";

const STATE_KEYS = [
  ADMIN_STR_STATE_ERROR_UID,
  ADMIN_STR_STATE_RESOURCE_UID,
  "CTRL-ADMIN-STR-01-STATE-SEARCH",
  "CTRL-ADMIN-STR-01-STATE-REFRESH",
  "CTRL-ADMIN-STR-01-STATE-EXPORTS",
  "CTRL-ADMIN-STR-01-STATE-DRAFT",
  ADMIN_STR_STATE_CANDIDATES_UID,
  "CTRL-ADMIN-STR-01-STATE-COMPARE",
  "CTRL-ADMIN-STR-01-STATE-AUDIT",
];

async function readState(uid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    "SELECT value_text FROM ghsn_admin_str_field_projection WHERE control_uid = ?",
    [uid],
  );
  const raw = rows[0]?.value_text ?? null;
  return raw === "" ? null : raw;
}

async function readError(): Promise<{ code?: string; detail?: string } | null> {
  const raw = await readState(ADMIN_STR_STATE_ERROR_UID);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as { code?: string; detail?: string };
  } catch {
    return null;
  }
}

async function readCandidates(): Promise<Array<{ candidateId: string; status: string; title: string }>> {
  const raw = await readState(ADMIN_STR_STATE_CANDIDATES_UID);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as Array<{ candidateId: string; status: string; title: string }>;
  } catch {
    return [];
  }
}

const CONFIG_PAYLOAD = {
  resource_type: "intelligence_fact",
  resource_id: "fact-q4-demand",
  config_patch_json: JSON.stringify({ fact_scope: "demand", refresh: "weekly" }),
  reason: "Quarterly intelligence fact refresh",
};

async function main(): Promise<void> {
  await bootstrapDatabase();
  await seedScope("adminStr");
  const client = getSqlClient();

  for (const uid of STATE_KEYS) {
    await client.run(
      `INSERT INTO ghsn_admin_str_field_projection (control_uid, value_text) VALUES (?, NULL)
       ON CONFLICT (control_uid) DO UPDATE SET value_text = NULL`,
      [uid],
    );
  }
  await client.run(
    "INSERT INTO ghsn_account_admin_str_permission (account_uid, permission_uid) VALUES (?, 'strategy.administration.read') ON CONFLICT (account_uid, permission_uid) DO NOTHING",
    [READONLY],
  );
  await client.run("DELETE FROM ghsn_account_admin_str_permission WHERE account_uid = ? AND permission_uid <> 'strategy.administration.read'", [READONLY]);

  // 1. Unregistered operation -> DO_NOT_INFER refusal.
  await persistRecordAdminStrAction(DEMO, ACT_SEARCH, "deleteProjection");
  assertEqual((await readError())?.code, "ADMIN-STR-ERR-UNDEFINED", "unregistered operation");

  // 2. searchProjection: empty query matches all rows (real projection only).
  await persistRecordAdminStrAction(DEMO, ACT_SEARCH, "searchProjection", JSON.stringify({ query: "" }));
  assertEqual((await readError())?.code, undefined, "search clears error");
  const searchAll = JSON.parse((await readState("CTRL-ADMIN-STR-01-STATE-SEARCH")) ?? "{}") as { matchedCount: number };
  assert(searchAll.matchedCount >= 16, `search sees registered rows (${searchAll.matchedCount})`);

  // 3. searchProjection with query filters on control_uid/value (the search
  // state row legitimately matches itself; the view control must be included).
  await persistRecordAdminStrAction(DEMO, ACT_SEARCH, "searchProjection", JSON.stringify({ query: "VIEW-DECISION" }));
  const searchFiltered = JSON.parse((await readState("CTRL-ADMIN-STR-01-STATE-SEARCH")) ?? "{}") as { matchedCount: number; matched: Array<{ controlUid: string }> };
  assertEqual(searchFiltered.matchedCount, 2, "search filters by uid (control + self state row)");
  assert(searchFiltered.matched.some((item) => item.controlUid === "CTRL-ADMIN-STR-01-VIEW-DECISION"), "view control matched");
  assert((await readState("CTRL-ADMIN-STR-01-STATE-AUDIT"))?.includes("SEARCH"), "audit records search");

  // 4. refreshProjection: real stamp (rows read / with value).
  await persistRecordAdminStrAction(DEMO, ACT_REFRESH, "refreshProjection");
  const refresh = JSON.parse((await readState("CTRL-ADMIN-STR-01-STATE-REFRESH")) ?? "{}") as { rowsRead: number; rowsWithValue: number };
  assert(refresh.rowsRead >= 16, "refresh reads registered rows");
  assertEqual((await readError())?.code, undefined, "refresh clears error");

  // 5. exportProjection: registered audit record.
  await persistRecordAdminStrAction(DEMO, ACT_EXPORT, "exportProjection", JSON.stringify({ export_scope: "intelligence_fact" }));
  const exports = JSON.parse((await readState("CTRL-ADMIN-STR-01-STATE-EXPORTS")) ?? "[]") as Array<{ exportScope: string }>;
  assertEqual(exports[0]?.exportScope, "intelligence_fact", "export recorded");

  // 6. configure missing fields -> refusal.
  await persistRecordAdminStrAction(DEMO, ACT_CONFIGURE, "configureGovernedResource", JSON.stringify({ resource_type: "intelligence_fact" }));
  assertEqual((await readError())?.code, "ADMIN-STR-ERR-UNDEFINED", "configure schema refusal");

  // 7. configure invalid patch json -> refusal.
  await persistRecordAdminStrAction(DEMO, ACT_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, config_patch_json: "{bad" }));
  assertEqual((await readError())?.code, "ADMIN-STR-ERR-UNDEFINED", "configure patch json refusal");

  // 8. configure valid -> DRAFT v1.
  await persistRecordAdminStrAction(DEMO, ACT_CONFIGURE, "configureGovernedResource", JSON.stringify(CONFIG_PAYLOAD));
  const resourceV1 = JSON.parse((await readState(ADMIN_STR_STATE_RESOURCE_UID)) ?? "{}") as { version: number; status: string };
  assertEqual(resourceV1.status, "DRAFT", "configured DRAFT");
  assertEqual(resourceV1.version, 1, "first version");

  // 9. approve DRAFT -> exact-state refusal.
  await persistRecordAdminStrAction(DEMO, ACT_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "intelligence_fact", resource_id: "fact-q4-demand", rationale: "ok" }));
  assertEqual((await readError())?.code, "ADMIN-STR-ERR-STATE", "approve refuses DRAFT");
  assertEqual((JSON.parse((await readState(ADMIN_STR_STATE_RESOURCE_UID)) ?? "{}") as { status: string }).status, "DRAFT", "DRAFT preserved");

  // 10. version conflict gate (promote resource to REVIEW v2 directly).
  await client.run(
    "UPDATE ghsn_admin_str_field_projection SET value_text = ? WHERE control_uid = ?",
    [JSON.stringify({ resourceType: "intelligence_fact", resourceId: "fact-q4-demand", version: 2, status: "REVIEW", configPatch: "{}", updatedAt: new Date().toISOString() }), ADMIN_STR_STATE_RESOURCE_UID],
  );
  await persistRecordAdminStrAction(DEMO, ACT_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "intelligence_fact", resource_id: "fact-q4-demand", rationale: "ok", expected_resource_version: "1" }));
  assertEqual((await readError())?.code, "ADMIN-STR-ERR-VERSION", "approve version conflict");

  // 11. REVIEW + matching version -> APPROVED.
  await persistRecordAdminStrAction(DEMO, ACT_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "intelligence_fact", resource_id: "fact-q4-demand", rationale: "Release", expected_resource_version: "2" }));
  const approved = JSON.parse((await readState(ADMIN_STR_STATE_RESOURCE_UID)) ?? "{}") as { status: string; version: number };
  assertEqual(approved.status, "APPROVED", "review approved");
  assertEqual(approved.version, 3, "approval bumps version");

  // 12. saveDraft -> DRAFT_ONLY (playbook_rule: never a publish command).
  await persistRecordAdminStrAction(DEMO, ACT_DRAFT, "saveDraft", JSON.stringify({ draft_id: "pb-2026-11", playbook_content: "Escalation path" }));
  const draft = JSON.parse((await readState("CTRL-ADMIN-STR-01-STATE-DRAFT")) ?? "{}") as { version: number; publishState: string };
  assertEqual(draft.publishState, "DRAFT_ONLY", "draft stays DRAFT_ONLY");
  await persistRecordAdminStrAction(DEMO, ACT_DRAFT, "saveDraft", JSON.stringify({ draft_id: "pb-2026-11", playbook_content: "Escalation path v2" }));
  assertEqual((JSON.parse((await readState("CTRL-ADMIN-STR-01-STATE-DRAFT")) ?? "{}") as { version: number }).version, 2, "draft version bumps");

  // 13. createCandidate -> CANDIDATE status (candidate_rule).
  await persistRecordAdminStrAction(DEMO, ACT_CREATE, "createCandidate", JSON.stringify({ candidate_title: "Expand QA capacity", candidate_summary: "Add reviewer pool", source_opportunity: "opp-7" }));
  await persistRecordAdminStrAction(DEMO, ACT_CREATE, "createCandidate", JSON.stringify({ candidate_title: "Automate triage", candidate_summary: "Reduce manual triage", source_opportunity: "opp-8" }));
  const candidates = await readCandidates();
  assertEqual(candidates.length, 2, "two candidates registered");
  assertEqual(candidates[0].status, "CANDIDATE", "candidate stays CANDIDATE");

  // 14. compare with <2 -> refusal; with 2 -> factual comparison, no winner.
  await persistRecordAdminStrAction(DEMO, ACT_COMPARE, "compareCandidates", JSON.stringify({ candidate_ids: [candidates[0].candidateId] }));
  assertEqual((await readError())?.code, "ADMIN-STR-ERR-STATE", "compare requires 2 candidates");
  await persistRecordAdminStrAction(DEMO, ACT_COMPARE, "compareCandidates", JSON.stringify({ candidate_ids: [candidates[0].candidateId, candidates[1].candidateId] }));
  const comparison = JSON.parse((await readState("CTRL-ADMIN-STR-01-STATE-COMPARE")) ?? "{}") as { comparedCount: number; decision: string | null };
  assertEqual(comparison.comparedCount, 2, "comparison covers both candidates");
  assertEqual(comparison.decision, null, "comparison writes no decision");

  // 15. reject with rationale -> REJECTED; reject again -> state refusal.
  await persistRecordAdminStrAction(DEMO, ACT_DECIDE, "rejectStrategyCandidate", JSON.stringify({ candidate_id: candidates[0].candidateId, rationale: "out of scope" }));
  assertEqual((await readCandidates())[0].status, "REJECTED", "candidate rejected");
  await persistRecordAdminStrAction(DEMO, ACT_DECIDE, "rejectStrategyCandidate", JSON.stringify({ candidate_id: candidates[0].candidateId, rationale: "again" }));
  assertEqual((await readError())?.code, "ADMIN-STR-ERR-STATE", "reject refuses non-CANDIDATE");

  // 16. adopt context -> ADOPTED_AS_CONTEXT (decision_rule: no canon/task/budget/publish writes).
  await persistRecordAdminStrAction(DEMO, ACT_ADOPT, "adoptAsContextCandidate", JSON.stringify({ candidate_id: candidates[1].candidateId, rationale: "use as context" }));
  assertEqual((await readCandidates())[1].status, "ADOPTED_AS_CONTEXT", "candidate adopted as context");

  // 17. Scope gate: page scope alone cannot write.
  await persistRecordAdminStrAction(READONLY, ACT_CREATE, "createCandidate", JSON.stringify({ candidate_title: "x", candidate_summary: "y" }));
  assertEqual((await readError())?.code, "ADMIN-STR-ERR-AUTH", "scope gate blocks write");
  assertEqual((await readCandidates()).length, 2, "denied write applied nothing");

  // 18. STATE uids exposed through the field list.
  const listed = await persistListAdminStrFields();
  const listedUids = new Set(listed.map((field) => field.controlUid));
  for (const uid of STATE_KEYS) assert(listedUids.has(uid), `field list exposes ${uid}`);

  // Restore sandbox to clean state.
  for (const uid of STATE_KEYS) {
    await client.run("UPDATE ghsn_admin_str_field_projection SET value_text = NULL WHERE control_uid = ?", [uid]);
  }

  console.log(`adminStrWorkspace: 18 checks passed (${new Date().toISOString()})`);
  process.exit(0);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
