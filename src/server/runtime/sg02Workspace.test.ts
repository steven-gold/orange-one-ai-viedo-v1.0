import { bootstrapDatabase } from "../db/migrate";
import { seedScope } from "../db/seed";
import { persistGetSg02ReadModel, persistListSg02Fields, persistRecordSg02Action } from "../db/persist";
import { getSqlClient } from "../db/client";
import {
  SG02_STATE_APPROVALS_UID,
  SG02_STATE_AUDIT_UID,
  SG02_STATE_CHECKS_UID,
  SG02_STATE_CRITERIA_UID,
  SG02_STATE_DIMENSIONS_UID,
  SG02_STATE_ERROR_UID,
  SG02_STATE_IDEMPOTENCY_UID,
  SG02_STATE_MAPPINGS_UID,
  SG02_STATE_POLICIES_UID,
  SG02_STATE_RESOURCE_UID,
  SG02_STATE_THRESHOLDS_UID,
} from "../domain/sg02";
import { deriveSg02PageState } from "../../components/pages/sg02Format";

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

const STATE_KEYS = [
  SG02_STATE_ERROR_UID,
  SG02_STATE_RESOURCE_UID,
  SG02_STATE_AUDIT_UID,
  SG02_STATE_IDEMPOTENCY_UID,
  SG02_STATE_CRITERIA_UID,
  SG02_STATE_DIMENSIONS_UID,
  SG02_STATE_THRESHOLDS_UID,
  SG02_STATE_MAPPINGS_UID,
  SG02_STATE_CHECKS_UID,
  SG02_STATE_POLICIES_UID,
  SG02_STATE_APPROVALS_UID,
];

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

interface Sg02Resource {
  resourceType: string;
  resourceId: string;
  version: number;
  status: string;
  configPatch: string;
}

async function readResource(): Promise<Sg02Resource | null> {
  const raw = await readState(SG02_STATE_RESOURCE_UID);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Sg02Resource;
  } catch {
    return null;
  }
}

async function readCriteria(): Promise<Array<{ version: number; status: string; configPatch: string; updatedAt: string; supersededBy?: number }>> {
  const raw = await readState(SG02_STATE_CRITERIA_UID);
  return raw ? (JSON.parse(raw) as Array<{ version: number; status: string; configPatch: string; updatedAt: string; supersededBy?: number }>) : [];
}

async function readRegistryEntries(uid: string): Promise<Array<Record<string, unknown>>> {
  const raw = await readState(uid);
  return raw ? (JSON.parse(raw) as Array<Record<string, unknown>>) : [];
}

const CONFIG_PAYLOAD = {
  resource_type: "quality_criteria_version",
  resource_id: "qcv-2026-11",
  config_patch_json: JSON.stringify({ dimensions: ["clarity", "evidence"], pass_threshold: 0.85 }),
  reason: "Quarterly criteria review",
};

