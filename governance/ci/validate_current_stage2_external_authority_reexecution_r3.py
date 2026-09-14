#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
LATEST = ROOT / 'governance/test/stage02/STAGE02_LATEST_TEST_EVIDENCE.json'
STATE = ROOT / 'governance/test/ACTIVE_STATE.yaml'
REGRESSION = ROOT / 'governance/test/stage02/STAGE02_DEFECT_SIGNATURE_REGRESSION_R3.yaml'
RESULT = ROOT / '.github/stage02-test/STAGE02_EXTERNAL_AUTHORITY_REEXECUTION_RESULT_R3.json'


def die(msg):
    print('BLOCK:', msg, file=sys.stderr)
    raise SystemExit(1)

for path in (LATEST, STATE, REGRESSION, RESULT):
    if not path.is_file():
        die('MISSING:' + str(path.relative_to(ROOT)))
latest = json.loads(LATEST.read_text(encoding='utf-8'))
result = json.loads(RESULT.read_text(encoding='utf-8'))
state = yaml.safe_load(STATE.read_text(encoding='utf-8')) or {}
reg = yaml.safe_load(REGRESSION.read_text(encoding='utf-8')) or {}
if latest != result:
    die('LATEST_AND_R3_RESULT_DIVERGED')
expected = {
    'reexecution_cycle': 'R3_EXTERNAL_AUTHORITY_AWARE',
    'result': 'BLOCKED',
    'stage_exit_allowed': False,
    'raw_discovery_gap_total': 171,
    'materialized_product_functional_elimination_count': 17,
    'materialized_external_authority_elimination_count': 4,
    'materialized_functional_elimination_count': 21,
    'fresh_total_elimination_count': 21,
    'fresh_functional_gap_total': 150,
    'effective_shared_owner_external_gap_count': 0,
    'preserved_external_authority_union_count': 8,
    'current_specification_mutated': False,
    'stage1_raw_source_mutated': False,
    'ai_autofill_used': False,
    'inference_used': False,
    'website_construction_allowed': False,
    'deployment_allowed': False,
}
for key, value in expected.items():
    if latest.get(key) != value:
        die(f'R3_RESULT_FIELD_DRIFT:{key}:expected={value!r}:actual={latest.get(key)!r}')
pages = latest.get('pages') or {}
if set(pages) != {'CORE-01','ASSET-01'}:
    die('R3_PAGE_DENOMINATOR_DRIFT')
if (pages['CORE-01'].get('functional_chain_effective_r3_scan') or {}).get('gap_count') != 40:
    die('R3_CORE_EFFECTIVE_COUNT_DRIFT')
if (pages['ASSET-01'].get('functional_chain_effective_r3_scan') or {}).get('gap_count') != 110:
    die('R3_ASSET_EFFECTIVE_COUNT_DRIFT')
execution = state.get('execution') or {}
if execution.get('current_stage') != 'STAGE-02-TESTED-BLOCKED' or (execution.get('stage2') or {}).get('result') != 'TEST_EXECUTED_BLOCKED':
    die('R3_STATE_NOT_BLOCKED')
if execution.get('website_construction_allowed') is not False or execution.get('deployment_allowed') is not False:
    die('R3_STATE_FAIL_CLOSED_DRIFT')
attempt = state.get('stage02_active_attempt') or {}
if attempt.get('fresh_functional_gap_total') != 150 or attempt.get('materialized_product_functional_elimination_count') != 17 or attempt.get('materialized_external_authority_elimination_count') != 4 or attempt.get('effective_shared_owner_external_gap_count') != 0 or attempt.get('product_design_authority_blocked') != 150 or attempt.get('preserved_external_shared_authority_blocked') != 0:
    die('R3_ACTIVE_ATTEMPT_SUMMARY_DRIFT')
if reg.get('reexecution_cycle') != 'R3_EXTERNAL_AUTHORITY_AWARE':
    die('R3_REGRESSION_RECEIPT_CYCLE_DRIFT')
for key in ('structural_missing_artifact_signature','bounded_product_functional_signature','gap006_shared_owner_authority_signature'):
    if (reg.get(key) or {}).get('effective_fresh_reproduction_count') != 0 or (reg.get(key) or {}).get('status') not in {'ZERO_REPRODUCTION_PASS','ZERO_EFFECTIVE_REPRODUCTION_PASS'}:
        die('R3_KNOWN_SIGNATURE_NOT_ZERO:' + key)
if (reg.get('remaining_product_contract_signature') or {}).get('effective_fresh_reproduction_count') != 150:
    die('R3_REMAINING_PRODUCT_SIGNATURE_DRIFT')
print('PASS: fresh R3 evidence is exact 171 - 17 product - 4 GAP-006 = 150 effective blockers')
print('PASS: GAP-006 effective reproduction count is zero while source Authority history remains preserved')
print('PASS: Stage-02 remains blocked; website construction and deployment remain false')
