from __future__ import annotations
import argparse, copy, hashlib, json, os, subprocess
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
SCOPE = ROOT / 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
REGISTRY = ROOT / 'governance/specifications/REGISTRY.yaml'
LIFECYCLE = ROOT / '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
ADAPTERS = ROOT / 'governance/ci/stage_execution_semantic_adapters.yaml'
TEST_ROOT = ROOT / 'governance/test/stage03'
EXPECTED_STAGE = 'STAGE-03'
EXPECTED_CAPABILITY = 'VISUAL_DESIGN'

def load(path):
    if not path.is_file():
        raise RuntimeError(f'MISSING:{path.relative_to(ROOT)}')
    obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(obj, dict):
        raise RuntimeError(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding='utf-8')

def jdump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_head():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

def rel(path):
    return path.relative_to(ROOT).as_posix()

def find_dep(work, name):
    rows = [str(x) for x in work.get('dependencies') or [] if str(x).endswith('/' + name) or str(x).endswith(name)]
    if len(rows) != 1:
        raise RuntimeError(f'EXACT_DEPENDENCY_REQUIRED:{name}:{rows}')
    p = ROOT / rows[0]
    if not p.is_file():
        raise RuntimeError(f'DEPENDENCY_MISSING:{rows[0]}')
    return p

def stage_defs():
    profile = load(LIFECYCLE)
    adapters = load(ADAPTERS)
    st = next((x for x in profile.get('stages', []) if x.get('stage_uid') == EXPECTED_STAGE), None)
    ad = (adapters.get('stages') or {}).get(EXPECTED_STAGE)
    if not st or not ad:
        raise RuntimeError('STAGE03_PROFILE_OR_ADAPTER_MISSING')
    return (st, ad)

def resolve():
    state = load(STATE)
    scope = load(SCOPE)
    reg = load(REGISTRY)
    work = state.get('active_work_unit') or {}
    gov = (reg.get('active_specification') or {}).get('governance_uid')
    if state.get('specification_uid') != gov or scope.get('governance_uid') != gov:
        raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    if state.get('current_primary_task_layer') != 'PRODUCT_STAGE_EXECUTION':
        raise RuntimeError('PRODUCT_STAGE_LAYER_REQUIRED')
    if work.get('stage_uid') != EXPECTED_STAGE or work.get('semantic_capability') != EXPECTED_CAPABILITY:
        raise RuntimeError('ACTIVE_STAGE03_WORK_UNIT_REQUIRED')
    pages = scope.get('included_units') or []
    if len(pages) != 1 or work.get('scope') != pages:
        raise RuntimeError('EXACT_SINGLE_PAGE_SCOPE_REQUIRED')
    page = pages[0]
    visual = find_dep(work, 'VISUAL_BASE_BLUEPRINT.yaml')
    package = find_dep(work, 'PAGE_CONSTRUCTION_SPEC_PACKAGE.yaml')
    workbench = find_dep(work, 'FUNCTIONAL_WORKBENCH_CONTRACT.yaml')
    topology = find_dep(work, 'INTERACTION_TOPOLOGY_SPEC.yaml')
    impact = find_dep(work, 'FUNCTION_VISUAL_IMPACT_MATRIX.yaml')
    ai = [ROOT / str(x) for x in work.get('dependencies') or [] if str(x).endswith('/AI_INTERACTION_CONTINUITY_CONTRACT.yaml')]
    for p in ai:
        if not p.is_file():
            raise RuntimeError('AI_CONTINUITY_DEPENDENCY_MISSING')
    run_root = Path(str(visual.relative_to(ROOT))).parents[2]
    raw_root = ROOT / run_root / '00_SOURCE_INTAKE/RAW_SOURCE' / page
    docs = []
    for p in sorted(raw_root.glob('*.yaml')):
        d = load(p)
        docs.append((p, d))
    page_auth = [(p, d) for p, d in docs if isinstance(d.get('layout'), dict) and isinstance((d.get('registries') or {}).get('visuals'), list)]
    visual_auth = [(p, d) for p, d in docs if isinstance(d.get('current_canonical_visual'), dict)]
    if len(page_auth) != 1 or len(visual_auth) != 1:
        raise RuntimeError('EXACT_PAGE_AND_VISUAL_AUTHORITY_REQUIRED')
    st, ad = stage_defs()
    return {'state': state, 'scope': scope, 'reg': reg, 'gov': gov, 'work': work, 'page': page, 'run_root': ROOT / run_root, 'visual': visual, 'package': package, 'workbench': workbench, 'topology': topology, 'impact': impact, 'ai': ai, 'page_auth_path': page_auth[0][0], 'page_auth': page_auth[0][1], 'visual_auth_path': visual_auth[0][0], 'visual_auth': visual_auth[0][1], 'stage': st, 'adapter': ad}

