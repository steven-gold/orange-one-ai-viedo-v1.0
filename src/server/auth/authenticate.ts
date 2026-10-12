import { persistFindSession } from "../db/persist";
import { readIdentitySession } from "../identity/login";
import { parseSessionCookie } from "../identity/sessionCookie";

export interface AuthenticatedPrincipal {
  accountUid: string;
  sessionUid: string;
  authenticated: boolean;
}

const SESSION_PATTERN = /^sess-[a-z0-9-]{6,}$/i;

export async function authenticate(headers: Headers): Promise<AuthenticatedPrincipal> {
  const cookieToken = parseSessionCookie(headers.get("cookie"));
  if (cookieToken) {
    const identity = await readIdentitySession(cookieToken);
    if (identity) {
      return { accountUid: identity.account_uid, sessionUid: identity.session_uid, authenticated: true };
    }
  }
  const session = headers.get("x-session-uid") ?? "";
  const accountUid = headers.get("x-account-uid") ?? "";
  if (!SESSION_PATTERN.test(session) || accountUid.length === 0) {
    return { accountUid, sessionUid: session, authenticated: false };
  }
  const row = await persistFindSession(session);
  if (!row || row.account_uid !== accountUid) {
    return { accountUid, sessionUid: session, authenticated: false };
  }
  return { accountUid, sessionUid: session, authenticated: true };
}
