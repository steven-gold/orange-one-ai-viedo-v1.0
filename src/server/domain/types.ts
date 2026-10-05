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

export interface DashboardSectionValue {
  sectionUid: string;
  controlUid: string;
  value: string | null;
  detail: string;
}

export interface DashboardReadModel {
  projectionUid: "CompanyDashboardProjection";
  pageUid: "workspace:WB-01";
  route: "/";
  permission: "workspace.dashboard.view";
  chainUid: "WB-01-FWC-DASHBOARD-READ-01";
  authorized: boolean;
  sections: DashboardSectionValue[];
}

export interface CoreFieldValue {
  controlUid: string;
  value: string | null;
}

export interface CoreReadModel {
  projectionUid: "CoreWorkbenchProjection";
  pageUid: "CORE-01";
  route: "/core";
  permission: "entity.write";
  chainUid: "CORE-01-FWC-PAGE-01";
  authorized: boolean;
  pageMode: "PROJECT_CORE" | "TOPIC_PRODUCTION" | null;
  fields: CoreFieldValue[];
}
