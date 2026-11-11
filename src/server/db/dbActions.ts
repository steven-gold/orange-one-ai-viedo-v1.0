import { getSqlClient } from "./client";
import {
  computeIntegrityFindings,
  describeColumns,
  listEntities,
  listForeignKeys,
  listMigrations,
  lookupAudit,
  primaryKeysOf,
  resolveContext,
  traceLineage,
  type DbFinding,
} from "./introspect";

// ACPOS DB-01 FINAL_LOCKED_ENCODING · actions (15) / gates (9) / errors (10) /
// stages (5). Read-only workspace: every action is CONTEXT_STATE or
// READ_MODEL_QUERY projected onto ghsn_db_field_projection; zero direct
// database mutation (derived_validation.direct_db_mutation_control_count = 0).

export const DB_STATE_ERROR_UID = "DB-01-STATE-ERROR";

const TABLE = "ghsn_db_field_projection";

const READ_PERMISSION = "database.metadata.read";
const TRACE_PERMISSION = "database.trace.read";
const MIGRATION_PERMISSION = "database.migration.read";
const INTEGRITY_PERMISSION = "database.integrity.read";
const AUDIT_PERMISSION = "audit.read";

export const DB_SCOPED_PERMISSIONS: Record<string, string> = {
  context: READ_PERMISSION,
  inspect: READ_PERMISSION,
  relation: READ_PERMISSION,
  trace: TRACE_PERMISSION,
  migration: MIGRATION_PERMISSION,
  integrity: INTEGRITY_PERMISSION,
  audit: AUDIT_PERMISSION,
};

interface DbErrorState {
  code: string;
  detail: string;
  recovery: string;
  at: string;
}

async function readField(controlUid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    "SELECT value_text FROM ghsn_db_field_projection WHERE control_uid = ?",
    [controlUid],
  );
  const value = rows[0]?.value_text;
  return value === undefined || value === "" ? null : value;
}

async function writeField(controlUid: string, value: string | null): Promise<void> {
  await getSqlClient().run(
    "INSERT INTO ghsn_db_field_projection (control_uid, value_text) VALUES (?, ?) ON CONFLICT (control_uid) DO UPDATE SET value_text = excluded.value_text",
    [controlUid, value ?? ""],
  );
}

async function writeError(error: DbErrorState): Promise<void> {
  await writeField(DB_STATE_ERROR_UID, JSON.stringify(error));
}

function err(code: string, detail: string, recovery: string): DbErrorState {
  return { code, detail, recovery, at: new Date().toISOString() };
}

async function hasScope(accountUid: string | undefined, scope: string): Promise<boolean> {
  if (!accountUid) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_db_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, scope],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

// Stage machine: max stage resolved from persisted projection state.
async function writeStage(): Promise<void> {
  const [tracePath, findings, migrationIntegrity, columns, contextHead] = await Promise.all([
    readField("DB-01-VIEW-TRACE-PATH"),
    readField("DB-01-LIST-FINDINGS"),
    readField("DB-01-FLD-MIGRATION-INTEGRITY"),
    readField("DB-01-TBL-COLUMNS"),
    readField("DB-01-FLD-SCHEMA-HEAD"),
  ]);
  let stage = "DB-01-STAGE-01-CONTEXT";
  if (contextHead) stage = "DB-01-STAGE-01-CONTEXT";
  if (columns) stage = "DB-01-STAGE-02-INSPECT";
  if (tracePath) stage = "DB-01-STAGE-03-TRACE";
  if (findings || migrationIntegrity) stage = "DB-01-STAGE-04-INTEGRITY";
  await writeField("DB-01-FLD-PAGE-STATE", stage);
}

async function selectedEntity(): Promise<string | null> {
  return readField("DB-01-FLD-ENTITY");
}

function entityListText(entities: Array<{ name: string; domain: string; kind: string }>, domainFilter: string | null, kindFilter: string | null, search: string | null): string {
  const needle = (search ?? "").trim().toLowerCase();
  const rows = entities.filter((entity) => {
    if (domainFilter && domainFilter !== "ALL" && entity.domain !== domainFilter) return false;
    if (kindFilter && kindFilter !== "ALL" && entity.kind !== kindFilter) return false;
    if (needle && !entity.name.toLowerCase().includes(needle)) return false;
    return true;
  });
  return rows.map((entity) => `${entity.name} · ${entity.domain} · ${entity.kind}`).join("\n");
}

