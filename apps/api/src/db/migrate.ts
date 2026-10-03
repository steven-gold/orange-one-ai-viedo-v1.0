import { createHash } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { CANONICAL_NAVIGATION_AUTHORITY } from './schema';
import type { SqlClient } from './client';

const MIGRATIONS_DIR = dirname(fileURLToPath(import.meta.url)) + '/migrations';

export interface MigrationResult {
  applied: string[];
  alreadyApplied: string[];
  dialect: SqlClient['dialect'];
}

function checksum(sql: string): string {
  return createHash('sha256').update(sql).digest('hex');
}

function listMigrationFiles(): string[] {
  return readdirSync(MIGRATIONS_DIR)
    .filter((name) => name.endsWith('.sql'))
    .sort();
}

async function ensureHistoryTable(client: SqlClient): Promise<void> {
  await client.exec(`
    CREATE TABLE IF NOT EXISTS schema_migration_history (
      filename TEXT PRIMARY KEY,
      applied_at TEXT NOT NULL,
      checksum TEXT NOT NULL
    )
  `);
}

async function appliedFilenames(client: SqlClient): Promise<Set<string>> {
  const rows = await client.all<{ filename: string }>('SELECT filename FROM schema_migration_history');
  return new Set(rows.map((row) => row.filename));
}

async function seedCanonicalData(client: SqlClient): Promise<void> {
  for (const item of CANONICAL_NAVIGATION_AUTHORITY.items) {
    await client.run(
      `INSERT INTO navigation_authority (navigation_uid, area, label_key, route, display_order, icon, aria_label_key)
       VALUES (?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(navigation_uid) DO UPDATE SET
         area = excluded.area,
         label_key = excluded.label_key,
         route = excluded.route,
         display_order = excluded.display_order,
         icon = excluded.icon,
         aria_label_key = excluded.aria_label_key`,
      [item.uid, item.area, item.labelKey, item.route, item.order, item.icon, item.ariaLabelKey],
    );
  }

  const demoGrants = CANONICAL_NAVIGATION_AUTHORITY.items.map((item) => item.uid);
  const limitedGrants = ['FRONT-01', 'FRONT-02'];
  for (const uid of demoGrants) {
    await client.run(
      `INSERT INTO account_permission_assignment (account_uid, navigation_uid)
       VALUES (?, ?)
       ON CONFLICT(account_uid, navigation_uid) DO NOTHING`,
      ['ACC-DEMO', uid],
    );
  }
  for (const uid of limitedGrants) {
    await client.run(
      `INSERT INTO account_permission_assignment (account_uid, navigation_uid)
       VALUES (?, ?)
       ON CONFLICT(account_uid, navigation_uid) DO NOTHING`,
      ['ACC-LIMITED', uid],
    );
  }

  const now = new Date().toISOString();
  await client.run(
    `INSERT INTO account_session (session_uid, account_uid, issued_at)
     VALUES (?, ?, ?)
     ON CONFLICT(session_uid) DO UPDATE SET account_uid = excluded.account_uid`,
    ['sess-demo-001', 'ACC-DEMO', now],
  );
  await client.run(
    `INSERT INTO account_session (session_uid, account_uid, issued_at)
     VALUES (?, ?, ?)
     ON CONFLICT(session_uid) DO UPDATE SET account_uid = excluded.account_uid`,
    ['sess-limited-001', 'ACC-LIMITED', now],
  );
}

export async function runMigrations(client: SqlClient): Promise<MigrationResult> {
  await ensureHistoryTable(client);
  const applied = await appliedFilenames(client);
  const files = listMigrationFiles();
  const newlyApplied: string[] = [];
  const alreadyApplied: string[] = [];

  for (const filename of files) {
    const sql = readFileSync(join(MIGRATIONS_DIR, filename), 'utf8');
    if (applied.has(filename)) {
      alreadyApplied.push(filename);
      continue;
    }
    await client.exec(sql);
    await client.run(
      `INSERT INTO schema_migration_history (filename, applied_at, checksum) VALUES (?, ?, ?)`,
      [filename, new Date().toISOString(), checksum(sql)],
    );
    newlyApplied.push(filename);
  }

  await seedCanonicalData(client);
  return { applied: newlyApplied, alreadyApplied, dialect: client.dialect };
}
