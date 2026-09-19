from __future__ import annotations
import argparse, copy, hashlib, io, json, lzma, os, re, subprocess, sys, tarfile, zipfile
from pathlib import Path
import yaml

def replace_exact_once(text, old, new):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'BOUNDED_REPLACE_TARGET_COUNT expected=1 actual={count}')
    idx = text.index(old)
    return text[:idx] + new + text[idx + len(old):]
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.github/governance-source/active/source'
OLD_UID = 'GOV-REV-20260919-SEMANTIC-BASELINE-CONSUMER-SINGLE-OWNER-HARDENING'
NEW_UID = 'GOV-REV-20260919-BLUEPRINT-CONSTRUCTION-TRACEABILITY-HARDENING'
OLD_DISPLAY = 'v2.2.9'
NEW_DISPLAY = 'v2.2.10'
NEW_SOURCE_REV = 'v2.2.10-blueprint-construction-traceability-hardening'
AUTH_UID = 'USR-DIRECTIVE-20260919-BLUEPRINT-CONSTRUCTION-TRACEABILITY-HARDENING-R12'
NEW_PACKAGE = 'AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.10_BLUEPRINT_CONSTRUCTION_TRACEABILITY_HARDENING_LOCAL_VERIFIED.zip'
WORK_UNIT = 'WU-GOV-BLUEPRINT-CONSTRUCTION-TRACEABILITY-HARDENING-001'
SPECS = {'WEB-GOV-01-S076': ('76', '施工藍圖包完整度 Gate / Construction Blueprint Package Completeness', '\nEvery governed Page, Surface, Module, or Cross-page Flow MUST materialize one complete `CONSTRUCTION_BLUEPRINT_PACKAGE` before Design Freeze or implementation handoff. The package is a non-owning binding package: it MUST reference the separate Current `PAGE_BASE_BLUEPRINT`, `VISUAL_BASE_BLUEPRINT`, functional-contract owners, and visual-design owners; it MUST_NOT become a second editable Page/Visual Authority.\n\nThe applicable package MUST contain, or bind by exact UID/hash to, at least:\n\n1. Current Truth / Source Map and Requirement / Problem Definition.\n2. `BUSINESS_ENTITY_INVENTORY`, `BUSINESS_ENTITY_OPERATION_MATRIX`, and `ENTITY_HIERARCHY_MATRIX`.\n3. User Journey Registry, `FUNCTIONAL_WORKBENCH_CONTRACT`, `INTERACTION_TOPOLOGY_MATRIX`, and conditional AI interaction continuity contract when applicable.\n4. Complete Functional Chain and every applicable Cross-page Flow Contract.\n5. Page Design, Section Registry, Component Registry, and Control / Field / Action / Gate / Permission binding.\n6. State / Transition / Error / Recovery contract and Data Object Binding.\n7. `FUNCTION_VISUAL_IMPACT_MATRIX`, Visual Anchor Registry, Visual Generation Manifest, and required Visual Candidates.\n8. `CONSTRUCTION_DELTA_MATRIX` against the existing implementation when any implementation already exists.\n9. Pre-Implementation Guards, Implementation Handoff, Acceptance Matrix, Audit Baseline, Definition of Done, and Resume / Next Step.\n\nEvery item MUST declare `REQUIRED`, `OPTIONAL`, or `NOT_APPLICABLE`; `NOT_APPLICABLE` requires Authority evidence. A missing applicable item is `BLUEPRINT_PACKAGE_INCOMPLETE` and MUST block Design Freeze and implementation.\n'), 'WEB-GOV-01-S077': ('77', '功能與視覺雙向追溯 Gate / Functional-Visual Bidirectional Traceability', '\nEvery user-visible or user-observable REQUIRED function MUST resolve the exact forward trace:\n\n`Business Entity -> Operation -> Journey -> Functional Workbench -> Section -> Component -> Control/System Trigger -> Field/Input -> State -> Visual Anchor -> Visual Candidate -> Implementation Target -> Acceptance Item`.\n\nThe reverse trace is also REQUIRED for every visible interactive or state-bearing visual element. Each Card, Panel, Tab, Button, Input, Selector, Badge, Drawer, Modal, Timeline, Conversation Surface, State Rail, Status Strip, and equivalent element MUST resolve backward to one governed Business Entity operation or registered non-entity utility operation.\n\nA visible element without such backward ownership is `ORPHAN_VISUAL_ELEMENT` and MUST block approval. A required user-observable function without a visual/state binding is `MISSING_VISUAL_BINDING` and MUST block approval unless Current Authority explicitly classifies it as `NON_VISUAL_SYSTEM_FUNCTION`.\n\nVisual Design MUST preserve the approved Functional Workbench and Interaction Topology. Geometry MAY change within the approved design system and Change Set, but arbitrary visual regrouping, reordering, detaching, or separating operations from their required context is forbidden.\n'), 'WEB-GOV-01-S078': ('78', '強制多情境視覺證據集 / Mandatory Multi-State Visual Evidence Set', '\nVisual Preview MUST cover the actual interaction states required by the Page Complexity Profile and approved journeys; one attractive overview image is insufficient.\n\nThe applicability set MUST evaluate at least:\n\n- `CANONICAL_WORKSPACE_OVERVIEW`: complete desktop work area showing shell relationship, information hierarchy, primary workbench, primary actions, and next-step surface.\n- `INTERACTION_TOPOLOGY_DIAGRAM`: REQUIRED for complex, contiguous, multi-step, conditional, or cross-surface journeys.\n- `INITIAL_OR_EMPTY_STATE`: REQUIRED when the scope has create/select/empty prerequisites.\n- `ACTIVE_WORKING_STATE`: REQUIRED for every interactive workbench.\n- `COMPLEX_OR_CONDITIONAL_STATE`: REQUIRED when multi-agent, compare, correction, layer, provider/async, branch, review, or equivalent conditional behavior exists.\n- `FINALIZATION_OR_CONFIRMATION_STATE`: REQUIRED when candidate, approval, confirmation, version, lock, publish, or handoff exists.\n- `ERROR_BLOCKED_RECOVERY_STATE`: REQUIRED when a user-visible error, blocked gate, retry, rollback, or recovery path exists.\n- `CROSS_PAGE_HANDOFF_DIAGRAM`: REQUIRED for P4 or any flow whose output becomes another Page/Module input.\n\nEvery required visual MUST target actual website structure, not a moodboard. All visuals for one Page MUST use the same approved Layout, Design Tokens, Visual Anchors, and Functional Topology unless an authorized Change Set explicitly changes them.\n'), 'WEB-GOV-01-S079': ('79', '視覺參考註解合約 / Visual Reference Annotation Contract', '\nEvery Visual Candidate MUST carry a machine- and human-readable annotation record containing at least:\n\n- Visual UID, Page/Scope UID, Scenario UID, State UID, Workbench UID, Journey UID.\n- Parent Visual UID, Design Version, Change Set UID, Viewport, Language, Theme.\n- Applicable Business Entity / Operation.\n- Visible Sections and Conditional Sections.\n- Locked Regions and Editable Regions.\n- Visual Anchor UIDs.\n- Primary Controls and Disabled/Blocked Controls with reason source.\n- Current Next Action / Next Gate.\n- Source Authority references and Authority classification.\n- A concise `verification_purpose` stating exactly what product behavior/state the visual proves.\n\nAn image without the required annotation MUST_NOT satisfy Visual Preview, Visual Review, Canonical Visual, Design Freeze, or implementation handoff.\n'), 'WEB-GOV-01-S080': ('80', '施工差異與既有實作缺口 Gate / Construction Delta and Existing Implementation Gap', '\nBefore implementation begins, approved required design MUST be compared against the existing implementation whenever code, runtime, data schema, UI, route, or other prior construction exists. The result MUST materialize one `CONSTRUCTION_DELTA_MATRIX`.\n\nEach delta row MUST include at least: Requirement UID; Business Entity / Operation; Current Program Artifact or Code Owner; Current path/identity; Existing Status; Required Disposition; Required Change; Authority Ref; Functional Impact; Visual Impact; API/Runtime/Data Impact; Permission Impact; State Impact; Cross-page Impact; Required Test/Audit; Construction Owner; Blocking State; downstream `REVERIFY_REQUIRED` impact.\n\n`Existing Status` MUST use a governed class such as `EXISTS`, `PARTIAL`, `MISSING`, `WRONG_BINDING`, `OBSOLETE`, or `DUPLICATE`. `Required Disposition` MUST use an exact class such as `KEEP`, `MODIFY`, `REMOVE`, `MERGE`, `REBIND`, or `ADD`.\n\nAn already-auditable construction deficiency MUST be classified before implementation; it MUST_NOT be deferred until downstream testing merely because the current code compiles or a control visually exists. Unknown or ambiguous product behavior remains an Authority Gap and MUST_NOT be guessed through the Delta Matrix.\n'), 'WEB-GOV-01-S081': ('81', '情境對功能視覺覆蓋 Gate / Scenario-to-Function Visual Coverage', '\nEvery critical Journey step, legal state transition, decision branch, permission-disabled state, asynchronous pending state, finalization state, and registered recovery branch MUST have explicit visual coverage when user-visible or user-observable.\n\nCoverage MUST be computed from the approved Required Journey/State denominator, not from the number of screenshots produced. Each required scenario MUST map to exact Workbench, Function/Operation, State, Controls, Visual Anchors, and Acceptance Items. Multiple scenarios MAY share one visual only when the annotation proves all required states are simultaneously and unambiguously represented.\n\nA visual scenario that changes layout topology, control ownership, semantic order, context identity, or next-step placement without an approved upstream contract/change set is `VISUAL_SCENARIO_DRIFT` and MUST block approval.\n'), 'WEB-GOV-01-S082': ('82', '量化 Design Freeze 完整度 Gate / Quantitative Design Freeze Completeness', '\n`DESIGN_FROZEN` MUST require machine-checkable completeness for every applicable denominator. At minimum:\n\n- Required Business Entity Operation coverage = 100%.\n- Required Functional Chain coverage = 100%.\n- Required Function -> Visual binding coverage = 100%.\n- Visible Visual Element -> Function/Utility binding coverage = 100%.\n- Required State/Scenario Visual coverage = 100%.\n- Required Cross-page Flow coverage = 100%.\n- Construction Delta classification = 100% when prior implementation exists.\n- Required Acceptance Item definition = 100%.\n- Orphan Visual Element count = 0.\n- Unbound Control count = 0.\n- Unbound Field count = 0.\n- Undefined Next Step count = 0.\n- Missing required Recovery Path count = 0.\n- Missing required Visual Candidate count = 0.\n\nA percentage MUST_NOT hide an unresolved `AUTHORITY_GAP`, `AUTHORITY_CONFLICT`, missing Current owner, or intentionally fail-closed condition. One overview screenshot, one mockup, or one successful visual review item MUST_NOT substitute for the complete denominator.\n'), 'WEB-GOV-01-S083': ('83', '藍圖至施工交接合約 / Blueprint-to-Implementation Handoff Contract', '\nBefore implementation, the Design Freeze Package MUST materialize one exact `BLUEPRINT_IMPLEMENTATION_HANDOFF` binding: frozen artifact UIDs/hashes; Construction Delta rows; Program Artifact/Construction owner; implementation dependency order; visual reference UIDs; required Workbench/Topology; state/gate/permission behavior; payload/input contracts; error/recovery behavior; acceptance/audit refs; and re-entry/rollback conditions.\n\nImplementation MAY construct only the frozen and approved requirements/deltas in this handoff. Discovery of a new Business Entity, operation, permission model, persistence owner, external dependency, visual interaction pattern, or topology change outside the frozen handoff MUST stop downstream implementation and reopen the owning capability.\n\nThe handoff MUST preserve bidirectional traceability from approved design to implementation target and from implementation target back to the exact approved Requirement/Operation/Visual/Acceptance identities. A code artifact that cannot resolve both directions is not handoff-complete.\n')}

