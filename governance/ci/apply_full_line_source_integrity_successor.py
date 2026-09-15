#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import lzma
import os
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.github/governance-source/active/source'
AUTH_UID = 'USR-DIRECTIVE-20260916-FULL-LINE-SOURCE-INTEGRITY-CLOSURE'
PREV_GOV_UID = 'GOV-REV-20260916-CANONICAL-REFERENCE-MIGRATION-ATOMICITY'
NEW_GOV_UID = 'GOV-REV-20260916-FULL-LINE-SOURCE-INTEGRITY-CLOSURE'
DISPLAY_VERSION = 'v2.2.2'
OLD_SOURCE_REV = 'v2.2.0-neutral-portable-governance'
NEW_SOURCE_REV = 'v2.2.1-full-line-source-integrity'
OLD_SOURCE_VERSION = '2.2.0'
NEW_SOURCE_VERSION = '2.2.1'
SEMANTIC_HASH = '81f79f898fe4824e147bff63b8ec7696bf404ac461c6224731260c4cc632c02a'
OLD_STALE_HASH = '9af585e1b2f289a04795a3dbc528b98380c0a64d6528dc6a6cc8cbf6995df0a6'
PACKAGE_FILENAME = 'AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.1_FULL_LINE_SOURCE_INTEGRITY_LOCAL_VERIFIED.zip'
BUILDER_PATH = ROOT / 'governance/ci/apply_full_line_source_integrity_successor.py'
WORKFLOW_PATH = ROOT / '.github/workflows/full-line-source-integrity-successor.yml'


def sh(*args: str, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, env=env)
    if check and cp.returncode != 0:
        raise RuntimeError(f"command failed rc={cp.returncode}: {' '.join(args)}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
    return cp


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def write(path: Path, value: str) -> None:
    path.write_text(value, encoding='utf-8')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(read(path)) or {}


def save_yaml(path: Path, data: dict) -> None:
    write(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=180))


def replace_exact(path: Path, old: str, new: str, expected_count: int = 1) -> None:
    body = read(path)
    count = body.count(old)
    if count != expected_count:
        raise RuntimeError(f'REPLACE_COUNT_MISMATCH:{path.relative_to(ROOT)} expected={expected_count} actual={count} old={old!r}')
    write(path, body.replace(old, new))


def replace_regex(path: Path, pattern: str, replacement: str, expected_count: int = 1) -> None:
    body = read(path)
    new_body, count = re.subn(pattern, replacement, body, flags=re.M | re.S)
    if count != expected_count:
        raise RuntimeError(f'REGEX_REPLACE_COUNT_MISMATCH:{path.relative_to(ROOT)} expected={expected_count} actual={count}')
    write(path, new_body)


