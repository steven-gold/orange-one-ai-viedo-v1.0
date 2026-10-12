import { ASSET_PERMISSION, ASSET_VISIBLE_CONTROLS } from "../domain/asset";
import { CORE_PERMISSION, CORE_VISIBLE_CONTROLS } from "../domain/core";
import { EDIT_PERMISSION, EDIT_VISIBLE_CONTROLS } from "../domain/edit";
import { DB_PERMISSION, DB_VISIBLE_CONTROLS } from "../domain/db";
import { QA_PERMISSION, QA_VISIBLE_CONTROLS } from "../domain/qa";
import { INFO_PERMISSION, INFO_VISIBLE_CONTROLS } from "../domain/info";
import { SYS_PERMISSION, SYS_VISIBLE_CONTROLS } from "../domain/sys";
import { IAM_PERMISSION, IAM_VISIBLE_CONTROLS } from "../domain/iam";
import { DEV_PERMISSION, DEV_VISIBLE_CONTROLS } from "../domain/dev";
import { SOC_PERMISSION, SOC_VISIBLE_CONTROLS } from "../domain/soc";
import { ERP_PERMISSION, ERP_VISIBLE_CONTROLS } from "../domain/erp";
import { AIAPI_PERMISSION, AIAPI_VISIBLE_CONTROLS } from "../domain/aiapi";
import { SG02_PERMISSION, SG02_VISIBLE_CONTROLS } from "../domain/sg02";
import { ADMIN_STR_PERMISSION, ADMIN_STR_VISIBLE_CONTROLS } from "../domain/adminStr";
import { KB_PERMISSION, KB_VISIBLE_CONTROLS } from "../domain/kb";
import { STR_PERMISSION, STR_VISIBLE_CONTROLS } from "../domain/str";
import { VIDEO_PERMISSION, VIDEO_VISIBLE_CONTROLS } from "../domain/video";
import { DASHBOARD_PERMISSION, DASHBOARD_SECTION_SEEDS } from "../domain/dashboard";
import { CANONICAL_NAVIGATION_AUTHORITY } from "../domain/schema";
import { getSqlClient, type SqlClient } from "./client";

export type SeedScope =
  | "identity"
  | "navigation"
  | "dashboard"
  | "core"
  | "asset"
  | "video"
  | "edit"
  | "qa"
  | "db"
  | "str"
  | "info"
  | "sys"
  | "iam"
  | "dev"
  | "soc"
  | "erp"
  | "aiapi"
  | "sg02"
  | "adminStr"
  | "kb";

const DEMO_SESSION = "sess-demo-001";
const DEMO_ACCOUNT = "ACC-DEMO";
const seeded = new Set<SeedScope>();

type PageSeed = {
  fieldTable: string;
  permissionTable: string;
  permission: string;
  controls: readonly string[];
};

