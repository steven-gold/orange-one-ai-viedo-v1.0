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

export interface ResolvedNavigationItem extends CanonicalNavigationItem {
  active: boolean;
}

export interface NavigationResolutionError {
  code: "NAVIGATION_TARGET_UNRESOLVABLE" | "NAVIGATION_AUTHORITY_UNAVAILABLE";
  message: string;
}

export interface NavigationContextResponse {
  area: NavigationArea;
  authorityUid: string;
  items: ResolvedNavigationItem[];
  resolved: boolean;
  error: NavigationResolutionError | null;
}

export function isNavigationTargetResolvable(item: CanonicalNavigationItem): boolean {
  return typeof item.route === "string" && item.route.startsWith("/");
}
