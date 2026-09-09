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
  assert.equal(checksum,"b56af22f743bafc0fcfc6dffd8856123da77d705f4e64c6120d2e7096bcd2c97");
  assert.ok(manifest.includes("b56af22f743bafc0fcfc6dffd8856123da77d705f4e64c6120d2e7096bcd2c97"));
  assert.match(neon,/MAX_SUPPORTED_MIGRATION_COUNT = 43/);

  for(const marker of [
    "TEST-PRJ-001","TEST_ONLY","TEST-1","TEST-TPL-VIDEO","TEST-GOAL-001","TEST-OUTPUT",
    "CLEANUP0043_TEST_WORK_PACKAGE_MARKER_INVALID",
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
  const businessInsert=migration.slice(0,idx).match(/INSERT INTO public\.(?!schema_migration_history)/g)??[];
  assert.equal(businessInsert.length,0,"0043 must not create business rows");
});
