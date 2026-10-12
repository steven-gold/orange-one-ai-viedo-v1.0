import { createHash, randomBytes, scrypt, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";

const scryptAsync = promisify(scrypt);

export const SCRYPT_N = 16384;
export const SCRYPT_R = 8;
export const SCRYPT_P = 1;
export const SCRYPT_KEYLEN = 32;
export const SESSION_TOKEN_BYTES = 32;

const DUMMY_SALT = Buffer.from("acpos-identity-dummy-salt-v1", "utf8");

export function sha256Hex(value: string | Buffer): string {
  return createHash("sha256").update(value).digest("hex");
}

export function randomToken(): { raw: string; hash: string } {
  const raw = randomBytes(SESSION_TOKEN_BYTES).toString("base64url");
  return { raw, hash: sha256Hex(raw) };
}

export function newSessionUid(): string {
  return `sess-${randomBytes(16).toString("hex")}`;
}

export async function hashPassword(password: string, salt = randomBytes(16)): Promise<string> {
  const derived = (await scryptAsync(password, salt, SCRYPT_KEYLEN)) as Buffer;
  return `scrypt$N=${SCRYPT_N}$r=${SCRYPT_R}$p=${SCRYPT_P}$${salt.toString("base64url")}$${derived.toString("base64url")}`;
}

export async function verifyPassword(password: string, encoded: string): Promise<boolean> {
  const parts = encoded.split("$");
  if (parts.length !== 6 || parts[0] !== "scrypt") return false;
  const salt = Buffer.from(parts[4], "base64url");
  const expected = Buffer.from(parts[5], "base64url");
  const derived = (await scryptAsync(password, salt, SCRYPT_KEYLEN)) as Buffer;
  if (derived.length !== expected.length) return false;
  return timingSafeEqual(derived, expected);
}

export async function dummyPasswordVerify(password: string): Promise<void> {
  await scryptAsync(password, DUMMY_SALT, SCRYPT_KEYLEN);
}
