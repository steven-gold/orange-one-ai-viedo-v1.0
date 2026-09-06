import { createHash } from "node:crypto";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type QueueRow = Record<string, unknown>;

export const PROVIDER_EXECUTION_QUEUE_KEY = "acpos.provider.execution.v1";
export const PROVIDER_EXECUTION_WORKER_KEY = "acpos.provider.execution.worker.v1";
export const PROVIDER_EXECUTION_EVENT = "ACPOS_PROVIDER_EXECUTION_REQUESTED";
export const QUEUE_RUNTIME_PROBE_EVENT = "ACPOS_QUEUE_RUNTIME_PROBE";

function asText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const v = value.trim();
  return v ? v : null;
}
function asInt(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}
function first(rows: unknown): QueueRow | null {
  return Array.isArray(rows) && rows[0] && typeof rows[0] === "object" ? rows[0] as QueueRow : null;
}
function sha256(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}
async function sqlClient(): Promise<SqlClient> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  return sql;
}

export async function getProviderExecutionQueueHealth(): Promise<{
  queue_ready: boolean;
  worker_ready: boolean;
  worker_last_heartbeat_at: string | null;
  pending: number;
  leased: number;
  dead_lettered: number;
}> {
  const sql = await sqlClient();
  const result = await sql`
    SELECT
      EXISTS(
        SELECT 1 FROM queues
        WHERE queue_key=${PROVIDER_EXECUTION_QUEUE_KEY} AND status='READY'
      ) AS queue_ready,
      EXISTS(
        SELECT 1 FROM workers w
        JOIN queues q ON q.queue_id=w.queue_id
        WHERE w.worker_key=${PROVIDER_EXECUTION_WORKER_KEY}
          AND q.queue_key=${PROVIDER_EXECUTION_QUEUE_KEY}
          AND w.status='READY'
      ) AS worker_ready,
      (
        SELECT w.last_heartbeat_at::text
        FROM workers w
        WHERE w.worker_key=${PROVIDER_EXECUTION_WORKER_KEY}
        LIMIT 1
      ) AS worker_last_heartbeat_at,
      (
        SELECT count(*)::int
        FROM outbox_events o
        JOIN queues q ON q.queue_id=o.queue_id
        WHERE q.queue_key=${PROVIDER_EXECUTION_QUEUE_KEY}
          AND o.published_at IS NULL
          AND o.dead_lettered_at IS NULL
          AND o.claimed_by_worker_id IS NULL
      ) AS pending,
      (
        SELECT count(*)::int
        FROM outbox_events o
        JOIN queues q ON q.queue_id=o.queue_id
        WHERE q.queue_key=${PROVIDER_EXECUTION_QUEUE_KEY}
          AND o.published_at IS NULL
          AND o.dead_lettered_at IS NULL
          AND o.claimed_by_worker_id IS NOT NULL
          AND o.lease_until >= now()
      ) AS leased,
      (
        SELECT count(*)::int
        FROM outbox_events o
        JOIN queues q ON q.queue_id=o.queue_id
        WHERE q.queue_key=${PROVIDER_EXECUTION_QUEUE_KEY}
          AND o.dead_lettered_at IS NOT NULL
      ) AS dead_lettered
  `;
  const row=first(result);
  return {
    queue_ready: row?.queue_ready === true,
    worker_ready: row?.worker_ready === true,
    worker_last_heartbeat_at: asText(row?.worker_last_heartbeat_at),
    pending: asInt(row?.pending),
    leased: asInt(row?.leased),
    dead_lettered: asInt(row?.dead_lettered),
  };
}

