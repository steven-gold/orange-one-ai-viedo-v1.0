import { CANONICAL_NAVIGATION_AUTHORITY } from '../db/schema';
import type { CanonicalNavigationItem, NavigationEvent, PermissionAssignment } from '../domain/types';

const items = new Map<string, CanonicalNavigationItem>(
  CANONICAL_NAVIGATION_AUTHORITY.items.map((entry) => [entry.uid, entry]),
);

const assignments = new Map<string, PermissionAssignment>([
  [
    'ACC-DEMO',
    {
      accountUid: 'ACC-DEMO',
      grantedNavigationUids: CANONICAL_NAVIGATION_AUTHORITY.items.map((entry) => entry.uid),
    },
  ],
  ['ACC-LIMITED', { accountUid: 'ACC-LIMITED', grantedNavigationUids: ['FRONT-01', 'FRONT-02'] }],
]);

const auditEvents: NavigationEvent[] = [];

export const runtimeStore = {
  authorityUid: CANONICAL_NAVIGATION_AUTHORITY.authorityUid,
  listItems(): CanonicalNavigationItem[] {
    return [...items.values()];
  },
  getItem(uid: string): CanonicalNavigationItem | undefined {
    return items.get(uid);
  },
  getAssignment(accountUid: string): PermissionAssignment | undefined {
    return assignments.get(accountUid);
  },
  listAuditEvents(): NavigationEvent[] {
    return [...auditEvents];
  },
  recordAuditEvent(event: NavigationEvent): NavigationEvent {
    auditEvents.push(event);
    return event;
  },
};
