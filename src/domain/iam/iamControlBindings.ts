export type IamControlEffect =
  | "READ"
  | "UI_ONLY"
  | "DRAFT_UI"
  | "REGISTERED_COMMAND"
  | "ORCHESTRATED_EXISTING_OPERATIONS"
  | "READ_UI";

export type IamControlBinding = {
  action_uid: string;
  gate_uid: string;
  permission: string;
  effect_type: IamControlEffect;
  operation: string | null;
  method_path: string | null;
  operations?: readonly string[];
};

export const IAM_CONTROL_BINDINGS = {
  "IAM-01-CTL-SEARCH": {
    action_uid: "IAM-01-ACT-SEARCH",
    gate_uid: "IAM-01-GATE-PAGE",
    permission: "projection.search",
    effect_type: "READ",
    operation: "searchProjection",
    method_path: "POST /v1/search",
  },
  "IAM-01-BTN-ADD": {
    action_uid: "IAM-01-ACT-OPEN-CREATE",
    gate_uid: "IAM-01-GATE-MANAGE",
    permission: "iam.user.create",
    effect_type: "UI_ONLY",
    operation: null,
    method_path: null,
  },
  "IAM-01-BTN-EDIT": {
    action_uid: "IAM-01-ACT-OPEN-EDIT",
    gate_uid: "IAM-01-GATE-MANAGE",
    permission: "iam.user.configure",
    effect_type: "UI_ONLY",
    operation: null,
    method_path: null,
  },
  "IAM-01-CTL-BASIC-DATA": {
    action_uid: "IAM-01-ACT-BASIC-DATA-EDIT",
    gate_uid: "IAM-01-GATE-DRAFT",
    permission: "iam.user.create/configure",
    effect_type: "DRAFT_UI",
    operation: null,
    method_path: null,
  },
  "IAM-01-SEL-DEPT-PRESET": {
    action_uid: "IAM-01-ACT-PRESET-APPLY-TO-DRAFT",
    gate_uid: "IAM-01-GATE-DRAFT",
    permission: "iam.permission.configure",
    effect_type: "DRAFT_UI",
    operation: null,
    method_path: null,
  },
  "IAM-01-CHK-FRONT-ALL": {
    action_uid: "IAM-01-ACT-FRONT-ALL-DRAFT",
    gate_uid: "IAM-01-GATE-DRAFT",
    permission: "iam.permission.configure",
    effect_type: "DRAFT_UI",
    operation: null,
    method_path: null,
  },
  "IAM-01-GRP-FRONT-L1": {
    action_uid: "IAM-01-ACT-L1-DRAFT-SET",
    gate_uid: "IAM-01-GATE-DRAFT",
    permission: "iam.permission.configure",
    effect_type: "DRAFT_UI",
    operation: null,
    method_path: null,
  },
  "IAM-01-CHK-BACK-ALL": {
    action_uid: "IAM-01-ACT-BACK-ALL-DRAFT",
    gate_uid: "IAM-01-GATE-DRAFT",
    permission: "iam.permission.configure",
    effect_type: "DRAFT_UI",
    operation: null,
    method_path: null,
  },
  "IAM-01-GRP-BACK-L1": {
    action_uid: "IAM-01-ACT-L1-DRAFT-SET",
    gate_uid: "IAM-01-GATE-DRAFT",
    permission: "iam.permission.configure",
    effect_type: "DRAFT_UI",
    operation: null,
    method_path: null,
  },
  "IAM-01-BTN-SAVE-DRAFT": {
    action_uid: "IAM-01-ACT-SAVE-DRAFT",
    gate_uid: "IAM-01-GATE-DRAFT",
    permission: "entity.write",
    effect_type: "REGISTERED_COMMAND",
    operation: "saveDraft",
    method_path: "POST /v1/drafts",
  },
  "IAM-01-BTN-VALIDATE": {
    action_uid: "IAM-01-ACT-VALIDATE-DRAFT",
    gate_uid: "IAM-01-GATE-DRAFT",
    permission: "entity.read",
    effect_type: "REGISTERED_COMMAND",
    operation: "validateDraft",
    method_path: "POST /v1/drafts/{id}/validate",
  },
  "IAM-01-BTN-PREVIEW": {
    action_uid: "IAM-01-ACT-PREVIEW",
    gate_uid: "IAM-01-GATE-PREVIEW",
    permission: "iam.permission.configure",
    effect_type: "REGISTERED_COMMAND",
    operation: "previewAuthorizationImpact",
    method_path: "POST /v1/iam/accounts/{accountId}/authorization-impact",
  },
  "IAM-01-BTN-COMPLETE": {
    action_uid: "IAM-01-ACT-COMPLETE",
    gate_uid: "IAM-01-GATE-COMPLETE",
    permission: "iam.user.create/configure + iam.permission.configure",
    effect_type: "ORCHESTRATED_EXISTING_OPERATIONS",
    operation: null,
    method_path: null,
    operations: [
      "saveDraft/configureGovernedResource",
      "validateDraft",
      "previewAuthorizationImpact",
      "assignAccountPermission",
      "revokeAccountPermission",
      "approveGovernedResource",
    ],
  },
  "IAM-01-BTN-AUDIT": {
    action_uid: "IAM-01-ACT-AUDIT-OPEN",
    gate_uid: "IAM-01-GATE-PAGE",
    permission: "page.view",
    effect_type: "READ_UI",
    operation: "getUiProjection",
    method_path: "GET /v1/ui-projections/{pageUid}",
  },
} as const satisfies Record<string, IamControlBinding>;

export type IamControlUid = keyof typeof IAM_CONTROL_BINDINGS;
export const IAM_CONTROL_BINDING_COUNT = Object.keys(IAM_CONTROL_BINDINGS).length;
