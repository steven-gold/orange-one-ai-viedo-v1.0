import { openSqlClient, type SqlClient } from "./client";
import { seedRuntimeIdentity } from "./seed";

const DDL = [
  `CREATE TABLE IF NOT EXISTS ghsn_schema_migration_history (
    filename TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    checksum TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_navigation_authority (
    navigation_uid TEXT PRIMARY KEY,
    area TEXT NOT NULL CHECK (area IN ('FRONT', 'ADMIN')),
    label_key TEXT NOT NULL,
    route TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    icon TEXT NOT NULL,
    aria_label_key TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_permission_assignment (
    account_uid TEXT NOT NULL,
    navigation_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, navigation_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_navigation_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    area TEXT NOT NULL,
    navigation_uid TEXT NOT NULL,
    route TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_session (
    session_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    issued_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_dashboard_section_projection (
    section_uid TEXT PRIMARY KEY,
    control_uid TEXT NOT NULL,
    label TEXT NOT NULL,
    value_text TEXT,
    detail_text TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_dashboard_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_dashboard_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    section_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_core_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_core_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_core_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_asset_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_asset_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_asset_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_video_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_video_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_video_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_edit_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_edit_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_edit_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_qa_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_qa_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_qa_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_db_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_db_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_db_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_str_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_str_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_str_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_info_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_info_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_info_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_sys_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_sys_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_sys_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_iam_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_iam_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_iam_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_dev_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_dev_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_dev_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_soc_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_soc_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_soc_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_erp_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_erp_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_erp_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_aiapi_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_aiapi_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_aiapi_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_aiapi_credential (
    credential_uid TEXT PRIMARY KEY,
    secret_text TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_sg02_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_sg02_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_sg02_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_admin_str_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_admin_str_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_admin_str_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_kb_field_projection (
    control_uid TEXT PRIMARY KEY,
    value_text TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_account_kb_permission (
    account_uid TEXT NOT NULL,
    permission_uid TEXT NOT NULL,
    PRIMARY KEY (account_uid, permission_uid)
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_kb_audit_event (
    event_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    control_uid TEXT NOT NULL,
    action_uid TEXT NOT NULL,
    occurred_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_runtime_account (
    account_uid TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    disabled_at TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_app_user (
    user_uid TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    account_uid TEXT NOT NULL,
    disabled_at TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS ghsn_identity_session (
    session_uid TEXT PRIMARY KEY,
    account_uid TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    issued_at TEXT NOT NULL
  )`,
];

export interface MigrationResult {
  applied: string[];
  alreadyApplied: string[];
  dialect: SqlClient["dialect"];
  migrationCount: number;
}

let bootstrapPromise: Promise<MigrationResult> | null = null;

const MIGRATION_FILES = [
  "001_init.sql",
  "002_sessions_and_history.sql",
  "003_dashboard.sql",
  "004_core.sql",
  "005_asset.sql",
  "006_video.sql",
  "007_edit.sql",
  "008_qa.sql",
  "009_db.sql",
  "010_str.sql",
  "011_info.sql",
  "012_sys.sql",
  "013_iam.sql",
  "014_dev.sql",
  "015_soc.sql",
  "016_erp.sql",
  "017_aiapi.sql",
  "018_sg02.sql",
  "019_admin_str.sql",
  "020_admin_kb.sql",
  "021_identity_session.sql",
  "022_reset_core_drafts.sql",
  "023_reset_aiapi_drafts.sql",
  "024_reset_aiapi_drafts.sql",
  "025_reset_aiapi_drafts.sql",
  "026_reset_aiapi_drafts.sql",
  "027_reset_aiapi_registry.sql",
];

const RESET_CORE_DRAFTS = [
  "UPDATE ghsn_core_field_projection SET value_text = NULL",
  `UPDATE ghsn_asset_field_projection SET value_text = NULL WHERE control_uid IN (
    'ASSET-01-CTL-PROJECT','ASSET-01-CTL-TOPIC','ASSET-01-FLD-TASK','ASSET-01-FLD-TASK-STATUS',
    'ASSET-01-FLD-BLUEPRINT','ASSET-01-FLD-SCRIPT','ASSET-01-FLD-DNA','ASSET-01-FLD-MANIFEST',
    'ASSET-01-FLD-CANONICAL-FILENAME','ASSET-01-FLD-NAMING-AUTHORITY',
    'ASSET-01-FLD-HANDOFF-ASSET-VERSION','ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE','ASSET-01-FLD-HANDOFF-BLUEPRINT',
    'ASSET-01-FLD-HANDOFF-SCRIPT-HASH','ASSET-01-FLD-HANDOFF-DNA','ASSET-01-FLD-HANDOFF-MANIFEST-ITEMS',
    'ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME','ASSET-01-FLD-HANDOFF-CHECKSUM','ASSET-01-FLD-HANDOFF-SCORECARD',
    'ASSET-01-FLD-HANDOFF-RIGHTS','ASSET-01-FLD-HANDOFF-CONTRACT-HASH'
  )`,
  `UPDATE ghsn_video_field_projection SET value_text = NULL WHERE control_uid IN (
    'VIDEO-01-FLD-PROJECT','VIDEO-01-FLD-TOPIC','VIDEO-01-FLD-TASK','VIDEO-01-FLD-BLUEPRINT-REF',
    'VIDEO-01-FLD-DNA-REFS','VIDEO-01-FLD-SCRIPT-SECTION','VIDEO-01-FLD-ASSET-REFS'
  )`,
  "UPDATE ghsn_dashboard_section_projection SET value_text = NULL, detail_text = ''",
];

