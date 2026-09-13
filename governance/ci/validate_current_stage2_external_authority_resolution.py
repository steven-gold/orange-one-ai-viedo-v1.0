#!/usr/bin/env python3
from pathlib import Path
import subprocess
import yaml

root=Path('.')
base=root/'00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
ext=base/'EXTERNAL_AUTHORITY'
evidence=ext/'STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml'
r2=base/'SHARED_OWNER_PORT_MAP_R2.yaml'
r1=base/'SHARED_OWNER_PORT_MAP.yaml'
raw_asset=root/'00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'

def die(m): raise SystemExit(m)
def load(p):
    try: d=yaml.safe_load(p.read_text(encoding='utf-8'))
    except Exception as e: die(f'parse failure {p}: {e}')
    if not isinstance(d,dict): die(f'mapping required {p}')
    return d
def gitobj(p):
    r=subprocess.run(['git','rev-parse','HEAD:'+str(p)],text=True,capture_output=True)
    if r.returncode: die(f'git object missing {p}')
    return r.stdout.strip()

# Preserve immutable prior/current evidence while adding an explicit successor.
locks={
    r1:'c683e76363323e0275e2bc1a3b9dcdb76243e597',
    raw_asset:'9668e2307c722ea4cf64f93f07c92da1b3abcc28',
    base/'STAGE2_DEPENDENCY_MAP.yaml':'59acc61d0a6db969bbd08328322b7f5214e6f5cf',
    base/'STATE_TRANSITION_LEDGER.yaml':'f08d7c637a51e29dab01dc8378555d6bc4c9e635',
}
for p,b in locks.items():
    if gitobj(p)!=b: die(f'immutable predecessor drift {p}')

# Exact Authority blobs are re-materialized byte-for-byte from pinned source commit.
source_blobs={
    ext/'ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml':'465329b6fb19b8e44c3083a9f280015ee95cc55c',
    ext/'GAP-005/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml':'12ef6d233e09f84571dd5d694ae8e3789ae70502',
    ext/'GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml':'12dbdf59a60df5b1cb3d3b18666209c05bb0c0a3',
    ext/'GAP-008/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml':'b09b7ca50313172ea021d9da0c8d57f2942f7b19',
    ext/'GAP-008/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml':'dd9f05e295af57cc833e90d1a12030c8198580c6',
    ext/'GAP-008/operation_registry.yaml':'7d234cc2f2f831b82f2007403c71d4008b46a012',
    ext/'ASYNC/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml':'ac3619b3bc547ce06f244c239fa69d3cac78da76',
}
for p,b in source_blobs.items():
    if gitobj(p)!=b: die(f'external Authority materialization drift {p}')

E=load(evidence); M=load(r2); A=load(source_blobs.keys().__iter__().__next__())
manifest=load(ext/'ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml')
shared=load(ext/'GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml')
asset=load(raw_asset)

if E.get('artifact_type')!='STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE' or E.get('status')!='CURRENT_PARTIAL_RESOLUTION': die('evidence identity/status drift')
if (E.get('source_pin') or {}).get('commit_sha')!='6c8a0c3334ccd17942ba14079976fb295859a43c': die('source pin drift')
ma=E.get('materialized_authorities') or {}
if set(ma)!={'GAP-005','GAP-006','GAP-008','ASYNC-QUEUE'}: die('materialized Authority coverage drift')
if ma['GAP-006'].get('functional_authority_gap_resolved') is not True or ma['GAP-006'].get('port_uid_requirement')!='NOT_APPLICABLE_BY_BINDING_KIND': die('GAP-006 resolution semantics drift')
for gap in ('GAP-005','GAP-008'):
    if ma[gap].get('s061_lifecycle_closure_claim') is not False: die(f'{gap} illegal S061 bulk closure')
if ma['ASYNC-QUEUE'].get('s061_lifecycle_closure_claim') is not False: die('async queue illegal S061 bulk closure')

current=manifest.get('current_authority_set') or {}
required_current={
 'authority/runtime/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml',
 'authority/runtime/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml',
 'authority/global/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml',
 'authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml',
 'authority/pages/admin/AIAPI-01/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml',
}
manifest_paths=set()
for v in current.values():
    if isinstance(v,list): manifest_paths.update(x for x in v if isinstance(x,str))
if not required_current.issubset(manifest_paths): die('required external Authority is not in Current Authority Manifest')

