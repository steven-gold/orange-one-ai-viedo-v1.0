from pathlib import Path
import re


def read(path: str) -> str:
    return Path(path).read_text()


def write(path: str, text: str) -> None:
    Path(path).write_text(text)


def replace_once(text: str, old: str, new: str, path: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one replacement, found {count}: {old[:120]!r}")
    return text.replace(old, new, 1)


def replace_truthful_status(text: str, path: str) -> str:
    pattern = r"^  truthful_status_rule:.*\n(?:    .*\n)*"
    replacement = (
        "  execution_state_policy:\n"
        "    mutable_execution_state_embedded: false\n"
        "    current_state_owner: CURRENT_EXECUTION_STATE.json\n"
        "    production_evidence_owner: docs/construction/evidence/\n"
    )
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"{path}: truthful_status_rule replacement count={count}")
    return updated


# INFO-01 is Current but explicitly non-L1 under Current Navigation Authority.
path = "authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml"
text = read(path)
text = replace_once(
    text,
    "  revision: 2026-08-30-USER-APPROVED-FRONT-L1-NAV09\n",
    "  revision: 2026-09-11-CURRENT-NON-GLOBAL-L1-ALIGNMENT\n",
    path,
)
text = replace_once(
    text,
    """  navigation_mode: FRONT_L1
  global_l1: true
  navigation_id: NAV-09
  navigation_label_zh: 最新資訊
  navigation_label_en: Latest Information
  navigation_entry_authority: ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY@V1.0
""",
    """  navigation_mode: NON_GLOBAL_L1_CURRENT_PAGE
  global_l1: false
  navigation_entry_authority: ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY@V1.0
  navigation_rule: This Page Authority does not declare or add a Global L1 item; global navigation is owned only by Current Navigation Authority.
""",
    path,
)
write(path, text)

# IAM-01 must expose only Current 8+8 L1 configuration choices; INFO/KB remain Current non-L1 pages.
path = "authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml"
text = read(path)
text = replace_once(
    text,
    "  revision: 2026-08-30-CURRENT-NAV-9X9-ALIGNMENT\n",
    "  revision: 2026-09-11-CURRENT-NAV-8X8-ALIGNMENT\n",
    path,
)
text = replace_once(text, "  system_implementation_status: NOT_EXECUTED\n", "", path)
text = replace_truthful_status(text, path)
text = replace_once(
    text,
    """  - order: 9
    bundle_key: FRONT-L1-09
    label: 最新資訊
    canonical_page_uid: workspace:INFO-01
""",
    "",
    path,
)
text = replace_once(
    text,
    """  - order: 9
    bundle_key: ADMIN-L1-KNOWLEDGE
    label: 知識庫
    canonical_page_uid: admin:KB-01
""",
    "",
    path,
)
for old, new in {
    "Select all 9 backend L1 choices in draft only; no super-admin bypass.": "Select all 8 backend L1 choices in draft only; no super-admin bypass.",
    "Select all 9 frontend L1 choices in the draft only.": "Select all 8 frontend L1 choices in the draft only.",
    "role: Nine frontend L1 permission choices only": "role: Eight frontend L1 permission choices only",
    "role: Nine backend L1 permission choices only": "role: Eight backend L1 permission choices only",
    "label: 前台 9 L1": "label: 前台 8 L1",
    "label: 後台 9 L1": "label: 後台 8 L1",
    "rule: Select/deselect all nine frontend L1 draft choices.": "rule: Select/deselect all eight frontend L1 draft choices.",
    "rule: Select/deselect all nine backend L1 draft choices; not super-admin.": "rule: Select/deselect all eight backend L1 draft choices; not super-admin.",
    "  condition: Exactly 9 current frontend permission choices in exact order.": "  condition: Exactly 8 current frontend permission choices in exact order.",
    "  condition: Exactly 9 confirmed backend permission choices in exact order.": "  condition: Exactly 8 confirmed backend permission choices in exact order.",
}.items():
    text = replace_once(text, old, new, path)
# Remove the non-L1 Current pages from the fixed L1 display-label lists as well.
text = replace_once(text, "    - 戰略中心\n    - 最新資訊\n    backend:\n", "    - 戰略中心\n    backend:\n", path)
text = replace_once(text, "    - QA 評分項目\n    - 戰略中心\n    - 知識庫\n", "    - QA 評分項目\n    - 戰略中心\n", path)
write(path, text)

# Page Authority files define contracts, not mutable release/deployment progress.
for path, status_line in [
    ("authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml", "  implementation_status: RUNTIME_BOUND_PENDING_RELEASE\n"),
    ("authority/pages/admin/DEV-01/ACPOS_DEV-01_ENTERPRISE_AUTOMATION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml", "  system_implementation_status: NOT_EXECUTED\n"),
    ("authority/pages/admin/SOC-01/ACPOS_SOC-01_SOCIAL_PUBLISHING_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml", "  system_implementation_status: NOT_EXECUTED\n"),
    ("authority/pages/admin/ERP-01/ACPOS_ERP-01_ERP_FINANCE_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml", "  system_implementation_status: NOT_EXECUTED\n"),
]:
    text = read(path)
    text = replace_once(text, status_line, "", path)
    text = replace_truthful_status(text, path)
    write(path, text)

