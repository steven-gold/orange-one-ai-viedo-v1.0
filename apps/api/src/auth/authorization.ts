import type { CanonicalNavigationItem } from '../domain/types';

export interface AuthorizationDecision {
  allowed: boolean;
  reason: string;
}

/**
 * Server-side authority check: an account may act on an item only when the
 * item appears in its resolved visible set. The UI never widens authority.
 */
export function authorizeNavigationAction(
  item: CanonicalNavigationItem,
  visibleUids: Iterable<string>,
): AuthorizationDecision {
  const granted = visibleUids instanceof Set ? visibleUids : new Set(visibleUids);
  if (!granted.has(item.uid)) {
    return { allowed: false, reason: 'NAVIGATION_TARGET_UNRESOLVABLE' };
  }
  return { allowed: true, reason: 'AUTHORIZED' };
}
