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
OLD_UID = 'GOV-REV-20260920-STAGE03-VISUAL-MATERIALIZATION-PROMOTION-CLOSURE'
NEW_UID = 'GOV-REV-20260920-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-HARDENING'
OLD_DISPLAY = 'v2.2.15'
NEW_DISPLAY = 'v2.2.16'
NEW_SOURCE_REV = 'v2.2.16-cross-stage-materialization-consumer-readiness-hardening'
AUTH_UID = 'USR-DIRECTIVE-20260920-CROSS-STAGE-MATERIALIZATION-CONTINUITY-HARDENING-R1'
NEW_PACKAGE = 'AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.16_CROSS_STAGE_MATERIALIZATION_CONSUMER_READINESS_HARDENING_LOCAL_VERIFIED.zip'
WORK_UNIT = 'WU-GOV-CROSS-STAGE-MATERIALIZATION-CONTINUITY-HARDENING-001'
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

SECTION_DEFS = {
    'WEB-GOV-01-S088': ('WEB-GOV-01', '12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md', '88', '跨階段來源實體化與後繼可用性 Gate / Cross-Stage Source Materialization and Successor Readiness', '''
A reference is not a materialized artifact. A UID, path, Registry entry, manifest name, Candidate identity, Visual Anchor identity, Authority reference, FINAL/LOCKED label, historical owner record, or dependency edge proves identity or intent only. It MUST NOT receive materialization, completeness, readiness, review, freeze, or Stage-exit credit by itself.

Every REQUIRED source-declared or Authority-declared dependency that can be consumed by the current or a later capability MUST be reconciled through one exact materialization record. This includes Authority owners, registries, manifests, Visual Candidates, Visual Anchors, assets, schemas, shared-owner contracts, external packages, generated artifacts, handoff records, and equivalent typed dependencies. The record MUST bind: dependency UID/ref; canonical owner; canonical/current physical path or explicit external evidence ref; version/schema; digest when registered; applicability; required successor capability or Stage; materialization status; required-field completeness; denominator inclusion; and consumer-readiness disposition.

Stage-01 Source Intake and Base Blueprint MUST distinguish SOURCE_REFERENCE_CAPTURED from SOURCE_ARTIFACT_MATERIALIZED. When Current source declares an Anchor Registry, Generation Manifest, Candidate UID set, required asset set, schema owner, external package member, or other required downstream dependency, Stage-01 MUST either physically capture and validate that owner or create an explicit SOURCE_CAPTURE_GAP. Classification or Base Blueprint compilation MUST NOT silently discard the dependency and MUST NOT convert a reference-only record into completed materialization.

A required dependency MAY be deferred only when Current Authority explicitly names a legal later owner, exact materialization boundary, and successor entry condition. Undefined deferral is forbidden. Historical bytes, an old commit, a stale generated output, or a previous successful test MUST NOT fill missing Current source data.

For any downstream-required item, the predecessor may receive Stage exit credit only after the successor-required input universe is reconciled. Missing physical source, missing required fields, unresolved digest/schema, denominator omission, or unproven consumer readiness MUST block or reopen the earliest owning capability. AI MUST NOT invent missing product values, Visual Anchors, Visual Candidates, or Authority content merely to satisfy this Gate.
'''),
    'WEB-GOV-02-S075': ('WEB-GOV-02', '12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md', '75', 'Producer/Consumer 實體交接與後繼輸入可用性 Gate / Producer-Consumer Materialized Handoff and Successor Input Readiness', '''
Every REQUIRED predecessor-output to successor-input edge MUST pass four distinct gates: (1) reference resolution, (2) physical materialization, (3) schema/version and required-field completeness, and (4) successor consumer readiness. Passing an earlier gate MUST NOT imply a later gate.

Each governed Stage or capability boundary MUST materialize a CROSS_STAGE_HANDOFF_READINESS_LEDGER. Each REQUIRED edge row MUST contain at least: producer Stage/capability; producer output UID/type; producer owner/path/evidence ref; producer hash/version/schema; consumer Stage/capability; consumer input UID/type; consumer owner/schema; applicability; reference-resolution status; physical-materialization status; parse/schema status; required-field completeness; denominator-inclusion status; consumer-admission/readiness result; unresolved dependency count; blocking owner/re-entry target; and current evidence ref.

Reference-only, UID-only, path-only, existence-without-parse, parse-without-required-fields, schema-compatible-but-denominator-omitted, or denominator-listed-but-consumer-unreadable states are incomplete and MUST NOT receive Stage exit credit.

Before a Stage closes, its complete applicable successor-required input universe MUST be reconciled against predecessor outputs, Current Authority, shared owners, persisted foundation artifacts, and registered external evidence. Every REQUIRED row must be READY, or the Stage remains BLOCKED and the earliest owning capability must be re-entered.

A producer hash, schema, required field, applicability, owner, or denominator change MUST mark impacted downstream consumers REVERIFY_REQUIRED until fresh consumer-readiness evidence is produced. Unaffected evidence may be preserved only through reverse-dependency proof.
'''),
    'WEB-GOV-03-S071': ('WEB-GOV-03', '12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md', '71', '跨階段實體交接 / Consumer Readiness / 回退控制 / Cross-Stage Materialized Handoff, Consumer Readiness and Re-entry Control', '''
Every governed Stage exit MUST execute the following order before the next Stage may be admitted:

1. Enumerate the complete applicable successor-required input universe from the Current lifecycle/profile/Authority.
2. Reconcile each required input to exactly one legal predecessor output, persisted foundation artifact, Current Authority/shared owner, or registered external evidence source.
3. Prove the referenced owner/evidence is physically available in the Current execution context or is a valid external receipt.
4. Parse and validate artifact type, schema/version, canonical identity, digest when registered, and every REQUIRED field.
5. Reconcile each required edge into the current denominator; zero-gap claims MUST include required handoff edges rather than omit them.
6. Run the successor consumer admission/readiness check using the same exact inputs that will be consumed downstream.
7. Persist CROSS_STAGE_HANDOFF_READINESS_LEDGER and affected reverse-dependency dispositions.
8. Only then evaluate Stage exit and next-Stage transition.

The closed failure-class vocabulary includes REFERENCE_ONLY_UNMATERIALIZED, PHYSICAL_REQUIRED_INPUT_MISSING, SCHEMA_OR_VERSION_MISMATCH, REQUIRED_FIELD_INCOMPLETE, DENOMINATOR_OMISSION, CONSUMER_NOT_READY, and DOWNSTREAM_DISCOVERED_UPSTREAM_GAP. These are blocking states unless Current Authority explicitly proves non-applicability.

If a downstream capability discovers an upstream-owned handoff defect, downstream mutation MUST stop. Execution MUST reopen the earliest owning capability, mark affected descendants REVERIFY_REQUIRED, preserve only reverse-dependency-proven unaffected evidence, and resume from the earliest impacted successor boundary. A downstream patch MUST NOT manufacture the missing upstream artifact or claim the predecessor was complete.

This control applies to every registered lifecycle Stage. Stage-local success, functional-gap-zero, visual-review-ready, implementation-complete, test-pass, build-pass, staging-pass, deployment-pass, or production-pass MUST NOT bypass materialized handoff and consumer readiness.
'''),
    'WEB-GOV-04-S085': ('WEB-GOV-04', '12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md', '85', '跨階段實體化 / 後繼可用性 / 假完成稽核 / Cross-Stage Materialization, Successor Readiness and False-Completion Audit', '''
Audit MUST independently reconstruct every REQUIRED predecessor-output to successor-input edge for the audited scope and verify the CROSS_STAGE_HANDOFF_READINESS_LEDGER against Current physical reality.

The audit denominator MUST separately report: required edge total; reference-resolved total; physically materialized total; parse/schema-valid total; required-field-complete total; denominator-included total; consumer-ready total; unresolved required dependency total; re-entry-required total; and impacted REVERIFY_REQUIRED consumer total. Counts MUST be UID/edge based, not inferred from Stage PASS labels.

Path presence, UID presence, Registry presence, ledger presence, historical evidence, a prior successful run, or a producer PASS MUST NOT substitute for physical parseable complete Current input and successful successor consumer admission. Missing or omitted REQUIRED edges are blockers even when the current Stage-local problem register says zero.

Audit regression MUST include destructive or mutation cases for at least: reference-only dependency with missing bytes; physical artifact with missing required fields; schema/version drift; required edge omitted from denominator; successor consumer unable to parse/admit; downstream discovery of an upstream-owned defect; and multi-state visual evidence falsely represented by one shared overview without explicit simultaneous/unambiguous state proof.

Stage closure requires zero unresolved REQUIRED handoff edges, zero denominator omissions, zero unproven consumer-ready edges, and zero incorrectly preserved downstream closure credit after an upstream defect. Any mismatch is CROSS_STAGE_HANDOFF_FALSE_COMPLETION and MUST block closure.
''')
}