export async function enqueueQueueRuntimeProbe(input: {
  correlation_id: string;
  idempotency_key?: string;
}): Promise<{ event_id: string; enqueued: boolean; idempotency_key: string }> {
  const sql = await sqlClient();
  const eventId=crypto.randomUUID();
  const aggregateId=crypto.randomUUID();
  const correlation=/^[0-9a-f-]{36}$/i.test(input.correlation_id) ? input.correlation_id : crypto.randomUUID();
  const idempotency=sha256(input.idempotency_key?.trim() || `queue-runtime-probe:${correlation}`);
  const payload=JSON.stringify({
    probe: "PRODUCTION_QUEUE_RUNTIME",
    external_provider_call: false,
    business_table_mutation: false,
  });
  const result=await sql`
    INSERT INTO outbox_events(
      event_id,event_type,event_version,aggregate_type,aggregate_id,aggregate_version,
      correlation_id,payload,payload_hash,queue_id,idempotency_key,max_attempts
    )
    SELECT
      ${eventId}::uuid,${QUEUE_RUNTIME_PROBE_EVENT},1,'QUEUE_RUNTIME_PROBE',
      ${aggregateId}::uuid,1,${correlation}::uuid,${payload}::jsonb,${sha256(payload)},
      q.queue_id,${idempotency},3
    FROM queues q
    WHERE q.queue_key=${PROVIDER_EXECUTION_QUEUE_KEY}
      AND q.status='READY'
    ON CONFLICT DO NOTHING
    RETURNING event_id::text AS event_id
  `;
  const inserted=first(result);
  if (inserted) return { event_id: asText(inserted.event_id) ?? eventId, enqueued: true, idempotency_key: idempotency };
  const existing=first(await sql`
    SELECT o.event_id::text AS event_id
    FROM outbox_events o
    JOIN queues q ON q.queue_id=o.queue_id
    WHERE q.queue_key=${PROVIDER_EXECUTION_QUEUE_KEY}
      AND o.idempotency_key=${idempotency}
    LIMIT 1
  `);
  const existingId=asText(existing?.event_id);
  if (!existingId) throw new NamedRuntimeError("QUEUE_RUNTIME_NOT_MATERIALIZED");
  return { event_id: existingId, enqueued: false, idempotency_key: idempotency };
}

async function heartbeat(sql: SqlClient, state: string, detail: Record<string, unknown>): Promise<void> {
  await sql`
    UPDATE workers
    SET last_heartbeat_at=now(),
        health=${JSON.stringify({ status: state, ...detail })}::jsonb
    WHERE worker_key=${PROVIDER_EXECUTION_WORKER_KEY}
  `;
}

async function claimBatch(sql: SqlClient, limit: number): Promise<QueueRow[]> {
  const result=await sql`
    WITH worker AS (
      SELECT w.worker_id,w.queue_id
      FROM workers w
      JOIN queues q ON q.queue_id=w.queue_id
      WHERE w.worker_key=${PROVIDER_EXECUTION_WORKER_KEY}
        AND q.queue_key=${PROVIDER_EXECUTION_QUEUE_KEY}
        AND w.status='READY'
      LIMIT 1
    ), candidate AS (
      SELECT o.outbox_event_id
      FROM outbox_events o
      JOIN worker w ON w.queue_id=o.queue_id
      WHERE o.published_at IS NULL
        AND o.dead_lettered_at IS NULL
        AND o.available_at<=now()
        AND o.attempt_count<o.max_attempts
        AND (o.claimed_by_worker_id IS NULL OR o.lease_until<now())
      ORDER BY o.available_at,o.occurred_at
      FOR UPDATE SKIP LOCKED
      LIMIT ${Math.max(1,Math.min(limit,10))}
    )
    UPDATE outbox_events o
    SET claimed_by_worker_id=w.worker_id,
        lease_until=now()+interval '120 seconds',
        attempt_count=o.attempt_count+1
    FROM candidate c,worker w
    WHERE o.outbox_event_id=c.outbox_event_id
    RETURNING
      o.outbox_event_id::text,
      o.event_id::text,
      o.event_type,
      o.payload,
      o.payload_hash,
      o.attempt_count,
      o.max_attempts,
      o.correlation_id::text
  `;
  return Array.isArray(result) ? result as QueueRow[] : [];
}

