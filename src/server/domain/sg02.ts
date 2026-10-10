export const SG02_PERMISSION = "quality.criteria.configure";
export const SG02_PAGE_UID = "admin:SG-02";
export const SG02_ROUTE = "/admin/qa-criteria";
export const SG02_PROJECTION = "Sg02WorkbenchProjection";
export const SG02_CHAIN = "SG-02-FWC-PAGE-01";

export const SG02_VISIBLE_CONTROLS = [
  "CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN",
  "CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN",
  "CTRL-ADMIN-SG-02-THRESHOLDS-OPEN",
  "CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN",
  "CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN",
  "CTRL-ADMIN-SG-02-GATE-POLICY-OPEN",
  "CTRL-ADMIN-SG-02-APPROVAL-OPEN",
  "CTRL-ADMIN-SG-02-IMPACT-OPEN",
  "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE",
  "CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE",
  "CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN",
] as const;

export const SG02_CONTROL_ACTIONS: Record<string, string> = {
  "CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN": "getUiProjection",
  "CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN": "getUiProjection",
  "CTRL-ADMIN-SG-02-THRESHOLDS-OPEN": "getUiProjection",
  "CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN": "getUiProjection",
  "CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN": "getUiProjection",
  "CTRL-ADMIN-SG-02-GATE-POLICY-OPEN": "getUiProjection",
  "CTRL-ADMIN-SG-02-APPROVAL-OPEN": "getUiProjection",
  "CTRL-ADMIN-SG-02-IMPACT-OPEN": "getUiProjection",
  "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE": "configureGovernedResource",
  "CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE": "approveGovernedResource",
  "CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN": "getUiProjection",
};

export interface Sg02FieldValue {
  controlUid: string;
  value: string | null;
}

export interface Sg02ReadModel {
  projectionUid: typeof SG02_PROJECTION;
  pageUid: typeof SG02_PAGE_UID;
  route: typeof SG02_ROUTE;
  permission: typeof SG02_PERMISSION;
  chainUid: typeof SG02_CHAIN;
  authorized: boolean;
  fields: Sg02FieldValue[];
}