ALL_STAGE_COMMON_SECTIONS = ['WEB-GOV-02-S075', 'WEB-GOV-03-S071', 'WEB-GOV-04-S085']
EARLY_STAGE_SOURCE_SECTION = 'WEB-GOV-01-S088'
CROSS_INV_UID = 'GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001'
HANDOFF_REQUIRED_FIELDS = [
    'producer_stage_or_capability','producer_output_uid_or_type','producer_owner',
    'producer_physical_ref_or_external_evidence','producer_hash_or_version_or_schema',
    'consumer_stage_or_capability','consumer_input_uid_or_type','consumer_owner_or_schema',
    'applicability','reference_resolution_status','physical_materialization_status',
    'parse_schema_status','required_field_completeness','denominator_inclusion_status',
    'consumer_readiness_status','unresolved_required_dependency_total',
    'blocking_owner_or_reentry_target','current_evidence_ref'
]

def add_mother_sections_v2216():
    for uid,(doc_id,rel,num,title,body) in SECTION_DEFS.items():
        p=SOURCE/rel
        marker=f'<!-- SECTION_UID: {uid} -->'
        s=p.read_text(encoding='utf-8')
        if marker not in s:
            s=s.rstrip()+f'\n\n{marker}\n## {num}. {title}\n\n{body.strip()}\n'
            p.write_text(s,encoding='utf-8')

def add_section_registry_v2216():
    p=SOURCE/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
    d=load(p)
    docs={x.get('document_id'):x for x in d.get('documents') or []}
    for uid,(doc_id,rel,num,title,_) in SECTION_DEFS.items():
        doc=docs.get(doc_id)
        if not doc: raise RuntimeError('section registry document missing:'+doc_id)
        rows=doc.setdefault('sections',[])
        if any(x.get('section_uid')==uid for x in rows): continue
        heading=f'## {num}. {title}'
        rows.append({
            'section_uid':uid,'level':2,'canonical_number':num,'title':title,
            'heading':heading,'path':rel,
            'binding_sha256':section_binding(uid,doc_id,rel,heading)
        })
    if 'governance_revision' in d: d['governance_revision']=NEW_SOURCE_REV
    dump(p,d)

def mutate_stage_invariant_v2216():
    p=SOURCE/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
    d=load(p); d['governance_revision']=NEW_SOURCE_REV
    inv=d.setdefault('invariants',{})
    inv['CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS']={
        'invariant_uid':CROSS_INV_UID,
        'required_artifact':'CROSS_STAGE_HANDOFF_READINESS_LEDGER',
        'applies_to_all_registered_stages':True,
        'required_row_fields':HANDOFF_REQUIRED_FIELDS,
        'reference_resolution_required':True,
        'reference_presence_is_materialization':False,
        'physical_materialization_required':True,
        'parse_required':True,
        'schema_version_identity_required':True,
        'required_field_completeness_required':True,
        'digest_verification_when_registered':True,
        'denominator_inclusion_required':True,
        'successor_consumer_readiness_required':True,
        'successor_required_input_universe_reconciliation_before_stage_exit':True,
        'historical_or_reference_only_completion_credit':0,
        'unresolved_required_dependency':'BLOCK_OR_REENTER_EARLIEST_OWNER',
        'downstream_discovered_upstream_gap':'STOP_REENTER_EARLIEST_OWNER_MARK_DESCENDANTS_REVERIFY_REQUIRED',
        'unaffected_evidence_preservation_requires_reverse_dependency_proof':True,
        'product_stage_credit_from_governance_validation':0
    }
    e=inv.setdefault('REQUIRED_EVIDENCE_MATERIALIZATION',{})
    e.update({
        'reference_only_claim_proves_physical_artifact':False,
        'physical_artifact_without_parse_or_required_fields_is_complete':False,
        'consumer_readiness_required_when_evidence_is_successor_input':True
    })
    pre=inv.setdefault('STAGE_ENTRY_PRECHECK',{})
    pre.update({
        'reference_only_required_input_is_ready':False,
        'required_input_parse_and_required_field_validation_required':True,
        'required_input_denominator_inclusion_required':True,
        'consumer_admission_on_exact_input_required':True
    })
    pcs=inv.setdefault('PRODUCER_CONSUMER_SCHEMA_IDENTITY',{})
    pcs.update({
        'producer_output_physical_materialization_required':True,
        'consumer_input_physical_resolution_required':True,
        'required_field_completeness_required':True,
        'denominator_reconciliation_required':True
    })
    mv=inv.setdefault('MANDATORY_MULTI_STATE_VISUAL_EVIDENCE',{})
    mv.update({
        'single_overview_visual_may_substitute_required_scenarios':False,
        'shared_visual_across_scenarios_requires_simultaneous_unambiguous_annotation_proof':True,
        'applicable_visual_anchor_uids_nonempty_required':True,
        'physical_candidate_evidence_required':True
    })
    va=inv.setdefault('VISUAL_REFERENCE_ANNOTATION',{})
    va.update({
        'applicable_visual_anchor_uids_nonempty_required':True,
        'candidate_physical_ref_required_when_candidate_is_declared':True
    })
    sv=inv.setdefault('SCENARIO_TO_FUNCTION_VISUAL_COVERAGE',{})
    sv.update({
        'empty_visual_anchor_mapping_for_applicable_visual_scenario':'BLOCK',
        'same_visual_for_multiple_required_scenarios_requires_explicit_state_coverage_proof':True
    })
    vm=inv.setdefault('VISUAL_DESIGN_PROFILE_MATERIALIZATION_COMPLETENESS',{})
    vm.update({
        'declared_candidate_requires_physical_candidate_evidence':True,
        'applicable_visual_anchor_registry_must_materialize_and_be_nonempty':True,
        'human_visual_review_with_missing_required_anchor_or_candidate':'BLOCK',
        'multi_state_records_all_pointing_to_one_overview_without_explicit_proof':'BLOCK'
    })
    dump(p,d)

