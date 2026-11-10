export const IAM_STATE_ACCOUNTS_UID = "IAM-01-STATE-ACCOUNTS";
export const IAM_STATE_DRAFT_UID = "IAM-01-STATE-DRAFT";
export const IAM_STATE_PREVIEW_UID = "IAM-01-STATE-PREVIEW";
export const IAM_STATE_APPLY_UID = "IAM-01-STATE-APPLY";
export const IAM_STATE_ERROR_UID = "IAM-01-STATE-ERROR";
export const IAM_STATE_QUERY_UID = "IAM-01-STATE-QUERY";
export const IAM_STATE_MODE_UID = "IAM-01-STATE-MODE";
export const IAM_STATE_AUDIT_UID = "IAM-01-STATE-AUDIT";
export const IAM_STATE_PLAN_UID = "IAM-01-STATE-PLAN";
export const IAM_STATE_MATERIALIZED_UID = "IAM-01-STATE-MATERIALIZED";

export type IamSide = "FRONT" | "BACK";

export interface IamL1Choice {
  key: string;
  pageUid: string;
  permission: string;
  permissionTable: string;
}

// Word contract Table 13: exactly 9 frontend + 9 backend L1 choices in exact
// order. Each choice materializes to the page's governed permission assignment
// (explicit assignment only; no wildcard, no role/department inheritance).
export const IAM_FRONT_L1_CATALOG: IamL1Choice[] = [
  { key: "iam.front-01", pageUid: "workspace:WB-01", permission: "workspace.dashboard.view", permissionTable: "ghsn_account_dashboard_permission" },
  { key: "iam.front-02", pageUid: "CORE-01", permission: "entity.write", permissionTable: "ghsn_account_core_permission" },
  { key: "iam.front-03", pageUid: "ASSET-01", permission: "asset.01.view", permissionTable: "ghsn_account_asset_permission" },
  { key: "iam.front-04", pageUid: "VIDEO-01", permission: "video.01.view", permissionTable: "ghsn_account_video_permission" },
  { key: "iam.front-05", pageUid: "EDIT-01", permission: "department.handoff.create", permissionTable: "ghsn_account_edit_permission" },
  { key: "iam.front-06", pageUid: "QA-01", permission: "qa.01.view", permissionTable: "ghsn_account_qa_permission" },
  { key: "iam.front-07", pageUid: "admin:DB-01", permission: "database.metadata.read", permissionTable: "ghsn_account_db_permission" },
  { key: "iam.front-08", pageUid: "workspace:STR-01", permission: "strategy.read", permissionTable: "ghsn_account_str_permission" },
  { key: "iam.front-09", pageUid: "workspace:INFO-01", permission: "information.read", permissionTable: "ghsn_account_info_permission" },
];

export const IAM_BACK_L1_CATALOG: IamL1Choice[] = [
  { key: "iam.back-01", pageUid: "admin:SYS-01", permission: "system.change.propose", permissionTable: "ghsn_account_sys_permission" },
  { key: "iam.back-02", pageUid: "admin:IAM-01", permission: "iam.user.configure", permissionTable: "ghsn_account_iam_permission" },
  { key: "iam.back-03", pageUid: "admin:DEV-01", permission: "outreach.discovery.configure", permissionTable: "ghsn_account_dev_permission" },
  { key: "iam.back-04", pageUid: "admin:SOC-01", permission: "social.account.configure", permissionTable: "ghsn_account_soc_permission" },
  { key: "iam.back-05", pageUid: "admin:ERP-01", permission: "erp.connector.read", permissionTable: "ghsn_account_erp_permission" },
  { key: "iam.back-06", pageUid: "admin:AIAPI-01", permission: "aiapi.provider.read", permissionTable: "ghsn_account_aiapi_permission" },
  { key: "iam.back-07", pageUid: "admin:SG-02", permission: "quality.criteria.configure", permissionTable: "ghsn_account_sg02_permission" },
  { key: "iam.back-08", pageUid: "admin:STR-01", permission: "strategy.administration.read", permissionTable: "ghsn_account_admin_str_permission" },
  { key: "iam.back-09", pageUid: "admin:KB-01", permission: "knowledge.read", permissionTable: "ghsn_account_kb_permission" },
];

export const IAM_L1_CATALOG: Record<IamSide, IamL1Choice[]> = {
  FRONT: IAM_FRONT_L1_CATALOG,
  BACK: IAM_BACK_L1_CATALOG,
};

export const IAM_DEPT_PRESETS = [
  { presetId: "ops-front", labelKey: "iam.preset-ops-front", side: "FRONT" as IamSide, keys: ["iam.front-01", "iam.front-02", "iam.front-03"] },
  { presetId: "studio", labelKey: "iam.preset-studio", side: "FRONT" as IamSide, keys: ["iam.front-01", "iam.front-04", "iam.front-05", "iam.front-06"] },
  { presetId: "platform-admin", labelKey: "iam.preset-platform-admin", side: "BACK" as IamSide, keys: ["iam.back-01", "iam.back-03", "iam.back-04", "iam.back-06"] },
] as const;

export interface IamAccountRow {
  accountUid: string;
  email: string;
  status: "ACTIVE" | "DISABLED";
  sessions: number;
  lastSeenAt: string;
  frontendL1: string[];
  backendL1: string[];
}

export interface IamDraft {
  mode: "CREATE" | "EDIT";
  accountId: string;
  basicData: { displayName: string; email: string; department: string };
  frontL1: string[];
  backL1: string[];
  correlationId: string;
  savedAt: string;
  version: number;
}

export type IamDeltaKind = "ADDED" | "REMOVED" | "UNCHANGED";

export interface IamAssignmentDelta {
  side: IamSide;
  key: string;
  pageUid: string;
  permission: string;
  permissionTable: string;
  kind: IamDeltaKind;
}

export interface IamPreview {
  accountId: string;
  mode: "CREATE" | "EDIT";
  deltas: IamAssignmentDelta[];
  added: number;
  removed: number;
  unchanged: number;
  blocked: number;
  blockers: string[];
  stamp: string;
  draftVersion: number;
  expectedVersion: number;
  // Snapshot of the account's L1 aggregate at preview time; the server
  // re-reads the governed tables before materializing and refuses with
  // IAM-01-ERR-VERSION when the live aggregate has drifted (word:
  // expected_version + preview current).
  baseline: { frontendL1: string[]; backendL1: string[] };
}

export interface IamApplyResult {
  accountId: string;
  status: "COMPLETE" | "PARTIAL" | "ERROR";
  applied: string[];
  failed: string[];
  correlationId: string;
  stamp: string;
  auditEventUid: string;
}

export interface IamErrorState {
  code: string;
  at: string;
}

export interface IamWorkbench {
  accounts: IamAccountRow[];
  draft: IamDraft | null;
  preview: IamPreview | null;
  apply: IamApplyResult | null;
  error: IamErrorState | null;
  query: string;
  mode: "LIST" | "CREATE" | "EDIT";
  audit: string[];
}
