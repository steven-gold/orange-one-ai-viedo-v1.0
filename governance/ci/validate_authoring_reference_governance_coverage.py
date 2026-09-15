#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "governance/test/AUTHORING_REFERENCE_GOVERNANCE_COVERAGE_REPORT.json"

MOTHER_01 = ROOT / ".github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md"
MOTHER_03 = ROOT / ".github/governance-source/active/source/12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md"
MOTHER_04 = ROOT / ".github/governance-source/active/source/12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md"

CURRENT = ROOT / "governance/specifications/current"
EXECUTION = CURRENT / "EXECUTION_CYCLE_CONTROL.yaml"
MUTATION = CURRENT / "SPECIFICATION_MUTATION_CONTROL.yaml"
LAYER = CURRENT / "GOVERNANCE_LAYER_SEPARATION_AND_PORTABILITY.yaml"
EVIDENCE = CURRENT / "EVIDENCE_FEEDBACK_ARTIFACT_LIFECYCLE.yaml"
MANIFEST = CURRENT / "SPECIFICATION_MANIFEST.yaml"
REGISTRY = ROOT / "governance/specifications/REGISTRY.yaml"
CURRENT_ENTRY = ROOT / "GOVERNANCE_CURRENT.yaml"

MUTATION_GUARD = ROOT / "governance/ci/specification_mutation_guard.py"
REFERENCE_GATE = ROOT / "governance/ci/validate_active_consumer_reference_integrity.py"
CANONICAL_GATE = ROOT / "governance/ci/validate_canonical_rule_registry.py"
LAYOUT_GATE = ROOT / "governance/ci/validate_governance_layout.py"

TARGETED = ROOT / ".github/workflows/targeted-stage01-stage02.yml"
FULL_LINE = ROOT / ".github/workflows/governance-full-line-system-gate.yml"

failures: list[str] = []
controls: list[dict] = []


def text(path: Path) -> str:
    if not path.is_file():
        failures.append(f"MISSING_REQUIRED_FILE:{path.relative_to(ROOT).as_posix()}")
        return ""
    value = path.read_text(encoding="utf-8")
    if not value.strip():
        failures.append(f"EMPTY_REQUIRED_FILE:{path.relative_to(ROOT).as_posix()}")
    return value


def require_tokens(control_id: str, path: Path, required: list[str]) -> None:
    body = text(path)
    missing = [token for token in required if token not in body]
    controls.append({
        "control_id": control_id,
        "path": path.relative_to(ROOT).as_posix(),
        "required_token_count": len(required),
        "missing": missing,
        "status": "PASS" if not missing else "FAIL",
    })
    for token in missing:
        failures.append(f"{control_id}:MISSING_TOKEN:{path.relative_to(ROOT).as_posix()}:{token}")


