#!/usr/bin/env python3
from pathlib import Path
import hashlib, io, json, lzma, re, subprocess, tarfile, zipfile, yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.github/governance-source/active/source'
AUTH_UID = 'USR-DIRECTIVE-20260919-MOTHER-SCOPE-STAGE-OWNERSHIP-REENTRY-PORTABILITY-HARDENING-R1'
OLD_UID = 'GOV-REV-20260918-DESIGN-REMEDIATION-ROUTING-HARDENING'
NEW_UID = 'GOV-REV-20260919-SCOPE-STAGE-REENTRY-PORTABILITY-HARDENING'
DISPLAY_VERSION = 'v2.2.6'
SOURCE_REVISION = 'v2.2.5-scope-stage-reentry-portability-hardening'
PACKAGE_FILENAME = 'AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.5_SCOPE_STAGE_REENTRY_PORTABILITY_HARDENING_LOCAL_VERIFIED.zip'
AUTH = ROOT / f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
HELPER = ROOT / '.github/governance-maintenance/materialize_scope_stage_reentry_successor.py'
WORKFLOW = ROOT / '.github/workflows/scope-stage-reentry-governance-successor.yml'
M1 = SOURCE / '12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md'
M2 = SOURCE / '12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md'
M3 = SOURCE / '12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md'
M4 = SOURCE / '12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md'
LIFECYCLE = SOURCE / '10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'

def load(p):
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

