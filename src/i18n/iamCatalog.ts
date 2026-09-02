import type { Locale } from "./catalog";

type Entry = Record<Locale, string>;

export const IAM_CATALOG = {
  pageName: { "zh-TW": "帳戶與權限", "zh-CN": "账户与权限", en: "Accounts & Permissions" },
  pageRole: { "zh-TW": "帳戶、明確權限指派、預覽與存取治理工作區", "zh-CN": "账户、明确权限指派、预览与访问治理工作区", en: "Account, explicit permission assignment, preview and access-governance workspace" },
  authorizedCount: { "zh-TW": "授權帳號", "zh-CN": "授权账户", en: "Authorized accounts" },
  addAccount: { "zh-TW": "新增帳號", "zh-CN": "新增账户", en: "Add account" },
  directory: { "zh-TW": "帳號目錄", "zh-CN": "账户目录", en: "Account Directory" },
  search: { "zh-TW": "搜尋帳號", "zh-CN": "搜索账户", en: "Search accounts" },
  searchHint: { "zh-TW": "輸入後按 Enter 查詢", "zh-CN": "输入后按 Enter 查询", en: "Type and press Enter to search" },
  noAccounts: { "zh-TW": "目前無可顯示的真實帳號資料", "zh-CN": "目前无可显示的真实账户数据", en: "No real account data is available to display" },
  accountDetail: { "zh-TW": "帳戶細節 / 安全 / 治理", "zh-CN": "账户详情 / 安全 / 治理", en: "Account Detail / Security / Governance" },
  identitySource: { "zh-TW": "Identity Source", "zh-CN": "Identity Source", en: "Identity Source" },
  membership: { "zh-TW": "Organization Scope", "zh-CN": "Organization Scope", en: "Organization Scope" },
  mfa: { "zh-TW": "MFA", "zh-CN": "MFA", en: "MFA" },
  risk: { "zh-TW": "Risk", "zh-CN": "Risk", en: "Risk" },
  session: { "zh-TW": "Session / Access History", "zh-CN": "Session / Access History", en: "Session / Access History" },
  effective: { "zh-TW": "Effective Permission", "zh-CN": "Effective Permission", en: "Effective Permission" },
  edit: { "zh-TW": "編輯", "zh-CN": "编辑", en: "Edit" },
  flow: { "zh-TW": "新增 / 編輯帳戶流程", "zh-CN": "新增 / 编辑账户流程", en: "Add / Edit Account Flow" },
  step1: { "zh-TW": "1 基本資料", "zh-CN": "1 基本数据", en: "1 Basic Data" },
  step2: { "zh-TW": "2 L1 權限", "zh-CN": "2 L1 权限", en: "2 L1 Permissions" },
  step3: { "zh-TW": "3 預覽與完成", "zh-CN": "3 预览与完成", en: "3 Preview & Complete" },
  schemaBlocked: { "zh-TW": "Exact Identity Candidate / Organization Scope schema 尚未解析；依 Authority 禁止自行建立姓名、Email、密碼等欄位。", "zh-CN": "Exact Identity Candidate / Organization Scope schema 尚未解析；依 Authority 禁止自行建立姓名、Email、密码等字段。", en: "Exact Identity Candidate / Organization Scope schema is unresolved. Authority forbids inventing name, email, password or other fields." },
  schemaReady: { "zh-TW": "欄位依目前註冊的 Identity / Organization schema 動態載入。", "zh-CN": "字段依当前注册的 Identity / Organization schema 动态载入。", en: "Fields are loaded dynamically from the current registered Identity / Organization schema." },
  preset: { "zh-TW": "預設部門權限", "zh-CN": "预设部门权限", en: "Department Permission Preset" },
  noPreset: { "zh-TW": "無預設 / 手動設定", "zh-CN": "无预设 / 手动设置", en: "No preset / Manual" },
  frontAll: { "zh-TW": "前台全部", "zh-CN": "前台全部", en: "All Frontend" },
  backAll: { "zh-TW": "後台總權限", "zh-CN": "后台总权限", en: "All Admin" },
  frontL1: { "zh-TW": "前台 9 L1", "zh-CN": "前台 9 L1", en: "Frontend 9 L1" },
  backL1: { "zh-TW": "後台 9 L1", "zh-CN": "后台 9 L1", en: "Admin 9 L1" },
  saveDraft: { "zh-TW": "儲存草稿", "zh-CN": "保存草稿", en: "Save Draft" },
  validate: { "zh-TW": "驗證", "zh-CN": "验证", en: "Validate" },
  previewButton: { "zh-TW": "權限預覽", "zh-CN": "权限预览", en: "Permission Preview" },
  complete: { "zh-TW": "完成建立 / 儲存變更", "zh-CN": "完成建立 / 保存变更", en: "Complete / Save Changes" },
  completeConfirm: { "zh-TW": "確認套用目前已預覽的帳戶與明確權限變更？", "zh-CN": "确认应用当前已预览的账户与明确权限变更？", en: "Apply the currently previewed account and explicit permission changes?" },
  preview: { "zh-TW": "有效權限 / 影響預覽", "zh-CN": "有效权限 / 影响预览", en: "Effective Permission / Impact Preview" },
  previewEmpty: { "zh-TW": "完成 Basic Data 驗證並形成明確 L1 草稿後，才可產生 added / removed / unchanged / blocked 預覽。", "zh-CN": "完成 Basic Data 验证并形成明确 L1 草稿后，才可产生 added / removed / unchanged / blocked 预览。", en: "Impact preview becomes available after Basic Data validates and an explicit L1 draft exists." },
  audit: { "zh-TW": "Audit / Access Review", "zh-CN": "Audit / Access Review", en: "Audit / Access Review" },
  auditEmpty: { "zh-TW": "目前無可顯示的真實 Audit / Access Review 資料", "zh-CN": "目前无可显示的真实 Audit / Access Review 数据", en: "No real Audit / Access Review data is available" },
  visualPhase: { "zh-TW": "視覺施工階段：不執行帳號或權限變更", "zh-CN": "视觉施工阶段：不执行账户或权限变更", en: "Visual phase: account and permission mutations are disabled" },
} satisfies Record<string, Entry>;

export type IamTranslationKey = keyof typeof IAM_CATALOG;
export function iamText(locale: Locale, key: IamTranslationKey): string { return IAM_CATALOG[key][locale]; }