async function claimEventById(sql: SqlClient, eventId: string): Promise<QueueRow | null> {
  const result=await sql`
    WITH worker AS (
      SELECT w.worker_id,w.queue_id
      FROM workers w
      JOIN queues q ON q.queue_id=w.queue_id
      WHERE w.worker_key=${PROVIDER_EXECUTION_WORKER_KEY}
        AND q.queue_key=${PROVIDER_EXECUTION_QUEUE_KEY}
        AND w.status='READY'
      LIMIT 1
    )
    UPDATE outbox_events o
    SET claimed_by_worker_id=w.worker_id,
        lease_until=now()+interval '120 seconds',
        attempt_count=o.attempt_count+1
    FROM worker w
    WHERE o.event_id=${eventId}::uuid
      AND o.queue_id=w.queue_id
      AND o.published_at IS NULL
      AND o.dead_lettered_at IS NULL
      AND o.available_at<=now()
      AND o.attempt_count<o.max_attempts
      AND (o.claimed_by_worker_id IS NULL OR o.lease_until<now())
    RETURNING
      o.outbox_event_id::text,
      o.event_id::text,
      o.event_type,
      o.payload,
      o.payload_hash,
      o.attempt_count,
      o.max_attempts,
      o.correlation_id::text
  `;
  return first(result);
}

async function completeEvent(sql: SqlClient, row: QueueRow, resultValue: Record<string, unknown>): Promise<void> {
  const eventId=asText(row.event_id);
  if (!eventId) throw new NamedRuntimeError("QUEUE_EVENT_ID_REQUIRED");
  await sql.transaction([
    sql`
      INSERT INTO inbox_events(consumer_name,event_id,result)
      VALUES(${PROVIDER_EXECUTION_WORKER_KEY},${eventId}::uuid,${JSON.stringify(resultValue)}::jsonb)
      ON CONFLICT(consumer_name,event_id) DO NOTHING
    `,
    sql`
      UPDATE outbox_events
      SET published_at=now(),claimed_by_worker_id=NULL,lease_until=NULL,last_error_code=NULL
      WHERE event_id=${eventId}::uuid
    `,
  ]);
}

async function failEvent(sql: SqlClient, row: QueueRow, reasonCode: string): Promise<"RETRY"|"DLQ"> {
  const eventId=asText(row.event_id);
  const attempt=asInt(row.attempt_count);
  const maxAttempts=Math.max(1,asInt(row.max_attempts));
  if (!eventId) throw new NamedRuntimeError("QUEUE_EVENT_ID_REQUIRED");

  if (attempt>=maxAttempts) {
    await sql.transaction([
      sql`
        INSERT INTO dead_letters(event_id,consumer_name,failure_code,payload_hash,retry_count,status)
        VALUES(
          ${eventId}::uuid,${PROVIDER_EXECUTION_WORKER_KEY},${reasonCode},
          ${asText(row.payload_hash) ?? sha256(eventId)},${attempt},'BLOCKED'
        )
        ON CONFLICT DO NOTHING
      `,
      sql`
        UPDATE outbox_events
        SET last_error_code=${reasonCode},dead_lettered_at=now(),claimed_by_worker_id=NULL,lease_until=NULL
        WHERE event_id=${eventId}::uuid
      `,
    ]);
    return "DLQ";
  }

  const backoff=attempt<=1 ? 30 : attempt===2 ? 120 : 300;
  await sql`
    UPDATE outbox_events
    SET last_error_code=${reasonCode},
        available_at=now()+${backoff}*interval '1 second',
        claimed_by_worker_id=NULL,
        lease_until=NULL
    WHERE event_id=${eventId}::uuid
  `;
  return "RETRY";
}

async function handleEvent(row: QueueRow): Promise<Record<string, unknown>> {
  const eventType=asText(row.event_type);
  if (eventType===QUEUE_RUNTIME_PROBE_EVENT) {
    return {
      event_type: eventType,
      probe: "PASS",
      external_provider_call: false,
      business_table_mutation: false,
    };
  }
  if (eventType===PROVIDER_EXECUTION_EVENT) {
    throw new NamedRuntimeError("PROVIDER_EXTERNAL_ADAPTER_EXECUTION_NOT_MATERIALIZED");
  }
  throw new NamedRuntimeError("QUEUE_EVENT_TYPE_NOT_REGISTERED");
}

