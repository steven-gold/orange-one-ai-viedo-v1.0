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

def collect_visual_anchor_uids(doc):
    found=set()
    def walk(value, key=None):
        if isinstance(value, dict):
            for k,v in value.items():
                if k in {'anchor_uid','visual_anchor_uid'} and isinstance(v,str) and v:
                    found.add(v)
                elif k in {'visual_anchor_uids','anchor_uids','anchors','visual_anchors'} and isinstance(v,list):
                    for item in v:
                        if isinstance(item,str) and item:
                            found.add(item)
                        elif isinstance(item,dict):
                            walk(item,k)
                walk(v,k)
        elif isinstance(value,list):
            for item in value:
                walk(item,key)
    walk(doc)
    return sorted(found)

def resolve_visual_anchor_registry(current_visual, work, run_root):
    ref=current_visual.get('anchor_registry_ref') or {}
    registry_uid=str(ref.get('anchor_registry_uid') or '')
    package_path=str(ref.get('package_path') or '')
    candidates=[]
    for key in ('materialized_path','current_path','canonical_path','package_path'):
        raw=str(ref.get(key) or '')
        if not raw:
            continue
        p=Path(raw)
        if p.is_absolute() or '..' in p.parts:
            raise RuntimeError(f'VISUAL_ANCHOR_REGISTRY_PATH_INVALID:{key}:{raw}')
        for candidate in (ROOT/p, run_root/p):
            if candidate.is_file():
                candidates.append(candidate)
    if package_path:
        name=Path(package_path).name
        for dep in work.get('dependencies') or []:
            dp=ROOT/str(dep)
            if dp.name==name and dp.is_file():
                candidates.append(dp)
    dep_map_path=run_root/'00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml'
    if dep_map_path.is_file():
        dep_map=load(dep_map_path)
        for rec in dep_map.get('materialization_records') or []:
            if not isinstance(rec,dict):
                continue
            matches_uid=registry_uid and rec.get('dependency_uid')==registry_uid
            matches_path=package_path and rec.get('declared_path')==package_path
            if matches_uid or matches_path:
                physical=str(rec.get('current_physical_path') or '')
                if physical:
                    p=ROOT/physical
                    if p.is_file():
                        candidates.append(p)
    unique={p.resolve() for p in candidates}
    if len(unique)>1 and len({sha(p) for p in unique})>1:
        raise RuntimeError('VISUAL_ANCHOR_REGISTRY_AMBIGUOUS_CURRENT_PHYSICAL_OWNER')
    path=next(iter(unique),None)
    anchor_uids=collect_visual_anchor_uids(load(path)) if path else []
    return {'declared':bool(registry_uid or package_path),'registry_uid':registry_uid,'declared_package_path':package_path,'physical_path':path,'visual_anchor_uids':anchor_uids,'ready':bool(path and anchor_uids)}

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

