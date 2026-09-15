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
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"
FREEZE = ROOT / "governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml"
LATEST = ROOT / "governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json"
FINDINGS = ROOT / "governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml"
RESULT = ROOT / ".github/stage02-test/STAGE02_R23_EFFECTIVE_REEXECUTION_RESULT.json"
RECEIPT = ROOT / "governance/test/stage02/STAGE02_R23_BOUNDED_MATERIALIZATION_RECEIPT.yaml"
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
BASE_EFFECTIVE_CATEGORIES = {
    "ACTION_WITHOUT_CONTROL_OR_TRIGGER": 1,
    "AUDIT_EVENT_NODE_MISSING": 13,
    "FAILURE_STATE_ERROR_BINDING_MISSING": 44,
    "PAYLOAD_INPUT_CONTRACT_MISSING": 34,
    "POST_ACTION_VALIDATION_NODE_MISSING": 1,
    "STATE_TRANSITION_LEDGER_FIELD_MISSING": 36,
}


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


def head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()


def load_fresh_scan():
    tree = ast.parse(SCANNER_SOURCE.read_text(encoding="utf-8"), filename=str(SCANNER_SOURCE))
    keep = {"idx", "present", "event_token", "has_transition", "add", "fresh_scan"}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if "KNOWN_AUTHORITIES" in {t.id for t in node.targets if isinstance(t, ast.Name)}:
                selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in keep:
            selected.append(node)
    found = {n.name for n in selected if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if found != keep:
        die(f"FRESH_SCAN_EXTRACTION_DRIFT:{sorted(found)}")
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {"Counter": Counter, "defaultdict": defaultdict, "re": re}
    exec(compile(module, str(SCANNER_SOURCE), "exec"), ns, ns)
    return ns["fresh_scan"]


def signature(page, gap):
    return (page, gap.get("category"), str(gap.get("uid")), gap.get("detail"))


def load_product(expected_r23):
    out = {}
    by_page = Counter()
    cycle_counts = Counter()
    for page, cfg in PAGES.items():
        ledger = load(cfg["ledger"])
        rems = ledger.get("remediations") or []
        if ledger.get("materialized_remediation_count") != len(rems):
            die(f"LEDGER_COUNT_DRIFT:{page}")
        for rem in rems:
            ds = rem.get("defect_signature") or {}
            key = (page, ds.get("category"), str(ds.get("uid")), ds.get("detail"))
            if key in out:
                die(f"DUPLICATE_PRODUCT_SIGNATURE:{key}")
            out[key] = rem
            by_page[page] += 1
            cycle_counts[str(rem.get("source_cycle") or "R3_BOUNDED_FUNCTIONAL_COMPLETION")] += 1
    expected_total = 38 + expected_r23
    expected_by_page = Counter({"ASSET-01": 33 + expected_r23, "CORE-01": 5})
    if len(out) != expected_total or by_page != expected_by_page:
        die(f"PRODUCT_DENOMINATOR_DRIFT:{len(out)}:{dict(by_page)} expected={expected_total}:{dict(expected_by_page)}")
    if cycle_counts.get("R22_POST_ACTION_SIGNAL_ROLE_CORRECTION") != 2:
        die(f"R22_PRODUCT_COUNT_DRIFT:{dict(cycle_counts)}")
    if cycle_counts.get("R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD") != expected_r23:
        die(f"R23_PRODUCT_COUNT_DRIFT:{dict(cycle_counts)}")
    return out, by_page, cycle_counts


def load_gap006():
    doc = load(GAP006_MAP)
    if doc.get("artifact_uid") != "FRESH-RUN-003-STAGE2-SHARED-OWNER-PORT-MAP-R3" or doc.get("status") != "RESOLVED_AUTHORITY_GAP_CURRENT_SUCCESSOR":
        die("GAP006_MAP_IDENTITY_DRIFT")
    out = {}
    for row in doc.get("consumers") or []:
        if row.get("page_uid") != "ASSET-01" or row.get("status") != "RESOLVED_EXACT_AUTHORITY" or row.get("binding_kind") != "SHARED_OPERATION_REFERENCE":
            die(f"GAP006_CONSUMER_DRIFT:{row.get('action_uid')}")
        key = ("ASSET-01", "SHARED_OWNER_AUTHORITY_UNRESOLVED", str(row.get("action_uid")), GAP006_DETAIL)
        out[key] = row
    if len(out) != 4:
        die(f"GAP006_DENOMINATOR:{len(out)}")
    return out


def external_refs(blueprint):
    return [
        {"gap_uid": r.get("gap_uid"), "authority_ref": r.get("authority_ref")}
        for r in (blueprint.get("unresolved_external_authority_refs") or []) if isinstance(r, dict)
    ]


def effective(page, raw_scan, product, gap006):
    remaining, prod_elim, auth_elim = [], [], []
    raw_keys = [signature(page, g) for g in (raw_scan.get("gaps") or [])]
    if len(raw_keys) != len(set(raw_keys)):
        die(f"RAW_SIGNATURE_DUPLICATE:{page}")
    for gap in raw_scan.get("gaps") or []:
        key = signature(page, gap)
        if key in product and key in gap006:
            die(f"OVERLAPPING_REMEDIATION:{key}")
        if key in product:
            rem = product[key]
            prod_elim.append({
                "raw_gap": gap,
                "remediation_uid": rem.get("remediation_uid"),
                "source_cycle": rem.get("source_cycle", "R3_BOUNDED_FUNCTIONAL_COMPLETION"),
                "materialized_closure": rem.get("materialized_closure"),
                "effective_reproduction": False,
            })
        elif key in gap006:
            auth_elim.append({
                "raw_gap": gap,
                "authority_gap_uid": "GAP-006",
                "resolution": "RESOLVED_EXACT_AUTHORITY",
                "effective_reproduction": False,
            })
        else:
            remaining.append(gap)
    return {
        "gap_count": len(remaining),
        "gap_categories": dict(sorted(Counter(x.get("category") for x in remaining).items())),
        "gap_classes": dict(sorted(Counter(x.get("class") for x in remaining).items())),
        "gaps": remaining,
        "product_materialization_elimination_count": len(prod_elim),
        "product_materialization_eliminations": prod_elim,
        "gap006_authority_elimination_count": len(auth_elim),
        "gap006_authority_eliminations": auth_elim,
        "total_elimination_count": len(prod_elim) + len(auth_elim),
    }


if os.environ.get("STAGE02_FULL_LINE_CONFIRMED") != "1":
    die("R23_REEXECUTION_REQUIRES_FULL_LINE_CONFIRMATION")
state = load(STATE)
freeze = load(FREEZE)
receipt = load(RECEIPT)
execution = state.get("execution") or {}
if execution.get("current_stage") != "STAGE-02-TESTED-BLOCKED" or (execution.get("stage2") or {}).get("result") != "TEST_EXECUTED_BLOCKED":
    die("R23_REEXECUTION_REQUIRES_STAGE02_BLOCKED_STATE")
if freeze.get("stage_uid") != "STAGE-02" or not freeze.get("frozen_governance_uid"):
    die("FROZEN_GOVERNANCE_RECEIPT_INVALID")
r23_count = receipt.get("materialized_now_total")
if not isinstance(r23_count, int) or r23_count < 1 or r23_count > 4:
    die(f"R23_RECEIPT_COUNT_INVALID:{r23_count}")
if receipt.get("before_materialized_product_total") != 38 or receipt.get("after_materialized_product_total") != 38 + r23_count:
    die("R23_RECEIPT_ARITHMETIC_DRIFT")

for validator in (
    ROOT / "governance/ci/validate_stage02_current_authority_payload_closures_r23.py",
    ROOT / "governance/ci/validate_stage02_r23_materialized_payload_closures.py",
    ROOT / "governance/ci/validate_current_stage2_external_authority_resolution_r3.py",
):
    cp = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die(f"PRE_REEXECUTION_VALIDATOR_FAILED:{validator.name}")

fresh_scan = load_fresh_scan()
product, product_by_page, cycle_counts = load_product(r23_count)
gap006 = load_gap006()
if set(product) & set(gap006):
    die("PRODUCT_GAP006_SIGNATURE_OVERLAP")

pages = {}
source_external = {}
union_gap_uids = set()
matched_product, matched_gap006 = set(), set()
raw_total = product_eliminated = gap006_eliminated = effective_total = 0
for page, cfg in PAGES.items():
    raw = load(cfg["raw"])
    blueprint = load(cfg["blueprint"])
    refs = external_refs(blueprint)
    for ref in refs:
        gid = ref.get("gap_uid")
        union_gap_uids.add(gid)
        rec = source_external.setdefault(gid, {"authority_ref": ref.get("authority_ref"), "consumers": [], "source_reference_preserved": True})
        rec["consumers"].append(page)
    raw_scan = fresh_scan(page, raw)
    eff = effective(page, raw_scan, product, gap006)
    raw_total += raw_scan.get("gap_count", 0)
    product_eliminated += eff["product_materialization_elimination_count"]
    gap006_eliminated += eff["gap006_authority_elimination_count"]
    effective_total += eff["gap_count"]
    matched_product |= {signature(page, x["raw_gap"]) for x in eff["product_materialization_eliminations"]}
    matched_gap006 |= {signature(page, x["raw_gap"]) for x in eff["gap006_authority_eliminations"]}
    pages[page] = {
        "blueprint_uid": blueprint.get("blueprint_uid"),
        "ai_interaction_profile_active": cfg["ai_profile"],
        "source_external_authority_ref_count": len(refs),
        "functional_chain_raw_fresh_scan": raw_scan,
        "functional_chain_effective_r23_scan": eff,
        "materialized_product_functional_contract_validation": "PASS",
        "gap006_external_authority_validation": "PASS",
    }

expected_product = 38 + r23_count
expected_effective = 129 - r23_count
expected_categories = dict(BASE_EFFECTIVE_CATEGORIES)
expected_categories["PAYLOAD_INPUT_CONTRACT_MISSING"] = 34 - r23_count
if raw_total != 171:
    die(f"RAW_DENOMINATOR_DRIFT:{raw_total}")
if matched_product != set(product):
    die(f"PRODUCT_SIGNATURE_MATCH_DRIFT:missing={sorted(set(product)-matched_product)}")
if matched_gap006 != set(gap006):
    die(f"GAP006_SIGNATURE_MATCH_DRIFT:missing={sorted(set(gap006)-matched_gap006)}")
if product_eliminated != expected_product or gap006_eliminated != 4 or effective_total != expected_effective:
    die(f"R23_EFFECTIVE_ARITHMETIC:raw={raw_total}:product={product_eliminated}:gap006={gap006_eliminated}:effective={effective_total}:expected={expected_effective}")
if effective_total != raw_total - product_eliminated - gap006_eliminated:
    die("R23_EFFECTIVE_ARITHMETIC_IDENTITY_FAILED")
if union_gap_uids != EXPECTED_GAPS:
    die(f"EXTERNAL_AUTHORITY_UNION_DRIFT:{sorted(union_gap_uids)}")
all_categories = Counter()
for page in pages.values():
    all_categories.update(page["functional_chain_effective_r23_scan"]["gap_categories"])
if dict(sorted(all_categories.items())) != expected_categories:
    die(f"R23_EFFECTIVE_CATEGORY_DRIFT:{dict(sorted(all_categories.items()))}:expected={expected_categories}")
if any(g.get("category") == "SHARED_OWNER_AUTHORITY_UNRESOLVED" for p in pages.values() for g in p["functional_chain_effective_r23_scan"]["gaps"]):
    die("GAP006_REPRODUCED")
remaining_payload_targets = sorted(
    str(g.get("uid"))
    for p in pages.values()
    for g in p["functional_chain_effective_r23_scan"]["gaps"]
    if g.get("category") == "PAYLOAD_INPUT_CONTRACT_MISSING"
)

result = {
    "schema_version": 6,
    "artifact_type": "NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "stage_name": "PAGE_FUNCTIONAL_CONTRACT",
    "reexecution_cycle": "R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD",
    "source_head_sha": head(),
    "frozen_governance_uid": freeze.get("frozen_governance_uid"),
    "test_mode": "FRESH_RAW_DISCOVERY_PLUS_VALIDATED_STAGE2_BOUNDED_CLOSURES_AND_GAP006_AUTHORITY",
    "fresh_scan_implementation": "EXACT_AST_EXTRACT_OF_run_current_stage2_actual_test.py::fresh_scan",
    "actual_product_stage_test_started": True,
    "actual_product_stage_test_completed": True,
    "stage_entry_gate": "PASS",
    "stage_exit_allowed": False,
    "result": "BLOCKED",
    "pages": pages,
    "raw_discovery_gap_total": 171,
    "product_materialization_total": expected_product,
    "product_materialization_by_page": dict(product_by_page),
    "product_materialization_cycle_counts": dict(cycle_counts),
    "product_materialization_elimination_count": expected_product,
    "r23_current_authority_payload_elimination_count": r23_count,
    "gap006_authority_elimination_count": 4,
    "total_effective_elimination_count": expected_product + 4,
    "fresh_functional_gap_total": expected_effective,
    "effective_gap_categories": dict(sorted(all_categories.items())),
    "remaining_payload_gap_total": 34 - r23_count,
    "remaining_payload_targets": remaining_payload_targets,
    "preserved_external_authorities": dict(sorted(source_external.items())),
    "preserved_external_authority_union_count": len(union_gap_uids),
    "preserved_external_authority_union_gap_uids": sorted(union_gap_uids),
    "remaining_r22_authority_gap": {
        "target_uid": "ASSET-01-ACT-CORRECTION-EXECUTE",
        "category": "POST_ACTION_VALIDATION_NODE_MISSING",
        "reason": "two distinct admissible action-result signals remain after transition-role correction",
    },
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "ai_autofill_used": False,
    "inference_used": False,
    "operation_registry_used_as_payload_authority": False,
    "prior_stage2_results_used_as_scan_input": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
    "notes": [
        "Fresh Raw discovery remained 171 using the exact first-run scanner implementation.",
        f"Exactly {expected_product} product materializations re-matched current fresh Raw signatures, including {r23_count} R23 Current Authority required_payload closures.",
        "Exactly four GAP-006 current-successor authority resolutions re-matched current fresh Raw signatures.",
        "R23 payload closures copy explicit required_payload from manifest-listed Current Shared Runtime Authority only; operation_registry was identity support only and not payload authority.",
        "ASSET-01-ACT-CORRECTION-EXECUTE remains blocked because action result and bound-port state_event remain distinct admissible result signals.",
        f"Stage-02 remains blocked with {expected_effective} effective functional gaps; Stage-03, website construction, and deployment remain prohibited.",
    ],
}
RESULT.parent.mkdir(parents=True, exist_ok=True)
text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
RESULT.write_text(text, encoding="utf-8")
LATEST.write_text(text, encoding="utf-8")
FINDINGS.write_text(yaml.safe_dump({
    "schema_version": 6,
    "artifact_type": "STAGE02_CURRENT_FINDINGS",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "source_cycle": "R23_CURRENT_AUTHORITY_REQUIRED_PAYLOAD",
    "source_head_sha": result["source_head_sha"],
    "raw_discovery_gap_total": 171,
    "validated_product_materialization_elimination_count": expected_product,
    "validated_r23_current_authority_payload_elimination_count": r23_count,
    "validated_external_authority_elimination_count": 4,
    "fresh_functional_gap_total": expected_effective,
    "effective_gap_categories": result["effective_gap_categories"],
    "remaining_payload_gap_total": 34 - r23_count,
    "remaining_true_authority_gap_count": 1,
    "remaining_true_authority_gap_targets": ["ASSET-01-ACT-CORRECTION-EXECUTE"],
    "result": "BLOCKED",
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print("PASS: fresh raw Stage-02 scan=171 using exact first-run scanner")
print(f"PASS: validated product eliminations={expected_product}; R23 payload eliminations={r23_count}; GAP-006 eliminations=4")
print(f"PASS: fresh effective Stage-02 functional gaps={expected_effective}")
print(f"PASS: effective categories={dict(sorted(all_categories.items()))}")
print("BLOCKED: residual functional gaps remain; Stage-02 / construction / deployment stay fail-closed")
