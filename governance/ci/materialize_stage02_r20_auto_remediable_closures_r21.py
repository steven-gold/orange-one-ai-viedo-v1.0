#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
PRODUCT_ROOT = RUN / "04_PAGE_FUNCTIONAL_CONTRACT"
R20 = ROOT / "governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R20_BOUNDED_MATERIALIZATION_R21_RECEIPT.yaml"
PAGES = ("CORE-01", "ASSET-01")
EXPECTED_OLD_TOTAL = 17
EXPECTED_NEW_TOTAL = 19
EXPECTED_AFTER_TOTAL = 36
EXPECTED_NEW_BY_CATEGORY = {
    "POST_ACTION_VALIDATION_NODE_MISSING": 15,
    "STATE_TRANSITION_LEDGER_FIELD_MISSING": 4,
}


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


def dump(path: Path, obj: dict) -> None:
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()


def sig_from_rem(page: str, rem: dict):
    ds = rem.get("defect_signature") or {}
    return (page, ds.get("category"), str(ds.get("uid")), ds.get("detail"))


def sig_from_r20(rec: dict):
    return (rec.get("page_uid"), rec.get("category"), str(rec.get("target_uid")), rec.get("missing_field_or_relation"))


def closure_for(rec: dict) -> dict:
    category = rec.get("category")
    value = rec.get("candidate_value")
    if value in (None, "", [], {}):
        die(f"EMPTY_R20_CANDIDATE:{rec.get('blocker_uid')}")
    if category == "POST_ACTION_VALIDATION_NODE_MISSING":
        return {
            "closure_type": "POST_ACTION_VALIDATION_FROM_UNIQUE_FROZEN_SUCCESS_SIGNAL",
            "action_uid": rec.get("target_uid"),
            "validation_signal": value,
            "projection_rule": "EXACT_COPY_OF_SINGLE_CANONICAL_R20_FROZEN_CHAIN_SIGNAL",
        }
    if category == "STATE_TRANSITION_LEDGER_FIELD_MISSING":
        if "mutation_owner" not in str(rec.get("missing_field_or_relation") or ""):
            die(f"R20_TRANSITION_AUTO_SCOPE_NOT_MUTATION_OWNER:{rec.get('blocker_uid')}:{rec.get('missing_field_or_relation')}")
        return {
            "closure_type": "TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER",
            "transition_uid": rec.get("target_uid"),
            "mutation_owner": value,
            "projection_rule": "EXACT_COPY_OF_SINGLE_CANONICAL_R20_TRIGGER_RUNTIME_OWNER",
        }
    die(f"UNSUPPORTED_R20_AUTO_CATEGORY:{category}:{rec.get('blocker_uid')}")


r20 = load(R20)
if r20.get("schema_version") != 2:
    die("R20_SCHEMA_VERSION_2_REQUIRED")
den = r20.get("denominators") or {}
if den.get("input_problem_total") != 150 or den.get("auto_remediable_total") != EXPECTED_NEW_TOTAL:
    die(f"R20_DENOMINATOR_DRIFT:{den}")
if den.get("blocker_reduction_claimed") != 0:
    die("R20_PREMATURE_BLOCKER_REDUCTION")
auto = [r for r in (r20.get("records") or []) if r.get("authorized_for_auto_completion") is True]
if len(auto) != EXPECTED_NEW_TOTAL:
    die(f"R20_AUTO_RECORD_COUNT:{len(auto)}")
cat_counts = Counter(r.get("category") for r in auto)
if dict(cat_counts) != EXPECTED_NEW_BY_CATEGORY:
    die(f"R20_AUTO_CATEGORY_DRIFT:{dict(cat_counts)}")

existing = {}
ledgers = {}
old_by_page = Counter()
for page in PAGES:
    path = PRODUCT_ROOT / page / "AUTO_COMPLETION_SCOPE_LEDGER.yaml"
    ledger = load(path)
    if ledger.get("artifact_type") != "AUTO_COMPLETION_SCOPE_LEDGER" or ledger.get("page_uid") != page or ledger.get("stage_uid") != "STAGE-02":
        die(f"LEDGER_IDENTITY_DRIFT:{page}")
    if ledger.get("stage_exit_claimed") is not False:
        die(f"STAGE_EXIT_PREMATURE:{page}")
    rems = ledger.get("remediations") or []
    if not isinstance(rems, list):
        die(f"REMEDIATIONS_LIST_REQUIRED:{page}")
    for rem in rems:
        key = sig_from_rem(page, rem)
        if key in existing:
            die(f"DUPLICATE_EXISTING_SIGNATURE:{key}")
        existing[key] = rem
        old_by_page[page] += 1
    ledgers[page] = (path, ledger)
if len(existing) != EXPECTED_OLD_TOTAL or old_by_page != Counter({"ASSET-01": 12, "CORE-01": 5}):
    die(f"EXISTING_MATERIALIZATION_BASELINE_DRIFT:total={len(existing)} pages={dict(old_by_page)}")

