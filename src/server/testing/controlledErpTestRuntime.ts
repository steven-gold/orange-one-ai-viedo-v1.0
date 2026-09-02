import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import type { InfoRequest } from "@/server/info/infoCommandRuntime";

const TEST_METADATA = {
  data_classification: "TEST_ONLY",
  synthetic: true,
  test_dataset_id: "TEST-ERP-01",
  test_run_id: "TEST-RUN-ERP-01-CONTROLLED",
  created_for_validation: true,
  production_eligible: false,
} as const;

const CONTROLLED_FORM_SCHEMAS = {
  "ERP-01-BTN-CONNECTOR-CREATE": [
    { key: "provider_key", type: "text", required: true },
    { key: "adapter_key", type: "text", required: true },
    { key: "secret_reference_id", type: "text", required: true },
    { key: "entity_scope", type: "text", required: true },
    { key: "mapping_version", type: "number", required: true },
    { key: "mapping_entity_name", type: "text", required: true },
    { key: "mapping_source_schema", type: "text", required: true },
    { key: "mapping_target_schema", type: "text", required: true },
    { key: "mapping_transform_spec", type: "text", required: true },
    { key: "data_classification", type: "text", required: true },
  ],
  "ERP-01-BTN-CONNECTOR-UPDATE": [
    { key: "entity_scope", type: "text", required: false },
    { key: "mapping_entity_name", type: "text", required: false },
    { key: "mapping_source_schema", type: "text", required: false },
    { key: "mapping_target_schema", type: "text", required: false },
    { key: "mapping_transform_spec", type: "text", required: false },
    { key: "data_classification", type: "text", required: false },
  ],
  "ERP-01-BTN-SNAPSHOT-REFRESH": [
    { key: "requested_scope", type: "text", required: true },
  ],
  "ERP-01-BTN-SYNC-CREATE": [
    { key: "requested_scope", type: "text", required: true },
    { key: "data_classification", type: "text", required: true },
    { key: "records_payload", type: "text", required: true },
    { key: "snapshot_type", type: "select", required: true, options: ["delta", "full"] },
    { key: "snapshot_document", type: "text", required: true },
    { key: "completeness", type: "text", required: true },
    { key: "external_result_verified", type: "select", required: true, options: ["false", "true"] },
    { key: "external_evidence_refs", type: "text", required: true },
  ],
  "ERP-01-BTN-EXPORT": [
    { key: "scope", type: "text", required: true },
  ],
} as const;

type ConnectorState = "UNCONFIGURED" | "CONFIGURING" | "VALIDATING" | "READY" | "DEGRADED";
type SnapshotState = "SNAPSHOT_STALE" | "SNAPSHOT_SYNCING" | "SNAPSHOT_FAILED";
type SyncJobState = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

type Mapping = {
  entity_name: string;
  source_schema: string;
  target_schema: string;
  transform_spec: string;
  data_classification: string;
};

type Connector = {
  connector_id: string;
  provider_key: string;
  adapter_key: string;
  secret_reference_id: string;
  entity_scope: string;
  mapping_version: number;
  connection_status: ConnectorState;
  mapping: Mapping;
  version: number;
};

type Snapshot = {
  snapshot_id: string;
  freshness_at: string;
  currency: string;
  timezone: string;
  completeness: string;
  last_sync_status: SnapshotState;
  failure_id: string | null;
  version: number;
};

type SyncJob = {
  job_id: string;
  erp_connector_id: string;
  requested_scope: string;
  data_classification: string;
  records_payload: string;
  snapshot_type: string;
  snapshot_document: string;
  completeness: string;
  external_result_verified: boolean;
  external_evidence_refs: string[];
  state: SyncJobState;
  version: number;
};

type FailureRecord = {
  failure_id: string;
  sync_job_ref: string;
  reason: string;
  retry_eligible: boolean;
  version: number;
};

type FinanceModel = {
  cost: string;
  revenue: string;
  cashflow: string;
  capacity: string;
  forecast: string;
  guardrails: string;
  recommendation_boundary: string;
};

type AuditEntry = {
  audit_ref: string;
  event: string;
  subject_ref: string;
  correlation_id: string;
  outcome: "SUCCESS" | "DENIED" | "ERROR";
  reason_code?: string;
};

type ControlledState = {
  connector: Connector | null;
  snapshot: Snapshot | null;
  sync_jobs: SyncJob[];
  failures: FailureRecord[];
  finance: FinanceModel;
  audits: AuditEntry[];
  audit_counter: number;
  idempotency: Map<string, { ok: boolean; value?: unknown; reason_code?: string; status?: number }>;
  entity_counter: number;
};

