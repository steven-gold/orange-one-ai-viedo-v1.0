import { CANONICAL_NAVIGATION_AUTHORITY } from '../db/schema';
import {
  persistGetAssignment,
  persistGetItem,
  persistListAuditEvents,
  persistListItems,
  persistRecordAuditEvent,
} from '../db/persist';
import type { CanonicalNavigationItem, NavigationEvent, PermissionAssignment } from '../domain/types';

/**
 * Persistent runtime facade. Navigation, permission and audit state live in
 * SQLite or Neon; this module never keeps an in-memory Map as authority.
 */
export const runtimeStore = {
  authorityUid: CANONICAL_NAVIGATION_AUTHORITY.authorityUid,
  listItems(): Promise<CanonicalNavigationItem[]> {
    return persistListItems();
  },
  getItem(uid: string): Promise<CanonicalNavigationItem | undefined> {
    return persistGetItem(uid);
  },
  getAssignment(accountUid: string): Promise<PermissionAssignment | undefined> {
    return persistGetAssignment(accountUid);
  },
  listAuditEvents(): Promise<NavigationEvent[]> {
    return persistListAuditEvents();
  },
  recordAuditEvent(event: NavigationEvent): Promise<NavigationEvent> {
    return persistRecordAuditEvent(event);
  },
};
