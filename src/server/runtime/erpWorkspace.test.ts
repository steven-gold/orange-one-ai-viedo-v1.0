import { bootstrapDatabase } from "../db/migrate";
import { seedScope } from "../db/seed";
import { persistGetErpReadModel, persistRecordErpAction } from "../db/persist";
import { applyErpWorkbenchAction } from "./erpActions";
import { getSqlClient } from "../db/client";
import { AIAPI_REGISTRY_UID, serializeProfiles, type AiapiProfile } from "@/lib/aiapiProfiles";
import {
  ERP_STATE_CONNECTOR_UID,
  ERP_STATE_ERROR_UID,
  ERP_STATE_EXPORTS_UID,
  ERP_STATE_FACTPACK_UID,
  ERP_STATE_SNAPSHOT_UID,
  ERP_STATE_SYNC_JOBS_UID,
} from "../domain/erp";
import { deriveErpPageState } from "../../components/pages/erpFormat";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

const DEMO = "ACC-DEMO";
const FINLESS = "ACC-ERP-FINLESS";

const ERP_STATE_KEYS = [
  ERP_STATE_ERROR_UID,
  ERP_STATE_CONNECTOR_UID,
  ERP_STATE_SNAPSHOT_UID,
  ERP_STATE_SYNC_JOBS_UID,
  ERP_STATE_FACTPACK_UID,
  ERP_STATE_EXPORTS_UID,
];

const FLD_KEYS = [
  "ERP-01-FLD-SCOPE",
  "ERP-01-FLD-SNAPSHOT",
  "ERP-01-FLD-FRESHNESS",
  "ERP-01-FLD-FIN-COST",
  "ERP-01-FLD-FIN-REVENUE",
  "ERP-01-FLD-FIN-CASHFLOW",
  "ERP-01-FLD-FIN-CAPACITY",
  "ERP-01-FLD-FIN-FORECAST",
  "ERP-01-FLD-FIN-GUARDRAILS",
  "ERP-01-FLD-FIN-RECOMMENDATION-BOUNDARY",
  "ERP-01-FLD-CONN-CONNECTOR-ID",
  "ERP-01-FLD-CONN-PROVIDER-KEY",
  "ERP-01-FLD-CONN-ADAPTER-KEY",
  "ERP-01-FLD-CONN-SECRET-REFERENCE-ID",
  "ERP-01-FLD-CONN-ENTITY-SCOPE",
  "ERP-01-FLD-CONN-CONNECTION-STATUS",
  "ERP-01-FLD-CONN-MAPPING-VERSION",
  "ERP-01-FLD-SYNC-SNAPSHOT-ID",
  "ERP-01-FLD-SYNC-FRESHNESS-AT",
  "ERP-01-FLD-SYNC-CURRENCY-TIMEZONE",
  "ERP-01-FLD-SYNC-COMPLETENESS",
  "ERP-01-FLD-SYNC-LAST-SYNC-STATUS",
  "ERP-01-FLD-SYNC-FAILURE-ID",
  "ERP-01-FLD-READINESS",
  "ERP-01-FLD-AUDIT-REF",
];

const REGISTRY_FIXTURE: AiapiProfile[] = [
  {
    profileId: "prof-erp-probe",
    version: 1,
    seq: 1,
    providerId: "mock",
    providerName: "mock",
    modelId: "m",
    modelName: "m",
    baseUrl: "http://localhost:4571",
    endpointPath: "/v1/chat",
    httpMethod: "POST",
    timeoutSeconds: "30",
    adapterType: "text_chat",
    requestTemplate: "{}",
    responseTextPath: "$.text",
    promptTemplate: "",
    capabilityType: "TEXT_CHAT",
    additionalCapabilities: "",
    supportsReferences: "",
    rightsCompatible: "",
    dataClassifications: "internal",
    preferredLanguage: "zh-TW",
    maxContext: "",
    enabled: true,
    credentialSet: false,
    lastTest: "",
    lastTestAt: "",
    lastTestDetail: "",
  },
];

