#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOT = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT"
R23 = ROOT / "governance/test/stage02/STAGE02_CURRENT_AUTHORITY_PAYLOAD_CLOSURE_R23.yaml"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R23_BOUNDED_MATERIALIZATION_RECEIPT.yaml"


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


r23 = load(R23)
receipt = load(RECEIPT)
auto = [r for r in (r23.get("records") or []) if r.get("authorized_for_auto_completion") is True]
expected = len(auto)
if expected < 1 or expected > 4:
    die(f"R23_AUTO_DENOMINATOR_INVALID:{expected}")
if receipt.get("artifact_type") != "STAGE02_R23_BOUNDED_MATERIALIZATION_RECEIPT" or receipt.get("materialized_now_total") != expected:
    die("R23_RECEIPT_IDENTITY_OR_COUNT_DRIFT")
if receipt.get("before_materialized_product_total") != 38 or receipt.get("after_materialized_product_total") != 38 + expected:
    die("R23_RECEIPT_TOTAL_ARITHMETIC_DRIFT")
if receipt.get("blocker_reduction_claimed_before_reexecution") != 0:
    die("R23_PREMATURE_BLOCKER_REDUCTION")
if receipt.get("current_specification_mutated") is not False or receipt.get("immutable_stage1_source_mutated") is not False:
    die("R23_RECEIPT_MUTATION_FLAG_DRIFT")
if receipt.get("semantic_inference_used") is not False or receipt.get("ai_invented_business_value") is not False or receipt.get("operation_registry_used_as_payload_authority") is not False:
    die("R23_RECEIPT_SAFETY_FLAG_DRIFT")

all_rems = {}
by_page = Counter()
cycle = Counter()
for page in ("CORE-01", "ASSET-01"):
    ledger = load(PRODUCT_ROOT / page / "AUTO_COMPLETION_SCOPE_LEDGER.yaml")
    rems = ledger.get("remediations") or []
    if ledger.get("materialized_remediation_count") != len(rems):
        die(f"R23_LEDGER_COUNT_DRIFT:{page}")
    by_page[page] = len(rems)
    for rem in rems:
        ds = rem.get("defect_signature") or {}
        sig = (page, ds.get("category"), str(ds.get("uid")), ds.get("detail"))
        if sig in all_rems:
            die(f"R23_DUPLICATE_LEDGER_SIGNATURE:{sig}")
        all_rems[sig] = rem
        cycle[str(rem.get("source_cycle") or "R3_BOUNDED_FUNCTIONAL_COMPLETION")] += 1

if len(all_rems) != 38 + expected or by_page != Counter({"CORE-01": 5, "ASSET-01": 33 + expected}):
    die(f"R23_LEDGER_DENOMINATOR_DRIFT:total={len(all_rems)} by_page={dict(by_page)} expected={expected}")
if cycle.get("R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD") != expected:
    die(f"R23_CYCLE_COUNT_DRIFT:{dict(cycle)}")

expected_targets = set()
for row in auto:
    sig = (row.get("page_uid"), row.get("category"), str(row.get("target_uid")), row.get("gap_detail"))
    rem = all_rems.get(sig)
    if not rem:
        die(f"R23_MATERIALIZED_SIGNATURE_MISSING:{sig}")
    expected_targets.add(row.get("target_uid"))
    if rem.get("source_cycle") != "R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD" or rem.get("source_blocker_uid") != row.get("blocker_uid"):
        die(f"R23_MATERIALIZED_LINEAGE_DRIFT:{sig}")
    proof = rem.get("exact_proof") or {}
    closure = rem.get("materialized_closure") or {}
    ev = (row.get("candidate_evidence") or [None])[0]
    if not isinstance(ev, dict):
        die(f"R23_SOURCE_EVIDENCE_MISSING:{sig}")
    if proof.get("source_authority_id") != ev.get("authority_id") or proof.get("operation_id") != ev.get("operation_id") or proof.get("required_payload") != ev.get("required_payload"):
        die(f"R23_EXACT_PROOF_DRIFT:{sig}")
    if closure.get("closure_type") != "REQUEST_INPUT_CONTRACT_FROM_CURRENT_SHARED_RUNTIME_REQUIRED_PAYLOAD":
        die(f"R23_CLOSURE_TYPE_DRIFT:{sig}")
    payload = closure.get("payload_contract") or {}
    if payload.get("required_fields") != ev.get("required_payload"):
        die(f"R23_PAYLOAD_CONTRACT_DRIFT:{sig}")
    if closure.get("projection_rule") != "EXACT_COPY_OF_CURRENT_AUTHORITY_REQUIRED_PAYLOAD_NO_FIELD_INFERENCE":
        die(f"R23_PROJECTION_RULE_DRIFT:{sig}")
    if rem.get("semantic_inference_used") is not False or rem.get("ai_invented_business_value") is not False or rem.get("outside_frozen_registered_dependency_closure") is not False:
        die(f"R23_MATERIALIZATION_SAFETY_DRIFT:{sig}")
    if rem.get("current_external_authority_evidence_used") is not True or rem.get("external_authority_resolution_performed") is not False:
        die(f"R23_EXTERNAL_AUTHORITY_USAGE_FLAG_DRIFT:{sig}")

if set(receipt.get("materialized_targets") or []) != expected_targets:
    die("R23_RECEIPT_TARGET_SET_DRIFT")
print(f"PASS: R23 materialized payload closures={expected}; total product materializations={38+expected}")
print(f"PASS: ledger by page CORE=5 ASSET={33+expected}")
print("PASS: every R23 closure preserves exact Current Authority required_payload without field inference")