const state: ControlledState = {
  connector: null,
  snapshot: null,
  sync_jobs: [],
  failures: [],
  finance: {
    cost: "[TEST] authorized provider cost status · masked quote on record",
    revenue: "[TEST] provider revenue · read-only status",
    cashflow: "[TEST] cashflow status · read-only projection",
    capacity: "[TEST] capacity guardrail · within governed bound",
    forecast: "[TEST] next period forecast · read model ready",
    guardrails: "[TEST] governed finance guardrails · read-only",
    recommendation_boundary: "[TEST] recommendation boundary · read-only",
  },
  audits: [],
  audit_counter: 0,
  idempotency: new Map(),
  entity_counter: 0,
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
function textList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
}
function numberValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value.trim());
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}
function boolValue(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (value === "true" || value === "1") return true;
  if (value === "false" || value === "0") return false;
  return null;
}

const DEFAULT_MAPPING: Mapping = {
  entity_name: "finance_ledger",
  source_schema: "erp_source_schema",
  target_schema: "acpos_target_schema",
  transform_spec: "governed transform spec",
  data_classification: "internal",
};

function seedFixture() {
  if (state.connector) return;
  state.connector = {
    connector_id: "TEST-ERP-CONNECTOR-001",
    provider_key: "test-erp-provider",
    adapter_key: "test-erp-adapter",
    secret_reference_id: "SEC-REF-TEST-ERP-001",
    entity_scope: "finance-ledger",
    mapping_version: 2,
    connection_status: "CONFIGURING",
    mapping: { ...DEFAULT_MAPPING },
    version: 2,
  };
  state.snapshot = {
    snapshot_id: "TEST-ERP-SNAPSHOT-001",
    freshness_at: "2026-08-29T09:00:00Z",
    currency: "TWD",
    timezone: "Asia/Taipei",
    completeness: "78%",
    last_sync_status: "SNAPSHOT_STALE",
    failure_id: null,
    version: 1,
  };
  state.sync_jobs.push(
    { job_id: "TEST-ERP-SYNC-001", erp_connector_id: "TEST-ERP-CONNECTOR-001", requested_scope: "finance-ledger", data_classification: "internal", records_payload: "incremental records", snapshot_type: "delta", snapshot_document: "TEST_ONLY delta snapshot document", completeness: "78%", external_result_verified: false, external_evidence_refs: ["evidence ref recorded"], state: "FAILED", version: 1 },
    { job_id: "TEST-ERP-SYNC-002", erp_connector_id: "TEST-ERP-CONNECTOR-001", requested_scope: "finance-ledger", data_classification: "internal", records_payload: "snapshot records", snapshot_type: "full", snapshot_document: "TEST_ONLY full snapshot document", completeness: "78%", external_result_verified: false, external_evidence_refs: ["evidence ref recorded"], state: "COMPLETED", version: 1 },
  );
  state.failures.push(
    { failure_id: "TEST-ERP-FAILURE-001", sync_job_ref: "TEST-ERP-SYNC-001", reason: "connector validation pending before snapshot continuation", retry_eligible: true, version: 1 },
  );
}

function appendAudit(entry: Omit<AuditEntry, "audit_ref">): AuditEntry {
  state.audit_counter += 1;
  const full: AuditEntry = { ...entry, audit_ref: `TEST-ERP01-AUDIT-${String(state.audit_counter).padStart(3, "0")}` };
  state.audits = [full, ...state.audits].slice(0, 10);
  return full;
}
function lastAudit(): AuditEntry | null {
  return state.audits[0] ?? null;
}
function nextEntityId(prefix: string): string {
  while (true) {
    state.entity_counter += 1;
    const id = `TEST-ERP-${prefix}-${String(state.entity_counter).padStart(3, "0")}`;
    const exists =
      state.connector?.connector_id === id ||
      state.snapshot?.snapshot_id === id ||
      state.sync_jobs.some(item => item.job_id === id) ||
      state.failures.some(item => item.failure_id === id);
    if (!exists) return id;
  }
}
function findSyncJob(id: string | null): SyncJob | null {
  return id ? state.sync_jobs.find(item => item.job_id === id) ?? null : null;
}
function findFailure(id: string | null): FailureRecord | null {
  return id ? state.failures.find(item => item.failure_id === id) ?? null : null;
}
function retryEligibleJob(): SyncJob | null {
  return state.sync_jobs.find(item => item.state === "FAILED") ?? null;
}
function latestSyncJob(): SyncJob | null {
  return state.sync_jobs[state.sync_jobs.length - 1] ?? null;
}
function latestFailure(): FailureRecord | null {
  return state.failures[0] ?? null;
}
function latestAuditRef(): string {
  const last = lastAudit();
  return last ? `${last.audit_ref} · ${last.event.replace(/\./g, " ")} · ${last.subject_ref} · ${last.outcome}` : "No governance actions yet";
}

