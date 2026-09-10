import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const migrationPath = 'database/migrations/0053_dev_discovery_permission_closure.sql';
const manifestPath = 'database/migrations/migration_checksum_manifest.yaml';
const expectedSha = 'e410c52e8a65e31f86554b591d1e9d2d895127d47e30a9402a3558a6eb3f9149';
const discoveryActions = [
  'action:admin:DEV-01:ACT-DISCOVERY-START',
  'action:admin:DEV-01:ACT-DISCOVERY-PAUSE',
  'action:admin:DEV-01:ACT-DISCOVERY-RESUME',
  'action:admin:DEV-01:ACT-DISCOVERY-STOP',
];

test('DEV 0053 grants only the four Current Discovery actions and keeps NAV untouched', () => {
  const sql = readFileSync(migrationPath, 'utf8');
  const marker = 'INSERT INTO public.schema_migration_history';
  const index = sql.indexOf(marker);
  assert.ok(index > 0, 'terminal migration registration missing');
  const actualSha = createHash('sha256').update(sql.slice(0, index)).digest('hex');
  assert.equal(actualSha, expectedSha);

  for (const resource of discoveryActions) assert.match(sql, new RegExp(resource.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  assert.match(sql, /DEV0053_PERMISSION_RESOURCE_COUNT_MISMATCH/);
  assert.match(sql, /DEV0053_APPROVED_ALLOW_COUNT_MISMATCH/);
  assert.match(sql, /ON CONFLICT \(user_id,resource_id,action,version_no\) DO NOTHING/);
  assert.doesNotMatch(sql, /'action:admin:DEV-01:ACT-NAV-OPEN'/);
  assert.match(sql, /'CR-DEV-0053-PENDING-PRODUCTION-APPLY'/);
});

test('migration manifest registers DEV 0053 with the exact payload checksum', () => {
  const manifest = readFileSync(manifestPath, 'utf8');
  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.53/);
  assert.match(manifest, /migration_id: 0053_dev_discovery_permission_closure/);
  assert.match(manifest, new RegExp(`payload_sha256: ${expectedSha}`));
  assert.match(manifest, /approval_ref: CR-DEV-0053-PENDING-PRODUCTION-APPLY/);
});
