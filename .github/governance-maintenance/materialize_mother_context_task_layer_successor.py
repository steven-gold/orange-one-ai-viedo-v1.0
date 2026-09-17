#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib
import io
import json
import lzma
import re
import subprocess
import tarfile
import zipfile
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.github/governance-source/active/source'
AUTH_UID = 'USR-DIRECTIVE-20260918-MOTHER-CONTEXT-TASK-LAYER-HARDENING-R2'
OLD_UID = 'GOV-REV-20260917-EXECUTION-CLOSURE-TRANSACTION-HARDENING'
NEW_UID = 'GOV-REV-20260918-MOTHER-CONTEXT-TASK-LAYER-HARDENING'
DISPLAY_VERSION = 'v2.2.3'
SOURCE_REVISION = 'v2.2.2-mother-context-task-layer-hardening'
PACKAGE_FILENAME = 'AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.2_MOTHER_CONTEXT_TASK_LAYER_HARDENING_LOCAL_VERIFIED.zip'
AUTH = ROOT / f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
HELPER = ROOT / '.github/governance-maintenance/materialize_mother_context_task_layer_successor.py'
WORKFLOW = ROOT / '.github/workflows/mother-context-task-layer-successor.yml'

MOTHER = {
    'WEB-GOV-01': SOURCE / '12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',
    'WEB-GOV-02': SOURCE / '12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md',
    'WEB-GOV-03': SOURCE / '12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',
    'WEB-GOV-04': SOURCE / '12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md',
}

