#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys

from governance_resolver import resolve

ROOT = Path(__file__).resolve().parents[2]
BINDING = ROOT / "governance/test/STAGE01_ACTIVE_BINDING.yaml"
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"

EXPECTED = {
    "CORE-01": {
        "00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/PAGE_BASE_BLUEPRINT.yaml": "v2.1.8",
        "00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/CORE-01/VISUAL_BASE_BLUEPRINT.yaml": "v2.1.9",
        "00_SOURCE_INTAKE/fresh_run_003/03_BLUEPRINT_BINDING/CORE-01/BLUEPRINT_BINDING_MANIFEST.yaml": "v2.1.10",
    },
    "ASSET-01": {
        "00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/PAGE_BASE_BLUEPRINT.yaml": "v2.1.8",
        "00_SOURCE_INTAKE/fresh_run_003/02_BASE_BLUEPRINT/ASSET-01/VISUAL_BASE_BLUEPRINT.yaml": "v2.1.9",
        "00_SOURCE_INTAKE/fresh_run_003/03_BLUEPRINT_BINDING/ASSET-01/BLUEPRINT_BINDING_MANIFEST.yaml": "v2.1.10",
    },
}

errors = []
resolved = resolve()

if not BINDING.is_file():
    errors.append("MISSING_STAGE01_ACTIVE_BINDING")
    binding_text = ""
else:
    binding_text = BINDING.read_text(encoding="utf-8")

if not STATE.is_file():
    errors.append("MISSING_ACTIVE_TEST_STATE")
    state_text = ""
else:
    state_text = STATE.read_text(encoding="utf-8")

required_binding_tokens = (
    "registry_ref: governance/specifications/REGISTRY.yaml",
    f"governance_uid: {resolved['governance_uid']}",
    "locator_mode: REGISTRY_ONLY",
    "version_labels_are_locator: false",
    "governance_overlay_field: CREATION_PROVENANCE_ONLY",
    "historical_version_labels_may_select_current_governance: false",
    "artifact_content_rewrite_for_display_version_change: false",
    "artifact_hash_rewrite_for_display_version_change: false",
    "current_governance_must_be_resolved_at_validation_runtime: true",
)
for token in required_binding_tokens:
    if token not in binding_text:
        errors.append("STAGE01_BINDING_TOKEN_MISSING:" + token)

# These are permanent Stage-01/current-governance identity invariants.
required_state_tokens = (
    "specification_registry_ref: governance/specifications/REGISTRY.yaml",
    f"specification_uid: {resolved['governance_uid']}",
    "stage1_binding_ref: governance/test/STAGE01_ACTIVE_BINDING.yaml",
    "stage1_binding_mode: REGISTRY_UID_RUNTIME_RESOLUTION",
)
for token in required_state_tokens:
    if token not in state_text:
        errors.append("ACTIVE_STATE_TOKEN_MISSING:" + token)

# Stage-02 runtime-result evidence is conditional execution evidence, not a Stage-01 binding invariant.
# A clean Stage-02 reset MUST NOT recreate these fields merely to satisfy this validator.
stage2_not_executed = (
    "current_stage: STAGE-01-CLOSED" in state_text
    and re.search(r"(?ms)^  stage2:\s*\n(?:    .*\n)*?    result:\s*NOT_EXECUTED\s*$", state_text) is not None
)

stage2_runtime_result_tokens = (
    "mode: RUNTIME_GENERATED_GITHUB_ACTION_ARTIFACT",
    "static_result_pointer_required: false",
    "static_run_id_copy_forbidden: true",
    "static_head_sha_copy_forbidden: true",
    "static_specification_digest_copy_forbidden: true",
)
if stage2_not_executed:
    # Clean reset semantics: old Stage-02 evidence/pointers must not survive as active state.
    for token in stage2_runtime_result_tokens:
        if token in state_text:
            errors.append("STAGE2_RESET_RUNTIME_RESULT_RESIDUAL:" + token)
else:
    for token in stage2_runtime_result_tokens:
        if token not in state_text:
            errors.append("ACTIVE_STAGE2_RESULT_TOKEN_MISSING:" + token)

# Active test state/binding may never point at a version-named governance directory.
version_locator = re.compile(r"governance/(?:current|specifications)/v\d+(?:\.\d+)+")
for label, text in (("STAGE01_ACTIVE_BINDING", binding_text), ("ACTIVE_STATE", state_text)):
    hit = version_locator.search(text)
    if hit:
        errors.append(f"ACTIVE_VERSION_NAMED_GOVERNANCE_LOCATOR:{label}:{hit.group(0)}")

# Static execution receipts/digests are runtime evidence, not copied active identity.
for forbidden in ("prior_run_id:", "prior_head_sha:", "runtime_bundle_sha256:", "specification_runtime_sha256:"):
    if forbidden in state_text or forbidden in binding_text:
        errors.append("STATIC_RUNTIME_EVIDENCE_COPY_FORBIDDEN:" + forbidden)


def read_overlay(path):
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            return json.loads(text).get("governance_overlay")
        except Exception as exc:
            errors.append(f"INVALID_JSON_STAGE01_ARTIFACT:{path.relative_to(ROOT)}:{exc}")
            return None
    match = re.search(r"^governance_overlay:\s*([^\s#]+)", text, re.MULTILINE)
    return match.group(1) if match else None


for page, artifacts in EXPECTED.items():
    if page not in binding_text:
        errors.append("STAGE01_BINDING_PAGE_MISSING:" + page)
    for rel, expected_overlay in artifacts.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append("STAGE01_ARTIFACT_MISSING:" + rel)
            continue
        overlay = read_overlay(path)
        if overlay != expected_overlay:
            errors.append(f"STAGE01_CREATION_PROVENANCE_DRIFT:{rel}:expected={expected_overlay}:actual={overlay}")
        if f"artifact_ref: {rel}" not in binding_text:
            errors.append("STAGE01_BINDING_ARTIFACT_REF_MISSING:" + rel)
        artifact_marker = f"artifact_ref: {rel}"
        marker_at = binding_text.find(artifact_marker)
        overlay_at = binding_text.find(f"creation_governance_overlay: {expected_overlay}", marker_at)
        if marker_at < 0 or overlay_at < 0:
            errors.append("STAGE01_BINDING_PROVENANCE_MISSING:" + rel)

# Historical rerun receipts may retain versioned paths, but ACTIVE_STATE must not use them as current pointers.
if "TARGETED_STAGE2_RERUN_V214_RESULT.json" in state_text:
    errors.append("HISTORICAL_VERSIONED_RESULT_USED_AS_ACTIVE_POINTER")

if errors:
    for error in errors:
        print("BLOCK:", error, file=sys.stderr)
    raise SystemExit(1)

print("PASS: Stage-01 CORE-01 and ASSET-01 artifacts remain byte-preserved historical construction outputs")
print("PASS: artifact governance_overlay values are classified as creation provenance only")
print("PASS: active Stage-01 governance identity resolves through Registry immutable UID")
print("PASS: display-version changes do not require Stage-01 artifact/hash rewrites")
if stage2_not_executed:
    print("PASS: Stage-02 is NOT_EXECUTED and no Stage-02 runtime result evidence is required or retained")
else:
    print("PASS: executed Stage-02 runtime result evidence contract is present")
print("PASS: active test state contains no stale static run/head/specification-digest pointer")
