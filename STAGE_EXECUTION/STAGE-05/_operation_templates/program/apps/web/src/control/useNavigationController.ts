import { useCallback, useEffect, useState } from 'react';
import { fetchNavigationContext, NavigationClientError } from '../api/client';
import type {
  NavigationArea,
  NavigationResolutionError,
  ResolvedNavigationItem,
} from '../domain/navigation';

export interface NavigationController {
  area: NavigationArea;
  items: ResolvedNavigationItem[];
  loading: boolean;
  error: NavigationResolutionError | null;
  switchArea: (area: NavigationArea) => void;
  navigate: (route: string) => void;
}

export function useNavigationController(
  accountUid: string,
  activePath: string,
  activePageUid: string | null,
): NavigationController {
  const [area, setArea] = useState<NavigationArea>('FRONT');
  const [items, setItems] = useState<ResolvedNavigationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<NavigationResolutionError | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchNavigationContext({ area, accountUid, activePath, activePageUid }, controller.signal)
      .then((context) => {
        if (cancelled) return;
        setItems(context.items);
        setError(context.error);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === 'AbortError') return;
        const code: NavigationResolutionError['code'] =
          cause instanceof NavigationClientError
            ? (cause.code as NavigationResolutionError['code'])
            : 'NAVIGATION_AUTHORITY_UNAVAILABLE';
        setError({ code, message: cause instanceof Error ? cause.message : String(cause) });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [area, accountUid, activePath, activePageUid]);

  const switchArea = useCallback((next: NavigationArea) => setArea(next), []);
  const navigate = useCallback((route: string) => {
    window.history.pushState({}, '', route);
  }, []);

  return { area, items, loading, error, switchArea, navigate };
}
