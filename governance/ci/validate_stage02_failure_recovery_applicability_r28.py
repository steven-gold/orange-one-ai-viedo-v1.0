#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "governance/test/stage02/STAGE02_FAILURE_RECOVERY_APPLICABILITY_AUDIT_R28.yaml"
NON_EFFECTFUL = {"READ_ONLY", "UI_ONLY", "CONTEXT_STATE"}


def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die("R28_MAPPING_REQUIRED")
    return obj


doc = load(DOC)
if doc.get("artifact_type") != "NON_NORMATIVE_STAGE02_FAILURE_RECOVERY_APPLICABILITY_AUDIT_R28" or doc.get("stage_uid") != "STAGE-02":
    die("R28_IDENTITY_DRIFT")
if doc.get("normative_authority") is not False:
    die("R28_NORMATIVE_AUTHORITY_DRIFT")
basis = doc.get("governance_basis") or {}
if basis.get("n_a_requires_exact_machine_proof") is not True or basis.get("absence_alone_may_not_prove_not_applicable") is not True or basis.get("semantic_guessing_for_n_a_forbidden") is not True:
    die("R28_GOVERNANCE_BASIS_DRIFT")
contract = doc.get("applicability_contract") or {}
if contract.get("effectful_or_transitioned_or_nonclient_action_keeps_failure_recovery_requirement") is not True:
    die("R28_REQUIRED_BOUNDARY_DRIFT")
if contract.get("not_applicable_does_not_create_recovery_value") is not True or contract.get("not_applicable_does_not_reduce_blocker_until_scanner_fix_and_fresh_reexecution") is not True:
    die("R28_NA_SAFETY_DRIFT")
den = doc.get("denominators") or {}
if den.get("failure_recovery_problems_audited") != 44 or den.get("blocker_reduction_claimed") != 0:
    die(f"R28_DENOMINATOR_DRIFT:{den}")
na = den.get("not_applicable_exact_proof_count")
keep = den.get("keep_gap_count")
if not isinstance(na, int) or not isinstance(keep, int) or na < 0 or keep < 0 or na + keep != 44:
    die(f"R28_PARTITION_DRIFT:{na}:{keep}")
rows = doc.get("records") or []
if len(rows) != 44 or len({x.get("blocker_uid") for x in rows}) != 44:
    die("R28_RECORD_DENOMINATOR_DRIFT")
calc_na = 0
for row in rows:
    proof = row.get("n_a_proof") or {}
    all_na = all(proof.get(k) is True for k in (
        "effect_type_is_non_effectful",
        "binding_kind_is_client_state_or_view_no_api_required",
        "api_required_is_false",
        "explicit_error_uid_absent",
        "stage_transition_absent",
    ))
    if row.get("applicability_classification") == "NOT_APPLICABLE_NON_EFFECTFUL_CLIENT_NO_API_NO_TRANSITION":
        calc_na += 1
        if not all_na or row.get("functional_chain_failure_node_applicability") != "NOT_APPLICABLE" or row.get("scanner_disposition") != "SUPPRESS_FAILURE_RECOVERY_GAP_WITH_EXACT_NA_PROOF":
            die(f"R28_NA_ROW_PROOF_DRIFT:{row.get('blocker_uid')}")
        if row.get("effect_type") not in NON_EFFECTFUL or row.get("runtime_binding_kind") != "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED" or row.get("api_required") is not False or row.get("stage_transition_uids") != []:
            die(f"R28_NA_ROW_MACHINE_IDENTITY_DRIFT:{row.get('blocker_uid')}")
    else:
        if row.get("applicability_classification") != "REQUIRED_OR_NOT_PROVEN_NOT_APPLICABLE" or row.get("scanner_disposition") != "KEEP_FAILURE_RECOVERY_GAP":
            die(f"R28_KEEP_ROW_DRIFT:{row.get('blocker_uid')}")
    if row.get("product_behavior_value_invented") is not False or row.get("recovery_value_invented") is not False:
        die(f"R28_INVENTION_FLAG_DRIFT:{row.get('blocker_uid')}")
if calc_na != na:
    die(f"R28_NA_RECOUNT_DRIFT:{calc_na}:{na}")
if doc.get("current_specification_mutated") is not False or doc.get("immutable_stage1_source_mutated") is not False:
    die("R28_MUTATION_FLAG_DRIFT")
print(f"PASS: R28 failure/recovery applicability partition validated: exact N/A={na}, keep={keep}")
print("PASS: no recovery/product behavior values invented")
