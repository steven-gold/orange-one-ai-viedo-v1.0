#!/usr/bin/env python3
from pathlib import Path
import subprocess,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'
def die(m): raise SystemExit(m)
def load(p):
 try: d=yaml.safe_load(p.read_text(encoding='utf-8'))
 except Exception as e: die('parse failure:'+str(p)+':'+str(e))
 if not isinstance(d,dict): die('mapping required:'+str(p))
 return d
def gitobj(path):
 r=subprocess.run(['git','rev-parse','HEAD:'+path],text=True,capture_output=True)
 if r.returncode: die('git object missing:'+path)
 return r.stdout.strip()
locked={
 '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/evidence/SOURCE_ENUMERATION_EVIDENCE.yaml':'fded0411e8c1bbc52bfa8ea3d11aca3f67b582ad',
 '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/evidence/CONFLICT_DECISION_EVIDENCE.yaml':'5cf6441cb17bcbdcd50c34992751364cb6269be4',
 '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/evidence/STAGE1_VALIDATION_EVIDENCE.yaml':'fa9e30a6007f0ae566d4f1897c461c3b8fd5ab6c',
 '00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml':'0c067fb8be186a899b42115a82d71312b4014502',
 '00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml':'52bb27bf7eb423ddb13bcac5bd34edbcb369de3a',
 '00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/VISUAL_BASE_BLUEPRINT.yaml':'8edd134ea4610ab3cb192bca7b3a34ec24ae6368',
 '00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/VISUAL_BASE_BLUEPRINT.yaml':'f09ec9e4ccbedd1487c91592cb1df83ba5e62464',
 '00_SOURCE_INTAKE/fresh_run_003/03_BLUEPRINT_BINDING/CORE-01/BLUEPRINT_BINDING_MANIFEST.yaml':'8180bda073fcd26e82372e6ae15b256026a5544e',
 '00_SOURCE_INTAKE/fresh_run_003/03_BLUEPRINT_BINDING/ASSET-01/BLUEPRINT_BINDING_MANIFEST.yaml':'1879d88110a430fa261660ec5052e9468a6adcdd'}
for p,b in locked.items():
 if gitobj(p)!=b: die('Stage1 predecessor artifact drift:'+p)
s=load(run/'EXECUTION_STATE.yaml')
for k in ('source_fact_materialization_completed','responsibility_classification_completed','page_base_blueprint_completed','visual_base_blueprint_completed','blueprint_binding_completed','stage1_validation_completed'):
 if s.get(k) is not True: die('Stage1 predecessor completion lost:'+k)
rec=(s.get('terminal_receipts') or {}).get('stage1_closure') or {}
expected={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'c6a9c2e5b38a189a6517d59345a0738618e8cd28','run_id':34755361339,'job_denominator':'12/12','conclusion':'SUCCESS'}
if rec!=expected: die('Stage1 external terminal receipt drift')
if s.get('stage2_started') is not True: die('Stage2 successor not started')
for page in ('CORE-01','ASSET-01'):
 d=load(run/f'04_PAGE_FUNCTIONAL_CONTRACT/{page}/FUNCTIONAL_CHAIN_SPEC.yaml')
 if d.get('stage_uid')!='STAGE-02' or d.get('operation_uid')!='FUNCTIONAL_CHAIN_COMPILE': die(page+' Stage2 spec identity drift')
 if d.get('functional_completion_claim') is not False: die(page+' false functional completion claim')
 er=((d.get('entry_gate') or {}).get('terminal_receipt') or {})
 if er!=expected: die(page+' Stage1 receipt binding drift')
print('PASS: Stage-01 immutable closure evidence and Page/Visual/Binding bytes remain exact under legal Stage-02 successor')
print('PASS: Stage-01 12/12 external receipt remains canonical; Stage-02 FUNCTIONAL_CHAIN_COMPILE materialized without false completion claim')
print('PASS: validator is successor-state monotonic; it does not pin global Current state or future successor flags')
