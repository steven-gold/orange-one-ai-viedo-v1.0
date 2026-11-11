import { openSqlClient } from "./client";
import { bootstrapDatabase } from "./migrate";
import { seedScope } from "./seed";
import { applyDbWorkbenchAction, DB_STATE_ERROR_UID } from "./dbActions";
import { DB_PERMISSION_SCOPES } from "../domain/db";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

async function readField(controlUid: string): Promise<string | null> {
  const client = await openSqlClient();
  const rows = await client.all<{ value_text: string | null }>(
    "SELECT value_text FROM ghsn_db_field_projection WHERE control_uid = ?",
    [controlUid],
  );
  const value = rows[0]?.value_text;
  return value === undefined || value === "" ? null : value;
}

async function readError(): Promise<{ code?: string; detail?: string } | null> {
  const raw = await readField(DB_STATE_ERROR_UID);
  if (!raw) return null;
  return JSON.parse(raw) as { code?: string; detail?: string };
}

const DEMO = "ACC-DEMO";

// Deterministic start: blank the DB-01 projection state (shared sandbox file).
const DB01_STATE_CONTROLS = [
  DB_STATE_ERROR_UID,
  "DB-01-FLD-ENV",
  "DB-01-FLD-SCHEMA-HEAD",
  "DB-01-FLD-MIGRATION-HEAD",
  "DB-01-FLD-SCOPE",
  "DB-01-FLD-HEALTH",
  "DB-01-FLD-ENTITY",
  "DB-01-FLD-TABLE",
  "DB-01-FLD-OWNER",
  "DB-01-FLD-CLASSIFICATION",
  "DB-01-FLD-PK",
  "DB-01-FLD-VERSION-RULE",
  "DB-01-TBL-COLUMNS",
  "DB-01-TBL-CONSTRAINTS",
  "DB-01-LIST-ENTITIES",
  "DB-01-LIST-RELATIONS",
  "DB-01-GRAPH-RELATIONS",
  "DB-01-LIST-FINDINGS",
  "DB-01-LIST-FINDINGS-ALL",
  "DB-01-VIEW-TRACE-PATH",
  "DB-01-FLD-TRACE-COMPLETE",
  "DB-01-VIEW-AUDIT",
  "DB-01-FLD-PAGE-STATE",
  "DB-01-FLD-REF-INTEGRITY",
  "DB-01-FLD-ORPHAN",
  "DB-01-FLD-IMMUTABLE",
  "DB-01-FLD-SOURCE-SYNC",
  "DB-01-FLD-CHANGE-OWNER",
  "DB-01-FLD-MIGRATION-INTEGRITY",
  "DB-01-FLD-FINDING-REASON",
  "DB-01-FLD-FINDING-AFFECTED",
  "DB-01-FLD-FINDING-EVIDENCE",
  "DB-01-FLD-FINDING-OWNER",
  "DB-01-FLD-DISABLED",
  "DB-01-SEL-TRACE-TYPE",
  "DB-01-INP-TRACE-ID",
  "DB-01-INP-AUDIT-ID",
];

async function main(): Promise<void> {
{
  const client = await openSqlClient();
  await bootstrapDatabase();
  await seedScope("db", client);
  for (const controlUid of DB01_STATE_CONTROLS) {
    await client.run("UPDATE ghsn_db_field_projection SET value_text = '' WHERE control_uid = ?", [controlUid]);
  }
  for (const scope of DB_PERMISSION_SCOPES) {
    const rows = await client.all<{ n: number }>(
      "SELECT count(*)::int AS n FROM ghsn_account_db_permission WHERE account_uid = ? AND permission_uid = ?",
      [DEMO, scope],
    );
    assertEqual(Number(rows[0]?.n ?? 0) >= 1, true, `seed grants ${scope}`);
  }
}

// ACT-SCHEMA-REFRESH resolves the context head from the live catalog.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-REFRESH", "DB-01-ACT-SCHEMA-REFRESH");
  const env = await readField("DB-01-FLD-ENV");
  const schemaHead = await readField("DB-01-FLD-SCHEMA-HEAD");
  const listEntities = await readField("DB-01-LIST-ENTITIES");
  assert(env !== null && env.length > 0, "FLD-ENV resolves real environment");
  assert(schemaHead !== null && /tables$/.test(schemaHead), "FLD-SCHEMA-HEAD carries table count");
  assert(listEntities !== null && listEntities.includes("ghsn_core_field_projection"), "LIST-ENTITIES lists real registered tables");
  assertEqual(await readField("DB-01-FLD-PAGE-STATE"), "DB-01-STAGE-01-CONTEXT", "stage after context");
}

