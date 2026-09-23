#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.github' / 'governance-source' / 'active' / 'source'
GOV = SOURCE / '09_TESTS' / 'governance'
VALIDATOR = GOV / 'validate_governance.py'
CHECKSUMS = SOURCE / 'CHECKSUMS.sha256'
TRUST_ROOT = Path('/tmp/acpos-governance-external-trust-root.json')
RESULT = ROOT / '.github' / 'governance-source' / 'FULL_LINE_SYSTEM_GATE_RESULT.json'

EXPECTED_CHECKSUMS_SHA256 = '274c2d5b85a04c165ea56adc46b5ee831037af827aff982cb6e50d82b059db5c'
EXPECTED_SEMANTIC_CONTENT_HASH = '543fcfd8c3f71a87e9f82efafdc479a55acb6eb9728aba20e784cd022ecd19d9'
EXPECTED_SOURCE_ZIP_SHA256 = 'caddc2e7bf325cdbf9ba2c2227ebf0d0273f0eaf8ba6fef6be1be8ac0217e0f0'
EXPECTED_BUNDLE_SHA256 = 'c3b2828a2864898f43b0f9437b7105afa6f457815710cc36e3ddf4184c5902cb'
EXPECTED_SELECTED_PROFILE_STEP_UIDS = [f'STAGE-{i:02}' for i in range(1, 12)]
EXPECTED_SELECTED_PROFILE_STEP_NAMES = [
    'SOURCE_INTAKE_AND_BASE_BLUEPRINT','PAGE_FUNCTIONAL_CONTRACT','VISUAL_DESIGN','FOUNDATION_FREEZE',
    'IMPLEMENTATION','VERIFICATION_QA','BUILD_RELEASE_CANDIDATE','STAGING','PRODUCTION_CUTOVER',
    'PRODUCTION_ACCEPTANCE','CLOSURE_OPERATIONS',
]
EXPECTED_SUITES = {'test_high_pressure_hardening.py': {'total': 25, 'passed_expectations': 25},
 'test_reference_semantic_guard.py': {'semantic_cases_total': 28,
                                      'semantic_passed_expectations': 28,
                                      'fuzz_total': 46,
                                      'fuzz_blocked': 46,
                                      'escaped': 0},
 'test_execution_load_guard.py': {'total': 14, 'passed_expectations': 14},
 'test_prefomal_stress_repairs.py': {'total': 21, 'passed_expectations': 21},
 'test_stage1_source_to_blueprint_minimal_control.py': {'total': 45, 'passed_expectations': 45},
 'test_v2_1_0_regressions.py': {'total': 12, 'passed_expectations': 12},
 'test_v2_1_0_post_v1_8_regressions.py': {'total': 6, 'passed_expectations': 6},
 'test_bugfix_regressions.py': {'total': 30, 'passed_expectations': 30},
 'test_v2_1_7_phase_authority_bugfix.py': {'total': 25, 'passed_expectations': 25},
 'test_v2_1_8_successor_evidence_sync_bugfix.py': {'total': 24, 'passed_expectations': 24},
 'test_v2_1_9_evidence_state_closure.py': {'total': 24, 'passed_expectations': 24},
 'test_v2_1_10_closure_evidence_continuity.py': {'total': 43, 'passed_expectations': 43},
 'test_v2_1_11_binding_authority_receipt_schema.py': {'total': 54, 'passed_expectations': 54},
 'test_v2_1_12_successor_state_evidence_parse.py': {'total': 60, 'passed_expectations': 60},
 'test_v2_1_13_stage_execution_invariants.py': {'total': 32, 'passed_expectations': 32},
 'test_v2_1_14_test_feedback_spec_evolution.py': {'total': 21, 'passed_expectations': 21},
 'test_v2_1_14_product_neutral_entity_lifecycle.py': {'total': 68, 'passed_expectations': 68}}

errors: list[str] = []

def block(msg: str) -> None:
    errors.append(msg)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

# Build an external trust-root outside the source tree, anchored by immutable hashes copied
# from the verified v2.1.15 package, never by unverified live source content alone.
if not CHECKSUMS.is_file():
    block('CHECKSUMS_MISSING')
elif sha256(CHECKSUMS) != EXPECTED_CHECKSUMS_SHA256:
    block('EXTERNAL_ANCHOR_CHECKSUM_MANIFEST_SHA_MISMATCH')

