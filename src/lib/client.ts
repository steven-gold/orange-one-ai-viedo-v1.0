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
