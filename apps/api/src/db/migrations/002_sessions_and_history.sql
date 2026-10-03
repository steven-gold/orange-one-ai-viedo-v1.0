CREATE TABLE IF NOT EXISTS schema_migration_history (
  filename TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL,
  checksum TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_session (
  session_uid TEXT PRIMARY KEY,
  account_uid TEXT NOT NULL,
  issued_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_account_session_account
  ON account_session (account_uid);
