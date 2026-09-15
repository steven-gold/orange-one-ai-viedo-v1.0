#!/usr/bin/env python3
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
PRODUCT_ROOT = RUN / "04_PAGE_FUNCTIONAL_CONTRACT"
SCANNER_SOURCE = ROOT / "governance/ci/run_current_stage2_actual_test.py"
R20_VALIDATOR = ROOT / "governance/ci/validate_stage02_functional_chain_auto_remediability_r20.py"
R21_VALIDATOR = ROOT / "governance/ci/validate_stage02_r20_materialized_closures_r21.py"
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"
FREEZE = ROOT / "governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml"
LATEST = ROOT / "governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json"
FINDINGS = ROOT / "governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml"
RESULT = ROOT / ".github/stage02-test/STAGE02_R20_EFFECTIVE_REEXECUTION_RESULT_R21.json"
GAP006_MAP = PRODUCT_ROOT / "SHARED_OWNER_PORT_MAP_R3.yaml"
PAGES = {
    "CORE-01": {
        "raw": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
        "blueprint": RUN / "02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml",
        "ledger": PRODUCT_ROOT / "CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml",
        "ai_profile": True,
    },
    "ASSET-01": {
        "raw": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
        "blueprint": RUN / "02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml",
        "ledger": PRODUCT_ROOT / "ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml",
        "ai_profile": False,
    },
}
EXPECTED_GAPS = {f"GAP-{i:03}" for i in range(1, 9)}
GAP006_DETAIL = "GAP-006: ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY"
EXPECTED_EFFECTIVE_CATEGORIES = {
    "ACTION_WITHOUT_CONTROL_OR_TRIGGER": 1,
    "AUDIT_EVENT_NODE_MISSING": 13,
    "FAILURE_STATE_ERROR_BINDING_MISSING": 44,
    "PAYLOAD_INPUT_CONTRACT_MISSING": 34,
    "POST_ACTION_VALIDATION_NODE_MISSING": 3,
    "STATE_TRANSITION_LEDGER_FIELD_MISSING": 36,
}


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()