def run(*args, check=True, env=None):
    cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, env=env)
    if check and cp.returncode:
        print(cp.stdout)
        print(cp.stderr, file=sys.stderr)
        raise SystemExit(cp.returncode)
    return cp

def load(path):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}

def dump(path, obj):
    Path(path).write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def hobj(d):
    x = copy.deepcopy(d)
    x.pop('content_hash', None)
    return hashlib.sha256(yaml.safe_dump(x, allow_unicode=True, sort_keys=True, width=180).encode()).hexdigest()

def append_once(path, marker, text):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    if marker not in s:
        p.write_text(s.rstrip() + '\n\n' + text.strip() + '\n', encoding='utf-8')

def insert_before_anchor(path, anchor, text):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    marker = text.strip().splitlines()[0]
    if marker in s:
        return
    if anchor not in s:
        raise RuntimeError('anchor missing ' + anchor)
    p.write_text(replace_exact_once(s, anchor, text.strip() + '\n\n' + anchor), encoding='utf-8')

def unique_extend(lst, items):
    for x in items:
        if x not in lst:
            lst.append(x)

def replace_const(path, name, value):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    pat = re.compile(f"(?m)^{re.escape(name)}\\s*=\\s*'[^']*'$")
    ns, n = pat.subn(f"{name} = '{value}'", s, 1)
    if n != 1:
        raise RuntimeError(f'constant {name} replacement count={n} in {path}')
    p.write_text(ns, encoding='utf-8')

def section_binding(uid, doc_id, path, heading):
    return hashlib.sha256(f'{uid}\n{doc_id}\n{path}\n{heading}\n'.encode()).hexdigest()

def mutate_mother():
    p = SOURCE / '12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'
    body = []
    for uid, (num, title, text) in SPECS.items():
        body.append(f'<!-- SECTION_UID: {uid} -->\n## {num}. {title}\n\n{text.strip()}')
    append_once(p, '<!-- SECTION_UID: WEB-GOV-01-S076 -->', '\n\n'.join(body))
    insert_before_anchor(SOURCE / '12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md', '<!-- SECTION_UID: WEB-GOV-02-S072 -->', '### Blueprint package / construction delta consumption hardening\n\nImplementation MUST consume the frozen `CONSTRUCTION_BLUEPRINT_PACKAGE`, `CONSTRUCTION_DELTA_MATRIX`, required annotated Visual Candidates, and `BLUEPRINT_IMPLEMENTATION_HANDOFF` produced by the design/freeze owners. A visible element, code artifact, handler, runtime path, or state projection without bidirectional Requirement/Operation/Visual/Acceptance traceability is an implementation defect. Existing code marked `PARTIAL`, `WRONG_BINDING`, `OBSOLETE`, or `DUPLICATE` MUST follow the exact frozen disposition; implementation MUST_NOT preserve it merely because it already exists.\n\nImplementation MUST_NOT substitute an arbitrary UI layout for the approved Workbench/Interaction Topology. If code reality exposes a new required delta outside the frozen handoff, execution MUST re-enter the owning design capability rather than silently expanding implementation.')
    insert_before_anchor(SOURCE / '12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md', '<!-- SECTION_UID: WEB-GOV-04-S078 -->', '### Blueprint construction traceability / visual evidence audit hardening\n\nAudit MUST verify the applicable `CONSTRUCTION_BLUEPRINT_PACKAGE` is complete and non-owning, preserves separate Page/Visual Authorities, and binds every REQUIRED function bidirectionally through Entity/Operation/Journey/Workbench/Section/Component/Control-or-Trigger/Field-or-Input/State/Visual Anchor/Visual Candidate/Implementation Target/Acceptance Item.\n\nAudit MUST verify required multi-state visual scenarios and annotations, zero orphan visual elements, zero unbound required controls/fields, complete required state/recovery/cross-page visual coverage, complete `CONSTRUCTION_DELTA_MATRIX` classification when prior implementation exists, quantitative Design Freeze denominators, and an exact Blueprint-to-Implementation Handoff. A visually attractive overview without these bindings MUST_NOT PASS.')