let idemSeq = 0;
function idem(): string {
  idemSeq += 1;
  return `idem-sg02-${String(idemSeq).padStart(3, "0")}`;
}

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

  // 2. Side-effect configure without idempotency_key -> refusal
  //    (required_backend_gates idempotency_when_side_effect).
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD }));
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "configure requires idempotency key");
  assertEqual(await readState(SG02_STATE_RESOURCE_UID), null, "no resource without idempotency key");

  // 3. Invalid config_patch_json -> refusal.
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, idempotency_key: idem(), config_patch_json: "{not-json" }));
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "invalid config patch");

  // 4. Valid configure -> DRAFT v1 + CONFIGURED action value + audit line.
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, idempotency_key: idem() }));
  assertEqual((await readError())?.code, undefined, "configure clears error");
  const resourceV1 = await readResource();
  assert(resourceV1, "resource registered after configure");
  assertEqual(resourceV1.status, "DRAFT", "configured resource is DRAFT");
  assertEqual(resourceV1.version, 1, "first version");
  const configuredValue = await readState(ACTION_CONFIGURE);
  assert(configuredValue?.includes("CONFIGURED") && configuredValue.includes("v1"), "action control records configure");
  const auditLine = await readState(SG02_STATE_AUDIT_UID);
  assert(auditLine?.includes("DRAFT · quality_criteria_version/qcv-2026-11 · v1"), "audit trail records configure");
  assert(auditLine?.includes("event=governance.configured"), "configure audit carries contract event marker");

  // 5. Idempotency replay: same action+key performs no new write.
  const registryBeforeReplay = await readCriteria();
  const replayKey = (JSON.parse(await readState(SG02_STATE_IDEMPOTENCY_UID) ?? "{}") as Record<string, string>);
  const firstConfigureKey = Object.keys(replayKey).find((k) => k.startsWith("configureGovernedResource:"));
  assert(firstConfigureKey, "idempotency registry recorded configure key");
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, idempotency_key: firstConfigureKey.split(":")[1] }));
  assertEqual((await readError())?.code, undefined, "replay clears error");
  assertEqual((await readCriteria()).length, registryBeforeReplay.length, "replay adds no criteria version");
  assertEqual((await readResource())?.version, 1, "replay preserves version");
  assert((await readState(SG02_STATE_AUDIT_UID))?.includes("IDEMPOTENT-REPLAY configureGovernedResource"), "audit records replay");

  // 6. Reconfigure with a fresh key -> version bump, still DRAFT (DRAFT -> DRAFT).
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, idempotency_key: idem(), reason: "Patch pass threshold" }));
  const resourceV2 = await readResource();
  assert(resourceV2, "resource registered after reconfigure");
  assertEqual(resourceV2.version, 2, "reconfigure bumps version");
  assertEqual(resourceV2.status, "DRAFT", "configure keeps DRAFT");
  const criteriaV2 = await readCriteria();
  assertEqual(criteriaV2.length, 2, "criteria registry holds both versions");
  for (const version of criteriaV2) assertEqual(version.status, "DRAFT", "registry versions start DRAFT");

  // 7. Approve missing rationale -> refusal.
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11" }));
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "approve requires rationale");

  // 8. Approve unregistered resource -> refusal.
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-unknown", rationale: "x", idempotency_key: idem() }));
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "approve unregistered resource");

  // 9. Approve DRAFT resource -> exact-state refusal (REVIEW -> APPROVED only).
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11", rationale: "ok", idempotency_key: idem() }));
  assertEqual((await readError())?.code, "SG-02-ERR-STATE", "approve refuses DRAFT");
  const draftAfterRefusal = await readResource();
  assert(draftAfterRefusal, "resource preserved after refusal");
  assertEqual(draftAfterRefusal.status, "DRAFT", "DRAFT preserved");

  // 10. Backend service transition: DRAFT -> REVIEW (review flow places the
  //     governed version under review; mirrored into the criteria registry).
  await client.run(
    "UPDATE ghsn_sg02_field_projection SET value_text = ? WHERE control_uid = ?",
    [JSON.stringify({ ...draftAfterRefusal, status: "REVIEW" }), SG02_STATE_RESOURCE_UID],
  );
  const criteriaForReview = await readCriteria();
  const reviewRecord = criteriaForReview.find((v) => v.version === 2);
  assert(reviewRecord, "criteria v2 present before review");
  reviewRecord.status = "REVIEW";
  await client.run("UPDATE ghsn_sg02_field_projection SET value_text = ? WHERE control_uid = ?", [JSON.stringify(criteriaForReview), SG02_STATE_CRITERIA_UID]);

  // 11. Version conflict -> expected_resource_version gate.
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11", rationale: "ok", expected_resource_version: "1", idempotency_key: idem() }));
  assertEqual((await readError())?.code, "SG-02-ERR-VERSION", "approve version conflict");
  const conflictAfter = await readResource();
  assert(conflictAfter, "resource preserved after conflict");
  assertEqual(conflictAfter.status, "REVIEW", "conflict preserves state");

  // 12. REVIEW + matching version -> APPROVED, then governance engine
  //     activation to ACTIVE; version preserved (approval keeps version).
  const approveKey = idem();
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11", rationale: "Release criteria", expected_resource_version: "2", idempotency_key: approveKey }));
  assertEqual((await readError())?.code, undefined, "approve clears error");
  const approved = await readResource();
  assert(approved, "resource preserved after approval");
  assertEqual(approved.status, "ACTIVE", "engine activates approved criteria");
  assertEqual(approved.version, 2, "approval preserves version");
  const approvedValue = await readState(ACTION_APPROVE);
  assert(approvedValue?.includes("APPROVED") && approvedValue.includes("v2"), "action control records approval");
  const criteriaAfterApproval = await readCriteria();
  assertEqual(criteriaAfterApproval.find((v) => v.version === 1)?.status, "DRAFT", "prior draft untouched");
  assertEqual(criteriaAfterApproval.find((v) => v.version === 2)?.status, "ACTIVE", "approved version ACTIVE in registry");
  assert((await readState(SG02_STATE_AUDIT_UID))?.includes("APPROVED · quality_criteria_version/qcv-2026-11 · v2 · event=governance.approved"), "approve audit carries contract event marker");
  assert((await readState(SG02_STATE_AUDIT_UID))?.includes("governance.approved engine activation"), "audit records engine activation");
  const approvals = await readRegistryEntries(SG02_STATE_APPROVALS_UID);
  assertEqual(approvals.length, 1, "approval registered");
  assertEqual(approvals[0].decision, "APPROVED", "approval decision recorded");
  assertEqual(approvals[0].version, 2, "approval version recorded");
  assertEqual(approvals[0].approvedBy, DEMO, "approval actor recorded");

  // 13. Approve idempotency replay: no duplicate approval.
  await persistRecordSg02Action(DEMO, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11", rationale: "Release criteria", expected_resource_version: "2", idempotency_key: approveKey }));
  assertEqual((await readError())?.code, undefined, "approve replay clears error");
  assertEqual((await readRegistryEntries(SG02_STATE_APPROVALS_UID)).length, 1, "approve replay adds no approval");
  assertEqual((await readResource())?.status, "ACTIVE", "approve replay preserves state");

  // 14. active_criteria_immutable: configure after ACTIVE -> new DRAFT
  //     version while ACTIVE stays reproducible.
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, idempotency_key: idem(), reason: "Next cycle" }));
  const criteriaV3 = await readCriteria();
  assertEqual(criteriaV3.length, 3, "new cycle adds version");
  assertEqual(criteriaV3.find((v) => v.version === 2)?.status, "ACTIVE", "ACTIVE stays reproducible");
  assertEqual(criteriaV3.find((v) => v.version === 3)?.status, "DRAFT", "change requires new DRAFT version");
  assertEqual((await readResource())?.version, 3, "resource tracks newest version");

  // 15. getUiProjection keeps the registry and clears transient error.
  await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "deleteEverything");
  assertEqual((await readError())?.code, "SG-02-ERR-UNDEFINED", "unregistered action blocked");
  await persistRecordSg02Action(DEMO, "CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN", "getUiProjection");
  assert((await readResource()), "projection read keeps registry");
  assertEqual((await readError())?.code, undefined, "projection read clears error");
  // Remaining FUNC-CTRL-ADMIN-SG-02-* control tests: every registered drawer
  // open and the rail nav action run as read-model projections.
  for (const controlUid of [
    "CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN",
    "CTRL-ADMIN-SG-02-THRESHOLDS-OPEN",
    "CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN",
    "CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN",
    "CTRL-ADMIN-SG-02-GATE-POLICY-OPEN",
    "CTRL-ADMIN-SG-02-APPROVAL-OPEN",
    "CTRL-ADMIN-SG-02-IMPACT-OPEN",
    "CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN",
  ]) {
    await persistRecordSg02Action(DEMO, controlUid, "getUiProjection");
    assertEqual((await readError())?.code, undefined, `${controlUid} accepted`);
    assert((await readResource()), `${controlUid} keeps registry`);
  }
  // Contract state_contract.allowed_states: full 10-state vocabulary.
  const baseInput = { loading: false, fetchError: null as string | null, authorized: true, configureAuthorized: true, errorCode: null as string | null, resourceStatus: null as string | null, hasRuntimeState: true };
  assertEqual(deriveSg02PageState({ ...baseInput, loading: true }), "LOADING", "state LOADING");
  assertEqual(deriveSg02PageState({ ...baseInput, fetchError: "x" }), "ERROR", "state ERROR");
  assertEqual(deriveSg02PageState({ ...baseInput, authorized: false }), "POLICY_BLOCKED", "state POLICY_BLOCKED");
  assertEqual(deriveSg02PageState({ ...baseInput, errorCode: "SG-02-ERR-VERSION" }), "VERSION_CONFLICT", "state VERSION_CONFLICT");
  assertEqual(deriveSg02PageState({ ...baseInput, errorCode: "SG-02-ERR-STATE" }), "REVIEW_REQUIRED", "state REVIEW_REQUIRED by code");
  assertEqual(deriveSg02PageState({ ...baseInput, resourceStatus: "REVIEW" }), "REVIEW_REQUIRED", "state REVIEW_REQUIRED by status");
  assertEqual(deriveSg02PageState({ ...baseInput, resourceStatus: "PENDING_EXTERNAL" }), "EXTERNAL_PENDING", "state EXTERNAL_PENDING");
  assertEqual(deriveSg02PageState({ ...baseInput, resourceStatus: "RETIRED" }), "ARCHIVED", "state ARCHIVED");
  assertEqual(deriveSg02PageState({ ...baseInput, configureAuthorized: false }), "READ_ONLY", "state READ_ONLY");
  assertEqual(deriveSg02PageState({ ...baseInput, hasRuntimeState: false }), "EMPTY", "state EMPTY");
  assertEqual(deriveSg02PageState(baseInput), "READY", "state READY");

  // 16. Server-side scope gate: page scope alone cannot configure.
  await persistRecordSg02Action(SCOPED, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ ...CONFIG_PAYLOAD, idempotency_key: idem() }));
  assertEqual((await readError())?.code, "SG-02-ERR-AUTH", "scope gate blocks configure");
  const deniedAfter = await readResource();
  assert(deniedAfter, "registry preserved after denied write");
  assertEqual(deniedAfter.version, 3, "denied write applied nothing");
  assertEqual(deniedAfter.resourceId, "qcv-2026-11", "denied write keeps registered resource");
  await persistRecordSg02Action(SCOPED, ACTION_APPROVE, "approveGovernedResource", JSON.stringify({ resource_type: "quality_criteria_version", resource_id: "qcv-2026-11", rationale: "x", idempotency_key: idem() }));
  assertEqual((await readError())?.code, "SG-02-ERR-AUTH", "scope gate blocks approve");

  // 17-21. Every governed resource type routes to its registry.
  const otherTypes: Array<[string, string, string, string]> = [
    ["quality_dimension", "SG02_STATE_DIMENSIONS", "dim-clarity", JSON.stringify({ name: "clarity", weight: 0.3 })],
    ["quality_threshold", "SG02_STATE_THRESHOLDS", "thr-pass", JSON.stringify({ metric: "pass_rate", operator: ">=", value: 0.85 })],
    ["quality_gate_policy", "SG02_STATE_POLICIES", "pol-gate", JSON.stringify({ gate: "qa-release", require_all_checks: true })],
    ["quality_department_mapping", "SG02_STATE_MAPPINGS", "map-dept", JSON.stringify({ department: "QA", criteria: "qcv-2026-11" })],
    ["quality_required_check", "SG02_STATE_CHECKS", "chk-review", JSON.stringify({ check: "peer_review", blocking: true })],
  ];
  const registryUidByName: Record<string, string> = {
    quality_dimension: SG02_STATE_DIMENSIONS_UID,
    quality_threshold: SG02_STATE_THRESHOLDS_UID,
    quality_gate_policy: SG02_STATE_POLICIES_UID,
    quality_department_mapping: SG02_STATE_MAPPINGS_UID,
    quality_required_check: SG02_STATE_CHECKS_UID,
  };
  for (const [resourceType, , resourceId, configPatch] of otherTypes) {
    await persistRecordSg02Action(DEMO, ACTION_CONFIGURE, "configureGovernedResource", JSON.stringify({ resource_type: resourceType, resource_id: resourceId, config_patch_json: configPatch, reason: "QA governance setup", idempotency_key: idem() }));
    assertEqual((await readError())?.code, undefined, `${resourceType} configure clears error`);
    const entries = await readRegistryEntries(registryUidByName[resourceType]);
    assertEqual(entries.length, 1, `${resourceType} registry entry`);
    assertEqual(entries[0].resourceId, resourceId, `${resourceType} registry id`);
    const typed = await readResource();
    assert(typed, `${resourceType} resource state`);
    assertEqual(typed.resourceType, resourceType, `${resourceType} routed`);
    assertEqual(typed.status, "DRAFT", `${resourceType} starts DRAFT`);
    assertEqual(typed.version, 1, `${resourceType} first version`);
  }

  // 22. STATE uids are exposed through the field list (STATE uids stay
  //     outside the 11-control denominator).
  const listed = await persistListSg02Fields();
  const listedUids = new Set(listed.map((field) => field.controlUid));
  for (const uid of STATE_KEYS) assert(listedUids.has(uid), `field list exposes ${uid}`);
  for (const uid of ["CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE", "CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN"]) assert(listedUids.has(uid), `field list keeps control ${uid}`);

  // 23. Read-model scope flags mirror the runtime gates directly.
  const demoModel = await persistGetSg02ReadModel(DEMO);
  assertEqual(demoModel.authorized, true, "demo page authorized");
  assertEqual(demoModel.configureAuthorized, true, "demo governance.configure granted");
  const scopedModel = await persistGetSg02ReadModel(SCOPED);
  assertEqual(scopedModel.authorized, true, "page-only account still reads the page");
  assertEqual(scopedModel.configureAuthorized, false, "page-only account cannot configure");

  // 24. Page-state derivation covers the contract allowed_states vocabulary.
  const base = { fetchError: null as string | null, authorized: true, configureAuthorized: true, errorCode: null as string | null, resourceStatus: null as string | null, hasRuntimeState: true };
  assertEqual(deriveSg02PageState({ ...base, loading: true }), "LOADING", "state LOADING");
  assertEqual(deriveSg02PageState({ ...base, loading: false, fetchError: "boom" }), "ERROR", "state ERROR");
  assertEqual(deriveSg02PageState({ ...base, loading: false, errorCode: "SG-02-ERR-AUTH" }), "POLICY_BLOCKED", "state POLICY_BLOCKED");
  assertEqual(deriveSg02PageState({ ...base, loading: false, errorCode: "SG-02-ERR-VERSION" }), "VERSION_CONFLICT", "state VERSION_CONFLICT");
  assertEqual(deriveSg02PageState({ ...base, loading: false, resourceStatus: "REVIEW" }), "REVIEW_REQUIRED", "state REVIEW_REQUIRED");
  assertEqual(deriveSg02PageState({ ...base, loading: false, resourceStatus: "RETIRED" }), "ARCHIVED", "state ARCHIVED");
  assertEqual(deriveSg02PageState({ ...base, loading: false, hasRuntimeState: false }), "EMPTY", "state EMPTY");
  assertEqual(deriveSg02PageState({ ...base, loading: false }), "READY", "state READY");
  assertEqual(deriveSg02PageState({ ...base, loading: false, authorized: false }), "POLICY_BLOCKED", "state unauthorized blocked");
  assertEqual(deriveSg02PageState({ ...base, loading: false, configureAuthorized: false }), "READ_ONLY", "state READ_ONLY without configure scope");

  // 25. Workspace test restores the sandbox to a clean SG-02 state.
  for (const uid of [...STATE_KEYS, ACTION_CONFIGURE, ACTION_APPROVE]) {
    await client.run("UPDATE ghsn_sg02_field_projection SET value_text = NULL WHERE control_uid = ?", [uid]);
  }

  console.log(`sg02Workspace: 28 sections passed (${new Date().toISOString()})`);
  process.exit(0);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
