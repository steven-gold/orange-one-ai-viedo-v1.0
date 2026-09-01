import type { Locale } from "./catalog";

type Entry = Record<Locale, string>;

export const AIAPI_TEXT = {
  pageName: { "zh-TW": "AI API 管理", "zh-CN": "AI API 管理", en: "AI API Management" },
  pageRole: { "zh-TW": "Provider、Model、Capability、路由測試、作業成本與事件的單頁管理工作區", "zh-CN": "Provider、Model、Capability、路由测试、作业成本与事件的单页管理工作区", en: "Single-page management workspace for providers, models, capabilities, route testing, operations, cost and incidents" },
  overview: { "zh-TW": "總覽", "zh-CN": "总览", en: "Overview" },
  provider: { "zh-TW": "Provider / API 設定", "zh-CN": "Provider / API 设置", en: "Provider / API Settings" },
  routing: { "zh-TW": "路由 / 測試", "zh-CN": "路由 / 测试", en: "Routing / Test" },
  operations: { "zh-TW": "作業 / 成本 / 事件", "zh-CN": "作业 / 成本 / 事件", en: "Operations / Cost / Incidents" },
  noData: { "zh-TW": "目前沒有可顯示的真實資料", "zh-CN": "目前没有可显示的真实数据", en: "No real data is available to display" },
  remapBlocked: { "zh-TW": "目前 Control / Permission / Navigation remap 尚未完成；effectful runtime 維持阻擋。", "zh-CN": "当前 Control / Permission / Navigation remap 尚未完成；effectful runtime 维持阻挡。", en: "Control / Permission / Navigation remap is not complete; effectful runtime remains blocked." },
  loading: { "zh-TW": "正在讀取受治理的 AI API 投影", "zh-CN": "正在读取受治理的 AI API 投影", en: "Loading the governed AI API projection" },
  projectionBound: { "zh-TW": "已接上 getUiProjection 讀取路徑", "zh-CN": "已接入 getUiProjection 读取路径", en: "getUiProjection read path is bound" },
  effectfulBlocked: { "zh-TW": "寫入／測試操作尚無 Current exact HTTP binding，依 Authority 維持阻擋。", "zh-CN": "写入／测试操作尚无 Current exact HTTP binding，依 Authority 保持阻挡。", en: "Effectful write/test operations have no Current exact HTTP binding and remain blocked by Authority." },
  correlation: { "zh-TW": "關聯 ID", "zh-CN": "关联 ID", en: "Correlation ID" },
  professional: { "zh-TW": "API 功能專業說明", "zh-CN": "API 功能专业说明", en: "API Professional Description" },
  selectGuidance: { "zh-TW": "選取已登錄 Provider / Model 後顯示真實 Metadata；目前未選取。", "zh-CN": "选择已登记 Provider / Model 后显示真实 Metadata；当前未选择。", en: "Select a registered Provider / Model to display real metadata; none is currently selected." },
  providerTable: { "zh-TW": "Provider / Model Registry", "zh-CN": "Provider / Model Registry", en: "Provider / Model Registry" },
  overviewSummary: { "zh-TW": "真實治理摘要", "zh-CN": "真实治理摘要", en: "Governed Real-Data Summary" },
  routingWorkspace: { "zh-TW": "Routing / Sandbox / Compile Audit", "zh-CN": "Routing / Sandbox / Compile Audit", en: "Routing / Sandbox / Compile Audit" },
  operationsWorkspace: { "zh-TW": "Job / Cost / Incident", "zh-CN": "Job / Cost / Incident", en: "Job / Cost / Incident" },
  secretRule: { "zh-TW": "API Key 僅 write-only 設定；禁止明文顯示、匯出、log、audit 或資料庫保存。", "zh-CN": "API Key 仅 write-only 设置；禁止明文显示、导出、log、audit 或数据库保存。", en: "API keys are write-only; plaintext reveal, export, logging, audit and database persistence are forbidden." },
} satisfies Record<string, Entry>;

export type AiApiTextKey = keyof typeof AIAPI_TEXT;
export function aiApiText(locale: Locale, key: AiApiTextKey): string { return AIAPI_TEXT[key][locale]; }

export const AIAPI_PRO_FIELDS: readonly [string, Entry][] = [
  ["AIAPI-01-PRO-DESC-IDENTITY", {"zh-TW":"API / Model 身分","zh-CN":"API / Model 身份",en:"API / Model Identity"}],
  ["AIAPI-01-PRO-DESC-POSITIONING", {"zh-TW":"功能定位","zh-CN":"功能定位",en:"Functional Positioning"}],
  ["AIAPI-01-PRO-DESC-ACPOS-SCOPE", {"zh-TW":"ACPOS 使用範圍","zh-CN":"ACPOS 使用范围",en:"ACPOS Scope"}],
  ["AIAPI-01-PRO-DESC-CAPABILITIES", {"zh-TW":"支援能力","zh-CN":"支持能力",en:"Capabilities"}],
  ["AIAPI-01-PRO-DESC-INPUT", {"zh-TW":"輸入要求","zh-CN":"输入要求",en:"Input Requirements"}],
  ["AIAPI-01-PRO-DESC-OUTPUT", {"zh-TW":"輸出內容","zh-CN":"输出内容",en:"Output Content"}],
  ["AIAPI-01-PRO-DESC-LIMITS", {"zh-TW":"限制","zh-CN":"限制",en:"Limits"}],
  ["AIAPI-01-PRO-DESC-ENDPOINT", {"zh-TW":"Endpoint / Method","zh-CN":"Endpoint / Method",en:"Endpoint / Method"}],
  ["AIAPI-01-PRO-DESC-AUTH", {"zh-TW":"認證","zh-CN":"认证",en:"Authentication"}],
  ["AIAPI-01-PRO-DESC-BILLING", {"zh-TW":"計費基準","zh-CN":"计费基准",en:"Billing Basis"}],
  ["AIAPI-01-PRO-DESC-HEALTH", {"zh-TW":"健康狀態","zh-CN":"健康状态",en:"Health"}],
  ["AIAPI-01-PRO-DESC-LAST-TEST", {"zh-TW":"最近測試","zh-CN":"最近测试",en:"Last Test"}],
  ["AIAPI-01-PRO-DESC-RECOMMENDED-USE", {"zh-TW":"推薦用途","zh-CN":"推荐用途",en:"Recommended Use"}],
  ["AIAPI-01-PRO-DESC-RESTRICTIONS", {"zh-TW":"不適用／限制","zh-CN":"不适用／限制",en:"Restrictions"}],
  ["AIAPI-01-PRO-DESC-DOCS", {"zh-TW":"官方／內部文件","zh-CN":"官方／内部文件",en:"Official / Internal Docs"}],
] as const;

export function aiApiProLabel(locale: Locale, entry: Entry): string { return entry[locale]; }
