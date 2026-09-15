#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOT = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT"
R23 = ROOT / "governance/test/stage02/STAGE02_CURRENT_AUTHORITY_PAYLOAD_CLOSURE_R23.yaml"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R23_BOUNDED_MATERIALIZATION_RECEIPT.yaml"
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


r23 = load(R23)
auto = [r for r in (r23.get("records") or []) if r.get("authorized_for_auto_completion") is True]
expected_auto = (r23.get("denominators") or {}).get("auto_remediable_current_authority_payload_total")
if len(auto) != expected_auto or not isinstance(expected_auto, int) or expected_auto < 0 or expected_auto > 4:
    die(f"R23_AUTO_DENOMINATOR:{len(auto)}:{expected_auto}")
if any(r.get("page_uid") != "ASSET-01" or r.get("category") != "PAYLOAD_INPUT_CONTRACT_MISSING" for r in auto):
    die("R23_AUTO_SCOPE_OR_CATEGORY_DRIFT")

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
if len(existing) != 38 or by_page != Counter({"ASSET-01": 33, "CORE-01": 5}):
    die(f"R22_BASELINE_DRIFT:total={len(existing)} pages={dict(by_page)}")

new = []
for rec in auto:
    key = (rec.get("page_uid"), rec.get("category"), str(rec.get("target_uid")), rec.get("gap_detail"))
    if key in existing:
        die(f"R23_OVERLAP:{key}")
    evidence = rec.get("candidate_evidence") or []
    if len(evidence) != 1:
        die(f"R23_NOT_UNIQUE:{key}:{len(evidence)}")
    ev = evidence[0]
    required_fields = ev.get("required_payload")
    value = rec.get("candidate_value") or {}
    if not isinstance(required_fields, list) or not required_fields or required_fields != value.get("required_fields"):
        die(f"R23_REQUIRED_FIELDS_DRIFT:{key}")
    if rec.get("semantic_inference_used") is not False or rec.get("ai_invented_business_value") is not False or rec.get("outside_frozen_registered_dependency_closure") is not False:
        die(f"R23_SAFETY_DRIFT:{key}")
    rem = {
        "remediation_uid": f"R23::{rec.get('page_uid')}::{rec.get('blocker_uid')}",
        "source_cycle": "R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD",
        "source_blocker_uid": rec.get("blocker_uid"),
        "defect_signature": {"category": rec.get("category"), "uid": rec.get("target_uid"), "detail": rec.get("gap_detail")},
        "owning_layer": "STAGE-02_PAGE_FUNCTIONAL_CONTRACT",
        "completion_basis": "CURRENT_MANIFEST_LISTED_RUNTIME_AUTHORITY_REQUIRED_PAYLOAD_EXACT_PROJECTION",
        "exact_proof": {
            "source_authority_id": ev.get("authority_id"),
            "source_authority_version": ev.get("authority_version"),
            "source_path": ev.get("source_path"),
            "operation_id": ev.get("operation_id"),
            "page_uid": ev.get("page_uid"),
            "action_uid": ev.get("action_uid"),
            "control_uid": ev.get("control_uid"),
            "method": ev.get("method"),
            "route": ev.get("route"),
            "required_payload": list(required_fields),
            "identity_proof": ev.get("identity_proof") or [],
            "operation_registry_used_as_payload_authority": False,
        },
        "materialized_closure": {
            "closure_type": "REQUEST_INPUT_CONTRACT_FROM_CURRENT_SHARED_RUNTIME_REQUIRED_PAYLOAD",
            "action_uid": rec.get("target_uid"),
            "operation_id": ev.get("operation_id"),
            "method": ev.get("method"),
            "route": ev.get("route"),
            "payload_contract": {"required_fields": list(required_fields)},
            "projection_rule": "EXACT_COPY_OF_CURRENT_AUTHORITY_REQUIRED_PAYLOAD_NO_FIELD_INFERENCE",
        },
        "semantic_inference_used": False,
        "ai_invented_business_value": False,
        "current_external_authority_evidence_used": True,
        "external_authority_resolution_performed": False,
        "outside_frozen_registered_dependency_closure": False,
        "generic_crud_symmetry_expansion_used": False,
        "sibling_feature_symmetry_expansion_used": False,
    }
    new.append((key, rem))

if len(new) != expected_auto:
    die("R23_NEW_DENOMINATOR_DRIFT")
asset_path, asset = ledgers["ASSET-01"]
r23ref = str(R23.relative_to(ROOT))
if new:
    asset["remediations"] = list(asset.get("remediations") or []) + [rem for _, rem in sorted(new)]
    asset["materialized_remediation_count"] = len(asset["remediations"])
    refs = list(asset.get("source_classification_refs") or [])
    if r23ref not in refs:
        refs.append(r23ref)
    asset["source_classification_refs"] = refs
    asset["latest_bounded_completion_cycle"] = "R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD"
    asset["stage_exit_claimed"] = False
    dump(asset_path, asset)
else:
    if asset.get("materialized_remediation_count") != 33:
        die(f"R23_ZERO_CLOSURE_LEDGER_BASELINE_DRIFT:{asset.get('materialized_remediation_count')}")
expected_after_asset = 33 + expected_auto
if (asset.get("materialized_remediation_count") or 0) != expected_after_asset:
    die(f"ASSET_AFTER_COUNT_DRIFT:{asset.get('materialized_remediation_count')}:{expected_after_asset}")

head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
receipt = {
    "schema_version": 2,
    "artifact_type": "STAGE02_R23_BOUNDED_MATERIALIZATION_RECEIPT",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "source_head_sha": head,
    "source_r23_ref": r23ref,
    "before_materialized_product_total": 38,
    "materialized_now_total": expected_auto,
    "after_materialized_product_total": 38 + expected_auto,
    "after_materialized_by_page": {"CORE-01": 5, "ASSET-01": expected_after_asset},
    "materialized_targets": [key[2] for key, _ in sorted(new)],
    "materialized_category": "PAYLOAD_INPUT_CONTRACT_MISSING",
    "source_authority": "ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY@1.0",
    "zero_closure_preserves_existing_ledger_bytes": expected_auto == 0,
    "blocker_reduction_claimed_before_reexecution": 0,
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "semantic_inference_used": False,
    "ai_invented_business_value": False,
    "operation_registry_used_as_payload_authority": False,
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}
dump(RECEIPT, receipt)
print("PASS: preserved prior product materializations=38")
print(f"PASS: appended exact R23 Current Authority payload materializations={expected_auto}")
print(f"PASS: product materialization total now={38 + expected_auto} (CORE=5 ASSET={expected_after_asset})")
if expected_auto == 0:
    print("PASS: zero exact intersection; ASSET ledger intentionally not mutated")
print("PASS: blocker reduction remains unclaimed before fresh reexecution")