SECTIONS_03 = '''

<!-- SECTION_UID: WEB-GOV-03-S063 -->
## 63. Mandatory Session Bootstrap / Resume Gate

Before any Current State judgment, planning, mutation, test, commit, workflow execution, deployment decision, closure claim, or continuation decision, the executor MUST complete one `SESSION_BOOTSTRAP_RESUME_GATE` in this exact dependency order:

1. Resolve the live repository, target branch, commit SHA, and tree SHA from the repository itself.
2. Resolve the formal Registry / Current Governance entry and immutable Current Governance UID; chat memory, historical summaries, Stage labels, profile labels, and run labels MUST_NOT select Current Governance.
3. Read the Current Mother Governance in canonical order `WEB-GOV-01 -> WEB-GOV-02 -> WEB-GOV-03 -> WEB-GOV-04` through the Current Section/Root registries.
4. Resolve Current Canonical Authority for the requested semantic concern.
5. Classify and lock the Current Primary Task Layer under WEB-GOV-03-S064.
6. Resolve the one legal Active Primary Work Unit for that task layer; if none exists, enter `WORK_UNIT_RESOLUTION_GATE` under WEB-GOV-03-S065 before doing effectful work.
7. Resolve Canonical Owner Mapping, exact write target, forward dependencies, reverse dependencies, and impacted consumers.
8. Resolve the persisted Current Resume Point and verify the last completed effectful action.
9. Resolve Current Audit / Evidence State and prove that evidence belongs to the Current Governance UID/revision or is explicitly classified historical/non-current evidence.
10. Resolve the selected Execution Profile only when applicable; profile-local Stage/step identity MUST remain subordinate to the Current Primary Task Layer and common Mother Policy.
11. Resolve Entry Conditions, Dependencies, Definition of Done, required Gates, terminal transition, and closure evidence requirements.
12. Recheck live commit/tree and Current Governance identity immediately before the first write or effectful action.

The gate MUST fail closed when any required Current identity, Authority, task layer, Work Unit, owner, Resume Point, evidence identity, dependency, reference, revision, or transition is missing, stale, ambiguous, conflicting, or points to a superseded/deleted owner.

`CHAT_MEMORY != CURRENT_TRUTH` and `INNER_STAGE_IDENTITY != PRIMARY_TASK_SELECTION` are permanent invariants.

<!-- SECTION_UID: WEB-GOV-03-S064 -->
## 64. Task Layer Classification / Primary Task Lock

Every governed request MUST be classified before Work Unit execution into exactly one Current Primary Task Layer:

- `GOVERNANCE_MAINTENANCE`
- `PRODUCT_STAGE_EXECUTION`
- `TEST_OR_VALIDATION_MAINTENANCE`
- `EVIDENCE_STATE_MAINTENANCE`
- `DEPLOYMENT_OR_PRODUCTION`

The classification MUST derive from the explicit user directive, Current Authority, authorized Change Request, Current Work Unit/Resume state, and applicable dependency/impact evidence. A Stage number, profile step, historical run, failing test, open blocker, or nearby executable MUST_NOT silently redefine the requested Primary Task Layer.

When `GOVERNANCE_MAINTENANCE` is primary, product Stage artifacts MAY be read only as evidence, regression provenance, dependency context, or impacted-consumer context unless a separately authorized product Work Unit becomes the legal primary task. Governance maintenance MUST_NOT drift into product materialization merely because a product Stage remains blocked.

Task-layer changes MUST be explicit, evidence-backed, recorded in Resume/Current State, and re-run the full Session Bootstrap / Resume Gate before effectful work continues.

<!-- SECTION_UID: WEB-GOV-03-S065 -->
## 65. Work Unit Resolution Gate

If the Current Primary Task Layer has no legal Active Primary Work Unit, execution MUST enter `WORK_UNIT_RESOLUTION_GATE`; absence of an Active Work Unit is not permission for AI to invent one or jump to the nearest Stage, file, test, or blocker.

The legal successor Work Unit MAY be resolved only from registered Current Authority, a valid explicit authorization or Change Request, Current impact set, dependency graph, applicability decision, unresolved blocker ledger, prior closure transition, and canonical owner mapping.

The resolution MUST prove:

- predecessor/current Work Unit state and terminal disposition;
- requested Primary Task Layer;
- candidate successor scope and canonical owner;
- dependency and reverse-dependency legality;
- applicability and Entry Conditions;
- no duplicate/parallel Work Unit or second owner;
- exact Resume Point and Definition of Done;
- whether the successor is blocked, executable, or requires human/Authority decision.

If two or more materially distinct successor Work Units remain legal without Authority selecting one, the result is `WORK_UNIT_RESOLUTION_AMBIGUOUS` and effectful execution MUST BLOCK. AI MUST_NOT create a synthetic Work Unit merely to continue activity.

<!-- SECTION_UID: WEB-GOV-03-S066 -->
## 66. Governance Maintenance Credit Isolation

Governance maintenance and product completion are different accounting domains. The following work MAY repair governance correctness but MUST receive zero product-stage gap-reduction and zero product-completion credit unless it separately materializes an already-authorized product requirement at the canonical product owner and passes that product requirement's own acceptance gates:

- Mother/Current governance repair or promotion;
- Registry, index, reference, checksum, source-identity, supersession, or residual cleanup;
- validator, scanner, classifier, parser, harness, workflow, CI, gate, or test-infrastructure repair;
- evidence, projector, Current State, Resume, ledger, report, or receipt repair;
- migration of stale/deleted/superseded governance references;
- negative-regression preservation or historical evidence cleanup.

`GOVERNANCE_MAINTENANCE_PASS != PRODUCT_STAGE_PASS`.

A governance Work Unit MUST record its own closure evidence and MUST_NOT decrement product blocker/gap denominators solely because the governance machinery became correct. Product denominators change only from fresh product/contract evidence under the legal product owner and Current Authority.

<!-- SECTION_UID: WEB-GOV-03-S067 -->
## 67. Terminal Closure Observation / Context Continuity Gate

A Work Unit, validation cycle, promotion, cleanup transaction, workflow-backed Gate, or release Gate MUST_NOT receive terminal closure credit from an inner step, job subset, generated preterminal projection, queued/in-progress workflow, timeout, cancellation, skipped terminal, or historical successful run.

When terminal execution is delegated to CI or another external executor, closure requires an observed outer terminal conclusion bound to the exact repository/project, commit SHA, evidence-cycle identity, required job/test denominator, and Current Governance UID. `INNER_STEP_PASS != TERMINAL_RUN_PASS`.

Before moving to a new Primary Task Layer or Work Unit, the executor MUST persist the terminal disposition, exact evidence refs, unresolved blockers, Current Resume Point, and legal next transition. A later session MUST recover from those persisted facts through WEB-GOV-03-S063 rather than from conversational memory.
'''

