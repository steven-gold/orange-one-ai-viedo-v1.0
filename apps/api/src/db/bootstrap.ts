import { closeSqlClient, getSqlClient, openSqlClient } from './client';
import { runMigrations, type MigrationResult } from './migrate';

export async function bootstrapDatabase(pathOverride?: string): Promise<MigrationResult> {
  await closeSqlClient();
  const client = await openSqlClient(pathOverride);
  return runMigrations(client);
}

export async function readyCheck(): Promise<{
  ready: boolean;
  dialect: string;
  migrationCount: number;
  reason: string;
}> {
  try {
    const client = getSqlClient();
    const rows = await client.all<{ n: number }>('SELECT count(*) AS n FROM schema_migration_history');
    const migrationCount = Number(rows[0]?.n ?? 0);
    const ready = migrationCount >= 1;
    return {
      ready,
      dialect: client.dialect,
      migrationCount,
      reason: ready ? 'BOUND' : 'SCHEMA_MIGRATION_HISTORY_UNAVAILABLE',
    };
  } catch (error) {
    return {
      ready: false,
      dialect: 'unbound',
      migrationCount: 0,
      reason: error instanceof Error ? error.message : 'DATABASE_RUNTIME_NOT_BOUND',
    };
  }
}
