#!/usr/bin/env python3
"""Validate STAGE_EXECUTION_MASTER_PLAN.yaml — definition-time, fail-closed.

Implements the C2-C7 checks from the stage-execution-master-plan design:
  C-A  intra-stage reference closure (conditional members, producers)
  C-B  gate chain (entry base == predecessor exit)
  C-C  order chain (next_stage_uid)
  C-D  input source resolvability (earlier-stage producer or external origin)
  C-E  required evidence has a declared producing operation
  C-F  required normative sections resolve in SECTION_NUMBER_REGISTRY
  C-G  invariant orphans are bound
  C-H  production readiness (deliverable + exit gate per stage)
  C-I  projection: plan is a superset of lifecycle registry (no dropped authority)
Read-only. No product mutation.
"""
from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_ORIGINS = {'RAW_SOURCE_SET', 'CURRENT_AUTHORITY_SET'}


def load(root, rel):
    return yaml.safe_load((root / rel).read_text(encoding='utf-8')) or {}


def _gate_base(gate):
    if isinstance(gate, dict):
        return gate.get('base')
    if isinstance(gate, str) and gate.endswith('_AND_PREDECESSOR_STAGE_CLOSED'):
        return gate[:-len('_AND_PREDECESSOR_STAGE_CLOSED')]
    return gate