# Coverage/enforcement map for already-existing authority. It is non-normative and
# must never be treated as a second registry, second policy owner, or substitute authority.
require_tokens("MOTHER_CANONICAL_OWNERSHIP", MOTHER_01, [
    "SECTION_UID: WEB-GOV-01-S002",
    "ONE AUTHORITY",
    "ONE CANONICAL NAME",
    "ONE OWNER FILE",
    "SECTION_UID: WEB-GOV-01-S003A",
    "MODIFY THE OWNER; DO NOT CREATE A PARALLEL COPY",
])
require_tokens("MOTHER_SEARCH_AND_REFERENCE", MOTHER_01, [
    "SECTION_UID: WEB-GOV-01-S007",
    "更新所有 Reference",
    "SECTION_UID: WEB-GOV-01-S008",
    "第一次搜尋沒有結果 MUST_NOT 直接建立新項目",
])
require_tokens("MOTHER_DUPLICATE_CONFLICT_SECOND_SYSTEM", MOTHER_03, [
    "SECTION_UID: WEB-GOV-03-S005",
    "PRE_IMPLEMENTATION_DUPLICATE_GUARD",
    "SECTION_UID: WEB-GOV-03-S006",
    "Duplicate-by-Renaming Guard",
    "SECTION_UID: WEB-GOV-03-S007",
    "SECOND_SYSTEM_GUARD",
    "SECTION_UID: WEB-GOV-03-S009",
    "Conflict Guard",
    "SECTION_UID: WEB-GOV-03-S015",
    "新檔建立前防呆",
])
require_tokens("MOTHER_STUB_AND_RESIDUAL", MOTHER_03, [
    "SECTION_UID: WEB-GOV-03-S014",
    "TODO in Required Flow",
    "Placeholder Runtime",
    "SECTION_UID: WEB-GOV-03-S016A",
    "empty placeholder",
    "UNJUSTIFIED_RESIDUAL_FILES = 0",
])
require_tokens("MOTHER_AUDIT_COVERAGE", MOTHER_04, [
    "SECTION_UID: WEB-GOV-04-S017",
    "Naming Audit",
    "SECTION_UID: WEB-GOV-04-S018",
    "Duplicate Audit",
    "SECTION_UID: WEB-GOV-04-S019",
    "Second-System Audit",
    "SECTION_UID: WEB-GOV-04-S020",
    "Conflict Audit",
    "SECTION_UID: WEB-GOV-04-S022A",
    "UNJUSTIFIED_RESIDUAL_FILES = 0",
])

require_tokens("CURRENT_EXECUTION_PREWRITE", EXECUTION, [
    "CANONICAL_OWNER_RESOLUTION",
    "COMPLETE_READ_SET",
    "DUPLICATE_CONFLICT_SUPERSESSION_SCAN",
    "GAP_PROOF",
    "PRE_WRITE_IDENTITY_RECHECK",
    "default_write_disposition: MODIFY_EXISTING_CANONICAL_OWNER",
    "first_search_miss_is_sufficient: false",
    "PROVE_ZERO_STALE_REFERENCE",
    "PROVE_ZERO_UNJUSTIFIED_RESIDUAL",
])
require_tokens("CURRENT_REFERENCE_ATOMICITY", MUTATION, [
    "complete_active_reverse_consumer_set_required: true",
    "reverse_consumer_set_must_be_frozen_against_prewrite_commit_and_tree: true",
    "partial_consumer_migration: BLOCK",
    "all_affected_active_references_must_migrate_in_same_atomic_commit: true",
    "persisted_head_reference_integrity_gate_required: true",
    "zero_stale_or_broken_current_reference_required: true",
    "zero_unjustified_residual_required: true",
])
require_tokens("CURRENT_SINGLE_RULE_OWNER", LAYER, [
    "one_canonical_rule_owner_per_semantic_rule: true",
    "duplicate_or_contradictory_active_rule_owner: BLOCK",
    "superseded_active_residual: BLOCK",
    "duplicate_local_rule_vocabulary: BLOCK",
])
require_tokens("CURRENT_EVIDENCE_RESIDUAL", EVIDENCE, [
    "temporary_artifact_cleanup_incomplete: BLOCK",
    "zero_residual_scan_failed: BLOCK",
    "duplicate_semantic_finding_without_regression_evidence: BLOCK",
])

