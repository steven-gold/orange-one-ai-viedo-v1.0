#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml"
R18 = ROOT / "governance/test/stage02/STAGE02_ACTION_CONTROL_TRIGGER_DEPENDENCY_TRACE_R18.yaml"
R31 = ROOT / "governance/test/stage02/STAGE02_OWNING_LAYER_REMEDIATION_INPUT_PACKET_R31.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_FINDING_CREATE_CONTROL_TRIGGER_CANDIDATE_REVIEW_R32.yaml"
BLOCKER = "STAGE02-R5-PRODUCT-AUTH-032"
INPUT_UID = "STAGE02-R27-INPUT-032"
ACTION = "ASSET-01-ACT-FINDING-CREATE"


def die(msg: str) -> None:
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def idx(items, key):
    out = {}
    for x in items or []:
        if isinstance(x, dict) and x.get(key):
            if x[key] in out:
                die(f"DUPLICATE_{key}:{x[key]}")
            out[x[key]] = x
    return out


raw = load(RAW)
r18 = load(R18)
r31 = load(R31)
reg = raw.get("registries") or {}
actions = idx(reg.get("actions"), "action_uid")
controls = idx(reg.get("controls"), "control_uid")
ports = idx(reg.get("integration_ports"), "port_uid")
objects = idx(reg.get("objects_refs"), "object_uid")
stages = idx(reg.get("stages"), "stage_uid")
transitions = idx(reg.get("stage_transitions"), "transition_uid")

r18rows = [x for x in (r18.get("records") or []) if x.get("blocker_uid") == BLOCKER]
if len(r18rows) != 1:
    die(f"R32_R18_RECORD_DENOMINATOR:{len(r18rows)}")
r18row = r18rows[0]
if r18row.get("target_uid") != ACTION or r18row.get("exact_control_binding_evidence") not in ([], None) or r18row.get("exact_trigger_binding_evidence") not in ([], None):
    die("R32_R18_BASELINE_DRIFT")
if r18row.get("classification") != "EXACT_PORT_EXPOSURE_ONLY_CONTROL_TRIGGER_MISSING":
    die("R32_R18_CLASSIFICATION_DRIFT")

inputs = [x for x in (r31.get("inputs") or []) if x.get("remediation_input_uid") == INPUT_UID]
if len(inputs) != 1:
    die(f"R32_R31_INPUT_DENOMINATOR:{len(inputs)}")
input_row = inputs[0]
if input_row.get("blocker_uid") != BLOCKER or input_row.get("target_uid") != ACTION or input_row.get("category") != "ACTION_WITHOUT_CONTROL_OR_TRIGGER":
    die("R32_R31_INPUT_IDENTITY_DRIFT")
if input_row.get("owning_layer_contract_value") is not None or input_row.get("input_status") != "REQUIRED_NOT_PROVIDED":
    die("R32_R31_INPUT_PREMATURE_VALUE")

action = actions.get(ACTION)
if not action:
    die("R32_ACTION_MISSING")
rb = action.get("runtime_binding") or {}
if action.get("permission_uid") != "ASSET_CORRECT" or action.get("gate_uid") != "ASSET-01-GATE-EVALUATION" or action.get("effect_type") != "FINDING_CREATE":
    die("R32_ACTION_CONTRACT_DRIFT")
if rb.get("binding_kind") != "SOURCE_INTEGRATION_PORT" or rb.get("port_uid") != "ASSET-01-PORT-FINDING" or rb.get("decision") != "SOURCE_DERIVED":
    die("R32_ACTION_RUNTIME_DRIFT")

port = ports.get("ASSET-01-PORT-FINDING")
if not port:
    die("R32_FINDING_PORT_MISSING")
if port.get("registered_operation") != "createFinding" or port.get("method_effective_path") != "POST /v1/findings" or port.get("registered_permission") != "finding.write":
    die("R32_FINDING_PORT_IDENTITY_DRIFT")
if port.get("state_event") != "IN_REVIEW→FINDING_OPEN | finding.created":
    die("R32_FINDING_PORT_STATE_EVENT_DRIFT")

finding = objects.get("ASSET-01-OBJ-FINDING")
evaluation = objects.get("ASSET-01-OBJ-EVALUATION")
scorecard = objects.get("ASSET-01-OBJ-SCORECARD")
if not finding or finding.get("owner") != "ASSET/EVALUATION" or "issue" not in str(finding.get("required_content") or ""):
    die("R32_FINDING_OBJECT_DRIFT")
if not evaluation or evaluation.get("owner") != "ASSET/EVALUATION" or "evidence" not in str(evaluation.get("required_content") or ""):
    die("R32_EVALUATION_OBJECT_DRIFT")
