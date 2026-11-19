import { bootstrapDatabase } from "../db/migrate";
import { seedScope } from "../db/seed";
import { persistListSg02Fields, persistRecordSg02Action } from "../db/persist";
import { getSqlClient } from "../db/client";
import { SG02_STATE_AUDIT_UID, SG02_STATE_ERROR_UID, SG02_STATE_RESOURCE_UID } from "../domain/sg02";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

const DEMO = "ACC-DEMO";
const SCOPED = "ACC-SG02-NOSCOPE";

const ACTION_CONFIGURE = "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE";
const ACTION_APPROVE = "CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE";

const STATE_KEYS = [SG02_STATE_ERROR_UID, SG02_STATE_RESOURCE_UID, SG02_STATE_AUDIT_UID];

async function readState(uid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    "SELECT value_text FROM ghsn_sg02_field_projection WHERE control_uid = ?",
    [uid],
  );
  const raw = rows[0]?.value_text ?? null;
  return raw === "" ? null : raw;
}

async function readError(): Promise<{ code?: string; detail?: string } | null> {
  const raw = await readState(SG02_STATE_ERROR_UID);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as { code?: string; detail?: string };
  } catch {
    return null;
  }
}

async function readResource(): Promise<{ resourceType: string; resourceId: string; version: number; status: string; configPatch: string } | null> {
  const raw = await readState(SG02_STATE_RESOURCE_UID);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as { resourceType: string; resourceId: string; version: number; status: string; configPatch: string };
  } catch {
    return null;
  }
}

const CONFIG_PAYLOAD = {
  resource_type: "quality_criteria_version",
  resource_id: "qcv-2026-11",
  config_patch_json: JSON.stringify({ dimensions: ["clarity", "evidence"], pass_threshold: 0.85 }),
  reason: "Quarterly criteria review",
};

