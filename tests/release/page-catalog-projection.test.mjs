import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("catalog PAGE VIEW covers the 17 non-WB-01 current pages", async () => {
  const catalog = await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const ui = await read("src/server/shared/uiProjectionRuntime.ts");
  const adapters = await read("src/domain/catalog/identityClientProjectionAdapters.ts");
  const shell = await read("src/components/shell/AppShell.tsx");

  const keys = [
    "CORE-01",
    "ASSET-01",
    "VIDEO-01",
    "EDIT-01",
    "QA-01",
    "admin:DB-01",
    "workspace:STR-01",
    "workspace:INFO-01",
    "admin:SYS-01",
    "admin:IAM-01",
    "admin:DEV-01",
    "admin:SOC-01",
    "admin:ERP-01",
    "admin:AIAPI-01",
    "admin:SG-02",
    "admin:STR-01",
    "admin:KB-01",
  ];
  for (const pageUid of keys) {
    assert.match(catalog, new RegExp(`"${pageUid.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"`));
  }
  assert.match(catalog, /resource_type = 'PAGE'/);
  assert.match(catalog, /a.action = 'VIEW'/);
  assert.match(catalog, /a.status = 'APPROVED'/);
  assert.match(catalog, /department_tasks/);
  assert.match(catalog, /t\.department::text = \$\{department\}/);
  assert.match(catalog, /FROM conversations c/);
  assert.match(catalog, /FROM information_schema\.tables/);
  assert.match(catalog, /FROM schema_migration_history/);
  assert.match(ui, /readCatalogPageProjection/);
  assert.match(ui, /if\s*\(!runtime\)/);
  assert.match(ui, /UI_PROJECTION_RUNTIME_NOT_BOUND/);
  assert.match(adapters, /bindIdentityClientProjectionAdapters/);
  assert.match(adapters, /isControlledTestMode/);
  assert.match(shell, /bindIdentityClientProjectionAdapters/);
});
