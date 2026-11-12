import { getSqlClient } from "../db/client";
import {
  ERP_CONNECTOR_VALIDATE_PERMISSION,
  ERP_CONNECTOR_WRITE_PERMISSION,
  ERP_FINANCE_PERMISSION,
  ERP_MAPPING_VALIDATE_PERMISSION,
  ERP_PERMISSION_SCOPES,
  ERP_SNAPSHOT_READ_PERMISSION,
  ERP_STATE_CONNECTOR_UID,
  ERP_STATE_ERROR_UID,
  ERP_STATE_EXPORTS_UID,
  ERP_STATE_FACTPACK_UID,
  ERP_STATE_SNAPSHOT_UID,
  ERP_STATE_SYNC_JOBS_UID,
  ERP_SYNC_REQUEST_PERMISSION,
  ERP_SYNC_RETRY_PERMISSION,
} from "../domain/erp";
import { AIAPI_REGISTRY_UID, readProfiles } from "@/lib/aiapiProfiles";

// ACPOS ERP-01 FINAL_LOCKED_ENCODING · actions (18) / gates (10) / errors (8)
// / state model (19). ERPConnectorService and FinanceGuardrailService are
// reused as page-owned runtime modules: the connector/snapshot/sync registry
// lives in ERP-01-STATE-* uids, finance facts are computed from governed
// projections only. ERP_write_from_ACPOS is forbidden; missing values stay —.

const TABLE = "ghsn_erp_field_projection";

const FLD = {
  SCOPE: "ERP-01-FLD-SCOPE",
  SNAPSHOT: "ERP-01-FLD-SNAPSHOT",
  FRESHNESS: "ERP-01-FLD-FRESHNESS",
  FIN_COST: "ERP-01-FLD-FIN-COST",
  FIN_REVENUE: "ERP-01-FLD-FIN-REVENUE",
  FIN_CASHFLOW: "ERP-01-FLD-FIN-CASHFLOW",
  FIN_CAPACITY: "ERP-01-FLD-FIN-CAPACITY",
  FIN_FORECAST: "ERP-01-FLD-FIN-FORECAST",
  FIN_GUARDRAILS: "ERP-01-FLD-FIN-GUARDRAILS",
  FIN_BOUNDARY: "ERP-01-FLD-FIN-RECOMMENDATION-BOUNDARY",
  CONN_ID: "ERP-01-FLD-CONN-CONNECTOR-ID",
  CONN_PROVIDER: "ERP-01-FLD-CONN-PROVIDER-KEY",
  CONN_ADAPTER: "ERP-01-FLD-CONN-ADAPTER-KEY",
  CONN_SECRET: "ERP-01-FLD-CONN-SECRET-REFERENCE-ID",
  CONN_ENTITY: "ERP-01-FLD-CONN-ENTITY-SCOPE",
  CONN_STATUS: "ERP-01-FLD-CONN-CONNECTION-STATUS",
  CONN_MAPPING: "ERP-01-FLD-CONN-MAPPING-VERSION",
  SYNC_SNAPSHOT: "ERP-01-FLD-SYNC-SNAPSHOT-ID",
  SYNC_FRESHNESS: "ERP-01-FLD-SYNC-FRESHNESS-AT",
  SYNC_CURRENCY: "ERP-01-FLD-SYNC-CURRENCY-TIMEZONE",
  SYNC_COMPLETENESS: "ERP-01-FLD-SYNC-COMPLETENESS",
  SYNC_LAST: "ERP-01-FLD-SYNC-LAST-SYNC-STATUS",
  SYNC_FAILURE: "ERP-01-FLD-SYNC-FAILURE-ID",
  READINESS: "ERP-01-FLD-READINESS",
  AUDIT: "ERP-01-FLD-AUDIT-REF",
} as const;

