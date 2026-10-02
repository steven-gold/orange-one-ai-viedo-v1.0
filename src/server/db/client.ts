import { neon } from "@neondatabase/serverless";
import { assertNeonIdentity, databaseUrl, isNeonConfigured } from "../config/env";

export type SqlDialect = "neon";

export interface SqlClient {
  dialect: SqlDialect;
  all<T = Record<string, unknown>>(sql: string, params?: unknown[]): Promise<T[]>;
  run(sql: string, params?: unknown[]): Promise<{ changes: number }>;
  exec(sql: string): Promise<void>;
}

function toPostgres(sql: string): string {
  let index = 0;
  return sql.replace(/\?/g, () => {
    index += 1;
    return `$${index}`;
  });
}

class NeonClient implements SqlClient {
  readonly dialect: SqlDialect = "neon";
  private readonly query: (text: string, params?: unknown[]) => Promise<unknown>;

  constructor(url: string) {
    assertNeonIdentity();
    const sql = neon(url, { fullResults: false });
    this.query = (text: string, params: unknown[] = []) => sql.query(text, params);
  }

  async all<T = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<T[]> {
    const rows = await this.query(toPostgres(sql), params);
    return (Array.isArray(rows) ? rows : []) as T[];
  }

  async run(sql: string, params: unknown[] = []): Promise<{ changes: number }> {
    const rows = await this.query(toPostgres(sql), params);
    return { changes: Array.isArray(rows) ? rows.length : 0 };
  }

  async exec(sql: string): Promise<void> {
    const statements = sql
      .split(";")
      .map((part) => part.trim())
      .filter(Boolean);
    for (const statement of statements) {
      await this.query(statement);
    }
  }
}

let active: SqlClient | null = null;
let bindReason = "DATABASE_RUNTIME_NOT_BOUND";

export function getProductionNeonBindReason(): string {
  return bindReason;
}

export async function openSqlClient(): Promise<SqlClient> {
  if (active) return active;
  if (!isNeonConfigured()) {
    bindReason = "DATABASE_RUNTIME_ENV_INCOMPLETE";
    throw new Error(bindReason);
  }
  active = new NeonClient(databaseUrl());
  bindReason = "BOUND";
  return active;
}

export function getSqlClient(): SqlClient {
  if (!active) {
    throw new Error("DATABASE_RUNTIME_NOT_BOUND");
  }
  return active;
}
