#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '00_SOURCE_INTAKE/fresh_run_003/04_PAGE_FUNCTIONAL_CONTRACT'
EXT = BASE / 'EXTERNAL_AUTHORITY'
CURRENT_MAP = BASE / 'SHARED_OWNER_PORT_MAP.yaml'
R3_MAP = BASE / 'SHARED_OWNER_PORT_MAP_R3.yaml'
EVIDENCE = EXT / 'STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE.yaml'
MANIFEST = EXT / 'ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'
SHARED = EXT / 'GAP-006/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml'
RAW_ASSET = ROOT / '00_SOURCE_INTAKE/fresh_run_003/00_SOURCE_INTAKE/RAW_SOURCE/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml'

EXPECTED = {
    'ASSET-01-ACT-CORRECTION-GENERATE': ('generateCorrectionScriptCandidate','/v1/state-commands/correctionscript/generate','api:generateCorrectionScriptCandidate','public.correction_script_versions'),
    'ASSET-01-ACT-CORRECTION-APPROVE': ('approveCorrectionScriptCandidate','/v1/state-commands/correctionscript/approve','api:approveCorrectionScriptCandidate','public.correction_script_versions'),
    'ASSET-01-ACT-RESTORE-AS-NEW': ('restoreAssetVersionAsNewDraft','/v1/state-commands/assetversion/restoreasnewdraft','api:restoreAssetVersionAsNewDraft','public.asset_version_restore_drafts'),
    'ASSET-01-ACT-VERSION-LOCK': ('lockAssetVersion','/v1/state-commands/assetversion/lock','api:lockAssetVersion','public.production_output_version_locks'),
}


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)


def load(path):
    if not path.is_file():
        die(f'MISSING:{path.relative_to(ROOT)}')
    try:
        obj = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as exc:
        die(f'YAML_PARSE:{path.relative_to(ROOT)}:{exc!r}')
    if not isinstance(obj, dict):
        die(f'MAPPING_REQUIRED:{path.relative_to(ROOT)}')
    return obj


def gitobj(path):
    rel = str(path.relative_to(ROOT))
    cp = subprocess.run(['git','rev-parse','HEAD:' + rel], cwd=str(ROOT), text=True, capture_output=True)
    if cp.returncode:
        die('GIT_OBJECT_MISSING:' + rel)
    return cp.stdout.strip()


def strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)
    elif obj is not None:
        yield str(obj)

# Immutable/current predecessor and exact recovered Authority bytes.
locked = {
    CURRENT_MAP: '93f395264d7deec54dc86ddc286e484a8368c239',
    RAW_ASSET: '9668e2307c722ea4cf64f93f07c92da1b3abcc28',
    MANIFEST: '465329b6fb19b8e44c3083a9f280015ee95cc55c',
    SHARED: '12dbdf59a60df5b1cb3d3b18666209c05bb0c0a3',
    EVIDENCE: 'ff99fd8c48f4593c5ef5cdeab1d49c5caa027cfd',
    EXT / 'GAP-005/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml': '12ef6d233e09f84571dd5d694ae8e3789ae70502',
    EXT / 'GAP-008/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml': 'b09b7ca50313172ea021d9da0c8d57f2942f7b19',
    EXT / 'GAP-008/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml': 'dd9f05e295af57cc833e90d1a12030c8198580c6',
    EXT / 'GAP-008/operation_registry.yaml': '7d234cc2f2f831b82f2007403c71d4008b46a012',
    EXT / 'ASYNC/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml': 'ac3619b3bc547ce06f244c239fa69d3cac78da76',
}
for path, expected_blob in locked.items():
    actual = gitobj(path)
    if actual != expected_blob:
        die(f'LOCKED_BLOB_DRIFT:{path.relative_to(ROOT)}:expected={expected_blob}:actual={actual}')

