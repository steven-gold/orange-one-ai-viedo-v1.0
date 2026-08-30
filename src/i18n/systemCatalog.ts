import type { Locale } from "./catalog";

type Entry = Record<Locale, string>;

export const SYSTEM_CATALOG = {
  pageName: { "zh-TW": "系統 AI 工作區", "zh-CN": "系统 AI 工作区", en: "System Lifecycle AI Workbench" },
  pageRole: { "zh-TW": "統一系統生命週期設計、變更、驗證與稽核工作台", "zh-CN": "统一系统生命周期设计、变更、验证与稽核工作台", en: "Unified system lifecycle design, change, validation and audit workbench" },
  systemContext: { "zh-TW": "系統上下文", "zh-CN": "系统上下文", en: "System Context" },
  conversation: { "zh-TW": "設計對話", "zh-CN": "设计对话", en: "Design Conversation" },
  candidateChange: { "zh-TW": "變更候選", "zh-CN": "变更候选", en: "Candidate Change" },
  sourceRefs: { "zh-TW": "來源引用", "zh-CN": "来源引用", en: "Source References" },
  impactPreview: { "zh-TW": "影響預覽", "zh-CN": "影响预览", en: "Impact Preview" },
  audit: { "zh-TW": "稽核", "zh-CN": "稽核", en: "Audit" },
  actionDock: { "zh-TW": "變更操作", "zh-CN": "变更操作", en: "Change Actions" },
  executionPanel: { "zh-TW": "驗證工作區", "zh-CN": "验证工作区", en: "Validation Workspace" },
  currentTruth: { "zh-TW": "Current System Truth", "zh-CN": "Current System Truth", en: "Current System Truth" },
  activeChange: { "zh-TW": "目前變更", "zh-CN": "当前变更", en: "Active Change" },
  systemVersion: { "zh-TW": "系統版本", "zh-CN": "系统版本", en: "System Version" },
  authority: { "zh-TW": "Active Authorities", "zh-CN": "Active Authorities", en: "Active Authorities" },
  services: { "zh-TW": "Active Services", "zh-CN": "Active Services", en: "Active Services" },
  runtime: { "zh-TW": "Runtime Refs", "zh-CN": "Runtime Refs", en: "Runtime Refs" },
  systemChangeId: { "zh-TW": "SYSTEM_CHANGE_ID", "zh-CN": "SYSTEM_CHANGE_ID", en: "SYSTEM_CHANGE_ID" },
  goal: { "zh-TW": "目標", "zh-CN": "目标", en: "Goal" },
  scope: { "zh-TW": "範圍", "zh-CN": "范围", en: "Scope" },
  candidateRef: { "zh-TW": "Candidate Ref", "zh-CN": "Candidate Ref", en: "Candidate Ref" },
  noData: { "zh-TW": "目前無資料", "zh-CN": "目前无数据", en: "No data" },
  assistant: { "zh-TW": "System AI", "zh-CN": "System AI", en: "System AI" },
  emptyConversation: { "zh-TW": "系統上下文解析完成後，設計對話會在此進行。", "zh-CN": "系统上下文解析完成后，设计对话会在此进行。", en: "Design conversation becomes available after system context is resolved." },
  sourceTypes: { "zh-TW": "Authority / Page / Control / Action / API / Data / Runtime / Permission / Provider / File", "zh-CN": "Authority / Page / Control / Action / API / Data / Runtime / Permission / Provider / File", en: "Authority / Page / Control / Action / API / Data / Runtime / Permission / Provider / File" },
  affectedTypes: { "zh-TW": "Page / Control / Action / API / Data / Runtime / Permission / Provider / File", "zh-CN": "Page / Control / Action / API / Data / Runtime / Permission / Provider / File", en: "Page / Control / Action / API / Data / Runtime / Permission / Provider / File" },
  candidateCreate: { "zh-TW": "建立變更候選", "zh-CN": "建立变更候选", en: "Create Candidate" },
  changeRequestCreate: { "zh-TW": "建立變更請求", "zh-CN": "建立变更请求", en: "Create Change Request" },
  openReference: { "zh-TW": "開啟引用項目", "zh-CN": "开启引用项目", en: "Open Reference" },
  sandboxTest: { "zh-TW": "Sandbox 測試", "zh-CN": "Sandbox 测试", en: "Sandbox Test" },
  validation: { "zh-TW": "Sandbox / Test / Regression / Evidence / Failure", "zh-CN": "Sandbox / Test / Regression / Evidence / Failure", en: "Sandbox / Test / Regression / Evidence / Failure" },
  disabledVisual: { "zh-TW": "視覺施工階段：業務操作尚未啟用", "zh-CN": "视觉施工阶段：业务操作尚未启用", en: "Visual phase: business actions are not enabled" },
  singleAi: { "zh-TW": "Single AI", "zh-CN": "Single AI", en: "Single AI" },
  multiAi: { "zh-TW": "Multi AI", "zh-CN": "Multi AI", en: "Multi AI" },
  discussion: { "zh-TW": "Discussion", "zh-CN": "Discussion", en: "Discussion" },
  parallel: { "zh-TW": "Parallel", "zh-CN": "Parallel", en: "Parallel" },
  auditTrail: { "zh-TW": "Change / Decision / Validation / Evidence", "zh-CN": "Change / Decision / Validation / Evidence", en: "Change / Decision / Validation / Evidence" },
} satisfies Record<string, Entry>;

export type SystemTranslationKey = keyof typeof SYSTEM_CATALOG;
export function systemText(locale: Locale, key: SystemTranslationKey): string {
  return SYSTEM_CATALOG[key][locale];
}
