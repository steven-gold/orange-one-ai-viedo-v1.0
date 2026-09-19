#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"
EVIDENCE = ROOT / "governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json"
FINDINGS = ROOT / "governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml"
CANDIDATES = ROOT / "governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml"
ZERO = ROOT / "governance/ci/validate_stage02_zero_residual.py"


def die(msg: str) -> None:
    print("BLOCK:", msg, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path, label: str) -> dict:
    if not path.is_file():
        die(f"{label}_MISSING")
    try:
        obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        die(f"{label}_PARSE_ERROR:{exc!r}")
    if not isinstance(obj, dict):
        die(f"{label}_MAPPING_REQUIRED")
    return obj


def blocked_product_root_continuity_error(
    *,
    root_present,
    evidence_root_present,
    material: dict,
    revalidation_mode: bool,
    canonical_owner_ref: str,
    repo_root: Path = ROOT,
) -> str | None:
    if root_present not in {True, False}:
        return "BLOCKED_STAGE2_ARTIFACT_ROOT_FLAG_INVALID"
    if root_present is False:
        return None
    if material.get("material_remediation_started") is not True:
        return "BLOCKED_PRODUCT_ROOT_REQUIRES_MATERIAL_REMEDIATION_STATE"
    if evidence_root_present is True:
        return None
    if not revalidation_mode:
        return "BLOCKED_PRODUCT_ROOT_EVIDENCE_MISMATCH"
    if int(material.get("product_blocker_credit") or 0) != 0:
        return "REVALIDATION_PRODUCT_ROOT_PREMATURE_PRODUCT_CREDIT"
    if int(material.get("exact_materialized_closure_count_pending_revalidation") or 0) <= 0:
        return "REVALIDATION_PRODUCT_ROOT_PENDING_CLOSURE_COUNT_MISSING"
    owner = str(canonical_owner_ref or "").strip()
    if not owner:
        return "REVALIDATION_PRODUCT_ROOT_CANONICAL_OWNER_MISSING"
    owner_path = Path(owner)
    if owner_path.is_absolute() or ".." in owner_path.parts:
        return "REVALIDATION_PRODUCT_ROOT_CANONICAL_OWNER_INVALID"
    if not (repo_root / owner_path).is_file():
        return "REVALIDATION_PRODUCT_ROOT_CANONICAL_OWNER_NOT_MATERIALIZED"
    return None


def self_test_revalidation_root_continuity() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        owner = Path("run/04_PAGE_FUNCTIONAL_CONTRACT/PAGE/FUNCTIONAL_CHAIN_SPEC.yaml")
        target = root / owner
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("artifact_type: FUNCTIONAL_CHAIN_SPEC\n", encoding="utf-8")
        material = {
            "material_remediation_started": True,
            "exact_materialized_closure_count_pending_revalidation": 1,
            "product_blocker_credit": 0,
        }
        assert blocked_product_root_continuity_error(
            root_present=True,
            evidence_root_present=False,
            material=material,
            revalidation_mode=True,
            canonical_owner_ref=str(owner),
            repo_root=root,
        ) is None
        assert blocked_product_root_continuity_error(
            root_present=True,
            evidence_root_present=False,
            material=material,
            revalidation_mode=False,
            canonical_owner_ref=str(owner),
            repo_root=root,
        ) == "BLOCKED_PRODUCT_ROOT_EVIDENCE_MISMATCH"
        bad_credit = dict(material)
        bad_credit["product_blocker_credit"] = 1
        assert blocked_product_root_continuity_error(
            root_present=True,
            evidence_root_present=False,
            material=bad_credit,
            revalidation_mode=True,
            canonical_owner_ref=str(owner),
            repo_root=root,
        ) == "REVALIDATION_PRODUCT_ROOT_PREMATURE_PRODUCT_CREDIT"
        assert blocked_product_root_continuity_error(
            root_present=True,
            evidence_root_present=False,
            material=material,
            revalidation_mode=True,
            canonical_owner_ref="missing/FUNCTIONAL_CHAIN_SPEC.yaml",
            repo_root=root,
        ) == "REVALIDATION_PRODUCT_ROOT_CANONICAL_OWNER_NOT_MATERIALIZED"
    print("PASS: Stage-02 revalidation product-root continuity remains fail-closed")


if "--self-test-revalidation-root-continuity" in sys.argv:
    self_test_revalidation_root_continuity()
    raise SystemExit(0)


state = load_yaml(STATE, "ACTIVE_STATE")
execution = state.get("execution") or {}
stage1 = execution.get("stage1") or {}
stage2 = execution.get("stage2") or {}
result = stage2.get("result")

