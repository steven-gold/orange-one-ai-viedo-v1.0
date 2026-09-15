#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "governance/test/stage02/STAGE02_POST_ACTION_SIGNAL_ROLE_RECLASSIFICATION_R22.yaml"
EXPECTED_AUTO = {"ASSET-01-ACT-FLOW-START", "ASSET-01-ACT-CANDIDATE-CONFIRM"}
EXPECTED_GAP = {"ASSET-01-ACT-CORRECTION-EXECUTE"}


def die(msg):
    print(f"BLOCK: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die("MAPPING_REQUIRED")
    return obj


d = load(P)
if d.get("artifact_type") != "NON_NORMATIVE_STAGE02_POST_ACTION_SIGNAL_ROLE_RECLASSIFICATION_R22" or d.get("normative_authority") is not False:
    die("R22_IDENTITY_DRIFT")
records = d.get("records") or []
if len(records) != 3:
    die(f"R22_DENOMINATOR:{len(records)}")
auto = [r for r in records if r.get("authorized_for_auto_completion") is True]
gaps = [r for r in records if r.get("authority_gap_proven") is True]
if {r.get("target_uid") for r in auto} != EXPECTED_AUTO:
    die(f"R22_AUTO_TARGET_DRIFT:{sorted(r.get('target_uid') for r in auto)}")
if {r.get("target_uid") for r in gaps} != EXPECTED_GAP:
    die(f"R22_GAP_TARGET_DRIFT:{sorted(r.get('target_uid') for r in gaps)}")
for r in records:
    if r.get("prior_r20_disposition") != "AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES":
        die(f"R22_PRIOR_DISPOSITION:{r.get('target_uid')}")
    excluded = r.get("excluded_non_validation_role_evidence") or []
    if not excluded:
        die(f"R22_TRANSITION_EXCLUSION_MISSING:{r.get('target_uid')}")
    if any(x.get("signal_role") != "FLOW_TRANSITION_DESTINATION_NON_VALIDATION_ROLE" or x.get("scanner_validation_role_admissible") is not False for x in excluded):
        die(f"R22_EXCLUDED_ROLE_DRIFT:{r.get('target_uid')}")
    admissible = r.get("admissible_validation_evidence") or []
    if not admissible:
        die(f"R22_NO_ADMISSIBLE_EVIDENCE:{r.get('target_uid')}")
    if any(x.get("signal_role") not in {"ACTION_RESULT_SIGNAL", "BOUND_PORT_RESULT_OR_STATE_SIGNAL"} or x.get("scanner_validation_role_admissible") is not True for x in admissible):
        die(f"R22_ADMISSIBLE_ROLE_DRIFT:{r.get('target_uid')}")
    if r.get("semantic_similarity_used") is not False or r.get("ai_invented_business_value") is not False or r.get("outside_frozen_registered_dependency_closure") is not False:
        die(f"R22_SAFETY_DRIFT:{r.get('target_uid')}")
    values = {yaml.safe_dump(x.get("value"), allow_unicode=True, sort_keys=True) for x in admissible}
    if r.get("authorized_for_auto_completion") is True:
        if r.get("disposition") != "AUTO_REMEDIABLE_AFTER_SIGNAL_ROLE_CORRECTION" or r.get("authority_gap_proven") is not False:
            die(f"R22_AUTO_FLAGS:{r.get('target_uid')}")
        if len(values) != 1 or r.get("admissible_candidate_value_count") != 1 or r.get("candidate_value") in (None, "", [], {}):
            die(f"R22_AUTO_NOT_UNIQUE:{r.get('target_uid')}")
    else:
        if r.get("target_uid") not in EXPECTED_GAP or r.get("disposition") != "AUTHORITY_GAP_MULTIPLE_ACTION_RESULT_SIGNALS_AFTER_ROLE_CORRECTION":
            die(f"R22_NONAUTO_DISPOSITION:{r.get('target_uid')}")
        if len(values) != 2 or r.get("admissible_candidate_value_count") != 2 or r.get("candidate_value") is not None:
            die(f"R22_TRUE_GAP_NOT_TWO:{r.get('target_uid')}:{len(values)}")
den = d.get("denominators") or {}
if den != {"input_r20_post_action_authority_gap_total": 3, "auto_remediable_after_role_correction": 2, "authority_gap_after_role_correction": 1, "blocker_reduction_claimed_before_materialization": 0}:
    die(f"R22_DENOMINATOR_DRIFT:{den}")
if d.get("current_specification_mutated") is not False or d.get("immutable_stage1_source_mutated") is not False or d.get("stage03_allowed") is not False:
    die("R22_STAGE_BOUNDARY_DRIFT")
print("PASS: R22 signal-role correction exact 3/3; auto=2; authority_gap=1")
print("PASS: transition.to_stage preserved as flow evidence but excluded from post-action validation role")
print("PASS: CORRECTION-EXECUTE remains blocked with two distinct admissible result signals")
