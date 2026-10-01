-- ACPOS Global Home / Shell / Adaptive Navigation — initial schema (DATABASE_MIGRATION).
-- Canonical navigation authority is the sole source of navigation identity.

CREATE TABLE IF NOT EXISTS navigation_authority (
  navigation_uid TEXT PRIMARY KEY,
  area TEXT NOT NULL CHECK (area IN ('FRONT', 'ADMIN')),
  label_key TEXT NOT NULL,
  route TEXT NOT NULL,
  display_order INTEGER NOT NULL,
  icon TEXT NOT NULL,
  aria_label_key TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_permission_assignment (
  account_uid TEXT NOT NULL,
  navigation_uid TEXT NOT NULL,
  PRIMARY KEY (account_uid, navigation_uid),
  FOREIGN KEY (navigation_uid) REFERENCES navigation_authority (navigation_uid)
);

CREATE TABLE IF NOT EXISTS navigation_audit_event (
  event_uid TEXT PRIMARY KEY,
  account_uid TEXT NOT NULL,
  area TEXT NOT NULL,
  navigation_uid TEXT NOT NULL,
  route TEXT NOT NULL,
  occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_navigation_authority_area
  ON navigation_authority (area, display_order);
