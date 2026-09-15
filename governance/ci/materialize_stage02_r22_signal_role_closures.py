#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOT = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT"
R22 = ROOT / "governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_ROLE_RECLASSIFICATION_R22.yaml"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R22_BOUNDED_MATERIALIZATION_RECEIPT.yaml"
PAGES = ("CORE-01", "ASSET-01")


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


def dump(path, obj):
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")


def sig(page, rem):
    ds = rem.get("defect_signature") or {}
    return (page, ds.get("category"), str(ds.get("uid")), ds.get("detail"))


r22 = load(R22)
auto = [r for r in (r22.get("records") or []) if r.get("authorized_for_auto_completion") is True]
if len(auto) != 2:
    die(f"R22_AUTO_DENOMINATOR:{len(auto)}")
if {r.get("target_uid") for r in auto} != {"ASSET-01-ACT-FLOW-START", "ASSET-01-ACT-CANDIDATE-CONFIRM"}:
    die("R22_AUTO_TARGET_DRIFT")

existing = {}
ledgers = {}
by_page = Counter()
for page in PAGES:
    path = PRODUCT_ROOT / page / "AUTO_COMPLETION_SCOPE_LEDGER.yaml"
    ledger = load(path)
    if ledger.get("artifact_type") != "AUTO_COMPLETION_SCOPE_LEDGER" or ledger.get("page_uid") != page or ledger.get("stage_uid") != "STAGE-02":
        die(f"LEDGER_IDENTITY:{page}")
    rems = ledger.get("remediations") or []
    if ledger.get("materialized_remediation_count") != len(rems):
        die(f"LEDGER_COUNT_DRIFT:{page}")
    for rem in rems:
        key = sig(page, rem)
        if key in existing:
            die(f"DUPLICATE_EXISTING:{key}")
        existing[key] = rem
        by_page[page] += 1
    ledgers[page] = (path, ledger)
if len(existing) != 36 or by_page != Counter({"ASSET-01": 31, "CORE-01": 5}):
    die(f"R21_BASELINE_DRIFT:total={len(existing)} pages={dict(by_page)}")

new = []
for rec in auto:
    key = (rec.get("page_uid"), rec.get("category"), str(rec.get("target_uid")), rec.get("missing_field_or_relation"))
    if key in existing:
        die(f"R22_OVERLAP:{key}")
    evidence = rec.get("admissible_validation_evidence") or []
    values = {yaml.safe_dump(x.get("value"), allow_unicode=True, sort_keys=True) for x in evidence}
    if len(values) != 1 or rec.get("admissible_candidate_value_count") != 1:
        die(f"R22_NOT_UNIQUE:{key}")
    if rec.get("semantic_similarity_used") is not False or rec.get("ai_invented_business_value") is not False or rec.get("outside_frozen_registered_dependency_closure") is not False:
        die(f"R22_SAFETY_DRIFT:{key}")
    rem = {
        "remediation_uid": f"R22::{rec.get('page_uid')}::{rec.get('blocker_uid')}",
        "source_cycle": "R22_POST_ACTION_SIGNAL_ROLE_CORRECTION",
        "source_blocker_uid": rec.get("blocker_uid"),
        "defect_signature": {"category": rec.get("category"), "uid": rec.get("target_uid"), "detail": rec.get("missing_field_or_relation")},
        "owning_layer": "STAGE-02_PAGE_FUNCTIONAL_CONTRACT",
        "completion_basis": rec.get("closure_type"),
        "exact_proof": {
            "candidate_value": rec.get("candidate_value"),
            "admissible_validation_evidence": evidence,
            "excluded_non_validation_role_evidence": rec.get("excluded_non_validation_role_evidence") or [],
            "admissible_candidate_value_count": 1,
            "signal_role_correction_applied": True,
        },
        "materialized_closure": {
            "closure_type": "POST_ACTION_VALIDATION_FROM_ROLE_CORRECT_UNIQUE_FROZEN_RESULT_SIGNAL",
            "action_uid": rec.get("target_uid"),
            "validation_signal": rec.get("candidate_value"),
            "projection_rule": "EXACT_COPY_AFTER_EXCLUDING_FLOW_TRANSITION_DESTINATION_FROM_VALIDATION_ROLE",
        },
        "semantic_inference_used": False,
        "ai_invented_business_value": False,
        "external_authority_resolution_performed": False,
        "outside_frozen_registered_dependency_closure": False,
        "generic_crud_symmetry_expansion_used": False,
        "sibling_feature_symmetry_expansion_used": False,
    }
    new.append((key, rem))

if len(new) != 2:
    die("R22_NEW_DENOMINATOR_NOT_2")
asset_path, asset = ledgers["ASSET-01"]
asset["remediations"] = list(asset.get("remediations") or []) + [rem for _, rem in sorted(new)]
asset["materialized_remediation_count"] = len(asset["remediations"])
refs = list(asset.get("source_classification_refs") or [])
r22ref = str(R22.relative_to(ROOT))
if r22ref not in refs:
    refs.append(r22ref)
asset["source_classification_refs"] = refs
asset["latest_bounded_completion_cycle"] = "R22_POST_ACTION_SIGNAL_ROLE_CORRECTION"
asset["stage_exit_claimed"] = False
dump(asset_path, asset)
if asset["materialized_remediation_count"] != 33:
    die(f"ASSET_AFTER_NOT_33:{asset['materialized_remediation_count']}")

head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
receipt = {
    "schema_version": 1,
    "artifact_type": "STAGE02_R22_BOUNDED_MATERIALIZATION_RECEIPT",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "source_head_sha": head,
    "source_r22_ref": r22ref,
    "before_materialized_product_total": 36,
    "materialized_now_total": 2,
    "after_materialized_product_total": 38,
    "after_materialized_by_page": {"CORE-01": 5, "ASSET-01": 33},
    "materialized_targets": [key[2] for key, _ in sorted(new)],
    "remaining_r22_authority_gap_targets": [r.get("target_uid") for r in (r22.get("records") or []) if r.get("authority_gap_proven") is True],
    "blocker_reduction_claimed_before_reexecution": 0,
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "semantic_inference_used": False,
    "ai_invented_business_value": False,
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}
dump(RECEIPT, receipt)
print("PASS: preserved prior product materializations=36")
print("PASS: appended exact R22 signal-role materializations=2")
print("PASS: product materialization total now=38 (CORE=5 ASSET=33)")
print("PASS: CORRECTION-EXECUTE remains unmaterialized authority gap")
print("PASS: blocker reduction remains unclaimed before fresh reexecution")
