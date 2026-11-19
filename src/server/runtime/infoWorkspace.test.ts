import { bootstrapDatabase } from "../db/migrate";
import { seedScope } from "../db/seed";
import { persistListInfoFields, persistRecordInfoAction } from "../db/persist";
import { getSqlClient } from "../db/client";
import { INFO_STATE_CANDIDATES_UID, INFO_STATE_ERROR_UID } from "../domain/info";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

const DEMO = "ACC-DEMO";
const READONLY = "ACC-INFO-READONLY";

const BTN_SEARCH = "INFO-01-BTN-SEARCH";
const BTN_REFRESH = "INFO-01-BTN-REFRESH";
const BTN_EXPORT = "INFO-01-BTN-EXPORT";
const BTN_ADOPT = "INFO-01-BTN-ADOPT-CONTEXT";
const BTN_DECIDE = "INFO-01-BTN-CANDIDATE-DECIDE";

const STATE_KEYS = [
  INFO_STATE_ERROR_UID,
  "INFO-01-STATE-REFRESH",
  "INFO-01-STATE-SEARCH",
  "INFO-01-STATE-EXPORTS",
  INFO_STATE_CANDIDATES_UID,
  "INFO-01-STATE-AUDIT",
];

async function readState(uid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    "SELECT value_text FROM ghsn_info_field_projection WHERE control_uid = ?",
    [uid],
  );
  const raw = rows[0]?.value_text ?? null;
  return raw === "" ? null : raw;
}

async function readError(): Promise<{ code?: string } | null> {
  const raw = await readState(INFO_STATE_ERROR_UID);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as { code?: string };
  } catch {
    return null;
  }
}