function gateState(): Record<string, boolean> {
  const connector = state.connector;
  const connectorMutable = connector !== null && (connector.connection_status === "CONFIGURING" || connector.connection_status === "VALIDATING" || connector.connection_status === "READY" || connector.connection_status === "DEGRADED");
  return {
    "ERP-01-GATE-PAGE": true,
    "ERP-01-GATE-FINANCE": true,
    "ERP-01-GATE-CONNECTOR-READ": Boolean(connector),
    "ERP-01-GATE-CONNECTOR-WRITE": connectorMutable || connector === null,
    "ERP-01-GATE-CONNECTOR-VALIDATE": connector !== null && (connector.connection_status === "CONFIGURING" || connector.connection_status === "VALIDATING"),
    "ERP-01-GATE-MAPPING-VALIDATE": Boolean(connector) && connector?.mapping_version != null,
    "ERP-01-GATE-SYNC-READ": Boolean(connector) && Boolean(state.snapshot),
    "ERP-01-GATE-SNAPSHOT-REFRESH": Boolean(connector),
    "ERP-01-GATE-SYNC-CREATE": Boolean(connector),
    "ERP-01-GATE-SYNC-RETRY": Boolean(retryEligibleJob()),
  };
}

function projectionValues(): Record<string, string> {
  const connector = state.connector;
  const snapshot = state.snapshot;
  const failure = latestFailure();
  const job = latestSyncJob();
  const connectorStateLabel = connector ? connector.connection_status.replace(/_/g, " ") : "not configured";
  const connectorStatus = connector ? `${connector.connector_id} · ${connectorStateLabel} · mapping v${connector.mapping_version}` : "—";
  const syncStatus = snapshot ? `${snapshot.last_sync_status.replace(/_/g, " ")} · freshness ${snapshot.freshness_at}` : "—";

  return {
    "ERP-01-FLD-SCOPE": connector ? `Current ERP workspace · v${connector.version} · ${connector.entity_scope}` : "Current ERP workspace · governed scope",
    "ERP-01-FLD-SNAPSHOT": snapshot ? `${snapshot.snapshot_id} · ${snapshot.last_sync_status.replace(/_/g, " ")}` : "—",
    "ERP-01-FLD-FRESHNESS": snapshot ? `${snapshot.freshness_at} · ${snapshot.currency} ${snapshot.timezone}` : "—",
    "ERP-01-FLD-FIN-COST": state.finance.cost,
    "ERP-01-FLD-FIN-REVENUE": state.finance.revenue,
    "ERP-01-FLD-FIN-CASHFLOW": state.finance.cashflow,
    "ERP-01-FLD-FIN-CAPACITY": state.finance.capacity,
    "ERP-01-FLD-FIN-FORECAST": state.finance.forecast,
    "ERP-01-FLD-FIN-GUARDRAILS": state.finance.guardrails,
    "ERP-01-FLD-FIN-RECOMMENDATION-BOUNDARY": state.finance.recommendation_boundary,
    "ERP-01-FLD-CONN-CONNECTOR-ID": connector?.connector_id ?? "—",
    "ERP-01-FLD-CONN-PROVIDER-KEY": connector?.provider_key ?? "—",
    "ERP-01-FLD-CONN-ADAPTER-KEY": connector?.adapter_key ?? "—",
    "ERP-01-FLD-CONN-SECRET-REFERENCE-ID": connector?.secret_reference_id ?? "—",
    "ERP-01-FLD-CONN-ENTITY-SCOPE": connector?.entity_scope ?? "—",
    "ERP-01-FLD-CONN-CONNECTION-STATUS": connector ? connectorStateLabel : "—",
    "ERP-01-FLD-CONN-MAPPING-VERSION": connector ? `v${connector.mapping_version} · ${connector.mapping.entity_name}` : "—",
    "ERP-01-FLD-SYNC-SNAPSHOT-ID": snapshot?.snapshot_id ?? "—",
    "ERP-01-FLD-SYNC-FRESHNESS-AT": snapshot?.freshness_at ?? "—",
    "ERP-01-FLD-SYNC-CURRENCY-TIMEZONE": snapshot ? `${snapshot.currency} · ${snapshot.timezone}` : "—",
    "ERP-01-FLD-SYNC-COMPLETENESS": snapshot?.completeness ?? "—",
    "ERP-01-FLD-SYNC-LAST-SYNC-STATUS": snapshot ? snapshot.last_sync_status.replace(/_/g, " ") : "—",
    "ERP-01-FLD-SYNC-FAILURE-ID": failure ? `${failure.failure_id} · ${failure.sync_job_ref} · ${failure.reason}` : snapshot?.failure_id ?? "no failure recorded",
    "ERP-01-FLD-READINESS": `${connectorStatus} · ${syncStatus} · ${state.sync_jobs.filter(item => item.state === "FAILED").length} failed job${state.sync_jobs.filter(item => item.state === "FAILED").length === 1 ? "" : "s"}`,
    "ERP-01-FLD-AUDIT-REF": latestAuditRef(),
  };
}

