#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R26 = ROOT / "governance/test/stage02/STAGE02_CURRENT_FUNCTIONAL_CONTRACT_PROBLEM_RECONCILIATION_R26.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_FAILURE_RECOVERY_APPLICABILITY_AUDIT_R28.yaml"
RAW = {
    "ASSET-01": ROOT / "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
    "CORE-01": ROOT / "00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
}
NON_EFFECTFUL = {"READ_ONLY", "UI_ONLY", "CONTEXT_STATE"}
CLIENT_NO_API = "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED"


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


def index(items, key):
    out = {}
    for item in items or []:
        if not isinstance(item, dict) or not item.get(key):
            continue
        if item[key] in out:
            die(f"DUPLICATE_{key}:{item[key]}")
        out[item[key]] = item
    return out


r26 = load(R26)
problems = [x for x in (r26.get("problems") or []) if x.get("category") == "FAILURE_STATE_ERROR_BINDING_MISSING"]
if len(problems) != 44:
    die(f"R28_FAILURE_PROBLEM_DENOMINATOR_DRIFT:{len(problems)}")

raw_pages = {}
for page, path in RAW.items():
    doc = load(path)
    reg = doc.get("registries") or {}
    actions = index(reg.get("actions"), "action_uid")
    transitions = index(reg.get("stage_transitions"), "transition_uid")
    transitions_by_action = defaultdict(list)
    for tid, transition in transitions.items():
        trigger = transition.get("action_uid") or transition.get("trigger_event_uid") or transition.get("trigger")
        if trigger in actions:
            transitions_by_action[trigger].append(tid)
    raw_pages[page] = (actions, transitions, transitions_by_action)

records = []
status_counts = Counter()
page_counts = Counter()
effect_counts = Counter()
binding_counts = Counter()
for problem in problems:
    page = problem.get("scope")
    aid = problem.get("target_uid")
    if page not in raw_pages:
        die(f"R28_UNKNOWN_SCOPE:{page}:{aid}")
    actions, transitions, transitions_by_action = raw_pages[page]
    action = actions.get(aid)
    if not action:
        die(f"R28_ACTION_NOT_FOUND:{page}:{aid}")
    effect = action.get("effect_type")
    rb = action.get("runtime_binding") or {}
    kind = rb.get("binding_kind")
    api_required = rb.get("api_required")
    tids = sorted(transitions_by_action.get(aid, []))
    transition_recovery = [
        {"transition_uid": tid, "recovery": (transitions.get(tid) or {}).get("recovery")}
        for tid in tids
        if (transitions.get(tid) or {}).get("recovery") not in (None, "", [], {})
    ]
    explicit_error_uid = action.get("error_uid")
    n_a_proof = (
        effect in NON_EFFECTFUL
        and kind == CLIENT_NO_API
        and api_required is False
        and explicit_error_uid in (None, "")
        and not tids
    )
    if n_a_proof:
        status = "NOT_APPLICABLE_NON_EFFECTFUL_CLIENT_NO_API_NO_TRANSITION"
        scanner_disposition = "SUPPRESS_FAILURE_RECOVERY_GAP_WITH_EXACT_NA_PROOF"
    else:
        status = "REQUIRED_OR_NOT_PROVEN_NOT_APPLICABLE"
        scanner_disposition = "KEEP_FAILURE_RECOVERY_GAP"
    status_counts[status] += 1
    page_counts[page] += 1
    effect_counts[str(effect)] += 1
    binding_counts[str(kind)] += 1
    records.append({
        "problem_uid": problem.get("problem_uid"),
        "blocker_uid": problem.get("blocker_uid"),
        "scope": page,
        "action_uid": aid,
        "effect_type": effect,
        "runtime_binding_kind": kind,
        "api_required": api_required,
        "explicit_error_uid": explicit_error_uid,
        "stage_transition_uids": tids,
        "stage_transition_recovery_evidence": transition_recovery,
        "functional_chain_failure_node_applicability": "NOT_APPLICABLE" if n_a_proof else "REQUIRED_OR_UNRESOLVED",
        "applicability_classification": status,
        "scanner_disposition": scanner_disposition,
        "n_a_proof": {
            "effect_type_is_non_effectful": effect in NON_EFFECTFUL,
            "binding_kind_is_client_state_or_view_no_api_required": kind == CLIENT_NO_API,
            "api_required_is_false": api_required is False,
            "explicit_error_uid_absent": explicit_error_uid in (None, ""),
            "stage_transition_absent": not tids,
        },
        "product_behavior_value_invented": False,
        "recovery_value_invented": False,
    })

head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    "schema_version": 1,
    "artifact_type": "NON_NORMATIVE_STAGE02_FAILURE_RECOVERY_APPLICABILITY_AUDIT_R28",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "cycle": "FAILURE_RECOVERY_APPLICABILITY_AUDIT_R28",
    "source_head_sha": head,
    "source_problem_reconciliation": str(R26.relative_to(ROOT)),
    "governance_basis": {
        "WEB_GOV_01_S040C": "Each functional-chain node must be classified Required, Optional, or Not Applicable.",
        "WEB_GOV_02_S009": "Effectful Capability must materialize the traceable contract chain and every node must have error behavior.",
        "scanner_effectful_definition": "effect_type not in {READ_ONLY, UI_ONLY, CONTEXT_STATE}",
        "n_a_requires_exact_machine_proof": True,
        "absence_alone_may_not_prove_not_applicable": True,
        "semantic_guessing_for_n_a_forbidden": True,
    },
    "applicability_contract": {
        "not_applicable_only_when_all": [
            "effect_type in READ_ONLY|UI_ONLY|CONTEXT_STATE",
            "runtime_binding.binding_kind == CLIENT_STATE_OR_VIEW_NO_API_REQUIRED",
            "runtime_binding.api_required == false",
            "action.error_uid absent",
            "no exact stage transition triggered by action",
        ],
        "effectful_or_transitioned_or_nonclient_action_keeps_failure_recovery_requirement": True,
        "not_applicable_does_not_create_recovery_value": True,
        "not_applicable_does_not_reduce_blocker_until_scanner_fix_and_fresh_reexecution": True,
    },
    "denominators": {
        "failure_recovery_problems_audited": 44,
        "scope_counts": dict(sorted(page_counts.items())),
        "effect_type_counts": dict(sorted(effect_counts.items())),
        "binding_kind_counts": dict(sorted(binding_counts.items())),
        "applicability_counts": dict(sorted(status_counts.items())),
        "not_applicable_exact_proof_count": status_counts["NOT_APPLICABLE_NON_EFFECTFUL_CLIENT_NO_API_NO_TRANSITION"],
        "keep_gap_count": status_counts["REQUIRED_OR_NOT_PROVEN_NOT_APPLICABLE"],
        "blocker_reduction_claimed": 0,
    },
    "records": records,
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "product_authority_value_invented": False,
    "stage02_status": "BLOCKED",
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
    "next_execution_gate": "VALIDATE_R28_THEN_CORRECT_SCANNER_APPLICABILITY_AND_FRESH_REEXECUTE_IF_NA_COUNT_GT_ZERO",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print(f"PASS: audited 44 failure/recovery problems; exact N/A={out['denominators']['not_applicable_exact_proof_count']}; keep={out['denominators']['keep_gap_count']}")
print("PASS: no failure/recovery product value invented; blocker reduction remains zero before scanner correction")