if not isinstance(stage1, dict) or not stage1 or any(v != "PASS" for v in stage1.values()):
    die(f"STAGE1_CLOSURE_CONTINUITY_MISSING:{stage1!r}")
if execution.get("website_construction_allowed") is not False:
    die("WEBSITE_CONSTRUCTION_MUST_REMAIN_BLOCKED")
if execution.get("deployment_allowed") is not False:
    die("DEPLOYMENT_MUST_REMAIN_BLOCKED")

if result == "NOT_EXECUTED":
    cp = subprocess.run([sys.executable, str(ZERO)], cwd=str(ROOT), text=True)
    if cp.returncode != 0:
        die("STAGE2_PREDECESSOR_ZERO_RESIDUAL_FAILED")
    print("PASS: Stage-02 predecessor state is NOT_EXECUTED and zero-residual")
    raise SystemExit(0)

if result not in {"TEST_EXECUTED_BLOCKED", "TEST_EXECUTED_PASS"}:
    die(f"UNKNOWN_STAGE2_RESULT:{result!r}")

runtime = state.get("stage2_result_evidence") or {}
required_runtime = {
    "mode": "RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT",
    "static_result_pointer_required": False,
    "static_run_id_copy_forbidden": True,
    "static_head_sha_copy_forbidden": True,
    "static_specification_digest_copy_forbidden": True,
}
for key, expected in required_runtime.items():
    if runtime.get(key) != expected:
        die(f"STAGE2_RUNTIME_EVIDENCE_CONTRACT:{key}:expected={expected!r}:actual={runtime.get(key)!r}")

if not EVIDENCE.is_file():
    die("STAGE2_LATEST_TEST_EVIDENCE_MISSING")
try:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
except Exception as exc:
    die(f"STAGE2_LATEST_TEST_EVIDENCE_PARSE_ERROR:{exc!r}")

required = {
    "stage_uid": "STAGE-02",
    "actual_product_stage_test_started": True,
    "actual_product_stage_test_completed": True,
    "current_specification_mutated": False,
    "ai_autofill_used": False,
    "inference_used": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
}
for key, expected in required.items():
    if evidence.get(key) != expected:
        die(f"STAGE2_EVIDENCE_FIELD:{key}:expected={expected!r}:actual={evidence.get(key)!r}")

active = state.get("stage02_active_attempt") or {}
findings = load_yaml(FINDINGS, "STAGE02_CURRENT_FINDINGS")
candidate_ledger = load_yaml(CANDIDATES, "SPECIFICATION_CHANGE_CANDIDATES")
candidate = candidate_ledger.get("current_stage2_execution") or {}
if not active:
    die("EXECUTED_STAGE2_REQUIRES_ACTIVE_ATTEMPT")
if not candidate:
    die("EXECUTED_STAGE2_REQUIRES_CURRENT_CANDIDATE_PROJECTION")

identity_checks = {
    "attempt_uid": (active.get("attempt_uid"), findings.get("attempt_uid"), candidate.get("attempt_uid")),
    "frozen_governance_uid": (
        active.get("frozen_governance_uid"), findings.get("frozen_governance_uid"), candidate.get("frozen_governance_uid"),
    ),
    "source_execution_sha": (
        active.get("source_execution_sha"), findings.get("source_head_sha"), candidate.get("source_execution_sha"),
    ),
    "source_workflow_run_id": (
        active.get("source_workflow_run_id"), findings.get("source_workflow_run_id"), candidate.get("source_workflow_run_id"),
    ),
    "source_artifact_id": (
        active.get("source_artifact_id"), findings.get("source_artifact_id"), candidate.get("source_artifact_id"),
    ),
    "source_artifact_sha256": (
        active.get("source_artifact_sha256"), findings.get("source_artifact_sha256"), candidate.get("source_artifact_sha256"),
    ),
}
for key, values in identity_checks.items():
    if any(v in (None, "") for v in values) or len(set(values)) != 1:
        die(f"STAGE2_CURRENT_PROJECTOR_IDENTITY_DRIFT:{key}:{values!r}")