# AIAPI-01 and admin STR-01 carry a whole stale runtime_truth snapshot. Externalize it.
for path in [
    "authority/pages/admin/AIAPI-01/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml",
    "authority/pages/admin/STR-01/ACPOS_STRATEGY_CENTER_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
]:
    text = read(path)
    pattern = r"^runtime_truth:\n(?:  .*\n)+(?=page_contract:)"
    replacement = (
        "execution_state_policy:\n"
        "  mutable_execution_state_embedded: false\n"
        "  current_state_owner: CURRENT_EXECUTION_STATE.json\n"
        "  production_evidence_owner: docs/construction/evidence/\n"
        "  rule: Runtime, validation, Release and Production deployment completion are resolved only from Current execution evidence.\n"
    )
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"{path}: runtime_truth replacement count={count}")
    write(path, updated)

# Existing release tests must validate runtime reachability without freezing obsolete mutable deployment state.
path = "tests/release/iam-reachability.test.mjs"
text = read(path)
text = replace_once(
    text,
    "  assert.match(authority, /system_implementation_status:\\s*NOT_EXECUTED/);\n",
    "  assert.match(authority, /execution_state_policy:/);\n  assert.match(authority, /mutable_execution_state_embedded:\\s*false/);\n  assert.match(authority, /current_state_owner:\\s*CURRENT_EXECUTION_STATE\\.json/);\n  assert.doesNotMatch(authority, /system_implementation_status:\\s*NOT_EXECUTED/);\n",
    path,
)
write(path, text)

path = "tests/release/runtime-hardening.test.mjs"
text = read(path)
text = replace_once(
    text,
    "  assert.match(authority, /implementation_status:\\s*RUNTIME_BOUND_PENDING_RELEASE/);\n",
    "  assert.match(authority, /execution_state_policy:/);\n  assert.match(authority, /mutable_execution_state_embedded:\\s*false/);\n  assert.match(authority, /current_state_owner:\\s*CURRENT_EXECUTION_STATE\\.json/);\n  assert.doesNotMatch(authority, /implementation_status:\\s*RUNTIME_BOUND_PENDING_RELEASE/);\n",
    path,
)
write(path, text)

# Permanent regression against revival of superseded page execution snapshots and 9x9 navigation.
Path("tests/release/page-authority-current-truth.test.mjs").write_text(r'''import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("INFO and IAM follow the Current 8+8 navigation authority", async () => {
  const info = await read("authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml");
  const iam = await read("authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");
  assert.match(info, /global_l1:\s*false/);
  assert.doesNotMatch(info, /navigation_id:\s*NAV-09|navigation_mode:\s*FRONT_L1/);
  assert.doesNotMatch(iam, /FRONT-L1-09|ADMIN-L1-KNOWLEDGE|9X9|前台 9 L1|後台 9 L1|all nine|Nine frontend|Nine backend|Exactly 9/);
  assert.match(iam, /前台 8 L1/);
  assert.match(iam, /後台 8 L1/);
  assert.match(iam, /Exactly 8 current frontend permission choices in exact order/);
  assert.match(iam, /Exactly 8 confirmed backend permission choices in exact order/);
  const fixedLabels = iam.match(/fixed_l1_labels_zh_tw:([\s\S]*?)hard_locks:/)?.[1] ?? "";
  assert.doesNotMatch(fixedLabels, /最新資訊|知識庫/);
});

test("Current page authorities externalize mutable execution and deployment state", async () => {
  const paths = [
    "authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml",
    "authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
    "authority/pages/admin/DEV-01/ACPOS_DEV-01_ENTERPRISE_AUTOMATION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
    "authority/pages/admin/SOC-01/ACPOS_SOC-01_SOCIAL_PUBLISHING_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
    "authority/pages/admin/ERP-01/ACPOS_ERP-01_ERP_FINANCE_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
    "authority/pages/admin/AIAPI-01/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml",
    "authority/pages/admin/STR-01/ACPOS_STRATEGY_CENTER_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
  ];
  for (const path of paths) {
    const text = await read(path);
    assert.match(text, /execution_state_policy:/, path);
    assert.match(text, /current_state_owner:\s*CURRENT_EXECUTION_STATE\.json/, path);
    assert.doesNotMatch(text, /system_implementation_status:\s*NOT_EXECUTED|implementation_status:\s*RUNTIME_BOUND_PENDING_RELEASE|runtime_truth:/, path);
  }
  const aiapi = await read(paths[5]);
  assert.doesNotMatch(aiapi, /PASS_RELEASE_GATE_384|PENDING_SINGLE_MAIN_RELEASE/);
  const strategy = await read(paths[6]);
  assert.doesNotMatch(strategy, /IMPLEMENTATION_REQUIRED_NOT_EXECUTED|production_deployment:\s*NOT_EXECUTED/);
});
''')

print("page authority Current-truth cleanup prepared")
