import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("CORE Current governed ports bind the existing API resources and dedicated Production owner",async()=>{
  const authority=await read("authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml");
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  assert.match(authority,/Compare Candidates[\s\S]*effect_type: READ_ONLY[\s\S]*Read comparison only; no version mutation/);
  assert.match(identity,/executeProductionCoreGovernedPort/);
  assert.match(identity,/isProductionCoreGovernedPort/);
  for(const key of [
    "api:createProjectDraft","api:validateProjectDraft","api:confirmProjectDraft","api:createStoryCandidateSet","api:createConversationThread","api:sendConversationMessage","api:createCandidate","api:compareCandidates","api:decideCandidate","api:requestDNALock","api:submitCoreReview",
    "api:createBlueprint","api:validateBlueprint","api:approveBlueprint","api:requestChildLock","api:getCanonicalScript","api:requestMotherLock","api:createTopic",
  ]) assert.ok(identity.includes(key),key);
  assert.match(runtime,/public\.candidate_versions/);
  assert.match(runtime,/public\.candidate_decisions/);
  assert.doesNotMatch(runtime,/story_candidates|story_candidate_comparisons/);
  assert.match(runtime,/read_only:true,version_mutation:false/);
  assert.match(runtime,/decisionInput==="RETURN"\?"MODIFY_REQUESTED"/);
});