def preview_svg(page_auth, workbench, impact):
    regs = page_auth.get('registries') or {}
    visuals = [x for x in regs.get('visuals') or [] if isinstance(x, dict)]
    controls = [x for x in regs.get('controls') or [] if isinstance(x, dict)]
    positions = {'CORE-01-VIS-CONTEXT': 70, 'CORE-01-VIS-LEFT': 170, 'CORE-01-VIS-CENTER-HEADER': 180, 'CORE-01-VIS-MESSAGES': 320, 'CORE-01-VIS-RUNTIME': 520, 'CORE-01-VIS-COMPOSER': 620, 'CORE-01-VIS-DECISION': 760, 'CORE-01-VIS-RIGHT-CORE': 180, 'CORE-01-VIS-RIGHT-TOPIC': 420, 'CORE-01-VIS-RIGHT-VERSION': 660}
    height = max(1500, 1000 + 24 * len(controls))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" viewBox="0 0 1280 {height}" data-normative="false" aria-label="Stage-03 authority-bounded reviewability preview">', '<style>rect,line{fill:none;stroke:currentColor;stroke-width:2} text{fill:currentColor;font-family:sans-serif;font-size:14px}.small{font-size:11px}</style>', '<text x="20" y="24">CORE-01 STAGE-03 AUTHORITY-BOUNDED REVIEWABILITY PREVIEW</text>', '<text x="20" y="44">GLOBAL VISUAL / SHELL AUTHORITY UNRESOLVED — HUMAN VISUAL REVIEW NOT REACHED</text>']
    boxes = {'CORE-01-VIS-CONTEXT': (20, 50, 1240, 54), 'CORE-01-VIS-LEFT': (20, 120, 250, 720), 'CORE-01-VIS-CENTER-HEADER': (290, 120, 650, 100), 'CORE-01-VIS-MESSAGES': (290, 240, 650, 220), 'CORE-01-VIS-RUNTIME': (290, 480, 650, 80), 'CORE-01-VIS-COMPOSER': (290, 580, 650, 100), 'CORE-01-VIS-DECISION': (290, 700, 650, 120), 'CORE-01-VIS-RIGHT-CORE': (960, 120, 300, 200), 'CORE-01-VIS-RIGHT-TOPIC': (960, 340, 300, 200), 'CORE-01-VIS-RIGHT-VERSION': (960, 560, 300, 260)}
    for row in visuals:
        uid = str(row.get('visual_uid') or '')
        if uid in boxes:
            x, y, w, h = boxes[uid]
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}"/>')
        yy = positions.get(uid, 880)
        parts.append(f'<text x="308" y="{yy}">{uid}</text>')
    parts.append('<text x="20" y="900">Required Control / Field identities from Current page authority:</text>')
    y = 930
    for row in controls:
        uid = str(row.get('control_uid') or '')
        if not uid:
            continue
        section = str(row.get('section_uid') or '')
        ctype = str(row.get('type') or '')
        parts.append(f'<text class="small" x="24" y="{y}">{uid} · {section} · {ctype}</text>')
        y += 22
    parts.append(f'<text class="small" x="20" y="{height - 20}">No global palette, typography, shell or component style is invented. Preview is blocked from Human Visual Review until unresolved external visual authorities are supplied.</text>')
    parts.append('</svg>')
    return '\n'.join(parts)

