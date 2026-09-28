#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "governance/specifications/REGISTRY.yaml"

def load_yaml(path):
    if not path.is_file():
        raise RuntimeError("missing yaml: " + str(path.relative_to(ROOT)))
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise RuntimeError("mapping required: " + str(path.relative_to(ROOT)))
    return value

def resolve():
    registry = load_yaml(REGISTRY)
    if registry.get("registry_role") != "CURRENT_GOVERNANCE_ENTRYPOINT":
        raise RuntimeError("current governance registry role drift")
    if registry.get("status") != "CURRENT":
        raise RuntimeError("current governance registry status drift")

    governance_branch = str(registry.get("branch") or "")
    roles = registry.get("branch_role_contract") or {}
    governance_role = str(roles.get(governance_branch) or "")
    if governance_role != "CURRENT_GOVERNANCE_WORKLINE":
        raise RuntimeError("current governance branch role drift")

    identity = registry.get("governance_identity") or {}
    for key in ("governance_uid","governance_revision","display_version","identity_authority",
                "specification_bundle_sha256","specification_bundle_digest_algorithm",
                "canonical_rule_registry_uid","canonical_rule_registry_digest"):
        if identity.get(key) in (None,"",[]):
            raise RuntimeError("registry governance identity missing: " + key)
    if identity.get("status") != "CURRENT":
        raise RuntimeError("current governance identity status drift")
    if identity.get("identity_state") != "EXACT_HEAD_AND_BUNDLE_DIGEST_BOUND":
        raise RuntimeError("current governance identity state drift")
    if identity.get("identity_authority") != "governance/specifications/REGISTRY.yaml":
        raise RuntimeError("registry governance identity authority drift")

    spec_root_rel = str(registry.get("rules_root") or "")
    if spec_root_rel != "governance/specifications/current":
        raise RuntimeError("current specification root drift")
    spec_root = ROOT / spec_root_rel
    if not spec_root.is_dir():
        raise RuntimeError("specification root missing: " + spec_root_rel)

    manifest = spec_root / "SPECIFICATION_MANIFEST.yaml"
    manifest_doc = load_yaml(manifest)
    if manifest_doc.get("normative_status") != "ACTIVE_CURRENT_GOVERNANCE":
        raise RuntimeError("current specification manifest status drift")
    if manifest_doc.get("current_governance_identity_source") != "governance/specifications/REGISTRY.yaml":
        raise RuntimeError("specification manifest current identity source drift")
    if manifest_doc.get("artifact_uid") != identity.get("governance_uid"):
        raise RuntimeError("current specification manifest governance uid projection drift")
    if manifest_doc.get("display_version") != identity.get("display_version"):
        raise RuntimeError("current specification manifest display version projection drift")
    if manifest_doc.get("branch_release_state") != "CURRENT_EXACT_HEAD_VALIDATION":
        raise RuntimeError("current specification validation state drift")
    if manifest_doc.get("artifact_uid_may_select_current_governance") is not False:
        raise RuntimeError("specification manifest artifact uid still selects current governance")
    if manifest_doc.get("display_version_may_select_current_governance") is not False:
        raise RuntimeError("specification manifest display version still selects current governance")
    if (manifest_doc.get("resolution_contract") or {}).get("canonical_root") != spec_root_rel:
        raise RuntimeError("manifest canonical_root does not match registry rules_root")

    canonical_rule_doc = load_yaml(spec_root / "CANONICAL_RULE_REGISTRY.yaml")
    expected_rule_uid = str(identity.get("canonical_rule_registry_uid"))
    expected_rule_digest = str(identity.get("canonical_rule_registry_digest"))
    if canonical_rule_doc.get("registry_uid") != expected_rule_uid or canonical_rule_doc.get("registry_digest") != expected_rule_digest:
        raise RuntimeError("canonical rule registry identity drift")
    resolution = manifest_doc.get("resolution_contract") or {}
    if resolution.get("canonical_rule_registry_uid") != expected_rule_uid or resolution.get("canonical_rule_registry_digest") != expected_rule_digest:
        raise RuntimeError("manifest canonical rule binding drift")

    lineage = manifest_doc.get("source_lineage") or {}
    if lineage.get("lineage_authority_source") != "governance/specifications/REGISTRY.yaml#governance_identity":
        raise RuntimeError("current specification manifest lineage authority drift")
    if lineage.get("lineage_projection_role") != "NON_NORMATIVE_PROVENANCE_ONLY":
        raise RuntimeError("current specification manifest lineage role drift")
    if lineage.get("concrete_repository_branch_head_or_issue_reference_may_define_common_policy") is not False:
        raise RuntimeError("current specification manifest concrete workline identity leak")

    digest = hashlib.sha256()
    files = []
    for path in sorted(x for x in spec_root.rglob("*") if x.is_file()):
        rel = path.relative_to(spec_root).as_posix()
        data = path.read_bytes()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
        files.append(rel)
    actual_bundle_sha256 = digest.hexdigest()
    expected_bundle_sha256 = str(identity.get("specification_bundle_sha256"))
    if identity.get("specification_bundle_digest_algorithm") != "SHA256_RELATIVE_PATH_NUL_BYTES_NUL_SORTED_V1":
        raise RuntimeError("registry specification bundle digest algorithm drift")
    if actual_bundle_sha256 != expected_bundle_sha256:
        raise RuntimeError("CURRENT_SPECIFICATION_BUNDLE_DIGEST_DRIFT expected="+expected_bundle_sha256+" actual="+actual_bundle_sha256)

    validation = registry.get("current_validation_contract") or {}
    if validation.get("authority_model") != "WORD_DERIVED_INTERNAL_VALIDATION":
        raise RuntimeError("current governance authority model drift")
    if validation.get("word_source_is_primary_product_design_source") is not True:
        raise RuntimeError("Word source primary authority flag drift")
    if validation.get("external_human_or_account_evidence_required") is not False:
        raise RuntimeError("external human/account gate reintroduced")
    if validation.get("external_auditor_required") is not False:
        raise RuntimeError("external auditor gate reintroduced")
    if validation.get("external_signer_required") is not False:
        raise RuntimeError("external signer gate reintroduced")
    if validation.get("promotion_required_before_product_stage_execution") is not False:
        raise RuntimeError("promotion gate reintroduced")
    if validation.get("released_governance_selection_required") is not False:
        raise RuntimeError("released-governance gate reintroduced")

    return {
        "registry": str(REGISTRY.relative_to(ROOT)),
        "registry_uid": registry.get("registry_uid"),
        "governance_branch": governance_branch,
        "governance_role": governance_role,
        "governance_uid": identity.get("governance_uid"),
        "governance_revision": identity.get("governance_revision"),
        "display_version": identity.get("display_version"),
        "identity_authority": identity.get("identity_authority"),
        "authorization_record_url": identity.get("authorization_record_url"),
        "authorized_scope": identity.get("authorized_scope"),
        "governance_validation_state": manifest_doc.get("branch_release_state"),
        "specification_root": spec_root_rel,
        "specification_manifest": str(manifest.relative_to(ROOT)),
        "specification_bundle_uid": manifest_doc.get("artifact_uid"),
        "specification_bundle_display_version": manifest_doc.get("display_version"),
        "runtime_bundle_sha256": actual_bundle_sha256,
        "expected_runtime_bundle_sha256": expected_bundle_sha256,
        "runtime_bundle_digest_algorithm": identity.get("specification_bundle_digest_algorithm"),
        "current_identity_state": identity.get("identity_state"),
        "canonical_rule_registry_uid": expected_rule_uid,
        "canonical_rule_registry_digest": expected_rule_digest,
        "component_files": files,
        "lifecycle_registry": registry.get("lifecycle_registry"),
        "stage_invariant_registry": registry.get("stage_invariant_registry"),
        "product_execution_branch": registry.get("product_execution_branch"),
    }

if __name__ == "__main__":
    try:
        result = resolve()
    except Exception as exc:
        print("BLOCK: GOVERNANCE_RESOLUTION_FAILED: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
    if "--root" in sys.argv:
        print(result["specification_root"])
    elif "--test-root" in sys.argv:
        print("BLOCK: LEGACY_TEST_STATE_ROOT_RETIRED", file=sys.stderr)
        raise SystemExit(2)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
