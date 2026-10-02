export type NavigationArea = "FRONT" | "ADMIN";

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

export interface NavigationEvent {
  eventUid: string;
  accountUid: string;
  area: NavigationArea;
  itemUid: string;
  route: string;
  occurredAt: string;
}

export interface ResolvedNavigationItem extends CanonicalNavigationItem {
  active: boolean;
}
