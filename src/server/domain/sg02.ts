export const SG02_PERMISSION = "quality.criteria.configure";
export const SG02_CONFIGURE_PERMISSION = "governance.configure";
export const SG02_APPROVE_PERMISSION = "governance.approve";
export const SG02_PAGE_UID = "admin:SG-02";
export const SG02_ROUTE = "/admin/qa-criteria";
export const SG02_PROJECTION = "Sg02WorkbenchProjection";
export const SG02_CHAIN = "SG-02-FWC-PAGE-01";

// Contract quality_governance_contract.lifecycle (6 states).
export const SG02_LIFECYCLE_STATES = ["DRAFT", "REVIEW", "APPROVED", "ACTIVE", "SUPERSEDED", "RETIRED"] as const;
export type Sg02LifecycleState = (typeof SG02_LIFECYCLE_STATES)[number];

// Governed resource types registered through configureGovernedResource.
export const SG02_RESOURCE_TYPES = [
  "quality_criteria_version",
  "quality_dimension",
  "quality_threshold",
  "quality_gate_policy",
  "quality_department_mapping",
  "quality_required_check",
] as const;
export type Sg02ResourceType = (typeof SG02_RESOURCE_TYPES)[number];

// Contract state/registry uids outside the 11-control denominator (same
// precedent as ERP-01-STATE-* / STR-01-STATE-* / KB-01-STATE-*).
export const SG02_STATE_ERROR_UID = "CTRL-ADMIN-SG-02-STATE-ERROR";
export const SG02_STATE_RESOURCE_UID = "CTRL-ADMIN-SG-02-STATE-RESOURCE";
export const SG02_STATE_AUDIT_UID = "CTRL-ADMIN-SG-02-STATE-AUDIT";
export const SG02_STATE_IDEMPOTENCY_UID = "CTRL-ADMIN-SG-02-STATE-IDEMPOTENCY";
export const SG02_STATE_CRITERIA_UID = "CTRL-ADMIN-SG-02-STATE-CRITERIA";
export const SG02_STATE_DIMENSIONS_UID = "CTRL-ADMIN-SG-02-STATE-DIMENSIONS";
export const SG02_STATE_THRESHOLDS_UID = "CTRL-ADMIN-SG-02-STATE-THRESHOLDS";
export const SG02_STATE_MAPPINGS_UID = "CTRL-ADMIN-SG-02-STATE-MAPPINGS";
export const SG02_STATE_CHECKS_UID = "CTRL-ADMIN-SG-02-STATE-CHECKS";
export const SG02_STATE_POLICIES_UID = "CTRL-ADMIN-SG-02-STATE-POLICIES";
export const SG02_STATE_APPROVALS_UID = "CTRL-ADMIN-SG-02-STATE-APPROVALS";

export const SG02_EXTRA_PROJECTION_KEYS = [
  SG02_STATE_ERROR_UID,
  SG02_STATE_RESOURCE_UID,
  SG02_STATE_AUDIT_UID,
  SG02_STATE_IDEMPOTENCY_UID,
  SG02_STATE_CRITERIA_UID,
  SG02_STATE_DIMENSIONS_UID,
  SG02_STATE_THRESHOLDS_UID,
  SG02_STATE_MAPPINGS_UID,
  SG02_STATE_CHECKS_UID,
  SG02_STATE_POLICIES_UID,
  SG02_STATE_APPROVALS_UID,
] as const;

// Server-side action scope map (ACCOUNT_PERMISSION_ASSIGNMENT_ONLY).
export const SG02_ACTION_SCOPES: Record<string, string> = {
  configureGovernedResource: SG02_CONFIGURE_PERMISSION,
  approveGovernedResource: SG02_APPROVE_PERMISSION,
  getUiProjection: SG02_PERMISSION,
};

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
  configureAuthorized: boolean;
  fields: Sg02FieldValue[];
}