def mutate_lifecycle_and_reference_v2216():
    lp=SOURCE/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
    life=load(lp)
    stages=life.get('stages') or []
    expected={f'STAGE-{i:02d}' for i in range(1,12)}
    actual={str(x.get('stage_uid')) for x in stages}
    if actual!=expected: raise RuntimeError('lifecycle stage set drift:'+repr(sorted(actual)))
    for st in stages:
        sid=str(st['stage_uid'])
        refs=st.setdefault('required_normative_section_uids',[])
        unique_extend(refs,ALL_STAGE_COMMON_SECTIONS)
        if sid in {'STAGE-01','STAGE-02','STAGE-03','STAGE-04'}:
            unique_extend(refs,[EARLY_STAGE_SOURCE_SECTION])
        st['cross_stage_materialization_gate']={
            'required':True,'invariant_uid':CROSS_INV_UID,
            'reference_resolution_required':True,
            'physical_materialization_required':True,
            'parse_schema_required_field_completeness_required':True,
            'denominator_inclusion_required':True,
            'successor_consumer_readiness_required':True,
            'reference_only_completion_credit':0,
            'successor_required_input_reconciliation_before_exit':True,
            'downstream_upstream_gap_disposition':'REENTER_EARLIEST_OWNER_AND_MARK_DESCENDANTS_REVERIFY_REQUIRED'
        }
        if sid=='STAGE-01':
            st['source_capture_materialization_gate']={
                'required':True,
                'source_declared_registry_manifest_candidate_anchor_dependency_must_be_physical_or_gap':True,
                'classification_or_blueprint_may_silently_drop_source_dependency':False,
                'reference_only_source_dependency_may_receive_stage1_completion_credit':False,
                'missing_required_physical_owner_disposition':'SOURCE_CAPTURE_GAP',
                'ai_may_invent_missing_source_content':False
            }
        if sid=='STAGE-02':
            st['successor_readiness_gate']={
                'required':True,
                'functional_gap_zero_substitutes_stage03_visual_dependency_readiness':False,
                'stage03_required_visual_dependency_reconciliation_required':True,
                'source_declared_anchor_candidate_manifest_readiness_required_when_applicable':True,
                'missing_successor_required_input':'BLOCK_AND_REENTER_OWNER'
            }
        if sid=='STAGE-03':
            vg=st.setdefault('visual_materialization_gate',{})
            vg.update({
                'applicable_visual_anchor_registry_must_be_nonempty':True,
                'declared_visual_candidate_requires_physical_evidence':True,
                'single_overview_may_substitute_required_scenarios':False,
                'shared_visual_requires_simultaneous_unambiguous_annotation_proof':True,
                'missing_required_anchor_or_candidate_blocks_human_visual_review':True
            })
    cross=life.setdefault('cross_stage_invariants',{}).setdefault('stage_execution_invariant_hardening',{})
    cross.update({
        'cross_stage_materialization_consumer_readiness_required':True,
        'cross_stage_materialization_invariant_uid':CROSS_INV_UID,
        'reference_presence_is_not_materialization':True,
        'physical_materialization_is_not_required_field_completeness':True,
        'required_field_completeness_is_not_consumer_readiness':True,
        'successor_input_reconciliation_before_stage_exit_required':True
    })
    if 'governance_revision' in life: life['governance_revision']=NEW_SOURCE_REV
    dump(lp,life)

    rp=SOURCE/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'
    ref=load(rp)
    for sid,row in (ref.get('stage_reference_rules') or {}).items():
        unique_extend(row.setdefault('exact_required_normative_section_uids',[]),ALL_STAGE_COMMON_SECTIONS)
        if sid in {'STAGE-01','STAGE-02','STAGE-03','STAGE-04'}:
            unique_extend(row['exact_required_normative_section_uids'],[EARLY_STAGE_SOURCE_SECTION])
    unique_extend(ref.setdefault('normative_section_uids',[]),ALL_STAGE_COMMON_SECTIONS+[EARLY_STAGE_SOURCE_SECTION])
    cb=ref.setdefault('common_bundle_reference_rules',{})
    if 'BUNDLE-GOV-CONSTRUCTION-BASE' in cb:
        unique_extend(cb['BUNDLE-GOV-CONSTRUCTION-BASE'].setdefault('exact_section_uids',[]),
                      ['WEB-GOV-01-S088','WEB-GOV-02-S075','WEB-GOV-03-S071'])
    if 'BUNDLE-GOV-AUDIT-BASE' in cb:
        unique_extend(cb['BUNDLE-GOV-AUDIT-BASE'].setdefault('exact_section_uids',[]),['WEB-GOV-04-S085'])
    if 'governance_revision' in ref: ref['governance_revision']=NEW_SOURCE_REV
    dump(rp,ref)

    sp=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    sem=load(sp)
    snap=sem.setdefault('semantic_snapshot',{})
    sr=snap.setdefault('stage_reference_rules',{})
    for sid,row in sr.items():
        unique_extend(row.setdefault('exact_required_normative_section_uids',[]),ALL_STAGE_COMMON_SECTIONS)
        if sid in {'STAGE-01','STAGE-02','STAGE-03','STAGE-04'}:
            unique_extend(row['exact_required_normative_section_uids'],[EARLY_STAGE_SOURCE_SECTION])
    cbr=snap.get('common_bundle_reference_rules') or {}
    if 'BUNDLE-GOV-CONSTRUCTION-BASE' in cbr:
        unique_extend(cbr['BUNDLE-GOV-CONSTRUCTION-BASE'].setdefault('exact_section_uids',[]),
                      ['WEB-GOV-01-S088','WEB-GOV-02-S075','WEB-GOV-03-S071'])
    if 'BUNDLE-GOV-AUDIT-BASE' in cbr:
        unique_extend(cbr['BUNDLE-GOV-AUDIT-BASE'].setdefault('exact_section_uids',[]),['WEB-GOV-04-S085'])
    sem['governance_revision']=NEW_SOURCE_REV
    sem['content_hash']=hobj(sem)
    dump(sp,sem)
    return sem['content_hash']

