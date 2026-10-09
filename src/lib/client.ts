import type { NavigationArea, NavigationContextResponse } from "./navigation";
import { isNavigationTargetResolvable } from "./navigation";

export class NavigationClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "NavigationClientError";
  }
}

interface NavigationQuery {
  area: NavigationArea;
  accountUid: string;
  sessionUid?: string;
  activePath?: string;
  activePageUid?: string | null;
}

export async function fetchNavigationContext(
  query: NavigationQuery,
  signal?: AbortSignal,
): Promise<NavigationContextResponse> {
  const params = new URLSearchParams({
    area: query.area,
    accountUid: query.accountUid,
  });
  if (query.activePath) params.set("activePath", query.activePath);
  if (query.activePageUid) params.set("activePageUid", query.activePageUid);

  const response = await fetch(`/api/navigation?${params.toString()}`, {
    signal,
    headers: {
      "x-account-uid": query.accountUid,
      "x-session-uid": query.sessionUid ?? "sess-demo-001",
    },
  });
  if (!response.ok) {
    throw new NavigationClientError(
      "NAVIGATION_AUTHORITY_UNAVAILABLE",
      `navigation request failed: ${response.status}`,
    );
  }
  const payload = (await response.json()) as NavigationContextResponse;
  const broken = payload.items.find((item) => !isNavigationTargetResolvable(item));
  if (broken) {
    return {
      ...payload,
      resolved: false,
      error: {
        code: "NAVIGATION_TARGET_UNRESOLVABLE",
        message: `navigation target cannot be resolved for ${broken.uid}`,
      },
    };
  }
  return payload;
}

export async function activateNavigation(
  accountUid: string,
  sessionUid: string,
  itemUid: string,
): Promise<void> {
  await fetch("/api/navigation/activate", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ itemUid }),
  });
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

export class DashboardClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "DashboardClientError";
  }
}

export async function fetchDashboardReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<DashboardReadModel> {
  const response = await fetch("/api/dashboard", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new DashboardClientError("DASHBOARD_READ_UNAVAILABLE", `dashboard request failed: ${response.status}`);
  }
  return (await response.json()) as DashboardReadModel;
}

export async function openDashboardSection(
  accountUid: string,
  sectionUid: string,
  controlUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/dashboard/open", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ sectionUid, controlUid }),
  });
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

export class CoreClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "CoreClientError";
  }
}

export async function fetchCoreReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<CoreReadModel> {
  const response = await fetch("/api/core", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new CoreClientError("CORE_READ_UNAVAILABLE", `core request failed: ${response.status}`);
  }
  return (await response.json()) as CoreReadModel;
}

export async function postCoreAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/core/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class AssetClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "AssetClientError";
  }
}

export async function fetchAssetReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<AssetReadModel> {
  const response = await fetch("/api/assets", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new AssetClientError("ASSET_READ_UNAVAILABLE", `asset request failed: ${response.status}`);
  }
  return (await response.json()) as AssetReadModel;
}

export async function postAssetAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/assets/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class VideoClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "VideoClientError";
  }
}

export async function fetchVideoReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<VideoReadModel> {
  const response = await fetch("/api/video", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new VideoClientError("VIDEO_READ_UNAVAILABLE", `video request failed: ${response.status}`);
  }
  return (await response.json()) as VideoReadModel;
}

export async function postVideoAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/video/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class EditClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "EditClientError";
  }
}

export async function fetchEditReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<EditReadModel> {
  const response = await fetch("/api/edit", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new EditClientError("EDIT_READ_UNAVAILABLE", `edit request failed: ${response.status}`);
  }
  return (await response.json()) as EditReadModel;
}

export async function postEditAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/edit/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class QaClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "QaClientError";
  }
}

export async function fetchQaReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<QaReadModel> {
  const response = await fetch("/api/qa", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new QaClientError("QA_READ_UNAVAILABLE", `qa request failed: ${response.status}`);
  }
  return (await response.json()) as QaReadModel;
}

export async function postQaAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/qa/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class DbClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "DbClientError";
  }
}

export async function fetchDbReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<DbReadModel> {
  const response = await fetch("/api/db", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new DbClientError("DB_READ_UNAVAILABLE", `db request failed: ${response.status}`);
  }
  return (await response.json()) as DbReadModel;
}

export async function postDbAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/db/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class StrClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "StrClientError";
  }
}

export async function fetchStrReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<StrReadModel> {
  const response = await fetch("/api/strategy", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new StrClientError("STR_READ_UNAVAILABLE", `strategy request failed: ${response.status}`);
  }
  return (await response.json()) as StrReadModel;
}

export async function postStrAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/strategy/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class InfoClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "InfoClientError";
  }
}

export async function fetchInfoReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<InfoReadModel> {
  const response = await fetch("/api/info", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new InfoClientError("INFO_READ_UNAVAILABLE", `info request failed: ${response.status}`);
  }
  return (await response.json()) as InfoReadModel;
}

export async function postInfoAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/info/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class SysClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "SysClientError";
  }
}

export async function fetchSysReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<SysReadModel> {
  const response = await fetch("/api/system", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new SysClientError("SYS_READ_UNAVAILABLE", `system request failed: ${response.status}`);
  }
  return (await response.json()) as SysReadModel;
}

export async function postSysAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/system/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class IamClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "IamClientError";
  }
}

export async function fetchIamReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<IamReadModel> {
  const response = await fetch("/api/accounts", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new IamClientError("IAM_READ_UNAVAILABLE", `accounts request failed: ${response.status}`);
  }
  return (await response.json()) as IamReadModel;
}

export async function postIamAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/accounts/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
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

export class DevClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "DevClientError";
  }
}

export async function fetchDevReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<DevReadModel> {
  const response = await fetch("/api/dev", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new DevClientError("DEV_READ_UNAVAILABLE", `dev request failed: ${response.status}`);
  }
  return (await response.json()) as DevReadModel;
}

export async function postDevAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/dev/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
}

export interface SocFieldValue {
  controlUid: string;
  value: string | null;
}

export interface SocReadModel {
  projectionUid: "SocWorkbenchProjection";
  pageUid: "admin:SOC-01";
  route: "/admin/social";
  permission: "social.account.configure";
  chainUid: "SOC-01-FWC-PAGE-01";
  authorized: boolean;
  fields: SocFieldValue[];
}

export class SocClientError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "SocClientError";
  }
}

export async function fetchSocReadModel(
  accountUid: string,
  sessionUid = "sess-demo-001",
  signal?: AbortSignal,
): Promise<SocReadModel> {
  const response = await fetch("/api/social", {
    signal,
    headers: {
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
  });
  if (!response.ok) {
    throw new SocClientError("SOC_READ_UNAVAILABLE", `social request failed: ${response.status}`);
  }
  return (await response.json()) as SocReadModel;
}

export async function postSocAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  sessionUid = "sess-demo-001",
): Promise<void> {
  await fetch("/api/social/action", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-account-uid": accountUid,
      "x-session-uid": sessionUid,
    },
    body: JSON.stringify({ controlUid, actionUid }),
  });
}