const PAGE_SEEDS: Record<Exclude<SeedScope, "identity" | "navigation" | "dashboard">, PageSeed> = {
  core: { fieldTable: "ghsn_core_field_projection", permissionTable: "ghsn_account_core_permission", permission: CORE_PERMISSION, controls: CORE_VISIBLE_CONTROLS },
  asset: { fieldTable: "ghsn_asset_field_projection", permissionTable: "ghsn_account_asset_permission", permission: ASSET_PERMISSION, controls: ASSET_VISIBLE_CONTROLS },
  video: { fieldTable: "ghsn_video_field_projection", permissionTable: "ghsn_account_video_permission", permission: VIDEO_PERMISSION, controls: VIDEO_VISIBLE_CONTROLS },
  edit: { fieldTable: "ghsn_edit_field_projection", permissionTable: "ghsn_account_edit_permission", permission: EDIT_PERMISSION, controls: EDIT_VISIBLE_CONTROLS },
  qa: { fieldTable: "ghsn_qa_field_projection", permissionTable: "ghsn_account_qa_permission", permission: QA_PERMISSION, controls: QA_VISIBLE_CONTROLS },
  db: { fieldTable: "ghsn_db_field_projection", permissionTable: "ghsn_account_db_permission", permission: DB_PERMISSION, controls: DB_VISIBLE_CONTROLS },
  str: { fieldTable: "ghsn_str_field_projection", permissionTable: "ghsn_account_str_permission", permission: STR_PERMISSION, controls: STR_VISIBLE_CONTROLS },
  info: { fieldTable: "ghsn_info_field_projection", permissionTable: "ghsn_account_info_permission", permission: INFO_PERMISSION, controls: INFO_VISIBLE_CONTROLS },
  sys: { fieldTable: "ghsn_sys_field_projection", permissionTable: "ghsn_account_sys_permission", permission: SYS_PERMISSION, controls: SYS_VISIBLE_CONTROLS },
  iam: { fieldTable: "ghsn_iam_field_projection", permissionTable: "ghsn_account_iam_permission", permission: IAM_PERMISSION, controls: IAM_VISIBLE_CONTROLS },
  dev: { fieldTable: "ghsn_dev_field_projection", permissionTable: "ghsn_account_dev_permission", permission: DEV_PERMISSION, controls: DEV_VISIBLE_CONTROLS },
  soc: { fieldTable: "ghsn_soc_field_projection", permissionTable: "ghsn_account_soc_permission", permission: SOC_PERMISSION, controls: SOC_VISIBLE_CONTROLS },
  erp: { fieldTable: "ghsn_erp_field_projection", permissionTable: "ghsn_account_erp_permission", permission: ERP_PERMISSION, controls: ERP_VISIBLE_CONTROLS },
  aiapi: { fieldTable: "ghsn_aiapi_field_projection", permissionTable: "ghsn_account_aiapi_permission", permission: AIAPI_PERMISSION, controls: AIAPI_VISIBLE_CONTROLS },
  sg02: { fieldTable: "ghsn_sg02_field_projection", permissionTable: "ghsn_account_sg02_permission", permission: SG02_PERMISSION, controls: SG02_VISIBLE_CONTROLS },
  adminStr: { fieldTable: "ghsn_admin_str_field_projection", permissionTable: "ghsn_account_admin_str_permission", permission: ADMIN_STR_PERMISSION, controls: ADMIN_STR_VISIBLE_CONTROLS },
  kb: { fieldTable: "ghsn_kb_field_projection", permissionTable: "ghsn_account_kb_permission", permission: KB_PERMISSION, controls: KB_VISIBLE_CONTROLS },
};

async function insertRows(
  client: SqlClient,
  tableSql: string,
  conflictSql: string,
  columnsPerRow: number,
  rows: unknown[][],
): Promise<void> {
  if (rows.length === 0) return;
  const chunkSize = Math.max(1, Math.floor(120 / columnsPerRow));
  for (let offset = 0; offset < rows.length; offset += chunkSize) {
    const chunk = rows.slice(offset, offset + chunkSize);
    const values = chunk
      .map(() => `(${Array.from({ length: columnsPerRow }, () => "?").join(", ")})`)
      .join(", ");
    await client.run(`${tableSql} VALUES ${values} ${conflictSql}`, chunk.flat());
  }
}