require_tokens("MACHINE_PREWRITE_GUARD", MUTATION_GUARD, [
    '"relevant_scope_read_complete"',
    '"canonical_owner_resolution_complete"',
    '"existing_semantics_comparison_complete"',
    '"duplicate_search_complete"',
    '"conflict_search_complete"',
    '"second_system_search_complete"',
    '"gap_proven_before_write"',
    '"MODIFY_EXISTING_CANONICAL_OWNER"',
    '"CREATE_NEW_ONLY_AFTER_NO_EXISTING_OWNER_PROVEN"',
])
require_tokens("MACHINE_REFERENCE_GATE", REFERENCE_GATE, [
    "MISSING_ACTIVE_CONSUMER_TARGET",
    "SEMVER_LOCATOR_IN_ACTIVE_WORKFLOW",
    "SEMVER_LOCATOR_IN_ACTIVE_CONSUMER",
    "ACTIVE_GOVERNANCE_PROJECTOR_STALE",
    "REFERENCE_INTEGRITY_GATE_MISSING_FROM_REQUIRED_REGRESSION",
])
require_tokens("MACHINE_CANONICAL_GATE", CANONICAL_GATE, [
    "PREWRITE_MISSING_DUPLICATE_PROOF_NOT_BLOCKED",
    "OBSOLETE_ACTIVE_CONSUMER_RESIDUAL",
    "ACTIVE_WORKFLOW_STALE_COMPAT_SHIM",
])
require_tokens("MACHINE_LAYOUT_RESIDUAL_GATE", LAYOUT_GATE, [
    "LEGACY_OR_DUPLICATE_ROOT",
    "TEMPORARY_TEST_ARTIFACT_RESIDUAL",
    "EMPTY_TEMPORARY_TEST_DIRECTORY_RESIDUAL",
])

# Current normative surfaces may not themselves contain unfinished authoring placeholders.
placeholder_re = re.compile(r"(?im)^\s*(?:TODO|TBD|PLACEHOLDER)(?:\s*[:=-]|\s*$)")
manifest_data = yaml.safe_load(text(MANIFEST)) or {}
current_surface_paths = [REGISTRY, CURRENT_ENTRY, MANIFEST]
for rec in manifest_data.get("components") or []:
    if rec.get("file"):
        current_surface_paths.append(CURRENT / rec["file"])
for rec in manifest_data.get("support_authorities") or []:
    if rec.get("file"):
        current_surface_paths.append(CURRENT / rec["file"])

seen: set[Path] = set()
for path in current_surface_paths:
    if path in seen:
        continue
    seen.add(path)
    body = text(path)
    if placeholder_re.search(body):
        failures.append(f"CURRENT_NORMATIVE_PLACEHOLDER:{path.relative_to(ROOT).as_posix()}")

coverage_gate_ref = "governance/ci/validate_authoring_reference_governance_coverage.py"
reference_gate_ref = "governance/ci/validate_active_consumer_reference_integrity.py"
for workflow in (TARGETED, FULL_LINE):
    body = text(workflow)
    rel = workflow.relative_to(ROOT).as_posix()
    if coverage_gate_ref not in body:
        failures.append(f"COVERAGE_GATE_NOT_WIRED:{rel}")
    if reference_gate_ref not in body:
        failures.append(f"REFERENCE_GATE_NOT_WIRED:{rel}")

report = {
    "artifact_type": "NON_NORMATIVE_AUTHORING_REFERENCE_GOVERNANCE_COVERAGE_REPORT",
    "scope": "AUTHORING_REFERENCE_DUPLICATE_CONFLICT_RESIDUAL_GOVERNANCE",
    "normative_authority": False,
    "authority_sources": [
        MOTHER_01.relative_to(ROOT).as_posix(),
        MOTHER_03.relative_to(ROOT).as_posix(),
        MOTHER_04.relative_to(ROOT).as_posix(),
        EXECUTION.relative_to(ROOT).as_posix(),
        MUTATION.relative_to(ROOT).as_posix(),
        LAYER.relative_to(ROOT).as_posix(),
        EVIDENCE.relative_to(ROOT).as_posix(),
    ],
    "control_count": len(controls),
    "controls": controls,
    "current_normative_surface_count": len(seen),
    "result": "PASS" if not failures else "FAIL",
    "failures": failures,
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if failures:
    for failure in failures:
        print("BLOCK:", failure, file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: authoring/reference governance controls={len(controls)}/{len(controls)}")
print(f"PASS: current normative surfaces checked={len(seen)}; no unfinished authoring placeholder")
print("PASS: search-before-create, canonical-owner, duplicate/conflict/second-system, reference-atomicity, residual, and audit coverage are connected")
print("PASS: coverage gate and active-consumer reference gate are wired into targeted and Full-Line regressions")
print("PASS: AUTHORING_REFERENCE_GOVERNANCE_COVERAGE")
