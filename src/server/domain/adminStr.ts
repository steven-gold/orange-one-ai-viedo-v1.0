export const ADMIN_STR_PERMISSION = "strategy.administration.read";
export const ADMIN_STR_PAGE_UID = "admin:STR-01";
export const ADMIN_STR_ROUTE = "/admin/strategy";
export const ADMIN_STR_PROJECTION = "AdminStrWorkbenchProjection";
export const ADMIN_STR_CHAIN = "ADMIN-STR-01-FWC-PAGE-01";

export const ADMIN_STR_VISIBLE_CONTROLS = [
  "CTRL-ADMIN-STR-01-VIEW-OVERVIEW",
  "CTRL-ADMIN-STR-01-VIEW-INTELLIGENCE-FACT",
  "CTRL-ADMIN-STR-01-VIEW-PLAYBOOK",
  "CTRL-ADMIN-STR-01-VIEW-OPPORTUNITY",
  "CTRL-ADMIN-STR-01-VIEW-DECISION",
  "CTRL-ADMIN-STR-01-ACT-SEARCH",
  "CTRL-ADMIN-STR-01-ACT-REFRESH",
  "CTRL-ADMIN-STR-01-ACT-NAV-OPEN",
  "CTRL-ADMIN-STR-01-ACT-CONFIGURE",
  "CTRL-ADMIN-STR-01-ACT-APPROVE",
  "CTRL-ADMIN-STR-01-ACT-EXPORT",
  "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE",
  "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT",
] as const;

export const ADMIN_STR_CONTROL_ACTIONS: Record<string, string> = {
  "CTRL-ADMIN-STR-01-VIEW-OVERVIEW": "getUiProjection",
  "CTRL-ADMIN-STR-01-VIEW-INTELLIGENCE-FACT": "getUiProjection",
  "CTRL-ADMIN-STR-01-VIEW-PLAYBOOK": "getUiProjection",
  "CTRL-ADMIN-STR-01-VIEW-OPPORTUNITY": "getUiProjection",
  "CTRL-ADMIN-STR-01-VIEW-DECISION": "getUiProjection",
  "CTRL-ADMIN-STR-01-ACT-SEARCH": "searchProjection",
  "CTRL-ADMIN-STR-01-ACT-REFRESH": "refreshProjection",
  "CTRL-ADMIN-STR-01-ACT-NAV-OPEN": "getUiProjection",
  "CTRL-ADMIN-STR-01-ACT-CONFIGURE": "configureGovernedResource",
  "CTRL-ADMIN-STR-01-ACT-APPROVE": "approveGovernedResource",
  "CTRL-ADMIN-STR-01-ACT-EXPORT": "exportProjection",
  "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE": "saveDraft",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE": "createCandidate",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE": "compareCandidates",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE": "rejectStrategyCandidate",
  "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT": "adoptAsContextCandidate",
};

export interface AdminStrFieldValue {
  controlUid: string;
  value: string | null;
}

export interface AdminStrReadModel {
  projectionUid: typeof ADMIN_STR_PROJECTION;
  pageUid: typeof ADMIN_STR_PAGE_UID;
  route: typeof ADMIN_STR_ROUTE;
  permission: typeof ADMIN_STR_PERMISSION;
  chainUid: typeof ADMIN_STR_CHAIN;
  authorized: boolean;
  fields: AdminStrFieldValue[];
}