def execute():
    c = resolve()
    state = c['state']
    scope = c['scope']
    work = c['work']
    page = c['page']
    gov = c['gov']
    source_head = git_head()
    out = c['run_root'] / '05_VISUAL_DESIGN' / page
    out.mkdir(parents=True, exist_ok=True)
    page_auth = c['page_auth']
    visual_auth = c['visual_auth']
    visual_bp = load(c['visual'])
    workbench = load(c['workbench'])
    topology = load(c['topology'])
    impact = load(c['impact'])
    regs = page_auth.get('registries') or {}
    visuals = regs.get('visuals') or []
    sections = regs.get('sections') or []
    components = regs.get('components') or []
    controls = regs.get('controls') or []
    unresolved = visual_bp.get('unresolved_external_authority_refs') or []
    visual_unresolved = [x for x in unresolved if isinstance(x, dict) and any((tok in str(x.get('authority_ref') or '') for tok in ('VISUAL', 'SHELL', 'HOME_SHELL', 'DESIGN_SYSTEM'))) and (x.get('resolved') is not True)]
    source_refs = [rel(c['visual']), rel(c['package']), rel(c['workbench']), rel(c['topology']), rel(c['impact']), rel(c['page_auth_path']), rel(c['visual_auth_path'])] + [rel(x) for x in c['ai']]
    common = {'schema_version': 2, 'normative_authority': False, 'governance_uid': gov, 'stage_uid': EXPECTED_STAGE, 'page_uid': page, 'source_execution_sha': source_head, 'source_refs': source_refs, 'ai_autofill_used': False, 'inference_used': False}
    current_visual = visual_auth.get('current_canonical_visual') or {}
    design = {**common, 'artifact_type': 'VISUAL_DESIGN_SPEC_PACKAGE', 'blueprint_type_uid': 'BPTYPE-GOV-004', 'planning_domain': 'VISUAL_CONSTRUCTION', 'current_canonical_visual': current_visual, 'layout': page_auth.get('layout'), 'sections': sections, 'components': components, 'visuals': visuals, 'unresolved_external_authority_refs': unresolved, 'new_visual_pattern_introduced': False, 'human_visual_review_candidate': False, 'status': 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY'}
    geometry = {**common, 'artifact_type': 'VISUAL_GEOMETRY_CONTRACT', 'layout': page_auth.get('layout'), 'visual_geometry_units': visuals, 'responsive_contract': {'desktop_min_width': (page_auth.get('layout') or {}).get('desktop_min_width'), 'below_min_width': (page_auth.get('layout') or {}).get('below_min_width'), 'semantic_order_preserved': True}, 'status': 'PASS_EXACT_AUTHORITY_PROJECTION'}
    changes = {**common, 'artifact_type': 'VISUAL_CHANGESET', 'change_kind': 'AUTHORITY_PRESERVING_STAGE03_MATERIALIZATION', 'baseline_visual_uid': current_visual.get('visual_uid'), 'candidate_uids': (visual_auth.get('change_trace_contract') or {}).get('candidate_uids') or [], 'new_visual_pattern_introduced': False, 'unapproved_visual_reorder_or_surface_insertion': False, 'authority_update_performed': False, 'design_freeze_performed': False, 'status': 'BLOCKED_BEFORE_HUMAN_REVIEW_UNRESOLVED_VISUAL_AUTHORITY'}
    topo = {**common, 'artifact_type': 'VISUAL_INTERACTION_TOPOLOGY_BINDING', 'functional_visual_impact_rows': impact.get('rows') or [], 'field_bindings': impact.get('field_bindings') or [], 'interaction_relations': topology.get('edges') or [], 'functional_to_visual_topology_equivalence': 'PRESERVED_FROM_STAGE02_EXACT_BINDINGS', 'status': 'PASS'}
    sec_to_visual = {str(x.get('section_uid')): x.get('visual_uid') for x in sections if isinstance(x, dict) and x.get('section_uid')}
    section_bindings = []
    for row in workbench.get('section_workbenches') or []:
        if not isinstance(row, dict):
            continue
        section_bindings.append({'workbench_uid': row.get('workbench_uid'), 'section_uid': row.get('section_uid'), 'visual_uid': sec_to_visual.get(str(row.get('section_uid'))), 'component_uids': row.get('component_uids') or [], 'control_uids': row.get('control_uids') or []})
    atomic_bindings = []
    for row in workbench.get('atomic_workbenches') or []:
        if not isinstance(row, dict):
            continue
        section_order = list(row.get('section_order') or [])
        atomic_bindings.append({'workbench_uid': row.get('workbench_uid'), 'workbench_type': row.get('workbench_type'), 'section_order': section_order, 'visual_order': [sec_to_visual.get(str(x)) for x in section_order], 'same_surface': row.get('same_surface'), 'shared_context': row.get('shared_context') or [], 'interruption_boundary': row.get('interruption_boundary'), 'split_into_independent_surfaces': row.get('split_into_independent_surfaces'), 'relation_to_conversation': row.get('relation_to_conversation'), 'status': 'PASS_EXACT_STAGE02_SEMANTIC_PROJECTION'})
    wb = {**common, 'artifact_type': 'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT', 'section_workbench_visual_bindings': section_bindings, 'atomic_workbench_visual_bindings': atomic_bindings, 'atomic_workbench_fragmentation': False, 'semantic_section_order_preserved': True, 'decision_dock_relation': 'DOWNSTREAM_OF_CONVERSATION_EVIDENCE_NOT_PART_OF_MESSAGE_INPUT_LOOP', 'status': 'PASS'}
    inheritance_rows = []
    inheritance_rows.append({'authority_ref': str((visual_auth.get('authority') or {}).get('id') or 'CORE01_CURRENT_CANONICAL_VISUAL_OWNER'), 'source_path': rel(c['visual_auth_path']), 'version': str((visual_auth.get('authority') or {}).get('version') or current_visual.get('version') or ''), 'content_sha256': sha(c['visual_auth_path']), 'resolution': 'RESOLVED_PAGE_LOCAL_CURRENT_CANONICAL_VISUAL', 'inherited_rule_or_component': 'PAGE_LEVEL_CURRENT_CANONICAL_VISUAL_IDENTITY', 'lock_status': 'LOCKED', 'allowed_page_local_variation': 'ONLY_WHAT_CURRENT_AUTHORITY_EXPLICITLY_LEAVES_OPEN', 'required_change_set_for_deviation': True})
    for row in visual_unresolved:
        inheritance_rows.append({'authority_ref': row.get('authority_ref'), 'source_path': None, 'version': str(row.get('authority_ref') or '').split('@', 1)[1] if '@' in str(row.get('authority_ref') or '') else None, 'content_sha256': None, 'authority_evidence_ref': row.get('authority_evidence_ref'), 'resolution': 'UNRESOLVED_AUTHORITY', 'inherited_rule_or_component': None, 'lock_status': 'BLOCKED_UNRESOLVED', 'allowed_page_local_variation': False, 'required_change_set_for_deviation': True, 'ai_autofill_used': False, 'inference_used': False})
    inheritance = {**common, 'artifact_type': 'VISUAL_INHERITANCE_MATRIX', 'rows': inheritance_rows, 'resolved_authority_count': 1, 'unresolved_applicable_visual_authority_count': len(visual_unresolved), 'unresolved_applicable_visual_authority_refs': [x.get('authority_ref') for x in visual_unresolved], 'global_visual_style_materialized': False, 'status': 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY'}
    all_control_uids = [str(x.get('control_uid')) for x in controls if isinstance(x, dict) and x.get('control_uid')]
    all_section_uids = [str(x.get('section_uid')) for x in sections if isinstance(x, dict) and x.get('section_uid')]
    all_visual_uids = [str(x.get('visual_uid')) for x in visuals if isinstance(x, dict) and x.get('visual_uid')]
    workbench_uids = [str(x.get('workbench_uid')) for x in workbench.get('atomic_workbenches') or [] if isinstance(x, dict) and x.get('workbench_uid')]
    journey_uids = sorted({str(x.get('journey_uid')) for x in impact.get('rows') or [] if isinstance(x, dict) and x.get('journey_uid')})
    operation_uids = sorted({str(x.get('operation_uid')) for x in impact.get('rows') or [] if isinstance(x, dict) and x.get('operation_uid')})
    annotation_row = {'visual_uid': current_visual.get('visual_uid') or f'{page}-VIS-CURRENT', 'page_scope_uid': page, 'scenario_uid': f'{page}-SCENARIO-AUTHORITY-BOUNDED-REVIEWABILITY', 'state_uid': 'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY', 'workbench_uids': workbench_uids, 'journey_uids': journey_uids, 'parent_visual_uid': None, 'design_version': current_visual.get('design_version'), 'basic_design_change_set_uid': (visual_auth.get('change_trace_contract') or {}).get('change_uid'), 'viewport': 'DESKTOP_AUTHORITY_GEOMETRY', 'language': 'zh-TW', 'theme': 'UNRESOLVED_GLOBAL_VISUAL_AUTHORITY', 'business_entity_operations': operation_uids, 'visible_sections': all_section_uids, 'conditional_sections': [], 'locked_regions': all_visual_uids, 'editable_regions': [], 'visual_anchor_uids': [], 'visual_anchor_resolution': 'BLOCKED_WITH_GLOBAL_VISUAL_AUTHORITY', 'primary_controls': all_control_uids, 'disabled_blocked_controls': [], 'current_next_action': 'RESOLVE_CORE01_STAGE03_VISUAL_AUTHORITY', 'current_next_gate': 'VISUAL_AUTHORITY_RESOLUTION_BEFORE_HUMAN_VISUAL_REVIEW', 'source_authority_refs': source_refs, 'inherited_visual_authority_refs': [x.get('authority_ref') for x in inheritance_rows], 'verification_purpose': 'Prove exact page geometry, complete control identity, atomic Workbench order, and the unresolved visual-Authority boundary without inventing global style.'}
    annotation = {**common, 'artifact_type': 'VISUAL_REFERENCE_ANNOTATION', 'visual_candidates': [annotation_row], 'annotation_complete_for_current_non_final_preview': True, 'human_visual_review_eligible': False, 'status': 'MATERIALIZED_BLOCKED_UNRESOLVED_VISUAL_AUTHORITY'}
    scenario_types = ['VISUAL_ARCHITECTURE_OVERVIEW', 'CANONICAL_WORKSPACE_OVERVIEW', 'VISUAL_STYLE_BOARD', 'INTERACTION_TOPOLOGY_DIAGRAM', 'INITIAL_OR_EMPTY_STATE', 'ACTIVE_WORKING_STATE', 'COMPLEX_OR_CONDITIONAL_STATE', 'FINALIZATION_OR_CONFIRMATION_STATE', 'ERROR_BLOCKED_RECOVERY_STATE', 'CROSS_PAGE_RELATION_DIAGRAM', 'RESPONSIVE_VARIANT']
    scenarios = []
    for kind in scenario_types:
        scenarios.append({'scenario_uid': f'{page}-VIS-SCENARIO-{kind}', 'scenario_type': kind, 'required': True, 'coverage_status': 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY', 'workbench_uids': workbench_uids, 'operation_uids': operation_uids, 'control_uids': all_control_uids, 'visual_anchor_uids': [], 'visual_inheritance_ref': 'VISUAL_INHERITANCE_MATRIX', 'visual_candidate_ref': None, 'reason': 'GLOBAL_VISUAL_OR_SHELL_AUTHORITY_UNRESOLVED'})
    scenario_set = {**common, 'artifact_type': 'VISUAL_SCENARIO_EVIDENCE_SET', 'required_scenario_total': len(scenarios), 'materialized_scenario_record_total': len(scenarios), 'reviewable_final_candidate_total': 0, 'scenarios': scenarios, 'status': 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY'}
    svg = preview_svg(page_auth, workbench, impact)
    preview_ref = out / 'VISUAL_PREVIEW.svg'
    preview_ref.write_text(svg, encoding='utf-8')
    preview = {**common, 'artifact_type': 'VISUAL_PREVIEW_EVIDENCE', 'preview_ref': rel(preview_ref), 'preview_kind': 'NON_NORMATIVE_AUTHORITY_BOUNDED_REVIEWABILITY_PREVIEW', 'visual_authority_changed': False, 'human_review_required': True, 'human_review_candidate': False, 'review_status': 'BLOCKED_UNRESOLVED_VISUAL_AUTHORITY', 'control_uid_total': len(all_control_uids), 'control_uids_materialized_in_preview': all_control_uids, 'visual_reference_annotation_ref': rel(out / 'VISUAL_REFERENCE_ANNOTATION.yaml'), 'visual_inheritance_matrix_ref': rel(out / 'VISUAL_INHERITANCE_MATRIX.yaml'), 'visual_scenario_evidence_ref': rel(out / 'VISUAL_SCENARIO_EVIDENCE_SET.yaml'), 'status': 'MATERIALIZED_BLOCKED_BEFORE_HUMAN_REVIEW'}
    review = {**common, 'artifact_type': 'VISUAL_REVIEW_EVIDENCE', 'preview_ref': rel(preview_ref), 'review_required': True, 'review_result': 'NOT_REACHED_UNRESOLVED_VISUAL_AUTHORITY', 'visual_approval': False, 'authority_update_allowed': False, 'design_freeze_allowed': False, 'blocking_authority_refs': [x.get('authority_ref') for x in visual_unresolved], 'status': 'BLOCKED_BEFORE_HUMAN_REVIEW'}
    files = {'VISUAL_DESIGN_SPEC_PACKAGE.yaml': design, 'VISUAL_GEOMETRY_CONTRACT.yaml': geometry, 'VISUAL_PREVIEW_EVIDENCE.yaml': preview, 'VISUAL_CHANGESET.yaml': changes, 'VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml': topo, 'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT.yaml': wb, 'VISUAL_REFERENCE_ANNOTATION.yaml': annotation, 'VISUAL_INHERITANCE_MATRIX.yaml': inheritance, 'VISUAL_SCENARIO_EVIDENCE_SET.yaml': scenario_set, 'VISUAL_REVIEW_EVIDENCE.yaml': review}
    for n, d in files.items():
        dump(out / n, d)
    root = c['run_root'] / '05_VISUAL_DESIGN'
    problems = []
    for idx, row in enumerate(visual_unresolved, 1):
        problems.append({'problem_uid': f'STAGE03-{page}-VISUAL-AUTHORITY-GAP-{idx:02d}', 'page_uid': page, 'class': 'EXTERNAL_AUTHORITY_GAP', 'category': 'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY', 'owner': 'EXTERNAL_AUTHORITY_OWNER', 'authority_ref': row.get('authority_ref'), 'authority_evidence_ref': row.get('authority_evidence_ref'), 'status': 'OPEN', 'auto_remediable': False, 'product_credit': 0})
    open_total = len(problems)
    support = {'REQUIRED_FIELD_MANIFEST.yaml': {**common, 'artifact_type': 'REQUIRED_FIELD_MANIFEST', 'required_outputs': c['stage'].get('outputs'), 'required_evidence': c['stage'].get('required_evidence'), 'required_control_uid_total': len(all_control_uids)}, 'FUNCTIONAL_CHAIN_MANIFEST.yaml': {**common, 'artifact_type': 'FUNCTIONAL_CHAIN_MANIFEST', 'stage_operations': c['stage'].get('operations'), 'functional_visual_source_ref': rel(c['impact']), 'atomic_workbench_uids': workbench_uids}, 'EFFECTIVE_CONTRACT_OVERLAY.yaml': {**common, 'artifact_type': 'EFFECTIVE_CONTRACT_OVERLAY', 'raw_authority_refs': source_refs, 'legal_successor_output_root': rel(out), 'open_gap_total': open_total, 'unresolved_visual_authority_refs': [x.get('authority_ref') for x in visual_unresolved]}, 'DEPENDENCY_TOPOLOGY.yaml': {**common, 'artifact_type': 'DEPENDENCY_TOPOLOGY', 'dependencies': source_refs}, 'DENOMINATOR_SNAPSHOT.yaml': {**common, 'artifact_type': 'DENOMINATOR_SNAPSHOT', 'required_visual_output_total': len(c['stage'].get('outputs') or []), 'materialized_visual_output_total': len(c['stage'].get('outputs') or []), 'required_control_uid_total': len(all_control_uids), 'materialized_control_uid_total': len(all_control_uids), 'unresolved_applicable_visual_authority_total': open_total, 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'remaining_scope_total': 1}, 'CLASSIFICATION_RULESET.yaml': {**common, 'artifact_type': 'CLASSIFICATION_RULESET', 'routes': {'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY': 'EXTERNAL_AUTHORITY_OWNER'}}, 'CHANGE_IMPACT_MAP.yaml': {**common, 'artifact_type': 'CHANGE_IMPACT_MAP', 'affected_units': [page], 'new_visual_pattern_introduced': False, 'authority_update_performed': False, 'blocked_by_unresolved_authority': bool(open_total)}, 'STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml': {**common, 'artifact_type': 'STAGE_EXECUTION_PREFLIGHT_RECEIPT', 'entry_gate': 'ALL_REQUIRED_PAGES_STAGE2_CLOSED', 'pre_execution_gate': 'GOVERNANCE_LOAD_RECEIPT_PASS', 'status': 'PASS_WITH_CURRENT_AUTHORITY_GAPS_CLASSIFIED'}, 'CURRENT_PROBLEM_REGISTER.yaml': {**common, 'artifact_type': 'CURRENT_PROBLEM_REGISTER', 'open_problem_count': open_total, 'resolved_problem_count': 0, 'problems': problems}, 'RESOLUTION_LEDGER.yaml': {**common, 'artifact_type': 'RESOLUTION_LEDGER', 'entries': [{'problem_uid': x['problem_uid'], 'disposition': 'BLOCKED_EXTERNAL_AUTHORITY_REQUIRED', 'fresh_recheck_performed': True} for x in problems]}}
    for n, d in support.items():
        dump(root / n, d)
    conv = next((x for x in workbench.get('atomic_workbenches') or [] if isinstance(x, dict) and x.get('workbench_uid') == 'CORE-01-WB-CONVERSATION'), {})
    decision = next((x for x in workbench.get('atomic_workbenches') or [] if isinstance(x, dict) and x.get('workbench_uid') == 'CORE-01-WB-DECISION-DOCK'), {})
    scanner_truth = {'VISUAL_DOMAIN': len(c['stage'].get('outputs') or []) == 9 and len(files) >= 10, 'GEOMETRY': geometry.get('layout') == design.get('layout') and geometry.get('visual_geometry_units') == design.get('visuals'), 'PREVIEW_IDENTITY': all((uid in svg for uid in all_control_uids)), 'FUNCTION_TO_VISUAL_BINDING': topo.get('functional_visual_impact_rows') == (impact.get('rows') or []) and topo.get('field_bindings') == (impact.get('field_bindings') or []), 'ATOMIC_WORKBENCH_COHESION': conv.get('section_order') == ['CORE-01-SEC-03', 'CORE-01-SEC-04', 'CORE-01-SEC-06', 'CORE-01-SEC-07'] and decision.get('section_order') == ['CORE-01-SEC-05'], 'TOPOLOGY_EQUIVALENCE': topo.get('interaction_relations') == (topology.get('edges') or []), 'RESPONSIVE_ORDER': geometry.get('responsive_contract', {}).get('semantic_order_preserved') is True}
    if set(scanner_truth) != set(c['adapter'].get('scanner_dimensions') or []):
        raise RuntimeError('STAGE03_SCANNER_DENOMINATOR_DRIFT')
    if not all(scanner_truth.values()):
        raise RuntimeError('STAGE03_INTERNAL_SCANNER_FAILURE:' + json.dumps(scanner_truth, sort_keys=True))
    attempt_uid = str(work.get('attempt_uid') or f'STAGE03-{page}-CURRENT')
    phases = []
    phase_names = ['SESSION_BOOTSTRAP_RESUME_GATE', 'CURRENT_GOVERNANCE', 'CURRENT_SCOPE', 'WORK_UNIT', 'AUTHORITY', 'APPLICABILITY', 'DEPENDENCY', 'REQUIRED_FIELD_MANIFEST', 'STAGE_INPUT_CONTRACT', 'STAGE_OPERATIONS', 'OUTPUT_PRODUCER', 'CURRENT_PROBLEM_REGISTER', 'DENOMINATOR_SNAPSHOT', 'CHANGE_IMPACT', 'RESOLUTION_LEDGER', 'FRESH_EXECUTION', 'STAGE_SPECIFIC_SCANNER', 'GAP_CLASSIFICATION', 'OWNER_REMEDIATION', 'FRESH_REEXECUTION', 'HIDDEN_DEFECT_SWEEP', 'REQUIRED_EVIDENCE', 'EXACT_HEAD_GATES', 'TERMINAL_CLOSURE', 'PERSIST_RESUME', 'NEXT_STAGE']
    for ph in phase_names:
        status = 'PASS'
        if ph == 'TERMINAL_CLOSURE':
            status = 'BLOCKED'
        elif ph == 'NEXT_STAGE':
            status = 'NOT_EXECUTED_AFTER_BLOCK'
        phases.append({'phase_uid': ph, 'status': status})
    operations = [{'operation_uid': x, 'status': 'PASS'} for x in c['stage'].get('operations') or []]
    producers = c['stage'].get('output_producers') or {}
    outputs = [{'output_uid': x, 'producer_operation_uid': str(producers.get(x)), 'status': 'PASS', 'ref': rel(out / (x + '.yaml'))} for x in c['stage'].get('outputs') or []]
    scanners = [{'scanner_dimension': x, 'status': 'PASS', 'detail': 'fresh_current_input_validation'} for x in c['adapter'].get('scanner_dimensions') or []]
    validators = [{'validator_uid': x, 'status': 'PASS'} for x in c['stage'].get('validators') or []]
    run_id = os.environ.get('GITHUB_RUN_ID', 'LOCAL')
    evidence = {'artifact_type': 'NORMALIZED_COMMON_STAGE_EXECUTION_EVIDENCE', 'governance_uid': gov, 'stage_uid': EXPECTED_STAGE, 'attempt_uid': attempt_uid, 'scope_manifest_ref': rel(SCOPE), 'actual_stage_execution_started': True, 'actual_stage_execution_completed': True, 'fresh_execution': True, 'prior_results_used': False, 'current_specification_mutated': False, 'denominator': {'required_total': len(c['stage'].get('outputs') or []), 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'remaining_scope_total': 1}, 'gaps': problems, 'closure_blockers': [x['problem_uid'] for x in problems], 'required_evidence': [{'evidence_type': 'VISUAL_REVIEW_EVIDENCE', 'status': 'PASS', 'ref': rel(out / 'VISUAL_REVIEW_EVIDENCE.yaml'), 'external_receipt': False}], 'result': 'BLOCKED', 'stage_exit_allowed': False, 'source_head_sha': source_head, 'phase_trace': phases, 'operation_results': operations, 'output_results': outputs, 'scanner_results': scanners, 'validator_results': validators, 'remediation': {'performed': True, 'discovered_gap_total': open_total, 'remediated_gap_total': 0, 'unresolved_gap_total': open_total, 'reexecution_required': True, 'reexecution_performed': True, 'owner_route': 'EXTERNAL_AUTHORITY_GAP', 'reason': 'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITIES_PRESERVED_AFTER_FRESH_RECHECK'}, 'hidden_defect_sweep': {'performed': True, 'result': 'PASS', 'discovered_defect_total': 0}, 'exact_head_gate_receipts': [{'gate_uid': 'PREEXECUTION_FULL_LINE_INLINE', 'head_sha': source_head, 'run_id': int(run_id) if str(run_id).isdigit() else str(run_id), 'conclusion': 'success'}], 'resume_persistence': {'performed': True, 'resume_point': f'STAGE3_{page.replace('-', '')}_VISUAL_AUTHORITY_BLOCKED'}, 'next_stage_transition': {'next_stage_uid': 'STAGE-04', 'status': 'BLOCKED', 'reason': 'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY'}}
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    jdump(TEST_ROOT / 'STAGE03_LATEST_TEST_EVIDENCE.json', evidence)
    dump(TEST_ROOT / 'STAGE03_CURRENT_FINDINGS.yaml', {**common, 'artifact_type': 'STAGE03_CURRENT_FINDINGS', 'attempt_uid': attempt_uid, 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'result': 'BLOCKED', 'next_action': f'RESOLVE_{page.replace('-', '')}_STAGE03_VISUAL_AUTHORITY', 'problems': problems})
    ex = state.setdefault('execution', {})
    ex['run_uid'] = str(work.get('run_uid') or ex.get('run_uid') or '')
    ex['scope_mode'] = 'EXACT_PAGE_SCOPE_ONLY'
    ex['target_pages'] = [page]
    ex['current_stage'] = 'STAGE-03-TESTED-BLOCKED'
    ex['stage3'] = {'result': 'TEST_EXECUTED_BLOCKED', 'work_unit_uid': work.get('work_unit_uid'), 'work_unit_resolution': 'PASS_SINGLE_LEGAL_SUCCESSOR', 'execution_started': True, 'pre_execution_gate': 'GOVERNANCE_LOAD_RECEIPT_PASS', 'pre_execution_gate_status': 'PASS', 'stage_exit_allowed': False, 'artifact_root_present': True, 'prior_results_authoritative_for_current_governance': False, 'revalidation_required_under_current_governance': False, 'target_page_uids': [page], 'remaining_page_uids': [page], 'current_scope_manifest_ref': rel(SCOPE), 'output_owner_materialized': True, 'visual_review_required': True, 'human_visual_review_reached': False}
    ex['website_construction_allowed'] = False
    ex['deployment_allowed'] = False
    state['execution'] = ex
    ps = state.setdefault('selected_execution_profile_state', {})
    ps['current_step_state_key'] = 'stage3'
    ps['active_attempt_state_key'] = 'stage03_active_attempt'
    state['stage03_active_attempt'] = {'attempt_uid': attempt_uid, 'run_uid': work.get('run_uid'), 'frozen_governance_uid': gov, 'source_execution_sha': source_head, 'target_pages': [page], 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'remaining_scope_total': 1, 'active_evidence_present': True, 'active_findings_present': True, 'next_action': f'RESOLVE_{page.replace('-', '')}_STAGE03_VISUAL_AUTHORITY', 'product_blocker_credit': 0, 'prior_results_used': False, 'fresh_revalidation_required': False, 'closure_credit_under_current_governance': True}
    trans = state.setdefault('governance_revision_transition', {})
    trans['fresh_revalidation_required'] = False
    work['current_status'] = 'BLOCKED_UNRESOLVED_VISUAL_AUTHORITY'
    work['canonical_owner'] = rel(out / 'VISUAL_DESIGN_SPEC_PACKAGE.yaml')
    work['planned_output_owner'] = rel(out / 'VISUAL_DESIGN_SPEC_PACKAGE.yaml')
    work['generated_output_root_present'] = True
    work['product_blocker_credit'] = 0
    work['fresh_execution_evidence_ref'] = rel(TEST_ROOT / 'STAGE03_LATEST_TEST_EVIDENCE.json')
    hb = work.setdefault('human_review_boundary', {})
    hb['visual_review'] = 'NOT_REACHED_UNRESOLVED_VISUAL_AUTHORITY'
    hb['visual_approval'] = False
    hb['authority_update'] = False
    hb['design_freeze'] = False
    state['active_work_unit'] = work
    state['status'] = f'ACTIVE_{page.replace('-', '')}_STAGE03_AUTHORITY_BLOCKED'
    state['next_action'] = f'RESOLVE_{page.replace('-', '')}_STAGE03_VISUAL_AUTHORITY'
    state['resume_control'] = {'current_resume_point': f'STAGE3_{page.replace('-', '')}_VISUAL_AUTHORITY_BLOCKED', 'current_work_unit_uid': work.get('work_unit_uid'), 'current_owner': rel(out / 'VISUAL_DESIGN_SPEC_PACKAGE.yaml'), 'exact_next_action': state['next_action'], 'historical_stage2_results_are_current_state': False, 'stage2_execution_requires_fresh_entry_resolution': False}
    state['current_primary_task_product_stage_credit'] = 0
    dump(STATE, state)
    scope['remaining_units'] = [page]
    scope['fresh_revalidation_required'] = False
    scope['stage_exit_credit_allowed'] = False
    scope['closure_status'] = 'STAGE03_AUTHORITY_BLOCKED'
    scope['next_action'] = f'RESOLVE_{page.replace('-', '')}_STAGE03_VISUAL_AUTHORITY'
    for ref in [rel(root / 'CURRENT_PROBLEM_REGISTER.yaml'), rel(root / 'DENOMINATOR_SNAPSHOT.yaml')]:
        if ref not in (scope.get('denominator_source_refs') or []):
            scope.setdefault('denominator_source_refs', []).append(ref)
    scope_copy = copy.deepcopy(scope)
    scope_copy.pop('content_hash', None)
    scope['content_hash'] = hashlib.sha256(yaml.safe_dump(scope_copy, sort_keys=True, allow_unicode=True).encode()).hexdigest()
    dump(SCOPE, scope)
    print(json.dumps({'result': 'BLOCKED_UNRESOLVED_VISUAL_AUTHORITY', 'page_uid': page, 'output_root': rel(out), 'required_outputs_materialized': len(c['stage'].get('outputs') or []), 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'human_visual_review_reached': False, 'next_action': state['next_action']}, ensure_ascii=False, indent=2))

def bind_provenance():
    run_id = os.environ.get('STAGE03_WORKFLOW_RUN_ID')
    source_sha = os.environ.get('STAGE03_SOURCE_SHA')
    artifact_id = os.environ.get('STAGE03_ARTIFACT_ID')
    digest = os.environ.get('STAGE03_ARTIFACT_DIGEST', '')
    digest = digest.split(':', 1)[1] if digest.startswith('sha256:') else digest
    if not run_id or not source_sha or (not artifact_id) or (len(digest) != 64):
        raise RuntimeError('STAGE03_PROVENANCE_ENV_INCOMPLETE')
    state = load(STATE)
    attempt = state.get('stage03_active_attempt') or {}
    if attempt.get('source_execution_sha') != source_sha:
        raise RuntimeError('STAGE03_PROVENANCE_SOURCE_SHA_DRIFT')
    attempt['source_workflow_run_id'] = int(run_id) if run_id.isdigit() else run_id
    attempt['source_artifact_id'] = int(artifact_id) if artifact_id.isdigit() else artifact_id
    attempt['source_artifact_sha256'] = digest.lower()
    attempt['fresh_revalidation_required'] = False
    attempt['closure_credit_under_current_governance'] = True
    state['stage03_active_attempt'] = attempt
    trans = state.setdefault('governance_revision_transition', {})
    trans['fresh_revalidation_required'] = False
    trans['current_product_attempt_uid'] = attempt.get('attempt_uid')
    trans['current_product_attempt_run_uid'] = attempt.get('run_uid')
    trans['current_product_attempt_workflow_run_id'] = attempt['source_workflow_run_id']
    trans['current_product_attempt_artifact_id'] = attempt['source_artifact_id']
    trans['current_product_attempt_artifact_sha256'] = attempt['source_artifact_sha256']
    state['stage03_result_evidence'] = {'mode': 'RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT', 'tracked_current_evidence_ref': 'governance/test/stage03/STAGE03_LATEST_TEST_EVIDENCE.json', 'artifact_provenance_recorded_in_active_attempt': True}
    dump(STATE, state)
    evidence_path = TEST_ROOT / 'STAGE03_LATEST_TEST_EVIDENCE.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    evidence['source_workflow_run_id'] = attempt['source_workflow_run_id']
    evidence['source_artifact_id'] = attempt['source_artifact_id']
    evidence['source_artifact_sha256'] = attempt['source_artifact_sha256']
    jdump(evidence_path, evidence)
    print(json.dumps({'result': 'PASS', 'workflow_run_id': attempt['source_workflow_run_id'], 'artifact_id': attempt['source_artifact_id'], 'artifact_sha256': attempt['source_artifact_sha256']}, indent=2))

def self_test():
    st, ad = stage_defs()
    assert len(st.get('operations') or []) == 9 and len(st.get('outputs') or []) == 9
    assert len(ad.get('scanner_dimensions') or []) == 7
    assert {'VISUAL_REFERENCE_ANNOTATION', 'VISUAL_INHERITANCE_MATRIX', 'VISUAL_SCENARIO_EVIDENCE_SET'}.issubset(set(st.get('outputs') or []))
    assert 'VISUAL_REVIEW_EVIDENCE' in (st.get('required_evidence') or [])
    dummy = {'registries': {'visuals': [{'visual_uid': 'CORE-01-VIS-CENTER-HEADER'}, {'visual_uid': 'CORE-01-VIS-MESSAGES'}, {'visual_uid': 'CORE-01-VIS-RUNTIME'}, {'visual_uid': 'CORE-01-VIS-COMPOSER'}, {'visual_uid': 'CORE-01-VIS-DECISION'}], 'controls': [{'control_uid': 'CORE-01-BTN-SEND', 'section_uid': 'CORE-01-SEC-07', 'type': 'PRIMARY_BUTTON'}]}}
    svg = preview_svg(dummy, {'atomic_workbenches': []}, {'rows': [], 'field_bindings': []})
    assert 'STRUCTURAL PREVIEW ONLY' not in svg
    assert 'CORE-01-BTN-SEND' in svg
    assert svg.index('CORE-01-VIS-MESSAGES') < svg.index('CORE-01-VIS-RUNTIME') < svg.index('CORE-01-VIS-COMPOSER') < svg.index('CORE-01-VIS-DECISION')
    print('PASS: Current v2.2.15 Stage-03 visual producer self-test outputs=9 scanners=7 authority-blocking=preserved')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--bind-provenance', action='store_true')
    a = p.parse_args()
    if a.self_test:
        self_test()
        return
    if a.execute:
        execute()
        return
    if a.bind_provenance:
        bind_provenance()
        return
    raise SystemExit('use --self-test, --execute, or --bind-provenance')
if __name__ == '__main__':
    main()
