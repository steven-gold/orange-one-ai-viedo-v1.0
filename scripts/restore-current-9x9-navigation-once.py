from pathlib import Path
import json
import re
import subprocess

ROOT = Path('.')

def read(path: str) -> str:
    return (ROOT / path).read_text()

def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text)

def show(ref: str, path: str) -> str:
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], text=True)

def replace_once(text: str, old: str, new: str, path: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one occurrence of {old!r}, found {count}')
    return text.replace(old, new, 1)

def replace_count(text: str, old: str, new: str, expected: int, path: str) -> str:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f'{path}: expected {expected} occurrences of {old!r}, found {count}')
    return text.replace(old, new)

# 1) Restore the canonical 9x9 Navigation Authority exactly from the state immediately
# before the erroneous 2026-09-07 8x8 authority commit.
nav_path = 'authority/global/ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY_FINAL_LOCKED.yaml'
nav = show('2848e4dc949ffe3ece967dbb59c530aaa5861a57', nav_path)
if 'front_workspace_navigation:\n  owner:' not in nav or 'count: 9' not in nav or 'NAV-09' not in nav or 'ADMIN-NAV-09' not in nav:
    raise SystemExit('historical 9x9 Navigation Authority source is not the expected topology')
write(nav_path, nav)

# 2) Restore the 9-item Global Shell authority from the last pre-error 9x9 source.
shell_path = 'authority/global/GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY_FINAL_LOCKED_V1.9.yaml'
shell = show('fc74dfb973073455895772b05307d97133348eeb', shell_path)
for token in ['count: 9', 'nav_id: NAV-09', 'control_uid: GHS-CTL-NAV-09', 'All nine navigation items']:
    if token not in shell:
        raise SystemExit(f'9x9 shell source missing {token}')
write(shell_path, shell)

# 3) Keep the Sep-11 Current Manifest/runtime cleanup, but restore its topology counts.
manifest_path = 'authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml'
manifest = read(manifest_path)
manifest = replace_once(manifest, 'front_l1_count: 8\n', 'front_l1_count: 9\n', manifest_path)
manifest = replace_once(manifest, 'admin_l1_count: 8\n', 'admin_l1_count: 9\n', manifest_path)
write(manifest_path, manifest)

# 4) Keep the Sep-11 System Authority execution-state cleanup, only restore 9x9 navigation facts.
system_path = 'authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml'
system = read(system_path)
system = replace_count(system, '    l1_count: 8\n', '    l1_count: 9\n', 2, system_path)
system = replace_once(system, '    - workspace:STR-01\n  admin:\n', '    - workspace:STR-01\n    - workspace:INFO-01\n  admin:\n', system_path)
system = replace_once(system, '    - admin:STR-01\npage_title_rule:\n', '    - admin:STR-01\n    - admin:KB-01\npage_title_rule:\n', system_path)
system = replace_once(
    system,
    '- Front workspace navigation has exactly 8 L1 items.\n- Admin navigation has exactly 8 L1 items.\n- INFO-01 remains a Current front workspace page but is not a Global L1 item.\n- KB-01 remains a Current admin page but is not a Global L1 item.\n',
    '- Front workspace navigation has exactly 9 L1 items.\n- Admin navigation has exactly 9 L1 items including Knowledge.\n- INFO-01 is the ninth front L1.\n- KB-01 is the ninth admin L1.\n',
    system_path,
)
write(system_path, system)

# 5) Restore IAM Page Authority 9x9 content from the pre-cleanup Current file, while
# retaining the Sep-11 rule that mutable runtime/deployment state lives outside Page Authority.
iam_authority_path = 'authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml'
iam = show('4c5430e83ab389df82c0ec652bee962f08e6c50b', iam_authority_path)
iam = replace_once(iam, '  revision: 2026-08-30-CURRENT-NAV-9X9-ALIGNMENT\n', '  revision: 2026-09-11-USER-RESTORE-CURRENT-NAV-9X9\n', iam_authority_path)
iam = replace_once(iam, '  system_implementation_status: NOT_EXECUTED\n', '', iam_authority_path)
iam = replace_once(
    iam,
    '  truthful_status_rule: This file completes the page design/encoding only. Application code, master merge, runtime, sandbox, regression, E2E and\n    production deployment are not executed by this file.\n',
    '  execution_state_policy:\n    mutable_execution_state_embedded: false\n    current_state_owner: CURRENT_EXECUTION_STATE.json\n    production_evidence_owner: docs/construction/evidence/\n',
    iam_authority_path,
)
write(iam_authority_path, iam)

