import { bootstrapDatabase, readyCheck } from './bootstrap';
import { closeSqlClient, getSqlClient } from './client';

async function main(): Promise<void> {
  await bootstrapDatabase(process.env.ACPOS_DATABASE_PATH || ':memory:');
  const client = getSqlClient();
  const tables = ['navigation_authority', 'account_permission_assignment', 'navigation_audit_event', 'account_session', 'schema_migration_history'];
  const counts: Record<string, number> = {};
  for (const table of tables) {
    const rows = await client.all<{ n: number }>(`SELECT count(*) AS n FROM ${table}`);
    counts[table] = Number(rows[0]?.n ?? 0);
  }
  const ready = await readyCheck();
  process.stdout.write(JSON.stringify({ ok: ready.ready, dialect: client.dialect, counts, ready }) + '\n');
  await closeSqlClient();
}

main().catch(async (error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  await closeSqlClient();
  process.exit(1);
});
