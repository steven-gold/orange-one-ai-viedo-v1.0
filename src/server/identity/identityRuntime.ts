import { createHash, randomBytes, scrypt, timingSafeEqual } from "node:crypto";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";

function scryptAsync(
  password: string,
  salt: Buffer,
  keylen: number,
  options: { N: number; r: number; p: number },
): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    scrypt(password, salt, keylen, options, (error, derived) => {
      if (error) reject(error);
      else resolve(derived as Buffer);
    });
  });
}

export const IDENTITY_COOKIE_NAME = "acpos_session";
export const OPEN_LOGIN_PATH = "/login";
export const IDENTITY_SESSION_PATH = "/v1/identity/session";
export const SESSION_TTL_SECONDS = 43_200;
export const SCRYPT_N = 16_384;
export const SCRYPT_R = 8;
export const SCRYPT_P = 1;
export const SCRYPT_KEYLEN = 32;

export type IdentityActor = {
  user_id: string;
  runtime_account_id: string;
  email: string;
  display_name: string;
  external_subject: string;
};

type IdentityFailure = { ok: false; status: number; reason_code: string };
type IdentitySuccess<T> = { ok: true } & T;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function asText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function tokenHash(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

export function hashSessionToken(token: string): string {
  return tokenHash(token);
}

export async function hashPassword(password: string): Promise<string> {
  const salt = randomBytes(16);
  const derived = (await scryptAsync(password, salt, SCRYPT_KEYLEN, {
    N: SCRYPT_N,
    r: SCRYPT_R,
    p: SCRYPT_P,
  })) as Buffer;
  return `scrypt$${SCRYPT_N}$${SCRYPT_R}$${SCRYPT_P}$${salt.toString("base64url")}$${derived.toString("base64url")}`;
}

export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  const parts = stored.split("$");
  if (parts.length !== 6 || parts[0] !== "scrypt") return false;
  const n = Number(parts[1]);
  const r = Number(parts[2]);
  const p = Number(parts[3]);
  if (![n, r, p].every((value) => Number.isSafeInteger(value) && value > 0)) return false;
  let salt: Buffer;
  let expected: Buffer;
  try {
    salt = Buffer.from(parts[4], "base64url");
    expected = Buffer.from(parts[5], "base64url");
  } catch {
    return false;
  }
  if (!salt.length || expected.length !== SCRYPT_KEYLEN) return false;
  const derived = (await scryptAsync(password, salt, SCRYPT_KEYLEN, { N: n, r, p })) as Buffer;
  if (derived.length !== expected.length) return false;
  return timingSafeEqual(derived, expected);
}

let dummyHashPromise: Promise<string> | null = null;
function dummyPasswordHash(): Promise<string> {
  dummyHashPromise ??= hashPassword("acpos-internal-dummy-not-a-credential");
  return dummyHashPromise;
}

function actorFromRow(row: Record<string, unknown>): IdentityActor | null {
  const user_id = asText(row.user_id);
  const runtime_account_id = asText(row.runtime_account_id);
  const email = asText(row.email);
  const display_name = asText(row.display_name);
  const external_subject = asText(row.external_subject);
  if (!user_id || !runtime_account_id || !email || !display_name || !external_subject) return null;
  return { user_id, runtime_account_id, email, display_name, external_subject };
}

export async function resolveIdentityFromCookie(
  cookieValue: string | undefined,
): Promise<IdentitySuccess<{ actor: IdentityActor }> | IdentityFailure> {
  const token = cookieValue?.trim() ?? "";
  if (!token) return { ok: false, status: 401, reason_code: "IDENTITY_RUNTIME_NOT_BOUND" };
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) return { ok: false, status: 503, reason_code: "DATABASE_RUNTIME_NOT_BOUND" };
  const hash = tokenHash(token);
  try {
    const rows = await sql`
      SELECT u.user_id::text AS user_id,
             a.id AS runtime_account_id,
             u.email::text AS email,
             u.display_name,
             u.external_subject
      FROM acpos_runtime.sessions s
      JOIN acpos_runtime.accounts a ON a.id = s.account_id
      JOIN app_users u ON lower(u.email::text) = lower(a.email)
      WHERE s.token_hash = ${hash}
        AND s.expires_at > now()
        AND u.disabled_at IS NULL
        AND a.status = 'READY'
      LIMIT 1
    `;
    const row = Array.isArray(rows) ? asRecord(rows[0]) : null;
    const actor = row ? actorFromRow(row) : null;
    if (!actor) return { ok: false, status: 401, reason_code: "IDENTITY_RUNTIME_NOT_BOUND" };
    return { ok: true, actor };
  } catch {
    return { ok: false, status: 503, reason_code: "IDENTITY_LOOKUP_FAILED" };
  }
}

export async function createIdentitySession(
  emailInput: string,
  password: string,
): Promise<IdentitySuccess<{ token: string; actor: IdentityActor }> | IdentityFailure> {
  const email = emailInput.trim();
  if (!email || !password) return { ok: false, status: 400, reason_code: "IDENTITY_CREDENTIALS_REJECTED" };
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) return { ok: false, status: 503, reason_code: "DATABASE_RUNTIME_NOT_BOUND" };
  try {
    const rows = await sql`
      SELECT id, email, password_hash, status
      FROM acpos_runtime.accounts
      WHERE lower(email) = lower(${email})
      LIMIT 1
    `;
    const row = Array.isArray(rows) ? asRecord(rows[0]) : null;
    const passwordHash = row ? asText(row.password_hash) : "";
    const verified = await verifyPassword(password, passwordHash || (await dummyPasswordHash()));
    if (!row || !verified || asText(row.status) !== "READY") {
      return { ok: false, status: 401, reason_code: "IDENTITY_CREDENTIALS_REJECTED" };
    }
    const accountId = asText(row.id);
    const token = randomBytes(32).toString("base64url");
    const hash = tokenHash(token);
    const expiresAt = new Date(Date.now() + SESSION_TTL_SECONDS * 1000).toISOString();
    await sql`
      INSERT INTO acpos_runtime.sessions (token_hash, account_id, expires_at)
      VALUES (${hash}, ${accountId}, ${expiresAt})
    `;
    const resolved = await resolveIdentityFromCookie(token);
    if (!resolved.ok) return { ok: false, status: 403, reason_code: "APP_USERS_EMAIL_JOIN_NOT_FOUND" };
    return { ok: true, token, actor: resolved.actor };
  } catch {
    return { ok: false, status: 503, reason_code: "IDENTITY_SESSION_CREATE_FAILED" };
  }
}

export async function destroyIdentitySession(cookieValue: string | undefined): Promise<void> {
  const token = cookieValue?.trim() ?? "";
  if (!token) return;
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) return;
  const hash = tokenHash(token);
  try {
    await sql`DELETE FROM acpos_runtime.sessions WHERE token_hash = ${hash}`;
  } catch {
    /* logout stays fail-closed */
  }
}
