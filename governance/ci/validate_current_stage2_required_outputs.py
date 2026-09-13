#!/usr/bin/env python3
from pathlib import Path
import subprocess
import yaml

root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
paths={
 'dep':base/'DEPENDENCY_MAP.yaml',
 'detail':base/'STAGE2_DEPENDENCY_MAP.yaml',
 'state':base/'STATE_TRANSITION_LEDGER.yaml',
 'core':base/'CORE-01/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml',
 'asset':base/'ASSET-01/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml',
 'async':base/'ASYNC_PROVIDER_CONTRACT.yaml',
 'shared':base/'SHARED_OWNER_PORT_MAP.yaml',
}

def die(m): raise SystemExit(m)
def load(p):
 try: d=yaml.safe_load(p.read_text(encoding='utf-8'))
 except Exception as e: die(f'parse failure {p}: {e}')
 if not isinstance(d,dict): die(f'mapping required {p}')
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode: die(f'git object missing {p}')
 return r.stdout.strip()

# Immutable predecessor/detail locks: successor artifacts may reference, never rewrite.
locks={
 base/'STAGE2_DEPENDENCY_MAP.yaml':'59acc61d0a6db969bbd08328322b7f5214e6f5cf',
 base/'STATE_TRANSITION_LEDGER.yaml':'f08d7c637a51e29dab01dc8378555d6bc4c9e635',
 root/'00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml':'0c067fb8be186a899b42115a82d71312b4014502',
 root/'00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml':'52bb27bf7eb423ddb13bcac5bd34edbcb369de3a',
 base/'CORE-01/FUNCTIONAL_CHAIN_SPEC.yaml':'6c58345625dc33916461980fe6635ab8b9b1905a',
 base/'ASSET-01/FUNCTIONAL_CHAIN_SPEC.yaml':'28adbde2e99e731206f0e2e73366fa5d0fdb3e02',
 root/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml':'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
 root/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml':'9668e2307c722ea4cf64f93f07c92da1b3abcc28',
}
for p,b in locks.items():
 if gitobj(p)!=b: die(f'predecessor/detail drift {p}')

D=load(paths['dep']); S=load(paths['state']); C=load(paths['core']); A=load(paths['asset']); Q=load(paths['async']); M=load(paths['shared'])
expected_outputs={'FUNCTIONAL_CHAIN_SPEC','DEPENDENCY_MAP','PAGE_CONSTRUCTION_SPEC_PACKAGE','ASYNC_PROVIDER_CONTRACT','SHARED_OWNER_PORT_MAP'}
materialized={'FUNCTIONAL_CHAIN_SPEC',D.get('artifact_type'),C.get('artifact_type'),A.get('artifact_type'),Q.get('artifact_type'),M.get('artifact_type')}
if not expected_outputs.issubset(materialized): die('Stage-02 required output set incomplete')
if D.get('artifact_type')!='DEPENDENCY_MAP' or D.get('operation_uid')!='DEPENDENCY_MAP_COMPILE': die('canonical dependency output identity drift')
ref=D.get('detail_materialization') or {}
if ref.get('ref')!='04_PAGE_FUNCTIONAL_CONTRACT/STAGE2_DEPENDENCY_MAP.yaml' or ref.get('git_blob')!='59acc61d0a6db969bbd08328322b7f5214e6f5cf' or ref.get('payload_duplication') is not False: die('dependency detail binding drift')
sm=D.get('summary') or {}
if sm.get('total')!=171 or sm.get('pages')!={'CORE-01':45,'ASSET-01':126} or sm.get('classes')!={'ARCHITECTURE_GAP':133,'INPUT_SOURCE_GAP':34,'AUTHORITY_GAP':4}: die('canonical dependency summary drift')
if D.get('functional_completion_claim') is not False: die('dependency map false completion claim')

