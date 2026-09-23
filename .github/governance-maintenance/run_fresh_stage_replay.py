#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json\nimport os
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".github/governance-source/active/source"
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"
SCOPE = ROOT / "governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml"
REGISTRY = ROOT / "governance/specifications/REGISTRY.yaml"
CURRENT_ENTRY = ROOT / "GOVERNANCE_CURRENT.yaml"
LIFECYCLE = ROOT / ".github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml"
COMMON_ENGINE = ROOT / "governance/ci/stage_execution_engine.py"
RUNNER_OWNER = ".github/governance-maintenance/run_fresh_stage_replay.py"


def load(path: Path) -> dict:
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def repo_rel(value: str, label: str) -> str:
    p = Path(str(value))
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise RuntimeError(f"{label}_INVALID_PATH:{value}")
    return p.as_posix()


def stage_map(profile: dict) -> dict[str, dict]:
    rows = profile.get("stages") or []
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("LIFECYCLE_STAGE_REGISTRY_EMPTY")
    out: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("stage_uid"):
            raise RuntimeError("LIFECYCLE_STAGE_RECORD_INVALID")
        uid = str(row["stage_uid"])
        if uid in out:
            raise RuntimeError("LIFECYCLE_STAGE_UID_DUPLICATE:" + uid)
        out[uid] = row
    return out