if not scorecard or scorecard.get("owner") != "ASSET/EVALUATION" or "issues" not in str(scorecard.get("required_content") or ""):
    die("R32_SCORECARD_OBJECT_DRIFT")

sec09_controls = [x for x in controls.values() if x.get("section_uid") == "ASSET-01-SEC-09"]
if any(x.get("action_uid") == ACTION for x in sec09_controls):
    die("R32_UNEXPECTED_EXISTING_MANUAL_CONTROL")
required_sec09_actions = {
    "ASSET-01-ACT-EVALUATE",
    "ASSET-01-ACT-CANDIDATE-CONFIRM",
    "ASSET-01-ACT-CORRECTION-OPEN",
}
if not required_sec09_actions.issubset({x.get("action_uid") for x in sec09_controls}):
    die("R32_SEC09_DECISION_NEIGHBORHOOD_DRIFT")

stage4 = stages.get("ASSET-01-STAGE-04-EVALUATE-DECIDE")
if not stage4 or "Confirm or enter Correction" not in str(stage4.get("flow") or ""):
    die("R32_EVALUATE_DECIDE_STAGE_DRIFT")
sttr3 = transitions.get("ASSET-01-STTR-03")
if not sttr3 or (sttr3.get("trigger") or sttr3.get("action_uid")) != "ASSET-01-ACT-EVALUATE" or sttr3.get("to_stage") != "ASSET-01-STAGE-04-EVALUATE-DECIDE":
    die("R32_EVALUATION_ENTRY_TRANSITION_DRIFT")

manual = {
    "candidate_uid": "R32-CANDIDATE-A-MANUAL-CONTROL",
    "behavior_kind": "MANUAL_UI_CONTROL_BINDING",
    "product_behavior_summary": "Operator explicitly creates an AssetFinding from the Evaluation/Decision context.",
    "grounding": [
        "ASSET-01-ACT-FINDING-CREATE already exists with ASSET_CORRECT and ASSET-01-GATE-EVALUATION.",
        "ASSET-01-SEC-09 is the existing Evaluation/Decision surface and already exposes Evaluate, Confirm, Modify, and issue summary controls.",
        "ASSET-01-OBJ-FINDING is owned by ASSET/EVALUATION and requires issue/evidence context.",
        "ASSET-01-PORT-FINDING already owns createFinding -> POST /v1/findings.",
    ],
    "would_reuse": {
        "section_uid": "ASSET-01-SEC-09",
        "action_uid": ACTION,
        "gate_uid": "ASSET-01-GATE-EVALUATION",
        "action_permission_uid": "ASSET_CORRECT",
        "runtime_port_uid": "ASSET-01-PORT-FINDING",
        "operation": "createFinding",
    },
    "authority_values_not_invented": {
        "new_control_uid": None,
        "control_type": None,
        "control_label": None,
        "exact_visual_placement": None,
    },
    "review": {
        "role_correct": True,
        "upstream_context_available": True,
        "gate_permission_alignment": True,
        "runtime_port_continuity": True,
        "requires_new_ui_design_authority": True,
        "uniquely_mandated_by_current_authority": False,
        "candidate_status": "REASONABLE_PRODUCT_BEHAVIOR_REQUIRES_AUTHORITY_SELECTION",
    },
}

automatic = {
    "candidate_uid": "R32-CANDIDATE-B-EVALUATION-SYSTEM-TRIGGER",
    "behavior_kind": "AUTOMATIC_EVALUATION_SYSTEM_TRIGGER",
    "product_behavior_summary": "Evaluation/score processing automatically creates an AssetFinding when the governed issue condition is met.",
    "grounding": [
        "AssetEvaluation and AssetScorecard already contain issue/evidence semantics under ASSET/EVALUATION.",
        "ASSET-01-ACT-FINDING-CREATE declares decision=SOURCE_DERIVED rather than a manual input value.",
        "ASSET-01-PORT-FINDING state_event is IN_REVIEW→FINDING_OPEN | finding.created.",
        "Stage 04 is explicitly Evaluate / Confirm or Modify, so a finding can reasonably be an evaluation-derived state before Correction.",
    ],
    "would_reuse": {
        "source_stage_uid": "ASSET-01-STAGE-04-EVALUATE-DECIDE",
        "upstream_action_uid": "ASSET-01-ACT-EVALUATE",
        "action_uid": ACTION,
        "gate_uid": "ASSET-01-GATE-EVALUATION",
        "action_permission_uid": "ASSET_CORRECT",
        "runtime_port_uid": "ASSET-01-PORT-FINDING",
        "operation": "createFinding",
    },
    "authority_values_not_invented": {
        "system_trigger_uid": None,
        "exact_trigger_condition": None,
        "issue_threshold_or_hard_block_rule": None,
        "single_vs_multiple_finding_policy": None,
    },
    "review": {
        "role_correct": True,
        "upstream_context_available": True,
        "gate_permission_alignment": True,
        "runtime_port_continuity": True,
        "requires_trigger_policy_authority": True,
        "uniquely_mandated_by_current_authority": False,
        "candidate_status": "REASONABLE_PRODUCT_BEHAVIOR_REQUIRES_AUTHORITY_SELECTION",
    },
}

