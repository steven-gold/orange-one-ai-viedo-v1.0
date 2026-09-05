import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("WB-01 production projection runtime names page-gate SQL and 14 section reads", async () => {
  const runtime = await read("src/server/dashboard/wb01ProjectionRuntime.ts");
  const instrumentation = await read("src/instrumentation.ts");
  const mapping = await read("authority/runtime/ACPOS_WB01_UI_PROJECTION_SQL_PERMISSION_MAPPING_FINAL_LOCKED_V1.0.yaml");

  assert.match(instrumentation, /bindWb01ProjectionRuntime/);
  assert.match(runtime, /configureDashboardRuntime/);
  assert.match(runtime, /configureUiProjectionRuntime/);
  assert.match(runtime, /page:workspace:WB-01/);
  assert.match(runtime, /IDENTITY_COOKIE_NAME/);
  assert.match(runtime, /a.status = 'APPROVED'/);
  assert.match(runtime, /FROM projects/);
  assert.match(runtime, /FROM topics/);
  assert.match(runtime, /FROM department_tasks/);
  assert.match(runtime, /FROM notifications/);
  assert.match(runtime, /FROM schema_migration_history/);
  assert.match(runtime, /JOIN child_locks/);
  assert.match(runtime, /company_announcements: \{ items: \[\] \}/);
  assert.match(runtime, /industry_news: \{ items: \[\] \}/);
  assert.match(runtime, /payload_hash/);
  assert.match(mapping, /section_sql_mapping: NAMED/);
  assert.match(mapping, /adapter_bind_allowed: true/);
  assert.doesNotMatch(mapping, /WB01_SECTION_READ_SQL_NOT_DEFINED/);
});