def resolve_execution_context_docs(state: dict, scope: dict, registry: dict, current: dict, lifecycle: dict) -> dict:
    active_spec = registry.get("active_specification") or {}
    governance_uid = str(active_spec.get("governance_uid") or "")
    display_version = str(active_spec.get("display_version") or "")
    if not governance_uid or not display_version:
        raise RuntimeError("CURRENT_GOVERNANCE_IDENTITY_INCOMPLETE")
    if current.get("active_governance_uid") != governance_uid or current.get("display_version") != display_version:
        raise RuntimeError("CURRENT_ENTRY_REGISTRY_DRIFT")
    if state.get("specification_uid") != governance_uid:
        raise RuntimeError("ACTIVE_STATE_GOVERNANCE_DRIFT")
    if state.get("current_primary_task_layer") != "PRODUCT_STAGE_EXECUTION":
        raise RuntimeError("ACTIVE_STAGE_EXECUTION_REQUIRES_PRODUCT_STAGE_TASK_LAYER")

    work = state.get("active_work_unit")
    if not isinstance(work, dict):
        raise RuntimeError("ACTIVE_PRODUCT_WORK_UNIT_MISSING")
    if work.get("primary_task_layer") != "PRODUCT_STAGE_EXECUTION":
        raise RuntimeError("ACTIVE_WORK_UNIT_TASK_LAYER_DRIFT")

    stage_uid = str(work.get("stage_uid") or "")
    stages = stage_map(lifecycle)
    if stage_uid not in stages:
        raise RuntimeError("ACTIVE_WORK_UNIT_STAGE_NOT_IN_LIFECYCLE:" + stage_uid)
    stage = stages[stage_uid]

    page_scope = work.get("scope")
    if not isinstance(page_scope, list) or not page_scope or not all(isinstance(x, str) and x for x in page_scope):
        raise RuntimeError("ACTIVE_WORK_UNIT_SCOPE_INVALID")
    if scope.get("included_units") != page_scope:
        raise RuntimeError("CURRENT_SCOPE_INCLUDED_UNITS_DRIFT")
    excluded = scope.get("excluded_units") or []
    if not isinstance(excluded, list):
        raise RuntimeError("CURRENT_SCOPE_EXCLUDED_UNITS_INVALID")
    if scope.get("governance_uid") != governance_uid:
        raise RuntimeError("CURRENT_SCOPE_GOVERNANCE_DRIFT")

    execution = state.get("execution") or {}
    run_uid = str(execution.get("run_uid") or "")
    if not run_uid:
        raise RuntimeError("CURRENT_EXECUTION_RUN_UID_MISSING")
    branch = str(execution.get("branch") or "")
    if not branch:
        raise RuntimeError("CURRENT_EXECUTION_BRANCH_MISSING")

    run_root = repo_rel(str(work.get("planned_run_root") or ""), "PLANNED_RUN_ROOT")
    if not run_root.startswith("00_SOURCE_INTAKE/"):
        raise RuntimeError("PLANNED_RUN_ROOT_OUTSIDE_SOURCE_INTAKE")

    expected_ops = [str(x) for x in (stage.get("operations") or [])]
    op_bindings = work.get("operation_bindings")
    if not isinstance(op_bindings, dict) or set(map(str, op_bindings)) != set(expected_ops):
        raise RuntimeError("ACTIVE_WORK_UNIT_OPERATION_BINDING_COVERAGE_INVALID")
    for op in expected_ops:
        binding = op_bindings.get(op)
        if not isinstance(binding, dict) or binding.get("executor_owner") != RUNNER_OWNER or not binding.get("result_owner"):
            raise RuntimeError("ACTIVE_WORK_UNIT_OPERATION_OWNER_DRIFT:" + op)

    required_outputs = set(map(str, stage.get("outputs") or []))
    declared_outputs = set(map(str, work.get("required_outputs") or []))
    if required_outputs != declared_outputs:
        raise RuntimeError("ACTIVE_WORK_UNIT_OUTPUT_DENOMINATOR_DRIFT")

    load_receipt_ref = repo_rel(str(work.get("governance_load_receipt_ref") or ""), "GOVERNANCE_LOAD_RECEIPT_REF")
    load_target_ref = repo_rel(str(work.get("governance_load_target_manifest_ref") or ""), "GOVERNANCE_LOAD_TARGET_MANIFEST_REF")
    source_projection_admission = work.get("source_projection_admission") or {"applicability": "NOT_APPLICABLE", "bindings": []}
    if not isinstance(source_projection_admission, dict):
        raise RuntimeError("SOURCE_PROJECTION_ADMISSION_INVALID")

    return {
        "governance_uid": governance_uid,
        "display_version": display_version,
        "branch": branch,
        "run_uid": run_uid,
        "run_root": run_root,
        "work_unit_uid": str(work.get("work_unit_uid") or ""),
        "stage_uid": stage_uid,
        "stage_name": str(stage.get("name") or ""),
        "page_scope": list(page_scope),
        "excluded_page_scope": list(excluded),
        "authorization_uid": str(state.get("current_primary_task_authorization_uid") or ""),
        "governance_load_receipt_ref": load_receipt_ref,
        "governance_load_target_manifest_ref": load_target_ref,
        "source_projection_admission": source_projection_admission,
        "scope_kind": str(scope.get("scope_kind") or ""),
        "next_stage_uid": stage.get("next_stage_uid"),
    }


def resolve_execution_context() -> dict:
    ctx = resolve_execution_context_docs(
        load(STATE),
        load(SCOPE),
        load(REGISTRY),
        load(CURRENT_ENTRY),
        load(LIFECYCLE),
    )
    for key in ("work_unit_uid", "authorization_uid"):
        if not ctx.get(key):
            raise RuntimeError("CURRENT_EXECUTION_CONTEXT_FIELD_MISSING:" + key)

    receipt_path = ROOT / ctx["governance_load_receipt_ref"]
    target_path = ROOT / ctx["governance_load_target_manifest_ref"]
    if not receipt_path.is_file() or not target_path.is_file():
        raise RuntimeError("GOVERNANCE_LOAD_EVIDENCE_MISSING")
    receipt = load(receipt_path)
    target = load(target_path)
    if receipt.get("status") != "PASS":
        raise RuntimeError("GOVERNANCE_LOAD_RECEIPT_NOT_PASS")
    if target.get("status") != "PREEXECUTION_TARGET_FROZEN":
        raise RuntimeError("STAGE_EXECUTION_LOAD_TARGET_NOT_FROZEN")
    if target.get("work_unit_uid") != ctx["work_unit_uid"] or target.get("stage_uid") != ctx["stage_uid"]:
        raise RuntimeError("STAGE_EXECUTION_LOAD_TARGET_IDENTITY_DRIFT")
    if target.get("execution_run_uid") != ctx["run_uid"] or target.get("governance_uid") != ctx["governance_uid"]:
        raise RuntimeError("STAGE_EXECUTION_LOAD_TARGET_RUN_OR_GOVERNANCE_DRIFT")
    return ctx


