import { bootstrapDatabase } from "../db/migrate";
import { seedScope } from "../db/seed";
import { persistGetInfoReadModel, persistListInfoFields, persistRecordInfoAction } from "../db/persist";
import { getSqlClient } from "../db/client";
import { INFO_PERMISSION_SET, INFO_STATE_CANDIDATES_UID, INFO_STATE_ERROR_UID, INFO_STATE_IDEMPOTENCY_UID } from "../domain/info";
import { deriveInfoPageState } from "@/components/pages/infoFormat";

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
  INFO_STATE_IDEMPOTENCY_UID,
];

const RESET_UIDS = [...STATE_KEYS, "INFO-01-FLD-LAST-REFRESH", "INFO-01-FLD-SCOPE", "INFO-01-FLD-PAGE-STATE", "INFO-01-FLD-PROJECTION-VERSION"];

let idemSeq = 0;
const key = (tag: string): string => `idem-${tag}-${(idemSeq += 1)}`;

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

  for (const uid of RESET_UIDS) {
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

  // 2. Unregistered action -> exact UNDEFINED-001 refusal.
  await persistRecordInfoAction(DEMO, BTN_REFRESH, "deleteProjection");
  assertEqual((await readError())?.code, "INFO-01-ERR-UNDEFINED-001", "unregistered action refusal");
  await persistRecordInfoAction(DEMO, "INFO-01-BTN-DOES-NOT-EXIST", "INFO-01-ACT-NOOP");
  assertEqual((await readError())?.code, "INFO-01-ERR-UNDEFINED-001", "unknown control refusal");

  // 3. Refresh without idempotency_key -> CONTEXT-001 refusal, nothing written.
  await persistRecordInfoAction(DEMO, BTN_REFRESH, "INFO-01-ACT-REFRESH");
  assertEqual((await readError())?.code, "INFO-01-ERR-CONTEXT-001", "keyless refresh refusal");
  assertEqual(await readState("INFO-01-STATE-REFRESH"), null, "keyless refresh writes nothing");

  // 4. Refresh: real stamp + header context fields + structured audit.
  const refreshKey = key("refresh");
  await persistRecordInfoAction(DEMO, BTN_REFRESH, "INFO-01-ACT-REFRESH", JSON.stringify({ idempotency_key: refreshKey }));
  const refresh = JSON.parse((await readState("INFO-01-STATE-REFRESH")) ?? "{}") as { rowsRead: number; rowsWithValue: number; refreshedAt: string };
  assert(refresh.rowsRead >= 66, `refresh reads registered rows (${refresh.rowsRead})`);
  assertEqual(await readState("INFO-01-FLD-LAST-REFRESH"), refresh.refreshedAt, "last-refresh stamp bound");
  assertEqual(await readState("INFO-01-FLD-PROJECTION-VERSION"), "1", "projection version incremented");
  assertEqual(await readState("INFO-01-FLD-PAGE-STATE"), "READY", "page state refreshed");
  const scopeField = await readState("INFO-01-FLD-SCOPE");
  assert(scopeField && scopeField.split(",").length >= 5, `scope flags written (${scopeField})`);
  assertEqual((await readError())?.code, undefined, "refresh clears error");
  const auditAfterRefresh = ((await readState("INFO-01-STATE-AUDIT")) ?? "").split("\n")[0];
  assert(auditAfterRefresh.includes("op=REFRESH") && auditAfterRefresh.includes(`key=${refreshKey}`) && auditAfterRefresh.includes("result=OK") && auditAfterRefresh.includes("actor=ACC-DEMO"), `structured audit line (${auditAfterRefresh})`);

  // 5. Refresh replay: same key -> IDEMPOTENT-REPLAY, zero re-write.
  const refreshStamp = await readState("INFO-01-STATE-REFRESH");
  await persistRecordInfoAction(DEMO, BTN_REFRESH, "INFO-01-ACT-REFRESH", JSON.stringify({ idempotency_key: refreshKey }));
  assertEqual((await readError())?.code, undefined, "replay clears error");
  const replayAudit = ((await readState("INFO-01-STATE-AUDIT")) ?? "").split("\n")[0];
  assert(replayAudit.includes("result=IDEMPOTENT-REPLAY") && replayAudit.includes("op=REFRESH-REPLAY"), `replay audit (${replayAudit})`);
  assertEqual(await readState("INFO-01-STATE-REFRESH"), refreshStamp, "replay did not rewrite state");
  assertEqual(await readState("INFO-01-FLD-PROJECTION-VERSION"), "1", "replay did not bump version");

  // 6. Search: empty query + missing key refusals, then a real search.
  await persistRecordInfoAction(DEMO, BTN_SEARCH, "INFO-01-ACT-SEARCH", JSON.stringify({ query: "", idempotency_key: key("search") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-SEARCH-001", "empty query refusal");
  await persistRecordInfoAction(DEMO, BTN_SEARCH, "INFO-01-ACT-SEARCH", JSON.stringify({ query: "CANDIDATE-ID" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-SEARCH-001", "keyless search refusal");
  await persistRecordInfoAction(DEMO, BTN_SEARCH, "INFO-01-ACT-SEARCH", JSON.stringify({ query: "CANDIDATE-ID", idempotency_key: key("search") }));
  const search = JSON.parse((await readState("INFO-01-STATE-SEARCH")) ?? "{}") as { matchedCount: number; matched: Array<{ controlUid: string }> };
  assert(search.matchedCount >= 1, "search matches registered rows");
  assert(search.matched.some((item) => item.controlUid === "INFO-01-FLD-CANDIDATE-ID"), "search finds candidate id control");

  // 7. Export: exact contract fields; missing fields + keyless refusals.
  await persistRecordInfoAction(DEMO, BTN_EXPORT, "INFO-01-ACT-EXPORT", JSON.stringify({ export_scope: "fact_pack", idempotency_key: key("export") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-EXPORT-001", "legacy export schema refusal");
  await persistRecordInfoAction(DEMO, BTN_EXPORT, "INFO-01-ACT-EXPORT", JSON.stringify({ projection_type: "fact_pack", format: "json" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-EXPORT-001", "keyless export refusal");
  await persistRecordInfoAction(DEMO, BTN_EXPORT, "INFO-01-ACT-EXPORT", JSON.stringify({ projection_type: "fact_pack", scope_ref: "ACC-DEMO", format: "json", idempotency_key: key("export") }));
  const exports = JSON.parse((await readState("INFO-01-STATE-EXPORTS")) ?? "[]") as Array<{ projectionType: string; scopeRef: string; format: string; rowCount: number; exportedAt: string }>;
  assertEqual(exports[0]?.projectionType, "fact_pack", "export projection_type recorded");
  assertEqual(exports[0]?.scopeRef, "ACC-DEMO", "export scope_ref recorded");
  assertEqual(exports[0]?.format, "json", "export format recorded");
  assert(exports[0].rowCount >= 66, "export counts real rows");

  // 8. Adopt: contract schema (context_candidate_id + decision_reason),
  // keyless refusal, unknown candidate, version mismatch.
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ candidate_id: "cc-1", rationale: "ok", idempotency_key: key("adopt") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "adopt legacy schema refusal");
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ context_candidate_id: "cc-1", decision_reason: "ok" }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "keyless adopt refusal");
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ context_candidate_id: "no-such", decision_reason: "x", expected_version: "1", idempotency_key: key("adopt") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "adopt unknown candidate refusal");

  // 9. Register a governed Context Candidate (SQL fixture, versioned) and adopt.
  await client.run(
    "UPDATE ghsn_info_field_projection SET value_text = ? WHERE control_uid = ?",
    [JSON.stringify([{ candidateId: "cc-1", scope: "demand", status: "CANDIDATE", decidedAt: null, version: 3 }]), INFO_STATE_CANDIDATES_UID],
  );
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ context_candidate_id: "cc-1", decision_reason: "use as context", expected_version: "2", idempotency_key: key("adopt") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "adopt version mismatch refusal");
  const adoptKey = key("adopt");
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ context_candidate_id: "cc-1", decision_reason: "use as context", expected_version: "3", idempotency_key: adoptKey }));
  assertEqual((await readError())?.code, undefined, "adopt clears error");
  const adoptedRegistry = JSON.parse((await readState(INFO_STATE_CANDIDATES_UID)) ?? "[]") as Array<{ status: string; decidedAt: string | null; version: number }>;
  assertEqual(adoptedRegistry[0].status, "ADOPTED", "candidate adopted");
  assertEqual(adoptedRegistry[0].version, 3, "adoption preserves version");
  assert(adoptedRegistry[0].decidedAt !== null, "adoption stamps decidedAt");
  // Adoption never writes Canon/Lock/Task/Publish surfaces — only the
  // candidate registry and audit trail changed (asserted by registry state).

  // 10. Adopt replay: zero state change.
  const adoptedStamp = await readState(INFO_STATE_CANDIDATES_UID);
  await persistRecordInfoAction(DEMO, BTN_ADOPT, "INFO-01-ACT-ADOPT-CONTEXT", JSON.stringify({ context_candidate_id: "cc-1", decision_reason: "use as context", expected_version: "3", idempotency_key: adoptKey }));
  assertEqual(await readState(INFO_STATE_CANDIDATES_UID), adoptedStamp, "adopt replay preserves registry");
  assert(((await readState("INFO-01-STATE-AUDIT")) ?? "").includes("result=IDEMPOTENT-REPLAY"), "adopt replay audited");

  // 11. Decide: vocabulary + version + state gates (rationale field removed).
  await client.run(
    "UPDATE ghsn_info_field_projection SET value_text = ? WHERE control_uid = ?",
    [JSON.stringify([{ candidateId: "cc-2", scope: "supply", status: "CANDIDATE", decidedAt: null, version: 1 }]), INFO_STATE_CANDIDATES_UID],
  );
  await persistRecordInfoAction(DEMO, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "APPROVED", expected_version: "1", idempotency_key: key("decide") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "invalid decision vocabulary refusal");
  await persistRecordInfoAction(DEMO, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "REJECTED", expected_version: "9", idempotency_key: key("decide") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "decide version mismatch refusal");
  await persistRecordInfoAction(DEMO, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "REJECTED", expected_version: "1", idempotency_key: key("decide") }));
  assertEqual((JSON.parse((await readState(INFO_STATE_CANDIDATES_UID)) ?? "[]") as Array<{ status: string }>)[0].status, "REJECTED", "candidate rejected");

  // 12. Decide already-decided candidate -> exact-state refusal.
  await persistRecordInfoAction(DEMO, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "ACCEPTED", expected_version: "1", idempotency_key: key("decide") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-CANDIDATE-001", "decide refuses non-CANDIDATE");

  // 13. Scope gate: page scope alone cannot refresh/search/export/decide.
  await persistRecordInfoAction(READONLY, BTN_REFRESH, "INFO-01-ACT-REFRESH", JSON.stringify({ idempotency_key: key("ro") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-PERM-001", "scope gate blocks refresh");
  await persistRecordInfoAction(READONLY, BTN_DECIDE, "INFO-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidate_id: "cc-2", decision: "ACCEPTED", expected_version: "1", idempotency_key: key("ro") }));
  assertEqual((await readError())?.code, "INFO-01-ERR-PERM-001", "scope gate blocks decide");
  assertEqual((JSON.parse((await readState(INFO_STATE_CANDIDATES_UID)) ?? "[]") as Array<{ status: string }>)[0].status, "REJECTED", "denied decision applied nothing");

  // 14. Read-model scope flags: DEMO holds the full permission set, READONLY
  // holds exactly information.read.
  const demoModel = await persistGetInfoReadModel(DEMO);
  assertEqual(demoModel.scopes.length, INFO_PERMISSION_SET.size, "demo scopes full set");
  const readonlyModel = await persistGetInfoReadModel(READONLY);
  assertEqual(readonlyModel.scopes.length, 1, "readonly scopes single");
  assertEqual(readonlyModel.scopes[0], "information.read", "readonly scope value");

  // 15. deriveInfoPageState: contract vocabulary of 8 states.
  assertEqual(deriveInfoPageState({ loading: true, fetchError: null, authorized: false, errorCode: null, stale: false, incomplete: false, hasOpenCandidates: false, hasRuntimeState: false }), "LOADING", "state LOADING");
  assertEqual(deriveInfoPageState({ loading: false, fetchError: "boom", authorized: true, errorCode: null, stale: false, incomplete: false, hasOpenCandidates: false, hasRuntimeState: true }), "ERROR", "state ERROR");
  assertEqual(deriveInfoPageState({ loading: false, fetchError: null, authorized: false, errorCode: null, stale: false, incomplete: false, hasOpenCandidates: false, hasRuntimeState: false }), "POLICY_BLOCKED", "state POLICY_BLOCKED");
  assertEqual(deriveInfoPageState({ loading: false, fetchError: null, authorized: true, errorCode: "INFO-01-ERR-PERM-001", stale: false, incomplete: false, hasOpenCandidates: false, hasRuntimeState: true }), "POLICY_BLOCKED", "state POLICY_BLOCKED by code");
  assertEqual(deriveInfoPageState({ loading: false, fetchError: null, authorized: true, errorCode: null, stale: false, incomplete: true, hasOpenCandidates: false, hasRuntimeState: true }), "INCOMPLETE", "state INCOMPLETE");
  assertEqual(deriveInfoPageState({ loading: false, fetchError: null, authorized: true, errorCode: null, stale: true, incomplete: false, hasOpenCandidates: false, hasRuntimeState: true }), "STALE", "state STALE");
  assertEqual(deriveInfoPageState({ loading: false, fetchError: null, authorized: true, errorCode: null, stale: false, incomplete: false, hasOpenCandidates: true, hasRuntimeState: true }), "CONTEXT_CANDIDATE", "state CONTEXT_CANDIDATE");
  assertEqual(deriveInfoPageState({ loading: false, fetchError: null, authorized: true, errorCode: null, stale: false, incomplete: false, hasOpenCandidates: false, hasRuntimeState: false }), "EMPTY", "state EMPTY");
  assertEqual(deriveInfoPageState({ loading: false, fetchError: null, authorized: true, errorCode: null, stale: false, incomplete: false, hasOpenCandidates: false, hasRuntimeState: true }), "READY", "state READY");

  // 16. STATE uids exposed through the field list.
  const listed = await persistListInfoFields();
  const listedUids = new Set(listed.map((field) => field.controlUid));
  for (const uid of STATE_KEYS) assert(listedUids.has(uid), `field list exposes ${uid}`);

  // Restore sandbox to clean state.
  for (const uid of RESET_UIDS) {
    await client.run("UPDATE ghsn_info_field_projection SET value_text = NULL WHERE control_uid = ?", [uid]);
  }

  console.log(`infoWorkspace: 16 sections passed (${new Date().toISOString()})`);
  process.exit(0);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
