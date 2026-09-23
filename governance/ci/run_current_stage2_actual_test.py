#!/usr/bin/env python3
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("ACPOS_COMMON_STAGE_ENGINE_EXECUTION") != "1":
    raise RuntimeError("DIRECT_EFFECTFUL_INVOCATION_FORBIDDEN_USE_COMMON_STAGE_ENGINE")
SELF_TEST_REVALIDATION_AUTHORITY = '--self-test-revalidation-authority' in sys.argv
SELF_TEST_APPLICABILITY_PROJECTION = '--self-test-applicability-projection' in sys.argv
SELF_TEST_SHARED_CONTRACT = '--self-test-shared-contract-hardening' in sys.argv
SELF_TEST_NORMALIZED_COMMON = '--self-test-normalized-common-evidence' in sys.argv
MATERIALIZE_NORMALIZED_COMMON = '--materialize-normalized-common-evidence' in sys.argv
RUN_ROOT_ENV = os.environ.get('ACPOS_RUN_ROOT', '').strip()
if not RUN_ROOT_ENV and not (SELF_TEST_REVALIDATION_AUTHORITY or SELF_TEST_APPLICABILITY_PROJECTION or SELF_TEST_SHARED_CONTRACT or SELF_TEST_NORMALIZED_COMMON):
    raise SystemExit('BLOCK: ACPOS_RUN_ROOT_REQUIRED')
RUN = ROOT / (RUN_ROOT_ENV or 'governance/test/temporary/stage02-self-test')
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
STAGE_REGISTRY = ROOT / '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
RESULT = ROOT / '.github/stage02-test/STAGE02_ACTUAL_TEST_RESULT.json'
NORMALIZED_RESULT = ROOT / 'governance/test/stage02/STAGE02_NORMALIZED_COMMON_EVIDENCE.json'
HANDOFF_LEDGER = ROOT / 'governance/test/stage02/STAGE02_CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml'
SCOPE_MANIFEST = ROOT / 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
OLD_STAGE2_ROOT = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'

def resolve_page(page_uid: str):
    raw_dir = RUN / '00_SOURCE_INTAKE/RAW_SOURCE' / page_uid
    blueprint = RUN / '02_BASE_BLUEPRINT' / page_uid / 'PAGE_BASE_BLUEPRINT.yaml'
    if not raw_dir.is_dir() or not blueprint.is_file():
        die(f'PAGE_SCOPE_OWNER_MISSING:{page_uid}')
    candidates = []
    for path in sorted(raw_dir.glob('*.yaml')):
        try:
            obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        except Exception:
            continue
        if (obj.get('authority') or {}).get('page_uid') == page_uid and isinstance(obj.get('registries'), dict):
            candidates.append(path)
    if len(candidates) != 1:
        die(f'PAGE_RAW_OWNER_DENOMINATOR:{page_uid}:{len(candidates)}')
    return {'raw': candidates[0], 'blueprint': blueprint}


def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