def mutate_audit_and_index_v2216():
    ap=SOURCE/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
    bp=load(ap); bp['governance_revision']=NEW_SOURCE_REV
    unique_extend(bp.setdefault('normative_section_uids',[]),[
        'WEB-GOV-01-S088','WEB-GOV-02-S075','WEB-GOV-03-S071','WEB-GOV-04-S085'])
    unique_extend(bp.setdefault('audit_item_uids',[]),['AUD-GOV-014'])
    bp['cross_stage_materialization_consumer_readiness_contract']={
        'required':True,'audit_item_uid':'AUD-GOV-014','validator_uid':'VAL-GOV-035',
        'applies_to_stages':[f'STAGE-{i:02d}' for i in range(1,12)],
        'required_artifact':'CROSS_STAGE_HANDOFF_READINESS_LEDGER',
        'reference_presence_only_acceptance':'BLOCK',
        'physical_materialization_required':True,
        'parse_schema_required_field_validation_required':True,
        'denominator_inclusion_required':True,
        'successor_consumer_readiness_required':True,
        'zero_unresolved_required_handoff_edges_at_exit':True,
        'downstream_discovered_upstream_gap_reentry_required':True
    }
    sec=bp.setdefault('stage_execution_invariant_contract',{})
    sec.update({
        'cross_stage_materialization_consumer_readiness_required':True,
        'cross_stage_materialization_invariant_uid':CROSS_INV_UID,
        'reference_only_required_dependency_completion':'BLOCK',
        'successor_readiness_required_before_stage_exit':True
    })
    dump(ap,bp)

    cp=SOURCE/'10_REGISTRY/AUDIT_CATALOG.yaml'
    cat=load(cp); cat['governance_revision']=NEW_SOURCE_REV
    rows=cat.setdefault('items',[])
    if not any(x.get('audit_item_uid')=='AUD-GOV-014' for x in rows):
        rows.append({
            'audit_item_uid':'AUD-GOV-014',
            'audit_type':'CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS',
            'stage_uid':'PREFORMAL','target_uid':'GOVERNANCE_PACKAGE',
            'requirement_type':'BLOCKING','validator_uid':'VAL-GOV-035',
            'required_evidence':['VALIDATOR_RESULT'],
            'denominator_eligible':True,'status':'REQUIRED',
            'validator_name':'STAGE_EXECUTION_INVARIANT_GUARD',
            'audit_type_uid':'AUDTYPE-GOV-014',
            'coverage_extensions':[
                'REFERENCE_RESOLUTION','PHYSICAL_MATERIALIZATION','PARSE_SCHEMA_REQUIRED_FIELDS',
                'DENOMINATOR_INCLUSION','SUCCESSOR_CONSUMER_READINESS','UPSTREAM_REENTRY'
            ]
        })
    dump(cp,cat)

    ip=SOURCE/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'
    idx=load(ip); ur=idx.setdefault('universal_rules',{})
    for k in [
        'reference_only_required_dependency_completion',
        'physical_required_input_missing',
        'required_input_schema_or_version_mismatch',
        'required_input_required_field_incomplete',
        'successor_required_edge_denominator_omission',
        'successor_consumer_readiness_unproven',
        'applicable_visual_anchor_registry_empty',
        'declared_visual_candidate_without_physical_evidence',
        'multi_state_visual_single_overview_without_explicit_simultaneous_state_proof'
    ]:
        ur[k]='BLOCK'
    ur['downstream_discovered_upstream_gap']='REENTER_EARLIEST_OWNER_MARK_DESCENDANTS_REVERIFY_REQUIRED'
    if 'governance_revision' in idx: idx['governance_revision']=NEW_SOURCE_REV
    dump(ip,idx)

def mutate_current_components_v2216():
    p=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'
    d=load(p); d['schema_version']=max(7,int(d.get('schema_version') or 0))
    d['cross_stage_materialization_consumer_readiness']={
        'required_for_every_registered_stage_boundary':True,
        'required_artifact':'CROSS_STAGE_HANDOFF_READINESS_LEDGER',
        'reference_resolution_is_physical_materialization':False,
        'physical_materialization_is_required_field_completeness':False,
        'required_field_completeness_is_consumer_readiness':False,
        'required_sequence':[
            'ENUMERATE_SUCCESSOR_REQUIRED_INPUT_UNIVERSE',
            'RESOLVE_LEGAL_PRODUCER_OR_CURRENT_OWNER',
            'VERIFY_CURRENT_PHYSICAL_OR_EXTERNAL_EVIDENCE',
            'PARSE_SCHEMA_VERSION_IDENTITY_AND_REQUIRED_FIELDS',
            'RECONCILE_DENOMINATOR',
            'RUN_SUCCESSOR_CONSUMER_ADMISSION',
            'PERSIST_HANDOFF_LEDGER_AND_REVERSE_IMPACT',
            'EVALUATE_STAGE_EXIT'
        ],
        'reference_only_completion_credit':0,
        'unresolved_required_dependency':'BLOCK_OR_REENTER_EARLIEST_OWNER',
        'downstream_discovered_upstream_gap':'STOP_AND_REENTER_EARLIEST_OWNER',
        'impacted_descendants':'REVERIFY_REQUIRED',
        'historical_value_may_fill_missing_current_input':False
    }
    dump(p,d)

    p=ROOT/'governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml'
    d=load(p); d['schema_version']=max(8,int(d.get('schema_version') or 0))
    rules=d.setdefault('rules',{})
    rules['CROSS_STAGE_SUCCESSOR_INPUT_READINESS']={
        'required_artifact':'CROSS_STAGE_HANDOFF_READINESS_LEDGER',
        'stage_local_zero_gap_is_successor_ready':False,
        'successor_required_input_universe_reconciliation_required':True,
        'source_declared_required_dependency_reference_only_credit':0,
        'physical_materialization_required':True,
        'required_field_completeness_required':True,
        'denominator_inclusion_required':True,
        'successor_consumer_admission_required':True,
        'missing_required_input':'BLOCK_AND_REENTER_EARLIEST_OWNER'
    }
    dump(p,d)

    p=ROOT/'governance/specifications/current/INTERACTION_TOPOLOGY_AI_CONTINUITY.yaml'
    d=load(p); d['schema_version']=max(6,int(d.get('schema_version') or 0))
    ci=d.setdefault('common_invariants',{})
    mv=ci.setdefault('MANDATORY_MULTI_STATE_VISUAL_EVIDENCE',{})
    mv.update({
        'single_overview_substitutes_required_states':False,
        'shared_visual_requires_simultaneous_unambiguous_state_annotation_proof':True,
        'applicable_visual_anchor_uids_nonempty_required':True,
        'declared_visual_candidate_physical_evidence_required':True
    })
    va=ci.setdefault('VISUAL_REFERENCE_ANNOTATION',{})
    va.update({
        'applicable_visual_anchor_uids_nonempty_required':True,
        'declared_candidate_physical_ref_required':True
    })
    sv=ci.setdefault('SCENARIO_TO_FUNCTION_VISUAL_COVERAGE',{})
    sv.update({
        'empty_visual_anchor_mapping':'BLOCK',
        'same_visual_multi_scenario_without_explicit_simultaneous_coverage_proof':'BLOCK'
    })
    dump(p,d)

def insert_before_final_return_in_function(path,func_name,code):
    import ast
    p=Path(path); s=p.read_text(encoding='utf-8'); tree=ast.parse(s)
    fn=next((x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==func_name),None)
    if fn is None: raise RuntimeError('AST function missing:'+func_name)
    returns=[x for x in fn.body if isinstance(x,ast.Return)]
    if len(returns)!=1: raise RuntimeError('AST top-level return count drift:'+func_name+':'+str(len(returns)))
    line=returns[0].lineno-1; lines=s.splitlines()
    payload=code.strip('\n').splitlines()
    lines[line:line]=payload
    ns='\n'.join(lines)+'\n'; ast.parse(ns)
    p.write_text(ns,encoding='utf-8')

