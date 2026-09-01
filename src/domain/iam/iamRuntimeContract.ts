export const IAM_CONTROL_COUNT = 14;
export const IAM_SECTION_COUNT = 6;

export const IAM_PORTS = [
  "getUiProjection",
  "searchProjection",
  "saveDraft",
  "validateDraft",
  "configureGovernedResource",
  "previewAuthorizationImpact",
  "assignAccountPermission",
  "revokeAccountPermission",
  "approveGovernedResource",
] as const;

export type IamOperation = (typeof IAM_PORTS)[number];

export const IAM_PAGE_STATES = [
  "LIST",
  "CREATE_BASIC",
  "CREATE_PERMISSION",
  "CREATE_PREVIEW",
  "EDIT_BASIC",
  "EDIT_PERMISSION",
  "EDIT_PREVIEW",
  "APPLYING",
  "COMPLETE",
  "BLOCKED",
  "ERROR",
] as const;

export type IamPageState = (typeof IAM_PAGE_STATES)[number];

export function isIamPageState(value: unknown): value is IamPageState {
  return typeof value === "string" && (IAM_PAGE_STATES as readonly string[]).includes(value);
}

export const IAM_FRONT_L1 = [
  "FRONT-L1-01",
  "FRONT-L1-02",
  "FRONT-L1-03",
  "FRONT-L1-04",
  "FRONT-L1-05",
  "FRONT-L1-06",
  "FRONT-L1-07",
  "FRONT-L1-08",
  "FRONT-L1-09",
] as const;

export const IAM_ADMIN_L1 = [
  "ADMIN-L1-SYSTEM",
  "ADMIN-L1-IAM",
  "ADMIN-L1-DEV",
  "ADMIN-L1-SOCIAL",
  "ADMIN-L1-ERP",
  "ADMIN-L1-AIAPI",
  "ADMIN-L1-QA-CRITERIA",
  "ADMIN-L1-STRATEGY",
  "ADMIN-L1-KNOWLEDGE",
] as const;