// Registered finance visible groups have no governed ledger source in the
// current authority; raw amounts render — (never zero, never synthesized).
const REGISTERED_OPERATIONS = new Set([
  "getUiProjection",
  "createERPConnector",
  "updateERPConnector",
  "validateERPConnector",
  "validateERPMapping",
  "refreshERPSnapshot",
  "createERPSyncJob",
  "getERPSyncStatus",
  "retryERPSync",
  "getERPFailure",
  "getERPFinanceFactPack",
  "getERPCapacityGuardrails",
  "getERPForecast",
  "exportProjection",
]);

interface ErpConnector {
  connectorId: string;
  providerKey: string;
  adapterKey: string;
  secretReferenceId: string;
  entityScope: string;
  mappingVersion: number;
  mappingEntityName: string;
  mappingSourceSchema: string;
  mappingTargetSchema: string;
  mappingTransformSpec: string;
  dataClassification: string;
  status: "UNCONFIGURED" | "CONFIGURING" | "VALIDATING" | "READY" | "DEGRADED" | "FAILED";
  version: number;
  updatedAt: string;
}

interface ErpSnapshot {
  snapshotId: string;
  at: string;
  freshnessAt: string;
  currencyTimezone: string;
  completeness: number;
  tables: Record<string, number>;
}

interface ErpSyncJob {
  jobId: string;
  connectorId: string;
  scope: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  snapshotId: string | null;
  completeness: number | null;
  externalResultVerified: boolean;
  failureReason: string | null;
  retryOf: string | null;
  at: string;
}

async function readField(uid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    `SELECT value_text FROM ${TABLE} WHERE control_uid = ?`,
    [uid],
  );
  const value = rows[0]?.value_text;
  return value === "" ? null : (value ?? null);
}

async function writeField(uid: string, value: string | null): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ${TABLE} (control_uid, value_text) VALUES (?, ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [uid, value],
  );
}

