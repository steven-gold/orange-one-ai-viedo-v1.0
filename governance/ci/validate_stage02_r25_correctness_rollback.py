#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
PRODUCT=ROOT/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
DOC=ROOT/'governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_INVALIDATION_R25.yaml'
RECEIPT=ROOT/'governance/test/stage02/STAGE02_R25_CORRECTNESS_ROLLBACK_RECEIPT.yaml'
def die(msg): print(f'BLOCK: {msg}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
doc=load(DOC); receipt=load(RECEIPT); blockers={x.get('blocker_uid') for x in doc.get('invalidations') or []}
if len(blockers)!=17: die('R25_DOC_BLOCKER_DENOMINATOR_DRIFT')
if receipt.get('artifact_type')!='STAGE02_R25_CORRECTNESS_ROLLBACK_RECEIPT': die('R25_RECEIPT_IDENTITY_DRIFT')
if receipt.get('before_product_materialization_total')!=34 or receipt.get('removed_invalid_materialization_total')!=17 or receipt.get('after_product_materialization_total')!=17: die('R25_RECEIPT_ARITHMETIC_DRIFT')
if receipt.get('removed_r20_post_action_total')!=15 or receipt.get('removed_r22_post_action_total')!=2: die('R25_RECEIPT_SOURCE_COUNTS_DRIFT')
if set(receipt.get('removed_blocker_uids') or [])!=blockers: die('R25_RECEIPT_BLOCKER_SET_DRIFT')
if receipt.get('replacement_materialization_total')!=0 or receipt.get('product_authority_value_invented') is not False: die('R25_REPLACEMENT_DRIFT')
allrems={}; by=Counter(); cycles=Counter()
for page,expected in (('CORE-01',5),('ASSET-01',12)):
    l=load(PRODUCT/page/'AUTO_COMPLETION_SCOPE_LEDGER.yaml'); rems=l.get('remediations') or []
    if l.get('materialized_remediation_count')!=expected or len(rems)!=expected: die(f'R25_LEDGER_COUNT_DRIFT:{page}:{len(rems)}')
    by[page]=len(rems)
    for rem in rems:
        ds=rem.get('defect_signature') or {}; s=(page,ds.get('category'),str(ds.get('uid')),ds.get('detail'))
        if s in allrems: die(f'R25_DUPLICATE_SIGNATURE:{s}')
        allrems[s]=rem; cycles[str(rem.get('source_cycle') or 'R3_BOUNDED_FUNCTIONAL_COMPLETION')]+=1
        if rem.get('source_blocker_uid') in blockers: die(f'R25_INVALID_BLOCKER_REMAINS:{rem.get("source_blocker_uid")}')
        if ds.get('category')=='POST_ACTION_VALIDATION_NODE_MISSING': die(f'R25_POST_ACTION_MATERIALIZATION_REMAINS:{s}')
if len(allrems)!=17 or by!=Counter({'ASSET-01':12,'CORE-01':5}): die(f'R25_TOTAL_DRIFT:{len(allrems)}:{dict(by)}')
if cycles.get('R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY',0)!=0 or cycles.get('R22_POST_ACTION_SIGNAL_ROLE_CORRECTION',0)!=0: die(f'R25_INVALID_SOURCE_CYCLE_REMAINS:{dict(cycles)}')
print('PASS: R25 corrected product materializations=17 (CORE=5 ASSET=12)')
print('PASS: no post-action validation materialization remains; no R20/R22 auto cycle remains')