async function main(): Promise<void> {
  await bootstrapDatabase();
  await seedScope("sg02");
  const client = getSqlClient();

  // Deterministic start: blank SG-02 state and action controls.
  for (const uid of [...STATE_KEYS, ACTION_CONFIGURE, ACTION_APPROVE]) {
    await client.run(
      `INSERT INTO ghsn_sg02_field_projection (control_uid, value_text) VALUES (?, NULL)
       ON CONFLICT (control_uid) DO UPDATE SET value_text = NULL`,
      [uid],
    );
  }
  // Probe account with page scope only (no governance.configure / governance.approve).
  await client.run(
    "INSERT INTO ghsn_account_sg02_permission (account_uid, permission_uid) VALUES (?, 'quality.criteria.configure') ON CONFLICT (account_uid, permission_uid) DO NOTHING",
    [SCOPED],
  );
  await client.run("DELETE FROM ghsn_account_sg02_permission WHERE account_uid = ? AND permission_uid <> 'quality.criteria.configure'", [SCOPED]);

  // 1. Missing required fields -> exact-schema refusal, nothing written.
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version" }));
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "missing configure fields");
  assertEqual(await readState(SG02_STATE_RESOURCE_UID), null, "no resource on incomplete configure");

  // 2. Invalid config_patch_json -> refusal.
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, config_patch_json: "{not-json" }));
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "invalid config patch");

  // 3. Valid configure -> DRAFT v1 + CONFIGURED action value + audit line.
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify(CONFIG_PAYLOAD));
  assertEqual((await readError())?.code, undefined, "configure clears error");
  const resourceV1 = await readResource();
  assert(resourceV1, "resource registered after configure");
  assertEqual(resourceV1.status, "DRAFT", "configured resource is DRAFT");
  assertEqual(resourceV1.version, 1, "first version");
  const configuredValue = await readState(ACTION_CONFIGURE);
  assert(configuredValue?.includes("CONFIGURED") && configuredValue.includes("v1"), "action control records configure");
  const auditLine = await readState(SG02_STATE_AUDIT_UID);
  assert(auditLine?.includes("DRAFT · quality_criteria_version/qcv-2026-11 · v1"), "audit trail records configure");

  // 4. Reconfigure same resource -> version bump, still DRAFT (DRAFT -> DRAFT).
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, reason: "Patch pass threshold" }));
  const resourceV2 = await readResource();
  assert(resourceV2, "resource registered after reconfigure");
  assertEqual(resourceV2.version, 2, "reconfigure bumps version");
  assertEqual(resourceV2.status, "DRAFT", "configure keeps DRAFT");

  // 5. Approve missing rationale -> refusal.
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11" }));
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "approve requires rationale");

  // 6. Approve unregistered resource -> refusal.
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-unknown", rationale: "x" }));
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "approve unregistered resource");

  // 7. Approve DRAFT resource -> exact-state refusal (REVIEW -> APPROVED only).
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11", rationale: "ok" }));
  assertEqual((await readError())?.code, "SG-02-ERR-STATE", "approve refuses DRAFT");
  const draftAfterRefusal = await readResource();
  assert(draftAfterRefusal, "resource preserved after refusal");
  assertEqual(draftAfterRefusal.status, "DRAFT", "DRAFT preserved");

  // 8. Version conflict -> expected_resource_version gate.
  await client.run(
    `UPDATE ghsn_sg02_field_projection SET value_text = ? WHERE control_uid = ?`,
    [
      JSON.stringify({ ...draftAfterRefusal, status: "REVIEW" }),
      SG02_STATE_RESOURCE_UID,
    ],
  );
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11", rationale: "ok", expected_resource_version: "1" }));
  assertEqual((await readError())?.code, "SG-02-ERR-VERSION", "approve version conflict");
  const conflictAfter = await readResource();
  assert(conflictAfter, "resource preserved after conflict");
  assertEqual(conflictAfter.status, "REVIEW", "conflict preserves state");

  // 9. REVIEW + matching version -> APPROVED with new version.
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11", rationale: "Release criteria", expected_resource_version: "2" }));
  assertEqual((await readError())?.code, undefined, "approve clears error");
  const approved = await readResource();
  assert(approved, "resource preserved after approval");
  assertEqual(approved.status, "APPROVED", "review approved");
  assertEqual(approved.version, 3, "approval bumps version");
  const approvedValue = await readState(ACTION_APPROVE);
  assert(approvedValue?.includes("APPROVED") && approvedValue.includes("v3"), "action control records approval");

  // 10. getUiProjection keeps the registry and clears transient error.
  await persistRecordSg02Action(DEMO, "CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN", "getUiProjection");
  assert((await readResource()), "projection read keeps registry");
  assertEqual((await readError())?.code, undefined, "projection read clears error");

  // 11. Unregistered action -> fail-closed refusal.
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "deleteEverything");
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "unregistered action blocked");

  // 12. Server-side scope gate: page scope alone cannot configure.
  await persistRecordSg02Action(SCOPED, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify(CONFIG_PAYLOAD));
  assertEqual((await readError())?.code, "SG-02-ERR-AUTH", "scope gate blocks configure");
  const deniedAfter = await readResource();
  assert(deniedAfter, "registry preserved after denied write");
  assertEqual(deniedAfter.version, 3, "denied write applied nothing");
  assertEqual(deniedAfter.resourceId, "qcv-2026-11", "denied write keeps registered resource");

  // 13. STATE uids are exposed through the field list (STATE uids stay
  // outside the 11-control denominator).
  const listed = await persistListSg02Fields();
  const listedUids = new Set(listed.map((field) => field.controlUid));
  for (const uid of STATE_KEYS) assert(listedUids.has(uid), `field list exposes ${uid}`);
  for (const uid of ["CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE", "CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN"]) assert(listedUids.has(uid), `field list keeps control ${uid}`);

  // 14. Workspace test restores the sandbox to a clean SG-02 state.
  for (const uid of STATE_KEYS) {
    await client.run("UPDATE ghsn_sg02_field_projection SET value_text = NULL WHERE control_uid = ?", [uid]);
  }
  for (const uid of [ACTION_CONFIGURE, ACTION_APPROVE]) {
    await client.run("UPDATE ghsn_sg02_field_projection SET value_text = NULL WHERE control_uid = ?", [uid]);
  }

  console.log(`sg02Workspace: 14 checks passed (${new Date().toISOString()})`);
  process.exit(0);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
