import type { Request } from 'express';

export interface AuthenticatedPrincipal {
  accountUid: string;
  sessionUid: string;
  authenticated: boolean;
}

const SESSION_PATTERN = /^sess-[a-z0-9-]{6,}$/i;

/**
 * Authentication decides identity only. It never decides navigation
 * visibility, which is a separate authorization concern.
 */
export function authenticate(req: Request): AuthenticatedPrincipal {
  const session = req.header('x-session-uid') ?? '';
  const accountUid = req.header('x-account-uid') ?? '';
  const authenticated = SESSION_PATTERN.test(session) && accountUid.length > 0;
  return { accountUid, sessionUid: session, authenticated };
}
