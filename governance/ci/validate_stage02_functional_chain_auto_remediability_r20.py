#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "governance/test/stage02/STAGE02_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY_R20.yaml"
R = ROOT / "governance/test/stage02/STAGE02_FUNCTIONAL_CONTRACT_REMEDIATION_PROBLEM_REGISTER_R19.yaml"
REQUIRED_SOURCE_KEYS = {"raw", "functional_chain", "operation_matrix", "scope_ledger"}
ALLOWED_SOURCE_KINDS = {"RAW_CURRENT_PAGE_REGISTRY", "FROZEN_STAGE02_FUNCTIONAL_CHAIN_EXACT_PROJECTION", "FROZEN_STAGE02_OPERATION_MATRIX_EXACT_PROJECTION", "FROZEN_STAGE02_SCOPE_LEDGER_EXACT_MATERIALIZATION"}


def die(msg):
    print("BLOCK:", msg, file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


out = load(P)
r19 = load(R)
records = out.get("records") or []
probs = r19.get("problems") or []
if len(records) != 150 or len(probs) != 150:
    die(f"DENOMINATOR:{len(records)}/{len(probs)}")
if out.get("schema_version") != 2:
    die("R20_SCHEMA_VERSION_2_REQUIRED")
source_bundle = out.get("source_bundle") or {}
if set(source_bundle) != {"ASSET-01", "CORE-01"}:
    die(f"SOURCE_BUNDLE_SCOPE_DRIFT:{sorted(source_bundle)}")
for page, manifest in source_bundle.items():
    if not REQUIRED_SOURCE_KEYS.issubset(manifest):
        die(f"SOURCE_MANIFEST_PATHS_MISSING:{page}")
    for flag in ("raw_loaded", "functional_chain_loaded", "operation_matrix_loaded", "scope_ledger_loaded", "functional_chain_page_uid_match", "operation_matrix_page_uid_match", "scope_ledger_page_uid_match"):
        if manifest.get(flag) is not True:
            die(f"SOURCE_MANIFEST_FLAG:{page}:{flag}")
    if int(manifest.get("functional_chain_action_count") or 0) <= 0:
        die(f"CHAIN_ACTIONS_NOT_LOADED:{page}")
    if int(manifest.get("operation_matrix_action_count") or 0) <= 0:
        die(f"MATRIX_ACTIONS_NOT_LOADED:{page}")
policy = out.get("source_policy") or {}
if policy.get("complete_stage02_functional_contract_bundle_required") is not True:
    die("FULL_BUNDLE_POLICY_MISSING")
if policy.get("natural_language_semantic_similarity_forbidden") is not True:
    die("SEMANTIC_SIMILARITY_GUARD_MISSING")
if set(policy.get("allowed_source_kinds") or []) != ALLOWED_SOURCE_KINDS:
    die("SOURCE_KIND_WHITELIST_DRIFT")
base = {(p.get("blocker_uid"), p.get("scope"), p.get("category"), str(p.get("target_uid"))): p for p in probs}
if len(base) != 150:
    die("R19_IDENTITY_NOT_UNIQUE")
seen = set()
auto = 0
authority_gap = 0
unresolved = 0
for rec in records:
    key = (rec.get("blocker_uid"), rec.get("page_uid"), rec.get("category"), str(rec.get("target_uid")))
    if key not in base:
        die(f"IDENTITY_DRIFT:{key}")
    if key in seen:
        die(f"DUPLICATE:{key}")
    seen.add(key)
    if rec.get("full_stage02_functional_contract_sources_checked") is not True:
        die(f"INCOMPLETE_SOURCE_CHECK:{key}")
    evidence = rec.get("candidate_evidence") or []
    for ev in evidence:
        if ev.get("source_kind") not in ALLOWED_SOURCE_KINDS:
            die(f"UNAPPROVED_EVIDENCE_KIND:{key}:{ev.get('source_kind')}")
        if not ev.get("source_path") or not ev.get("node"):
            die(f"EVIDENCE_PROVENANCE_INCOMPLETE:{key}")
    disposition = rec.get("disposition")
    if disposition == "AUTO_REMEDIABLE_DETERMINISTIC_MINIMAL_CLOSURE":
        auto += 1
        if rec.get("authorized_for_auto_completion") is not True:
            die(f"AUTO_NOT_AUTHORIZED:{key}")
        if rec.get("authority_gap_proven") is not False or rec.get("outside_frozen_closure") is not False:
            die(f"AUTO_BOUNDARY:{key}")
        if rec.get("distinct_candidate_value_count") != 1 or rec.get("candidate_value") in (None, "", [], {}):
            die(f"AUTO_NOT_UNIQUE:{key}")
        if not evidence:
            die(f"AUTO_WITHOUT_EVIDENCE:{key}")
        canon = {yaml.safe_dump(ev.get("value"), allow_unicode=True, sort_keys=True) for ev in evidence}
        if len(canon) != 1:
            die(f"AUTO_EVIDENCE_CONFLICT:{key}:{len(canon)}")
        score = rec.get("function_admission_scorecard") or {}
        ledger = rec.get("auto_completion_scope_ledger_entry") or {}
        if score.get("current_authority_or_deterministic_required_dependency") is not True:
            die(f"SCORECARD_AUTHORITY:{key}")
        if score.get("complete_stage02_functional_chain_checked") is not True:
            die(f"SCORECARD_FULL_CHAIN_MISSING:{key}")
        if score.get("authority_created_by_score") is not False:
            die(f"SCORE_CREATED_AUTHORITY:{key}")
        for field in ("outside_frozen_registered_dependency_closure", "generic_crud_symmetry_expansion_used", "sibling_feature_symmetry_expansion_used", "semantic_similarity_used", "ai_invented_business_value"):
            if ledger.get(field) is not False:
                die(f"LEDGER_FORBIDDEN:{key}:{field}")
    elif disposition == "AUTHORITY_GAP_MULTIPLE_REASONABLE_CLOSURES":
        authority_gap += 1
        if rec.get("authorized_for_auto_completion") is not False or rec.get("authority_gap_proven") is not True:
            die(f"AUTHORITY_GAP_FLAGS:{key}")
        if int(rec.get("distinct_candidate_value_count") or 0) < 2:
            die(f"AUTHORITY_GAP_NOT_MULTIPLE:{key}")
    elif disposition == "UNRESOLVED_FUNCTIONAL_CONTRACT_GAP_NO_UNIQUE_CLOSURE":
        unresolved += 1
        if rec.get("authorized_for_auto_completion") is not False or rec.get("authority_gap_proven") is not False:
            die(f"UNRESOLVED_FLAGS:{key}")
        if int(rec.get("distinct_candidate_value_count") or 0) != 0:
            die(f"UNRESOLVED_HAS_CANDIDATE:{key}")
    else:
        die(f"UNKNOWN_DISPOSITION:{key}:{disposition}")
if seen != set(base):
    die("R19_COVERAGE_DRIFT")
den = out.get("denominators") or {}
if den.get("input_problem_total") != 150 or den.get("auto_remediable_total") != auto or den.get("true_authority_gap_total") != authority_gap or den.get("unresolved_no_unique_closure_total") != unresolved:
    die("SUMMARY_DRIFT")
if den.get("blocker_reduction_claimed") != 0:
    die("PREMATURE_BLOCKER_REDUCTION")
if out.get("current_specification_mutated") is not False or out.get("stage03_allowed") is not False:
    die("STAGE_BOUNDARY_VIOLATION")
contract = out.get("classification_contract") or {}
if contract.get("absence_of_materialized_contract_alone_is_authority_gap") is not False:
    die("ABSENCE_AUTHORITY_RULE_DRIFT")
if contract.get("full_chain_unique_deterministic_closure_checked_before_block") is not True:
    die("FULL_CHAIN_CLASSIFICATION_RULE_MISSING")
if contract.get("raw_registry_only_classification_forbidden") is not True:
    die("RAW_ONLY_GUARD_MISSING")
if contract.get("all_exact_current_stage02_projection_sources_checked") is not True:
    die("STAGE02_PROJECTION_CHECK_MISSING")
print(f"PASS: R20 exact R19 coverage 150/150; auto={auto}; authority_gap={authority_gap}; unresolved={unresolved}")
print("PASS: complete Stage-02 Functional Contract bundle loaded for ASSET-01 and CORE-01")
print("PASS: every AUTO_REMEDIABLE record has one canonical value across exact whitelisted evidence")
print("PASS: classification claims zero blocker reduction before materialization")
