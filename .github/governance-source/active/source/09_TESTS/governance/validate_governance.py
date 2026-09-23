#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,sys,yaml,re,importlib.util,subprocess,os,concurrent.futures
from collections import defaultdict
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]

def load_yaml(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def hobj(d):
    x=dict(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=160).encode()).hexdigest()
def import_local(name):
    p=Path(__file__).resolve().parent/f'{name}.py'; spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def parser_hygiene(root):
    failures=[]; counts={'yaml':0,'json':0,'python':0}
    forbidden_parts={'__pycache__','.next','dist','build','coverage','playwright-report','test-results','node_modules'}; forbidden_suffix={'.pyc','.pyo','.tmp','.bak','.swp'}
    for p in root.rglob('*'):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        if any(x in forbidden_parts for x in p.parts) or p.suffix in forbidden_suffix or p.name.endswith('~'): failures.append('garbage:'+rel)
        try:
            if p.suffix in ('.yaml','.yml'): counts['yaml']+=1; yaml.safe_load(p.read_text(encoding='utf-8'))
            elif p.suffix=='.json': counts['json']+=1; json.loads(p.read_text(encoding='utf-8'))
            elif p.suffix=='.py': counts['python']+=1; compile(p.read_text(encoding='utf-8'),str(p),'exec')
        except Exception as e: failures.append(f'parse_error:{rel}:{e}')
    return {'status':'PASS' if not failures else 'FAIL','counts':counts,'failures':failures}

def baseline_guard(root):
    failures=[]; bp=root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'; cat=root/'10_REGISTRY/AUDIT_CATALOG.yaml'; sec=root/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'; base=root/'11_EVIDENCE/audit/AUDIT_BASELINE.yaml'
    for p in (bp,cat,sec,base):
        if not p.exists(): failures.append('missing:'+p.relative_to(root).as_posix())
    if failures: return {'status':'FAIL','failures':failures}
    bpd,catd,secd,bd=map(load_yaml,(bp,cat,sec,base))
    cf=bd.get('compiled_from') or {}
    if cf.get('acceptance_blueprint_uid')!=bpd.get('artifact_uid') or cf.get('acceptance_blueprint_sha256')!=sha(bp): failures.append('baseline_acceptance_blueprint_binding_stale')
    if cf.get('audit_catalog_uid')!=catd.get('artifact_uid') or cf.get('audit_catalog_sha256')!=sha(cat): failures.append('baseline_audit_catalog_binding_stale')
    if cf.get('section_registry_uid') not in (secd.get('artifact_uid'),secd.get('registry_uid')) or cf.get('section_registry_sha256')!=sha(sec): failures.append('baseline_section_registry_binding_stale')
    cat_uids=[x.get('audit_item_uid') for x in catd.get('items') or []]
    if bd.get('denominator',{}).get('audit_item_uids')!=cat_uids: failures.append('baseline_denominator_mismatch')
    if bd.get('content_hash')!=hobj(bd): failures.append('baseline_content_hash_mismatch')
    from governance_common import extract_requirements
    reqs,sources=extract_requirements(root)
    srcmap={x['document_id']:x for x in bd.get('governance_compilation',{}).get('sources') or []}
    for s in sources:
        if not srcmap.get(s['document_id']) or srcmap[s['document_id']].get('sha256')!=s.get('sha256'): failures.append('baseline_normative_source_stale:'+s['document_id'])
    current={(r['source'],r['line'],r['modality'],r['clause_hash']) for r in reqs}
    compiled={(r.get('src'),r.get('line'),r.get('mode'),r.get('hash')) for r in bd.get('governance_compilation',{}).get('requirements') or []}
    if current!=compiled: failures.append(f'baseline_requirement_compilation_mismatch:missing={len(current-compiled)}:extra={len(compiled-current)}')
    return {'status':'PASS' if not failures else 'FAIL','compiled_requirements':len(compiled),'audit_denominator':len(cat_uids),'failures':failures}

def root_manifest_guard(root):
    failures=[]; p=root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'; pp=root/'10_REGISTRY/PROTECTED_CURRENT_ARTIFACT_REGISTRY.yaml'; bp=root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    if not p.exists(): return {'status':'FAIL','failures':['root_manifest_missing']}
    if not pp.exists(): return {'status':'FAIL','failures':['protected_registry_missing']}
    if not bp.exists(): return {'status':'FAIL','failures':['semantic_authority_baseline_missing']}
    d=load_yaml(p); protected=load_yaml(pp); baseline=load_yaml(bp); seen=set()
    for group in ('current_artifacts','validators'):
        for rec in d.get(group) or []:
            rel=rec.get('path')
            if not rel or rel in seen: failures.append('duplicate_or_missing_manifest_path:'+str(rel)); continue
            seen.add(rel); fp=root/rel
            if not fp.exists(): failures.append('manifest_target_missing:'+rel); continue
            if rel=='10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml':
                if rec.get('sha256')!='SELF_EXCLUDED': failures.append('root_manifest_self_hash_policy_invalid')
            elif rec.get('sha256')!=sha(fp): failures.append('manifest_hash_stale:'+rel)
    expected=set(baseline.get('required_root_manifest_paths') or [])
    protected_set={x.get('path') for x in protected.get('protected_paths') or [] if x.get('path')}
    if seen!=expected: failures.append('root_manifest_required_set_mismatch:missing='+str(sorted(expected-seen))+':extra='+str(sorted(seen-expected)))
    if protected_set!=expected: failures.append('protected_current_required_set_mismatch:missing='+str(sorted(expected-protected_set))+':extra='+str(sorted(protected_set-expected)))
    return {'status':'PASS' if not failures else 'FAIL','manifest_entries':len(seen),'required_entries':len(expected),'failures':failures}

