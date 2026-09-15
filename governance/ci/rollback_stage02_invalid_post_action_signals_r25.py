#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import subprocess,sys,yaml
ROOT=Path(__file__).resolve().parents[2]
PRODUCT=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
DOC=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_INVALIDATION_R25.yaml'
ASSET=PRODUCT/'ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml'; CORE=PRODUCT/'CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml'
RECEIPT=ROOT/'governance/test/stage02/STAGE02_R25_CORRECTNESS_ROLLBACK_RECEIPT.yaml'
def die(msg): print(f'BLOCK: {msg}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
def dump(p,o): p.write_text(yaml.safe_dump(o,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
doc=load(DOC); asset=load(ASSET); core=load(CORE)
rows=doc.get('invalidations') or []; blockers={x.get('blocker_uid') for x in rows}
if len(blockers)!=17: die(f'R25_BLOCKER_COUNT:{len(blockers)}')
if asset.get('materialized_remediation_count')!=29 or len(asset.get('remediations') or [])!=29: die('R25_ASSET_BASELINE_NOT_29')
if core.get('materialized_remediation_count')!=5 or len(core.get('remediations') or [])!=5: die('R25_CORE_BASELINE_NOT_5')
removed=[]; kept=[]
for rem in asset.get('remediations') or []:
    if rem.get('source_blocker_uid') in blockers and rem.get('source_cycle') in {'R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY','R22_POST_ACTION_SIGNAL_ROLE_CORRECTION'}:
        ds=rem.get('defect_signature') or {}; cl=rem.get('materialized_closure') or {}
        if ds.get('category')!='POST_ACTION_VALIDATION_NODE_MISSING' or ds.get('detail')!='no explicit success/validation/evaluation contract': die(f'R25_TARGET_SIGNATURE_DRIFT:{rem.get("source_blocker_uid")}')
        if cl.get('closure_type') not in {'POST_ACTION_VALIDATION_FROM_UNIQUE_FROZEN_SUCCESS_SIGNAL','POST_ACTION_VALIDATION_FROM_ROLE_CORRECT_UNIQUE_FROZEN_RESULT_SIGNAL'}: die(f'R25_TARGET_CLOSURE_DRIFT:{rem.get("source_blocker_uid")}')
        removed.append(rem)
    else: kept.append(rem)
if len(removed)!=17 or {x.get('source_blocker_uid') for x in removed}!=blockers: die('R25_REMOVAL_SET_DRIFT')
if len(kept)!=12: die(f'R25_ASSET_AFTER_COUNT:{len(kept)}')
cycles=Counter(str(x.get('source_cycle') or 'R3_BOUNDED_FUNCTIONAL_COMPLETION') for x in kept)
if cycles.get('R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY',0)!=0 or cycles.get('R22_POST_ACTION_SIGNAL_ROLE_CORRECTION',0)!=0: die(f'R25_INVALID_CYCLE_REMAINS:{dict(cycles)}')
asset['remediations']=kept; asset['materialized_remediation_count']=12
refs=list(asset.get('source_classification_refs') or []); ref=str(DOC.relative_to(ROOT))
if ref not in refs: refs.append(ref)
asset['source_classification_refs']=refs; asset['latest_bounded_completion_cycle']='R25_CORRECTNESS_ROLLBACK_INVALID_POST_ACTION_SIGNAL_PROMOTION'; asset['stage_exit_claimed']=False
dump(ASSET,asset)
head=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
receipt={'schema_version':1,'artifact_type':'STAGE02_R25_CORRECTNESS_ROLLBACK_RECEIPT','normative_authority':False,'stage_uid':'STAGE-02','source_head_sha':head,'source_invalidation_ref':ref,'before_product_materialization_total':34,'removed_invalid_materialization_total':17,'after_product_materialization_total':17,'after_materialized_by_page':{'CORE-01':5,'ASSET-01':12},'removed_blocker_uids':sorted(blockers),'removed_remediation_uids':sorted(str(x.get('remediation_uid')) for x in removed),'removed_r20_post_action_total':sum(x.get('source_cycle')=='R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY' for x in removed),'removed_r22_post_action_total':sum(x.get('source_cycle')=='R22_POST_ACTION_SIGNAL_ROLE_CORRECTION' for x in removed),'replacement_materialization_total':0,'blocker_reduction_claimed':0,'effective_gap_increase_claimed_before_fresh_reexecution':0,'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'product_authority_value_invented':False,'stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False}
dump(RECEIPT,receipt)
print('PASS: removed exactly 17 invalid post-action signal promotions (R20=15 R22=2)')
print('PASS: product ledger 34 -> 17 (CORE=5 ASSET=12)')
print('PASS: no replacement validation contract invented; fresh reexecution required')