def update_source_versions() -> None:
    # Package-level current registries advance together. The immutable semantic baseline
    # deliberately retains its v2.2.0 creation revision and content_hash.
    for path in sorted((SOURCE / '10_REGISTRY').glob('*.yaml')):
        if path.name == 'SEMANTIC_AUTHORITY_BASELINE.yaml':
            continue
        body = read(path)
        pattern = rf'(?m)^governance_revision:\s*{re.escape(OLD_SOURCE_REV)}\s*$'
        body2, count = re.subn(pattern, f'governance_revision: {NEW_SOURCE_REV}', body, count=1)
        if count:
            write(path, body2)

    for name in (
        '01_BLUEPRINT_DESIGN_GOVERNANCE.md',
        '02_IMPLEMENTATION_DELIVERY_STANDARD.md',
        '03_EXECUTION_CONTROL_STANDARD.md',
        '04_AUDIT_PROGRESS_STANDARD.md',
    ):
        p = SOURCE / '12_DOCS/mother-spec' / name
        replace_regex(p, rf'(?m)^version:\s*{re.escape(OLD_SOURCE_VERSION)}\s*$', f'version: {NEW_SOURCE_VERSION}')

    mother2 = SOURCE / '12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md'
    old = ('Profile completion requires every applicable profile-required step to close; '
           'a profile-local 11-step ACPOS lifecycle therefore remains 11/11 for ACPOS while '
           'a different website MAY legally use a different profile.')
    new = ('Profile completion requires every applicable profile-required step to close; '
           'whatever denominator the selected profile declares MUST close against that profile-local '
           'denominator, while a different adopter MAY legally use a different profile.')
    replace_exact(mother2, old, new)

    versioning = SOURCE / 'VERSIONING_RULE.md'
    body = read(versioning)
    addition = '''\n\n## v2.2.0 neutral-portable governance rule\n- v2.2.0 is the verified neutral/portable predecessor source revision. Product/profile identities may exist only in explicitly non-global profile/provenance layers and MUST NOT be required to interpret reusable Mother Policy.\n- Semantic authority baseline identity remains immutable across a successor unless an explicit semantic-baseline maintenance authorization changes that baseline itself.\n\n## v2.2.1 full-line source-integrity successor rule\n- v2.2.1 is a bounded successor for reproduced Full-Line integrity defects: stale semantic-baseline hash consumers, stale revision whitelists, stale prose-coupled validators, and product-neutrality classification drift.\n- Validator/harness defects MUST be repaired at validation implementation; they MUST NOT be solved by weakening denominators, deleting expectations, or reinserting obsolete prose into Mother Policy.\n- The reusable Mother Policy MUST remain product-neutral. Product-specific profile identity is legal only in an explicitly classified non-global execution-profile/provenance context.\n- Source bytes, Root Manifest, compiled baseline, checksum manifest, deterministic package identity, external trust projection, and Current governance source-lineage projection MUST advance atomically.\n'''
    if '## v2.2.1 full-line source-integrity successor rule' not in body:
        write(versioning, body.rstrip() + addition + '\n')


