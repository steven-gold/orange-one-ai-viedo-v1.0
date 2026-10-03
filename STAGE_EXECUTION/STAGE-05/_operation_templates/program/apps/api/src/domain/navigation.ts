import type { CanonicalNavigationItem, PermissionAssignment } from '../domain/types';
import { getAssignment } from '../repositories/permissionRepository';
import { getAuthorityUid, listNavigationItems } from '../repositories/navigationRepository';

export interface ResolvedNavigationItem extends CanonicalNavigationItem {
  active: boolean;
}

export interface NavigationResolution {
  authorityUid: string;
  items: ResolvedNavigationItem[];
}

export type NavigationErrorCode =
  | 'NAVIGATION_TARGET_UNRESOLVABLE'
  | 'NAVIGATION_AUTHORITY_UNAVAILABLE';

export class NavigationResolutionError extends Error {
  readonly code: NavigationErrorCode;

  constructor(code: NavigationErrorCode, message: string) {
    super(message);
    this.code = code;
    this.name = 'NavigationResolutionError';
  }
}

/**
 * Front/L1 visibility is the intersection of Canonical Navigation Authority
 * and the account's permission assignment. No other rule may widen it.
 */
export async function resolveVisibleNavigation(accountUid: string): Promise<NavigationResolution> {
  const assignment: PermissionAssignment | undefined = await getAssignment(accountUid);
  if (!assignment) {
    throw new NavigationResolutionError(
      'NAVIGATION_TARGET_UNRESOLVABLE',
      `No permission assignment for account ${accountUid}`,
    );
  }
  const granted = new Set(assignment.grantedNavigationUids);
  const items = (await listNavigationItems())
    .filter((entry) => granted.has(entry.uid))
    .map((entry) => ({ ...entry, active: false }));
  if (items.length === 0) {
    throw new NavigationResolutionError(
      'NAVIGATION_AUTHORITY_UNAVAILABLE',
      `No visible navigation for account ${accountUid}`,
    );
  }
  return { authorityUid: getAuthorityUid(), items };
}

export function resolveFrontActiveUid(
  items: CanonicalNavigationItem[],
  pageAncestry: string[],
): string | null {
  const front = items.filter((entry) => entry.area === 'FRONT');
  for (const ancestor of pageAncestry) {
    const match = front.find((entry) => entry.uid === ancestor);
    if (match) return match.uid;
  }
  return null;
}

export function resolveAdminActiveUid(
  items: CanonicalNavigationItem[],
  activePageUid: string | null,
): string | null {
  if (!activePageUid) return null;
  const match = items.find((entry) => entry.area === 'ADMIN' && entry.uid === activePageUid);
  return match ? match.uid : null;
}
