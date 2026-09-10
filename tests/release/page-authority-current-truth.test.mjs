import test from "node:test";
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