current_governance_uid = state.get("specification_uid")
frozen_governance_uid = active.get("frozen_governance_uid")
promotion_revalidation = bool(stage2.get("revalidation_required_under_current_governance"))
if frozen_governance_uid != current_governance_uid:
    if not promotion_revalidation:
        die(f"STAGE2_ACTIVE_ATTEMPT_GOVERNANCE_UID_DRIFT_WITHOUT_REVALIDATION:frozen={frozen_governance_uid}:current={current_governance_uid}")
    if active.get("fresh_revalidation_required") is not True:
        die("PROMOTED_GOVERNANCE_REQUIRES_ACTIVE_ATTEMPT_FRESH_REVALIDATION")
    if active.get("closure_credit_under_current_governance") is not False:
        die("PREDECESSOR_ATTEMPT_CANNOT_RECEIVE_CURRENT_GOVERNANCE_CLOSURE_CREDIT")
    if result == "TEST_EXECUTED_PASS":
        if not evidence.get("stage_scope_complete"):
            die("PARTIAL_SCOPE_CANNOT_RECEIVE_STAGE2_PASS")
        die("PREDECESSOR_ATTEMPT_CANNOT_PROJECT_CURRENT_STAGE_PASS_AFTER_GOVERNANCE_PROMOTION")
else:
    if promotion_revalidation and active.get("closure_credit_under_current_governance") is True:
        die("REVALIDATION_FLAG_CONFLICTS_WITH_CURRENT_CLOSURE_CREDIT")

if evidence.get("source_head_sha") != active.get("source_execution_sha"):
    die("STAGE2_EVIDENCE_SOURCE_SHA_DRIFT")

fresh_gap_total = int(evidence.get("fresh_functional_gap_total") or 0)
closure_total = int(evidence.get("closure_blocker_total") or 0)
count_checks = {
    "fresh_functional_gap_total": (int(active.get("fresh_functional_gap_total") or 0), int(findings.get("fresh_functional_gap_total") or 0), int(candidate.get("raw_discovery_gap_count") or 0), fresh_gap_total),
    "fresh_closure_blocker_total": (int(active.get("fresh_closure_blocker_total") or 0), int(findings.get("fresh_closure_blocker_total") or 0), int(candidate.get("current_closure_blocker_count") or 0), closure_total),
    "preserved_external_authority_union_count": (int(active.get("preserved_external_authority_union_count") or 0), int(findings.get("preserved_external_authority_union_count") or 0), int(candidate.get("preserved_external_authority_union_count") or 0), int(evidence.get("preserved_external_authority_union_count") or 0)),
    "official_stage_output_denominator_count": (int(active.get("official_stage_output_denominator_count") or 0), int(findings.get("official_stage_output_denominator_count") or 0), int(candidate.get("official_stage_output_denominator_count") or 0), len(evidence.get("official_stage_output_denominator") or [])),
    "current_manifest_mandatory_stage_output_subset_count": (int(active.get("current_manifest_mandatory_stage_output_subset_count") or 0), int(findings.get("current_manifest_mandatory_stage_output_subset_count") or 0), int(candidate.get("current_manifest_mandatory_stage_output_subset_count") or 0), len(evidence.get("execution_profile_mandatory_output_subset") or [])),
}
for key, values in count_checks.items():
    if len(set(values)) != 1:
        die(f"STAGE2_CURRENT_PROJECTOR_COUNT_DRIFT:{key}:{values!r}")

active_work = state.get("active_work_unit") or {}
resume = state.get("resume_control") or {}
common_engine_interrupt = active_work.get("current_status") == "IN_PROGRESS_COMMON_ENGINE_INTERRUPT"
if common_engine_interrupt:
    work_uid = active_work.get("work_unit_uid")
    work_owner = active_work.get("canonical_owner")
    interrupt_action = state.get("next_action")
    if not work_uid or not work_owner or not interrupt_action:
        die("COMMON_ENGINE_INTERRUPT_IDENTITY_INCOMPLETE")
    if resume.get("current_work_unit_uid") != work_uid or resume.get("current_owner") != work_owner:
        die("COMMON_ENGINE_INTERRUPT_RESUME_IDENTITY_DRIFT")
    if resume.get("exact_next_action") != interrupt_action or active.get("next_action") != interrupt_action:
        die("COMMON_ENGINE_INTERRUPT_NEXT_ACTION_DRIFT")
    parent_actions = (findings.get("next_action"), candidate.get("next_action"))
    if any(v in (None, "") for v in parent_actions) or len(set(parent_actions)) != 1:
        die(f"COMMON_ENGINE_INTERRUPT_PARENT_PROJECTOR_DRIFT:{parent_actions!r}")
    if not resume.get("parent_resume_point") or resume.get("current_resume_point") == resume.get("parent_resume_point"):
        die("COMMON_ENGINE_INTERRUPT_PARENT_RESUME_MISSING")
    if active_work.get("product_blocker_credit") != 0:
        die("COMMON_ENGINE_INTERRUPT_PRODUCT_BLOCKER_CREDIT_FORBIDDEN")
else:
    next_actions = (state.get("next_action"), active.get("next_action"), findings.get("next_action"), candidate.get("next_action"))
    if any(v in (None, "") for v in next_actions) or len(set(next_actions)) != 1:
        die(f"STAGE2_CURRENT_PROJECTOR_NEXT_ACTION_DRIFT:{next_actions!r}")