test("CORE Story Candidate direct API cannot invent candidate_key",async()=>{
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  assert.match(identity,/const candidate_key = requirePayloadText\(payload, "candidate_key"\)/);
  assert.doesNotMatch(identity,/STORY-\$\{Date\.now\(\)/);
  assert.match(identity,/requirePayloadJson\(payload, "content"\)/);
  assert.match(identity,/requirePayloadJson\(payload, "strengths"\)/);
  assert.match(identity,/requirePayloadJson\(payload, "weaknesses"\)/);
});

test("CORE legacy mutation ports enforce their registered API resources server-side",async()=>{
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const expected={
    "CORE-01-PORT-PROJECT-VALIDATE":"api:validateProjectDraft",
    "CORE-01-PORT-PROJECT-CONFIRM":"api:confirmProjectDraft",
    "CORE-01-PORT-STORY-CANDIDATE":"api:createStoryCandidateSet",
    "CORE-01-PORT-THREAD-CREATE":"api:createConversationThread",
    "CORE-01-PORT-MESSAGE-SEND":"api:sendConversationMessage",
  };
  for(const [port,resource] of Object.entries(expected)){
    assert.ok(identity.includes(`"${port}":"${resource}"`),`${port} -> ${resource}`);
  }
});

test("CORE ConversationThread work-item lineage has a dedicated immutable owner and exact UI scope",async()=>{
  const migration=await read("database/migrations/0038_core_conversation_thread_work_item_lineage.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const projection=await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const adapter=await read("src/domain/core/coreProjectionAdapter.ts");
  const visual=await read("src/components/pages/CoreVisual.tsx");

  assert.match(migration,/CREATE TABLE public\.core_conversation_thread_bindings/);
  for(const column of ["conversation_id","project_id","topic_id","work_item","parent_conversation_id","source_message_id","relation_kind","created_by"]){
    assert.ok(migration.includes(column),column);
  }
  assert.match(migration,/core_conversation_thread_mode_check/);
  assert.match(migration,/core_conversation_thread_relation_check/);
  assert.match(migration,/validate_core_conversation_thread_binding/);
  assert.match(migration,/CORE0038_TOPIC_PROJECT_LINEAGE_MISMATCH/);
  assert.match(migration,/CORE0038_PARENT_THREAD_SCOPE_MISMATCH/);
  assert.match(migration,/CORE0038_SOURCE_MESSAGE_PARENT_MISMATCH/);
  assert.match(migration,/CORE0038_BOUND_CONVERSATION_LINEAGE_IMMUTABLE/);
  assert.match(migration,/core_bound_conversation_lineage_guard/);
  assert.match(migration,/ALTER TABLE public\.core_conversation_thread_bindings ENABLE ROW LEVEL SECURITY/);
  assert.match(migration,/GRANT SELECT,INSERT ON public\.core_conversation_thread_bindings TO acpos_app_runtime/);
  assert.match(migration,/384e62c682f00d7380c22d5c64a66e1a509b59e9d9bb9dd645474bbf689d6b9d/);
  assert.match(manifest,/0038_core_conversation_thread_work_item_lineage[\s\S]*384e62c682f00d7380c22d5c64a66e1a509b59e9d9bb9dd645474bbf689d6b9d/);
  assert.match(neon,/MAX_SUPPORTED_MIGRATION_COUNT = 42/);

  assert.match(identity,/runRlsActorTransaction/);
  assert.match(identity,/INSERT INTO core_conversation_thread_bindings/);
  assert.match(identity,/WORK_ITEM_NOT_ALLOWED_IN_CURRENT_MODE/);
  assert.match(identity,/TOPIC_PROJECT_LINEAGE_MISMATCH/);
  assert.match(identity,/BRANCH_THREAD_SCOPE_MISMATCH/);
  assert.doesNotMatch(identity,/const title = `\$\{work_item\} \/ \$\{new Date\(\)\.toISOString\(\)\}`/);

  assert.match(projection,/JOIN core_conversation_thread_bindings b ON b\.conversation_id=c\.conversation_id/);
  assert.match(projection,/const currentConversationId: string \| null = null/);
  assert.match(adapter,/project_id: string; topic_id: string \| null; work_item: string/);
  assert.match(visual,/PROJECT_CORE_WORK_ITEMS/);
  assert.match(visual,/TOPIC_PRODUCTION_WORK_ITEMS/);
  assert.match(visual,/visibleThreads/);
  assert.match(visual,/visibleTopics/);
  assert.match(visual,/item\.project_id === clientState\.project_id/);
  assert.match(visual,/THREAD_NOT_IN_CURRENT_CONTEXT/);
});

test("CORE Project validate verifies stored draft lineage and Confirm blocks unresolved adopt contract",async()=>{
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  assert.match(runtime,/"CORE-01-PORT-PROJECT-VALIDATE"/);
  assert.match(runtime,/"CORE-01-PORT-PROJECT-CONFIRM"/);
  assert.match(runtime,/PROJECT_DRAFT_CONTENT_HASH_MISMATCH/);
  assert.match(runtime,/workspace_status/);
  assert.match(runtime,/decision_reason='VALIDATED'/);
  assert.match(runtime,/PROJECT_CONFIRM_ADOPT_CONTRACT_NOT_BOUND/);
  assert.doesNotMatch(identity,/case "CORE-01-PORT-PROJECT-VALIDATE"/);
  assert.doesNotMatch(identity,/case "CORE-01-PORT-PROJECT-CONFIRM"/);
});

test("CORE Project draft creation requires registered fields and has no owner or naming fallback",async()=>{
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  assert.match(identity,/"CORE-01-PORT-PROJECT-CREATE":"api:createProjectDraft"/);
  assert.doesNotMatch(identity,/case "CORE-01-PORT-PROJECT-CREATE"[\s\S]*slugCode\(/);
  assert.match(runtime,/"CORE-01-PORT-PROJECT-CREATE"/);
  for(const field of ["workspace_id","project_code","title","story_core"]){
    assert.ok(runtime.includes(field),field);
  }
  assert.match(runtime,/PROJECT_DRAFT_REGISTERED_SCHEMA_PAYLOAD_REQUIRED/);
  assert.doesNotMatch(runtime,/slugCode\(title/);
  assert.doesNotMatch(runtime,/story_core\s*=\s*JSON\.stringify\(\{ title \}\)/);
  assert.match(runtime,/runRlsActorTransaction/);
});

test("CORE Topic creation requires exact canonical lineage and uses only session-bound RLS writes",async()=>{
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  const rls=await read("src/server/database/rlsRuntime.ts");
  assert.match(identity,/"CORE-01-PORT-TOPIC-CREATE":"api:createTopic"/);
  assert.doesNotMatch(identity,/case "CORE-01-PORT-TOPIC-CREATE"[\s\S]*slugCode\(/);
  assert.match(runtime,/"CORE-01-PORT-TOPIC-CREATE"/);
  assert.match(runtime,/TOPIC_CANONICAL_LINEAGE_INCOMPLETE/);
  for(const field of ["topic_code","mother_lock_ref","mother_project_version_ref","boundary","bridge"]){
    assert.ok(runtime.includes(field),field);
  }
  assert.doesNotMatch(runtime,/slugCode\(title/);
  assert.doesNotMatch(runtime,/const boundary\s*=\s*JSON\.stringify\(\{ title \}\)/);
  assert.doesNotMatch(runtime,/const bridge\s*=\s*JSON\.stringify\(\{\}\)/);
  assert.match(runtime,/runRlsActorTransaction/);
  assert.match(rls,/export async function runRlsActorTransaction/);
});

test("CORE Candidate and Blueprint creation fail closed instead of fabricating Current business objects",async()=>{
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  assert.match(runtime,/CORE_STRUCTURED_DECISION_REQUIRED/);
  assert.match(runtime,/core_structured_decisions/);
  assert.match(runtime,/core_human_decisions/);
  assert.match(runtime,/core_evaluations/);
  assert.match(runtime,/e\.result='PASS'/);
  assert.match(runtime,/COALESCE\(schema->>'purpose',''\)<>'TEST_ONLY'/);
  assert.match(runtime,/MASTER_BLUEPRINT_AUTHORITY_NOT_READY/);
  assert.match(runtime,/CORE_BLUEPRINT_DOCUMENT_MATERIALIZER_NOT_BOUND/);
  assert.match(runtime,/CORE_LOCK_REVIEWER_PATH_UNRESOLVED/);
  assert.match(runtime,/LOCK_CRITERIA_VERSION_REQUIRED/);
  assert.match(runtime,/LOCK_EVIDENCE_REQUIRED/);
  assert.match(runtime,/acpos_runtime\.request_lock_review/);
  assert.doesNotMatch(runtime,/reviewer_path\s*=\s*JSON\.stringify\(\[\]\)/);
  assert.doesNotMatch(runtime,/blueprint_document\s*=\s*JSON\.stringify\(\{\s*topic_id/);
});

test("CORE DNA review and canonical script reads preserve exact authority lineage",async()=>{
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  assert.match(runtime,/resource_key='api:requestDNALock'/);
  assert.match(runtime,/required_action[\s\S]*?'EXECUTE'/);
  assert.match(runtime,/expected_checksum/);
  assert.match(runtime,/CANONICAL_SCRIPT_LINEAGE_UNRESOLVED/);
  assert.match(runtime,/project_blueprint_ref/);
  assert.match(runtime,/topic_production_scope_ref/);
  assert.match(runtime,/source_candidate_ref/);
  assert.match(runtime,/d\.decision='ACCEPTED'/);
  assert.match(runtime,/lineage_complete:true,read_only:true/);
});

test("migration 0037 grants only existing CORE API resources and closes missing session-bound RLS",async()=>{
  const migration=await read("database/migrations/0037_core_governed_runtime_permission_rls_closure.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  assert.match(migration,/CORE0037_API_RESOURCE_COUNT_MISMATCH/);
  assert.match(migration,/resource_count<>18/);
  assert.match(migration,/CORE0037_ASSIGNMENT_COUNT_MISMATCH/);
  assert.match(migration,/assignment_count<>18/);
  for(const table of [
    "topic_versions","topic_production_contracts","master_blueprints","topic_blueprints","blueprint_versions",
    "dna_versions","lock_reviews","decision_requests","canonical_script_versions",
  ]) assert.match(migration,new RegExp(`ALTER TABLE public\\.${table} ENABLE ROW LEVEL SECURITY`),table);
  assert.match(migration,/acpos_runtime\.can_access_project/);
  assert.match(migration,/acpos_runtime\.can_manage_project/);
  assert.match(migration,/7385e677951edd84d440fe124c68e0772e199b071770fc54c0cd1a7f639a74e8/);
  assert.doesNotMatch(migration,/INSERT INTO public\.(candidate_versions|blueprint_versions|dna_versions|canonical_script_versions)/);
  assert.match(manifest,/0037_core_governed_runtime_permission_rls_closure/);
  assert.match(manifest,/7385e677951edd84d440fe124c68e0772e199b071770fc54c0cd1a7f639a74e8/);
  const ceiling=Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1] ?? 0);
  assert.ok(ceiling>=37,`migration ceiling must include 0037, found ${ceiling}`);
});

test("CORE projection resolves Current candidate DNA blueprint and script refs from canonical owners",async()=>{
  const projection=await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  for(const owner of [
    "candidate_versions","core_evaluations","core_structured_decisions","candidate_decisions",
    "dna_versions","blueprint_versions","topic_production_contracts","canonical_script_versions","lock_reviews",
  ]) assert.ok(projection.includes(owner),owner);
  assert.match(projection,/dna_version_ref: asText\(currentDna\.dna_version_ref\)/);
  assert.match(projection,/blueprint_version_ref: asText\(currentBlueprint\.blueprint_version_ref\)/);
  assert.match(projection,/candidate_ref: asText\(currentCandidate\.candidate_ref\)/);
  assert.match(projection,/canonical_script_source_candidate_ref/);
});


test("CORE Current visual exposes real prerequisite gates instead of busy-only enabled controls",async()=>{
  const visual=await read("src/components/pages/CoreVisual.tsx");
  assert.match(visual,/coreControlDisabledReason/);
  for(const reason of [
    "PROJECT_VERSION_REQUIRED",
    "PROJECT_AND_WORK_ITEM_REQUIRED",
    "CONVERSATION_REQUIRED",
    "HUMAN_DECISION_REQUIRED",
    "EXACT_CANDIDATE_REF_REQUIRED",
    "PROJECT_CONFIRM_ADOPT_CONTRACT_NOT_BOUND",
    "CORE_LOCK_REVIEWER_PATH_UNRESOLVED",
    "CORE_BLUEPRINT_DOCUMENT_MATERIALIZER_NOT_BOUND",
    "EXACT_BLUEPRINT_VERSION_REF_REQUIRED",
  ]) assert.ok(visual.includes(reason),reason);
  assert.match(visual,/data-disabled-reason=\{disabled \? disabledReason/);
  assert.match(visual,/data-runtime-binding=\{disabled \? "BLOCKED" : "ACTION_BOUND"\}/);
  assert.doesNotMatch(visual,/<ActionButton[^>]+disabled=\{isBusy\}/);
  assert.match(visual,/CORE-01-FLD-MESSAGE"[\s\S]*disabled=\{isBusy \|\| !clientState\.conversation_id\}/);
  assert.match(visual,/CORE-01-FLD-HUMAN-DECISION"[\s\S]*disabled=\{isBusy \|\| !clientState\.conversation_id\}/);
});