# INFO-01 itself was a valid post-R9 Current NAV-09 page. Restore its exact pre-cleanup page authority.
info_authority_path = 'authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml'
info = show('4c5430e83ab389df82c0ec652bee962f08e6c50b', info_authority_path)
if 'global_l1: true' not in info or 'navigation_id: NAV-09' not in info:
    raise SystemExit('pre-cleanup INFO-01 does not contain the expected NAV-09 Current contract')
write(info_authority_path, info)

# 6) Restore 9th entries in current client shell without reverting later runtime/identity changes.
app_shell_path = 'src/components/shell/AppShell.tsx'
app_shell = read(app_shell_path)
app_shell = replace_once(
    app_shell,
    '  { id: "NAV-08", pageUid: "workspace:STR-01", labelKey: "global.nav.strategy", icon: "strategy", href: "/strategy" },\n] as const;',
    '  { id: "NAV-08", pageUid: "workspace:STR-01", labelKey: "global.nav.strategy", icon: "strategy", href: "/strategy" },\n  { id: "NAV-09", pageUid: "workspace:INFO-01", labelKey: "global.nav.latest_information", icon: "info", href: "/info" },\n] as const;',
    app_shell_path,
)
app_shell = replace_once(
    app_shell,
    '  { id: "ADMIN-NAV-08", pageUid: "admin:STR-01", labelKey: "global.admin.strategy", icon: "strategy", href: "/admin/strategy" },\n] as const;',
    '  { id: "ADMIN-NAV-08", pageUid: "admin:STR-01", labelKey: "global.admin.strategy", icon: "strategy", href: "/admin/strategy" },\n  { id: "ADMIN-NAV-09", pageUid: "admin:KB-01", labelKey: "global.admin.knowledge", icon: "asset", href: "/admin/knowledge" },\n] as const;',
    app_shell_path,
)
write(app_shell_path, app_shell)

# 7) Restore IAM UI's ninth frontend/admin permission choices and select-all semantics.
iam_visual_path = 'src/components/pages/IamVisual.tsx'
iam_visual = read(iam_visual_path)
iam_visual = replace_once(
    iam_visual,
    '  ["FRONT-L1-08", "global.nav.strategy"],\n] as const;',
    '  ["FRONT-L1-08", "global.nav.strategy"],\n  ["FRONT-L1-09", "global.nav.latest_information"],\n] as const;',
    iam_visual_path,
)
iam_visual = replace_once(
    iam_visual,
    '  ["ADMIN-L1-STRATEGY", "global.admin.strategy"],\n] as const;',
    '  ["ADMIN-L1-STRATEGY", "global.admin.strategy"],\n  ["ADMIN-L1-KNOWLEDGE", "global.admin.knowledge"],\n] as const;',
    iam_visual_path,
)
iam_visual = replace_once(iam_visual, '      data-frontend-l1-count="8"\n', '      data-frontend-l1-count="9"\n', iam_visual_path)
iam_visual = replace_once(iam_visual, '      data-backend-l1-count="8"\n', '      data-backend-l1-count="9"\n', iam_visual_path)
iam_visual = replace_count(iam_visual, 'length === 8', 'length === 9', 4, iam_visual_path)
write(iam_visual_path, iam_visual)

iam_catalog_path = 'src/i18n/iamCatalog.ts'
iam_catalog = read(iam_catalog_path)
iam_catalog = replace_once(iam_catalog, 'frontL1: { "zh-TW": "前台 8 L1", "zh-CN": "前台 8 L1", en: "Frontend 8 L1" }', 'frontL1: { "zh-TW": "前台 9 L1", "zh-CN": "前台 9 L1", en: "Frontend 9 L1" }', iam_catalog_path)
iam_catalog = replace_once(iam_catalog, 'backL1: { "zh-TW": "後台 8 L1", "zh-CN": "后台 8 L1", en: "Admin 8 L1" }', 'backL1: { "zh-TW": "後台 9 L1", "zh-CN": "后台 9 L1", en: "Admin 9 L1" }', iam_catalog_path)
write(iam_catalog_path, iam_catalog)