for key in ("stage_exit_allowed", "website_construction_allowed", "deployment_allowed"):
    expected = False if result == "TEST_EXECUTED_BLOCKED" else True if key == "stage_exit_allowed" else False
    if candidate.get(key) is not expected:
        die(f"STAGE2_CANDIDATE_GATE_DRIFT:{key}:expected={expected!r}:actual={candidate.get(key)!r}")

if result == "TEST_EXECUTED_BLOCKED":
    if candidate.get("state") != "TEST_EXECUTED_BLOCKED": die("BLOCKED_CANDIDATE_STATE_MISMATCH")
    if findings.get("result") != "BLOCKED": die("BLOCKED_FINDINGS_RESULT_MISMATCH")
    if evidence.get("result") != "BLOCKED" or evidence.get("stage_exit_allowed") is not False: die("BLOCKED_STATE_EVIDENCE_MISMATCH")
    if execution.get("current_stage") != "STAGE-02-TESTED-BLOCKED": die("BLOCKED_STATE_CURRENT_STAGE_MISMATCH")
    pages = evidence.get("pages") or {}
    target_pages = evidence.get("target_pages") or []
    if not isinstance(target_pages, list) or not target_pages: die("STAGE2_TARGET_PAGE_SCOPE_MISSING")
    if set(pages) != set(target_pages): die("STAGE2_PAGE_DENOMINATOR_MISMATCH")
    if not set(target_pages).issubset(set(stage1)): die("STAGE2_TARGET_PAGE_SCOPE_OUTSIDE_STAGE1")
    if evidence.get("stage_scope_complete") is not (set(target_pages) == set(stage1)): die("STAGE2_SCOPE_COMPLETENESS_DRIFT")
    root_present = stage2.get("artifact_root_present")
    material = state.get("stage02_material_remediation") or {}
    revalidation_mode = os.environ.get("STAGE02_REVALIDATION_MODE", "").strip() == "1"
    root_error = blocked_product_root_continuity_error(
        root_present=root_present,
        evidence_root_present=evidence.get("physical_stage2_product_artifact_root_present"),
        material=material,
        revalidation_mode=revalidation_mode,
        canonical_owner_ref=active_work.get("canonical_owner"),
    )
    if root_error:
        die(root_error)
    if root_present is True and evidence.get("physical_stage2_product_artifact_root_present") is not True and revalidation_mode:
        print("PASS: bounded remediation materialized a Current product root after predecessor evidence; fresh revalidation remains required before product credit")
    effective = evidence.get("effective_functional_gap_total")
    blocking_functional = int(effective if effective is not None else fresh_gap_total)
    scope_incomplete = evidence.get("stage_scope_complete") is False and bool(evidence.get("remaining_pages"))
    if blocking_functional <= 0 and closure_total <= 0 and not scope_incomplete:
        die("BLOCKED_STATE_WITHOUT_EFFECTIVE_OR_STRUCTURAL_BLOCKERS_OR_REMAINING_SCOPE")
    if blocking_functional <= 0 and closure_total <= 0 and scope_incomplete:
        page_effective = [int((rec or {}).get("effective_functional_gap_count") or 0) for rec in (pages or {}).values()]
        if any(page_effective):
            die("PARTIAL_SCOPE_EFFECTIVE_ZERO_DECLARATION_DRIFT")
else:
    if candidate.get("state") != "TEST_EXECUTED_PASS": die("PASS_CANDIDATE_STATE_MISMATCH")
    if evidence.get("result") != "PASS" or evidence.get("stage_exit_allowed") is not True: die("PASS_STATE_EVIDENCE_MISMATCH")
    if execution.get("current_stage") != "STAGE-02-CLOSED": die("PASS_STATE_CURRENT_STAGE_MISMATCH")
    if stage2.get("artifact_root_present") is not True: die("PASS_STATE_REQUIRES_PRODUCT_ARTIFACT_ROOT")

print(f"PASS: Stage-02 successor state integrity result={result}")
print("PASS: Stage-01 closure continuity retained")
print("PASS: ACTIVE_STATE, findings, evidence, and candidate projectors remain identity/count synchronized")
if frozen_governance_uid != current_governance_uid:
    print("PASS: predecessor frozen attempt retained as provenance only; Current governance closure credit invalidated pending fresh revalidation")
if common_engine_interrupt:
    print(f"PASS: governance/common-engine interrupt work_unit={active_work.get('work_unit_uid')} preserves parent product projector with zero product credit")
print("PASS: website construction and deployment remain fail-closed")
