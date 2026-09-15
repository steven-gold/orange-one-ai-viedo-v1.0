#!/usr/bin/env python3
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path
import json, os, re, subprocess, sys, yaml

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'00_SOURCE_INTAKE/fresh_run_003'
PRODUCT=RUN/'04_PAGE_FUNCTIONAL_CONTRACT'
SCANNER=ROOT/'governance/ci/run_current_stage2_actual_test.py'
STATE=ROOT/'governance/test/ACTIVE_STATE.yaml'
FREEZE=ROOT/'governance/test/stage02/STAGE02_STAGE_FROZEN_GOVERNANCE_RECEIPT.yaml'
LATEST=ROOT/'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
FINDINGS=ROOT/'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
RESULT=ROOT/'.github/stage02-test/STAGE02_R29_EFFECTIVE_REEXECUTION_RESULT.json'
R28=ROOT/'governance/test/stage02/STAGE02_FAILURE_RECOVERY_APPLICABILITY_AUDIT_R28.yaml'
GAP006=PRODUCT/'SHARED_OWNER_PORT_MAP_R3.yaml'
PAGES={
 'CORE-01':{'raw':RUN/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml','blueprint':RUN/'02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml','ledger':PRODUCT/'CORE-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml','ai':True},
 'ASSET-01':{'raw':RUN/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml','blueprint':RUN/'02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml','ledger':PRODUCT/'ASSET-01/AUTO_COMPLETION_SCOPE_LEDGER.yaml','ai':False},
}
EXPECTED_GAPS={f'GAP-{i:03}' for i in range(1,9)}
GAP006_DETAIL='GAP-006: ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY'
EXPECTED_EFFECTIVE_CATEGORIES={
 'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1,
 'AUDIT_EVENT_NODE_MISSING':13,
 'FAILURE_STATE_ERROR_BINDING_MISSING':23,
 'PAYLOAD_INPUT_CONTRACT_MISSING':34,
 'POST_ACTION_VALIDATION_NODE_MISSING':18,
 'STATE_TRANSITION_LEDGER_FIELD_MISSING':40,
}

def die(msg): print(f'BLOCK: {msg}',file=sys.stderr); raise SystemExit(1)
def load(p):
    if not p.is_file(): die(f'MISSING:{p.relative_to(ROOT)}')
    o=yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(o,dict): die(f'MAPPING_REQUIRED:{p.relative_to(ROOT)}')
    return o
def head(): return subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True,capture_output=True,check=True).stdout.strip()
def sig(page,g): return (page,g.get('category'),str(g.get('uid')),g.get('detail'))

def fresh_scan_fn():
    tree=ast.parse(SCANNER.read_text(encoding='utf-8'),filename=str(SCANNER)); keep={'idx','present','event_token','has_transition','add','fresh_scan'}; selected=[]
    for node in tree.body:
        if isinstance(node,ast.Assign) and 'KNOWN_AUTHORITIES' in {t.id for t in node.targets if isinstance(t,ast.Name)}: selected.append(node)
        elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in keep: selected.append(node)
    found={n.name for n in selected if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    if found!=keep: die(f'FRESH_SCAN_EXTRACTION_DRIFT:{sorted(found)}')
    module=ast.Module(body=selected,type_ignores=[]); ast.fix_missing_locations(module); ns={'Counter':Counter,'defaultdict':defaultdict,'re':re}
    exec(compile(module,str(SCANNER),'exec'),ns,ns); return ns['fresh_scan']

def load_product():
    out={}; by=Counter(); cycle=Counter()
    for page,cfg in PAGES.items():
        l=load(cfg['ledger']); rems=l.get('remediations') or []; expected=5 if page=='CORE-01' else 12
        if l.get('materialized_remediation_count')!=expected or len(rems)!=expected: die(f'R29_LEDGER_COUNT_DRIFT:{page}:{len(rems)}')
        for rem in rems:
            ds=rem.get('defect_signature') or {}; key=(page,ds.get('category'),str(ds.get('uid')),ds.get('detail'))
            if key in out: die(f'DUPLICATE_PRODUCT_SIGNATURE:{key}')
            if ds.get('category') in {'POST_ACTION_VALIDATION_NODE_MISSING','FAILURE_STATE_ERROR_BINDING_MISSING'}: die(f'R29_DISALLOWED_PRODUCT_MATERIALIZATION_CATEGORY:{key}')
            out[key]=rem; by[page]+=1; cycle[str(rem.get('source_cycle') or 'R3_BOUNDED_FUNCTIONAL_COMPLETION')]+=1
    if len(out)!=17 or by!=Counter({'ASSET-01':12,'CORE-01':5}): die(f'R29_PRODUCT_DENOMINATOR_DRIFT:{len(out)}:{dict(by)}')
    if cycle.get('R20_FUNCTIONAL_CHAIN_AUTO_REMEDIABILITY',0)!=0 or cycle.get('R22_POST_ACTION_SIGNAL_ROLE_CORRECTION',0)!=0: die(f'R29_INVALID_CYCLE_REMAINS:{dict(cycle)}')
    return out,by,cycle

def load_gap006():
    d=load(GAP006); out={}
    if d.get('artifact_uid')!='FRESH-RUN-003-STAGE2-SHARED-OWNER-PORT-MAP-R3' or d.get('status')!='RESOLVED_AUTHORITY_GAP_CURRENT_SUCCESSOR': die('GAP006_MAP_DRIFT')
    for row in d.get('consumers') or []:
        if row.get('page_uid')!='ASSET-01' or row.get('status')!='RESOLVED_EXACT_AUTHORITY': die('GAP006_CONSUMER_DRIFT')
        out[('ASSET-01','SHARED_OWNER_AUTHORITY_UNRESOLVED',str(row.get('action_uid')),GAP006_DETAIL)]=row
    if len(out)!=4: die(f'GAP006_COUNT:{len(out)}')
    return out

def extrefs(bp): return [{'gap_uid':x.get('gap_uid'),'authority_ref':x.get('authority_ref')} for x in bp.get('unresolved_external_authority_refs') or [] if isinstance(x,dict)]
def effective(page,rawscan,product,gap006):
    remain=[]; prod=[]; auth=[]; keys=[sig(page,g) for g in rawscan.get('gaps') or []]
    if len(keys)!=len(set(keys)): die(f'RAW_SIGNATURE_DUPLICATE:{page}')
    for gap in rawscan.get('gaps') or []:
        key=sig(page,gap)
        if key in product and key in gap006: die(f'OVERLAP:{key}')
        if key in product:
            rem=product[key]; prod.append({'raw_gap':gap,'remediation_uid':rem.get('remediation_uid'),'source_cycle':rem.get('source_cycle','R3_BOUNDED_FUNCTIONAL_COMPLETION'),'materialized_closure':rem.get('materialized_closure'),'effective_reproduction':False})
        elif key in gap006: auth.append({'raw_gap':gap,'authority_gap_uid':'GAP-006','resolution':'RESOLVED_EXACT_AUTHORITY','effective_reproduction':False})
        else: remain.append(gap)
    return {'gap_count':len(remain),'gap_categories':dict(sorted(Counter(x.get('category') for x in remain).items())),'gap_classes':dict(sorted(Counter(x.get('class') for x in remain).items())),'gaps':remain,'product_materialization_elimination_count':len(prod),'product_materialization_eliminations':prod,'gap006_authority_elimination_count':len(auth),'gap006_authority_eliminations':auth,'total_elimination_count':len(prod)+len(auth)}

if os.environ.get('STAGE02_FULL_LINE_CONFIRMED')!='1': die('R29_REEXECUTION_REQUIRES_FULL_LINE_CONFIRMATION')
state=load(STATE); freeze=load(FREEZE); r28=load(R28); execution=state.get('execution') or {}
if execution.get('current_stage')!='STAGE-02-TESTED-BLOCKED' or (execution.get('stage2') or {}).get('result')!='TEST_EXECUTED_BLOCKED': die('R29_REQUIRES_STAGE02_BLOCKED')
if freeze.get('stage_uid')!='STAGE-02' or not freeze.get('frozen_governance_uid'): die('R29_FREEZE_RECEIPT_DRIFT')
if (r28.get('denominators') or {}).get('not_applicable_exact_proof_count')!=21 or (r28.get('denominators') or {}).get('keep_gap_count')!=23: die('R29_R28_APPLICABILITY_DENOMINATOR_DRIFT')
for v in (ROOT/'governance/ci/validate_stage02_failure_recovery_applicability_r28.py',ROOT/'governance/ci/validate_stage02_failure_recovery_scanner_fix_r29.py',ROOT/'governance/ci/validate_stage02_r25_correctness_rollback.py',ROOT/'governance/ci/validate_current_stage2_external_authority_resolution_r3.py'):
    if subprocess.run([sys.executable,str(v)],cwd=str(ROOT)).returncode!=0: die(f'PRE_REEXECUTION_VALIDATOR_FAILED:{v.name}')

scan=fresh_scan_fn(); product,product_by,cycles=load_product(); gap006=load_gap006()
if set(product)&set(gap006): die('PRODUCT_GAP006_OVERLAP')
pages={}; source_external={}; union=set(); matched_product=set(); matched_gap006=set(); raw_total=prod_elim=auth_elim=eff_total=0
raw_cats=Counter()
for page,cfg in PAGES.items():
    raw=load(cfg['raw']); bp=load(cfg['blueprint']); refs=extrefs(bp)
    for ref in refs:
        gid=ref.get('gap_uid'); union.add(gid); rec=source_external.setdefault(gid,{'authority_ref':ref.get('authority_ref'),'consumers':[],'source_reference_preserved':True}); rec['consumers'].append(page)
    rawscan=scan(page,raw); eff=effective(page,rawscan,product,gap006)
    raw_total+=rawscan.get('gap_count',0); raw_cats.update(rawscan.get('gap_categories') or {}); prod_elim+=eff['product_materialization_elimination_count']; auth_elim+=eff['gap006_authority_elimination_count']; eff_total+=eff['gap_count']
    matched_product|={sig(page,x['raw_gap']) for x in eff['product_materialization_eliminations']}; matched_gap006|={sig(page,x['raw_gap']) for x in eff['gap006_authority_eliminations']}
    pages[page]={'blueprint_uid':bp.get('blueprint_uid'),'ai_interaction_profile_active':cfg['ai'],'source_external_authority_ref_count':len(refs),'functional_chain_raw_fresh_scan':rawscan,'functional_chain_effective_r29_scan':eff,'materialized_product_functional_contract_validation':'PASS','gap006_external_authority_validation':'PASS'}
if raw_total!=150: die(f'R29_RAW_DENOMINATOR_DRIFT:{raw_total}')
if raw_cats.get('FAILURE_STATE_ERROR_BINDING_MISSING')!=23: die(f'R29_RAW_FAILURE_CATEGORY_DRIFT:{dict(raw_cats)}')
if matched_product!=set(product): die(f'PRODUCT_SIGNATURE_MATCH_DRIFT:missing={sorted(set(product)-matched_product)}')
if matched_gap006!=set(gap006): die(f'GAP006_SIGNATURE_MATCH_DRIFT:missing={sorted(set(gap006)-matched_gap006)}')
if prod_elim!=17 or auth_elim!=4 or eff_total!=129: die(f'R29_ARITHMETIC_DRIFT:{raw_total}:{prod_elim}:{auth_elim}:{eff_total}')
if eff_total!=raw_total-prod_elim-auth_elim: die('R29_ARITHMETIC_IDENTITY_FAILED')
if union!=EXPECTED_GAPS: die(f'EXTERNAL_AUTHORITY_UNION_DRIFT:{sorted(union)}')
cats=Counter()
for p in pages.values(): cats.update(p['functional_chain_effective_r29_scan']['gap_categories'])
if dict(sorted(cats.items()))!=EXPECTED_EFFECTIVE_CATEGORIES: die(f'R29_EFFECTIVE_CATEGORY_DRIFT:{dict(sorted(cats.items()))}')

result={'schema_version':9,'artifact_type':'NON_NORMATIVE_STAGE02_ACTUAL_TEST_EVIDENCE','normative_authority':False,'stage_uid':'STAGE-02','stage_name':'PAGE_FUNCTIONAL_CONTRACT','reexecution_cycle':'R29_FAILURE_RECOVERY_APPLICABILITY_SCANNER_CORRECTION','source_head_sha':head(),'frozen_governance_uid':freeze.get('frozen_governance_uid'),'test_mode':'FRESH_RAW_DISCOVERY_WITH_CANONICAL_APPLICABILITY_FIX_PLUS_VALIDATED_STAGE2_BOUNDED_CLOSURES_AND_GAP006_AUTHORITY','fresh_scan_implementation':'EXACT_AST_EXTRACT_OF_CORRECTED_run_current_stage2_actual_test.py::fresh_scan','actual_product_stage_test_started':True,'actual_product_stage_test_completed':True,'stage_entry_gate':'PASS','stage_exit_allowed':False,'result':'BLOCKED','pages':pages,'raw_discovery_gap_total':150,'raw_failure_recovery_gap_total':23,'r28_exact_not_applicable_count':21,'product_materialization_total':17,'product_materialization_by_page':dict(product_by),'product_materialization_cycle_counts':dict(cycles),'product_materialization_elimination_count':17,'gap006_authority_elimination_count':4,'total_effective_elimination_count':21,'fresh_functional_gap_total':129,'effective_gap_categories':dict(sorted(cats.items())),'preserved_external_authorities':dict(sorted(source_external.items())),'preserved_external_authority_union_count':len(union),'preserved_external_authority_union_gap_uids':sorted(union),'correctness_correction':{'finding_uid':'FIND-20260915-025','false_positive_failure_recovery_gaps_removed':21,'reason':'WEB-GOV-01-S040C requires Required/Optional/Not Applicable classification and WEB-GOV-02-S009 mandates complete error behavior for Effectful Capability; exact non-effectful client/no-api/no-transition actions are N/A rather than missing recovery contracts','recovery_value_materialized':False},'current_specification_mutated':False,'immutable_stage1_source_mutated':False,'ai_autofill_used':False,'inference_used':False,'prior_stage2_results_used_as_scan_input':False,'website_construction_allowed':False,'deployment_allowed':False,'notes':['R29 corrected the canonical scanner applicability boundary before FAILURE_STATE_ERROR_BINDING_MISSING emission.','Exactly 21 ASSET non-effectful client/no-api/no-transition actions are proven Failure/Recovery NOT_APPLICABLE; no recovery value was invented.','Fresh Raw discovery is 150; validated product eliminations remain 17; GAP-006 authority eliminations remain 4; effective gaps are 129.','FAILURE_STATE_ERROR_BINDING_MISSING is now 23.','Stage-02 remains blocked; Stage-03, website construction, and deployment remain prohibited.']}
RESULT.parent.mkdir(parents=True,exist_ok=True); text=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n'; RESULT.write_text(text,encoding='utf-8'); LATEST.write_text(text,encoding='utf-8')
FINDINGS.write_text(yaml.safe_dump({'schema_version':9,'artifact_type':'STAGE02_CURRENT_FINDINGS','normative_authority':False,'stage_uid':'STAGE-02','source_cycle':'R29_FAILURE_RECOVERY_APPLICABILITY_SCANNER_CORRECTION','source_head_sha':result['source_head_sha'],'raw_discovery_gap_total':150,'failure_recovery_not_applicable_false_positive_removed':21,'validated_product_materialization_elimination_count':17,'validated_external_authority_elimination_count':4,'fresh_functional_gap_total':129,'effective_gap_categories':EXPECTED_EFFECTIVE_CATEGORIES,'result':'BLOCKED','current_specification_mutated':False,'immutable_stage1_source_mutated':False,'stage03_allowed':False,'website_construction_allowed':False,'deployment_allowed':False},allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
print('PASS: corrected fresh raw Stage-02 scan=150; failure/recovery gaps=23')
print('PASS: product eliminations=17; GAP-006 eliminations=4; effective gaps=129')
print('BLOCKED: Stage-02 remains fail-closed')