def fix_source_validators() -> None:
    ref = SOURCE / '09_TESTS/governance/validate_reference_semantics.py'
    pa = SOURCE / '09_TESTS/governance/program_artifact_instance_guard.py'
    replace_exact(ref, f"SEMANTIC_BASELINE_CONTENT_HASH='{OLD_STALE_HASH}'", f"SEMANTIC_BASELINE_CONTENT_HASH='{SEMANTIC_HASH}'")
    replace_exact(pa, f"SEMANTIC_BASELINE_CONTENT_HASH='{OLD_STALE_HASH}'", f"SEMANTIC_BASELINE_CONTENT_HASH='{SEMANTIC_HASH}'")

    stage = SOURCE / '09_TESTS/governance/validate_stage_execution_invariants.py'
    old = "rev=str(d.get('governance_revision') or '')\n    if not (rev.startswith('v2.1.13-') or rev.startswith('v2.1.14-') or rev.startswith('v2.1.15-')): failures.append('revision_invalid')"
    new = "rev=str(d.get('governance_revision') or '')\n    root_rev=str(load(root,'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml').get('governance_revision') or '')\n    if not rev or rev != root_rev: failures.append('revision_invalid')"
    replace_exact(stage, old, new)

    feedback = SOURCE / '09_TESTS/governance/validate_test_feedback_spec_evolution.py'
    old = "rev=str(invreg.get('governance_revision') or '')\n    if not (rev.startswith('v2.1.14-') or rev.startswith('v2.1.15-')): failures.append('revision_not_v214_or_v215')"
    new = "rev=str(invreg.get('governance_revision') or '')\n    root_rev=str(load(root,'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml').get('governance_revision') or '')\n    if not rev or rev != root_rev: failures.append('revision_not_current_source_revision')"
    replace_exact(feedback, old, new)

    old = "if 'SECTION_UID: WEB-GOV-03-S059' not in d3 or 'SOURCE_CONTROL_CURRENT_AUTHORITY_PROMOTION' not in d3: failures.append('mother_spec_03_closed_loop_missing')\n    if 'SECTION_UID: WEB-GOV-04-S075' not in d4 or 'Source-Control Single-Authority Audit' not in d4: failures.append('mother_spec_04_audit_missing')"
    new = """s3_marker='<!-- SECTION_UID: WEB-GOV-03-S059 -->'\n    s4_marker='<!-- SECTION_UID: WEB-GOV-04-S075 -->'\n    s3=(d3.split(s3_marker,1)[1].split('<!-- SECTION_UID:',1)[0] if s3_marker in d3 else '')\n    s4=(d4.split(s4_marker,1)[1].split('<!-- SECTION_UID:',1)[0] if s4_marker in d4 else '')\n    for tok in ['Every governed validation cycle MUST durably record reproduced bugs','Each issue MUST be classified by one primary owner','Reusable-policy candidates remain non-normative until explicit authorization','provider/project adapter MUST expose exactly one Current governance entry']:\n        if tok not in s3: failures.append('mother_spec_03_closed_loop_missing:'+tok)\n    for tok in ['Audit MUST verify every governed validation cycle produces a complete defect/gap ledger','Reusable-policy repair is valid only when explicit authorization preexists','Source-Control governance audit MUST verify exactly one Current policy entry']:\n        if tok not in s4: failures.append('mother_spec_04_audit_missing:'+tok)"""
    replace_exact(feedback, old, new)

    closure = SOURCE / '09_TESTS/governance/validate_closure_evidence_continuity.py'
    pattern = r"    tokens=\[.*?\]\n    for tok in tokens:\n        if tok not in doc: failures\.append\('normative_continuity_text_missing:'\+tok\)"
    replacement = """    marker='<!-- SECTION_UID: WEB-GOV-03-S058 -->'\n    section=(doc.split(marker,1)[1].split('<!-- SECTION_UID:',1)[0] if marker in doc else '')\n    tokens=['MERGE_APPEND_OR_EXPLICIT_SUPERSEDE','Current execution/evidence ledgers MUST synchronize as one logical transaction','Materialization evidence and terminal CI receipt are separate identities','provider, repository/project, head SHA, evidence-cycle identity, job denominator, and conclusion','Required evidence must parse and pass its schema/field validator; presence alone is not evidence validity','Unresolved Authority continuity is exact, not count-only','AI inference, alias substitution, default filling, or evidence-reference drift MUST_NOT resolve external Authority']\n    if not section: failures.append('normative_continuity_section_missing:WEB-GOV-03-S058')\n    for tok in tokens:\n        if tok not in section: failures.append('normative_continuity_text_missing:'+tok)"""
    replace_regex(closure, pattern, replacement)

    product = SOURCE / '09_TESTS/governance/validate_product_neutral_entity_lifecycle.py'
    old = """    # Empirical product markers are allowed only inside explicit provenance of the common invariant registry.\n    for path,val in recursive_strings(reg):\n        if any(marker and marker in val for marker in forbidden_markers) and (not path or path[0] != 'provenance'):\n            failures.append('product_marker_outside_empirical_provenance:'+('.'.join(path)))"""
    new = """    # Product-specific material is legal only in explicit provenance or an explicitly\n    # non-global execution-profile projection. It remains forbidden in reusable invariants.\n    profile_identity_allowed=(reg.get('layer_classification')=='EXECUTION_PROFILE' and reg.get('global_normative_authority') is False)\n    for path,val in recursive_strings(reg):\n        has_marker=any(marker and marker in val for marker in forbidden_markers)\n        allowed=(bool(path) and path[0]=='provenance') or (profile_identity_allowed and path==('profile_uid',))\n        if has_marker and not allowed:\n            failures.append('product_marker_outside_allowed_profile_or_provenance:'+('.'.join(path)))"""
    replace_exact(product, old, new)


