import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

const authority=await readFile("authority/runtime/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml","utf8");
const migration=await readFile("database/migrations/0019_async_queue_delivery_runtime.sql","utf8");
const manifest=await readFile("database/migrations/migration_checksum_manifest.yaml","utf8");
const runtime=await readFile("src/server/queue/providerExecutionQueueRuntime.ts","utf8");
const route=await readFile("src/app/v1/internal/queue/provider-execution/drain/route.ts","utf8");
const vercel=await readFile("vercel.json","utf8");
const env=await readFile(".env.example","utf8");

test("queue authority reuses canonical outbox/worker/DLQ ownership",()=>{
  assert.match(authority,/second_queue_system: FORBIDDEN/);
  for(const owner of ["public.queues","public.workers","public.outbox_events","public.inbox_events","public.dead_letters"]){
    assert.match(authority,new RegExp(owner.replace(".","\\.")));
  }
  assert.match(authority,/acpos\.provider\.execution\.v1/);
  assert.match(authority,/acpos\.provider\.execution\.worker\.v1/);
  assert.match(authority,/FOR_UPDATE_SKIP_LOCKED/);
  assert.match(authority,/LEASE_EXPIRY_RECLAIM/);
});

test("0019 extends canonical outbox instead of creating another queue table",()=>{
  assert.doesNotMatch(migration,/CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:public\.)?(?:queue|worker|outbox|dead_letter)/i);
  assert.match(migration,/ALTER TABLE public\.outbox_events/);
  for(const column of ["queue_id","idempotency_key","available_at","claimed_by_worker_id","lease_until","attempt_count","max_attempts","last_error_code","dead_lettered_at"]){
    assert.match(migration,new RegExp(`ADD COLUMN IF NOT EXISTS ${column}\\b`));
  }
  assert.match(migration,/uq_outbox_queue_idempotency/);
  assert.match(migration,/idx_outbox_queue_claimable/);
  assert.match(migration,/0019_async_queue_delivery_runtime/);
});

test("0019 payload checksum is exact and registered",()=>{
  const separator="\nINSERT INTO schema_migration_history";
  const index=migration.indexOf(separator);
  assert.ok(index>0);
  const payload=migration.slice(0,index);
  const checksum=createHash("sha256").update(payload).digest("hex");
  assert.equal(checksum,"aea7ea811c826b255d3478e12e9715cb042444c5d2c6f8431f02b0189c0818cc");
  assert.match(manifest,new RegExp(`0019_async_queue_delivery_runtime[\\s\\S]*?${checksum}`));
});

test("provider queue runtime implements claim, lease recovery, retry, DLQ, idempotency and heartbeat",()=>{
  assert.match(runtime,/FOR UPDATE SKIP LOCKED/);
  assert.match(runtime,/lease_until<now\(\)/);
  assert.match(runtime,/attempt_count=o\.attempt_count\+1/);
  assert.match(runtime,/ON CONFLICT\(consumer_name,event_id\) DO NOTHING/);
  assert.match(runtime,/dead_letters/);
  assert.match(runtime,/dead_lettered_at=now\(\)/);
  assert.match(runtime,/last_heartbeat_at=now\(\)/);
  assert.match(runtime,/PROVIDER_EXTERNAL_ADAPTER_EXECUTION_NOT_MATERIALIZED/);
  assert.match(runtime,/external_provider_call: false/);
});

test("cron drain is secret-gated and provider queue is scheduled",()=>{
  assert.match(route,/QUEUE_CRON_SECRET_NOT_BOUND/);
  assert.match(route,/QUEUE_CRON_UNAUTHORIZED/);
  assert.match(route,/authorization/);
  assert.match(route,/Bearer/);
  assert.match(env,/CRON_SECRET=/);
  const config=JSON.parse(vercel);
  assert.deepEqual(config.crons,[{
    path:"/v1/internal/queue/provider-execution/drain",
    schedule:"*/5 * * * *",
  }]);
});
