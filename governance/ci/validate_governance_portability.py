#!/usr/bin/env python3
from pathlib import Path
import json
import re
import yaml
from canonical_rule_registry import load_registry, scan_policy_text

ROOT=Path(__file__).resolve().parents[2]
CUR=ROOT/'governance/specifications/current'
MOTHER=ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec'
CURRENT_ENTRY=ROOT/'GOVERNANCE_CURRENT.yaml'
failures=[]
try:
    canonical=load_registry()
except Exception as exc:
    canonical={}
    failures.append('canonical_rule_registry_invalid:'+str(exc))

for p in sorted(MOTHER.glob('*.md')):
    t=p.read_text(encoding='utf-8')
    for finding in scan_policy_text(t):
        failures.append('mother_policy_semantic_leak:'+p.name+':'+finding['semantic_type']+':'+finding['match'])

# Secondary literal contamination defense for reusable Mother prose. These values
# belong to execution-profile, product-adapter, run-state, workflow or evidence layers.
mother_literal_patterns={
    'profile_retry_token': re.compile(r'\bR\d{1,3}\b'),
    'fixed_stage_token': re.compile(r'\bSTAGE-\d{1,2}\b', re.IGNORECASE),
    'concrete_product_uid': re.compile(r'\b(?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI)-\d+\b'),
    'workflow_path': re.compile(r'\.github/workflows/'),
    'governance_script_path': re.compile(r'\bgovernance/ci/[A-Za-z0-9_.\-/]+'),
    'long_run_id': re.compile(r'\b\d{8,12}\b'),
}
for p in sorted(MOTHER.glob('*.md')):
    body=p.read_text(encoding='utf-8')
    for kind,pat in mother_literal_patterns.items():
        for m in pat.finditer(body):
            failures.append('mother_policy_literal_contamination:'+p.name+':'+kind+':'+m.group(0))

manifest=yaml.safe_load((CUR/'SPECIFICATION_MANIFEST.yaml').read_text()) or {}
files=[]
for rec in manifest.get('components') or []:
    fn=rec.get('file'); p=CUR/fn; files.append(fn)
    if not p.is_file(): failures.append('current_component_missing:'+str(fn)); continue
    d=yaml.safe_load(p.read_text()) or {}
    if d.get('formal_current_authority') is not True: failures.append('current_component_not_formal:'+str(fn))
    if d.get('layer_classification')!='POLICY': failures.append('current_component_not_policy:'+str(fn))
    if 'TEST_SPECIFICATION' in str(d.get('normative_status','')): failures.append('test_component_in_current:'+str(fn))
    for finding in scan_policy_text(p.read_text(encoding='utf-8')):
        failures.append('current_policy_semantic_leak:'+str(fn)+':'+finding['semantic_type']+':'+finding['match'])

old={'STAGE_EXECUTION_OPTIMIZATION.yaml','STAGE_TEST_REMEDIATION_CLOSURE_PROTOCOL.yaml','TEST_FEEDBACK_TEMPORARY_ARTIFACT_LIFECYCLE.yaml'}
if old & set(files): failures.append('superseded_stage_test_component_still_manifested')
if any((CUR/x).exists() for x in old): failures.append('superseded_stage_test_component_residual')

entry=yaml.safe_load(CURRENT_ENTRY.read_text(encoding='utf-8')) or {}
selected=entry.get('selected_execution_profile') or {}
profile_ref=selected.get('registry')
if not profile_ref:
    failures.append('selected_profile_registry_missing')
    prof={}
else:
    profile_path=ROOT/str(profile_ref)
    if not profile_path.is_file():
        failures.append('selected_profile_registry_target_missing:'+str(profile_ref))
        prof={}
    else:
        prof=yaml.safe_load(profile_path.read_text(encoding='utf-8')) or {}

if selected.get('layer_classification')!='EXECUTION_PROFILE' or selected.get('global_normative_authority') is not False:
    failures.append('current_selected_profile_classification_invalid')
if prof.get('artifact_type')!='EXECUTION_PROFILE_REGISTRY':
    failures.append('profile_registry_type_invalid')
if prof.get('layer_classification')!='EXECUTION_PROFILE' or prof.get('global_normative_authority') is not False:
    failures.append('profile_layer_classification_invalid')
if prof.get('profile_uid') != selected.get('profile_uid'):
    failures.append('selected_profile_uid_drift')
profile_steps=prof.get('stages') or []
if int(prof.get('profile_local_denominator') or -1)!=len(profile_steps):
    failures.append('profile_local_denominator_drift')
if int(selected.get('profile_local_denominator') or -1)!=len(profile_steps):
    failures.append('current_selected_profile_denominator_drift')

synthetic=[
    {'uid':'SYNTH-A','steps':['discover','design','ship']},
    {'uid':'SYNTH-B','steps':['intake','contract','visual','build','verify','release','operate']},
]
if len({len(x['steps']) for x in synthetic}) < 2:
    failures.append('synthetic_profile_denominators_not_materially_different')
