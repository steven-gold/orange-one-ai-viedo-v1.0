import { DatabaseSync } from "node:sqlite";
import type { SqlClient } from "./client";

/**
 * In-memory SQL client for environments without a provisioned database.
 *
 * It backs the exact SQL subset the runtime issues (CREATE TABLE, INSERT with
 * ON CONFLICT upsert, SELECT, UPDATE, DELETE) with a bundled SQLite engine, so
 * the workbench pages are fully exercisable in a local sandbox. It is never
 * selected when a real database is configured.
 */
function toSqlite(sql: string): string {
  return sql.replace(/::int/gi, "");
}

function asParams(params: unknown[]): unknown[] {
  return params.map((value) => (value === undefined ? null : value));
}

export class MemoryClient implements SqlClient {
  readonly dialect = "memory" as const;
  private readonly db: DatabaseSync;

  constructor() {
    this.db = new DatabaseSync(":memory:");
  }

  async all<T = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<T[]> {
    const statement = this.db.prepare(toSqlite(sql));
    const rows = statement.all(...(asParams(params) as never[])) as Record<string, unknown>[];
    return rows.map((row) => ({ ...row })) as T[];
  }

  async run(sql: string, params: unknown[] = []): Promise<{ changes: number }> {
    const statement = this.db.prepare(toSqlite(sql));
    const info = statement.run(...(asParams(params) as never[]));
    return { changes: Number(info.changes ?? 0) };
  }

  async exec(sql: string): Promise<void> {
    for (const statement of sql.split(";").map((part) => part.trim()).filter(Boolean)) {
      this.db.exec(toSqlite(statement));
    }
  }
}