# 8) Restore active navigation identity on the two ninth routes.
info_route_path = 'src/app/info/page.tsx'
info_route = read(info_route_path)
info_route = replace_once(info_route, '  return <AppShell><InfoVisual /></AppShell>;\n', '  return <AppShell activeNavId="NAV-09"><InfoVisual /></AppShell>;\n', info_route_path)
write(info_route_path, info_route)

kb_route_path = 'src/app/admin/knowledge/page.tsx'
kb_route = read(kb_route_path)
kb_route = replace_once(kb_route, '    <AppShell surface="admin">\n', '    <AppShell surface="admin" activeNavId="ADMIN-NAV-09">\n', kb_route_path)
write(kb_route_path, kb_route)

# 9) Replace the accidental 8x8 regression with the corrected topology invariant.
test_path = 'tests/release/page-authority-current-truth.test.mjs'
write(test_path, '''import test from "node:test";\nimport assert from "node:assert/strict";\nimport { readFile } from "node:fs/promises";\n\nconst read = (path) => readFile(path, "utf8");\n\ntest("Current topology is 18 pages with 9+9 Global L1", async () => {\n  const manifest = await read("authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml");\n  const nav = await read("authority/global/ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY_FINAL_LOCKED.yaml");\n  const system = await read("authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml");\n  const shell = await read("authority/global/GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY_FINAL_LOCKED_V1.9.yaml");\n  const info = await read("authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml");\n  const iam = await read("authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");\n  const appShell = await read("src/components/shell/AppShell.tsx");\n  const iamVisual = await read("src/components/pages/IamVisual.tsx");\n  const infoRoute = await read("src/app/info/page.tsx");\n  const knowledgeRoute = await read("src/app/admin/knowledge/page.tsx");\n\n  assert.match(manifest, /current_page_count:\\s*18/);\n  assert.match(manifest, /front_l1_count:\\s*9/);\n  assert.match(manifest, /admin_l1_count:\\s*9/);\n  assert.match(nav, /front_workspace_navigation:[\\s\\S]*?count:\\s*9/);\n  assert.match(nav, /admin_navigation:[\\s\\S]*?count:\\s*9/);\n  assert.match(nav, /nav_id:\\s*NAV-09[\\s\\S]*?page_uid:\\s*workspace:INFO-01/);\n  assert.match(nav, /nav_id:\\s*ADMIN-NAV-09[\\s\\S]*?page_uid:\\s*admin:KB-01/);\n  assert.match(system, /front_workspace:[\\s\\S]*?l1_count:\\s*9[\\s\\S]*?- workspace:INFO-01/);\n  assert.match(system, /admin:[\\s\\S]*?l1_count:\\s*9[\\s\\S]*?- admin:KB-01/);\n  assert.match(shell, /navigation:[\\s\\S]*?count:\\s*9/);\n  assert.match(shell, /control_uid:\\s*GHS-CTL-NAV-09/);\n  assert.match(info, /global_l1:\\s*true/);\n  assert.match(info, /navigation_id:\\s*NAV-09/);\n  assert.match(iam, /FRONT-L1-09/);\n  assert.match(iam, /ADMIN-L1-KNOWLEDGE/);\n  assert.match(iam, /前台 9 L1/);\n  assert.match(iam, /後台 9 L1/);\n  assert.match(iam, /Exactly 9 current frontend permission choices in exact order/);\n  assert.match(iam, /Exactly 9 confirmed backend permission choices in exact order/);\n  assert.match(appShell, /id: "NAV-09"[\\s\\S]*?pageUid: "workspace:INFO-01"/);\n  assert.match(appShell, /id: "ADMIN-NAV-09"[\\s\\S]*?pageUid: "admin:KB-01"/);\n  assert.match(iamVisual, /data-frontend-l1-count="9"/);\n  assert.match(iamVisual, /data-backend-l1-count="9"/);\n  assert.match(infoRoute, /activeNavId="NAV-09"/);\n  assert.match(knowledgeRoute, /activeNavId="ADMIN-NAV-09"/);\n});\n\ntest("Current page authorities externalize mutable execution and deployment state", async () => {\n  const paths = [\n    "authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml",\n    "authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",\n    "authority/pages/admin/DEV-01/ACPOS_DEV-01_ENTERPRISE_AUTOMATION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",\n    "authority/pages/admin/SOC-01/ACPOS_SOC-01_SOCIAL_PUBLISHING_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",\n    "authority/pages/admin/ERP-01/ACPOS_ERP-01_ERP_FINANCE_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",\n    "authority/pages/admin/AIAPI-01/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml",\n    "authority/pages/admin/STR-01/ACPOS_STRATEGY_CENTER_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",\n  ];\n  for (const path of paths) {\n    const text = await read(path);\n    assert.match(text, /execution_state_policy:/, path);\n    assert.match(text, /current_state_owner:\\s*CURRENT_EXECUTION_STATE\\.json/, path);\n    assert.doesNotMatch(text, /system_implementation_status:\\s*NOT_EXECUTED|implementation_status:\\s*RUNTIME_BOUND_PENDING_RELEASE|runtime_truth:/, path);\n  }\n  const aiapi = await read(paths[5]);\n  assert.doesNotMatch(aiapi, /PASS_RELEASE_GATE_384|PENDING_SINGLE_MAIN_RELEASE/);\n  const strategy = await read(paths[6]);\n  assert.doesNotMatch(strategy, /IMPLEMENTATION_REQUIRED_NOT_EXECUTED|production_deployment:\\s*NOT_EXECUTED/);\n});\n''')