def mutate_section_registry():
    p = SOURCE / '10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
    d = load(p)
    doc = next((x for x in d.get('documents', []) if x.get('document_id') == 'WEB-GOV-01'), None)
    if not doc:
        raise RuntimeError('WEB-GOV-01 document missing')
    existing = {x.get('section_uid') for x in doc.get('sections', [])}
    rel = '12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'
    for uid, (num, title, _) in SPECS.items():
        if uid in existing:
            continue
        heading = f'## {num}. {title}'
        doc.setdefault('sections', []).append({'section_uid': uid, 'level': 2, 'canonical_number': num, 'title': title, 'heading': heading, 'path': rel, 'binding_sha256': section_binding(uid, 'WEB-GOV-01', rel, heading)})
    if 'governance_revision' in d:
        d['governance_revision'] = NEW_SOURCE_REV
    dump(p, d)

def mutate_stage_and_semantic():
    stage_add = {'STAGE-02': ['WEB-GOV-01-S077'], 'STAGE-03': ['WEB-GOV-01-S077', 'WEB-GOV-01-S078', 'WEB-GOV-01-S079', 'WEB-GOV-01-S081'], 'STAGE-04': ['WEB-GOV-01-S076', 'WEB-GOV-01-S077', 'WEB-GOV-01-S080', 'WEB-GOV-01-S081', 'WEB-GOV-01-S082', 'WEB-GOV-01-S083'], 'STAGE-05': ['WEB-GOV-01-S080', 'WEB-GOV-01-S083']}
    lp = SOURCE / '10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
    life = load(lp)
    for st in life.get('stages', []):
        unique_extend(st.setdefault('required_normative_section_uids', []), stage_add.get(st.get('stage_uid'), []))
    cross = life.setdefault('cross_stage_invariants', {}).setdefault('stage_execution_invariant_hardening', {})
    for k in ['construction_blueprint_package_required_before_freeze_and_implementation', 'function_visual_bidirectional_traceability_required', 'mandatory_multi_state_visual_evidence_required_when_applicable', 'visual_reference_annotation_required', 'construction_delta_matrix_required_when_prior_implementation_exists', 'scenario_to_function_visual_coverage_required', 'quantitative_design_freeze_completeness_required', 'blueprint_to_implementation_handoff_required']:
        cross[k] = True
    if 'governance_revision' in life:
        life['governance_revision'] = NEW_SOURCE_REV
    dump(lp, life)
    rp = SOURCE / '10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'
    ref = load(rp)
    for uid, items in stage_add.items():
        unique_extend(ref['stage_reference_rules'][uid]['exact_required_normative_section_uids'], items)
    if 'governance_revision' in ref:
        ref['governance_revision'] = NEW_SOURCE_REV
    dump(rp, ref)
    sp = SOURCE / '10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    sem = load(sp)
    for uid, items in stage_add.items():
        unique_extend(sem['semantic_snapshot']['stage_reference_rules'][uid]['exact_required_normative_section_uids'], items)
    sem['governance_revision'] = NEW_SOURCE_REV
    sem['content_hash'] = hobj(sem)
    dump(sp, sem)
    return sem['content_hash']