def validate(root=ROOT):
    failures = []
    plan = load(root, '10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml')
    if plan.get('artifact_type') != 'STAGE_EXECUTION_MASTER_PLAN':
        failures.append('master_plan_artifact_type_invalid')
    if not plan.get('stages'):
        return {'status': 'FAIL', 'failures': failures + ['master_plan_stages_missing']}

    sections = load(root, '10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml')
    sec_uids = {s['section_uid'] for d in sections.get('documents', []) for s in d.get('sections', [])}
    authoritative_stages = {s['stage_uid']: s for s in plan.get('stages', [])}

    order = [s['stage_uid'] for s in plan['stages']]
    stages = {s['stage_uid']: (s.get('projection') or {}) for s in plan['stages']}

    # C-A intra-stage reference closure
    for sid in order:
        s = stages[sid]
        for field, key in (('operations', 'operation_uid'), ('outputs', 'output_uid'), ('required_evidence', 'evidence_uid')):
            uids = [m[key] for m in s.get(field) or []]
            dups = sorted({u for u in uids if uids.count(u) > 1})
            if dups:
                failures.append(f'MASTER_PLAN_DUPLICATE_MEMBER:{sid}:{field}:{dups}')
        ops = {o['operation_uid'] for o in s['operations']}
        outs = {o['output_uid'] for o in s['outputs']}
        for o in s['operations']:
            for po in o.get('producer_outputs') or []:
                if po not in outs:
                    failures.append(f'MASTER_PLAN_DANGLING_REF:{sid}:operation_producer_output:{po}')
        for o in s['outputs']:
            p = o.get('producer_operation_uid')
            if not p:
                failures.append(f'MASTER_PLAN_FIELD_MISSING:{sid}:output_producer:{o["output_uid"]}')
            elif p not in ops:
                failures.append(f'MASTER_PLAN_DANGLING_REF:{sid}:output_producer:{p}')
            if o.get('classification') not in {'HANDOFF', 'INTERNAL'}:
                failures.append(f'MASTER_PLAN_CLASSIFICATION_INVALID:{sid}:{o["output_uid"]}')

    # C-B gate chain + C-C order chain
    for i in range(1, len(order)):
        prev, cur = stages[order[i-1]], stages[order[i]]
        if _gate_base(prev.get('exit_gate')) != _gate_base(cur.get('entry_gate')):
            failures.append(f'MASTER_PLAN_CONTINUITY_BREAK:{order[i]}:entry_gate_vs_{order[i-1]}_exit_gate')
        if prev.get('next_stage_uid') != cur.get('stage_uid'):
            failures.append(f'MASTER_PLAN_CONTINUITY_BREAK:{order[i-1]}:next_stage_uid')

    # C-D input source resolvability
    produced_by = {o['output_uid']: sid for sid in order for o in stages[sid]['outputs']}
    for i, sid in enumerate(order):
        for inp in stages[sid].get('inputs') or []:
            uid = inp.get('input_uid')
            if uid in EXTERNAL_ORIGINS and sid == 'STAGE-01':
                continue
            origin = inp.get('origin_stage_uid')
            if not origin:
                failures.append(f'MASTER_PLAN_DANGLING_REF:{sid}:input_origin:{uid}')
                continue
            if origin not in stages:
                failures.append(f'MASTER_PLAN_DANGLING_REF:{sid}:input_origin_stage:{origin}')
                continue
            if order.index(origin) >= i:
                failures.append(f'MASTER_PLAN_CONTINUITY_BREAK:{sid}:input_origin_not_earlier:{uid}')
            if uid not in produced_by:
                failures.append(f'MASTER_PLAN_DANGLING_REF:{sid}:input_unproduced:{uid}')

    # C-E evidence producer
    for sid in order:
        ops = {o['operation_uid'] for o in stages[sid]['operations']}
        for e in stages[sid].get('required_evidence') or []:
            p = e.get('producer_operation_uid')
            if not p:
                failures.append(f'MASTER_PLAN_FIELD_MISSING:{sid}:evidence_producer:{e.get("evidence_uid")}')
            elif p not in ops:
                failures.append(f'MASTER_PLAN_DANGLING_REF:{sid}:evidence_producer:{p}')

    # C-F section resolution
    for sid in order:
        for uid in stages[sid].get('required_normative_sections') or []:
            if uid not in sec_uids:
                failures.append(f'MASTER_PLAN_SECTION_UNRESOLVED:{uid}')

    # C-G orphan invariant binding
    binding = plan.get('orphan_invariant_binding') or {}
    for k, v in binding.items():
        if not v:
            failures.append(f'MASTER_PLAN_FIELD_MISSING:orphan_invariant_binding:{k}')
    if 'SINGLE_STATE_SINGLE_ORCHESTRATOR_STAGE_CORE' not in binding:
        failures.append('MASTER_PLAN_FIELD_MISSING:orphan_invariant_binding:SINGLE_STATE_SINGLE_ORCHESTRATOR_STAGE_CORE')

    # C-H production readiness
    for sid in order:
        s = stages[sid]
        if not s.get('outputs'):
            failures.append(f'PRODUCTION_READINESS_INCOMPLETE:{sid}:no_outputs')
        if not s.get('exit_gate'):
            failures.append(f'PRODUCTION_READINESS_INCOMPLETE:{sid}:no_exit_gate')
        pr = s.get('production_readiness') or {}
        if not pr.get('required_sections'):
            failures.append(f'PRODUCTION_READINESS_INCOMPLETE:{sid}:no_required_sections')

    # C-I projection superset: nothing in the authoritative top-level may be absent from the projection
    for sid, ls in authoritative_stages.items():
        ps = stages.get(sid)
        if not ps:
            failures.append(f'MASTER_PLAN_PROJECTION_DRIFT:{sid}:stage_missing')
            continue
        plan_ops = {o['operation_uid'] for o in ps['operations']}
        plan_outs = {o['output_uid'] for o in ps['outputs']}
        plan_evid = {e['evidence_uid'] for e in ps['required_evidence']}
        plan_secs = set(ps.get('required_normative_sections') or [])
        for o in ls.get('operations') or []:
            if o not in plan_ops:
                failures.append(f'MASTER_PLAN_PROJECTION_DRIFT:{sid}:registry_operation_missing:{o}')
        for o in ls.get('outputs') or []:
            if o not in plan_outs:
                failures.append(f'MASTER_PLAN_PROJECTION_DRIFT:{sid}:registry_output_missing:{o}')
        for e in ls.get('required_evidence') or []:
            if e not in plan_evid:
                failures.append(f'MASTER_PLAN_PROJECTION_DRIFT:{sid}:registry_evidence_missing:{e}')
        for sec in ls.get('required_normative_section_uids') or []:
            if sec not in plan_secs:
                failures.append(f'MASTER_PLAN_PROJECTION_DRIFT:{sid}:registry_section_missing:{sec}')

    return {
        'status': 'PASS' if not failures else 'FAIL',
        'stage_count': len(order),
        'failures': failures,
    }


if __name__ == '__main__':
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
