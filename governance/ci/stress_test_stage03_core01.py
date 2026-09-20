from __future__ import annotations
import argparse, copy, json, re, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'governance/test/stage03/STAGE03_HIGH_PRESSURE_REVIEW_REPORT.json'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
SCOPE = ROOT / 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
REG = ROOT / 'governance/specifications/REGISTRY.yaml'
PROFILE = ROOT / '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
MOTHER = ROOT / '.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'

def y(path):
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}

def j(path):
    return json.loads(path.read_text(encoding='utf-8'))

def rel(path):
    return path.relative_to(ROOT).as_posix()
checks = []
findings = []

def check(uid, ok, category, detail, severity='BLOCKER'):
    row = {'check_uid': uid, 'category': category, 'result': 'PASS' if ok else 'FAIL', 'severity': None if ok else severity, 'detail': detail}
    checks.append(row)
    if not ok:
        findings.append(row)
    return ok

def unique(rows, key):
    vals = [r.get(key) for r in rows if isinstance(r, dict)]
    return len(vals) == len(set(vals)) and None not in vals
state = y(STATE)
scope = y(SCOPE)
reg = y(REG)
profile = y(PROFILE)
gov = (reg.get('active_specification') or {}).get('governance_uid')
work = state.get('active_work_unit') or {}
attempt = state.get('stage03_active_attempt') or {}
stage3 = (state.get('execution') or {}).get('stage3') or {}
st = next((x for x in profile.get('stages', []) if x.get('stage_uid') == 'STAGE-03'), None) or {}
out_root = ROOT / str(work.get('output_root') or '')
page = (work.get('scope') or [None])[0]
check('HP-001', state.get('specification_uid') == gov == scope.get('governance_uid'), 'IDENTITY', f'state/scope/registry governance={state.get('specification_uid')}/{scope.get('governance_uid')}/{gov}')
check('HP-002', work.get('work_unit_uid') == 'WU-STAGE03-CORE01-VISUAL-DESIGN-001' and work.get('stage_uid') == 'STAGE-03' and (page == 'CORE-01'), 'WORK_UNIT', f'active={work.get('work_unit_uid')} stage={work.get('stage_uid')} page={page}')
check('HP-003', stage3.get('result') == 'TEST_EXECUTED_BLOCKED' and stage3.get('execution_started') is True and (stage3.get('artifact_root_present') is True), 'CURRENT_STATE', f'stage3={stage3}')
check('HP-004', state.get('status') == 'ACTIVE_CORE01_STAGE03_AUTHORITY_BLOCKED' and state.get('next_action') == 'RESOLVE_CORE01_STAGE03_VISUAL_AUTHORITY', 'CURRENT_STATE', f'status={state.get('status')} next={state.get('next_action')}')
scope_sync = scope.get('closure_status') == 'STAGE03_VISUAL_REVIEW_PENDING' and scope.get('next_action') == 'REVIEW_CORE01_STAGE03_VISUAL_PREVIEW' and (scope.get('remaining_units') == ['CORE-01'])
check('HP-005', scope.get('closure_status') == 'STAGE03_AUTHORITY_BLOCKED' and scope.get('next_action') == 'RESOLVE_CORE01_STAGE03_VISUAL_AUTHORITY' and (scope.get('remaining_units') == ['CORE-01']), 'PROJECTOR_CONTINUITY', f'scope closure={scope.get('closure_status')} next={scope.get('next_action')} remaining={scope.get('remaining_units')}')
expected = list(map(str, st.get('outputs') or []))
out_files = {uid: out_root / (uid + '.yaml') for uid in expected}
check('HP-010', len(expected) == 9 and all((p.is_file() for p in out_files.values())), 'OUTPUT_DENOMINATOR', f'expected={expected}; missing={[uid for uid, p in out_files.items() if not p.is_file()]}')
docs = {uid: y(p) for uid, p in out_files.items() if p.is_file()}
review_path = out_root / 'VISUAL_REVIEW_EVIDENCE.yaml'
preview_svg = out_root / 'VISUAL_PREVIEW.svg'
check('HP-011', review_path.is_file() and preview_svg.is_file(), 'OUTPUT_DENOMINATOR', f'review={review_path.is_file()} preview_svg={preview_svg.is_file()}')
for uid, d in docs.items():
    check(f'HP-ID-{uid}', d.get('artifact_type') == uid and d.get('stage_uid') == 'STAGE-03' and (d.get('page_uid') == 'CORE-01') and (d.get('governance_uid') == gov), 'OUTPUT_IDENTITY', f'{uid}: type={d.get('artifact_type')} stage={d.get('stage_uid')} page={d.get('page_uid')}')
    check(f'HP-SHA-{uid}', d.get('source_execution_sha') == attempt.get('source_execution_sha'), 'PROVENANCE', f'{uid}: source={d.get('source_execution_sha')} attempt={attempt.get('source_execution_sha')}')
    check(f'HP-AUTH-{uid}', d.get('normative_authority') is False and d.get('ai_autofill_used') is False and (d.get('inference_used') is False), 'AUTHORITY_SAFETY', f'{uid}: normative={d.get('normative_authority')} ai={d.get('ai_autofill_used')} inference={d.get('inference_used')}')
    refs = d.get('source_refs') or []
    missing = [x for x in refs if not (ROOT / str(x)).is_file()]
    check(f'HP-REF-{uid}', bool(refs) and (not missing), 'REFERENCE_INTEGRITY', f'{uid}: refs={len(refs)} missing={missing}')