SECTIONS_04 = '''

<!-- SECTION_UID: WEB-GOV-04-S079 -->
## 79. Session Bootstrap / Current Primary Task Audit

Every `PRE_WORK_AUDIT` and every resumed execution MUST verify the complete `SESSION_BOOTSTRAP_RESUME_GATE` defined by WEB-GOV-03-S063 before accepting Current State. Audit MUST record at least live repository/branch/commit/tree, Current Governance UID, Mother read-set identity, Current Canonical Authority, Current Primary Task Layer, Active Work Unit or Work Unit Resolution disposition, Canonical Owner, Resume Point, Current evidence identity, selected profile when applicable, and pre-write identity recheck state.

Audit MUST FAIL when Current State was selected from chat memory, a historical summary, Stage/profile/run identity, stale evidence, or a superseded/deleted reference instead of the formal Current chain.

<!-- SECTION_UID: WEB-GOV-04-S080 -->
## 80. Work Unit Resolution / Task-Layer Credit Isolation Audit

Audit MUST prove the Active Work Unit belongs to the locked Current Primary Task Layer. When no Active Work Unit existed, Audit MUST require a persisted `WORK_UNIT_RESOLUTION_GATE` result and prove the successor was derived from registered Authority/authorization, impact, dependency, applicability and owner evidence rather than AI invention.

For governance, test/harness, evidence/state, reference, residual, CI, or gate maintenance, Audit MUST separately report governance-maintenance closure and product-stage status. Product gap/blocker denominators MUST remain unchanged unless fresh product-owner evidence proves an authorized product remediation. Governance cleanup, successful validator repair, successful workflow repair, or source/reference hygiene MUST_NOT be reported as product completion.

<!-- SECTION_UID: WEB-GOV-04-S081 -->
## 81. Outer Terminal Conclusion / Resume Continuity Audit

Terminal Audit MUST distinguish inner-step/job success from the outer terminal execution result. Closure credit requires the exact terminal conclusion and required denominator for the exact tested commit/evidence cycle; queued, in-progress, timed-out, cancelled, skipped, failed, ambiguous, or historical runs are not Current terminal PASS.

Audit MUST prove closure state, evidence references, unresolved blockers, exact Resume Point, and legal next transition were persisted before task-layer or Work Unit movement. A resumed session that cannot reconcile these facts to the Current Governance UID and live repository identity MUST be `NOT_VERIFIED` or `BLOCKED`, never inferred PASS.
'''


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def write_yaml(path: Path, obj):
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=160), encoding='utf-8')


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(*args, cwd=ROOT):
    print('+', *args)
    subprocess.run(args, cwd=cwd, check=True)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'{label}: expected token missing: {old!r}')
    if text.count(old) != 1:
        raise RuntimeError(f'{label}: expected exactly one token, got {text.count(old)}: {old!r}')
    return text.replace(old, new, 1)


def section_binding(uid: str, doc_id: str, path: str, heading: str) -> str:
    return sha256_bytes(f'{uid}\n{doc_id}\n{path}\n{heading}\n'.encode())


def deterministic_bundle_and_zip(source: Path):
    files = sorted((p for p in source.rglob('*') if p.is_file()), key=lambda p: p.relative_to(source).as_posix())
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode='w', format=tarfile.PAX_FORMAT) as tf:
        for p in files:
            rel = p.relative_to(source).as_posix()
            info = tf.gettarinfo(str(p), arcname=rel)
            info.uid = 0; info.gid = 0; info.uname = ''; info.gname = ''; info.mtime = 0
            with p.open('rb') as fh:
                tf.addfile(info, fh)
    bundle = lzma.compress(tar_buf.getvalue(), format=lzma.FORMAT_XZ, preset=9)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            rel = p.relative_to(source).as_posix()
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3
            mode = 0o755 if (p.stat().st_mode & 0o111) else 0o644
            zi.external_attr = (mode & 0xFFFF) << 16
            zf.writestr(zi, p.read_bytes())
    return sha256_bytes(bundle), sha256_bytes(zbuf.getvalue())


def patch_mother_docs():
    for path in MOTHER.values():
        text = path.read_text(encoding='utf-8')
        text = replace_once(text, 'version: 2.2.1', 'version: 2.2.2', path.name)
        path.write_text(text, encoding='utf-8')
    p3 = MOTHER['WEB-GOV-03']
    t3 = p3.read_text(encoding='utf-8')
    if 'WEB-GOV-03-S063' in t3:
        raise RuntimeError('Mother 03 successor section already exists')
    p3.write_text(t3.rstrip() + SECTIONS_03 + '\n', encoding='utf-8')
    p4 = MOTHER['WEB-GOV-04']
    t4 = p4.read_text(encoding='utf-8')
    if 'WEB-GOV-04-S079' in t4:
        raise RuntimeError('Mother 04 successor section already exists')
    p4.write_text(t4.rstrip() + SECTIONS_04 + '\n', encoding='utf-8')


