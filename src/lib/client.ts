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