def mutate_invariant_registry():
    p = SOURCE / '10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
    d = load(p)
    inv = d.setdefault('invariants', {})
    inv['CONSTRUCTION_BLUEPRINT_PACKAGE_COMPLETENESS'] = {'required_artifact': 'CONSTRUCTION_BLUEPRINT_PACKAGE', 'package_is_non_owning_binding': True, 'separate_page_and_visual_authority_preserved': True, 'required_domain_bindings': ['CURRENT_TRUTH_SOURCE_MAP', 'REQUIREMENT_PROBLEM_DEFINITION', 'BUSINESS_ENTITY_INVENTORY', 'BUSINESS_ENTITY_OPERATION_MATRIX', 'ENTITY_HIERARCHY_MATRIX', 'USER_JOURNEY_REGISTRY', 'FUNCTIONAL_WORKBENCH_CONTRACT', 'INTERACTION_TOPOLOGY_MATRIX', 'FUNCTIONAL_CHAIN', 'CROSS_PAGE_FLOW_WHEN_APPLICABLE', 'PAGE_DESIGN', 'SECTION_COMPONENT_REGISTRY', 'CONTROL_FIELD_ACTION_GATE_PERMISSION_BINDING', 'STATE_TRANSITION_ERROR_RECOVERY', 'DATA_OBJECT_BINDING', 'FUNCTION_VISUAL_IMPACT_MATRIX', 'VISUAL_ANCHOR_REGISTRY', 'VISUAL_GENERATION_MANIFEST', 'VISUAL_CANDIDATES', 'CONSTRUCTION_DELTA_MATRIX_WHEN_PRIOR_IMPLEMENTATION_EXISTS', 'PRE_IMPLEMENTATION_GUARDS', 'BLUEPRINT_IMPLEMENTATION_HANDOFF', 'ACCEPTANCE_MATRIX', 'AUDIT_BASELINE', 'DEFINITION_OF_DONE', 'RESUME_NEXT_STEP'], 'missing_applicable_package_item': 'BLUEPRINT_PACKAGE_INCOMPLETE', 'implementation_before_complete_package': 'BLOCK'}
    inv['FUNCTION_VISUAL_BIDIRECTIONAL_TRACEABILITY'] = {'required_forward_trace': ['BUSINESS_ENTITY', 'OPERATION', 'JOURNEY', 'FUNCTIONAL_WORKBENCH', 'SECTION', 'COMPONENT', 'CONTROL_OR_SYSTEM_TRIGGER', 'FIELD_OR_INPUT', 'STATE', 'VISUAL_ANCHOR', 'VISUAL_CANDIDATE', 'IMPLEMENTATION_TARGET', 'ACCEPTANCE_ITEM'], 'reverse_trace_required_for_visible_interactive_or_state_bearing_elements': True, 'orphan_visual_element': 'BLOCK', 'required_user_observable_function_without_visual_binding': 'BLOCK', 'non_visual_system_function_requires_authority': True, 'arbitrary_visual_topology_change': 'BLOCK'}
    inv['MANDATORY_MULTI_STATE_VISUAL_EVIDENCE'] = {'required_artifact': 'VISUAL_SCENARIO_EVIDENCE_SET', 'scenario_universe': ['CANONICAL_WORKSPACE_OVERVIEW', 'INTERACTION_TOPOLOGY_DIAGRAM', 'INITIAL_OR_EMPTY_STATE', 'ACTIVE_WORKING_STATE', 'COMPLEX_OR_CONDITIONAL_STATE', 'FINALIZATION_OR_CONFIRMATION_STATE', 'ERROR_BLOCKED_RECOVERY_STATE', 'CROSS_PAGE_HANDOFF_DIAGRAM'], 'applicability_required': True, 'moodboard_may_satisfy_actual_structure_preview': False, 'missing_required_scenario': 'BLOCK', 'same_layout_tokens_anchors_topology_required_unless_change_set': True}
    inv['VISUAL_REFERENCE_ANNOTATION'] = {'required_artifact': 'VISUAL_REFERENCE_ANNOTATION', 'required_fields': ['visual_uid', 'page_or_scope_uid', 'scenario_uid', 'state_uid', 'workbench_uid', 'journey_uid', 'parent_visual_uid', 'design_version', 'change_set_uid', 'viewport', 'language', 'theme', 'applicable_entity_operation', 'visible_sections', 'conditional_sections', 'locked_regions', 'editable_regions', 'visual_anchor_uids', 'primary_controls', 'disabled_or_blocked_controls', 'next_action_or_gate', 'source_authority_refs', 'authority_classification', 'verification_purpose'], 'unannotated_visual_may_pass_visual_review': False}
    inv['CONSTRUCTION_DELTA_EXISTING_IMPLEMENTATION'] = {'required_artifact': 'CONSTRUCTION_DELTA_MATRIX', 'activation': 'PRIOR_IMPLEMENTATION_EXISTS', 'existing_status_universe': ['EXISTS', 'PARTIAL', 'MISSING', 'WRONG_BINDING', 'OBSOLETE', 'DUPLICATE'], 'required_disposition_universe': ['KEEP', 'MODIFY', 'REMOVE', 'MERGE', 'REBIND', 'ADD'], 'required_fields': ['requirement_uid', 'business_entity_operation', 'current_program_artifact_or_code_owner', 'current_path_or_identity', 'existing_status', 'required_disposition', 'required_change', 'authority_ref', 'functional_impact', 'visual_impact', 'api_runtime_data_impact', 'permission_impact', 'state_impact', 'cross_page_impact', 'required_test_or_audit', 'construction_owner', 'blocking_state', 'downstream_reverify_impact'], 'already_auditable_gap_deferred_until_downstream_test': 'BLOCK', 'ambiguous_product_behavior_autofill': 'BLOCK'}
    inv['SCENARIO_TO_FUNCTION_VISUAL_COVERAGE'] = {'denominator': 'APPROVED_REQUIRED_JOURNEY_STATE_BRANCH_SET', 'required_mapping': ['WORKBENCH', 'FUNCTION_OR_OPERATION', 'STATE', 'CONTROLS', 'VISUAL_ANCHORS', 'ACCEPTANCE_ITEMS'], 'required_coverage_percent': 100, 'visual_scenario_drift': 'BLOCK'}
    inv['DESIGN_FREEZE_QUANTITATIVE_COMPLETENESS'] = {'required_percent_fields': {'business_entity_operation_coverage': 100, 'functional_chain_coverage': 100, 'function_to_visual_binding_coverage': 100, 'visible_visual_to_function_binding_coverage': 100, 'required_state_scenario_visual_coverage': 100, 'cross_page_flow_coverage': 100, 'construction_delta_classification_when_applicable': 100, 'required_acceptance_item_definition': 100}, 'required_zero_fields': ['orphan_visual_element_count', 'unbound_control_count', 'unbound_field_count', 'undefined_next_step_count', 'missing_required_recovery_path_count', 'missing_required_visual_candidate_count'], 'authority_gap_may_be_hidden_by_percentage': False, 'single_overview_visual_may_substitute_denominator': False}
    inv['BLUEPRINT_TO_IMPLEMENTATION_HANDOFF'] = {'required_artifact': 'BLUEPRINT_IMPLEMENTATION_HANDOFF', 'required_fields': ['frozen_artifact_uids_hashes', 'construction_delta_rows', 'program_artifact_or_construction_owner', 'implementation_dependency_order', 'visual_reference_uids', 'functional_workbench_and_topology_refs', 'state_gate_permission_behavior', 'payload_input_contracts', 'error_recovery_behavior', 'acceptance_audit_refs', 'reentry_rollback_conditions'], 'implementation_outside_frozen_handoff': 'BLOCK_AND_REOPEN_OWNING_CAPABILITY', 'bidirectional_design_to_code_traceability_required': True}
    if 'governance_revision' in d:
        d['governance_revision'] = NEW_SOURCE_REV
    dump(p, d)

def mutate_blueprint_acceptance_index():
    bp = SOURCE / '10_REGISTRY/BLUEPRINT_REGISTRY.yaml'
    d = load(bp)
    unique_extend(d.setdefault('normative_section_uids', []), list(SPECS))
    if not any((x.get('blueprint_type') == 'CONSTRUCTION_BLUEPRINT_PACKAGE' for x in d.get('blueprint_types', []))):
        d.setdefault('blueprint_types', []).append({'blueprint_type': 'CONSTRUCTION_BLUEPRINT_PACKAGE', 'planning_domain': 'NON_OWNING_BINDING', 'created_stage_uid': 'STAGE-04', 'owner_mode': 'BINDING_ONLY', 'blueprint_type_uid': 'BPTYPE-GOV-007'})
    d['governance_revision'] = NEW_SOURCE_REV
    dump(bp, d)
    ap = SOURCE / '10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
    a = load(ap)
    c = a.setdefault('product_neutral_entity_lifecycle_contract', {})
    for k in ['construction_blueprint_package_required', 'function_visual_bidirectional_traceability_required', 'mandatory_multi_state_visual_evidence_required', 'visual_reference_annotation_required', 'construction_delta_matrix_required_when_prior_implementation_exists', 'scenario_to_function_visual_coverage_required', 'quantitative_design_freeze_completeness_required', 'blueprint_to_implementation_handoff_required', 'orphan_visual_element_zero_required', 'unbound_control_zero_required', 'unbound_field_zero_required', 'undefined_next_step_zero_required', 'missing_recovery_path_zero_required', 'required_visual_candidate_missing_zero_required']:
        c[k] = True
    c['arbitrary_visual_layout_without_topology_binding'] = 'BLOCK'
    unique_extend(a.setdefault('normative_section_uids', []), list(SPECS))
    a['governance_revision'] = NEW_SOURCE_REV
    dump(ap, a)
    catp = SOURCE / '10_REGISTRY/AUDIT_CATALOG.yaml'
    cat = load(catp)
    unique_extend(cat.setdefault('normative_section_uids', []), list(SPECS))
    for item in cat.get('items', []):
        if item.get('audit_item_uid') == 'AUD-GOV-013':
            unique_extend(item.setdefault('coverage_extensions', []), ['CONSTRUCTION_BLUEPRINT_PACKAGE_COMPLETENESS', 'FUNCTION_VISUAL_BIDIRECTIONAL_TRACEABILITY', 'MANDATORY_MULTI_STATE_VISUAL_EVIDENCE', 'VISUAL_REFERENCE_ANNOTATION', 'CONSTRUCTION_DELTA_EXISTING_IMPLEMENTATION', 'SCENARIO_TO_FUNCTION_VISUAL_COVERAGE', 'DESIGN_FREEZE_QUANTITATIVE_COMPLETENESS', 'BLUEPRINT_TO_IMPLEMENTATION_HANDOFF'])
    cat['governance_revision'] = NEW_SOURCE_REV
    dump(catp, cat)
    ip = SOURCE / '10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
    idx = load(ip)
    u = idx.setdefault('universal_rules', {})
    for k in ['construction_blueprint_package_incomplete', 'function_visual_traceability_missing', 'orphan_visual_element', 'required_visual_scenario_missing', 'unannotated_visual_candidate', 'construction_delta_unclassified', 'design_freeze_quantitative_coverage_incomplete', 'blueprint_handoff_unbound', 'arbitrary_visual_layout_without_functional_topology_binding']:
        u[k] = 'BLOCK'
    idx['governance_revision'] = NEW_SOURCE_REV
    dump(ip, idx)

