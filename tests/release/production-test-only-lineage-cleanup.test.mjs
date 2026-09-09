import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0043 removes only the historical TEST_ONLY production lineage and creates no business data",async()=>{
  const migration=await read("database/migrations/0043_production_test_only_lineage_cleanup.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"adc47bc0c6c20a8178b124534866ebd0121f1d08725cce7dc62f3b6bf0a113cc");
  assert.ok(manifest.includes("adc47bc0c6c20a8178b124534866ebd0121f1d08725cce7dc62f3b6bf0a113cc"));
  assert.match(neon,/MAX_SUPPORTED_MIGRATION_COUNT = 43/);

  for(const marker of [
    "TEST-PRJ-001","TEST_ONLY","TEST-1","TEST-TPL-VIDEO","TEST-GOAL-001","TEST-OUTPUT",
    "CLEANUP0043_TEST_WORK_PACKAGE_MARKER_INVALID",
    "CLEANUP0043_TEST_BLUEPRINT_VERSION_MARKER_INVALID",
    "CLEANUP0043_TEST_MOTHER_REVIEW_MARKER_INVALID",
    "CLEANUP0043_TEST_CHILD_REVIEW_MARKER_INVALID",
    "CLEANUP0043_TEST_TEMPLATE_SHARED",
    "CLEANUP0043_TEST_OUTPUT_CONTRACT_SHARED",
    "CLEANUP0043_TEST_MASTER_BLUEPRINT_SHARED",
  ])assert.ok(migration.includes(marker),marker);

  assert.match(migration,/IF v_project IS NULL THEN\s+RETURN;/);
  assert.match(migration,/UPDATE public\.work_packages SET dag_snapshot_id=NULL/);
  assert.match(migration,/UPDATE public\.topic_blueprints SET active_version_id=NULL/);
  assert.match(migration,/DELETE FROM public\.department_tasks/);
  assert.match(migration,/DELETE FROM public\.lock_reviews/);
  assert.match(migration,/DELETE FROM public\.projects/);
  assert.match(migration,/DELETE FROM public\.notifications/);
  assert.match(migration,/notification_type='TEST_SETUP'/);
  assert.match(migration,/delete_after_test/);
  const businessInsert=migration.slice(0,idx).match(/INSERT INTO public\.(?!schema_migration_history)/g)??[];
  assert.equal(businessInsert.length,0,"0043 must not create business rows");
});
