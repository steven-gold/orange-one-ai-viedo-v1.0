#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "governance/specifications/REGISTRY.yaml"


def get_scalar(text, key):
    pattern = r"^\s*" + re.escape(key) + r":\s*([^#\n]+?)\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise RuntimeError("missing registry key: " + key)
    return match.group(1).strip().strip("\"'")


def resolve():
    text = REGISTRY.read_text(encoding="utf-8")
    spec_root_rel = get_scalar(text, "specification_root")
    manifest_rel = get_scalar(text, "specification_manifest")
    test_root_rel = get_scalar(text, "test_state_root")
    governance_uid = get_scalar(text, "governance_uid")
    display_version = get_scalar(text, "display_version")

    if re.search(r"(^|/)v\d+\.\d+(?:\.\d+)?(?:/|$)", spec_root_rel):
        raise RuntimeError("stable specification root may not contain a semantic version segment")

    spec_root = ROOT / spec_root_rel
    manifest = ROOT / manifest_rel
    test_root = ROOT / test_root_rel
    if not spec_root.is_dir():
        raise RuntimeError("specification root missing: " + spec_root_rel)
    if not manifest.is_file():
        raise RuntimeError("specification manifest missing: " + manifest_rel)
    if not test_root.is_dir():
        raise RuntimeError("test state root missing: " + test_root_rel)

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

    if governance_uid not in manifest.read_text(encoding="utf-8"):
        raise RuntimeError("registry governance_uid does not match specification manifest")

    return {
        "registry": str(REGISTRY.relative_to(ROOT)),
        "governance_uid": governance_uid,
        "display_version": display_version,
        "specification_root": spec_root_rel,
        "specification_manifest": manifest_rel,
        "test_state_root": test_root_rel,
        "runtime_bundle_sha256": digest.hexdigest(),
        "component_files": files,
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
        print(result["test_state_root"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