def harden_validator():
    p = SOURCE / '09_TESTS/governance/validate_product_neutral_entity_lifecycle.py'
    s = p.read_text(encoding='utf-8')
    if 'construction_blueprint_package_contract_missing' in s:
        return
    marker = "    return {'status':'PASS' if not failures else 'FAIL'"
    block = "\n    cb=inv.get('CONSTRUCTION_BLUEPRINT_PACKAGE_COMPLETENESS') or {}\n    if cb.get('required_artifact')!='CONSTRUCTION_BLUEPRINT_PACKAGE' or cb.get('package_is_non_owning_binding') is not True or cb.get('separate_page_and_visual_authority_preserved') is not True: failures.append('construction_blueprint_package_contract_missing')\n    if cb.get('missing_applicable_package_item')!='BLUEPRINT_PACKAGE_INCOMPLETE' or cb.get('implementation_before_complete_package')!='BLOCK': failures.append('construction_blueprint_package_fail_closed_invalid')\n    fv=inv.get('FUNCTION_VISUAL_BIDIRECTIONAL_TRACEABILITY') or {}\n    if fv.get('reverse_trace_required_for_visible_interactive_or_state_bearing_elements') is not True or fv.get('orphan_visual_element')!='BLOCK' or fv.get('required_user_observable_function_without_visual_binding')!='BLOCK' or fv.get('arbitrary_visual_topology_change')!='BLOCK': failures.append('function_visual_bidirectional_traceability_invalid')\n    mv=inv.get('MANDATORY_MULTI_STATE_VISUAL_EVIDENCE') or {}\n    required_scenarios={'CANONICAL_WORKSPACE_OVERVIEW','INTERACTION_TOPOLOGY_DIAGRAM','INITIAL_OR_EMPTY_STATE','ACTIVE_WORKING_STATE','COMPLEX_OR_CONDITIONAL_STATE','FINALIZATION_OR_CONFIRMATION_STATE','ERROR_BLOCKED_RECOVERY_STATE','CROSS_PAGE_HANDOFF_DIAGRAM'}\n    if mv.get('required_artifact')!='VISUAL_SCENARIO_EVIDENCE_SET' or set(mv.get('scenario_universe') or [])!=required_scenarios or mv.get('applicability_required') is not True or mv.get('missing_required_scenario')!='BLOCK': failures.append('multi_state_visual_evidence_contract_invalid')\n    va=inv.get('VISUAL_REFERENCE_ANNOTATION') or {}\n    if va.get('required_artifact')!='VISUAL_REFERENCE_ANNOTATION' or va.get('unannotated_visual_may_pass_visual_review') is not False or 'verification_purpose' not in (va.get('required_fields') or []): failures.append('visual_reference_annotation_contract_invalid')\n    cd=inv.get('CONSTRUCTION_DELTA_EXISTING_IMPLEMENTATION') or {}\n    if cd.get('required_artifact')!='CONSTRUCTION_DELTA_MATRIX' or cd.get('activation')!='PRIOR_IMPLEMENTATION_EXISTS' or cd.get('already_auditable_gap_deferred_until_downstream_test')!='BLOCK' or cd.get('ambiguous_product_behavior_autofill')!='BLOCK': failures.append('construction_delta_contract_invalid')\n    sv=inv.get('SCENARIO_TO_FUNCTION_VISUAL_COVERAGE') or {}\n    if sv.get('denominator')!='APPROVED_REQUIRED_JOURNEY_STATE_BRANCH_SET' or int(sv.get('required_coverage_percent',0))!=100 or sv.get('visual_scenario_drift')!='BLOCK': failures.append('scenario_visual_coverage_contract_invalid')\n    df=inv.get('DESIGN_FREEZE_QUANTITATIVE_COMPLETENESS') or {}\n    if any(int(v)!=100 for v in (df.get('required_percent_fields') or {}).values()) or len(df.get('required_zero_fields') or [])<6 or df.get('authority_gap_may_be_hidden_by_percentage') is not False or df.get('single_overview_visual_may_substitute_denominator') is not False: failures.append('quantitative_design_freeze_contract_invalid')\n    bh=inv.get('BLUEPRINT_TO_IMPLEMENTATION_HANDOFF') or {}\n    if bh.get('required_artifact')!='BLUEPRINT_IMPLEMENTATION_HANDOFF' or bh.get('implementation_outside_frozen_handoff')!='BLOCK_AND_REOPEN_OWNING_CAPABILITY' or bh.get('bidirectional_design_to_code_traceability_required') is not True: failures.append('blueprint_implementation_handoff_contract_invalid')\n    for k in ['construction_blueprint_package_required','function_visual_bidirectional_traceability_required','mandatory_multi_state_visual_evidence_required','visual_reference_annotation_required','construction_delta_matrix_required_when_prior_implementation_exists','scenario_to_function_visual_coverage_required','quantitative_design_freeze_completeness_required','blueprint_to_implementation_handoff_required','orphan_visual_element_zero_required','unbound_control_zero_required','unbound_field_zero_required','undefined_next_step_zero_required','missing_recovery_path_zero_required','required_visual_candidate_missing_zero_required']:\n        if c.get(k) is not True: failures.append('acceptance_blueprint_traceability_rule_missing:'+k)\n    if c.get('arbitrary_visual_layout_without_topology_binding')!='BLOCK': failures.append('acceptance_arbitrary_visual_layout_not_blocked')\n    for k in ['construction_blueprint_package_incomplete','function_visual_traceability_missing','orphan_visual_element','required_visual_scenario_missing','unannotated_visual_candidate','construction_delta_unclassified','design_freeze_quantitative_coverage_incomplete','blueprint_handoff_unbound','arbitrary_visual_layout_without_functional_topology_binding']:\n        if ur.get(k)!='BLOCK': failures.append('construction_blueprint_traceability_rule_not_block:'+k)\n    for uid in ['WEB-GOV-01-S076','WEB-GOV-01-S077','WEB-GOV-01-S078','WEB-GOV-01-S079','WEB-GOV-01-S080','WEB-GOV-01-S081','WEB-GOV-01-S082','WEB-GOV-01-S083']:\n        if uid not in (root/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md').read_text(encoding='utf-8'): failures.append('mother_blueprint_traceability_section_missing:'+uid)\n"
    if marker not in s:
        raise RuntimeError('validator return marker missing')
    p.write_text(replace_exact_once(s, marker, block + '\n' + marker), encoding='utf-8')

