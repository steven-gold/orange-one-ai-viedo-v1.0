#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import copy, hashlib, io, json, lzma, re, subprocess, tarfile, zipfile
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.github/governance-source/active/source'
AUTH_UID = 'USR-DIRECTIVE-20260919-MOTHER-PROFILE-TOKEN-DECONTAMINATION-R1'
OLD_UID = 'GOV-REV-20260919-SCOPE-STAGE-REENTRY-PORTABILITY-HARDENING'
NEW_UID = 'GOV-REV-20260919-PROFILE-TOKEN-DECONTAMINATION-HARDENING'
DISPLAY_VERSION = 'v2.2.7'
SOURCE_REVISION = 'v2.2.6-profile-token-decontamination-hardening'
PACKAGE_FILENAME = 'AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.6_PROFILE_TOKEN_DECONTAMINATION_HARDENING_LOCAL_VERIFIED.zip'
AUTH = ROOT / f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
MOTHER_DIR = SOURCE / '12_DOCS/mother-spec'
M1 = MOTHER_DIR / '01_BLUEPRINT_DESIGN_GOVERNANCE.md'
M2 = MOTHER_DIR / '02_IMPLEMENTATION_DELIVERY_STANDARD.md'

def load(p: Path):
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

def write(p: Path, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=180), encoding='utf-8')

def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha(p: Path) -> str:
    return sha_bytes(p.read_bytes())

def run(*args, cwd=ROOT):
    print('+', ' '.join(map(str, args)))
    subprocess.run(args, cwd=cwd, check=True)

def patch_mother_profile_tokens():
    old1 = 'before R7 or any equivalent authority-ingestion/materialization step may consume it.'
    new1 = 'before the registered downstream authority-ingestion/materialization capability may consume it.'
    old2 = '再由 R7 或等價 ingestion 消費；Candidate/Test/Evidence 不得直接成為 Authority。'
    new2 = '再由已註冊的下游 Authority ingestion/materialization capability 消費；Candidate/Test/Evidence 不得直接成為 Authority。'
    t1 = M1.read_text(encoding='utf-8')
    t2 = M2.read_text(encoding='utf-8')
    if t1.count(old1) != 1:
        raise RuntimeError(f'MOTHER01_R7_ANCHOR_DRIFT:{t1.count(old1)}')
    if t2.count(old2) != 1:
        raise RuntimeError(f'MOTHER02_R7_ANCHOR_DRIFT:{t2.count(old2)}')
    M1.write_text(t1.replace(old1, new1, 1), encoding='utf-8')
    M2.write_text(t2.replace(old2, new2, 1), encoding='utf-8')

    patterns = {
        'profile_retry_token': re.compile(r'\bR\d{1,3}\b'),
        'fixed_stage_token': re.compile(r'\bSTAGE-\d{1,2}\b', re.I),
        'concrete_product_uid': re.compile(r'\b(?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI)-\d+\b'),
        'workflow_path': re.compile(r'\.github/workflows/'),
        'governance_script_path': re.compile(r'\bgovernance/ci/[A-Za-z0-9_.\-/]+'),
        'long_run_id': re.compile(r'\b\d{8,12}\b'),
    }
    leaks = []
    for p in sorted(MOTHER_DIR.glob('*.md')):
        text = p.read_text(encoding='utf-8')
        for kind, pat in patterns.items():
            for m in pat.finditer(text):
                leaks.append(f'{p.name}:{kind}:{m.group(0)}')
    if leaks:
        raise RuntimeError('MOTHER_COMMON_POLICY_CONTAMINATION:' + '|'.join(leaks[:50]))

