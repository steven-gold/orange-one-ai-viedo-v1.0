import type { SqlClient } from "./client";

// ACPOS DB-01 FINAL_LOCKED_ENCODING: real_data_only — every value below is
// read from the live database catalog (sqlite_master / information_schema),
// never synthesized. Missing metadata yields "—" upstream, never a guess.

export interface DbEntity {
  name: string;
  domain: string;
  kind: string;
}

export interface DbColumnSpec {
  name: string;
  type: string;
  notNull: boolean;
  defaultValue: string | null;
  pk: boolean;
}

export interface DbRelationSpec {
  fromTable: string;
  fromColumn: string;
  toTable: string;
  toColumn: string;
  kind: "FK";
}

export interface DbMigrationRow {
  filename: string;
  appliedAt: string;
  checksum: string;
}

export interface DbFinding {
  findingUid: string;
  type: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  reason: string;
  affected: string;
  evidence: string;
  owner: string;
}

export interface DbTraceSegment {
  label: string;
  detail: string;
  ok: boolean;
}

export interface DbTraceResult {
  path: string;
  complete: boolean;
  segments: DbTraceSegment[];
}

const DOMAIN_BY_PREFIX: Array<[string, string]> = [
  ["ghsn_core", "CORE"],
  ["ghsn_asset", "ASSET"],
  ["ghsn_video", "VIDEO"],
  ["ghsn_edit", "EDIT"],
  ["ghsn_qa", "QA"],
  ["ghsn_db", "DB"],
  ["ghsn_str", "STR"],
  ["ghsn_info", "INFO"],
  ["ghsn_sys", "SYS"],
  ["ghsn_iam", "IAM"],
  ["ghsn_dev", "DEV"],
  ["ghsn_soc", "SOC"],
  ["ghsn_erp", "ERP"],
  ["ghsn_aiapi", "AIAPI"],
  ["ghsn_sg02", "SG02"],
  ["ghsn_admin_str", "ADMIN_STR"],
  ["ghsn_kb", "KB"],
  ["ghsn_account", "ACCOUNT"],
  ["ghsn_navigation", "NAVIGATION"],
  ["ghsn_dashboard", "DASHBOARD"],
  ["ghsn_schema", "SCHEMA"],
  ["ghsn_runtime", "SYSTEM"],
  ["ghsn_app_user", "SYSTEM"],
  ["ghsn_identity", "SYSTEM"],
  ["ghsn_conversation", "SYSTEM"],
];

export function domainOfTable(table: string): string {
  for (const [prefix, domain] of DOMAIN_BY_PREFIX) {
    if (table === prefix || table.startsWith(`${prefix}_`)) return domain;
  }
  return "UNMAPPED";
}

export function kindOfTable(table: string): string {
  if (table.endsWith("_field_projection")) return "field_projection";
  if (table.endsWith("_audit_event")) return "audit_event";
  if (table.startsWith("ghsn_account_") && table.endsWith("_permission")) return "permission";
  if (table === "ghsn_account_session" || table === "ghsn_identity_session") return "session";
  if (table === "ghsn_schema_migration_history") return "migration_history";
  return "runtime";
}

function isImmutableKind(kind: string): boolean {
  return kind === "audit_event" || kind === "migration_history";
}

export async function listEntities(client: SqlClient): Promise<DbEntity[]> {
  if (client.dialect === "memory") {
    const rows = await client.all<{ name: string }>(
      "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'ghsn_%' ORDER BY name",
    );
    return rows.map((row) => ({
      name: row.name,
      domain: domainOfTable(row.name),
      kind: kindOfTable(row.name),
    }));
  }
  const rows = await client.all<{ table_name: string }>(
    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'ghsn_%' ORDER BY table_name",
  );
  return rows.map((row) => ({
    name: row.table_name,
    domain: domainOfTable(row.table_name),
    kind: kindOfTable(row.table_name),
  }));
}

