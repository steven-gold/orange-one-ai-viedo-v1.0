export const DB_PORT_UIDS = [
  "DB-01-PORT-ENTITY-LIST",
  "DB-01-PORT-SCHEMA",
  "DB-01-PORT-TRACE",
  "DB-01-PORT-MIGRATION",
  "DB-01-PORT-INTEGRITY",
  "DB-01-PORT-AUDIT",
  "DB-01-PORT-SYSTEM-LIFECYCLE",
] as const;
export type DbPortUid = typeof DB_PORT_UIDS[number];

export const DB_READ_OPERATIONS = {
  "DB-01-PORT-ENTITY-LIST": "DatabaseReadModel.list_entities",
  "DB-01-PORT-SCHEMA": "DatabaseReadModel.get_entity_schema",
  "DB-01-PORT-TRACE": "TraceabilityReadModel.trace_entity_lineage",
  "DB-01-PORT-MIGRATION": "MigrationReadModel.list_history",
  "DB-01-PORT-INTEGRITY": "DatabaseIntegrityReadModel.list_findings",
  "DB-01-PORT-AUDIT": "AuditReadModel.trace",
} as const;
export type DbReadPortUid = keyof typeof DB_READ_OPERATIONS;
export type DbReadOperation = typeof DB_READ_OPERATIONS[DbReadPortUid];

export const DB_PORT_METHOD_PATH: Record<DbReadPortUid, { method: "GET"; path: string }> = {
  "DB-01-PORT-ENTITY-LIST": { method: "GET", path: "/v1/database/entities" },
  "DB-01-PORT-SCHEMA": { method: "GET", path: "/v1/database/entities/{id}" },
  "DB-01-PORT-TRACE": { method: "GET", path: "/v1/database/trace" },
  "DB-01-PORT-MIGRATION": { method: "GET", path: "/v1/database/migrations" },
  "DB-01-PORT-INTEGRITY": { method: "GET", path: "/v1/database/integrity-findings" },
  "DB-01-PORT-AUDIT": { method: "GET", path: "/v1/audit-events" },
};

export const DB_PORT_PERMISSION: Record<DbReadPortUid, string> = {
  "DB-01-PORT-ENTITY-LIST": "database.metadata.read",
  "DB-01-PORT-SCHEMA": "database.metadata.read",
  "DB-01-PORT-TRACE": "database.trace.read",
  "DB-01-PORT-MIGRATION": "database.migration.read",
  "DB-01-PORT-INTEGRITY": "database.integrity.read",
  "DB-01-PORT-AUDIT": "audit.read",
};

export const DB_PORT_COUNT = DB_PORT_UIDS.length;
export const DB_EXPECTED_ACTION_COUNT = 15;
export const DB_EXPECTED_CONTROL_COUNT = 49;

export type DbErrorUid =
  | "DB-01-ERR-CONTEXT-001"
  | "DB-01-ERR-ENTITY-001"
  | "DB-01-ERR-SCHEMA-001"
  | "DB-01-ERR-TRACE-001"
  | "DB-01-ERR-VERSION-001"
  | "DB-01-ERR-MIGRATION-001"
  | "DB-01-ERR-INTEGRITY-001"
  | "DB-01-ERR-AUDIT-001"
  | "DB-01-ERR-PERM-001"
  | "DB-01-ERR-UNDEFINED-001";