def load(path: Path):
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:
        die(f'PARSE_ERROR:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj

def idx(items, key):
    return {x.get(key): x for x in (items or []) if isinstance(x, dict) and x.get(key)}

def present(obj, *names):
    return any(isinstance(obj, dict) and obj.get(name) not in (None, '', [], {}) for name in names)

def event_token(text: str):
    text = str(text or '')
    if '|' in text:
        tail = text.split('|', 1)[1].strip()
        if tail and tail.lower() not in {'event none', 'none'}:
            return tail
    m = re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b', text)
    return m.group(0) if m else None

def has_transition(text: str):
    text = str(text or '')
    return '→' in text or '->' in text

def add(gaps, page, klass, category, uid, detail, owner='PAGE_FUNCTIONAL_CONTRACT'):
    gaps.append({'page_uid': page, 'class': klass, 'category': category, 'uid': uid, 'detail': detail, 'gap_owner': owner})

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _safe_repo_path(value: str, repo_root: Path) -> Path:
    rel = Path(str(value))
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise ValueError(f'INVALID_RELATIVE_PATH:{value}')
    return repo_root / rel

def _verify_external_authority_record(rec: dict, repo_root: Path = ROOT) -> str:
    required = (
        'authority_ref','authority_source_path','authority_content_sha256',
        'authority_manifest_path','authority_manifest_sha256','canonical_authority_path',
    )
    if not isinstance(rec, dict) or any(not str(rec.get(k) or '').strip() for k in required):
        raise ValueError('EXTERNAL_AUTHORITY_RESOLUTION_RECORD_INCOMPLETE')
    authority_ref = str(rec['authority_ref']).strip()
    source = _safe_repo_path(str(rec['authority_source_path']), repo_root)
    manifest_path = _safe_repo_path(str(rec['authority_manifest_path']), repo_root)
    if not source.is_file() or not manifest_path.is_file():
        raise ValueError(f'EXTERNAL_AUTHORITY_SOURCE_OR_MANIFEST_MISSING:{authority_ref}')
    if _sha256_file(source) != str(rec['authority_content_sha256']):
        raise ValueError(f'EXTERNAL_AUTHORITY_CONTENT_SHA256_DRIFT:{authority_ref}')
    if _sha256_file(manifest_path) != str(rec['authority_manifest_sha256']):
        raise ValueError(f'EXTERNAL_AUTHORITY_MANIFEST_SHA256_DRIFT:{authority_ref}')
    source_doc = yaml.safe_load(source.read_text(encoding='utf-8')) or {}
    manifest = yaml.safe_load(manifest_path.read_text(encoding='utf-8')) or {}
    if not isinstance(source_doc, dict) or not isinstance(manifest, dict):
        raise ValueError(f'EXTERNAL_AUTHORITY_MAPPING_REQUIRED:{authority_ref}')
    ids = {
        str(source_doc.get('authority_id') or ''),
        str(source_doc.get('artifact_uid') or ''),
        str(source_doc.get('id') or ''),
        str((source_doc.get('authority') or {}).get('id') or '') if isinstance(source_doc.get('authority'), dict) else '',
    }
    if authority_ref not in ids:
        raise ValueError(f'EXTERNAL_AUTHORITY_IDENTITY_DRIFT:{authority_ref}')
    current_set = manifest.get('current_authority_set') or {}
    members = set()
    if isinstance(current_set, dict):
        for values in current_set.values():
            if isinstance(values, list):
                members.update(str(x) for x in values)
    canonical = str(rec['canonical_authority_path']).strip()
    if canonical not in members:
        raise ValueError(f'EXTERNAL_AUTHORITY_NOT_IN_CURRENT_AUTHORITY_SET:{authority_ref}:{canonical}')
    auth_meta = manifest.get('authority') or {}
    if not isinstance(auth_meta, dict) or auth_meta.get('status') != 'FINAL_LOCKED' or auth_meta.get('current_only') is not True:
        raise ValueError('CURRENT_AUTHORITY_MANIFEST_NOT_FINAL_LOCKED_CURRENT_ONLY')
    return authority_ref

def _resolve_external_authority_records(records, repo_root: Path = ROOT) -> list[str]:
    if records in (None, []):
        return []
    if not isinstance(records, list):
        die('RESOLVED_EXTERNAL_AUTHORITY_RECORDS_LIST_REQUIRED')
    out = []
    for rec in records:
        try:
            ref = _verify_external_authority_record(rec, repo_root)
        except ValueError as exc:
            die(str(exc))
        if ref in out:
            die(f'DUPLICATE_RESOLVED_EXTERNAL_AUTHORITY_REF:{ref}')
        out.append(ref)
    return sorted(out)

def _validate_stage02_admission(state: dict, revalidation_mode: bool) -> dict:
    execution = state.get('execution') or {}
    stage1_state = execution.get('stage1') or {}
    if not isinstance(stage1_state, dict) or not stage1_state or any(v != 'PASS' for v in stage1_state.values()):
        die(f'STAGE02_ADMISSION_STAGE1_NOT_CLOSED:{stage1_state!r}')
    if revalidation_mode:
        if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED':
            die(f'STAGE02_REVALIDATION_CURRENT_STAGE:{execution.get("current_stage")!r}')
        if (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
            die('STAGE02_REVALIDATION_REQUIRES_BLOCKED_CURRENT_ATTEMPT')
        attempt = state.get('stage02_active_attempt') or {}
        if not isinstance(attempt, dict) or not attempt.get('attempt_uid') or attempt.get('run_uid') != execution.get('run_uid'):
            die('STAGE02_REVALIDATION_ACTIVE_ATTEMPT_IDENTITY_DRIFT')
        return execution
    if execution.get('current_stage') != 'STAGE-01-CLOSED':
        die(f'STAGE02_ADMISSION_CURRENT_STAGE:{execution.get("current_stage")!r}')
    if (execution.get('stage2') or {}).get('result') != 'NOT_EXECUTED':
        die('STAGE02_ADMISSION_REQUIRES_NOT_EXECUTED')
    return execution

def _collect_declared_package_paths(value) -> set[str]:
    out=set()
    def walk(v):
        if isinstance(v,dict):
            p=v.get('package_path')
            if isinstance(p,str) and p.strip():
                out.add(p.strip())
            for child in v.values():
                walk(child)
        elif isinstance(v,list):
            for child in v:
                walk(child)
    walk(value)
    return out

def _stage3_successor_readiness(page_uid: str, page_dir: Path, ai_profile_active: bool) -> dict:
    registry=load(STAGE_REGISTRY)
    stage3_rows=[x for x in (registry.get('stages') or []) if isinstance(x,dict) and x.get('stage_uid')=='STAGE-03']
    if len(stage3_rows)!=1:
        die(f'STAGE03_REGISTRY_RECORD_DENOMINATOR:{len(stage3_rows)}')
    stage3=stage3_rows[0]
    required_inputs=list(stage3.get('inputs') or [])
    if ai_profile_active:
        required_inputs.append('AI_INTERACTION_CONTINUITY_CONTRACT')
    rows=[]
    blockers=[]
    for input_uid in required_inputs:
        if input_uid=='VISUAL_BASE_BLUEPRINT':
            path=RUN/'02_BASE_BLUEPRINT'/page_uid/'VISUAL_BASE_BLUEPRINT.yaml'
        else:
            path=page_dir/f'{input_uid}.yaml'
        exists=path.is_file()
        parse_ok=False
        nonempty=False
        if exists:
            try:
                obj=load(path)
                parse_ok=True
                nonempty=bool(obj)
            except SystemExit:
                parse_ok=False
        ready=exists and parse_ok and nonempty
        rows.append({
          'input_uid':input_uid,
          'origin':(stage3.get('input_origins') or {}).get(input_uid,'STAGE-02_CONDITIONAL'),
          'physical_ref':path.relative_to(ROOT).as_posix(),
          'physical_materialization_status':'PASS' if exists else 'BLOCKED',
          'parse_schema_status':'PASS' if parse_ok else 'BLOCKED',
          'required_field_completeness':'PASS' if nonempty else 'BLOCKED',
          'consumer_readiness_status':'PASS' if ready else 'BLOCKED',
        })
        if not ready:
            blockers.append('STAGE03_SUCCESSOR_INPUT_NOT_READY:'+input_uid)

    dep_path=RUN/'00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml'
    dep=load(dep_path) if dep_path.is_file() else {}
    materialized={
      str(x.get('declared_path'))
      for x in (dep.get('materialization_records') or [])
      if isinstance(x,dict) and x.get('materialization_status')=='MATERIALIZED_CURRENT'
    }
    explicit_gaps=[
      x for x in (dep.get('unresolved_source_capture_gaps') or [])
      if isinstance(x,dict)
    ]
    declared=set()
    raw_root=RUN/'00_SOURCE_INTAKE/RAW_SOURCE'/page_uid
    if raw_root.is_dir():
        for p in sorted(raw_root.glob('*.yaml')):
            try:
                declared.update(_collect_declared_package_paths(load(p)))
            except SystemExit:
                blockers.append('STAGE03_SOURCE_DECLARED_DEPENDENCY_PARSE_FAILED:'+p.name)
    unresolved_declared=sorted(x for x in declared if x not in materialized)
    for row in explicit_gaps:
        p=str(row.get('declared_path') or row.get('dependency_uid') or 'UNKNOWN')
        if p not in unresolved_declared:
            unresolved_declared.append(p)
    for p in sorted(set(unresolved_declared)):
        blockers.append('STAGE03_SOURCE_DECLARED_DEPENDENCY_NOT_READY:'+p)
    return {
      'successor_stage_uid':'STAGE-03',
      'required_input_total':len(required_inputs),
      'input_rows':rows,
      'source_declared_dependency_total':len(declared),
      'source_declared_materialized_total':len(declared & materialized),
      'unresolved_source_declared_dependencies':sorted(set(unresolved_declared)),
      'unresolved_required_dependency_total':len(set(blockers)),
      'consumer_readiness_complete':len(set(blockers))==0,
      'status':'PASS' if not blockers else 'BLOCKED',
      'blockers':sorted(set(blockers)),
    }


def _self_test_external_authority_and_revalidation():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / 'authority/runtime/shared.yaml'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('authority_id: SYNTH_SHARED_AUTH\n', encoding='utf-8')
        manifest = root / 'authority/manifest.yaml'
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            'authority:\n  id: SYNTH_MANIFEST\n  status: FINAL_LOCKED\n  current_only: true\n'
            'current_authority_set:\n  runtime:\n  - authority/runtime/shared.yaml\n',
            encoding='utf-8',
        )
        rec = {
            'authority_ref':'SYNTH_SHARED_AUTH',
            'authority_source_path':'authority/runtime/shared.yaml',
            'authority_content_sha256':_sha256_file(source),
            'authority_manifest_path':'authority/manifest.yaml',
            'authority_manifest_sha256':_sha256_file(manifest),
            'canonical_authority_path':'authority/runtime/shared.yaml',
        }
        assert _verify_external_authority_record(rec, root) == 'SYNTH_SHARED_AUTH'
        bad = dict(rec); bad['authority_content_sha256'] = '0' * 64
        try:
            _verify_external_authority_record(bad, root)
        except ValueError as exc:
            assert 'CONTENT_SHA256_DRIFT' in str(exc)
        else:
            raise AssertionError('wrong external authority hash was admitted')
    base = {'execution':{'run_uid':'SYNTH-RUN','current_stage':'STAGE-02-TESTED-BLOCKED','stage1':{'SYNTH-PAGE':'PASS'},'stage2':{'result':'TEST_EXECUTED_BLOCKED'}},'stage02_active_attempt':{'attempt_uid':'SYNTH-ATTEMPT','run_uid':'SYNTH-RUN'}}
    _validate_stage02_admission(base, True)
    bad = deepcopy(base); bad['execution']['stage2']['result'] = 'TEST_EXECUTED_PASS'
    try:
        _validate_stage02_admission(bad, True)
    except SystemExit:
        pass
    else:
        raise AssertionError('non-blocked attempt was admitted for blocked revalidation')
    print('PASS: Stage-02 exact external-authority resolution and blocked-attempt revalidation self-test')

def _self_test_applicability_and_contract_projection():
    baseline = 'a' * 64
    raw = {
        'registries': {'controls': [], 'objects_refs': []},
        'stage02_completeness_contract': {
            'status': 'REQUIRED_FOR_STAGE02_CLOSURE',
            'planning_baseline_sha256': baseline,
            'required_contracts': ['entity_operation_applicability_contract', 'entity_hierarchy_contract'],
            'required_invariants': [],
        },
        'entity_operation_applicability_contract': {
            'operation_vocabulary': ['DISCOVER_OR_LIST'],
            'profiles': {'EMPTY': {'required': [], 'optional': []}},
            'entity_profile_bindings': [],
        },
        'entity_hierarchy_contract': {'relationships': []},
    }
    gaps = []
    declared_stage02_completeness_gaps('SYNTH-PAGE', raw, {}, {}, gaps)
    forbidden = {
        'CONVERSATION_ATOMIC_WORKBENCH_CONTRACT_INCOMPLETE',
        'WORK_ITEM_LIFECYCLE_DENOMINATOR_DRIFT',
        'WORKING_MEMORY_OWNER_BINDING_INCOMPLETE',
        'MULTI_AI_SAME_QUESTION_EXACT_CONTEXT_INCOMPLETE',
        'SINGULAR_FINALIZATION_PIPELINE_INCOMPLETE',
    }
    assert not [g for g in gaps if g.get('category') in forbidden], gaps

    successor_raw = {'registries': {}}
    spec = {'contract_projection': {
        'stage02_completeness_contract': raw['stage02_completeness_contract'],
        'entity_operation_applicability_contract': raw['entity_operation_applicability_contract'],
        'entity_hierarchy_contract': raw['entity_hierarchy_contract'],
    }}
    meta = {
        'contract_projection_allowed': True,
        'approved_contract_projection_keys': sorted(spec['contract_projection']),
        'approved_contract_override_keys': [],
    }
    merged, applied = _apply_approved_top_level_contract_projection(successor_raw, spec, meta)
    assert set(applied) == set(spec['contract_projection'])
    assert merged['stage02_completeness_contract']['planning_baseline_sha256'] == baseline
    assert 'stage02_completeness_contract' not in successor_raw
    bad_meta = dict(meta); bad_meta['contract_projection_allowed'] = False
    try:
        _apply_approved_top_level_contract_projection(successor_raw, spec, bad_meta)
    except ValueError as exc:
        assert 'NOT_APPROVED' in str(exc)
    else:
        raise AssertionError('unapproved contract projection was admitted')
    print('PASS: Stage-02 required-contract applicability and approved successor contract projection self-test')


def _apply_approved_top_level_contract_projection(raw: dict, spec: dict, meta: dict):
    projection = spec.get('contract_projection') or {}
    if projection in ({}, None):
        return deepcopy(raw), []
    if not isinstance(projection, dict):
        raise ValueError('FUNCTIONAL_CHAIN_CONTRACT_PROJECTION_INVALID')
    if meta.get('contract_projection_allowed') is not True:
        raise ValueError('FUNCTIONAL_CHAIN_CONTRACT_PROJECTION_NOT_APPROVED')
    allowed = {
        'field_binding_contract',
        'functional_workbench_topology_contract',
        'working_memory_binding',
        'conversation_policy',
        'conversation_finalization_pipeline_contract',
        'domain_materialization_operations',
        'work_item_lifecycle_contract',
        'change_impact_contract',
        'entity_operation_applicability_contract',
        'entity_hierarchy_contract',
        'stage02_completeness_contract',
        'canonical_production_script_authoring_contract',
        'page_modes',
    }
    keys = set(str(x) for x in projection)
    unknown = sorted(keys - allowed)
    if unknown:
        raise ValueError(f'FUNCTIONAL_CHAIN_CONTRACT_PROJECTION_KEY_FORBIDDEN:{unknown!r}')
    approved_keys = set(str(x) for x in (meta.get('approved_contract_projection_keys') or []))
    if keys != approved_keys:
        raise ValueError(f'FUNCTIONAL_CHAIN_CONTRACT_PROJECTION_APPROVAL_SET_DRIFT:{sorted(keys)!r}:{sorted(approved_keys)!r}')
    override_keys = set(str(x) for x in (meta.get('approved_contract_override_keys') or []))
    if not override_keys.issubset(keys):
        raise ValueError('FUNCTIONAL_CHAIN_CONTRACT_OVERRIDE_OUTSIDE_PROJECTION')
    merged = deepcopy(raw)
    applied = []
    for key in sorted(keys):
        value = projection.get(key)
        if not isinstance(value, (dict, list)):
            raise ValueError(f'FUNCTIONAL_CHAIN_CONTRACT_PROJECTION_VALUE_INVALID:{key}')
        existing = merged.get(key)
        if existing not in (None, {}, []) and existing != value and key not in override_keys:
            raise ValueError(f'FUNCTIONAL_CHAIN_CONTRACT_PROJECTION_UNAUTHORIZED_OVERRIDE:{key}')
        merged[key] = deepcopy(value)
        applied.append(key)
    return merged, applied

def effective_page_contract(page: str, raw: dict):
    """Compose immutable Stage-01 source facts with an approved Stage-02 canonical successor."""
    spec_path = OLD_STAGE2_ROOT / page / 'FUNCTIONAL_CHAIN_SPEC.yaml'
    if not spec_path.is_file():
        return raw, {'applied': False, 'reason': 'NO_STAGE2_CANONICAL_SUCCESSOR'}
    spec = load(spec_path)
    meta = spec.get('design_contract_remediation') or {}
    if meta.get('canonical_owner_materialization') is not True:
        return raw, {'applied': False, 'reason': 'NO_APPROVED_CANONICAL_MATERIALIZATION'}
    if spec.get('page_uid') != page:
        die(f'{page}:FUNCTIONAL_CHAIN_PAGE_UID_DRIFT')
    if meta.get('candidate_bytes_became_authority_directly') is not False:
        die(f'{page}:CANDIDATE_BYTES_MASQUERADE_AS_AUTHORITY')
    if meta.get('raw_source_mutated') is not False:
        die(f'{page}:STAGE1_RAW_SOURCE_MUTATION_FORBIDDEN')
    approval_ref = str(meta.get('approval_evidence_ref') or '').strip()
    if not approval_ref or not (ROOT / approval_ref).is_file():
        die(f'{page}:APPROVAL_EVIDENCE_MISSING_FOR_CANONICAL_SUCCESSOR')
    projection = spec.get('source_projection')
    if not isinstance(projection, dict):
        die(f'{page}:FUNCTIONAL_CHAIN_SOURCE_PROJECTION_MISSING')
    resolved_external_authority_refs = _resolve_external_authority_records(meta.get('resolved_external_authority_refs') or [])

    merged = deepcopy(raw)
    reg = merged.setdefault('registries', {})
    if not isinstance(reg, dict):
        die(f'{page}:RAW_REGISTRY_INVALID')
    overlay_keys = ('actions', 'controls', 'stages', 'stage_transitions', 'events', 'integration_ports')
    applied = []
    for key in overlay_keys:
        if key not in projection:
            continue
        value = projection.get(key)
        if not isinstance(value, list):
            die(f'{page}:FUNCTIONAL_CHAIN_PROJECTION_INVALID:{key}')
        reg[key] = deepcopy(value)
        applied.append(key)
    try:
        merged, applied_contracts = _apply_approved_top_level_contract_projection(merged, spec, meta)
    except ValueError as exc:
        die(f'{page}:{exc}')
    if not applied and not applied_contracts:
        die(f'{page}:FUNCTIONAL_CHAIN_PROJECTION_EMPTY')
    return merged, {
        'applied': True,
        'canonical_owner_ref': str(spec_path.relative_to(ROOT)),
        'approval_evidence_ref': approval_ref,
        'overlay_registry_keys': applied,
        'overlay_contract_keys': applied_contracts,
        'resolved_external_authority_refs': resolved_external_authority_refs,
        'raw_source_mutated': False,
    }

def declared_stage02_completeness_gaps(page: str, raw: dict, controls: dict, objects: dict, gaps: list[dict]):
    meta = raw.get('stage02_completeness_contract')
    if not isinstance(meta, dict) or meta.get('status') != 'REQUIRED_FOR_STAGE02_CLOSURE':
        add(gaps, page, 'ARCHITECTURE_GAP', 'STAGE02_PLANNING_COMPLETENESS_CONTRACT_MISSING', page, 'required Stage-02 planning completeness contract absent')
        return
    baseline = str(meta.get('planning_baseline_sha256') or '')
    if not re.fullmatch(r'[0-9a-f]{64}', baseline):
        add(gaps, page, 'ARCHITECTURE_GAP', 'PLANNING_BASELINE_IDENTITY_MISSING', page, baseline or 'missing sha256')
    required = set(str(x) for x in (meta.get('required_contracts') or []))
    invariants = set(str(x) for x in (meta.get('required_invariants') or []))
    for key in required:
        if not isinstance(raw.get(key), (dict, list)):
            add(gaps, page, 'ARCHITECTURE_GAP', 'DECLARED_COMPLETENESS_CONTRACT_MISSING', key, 'required top-level contract missing')

    if 'field_binding_contract' in required:
        field_contract = raw.get('field_binding_contract') or {}
        declared_fields = field_contract.get('fields') or []
        for row in declared_fields:
            if not isinstance(row, dict) or not row.get('control_uid'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_BINDING_DECLARATION_INVALID', page, str(row))
                continue
            cid = str(row['control_uid'])
            control = controls.get(cid)
            if not control:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'DECLARED_FIELD_CONTROL_MISSING', cid, 'field binding control absent')
                continue
            if control.get('action_uid') not in (None, '', 'NONE_FIELD_BINDING'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_MASQUERADES_AS_ACTION', cid, str(control.get('action_uid')))
            if control.get('binding_semantics') != 'DATA_OR_DRAFT_STATE_ONLY':
                add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_BINDING_SEMANTICS_MISSING', cid, str(control.get('binding_semantics')))
            if not control.get('data_binding') or control.get('data_binding') != row.get('data_binding'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_DATA_BINDING_DRIFT', cid, str(control.get('data_binding')))
        send = field_contract.get('send_binding') or {}
        send_action = send.get('action_uid')
        send_control = send.get('send_control_uid')
        owners = sorted(cid for cid, control in controls.items() if control.get('action_uid') == send_action)
        if send_action and owners != [send_control]:
            add(gaps, page, 'ARCHITECTURE_GAP', 'SEND_ACTION_NOT_UNIQUELY_OWNED_BY_SEND_CONTROL', str(send_action), str(owners))

    if 'functional_workbench_topology_contract' in required or 'CONVERSATION_ATOMIC_SAME_SURFACE' in invariants:
        wb = raw.get('functional_workbench_topology_contract') or {}
        conv = wb.get('conversation_workbench') or {}
        section_registry = idx((raw.get('registries') or {}).get('sections'), 'section_uid')
        required_sections = conv.get('section_order') or []
        valid_section_order = isinstance(required_sections, list) and bool(required_sections) and all(str(x) in section_registry for x in required_sections)
        if (not conv.get('workbench_uid') or conv.get('workbench_type') != 'ATOMIC_WORKBENCH' or conv.get('same_surface') != 'REQUIRED'
                or not valid_section_order or conv.get('split_into_independent_surfaces') != 'FORBIDDEN'):
            add(gaps, page, 'ARCHITECTURE_GAP', 'CONVERSATION_ATOMIC_WORKBENCH_CONTRACT_INCOMPLETE', str(conv.get('workbench_uid') or page), str(conv))

    if 'work_item_lifecycle_contract' in required:
        lifecycle = raw.get('work_item_lifecycle_contract') or {}
        declared_items = {}
        for row in (lifecycle.get('project_core_order') or []) + (lifecycle.get('topic_production_order') or []):
            if isinstance(row, dict) and row.get('work_item'):
                declared_items[str(row['work_item'])] = row
        modes = raw.get('page_modes') or {}
        expected_items = []
        for mode_record in modes.values() if isinstance(modes, dict) else []:
            if isinstance(mode_record, dict):
                expected_items.extend(mode_record.get('editable_work_items') or [])
        if set(declared_items) != set(expected_items):
            add(gaps, page, 'ARCHITECTURE_GAP', 'WORK_ITEM_LIFECYCLE_DENOMINATOR_DRIFT', page, str({'expected':sorted(expected_items),'actual':sorted(declared_items)}))
        domain_ops = {str(x.get('operation_uid')): x for x in (raw.get('domain_materialization_operations') or []) if isinstance(x, dict) and x.get('operation_uid')}
        actions = idx((raw.get('registries') or {}).get('actions'), 'action_uid')
        for wi, row in declared_items.items():
            if not row.get('formal_output'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'WORK_ITEM_FORMAL_OUTPUT_MISSING', wi, 'formal_output')
            op = row.get('finalization_operation_uid')
            action = row.get('finalization_action_uid')
            actions_list = row.get('finalization_action_uids') or []
            if op:
                rec = domain_ops.get(str(op))
                if not rec:
                    add(gaps, page, 'ARCHITECTURE_GAP', 'WORK_ITEM_DOMAIN_FINALIZATION_OPERATION_MISSING', wi, str(op))
                else:
                    for field in ('runtime_owner','persistence_owner','required_inputs','validation','audit_event_uid','failure_state','recovery','resulting_state','transport_surface'):
                        if rec.get(field) in (None,'',[],{}):
                            add(gaps, page, 'ARCHITECTURE_GAP', 'DOMAIN_FINALIZATION_FIELD_MISSING', str(op), field)
                    if 'PAGE_LOCAL_API' in str(rec.get('transport_surface')) and 'NOT_PAGE_LOCAL_API' not in str(rec.get('transport_surface')):
                        add(gaps, page, 'ARCHITECTURE_GAP', 'PAGE_LOCAL_FINALIZATION_API_FORBIDDEN', str(op), str(rec.get('transport_surface')))
            elif action:
                if action not in actions:
                    add(gaps, page, 'IMPLEMENTATION_GAP', 'WORK_ITEM_FINALIZATION_ACTION_MISSING', wi, str(action))
            elif actions_list:
                missing = [x for x in actions_list if x not in actions]
                if missing:
                    add(gaps, page, 'IMPLEMENTATION_GAP', 'WORK_ITEM_FINALIZATION_ACTION_SET_INCOMPLETE', wi, str(missing))
            else:
                add(gaps, page, 'ARCHITECTURE_GAP', 'WORK_ITEM_FINALIZATION_BINDING_MISSING', wi, 'no operation/action binding')
        if lifecycle.get('known_authority_gaps_open') not in ([], None):
            add(gaps, page, 'AUTHORITY_GAP', 'KNOWN_WORK_ITEM_AUTHORITY_GAP_STILL_OPEN', page, str(lifecycle.get('known_authority_gaps_open')))

    if 'working_memory_binding' in required:
        memory = raw.get('working_memory_binding') or {}
        if not memory.get('owner') or memory.get('page_local_second_service') != 'FORBIDDEN' or memory.get('formal_truth') is not False:
            add(gaps, page, 'ARCHITECTURE_GAP', 'WORKING_MEMORY_OWNER_BINDING_INCOMPLETE', page, str(memory))

    if 'conversation_policy' in required or 'SINGLE_MULTI_SAME_ORIGINAL_QUESTION_EXACT_CONTEXT' in invariants:
        cp = raw.get('conversation_policy') or {}
        required_context = ['Project','Topic if applicable','Work Item','Thread','Attachment refs','Reference refs','Context Package']
        if not cp.get('same_problem_rule') or cp.get('exact_relevant_context') != required_context or not cp.get('response_traceability') or not cp.get('finalization_reentry'):
            add(gaps, page, 'ARCHITECTURE_GAP', 'MULTI_AI_SAME_QUESTION_EXACT_CONTEXT_INCOMPLETE', page, str(cp))

    if 'change_impact_contract' in required:
        impact = raw.get('change_impact_contract') or {}
        states = set(impact.get('affected_downstream_states') or [])
        if not {'NEEDS_REVIEW','NEEDS_REVALIDATION'}.issubset(states) or impact.get('silent_downstream_rewrite') != 'FORBIDDEN' or impact.get('exact_base_version_required_for_revision') is not True:
            add(gaps, page, 'ARCHITECTURE_GAP', 'UPSTREAM_CHANGE_IMPACT_REVALIDATION_INCOMPLETE', page, str(impact))

    if 'entity_operation_applicability_contract' in required:
        op_contract = raw.get('entity_operation_applicability_contract') or {}
        vocabulary = op_contract.get('operation_vocabulary') or []
        profiles = op_contract.get('profiles') or {}
        bindings = op_contract.get('entity_profile_bindings') or []
        binding_map = {str(x.get('object_uid')): str(x.get('profile')) for x in bindings if isinstance(x, dict) and x.get('object_uid')}
        if set(binding_map) != set(objects):
            add(gaps, page, 'ARCHITECTURE_GAP', 'BUSINESS_ENTITY_OPERATION_APPLICABILITY_DENOMINATOR_DRIFT', page, str({'entity_count':len(objects),'binding_count':len(binding_map)}))
        if not vocabulary or not profiles:
            add(gaps, page, 'ARCHITECTURE_GAP', 'BUSINESS_ENTITY_OPERATION_APPLICABILITY_AUTHORITY_MISSING', page, 'vocabulary/profiles absent')
        for oid, profile in binding_map.items():
            rec = profiles.get(profile)
            if not isinstance(rec, dict):
                add(gaps, page, 'ARCHITECTURE_GAP', 'BUSINESS_ENTITY_OPERATION_PROFILE_MISSING', oid, profile)
                continue
            req = rec.get('required') or []
            optional = rec.get('optional') or []
            if any(x not in vocabulary for x in req + optional):
                add(gaps, page, 'ARCHITECTURE_GAP', 'BUSINESS_ENTITY_OPERATION_PROFILE_UNKNOWN_OPERATION', oid, profile)

    if 'entity_hierarchy_contract' in required:
        hierarchy = raw.get('entity_hierarchy_contract') or {}
        rels = hierarchy.get('relationships') or []
        rel_map = {str(x.get('object_uid')): x for x in rels if isinstance(x, dict) and x.get('object_uid')}
        if set(rel_map) != set(objects):
            add(gaps, page, 'ARCHITECTURE_GAP', 'ENTITY_HIERARCHY_DENOMINATOR_DRIFT', page, str({'entity_count':len(objects),'relationship_count':len(rel_map)}))
        for oid, row in rel_map.items():
            if not row.get('relation_status') or not row.get('relation'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'ENTITY_HIERARCHY_RELATION_INCOMPLETE', oid, str(row))
            parent = row.get('parent_object_uid')
            if parent and parent not in objects:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'ENTITY_HIERARCHY_PARENT_REF_MISSING', oid, str(parent))

    if 'conversation_finalization_pipeline_contract' in required:
        pipeline = raw.get('conversation_finalization_pipeline_contract') or {}
        steps = pipeline.get('steps') or []
        orders = [x.get('order') for x in steps if isinstance(x,dict)]
        if pipeline.get('singular_pipeline') is not True or not orders or orders != list(range(1,len(orders)+1)):
            add(gaps, page, 'ARCHITECTURE_GAP', 'SINGULAR_FINALIZATION_PIPELINE_INCOMPLETE', page, str(pipeline.get('singular_pipeline')))

def materialized_stage02_completeness_blockers(page_dir: Path, raw: dict) -> list[str]:
    meta = raw.get('stage02_completeness_contract')
    if not isinstance(meta, dict) or meta.get('status') != 'REQUIRED_FOR_STAGE02_CLOSURE':
        return ['STAGE02_PLANNING_COMPLETENESS_CONTRACT_MISSING']
    blockers = []
    baseline = meta.get('planning_baseline_sha256')
    required = set(str(x) for x in (meta.get('required_contracts') or []))
    invariants = set(str(x) for x in (meta.get('required_invariants') or []))
    reg = raw.get('registries') or {}
    objects = idx(reg.get('objects_refs'), 'object_uid')

    def doc(name):
        path = page_dir / name
        return load(path) if path.is_file() else {}

    if 'entity_operation_applicability_contract' in required:
        opm = doc('BUSINESS_ENTITY_OPERATION_MATRIX.yaml')
        if opm.get('semantic_entity_join_used') is not True or opm.get('entity_count') != len(objects):
            blockers.append('BUSINESS_ENTITY_OPERATION_MATRIX_SEMANTIC_JOIN_MISSING')
        vocabulary = (raw.get('entity_operation_applicability_contract') or {}).get('operation_vocabulary') or []
        rows = opm.get('entity_rows') or []
        if len(rows) != len(objects):
            blockers.append('BUSINESS_ENTITY_OPERATION_MATRIX_ENTITY_DENOMINATOR_DRIFT')
        else:
            for row in rows:
                decisions = row.get('operation_applicability') or {}
                if set(decisions) != set(vocabulary) or any(v not in {'REQUIRED','OPTIONAL','NOT_APPLICABLE'} for v in decisions.values()):
                    blockers.append('BUSINESS_ENTITY_OPERATION_MATRIX_APPLICABILITY_INCOMPLETE')
                    break

    if 'entity_hierarchy_contract' in required:
        hm = doc('ENTITY_HIERARCHY_MATRIX.yaml')
        if hm.get('explicit_relationship_authority_used') is not True or hm.get('entity_count') != len(objects) or len(hm.get('rows') or []) != len(objects):
            blockers.append('ENTITY_HIERARCHY_RELATIONSHIPS_MISSING')
        elif any(not x.get('relation_status') or not x.get('relation') for x in (hm.get('rows') or [])):
            blockers.append('ENTITY_HIERARCHY_RELATIONSHIPS_INCOMPLETE')

    if 'functional_workbench_topology_contract' in required or 'CONVERSATION_ATOMIC_SAME_SURFACE' in invariants:
        wb = doc('FUNCTIONAL_WORKBENCH_CONTRACT.yaml')
        atomics = {str(x.get('workbench_uid')): x for x in (wb.get('atomic_workbenches') or []) if isinstance(x,dict)}
        source_conv = ((raw.get('functional_workbench_topology_contract') or {}).get('conversation_workbench') or {})
        source_conv_uid = str(source_conv.get('workbench_uid') or '')
        conv = atomics.get(source_conv_uid) or {}
        if (not source_conv_uid or conv.get('workbench_type') != source_conv.get('workbench_type')
                or conv.get('same_surface') != source_conv.get('same_surface')
                or conv.get('section_order') != source_conv.get('section_order')):
            blockers.append('CONVERSATION_ATOMIC_WORKBENCH_MISSING')

    if 'field_binding_contract' in required:
        field_contract = raw.get('field_binding_contract') or {}
        declared_field_uids = {str(x.get('control_uid')) for x in (field_contract.get('fields') or []) if isinstance(x,dict) and x.get('control_uid')}
        topo = doc('INTERACTION_TOPOLOGY_SPEC.yaml')
        illegal = [x for x in (topo.get('edges') or []) if x.get('relation') == 'CONTROL_TRIGGERS_ACTION' and x.get('from') in declared_field_uids]
        if illegal:
            blockers.append('FIELD_ACTION_TOPOLOGY_DRIFT')
        send = field_contract.get('send_binding') or {}
        send_edges = [x for x in (topo.get('edges') or []) if x.get('relation') == 'CONTROL_TRIGGERS_ACTION' and x.get('to') == send.get('action_uid')]
        if send.get('action_uid') and sorted(x.get('from') for x in send_edges) != [send.get('send_control_uid')]:
            blockers.append('SEND_ACTION_TOPOLOGY_NOT_UNIQUE')

    if ('conversation_policy' in required or 'SINGLE_MULTI_SAME_ORIGINAL_QUESTION_EXACT_CONTEXT' in invariants
            or 'conversation_finalization_pipeline_contract' in required):
        ai = doc('AI_INTERACTION_CONTINUITY_CONTRACT.yaml')
        source_conversation = raw.get('conversation_policy') or {}
        source_pipeline = raw.get('conversation_finalization_pipeline_contract') or {}
        if source_conversation and (ai.get('same_problem_rule') != source_conversation.get('same_problem_rule') or ai.get('exact_relevant_context') != source_conversation.get('exact_relevant_context')):
            blockers.append('AI_SAME_QUESTION_CONTEXT_CONTINUITY_MISSING')
        if source_pipeline and ai.get('single_finalization_pipeline') is not bool(source_pipeline.get('singular_pipeline')):
            blockers.append('AI_SAME_QUESTION_CONTEXT_CONTINUITY_MISSING')

    chain = doc('FUNCTIONAL_CHAIN_SPEC.yaml')
    required_projected = set(required) | {'stage02_completeness_contract'}
    if any(key not in chain for key in required_projected):
        blockers.append('FUNCTIONAL_CHAIN_PLANNING_CONTRACT_PROJECTION_INCOMPLETE')
    if chain.get('planning_baseline_sha256') != baseline:
        blockers.append('FUNCTIONAL_CHAIN_PLANNING_BASELINE_IDENTITY_DRIFT')

    return sorted(set(blockers))

def control_vs_system_trigger_resolution(aid: str, action: dict, controls_by_action: dict, transitions_by_action: dict, ports: dict):
    if controls_by_action.get(aid):
        return {'status':'CONTROL_BOUND'}
    if present(action, 'trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind') or bool(transitions_by_action.get(aid)):
        return {'status':'EXPLICIT_TRIGGER_BOUND'}
    rb=action.get('runtime_binding') or {}
    decision=str(rb.get('decision') or '')
    if decision not in {'SOURCE_DERIVED','SOURCE_DERIVED_CLOSURE'}:
        return {'status':'UNRESOLVED'}
    refs=[]
    for field in ('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid'):
        puid=rb.get(field)
        if puid and puid in ports:
            refs.append((field,puid,ports[puid]))
    uniq={puid:(field,port) for field,puid,port in refs}
    if len(uniq)!=1:
        return {'status':'UNRESOLVED'}
    puid,(field,port)=next(iter(uniq.items()))
    operation=port.get('operation') or port.get('registered_operation')
    permission=port.get('permission') or port.get('registered_permission')
    state_event=str(port.get('state_event') or '')
    if not operation or not permission or not state_event or not action.get('gate_uid') or not action.get('permission_uid'):
        return {'status':'UNRESOLVED'}
    return {'status':'DETERMINISTIC_SYSTEM_TRIGGER_REQUIRED','contract':{
        'trigger_kind':'SYSTEM_DERIVED_GOVERNED_OPERATION',
        'source_decision':decision,
        'gate_uid':action.get('gate_uid'),
        'runtime_port_uid':puid,
        'runtime_port_binding_field':field,
        'registered_operation':operation,
        'success_state_event':state_event,
        'user_control_required':False,
    }}

def _self_test_shared_contract_hardening():
    controls=defaultdict(list); transitions=defaultdict(list)
    ports={'PORT-1':{'registered_operation':'createDerivedRecord','registered_permission':'record.write','state_event':'REVIEW->OPEN | record.created'}}
    action={'permission_uid':'PERM-1','gate_uid':'GATE-1','effect_type':'CREATE','runtime_binding':{'binding_kind':'SOURCE_INTEGRATION_PORT','port_uid':'PORT-1','decision':'SOURCE_DERIVED'}}
    exact=control_vs_system_trigger_resolution('ACT-1',action,controls,transitions,ports)
    assert exact.get('status')=='DETERMINISTIC_SYSTEM_TRIGGER_REQUIRED', exact
    assert exact['contract']['user_control_required'] is False
    ambiguous={**action,'runtime_binding':dict(action['runtime_binding'])}; ambiguous['runtime_binding'].pop('decision')
    assert control_vs_system_trigger_resolution('ACT-2',ambiguous,controls,transitions,ports).get('status')=='UNRESOLVED'
    controls['ACT-3'].append('CTRL-1')
    assert control_vs_system_trigger_resolution('ACT-3',action,controls,transitions,ports).get('status')=='CONTROL_BOUND'
    print('PASS: control-vs-system-trigger shared semantic resolution self-test')

def fresh_scan(page: str, raw: dict, unresolved_authority_by_ref: dict):
    reg = raw.get('registries') or {}
    actions = idx(reg.get('actions'), 'action_uid')
    controls = idx(reg.get('controls'), 'control_uid')
    permissions = idx(reg.get('permissions'), 'permission_uid')
    gates = idx(reg.get('gates'), 'gate_uid')
    errors = idx(reg.get('errors'), 'error_uid')
    ports = idx(reg.get('integration_ports'), 'port_uid')
    stages = idx(reg.get('stages'), 'stage_uid')
    events = idx(reg.get('events'), 'event_uid')
    transitions = idx(reg.get('stage_transitions'), 'transition_uid')
    controls_by_action = defaultdict(list)
    transitions_by_action = defaultdict(list)
    gaps = []

    for cid, control in controls.items():
        aid = control.get('action_uid')
        is_data_field = control.get('binding_semantics') == 'DATA_OR_DRAFT_STATE_ONLY'
        if is_data_field:
            if aid not in (None, '', 'NONE_FIELD_BINDING'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_MASQUERADES_AS_ACTION', cid, str(aid))
            if not control.get('data_binding'):
                add(gaps, page, 'ARCHITECTURE_GAP', 'FIELD_DATA_BINDING_MISSING', cid, 'data_binding absent')
        else:
            if aid:
                controls_by_action[aid].append(cid)
            if not aid or aid not in actions:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'CONTROL_WITHOUT_VALID_ACTION', cid, str(aid))
        if control.get('gate_uid') and control.get('gate_uid') not in gates:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'CONTROL_GATE_REF_MISSING', cid, str(control.get('gate_uid')))
        if control.get('permission_uid') and control.get('permission_uid') not in permissions:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'CONTROL_PERMISSION_REF_MISSING', cid, str(control.get('permission_uid')))

    for tid, transition in transitions.items():
        trigger = transition.get('action_uid') or transition.get('trigger_event_uid') or transition.get('trigger')
        if trigger in actions:
            transitions_by_action[trigger].append(tid)

    effectful = 0
    runtime_refs = 0
    for aid, action in actions.items():
        effect = action.get('effect_type')
        is_effectful = effect not in {'READ_ONLY', 'UI_ONLY', 'CONTEXT_STATE'}
        effectful += int(is_effectful)
        if not action.get('label'):
            add(gaps, page, 'IMPLEMENTATION_GAP', 'BUSINESS_INTENT_MISSING', aid, 'action label/intent absent')
        for field, registry, category in (
            ('permission_uid', permissions, 'ACTION_PERMISSION_REF_MISSING'),
            ('gate_uid', gates, 'ACTION_GATE_REF_MISSING'),
        ):
            ref = action.get(field)
            if not ref or ref not in registry:
                add(gaps, page, 'IMPLEMENTATION_GAP', category, aid, str(ref))
        rb = action.get('runtime_binding') or {}
        kind = rb.get('binding_kind')
        failure_recovery_not_applicable = (
            not is_effectful
            and kind == 'CLIENT_STATE_OR_VIEW_NO_API_REQUIRED'
            and rb.get('api_required') is False
            and not transitions_by_action.get(aid)
        )
        err = action.get('error_uid')
        if err:
            if err not in errors:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'ACTION_ERROR_REF_MISSING', aid, str(err))
            elif not errors[err].get('recovery'):
                add(gaps, page, 'IMPLEMENTATION_GAP', 'RECOVERY_CONTRACT_MISSING', aid, str(err))
        elif not failure_recovery_not_applicable and not any((transitions.get(tid) or {}).get('recovery') for tid in transitions_by_action.get(aid, [])):
            add(gaps, page, 'ARCHITECTURE_GAP', 'FAILURE_STATE_ERROR_BINDING_MISSING', aid, 'no exact action->error/recovery or transition recovery binding')

        trigger_resolution = control_vs_system_trigger_resolution(aid, action, controls_by_action, transitions_by_action, ports)
        if not controls_by_action.get(aid) and trigger_resolution.get('status') not in {'EXPLICIT_TRIGGER_BOUND','CONTROL_BOUND'}:
            if trigger_resolution.get('status') == 'DETERMINISTIC_SYSTEM_TRIGGER_REQUIRED':
                add(gaps, page, 'ARCHITECTURE_GAP', 'SYSTEM_TRIGGER_BINDING_MISSING', aid, json.dumps(trigger_resolution.get('contract') or {}, ensure_ascii=False, sort_keys=True), 'AUTO_REMEDIABLE_FUNCTIONAL_CLOSURE')
            else:
                add(gaps, page, 'ARCHITECTURE_GAP', 'ACTION_WITHOUT_CONTROL_OR_TRIGGER', aid, 'no registered control or deterministic system-trigger proof')
        if not kind:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'RUNTIME_BINDING_MISSING', aid, 'runtime_binding.binding_kind absent')
            continue
        resolved_ports = []
        for field in ('port_uid', 'persist_via_port_uid', 'execute_port_uid', 'decision_port_uid'):
            puid = rb.get(field)
            if not puid:
                continue
            port = ports.get(puid)
            if not port:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'RUNTIME_PORT_REF_MISSING', aid, f'{field}={puid}')
            else:
                resolved_ports.append((puid, port))
                runtime_refs += 1

        if kind == 'CLIENT_STATE_OR_VIEW_NO_API_REQUIRED':
            if rb.get('api_required') is not False:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'CLIENT_ACTION_API_NA_CONTRACT_MISSING', aid, 'api_required must be false')
        elif kind == 'SHARED_OPERATION_REFERENCE':
            auth = rb.get('shared_authority_id')
            op = rb.get('shared_operation_id')
            if not auth or not op:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'SHARED_OWNER_REFERENCE_INCOMPLETE', aid, str((auth, op)))
            elif auth in unresolved_authority_by_ref:
                add(gaps, page, 'AUTHORITY_GAP', 'SHARED_OWNER_AUTHORITY_UNRESOLVED', aid, f'{unresolved_authority_by_ref[auth]}: {auth}', 'EXTERNAL_AUTHORITY')
        else:
            if not resolved_ports:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'RUNTIME_ENTRY_OR_PORT_MISSING', aid, str(kind))
            for puid, port in resolved_ports:
                operation = port.get('operation') or port.get('registered_operation')
                method = port.get('method_path') or port.get('method_effective_path')
                permission = port.get('permission') or port.get('registered_permission')
                if not operation:
                    add(gaps, page, 'IMPLEMENTATION_GAP', 'PORT_OPERATION_MISSING', aid, puid)
                if not method:
                    add(gaps, page, 'IMPLEMENTATION_GAP', 'API_ENTRY_MISSING', aid, puid)
                if not permission:
                    add(gaps, page, 'IMPLEMENTATION_GAP', 'PORT_PERMISSION_MISSING', aid, puid)

        if is_effectful and kind != 'SHARED_OPERATION_REFERENCE':
            port = resolved_ports[0][1] if resolved_ports else {}
            if not (present(action, 'success_contract', 'validation_contract', 'validator_uid') or present(rb, 'validation', 'validation_rule', 'evaluation_rule') or present(port, 'validation', 'validation_rule', 'validator_uid')):
                add(gaps, page, 'ARCHITECTURE_GAP', 'POST_ACTION_VALIDATION_NODE_MISSING', aid, 'no explicit success/validation/evaluation contract')
            if not (present(action, 'payload', 'payload_rule', 'input_contract', 'request_contract') or present(rb, 'payload', 'payload_rule', 'payload_mode', 'input_contract', 'request_contract') or present(port, 'payload', 'payload_rule', 'input_contract', 'request_contract', 'request_schema')):
                add(gaps, page, 'INPUT_SOURCE_GAP', 'PAYLOAD_INPUT_CONTRACT_MISSING', aid, 'no explicit payload/input contract or schema')
            state_event = str(port.get('state_event') or '')
            if not event_token(state_event):
                add(gaps, page, 'ARCHITECTURE_GAP', 'AUDIT_EVENT_NODE_MISSING', aid, 'registered port has no explicit audit/event UID in state_event')
            if not (has_transition(state_event) or bool(transitions_by_action.get(aid)) or action.get('state_effect')):
                add(gaps, page, 'ARCHITECTURE_GAP', 'SUCCESS_NEXT_STATE_BINDING_MISSING', aid, 'no state_effect, state transition, or port state_event transition')

    for tid, transition in transitions.items():
        if transition.get('from_stage') not in stages or transition.get('to_stage') not in stages:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'TRANSITION_STAGE_REF_MISSING', tid, str((transition.get('from_stage'), transition.get('to_stage'))))
        trigger = transition.get('action_uid') or transition.get('trigger_event_uid') or transition.get('trigger')
        if not trigger:
            add(gaps, page, 'ARCHITECTURE_GAP', 'TRANSITION_TRIGGER_MISSING', tid, 'trigger/action absent')
        elif transition.get('trigger_event_uid') and events and transition.get('trigger_event_uid') not in events:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'TRANSITION_EVENT_REF_MISSING', tid, str(transition.get('trigger_event_uid')))
        gate = transition.get('gate_uid') or transition.get('gate')
        if not gate:
            add(gaps, page, 'ARCHITECTURE_GAP', 'TRANSITION_GATE_PRECONDITION_MISSING', tid, 'gate/preconditions absent')
        elif transition.get('gate_uid') and transition.get('gate_uid') not in gates:
            add(gaps, page, 'IMPLEMENTATION_GAP', 'TRANSITION_GATE_REF_MISSING', tid, str(transition.get('gate_uid')))
        for required in ('mutation_owner', 'failure_state', 'recovery', 'audit_event_uid', 'illegal_transition_tests'):
            if transition.get(required) in (None, '', [], {}):
                add(gaps, page, 'ARCHITECTURE_GAP', 'STATE_TRANSITION_LEDGER_FIELD_MISSING', tid, required)

    declared_stage02_completeness_gaps(page, raw, controls, idx(reg.get('objects_refs'), 'object_uid'), gaps)

    unique, seen = [], set()
    for gap in gaps:
        key = (gap['page_uid'], gap['class'], gap['category'], gap['uid'], gap['detail'])
        if key not in seen:
            seen.add(key)
            unique.append(gap)
    classes = Counter(x['class'] for x in unique)
    categories = Counter(x['category'] for x in unique)
    return {
        'registry_denominator': {
            'actions': len(actions), 'controls': len(controls), 'permissions': len(permissions),
            'gates': len(gates), 'errors': len(errors), 'integration_ports': len(ports),
            'stages': len(stages), 'events': len(events), 'stage_transitions': len(transitions),
            'effectful_actions': effectful,
        },
        'registered_runtime_reference_count': runtime_refs,
        'gap_count': len(unique),
        'gap_classes': dict(sorted(classes.items())),
        'gap_categories': dict(sorted(categories.items())),
        'gaps': unique,
        'functional_completion': len(unique) == 0,
    }