def insert_before_assignment_in_function(path,func_name,target_name,code):
    import ast
    p=Path(path); s=p.read_text(encoding='utf-8'); tree=ast.parse(s)
    fn=next((x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==func_name),None)
    if fn is None: raise RuntimeError('AST function missing:'+func_name)
    nodes=[]
    for x in fn.body:
        if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==target_name for t in x.targets):
            nodes.append(x)
    if len(nodes)!=1: raise RuntimeError('AST assignment target drift:'+func_name+':'+target_name)
    line=nodes[0].lineno-1; lines=s.splitlines()
    lines[line:line]=code.strip('\n').splitlines()
    ns='\n'.join(lines)+'\n'; ast.parse(ns)
    p.write_text(ns,encoding='utf-8')

def add_set_literal_member_ast(path,target_name,item):
    import ast
    p=Path(path); s=p.read_text(encoding='utf-8'); tree=ast.parse(s)
    nodes=[]
    for x in tree.body:
        if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==target_name for t in x.targets):
            nodes.append(x)
    if len(nodes)!=1: raise RuntimeError('AST set assignment drift:'+target_name)
    node=nodes[0]
    vals=ast.literal_eval(node.value)
    if not isinstance(vals,set): raise RuntimeError('AST assignment not set:'+target_name)
    vals.add(item)
    rendered=target_name+'={'+','.join(repr(x) for x in sorted(vals))+'}'
    lines=s.splitlines(); lines[node.lineno-1:node.end_lineno]=[rendered]
    ns='\n'.join(lines)+'\n'; ast.parse(ns)
    p.write_text(ns,encoding='utf-8')

def harden_source_validator_v2216():
    p=SOURCE/'09_TESTS/governance/validate_stage_execution_invariants.py'
    code=r'''
    crossmat = inv.get('CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS') or {}
    if crossmat.get('invariant_uid') != 'GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
        failures.append('cross_stage_materialization_invariant_uid_missing')
    if crossmat.get('required_artifact') != 'CROSS_STAGE_HANDOFF_READINESS_LEDGER' or crossmat.get('applies_to_all_registered_stages') is not True:
        failures.append('cross_stage_materialization_contract_missing')
    if crossmat.get('reference_presence_is_materialization') is not False or crossmat.get('physical_materialization_required') is not True:
        failures.append('reference_vs_materialization_separation_missing')
    for key in ('parse_required','schema_version_identity_required','required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_universe_reconciliation_before_stage_exit'):
        if crossmat.get(key) is not True:
            failures.append('cross_stage_readiness_flag_missing:' + key)
    if set(crossmat.get('required_row_fields') or []) != set(HANDOFF_REQUIRED_FIELDS_FOR_VALIDATOR):
        failures.append('cross_stage_handoff_row_schema_drift')
    if crossmat.get('historical_or_reference_only_completion_credit') != 0:
        failures.append('reference_only_completion_credit_leak')
    if crossmat.get('downstream_discovered_upstream_gap') != 'STOP_REENTER_EARLIEST_OWNER_MARK_DESCENDANTS_REVERIFY_REQUIRED':
        failures.append('upstream_reentry_disposition_missing')

    bcross = bp.get('cross_stage_materialization_consumer_readiness_contract') or {}
    if bcross.get('required') is not True or bcross.get('audit_item_uid') != 'AUD-GOV-014' or bcross.get('validator_uid') != 'VAL-GOV-035':
        failures.append('acceptance_cross_stage_readiness_binding_missing')
    catalog = load(root, '10_REGISTRY/AUDIT_CATALOG.yaml')
    aud14 = next((x for x in catalog.get('items') or [] if x.get('audit_item_uid') == 'AUD-GOV-014'), None)
    if not isinstance(aud14, dict) or aud14.get('audit_type') != 'CROSS_STAGE_MATERIALIZATION_AND_CONSUMER_READINESS' or aud14.get('validator_uid') != 'VAL-GOV-035':
        failures.append('audit_catalog_cross_stage_item_missing')

    for sid, stage in stage_map.items():
        gate = stage.get('cross_stage_materialization_gate') or {}
        if gate.get('required') is not True or gate.get('invariant_uid') != 'GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
            failures.append('cross_stage_gate_missing:' + str(sid))
        for key in ('reference_resolution_required','physical_materialization_required','parse_schema_required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_reconciliation_before_exit'):
            if gate.get(key) is not True:
                failures.append('cross_stage_gate_flag_missing:' + str(sid) + ':' + key)
        if gate.get('reference_only_completion_credit') != 0:
            failures.append('cross_stage_reference_only_credit_leak:' + str(sid))

    st1 = stage_map.get('STAGE-01') or {}
    s1g = st1.get('source_capture_materialization_gate') or {}
    if s1g.get('required') is not True or s1g.get('source_declared_registry_manifest_candidate_anchor_dependency_must_be_physical_or_gap') is not True or s1g.get('reference_only_source_dependency_may_receive_stage1_completion_credit') is not False or s1g.get('missing_required_physical_owner_disposition') != 'SOURCE_CAPTURE_GAP':
        failures.append('stage01_source_capture_materialization_gate_incomplete')
    st2x = stage_map.get('STAGE-02') or {}
    s2g = st2x.get('successor_readiness_gate') or {}
    if s2g.get('required') is not True or s2g.get('functional_gap_zero_substitutes_stage03_visual_dependency_readiness') is not False or s2g.get('stage03_required_visual_dependency_reconciliation_required') is not True:
        failures.append('stage02_successor_readiness_gate_incomplete')
    st3x = stage_map.get('STAGE-03') or {}
    s3g = st3x.get('visual_materialization_gate') or {}
    if s3g.get('applicable_visual_anchor_registry_must_be_nonempty') is not True or s3g.get('declared_visual_candidate_requires_physical_evidence') is not True or s3g.get('single_overview_may_substitute_required_scenarios') is not False or s3g.get('missing_required_anchor_or_candidate_blocks_human_visual_review') is not True:
        failures.append('stage03_anchor_candidate_scenario_readiness_gate_incomplete')

    for key in ('reference_only_required_dependency_completion','physical_required_input_missing','required_input_schema_or_version_mismatch','required_input_required_field_incomplete','successor_required_edge_denominator_omission','successor_consumer_readiness_unproven','applicable_visual_anchor_registry_empty','declared_visual_candidate_without_physical_evidence','multi_state_visual_single_overview_without_explicit_simultaneous_state_proof'):
        if ur.get(key) != 'BLOCK':
            failures.append('construction_universal_cross_stage_rule_not_block:' + key)
'''
    # validator-local schema constant inserted at module level using AST-safe line position.
    s=p.read_text(encoding='utf-8')
    if 'HANDOFF_REQUIRED_FIELDS_FOR_VALIDATOR' not in s:
        import ast
        tree=ast.parse(s)
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='validate')
        line=fn.lineno-1; lines=s.splitlines()
        const="HANDOFF_REQUIRED_FIELDS_FOR_VALIDATOR="+repr(HANDOFF_REQUIRED_FIELDS)
        lines[line:line]=[const,'']
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    insert_before_final_return_in_function(p,'validate',code)