def patch_portability_validator():
    p = ROOT / 'governance/ci/validate_governance_portability.py'
    t = p.read_text(encoding='utf-8')
    anchor = """for p in sorted(MOTHER.glob('*.md')):
    t=p.read_text(encoding='utf-8')
    for finding in scan_policy_text(t):
        failures.append('mother_policy_semantic_leak:'+p.name+':'+finding['semantic_type']+':'+finding['match'])

manifest=yaml.safe_load((CUR/'SPECIFICATION_MANIFEST.yaml').read_text()) or {}
"""
    replacement = """for p in sorted(MOTHER.glob('*.md')):
    t=p.read_text(encoding='utf-8')
    for finding in scan_policy_text(t):
        failures.append('mother_policy_semantic_leak:'+p.name+':'+finding['semantic_type']+':'+finding['match'])

# Secondary literal contamination defense for reusable Mother prose. These values
# belong to execution-profile, product-adapter, run-state, workflow or evidence layers.
mother_literal_patterns={
    'profile_retry_token': re.compile(r'\\bR\\d{1,3}\\b'),
    'fixed_stage_token': re.compile(r'\\bSTAGE-\\d{1,2}\\b', re.IGNORECASE),
    'concrete_product_uid': re.compile(r'\\b(?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI)-\\d+\\b'),
    'workflow_path': re.compile(r'\\.github/workflows/'),
    'governance_script_path': re.compile(r'\\bgovernance/ci/[A-Za-z0-9_.\\-/]+'),
    'long_run_id': re.compile(r'\\b\\d{8,12}\\b'),
}
for p in sorted(MOTHER.glob('*.md')):
    body=p.read_text(encoding='utf-8')
    for kind,pat in mother_literal_patterns.items():
        for m in pat.finditer(body):
            failures.append('mother_policy_literal_contamination:'+p.name+':'+kind+':'+m.group(0))

manifest=yaml.safe_load((CUR/'SPECIFICATION_MANIFEST.yaml').read_text()) or {}
"""
    if anchor not in t:
        raise RuntimeError('PORTABILITY_MOTHER_SCAN_ANCHOR_DRIFT')
    p.write_text(t.replace(anchor, replacement, 1), encoding='utf-8')

def patch_neutrality_workflow():
    p = ROOT / '.github/workflows/mother-spec-neutrality-audit.yml'
    body = """name: Mother Spec Neutrality Audit

on:
  push:
    branches: [rebuild-v2.1.1]
    paths:
      - '.github/governance-source/active/source/12_DOCS/mother-spec/**'
      - 'governance/specifications/current/**'
      - 'governance/specifications/REGISTRY.yaml'
      - 'GOVERNANCE_CURRENT.yaml'
      - 'governance/ci/validate_governance_portability.py'
      - '.github/governance-source/active/source/10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml'
      - '.github/workflows/mother-spec-neutrality-audit.yml'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  audit:
    runs-on: ubuntu-24.04
    env:
      PYTHONDONTWRITEBYTECODE: '1'
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install verifier dependency
        run: python -m pip install --disable-pip-version-check 'PyYAML==6.0.2'
      - name: Enforce reusable-policy neutrality and portability
        run: python governance/ci/validate_governance_portability.py
      - name: Report Mother literal contamination denominator
        shell: bash
        run: |
          python - <<'PY'
          from pathlib import Path
          import json,re,sys
          root=Path('.github/governance-source/active/source/12_DOCS/mother-spec')
          pats={
            'profile_retry_token': re.compile(r'\\bR\\d{1,3}\\b'),
            'fixed_stage_token': re.compile(r'\\bSTAGE-\\d{1,2}\\b',re.I),
            'concrete_product_uid': re.compile(r'\\b(?:CORE|ASSET|VIDEO|EDIT|VOICE|QA|IAM|ERP|AIAPI)-\\d+\\b'),
            'workflow_path': re.compile(r'\\.github/workflows/'),
            'governance_script_path': re.compile(r'\\bgovernance/ci/[A-Za-z0-9_.\\-/]+'),
            'long_run_id': re.compile(r'\\b\\d{8,12}\\b'),
          }
          hits=[]
          for p in sorted(root.glob('*.md')):
              text=p.read_text(encoding='utf-8')
              for kind,pat in pats.items():
                  for m in pat.finditer(text):
                      hits.append({'path':p.as_posix(),'kind':kind,'match':m.group(0)})
          print(json.dumps({'mother_files':len(list(root.glob('*.md'))),'contamination_hits':hits,'count':len(hits)},ensure_ascii=False,indent=2))
          if hits:
              sys.exit(1)
          PY
"""
    p.write_text(body, encoding='utf-8')