def patch_section_registry():
    p = SOURCE / '10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
    d = load_yaml(p)
    d['governance_revision'] = SOURCE_REVISION
    additions = {
        'WEB-GOV-03': [
            ('WEB-GOV-03-S063','63','Mandatory Session Bootstrap / Resume Gate'),
            ('WEB-GOV-03-S064','64','Task Layer Classification / Primary Task Lock'),
            ('WEB-GOV-03-S065','65','Work Unit Resolution Gate'),
            ('WEB-GOV-03-S066','66','Governance Maintenance Credit Isolation'),
            ('WEB-GOV-03-S067','67','Terminal Closure Observation / Context Continuity Gate'),
        ],
        'WEB-GOV-04': [
            ('WEB-GOV-04-S079','79','Session Bootstrap / Current Primary Task Audit'),
            ('WEB-GOV-04-S080','80','Work Unit Resolution / Task-Layer Credit Isolation Audit'),
            ('WEB-GOV-04-S081','81','Outer Terminal Conclusion / Resume Continuity Audit'),
        ],
    }
    docs = {x.get('document_id'): x for x in d.get('documents') or []}
    for doc_id, records in additions.items():
        doc = docs[doc_id]
        rel = doc['path']
        existing = {x.get('section_uid') for x in doc.get('sections') or []}
        for uid, num, title in records:
            if uid in existing:
                raise RuntimeError(f'duplicate section uid {uid}')
            heading = f'## {num}. {title}'
            doc.setdefault('sections', []).append({
                'section_uid': uid,
                'level': 2,
                'canonical_number': num,
                'title': title,
                'heading': heading,
                'path': rel,
                'binding_sha256': section_binding(uid, doc_id, rel, heading),
            })
    write_yaml(p, d)


def patch_source_management_guard():
    p = SOURCE / '09_TESTS/governance/governance_management_contract_guard.py'
    text = p.read_text(encoding='utf-8')
    needle = "    return {'status':'PASS' if not failures else 'FAIL','management_artifacts':len(REQ),'failures':failures}\n"
    block = '''    # Mother context/task-layer hardening: this existing management owner verifies the\n    # canonical Mother sections directly instead of creating a second validator.\n    m3=(root/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md').read_text(encoding='utf-8')\n    m4=(root/'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md').read_text(encoding='utf-8')\n    required_m3=[\n      'WEB-GOV-03-S063','SESSION_BOOTSTRAP_RESUME_GATE','live repository, target branch, commit SHA, and tree SHA',\n      'WEB-GOV-03-S064','GOVERNANCE_MAINTENANCE','PRODUCT_STAGE_EXECUTION','INNER_STAGE_IDENTITY != PRIMARY_TASK_SELECTION',\n      'WEB-GOV-03-S065','WORK_UNIT_RESOLUTION_GATE','WORK_UNIT_RESOLUTION_AMBIGUOUS',\n      'WEB-GOV-03-S066','GOVERNANCE_MAINTENANCE_PASS != PRODUCT_STAGE_PASS','zero product-stage gap-reduction',\n      'WEB-GOV-03-S067','INNER_STEP_PASS != TERMINAL_RUN_PASS','outer terminal conclusion',\n    ]\n    required_m4=['WEB-GOV-04-S079','WEB-GOV-04-S080','WEB-GOV-04-S081','Current Primary Task Layer','Product gap/blocker denominators MUST remain unchanged','outer terminal execution result']\n    for token in required_m3:\n        if token not in m3: failures.append('mother_context_task_layer_rule_missing:WEB-GOV-03:'+token)\n    for token in required_m4:\n        if token not in m4: failures.append('mother_context_task_layer_audit_missing:WEB-GOV-04:'+token)\n    return {'status':'PASS' if not failures else 'FAIL','management_artifacts':len(REQ),'failures':failures}\n'''
    text = replace_once(text, needle, block, 'governance_management_contract_guard.py')
    p.write_text(text, encoding='utf-8')


def patch_source_root_revision():
    p = SOURCE / '10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
    d = load_yaml(p); d['governance_revision'] = SOURCE_REVISION; write_yaml(p, d)