def checksum_guard(root):
    failures=[]; cp=root/'CHECKSUMS.sha256'
    if not cp.exists(): return {'status':'FAIL','failures':['checksums_missing']}
    entries={}
    for line in cp.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        parts=line.split(None,1)
        if len(parts)!=2: failures.append('checksum_line_invalid:'+line); continue
        digest,rel=parts; rel=rel.strip()
        if rel.startswith('./'): rel=rel[2:]
        if rel in entries: failures.append('checksum_duplicate_path:'+rel)
        entries[rel]=digest
    actual=set()
    forbidden_parts={'__pycache__','.next','dist','build','coverage','playwright-report','test-results','node_modules'}
    forbidden_suffix={'.pyc','.pyo','.tmp','.bak','.swp'}
    for fp in root.rglob('*'):
        if not fp.is_file(): continue
        rel=fp.relative_to(root).as_posix()
        if rel=='CHECKSUMS.sha256': continue
        if any(x in fp.parts for x in forbidden_parts) or fp.suffix in forbidden_suffix or fp.name.endswith('~'): continue
        actual.add(rel)
    if set(entries)!=actual: failures.append('checksum_coverage_mismatch:missing='+str(sorted(actual-set(entries)))+':extra='+str(sorted(set(entries)-actual)))
    for rel,digest in entries.items():
        fp=root/rel
        if not fp.exists(): failures.append('checksum_target_missing:'+rel)
        elif sha(fp)!=digest: failures.append('checksum_digest_mismatch:'+rel)
    return {'status':'PASS' if not failures else 'FAIL','entries':len(entries),'failures':failures}

def external_trust_anchor_guard(root):
    failures=[]
    trust_path=os.environ.get('WEB_GOVERNANCE_TRUST_ROOT')
    if not trust_path: return {'status':'FAIL','failures':['external_trust_root_env_missing:WEB_GOVERNANCE_TRUST_ROOT']}
    tp=Path(trust_path)
    if not tp.exists() or not tp.is_file(): return {'status':'FAIL','failures':['external_trust_root_missing:'+str(tp)]}
    try: d=json.loads(tp.read_text(encoding='utf-8'))
    except Exception as e: return {'status':'FAIL','failures':['external_trust_root_parse_error:'+repr(e)]}
    if d.get('schema_version')!=1: failures.append('external_trust_root_schema_invalid')
    if d.get('trust_model')!='EXTERNAL_IMMUTABLE_PACKAGE_HASH_SET': failures.append('external_trust_model_invalid')
    raw_expected=d.get('package_files') or []
    if isinstance(raw_expected, list):
        expected={}
        for rec in raw_expected:
            if not isinstance(rec, dict) or not rec.get('path') or not rec.get('sha256'):
                failures.append('external_trust_package_file_record_invalid')
                continue
            if rec['path'] in expected:
                failures.append('external_trust_duplicate_path:'+rec['path'])
            expected[rec['path']]=rec['sha256']
    elif isinstance(raw_expected, dict):
        expected=dict(raw_expected)
    else:
        expected={}
        failures.append('external_trust_package_files_invalid_type')
    actual={}
    forbidden_parts={'__pycache__','.next','dist','build','coverage','playwright-report','test-results','node_modules'}
    forbidden_suffix={'.pyc','.pyo','.tmp','.bak','.swp'}
    for fp in root.rglob('*'):
        if not fp.is_file(): continue
        if any(x in fp.parts for x in forbidden_parts) or fp.suffix in forbidden_suffix or fp.name.endswith('~'): continue
        rel=fp.relative_to(root).as_posix(); actual[rel]=sha(fp)
    if set(actual)!=set(expected): failures.append('external_trust_file_set_mismatch:missing='+str(sorted(set(expected)-set(actual)))+':extra='+str(sorted(set(actual)-set(expected))))
    for rel,digest in expected.items():
        if actual.get(rel)!=digest: failures.append('external_trust_hash_mismatch:'+rel)
    sem=load_yaml(root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml') if (root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml').exists() else {}
    if d.get('semantic_authority_content_hash')!=sem.get('content_hash'): failures.append('external_trust_semantic_anchor_mismatch')
    return {'status':'PASS' if not failures else 'FAIL','trust_root':str(tp),'files_verified':len(expected),'failures':failures}