def write(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def run(*a, cwd=ROOT):
    print('+', ' '.join(map(str, a)))
    subprocess.run(a, cwd=cwd, check=True)

def append_section(path, uid, title, body):
    text = path.read_text(encoding='utf-8').rstrip() + '\n'
    marker = f'<!-- SECTION_UID: {uid} -->'
    if marker in text:
        raise RuntimeError(f'SECTION_ALREADY_EXISTS:{uid}')
    text += f'\n{marker}\n## {title}\n\n{body.strip()}\n'
    path.write_text(text, encoding='utf-8')

def patch_mother():
    append_section(M1, 'WEB-GOV-01-S075', 'Execution Scope Authority / Capability Ownership / Upstream Re-entry', '''
Every governed execution cycle and Work Unit MUST resolve one Current EXECUTION_SCOPE_MANIFEST before product analysis, design remediation, validation, implementation, verification, release, deployment, or closure work begins. The manifest is execution state, not reusable Product Authority. It MUST identify scope UID and scope kind; included, excluded, and remaining governed units; scope-selection Authority; owning capability; predecessor and dependency closure references; denominator sources; partial-scope status; Stage-exit-credit policy; and an exact content hash.

Reusable Mother Policy MUST NOT encode a concrete page UID, page combination, route, product module, blocker count, expected problem count, historical run denominator, or project-specific file list as the common execution scope. Those values belong to the selected Product/Execution Profile or Current run-state manifest. A product adapter MAY name concrete product identities only inside its explicitly registered local scope and MUST NOT redefine common policy, common applicability, or the denominator of a reusable validator.

Work Unit closure and Stage/capability closure are different decisions. A partial Work Unit MAY close when its exact included scope satisfies its Definition of Done, but it MUST persist remaining scope and MUST NOT grant Stage exit credit while required governed units remain. Stage closure MUST reconcile the declared Stage universe against completed, formally non-applicable, blocked, and remaining units from Current scope/denominator Authority; it MUST NOT infer completion from one successful subset.

Capability ownership is semantic. Source-intake/base-blueprint capability owns source capture, enumeration, source facts, responsibility classification, and base blueprint identities. Functional-contract capability owns Business Entity lifecycle and hierarchy, required operations, field/data/action boundaries, payload/input-source contracts, state/transition/error/recovery/audit contracts, functional workbench boundaries and operation order, interaction/context continuity, conditional AI-interaction identity, finalization/version lifecycle, dependency/change-impact semantics, and function-to-visual impact classification. Visual-design capability owns approved visual projection and geometry without redefining functional semantics. Freeze owns the accepted immutable denominator. Implementation owns code/runtime/data materialization of frozen contracts. Verification owns executable QA evidence. Build/release, staging, production cutover, production acceptance, and closure/operations each own their corresponding downstream evidence and transition.

Replaying an earlier capability MUST NOT be treated as repairing a later-capability defect unless the earlier capability's own Current input or output is proven defective, changed, stale, or incomplete. In particular, re-running source intake or base blueprint compilation does not satisfy a missing functional-contract decision when source/base-blueprint truth is unchanged.

When any later capability discovers a required semantic fact, interaction topology, visual decision, frozen denominator, implementation contract, verification condition, release identity, deployment condition, or production-acceptance condition that belongs to an earlier capability, execution MUST stop downstream mutation and reopen the owning capability. Impacted descendants MUST become REVERIFY_REQUIRED; unaffected evidence MAY remain reusable only when reverse-dependency analysis proves it unchanged. After the owner closes under Current Authority, execution resumes from the earliest impacted successor boundary with fresh evidence.

Whenever a missing REQUIRED function or contract is analyzed for automatic completion or Design/Contract Remediation, FUNCTION_ADMISSION_SCORECARD and AUTO_COMPLETION_SCOPE_LEDGER are required analysis outputs even when the final disposition is NO_AUTO_COMPLETION, REVIEW_ONLY_DESIGN_CANDIDATE, AUTHORITY_GAP, or BLOCKED. Their purpose is to prove boundedness and routing; neither artifact creates Product Authority.
''')

    append_section(M2, 'WEB-GOV-02-S074', 'Scope-Bound Delivery / Re-entry / Temporary-to-Formal Boundary', '''
Implementation and delivery MUST consume the frozen EXECUTION_SCOPE_MANIFEST, functional contracts, approved visual projection, dependency closure, and acceptance denominator applicable to the exact Work Unit. Reusable implementation validators, runners, and workflow helpers MUST derive included units and denominators from Current manifests/registers. A literal product page set, module list, blocker count, expected gap count, prior-run report count, or manually copied denominator MUST NOT define reusable completion.

A registered product adapter MAY contain concrete product identities needed to invoke a local implementation or test, but those identities MUST be resolved against the Current scope manifest and typed program identity/owner registries before use. The adapter MUST fail when a requested identity is outside Current scope and MUST NOT expand the scope, Stage universe, or common denominator by code literals.

If implementation or any later delivery capability discovers an upstream functional, interaction, visual, freeze, Authority, dependency, or acceptance-definition defect, it MUST stop the affected downstream write path and return the issue to the owning capability. Downstream code MUST NOT invent a local substitute. The impact closure MUST mark affected descendants REVERIFY_REQUIRED and resume only after the upstream canonical owner is materially corrected and freshly revalidated.

Temporary analysis, mutation-test, destructive-test, candidate, harness, or intermediate artifacts are non-authoritative. They MAY exist only inside an explicitly declared temporary cycle and MUST have owner, lifecycle, cleanup disposition, and promotion boundary. Formal Full-Line, Foundation Freeze, Release Candidate, Staging, Production Cutover, Production Acceptance, and terminal closure gates require temporary residual count zero unless a Current Authority explicitly classifies the artifact as required non-current evidence outside the temporary root.

A formal gate blocked solely because temporary residuals still exist is an execution-environment or lifecycle-hygiene block. It MUST NOT be reported as proof that the underlying Design/Contract Candidate is semantically invalid. Candidate semantic validation and formal package cleanliness are separate evidence dimensions and both must pass at their proper boundaries.

No downstream delivery PASS may compensate for an unresolved upstream owning-capability gap. Conversely, a governance, validator, workflow, or temporary-artifact fix receives zero product completion credit until the product owner is freshly executed and the affected product denominator changes through Current evidence.
''')

    append_section(M3, 'WEB-GOV-03-S069', 'Execution Scope Manifest / Dynamic Denominator / Capability Re-entry Control', '''
Every governed execution iteration MUST use this order:

1. Resolve Current Governance, Product/Execution Profile, Current Primary Task Layer, and legal Work Unit.
2. Resolve or materialize one EXECUTION_SCOPE_MANIFEST from Current Authority, applicability, dependency closure, and persisted state.
3. Derive all product units and denominators from that manifest plus Current physical scan/registered manifests; never from literal reusable-code page lists or historical expected counts.
4. Execute only included scope. Persist excluded and remaining scope explicitly.
5. Classify every discovered issue by owning capability before remediation.
6. For INPUT_SOURCE_GAP or ARCHITECTURE_GAP without a unique role-correct Current closure, enter bounded Design/Contract Remediation with FUNCTION_ADMISSION_SCORECARD and AUTO_COMPLETION_SCOPE_LEDGER. Only two or more materially distinct viable behaviors become AUTHORITY_GAP.
7. Materialize approved content only to the single Current canonical owner, then rerun the affected owner and reverse-dependency closure from fresh inputs/evidence.
8. A partial Work Unit may receive local closure credit only for its exact scope. Stage/capability exit requires reconciliation of the full declared required universe and cannot be granted while remaining required scope exists.
9. If a downstream capability discovers an upstream-owned defect, stop downstream mutation, reopen the owning capability, mark affected descendants REVERIFY_REQUIRED, preserve proven-unaffected evidence, and resume at the earliest impacted successor boundary.

Reusable validators/scanners/classifiers/remediation executors MUST be scope-parametric. Product IDs, page IDs, provider IDs, fixed page combinations, blocker counts, gap counts, write-set counts, and retry/run identifiers MAY be asserted only when they are resolved from a Current product/profile/Work Unit manifest or typed adapter input. Such values MUST NOT appear as the implicit denominator of a reusable consumer.

The current denominator for an execution cycle MUST be computed from Current scope plus physical scan and legal successor reconciliation. Raw discovery count, effective open count, resolved count, remaining-scope count, and external/shared Authority count are separate values. A validator MUST NOT force effective open count to equal raw historical discovery count after a legal Current successor closes a signature.

Temporary cycles MUST declare temporary roots and cleanup boundaries. Temporary residuals may block a formal cleanliness gate, but this classification is TEMPORARY_LIFECYCLE_RESIDUAL, not PRODUCT_SEMANTIC_FAILURE. Temporary output MUST be promoted only through the registered candidate/approval/materialization path and MUST be absent from formal package roots at formal closure unless explicitly retained as legal non-current evidence.

Capability re-entry is owner-based, not stage-number-based Mother Policy. A selected Execution Profile MAY map source intake, functional contract, visual design, freeze, implementation, verification, build/release, staging, cutover, production acceptance, and operations/closure capabilities to concrete stage UIDs. Changing that profile mapping MUST NOT require Mother Policy changes.
''')

    append_section(M4, 'WEB-GOV-04-S083', 'Dynamic Scope / Ownership / Re-entry / Consumer Portability Audit', '''
Audit MUST verify one exact EXECUTION_SCOPE_MANIFEST for every governed Work Unit/cycle and prove its included, excluded, remaining, dependency, denominator, partial-scope, and Stage-exit-credit fields came from Current Authority/profile/state rather than chat memory, old reports, or reusable-code literals.

For every reusable validator, scanner, classifier, remediation executor, projector, or common workflow helper, Audit MUST prove that concrete product page/module identities, fixed product page combinations, blocker/gap counts, and historical run denominators do not define the common scope or expected completion denominator. Product/profile adapters may contain concrete identities only when their local-adapter role is explicit and the values are checked against the Current scope/identity authority.

Audit MUST distinguish Work Unit closure from Stage/capability closure. A partial-scope PASS with remaining required units MUST have zero Stage-exit credit. Remaining scope MUST be persisted and recoverable through Resume/Work Unit Resolution.

Audit MUST prove each discovered gap was routed to its owning capability. Re-running an earlier capability without a defect/change in that owner MUST NOT be credited as repairing a later-owned semantic gap. Downstream discovery of an upstream-owned defect MUST show: downstream stop, owner re-entry, impacted reverse-dependency set, REVERIFY_REQUIRED descendants, preserved unaffected evidence where proven, owner remediation, and fresh successor verification.

For missing required functional/contract behavior, Audit MUST require FUNCTION_ADMISSION_SCORECARD and AUTO_COMPLETION_SCOPE_LEDGER before completion/remediation routing. NO_AUTO_COMPLETION and review-only outcomes do not waive those artifacts. Review-only candidate evidence receives zero Product Authority or product blocker credit until approved content reaches the single Current canonical owner and fresh execution closes the affected signatures.

Audit MUST independently report candidate semantic result and temporary/formal package cleanliness. A TEMPORARY_LIFECYCLE_RESIDUAL may block Full-Line or formal closure, but MUST NOT be mislabeled as candidate semantic invalidity. Formal Freeze/Release/Deployment/Production closure requires zero unauthorized temporary residuals.

Portability audit MUST substitute materially different product/profile scope identities and denominators without changing common Mother Policy. If reusable policy or reusable execution consumers require edits merely because page names, module count, blocker count, or profile-local execution scope changes, portability MUST FAIL.
''')

def patch_machine():
    p = ROOT / 'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'
    d = load(p)
    d['execution_scope_manifest_contract'] = {
        'required_for_every_governed_work_unit_or_cycle': True,
        'artifact': 'EXECUTION_SCOPE_MANIFEST',
        'layer': 'RUN_STATE_NON_NORMATIVE',
        'required_fields': [
            'scope_uid','scope_kind','included_units','excluded_units','remaining_units',
            'scope_selection_authority','owning_capability','dependency_closure_refs',
            'denominator_source_refs','partial_scope','stage_exit_credit_allowed','content_hash'
        ],
        'reusable_consumer_literal_product_scope_as_denominator': 'BLOCK',
        'reusable_consumer_literal_problem_count_as_denominator': 'BLOCK',
        'work_unit_closure_is_stage_exit': False,
        'partial_scope_stage_exit_credit': 0,
        'stage_exit_requires_declared_required_universe_reconciliation': True,
    }
    d['capability_ownership_and_reentry_contract'] = {
        'SOURCE_INTAKE_BASE_BLUEPRINT': ['SOURCE_CAPTURE','SOURCE_FACTS','RESPONSIBILITY_CLASSIFICATION','BASE_BLUEPRINT'],
        'FUNCTIONAL_CONTRACT': ['BUSINESS_ENTITY_LIFECYCLE','OPERATION_HIERARCHY','FIELD_DATA_ACTION_BOUNDARY','PAYLOAD_INPUT','STATE_TRANSITION','ERROR_RECOVERY_AUDIT','FUNCTIONAL_WORKBENCH','INTERACTION_TOPOLOGY','AI_INTERACTION_IDENTITY','FINALIZATION_VERSION','DEPENDENCY_CHANGE_IMPACT','FUNCTION_VISUAL_IMPACT'],
        'VISUAL_DESIGN': ['VISUAL_PROJECTION','GEOMETRY','RESPONSIVE_REFLOW'],
        'FOUNDATION_FREEZE': ['FROZEN_DENOMINATOR','ACCEPTANCE_BLUEPRINT'],
        'IMPLEMENTATION': ['FRONTEND','CONTROL_HANDLER','API_RUNTIME','DATA_PERSISTENCE','ASYNC_STORAGE_EXTERNAL_ADAPTER'],
        'VERIFICATION': ['UNIT_INTEGRATION_PERMISSION_BROWSER_VISUAL_I18N_ACCESSIBILITY_QA'],
        'BUILD_RELEASE': ['BUILD_IDENTITY','RELEASE_CANDIDATE'],
        'STAGING': ['STAGING_EXECUTION_AND_ACCEPTANCE'],
        'PRODUCTION_CUTOVER': ['DEPLOYMENT_AND_RUNTIME_RELEASE_IDENTITY'],
        'PRODUCTION_ACCEPTANCE': ['PRODUCTION_BROWSER_DATA_EFFECTFUL_VISUAL_ACCEPTANCE'],
        'CLOSURE_OPERATIONS': ['MONITORING_RECOVERY_ROLLBACK_FINAL_RECONCILIATION'],
        'downstream_may_patch_upstream_owned_gap': False,
        'downstream_discovery_action': 'STOP_AND_REOPEN_OWNING_CAPABILITY',
        'impacted_descendants': 'REVERIFY_REQUIRED',
        'unaffected_evidence_may_be_preserved_only_by_reverse_dependency_proof': True,
        'source_replay_repairs_functional_contract_without_source_or_base_defect': False,
    }
    d['temporary_cycle_transition_contract'] = {
        'temporary_layer_is_authority': False,
        'temporary_cycle_must_declare_root_owner_and_cleanup_boundary': True,
        'formal_full_line_freeze_release_deployment_closure_requires_temporary_residual_zero': True,
        'temporary_residual_classification': 'TEMPORARY_LIFECYCLE_RESIDUAL',
        'temporary_residual_is_candidate_semantic_failure': False,
        'promotion_requires_registered_candidate_approval_materialization_path': True,
    }
    write(p, d)

    p = ROOT / 'governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml'
    d = load(p)
    r = d.setdefault('rules', {})
    admission = r.setdefault('FUNCTION_ADMISSION_NECESSITY_AND_UTILITY', {})
    admission['activation'] = 'MISSING_REQUIRED_FUNCTION_OR_CONTRACT_ANALYZED_FOR_COMPLETION_OR_DESIGN_REMEDIATION'
    admission['required_even_when_outcome_is_no_auto_completion_or_review_only'] = True
    bounded = r.setdefault('BOUNDED_FUNCTIONAL_COMPLETION', {})
    bounded['scope_ledger_required_even_when_auto_completion_not_activated'] = True
    bounded['no_auto_completion_is_legal_terminal_analysis_disposition'] = True
    bounded['stage1_replay_without_stage1_defect_may_close_stage2_functional_gap'] = False
    bounded['approved_candidate_requires_fresh_owner_and_reverse_dependency_reexecution'] = True
    write(p, d)

    p = ROOT / 'governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml'
    d = load(p)
    d['scope_and_reentry_boundary'] = {
        'execution_scope_manifest_required': True,
        'partial_work_unit_closure_may_grant_stage_exit': False,
        'remaining_scope_must_persist': True,
        'reusable_validator_literal_product_scope_or_count_as_denominator': 'BLOCK',
        'downstream_upstream_owner_mismatch': 'STOP_REOPEN_OWNER_AND_REVERIFY_IMPACTED_DESCENDANTS',
        'source_replay_without_source_defect_as_downstream_remediation': 'BLOCK',
    }
    d['temporary_formalization_boundary'] = {
        'temporary_artifact_is_authority': False,
        'temporary_residual_zero_before_formal_full_line_freeze_release_or_closure': True,
        'temporary_residual_block_is_semantic_candidate_failure': False,
        'candidate_semantic_result_and_package_cleanliness_are_separate': True,
    }
    write(p, d)

    p = ROOT / 'governance/specifications/current/GOVERNANCE_LAYER_SEPARATION_AND_PORTABILITY.yaml'
    d = load(p)
    pc = d.setdefault('promotion_contamination_guard', {})
    pc['product_page_or_module_identity_in_common_policy'] = 'BLOCK'
    pc['fixed_product_scope_combination_in_common_policy'] = 'BLOCK'
    pc['fixed_product_problem_or_blocker_count_in_common_policy'] = 'BLOCK'
    d['reusable_consumer_portability'] = {
        'reusable_validator_runner_scanner_projector_scope_parametric': True,
        'literal_product_identity_may_define_common_denominator': False,
        'literal_historical_problem_count_may_define_common_denominator': False,
        'registered_product_adapter_may_name_concrete_identity': True,
        'product_adapter_must_validate_identity_against_current_scope_manifest': True,
        'product_adapter_may_redefine_common_policy_or_stage_universe': False,
    }
    write(p, d)

def patch_lifecycle():
    d = load(LIFECYCLE)
    refs = d.setdefault('normative_section_uids', [])
    for uid in ['WEB-GOV-01-S075','WEB-GOV-02-S074','WEB-GOV-03-S069','WEB-GOV-04-S083']:
        if uid not in refs:
            refs.append(uid)
    d['execution_scope_contract'] = {
        'current_scope_artifact': 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
        'scope_source': 'CURRENT_AUTHORITY_PROFILE_APPLICABILITY_DEPENDENCY_AND_PERSISTED_STATE',
        'work_unit_scope_source': 'EXECUTION_SCOPE_MANIFEST',
        'stage_exit_scope_source': 'DECLARED_STAGE_REQUIRED_UNIVERSE_RECONCILIATION',
        'partial_work_unit_closure_may_grant_stage_exit': False,
        'remaining_scope_persistence_required': True,
        'reusable_consumer_literal_product_scope_or_denominator': 'BLOCK',
    }
    d['capability_reentry_map'] = {
        'SOURCE_INTAKE_BASE_BLUEPRINT': 'STAGE-01',
        'FUNCTIONAL_CONTRACT': 'STAGE-02',
        'VISUAL_DESIGN': 'STAGE-03',
        'FOUNDATION_FREEZE': 'STAGE-04',
        'IMPLEMENTATION': 'STAGE-05',
        'VERIFICATION': 'STAGE-06',
        'BUILD_RELEASE': 'STAGE-07',
        'STAGING': 'STAGE-08',
        'PRODUCTION_CUTOVER': 'STAGE-09',
        'PRODUCTION_ACCEPTANCE': 'STAGE-10',
        'CLOSURE_OPERATIONS': 'STAGE-11',
        'downstream_gap_owned_by_earlier_capability': 'STOP_REOPEN_OWNER_MARK_IMPACTED_DESCENDANTS_REVERIFY_REQUIRED',
    }
    stages = d.get('stages') or []
    for s in stages:
        s['work_unit_scope_source'] = 'CURRENT_EXECUTION_SCOPE_MANIFEST'
        s['stage_exit_scope_source'] = 'DECLARED_STAGE_REQUIRED_UNIVERSE_RECONCILIATION'
        s['partial_work_unit_closure_may_grant_stage_exit'] = False
        nr = s.setdefault('required_normative_section_uids', [])
        for uid in ['WEB-GOV-01-S075','WEB-GOV-03-S069','WEB-GOV-04-S083']:
            if uid not in nr:
                nr.append(uid)
    s1 = next(x for x in stages if x.get('stage_uid') == 'STAGE-01')
    s1['capability_ownership_boundary'] = {
        'owns': ['SOURCE_CAPTURE','SOURCE_FACTS','RESPONSIBILITY_CLASSIFICATION','BASE_BLUEPRINT'],
        'functional_contract_materialization': 'BLOCK',
        'stage2_gap_repair_by_stage1_replay_without_stage1_defect': 'BLOCK',
    }
    s2 = next(x for x in stages if x.get('stage_uid') == 'STAGE-02')
    for op in ['FUNCTION_ADMISSION_SCORECARD_COMPILE','AUTO_COMPLETION_SCOPE_LEDGER_COMPILE']:
        if op not in s2['operations']:
            s2['operations'].append(op)
    for out in ['FUNCTION_ADMISSION_SCORECARD','AUTO_COMPLETION_SCOPE_LEDGER']:
        if out not in s2['outputs']:
            s2['outputs'].append(out)
    s2.setdefault('output_producers', {})['FUNCTION_ADMISSION_SCORECARD'] = 'FUNCTION_ADMISSION_SCORECARD_COMPILE'
    s2.setdefault('output_producers', {})['AUTO_COMPLETION_SCOPE_LEDGER'] = 'AUTO_COMPLETION_SCOPE_LEDGER_COMPILE'
    app = s2.setdefault('required_output_applicability', {})
    app['when_missing_required_function_or_contract_is_analyzed'] = ['FUNCTION_ADMISSION_SCORECARD','AUTO_COMPLETION_SCOPE_LEDGER']
    app.pop('when_ai_or_auto_proposes_functional_addition', None)
    app.pop('when_bounded_auto_completion_is_activated', None)
    s2['functional_contract_ownership'] = [
        'BUSINESS_ENTITY_LIFECYCLE','OPERATION_HIERARCHY','FIELD_DATA_ACTION_BOUNDARY','PAYLOAD_INPUT',
        'STATE_TRANSITION','ERROR_RECOVERY_AUDIT','FUNCTIONAL_WORKBENCH','INTERACTION_TOPOLOGY',
        'AI_INTERACTION_IDENTITY','FINALIZATION_VERSION','DEPENDENCY_CHANGE_IMPACT','FUNCTION_VISUAL_IMPACT'
    ]
    s2['downstream_discovered_owned_gap_reentry'] = 'REOPEN_STAGE02_AND_MARK_IMPACTED_SUCCESSORS_REVERIFY_REQUIRED'
    s3 = next(x for x in stages if x.get('stage_uid') == 'STAGE-03')
    s3['functional_topology_redefinition'] = 'BLOCK_REOPEN_STAGE02'
    s4 = next(x for x in stages if x.get('stage_uid') == 'STAGE-04')
    s4['upstream_contract_or_visual_change_after_freeze'] = 'INVALIDATE_IMPACTED_FREEZE_AND_REVERIFY'
    for s in stages[4:]:
        s['upstream_owned_gap_discovered'] = 'STOP_AND_REENTER_CAPABILITY_REENTRY_MAP'
    d['governance_revision'] = SOURCE_REVISION
    write(LIFECYCLE, d)

def patch_consumer_scripts():
    p = ROOT / 'governance/ci/validate_current_stage2_materialized_closure.py'
    t = p.read_text(encoding='utf-8')
    t = re.sub(r'''PAGES = \{.*?\n\}\nREQUIRED_PAGE_FILES =''', '''def resolve_page(page_uid: str):
    raw_dir = RUN / "00_SOURCE_INTAKE/RAW_SOURCE" / page_uid
    blueprint = RUN / "02_BASE_BLUEPRINT" / page_uid / "PAGE_BASE_BLUEPRINT.yaml"
    if not raw_dir.is_dir() or not blueprint.is_file():
        errors.append(f"CURRENT_TARGET_PAGE_SCOPE_UNRESOLVED:{page_uid}")
        return None
    candidates = []
    for path in sorted(raw_dir.glob("*.yaml")):
        try:
            obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if (obj.get("authority") or {}).get("page_uid") == page_uid and isinstance(obj.get("registries"), dict):
            candidates.append(path)
    if len(candidates) != 1:
        errors.append(f"CURRENT_PAGE_RAW_OWNER_DENOMINATOR:{page_uid}:{len(candidates)}")
        return None
    bp = yaml.safe_load(blueprint.read_text(encoding="utf-8")) or {}
    ai = "CONVERSATION_POLICY" in set(bp.get("required_responsibility_uids") or [])
    return {"raw": candidates[0], "blueprint": blueprint, "ai": ai}

REQUIRED_PAGE_FILES =''', t, count=1, flags=re.S)
    t = t.replace('EXPECTED_GAPS = {f"GAP-{i:03}" for i in range(1, 9)}\n', '')
    old = '''unknown_target_pages = sorted(set(target_page_uids) - set(PAGES))
if unknown_target_pages:
    errors.append(f"CURRENT_TARGET_PAGE_SCOPE_UNKNOWN:{unknown_target_pages!r}")
target_pages = {uid: PAGES[uid] for uid in target_page_uids if uid in PAGES}
expected_gaps = set(evidence.get("preserved_external_authority_union_gap_uids") or [])
if not expected_gaps or not expected_gaps.issubset(EXPECTED_GAPS):
    errors.append(f"CURRENT_EXTERNAL_AUTHORITY_SCOPE_INVALID:{sorted(expected_gaps)!r}")
expected_blocker_count = sum(7 if cfg["ai"] else 6 for cfg in target_pages.values())
'''
    new = '''target_pages = {}
for uid in target_page_uids:
    cfg = resolve_page(uid)
    if cfg:
        target_pages[uid] = cfg
expected_gaps = set(evidence.get("preserved_external_authority_union_gap_uids") or [])
if not expected_gaps:
    errors.append("CURRENT_EXTERNAL_AUTHORITY_SCOPE_MISSING")
receipt_for_scope = load(RECEIPT)
receipt_blockers = receipt_for_scope.get("materialized_missing_artifact_blockers") or {}
expected_blocker_count = sum(len(receipt_blockers.get(uid) or []) for uid in target_page_uids)
if receipt_for_scope.get("materialized_missing_artifact_blocker_count") != expected_blocker_count:
    errors.append("REMEDIATION_RECEIPT_INTERNAL_BLOCKER_DENOMINATOR_DRIFT")
'''
    if old not in t:
        raise RuntimeError('MATERIAL_VALIDATOR_SCOPE_ANCHOR_DRIFT')
    t = t.replace(old, new, 1)
    t = t.replace('print("PASS: GAP-001..GAP-008 remain unresolved and no stale EXTERNAL_AUTHORITY tree was restored")',
                  'print(f"PASS: preserved external Authority refs remain unresolved for Current scope count={len(expected_gaps)} and no stale EXTERNAL_AUTHORITY tree was restored")')
    p.write_text(t, encoding='utf-8')

    p = ROOT / 'governance/ci/run_current_stage2_actual_test.py'
    t = p.read_text(encoding='utf-8')
    t = re.sub(r'''PAGES = \{.*?\n\}\nEXPECTED_GAPS = .*?\nKNOWN_AUTHORITIES = \{.*?\n\}\n\n''', '''def resolve_page(page_uid: str):
    raw_dir = RUN / '00_SOURCE_INTAKE/RAW_SOURCE' / page_uid
    blueprint = RUN / '02_BASE_BLUEPRINT' / page_uid / 'PAGE_BASE_BLUEPRINT.yaml'
    if not raw_dir.is_dir() or not blueprint.is_file():
        die(f'PAGE_SCOPE_OWNER_MISSING:{page_uid}')
    candidates = []
    for path in sorted(raw_dir.glob('*.yaml')):
        try:
            obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        except Exception:
            continue
        if (obj.get('authority') or {}).get('page_uid') == page_uid and isinstance(obj.get('registries'), dict):
            candidates.append(path)
    if len(candidates) != 1:
        die(f'PAGE_RAW_OWNER_DENOMINATOR:{page_uid}:{len(candidates)}')
    return {'raw': candidates[0], 'blueprint': blueprint}

''', t, count=1, flags=re.S)
    t = t.replace('def fresh_scan(page: str, raw: dict):', 'def fresh_scan(page: str, raw: dict, unresolved_authority_by_ref: dict):', 1)
    t = t.replace("            elif auth in KNOWN_AUTHORITIES:\n                add(gaps, page, 'AUTHORITY_GAP', 'SHARED_OWNER_AUTHORITY_UNRESOLVED', aid, f'{KNOWN_AUTHORITIES[auth]}: {auth}', 'EXTERNAL_AUTHORITY')",
                  "            elif auth in unresolved_authority_by_ref:\n                add(gaps, page, 'AUTHORITY_GAP', 'SHARED_OWNER_AUTHORITY_UNRESOLVED', aid, f'{unresolved_authority_by_ref[auth]}: {auth}', 'EXTERNAL_AUTHORITY')", 1)
    old = '''if (execution.get('stage1') or {}) != {'CORE-01': 'PASS', 'ASSET-01': 'PASS'}:
    die('STAGE02_ADMISSION_STAGE1_NOT_CLOSED')
if OLD_STAGE2_ROOT.exists():
    die('STAGE02_ADMISSION_OLD_PRODUCT_ARTIFACT_ROOT_PRESENT')
'''
    new = '''stage1_state = execution.get('stage1') or {}
if not isinstance(stage1_state, dict) or not stage1_state or any(v != 'PASS' for v in stage1_state.values()):
    die(f'STAGE02_ADMISSION_STAGE1_NOT_CLOSED:{stage1_state!r}')
required_page_uids = list(stage1_state)
'''
    if old not in t:
        raise RuntimeError('RUNNER_STAGE1_ANCHOR_DRIFT')
    t = t.replace(old, new, 1)
    old = '''scope = os.environ.get('STAGE02_PAGE_SCOPE', 'ALL_REQUIRED_PAGES').strip()
if scope == 'CORE-01':
    target_page_uids = ['CORE-01']
elif scope == 'ALL_REQUIRED_PAGES':
    target_page_uids = list(PAGES)
else:
    die(f'UNSUPPORTED_STAGE02_PAGE_SCOPE:{scope!r}')
target_pages = {page: PAGES[page] for page in target_page_uids}
remaining_page_uids = [page for page in PAGES if page not in target_page_uids]
scope_complete = not remaining_page_uids
'''
    new = '''scope = os.environ.get('STAGE02_PAGE_SCOPE', 'ALL_REQUIRED_PAGES').strip()
if scope == 'ALL_REQUIRED_PAGES':
    target_page_uids = list(required_page_uids)
else:
    target_page_uids = [x.strip() for x in scope.split(',') if x.strip()]
    if not target_page_uids or len(target_page_uids) != len(set(target_page_uids)):
        die(f'INVALID_STAGE02_PAGE_SCOPE:{scope!r}')
    unknown = sorted(set(target_page_uids) - set(required_page_uids))
    if unknown:
        die(f'STAGE02_PAGE_SCOPE_OUTSIDE_STAGE1:{unknown!r}')
target_pages = {page: resolve_page(page) for page in target_page_uids}
remaining_page_uids = [page for page in required_page_uids if page not in target_page_uids]
scope_complete = not remaining_page_uids
'''
    if old not in t:
        raise RuntimeError('RUNNER_SCOPE_ANCHOR_DRIFT')
    t = t.replace(old, new, 1)
    t = t.replace("    scan = fresh_scan(page, raw)\n    responsibilities = set(blueprint.get('required_responsibility_uids') or [])",
                  "    unresolved_authority_by_ref = {str(x.get('authority_ref')): x.get('gap_uid') for x in refs if isinstance(x, dict) and x.get('authority_ref') and x.get('gap_uid')}\n    scan = fresh_scan(page, raw, unresolved_authority_by_ref)\n    responsibilities = set(blueprint.get('required_responsibility_uids') or [])", 1)
    old = '''    closure = [
        'MISSING_BUSINESS_ENTITY_INVENTORY',
        'MISSING_BUSINESS_ENTITY_OPERATION_MATRIX',
        'MISSING_ENTITY_HIERARCHY_MATRIX',
        'MISSING_FUNCTIONAL_WORKBENCH_CONTRACT',
        'MISSING_INTERACTION_TOPOLOGY_SPEC',
        'MISSING_FUNCTION_VISUAL_IMPACT_MATRIX',
    ]
    if ai_profile_active:
        closure.append('MISSING_AI_INTERACTION_CONTINUITY_CONTRACT')
'''
    new = '''    page_dir = OLD_STAGE2_ROOT / page
    closure_defs = [
        ('BUSINESS_ENTITY_INVENTORY.yaml', 'MISSING_BUSINESS_ENTITY_INVENTORY'),
        ('BUSINESS_ENTITY_OPERATION_MATRIX.yaml', 'MISSING_BUSINESS_ENTITY_OPERATION_MATRIX'),
        ('ENTITY_HIERARCHY_MATRIX.yaml', 'MISSING_ENTITY_HIERARCHY_MATRIX'),
        ('FUNCTIONAL_WORKBENCH_CONTRACT.yaml', 'MISSING_FUNCTIONAL_WORKBENCH_CONTRACT'),
        ('INTERACTION_TOPOLOGY_SPEC.yaml', 'MISSING_INTERACTION_TOPOLOGY_SPEC'),
        ('FUNCTION_VISUAL_IMPACT_MATRIX.yaml', 'MISSING_FUNCTION_VISUAL_IMPACT_MATRIX'),
    ]
    closure = [code for filename, code in closure_defs if not (page_dir / filename).is_file()]
    if ai_profile_active and not (page_dir / 'AI_INTERACTION_CONTINUITY_CONTRACT.yaml').is_file():
        closure.append('MISSING_AI_INTERACTION_CONTINUITY_CONTRACT')
    if scan.get('gap_count', 0) > 0:
        if not (page_dir / 'FUNCTION_ADMISSION_SCORECARD.yaml').is_file():
            closure.append('MISSING_FUNCTION_ADMISSION_SCORECARD')
        if not (page_dir / 'AUTO_COMPLETION_SCOPE_LEDGER.yaml').is_file():
            closure.append('MISSING_AUTO_COMPLETION_SCOPE_LEDGER')
'''
    if old not in t:
        raise RuntimeError('RUNNER_CLOSURE_ANCHOR_DRIFT')
    t = t.replace(old, new, 1)
    t = t.replace("        'function_admission_scorecard': 'NOT_APPLICABLE_NO_AUTO_OR_AI_PROPOSED_FUNCTION_CREATED_BY_THIS_TEST',\n        'automatic_completion_scope': 'NOT_APPLICABLE_NO_AUTOMATIC_COMPLETION_ATTEMPT',",
                  "        'function_admission_scorecard': 'PRESENT' if (page_dir / 'FUNCTION_ADMISSION_SCORECARD.yaml').is_file() else 'REQUIRED_WHEN_GAP_ANALYSIS_EXISTS',\n        'automatic_completion_scope': 'PRESENT' if (page_dir / 'AUTO_COMPLETION_SCOPE_LEDGER.yaml').is_file() else 'REQUIRED_WHEN_GAP_ANALYSIS_EXISTS',", 1)
    t = re.sub(r'''\nif not union_gap_uids\.issubset\(EXPECTED_GAPS\):.*?die\(f'EXTERNAL_AUTHORITY_UNION_DRIFT:expected=\{sorted\(EXPECTED_GAPS\)\} actual=\{sorted\(union_gap_uids\)\}'\)\n''',
               "\nif any(not gid for gid in union_gap_uids):\n    die('EXTERNAL_AUTHORITY_GAP_UID_MISSING')\n", t, count=1, flags=re.S)
    t = t.replace("'physical_stage2_product_artifact_root_present': False,", "'physical_stage2_product_artifact_root_present': OLD_STAGE2_ROOT.is_dir(),", 1)
    p.write_text(t, encoding='utf-8')

    for name in ['validate_stage02_state_integrity.py','validate_stage02_successor_integrity.py']:
        p = ROOT / 'governance/ci' / name
        t = p.read_text(encoding='utf-8')
        old = '''if stage1 != {"CORE-01": "PASS", "ASSET-01": "PASS"}:
    die(f"STAGE1_CLOSURE_CONTINUITY_MISSING:{stage1!r}")
'''
        if old not in t:
            old = """if stage1 != {'CORE-01': 'PASS', 'ASSET-01': 'PASS'}:
    die(f'STAGE1_CLOSURE_CONTINUITY_MISSING:{stage1!r}')
"""
            new = """if not isinstance(stage1, dict) or not stage1 or any(v != 'PASS' for v in stage1.values()):
    die(f'STAGE1_CLOSURE_CONTINUITY_MISSING:{stage1!r}')
"""
        else:
            new = '''if not isinstance(stage1, dict) or not stage1 or any(v != "PASS" for v in stage1.values()):
    die(f"STAGE1_CLOSURE_CONTINUITY_MISSING:{stage1!r}")
'''
        if old not in t:
            raise RuntimeError(f'{name}:STAGE1_SCOPE_ANCHOR_DRIFT')
        p.write_text(t.replace(old, new, 1), encoding='utf-8')

    p = ROOT / 'governance/ci/validate_governance_portability.py'
    t = p.read_text(encoding='utf-8')
    anchor = "# Mother context/task-layer machine binding checks. These extend the existing portability owner.\n"
    add = '''# Reusable product-scope consumers must remain scope-parametric.
scope_neutral_surfaces=[
    ROOT/'governance/ci/run_current_stage2_actual_test.py',
    ROOT/'governance/ci/validate_current_stage2_materialized_closure.py',
    ROOT/'governance/ci/validate_stage02_state_integrity.py',
    ROOT/'governance/ci/validate_stage02_successor_integrity.py',
]
literal_product_identity=re.compile(r"['\\\"](?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI)-\\d+['\\\"]")
for surface in scope_neutral_surfaces:
    if not surface.is_file():
        failures.append('scope_neutral_surface_missing:'+surface.relative_to(ROOT).as_posix())
        continue
    body=surface.read_text(encoding='utf-8')
    if literal_product_identity.search(body):
        failures.append('reusable_consumer_literal_product_scope:'+surface.relative_to(ROOT).as_posix())

'''
    if anchor not in t:
        raise RuntimeError('PORTABILITY_ANCHOR_DRIFT')
    p.write_text(t.replace(anchor, add + anchor, 1), encoding='utf-8')

def patch_workflow():
    p = ROOT / '.github/workflows/stage02-actual-test.yml'
    t = p.read_text(encoding='utf-8')
    old = '''          target_pages = ev.get('target_pages') or []
          assert target_pages in (['CORE-01'], ['CORE-01', 'ASSET-01']), target_pages
          assert set(pages) == set(target_pages), (sorted(pages), target_pages)
          assert ev.get('stage_scope_complete') is (set(target_pages) == {'CORE-01', 'ASSET-01'})
'''
    new = '''          target_pages = ev.get('target_pages') or []
          scope_state = yaml.safe_load((ROOT/'governance/test/ACTIVE_STATE.yaml').read_text()) or {}
          stage1_scope = (scope_state.get('execution') or {}).get('stage1') or {}
          required_pages = {uid for uid, status in stage1_scope.items() if status == 'PASS'}
          assert target_pages and set(target_pages).issubset(required_pages), (target_pages, sorted(required_pages))
          assert set(pages) == set(target_pages), (sorted(pages), target_pages)
          assert ev.get('stage_scope_complete') is (set(target_pages) == required_pages)
'''
    if old not in t:
        raise RuntimeError('WORKFLOW_CURRENT_PROJECTION_SCOPE_ANCHOR_DRIFT')
    t = t.replace(old, new, 1)
    t = t.replace("'out_of_scope': ['ASSET-01','STAGE03','WEBSITE_CONSTRUCTION','DEPLOYMENT','PRODUCT_AUTHORITY_AUTOFILL'],",
                  "'out_of_scope': list(ev.get('remaining_pages') or []) + ['STAGE03','WEBSITE_CONSTRUCTION','DEPLOYMENT','PRODUCT_AUTHORITY_AUTOFILL'],")
    t = t.replace("'out_of_scope': ['ASSET-01','STAGE03','WEBSITE_CONSTRUCTION','DEPLOYMENT','PRODUCT_AUTHORITY_AUTOFILL','EXTERNAL_AUTHORITY_AUTOFILL'],",
                  "'out_of_scope': list(ev.get('remaining_pages') or []) + ['STAGE03','WEBSITE_CONSTRUCTION','DEPLOYMENT','PRODUCT_AUTHORITY_AUTOFILL','EXTERNAL_AUTHORITY_AUTOFILL'],")
    old = '''          assert len(ev.get('official_stage_output_denominator') or []) == 17
          assert len(ev.get('execution_profile_mandatory_output_subset') or []) == 12
'''
    new = '''          assert len(ev.get('official_stage_output_denominator') or []) == len(prev.get('official_stage_output_denominator') or [])
          assert len(ev.get('execution_profile_mandatory_output_subset') or []) == len(prev.get('execution_profile_mandatory_output_subset') or [])
'''
    if old in t:
        t = t.replace(old, new, 1)
    t = t.replace("          assert target_pages == ['CORE-01'], target_pages\n", "          assert target_pages and len(target_pages) == len(set(target_pages)), target_pages\n", 1)
    t = t.replace("          assert ev.get('stage_scope_complete') is False\n", "          assert ev.get('stage_scope_complete') is (not remaining_pages)\n", 1)
    old = '''          test "$(git diff --cached --name-only | wc -l | tr -d ' ')" = '13'
'''
    if old in t:
        new = '''          expected_count="$(printf '%s\n' "$permitted" | sed '/^$/d' | wc -l | tr -d ' ')"
          test "$(git diff --cached --name-only | wc -l | tr -d ' ')" = "$expected_count"
'''
        t = t.replace(old, new, 1)
    t = t.replace("print(f'PASS: exact CORE-01 structural materialization write-set={len(actual)}/13')",
                  "print(f'PASS: exact structural materialization write-set={len(actual)}/{len(permitted)}')", 1)
    p.write_text(t, encoding='utf-8')

def materialize_scope_manifest(state):
    ex = state.get('execution') or {}
    stage1 = ex.get('stage1') or {}
    stage2 = ex.get('stage2') or {}
    active = state.get('stage02_active_attempt') or {}
    included = list(active.get('target_pages') or stage2.get('tested_page_uids') or ex.get('target_pages') or [])
    remaining = list(active.get('remaining_pages') or stage2.get('remaining_page_uids') or [])
    required = [uid for uid, status in stage1.items() if status == 'PASS']
    if not included:
        included = [uid for uid in required if uid not in remaining]
    excluded = [uid for uid in required if uid not in included]
    if not remaining:
        remaining = list(excluded)
    scope = {
        'schema_version': 1,
        'artifact_type': 'EXECUTION_SCOPE_MANIFEST',
        'normative_authority': False,
        'governance_uid': NEW_UID,
        'owning_capability': 'FUNCTIONAL_CONTRACT',
        'scope_kind': 'PARTIAL_WORK_UNIT' if remaining else 'FULL_STAGE_SCOPE',
        'included_units': included,
        'excluded_units': excluded,
        'remaining_units': remaining,
        'stage_required_units': required,
        'scope_selection_authority': 'PERSISTED_CURRENT_STAGE_STATE_AND_STAGE1_CLOSED_UNIVERSE',
        'dependency_closure_refs': ['governance/test/ACTIVE_STATE.yaml'],
        'denominator_source_refs': ['governance/test/ACTIVE_STATE.yaml','governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json','00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT/CURRENT_PROBLEM_REGISTER.yaml'],
        'partial_scope': bool(remaining),
        'stage_exit_credit_allowed': not bool(remaining),
        'predecessor_governance_uid': OLD_UID,
        'fresh_revalidation_required': True,
    }
    raw = json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()
    scope['content_hash'] = hashlib.sha256(raw).hexdigest()
    write(ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml', scope)
    return scope

def update_source_revision():
    for p in sorted((SOURCE/'10_REGISTRY').glob('*.yaml')):
        d = load(p)
        if 'governance_revision' in d:
            d['governance_revision'] = SOURCE_REVISION
            write(p, d)

def deterministic():
    files = sorted((p for p in SOURCE.rglob('*') if p.is_file()), key=lambda p: p.relative_to(SOURCE).as_posix())
    tb = io.BytesIO()
    with tarfile.open(fileobj=tb, mode='w', format=tarfile.PAX_FORMAT) as tf:
        for p in files:
            rel = p.relative_to(SOURCE).as_posix()
            info = tf.gettarinfo(str(p), arcname=rel)
            info.uid=0; info.gid=0; info.uname=''; info.gname=''; info.mtime=0
            with p.open('rb') as fh:
                tf.addfile(info, fh)
    bundle = hashlib.sha256(lzma.compress(tb.getvalue(), format=lzma.FORMAT_XZ, preset=9)).hexdigest()
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            rel = p.relative_to(SOURCE).as_posix()
            zi = zipfile.ZipInfo(rel, date_time=(1980,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED; zi.create_system=3
            mode=0o755 if (p.stat().st_mode & 0o111) else 0o644
            zi.external_attr=(mode & 0xffff)<<16
            zf.writestr(zi, p.read_bytes())
    return bundle, hashlib.sha256(zb.getvalue()).hexdigest()

def refresh_source():
    run('python', str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'), cwd=SOURCE/'09_TESTS/governance')
    run('python', str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'), cwd=SOURCE/'09_TESTS/governance')
    cp = SOURCE/'CHECKSUMS.sha256'
    files = sorted(p for p in SOURCE.rglob('*') if p.is_file() and p != cp)
    if len(files) != 74:
        raise RuntimeError(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(files)}')
    cp.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files), encoding='utf-8')
    checksum = sha(cp)
    bundle, zips = deterministic()
    vp = ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'
    v = vp.read_text(encoding='utf-8')
    v = re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'", f"EXPECTED_BUNDLE_SHA256 = '{bundle}'", v, count=1)
    v = re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'", f"EXPECTED_SOURCE_ZIP_SHA256 = '{zips}'", v, count=1)
    vp.write_text(v, encoding='utf-8')
    fp = ROOT/'.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'
    f = fp.read_text(encoding='utf-8')
    f = re.sub(r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'", f"EXPECTED_CHECKSUMS_SHA256 = '{checksum}'", f, count=1)
    f = re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'", f"EXPECTED_SOURCE_ZIP_SHA256 = '{zips}'", f, count=1)
    f = re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'", f"EXPECTED_BUNDLE_SHA256 = '{bundle}'", f, count=1)
    fp.write_text(f, encoding='utf-8')
    return checksum, bundle, zips

def patch_projectors(checksum, bundle, zips):
    p = ROOT/'governance/specifications/REGISTRY.yaml'
    d = load(p)
    old = d['active_specification']
    if old.get('governance_uid') != OLD_UID:
        raise RuntimeError('REGISTRY_CURRENT_UID_DRIFT')
    d['immediate_predecessor'] = {
        'governance_uid': OLD_UID,
        'display_version': old.get('display_version'),
        'version_role': 'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY',
        'status': 'SUPERSEDED_HISTORY_ONLY_AFTER_SCOPE_STAGE_REENTRY_PORTABILITY_HARDENING',
    }
    old['governance_uid'] = NEW_UID
    old['display_version'] = DISPLAY_VERSION
    aliases = old.setdefault('aliases', [])
    if 'scope-stage-reentry-portability-hardening' not in aliases:
        aliases.append('scope-stage-reentry-portability-hardening')
    write(p, d)

    p = ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    d = load(p)
    d['artifact_uid'] = NEW_UID
    d['display_version'] = DISPLAY_VERSION
    sl = d['source_lineage']
    sl['predecessor_governance_uid'] = OLD_UID
    sl['promotion_authorization_uid'] = AUTH_UID
    sl['verified_package_filename'] = PACKAGE_FILENAME
    sl['verified_package_sha256'] = zips
    sl['deterministic_source_bundle_sha256'] = bundle
    sl['checksum_manifest_sha256'] = checksum
    sl['verified_source_revision'] = SOURCE_REVISION
    sl['source_bytes_changed_by_this_successor'] = True
    sl['source_identity_reused_only_because_source_bytes_are_unchanged'] = False
    write(p, d)

    p = ROOT/'GOVERNANCE_CURRENT.yaml'
    d = load(p)
    d['active_governance_uid'] = NEW_UID
    d['display_version'] = DISPLAY_VERSION
    si = d['source_identity']
    si['verified_package_sha256'] = zips
    si['deterministic_source_bundle_sha256'] = bundle
    si['checksum_manifest_sha256'] = checksum
    si['verified_source_revision'] = SOURCE_REVISION
    si['source_bytes_changed_by_current_successor'] = True
    write(p, d)

    p = ROOT/'governance/test/ACTIVE_STATE.yaml'
    a = load(p)
    a['specification_uid'] = NEW_UID
    scope = materialize_scope_manifest(a)
    ex = a.setdefault('execution', {})
    s2 = ex.setdefault('stage2', {})
    s2['revalidation_required_under_current_governance'] = True
    s2['prior_results_authoritative_for_current_governance'] = False
    s2['stage_exit_allowed'] = False
    s2['current_scope_manifest_ref'] = 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    ex['website_construction_allowed'] = False
    ex['deployment_allowed'] = False
    new_action = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE02_REVALIDATION_UNDER_CURRENT_GOVERNANCE'
    active = a.get('stage02_active_attempt')
    if isinstance(active, dict):
        active['fresh_revalidation_required'] = True
        active['closure_credit_under_current_governance'] = False
        active['current_scope_manifest_ref'] = 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
        active['next_action'] = new_action
    a['next_action'] = new_action
    a['current_primary_task_layer'] = 'GOVERNANCE_MAINTENANCE'
    a['current_primary_task_authorization_uid'] = AUTH_UID
    a['current_primary_task_product_stage_credit'] = 0
    rc = a.setdefault('resume_control', {})
    rc['current_resume_point'] = 'POST_GOVERNANCE_PROMOTION_STAGE2_REVERIFY_REQUIRED'
    rc['current_work_unit_uid'] = None
    rc['current_owner'] = None
    rc['exact_next_action'] = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE02_REVALIDATION_UNDER_CURRENT_GOVERNANCE'
    rc['historical_stage2_results_are_current_state'] = False
    rc['stage2_execution_requires_fresh_entry_resolution'] = True
    tr = a.setdefault('governance_revision_transition', {})
    tr['predecessor_governance_uid'] = OLD_UID
    tr['current_governance_uid'] = NEW_UID
    tr['predecessor_attempt_preserved_as_historical_evidence'] = True
    tr['predecessor_attempt_may_close_under_current_governance'] = False
    tr['fresh_revalidation_required'] = True
    tr['fresh_revalidation_scope'] = 'AFFECTED_FUNCTIONAL_CONTRACT_SCOPE_AND_REUSABLE_SCOPE_CONSUMERS'
    tr['website_construction_remains_blocked'] = True
    tr['deployment_remains_blocked'] = True
    tr['execution_scope_manifest_ref'] = 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    a['scope_stage_reentry_successor'] = {
        'authorization_uid': AUTH_UID,
        'predecessor_governance_uid': OLD_UID,
        'current_governance_uid': NEW_UID,
        'execution_scope_manifest_ref': 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
        'included_unit_count': len(scope.get('included_units') or []),
        'remaining_unit_count': len(scope.get('remaining_units') or []),
        'partial_scope_stage_exit_credit': 0 if scope.get('partial_scope') else 1,
        'product_stage_credit': 0,
        'status': 'GOVERNANCE_PROMOTED_PRODUCT_REVERIFY_REQUIRED',
    }
    fl = a.setdefault('full_lifecycle_governance_system_test', {})
    fl['deterministic_source_bundle_sha256'] = bundle
    fl['persisted_head_revalidation_required'] = True
    fl['full_line_github_result'] = 'REVALIDATION_REQUIRED_AFTER_SCOPE_STAGE_REENTRY_PROMOTION'
    fl['terminal_run_conclusion'] = 'REVALIDATION_REQUIRED'
    fl['terminal_result_credit_allowed'] = False
    write(p, a)

    findings_path = ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
    if findings_path.is_file():
        findings = load(findings_path)
        findings['next_action'] = new_action
        findings['current_governance_revalidation_required'] = True
        findings['closure_credit_under_current_governance'] = False
        write(findings_path, findings)

    p = ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
    c = load(p)
    cur = c.setdefault('current_stage2_execution', {})
    cur['fresh_revalidation_required_under_current_governance'] = True
    cur['current_governance_uid'] = NEW_UID
    cur['closure_credit_under_current_governance'] = False
    cur['execution_scope_manifest_ref'] = 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    cur['next_action'] = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE02_REVALIDATION_UNDER_CURRENT_GOVERNANCE'
    write(p, c)

def validate():
    for p in [
        ROOT/'governance/ci/run_current_stage2_actual_test.py',
        ROOT/'governance/ci/validate_current_stage2_materialized_closure.py',
        ROOT/'governance/ci/validate_stage02_state_integrity.py',
        ROOT/'governance/ci/validate_stage02_successor_integrity.py',
        ROOT/'governance/ci/validate_governance_portability.py',
    ]:
        run('python', '-m', 'py_compile', str(p))
    run('python', str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'))
    run('python', str(ROOT/'governance/ci/governance_resolver.py'))
    run('python', str(ROOT/'governance/ci/validate_governance_portability.py'))
    run('python', str(ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py'))
    run('python', str(SOURCE/'09_TESTS/governance/validate_section_registry.py'), cwd=SOURCE)
    run('python', str(SOURCE/'09_TESTS/governance/governance_management_contract_guard.py'), cwd=SOURCE)
    run('python', str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py'))
    run('python', str(ROOT/'governance/ci/validate_stage02_state_integrity.py'))
    run('python', str(ROOT/'governance/ci/validate_stage02_successor_integrity.py'))
    for rel in [
        '.github/governance-source/SOURCE_IDENTITY_REPORT.json',
        'governance/test/ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT.json',
        'governance/test/FINDING_CLOSURE_READINESS.json',
    ]:
        q = ROOT/rel
        if q.exists():
            run('git', 'checkout', '--', rel)
    run('git', 'diff', '--check')

def main():
    if not AUTH.is_file():
        raise RuntimeError('AUTHORIZATION_MISSING')
    auth = load(AUTH)
    if auth.get('status') != 'APPROVED_FOR_EXACT_SCOPE' or auth.get('single_use') is not True:
        raise RuntimeError('AUTHORIZATION_INVALID')
    if load(ROOT/'governance/specifications/REGISTRY.yaml')['active_specification']['governance_uid'] != OLD_UID:
        raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')
    patch_mother()
    patch_machine()
    patch_lifecycle()
    patch_consumer_scripts()
    update_source_revision()
    checksum, bundle, zips = refresh_source()
    patch_projectors(checksum, bundle, zips)
    validate()
    run('git', 'diff', '--check')
    print(json.dumps({
        'new_governance_uid': NEW_UID,
        'display_version': DISPLAY_VERSION,
        'source_revision': SOURCE_REVISION,
        'checksum_manifest_sha256': checksum,
        'deterministic_source_bundle_sha256': bundle,
        'deterministic_source_zip_sha256': zips,
        'product_stage_credit': 0,
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
