#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, yaml

root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
r3=base/'FUNCTIONAL_CHAIN_GAP_LEDGER.yaml'
r4=base/'FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
r2=base/'SHARED_OWNER_PORT_MAP_R2.yaml'
ev=base/'EXTERNAL_AUTHORITY/STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml'
raw= root/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'

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

def expand(groups):
    rows=[]
    for cat,g in groups.items():
        klass=g.get('class')
        fields=g.get('required_fields') or []
        for page in ('CORE-01','ASSET-01'):
            pg=g.get(page)
            if not isinstance(pg,dict): continue
            if 'action_uids' in pg:
                rows += [(page,klass,cat,uid,None) for uid in pg['action_uids']]
            elif 'transition_uids' in pg:
                rows += [(page,klass,cat,uid,f) for uid in pg['transition_uids'] for f in fields]
    return rows

locks={
    r3:'093c72a8e3227c1228180a29586980ab5e8f85cd',
    r2:'65f821ad766994716f4336e961b1b160b5aac457',
    ev:'ff99fd8c48f4593c5ef5cdeab1d49c5caa027cfd',
    raw:'9668e2307c722ea4cf64f93f07c92da1b3abcc28',
}
for p,b in locks.items():
    if gitobj(p)!=b: die(f'locked predecessor/evidence drift {p}')

A=load(r3); B=load(r4); S=load(r2); E=load(ev); R=load(raw)
if B.get('artifact_type')!='FUNCTIONAL_CHAIN_GAP_LEDGER' or B.get('operation_uid')!='FUNCTIONAL_CHAIN_COMPILE': die('R4 functional ledger identity drift')
if B.get('detector_revision')!='v4-external-authority-successor-aware': die('R4 detector revision drift')
if B.get('status')!='CANDIDATE_AWAITING_DEDICATED_GATE': die('R4 must remain candidate before dedicated CI receipt')
so=B.get('successor_of') or {}
if so.get('git_blob')!='093c72a8e3227c1228180a29586980ab5e8f85cd' or so.get('predecessor_gap_total')!=171: die('R4 predecessor identity drift')
ri=B.get('resolution_input') or {}
if ri.get('shared_owner_successor_git_blob')!='65f821ad766994716f4336e961b1b160b5aac457' or ri.get('external_authority_evidence_git_blob')!='ff99fd8c48f4593c5ef5cdeab1d49c5caa027cfd': die('R4 resolution evidence binding drift')
expected_consumers=['ASSET-01-ACT-CORRECTION-GENERATE','ASSET-01-ACT-CORRECTION-APPROVE','ASSET-01-ACT-RESTORE-AS-NEW','ASSET-01-ACT-VERSION-LOCK']
if ri.get('resolved_gap_count')!=4 or ri.get('exact_resolved_consumers')!=expected_consumers: die('R4 resolved consumer set drift')

# Prove exact semantic delta: predecessor has precisely the four Authority gaps and every other expanded gap survives unchanged.
ag= A.get('category_groups') or {}; bg=B.get('category_groups') or {}
shared=ag.get('SHARED_OWNER_AUTHORITY_UNRESOLVED') or {}
sp=(shared.get('ASSET-01') or {}).get('action_uids') or []
if sp!=expected_consumers or (shared.get('ASSET-01') or {}).get('expanded_gap_count')!=4: die('predecessor shared Authority gap set drift')
expected_group_keys=set(ag)-{'SHARED_OWNER_AUTHORITY_UNRESOLVED'}
if set(bg)!=expected_group_keys: die('R4 category set changed beyond resolved Authority category')
for k in expected_group_keys:
    if bg[k]!=ag[k]: die(f'R4 modified unrelated predecessor category: {k}')
old_rows=expand(ag); new_rows=expand(bg)
old_set=set(old_rows); new_set=set(new_rows)
removed=old_set-new_set; added=new_set-old_set
expected_removed={('ASSET-01','AUTHORITY_GAP','SHARED_OWNER_AUTHORITY_UNRESOLVED',x,None) for x in expected_consumers}
if removed!=expected_removed or added: die(f'R4 semantic delta invalid removed={removed} added={added}')
if len(old_rows)!=171 or len(new_rows)!=167: die(f'expanded cardinality invalid old={len(old_rows)} new={len(new_rows)}')