def mandatory_regression_guard(root):
    # Child preformal calls made by destructive regression suites must not recursively execute the full suite matrix.
    if os.environ.get('WEB_GOVERNANCE_PREFORMAL_SUITE_CHILD')=='1':
        c=checksum_guard(root)
        return {'status':c.get('status'),'nested_suite_execution_skipped':True,'checksum_entries':c.get('entries'),'failures':['package_integrity:'+x for x in c.get('failures',[])]}
    failures=[]; gov=root/'09_TESTS/governance'; env=dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPYCACHEPREFIX']='/tmp/web-governance-no-pycache'; env['WEB_GOVERNANCE_PREFORMAL_SUITE_CHILD']='1'
    baseline=load_yaml(root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')
    specs=baseline.get('mandatory_regression_assets') or []
    results=[]
    def execute(spec):
        name=Path(spec.get('path','')).name; p=root/spec.get('path','')
        rec={'suite':name}
        if not p.exists(): rec['failure']='asset_missing'; return rec
        try:
            cp=subprocess.run([sys.executable,str(p)],cwd=str(gov),env=env,capture_output=True,text=True,timeout=240)
            rec['returncode']=cp.returncode
            try: parsed=json.loads(cp.stdout)
            except Exception as e: rec['failure']='invalid_json_output:'+repr(e); rec['stdout_tail']=cp.stdout[-1000:]; return rec
            rec['parsed']=parsed
            ok=cp.returncode==0
            if 'expected_total' in spec:
                ok=ok and parsed.get('total')==spec.get('expected_total') and parsed.get('passed_expectations')==spec.get('expected_passed')
            else:
                ok=ok and parsed.get('semantic_cases_total')==spec.get('expected_semantic_total') and parsed.get('semantic_passed_expectations')==spec.get('expected_semantic_passed') and parsed.get('fuzz_total')==spec.get('expected_fuzz_total') and parsed.get('fuzz_blocked')==spec.get('expected_fuzz_blocked') and parsed.get('escaped')==spec.get('expected_escaped')
            rec['ok']=bool(ok)
            if not ok: rec['failure']='denominator_or_expectation_mismatch'
            return rec
        except Exception as e:
            rec['failure']='exception:'+repr(e); rec['ok']=False; return rec
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(2,max(1,len(specs)))) as ex:
        futs=[ex.submit(execute,spec) for spec in specs]
        for fut in futs: results.append(fut.result())
    for r in results:
        if not r.get('ok'): failures.append('mandatory_regression_failed:'+r.get('suite','<unknown>')+':'+str(r.get('failure')))
    c=checksum_guard(root)
    if c.get('status')!='PASS': failures.extend('package_integrity:'+x for x in c.get('failures',[]))
    compact=[]
    for r in results:
        parsed=r.get('parsed') or {}
        compact.append({'suite':r.get('suite'),'returncode':r.get('returncode'),'ok':r.get('ok'),'total':parsed.get('total'),'passed_expectations':parsed.get('passed_expectations'),'semantic_cases_total':parsed.get('semantic_cases_total'),'semantic_passed_expectations':parsed.get('semantic_passed_expectations'),'fuzz_total':parsed.get('fuzz_total'),'fuzz_blocked':parsed.get('fuzz_blocked'),'escaped':parsed.get('escaped'),'failure':r.get('failure')})
    return {'status':'PASS' if not failures else 'FAIL','suites':compact,'suite_count':len(specs),'checksum_entries':c.get('entries'),'failures':failures}

def candidate_truth_guard(root):
    failures=[]; p=root/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    if not p.exists(): return {'status':'FAIL','failures':['candidate_state_missing']}
    d=load_yaml(p)
    if d.get('website_construction_allowed') is not False: failures.append('website_construction_not_blocked')
    if d.get('github_upload_allowed') is not False: failures.append('github_upload_not_blocked')
    if d.get('formal_test_started') is not False: failures.append('formal_test_started_during_prefomal')
    if 'FORMAL_FREEZE' in str(d.get('completion_claim','')).upper() and 'NOT_STARTED' not in str(d.get('completion_claim','')).upper(): failures.append('candidate_state_overclaims_freeze')
    return {'status':'PASS' if not failures else 'FAIL','failures':failures}

def preformal(root):
    checks=[]
    def run(cid,fn):
        try: out=fn(root); checks.append({'check_id':cid,**out})
        except Exception as e: checks.append({'check_id':cid,'status':'FAIL','failures':['exception:'+repr(e)]})
    run('external_trust_root',external_trust_anchor_guard)
    run('parser_hygiene',parser_hygiene)
    run('section_registry',import_local('validate_section_registry').validate)
    run('construction_artifact_index',import_local('validate_construction_artifact_index').validate)
    run('execution_governance_load',import_local('validate_execution_governance_load').validate_definition)
    run('cleanup_protection',import_local('validate_cleanup_protection').validate)
    run('lifecycle_stage_contract',import_local('governance_lifecycle_stage_contract_guard').validate)
    run('management_contract',import_local('governance_management_contract_guard').validate)
    run('reference_semantics',import_local('validate_reference_semantics').validate)
    run('program_artifact_instance_guard',import_local('program_artifact_instance_guard').validate_definition)
    run('current_test_evidence_sync',import_local('validate_current_test_evidence').validate)
    run('evidence_state_closure',import_local('validate_evidence_state_closure').validate)
    run('closure_evidence_continuity',import_local('validate_closure_evidence_continuity').validate)
    run('stage_execution_invariants',import_local('validate_stage_execution_invariants').validate)
    run('test_feedback_spec_evolution',import_local('validate_test_feedback_spec_evolution').validate)
    run('product_neutral_entity_lifecycle',import_local('validate_product_neutral_entity_lifecycle').validate)
    run('acceptance_blueprint_compiled_baseline',baseline_guard)
    run('root_manifest',root_manifest_guard)
    run('mandatory_regression_and_package_integrity',mandatory_regression_guard)
    run('candidate_truth',candidate_truth_guard)
    fails=[c for c in checks if c.get('status')!='PASS']
    return {'mode':'PRE_FORMAL_DEFINITION_AUDIT','status':'PASS' if not fails else 'FAIL','checks_total':len(checks),'pass_count':len(checks)-len(fails),'blocking_failures':len(fails),'checks':checks,'formal_freeze_allowed':False,'formal_test_allowed':False,'github_upload_allowed':False,'website_reconstruction_allowed':False}