async function clearEntityPanel(): Promise<void> {
  for (const uid of [
    "DB-01-FLD-ENTITY",
    "DB-01-FLD-TABLE",
    "DB-01-FLD-OWNER",
    "DB-01-FLD-CLASSIFICATION",
    "DB-01-FLD-PK",
    "DB-01-FLD-VERSION-RULE",
    "DB-01-TBL-COLUMNS",
    "DB-01-TBL-CONSTRAINTS",
    "DB-01-LIST-RELATIONS",
    "DB-01-GRAPH-RELATIONS",
    "DB-01-FLD-IMMUTABLE",
    "DB-01-FLD-SOURCE-SYNC",
  ]) {
    await writeField(uid, null);
  }
}

export async function applyDbWorkbenchAction(
  accountUid: string | undefined,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<void> {
  const client = getSqlClient();
  const own = async () => {
    if (nextValue !== undefined) await writeField(controlUid, nextValue);
  };

  switch (actionUid) {
    case "DB-01-ACT-NOOP":
      return;

    case "DB-01-ACT-CONTEXT": {
      // SEL-TRACE-TYPE / INP-TRACE-ID / INP-AUDIT-ID: authorized context value;
      // dependent trace/audit outputs are cleared (Word: dependent selections cleared).
      await own();
      await writeField("DB-01-VIEW-TRACE-PATH", null);
      await writeField("DB-01-FLD-TRACE-COMPLETE", null);
      await writeField("DB-01-VIEW-AUDIT", null);
      await writeStage();
      return;
    }

    case "DB-01-ACT-SEARCH": {
      await own();
      const entities = await listEntities(client);
      const domain = await readField("DB-01-SEL-DOMAIN");
      const kind = await readField("DB-01-SEL-ENTITY-TYPE");
      await writeField("DB-01-LIST-ENTITIES", entityListText(entities, domain, kind, nextValue ?? null));
      await writeStage();
      return;
    }

    case "DB-01-ACT-FILTER": {
      await own();
      if (controlUid !== "DB-01-SEL-FINDING-TYPE") {
        const entities = await listEntities(client);
        const domain = await readField("DB-01-SEL-DOMAIN");
        const kind = await readField("DB-01-SEL-ENTITY-TYPE");
        const search = await readField("DB-01-INP-SEARCH");
        await writeField("DB-01-LIST-ENTITIES", entityListText(entities, domain, kind, search));
      } else {
        const findingsRaw = await readField("DB-01-LIST-FINDINGS-ALL");
        if (findingsRaw) {
          const findings = JSON.parse(findingsRaw) as DbFinding[];
          const type = nextValue ?? null;
          const rows = findings.filter((finding) => !type || type === "ALL" || finding.type === type);
          await writeField("DB-01-LIST-FINDINGS", rows.map((finding) => `${finding.findingUid} · ${finding.type} · ${finding.severity}`).join("\n"));
        }
      }
      await writeStage();
      return;
    }

    case "DB-01-ACT-ENTITY-SELECT": {
      // GATE-ENTITY: selected entity/table is registered and permitted.
      const entities = await listEntities(client);
      const entity = entities.find((candidate) => candidate.name === (nextValue ?? "").trim());
      if (!entity) {
        await clearEntityPanel();
        await writeError(err("DB-01-ERR-ENTITY-001", `Entity/table not registered: ${nextValue ?? "(empty)"}`, "BLOCK selection; no database-name guessing"));
        await writeStage();
        return;
      }
      await writeField(DB_STATE_ERROR_UID, null);
      await writeField("DB-01-FLD-ENTITY", entity.name);
      await writeField("DB-01-FLD-TABLE", entity.name);
      await writeField("DB-01-FLD-OWNER", entity.domain);
      await writeField("DB-01-FLD-CLASSIFICATION", entity.kind);
      await writeStage();
      return;
    }

    case "DB-01-ACT-SCHEMA-REFRESH": {
      // BTN-REFRESH + BTN-SCHEMA-REFRESH: resolve context head (GATE-CONTEXT)
      // and, when an entity is selected, its authoritative schema panel.
      const context = await resolveContext(client);
      if (!context.ok) {
        await writeError(err("DB-01-ERR-CONTEXT-001", "Database context/environment/schema head unavailable", "BLOCK data panels; resolve authorized context"));
        return;
      }
      await writeField(DB_STATE_ERROR_UID, null);
      await writeField("DB-01-FLD-ENV", `${context.env} · ${context.tableCount} tables`);
      await writeField("DB-01-FLD-SCHEMA-HEAD", context.schemaHead);
      await writeField("DB-01-FLD-MIGRATION-HEAD", context.migrationHead);
      await writeField("DB-01-FLD-SCOPE", `admin:DB-01 · ${READ_PERMISSION} · single_machine_authority`);
      const entities = await listEntities(client);
      const domain = await readField("DB-01-SEL-DOMAIN");
      const kind = await readField("DB-01-SEL-ENTITY-TYPE");
      const search = await readField("DB-01-INP-SEARCH");
      await writeField("DB-01-LIST-ENTITIES", entityListText(entities, domain, kind, search));
      await writeField("DB-01-FLD-CHANGE-OWNER", context.migrationHead === "—" ? null : `schema_migration_history · ${context.migrationHead}`);
      const entity = await selectedEntity();
      if (entity) await inspectEntity(entity);
      await writeStage();
      return;
    }

    case "DB-01-ACT-RELATION-MODE": {
      await own();
      return;
    }

    case "DB-01-ACT-RELATION-OPEN": {
      // GATE-RELATION: registered typed relations only (FK constraints from
      // the live catalog); no inferred relation from naming.
      const entity = await selectedEntity();
      if (!entity) {
        await writeError(err("DB-01-ERR-SCHEMA-001", "No selected entity with authoritative schema metadata", "Select a registered entity and refresh schema"));
        return;
      }
      await writeField(DB_STATE_ERROR_UID, null);
      const relations = await listForeignKeys(client, entity);
      const rows = relations.map((relation) => `FK · ${relation.fromTable}.${relation.fromColumn} -> ${relation.toTable}.${relation.toColumn || "(rowid)"}`);
      await writeField("DB-01-LIST-RELATIONS", rows.length > 0 ? rows.join("\n") : null);
      await writeField("DB-01-GRAPH-RELATIONS", rows.length > 0 ? `${entity} => ${relations.map((relation) => relation.toTable).join(", ")}` : `${entity} (no registered FK relations)`);
      await writeStage();
      return;
    }

    case "DB-01-ACT-TRACE": {
      // GATE-TRACE: source_type + exact source_id/version present and authorized.
      if (!(await hasScope(accountUid, TRACE_PERMISSION))) {
        await writeError(err("DB-01-ERR-PERM-001", `${TRACE_PERMISSION} required for lineage trace`, "Disable access/action and show actual reason"));
        return;
      }
      const sourceType = await readField("DB-01-SEL-TRACE-TYPE");
      const sourceId = await readField("DB-01-INP-TRACE-ID");
      if (!sourceType || !sourceId) {
        await writeError(err("DB-01-ERR-TRACE-001", "Trace source ref missing", "Show broken path; do not silently repair or jump to latest"));
        await writeField("DB-01-FLD-TRACE-COMPLETE", null);
        return;
      }
      await writeField(DB_STATE_ERROR_UID, null);
      const trace = await traceLineage(client, sourceType, sourceId);
      const detail = trace.segments.map((segment) => `${segment.label} ${segment.ok ? "OK" : "BROKEN"} · ${segment.detail}`).join("\n");
      await writeField("DB-01-VIEW-TRACE-PATH", `${trace.path}\n${detail}`);
      await writeField("DB-01-FLD-TRACE-COMPLETE", trace.complete ? "COMPLETE" : "BROKEN");
      await writeStage();
      return;
    }

    case "DB-01-ACT-MIGRATION-SELECT": {
      await own();
      return;
    }

    case "DB-01-ACT-MIGRATION-REFRESH": {
      // GATE-MIGRATION: registered migration/checksum manifest from live history.
      if (!(await hasScope(accountUid, MIGRATION_PERMISSION))) {
        await writeError(err("DB-01-ERR-PERM-001", `${MIGRATION_PERMISSION} required`, "Disable access/action and show actual reason"));
        return;
      }
      const migrations = await listMigrations(client);
      if (migrations.length === 0) {
        await writeError(err("DB-01-ERR-MIGRATION-001", "Migration history empty or unavailable", "Show migration integrity blocker; route change to System Lifecycle"));
        return;
      }
      await writeField(DB_STATE_ERROR_UID, null);
      await writeField("DB-01-TBL-MIGRATIONS", migrations.map((row) => `${row.filename} · ${row.appliedAt} · ${row.checksum === row.filename ? "checksum OK" : `checksum ${row.checksum || "missing"}`}`).join("\n"));
      const invalid = migrations.filter((row) => !row.checksum || row.checksum !== row.filename);
      await writeField("DB-01-FLD-MIGRATION-INTEGRITY", invalid.length === 0 ? `OK · ${migrations.length} migrations` : `BLOCKED · ${invalid.length} invalid: ${invalid.map((row) => row.filename).join(", ")}`);
      if (invalid.length > 0) {
        await writeError(err("DB-01-ERR-MIGRATION-001", "Migration/checksum/dependency history invalid or incomplete", "Show migration integrity blocker; route change to System Lifecycle"));
      }
      await writeStage();
      return;
    }

    case "DB-01-ACT-INTEGRITY-REFRESH": {
      // GATE-INTEGRITY: integrity read source is the live catalog itself.
      if (!(await hasScope(accountUid, INTEGRITY_PERMISSION))) {
        await writeError(err("DB-01-ERR-PERM-001", `${INTEGRITY_PERMISSION} required`, "Disable access/action and show actual reason"));
        return;
      }
      const findings = await computeIntegrityFindings(client);
      await writeField(DB_STATE_ERROR_UID, null);
      await writeField("DB-01-LIST-FINDINGS-ALL", JSON.stringify(findings));
      const typeFilter = await readField("DB-01-SEL-FINDING-TYPE");
      const rows = findings.filter((finding) => !typeFilter || typeFilter === "ALL" || finding.type === typeFilter);
      await writeField("DB-01-LIST-FINDINGS", rows.length > 0 ? rows.map((finding) => `${finding.findingUid} · ${finding.type} · ${finding.severity}`).join("\n") : "NO FINDINGS · catalog checks clean");
      const fks = findings.filter((finding) => finding.type === "FK_ORPHAN");
      await writeField("DB-01-FLD-REF-INTEGRITY", fks.length === 0 ? "OK · foreign_key_check clean" : `${fks.length} orphan reference(s)`);
      const orphans = findings.filter((finding) => finding.type === "ACCOUNT_ORPHAN" || finding.type === "AUDIT_PROJECTION_PAIR");
      await writeField("DB-01-FLD-ORPHAN", orphans.length === 0 ? null : orphans.map((finding) => finding.findingUid).join(", "));
      await writeField("DB-01-FLD-HEALTH", findings.length === 0 ? "OK" : `${findings.length} finding(s)`);
      const entity = await selectedEntity();
      if (entity) {
        const entityFindings = findings.filter((finding) => finding.affected.includes(entity));
        await writeField("DB-01-FLD-DISABLED", entityFindings.length === 0 ? null : entityFindings.map((finding) => finding.type).join(", "));
      }
      if (findings.length > 0) {
        await writeError(err("DB-01-ERR-INTEGRITY-001", findings[0].reason, "Show finding and affected exact refs; no direct production repair"));
      }
      await writeStage();
      return;
    }

    case "DB-01-ACT-FINDING-SELECT": {
      const allRaw = await readField("DB-01-LIST-FINDINGS-ALL");
      if (!allRaw) {
        await writeError(err("DB-01-ERR-INTEGRITY-001", "No integrity findings loaded", "Run integrity refresh first"));
        return;
      }
      const findings = JSON.parse(allRaw) as DbFinding[];
      const finding = findings.find((candidate) => candidate.findingUid === (nextValue ?? "").trim().split(" · ")[0]);
      if (!finding) {
        await writeError(err("DB-01-ERR-INTEGRITY-001", `Finding not registered: ${nextValue ?? "(empty)"}`, "Show finding and affected exact refs"));
        return;
      }
      await writeField(DB_STATE_ERROR_UID, null);
      await writeField("DB-01-FLD-FINDING-REASON", finding.reason);
      await writeField("DB-01-FLD-FINDING-AFFECTED", finding.affected);
      await writeField("DB-01-FLD-FINDING-EVIDENCE", finding.evidence);
      await writeField("DB-01-FLD-FINDING-OWNER", finding.owner);
      await writeStage();
      return;
    }

    case "DB-01-ACT-AUDIT-OPEN": {
      // GATE-AUDIT: audit read permission + exact correlation/entity scope.
      if (!(await hasScope(accountUid, AUDIT_PERMISSION))) {
        await writeError(err("DB-01-ERR-PERM-001", `${AUDIT_PERMISSION} required`, "Disable access/action and show actual reason"));
        return;
      }
      const query = await readField("DB-01-INP-AUDIT-ID");
      if (!query) {
        await writeError(err("DB-01-ERR-AUDIT-001", "Audit correlation id missing", "Show read restriction / missing audit evidence"));
        return;
      }
      const hits = await lookupAudit(client, query);
      if (hits.length === 0) {
        await writeError(err("DB-01-ERR-AUDIT-001", `No audit evidence for ${query}`, "Show read restriction / missing audit evidence"));
        await writeField("DB-01-VIEW-AUDIT", null);
        return;
      }
      await writeField(DB_STATE_ERROR_UID, null);
      await writeField("DB-01-VIEW-AUDIT", hits.join("\n"));
      await writeStage();
      return;
    }

    case "DB-01-ACT-SYSTEM-LIFECYCLE":
      // UI_ONLY: route change is owned by the global shell; no projection write.
      return;

    default:
      // Word §errors: unlisted action is BLOCK + REPORT_AUTHORITY_GAP. The
      // route layer 404s first; this projection-level guard mirrors QA-01.
      await writeError(err("DB-01-ERR-UNDEFINED-001", `Unlisted control/action requested: ${controlUid}/${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
      return;
  }
}

async function inspectEntity(entity: string): Promise<void> {
  const client = getSqlClient();
  const columns = await describeColumns(client, entity);
  if (columns.length === 0) {
    await writeError(err("DB-01-ERR-SCHEMA-001", `Schema/column/relation metadata missing for ${entity}`, "Show explicit authority gap/integrity finding; do not synthesize schema"));
    return;
  }
  await writeField(DB_STATE_ERROR_UID, null);
  await writeField("DB-01-TBL-COLUMNS", columns.map((column) => `${column.name} · ${column.type} · ${column.notNull ? "NOT NULL" : "nullable"}${column.pk ? " · PK" : ""}`).join("\n"));
  const pks = columns.filter((column) => column.pk).map((column) => column.name);
  await writeField("DB-01-FLD-PK", pks.length > 0 ? pks.join(", ") : "rowid");
  const constraints = columns.filter((column) => column.notNull && !column.pk).map((column) => `NOT NULL · ${column.name}`);
  const relations = await listForeignKeys(client, entity);
  for (const relation of relations) constraints.push(`FK · ${relation.fromColumn} -> ${relation.toTable}.${relation.toColumn || "(rowid)"}`);
  await writeField("DB-01-TBL-CONSTRAINTS", constraints.length > 0 ? constraints.join("\n") : null);
  await writeField("DB-01-FLD-VERSION-RULE", isImmutableKind(entity) ? "immutable lineage · append-only" : "projection · governed by applyAction whitelist");
  await writeField("DB-01-FLD-IMMUTABLE", isImmutableKind(entity) ? "YES (append-only)" : "NO (projection)");
  const audits = await lookupAudit(client, entity);
  await writeField("DB-01-FLD-SOURCE-SYNC", audits.length > 0 ? audits[0].split(" · ")[0] : "no audit events yet");
}

function isImmutableKind(entity: string): boolean {
  return entity.endsWith("_audit_event") || entity === "ghsn_schema_migration_history";
}
