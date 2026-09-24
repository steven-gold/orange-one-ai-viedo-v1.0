#!/usr/bin/env python3
from pathlib import Path
import json
import yaml

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/'10_REGISTRY'

def load(name):
    p=REG/name
    obj=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(obj,dict):
        raise SystemExit('MAPPING_REQUIRED:'+name)
    return obj

def validate():
    failures=[]
    inv=load('STAGE_EXECUTION_INVARIANT_REGISTRY.yaml').get('invariants') or {}
    idx=inv.get('INDEXED_INCREMENTAL_VALIDATION') or {}
    if idx.get('impact_and_reverse_dependency_index_loading_required') is not True:
        failures.append('impact_reverse_dependency_index_loading_not_required')
    if idx.get('validation_impact_index_required') is not True:
        failures.append('validation_impact_index_not_required')
    if idx.get('reverse_dependency_index_required') is not True:
        failures.append('reverse_dependency_index_not_required')
    if idx.get('changed_artifact_must_invalidate_affected_cache_and_reverse_dependencies') is not True:
        failures.append('changed_artifact_cache_invalidation_missing')
    if idx.get('index_may_skip_required_impacted_validator') is not False:
        failures.append('impacted_validator_skip_not_blocked')
    if idx.get('index_drift_full_sweep_required_before_freeze') is not True:
        failures.append('index_drift_full_sweep_not_required')
    if idx.get('index_and_full_sweep_result_divergence')!='BLOCK':
        failures.append('index_full_sweep_divergence_not_blocked')
    if idx.get('mutation_case_copy_mode')!='COPY_ON_WRITE_OR_IN_MEMORY_OVERLAY_PREFERRED':
        failures.append('mutation_copy_mode_invalid')

    bp=load('GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    c=bp.get('product_neutral_entity_lifecycle_contract') or {}
    if c.get('indexed_incremental_validation_required') is not True:
        failures.append('acceptance_indexed_validation_missing')
    if c.get('index_may_skip_impacted_validator') is not False:
        failures.append('acceptance_impacted_validator_skip_not_blocked')
    if c.get('index_drift_full_sweep_required_before_freeze') is not True:
        failures.append('acceptance_full_sweep_before_freeze_missing')

    life=load('GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    cs=(life.get('cross_stage_invariants') or {}).get('stage_execution_invariant_hardening') or {}
    if cs.get('indexed_incremental_validation_required') is not True:
        failures.append('lifecycle_indexed_validation_missing')
    if cs.get('index_may_skip_impacted_validator') is not False:
        failures.append('lifecycle_impacted_validator_skip_not_blocked')

    return {
        'artifact_type':'VALIDATOR_RESULT',
        'validator_uid':'VAL-GOV-003',
        'validator_name':'INDEXED_INCREMENTAL_VALIDATION_GUARD',
        'status':'PASS' if not failures else 'FAIL',
        'failures':failures,
    }

if __name__=='__main__':
    out=validate()
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if out['status']=='PASS' else 1)