def identity_self_test() -> None:
    source_before = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    lifecycle = {
        "stages": [
            {
                "stage_uid": "SYNTH-STAGE-A",
                "name": "SYNTH",
                "operations": ["OP-A"],
                "outputs": ["OUT-A"],
                "next_stage_uid": "SYNTH-STAGE-B",
            }
        ]
    }
    work = {
        "work_unit_uid": "WU-SYNTH",
        "primary_task_layer": "PRODUCT_STAGE_EXECUTION",
        "stage_uid": "SYNTH-STAGE-A",
        "scope": ["SYNTH-PAGE"],
        "planned_run_root": "00_SOURCE_INTAKE/synth-run",
        "required_outputs": ["OUT-A"],
        "operation_bindings": {
            "OP-A": {"executor_owner": RUNNER_OWNER, "result_owner": "synthetic/result.yaml"}
        },
        "governance_load_receipt_ref": "synthetic/load.yaml",
        "governance_load_target_manifest_ref": "synthetic/target.yaml",
    }
    state = {
        "specification_uid": "GOV-SYNTH",
        "current_primary_task_layer": "PRODUCT_STAGE_EXECUTION",
        "current_primary_task_authorization_uid": "AUTH-SYNTH",
        "active_work_unit": work,
        "execution": {"run_uid": "RUN-SYNTH", "branch": "synthetic"},
    }
    scope = {
        "governance_uid": "GOV-SYNTH",
        "included_units": ["SYNTH-PAGE"],
        "excluded_units": [],
        "scope_kind": "SYNTH",
    }
    synth_version = "v" + "0.0.0"
    registry = {"active_specification": {"governance_uid": "GOV-SYNTH", "display_version": synth_version}}
    current = {"active_governance_uid": "GOV-SYNTH", "display_version": synth_version}
    ctx = resolve_execution_context_docs(state, scope, registry, current, lifecycle)
    source_after = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if ctx["stage_uid"] != "SYNTH-STAGE-A" or ctx["work_unit_uid"] != "WU-SYNTH" or source_before != source_after:
        raise RuntimeError("ACTIVE_WORK_UNIT_CONTEXT_SELF_TEST_FAILED")
    print(json.dumps({
        "result": "PASS",
        "driver_binding_source": "ACTIVE_WORK_UNIT",
        "stage_uid": ctx["stage_uid"],
        "work_unit_uid": ctx["work_unit_uid"],
        "executable_sha256": source_before,
        "executable_bytes_equal": True,
    }, ensure_ascii=False, indent=2))