export function isControlledErpServerTestMode() {
  return isControlledTestMode();
}

export function readControlledErpTestProjection() {
  seedFixture();
  const connector = state.connector;
  const snapshot = state.snapshot;
  const job = retryEligibleJob() ?? latestSyncJob();
  const failure = latestFailure();
  return {
    page_state: "READY",
    values: projectionValues(),
    gate_state: gateState(),
    selected: {
      connector_id: connector?.connector_id ?? "",
      connector_version: connector ? String(connector.version) : "0",
      mapping_version: connector ? String(connector.mapping_version) : "0",
      snapshot_version: snapshot ? String(snapshot.version) : "0",
      sync_job_id: job?.job_id ?? "",
      sync_job_version: job ? String(job.version) : "1",
      failure_id: failure?.failure_id ?? "",
      failure_version: failure ? String(failure.version) : "1",
      requested_scope: connector?.entity_scope ?? "finance-ledger",
      data_classification: connector?.mapping.data_classification ?? "internal",
    },
    form_schemas: CONTROLLED_FORM_SCHEMAS,
    test_metadata: TEST_METADATA,
  };
}

export type ErpCommandOperation =
  | "createERPConnector" | "updateERPConnector" | "validateERPConnector" | "validateERPMapping"
  | "refreshERPSnapshot" | "createERPSyncJob" | "getERPSyncStatus" | "retryERPSync" | "getERPFailure"
  | "getERPFinanceFactPack" | "getERPCapacityGuardrails" | "getERPForecast"
  | "exportProjection" | "refreshProjection";

export type ErpRuntimeRequest = {
  operation_id: ErpCommandOperation;
  correlation_id: string;
  path_params: Record<string, string>;
  payload: unknown;
};

export type ErpRuntimeResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; status: number; reason_code: string; correlation_id: string };

type GateFailure = { ok: false; status: number; reason_code: string };

function fail(reason_code: string, status = 403): GateFailure {
  return { ok: false, status, reason_code };
}

function additionalPropertiesGuard(payload: Record<string, unknown>, allowed: readonly string[]): GateFailure | null {
  const set = new Set(allowed);
  for (const key of Object.keys(payload)) if (!set.has(key)) return fail("ERP01_ADDITIONAL_PROPERTY_FORBIDDEN", 400);
  return null;
}
function requiredBoolean(payload: Record<string, unknown>, key: string): GateFailure | null {
  if (!Object.prototype.hasOwnProperty.call(payload, key) || boolValue(payload[key]) === null) return fail("ERP01_REQUIRED_SYNC_FIELD_MISSING", 400);
  return null;
}

function idempotencyGuard(payload: Record<string, unknown>): GateFailure | null {
  if (!text(payload.idempotency_key)) return fail("ERP01_IDEMPOTENCY_KEY_REQUIRED", 400);
  return null;
}
function expectedVersionOf(payload: Record<string, unknown>): number | null {
  const raw = payload.expected_version ?? payload.expected_source_version ?? payload.expected_resource_version;
  if (raw === undefined || raw === null) return null;
  const version = Number(raw);
  return Number.isFinite(version) ? version : -1;
}
function versionGuard(payload: Record<string, unknown>, actual: number | null): GateFailure | null {
  const expected = expectedVersionOf(payload);
  if (expected === null) return fail("ERP01_EXPECTED_VERSION_MISSING", 400);
  if (actual === null || expected !== actual) return fail("ERP01_VERSION_CONFLICT", 409);
  return null;
}

