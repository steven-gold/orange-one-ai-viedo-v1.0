import type {
  NeonQueryFunction,
  NeonQueryPromise,
} from "@neondatabase/serverless";

export const RLS_RUNTIME_ROLE = "acpos_app_runtime";

type NeonSql = NeonQueryFunction<false, false>;
type NeonQuery = NeonQueryPromise<false, false>;
export type RlsRows = Record<string, unknown>[];


export async function runRlsActorTransaction(
  sql: NeonSql,
  sessionTokenHash: string,
  queries: readonly NeonQuery[],
): Promise<RlsRows[]> {
  const tokenHash = sessionTokenHash.trim();
  if (!tokenHash) {
    throw new Error("RLS_SESSION_CONTEXT_REQUIRED");
  }
  if (queries.length === 0) {
    return [];
  }

  const results = await sql.transaction([
    sql`SELECT set_config('acpos.session_token_hash', ${tokenHash}, true)`,
    sql`SET LOCAL ROLE acpos_app_runtime`,
    ...queries,
  ]);

  return results.slice(2) as RlsRows[];
}

export async function runRlsActorQuery(
  sql: NeonSql,
  sessionTokenHash: string,
  query: NeonQuery,
): Promise<RlsRows> {
  const tokenHash = sessionTokenHash.trim();
  if (!tokenHash) {
    throw new Error("RLS_SESSION_CONTEXT_REQUIRED");
  }

  const results = await sql.transaction([
    sql`SELECT set_config('acpos.session_token_hash', ${tokenHash}, true)`,
    sql`SET LOCAL ROLE acpos_app_runtime`,
    query,
  ]);

  return results[2] as RlsRows;
}

export async function runRlsServiceTransaction(
  sql: NeonSql,
  serviceIdentityKey: string,
  queries: readonly NeonQuery[],
): Promise<RlsRows[]> {
  const key = serviceIdentityKey.trim();
  if (!key) throw new Error("SERVICE_IDENTITY_CONTEXT_REQUIRED");
  if (queries.length === 0) return [];
  const results = await sql.transaction([
    sql`SELECT set_config('acpos.service_identity_key', ${key}, true)`,
    sql`SET LOCAL ROLE acpos_app_runtime`,
    ...queries,
  ]);
  return results.slice(2) as RlsRows[];
}

export async function runRlsServiceQuery(
  sql: NeonSql,
  serviceIdentityKey: string,
  query: NeonQuery,
): Promise<RlsRows> {
  const key = serviceIdentityKey.trim();
  if (!key) throw new Error("SERVICE_IDENTITY_CONTEXT_REQUIRED");
  const results = await sql.transaction([
    sql`SELECT set_config('acpos.service_identity_key', ${key}, true)`,
    sql`SET LOCAL ROLE acpos_app_runtime`,
    query,
  ]);
  return results[2] as RlsRows;
}