def append_source_defects() -> None:
    p = SOURCE / '11_EVIDENCE/audit/GOVERNANCE_DEFECT_LEDGER.yaml'
    d = load_yaml(p)
    defects = d.setdefault('defects', [])
    existing = {x.get('defect_uid') for x in defects if isinstance(x, dict)}
    records = [
        {
            'defect_uid': 'GOV-DEFECT-V221-STALE-SEMANTIC-BASELINE-HASH-CONSUMERS',
            'status': 'REMEDIATED_LOCAL_PREFORMAL_PERSISTED_HEAD_REVERIFY_REQUIRED',
            'scope': 'REFERENCE_SEMANTICS_AND_PROGRAM_ARTIFACT_VALIDATION',
            'reproduced_problem': 'Two active validators pinned an obsolete semantic-authority content hash and rejected the unchanged immutable baseline, cascading into multiple mandatory suite failures.',
            'correction': 'Bind both validators to the immutable baseline content hash 81f79f... used by the current verified semantic baseline; retain external trust-root enforcement and do not mutate the baseline itself.',
        },
        {
            'defect_uid': 'GOV-DEFECT-V221-STALE-REVISION-WHITELIST',
            'status': 'REMEDIATED_LOCAL_PREFORMAL_PERSISTED_HEAD_REVERIFY_REQUIRED',
            'scope': 'STAGE_INVARIANT_AND_TEST_FEEDBACK_VALIDATORS',
            'reproduced_problem': 'Validators accepted only historical v2.1.13-v2.1.15 revision prefixes while the selected current source revision was v2.2.0.',
            'correction': 'Resolve the accepted revision from the current Root Manifest instead of private historical revision whitelists.',
        },
        {
            'defect_uid': 'GOV-DEFECT-V221-STALE-PROSE-COUPLED-VALIDATION',
            'status': 'REMEDIATED_LOCAL_PREFORMAL_PERSISTED_HEAD_REVERIFY_REQUIRED',
            'scope': 'CLOSURE_CONTINUITY_AND_TEST_FEEDBACK_VALIDATION',
            'reproduced_problem': 'Validators required obsolete exact prose tokens even though current canonical sections preserved the governed semantics through updated neutral wording.',
            'correction': 'Validate the canonical SECTION_UID-owned section and its current semantic clauses instead of predecessor wording or old heading text.',
        },
        {
            'defect_uid': 'GOV-DEFECT-V221-MOTHER-POLICY-PRODUCT-NAME-RESIDUAL',
            'status': 'REMEDIATED_LOCAL_PREFORMAL_PERSISTED_HEAD_REVERIFY_REQUIRED',
            'scope': 'PRODUCT_NEUTRAL_MOTHER_POLICY',
            'reproduced_problem': 'Reusable Mother 02 contained an ACPOS-specific example while the common policy requires product neutrality.',
            'correction': 'Replace the named-product/fixed-count example with selected-profile-local denominator language without changing the underlying completion rule.',
        },
        {
            'defect_uid': 'GOV-DEFECT-V221-EXECUTION-PROFILE-MISCLASSIFIED-AS-POLICY-POLLUTION',
            'status': 'REMEDIATED_LOCAL_PREFORMAL_PERSISTED_HEAD_REVERIFY_REQUIRED',
            'scope': 'PRODUCT_NEUTRAL_STATIC_AUDIT',
            'reproduced_problem': 'The product-neutral validator rejected an explicitly non-global EXECUTION_PROFILE profile_uid even though product/profile material is permitted in profile extensions.',
            'correction': 'Permit product markers only at the explicit non-global profile identity boundary or provenance; continue blocking product markers inside reusable invariants.',
        },
    ]
    for rec in records:
        if rec['defect_uid'] not in existing:
            defects.append(rec)
    save_yaml(p, d)


