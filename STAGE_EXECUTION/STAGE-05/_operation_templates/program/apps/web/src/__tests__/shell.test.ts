import { createElement } from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import type {
  CanonicalNavigationItem,
  NavigationAuthority,
  PermissionAssignment,
  ResolvedNavigationItem,
} from '../domain/navigation';
import { resolveAdminActiveUid, resolveFrontActiveUid, resolveVisibleItems } from '../domain/navigation';
import { Sidebar } from '../shell/Sidebar';

afterEach(cleanup);

function item(uid: string, area: 'FRONT' | 'ADMIN', order: number, route: string): CanonicalNavigationItem {
  return {
    uid,
    area,
    order,
    route,
    labelKey: 'nav.home',
    icon: uid.slice(0, 1).toUpperCase(),
    ariaLabelKey: 'nav.home',
  };
}

const authority: NavigationAuthority = {
  authorityUid: 'CANONICAL-NAV-AUTHORITY-HOME-001',
  items: [
    item('FRONT-01', 'FRONT', 1, '/home'),
    item('FRONT-02', 'FRONT', 2, '/dashboard'),
    item('ADMIN-01', 'ADMIN', 1, '/admin/overview'),
    item('ADMIN-02', 'ADMIN', 2, '/admin/accounts'),
  ],
};

const assignment: PermissionAssignment = {
  accountUid: 'ACC-DEMO',
  grantedNavigationUids: ['FRONT-01', 'FRONT-02', 'ADMIN-01'],
};

describe('navigation authority resolution', () => {
  it('resolves visibility as the intersection of authority and assignment', () => {
    const visible = resolveVisibleItems(authority, assignment, 'FRONT');
    expect(visible.map((entry) => entry.uid)).toEqual(['FRONT-01', 'FRONT-02']);
    const admin = resolveVisibleItems(authority, assignment, 'ADMIN');
    expect(admin.map((entry) => entry.uid)).toEqual(['ADMIN-01']);
  });

  it('resolves the front active item from canonical page ancestry', () => {
    const items = resolveVisibleItems(authority, assignment, 'FRONT');
    expect(resolveFrontActiveUid(items, ['FRONT-02', 'child'])).toBe('FRONT-02');
    expect(resolveFrontActiveUid(items, [])).toBeNull();
  });

  it('resolves the admin active item only by exact admin page UID', () => {
    const items = resolveVisibleItems(authority, assignment, 'ADMIN');
    expect(resolveAdminActiveUid(items, 'ADMIN-01')).toBe('ADMIN-01');
    expect(resolveAdminActiveUid(items, 'ADMIN-09')).toBeNull();
  });
});

describe('sidebar rendering', () => {
  const resolved: ResolvedNavigationItem[] = [
    { ...item('FRONT-01', 'FRONT', 1, '/home'), active: true },
  ];

  it('hides labels when collapsed but exposes a full aria-label', () => {
    render(
      createElement(Sidebar, {
        items: resolved,
        collapsed: true,
        reducedMotion: false,
        onActivate: () => undefined,
        onFocusWithin: () => undefined,
      }),
    );
    expect(screen.queryByText('Home')).toBeNull();
    expect(screen.getByRole('button', { name: 'Home' })).toBeTruthy();
  });

  it('shows labels when expanded', () => {
    render(
      createElement(Sidebar, {
        items: resolved,
        collapsed: false,
        reducedMotion: false,
        onActivate: () => undefined,
        onFocusWithin: () => undefined,
      }),
    );
    expect(screen.getByText('Home')).toBeTruthy();
  });
});
