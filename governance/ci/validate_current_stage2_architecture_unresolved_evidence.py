#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys, yaml

root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
evidence_path=base/'ARCHITECTURE_GAP_UNRESOLVED_EVIDENCE_R1.yaml'
r4_path=base/'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
R4_BLOB='29855a6aa9940b6ea64ca75d355c60acda3d2b94'
RECEIPT_SHA='26ee0f8940c01a998e12991855afa0c856eb993b'
EXPECTED={
 'STATE_TRANSITION_LEDGER_FIELD_MISSING':50,
 'FAILURE_STATE_ERROR_BINDING_MISSING':44,
 'POST_ACTION_VALIDATION_NODE_MISSING':18,
 'AUDIT_EVENT_NODE_MISSING':13,
 'SUCCESS_NEXT_STATE_BINDING_MISSING':7,
 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,
}
VALIDATORS=[
 'governance/ci/validate_current_stage2_state_transition_authority_audit.py',
 'governance/ci/validate_current_stage2_failure_state_error_binding_inventory.py',
 'governance/ci/validate_current_stage2_failure_state_error_binding_authority_audit.py',
 'governance/ci/validate_current_stage2_post_action_validation_inventory.py',
 'governance/ci/validate_current_stage2_post_action_validation_authority_audit.py',
 'governance/ci/validate_current_stage2_audit_event_inventory.py',
 'governance/ci/validate_current_stage2_audit_event_authority_audit.py',
 'governance/ci/validate_current_stage2_success_next_state_inventory.py',
 'governance/ci/validate_current_stage2_success_next_state_authority_audit.py',
 'governance/ci/validate_current_stage2_action_without_control_or_trigger_inventory.py',
 'governance/ci/validate_current_stage2_action_control_trigger_authority_audit.py',
]
OUTPUTS={
 'stage2_failure_state_error_binding_inventory.json':44,
 'stage2_failure_state_error_binding_authority_audit.json':44,
 'stage2_post_action_validation_inventory.json':18,
 'stage2_post_action_validation_authority_audit.json':18,
 'stage2_audit_event_inventory.json':13,
 'stage2_audit_event_authority_audit.json':13,
 'stage2_success_next_state_inventory.json':7,
 'stage2_success_next_state_authority_audit.json':7,
 'stage2_action_without_control_or_trigger_inventory.json':1,
 'stage2_action_control_trigger_authority_audit.json':1,
}

def die(m): raise SystemExit(m)
def load_yaml(p):
 d=yaml.safe_load(p.read_text(encoding='utf-8'))
 if not isinstance(d,dict): die('mapping required: '+str(p))
 return d
def gitobj(p):
 r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
 if r.returncode: die('git object missing: '+str(p))
 return r.stdout.strip()
def assert_fail_closed_json(obj,name,expected):
 rows=obj.get('rows') or []
 for row in rows:
  if not isinstance(row,dict): continue
  for k in ('authorized_for_gap_removal','authorized_for_removal','detector_resolvable'):
   if row.get(k) is True: die(f'{name}: unexpected resolvable/authorized row via {k}')
 s=obj.get('summary') or {}
 for k,v in s.items():
  lk=str(k).lower()
  if 'authorized' in lk and isinstance(v,int) and v!=0:
   die(f'{name}: nonzero authorized count {k}={v}')
 if s.get('authorized_action_uids') not in (None,[]):
  die(f'{name}: authorized_action_uids must be empty')
 unresolved=None
 for k in ('unresolved_gap_count_after_audit','unresolved_gap_count_after_inventory'):
  if k in s: unresolved=s[k]; break
 if unresolved is not None and unresolved!=expected:
  die(f'{name}: unresolved count {unresolved} != {expected}')
 if s.get('current_architecture_gap_total') not in (None,133):
  die(f'{name}: architecture total drift')
 if s.get('current_functional_gap_total') not in (None,167):
  die(f'{name}: functional total drift')

if gitobj(r4_path)!=R4_BLOB: die('R4 blob drift')
E=load_yaml(evidence_path); R4=load_yaml(r4_path)
if E.get('artifact_uid')!='FRESH-RUN-003-STAGE2-ARCHITECTURE-GAP-UNRESOLVED-EVIDENCE-V212-R1': die('artifact uid drift')
if E.get('artifact_type')!='ARCHITECTURE_GAP_UNRESOLVED_EVIDENCE': die('artifact type drift')
if E.get('status')!='AUDIT_COMPLETE_GAPS_REMAIN_OPEN': die('status drift')
if E.get('governance_overlay')!='v2.1.12' or E.get('stage_uid')!='STAGE-02': die('governance/stage drift')
if E.get('closure_policy')!='MERGE_APPEND_OR_EXPLICIT_SUPERSEDE': die('closure policy drift')
pred=E.get('predecessor') or {}
if pred.get('functional_gap_ledger_git_blob')!=R4_BLOB: die('predecessor R4 blob mismatch')
counts=E.get('current_counts_preserved') or {}
expected_counts={
 'functional_gap_total':167,
 'architecture_gap_total':133,
 'input_source_gap_total':34,
 'functional_authority_gap_total':0,
 'architecture_authorized_removals':0,
 'architecture_unresolved_after_full_audit':133,
}
for k,v in expected_counts.items():
 if counts.get(k)!=v: die(f'consolidation count drift: {k}')
