import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const runtime = readFileSync('src/server/database/neonRuntime.ts', 'utf8');
const manifest = readFileSync('database/migrations/migration_checksum_manifest.yaml', 'utf8');

test('Production Neon runtime accepts the Current 0053 migration head', () => {
  assert.match(runtime, /export const REQUIRED_MIGRATION_COUNT = 20;/);
  assert.match(runtime, /export const MAX_SUPPORTED_MIGRATION_COUNT = 53;/);
  assert.match(runtime, /value >= REQUIRED_MIGRATION_COUNT && value <= MAX_SUPPORTED_MIGRATION_COUNT/);
  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.53/);
  assert.match(manifest, /migration_id: 0053_dev_discovery_permission_closure/);
});