current_map = load(CURRENT_MAP)
r3 = load(R3_MAP)
manifest = load(MANIFEST)
shared = load(SHARED)
evidence = load(EVIDENCE)
asset = load(RAW_ASSET)

if current_map.get('artifact_type') != 'SHARED_OWNER_PORT_MAP' or current_map.get('shared_owner_binding_count') != 4:
    die('CURRENT_SHARED_OWNER_MAP_IDENTITY_DRIFT')
if current_map.get('external_authority_resolution_performed') is not False:
    die('CURRENT_PREDECESSOR_MUST_REMAIN_PRESERVED_REFERENCE_ONLY')
current_bindings = current_map.get('bindings') or []
if len(current_bindings) != 4:
    die('CURRENT_PREDECESSOR_BINDING_DENOMINATOR_DRIFT')
for row in current_bindings:
    action = row.get('action_uid')
    if action not in EXPECTED:
        die(f'UNEXPECTED_CURRENT_PREDECESSOR_ACTION:{action}')
    if row.get('page_uid') != 'ASSET-01' or row.get('shared_authority_id') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or row.get('shared_operation_id') != EXPECTED[action][0] or row.get('resolution_status') != 'PRESERVED_EXTERNAL_AUTHORITY_REFERENCE':
        die(f'CURRENT_PREDECESSOR_BINDING_DRIFT:{action}')

if (shared.get('authority_id'), str(shared.get('version')), shared.get('status')) != ('ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY','1.0','CURRENT_CONTRACT'):
    die('SHARED_AUTHORITY_IDENTITY_DRIFT')
manifest_text = set(strings(manifest))
required_manifest_path = 'authority/runtime/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml'
if required_manifest_path not in manifest_text:
    die('GAP006_AUTHORITY_NOT_CURRENT_MANIFEST_MEMBER')
if evidence.get('artifact_type') != 'STAGE2_EXTERNAL_AUTHORITY_MATERIALIZATION_EVIDENCE' or evidence.get('status') != 'CURRENT_PARTIAL_RESOLUTION':
    die('MATERIALIZATION_EVIDENCE_IDENTITY_DRIFT')
if (evidence.get('source_pin') or {}).get('commit_sha') != '6c8a0c3334ccd17942ba14079976fb295859a43c':
    die('MATERIALIZATION_SOURCE_PIN_DRIFT')
ma = evidence.get('materialized_authorities') or {}
if (ma.get('GAP-006') or {}).get('functional_authority_gap_resolved') is not True:
    die('GAP006_MATERIALIZATION_NOT_VERIFIED')
if (ma.get('GAP-006') or {}).get('port_uid_requirement') != 'NOT_APPLICABLE_BY_BINDING_KIND':
    die('GAP006_PORT_APPLICABILITY_DRIFT')

ops = shared.get('operations') or {}
raw_actions = {x.get('action_uid'): x for x in (((asset.get('registries') or {}).get('actions')) or []) if isinstance(x, dict)}
for action, (opid, route, api, owner) in EXPECTED.items():
    op = ops.get(opid) or {}
    binding = (op.get('page_bindings') or {}).get('ASSET-01') or {}
    if binding.get('action_uid') != action:
        die(f'AUTHORITY_PAGE_BINDING_DRIFT:{action}')
    if (op.get('route'), op.get('api_resource_key'), op.get('canonical_owner')) != (route, api, owner):
        die(f'AUTHORITY_RUNTIME_BINDING_DRIFT:{action}')
    raw_binding = (raw_actions.get(action) or {}).get('runtime_binding') or {}
    if raw_binding.get('binding_kind') != 'SHARED_OPERATION_REFERENCE' or raw_binding.get('shared_authority_id') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or raw_binding.get('shared_operation_id') != opid:
        die(f'RAW_SHARED_OPERATION_REFERENCE_DRIFT:{action}')
    if 'port_uid' in raw_binding:
        die(f'RAW_SHARED_OPERATION_REFERENCE_FAKE_PORT:{action}')