def harden_source_regression_v2216():
    import ast
    p=SOURCE/'09_TESTS/governance/test_v2_1_13_stage_execution_invariants.py'
    s=p.read_text(encoding='utf-8'); tree=ast.parse(s)
    if 'reference_only_handoff_is_not_ready' not in s:
        target=None
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='out' for t in node.targets):
                if isinstance(node.value,ast.Call):
                    target=node; break
        if target is None: raise RuntimeError('source regression package validation assignment missing')
        add=r'''
def handoff_ready(reference=True, physical=True, complete=True, denominator=True, consumer=True, unresolved=0):
    return bool(reference and physical and complete and denominator and consumer and unresolved == 0)
res.append(case('reference_only_handoff_is_not_ready', not handoff_ready(reference=True, physical=False)))
res.append(case('physical_but_required_field_incomplete_handoff_is_not_ready', not handoff_ready(complete=False)))
res.append(case('required_handoff_denominator_omission_is_not_ready', not handoff_ready(denominator=False)))
res.append(case('successor_consumer_not_ready_blocks_handoff', not handoff_ready(consumer=False)))
res.append(case('unresolved_required_dependency_blocks_handoff', not handoff_ready(unresolved=1)))
res.append(case('complete_materialized_consumer_ready_handoff_passes', handoff_ready()))
'''.strip('\n').splitlines()
        lines=s.splitlines(); lines[target.lineno-1:target.lineno-1]=add+['']
        s='\n'.join(lines)+'\n'
    old="out['total']==26 and out['passed_expectations']==26"
    if old in s:
        if s.count(old)!=1: raise RuntimeError('source regression expected-count selector drift')
        s=s.replace(old,"out['total']==32 and out['passed_expectations']==32")
    elif "out['total']==32 and out['passed_expectations']==32" not in s:
        raise RuntimeError('source regression terminal expectation not found')
    ast.parse(s); p.write_text(s,encoding='utf-8')

def harden_root_stage_engine_v2216():
    p=ROOT/'governance/ci/stage_execution_engine.py'
    add_set_literal_member_ast(p,'EVIDENCE_FIELDS','cross_stage_handoff')
    s=p.read_text(encoding='utf-8')
    if 'CROSS_STAGE_GATE_INVALID' not in s:
        import ast
        tree=ast.parse(s)
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='validate_definition_data')
        top_for=[x for x in fn.body if isinstance(x,ast.For)]
        stage_fors=[]
        for x in top_for:
            seg=ast.get_source_segment(s,x) or ''
            if 'stages.items()' in seg: stage_fors.append(x)
        if len(stage_fors)<2: raise RuntimeError('definition stage-loop selector drift')
        node=stage_fors[1]
        block=r'''
    for _sid,_stage in stages.items():
        _gate=_stage.get('cross_stage_materialization_gate') or {}
        if _gate.get('required') is not True or _gate.get('invariant_uid')!='GOV-INV-CROSS-STAGE-MATERIALIZATION-CONSUMER-READINESS-001':
            fail(f'CROSS_STAGE_GATE_INVALID:{_sid}')
        for _k in ('reference_resolution_required','physical_materialization_required','parse_schema_required_field_completeness_required','denominator_inclusion_required','successor_consumer_readiness_required','successor_required_input_reconciliation_before_exit'):
            if _gate.get(_k) is not True:
                fail(f'CROSS_STAGE_GATE_FLAG_MISSING:{_sid}:{_k}')
        if _gate.get('reference_only_completion_credit')!=0:
            fail(f'CROSS_STAGE_REFERENCE_ONLY_CREDIT_LEAK:{_sid}')
'''.strip('\n').splitlines()
        lines=s.splitlines(); lines[node.lineno-1:node.lineno-1]=block
        s='\n'.join(lines)+'\n'; ast.parse(s); p.write_text(s,encoding='utf-8')
    s=p.read_text(encoding='utf-8')
    if 'CROSS_STAGE_HANDOFF_INVALID' not in s:
        code=r'''
    handoff=e.get('cross_stage_handoff')
    if not isinstance(handoff,dict):
        fail('CROSS_STAGE_HANDOFF_INVALID')
    required_handoff_fields={'ledger_ref','external_receipt','successor_stage_uid','reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete','unresolved_required_dependency_total','status'}
    if not required_handoff_fields.issubset(handoff):
        fail('CROSS_STAGE_HANDOFF_FIELD_MISSING')
    if handoff.get('successor_stage_uid')!=st.get('next_stage_uid'):
        fail('CROSS_STAGE_HANDOFF_SUCCESSOR_DRIFT')
    if handoff.get('status') not in {'PASS','BLOCKED'}:
        fail('CROSS_STAGE_HANDOFF_STATUS_INVALID')
    if not isinstance(handoff.get('unresolved_required_dependency_total'),int) or handoff.get('unresolved_required_dependency_total')<0:
        fail('CROSS_STAGE_HANDOFF_UNRESOLVED_COUNT_INVALID')
    if not handoff.get('external_receipt'):
        ref=str(handoff.get('ledger_ref') or '')
        if not ref or not (ROOT/ref).is_file():
            fail('CROSS_STAGE_HANDOFF_LEDGER_PHYSICAL_REF_MISSING')
    if e.get('result')=='PASS':
        for key in ('reference_resolution_complete','physical_materialization_complete','required_field_completeness_complete','denominator_reconciled','consumer_readiness_complete'):
            if handoff.get(key) is not True:
                fail('PASS_WITH_CROSS_STAGE_HANDOFF_NOT_READY:'+key)
        if handoff.get('unresolved_required_dependency_total')!=0 or handoff.get('status')!='PASS':
            fail('PASS_WITH_UNRESOLVED_CROSS_STAGE_HANDOFF')
'''
        insert_before_assignment_in_function(p,'validate_evidence_data','gates',code)

