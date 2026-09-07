import type { Locale } from "./catalog";

type Entry = Record<Locale, string>;

export const QA_CRITERIA_TEXT = {
  pageName: {"zh-TW":"QA 審查項目名單","zh-CN":"QA 审查项目名单",en:"QA Review Criteria"},
  pageRole: {"zh-TW":"管理 Criteria Version、Dimension、Threshold、Department Applicability、Required Check、Gate Policy 與 Approval；不是專案待審 Queue。","zh-CN":"管理 Criteria Version、Dimension、Threshold、Department Applicability、Required Check、Gate Policy 与 Approval；不是项目待审 Queue。",en:"Govern criteria versions, dimensions, thresholds, department applicability, required checks, gate policy and approval; this is not a project pending-QA queue."},
  criteriaTable: {"zh-TW":"QA 審查項目名單","zh-CN":"QA 审查项目名单",en:"Review Criteria List"},
  version: {"zh-TW":"Criteria Version","zh-CN":"Criteria Version",en:"Criteria Version"},
  dimension: {"zh-TW":"Dimension","zh-CN":"Dimension",en:"Dimension"},
  policy: {"zh-TW":"Gate Policy","zh-CN":"Gate Policy",en:"Gate Policy"},
  mapping: {"zh-TW":"Department Mapping","zh-CN":"Department Mapping",en:"Department Mapping"},
  approval: {"zh-TW":"Approval","zh-CN":"Approval",en:"Approval"},
  noData: {"zh-TW":"目前沒有可顯示的真實 Criteria 資料","zh-CN":"目前没有可显示的真实 Criteria 数据",en:"No real criteria data is available to display"},
  detailSections: {"zh-TW":"審查標準詳細治理區塊","zh-CN":"审查标准详细治理区块",en:"Review Standard Detail Sections"},
  configure: {"zh-TW":"設定治理資源","zh-CN":"设置治理资源",en:"Configure Governed Resource"},
  approve: {"zh-TW":"核准治理資源","zh-CN":"批准治理资源",en:"Approve Governed Resource"},
  navOpen: {"zh-TW":"查看治理詳細資料","zh-CN":"查看治理详细资料",en:"View Governance Detail"},
  visualPhase: {"zh-TW":"視覺施工階段：Configure / Approve business runtime 尚未啟用；門檻值不硬編、不建立假 Criteria。","zh-CN":"视觉施工阶段：Configure / Approve business runtime 尚未启用；门槛值不硬编码、不建立假 Criteria。",en:"Visual phase: Configure / Approve business runtime is not enabled; thresholds are not hardcoded and no fake criteria are created."},
  drawerEmpty: {"zh-TW":"僅顯示已授權的真實 read-model projection；目前無資料。","zh-CN":"仅显示已授权的真实 read-model projection；当前无数据。",en:"Only authorized real read-model projections are shown; no data is currently available."},
  context: {"zh-TW":"SG-02 上下文","zh-CN":"SG-02 上下文",en:"SG-02 Context"},
  eyebrow: {"zh-TW":"ADMIN · SG-02 · QA 治理","zh-CN":"ADMIN · SG-02 · QA 治理",en:"ADMIN · SG-02 · QUALITY GOVERNANCE"},
  governanceState: {"zh-TW":"QA 治理","zh-CN":"QA 治理",en:"Quality Governance"},
  correlation: {"zh-TW":"關聯","zh-CN":"关联",en:"Correlation"},
  criteriaSummaryHint: {"zh-TW":"Criteria 版本 · Dimension · Policy · Mapping · Approval","zh-CN":"Criteria 版本 · Dimension · Policy · Mapping · Approval",en:"Criteria versions · dimensions · policies · mappings · approvals"},
  truthNote: {"zh-TW":"DRAFT → REVIEW → APPROVED → ACTIVE → SUPERSEDED → RETIRED。Active Criteria 為不可變版本；任何修改都必須建立新的核准版本，並完成 Impact、Approval 與受影響 Task 的重新驗證。此視覺層不硬編任何 Threshold。","zh-CN":"DRAFT → REVIEW → APPROVED → ACTIVE → SUPERSEDED → RETIRED。Active Criteria 为不可变版本；任何修改都必须建立新的批准版本，并完成 Impact、Approval 与受影响 Task 的重新验证。此视觉层不硬编码任何 Threshold。",en:"DRAFT → REVIEW → APPROVED → ACTIVE → SUPERSEDED → RETIRED. Active criteria is immutable; changes require a new approved version, Impact, Approval and affected-task revalidation. No threshold is hardcoded in this visual layer."},
  openDrawer: {"zh-TW":"開啟","zh-CN":"打开",en:"Open"},
  actionDock: {"zh-TW":"SG-02 操作區","zh-CN":"SG-02 操作区",en:"SG-02 Action Dock"},
  qualityCriteriaGatePolicy: {"zh-TW":"QA Criteria / Gate Policy","zh-CN":"QA Criteria / Gate Policy",en:"Quality Criteria / Gate Policy"},
  closeDrawer: {"zh-TW":"關閉詳細資料","zh-CN":"关闭详细数据",en:"Close detail drawer"},
  detailDrawer: {"zh-TW":"SG-02 詳細資料","zh-CN":"SG-02 详细数据",en:"SG-02 Detail Drawer"},
  close: {"zh-TW":"關閉","zh-CN":"关闭",en:"Close"},
  registeredDetailSurface: {"zh-TW":"已註冊 SECTION_OPEN / getUiProjection 詳細資料介面","zh-CN":"已注册 SECTION_OPEN / getUiProjection 详细数据界面",en:"Registered SECTION_OPEN / getUiProjection detail surface"},
  resourceType: {"zh-TW":"資源類型 / resource_type","zh-CN":"资源类型 / resource_type",en:"Resource Type / resource_type"},
  resourceId: {"zh-TW":"資源 ID / resource_id","zh-CN":"资源 ID / resource_id",en:"Resource ID / resource_id"},
  configPatch: {"zh-TW":"設定 Patch / config_patch_json","zh-CN":"设置 Patch / config_patch_json",en:"Configuration Patch / config_patch_json"},
  reason: {"zh-TW":"原因 / reason","zh-CN":"原因 / reason",en:"Reason / reason"},
  rationale: {"zh-TW":"核准理由 / rationale","zh-CN":"批准理由 / rationale",en:"Rationale / rationale"},
  expectedResourceVersion: {"zh-TW":"預期資源版本 / expected_resource_version","zh-CN":"预期资源版本 / expected_resource_version",en:"Expected Resource Version / expected_resource_version"},
  authorizedProjection: {"zh-TW":"已授權 read-model 投影","zh-CN":"已授权 read-model 投影",en:"Authorized read-model projection"},
  currentVersionState: {"zh-TW":"目前版本 / 狀態","zh-CN":"当前版本 / 状态",en:"Current version / state"},
  auditImpactApprovalRef: {"zh-TW":"Audit / Impact / Approval 參照","zh-CN":"Audit / Impact / Approval 引用",en:"Audit / Impact / Approval reference"},
} satisfies Record<string, Entry>;

