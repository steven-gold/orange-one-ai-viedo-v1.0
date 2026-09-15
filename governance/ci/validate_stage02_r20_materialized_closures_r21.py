#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
PRODUCT_ROOT = RUN / "04_PAGE_FUNCTIONAL_CONTRACT"
R20 = ROOT / "governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R20_BOUNDED_MATERIALIZATION_R21_RECEIPT.yaml"
PAGES = ("CORE-01", "ASSET-01")


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def sig(page, rem):
    ds = rem.get("defect_signature") or {}
    return (page, ds.get("category"), str(ds.get("uid")), ds.get("detail"))


def r20_sig(rec):
    return (rec.get("page_uid"), rec.get("category"), str(rec.get("target_uid")), rec.get("missing_field_or_relation"))


r20 = load(R20)
receipt = load(RECEIPT)
auto = [r for r in (r20.get("records") or []) if r.get("authorized_for_auto_completion") is True]
if len(auto) != 19:
    die(f"R20_AUTO_DENOMINATOR:{len(auto)}")
expected = {r20_sig(r): r for r in auto}
if len(expected) != 19:
    die("R20_AUTO_SIGNATURE_NOT_UNIQUE")
actual_r21 = {}
all_actual = {}
by_page = Counter()
for page in PAGES:
    ledger = load(PRODUCT_ROOT / page / "AUTO_COMPLETION_SCOPE_LEDGER.yaml")
    if ledger.get("artifact_type") != "AUTO_COMPLETION_SCOPE_LEDGER" or ledger.get("page_uid") != page:
        die(f"LEDGER_IDENTITY:{page}")
    rems = ledger.get("remediations") or []
    if ledger.get("materialized_remediation_count") != len(rems):
        die(f"LEDGER_COUNT_DRIFT:{page}")
    if ledger.get("stage_exit_claimed") is not False:
        die(f"PREMATURE_STAGE_EXIT:{page}")
    if str(R20.relative_to(ROOT)) not in (ledger.get("source_classification_refs") or []):
        die(f"R20_SOURCE_REF_NOT_BOUND:{page}")
    for rem in rems:
        key = sig(page, rem)
        if key in all_actual:
            die(f"DUPLICATE_LEDGER_SIGNATURE:{key}")
        all_actual[key] = rem
        by_page[page] += 1
        if rem.get("source_cycle") == "R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY":
            if key not in expected:
                die(f"UNAUTHORIZED_R21_REMEDIATION:{key}")
            actual_r21[key] = rem
if len(all_actual) != 36:
    die(f"TOTAL_PRODUCT_MATERIALIZATION_NOT_36:{len(all_actual)}")
if set(actual_r21) != set(expected):
    die(f"R21_SET_MISMATCH:missing={sorted(set(expected)-set(actual_r21))}:extra={sorted(set(actual_r21)-set(expected))}")
if len(actual_r21) != 19:
    die(f"R21_TOTAL_NOT_19:{len(actual_r21)}")

cats = Counter()
for key, rem in actual_r21.items():
    exp = expected[key]
    cats[key[1]] += 1
    if rem.get("owning_layer") != "STAGE-02_PAGE_FUNCTIONAL_CONTRACT":
        die(f"OWNING_LAYER_DRIFT:{key}")
    if rem.get("source_blocker_uid") != exp.get("blocker_uid"):
        die(f"BLOCKER_UID_DRIFT:{key}")
    if rem.get("completion_basis") != exp.get("closure_type"):
        die(f"COMPLETION_BASIS_DRIFT:{key}")
    proof = rem.get("exact_proof") or {}
    if proof.get("candidate_value") != exp.get("candidate_value"):
        die(f"CANDIDATE_VALUE_DRIFT:{key}")
    if proof.get("candidate_evidence") != exp.get("candidate_evidence"):
        die(f"CANDIDATE_EVIDENCE_DRIFT:{key}")
    if proof.get("distinct_candidate_value_count") != 1 or proof.get("full_stage02_functional_contract_sources_checked") is not True:
        die(f"PROOF_NOT_EXACT:{key}")
    for field in (
        "semantic_inference_used",
        "ai_invented_business_value",
        "external_authority_resolution_performed",
        "outside_frozen_registered_dependency_closure",
        "generic_crud_symmetry_expansion_used",
        "sibling_feature_symmetry_expansion_used",
    ):
        if rem.get(field) is not False:
            die(f"FORBIDDEN_MATERIALIZATION_METHOD:{key}:{field}")
    closure = rem.get("materialized_closure") or {}
    if key[1] == "POST_ACTION_VALIDATION_NODE_MISSING":
        if closure.get("closure_type") != "POST_ACTION_VALIDATION_FROM_UNIQUE_FROZEN_SUCCESS_SIGNAL":
            die(f"POST_VALIDATION_CLOSURE_TYPE:{key}")
        if closure.get("action_uid") != key[2] or closure.get("validation_signal") != exp.get("candidate_value"):
            die(f"POST_VALIDATION_CLOSURE_VALUE:{key}")
        if closure.get("projection_rule") != "EXACT_COPY_OF_SINGLE_CANONICAL_R20_FROZEN_CHAIN_SIGNAL":
            die(f"POST_VALIDATION_PROJECTION_RULE:{key}")
    elif key[1] == "STATE_TRANSITION_LEDGER_FIELD_MISSING":
        if "mutation_owner" not in str(key[3]):
            die(f"TRANSITION_R21_NON_OWNER_FIELD:{key}")
        if closure.get("closure_type") != "TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER":
            die(f"TRANSITION_CLOSURE_TYPE:{key}")
        if closure.get("transition_uid") != key[2] or closure.get("mutation_owner") != exp.get("candidate_value"):
            die(f"TRANSITION_CLOSURE_VALUE:{key}")
        if closure.get("projection_rule") != "EXACT_COPY_OF_SINGLE_CANONICAL_R20_TRIGGER_RUNTIME_OWNER":
            die(f"TRANSITION_PROJECTION_RULE:{key}")
    else:
        die(f"UNEXPECTED_R21_CATEGORY:{key}")

if dict(cats) != {"POST_ACTION_VALIDATION_NODE_MISSING": 15, "STATE_TRANSITION_LEDGER_FIELD_MISSING": 4}:
    die(f"R21_CATEGORY_COUNTS:{dict(cats)}")
if receipt.get("before_materialized_product_total") != 17 or receipt.get("materialized_now_total") != 19 or receipt.get("after_materialized_product_total") != 36:
    die("R21_RECEIPT_DENOMINATOR_DRIFT")
if receipt.get("blocker_reduction_claimed_before_reexecution") != 0:
    die("R21_PREMATURE_BLOCKER_REDUCTION")
for field in ("current_specification_mutated", "immutable_stage1_source_mutated", "external_authority_resolution_performed", "semantic_inference_used", "ai_invented_business_value"):
    if receipt.get(field) is not False:
        die(f"R21_RECEIPT_SAFETY_DRIFT:{field}")
print(f"PASS: R21 materialized exact R20 AUTO set 19/19; total product materializations=36; pages={dict(by_page)}")
print("PASS: post-action validation exact projections=15; transition mutation-owner exact projections=4")
print("PASS: prior 17 materializations preserved; no semantic inference, AI value invention, external-authority mutation, Stage-1 mutation, or Current Spec mutation")
print("PASS: blocker reduction remains unclaimed until fresh effective reexecution")
