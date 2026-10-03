import { createElement } from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('homepage shell runtime', () => {
  it('renders authenticated front navigation from the API contract', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          area: 'FRONT',
          authorityUid: 'CANONICAL-NAV-AUTHORITY-HOME-001',
          items: [
            {
              uid: 'FRONT-01',
              area: 'FRONT',
              labelKey: 'nav.home',
              route: '/home',
              order: 1,
              icon: 'H',
              ariaLabelKey: 'nav.home',
              active: true,
            },
            {
              uid: 'FRONT-02',
              area: 'FRONT',
              labelKey: 'nav.dashboard',
              route: '/dashboard',
              order: 2,
              icon: 'D',
              ariaLabelKey: 'nav.dashboard',
              active: false,
            },
          ],
          resolved: true,
          error: null,
        }),
      })),
    );
    render(createElement(App, { accountUid: 'ACC-LIMITED' }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Home' })).toBeTruthy();
    });
    expect(screen.getByText('Dashboard')).toBeTruthy();
    expect(screen.getByRole('tablist', { name: 'Frontend Admin switch' })).toBeTruthy();
  });
});
