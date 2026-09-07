import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import {
  hashSessionToken,
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { KnowledgeRuntimeRequest } from "@/domain/knowledge/knowledgeRuntimeContract";

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
function uuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}
function exactKeys(payload: Row): boolean {
  const actual = Object.keys(payload).sort();
  const expected = ["correlation_id","expected_version","idempotency_key","reason","source_id"];
  return actual.length === expected.length && expected.every((key, index) => actual[index] === key);
}

async function requireContext(): Promise<{
  sql: SqlClient;
  actor_user_id: string;
  session_token_hash: string;
}> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const store = await cookies();
  const token = store.get(IDENTITY_COOKIE_NAME)?.value?.trim() ?? "";
  if (!token) throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity = await resolveIdentityFromCookie(token);
  if (!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  return {
    sql,
    actor_user_id: identity.actor.user_id,
    session_token_hash: hashSessionToken(token),
  };
}

export async function transitionProductionKnowledgeSource(request: KnowledgeRuntimeRequest): Promise<unknown> {
  if (request.operation !== "pauseKnowledgeSource" && request.operation !== "resumeKnowledgeSource") {
    throw new NamedRuntimeError("KB_UNSUPPORTED_OPERATION");
  }

  const payload = record(request.payload);
  if (!exactKeys(payload)) throw new NamedRuntimeError("KB01_SOURCE_STATE_REQUEST_SCHEMA_INVALID");

  const sourceId = text(payload.source_id);
  const pathSourceId = text(request.path_params?.sourceId);
  if (!uuid(sourceId) || sourceId !== pathSourceId) throw new NamedRuntimeError("KB01_SOURCE_ID_MISMATCH");

  const expectedVersion = positiveInt(payload.expected_version);
  if (!expectedVersion) throw new NamedRuntimeError("KB01_EXPECTED_VERSION_MISSING");

  const reason = text(payload.reason);
  if (!reason) throw new NamedRuntimeError("KB01_SOURCE_STATE_REASON_REQUIRED");

  const bodyCorrelation = text(payload.correlation_id);
  if (!uuid(bodyCorrelation) || bodyCorrelation !== request.correlation_id) {
    throw new NamedRuntimeError("KB01_CORRELATION_ID_MISMATCH");
  }

  const idempotencyKey = text(payload.idempotency_key);
  if (!idempotencyKey || idempotencyKey.length > 128) {
    throw new NamedRuntimeError("KB01_IDEMPOTENCY_KEY_REQUIRED");
  }

  const expectedState = request.operation === "pauseKnowledgeSource" ? "ACTIVE" : "PAUSED";
  const targetState = request.operation === "pauseKnowledgeSource" ? "PAUSED" : "ACTIVE";
  const auditAction = request.operation === "pauseKnowledgeSource"
    ? "knowledge.source.paused"
    : "knowledge.source.resumed";

  const { sql, actor_user_id, session_token_hash } = await requireContext();

  const replayRows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      SELECT
        entity_id::text AS source_id,
        action,
        reason,
        before_version,
        after_version
      FROM public.audit_events
      WHERE payload_hash=encode(digest(${idempotencyKey}::text,'sha256'),'hex')
        AND entity_type='admin:KB-01'
      ORDER BY occurred_at DESC
      LIMIT 1
    `,
  );
  const replay = first(replayRows);
  if (replay) {
    const beforeVersion = record(replay.before_version);
    const afterVersion = record(replay.after_version);
    if (
      text(replay.source_id) !== sourceId
      || text(replay.action) !== auditAction
      || text(replay.reason) !== reason
      || Number(beforeVersion.source_version) !== expectedVersion
    ) {
      throw new NamedRuntimeError("KB01_IDEMPOTENCY_CONFLICT");
    }
    return {
      source_id: sourceId,
      state: text(afterVersion.status) || targetState,
      source_version: Number(afterVersion.source_version) || expectedVersion + 1,
      idempotent_replay: true,
      external_request_sent: false,
    };
  }

  const rows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      WITH updated AS (
        UPDATE public.knowledge_sources
        SET status=${targetState},
            source_version=source_version+1,
            updated_at=now()
        WHERE knowledge_source_id=${sourceId}::uuid
          AND status=${expectedState}
          AND source_version=${expectedVersion}
        RETURNING knowledge_source_id::text AS source_id,status,source_version
      ),
      audited AS (
        INSERT INTO public.audit_events(
          action,
          entity_type,
          entity_id,
          actor_id,
          actor_type,
          before_version,
          after_version,
          reason,
          correlation_id,
          payload_hash
        )
        SELECT
          ${auditAction},
          'admin:KB-01',
          u.source_id::uuid,
          ${actor_user_id}::uuid,
          'USER',
          jsonb_build_object('status',${expectedState},'source_version',${expectedVersion}),
          jsonb_build_object('status',u.status,'source_version',u.source_version),
          ${reason},
          ${request.correlation_id}::uuid,
          encode(digest(${idempotencyKey}::text,'sha256'),'hex')
        FROM updated u
        RETURNING audit_event_id::text AS audit_event_id
      )
      SELECT u.source_id,u.status,u.source_version,a.audit_event_id
      FROM updated u
      CROSS JOIN audited a
    `,
  );

  const changed = first(rows);
  if (!changed) {
    const currentRows = await runRlsActorQuery(
      sql,
      session_token_hash,
      sql`
        SELECT knowledge_source_id::text AS source_id,status,source_version
        FROM public.knowledge_sources
        WHERE knowledge_source_id=${sourceId}::uuid
        LIMIT 1
      `,
    );
    const current = first(currentRows);
    if (!current) throw new NamedRuntimeError("KB01_SOURCE_NOT_FOUND");
    if (Number(current.source_version) !== expectedVersion) throw new NamedRuntimeError("KB01_SOURCE_VERSION_CONFLICT");
    throw new NamedRuntimeError("KB01_SOURCE_STATE_GUARD_REJECTED");
  }

  return {
    source_id: text(changed.source_id),
    state: text(changed.status),
    source_version: Number(changed.source_version),
    audit_event_id: text(changed.audit_event_id),
    idempotent_replay: false,
    external_request_sent: false,
  };
}