def update_source_revision_and_semantic_anchor():
    for p in sorted((SOURCE/'10_REGISTRY').glob('*.yaml')):
        d = load(p)
        if 'governance_revision' in d:
            d['governance_revision'] = SOURCE_REVISION
            write(p, d)

    sem_p = SOURCE / '10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    sem = load(sem_p)
    sem['governance_revision'] = SOURCE_REVISION
    tmp = copy.deepcopy(sem)
    tmp.pop('content_hash', None)
    sem_hash = sha_bytes(yaml.safe_dump(tmp, allow_unicode=True, sort_keys=True, width=180).encode())
    sem['content_hash'] = sem_hash
    write(sem_p, sem)

    val_p = SOURCE / '09_TESTS/governance/validate_reference_semantics.py'
    body = val_p.read_text(encoding='utf-8')
    body2, n = re.subn(
        r"SEMANTIC_BASELINE_CONTENT_HASH='[0-9a-f]+'",
        f"SEMANTIC_BASELINE_CONTENT_HASH='{sem_hash}'",
        body,
        count=1,
    )
    if n != 1:
        raise RuntimeError('SEMANTIC_HASH_CONSTANT_ANCHOR_DRIFT')
    val_p.write_text(body2, encoding='utf-8')
    return sem_hash

def sync_source_candidate_state():
    p = SOURCE / '11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    d = load(p)
    d['candidate'] = 'v2.2.6_PROFILE_TOKEN_DECONTAMINATION_HARDENING_CANDIDATE'
    fresh = d.setdefault('fresh_revalidation', {})
    fresh['required'] = True
    fresh['current_source_revision'] = SOURCE_REVISION
    fresh['current_closure_credit'] = False
    fresh['predecessor_evidence_current_closure_credit'] = False
    fresh['embedded_preformal_execution_role'] = 'HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'
    fresh['predecessor_wrapper_result_role'] = 'HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'
    fresh['persisted_head_full_line_required'] = True
    fresh['historical_evidence_may_close_successor'] = False
    write(p, d)

