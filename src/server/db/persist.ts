import { DASHBOARD_CHAIN, DASHBOARD_PAGE_UID, DASHBOARD_PERMISSION, DASHBOARD_PROJECTION, DASHBOARD_ROUTE } from "../domain/dashboard";
import {
  CORE_CHAIN,
  CORE_CONTROL_ACTIONS,
  CORE_PAGE_UID,
  CORE_PERMISSION,
  CORE_PROJECTION,
  CORE_ROUTE,
  CORE_VISIBLE_CONTROLS,
} from "../domain/core";
import {
  ASSET_CHAIN,
  ASSET_CONTROL_ACTIONS,
  ASSET_PAGE_UID,
  ASSET_PERMISSION,
  ASSET_PROJECTION,
  ASSET_ROUTE,
  ASSET_VISIBLE_CONTROLS,
} from "../domain/asset";
import {
  VIDEO_CHAIN,
  VIDEO_CONTROL_ACTIONS,
  VIDEO_PAGE_UID,
  VIDEO_PERMISSION,
  VIDEO_PROJECTION,
  VIDEO_ROUTE,
  VIDEO_VISIBLE_CONTROLS,
} from "../domain/video";
import {
  EDIT_CHAIN,
  EDIT_CONTROL_ACTIONS,
  EDIT_PAGE_UID,
  EDIT_PERMISSION,
  EDIT_PROJECTION,
  EDIT_ROUTE,
  EDIT_VISIBLE_CONTROLS,
} from "../domain/edit";
import {
  QA_CHAIN,
  QA_CONTROL_ACTIONS,
  QA_PAGE_UID,
  QA_PERMISSION,
  QA_PROJECTION,
  QA_ROUTE,
  QA_VISIBLE_CONTROLS,
} from "../domain/qa";
import {
  DB_CHAIN,
  DB_CONTROL_ACTIONS,
  DB_PAGE_UID,
  DB_PERMISSION,
  DB_PROJECTION,
  DB_ROUTE,
  DB_VISIBLE_CONTROLS,
} from "../domain/db";
import {
  STR_CHAIN,
  STR_CONTROL_ACTIONS,
  STR_PAGE_UID,
  STR_PERMISSION,
  STR_PROJECTION,
  STR_ROUTE,
  STR_VISIBLE_CONTROLS,
} from "../domain/str";
import {
  INFO_CHAIN,
  INFO_CONTROL_ACTIONS,
  INFO_PAGE_UID,
  INFO_PERMISSION,
  INFO_PROJECTION,
  INFO_ROUTE,
  INFO_VISIBLE_CONTROLS,
} from "../domain/info";
import {
  SYS_CHAIN,
  SYS_CONTROL_ACTIONS,
  SYS_PAGE_UID,
  SYS_PERMISSION,
  SYS_PROJECTION,
  SYS_ROUTE,
  SYS_VISIBLE_CONTROLS,
} from "../domain/sys";
import {
  IAM_CHAIN,
  IAM_CONTROL_ACTIONS,
  IAM_PAGE_UID,
  IAM_PERMISSION,
  IAM_PROJECTION,
  IAM_ROUTE,
  IAM_VISIBLE_CONTROLS,
} from "../domain/iam";
import {
  DEV_CHAIN,
  DEV_CONTROL_ACTIONS,
  DEV_PAGE_UID,
  DEV_PERMISSION,
  DEV_PROJECTION,
  DEV_ROUTE,
  DEV_VISIBLE_CONTROLS,
} from "../domain/dev";
import { getSqlClient } from "./client";
import type {
  AssetFieldValue,
  AssetReadModel,
  CanonicalNavigationItem,
  CoreFieldValue,
  CoreReadModel,
  DashboardReadModel,
  DashboardSectionValue,
  DbFieldValue,
  DbReadModel,
  EditFieldValue,
  EditReadModel,
  NavigationEvent,
  PermissionAssignment,
  QaFieldValue,
  QaReadModel,
  InfoFieldValue,
  InfoReadModel,
  StrFieldValue,
  StrReadModel,
  SysFieldValue,
  SysReadModel,
  IamFieldValue,
  IamReadModel,
  DevFieldValue,
  DevReadModel,
  VideoFieldValue,
  VideoReadModel,
} from "../domain/types";

