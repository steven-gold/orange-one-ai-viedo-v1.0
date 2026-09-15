#!/usr/bin/env python3
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "00_SOURCE_INTAKE/fresh_run_003"
SCANNER = ROOT / "governance/ci/run_current_stage2_actual_test.py"
R29 = ROOT / ".github/stage02-test/STAGE02_R29_EFFECTIVE_REEXECUTION_RESULT.json"
PRODUCT = RUN / "04_PAGE_FUNCTIONAL_CONTRACT"
OUT = ROOT / "governance/test/stage02/STAGE02_INDEPENDENT_DENOMINATOR_RECOMPUTATION_R35.yaml"
FINDING = ROOT / "governance/test/stage02/FIND-20260915-026_STAGE02_DENOMINATOR_UNDERCOUNT.yaml"
PAGES = {
    "CORE-01": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
    "ASSET-01": RUN / "00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
}
GAP006 = PRODUCT / "SHARED_OWNER_PORT_MAP_R3.yaml"
GAP006_DETAIL = "GAP-006: ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY"


def die(msg: str) -> None:
    raise SystemExit(f"BLOCK: {msg}")


def load_yaml(path: Path):
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def scanner_fn():
    tree = ast.parse(SCANNER.read_text(encoding="utf-8"), filename=str(SCANNER))
    keep = {"idx", "present", "event_token", "has_transition", "add", "fresh_scan"}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and "KNOWN_AUTHORITIES" in {t.id for t in node.targets if isinstance(t, ast.Name)}:
            selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in keep:
            selected.append(node)
    found = {n.name for n in selected if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if found != keep:
        die(f"SCANNER_EXTRACTION_DRIFT:{sorted(found)}")
    mod = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(mod)
    ns = {"Counter": Counter, "defaultdict": defaultdict, "re": re}
    exec(compile(mod, str(SCANNER), "exec"), ns, ns)
    return ns["fresh_scan"]


def signature(page: str, gap: dict):
    return (page, gap.get("category"), str(gap.get("uid")), gap.get("detail"))


def product_signatures():
    out = {}
    for page in PAGES:
        ledger = load_yaml(PRODUCT / page / "AUTO_COMPLETION_SCOPE_LEDGER.yaml")
        for rem in ledger.get("remediations") or []:
            ds = rem.get("defect_signature") or {}
            key = (page, ds.get("category"), str(ds.get("uid")), ds.get("detail"))
            if key in out:
                die(f"DUPLICATE_PRODUCT_SIGNATURE:{key}")
            out[key] = rem.get("remediation_uid")
    return out


def gap006_signatures():
    d = load_yaml(GAP006)
    out = {}
    for row in d.get("consumers") or []:
        key = ("ASSET-01", "SHARED_OWNER_AUTHORITY_UNRESOLVED", str(row.get("action_uid")), GAP006_DETAIL)
        out[key] = "GAP-006"
    return out


scan = scanner_fn()
prod = product_signatures()
ext = gap006_signatures()
raw_total = 0
effective_total = 0
raw_categories = Counter()
effective_categories = Counter()
page_results = {}
matched_prod = set()
matched_ext = set()
transition_gap_rows = []

for page, raw_path in PAGES.items():
    raw = load_yaml(raw_path)
    result = scan(page, raw)
    gaps = result.get("gaps") or []
    raw_total += len(gaps)
    raw_categories.update(g.get("category") for g in gaps)
    remaining = []
    for gap in gaps:
        key = signature(page, gap)
        if key in prod and key in ext:
            die(f"ELIMINATION_OVERLAP:{key}")
        if key in prod:
            matched_prod.add(key)
            continue
        if key in ext:
            matched_ext.add(key)
            continue
        remaining.append(gap)
    effective_total += len(remaining)
    effective_categories.update(g.get("category") for g in remaining)
    transition_rows = [
        {"transition_uid": str(g.get("uid")), "missing_field": str(g.get("detail"))}
        for g in gaps
        if g.get("category") == "STATE_TRANSITION_LEDGER_FIELD_MISSING"
    ]
    transition_gap_rows.extend({"page_uid": page, **r} for r in transition_rows)
    page_results[page] = {
        "raw_gap_total": len(gaps),
        "raw_gap_categories": dict(sorted(Counter(g.get("category") for g in gaps).items())),
        "effective_gap_total": len(remaining),
        "effective_gap_categories": dict(sorted(Counter(g.get("category") for g in remaining).items())),
        "stage_transition_denominator": (result.get("registry_denominator") or {}).get("stage_transitions"),
        "transition_missing_field_rows": transition_rows,
    }

import json
prior = json.loads(R29.read_text(encoding="utf-8"))
prior_raw = int(prior.get("raw_discovery_gap_total", -1))
prior_effective = int(prior.get("fresh_functional_gap_total", -1))
missing_fields = Counter(r["missing_field"] for r in transition_gap_rows)
transition_uids = sorted({(r["page_uid"], r["transition_uid"]) for r in transition_gap_rows})
result = {
    "schema_version": 1,
    "artifact_uid": "STAGE02-INDEPENDENT-DENOMINATOR-RECOMPUTATION-R35",
    "artifact_type": "NON_NORMATIVE_STAGE02_DENOMINATOR_CORRECTNESS_EVIDENCE",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "source_head_sha": head(),
    "source_scanner": str(SCANNER.relative_to(ROOT)),
    "recomputation_mode": "INDEPENDENT_FROM_CURRENT_SCANNER_AND_IMMUTABLE_RAW_WITHOUT_EXPECTED_DENOMINATOR_CONSTANT",
    "raw_gap_total": raw_total,
    "raw_gap_categories": dict(sorted(raw_categories.items())),
    "validated_product_elimination_count": len(matched_prod),
    "validated_gap006_elimination_count": len(matched_ext),
    "effective_gap_total": effective_total,
    "effective_gap_categories": dict(sorted(effective_categories.items())),
    "pages": page_results,
    "transition_required_field_gap_total": len(transition_gap_rows),
    "transition_missing_field_counts": dict(sorted(missing_fields.items())),
    "transition_uid_denominator": len(transition_uids),
    "r29_claimed_raw_gap_total": prior_raw,
    "r29_claimed_effective_gap_total": prior_effective,
    "raw_denominator_delta_vs_r29": raw_total - prior_raw,
    "effective_denominator_delta_vs_r29": effective_total - prior_effective,
    "denominator_mismatch_detected": raw_total != prior_raw or effective_total != prior_effective,
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "blocker_reduction_claimed": 0,
    "stage_exit_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}
OUT.write_text(yaml.safe_dump(result, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")

finding = {
    "schema_version": 1,
    "finding_uid": "FIND-20260915-026",
    "stage_uid": "STAGE-02",
    "finding_type": "TEST_EVIDENCE_DENOMINATOR_UNDERCOUNT_OR_DRIFT",
    "status": "OPEN" if result["denominator_mismatch_detected"] else "NOT_REPRODUCED",
    "summary": "R29/R30 denominator must be reconciled against an independent current-scanner recomputation; no expected denominator constant is accepted as evidence.",
    "r35_evidence_ref": str(OUT.relative_to(ROOT)),
    "observed_raw_gap_total": raw_total,
    "observed_effective_gap_total": effective_total,
    "prior_r29_raw_gap_total": prior_raw,
    "prior_r29_effective_gap_total": prior_effective,
    "transition_required_field_gap_total": len(transition_gap_rows),
    "transition_missing_field_counts": dict(sorted(missing_fields.items())),
    "forbidden_resolution": ["LOOSEN_R34_VALIDATOR_TO_MATCH_STALE_DENOMINATOR", "DROP_ILLEGAL_TRANSITION_TESTS", "MUTATE_FROZEN_CURRENT_SPEC"],
    "required_remediation_if_reproduced": "CORRECT_INTERMEDIATE_TRACE_REGISTER_DENOMINATOR_AND_REBUILD_SUCCESSORS_FROM_FRESH_PHYSICAL_SCAN",
}
FINDING.write_text(yaml.safe_dump(finding, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print(yaml.safe_dump(result, allow_unicode=True, sort_keys=False, width=180))
