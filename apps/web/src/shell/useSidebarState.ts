import { useCallback, useEffect, useMemo, useState } from 'react';

export interface SidebarState {
  collapsed: boolean;
  reducedMotion: boolean;
  expand: () => void;
  collapse: () => void;
  toggle: () => void;
  collapseOnNavigate: () => void;
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Sidebar interaction state machine: collapsed/expanded. Navigation immediately
 * collapses the sidebar and restores the maximum workspace.
 */
export function useSidebarState(initialCollapsed = false): SidebarState {
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setReducedMotion(query.matches);
    query.addEventListener?.('change', onChange);
    return () => query.removeEventListener?.('change', onChange);
  }, []);

  const expand = useCallback(() => setCollapsed(false), []);
  const collapse = useCallback(() => setCollapsed(true), []);
  const toggle = useCallback(() => setCollapsed((value) => !value), []);
  const collapseOnNavigate = useCallback(() => setCollapsed(true), []);

  return useMemo(
    () => ({ collapsed, reducedMotion, expand, collapse, toggle, collapseOnNavigate }),
    [collapsed, reducedMotion, expand, collapse, toggle, collapseOnNavigate],
  );
}