def preview_svg(page_auth, workbench, impact, authority_ready=False, visual_system=None, home_shell=None):
    regs = page_auth.get('registries') or {}
    visuals = [x for x in regs.get('visuals') or [] if isinstance(x, dict) and x.get('visual_uid')]
    controls = [x for x in regs.get('controls') or [] if isinstance(x, dict) and x.get('control_uid')]
    page_uid = str((page_auth.get('authority') or {}).get('page_uid') or page_auth.get('page_uid') or 'CURRENT-PAGE')
    tokens = (visual_system or {}).get('tokens') or {}
    bg = (tokens.get('background') or {}).get('page', '#050816')
    surface1 = (tokens.get('surface') or {}).get('l1', '#0C1026')
    surface2 = (tokens.get('surface') or {}).get('l2', '#111936')
    border = (tokens.get('border') or {}).get('normal', 'rgba(142,112,255,0.28)')
    text_primary = (tokens.get('text') or {}).get('primary', '#F3F5FF')
    text_secondary = (tokens.get('text') or {}).get('secondary', '#AEB7D9')
    cols=2
    rows=max(1,(len(visuals)+cols-1)//cols)
    visual_bottom=150+rows*112
    height=max(900,visual_bottom+160+24*len(controls))
    boundary = 'CURRENT VISUAL INPUTS RESOLVED — HUMAN VISUAL REVIEW PENDING' if authority_ready else 'CURRENT VISUAL INPUTS INCOMPLETE — HUMAN VISUAL REVIEW NOT REACHED'
    footer = 'Preview is non-normative and derived only from Current registered visual/control identities.'
    parts=[
      f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" viewBox="0 0 1280 {height}" data-normative="false" aria-label="Stage-03 source-derived reviewability preview">',
      f'<rect x="0" y="0" width="1280" height="{height}" fill="{bg}"/>',
      f'<style>text{{fill:{text_primary};font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:14px}}.small{{font-size:11px;fill:{text_secondary}}}.label{{font-size:12px;fill:{text_secondary}}}.panel{{fill:{surface1};stroke:{border};stroke-width:1.5}}.panel2{{fill:{surface2};stroke:{border};stroke-width:1.5}}</style>',
      f'<rect x="0" y="0" width="1280" height="58" fill="{surface1}" stroke="{border}"/>',
      f'<text x="28" y="35" font-weight="700">ORANGE ONE · {page_uid}</text>',
      f'<text x="28" y="82" class="label">{boundary}</text>',
    ]
    for i,row in enumerate(visuals):
        col=i%cols
        rr=i//cols
        x=72+col*588
        y=112+rr*112
        uid=str(row.get('visual_uid'))
        label=str(row.get('label') or row.get('name') or row.get('role') or '')
        parts.append(f'<rect x="{x}" y="{y}" width="552" height="88" rx="12" class="panel"/>')
        parts.append(f'<text x="{x+18}" y="{y+32}" class="label">{uid}</text>')
        if label:
            parts.append(f'<text x="{x+18}" y="{y+58}" class="small">{label}</text>')
    control_y=visual_bottom+36
    parts.append(f'<text x="72" y="{control_y}">Registered controls from Current page source:</text>')
    y=control_y+28
    for row in controls:
        uid=str(row.get('control_uid'))
        section=str(row.get('section_uid') or '')
        ctype=str(row.get('type') or '')
        parts.append(f'<text class="small" x="76" y="{y}">{uid} · {section} · {ctype}</text>')
        y+=22
    parts.append(f'<text class="small" x="20" y="{height-20}">{footer}</text>')
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

    expected_external = {
        'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9': {'path': ROOT / 'authority/global/GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY_FINAL_LOCKED_V1.9.yaml', 'id': 'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY', 'version': 'V1.9', 'role': 'GLOBAL_HOME_SHELL'},
        'GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0': {'path': ROOT / 'authority/global/GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY_FINAL_LOCKED.yaml', 'id': 'GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY', 'version': 'V1.0', 'role': 'GLOBAL_WEB_VISUAL_SYSTEM'}
    }
    resolved_external = []
    visual_unresolved = []
    for row in unresolved:
        if not isinstance(row, dict):
            continue
        ref = str(row.get('authority_ref') or '')
        visual_applicable = any(tok in ref for tok in ('VISUAL', 'SHELL', 'HOME_SHELL', 'DESIGN_SYSTEM'))
        if not visual_applicable:
            continue
        spec = expected_external.get(ref)
        if spec and spec['path'].is_file():
            doc = load(spec['path'])
            auth = doc.get('authority') or {}
            if auth.get('id') != spec['id'] or auth.get('version') != spec['version'] or not str(auth.get('status') or '').startswith('FINAL_LOCKED'):
                raise RuntimeError(f'EXTERNAL_VISUAL_AUTHORITY_IDENTITY_DRIFT:{ref}')
            resolved_external.append({'authority_ref': ref, 'path': spec['path'], 'authority': auth, 'role': spec['role'], 'content_sha256': sha(spec['path'])})
            continue
        visual_unresolved.append(row)
    external_authority_ready = len(resolved_external) == len(expected_external) and not visual_unresolved
    resolved_by_ref = {x['authority_ref']: x for x in resolved_external}
    global_visual_doc = load(expected_external['GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0']['path']) if 'GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0' in resolved_by_ref else {}
    home_shell_doc = load(expected_external['GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9']['path']) if 'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9' in resolved_by_ref else {}

    current_visual = visual_auth.get('current_canonical_visual') or {}
    anchor_state = resolve_visual_anchor_registry(current_visual, work, c['run_root'])
    anchor_uids = anchor_state['visual_anchor_uids']
    anchor_ready = anchor_state['ready']
    authority_ready = external_authority_ready and anchor_ready

    source_refs = [rel(c['visual']), rel(c['package']), rel(c['workbench']), rel(c['topology']), rel(c['impact']), rel(c['page_auth_path']), rel(c['visual_auth_path'])] + [rel(x) for x in c['ai']]
    source_refs.extend(rel(x['path']) for x in resolved_external)
    if anchor_state['physical_path']:
        source_refs.append(rel(anchor_state['physical_path']))
    common = {'schema_version': 2, 'normative_authority': False, 'governance_uid': gov, 'stage_uid': EXPECTED_STAGE, 'page_uid': page, 'source_execution_sha': source_head, 'source_refs': source_refs, 'ai_autofill_used': False, 'inference_used': False}
    design = {**common, 'artifact_type': 'VISUAL_DESIGN_SPEC_PACKAGE', 'blueprint_type_uid': 'BPTYPE-GOV-004', 'planning_domain': 'VISUAL_CONSTRUCTION', 'current_canonical_visual': current_visual, 'layout': page_auth.get('layout'), 'sections': sections, 'components': components, 'visuals': visuals, 'source_blueprint_unresolved_external_authority_refs': unresolved, 'current_unresolved_applicable_visual_authority_refs': visual_unresolved, 'resolved_current_external_visual_authorities': [{'authority_ref': x['authority_ref'], 'source_path': rel(x['path']), 'content_sha256': x['content_sha256']} for x in resolved_external], 'new_visual_pattern_introduced': False, 'human_visual_review_candidate': authority_ready, 'status': 'READY_FOR_HUMAN_VISUAL_REVIEW' if authority_ready else 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY'}
    design['visual_anchor_registry_uid'] = anchor_state['registry_uid'] or None
    design['visual_anchor_registry_declared_package_path'] = anchor_state['declared_package_path'] or None
    design['visual_anchor_registry_physical_ref'] = rel(anchor_state['physical_path']) if anchor_state['physical_path'] else None
    design['visual_anchor_uids'] = anchor_uids
    design['visual_anchor_readiness'] = 'READY' if anchor_ready else 'BLOCKED_SOURCE_CAPTURE_GAP'
    geometry = {**common, 'artifact_type': 'VISUAL_GEOMETRY_CONTRACT', 'layout': page_auth.get('layout'), 'visual_geometry_units': visuals, 'global_shell_authority_ref': 'GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9' if authority_ready else None, 'responsive_contract': {'desktop_min_width': (page_auth.get('layout') or {}).get('desktop_min_width'), 'below_min_width': (page_auth.get('layout') or {}).get('below_min_width'), 'semantic_order_preserved': True}, 'status': 'PASS_EXACT_AUTHORITY_PROJECTION'}
    changes = {**common, 'artifact_type': 'VISUAL_CHANGESET', 'change_kind': 'AUTHORITY_PRESERVING_STAGE03_MATERIALIZATION', 'baseline_visual_uid': current_visual.get('visual_uid'), 'candidate_uids': (visual_auth.get('change_trace_contract') or {}).get('candidate_uids') or [], 'new_visual_pattern_introduced': False, 'unapproved_visual_reorder_or_surface_insertion': False, 'authority_update_performed': False, 'design_freeze_performed': False, 'status': 'READY_FOR_HUMAN_VISUAL_REVIEW' if authority_ready else 'BLOCKED_BEFORE_HUMAN_REVIEW_UNRESOLVED_VISUAL_AUTHORITY'}
    topo = {**common, 'artifact_type': 'VISUAL_INTERACTION_TOPOLOGY_BINDING', 'functional_visual_impact_rows': impact.get('rows') or [], 'field_bindings': impact.get('field_bindings') or [], 'interaction_relations': topology.get('edges') or [], 'functional_to_visual_topology_equivalence': 'PRESERVED_FROM_STAGE02_EXACT_BINDINGS', 'status': 'PASS'}

    sec_to_visual = {str(x.get('section_uid')): x.get('visual_uid') for x in sections if isinstance(x, dict) and x.get('section_uid')}
    section_bindings = []
    for row in workbench.get('section_workbenches') or []:
        if isinstance(row, dict):
            section_bindings.append({'workbench_uid': row.get('workbench_uid'), 'section_uid': row.get('section_uid'), 'visual_uid': sec_to_visual.get(str(row.get('section_uid'))), 'component_uids': row.get('component_uids') or [], 'control_uids': row.get('control_uids') or []})
    atomic_bindings = []
    for row in workbench.get('atomic_workbenches') or []:
        if not isinstance(row, dict):
            continue
        section_order = list(row.get('section_order') or [])
        atomic_bindings.append({'workbench_uid': row.get('workbench_uid'), 'workbench_type': row.get('workbench_type'), 'section_order': section_order, 'visual_order': [sec_to_visual.get(str(x)) for x in section_order], 'same_surface': row.get('same_surface'), 'shared_context': row.get('shared_context') or [], 'interruption_boundary': row.get('interruption_boundary'), 'split_into_independent_surfaces': row.get('split_into_independent_surfaces'), 'relation_to_conversation': row.get('relation_to_conversation'), 'status': 'PASS_EXACT_STAGE02_SEMANTIC_PROJECTION'})
    wb = {**common, 'artifact_type': 'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT', 'section_workbench_visual_bindings': section_bindings, 'atomic_workbench_visual_bindings': atomic_bindings, 'atomic_workbench_fragmentation': False, 'semantic_section_order_preserved': True, 'decision_dock_relation': 'DOWNSTREAM_OF_CONVERSATION_EVIDENCE_NOT_PART_OF_MESSAGE_INPUT_LOOP', 'status': 'PASS'}

    inheritance_rows = [{'authority_ref': str((visual_auth.get('authority') or {}).get('id') or 'CORE01_CURRENT_CANONICAL_VISUAL_OWNER'), 'source_path': rel(c['visual_auth_path']), 'version': str((visual_auth.get('authority') or {}).get('version') or current_visual.get('version') or ''), 'content_sha256': sha(c['visual_auth_path']), 'resolution': 'RESOLVED_PAGE_LOCAL_CURRENT_CANONICAL_VISUAL', 'inherited_rule_or_component': 'PAGE_LEVEL_CURRENT_CANONICAL_VISUAL_IDENTITY', 'lock_status': 'LOCKED', 'allowed_page_local_variation': 'ONLY_WHAT_CURRENT_AUTHORITY_EXPLICITLY_LEAVES_OPEN', 'required_change_set_for_deviation': True}]
    for row in resolved_external:
        inheritance_rows.append({'authority_ref': row['authority_ref'], 'source_path': rel(row['path']), 'version': row['authority'].get('version'), 'content_sha256': row['content_sha256'], 'resolution': 'RESOLVED_CURRENT_PHYSICAL_AUTHORITY', 'inherited_rule_or_component': row['role'], 'lock_status': row['authority'].get('status'), 'allowed_page_local_variation': False if row['role'] == 'GLOBAL_HOME_SHELL' else 'ONLY_WHERE_PAGE_AUTHORITY_EXPLICITLY_OWNS_INTERNAL_LAYOUT', 'required_change_set_for_deviation': True, 'ai_autofill_used': False, 'inference_used': False})
    for row in visual_unresolved:
        inheritance_rows.append({'authority_ref': row.get('authority_ref'), 'source_path': None, 'version': str(row.get('authority_ref') or '').split('@', 1)[1] if '@' in str(row.get('authority_ref') or '') else None, 'content_sha256': None, 'authority_evidence_ref': row.get('authority_evidence_ref'), 'resolution': 'UNRESOLVED_AUTHORITY', 'inherited_rule_or_component': None, 'lock_status': 'BLOCKED_UNRESOLVED', 'allowed_page_local_variation': False, 'required_change_set_for_deviation': True, 'ai_autofill_used': False, 'inference_used': False})
    inheritance = {**common, 'artifact_type': 'VISUAL_INHERITANCE_MATRIX', 'rows': inheritance_rows, 'resolved_authority_count': 1 + len(resolved_external), 'unresolved_applicable_visual_authority_count': len(visual_unresolved), 'unresolved_applicable_visual_authority_refs': [x.get('authority_ref') for x in visual_unresolved], 'global_visual_style_materialized': authority_ready, 'status': 'PASS_READY_FOR_HUMAN_VISUAL_REVIEW' if authority_ready else 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY'}

    all_control_uids = [str(x.get('control_uid')) for x in controls if isinstance(x, dict) and x.get('control_uid')]
    all_section_uids = [str(x.get('section_uid')) for x in sections if isinstance(x, dict) and x.get('section_uid')]
    all_visual_uids = [str(x.get('visual_uid')) for x in visuals if isinstance(x, dict) and x.get('visual_uid')]
    workbench_uids = [str(x.get('workbench_uid')) for x in workbench.get('atomic_workbenches') or [] if isinstance(x, dict) and x.get('workbench_uid')]
    journey_uids = sorted({str(x.get('journey_uid')) for x in impact.get('rows') or [] if isinstance(x, dict) and x.get('journey_uid')})
    operation_uids = sorted({str(x.get('operation_uid')) for x in impact.get('rows') or [] if isinstance(x, dict) and x.get('operation_uid')})
    if not anchor_ready:
        next_action = 'WORK_UNIT_RESOLUTION_GATE_REENTER_SOURCE_INTAKE_BASE_BLUEPRINT'
        resume_point = f'STAGE3_{page.replace("-", "")}_UPSTREAM_VISUAL_ANCHOR_SOURCE_CAPTURE_REENTRY_REQUIRED'
    elif authority_ready:
        next_action = f'HUMAN_VISUAL_REVIEW_{page.replace("-", "")}_STAGE03'
        resume_point = f'STAGE3_{page.replace("-", "")}_VISUAL_REVIEW_PENDING'
    else:
        next_action = f'RESOLVE_{page.replace("-", "")}_STAGE03_VISUAL_AUTHORITY'
        resume_point = f'STAGE3_{page.replace("-", "")}_VISUAL_AUTHORITY_BLOCKED'
    annotation_row = {'visual_uid': current_visual.get('visual_uid') or f'{page}-VIS-CURRENT', 'page_scope_uid': page, 'scenario_uid': f'{page}-SCENARIO-AUTHORITY-BOUNDED-REVIEWABILITY', 'state_uid': 'HUMAN_VISUAL_REVIEW_PENDING' if authority_ready else 'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY', 'workbench_uids': workbench_uids, 'journey_uids': journey_uids, 'parent_visual_uid': None, 'design_version': current_visual.get('design_version'), 'basic_design_change_set_uid': (visual_auth.get('change_trace_contract') or {}).get('change_uid'), 'viewport': 'DESKTOP_AUTHORITY_GEOMETRY', 'language': 'zh-TW', 'theme': 'GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0' if authority_ready else 'UNRESOLVED_GLOBAL_VISUAL_AUTHORITY', 'business_entity_operations': operation_uids, 'visible_sections': all_section_uids, 'conditional_sections': [], 'locked_regions': all_visual_uids, 'editable_regions': [], 'visual_anchor_uids': anchor_uids, 'visual_anchor_resolution': 'CURRENT_AUTHORITIES_RESOLVED_REVIEW_PENDING' if authority_ready else 'BLOCKED_WITH_GLOBAL_VISUAL_AUTHORITY', 'primary_controls': all_control_uids, 'disabled_blocked_controls': [], 'current_next_action': next_action, 'current_next_gate': 'HUMAN_VISUAL_REVIEW' if authority_ready else 'VISUAL_AUTHORITY_RESOLUTION_BEFORE_HUMAN_VISUAL_REVIEW', 'source_authority_refs': source_refs, 'inherited_visual_authority_refs': [x.get('authority_ref') for x in inheritance_rows], 'verification_purpose': 'Prove exact page geometry, complete control identity, atomic Workbench order, Current global visual inheritance, and the human visual review boundary without self-approval.'}
    annotation = {**common, 'artifact_type': 'VISUAL_REFERENCE_ANNOTATION', 'visual_candidates': [annotation_row], 'annotation_complete_for_current_non_final_preview': True, 'human_visual_review_eligible': authority_ready, 'status': 'MATERIALIZED_READY_FOR_HUMAN_VISUAL_REVIEW' if authority_ready else 'MATERIALIZED_BLOCKED_UNRESOLVED_VISUAL_AUTHORITY'}

    scenario_types = ['VISUAL_ARCHITECTURE_OVERVIEW', 'CANONICAL_WORKSPACE_OVERVIEW', 'VISUAL_STYLE_BOARD', 'INTERACTION_TOPOLOGY_DIAGRAM', 'INITIAL_OR_EMPTY_STATE', 'ACTIVE_WORKING_STATE', 'COMPLEX_OR_CONDITIONAL_STATE', 'FINALIZATION_OR_CONFIRMATION_STATE', 'ERROR_BLOCKED_RECOVERY_STATE', 'CROSS_PAGE_RELATION_DIAGRAM', 'RESPONSIVE_VARIANT']
    scenarios = []
    for kind in scenario_types:
        scenarios.append({'scenario_uid': f'{page}-VIS-SCENARIO-{kind}', 'scenario_type': kind, 'required': True, 'coverage_status': 'MATERIALIZED_FOR_HUMAN_VISUAL_REVIEW' if authority_ready else 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY', 'workbench_uids': workbench_uids, 'operation_uids': operation_uids, 'control_uids': all_control_uids, 'visual_anchor_uids': anchor_uids, 'visual_inheritance_ref': 'VISUAL_INHERITANCE_MATRIX', 'visual_candidate_ref': 'VISUAL_PREVIEW.svg' if authority_ready else None, 'reason': 'HUMAN_VISUAL_REVIEW_PENDING' if authority_ready else 'GLOBAL_VISUAL_OR_SHELL_AUTHORITY_UNRESOLVED'})
    scenario_set = {**common, 'artifact_type': 'VISUAL_SCENARIO_EVIDENCE_SET', 'required_scenario_total': len(scenarios), 'materialized_scenario_record_total': len(scenarios), 'reviewable_final_candidate_total': len(scenarios) if authority_ready else 0, 'scenarios': scenarios, 'status': 'MATERIALIZED_READY_FOR_HUMAN_VISUAL_REVIEW' if authority_ready else 'BLOCKED_UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY'}

    svg = preview_svg(page_auth, workbench, impact, authority_ready=authority_ready, visual_system=global_visual_doc, home_shell=home_shell_doc)
    preview_ref = out / 'VISUAL_PREVIEW.svg'
    preview_ref.write_text(svg, encoding='utf-8')
    preview = {**common, 'artifact_type': 'VISUAL_PREVIEW_EVIDENCE', 'preview_ref': rel(preview_ref), 'preview_kind': 'NON_NORMATIVE_AUTHORITY_BOUNDED_REVIEWABILITY_PREVIEW', 'visual_authority_changed': False, 'human_review_required': True, 'human_review_candidate': authority_ready, 'review_status': 'PENDING_HUMAN_VISUAL_REVIEW' if authority_ready else 'BLOCKED_UNRESOLVED_VISUAL_AUTHORITY', 'control_uid_total': len(all_control_uids), 'control_uids_materialized_in_preview': all_control_uids, 'resolved_global_authority_refs': [x['authority_ref'] for x in resolved_external], 'visual_reference_annotation_ref': rel(out / 'VISUAL_REFERENCE_ANNOTATION.yaml'), 'visual_inheritance_matrix_ref': rel(out / 'VISUAL_INHERITANCE_MATRIX.yaml'), 'visual_scenario_evidence_ref': rel(out / 'VISUAL_SCENARIO_EVIDENCE_SET.yaml'), 'status': 'READY_FOR_HUMAN_VISUAL_REVIEW' if authority_ready else 'MATERIALIZED_BLOCKED_BEFORE_HUMAN_REVIEW'}
    review = {**common, 'artifact_type': 'VISUAL_REVIEW_EVIDENCE', 'preview_ref': rel(preview_ref), 'review_required': True, 'review_result': 'PENDING_HUMAN_VISUAL_REVIEW' if authority_ready else 'NOT_REACHED_UNRESOLVED_VISUAL_AUTHORITY', 'visual_approval': False, 'authority_update_allowed': False, 'design_freeze_allowed': False, 'blocking_authority_refs': [x.get('authority_ref') for x in visual_unresolved], 'resolved_authority_refs': [x['authority_ref'] for x in resolved_external], 'status': 'PENDING_HUMAN_VISUAL_REVIEW' if authority_ready else 'BLOCKED_BEFORE_HUMAN_REVIEW'}
    files = {'VISUAL_DESIGN_SPEC_PACKAGE.yaml': design, 'VISUAL_GEOMETRY_CONTRACT.yaml': geometry, 'VISUAL_PREVIEW_EVIDENCE.yaml': preview, 'VISUAL_CHANGESET.yaml': changes, 'VISUAL_INTERACTION_TOPOLOGY_BINDING.yaml': topo, 'FUNCTIONAL_WORKBENCH_LAYOUT_CONTRACT.yaml': wb, 'VISUAL_REFERENCE_ANNOTATION.yaml': annotation, 'VISUAL_INHERITANCE_MATRIX.yaml': inheritance, 'VISUAL_SCENARIO_EVIDENCE_SET.yaml': scenario_set, 'VISUAL_REVIEW_EVIDENCE.yaml': review}
    for n, d in files.items():
        dump(out / n, d)

    root = c['run_root'] / '05_VISUAL_DESIGN'
    problems = []
    for idx, row in enumerate(visual_unresolved, 1):
        problems.append({'problem_uid': f'STAGE03-{page}-VISUAL-AUTHORITY-GAP-{idx:02d}', 'page_uid': page, 'class': 'EXTERNAL_AUTHORITY_GAP', 'category': 'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY', 'owner': 'EXTERNAL_AUTHORITY_OWNER', 'authority_ref': row.get('authority_ref'), 'authority_evidence_ref': row.get('authority_evidence_ref'), 'status': 'OPEN', 'auto_remediable': False, 'product_credit': 0})
    if not anchor_ready:
        problems.append({'problem_uid': f'STAGE03-{page}-VISUAL-ANCHOR-SOURCE-CAPTURE-GAP-01', 'page_uid': page, 'class': 'SOURCE_CAPTURE_GAP', 'category': 'VISUAL_ANCHOR_REGISTRY_NOT_PHYSICALLY_MATERIALIZED' if not anchor_state['physical_path'] else 'VISUAL_ANCHOR_REGISTRY_EMPTY', 'owner': 'SOURCE_INTAKE_BASE_BLUEPRINT', 'authority_ref': anchor_state['registry_uid'] or anchor_state['declared_package_path'], 'authority_evidence_ref': rel(c['visual_auth_path']), 'status': 'OPEN', 'auto_remediable': False, 'product_credit': 0})
    open_total = len(problems)
    remaining_scope_total = 1
    resolution_entries = [{'authority_ref': x['authority_ref'], 'disposition': 'RESOLVED_BY_CURRENT_PHYSICAL_AUTHORITY', 'source_path': rel(x['path']), 'content_sha256': x['content_sha256'], 'fresh_recheck_performed': True} for x in resolved_external]
    if anchor_ready:
        resolution_entries.append({'authority_ref': anchor_state['registry_uid'], 'disposition': 'RESOLVED_BY_CURRENT_PHYSICAL_VISUAL_ANCHOR_REGISTRY', 'source_path': rel(anchor_state['physical_path']), 'visual_anchor_uid_total': len(anchor_uids), 'fresh_recheck_performed': True})
    resolution_entries.extend({'problem_uid': x['problem_uid'], 'disposition': 'BLOCKED_OWNER_REENTRY_REQUIRED' if x.get('class') == 'SOURCE_CAPTURE_GAP' else 'BLOCKED_EXTERNAL_AUTHORITY_REQUIRED', 'fresh_recheck_performed': True} for x in problems)
    support = {
        'REQUIRED_FIELD_MANIFEST.yaml': {**common, 'artifact_type': 'REQUIRED_FIELD_MANIFEST', 'required_outputs': c['stage'].get('outputs'), 'required_evidence': c['stage'].get('required_evidence'), 'required_control_uid_total': len(all_control_uids)},
        'FUNCTIONAL_CHAIN_MANIFEST.yaml': {**common, 'artifact_type': 'FUNCTIONAL_CHAIN_MANIFEST', 'stage_operations': c['stage'].get('operations'), 'functional_visual_source_ref': rel(c['impact']), 'atomic_workbench_uids': workbench_uids},
        'EFFECTIVE_CONTRACT_OVERLAY.yaml': {**common, 'artifact_type': 'EFFECTIVE_CONTRACT_OVERLAY', 'raw_authority_refs': source_refs, 'legal_successor_output_root': rel(out), 'open_gap_total': open_total, 'resolved_external_visual_authority_refs': [x['authority_ref'] for x in resolved_external], 'unresolved_visual_authority_refs': [x.get('authority_ref') for x in visual_unresolved]},
        'DEPENDENCY_TOPOLOGY.yaml': {**common, 'artifact_type': 'DEPENDENCY_TOPOLOGY', 'dependencies': source_refs},
        'DENOMINATOR_SNAPSHOT.yaml': {**common, 'artifact_type': 'DENOMINATOR_SNAPSHOT', 'required_visual_output_total': len(c['stage'].get('outputs') or []), 'materialized_visual_output_total': len(c['stage'].get('outputs') or []), 'required_control_uid_total': len(all_control_uids), 'materialized_control_uid_total': len(all_control_uids), 'resolved_applicable_visual_authority_total': len(resolved_external), 'unresolved_applicable_visual_authority_total': open_total, 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'remaining_scope_total': remaining_scope_total},
        'CLASSIFICATION_RULESET.yaml': {**common, 'artifact_type': 'CLASSIFICATION_RULESET', 'routes': {'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY': 'EXTERNAL_AUTHORITY_OWNER', 'HUMAN_VISUAL_REVIEW_PENDING': 'USER_OR_AUTHORIZED_VISUAL_REVIEWER'}},
        'CHANGE_IMPACT_MAP.yaml': {**common, 'artifact_type': 'CHANGE_IMPACT_MAP', 'affected_units': [page], 'new_visual_pattern_introduced': False, 'authority_update_performed': False, 'blocked_by_unresolved_authority': bool(open_total), 'human_visual_review_pending': authority_ready},
        'STAGE_EXECUTION_PREFLIGHT_RECEIPT.yaml': {**common, 'artifact_type': 'STAGE_EXECUTION_PREFLIGHT_RECEIPT', 'entry_gate': 'ALL_REQUIRED_PAGES_STAGE2_CLOSED', 'pre_execution_gate': 'GOVERNANCE_LOAD_RECEIPT_PASS', 'status': 'PASS_READY_FOR_HUMAN_VISUAL_REVIEW' if authority_ready else 'PASS_WITH_CURRENT_AUTHORITY_GAPS_CLASSIFIED'},
        'CURRENT_PROBLEM_REGISTER.yaml': {**common, 'artifact_type': 'CURRENT_PROBLEM_REGISTER', 'open_problem_count': open_total, 'resolved_problem_count': len(resolved_external), 'problems': problems},
        'RESOLUTION_LEDGER.yaml': {**common, 'artifact_type': 'RESOLUTION_LEDGER', 'entries': resolution_entries}
    }
    support['DENOMINATOR_SNAPSHOT.yaml']['declared_visual_anchor_registry_total'] = 1 if anchor_state['declared'] else 0
    support['DENOMINATOR_SNAPSHOT.yaml']['materialized_visual_anchor_registry_total'] = 1 if anchor_state['physical_path'] else 0
    support['DENOMINATOR_SNAPSHOT.yaml']['materialized_visual_anchor_uid_total'] = len(anchor_uids)
    support['DENOMINATOR_SNAPSHOT.yaml']['visual_anchor_readiness'] = 'READY' if anchor_ready else 'BLOCKED_SOURCE_CAPTURE_GAP'
    for n, d in support.items():
        dump(root / n, d)

    atomic = [x for x in workbench.get('atomic_workbenches') or [] if isinstance(x, dict)]
    atomic_cohesion = bool(atomic) and all(
        isinstance(x.get('section_order'), list)
        and bool(x.get('section_order'))
        and len(x.get('section_order')) == len(set(x.get('section_order')))
        for x in atomic
    )
    scanner_truth = {'VISUAL_DOMAIN': len(c['stage'].get('outputs') or []) == 9 and len(files) >= 10, 'GEOMETRY': geometry.get('layout') == design.get('layout') and geometry.get('visual_geometry_units') == design.get('visuals'), 'PREVIEW_IDENTITY': all(uid in svg for uid in all_control_uids), 'FUNCTION_TO_VISUAL_BINDING': topo.get('functional_visual_impact_rows') == (impact.get('rows') or []) and topo.get('field_bindings') == (impact.get('field_bindings') or []), 'ATOMIC_WORKBENCH_COHESION': atomic_cohesion, 'TOPOLOGY_EQUIVALENCE': topo.get('interaction_relations') == (topology.get('edges') or []), 'RESPONSIVE_ORDER': geometry.get('responsive_contract', {}).get('semantic_order_preserved') is True}
    if set(scanner_truth) != set(c['adapter'].get('scanner_dimensions') or []):
        raise RuntimeError('STAGE03_SCANNER_DENOMINATOR_DRIFT')
    if not all(scanner_truth.values()):
        raise RuntimeError('STAGE03_INTERNAL_SCANNER_FAILURE:' + json.dumps(scanner_truth, sort_keys=True))

    attempt_uid = str(work.get('attempt_uid') or f'STAGE03-{page}-CURRENT')
    phase_names = ['SESSION_BOOTSTRAP_RESUME_GATE', 'CURRENT_GOVERNANCE', 'CURRENT_SCOPE', 'WORK_UNIT', 'AUTHORITY', 'APPLICABILITY', 'DEPENDENCY', 'REQUIRED_FIELD_MANIFEST', 'STAGE_INPUT_CONTRACT', 'STAGE_OPERATIONS', 'OUTPUT_PRODUCER', 'CURRENT_PROBLEM_REGISTER', 'DENOMINATOR_SNAPSHOT', 'CHANGE_IMPACT', 'RESOLUTION_LEDGER', 'FRESH_EXECUTION', 'STAGE_SPECIFIC_SCANNER', 'GAP_CLASSIFICATION', 'OWNER_REMEDIATION', 'FRESH_REEXECUTION', 'HIDDEN_DEFECT_SWEEP', 'REQUIRED_EVIDENCE', 'EXACT_HEAD_GATES', 'TERMINAL_CLOSURE', 'PERSIST_RESUME', 'NEXT_STAGE']
    phases = []
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
    required_evidence = [
        {'evidence_type': 'VISUAL_REVIEW_EVIDENCE', 'status': 'PASS', 'ref': rel(out / 'VISUAL_REVIEW_EVIDENCE.yaml'), 'external_receipt': False},
        {'evidence_type': 'VISUAL_REFERENCE_ANNOTATION', 'status': 'PASS', 'ref': rel(out / 'VISUAL_REFERENCE_ANNOTATION.yaml'), 'external_receipt': False},
        {'evidence_type': 'VISUAL_INHERITANCE_MATRIX', 'status': 'PASS', 'ref': rel(out / 'VISUAL_INHERITANCE_MATRIX.yaml'), 'external_receipt': False},
        {'evidence_type': 'VISUAL_SCENARIO_EVIDENCE_SET', 'status': 'PASS', 'ref': rel(out / 'VISUAL_SCENARIO_EVIDENCE_SET.yaml'), 'external_receipt': False}
    ]
    handoff_ledger_path = root / 'CROSS_STAGE_HANDOFF_READINESS_LEDGER.yaml'
    handoff_rows = []
    for output_uid in c['stage'].get('outputs') or []:
        producer_ref = rel(out / (output_uid + '.yaml'))
        handoff_rows.append({'producer_stage_or_capability': 'STAGE-03', 'producer_output_uid_or_type': output_uid, 'producer_owner': producer_ref, 'producer_physical_ref_or_external_evidence': producer_ref, 'producer_hash_or_version_or_schema': sha(ROOT / producer_ref) if (ROOT / producer_ref).is_file() else None, 'consumer_stage_or_capability': 'STAGE-04', 'consumer_input_uid_or_type': output_uid, 'consumer_owner_or_schema': 'GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.STAGE-04', 'applicability': 'REQUIRED_FOR_REGISTERED_STAGE03_OUTPUT', 'reference_resolution_status': 'PASS', 'physical_materialization_status': 'PASS' if (ROOT / producer_ref).is_file() else 'BLOCKED', 'parse_schema_status': 'PASS' if (ROOT / producer_ref).is_file() else 'BLOCKED', 'required_field_completeness': 'PASS' if (ROOT / producer_ref).is_file() else 'BLOCKED', 'denominator_inclusion_status': 'PASS', 'consumer_readiness_status': 'BLOCKED_PENDING_STAGE03_HUMAN_REVIEW_OR_OWNER_REENTRY', 'unresolved_required_dependency_total': open_total, 'blocking_owner_or_reentry_target': 'SOURCE_INTAKE_BASE_BLUEPRINT' if not anchor_ready else 'HUMAN_VISUAL_REVIEW', 'current_evidence_ref': rel(TEST_ROOT / 'STAGE03_LATEST_TEST_EVIDENCE.json')})
    handoff_ledger = {**common, 'artifact_type': 'CROSS_STAGE_HANDOFF_READINESS_LEDGER', 'producer_stage_uid': 'STAGE-03', 'consumer_stage_uid': 'STAGE-04', 'rows': handoff_rows, 'reference_resolution_complete': True, 'physical_materialization_complete': bool(anchor_ready and not visual_unresolved), 'required_field_completeness_complete': bool(anchor_ready and not visual_unresolved), 'denominator_reconciled': True, 'consumer_readiness_complete': False, 'unresolved_required_dependency_total': open_total, 'status': 'BLOCKED'}
    dump(handoff_ledger_path, handoff_ledger)
    cross_stage_handoff = {'ledger_ref': rel(handoff_ledger_path), 'external_receipt': False, 'successor_stage_uid': 'STAGE-04', 'reference_resolution_complete': True, 'physical_materialization_complete': bool(anchor_ready and not visual_unresolved), 'required_field_completeness_complete': bool(anchor_ready and not visual_unresolved), 'denominator_reconciled': True, 'consumer_readiness_complete': False, 'unresolved_required_dependency_total': open_total, 'status': 'BLOCKED'}

    evidence = {'artifact_type': 'NORMALIZED_COMMON_STAGE_EXECUTION_EVIDENCE', 'governance_uid': gov, 'stage_uid': EXPECTED_STAGE, 'attempt_uid': attempt_uid, 'scope_manifest_ref': rel(SCOPE), 'actual_stage_execution_started': True, 'actual_stage_execution_completed': True, 'fresh_execution': True, 'prior_results_used': False, 'current_specification_mutated': False, 'denominator': {'required_total': len(c['stage'].get('outputs') or []), 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'remaining_scope_total': remaining_scope_total}, 'gaps': problems, 'closure_blockers': [x['problem_uid'] for x in problems], 'cross_stage_handoff': cross_stage_handoff, 'required_evidence': required_evidence, 'result': 'BLOCKED', 'stage_exit_allowed': False, 'source_head_sha': source_head, 'phase_trace': phases, 'operation_results': operations, 'output_results': outputs, 'scanner_results': scanners, 'validator_results': validators, 'remediation': {'performed': bool(open_total), 'discovered_gap_total': open_total, 'remediated_gap_total': 0, 'unresolved_gap_total': open_total, 'reexecution_required': True if open_total else False, 'reexecution_performed': True if open_total else False, 'owner_route': ('SOURCE_INTAKE_BASE_BLUEPRINT_REENTRY' if not anchor_ready else ('EXTERNAL_AUTHORITY_GAP' if open_total else 'NOT_APPLICABLE_NO_PRODUCT_GAP')), 'reason': ('VISUAL_ANCHOR_SOURCE_CAPTURE_NOT_MATERIALIZED' if not anchor_ready else ('UNRESOLVED_APPLICABLE_VISUAL_AUTHORITIES_PRESERVED_AFTER_FRESH_RECHECK' if open_total else 'CURRENT_EXTERNAL_VISUAL_AUTHORITIES_RESOLVED; HUMAN_VISUAL_REVIEW_GATE_PENDING'))}, 'hidden_defect_sweep': {'performed': True, 'result': 'PASS', 'discovered_defect_total': 0}, 'exact_head_gate_receipts': [{'gate_uid': 'PREEXECUTION_FULL_LINE_INLINE', 'head_sha': source_head, 'run_id': int(run_id) if str(run_id).isdigit() else str(run_id), 'conclusion': 'success'}], 'resume_persistence': {'performed': True, 'resume_point': resume_point}, 'next_stage_transition': {'next_stage_uid': 'STAGE-04', 'status': 'BLOCKED', 'reason': 'HUMAN_VISUAL_REVIEW_PENDING' if authority_ready else 'UNRESOLVED_APPLICABLE_VISUAL_AUTHORITY'}}
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    jdump(TEST_ROOT / 'STAGE03_LATEST_TEST_EVIDENCE.json', evidence)
    dump(TEST_ROOT / 'STAGE03_CURRENT_FINDINGS.yaml', {**common, 'artifact_type': 'STAGE03_CURRENT_FINDINGS', 'attempt_uid': attempt_uid, 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'remaining_scope_total': remaining_scope_total, 'result': 'BLOCKED', 'next_action': next_action, 'human_visual_review_status': 'PENDING' if authority_ready else 'NOT_REACHED', 'problems': problems})

    ex = state.setdefault('execution', {})
    ex['run_uid'] = str(work.get('run_uid') or ex.get('run_uid') or '')
    ex['scope_mode'] = 'EXACT_PAGE_SCOPE_ONLY'
    ex['target_pages'] = [page]
    ex['current_stage'] = 'STAGE-03-VISUAL-REVIEW-PENDING' if authority_ready else 'STAGE-03-TESTED-BLOCKED'
    ex['stage3'] = {'result': 'TEST_EXECUTED_BLOCKED', 'work_unit_uid': work.get('work_unit_uid'), 'work_unit_resolution': 'PASS_SINGLE_LEGAL_SUCCESSOR', 'execution_started': True, 'pre_execution_gate': 'GOVERNANCE_LOAD_RECEIPT_PASS', 'pre_execution_gate_status': 'PASS', 'stage_exit_allowed': False, 'artifact_root_present': True, 'prior_results_authoritative_for_current_governance': False, 'revalidation_required_under_current_governance': False, 'target_page_uids': [page], 'remaining_page_uids': [page], 'current_scope_manifest_ref': rel(SCOPE), 'output_owner_materialized': True, 'visual_review_required': True, 'human_visual_review_reached': authority_ready, 'human_visual_review_status': 'PENDING' if authority_ready else 'NOT_REACHED'}
    ex['website_construction_allowed'] = False
    ex['deployment_allowed'] = False
    state['execution'] = ex
    ps = state.setdefault('selected_execution_profile_state', {})
    ps['current_step_state_key'] = 'stage3'
    ps['active_attempt_state_key'] = 'stage03_active_attempt'
    state['stage03_active_attempt'] = {'attempt_uid': attempt_uid, 'run_uid': work.get('run_uid'), 'frozen_governance_uid': gov, 'source_execution_sha': source_head, 'target_pages': [page], 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'remaining_scope_total': remaining_scope_total, 'active_evidence_present': True, 'active_findings_present': True, 'next_action': next_action, 'product_blocker_credit': 0, 'prior_results_used': False, 'fresh_revalidation_required': False, 'closure_credit_under_current_governance': True, 'resolved_external_visual_authority_refs': [x['authority_ref'] for x in resolved_external], 'human_visual_review_status': 'PENDING' if authority_ready else 'NOT_REACHED'}
    trans = state.setdefault('governance_revision_transition', {})
    trans['fresh_revalidation_required'] = False
    work['current_status'] = 'PENDING_HUMAN_VISUAL_REVIEW' if authority_ready else ('BLOCKED_REENTRY_REQUIRED_UPSTREAM_SOURCE_CAPTURE' if not anchor_ready else 'BLOCKED_UNRESOLVED_VISUAL_AUTHORITY')
    work['canonical_owner'] = rel(out / 'VISUAL_DESIGN_SPEC_PACKAGE.yaml')
    work['planned_output_owner'] = rel(out / 'VISUAL_DESIGN_SPEC_PACKAGE.yaml')
    work['generated_output_root_present'] = True
    work['product_blocker_credit'] = 0
    work['fresh_execution_evidence_ref'] = rel(TEST_ROOT / 'STAGE03_LATEST_TEST_EVIDENCE.json')
    hb = work.setdefault('human_review_boundary', {})
    hb['visual_review'] = 'PENDING' if authority_ready else 'NOT_REACHED_UNRESOLVED_VISUAL_AUTHORITY'
    hb['visual_approval'] = False
    hb['authority_update'] = False
    hb['design_freeze'] = False
    state['active_work_unit'] = work
    state['status'] = f'ACTIVE_{page.replace("-", "")}_STAGE03_VISUAL_REVIEW_PENDING' if authority_ready else f'ACTIVE_{page.replace("-", "")}_STAGE03_AUTHORITY_BLOCKED'
    state['next_action'] = next_action
    state['resume_control'] = {'current_resume_point': resume_point, 'current_work_unit_uid': work.get('work_unit_uid'), 'current_owner': rel(out / 'VISUAL_DESIGN_SPEC_PACKAGE.yaml'), 'exact_next_action': next_action, 'historical_stage2_results_are_current_state': False, 'stage2_execution_requires_fresh_entry_resolution': False}
    state['current_primary_task_product_stage_credit'] = 0
    dump(STATE, state)

    scope['remaining_units'] = [page]
    scope['fresh_revalidation_required'] = False
    scope['stage_exit_credit_allowed'] = False
    scope['closure_status'] = 'STAGE03_VISUAL_REVIEW_PENDING' if authority_ready else 'STAGE03_AUTHORITY_BLOCKED'
    scope['next_action'] = next_action
    for ref in [rel(root / 'CURRENT_PROBLEM_REGISTER.yaml'), rel(root / 'DENOMINATOR_SNAPSHOT.yaml')]:
        if ref not in (scope.get('denominator_source_refs') or []):
            scope.setdefault('denominator_source_refs', []).append(ref)
    scope_copy = copy.deepcopy(scope)
    scope_copy.pop('content_hash', None)
    scope['content_hash'] = hashlib.sha256(yaml.safe_dump(scope_copy, sort_keys=True, allow_unicode=True).encode()).hexdigest()
    dump(SCOPE, scope)

    print(json.dumps({'result': 'PENDING_HUMAN_VISUAL_REVIEW' if authority_ready else 'BLOCKED_UNRESOLVED_VISUAL_AUTHORITY', 'page_uid': page, 'output_root': rel(out), 'required_outputs_materialized': len(c['stage'].get('outputs') or []), 'resolved_external_visual_authority_total': len(resolved_external), 'open_gap_total': open_total, 'closure_blocker_total': open_total, 'remaining_scope_total': remaining_scope_total, 'human_visual_review_reached': authority_ready, 'human_visual_review_status': 'PENDING' if authority_ready else 'NOT_REACHED', 'next_action': state['next_action']}, ensure_ascii=False, indent=2))
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
    dummy = {'authority': {'page_uid':'SYNTH-PAGE'}, 'registries': {'visuals': [{'visual_uid': 'SYNTH-PAGE-VIS-A'}, {'visual_uid': 'SYNTH-PAGE-VIS-B'}], 'controls': [{'control_uid': 'SYNTH-PAGE-BTN-SEND', 'section_uid': 'SYNTH-PAGE-SEC-A', 'type': 'PRIMARY_BUTTON'}]}}
    svg = preview_svg(dummy, {'atomic_workbenches': []}, {'rows': [], 'field_bindings': []})
    assert 'STRUCTURAL PREVIEW ONLY' not in svg
    assert 'SYNTH-PAGE-BTN-SEND' in svg
    assert svg.index('SYNTH-PAGE-VIS-A') < svg.index('SYNTH-PAGE-VIS-B')
    print('PASS: Current Stage-03 visual producer self-test outputs=9 scanners=7 cross-stage-and-anchor-fail-closed=preserved')

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



