#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import hashlib
import json
import copy
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"

def die(msg: str) -> None:
    print("BLOCK:", msg, file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    if not path.is_file():
        die(f"MISSING:{path.relative_to(ROOT)}")
    try:
        obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        die(f"PARSE:{path.relative_to(ROOT)}:{exc!r}")
    if not isinstance(obj, dict):
        die(f"MAPPING_REQUIRED:{path.relative_to(ROOT)}")
    return obj


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index(items, key):
    return {x.get(key): x for x in (items or []) if isinstance(x, dict) and x.get(key)}


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def external_refs(blueprint: dict):
    refs = []
    for ref in blueprint.get("unresolved_external_authority_refs") or []:
        refs.append({
            "gap_uid": ref.get("gap_uid"),
            "authority_ref": ref.get("authority_ref"),
            "resolved": False,
            "satisfied": False,
            "auto_filled": False,
            "inferred": False,
            "source_evidence_ref": ref.get("authority_evidence_ref"),
        })
    return refs


def port_refs(action: dict):
    rb = action.get("runtime_binding") or {}
    result = []
    for field in ("port_uid", "persist_via_port_uid", "execute_port_uid", "decision_port_uid"):
        value = rb.get(field)
        if value:
            result.append({"field": field, "port_uid": value})
    return result



def _require_record_schema(record: dict, required: dict, context: str) -> None:
    for field, typ in required.items():
        if field not in record or record.get(field) in (None, ''):
            raise SystemExit(f'BLOCK: PRODUCER_CONSUMER_SCHEMA_MISMATCH:{context}:missing:{field}')
        if typ is not None and not isinstance(record.get(field), typ):
            raise SystemExit(f'BLOCK: PRODUCER_CONSUMER_SCHEMA_MISMATCH:{context}:type:{field}')
    if context == 'STAGE02_AUDIT_EVENT_BINDING' and 'event_uid' in record and 'audit_event_uid' not in record:
        raise SystemExit('BLOCK: PRODUCER_CONSUMER_SCHEMA_MISMATCH:STAGE02_AUDIT_EVENT_BINDING:event_uid_alias_forbidden')

def _deterministic_system_trigger(action_uid: str, action: dict, raw_reg: dict):
    controls=[x for x in (raw_reg.get('controls') or []) if isinstance(x,dict) and x.get('action_uid')==action_uid]
    if controls:
        return None
    rb=action.get('runtime_binding') or {}
    decision=str(rb.get('decision') or '')
    if decision not in {'SOURCE_DERIVED','SOURCE_DERIVED_CLOSURE'}:
        return None
    ports=index(raw_reg.get('integration_ports'),'port_uid')
    refs=[]
    for field in ('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid'):
        puid=rb.get(field)
        if puid and puid in ports:
            refs.append((field,puid,ports[puid]))
    uniq={puid:(field,port) for field,puid,port in refs}
    if len(uniq)!=1:
        return None
    puid,(field,port)=next(iter(uniq.items()))
    operation=port.get('operation') or port.get('registered_operation')
    permission=port.get('permission') or port.get('registered_permission')
    state_event=str(port.get('state_event') or '')
    if not operation or not permission or not state_event or not action.get('gate_uid') or not action.get('permission_uid'):
        return None
    return {'trigger_kind':'SYSTEM_DERIVED_GOVERNED_OPERATION','source_decision':decision,'gate_uid':action.get('gate_uid'),'runtime_port_uid':puid,'runtime_port_binding_field':field,'registered_operation':operation,'success_state_event':state_event,'user_control_required':False}

def _self_test_shared_contract_hardening():
    good={'action_uid':'ACT-1','gate_uid':'GATE-1','permission_uid':'PERM-1','runtime_binding':{'port_uid':'PORT-1','decision':'SOURCE_DERIVED'}}
    reg={'controls':[],'integration_ports':[{'port_uid':'PORT-1','registered_operation':'createRecord','registered_permission':'record.write','state_event':'REVIEW->OPEN | record.created'}]}
    assert _deterministic_system_trigger('ACT-1',good,reg)
    bad=copy.deepcopy(good); bad['runtime_binding'].pop('decision')
    assert _deterministic_system_trigger('ACT-1',bad,reg) is None
    _require_record_schema({'action_uid':'ACT-1','audit_event_uid':'audit.record.created'},{'action_uid':str,'audit_event_uid':str},'STAGE02_AUDIT_EVENT_BINDING')
    try:
        _require_record_schema({'action_uid':'ACT-1','event_uid':'audit.record.created'},{'action_uid':str,'audit_event_uid':str},'STAGE02_AUDIT_EVENT_BINDING')
    except SystemExit:
        pass
    else:
        raise AssertionError('event_uid alias unexpectedly accepted')
    print('PASS: Stage-02 materializer shared trigger/schema self-test')

def _current_design_context():
    scope_path = ROOT / "governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml"
    state = load(STATE)
    scope = load(scope_path)
    if state.get("current_primary_task_layer") != "PRODUCT_STAGE_EXECUTION":
        die(f"APPROVED_DESIGN_MATERIALIZATION_REQUIRES_PRODUCT_LAYER:{state.get('current_primary_task_layer')!r}")
    work = state.get("active_work_unit") or {}
    if work.get("stage_uid") != "STAGE-02" or work.get("semantic_capability") != "PAGE_FUNCTIONAL_CONTRACT":
        die(f"CURRENT_STAGE02_PRODUCT_WORK_UNIT_REQUIRED:{work.get('work_unit_uid')!r}")
    if work.get("current_status") != "EXACT_CLOSURES_REVALIDATED_REVIEW_ONLY_PRODUCT_AUTHORITY_REQUIRED":
        die(f"CURRENT_STAGE02_DESIGN_REVIEW_STATE_REQUIRED:{work.get('current_status')!r}")
    pages = list(scope.get("included_units") or [])
    if len(pages) != 1 or work.get("scope") != pages:
        die(f"CURRENT_SCOPE_WORK_UNIT_DRIFT:{pages!r}:{work.get('scope')!r}")
    page = pages[0]
    owner = str(work.get("canonical_owner") or "")
    marker = "/04_PAGE_FUNCTIONAL_CONTRACT/"
    if marker not in owner:
        die("CURRENT_RUN_ROOT_UNRESOLVED")
    run_root = ROOT / owner.split(marker, 1)[0]
    product_root = run_root / "04_PAGE_FUNCTIONAL_CONTRACT"
    page_root = product_root / page
    raw_dir = run_root / "00_SOURCE_INTAKE/RAW_SOURCE" / page
    raw_candidates = sorted(p for p in raw_dir.glob("*.yaml") if p.is_file())
    if len(raw_candidates) != 1:
        die(f"CURRENT_RAW_SOURCE_IDENTITY_AMBIGUOUS:{[str(x.relative_to(ROOT)) for x in raw_candidates]!r}")
    blueprint_path = run_root / "02_BASE_BLUEPRINT" / page / "PAGE_BASE_BLUEPRINT.yaml"
    paths = {
        "scope": scope_path,
        "problem": product_root / "CURRENT_PROBLEM_REGISTER.yaml",
        "candidate": page_root / "DESIGN_CONTRACT_CANDIDATE.yaml",
        "semantic_review": page_root / "REMEDIATION_SEMANTIC_REVIEW.yaml",
        "chain": page_root / "FUNCTIONAL_CHAIN_SPEC.yaml",
        "raw": raw_candidates[0],
        "blueprint": blueprint_path,
        "approval": page_root / "DESIGN_CONTRACT_APPROVAL_EVIDENCE.yaml",
        "receipt": page_root / "DESIGN_CONTRACT_MATERIALIZATION_RECEIPT.yaml",
    }
    for label, path in paths.items():
        if label in {"approval", "receipt"}:
            continue
        if not path.is_file():
            die(f"CURRENT_DESIGN_INPUT_MISSING:{label}:{path.relative_to(ROOT)}")
    if paths["approval"].exists() or paths["receipt"].exists():
        die("APPROVED_DESIGN_MATERIALIZATION_EVIDENCE_ALREADY_EXISTS_REFUSE_OVERWRITE")
    return state, scope, work, page, run_root, product_root, page_root, paths

def _profile_for_entity(entity: str) -> str:
    mapping = {
        "LockedBlueprintRef": "EXTERNAL_REFERENCE",
        "AssetProductionScriptViewRef": "EXTERNAL_REFERENCE",
        "DNABindingRef": "EXTERNAL_REFERENCE",
        "AssetManifestRef": "EXTERNAL_REFERENCE",
        "SystemOutputNamingRef": "EXTERNAL_REFERENCE",
        "InstructionPackageRef": "EXTERNAL_REFERENCE",
        "ProviderRouteSnapshotRef": "EXTERNAL_REFERENCE",
        "AssetExecutionInputManifest": "EXECUTION_MANIFEST",
        "AssetCandidateOutput": "CANDIDATE_OUTPUT",
        "AssetEvaluation": "EVALUATION_RECORD",
        "AssetFinding": "FINDING_RECORD",
        "AssetCorrectionContext": "CORRECTION_CONTEXT",
        "CorrectionScriptCandidate": "CORRECTION_SCRIPT",
        "VersionedLayerDocument": "LAYER_DOCUMENT",
        "AssetPatch": "ASSET_PATCH",
        "AssetOutputVersion": "ASSET_VERSION",
        "AssetScorecard": "SCORECARD",
        "AssetHandoffManifest": "HANDOFF_MANIFEST",
    }
    profile = mapping.get(str(entity))
    if not profile:
        die(f"ENTITY_PROFILE_UNRESOLVED:{entity!r}")
    return profile


def _entity_operation_contract(objects: dict) -> dict:
    vocabulary = [
        "READ", "CREATE", "UPDATE", "VALIDATE", "EXECUTE", "EVALUATE",
        "DECIDE", "VERSION", "LOCK", "RESTORE", "HANDOFF", "RETRY",
        "AUDIT", "ERROR_RECOVERY",
    ]
    profiles = {
        "EXTERNAL_REFERENCE": {"required": ["READ", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "EXECUTION_MANIFEST": {"required": ["READ", "CREATE", "VALIDATE", "EXECUTE", "AUDIT", "ERROR_RECOVERY"], "optional": ["RETRY"]},
        "CANDIDATE_OUTPUT": {"required": ["READ", "CREATE", "VALIDATE", "DECIDE", "VERSION", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "EVALUATION_RECORD": {"required": ["READ", "CREATE", "VALIDATE", "EVALUATE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "FINDING_RECORD": {"required": ["READ", "CREATE", "UPDATE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "CORRECTION_CONTEXT": {"required": ["READ", "CREATE", "UPDATE", "VALIDATE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "CORRECTION_SCRIPT": {"required": ["READ", "CREATE", "VALIDATE", "DECIDE", "VERSION", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "LAYER_DOCUMENT": {"required": ["READ", "CREATE", "UPDATE", "VERSION", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "ASSET_PATCH": {"required": ["READ", "CREATE", "VALIDATE", "DECIDE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "ASSET_VERSION": {"required": ["READ", "CREATE", "VERSION", "LOCK", "RESTORE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "SCORECARD": {"required": ["READ", "CREATE", "VALIDATE", "EVALUATE", "AUDIT", "ERROR_RECOVERY"], "optional": []},
        "HANDOFF_MANIFEST": {"required": ["READ", "CREATE", "VALIDATE", "HANDOFF", "AUDIT", "ERROR_RECOVERY"], "optional": []},
    }
    bindings = []
    for oid, obj in objects.items():
        bindings.append({"object_uid": oid, "profile": _profile_for_entity(obj.get("entity"))})
    return {
        "authority_source": "CURRENT_OBJECT_REGISTRY_AND_APPROVED_STAGE02_ASSET_DESIGN_REMEDIATION",
        "operation_vocabulary": vocabulary,
        "profile_rule": "Operations not REQUIRED or OPTIONAL by the bound profile are NOT_APPLICABLE.",
        "profiles": profiles,
        "entity_profile_bindings": bindings,
    }


def _entity_hierarchy_contract(objects: dict) -> dict:
    by_entity = {str(v.get("entity")): oid for oid, v in objects.items()}
    external = {
        "LockedBlueprintRef", "AssetProductionScriptViewRef", "DNABindingRef",
        "AssetManifestRef", "SystemOutputNamingRef", "InstructionPackageRef", "ProviderRouteSnapshotRef",
    }
    parent_entity = {
        "AssetExecutionInputManifest": None,
        "AssetCandidateOutput": "AssetExecutionInputManifest",
        "AssetEvaluation": "AssetCandidateOutput",
        "AssetFinding": "AssetEvaluation",
        "AssetCorrectionContext": "AssetFinding",
        "CorrectionScriptCandidate": "AssetCorrectionContext",
        "VersionedLayerDocument": "AssetCandidateOutput",
        "AssetPatch": "VersionedLayerDocument",
        "AssetOutputVersion": "AssetCandidateOutput",
        "AssetScorecard": "AssetEvaluation",
        "AssetHandoffManifest": "AssetOutputVersion",
    }
    relation_by_entity = {
        "AssetExecutionInputManifest": "EXECUTION_INPUT_AGGREGATES_EXACT_UPSTREAM_REFERENCES",
        "AssetCandidateOutput": "CANDIDATE_PRODUCED_FROM_EXECUTION_INPUT",
        "AssetEvaluation": "EVALUATION_BOUND_TO_CANDIDATE_OUTPUT",
        "AssetFinding": "FINDING_DERIVED_FROM_EVALUATION_EVIDENCE",
        "AssetCorrectionContext": "CORRECTION_CONTEXT_BOUND_TO_FINDING_AND_EXACT_OUTPUT",
        "CorrectionScriptCandidate": "CORRECTION_SCRIPT_DERIVED_FROM_CORRECTION_CONTEXT",
        "VersionedLayerDocument": "LAYER_DOCUMENT_DERIVED_FROM_CANDIDATE_OUTPUT",
        "AssetPatch": "PATCH_TARGETS_VERSIONED_LAYER_DOCUMENT",
        "AssetOutputVersion": "IMMUTABLE_OUTPUT_VERSION_DERIVED_FROM_ACCEPTED_CANDIDATE",
        "AssetScorecard": "SCORECARD_DERIVED_FROM_EVALUATION",
        "AssetHandoffManifest": "HANDOFF_BINDS_LOCKED_ASSET_OUTPUT_VERSION",
    }
    rows = []
    for oid, obj in objects.items():
        entity = str(obj.get("entity") or "")
        if entity in external:
            rows.append({
                "object_uid": oid,
                "relation_status": "EXTERNAL_ROOT",
                "parent_object_uid": None,
                "relation": f"EXTERNAL_{entity.upper()}_REFERENCE",
            })
            continue
        if entity not in parent_entity:
            die(f"ENTITY_HIERARCHY_RELATION_UNRESOLVED:{oid}:{entity}")
        pe = parent_entity[entity]
        parent_uid = by_entity.get(pe) if pe else None
        if pe and not parent_uid:
            die(f"ENTITY_HIERARCHY_PARENT_ENTITY_MISSING:{entity}:{pe}")
        rows.append({
            "object_uid": oid,
            "relation_status": "EXACT_CURRENT_STAGE02_DESIGN_RELATION",
            "parent_object_uid": parent_uid,
            "relation": relation_by_entity[entity],
        })
    return {
        "authority_source": "CURRENT_OBJECT_REGISTRY_REQUIRED_CONTENT_AND_APPROVED_STAGE02_ASSET_DESIGN_REMEDIATION",
        "relationships": rows,
    }


def _append_audit_event(port: dict, event_uid: str) -> None:
    current = str(port.get("state_event") or "").strip()
    tokens = [x.strip() for x in current.split("|") if x.strip()]
    if event_uid not in tokens:
        tokens.append(event_uid)
    port["state_event"] = " | ".join(tokens)


def _build_structural_outputs(*, page: str, raw: dict, blueprint: dict, effective_actions: dict, effective_ports: dict,
                              objects: dict, page_root: Path, product_root: Path, chain: dict,
                              operation_contract: dict, hierarchy_contract: dict) -> list[str]:
    reg = raw.get("registries") or {}
    sections = index(reg.get("sections"), "section_uid")
    components = index(reg.get("components"), "component_uid")
    controls = index(reg.get("controls"), "control_uid")
    visuals = index(reg.get("visuals"), "visual_uid")
    gates = index(reg.get("gates"), "gate_uid")
    permissions = index(reg.get("permissions"), "permission_uid")
    controls_by_action = defaultdict(list)
    components_by_section = defaultdict(list)
    controls_by_section = defaultdict(list)
    for comp in components.values():
        if comp.get("section_uid"):
            components_by_section[comp.get("section_uid")].append(comp.get("component_uid"))
    for control in controls.values():
        aid = control.get("action_uid")
        if aid in effective_actions:
            controls_by_action[aid].append(control)
        if control.get("section_uid"):
            controls_by_section[control.get("section_uid")].append(control.get("control_uid"))

    entity_entries = [{
        "object_uid": oid,
        "entity": obj.get("entity"),
        "owner": obj.get("owner"),
        "required_content": obj.get("required_content"),
        "source_kind": "registries.objects_refs",
    } for oid, obj in objects.items()]
    dump(page_root / "BUSINESS_ENTITY_INVENTORY.yaml", {
        "schema_version": 1, "artifact_type": "BUSINESS_ENTITY_INVENTORY", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "CURRENT_OBJECT_REGISTRY_EXACT_PROJECTION_NO_NEW_ENTITY",
        "entity_count": len(entity_entries), "entities": entity_entries,
    })

    vocabulary = operation_contract["operation_vocabulary"]
    profiles = operation_contract["profiles"]
    binding_map = {x["object_uid"]: x["profile"] for x in operation_contract["entity_profile_bindings"]}
    entity_rows = []
    for oid, obj in objects.items():
        profile = binding_map[oid]
        rec = profiles[profile]
        required = set(rec.get("required") or [])
        optional = set(rec.get("optional") or [])
        decisions = {op: ("REQUIRED" if op in required else "OPTIONAL" if op in optional else "NOT_APPLICABLE") for op in vocabulary}
        entity_rows.append({
            "object_uid": oid, "entity": obj.get("entity"), "owner": obj.get("owner"),
            "profile": profile, "operation_applicability": decisions,
        })
    operation_rows = []
    for aid, action in effective_actions.items():
        rb = action.get("runtime_binding") or {}
        operation_rows.append({
            "action_uid": aid, "label": action.get("label"), "effect_type": action.get("effect_type"),
            "gate_uid": action.get("gate_uid"), "permission_uid": action.get("permission_uid"),
            "runtime_binding_kind": rb.get("binding_kind"), "port_refs": port_refs(action),
            "control_uids": [c.get("control_uid") for c in controls_by_action.get(aid, [])],
        })
    dump(page_root / "BUSINESS_ENTITY_OPERATION_MATRIX.yaml", {
        "schema_version": 2, "artifact_type": "BUSINESS_ENTITY_OPERATION_MATRIX", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "CURRENT_ENTITY_PROFILE_APPLICABILITY_PLUS_EXACT_ACTION_BINDING",
        "semantic_entity_join_used": True, "entity_count": len(objects), "entity_rows": entity_rows,
        "operation_count": len(operation_rows), "operations": operation_rows,
    })

    rels = hierarchy_contract["relationships"]
    dump(page_root / "ENTITY_HIERARCHY_MATRIX.yaml", {
        "schema_version": 2, "artifact_type": "ENTITY_HIERARCHY_MATRIX", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "APPROVED_EXPLICIT_CURRENT_OBJECT_RELATIONSHIPS",
        "explicit_relationship_authority_used": True, "entity_count": len(objects), "rows": copy.deepcopy(rels),
    })

    workbenches = []
    for sid, section in sections.items():
        workbenches.append({
            "workbench_uid": f"{page}-WB-{sid}", "workbench_class": "SAME_SURFACE_CLUSTER",
            "classification_basis": "EXACT_SECTION_UID_MEMBERSHIP", "section_uid": sid,
            "section_name": section.get("name"), "section_responsibility": section.get("responsibility"),
            "visual_uid": section.get("visual_uid"), "component_uids": sorted(components_by_section.get(sid, [])),
            "control_uids": sorted(controls_by_section.get(sid, [])),
        })
    dump(page_root / "FUNCTIONAL_WORKBENCH_CONTRACT.yaml", {
        "schema_version": 1, "artifact_type": "FUNCTIONAL_WORKBENCH_CONTRACT", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "EXACT_SECTION_COMPONENT_CONTROL_MEMBERSHIP", "workbench_count": len(workbenches),
        "workbenches": workbenches, "atomic_workbenches": [],
    })

    nodes = {
        "sections": sorted(sections), "components": sorted(components), "controls": sorted(controls),
        "actions": sorted(effective_actions), "gates": sorted(gates), "permissions": sorted(permissions), "visuals": sorted(visuals),
    }
    edges = []
    for cid, comp in components.items():
        if comp.get("section_uid"):
            edges.append({"from": comp.get("section_uid"), "to": cid, "relation": "SECTION_HAS_COMPONENT"})
    for cid, control in controls.items():
        if control.get("component_uid"):
            edges.append({"from": control.get("component_uid"), "to": cid, "relation": "COMPONENT_HAS_CONTROL"})
        if control.get("action_uid") in effective_actions:
            edges.append({"from": cid, "to": control.get("action_uid"), "relation": "CONTROL_TRIGGERS_ACTION"})
        if control.get("gate_uid"):
            edges.append({"from": cid, "to": control.get("gate_uid"), "relation": "CONTROL_REQUIRES_GATE"})
        if control.get("permission_uid"):
            edges.append({"from": cid, "to": control.get("permission_uid"), "relation": "CONTROL_REQUIRES_PERMISSION"})
        if control.get("visual_uid"):
            edges.append({"from": cid, "to": control.get("visual_uid"), "relation": "CONTROL_RENDERED_IN_VISUAL"})
    dump(page_root / "INTERACTION_TOPOLOGY_SPEC.yaml", {
        "schema_version": 1, "artifact_type": "INTERACTION_TOPOLOGY_MATRIX", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "EXACT_REGISTRY_UID_EDGES_ONLY", "semantic_edge_inference_used": False,
        "nodes": nodes, "edge_count": len(edges), "edges": edges,
    })

    visual_rows = []
    for aid, action in effective_actions.items():
        bindings = [{
            "control_uid": c.get("control_uid"), "section_uid": c.get("section_uid"),
            "component_uid": c.get("component_uid"), "visual_uid": c.get("visual_uid"),
        } for c in controls_by_action.get(aid, [])]
        visual_rows.append({
            "action_uid": aid, "effect_type": action.get("effect_type"), "bindings": bindings,
            "visual_binding_status": "EXACT_CONTROL_VISUAL_BINDINGS" if bindings else "NO_REGISTERED_CONTROL_VISUAL_BINDING",
        })
    dump(page_root / "FUNCTION_VISUAL_IMPACT_MATRIX.yaml", {
        "schema_version": 1, "artifact_type": "FUNCTION_VISUAL_IMPACT_MATRIX", "stage_uid": "STAGE-02", "page_uid": page,
        "derivation": "EXACT_CONTROL_TO_ACTION_AND_VISUAL_BINDING", "action_count": len(visual_rows), "rows": visual_rows,
    })

    shared_rows = []
    for aid, action in effective_actions.items():
        rb = action.get("runtime_binding") or {}
        if rb.get("binding_kind") == "SHARED_OPERATION_REFERENCE":
            shared_rows.append({
                "page_uid": page, "action_uid": aid, "shared_authority_id": rb.get("shared_authority_id"),
                "shared_operation_id": rb.get("shared_operation_id"), "resolution_status": "CURRENT_SHARED_OPERATION_REFERENCE",
            })
    dump(product_root / "SHARED_OWNER_PORT_MAP.yaml", {
        "schema_version": 1, "artifact_type": "SHARED_OWNER_PORT_MAP", "stage_uid": "STAGE-02",
        "derivation": "CURRENT_EFFECTIVE_ACTION_SHARED_OPERATION_REFERENCE_PROJECTION",
        "shared_owner_binding_count": len(shared_rows), "bindings": shared_rows,
    })
    provider_rows = [{
        "page_uid": page, "port_uid": pid, "boundary": port.get("boundary"),
        "operation": port.get("operation") or port.get("registered_operation"),
        "method_path": port.get("method_path") or port.get("method_effective_path"),
        "permission": port.get("permission") or port.get("registered_permission"),
        "state_event": port.get("state_event"), "exposure": port.get("exposure"),
    } for pid, port in effective_ports.items()]
    dump(product_root / "ASYNC_PROVIDER_CONTRACT.yaml", {
        "schema_version": 1, "artifact_type": "ASYNC_PROVIDER_CONTRACT", "stage_uid": "STAGE-02",
        "derivation": "CURRENT_EFFECTIVE_INTEGRATION_PORT_PROJECTION", "provider_route_inference_used": False,
        "port_count": len(provider_rows), "ports": provider_rows,
    })
    refs = []
    for ref in blueprint.get("unresolved_external_authority_refs") or []:
        refs.append({"gap_uid": ref.get("gap_uid"), "authority_ref": ref.get("authority_ref"), "resolved": False})
    dump(product_root / "DEPENDENCY_MAP.yaml", {
        "schema_version": 1, "artifact_type": "DEPENDENCY_MAP", "stage_uid": "STAGE-02",
        "derivation": "CURRENT_STAGE1_BLUEPRINT_AND_AUTHORITY_REFERENCE_PROJECTION",
        "pages": [{"page_uid": page, "blueprint_uid": blueprint.get("blueprint_uid"),
                   "blueprint_hash": blueprint.get("blueprint_hash"),
                   "unresolved_external_authority_refs": refs}],
    })
    included = [
        "BUSINESS_ENTITY_INVENTORY.yaml", "BUSINESS_ENTITY_OPERATION_MATRIX.yaml", "ENTITY_HIERARCHY_MATRIX.yaml",
        "FUNCTIONAL_WORKBENCH_CONTRACT.yaml", "INTERACTION_TOPOLOGY_SPEC.yaml", "FUNCTION_VISUAL_IMPACT_MATRIX.yaml",
        "FUNCTIONAL_CHAIN_SPEC.yaml",
    ]
    dump(page_root / "PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml", {
        "schema_version": 1, "artifact_type": "PAGE_CONSTRUCTION_SPEC_PACKAGE", "stage_uid": "STAGE-02", "page_uid": page,
        "source_blueprint_uid": blueprint.get("blueprint_uid"), "included_artifacts": included,
        "candidate_bytes_became_authority_directly": False, "stage_exit_claimed": False,
    })
    return included + ["PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml", "../DEPENDENCY_MAP.yaml", "../ASYNC_PROVIDER_CONTRACT.yaml", "../SHARED_OWNER_PORT_MAP.yaml"]


def materialize_current_approved_design_contract():
    state, scope, work, page, run_root, product_root, page_root, paths = _current_design_context()
    problem = load(paths["problem"])
    candidate = load(paths["candidate"])
    semantic = load(paths["semantic_review"])
    chain = load(paths["chain"])
    raw = load(paths["raw"])
    blueprint = load(paths["blueprint"])

    if candidate.get("page_uid") != page or candidate.get("status") != "REVIEW_ONLY_NON_AUTHORITY_NON_MATERIALIZABLE":
        die("CURRENT_DESIGN_CANDIDATE_IDENTITY_OR_STATUS_DRIFT")
    if semantic.get("page_uid") != page or semantic.get("status") != "PASS_AS_REVIEW_ONLY_PACKAGE_NOT_APPROVED_FOR_MATERIALIZATION":
        die("CURRENT_DESIGN_SEMANTIC_REVIEW_STATUS_DRIFT")
    blockers = semantic.get("blocking_authority_selection") or []
    rows = list(problem.get("problems") or [])
    if int(problem.get("open_problem_count") or 0) != len(rows):
        die("CURRENT_PROBLEM_REGISTER_OPEN_DENOMINATOR_DRIFT")
    approved_rows = list(rows)
    approved_uids = {str(x.get("problem_uid") or "") for x in approved_rows}
    remaining_uids = set()
    boundaries = candidate.get("design_boundaries") or {}
    if int(candidate.get("covered_review_only_problem_count") or 0) != len(rows):
        die("REVIEW_ONLY_CANDIDATE_CURRENT_REGISTER_DENOMINATOR_DRIFT")

    current_uid = str(state.get("specification_uid") or "")
    frozen_product_uid = str((state.get("stage02_active_attempt") or {}).get("frozen_governance_uid") or "")
    if not frozen_product_uid:
        die("FROZEN_PRODUCT_GOVERNANCE_UID_MISSING")
    if candidate.get("current_governance_uid") != frozen_product_uid or semantic.get("current_governance_uid") != frozen_product_uid:
        die("FROZEN_PRODUCT_GOVERNANCE_UID_DRIFT_IN_DESIGN_PACKAGE")
    prior_credit = int(work.get("product_blocker_credit") or 0)
    exact = work.get("exact_closure_materialization") or {}
    if exact.get("revalidation_status") != "FRESH_REVALIDATED" or int(exact.get("product_blocker_credit_after_fresh_revalidation") or 0) != prior_credit:
        die("PRIOR_EXACT_CLOSURE_CREDIT_NOT_FRESH_REVALIDATED")

    projection = chain.setdefault("source_projection", {})
    actions_list = projection.get("actions")
    ports_list = projection.get("integration_ports")
    transitions_list = projection.get("stage_transitions")
    if not isinstance(actions_list, list) or not isinstance(ports_list, list) or not isinstance(transitions_list, list):
        die("CANONICAL_SUCCESSOR_REQUIRED_PROJECTION_LIST_MISSING")
    actions = index(actions_list, "action_uid")
    ports = index(ports_list, "port_uid")
    transitions = index(transitions_list, "transition_uid")
    raw_reg = raw.get("registries") or {}
    errors = index(raw_reg.get("errors"), "error_uid")
    objects = index(raw_reg.get("objects_refs"), "object_uid")

    failure = boundaries.get("failure_error_binding") or {}
    failure_rows = failure.get("proposal") or []
    if int(failure.get("problem_count") or 0) != len(failure_rows):
        die("FAILURE_ERROR_BINDING_PROPOSAL_DENOMINATOR_DRIFT")
    for proposal in failure_rows:
        aid = str(proposal.get("action_uid") or "")
        eid = str(proposal.get("error_uid") or "")
        action = actions.get(aid)
        error = errors.get(eid)
        if not action or not error or not error.get("recovery"):
            die(f"FAILURE_ERROR_BINDING_TARGET_INVALID:{aid}:{eid}")
        prior = action.get("error_uid")
        if prior not in (None, "", eid):
            die(f"FAILURE_ERROR_BINDING_CONFLICT:{aid}:{prior}:{eid}")
        action["error_uid"] = eid

    payload = boundaries.get("payload_input_contract") or {}
    payload_rows = payload.get("proposal") or []
    if int(payload.get("problem_count") or 0) != len(payload_rows):
        die("PAYLOAD_INPUT_PROPOSAL_DENOMINATOR_DRIFT")
    for proposal in payload_rows:
        aid = str(proposal.get("action_uid") or "")
        action = actions.get(aid)
        required_inputs = list(proposal.get("required_inputs") or [])
        policy = str(proposal.get("payload_policy") or "")
        if not action or not required_inputs or not policy:
            die(f"PAYLOAD_INPUT_PROPOSAL_INVALID:{aid}")
        rb = action.setdefault("runtime_binding", {})
        desired = {"required_inputs": required_inputs, "payload_policy": policy}
        prior = rb.get("input_contract")
        if prior not in (None, {}, desired):
            die(f"PAYLOAD_INPUT_CONTRACT_CONFLICT:{aid}")
        rb["input_contract"] = desired

    audit = boundaries.get("audit_event_binding") or {}
    audit_rows = audit.get("proposal") or []
    if int(audit.get("problem_count") or 0) != len(audit_rows):
        die("AUDIT_EVENT_PROPOSAL_DENOMINATOR_DRIFT")
    for proposal in audit_rows:
        _require_record_schema(proposal, {"action_uid": str, "audit_event_uid": str}, "STAGE02_AUDIT_EVENT_BINDING")
        aid = str(proposal.get("action_uid") or "")
        event_uid = str(proposal.get("audit_event_uid") or "")
        action = actions.get(aid)
        if not action or not event_uid:
            die(f"AUDIT_EVENT_PROPOSAL_INVALID:{aid}:{event_uid}")
        refs = [x["port_uid"] for x in port_refs(action) if x.get("port_uid") in ports]
        refs = sorted(set(refs))
        if len(refs) != 1:
            die(f"AUDIT_EVENT_PORT_RESOLUTION_NOT_EXACT:{aid}:{refs!r}")
        _append_audit_event(ports[refs[0]], event_uid)

    trans_boundary = boundaries.get("transition_required_fields") or {}
    trans_rows = trans_boundary.get("proposal") or []
    if int(trans_boundary.get("problem_count") or 0) != len(trans_rows) * 4:
        die("TRANSITION_REQUIRED_FIELD_DENOMINATOR_DRIFT")
    for proposal in trans_rows:
        tid = str(proposal.get("transition_uid") or "")
        transition = transitions.get(tid)
        if not transition:
            die(f"TRANSITION_PROPOSAL_TARGET_MISSING:{tid}")
        from_stage = transition.get("from_stage")
        if not from_stage:
            die(f"TRANSITION_FROM_STAGE_MISSING:{tid}")
        desired = {
            "mutation_owner": proposal.get("mutation_owner"),
            "failure_error_uid": proposal.get("failure_error_uid"),
            "failure_state": from_stage,
            "recovery": {
                "retain_stage": from_stage,
                "action": proposal.get("recovery"),
                "error_uid": proposal.get("failure_error_uid"),
            },
            "audit_event_uid": proposal.get("audit_event_uid"),
        }
        if any(v in (None, "", {}) for v in desired.values()):
            die(f"TRANSITION_PROPOSAL_INCOMPLETE:{tid}:{desired!r}")
        for key, value in desired.items():
            prior = transition.get(key)
            if prior not in (None, "", {}, value):
                die(f"TRANSITION_FIELD_CONFLICT:{tid}:{key}:{prior!r}:{value!r}")
            transition[key] = value

    post = boundaries.get("post_action_validation_remaining") or {}
    post_rows = post.get("proposal") or []
    if int(post.get("problem_count") or 0) != len(post_rows):
        die("POST_ACTION_VALIDATION_PROPOSAL_DENOMINATOR_DRIFT")
    for proposal in post_rows:
        aid = str(proposal.get("action_uid") or "")
        action = actions.get(aid)
        source_port = str(proposal.get("source_port") or "")
        if not action or source_port not in ports:
            die(f"POST_ACTION_VALIDATION_TARGET_INVALID:{aid}:{source_port}")
        rb = action.setdefault("runtime_binding", {})
        desired = {
            "contract_type": proposal.get("validation_contract_type"),
            "source_port_uid": source_port,
            "expected_signal": proposal.get("signal"),
        }
        if proposal.get("mode"):
            desired["mode"] = proposal.get("mode")
        prior = rb.get("validation")
        if prior not in (None, {}, desired):
            die(f"POST_ACTION_VALIDATION_CONFLICT:{aid}")
        rb["validation"] = desired

    trigger_rows = [x for x in rows if x.get("category") in {"SYSTEM_TRIGGER_BINDING_MISSING","ACTION_WITHOUT_CONTROL_OR_TRIGGER"}]
    system_trigger_materializations=[]
    for row in trigger_rows:
        aid=str(row.get("target_uid") or row.get("uid") or "")
        action=actions.get(aid)
        contract=_deterministic_system_trigger(aid, action or {}, raw_reg) if action else None
        if contract is None:
            remaining_uids.add(str(row.get("problem_uid") or ""))
            continue
        if action.get("system_trigger") not in (None, {}, contract):
            die(f"SYSTEM_TRIGGER_CONFLICT:{aid}")
        action["system_trigger"]=contract
        action["trigger_authority"]={"source":"CURRENT_AUTHORITY_DETERMINISTIC_RESOLUTION","new_visual_control":False}
        system_trigger_materializations.append({"action_uid":aid,"system_trigger":contract})
    approved_uids -= remaining_uids

    planning = boundaries.get("stage02_planning_completeness") or {}
    plan = planning.get("proposal") or {}
    required_contracts = list(plan.get("required_contracts") or [])
    required_invariants = list(plan.get("required_invariants") or [])
    if int(planning.get("problem_count") or 0) != 1 or plan.get("status") != "REQUIRED_FOR_STAGE02_CLOSURE":
        die("STAGE02_PLANNING_CANDIDATE_INVALID")
    if set(required_contracts) != {"change_impact_contract", "entity_operation_applicability_contract", "entity_hierarchy_contract"}:
        die(f"STAGE02_PLANNING_REQUIRED_CONTRACT_SET_DRIFT:{required_contracts!r}")

    operation_contract = _entity_operation_contract(objects)
    hierarchy_contract = _entity_hierarchy_contract(objects)
    change_impact = {
        "authority_source": "CURRENT_ASSET_STAGE_FLOW_AND_APPROVED_STAGE02_DESIGN_REMEDIATION",
        "trigger": "UPSTREAM_LOCKED_BLUEPRINT_SCRIPT_DNA_MANIFEST_OR_ROUTE_CHANGED",
        "affected_downstream_states": ["NEEDS_REVIEW", "NEEDS_REVALIDATION"],
        "silent_downstream_rewrite": "FORBIDDEN",
        "exact_base_version_required_for_revision": True,
        "prior_locked_asset_version_immutable": True,
        "dependency_order": [
            "AssetExecutionInputManifest", "AssetCandidateOutput", "AssetEvaluation", "AssetFinding",
            "AssetCorrectionContext", "CorrectionScriptCandidate", "VersionedLayerDocument", "AssetPatch",
            "AssetOutputVersion", "AssetScorecard", "AssetHandoffManifest",
        ],
    }
    baseline_sha256 = sha256(paths["raw"])
    completeness = {
        "authority_source": "EXPLICIT_USER_DIRECTIVE_PLUS_CURRENT_ASSET_STAGE02_DESIGN_CANDIDATE",
        "planning_baseline_file": str(paths["raw"].relative_to(ROOT)),
        "planning_baseline_sha256": baseline_sha256,
        "planning_baseline_git_blob_sha": (plan.get("planning_baseline_identity") or {}).get("git_blob_sha"),
        "status": "REQUIRED_FOR_STAGE02_CLOSURE",
        "required_contracts": required_contracts,
        "required_invariants": required_invariants,
        "excluded_non_applicable_contract_families": list(planning.get("excluded_non_applicable_contract_families") or []),
        "product_specific_adapter": True,
        "common_policy_override": False,
    }
    chain["change_impact_contract"] = change_impact
    chain["entity_operation_applicability_contract"] = operation_contract
    chain["entity_hierarchy_contract"] = hierarchy_contract
    chain["stage02_completeness_contract"] = completeness
    chain["planning_baseline_sha256"] = baseline_sha256
    projection["actions"] = list(actions.values())
    projection["integration_ports"] = list(ports.values())
    projection["stage_transitions"] = list(transitions.values())

    approval_ref = str(paths["approval"].relative_to(ROOT))
    receipt_ref = str(paths["receipt"].relative_to(ROOT))
    remediation = chain.setdefault("design_contract_remediation", {})
    remediation.update({
        "canonical_owner_materialization": True,
        "materialization_scope": "APPROVED_COHERENT_CANDIDATE_PLUS_DETERMINISTIC_SYSTEM_TRIGGER_RESOLUTION",
        "approved_design_contract_problem_count": len(approved_uids),
        "remaining_authority_gap_problem_count": len(remaining_uids),
        "candidate_bytes_became_authority_directly": False,
        "raw_source_mutated": False,
        "approval_kind": "EXPLICIT_USER_APPROVAL_COHERENT_CANDIDATE_PLUS_GOVERNED_AUTO_REMEDIATION",
        "approval_evidence_ref": approval_ref,
        "contract_projection_allowed": True,
        "approved_contract_projection_keys": [
            "change_impact_contract", "entity_operation_applicability_contract",
            "entity_hierarchy_contract", "stage02_completeness_contract",
        ],
    })
    dump(paths["chain"], chain)

    structural = _build_structural_outputs(
        page=page, raw=raw, blueprint=blueprint, effective_actions=actions, effective_ports=ports,
        objects=objects, page_root=page_root, product_root=product_root, chain=chain,
        operation_contract=operation_contract, hierarchy_contract=hierarchy_contract,
    )

    authorization_uid = str(state.get("current_primary_task_authorization_uid") or "")
    if not authorization_uid:
        die("EXPLICIT_USER_AUTHORIZATION_UID_MISSING")
    approval = {
        "schema_version": 1,
        "artifact_type": "PRODUCT_DESIGN_CONTRACT_PACKAGE_REVIEW_EVIDENCE",
        "normative_authority": False,
        "current_governance_uid": current_uid,
        "product_candidate_frozen_governance_uid": frozen_product_uid,
        "work_unit_uid": str(work.get("work_unit_uid") or ""),
        "page_uid": page,
        "decision": "APPROVE_COHERENT_CANDIDATE_WITH_GOVERNED_AUTO_REMEDIATION",
        "approved_by": "USER",
        "explicit_user_decision_observed": True,
        "self_reported_approval": False,
        "authorization_uid": authorization_uid,
        "authorization_directive": "把這部分列入待修正bug，先執行繼續跑完素材頁面stage-02，確認是否還有這些問題。",
        "system_trigger_materializations": system_trigger_materializations,
        "approved_problem_count": len(approved_uids),
        "approved_problem_uids": sorted(approved_uids),
        "excluded_authority_selection_problem_uids": sorted(remaining_uids),
        "excluded_authority_selection_target_uids": sorted({str(x.get("target_uid") or x.get("uid") or "") for x in rows if str(x.get("problem_uid") or "") in remaining_uids}),
        "candidate_ref": str(paths["candidate"].relative_to(ROOT)),
        "candidate_sha256": sha256(paths["candidate"]),
        "semantic_review_ref": str(paths["semantic_review"].relative_to(ROOT)),
        "semantic_review_sha256": sha256(paths["semantic_review"]),
        "problem_register_ref": str(paths["problem"].relative_to(ROOT)),
        "problem_register_sha256": sha256(paths["problem"]),
        "candidate_bytes_became_authority_directly": False,
        "current_specification_mutated": False,
        "raw_source_mutated": False,
    }
    dump(paths["approval"], approval)
    receipt = {
        "schema_version": 1,
        "artifact_type": "APPROVED_DESIGN_CONTRACT_MATERIALIZATION_RECEIPT",
        "normative_authority": False,
        "current_governance_uid": current_uid,
        "product_candidate_frozen_governance_uid": frozen_product_uid,
        "work_unit_uid": str(work.get("work_unit_uid") or ""),
        "page_uid": page,
        "canonical_successor_ref": str(paths["chain"].relative_to(ROOT)),
        "approval_evidence_ref": approval_ref,
        "approved_problem_count": len(approved_uids),
        "approved_problem_uids": sorted(approved_uids),
        "remaining_authority_gap_problem_uids": sorted(remaining_uids),
        "remaining_authority_gap_target_uids": sorted({str(x.get("target_uid") or x.get("uid") or "") for x in rows if str(x.get("problem_uid") or "") in remaining_uids}),
        "prior_product_credit": prior_credit,
        "product_blocker_credit_before_fresh_revalidation": prior_credit,
        "generated_structural_outputs": structural,
        "status": "MATERIALIZED_PENDING_FRESH_REVALIDATION",
        "fresh_revalidation_required": True,
        "candidate_bytes_became_authority_directly": False,
        "raw_source_mutated": False,
        "current_specification_mutated": False,
    }
    dump(paths["receipt"], receipt)

    next_action = f"REVALIDATE_{page.replace('-','')}_STAGE02_AFTER_APPROVED_DESIGN_CONTRACT_MATERIALIZATION"
    work["current_status"] = "APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED"
    work["product_blocker_credit"] = prior_credit
    work["design_contract_materialization"] = {
        "canonical_successor_ref": str(paths["chain"].relative_to(ROOT)),
        "approval_evidence_ref": approval_ref,
        "receipt_ref": receipt_ref,
        "approved_problem_count": len(approved_uids),
        "approved_problem_uids": sorted(approved_uids),
        "remaining_authority_gap_problem_uids": sorted(remaining_uids),
        "prior_product_credit": prior_credit,
        "product_blocker_credit_before_fresh_revalidation": prior_credit,
        "revalidation_status": "PENDING_FRESH_REVALIDATION",
    }
    state["active_work_unit"] = work
    state["status"] = f"ACTIVE_{page.replace('-','')}_STAGE02_APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED"
    state["next_action"] = next_action
    state["current_primary_task_product_stage_credit"] = prior_credit
    attempt = state.setdefault("stage02_active_attempt", {})
    attempt["next_action"] = next_action
    attempt["fresh_revalidation_required"] = True
    attempt["product_blocker_credit"] = prior_credit
    material = state.setdefault("stage02_material_remediation", {})
    material.update({
        "material_remediation_started": True,
        "source_problem_denominator": int(problem.get("open_problem_count") or 0),
        "source_closure_blocker_denominator": int(work.get("source_closure_blocker_denominator") or 0),
        "exact_materialized_closure_count": int((work.get("exact_closure_materialization") or {}).get("materialized_closure_count") or 0),
        "approved_design_contract_problem_count_pending_revalidation": len(approved_uids),
        "remaining_authority_gap_problem_count": len(remaining_uids),
        "product_blocker_credit": prior_credit,
        "status": "APPROVED_DESIGN_CONTRACT_MATERIALIZED_PENDING_FRESH_REVALIDATION",
    })
    state["resume_control"] = {
        "current_resume_point": f"{page.replace('-','')}_STAGE2_APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED",
        "current_work_unit_uid": work.get("work_unit_uid"),
        "current_owner": str(paths["chain"].relative_to(ROOT)),
        "historical_stage2_results_are_current_state": False,
        "stage2_execution_requires_fresh_entry_resolution": False,
        "exact_next_action": next_action,
    }
    dump(STATE, state)

    findings_path = ROOT / "governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml"
    candidate_state_path = ROOT / "governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml"
    findings = load(findings_path)
    findings["next_action"] = next_action
    findings["product_blocker_credit"] = prior_credit
    findings["approved_design_contract_problem_count_pending_revalidation"] = len(approved_uids)
    dump(findings_path, findings)
    candidate_state = load(candidate_state_path)
    cur = candidate_state.setdefault("current_stage2_execution", {})
    cur["next_action"] = next_action
    cur["current_work_unit_status"] = "APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED"
    cur["product_blocker_reduction_credit"] = prior_credit
    cur["approved_design_contract_problem_count_pending_revalidation"] = len(approved_uids)
    dump(candidate_state_path, candidate_state)

    scope["fresh_revalidation_required"] = True
    scope["stage_exit_credit_allowed"] = False
    tmp = copy.deepcopy(scope)
    tmp.pop("content_hash", None)
    scope["content_hash"] = hashlib.sha256(
        json.dumps(tmp, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    dump(paths["scope"], scope)

    print(f"APPROVED_DESIGN_PAGE={page}")
    print(f"APPROVED_DESIGN_PROBLEM_COUNT={len(approved_uids)}")
    print(f"REMAINING_AUTHORITY_GAP_COUNT={len(remaining_uids)}")
    print(f"PRIOR_PRODUCT_CREDIT={prior_credit}")
    print(f"CANONICAL_SUCCESSOR={paths['chain'].relative_to(ROOT)}")
    print("PASS: approved non-ambiguous design-contract scope materialized; remaining authority selection preserved unresolved")


if __name__ == "__main__":
    if "--self-test-shared-contract-hardening" in sys.argv:
        _self_test_shared_contract_hardening()
        raise SystemExit(0)
    if "--approved-design-current" in sys.argv:
        materialize_current_approved_design_contract()
        raise SystemExit(0)
    die("CURRENT_DYNAMIC_MATERIALIZATION_MODE_REQUIRED")
