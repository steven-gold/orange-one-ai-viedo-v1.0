#!/usr/bin/env python3
from pathlib import Path
import subprocess, yaml

root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
classification=base/'PAYLOAD_OPERATION_AUTHORITY_CLASSIFICATION_R1.yaml'
audit=base/'PAYLOAD_INPUT_AUTHORITY_AUDIT.yaml'
manifest=base/'PAYLOAD_AUTHORITY_AUDIT_SOURCE/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'
candidate=base/'PAYLOAD_AUTHORITY_AUDIT_SOURCE/business_payload_registry.yaml'
gap=base/'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
r2=root/'governance/ci/validate_current_stage2_payload_action_operation_inventory_r2.py'

LOCKED={
 classification:'bc8564083e676580a4d89f2cce2c0c65d21e2516',
 audit:'61072f986978177aa7a535b9ff3fb495eb71d1ca',
 manifest:'465329b6fb19b8e44c3083a9f280015ee95cc55c',
 candidate:'3b1130c098380ee6b64f56ee83c0ef7006a5af72',
 gap:'29855a6aa9940b6ea64ca75d355c60acda3d2b94',
 r2:'b04d680c823bd0bebbfdd1da7bdd059f103cbe8d',
}

def die(m): raise SystemExit(m)
def load(p):
 d=yaml.safe_load(p.read_text(encoding='utf-8'))
 if not isinstance(d,dict): die('mapping required:'+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+str(p))
 return r.stdout.strip()
def flatten(x):
 out=[]
 if isinstance(x,str): out.append(x)
 elif isinstance(x,list):
  for v in x: out.extend(flatten(v))
 elif isinstance(x,dict):
  for v in x.values(): out.extend(flatten(v))
 return out

for p,b in LOCKED.items():
 if gitobj(p)!=b: die('payload classification evidence drift:'+str(p))

C=load(classification); A=load(audit); M=load(manifest); G=load(gap)
if C.get('artifact_type')!='PAYLOAD_OPERATION_AUTHORITY_CLASSIFICATION' or C.get('status')!='CLASSIFIED_BLOCKED_BY_CURRENT_PAYLOAD_SCHEMA_AUTHORITY': die('classification identity/status drift')

basis=C.get('current_functional_gap_basis') or {}
if basis.get('gap_ledger_git_blob')!=LOCKED[gap] or basis.get('total_functional_gaps')!=167 or basis.get('architecture_gap_total')!=133 or basis.get('payload_input_contract_missing_total')!=34 or basis.get('CORE-01')!=16 or basis.get('ASSET-01')!=18: die('classification functional basis drift')

rec=C.get('operation_inventory_receipt') or {}; s=rec.get('verified_summary') or {}
if rec.get('validator_git_blob')!=LOCKED[r2] or rec.get('workflow_run_id')!=34779207972 or rec.get('workflow_run_number')!=183 or rec.get('head_sha')!='f9a534285390c491d1d713c7c066460ab042e7a7' or rec.get('job_id')!=103782982982 or rec.get('job_conclusion')!='success' or rec.get('workflow_job_total')!=31 or rec.get('workflow_conclusion')!='success' or rec.get('artifact_id')!=10324104892 or rec.get('artifact_digest')!='sha256:420b623b1aca9346f5d78750e6911e0f912c941a56ffaa6dce286e9f50f9cd19': die('Gate31 receipt drift')
if s.get('total_actions')!=34 or s.get('CORE-01')!=16 or s.get('ASSET-01')!=18 or s.get('exact_port_operation_mapping')!=34 or s.get('composite_mapping_count')!=1 or s.get('composite_mapping_actions')!=['ASSET-01-ACT-EVALUATE'] or s.get('inline_schema_candidate_count')!=0 or s.get('inventory_changes_current_gap_count') is not False or s.get('current_payload_gap_count')!=34: die('Gate31 verified summary drift')

adm=C.get('payload_authority_admissibility_basis') or {}
if adm.get('audit_git_blob')!=LOCKED[audit] or adm.get('current_authority_manifest_git_blob')!=LOCKED[manifest] or adm.get('candidate_payload_registry_git_blob')!=LOCKED[candidate] or adm.get('candidate_listed_in_current_authority_set') is not False or adm.get('candidate_current_construction_admissibility')!='REJECTED_UNLISTED_CURRENT_AUTHORITY': die('admissibility basis drift')
mi=M.get('authority') or {}; lp=M.get('load_policy') or {}
if mi.get('status')!='FINAL_LOCKED' or mi.get('current_only') is not True or mi.get('load_rule')!='Load only exact repository paths in current_authority_set.': die('Current Manifest identity/load-rule drift')
if lp.get('only_listed_files_are_current_authority') is not True or lp.get('unlisted_authority_or_spec_file')!='DO_NOT_LOAD_FOR_CURRENT_CONSTRUCTION': die('Current Manifest unlisted policy drift')
if '03_api/business_payload_registry.yaml' in set(flatten(M.get('current_authority_set') or {})): die('candidate unexpectedly became Current Authority')

ac=A.get('audit_conclusion') or {}
if A.get('status')!='AUDITED_NO_GAP_REMOVAL_AUTHORIZED' or ac.get('candidate_is_current_authority') is not False or ac.get('validated_gap_removal_count')!=0 or ac.get('current_input_gap_count_remains')!=34: die('predecessor payload audit drift')

gs=G.get('summary') or {}; cls=gs.get('classes') or {}; cats=gs.get('categories') or {}
if gs.get('total')!=167 or cls.get('ARCHITECTURE_GAP')!=133 or cls.get('INPUT_SOURCE_GAP')!=34 or cats.get('PAYLOAD_INPUT_CONTRACT_MISSING')!=34: die('R4 gap truth drift')

c=C.get('classification') or {}
if c.get('exact_operation_mapping_complete') is not True or c.get('exact_operation_mapping_count')!=34 or c.get('admissible_current_payload_schema_binding_count')!=0 or c.get('payload_gap_removal_authorized')!=0 or c.get('current_payload_gap_count_after_classification')!=34 or c.get('current_functional_gap_total_after_classification')!=167 or c.get('operation_mapping_is_payload_schema') is not False or c.get('unlisted_candidate_may_be_promoted_by_inference') is not False or c.get('cross_source_union_used') is not False or c.get('authority_set_mutated') is not False or c.get('raw_source_mutated') is not False: die('classification outcome drift')

br=C.get('blocker_reason') or {}
if br.get('code')!='CURRENT_PAYLOAD_SCHEMA_AUTHORITY_MISSING' or br.get('ai_default_or_schema_invention')!='FORBIDDEN': die('blocker reason drift')
eff=C.get('stage2_effect') or {}
if eff.get('functional_completion') is not False or eff.get('exit_gate_result')!='BLOCKED' or eff.get('website_construction_allowed') is not False or eff.get('deployment_allowed') is not False: die('classification falsely enables Stage2/site/deploy')

print('PASS: Gate31 proves exact action-to-port-to-operation mapping for all 34 payload-gap consumers')
print('PASS: mapping completeness is not payload-schema completeness; admissible Current payload schema bindings remain 0/34')
print('PASS: unlisted business_payload_registry remains inadmissible under Current Authority Manifest and authorizes 0 removals')
print('PASS: Current Stage-02 truth remains 167 functional gaps = 133 architecture + 34 input-source; website/deploy remain blocked')
