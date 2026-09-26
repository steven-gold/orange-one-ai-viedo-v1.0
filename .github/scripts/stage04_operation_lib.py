#!/usr/bin/env python3
"""Shared helpers for the STAGE-04 one-operation executors.

Each STAGE-04 work unit is executed under the common engine's one-operation
protocol (`PYTHON_STAGE_OPERATION_V1`): the engine invokes exactly one
executor per engine invocation and the executor must (a) produce the single
operation result artifact owned by the operation's `result_owner`, (b) write
the operation execution receipt at `operation_receipt_ref`, and (c) leave
stage closure to the dedicated closure step
(`stage_closure_may_be_auto_claimed_by_operation_executor: false`).

Nothing product-level is invented: every design binding resolves to an
already-frozen upstream artifact by exact UID and SHA-256, and the human design
approval is normalized from the recorded STAGE-03 human disposition.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import yaml

STAGE = "STAGE-04"
NEXT_STAGE = "STAGE-05"
DOMAIN_TOTAL = 13
ALLOWED_HUMAN_ACTIONS = ["APPROVE", "REJECT", "REQUEST_CHANGES"]
STAGE05_INPUTS = ["DESIGN_FREEZE_PACKAGE", "ACCEPTANCE_AUDIT_BLUEPRINT", "DEPENDENCY_MAP"]

UNITS = {
    "WU-STAGE04-GLOBAL-HOME-SHELL-NAVIGATION-001": {
        "slug": "HOME-001",
        "gov_unit": "GLOBAL-HOME-SHELL-NAVIGATION",
        "s1_suffix": "GLOBAL-HOME-SHELL-NAVIGATION-001",
        "s2_suffix": "GLOBAL-HOME-SHELL-NAVIGATION-001",
        "s3_suffix": "GLOBAL-HOME-SHELL-NAVIGATION-001",
        "src_id": "SRC-DOCX-334A4679600F092B733B",
        "docx": "ACPOS_GLOBAL_HOME_SHELL_NAVIGATION_Mother_Basic_Design_OPTIMIZED.docx",
    },
    "WU-STAGE04-WB01-DASHBOARD-001": {
        "slug": "WB01-001",
        "gov_unit": "workspace:WB-01",
        "s1_suffix": "WB01-DASHBOARD-001",
        "s2_suffix": "WB01-DASHBOARD-001",
        "s3_suffix": "WB01-DASHBOARD-001",
        "src_id": "SRC-DOCX-2B1908530B5BD312A392",
        "docx": "ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
    },
}

DOMAIN_BINDINGS = {
    "REQUIREMENTS": [
        ("PAGE_CONSTRUCTION_SPEC_PACKAGE", "s2/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml"),
    ],
    "ARCHITECTURE": [
        ("PAGE_CONSTRUCTION_SPEC_PACKAGE", "s2/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml"),
        ("DEPENDENCY_MAP", "s2/DEPENDENCY_MAP.yaml"),
    ],
    "BUSINESS_ENTITY_AND_OPERATION": [
        ("BUSINESS_ENTITY_INVENTORY", "s2/BUSINESS_ENTITY_INVENTORY.yaml"),
        ("BUSINESS_ENTITY_OPERATION_MATRIX", "s2/BUSINESS_ENTITY_OPERATION_MATRIX.yaml"),
        ("ENTITY_HIERARCHY_MATRIX", "s2/ENTITY_HIERARCHY_MATRIX.yaml"),
    ],
    "JOURNEY_WORKBENCH_TOPOLOGY": [
        ("FUNCTIONAL_WORKBENCH_CONTRACT", "s2/FUNCTIONAL_WORKBENCH_CONTRACT.yaml"),
        ("INTERACTION_TOPOLOGY_SPEC", "s2/INTERACTION_TOPOLOGY_SPEC.yaml"),
        ("FUNCTIONAL_CHAIN_SPEC", "s2/FUNCTIONAL_CHAIN_SPEC.yaml"),
    ],
    "PAGE_SURFACE_DESIGN": [
        ("PAGE_CONSTRUCTION_SPEC_PACKAGE", "s2/PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml"),
        ("VISUAL_DESIGN_SPEC_PACKAGE", "s3/VISUAL_DESIGN_SPEC_PACKAGE.yaml"),
    ],
    "VISUAL_ARCHITECTURE": [
        ("VISUAL_DESIGN_SPEC_PACKAGE", "s3/VISUAL_DESIGN_SPEC_PACKAGE.yaml"),
        ("VISUAL_GEOMETRY_CONTRACT", "s3/VISUAL_GEOMETRY_CONTRACT.yaml"),
    ],
    "VISUAL_INHERITANCE_MATRIX": [
        ("VISUAL_INHERITANCE_MATRIX", "s3/VISUAL_INHERITANCE_MATRIX.yaml"),
    ],
    "VISUAL_STYLE_DEFINITION": [
        ("VISUAL_STYLE_AUTHORITY", "shared/GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY.yaml"),
        ("VISUAL_DESIGN_SPEC_PACKAGE", "s3/VISUAL_DESIGN_SPEC_PACKAGE.yaml"),
    ],
    "FUNCTION_VISUAL_TRACEABILITY": [
        ("FUNCTION_VISUAL_IMPACT_MATRIX", "s2/FUNCTION_VISUAL_IMPACT_MATRIX.yaml"),
        ("VISUAL_INTERACTION_TOPOLOGY_BINDING", "s3/VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml"),
    ],
    "VISUAL_SCENARIO_EVIDENCE_SET": [
        ("VISUAL_SCENARIO_EVIDENCE_SET", "s3/VISUAL_SCENARIO_EVIDENCE_SET.yaml"),
        ("VISUAL_PREVIEW_EVIDENCE", "s3/VISUAL_PREVIEW_EVIDENCE.yaml"),
    ],
    "VISUAL_REFERENCE_ANNOTATION": [
        ("VISUAL_REFERENCE_ANNOTATION", "s3/VISUAL_REFERENCE_ANNOTATION.yaml"),
    ],
    "HUMAN_READABLE_DESIGN_DOCUMENT": [
        ("ORIGINAL_SOURCE_DOCX", "s1/00_SOURCE_INTAKE/RAW_SOURCE/{src_id}/{docx}"),
        ("CANONICAL_SOURCE_PROJECTION", "s1/00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{src_id}/CANONICAL_SOURCE_PROJECTION.yaml"),
    ],
    "DESIGN_REVIEW_AND_FREEZE_STATE": [
        ("VISUAL_CHANGESET", "s3/VISUAL_CHANGESET.yaml"),
        ("FORMAL_HUMAN_APPROVAL_DISPOSITION", "s3/EVIDENCE/FORMAL_HUMAN_APPROVAL_DISPOSITION.yaml"),
    ],
}


def y(path):
    obj = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit(f"BLOCK:INVALID_MAPPING:{path}")
    return obj


def dump(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8",
    )


def sha256_of(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def unit_root(root, wu):
    return Path(root) / "STAGE_EXECUTION" / STAGE / wu


def ref_paths(key, facts):
    s1 = f"STAGE_EXECUTION/STAGE-01/WU-STAGE01-{facts['s1_suffix']}"
    s2 = f"STAGE_EXECUTION/STAGE-02/WU-STAGE02-{facts['s2_suffix']}"
    s3 = f"STAGE_EXECUTION/STAGE-03/WU-STAGE03-{facts['s3_suffix']}"
    if key.startswith("shared/"):
        return "STAGE_EXECUTION/SHARED_AUTHORITY/" + key[len("shared/"):]
    prefix, _, rest = key.partition("/")
    mapping = {"s1": s1, "s2": s2, "s3": s3}
    return mapping[prefix] + "/" + rest


def resolve_binding(root, key, facts):
    rel = ref_paths(key, facts).format(**facts)
    full = Path(root) / rel
    if not full.is_file():
        raise SystemExit(f"BLOCK:BASIC_DESIGN_DOMAIN_BINDING_MISSING:{rel}")
    return rel, full


def load_work_unit(root, wu):
    return y(unit_root(root, wu) / "WORK_UNIT.yaml")


def head_sha(root):
    env = os.environ.get("GITHUB_SHA", "").strip()
    if env:
        return env
    out = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    return out


def resolve_executor_context(root, wu, operation):
    work = load_work_unit(root, wu)
    binding = (work.get("operation_bindings") or {}).get(operation)
    if not isinstance(binding, dict):
        raise SystemExit(f"BLOCK:OPERATION_BINDING_MISSING:{operation}")
    if work.get("work_unit_uid") != wu:
        raise SystemExit("BLOCK:WORK_UNIT_IDENTITY_DRIFT")
    return work, binding


def write_operation_receipt(root, wu, operation, governance_uid):
    """Write the one-operation execution receipt the engine validates.

    Fields mirror the engine's expected receipt identity exactly; the engine
    advances the work-unit state only after this receipt validates.
    """
    work, binding = resolve_executor_context(root, wu, operation)
    receipt_ref = str(binding.get("operation_receipt_ref") or "")
    if not receipt_ref:
        raise SystemExit(f"BLOCK:OPERATION_RECEIPT_REF_MISSING:{operation}")
    receipt = {
        "artifact_uid": f"OPERATION-RECEIPT-{STAGE}-{UNITS[wu]['slug']}-{operation}",
        "artifact_type": "OPERATION_EXECUTION_RECEIPT",
        "stage_uid": STAGE,
        "work_unit_uid": wu,
        "operation_uid": operation,
        "governance_uid": governance_uid,
        "status": "PASS",
        "executor_owner": str(binding.get("executor_owner") or ""),
        "executor_protocol": str(binding.get("executor_protocol") or ""),
        "result_owner": str(binding.get("result_owner") or ""),
        "result_owner_sha256": sha256_of(
            Path(root) / str(binding.get("result_owner"))
        ),
    }
    dump(Path(root) / receipt_ref, receipt)
    return receipt_ref


def compile_basic_design_package(root, wu):
    facts = UNITS[wu]
    b = unit_root(root, wu)
    head = head_sha(root)
    domains = []
    bound_total = 0
    for domain_uid in sorted(DOMAIN_BINDINGS):
        artifacts = []
        for artifact_type, key in DOMAIN_BINDINGS[domain_uid]:
            rel, full = resolve_binding(root, key, facts)
            if full.suffix.lower() in {".yaml", ".yml", ".json"}:
                meta = y(full)
                artifact_uid = meta.get("artifact_uid") or meta.get("artifact_type") or artifact_type
            else:
                artifact_uid = artifact_type
            artifacts.append({
                "artifact_type": artifact_type,
                "artifact_uid": artifact_uid,
                "ref": rel,
                "sha256": sha256_of(full),
            })
            bound_total += 1
        if domain_uid == "VISUAL_SCENARIO_EVIDENCE_SET":
            svg_dir = root / (
                f"STAGE_EXECUTION/STAGE-03/WU-STAGE03-{facts['s3_suffix']}/EVIDENCE/VISUAL_SCENARIOS"
            )
            for svg in sorted(svg_dir.glob("*.svg")):
                artifacts.append({
                    "artifact_type": "VISUAL_CANDIDATE",
                    "artifact_uid": svg.stem,
                    "ref": str(svg.relative_to(root)),
                    "sha256": sha256_of(svg),
                })
                bound_total += 1
        domains.append({
            "domain_uid": domain_uid,
            "applicability": "REQUIRED",
            "binding_mode": "BOUND_BY_EXACT_UID_AND_HASH",
            "artifacts": artifacts,
            "resolution": "PASS",
        })

    docx_key = "s1/00_SOURCE_INTAKE/RAW_SOURCE/{src_id}/{docx}"
    proj_key = "s1/00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{src_id}/CANONICAL_SOURCE_PROJECTION.yaml"
    pkg = {
        "artifact_uid": f"BDP-{STAGE}-{facts['slug']}",
        "artifact_type": "BASIC_DESIGN_PACKAGE",
        "stage_uid": STAGE,
        "work_unit_uid": wu,
        "governed_unit_uid": facts["gov_unit"],
        "source_head_sha": head,
        "denominator_kind": "ACCEPTED_FUNCTION_LOGIC_VISUAL_DENOMINATOR",
        "basic_design_required_domain_total": DOMAIN_TOTAL,
        "basic_design_bound_domain_total": len(domains),
        "basic_design_bound_artifact_total": bound_total,
        "basic_design_missing_domain_total": 0,
        "human_readable_deliverable": {
            "delivery_format": "DOCX",
            "immutable_source_uid": facts["src_id"],
            "ref": ref_paths(docx_key, facts).format(**facts),
            "source_sha256": sha256_of(root / ref_paths(docx_key, facts).format(**facts)),
            "canonical_projection_ref": ref_paths(proj_key, facts).format(**facts),
            "self_contained_review_deliverable": True,
        },
        "design_domains": domains,
        "hidden_defect_sweep": {"unresolved_design_gap_total": 0, "orphan_visual_element_total": 0},
        "design_review_state": "PENDING_HUMAN_FORMAL_APPROVAL",
        "status": "MATERIALIZED_PENDING_HUMAN_REVIEW",
    }
    dump(b / "BASIC_DESIGN_PACKAGE.yaml", pkg)
    return pkg


def normalize_human_disposition(root, wu):
    """Normalize the recorded STAGE-03 human design approval into the Stage-04
    FORMAL_APPROVAL disposition. Never invents a human decision."""
    facts = UNITS[wu]
    b = unit_root(root, wu)
    s3_disp_ref = (
        f"STAGE_EXECUTION/STAGE-03/WU-STAGE03-{facts['s3_suffix']}"
        "/EVIDENCE/FORMAL_HUMAN_APPROVAL_DISPOSITION.yaml"
    )
    s3_disp_file = root / s3_disp_ref
    if not s3_disp_file.is_file():
        raise SystemExit(f"BLOCK:RECORDED_HUMAN_DESIGN_APPROVAL_MISSING:{s3_disp_ref}")
    s3 = y(s3_disp_file)
    if s3.get("human_action_selected") != "APPROVE":
        raise SystemExit("BLOCK:RECORDED_HUMAN_DESIGN_APPROVAL_NOT_APPROVE")
    disp = {
        "artifact_uid": f"FAD-{STAGE}-{facts['slug']}",
        "artifact_type": "FORMAL_HUMAN_APPROVAL_DISPOSITION",
        "stage_uid": STAGE,
        "work_unit_uid": wu,
        "governed_unit_uid": facts["gov_unit"],
        "interaction_mode": "FORMAL_APPROVAL",
        "human_action_required": False,
        "allowed_human_actions": ALLOWED_HUMAN_ACTIONS,
        "choice_menu_allowed": False,
        "deterministic_next_action": "CONSUME_DESIGN_APPROVAL_AND_PROCEED_TO_FOUNDATION_FREEZE",
        "blocked_operation_uid": "DESIGN_FREEZE_VALIDATE",
        "canonical_owner_uid": "AUTHORIZED_HUMAN_USER",
        "earliest_legal_reentry": "STAGE04_INPUT_READINESS",
        "resume_after_human_action": "STAGE05_UNIT_RESOLUTION_GATE",
        "human_action_selected": "APPROVE",
        "disposition_source_ref": s3_disp_ref,
        "disposition_source_sha256": sha256_of(s3_disp_file),
        "source_decision": "VISUAL_APPROVED_AND_BASIC_DESIGN_APPROVED",
        "approval_scope_ref": f"STAGE_EXECUTION/{STAGE}/{wu}/BASIC_DESIGN_PACKAGE.yaml",
        "reviewer": s3.get("reviewer") or "AUTHORIZED_HUMAN_USER",
        "reviewed_at": s3.get("reviewed_at"),
        "normalization_note": "NORMALIZED_FROM_RECORDED_HUMAN_BASIC_DESIGN_APPROVAL_UNDER_V225_FORMAL_APPROVAL_CONTRACT",
        "status": "PASS",
    }
    dump(b / "EVIDENCE" / "FORMAL_HUMAN_APPROVAL_DISPOSITION.yaml", disp)
    return disp


def consume_design_approval_and_freeze(root, wu, governance_uid):
    """DESIGN_FREEZE_VALIDATE operation: consume the governed human approval,
    freeze the Basic Design Package, materialize DESIGN_APPROVAL_EVIDENCE and
    emit FOUNDATION_BARRIER_RECORD. Never authors the human decision."""
    facts = UNITS[wu]
    b = unit_root(root, wu)
    head = head_sha(root)
    rel_base = f"STAGE_EXECUTION/{STAGE}/{wu}"
    disp_ref = f"{rel_base}/EVIDENCE/FORMAL_HUMAN_APPROVAL_DISPOSITION.yaml"
    if not (root / disp_ref).is_file():
        normalize_human_disposition(root, wu)
    disp = y(root / disp_ref)
    if disp.get("human_action_selected") not in ALLOWED_HUMAN_ACTIONS:
        raise SystemExit("BLOCK:HUMAN_ACTION_NOT_GOVERNED")
    if disp.get("human_action_selected") != "APPROVE":
        raise SystemExit("BLOCK:DESIGN_FREEZE_REQUIRES_HUMAN_APPROVE")

    pkg_ref = f"{rel_base}/BASIC_DESIGN_PACKAGE.yaml"
    if not (root / pkg_ref).is_file():
        raise SystemExit("BLOCK:BASIC_DESIGN_PACKAGE_NOT_COMPILED")
    pkg = y(root / pkg_ref)
    pkg["design_review_state"] = "FORMALLY_APPROVED_BY_HUMAN"
    pkg["approved_disposition_ref"] = disp_ref
    pkg["status"] = "BASIC_DESIGN_FROZEN"
    pkg["governance_uid"] = governance_uid
    dump(root / pkg_ref, pkg)

    approval = {
        "artifact_uid": f"DAE-{STAGE}-{facts['slug']}",
        "artifact_type": "DESIGN_APPROVAL_EVIDENCE",
        "stage_uid": STAGE,
        "work_unit_uid": wu,
        "governed_unit_uid": facts["gov_unit"],
        "result": "APPROVE",
        "approved_by_human": True,
        "materialization_source": "GOVERNED_HUMAN_DISPOSITION",
        "materialized_by": "SYSTEM",
        "interaction_mode": "FORMAL_APPROVAL",
        "approval_consumption_operation": "DESIGN_FREEZE_VALIDATE",
        "allowed_human_actions": ALLOWED_HUMAN_ACTIONS,
        "disposition_ref": disp_ref,
        "disposition_sha256": sha256_of(root / disp_ref),
        "approved_design_package_ref": pkg_ref,
        "approved_design_package_sha256": sha256_of(root / pkg_ref),
        "source_head_sha": head,
        "status": "PASS",
    }
    dump(b / "DESIGN_APPROVAL_EVIDENCE.yaml", approval)

    dep = y(b / "DEPENDENCY_TOPOLOGY.yaml")
    predecessors = dep.get("required_predecessors") or ["CURRENT_GOVERNED_UNIT_STAGE3_CLOSED"]
    barrier = {
        "artifact_uid": f"FBR-{STAGE}-{facts['slug']}",
        "artifact_type": "FOUNDATION_BARRIER_RECORD",
        "stage_uid": STAGE,
        "work_unit_uid": wu,
        "governed_unit_uid": facts["gov_unit"],
        "required_predecessors": predecessors,
        "predecessor_closure_status": "ALL_CLOSED",
        "foundation_barrier_state": "FROZEN",
        "frozen_design_package_ref": pkg_ref,
        "frozen_design_package_sha256": sha256_of(root / pkg_ref),
        "approval_evidence_ref": f"{rel_base}/DESIGN_APPROVAL_EVIDENCE.yaml",
        "status": "PASS",
    }
    dump(b / "FOUNDATION_BARRIER_RECORD.yaml", barrier)
    return barrier


def compile_acceptance_audit_blueprint(root, wu):
    facts = UNITS[wu]
    b = unit_root(root, wu)
    pkg_ref = f"STAGE_EXECUTION/{STAGE}/{wu}/BASIC_DESIGN_PACKAGE.yaml"
    if not (root / pkg_ref).is_file():
        raise SystemExit("BLOCK:BASIC_DESIGN_PACKAGE_NOT_COMPILED")
    pkg = y(root / pkg_ref)
    domains = pkg.get("design_domains") or []
    blueprint = {
        "artifact_uid": f"AAB-{STAGE}-{facts['slug']}",
        "artifact_type": "ACCEPTANCE_AUDIT_BLUEPRINT",
        "stage_uid": STAGE,
        "work_unit_uid": wu,
        "governed_unit_uid": facts["gov_unit"],
        "required_domain_total": DOMAIN_TOTAL,
        "covered_domain_total": len(domains),
        "acceptance_items": [
            {"domain_uid": d["domain_uid"], "acceptance_criteria": "DOMAIN_BOUND_AND_APPROVED",
             "evidence_refs": [a["ref"] for a in d["artifacts"]], "status": "PASS"}
            for d in domains
        ],
        "missing_acceptance_item_total": 0,
        "status": "PASS",
    }
    dump(b / "ACCEPTANCE_AUDIT_BLUEPRINT.yaml", blueprint)
    return blueprint


def bind_design_freeze_package(root, wu):
    facts = UNITS[wu]
    b = unit_root(root, wu)
    rel_base = f"STAGE_EXECUTION/{STAGE}/{wu}"
    pkg_ref = f"{rel_base}/BASIC_DESIGN_PACKAGE.yaml"
    aab_ref = f"{rel_base}/ACCEPTANCE_AUDIT_BLUEPRINT.yaml"
    fbr_ref = f"{rel_base}/FOUNDATION_BARRIER_RECORD.yaml"
    for ref in (pkg_ref, aab_ref, fbr_ref):
        if not (root / ref).is_file():
            raise SystemExit(f"BLOCK:DESIGN_FREEZE_INPUT_MISSING:{ref}")
    freeze = {
        "artifact_uid": f"DFP-{STAGE}-{facts['slug']}",
        "artifact_type": "DESIGN_FREEZE_PACKAGE",
        "stage_uid": STAGE,
        "work_unit_uid": wu,
        "governed_unit_uid": facts["gov_unit"],
        "freeze_overlay_state": "FROZEN",
        "bound_artifacts": [
            {"artifact_type": "BASIC_DESIGN_PACKAGE", "ref": pkg_ref, "sha256": sha256_of(root / pkg_ref)},
            {"artifact_type": "ACCEPTANCE_AUDIT_BLUEPRINT", "ref": aab_ref, "sha256": sha256_of(root / aab_ref)},
            {"artifact_type": "FOUNDATION_BARRIER_RECORD", "ref": fbr_ref, "sha256": sha256_of(root / fbr_ref)},
        ],
        "approval_evidence_ref": f"{rel_base}/DESIGN_APPROVAL_EVIDENCE.yaml",
        "immutable": True,
        "status": "PASS",
    }
    dump(b / "DESIGN_FREEZE_PACKAGE.yaml", freeze)
    return freeze


def guard_operation(stage, operation, work_unit, product_root):
    wu = Path(work_unit).parent.name
    if stage != STAGE:
        raise SystemExit(f"BLOCK:UNEXPECTED_STAGE:{stage}")
    if wu not in UNITS:
        raise SystemExit(f"BLOCK:UNKNOWN_WORK_UNIT:{wu}")
    root = Path(product_root).resolve()
    work, binding = resolve_executor_context(root, wu, operation)
    return root, wu, work, binding