interface AuthorityRow {
  navigation_uid: string;
  area: "FRONT" | "ADMIN";
  label_key: string;
  route: string;
  display_order: number;
  icon: string;
  aria_label_key: string;
}

interface AssignmentRow {
  navigation_uid: string;
}

interface AuditRow {
  event_uid: string;
  account_uid: string;
  area: "FRONT" | "ADMIN";
  navigation_uid: string;
  route: string;
  occurred_at: string;
}

interface SessionRow {
  session_uid: string;
  account_uid: string;
}

function toItem(row: AuthorityRow): CanonicalNavigationItem {
  return {
    uid: row.navigation_uid,
    area: row.area,
    labelKey: row.label_key,
    route: row.route,
    order: Number(row.display_order),
    icon: row.icon,
    ariaLabelKey: row.aria_label_key,
  };
}

export async function persistListItems(): Promise<CanonicalNavigationItem[]> {
  const rows = await getSqlClient().all<AuthorityRow>(
    "SELECT navigation_uid, area, label_key, route, display_order, icon, aria_label_key FROM ghsn_navigation_authority ORDER BY area, display_order",
  );
  return rows.map(toItem);
}

export async function persistGetItem(uid: string): Promise<CanonicalNavigationItem | undefined> {
  const rows = await getSqlClient().all<AuthorityRow>(
    "SELECT navigation_uid, area, label_key, route, display_order, icon, aria_label_key FROM ghsn_navigation_authority WHERE navigation_uid = ?",
    [uid],
  );
  return rows[0] ? toItem(rows[0]) : undefined;
}

export async function persistGetAssignment(accountUid: string): Promise<PermissionAssignment | undefined> {
  const rows = await getSqlClient().all<AssignmentRow>(
    "SELECT navigation_uid FROM ghsn_account_permission_assignment WHERE account_uid = ?",
    [accountUid],
  );
  if (rows.length === 0) return undefined;
  return {
    accountUid,
    grantedNavigationUids: rows.map((row) => row.navigation_uid),
  };
}

