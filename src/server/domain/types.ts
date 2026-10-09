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

export interface AssetFieldValue {
  controlUid: string;
  value: string | null;
}

export interface AssetReadModel {
  projectionUid: "AssetWorkbenchProjection";
  pageUid: "ASSET-01";
  route: "/assets";
  permission: "asset.01.view";
  chainUid: "ASSET-01-FWC-PAGE-01";
  authorized: boolean;
  fields: AssetFieldValue[];
}

export interface VideoFieldValue {
  controlUid: string;
  value: string | null;
}

export interface VideoReadModel {
  projectionUid: "VideoWorkbenchProjection";
  pageUid: "VIDEO-01";
  route: "/video";
  permission: "video.01.view";
  chainUid: "VIDEO-01-FWC-PAGE-01";
  authorized: boolean;
  fields: VideoFieldValue[];
}

export interface EditFieldValue {
  controlUid: string;
  value: string | null;
}

export interface EditReadModel {
  projectionUid: "EditWorkbenchProjection";
  pageUid: "EDIT-01";
  route: "/edit";
  permission: "department.handoff.create";
  chainUid: "EDIT-01-FWC-PAGE-01";
  authorized: boolean;
  fields: EditFieldValue[];
}

export interface QaFieldValue {
  controlUid: string;
  value: string | null;
}

export interface QaReadModel {
  projectionUid: "QaWorkbenchProjection";
  pageUid: "QA-01";
  route: "/qa";
  permission: "qa.01.view";
  chainUid: "QA-01-FWC-PAGE-01";
  authorized: boolean;
  fields: QaFieldValue[];
}

export interface DbFieldValue {
  controlUid: string;
  value: string | null;
}

export interface DbReadModel {
  projectionUid: "DbWorkbenchProjection";
  pageUid: "admin:DB-01";
  route: "/db";
  permission: "database.metadata.read";
  chainUid: "DB-01-FWC-PAGE-01";
  authorized: boolean;
  fields: DbFieldValue[];
}

export interface StrFieldValue {
  controlUid: string;
  value: string | null;
}

export interface StrReadModel {
  projectionUid: "StrWorkbenchProjection";
  pageUid: "workspace:STR-01";
  route: "/strategy";
  permission: "strategy.read";
  chainUid: "STR-01-FWC-PAGE-01";
  authorized: boolean;
  fields: StrFieldValue[];
}

export interface InfoFieldValue {
  controlUid: string;
  value: string | null;
}

export interface InfoReadModel {
  projectionUid: "InfoWorkbenchProjection";
  pageUid: "workspace:INFO-01";
  route: "/info";
  permission: "information.read";
  chainUid: "INFO-01-FWC-PAGE-01";
  authorized: boolean;
  fields: InfoFieldValue[];
}

export interface SysFieldValue {
  controlUid: string;
  value: string | null;
}

export interface SysReadModel {
  projectionUid: "SysWorkbenchProjection";
  pageUid: "admin:SYS-01";
  route: "/admin/system";
  permission: "system.change.propose";
  chainUid: "SYS-01-FWC-PAGE-01";
  authorized: boolean;
  fields: SysFieldValue[];
}

export interface IamFieldValue {
  controlUid: string;
  value: string | null;
}

export interface IamReadModel {
  projectionUid: "IamWorkbenchProjection";
  pageUid: "admin:IAM-01";
  route: "/admin/accounts";
  permission: "iam.user.configure";
  chainUid: "IAM-01-FWC-PAGE-01";
  authorized: boolean;
  fields: IamFieldValue[];
}

export interface DevFieldValue {
  controlUid: string;
  value: string | null;
}

export interface DevReadModel {
  projectionUid: "DevWorkbenchProjection";
  pageUid: "admin:DEV-01";
  route: "/admin/dev";
  permission: "outreach.discovery.configure";
  chainUid: "DEV-01-FWC-PAGE-01";
  authorized: boolean;
  fields: DevFieldValue[];
}