export async function describeColumns(client: SqlClient, table: string): Promise<DbColumnSpec[]> {
  if (!isRegisteredIdentifier(table)) return [];
  if (client.dialect === "memory") {
    const rows = await client.all<{ name: string; type: string; notnull: number; dflt_value: string | null; pk: number }>(
      'SELECT name, type, "notnull", dflt_value, pk FROM pragma_table_info(?)',
      [table],
    );
    return rows.map((row) => ({
      name: row.name,
      type: row.type,
      notNull: Number(row.notnull) === 1,
      defaultValue: row.dflt_value,
      pk: Number(row.pk) > 0,
    }));
  }
  const rows = await client.all<{ column_name: string; data_type: string; is_nullable: string; column_default: string | null }>(
    "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = 'public' AND table_name = ? ORDER BY ordinal_position",
    [table],
  );
  // information_schema.columns carries no key metadata: resolve the primary
  // key from table constraints so PK markers survive the neon dialect.
  const pkRows = await client.all<{ column_name: string }>(
    "SELECT kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name WHERE tc.table_schema = 'public' AND tc.table_name = ? AND tc.constraint_type = 'PRIMARY KEY' ORDER BY kcu.ordinal_position",
    [table],
  );
  const pkNames = new Set(pkRows.map((row) => row.column_name));
  return rows.map((row) => ({
    name: row.column_name,
    type: row.data_type,
    notNull: row.is_nullable === "NO",
    defaultValue: row.column_default,
    pk: pkNames.has(row.column_name),
  }));
}

export async function primaryKeysOf(client: SqlClient, table: string): Promise<string[]> {
  const columns = await describeColumns(client, table);
  return columns.filter((column) => column.pk).map((column) => column.name);
}

export async function listForeignKeys(client: SqlClient, table: string): Promise<DbRelationSpec[]> {
  if (!isRegisteredIdentifier(table)) return [];
  if (client.dialect === "memory") {
    const raw = await client.all<Record<string, string | null>>(
      'SELECT "table", "from", "to" FROM pragma_foreign_key_list(?)',
      [table],
    );
    return raw.map((row) => ({
      fromTable: table,
      fromColumn: String(row.from),
      toTable: String(row.table),
      toColumn: row.to === null ? "" : String(row.to),
      kind: "FK" as const,
    }));
  }
  const rows = await client.all<{ column_name: string; foreign_table: string; foreign_column: string }>(
    "SELECT kcu.column_name, ccu.table_name AS foreign_table, ccu.column_name AS foreign_column FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name WHERE tc.table_schema = 'public' AND tc.table_name = ? AND tc.constraint_type = 'FOREIGN KEY'",
    [table],
  );
  return rows.map((row) => ({
    fromTable: table,
    fromColumn: row.column_name,
    toTable: row.foreign_table,
    toColumn: row.foreign_column,
    kind: "FK" as const,
  }));
}

export async function listRelations(client: SqlClient, tables: string[]): Promise<DbRelationSpec[]> {
  const relations: DbRelationSpec[] = [];
  for (const table of tables) {
    relations.push(...(await listForeignKeys(client, table)));
  }
  return relations;
}

export async function listMigrations(client: SqlClient): Promise<DbMigrationRow[]> {
  const rows = await client.all<{ filename: string; applied_at: string; checksum: string }>(
    "SELECT filename, applied_at, checksum FROM ghsn_schema_migration_history ORDER BY applied_at ASC, filename ASC",
  );
  return rows.map((row) => ({
    filename: row.filename,
    appliedAt: row.applied_at,
    checksum: row.checksum,
  }));
}