def update_candidate_state() -> None:
    p = SOURCE / '11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'
    d = load_yaml(p)
    d['candidate'] = 'v2.2.1_FULL_LINE_SOURCE_INTEGRITY_CANDIDATE'
    d['baseline'] = 'v2.2.0_NEUTRAL_PORTABLE_GOVERNANCE_LOCAL_VERIFIED'
    d['status'] = 'CANDIDATE_UNDER_FRESH_FULL_LINE_REVALIDATION'
    repairs = d.setdefault('current_repairs', [])
    for x in [
        'STALE_SEMANTIC_BASELINE_HASH_CONSUMER_REPAIR',
        'CURRENT_SOURCE_REVISION_RESOLUTION',
        'CANONICAL_SECTION_SEMANTIC_VALIDATION',
        'PRODUCT_NEUTRAL_MOTHER_POLICY_RESIDUAL_REMOVAL',
        'EXECUTION_PROFILE_PRODUCT_IDENTITY_LAYER_CLASSIFICATION',
    ]:
        if x not in repairs:
            repairs.append(x)
    d['website_construction_allowed'] = False
    d['github_upload_allowed'] = False
    d['formal_test_started'] = False
    save_yaml(p, d)


def compile_and_refresh_source() -> None:
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONPYCACHEPREFIX'] = '/tmp/acpos-governance-pycache'
    sh(sys.executable, str(SOURCE/'09_TESTS/governance/compile_governance_baseline.py'), env=env)
    sh(sys.executable, str(SOURCE/'09_TESTS/governance/refresh_governance_root_manifest.py'), env=env)

    files = sorted(p for p in SOURCE.rglob('*') if p.is_file() and p.name != 'CHECKSUMS.sha256' and p.suffix not in {'.pyc','.pyo','.tmp','.bak','.swp'} and '__pycache__' not in p.parts)
    lines = [f'{sha(p)}  {p.relative_to(SOURCE).as_posix()}' for p in files]
    write(SOURCE/'CHECKSUMS.sha256', '\n'.join(lines) + '\n')


def deterministic_bundle_sha() -> str:
    files = sorted((p for p in SOURCE.rglob('*') if p.is_file()), key=lambda p: p.relative_to(SOURCE).as_posix())
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode='w', format=tarfile.PAX_FORMAT) as tf:
        for p in files:
            rel = p.relative_to(SOURCE).as_posix()
            info = tf.gettarinfo(str(p), arcname=rel)
            info.uid = 0; info.gid = 0; info.uname = ''; info.gname = ''; info.mtime = 0
            with p.open('rb') as fh:
                tf.addfile(info, fh)
    bundle = lzma.compress(tar_buf.getvalue(), format=lzma.FORMAT_XZ, preset=9)
    return hashlib.sha256(bundle).hexdigest()


def deterministic_zip_sha() -> str:
    files = sorted((p for p in SOURCE.rglob('*') if p.is_file()), key=lambda p: p.relative_to(SOURCE).as_posix())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            rel = p.relative_to(SOURCE).as_posix()
            zi = zipfile.ZipInfo(rel, date_time=(1980,1,1,0,0,0))
            zi.create_system = 3
            zi.external_attr = (p.stat().st_mode & 0xFFFF) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return hashlib.sha256(buf.getvalue()).hexdigest()


def update_outer_source_identity(bundle_sha: str, zip_sha: str, checksums_sha: str) -> None:
    verify = ROOT / '.github/governance-source/VERIFY_SOURCE_IDENTITY.py'
    run = ROOT / '.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'
    replace_regex(verify, r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]{64}'", f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'")
    replace_regex(run, r"EXPECTED_CHECKSUMS_SHA256 = '[0-9a-f]{64}'", f"EXPECTED_CHECKSUMS_SHA256 = '{checksums_sha}'")
    replace_regex(run, r"EXPECTED_SOURCE_ZIP_SHA256 = '[0-9a-f]{64}'", f"EXPECTED_SOURCE_ZIP_SHA256 = '{zip_sha}'")
    replace_regex(run, r"EXPECTED_BUNDLE_SHA256 = '[0-9a-f]{64}'", f"EXPECTED_BUNDLE_SHA256 = '{bundle_sha}'")