new_by_page = defaultdict(list)
new_keys = set()
for rec in auto:
    page = rec.get("page_uid")
    if page not in PAGES:
        die(f"R20_AUTO_PAGE_DRIFT:{page}")
    if rec.get("disposition") != "AUTO_REMEDIABLE_DETERMINISTIC_MINIMAL_CLOSURE":
        die(f"R20_AUTO_DISPOSITION_DRIFT:{rec.get('blocker_uid')}")
    if rec.get("authority_gap_proven") is not False or rec.get("outside_frozen_closure") is not False:
        die(f"R20_AUTO_BOUNDARY_DRIFT:{rec.get('blocker_uid')}")
    if rec.get("full_stage02_functional_contract_sources_checked") is not True:
        die(f"R20_AUTO_INCOMPLETE_SOURCE_CHECK:{rec.get('blocker_uid')}")
    if rec.get("distinct_candidate_value_count") != 1:
        die(f"R20_AUTO_NOT_UNIQUE:{rec.get('blocker_uid')}")
    evidence = rec.get("candidate_evidence") or []
    if not evidence:
        die(f"R20_AUTO_NO_EVIDENCE:{rec.get('blocker_uid')}")
    canon = {yaml.safe_dump(x.get("value"), allow_unicode=True, sort_keys=True) for x in evidence}
    if len(canon) != 1:
        die(f"R20_AUTO_EVIDENCE_CONFLICT:{rec.get('blocker_uid')}")
    key = sig_from_r20(rec)
    if key in existing:
        die(f"R20_AUTO_OVERLAPS_EXISTING_R3:{key}")
    if key in new_keys:
        die(f"R20_AUTO_DUPLICATE_SIGNATURE:{key}")
    new_keys.add(key)
    scope = rec.get("auto_completion_scope_ledger_entry") or {}
    for field in (
        "outside_frozen_registered_dependency_closure",
        "generic_crud_symmetry_expansion_used",
        "sibling_feature_symmetry_expansion_used",
        "semantic_similarity_used",
        "ai_invented_business_value",
    ):
        if scope.get(field) is not False:
            die(f"R20_SCOPE_GUARD_FAILED:{rec.get('blocker_uid')}:{field}")
    rem = {
        "remediation_uid": f"R21::{page}::{rec.get('blocker_uid')}",
        "source_cycle": "R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY",
        "source_blocker_uid": rec.get("blocker_uid"),
        "defect_signature": {
            "category": rec.get("category"),
            "uid": rec.get("target_uid"),
            "detail": rec.get("missing_field_or_relation"),
        },
        "owning_layer": "STAGE-02_PAGE_FUNCTIONAL_CONTRACT",
        "completion_basis": rec.get("closure_type"),
        "exact_proof": {
            "candidate_value": rec.get("candidate_value"),
            "candidate_evidence": evidence,
            "distinct_candidate_value_count": 1,
            "full_stage02_functional_contract_sources_checked": True,
        },
        "materialized_closure": closure_for(rec),
        "semantic_inference_used": False,
        "ai_invented_business_value": False,
        "external_authority_resolution_performed": False,
        "outside_frozen_registered_dependency_closure": False,
        "generic_crud_symmetry_expansion_used": False,
        "sibling_feature_symmetry_expansion_used": False,
    }
    new_by_page[page].append(rem)

if len(new_keys) != EXPECTED_NEW_TOTAL:
    die(f"NEW_SIGNATURE_DENOMINATOR:{len(new_keys)}")

for page in PAGES:
    path, ledger = ledgers[page]
    rems = list(ledger.get("remediations") or [])
    rems.extend(sorted(new_by_page[page], key=lambda x: x["remediation_uid"]))
    ledger["remediations"] = rems
    ledger["materialized_remediation_count"] = len(rems)
    refs = list(ledger.get("source_classification_refs") or [])
    old_ref = ledger.get("source_classification_ref")
    if old_ref and old_ref not in refs:
        refs.append(old_ref)
    r20_ref = str(R20.relative_to(ROOT))
    if r20_ref not in refs:
        refs.append(r20_ref)
    ledger["source_classification_refs"] = refs
    ledger["latest_bounded_completion_cycle"] = "R21_R20_DETERMINISTIC_MINIMAL_CLOSURE_MATERIALIZATION"
    ledger["stage_exit_claimed"] = False
    dump(path, ledger)

head = git_head()
new_page_counts = {p: len(new_by_page[p]) for p in PAGES}
after_page_counts = {p: old_by_page[p] + len(new_by_page[p]) for p in PAGES}
receipt = {
    "schema_version": 1,
    "artifact_type": "STAGE02_R20_BOUNDED_MATERIALIZATION_R21_RECEIPT",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "cycle": "R21_R20_DETERMINISTIC_MINIMAL_CLOSURE_MATERIALIZATION",
    "source_head_sha": head,
    "source_r20_ref": str(R20.relative_to(ROOT)),
    "owning_layer": "STAGE-02_PAGE_FUNCTIONAL_CONTRACT",
    "before_materialized_product_total": EXPECTED_OLD_TOTAL,
    "materialized_now_total": EXPECTED_NEW_TOTAL,
    "after_materialized_product_total": EXPECTED_AFTER_TOTAL,
    "materialized_now_by_page": new_page_counts,
    "after_materialized_by_page": after_page_counts,
    "materialized_now_by_category": dict(cat_counts),
    "materialized_signatures": [list(x) for x in sorted(new_keys)],
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "external_authority_resolution_performed": False,
    "semantic_inference_used": False,
    "ai_invented_business_value": False,
    "blocker_reduction_claimed_before_reexecution": 0,
    "expected_effective_remaining_only_if_fresh_r21_reexecution_accepts_all_19": 131,
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}
dump(RECEIPT, receipt)
print(f"PASS: preserved existing materializations={EXPECTED_OLD_TOTAL}")
print(f"PASS: appended R20 deterministic materializations={EXPECTED_NEW_TOTAL}")
print(f"PASS: product materialization total now={EXPECTED_AFTER_TOTAL}")
print(f"PASS: new by page={new_page_counts}")
print(f"PASS: new by category={dict(cat_counts)}")
print("PASS: no blocker reduction claimed before fresh R21 reexecution")
