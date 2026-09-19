#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import copy, hashlib, importlib.util, json, os, re, sys
import yaml

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
SCOPE=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
HISTORY=ROOT/'governance/test/SELECTED_PROFILE_HISTORY_BINDING.yaml'
CANDIDATES=ROOT/'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
FINDINGS=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
EVIDENCE=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
RUNNER=ROOT/'.github/governance-maintenance/run_fresh_stage_replay.py'
EXACT_CLOSURE_COVERAGE_KEYS=(
    'exact_external_authority',
    'exact_port_state',
    'deterministic_negative_transition_tests',
    'exact_success_signal_wrappers',
    'deterministic_system_triggers',
)

def load_runner():
    spec=importlib.util.spec_from_file_location('acpos_dynamic_fresh_replay_runner',RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError('DYNAMIC_REPLAY_RUNNER_IMPORT_FAILED')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_yaml(p:Path):
    obj=yaml.safe_load(p.read_text(encoding='utf-8'))
    if not isinstance(obj,dict):
        raise RuntimeError(f'MAPPING_REQUIRED:{p}')
    return obj

def dump_yaml(p:Path,obj:dict):
    p.write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

def sha_obj(obj:dict)->str:
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def need_env(name:str)->str:
    v=os.environ.get(name,'').strip()
    if not v:
        raise RuntimeError(f'MISSING_ENV:{name}')
    return v


def _stage02_problem_signature_from_problem(row:dict)->tuple:
    return (str(row.get('page_uid') or ''),str(row.get('class') or ''),str(row.get('category') or ''),str(row.get('target_uid') or ''),str(row.get('detail') or ''),str(row.get('gap_owner') or ''))

def _stage02_problem_signature_from_gap(row:dict)->tuple:
    return (str(row.get('page_uid') or ''),str(row.get('class') or ''),str(row.get('category') or ''),str(row.get('uid') or ''),str(row.get('detail') or ''),str(row.get('gap_owner') or ''))

def _close_current_revalidation_transition(state:dict, current_uid:str, attempt:dict)->dict:
    trans=state.setdefault('governance_revision_transition',{})
    trans['current_governance_uid']=current_uid
    trans['fresh_revalidation_required']=False
    trans['current_product_attempt_uid']=attempt.get('attempt_uid')
    trans['current_product_attempt_run_uid']=attempt.get('run_uid')
    trans['current_product_attempt_workflow_run_id']=attempt.get('source_workflow_run_id')
    trans['current_product_attempt_artifact_id']=attempt.get('source_artifact_id')
    trans['current_product_attempt_artifact_sha256']=attempt.get('source_artifact_sha256')
    return trans

def _stage02_revalidation_reconcile(register:dict, ev:dict, authorized_problem_uids:set[str])->tuple[dict,list[dict]]:
    pages=ev.get('pages') or {}
    target_pages=ev.get('target_pages') or []
    fresh=[]
    for page_uid in target_pages:
        rec=pages.get(page_uid) or {}
        scan=rec.get('functional_chain_fresh_scan') or {}
        fresh.extend(scan.get('gaps') or [])
    if len(fresh)!=int(ev.get('fresh_functional_gap_total') or 0):
        raise RuntimeError('REVALIDATION_FRESH_GAP_DENOMINATOR_DRIFT')
    old_rows=register.get('problems') or []
    by_sig={}
    for row in old_rows:
        sig=_stage02_problem_signature_from_problem(row)
        if sig in by_sig:
            raise RuntimeError(f'DUPLICATE_CURRENT_PROBLEM_SIGNATURE:{sig!r}')
        by_sig[sig]=row
    fresh_sigs=[]
    open_rows=[]
    for gap in fresh:
        sig=_stage02_problem_signature_from_gap(gap)
        if sig in fresh_sigs:
            raise RuntimeError(f'DUPLICATE_FRESH_REVALIDATION_SIGNATURE:{sig!r}')
        fresh_sigs.append(sig)
        prior=by_sig.get(sig)
        if prior is None:
            raise RuntimeError(f'FRESH_REVALIDATION_GAP_NOT_IN_CURRENT_REGISTER:{sig!r}')
        row=copy.deepcopy(prior)
        row['status']='OPEN_FRESH_REVALIDATED_CURRENT_RUN'
        row['resolution_credit']=0
        open_rows.append(row)
    fresh_set=set(fresh_sigs)
    resolved=[copy.deepcopy(row) for sig,row in by_sig.items() if sig not in fresh_set]
    resolved_uids={str(x.get('problem_uid') or '') for x in resolved}
    if resolved_uids!=authorized_problem_uids:
        raise RuntimeError('REVALIDATION_RESOLVED_SET_NOT_AUTHORIZED_MATERIALIZATION:' + f'expected={sorted(authorized_problem_uids)} actual={sorted(resolved_uids)}')
    out=copy.deepcopy(register)
    prior_resolved=int(register.get('resolved_problem_count') or 0)
    out['fresh_physical_problem_count']=len(open_rows)
    out['open_problem_count']=len(open_rows)
    out['resolved_problem_count']=prior_resolved+len(resolved)
    out['problems']=open_rows
    return out,resolved

def _stage02_revalidation_self_test():
    synthetic_page='UNIT-X'
    base_rows=[
      {'problem_uid':'P1','page_uid':synthetic_page,'class':'ARCHITECTURE_GAP','category':'C1','target_uid':'A1','detail':'d1','gap_owner':'PAGE_FUNCTIONAL_CONTRACT','status':'OPEN_FRESH_CURRENT_RUN','resolution_credit':0},
      {'problem_uid':'P2','page_uid':synthetic_page,'class':'ARCHITECTURE_GAP','category':'C2','target_uid':'A2','detail':'d2','gap_owner':'PAGE_FUNCTIONAL_CONTRACT','status':'OPEN_FRESH_CURRENT_RUN','resolution_credit':0},
    ]
    register={'resolved_problem_count':31,'problems':copy.deepcopy(base_rows)}
    ev={'target_pages':[synthetic_page],'fresh_functional_gap_total':1,'pages':{synthetic_page:{'functional_chain_fresh_scan':{'gaps':[
      {'page_uid':synthetic_page,'class':'ARCHITECTURE_GAP','category':'C1','uid':'A1','detail':'d1','gap_owner':'PAGE_FUNCTIONAL_CONTRACT'}
    ]}}}}
    out,resolved=_stage02_revalidation_reconcile(register,ev,{'P2'})
    assert out['open_problem_count']==1 and out['resolved_problem_count']==32
    assert [x['problem_uid'] for x in out['problems']]==['P1']
    assert [x['problem_uid'] for x in resolved]==['P2']
    try:
        _stage02_revalidation_reconcile(register,ev,{'P1'})
    except RuntimeError as exc:
        assert 'REVALIDATION_RESOLVED_SET_NOT_AUTHORIZED_MATERIALIZATION' in str(exc)
    else:
        raise AssertionError('wrong authorized closure set was not rejected')

    extra_register={'resolved_problem_count':31,'problems':copy.deepcopy(base_rows)+[
      {'problem_uid':'P3','page_uid':synthetic_page,'class':'ARCHITECTURE_GAP','category':'C3','target_uid':'A3','detail':'d3','gap_owner':'PAGE_FUNCTIONAL_CONTRACT','status':'OPEN_FRESH_CURRENT_RUN','resolution_credit':0},
    ]}
    try:
        _stage02_revalidation_reconcile(extra_register,ev,{'P2'})
    except RuntimeError as exc:
        assert 'REVALIDATION_RESOLVED_SET_NOT_AUTHORIZED_MATERIALIZATION' in str(exc)
    else:
        raise AssertionError('extra unapproved elimination was not rejected')
    assert 'deterministic_system_triggers' in EXACT_CLOSURE_COVERAGE_KEYS
    assert len(EXACT_CLOSURE_COVERAGE_KEYS)==5
    print('PASS: Stage-02 revalidation exact-closure coverage supports deterministic system-trigger closures')
    synthetic_state={'governance_revision_transition':{'fresh_revalidation_required':True}}
    synthetic_attempt={
      'attempt_uid':'ATTEMPT-X','run_uid':'RUN-X','source_workflow_run_id':123,
      'source_artifact_id':456,'source_artifact_sha256':'a'*64,
    }
    trans=_close_current_revalidation_transition(synthetic_state,'GOV-X',synthetic_attempt)
    assert trans['fresh_revalidation_required'] is False
    assert trans['current_governance_uid']=='GOV-X'
    assert trans['current_product_attempt_uid']=='ATTEMPT-X'
    assert trans['current_product_attempt_run_uid']=='RUN-X'
    assert trans['current_product_attempt_workflow_run_id']==123
    assert trans['current_product_attempt_artifact_id']==456
    assert trans['current_product_attempt_artifact_sha256']=='a'*64
    print('PASS: Stage-02 revalidation transition projector closes Current revalidation atomically')
    print('PASS: Stage-02 revalidation projector accepts exact authorized batch and rejects wrong/extra eliminations')

def _stage02_revalidation_materialization_context(work:dict, page_root:Path)->dict:
    status=str(work.get('current_status') or '')
    if status=='EXACT_CLOSURES_MATERIALIZED_REVALIDATION_REQUIRED':
        coverage=load_yaml(page_root/'REMEDIATION_BLOCKER_COVERAGE.yaml')
        problem_uids=set()
        for key in EXACT_CLOSURE_COVERAGE_KEYS:
            rows=coverage.get(key) or []
            if not isinstance(rows,list):
                raise RuntimeError(f'REVALIDATION_COVERAGE_LIST_REQUIRED:{key}')
            problem_uids.update(str(x) for x in rows)
        materialization=work.get('exact_closure_materialization') or {}
        expected=int(materialization.get('materialized_closure_count') or 0)
        if expected<=0 or len(problem_uids)!=expected:
            raise RuntimeError(f'REVALIDATION_EXACT_CLOSURE_DENOMINATOR_DRIFT:expected={expected}:actual={len(problem_uids)}')
        return {
          'kind':'EXACT_CLOSURE',
          'problem_uids':problem_uids,
          'expected_count':expected,
          'receipt_ref':str(materialization.get('receipt_ref') or ''),
          'prior_product_credit':int(work.get('product_blocker_credit') or 0),
          'remaining_authority_gap_problem_uids':set(),
          'materialization_key':'exact_closure_materialization',
          'coverage':coverage,
        }
    if status=='APPROVED_DESIGN_CONTRACT_MATERIALIZED_REVALIDATION_REQUIRED':
        materialization=work.get('design_contract_materialization') or {}
        problem_uids={str(x) for x in (materialization.get('approved_problem_uids') or []) if str(x)}
        expected=int(materialization.get('approved_problem_count') or 0)
        if expected<=0 or len(problem_uids)!=expected:
            raise RuntimeError(f'REVALIDATION_DESIGN_CONTRACT_DENOMINATOR_DRIFT:expected={expected}:actual={len(problem_uids)}')
        remaining={str(x) for x in (materialization.get('remaining_authority_gap_problem_uids') or []) if str(x)}
        if problem_uids & remaining:
            raise RuntimeError('REVALIDATION_DESIGN_AND_AUTHORITY_GAP_SET_OVERLAP')
        approval_ref=str(materialization.get('approval_evidence_ref') or '')
        if not approval_ref or not (ROOT/approval_ref).is_file():
            raise RuntimeError('REVALIDATION_DESIGN_APPROVAL_EVIDENCE_MISSING')
        return {
          'kind':'APPROVED_DESIGN_CONTRACT',
          'problem_uids':problem_uids,
          'expected_count':expected,
          'receipt_ref':str(materialization.get('receipt_ref') or ''),
          'prior_product_credit':int(materialization.get('prior_product_credit') or work.get('product_blocker_credit') or 0),
          'remaining_authority_gap_problem_uids':remaining,
          'materialization_key':'design_contract_materialization',
          'coverage':load_yaml(page_root/'REMEDIATION_BLOCKER_COVERAGE.yaml'),
        }
    raise RuntimeError(f'REVALIDATION_PRODUCT_WORK_UNIT_STATUS_DRIFT:{status!r}')

def finalize_stage02_revalidation_persistence():
    run_id=need_env('STAGE02_REVALIDATION_RUN_ID')
    source_sha=need_env('STAGE02_REVALIDATION_SOURCE_SHA')
    artifact_id=need_env('STAGE02_REVALIDATION_ARTIFACT_ID')
    digest=need_env('STAGE02_REVALIDATION_ARTIFACT_DIGEST')
    digest=digest.split(':',1)[1] if digest.startswith('sha256:') else digest
    if not re.fullmatch(r'[0-9a-f]{40}',source_sha):
        raise RuntimeError('REVALIDATION_SOURCE_SHA_INVALID')
    if not re.fullmatch(r'[0-9a-fA-F]{64}',digest):
        raise RuntimeError('REVALIDATION_ARTIFACT_DIGEST_NOT_SHA256')
    runtime_path=ROOT/'.github/stage02-test/STAGE02_ACTUAL_TEST_RESULT.json'
    ev=json.loads(runtime_path.read_text(encoding='utf-8'))
    if ev.get('test_mode')!='SAME_ATTEMPT_BOUNDED_REMEDIATION_REVALIDATION':
        raise RuntimeError(f'REVALIDATION_TEST_MODE_REQUIRED:{ev.get("test_mode")!r}')
    if ev.get('source_head_sha')!=source_sha:
        raise RuntimeError('REVALIDATION_SOURCE_SHA_DRIFT')
    if ev.get('actual_product_stage_test_completed') is not True or ev.get('prior_stage2_results_used') is not False:
        raise RuntimeError('REVALIDATION_RUNTIME_EVIDENCE_INCOMPLETE_OR_REUSED')
    if ev.get('current_specification_mutated') is not False or ev.get('ai_autofill_used') is not False or ev.get('inference_used') is not False:
        raise RuntimeError('REVALIDATION_UNSAFE_MUTATION_OR_INFERENCE')

    state=load_yaml(STATE)
    current_uid=state.get('specification_uid')
    work=state.get('active_work_unit') or {}
    if work.get('stage_uid')!='STAGE-02' or work.get('semantic_capability')!='PAGE_FUNCTIONAL_CONTRACT' or work.get('primary_task_layer')!='PRODUCT_STAGE_EXECUTION':
        raise RuntimeError(f'REVALIDATION_PRODUCT_WORK_UNIT_NOT_ACTIVE:{work.get("work_unit_uid")!r}')
    if state.get('current_primary_task_layer')!='PRODUCT_STAGE_EXECUTION':
        raise RuntimeError('REVALIDATION_PRIMARY_TASK_LAYER_DRIFT')

    scope=load_yaml(SCOPE)
    pages=list(scope.get('included_units') or [])
    if len(pages)!=1 or ev.get('target_pages')!=pages:
        raise RuntimeError(f'REVALIDATION_SCOPE_DRIFT:state={pages!r}:evidence={ev.get("target_pages")!r}')
    PAGE=pages[0]
    if not isinstance(PAGE,str) or not PAGE:
        raise RuntimeError('REVALIDATION_PAGE_SCOPE_INVALID')
    owner=str(work.get('canonical_owner') or '')
    marker='/04_PAGE_FUNCTIONAL_CONTRACT/'
    if marker not in owner:
        raise RuntimeError('REVALIDATION_CANONICAL_OWNER_ROOT_UNRESOLVED')
    run_root=owner.split(marker,1)[0]
    product_root=ROOT/run_root/'04_PAGE_FUNCTIONAL_CONTRACT'
    problem_path=product_root/'CURRENT_PROBLEM_REGISTER.yaml'
    denom_path=product_root/'DENOMINATOR_SNAPSHOT.yaml'
    overlay_path=product_root/'EFFECTIVE_CONTRACT_OVERLAY.yaml'
    resolution_path=product_root/'RESOLUTION_LEDGER.yaml'
    page_root=product_root/PAGE

    ctx=_stage02_revalidation_materialization_context(work,page_root)
    authorized_ids=ctx['problem_uids']
    expected_count=ctx['expected_count']
    prior_product_credit=ctx['prior_product_credit']
    batch_kind=ctx['kind']
    coverage=ctx['coverage']

    register=load_yaml(problem_path)
    before_open=int(register.get('open_problem_count') or 0)
    projected,resolved=_stage02_revalidation_reconcile(register,ev,authorized_ids)
    after_open=int(projected.get('open_problem_count') or 0)
    fresh_credit=before_open-after_open
    if fresh_credit!=expected_count or fresh_credit!=len(authorized_ids):
        raise RuntimeError(f'REVALIDATION_FRESH_CREDIT_DRIFT:expected={expected_count}:actual={fresh_credit}')
    if after_open!=int(ev.get('fresh_functional_gap_total') or 0):
        raise RuntimeError('REVALIDATION_PROJECTED_OPEN_COUNT_DRIFT')
    if batch_kind=='APPROVED_DESIGN_CONTRACT':
        actual_remaining={str(x.get('problem_uid') or '') for x in (projected.get('problems') or [])}
        if actual_remaining!=ctx['remaining_authority_gap_problem_uids']:
            raise RuntimeError('REVALIDATION_REMAINING_AUTHORITY_GAP_SET_DRIFT:' + f'expected={sorted(ctx["remaining_authority_gap_problem_uids"])} actual={sorted(actual_remaining)}')

    total_product_credit=prior_product_credit+fresh_credit
    projected['source_problem_count_before_revalidation']=before_open
    projected['last_revalidation']={
      'source_execution_sha':source_sha,
      'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'source_artifact_sha256':digest.lower(),
      'materialization_kind':batch_kind,
      'fresh_elimination_count':fresh_credit,
      'cumulative_product_credit':total_product_credit,
      'closure_blocker_total':int(ev.get('closure_blocker_total') or 0),
      'test_mode':ev.get('test_mode'),
    }
    dump_yaml(problem_path,projected)

    receipt_ref=ctx['receipt_ref']
    if not receipt_ref:
        raise RuntimeError('REVALIDATION_MATERIALIZATION_RECEIPT_REF_MISSING')
    receipt_path=ROOT/receipt_ref
    if not receipt_path.is_file():
        raise RuntimeError('REVALIDATION_MATERIALIZATION_RECEIPT_MISSING')
    receipt=load_yaml(receipt_path)
    count_field='materialized_closure_count' if batch_kind=='EXACT_CLOSURE' else 'approved_problem_count'
    if int(receipt.get(count_field) or 0)!=fresh_credit:
        raise RuntimeError('REVALIDATION_MATERIALIZATION_RECEIPT_DENOMINATOR_DRIFT')
    if receipt.get('status')!='MATERIALIZED_PENDING_FRESH_REVALIDATION':
        raise RuntimeError(f'REVALIDATION_MATERIALIZATION_RECEIPT_STATUS_DRIFT:{receipt.get("status")!r}')
    receipt['status']='MATERIALIZED_FRESH_REVALIDATED'
    receipt['fresh_revalidation_evidence']={
      'source_execution_sha':source_sha,
      'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'source_artifact_sha256':digest.lower(),
      'fresh_functional_gap_total':after_open,
      'fresh_closure_blocker_total':int(ev.get('closure_blocker_total') or 0),
    }
    receipt['product_blocker_credit_after_fresh_revalidation']=fresh_credit
    receipt['cumulative_product_blocker_credit']=total_product_credit
    dump_yaml(receipt_path,receipt)

    materialization=work.get(ctx['materialization_key']) or {}
    materialization['revalidation_status']='FRESH_REVALIDATED'
    materialization['fresh_revalidation_source_sha']=source_sha
    materialization['product_blocker_credit_after_fresh_revalidation']=fresh_credit
    materialization['cumulative_product_blocker_credit']=total_product_credit
    work[ctx['materialization_key']]=materialization

    ledger=load_yaml(resolution_path)
    entries=list(ledger.get('entries') or [])
    existing={str(x.get('source_problem_uid') or '') for x in entries if isinstance(x,dict)}
    if existing & authorized_ids:
        raise RuntimeError('REVALIDATION_RESOLUTION_LEDGER_DUPLICATE_CURRENT_BATCH')
    for row in resolved:
        entries.append({
          'resolution_uid':f'REVALIDATED-{row.get("problem_uid")}',
          'source_problem_uid':row.get('problem_uid'),
          'page_uid':row.get('page_uid'),
          'class':row.get('class'),
          'category':row.get('category'),
          'target_uid':row.get('target_uid'),
          'detail':row.get('detail'),
          'resolution_status':'RESOLVED_FRESH_REVALIDATION',
          'resolution_materialization_kind':batch_kind,
          'resolution_evidence_ref':receipt_ref,
          'source_execution_sha':source_sha,
          'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
          'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
          'product_blocker_credit':1,
        })
    ledger['entries']=entries
    ledger['resolved_problem_count']=len(entries)
    ledger['last_revalidation_source_sha']=source_sha
    dump_yaml(resolution_path,ledger)

    denom=load_yaml(denom_path)
    denom.update({
      'fresh_functional_gap_total':after_open,
      'closure_blocker_total':int(ev.get('closure_blocker_total') or 0),
      'source_problem_count_before_revalidation':before_open,
      'fresh_elimination_count':fresh_credit,
      'cumulative_product_credit':total_product_credit,
      'source_execution_sha':source_sha,
      'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'source_artifact_sha256':digest.lower(),
    })
    dump_yaml(denom_path,denom)

    overlay=load_yaml(overlay_path)
    overlay.update({
      'raw_gap_count':before_open,
      'legal_successor_resolution_count':fresh_credit,
      'effective_open_gap_count':after_open,
      'cumulative_product_credit':total_product_credit,
      'source_execution_sha':source_sha,
    })
    dump_yaml(overlay_path,overlay)

    tracked=copy.deepcopy(ev)
    tracked.update({
      'attempt_uid':state.get('stage02_active_attempt',{}).get('attempt_uid'),
      'frozen_governance_uid':current_uid,
      'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'source_artifact_sha256':digest.lower(),
      'revalidation_materialization_kind':batch_kind,
      'fresh_product_credit':fresh_credit,
      'cumulative_product_credit':total_product_credit,
    })
    EVIDENCE.write_text(json.dumps(tracked,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

    page=(ev.get('pages') or {}).get(PAGE) or {}
    scan=page.get('functional_chain_fresh_scan') or {}
    candidate_path=page_root/'DESIGN_CONTRACT_CANDIDATE.yaml'
    candidate_doc=load_yaml(candidate_path)
    if candidate_doc.get('status')!='REVIEW_ONLY_NON_AUTHORITY_NON_MATERIALIZABLE':
        raise RuntimeError('REVALIDATION_REMAINING_CANDIDATE_STATUS_DRIFT')
    if batch_kind=='EXACT_CLOSURE':
        if int(candidate_doc.get('covered_review_only_problem_count') or -1)!=after_open:
            raise RuntimeError('REVALIDATION_REVIEW_ONLY_CANDIDATE_DENOMINATOR_DRIFT')
        page_token=PAGE.replace('-','')
        next_action=f'REVIEW_{page_token}_STAGE02_REMAINING_REVIEW_ONLY_DESIGN_CONTRACT_CANDIDATE'
        resume_point=f'{page_token}_STAGE2_EXACT_CLOSURES_REVALIDATED_REVIEW_ONLY_PRODUCT_AUTHORITY_REQUIRED'
        work_status='EXACT_CLOSURES_REVALIDATED_REVIEW_ONLY_PRODUCT_AUTHORITY_REQUIRED'
        state_status=f'ACTIVE_{page_token}_STAGE02_REVALIDATED_REVIEW_ONLY_PRODUCT_AUTHORITY_REQUIRED'
    else:
        page_token=PAGE.replace('-','')
        if after_open:
            next_action=f'RESOLVE_{page_token}_STAGE02_REMAINING_PRODUCT_AUTHORITY_SELECTION'
            resume_point=f'{page_token}_STAGE2_APPROVED_DESIGN_CONTRACT_REVALIDATED_AUTHORITY_SELECTION_REQUIRED'
            work_status='APPROVED_DESIGN_CONTRACT_REVALIDATED_AUTHORITY_SELECTION_REQUIRED'
            state_status=f'ACTIVE_{page_token}_STAGE02_APPROVED_DESIGN_CONTRACT_REVALIDATED_AUTHORITY_SELECTION_REQUIRED'
        else:
            next_action=f'VERIFY_{page_token}_STAGE02_TERMINAL_CLOSURE'
            resume_point=f'{page_token}_STAGE2_APPROVED_DESIGN_CONTRACT_REVALIDATED_READY_FOR_TERMINAL_CLOSURE'
            work_status='APPROVED_DESIGN_CONTRACT_REVALIDATED_READY_FOR_TERMINAL_CLOSURE'
            state_status=f'ACTIVE_{page_token}_STAGE02_APPROVED_DESIGN_CONTRACT_REVALIDATED_READY_FOR_TERMINAL_CLOSURE'

    findings=load_yaml(FINDINGS)
    findings.update({
      'governance_uid':current_uid,
      'fresh_functional_gap_total':after_open,
      'closure_blocker_total':int(ev.get('closure_blocker_total') or 0),
      'fresh_closure_blocker_total':int(ev.get('closure_blocker_total') or 0),
      'preserved_external_authority_union_count':int(ev.get('preserved_external_authority_union_count') or 0),
      'official_stage_output_denominator_count':len(ev.get('official_stage_output_denominator') or []),
      'current_manifest_mandatory_stage_output_subset_count':len(ev.get('execution_profile_mandatory_output_subset') or []),
      'gap_classes':scan.get('gap_classes') or {},
      'gap_categories':scan.get('gap_categories') or {},
      'status':'DESIGN_CONTRACT_REMEDIATION_REQUIRED' if ev.get('result')=='BLOCKED' else 'PASS',
      'result':ev.get('result'),
      'source_head_sha':source_sha,
      'source_execution_sha':source_sha,
      'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'source_artifact_sha256':digest.lower(),
      'next_action':next_action,
      'prior_stage2_results_used':False,
      'product_blocker_credit':total_product_credit,
      'fresh_batch_product_credit':fresh_credit,
      'validated_exact_closure_count':int((work.get('exact_closure_materialization') or {}).get('materialized_closure_count') or 0),
      'validated_design_contract_count':fresh_credit if batch_kind=='APPROVED_DESIGN_CONTRACT' else 0,
    })
    dump_yaml(FINDINGS,findings)

    candidates=load_yaml(CANDIDATES)
    cur=candidates.setdefault('current_stage2_execution',{})
    cur.update({
      'state':'TEST_EXECUTED_BLOCKED' if ev.get('result')=='BLOCKED' else 'TEST_EXECUTED_PASS',
      'current_functional_gap_count':after_open,
      'current_closure_blocker_count':int(ev.get('closure_blocker_total') or 0),
      'active_evidence_present':True,
      'active_findings_present':True,
      'stage_exit_allowed':bool(ev.get('stage_exit_allowed')),
      'website_construction_allowed':False,
      'deployment_allowed':False,
      'historical_counts_may_be_treated_as_current':False,
      'source_execution_sha':source_sha,
      'reexecution_cycle':'SAME_ATTEMPT_BOUNDED_REMEDIATION_REVALIDATION',
      'target_pages':pages,
      'remaining_pages':list(ev.get('remaining_pages') or []),
      'stage_scope_complete':bool(ev.get('stage_scope_complete')),
      'next_action':next_action,
      'attempt_uid':findings.get('attempt_uid'),
      'frozen_governance_uid':current_uid,
      'raw_discovery_gap_count':after_open,
      'product_materialization_elimination_count':total_product_credit,
      'fresh_batch_product_materialization_elimination_count':fresh_credit,
      'external_authority_elimination_count':len(coverage.get('exact_external_authority') or []),
      'total_fresh_elimination_count':fresh_credit,
      'preserved_external_authority_union_count':int(ev.get('preserved_external_authority_union_count') or 0),
      'official_stage_output_denominator_count':len(ev.get('official_stage_output_denominator') or []),
      'current_manifest_mandatory_stage_output_subset_count':len(ev.get('execution_profile_mandatory_output_subset') or []),
      'prior_stage2_results_used':False,
      'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'source_artifact_sha256':digest.lower(),
      'product_blocker_reduction_credit':total_product_credit,
      'validated_product_successor_signature_count':total_product_credit,
      'effective_functional_gap_count':after_open,
      'planning_baseline_completeness':ev.get('planning_baseline_completeness'),
      'current_work_unit_status':work_status,
      'fresh_revalidation_required_under_current_governance':False,
      'current_governance_uid':current_uid,
      'closure_credit_under_current_governance':True,
      'execution_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
      'canonical_product_contract_owner_ref':f'{run_root}/04_PAGE_FUNCTIONAL_CONTRACT/{PAGE}/FUNCTIONAL_CHAIN_SPEC.yaml',
    })
    dump_yaml(CANDIDATES,candidates)

    ex=state.setdefault('execution',{})
    s2=ex.setdefault('stage2',{})
    ex['current_stage']='STAGE-02-TESTED-BLOCKED' if ev.get('result')=='BLOCKED' else 'STAGE-02-CLOSED'
    s2.update({
      'result':'TEST_EXECUTED_BLOCKED' if ev.get('result')=='BLOCKED' else 'TEST_EXECUTED_PASS',
      'stage_entry_gate':'PASS',
      'stage_exit_allowed':bool(ev.get('stage_exit_allowed')),
      'artifact_root_present':True,
      'tested_page_uids':pages,
      'remaining_page_uids':list(ev.get('remaining_pages') or []),
      'stage_scope_complete':bool(ev.get('stage_scope_complete')),
      'prior_results_used_in_current_run':False,
      'prior_results_authoritative_for_current_governance':False,
      'revalidation_required_under_current_governance':False,
    })
    ex['website_construction_allowed']=False
    ex['deployment_allowed']=False
    state['execution']=ex
    attempt=state.setdefault('stage02_active_attempt',{})
    attempt.update({
      'frozen_governance_uid':current_uid,
      'source_execution_sha':source_sha,
      'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'source_artifact_sha256':digest.lower(),
      'active_evidence_present':True,
      'active_findings_present':True,
      'fresh_functional_gap_total':after_open,
      'fresh_closure_blocker_total':int(ev.get('closure_blocker_total') or 0),
      'preserved_external_authority_union_count':int(ev.get('preserved_external_authority_union_count') or 0),
      'official_stage_output_denominator_count':len(ev.get('official_stage_output_denominator') or []),
      'current_manifest_mandatory_stage_output_subset_count':len(ev.get('execution_profile_mandatory_output_subset') or []),
      'next_action':next_action,
      'product_blocker_credit':total_product_credit,
      'fresh_batch_product_credit':fresh_credit,
      'prior_results_used':False,
      'fresh_revalidation_required':False,
      'closure_credit_under_current_governance':True,
    })
    state['stage02_active_attempt']=attempt
    state['stage2_result_evidence']={
      'mode':'RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT',
      'static_result_pointer_required':False,
      'static_run_id_copy_forbidden':True,
      'static_head_sha_copy_forbidden':True,
      'static_specification_digest_copy_forbidden':True,
      'tracked_current_evidence_ref':'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
      'artifact_provenance_recorded_in_active_attempt':True,
    }
    state['stage02_material_remediation']={
      'material_remediation_started':True,
      'run_uid':attempt.get('run_uid'),
      'attempt_uid':attempt.get('attempt_uid'),
      'source_problem_denominator':before_open,
      'fresh_revalidated_problem_denominator':after_open,
      'source_closure_blocker_denominator':int(work.get('source_closure_blocker_denominator') or 0),
      'fresh_revalidated_closure_blocker_denominator':int(ev.get('closure_blocker_total') or 0),
      'materialization_kind':batch_kind,
      'fresh_batch_materialized_closure_count':fresh_credit,
      'cumulative_product_blocker_credit':total_product_credit,
      'product_blocker_credit':total_product_credit,
      'status':'APPROVED_DESIGN_CONTRACT_FRESH_REVALIDATED_REMAINING_AUTHORITY_SELECTION' if batch_kind=='APPROVED_DESIGN_CONTRACT' and after_open else ('PRODUCT_REVALIDATED_READY_FOR_TERMINAL_CLOSURE' if after_open==0 else 'EXACT_CLOSURES_FRESH_REVALIDATED_REMAINING_REVIEW_ONLY'),
    }
    state['stage02_revalidation_provenance']={
      'source_execution_sha':source_sha,
      'workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'evidence_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'evidence_artifact_sha256':digest.lower(),
      'test_mode':ev.get('test_mode'),
      'materialization_kind':batch_kind,
      'fresh_functional_gap_total':after_open,
      'fresh_closure_blocker_total':int(ev.get('closure_blocker_total') or 0),
      'fresh_batch_product_credit':fresh_credit,
      'cumulative_product_credit':total_product_credit,
      'status':'CURRENT_SAME_ATTEMPT_REVALIDATION_EVIDENCE_BOUND',
    }
    trans=_close_current_revalidation_transition(state,current_uid,attempt)
    work['current_status']=work_status
    work['source_problem_denominator']=after_open
    work['source_closure_blocker_denominator']=int(ev.get('closure_blocker_total') or 0)
    work['product_blocker_credit']=total_product_credit
    work['fresh_revalidation_evidence']={
      'source_execution_sha':source_sha,
      'source_workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'source_artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'source_artifact_sha256':digest.lower(),
      'materialization_kind':batch_kind,
      'pre_revalidation_problem_denominator':before_open,
      'fresh_problem_denominator':after_open,
      'fresh_closure_blocker_denominator':int(ev.get('closure_blocker_total') or 0),
      'fresh_batch_product_credit':fresh_credit,
      'cumulative_product_credit':total_product_credit,
    }
    state['active_work_unit']=work
    state['current_primary_task_product_stage_credit']=total_product_credit
    state['status']=state_status
    state['next_action']=next_action
    state['resume_control']={
      'current_resume_point':resume_point,
      'current_work_unit_uid':work.get('work_unit_uid'),
      'current_owner':str(candidate_path.relative_to(ROOT)),
      'historical_stage2_results_are_current_state':False,
      'stage2_execution_requires_fresh_entry_resolution':False,
      'exact_next_action':next_action,
    }
    dump_yaml(STATE,state)

    scope['fresh_revalidation_required']=False
    scope['stage_exit_credit_allowed']=bool(ev.get('stage_exit_allowed'))
    scope['denominator_source_refs']=[
      'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
      str(problem_path.relative_to(ROOT)),
    ]
    tmp=copy.deepcopy(scope); tmp.pop('content_hash',None)
    scope['content_hash']=sha_obj(tmp)
    dump_yaml(SCOPE,scope)
    print(json.dumps({
      'result':'PASS',
      'source_execution_sha':source_sha,
      'workflow_run_id':int(run_id) if run_id.isdigit() else run_id,
      'artifact_id':int(artifact_id) if artifact_id.isdigit() else artifact_id,
      'materialization_kind':batch_kind,
      'fresh_functional_gap_total':after_open,
      'fresh_closure_blocker_total':int(ev.get('closure_blocker_total') or 0),
      'fresh_batch_product_credit':fresh_credit,
      'cumulative_product_credit':total_product_credit,
      'next_action':next_action,
    },ensure_ascii=False,indent=2))

def close_stage02_revalidation_persistence_maintenance():
    state=load_yaml(STATE)
    active=state.get('active_work_unit') or {}
    if active.get('primary_task_layer')!='TEST_OR_VALIDATION_MAINTENANCE':
        raise RuntimeError(f'PERSISTENCE_MAINTENANCE_TASK_LAYER_DRIFT:{active.get("primary_task_layer")!r}')
    required_scope={
      'SAME_ATTEMPT_REVALIDATION_ARTIFACT_PROVENANCE_BINDING',
      'CURRENT_PROBLEM_REGISTER_RECONCILIATION',
      'CURRENT_FINDINGS_CANDIDATE_ACTIVE_STATE_PROJECTOR_SYNC',
      'RESOLUTION_LEDGER_EXACT_CLOSURE_PERSISTENCE',
      'ATOMIC_CURRENT_STATE_COMMIT',
    }
    if set(active.get('scope') or [])!=required_scope:
        raise RuntimeError(f'PERSISTENCE_MAINTENANCE_SCOPE_DRIFT:{active.get("scope")!r}')
    if int(active.get('product_stage_credit') or 0)!=0:
        raise RuntimeError('PERSISTENCE_MAINTENANCE_PRODUCT_CREDIT_MUST_BE_ZERO')
    parent_uid=str(active.get('parent_product_work_unit_uid') or '')
    if not parent_uid:
        raise RuntimeError('PERSISTENCE_MAINTENANCE_PARENT_WORK_UNIT_MISSING')

    matches=[]
    for key,value in state.items():
        if not isinstance(value,dict):
            continue
        if value.get('work_unit_uid')==parent_uid and value.get('primary_task_layer')=='PRODUCT_STAGE_EXECUTION':
            matches.append((key,value))
    if len(matches)!=1:
        raise RuntimeError(f'PERSISTENCE_MAINTENANCE_PARENT_RESOLUTION_AMBIGUOUS:{[x[0] for x in matches]!r}')
    parent_key,parent=matches[0]
    if parent.get('current_status')!='SUSPENDED_FOR_STAGE02_REVALIDATION_PERSISTENCE_MAINTENANCE':
        raise RuntimeError(f'PERSISTENCE_MAINTENANCE_PARENT_STATUS_DRIFT:{parent.get("current_status")!r}')

    resume=state.get('resume_control') or {}
    if resume.get('parent_work_unit_uid')!=parent_uid:
        raise RuntimeError('PERSISTENCE_MAINTENANCE_PARENT_RESUME_UID_DRIFT')
    parent_resume=str(resume.get('parent_resume_point') or '')
    parent_next=str(resume.get('parent_exact_next_action') or '')
    parent_layer=str(resume.get('parent_primary_task_layer') or '')
    if not parent_resume or not parent_next or parent_layer!='PRODUCT_STAGE_EXECUTION':
        raise RuntimeError('PERSISTENCE_MAINTENANCE_PARENT_RESUME_INCOMPLETE')

    validated_head=need_env('MAINTENANCE_VALIDATED_HEAD')
    if not re.fullmatch(r'[0-9a-f]{40}',validated_head):
        raise RuntimeError('MAINTENANCE_VALIDATED_HEAD_INVALID')
    run_fields={}
    for env_name,out_name in (
      ('MAINTENANCE_FULL_LINE_RUN_ID','full_line_run_id'),
      ('MAINTENANCE_SELECTED_PROFILE_RUN_ID','selected_profile_run_id'),
      ('MAINTENANCE_BRANCH_GUARD_RUN_ID','branch_guard_run_id'),
      ('MAINTENANCE_STAGE02_REGRESSION_RUN_ID','stage02_regression_run_id'),
    ):
        raw=need_env(env_name)
        if not raw.isdigit():
            raise RuntimeError(f'MAINTENANCE_RUN_ID_INVALID:{env_name}')
        run_fields[out_name]=int(raw)

    evidence={
      'validated_head_sha':validated_head,
      **run_fields,
      'outer_terminal_conclusions':['SUCCESS','SUCCESS','SUCCESS','SUCCESS'],
      'maintenance_product_stage_credit':0,
      'current_specification_mutated':False,
      'product_contract_content_mutated':False,
      'legal_next_transition':parent_next,
    }
    closed=copy.deepcopy(active)
    closed['current_status']='CLOSED_VERIFIED_NO_PRODUCT_CREDIT'
    closed['terminal_evidence']=copy.deepcopy(evidence)
    closed['product_stage_credit']=0

    closed_key='closed_test_validation_maintenance_work_unit_stage02_revalidation_persistence'
    if closed_key in state:
        raise RuntimeError('PERSISTENCE_MAINTENANCE_CLOSURE_ALREADY_PRESENT')
    del state[parent_key]
    state[closed_key]=closed

    parent=copy.deepcopy(parent)
    parent['current_status']='EXACT_CLOSURES_MATERIALIZED_REVALIDATION_REQUIRED'
    parent['product_blocker_credit']=int(parent.get('product_blocker_credit') or 0)
    if parent['product_blocker_credit']!=0:
        raise RuntimeError('PERSISTENCE_MAINTENANCE_PARENT_PRODUCT_CREDIT_CHANGED_BEFORE_FRESH_REVALIDATION')
    parent['restoration_after_revalidation_persistence_maintenance']=copy.deepcopy(evidence)
    state['active_work_unit']=parent
    state['current_primary_task_layer']='PRODUCT_STAGE_EXECUTION'
    state['current_primary_task_product_stage_credit']=0
    if '_STAGE2_' not in parent_resume:
        raise RuntimeError(f'PERSISTENCE_MAINTENANCE_PARENT_RESUME_FORMAT_UNSUPPORTED:{parent_resume!r}')
    state['status']='ACTIVE_'+parent_resume.replace('_STAGE2_','_STAGE02_')
    state['next_action']=parent_next
    owner=(parent.get('exact_closure_materialization') or {}).get('canonical_successor_ref') or parent.get('canonical_owner')
    if not owner:
        raise RuntimeError('PERSISTENCE_MAINTENANCE_PARENT_OWNER_MISSING')
    state['resume_control']={
      'current_resume_point':parent_resume,
      'current_work_unit_uid':parent_uid,
      'current_owner':owner,
      'historical_stage2_results_are_current_state':False,
      'stage2_execution_requires_fresh_entry_resolution':False,
      'exact_next_action':parent_next,
    }
    state['stage02_revalidation_persistence_maintenance_closure']={
      'work_unit_uid':closed.get('work_unit_uid'),
      'status':'CLOSED_VERIFIED_NO_PRODUCT_CREDIT',
      **copy.deepcopy(evidence),
    }
    dump_yaml(STATE,state)
    print(json.dumps({
      'result':'PASS',
      'closed_work_unit_uid':closed.get('work_unit_uid'),
      'restored_product_work_unit_uid':parent_uid,
      'restored_resume_point':parent_resume,
      'restored_next_action':parent_next,
      'product_stage_credit':0,
      'validated_head_sha':validated_head,
    },ensure_ascii=False,indent=2))

def main():
    if '--close-stage02-revalidation-persistence-maintenance' in sys.argv:
        close_stage02_revalidation_persistence_maintenance()
        return
    if '--stage02-revalidation-self-test' in sys.argv:
        _stage02_revalidation_self_test()
        return
    if '--stage02-revalidation' in sys.argv:
        finalize_stage02_revalidation_persistence()
        return
    runner=load_runner()
    if '--identity-self-test' in sys.argv:
        runner.identity_self_test()
        print(json.dumps({'result':'PASS','finalizer_dynamic_context_import':True},indent=2))
        return
    ctx=runner.resolve_execution_context()
    CURRENT_UID=ctx['governance_uid']
    DISPLAY_VERSION=ctx['display_version']
    RUN_UID=ctx['run_uid']
    PAGE=ctx['page_scope'][0]
    ATTEMPT_UID=ctx['attempt_uid']
    RUN_ROOT=ctx['run_root']
    EXCLUDED_UNITS=list(ctx['excluded_page_scope'])
    run_id=need_env('FRESH_REPLAY_RUN_ID')
    source_sha=need_env('FRESH_REPLAY_SOURCE_SHA')
    artifact_id=need_env('FRESH_EVIDENCE_ARTIFACT_ID')
    digest=need_env('FRESH_EVIDENCE_ARTIFACT_DIGEST')
    digest=digest.split(':',1)[1] if digest.startswith('sha256:') else digest
    if not re.fullmatch(r'[0-9a-fA-F]{64}',digest):
        raise RuntimeError('ARTIFACT_DIGEST_NOT_SHA256')
    if not re.fullmatch(r'[0-9a-f]{40}',source_sha):
        raise RuntimeError('SOURCE_SHA_INVALID')

    state=load_yaml(STATE)
    if state.get('specification_uid')!=CURRENT_UID:
        raise RuntimeError('CURRENT_GOVERNANCE_UID_DRIFT')
    ex=state.get('execution') or {}
    if ex.get('run_uid')!=RUN_UID or ex.get('target_pages')!=[PAGE]:
        raise RuntimeError('FRESH_RUN_IDENTITY_DRIFT')
    s2=ex.get('stage2') or {}
    if s2.get('result') not in {'TEST_EXECUTED_BLOCKED','TEST_EXECUTED_PASS'}:
        raise RuntimeError('STAGE02_RESULT_NOT_EXECUTED')
    if s2.get('prior_results_used_in_current_run') is not False:
        raise RuntimeError('PRIOR_STAGE02_REUSE_DETECTED')

    attempt=state.get('stage02_active_attempt') or {}
    if attempt.get('attempt_uid')!=ATTEMPT_UID or attempt.get('run_uid')!=RUN_UID:
        raise RuntimeError('ACTIVE_ATTEMPT_IDENTITY_DRIFT')
    if attempt.get('frozen_governance_uid')!=CURRENT_UID:
        raise RuntimeError('ACTIVE_ATTEMPT_GOVERNANCE_DRIFT')

    ev=json.loads(EVIDENCE.read_text(encoding='utf-8'))
    if ev.get('target_pages')!=[PAGE] or ev.get('prior_stage2_results_used') is not False:
        raise RuntimeError('EVIDENCE_SCOPE_OR_REUSE_DRIFT')

    attempt['source_execution_sha']=source_sha
    attempt['source_workflow_run_id']=int(run_id) if run_id.isdigit() else run_id
    attempt['source_artifact_id']=int(artifact_id) if artifact_id.isdigit() else artifact_id
    attempt['source_artifact_sha256']=digest.lower()
    attempt['active_evidence_present']=True
    attempt['active_findings_present']=True
    attempt['fresh_revalidation_required']=False
    attempt['closure_credit_under_current_governance']=True
    attempt['fresh_functional_gap_total']=int(ev.get('fresh_functional_gap_total') or 0)
    attempt['fresh_closure_blocker_total']=int(ev.get('closure_blocker_total') or 0)
    attempt['preserved_external_authority_union_count']=int(ev.get('preserved_external_authority_union_count') or 0)
    attempt['official_stage_output_denominator_count']=len(ev.get('official_stage_output_denominator') or [])
    attempt['current_manifest_mandatory_stage_output_subset_count']=len(ev.get('execution_profile_mandatory_output_subset') or [])
    attempt['next_action']=state.get('next_action')
    state['stage02_active_attempt']=attempt
    state['stage2_result_evidence']={
      'mode':'RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT',
      'static_result_pointer_required':False,
      'static_run_id_copy_forbidden':True,
      'static_head_sha_copy_forbidden':True,
      'static_specification_digest_copy_forbidden':True,
      'tracked_current_evidence_ref':'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json',
      'artifact_provenance_recorded_in_active_attempt':True,
    }
    state['stage02_material_remediation']={
      'material_remediation_started':bool(s2.get('artifact_root_present')),
      'run_uid':RUN_UID,'attempt_uid':ATTEMPT_UID,
      'source_problem_denominator':attempt['fresh_functional_gap_total'],
      'source_closure_blocker_denominator':attempt['fresh_closure_blocker_total'],
      'product_blocker_credit':0,
      'status':'CURRENT_FRESH_PRODUCT_ROOT_PROVENANCE_BOUND',
    }

    profile=state.setdefault('selected_execution_profile_state',{})
    profile['active_attempt_state_key']='stage02_active_attempt'

    trans=_close_current_revalidation_transition(state,CURRENT_UID,attempt)
    trans['predecessor_attempt_preserved_as_historical_evidence']=True
    trans['predecessor_attempt_may_close_under_current_governance']=False

    s2['prior_results_authoritative_for_current_governance']=False
    s2['revalidation_required_under_current_governance']=False
    ex['stage2']=s2
    state['execution']=ex

    state['fresh_replay_provenance']={
      'run_uid':RUN_UID,
      'page_scope':[PAGE],
      'workflow_run_id':attempt['source_workflow_run_id'],
      'source_execution_sha':source_sha,
      'evidence_artifact_id':attempt['source_artifact_id'],
      'evidence_artifact_sha256':attempt['source_artifact_sha256'],
      'prior_stage01_stage02_product_outputs_reused':False,
      'excluded_unit_generated_data_present':{uid:False for uid in EXCLUDED_UNITS},
      'product_blocker_credit':0,
      'status':'CURRENT_FRESH_STAGE01_STAGE02_EXECUTION_EVIDENCE_BOUND',
    }
    replay_ctx=state.get('fresh_replay_execution_context') or {}
    if replay_ctx.get('run_uid')!=RUN_UID or replay_ctx.get('status')!='READY_FOR_REPLAY':
        raise RuntimeError('FRESH_REPLAY_CONTEXT_CONSUMPTION_DRIFT')
    replay_ctx['status']='CONSUMED'
    replay_ctx['consumed_by_workflow_run_id']=attempt['source_workflow_run_id']
    replay_ctx['consumed_source_sha']=source_sha
    replay_ctx['evidence_artifact_id']=attempt['source_artifact_id']
    replay_ctx['evidence_artifact_sha256']=attempt['source_artifact_sha256']
    state['fresh_replay_execution_context']=replay_ctx
    dump_yaml(STATE,state)

    scope=load_yaml(SCOPE)
    if scope.get('included_units')!=[PAGE] or scope.get('excluded_units')!=EXCLUDED_UNITS:
        raise RuntimeError('EXECUTION_SCOPE_DRIFT')
    scope['fresh_revalidation_required']=False
    scope['stage_exit_credit_allowed']=bool(s2.get('stage_exit_allowed'))
    tmp=copy.deepcopy(scope)
    tmp.pop('content_hash',None)
    scope['content_hash']=sha_obj(tmp)
    dump_yaml(SCOPE,scope)

    history=load_yaml(HISTORY)
    history['status']='ACTIVE_PROFILE_HISTORY_EVIDENCE_BINDING'
    history['scope']={
      PAGE:{
        'expected_result':'PASS',
        'artifacts':[
          {'artifact_ref':f'{RUN_ROOT}/02_BASE_BLUEPRINT/{PAGE}/PAGE_BASE_BLUEPRINT.yaml','creation_governance_overlay':DISPLAY_VERSION},
          {'artifact_ref':f'{RUN_ROOT}/02_BASE_BLUEPRINT/{PAGE}/VISUAL_BASE_BLUEPRINT.yaml','creation_governance_overlay':DISPLAY_VERSION},
          {'artifact_ref':f'{RUN_ROOT}/03_BLUEPRINT_BINDING/{PAGE}/BLUEPRINT_BINDING_MANIFEST.yaml','creation_governance_overlay':DISPLAY_VERSION},
        ],
        'profile_step_uid':'STAGE-01',
      }
    }
    history['current_scope_binding']={
      'run_uid':RUN_UID,
      'page_scope':[PAGE],
      'excluded_page_scope':EXCLUDED_UNITS,
      'prior_product_artifact_reuse':False,
      'binding_reason':'FRESH_STAGE01_REPLAY_CURRENT_SCOPE',
    }
    dump_yaml(HISTORY,history)

    candidates=load_yaml(CANDIDATES)
    candidates['current_stage2_execution']={
      'state':s2.get('result'),
      'current_functional_gap_count':attempt.get('fresh_functional_gap_total'),
      'current_closure_blocker_count':attempt.get('fresh_closure_blocker_total'),
      'active_evidence_present':True,
      'active_findings_present':True,
      'stage_exit_allowed':bool(s2.get('stage_exit_allowed')),
      'website_construction_allowed':False,
      'deployment_allowed':False,
      'historical_counts_may_be_treated_as_current':False,
      'source_execution_sha':source_sha,
      'reexecution_cycle':RUN_UID,
      'target_pages':[PAGE],
      'remaining_pages':[],
      'stage_scope_complete':True,
      'next_action':state.get('next_action'),
      'attempt_uid':ATTEMPT_UID,
      'frozen_governance_uid':CURRENT_UID,
      'raw_discovery_gap_count':attempt.get('fresh_functional_gap_total'),
      'product_materialization_elimination_count':0,
      'external_authority_elimination_count':0,
      'total_fresh_elimination_count':0,
      'preserved_external_authority_union_count':ev.get('preserved_external_authority_union_count'),
      'official_stage_output_denominator_count':len(ev.get('official_stage_output_denominator') or []),
      'current_manifest_mandatory_stage_output_subset_count':len(ev.get('execution_profile_mandatory_output_subset') or []),
      'prior_stage2_results_used':False,
      'source_workflow_run_id':attempt['source_workflow_run_id'],
      'source_artifact_id':attempt['source_artifact_id'],
      'source_artifact_sha256':attempt['source_artifact_sha256'],
      'product_blocker_reduction_credit':0,
      'validated_product_successor_signature_count':0,
      'effective_functional_gap_count':attempt.get('fresh_functional_gap_total'),
      'planning_baseline_completeness':ev.get('planning_baseline_completeness'),
      'current_work_unit_status':'DESIGN_CONTRACT_REMEDIATION_REQUIRED' if attempt.get('fresh_functional_gap_total') else 'READY_FOR_TERMINAL_CLOSURE',
      'fresh_revalidation_required_under_current_governance':False,
      'current_governance_uid':CURRENT_UID,
      'closure_credit_under_current_governance':True,
      'execution_scope_manifest_ref':'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml',
      'canonical_product_contract_owner_ref':f'{RUN_ROOT}/04_PAGE_FUNCTIONAL_CONTRACT/{PAGE}/FUNCTIONAL_CHAIN_SPEC.yaml',
    }
    dump_yaml(CANDIDATES,candidates)

    findings=load_yaml(FINDINGS)
    findings['attempt_uid']=ATTEMPT_UID
    findings['run_uid']=RUN_UID
    findings['governance_uid']=CURRENT_UID
    findings['frozen_governance_uid']=CURRENT_UID
    findings['source_execution_sha']=source_sha
    findings['source_head_sha']=source_sha
    findings['source_workflow_run_id']=attempt['source_workflow_run_id']
    findings['source_artifact_id']=attempt['source_artifact_id']
    findings['source_artifact_sha256']=attempt['source_artifact_sha256']
    findings['fresh_functional_gap_total']=attempt.get('fresh_functional_gap_total')
    findings['closure_blocker_total']=attempt.get('fresh_closure_blocker_total')
    findings['fresh_closure_blocker_total']=attempt.get('fresh_closure_blocker_total')
    findings['preserved_external_authority_union_count']=attempt.get('preserved_external_authority_union_count')
    findings['official_stage_output_denominator_count']=attempt.get('official_stage_output_denominator_count')
    findings['current_manifest_mandatory_stage_output_subset_count']=attempt.get('current_manifest_mandatory_stage_output_subset_count')
    findings['next_action']=state.get('next_action')
    findings['result']='BLOCKED' if s2.get('result') == 'TEST_EXECUTED_BLOCKED' else 'PASS'
    findings['prior_stage2_results_used']=False
    findings['product_blocker_credit']=0
    dump_yaml(FINDINGS,findings)

    print(json.dumps({
      'run_uid':RUN_UID,
      'attempt_uid':ATTEMPT_UID,
      'workflow_run_id':attempt['source_workflow_run_id'],
      'artifact_id':attempt['source_artifact_id'],
      'artifact_sha256':attempt['source_artifact_sha256'],
      'stage2_result':s2.get('result'),
      'planning_baseline_completeness':ev.get('planning_baseline_completeness'),
      'fresh_revalidation_required':False,
      'closure_credit_under_current_governance':True,
      'product_blocker_credit':0,
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
