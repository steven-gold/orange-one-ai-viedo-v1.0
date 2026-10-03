import type { Request } from 'express';
import { persistFindSession } from '../db/persist';

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
export async function authenticate(req: Request): Promise<AuthenticatedPrincipal> {
  const session = req.header('x-session-uid') ?? '';
  const accountUid = req.header('x-account-uid') ?? '';
  if (!SESSION_PATTERN.test(session) || accountUid.length === 0) {
    return { accountUid, sessionUid: session, authenticated: false };
  }
  const row = await persistFindSession(session);
  if (!row || row.account_uid !== accountUid) {
    return { accountUid, sessionUid: session, authenticated: false };
  }
  return { accountUid, sessionUid: session, authenticated: true };
}