def harden_root_stage_engine_test_v2216():
    import ast
    p=ROOT/'governance/ci/test_stage_execution_engine.py'
    s=p.read_text(encoding='utf-8'); tree=ast.parse(s)
    if "'cross_stage_handoff'" not in s and '"cross_stage_handoff"' not in s:
        # Add the synthetic handoff immediately after sample dict construction.
        marker="eng.validate_evidence_data(stage_uid,deepcopy(sample))"
        if s.count(marker)!=1: raise RuntimeError('root test sample selector drift')
        payload="""sample['cross_stage_handoff']={'ledger_ref':'synthetic://external','external_receipt':True,'successor_stage_uid':st['next_stage_uid'],'reference_resolution_complete':True,'physical_materialization_complete':True,'required_field_completeness_complete':True,'denominator_reconciled':True,'consumer_readiness_complete':True,'unresolved_required_dependency_total':0,'status':'PASS'}\n"""
        s=s.replace(marker,payload+marker)
    if "cross_stage_gate_missing" not in s:
        anchor="block('partial_stage_exit_allowed',lambda p,a:p['stages'][0].__setitem__('partial_work_unit_closure_may_grant_stage_exit',True))"
        if s.count(anchor)!=1: raise RuntimeError('root test definition anchor drift')
        s=s.replace(anchor,anchor+"\nblock('cross_stage_gate_missing',lambda p,a:p['stages'][0].pop('cross_stage_materialization_gate'))")
    if "handoff_reference_resolution_false" not in s:
        anchor="block_evidence('blocked_without_blocked_phase',make_blocked_without_phase)"
        if s.count(anchor)!=1: raise RuntimeError('root test evidence anchor drift')
        extra=r'''
block_evidence('handoff_reference_resolution_false',lambda x:x['cross_stage_handoff'].__setitem__('reference_resolution_complete',False))
block_evidence('handoff_physical_materialization_false',lambda x:x['cross_stage_handoff'].__setitem__('physical_materialization_complete',False))
block_evidence('handoff_required_field_completeness_false',lambda x:x['cross_stage_handoff'].__setitem__('required_field_completeness_complete',False))
block_evidence('handoff_denominator_not_reconciled',lambda x:x['cross_stage_handoff'].__setitem__('denominator_reconciled',False))
block_evidence('handoff_consumer_not_ready',lambda x:x['cross_stage_handoff'].__setitem__('consumer_readiness_complete',False))
block_evidence('handoff_unresolved_required_dependency',lambda x:x['cross_stage_handoff'].__setitem__('unresolved_required_dependency_total',1))
'''.strip('\n')
        s=s.replace(anchor,anchor+"\n"+extra)
    old="negative regression {cases}/32"
    if old in s:
        s=s.replace(old,"negative regression {cases}/39")
    elif "negative regression {cases}/39" not in s:
        raise RuntimeError('root test expected count marker missing')
    ast.parse(s); p.write_text(s,encoding='utf-8')

def record_governance_finding_v2216():
    p=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
    d=load(p); rows=d.setdefault('findings',[])
    uid='FIND-20260920-CROSS-STAGE-MATERIALIZATION-001'
    if not any(x.get('finding_uid')==uid for x in rows):
        rows.append({
            'finding_uid':uid,
            'class':'GLOBAL_SHARED_GOVERNANCE_EXECUTION_DEFECT',
            'title':'Reference resolution could receive Stage completion without physical downstream materialization and consumer readiness',
            'evidence':'CORE-01 Stage-01 retained CHANGE-CORE-001 anchor/candidate references without physical owner materialization; Stage-02 denominator omitted Stage-03 visual dependency readiness; Stage-03 then produced empty visual_anchor_uids while previous machine gates passed.',
            'affected_scope':'ALL_REGISTERED_STAGE_HANDOFFS',
            'disposition':'AUTHORIZED_SUCCESSOR_GOVERNANCE_HARDENING',
            'authorization_uid':AUTH_UID,
            'specification_change_required':True,
            'formal_specification_mutated_for_fix':True,
            'product_stage_credit':0
        })
    dump(p,d)