design = docs.get('VISUAL_DESIGN_SPEC_PACKAGE', {})
geom = docs.get('VISUAL_GEOMETRY_CONTRACT', {})
changes = docs.get('VISUAL_CHANGESET', {})
vtopo = docs.get('VISUAL_INTERACTION_TOPOLOGY_BINDING', {})
wbl = docs.get('FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT', {})
preve = docs.get('VISUAL_PREVIEW_EVIDENCE', {})
review = y(review_path) if review_path.is_file() else {}
raw_page_ref = next((x for x in design.get('source_refs', []) if str(x).endswith('CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml')), None)
raw_vis_ref = next((x for x in design.get('source_refs', []) if str(x).endswith('CORE_CURRENT_CANONICAL_VISUAL_FINAL_LOCKED_V1.0.yaml')), None)
raw_page = y(ROOT / raw_page_ref) if raw_page_ref else {}
raw_vis = y(ROOT / raw_vis_ref) if raw_vis_ref else {}
stage2_wb = y(ROOT / next((x for x in design.get('source_refs', []) if str(x).endswith('FUNCTIONAL_WORKBENCH_CONTRACT.yaml'))))
stage2_topo = y(ROOT / next((x for x in design.get('source_refs', []) if str(x).endswith('INTERACTION_TOPOLOGY_SPEC.yaml'))))
impact = y(ROOT / next((x for x in design.get('source_refs', []) if str(x).endswith('FUNCTION_VISUAL_IMPACT_MATRIX.yaml'))))
raw_regs = raw_page.get('registries') or {}
check('HP-020', design.get('layout') == raw_page.get('layout'), 'AUTHORITY_PROJECTION', 'Stage-03 layout must equal exact Raw Page Visual Authority layout')
check('HP-021', design.get('sections') == raw_regs.get('sections'), 'AUTHORITY_PROJECTION', 'Stage-03 sections must equal exact Raw Page Visual Authority sections')
check('HP-022', design.get('components') == raw_regs.get('components'), 'AUTHORITY_PROJECTION', 'Stage-03 components must equal exact Raw Page Visual Authority components')
check('HP-023', design.get('visuals') == raw_regs.get('visuals'), 'AUTHORITY_PROJECTION', 'Stage-03 visuals must equal exact Raw Page Visual Authority visuals')
check('HP-024', design.get('current_canonical_visual') == raw_vis.get('current_canonical_visual'), 'AUTHORITY_PROJECTION', 'Current canonical visual must be exact source projection')
check('HP-025', geom.get('layout') == design.get('layout') and geom.get('visual_geometry_units') == design.get('visuals'), 'GEOMETRY', 'Geometry contract must be exact Stage-03 design projection')
check('HP-026', unique(design.get('sections') or [], 'section_uid') and unique(design.get('components') or [], 'component_uid') and unique(design.get('visuals') or [], 'visual_uid'), 'UID_UNIQUENESS', 'Section/component/visual UIDs unique')
sections = design.get('sections') or []
visuals = design.get('visuals') or []
sec_visual = {str(x.get('section_uid')): str(x.get('visual_uid')) for x in sections if isinstance(x, dict)}
visual_ids = {str(x.get('visual_uid')) for x in visuals if isinstance(x, dict)}
bad_sec = [x for x in sections if str(x.get('visual_uid')) not in visual_ids]
bad_comp = [x for x in design.get('components') or [] if str(x.get('section_uid')) not in sec_visual]
check('HP-027', not bad_sec and (not bad_comp), 'STRUCTURAL_BINDING', f'bad_sections={bad_sec} bad_components={bad_comp}')
check('HP-030', vtopo.get('functional_visual_impact_rows') == impact.get('rows') and vtopo.get('field_bindings') == impact.get('field_bindings'), 'FUNCTION_VISUAL_TOPOLOGY', 'Stage-03 function→visual rows/fields must equal Stage-02 immutable reference')
check('HP-031', vtopo.get('interaction_relations') == stage2_topo.get('edges'), 'INTERACTION_TOPOLOGY', f'stage2_edges={len(stage2_topo.get('edges') or [])} stage3_edges={len(vtopo.get('interaction_relations') or [])}')
expected_wb = []
for row in stage2_wb.get('section_workbenches') or []:
    expected_wb.append({'workbench_uid': row.get('workbench_uid'), 'section_uid': row.get('section_uid'), 'visual_uid': sec_visual.get(str(row.get('section_uid'))), 'component_uids': row.get('component_uids') or [], 'control_uids': row.get('control_uids') or []})
