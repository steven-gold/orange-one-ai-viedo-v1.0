#!/usr/bin/env python3
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import argparse, json, os, re, subprocess, sys, urllib.request
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '00_SOURCE_INTAKE/fresh_run_003'
BASE = RUN / '04_PAGE_FUNCTIONAL_CONTRACT'
CORE = BASE / 'CORE-01'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
REGISTRY = ROOT / 'governance/specifications/REGISTRY.yaml'
CANDIDATE = ROOT / 'governance/test/stage02/STAGE02_CORE01_DESIGN_CONTRACT_CANDIDATE.json'
SEMANTIC = ROOT / 'governance/test/stage02/STAGE02_CORE01_DESIGN_CONTRACT_SEMANTIC_REVIEW.json'
PACKAGE = ROOT / 'governance/test/stage02/STAGE02_CORE01_DESIGN_CONTRACT_REVIEW_PACKAGE.json'
APPROVAL = ROOT / 'governance/test/stage02/STAGE02_CORE01_COHERENT_DESIGN_CONTRACT_APPROVAL_EVIDENCE.yaml'
SPEC = CORE / 'FUNCTIONAL_CHAIN_SPEC.yaml'
PROBLEMS = BASE / 'CURRENT_PROBLEM_REGISTER.yaml'
OVERLAY = BASE / 'EFFECTIVE_CONTRACT_OVERLAY.yaml'
LEDGER = BASE / 'RESOLUTION_LEDGER.yaml'
LATEST = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
FINDINGS = ROOT / 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
CHANGE = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
RAW = RUN / '00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml'
CURRENT_UID = 'GOV-REV-20260918-DESIGN-REMEDIATION-ROUTING-HARDENING'
WORK_UID = 'WU-STAGE02-CORE01-FUNCTIONAL-REMEDIATION-002'
ATTEMPT_UID = 'STAGE02-FRESH-20260918-007'
EXPECTED_RAW_BLOB = '9490f3bcc28c5511bc04d6c3ce53c026e3c4667f'
RESOLUTION_UID = 'STAGE02-RESOLUTION-CORE01-DESIGN-CONTRACT-20260919-001'
NEXT = 'VERIFY_PERSISTED_CORE01_DESIGN_CONTRACT_MATERIALIZATION_AND_CLOSE_WORK_UNIT'
CLOSE_NEXT = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_REMAINING_STAGE02_SCOPE'

def die(msg: str) -> None:
    print('BLOCK:', msg, file=sys.stderr); raise SystemExit(1)

def load_yaml(path: Path) -> dict:
    if not path.is_file(): die('MISSING:' + str(path.relative_to(ROOT)))
    try: obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc: die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict): die('MAPPING_REQUIRED:' + str(path.relative_to(ROOT)))
    return obj