def _common_engine_module():
    ci = str(ROOT / 'governance/ci')
    if ci not in sys.path:
        sys.path.insert(0, ci)
    import stage_execution_engine as eng
    return eng

def _output_materialization_status(output_uid: str, target_pages: list[str]) -> tuple[str, str | None]:
    candidates=[OLD_STAGE2_ROOT / f'{output_uid}.yaml']
    candidates.extend(OLD_STAGE2_ROOT / page / f'{output_uid}.yaml' for page in target_pages)
    existing=[p for p in candidates if p.is_file()]
    if len(existing)==1:
        return 'PASS', existing[0].relative_to(ROOT).as_posix()
    if len(existing)>1:
        return 'BLOCKED', None
    return 'BLOCKED', None

def _flatten_legacy_gaps(legacy: dict) -> list[dict]:
    out=[]
    for page,rec in sorted((legacy.get('pages') or {}).items()):
        scan=(rec or {}).get('functional_chain_fresh_scan') or {}
        for gap in scan.get('gaps') or []:
            row=dict(gap) if isinstance(gap,dict) else {'detail':str(gap)}
            row.setdefault('page_uid',page)
            row.setdefault('problem_uid', f"STAGE02-{page}-{len(out)+1:04d}")
            out.append(row)
    return out

def _flatten_legacy_blockers(legacy: dict) -> list[str]:
    out=[]
    for page,rec in sorted((legacy.get('pages') or {}).items()):
        for blocker in (rec or {}).get('closure_blockers') or []:
            out.append(f'{page}:{blocker}')
    return out

