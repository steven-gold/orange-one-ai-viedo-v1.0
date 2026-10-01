import request from 'supertest';
import { describe, expect, it } from 'vitest';
import { createApp } from '../app';

const app = createApp();

describe('navigation runtime API', () => {
  it('returns the visible navigation as the authority/assignment intersection', async () => {
    const res = await request(app).get('/api/navigation').set('x-account-uid', 'ACC-LIMITED');
    expect(res.status).toBe(200);
    expect(res.body.authorityUid).toBe('CANONICAL-NAV-AUTHORITY-HOME-001');
    expect(res.body.items.map((i: { uid: string }) => i.uid)).toEqual(['FRONT-01', 'FRONT-02']);
  });

  it('rejects navigation for an account with no assignment', async () => {
    const res = await request(app).get('/api/navigation').set('x-account-uid', 'ACC-UNKNOWN');
    expect(res.status).toBe(404);
    expect(res.body.error.code).toBe('NAVIGATION_TARGET_UNRESOLVABLE');
  });

  it('records an activation for a visible item', async () => {
    const res = await request(app)
      .post('/api/navigation/activate')
      .set('x-account-uid', 'ACC-LIMITED')
      .send({ itemUid: 'FRONT-02' });
    expect(res.status).toBe(202);
    expect(res.body.route).toBe('/dashboard');
  });

  it('denies activation for a non-visible item', async () => {
    const res = await request(app)
      .post('/api/navigation/activate')
      .set('x-account-uid', 'ACC-LIMITED')
      .send({ itemUid: 'ADMIN-01' });
    expect(res.status).toBe(404);
  });

  it('resolves the front active uid from canonical ancestry', async () => {
    const res = await request(app)
      .get('/api/navigation/active?area=FRONT&ancestry=FRONT-02')
      .set('x-account-uid', 'ACC-LIMITED');
    expect(res.status).toBe(200);
    expect(res.body.activeNavigationUid).toBe('FRONT-02');
  });
});