policy_blob='\n'.join((CUR/f).read_text(encoding='utf-8') for f in files)
for synthetic_profile in synthetic:
    if synthetic_profile['uid'] in policy_blob:
        failures.append('synthetic_profile_leaked_into_policy:'+synthetic_profile['uid'])

# Machine-layer portability: reusable/global validators and workflows must not
# hard-bind any concrete profile step identity or profile-specific step schema.
global_surfaces=[
    ROOT/'governance/ci/validate_governance_portability.py',
    ROOT/'governance/ci/validate_active_consumer_reference_integrity.py',
    ROOT/'governance/ci/validate_authoring_reference_governance_coverage.py',
    ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py',
    ROOT/'governance/ci/validate_selected_execution_profile_integrity.py',
    ROOT/'.github/workflows/governance-selected-profile-integrity.yml',
    ROOT/'.github/workflows/governance-full-line-system-gate.yml',
]
fixed_step=re.compile(r'\bSTAGE-\d{2}\b', re.IGNORECASE)
fixed_schema=re.compile(r'\bstage0?[1-9]\b', re.IGNORECASE)
for surface in global_surfaces:
    if not surface.is_file():
        failures.append('global_portability_surface_missing:'+surface.relative_to(ROOT).as_posix())
        continue
    body=surface.read_text(encoding='utf-8')
    if fixed_step.search(body):
        failures.append('global_machine_fixed_profile_step_identity:'+surface.relative_to(ROOT).as_posix())
    if fixed_schema.search(body):
        failures.append('global_machine_profile_specific_step_schema:'+surface.relative_to(ROOT).as_posix())

# Reusable product-scope consumers must remain scope-parametric.
scope_neutral_surfaces=[
    ROOT/'governance/ci/run_current_stage2_actual_test.py',
    ROOT/'governance/ci/validate_current_stage2_materialized_closure.py',
    ROOT/'governance/ci/validate_stage02_state_integrity.py',
    ROOT/'governance/ci/validate_stage02_successor_integrity.py',
]
literal_product_identity=re.compile(r"['\"](?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI)-\d+['\"]")
for surface in scope_neutral_surfaces:
    if not surface.is_file():
        failures.append('scope_neutral_surface_missing:'+surface.relative_to(ROOT).as_posix())
        continue
    body=surface.read_text(encoding='utf-8')
    if literal_product_identity.search(body):
        failures.append('reusable_consumer_literal_product_scope:'+surface.relative_to(ROOT).as_posix())

# Mother context/task-layer machine binding checks. These extend the existing portability owner.
exec_control=yaml.safe_load((CUR/'EXECUTION_CYCLE_CONTROL.yaml').read_text(encoding='utf-8')) or {}
closure=yaml.safe_load((CUR/'VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml').read_text(encoding='utf-8')) or {}
boot=exec_control.get('session_bootstrap_resume_gate') or {}
task=exec_control.get('task_layer_classification') or {}
wu=exec_control.get('work_unit_resolution_gate') or {}
credit=closure.get('governance_maintenance_credit_isolation') or {}
terminal=closure.get('terminal_result_semantics') or {}
if boot.get('required_before_any_current_state_judgment_planning_write_test_commit_workflow_deployment_or_closure_claim') is not True: failures.append('session_bootstrap_resume_gate_not_required')
if boot.get('stage_profile_or_run_identity_may_select_current_governance') is not False: failures.append('stage_profile_run_may_select_current_governance')
expected_layers={'GOVERNANCE_MAINTENANCE','PRODUCT_STAGE_EXECUTION','TEST_OR_VALIDATION_MAINTENANCE','EVIDENCE_STATE_MAINTENANCE','DEPLOYMENT_OR_PRODUCTION'}
if set(task.get('allowed_primary_layers') or []) != expected_layers: failures.append('primary_task_layer_denominator_drift')
if task.get('stage_profile_run_or_open_blocker_may_silently_redirect_primary_task') is not False: failures.append('primary_task_silent_redirect_not_forbidden')
if wu.get('required_when_no_legal_active_primary_work_unit') is not True or wu.get('ai_may_invent_successor_work_unit') is not False: failures.append('work_unit_resolution_gate_not_fail_closed')
if credit.get('product_stage_gap_reduction_credit') != 0 or credit.get('product_completion_credit') != 0: failures.append('governance_maintenance_product_credit_not_zero')
if terminal.get('outer_terminal_conclusion_is_closure_authority') is not True or terminal.get('inner_step_pass_is_terminal_run_pass') is not False: failures.append('outer_terminal_closure_semantics_invalid')

out={
    'status':'PASS' if not failures else 'FAIL',
    'canonical_registry_uid':canonical.get('registry_uid'),
    'canonical_registry_digest':canonical.get('registry_digest'),
    'mother_files':len(list(MOTHER.glob('*.md'))),
    'current_components':len(files),
    'selected_profile_uid':selected.get('profile_uid'),
    'selected_profile_steps':len(profile_steps),
    'synthetic_profile_denominators':[len(x['steps']) for x in synthetic],
    'global_machine_surfaces_checked':len(global_surfaces),
    'failures':failures,
}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if not failures else 1)
