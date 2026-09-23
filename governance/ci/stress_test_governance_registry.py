#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import re
import shutil
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[2]
RESOLVER_PATH = ROOT / "governance/ci/governance_resolver.py"

spec = importlib.util.spec_from_file_location("governance_resolver_stress", RESOLVER_PATH)
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)

BASE = resolver.resolve()
BASE_UID = BASE["governance_uid"]
BASE_ROOT = BASE["specification_root"]
BASE_DIGEST = BASE["runtime_bundle_sha256"]

results = []


def record(name, passed, detail=""):
    results.append((name, passed, detail))
    print(("PASS" if passed else "FAIL") + ": " + name + (" :: " + detail if detail else ""))


def make_sandbox():
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    shutil.copytree(ROOT / "governance/specifications", root / "governance/specifications")
    shutil.copytree(ROOT / "governance/test", root / "governance/test")
    (root / "governance/ci").mkdir(parents=True, exist_ok=True)
    return td, root


def resolve_at(root):
    old_root, old_registry = resolver.ROOT, resolver.REGISTRY
    try:
        resolver.ROOT = root
        resolver.REGISTRY = root / "governance/specifications/REGISTRY.yaml"
        return resolver.resolve()
    finally:
        resolver.ROOT, resolver.REGISTRY = old_root, old_registry


def expect_block(name, mutator, contains=None):
    td, root = make_sandbox()
    try:
        mutator(root)
        try:
            resolve_at(root)
        except Exception as exc:
            text = str(exc)
            ok = contains is None or contains in text
            record(name, ok, text)
        else:
            record(name, False, "mutation unexpectedly resolved")
    finally:
        td.cleanup()


# 1. Baseline stable resolution.
record(
    "baseline_registry_resolution",
    BASE_ROOT == "governance/specifications/current" and not re.search(r"(^|/)v\d+\.\d+", BASE_ROOT),
    f"uid={BASE_UID} root={BASE_ROOT} digest={BASE_DIGEST}",
)

# 2. Display version/alias rename must not alter locator or immutable identity.
td, root = make_sandbox()
try:
    p = root / "governance/specifications/REGISTRY.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    active = data.get("active_specification")
    if not isinstance(active, dict) or active.get("display_version") != BASE["display_version"]:
        raise RuntimeError("stress fixture registry active_specification drift")
    active["display_version"] = "release-green"
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    got = resolve_at(root)
    record(
        "display_alias_rename_does_not_move_current",
        got["governance_uid"] == BASE_UID and got["specification_root"] == BASE_ROOT and got["display_version"] == "release-green",
        f"uid={got['governance_uid']} root={got['specification_root']} display={got['display_version']}",
    )
finally:
    td.cleanup()

# 3. A numerically higher unverified candidate must not become Current.
td, root = make_sandbox()
try:
    fake_locator = "governance/specifications/" + "v999.999.999"
    fake = root / fake_locator
    fake.mkdir(parents=True)
    (fake / "SPECIFICATION_MANIFEST.yaml").write_text("artifact_uid: FAKE-NEWER-CANDIDATE\n", encoding="utf-8")
    got = resolve_at(root)
    record(
        "higher_version_candidate_cannot_hijack_current",
        got["governance_uid"] == BASE_UID and got["specification_root"] == BASE_ROOT,
        f"resolved={got['specification_root']}",
    )
finally:
    td.cleanup()

# 4. Semver directory locator injection must fail closed.
def version_path_injection(root):
    reg = root / "governance/specifications/REGISTRY.yaml"
    bad_locator = "governance/specifications/" + "v9.9.9"
    data = yaml.safe_load(reg.read_text(encoding="utf-8")) or {}
    stable = data.get("stable_entrypoint")
    if not isinstance(stable, dict) or stable.get("specification_root") != "governance/specifications/current":
        raise RuntimeError("stress fixture stable_entrypoint drift")
    stable["specification_root"] = bad_locator
    reg.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

expect_block("semantic_version_locator_is_blocked", version_path_injection, "semantic version segment")

# 5. Registry/manifest UID mismatch must fail closed.
def uid_mismatch(root):
    manifest = root / "governance/specifications/current/SPECIFICATION_MANIFEST.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    if data.get("artifact_uid") != BASE_UID:
        raise RuntimeError("stress fixture manifest artifact_uid drift")
    data["artifact_uid"] = "GOV-REV-INVALID-MISMATCH"
    manifest.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