if (shared.get('authority_id'),str(shared.get('version')),shared.get('status')) != ('ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY','1.0','CURRENT_CONTRACT'): die('shared Authority identity drift')
ops=shared.get('operations') or {}
expected={
 'ASSET-01-ACT-CORRECTION-GENERATE':('generateCorrectionScriptCandidate','/v1/state-commands/correctionscript/generate','api:generateCorrectionScriptCandidate','public.correction_script_versions'),
 'ASSET-01-ACT-CORRECTION-APPROVE':('approveCorrectionScriptCandidate','/v1/state-commands/correctionscript/approve','api:approveCorrectionScriptCandidate','public.correction_script_versions'),
 'ASSET-01-ACT-RESTORE-AS-NEW':('restoreAssetVersionAsNewDraft','/v1/state-commands/assetversion/restoreasnewdraft','api:restoreAssetVersionAsNewDraft','public.asset_version_restore_drafts'),
 'ASSET-01-ACT-VERSION-LOCK':('lockAssetVersion','/v1/state-commands/assetversion/lock','api:lockAssetVersion','public.production_output_version_locks'),
}
for action,(opid,route,api,owner) in expected.items():
    o=ops.get(opid) or {}
    pb=(o.get('page_bindings') or {}).get('ASSET-01') or {}
    if pb.get('action_uid')!=action: die(f'{action} Authority page binding drift')
    if (o.get('route'),o.get('api_resource_key'),o.get('canonical_owner'))!=(route,api,owner): die(f'{action} Authority runtime binding drift')

# Raw Source itself declares these consumers as SHARED_OPERATION_REFERENCE and names only shared authority + operation.
raw_actions={x.get('action_uid'):x for x in ((asset.get('registries') or {}).get('actions') or [])}
for action,(opid,_,_,_) in expected.items():
    rb=(raw_actions.get(action) or {}).get('runtime_binding') or {}
    if rb.get('binding_kind')!='SHARED_OPERATION_REFERENCE' or rb.get('shared_authority_id')!='ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or rb.get('shared_operation_id')!=opid: die(f'{action} Raw Source shared operation identity drift')
    if 'port_uid' in rb: die(f'{action} Raw Source unexpectedly invents a shared-operation port')

if M.get('artifact_type')!='SHARED_OWNER_PORT_MAP' or M.get('operation_uid')!='SHARED_OWNER_PORT_RESOLVE' or M.get('status')!='RESOLVED_AUTHORITY_GAP': die('R2 shared owner successor identity drift')
if (M.get('successor_of') or {}).get('git_blob')!='c683e76363323e0275e2bc1a3b9dcdb76243e597': die('R2 predecessor binding drift')
if (M.get('resolution_evidence') or {}).get('git_blob')!='ff99fd8c48f4593c5ef5cdeab1d49c5caa027cfd': die('R2 evidence binding drift')
bs=M.get('binding_semantics') or {}
if bs.get('binding_kind')!='SHARED_OPERATION_REFERENCE' or bs.get('integration_port_uid_required') is not False or bs.get('resolved_port_uid') is not None or bs.get('resolved_port_uid_status')!='NOT_APPLICABLE_BY_BINDING_KIND': die('shared operation port applicability drift')
cons=M.get('consumers') or []
if len(cons)!=4: die('R2 consumer count drift')
for c in cons:
    action=c.get('action_uid')
    if action not in expected: die(f'unexpected R2 consumer {action}')
    opid,route,api,owner=expected[action]
    if c.get('resolved_owner_uid')!='ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or c.get('resolved_operation_uid')!=opid: die(f'{action} owner/operation not exact')
    if c.get('resolved_port_uid') is not None or c.get('port_uid_status')!='NOT_APPLICABLE_BY_BINDING_KIND': die(f'{action} fake port introduced')
    if (c.get('route'),c.get('api_resource_key'),c.get('canonical_owner'))!=(route,api,owner) or c.get('status')!='RESOLVED_EXACT_AUTHORITY': die(f'{action} resolved Authority detail drift')
summary=M.get('resolution_summary') or {}
if summary.get('resolved_consumer_total')!=4 or summary.get('unresolved_consumer_total')!=0 or summary.get('candidate_successor_functional_gap_total')!=167 or summary.get('gap_ledger_supersession_required_before_count_becomes_current') is not True or summary.get('functional_completion_claim') is not False: die('R2 resolution summary drift')
if (M.get('policy') or {}).get('website_construction_allowed') is not False or (M.get('policy') or {}).get('deployment_allowed') is not False: die('R2 construction/deployment block drift')

print('PASS: pinned external Authority blobs are materialized byte-for-byte and remain Current-Manifest members')
print('PASS: GAP-006 four ASSET consumers exactly match Current shared Authority owner + operation bindings')
print('PASS: SHARED_OPERATION_REFERENCE does not invent a port_uid; port is explicitly N/A by binding kind')
print('PASS: GAP-005/GAP-008 Authority evidence is located without bulk-closing unresolved S061 lifecycle fields')
print('PASS: R2 is a successor only; 167 remains candidate until functional Gap Ledger supersession is materialized and validated')