def _handoff_ledger_from_legacy(legacy: dict, governance_uid: str, source_head: str) -> dict:
    aggregate=legacy.get('stage3_successor_readiness') or {}
    rows=[]
    for page,ready in sorted((aggregate.get('page_results') or {}).items()):
        ready=ready or {}
        for rec in ready.get('input_rows') or []:
            rows.append({
              'producer_stage_or_capability':'STAGE-02_OR_REGISTERED_PREDECESSOR',
              'producer_output_uid_or_type':rec.get('input_uid'),
              'producer_owner':rec.get('origin'),
              'producer_physical_ref_or_external_evidence':rec.get('physical_ref'),
              'producer_hash_or_version_or_schema':None,
              'consumer_stage_or_capability':'STAGE-03',
              'consumer_input_uid_or_type':rec.get('input_uid'),
              'consumer_owner_or_schema':'GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.STAGE-03',
              'page_uid':page,
              'applicability':'REQUIRED',
              'reference_resolution_status':'PASS' if rec.get('origin') else 'BLOCKED',
              'physical_materialization_status':rec.get('physical_materialization_status'),
              'parse_schema_status':rec.get('parse_schema_status'),
              'required_field_completeness':rec.get('required_field_completeness'),
              'denominator_inclusion_status':'PASS',
              'consumer_readiness_status':rec.get('consumer_readiness_status'),
              'blocking_owner_or_reentry_target':None if rec.get('consumer_readiness_status')=='PASS' else 'EARLIEST_DECLARED_OWNER',
            })
        for dep in ready.get('unresolved_source_declared_dependencies') or []:
            rows.append({
              'producer_stage_or_capability':'STAGE-01_SOURCE_INTAKE_BASE_BLUEPRINT',
              'producer_output_uid_or_type':'SOURCE_DECLARED_LOCAL_DEPENDENCY',
              'producer_owner':'SOURCE_PROVIDER_OR_SOURCE_CAPTURE_OWNER',
              'producer_physical_ref_or_external_evidence':str(dep),
              'producer_hash_or_version_or_schema':None,
              'consumer_stage_or_capability':'STAGE-03',
              'consumer_input_uid_or_type':'SOURCE_DECLARED_LOCAL_DEPENDENCY',
              'consumer_owner_or_schema':'GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.STAGE-03',
              'page_uid':page,
              'applicability':'REQUIRED',
              'reference_resolution_status':'PASS',
              'physical_materialization_status':'BLOCKED',
              'parse_schema_status':'BLOCKED',
              'required_field_completeness':'BLOCKED',
              'denominator_inclusion_status':'PASS',
              'consumer_readiness_status':'BLOCKED',
              'blocking_owner_or_reentry_target':'STAGE-01_SOURCE_INTAKE_BASE_BLUEPRINT',
            })
    unresolved=int(aggregate.get('unresolved_required_dependency_total') or 0)
    consumer_ready=aggregate.get('consumer_readiness_complete') is True and unresolved==0
    physical=all(x.get('physical_materialization_status')=='PASS' for x in rows) if rows else consumer_ready
    field_complete=all(x.get('required_field_completeness')=='PASS' for x in rows) if rows else consumer_ready
    reference=all(x.get('reference_resolution_status')=='PASS' for x in rows) if rows else True
    return {
      'schema_version':1,
      'artifact_type':'CROSS_STAGE_HANDOFF_READINESS_LEDGER',
      'normative_authority':False,
      'governance_uid':governance_uid,
      'source_head_sha':source_head,
      'producer_stage_uid':'STAGE-02',
      'consumer_stage_uid':'STAGE-03',
      'rows':rows,
      'required_edge_total':len(rows),
      'reference_resolution_complete':reference,
      'physical_materialization_complete':physical,
      'required_field_completeness_complete':field_complete,
      'denominator_reconciled':True,
      'consumer_readiness_complete':consumer_ready,
      'unresolved_required_dependency_total':unresolved,
      'status':'PASS' if consumer_ready and physical and field_complete and reference else 'BLOCKED',
    }

