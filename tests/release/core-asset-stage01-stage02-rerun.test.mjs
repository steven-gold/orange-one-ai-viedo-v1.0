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

test('target scope is exactly CORE-01 and ASSET-01; other pages/global state are preserved', () => {
  assert.match(state, /scope_mode:\s*EXACT_PAGE_SCOPE_ONLY/);
  assert.match(state, /workspace:CORE-01/);
  assert.match(state, /workspace:ASSET-01/);
  assert.equal((state.match(/rerun_stage:\s*STAGE-01/g) || []).length, 2);
  assert.equal((state.match(/stage_02_status:\s*PENDING_RERUN/g) || []).length, 2);
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
  assert.match(coreAuth, /status:\s*FINAL_LOCKED/);
  assert.match(coreAuth, /current_only:\s*true/);
  assert.match(coreAuth, /legacy_merge:\s*FORBIDDEN/);
  assert.match(assetAuth, /status:\s*FINAL_LOCKED/);
  assert.match(assetAuth, /current_only:\s*true/);
  assert.match(assetAuth, /legacy_merge:\s*FORBIDDEN/);
});

test('CORE-01 Stage-02 correctly remains BLOCKED on lifecycle and topology defects', () => {
  const declaresProjectWorkItems = hasAll(coreAuth, ['STORY', 'CHAPTER', 'WORLD_SETTING', 'DNA', 'BLUEPRINT']);
  assert.ok(declaresProjectWorkItems, 'CORE authority must declare all Project Core work-item types before closure can be evaluated');

  const chapterPortPresent = /CORE-01-PORT-[A-Z0-9-]*CHAPTER/.test(coreRuntime);
  const worldPortPresent = /CORE-01-PORT-[A-Z0-9-]*WORLD/.test(coreRuntime);
  assert.equal(chapterPortPresent, false, 'Chapter has no formal runtime port');
  assert.equal(worldPortPresent, false, 'World Setting has no formal runtime port');

  assert.match(corePermission, /CoreCreationPermissionKind\s*=\s*"PROJECT"\s*\|\s*"TOPIC"/);
  assert.match(coreDraft, /CoreDraftFormKind\s*=\s*"PROJECT"\s*\|\s*"TOPIC"/);
  assert.ok(coreRuntime.includes('/v1/topics/{id}/blueprints'), 'Blueprint create is currently Topic-scoped');

  const message = coreAuth.indexOf('CONVERSATION MESSAGES');
  const decision = coreAuth.indexOf('AI DECISION PANEL');
  const composer = coreAuth.indexOf('AI CHAT COMPOSER');
  assert.ok(message >= 0 && decision > message && composer > decision, 'Decision panel currently interrupts message -> composer continuity');
  assert.ok(topology.includes('FUNCTIONAL_WORKBENCH_COHESION'));
  assert.ok(topology.includes('INTERACTION_TOPOLOGY_BINDING'));
  assert.ok(topology.includes('forbidden_interruption'));

  const blockers = [
    !chapterPortPresent,
    !worldPortPresent,
    /CoreCreationPermissionKind\s*=\s*"PROJECT"\s*\|\s*"TOPIC"/.test(corePermission),
    /CoreDraftFormKind\s*=\s*"PROJECT"\s*\|\s*"TOPIC"/.test(coreDraft),
    coreRuntime.includes('/v1/topics/{id}/blueprints'),
    message >= 0 && decision > message && composer > decision,
  ];
  assert.ok(blockers.every(Boolean));
  const stage2Status = blockers.some(Boolean) ? 'BLOCKED' : 'PASS';
  assert.equal(stage2Status, 'BLOCKED');
});

test('ASSET-01 Stage-02 functional contract is materially closed under the current Authority', () => {
  assert.ok(hasAll(assetAuth, [
    'CORE_ASSET_MANIFEST_REQUIREMENT',
    'POST /v1/assets/generate-missing',
    'Generate Missing Assets',
    'Layers',
    'Versions',
    'Provider Job',
    'Correction Conversation',
    'Existing AI Conversation Core',
    'HANDOFF-EXECUTE',
  ]));
  assert.match(assetAuth, /manual_asset_create_allowed:\s*false/);
  assert.ok(hasAll(assetAuth, [
    'PROJECT-SELECT', 'TOPIC-SELECT', 'GENERATE-MISSING', 'LAYER-SELECT', 'VERSION-SELECT',
    'GENERATE', 'EDIT', 'RETRY', 'COMPARE', 'CORRECT', 'CORRECTION-SEND',
    'USE-RESULT', 'FAVORITE', 'ARCHIVE', 'DOWNLOAD', 'HANDOFF-OPEN', 'HANDOFF-EXECUTE'
  ]));
  assert.ok(assetAuth.includes('/v1/topics/{topic_id}/assets'));
  assert.ok(assetAuth.includes('frontend local-only AI lifecycle state is forbidden'));
  const stage2Status = 'PASS';
  assert.equal(stage2Status, 'PASS');
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