package_files: list[dict[str, str]] = []
if not errors:
    for raw in CHECKSUMS.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line:
            continue
        digest, rel = line.split(None, 1)
        package_files.append({'path': rel.lstrip('* '), 'sha256': digest})
    package_files.append({'path': 'CHECKSUMS.sha256', 'sha256': EXPECTED_CHECKSUMS_SHA256})
    if len(package_files) != 75:
        block(f'EXTERNAL_TRUST_FILE_COUNT expected=75 actual={len(package_files)}')

trust = {
    'schema_version': 1,
    'artifact_type': 'NON_NORMATIVE_EXTERNAL_TRUST_ROOT',
    'normative_authority': False,
    'trust_model': 'EXTERNAL_IMMUTABLE_PACKAGE_HASH_SET',
    'source_zip_sha256': EXPECTED_SOURCE_ZIP_SHA256,
    'deterministic_bundle_sha256': EXPECTED_BUNDLE_SHA256,
    'semantic_authority_content_hash': EXPECTED_SEMANTIC_CONTENT_HASH,
    'package_files': package_files,
}
TRUST_ROOT.write_text(json.dumps(trust, indent=2) + '\n', encoding='utf-8')

# Pin the active semantic authority and lifecycle denominator before executing any suite.
semantic_path = SOURCE / '10_REGISTRY' / 'SEMANTIC_AUTHORITY_BASELINE.yaml'
stage_path = SOURCE / '10_REGISTRY' / 'GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
try:
    semantic = yaml.safe_load(semantic_path.read_text(encoding='utf-8')) or {}
    stages = yaml.safe_load(stage_path.read_text(encoding='utf-8')) or {}
except Exception as exc:
    block(f'REGISTRY_PARSE_ERROR:{exc!r}')
    semantic, stages = {}, {}
if semantic.get('content_hash') != EXPECTED_SEMANTIC_CONTENT_HASH:
    block('SEMANTIC_AUTHORITY_CONTENT_HASH_MISMATCH')
records = stages.get('stages') or []
actual_stage_uids = [x.get('stage_uid') for x in records]
actual_stage_names = [x.get('name') or x.get('stage_name') for x in records]
if actual_stage_uids != EXPECTED_SELECTED_PROFILE_STEP_UIDS:
    block(f'SELECTED_PROFILE_STEP_UID_SET_MISMATCH:{actual_stage_uids}')
if actual_stage_names != EXPECTED_SELECTED_PROFILE_STEP_NAMES:
    block(f'SELECTED_PROFILE_STEP_NAME_SET_MISMATCH:{actual_stage_names}')
mandatory_assets = semantic.get('mandatory_regression_assets') or []
if len(mandatory_assets) != 17:
    block(f'MANDATORY_ASSET_COUNT_MISMATCH expected=17 actual={len(mandatory_assets)}')
asset_names = [Path(x.get('path','')).name for x in mandatory_assets]
if set(asset_names) != set(EXPECTED_SUITES):
    block(f'MANDATORY_ASSET_SET_MISMATCH actual={asset_names}')

# Collection isolation contract is deliberately not one of the 17 standalone JSON suites,
# but it is a required prerequisite and must execute successfully.
collection = GOV / 'test_pytest_collection_contract.py'
env = dict(os.environ)
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['PYTHONPYCACHEPREFIX'] = '/tmp/acpos-governance-pycache'
env['WEB_GOVERNANCE_TRUST_ROOT'] = str(TRUST_ROOT)
if not errors:
    try:
        cp = subprocess.run([sys.executable, str(collection)], cwd=str(GOV), env=env, capture_output=True, text=True, timeout=120)
        if cp.returncode != 0 or cp.stdout.strip() != 'PASS':
            block(f'COLLECTION_ISOLATION_CONTRACT_FAILED rc={cp.returncode} stdout={cp.stdout[-500:]} stderr={cp.stderr[-500:]}')
    except subprocess.TimeoutExpired:
        block('COLLECTION_ISOLATION_CONTRACT_TIMEOUT')

preformal = None
if not errors:
    try:
        cp = subprocess.run(
            [sys.executable, str(VALIDATOR), '--mode', 'PRE_FORMAL_DEFINITION_AUDIT'],
            cwd=str(GOV), env=env, capture_output=True, text=True, timeout=2400,
        )
        try:
            preformal = json.loads(cp.stdout)
        except Exception as exc:
            block(f'PREFORMAL_INVALID_JSON:{exc!r}:stdout_tail={cp.stdout[-1000:]}')
        if cp.returncode != 0:
            block(f'PREFORMAL_RETURN_CODE:{cp.returncode}')
    except subprocess.TimeoutExpired:
        block('PREFORMAL_TIMEOUT')