def stage_exec(root,stage_uid,evidence_root):
    pre=preformal(root)
    if pre['status']!='PASS': return {'mode':'STAGE_EXECUTION_VALIDATION','status':'FAIL','reason':'preformal_definition_audit_failed','preformal':pre}
    reg=load_yaml(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'); ids={s.get('stage_uid') for s in reg.get('stages') or []}
    failures=[]
    if stage_uid not in ids: failures.append('unknown_stage_uid:'+str(stage_uid))
    er=Path(evidence_root) if evidence_root else None
    if not er or not er.exists(): failures.append('stage_evidence_root_required')
    return {'mode':'STAGE_EXECUTION_VALIDATION','stage_uid':stage_uid,'status':'PASS' if not failures else 'FAIL','failures':failures,'note':'Definition-level stage-mode entry guard only; product evidence validators execute from the selected stage contract.'}

def release_final(root,evidence_root):
    pre=preformal(root); failures=[]
    if pre['status']!='PASS': failures.append('preformal_definition_audit_failed')
    er=Path(evidence_root) if evidence_root else None
    if not er or not er.exists(): failures.append('release_evidence_root_required')
    elif not (er/'RELEASE_FINAL_ACCEPTANCE.yaml').exists(): failures.append('release_final_acceptance_missing')
    else:
        d=load_yaml(er/'RELEASE_FINAL_ACCEPTANCE.yaml')
        if d.get('status')!='PASS': failures.append('release_final_acceptance_not_pass')
    return {'mode':'RELEASE_FINAL_VALIDATION','status':'PASS' if not failures else 'FAIL','failures':failures}

# Legacy v2.1.0 regression compatibility surface. These checks are not automatically
# consumed by PRE_FORMAL mode; they remain callable by inherited regression harnesses.
RESULTS=[]
def add(check_id,status,summary,details=None,blocking=True):
    RESULTS.append({"check_id":check_id,"status":status,"blocking":blocking,"summary":summary,"details":details or {}})
def load_json(p): return json.loads(p.read_text(encoding="utf-8"))

def _load_evidence_ledger(relpath, check_id):
    p=ROOT/relpath
    if not p.exists():
        add(check_id,'FAIL',f'{relpath} missing',{'required_path':relpath}); return None
    try:
        if p.suffix.lower()=='.json': d=load_json(p)
        else: d=load_yaml(p)
    except Exception as e:
        add(check_id,'FAIL',f'{relpath} parse failed',{'error':str(e)}); return None
    return d or {}

def _run_context(required=True):
    p=ROOT/'11_EVIDENCE/audit/VALIDATION_RUN_CONTEXT.yaml'
    if not p.exists():
        return None, ['VALIDATION_RUN_CONTEXT.yaml missing'] if required else []
    try: d=load_yaml(p) or {}
    except Exception as e: return None,[f'run context parse failed: {e}']
    req=['run_uid','execution_cycle','source_revision','started_at','terminal_status']
    failures=[f'missing:{k}' for k in req if not d.get(k)]
    if d.get('terminal_status') not in ('RUNNING','PASS','FAIL','BLOCKED'):
        failures.append('invalid terminal_status')
    return d,failures

def _ledger_run_binding(d, run_ctx, failures, ledger_name):
    if not run_ctx: return
    if d.get('run_uid') != run_ctx.get('run_uid'):
        failures.append({'ledger':ledger_name,'run_uid':d.get('run_uid'),'expected_run_uid':run_ctx.get('run_uid')})
    if d.get('source_revision') and d.get('source_revision') != run_ctx.get('source_revision'):
        failures.append({'ledger':ledger_name,'source_revision':d.get('source_revision'),'expected':run_ctx.get('source_revision')})

def _num(v):
    return float(v) if isinstance(v,(int,float)) else None

def check_validation_run_freshness():
    d,failures=_run_context(True)
    add('validation_run_freshness_guard','PASS' if d and not failures else 'FAIL',f'failures={len(failures)}',{'failures':failures})

def check_execution_cycle():
    d,failures=_run_context(True)
    allowed={'INITIAL_RELEASE','CHANGE_RELEASE','HOTFIX','MAINTENANCE'}
    if d and d.get('execution_cycle') not in allowed: failures.append('invalid execution_cycle')
    rp=ROOT/'11_EVIDENCE/audit/RELEASE_GATE_LEDGER.yaml'
    release=load_yaml(rp) if rp.exists() else None
    if d and d.get('execution_cycle')=='INITIAL_RELEASE':
        if not release: failures.append('RELEASE_GATE_LEDGER.yaml missing for INITIAL_RELEASE')
        else:
            stages=release.get('stages',{})
            for k in ['pre_release','production_deploy','post_deploy_acceptance','final_acceptance']:
                if stages.get(k) != 'PASS': failures.append(f'{k}:{stages.get(k)}')
            if release.get('staging_applicable',True) and stages.get('staging')!='PASS': failures.append(f"staging:{stages.get('staging')}")
    add('execution_cycle_guard','PASS' if d and not failures else 'FAIL',f'failures={len(failures)}',{'failures':failures})

def check_repository_boundary():
    rel='11_EVIDENCE/audit/REPOSITORY_BOUNDARY.yaml'; d=_load_evidence_ledger(rel,'repository_boundary_guard')
    if d is None:return
    failures=[]
    for k in ['repo_root','governed_paths','evidence_root']:
        if not d.get(k): failures.append({'missing':k})
    def unsafe(p):
        s=str(p or '')
        return s.startswith('/') or '..' in Path(s).parts
    for p in (d.get('governed_paths') or [])+[d.get('evidence_root')]:
        if unsafe(p): failures.append({'escaped_path':p})
    add('repository_boundary_guard','PASS' if not failures else 'FAIL',f'failures={len(failures)}',{'failures':failures})

def check_design_approval_timing():
    rel='11_EVIDENCE/audit/DESIGN_APPROVAL_LEDGER.yaml'; d=_load_evidence_ledger(rel,'design_approval_timing_guard')
    if d is None:return
    failures=[]
    if d.get('visual_review_status')!='PASS': failures.append('visual_review_not_pass')
    if d.get('design_approval_status')!='PASS': failures.append('design_approval_not_pass')
    if d.get('freeze_status')!='PASS': failures.append('freeze_not_pass')
    if not d.get('design_revision') or d.get('design_revision')!=d.get('approved_design_revision'):
        failures.append('design_revision_mismatch')
    # ISO 8601 lexical ordering is sufficient if normalized timezone format is used.
    vr=d.get('visual_reviewed_at'); ap=d.get('design_approved_at'); fr=d.get('frozen_at')
    if not all([vr,ap,fr]) or not (vr <= ap <= fr): failures.append('approval_timing_invalid')
    add('design_approval_timing_guard','PASS' if not failures else 'FAIL',f'failures={len(failures)}',{'failures':failures})

def check_deployment_applicability():
    rel='11_EVIDENCE/audit/DEPLOYMENT_APPLICABILITY.yaml'; d=_load_evidence_ledger(rel,'deployment_applicability_guard')
    if d is None:return
    failures=[]
    applicable=d.get('deployment_applicable')
    if applicable is True:
        for k in ['build_gate_consumed','deployment_gate_consumed','production_identity_gate_consumed','production_browser_gate_consumed']:
            if d.get(k) is not True: failures.append({k:d.get(k)})
    elif applicable is False:
        if d.get('authority_applicability')!='NOT_APPLICABLE' or not d.get('authority_evidence'):
            failures.append('deployment N/A missing authority evidence')
    else: failures.append('deployment_applicable missing')
    add('deployment_applicability_guard','PASS' if not failures else 'FAIL',f'failures={len(failures)}',{'failures':failures})

def check_source_truth():
    rel='11_EVIDENCE/audit/SOURCE_TRUTH_LEDGER.yaml'; d=_load_evidence_ledger(rel,'source_truth_guard')
    if d is None:return
    records=d.get('sources',[]); failures=[]
    run_ctx,_=_run_context(False); _ledger_run_binding(d,run_ctx,failures,rel)
    req=['source_uid','source_path','source_hash','source_type','representation_role','authority_role','canonical_uid','owner_claim','revision','current_authority_membership','positive_ui_authority','authority_scope','conflict_state','contamination_state','resolution_result','evidence_ref']
    forbidden_current_roles={'DRAFT','REFERENCE_ONLY','HISTORICAL','SUPERSEDED','GENERATED_NON_AUTHORITY','EXECUTION_ARTIFACT'}
    groups=defaultdict(list)
    for x in records:
        miss=[k for k in req if k not in x]
        if miss: failures.append({'source_uid':x.get('source_uid'),'missing':miss})
        if x.get('resolution_result') in (None,'UNRESOLVED') or x.get('conflict_state') in ('CONFLICTING','UNRESOLVED') or x.get('contamination_state') in ('CONTAMINATED','UNRESOLVED'):
            failures.append({'source_uid':x.get('source_uid'),'state':'unresolved_or_contaminated'})
        current=bool(x.get('current_authority_membership'))
        positive=x.get('positive_ui_authority') is True
        scope=x.get('authority_scope')
        representation=str(x.get('representation_role','')).upper()
        if representation in ('MACHINE_ENCODING_MIRROR','GENERATED_MIRROR','SNAPSHOT_POINTER'):
            if not x.get('canonical_owner_ref'):
                failures.append({'source_uid':x.get('source_uid'),'mirror_missing_canonical_owner_ref':True})
            if representation in ('MACHINE_ENCODING_MIRROR','GENERATED_MIRROR') and not x.get('semantic_sync_evidence'):
                failures.append({'source_uid':x.get('source_uid'),'mirror_missing_semantic_sync_evidence':True})
            if positive:
                failures.append({'source_uid':x.get('source_uid'),'mirror_cannot_be_positive_editable_authority':representation})
        if current and positive:
            groups[(x.get('canonical_uid'),scope)].append(x)
        role=str(x.get('authority_role','')).upper()
        status=str(x.get('authority_status','')).upper()
        if current and (role in forbidden_current_roles or status in forbidden_current_roles):
            failures.append({'source_uid':x.get('source_uid'),'invalid_current_role':role or status})
        if status=='SUPERSEDED' and current: failures.append({'source_uid':x.get('source_uid'),'superseded_marked_current':True})
    for key,arr in groups.items():
        owners={(str(x.get('current_owner_uid') or x.get('owner_claim')),str(x.get('source_path'))) for x in arr}
        if len(owners)>1:
            failures.append({'canonical_scope':key,'recomputed_current_owner_conflict':[x.get('source_uid') for x in arr]})
    # metrics are informational; recomputation wins.
    metrics=d.get('metrics',{})
    for k in ['unresolved_source_truth','current_owner_conflict','current_source_contamination','unmapped_superseded_content']:
        if metrics.get(k) not in (None,0): failures.append({'metric':k,'value':metrics.get(k)})
    add('source_truth_guard','PASS' if records and not failures else 'FAIL',f'source_records={len(records)} failures={len(failures)}',{'failures':failures[:100]})

def check_functional_chain():
    rel='11_EVIDENCE/audit/FUNCTIONAL_CHAIN_MATRIX.yaml'; d=_load_evidence_ledger(rel,'functional_chain_guard')
    if d is None:return
    chains=d.get('chains',[]); failures=[]
    run_ctx,_=_run_context(False); _ledger_run_binding(d,run_ctx,failures,rel)
    allowed={'COMPLETE','AUTO_REMEDIABLE','IMPLEMENTATION_GAP','SHARED_OWNER_REFERENCE','INPUT_SOURCE_GAP','AUTHORITY_GAP','ARCHITECTURE_GAP','INTENTIONAL_FAIL_CLOSED','TEST_ONLY_BEHAVIOR'}
    base_nodes=['business_intent','preconditions','entry','input_source','trigger','gate','permission','action','validation','response_feedback','success_state','next_state','next_step','next_gate','failure_state','recovery','terminal_outcome']
    effectful={'EXTERNAL_EFFECTS_REQUIRED','CONVERSATION_WRITE','JOB_START','DRAFT_MUTATION','VERSION_CREATE','VERSION_LOCK','DECISION_MUTATION','SCORE_MUTATION','HANDOFF_CREATE','CANDIDATE_CREATE','FINDING_CREATE'}
    no_api={'UI_ONLY','CONTEXT_STATE'}
    for c in chains:
        uid=c.get('flow_uid'); nodes=c.get('nodes',{}); effect=str(c.get('effect_type','')).upper()
        miss=[n for n in base_nodes if n not in nodes or nodes.get(n) in (None,'')]
        if miss: failures.append({'flow_uid':uid,'missing_nodes':miss})
        if not effect: failures.append({'flow_uid':uid,'missing_effect_type':True})
        cls=c.get('classification','COMPLETE')
        if cls not in allowed: failures.append({'flow_uid':uid,'bad_classification':cls})
        production_required=c.get('production_required',c.get('required',True))
        if production_required and cls in ('INTENTIONAL_FAIL_CLOSED','TEST_ONLY_BEHAVIOR'):
            failures.append({'flow_uid':uid,'production_required_but_not_eligible':cls})
        if production_required and c.get('production_eligible') is False:
            failures.append({'flow_uid':uid,'production_eligible':False})
        if c.get('required',True) and cls not in ('COMPLETE','SHARED_OWNER_REFERENCE'):
            failures.append({'flow_uid':uid,'open_gap':cls})
        binding=str(c.get('binding_kind','')).upper()
        if effect in effectful:
            # Never infer a new page-local API/runtime when the current Authority delegates to a shared owner.
            # The evidence chain must instead resolve the exact shared owner/operation or exact integration port.
            if binding == 'SHARED_OPERATION_REFERENCE':
                for n in ['payload','runtime_owner','audit_event']:
                    val=nodes.get(n)
                    if val in (None,'','N/A','NOT_APPLICABLE'):
                        failures.append({'flow_uid':uid,'effect_type':effect,'required_effect_node':n,'value':val})
                if not c.get('shared_owner_reference') or not c.get('shared_operation_id'):
                    failures.append({'flow_uid':uid,'shared_owner_reference_incomplete':True})
                for n in ['api_entry','data_provider']:
                    val=nodes.get(n)
                    if val in (None,'','N/A','NOT_APPLICABLE') and not c.get('not_applicable_authority_evidence'):
                        failures.append({'flow_uid':uid,'shared_binding_n_a_without_authority':n})
            elif binding in ('SOURCE_INTEGRATION_PORT','COMPOSITE_TO_EXISTING_EXECUTE_PORT','EVALUATION_COMPOSITE'):
                for n in ['payload','api_entry','runtime_owner','data_provider','audit_event']:
                    val=nodes.get(n)
                    if val in (None,'','N/A','NOT_APPLICABLE'):
                        failures.append({'flow_uid':uid,'effect_type':effect,'required_effect_node':n,'value':val})
                if not c.get('port_uid') and binding != 'EVALUATION_COMPOSITE':
                    failures.append({'flow_uid':uid,'binding_kind':binding,'missing_port_uid':True})
            else:
                for n in ['payload','api_entry','runtime_owner','data_provider','audit_event']:
                    val=nodes.get(n)
                    if val in (None,'','N/A','NOT_APPLICABLE'):
                        failures.append({'flow_uid':uid,'effect_type':effect,'required_effect_node':n,'value':val})
                if binding in ('','CLIENT_STATE_OR_VIEW_NO_API_REQUIRED'):
                    failures.append({'flow_uid':uid,'effect_type':effect,'invalid_effectful_binding_kind':binding or 'MISSING'})
        elif effect in no_api:
            if binding and binding != 'CLIENT_STATE_OR_VIEW_NO_API_REQUIRED':
                failures.append({'flow_uid':uid,'effect_type':effect,'unexpected_binding_kind':binding})
            for n in ['api_entry','runtime_owner','data_provider']:
                val=nodes.get(n)
                if val in ('N/A','NOT_APPLICABLE',None,'') and not c.get('not_applicable_authority_evidence'):
                    failures.append({'flow_uid':uid,'effect_type':effect,'n_a_without_authority':n})
        if effect=='JOB_START':
            a=c.get('async_lifecycle') or {}
            for k in ['request_identity','input_fingerprint','idempotency','states','retry_policy','result_provenance','output_persistence','audit_correlation']:
                if not a.get(k): failures.append({'flow_uid':uid,'async_missing':k})
        if c.get('invented_default') is True or c.get('test_only_used_in_production') is True:
            failures.append({'flow_uid':uid,'unsafe_auto_fill':True})
    add('functional_chain_guard','PASS' if chains and not failures else 'FAIL',f'chains={len(chains)} failures={len(failures)}',{'failures':failures[:100]})

def check_visual_geometry():
    rel='11_EVIDENCE/audit/VISUAL_GEOMETRY_BASELINE.yaml'; d=_load_evidence_ledger(rel,'visual_geometry_guard')
    if d is None:return
    views=d.get('viewports',[]); failures=[]
    run_ctx,_=_run_context(False); _ledger_run_binding(d,run_ctx,failures,rel)
    metric_keys=['overlap_count','clipping_count','overflow_count','occlusion_count','unexpected_wrap_count','text_overflow_count','dimension_violation_count','anchor_drift_count']
    for v in views:
        for k in ['viewport_uid','width','height','targets']:
            if k not in v: failures.append({'viewport_uid':v.get('viewport_uid'),'missing':k})
        if v.get('measurement_source') not in ('BROWSER_DOM','PLAYWRIGHT_DOM','PRODUCTION_BROWSER_DOM') or not v.get('captured_at'):
            failures.append({'viewport_uid':v.get('viewport_uid'),'missing_verifiable_measurement':True})
        for t in v.get('targets',[]):
            exp=t.get('expected_geometry'); act=t.get('actual_geometry'); tol=t.get('tolerance',0)
            if not isinstance(exp,dict) or not isinstance(act,dict):
                failures.append({'target_uid':t.get('target_uid'),'missing_geometry':True}); continue
            try: tol=float(tol)
            except: tol=0.0; failures.append({'target_uid':t.get('target_uid'),'bad_tolerance':t.get('tolerance')})
            for dim in set(exp).intersection(act):
                a=_num(exp[dim]); b=_num(act[dim])
                if a is not None and b is not None and abs(a-b)>tol:
                    failures.append({'target_uid':t.get('target_uid'),'dimension':dim,'expected':a,'actual':b,'tolerance':tol})
            for k in metric_keys:
                if t.get(k,0)!=0: failures.append({'target_uid':t.get('target_uid'),'metric':k,'value':t.get(k)})
            if t.get('visual_diff_result') not in (None,'PASS'): failures.append({'target_uid':t.get('target_uid'),'visual_diff_result':t.get('visual_diff_result')})
    add('visual_geometry_guard','PASS' if views and not failures else 'FAIL',f'viewports={len(views)} failures={len(failures)}',{'failures':failures[:100]})

def check_production_render_identity():
    rel='11_EVIDENCE/audit/DEPLOYMENT_RENDER_IDENTITY.yaml'; d=_load_evidence_ledger(rel,'production_render_identity_guard')
    if d is None:return
    failures=[]; run_ctx,_=_run_context(False); _ledger_run_binding(d,run_ctx,failures,rel)
    for k in ['run_uid','captured_at','production_url','capture_source']:
        if not d.get(k): failures.append({'missing':k})
    if d.get('capture_source') not in ('PRODUCTION_BROWSER','PRODUCTION_BROWSER_DOM'): failures.append({'capture_source':d.get('capture_source')})
    revisions=[d.get('expected_source_revision'),d.get('build_source_revision'),d.get('deployed_source_revision'),d.get('runtime_reported_revision')]
    if not all(revisions) or len(set(revisions))!=1: failures.append({'revision_chain':revisions})
    for a,b,name in [(d.get('route_manifest_hash'),d.get('production_route_manifest_hash'),'route_manifest'),(d.get('client_asset_manifest_hash'),d.get('production_client_asset_manifest_hash'),'client_asset_manifest'),(d.get('expected_dom_fingerprint'),d.get('dom_fingerprint'),'dom_fingerprint')]:
        if not a or not b or a!=b: failures.append({'mismatch':name,'expected':a,'actual':b})
    if d.get('visual_geometry_result')!='PASS': failures.append({'visual_geometry_result':d.get('visual_geometry_result')})
    if d.get('stale_release_fingerprint_detected') not in (False,0): failures.append({'stale_release_fingerprint_detected':d.get('stale_release_fingerprint_detected')})
    add('production_render_identity_guard','PASS' if not failures else 'FAIL',f'failures={len(failures)}',{'failures':failures})

def check_cross_page_flow():
    rel='11_EVIDENCE/audit/CROSS_PAGE_FLOW_MATRIX.yaml'; d=_load_evidence_ledger(rel,'cross_page_flow_guard')
    if d is None:return
    flows=d.get('flows',[]); failures=[]; run_ctx,_=_run_context(False); _ledger_run_binding(d,run_ctx,failures,rel)
    if d.get('not_applicable') is True:
        if d.get('authority_applicability')!='NOT_APPLICABLE' or not d.get('authority_evidence'):
            failures.append({'n_a_without_authority':True})
    req=['flow_uid','source_uid','exit_contract','target_uid','target_entry_contract','permission_continuity','state_transition','error_retry_resume','audit_continuity','production_e2e']
    for f in flows:
        miss=[k for k in req if k not in f]
        if miss: failures.append({'flow_uid':f.get('flow_uid'),'missing':miss})
        if f.get('required',True):
            for k in ['permission_continuity','state_transition','error_retry_resume','audit_continuity','production_e2e']:
                if f.get(k)!='PASS': failures.append({'flow_uid':f.get('flow_uid'),'gate':k,'value':f.get(k)})
    ok=(bool(flows) or (d.get('not_applicable') is True and d.get('authority_applicability')=='NOT_APPLICABLE' and bool(d.get('authority_evidence')))) and not failures
    add('cross_page_flow_guard','PASS' if ok else 'FAIL',f'flows={len(flows)} failures={len(failures)}',{'failures':failures[:100]})

def check_state_transition():
    rel='11_EVIDENCE/audit/STATE_TRANSITION_LEDGER.yaml'; d=_load_evidence_ledger(rel,'state_transition_guard')
    if d is None:return
    failures=[]
    if d.get('not_applicable') is True:
        if d.get('authority_applicability')!='NOT_APPLICABLE' or not d.get('authority_evidence'): failures.append('N/A without authority')
    else:
        trs=d.get('transitions',[])
        for t in trs:
            for k in ['transition_uid','from_state','to_state','trigger','gate','preconditions','mutation_owner','failure_state','recovery','audit_event','illegal_transition_test','status']:
                if t.get(k) in (None,''): failures.append({'transition_uid':t.get('transition_uid'),'missing':k})
            if t.get('status')!='PASS': failures.append({'transition_uid':t.get('transition_uid'),'status':t.get('status')})
        if d.get('required',True) and not trs: failures.append('required transitions empty')
    add('state_transition_guard','PASS' if not failures else 'FAIL',f'failures={len(failures)}',{'failures':failures[:100]})

def check_field_identity():
    rel='11_EVIDENCE/audit/FIELD_IDENTITY_LEDGER.yaml'; d=_load_evidence_ledger(rel,'field_identity_guard')
    if d is None:return
    failures=[]
    if d.get('not_applicable') is True:
        if d.get('authority_applicability')!='NOT_APPLICABLE' or not d.get('authority_evidence'): failures.append('N/A without authority')
    else:
        mappings=d.get('mappings',[])
        for m in mappings:
            for k in ['concept_object','canonical_field','ui_label','localization_key','validation_contract']:
                if not m.get(k): failures.append({'canonical_field':m.get('canonical_field'),'missing':k})
            if m.get('generated_identity') is True and (m.get('read_only') is not True or m.get('client_generated') is not False):
                failures.append({'canonical_field':m.get('canonical_field'),'generated_identity_mutability_violation':True})
        if d.get('required',True) and not mappings: failures.append('required mappings empty')
    add('field_identity_guard','PASS' if not failures else 'FAIL',f'failures={len(failures)}',{'failures':failures[:100]})

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',default='PRE_FORMAL_DEFINITION_AUDIT',choices=['PRE_FORMAL_DEFINITION_AUDIT','STAGE_EXECUTION_VALIDATION','RELEASE_FINAL_VALIDATION']); ap.add_argument('--stage'); ap.add_argument('--evidence-root'); args=ap.parse_args()
    if args.mode=='PRE_FORMAL_DEFINITION_AUDIT': out=preformal(ROOT)
    elif args.mode=='STAGE_EXECUTION_VALIDATION': out=stage_exec(ROOT,args.stage,args.evidence_root)
    else: out=release_final(ROOT,args.evidence_root)
    print(json.dumps(out,ensure_ascii=False,indent=2)); return 0 if out['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