def patch_current_machine_policy():
    ep = ROOT / 'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'
    e = load_yaml(ep)
    e['session_bootstrap_resume_gate'] = {
        'required_before_any_current_state_judgment_planning_write_test_commit_workflow_deployment_or_closure_claim': True,
        'ordered_resolution': [
            'LIVE_REPOSITORY_BRANCH_COMMIT_TREE', 'FORMAL_REGISTRY_AND_CURRENT_GOVERNANCE_ENTRY',
            'MOTHER_GOVERNANCE_01_02_03_04', 'CURRENT_CANONICAL_AUTHORITY', 'CURRENT_PRIMARY_TASK_LAYER',
            'ACTIVE_WORK_UNIT_OR_WORK_UNIT_RESOLUTION_GATE', 'CANONICAL_OWNER_AND_IMPACTED_CONSUMERS',
            'PERSISTED_RESUME_POINT_AND_LAST_EFFECTFUL_ACTION', 'CURRENT_AUDIT_AND_EVIDENCE_STATE',
            'SELECTED_EXECUTION_PROFILE_WHEN_APPLICABLE', 'ENTRY_DEPENDENCIES_DOD_GATES_AND_TRANSITION',
            'PRE_WRITE_LIVE_IDENTITY_RECHECK'],
        'chat_memory_or_historical_summary_may_select_current_truth': False,
        'stage_profile_or_run_identity_may_select_current_governance': False,
        'missing_stale_ambiguous_conflicting_or_superseded_reference': 'BLOCK_RELOAD_OR_RESOLVE_REQUIRED',
    }
    e['task_layer_classification'] = {
        'required_before_work_unit_execution': True,
        'allowed_primary_layers': ['GOVERNANCE_MAINTENANCE','PRODUCT_STAGE_EXECUTION','TEST_OR_VALIDATION_MAINTENANCE','EVIDENCE_STATE_MAINTENANCE','DEPLOYMENT_OR_PRODUCTION'],
        'explicit_user_directive_and_current_authority_take_precedence_over_stage_profile_run_labels': True,
        'stage_profile_run_or_open_blocker_may_silently_redirect_primary_task': False,
        'task_layer_change_requires_fresh_session_bootstrap': True,
    }
    e['work_unit_resolution_gate'] = {
        'required_when_no_legal_active_primary_work_unit': True,
        'legal_inputs': ['CURRENT_AUTHORITY','EXPLICIT_AUTHORIZATION_OR_CHANGE_REQUEST','CHANGE_IMPACT_SET','DEPENDENCY_GRAPH','APPLICABILITY','BLOCKER_LEDGER','PREDECESSOR_CLOSURE_TRANSITION','CANONICAL_OWNER_MAPPING'],
        'ai_may_invent_successor_work_unit': False,
        'multiple_materially_distinct_legal_successors_without_authority': 'WORK_UNIT_RESOLUTION_AMBIGUOUS_BLOCK',
        'nearest_stage_file_test_or_blocker_is_implicit_successor': False,
    }
    write_yaml(ep, e)

    cp = ROOT / 'governance/specifications/current/VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml'
    c = load_yaml(cp)
    c['governance_maintenance_credit_isolation'] = {
        'applies_to': ['GOVERNANCE_POLICY_OR_REGISTRY','REFERENCE_OR_RESIDUAL_CLEANUP','VALIDATOR_SCANNER_CLASSIFIER_PARSER_HARNESS','WORKFLOW_CI_OR_GATE','EVIDENCE_STATE_PROJECTOR_RESUME_LEDGER_OR_RECEIPT','NEGATIVE_REGRESSION_OR_HISTORICAL_EVIDENCE_MAINTENANCE'],
        'product_stage_gap_reduction_credit': 0,
        'product_completion_credit': 0,
        'fresh_product_owner_evidence_required_to_change_product_denominator': True,
        'governance_maintenance_pass_is_product_stage_pass': False,
    }
    c.setdefault('terminal_result_semantics', {})['outer_terminal_conclusion_is_closure_authority'] = True
    c['terminal_result_semantics']['inner_job_or_step_success_may_close_outer_workflow'] = False
    c['terminal_result_semantics']['queued_or_in_progress_workflow_may_close'] = False
    cycle = c.get('canonical_cycle') or []
    for token in ['SESSION_BOOTSTRAP_RESUME_GATE','CLASSIFY_AND_LOCK_CURRENT_PRIMARY_TASK_LAYER','RESOLVE_ACTIVE_WORK_UNIT_OR_WORK_UNIT_RESOLUTION_GATE']:
        if token not in cycle:
            cycle.insert(0, token)
    c['canonical_cycle'] = cycle
    write_yaml(cp, c)