# 10) Correct Current State/history: 9x9 is the Current user ruling; the Sep-07 8x8 commits are recorded as erroneous, not authority.
state_path = 'CURRENT_EXECUTION_STATE.json'
state = json.loads(read(state_path))
state['schema_version'] = '2.3'
state['navigation_topology'] = {
    'current_pages_total': 18,
    'current_page_partition': '9 workspace-facing + 9 admin',
    'global_front_l1_count': 9,
    'global_admin_l1_count': 9,
    'front_l1_09': 'workspace:INFO-01',
    'admin_l1_09': 'admin:KB-01',
    'history': {
        'correct_post_r9_9x9_construction_commit': '357fdb5601ba3353476594e850b66229d3c333a0',
        'erroneous_8x8_shell_commit': '2848e4dc949ffe3ece967dbb59c530aaa5861a57',
        'erroneous_8x8_authority_commit': '613991373b01f7f89e77ea45a2f18657e4a63cad'
    },
    'rule': 'Current topology is 18 Current pages and 9+9 Global L1. INFO-01 is FRONT-L1-09/NAV-09 and KB-01 is ADMIN-L1-KNOWLEDGE/ADMIN-NAV-09. The Sep-07 8x8 changes were execution errors and must not be used as Current authority.'
}
cleanup = state.setdefault('cleanup', {})
cleanup['page_authority_cleanup_classification_correction'] = 'Aug-30 9x9 was post-R9 Current construction and is correct. The Sep-07 8x8 shell/navigation changes were execution errors. Any Sep-11 cleanup that aligned IAM/INFO to 8x8 is superseded by this restoration.'
cleanup['page_authority_cleanup_scope'] = [
    'workspace:INFO-01 restored as Current FRONT-L1-09 / NAV-09; page remains Current',
    'admin:IAM-01 restored to Current 9x9 L1 permission model including INFO-01 and KB-01',
    'admin:SYS-01 mutable pending-release status remains externalized',
    'admin:DEV-01 mutable NOT_EXECUTED status remains externalized',
    'admin:SOC-01 mutable NOT_EXECUTED status remains externalized',
    'admin:ERP-01 mutable NOT_EXECUTED status remains externalized',
    'admin:AIAPI-01 old Release/deployment runtime snapshot remains externalized',
    'admin:STR-01 old NOT_EXECUTED runtime snapshot remains externalized'
]
cleanup['navigation_route_residual_fix'] = {
    'status': '9X9_RESTORED_SOURCE_RELEASE_PENDING',
    'info_route_nav_09_restored': True,
    'knowledge_route_admin_nav_09_restored': True,
    'permanent_regression_updated': test_path
}
page_scan = cleanup.setdefault('page_authority_scan', {})
page_scan['workspace:INFO-01'] = 'CURRENT_FRONT_L1_09_RESTORED'
page_scan['admin:IAM-01'] = 'CURRENT_9X9_PERMISSION_MODEL_RESTORED'
page_scan['admin:KB-01'] = 'CURRENT_ADMIN_L1_09_RETAINED'
state['current_batch_validation'] = {
    'item': 'RESTORE_USER_CONFIRMED_9X9_CURRENT_TOPOLOGY',
    'source_head': 'AUTOMATION_COMMIT_PENDING',
    'release_gate': 'PENDING'
}
state['remaining_queue_policy'] = 'Only top-level closures are counted here. Discovered subdependencies remain inside their owning item and must not inflate the queue count.'
state['next_execution_order'] = [
    'Close the WorkPackage Current operation/runtime owner blocker without restoring superseded compiler authority',
    'Classify the 97 no-RLS tables and verify runtime-role enforcement',
    'Run fresh Production External Provider acceptance',
    'Run fresh Production Queue/Worker/DLQ acceptance',
    'Run Production Read Models acceptance',
    'Close MFA/risk/org-owner prerequisites',
    'Continue Gate25 disposition work for the remaining 1226 NOT_EXECUTED resources'
]
write(state_path, json.dumps(state, ensure_ascii=False, indent=2) + '\n')