expected_pages={
 'CORE-01':(C,'V218-REPLAY-BP-CORE-01-PAGE-BASE','0c067fb8be186a899b42115a82d71312b4014502','FRESH-RUN-003-CORE-01-FUNCTIONAL-CHAIN-SPEC-V212','6c58345625dc33916461980fe6635ab8b9b1905a',45,{'PAYLOAD_INPUT_CONTRACT_MISSING':16,'AUDIT_EVENT_NODE_MISSING':4,'STATE_TRANSITION_LEDGER_FIELD_MISSING':25},7),
 'ASSET-01':(A,'V218-REPLAY-BP-ASSET-01-PAGE-BASE','52bb27bf7eb423ddb13bcac5bd34edbcb369de3a','FRESH-RUN-003-ASSET-01-FUNCTIONAL-CHAIN-SPEC-V212','28adbde2e99e731206f0e2e73366fa5d0fdb3e02',126,{'PAYLOAD_INPUT_CONTRACT_MISSING':18,'AUDIT_EVENT_NODE_MISSING':9,'STATE_TRANSITION_LEDGER_FIELD_MISSING':25,'FAILURE_STATE_ERROR_BINDING_MISSING':44,'POST_ACTION_VALIDATION_NODE_MISSING':18,'SHARED_OWNER_AUTHORITY_UNRESOLVED':4,'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,'SUCCESS_NEXT_STATE_BINDING_MISSING':7},6),
}
for page,(P,bpuid,bpblob,fsuid,fsblob,total,cats,extn) in expected_pages.items():
 if P.get('artifact_type')!='PAGE_CONSTRUCTION_SPEC_PACKAGE' or P.get('blueprint_type_uid')!='BPTYPE-GOV-003' or P.get('operation_uid')!='PAGE_CONSTRUCTION_SPEC_COMPILE' or P.get('page_uid')!=page: die(f'{page} construction package identity drift')
 if P.get('status')!='OPEN_BLOCKING_GAPS' or P.get('functional_completion_claim') is not False: die(f'{page} construction package closure drift')
 I=P.get('inputs') or {}; bp=I.get('page_base_blueprint') or {}; fs=I.get('functional_chain_spec') or {}
 if (bp.get('blueprint_uid'),bp.get('git_blob'))!=(bpuid,bpblob) or (fs.get('artifact_uid'),fs.get('git_blob'))!=(fsuid,fsblob): die(f'{page} immutable input binding drift')
 if (P.get('gap_materialization') or {}).get('page_gap_total')!=total or (P.get('gap_materialization') or {}).get('category_counts')!=cats: die(f'{page} gap materialization drift')
 if (P.get('state_machine') or {}).get('unresolved_required_field_count')!=25: die(f'{page} transition blocker drift')
 if len(P.get('unresolved_external_authority_refs') or [])!=extn: die(f'{page} external authority preservation drift')
 gate=P.get('construction_gate') or {}
 if gate.get('ready_for_implementation') is not False or gate.get('website_construction_allowed') is not False or gate.get('deployment_allowed') is not False: die(f'{page} construction block drift')
 if P.get('ai_autofill_used') is not False or P.get('inference_used') is not False: die(f'{page} inference/autofill drift')

async_fields=['request_identity','input_fingerprint','idempotency','queued','running','succeeded','failed','cancel','retry_eligibility','callback_result_provenance','output_persistence','audit_correlation']
if Q.get('artifact_type')!='ASYNC_PROVIDER_CONTRACT' or Q.get('operation_uid')!='ASYNC_PROVIDER_CONTRACT_COMPILE' or Q.get('normative_gate_ref')!='WEB-GOV-01-S061': die('async provider contract identity drift')
if Q.get('required_lifecycle_fields')!=async_fields: die('async provider lifecycle field set drift')
qp=Q.get('pages') or {}
if set(qp)!={'CORE-01','ASSET-01'}: die('async provider page scope drift')
if (qp['CORE-01'].get('binding_status')!='UNRESOLVED_EXTERNAL_AUTHORITY' or qp['CORE-01'].get('resolved_lifecycle_fields')!={} or qp['CORE-01'].get('unresolved_lifecycle_fields')!=async_fields): die('CORE async provider unresolved state drift')
aa=qp['ASSET-01'].get('provider_adapter_authority') or {}
if aa!={'contract_ref':'ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT@V1.3#provider_adapter','profile_owner':'admin:AIAPI-01#provider_model_profiles','department_provider_registry':'FORBIDDEN','router_owner':'ACPOS AI Execution / current AI API Router','raw_source_git_blob':'9668e2307c722ea4cf64f93f07c92da1b3abcc28'}: die('ASSET exact provider adapter authority drift')
if qp['ASSET-01'].get('resolved_lifecycle_fields')!={} or qp['ASSET-01'].get('unresolved_lifecycle_fields')!=async_fields: die('ASSET async lifecycle unresolved state drift')
if (Q.get('policy') or {}).get('duplicate_provider_adapter_creation')!='FORBIDDEN' or (Q.get('policy') or {}).get('ai_default_lifecycle_values')!='FORBIDDEN': die('async provider no-dup/no-inference policy drift')

expected_actions=['ASSET-01-ACT-CORRECTION-GENERATE','ASSET-01-ACT-CORRECTION-APPROVE','ASSET-01-ACT-RESTORE-AS-NEW','ASSET-01-ACT-VERSION-LOCK']
if M.get('artifact_type')!='SHARED_OWNER_PORT_MAP' or M.get('operation_uid')!='SHARED_OWNER_PORT_RESOLVE': die('shared owner map identity drift')
ag=M.get('authority_gap') or {}
if ag.get('gap_uid')!='GAP-006' or ag.get('authority_ref')!='ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or ag.get('consumer_count')!=4 or ag.get('resolution_status')!='EXPLICITLY_UNRESOLVED_PRESERVED': die('shared owner gap preservation drift')
cons=M.get('consumers') or []
if [x.get('action_uid') for x in cons]!=expected_actions: die('shared owner consumer set/order drift')
for x in cons:
 if x.get('shared_owner_authority_ref')!='ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or x.get('resolved_owner_uid') is not None or x.get('resolved_operation_uid') is not None or x.get('resolved_port_uid') is not None or x.get('status')!='UNRESOLVED_AUTHORITY_GAP': die('shared owner consumer illegally resolved')
if (M.get('policy') or {}).get('ai_guess')!='FORBIDDEN' or (M.get('policy') or {}).get('duplicate_page_local_runtime_api_repository_or_provider')!='FORBIDDEN': die('shared owner no-guess/no-duplicate policy drift')

# Existing transition architecture gaps remain explicitly unresolved; successor output materialization is not closure.
if (S.get('summary') or {}).get('unresolved_required_field_total')!=50 or (S.get('summary') or {}).get('resolved_required_field_total')!=0: die('state transition gap state drift')
for obj,name in [(D,'dependency'),(C,'core construction'),(A,'asset construction'),(Q,'async provider'),(M,'shared owner')]:
 if obj.get('website_construction_allowed',False) is not False and name not in ('core construction','asset construction'): die(f'{name} website block missing')
 if obj.get('deployment_allowed',False) is not False and name not in ('core construction','asset construction'): die(f'{name} deployment block missing')

print('PASS: canonical Stage-02 DEPENDENCY_MAP exists and reference-binds the immutable 171-gap detail materialization')
print('PASS: both PAGE_CONSTRUCTION_SPEC_PACKAGE outputs exist as Page-owned OPEN/BLOCKING successors with exact predecessor refs')
print('PASS: ASYNC_PROVIDER_CONTRACT preserves provider authority without inventing lifecycle fields')
print('PASS: SHARED_OWNER_PORT_MAP preserves all 4 GAP-006 consumers unresolved; no duplicate owner/runtime/port was invented')
print('PASS: Stage-02 required successor outputs are materialized without claiming functional completion; website/deployment remain blocked')