function evaluateGates(operation: ErpCommandOperation, request: ErpRuntimeRequest): GateFailure | null {
  const payload = record(request.payload);
  const pathId = text(request.path_params?.id) ?? text(request.path_params?.jobId) ?? text(request.path_params?.failureId) ?? null;
  const connector = state.connector;
  for (const forbidden of ["secret","secret_value","raw_secret","credential_value","api_key"]) {
    if (Object.prototype.hasOwnProperty.call(payload, forbidden)) return fail("ERP01_SECRET_VALUE_FORBIDDEN", 400);
  }
  switch (operation) {
    case "createERPConnector": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const extra = additionalPropertiesGuard(payload, ["provider_key","adapter_key","secret_reference_id","entity_scope","mapping_version","mapping_entity_name","mapping_source_schema","mapping_target_schema","mapping_transform_spec","data_classification","scope","expected_version","correlation_id","idempotency_key"]); if (extra) return extra;
      if (connector) return fail("ERP01_CONNECTOR_STATE_GUARD_REJECTED");
      const vg = versionGuard(payload, 0); if (vg) return vg;
      for (const key of ["provider_key","adapter_key","secret_reference_id","entity_scope","mapping_entity_name","mapping_source_schema","mapping_target_schema","mapping_transform_spec","data_classification","scope"]) if (!text(payload[key])) return fail("ERP01_REQUIRED_CONNECTOR_FIELD_MISSING", 400);
      if (numberValue(payload.mapping_version) === null) return fail("ERP01_REQUIRED_CONNECTOR_FIELD_MISSING", 400);
      return null;
    }
    case "updateERPConnector": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const extra = additionalPropertiesGuard(payload, ["entity_scope","mapping_entity_name","mapping_source_schema","mapping_target_schema","mapping_transform_spec","data_classification","scope","expected_version","idempotency_key"]); if (extra) return extra;
      const target = pathId === null ? connector : (state.connector && state.connector.connector_id === pathId ? state.connector : null);
      if (!target) return fail("ERP01_CONNECTOR_NOT_FOUND");
      const guard = versionGuard(payload, target.version); if (guard) return guard;
      if (target.connection_status !== "CONFIGURING" && target.connection_status !== "VALIDATING" && target.connection_status !== "READY" && target.connection_status !== "DEGRADED") return fail("ERP01_CONNECTOR_STATE_GUARD_REJECTED");
      return null;
    }
    case "validateERPConnector": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const extra = additionalPropertiesGuard(payload, ["scope","expected_version","idempotency_key"]); if (extra) return extra;
      const target = pathId === null ? connector : (state.connector && state.connector.connector_id === pathId ? state.connector : null);
      if (!target) return fail("ERP01_CONNECTOR_NOT_FOUND");
      const guard = versionGuard(payload, target.version); if (guard) return guard;
      if (target.connection_status !== "CONFIGURING" && target.connection_status !== "VALIDATING") return fail("ERP01_CONNECTOR_NOT_VALIDATION_ELIGIBLE");
      return null;
    }
    case "validateERPMapping": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const extra = additionalPropertiesGuard(payload, ["scope","expected_version","idempotency_key"]); if (extra) return extra;
      if (!connector) return fail("ERP01_CONNECTOR_NOT_FOUND");
      const guard = versionGuard(payload, connector.mapping_version); if (guard) return guard;
      return null;
    }
    case "refreshERPSnapshot": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const extra = additionalPropertiesGuard(payload, ["requested_scope","scope","expected_version","idempotency_key"]); if (extra) return extra;
      if (!connector) return fail("ERP01_CONNECTOR_NOT_FOUND");
      if (!state.snapshot) return fail("ERP01_SNAPSHOT_NOT_FOUND");
      if (!text(payload.requested_scope) || !text(payload.scope)) return fail("ERP01_REQUIRED_SNAPSHOT_SCOPE_MISSING", 400);
      const guard = versionGuard(payload, state.snapshot.version); if (guard) return guard;
      if (state.snapshot.last_sync_status === "SNAPSHOT_SYNCING") return fail("ERP01_SNAPSHOT_STATE_GUARD_REJECTED");
      return null;
    }
    case "createERPSyncJob": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const extra = additionalPropertiesGuard(payload, ["erp_connector_id","requested_scope","data_classification","records_payload","snapshot_type","snapshot_document","completeness","external_result_verified","external_evidence_refs","scope","expected_version","idempotency_key"]); if (extra) return extra;
      const connectorRef = text(payload.erp_connector_id);
      if (!connectorRef || (connector && connector.connector_id !== connectorRef && connectorRef !== "TEST-ERP-CONNECTOR-001")) return fail("ERP01_CONNECTOR_NOT_FOUND");
      const guard = versionGuard(payload, connector?.version ?? null); if (guard) return guard;
      for (const key of ["requested_scope","data_classification","records_payload","snapshot_type","snapshot_document","completeness","scope"]) if (!text(payload[key])) return fail("ERP01_REQUIRED_SYNC_FIELD_MISSING", 400);
      const boolGuard = requiredBoolean(payload, "external_result_verified"); if (boolGuard) return boolGuard;
      if (!Array.isArray(payload.external_evidence_refs)) return fail("ERP01_REQUIRED_SYNC_FIELD_MISSING", 400);
      return null;
    }
    case "getERPSyncStatus": {
      const job = findSyncJob(pathId);
      if (!job) return fail("ERP01_SYNC_JOB_NOT_FOUND");
      return null;
    }
    case "retryERPSync": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const extra = additionalPropertiesGuard(payload, ["scope","expected_version","idempotency_key"]); if (extra) return extra;
      const job = findSyncJob(pathId);
      if (!job) return fail("ERP01_SYNC_JOB_NOT_FOUND");
      const guard = versionGuard(payload, job.version); if (guard) return guard;
      const failure = state.failures.find(item => item.sync_job_ref === job.job_id);
      if (job.state !== "FAILED" || !failure?.retry_eligible) return fail("ERP01_SYNC_JOB_NOT_RETRY_ELIGIBLE");
      return null;
    }
    case "getERPFailure": {
      const failure = findFailure(pathId);
      if (!failure) return fail("ERP01_FAILURE_NOT_FOUND");
      return null;
    }
    case "getERPFinanceFactPack":
    case "getERPCapacityGuardrails":
    case "getERPForecast":
      return null;
    case "exportProjection": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const extra = additionalPropertiesGuard(payload, ["page_uid","scope","idempotency_key"]); if (extra) return extra;
      if (!text(payload.scope)) return fail("ERP01_EXPORT_SCOPE_REQUIRED", 400);
      return null;
    }
    case "refreshProjection":
      return null;
    default:
      return fail("ERP01_UNSUPPORTED_OPERATION", 400);
  }
}