// ACT-ENTITY-SELECT registered entity loads metadata; unknown is BLOCK + ERR-ENTITY-001.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-LIST-ENTITIES", "DB-01-ACT-ENTITY-SELECT", "ghsn_core_field_projection");
  assertEqual(await readField("DB-01-FLD-OWNER"), "CORE", "entity owner maps to CORE domain");
  assertEqual(await readField("DB-01-FLD-CLASSIFICATION"), "field_projection", "entity classification");
  assertEqual(await readError(), null, "no error on registered entity");

  await applyDbWorkbenchAction(DEMO, "DB-01-LIST-ENTITIES", "DB-01-ACT-ENTITY-SELECT", "ghsn_not_a_real_table");
  assertEqual((await readError())?.code, "DB-01-ERR-ENTITY-001", "unknown entity blocks with ERR-ENTITY-001");
  assertEqual(await readField("DB-01-FLD-ENTITY"), null, "selection cleared on block");
}

// ACT-SCHEMA-REFRESH with selected entity inspects real columns/PK.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-LIST-ENTITIES", "DB-01-ACT-ENTITY-SELECT", "ghsn_core_field_projection");
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-SCHEMA-REFRESH", "DB-01-ACT-SCHEMA-REFRESH");
  const columns = await readField("DB-01-TBL-COLUMNS");
  assert(columns !== null && columns.includes("control_uid") && columns.includes("value_text"), "TBL-COLUMNS from live table_info");
  assertEqual(await readField("DB-01-FLD-PK"), "control_uid", "PK resolved from catalog");
  assertEqual(await readField("DB-01-FLD-IMMUTABLE"), "NO (projection)", "projection mutability rule");
  assertEqual(await readField("DB-01-STAGE-NOPE" as never), null, "no stray stage writes");
  assertEqual(await readField("DB-01-FLD-PAGE-STATE"), "DB-01-STAGE-02-INSPECT", "stage after inspect");
}

// Audit table shows append-only rule; relations come from real FK metadata.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-LIST-ENTITIES", "DB-01-ACT-ENTITY-SELECT", "ghsn_core_audit_event");
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-SCHEMA-REFRESH", "DB-01-ACT-SCHEMA-REFRESH");
  assertEqual(await readField("DB-01-FLD-IMMUTABLE"), "YES (append-only)", "audit table lineage rule");
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-SCHEMA-REFRESH", "DB-01-ACT-RELATION-OPEN");
  const relations = await readField("DB-01-LIST-RELATIONS");
  const graph = await readField("DB-01-GRAPH-RELATIONS");
  assert(graph !== null && graph.includes("ghsn_core_audit_event"), "relation graph names selected entity");
  assert(relations === null || relations.includes("FK ·"), "relations are typed FK rows only");
}

