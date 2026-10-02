import { CANONICAL_NAVIGATION_AUTHORITY } from "../domain/schema";
import { openSqlClient, type SqlClient } from "./client";

const DDL = [
  `CREATE TABLE IF NOT EXISTS schema_migration_history (
    filename TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    checksum TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS navigation_authority (
    navigation_uid TEXT PRIMARY KEY,
    area TEXT NOT NULL CHECK (area IN ('FRONT', 'ADMIN')),
    label_key TEXT NOT NULL,
    route TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    icon TEXT NOT NULL,
    aria_label_key TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS account_permission_assignment (
    account_uid TEXT NOT NULL,
    navigation_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, navigation_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS navigation_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    area TEXT NOT NULL,
    navigation_uid TEXT NOT NULL,
    route TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS account_session (
    session_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    issued_at TEXT NOT NULL
  )`,
];

export interface MigrationResult {
  applied: string[];
  alreadyApplied: string[];
  dialect: SqlClient["dialect"];
  migrationCount: number;
}

async function seedCanonicalData(client: SqlClient): Promise<void> {
  for (const item of CANONICAL_NAVIGATION_AUTHORITY.items) {
    await client.run(
      `INSERT INTO navigation_authority (navigation_uid, area, label_key, route, display_order, icon, aria_label_key)
       VALUES (?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT (navigation_uid) DO UPDATE SET
         area = EXCLUDED.area,
         label_key = EXCLUDED.label_key,
         route = EXCLUDED.route,
         display_order = EXCLUDED.display_order,
         icon = EXCLUDED.icon,
         aria_label_key = EXCLUDED.aria_label_key`,
      [item.uid, item.area, item.labelKey, item.route, item.order, item.icon, item.ariaLabelKey],
    );
  }

  const demoGrants = CANONICAL_NAVIGATION_AUTHORITY.items.map((item) => item.uid);
  const limitedGrants = ["FRONT-01", "FRONT-02"];
  for (const uid of demoGrants) {
    await client.run(
      `INSERT INTO account_permission_assignment (account_uid, navigation_uid)
       VALUES (?, ?)
       ON CONFLICT (account_uid, navigation_uid) DO NOTHING`,
      ["ACC-DEMO", uid],
    );
  }
  for (const uid of limitedGrants) {
    await client.run(
      `INSERT INTO account_permission_assignment (account_uid, navigation_uid)
       VALUES (?, ?)
       ON CONFLICT (account_uid, navigation_uid) DO NOTHING`,
      ["ACC-LIMITED", uid],
    );
  }

  const now = new Date().toISOString();
  await client.run(
    `INSERT INTO account_session (session_uid, account_uid, issued_at)
     VALUES (?, ?, ?)
     ON CONFLICT (session_uid) DO UPDATE SET account_uid = EXCLUDED.account_uid`,
    ["sess-demo-001", "ACC-DEMO", now],
  );
  await client.run(
    `INSERT INTO account_session (session_uid, account_uid, issued_at)
     VALUES (?, ?, ?)
     ON CONFLICT (session_uid) DO UPDATE SET account_uid = EXCLUDED.account_uid`,
    ["sess-limited-001", "ACC-LIMITED", now],
  );
}

export async function bootstrapDatabase(): Promise<MigrationResult> {
  const client = await openSqlClient();
  for (const statement of DDL) {
    await client.exec(statement);
  }
  const existing = await client.all<{ filename: string }>("SELECT filename FROM schema_migration_history");
  const applied = new Set(existing.map((row) => row.filename));
  const files = ["001_init.sql", "002_sessions_and_history.sql"];
  const newlyApplied: string[] = [];
  const alreadyApplied: string[] = [];
  for (const filename of files) {
    if (applied.has(filename)) {
      alreadyApplied.push(filename);
      continue;
    }
    await client.run(
      `INSERT INTO schema_migration_history (filename, applied_at, checksum)
       VALUES (?, ?, ?)
       ON CONFLICT (filename) DO NOTHING`,
      [filename, new Date().toISOString(), filename],
    );
    newlyApplied.push(filename);
  }
  await seedCanonicalData(client);
  const countRows = await client.all<{ n: number }>("SELECT count(*)::int AS n FROM schema_migration_history");
  return {
    applied: newlyApplied,
    alreadyApplied,
    dialect: client.dialect,
    migrationCount: Number(countRows[0]?.n ?? 0),
  };
}

export async function readyCheck(): Promise<{
  ready: boolean;
  dialect: string;
  migrationCount: number;
  reason: string;
}> {
  try {
    const result = await bootstrapDatabase();
    return {
      ready: result.migrationCount >= 1,
      dialect: result.dialect,
      migrationCount: result.migrationCount,
      reason: result.migrationCount >= 1 ? "BOUND" : "SCHEMA_MIGRATION_HISTORY_UNAVAILABLE",
    };
  } catch (error) {
    return {
      ready: false,
      dialect: "unbound",
      migrationCount: 0,
      reason: error instanceof Error ? error.message : "DATABASE_RUNTIME_NOT_BOUND",
    };
  }
}
