import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../app';
import { bootstrapDatabase } from '../db/bootstrap';
import { closeSqlClient } from '../db/client';

const app = createApp();

beforeAll(async () => {
  await bootstrapDatabase(':memory:');
});

afterAll(async () => {
  await closeSqlClient();
});

describe('authentication middleware', () => {
  it('rejects mismatched session and account', async () => {
    const res = await request(app)
      .get('/api/permissions')
      .set('x-account-uid', 'ACC-DEMO')
      .set('x-session-uid', 'sess-limited-001');
    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe('UNAUTHENTICATED');
  });

  it('returns persisted permission assignment for an authenticated account', async () => {
    const res = await request(app)
      .get('/api/permissions')
      .set('x-account-uid', 'ACC-DEMO')
      .set('x-session-uid', 'sess-demo-001');
    expect(res.status).toBe(200);
    expect(res.body.accountUid).toBe('ACC-DEMO');
    expect(res.body.grantedNavigationUids).toHaveLength(18);
  });
});
