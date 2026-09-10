import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("Current topology keeps all 18 pages while Global L1 remains 8+8", async () => {
  const manifest = await read("authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml");
  const nav = await read("authority/global/ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY_FINAL_LOCKED.yaml");
  const info = await read("authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml");
  const iam = await read("authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");
  const infoRoute = await read("src/app/info/page.tsx");
  const knowledgeRoute = await read("src/app/admin/knowledge/page.tsx");

  assert.match(manifest, /current_page_count:\s*18/);
  assert.match(manifest, /front_l1_count:\s*8/);
  assert.match(manifest, /admin_l1_count:\s*8/);
  assert.match(manifest, /authority\/pages\/workspace\/INFO-01\/ACPOS_INFO-01_FINAL_LOCKED_ENCODING\.yaml/);
  assert.match(manifest, /authority\/pages\/admin\/KB-01\/ACPOS_KB-01_FINAL_LOCKED_ENCODING\.yaml/);

  assert.match(nav, /revision:\s*2026-09-07-USER-RECONFIRM-FRONT8-ADMIN8-NON_L1_INFO_KB/);
  assert.match(nav, /front_workspace_navigation:[\s\S]*?count:\s*8/);
  assert.match(nav, /admin_navigation:[\s\S]*?count:\s*8/);
  assert.match(nav, /page_file_may_add_global_l1:\s*false/);

  assert.match(info, /global_l1:\s*false/);
  assert.doesNotMatch(info, /navigation_id:\s*NAV-09|navigation_mode:\s*FRONT_L1/);
  assert.doesNotMatch(iam, /FRONT-L1-09|ADMIN-L1-KNOWLEDGE|9X9|前台 9 L1|後台 9 L1|all nine|Nine frontend|Nine backend|Exactly 9/);
  assert.match(iam, /前台 8 L1/);
  assert.match(iam, /後台 8 L1/);
  assert.match(iam, /Exactly 8 current frontend permission choices in exact order/);
  assert.match(iam, /Exactly 8 confirmed backend permission choices in exact order/);
  const fixedLabels = iam.match(/fixed_l1_labels_zh_tw:([\s\S]*?)hard_locks:/)?.[1] ?? "";
  assert.doesNotMatch(fixedLabels, /最新資訊|知識庫/);

  assert.doesNotMatch(infoRoute, /activeNavId=["']NAV-09["']/);
  assert.doesNotMatch(knowledgeRoute, /activeNavId=["']ADMIN-NAV-09["']/);
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