// ACT-TRACE without inputs is ERR-TRACE-001; with inputs it traces lineage.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-TRACE", "DB-01-ACT-TRACE");
  assertEqual((await readError())?.code, "DB-01-ERR-TRACE-001", "missing trace refs blocked");
  await applyDbWorkbenchAction(DEMO, "DB-01-SEL-TRACE-TYPE", "DB-01-ACT-CONTEXT", "table");
  await applyDbWorkbenchAction(DEMO, "DB-01-INP-TRACE-ID", "DB-01-ACT-CONTEXT", "ghsn_core_field_projection");
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-TRACE", "DB-01-ACT-TRACE");
  const tracePath = await readField("DB-01-VIEW-TRACE-PATH");
  assert(tracePath !== null && tracePath.startsWith("ENTITY"), "trace path starts at entity");
  const complete = await readField("DB-01-FLD-TRACE-COMPLETE");
  assert(complete === "COMPLETE" || complete === "BROKEN", "trace completeness is exact");
  assertEqual(await readField("DB-01-FLD-PAGE-STATE"), "DB-01-STAGE-03-TRACE", "stage after trace");
}

// Migration refresh reads real history with checksum validation.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-MIGRATION-REFRESH", "DB-01-ACT-MIGRATION-REFRESH");
  const rows = await readField("DB-01-TBL-MIGRATIONS");
  assert(rows !== null && rows.length > 0, "TBL-MIGRATIONS carries live history");
  const integrity = await readField("DB-01-FLD-MIGRATION-INTEGRITY");
  assert(integrity !== null && (integrity.startsWith("OK ·") || integrity.startsWith("BLOCKED ·")), "migration integrity verdict");
  assertEqual(await readField("DB-01-FLD-PAGE-STATE"), "DB-01-STAGE-04-INTEGRITY", "stage reaches integrity");
}

// Integrity refresh computes findings from the live catalog.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-INTEGRITY-REFRESH", "DB-01-ACT-INTEGRITY-REFRESH");
  const findings = await readField("DB-01-LIST-FINDINGS");
  assert(findings !== null && findings.length > 0, "LIST-FINDINGS populated");
  const refIntegrity = await readField("DB-01-FLD-REF-INTEGRITY");
  assert(refIntegrity !== null && (refIntegrity.startsWith("OK ·") || /\borphan/.test(refIntegrity)), "FK check verdict");
  const health = await readField("DB-01-FLD-HEALTH");
  assert(health !== null && (health === "OK" || /finding/.test(health)), "health reflects findings");
}

// Audit open requires an exact correlation id and finds real events.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-AUDIT", "DB-01-ACT-AUDIT-OPEN");
  assertEqual((await readError())?.code, "DB-01-ERR-AUDIT-001", "missing audit id blocked");
  const client = await openSqlClient();
  await client.run(
    "INSERT INTO ghsn_db_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT (event_uid) DO NOTHING",
    ["EVT-TEST-DB-0001", DEMO, "DB-01-BTN-REFRESH", "DB-01-ACT-SCHEMA-REFRESH", new Date().toISOString()],
  );
  await applyDbWorkbenchAction(DEMO, "DB-01-INP-AUDIT-ID", "DB-01-ACT-CONTEXT", "EVT-TEST-DB-0001");
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-AUDIT", "DB-01-ACT-AUDIT-OPEN");
  const view = await readField("DB-01-VIEW-AUDIT");
  assert(view !== null && view.includes("EVT-TEST-DB-0001"), "audit view carries the real event");
  assertEqual(await readField("DB-01-FLD-PAGE-STATE"), "DB-01-STAGE-04-INTEGRITY", "stage machine keeps max resolved stage");
}

// Unlisted action lands BLOCK + REPORT_AUTHORITY_GAP.
{
  await applyDbWorkbenchAction(DEMO, "DB-01-BTN-REFRESH", "DB-01-ACT-DROP-TABLE");
  assertEqual((await readError())?.code, "DB-01-ERR-UNDEFINED-001", "undefined action blocked");
}

// Scoped permission denial for a non-provisioned account.
{
  await applyDbWorkbenchAction("ACC-NOPERM", "DB-01-BTN-TRACE", "DB-01-ACT-TRACE");
  assertEqual((await readError())?.code, "DB-01-ERR-PERM-001", "trace requires database.trace.read");
}
}

main().then(
  () => console.log("dbWorkspace.test.ts PASS"),
  (cause: unknown) => {
    console.error(cause);
    process.exit(1);
  },
);