def deterministic_hashes():
    cp = SOURCE / 'CHECKSUMS.sha256'
    files = sorted((p for p in SOURCE.rglob('*') if p.is_file() and p != cp), key=lambda p: p.relative_to(SOURCE).as_posix())
    if len(files) != 74:
        raise RuntimeError(f'CHECKSUM_TARGET_DENOMINATOR_DRIFT:{len(files)}')
    cp.write_text(''.join(f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}\n' for p in files), encoding='utf-8')
    checksum = sha(cp)

    identity_files = sorted(files + [cp], key=lambda p: p.relative_to(SOURCE).as_posix())
    tb = io.BytesIO()
    with tarfile.open(fileobj=tb, mode='w', format=tarfile.PAX_FORMAT) as tf:
        for p in identity_files:
            rel = p.relative_to(SOURCE).as_posix()
            info = tf.gettarinfo(str(p), arcname=rel)
            info.uid = 0
            info.gid = 0
            info.uname = ''
            info.gname = ''
            info.mtime = 0
            with p.open('rb') as fh:
                tf.addfile(info, fh)
    bundle = sha_bytes(lzma.compress(tb.getvalue(), format=lzma.FORMAT_XZ, preset=9))

    zb = io.BytesIO()
    with zipfile.ZipFile(zb, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in identity_files:
            rel = p.relative_to(SOURCE).as_posix()
            zi = zipfile.ZipInfo(rel, date_time=(1980,1,1,0,0,0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3
            mode = 0o755 if (p.stat().st_mode & 0o111) else 0o644
            zi.external_attr = (mode & 0xffff) << 16
            zf.writestr(zi, p.read_bytes())
    zhash = sha_bytes(zb.getvalue())
    return checksum, bundle, zhash

def refresh_source():
    run('python', str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'), cwd=SOURCE/'09_TESTS/governance')
    run('python', str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'), cwd=SOURCE/'09_TESTS/governance')
    checksum, bundle, zhash = deterministic_hashes()
    return checksum, bundle, zhash

def patch_identity_consumers(checksum, bundle, zhash, sem_hash):
    vp = ROOT / '.github/governance-source/VERIFY_SOURCE_IDENTITY.py'
    t = vp.read_text(encoding='utf-8')
    for pattern, value in [
        (r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'", bundle),
        (r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'", zhash),
    ]:
        t, n = re.subn(pattern, lambda m: m.group(0).split('=')[0] + "= '" + value + "'", t, count=1)
        if n != 1:
            raise RuntimeError('IDENTITY_CONSTANT_ANCHOR_DRIFT:' + pattern)
    vp.write_text(t, encoding='utf-8')

    fp = ROOT / '.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'
    t = fp.read_text(encoding='utf-8')
    for pattern, value in [
        (r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]+'", checksum),
        (r"EXPECTED_SEMANTIC_CONTENT_HASH = '[0-9a-f]+'", sem_hash),
        (r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]+'", zhash),
        (r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]+'", bundle),
    ]:
        t, n = re.subn(pattern, lambda m: m.group(0).split('=')[0] + "= '" + value + "'", t, count=1)
        if n != 1:
            raise RuntimeError('FULLLINE_IDENTITY_CONSTANT_ANCHOR_DRIFT:' + pattern)
    fp.write_text(t, encoding='utf-8')

def update_scope_manifest_governance_uid():
    p = ROOT / 'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'
    if not p.is_file():
        return
    d = load(p)
    d['governance_uid'] = NEW_UID
    d['predecessor_governance_uid'] = OLD_UID
    d['fresh_revalidation_required'] = True
    tmp = copy.deepcopy(d)
    tmp.pop('content_hash', None)
    d['content_hash'] = sha_bytes(json.dumps(tmp, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
    write(p, d)

def patch_projectors(checksum, bundle, zhash, sem_hash):
    p = ROOT / 'governance/specifications/REGISTRY.yaml'
    d = load(p)
    active = d.get('active_specification') or {}
    if active.get('governance_uid') != OLD_UID:
        raise RuntimeError('REGISTRY_CURRENT_UID_DRIFT')
    d['immediate_predecessor'] = {
        'governance_uid': OLD_UID,
        'display_version': active.get('display_version'),
        'version_role': 'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY',
        'status': 'SUPERSEDED_HISTORY_ONLY_AFTER_PROFILE_TOKEN_DECONTAMINATION_HARDENING',
    }
    active['governance_uid'] = NEW_UID
    active['display_version'] = DISPLAY_VERSION
    aliases = active.setdefault('aliases', [])
    if 'profile-token-decontamination-hardening' not in aliases:
        aliases.append('profile-token-decontamination-hardening')
    d['active_specification'] = active
    write(p, d)

    p = ROOT / 'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    d = load(p)
    d['artifact_uid'] = NEW_UID
    d['display_version'] = DISPLAY_VERSION
    sl = d.setdefault('source_lineage', {})
    sl['predecessor_governance_uid'] = OLD_UID
    sl['promotion_authorization_uid'] = AUTH_UID
    sl['verified_package_filename'] = PACKAGE_FILENAME
    sl['verified_package_sha256'] = zhash
    sl['deterministic_source_bundle_sha256'] = bundle
    sl['checksum_manifest_sha256'] = checksum
    sl['semantic_authority_content_hash'] = sem_hash
    sl['verified_source_revision'] = SOURCE_REVISION
    sl['source_bytes_changed_by_this_successor'] = True
    sl['source_identity_reused_only_because_source_bytes_are_unchanged'] = False
    write(p, d)

    p = ROOT / 'GOVERNANCE_CURRENT.yaml'
    d = load(p)
    d['active_governance_uid'] = NEW_UID
    d['display_version'] = DISPLAY_VERSION
    si = d.setdefault('source_identity', {})
    si['verified_package_sha256'] = zhash
    si['deterministic_source_bundle_sha256'] = bundle
    si['checksum_manifest_sha256'] = checksum
    si['semantic_authority_content_hash'] = sem_hash
    si['verified_source_revision'] = SOURCE_REVISION
    si['source_bytes_changed_by_current_successor'] = True
    write(p, d)

    update_scope_manifest_governance_uid()

    p = ROOT / 'governance/test/ACTIVE_STATE.yaml'
    a = load(p)
    a['specification_uid'] = NEW_UID
    a['next_action'] = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE02_REVALIDATION_UNDER_CURRENT_GOVERNANCE'
    a['current_primary_task_layer'] = 'GOVERNANCE_MAINTENANCE'
    a['current_primary_task_authorization_uid'] = AUTH_UID
    a['current_primary_task_product_stage_credit'] = 0
    rc = a.setdefault('resume_control', {})
    rc['current_resume_point'] = 'POST_GOVERNANCE_PROMOTION_STAGE2_REVERIFY_REQUIRED'
    rc['current_work_unit_uid'] = None
    rc['current_owner'] = None
    rc['historical_stage2_results_are_current_state'] = False
    rc['stage2_execution_requires_fresh_entry_resolution'] = True
    rc['exact_next_action'] = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE02_REVALIDATION_UNDER_CURRENT_GOVERNANCE'
    tr = a.setdefault('governance_revision_transition', {})
    tr['predecessor_governance_uid'] = OLD_UID
    tr['current_governance_uid'] = NEW_UID
    tr['predecessor_attempt_preserved_as_historical_evidence'] = True
    tr['predecessor_attempt_may_close_under_current_governance'] = False
    tr['fresh_revalidation_required'] = True
    tr['fresh_revalidation_scope'] = 'AFFECTED_PRODUCT_SCOPE_AND_REUSABLE_POLICY_CONSUMERS'
    tr['website_construction_remains_blocked'] = True
    tr['deployment_remains_blocked'] = True
    active_attempt = a.get('stage02_active_attempt')
    if isinstance(active_attempt, dict):
        active_attempt['fresh_revalidation_required'] = True
        active_attempt['closure_credit_under_current_governance'] = False
        active_attempt['next_action'] = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE02_REVALIDATION_UNDER_CURRENT_GOVERNANCE'
    ex = a.get('execution')
    if isinstance(ex, dict):
        s2 = ex.get('stage2')
        if isinstance(s2, dict):
            s2['revalidation_required_under_current_governance'] = True
            s2['prior_results_authoritative_for_current_governance'] = False
            s2['stage_exit_allowed'] = False
        ex['website_construction_allowed'] = False
        ex['deployment_allowed'] = False
    a['profile_token_decontamination_successor'] = {
        'authorization_uid': AUTH_UID,
        'predecessor_governance_uid': OLD_UID,
        'current_governance_uid': NEW_UID,
        'product_stage_credit': 0,
        'mother_profile_local_token_count_after_promotion': 0,
        'neutrality_validator_hardened': True,
        'neutrality_workflow_hardening_pending': True,
        'status': 'GOVERNANCE_PROMOTED_PRODUCT_REVERIFY_REQUIRED',
    }
    fl = a.setdefault('full_lifecycle_governance_system_test', {})
    fl['deterministic_source_bundle_sha256'] = bundle
    fl['persisted_head_revalidation_required'] = True
    fl['full_line_github_result'] = 'REVALIDATION_REQUIRED_AFTER_PROFILE_TOKEN_DECONTAMINATION_PROMOTION'
    fl['terminal_run_conclusion'] = 'REVALIDATION_REQUIRED'
    fl['terminal_result_credit_allowed'] = False
    write(p, a)

    findings = ROOT / 'governance/test/stage02/STAGE02_CURRENT_FINDINGS.yaml'
    if findings.is_file():
        d = load(findings)
        d['current_governance_revalidation_required'] = True
        d['closure_credit_under_current_governance'] = False
        d['next_action'] = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE02_REVALIDATION_UNDER_CURRENT_GOVERNANCE'
        write(findings, d)

    cand = ROOT / 'governance/test/SPECIFICATION_CHANGE_CANDIDATES.yaml'
    if cand.is_file():
        d = load(cand)
        cur = d.setdefault('current_stage2_execution', {})
        cur['current_governance_uid'] = NEW_UID
        cur['fresh_revalidation_required_under_current_governance'] = True
        cur['closure_credit_under_current_governance'] = False
        cur['next_action'] = 'WORK_UNIT_RESOLUTION_GATE_REQUIRED_FOR_STAGE02_REVALIDATION_UNDER_CURRENT_GOVERNANCE'
        write(cand, d)

def validate():
    checks = [
        ['python', '-m', 'py_compile', str(ROOT/'governance/ci/validate_governance_portability.py')],
        ['python', '-m', 'py_compile', str(SOURCE/'09_TESTS/governance/validate_reference_semantics.py')],
        ['python', str(ROOT/'.github/governance-source/VERIFY_SOURCE_IDENTITY.py')],
        ['python', str(ROOT/'governance/ci/governance_resolver.py')],
        ['python', str(ROOT/'governance/ci/validate_governance_portability.py')],
        ['python', str(ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py')],
        ['python', str(SOURCE/'09_TESTS/governance/validate_section_registry.py')],
        ['python', str(SOURCE/'09_TESTS/governance/validate_reference_semantics.py')],
        ['python', str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py')],
    ]
    for cmd in checks:
        run(*cmd)
    for rel in [
        'governance/test/ACTIVE_CONSUMER_REFERENCE_INTEGRITY_REPORT.json',
        '.github/governance-source/SOURCE_IDENTITY_REPORT.json',
    ]:
        p = ROOT / rel
        if p.exists():
            # Keep generated evidence if tracked; it will be committed as Current evidence.
            pass
    run('git', 'diff', '--check')

def main():
    if not AUTH.is_file():
        raise RuntimeError('AUTHORIZATION_MISSING')
    auth = load(AUTH)
    if auth.get('status') != 'APPROVED_FOR_EXACT_SCOPE' or auth.get('single_use') is not True:
        raise RuntimeError('AUTHORIZATION_INVALID')
    if load(ROOT/'governance/specifications/REGISTRY.yaml').get('active_specification', {}).get('governance_uid') != OLD_UID:
        raise RuntimeError('CURRENT_GOVERNANCE_DRIFT')

    patch_mother_profile_tokens()
    patch_portability_validator()
    # GitHub Actions App cannot mutate workflow files. The normative Mother successor
    # remains one atomic transaction; the non-normative neutrality workflow is hardened
    # separately through the authorized repository connector after promotion succeeds.
    update_source_revision_and_semantic_anchor()
    sync_source_candidate_state()
    checksum, bundle, zhash = refresh_source()
    patch_identity_consumers(checksum, bundle, zhash, load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')['content_hash'])

    # Refresh the root manifest once more after semantic/compiled source changes, then
    # recompute the final source identity and propagate it to all external consumers.
    run('python', str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'), cwd=SOURCE/'09_TESTS/governance')
    checksum, bundle, zhash = deterministic_hashes()
    sem_hash = load(SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml')['content_hash']
    patch_identity_consumers(checksum, bundle, zhash, sem_hash)
    patch_projectors(checksum, bundle, zhash, sem_hash)

    validate()
    print(json.dumps({
        'new_governance_uid': NEW_UID,
        'display_version': DISPLAY_VERSION,
        'source_revision': SOURCE_REVISION,
        'semantic_authority_content_hash': sem_hash,
        'checksum_manifest_sha256': checksum,
        'deterministic_source_bundle_sha256': bundle,
        'deterministic_source_zip_sha256': zhash,
        'mother_profile_local_token_count': 0,
        'product_stage_credit': 0,
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