def patch_current_portability_validator():
    p = ROOT / 'governance/ci/validate_governance_portability.py'
    text = p.read_text(encoding='utf-8')
    marker = "out={\n"
    block = '''# Mother context/task-layer machine binding checks. These extend the existing portability owner.\nexec_control=yaml.safe_load((CUR/'EXECUTION_CYCLE_CONTROL.yaml').read_text(encoding='utf-8')) or {}\nclosure=yaml.safe_load((CUR/'VALIDATION_REMEDIATION_CLOSURE_PROTOCOL.yaml').read_text(encoding='utf-8')) or {}\nboot=exec_control.get('session_bootstrap_resume_gate') or {}\ntask=exec_control.get('task_layer_classification') or {}\nwu=exec_control.get('work_unit_resolution_gate') or {}\ncredit=closure.get('governance_maintenance_credit_isolation') or {}\nterminal=closure.get('terminal_result_semantics') or {}\nif boot.get('required_before_any_current_state_judgment_planning_write_test_commit_workflow_deployment_or_closure_claim') is not True: failures.append('session_bootstrap_resume_gate_not_required')\nif boot.get('stage_profile_or_run_identity_may_select_current_governance') is not False: failures.append('stage_profile_run_may_select_current_governance')\nexpected_layers={'GOVERNANCE_MAINTENANCE','PRODUCT_STAGE_EXECUTION','TEST_OR_VALIDATION_MAINTENANCE','EVIDENCE_STATE_MAINTENANCE','DEPLOYMENT_OR_PRODUCTION'}\nif set(task.get('allowed_primary_layers') or []) != expected_layers: failures.append('primary_task_layer_denominator_drift')\nif task.get('stage_profile_run_or_open_blocker_may_silently_redirect_primary_task') is not False: failures.append('primary_task_silent_redirect_not_forbidden')\nif wu.get('required_when_no_legal_active_primary_work_unit') is not True or wu.get('ai_may_invent_successor_work_unit') is not False: failures.append('work_unit_resolution_gate_not_fail_closed')\nif credit.get('product_stage_gap_reduction_credit') != 0 or credit.get('product_completion_credit') != 0: failures.append('governance_maintenance_product_credit_not_zero')\nif terminal.get('outer_terminal_conclusion_is_closure_authority') is not True or terminal.get('inner_step_pass_is_terminal_run_pass') is not False: failures.append('outer_terminal_closure_semantics_invalid')\n\n'''
    text = replace_once(text, marker, block + marker, 'validate_governance_portability.py')
    p.write_text(text, encoding='utf-8')


