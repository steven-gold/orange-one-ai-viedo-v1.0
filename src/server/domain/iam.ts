export const IAM_PERMISSION = "iam.user.configure";
export const IAM_PAGE_UID = "admin:IAM-01";
export const IAM_ROUTE = "/admin/accounts";
export const IAM_PROJECTION = "IamWorkbenchProjection";
export const IAM_CHAIN = "IAM-01-FWC-PAGE-01";

export const IAM_VISIBLE_CONTROLS = [
  "IAM-01-CTL-SEARCH",
  "IAM-01-BTN-ADD",
  "IAM-01-BTN-EDIT",
  "IAM-01-CTL-BASIC-DATA",
  "IAM-01-SEL-DEPT-PRESET",
  "IAM-01-CHK-FRONT-ALL",
  "IAM-01-GRP-FRONT-L1",
  "IAM-01-CHK-BACK-ALL",
  "IAM-01-GRP-BACK-L1",
  "IAM-01-BTN-SAVE-DRAFT",
  "IAM-01-BTN-VALIDATE",
  "IAM-01-BTN-PREVIEW",
  "IAM-01-BTN-COMPLETE",
  "IAM-01-BTN-AUDIT",
] as const;

export const IAM_CONTROL_ACTIONS: Record<string, string> = {
  "IAM-01-CTL-SEARCH": "IAM-01-ACT-SEARCH",
  "IAM-01-BTN-ADD": "IAM-01-ACT-OPEN-CREATE",
  "IAM-01-BTN-EDIT": "IAM-01-ACT-OPEN-EDIT",
  "IAM-01-CTL-BASIC-DATA": "IAM-01-ACT-BASIC-DATA-EDIT",
  "IAM-01-SEL-DEPT-PRESET": "IAM-01-ACT-PRESET-APPLY-TO-DRAFT",
  "IAM-01-CHK-FRONT-ALL": "IAM-01-ACT-FRONT-ALL-DRAFT",
  "IAM-01-GRP-FRONT-L1": "IAM-01-ACT-L1-DRAFT-SET",
  "IAM-01-CHK-BACK-ALL": "IAM-01-ACT-BACK-ALL-DRAFT",
  "IAM-01-GRP-BACK-L1": "IAM-01-ACT-L1-DRAFT-SET",
  "IAM-01-BTN-SAVE-DRAFT": "IAM-01-ACT-SAVE-DRAFT",
  "IAM-01-BTN-VALIDATE": "IAM-01-ACT-VALIDATE-DRAFT",
  "IAM-01-BTN-PREVIEW": "IAM-01-ACT-PREVIEW",
  "IAM-01-BTN-COMPLETE": "IAM-01-ACT-COMPLETE",
  "IAM-01-BTN-AUDIT": "IAM-01-ACT-AUDIT-OPEN",
};

export interface IamFieldValue {
  controlUid: string;
  value: string | null;
}

export interface IamReadModel {
  projectionUid: typeof IAM_PROJECTION;
  pageUid: typeof IAM_PAGE_UID;
  route: typeof IAM_ROUTE;
  permission: typeof IAM_PERMISSION;
  chainUid: typeof IAM_CHAIN;
  authorized: boolean;
  fields: IamFieldValue[];
}