const RESET_AIAPI_DRAFTS = [
  "UPDATE ghsn_aiapi_field_projection SET value_text = NULL",
];

const RESET_AIAPI_REGISTRY = [
  "UPDATE ghsn_aiapi_field_projection SET value_text = NULL",
  "DELETE FROM ghsn_aiapi_credential",
];

const RESET_MIGRATIONS: Record<string, string[]> = {
  "022_reset_core_drafts.sql": RESET_CORE_DRAFTS,
  "023_reset_aiapi_drafts.sql": RESET_AIAPI_DRAFTS,
  "024_reset_aiapi_drafts.sql": RESET_AIAPI_DRAFTS,
  "025_reset_aiapi_drafts.sql": RESET_AIAPI_DRAFTS,
  "026_reset_aiapi_drafts.sql": RESET_AIAPI_DRAFTS,
  "027_reset_aiapi_registry.sql": RESET_AIAPI_REGISTRY,
};

async function runBootstrap(): Promise<MigrationResult> {
  const client = await openSqlClient();
  try {
    const existing = await client.all<{ filename: string }>("SELECT filename FROM ghsn_schema_migration_history");
    const applied = new Set(existing.map((row) => row.filename));
    if (MIGRATION_FILES.every((filename) => applied.has(filename))) {
      await seedRuntimeIdentity(client);
      return {
        applied: [],
        alreadyApplied: [...MIGRATION_FILES],
        dialect: client.dialect,
        migrationCount: existing.length,
      };
    }
  } catch {
    // Schema is not ready yet; fall through to CREATE TABLE.
  }
  for (const statement of DDL) {
    await client.exec(statement);
  }
  const existing = await client.all<{ filename: string }>("SELECT filename FROM ghsn_schema_migration_history");
  const applied = new Set(existing.map((row) => row.filename));
  const newlyApplied: string[] = [];
  const alreadyApplied: string[] = [];
  for (const filename of MIGRATION_FILES) {
    if (applied.has(filename)) {
      alreadyApplied.push(filename);
      continue;
    }
    const resetStatements = RESET_MIGRATIONS[filename];
    if (resetStatements) {
      for (const statement of resetStatements) {
        await client.exec(statement);
      }
    }
    await client.run(
      `INSERT INTO ghsn_schema_migration_history (filename, applied_at, checksum)
       VALUES (?, ?, ?)
       ON CONFLICT (filename) DO NOTHING`,
      [filename, new Date().toISOString(), filename],
    );
    newlyApplied.push(filename);
  }
  await seedRuntimeIdentity(client);
  const countRows = await client.all<{ n: number }>("SELECT count(*)::int AS n FROM ghsn_schema_migration_history");
  return {
    applied: newlyApplied,
    alreadyApplied,
    dialect: client.dialect,
    migrationCount: Number(countRows[0]?.n ?? 0),
  };
}

export async function bootstrapDatabase(): Promise<MigrationResult> {
  if (!bootstrapPromise) {
    bootstrapPromise = runBootstrap().catch((error) => {
      bootstrapPromise = null;
      throw error;
    });
  }
  return bootstrapPromise;
}

export async function readyCheck(): Promise<{
  ready: boolean;
  dialect: string;
  migrationCount: number;
  reason: string;
}> {
  try {
    const result = await bootstrapDatabase();
    return {
      ready: result.migrationCount >= 1,
      dialect: result.dialect,
      migrationCount: result.migrationCount,
      reason: result.migrationCount >= 1 ? "BOUND" : "SCHEMA_MIGRATION_HISTORY_UNAVAILABLE",
    };
  } catch (error) {
    return {
      ready: false,
      dialect: "unbound",
      migrationCount: 0,
      reason: error instanceof Error ? error.message : "DATABASE_RUNTIME_NOT_BOUND",
    };
  }
}