def update_current_governance(bundle_sha: str, zip_sha: str, checksums_sha: str) -> None:
    registry_p = ROOT / 'governance/specifications/REGISTRY.yaml'
    registry = load_yaml(registry_p)
    active = registry.setdefault('active_specification', {})
    if active.get('governance_uid') != PREV_GOV_UID:
        raise RuntimeError('CURRENT_GOVERNANCE_UID_DRIFT_BEFORE_SUCCESSOR')
    active['governance_uid'] = NEW_GOV_UID
    active['display_version'] = DISPLAY_VERSION
    aliases = active.setdefault('aliases', [])
    if 'full-line-source-integrity-closure' not in aliases:
        aliases.append('full-line-source-integrity-closure')
    registry['immediate_predecessor'] = {
        'governance_uid': PREV_GOV_UID,
        'display_version': DISPLAY_VERSION,
        'version_role': 'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY',
        'status': 'SUPERSEDED_HISTORY_ONLY_AFTER_FULL_LINE_SOURCE_INTEGRITY_SUCCESSOR',
    }
    save_yaml(registry_p, registry)

    manifest_p = ROOT / 'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'
    manifest = load_yaml(manifest_p)
    manifest['artifact_uid'] = NEW_GOV_UID
    sl = manifest.setdefault('source_lineage', {})
    old_name = sl.get('verified_package_filename')
    old_sha = sl.get('verified_package_sha256')
    sl['verified_source_revision'] = NEW_SOURCE_REV
    sl['verified_package_filename'] = PACKAGE_FILENAME
    sl['verified_package_sha256'] = zip_sha
    sl['verified_package_hash_model'] = 'DETERMINISTIC_ZIP_SOURCE_SET_V1'
    sl['predecessor_verified_package_filename'] = old_name
    sl['predecessor_verified_package_sha256'] = old_sha
    sl['predecessor_governance_uid'] = PREV_GOV_UID
    sl['promotion_authorization_uid'] = AUTH_UID
    sl['source_bytes_changed_by_this_successor'] = True
    sl['source_identity_reused_only_because_source_bytes_are_unchanged'] = False
    sl['deterministic_source_bundle_sha256'] = bundle_sha
    sl['checksum_manifest_sha256'] = checksums_sha
    sl['semantic_authority_content_hash'] = SEMANTIC_HASH
    save_yaml(manifest_p, manifest)

    current_p = ROOT / 'GOVERNANCE_CURRENT.yaml'
    current = load_yaml(current_p)
    current['active_governance_uid'] = NEW_GOV_UID
    si = current.setdefault('source_identity', {})
    si['verified_source_revision'] = NEW_SOURCE_REV
    si['source_bytes_changed_by_current_successor'] = True
    si['verified_package_sha256'] = zip_sha
    si['deterministic_source_bundle_sha256'] = bundle_sha
    si['checksum_manifest_sha256'] = checksums_sha
    si['semantic_authority_content_hash'] = SEMANTIC_HASH
    save_yaml(current_p, current)

    stage1_p = ROOT / 'governance/test/STAGE01_ACTIVE_BINDING.yaml'
    stage1 = load_yaml(stage1_p)
    stage1.setdefault('current_governance_resolution', {})['governance_uid'] = NEW_GOV_UID
    save_yaml(stage1_p, stage1)

    state_p = ROOT / 'governance/test/ACTIVE_STATE.yaml'
    state = load_yaml(state_p)
    state['specification_uid'] = NEW_GOV_UID
    fl = state.setdefault('full_lifecycle_governance_system_test', {})
    fl['verified_source_package_sha256'] = zip_sha
    fl['deterministic_source_bundle_sha256'] = bundle_sha
    fl['full_line_github_result'] = 'REVERIFY_REQUIRED_AFTER_FULL_LINE_SOURCE_INTEGRITY_SUCCESSOR'
    fl['persisted_head_revalidation_required'] = True
    fl['local_source_successor_full_line'] = 'PASS_REQUIRED_BEFORE_PUSH'
    trans = state.setdefault('governance_revision_transition', {})
    trans['previous_governance_uid'] = PREV_GOV_UID
    trans['current_governance_uid'] = NEW_GOV_UID
    trans['fresh_revalidation_required'] = True
    state['status'] = 'ACTIVE_STAGE2_TESTED_BLOCKED_REVERIFY_REQUIRED_AFTER_FULL_LINE_SOURCE_INTEGRITY_SUCCESSOR'
    state['next_action'] = f'FRESH_REVALIDATION_UNDER_{NEW_GOV_UID}_BEFORE_PRODUCT_REMEDIATION_CREDIT'
    save_yaml(state_p, state)

    cr_p = ROOT / 'governance/specifications/current/CANONICAL_RULE_REGISTRY.yaml'
    cr = load_yaml(cr_p)
    cr['governance_uid_role'] = 'REGISTRY_MATERIALIZATION_PROVENANCE_ONLY'
    cr['governance_uid_may_select_current_governance'] = False
    cr['current_governance_identity_source'] = 'governance/specifications/REGISTRY.yaml'
    save_yaml(cr_p, cr)

    validator = ROOT / 'governance/ci/validate_canonical_rule_registry.py'
    body = read(validator)
    needle = "expected_uid = rules.get('registry_uid')\nexpected_digest = rules.get('registry_digest')\n"
    insert = "expected_uid = rules.get('registry_uid')\nexpected_digest = rules.get('registry_digest')\nif rules.get('governance_uid_role') != 'REGISTRY_MATERIALIZATION_PROVENANCE_ONLY':\n    fail('CANONICAL_RULE_REGISTRY_GOVERNANCE_UID_ROLE_AMBIGUOUS')\nif rules.get('governance_uid_may_select_current_governance') is not False:\n    fail('CANONICAL_RULE_REGISTRY_GOVERNANCE_UID_MAY_SELECT_CURRENT')\nif rules.get('current_governance_identity_source') != 'governance/specifications/REGISTRY.yaml':\n    fail('CANONICAL_RULE_REGISTRY_CURRENT_IDENTITY_SOURCE_DRIFT')\n"
    if needle not in body:
        raise RuntimeError('CANONICAL_VALIDATOR_INSERTION_POINT_MISSING')
    write(validator, body.replace(needle, insert, 1))


