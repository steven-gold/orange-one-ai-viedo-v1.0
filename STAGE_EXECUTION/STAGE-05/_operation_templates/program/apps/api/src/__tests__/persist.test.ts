import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { bootstrapDatabase } from '../db/bootstrap';
import { closeSqlClient } from '../db/client';
import { persistGetAssignment, persistListItems, persistRecordAuditEvent } from '../db/persist';
import { backupToFile, restoreFromFile } from '../ops/backup';

beforeEach(async () => {
  await bootstrapDatabase(':memory:');
});

afterEach(async () => {
  await closeSqlClient();
});

describe('persistent navigation runtime', () => {
  it('loads canonical authority and permission rows from sqlite', async () => {
    const items = await persistListItems();
    expect(items).toHaveLength(18);
    const limited = await persistGetAssignment('ACC-LIMITED');
    expect(limited?.grantedNavigationUids).toEqual(['FRONT-01', 'FRONT-02']);
  });

  it('survives backup and restore of audit events', async () => {
    await persistRecordAuditEvent({
      eventUid: 'EVT-TEST-FRONT-01',
      accountUid: 'ACC-LIMITED',
      area: 'FRONT',
      itemUid: 'FRONT-01',
      route: '/home',
      occurredAt: new Date().toISOString(),
    });
    const snapshotPath = join(mkdtempSync(join(tmpdir(), 'acpos-backup-')), 'backup.json');
    const snapshot = await backupToFile(snapshotPath);
    expect(snapshot.events.some((event) => event.eventUid === 'EVT-TEST-FRONT-01')).toBe(true);
    await persistRecordAuditEvent({
      eventUid: 'EVT-TEST-FRONT-02',
      accountUid: 'ACC-LIMITED',
      area: 'FRONT',
      itemUid: 'FRONT-02',
      route: '/dashboard',
      occurredAt: new Date().toISOString(),
    });
    await restoreFromFile(snapshotPath);
    const restored = await persistGetAssignment('ACC-LIMITED');
    expect(restored?.grantedNavigationUids).toEqual(['FRONT-01', 'FRONT-02']);
  });
});
