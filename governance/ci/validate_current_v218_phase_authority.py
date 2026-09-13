#!/usr/bin/env python3
from pathlib import Path
import yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'; contract=yaml.safe_load((root/'governance/current/v2.1.8/STAGE1_SUCCESSOR_EVIDENCE_SYNC_CONTRACT.yaml').read_text()); state=yaml.safe_load((run/'EXECUTION_STATE.yaml').read_text())
def die(m): raise SystemExit(m)
ci=state.get('github_ci') or {}; expected=set(contract['unresolved_external_authority']['expected_current_replay_refs'])
segment=state.get('source_segment_mapping_completed') is True; sf_start=state.get('source_fact_materialization_started') is True; sf_done=state.get('source_fact_materialization_completed') is True
cls_start=state.get('responsibility_classification_started') is True; cls_done=state.get('responsibility_classification_completed') is True
page_start=state.get('page_base_blueprint_started') is True; page_done=state.get('page_base_blueprint_completed') is True
visual_start=state.get('visual_base_blueprint_started') is True; visual_done=state.get('visual_base_blueprint_completed') is True
bind_start=state.get('blueprint_binding_started') is True; bind_done=state.get('blueprint_binding_completed') is True
if sf_start and not segment: die('Source Fact started before Segment Mapping close')
if sf_done and not sf_start: die('Source Fact completed without start')
if cls_start and not sf_done: die('Classification started before Source Fact close')
if cls_done and not cls_start: die('Classification completed without start')
if page_start and not (cls_done and ci.get('current_classification_gate')=='SUCCESS'): die('Page Blueprint started without Classification CI PASS')
if page_done and not page_start: die('Page Blueprint completed without start')
if visual_start and not (page_done and ci.get('current_page_blueprint_gate')=='SUCCESS'): die('Visual Blueprint started without Page Blueprint CI PASS')
if visual_done and not visual_start: die('Visual Blueprint completed without start')
if bind_start and not (page_done and ci.get('current_page_blueprint_gate')=='SUCCESS' and visual_done and ci.get('current_visual_blueprint_gate')=='SUCCESS'): die('Binding started without Page+Visual CI PASS')
if bind_done and not bind_start: die('Binding completed without start')
# v2.1.12 common invariant: Stage-01 phase guard owns entry/exit ordering, but must not permanently pin later legal successors to Stage-01 flags.
trs=state.get('terminal_receipts') or {}
expected_stage1={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'c6a9c2e5b38a189a6517d59345a0738618e8cd28','run_id':34755361339,'job_denominator':'12/12','conclusion':'SUCCESS'}
stage1_closed=(state.get('stage1_validation_started') is True and state.get('stage1_validation_completed') is True and trs.get('stage1_closure')==expected_stage1)
if state.get('stage2_started') is True and not stage1_closed: die('Stage-02 started before Stage-01 external closure receipt')
if not stage1_closed:
    for k in ('website_construction_started','deployment_started'):
        if state.get(k) is True: die('Stage-1 forbidden phase started before closure:'+k)
if sf_done:
    dep=yaml.safe_load((run/'00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml').read_text()); gaps=dep.get('unresolved_authority_gaps') or []
    if dep.get('invented_dependency_count')!=0 or len(gaps)!=8 or len({g.get('gap_uid') for g in gaps})!=8: die('external Authority gap count/UID drift')
    if {g.get('authority_ref') for g in gaps}!=expected: die('external Authority reference identity drift')
    for g in gaps:
        if g.get('disposition')!='UNRESOLVED_AUTHORITY_GAP' or not g.get('consumer_source_uids') or not g.get('authority_evidence_ref'): die('external Authority record invalid:'+str(g.get('gap_uid')))
        if g.get('resolved') is True or g.get('satisfied') is True or g.get('auto_filled') is True or g.get('inferred') is True or g.get('substitute_authority_ref'): die('synthetic Authority resolution:'+str(g.get('gap_uid')))
print('PASS: v2.1.8 exact phase chain Segment -> Source Facts -> Classification -> Page -> Visual -> Binding remains fail-closed')
print('PASS: Stage-01 external 12/12 closure receipt gates Stage-02 entry; legal later successors are no longer retroactively blocked by Stage-01 flags')
print('PASS: 8 unresolved external Authority refs preserved without synthetic resolution')
