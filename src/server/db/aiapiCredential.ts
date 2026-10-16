import { getSqlClient } from "./client";

export const AIAPI_ACTIVE_CREDENTIAL_UID = "AIAPI-01-CRED-ACTIVE";

export async function setAiapiCredential(secret: string): Promise<void> {
  const normalized = secret.trim();
  if (!normalized) return;
  await getSqlClient().run(
    `INSERT INTO ghsn_aiapi_credential (credential_uid, secret_text, updated_at)
     VALUES (?, ?, ?)
     ON CONFLICT (credential_uid) DO UPDATE SET secret_text = EXCLUDED.secret_text, updated_at = EXCLUDED.updated_at`,
    [AIAPI_ACTIVE_CREDENTIAL_UID, normalized, new Date().toISOString()],
  );
}

export async function clearAiapiCredential(): Promise<void> {
  await getSqlClient().run(
    "UPDATE ghsn_aiapi_credential SET secret_text = '', updated_at = ? WHERE credential_uid = ?",
    [new Date().toISOString(), AIAPI_ACTIVE_CREDENTIAL_UID],
  );
}

export async function getAiapiCredential(): Promise<string | null> {
  const rows = await getSqlClient().all<{ secret_text: string | null }>(
    "SELECT secret_text FROM ghsn_aiapi_credential WHERE credential_uid = ?",
    [AIAPI_ACTIVE_CREDENTIAL_UID],
  );
  const value = (rows[0]?.secret_text ?? "").trim();
  return value ? value : null;
}