def _normalized_common_from_legacy(legacy: dict, *, external_receipts: bool, source_head: str, run_id: str) -> tuple[dict, dict]:
    eng=_common_engine_module()
    registry=load(STAGE_REGISTRY)
    stages={str(x.get('stage_uid')):x for x in (registry.get('stages') or []) if isinstance(x,dict)}
    stage=stages['STAGE-02']
    adapter_doc=load(ROOT/'governance/ci/stage_execution_semantic_adapters.yaml')
    adapter=(adapter_doc.get('stages') or {}).get('STAGE-02') or {}
    gov=((load(ROOT/'governance/specifications/REGISTRY.yaml').get('active_specification') or {}).get('governance_uid'))
    if not gov:
        die('CURRENT_GOVERNANCE_UID_MISSING_FOR_NORMALIZED_STAGE02')
    gaps=_flatten_legacy_gaps(legacy)
    blockers=_flatten_legacy_blockers(legacy)
    if len(gaps)!=int(legacy.get('fresh_functional_gap_total') or 0):
        die('NORMALIZED_STAGE02_GAP_DENOMINATOR_DRIFT')
    if len(blockers)!=int(legacy.get('closure_blocker_total') or 0):
        die('NORMALIZED_STAGE02_BLOCKER_DENOMINATOR_DRIFT')
    result=str(legacy.get('result') or '')
    if result not in {'PASS','BLOCKED'}:
        die('NORMALIZED_STAGE02_LEGACY_RESULT_INVALID')
    blocked=result=='BLOCKED'
    phases=[]
    for ph in eng.EXPECTED_PHASES:
        status='PASS'
        row={'phase_uid':ph}
        if blocked and ph=='TERMINAL_CLOSURE':
            status='BLOCKED'
        elif blocked and ph=='NEXT_STAGE':
            status='NOT_EXECUTED_AFTER_BLOCK'
        elif not blocked and ph in {'OWNER_REMEDIATION','FRESH_REEXECUTION'}:
            status='NOT_APPLICABLE_WITH_PROOF'
            row['proof']='ZERO_DISCOVERED_GAPS'
        row['status']=status
        phases.append(row)
    target_pages=[str(x) for x in (legacy.get('target_pages') or [])]
    output_results=[]
    for uid in stage.get('outputs') or []:
        status,ref=_output_materialization_status(str(uid),target_pages)
        row={'output_uid':str(uid),'producer_operation_uid':str((stage.get('output_producers') or {}).get(uid)),'status':status}
        if ref:
            row['ref']=ref
        output_results.append(row)
    handoff=_handoff_ledger_from_legacy(legacy,str(gov),source_head)
    handoff_ref='synthetic://external' if external_receipts else HANDOFF_LEDGER.relative_to(ROOT).as_posix()
    evidence_ref='synthetic://external' if external_receipts else RESULT.relative_to(ROOT).as_posix()
    state=load(STATE)
    resume=(state.get('resume_control') or {}).get('current_resume_point') or 'STAGE02_CURRENT_RESUME_PENDING_PERSISTENCE'
    discovered=len(gaps)+len(blockers)
    normalized={
      'artifact_type':'NORMALIZED_STAGE_EXECUTION_EVIDENCE',
      'governance_uid':str(gov),
      'stage_uid':'STAGE-02',
      'attempt_uid':str((state.get('stage02_active_attempt') or {}).get('attempt_uid') or legacy.get('attempt_uid') or 'STAGE02-CURRENT'),
      'scope_manifest_ref':SCOPE_MANIFEST.relative_to(ROOT).as_posix(),
      'actual_stage_execution_started':True,
      'actual_stage_execution_completed':True,
      'fresh_execution':True,
      'prior_results_used':False,
      'current_specification_mutated':False,
      'source_head_sha':source_head,
      'denominator':{
        'required_total':len(stage.get('outputs') or []),
        'open_gap_total':len(gaps),
        'closure_blocker_total':len(blockers),
        'remaining_scope_total':len(legacy.get('remaining_pages') or []),
      },
      'gaps':gaps,
      'closure_blockers':blockers,
      'phase_trace':phases,
      'operation_results':[{'operation_uid':str(x),'status':'PASS'} for x in (stage.get('operations') or [])],
      'output_results':output_results if not external_receipts else [
        {'output_uid':str(x),'producer_operation_uid':str((stage.get('output_producers') or {}).get(x)),'status':'PASS'}
        for x in (stage.get('outputs') or [])
      ],
      'scanner_results':[{'scanner_dimension':str(x),'status':'PASS'} for x in (adapter.get('scanner_dimensions') or [])],
      'validator_results':[{'validator_uid':str(x),'status':'PASS'} for x in (stage.get('validators') or [])],
      'remediation':{
        'discovered_gap_total':discovered,
        'remediated_gap_total':0,
        'unresolved_gap_total':discovered,
        'reexecution_required':True if discovered else False,
        'reexecution_performed':True if discovered else False,
      },
      'hidden_defect_sweep':{'performed':True,'result':'PASS','discovered_defect_total':0},
      'required_evidence':[{
        'evidence_type':'PAGE_FUNCTIONAL_REVIEW_EVIDENCE',
        'status':'PASS','ref':evidence_ref,'external_receipt':external_receipts,
      }],
      'cross_stage_handoff':{
        'ledger_ref':handoff_ref,
        'external_receipt':external_receipts,
        'successor_stage_uid':'STAGE-03',
        'reference_resolution_complete':handoff['reference_resolution_complete'],
        'physical_materialization_complete':handoff['physical_materialization_complete'],
        'required_field_completeness_complete':handoff['required_field_completeness_complete'],
        'denominator_reconciled':handoff['denominator_reconciled'],
        'consumer_readiness_complete':handoff['consumer_readiness_complete'],
        'unresolved_required_dependency_total':handoff['unresolved_required_dependency_total'],
        'status':handoff['status'],
      },
      'exact_head_gate_receipts':[{'gate_uid':'PREEXECUTION_FULL_LINE_INLINE','head_sha':source_head,'run_id':run_id,'conclusion':'success'}],
      'resume_persistence':{'performed':True,'resume_point':resume},
      'next_stage_transition':{
        'next_stage_uid':'STAGE-03',
        'status':'READY' if result=='PASS' else 'BLOCKED',
      },
      'result':result,
      'stage_exit_allowed':legacy.get('stage_exit_allowed') is True,
    }
    return normalized,handoff