function executeCommand(operation: ErpCommandOperation, request: ErpRuntimeRequest): unknown {
  const payload = record(request.payload);
  const pathId = text(request.path_params?.id) ?? text(request.path_params?.jobId) ?? text(request.path_params?.failureId) ?? null;

  switch (operation) {
    case "createERPConnector": {
      const connector: Connector = {
        connector_id: nextEntityId("CONNECTOR"),
        provider_key: text(payload.provider_key) as string,
        adapter_key: text(payload.adapter_key) as string,
        secret_reference_id: text(payload.secret_reference_id) as string,
        entity_scope: text(payload.entity_scope) as string,
        mapping_version: numberValue(payload.mapping_version) as number,
        connection_status: "CONFIGURING",
        mapping: {
          entity_name: text(payload.mapping_entity_name) as string,
          source_schema: text(payload.mapping_source_schema) as string,
          target_schema: text(payload.mapping_target_schema) as string,
          transform_spec: text(payload.mapping_transform_spec) as string,
          data_classification: text(payload.data_classification) as string,
        },
        version: 1,
      };
      state.connector = connector;
      appendAudit({ event: "erp.connector.created", subject_ref: connector.connector_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { connector_id: connector.connector_id, state: connector.connection_status, version: connector.version, event: "erp.connector.created", test_metadata: TEST_METADATA };
    }
    case "updateERPConnector": {
      const connector = state.connector as Connector;
      if (text(payload.mapping_entity_name)) connector.mapping.entity_name = text(payload.mapping_entity_name) as string;
      if (text(payload.mapping_source_schema)) connector.mapping.source_schema = text(payload.mapping_source_schema) as string;
      if (text(payload.mapping_target_schema)) connector.mapping.target_schema = text(payload.mapping_target_schema) as string;
      if (text(payload.mapping_transform_spec)) connector.mapping.transform_spec = text(payload.mapping_transform_spec) as string;
      if (text(payload.data_classification)) connector.mapping.data_classification = text(payload.data_classification) as string;
      if (text(payload.entity_scope)) connector.entity_scope = text(payload.entity_scope) as string;
      connector.mapping_version += 1;
      connector.connection_status = "VALIDATING";
      connector.version += 1;
      appendAudit({ event: "erp.connector.updated", subject_ref: connector.connector_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { connector_id: connector.connector_id, state: connector.connection_status, version: connector.version, mapping_version: connector.mapping_version, event: "erp.connector.updated", test_metadata: TEST_METADATA };
    }
    case "validateERPConnector": {
      const connector = state.connector as Connector;
      connector.connection_status = "READY";
      connector.version += 1;
      appendAudit({ event: "erp.connector.validation_requested", subject_ref: connector.connector_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { connector_id: connector.connector_id, state: connector.connection_status, version: connector.version, event: "erp.connector.validation_requested", test_metadata: TEST_METADATA };
    }
    case "validateERPMapping": {
      const connector = state.connector as Connector;
      connector.mapping_version += 1;
      connector.connection_status = "READY";
      connector.version += 1;
      appendAudit({ event: "erp.mapping.validated", subject_ref: connector.connector_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { connector_id: connector.connector_id, state: connector.connection_status, mapping_version: connector.mapping_version, version: connector.version, event: "erp.mapping.validated", test_metadata: TEST_METADATA };
    }
    case "refreshERPSnapshot": {
      const snapshot = state.snapshot as Snapshot;
      snapshot.last_sync_status = "SNAPSHOT_SYNCING";
      snapshot.version += 1;
      appendAudit({ event: "erp.snapshot.refresh_requested", subject_ref: snapshot.snapshot_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { snapshot_id: snapshot.snapshot_id, state: snapshot.last_sync_status, completeness: snapshot.completeness, version: snapshot.version, event: "erp.snapshot.refresh_requested", test_metadata: TEST_METADATA };
    }
    case "createERPSyncJob": {
      const job: SyncJob = {
        job_id: nextEntityId("SYNC"),
        erp_connector_id: text(payload.erp_connector_id) ?? (state.connector?.connector_id as string),
        requested_scope: text(payload.requested_scope) as string,
        data_classification: text(payload.data_classification) as string,
        records_payload: text(payload.records_payload) as string,
        snapshot_type: text(payload.snapshot_type) as string,
        snapshot_document: text(payload.snapshot_document) as string,
        completeness: text(payload.completeness) as string,
        external_result_verified: boolValue(payload.external_result_verified) as boolean,
        external_evidence_refs: textList(payload.external_evidence_refs),
        state: "RUNNING",
        version: 1,
      };
      state.sync_jobs.push(job);
      appendAudit({ event: "erp.sync.requested", subject_ref: job.job_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { job_id: job.job_id, state: job.state, requested_scope: job.requested_scope, event: "erp.sync.requested", test_metadata: TEST_METADATA };
    }
    case "getERPSyncStatus": {
      const job = findSyncJob(pathId) as SyncJob;
      appendAudit({ event: "erp.sync.status_read", subject_ref: job.job_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { job_id: job.job_id, state: job.state, requested_scope: job.requested_scope, snapshot_type: job.snapshot_type, completeness: job.completeness, external_result_verified: job.external_result_verified, event: "erp.sync.status_read", test_metadata: TEST_METADATA };
    }
    case "retryERPSync": {
      const job = findSyncJob(pathId) as SyncJob;
      job.state = "RUNNING";
      job.version += 1;
      const failure = state.failures.find(item => item.sync_job_ref === job.job_id);
      if (failure) {
        failure.retry_eligible = false;
        failure.version += 1;
      }
      appendAudit({ event: "erp.sync.retry_requested", subject_ref: job.job_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { job_id: job.job_id, state: job.state, version: job.version, event: "erp.sync.retry_requested", test_metadata: TEST_METADATA };
    }
    case "getERPFailure": {
      const failure = findFailure(pathId) as FailureRecord;
      appendAudit({ event: "erp.failure.read", subject_ref: failure.failure_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { failure_id: failure.failure_id, sync_job_ref: failure.sync_job_ref, reason: failure.reason, retry_eligible: failure.retry_eligible, event: "erp.failure.read", test_metadata: TEST_METADATA };
    }
    case "getERPFinanceFactPack": {
      appendAudit({ event: "erp.finance.fact_pack_read", subject_ref: state.connector?.entity_scope ?? "finance-ledger", correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { fact_pack: state.finance, event: "erp.finance.fact_pack_read", test_metadata: TEST_METADATA };
    }
    case "getERPCapacityGuardrails": {
      appendAudit({ event: "erp.finance.capacity_guardrails_read", subject_ref: state.connector?.entity_scope ?? "finance-ledger", correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { capacity: state.finance.capacity, guardrails: state.finance.guardrails, event: "erp.finance.capacity_guardrails_read", test_metadata: TEST_METADATA };
    }
    case "getERPForecast": {
      appendAudit({ event: "erp.finance.forecast_read", subject_ref: state.connector?.entity_scope ?? "finance-ledger", correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { forecast: state.finance.forecast, event: "erp.finance.forecast_read", test_metadata: TEST_METADATA };
    }
    case "exportProjection": {
      const exportRef = nextEntityId("EXPORT");
      appendAudit({ event: "export.requested", subject_ref: exportRef, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { export_ref: exportRef, scope: text(payload.scope), status: "EXPORTED", event: "export.requested", test_metadata: TEST_METADATA };
    }
    case "refreshProjection": {
      const ref = `TEST-ERP-REFRESH-${String(state.audit_counter + 1).padStart(3, "0")}`;
      appendAudit({ event: "erp.projection.refreshed", subject_ref: ref, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { refresh_ref: ref, projection_state: "READY", test_metadata: TEST_METADATA };
    }
    default:
      return { error: "ERP01_UNSUPPORTED_OPERATION", test_metadata: TEST_METADATA };
  }
}

export async function executeControlledErpCommand(request: ErpRuntimeRequest): Promise<ErpRuntimeResult> {
  if (!isControlledErpServerTestMode()) {
    return { ok: false, status: 503, reason_code: "ERP_TEST_RUNTIME_DISABLED", correlation_id: request.correlation_id };
  }
  const isMutation = [
    "createERPConnector", "updateERPConnector", "validateERPConnector", "validateERPMapping",
    "refreshERPSnapshot", "createERPSyncJob", "retryERPSync", "exportProjection",
  ].includes(request.operation_id);
  const idempotency_key = isMutation ? text(record(request.payload).idempotency_key) : null;
  if (isMutation && idempotency_key) {
    const cached = state.idempotency.get(idempotency_key);
    if (cached) {
      return cached.ok
        ? { ok: true, value: cached.value, correlation_id: request.correlation_id }
        : { ok: false, status: cached.status ?? 403, reason_code: cached.reason_code as string, correlation_id: request.correlation_id };
    }
  }
  if (request.operation_id !== "createERPConnector") seedFixture();
  const gate = evaluateGates(request.operation_id, request);
  if (gate) {
    if (isMutation) {
      if (idempotency_key) state.idempotency.set(idempotency_key, { ok: false, reason_code: gate.reason_code, status: gate.status });
      appendAudit({ event: `erp.gate.denied`, subject_ref: text(record(request.payload).connector_id) ?? text(record(request.payload).job_id) ?? text(request.path_params?.id) ?? "unresolved", correlation_id: request.correlation_id, outcome: "DENIED", reason_code: gate.reason_code });
    }
    return { ...gate, correlation_id: request.correlation_id };
  }
  const value = executeCommand(request.operation_id, request);
  if (isMutation && idempotency_key) state.idempotency.set(idempotency_key, { ok: true, value, status: 200 });
  return { ok: true, value, correlation_id: request.correlation_id };
}

function isErpScope(scope: string | null | undefined): boolean {
  return typeof scope === "string" && (scope.startsWith("admin:ERP") || scope.startsWith("erp") || scope.startsWith("finance"));
}

export async function executeControlledErpInfoCommand(r: InfoRequest):
  Promise<{ ok: true; value: unknown } | { ok: false; status: number; reason_code: string } | null> {
  if (!isControlledErpServerTestMode()) return null;
  const payload = record(r.payload);
  const pageUid = text(payload.page_uid);
  const scope = text(payload.scope);
  if (pageUid !== "admin:ERP-01" && !isErpScope(scope)) return null;
  if (r.operation_id !== "exportProjection" && r.operation_id !== "refreshProjection") return null;
  const result = await executeControlledErpCommand({
    operation_id: r.operation_id, correlation_id: r.correlation_id,
    path_params: r.path_params ?? {}, payload: r.payload,
  });
  if (!result.ok) return { ok: false as const, status: result.status, reason_code: result.reason_code };
  return { ok: true as const, value: result.value };
}

export function resetControlledErpStateForTest() {
  state.connector = null;
  state.snapshot = null;
  state.sync_jobs = [];
  state.failures = [];
  state.finance = {
    cost: "[TEST] authorized provider cost status · masked quote on record",
    revenue: "[TEST] provider revenue · read-only status",
    cashflow: "[TEST] cashflow status · read-only projection",
    capacity: "[TEST] capacity guardrail · within governed bound",
    forecast: "[TEST] next period forecast · read model ready",
    guardrails: "[TEST] governed finance guardrails · read-only",
    recommendation_boundary: "[TEST] recommendation boundary · read-only",
  };
  state.audits = [];
  state.audit_counter = 0;
  state.idempotency.clear();
  state.entity_counter = 0;
}
