#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
R20 = ROOT / "governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml"
R17 = ROOT / "governance/test/stage02/STAGE02_STATE_TRANSITION_LEDGER_DEPENDENCY_TRACE_R17.yaml"
LEDGER = ROOT / "00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml"
OUT = ROOT / "governance/test/stage02/STAGE02_R20_TRANSITION_OWNER_INVALIDATION_R24.yaml"
EXPECTED_BLOCKERS = {
    "STAGE02-R5-PRODUCT-AUTH-091",
    "STAGE02-R5-PRODUCT-AUTH-099",
    "STAGE02-R5-PRODUCT-AUTH-103",
    "STAGE02-R5-PRODUCT-AUTH-107",
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


r20 = load(R20)
r17 = load(R17)
ledger = load(LEDGER)

r17_contract = r17.get("trace_contract") or {}
if r17_contract.get("field_must_be_physically_present_on_same_exact_transition_uid") is not True:
    die("R17_SAME_TRANSITION_FIELD_INVARIANT_MISSING")
if r17_contract.get("action_owner_may_supply_mutation_owner") is not False:
    die("R17_ACTION_OWNER_PROHIBITION_DRIFT")
if (r17.get("denominators") or {}).get("exact_transition_ledger_field_found") != 0:
    die("R17_EXACT_FIELD_DENOMINATOR_DRIFT")
if (r17.get("denominators") or {}).get("state_transition_ledger_field_gaps_traced") != 40:
    die("R17_TRANSITION_DENOMINATOR_DRIFT")

r17_index = {(x.get("blocker_uid"), x.get("scope"), x.get("target_uid"), x.get("missing_field_or_relation")): x for x in (r17.get("records") or [])}
if len(r17_index) != 40:
    die(f"R17_RECORD_INDEX_DRIFT:{len(r17_index)}")

auto_state = [
    x for x in (r20.get("records") or [])
    if x.get("category") == "STATE_TRANSITION_LEDGER_FIELD_MISSING" and x.get("authorized_for_auto_completion") is True
]
if len(auto_state) != 4:
    die(f"R20_AUTO_STATE_DENOMINATOR_DRIFT:{len(auto_state)}")
if {x.get("blocker_uid") for x in auto_state} != EXPECTED_BLOCKERS:
    die(f"R20_AUTO_STATE_BLOCKER_SET_DRIFT:{sorted(x.get('blocker_uid') for x in auto_state)}")

ledger_entries = {
    x.get("source_blocker_uid"): x
    for x in (ledger.get("remediations") or [])
    if x.get("source_cycle") == "R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY"
    and (x.get("defect_signature") or {}).get("category") == "STATE_TRANSITION_LEDGER_FIELD_MISSING"
}
if set(ledger_entries) != EXPECTED_BLOCKERS:
    die(f"CURRENT_LEDGER_SUSPECT_SET_DRIFT:{sorted(ledger_entries)}")

invalidations = []
for row in sorted(auto_state, key=lambda x: x.get("blocker_uid")):
    blocker = row.get("blocker_uid")
    if row.get("page_uid") != "ASSET-01" or row.get("missing_field_or_relation") != "mutation_owner":
        die(f"R20_AUTO_STATE_SCOPE_OR_FIELD_DRIFT:{blocker}")
    if row.get("closure_type") != "TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER":
        die(f"R20_AUTO_STATE_CLOSURE_TYPE_DRIFT:{blocker}:{row.get('closure_type')}")
    if row.get("distinct_candidate_value_count") != 1:
        die(f"R20_AUTO_STATE_CANDIDATE_COUNT_DRIFT:{blocker}")
    target = row.get("target_uid")
    r17_row = r17_index.get((blocker, "ASSET-01", target, "mutation_owner"))
    if not r17_row:
        die(f"R17_MATCHING_RECORD_MISSING:{blocker}")
    if r17_row.get("exact_transition_ledger_field_evidence") not in ([], None):
        die(f"R17_UNEXPECTED_EXACT_FIELD_EVIDENCE:{blocker}")
    evidence = row.get("candidate_evidence") or []
    if not evidence:
        die(f"R20_CANDIDATE_EVIDENCE_MISSING:{blocker}")
    nodes = [str(ev.get("node") or "") for ev in evidence]
    if not any(node.startswith("actions:") and ("runtime_binding.port_uid" in node or "runtime_binding.persist_via_port_uid" in node) for node in nodes):
        die(f"R20_SUSPECT_ACTION_RUNTIME_OWNER_EVIDENCE_MISSING:{blocker}")
    if any("stage_transitions:" in node or "mutation_owner" in node for node in nodes):
        die(f"R20_SUSPECT_EVIDENCE_UNEXPECTED_SAME_TRANSITION_FIELD:{blocker}")
    current = ledger_entries[blocker]
    if current.get("completion_basis") != "TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER":
        die(f"LEDGER_SUSPECT_COMPLETION_BASIS_DRIFT:{blocker}")
    closure = current.get("materialized_closure") or {}
    if closure.get("transition_uid") != target or closure.get("closure_type") != "TRANSITION_MUTATION_OWNER_FROM_UNIQUE_TRIGGER_RUNTIME_OWNER":
        die(f"LEDGER_SUSPECT_CLOSURE_DRIFT:{blocker}")
    invalidations.append({
        "blocker_uid": blocker,
        "page_uid": "ASSET-01",
        "transition_uid": target,
        "field": "mutation_owner",
        "r20_candidate_value": row.get("candidate_value"),
        "r20_candidate_evidence": evidence,
        "current_ledger_remediation_uid": current.get("remediation_uid"),
        "invalidity": "ACTION_TRIGGER_RUNTIME_OWNER_WAS_PROMOTED_TO_TRANSITION_MUTATION_OWNER_WITHOUT_SAME_TRANSITION_FIELD_AUTHORITY",
        "r17_invariant": {
            "field_must_be_physically_present_on_same_exact_transition_uid": True,
            "action_owner_may_supply_mutation_owner": False,
            "r17_exact_transition_ledger_field_evidence": [],
        },
        "rollback_required": True,
        "replacement_value": None,
        "semantic_inference_used_for_replacement": False,
        "product_authority_value_invented": False,
    })

head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
out = {
    "schema_version": 2,
    "artifact_type": "NON_NORMATIVE_STAGE02_R20_TRANSITION_OWNER_INVALIDATION_R24",
    "normative_authority": False,
    "stage_uid": "STAGE-02",
    "source_head_sha": head,
    "source_r20": str(R20.relative_to(ROOT)),
    "source_r17": str(R17.relative_to(ROOT)),
    "source_current_ledger": str(LEDGER.relative_to(ROOT)),
    "correction_basis": {
        "r17_precedes_r20_as_category_exact_trace": True,
        "same_transition_physical_field_required": True,
        "action_owner_to_transition_mutation_owner_promotion_forbidden": True,
        "action_operation_matrix_lineage_is_not_transition_field_authority": True,
        "rollback_only_no_replacement_value": True,
        "current_specification_mutation_forbidden": True,
        "stage1_raw_mutation_forbidden": True,
    },
    "denominators": {
        "r20_state_transition_auto_total": 4,
        "invalid_r20_state_transition_auto_total": len(invalidations),
        "valid_r20_state_transition_auto_total": 0,
        "current_product_materialization_total_before_rollback": 38,
        "expected_product_materialization_total_after_rollback": 34,
        "blocker_reduction_claimed_before_fresh_reexecution": 0,
    },
    "invalidations": invalidations,
    "current_specification_mutated": False,
    "immutable_stage1_source_mutated": False,
    "stage02_status": "BLOCKED",
    "stage03_allowed": False,
    "website_construction_allowed": False,
    "deployment_allowed": False,
    "next_execution_gate": "ROLLBACK_EXACT_FOUR_INVALID_R20_TRANSITION_MUTATION_OWNER_MATERIALIZATIONS_THEN_FRESH_STAGE02_REEXECUTION",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=180), encoding="utf-8")
print("PASS: R24 identified exactly four invalid R20 transition mutation_owner materializations")
for x in invalidations:
    print(f"INVALIDATE {x['blocker_uid']} {x['transition_uid']}.mutation_owner")
print("PASS: action/operation-matrix lineage was not promoted into same-transition field authority")
print("PASS: no replacement mutation_owner value invented")