export async function drainProviderExecutionQueue(limit=10): Promise<{
  claimed: number;
  succeeded: number;
  retried: number;
  dead_lettered: number;
}> {
  const sql=await sqlClient();
  await heartbeat(sql,"DRAINING",{ claimed:0 });
  const claimed=await claimBatch(sql,limit);
  let succeeded=0,retried=0,deadLettered=0;

  for (const row of claimed) {
    try {
      const value=await handleEvent(row);
      await completeEvent(sql,row,value);
      succeeded+=1;
    } catch (error) {
      const reason=error instanceof Error && error.message ? error.message : "QUEUE_HANDLER_FAILED";
      const outcome=await failEvent(sql,row,reason);
      if (outcome==="RETRY") retried+=1;
      else deadLettered+=1;
    }
  }

  await heartbeat(sql,"HEALTHY",{
    claimed: claimed.length,
    succeeded,
    retried,
    dead_lettered: deadLettered,
  });
  return { claimed:claimed.length,succeeded,retried,dead_lettered:deadLettered };
}

export async function runProviderQueueRuntimeProbe(input: {
  correlation_id: string;
  idempotency_key?: string;
}): Promise<{
  status: "PASS";
  event_id: string;
  idempotent_enqueue: boolean;
  claimed: number;
  inbox_receipt: number;
  published: number;
  residual_probe_rows: number;
  external_provider_call: false;
}> {
  const sql=await sqlClient();
  const queued=await enqueueQueueRuntimeProbe(input);
  await heartbeat(sql,"PROBING",{ event_id:queued.event_id });

  const claimed=await claimEventById(sql,queued.event_id);
  if (!claimed) {
    const existing=first(await sql`
      SELECT published_at,dead_lettered_at
      FROM outbox_events
      WHERE event_id=${queued.event_id}::uuid
      LIMIT 1
    `);
    if (!existing || existing.published_at == null) {
      throw new NamedRuntimeError("QUEUE_RUNTIME_PROBE_CLAIM_FAILED");
    }
  } else {
    const value=await handleEvent(claimed);
    await completeEvent(sql,claimed,value);
  }

  const evidence=first(await sql`
    SELECT
      (SELECT count(*)::int FROM inbox_events
       WHERE consumer_name=${PROVIDER_EXECUTION_WORKER_KEY}
         AND event_id=${queued.event_id}::uuid) AS inbox_receipt,
      (SELECT count(*)::int FROM outbox_events
       WHERE event_id=${queued.event_id}::uuid
         AND published_at IS NOT NULL
         AND dead_lettered_at IS NULL
         AND claimed_by_worker_id IS NULL
         AND lease_until IS NULL) AS published
  `);
  const inboxReceipt=asInt(evidence?.inbox_receipt);
  const published=asInt(evidence?.published);
  if (inboxReceipt !== 1 || published !== 1) {
    throw new NamedRuntimeError("QUEUE_RUNTIME_PROBE_EVIDENCE_FAILED");
  }

  await heartbeat(sql,"HEALTHY",{
    last_probe:"PRODUCTION_HTTP_RUNTIME_PASS",
    external_provider_call:false,
  });

  await sql.transaction([
    sql`
      DELETE FROM inbox_events
      WHERE consumer_name=${PROVIDER_EXECUTION_WORKER_KEY}
        AND event_id=${queued.event_id}::uuid
    `,
    sql`
      DELETE FROM dead_letters
      WHERE event_id=${queued.event_id}::uuid
    `,
    sql`
      DELETE FROM outbox_events
      WHERE event_id=${queued.event_id}::uuid
    `,
  ]);

  const residual=first(await sql`
    SELECT
      (
        (SELECT count(*) FROM outbox_events WHERE event_id=${queued.event_id}::uuid)
        +
        (SELECT count(*) FROM inbox_events WHERE event_id=${queued.event_id}::uuid)
        +
        (SELECT count(*) FROM dead_letters WHERE event_id=${queued.event_id}::uuid)
      )::int AS residual_probe_rows
  `);

  return {
    status:"PASS",
    event_id:queued.event_id,
    idempotent_enqueue:!queued.enqueued,
    claimed:claimed ? 1 : 0,
    inbox_receipt:inboxReceipt,
    published,
    residual_probe_rows:asInt(residual?.residual_probe_rows),
    external_provider_call:false,
  };
}

