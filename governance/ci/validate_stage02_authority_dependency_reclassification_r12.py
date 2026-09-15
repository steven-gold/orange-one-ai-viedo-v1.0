#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R10 = ROOT / "governance/test/stage02/STAGE02_PRODUCT_AUTHORITY_APPROVAL_DOCKET_R10.yaml"
R12 = ROOT / "governance/test/stage02/STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12.yaml"
ALLOWED = {"DETERMINISTIC_REQUIRED_DEPENDENCY", "TRUE_PRODUCT_AUTHORITY_GAP", "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP"}
EVIDENCE_PREFIX = "00_SOURCE_INTAKE/fresh_run_003/"


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def identity(row):
    return (row.get("blocker_uid"), row.get("scope"), row.get("category"), row.get("target_uid"), row.get("missing_field_or_relation"))


def evidence_paths(row):
    paths = []
    for key in ("authority_requirement_evidence", "deterministic_dependency_evidence", "conflicting_dependency_evidence"):
        for item in row.get(key) or []:
            path = item.get("path")
            if path:
                paths.append(path)
    return paths


def main() -> None:
    r10 = load(R10)
    r12 = load(R12)
    if r12.get("artifact_type") != "NON_NORMATIVE_STAGE02_AUTHORITY_DEPENDENCY_RECLASSIFICATION_R12":
        die("R12_ARTIFACT_TYPE")
    if r12.get("normative_authority") is not False:
        die("R12_MUST_BE_NON_NORMATIVE")
    if r12.get("source_contracts", {}).get("r10_product_authority_conclusion_accepted_as_evidence") is not False:
        die("R12_MUST_NOT_ACCEPT_R10_AUTHORITY_CONCLUSION_AS_EVIDENCE")
    old = r10.get("records") or []
    new = r12.get("records") or []
    if len(old) != 150 or len(new) != 150:
        die(f"R12_DENOMINATOR:{len(old)}:{len(new)}")
    if len({identity(x) for x in new}) != 150:
        die("R12_DUPLICATE_IDENTITY")
    if {identity(x) for x in old} != {identity(x) for x in new}:
        die("R12_IDENTITY_COVERAGE_DRIFT")
    classes = Counter()
    for row in new:
        cls = row.get("classification")
        if cls not in ALLOWED:
            die(f"R12_BAD_CLASS:{row.get('blocker_uid')}:{cls}")
        classes[cls] += 1
        if row.get("r10_identity_only") is not True:
            die(f"R12_R10_NOT_IDENTITY_ONLY:{row.get('blocker_uid')}")
        if row.get("r10_approval_state_used_as_evidence") is not False:
            die(f"R12_R10_APPROVAL_LEAK:{row.get('blocker_uid')}")
        if row.get("r10_authority_decision_used_as_evidence") is not False:
            die(f"R12_R10_DECISION_LEAK:{row.get('blocker_uid')}")
        if row.get("semantic_inference_used") is not False:
            die(f"R12_SEMANTIC_INFERENCE:{row.get('blocker_uid')}")
        if row.get("historical_non_current_authority_used") is not False:
            die(f"R12_HISTORICAL_AUTHORITY:{row.get('blocker_uid')}")
        if row.get("blocker_reduction_credit") != 0:
            die(f"R12_FALSE_REDUCTION:{row.get('blocker_uid')}")
        for path in evidence_paths(row):
            if not path.startswith(EVIDENCE_PREFIX):
                die(f"R12_NON_FROZEN_EVIDENCE:{row.get('blocker_uid')}:{path}")
            if "/governance/test/" in path:
                die(f"R12_TEST_OUTPUT_AS_SUBSTANTIVE_EVIDENCE:{row.get('blocker_uid')}:{path}")
        if cls == "DETERMINISTIC_REQUIRED_DEPENDENCY":
            if not row.get("deterministic_dependency_evidence"):
                die(f"R12_DETERMINISTIC_WITHOUT_EVIDENCE:{row.get('blocker_uid')}")
            if row.get("unique_minimal_dependency") is not True:
                die(f"R12_DETERMINISTIC_NOT_UNIQUE:{row.get('blocker_uid')}")
            if row.get("authority_gap_zero_for_this_derivation") is not True:
                die(f"R12_DETERMINISTIC_AUTHORITY_GAP:{row.get('blocker_uid')}")
            if row.get("scope_ambiguity_zero") is not True:
                die(f"R12_DETERMINISTIC_SCOPE_AMBIGUITY:{row.get('blocker_uid')}")
            if row.get("materialization_candidate") is not True:
                die(f"R12_DETERMINISTIC_NOT_CANDIDATE:{row.get('blocker_uid')}")
        if cls == "TRUE_PRODUCT_AUTHORITY_GAP":
            if not row.get("authority_requirement_evidence"):
                die(f"R12_AUTHORITY_WITHOUT_EXPLICIT_EVIDENCE:{row.get('blocker_uid')}")
            if row.get("materialization_candidate") is not False:
                die(f"R12_AUTHORITY_FALSE_MATERIALIZATION:{row.get('blocker_uid')}")
        if cls == "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP" and row.get("materialization_candidate") is not False:
            die(f"R12_UNRESOLVED_FALSE_MATERIALIZATION:{row.get('blocker_uid')}")
    den = r12.get("denominators") or {}
    if den.get("total_reclassified") != 150:
        die("R12_TOTAL_NOT_150")
    if den.get("deterministic_required_dependency") != classes["DETERMINISTIC_REQUIRED_DEPENDENCY"]:
        die("R12_DETERMINISTIC_COUNT_DRIFT")
    if den.get("true_product_authority_gap_proven") != classes["TRUE_PRODUCT_AUTHORITY_GAP"]:
        die("R12_AUTHORITY_COUNT_DRIFT")
    if den.get("unresolved_functional_contract_gap") != classes["UNRESOLVED_FUNCTIONAL_CONTRACT_GAP"]:
        die("R12_UNRESOLVED_COUNT_DRIFT")
    if sum(classes.values()) != 150:
        die("R12_CLASS_TOTAL_DRIFT")
    if den.get("effective_stage02_blocker_reduction_claimed") != 0:
        die("R12_FALSE_GLOBAL_REDUCTION")
    if r12.get("stage02_status") != "BLOCKED":
        die("R12_STAGE02_MUST_REMAIN_BLOCKED")
    if r12.get("stage03_allowed") is not False or r12.get("website_construction_allowed") is not False or r12.get("deployment_allowed") is not False:
        die("R12_DOWNSTREAM_FALSE_ALLOW")
    if r12.get("supersession", {}).get("r5_r10_r11_all_150_product_authority_interpretation") != "SUPERSEDED_FOR_CLASSIFICATION_BY_R12":
        die("R12_SUPERSESSION_MISSING")
    print(f"PASS: R12 exact 150 identity coverage classes={dict(classes)}")
    print("PASS: true Product Authority requires explicit evidence; absence alone cannot classify it")
    print("PASS: deterministic candidates require exact frozen evidence and still receive zero blocker reduction until materialization + fresh reexecution")


if __name__ == "__main__":
    main()