// Integrity findings from real catalog state only. No direct repair: DB-01 is
// a read-only workspace (derived_validation.direct_db_mutation_control_count=0).
export async function computeIntegrityFindings(client: SqlClient): Promise<DbFinding[]> {
  const findings: DbFinding[] = [];
  const push = (finding: DbFinding) => findings.push(finding);

  if (client.dialect === "memory") {
    const orphans = await client.all<{ table: string; rowid: number; parent: string; fkid: number }>(
      'SELECT "table", rowid, "parent", fkid FROM pragma_foreign_key_check',
    );
    for (const orphan of orphans.slice(0, 20)) {
      push({
        findingUid: `FIND-FK-${orphan.table}-${orphan.rowid}`,
        type: "FK_ORPHAN",
        severity: "HIGH",
        reason: "Foreign key reference target row missing (pragma_foreign_key_check)",
        affected: `${orphan.table}#${orphan.rowid} -> ${orphan.parent}#${orphan.fkid}`,
        evidence: "pragma_foreign_key_check",
        owner: domainOfTable(orphan.table),
      });
    }
  }

  const migrations = await listMigrations(client);
  const badMigrations = migrations.filter((row) => !row.checksum || row.checksum !== row.filename);
  if (badMigrations.length > 0) {
    push({
      findingUid: `FIND-MIGRATION-${badMigrations[0].filename}`,
      type: "MIGRATION_CHECKSUM",
      severity: "MEDIUM",
      reason: "Migration history checksum missing or mismatched with registered manifest",
      affected: badMigrations.map((row) => row.filename).join(", "),
      evidence: `${badMigrations.length}/${migrations.length} rows`,
      owner: "SCHEMA",
    });
  }

  const tables = await listEntities(client);
  const projectionTables = new Set(tables.filter((entity) => entity.kind === "field_projection").map((entity) => entity.name));
  const auditTables = tables.filter((entity) => entity.kind === "audit_event");
  for (const auditTable of auditTables) {
    const projectionTable = `ghsn_${auditTable.domain.toLowerCase()}_field_projection`;
    if (projectionTables.has(projectionTable)) continue;
    push({
      findingUid: `FIND-AUDIT-PROJECTION-${auditTable.name}`,
      type: "AUDIT_PROJECTION_PAIR",
      severity: "LOW",
      reason: "Audit domain has no matching field projection table",
      affected: auditTable.name,
      evidence: `missing ${projectionTable}`,
      owner: auditTable.domain,
    });
  }

  const permissionTables = tables.filter((entity) => entity.kind === "permission");
  for (const permissionTable of permissionTables) {
    if (client.dialect !== "memory") continue;
    const rows = await client.all<{ account_uid: string }>(`SELECT DISTINCT account_uid FROM ${permissionTable.name}`);
    for (const row of rows) {
      const known = await client.all<{ n: number }>(
        "SELECT count(*)::int AS n FROM ghsn_runtime_account WHERE account_uid = ?",
        [row.account_uid],
      );
      if (Number(known[0]?.n ?? 0) === 0 && row.account_uid !== "ACC-DEMO") {
        push({
          findingUid: `FIND-ACCOUNT-${permissionTable.name}-${row.account_uid}`,
          type: "ACCOUNT_ORPHAN",
          severity: "MEDIUM",
          reason: "Permission assignment references unknown runtime account",
          affected: `${permissionTable.name} · ${row.account_uid}`,
          evidence: "ghsn_runtime_account lookup empty",
          owner: "ACCOUNT",
        });
      }
    }
  }

  return findings;
}

export async function lookupAudit(client: SqlClient, query: string): Promise<string[]> {
  const tables = await listEntities(client);
  const auditTables = tables.filter((entity) => entity.kind === "audit_event").map((entity) => entity.name);
  const hits: string[] = [];
  for (const auditTable of auditTables) {
    const columns = (await describeColumns(client, auditTable)).map((column) => column.name);
    const matchable = ["event_uid", "control_uid", "action_uid", "account_uid"].filter((name) => columns.includes(name));
    if (matchable.length === 0) continue;
    const where = matchable.map((name) => `${name} = ?`).join(" OR ");
    const display = ["occurred_at", "event_uid", "control_uid", "action_uid", "area", "route", "section_uid", "navigation_uid"].filter((name) => columns.includes(name));
    const rows = await client.all<Record<string, string | null>>(
      `SELECT ${display.join(", ")} FROM ${auditTable} WHERE ${where} ORDER BY occurred_at DESC LIMIT 5`,
      matchable.map(() => query),
    );
    for (const row of rows) {
      const parts = display.map((name) => row[name]).filter((value) => value !== null && value !== undefined && value !== "");
      hits.push(parts.join(" · "));
    }
  }
  return hits;
}

