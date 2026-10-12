import { SESSION_MAX_AGE_SECONDS } from "./sessionCookie";
import { dummyPasswordVerify, newSessionUid, randomToken, sha256Hex, verifyPassword } from "./crypto";
import { bootstrapDatabase } from "../db/migrate";
import {
  persistCreateIdentitySession,
  persistFindAppUserByEmail,
  persistFindIdentitySessionByTokenHash,
  persistFindRuntimeAccountByEmail,
  persistDeleteIdentitySession,
} from "../db/persist";
import type { LoginReasonCode } from "../domain/identity";

export type LoginSuccess = {
  ok: true;
  sessionUid: string;
  accountUid: string;
  token: string;
};

export type LoginFailure = {
  ok: false;
  reason: LoginReasonCode;
};

export async function establishIdentity(emailRaw: string, password: string): Promise<LoginSuccess | LoginFailure> {
  try {
    await bootstrapDatabase();
  } catch {
    return { ok: false, reason: "DATABASE_RUNTIME_NOT_BOUND" };
  }
  const email = emailRaw.trim();
  if (!email || !password) {
    await dummyPasswordVerify(password || " ");
    return { ok: false, reason: "IDENTITY_CREDENTIALS_REJECTED" };
  }
  const account = await persistFindRuntimeAccountByEmail(email);
  if (!account || account.status !== "READY" || account.disabled_at) {
    await dummyPasswordVerify(password);
    return { ok: false, reason: "IDENTITY_CREDENTIALS_REJECTED" };
  }
  const passwordOk = await verifyPassword(password, account.password_hash);
  if (!passwordOk) {
    return { ok: false, reason: "IDENTITY_CREDENTIALS_REJECTED" };
  }
  const appUser = await persistFindAppUserByEmail(email);
  if (!appUser || appUser.disabled_at || appUser.account_uid !== account.account_uid) {
    return { ok: false, reason: "APP_USERS_EMAIL_JOIN_NOT_FOUND" };
  }
  const token = randomToken();
  const sessionUid = newSessionUid();
  const issuedAt = new Date();
  const expiresAt = new Date(issuedAt.getTime() + SESSION_MAX_AGE_SECONDS * 1000);
  try {
    await persistCreateIdentitySession({
      session_uid: sessionUid,
      account_uid: account.account_uid,
      token_hash: token.hash,
      expires_at: expiresAt.toISOString(),
      issued_at: issuedAt.toISOString(),
    });
  } catch {
    return { ok: false, reason: "IDENTITY_SESSION_CREATE_FAILED" };
  }
  return { ok: true, sessionUid, accountUid: account.account_uid, token: token.raw };
}

export async function readIdentitySession(token: string) {
  if (!token) return null;
  try {
    await bootstrapDatabase();
  } catch {
    return null;
  }
  const row = await persistFindIdentitySessionByTokenHash(sha256Hex(token));
  if (!row) return null;
  if (new Date(row.expires_at).getTime() <= Date.now()) {
    await persistDeleteIdentitySession(row.session_uid);
    return null;
  }
  return row;
}

export async function endIdentitySession(token: string): Promise<void> {
  const row = await readIdentitySession(token);
  if (!row) return;
  await persistDeleteIdentitySession(row.session_uid);
}