export async function persistRecordAuditEvent(event: NavigationEvent): Promise<NavigationEvent> {
  await getSqlClient().run(
    `INSERT INTO ghsn_navigation_audit_event (event_uid, account_uid, area, navigation_uid, route, occurred_at)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [event.eventUid, event.accountUid, event.area, event.itemUid, event.route, event.occurredAt],
  );
  return event;
}

export async function persistFindSession(sessionUid: string): Promise<SessionRow | undefined> {
  const rows = await getSqlClient().all<SessionRow>(
    "SELECT session_uid, account_uid FROM ghsn_account_session WHERE session_uid = ?",
    [sessionUid],
  );
  return rows[0];
}

interface DashboardSectionRow {
  section_uid: string;
  control_uid: string;
  value_text: string | null;
  detail_text: string;
}

export async function persistHasDashboardPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_dashboard_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, DASHBOARD_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListDashboardSections(): Promise<DashboardSectionValue[]> {
  const rows = await getSqlClient().all<DashboardSectionRow>(
    "SELECT section_uid, control_uid, value_text, detail_text FROM ghsn_dashboard_section_projection",
  );
  return rows.map((row) => ({
    sectionUid: row.section_uid,
    controlUid: row.control_uid,
    value: row.value_text === "" ? null : row.value_text,
    detail: row.detail_text,
  }));
}

export async function persistGetDashboardReadModel(accountUid: string): Promise<DashboardReadModel> {
  const authorized = await persistHasDashboardPermission(accountUid);
  const sections = authorized ? await persistListDashboardSections() : [];
  return {
    projectionUid: DASHBOARD_PROJECTION,
    pageUid: DASHBOARD_PAGE_UID,
    route: DASHBOARD_ROUTE,
    permission: DASHBOARD_PERMISSION,
    chainUid: DASHBOARD_CHAIN,
    authorized,
    sections,
  };
}

export async function persistRecordSectionOpen(
  accountUid: string,
  sectionUid: string,
  controlUid: string,
): Promise<string> {
  const eventUid = `EVT-SECTION-OPEN-${Date.now()}-${sectionUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_dashboard_audit_event (event_uid, account_uid, section_uid, control_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, sectionUid, controlUid, new Date().toISOString()],
  );
  return eventUid;
}

interface CoreFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasCorePermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_core_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, CORE_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListCoreFields(): Promise<CoreFieldValue[]> {
  const rows = await getSqlClient().all<CoreFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_core_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return CORE_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetCoreReadModel(accountUid: string): Promise<CoreReadModel> {
  const authorized = await persistHasCorePermission(accountUid);
  const fields = authorized ? await persistListCoreFields() : [];
  const pageModeRow = fields.find((row) => row.controlUid === "CORE-01-FLD-PAGE-MODE");
  const pageMode =
    pageModeRow?.value === "TOPIC_PRODUCTION" || pageModeRow?.value === "PROJECT_CORE" ? pageModeRow.value : null;
  return {
    projectionUid: CORE_PROJECTION,
    pageUid: CORE_PAGE_UID,
    route: CORE_ROUTE,
    permission: CORE_PERMISSION,
    chainUid: CORE_CHAIN,
    authorized,
    pageMode,
    fields,
  };
}

export function knownCoreAction(controlUid: string, actionUid: string): boolean {
  return CORE_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordCoreAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_core_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface AssetFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasAssetPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_asset_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, ASSET_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListAssetFields(): Promise<AssetFieldValue[]> {
  const rows = await getSqlClient().all<AssetFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_asset_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return ASSET_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetAssetReadModel(accountUid: string): Promise<AssetReadModel> {
  const authorized = await persistHasAssetPermission(accountUid);
  const fields = authorized ? await persistListAssetFields() : [];
  return {
    projectionUid: ASSET_PROJECTION,
    pageUid: ASSET_PAGE_UID,
    route: ASSET_ROUTE,
    permission: ASSET_PERMISSION,
    chainUid: ASSET_CHAIN,
    authorized,
    fields,
  };
}

export function knownAssetAction(controlUid: string, actionUid: string): boolean {
  return ASSET_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordAssetAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_asset_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface VideoFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasVideoPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_video_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, VIDEO_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListVideoFields(): Promise<VideoFieldValue[]> {
  const rows = await getSqlClient().all<VideoFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_video_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return VIDEO_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetVideoReadModel(accountUid: string): Promise<VideoReadModel> {
  const authorized = await persistHasVideoPermission(accountUid);
  const fields = authorized ? await persistListVideoFields() : [];
  return {
    projectionUid: VIDEO_PROJECTION,
    pageUid: VIDEO_PAGE_UID,
    route: VIDEO_ROUTE,
    permission: VIDEO_PERMISSION,
    chainUid: VIDEO_CHAIN,
    authorized,
    fields,
  };
}

export function knownVideoAction(controlUid: string, actionUid: string): boolean {
  return VIDEO_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordVideoAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_video_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface EditFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasEditPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_edit_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, EDIT_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListEditFields(): Promise<EditFieldValue[]> {
  const rows = await getSqlClient().all<EditFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_edit_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return EDIT_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetEditReadModel(accountUid: string): Promise<EditReadModel> {
  const authorized = await persistHasEditPermission(accountUid);
  const fields = authorized ? await persistListEditFields() : [];
  return {
    projectionUid: EDIT_PROJECTION,
    pageUid: EDIT_PAGE_UID,
    route: EDIT_ROUTE,
    permission: EDIT_PERMISSION,
    chainUid: EDIT_CHAIN,
    authorized,
    fields,
  };
}

export function knownEditAction(controlUid: string, actionUid: string): boolean {
  return EDIT_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordEditAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_edit_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface QaFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasQaPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_qa_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, QA_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListQaFields(): Promise<QaFieldValue[]> {
  const rows = await getSqlClient().all<QaFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_qa_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return QA_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetQaReadModel(accountUid: string): Promise<QaReadModel> {
  const authorized = await persistHasQaPermission(accountUid);
  const fields = authorized ? await persistListQaFields() : [];
  return {
    projectionUid: QA_PROJECTION,
    pageUid: QA_PAGE_UID,
    route: QA_ROUTE,
    permission: QA_PERMISSION,
    chainUid: QA_CHAIN,
    authorized,
    fields,
  };
}

export function knownQaAction(controlUid: string, actionUid: string): boolean {
  return QA_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordQaAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_qa_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface DbFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasDbPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_db_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, DB_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListDbFields(): Promise<DbFieldValue[]> {
  const rows = await getSqlClient().all<DbFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_db_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return DB_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetDbReadModel(accountUid: string): Promise<DbReadModel> {
  const authorized = await persistHasDbPermission(accountUid);
  const fields = authorized ? await persistListDbFields() : [];
  return {
    projectionUid: DB_PROJECTION,
    pageUid: DB_PAGE_UID,
    route: DB_ROUTE,
    permission: DB_PERMISSION,
    chainUid: DB_CHAIN,
    authorized,
    fields,
  };
}

export function knownDbAction(controlUid: string, actionUid: string): boolean {
  return DB_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordDbAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_db_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface StrFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasStrPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_str_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, STR_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListStrFields(): Promise<StrFieldValue[]> {
  const rows = await getSqlClient().all<StrFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_str_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return STR_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetStrReadModel(accountUid: string): Promise<StrReadModel> {
  const authorized = await persistHasStrPermission(accountUid);
  const fields = authorized ? await persistListStrFields() : [];
  return {
    projectionUid: STR_PROJECTION,
    pageUid: STR_PAGE_UID,
    route: STR_ROUTE,
    permission: STR_PERMISSION,
    chainUid: STR_CHAIN,
    authorized,
    fields,
  };
}

export function knownStrAction(controlUid: string, actionUid: string): boolean {
  return STR_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordStrAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_str_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface InfoFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasInfoPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_info_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, INFO_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListInfoFields(): Promise<InfoFieldValue[]> {
  const rows = await getSqlClient().all<InfoFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_info_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return INFO_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetInfoReadModel(accountUid: string): Promise<InfoReadModel> {
  const authorized = await persistHasInfoPermission(accountUid);
  const fields = authorized ? await persistListInfoFields() : [];
  return {
    projectionUid: INFO_PROJECTION,
    pageUid: INFO_PAGE_UID,
    route: INFO_ROUTE,
    permission: INFO_PERMISSION,
    chainUid: INFO_CHAIN,
    authorized,
    fields,
  };
}

export function knownInfoAction(controlUid: string, actionUid: string): boolean {
  return INFO_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordInfoAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_info_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface SysFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasSysPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_sys_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, SYS_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListSysFields(): Promise<SysFieldValue[]> {
  const rows = await getSqlClient().all<SysFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_sys_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return SYS_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetSysReadModel(accountUid: string): Promise<SysReadModel> {
  const authorized = await persistHasSysPermission(accountUid);
  const fields = authorized ? await persistListSysFields() : [];
  return {
    projectionUid: SYS_PROJECTION,
    pageUid: SYS_PAGE_UID,
    route: SYS_ROUTE,
    permission: SYS_PERMISSION,
    chainUid: SYS_CHAIN,
    authorized,
    fields,
  };
}

export function knownSysAction(controlUid: string, actionUid: string): boolean {
  return SYS_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordSysAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_sys_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface IamFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasIamPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_iam_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, IAM_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListIamFields(): Promise<IamFieldValue[]> {
  const rows = await getSqlClient().all<IamFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_iam_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return IAM_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetIamReadModel(accountUid: string): Promise<IamReadModel> {
  const authorized = await persistHasIamPermission(accountUid);
  const fields = authorized ? await persistListIamFields() : [];
  return {
    projectionUid: IAM_PROJECTION,
    pageUid: IAM_PAGE_UID,
    route: IAM_ROUTE,
    permission: IAM_PERMISSION,
    chainUid: IAM_CHAIN,
    authorized,
    fields,
  };
}

export function knownIamAction(controlUid: string, actionUid: string): boolean {
  return IAM_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordIamAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_iam_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface DevFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasDevPermission(accountUid: string): Promise<boolean> {
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_dev_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, DEV_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListDevFields(): Promise<DevFieldValue[]> {
  const rows = await getSqlClient().all<DevFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_dev_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return DEV_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetDevReadModel(accountUid: string): Promise<DevReadModel> {
  const authorized = await persistHasDevPermission(accountUid);
  const fields = authorized ? await persistListDevFields() : [];
  return {
    projectionUid: DEV_PROJECTION,
    pageUid: DEV_PAGE_UID,
    route: DEV_ROUTE,
    permission: DEV_PERMISSION,
    chainUid: DEV_CHAIN,
    authorized,
    fields,
  };
}

export function knownDevAction(controlUid: string, actionUid: string): boolean {
  return DEV_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordDevAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_dev_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}
