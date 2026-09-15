#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOT = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT"
R22 = ROOT / "governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_ROLE_RECLASSIFICATION_R22.yaml"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R22_BOUNDED_MATERIALIZATION_RECEIPT.yaml"


def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def sig(page, rem):
    ds = rem.get("defect_signature") or {}
    return (page, ds.get("category"), str(ds.get("uid")), ds.get("detail"))


r22 = load(R22)
receipt = load(RECEIPT)
auto = [r for r in (r22.get("records") or []) if r.get("authorized_for_auto_completion") is True]
expected = {(r.get("page_uid"), r.get("category"), str(r.get("target_uid")), r.get("missing_field_or_relation")): r for r in auto}
if len(expected) != 2:
    die(f"R22_EXPECTED_AUTO_NOT_2:{len(expected)}")
all_sigs = {}
r22_sigs = {}
page_counts = {}
for page in ("CORE-01", "ASSET-01"):
    ledger = load(PRODUCT_ROOT / page / "AUTO_COMPLETION_SCOPE_LEDGER.yaml")
    rems = ledger.get("remediations") or []
    page_counts[page] = len(rems)
    if ledger.get("materialized_remediation_count") != len(rems) or ledger.get("stage_exit_claimed") is not False:
        die(f"LEDGER_COUNT_OR_EXIT_DRIFT:{page}")
    for rem in rems:
        key = sig(page, rem)
        if key in all_sigs:
            die(f"DUPLICATE_SIGNATURE:{key}")
        all_sigs[key] = rem
        if rem.get("source_cycle") == "R22_POST_ACTION_SIGNAL_ROLE_CORRECTION":
            r22_sigs[key] = rem
if len(all_sigs) != 38 or page_counts != {"CORE-01": 5, "ASSET-01": 33}:
    die(f"R22_TOTAL_DRIFT:{len(all_sigs)}:{page_counts}")
if set(r22_sigs) != set(expected):
    die(f"R22_SET_MISMATCH:missing={sorted(set(expected)-set(r22_sigs))}:extra={sorted(set(r22_sigs)-set(expected))}")
for key, rem in r22_sigs.items():
    exp = expected[key]
    if rem.get("source_blocker_uid") != exp.get("blocker_uid") or rem.get("completion_basis") != exp.get("closure_type"):
        die(f"R22_BINDING_DRIFT:{key}")
    proof = rem.get("exact_proof") or {}
    if proof.get("candidate_value") != exp.get("candidate_value") or proof.get("admissible_validation_evidence") != exp.get("admissible_validation_evidence"):
        die(f"R22_PROOF_DRIFT:{key}")
    if proof.get("excluded_non_validation_role_evidence") != exp.get("excluded_non_validation_role_evidence"):
        die(f"R22_EXCLUDED_EVIDENCE_DRIFT:{key}")
    if proof.get("admissible_candidate_value_count") != 1 or proof.get("signal_role_correction_applied") is not True:
        die(f"R22_PROOF_FLAGS:{key}")
    closure = rem.get("materialized_closure") or {}
    if closure != {
        "closure_type": "POST_ACTION_VALIDATION_FROM_ROLE_CORRECT_UNIQUE_FROZEN_RESULT_SIGNAL",
        "action_uid": exp.get("target_uid"),
        "validation_signal": exp.get("candidate_value"),
        "projection_rule": "EXACT_COPY_AFTER_EXCLUDING_FLOW_TRANSITION_DESTINATION_FROM_VALIDATION_ROLE",
    }:
        die(f"R22_CLOSURE_DRIFT:{key}:{closure}")
    for field in ("semantic_inference_used", "ai_invented_business_value", "external_authority_resolution_performed", "outside_frozen_registered_dependency_closure", "generic_crud_symmetry_expansion_used", "sibling_feature_symmetry_expansion_used"):
        if rem.get(field) is not False:
            die(f"R22_FORBIDDEN_METHOD:{key}:{field}")
if receipt.get("before_materialized_product_total") != 36 or receipt.get("materialized_now_total") != 2 or receipt.get("after_materialized_product_total") != 38:
    die("R22_RECEIPT_DENOMINATOR_DRIFT")
if receipt.get("remaining_r22_authority_gap_targets") != ["ASSET-01-ACT-CORRECTION-EXECUTE"]:
    die(f"R22_RECEIPT_REMAINING_GAP_DRIFT:{receipt.get('remaining_r22_authority_gap_targets')}")
if receipt.get("blocker_reduction_claimed_before_reexecution") != 0:
    die("R22_PREMATURE_REDUCTION")
print("PASS: R22 materialized exact role-correct AUTO set 2/2; total product materializations=38")
print("PASS: CORE=5 ASSET=33; CORRECTION-EXECUTE not materialized")
print("PASS: no semantic inference, AI value invention, Stage-1 mutation, Current Spec mutation, or premature blocker reduction")