expect_block("registry_manifest_uid_mismatch_is_blocked", uid_mismatch, "governance_uid does not match")

# 6. Missing manifest must fail closed.
def missing_manifest(root):
    (root / "governance/specifications/current/SPECIFICATION_MANIFEST.yaml").unlink()

expect_block("missing_manifest_is_blocked", missing_manifest, "specification manifest missing")

# 7. Missing test root must fail closed.
def missing_test_root(root):
    shutil.rmtree(root / "governance/test")

expect_block("missing_test_root_is_blocked", missing_test_root, "test state root missing")

# 8. Any Current specification content mutation must produce a different runtime digest.
td, root = make_sandbox()
try:
    target = root / "governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml"
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    data["stress_digest_mutation_probe"] = True
    target.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    got = resolve_at(root)
    record(
        "current_content_change_recomputes_digest",
        got["runtime_bundle_sha256"] != BASE_DIGEST and got["specification_root"] == BASE_ROOT,
        f"before={BASE_DIGEST} after={got['runtime_bundle_sha256']}",
    )
finally:
    td.cleanup()

# 9. Stale copied hash outside the specification bundle may not redirect resolution.
td, root = make_sandbox()
try:
    stale = root / "consumer_state.yaml"
    stale.write_text("copied_governance_hash: 00000000000000000000000000000000\n", encoding="utf-8")
    got = resolve_at(root)
    record(
        "stale_consumer_hash_cannot_redirect_resolution",
        got["governance_uid"] == BASE_UID and got["specification_root"] == BASE_ROOT and got["runtime_bundle_sha256"] == BASE_DIGEST,
        f"root={got['specification_root']} digest={got['runtime_bundle_sha256']}",
    )
finally:
    td.cleanup()

# 10. Current manifest declarations must exactly cover all active component YAMLs.
manifest_text = (ROOT / BASE["specification_manifest"]).read_text(encoding="utf-8")
declared = set(re.findall(r"^\s*-?\s*file:\s*([^#\n]+?)\s*$", manifest_text, re.MULTILINE))
actual = {
    p.name for p in (ROOT / BASE_ROOT).glob("*.yaml")
    if p.name != "SPECIFICATION_MANIFEST.yaml"
}
record("manifest_component_coverage_exact", declared == actual, f"declared={sorted(declared)} actual={sorted(actual)}")

# 11. Legacy roots and temporary residuals must be absent from HEAD.
legacy = [
    rel for rel in (
        "governance/current",
        "governance/candidates",
        "governance/test-runtime",
        "governance/test-temporary",
    ) if (ROOT / rel).exists()
]
record("legacy_governance_roots_absent", not legacy, f"found={legacy}")

tmp_root = ROOT / "governance/test/temporary"
tmp_files = list(tmp_root.rglob("*")) if tmp_root.exists() else []
record("temporary_test_zero_residual", not tmp_root.exists(), f"entries={len(tmp_files)}")

# 12. Every active workflow and every governance Python consumer directly invoked by a workflow
#     must be free of a hard-coded semver governance locator. Mutation fixtures above construct
#     prohibited paths dynamically so the scanner tests executable locator usage, not fixture text.
pattern = re.compile(r"governance/(?:current|specifications)/v\d+(?:\.\d+)+")
active_files = set()
workflow_dir = ROOT / ".github/workflows"
for workflow in workflow_dir.glob("*.y*ml"):
    active_files.add(workflow)
    text = workflow.read_text(encoding="utf-8")
    for match in re.finditer(r"python(?:3)?\s+(governance/ci/[A-Za-z0-9_.-]+\.py)", text):
        active_files.add(ROOT / match.group(1))

hardcoded = []
for path in sorted(active_files):
    if not path.is_file():
        hardcoded.append(f"MISSING:{path.relative_to(ROOT)}")
        continue
    text = path.read_text(encoding="utf-8")
    if pattern.search(text):
        hardcoded.append(str(path.relative_to(ROOT)))
record("active_consumers_have_no_semver_governance_locator", not hardcoded, f"violations={hardcoded}")

failed = [name for name, passed, _ in results if not passed]
print(f"STRESS_SUMMARY total={len(results)} pass={len(results)-len(failed)} fail={len(failed)}")
if failed:
    print("BLOCK: governance registry stress failures: " + ", ".join(failed))
    raise SystemExit(1)
print("PASS: governance registry multidirectional stress suite")
