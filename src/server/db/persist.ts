import { getSqlClient } from "./client";
import type { CanonicalNavigationItem, NavigationEvent, PermissionAssignment } from "../domain/types";

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
    "SELECT navigation_uid, area, label_key, route, display_order, icon, aria_label_key FROM navigation_authority ORDER BY area, display_order",
  );
  return rows.map(toItem);
}

export async function persistGetItem(uid: string): Promise<CanonicalNavigationItem | undefined> {
  const rows = await getSqlClient().all<AuthorityRow>(
    "SELECT navigation_uid, area, label_key, route, display_order, icon, aria_label_key FROM navigation_authority WHERE navigation_uid = ?",
    [uid],
  );
  return rows[0] ? toItem(rows[0]) : undefined;
}

export async function persistGetAssignment(accountUid: string): Promise<PermissionAssignment | undefined> {
  const rows = await getSqlClient().all<AssignmentRow>(
    "SELECT navigation_uid FROM account_permission_assignment WHERE account_uid = ?",
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
    `INSERT INTO navigation_audit_event (event_uid, account_uid, area, navigation_uid, route, occurred_at)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [event.eventUid, event.accountUid, event.area, event.itemUid, event.route, event.occurredAt],
  );
  return event;
}

export async function persistFindSession(sessionUid: string): Promise<SessionRow | undefined> {
  const rows = await getSqlClient().all<SessionRow>(
    "SELECT session_uid, account_uid FROM account_session WHERE session_uid = ?",
    [sessionUid],
  );
  return rows[0];
}