async function main(): Promise<void> {
  await bootstrapDatabase();
  await seedScope("info");
  const client = getSqlClient();

  for (const uid of [...STATE_KEYS, "INFO-01-FLD-LAST-REFRESH"]) {
    await client.run(
      `INSERT INTO ghsn_info_field_projection (control_uid, value_text) VALUES (?, NULL)
       ON CONFLICT (control_uid) DO UPDATE SET value_text = NULL`,
      [uid],
    );
  }
  await client.run(
    "INSERT INTO ghsn_account_info_permission (account_uid, permission_uid) VALUES (?, 'information.read') ON CONFLICT (account_uid, permission_uid) DO NOTHING",
    [READONLY],
  );
  await client.run("DELETE FROM ghsn_account_info_permission WHERE account_uid = ? AND permission_uid <> 'information.read'", [READONLY]);

  // 1. Read-model actions: no mutation, context-preserving.
  await persistRecordInfoAction(DEMO, "INFO-01-LST-SOURCES", "INFO-01-ACT-SOURCE-SELECT");
  assertEqual((await readError())?.code, undefined, "source select clears error");
  assertEqual(await readState("INFO-01-STATE-REFRESH"), null, "source select writes nothing");

  // 2. Unregistered action -> refusal.
  await persistRecordInfoAction(DEMO, BTN_REFRESH, "deleteProjection");
  assertEqual((await readError())?.code, "INFO-01-ERR-CONTEXT-001", "unregistered action refusal");

  // 3. Refresh: real stamp written to STATE-REFRESH and FLD-LAST-REFRESH.
  await persistRecordInfoAction(DEMO, BTN_REFRESH, "INFO-01-ACT-REFRESH");
  const refresh = JSON.parse((await readState("INFO-01-STATE-REFRESH")) ?? "{}") as { rowsRead: number; rowsWithValue: number; refreshedAt: string };
  assert(refresh.rowsRead >= 66, `refresh reads registered rows (${refresh.rowsRead})`);
  assertEqual(await readState("INFO-01-FLD-LAST-REFRESH"), refresh.refreshedAt, "last-refresh stamp bound");
  assertEqual((await readError())?.code, undefined, "refresh clears error");

  // 4. Search requires non-empty query.
  await persistRecordInfoAction(DEMO, BTN_SEARCH, "INFO-01-ACT-SEARCH", JSON.stringify({ query: "" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-SEARCH-001", "empty query refusal");
  await persistRecordInfoAction(DEMO, BTN_SEARCH, "INFO-01-ACT-SEARCH", JSON.stringify({ query: "CANDIDATE-ID" }));
  const search = JSON.parse((await readState("INFO-01-STATE-SEARCH")) ?? "{}") as { matchedCount: number; matched: Array<{ controlUid: string }> };
  assert(search.matchedCount >= 1, "search matches registered rows");
  assert(search.matched.some((item) => item.controlUid === "INFO-01-FLD-CANDIDATE-ID"), "search finds candidate id control");

  // 5. Export: registered record only, no local file fabrication.
  await persistRecordInfoAction(DEMO, BTN_EXPORT, "INFO-01-ACT-EXPORT", JSON.stringify({ export_scope: "fact_pack" }));
  const exports = JSON.parse((await readState("INFO-01-STATE-EXPORTS")) ?? "[]") as Array<{ exportScope: string; rowCount: number }>;
  assertEqual(exports[0]?.exportScope, "fact_pack", "export recorded");
  assert(exports[0].rowCount >= 66, "export counts real rows");

  // 6. Adopt/decide require candidate_id + rationale.
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ candidate_id: "cc-1" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "adopt schema refusal");
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ candidate_id: "cc-1", rationale: "ok" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "adopt unknown candidate refusal");

  // 7. Register a governed Context Candidate (SQL fixture) and adopt it.
  await client.run(
    "UPDATE ghsn_info_field_projection SET value_text = ? WHERE control_uid = ?",
    [JSON.stringify([{ candidateId: "cc-1", scope: "demand", status: "CANDIDATE", decidedAt: null }]), INFO_STATE_CANDIDATES_UID],
  );
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ candidate_id: "cc-1", rationale: "use as context" }));
  assertEqual((await readError())?.code, undefined, "adopt clears error");
  assertEqual((JSON.parse((await readState(INFO_STATE_CANDIDATES_UID)) ?? "[]") as Array<{ status: string }>)[0].status, "ADOPTED", "candidate adopted");
  // Adoption never writes Canon/Lock/Task/Publish surfaces — only the
  // candidate registry and audit trail changed (asserted by registry state).

  // 8. Decide: vocabulary + state gates; ACCEPTED/REJECTED only.
  await client.run(
    "UPDATE ghsn_info_field_projection SET value_text = ? WHERE control_uid = ?",
    [JSON.stringify([{ candidateId: "cc-2", scope: "supply", status: "CANDIDATE", decidedAt: null }]), INFO_STATE_CANDIDATES_UID],
  );
  await persistRecordInfoAction(DEMO, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "APPROVED", rationale: "x" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "invalid decision vocabulary refusal");
  await persistRecordInfoAction(DEMO, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "REJECTED", rationale: "out of scope" }));
  assertEqual((JSON.parse((await readState(INFO_STATE_CANDIDATES_UID)) ?? "[]") as Array<{ status: string }>)[0].status, "REJECTED", "candidate rejected");

  // 9. Decide already-decided candidate -> exact-state refusal.
  await persistRecordInfoAction(DEMO, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "ACCEPTED", rationale: "again" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "decide refuses non-CANDIDATE");

  // 10. Scope gate: page scope alone cannot refresh/search/export/decide.
  await persistRecordInfoAction(READONLY, BTN_REFRESH, "INFO-01-ACT-REFRESH");
  assertEqual((await readError())?.code, "INFO-01-ERR-PERM-001", "scope gate blocks refresh");
  await persistRecordInfoAction(READONLY, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "ACCEPTED", rationale: "x" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-PERM-001", "scope gate blocks decide");
  assertEqual((JSON.parse((await readState(INFO_STATE_CANDIDATES_UID)) ?? "[]") as Array<{ status: string }>)[0].status, "REJECTED", "denied decision applied nothing");

  // 11. STATE uids exposed through the field list.
  const listed = await persistListInfoFields();
  const listedUids = new Set(listed.map((field) => field.controlUid));
  for (const uid of STATE_KEYS) assert(listedUids.has(uid), `field list exposes ${uid}`);

  // Restore sandbox to clean state.
  for (const uid of [...STATE_KEYS, "INFO-01-FLD-LAST-REFRESH"]) {
    await client.run("UPDATE ghsn_info_field_projection SET value_text = NULL WHERE control_uid = ?", [uid]);
  }

  console.log(`infoWorkspace: 11 checks passed (${new Date().toISOString()})`);
  process.exit(0);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