async function alreadyGranted(client: SqlClient, table: string, permission: string): Promise<boolean> {
  const rows = await client.all<{ n: number }>(
    `SELECT count(*)::int AS n FROM ${table} WHERE account_uid = ? AND permission_uid = ?`,
    [DEMO_ACCOUNT, permission],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

async function seedIdentity(client: SqlClient): Promise<void> {
  const rows = await client.all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_session WHERE session_uid = ? AND account_uid = ?",
    [DEMO_SESSION, DEMO_ACCOUNT],
  );
  if (Number(rows[0]?.n ?? 0) > 0) return;
  const now = new Date().toISOString();
  await insertRows(
    client,
    `INSERT INTO ghsn_account_session (session_uid, account_uid, issued_at)`,
    `ON CONFLICT (session_uid) DO UPDATE SET account_uid = EXCLUDED.account_uid`,
    3,
    [
      [DEMO_SESSION, DEMO_ACCOUNT, now],
      ["sess-limited-001", "ACC-LIMITED", now],
    ],
  );
}

async function seedNavigation(client: SqlClient): Promise<void> {
  const rows = await client.all<{ n: number }>("SELECT count(*)::int AS n FROM ghsn_navigation_authority");
  if (Number(rows[0]?.n ?? 0) >= CANONICAL_NAVIGATION_AUTHORITY.items.length) return;
  await insertRows(
    client,
    `INSERT INTO ghsn_navigation_authority (navigation_uid, area, label_key, route, display_order, icon, aria_label_key)`,
    `ON CONFLICT (navigation_uid) DO UPDATE SET
      area = EXCLUDED.area,
      label_key = EXCLUDED.label_key,
      route = EXCLUDED.route,
      display_order = EXCLUDED.display_order,
      icon = EXCLUDED.icon,
      aria_label_key = EXCLUDED.aria_label_key`,
    7,
    CANONICAL_NAVIGATION_AUTHORITY.items.map((item) => [
      item.uid,
      item.area,
      item.labelKey,
      item.route,
      item.order,
      item.icon,
      item.ariaLabelKey,
    ]),
  );
  await insertRows(
    client,
    `INSERT INTO ghsn_account_permission_assignment (account_uid, navigation_uid)`,
    `ON CONFLICT (account_uid, navigation_uid) DO NOTHING`,
    2,
    [
      ...CANONICAL_NAVIGATION_AUTHORITY.items.map((item) => [DEMO_ACCOUNT, item.uid]),
      ["ACC-LIMITED", "workspace:WB-01"],
      ["ACC-LIMITED", "CORE-01"],
    ],
  );
}

async function seedDashboard(client: SqlClient): Promise<void> {
  if (await alreadyGranted(client, "ghsn_account_dashboard_permission", DASHBOARD_PERMISSION)) return;
  await insertRows(
    client,
    `INSERT INTO ghsn_dashboard_section_projection (section_uid, control_uid, label, value_text, detail_text)`,
    `ON CONFLICT (section_uid) DO UPDATE SET control_uid = EXCLUDED.control_uid, label = EXCLUDED.label`,
    5,
    DASHBOARD_SECTION_SEEDS.map((section) => [section.sectionUid, section.controlUid, section.label, null, ""]),
  );
  await insertRows(
    client,
    `INSERT INTO ghsn_account_dashboard_permission (account_uid, permission_uid)`,
    `ON CONFLICT (account_uid, permission_uid) DO NOTHING`,
    2,
    [
      [DEMO_ACCOUNT, DASHBOARD_PERMISSION],
      ["ACC-LIMITED", DASHBOARD_PERMISSION],
    ],
  );
}

async function seedPage(client: SqlClient, page: PageSeed): Promise<void> {
  if (await alreadyGranted(client, page.permissionTable, page.permission)) return;
  await insertRows(
    client,
    `INSERT INTO ${page.fieldTable} (control_uid, value_text)`,
    `ON CONFLICT (control_uid) DO NOTHING`,
    2,
    page.controls.map((controlUid) => [controlUid, null]),
  );
  await client.run(
    `INSERT INTO ${page.permissionTable} (account_uid, permission_uid)
     VALUES (?, ?)
     ON CONFLICT (account_uid, permission_uid) DO NOTHING`,
    [DEMO_ACCOUNT, page.permission],
  );
}

export async function seedScope(scope: SeedScope, client: SqlClient = getSqlClient()): Promise<void> {
  if (seeded.has(scope)) return;
  if (scope === "identity") await seedIdentity(client);
  else if (scope === "navigation") await seedNavigation(client);
  else if (scope === "dashboard") await seedDashboard(client);
  else await seedPage(client, PAGE_SEEDS[scope]);
  seeded.add(scope);
}

export async function seedRuntimeIdentity(client: SqlClient): Promise<void> {
  await seedScope("identity", client);
  await seedScope("navigation", client);
}