def mutate_current_components():
    p = ROOT / 'governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml'
    d = load(p)
    rules = d.setdefault('rules', {})
    rules['CONSTRUCTION_BLUEPRINT_PACKAGE_COMPLETENESS'] = {'required_artifact': 'CONSTRUCTION_BLUEPRINT_PACKAGE', 'package_is_non_owning_binding': True, 'missing_applicable_item': 'BLUEPRINT_PACKAGE_INCOMPLETE', 'implementation_before_complete_package': 'BLOCK'}
    rules['CONSTRUCTION_DELTA_EXISTING_IMPLEMENTATION'] = {'required_artifact': 'CONSTRUCTION_DELTA_MATRIX', 'activation': 'PRIOR_IMPLEMENTATION_EXISTS', 'allowed_existing_status': ['EXISTS', 'PARTIAL', 'MISSING', 'WRONG_BINDING', 'OBSOLETE', 'DUPLICATE'], 'allowed_disposition': ['KEEP', 'MODIFY', 'REMOVE', 'MERGE', 'REBIND', 'ADD'], 'unclassified_existing_gap': 'BLOCK'}
    rules['QUANTITATIVE_DESIGN_FREEZE_COMPLETENESS'] = {'required_percent': 100, 'orphan_visual_zero': True, 'unbound_control_zero': True, 'unbound_field_zero': True, 'undefined_next_step_zero': True, 'missing_recovery_zero': True, 'missing_required_visual_zero': True, 'authority_gap_hidden_by_percentage': 'BLOCK'}
    rules['BLUEPRINT_TO_IMPLEMENTATION_HANDOFF'] = {'required_artifact': 'BLUEPRINT_IMPLEMENTATION_HANDOFF', 'bidirectional_traceability_required': True, 'out_of_handoff_discovery': 'REOPEN_OWNING_CAPABILITY'}
    d['schema_version'] = 4
    dump(p, d)
    p = ROOT / 'governance/specifications/current/INTERACTION_TOPOLOGY_AI_CONTINUITY.yaml'
    d = load(p)
    ci = d.setdefault('common_invariants', {})
    ci['FUNCTION_VISUAL_BIDIRECTIONAL_TRACEABILITY'] = {'forward_trace_required': ['BUSINESS_ENTITY', 'OPERATION', 'JOURNEY', 'FUNCTIONAL_WORKBENCH', 'SECTION', 'COMPONENT', 'CONTROL_OR_SYSTEM_TRIGGER', 'FIELD_OR_INPUT', 'STATE', 'VISUAL_ANCHOR', 'VISUAL_CANDIDATE', 'IMPLEMENTATION_TARGET', 'ACCEPTANCE_ITEM'], 'reverse_trace_for_visible_elements_required': True, 'orphan_visual_element': 'BLOCK', 'missing_visual_binding': 'BLOCK', 'arbitrary_layout_topology_change': 'BLOCK'}
    ci['MANDATORY_MULTI_STATE_VISUAL_EVIDENCE'] = {'required_contract': 'VISUAL_SCENARIO_EVIDENCE_SET', 'applicability_required': True, 'missing_required_scenario': 'BLOCK', 'single_overview_substitutes_required_states': False}
    ci['VISUAL_REFERENCE_ANNOTATION'] = {'required_contract': 'VISUAL_REFERENCE_ANNOTATION', 'verification_purpose_required': True, 'unannotated_visual_may_pass_review': False}
    ci['SCENARIO_TO_FUNCTION_VISUAL_COVERAGE'] = {'required_coverage_percent': 100, 'denominator': 'APPROVED_REQUIRED_JOURNEY_STATE_BRANCH_SET', 'visual_scenario_drift': 'BLOCK'}
    d['schema_version'] = 3
    dump(p, d)

def source_checksums_and_archives():
    checks = SOURCE / 'CHECKSUMS.sha256'
    files = sorted([p for p in SOURCE.rglob('*') if p.is_file() and p != checks], key=lambda p: p.relative_to(SOURCE).as_posix())
    checks.write_text(''.join((f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files)), encoding='utf-8')
    allfiles = sorted([p for p in SOURCE.rglob('*') if p.is_file()], key=lambda p: p.relative_to(SOURCE).as_posix())
    if len(allfiles) != 75:
        raise RuntimeError(f'source file count changed: {len(allfiles)}')
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode='w', format=tarfile.PAX_FORMAT) as tf:
        for p in allfiles:
            rel = p.relative_to(SOURCE).as_posix()
            info = tf.gettarinfo(str(p), arcname=rel)
            info.uid = 0
            info.gid = 0
            info.uname = ''
            info.gname = ''
            info.mtime = 0
            with p.open('rb') as fh:
                tf.addfile(info, fh)
    bundle = lzma.compress(tar_buf.getvalue(), format=lzma.FORMAT_XZ, preset=9)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in allfiles:
            rel = p.relative_to(SOURCE).as_posix()
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3
            mode = 493 if p.stat().st_mode & 73 else 420
            zi.external_attr = (mode & 65535) << 16
            zf.writestr(zi, p.read_bytes())
    return (sha(checks), hashlib.sha256(bundle).hexdigest(), hashlib.sha256(zbuf.getvalue()).hexdigest())

def refresh_source(semantic_hash):
    for rel in ['10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml', '10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml', '10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml', '10_REGISTRY/BLUEPRINT_REGISTRY.yaml', '10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml', '10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml', '10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml', '10_REGISTRY/AUDIT_CATALOG.yaml']:
        p = SOURCE / rel
        d = load(p)
        if 'governance_revision' in d:
            d['governance_revision'] = NEW_SOURCE_REV
        dump(p, d)
    rootp = SOURCE / '10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
    rd = load(rootp)
    rd['governance_revision'] = NEW_SOURCE_REV
    dump(rootp, rd)
    append_once(SOURCE / 'README.md', '## v2.2.10 blueprint construction traceability hardening', '## v2.2.10 blueprint construction traceability hardening\nThis successor hardens the initial/basic design contract so a governed blueprint cannot close as prose plus one arbitrary mockup. It requires a complete non-owning Construction Blueprint Package, bidirectional Function/Visual traceability, applicable multi-state visual evidence with explicit annotations, Existing-Implementation Construction Delta classification, scenario-to-function coverage, quantitative Design Freeze denominators, and an exact Blueprint-to-Implementation Handoff. The rules remain product-neutral; product-specific concepts enter only through the selected Product Profile/Authority.')
    append_once(SOURCE / 'VERSIONING_RULE.md', '## v2.2.10 blueprint construction traceability hardening rule', '## v2.2.10 blueprint construction traceability hardening rule\n- v2.2.9 remains immutable predecessor history.\n- A blueprint is not implementation-ready merely because controls/components exist or one overview visual was produced.\n- Applicable blueprint artifacts, function-to-visual and visual-to-function traces, multi-state visual evidence/annotations, construction-delta classification, quantitative freeze coverage, and implementation handoff are Required before Design Freeze/implementation where applicable.\n- Product-specific behavior remains governed by Product Authority; these common rules define completeness and traceability and MUST_NOT invent product semantics.')
    replace_const(SOURCE / '09_TESTS/governance/validate_reference_semantics.py', 'SEMANTIC_BASELINE_CONTENT_HASH', semantic_hash)
    run(sys.executable, str(SOURCE / '09_TESTS/governance/compile_governance_baseline.py'))
    run(sys.executable, str(SOURCE / '09_TESTS/governance/refresh_governance_root_manifest.py'))
    checks, bundle, zips = source_checksums_and_archives()
    replace_const(ROOT / '.github/governance-source/VERIFY_SOURCE_IDENTITY.py', 'EXPECTED_BUNDLE_SHA256', bundle)
    replace_const(ROOT / '.github/governance-source/VERIFY_SOURCE_IDENTITY.py', 'EXPECTED_SOURCE_ZIP_SHA256', zips)
    for name, val in [('EXPECTED_CHECKSUMS_SHA256', checks), ('EXPECTED_SEMANTIC_CONTENT_HASH', semantic_hash), ('EXPECTED_SOURCE_ZIP_SHA256', zips), ('EXPECTED_BUNDLE_SHA256', bundle)]:
        replace_const(ROOT / '.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py', name, val)
    return (checks, bundle, zips)

