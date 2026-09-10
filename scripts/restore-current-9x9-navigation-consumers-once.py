from pathlib import Path

ROOT = Path('.')

def read(path):
    return (ROOT / path).read_text()

def write(path, text):
    (ROOT / path).write_text(text)

def replace_once(text, old, new, path):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one occurrence, found {count}: {old!r}')
    return text.replace(old, new, 1)

# Reverse only the erroneous 8x8 portions of the Sep-07 integration-matrix change.
matrix_path = 'authority/global/ACPOS_PAGE_INTEGRATION_MATRIX_FINAL_LOCKED_CURRENT.yaml'
matrix = read(matrix_path)
matrix = replace_once(matrix, '  navigation: NON_L1_CURRENT_PAGE\n', '  navigation: FRONT_L1_NAV-09\n', matrix_path)
matrix = replace_once(matrix, '  admin_l1_bundle_count: 8\n', '  admin_l1_bundle_count: 9\n  knowledge_bundle: ADMIN-L1-KNOWLEDGE\n', matrix_path)
matrix = replace_once(matrix, '  navigation: NON_L1_CURRENT_ADMIN_PAGE\n', '', matrix_path)
write(matrix_path, matrix)

# Keep the newer header Surface Switch acceptance, but restore 9+9 navigation expectations.
browser_path = 'scripts/post-deploy-auth-browser-e2e.mjs'
browser = read(browser_path)
browser = replace_once(browser,
    'const frontNavIds = ["NAV-01","NAV-02","NAV-03","NAV-04","NAV-05","NAV-06","NAV-07","NAV-08"];',
    'const frontNavIds = ["NAV-01","NAV-02","NAV-03","NAV-04","NAV-05","NAV-06","NAV-07","NAV-08","NAV-09"];', browser_path)
browser = replace_once(browser,
    'const adminNavIds = ["ADMIN-NAV-01","ADMIN-NAV-02","ADMIN-NAV-03","ADMIN-NAV-04","ADMIN-NAV-05","ADMIN-NAV-06","ADMIN-NAV-07","ADMIN-NAV-08"];',
    'const adminNavIds = ["ADMIN-NAV-01","ADMIN-NAV-02","ADMIN-NAV-03","ADMIN-NAV-04","ADMIN-NAV-05","ADMIN-NAV-06","ADMIN-NAV-07","ADMIN-NAV-08","ADMIN-NAV-09"];', browser_path)
browser = replace_once(browser, 'assert(frontTargets.length === 8,', 'assert(frontTargets.length === 9,', browser_path)
browser = replace_once(browser, 'assert(adminTargets.length === 8,', 'assert(adminTargets.length === 9,', browser_path)
browser = replace_once(browser,
    'POST_DEPLOY_AUTH_BROWSER_E2E_PASS login_visual=ACPOS_LOGIN_CURRENT_V2 login_locales=3 front_nav=8 admin_nav=8 visible_pages=18',
    'POST_DEPLOY_AUTH_BROWSER_E2E_PASS login_visual=ACPOS_LOGIN_CURRENT_V2 login_locales=3 front_nav=9 admin_nav=9 visible_pages=18', browser_path)
write(browser_path, browser)

# Keep permission-derived visibility and newer Surface Switch checks; remove only stale 8x8 assertions.
test_path = 'tests/release/navigation-visibility.test.mjs'
test = read(test_path)
test = replace_once(test,
    '  assert.doesNotMatch(shell, /id: "NAV-09"/);\n  assert.doesNotMatch(shell, /id: "ADMIN-NAV-09"/);\n',
    '  assert.match(shell, /id: "NAV-09"[\\s\\S]*?pageUid: "workspace:INFO-01"/);\n  assert.match(shell, /id: "ADMIN-NAV-09"[\\s\\S]*?pageUid: "admin:KB-01"/);\n', test_path)
test = replace_once(test,
    'POST_DEPLOY_AUTH_BROWSER_E2E_PASS login_visual=ACPOS_LOGIN_CURRENT_V2 login_locales=3 front_nav=8 admin_nav=8 visible_pages=18',
    'POST_DEPLOY_AUTH_BROWSER_E2E_PASS login_visual=ACPOS_LOGIN_CURRENT_V2 login_locales=3 front_nav=9 admin_nav=9 visible_pages=18', test_path)
marker = 'test("Current Global L1 authority is user-confirmed 8 frontend + 8 admin while INFO/KB remain non-L1 current pages", async () => {'
start = test.find(marker)
if start < 0:
    raise SystemExit(f'{test_path}: stale 8x8 topology test block not found')
replacement = '''test("Current Global L1 authority is 9 frontend + 9 admin with INFO/KB as ninth L1", async () => {\n  const manifest = await read("authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml");\n  const nav = await read("authority/global/ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY_FINAL_LOCKED.yaml");\n  const shellAuthority = await read("authority/global/GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY_FINAL_LOCKED_V1.9.yaml");\n  const system = await read("authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml");\n  const matrix = await read("authority/global/ACPOS_PAGE_INTEGRATION_MATRIX_FINAL_LOCKED_CURRENT.yaml");\n  const iam = await read("src/components/pages/IamVisual.tsx");\n  const iamCatalog = await read("src/i18n/iamCatalog.ts");\n\n  assert.match(manifest, /front_l1_count:\\s*9/);\n  assert.match(manifest, /admin_l1_count:\\s*9/);\n  assert.match(nav, /front_workspace_navigation:[\\s\\S]*?count: 9/);\n  assert.match(nav, /admin_navigation:[\\s\\S]*?count: 9/);\n  assert.match(nav, /nav_id: NAV-09[\\s\\S]*?page_uid: workspace:INFO-01/);\n  assert.match(nav, /nav_id: ADMIN-NAV-09[\\s\\S]*?page_uid: admin:KB-01/);\n  assert.match(shellAuthority, /navigation:[\\s\\S]*?count: 9/);\n  assert.match(shellAuthority, /nav_id: NAV-09/);\n  assert.match(system, /Front workspace navigation has exactly 9 L1 items/);\n  assert.match(system, /Admin navigation has exactly 9 L1 items/);\n  assert.match(matrix, /page_uid: workspace:INFO-01[\\s\\S]*?navigation: FRONT_L1_NAV-09/);\n  assert.match(matrix, /admin_l1_bundle_count: 9/);\n  assert.match(matrix, /knowledge_bundle: ADMIN-L1-KNOWLEDGE/);\n  assert.doesNotMatch(matrix, /NON_L1_CURRENT_PAGE|NON_L1_CURRENT_ADMIN_PAGE/);\n  assert.match(iam, /data-frontend-l1-count="9"/);\n  assert.match(iam, /data-backend-l1-count="9"/);\n  assert.match(iamCatalog, /前台 9 L1/);\n  assert.match(iamCatalog, /後台 9 L1/);\n});\n'''
test = test[:start] + replacement
write(test_path, test)

print('ACPOS_9X9_CURRENT_CONSUMERS_RESTORE_PASS')
