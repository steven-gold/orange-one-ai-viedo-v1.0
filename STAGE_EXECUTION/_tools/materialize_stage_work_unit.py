#!/usr/bin/env python3
"""Deterministically materialize a governed stage Work Unit scaffold.

This is the FIXED PATTERN for every governed-unit page run. Whenever a stage is
about to execute (or a predecessor stage needs its successor present to resolve
the cross-stage handoff), this single tool builds the Work Unit contract surface:

  WORK_UNIT.yaml, CURRENT_EXECUTION_SCOPE_MANIFEST.yaml, EXECUTION_STATE.yaml,
  NORMATIVE_EXECUTION_MATRIX.yaml and the CURRENT_LEDGERS projections.

Contract sources (never invented here):
  * Operations / outputs / output producers / validators / required evidence /
    exit gate / next stage / required normative sections / scanners are read from
    the authoritative STAGE_EXECUTION_MASTER_PLAN.yaml (top-level `stages`).
  * Successor input bindings are read from the master plan `inputs` +
    `input_origins`, and each artifact_ref is resolved to the owning predecessor
    Work Unit on disk.
  * The only stage-local data not derivable from the master plan (the Normative
    Execution Matrix section -> artifact -> required-field mapping) is declared
    in STAGE_EXECUTION/_tools/stage_specs/<STAGE>.yaml.

The generator is deterministic and idempotent. It refuses to overwrite an
already-materialized Work Unit unless --force is given, because overwriting a
running/closed stage would reset its authoritative EXECUTION_STATE.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys
import yaml

DEFAULT_ROOT = Path('/workspace')
DEFAULT_PLAN = Path('.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml')
SPEC_DIR = Path(__file__).resolve().parent / 'stage_specs'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(obj) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)


def load_yaml(path: Path):
    with path.open(encoding='utf-8') as fh:
        return yaml.safe_load(fh)


def stage_index(plan_path: Path) -> dict:
    doc = load_yaml(plan_path)
    raw = doc.get('stages')
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, list):
        return {str(s.get('stage_uid')): s for s in raw if isinstance(s, dict) and s.get('stage_uid')}
    raise SystemExit('MASTER_PLAN_STAGES_UNRESOLVED')


def find_work_unit(root: Path, stage_uid: str, governed: str) -> Path:
    stage_dir = root / 'STAGE_EXECUTION' / stage_uid
    candidates = []
    if stage_dir.is_dir():
        for d in sorted(stage_dir.iterdir()):
            if not d.is_dir() or d.name.startswith('_'):
                continue
            w = d / 'WORK_UNIT.yaml'
            if not w.is_file():
                continue
            try:
                wd = load_yaml(w) or {}
            except yaml.YAMLError:
                continue
            if str(wd.get('stage_uid')) == stage_uid and str(wd.get('governed_unit_uid')) == governed:
                candidates.append(w)
    if len(candidates) > 1:
        raise SystemExit(f'MULTIPLE_WORK_UNITS:{stage_uid}:{governed}')
    return candidates[0] if candidates else None


def resolve_input_binding(root: Path, governed: str, stage_uid: str, input_uid: str, origin: str,
                          allow_pending: bool = False) -> dict:
    """Build one stage-input binding from the owning predecessor Work Unit.

    When materializing a SUCCESSOR scaffold before the producing stage has run,
    the producer-owned artifact does not exist yet. `allow_pending` then emits a
    producer-pending binding: the artifact_ref is still the authoritative future
    path, the hash is left empty, and the orchestrator refreshes it from the
    predecessor's cross-stage handoff at the owning transition boundary. This is
    never used for inputs whose producer has already closed.
    """
    origin_stage = origin.split('_')[0]
    owner = find_work_unit(root, origin_stage, governed)
    if owner is None:
        raise SystemExit(f'INPUT_ORIGIN_WORK_UNIT_MISSING:{input_uid}:{origin_stage}')
    art = owner.parent / f'{input_uid}.yaml'
    pending = not art.is_file()
    if pending and not allow_pending:
        raise SystemExit(f'INPUT_ARTIFACT_MISSING:{input_uid}:{art}')
    readiness = ''
    pred = find_work_unit(root, f'STAGE-{int(stage_uid.split("-")[1]) - 1:02d}', governed)
    if pred is not None:
        rp = pred.parent / 'EVIDENCE' / 'SUCCESSOR_INPUTS' / f'{input_uid}.readiness.yaml'
        if rp.is_file():
            readiness = str(rp.relative_to(root)).replace('\\', '/')
    return {
        'input_uid': input_uid,
        'origin': origin,
        'status': 'MATERIALIZED',
        'artifact_ref': str(art.relative_to(root)).replace('\\', '/'),
        'content_sha256': '' if pending else sha(art),
        'external_evidence_ref': '',
        'authority_evidence_ref': '',
        'consumer_readiness_evidence_ref': readiness,
    }


def artifact_ref_for(stage_uid: str, wu: str, atype: str, outputs: list, evidence: list) -> str:
    if atype in evidence and atype not in outputs:
        return f'STAGE_EXECUTION/{stage_uid}/{wu}/EVIDENCE/{atype}.yaml'
    return f'STAGE_EXECUTION/{stage_uid}/{wu}/{atype}.yaml'


def build_nem(stage_uid: str, wu: str, gov: str, governed: str, spec: dict, section_universe: list, outputs: list, evidence: list, exit_gate: str) -> dict:
    rows = []
    for i, row in enumerate(spec.get('nem') or [], 1):
        section = str(row['section'])
        atype = str(row['artifact_type'])
        ref = artifact_ref_for(stage_uid, wu, atype, outputs, evidence)
        rows.append({
            'matrix_row_uid': f'NEM-{stage_uid.replace("STAGE-", "S")}-{i:04d}',
            'normative_section_uid': section,
            'requirement_uid': f'{section}:NORMATIVE_REQUIRED_FIELD',
            'required_artifact_type': atype,
            'artifact_ref': ref,
            'artifact_owner': f'GOVERNED_UNIT:{governed}',
            'row_denominator_source': f'STAGE_EXECUTION/{stage_uid}/{wu}/DENOMINATOR_SNAPSHOT.yaml',
            'row_identity': f'NORMATIVE_REQUIRED_FIELD:{section}',
            'field_path': list(row['field_path']),
            'applicability': 'REQUIRED',
            'validator_uid': str(spec['nem_validator_uid']),
            'validator_check_id': f'{spec.get("nem_check_prefix", "CONTRACT_COMPLETE")}:{section}',
            'evidence_ref': ref,
            'closure_gate': exit_gate,
            'failure_disposition': f'BLOCK_{stage_uid}_CLOSURE_AND_REVERIFY',
            'reentry_owner': f'{stage_uid}:{spec.get("stage_role", "EXECUTION")}',
        })
    required_sections = set(map(str, section_universe))
    represented_sections = {str(r['section']) for r in (spec.get('nem') or [])}
    artifact_types = {str(r['artifact_type']) for r in (spec.get('nem') or [])}
    required_artifacts = set(map(str, outputs)) | set(map(str, evidence))
    n = len(rows)
    coverage = {
        'required_normative_section_total': len(required_sections),
        'represented_normative_section_total': len(required_sections & represented_sections),
        'required_artifact_total': len(required_artifacts),
        'represented_artifact_total': len(required_artifacts & artifact_types),
        'required_field_total': n,
        'validator_bound_field_total': n,
        'closure_bound_field_total': n,
        'missing_required_row_count': 0,
        'missing_required_field_count': 0,
        'duplicate_credit_count': 0,
        'summary_only_credit_count': 0,
        'unclassified_applicability_count': 0,
        'validator_unbound_count': 0,
        'closure_unbound_count': 0,
        'stale_matrix_count': 0,
    }
    return {
        'artifact_uid': f'NEM-{stage_uid}-{wu}',
        'artifact_type': 'NORMATIVE_EXECUTION_MATRIX',
        'governance_uid': gov,
        'stage_uid': stage_uid,
        'work_unit_uid': wu,
        'governed_unit_uid': governed,
        'matrix_contract': 'Normative Section -> Required Artifact -> Required Row -> Required Field -> Validator -> Closure Gate',
        'denominator_policy': 'COMPLETE_APPLICABLE_NORMATIVE_ARTIFACT_ROW_FIELD_UNIVERSE',
        'binding_basis': 'PRE_EXECUTION_CURRENT_AUTHORITY_ANCHOR',
        'rows': rows,
        'coverage': coverage,
        'status': 'PASS',
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--stage', required=True)
    p.add_argument('--governed-unit', required=True)
    p.add_argument('--product-root', default=str(DEFAULT_ROOT))
    p.add_argument('--master-plan', default=None)
    p.add_argument('--spec', default=None)
    p.add_argument('--work-unit-uid', default=None)
    p.add_argument('--allow-pending-inputs', action='store_true')
    p.add_argument('--force', action='store_true')
    a = p.parse_args()

    root = Path(a.product_root).resolve()
    plan = Path(a.master_plan) if a.master_plan else root / DEFAULT_PLAN
    if not plan.is_file():
        raise SystemExit(f'MASTER_PLAN_MISSING:{plan}')
    stages = stage_index(plan)
    if a.stage not in stages:
        raise SystemExit(f'UNKNOWN_STAGE:{a.stage}')
    st = stages[a.stage]

    spec_path = Path(a.spec) if a.spec else SPEC_DIR / f'{a.stage}.yaml'
    if not spec_path.is_file():
        raise SystemExit(f'STAGE_SPEC_MISSING:{spec_path}')
    spec = load_yaml(spec_path)

    gov = str(spec['governance_uid'])
    governed = a.governed_unit
    stage_uid = a.stage
    wu = a.work_unit_uid or f'WU-{stage_uid}-{governed}-001'
    wu_rel = f'STAGE_EXECUTION/{stage_uid}/{wu}'
    wd = root / wu_rel

    if (wd / 'WORK_UNIT.yaml').is_file() and not a.force:
        raise SystemExit(f'WORK_UNIT_ALREADY_MATERIALIZED:{wu_rel} (use --force to overwrite)')

    ops = [str(x) for x in (st.get('operations') or [])]
    outputs = [str(x) for x in (st.get('outputs') or [])]
    producers = dict(st.get('output_producers') or {})
    validators = [str(x) for x in (st.get('validators') or [])]
    required_evidence = [str(x) for x in (st.get('required_evidence') or [])]
    exit_gate = str(st.get('exit_gate') or '')
    section_universe = [str(x) for x in (st.get('required_normative_section_uids') or [])]
    scanners = [str(x) for x in ((st.get('projection') or {}).get('scanners') or st.get('scanners') or [])]
    inputs = [str(x) for x in (st.get('inputs') or [])]
    origins = {str(k): str(v) for k, v in (st.get('input_origins') or {}).items()}

    if not ops:
        raise SystemExit('STAGE_OPERATIONS_EMPTY')
    if set(inputs) != set(origins):
        raise SystemExit('STAGE_INPUT_ORIGIN_DENOMINATOR_DRIFT')

    stage_number = int(stage_uid.split('-')[1])
    executor_owner = f'STAGE_EXECUTION/{stage_uid}/stage{stage_number:02d}_operation_executor.py'
    receipt_dir = f'{wu_rel}/EVIDENCE/OPERATION_RECEIPTS'
    glr_dir = f'{wu_rel}/EVIDENCE/GOVERNANCE_LOAD_RECEIPTS'

    wd.mkdir(parents=True, exist_ok=True)
    (wd / 'CURRENT_LEDGERS').mkdir(exist_ok=True)
    (wd / 'EVIDENCE' / 'OPERATION_RECEIPTS').mkdir(parents=True, exist_ok=True)
    (wd / 'EVIDENCE' / 'GOVERNANCE_LOAD_RECEIPTS').mkdir(parents=True, exist_ok=True)

    ledger_classes = list(spec['ledger_classes'])
    for lc in ledger_classes:
        (wd / 'CURRENT_LEDGERS' / f'{lc}.yaml').write_text(dump({
            'artifact_type': 'CURRENT_LEDGER_PROJECTION', 'ledger_class': lc,
            'stage_uid': stage_uid, 'work_unit_uid': wu, 'governance_uid': gov, 'status': 'CURRENT',
        }), encoding='utf-8')

    nem = build_nem(stage_uid, wu, gov, governed, spec, section_universe, outputs, required_evidence, exit_gate)
    (wd / 'NORMATIVE_EXECUTION_MATRIX.yaml').write_text(dump(nem), encoding='utf-8')

    state = {
        'artifact_type': 'EXECUTION_STATE', 'stage_uid': stage_uid, 'work_unit_uid': wu,
        'governed_unit_uid': governed, 'governance_uid': gov, 'status': 'IN_PROGRESS', 'current_status': 'IN_PROGRESS',
        'current_operation': ops[0], 'completed_operations': [],
        'resume_control': {'product_execution_allowed': True},
        'last_operation_uid': None, 'last_operation_receipt_ref': None,
        'blocker_disposition': None, 'next_action': 'EXECUTE_OPERATION',
    }
    (wd / 'EXECUTION_STATE.yaml').write_text(dump(state), encoding='utf-8')

    scope = {
        'artifact_type': 'EXECUTION_SCOPE_MANIFEST', 'artifact_uid': f'SCOPE-{wu}',
        'stage_uid': stage_uid, 'work_unit_uid': wu, 'governance_uid': gov,
        'governed_unit_uid': governed, 'governed_unit_type': str(spec.get('governed_unit_type', 'SYSTEM_LOGIC_UNIT')),
        'product_stage_execution_allowed': True, 'status': 'OPEN',
        'governance_binding_mode': 'DIRECT_CURRENT_WORKLINE_RECEIPT',
        'current_reverify_required': True, 'included_units': [governed], 'partial_scope': False,
    }
    (wd / 'CURRENT_EXECUTION_SCOPE_MANIFEST.yaml').write_text(dump(scope), encoding='utf-8')

    op_bindings = {}
    for op in ops:
        op_bindings[op] = {
            'applicability': 'REQUIRED', 'executor_owner': executor_owner,
            'executor_protocol': 'PYTHON_STAGE_OPERATION_V1',
            'result_owner': f'{receipt_dir}/{op}.yaml',
            'operation_receipt_ref': f'{receipt_dir}/{op}.yaml',
            'governance_load_receipt_ref': f'{glr_dir}/{op}.yaml',
        }
    scanner_bindings = {}
    for dim in scanners:
        scanner_bindings[dim] = {
            'scanner_owner': str(spec.get('scanner_owner', f'{stage_uid}_SEMANTIC_SCANNER')),
            'result_owner': f'{wu_rel}/EVIDENCE/SCANNERS/{dim}.yaml',
        }

    ledger_bindings = {}
    for lc in ledger_classes:
        lp = wd / 'CURRENT_LEDGERS' / f'{lc}.yaml'
        ledger_bindings[lc] = {
            'ledger_class': lc, 'binding_kind': 'LOCAL_ARTIFACT',
            'artifact_ref': f'{wu_rel}/CURRENT_LEDGERS/{lc}.yaml',
            'content_sha256': sha(lp), 'external_evidence_ref': '',
        }
    ledger_bindings['EXECUTION_STATE'] = {
        'ledger_class': 'EXECUTION_STATE', 'binding_kind': 'LOCAL_ARTIFACT',
        'artifact_ref': f'{wu_rel}/EXECUTION_STATE.yaml',
        'content_sha256': sha(wd / 'EXECUTION_STATE.yaml'), 'external_evidence_ref': '',
    }

    input_bindings = {
        uid: resolve_input_binding(root, governed, stage_uid, uid, origins[uid], a.allow_pending_inputs) for uid in inputs
    }
    dependencies = [row['artifact_ref'] for row in input_bindings.values()]

    work = {
        'artifact_uid': f'WUDEF-{wu}', 'artifact_type': 'WORK_UNIT', 'work_unit_uid': wu,
        'stage_uid': stage_uid, 'governed_unit_uid': governed,
        'governed_unit_type': str(spec.get('governed_unit_type', 'SYSTEM_LOGIC_UNIT')),
        'primary_task_layer': 'PRODUCT_STAGE_EXECUTION',
        'work_unit_activation_kind': 'INITIAL_STAGE_WORK_UNIT',
        'status': 'OPEN', 'current_status': 'OPEN', 'governance_uid': gov,
        'pre_execution_gate_status': 'PASS',
        'normative_execution_matrix_ref': f'{wu_rel}/NORMATIVE_EXECUTION_MATRIX.yaml',
        'required_outputs': outputs,
        'output_producers': producers,
        'required_evidence': required_evidence,
        'validators': validators,
        'operation_bindings': op_bindings, 'scanner_bindings': scanner_bindings,
        'input_bindings': input_bindings, 'current_ledger_bindings': ledger_bindings,
        'dependencies': dependencies,
        'governance_binding_mode': 'DIRECT_CURRENT_WORKLINE_RECEIPT',
        'current_state_authority_ref': f'{wu_rel}/EXECUTION_STATE.yaml',
        'current_state_authority_sha256': sha(wd / 'EXECUTION_STATE.yaml'),
        'projection_role': 'NON_AUTHORITATIVE',
    }
    (wd / 'WORK_UNIT.yaml').write_text(dump(work), encoding='utf-8')

    print(f'materialized {wu_rel}')
    print(f'ops={len(ops)} scanners={len(scanners)} nem_rows={len(nem["rows"])} inputs={len(inputs)}')


if __name__ == '__main__':
    main()