def run_precommit_verification() -> None:
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONPYCACHEPREFIX'] = '/tmp/acpos-governance-pycache'
    commands = [
        [sys.executable, '.github/governance-source/VERIFY_SOURCE_IDENTITY.py'],
        [sys.executable, '.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'],
        [sys.executable, 'governance/ci/governance_resolver.py'],
        [sys.executable, 'governance/ci/validate_canonical_rule_registry.py'],
        [sys.executable, 'governance/ci/validate_governance_portability.py'],
        [sys.executable, 'governance/ci/validate_validation_remediation_closure_protocol.py'],
        [sys.executable, 'governance/ci/validate_governance_layout.py'],
        [sys.executable, 'governance/ci/validate_authoring_reference_governance_coverage.py'],
        [sys.executable, 'governance/ci/validate_stage01_registry_binding.py'],
        [sys.executable, 'governance/ci/validate_stage02_successor_integrity_external_aware_r3.py'],
    ]
    for cmd in commands:
        cp = sh(*cmd, check=False, env=env)
        print(f"$ {' '.join(cmd)}\n{cp.stdout}", flush=True)
        if cp.returncode != 0:
            print(cp.stderr, file=sys.stderr, flush=True)
            raise RuntimeError(f'PRECOMMIT_VERIFICATION_FAILED:{cmd}')


