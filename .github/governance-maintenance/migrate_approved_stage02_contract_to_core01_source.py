#!/usr/bin/env python3
from pathlib import Path
import copy, yaml

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'00_SOURCE_INTAKE/fresh_run_005/00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'
SPEC=ROOT/'00_SOURCE_INTAKE/fresh_run_005/04_PAGE_FUNCTIONAL_CONTRACT/CORE-01/FUNCTIONAL_CHAIN_SPEC.yaml'
AUTH=ROOT/'governance/test/spec_change_authorizations/USR-DIRECTIVE-20260919-CORE01-STAGE02-COMPLETENESS-R3.yaml'

def load(p):
    x=yaml.safe_load(p.read_text(encoding='utf-8'))
    if not isinstance(x,dict): raise RuntimeError('MAPPING_REQUIRED:'+str(p))
    return x

def main():
    raw=load(RAW); spec=load(SPEC); auth=load(AUTH)
    if auth.get('status')!='APPROVED_FOR_EXACT_SCOPE':
        raise RuntimeError('AUTHORIZATION_INVALID')
    meta=spec.get('design_contract_remediation') or {}
    if meta.get('canonical_owner_materialization') is not True:
        raise RuntimeError('PREDECESSOR_SUCCESSOR_NOT_CANONICAL_MATERIALIZATION')
    if meta.get('candidate_bytes_became_authority_directly') is not False:
        raise RuntimeError('CANDIDATE_BYTES_NOT_ALLOWED')
    if meta.get('raw_source_mutated') is not False:
        raise RuntimeError('PREDECESSOR_RAW_MUTATION_FLAG_INVALID')
    approval=str(meta.get('approval_evidence_ref') or '')
    if not approval or not (ROOT/approval).is_file():
        raise RuntimeError('APPROVAL_EVIDENCE_MISSING')
    projection=spec.get('source_projection') or {}
    required=('actions','stages','stage_transitions','events','integration_ports')
    if any(not isinstance(projection.get(k),list) for k in required):
        raise RuntimeError('APPROVED_SOURCE_PROJECTION_INCOMPLETE')
    reg=raw.setdefault('registries',{})
    if not isinstance(reg,dict): raise RuntimeError('RAW_REGISTRY_INVALID')
    # Preserve current controls because the 2026-09-11 baseline corrected Field != Action bindings.
    for k in required:
        reg[k]=copy.deepcopy(projection[k])
    raw['stage02_approved_successor_source_migration']={
        'authority_source':'USR-DIRECTIVE-20260919-CORE01-STAGE02-COMPLETENESS-R3',
        'source_canonical_owner_ref':SPEC.relative_to(ROOT).as_posix(),
        'approval_evidence_ref':approval,
        'migrated_projection_keys':list(required),
        'controls_preserved_from_2026_09_11_planning_baseline':True,
        'prior_generated_artifact_reused_as_fresh_output':False,
        'purpose':'Make approved payload/state-transition/audit contracts reproducible from source after destructive Stage-01/02 reset.',
    }
    RAW.write_text(yaml.safe_dump(raw,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
    print('PASS: approved Stage-02 canonical successor contracts migrated into CORE-01 source authority')
    print('PASS: current 2026-09-11 field/control/workbench completeness corrections preserved')

if __name__=='__main__':
    main()