def update_current_projection_v2216(semantic_hash,bundle_hash,zip_hash,checksums_hash):
    manifestp=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    m=load(manifestp); old_sl=copy.deepcopy(m.get('source_lineage') or {})
    m['artifact_uid']=NEW_UID; m['display_version']=NEW_DISPLAY
    sl=m.setdefault('source_lineage',{})
    sl.update({
        'verified_package_filename':NEW_PACKAGE,'verified_package_sha256':zip_hash,
        'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,
        'source_bytes_changed_by_this_successor':True,'source_identity_reused_only_because_source_bytes_are_unchanged':False,
        'deterministic_source_bundle_sha256':bundle_hash,'checksum_manifest_sha256':checksums_hash,
        'semantic_authority_content_hash':semantic_hash,'verified_source_revision':NEW_SOURCE_REV,
        'predecessor_verified_package_filename':old_sl.get('verified_package_filename'),
        'predecessor_verified_package_sha256':old_sl.get('verified_package_sha256'),
        'post_promotion_projector_sync_authorization_uid':AUTH_UID
    })
    dump(manifestp,m)

    rp=ROOT/'governance/specifications/REGISTRY.yaml'
    r=load(rp); a=r['active_specification']
    a['governance_uid']=NEW_UID; a['display_version']=NEW_DISPLAY
    unique_extend(a.setdefault('aliases',[]),['cross-stage-materialization-consumer-readiness-hardening'])
    r['immediate_predecessor']={
        'governance_uid':OLD_UID,'display_version':OLD_DISPLAY,
        'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY',
        'status':'SUPERSEDED_HISTORY_ONLY_AFTER_CROSS_STAGE_MATERIALIZATION_CONSUMER_READINESS_HARDENING'
    }
    dump(rp,r)

    cp=ROOT/'GOVERNANCE_CURRENT.yaml'
    c=load(cp); c['active_governance_uid']=NEW_UID; c['display_version']=NEW_DISPLAY
    c.setdefault('source_identity',{}).update({
        'verified_package_sha256':zip_hash,'deterministic_source_bundle_sha256':bundle_hash,
        'checksum_manifest_sha256':checksums_hash,'semantic_authority_content_hash':semantic_hash,
        'verified_source_revision':NEW_SOURCE_REV,'source_bytes_changed_by_current_successor':True
    })
    dump(cp,c)

    ap=ROOT/'governance/test/ACTIVE_STATE.yaml'
    st=load(ap)
    if st.get('current_primary_task_layer')!='GOVERNANCE_MAINTENANCE' or (st.get('active_work_unit') or {}).get('work_unit_uid')!=WORK_UNIT:
        raise RuntimeError('active governance WU drift before projection')
    st['specification_uid']=NEW_UID
    gt=st.setdefault('governance_revision_transition',{})
    gt.update({
        'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,
        'fresh_revalidation_required':True,
        'fresh_revalidation_scope':'STAGE01_SOURCE_CAPTURE_THROUGH_STAGE03_VISUAL_READINESS_AND_ALL_11_STAGE_HANDOFF_DEFINITION',
        'predecessor_stage03_evidence_role':'HISTORICAL_PREDECESSOR_EVIDENCE_ONLY',
        'website_construction_remains_blocked':True,'deployment_remains_blocked':True
    })
    aw=st['active_work_unit']
    aw['current_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'
    aw['promoted_governance_uid']=NEW_UID
    aw['product_stage_credit']=0
    st['active_work_unit']=aw
    sw=st.get('suspended_product_work_unit_for_cross_stage_governance_hardening') or {}
    if sw.get('work_unit_uid')=='WU-STAGE03-CORE01-VISUAL-DESIGN-001':
        sw['current_status']='REVERIFY_REQUIRED_UPSTREAM_SOURCE_CAPTURE_AND_SUCCESSOR_READINESS'
        sw['product_blocker_credit']=0
        hb=sw.setdefault('human_review_boundary',{})
        hb.update({'visual_review':'NOT_REACHED_REVERIFY_REQUIRED','visual_approval':False,'authority_update':False,'design_freeze':False})
        sw['reentry_owner_capability']='SOURCE_INTAKE_BASE_BLUEPRINT'
        sw['reentry_stage_uid']='STAGE-01'
        sw['reentry_reason']='SOURCE_DECLARED_VISUAL_ANCHOR_AND_CANDIDATE_REFERENCES_NOT_PHYSICALLY_MATERIALIZED_OR_CONSUMER_READY'
        st['suspended_product_work_unit_for_cross_stage_governance_hardening']=sw
    att=st.get('stage03_active_attempt') or {}
    if att:
        att['closure_credit_under_current_governance']=False
        att['fresh_revalidation_required']=True
        att['evidence_role']='PREDECESSOR_HISTORICAL_ONLY_AFTER_V2_2_16'
        att['human_visual_review_status']='REVOKED_REVERIFY_REQUIRED'
        att['next_action']='REENTER_STAGE01_SOURCE_CAPTURE_MATERIALIZATION_CONTINUITY'
        st['stage03_active_attempt']=att
    ex=st.get('execution') or {}
    if isinstance(ex.get('stage3'),dict):
        ex['stage3']['stage_exit_allowed']=False
        ex['stage3']['human_visual_review_reached']=False
        ex['stage3']['human_visual_review_status']='REVOKED_REVERIFY_REQUIRED'
        ex['stage3']['result']='PREDECESSOR_RESULT_REVERIFY_REQUIRED'
    ex['website_construction_allowed']=False; ex['deployment_allowed']=False
    st['execution']=ex
    st['status']='ACTIVE_GOVERNANCE_CROSS_STAGE_MATERIALIZATION_HARDENING_PROMOTED_REVALIDATION_REQUIRED'
    st['next_action']='RUN_V2_2_16_EXACT_HEAD_FULL_LINE_SELECTED_PROFILE_AND_CROSS_STAGE_REGRESSION'
    st['resume_control']={
        'current_resume_point':'V2_2_16_CROSS_STAGE_MATERIALIZATION_SUCCESSOR_PROMOTED_REVALIDATION_REQUIRED',
        'current_work_unit_uid':WORK_UNIT,
        'current_owner':'governance/specifications/current/SPECIFICATION_MUTATION_CONTROL.yaml',
        'exact_next_action':'RUN_V2_2_16_EXACT_HEAD_FULL_LINE_SELECTED_PROFILE_AND_CROSS_STAGE_REGRESSION',
        'suspended_product_work_unit_uid':'WU-STAGE03-CORE01-VISUAL-DESIGN-001',
        'suspended_product_resume_point':'REENTER_STAGE01_SOURCE_CAPTURE_MATERIALIZATION_CONTINUITY'
    }
    dump(ap,st)

    sp=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    if sp.exists():
        q=load(sp)
        q['governance_uid']=NEW_UID
        q['fresh_revalidation_required']=True
        q['stage_exit_credit_allowed']=False
        q['closure_status']='REVERIFY_REQUIRED_UPSTREAM_SOURCE_CAPTURE_AND_SUCCESSOR_READINESS'
        q['next_action']='REENTER_STAGE01_SOURCE_CAPTURE_MATERIALIZATION_CONTINUITY'
        x=copy.deepcopy(q); x.pop('content_hash',None)
        q['content_hash']=hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()
        dump(sp,q)

def update_candidate_state_v2216():
    p=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    d=load(p)
    d['candidate']='v2.2.16_CROSS_STAGE_MATERIALIZATION_CONSUMER_READINESS_HARDENING_CANDIDATE'
    d['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'
    repairs=d.setdefault('current_repairs',[])
    unique_extend(repairs,[
        'CROSS_STAGE_REFERENCE_VS_MATERIALIZATION_SEPARATION',
        'CROSS_STAGE_REQUIRED_FIELD_COMPLETENESS',
        'SUCCESSOR_CONSUMER_READINESS',
        'STAGE01_SOURCE_CAPTURE_MATERIALIZATION',
        'STAGE02_SUCCESSOR_VISUAL_DEPENDENCY_READINESS',
        'STAGE03_ANCHOR_CANDIDATE_MULTI_STATE_READINESS',
        'ALL_STAGE_HANDOFF_FALSE_COMPLETION_GUARD'
    ])
    fr=d.setdefault('fresh_revalidation',{})
    fr.update({
        'required':True,'current_source_revision':NEW_SOURCE_REV,
        'current_closure_credit':False,'predecessor_evidence_current_closure_credit':False,
        'persisted_head_full_line_required':True,'historical_evidence_may_close_successor':False
    })
    dump(p,d)
    rp=SOURCE/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml'
    rv=load(rp)
    if 'governance_revision' in rv: rv['governance_revision']=NEW_SOURCE_REV
    dump(rp,rv)

def apply_v2216():
    current=load(ROOT/'GOVERNANCE_CURRENT.yaml')
    if current.get('active_governance_uid') not in (OLD_UID,NEW_UID):
        raise RuntimeError('unexpected current governance uid')
    auth=ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
    if not auth.exists(): raise RuntimeError('preexisting authorization missing')
    a=load(auth)
    if a.get('status')!='AUTHORIZED_EXACT_SCOPE' or a.get('current_governance_uid_at_authorization')!=OLD_UID:
        raise RuntimeError('authorization receipt invalid or wrong predecessor')

    add_mother_sections_v2216()
    add_section_registry_v2216()
    mutate_stage_invariant_v2216()
    semantic_hash=mutate_lifecycle_and_reference_v2216()
    mutate_audit_and_index_v2216()
    mutate_current_components_v2216()
    harden_source_validator_v2216()
    harden_source_regression_v2216()
    harden_root_stage_engine_v2216()
    harden_root_stage_engine_test_v2216()
    record_governance_finding_v2216()
    update_candidate_state_v2216()

    # Recompute semantic baseline after all source mutations that can affect registered semantics.
    sp=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    sem=load(sp); sem['governance_revision']=NEW_SOURCE_REV; sem['content_hash']=hobj(sem); dump(sp,sem)
    semantic_hash=sem['content_hash']

    checks,bundle,zips=refresh_source(semantic_hash)
    update_current_projection_v2216(semantic_hash,bundle,zips,checks)
    return {'semantic_hash':semantic_hash,'checksums_hash':checks,'bundle_hash':bundle,'zip_hash':zips}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=['precheck','promote'],required=True)
    args=ap.parse_args()
    result=apply_v2216()
    validate_all()
    print(json.dumps({'mode':args.mode,'new_uid':NEW_UID,**result},indent=2))
    if args.mode=='precheck':
        print('PRECHECK_PASS_NO_COMMIT')
        return 0
    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','-A')
    if run('git','diff','--cached','--quiet',check=False).returncode==0:
        raise RuntimeError('no promotion delta')
    msg='feat(governance): promote cross-stage materialization consumer readiness hardening\n\nSpec-Change-Authorization: '+AUTH_UID+'\nSpec-Change-Scope: ALL_STAGE_REFERENCE_PHYSICAL_COMPLETENESS_DENOMINATOR_CONSUMER_READINESS'
    run('git','commit','-m',msg)
    run(sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py'))
    run('git','push','origin','HEAD:rebuild-v2.1.1')
    print('PROMOTION_PUSHED',run('git','rev-parse','HEAD').stdout.strip())
    return 0

if __name__=='__main__':
    raise SystemExit(main())
