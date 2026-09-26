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
    spec_root_rel = registry.get("rules_root")
    if not isinstance(spec_root_rel, str) or not spec_root_rel.strip():
        raise RuntimeError("missing registry key: rules_root")

    roles = registry.get("branch_role_contract") or {}
    governance_branch = str(registry.get("branch") or "")
    governance_role = str(roles.get(governance_branch) or "")
    if governance_role not in {"IMMUTABLE_GOVERNANCE_RULESET", "GOVERNANCE_REVISION_CANDIDATE"}:
        raise RuntimeError("governance branch role invalid")

    identity = registry.get("governance_identity") or {}
    required_identity = ("governance_uid", "governance_revision", "display_version", "identity_authority")
    missing = [key for key in required_identity if not identity.get(key)]
    if missing:
        raise RuntimeError("registry governance identity missing: " + ",".join(missing))
    if identity.get("identity_authority") != "governance/specifications/REGISTRY.yaml":
        raise RuntimeError("registry governance identity authority drift")

    spec_root = ROOT / spec_root_rel
    if not spec_root.is_dir():
        raise RuntimeError("specification root missing: " + spec_root_rel)
    manifest = spec_root / "SPECIFICATION_MANIFEST.yaml"
    manifest_doc = load_yaml(manifest)
    if manifest_doc.get("current_governance_identity_source") != "governance/specifications/REGISTRY.yaml":
        raise RuntimeError("specification manifest current identity source drift")
    if manifest_doc.get("artifact_uid_may_select_current_governance") is not False:
        raise RuntimeError("specification manifest artifact uid still selects current governance")
    if manifest_doc.get("display_version_may_select_current_governance") is not False:
        raise RuntimeError("specification manifest display version still selects current governance")
    if (manifest_doc.get("resolution_contract") or {}).get("canonical_root") != spec_root_rel:
        raise RuntimeError("manifest canonical_root does not match registry rules_root")

    if governance_role == "GOVERNANCE_REVISION_CANDIDATE":
        if identity.get("status") != "CANDIDATE":
            raise RuntimeError("candidate governance identity status drift")
        for key in ("predecessor_branch", "predecessor_head_sha", "predecessor_root_manifest_ref",
                    "predecessor_governance_revision", "authorization_record_url", "authorized_scope"):
            if identity.get(key) in (None, "", []):
                raise RuntimeError("candidate governance identity missing: " + key)
        root_manifest = load_yaml(ROOT / str(identity["predecessor_root_manifest_ref"]))
        if root_manifest.get("governance_revision") != identity.get("predecessor_governance_revision"):
            raise RuntimeError("candidate predecessor root revision drift")

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
        "specification_root": spec_root_rel,
        "specification_manifest": str(manifest.relative_to(ROOT)),
        "specification_bundle_uid": manifest_doc.get("artifact_uid"),
        "specification_bundle_display_version": manifest_doc.get("display_version"),
        "runtime_bundle_sha256": digest.hexdigest(),
        "component_files": files,
        "lifecycle_registry": registry.get("lifecycle_registry"),
        "stage_invariant_registry": registry.get("stage_invariant_registry"),
        "product_execution_branch": registry.get("product_execution_branch"),
        "test_state_root": None,
        "test_state_root_status": "RETIRED_NOT_PART_OF_CURRENT_GOVERNANCE_REGISTRY",
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