if r3.get('artifact_type') != 'SHARED_OWNER_PORT_MAP' or r3.get('artifact_uid') != 'FRESH-RUN-003-STAGE2-SHARED-OWNER-PORT-MAP-R3' or r3.get('status') != 'RESOLVED_AUTHORITY_GAP_CURRENT_SUCCESSOR':
    die('R3_SUCCESSOR_IDENTITY_DRIFT')
if (r3.get('successor_of') or {}).get('git_blob') != '93f395264d7deec54dc86ddc286e484a8368c239':
    die('R3_SUCCESSOR_CURRENT_PREDECESSOR_DRIFT')
if (r3.get('resolution_evidence') or {}).get('git_blob') != 'ff99fd8c48f4593c5ef5cdeab1d49c5caa027cfd':
    die('R3_SUCCESSOR_EVIDENCE_DRIFT')
if (r3.get('historical_verified_successor') or {}).get('git_blob') != '65f821ad766994716f4336e961b1b160b5aac457':
    die('R3_HISTORICAL_PROVENANCE_DRIFT')
sem = r3.get('binding_semantics') or {}
if sem.get('binding_kind') != 'SHARED_OPERATION_REFERENCE' or sem.get('integration_port_uid_required') is not False or sem.get('resolved_port_uid') is not None or sem.get('resolved_port_uid_status') != 'NOT_APPLICABLE_BY_BINDING_KIND':
    die('R3_BINDING_SEMANTICS_DRIFT')
consumers = r3.get('consumers') or []
if len(consumers) != 4 or {x.get('action_uid') for x in consumers} != set(EXPECTED):
    die('R3_CONSUMER_DENOMINATOR_DRIFT')
for row in consumers:
    action = row.get('action_uid')
    opid, route, api, owner = EXPECTED[action]
    if row.get('page_uid') != 'ASSET-01' or row.get('binding_kind') != 'SHARED_OPERATION_REFERENCE' or row.get('resolved_owner_uid') != 'ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or row.get('resolved_operation_uid') != opid:
        die(f'R3_OWNER_OPERATION_DRIFT:{action}')
    if row.get('resolved_port_uid') is not None or row.get('port_uid_status') != 'NOT_APPLICABLE_BY_BINDING_KIND':
        die(f'R3_FAKE_PORT:{action}')
    if (row.get('route'), row.get('api_resource_key'), row.get('canonical_owner'), row.get('status')) != (route, api, owner, 'RESOLVED_EXACT_AUTHORITY'):
        die(f'R3_RUNTIME_DETAIL_DRIFT:{action}')
summary = r3.get('resolution_summary') or {}
if summary.get('resolved_consumer_total') != 4 or summary.get('unresolved_consumer_total') != 0 or summary.get('resolved_gap_uid') != 'GAP-006' or summary.get('raw_gap_signature_detail') != 'GAP-006: ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY' or summary.get('ai_inference_used') is not False or summary.get('raw_source_mutated') is not False or summary.get('functional_completion_claim') is not False:
    die('R3_RESOLUTION_SUMMARY_DRIFT')
policy = r3.get('policy') or {}
if policy.get('current_specification_mutated') is not False or policy.get('stage1_raw_source_mutated') is not False or policy.get('stage2_exit_allowed') is not False or policy.get('website_construction_allowed') is not False or policy.get('deployment_allowed') is not False:
    die('R3_FAIL_CLOSED_POLICY_DRIFT')

print('PASS: Current SHARED_OWNER_PORT_MAP remains the preserved-reference predecessor; no rollback to historical predecessor bytes')
print('PASS: recovered GAP-006 Authority and materialization evidence remain exact locked blobs and Current-Manifest member')
print('PASS: R3 successor resolves exactly four ASSET shared-operation consumers with no invented port_uid and no AI inference')
print('PASS: Stage-01 Raw Source and Current Specification remain unchanged; Stage-02 exit/website/deployment remain blocked')
