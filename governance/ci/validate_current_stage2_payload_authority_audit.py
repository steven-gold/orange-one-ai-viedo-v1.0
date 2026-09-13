#!/usr/bin/env python3
from pathlib import Path
import subprocess,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; base=run/'04_PAGE_FUNCTIONAL_CONTRACT'
audit=base/'PAYLOAD_INPUT_AUTHORITY_AUDIT.yaml'
manifest=base/'PAYLOAD_AUTHORITY_AUDIT_SOURCE/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'
candidate=base/'PAYLOAD_AUTHORITY_AUDIT_SOURCE/business_payload_registry.yaml'
r4=base/'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
core=run/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'
asset=run/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
transaction=base/'CURRENT_LEDGER_SYNCHRONIZATION_R3.yaml'

def die(m): raise SystemExit(m)
def load(p):
 try:d=yaml.safe_load(p.read_text(encoding='utf-8'))
 except Exception as e:die('parse failure '+str(p)+': '+str(e))
 if not isinstance(d,dict):die('mapping required:'+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode:die('git object missing:'+str(p))
 return r.stdout.strip()
def flatten(x):
 out=[]
 if isinstance(x,str):out.append(x)
 elif isinstance(x,list):
  for v in x:out.extend(flatten(v))
 elif isinstance(x,dict):
  for v in x.values():out.extend(flatten(v))
 return out

locked={
 audit:'61072f986978177aa7a535b9ff3fb495eb71d1ca',
 manifest:'465329b6fb19b8e44c3083a9f280015ee95cc55c',
 candidate:'3b1130c098380ee6b64f56ee83c0ef7006a5af72',
 r4:'29855a6aa9940b6ea64ca75d355c60acda3d2b94',
 core:'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
 asset:'9668e2307c722ea4cf64f93f07c92da1b3abcc28',
 transaction:'9a6f11d383a625e3fe87a1b654644206480b321c'}
for p,b in locked.items():
 if gitobj(p)!=b:die('payload audit evidence/predecessor drift:'+str(p))
A=load(audit); M=load(manifest); C=load(candidate); G=load(r4); AS=load(asset)
if A.get('artifact_type')!='PAYLOAD_INPUT_AUTHORITY_AUDIT' or A.get('artifact_uid')!='FRESH-RUN-003-STAGE2-PAYLOAD-INPUT-AUTHORITY-AUDIT-V212-R1' or A.get('status')!='AUDITED_NO_GAP_REMOVAL_AUTHORIZED':die('audit identity/status drift')
sp=A.get('source_pin') or {}
if sp.get('commit')!='6c8a0c3334ccd17942ba14079976fb295859a43c':die('source pin drift')
ma=A.get('current_authority_manifest') or {}; ca=A.get('candidate_payload_registry') or {}
if ma.get('source_path')!='authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml' or ma.get('source_git_blob')!='465329b6fb19b8e44c3083a9f280015ee95cc55c' or ma.get('materialized_git_blob')!='465329b6fb19b8e44c3083a9f280015ee95cc55c':die('manifest evidence drift')
if ca.get('source_path')!='03_api/business_payload_registry.yaml' or ca.get('source_git_blob')!='3b1130c098380ee6b64f56ee83c0ef7006a5af72' or ca.get('materialized_git_blob')!='3b1130c098380ee6b64f56ee83c0ef7006a5af72':die('candidate evidence drift')
mi=M.get('authority') or {}; lp=M.get('load_policy') or {}
if mi.get('id')!='ACPOS_CURRENT_AUTHORITY_MANIFEST' or mi.get('status')!='FINAL_LOCKED' or mi.get('current_only') is not True:die('Current Authority Manifest identity drift')
if mi.get('load_rule')!='Load only exact repository paths in current_authority_set.':die('manifest exact load rule drift')
if lp.get('only_listed_files_are_current_authority') is not True or lp.get('unlisted_authority_or_spec_file')!='DO_NOT_LOAD_FOR_CURRENT_CONSTRUCTION':die('manifest unlisted policy drift')
current_paths=set(flatten(M.get('current_authority_set') or {}))
if '03_api/business_payload_registry.yaml' in current_paths:die('candidate unexpectedly became Current Authority')
for required in ('authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml','authority/pages/workspace/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'):
 if required not in current_paths:die('required Current Page Authority missing from manifest:'+required)
reg=C.get('business_payload_registry') or {}; meta=reg.get('contract_meta') or {}
if meta.get('contract_id')!='ACPOS-CURRENT-BUSINESS-PAYLOAD-REGISTRY-1.1.0' or meta.get('status')!='FINAL_LOCKED':die('candidate registry identity/status drift')
dep=C.get('department_runtime_payload_registry') or {}; ops=dep.get('operations') or []
score=[x for x in ops if isinstance(x,dict) and x.get('operation_id')=='submitScorecard']
if len(score)!=1:die('candidate submitScorecard entry cardinality drift')
score=score[0]
if not score.get('required_body'):die('candidate submitScorecard required_body unexpectedly absent')
if score.get('method') is not None or score.get('path') is not None:die('candidate submitScorecard unexpectedly owns exact ingress')
ports=((AS.get('registries') or {}).get('integration_ports') or [])
cp=[x for x in ports if isinstance(x,dict) and x.get('port_uid')=='ASSET-01-PORT-SCORECARD']
if len(cp)!=1:die('Current ASSET scorecard port cardinality drift')
cp=cp[0]
if cp.get('registered_operation')!='submitScorecard' or cp.get('method_effective_path')!='POST /v1/scorecards':die('Current ASSET submitScorecard ingress drift')
expected_core=['CORE-01-ACT-PROJECT-CREATE','CORE-01-ACT-TOPIC-CREATE','CORE-01-ACT-THREAD-CREATE','CORE-01-ACT-SEND','CORE-01-ACT-CANDIDATE-CREATE','CORE-01-ACT-CANDIDATE-ACCEPT','CORE-01-ACT-PROJECT-VALIDATE','CORE-01-ACT-PROJECT-CONFIRM','CORE-01-ACT-STORY-CANDIDATE','CORE-01-ACT-DNA-LOCK-REQUEST','CORE-01-ACT-CORE-REVIEW-SUBMIT','CORE-01-ACT-MOTHER-LOCK-REQUEST','CORE-01-ACT-BLUEPRINT-CREATE','CORE-01-ACT-BLUEPRINT-VALIDATE','CORE-01-ACT-BLUEPRINT-APPROVE','CORE-01-ACT-CHILD-LOCK-REQUEST']
expected_asset=['ASSET-01-ACT-FLOW-START','ASSET-01-ACT-EVALUATE','ASSET-01-ACT-CANDIDATE-CONFIRM','ASSET-01-ACT-FINDING-CREATE','ASSET-01-ACT-TASK-RETRY','ASSET-01-ACT-HANDOFF','ASSET-01-ACT-LAYER-DOC-CREATE','ASSET-01-ACT-LAYER-DOC-UPDATE','ASSET-01-ACT-LAYER-ADD','ASSET-01-ACT-LAYER-DELETE','ASSET-01-ACT-LAYER-DUPLICATE','ASSET-01-ACT-LAYER-REORDER','ASSET-01-ACT-LAYER-PROPERTIES','ASSET-01-ACT-LAYER-MASK','ASSET-01-ACT-PATCH-CREATE','ASSET-01-ACT-PATCH-PREVIEW','ASSET-01-ACT-PATCH-ACCEPT','ASSET-01-ACT-PATCH-REJECT']
s=G.get('summary') or {}; classes=s.get('classes') or {}; groups=G.get('category_groups') or {}; pg=groups.get('PAYLOAD_INPUT_CONTRACT_MISSING') or {}
if s.get('total')!=167 or classes.get('INPUT_SOURCE_GAP')!=34:die('R4 current gap totals drift')
for page,expected in [('CORE-01',expected_core),('ASSET-01',expected_asset)]:
 p=pg.get(page) or []
 if isinstance(p,dict): actions=p.get('action_uids') or []; count=p.get('expanded_gap_count')
 else: actions=p; count=len(p)
 if actions!=expected or count!=len(expected):die(page+' payload-gap consumer universe drift')
if len(expected_core)+len(expected_asset)!=34:die('internal expected payload universe drift')
basis=A.get('current_functional_gap_basis') or {}
if basis.get('gap_ledger_git_blob')!='29855a6aa9940b6ea64ca75d355c60acda3d2b94' or basis.get('payload_input_contract_missing_total')!=34 or basis.get('CORE-01')!=16 or basis.get('ASSET-01')!=18 or basis.get('gap_removal_authorized_by_this_audit')!=0 or basis.get('gap_total_after_this_audit')!=167 or basis.get('payload_input_gap_total_after_this_audit')!=34:die('audit current gap basis drift')
chk=((A.get('current_page_authority_checks') or {}).get('ASSET-01') or {}).get('submitScorecard') or {}
if chk.get('current_port_uid')!='ASSET-01-PORT-SCORECARD' or chk.get('current_operation')!='submitScorecard' or chk.get('current_ingress')!='POST /v1/scorecards' or chk.get('candidate_required_body_present') is not True or chk.get('candidate_method_present') is not False or chk.get('candidate_path_present') is not False or chk.get('exact_ingress_contract_from_candidate') is not False or chk.get('disposition')!='NON_EXACT_INCOMPLETE_CANDIDATE':die('audit submitScorecard negative evidence drift')
con=A.get('audit_conclusion') or {}
if con.get('candidate_is_current_authority') is not False or con.get('candidate_may_be_consumed_by_current_functional_compiler') is not False or con.get('candidate_may_resolve_any_of_34_by_itself') is not False or con.get('validated_gap_removal_count')!=0 or con.get('current_input_gap_count_remains')!=34 or con.get('ai_inference_or_cross_source_union_used') is not False or con.get('raw_source_mutated') is not False or con.get('current_authority_set_mutated') is not False:die('audit conclusion drift')
eff=A.get('stage2_effect') or {}
if eff.get('functional_completion') is not False or eff.get('exit_gate_result')!='BLOCKED' or eff.get('website_construction_allowed') is not False or eff.get('deployment_allowed') is not False:die('payload audit falsely enables Stage2/site/deploy')
print('PASS: unlisted FINAL_LOCKED business payload registry is not Current Authority under the exact Current Authority Manifest load rule')
print('PASS: materialization does not upgrade Authority rank; this candidate authorizes 0 of 34 payload-gap removals')
print('PASS: Current R4 payload-gap universe remains exact 34 = CORE 16 + ASSET 18')
print('PASS: submitScorecard negative exact-match check confirms candidate body entry does not independently own the Current POST /v1/scorecards ingress contract')
print('PASS: Stage-02 remains blocked; no AI inference, Raw Source mutation, website construction, or deployment is authorized')