summary=R4.get('summary') or {}
if summary.get('total')!=167: die('R4 total drift')
classes=summary.get('classes') or {}
if classes.get('ARCHITECTURE_GAP')!=133 or classes.get('INPUT_SOURCE_GAP')!=34:
 die('R4 class totals drift')
if classes.get('AUTHORITY_GAP',0)!=0: die('R4 Authority gap must remain zero')
cats=summary.get('categories') or {}
for cat,n in EXPECTED.items():
 if cats.get(cat)!=n: die(f'R4 category drift: {cat}')
if sum(EXPECTED.values())!=133: die('internal architecture sum error')
coverage=E.get('architecture_category_coverage') or []
if len(coverage)!=6: die('architecture coverage must contain exactly six categories')
seen={}
for row in coverage:
 if not isinstance(row,dict): die('coverage row must be mapping')
 cat=row.get('category')
 if cat in seen: die('duplicate architecture category: '+str(cat))
 seen[cat]=row
for cat,n in EXPECTED.items():
 row=seen.get(cat)
 if not row: die('missing architecture category: '+cat)
 if row.get('expected_gap_count')!=n or row.get('authorized_removals')!=0 or row.get('unresolved_gap_count')!=n:
  die('coverage count/removal drift: '+cat)
 for k in ('page_or_registry_validator','bounded_authority_validator','dedicated_gate'):
  if not row.get(k): die(f'{cat}: missing {k}')
receipt=E.get('simultaneous_terminal_receipt') or {}
if receipt.get('run_number')!=207 or receipt.get('run_id')!=34783179077 or receipt.get('exact_head_sha')!=RECEIPT_SHA:
 die('terminal receipt identity drift')
if receipt.get('job_total')!=43 or receipt.get('completed_success_jobs')!=43 or receipt.get('status')!='completed' or receipt.get('conclusion')!='success':
 die('terminal receipt result drift')
if subprocess.run(['git','cat-file','-e',RECEIPT_SHA+'^{commit}']).returncode: die('receipt commit missing locally')
if subprocess.run(['git','merge-base','--is-ancestor',RECEIPT_SHA,'HEAD']).returncode: die('receipt commit is not an ancestor of HEAD')
dec=E.get('governance_decision') or {}
required_false=('authorizes_gap_removal','authorizes_current_ledger_mutation','authorizes_authority_inference','website_construction_allowed','deployment_allowed')
for k in required_false:
 if dec.get(k) is not False: die('fail-closed decision drift: '+k)
if dec.get('stage2_status')!='BLOCKED': die('Stage-02 must remain BLOCKED')

results=[]
for script in VALIDATORS:
 p=root/script
 if not p.is_file(): die('validator missing: '+script)
 r=subprocess.run([sys.executable,script],text=True,capture_output=True)
 results.append({'validator':script,'returncode':r.returncode,'stdout_tail':r.stdout.strip().splitlines()[-3:]})
 if r.returncode!=0:
  sys.stderr.write(r.stdout+'\n'+r.stderr+'\n')
  die('nested architecture validator failed: '+script)

for filename,expected in OUTPUTS.items():
 p=root/filename
 if not p.is_file(): die('expected machine audit output missing: '+filename)
 try: obj=json.loads(p.read_text(encoding='utf-8'))
 except Exception as exc: die(f'{filename}: invalid JSON: {exc}')
 if not isinstance(obj,dict): die(filename+': root mapping required')
 assert_fail_closed_json(obj,filename,expected)

result={
 'artifact_type':'ARCHITECTURE_GAP_UNRESOLVED_EVIDENCE_VALIDATION_RESULT',
 'artifact_uid':'FRESH-RUN-003-STAGE2-ARCHITECTURE-GAP-UNRESOLVED-EVIDENCE-VALIDATION-V212-R1',
 'validated_evidence_ref':str(evidence_path),
 'source_r4_git_blob':R4_BLOB,
 'architecture_category_count':6,
 'architecture_gap_total':133,
 'architecture_authorized_removals':0,
 'architecture_unresolved_after_full_audit':133,
 'functional_gap_total':167,
 'input_source_gap_total':34,
 'nested_validator_count':len(VALIDATORS),
 'nested_validators_all_passed':True,
 'receipt_run_number':207,
 'receipt_run_id':34783179077,
 'receipt_exact_head_sha':RECEIPT_SHA,
 'receipt_jobs':'43/43 SUCCESS',
 'stage2_status':'BLOCKED',
 'website_construction_allowed':False,
 'deployment_allowed':False,
 'nested_validator_results':results,
}
Path('stage2_architecture_unresolved_evidence_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: Architecture 133 unresolved consolidation exactly covers 50+44+18+13+7+1')
print('PASS: 11 dedicated/current architecture validators all re-executed successfully')
print('PASS: authorized removals remain 0; Current remains 167 = 133 Architecture + 34 Input Source')
print('PASS: Stage-02 remains BLOCKED; website construction/deployment remain forbidden')
