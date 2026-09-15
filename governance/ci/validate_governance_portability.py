#!/usr/bin/env python3
from pathlib import Path
import json
import re
import yaml
from canonical_rule_registry import load_registry, scan_policy_text

ROOT=Path(__file__).resolve().parents[2]
CUR=ROOT/'governance/specifications/current'
MOTHER=ROOT/'.github/governance-source/active/source/12_DOCS/mother-spec'
PROFILE=ROOT/'.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
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

prof=yaml.safe_load(PROFILE.read_text()) or {}
if prof.get('layer_classification')!='EXECUTION_PROFILE' or prof.get('global_normative_authority') is not False: failures.append('profile_layer_classification_invalid')
if prof.get('profile_local_denominator')!=len(prof.get('stages') or []): failures.append('profile_local_denominator_drift')
if prof.get('profile_local_denominator')!=11: failures.append('acpos_profile_11_step_contract_drift')

synthetic=[{'uid':'SYNTH-A','steps':['discover','design','ship']},{'uid':'SYNTH-B','steps':['intake','contract','visual','build','verify','release','operate']}]
policy_blob='\n'.join((CUR/f).read_text(encoding='utf-8') for f in files)
for s in synthetic:
    for step in s['steps']:
        if step.upper() in policy_blob and ('SYNTH-' in policy_blob): failures.append('synthetic_profile_leaked_into_policy')

out={'status':'PASS' if not failures else 'FAIL','canonical_registry_uid':canonical.get('registry_uid'),'canonical_registry_digest':canonical.get('registry_digest'),'mother_files':len(list(MOTHER.glob('*.md'))),'current_components':len(files),'selected_profile_steps':len(prof.get('stages') or []),'synthetic_profile_denominators':[len(x['steps']) for x in synthetic],'failures':failures}
print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if not failures else 1)