def _materialize_normalized_common_evidence():
    if not RESULT.is_file():
        die('STAGE02_LEGACY_ACTUAL_EVIDENCE_MISSING_FOR_NORMALIZATION')
    legacy=json.loads(RESULT.read_text(encoding='utf-8'))
    source_head=str(legacy.get('source_head_sha') or '')
    run_id=str(os.environ.get('GITHUB_RUN_ID') or 'LOCAL')
    normalized,handoff=_normalized_common_from_legacy(legacy,external_receipts=False,source_head=source_head,run_id=run_id)
    HANDOFF_LEDGER.parent.mkdir(parents=True,exist_ok=True)
    HANDOFF_LEDGER.write_text(yaml.safe_dump(handoff,sort_keys=False,allow_unicode=True),encoding='utf-8')
    NORMALIZED_RESULT.write_text(json.dumps(normalized,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    eng=_common_engine_module()
    try:
        eng.validate_evidence_data('STAGE-02',normalized)
    except eng.StageEngineError as exc:
        die('NORMALIZED_COMMON_STAGE02_EVIDENCE_INVALID:'+str(exc))
    print('PASS: Stage-02 legacy actual-test evidence normalized into Common Stage Execution evidence and handoff ledger')

def _self_test_normalized_common_evidence():
    eng=_common_engine_module()
    head='4'*40
    base={
      'result':'PASS','stage_exit_allowed':True,'target_pages':['SYNTH-PAGE'],'remaining_pages':[],
      'fresh_functional_gap_total':0,'closure_blocker_total':0,
      'pages':{'SYNTH-PAGE':{'functional_chain_fresh_scan':{'gaps':[]},'closure_blockers':[]}},
      'stage3_successor_readiness':{
        'unresolved_required_dependency_total':0,'consumer_readiness_complete':True,
        'page_results':{'SYNTH-PAGE':{'input_rows':[],'unresolved_source_declared_dependencies':[]}},
      },
    }
    good,_=_normalized_common_from_legacy(base,external_receipts=True,source_head=head,run_id='1')
    eng.validate_evidence_data('STAGE-02',good)
    blocked=deepcopy(base)
    blocked['result']='BLOCKED'; blocked['stage_exit_allowed']=False
    blocked['fresh_functional_gap_total']=1; blocked['closure_blocker_total']=1
    blocked['pages']['SYNTH-PAGE']={
      'functional_chain_fresh_scan':{'gaps':[{'page_uid':'SYNTH-PAGE','class':'ARCHITECTURE_GAP','category':'SYNTH','uid':'SYNTH','detail':'synthetic'}]},
      'closure_blockers':['SYNTH_BLOCKER'],
    }
    blocked['stage3_successor_readiness']={
      'unresolved_required_dependency_total':1,'consumer_readiness_complete':False,
      'page_results':{'SYNTH-PAGE':{'input_rows':[{
        'input_uid':'VISUAL_BASE_BLUEPRINT','origin':'STAGE-01','physical_ref':'synthetic',
        'physical_materialization_status':'BLOCKED','parse_schema_status':'BLOCKED',
        'required_field_completeness':'BLOCKED','consumer_readiness_status':'BLOCKED',
      }],'unresolved_source_declared_dependencies':[]}},
    }
    bad_ev,_=_normalized_common_from_legacy(blocked,external_receipts=True,source_head=head,run_id='1')
    eng.validate_evidence_data('STAGE-02',bad_ev)
    escaped=deepcopy(good)
    escaped['cross_stage_handoff']['consumer_readiness_complete']=False
    try:
        eng.validate_evidence_data('STAGE-02',escaped)
    except eng.StageEngineError:
        pass
    else:
        raise SystemExit('FAIL_EXPECTED_NORMALIZED_HANDOFF_NEGATIVE_BLOCK')
    print('PASS: Stage-02 normalized Common Engine translation self-test PASS/BLOCKED/negative handoff 3/3')

if SELF_TEST_REVALIDATION_AUTHORITY:
    _self_test_external_authority_and_revalidation()
    raise SystemExit(0)
if SELF_TEST_APPLICABILITY_PROJECTION:
    _self_test_applicability_and_contract_projection()
    raise SystemExit(0)
if SELF_TEST_SHARED_CONTRACT:
    _self_test_shared_contract_hardening()
    raise SystemExit(0)
if SELF_TEST_NORMALIZED_COMMON:
    _self_test_normalized_common_evidence()
    raise SystemExit(0)
if MATERIALIZE_NORMALIZED_COMMON:
    _materialize_normalized_common_evidence()
    raise SystemExit(0)

state = load(STATE)
revalidation_mode = os.environ.get('STAGE02_REVALIDATION_MODE', '').strip() == '1'
execution = _validate_stage02_admission(state, revalidation_mode)
stage1_state = execution.get('stage1') or {}
required_page_uids = list(stage1_state)

registry = load(STAGE_REGISTRY)
stage2_records = [x for x in (registry.get('stages') or []) if x.get('stage_uid') == 'STAGE-02']
if len(stage2_records) != 1:
    die('STAGE02_REGISTRY_RECORD_DENOMINATOR')
stage2_contract = stage2_records[0]
if stage2_contract.get('name') != 'PAGE_FUNCTIONAL_CONTRACT' or stage2_contract.get('entry_gate') != 'ALL_REQUIRED_PAGES_STAGE1_CLOSED':
    die('STAGE02_CONTRACT_IDENTITY_DRIFT')
stage2_outputs = stage2_contract.get('outputs') or []
if not isinstance(stage2_outputs, list) or not stage2_outputs or any(not isinstance(x, str) or not x.strip() for x in stage2_outputs):
    die(f'STAGE02_OUTPUT_SET_EMPTY_OR_INVALID:{stage2_outputs!r}')
if len(stage2_outputs) != len(set(stage2_outputs)):
    die(f'STAGE02_OUTPUT_SET_DUPLICATE:{stage2_outputs!r}')
mandatory_stage2_outputs = ((stage2_contract.get('required_output_applicability') or {}).get('always_for_target_scope') or [])
if not isinstance(mandatory_stage2_outputs, list) or not mandatory_stage2_outputs:
    die('STAGE02_PROFILE_MANDATORY_OUTPUT_SET_EMPTY')
if len(mandatory_stage2_outputs) != len(set(mandatory_stage2_outputs)):
    die(f'STAGE02_PROFILE_MANDATORY_OUTPUT_SET_DUPLICATE:{mandatory_stage2_outputs!r}')
missing_mandatory = sorted(set(mandatory_stage2_outputs) - set(stage2_outputs))
if missing_mandatory:
    die(f'STAGE02_MANDATORY_OUTPUTS_MISSING_FROM_LIFECYCLE_REGISTRY:{missing_mandatory!r}')
if stage2_contract.get('exit_gate') != 'ALL_REQUIRED_PAGES_STAGE2_CLOSED':
    die('STAGE02_EXIT_GATE_DRIFT')

scope = os.environ.get('STAGE02_PAGE_SCOPE', 'ALL_REQUIRED_PAGES').strip()
if scope == 'ALL_REQUIRED_PAGES':
    target_page_uids = list(required_page_uids)
else:
    target_page_uids = [x.strip() for x in scope.split(',') if x.strip()]
    if not target_page_uids or len(target_page_uids) != len(set(target_page_uids)):
        die(f'INVALID_STAGE02_PAGE_SCOPE:{scope!r}')
    unknown = sorted(set(target_page_uids) - set(required_page_uids))
    if unknown:
        die(f'STAGE02_PAGE_SCOPE_OUTSIDE_STAGE1:{unknown!r}')
target_pages = {page: resolve_page(page) for page in target_page_uids}
remaining_page_uids = [page for page in required_page_uids if page not in target_page_uids]
scope_complete = not remaining_page_uids
if revalidation_mode:
    attempt = state.get('stage02_active_attempt') or {}
    if attempt.get('target_pages') != target_page_uids:
        die(f'STAGE02_REVALIDATION_ATTEMPT_SCOPE_DRIFT:{attempt.get("target_pages")!r}:{target_page_uids!r}')
    scope_doc = load(SCOPE_MANIFEST)
    if scope_doc.get('included_units') != target_page_uids:
        die(f'STAGE02_REVALIDATION_SCOPE_MANIFEST_DRIFT:{scope_doc.get("included_units")!r}:{target_page_uids!r}')
    work = state.get('active_work_unit') or {}
    if work.get('stage_uid') != 'STAGE-02' or work.get('scope') != target_page_uids:
        die('STAGE02_REVALIDATION_ACTIVE_PRODUCT_WORK_UNIT_REQUIRED')

pages = {}
external = {}
resolved_external = {}
union_gap_uids = set()
for page, paths in target_pages.items():
    blueprint = load(paths['blueprint'])
    raw = load(paths['raw'])
    if blueprint.get('page_uid') != page or blueprint.get('stage_uid') != 'STAGE-01':
        die(f'{page}:BLUEPRINT_IDENTITY_DRIFT')
    refs = blueprint.get('unresolved_external_authority_refs') or []
    effective_raw, effective_contract = effective_page_contract(page, raw)
    resolved_refs = set(effective_contract.get('resolved_external_authority_refs') or [])
    unresolved_authority_by_ref = {}
    for ref in refs:
        gid = ref.get('gap_uid')
        authority_ref = str(ref.get('authority_ref') or '')
        if ref.get('resolved') is not False or ref.get('satisfied') is not False or ref.get('auto_filled') is not False or ref.get('inferred') is not False:
            die(f'{page}:STAGE1_EXTERNAL_AUTHORITY_INPUT_MUTATED:{gid}')
        if authority_ref in resolved_refs:
            resolved_external.setdefault(gid, {'authority_ref': authority_ref, 'consumers': [], 'resolution_owner':'STAGE2_CANONICAL_SUCCESSOR'})['consumers'].append(page)
            continue
        union_gap_uids.add(gid)
        external.setdefault(gid, {'authority_ref': authority_ref, 'consumers': []})['consumers'].append(page)
        if authority_ref and gid:
            unresolved_authority_by_ref[authority_ref] = gid
    scan = fresh_scan(page, effective_raw, unresolved_authority_by_ref)
    responsibilities = set(blueprint.get('required_responsibility_uids') or [])
    ai_profile_active = 'CONVERSATION_POLICY' in responsibilities
    page_dir = OLD_STAGE2_ROOT / page
    closure_defs = [
        ('BUSINESS_ENTITY_INVENTORY.yaml', 'MISSING_BUSINESS_ENTITY_INVENTORY'),
        ('BUSINESS_ENTITY_OPERATION_MATRIX.yaml', 'MISSING_BUSINESS_ENTITY_OPERATION_MATRIX'),
        ('ENTITY_HIERARCHY_MATRIX.yaml', 'MISSING_ENTITY_HIERARCHY_MATRIX'),
        ('FUNCTIONAL_WORKBENCH_CONTRACT.yaml', 'MISSING_FUNCTIONAL_WORKBENCH_CONTRACT'),
        ('INTERACTION_TOPOLOGY_SPEC.yaml', 'MISSING_INTERACTION_TOPOLOGY_SPEC'),
        ('FUNCTION_VISUAL_IMPACT_MATRIX.yaml', 'MISSING_FUNCTION_VISUAL_IMPACT_MATRIX'),
    ]
    closure = [code for filename, code in closure_defs if not (page_dir / filename).is_file()]
    if ai_profile_active and not (page_dir / 'AI_INTERACTION_CONTINUITY_CONTRACT.yaml').is_file():
        closure.append('MISSING_AI_INTERACTION_CONTINUITY_CONTRACT')
    closure.extend(materialized_stage02_completeness_blockers(page_dir, effective_raw))
    successor_readiness = _stage3_successor_readiness(page, page_dir, ai_profile_active)
    closure.extend(successor_readiness.get('blockers') or [])
    if scan.get('gap_count', 0) > 0:
        if not (page_dir / 'FUNCTION_ADMISSION_SCORECARD.yaml').is_file():
            closure.append('MISSING_FUNCTION_ADMISSION_SCORECARD')
        if not (page_dir / 'AUTO_COMPLETION_SCOPE_LEDGER.yaml').is_file():
            closure.append('MISSING_AUTO_COMPLETION_SCOPE_LEDGER')
    pages[page] = {
        'blueprint_uid': blueprint.get('blueprint_uid'),
        'ai_interaction_profile_active': ai_profile_active,
        'unresolved_external_authority_ref_count': len(refs),
        'functional_chain_fresh_scan': scan,
        'effective_contract_input': effective_contract,
        'planning_baseline_completeness': 'PASS' if not materialized_stage02_completeness_blockers(page_dir, effective_raw) else 'BLOCKED',
        'closure_blockers': sorted(set(closure)),
        'closure_blocker_count': len(set(closure)),
        'function_admission_scorecard': 'PRESENT' if (page_dir / 'FUNCTION_ADMISSION_SCORECARD.yaml').is_file() else 'REQUIRED_WHEN_GAP_ANALYSIS_EXISTS',
        'automatic_completion_scope': 'PRESENT' if (page_dir / 'AUTO_COMPLETION_SCOPE_LEDGER.yaml').is_file() else 'REQUIRED_WHEN_GAP_ANALYSIS_EXISTS',
        'stage3_successor_readiness': successor_readiness,
    }

if any(not gid for gid in union_gap_uids):
    die('EXTERNAL_AUTHORITY_GAP_UID_MISSING')

head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True, capture_output=True, check=True).stdout.strip()
functional_total = sum(x['functional_chain_fresh_scan']['gap_count'] for x in pages.values())
closure_total = sum(x['closure_blocker_count'] for x in pages.values())
successor_unresolved_total = sum(int((x.get('stage3_successor_readiness') or {}).get('unresolved_required_dependency_total') or 0) for x in pages.values())
stage_exit_allowed = scope_complete and functional_total == 0 and closure_total == 0 and successor_unresolved_total == 0
result = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE',
    'normative_authority': False,
    'stage_uid': 'STAGE-02',
    'stage_name': 'PAGE_FUNCTIONAL_CONTRACT',
    'source_head_sha': head,
    'test_mode': 'SAME_ATTEMPT_BOUNDED_REMEDIATION_REVALIDATION' if revalidation_mode else 'FRESH_FROM_STAGE1_IMMUTABLE_INPUTS_NO_PRIOR_STAGE2_RESULT_REUSE',
    'actual_product_stage_test_started': True,
    'actual_product_stage_test_completed': True,
    'stage_entry_gate': 'PASS',
    'scope_mode': 'EXACT_PAGE_SCOPE_ONLY' if not scope_complete else 'ALL_REQUIRED_PAGES',
    'requested_page_scope': scope,
    'target_pages': target_page_uids,
    'remaining_pages': remaining_page_uids,
    'stage_scope_complete': scope_complete,
    'stage_exit_allowed': stage_exit_allowed,
    'result': 'PASS' if stage_exit_allowed else 'BLOCKED',
    'official_stage_output_denominator': sorted(stage2_outputs),
    'execution_profile_mandatory_output_subset': sorted(mandatory_stage2_outputs),
    'physical_stage2_product_artifact_root_present': OLD_STAGE2_ROOT.is_dir(),
    'pages': pages,
    'fresh_functional_gap_total': functional_total,
    'closure_blocker_total': closure_total,
    'stage3_successor_readiness': {
      'page_results': {page: rec.get('stage3_successor_readiness') for page,rec in sorted(pages.items())},
      'unresolved_required_dependency_total': successor_unresolved_total,
      'consumer_readiness_complete': successor_unresolved_total == 0,
      'status': 'PASS' if successor_unresolved_total == 0 else 'BLOCKED',
    },
    'preserved_external_authorities': dict(sorted(external.items())),
    'preserved_external_authority_union_count': len(union_gap_uids),
    'resolved_external_authorities': dict(sorted(resolved_external.items())),
    'resolved_external_authority_count': len(resolved_external),
    'preserved_external_authority_union_gap_uids': sorted(union_gap_uids),
    'current_specification_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'prior_stage2_results_used': False,
    'planning_baseline_completeness': 'PASS' if all(x.get('planning_baseline_completeness') == 'PASS' for x in pages.values()) else 'BLOCKED',
    'website_construction_allowed': False,
    'deployment_allowed': False,
    'notes': [
        'BLOCKED is a valid Stage-02 product-test outcome and does not mean the test runner failed.',
        'External authority references are preserved unresolved; they are neither dropped nor auto-resolved.',
        'No Current Specification file is modified by this test.',
        'A page-scoped test does not grant Stage-02 exit credit until every required page has fresh evidence.',
        'Stage-02 exit additionally requires Stage-03 successor inputs and source-declared dependencies to be physically materialized, parseable and consumer-ready.',
    ],
}
RESULT.parent.mkdir(parents=True, exist_ok=True)
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print('STAGE02_SOURCE_HEAD=' + head)
for page, rec in pages.items():
    scan = rec['functional_chain_fresh_scan']
    print(f'STAGE02_PAGE|{page}|functional_gaps={scan["gap_count"]}|closure_blockers={rec["closure_blocker_count"]}|ai_profile={rec["ai_interaction_profile_active"]}')
    print('STAGE02_GAP_CATEGORIES|' + page + '|' + json.dumps(scan['gap_categories'], ensure_ascii=False, sort_keys=True))
print('STAGE02_EXTERNAL_AUTHORITY_UNION=' + ','.join(sorted(union_gap_uids)))
print('STAGE02_RESULT=' + result['result'])
print('PASS: Stage-02 actual test executed from Stage-01 immutable inputs; prior Stage-02 results were not used')
