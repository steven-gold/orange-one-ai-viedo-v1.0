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
} satisfies Record<string, Entry>;

export type QaCriteriaTextKey = keyof typeof QA_CRITERIA_TEXT;
export function qaCriteriaText(locale: Locale, key: QaCriteriaTextKey): string { return QA_CRITERIA_TEXT[key][locale]; }

export const QA_SECTION_LABELS: Record<string, Entry> = {
  criteria_table:{"zh-TW":"Criteria Table","zh-CN":"Criteria Table",en:"Criteria Table"},
  dimension_library:{"zh-TW":"Dimension Library","zh-CN":"Dimension Library",en:"Dimension Library"},
  thresholds:{"zh-TW":"Thresholds","zh-CN":"Thresholds",en:"Thresholds"},
  department_mapping:{"zh-TW":"Department Mapping","zh-CN":"Department Mapping",en:"Department Mapping"},
  required_checks:{"zh-TW":"Required Checks","zh-CN":"Required Checks",en:"Required Checks"},
  gate_policy:{"zh-TW":"Gate Policy","zh-CN":"Gate Policy",en:"Gate Policy"},
  approval:{"zh-TW":"Approval","zh-CN":"Approval",en:"Approval"},
  impact:{"zh-TW":"Impact / Revalidation","zh-CN":"Impact / Revalidation",en:"Impact / Revalidation"},
};
export function qaSectionLabel(locale: Locale, key: string): string { return QA_SECTION_LABELS[key][locale]; }