if isinstance(preformal, dict):
    if preformal.get('status') != 'PASS':
        block(f'PREFORMAL_STATUS:{preformal.get("status")}')
    if preformal.get('checks_total') != 20:
        block(f'PREFORMAL_CHECK_COUNT expected=20 actual={preformal.get("checks_total")}')
    if preformal.get('pass_count') != 20:
        block(f'PREFORMAL_PASS_COUNT expected=20 actual={preformal.get("pass_count")}')
    if preformal.get('blocking_failures') != 0:
        block(f'PREFORMAL_BLOCKING_FAILURES:{preformal.get("blocking_failures")}')
    checks = {c.get('check_id'): c for c in (preformal.get('checks') or [])}
    required_checks = {
        'external_trust_root','parser_hygiene','section_registry','construction_artifact_index',
        'execution_governance_load','cleanup_protection','lifecycle_stage_contract','management_contract',
        'reference_semantics','program_artifact_instance_guard','current_test_evidence_sync',
        'evidence_state_closure','closure_evidence_continuity','stage_execution_invariants',
        'test_feedback_spec_evolution','product_neutral_entity_lifecycle',
        'acceptance_blueprint_compiled_baseline','root_manifest',
        'mandatory_regression_and_package_integrity','candidate_truth',
    }
    if set(checks) != required_checks:
        block(f'PREFORMAL_CHECK_SET_MISMATCH missing={sorted(required_checks-set(checks))} extra={sorted(set(checks)-required_checks)}')
    for cid in required_checks:
        if checks.get(cid, {}).get('status') != 'PASS':
            block(f'PREFORMAL_CHECK_FAILED:{cid}')
    mandatory = checks.get('mandatory_regression_and_package_integrity') or {}
    if mandatory.get('suite_count') != 17:
        block(f'MANDATORY_RUNTIME_SUITE_COUNT expected=17 actual={mandatory.get("suite_count")}')
    suites = {x.get('suite'): x for x in (mandatory.get('suites') or [])}
    if set(suites) != set(EXPECTED_SUITES):
        block(f'MANDATORY_RUNTIME_SUITE_SET_MISMATCH actual={sorted(suites)}')
    for name, expected in EXPECTED_SUITES.items():
        rec = suites.get(name) or {}
        if rec.get('ok') is not True or rec.get('returncode') != 0 or rec.get('failure') not in (None, ''):
            block(f'MANDATORY_SUITE_NOT_PASS:{name}:{rec}')
            continue
        for key, value in expected.items():
            if rec.get(key) != value:
                block(f'MANDATORY_DENOMINATOR_MISMATCH:{name}:{key}:expected={value}:actual={rec.get(key)}')

# A full-system definition gate must not mutate the verified source package or leave runtime residue.
residual = [p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file() and (p.suffix == '.pyc' or '__pycache__' in p.parts)]
if residual:
    block('SOURCE_RUNTIME_RESIDUAL:' + ','.join(residual))

result = {
    'artifact_type': 'NON_NORMATIVE_FULL_LINE_SYSTEM_GATE_EVIDENCE',
    'mode': 'SYSTEM_ROUND_1_FULL_LINE_HIGH_PRESSURE',
    'source_zip_sha256': EXPECTED_SOURCE_ZIP_SHA256,
    'deterministic_source_bundle_sha256': EXPECTED_BUNDLE_SHA256,
    'lifecycle_stage_count': len(records),
    'lifecycle_stage_uids': actual_stage_uids,
    'mandatory_suite_count': 17,
    'mandatory_expected_denominators': EXPECTED_SUITES,
    'collection_isolation': 'PASS' if not any(x.startswith('COLLECTION_') for x in errors) else 'FAIL',
    'preformal': preformal,
    'source_runtime_residual_count': len(residual),
    'result': 'PASS' if not errors else 'FAIL',
    'errors': errors,
    'actual_product_stage_test_started': False,
}
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if errors:
    for err in errors:
        print('BLOCK:', err, file=sys.stderr)
    raise SystemExit(1)

print('PASS: lifecycle stages=11/11 exact')
print('PASS: collection isolation contract')
print('PASS: official PRE_FORMAL_DEFINITION_AUDIT checks=20/20')
print('PASS: mandatory regression suites=17/17 with exact denominators')
print('PASS: destructive/high-pressure regressions terminally passed; no skip/timeout accepted')
print('PASS: source runtime residual=0')
print('PASS: SYSTEM_ROUND_1_FULL_LINE_HIGH_PRESSURE')