head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    "schema_version": 1,
    "artifact_type": "NON_NORMATIVE_STAGE02_FUNCTIONAL_CHAIN_PRODUCT_BEHAVIOR_CANDIDATE_REVIEW_R32",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "cycle": "FINDING_CREATE_CONTROL_TRIGGER_CANDIDATE_REVIEW_R32",
    "source_head_sha": head,
    "problem_identity": {
        "problem_uid": "STAGE02-FUNCTIONAL-REMEDIATION-032",
        "blocker_uid": BLOCKER,
        "remediation_input_uid": INPUT_UID,
        "scope": "ASSET-01",
        "category": "ACTION_WITHOUT_CONTROL_OR_TRIGGER",
        "target_uid": ACTION,
        "owning_contract": "PAGE_CONTROL_OR_REGISTERED_TRIGGER_BINDING",
    },
    "source_contracts": {
        "current_raw_page_authority": str(RAW.relative_to(ROOT)),
        "exact_dependency_trace": str(R18.relative_to(ROOT)),
        "current_owning_layer_input": str(R31.relative_to(ROOT)),
    },
    "candidate_review_contract": {
        "candidate_is_not_authority": True,
        "candidate_may_not_reduce_blocker": True,
        "candidate_may_not_create_canonical_uid": True,
        "candidate_may_not_create_trigger_condition": True,
        "two_or_more_reasonable_behaviors_without_unique_authority_proves_product_authority_decision_required": True,
        "port_exposure_may_not_be_promoted_to_trigger": True,
        "current_specification_mutation_forbidden": True,
        "stage1_raw_mutation_forbidden": True,
    },
    "functional_chain_evidence": {
        "upstream_evaluation_action_uid": "ASSET-01-ACT-EVALUATE",
        "evaluation_entry_transition_uid": "ASSET-01-STTR-03",
        "evaluation_decision_stage_uid": "ASSET-01-STAGE-04-EVALUATE-DECIDE",
        "finding_object_uid": "ASSET-01-OBJ-FINDING",
        "finding_object_owner": "ASSET/EVALUATION",
        "scorecard_contains_issues": True,
        "evaluation_contains_evidence": True,
        "finding_action_uid": ACTION,
        "finding_gate_uid": action.get("gate_uid"),
        "finding_action_permission_uid": action.get("permission_uid"),
        "finding_port_uid": rb.get("port_uid"),
        "finding_operation": port.get("registered_operation"),
        "finding_method_path": port.get("method_effective_path"),
        "finding_state_event": port.get("state_event"),
        "existing_exact_control_binding_count": 0,
        "existing_exact_registered_trigger_count": 0,
        "existing_nonqualifying_port_exposure_count": len(r18row.get("nonqualifying_lineage_evidence") or []),
    },
    "candidates": [manual, automatic],
    "review_result": {
        "reasonable_candidate_count": 2,
        "unique_minimal_behavior_proven": False,
        "exact_current_authority_selecting_manual": False,
        "exact_current_authority_selecting_automatic": False,
        "product_authority_decision_required": True,
        "classification": "AUTHORITY_GAP_MULTIPLE_REASONABLE_PRODUCT_BEHAVIORS",
        "required_product_decision": "Choose whether AssetFinding creation is operator-invoked via an Evaluation UI control or automatically system-triggered from evaluation/score issue conditions; if automatic, define the exact trigger policy; if manual, define the governed control identity/type/label/placement.",
        "owning_layer_contract_value_materialized": False,
        "blocker_reduction_credit": 0,
    },
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "product_behavior_selected_by_ai": False,
    "stage02_status": "BLOCKED",
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
    "next_execution_gate": "PRODUCT_AUTHORITY_DECISION_FOR_STAGED_FINDING_CREATION_TRIGGER_BEHAVIOR",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print("PASS: R32 built two grounded role-correct Finding Create behavior candidates")
print("BLOCKED: no unique behavior selected; Product Authority decision is required; blocker reduction=0")