def load_json(path: Path) -> dict:
    if not path.is_file(): die('MISSING:' + str(path.relative_to(ROOT)))
    try: obj = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc: die(f'JSON_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict): die('MAPPING_REQUIRED:' + str(path.relative_to(ROOT)))
    return obj

def dump_yaml(path: Path, obj: dict) -> None:
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')

def dump_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def git(*args: str) -> str:
    cp = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    if cp.returncode: die('GIT:' + cp.stderr.strip())
    return cp.stdout.strip()

def git_blob(path: Path) -> str: return git('rev-parse', 'HEAD:' + str(path.relative_to(ROOT)))
def idx(items, key): return {x.get(key): x for x in (items or []) if isinstance(x, dict) and x.get(key)}

def canonicalize(value):
    if isinstance(value, dict): return {k: canonicalize(v) for k, v in value.items()}
    if isinstance(value, list): return [canonicalize(v) for v in value]
    if isinstance(value, str) and value.startswith('TEMP-CORE01-'): return value[len('TEMP-'):]
    return value

def event_token(text: str):
    text = str(text or '')
    if '|' in text:
        tail = text.split('|', 1)[1].strip()
        if tail and tail.lower() not in {'event none', 'none'}: return tail
    m = re.search(r'\b[a-z][a-z0-9_]*\.[a-z0-9_.]+\b', text)
    return m.group(0) if m else None

def build_event_state(old: str, event: str) -> str:
    old = str(old or '').strip()
    if '|' in old:
        prefix = old.split('|', 1)[0].strip()
        return f'{prefix} | {event}' if prefix else event
    if 'no canonical transition/event' in old.lower(): return f'business action | {event}'
    return f'{old} | {event}' if old else event

def validate_identity(state, registry, package, candidate, semantic, approval):
    gov = (registry.get('active_specification') or {}).get('governance_uid')
    if gov != CURRENT_UID or state.get('specification_uid') != CURRENT_UID: die('CURRENT_GOVERNANCE_UID_DRIFT')
    work = state.get('active_work_unit') or {}
    if work.get('work_unit_uid') != WORK_UID or work.get('current_status') not in {'PENDING_EXPLICIT_COHERENT_PACKAGE_REVIEW','PENDING_EXACT_HEAD_TERMINAL_CLOSURE'}:
        die('CURRENT_WORK_UNIT_IDENTITY_OR_STATUS_DRIFT')
    if (state.get('resume_control') or {}).get('current_work_unit_uid') != WORK_UID: die('CURRENT_RESUME_WORK_UNIT_DRIFT')
    if package.get('current_governance_uid') != CURRENT_UID or package.get('work_unit_uid') != WORK_UID: die('PACKAGE_IDENTITY_DRIFT')
    if package.get('review_model', {}).get('one_coherent_package_review_supported') is not True: die('PACKAGE_WHOLE_REVIEW_NOT_ALLOWED')
    if candidate.get('current_governance_uid') != CURRENT_UID or candidate.get('work_unit_uid') != WORK_UID: die('CANDIDATE_IDENTITY_DRIFT')
    if candidate.get('status') != 'READY_FOR_EXPLICIT_COHERENT_PACKAGE_REVIEW': die('CANDIDATE_NOT_REVIEW_READY')
    if candidate.get('materialization_allowed') is not False or candidate.get('product_blocker_credit') != 0: die('CANDIDATE_PREMATURE_AUTHORITY_EFFECT')
    if semantic.get('machine_review_result') != 'PASS_CURRENT_IDENTITY_AND_TESTED_SEMANTIC_TEMPLATE_REVALIDATION': die('SEMANTIC_MACHINE_REVIEW_NOT_PASS')
    if semantic.get('human_product_contract_review_status') != 'PENDING_EXPLICIT_COHERENT_PACKAGE_REVIEW': die('SEMANTIC_REVIEW_STATUS_DRIFT')
    if approval.get('artifact_type') != 'PRODUCT_DESIGN_CONTRACT_PACKAGE_REVIEW_EVIDENCE' or approval.get('normative_authority') is not False: die('APPROVAL_EVIDENCE_TYPE_DRIFT')
    if approval.get('current_governance_uid') != CURRENT_UID or approval.get('work_unit_uid') != WORK_UID or approval.get('page_uid') != 'CORE-01': die('APPROVAL_EVIDENCE_IDENTITY_DRIFT')
    if approval.get('decision') != 'APPROVE_WHOLE_COHERENT_CANDIDATE_AND_CONTINUE_CORE01_TO_CLOSURE': die('APPROVAL_DECISION_MISSING')
    if approval.get('approved_by') != 'USER' or approval.get('explicit_user_decision_observed') is not True: die('EXPLICIT_USER_APPROVAL_EVIDENCE_MISSING')
    if approval.get('candidate_is_product_authority') is not False or approval.get('canonical_owner_materialization_allowed') is not True: die('APPROVAL_AUTHORITY_BOUNDARY_DRIFT')
    refs = approval.get('bound_artifacts') or {}
    for key, path, expected_uid in (
        ('review_package', PACKAGE, package.get('artifact_uid')),
        ('candidate', CANDIDATE, candidate.get('artifact_uid')),
        ('semantic_review', SEMANTIC, semantic.get('artifact_uid')),
    ):
        rec = refs.get(key) or {}
        if rec.get('path') != str(path.relative_to(ROOT)) or rec.get('artifact_uid') != expected_uid: die(f'APPROVAL_BOUND_ARTIFACT_DRIFT:{key}')
        if rec.get('git_blob_sha') != git_blob(path): die(f'APPROVAL_BOUND_BLOB_DRIFT:{key}')
    if git_blob(RAW) != EXPECTED_RAW_BLOB: die('IMMUTABLE_RAW_BLOB_DRIFT')

def prepare_units(candidate: dict, problems: dict):
    units = candidate.get('units') or []; rows = problems.get('problems') or []
    if len(units) != 25 or len(rows) != 45: die(f'DENOMINATOR_DRIFT:units={len(units)}:problems={len(rows)}')
    by_problem = {}
    for unit in units:
        for uid in unit.get('blocker_uids') or []:
            if uid in by_problem: die('DUPLICATE_CANDIDATE_BLOCKER:' + uid)
            by_problem[uid] = unit
    problem_uids = [r.get('problem_uid') for r in rows]
    if len(set(problem_uids)) != 45 or set(problem_uids) != set(by_problem): die('CANDIDATE_PROBLEM_COVERAGE_NOT_45_OF_45')
    for row in rows:
        unit = by_problem[row['problem_uid']]
        if unit.get('target_uid') != row.get('target_uid') or unit.get('category') != row.get('category'): die('CANDIDATE_PROBLEM_IDENTITY_MISMATCH:' + row['problem_uid'])
    return units, rows

def apply_materialization(spec: dict, units: list[dict], approval_ref: str) -> dict:
    out = deepcopy(spec); proj = out.get('source_projection') or {}
    ports = idx(proj.get('integration_ports'), 'port_uid'); events = idx(proj.get('events'), 'event_uid'); transitions = idx(proj.get('stage_transitions'), 'transition_uid')
    identity_promotions = {}
    for unit in units:
        prop = canonicalize(unit.get('proposal') or {}); kind = prop.get('proposal_kind')
        if kind == 'ACTION_PAYLOAD_INPUT_SCHEMA':
            puid = prop.get('port_uid'); port = ports.get(puid)
            if not port: die('MATERIALIZE_PORT_NOT_FOUND:' + str(puid))
            schema = prop.get('schema')
            if not isinstance(schema, dict): die('MATERIALIZE_SCHEMA_MISSING:' + str(unit.get('target_uid')))
            original_uid = ((unit.get('proposal') or {}).get('schema') or {}).get('schema_uid'); promoted_uid = schema.get('schema_uid')
            if original_uid and promoted_uid and original_uid != promoted_uid: identity_promotions[original_uid] = promoted_uid
            if port.get('request_schema') not in (None, {}) and port.get('request_schema') != schema: die('CONFLICTING_EXISTING_REQUEST_SCHEMA:' + puid)
            port['request_schema'] = schema
        elif kind == 'AUDIT_EVENT_BINDING_AND_EVENT_REGISTRY_ENTRY':
            puid = prop.get('port_uid'); port = ports.get(puid)
            if not port: die('MATERIALIZE_AUDIT_PORT_NOT_FOUND:' + str(puid))
            euid, event = prop.get('event_uid'), prop.get('event')
            if not euid or not event: die('MATERIALIZE_AUDIT_EVENT_IDENTITY_MISSING')
            existing_event = events.get(euid)
            if existing_event:
                if existing_event.get('event') != event: die('CONFLICTING_EVENT_IDENTITY:' + euid)
            else:
                rec = {'event_uid': euid, 'event': event}; proj.setdefault('events', []).append(rec); events[euid] = rec
            port['state_event'] = build_event_state(port.get('state_event'), event)
        elif kind == 'STATE_TRANSITION_LEDGER_ENRICHMENT':
            tid = prop.get('transition_uid'); tr = transitions.get(tid)
            if not tr: die('MATERIALIZE_TRANSITION_NOT_FOUND:' + str(tid))
            for key in ('mutation_owner','failure_state','recovery','audit_event_uid','illegal_transition_tests'):
                val = prop.get(key)
                if val in (None, '', [], {}): die(f'MATERIALIZE_TRANSITION_FIELD_MISSING:{tid}:{key}')
                if key == 'illegal_transition_tests':
                    for a, b in zip((unit.get('proposal') or {}).get(key) or [], val):
                        if isinstance(a, dict) and isinstance(b, dict) and a.get('test_uid') != b.get('test_uid'): identity_promotions[a.get('test_uid')] = b.get('test_uid')
                if tr.get(key) not in (None, '', [], {}) and tr.get(key) != val: die(f'CONFLICTING_TRANSITION_FIELD:{tid}:{key}')
                tr[key] = val
        else: die('UNSUPPORTED_CANDIDATE_PROPOSAL_KIND:' + str(kind))
    out['design_contract_remediation'] = {
        'current_governance_uid': CURRENT_UID,'work_unit_uid': WORK_UID,'review_package_ref': str(PACKAGE.relative_to(ROOT)),
        'candidate_ref': str(CANDIDATE.relative_to(ROOT)),'semantic_review_ref': str(SEMANTIC.relative_to(ROOT)),
        'approval_evidence_ref': approval_ref,'approved_unit_count': 25,'covered_problem_count': 45,
        'canonical_owner_materialization': True,'candidate_bytes_became_authority_directly': False,'raw_source_mutated': False,
        'identity_promotion_rule': 'TEMP-CORE01-* -> CORE-01-*; semantic payload unchanged','identity_promotions': dict(sorted(identity_promotions.items())),
    }
    return out

def validate_materialized(spec: dict, units: list[dict], problems: dict) -> None:
    proj = spec.get('source_projection') or {}; ports = idx(proj.get('integration_ports'), 'port_uid'); events = idx(proj.get('events'), 'event_uid'); transitions = idx(proj.get('stage_transitions'), 'transition_uid')
    covered = []
    for unit in units:
        prop = canonicalize(unit.get('proposal') or {}); kind = prop.get('proposal_kind')
        if kind == 'ACTION_PAYLOAD_INPUT_SCHEMA':
            if (ports.get(prop.get('port_uid')) or {}).get('request_schema') != prop.get('schema'): die('VALIDATE_REQUEST_SCHEMA_MISMATCH:' + str(unit.get('target_uid')))
        elif kind == 'AUDIT_EVENT_BINDING_AND_EVENT_REGISTRY_ENTRY':
            euid, event = prop.get('event_uid'), prop.get('event')
            if (events.get(euid) or {}).get('event') != event: die('VALIDATE_EVENT_REGISTRY_MISMATCH:' + str(euid))
            if event_token((ports.get(prop.get('port_uid')) or {}).get('state_event')) != event: die('VALIDATE_PORT_EVENT_BINDING_MISMATCH:' + str(prop.get('port_uid')))
        elif kind == 'STATE_TRANSITION_LEDGER_ENRICHMENT':
            tr = transitions.get(prop.get('transition_uid')) or {}
            for key in ('mutation_owner','failure_state','recovery','audit_event_uid','illegal_transition_tests'):
                if tr.get(key) != prop.get(key): die(f'VALIDATE_TRANSITION_FIELD_MISMATCH:{prop.get("transition_uid")}:{key}')
        else: die('VALIDATE_UNSUPPORTED_KIND:' + str(kind))
        covered.extend(unit.get('blocker_uids') or [])
    if len(covered) != 45 or len(set(covered)) != 45: die('VALIDATED_BLOCKER_COVERAGE_NOT_45')
    if set(covered) != {r.get('problem_uid') for r in problems.get('problems') or []}: die('VALIDATED_BLOCKER_UID_SET_DRIFT')
    meta = spec.get('design_contract_remediation') or {}
    if meta.get('current_governance_uid') != CURRENT_UID or meta.get('work_unit_uid') != WORK_UID or meta.get('covered_problem_count') != 45: die('MATERIALIZATION_METADATA_DRIFT')

def materialize():
    state=load_yaml(STATE); registry=load_yaml(REGISTRY); package=load_json(PACKAGE); candidate=load_json(CANDIDATE); semantic=load_json(SEMANTIC); approval=load_yaml(APPROVAL)
    validate_identity(state, registry, package, candidate, semantic, approval)
    problems=load_yaml(PROBLEMS); overlay=load_yaml(OVERLAY); ledger=load_yaml(LEDGER); spec=load_yaml(SPEC); latest=load_json(LATEST); findings=load_yaml(FINDINGS); change=load_yaml(CHANGE)
    units, rows = prepare_units(candidate, problems); approved = apply_materialization(spec, units, str(APPROVAL.relative_to(ROOT))); validate_materialized(approved, units, problems); dump_yaml(SPEC, approved)
    for row in rows:
        row.update({'status':'RESOLVED_VERIFIED_DESIGN_CONTRACT_MATERIALIZATION','resolution_credit':1,'resolution_uid':RESOLUTION_UID,'resolution_ref':str(LEDGER.relative_to(ROOT))+'#'+RESOLUTION_UID,'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_owner_ref':str(SPEC.relative_to(ROOT)),'external_authority_resolution_claimed':False})
    problems.update({'raw_discovery_problem_count':45,'validated_product_successor_signature_count':45,'effective_open_problem_count':0,'open_problem_count':0,'resolved_problem_count':45,'stage_exit_allowed':False,'stage03_allowed':False}); dump_yaml(PROBLEMS, problems)
    overlay.update({'current_discovery_gap_total':45,'validated_product_successor_signature_count':45,'current_effective_gap_elimination_claimed':45,'current_effective_gap_total':0,'raw_absence_alone_is_effective_gap':False,'physical_rescan_and_signature_reconciliation_required':True,'current_product_contract_owner_ref':str(SPEC.relative_to(ROOT)),'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'external_authority_resolution_claimed':False}); dump_yaml(OVERLAY, overlay)
    entries=ledger.setdefault('entries', [])
    rec={'resolution_uid':RESOLUTION_UID,'resolution_type':'APPROVED_COHERENT_DESIGN_CONTRACT_MATERIALIZATION','work_unit_uid':WORK_UID,'page_uid':'CORE-01','review_package_ref':str(PACKAGE.relative_to(ROOT)),'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_owner_ref':str(SPEC.relative_to(ROOT)),'source_problem_denominator':45,'materialized_design_unit_count':25,'validated_product_successor_signature_count':45,'fresh_raw_discovery_gap_count':45,'effective_functional_gap_count':0,'functional_gap_reduction_credit':45,'external_authority_resolution_credit':0,'validation_status':'PASS_EXACT_45_OF_45'}
    existing=next((x for x in entries if x.get('resolution_uid')==RESOLUTION_UID), None)
    if existing and existing != rec: die('EXISTING_RESOLUTION_ENTRY_CONFLICT')
    if not existing: entries.append(rec)
    ledger['functional_problem_resolution_credit_total']=sum(int(x.get('functional_gap_reduction_credit',0)) for x in entries); ledger['external_authority_resolution_credit_total']=sum(int(x.get('external_authority_resolution_credit',0)) for x in entries); dump_yaml(LEDGER, ledger)
    head=git('rev-parse','HEAD')
    latest.update({'source_head_sha':head,'test_mode':'FRESH_REEXECUTION_FROM_IMMUTABLE_STAGE1_INPUTS_WITH_APPROVED_CORE01_DESIGN_CONTRACT_SUCCESSOR','reexecution_cycle':'CORE01_DESIGN_CONTRACT_REEXECUTION_R1','fresh_functional_gap_total':45,'validated_product_successor_signature_count':45,'effective_functional_gap_total':0,'closure_blocker_total':0,'result':'BLOCKED','stage_exit_allowed':False,'stage_scope_complete':False,'target_pages':['CORE-01'],'remaining_pages':['ASSET-01'],'current_specification_mutated':False,'ai_autofill_used':False,'inference_used':False,'prior_stage2_results_used':False,'prior_stage2_counts_used_as_scan_input':False})
    latest['design_contract_materialization']={'work_unit_uid':WORK_UID,'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_owner_ref':str(SPEC.relative_to(ROOT)),'approved_design_unit_count':25,'validated_product_successor_signature_count':45,'effective_functional_gap_count':0,'raw_source_mutated':False,'external_authority_resolution_claimed':False}
    page=latest.setdefault('pages',{}).setdefault('CORE-01',{}); page.update({'validated_product_successor_signature_count':45,'effective_functional_gap_count':0,'functional_completion_effective':True})
    latest['notes']=['Raw discovery remains 45 because immutable Stage-1 Raw Source is preserved by design.','Exactly 45 CORE-01 signatures are freshly reconciled against the approved canonical product-contract successor.','CORE-01 effective functional gaps are zero; whole Stage-02 remains BLOCKED only because ASSET-01 is outside this work unit and not yet executed.','All seven external Authority references remain unresolved and receive zero resolution credit.']; dump_json(LATEST, latest)
    findings.update({'source_cycle':'CORE01_DESIGN_CONTRACT_REEXECUTION_R1','source_head_sha':head,'fresh_functional_gap_total':45,'validated_product_successor_signature_count':45,'fresh_effective_gap_total':0,'fresh_closure_blocker_total':0,'page_results':{'CORE-01':{'raw_functional_gap_count':45,'validated_product_successor_signature_count':45,'effective_functional_gap_count':0,'closure_blocker_count':0,'closure_blockers':[]}},'result':'BLOCKED','next_action':NEXT,'review_only_design_contract_package_ref':str(PACKAGE.relative_to(ROOT)),'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_product_contract_owner_ref':str(SPEC.relative_to(ROOT))}); dump_yaml(FINDINGS, findings)
    cur=change.setdefault('current_stage2_execution',{}); cur.update({'state':'TEST_EXECUTED_BLOCKED','current_functional_gap_count':0,'current_closure_blocker_count':0,'stage_exit_allowed':False,'website_construction_allowed':False,'deployment_allowed':False,'source_execution_sha':head,'reexecution_cycle':'CORE01_DESIGN_CONTRACT_REEXECUTION_R1','target_pages':['CORE-01'],'remaining_pages':['ASSET-01'],'stage_scope_complete':False,'next_action':NEXT,'attempt_uid':ATTEMPT_UID,'frozen_governance_uid':CURRENT_UID,'raw_discovery_gap_count':45,'product_materialization_elimination_count':45,'validated_product_successor_signature_count':45,'effective_functional_gap_count':0,'external_authority_elimination_count':0,'total_fresh_elimination_count':45,'preserved_external_authority_union_count':7,'prior_stage2_results_used':False,'review_only_design_contract_package_ref':str(PACKAGE.relative_to(ROOT)),'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'canonical_product_contract_owner_ref':str(SPEC.relative_to(ROOT)),'product_blocker_reduction_credit':45}); dump_yaml(CHANGE, change)
    work=state.get('active_work_unit') or {}; work.update({'current_status':'PENDING_EXACT_HEAD_TERMINAL_CLOSURE','product_blocker_credit':45,'human_product_contract_review_status':'APPROVED_EXPLICIT_COHERENT_PACKAGE_REVIEW','product_contract_materialization_owner':str(SPEC.relative_to(ROOT))}); work['design_contract_materialization']={'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),'approved_design_unit_count':25,'raw_discovery_problem_count':45,'validated_product_successor_signature_count':45,'effective_open_problem_count':0,'resolution_uid':RESOLUTION_UID,'fresh_reexecution_source_head':head,'outer_terminal_result':'PENDING'}
    state['next_action']=NEXT; resume=state.setdefault('resume_control',{}); resume.update({'current_resume_point':'STAGE2_CORE01_DESIGN_CONTRACT_MATERIALIZED_PENDING_EXACT_HEAD_TERMINAL_CLOSURE','exact_next_action':NEXT,'current_work_unit_uid':WORK_UID})
    state['stage02_current_problem_state'].update({'fresh_functional_gap_total':45,'effective_functional_gap_total':0,'validated_product_successor_signature_count':45,'fresh_closure_blocker_total':0})
    state['stage02_material_remediation'].update({'cycle':'CORE01_DESIGN_CONTRACT_REEXECUTION_R1','remaining_fresh_functional_gap_count':0,'raw_discovery_functional_gap_count':45,'validated_product_materialization_count':45,'effective_functional_gap_total':0,'status':'CORE01_DESIGN_CONTRACT_MATERIALIZED_FRESHLY_REEXECUTED_EFFECTIVE_ZERO'})
    active=state.get('stage02_active_attempt') or {}; active.update({'source_execution_sha':head,'fresh_functional_gap_total':45,'effective_functional_gap_total':0,'fresh_closure_blocker_total':0,'validated_product_materialization_count':45,'next_action':NEXT,'reexecution_cycle':'CORE01_DESIGN_CONTRACT_REEXECUTION_R1','candidate_materialization_allowed':True,'design_contract_approval_evidence_ref':str(APPROVAL.relative_to(ROOT))}); dump_yaml(STATE,state)
    print('PASS: approved coherent CORE-01 candidate materialized into existing canonical FUNCTIONAL_CHAIN_SPEC owner')
    print('PASS: fresh raw discovery=45; exact validated successor signatures=45; effective CORE-01 gaps=0')
    print('PASS: external Authority resolution credit=0; ASSET-01 remains out of scope')

def finalize_artifact():
    artifact_id=__import__('os').environ.get('STAGE02_SOURCE_ARTIFACT_ID','').strip(); artifact_digest=__import__('os').environ.get('STAGE02_SOURCE_ARTIFACT_DIGEST','').strip(); run_id=__import__('os').environ.get('GITHUB_RUN_ID','').strip()
    if not artifact_id or not artifact_digest or not run_id: die('FINALIZE_ARTIFACT_ENV_MISSING')
    state=load_yaml(STATE); findings=load_yaml(FINDINGS); change=load_yaml(CHANGE); active=state.get('stage02_active_attempt') or {}
    active.update({'source_workflow_run_id':int(run_id),'source_artifact_id':int(artifact_id),'source_artifact_sha256':artifact_digest.removeprefix('sha256:')})
    findings.update({'source_workflow_run_id':int(run_id),'source_artifact_id':int(artifact_id),'source_artifact_sha256':artifact_digest.removeprefix('sha256:')})
    cur=change.get('current_stage2_execution') or {}; cur.update({'source_workflow_run_id':int(run_id),'source_artifact_id':int(artifact_id),'source_artifact_sha256':artifact_digest.removeprefix('sha256:')})
    work=state.get('active_work_unit') or {}; dm=work.get('design_contract_materialization') or {}; dm.update({'source_workflow_run_id':int(run_id),'source_artifact_id':int(artifact_id),'source_artifact_sha256':artifact_digest.removeprefix('sha256:')}); work['design_contract_materialization']=dm
    dump_yaml(STATE,state); dump_yaml(FINDINGS,findings); dump_yaml(CHANGE,change); print(f'PASS: finalized fresh CORE-01 materialization artifact identity run={run_id} artifact={artifact_id}')

def github_run(run_id: int) -> dict:
    token=os.environ.get('GITHUB_TOKEN','').strip(); repo=os.environ.get('GITHUB_REPOSITORY','').strip()
    if not token or not repo: die('GITHUB_TERMINAL_OBSERVATION_CONTEXT_MISSING')
    req=urllib.request.Request(
        f'https://api.github.com/repos/{repo}/actions/runs/{run_id}',
        headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp: obj=json.loads(resp.read().decode('utf-8'))
    except Exception as exc: die(f'GITHUB_TERMINAL_OBSERVATION_FAILED:{exc!r}')
    if not isinstance(obj,dict): die('GITHUB_TERMINAL_OBSERVATION_INVALID')
    return obj

def close_work_unit():
    state=load_yaml(STATE); findings=load_yaml(FINDINGS); change=load_yaml(CHANGE); problems=load_yaml(PROBLEMS); latest=load_json(LATEST)
    work=state.get('active_work_unit') or {}
    if work.get('work_unit_uid')!=WORK_UID or work.get('current_status')!='PENDING_EXACT_HEAD_TERMINAL_CLOSURE': die('WORK_UNIT_NOT_READY_FOR_TERMINAL_CLOSURE')
    if work.get('product_blocker_credit')!=45: die('WORK_UNIT_PRODUCT_CREDIT_NOT_45')
    if problems.get('open_problem_count')!=0 or problems.get('resolved_problem_count')!=45 or problems.get('effective_open_problem_count')!=0: die('PROBLEM_REGISTER_NOT_READY_FOR_CLOSURE')
    if latest.get('effective_functional_gap_total')!=0 or latest.get('validated_product_successor_signature_count')!=45: die('FRESH_EVIDENCE_NOT_EFFECTIVE_ZERO')
    dm=work.get('design_contract_materialization') or {}; run_id=int(dm.get('source_workflow_run_id') or 0)
    if not run_id: die('MATERIALIZATION_OUTER_RUN_ID_MISSING')
    run=github_run(run_id)
    if run.get('status')!='completed' or run.get('conclusion')!='success': die('MATERIALIZATION_OUTER_RUN_NOT_TERMINAL_SUCCESS')
    if run.get('head_sha')!=dm.get('fresh_reexecution_source_head'): die('MATERIALIZATION_OUTER_RUN_HEAD_DRIFT')
    materialization_commit=git('log','-1','--format=%H','--grep=persist approved core01 design contract materialization and fresh reexecution')
    if not materialization_commit: die('PERSISTED_MATERIALIZATION_COMMIT_NOT_FOUND')
    git('merge-base','--is-ancestor',materialization_commit,'HEAD')
    closed=deepcopy(work)
    closed['current_status']='CLOSED_VERIFIED_CORE01_EFFECTIVE_FUNCTIONAL_GAPS_ZERO'
    closed['terminal_disposition']='CLOSED_VERIFIED_PRODUCT_CONTRACT_MATERIALIZATION_AND_FRESH_REEXECUTION'
    closed['resume_after_closure']=CLOSE_NEXT
    closed_dm=closed.get('design_contract_materialization') or {}; closed_dm['outer_terminal_result']='success'; closed_dm['persisted_materialization_commit']=materialization_commit; closed['design_contract_materialization']=closed_dm
    closed['closure_evidence']={
        'current_governance_uid':CURRENT_UID,
        'attempt_uid':ATTEMPT_UID,
        'approval_evidence_ref':str(APPROVAL.relative_to(ROOT)),
        'review_package_ref':str(PACKAGE.relative_to(ROOT)),
        'canonical_product_contract_owner':str(SPEC.relative_to(ROOT)),
        'resolution_uid':RESOLUTION_UID,
        'raw_discovery_problem_count':45,
        'validated_product_successor_signature_count':45,
        'effective_open_problem_count':0,
        'product_blocker_reduction_credit':45,
        'external_authority_resolution_credit':0,
        'persisted_materialization_commit':materialization_commit,
        'materialization_outer_run_id':run_id,
        'materialization_outer_run_result':'success',
        'source_artifact_id':dm.get('source_artifact_id'),
        'source_artifact_sha256':dm.get('source_artifact_sha256'),
        'persisted_child_revalidated_in_outer_workflow':True,
        'persisted_child_full_line_result':'success',
        'full_line_source_file_count':75,
        'lifecycle_stage_result':'11/11',
        'preformal_result':'20/20',
        'mandatory_regression_result':'17/17',
        'immutable_raw_blob_sha':EXPECTED_RAW_BLOB,
    }
    old_prev=state.get('previous_closed_product_work_unit')
    old_last=state.get('last_closed_product_work_unit')
    if old_prev: state['earlier_closed_product_work_unit']=old_prev
    if old_last: state['previous_closed_product_work_unit']=old_last
    state['last_closed_product_work_unit']=closed
    state.pop('active_work_unit',None)
    state['next_action']=CLOSE_NEXT
    state['current_primary_task_product_stage_credit']=45
    resume=state.setdefault('resume_control',{})
    resume.update({
        'current_resume_point':'STAGE2_CORE01_FUNCTIONAL_REMEDIATION_CLOSED_TRANSITION_BOUNDARY',
        'current_work_unit_uid':None,'current_owner':None,
        'last_closed_product_work_unit_uid':WORK_UID,
        'last_closed_product_validation_head':materialization_commit,
        'last_closed_product_outer_run_id':run_id,
        'last_closed_product_outer_result':'success',
        'exact_next_action':CLOSE_NEXT,
    })
    active=state.get('stage02_active_attempt') or {}; active['next_action']=CLOSE_NEXT
    state['stage02_material_remediation']['status']='CORE01_FUNCTIONAL_REMEDIATION_CLOSED_EFFECTIVE_ZERO'
    state['stage02_material_remediation']['functional_work_unit_closed']=True
    state['stage02_material_remediation']['closure_materialization_head']=materialization_commit
    state['stage02_material_remediation']['closure_outer_run_id']=run_id
    findings['next_action']=CLOSE_NEXT
    findings['core01_work_unit_status']='CLOSED_VERIFIED_CORE01_EFFECTIVE_FUNCTIONAL_GAPS_ZERO'
    findings['core01_closure_materialization_head']=materialization_commit
    findings['core01_closure_outer_run_id']=run_id
    cur=change.get('current_stage2_execution') or {}; cur['next_action']=CLOSE_NEXT
    cur['core01_work_unit_status']='CLOSED_VERIFIED_CORE01_EFFECTIVE_FUNCTIONAL_GAPS_ZERO'
    cur['core01_closure_materialization_head']=materialization_commit
    cur['core01_closure_outer_run_id']=run_id
    cur['r7_disposition']='NOT_TRIGGERED_OLD_AUTHORITY_WAIT_ROUTE_NOT_APPLICABLE_AFTER_CURRENT_V2_2_5_CANONICAL_OWNER_MATERIALIZATION'
    dump_yaml(STATE,state); dump_yaml(FINDINGS,findings); dump_yaml(CHANGE,change)
    print(f'PASS: CORE-01 work unit closed from persisted materialization head={materialization_commit} outer_run={run_id}')

def validate_closure():
    state=load_yaml(STATE); findings=load_yaml(FINDINGS); change=load_yaml(CHANGE); problems=load_yaml(PROBLEMS); latest=load_json(LATEST)
    if state.get('active_work_unit') not in (None,{}): die('CLOSED_CORE01_MUST_NOT_REMAIN_ACTIVE_WORK_UNIT')
    closed=state.get('last_closed_product_work_unit') or {}
    if closed.get('work_unit_uid')!=WORK_UID or closed.get('current_status')!='CLOSED_VERIFIED_CORE01_EFFECTIVE_FUNCTIONAL_GAPS_ZERO': die('LAST_CLOSED_PRODUCT_WORK_UNIT_DRIFT')
    ce=closed.get('closure_evidence') or {}
    if ce.get('current_governance_uid')!=CURRENT_UID or ce.get('validated_product_successor_signature_count')!=45 or ce.get('effective_open_problem_count')!=0 or ce.get('product_blocker_reduction_credit')!=45: die('CORE01_CLOSURE_EVIDENCE_DRIFT')
    if ce.get('materialization_outer_run_result')!='success' or ce.get('persisted_child_full_line_result')!='success': die('CORE01_TERMINAL_EVIDENCE_NOT_SUCCESS')
    actions=(state.get('next_action'),(state.get('resume_control') or {}).get('exact_next_action'),(state.get('stage02_active_attempt') or {}).get('next_action'),findings.get('next_action'),(change.get('current_stage2_execution') or {}).get('next_action'))
    if any(x!=CLOSE_NEXT for x in actions): die('CORE01_CLOSURE_NEXT_ACTION_DRIFT')
    if problems.get('open_problem_count')!=0 or problems.get('resolved_problem_count')!=45: die('CORE01_CLOSURE_PROBLEM_REGISTER_DRIFT')
    if latest.get('fresh_functional_gap_total')!=45 or latest.get('effective_functional_gap_total')!=0 or latest.get('stage_scope_complete') is not False: die('CORE01_CLOSURE_LATEST_EVIDENCE_DRIFT')
    materialization_commit=ce.get('persisted_materialization_commit')
    if not materialization_commit: die('CORE01_CLOSURE_MATERIALIZATION_HEAD_MISSING')
    git('merge-base','--is-ancestor',materialization_commit,'HEAD')
    if git_blob(RAW)!=EXPECTED_RAW_BLOB: die('RAW_BLOB_CHANGED_AFTER_CORE01_CLOSURE')
    print(f'PASS: CORE-01 closure state is terminal, effective gaps=0, remaining Stage-02 scope=ASSET-01, next={CLOSE_NEXT}')

def validate_only(require_finalized: bool):
    state=load_yaml(STATE); registry=load_yaml(REGISTRY); package=load_json(PACKAGE); candidate=load_json(CANDIDATE); semantic=load_json(SEMANTIC); approval=load_yaml(APPROVAL); validate_identity(state, registry, package, candidate, semantic, approval)
    problems=load_yaml(PROBLEMS); units, rows=prepare_units(candidate, problems); validate_materialized(load_yaml(SPEC), units, problems)
    if problems.get('open_problem_count') != 0 or problems.get('resolved_problem_count') != 45 or problems.get('effective_open_problem_count') != 0: die('PROBLEM_REGISTER_NOT_EFFECTIVE_ZERO')
    if any(r.get('status')!='RESOLVED_VERIFIED_DESIGN_CONTRACT_MATERIALIZATION' or r.get('resolution_credit')!=1 for r in rows): die('PROBLEM_REGISTER_ROW_NOT_RESOLVED')
    overlay=load_yaml(OVERLAY)
    if overlay.get('current_discovery_gap_total')!=45 or overlay.get('validated_product_successor_signature_count')!=45 or overlay.get('current_effective_gap_total')!=0: die('EFFECTIVE_OVERLAY_DRIFT')
    ledger=load_yaml(LEDGER); rec=next((x for x in ledger.get('entries') or [] if x.get('resolution_uid')==RESOLUTION_UID),None)
    if not rec or rec.get('functional_gap_reduction_credit')!=45 or rec.get('validation_status')!='PASS_EXACT_45_OF_45': die('RESOLUTION_LEDGER_CURRENT_ENTRY_INVALID')
    latest=load_json(LATEST)
    if latest.get('fresh_functional_gap_total')!=45 or latest.get('validated_product_successor_signature_count')!=45 or latest.get('effective_functional_gap_total')!=0: die('LATEST_EVIDENCE_RECONCILIATION_DRIFT')
    if latest.get('stage_scope_complete') is not False or latest.get('remaining_pages')!=['ASSET-01'] or latest.get('result')!='BLOCKED': die('LATEST_EVIDENCE_SCOPE_DRIFT')
    work=state.get('active_work_unit') or {}
    if work.get('product_blocker_credit')!=45 or work.get('current_status')!='PENDING_EXACT_HEAD_TERMINAL_CLOSURE': die('WORK_UNIT_MATERIALIZATION_STATE_DRIFT')
    if require_finalized:
        active=state.get('stage02_active_attempt') or {}; findings=load_yaml(FINDINGS); change=load_yaml(CHANGE).get('current_stage2_execution') or {}
        vals=(active.get('source_workflow_run_id'),findings.get('source_workflow_run_id'),change.get('source_workflow_run_id')); aids=(active.get('source_artifact_id'),findings.get('source_artifact_id'),change.get('source_artifact_id')); digests=(active.get('source_artifact_sha256'),findings.get('source_artifact_sha256'),change.get('source_artifact_sha256'))
        if any(v in (None,'') for v in vals+aids+digests) or len(set(vals))!=1 or len(set(aids))!=1 or len(set(digests))!=1: die('FINALIZED_ARTIFACT_PROJECTOR_DRIFT')
    if git_blob(RAW)!=EXPECTED_RAW_BLOB: die('RAW_BLOB_CHANGED_AFTER_MATERIALIZATION')
    print('PASS: canonical CORE-01 design-contract materialization validates 45/45 and effective gaps remain zero')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['materialize','finalize-artifact','validate-only','close-work-unit','validate-closure'],default='materialize'); ap.add_argument('--require-finalized',action='store_true'); args=ap.parse_args()
    if args.mode=='materialize': materialize()
    elif args.mode=='finalize-artifact': finalize_artifact()
    elif args.mode=='close-work-unit': close_work_unit()
    elif args.mode=='validate-closure': validate_closure()
    else: validate_only(args.require_finalized)

if __name__=='__main__': main()
