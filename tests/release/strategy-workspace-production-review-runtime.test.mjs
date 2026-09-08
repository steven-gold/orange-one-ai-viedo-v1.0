import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("STR-01 projection uses session-bound RLS and immutable candidate fingerprint for review/adopt gating", async () => {
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");

  assert.match(projection, /runRlsActorQuery\([\s\S]*FROM strategy_candidates s/);
  assert.match(projection, /encode\(digest\(concat_ws\('\|'/);
  assert.match(projection, /candidate_version_ref: firstCandidate\?\.version_ref \?\? null/);
  assert.match(projection, /candidateState === "DECISION_PENDING"[\s\S]*"REVIEW_REQUIRED"/);
  assert.match(projection, /candidateState === "APPROVED"[\s\S]*"ADOPTED_CONTEXT"/);
  assert.match(projection, /"STR-01-GATE-REVIEW": candidateState === "CANDIDATE"/);
  assert.match(projection, /"STR-01-GATE-ADOPT": candidateState === "DECISION_PENDING" && approvedReviewReady/);
  assert.match(projection, /FROM decision_requests d/);
  assert.match(projection, /d\.state='APPROVED'/);
  assert.match(projection, /FROM strategy_decisions d/);
});

test("STR-01 Production lifecycle creates governance review request and never self-approves adoption", async () => {
  const runtime = await read("src/server/strategy/productionStrategyDecisionRuntime.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");
  const client = await read("src/domain/strategy/strategyCommandPort.ts");

  assert.match(runtime, /decision_status='CANDIDATE'/);
  assert.match(runtime, /INSERT INTO public\.decision_requests/);
  assert.match(runtime, /'STRATEGY_CANDIDATE_HUMAN_REVIEW_REQUIRED'/);
  assert.match(runtime, /'OPEN'/);
  assert.match(runtime, /SET decision_status='DECISION_PENDING'/);
  assert.match(runtime, /d\.state='APPROVED'/);
  assert.match(runtime, /d\.decided_by_user_id IS NOT NULL/);
  assert.match(runtime, /NULLIF\(d\.decision_reason,''\) IS NOT NULL/);
  assert.match(runtime, /d\.evidence_refs<>'\[\]'::jsonb/);
  assert.match(runtime, /SET decision_status='APPROVED'/);
  assert.match(runtime, /INSERT INTO public\.strategy_decisions/);
  assert.match(runtime, /'ADOPT_CONTEXT'/);
  assert.match(runtime, /false AS owner_execution_performed/);
  assert.doesNotMatch(runtime, /UPDATE public\.decision_requests[\s\S]*state='APPROVED'/);

  assert.match(identity, /submitStrategyReview:\{resource_key:"api:submitStrategyReview",action:"EXECUTE"\}/);
  assert.match(identity, /adoptAsContextCandidate:\{resource_key:"api:adoptAsContextCandidate",action:"EXECUTE"\}/);
  assert.match(identity, /configureStrategyDecisionRuntime\(\{[\s\S]*authorize: authorizeStrategyDecision,[\s\S]*execute: executeProductionStrategyDecision/);

  assert.match(client, /input\.action_uid==='STR-01-ACT-REVIEW'\|\|input\.action_uid==='STR-01-ACT-ADOPT'/);
  assert.match(client, /candidate_ref:input\.candidate_ref,candidate_version_ref:input\.candidate_version_ref/);
  assert.doesNotMatch(client, /currentBuild[\s\S]*human_review:\{decision:'APPROVED'/);
});

test("migration 0028 reuses existing Strategy owners and stages only two exact API assignments", async () => {
  const migration = await read("database/migrations/0028_strategy_human_review_permission_rls_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");

  assert.match(migration, /api:submitStrategyReview/);
  assert.match(migration, /api:adoptAsContextCandidate/);
  assert.match(migration, /resource_count <> 2/);
  assert.match(migration, /approved_allow_count <> 2/);
  assert.match(migration, /has_strategy_resource_action/);
  assert.match(migration, /page:workspace:STR-01/);
  assert.match(migration, /ALTER TABLE public\.strategy_candidates ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /ALTER TABLE public\.strategy_decisions ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /ALTER TABLE public\.decision_requests ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /policy_count <> 6/);
  assert.match(migration, /fbfb62018cdc45e2df51bb8262647a468845a7cdc98439e092453421949f865e/);
  assert.doesNotMatch(migration, /INSERT INTO public\.permission_resources/);
  assert.doesNotMatch(migration, /CREATE TABLE/);
  assert.doesNotMatch(migration, /INSERT INTO public\.strategy_candidates/);
  assert.doesNotMatch(migration, /INSERT INTO public\.strategy_decisions/);
  assert.doesNotMatch(migration, /INSERT INTO public\.decision_requests/);

  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.15/);
  assert.match(manifest, /migration_id: 0028_strategy_human_review_permission_rls_closure/);
  assert.match(manifest, /payload_sha256: fbfb62018cdc45e2df51bb8262647a468845a7cdc98439e092453421949f865e/);
  assert.match(manifest, /approval_ref: CR-STR-0028-PENDING-PRODUCTION-APPLY/);
  assert.ok(Number(neonRuntime.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1] ?? 0) >= 28);
});