def update_current_projection(semantic_hash, bundle_hash, zip_hash, checksums_hash):
    manifestp = ROOT / 'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    m = load(manifestp)
    old_sl = copy.deepcopy(m.get('source_lineage') or {})
    m['artifact_uid'] = NEW_UID
    m['display_version'] = NEW_DISPLAY
    sl = m.setdefault('source_lineage', {})
    sl.update({'verified_package_filename': NEW_PACKAGE, 'verified_package_sha256': zip_hash, 'predecessor_governance_uid': OLD_UID, 'promotion_authorization_uid': AUTH_UID, 'source_bytes_changed_by_this_successor': True, 'source_identity_reused_only_because_source_bytes_are_unchanged': False, 'deterministic_source_bundle_sha256': bundle_hash, 'checksum_manifest_sha256': checksums_hash, 'semantic_authority_content_hash': semantic_hash, 'verified_source_revision': NEW_SOURCE_REV, 'predecessor_verified_package_filename': old_sl.get('verified_package_filename'), 'predecessor_verified_package_sha256': old_sl.get('verified_package_sha256'), 'post_promotion_projector_sync_authorization_uid': AUTH_UID})
    dump(manifestp, m)
    rp = ROOT / 'governance/specifications/REGISTRY.yaml'
    r = load(rp)
    r['active_specification']['governance_uid'] = NEW_UID
    r['active_specification']['display_version'] = NEW_DISPLAY
    unique_extend(r['active_specification'].setdefault('aliases', []), ['blueprint-construction-traceability-hardening'])
    r['immediate_predecessor'] = {'governance_uid': OLD_UID, 'display_version': OLD_DISPLAY, 'version_role': 'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY', 'status': 'SUPERSEDED_HISTORY_ONLY_AFTER_BLUEPRINT_CONSTRUCTION_TRACEABILITY_HARDENING'}
    dump(rp, r)
    cp = ROOT / 'GOVERNANCE_CURRENT.yaml'
    c = load(cp)
    c['active_governance_uid'] = NEW_UID
    c['display_version'] = NEW_DISPLAY
    c.setdefault('source_identity', {}).update({'verified_package_sha256': zip_hash, 'deterministic_source_bundle_sha256': bundle_hash, 'checksum_manifest_sha256': checksums_hash, 'semantic_authority_content_hash': semantic_hash, 'verified_source_revision': NEW_SOURCE_REV, 'source_bytes_changed_by_current_successor': True})
    dump(cp, c)
    ap = ROOT / 'governance/test/ACTIVE_STATE.yaml'
    a = load(ap)
    a['specification_uid'] = NEW_UID
    gt = a.setdefault('governance_revision_transition', {})
    gt.update({'predecessor_governance_uid': OLD_UID, 'current_governance_uid': NEW_UID, 'fresh_revalidation_required': True, 'fresh_revalidation_scope': 'LATEST_BLUEPRINT_STANDARD_PILOT_REEXECUTION_AND_AFFECTED_DESIGN_CONSUMERS', 'website_construction_remains_blocked': True, 'deployment_remains_blocked': True})
    a['status'] = 'ACTIVE_GOVERNANCE_BLUEPRINT_CONSTRUCTION_TRACEABILITY_HARDENING_PROMOTED_REVALIDATION_REQUIRED'
    a['next_action'] = 'RUN_SUCCESSOR_EXACT_HEAD_VALIDATION_THEN_EXECUTE_ONE_FRESH_BLUEPRINT_REPLANNING'
    aw = a.get('active_work_unit') or {}
    if aw.get('work_unit_uid') != WORK_UNIT:
        raise RuntimeError('active governance work unit drift')
    aw['current_status'] = 'PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'
    a['active_work_unit'] = aw
    rc = a.setdefault('resume_control', {})
    rc['current_resume_point'] = 'BLUEPRINT_TRACEABILITY_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'
    rc['current_work_unit_uid'] = WORK_UNIT
    rc['exact_next_action'] = 'RUN_SUCCESSOR_EXACT_HEAD_VALIDATION_THEN_EXECUTE_ONE_FRESH_BLUEPRINT_REPLANNING'
    dump(ap, a)
    for rel in ['governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml', 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml']:
        p = ROOT / rel
        if p.exists():
            d = load(p)
            if d.get('governance_uid') == OLD_UID:
                d['governance_uid'] = NEW_UID
            if 'content_hash' in d:
                x = copy.deepcopy(d)
                x.pop('content_hash', None)
                d['content_hash'] = hashlib.sha256(yaml.safe_dump(x, allow_unicode=True, sort_keys=True, width=180).encode()).hexdigest()
            dump(p, d)

def mutate_current_components():
    p = ROOT / 'governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml'
    d = load(p)
    rules = d.setdefault('rules', {})
    rules['CONSTRUCTION_BLUEPRINT_PACKAGE_COMPLETENESS'] = {'required_artifact': 'CONSTRUCTION_BLUEPRINT_PACKAGE', 'package_is_non_owning_binding': True, 'missing_applicable_item': 'BLUEPRINT_PACKAGE_INCOMPLETE', 'implementation_before_complete_package': 'BLOCK'}
    rules['CONSTRUCTION_DELTA_EXISTING_IMPLEMENTATION'] = {'required_artifact': 'CONSTRUCTION_DELTA_MATRIX', 'activation': 'PRIOR_IMPLEMENTATION_EXISTS', 'allowed_existing_status': ['EXISTS', 'PARTIAL', 'MISSING', 'WRONG_BINDING', 'OBSOLETE', 'DUPLICATE'], 'allowed_disposition': ['KEEP', 'MODIFY', 'REMOVE', 'MERGE', 'REBIND', 'ADD'], 'unclassified_existing_gap': 'BLOCK'}
    rules['QUANTITATIVE_DESIGN_FREEZE_COMPLETENESS'] = {'required_percent': 100, 'orphan_visual_zero': True, 'unbound_control_zero': True, 'unbound_field_zero': True, 'undefined_next_step_zero': True, 'missing_recovery_zero': True, 'missing_required_visual_zero': True, 'authority_gap_hidden_by_percentage': 'BLOCK'}
    rules['BLUEPRINT_TO_IMPLEMENTATION_HANDOFF'] = {'required_artifact': 'BLUEPRINT_IMPLEMENTATION_HANDOFF', 'bidirectional_traceability_required': True, 'out_of_handoff_discovery': 'REOPEN_OWNING_CAPABILITY'}
    d['schema_version'] = 4
    dump(p, d)
    p = ROOT / 'governance/specifications/current/INTERACTION_TOPOLOGY_AI_CONTINUITY.yaml'
    d = load(p)
    ci = d.setdefault('common_invariants', {})
    ci['FUNCTION_VISUAL_BIDIRECTIONAL_TRACEABILITY'] = {'forward_trace_required': ['BUSINESS_ENTITY', 'OPERATION', 'JOURNEY', 'FUNCTIONAL_WORKBENCH', 'SECTION', 'COMPONENT', 'CONTROL_OR_SYSTEM_TRIGGER', 'FIELD_OR_INPUT', 'STATE', 'VISUAL_ANCHOR', 'VISUAL_CANDIDATE', 'IMPLEMENTATION_TARGET', 'ACCEPTANCE_ITEM'], 'reverse_trace_for_visible_elements_required': True, 'orphan_visual_element': 'BLOCK', 'missing_visual_binding': 'BLOCK', 'arbitrary_layout_topology_change': 'BLOCK'}
    ci['MANDATORY_MULTI_STATE_VISUAL_EVIDENCE'] = {'required_contract': 'VISUAL_SCENARIO_EVIDENCE_SET', 'applicability_required': True, 'missing_required_scenario': 'BLOCK', 'single_overview_substitutes_required_states': False}
    ci['VISUAL_REFERENCE_ANNOTATION'] = {'required_contract': 'VISUAL_REFERENCE_ANNOTATION', 'verification_purpose_required': True, 'unannotated_visual_may_pass_review': False}
    ci['SCENARIO_TO_FUNCTION_VISUAL_COVERAGE'] = {'required_coverage_percent': 100, 'denominator': 'APPROVED_REQUIRED_JOURNEY_STATE_BRANCH_SET', 'visual_scenario_drift': 'BLOCK'}
    d['schema_version'] = 3
    dump(p, d)

def validate_all():
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONPYCACHEPREFIX'] = '/tmp/acpos-blueprint-traceability-pycache'
    cmds = [[sys.executable, str(SOURCE / '09_TESTS/governance/validate_section_registry.py')], [sys.executable, str(SOURCE / '09_TESTS/governance/validate_reference_semantics.py')], [sys.executable, str(SOURCE / '09_TESTS/governance/validate_product_neutral_entity_lifecycle.py')], [sys.executable, str(ROOT / '.github/governance-source/VERIFY_SOURCE_IDENTITY.py')], [sys.executable, str(ROOT / 'governance/ci/governance_resolver.py')], [sys.executable, str(ROOT / 'governance/ci/validate_governance_portability.py')], [sys.executable, str(ROOT / 'governance/ci/validate_active_consumer_reference_integrity.py')], [sys.executable, str(ROOT / 'governance/ci/validate_structured_mutation_safety.py')], [sys.executable, str(ROOT / 'governance/ci/stress_test_governance_registry.py')], [sys.executable, str(ROOT / 'governance/ci/validate_selected_execution_profile_integrity.py')], [sys.executable, str(ROOT / 'governance/ci/stage_execution_engine.py'), '--definition-audit-all'], [sys.executable, str(ROOT / 'governance/ci/test_stage_execution_engine.py')], [sys.executable, str(ROOT / '.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py')]]
    for cmd in cmds:
        cp = run(*cmd, check=False, env=env)
        print('$', ' '.join(map(str, cmd)))
        print(cp.stdout[-5000:])
        if cp.returncode:
            print(cp.stderr[-7000:], file=sys.stderr)
            raise SystemExit(cp.returncode)

def apply():
    current = load(ROOT / 'GOVERNANCE_CURRENT.yaml')
    if current.get('active_governance_uid') not in (OLD_UID, NEW_UID):
        raise RuntimeError('unexpected current governance uid')
    mutate_mother()
    mutate_section_registry()
    mutate_invariant_registry()
    mutate_blueprint_acceptance_index()
    harden_validator()
    semantic_hash = mutate_stage_and_semantic()
    mutate_current_components()
    rp = SOURCE / '10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'
    ref = load(rp)
    bt_ref = ref.setdefault('blueprint_type_identities', [])
    if not any(((x or {}).get('blueprint_type_uid') == 'BPTYPE-GOV-007' for x in bt_ref)):
        bt_ref.append({'blueprint_type_uid': 'BPTYPE-GOV-007', 'canonical_name': 'CONSTRUCTION_BLUEPRINT_PACKAGE', 'planning_domain': 'NON_OWNING_BINDING', 'created_stage_uid': 'STAGE-04'})
    dump(rp, ref)
    sp = SOURCE / '10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    sem = load(sp)
    bt_sem = sem['semantic_snapshot'].setdefault('blueprint_type_identities', [])
    if not any(((x or {}).get('blueprint_type_uid') == 'BPTYPE-GOV-007' for x in bt_sem)):
        bt_sem.append({'blueprint_type_uid': 'BPTYPE-GOV-007', 'canonical_name': 'CONSTRUCTION_BLUEPRINT_PACKAGE', 'planning_domain': 'NON_OWNING_BINDING', 'created_stage_uid': 'STAGE-04'})
    sem['content_hash'] = hobj(sem)
    dump(sp, sem)
    semantic_hash = sem['content_hash']
    csp = SOURCE / '11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    cs = load(csp)
    cs['candidate'] = 'v2.2.10_BLUEPRINT_CONSTRUCTION_TRACEABILITY_HARDENING_CANDIDATE'
    cs['status'] = 'CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'
    fresh = cs.setdefault('fresh_revalidation', {})
    fresh['required'] = True
    fresh['current_source_revision'] = NEW_SOURCE_REV
    fresh['current_closure_credit'] = False
    fresh['predecessor_evidence_current_closure_credit'] = False
    fresh['embedded_preformal_execution_role'] = 'HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'
    fresh['predecessor_wrapper_result_role'] = 'HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'
    fresh['persisted_head_full_line_required'] = True
    fresh['historical_evidence_may_close_successor'] = False
    dump(csp, cs)
    rvp = SOURCE / '10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml'
    rv = load(rvp)
    rv['governance_revision'] = NEW_SOURCE_REV
    dump(rvp, rv)
    checks, bundle, zips = refresh_source(semantic_hash)
    update_current_projection(semantic_hash, bundle, zips, checks)
    return {'semantic_hash': semantic_hash, 'checksums_hash': checks, 'bundle_hash': bundle, 'zip_hash': zips}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['precheck', 'promote'], required=True)
    args = ap.parse_args()
    result = apply()
    validate_all()
    print(json.dumps({'mode': args.mode, 'new_uid': NEW_UID, **result}, indent=2))
    if args.mode == 'precheck':
        print('PRECHECK_PASS_NO_COMMIT')
        return 0
    auth = ROOT / f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
    if not auth.exists():
        raise RuntimeError('preexisting authorization missing')
    for p in [ROOT / '.github/governance-maintenance/BLUEPRINT_TRACEABILITY_PROMOTE_TRIGGER', ROOT / '.github/workflows/blueprint-traceability-governance-promotion.yml', ROOT / '.github/governance-maintenance/promote_blueprint_traceability_governance.py.gz']:
        if p.exists():
            p.unlink()
    for extra in [ROOT / '.github/governance-maintenance/patch_blueprint_type_identity.py', ROOT / '.github/governance-maintenance/promote_blueprint_traceability_governance.py.gz']:
        if extra.exists():
            extra.unlink()
    run('git', 'config', 'user.name', 'github-actions[bot]')
    run('git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    run('git', 'add', '-A')
    if run('git', 'diff', '--cached', '--quiet', check=False).returncode == 0:
        raise RuntimeError('no promotion delta')
    msg = 'feat(governance): promote blueprint construction traceability hardening\n\nSpec-Change-Authorization: USR-DIRECTIVE-20260919-BLUEPRINT-CONSTRUCTION-TRACEABILITY-HARDENING-R12\nSpec-Change-Scope: INITIAL_BLUEPRINT_PACKAGE_FUNCTION_VISUAL_TRACEABILITY_VISUAL_EVIDENCE_CONSTRUCTION_DELTA_AND_FREEZE_HARDENING'
    run('git', 'commit', '-m', msg)
    run(sys.executable, str(ROOT / 'governance/ci/specification_mutation_guard.py'))
    run('git', 'push', 'origin', 'HEAD:rebuild-v2.1.1')
    print('PROMOTION_PUSHED', run('git', 'rev-parse', 'HEAD').stdout.strip())
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