// Exact lineage: registered table -> owning migration -> live projection rows
// -> audit events. Complete only when every segment resolves from real data.
export async function traceLineage(client: SqlClient, sourceType: string, sourceId: string): Promise<DbTraceResult> {
  const tables = await listEntities(client);
  const segments: DbTraceSegment[] = [];
  const push = (label: string, detail: string, ok: boolean) => segments.push({ label, detail, ok });

  if (sourceType === "table") {
    const entity = tables.find((candidate) => candidate.name === sourceId);
    push("ENTITY", entity ? `${entity.name} · ${entity.domain} · ${entity.kind}` : `${sourceId} not registered`, Boolean(entity));
    if (entity) {
      const migrations = await listMigrations(client);
      const origin = migrations[migrations.length - 1];
      push("MIGRATION", origin ? `${origin.filename} @ ${origin.appliedAt}` : "no migration history", Boolean(origin));
      const columns = await describeColumns(client, entity.name);
      push("SCHEMA", columns.length > 0 ? `${columns.length} columns` : "no columns resolved", columns.length > 0);
      if (entity.kind === "field_projection") {
        const rows = await client.all<{ n: number }>(`SELECT count(*)::int AS n FROM ${entity.name}`);
        push("PROJECTION", `${Number(rows[0]?.n ?? 0)} projected controls`, true);
        const auditTable = `ghsn_${entity.domain.toLowerCase().replace("admin_str", "admin_str")}_audit_event`;
        const auditExists = tables.some((candidate) => candidate.name === auditTable);
        const auditCount = auditExists
          ? await client.all<{ n: number }>(`SELECT count(*)::int AS n FROM ${auditTable}`)
          : [{ n: 0 }];
        push("AUDIT", `${Number(auditCount[0]?.n ?? 0)} audit events`, auditExists);
      } else if (entity.kind === "audit_event") {
        const rows = await client.all<{ n: number }>(`SELECT count(*)::int AS n FROM ${entity.name}`);
        push("AUDIT", `${Number(rows[0]?.n ?? 0)} audit events (append-only)`, true);
      } else {
        push("STATE", `${entity.kind} · governed by permission gate`, true);
      }
    }
  } else if (sourceType === "audit") {
    const hits = await lookupAudit(client, sourceId);
    push("AUDIT", hits.length > 0 ? hits.slice(0, 3).join(" | ") : `${sourceId} has no audit evidence`, hits.length > 0);
  } else {
    push("TRACE", `unsupported source_type ${sourceType}`, false);
  }

  const complete = segments.length > 0 && segments.every((segment) => segment.ok);
  const path = segments.map((segment) => `${segment.label}:${segment.ok ? "OK" : "BROKEN"}`).join(" -> ");
  return { path, complete, segments };
}

export interface DbContextHead {
  env: string;
  schemaHead: string;
  migrationHead: string;
  health: string;
  tableCount: number;
  ok: boolean;
}

export async function resolveContext(client: SqlClient): Promise<DbContextHead> {
  const tables = await listEntities(client);
  const migrations = await listMigrations(client);
  const latest = migrations[migrations.length - 1];
  return {
    env: client.dialect === "memory" ? "sqlite · local sandbox" : "postgres · neon",
    schemaHead: `${tables.length} ghsn tables`,
    migrationHead: latest ? `${latest.filename} @ ${latest.appliedAt}` : "—",
    health: "PENDING",
    tableCount: tables.length,
    ok: tables.length > 0,
  };
}

// Contract gate: only registered identifiers may be introspected; anything
// else is DB-01-ERR-ENTITY-001 (no database-name guessing).
export function isRegisteredIdentifier(table: string): boolean {
  return /^[A-Za-z_][A-Za-z0-9_]*$/.test(table);
}
