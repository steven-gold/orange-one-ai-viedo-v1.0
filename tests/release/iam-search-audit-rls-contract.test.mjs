import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

test("0052 narrows IAM Search audit RLS to Current actor and exact IAM resources",async()=>{
  const migration=await readFile("database/migrations/0052_iam_search_audit_rls_closure.sql","utf8");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  assert.equal(createHash("sha256").update(migration.slice(0,idx)).digest("hex"),"576e039f06550edd7374471ce01ad7384478393b19e5cf9530e85c07de95c305");
  assert.match(migration,/entity_type='admin:IAM-01'/);
  assert.match(migration,/action='searchProjection'/);
  assert.match(migration,/actor_id=acpos_runtime\.current_actor_user_id\(\)/);
  assert.match(migration,/has_account_resource_action\('page:admin:IAM-01','VIEW'\)/);
  assert.match(migration,/has_account_resource_action\('action:admin:IAM-01:ACT-SEARCH','INVOKE'\)/);
  assert.doesNotMatch(migration,/CREATE TABLE/i);
  assert.doesNotMatch(migration,/INSERT INTO public\.(app_users|account_permission_assignments|access_reviews|security_audits)\b/i);
});

test("shared search binds exact IAM Search audit instead of a no-op",async()=>{
  const runtime=await readFile("src/server/shared/identityPageCommandRuntime.ts","utf8");
  const neon=await readFile("src/server/database/neonRuntime.ts","utf8");
  assert.match(runtime,/async function auditInfoCommand/);
  assert.match(runtime,/pageUid !== "admin:IAM-01" \|\| entry\.operation_id !== "searchProjection"/);
  assert.match(runtime,/INSERT INTO public\.audit_events/);
  assert.match(runtime,/'searchProjection','admin:IAM-01'/);
  assert.match(runtime,/audit: auditInfoCommand/);
  assert.ok(Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1]??0)>=52);
});
