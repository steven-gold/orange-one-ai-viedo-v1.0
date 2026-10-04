import { DASHBOARD_CHAIN, DASHBOARD_PAGE_UID, DASHBOARD_PERMISSION, DASHBOARD_PROJECTION, DASHBOARD_ROUTE } from "../domain/dashboard";
import { getSqlClient } from "./client";
import type { CanonicalNavigationItem, DashboardReadModel, DashboardSectionValue, NavigationEvent, PermissionAssignment } from "../domain/types";

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