def verify_frozen_projection_admission(ctx: dict) -> None:
    admission = ctx.get("source_projection_admission") or {}
    applicability = str(admission.get("applicability") or "NOT_APPLICABLE")
    bindings = admission.get("bindings") or []
    if applicability != "REQUIRED":
        return
    if not isinstance(bindings, list) or not bindings:
        raise RuntimeError("REQUIRED_SOURCE_PROJECTION_BINDING_MISSING")
    scope = load(SCOPE)
    scope_binding = scope.get("source_projection_binding") or {}
    for binding in bindings:
        if not isinstance(binding, dict):
            raise RuntimeError("SOURCE_PROJECTION_BINDING_INVALID")
        for key in ("source_uid", "freeze_receipt_ref", "pair_hash", "raw_source_sha256", "projection_uid", "projection_content_hash"):
            if not binding.get(key):
                raise RuntimeError("SOURCE_PROJECTION_BINDING_FIELD_MISSING:" + key)
        freeze_path = ROOT / repo_rel(binding["freeze_receipt_ref"], "FREEZE_RECEIPT_REF")
        if not freeze_path.is_file():
            raise RuntimeError("SOURCE_PROJECTION_FREEZE_RECEIPT_MISSING:" + str(binding["source_uid"]))
        freeze = load(freeze_path)
        if freeze.get("status") != "FROZEN_FOR_STAGE01" or freeze.get("lock_state") != "SOURCE_PAIR_FROZEN":
            raise RuntimeError("SOURCE_PROJECTION_PAIR_NOT_FROZEN:" + str(binding["source_uid"]))
        for key in ("pair_hash", "raw_source_sha256", "projection_uid", "projection_content_hash"):
            if freeze.get(key) != binding.get(key):
                raise RuntimeError("SOURCE_PROJECTION_FREEZE_BINDING_DRIFT:" + str(binding["source_uid"]) + ":" + key)
        if scope_binding and str(scope_binding.get("source_uid") or "") == str(binding["source_uid"]):
            for key in ("pair_hash", "raw_source_sha256", "projection_uid", "projection_content_hash"):
                if scope_binding.get(key) != binding.get(key):
                    raise RuntimeError("SCOPE_SOURCE_PROJECTION_BINDING_DRIFT:" + key)
        projection_path = freeze_path.parent / "CANONICAL_SOURCE_PROJECTION.yaml"
        if not projection_path.is_file():
            raise RuntimeError("CANONICAL_SOURCE_PROJECTION_MISSING:" + str(binding["source_uid"]))


def run_common_engine_admission(stage_uid: str) -> None:
    subprocess.run(
        [sys.executable, str(COMMON_ENGINE), "--admission-check", "--stage", stage_uid],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    if "--identity-self-test" in sys.argv:
        identity_self_test()
        return

    ctx = resolve_execution_context()
    if "--execute" in sys.argv and os.environ.get("ACPOS_COMMON_STAGE_ENGINE_EXECUTION") != "1":
        raise RuntimeError("DIRECT_EFFECTFUL_INVOCATION_FORBIDDEN_USE_COMMON_STAGE_ENGINE")
    if not any(x in sys.argv for x in ("--print-context-json", "--print-context-github-output")) and "--execute" not in sys.argv:
        raise RuntimeError("DIRECT_EFFECTFUL_INVOCATION_FORBIDDEN_USE_COMMON_STAGE_ENGINE")
    if "--print-context-json" in sys.argv:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
        return
    if "--print-context-github-output" in sys.argv:
        print("run_uid=" + ctx["run_uid"])
        print("run_root=" + ctx["run_root"])
        print("authorization_uid=" + ctx["authorization_uid"])
        print("stage_uid=" + ctx["stage_uid"])
        print("work_unit_uid=" + ctx["work_unit_uid"])
        print("artifact_name=" + re.sub(r"[^A-Za-z0-9_.-]+", "-", ctx["run_uid"]).strip("-").lower())
        return

    run_common_engine_admission(ctx["stage_uid"])
    verify_frozen_projection_admission(ctx)

    # Effectful semantic execution is deliberately fail-closed until the registered
    # Active-Stage executor consumes the frozen projection/inputs defined by the
    # Current Work Unit. Re-introducing a legacy replay context, raw YAML shortcut,
    # raw DOCX semantic parse, or direct successor-stage execution is forbidden.
    raise RuntimeError(
        "ACTIVE_STAGE_SEMANTIC_EXECUTOR_NOT_YET_MIGRATED_TO_CURRENT_WORK_UNIT_INPUT_CONTRACT:"
        + ctx["stage_uid"]
    )


if __name__ == "__main__":
    main()
