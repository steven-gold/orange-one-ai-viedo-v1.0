#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT"
DOC = ROOT / "governance/test/stage02/STAGE02_R20_TRANSITION_OWNER_INVALIDATION_R24.yaml"
ASSET = PRODUCT / "ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml"
CORE = PRODUCT / "CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R24_CORRECTNESS_ROLLBACK_RECEIPT.yaml"

def die(msg): print(f"BLOCK: {msg}", file=sys.stderr); raise SystemExit(1)
def load(path):
    if not path.is_file(): die(f"MISSING:{path.relative_to(ROOT)}")
    obj=yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj,dict): die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj

def dump(path,obj): path.write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False,width=180),encoding="utf-8")

doc=load(DOC); asset=load(ASSET); core=load(CORE)
rows=doc.get("invalidations") or []
blockers={x.get("blocker_uid") for x in rows}
if len(blockers)!=4: die(f"R24_INVALIDATION_COUNT:{len(blockers)}")
if asset.get("materialized_remediation_count")!=33 or len(asset.get("remediations") or [])!=33: die("R24_ASSET_BASELINE_NOT_33")
if core.get("materialized_remediation_count")!=5 or len(core.get("remediations") or [])!=5: die("R24_CORE_BASELINE_NOT_5")

before=list(asset.get("remediations") or [])
removed=[]; kept=[]
for rem in before:
    if rem.get("source_cycle")=="R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY" and rem.get("source_blocker_uid") in blockers:
        ds=rem.get("defect_signature") or {}; cl=rem.get("materialized_closure") or {}
        if ds.get("category")!="STATE_TRANSITION_LEDGER_FIELD_MISSING" or ds.get("detail")!="mutation_owner": die(f"R24_TARGET_SIGNATURE_DRIFT:{rem.get('source_blocker_uid')}")
        if cl.get("closure_type")!="TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER": die(f"R24_TARGET_CLOSURE_DRIFT:{rem.get('source_blocker_uid')}")
        removed.append(rem)
    else:
        kept.append(rem)
if len(removed)!=4 or {x.get("source_blocker_uid") for x in removed}!=blockers: die("R24_REMOVAL_SET_DRIFT")
if len(kept)!=29: die(f"R24_ASSET_AFTER_COUNT:{len(kept)}")

# Prove all 15 non-transition R20 auto materializations and both R22 corrections remain.
cycles=Counter(str(x.get("source_cycle") or "R3_BOUNDED_FUNCTIONAL_COMPLETION") for x in kept)
if cycles.get("R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY")!=15: die(f"R24_VALID_R20_COUNT_DRIFT:{dict(cycles)}")
if cycles.get("R22_POST_ACTION_SIGNAL_ROLE_CORRECTION")!=2: die(f"R24_R22_COUNT_DRIFT:{dict(cycles)}")
asset["remediations"]=kept
asset["materialized_remediation_count"]=29
refs=list(asset.get("source_classification_refs") or [])
r24ref=str(DOC.relative_to(ROOT))
if r24ref not in refs: refs.append(r24ref)
asset["source_classification_refs"]=refs
asset["latest_bounded_completion_cycle"]="R24_CORRECTNESS_ROLLBACK_INVALID_R20_TRANSITION_OWNER"
asset["stage_exit_claimed"]=False
dump(ASSET,asset)

head=subprocess.run(["git","rev-parse","HEAD"],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
receipt={
  "schema_version":1,
  "artifact_type":"STAGE02_R24_CORRECTNESS_ROLLBACK_RECEIPT",
  "normative_authority":False,
  "stage_uid":"STAGE-02",
  "source_head_sha":head,
  "source_invalidation_ref":r24ref,
  "before_product_materialization_total":38,
  "removed_invalid_materialization_total":4,
  "after_product_materialization_total":34,
  "after_materialized_by_page":{"CORE-01":5,"ASSET-01":29},
  "removed_blocker_uids":sorted(blockers),
  "removed_remediation_uids":sorted(str(x.get("remediation_uid")) for x in removed),
  "preserved_r20_valid_post_action_total":15,
  "preserved_r22_role_correct_total":2,
  "replacement_materialization_total":0,
  "blocker_reduction_claimed":0,
  "effective_gap_increase_claimed_before_fresh_reexecution":0,
  "current_specification_mutated":False,
  "immutable_stage1_source_mutated":False,
  "product_authority_value_invented":False,
  "stage03_allowed":False,
  "website_construction_allowed":False,
  "deployment_allowed":False,
}
dump(RECEIPT,receipt)
print("PASS: removed exactly four invalid R20 transition mutation_owner materializations")
print("PASS: product ledger 38 -> 34 (CORE=5 ASSET=29); valid R20=15 and R22=2 preserved")
print("PASS: no replacement mutation_owner invented; fresh reexecution still required")