def load_exact_fresh_scan_implementation():
    source = SCANNER_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SCANNER_SOURCE))
    keep_functions = {"idx", "present", "event_token", "has_transition", "add", "fresh_scan"}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if "KNOWN_AUTHORITIES" in names:
                selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in keep_functions:
            selected.append(node)
    found = {node.name for node in selected if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if found != keep_functions:
        die(f"FRESH_SCAN_IMPLEMENTATION_EXTRACTION_DRIFT:expected={sorted(keep_functions)} actual={sorted(found)}")
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {"Counter": Counter, "defaultdict": defaultdict, "re": re}
    exec(compile(module, str(SCANNER_SOURCE), "exec"), ns, ns)
    if not callable(ns.get("fresh_scan")):
        die("FRESH_SCAN_IMPLEMENTATION_NOT_CALLABLE")
    return ns["fresh_scan"]


def signature(page_uid: str, gap: dict):
    return (page_uid, gap.get("category"), str(gap.get("uid")), gap.get("detail"))


def exact_external_refs(blueprint: dict):
    refs = []
    for ref in blueprint.get("unresolved_external_authority_refs") or []:
        if isinstance(ref, dict):
            refs.append({"gap_uid": ref.get("gap_uid"), "authority_ref": ref.get("authority_ref")})
    return refs


def load_product_signatures():
    materialized = {}
    by_page = Counter()
    r21 = 0
    for page_uid, cfg in PAGES.items():
        ledger = load_yaml(cfg["ledger"])
        if ledger.get("artifact_type") != "AUTO_COMPLETION_SCOPE_LEDGER" or ledger.get("page_uid") != page_uid:
            die(f"WRONG_AUTO_COMPLETION_LEDGER:{page_uid}")
        for rem in ledger.get("remediations") or []:
            ds = rem.get("defect_signature") or {}
            key = (page_uid, ds.get("category"), str(ds.get("uid")), ds.get("detail"))
            if key in materialized:
                die(f"DUPLICATE_PRODUCT_SIGNATURE:{key}")
            materialized[key] = rem
            by_page[page_uid] += 1
            if rem.get("source_cycle") == "R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY":
                r21 += 1
    if len(materialized) != 36 or sum(by_page.values()) != 36 or r21 != 19:
        die(f"PRODUCT_SIGNATURE_DENOMINATOR_DRIFT:total={len(materialized)} pages={dict(by_page)} r21={r21}")
    return materialized, by_page


def load_gap006_signatures():
    doc = load_yaml(GAP006_MAP)
    if doc.get("artifact_uid") != "FRESH-RUN-003-STAGE2-SHARED-OWNER-PORT-MAP-R3" or doc.get("status") != "RESOLVED_AUTHORITY_GAP_CURRENT_SUCCESSOR":
        die("GAP006_R3_MAP_IDENTITY_DRIFT")
    consumers = doc.get("consumers") or []
    if len(consumers) != 4:
        die(f"GAP006_CONSUMER_DENOMINATOR_DRIFT:{len(consumers)}")
    materialized = {}
    for row in consumers:
        if row.get("page_uid") != "ASSET-01" or row.get("status") != "RESOLVED_EXACT_AUTHORITY" or row.get("binding_kind") != "SHARED_OPERATION_REFERENCE" or row.get("resolved_port_uid") is not None or row.get("port_uid_status") != "NOT_APPLICABLE_BY_BINDING_KIND":
            die(f"GAP006_CONSUMER_NOT_EXACT:{row.get('action_uid')}")
        key = ("ASSET-01", "SHARED_OWNER_AUTHORITY_UNRESOLVED", str(row.get("action_uid")), GAP006_DETAIL)
        if key in materialized:
            die(f"DUPLICATE_GAP006_SIGNATURE:{key}")
        materialized[key] = row
    return materialized


def effective_scan(page_uid: str, raw_scan: dict, product: dict, gap006: dict):
    raw_gaps = raw_scan.get("gaps") or []
    raw_keys = [signature(page_uid, g) for g in raw_gaps]
    if len(raw_keys) != len(set(raw_keys)):
        die(f"RAW_GAP_SIGNATURE_DUPLICATE:{page_uid}")
    remaining, product_eliminated, authority_eliminated = [], [], []
    for gap in raw_gaps:
        key = signature(page_uid, gap)
        if key in product and key in gap006:
            die(f"OVERLAPPING_REMEDIATION_SIGNATURE:{key}")
        if key in product:
            rem = product[key]
            product_eliminated.append({
                "raw_gap": gap,
                "remediation_uid": rem.get("remediation_uid"),
                "source_cycle": rem.get("source_cycle", "R3_BOUNDED_FUNCTIONAL_COMPLETION"),
                "owning_layer": rem.get("owning_layer"),
                "materialized_closure": rem.get("materialized_closure"),
                "effective_reproduction": False,
            })
        elif key in gap006:
            authority_eliminated.append({
                "raw_gap": gap,
                "authority_gap_uid": "GAP-006",
                "resolution": "RESOLVED_EXACT_AUTHORITY",
                "binding_kind": "SHARED_OPERATION_REFERENCE",
                "effective_reproduction": False,
            })
        else:
            remaining.append(gap)
    return {
        "gap_count": len(remaining),
        "gap_categories": dict(sorted(Counter(g.get("category") for g in remaining).items())),
        "gap_classes": dict(sorted(Counter(g.get("class") for g in remaining).items())),
        "gaps": remaining,
        "product_materialization_elimination_count": len(product_eliminated),
        "product_materialization_eliminations": product_eliminated,
        "gap006_authority_elimination_count": len(authority_eliminated),
        "gap006_authority_eliminations": authority_eliminated,
        "total_elimination_count": len(product_eliminated) + len(authority_eliminated),
    }


if os.environ.get("STAGE02_FULL_LINE_CONFIRMED") != "1":
    die("R21_REEXECUTION_REQUIRES_SAME_WORKFLOW_FULL_LINE_CONFIRMATION")
state = load_yaml(STATE)
freeze = load_yaml(FREEZE)
execution = state.get("execution") or {}
if execution.get("current_stage") != "STAGE-02-TESTED-BLOCKED" or (execution.get("stage2") or {}).get("result") != "TEST_EXECUTED_BLOCKED":
    die("R21_REEXECUTION_REQUIRES_CURRENT_STAGE02_BLOCKED_STATE")
if not freeze.get("frozen_governance_uid") or freeze.get("stage_uid") != "STAGE-02":
    die("R21_FROZEN_GOVERNANCE_RECEIPT_INVALID")
for validator in (R20_VALIDATOR, R21_VALIDATOR):
    cp = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die(f"R21_PRE_EXECUTION_VALIDATOR_FAILED:{validator.name}")

fresh_scan = load_exact_fresh_scan_implementation()
product, product_by_page = load_product_signatures()
gap006 = load_gap006_signatures()
if set(product) & set(gap006):
    die("PRODUCT_AND_GAP006_SIGNATURE_SETS_OVERLAP")

head = git_head()
pages = {}
source_external = {}
union_gap_uids = set()
raw_total = 0
product_eliminated_total = 0
gap006_eliminated_total = 0
effective_total = 0
matched_product = set()
matched_gap006 = set()

for page_uid, cfg in PAGES.items():
    raw = load_yaml(cfg["raw"])
    blueprint = load_yaml(cfg["blueprint"])
    refs = exact_external_refs(blueprint)
    for ref in refs:
        gid = ref.get("gap_uid")
        union_gap_uids.add(gid)
        rec = source_external.setdefault(gid, {"authority_ref": ref.get("authority_ref"), "consumers": [], "source_reference_preserved": True})
        rec["consumers"].append(page_uid)
    raw_scan = fresh_scan(page_uid, raw)
    eff = effective_scan(page_uid, raw_scan, product, gap006)
    raw_total += int(raw_scan.get("gap_count") or 0)
    product_eliminated_total += eff["product_materialization_elimination_count"]
    gap006_eliminated_total += eff["gap006_authority_elimination_count"]
    effective_total += eff["gap_count"]
    for item in eff["product_materialization_eliminations"]:
        matched_product.add(signature(page_uid, item["raw_gap"]))
    for item in eff["gap006_authority_eliminations"]:
        matched_gap006.add(signature(page_uid, item["raw_gap"]))
    pages[page_uid] = {
        "blueprint_uid": blueprint.get("blueprint_uid"),
        "ai_interaction_profile_active": cfg["ai_profile"],
        "source_external_authority_ref_count": len(refs),
        "functional_chain_fresh_scan": raw_scan,
        "functional_chain_raw_fresh_scan": raw_scan,
        "functional_chain_effective_r21_scan": eff,
        "closure_blockers": [],
        "closure_blocker_count": 0,
        "materialized_product_functional_contract_validation": "PASS",
        "gap006_external_authority_validation": "PASS",
    }

if raw_total != 171:
    die(f"RAW_DISCOVERY_DENOMINATOR_DRIFT:{raw_total}")
if matched_product != set(product):
    die(f"PRODUCT_SIGNATURE_RAW_MATCH_DRIFT:missing={sorted(set(product)-matched_product)} extra={sorted(matched_product-set(product))}")
if matched_gap006 != set(gap006):
    die(f"GAP006_SIGNATURE_RAW_MATCH_DRIFT:missing={sorted(set(gap006)-matched_gap006)} extra={sorted(matched_gap006-set(gap006))}")
if product_eliminated_total != 36 or gap006_eliminated_total != 4:
    die(f"R21_ELIMINATION_DENOMINATOR_DRIFT:product={product_eliminated_total}:gap006={gap006_eliminated_total}")
if effective_total != 131 or effective_total != raw_total - product_eliminated_total - gap006_eliminated_total:
    die(f"R21_EFFECTIVE_ARITHMETIC_DRIFT:raw={raw_total}:product={product_eliminated_total}:gap006={gap006_eliminated_total}:effective={effective_total}")
if union_gap_uids != EXPECTED_GAPS:
    die(f"SOURCE_EXTERNAL_AUTHORITY_UNION_DRIFT:{sorted(union_gap_uids)}")
all_effective_categories = Counter()
for rec in pages.values():
    all_effective_categories.update(rec["functional_chain_effective_r21_scan"]["gap_categories"])
if dict(sorted(all_effective_categories.items())) != EXPECTED_EFFECTIVE_CATEGORIES:
    die(f"R21_EFFECTIVE_CATEGORY_DRIFT:{dict(sorted(all_effective_categories.items()))}")
if any(g.get("category") == "SHARED_OWNER_AUTHORITY_UNRESOLVED" for rec in pages.values() for g in rec["functional_chain_effective_r21_scan"]["gaps"]):
    die("GAP006_EFFECTIVE_REPRODUCTION_NOT_ZERO")

result = {
    "schema_version": 4,
    "artifact_type": "NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "stage_name": "PAGE_FUNCTIONAL_CONTRACT",
    "reexecution_cycle": "R21_R20_BOUNDED_CLOSURE_PLUS_GAP006",
    "source_head_sha": head,
    "frozen_governance_uid": freeze.get("frozen_governance_uid"),
    "test_mode": "FRESH_RAW_DISCOVERY_PLUS_VALIDATED_STAGE2_R20_BOUNDED_CLOSURE_AND_GAP006_AUTHORITY",
    "fresh_scan_implementation": "EXACT_AST_EXTRACT_OF_run_current_stage2_actual_test.py::fresh_scan",
    "actual_product_stage_test_started": True,
    "actual_product_stage_test_completed": True,
    "stage_entry_gate": "PASS",
    "stage_exit_allowed": False,
    "result": "BLOCKED",
    "physical_stage2_product_artifact_root_present": True,
    "pages": pages,
    "raw_discovery_gap_total": raw_total,
    "product_materialization_total": len(product),
    "product_materialization_by_page": dict(product_by_page),
    "product_materialization_elimination_count": product_eliminated_total,
    "gap006_authority_elimination_count": gap006_eliminated_total,
    "total_effective_elimination_count": product_eliminated_total + gap006_eliminated_total,
    "fresh_functional_gap_total": effective_total,
    "effective_gap_categories": dict(sorted(all_effective_categories.items())),
    "closure_blocker_total": 0,
    "preserved_external_authorities": dict(sorted(source_external.items())),
    "preserved_external_authority_union_count": len(union_gap_uids),
    "preserved_external_authority_union_gap_uids": sorted(union_gap_uids),
    "resolved_gap006_effective_reproduction_count": 0,
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "ai_autofill_used": False,
    "inference_used": False,
    "prior_stage2_results_used": False,
    "prior_stage2_counts_used_as_scan_input": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
    "notes": [
        "Raw discovery was freshly executed from immutable Stage-1 authority using the exact first-run scanner.",
        "Only exact fresh raw defect signatures present in the validated current Stage-02 AUTO_COMPLETION_SCOPE_LEDGER were eliminated as product materializations.",
        "The prior 17 product materializations are preserved; the 19 R20 deterministic minimal closures are added and validated, for 36 product eliminations total.",
        "The four GAP-006 exact current-successor authority resolutions are preserved and independently eliminated.",
        "No historical count was subtracted as scan input; all 40 eliminations were re-matched against the fresh 171-gap raw scan.",
        "Stage-02 remains blocked with 131 effective functional gaps; Stage-03, website construction, and deployment remain prohibited.",
    ],
}
RESULT.parent.mkdir(parents=True, exist_ok=True)
text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
RESULT.write_text(text, encoding="utf-8")
LATEST.write_text(text, encoding="utf-8")

findings = {
    "schema_version": 4,
    "artifact_type": "STAGE02_CURRENT_FINDINGS",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "source_cycle": "R21_R20_BOUNDED_CLOSURE_PLUS_GAP006",
    "source_head_sha": head,
    "raw_discovery_gap_total": 171,
    "validated_product_materialization_elimination_count": 36,
    "validated_external_authority_elimination_count": 4,
    "fresh_functional_gap_total": 131,
    "effective_gap_categories": dict(sorted(all_effective_categories.items())),
    "result": "BLOCKED",
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}
FINDINGS.write_text(yaml.safe_dump(findings, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print("PASS: fresh raw Stage-02 scan=171 gaps using exact first-run scanner implementation")
print("PASS: validated product materialization eliminations=36 (prior 17 + R20/R21 19)")
print("PASS: validated GAP-006 authority eliminations=4")
print("PASS: fresh effective Stage-02 functional gaps=131")
print(f"PASS: effective categories={dict(sorted(all_effective_categories.items()))}")
print("BLOCKED: Stage-02 remains blocked; Stage-03 / website construction / deployment remain prohibited")