async function main(): Promise<void> {
  await bootstrapDatabase();
  await seedScope("erp");
  const client = getSqlClient();
  // Cross-module shared state: capture the governed AIAPI registry and
  // restore it after the run (ERP tests must not leak provider state).
  const registryBefore = await client
    .all<{ value_text: string | null }>("SELECT value_text FROM ghsn_aiapi_field_projection WHERE control_uid = ?", [AIAPI_REGISTRY_UID])
    .catch(() => [{ value_text: null }]);
  const registryOriginal = registryBefore[0]?.value_text ?? null;

  // Deterministic start: blank the ERP projection state and give the finless
  // probe account the page scope only (finance mask probe).
  for (const uid of [...ERP_STATE_KEYS, ...FLD_KEYS]) {
    await client.run(
      `INSERT INTO ghsn_erp_field_projection (control_uid, value_text) VALUES (?, NULL)
       ON CONFLICT (control_uid) DO UPDATE SET value_text = NULL`,
      [uid],
    );
  }
  await client.run(
    "INSERT INTO ghsn_account_erp_permission (account_uid, permission_uid) VALUES (?, 'erp.connector.read') ON CONFLICT (account_uid, permission_uid) DO NOTHING",
    [FINLESS],
  );
  await client.run(
    "DELETE FROM ghsn_account_erp_permission WHERE account_uid = ? AND permission_uid <> 'erp.connector.read'",
    [FINLESS],
  );

  const readError = async (): Promise<{ code?: string } | null> => {
    const rows = await client.all<{ value_text: string | null }>("SELECT value_text FROM ghsn_erp_field_projection WHERE control_uid = ?", [
      ERP_STATE_ERROR_UID,
    ]);
    const raw = rows[0]?.value_text;
    return raw ? (JSON.parse(raw) as { code?: string }) : null;
  };
  const readField = async (uid: string): Promise<string | null> => {
    const rows = await client.all<{ value_text: string | null }>("SELECT value_text FROM ghsn_erp_field_projection WHERE control_uid = ?", [uid]);
    return rows[0]?.value_text === "" ? null : (rows[0]?.value_text ?? null);
  };

  try {
    // Unregistered action -> BLOCK + REPORT_AUTHORITY_GAP.
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-FACTPACK", "ERP-01-ACT-NOPE");
    assertEqual((await readError())?.code, "ERP-01-ERR-UNDEFINED", "undefined action blocked");

    // finance gate: fact pack without finance.read is denied (ERR-AUTH).
    await applyErpWorkbenchAction(FINLESS, "ERP-01-BTN-FACTPACK", "ERP-01-ACT-FACTPACK");
    assertEqual((await readError())?.code, "ERP-01-ERR-AUTH", "finance.read required");

    // Connector create with a raw secret value -> secret boundary BLOCK.
    await applyErpWorkbenchAction(
      DEMO,
      "ERP-01-BTN-CONNECTOR-CREATE",
      "ERP-01-ACT-CONNECTOR-CREATE",
      JSON.stringify({ provider_key: "mock", adapter_key: "text_chat", secret_value: "sk-raw", entity_scope: "core", mapping_version: 1, data_classification: "internal" }),
    );
    assertEqual((await readError())?.code, "ERP-01-ERR-SECRET", "raw secret blocked");

    // Connector create missing required fields -> schema denial.
    await applyErpWorkbenchAction(
      DEMO,
      "ERP-01-BTN-CONNECTOR-CREATE",
      "ERP-01-ACT-CONNECTOR-CREATE",
      JSON.stringify({ provider_key: "mock" }),
    );
    assertEqual((await readError())?.code, "ERP-01-ERR-UNDEFINED", "schema fields required");

    // Valid create lands CONFIGURING with exact reference fields (mapping
    // detail fields default to — until a governed update completes them).
    await applyErpWorkbenchAction(
      DEMO,
      "ERP-01-BTN-CONNECTOR-CREATE",
      "ERP-01-ACT-CONNECTOR-CREATE",
      JSON.stringify({
        provider_key: "mock",
        adapter_key: "text_chat",
        secret_reference_id: "SECRET-REF-001",
        entity_scope: "enterprise-finance",
        mapping_version: 1,
        data_classification: "internal",
      }),
    );
    assertEqual(await readError(), null, "valid create clears error");
    assertEqual(await readField("ERP-01-FLD-CONN-CONNECTION-STATUS"), "CONFIGURING", "connector CONFIGURING");
    assertEqual(await readField("ERP-01-FLD-CONN-SECRET-REFERENCE-ID"), "SECRET-REF-001", "secret reference only");
    const connectorRaw = await readField(ERP_STATE_CONNECTOR_UID);
    assert(connectorRaw !== null && !connectorRaw.includes("sk-raw"), "no raw secret stored");

    // Update with a stale expected_version -> VERSION_CONFLICT.
    await applyErpWorkbenchAction(
      DEMO,
      "ERP-01-BTN-CONNECTOR-UPDATE",
      "ERP-01-ACT-CONNECTOR-UPDATE",
      JSON.stringify({ expected_version: 99 }),
    );
    assertEqual((await readError())?.code, "ERP-01-ERR-VERSION", "stale version blocked");

    // Mapping validate before mapping fields complete -> ERR-CONNECTOR.
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-MAPPING-VALIDATE", "ERP-01-ACT-MAPPING-VALIDATE");
    assertEqual((await readError())?.code, "ERP-01-ERR-CONNECTOR", "incomplete mapping blocked");

    // Version-aligned update completes the mapping spec (v1 -> v2).
    await applyErpWorkbenchAction(
      DEMO,
      "ERP-01-BTN-CONNECTOR-UPDATE",
      "ERP-01-ACT-CONNECTOR-UPDATE",
      JSON.stringify({
        expected_version: 1,
        mapping_entity_name: "cost_centers",
        mapping_source_schema: "erp.cost_centers.v1",
        mapping_target_schema: "acpos.finance.v1",
        mapping_transform_spec: "identity",
      }),
    );
    assertEqual(await readError(), null, "aligned update clears error");

    // Connector validate: honest READY when the provider exists in the
    // governed AIAPI registry, honest DEGRADED with the exact reason otherwise.
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-CONNECTOR-VALIDATE", "ERP-01-ACT-CONNECTOR-VALIDATE");
    const status = await readField("ERP-01-FLD-CONN-CONNECTION-STATUS");
    assert(status === "READY" || status === "DEGRADED", "validation keeps exact returned state");
    if (status === "DEGRADED") {
      assertEqual((await readError())?.code, "ERP-01-ERR-CONNECTOR", "degraded validation surfaces the failure reason");
      // Force a governed registry match for the remainder of the contract run.
      await client.run(
        `INSERT INTO ghsn_aiapi_field_projection (control_uid, value_text) VALUES (?, ?)
         ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
        [AIAPI_REGISTRY_UID, serializeProfiles(REGISTRY_FIXTURE)],
      );
      await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-CONNECTOR-VALIDATE", "ERP-01-ACT-CONNECTOR-VALIDATE");
    }
    assertEqual(await readField("ERP-01-FLD-CONN-CONNECTION-STATUS"), "READY", "connector READY against governed registry");

    // Snapshot refresh computes a real governed fingerprint.
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-SNAPSHOT-REFRESH", "ERP-01-ACT-SNAPSHOT-REFRESH");
    const snapshotRaw = await readField(ERP_STATE_SNAPSHOT_UID);
    const snapshot = snapshotRaw ? (JSON.parse(snapshotRaw) as { tables: Record<string, number>; completeness: number }) : null;
    assert(snapshot !== null && (snapshot.tables.core ?? 0) >= 1, "snapshot carries real table counts");
    assert((await readField("ERP-01-FLD-SNAPSHOT") ?? "").startsWith("ERP-SNAP-"), "snapshot id registered");
    assert((await readField("ERP-01-FLD-SYNC-COMPLETENESS") ?? "").endsWith("%"), "completeness computed");
    assertEqual(await readError(), null, "snapshot refresh clears error");

    // Sync job on a READY connector completes with the real snapshot ref.
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-SYNC-CREATE", "ERP-01-ACT-SYNC-CREATE", JSON.stringify({ requested_scope: "enterprise-finance" }));
    assertEqual(await readError(), null, "sync create accepted");
    assert((await readField("ERP-01-FLD-SYNC-LAST-SYNC-STATUS") ?? "").includes("COMPLETED"), "sync job completed");
    const snapshotId = await readField("ERP-01-FLD-SYNC-SNAPSHOT-ID");
    assert(snapshotId !== null && snapshotId.startsWith("ERP-SNAP-"), "sync job references the real snapshot");

    // Retry without a FAILED job -> registered sync error.
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-SYNC-RETRY", "ERP-01-ACT-SYNC-RETRY");
    assertEqual((await readError())?.code, "ERP-01-ERR-SYNC", "retry only retry-eligible jobs");

    // Forecast without a registered source -> honest ERR-FINANCE + —.
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-FORECAST", "ERP-01-ACT-FORECAST");
    assertEqual((await readError())?.code, "ERP-01-ERR-FINANCE", "forecast honest missing source");
    assertEqual(await readField("ERP-01-FLD-FIN-FORECAST"), null, "no synthesized forecast");

    // Fact pack records real governed facts; export records the request.
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-FACTPACK", "ERP-01-ACT-FACTPACK");
    const factPack = await readField(ERP_STATE_FACTPACK_UID);
    assert(factPack !== null && factPack.includes("ERP_FINANCE_FACT_PACK"), "fact pack registered");
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-EXPORT", "ERP-01-ACT-EXPORT");
    const exports = JSON.parse((await readField(ERP_STATE_EXPORTS_UID)) ?? "[]") as Array<{ exportId: string; ref: string }>;
    assert(exports.length === 1 && exports[0].ref === "FACT_PACK", "export request recorded with ref");
    assertEqual(await readError(), null, "export clears error");

    // Finance masking: account without finance.read receives masked status.
    const finlessModel = await persistGetErpReadModel(FINLESS);
    assert(finlessModel.authorized, "page scope grants authorized");
    const cost = finlessModel.fields.find((row) => row.controlUid === "ERP-01-FLD-FIN-COST");
    assertEqual(cost?.value, "MASKED（finance.read required）", "finance masked without scope");
    const demoModel = await persistGetErpReadModel(DEMO);
    const demoCost = demoModel.fields.find((row) => row.controlUid === "ERP-01-FLD-FIN-COST");
    assert(demoCost?.value !== "MASKED（finance.read required）", "finance.read sees unmasked fields");

    // DETAIL-OPEN surfaces route-recorded audit events.
    await persistRecordErpAction(DEMO, "ERP-01-BTN-DETAIL", "ERP-01-ACT-DETAIL-OPEN");
    await applyErpWorkbenchAction(DEMO, "ERP-01-BTN-DETAIL", "ERP-01-ACT-DETAIL-OPEN");
    assert((await readField("ERP-01-FLD-AUDIT-REF")) !== null, "audit trail populated");

    // Contract page-state vocabulary derivation (pure function).
    const base = { loading: false, authorized: true, errorCode: null, connectorStatus: null, syncJobsRaw: null, snapshotRaw: null, completenessRaw: null };
    assertEqual(deriveErpPageState({ ...base, loading: true }), "LOADING", "state LOADING");
    assertEqual(deriveErpPageState({ ...base, errorCode: "ERP-01-ERR-VERSION" }), "VERSION_CONFLICT", "state VERSION_CONFLICT");
    assertEqual(deriveErpPageState({ ...base, errorCode: "ERP-01-ERR-SYNC" }), "ERROR", "state ERROR");
    assertEqual(deriveErpPageState({ ...base, authorized: false }), "POLICY_BLOCKED", "state POLICY_BLOCKED");
    assertEqual(deriveErpPageState({ ...base, connectorStatus: "VALIDATING" }), "CONNECTOR_VALIDATING", "state CONNECTOR_VALIDATING");
    assertEqual(deriveErpPageState({ ...base, connectorStatus: "CONFIGURING" }), "CONNECTOR_CONFIGURING", "state CONNECTOR_CONFIGURING");
    assertEqual(
      deriveErpPageState({ ...base, connectorStatus: "READY", syncJobsRaw: JSON.stringify([{ status: "RUNNING" }]) }),
      "SNAPSHOT_SYNCING",
      "state SNAPSHOT_SYNCING",
    );
    assertEqual(
      deriveErpPageState({ ...base, connectorStatus: "READY", syncJobsRaw: JSON.stringify([{ status: "FAILED" }]) }),
      "SNAPSHOT_FAILED",
      "state SNAPSHOT_FAILED",
    );
    assertEqual(deriveErpPageState({ ...base, connectorStatus: "DEGRADED" }), "CONNECTOR_DEGRADED", "state CONNECTOR_DEGRADED");
    assertEqual(deriveErpPageState({ ...base, connectorStatus: "FAILED" }), "CONNECTOR_DEGRADED", "connector FAILED maps to vocabulary");
    assertEqual(
      deriveErpPageState({
        ...base,
        connectorStatus: "READY",
        syncJobsRaw: JSON.stringify([{ status: "COMPLETED", at: "2026-01-02T00:00:00.000Z" }]),
        snapshotRaw: JSON.stringify({ at: "2026-01-01T00:00:00.000Z" }),
        completenessRaw: "100%",
      }),
      "SNAPSHOT_STALE",
      "state SNAPSHOT_STALE",
    );
    assertEqual(
      deriveErpPageState({
        ...base,
        connectorStatus: "READY",
        syncJobsRaw: JSON.stringify([{ status: "COMPLETED", at: "2026-01-01T00:00:00.000Z" }]),
        snapshotRaw: JSON.stringify({ at: "2026-01-01T00:00:00.000Z" }),
        completenessRaw: "50%",
      }),
      "DATA_INCOMPLETE",
      "state DATA_INCOMPLETE",
    );
    assertEqual(
      deriveErpPageState({
        ...base,
        connectorStatus: "READY",
        syncJobsRaw: JSON.stringify([{ status: "COMPLETED", at: "2026-01-01T00:00:00.000Z" }]),
        snapshotRaw: JSON.stringify({ at: "2026-01-01T00:00:00.000Z" }),
        completenessRaw: "100%",
      }),
      "READY",
      "state READY",
    );
    assertEqual(
      deriveErpPageState({ ...base, connectorStatus: null, snapshotRaw: JSON.stringify({ at: "2026-01-01T00:00:00.000Z" }) }),
      "CONNECTOR_UNCONFIGURED",
      "state CONNECTOR_UNCONFIGURED with snapshot",
    );
    assertEqual(deriveErpPageState({ ...base }), "CONNECTOR_UNCONFIGURED", "state CONNECTOR_UNCONFIGURED empty");

    console.log("erp-workbench: all assertions passed");
  } finally {
    await client.run(
      `INSERT INTO ghsn_aiapi_field_projection (control_uid, value_text) VALUES (?, ?)
       ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
      [AIAPI_REGISTRY_UID, registryOriginal],
    );
  }
  process.exit(0);
}

void main();