export type QaCriteriaTextKey = keyof typeof QA_CRITERIA_TEXT;
export function qaCriteriaText(locale: Locale, key: QaCriteriaTextKey): string { return QA_CRITERIA_TEXT[key][locale]; }

export const QA_SECTION_LABELS: Record<string, Entry> = {
  criteria_table:{"zh-TW":"Criteria 表格","zh-CN":"Criteria 表格",en:"Criteria Table"},
  dimension_library:{"zh-TW":"Dimension 資料庫","zh-CN":"Dimension 数据库",en:"Dimension Library"},
  thresholds:{"zh-TW":"Threshold 設定","zh-CN":"Threshold 设置",en:"Thresholds"},
  department_mapping:{"zh-TW":"部門對應","zh-CN":"部门映射",en:"Department Mapping"},
  required_checks:{"zh-TW":"必要檢查","zh-CN":"必要检查",en:"Required Checks"},
  gate_policy:{"zh-TW":"Gate Policy","zh-CN":"Gate Policy",en:"Gate Policy"},
  approval:{"zh-TW":"核准","zh-CN":"批准",en:"Approval"},
  impact:{"zh-TW":"Impact / 重新驗證","zh-CN":"Impact / 重新验证",en:"Impact / Revalidation"},
};
export function qaSectionLabel(locale: Locale, key: string): string { return QA_SECTION_LABELS[key][locale]; }
