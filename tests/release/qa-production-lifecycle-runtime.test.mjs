import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("QA-01 Production projection resolves exact QA handoff output and approved criteria without latest-output guessing", async () => {
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");

  assert.match(projection, /h0\.target_task_id=t\.task_id/);
  assert.match(projection, /h0\.status IN \('HANDOFF_READY','HANDED_OFF'\)/);
  assert.match(projection, /handed_off_output_version_id/);
  assert.match(projection, /FROM quality_criteria_versions/);
  assert.match(projection, /WHERE status='APPROVED'/);
  assert.match(projection, /"QA-01-GATE-START": Boolean\(first\?\.task_id && first\?\.handed_off_output_version_id && criteria\?\.ref\)/);
  assert.doesNotMatch(projection, /FROM task_outputs[\s\S]{0,220}ORDER BY created_at DESC[\s\S]{0,120}QA-01-GATE-START/);
});

test("QA-01 lifecycle runtime requires real canonical owners and never synthesizes provider score or release evidence", async () => {
  const runtime = await read("src/server/qa/productionQaLifecycleRuntime.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");
  const qaRuntime = await read("src/server/qa/qaRuntime.ts");

  assert.match(runtime, /JOIN public\.handoffs h/);
  assert.match(runtime, /h\.target_task_id=t\.task_id/);
  assert.match(runtime, /h\.source_output_version_id=\$\{outputVersionId\}::uuid/);
  assert.match(runtime, /JOIN public\.quality_criteria_versions q/);
  assert.match(runtime, /q\.status='APPROVED'/);
  assert.match(runtime, /INSERT INTO public\.qa_review_runs/);
  assert.match(runtime, /ON CONFLICT \(qa_task_id,output_version_id\) DO NOTHING/);

  assert.match(runtime, /JOIN public\.correction_requests cr/);
  assert.match(runtime, /h\.created_at>=cr\.created_at/);
  assert.match(runtime, /SET output_version_id=e\.verified_new_output_version_id/);
  assert.match(runtime, /status='RECHECK'/);

  assert.match(runtime, /FROM public\.scorecards s/);
  assert.match(runtime, /s\.gate_status=\$\{decision\}/);
  assert.match(runtime, /f\.closed_at IS NULL/);
  assert.match(runtime, /m\.decided_at IS NULL/);
  assert.match(runtime, /QA01_PASS_GATE_NOT_SATISFIED/);
  assert.match(runtime, /QA01_FAIL_GATE_NOT_SATISFIED/);

  assert.match(runtime, /QA01_RELEASE_RIGHTS_POLICY_EVIDENCE_REQUIRED/);
  assert.match(runtime, /QA01_RELEASE_RIGHTS_PROFILE_NOT_VERIFIABLE/);
  assert.match(runtime, /QA01_RELEASE_EVIDENCE_OWNER_NOT_MATERIALIZED/);
  assert.doesNotMatch(runtime, /INSERT INTO public\.release_packages/);
  assert.doesNotMatch(runtime, /submitScorecard|providerHttp|fetch\(/);

  for (const operation of ["startQaReview","startRecheck","decidePass","decideFail","createReleasePackage"]) {
    assert.ok(identity.includes(operation + ':{resource_key:"api:' + operation + '",action:"EXECUTE"}'), operation);
  }
  assert.match(identity, /configureQaRuntime\(\{[\s\S]*authorize: authorizeQa,[\s\S]*execute: executeQa/);
  assert.match(qaRuntime, /function statusFor\(reason_code: string\)/);
});

test("migration 0027 stages only five existing QA lifecycle API assignments and the missing RLS owner", async () => {
  const migration = await read("database/migrations/0027_qa_review_lifecycle_permission_rls_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");

  for (const resource of [
    "api:startQaReview",
    "api:startRecheck",
    "api:decidePass",
    "api:decideFail",
    "api:createReleasePackage",
  ]) assert.ok(migration.includes(resource), resource);

  assert.match(migration, /resource_count <> 5/);
  assert.match(migration, /approved_allow_count <> 5/);
  assert.match(migration, /GRANT SELECT ON public\.quality_criteria_versions TO acpos_app_runtime/);
  assert.match(migration, /UPDATE\(status,output_version_id,decision_reason,decided_at\)/);
  assert.match(migration, /ALTER TABLE public\.qa_review_runs ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /acpos_qa_review_runs_insert/);
  assert.match(migration, /acpos_qa_review_runs_update/);
  assert.match(migration, /9309b61424bbd72adace0e7da86836bc6ac429e4b99c96a5a2105fec10979c19/);
  assert.doesNotMatch(migration, /INSERT INTO public\.permission_resources/);
  assert.doesNotMatch(migration, /INSERT INTO public\.qa_review_runs/);
  assert.doesNotMatch(migration, /INSERT INTO public\.scorecards/);
  assert.doesNotMatch(migration, /INSERT INTO public\.release_packages/);

  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.14/);
  assert.match(manifest, /migration_id: 0027_qa_review_lifecycle_permission_rls_closure/);
  assert.match(manifest, /payload_sha256: 9309b61424bbd72adace0e7da86836bc6ac429e4b99c96a5a2105fec10979c19/);
  assert.match(manifest, /approval_ref: CR-QA-0027-PENDING-PRODUCTION-APPLY/);
  assert.match(neonRuntime, /MAX_SUPPORTED_MIGRATION_COUNT = 27/);
});
