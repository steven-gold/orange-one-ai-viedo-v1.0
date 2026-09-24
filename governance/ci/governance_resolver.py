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

    spec_root = ROOT / spec_root_rel
    if not spec_root.is_dir():
        raise RuntimeError("specification root missing: " + spec_root_rel)

    manifest = spec_root / "SPECIFICATION_MANIFEST.yaml"
    manifest_doc = load_yaml(manifest)
    governance_uid = manifest_doc.get("artifact_uid")
    display_version = manifest_doc.get("display_version")
    if not isinstance(governance_uid, str) or not governance_uid:
        raise RuntimeError("current specification manifest artifact_uid missing")
    if not isinstance(display_version, str) or not display_version:
        raise RuntimeError("current specification manifest display_version missing")

    resolution = manifest_doc.get("resolution_contract") or {}
    if resolution.get("canonical_root") != spec_root_rel:
        raise RuntimeError("manifest canonical_root does not match registry rules_root")

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
        "governance_uid": governance_uid,
        "display_version": display_version,
        "specification_root": spec_root_rel,
        "specification_manifest": str(manifest.relative_to(ROOT)),
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
