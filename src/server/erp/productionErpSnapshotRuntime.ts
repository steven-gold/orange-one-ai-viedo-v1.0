import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { IDENTITY_COOKIE_NAME, resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { ErpRuntimeRequest } from "@/server/testing/controlledErpTestRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

function record(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function positiveInt(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) && rows.length > 0 && rows[0] && typeof rows[0] === "object"
    ? rows[0] as Row
    : null;
}
async function requireContext(): Promise<{ sql: SqlClient; actor_user_id: string }> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const store = await cookies();
  const token = store.get(IDENTITY_COOKIE_NAME)?.value?.trim() ?? "";
  if (!token) throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity = await resolveIdentityFromCookie(token);
  if (!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  return { sql, actor_user_id: identity.actor.user_id };
}

async function audit(
  sql: SqlClient,
  input: { actor_user_id: string; correlation_id: string; entity_id: string; payload: unknown },
) {
  await sql`
    INSERT INTO audit_events(action,entity_type,entity_id,actor_id,actor_type,correlation_id,payload_hash)
    VALUES(
      'erp.snapshot.refresh_requested',
      'admin:ERP-01',
      ${input.entity_id}::uuid,
      ${input.actor_user_id}::uuid,
      'USER',
      ${input.correlation_id},
      encode(digest(${JSON.stringify(input.payload)}::text,'sha256'),'hex')
    )
  `;
}

export async function requestProductionErpSnapshotRefresh(request: ErpRuntimeRequest): Promise<unknown> {
  const payload = record(request.payload);
  const requestedScope = text(payload.requested_scope);
  const scope = text(payload.scope);
  if (!requestedScope || !scope || requestedScope !== scope) {
    throw new NamedRuntimeError("ERP01_REQUIRED_SNAPSHOT_SCOPE_MISSING");
  }

  const expectedVersion = positiveInt(payload.expected_version);
  if (!expectedVersion) throw new NamedRuntimeError("ERP01_EXPECTED_VERSION_MISSING");
  const idempotencyKey = text(payload.idempotency_key);
  if (!idempotencyKey) throw new NamedRuntimeError("ERP01_IDEMPOTENCY_KEY_REQUIRED");
  if (idempotencyKey.length > 64) throw new NamedRuntimeError("ERP01_IDEMPOTENCY_KEY_INVALID");

  const { sql, actor_user_id } = await requireContext();

  const targets = await sql`
    SELECT c.erp_connector_id::text AS connector_id,
           c.connection_status,
           CASE
             WHEN jsonb_typeof(c.entity_scope)='string' THEN c.entity_scope #>> '{}'
             ELSE c.entity_scope::text
           END AS scope_text,
           s.erp_snapshot_id::text AS snapshot_id,
           s.snapshot_type,
           s.status::text AS snapshot_status,
           floor(extract(epoch FROM s.created_at) * 1000)::bigint::text AS snapshot_version
    FROM public.erp_connectors c
    JOIN LATERAL (
      SELECT s0.*
      FROM public.erp_snapshots s0
      WHERE s0.erp_connector_id=c.erp_connector_id
      ORDER BY s0.created_at DESC, s0.erp_snapshot_id DESC
      LIMIT 1
    ) s ON true
    WHERE (
      CASE
        WHEN jsonb_typeof(c.entity_scope)='string' THEN c.entity_scope #>> '{}'
        ELSE c.entity_scope::text
      END
    )=${requestedScope}
    ORDER BY c.updated_at DESC,c.erp_connector_id
    LIMIT 2
  `;

  if (!Array.isArray(targets) || targets.length === 0) throw new NamedRuntimeError("ERP01_SNAPSHOT_NOT_FOUND");
  if (targets.length !== 1) throw new NamedRuntimeError("ERP01_SNAPSHOT_REFRESH_TARGET_AMBIGUOUS");
  const target = first(targets);
  if (!target) throw new NamedRuntimeError("ERP01_SNAPSHOT_NOT_FOUND");

  const connectionStatus = text(target.connection_status);
  if (connectionStatus !== "READY" && connectionStatus !== "DEGRADED") {
    throw new NamedRuntimeError("ERP01_CONNECTOR_STATE_GUARD_REJECTED");
  }
  if (Number(target.snapshot_version) !== expectedVersion) {
    throw new NamedRuntimeError("ERP01_SNAPSHOT_VERSION_CONFLICT");
  }

  const connectorId = text(target.connector_id);
  const snapshotId = text(target.snapshot_id);
  const snapshotType = text(target.snapshot_type) || "GENERAL";

  const active = first(await sql`
    SELECT erp_sync_job_id::text AS sync_job_id,status
    FROM public.erp_sync_jobs
    WHERE erp_connector_id=${connectorId}::uuid
      AND status IN ('QUEUED','RUNNING','PENDING_EXTERNAL')
    ORDER BY requested_at DESC
    LIMIT 1
  `);
  if (active) throw new NamedRuntimeError("ERP01_SNAPSHOT_STATE_GUARD_REJECTED");

  const cached = first(await sql`
    SELECT erp_sync_job_id::text AS sync_job_id,
           erp_connector_id::text AS connector_id,
           requested_scope,
           snapshot_type,
           status
    FROM public.erp_sync_jobs
    WHERE idempotency_key=${idempotencyKey}
    LIMIT 1
  `);
  if (cached) {
    const cachedScope = record(cached.requested_scope);
    if (text(cached.connector_id) !== connectorId || text(cachedScope.scope) !== requestedScope) {
      throw new NamedRuntimeError("ERP01_IDEMPOTENCY_CONFLICT");
    }
    return {
      sync_job_id: text(cached.sync_job_id),
      snapshot_id: snapshotId,
      state: text(cached.status),
      requested_scope: requestedScope,
      source_snapshot_version: expectedVersion,
      idempotent_replay: true,
      external_request_sent: false,
      snapshot_mutated: false,
    };
  }

  const requestedScopeDocument = {
    scope: requestedScope,
    operation: "refreshERPSnapshot",
    source_snapshot_id: snapshotId,
    source_snapshot_version: expectedVersion,
    external_request_sent: false,
  };
  const rows = await sql`
    INSERT INTO public.erp_sync_jobs(
      erp_connector_id,
      requested_by,
      idempotency_key,
      requested_scope,
      data_classification,
      snapshot_type,
      attempt_no,
      external_evidence_refs,
      status
    )
    VALUES(
      ${connectorId}::uuid,
      ${actor_user_id}::uuid,
      ${idempotencyKey},
      ${JSON.stringify(requestedScopeDocument)}::jsonb,
      'INTERNAL',
      ${snapshotType},
      1,
      '[]'::jsonb,
      'QUEUED'
    )
    RETURNING erp_sync_job_id::text AS sync_job_id,status
  `;
  const created = first(rows);
  if (!created) throw new NamedRuntimeError("ERP01_SNAPSHOT_REFRESH_REQUEST_FAILED");

  await audit(sql,{
    actor_user_id,
    correlation_id:request.correlation_id,
    entity_id:text(created.sync_job_id),
    payload:{
      connector_id:connectorId,
      snapshot_id:snapshotId,
      requested_scope:requestedScope,
      source_snapshot_version:expectedVersion,
      idempotency_key:idempotencyKey,
      external_request_sent:false,
    },
  });

  return {
    sync_job_id: text(created.sync_job_id),
    snapshot_id: snapshotId,
    state: text(created.status),
    requested_scope: requestedScope,
    source_snapshot_version: expectedVersion,
    idempotent_replay: false,
    external_request_sent: false,
    snapshot_mutated: false,
  };
}
