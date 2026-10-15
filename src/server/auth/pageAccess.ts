/**
 * Page access policy.
 *
 * A rendered page is a site-wide capability: it is reachable by any
 * authenticated principal, independent of the account. Account-scoped
 * authorization is a separate, later layer (which controls data and effectful
 * operations within a page) and must not be the precondition for reaching or
 * exercising the page itself.
 *
 * Account-scoped page permission enforcement is intentionally deferred. Flip
 * ACCOUNT_PAGE_PERMISSION_ENFORCED to true to re-enable the per-account
 * permission tables without touching any call site.
 */
export const ACCOUNT_PAGE_PERMISSION_ENFORCED = false;

export function pagePermissionEnforced(): boolean {
  return ACCOUNT_PAGE_PERMISSION_ENFORCED;
}