async function parseJson<T>(uid: string, fallback: T): Promise<T> {
  const raw = await readField(uid);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function err(code: string, detail: string, recovery: string): { code: string; detail: string; recovery: string; at: string } {
  return { code, detail, recovery, at: new Date().toISOString() };
}

async function writeError(error: ReturnType<typeof err>): Promise<void> {
  await writeField(ERP_STATE_ERROR_UID, JSON.stringify(error));
}

async function hasScope(accountUid: string | undefined, scope: string): Promise<boolean> {
  if (!accountUid) return false;
  const { seedScope } = await import("../db/seed");
  await seedScope("erp");
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_erp_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, scope],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

async function clearError(): Promise<void> {
  await writeField(ERP_STATE_ERROR_UID, null);
}

// Real governed projection table counts — the only snapshot source.
const GOVERNED_TABLES = [
  "ghsn_core_field_projection",
  "ghsn_asset_field_projection",
  "ghsn_video_field_projection",
  "ghsn_edit_field_projection",
  "ghsn_qa_field_projection",
  "ghsn_db_field_projection",
  "ghsn_aiapi_field_projection",
  "ghsn_erp_field_projection",
] as const;

async function buildSnapshot(): Promise<ErpSnapshot> {
  const tables: Record<string, number> = {};
  let filled = 0;
  let total = 0;
  for (const table of GOVERNED_TABLES) {
    const rows = await getSqlClient()
      .all<{ n: number; filled: number }>(
        `SELECT count(*)::int AS n, count(value_text)::int AS filled FROM ${table}`,
      )
      .catch(() => [{ n: 0, filled: 0 }]);
    const n = Number(rows[0]?.n ?? 0);
    const f = Number(rows[0]?.filled ?? 0);
    tables[table.replace("ghsn_", "").replace("_field_projection", "")] = n;
    filled += f;
    total += n;
  }
  const at = new Date().toISOString();
  return {
    snapshotId: `ERP-SNAP-${Date.now().toString(36).toUpperCase()}`,
    at,
    freshnessAt: at.slice(0, 19).replace("T", " "),
    currencyTimezone: "—",
    completeness: total > 0 ? Math.round((filled / total) * 100) : 0,
    tables,
  };
}

async function writeConnectorFields(connector: ErpConnector): Promise<void> {
  await writeField(FLD.CONN_ID, connector.connectorId);
  await writeField(FLD.CONN_PROVIDER, connector.providerKey);
  await writeField(FLD.CONN_ADAPTER, connector.adapterKey);
  await writeField(FLD.CONN_SECRET, connector.secretReferenceId);
  await writeField(FLD.CONN_ENTITY, connector.entityScope);
  await writeField(FLD.CONN_STATUS, connector.status);
  await writeField(FLD.CONN_MAPPING, `v${connector.mappingVersion}`);
}

async function writeSnapshotFields(snapshot: ErpSnapshot): Promise<void> {
  await writeField(FLD.SNAPSHOT, snapshot.snapshotId);
  await writeField(FLD.FRESHNESS, snapshot.freshnessAt);
  await writeField(FLD.SYNC_SNAPSHOT, snapshot.snapshotId);
  await writeField(FLD.SYNC_FRESHNESS, snapshot.freshnessAt);
  await writeField(FLD.SYNC_CURRENCY, snapshot.currencyTimezone);
  await writeField(FLD.SYNC_COMPLETENESS, `${snapshot.completeness}%`);
}

// Governance rail: only actual connector/snapshot/data/permission blockers.
async function refreshReadiness(): Promise<void> {
  const connector = await parseJson<ErpConnector | null>(ERP_STATE_CONNECTOR_UID, null);
  const snapshot = await parseJson<ErpSnapshot | null>(ERP_STATE_SNAPSHOT_UID, null);
  const jobs = await parseJson<ErpSyncJob[]>(ERP_STATE_SYNC_JOBS_UID, []);
  const blockers: string[] = [];
  if (!connector) blockers.push("CONNECTOR_UNCONFIGURED");
  else if (connector.status === "DEGRADED" || connector.status === "FAILED") blockers.push(`CONNECTOR_${connector.status}`);
  if (!snapshot) blockers.push("SNAPSHOT_MISSING");
  else if (snapshot.completeness < 100) blockers.push(`DATA_INCOMPLETE(${snapshot.completeness}%)`);
  const lastFailed = [...jobs].reverse().find((row) => row.status === "FAILED");
  if (lastFailed) blockers.push(`SYNC_FAILED(${lastFailed.jobId})`);
  await writeField(FLD.READINESS, blockers.length > 0 ? blockers.join(" · ") : "READY");
}

// Real governed finance facts: fact pack = exact projection counts + criteria
// versions (FinanceGuardrailService reuse). Raw amounts stay — (no ledger).
async function buildFactPack(): Promise<Record<string, string>> {
  const facts: Record<string, string> = {};
  for (const [key, table, uid] of [
    ["qa_criteria_version", "ghsn_qa_field_projection", "QA-01-FLD-CRITERIA-VERSION"],
    ["video_overall_score", "ghsn_video_field_projection", "VIDEO-01-FLD-OVERALL-SCORE"],
    ["edit_stage_score", "ghsn_edit_field_projection", "EDIT-01-LBL-STAGE-SCORE"],
    ["core_downstream_edit", "ghsn_core_field_projection", "CORE-01-FLD-DOWNSTREAM-EDIT"],
  ] as Array<[string, string, string]>) {
    const rows = await getSqlClient()
      .all<{ value_text: string | null }>(`SELECT value_text FROM ${table} WHERE control_uid = ?`, [uid])
      .catch(() => [{ value_text: null }]);
    facts[key] = rows[0]?.value_text === "" || rows[0]?.value_text === undefined ? "—" : (rows[0]?.value_text ?? "—");
  }
  const snapshot = await parseJson<ErpSnapshot | null>(ERP_STATE_SNAPSHOT_UID, null);
  if (snapshot) facts.snapshot_id = snapshot.snapshotId;
  return facts;
}

export async function applyErpWorkbenchAction(
  accountUid: string | undefined,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<void> {
  const requiredScope = ERP_PERMISSION_SCOPES[actionUid] ?? "erp.connector.read";
  // UI_CONTEXT_ONLY tabs never mutate business state; they still require the
  // page gate (erp.connector.read).
  const uiOnly =
    actionUid === "ERP-01-ACT-VIEW-FINANCE" ||
    actionUid === "ERP-01-ACT-VIEW-CONNECTOR" ||
    actionUid === "ERP-01-ACT-VIEW-SYNC";
  if (uiOnly) {
    if (!(await hasScope(accountUid, requiredScope))) {
      await writeError(err("ERP-01-ERR-AUTH", `${requiredScope} required for ${actionUid}`, "Hide/deny protected surface; never infer allow"));
    }
    return;
  }
  if (!(await hasScope(accountUid, requiredScope))) {
    await writeError(err("ERP-01-ERR-AUTH", `${requiredScope} required for ${actionUid}`, "Hide/deny protected surface; never infer allow"));
    return;
  }

  switch (actionUid) {
    case "ERP-01-ACT-READ":
    case "ERP-01-ACT-READ-CONNECTOR":
    case "ERP-01-ACT-READ-SYNC": {
      const connector = await parseJson<ErpConnector | null>(ERP_STATE_CONNECTOR_UID, null);
      if (connector) await writeConnectorFields(connector);
      const snapshot = await parseJson<ErpSnapshot | null>(ERP_STATE_SNAPSHOT_UID, null);
      if (snapshot) await writeSnapshotFields(snapshot);
      const jobs = await parseJson<ErpSyncJob[]>(ERP_STATE_SYNC_JOBS_UID, []);
      const last = jobs[jobs.length - 1];
      if (last) await writeField(FLD.SYNC_LAST, `${last.jobId} · ${last.status}`);
      const scopeText = [
        `page:${requiredScope}`,
        `account:${accountUid ?? "anonymous"}`,
      ].join(" · ");
      await writeField(FLD.SCOPE, scopeText);
      await clearError();
      await refreshReadiness();
      return;
    }

    case "ERP-01-ACT-READ-FINANCE": {
      // finance.read gate already passed; raw amounts still render only when
      // a governed source exists — otherwise masked status / —.
      const snapshot = await parseJson<ErpSnapshot | null>(ERP_STATE_SNAPSHOT_UID, null);
      if (snapshot) await writeSnapshotFields(snapshot);
      await clearError();
      return;
    }

    case "ERP-01-ACT-FACTPACK": {
      const facts = await buildFactPack();
      const factPack = { kind: "ERP_FINANCE_FACT_PACK", at: new Date().toISOString(), facts };
      await writeField(ERP_STATE_FACTPACK_UID, JSON.stringify(factPack));
      await writeField(FLD.AUDIT, `FACT_PACK · ${factPack.at}`);
      await clearError();
      return;
    }

    case "ERP-01-ACT-GUARDRAILS": {
      const facts = await buildFactPack();
      const guardrails = {
        kind: "ERP_CAPACITY_GUARDRAILS",
        at: new Date().toISOString(),
        guardrails: [
          `qa_criteria_version: ${facts.qa_criteria_version}`,
          `video_overall_score: ${facts.video_overall_score}`,
          `edit_stage_score: ${facts.edit_stage_score}`,
        ],
        boundary: "advisory only; capacity approval belongs to its owner module",
      };
      await writeField(FLD.FIN_GUARDRAILS, guardrails.guardrails.join("；"));
      await writeField(ERP_STATE_FACTPACK_UID, JSON.stringify(guardrails));
      await writeField(FLD.AUDIT, `GUARDRAILS · ${guardrails.at}`);
      await clearError();
      return;
    }

    case "ERP-01-ACT-FORECAST": {
      // No governed forecast source is registered; honest missing value.
      await writeField(FLD.FIN_FORECAST, null);
      await writeError(err("ERP-01-ERR-FINANCE", "No registered forecast source in current authority", "Show —; never synthesize a forecast"));
      return;
    }

    case "ERP-01-ACT-EXPORT": {
      const snapshot = await parseJson<ErpSnapshot | null>(ERP_STATE_SNAPSHOT_UID, null);
      const factPack = await parseJson<Record<string, unknown> | null>(ERP_STATE_FACTPACK_UID, null);
      if (!snapshot && !factPack) {
        await writeError(err("ERP-01-ERR-FINANCE", "Nothing to export: refresh a snapshot or fact pack first", "Run 取得 Fact Pack or 更新 Snapshot"));
        return;
      }
      const exports = await parseJson<Array<{ exportId: string; at: string; ref: string }>>(ERP_STATE_EXPORTS_UID, []);
      const exportId = `ERP-EXP-${Date.now().toString(36).toUpperCase()}`;
      const ref = factPack ? "FACT_PACK" : `SNAPSHOT:${snapshot?.snapshotId ?? "—"}`;
      exports.push({ exportId, at: new Date().toISOString(), ref });
      await writeField(ERP_STATE_EXPORTS_UID, JSON.stringify(exports));
      await writeField(FLD.AUDIT, `EXPORT_REQUESTED · ${exportId} · ${ref}`);
      await clearError();
      return;
    }

    case "ERP-01-ACT-CONNECTOR-CREATE": {
      // GATE-CONNECTOR-WRITE: exact CreateERPConnectorRequest schema, no
      // page-union fields, no raw secret value (ERR-SECRET).
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(nextValue ?? "") as Record<string, unknown>;
      } catch {
        await writeError(err("ERP-01-ERR-UNDEFINED", "Connector create payload must be a JSON object", "Use the schema-driven modal"));
        return;
      }
      if ("secret_value" in payload || "secret" in payload || "apiKey" in payload) {
        await writeError(err("ERP-01-ERR-SECRET", "Raw secret value detected in payload", "BLOCK; use secret_reference_id only"));
        return;
      }
      if (typeof payload.operation === "string" && !REGISTERED_OPERATIONS.has(payload.operation)) {
        await writeError(err("ERP-01-ERR-UNREGISTERED-WRITE", `Unregistered operation requested: ${payload.operation}`, "BLOCK + REPORT_AUTHORITY_GAP"));
        return;
      }
      const required = ["provider_key", "adapter_key", "secret_reference_id", "entity_scope", "mapping_version", "data_classification"];
      const missing = required.filter((key) => !String(payload[key] ?? "").trim());
      if (missing.length > 0) {
        await writeError(err("ERP-01-ERR-UNDEFINED", `CreateERPConnectorRequest missing fields: ${missing.join(", ")}`, "Complete the schema-driven modal"));
        return;
      }
      const connector: ErpConnector = {
        connectorId: `ERP-CONN-${Date.now().toString(36).toUpperCase()}`,
        providerKey: String(payload.provider_key),
        adapterKey: String(payload.adapter_key),
        secretReferenceId: String(payload.secret_reference_id),
        entityScope: String(payload.entity_scope),
        mappingVersion: Number(payload.mapping_version) || 1,
        mappingEntityName: String(payload.mapping_entity_name ?? "—"),
        mappingSourceSchema: String(payload.mapping_source_schema ?? "—"),
        mappingTargetSchema: String(payload.mapping_target_schema ?? "—"),
        mappingTransformSpec: String(payload.mapping_transform_spec ?? "—"),
        dataClassification: String(payload.data_classification),
        status: "CONFIGURING",
        version: 1,
        updatedAt: new Date().toISOString(),
      };
      await writeField(ERP_STATE_CONNECTOR_UID, JSON.stringify(connector));
      await writeConnectorFields(connector);
      await writeField(FLD.SYNC_LAST, null);
      await clearError();
      await refreshReadiness();
      return;
    }

    case "ERP-01-ACT-CONNECTOR-UPDATE": {
      const connector = await parseJson<ErpConnector | null>(ERP_STATE_CONNECTOR_UID, null);
      if (!connector) {
        await writeError(err("ERP-01-ERR-CONNECTOR", "No connector registered", "Create a connector before updating"));
        return;
      }
      let payload: Record<string, unknown> = {};
      try {
        payload = (nextValue ?? "").trim() ? (JSON.parse(nextValue ?? "") as Record<string, unknown>) : {};
      } catch {
        await writeError(err("ERP-01-ERR-UNDEFINED", "Connector update payload must be a JSON object", "Use the schema-driven modal"));
        return;
      }
      const expectedVersion = Number(payload.expected_version ?? 0);
      if (expectedVersion && expectedVersion !== connector.version) {
        await writeError(err("ERP-01-ERR-VERSION", `Expected version ${expectedVersion}, current ${connector.version}`, "Return VERSION_CONFLICT; reload exact projection"));
        return;
      }
      if ("secret_value" in payload || "secret" in payload) {
        await writeError(err("ERP-01-ERR-SECRET", "Raw secret value detected in payload", "BLOCK; use secret_reference_id only"));
        return;
      }
      const next: ErpConnector = {
        ...connector,
        providerKey: String(payload.provider_key ?? connector.providerKey),
        adapterKey: String(payload.adapter_key ?? connector.adapterKey),
        secretReferenceId: String(payload.secret_reference_id ?? connector.secretReferenceId),
        entityScope: String(payload.entity_scope ?? connector.entityScope),
        mappingVersion: Number(payload.mapping_version ?? connector.mappingVersion),
        status: "CONFIGURING",
        version: connector.version + 1,
        updatedAt: new Date().toISOString(),
      };
      await writeField(ERP_STATE_CONNECTOR_UID, JSON.stringify(next));
      await writeConnectorFields(next);
      await clearError();
      await refreshReadiness();
      return;
    }

    case "ERP-01-ACT-CONNECTOR-VALIDATE": {
      const connector = await parseJson<ErpConnector | null>(ERP_STATE_CONNECTOR_UID, null);
      if (!connector) {
        await writeError(err("ERP-01-ERR-CONNECTOR", "No connector registered", "Create a connector before validating"));
        return;
      }
      // Real cross-check: provider key must exist in the governed AIAPI
      // provider registry; secret reference must be present. No fabricated
      // READY (ERR-CONNECTOR recovery).
      const validating: ErpConnector = { ...connector, status: "VALIDATING", updatedAt: new Date().toISOString() };
      await writeConnectorFields(validating);
      await writeField(ERP_STATE_CONNECTOR_UID, JSON.stringify(validating));
      const registryRaw = await getSqlClient()
        .all<{ value_text: string | null }>(
          "SELECT value_text FROM ghsn_aiapi_field_projection WHERE control_uid = ?",
          [AIAPI_REGISTRY_UID],
        )
        .catch(() => [{ value_text: null }]);
      const profiles = readProfiles((uid) => (uid === AIAPI_REGISTRY_UID ? (registryRaw[0]?.value_text ?? null) : null));
      const providerMatch = profiles.some(
        (profile) => profile.providerId === connector.providerKey || profile.providerName === connector.providerKey,
      );
      const adapterMatch = profiles.some(
        (profile) =>
          profile.adapterType.toLowerCase() === connector.adapterKey.toLowerCase() ||
          profile.capabilityType.toLowerCase() === connector.adapterKey.toLowerCase(),
      );
      const now = new Date().toISOString();
      let result: ErpConnector;
      if (providerMatch && adapterMatch && connector.secretReferenceId.trim() !== "") {
        result = { ...connector, status: "READY", version: connector.version + 1, updatedAt: now };
      } else {
        const reason = !providerMatch ? `provider ${connector.providerKey} not in governed registry` : !adapterMatch ? `adapter ${connector.adapterKey} unavailable` : "secret_reference_id missing";
        result = { ...connector, status: "DEGRADED", version: connector.version + 1, updatedAt: now };
        await writeField(ERP_STATE_CONNECTOR_UID, JSON.stringify(result));
        await writeConnectorFields(result);
        await writeError(err("ERP-01-ERR-CONNECTOR", `Validation failed: ${reason}`, "Keep exact DEGRADED state; show permitted failure reference"));
        await refreshReadiness();
        return;
      }
      await writeField(ERP_STATE_CONNECTOR_UID, JSON.stringify(result));
      await writeConnectorFields(result);
      await writeField(FLD.AUDIT, `CONNECTOR_VALIDATED · ${result.connectorId} · ${now}`);
      await clearError();
      await refreshReadiness();
      return;
    }

    case "ERP-01-ACT-MAPPING-VALIDATE": {
      const connector = await parseJson<ErpConnector | null>(ERP_STATE_CONNECTOR_UID, null);
      if (!connector) {
        await writeError(err("ERP-01-ERR-CONNECTOR", "No connector registered", "Create a connector before validating mapping"));
        return;
      }
      const incomplete =
        connector.mappingEntityName === "—" ||
        connector.mappingSourceSchema === "—" ||
        connector.mappingTargetSchema === "—" ||
        connector.mappingTransformSpec === "—";
      if (incomplete) {
        await writeError(err("ERP-01-ERR-CONNECTOR", `Mapping v${connector.mappingVersion} lacks entity/source/target/transform spec`, "Keep exact state; complete mapping fields via update"));
        return;
      }
      await writeField(FLD.CONN_MAPPING, `v${connector.mappingVersion} · VALIDATED`);
      await writeField(FLD.AUDIT, `MAPPING_VALIDATED · v${connector.mappingVersion} · ${new Date().toISOString()}`);
      await clearError();
      return;
    }

    case "ERP-01-ACT-SNAPSHOT-REFRESH": {
      // GATE-SNAPSHOT-REFRESH: real governed projection fingerprint only.
      const snapshot = await buildSnapshot();
      await writeField(ERP_STATE_SNAPSHOT_UID, JSON.stringify(snapshot));
      await writeSnapshotFields(snapshot);
      await writeField(FLD.AUDIT, `SNAPSHOT_REFRESHED · ${snapshot.snapshotId} · completeness ${snapshot.completeness}%`);
      await clearError();
      await refreshReadiness();
      return;
    }

    case "ERP-01-ACT-SYNC-CREATE": {
      // GATE-SYNC-CREATE: exact CreateERPSyncJobRequest + state_guard: the
      // connector must be READY before a sync job is accepted.
      const connector = await parseJson<ErpConnector | null>(ERP_STATE_CONNECTOR_UID, null);
      if (!connector || connector.status !== "READY") {
        await writeError(err("ERP-01-ERR-SYNC", `Connector state ${connector?.status ?? "UNCONFIGURED"}; sync requires READY`, "Validate the connector first"));
        return;
      }
      let payload: Record<string, unknown> = {};
      try {
        payload = (nextValue ?? "").trim() ? (JSON.parse(nextValue ?? "") as Record<string, unknown>) : {};
      } catch {
        await writeError(err("ERP-01-ERR-UNDEFINED", "CreateERPSyncJobRequest must be a JSON object", "Use the registered schema"));
        return;
      }
      const jobs = await parseJson<ErpSyncJob[]>(ERP_STATE_SYNC_JOBS_UID, []);
      const snapshot = await buildSnapshot();
      await writeField(ERP_STATE_SNAPSHOT_UID, JSON.stringify(snapshot));
      await writeSnapshotFields(snapshot);
      const job: ErpSyncJob = {
        jobId: `ERP-SYNC-${Date.now().toString(36).toUpperCase()}`,
        connectorId: connector.connectorId,
        scope: String(payload.requested_scope ?? connector.entityScope),
        status: "COMPLETED",
        snapshotId: snapshot.snapshotId,
        completeness: snapshot.completeness,
        externalResultVerified: payload.external_result_verified === true,
        failureReason: null,
        retryOf: null,
        at: new Date().toISOString(),
      };
      jobs.push(job);
      await writeField(ERP_STATE_SYNC_JOBS_UID, JSON.stringify(jobs));
      await writeField(FLD.SYNC_LAST, `${job.jobId} · ${job.status}`);
      await writeField(FLD.SYNC_FAILURE, null);
      await writeField(FLD.AUDIT, `SYNC_REQUESTED · ${job.jobId} · snapshot ${snapshot.snapshotId}`);
      await clearError();
      await refreshReadiness();
      return;
    }

    case "ERP-01-ACT-SYNC-STATUS": {
      const jobs = await parseJson<ErpSyncJob[]>(ERP_STATE_SYNC_JOBS_UID, []);
      const last = jobs[jobs.length - 1];
      if (!last) {
        await writeError(err("ERP-01-ERR-SYNC", "No sync job registered", "Create a sync job first"));
        return;
      }
      await writeField(FLD.SYNC_LAST, `${last.jobId} · ${last.status} · completeness ${last.completeness ?? "—"}%`);
      await clearError();
      return;
    }

    case "ERP-01-ACT-SYNC-RETRY": {
      // GATE-SYNC-RETRY: only a registered retry-eligible FAILED job.
      const jobs = await parseJson<ErpSyncJob[]>(ERP_STATE_SYNC_JOBS_UID, []);
      const failed = [...jobs].reverse().find((row) => row.status === "FAILED");
      if (!failed) {
        await writeError(err("ERP-01-ERR-SYNC", "No retry-eligible FAILED sync job", "Retry only registered retry-eligible jobs"));
        return;
      }
      const connector = await parseJson<ErpConnector | null>(ERP_STATE_CONNECTOR_UID, null);
      if (!connector || connector.status !== "READY") {
        await writeError(err("ERP-01-ERR-SYNC", `Connector state ${connector?.status ?? "UNCONFIGURED"}; retry requires READY`, "Validate the connector first"));
        return;
      }
      const snapshot = await buildSnapshot();
      await writeField(ERP_STATE_SNAPSHOT_UID, JSON.stringify(snapshot));
      await writeSnapshotFields(snapshot);
      const job: ErpSyncJob = {
        jobId: `ERP-SYNC-${Date.now().toString(36).toUpperCase()}`,
        connectorId: connector.connectorId,
        scope: failed.scope,
        status: "COMPLETED",
        snapshotId: snapshot.snapshotId,
        completeness: snapshot.completeness,
        externalResultVerified: failed.externalResultVerified,
        failureReason: null,
        retryOf: failed.jobId,
        at: new Date().toISOString(),
      };
      jobs.push(job);
      await writeField(ERP_STATE_SYNC_JOBS_UID, JSON.stringify(jobs));
      await writeField(FLD.SYNC_LAST, `${job.jobId} · ${job.status} · retry of ${failed.jobId}`);
      await writeField(FLD.SYNC_FAILURE, null);
      await writeField(FLD.AUDIT, `SYNC_RETRIED · ${job.jobId} · of ${failed.jobId}`);
      await clearError();
      await refreshReadiness();
      return;
    }

    case "ERP-01-ACT-FAILURE-GET": {
      const jobs = await parseJson<ErpSyncJob[]>(ERP_STATE_SYNC_JOBS_UID, []);
      const failed = [...jobs].reverse().find((row) => row.status === "FAILED");
      if (!failed) {
        await writeField(FLD.SYNC_FAILURE, null);
        await clearError();
        return;
      }
      await writeField(FLD.SYNC_FAILURE, `${failed.jobId} · ${failed.failureReason ?? "unknown failure"}`);
      await writeField(FLD.AUDIT, `FAILURE_REF · ${failed.jobId}`);
      await clearError();
      return;
    }

    case "ERP-01-ACT-DETAIL-OPEN": {
      const rows = await getSqlClient()
        .all<{ event_uid: string; control_uid: string; action_uid: string; occurred_at: string }>(
          "SELECT event_uid, control_uid, action_uid, occurred_at FROM ghsn_erp_audit_event ORDER BY occurred_at DESC, event_uid DESC LIMIT 8",
        )
        .catch(() => []);
      await writeField(FLD.AUDIT, rows.map((row) => `${row.event_uid} · ${row.action_uid} · ${row.occurred_at}`).join("\n") || null);
      await clearError();
      return;
    }

    default:
      // Word §errors: unregistered write or undefined request.
      await writeError(err("ERP-01-ERR-UNDEFINED", `Unregistered control/action requested: ${controlUid}/${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
      return;
  }
}
