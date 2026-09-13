#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, yaml

root = Path('.')
base = root / '00_SOURCE_INTAKE/fresh_run_003'
gap_path = base / '04_PAGE_FUNCTIONAL_CONTRACT/FUNCTIONAL_CHAIN_GAP_LEDGER_R4.yaml'
asset_path = base / '00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'
LOCKED = {
    gap_path: '29855a6aa9940b6ea64ca75d355c60acda3d2b94',
    asset_path: '9668e2307c722ea4cf64f93f07c92da1b3abcc28',
}
PORT_FIELDS = ('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid')
ACTION_VALIDATION_FIELDS = ('success_contract','validation_contract','validator_uid')
RUNTIME_VALIDATION_FIELDS = ('validation','validation_rule','evaluation_rule')
PORT_VALIDATION_FIELDS = ('validation','validation_rule','validator_uid')

def die(msg): raise SystemExit(msg)
def load(path):
    d = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(d, dict): die('mapping required: '+str(path))
    return d
def gitobj(path):
    r = subprocess.run(['git','rev-parse','HEAD:'+str(path)], text=True, capture_output=True)
    if r.returncode: die('git object missing: '+str(path))
    return r.stdout.strip()
def idx(items,key): return {x.get(key):x for x in (items or []) if isinstance(x,dict) and x.get(key)}
def nonempty(v): return v not in (None,'',[],{})
def signals(node, fields):
    if not isinstance(node, dict): return {}
    return {f:node.get(f) for f in fields if nonempty(node.get(f))}

for p,b in LOCKED.items():
    if gitobj(p) != b: die('locked source drift: '+str(p))
G = load(gap_path); A = load(asset_path)
cat = (G.get('category_groups') or {}).get('POST_ACTION_VALIDATION_NODE_MISSING') or {}
grp = cat.get('ASSET-01') or {}
gap_actions = grp.get('action_uids') or []
if cat.get('class') != 'ARCHITECTURE_GAP' or len(gap_actions) != 18 or grp.get('expanded_gap_count') != 18:
    die('R4 validation gap universe must remain exact 18')
summary = G.get('summary') or {}
if (summary.get('categories') or {}).get('POST_ACTION_VALIDATION_NODE_MISSING') != 18:
    die('R4 validation category count drift')
if (summary.get('classes') or {}).get('ARCHITECTURE_GAP') != 133 or summary.get('total') != 167:
    die('R4 totals drift')
reg = A.get('registries') or {}
actions = idx(reg.get('actions'),'action_uid')
ports = idx(reg.get('integration_ports'),'port_uid')
if len(actions) != 44: die('ASSET action registry drift')
rows=[]; detector_resolvable=[]; latent_secondary=[]
for aid in gap_actions:
    a=actions.get(aid)
    if not a: die('gap action missing from ASSET registry: '+aid)
    rb=a.get('runtime_binding') or {}
    refs=[]
    for fld in PORT_FIELDS:
        puid=rb.get(fld)
        if puid:
            refs.append({'field':fld,'port_uid':puid,'port':ports.get(puid)})
    action_sig=signals(a,ACTION_VALIDATION_FIELDS)
    runtime_sig=signals(rb,RUNTIME_VALIDATION_FIELDS)
    port_rows=[]
    for r in refs:
        p=r['port'] or {}
        port_rows.append({'field':r['field'],'port_uid':r['port_uid'],'port_exists':bool(r['port']),'validation_signals':signals(p,PORT_VALIDATION_FIELDS)})
    first_port_sig = port_rows[0]['validation_signals'] if port_rows else {}
    detector_ok = bool(action_sig or runtime_sig or first_port_sig)
    any_port_sig = any(bool(x['validation_signals']) for x in port_rows)
    secondary_only = (not detector_ok) and any_port_sig
    if detector_ok: detector_resolvable.append(aid)
    if secondary_only: latent_secondary.append(aid)
    rows.append({
        'action_uid':aid,
        'binding_kind':rb.get('binding_kind'),
        'action_validation_signals':action_sig,
        'runtime_validation_signals':runtime_sig,
        'referenced_ports':port_rows,
        'detector_resolvable_by_current_page_authority':detector_ok,
        'latent_validation_signal_on_nonprimary_port_only':secondary_only,
        'gap_status_after_inventory':'POTENTIAL_COMPILER_MISS_REVIEW_REQUIRED' if secondary_only else ('RESOLVABLE_BY_EXISTING_DETECTOR' if detector_ok else 'OPEN'),
    })
out_summary={
    'gap_action_total':18,
    'actions_with_action_validation_signal':sum(bool(r['action_validation_signals']) for r in rows),
    'actions_with_runtime_validation_signal':sum(bool(r['runtime_validation_signals']) for r in rows),
    'actions_with_any_port_validation_signal':sum(any(bool(p['validation_signals']) for p in r['referenced_ports']) for r in rows),
    'detector_resolvable_gap_count':len(detector_resolvable),
    'detector_resolvable_action_uids':detector_resolvable,
    'latent_secondary_port_only_count':len(latent_secondary),
    'latent_secondary_port_only_action_uids':latent_secondary,
    'unresolved_gap_count_if_no_latent_successor':18-len(detector_resolvable),
    'inventory_changes_current_gap_count':False,
    'current_post_action_validation_gap_count':18,
    'current_architecture_gap_total':133,
    'current_functional_gap_total':167,
}
out={
    'schema_version':1,
    'artifact_type':'POST_ACTION_VALIDATION_INVENTORY_RESULT',
    'artifact_uid':'FRESH-RUN-003-STAGE2-POST-ACTION-VALIDATION-INVENTORY-V212-R1',
    'governance_overlay':'v2.1.12','run_uid':'FRESH-RUN-003','stage_uid':'STAGE-02',
    'source_gap_ledger_git_blob':LOCKED[gap_path],
    'source_asset_authority_git_blob':LOCKED[asset_path],
    'detector_rule':{
        'action_fields':list(ACTION_VALIDATION_FIELDS),
        'runtime_binding_fields':list(RUNTIME_VALIDATION_FIELDS),
        'primary_resolved_port_fields':list(PORT_VALIDATION_FIELDS),
        'port_reference_order':list(PORT_FIELDS),
        'secondary_port_scan_added_for_parser_miss_detection':True,
    },
    'rows':rows,'summary':out_summary,
    'functional_completion_claim':False,'website_construction_allowed':False,'deployment_allowed':False,
}
Path('stage2_post_action_validation_inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: exact 18-action post-action validation inventory compiled')
print('PASS: primary detector semantics reproduced and all referenced ports additionally scanned for latent parser misses')
print('PASS: inventory never mutates Current gap totals')
print(json.dumps(out_summary,ensure_ascii=False,sort_keys=True))
