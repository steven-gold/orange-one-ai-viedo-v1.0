#!/usr/bin/env python3
from pathlib import Path
import yaml
root=Path('.')
run=root/'00_SOURCE_INTAKE/fresh_run_003'
contract=yaml.safe_load((root/'governance/current/v2.1.7/STAGE1_PHASE_AUTHORITY_CONTRACT.yaml').read_text())
state=yaml.safe_load((run/'EXECUTION_STATE.yaml').read_text())
expected=set(contract['unresolved_external_authority']['expected_current_replay_refs'])
def die(msg): raise SystemExit(msg)
if state.get('source_segment_mapping_completed') is not True: die('segment mapping must be closed')
sf_started=state.get('source_fact_materialization_started') is True
sf_done=state.get('source_fact_materialization_completed') is True
if sf_started and state.get('source_segment_mapping_completed') is not True: die('source fact started before segment mapping close')
if sf_done and not sf_started: die('source fact completed without start')
for key in ('website_construction_started','deployment_started'):
    if state.get(key) is True: die('Stage-1 forbidden phase started: '+key)
if not sf_done:
    for key in ('domain_decomposition_started','responsibility_classification_started','blueprint_materialization_started'):
        if state.get(key) is True: die('downstream phase started before source fact close: '+key)
    if not sf_started:
        for fn in ('SOURCE_CONTEXT_MANIFEST.yaml','CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml','SOURCE_DEPENDENCY_MAP.yaml'):
            if (run/'00_SOURCE_INTAKE'/fn).exists(): die('source fact artifact exists before explicit source fact start: '+fn)
else:
    dep=yaml.safe_load((run/'00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml').read_text())
    if dep.get('invented_dependency_count')!=0: die('invented dependency count nonzero')
    gaps=dep.get('unresolved_authority_gaps') or []
    if len(gaps)!=8: die('unresolved authority gap count drift: '+str(len(gaps)))
    refs={g.get('authority_ref') for g in gaps}
    if refs!=expected: die('unresolved authority reference identity drift')
    if len({g.get('gap_uid') for g in gaps})!=8: die('unresolved authority gap uid duplicate/drift')
    for g in gaps:
        if g.get('disposition')!='UNRESOLVED_AUTHORITY_GAP': die('false authority resolution: '+str(g.get('gap_uid')))
        if not g.get('consumer_source_uids') or not g.get('authority_evidence_ref'): die('unresolved authority identity/evidence incomplete: '+str(g.get('gap_uid')))
        if g.get('resolved') is True or g.get('satisfied') is True or g.get('auto_filled') is True or g.get('inferred') is True or g.get('substitute_authority_ref'): die('synthetic authority resolution: '+str(g.get('gap_uid')))
    if state.get('unresolved_authority_gap_count') not in (None,8): die('execution state unresolved gap count drift')
print('PASS: v2.1.7 phase boundary legal; Source Fact successor does not invalidate Segment Mapping; unresolved external Authority refs preserved exactly when Source Facts are materialized')
