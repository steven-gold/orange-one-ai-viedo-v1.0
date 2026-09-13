#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import subprocess,yaml
root=Path('.'); run=root/'00_SOURCE_INTAKE/fresh_run_003'
ledger_path=run/'04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER.yaml'
evidence_path=run/'00_SOURCE_INTAKE/evidence/STAGE2_FUNCTIONAL_CHAIN_PREFLIGHT_EVIDENCE.yaml'

def die(m): raise SystemExit(m)
def load(p):
    try: d=yaml.safe_load(p.read_text(encoding='utf-8'))
    except Exception as e: die(f'parse failure {p}: {e}')
    if not isinstance(d,dict): die(f'mapping required: {p}')
    return d

def gitobj(path):
    r=subprocess.run(['git','rev-parse','HEAD:'+str(path)],text=True,capture_output=True)
    if r.returncode: die('git object missing:'+str(path))
    return r.stdout.strip()

locked={
 run/'00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml':'9490f3bcc28c5511bc04d6c3ce53c026e3c4667f',
 run/'00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml':'9668e2307c722ea4cf64f93f07c92da1b3abcc28',
 run/'02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml':'0c067fb8be186a899b42115a82d71312b4014502',
 run/'02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml':'52bb27bf7eb423ddb13bcac5bd34edbcb369de3a',
 run/'02_BASE_BLUEPRINT/CORE-01/VISUAL_BASE_BLUEPRINT.yaml':'8edd134ea4610ab3cb192bca7b3a34ec24ae6368',
 run/'02_BASE_BLUEPRINT/ASSET-01/VISUAL_BASE_BLUEPRINT.yaml':'f09ec9e4ccbedd1487c91592cb1df83ba5e62464',
 run/'03_BLUEPRINT_BINDING/CORE-01/BLUEPRINT_BINDING_MANIFEST.yaml':'8180bda073fcd26e82372e6ae15b256026a5544e',
 run/'03_BLUEPRINT_BINDING/ASSET-01/BLUEPRINT_BINDING_MANIFEST.yaml':'1879d88110a430fa261660ec5052e9468a6adcdd'}
for p,b in locked.items():
    if gitobj(p)!=b: die('predecessor artifact drift:'+str(p))

L=load(ledger_path); E=load(evidence_path)
if L.get('artifact_type')!='FUNCTIONAL_CHAIN_GAP_LEDGER': die('gap ledger artifact_type drift')
if L.get('governance_overlay')!='v2.1.12' or L.get('stage_uid')!='STAGE-02': die('gap ledger governance/stage drift')
if L.get('detector_revision')!='v3-authority-native-semantic-calibrated': die('detector revision drift')
if L.get('status')!='OPEN_BLOCKING_GAPS': die('gap ledger must remain open while gaps exist')
expected={'provider':'GITHUB_ACTIONS','repository_or_project':'steven-gold/orange-one-ai-viedo-v1.0','head_sha':'3d3ab89b2ee8092c22a3cf044c5d5ec57a904dcf','run_id':34759480842,'job_denominator':'15/15','conclusion':'SUCCESS'}
if (L.get('source_ci_receipt') or {})!=expected: die('Stage2 preflight CI receipt drift')
art=L.get('machine_result_artifact') or {}
if art.get('artifact_id')!=10317579755 or art.get('digest')!='sha256:eb06d2ca1227cfff4d97600684d1ffd7f26930ad5ab6dcdd2e9f16e245baaf1f': die('machine artifact receipt drift')
if art.get('functional_completion') is not False or art.get('gap_total')!=171: die('machine result completion/gap total drift')
summary=L.get('summary') or {}
if summary.get('total')!=171 or summary.get('pages')!={'CORE-01':45,'ASSET-01':126}: die('page gap totals drift')
if summary.get('classes')!={'ARCHITECTURE_GAP':133,'INPUT_SOURCE_GAP':34,'AUTHORITY_GAP':4}: die('class totals drift')
expected_cats={'STATE_TRANSITION_LEDGER_FIELD_MISSING':50,'FAILURE_STATE_ERROR_BINDING_MISSING':44,'PAYLOAD_INPUT_CONTRACT_MISSING':34,'POST_ACTION_VALIDATION_NODE_MISSING':18,'AUDIT_EVENT_NODE_MISSING':13,'SUCCESS_NEXT_STATE_BINDING_MISSING':7,'SHARED_OWNER_AUTHORITY_UNRESOLVED':4,'ACTION_WITHOUT_CONTROL_OR_TRIGGER':1}
if summary.get('categories')!=expected_cats: die('category totals drift')
G=L.get('category_groups') or {}
if set(G)!=set(expected_cats): die('category group set drift')
# Validate each compressed group expands to the exact machine gap cardinality.
expanded=0
for cat,count in expected_cats.items():
    group=G[cat]
    subtotal=0
    for page in ('CORE-01','ASSET-01'):
        p=group.get(page)
        if isinstance(p,dict):
            n=p.get('expanded_gap_count')
            if not isinstance(n,int) or n<0: die(f'{cat}/{page} expanded count invalid')
            subtotal+=n
            if 'action_uids' in p and len(p['action_uids'])!=n: die(f'{cat}/{page} action UID cardinality drift')
            if 'transition_uids' in p:
                fields=group.get('required_fields') or []
                if len(p['transition_uids'])*len(fields)!=n: die(f'{cat}/{page} transition expansion drift')
    if subtotal!=count: die(f'{cat} subtotal drift {subtotal}!={count}')
    expanded+=subtotal
if expanded!=171: die('compressed ledger expansion total drift')
pol=L.get('resolution_policy') or {}
if pol.get('functional_completion_claim') is not False or pol.get('authority_gap_ai_guess')!='FORBIDDEN' or pol.get('website_construction_allowed') is not False or pol.get('deployment_allowed') is not False: die('resolution policy drift')
cr=E.get('current_result') or {}
if cr.get('functional_completion_claim') is not False or cr.get('gap_total')!=171 or cr.get('detector_revision')!='v3-authority-native-semantic-calibrated': die('evidence current result drift')
if (cr.get('ci_receipt') or {})!=expected: die('evidence CI receipt drift')
if cr.get('gap_ledger_ref')!='04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER.yaml': die('evidence gap ledger ref drift')
if E.get('website_construction_started') is not False or E.get('deployment_started') is not False: die('website/deploy started during Stage2 gap resolution')
print('PASS: Stage-02 v3 semantic-calibrated gap ledger expands to exact 171 gaps (CORE 45 / ASSET 126)')
print('PASS: ARCHITECTURE=133 INPUT_SOURCE=34 AUTHORITY=4; no false functional completion claimed')
print('PASS: Raw Source/Page/Visual/Binding predecessor bytes remain exact; website/deployment remain blocked')
