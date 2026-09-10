import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const workPackagePath="docs/construction/evidence/WORKPACKAGE_CURRENT_AUTHORITY_BLOCKER_2026-09-10.json";
const chainPath="docs/construction/evidence/COMPILER_RUNTIME_CHAIN_PRODUCTION_BLOCKER_2026-09-10.json";

const readJson=async(path)=>JSON.parse(await readFile(path,"utf8"));

test("WorkPackage remains fail-closed while Current operation authority is absent",async()=>{
  const blocker=await readJson(workPackagePath);
  const registry=await readFile("03_api/operation_registry.yaml","utf8");
  assert.equal(blocker.status,"HARD_BLOCKER_AUTHORITY_DECISION_REQUIRED");
  assert.equal(blocker.current_evidence.operation_registry.compileWorkPackage_registered,false);
  assert.equal(blocker.current_evidence.operation_registry.undefined_behavior,"BLOCK + REPORT_AUTHORITY_GAP");
  assert.equal(blocker.current_evidence.production_permission_catalog.resource_key,"api:compileWorkPackage");
  assert.deepEqual(blocker.current_evidence.production_permission_catalog.allowed_actions,["EXECUTE"]);
  assert.equal(blocker.current_evidence.production_permission_catalog.active,true);
  assert.equal(blocker.current_evidence.production_database_runtime.pg_proc_work_package_functions,0);
  assert.equal(blocker.execution_disposition,"BLOCKED_NO_IMPLEMENTATION_UNTIL_CURRENT_AUTHORITY_RESOLVES_CONFLICT");
  assert.doesNotMatch(registry,/^\s*-\s*operation_id:\s*compileWorkPackage\s*$/m);
  assert.ok(Array.isArray(blocker.unblock_requirement)&&blocker.unblock_requirement.length>=6);
  assert.ok(Array.isArray(blocker.prohibited_fixes)&&blocker.prohibited_fixes.length>=4);
});

test("compiler/runtime chain evidence preserves canonical zero-lineage truth without fake materialization",async()=>{
  const blocker=await readJson(chainPath);
  assert.equal(blocker.status,"PRODUCTION_DATA_AND_AUTHORITY_BLOCKED_NO_FABRICATION");
  assert.equal(blocker.upstream_blocker,"WORKPACKAGE_CURRENT_AUTHORITY_BLOCKER_2026-09-10");
  const expected=[
    "work_packages","dag_edges","department_script_views","task_input_manifests","instruction_packages",
    "task_templates","topic_production_goals","output_contracts","rights_profiles","script_projection_rules",
  ];
  assert.deepEqual(Object.keys(blocker.production_counts).sort(),expected.sort());
  for(const key of expected) assert.equal(blocker.production_counts[key],0,`${key} must remain evidence-recorded as zero`);
  assert.equal(blocker.execution_implication.work_package_positive_materialization,false);
  assert.equal(blocker.execution_implication.department_task_orchestration_positive_materialization,false);
  assert.equal(blocker.execution_implication.department_script_view_positive_materialization,false);
  assert.equal(blocker.execution_implication.task_input_manifest_positive_materialization,false);
  assert.equal(blocker.execution_implication.instruction_package_positive_materialization,false);
  assert.match(blocker.rule,/Do not fabricate compiler inputs or Production business rows/);
});
