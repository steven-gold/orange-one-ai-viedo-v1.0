#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
PRODUCT=ROOT/"00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT"
DOC=ROOT/"governance/test/stage02/STAGE02_R20_TRANSITION_OWNER_INVALIDATION_R24.yaml"
RECEIPT=ROOT/"governance/test/stage02/STAGE02_R24_CORRECTNESS_ROLLBACK_RECEIPT.yaml"
R20=ROOT/"governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml"
EXPECTED={"STAGE02-R5-PRODUCT-AUTH-091","STAGE02-R5-PRODUCT-AUTH-099","STAGE02-R5-PRODUCT-AUTH-103","STAGE02-R5-PRODUCT-AUTH-107"}

def die(msg): print(f"BLOCK: {msg}",file=sys.stderr); raise SystemExit(1)
def load(path):
    if not path.is_file(): die(f"MISSING:{path.relative_to(ROOT)}")
    obj=yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj,dict): die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj

doc=load(DOC); receipt=load(RECEIPT); r20=load(R20)
if receipt.get("artifact_type")!="STAGE02_R24_CORRECTNESS_ROLLBACK_RECEIPT" or receipt.get("stage_uid")!="STAGE-02": die("R24_RECEIPT_IDENTITY_DRIFT")
if receipt.get("before_product_materialization_total")!=38 or receipt.get("removed_invalid_materialization_total")!=4 or receipt.get("after_product_materialization_total")!=34: die("R24_RECEIPT_ARITHMETIC_DRIFT")
if set(receipt.get("removed_blocker_uids") or [])!=EXPECTED: die("R24_RECEIPT_BLOCKER_SET_DRIFT")
if receipt.get("replacement_materialization_total")!=0 or receipt.get("product_authority_value_invented") is not False: die("R24_REPLACEMENT_OR_INVENTION_DRIFT")
if receipt.get("current_specification_mutated") is not False or receipt.get("immutable_stage1_source_mutated") is not False: die("R24_MUTATION_FLAG_DRIFT")

all_rems={}; by_page=Counter(); cycle=Counter()
for page,expected in (("CORE-01",5),("ASSET-01",29)):
    ledger=load(PRODUCT/page/"AUTO_COMPLETION_SCOPE_LEDGER.yaml")
    rems=ledger.get("remediations") or []
    if ledger.get("materialized_remediation_count")!=expected or len(rems)!=expected: die(f"R24_LEDGER_COUNT_DRIFT:{page}:{len(rems)}")
    by_page[page]=len(rems)
    for rem in rems:
        ds=rem.get("defect_signature") or {}; sig=(page,ds.get("category"),str(ds.get("uid")),ds.get("detail"))
        if sig in all_rems: die(f"R24_DUPLICATE_SIGNATURE:{sig}")
        all_rems[sig]=rem
        cycle[str(rem.get("source_cycle") or "R3_BOUNDED_FUNCTIONAL_COMPLETION")]+=1
        if rem.get("source_blocker_uid") in EXPECTED: die(f"R24_INVALID_BLOCKER_STILL_PRESENT:{rem.get('source_blocker_uid')}")
        if (rem.get("materialized_closure") or {}).get("closure_type")=="TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER": die(f"R24_INVALID_CLOSURE_TYPE_STILL_PRESENT:{sig}")
if len(all_rems)!=34 or by_page!=Counter({"ASSET-01":29,"CORE-01":5}): die(f"R24_TOTAL_DRIFT:{len(all_rems)}:{dict(by_page)}")
if cycle.get("R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY")!=15 or cycle.get("R22_POST_ACTION_SIGNAL_ROLE_CORRECTION")!=2: die(f"R24_CYCLE_PRESERVATION_DRIFT:{dict(cycle)}")

valid_r20=[x for x in (r20.get("records") or []) if x.get("authorized_for_auto_completion") is True and x.get("category")=="POST_ACTION_VALIDATION_NODE_MISSING"]
if len(valid_r20)!=15: die(f"R24_R20_VALID_POST_ACTION_DENOMINATOR:{len(valid_r20)}")
ledger_r20={rem.get("source_blocker_uid") for rem in all_rems.values() if rem.get("source_cycle")=="R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY"}
if ledger_r20!={x.get("blocker_uid") for x in valid_r20}: die("R24_VALID_R20_PRESERVATION_SET_DRIFT")
print("PASS: R24 rollback product materializations=34 (CORE=5 ASSET=29)")
print("PASS: four invalid transition-owner closures absent; all 15 valid R20 post-action closures and 2 R22 corrections preserved")
