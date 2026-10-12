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
import type { SqlClient } from "./client";

const DEMO_SESSION = "sess-demo-001";
const DEMO_ACCOUNT = "ACC-DEMO";

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

export async function seedCanonicalData(client: SqlClient): Promise<void> {
  const seeded = await client.all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_session WHERE session_uid = ? AND account_uid = ?",
    [DEMO_SESSION, DEMO_ACCOUNT],
  );
  const permitted = await client.all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_core_permission WHERE account_uid = ? AND permission_uid = ?",
    [DEMO_ACCOUNT, CORE_PERMISSION],
  );
  if (Number(seeded[0]?.n ?? 0) > 0 && Number(permitted[0]?.n ?? 0) > 0) {
    return;
  }

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

  const fieldTables: Array<{ table: string; controls: readonly string[] }> = [
    { table: "ghsn_core_field_projection", controls: CORE_VISIBLE_CONTROLS },
    { table: "ghsn_asset_field_projection", controls: ASSET_VISIBLE_CONTROLS },
    { table: "ghsn_video_field_projection", controls: VIDEO_VISIBLE_CONTROLS },
    { table: "ghsn_edit_field_projection", controls: EDIT_VISIBLE_CONTROLS },
    { table: "ghsn_qa_field_projection", controls: QA_VISIBLE_CONTROLS },
    { table: "ghsn_db_field_projection", controls: DB_VISIBLE_CONTROLS },
    { table: "ghsn_str_field_projection", controls: STR_VISIBLE_CONTROLS },
    { table: "ghsn_info_field_projection", controls: INFO_VISIBLE_CONTROLS },
    { table: "ghsn_sys_field_projection", controls: SYS_VISIBLE_CONTROLS },
    { table: "ghsn_iam_field_projection", controls: IAM_VISIBLE_CONTROLS },
    { table: "ghsn_dev_field_projection", controls: DEV_VISIBLE_CONTROLS },
    { table: "ghsn_soc_field_projection", controls: SOC_VISIBLE_CONTROLS },
    { table: "ghsn_erp_field_projection", controls: ERP_VISIBLE_CONTROLS },
    { table: "ghsn_aiapi_field_projection", controls: AIAPI_VISIBLE_CONTROLS },
    { table: "ghsn_sg02_field_projection", controls: SG02_VISIBLE_CONTROLS },
    { table: "ghsn_admin_str_field_projection", controls: ADMIN_STR_VISIBLE_CONTROLS },
    { table: "ghsn_kb_field_projection", controls: KB_VISIBLE_CONTROLS },
  ];
  for (const field of fieldTables) {
    await insertRows(
      client,
      `INSERT INTO ${field.table} (control_uid, value_text)`,
      `ON CONFLICT (control_uid) DO NOTHING`,
      2,
      field.controls.map((controlUid) => [controlUid, null]),
    );
  }

  const permissionGrants: Array<{ table: string; permission: string }> = [
    { table: "ghsn_account_core_permission", permission: CORE_PERMISSION },
    { table: "ghsn_account_asset_permission", permission: ASSET_PERMISSION },
    { table: "ghsn_account_video_permission", permission: VIDEO_PERMISSION },
    { table: "ghsn_account_edit_permission", permission: EDIT_PERMISSION },
    { table: "ghsn_account_qa_permission", permission: QA_PERMISSION },
    { table: "ghsn_account_db_permission", permission: DB_PERMISSION },
    { table: "ghsn_account_str_permission", permission: STR_PERMISSION },
    { table: "ghsn_account_info_permission", permission: INFO_PERMISSION },
    { table: "ghsn_account_sys_permission", permission: SYS_PERMISSION },
    { table: "ghsn_account_iam_permission", permission: IAM_PERMISSION },
    { table: "ghsn_account_dev_permission", permission: DEV_PERMISSION },
    { table: "ghsn_account_soc_permission", permission: SOC_PERMISSION },
    { table: "ghsn_account_erp_permission", permission: ERP_PERMISSION },
    { table: "ghsn_account_aiapi_permission", permission: AIAPI_PERMISSION },
    { table: "ghsn_account_sg02_permission", permission: SG02_PERMISSION },
    { table: "ghsn_account_admin_str_permission", permission: ADMIN_STR_PERMISSION },
    { table: "ghsn_account_kb_permission", permission: KB_PERMISSION },
  ];
  for (const grant of permissionGrants) {
    await client.run(
      `INSERT INTO ${grant.table} (account_uid, permission_uid)
       VALUES (?, ?)
       ON CONFLICT (account_uid, permission_uid) DO NOTHING`,
      [DEMO_ACCOUNT, grant.permission],
    );
  }
}
