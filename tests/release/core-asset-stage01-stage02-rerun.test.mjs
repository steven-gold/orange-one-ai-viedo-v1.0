import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (p) => fs.readFileSync(p, 'utf8');
const hasAll = (text, values) => values.every((v) => text.includes(v));

const state = read('docs/construction/evidence/CORE_ASSET_STAGE01_RERUN_STATE_2026-09-14.yaml');
const manifest = read('authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml');
const coreAuth = read('authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml');
const assetAuth = read('authority/pages/workspace/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml');
const coreRuntime = read('src/domain/core/coreRuntimeContract.ts');
const corePermission = read('src/domain/core/coreCreationPermissionAdapter.ts');
const coreDraft = read('src/domain/core/coreDraftFormAdapter.ts');
const bounded = read('docs/governance/candidates/v2.1.14/BOUNDED_FUNCTIONAL_COMPLETION_DELTA.yaml');
const topology = read('docs/governance/candidates/v2.1.14/INTERACTION_TOPOLOGY_AI_CONTINUITY_DELTA.yaml');

test('targeted rerun result is scoped exactly to CORE-01 and ASSET-01; other pages/global state are preserved', () => {
  assert.match(state, /status:\s*TARGETED_RERUN_VALIDATED/);
  assert.match(state, /scope_mode:\s*EXACT_PAGE_SCOPE_ONLY/);
  assert.match(state, /workspace:CORE-01/);
  assert.match(state, /workspace:ASSET-01/);
  assert.equal((state.match(/stage_01_status:\s*PASS/g) || []).length, 2);
  assert.equal((state.match(/stage_02_status:\s*BLOCKED/g) || []).length, 1);
  assert.equal((state.match(/stage_02_status:\s*PASS_TARGETED_CONTRACT_AUDIT/g) || []).length, 1);
  assert.match(state, /release_gate_run_number:\s*1291/);
  assert.match(state, /release_gate_conclusion:\s*SUCCESS/);
  assert.match(state, /all_other_current_pages:\s*PRESERVE_CURRENT_STATE/);
  assert.match(state, /current_execution_state_json:\s*NO_GLOBAL_STAGE_RESET/);
  assert.match(state, /production_runtime:\s*NO_MUTATION/);
  assert.match(state, /deployment:\s*NO_MUTATION/);
});

test('Stage-01 intake resolves both exact Current Authority inputs and does not use unlisted authority', () => {
  const corePath = 'authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml';
  const assetPath = 'authority/pages/workspace/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml';
  assert.ok(manifest.includes(corePath));
  assert.ok(manifest.includes(assetPath));
  assert.match(manifest, /only_listed_files_are_current_authority:\s*true/);
  assert.match(manifest, /unlisted_authority_or_spec_file:\s*DO_NOT_LOAD_FOR_CURRENT_CONSTRUCTION/);
  for (const authority of [coreAuth, assetAuth]) {
    assert.match(authority, /status:\s*FINAL_LOCKED/);
    assert.match(authority, /current_only:\s*true/);
    assert.match(authority, /legacy_merge:\s*FORBIDDEN/);
  }
});

test('CORE-01 Stage-02 correctly remains BLOCKED on lifecycle and topology defects', () => {
  assert.ok(hasAll(coreAuth, ['STORY', 'CHAPTER', 'WORLD_SETTING', 'DNA', 'BLUEPRINT']));

  const chapterPortPresent = /CORE-01-PORT-[A-Z0-9-]*CHAPTER/.test(coreRuntime);
  const worldPortPresent = /CORE-01-PORT-[A-Z0-9-]*WORLD/.test(coreRuntime);
  assert.equal(chapterPortPresent, false, 'Chapter has no formal runtime port');
  assert.equal(worldPortPresent, false, 'World Setting has no formal runtime port');
  assert.match(corePermission, /CoreCreationPermissionKind\s*=\s*"PROJECT"\s*\|\s*"TOPIC"/);
  assert.match(coreDraft, /CoreDraftFormKind\s*=\s*"PROJECT"\s*\|\s*"TOPIC"/);
  assert.ok(coreRuntime.includes('/v1/topics/{id}/blueprints'), 'Blueprint create is currently Topic-scoped');

  const message = coreAuth.indexOf('section_uid: CORE-01-SEC-04');
  const decision = coreAuth.indexOf('section_uid: CORE-01-SEC-05');
  const runtime = coreAuth.indexOf('section_uid: CORE-01-SEC-06');
  const composer = coreAuth.indexOf('section_uid: CORE-01-SEC-07');
  assert.ok(message >= 0 && decision > message && runtime > decision && composer > runtime,
    'Current visual topology places Evaluation/Decision and Runtime between Message Workspace and Input Composer');
  assert.ok(hasAll(coreAuth, ['name: Message Workspace', 'name: Evaluation / Human Decision', 'name: Runtime Stage Strip', 'name: Input Composer']));
  assert.ok(topology.includes('FUNCTIONAL_WORKBENCH_COHESION'));
  assert.ok(topology.includes('INTERACTION_TOPOLOGY_BINDING'));
  assert.ok(topology.includes('unrelated_surface_interrupting_atomic_workbench'));
  assert.ok(topology.includes('functional_unit_present_but_fragmented_across_unapproved_surfaces'));

  const blockers = [
    !chapterPortPresent,
    !worldPortPresent,
    /CoreCreationPermissionKind\s*=\s*"PROJECT"\s*\|\s*"TOPIC"/.test(corePermission),
    /CoreDraftFormKind\s*=\s*"PROJECT"\s*\|\s*"TOPIC"/.test(coreDraft),
    coreRuntime.includes('/v1/topics/{id}/blueprints'),
    message >= 0 && decision > message && runtime > decision && composer > runtime,
  ];
  assert.ok(blockers.every(Boolean));
  assert.equal(blockers.some(Boolean) ? 'BLOCKED' : 'PASS', 'BLOCKED');
});