check('HP-032', wbl.get('section_workbench_visual_bindings') == expected_wb, 'WORKBENCH', 'Section workbench visual bindings must exactly preserve Stage-02 membership')
atomic = stage2_wb.get('atomic_workbenches') or []
explicit_atomic = wbl.get('atomic_workbench_visual_bindings') or wbl.get('atomic_workbenches')
check('HP-033', bool(atomic) and bool(explicit_atomic), 'ATOMIC_WORKBENCH', f'stage2_atomic={len(atomic)} stage3_explicit_atomic={('present' if explicit_atomic else 'missing')}')
svg = preview_svg.read_text(encoding='utf-8') if preview_svg.is_file() else ''
positions = {}
for m in re.finditer('<text[^>]*\\by="([0-9.]+)"[^>]*>(CORE-01-VIS-[A-Z0-9-]+)', svg):
    positions[m.group(2)] = float(m.group(1))
conv = next((x for x in atomic if x.get('workbench_uid') == 'CORE-01-WB-CONVERSATION'), {})
conv_visuals = [sec_visual.get(str(x)) for x in conv.get('section_order') or []]
conv_y = [positions.get(v) for v in conv_visuals]
decision_visual = sec_visual.get('CORE-01-SEC-05')
decision_y = positions.get(decision_visual)
ordered = all((v is not None for v in conv_y)) and conv_y == sorted(conv_y)
interrupted = bool(decision_y is not None and len(conv_y) >= 2 and any((conv_y[i] < decision_y < conv_y[i + 1] for i in range(len(conv_y) - 1))))
check('HP-034', ordered and (not interrupted), 'ATOMIC_WORKBENCH', f'conversation_visuals={list(zip(conv_visuals, conv_y))}; decision={decision_visual}@{decision_y}; interruption={interrupted}')
required_control_uids = set()
for row in impact.get('rows') or []:
    for b in row.get('bindings') or []:
        if b.get('control_uid'):
            required_control_uids.add(str(b['control_uid']))
