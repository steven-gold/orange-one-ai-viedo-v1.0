#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "governance/test/stage02/STAGE02_R20_TRANSITION_OWNER_INVALIDATION_R24.yaml"
EXPECTED = {
    ("STAGE02-R5-PRODUCT-AUTH-091", "ASSET-01-STTR-01"),
    ("STAGE02-R5-PRODUCT-AUTH-099", "ASSET-01-STTR-03"),
    ("STAGE02-R5-PRODUCT-AUTH-103", "ASSET-01-STTR-04"),
    ("STAGE02-R5-PRODUCT-AUTH-107", "ASSET-01-STTR-05"),
}

def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr); raise SystemExit(1)

def load(path):
    if not path.is_file(): die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict): die("R24_MAPPING_REQUIRED")
    return obj

doc = load(DOC)
if doc.get("artifact_type") != "NON_NORMATIVE_STAGE02_R20_TRANSITION_OWNER_INVALIDATION_R24" or doc.get("stage_uid") != "STAGE-02":
    die("R24_IDENTITY_DRIFT")
if doc.get("normative_authority") is not False:
    die("R24_NORMATIVE_AUTHORITY_DRIFT")
base = doc.get("correction_basis") or {}
for key in ("r17_precedes_r20_as_category_exact_trace", "same_transition_physical_field_required", "action_owner_to_transition_mutation_owner_promotion_forbidden", "rollback_only_no_replacement_value", "current_specification_mutation_forbidden", "stage1_raw_mutation_forbidden"):
    if base.get(key) is not True: die(f"R24_CORRECTION_BASIS_DRIFT:{key}")
den = doc.get("denominators") or {}
if den.get("r20_state_transition_auto_total") != 4 or den.get("invalid_r20_state_transition_auto_total") != 4 or den.get("valid_r20_state_transition_auto_total") != 0:
    die(f"R24_INVALIDATION_DENOMINATOR_DRIFT:{den}")
if den.get("current_product_materialization_total_before_rollback") != 38 or den.get("expected_product_materialization_total_after_rollback") != 34:
    die("R24_PRODUCT_DENOMINATOR_DRIFT")
if den.get("blocker_reduction_claimed_before_fresh_reexecution") != 0:
    die("R24_PREMATURE_REDUCTION")
rows = doc.get("invalidations") or []
if len(rows) != 4 or {(x.get("blocker_uid"), x.get("transition_uid")) for x in rows} != EXPECTED:
    die("R24_INVALIDATION_SET_DRIFT")
for row in rows:
    if row.get("field") != "mutation_owner" or row.get("rollback_required") is not True or row.get("replacement_value") is not None:
        die(f"R24_ROW_CONTRACT_DRIFT:{row.get('blocker_uid')}")
    inv = row.get("r17_invariant") or {}
    if inv.get("field_must_be_physically_present_on_same_exact_transition_uid") is not True or inv.get("action_owner_may_supply_mutation_owner") is not False or inv.get("r17_exact_transition_ledger_field_evidence") != []:
        die(f"R24_R17_INVARIANT_DRIFT:{row.get('blocker_uid')}")
    if row.get("semantic_inference_used_for_replacement") is not False or row.get("product_authority_value_invented") is not False:
        die(f"R24_SAFETY_DRIFT:{row.get('blocker_uid')}")
if doc.get("current_specification_mutated") is not False or doc.get("immutable_stage1_source_mutated") is not False:
    die("R24_MUTATION_FLAG_DRIFT")
print("PASS: R24 exact invalidation set=4; rollback-only; no replacement authority invented")