test('ASSET-01 Stage-02 action/gate/runtime contract is closed for the targeted audit', () => {
  assert.ok(hasAll(assetAuth, [
    'ASSET-01-GATE-CONTEXT', 'ASSET-01-GATE-EXECUTE', 'ASSET-01-GATE-EVALUATION',
    'ASSET-01-GATE-CORRECTION', 'ASSET-01-GATE-CONFIRM', 'ASSET-01-GATE-LOCK', 'ASSET-01-GATE-HANDOFF',
    'ASSET-01-ACT-FLOW-START', 'ASSET-01-ACT-EVALUATE', 'ASSET-01-ACT-CANDIDATE-CONFIRM',
    'ASSET-01-ACT-CORRECTION-OPEN', 'ASSET-01-ACT-CORRECTION-GENERATE', 'ASSET-01-ACT-CORRECTION-APPROVE',
    'ASSET-01-ACT-CORRECTION-EXECUTE', 'ASSET-01-ACT-TASK-RETRY', 'ASSET-01-ACT-VERSION-LOCK',
    'ASSET-01-ACT-HANDOFF', 'ASSET-01-ACT-LAYER-DOC-CREATE', 'ASSET-01-ACT-LAYER-DOC-UPDATE',
    'ASSET-01-ACT-LAYER-ADD', 'ASSET-01-ACT-LAYER-DELETE', 'ASSET-01-ACT-LAYER-REORDER',
    'ASSET-01-ACT-PATCH-CREATE', 'ASSET-01-ACT-PATCH-PREVIEW', 'ASSET-01-ACT-PATCH-ACCEPT', 'ASSET-01-ACT-PATCH-REJECT'
  ]));
  assert.ok(hasAll(assetAuth, [
    'section_uid: ASSET-01-SEC-06', 'name: Correction Conversation',
    'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY', 'generateCorrectionScriptCandidate', 'approveCorrectionScriptCandidate',
    'result: NEW candidate/version; never overwrite source version'
  ]));

  const actionsStart = assetAuth.indexOf('  actions:\n');
  const controlsStart = assetAuth.indexOf('  controls:\n');
  assert.ok(actionsStart >= 0 && controlsStart > actionsStart);
  const actionRegistry = assetAuth.slice(actionsStart, controlsStart);
  const actionBlocks = actionRegistry.split(/\n  - action_uid:/).slice(1).map((b) => `action_uid:${b}`);
  assert.ok(actionBlocks.length >= 30, `expected substantial ASSET action registry, got ${actionBlocks.length}`);

  for (const block of actionBlocks) {
    const uid = block.match(/action_uid:\s*([^\n]+)/)?.[1]?.trim() || 'UNKNOWN';
    assert.match(block, /permission_uid:/, `${uid} missing permission`);
    assert.match(block, /gate_uid:/, `${uid} missing gate`);
    assert.match(block, /effect_type:/, `${uid} missing effect type`);
    assert.match(block, /runtime_binding:/, `${uid} missing runtime binding`);
    const effect = block.match(/effect_type:\s*([^\n]+)/)?.[1]?.trim();
    if (!['UI_ONLY', 'CONTEXT_STATE'].includes(effect)) {
      assert.ok(/port_uid:|persist_via_port_uid:|shared_operation_id:/.test(block), `${uid} effectful action lacks formal runtime owner/port`);
    }
  }
  assert.equal('PASS_TARGETED_CONTRACT_AUDIT', 'PASS_TARGETED_CONTRACT_AUDIT');
});

test('targeted rerun uses bounded completion and conditional interaction/AI governance without expanding scope', () => {
  assert.ok(bounded.includes('BOUNDED_FUNCTIONAL_COMPLETION'));
  assert.ok(bounded.includes('FUNCTION_VISUAL_SYNCHRONIZED_COMPLETION'));
  assert.ok(topology.includes('AI_CONVERSATION'));
  assert.ok(topology.includes('AI_ASSISTED_WORKSPACE'));
  assert.ok(topology.includes('MULTI_AGENT_INTERACTION'));
  assert.ok(topology.includes('CONVERSATION_IDENTITY_CONTINUITY'));
  assert.ok(topology.includes('AI_OUTPUT_FORMALIZATION_BOUNDARY'));
  assert.ok(topology.includes('REVISION_CONTEXT_CONTINUITY'));
  assert.ok(topology.includes('BRANCH_CONTEXT_ISOLATION_AND_ADOPTION'));
});
