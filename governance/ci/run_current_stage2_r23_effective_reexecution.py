#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R22_RUNNER = ROOT / "governance/ci/run_current_stage2_r22_effective_reexecution.py"
R22_RESULT = ROOT / ".github/stage02-test/STAGE02_R22_EFFECTIVE_REEXECUTION_RESULT.json"
R23_RESULT = ROOT / ".github/stage02-test/STAGE02_R23_EFFECTIVE_REEXECUTION_RESULT.json"
LATEST = ROOT / "governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json"
FINDINGS = ROOT / "governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R23_BOUNDED_MATERIALIZATION_RECEIPT.yaml"
CLASSIFIER = ROOT / "governance/test/stage02/STAGE02_CURRENT_AUTHORITY_PAYLOAD_CLOSURE_R23.yaml"


def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def load_json(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        die(f"JSON_MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()


if os.environ.get("STAGE02_FULL_LINE_CONFIRMED") != "1":
    die("R23_REEXECUTION_REQUIRES_FULL_LINE_CONFIRMATION")
for validator in (
    ROOT / "governance/ci/validate_stage02_current_authority_payload_closures_r23.py",
    ROOT / "governance/ci/validate_stage02_r23_materialized_payload_closures.py",
    ROOT / "governance/ci/validate_current_stage2_external_authority_resolution_r3.py",
):
    cp = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die(f"PRE_REEXECUTION_VALIDATOR_FAILED:{validator.name}")

receipt = load_yaml(RECEIPT)
classifier = load_yaml(CLASSIFIER)
r23_count = receipt.get("materialized_now_total")
if r23_count != 0:
    die(f"R23_ZERO_INTERSECTION_REEXECUTION_EXPECTED_0:{r23_count}")
if receipt.get("before_materialized_product_total") != 38 or receipt.get("after_materialized_product_total") != 38:
    die("R23_ZERO_RECEIPT_PRODUCT_DENOMINATOR_DRIFT")
if receipt.get("zero_closure_preserves_existing_ledger_bytes") is not True:
    die("R23_ZERO_LEDGER_PRESERVATION_NOT_PROVEN")
if (classifier.get("denominators") or {}).get("auto_remediable_current_authority_payload_total") != 0:
    die("R23_CLASSIFIER_ZERO_INTERSECTION_DRIFT")
if (classifier.get("denominators") or {}).get("unresolved_no_exact_current_payload_total") != 34:
    die("R23_CLASSIFIER_UNRESOLVED_PAYLOAD_DRIFT")

# This is a real fresh replay, not reuse of a prior result. R22 runner re-extracts the
# first-run fresh_scan implementation and scans the immutable Raw sources again.
cp = subprocess.run([sys.executable, str(R22_RUNNER)], cwd=str(ROOT), text=True)
if cp.returncode != 0:
    die("R23_ZERO_CLOSURE_PARENT_FRESH_REEXECUTION_FAILED")
base = load_json(R22_RESULT)
if base.get("raw_discovery_gap_total") != 171:
    die(f"R23_RAW_DENOMINATOR_DRIFT:{base.get('raw_discovery_gap_total')}")
if base.get("product_materialization_elimination_count") != 38 or base.get("gap006_authority_elimination_count") != 4:
    die("R23_ZERO_CLOSURE_PARENT_ELIMINATION_DRIFT")
if base.get("fresh_functional_gap_total") != 129:
    die(f"R23_ZERO_CLOSURE_EFFECTIVE_DRIFT:{base.get('fresh_functional_gap_total')}")
expected_categories = {
    "ACTION_WITHOUT_CONTROL_OR_TRIGGER": 1,
    "AUDIT_EVENT_NODE_MISSING": 13,
    "FAILURE_STATE_ERROR_BINDING_MISSING": 44,
    "PAYLOAD_INPUT_CONTRACT_MISSING": 34,
    "POST_ACTION_VALIDATION_NODE_MISSING": 1,
    "STATE_TRANSITION_LEDGER_FIELD_MISSING": 36,
}
if base.get("effective_gap_categories") != expected_categories:
    die(f"R23_ZERO_CLOSURE_CATEGORY_DRIFT:{base.get('effective_gap_categories')}")

result = copy.deepcopy(base)
result["schema_version"] = 6
result["reexecution_cycle"] = "R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD_ZERO_INTERSECTION"
result["source_head_sha"] = head()
result["r23_current_authority_payload_elimination_count"] = 0
result["r23_current_authority_payload_exact_intersection_total"] = 0
result["remaining_payload_gap_total"] = 34
result["remaining_payload_targets"] = sorted(
    str(gap.get("uid"))
    for page in (result.get("pages") or {}).values()
    for gap in ((page.get("functional_chain_effective_r22_scan") or {}).get("gaps") or [])
    if gap.get("category") == "PAYLOAD_INPUT_CONTRACT_MISSING"
)
result["operation_registry_used_as_payload_authority"] = False
result["prior_stage2_results_used_as_scan_input"] = False
result["current_specification_mutated"] = False
result["immutable_stage1_source_mutated"] = False
result["website_construction_allowed"] = False
result["deployment_allowed"] = False
result["notes"] = [
    "R23 classifier evaluated all 34 currently effective payload gaps against manifest-listed Current Shared Runtime Authority.",
    "Exact page/action/operation/method/path intersection with explicit required_payload was zero; no payload closure was invented or materialized.",
    "A real fresh Raw Stage-02 scan was executed through the exact R22 first-run scanner path after proving the product ledger stayed at 38.",
    "Fresh Raw discovery remained 171; validated product eliminations remained 38; GAP-006 authority eliminations remained 4; effective gaps remained 129.",
    "ASSET-01-ACT-CORRECTION-EXECUTE remains the one proven post-action multiple-signal Product Authority gap.",
    "Stage-02 remains blocked; Stage-03, website construction, and deployment remain prohibited.",
]
for page in (result.get("pages") or {}).values():
    if "functional_chain_effective_r22_scan" in page:
        page["functional_chain_effective_r23_scan"] = page.pop("functional_chain_effective_r22_scan")

R23_RESULT.parent.mkdir(parents=True, exist_ok=True)
text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
R23_RESULT.write_text(text, encoding="utf-8")
LATEST.write_text(text, encoding="utf-8")
FINDINGS.write_text(yaml.safe_dump({
    "schema_version": 6,
    "artifact_type": "STAGE02_CURRENT_FINDINGS",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "source_cycle": "R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD_ZERO_INTERSECTION",
    "source_head_sha": result["source_head_sha"],
    "raw_discovery_gap_total": 171,
    "validated_product_materialization_elimination_count": 38,
    "validated_r23_current_authority_payload_elimination_count": 0,
    "validated_external_authority_elimination_count": 4,
    "fresh_functional_gap_total": 129,
    "effective_gap_categories": expected_categories,
    "remaining_payload_gap_total": 34,
    "remaining_true_authority_gap_count": 1,
    "remaining_true_authority_gap_targets": ["ASSET-01-ACT-CORRECTION-EXECUTE"],
    "result": "BLOCKED",
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print("PASS: R23 exact Current Authority payload intersection=0")
print("PASS: fresh raw Stage-02 scan=171; product eliminations=38; GAP-006 eliminations=4")
print("PASS: fresh effective Stage-02 functional gaps remain=129; payload gaps remain=34")
print("BLOCKED: residual functional gaps remain; Stage-02 / construction / deployment stay fail-closed")
