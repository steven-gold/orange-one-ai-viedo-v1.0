#!/usr/bin/env python3
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

TARGET = "tests/release/authority.test.mjs"
PRE_BLOB = "8ee2ead8ff97d6a11ef6277d966a7d50ef25add7"
POST_BLOB = "a91ab5d3300d92799abaf8cef0a6790317127c09"

OLD = r'''test("Current Authority contains exactly 18 unique page authorities", () => {
  const pages = [...manifest.matchAll(/^  - (authority\/pages\/[^\n]+)$/gm)].map((match) => match[1]);
  assert.equal(pages.length, 18);
  assert.equal(new Set(pages).size, 18);
  assert.match(manifest, /current_page_count:\s*18/);
});
'''

NEW = r'''function currentAuthoritySetSection(name) {
  const lines = manifest.split(/\r?\n/);
  const start = lines.findIndex((line) => line === `  ${name}:`);
  assert.notEqual(start, -1, `current_authority_set.${name} must exist`);
  const values = [];
  for (let index = start + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (/^[A-Za-z0-9_]+:\s*$/.test(line) || /^  [A-Za-z0-9_]+:\s*$/.test(line)) break;
    const match = line.match(/^  - (.+)$/);
    if (match) values.push(match[1]);
  }
  return values;
}

test("Current Authority page denominator is scoped to current_authority_set.pages", () => {
  const pages = currentAuthoritySetSection("pages");
  const registries = currentAuthoritySetSection("registries");
  const declared = Number(manifest.match(/^current_page_count:\s*(\d+)$/m)?.[1] ?? "NaN");
  assert.ok(Number.isInteger(declared), "current_page_count must be an integer");
  assert.equal(pages.length, declared);
  assert.equal(new Set(pages).size, pages.length);
  assert.equal(pages.filter((path) => path.includes("/CORE-01/CORE_CURRENT_CANONICAL_VISUAL_")).length, 0);
  assert.deepEqual(registries, [
    "authority/pages/workspace/CORE-01/CORE_CURRENT_CANONICAL_VISUAL_FINAL_LOCKED_V1.0.yaml",
  ]);
});
'''

def blob(root: Path) -> str:
    return subprocess.check_output(["git", "hash-object", TARGET], cwd=root, text=True).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product-root", required=True)
    args = ap.parse_args()
    root = Path(args.product_root).resolve()
    target = root / TARGET
    if not target.is_file():
        raise SystemExit("PATCH_TARGET_MISSING")
    before = blob(root)
    if before != PRE_BLOB:
        raise SystemExit(f"PATCH_PREIMAGE_BLOB_MISMATCH:{before}")
    source = target.read_text(encoding="utf-8")
    if source.count(OLD) != 1:
        raise SystemExit(f"PATCH_PREIMAGE_BLOCK_COUNT:{source.count(OLD)}")
    target.write_text(source.replace(OLD, NEW), encoding="utf-8")
    after = blob(root)
    if after != POST_BLOB:
        raise SystemExit(f"PATCH_POSTIMAGE_BLOB_MISMATCH:{after}")
    changed = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True).splitlines()
    if len(changed) != 1 or not changed[0].endswith(" " + TARGET):
        raise SystemExit("PATCH_WRITESET_INVALID:" + "|".join(changed))
    print(f"PASS TEST_ONLY_SOURCE_PATCH path={TARGET} pre_blob={before} post_blob={after}")

if __name__ == "__main__":
    main()
