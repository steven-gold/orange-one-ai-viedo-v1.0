import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../app';
import { bootstrapDatabase } from '../db/bootstrap';
import { closeSqlClient } from '../db/client';
import { persistListAuditEvents } from '../db/persist';

const app = createApp();

beforeAll(async () => {
  await bootstrapDatabase(':memory:');
});

afterAll(async () => {
  await closeSqlClient();
});

describe('navigation runtime API', () => {
  it('rejects unauthenticated navigation', async () => {
    const res = await request(app).get('/api/navigation').set('x-account-uid', 'ACC-LIMITED');
    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe('UNAUTHENTICATED');
  });

  it('returns the visible navigation as the authority/assignment intersection', async () => {
    const res = await request(app)
      .get('/api/navigation')
      .set('x-account-uid', 'ACC-LIMITED')
      .set('x-session-uid', 'sess-limited-001');
    expect(res.status).toBe(200);
    expect(res.body.authorityUid).toBe('CANONICAL-NAV-AUTHORITY-HOME-001');
    expect(res.body.items.map((i: { uid: string }) => i.uid)).toEqual(['FRONT-01', 'FRONT-02']);
  });

  it('rejects navigation for an account with no assignment', async () => {
    const res = await request(app)
      .get('/api/navigation')
      .set('x-account-uid', 'ACC-UNKNOWN')
      .set('x-session-uid', 'sess-limited-001');
    expect(res.status).toBe(401);
  });

  it('records an activation for a visible item in persistent audit storage', async () => {
    const res = await request(app)
      .post('/api/navigation/activate')
      .set('x-account-uid', 'ACC-LIMITED')
      .set('x-session-uid', 'sess-limited-001')
      .send({ itemUid: 'FRONT-02' });
    expect(res.status).toBe(202);
    expect(res.body.route).toBe('/dashboard');
    const events = await persistListAuditEvents();
    expect(events.some((event) => event.itemUid === 'FRONT-02' && event.accountUid === 'ACC-LIMITED')).toBe(true);
  });

  it('denies activation for a non-visible item', async () => {
    const res = await request(app)
      .post('/api/navigation/activate')
      .set('x-account-uid', 'ACC-LIMITED')
      .set('x-session-uid', 'sess-limited-001')
      .send({ itemUid: 'ADMIN-01' });
    expect(res.status).toBe(404);
  });

  it('resolves the front active uid from canonical ancestry', async () => {
    const res = await request(app)
      .get('/api/navigation/active?area=FRONT&ancestry=FRONT-02')
      .set('x-account-uid', 'ACC-LIMITED')
      .set('x-session-uid', 'sess-limited-001');
    expect(res.status).toBe(200);
    expect(res.body.activeNavigationUid).toBe('FRONT-02');
  });

  it('reports ready after migrations bind', async () => {
    const res = await request(app).get('/health/ready');
    expect(res.status).toBe(200);
    expect(res.body.ready).toBe(true);
    expect(res.body.migrationCount).toBeGreaterThanOrEqual(1);
  });
});