def regenerate_source_derivatives():
    run('python', str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'), cwd=SOURCE/'09_TESTS/governance')
    run('python', str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'), cwd=SOURCE/'09_TESTS/governance')
    cp = SOURCE / 'CHECKSUMS.sha256'
    files = sorted(p for p in SOURCE.rglob('*') if p.is_file() and p != cp)
    cp.write_text(''.join(f'{sha256_file(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files), encoding='utf-8')
    if len(files) != 74:
        raise RuntimeError(f'expected 74 checksum targets, got {len(files)}')
    return sha256_file(cp), *deterministic_bundle_and_zip(SOURCE)


def patch_identity_runners(checksum_sha: str, bundle_sha: str, zip_sha: str):
    vp = ROOT / '.github/governance-source/VERIFY_SOURCE_IDENTITY.py'
    v = vp.read_text(encoding='utf-8')
    v = replace_once(v, "import tarfile\n", "import tarfile\nimport zipfile\n", 'VERIFY_SOURCE_IDENTITY import')
    v = re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'", f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'", v, count=1)
    if 'EXPECTED_SOURCE_ZIP_SHA256' not in v:
        v = replace_once(v, f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'\n", f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'\nEXPECTED_SOURCE_ZIP_SHA256 = '{zip_sha}'\n", 'VERIFY source zip constant')
    zip_block = '''source_zip_sha = None\nif not errors:\n    zbuf = io.BytesIO()\n    with zipfile.ZipFile(zbuf, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:\n        for p in files:\n            rel = p.relative_to(SOURCE).as_posix()\n            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))\n            zi.compress_type = zipfile.ZIP_DEFLATED\n            zi.create_system = 3\n            mode = 0o755 if (p.stat().st_mode & 0o111) else 0o644\n            zi.external_attr = (mode & 0xFFFF) << 16\n            zf.writestr(zi, p.read_bytes())\n    source_zip_sha = hashlib.sha256(zbuf.getvalue()).hexdigest()\n    if source_zip_sha != EXPECTED_SOURCE_ZIP_SHA256:\n        fail(f'DETERMINISTIC_SOURCE_ZIP_SHA_MISMATCH expected={EXPECTED_SOURCE_ZIP_SHA256} actual={source_zip_sha}')\n\n'''
    if 'source_zip_sha = None' not in v:
        v = replace_once(v, 'report = {\n', zip_block + 'report = {\n', 'VERIFY zip computation')
        v = replace_once(v, "    'deterministic_bundle_sha256_actual': bundle_sha,\n", "    'deterministic_bundle_sha256_actual': bundle_sha,\n    'deterministic_source_zip_sha256_expected': EXPECTED_SOURCE_ZIP_SHA256,\n    'deterministic_source_zip_sha256_actual': source_zip_sha,\n", 'VERIFY zip report')
        v = replace_once(v, "print(f'PASS: deterministic bundle sha256={bundle_sha}')\n", "print(f'PASS: deterministic bundle sha256={bundle_sha}')\nprint(f'PASS: deterministic source zip sha256={source_zip_sha}')\n", 'VERIFY zip print')
    vp.write_text(v, encoding='utf-8')

    fp = ROOT / '.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'
    f = fp.read_text(encoding='utf-8')
    f = re.sub(r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'", f"EXPECTED_CHECKSUMS_SHA256 = '{checksum_sha}'", f, count=1)
    f = re.sub(r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'", f"EXPECTED_SOURCE_ZIP_SHA256 = '{zip_sha}'", f, count=1)
    f = re.sub(r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'", f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'", f, count=1)
    fp.write_text(f, encoding='utf-8')


def patch_current_projectors(checksum_sha: str, bundle_sha: str, zip_sha: str):
    regp = ROOT / 'governance/specifications/REGISTRY.yaml'
    reg = load_yaml(regp)
    active = reg['active_specification']
    if active.get('governance_uid') != OLD_UID:
        raise RuntimeError(f'Current governance drift: {active.get("governance_uid")}')
    reg['immediate_predecessor'] = {
        'governance_uid': OLD_UID,
        'display_version': active.get('display_version'),
        'version_role': 'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY',
        'status': 'SUPERSEDED_HISTORY_ONLY_AFTER_MOTHER_CONTEXT_TASK_LAYER_HARDENING',
    }
    active['governance_uid'] = NEW_UID
    active['display_version'] = DISPLAY_VERSION
    active['version_role'] = 'CURRENT_GOVERNANCE_DISPLAY_VERSION'
    active['status'] = 'ACTIVE_CURRENT_GOVERNANCE'
    aliases = active.setdefault('aliases', [])
    if 'mother-context-task-layer-hardening' not in aliases: aliases.append('mother-context-task-layer-hardening')
    rp = reg.setdefault('resolution_policy', {})
    rp['session_bootstrap_resume_gate_required_before_current_state_or_effectful_execution'] = True
    rp['current_primary_task_layer_required'] = True
    rp['stage_profile_run_identity_may_redirect_primary_task'] = False
    rp['work_unit_resolution_gate_required_when_active_work_unit_missing'] = True
    write_yaml(regp, reg)

    mp = ROOT / 'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    m = load_yaml(mp)
    m['artifact_uid'] = NEW_UID
    m['display_version'] = DISPLAY_VERSION
    sl = m.setdefault('source_lineage', {})
    sl['verified_package_filename'] = PACKAGE_FILENAME
    sl['verified_package_sha256'] = zip_sha
    sl['predecessor_governance_uid'] = OLD_UID
    sl['promotion_authorization_uid'] = AUTH_UID
    sl['source_bytes_changed_by_this_successor'] = True
    sl['source_identity_reused_only_because_source_bytes_are_unchanged'] = False
    sl['deterministic_source_bundle_sha256'] = bundle_sha
    sl['checksum_manifest_sha256'] = checksum_sha
    sl['verified_source_revision'] = SOURCE_REVISION
    sl['verified_package_hash_model'] = 'DETERMINISTIC_ZIP_SOURCE_SET_V2_FIXED_METADATA'
    cp = m.setdefault('closure_policy', {})
    cp['session_bootstrap_resume_gate_required'] = True
    cp['current_primary_task_layer_lock_required'] = True
    cp['governance_maintenance_product_credit'] = 0
    cp['work_unit_resolution_gate_required_when_no_active_work_unit'] = True
    cp['outer_terminal_conclusion_required_for_terminal_credit'] = True
    write_yaml(mp, m)

    gp = ROOT / 'GOVERNANCE_CURRENT.yaml'
    g = load_yaml(gp)
    g['active_governance_uid'] = NEW_UID; g['display_version'] = DISPLAY_VERSION
    si = g.setdefault('source_identity', {})
    si['source_bytes_changed_by_current_successor'] = True
    si['verified_package_sha256'] = zip_sha
    si['deterministic_source_bundle_sha256'] = bundle_sha
    si['checksum_manifest_sha256'] = checksum_sha
    si['verified_source_revision'] = SOURCE_REVISION
    g['current_primary_task_selection_contract'] = {
        'session_bootstrap_resume_gate_required': True,
        'task_layer_classification_required': True,
        'stage_profile_run_identity_may_redirect_primary_task': False,
        'missing_active_work_unit_requires_work_unit_resolution_gate': True,
    }
    write_yaml(gp, g)

    ap = ROOT / 'governance/test/ACTIVE_STATE.yaml'
    a = load_yaml(ap)
    a['specification_uid'] = NEW_UID
    tr = a.setdefault('governance_revision_transition', {})
    tr['predecessor_governance_uid'] = OLD_UID; tr['current_governance_uid'] = NEW_UID; tr['fresh_revalidation_required'] = True
    ex = a.setdefault('execution', {})
    ex['website_construction_allowed'] = False; ex['deployment_allowed'] = False
    s2 = ex.setdefault('stage2', {})
    s2['stage_entry_gate'] = 'REVERIFY_REQUIRED'; s2['stage_exit_allowed'] = False; s2['revalidation_required_under_current_governance'] = True; s2['prior_results_authoritative_for_current_governance'] = False
    proto = a.setdefault('stage_execution_remediation_closure_protocol', {})
    proto['frozen_specification_uid'] = NEW_UID
    a['current_primary_task_layer'] = 'GOVERNANCE_MAINTENANCE'
    a['current_primary_task_authorization_uid'] = AUTH_UID
    a['current_primary_task_product_stage_credit'] = 0
    write_yaml(ap, a)

    candp = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
    cand = load_yaml(candp)
    cur = cand.get('current_stage2_execution')
    if isinstance(cur, dict):
        cur['current_governance_uid'] = NEW_UID
        cur['fresh_revalidation_required'] = True
        cur['product_credit_from_governance_maintenance'] = 0
        write_yaml(candp, cand)


def validate_worktree():
    run('python', str(SOURCE/'09_TESTS/governance/validate_section_registry.py'), cwd=SOURCE/'09_TESTS/governance')
    run('python', str(SOURCE/'09_TESTS/governance/governance_management_contract_guard.py'), cwd=SOURCE/'09_TESTS/governance')
    run('python', str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py'))
    run('python', str(ROOT/'governance/ci/governance_resolver.py'))
    run('python', str(ROOT/'governance/ci/validate_governance_portability.py'))
    run('python', str(ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py'))
    # Generated reports are CI evidence, not part of this successor source transaction.
    for rel in ['.github/governance-source/SOURCE_IDENTITY_REPORT.json']:
        run('git', 'checkout', '--', rel)


def main():
    if not AUTH.is_file(): raise RuntimeError('R2 authorization receipt missing')
    auth = load_yaml(AUTH)
    if auth.get('status') != 'APPROVED_FOR_EXACT_SCOPE' or auth.get('single_use') is not True:
        raise RuntimeError('R2 authorization receipt invalid')
    registry = load_yaml(ROOT/'governance/specifications/REGISTRY.yaml')
    if registry.get('active_specification', {}).get('governance_uid') != OLD_UID:
        raise RuntimeError('Current governance changed before materialization')

    patch_mother_docs()
    patch_section_registry()
    patch_source_management_guard()
    patch_source_root_revision()
    patch_current_machine_policy()
    patch_current_portability_validator()
    checksum_sha, bundle_sha, zip_sha = regenerate_source_derivatives()
    patch_identity_runners(checksum_sha, bundle_sha, zip_sha)
    patch_current_projectors(checksum_sha, bundle_sha, zip_sha)
    validate_worktree()

    # One-time transaction machinery MUST leave zero Current residual.
    if HELPER.exists(): HELPER.unlink()
    if WORKFLOW.exists(): WORKFLOW.unlink()

    summary = {
        'new_governance_uid': NEW_UID,
        'display_version': DISPLAY_VERSION,
        'source_revision': SOURCE_REVISION,
        'checksum_manifest_sha256': checksum_sha,
        'deterministic_source_bundle_sha256': bundle_sha,
        'deterministic_source_zip_sha256': zip_sha,
    }
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