progress_path = 'docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml'
progress = read(progress_path)
progress = replace_once(progress, '  global_front_l1: 8\n', '  global_front_l1: 9\n', progress_path)
progress = replace_once(progress, '  global_admin_l1: 8\n', '  global_admin_l1: 9\n', progress_path)
progress = replace_once(progress, '  current_non_global_l1_pages:\n    - workspace:INFO-01\n    - admin:KB-01\n', '  front_l1_09: workspace:INFO-01\n  admin_l1_09: admin:KB-01\n', progress_path)
progress = replace_once(
    progress,
    '    post_r9_9x9_construction_commit: 357fdb5601ba3353476594e850b66229d3c333a0\n    user_8x8_shell_restore_commit: 2848e4dc949ffe3ece967dbb59c530aaa5861a57\n    user_8x8_navigation_authority_commit: 613991373b01f7f89e77ea45a2f18657e4a63cad\n  rule: 18 Current pages and 16 Global L1 menu items are different counts. The Aug-30 9x9 navigation was post-R9 construction, then explicitly superseded by the Sep-07 user-confirmed 8x8 Global L1 topology. INFO-01 and KB-01 remain Current pages.\n',
    '    correct_post_r9_9x9_construction_commit: 357fdb5601ba3353476594e850b66229d3c333a0\n    erroneous_8x8_shell_commit: 2848e4dc949ffe3ece967dbb59c530aaa5861a57\n    erroneous_8x8_navigation_authority_commit: 613991373b01f7f89e77ea45a2f18657e4a63cad\n  rule: Current topology is 18 Current pages and 9+9 Global L1. INFO-01 is the ninth front L1 and KB-01 is the ninth admin L1. The Sep-07 8x8 changes were execution errors.\n',
    progress_path,
)
progress = replace_once(
    progress,
    '  page_authority_cleanup_classification_correction: Aug-30 9x9 was post-R9 construction, not legacy R9; its L1 topology was superseded by user-confirmed Sep-07 8x8 authority. Page deletion was not part of the cleanup.\n  navigation_route_residual_fix: SOURCE_PATCHED_RELEASE_PENDING\n',
    '  page_authority_cleanup_classification_correction: Aug-30 9x9 is post-R9 Current construction and is correct; Sep-07 8x8 was an execution error. Sep-11 8x8 alignment is superseded by the 9x9 restoration.\n  navigation_route_residual_fix: 9X9_RESTORED_SOURCE_RELEASE_PENDING\n',
    progress_path,
)
write(progress_path, progress)

# Final source-level invariants before tests.
checks = {
    nav_path: ['count: 9', 'NAV-09', 'ADMIN-NAV-09'],
    manifest_path: ['front_l1_count: 9', 'admin_l1_count: 9'],
    system_path: ['l1_count: 9', 'workspace:INFO-01', 'admin:KB-01'],
    shell_path: ['count: 9', 'GHS-CTL-NAV-09'],
    iam_authority_path: ['FRONT-L1-09', 'ADMIN-L1-KNOWLEDGE', '前台 9 L1', '後台 9 L1'],
    info_authority_path: ['global_l1: true', 'navigation_id: NAV-09'],
    app_shell_path: ['id: "NAV-09"', 'id: "ADMIN-NAV-09"'],
    iam_visual_path: ['data-frontend-l1-count="9"', 'data-backend-l1-count="9"'],
}
for path, tokens in checks.items():
    text = read(path)
    for token in tokens:
        if token not in text:
            raise SystemExit(f'{path}: missing restored invariant {token}')

print('ACPOS_9X9_CURRENT_TOPOLOGY_SOURCE_RESTORE_PASS')
