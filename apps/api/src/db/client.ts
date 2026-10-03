import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { assertNeonIdentity, databaseUrl, isNeonConfigured, sqlitePath } from '../config/env';

export type SqlDialect = 'sqlite' | 'neon';

export interface SqlClient {
  dialect: SqlDialect;
  all<T = Record<string, unknown>>(sql: string, params?: unknown[]): Promise<T[]>;
  run(sql: string, params?: unknown[]): Promise<{ changes: number }>;
  exec(sql: string): Promise<void>;
  close(): Promise<void>;
}

class SqliteClient implements SqlClient {
  readonly dialect: SqlDialect = 'sqlite';
  private readonly db: DatabaseSync;

  constructor(path: string) {
    if (path !== ':memory:') {
      mkdirSync(dirname(resolve(path)), { recursive: true });
    }
    this.db = new DatabaseSync(path);
  }

  async all<T = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<T[]> {
    const stmt = this.db.prepare(sql);
    return stmt.all(...params) as T[];
  }

  async run(sql: string, params: unknown[] = []): Promise<{ changes: number }> {
    const stmt = this.db.prepare(sql);
    const result = stmt.run(...params) as { changes?: number };
    return { changes: Number(result.changes ?? 0) };
  }

  async exec(sql: string): Promise<void> {
    this.db.exec(sql);
  }

  async close(): Promise<void> {
    this.db.close();
  }
}

function toPostgres(sql: string): string {
  let index = 0;
  return sql.replace(/\?/g, () => {
    index += 1;
    return `$${index}`;
  });
}

class NeonClient implements SqlClient {
  readonly dialect: SqlDialect = 'neon';
  private readonly query: (sql: string, params?: unknown[]) => Promise<unknown>;

  constructor(url: string) {
    assertNeonIdentity();
    this.query = this.bindNeon(url);
  }

  private bindNeon(url: string): (sql: string, params?: unknown[]) => Promise<unknown> {
    const load = (): Promise<(sql: string, params?: unknown[]) => Promise<unknown>> => {
      const specifier = '@neondatabase/' + 'serverless';
      return import(specifier).then((mod: { neon: (connection: string) => { query: (text: string, params?: unknown[]) => Promise<unknown> } }) => {
        const sql = mod.neon(url);
        return (text: string, params: unknown[] = []) => sql.query(text, params);
      });
    };
    let bound: ((sql: string, params?: unknown[]) => Promise<unknown>) | null = null;
    return async (sql: string, params: unknown[] = []) => {
      if (!bound) bound = await load();
      return bound(sql, params);
    };
  }

  async all<T = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<T[]> {
    const rows = await this.query(toPostgres(sql), params);
    return (Array.isArray(rows) ? rows : []) as T[];
  }

  async run(sql: string, params: unknown[] = []): Promise<{ changes: number }> {
    const rows = await this.query(toPostgres(sql), params);
    const count = Array.isArray(rows) ? rows.length : 0;
    return { changes: count };
  }

  async exec(sql: string): Promise<void> {
    await this.query(toPostgres(sql), []);
  }

  async close(): Promise<void> {
    return;
  }
}

let active: SqlClient | null = null;

export async function openSqlClient(pathOverride?: string): Promise<SqlClient> {
  if (isNeonConfigured() && !pathOverride) {
    active = new NeonClient(databaseUrl());
    return active;
  }
  active = new SqliteClient(pathOverride ?? sqlitePath());
  return active;
}

export function getSqlClient(): SqlClient {
  if (!active) {
    throw new Error('DATABASE_RUNTIME_NOT_BOUND');
  }
  return active;
}

export async function closeSqlClient(): Promise<void> {
  if (active) {
    await active.close();
    active = null;
  }
}