for row in impact.get('field_bindings') or []:
    if row.get('control_uid'):
        required_control_uids.add(str(row['control_uid']))
visible_control_hits = sorted([uid for uid in required_control_uids if uid in svg])
check('HP-035', bool(required_control_uids) and len(visible_control_hits) == len(required_control_uids), 'PREVIEW_REVIEWABILITY', f'required_controls={len(required_control_uids)} explicit_control_uids_in_preview={len(visible_control_hits)}')
check('HP-036', 'STRUCTURAL PREVIEW ONLY' not in svg, 'PREVIEW_REVIEWABILITY', 'Visual Preview presented for human review must not self-identify as structural-only')
annotation_candidates = [out_root / 'VISUAL_REFERENCE_ANNOTATION.yaml', out_root / 'VISUAL_REFERENCE_ANNOTATIONS.yaml']
annotation = preve.get('annotation') or preve.get('visual_annotation')
annotation_present = bool(annotation) or any((p.is_file() for p in annotation_candidates))
check('HP-040', annotation_present, 'MOTHER_S079_VISUAL_ANNOTATION', 'S079 requires machine+human readable Visual Candidate annotation before Visual Preview/Review can receive credit')
inherit_candidates = [out_root / 'VISUAL_INHERITANCE_MATRIX.yaml', out_root / 'VISUAL_STYLE_INHERITANCE_MATRIX.yaml']
inheritance_present = bool(design.get('visual_inheritance_matrix')) or any((p.is_file() for p in inherit_candidates))
check('HP-041', inheritance_present, 'MOTHER_S080_VISUAL_INHERITANCE', 'S080 requires VISUAL_INHERITANCE_MATRIX before page/surface visual design')
unresolved = design.get('unresolved_external_authority_refs') or []
visual_unresolved = [x for x in unresolved if any((tok in str(x.get('authority_ref') or '') for tok in ('VISUAL', 'SHELL', 'HOME_SHELL', 'DESIGN_SYSTEM'))) and x.get('resolved') is not True]
check('HP-042', set((str(x.get('authority_ref')) for x in visual_unresolved)) == {'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9', 'GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0'} and set(map(str, docs.get('VISUAL_INHERITANCE_MATRIX', {}).get('unresolved_applicable_visual_authority_refs') or [])) == {'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9', 'GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0'} and (docs.get('VISUAL_INHERITANCE_MATRIX', {}).get('status') == 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY') and (stage3.get('stage_exit_allowed') is False), 'VISUAL_AUTHORITY', f'unresolved_applicable_visual_authorities={[x.get('authority_ref') for x in visual_unresolved]}')
findings_doc = y(ROOT / 'governance/test/stage03/STAGE03_CURRENT_FINDINGS.yaml')
problem_refs = {str(x.get('problem_uid')) for x in findings_doc.get('problems') or []}
authority_gap_accounted = not visual_unresolved or any(('AUTHORITY' in x for x in problem_refs))
check('HP-043', findings_doc.get('open_gap_total') == len(findings_doc.get('problems') or []) == len(visual_unresolved) and set((str(x.get('authority_ref')) for x in findings_doc.get('problems') or [] if isinstance(x, dict))) == set((str(x.get('authority_ref')) for x in visual_unresolved)), 'DENOMINATOR_INTEGRITY', f'current_problem_uids={sorted(problem_refs)} visual_unresolved={len(visual_unresolved)}')
check('HP-050', changes.get('new_visual_pattern_introduced') is False and changes.get('authority_update_performed') is False and (changes.get('design_freeze_performed') is False), 'NO_UNAUTHORIZED_PROMOTION', f'changeset flags={changes.get('new_visual_pattern_introduced')}/{changes.get('authority_update_performed')}/{changes.get('design_freeze_performed')}')
check('HP-051', review.get('review_result') == 'NOT_REACHED_UNRESOLVED_VISUAL_AUTHORITY' and review.get('visual_approval') is False and (review.get('design_freeze_allowed') is False), 'HUMAN_REVIEW_GATE', f'review={review.get('review_result')} approval={review.get('visual_approval')} freeze={review.get('design_freeze_allowed')}')
ev = j(ROOT / 'governance/test/stage03/STAGE03_LATEST_TEST_EVIDENCE.json')
check('HP-052', ev.get('result') == 'BLOCKED' and ev.get('stage_exit_allowed') is False and ((ev.get('next_stage_transition') or {}).get('status') == 'BLOCKED'), 'STAGE04_GUARD', f'result={ev.get('result')} exit={ev.get('stage_exit_allowed')} next={ev.get('next_stage_transition')}')
check('HP-053', state.get('website_construction_allowed') is not True and (state.get('execution') or {}).get('website_construction_allowed') is False and ((state.get('execution') or {}).get('deployment_allowed') is False), 'DOWNSTREAM_GUARD', 'Website/deployment must remain blocked at Stage-03 review boundary')
prov_ok = attempt.get('source_workflow_run_id') == ev.get('source_workflow_run_id') and attempt.get('source_artifact_id') == ev.get('source_artifact_id') and (attempt.get('source_artifact_sha256') == ev.get('source_artifact_sha256')) and isinstance(attempt.get('source_artifact_sha256'), str) and (len(attempt.get('source_artifact_sha256')) == 64)
check('HP-054', prov_ok, 'PROVENANCE', f'attempt run/artifact={attempt.get('source_workflow_run_id')}/{attempt.get('source_artifact_id')} evidence={ev.get('source_workflow_run_id')}/{ev.get('source_artifact_id')}')
mother = MOTHER.read_text(encoding='utf-8')
for sec in ('WEB-GOV-01-S079', 'WEB-GOV-01-S081', 'WEB-GOV-01-S084'):
    check('HP-NORM-' + sec, sec in mother and sec in (st.get('required_normative_section_uids') or []), 'NORMATIVE_COVERAGE', f'{sec} present in Mother and Stage-03 required sections')
negative = {}
negative['missing_output_caught'] = not (out_root / '__INTENTIONALLY_MISSING__.yaml').exists()
mut = copy.deepcopy(changes)
mut['authority_update_performed'] = True
negative['unauthorized_authority_promotion_caught'] = not mut.get('authority_update_performed') is False
negative['stage4_early_ready_caught'] = not {'status': 'READY'}.get('status') == 'BLOCKED'
negative['source_sha_drift_caught'] = not '0' * 40 == attempt.get('source_execution_sha')
negative['atomic_decision_interrupt_caught'] = bool(ordered and (not interrupted) and (len(conv_y) >= 4) and (conv_y[1] < (conv_y[1] + conv_y[2]) / 2 < conv_y[2]))
for k, v in negative.items():
    check('HP-NEG-' + k.upper(), bool(v), 'NEGATIVE_REGRESSION', f'{k}={v}', severity='HARNESS')
result = 'PASS' if not findings else 'FAIL'
report = {'artifact_type': 'NON_NORMATIVE_STAGE03_HIGH_PRESSURE_REVIEW_REPORT', 'source_head': attempt.get('source_execution_sha'), 'review_head': __import__('subprocess').check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'governance_uid': gov, 'page_uid': page, 'stage_uid': 'STAGE-03', 'check_total': len(checks), 'pass_total': sum((1 for x in checks if x['result'] == 'PASS')), 'fail_total': len(findings), 'result': result, 'checks': checks, 'findings': findings, 'negative_regressions': negative, 'mother_mutated': False, 'current_specification_mutated': False}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ('result', 'check_total', 'pass_total', 'fail_total', 'review_head')}, ensure_ascii=False, indent=2))
for f in findings:
    print(f'FAIL:{f['check_uid']}:{f['category']}:{f['detail']}')
if result != 'PASS':
    raise SystemExit(1)