def commit_validate_and_push() -> None:
    # One-shot builder artifacts must not survive the successor commit.
    if BUILDER_PATH.exists(): BUILDER_PATH.unlink()
    if WORKFLOW_PATH.exists(): WORKFLOW_PATH.unlink()

    sh('git', 'config', 'user.name', 'acpos-governance-bot')
    sh('git', 'config', 'user.email', 'actions@users.noreply.github.com')
    sh('git', 'add', '-A')
    status = sh('git', 'status', '--porcelain').stdout.strip()
    if not status:
        raise RuntimeError('NO_SUCCESSOR_DIFF')
    print(status)
    msg = (
        'fix(governance): close Full-Line source integrity successor\n\n'
        f'Spec-Change-Authorization: {AUTH_UID}\n'
        'Spec-Change-Scope: full-line-source-integrity-successor-and-current-projection'
    )
    sh('git', 'commit', '-m', msg)

    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONPYCACHEPREFIX'] = '/tmp/acpos-governance-pycache'
    for cmd in [
        [sys.executable, 'governance/ci/specification_mutation_guard.py'],
        [sys.executable, '.github/governance-source/VERIFY_SOURCE_IDENTITY.py'],
        [sys.executable, '.github/governance-source/RUN_FULL_LINE_SYSTEM_GATE.py'],
        [sys.executable, 'governance/ci/validate_canonical_rule_registry.py'],
        [sys.executable, 'governance/ci/validate_authoring_reference_governance_coverage.py'],
        [sys.executable, 'governance/ci/validate_active_consumer_reference_integrity.py'],
        [sys.executable, 'governance/ci/stress_test_governance_registry.py'],
        [sys.executable, 'governance/ci/validate_stage01_registry_binding.py'],
        [sys.executable, 'governance/ci/validate_stage02_successor_integrity_external_aware_r3.py'],
    ]:
        cp = sh(*cmd, check=False, env=env)
        print(f"$ {' '.join(cmd)}\n{cp.stdout}", flush=True)
        if cp.returncode != 0:
            print(cp.stderr, file=sys.stderr, flush=True)
            raise RuntimeError(f'POSTCOMMIT_VERIFICATION_FAILED:{cmd}')
    sh('git', 'diff', '--exit-code', 'HEAD', '--', '.github/governance-source/active/source')
    sh('git', 'push', 'origin', 'HEAD:rebuild-v2.1.1')
    print('SUCCESSOR_PUSHED=' + sh('git', 'rev-parse', 'HEAD').stdout.strip())


def main() -> None:
    auth = ROOT / f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
    if not auth.is_file():
        raise RuntimeError('AUTHORIZATION_RECEIPT_MISSING')
    receipt = load_yaml(auth)
    baseline = ((receipt.get('execution_context_identity_lock') or {}).get('baseline_commit_sha'))
    parent = sh('git', 'rev-parse', 'HEAD^').stdout.strip()
    if baseline != parent:
        raise RuntimeError(f'AUTHORIZATION_BASELINE_DRIFT expected={baseline} actual={parent}')
    if sh('git', 'status', '--porcelain').stdout.strip():
        raise RuntimeError('DIRTY_WORKTREE_BEFORE_SUCCESSOR')

    update_source_versions()
    fix_source_validators()
    append_source_defects()
    update_candidate_state()
    compile_and_refresh_source()

    checksums_sha = sha(SOURCE/'CHECKSUMS.sha256')
    bundle_sha = deterministic_bundle_sha()
    zip_sha = deterministic_zip_sha()
    update_outer_source_identity(bundle_sha, zip_sha, checksums_sha)
    update_current_governance(bundle_sha, zip_sha, checksums_sha)

    run_precommit_verification()
    commit_validate_and_push()


if __name__ == '__main__':
    main()
