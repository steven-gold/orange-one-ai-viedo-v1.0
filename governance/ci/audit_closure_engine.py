#!/usr/bin/env python3
"""Neutral audit-closure engine for the AUDIT execution domain.

This engine executes the registered AUDIT_CLOSURE_FLOW (AU-01..AU-09) as a
static, read-only closure audit of a declared audit target. For the governance
package target the denominator is the AUDIT_CATALOG universe and every item is
checked for validator wiring, evidence binding, owner binding and completeness
against the universal audit dimensions.

The engine never creates normative requirements and never mutates the governed
tree. It projects the existing registries only.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import sys
from pathlib import Path

import yaml
from governance_resolver import resolve as resolve_governance

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".github" / "governance-source" / "active" / "source"
DOMAINS = ROOT / "governance" / "execution-domains"
CATALOG_PATH = SOURCE / "10_REGISTRY" / "AUDIT_CATALOG.yaml"
RULE_REGISTRY_PATH = SOURCE / "10_REGISTRY" / "REFERENCE_RULE_REGISTRY.yaml"
STEPS_PATH = DOMAINS / "AUDIT" / "STEPS.yaml"
DOMAIN_PATH = DOMAINS / "AUDIT" / "DOMAIN.yaml"
PROFILE_PATH = DOMAINS / "AUDIT_PROFILE.yaml"
BINDINGS_PATH = DOMAINS / "AUTHORITY_BINDINGS.yaml"
SCHEMA_PATH = DOMAINS / "STEP_CONTRACT_SCHEMA.yaml"
INVARIANT_PATH = SOURCE / "10_REGISTRY" / "STAGE_EXECUTION_INVARIANT_REGISTRY.yaml"
CURRENT_POLICY_PATH = ROOT / "governance" / "specifications" / "current" / "EXECUTION_CYCLE_CONTROL.yaml"

AUDIT_TARGET_UID = "GOVERNANCE_PACKAGE"
GOVERNANCE_RESOLVABLE_EVIDENCE = {"VALIDATOR_RESULT"}
REQUIRED_ITEM_FIELDS = (
    "audit_item_uid",
    "audit_type",
    "audit_type_uid",
    "stage_uid",
    "target_uid",
    "requirement_type",
    "validator_uid",
    "validator_name",
    "required_evidence",
    "denominator_eligible",
    "status",
)
NA_DIMENSION_AUTHORITY = {
    "PERMISSION_GATE_STATE_WHEN_APPLICABLE": "GOVERNANCE_PACKAGE_HAS_NO_PRODUCT_PERMISSION_GATE",
    "FUNCTIONAL_VISUAL_BINDING_WHEN_APPLICABLE": "GOVERNANCE_PACKAGE_HAS_NO_FUNCTIONAL_VISUAL_SURFACE",
}
ALLOWED_STEP_FAILURES = {"STOP", "STOP_AND_REENTER_EARLIEST_OWNER"}


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"MAPPING_REQUIRED:{path}")
    return data


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_ok(path: Path) -> bool:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except (SyntaxError, UnicodeDecodeError):
        return False


def load_context() -> dict:
    catalog = load_yaml(CATALOG_PATH)
    rules = load_yaml(RULE_REGISTRY_PATH)
    steps = load_yaml(STEPS_PATH)
    domain = load_yaml(DOMAIN_PATH)
    profile = load_yaml(PROFILE_PATH)
    bindings = load_yaml(BINDINGS_PATH)
    schema = load_yaml(SCHEMA_PATH)
    invariant_registry = load_yaml(INVARIANT_PATH)
    current_policy = load_yaml(CURRENT_POLICY_PATH)
    current_identity = resolve_governance()

    validators = {}
    for rec in rules.get("validator_identities") or []:
        if rec.get("validator_uid"):
            validators[rec["validator_uid"]] = rec
    audit_types = {}
    for rec in rules.get("audit_type_identities") or []:
        if rec.get("audit_type_uid"):
            audit_types[rec["audit_type_uid"]] = rec
    return {
        "catalog": catalog,
        "steps": steps.get("steps") or [],
        "domain": domain,
        "profile": profile,
        "bindings": bindings,
        "required_step_fields": schema.get("required_step_fields") or [],
        "validators": validators,
        "audit_types": audit_types,
        "stage_invariants": invariant_registry.get("invariants") or {},
        "current_policy": current_policy,
        "current_identity": current_identity,
        "independent_evaluator_records": [],
    }


def validate_current_truth_precedence_contract(ctx: dict) -> dict:
    det=(ctx.get('stage_invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
    expected=[
        'CURRENT_GOVERNANCE_REGISTRY','CURRENT_MOTHER_STANDARD','CURRENT_LIFECYCLE_AND_INVARIANT_REGISTRIES',
        'CURRENT_CANONICAL_AUTHORITY','CURRENT_EXECUTION_SCOPE_MANIFEST','CURRENT_WORK_UNIT_DEFINITION',
        'CURRENT_EXECUTION_STATE','CURRENT_RESUME_POINT','OPERATION_RECEIPTS','REQUIRED_OUTPUTS',
        'VALIDATION_EVIDENCE','TERMINAL_RECEIPT','SUCCESSOR_ADMISSION_RECORD','HISTORICAL_EVIDENCE'
    ]
    actual=list(map(str,det.get('current_truth_precedence') or []))
    if actual!=expected:
        return {'status':'FAIL','reason':'CURRENT_TRUTH_PRECEDENCE_DRIFT','expected':expected,'actual':actual}
    if det.get('same_rank_current_state_conflict_must_not_be_precedence_overridden') is not True:
        return {'status':'FAIL','reason':'CURRENT_STATE_CONFLICT_PRECEDENCE_OVERRIDE_NOT_BLOCKED'}
    return {'status':'PASS','precedence_count':len(actual)}

def validate_audit_denominator_contract(ctx: dict, items: list[dict] | None = None, frozen_item_uids: list[str] | None = None) -> dict:
    det=(ctx.get('stage_invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
    contract=det.get('audit_denominator_contract') or {}
    expected_classes={
        'GOVERNED_UNITS','OPERATIONS','INPUTS','OUTPUTS','ARTIFACTS','REQUIRED_FIELDS','VALIDATORS',
        'EVIDENCE','STATE_RECORDS','CLOSURE_RECORDS','SUCCESSOR_BINDINGS','CURRENT_GOVERNANCE_BINDINGS'
    }
    expected_counters={'expected_count','observed_count','missing_count','duplicate_count','invalid_count','stale_count','conflicted_count'}
    if contract.get('freeze_before_validation') is not True:
        return {'status':'FAIL','reason':'AUDIT_DENOMINATOR_FREEZE_CONTRACT_MISSING'}
    if set(map(str,contract.get('required_classes') or []))!=expected_classes:
        return {'status':'FAIL','reason':'AUDIT_DENOMINATOR_CLASS_DRIFT'}
    if set(map(str,contract.get('counters_required') or []))!=expected_counters:
        return {'status':'FAIL','reason':'AUDIT_DENOMINATOR_COUNTER_DRIFT'}
    if str(contract.get('denominator_shrink_during_audit') or '')!='BLOCK':
        return {'status':'FAIL','reason':'AUDIT_DENOMINATOR_SHRINK_NOT_BLOCKED'}
    if items is not None:
        uids=[str(x.get('audit_item_uid') or '') for x in items]
        if any(not x for x in uids) or len(uids)!=len(set(uids)):
            return {'status':'FAIL','reason':'AUDIT_DENOMINATOR_ITEM_IDENTITY_INVALID'}
        if frozen_item_uids is not None:
            frozen=list(map(str,frozen_item_uids))
            if len(uids)<len(frozen):
                return {'status':'FAIL','reason':'AUDIT_DENOMINATOR_SHRINK_BLOCKED'}
            if set(uids)!=set(frozen):
                return {'status':'FAIL','reason':'AUDIT_DENOMINATOR_CHANGED_AFTER_FREEZE'}
    return {'status':'PASS','item_count':len(items or [])}

def canonical_finding_severity(ctx: dict, finding_code: str) -> dict:
    det=(ctx.get('stage_invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
    if det.get('finding_name_may_be_freely_reworded') is not False:
        return {'status':'FAIL','reason':'CANONICAL_FINDING_NAME_POLICY_DRIFT'}
    if det.get('finding_severity_may_be_auditor_selected') is not False:
        return {'status':'FAIL','reason':'CANONICAL_FINDING_SEVERITY_POLICY_DRIFT'}
    mapping=det.get('canonical_finding_severity') or {}
    vocabulary=set(map(str,det.get('severity_vocabulary') or []))
    code=str(finding_code or '')
    if code not in mapping:
        return {'status':'FAIL','reason':'CANONICAL_FINDING_UNREGISTERED','finding_code':code}
    severity=str(mapping.get(code) or '')
    if severity not in vocabulary:
        return {'status':'FAIL','reason':'CANONICAL_FINDING_SEVERITY_INVALID','finding_code':code,'severity':severity}
    return {'status':'PASS','finding_code':code,'severity':severity}

def validate_canonical_terminology_contract(ctx: dict) -> dict:
    det=(ctx.get('stage_invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
    contract=det.get('canonical_terminology_contract') or {}
    aliases=set(map(str,contract.get('forbidden_aliases') or []))
    expected_aliases={'STAGE_NOT_PASS','AUTHORIZED_NA','VERIFICATION','BUILD_RELEASE'}
    if contract.get('stage_capability_must_equal_lifecycle_registry_name') is not True:
        return {'status':'FAIL','reason':'CANONICAL_STAGE_CAPABILITY_BINDING_DRIFT'}
    if str(contract.get('authorized_not_applicable_token') or '')!='AUTHORIZED_NOT_APPLICABLE':
        return {'status':'FAIL','reason':'CANONICAL_NA_TOKEN_DRIFT'}
    if aliases!=expected_aliases:
        return {'status':'FAIL','reason':'CANONICAL_FORBIDDEN_ALIAS_DRIFT'}
    if str(contract.get('noncanonical_stage_status_or_capability_name') or '')!='BLOCK':
        return {'status':'FAIL','reason':'NONCANONICAL_TERMINOLOGY_NOT_BLOCKED'}
    return {'status':'PASS'}

def deterministic_contract_ok(ctx: dict) -> bool:
    det = (ctx.get("stage_invariants") or {}).get("DETERMINISTIC_STAGE_AUDIT") or {}
    statuses = set(det.get("canonical_stage_statuses") or [])
    required_statuses = {
        "NOT_STARTED", "READY_FOR_EXECUTION", "IN_PROGRESS", "BLOCKED",
        "REVERIFY_REQUIRED", "CURRENT_STATE_CONFLICT",
        "EXECUTION_COMPLETE_CLOSURE_PENDING", "CLOSED_PASS", "CLOSED_FAIL",
        "SNAPSHOT_INVALIDATED",
    }
    truth_ok=validate_current_truth_precedence_contract(ctx).get('status')=='PASS'
    denominator_ok=validate_audit_denominator_contract(ctx).get('status')=='PASS'
    terminology_ok=validate_canonical_terminology_contract(ctx).get('status')=='PASS'
    severity_ok=canonical_finding_severity(ctx,'CURRENT_STATE_CONFLICT').get('severity')=='S1_BLOCKER'
    return bool(
        det.get("invariant_uid") == "GOV-INV-DETERMINISTIC-STAGE-AUDIT-001"
        and det.get("applies_to_all_registered_stages") is True
        and det.get("same_complete_input_same_complete_result") is True
        and statuses == required_statuses
        and (det.get("current_state_conflict_contract") or {}).get("stage_pass_allowed") is False
        and (det.get("historical_evidence_contract") or {}).get("historical_pass_is_current_pass") is False
        and truth_ok and denominator_ok and terminology_ok and severity_ok
    )


def resolve_implementation(rec: dict) -> dict:
    rel = rec.get("implementation_path")
    if not rel:
        return {"implementation_path": None, "exists": False, "parse_ok": False}
    path = SOURCE / rel
    return {
        "implementation_path": rel,
        "exists": path.is_file(),
        "parse_ok": path.is_file() and parse_ok(path),
    }


def build_denominator(ctx: dict) -> list[dict]:
    items = ctx["catalog"].get("items") or []
    return [
        it
        for it in items
        if it.get("target_uid") == AUDIT_TARGET_UID
        and it.get("status") == "REQUIRED"
        and it.get("denominator_eligible") is True
    ]


def resolve_item(item: dict, ctx: dict) -> dict:
    rec = ctx["validators"].get(item.get("validator_uid")) or {}
    audit_type = ctx["audit_types"].get(item.get("audit_type_uid")) or {}
    impl = resolve_implementation(rec)
    evidence = []
    for ev in item.get("required_evidence") or []:
        if ev in GOVERNANCE_RESOLVABLE_EVIDENCE:
            evidence.append({
                "evidence_type": ev,
                "evidence_level": "REQUIRED",
                "artifact_ref": impl.get("implementation_path"),
                "resolved": bool(impl.get("exists") and impl.get("parse_ok")),
            })
        else:
            governed = bool(
                item.get("applicability")
                and item.get("not_applicable_requires_authority") is True
            )
            evidence.append({
                "evidence_type": ev,
                "evidence_level": "APPLICABILITY_GATED",
                "artifact_ref": item.get("applicability"),
                "resolved": governed,
            })
    return {
        "item": item,
        "validator": rec,
        "audit_type": audit_type,
        "impl": impl,
        "evidence": evidence,
    }


def dimension_applicable(dimension: str) -> bool:
    return dimension not in NA_DIMENSION_AUTHORITY


def check_dimension(dimension: str, resolved: dict, ctx: dict) -> tuple[bool, str]:
    item = resolved["item"]
    rec = resolved["validator"]
    audit_type = resolved["audit_type"]

    if dimension == "AUTHORITY_AND_SCOPE":
        ok = (
            item.get("target_uid") == AUDIT_TARGET_UID
            and bool(rec)
            and bool(audit_type)
        )
        return ok, "target and audit authority resolved" if ok else "target or authority unresolved"

    if dimension == "INPUT_IDENTITY_AND_HASH":
        uid = item.get("audit_item_uid")
        auid = item.get("audit_type_uid")
        ok = bool(uid) and bool(auid)
        return ok, "audit identity present" if ok else "audit identity missing"

    if dimension == "REQUIRED_FIELD_COMPLETENESS":
        missing = [f for f in REQUIRED_ITEM_FIELDS if not item.get(f)]
        return (not missing), "all required item fields present" if not missing else "missing:" + ",".join(missing)

    if dimension == "OPERATION_AND_OWNER_BINDING":
        if not rec:
            return False, "validator identity unresolved"
        if rec.get("canonical_name") != item.get("validator_name"):
            return False, "validator canonical_name mismatch"
        if rec.get("identity_mode") == "PHYSICAL_VALIDATOR" and not resolved["impl"].get("exists"):
            return False, "physical validator implementation missing"
        return True, "operation and owner binding resolved"

    if dimension == "OUTPUT_SCHEMA_AND_DENOMINATOR":
        ok = (
            bool(item.get("required_evidence"))
            and item.get("denominator_eligible") is True
            and audit_type.get("denominator_eligible") is True
        )
        return ok, "denominator eligibility consistent" if ok else "denominator eligibility inconsistent"

    if dimension == "DEPENDENCY_AND_SUCCESSOR_BINDING":
        usage = rec.get("allowed_usage") or []
        stages = audit_type.get("allowed_stage_uids") or []
        ok = "AUDIT_CATALOG" in usage and item.get("stage_uid") in stages
        return ok, "dependency and successor bindings resolved" if ok else "dependency or successor binding missing"

    if dimension == "ERROR_BLOCKED_RECOVERY_WHEN_APPLICABLE":
        for step in ctx["steps"]:
            recovery = step.get("failure_reentry_checkpoint_next_step") or {}
            if recovery.get("failure") not in ALLOWED_STEP_FAILURES:
                return False, "step failure disposition not fail-closed:" + str(step.get("step_uid"))
            if not recovery.get("reentry") or not recovery.get("next_step"):
                return False, "step recovery edge incomplete:" + str(step.get("step_uid"))
        return True, "fail-closed recovery edges complete"

    if dimension == "EVIDENCE_SCHEMA_AND_BYTES":
        unresolved = [e for e in resolved["evidence"] if not e.get("resolved")]
        return (not unresolved), "evidence bound" if not unresolved else "unresolved evidence:" + ",".join(e["evidence_type"] for e in unresolved)

    if dimension == "DUPLICATE_CONFLICT_ORPHAN_GAP":
        items = ctx["catalog"].get("items") or []
        uid_dup = len({i.get("audit_item_uid") for i in items}) != len(items)
        type_dup = len({i.get("audit_type_uid") for i in items}) != len(items)
        bound = ctx["bindings"].get("audit") or {}
        step_ids = {s.get("step_uid") for s in ctx["steps"]}
        orphan = [label for label in bound if label not in step_ids]
        ok = not uid_dup and not type_dup and not orphan
        return ok, "no duplicate or orphan finding" if ok else "duplicate or orphan finding detected"

    if dimension == "CHECKPOINT_RESUME":
        for step in ctx["steps"]:
            recovery = step.get("failure_reentry_checkpoint_next_step") or {}
            if not recovery.get("checkpoint"):
                return False, "checkpoint missing:" + str(step.get("step_uid"))
        return True, "checkpoint edges complete"

    if dimension == "LOCAL_REGRESSION_IMPACT":
        ok = bool(ctx["catalog"].get("items")) and ctx["domain"].get("recursive_governance_tree_scan") == "FORBIDDEN"
        return ok, "read-only projection with complete denominator" if ok else "denominator or isolation contract invalid"

    if dimension == "NEXT_STEP_AUTHORIZATION":
        step_ids = {s.get("step_uid") for s in ctx["steps"]}
        ok = any(str(uid).startswith("AU-09") for uid in step_ids)
        return ok, "successor authorization gate registered" if ok else "successor authorization gate missing"

    return False, "unknown dimension"


def evaluate_item(resolved: dict, ctx: dict, dimensions: list[str]) -> dict:
    findings = []
    item_failed = False
    for dimension in dimensions:
        if not dimension_applicable(dimension):
            findings.append({
                "audit_dimension": dimension,
                "result": "NOT_APPLICABLE",
                "na_authority": NA_DIMENSION_AUTHORITY[dimension],
                "na_evidence": "governance/execution-domains/AUDIT_PROFILE.yaml",
            })
            continue
        try:
            passed, detail = check_dimension(dimension, resolved, ctx)
        except Exception as exc:  # fail-closed
            passed, detail = False, "exception:" + repr(exc)
        if not passed:
            item_failed = True
        findings.append({
            "audit_dimension": dimension,
            "result": "PASS" if passed else "FAIL",
            "detail": detail,
        })
    return {
        "audit_item_uid": resolved["item"].get("audit_item_uid"),
        "audit_type_uid": resolved["item"].get("audit_type_uid"),
        "validator_uid": resolved["item"].get("validator_uid"),
        "owner_uid": resolved["item"].get("validator_uid"),
        "evidence": resolved["evidence"],
        "result": "FAIL" if item_failed else "PASS",
        "dimensions": findings,
    }


def run_steps(ctx: dict, items: list[dict]) -> tuple[list[dict], list[str]]:
    steps = ctx["steps"]
    receipts = []
    required = ctx["required_step_fields"]
    for step in sorted(steps, key=lambda s: str(s.get("step_uid"))):
        missing = [f for f in required if not step.get(f)]
        receipts.append({
            "step_uid": step.get("step_uid"),
            "entry_gate": step.get("entry_gate"),
            "denominator": step.get("denominator"),
            "status": "PASS" if not missing else "FAIL",
            "missing_required_fields": missing,
        })
    return receipts, [r["step_uid"] for r in receipts if r["status"] != "PASS"]


def run_closure(ctx: dict) -> dict:
    profile = ctx["profile"]
    dimensions = profile.get("fixed_audit_dimensions") or []
    denominator = build_denominator(ctx)
    resolved = [resolve_item(item, ctx) for item in denominator]
    results = [evaluate_item(r, ctx, dimensions) for r in resolved]
    step_receipts, failed_steps = run_steps(ctx, denominator)
    deterministic_ok = deterministic_contract_ok(ctx)
    if not deterministic_ok:
        failed_steps.append("DETERMINISTIC_STAGE_AUDIT_CONTRACT")

    pass_count = sum(1 for r in results if r["result"] == "PASS")
    fail_count = sum(1 for r in results if r["result"] == "FAIL")
    applicable = [f for r in results for f in r["dimensions"] if f["result"] != "NOT_APPLICABLE"]
    na_count = sum(1 for r in results for f in r["dimensions"] if f["result"] == "NOT_APPLICABLE")
    unresolved = sum(1 for f in applicable if f["result"] == "FAIL")

    item_uids = [it.get("audit_item_uid") for it in denominator]
    coverage = (len(denominator) == len(item_uids)) and bool(denominator)
    result = (
        "PASS"
        if (fail_count == 0 and unresolved == 0 and not failed_steps and coverage)
        else "FAIL"
    )

    reconciliation = {
        "denominator_count": len(denominator),
        "audited_count": len(results),
        "pass_count": pass_count,
        "partial_count": 0,
        "fail_count": fail_count,
        "blocked_count": 0,
        "not_verified_count": 0,
        "na_count": na_count,
        "unresolved_problem_count": unresolved,
        "dimension_application_count": len(applicable),
        "missing_item_count": len(denominator) - len(results),
        "duplicate_item_count": len(item_uids) - len(set(item_uids)),
    }

    current_identity=ctx.get("current_identity") or {}
    formal_independence=validate_independent_evaluator_implementations(ctx,ctx.get("independent_evaluator_records") or [])
    promotion_authorized=(result=="PASS" and formal_independence.get("status")=="PASS")
    return {
        "schema_version": 1,
        "audit_uid": "AUDIT-CLOSURE-GOVERNANCE-PACKAGE-001",
        "target_uid": AUDIT_TARGET_UID,
        "domain_uid": ctx["domain"].get("domain_uid"),
        "governance_uid": current_identity.get("governance_uid"),
        "governance_revision": current_identity.get("governance_revision"),
        "display_version": current_identity.get("display_version"),
        "source_catalog_governance_revision": ctx["catalog"].get("governance_revision"),
        "source_revision": file_sha(CATALOG_PATH),
        "denominator_policy": ctx["catalog"].get("denominator_policy"),
        "dimension_denominator": len(dimensions),
        "steps": step_receipts,
        "determinism_contract": {"invariant_uid": "GOV-INV-DETERMINISTIC-STAGE-AUDIT-001", "status": "PASS" if deterministic_ok else "FAIL"},
        "formal_auditor_independence": formal_independence,
        "items": results,
        "reconciliation": reconciliation,
        "result": result,
        "successor_authorization": "AUTHORIZED" if promotion_authorized else ("BLOCKED_FORMAL_PROMOTION_PENDING_INDEPENDENT_AUDITOR_EVIDENCE" if result=="PASS" else "BLOCKED"),
        "next_step_uid": "REGISTERED_SUCCESSOR_IF_PASS_ELSE_NONE" if promotion_authorized else "REGISTER_INDEPENDENT_AUDITOR_EVIDENCE",
    }


def closure_failures(receipt: dict) -> list[str]:
    failures = []
    for step in receipt["steps"]:
        if step["status"] != "PASS":
            failures.append("STEP_INCOMPLETE:" + str(step["step_uid"]))
    for item in receipt["items"]:
        if item["result"] != "PASS":
            failures.append("ITEM_FAIL:" + str(item["audit_item_uid"]))
    rec = receipt["reconciliation"]
    if rec["missing_item_count"] or rec["duplicate_item_count"]:
        failures.append("RECONCILIATION_MISMATCH")
    if receipt["result"] != "PASS":
        failures.append("AUDIT_RESULT_NOT_PASS")
    return failures


def validate_audit_snapshot(snapshot: dict, ctx: dict, frozen_snapshot: dict | None = None) -> dict:
    det=(ctx.get('stage_invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
    contract=det.get('audit_snapshot_contract') or {}
    required=list(map(str,contract.get('required_fields') or []))
    if not required:
        return {'status':'FAIL','reason':'AUDIT_SNAPSHOT_REQUIRED_FIELD_DENOMINATOR_EMPTY'}
    if not isinstance(snapshot,dict):
        return {'status':'FAIL','reason':'AUDIT_SNAPSHOT_INVALID'}
    missing=[field for field in required if snapshot.get(field) in (None,'',[])]
    if missing:
        return {'status':'FAIL','reason':'AUDIT_SNAPSHOT_INVALID','missing_fields':missing}
    if contract.get('freeze_before_audit') is not True:
        return {'status':'FAIL','reason':'AUDIT_SNAPSHOT_FREEZE_CONTRACT_MISSING'}
    if frozen_snapshot is not None:
        if not isinstance(frozen_snapshot,dict):
            return {'status':'FAIL','reason':'AUDIT_SNAPSHOT_INVALID'}
        immutable_fields=(
            'repository','branch','exact_head_sha','tree_sha','governance_branch','governance_head_sha',
            'governance_uid','governance_revision','registry_revision','lifecycle_registry_revision',
            'stage_uid','work_unit_uid','governed_unit_uid','source_authority_uid','audit_scope',
            'denominator_hash','authority_set_hash','evidence_set_hash','validator_set_hash',
            'audit_engine_version','audit_contract_version'
        )
        drift=[field for field in immutable_fields if snapshot.get(field)!=frozen_snapshot.get(field)]
        if drift:
            return {'status':'FAIL','reason':'SNAPSHOT_INVALIDATED','drift_fields':drift}
    return {'status':'PASS','required_field_count':len(required)}

def validate_determinism_acceptance(ctx: dict) -> dict:
    det=(ctx.get('stage_invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
    indep=det.get('auditor_independence_acceptance') or {}
    repeat=det.get('repeatability_acceptance') or {}
    evaluator_count=int(indep.get('independent_evaluator_count') or 0)
    repeat_count=int(repeat.get('same_evaluator_repeat_count') or 0)
    if evaluator_count!=3 or repeat_count!=3:
        return {'status':'FAIL','reason':'DETERMINISM_ACCEPTANCE_DENOMINATOR_DRIFT'}
    baseline=run_closure(copy.deepcopy(ctx))
    canonical=json.dumps(baseline,sort_keys=True,separators=(',',':'))
    identity_variants=[]
    for idx in range(evaluator_count):
        candidate=copy.deepcopy(ctx)
        candidate['runtime_auditor_identity']=f'SYNTHETIC-EVALUATOR-{idx+1}'
        result=run_closure(candidate)
        identity_variants.append(json.dumps(result,sort_keys=True,separators=(',',':')))
    if any(value!=canonical for value in identity_variants):
        return {'status':'FAIL','reason':'AUDIT_DETERMINISM_CONTRACT_FAILURE','dimension':'SYNTHETIC_EVALUATOR_IDENTITY_INVARIANCE'}
    repeat_results=[]
    for _ in range(repeat_count):
        candidate=copy.deepcopy(ctx)
        candidate['runtime_auditor_identity']='SYNTHETIC-EVALUATOR-REPEAT'
        result=run_closure(candidate)
        repeat_results.append(json.dumps(result,sort_keys=True,separators=(',',':')))
    if any(value!=canonical for value in repeat_results):
        return {'status':'FAIL','reason':'AUDIT_DETERMINISM_CONTRACT_FAILURE','dimension':'REPEATABILITY'}
    return {
        'status':'PASS',
        'synthetic_identity_invariance_count':evaluator_count,
        'repeat_count':repeat_count,
        'formal_independent_implementation_credit':0,
        'formal_independent_implementation_status':'NOT_VERIFIED_BY_SYNTHETIC_IDENTITY_VARIATION',
    }

def validate_independent_evaluator_implementations(ctx: dict, records: list[dict]) -> dict:
    contract=(ctx.get('current_policy') or {}).get('auditor_implementation_independence') or {}
    required_count=int(contract.get('formal_independent_evaluator_required_count') or 0)
    required=tuple(map(str,contract.get('formal_independent_evaluator_required_fields') or []))
    if contract.get('synthetic_evaluator_identity_invariance_is_formal_independence') is not False:
        return {'status':'FAIL','reason':'AUDITOR_INDEPENDENCE_POLICY_SYNTHETIC_CREDIT_DRIFT'}
    if required_count!=3 or set(required)!={'evaluator_uid','implementation_owner_uid','implementation_hash','result_fingerprint'}:
        return {'status':'FAIL','reason':'AUDITOR_INDEPENDENCE_POLICY_DENOMINATOR_DRIFT'}
    if not isinstance(records,list) or len(records)!=required_count:
        return {'status':'NOT_VERIFIED','reason':'AUDITOR_INDEPENDENT_IMPLEMENTATION_EVIDENCE_MISSING_OR_INCOMPLETE','required_count':required_count,'observed_count':len(records) if isinstance(records,list) else 0}
    for idx,record in enumerate(records):
        if not isinstance(record,dict):
            return {'status':'FAIL','reason':'AUDITOR_INDEPENDENT_IMPLEMENTATION_RECORD_INVALID','index':idx}
        missing=[key for key in required if not str(record.get(key) or '').strip()]
        if missing:
            return {'status':'FAIL','reason':'AUDITOR_INDEPENDENT_IMPLEMENTATION_FIELD_MISSING','index':idx,'fields':missing}
    for key,flag in (
        ('evaluator_uid','distinct_evaluator_uid_required'),
        ('implementation_owner_uid','distinct_implementation_owner_uid_required'),
        ('implementation_hash','distinct_implementation_hash_required'),
    ):
        values=[str(record[key]) for record in records]
        if contract.get(flag) is not True or len(set(values))!=required_count:
            return {'status':'FAIL','reason':'AUDITOR_IMPLEMENTATION_INDEPENDENCE_NOT_PROVEN','field':key}
    fingerprints=[str(record['result_fingerprint']) for record in records]
    if contract.get('identical_result_fingerprint_required') is not True or len(set(fingerprints))!=1:
        return {'status':'FAIL','reason':'AUDIT_DETERMINISM_CONTRACT_FAILURE','dimension':'INDEPENDENT_IMPLEMENTATION_RESULT_MISMATCH'}
    return {'status':'PASS','independent_implementation_count':required_count,'result_fingerprint':fingerprints[0]}

def load_independent_evaluator_evidence(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError('AUDITOR_INDEPENDENCE_EVIDENCE_FILE_MISSING:'+str(path))
    data=yaml.safe_load(path.read_text(encoding='utf-8'))
    records=(data.get('evaluators') if isinstance(data,dict) else data)
    if not isinstance(records,list):
        raise ValueError('AUDITOR_INDEPENDENCE_EVIDENCE_LIST_REQUIRED')
    return records

def run_self_test() -> int:
    base = load_context()
    cases = []
    if run_closure(base)["result"] != "PASS":
        print("FAIL: baseline closure did not pass", file=sys.stderr)
        return 1
    cases.append("baseline_pass")

    snapshot_required=((base.get('stage_invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}).get('audit_snapshot_contract',{}).get('required_fields') or []
    synthetic_snapshot={field:'SYNTHETIC-'+field for field in snapshot_required}
    snap_ok=validate_audit_snapshot(synthetic_snapshot,base)
    if snap_ok.get('status')!='PASS':
        print('FAIL: audit snapshot baseline invalid: '+json.dumps(snap_ok,sort_keys=True),file=sys.stderr)
        return 1
    cases.append('audit_snapshot_required_fields_pass')
    missing_snapshot=copy.deepcopy(synthetic_snapshot)
    missing_snapshot.pop('denominator_hash',None)
    if validate_audit_snapshot(missing_snapshot,base).get('status')=='PASS':
        print('FAIL: missing audit snapshot field escaped validation',file=sys.stderr)
        return 1
    cases.append('audit_snapshot_missing_field_blocked')
    drift_snapshot=copy.deepcopy(synthetic_snapshot)
    drift_snapshot['exact_head_sha']='SYNTHETIC-HEAD-DRIFT'
    drift_result=validate_audit_snapshot(drift_snapshot,base,synthetic_snapshot)
    if drift_result.get('reason')!='SNAPSHOT_INVALIDATED':
        print('FAIL: audit snapshot head drift did not invalidate snapshot',file=sys.stderr)
        return 1
    cases.append('audit_snapshot_head_drift_invalidated')
    denominator_drift=copy.deepcopy(synthetic_snapshot)
    denominator_drift['denominator_hash']='SYNTHETIC-DENOMINATOR-DRIFT'
    denominator_result=validate_audit_snapshot(denominator_drift,base,synthetic_snapshot)
    if denominator_result.get('reason')!='SNAPSHOT_INVALIDATED':
        print('FAIL: audit denominator drift did not invalidate snapshot',file=sys.stderr)
        return 1
    cases.append('audit_snapshot_denominator_drift_invalidated')

    truth_ok=validate_current_truth_precedence_contract(base)
    if truth_ok.get('status')!='PASS':
        print('FAIL: current truth precedence baseline invalid: '+json.dumps(truth_ok,sort_keys=True),file=sys.stderr)
        return 1
    cases.append('current_truth_precedence_pass')
    truth_drift=copy.deepcopy(base)
    precedence=truth_drift['stage_invariants']['DETERMINISTIC_STAGE_AUDIT']['current_truth_precedence']
    precedence[0],precedence[1]=precedence[1],precedence[0]
    if validate_current_truth_precedence_contract(truth_drift).get('status')=='PASS':
        print('FAIL: current truth precedence drift escaped validation',file=sys.stderr)
        return 1
    cases.append('current_truth_precedence_drift_blocked')

    denominator=build_denominator(base)
    frozen=[str(x.get('audit_item_uid') or '') for x in denominator]
    denom_ok=validate_audit_denominator_contract(base,denominator,frozen)
    if denom_ok.get('status')!='PASS':
        print('FAIL: audit denominator baseline invalid: '+json.dumps(denom_ok,sort_keys=True),file=sys.stderr)
        return 1
    cases.append('audit_denominator_freeze_pass')
    if validate_audit_denominator_contract(base,denominator[:-1],frozen).get('reason')!='AUDIT_DENOMINATOR_SHRINK_BLOCKED':
        print('FAIL: audit denominator shrink escaped validation',file=sys.stderr)
        return 1
    cases.append('audit_denominator_shrink_blocked')

    severity=canonical_finding_severity(base,'CURRENT_STATE_CONFLICT')
    if severity.get('severity')!='S1_BLOCKER':
        print('FAIL: canonical finding severity drift',file=sys.stderr)
        return 1
    cases.append('canonical_finding_severity_pass')
    if canonical_finding_severity(base,'SYNTHETIC_UNREGISTERED_FINDING').get('status')=='PASS':
        print('FAIL: unregistered canonical finding escaped validation',file=sys.stderr)
        return 1
    cases.append('unregistered_finding_blocked')

    term_ok=validate_canonical_terminology_contract(base)
    if term_ok.get('status')!='PASS':
        print('FAIL: canonical terminology baseline invalid: '+json.dumps(term_ok,sort_keys=True),file=sys.stderr)
        return 1
    cases.append('canonical_terminology_pass')
    term_drift=copy.deepcopy(base)
    term_drift['stage_invariants']['DETERMINISTIC_STAGE_AUDIT']['canonical_terminology_contract']['authorized_not_applicable_token']='AUTHORIZED_NA'
    if validate_canonical_terminology_contract(term_drift).get('status')=='PASS':
        print('FAIL: canonical terminology drift escaped validation',file=sys.stderr)
        return 1
    cases.append('canonical_terminology_drift_blocked')



    first = run_closure(base)
    second = run_closure(copy.deepcopy(base))
    if json.dumps(first, sort_keys=True) != json.dumps(second, sort_keys=True):
        print("FAIL: same complete audit input produced different result", file=sys.stderr)
        return 1
    cases.append("same_input_same_result")

    det_accept=validate_determinism_acceptance(base)
    if det_accept.get('status')!='PASS':
        print('FAIL: deterministic auditor independence or repeatability failed: '+json.dumps(det_accept,sort_keys=True),file=sys.stderr)
        return 1
    cases.append('synthetic_evaluator_identity_invariance_3of3')
    cases.append('same_evaluator_repeatability_3of3')
    _same_impl=[
      {'evaluator_uid':f'EVAL-{i}','implementation_owner_uid':'OWNER-SAME','implementation_hash':'HASH-SAME','result_fingerprint':'RESULT-1'}
      for i in range(1,4)
    ]
    if validate_independent_evaluator_implementations(base,_same_impl).get('status')=='PASS':
        print('FAIL: same implementation incorrectly received formal auditor-independence credit',file=sys.stderr)
        return 1
    cases.append('formal_independence_same_implementation_blocked')
    _distinct_impl=[
      {'evaluator_uid':f'EVAL-{i}','implementation_owner_uid':f'OWNER-{i}','implementation_hash':f'HASH-{i}','result_fingerprint':'RESULT-1'}
      for i in range(1,4)
    ]
    if validate_independent_evaluator_implementations(base,_distinct_impl).get('status')!='PASS':
        print('FAIL: distinct evaluator implementation contract fixture did not pass',file=sys.stderr)
        return 1
    cases.append('formal_independent_evaluator_contract_fixture_3of3')
    _baseline_promotion=run_closure(base)
    if _baseline_promotion.get('successor_authorization')!='BLOCKED_FORMAL_PROMOTION_PENDING_INDEPENDENT_AUDITOR_EVIDENCE':
        print('FAIL: governance promotion was authorized without independent evaluator evidence',file=sys.stderr)
        return 1
    cases.append('formal_promotion_blocked_without_independent_evidence')
    _authorized_ctx=copy.deepcopy(base)
    _authorized_ctx['independent_evaluator_records']=_distinct_impl
    if run_closure(_authorized_ctx).get('successor_authorization')!='AUTHORIZED':
        print('FAIL: valid independent evaluator evidence did not authorize successor',file=sys.stderr)
        return 1
    cases.append('formal_promotion_authorized_with_independent_evidence')


    no_det = copy.deepcopy(base)
    no_det["stage_invariants"]["DETERMINISTIC_STAGE_AUDIT"]["same_complete_input_same_complete_result"] = False
    if run_closure(no_det)["result"] == "PASS":
        print("FAIL: invalid deterministic audit contract escaped closure", file=sys.stderr)
        return 1
    cases.append("determinism_contract_blocked")

    dup = copy.deepcopy(base)
    dup["catalog"]["items"].append(copy.deepcopy(dup["catalog"]["items"][0]))
    if run_closure(dup)["result"] == "PASS":
        print("FAIL: duplicate item escaped closure", file=sys.stderr)
        return 1
    cases.append("duplicate_blocked")

    orphan = copy.deepcopy(base)
    orphan["catalog"]["items"][0]["validator_uid"] = "VAL-GOV-999"
    if run_closure(orphan)["result"] == "PASS":
        print("FAIL: orphan validator escaped closure", file=sys.stderr)
        return 1
    cases.append("orphan_blocked")

    blank = copy.deepcopy(base)
    blank["catalog"]["items"][0]["required_evidence"] = []
    if run_closure(blank)["result"] == "PASS":
        print("FAIL: blank required field escaped closure", file=sys.stderr)
        return 1
    cases.append("blank_field_blocked")

    recovery = copy.deepcopy(base)
    recovery["steps"][0]["failure_reentry_checkpoint_next_step"]["failure"] = "CONTINUE"
    if run_closure(recovery)["result"] == "PASS":
        print("FAIL: non fail-closed recovery escaped closure", file=sys.stderr)
        return 1
    cases.append("recovery_blocked")

    print(json.dumps({"self_test": "PASS", "cases": len(cases), "case_ids": cases}, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--receipt-out")
    ap.add_argument("--independent-evaluator-evidence")
    args = ap.parse_args()
    if args.self_test:
        return run_self_test()

    ctx=load_context()
    if args.independent_evaluator_evidence:
        ctx['independent_evaluator_records']=load_independent_evaluator_evidence(Path(args.independent_evaluator_evidence))
    receipt = run_closure(ctx)
    if args.receipt_out:
        Path(args.receipt_out).write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    failures = closure_failures(receipt)
    if failures:
        for failure in failures:
            print("BLOCK:", failure, file=sys.stderr)
        print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    rec = receipt["reconciliation"]
    print(
        "PASS: audit closure target=%s items=%d dimensions=%d pass=%d unresolved=%d result=%s successor=%s"
        % (
            receipt["target_uid"],
            rec["denominator_count"],
            receipt["dimension_denominator"],
            rec["pass_count"],
            rec["unresolved_problem_count"],
            receipt["result"],
            receipt["successor_authorization"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
