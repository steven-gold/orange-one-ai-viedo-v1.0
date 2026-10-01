export type NavigationArea = 'FRONT' | 'ADMIN';

export interface CanonicalNavigationItem {
  uid: string;
  area: NavigationArea;
  labelKey: string;
  route: string;
  order: number;
  icon: string;
  ariaLabelKey: string;
}

export interface NavigationAuthority {
  authorityUid: string;
  items: CanonicalNavigationItem[];
}

export interface PermissionAssignment {
  accountUid: string;
  grantedNavigationUids: string[];
}

export interface ResolvedNavigationItem extends CanonicalNavigationItem {
  active: boolean;
}

export interface NavigationResolutionError {
  code: 'NAVIGATION_TARGET_UNRESOLVABLE' | 'NAVIGATION_AUTHORITY_UNAVAILABLE';
  message: string;
}

export interface NavigationContextResponse {
  area: NavigationArea;
  authorityUid: string;
  items: ResolvedNavigationItem[];
  resolved: boolean;
  error: NavigationResolutionError | null;
}

/** Visibility is the intersection of the canonical authority and the account assignment. */
export function resolveVisibleItems(
  authority: NavigationAuthority,
  assignment: PermissionAssignment,
  area: NavigationArea,
): CanonicalNavigationItem[] {
  const granted = new Set(assignment.grantedNavigationUids);
  return authority.items
    .filter((item) => item.area === area && granted.has(item.uid))
    .sort((a, b) => a.order - b.order);
}

/** Front active item is decided by canonical page ancestry, never by URL string guessing. */
export function resolveFrontActiveUid(
  items: CanonicalNavigationItem[],
  pageAncestry: string[],
): string | null {
  const ancestry = new Set(pageAncestry);
  for (const item of items) {
    if (ancestry.has(item.uid)) return item.uid;
  }
  const match = items.find((item) => pageAncestry.some((seg) => item.route === `/${seg}`));
  return match ? match.uid : null;
}

/** Admin active item is decided by the exact admin page UID. */
export function resolveAdminActiveUid(
  items: CanonicalNavigationItem[],
  activePageUid: string | null,
): string | null {
  if (!activePageUid) return null;
  return items.some((item) => item.uid === activePageUid) ? activePageUid : null;
}

export function isNavigationTargetResolvable(item: CanonicalNavigationItem): boolean {
  return typeof item.route === 'string' && item.route.startsWith('/');
}
