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

export const SG02_LIFECYCLE_ROWS = ["DRAFT", "REVIEW", "ACTIVE", "SUPERSEDED"] as const;

export const SG02_TABLE_COLUMNS = [
  "sg02.col-version",
  "sg02.col-state",
  "sg02.col-dimensions",
  "sg02.col-threshold",
  "sg02.col-department",
  "sg02.col-approval",
  "sg02.col-impact",
] as const;

export type Sg02Drawer =
  | "criteria_table"
  | "dimension_library"
  | "thresholds"
  | "department_mapping"
  | "required_checks"
  | "gate_policy"
  | "approval"
  | "impact"
  | "nav";

export type Sg02Surface = "main" | "approval";
