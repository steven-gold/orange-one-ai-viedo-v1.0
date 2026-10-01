export type NavigationArea = 'FRONT' | 'ADMIN';

export interface CanonicalNavigationItem {
  uid: string;
  area: NavigationArea;
  labelKey: string;
  route: string;
  order: number;
  icon: string;
  ariaLabelKey: string;
}

export interface NavigationAuthority {
  authorityUid: string;
  items: CanonicalNavigationItem[];
}

export interface PermissionAssignment {
  accountUid: string;
  grantedNavigationUids: string[];
}

export interface ResolvedNavigationItem extends CanonicalNavigationItem {
  active: boolean;
}

export interface NavigationResolutionError {
  code: 'NAVIGATION_TARGET_UNRESOLVABLE' | 'NAVIGATION_AUTHORITY_UNAVAILABLE';
  message: string;
}

export interface NavigationContext {
  area: NavigationArea;
  authorityUid: string;
  items: ResolvedNavigationItem[];
  resolved: boolean;
  error: NavigationResolutionError | null;
}

export interface NavigationEvent {
  eventUid: string;
  accountUid: string;
  area: NavigationArea;
  itemUid: string;
  route: string;
  occurredAt: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}