summary=B.get('summary') or {}
if summary.get('total')!=167 or summary.get('pages')!={'CORE-01':45,'ASSET-01':122}: die('R4 page totals drift')
if summary.get('classes')!={'ARCHITECTURE_GAP':133,'INPUT_SOURCE_GAP':34}: die('R4 class totals drift')
expected_cats={'STATE_TRANSITION_LEDGER_FIELD_MISSING':50,'FAILURE_STATE_ERROR_BINDING_MISSING':44,'PAYLOAD_INPUT_CONTRACT_MISSING':34,'POST_ACTION_VALIDATION_NODE_MISSING':18,'AUDIT_EVENT_NODE_MISSING':13,'SUCCESS_NEXT_STATE_BINDING_MISSING':7,'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1}
if summary.get('categories')!=expected_cats or sum(expected_cats.values())!=167: die('R4 category totals drift')

# Prove the resolution source itself says all four are exact Current shared-owner operation bindings.
if S.get('status')!='RESOLVED_AUTHORITY_GAP': die('shared-owner R2 is not resolved')
cons=S.get('consumers') or []
by_action={x.get('action_uid'):x for x in cons}
if set(by_action)!=set(expected_consumers): die('shared-owner R2 consumer set drift')
raw_actions={x.get('action_uid'):x for x in ((R.get('registries') or {}).get('actions') or []) if isinstance(x,dict)}
for uid in expected_consumers:
    c=by_action[uid]; rb=(raw_actions.get(uid) or {}).get('runtime_binding') or {}
    if c.get('status')!='RESOLVED_EXACT_AUTHORITY': die(f'{uid} R2 not exact resolved')
    if c.get('resolved_owner_uid')!='ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY': die(f'{uid} owner drift')
    if c.get('resolved_operation_uid')!=rb.get('shared_operation_id'): die(f'{uid} operation does not match Raw Source')
    if rb.get('shared_authority_id')!='ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or rb.get('binding_kind')!='SHARED_OPERATION_REFERENCE': die(f'{uid} Raw Source binding kind/authority drift')
    if c.get('resolved_port_uid') is not None or c.get('port_uid_status')!='NOT_APPLICABLE_BY_BINDING_KIND': die(f'{uid} fake integration port introduced')

ma=E.get('materialized_authorities') or {}
if (ma.get('GAP-006') or {}).get('functional_authority_gap_resolved') is not True: die('external Authority evidence does not resolve GAP-006')
if (ma.get('GAP-005') or {}).get('s061_lifecycle_closure_claim') is not False or (ma.get('GAP-008') or {}).get('s061_lifecycle_closure_claim') is not False: die('unrelated S061 lifecycle was bulk-closed')
pol=B.get('resolution_policy') or {}
if pol.get('functional_completion_claim') is not False or pol.get('authority_gap_ai_guess')!='FORBIDDEN' or pol.get('website_construction_allowed') is not False or pol.get('deployment_allowed') is not False: die('R4 fail-closed policy drift')

result={'schema_version':1,'operation_uid':'FUNCTIONAL_CHAIN_COMPILE','detector_revision':'v4-external-authority-successor-aware','predecessor_gap_total':171,'resolved_exact_authority_gaps':4,'current_candidate_gap_total':167,'pages':{'CORE-01':45,'ASSET-01':122},'classes':{'ARCHITECTURE_GAP':133,'INPUT_SOURCE_GAP':34},'removed_category':'SHARED_OWNER_AUTHORITY_UNRESOLVED','removed_consumers':expected_consumers,'functional_completion':False,'website_construction_allowed':False,'deployment_allowed':False}
Path('stage2_functional_gap_successor_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
print('PASS: FUNCTIONAL_CHAIN_COMPILE successor removes exactly 4 GAP-006 Authority gaps and no other gap identity')
print('PASS: candidate gap total is 167 = ARCHITECTURE 133 + INPUT_SOURCE 34; CORE 45 / ASSET 122')
print('PASS: Raw Source and R3 predecessor remain immutable; no fake port UID and no GAP-005/GAP-008 S061 bulk closure')
print('PASS: candidate remains fail-closed until dedicated CI receipt/current-ledger supersession is recorded')
