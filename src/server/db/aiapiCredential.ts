import { getSqlClient } from "./client";

export const AIAPI_ACTIVE_CREDENTIAL_UID = "AIAPI-01-CRED-ACTIVE";

function credentialKey(profileId: string): string {
  return profileId.trim();
}

export async function setAiapiCredential(profileId: string, secret: string): Promise<void> {
  const key = credentialKey(profileId);
  const normalized = secret.trim();
  if (!key || !normalized) return;
  await getSqlClient().run(
    `INSERT INTO ghsn_aiapi_credential (credential_uid, secret_text, updated_at)
     VALUES (?, ?, ?)
     ON CONFLICT (credential_uid) DO UPDATE SET secret_text = EXCLUDED.secret_text, updated_at = EXCLUDED.updated_at`,
    [key, normalized, new Date().toISOString()],
  );
}

export async function clearAiapiCredential(profileId: string): Promise<void> {
  const key = credentialKey(profileId);
  if (!key) return;
  await getSqlClient().run(
    "UPDATE ghsn_aiapi_credential SET secret_text = '', updated_at = ? WHERE credential_uid = ?",
    [new Date().toISOString(), key],
  );
}

export async function getAiapiCredential(profileId: string): Promise<string | null> {
  const key = credentialKey(profileId);
  if (!key) return null;
  const rows = await getSqlClient().all<{ secret_text: string | null }>(
    "SELECT secret_text FROM ghsn_aiapi_credential WHERE credential_uid = ?",
    [key],
  );
  const value = (rows[0]?.secret_text ?? "").trim();
  return value ? value : null;
}
