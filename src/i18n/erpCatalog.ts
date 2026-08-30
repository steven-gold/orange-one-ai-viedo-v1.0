import type { Locale } from "./catalog";

type Entry = Record<Locale, string>;

export const ERP_TEXT = {
  pageName: { "zh-TW": "ERP", "zh-CN": "ERP", en: "ERP & Finance" },
  pageRole: { "zh-TW": "財務概況、ERP 連接、同步與資料品質的單頁管理工作區", "zh-CN": "财务概况、ERP 连接、同步与数据质量的单页管理工作区", en: "Single-page workspace for finance overview, ERP connection, sync and data quality" },
  finance: { "zh-TW": "財務概況", "zh-CN": "财务概况", en: "Finance Overview" },
  connector: { "zh-TW": "ERP 連接", "zh-CN": "ERP 连接", en: "ERP Connection" },
  sync: { "zh-TW": "同步與資料品質", "zh-CN": "同步与数据质量", en: "Sync & Data Quality" },
  currentView: { "zh-TW": "目前視圖", "zh-CN": "当前视图", en: "Current View" },
  noRealData: { "zh-TW": "目前沒有可顯示的真實 ERP／財務資料", "zh-CN": "目前没有可显示的真实 ERP／财务数据", en: "No real ERP / finance data is available to display" },
  visualPhase: { "zh-TW": "視覺施工階段：ERP Connector、同步、匯出與外部服務動作全部停用。", "zh-CN": "视觉施工阶段：ERP Connector、同步、导出与外部服务动作全部停用。", en: "Visual phase: ERP connector, sync, export and external service mutations are disabled." },
  governance: { "zh-TW": "Readiness / Governance", "zh-CN": "Readiness / Governance", en: "Readiness / Governance" },
  actionDock: { "zh-TW": "目前視圖操作", "zh-CN": "当前视图操作", en: "Current View Actions" },
  financeBoundary: { "zh-TW": "財務視圖只讀／匯出；不得建立收益、費用、Ledger、預算異動或 ERP writeback。", "zh-CN": "财务视图只读／导出；不得建立收益、费用、Ledger、预算变更或 ERP writeback。", en: "Finance is read/export only; revenue, expense, ledger, budget mutations and ERP writeback are forbidden." },
  secretBoundary: { "zh-TW": "僅顯示 Secret Reference ID；不得顯示或儲存 raw secret。", "zh-CN": "仅显示 Secret Reference ID；不得显示或储存 raw secret。", en: "Only Secret Reference ID may be shown; raw secrets must never be rendered or stored." },
  missingBoundary: { "zh-TW": "缺值維持 —／stale／incomplete／error；不得替換成 0 或成功狀態。", "zh-CN": "缺值维持 —／stale／incomplete／error；不得替换成 0 或成功状态。", en: "Missing values remain — / stale / incomplete / error and must never be replaced with zero or success." },
  detail: { "zh-TW": "詳細資料 / Audit", "zh-CN": "详细资料 / Audit", en: "Detail / Audit" },
} satisfies Record<string, Entry>;

export type ErpTextKey = keyof typeof ERP_TEXT;
export function erpText(locale: Locale, key: ErpTextKey): string { return ERP_TEXT[key][locale]; }

export const ERP_CONTROL_LABELS: Record<string, Entry> = {
  "ERP-01-FLD-SCOPE": { "zh-TW": "ERP Scope", "zh-CN": "ERP Scope", en: "ERP Scope" },
  "ERP-01-FLD-SNAPSHOT": { "zh-TW": "Snapshot ID", "zh-CN": "Snapshot ID", en: "Snapshot ID" },
  "ERP-01-FLD-FRESHNESS": { "zh-TW": "資料時間 / Freshness", "zh-CN": "数据时间 / Freshness", en: "Data Time / Freshness" },
  "ERP-01-BTN-TAB-FINANCE": { "zh-TW": "財務概況", "zh-CN": "财务概况", en: "Finance Overview" },
  "ERP-01-BTN-TAB-CONNECTOR": { "zh-TW": "ERP 連接", "zh-CN": "ERP 连接", en: "ERP Connection" },
  "ERP-01-BTN-TAB-SYNC": { "zh-TW": "同步與資料品質", "zh-CN": "同步与数据质量", en: "Sync & Data Quality" },
  "ERP-01-FLD-FIN-COST": { "zh-TW": "成本", "zh-CN": "成本", en: "Cost" },
  "ERP-01-FLD-FIN-REVENUE": { "zh-TW": "收益", "zh-CN": "收益", en: "Revenue" },
  "ERP-01-FLD-FIN-CASHFLOW": { "zh-TW": "現金流", "zh-CN": "现金流", en: "Cashflow" },
  "ERP-01-FLD-FIN-CAPACITY": { "zh-TW": "產能", "zh-CN": "产能", en: "Capacity" },
  "ERP-01-FLD-FIN-FORECAST": { "zh-TW": "Forecast", "zh-CN": "Forecast", en: "Forecast" },
  "ERP-01-FLD-FIN-GUARDRAILS": { "zh-TW": "Guardrails", "zh-CN": "Guardrails", en: "Guardrails" },
  "ERP-01-FLD-FIN-RECOMMENDATION-BOUNDARY": { "zh-TW": "建議邊界", "zh-CN": "建议边界", en: "Recommendation Boundary" },
  "ERP-01-BTN-FACTPACK": { "zh-TW": "取得 Fact Pack", "zh-CN": "获取 Fact Pack", en: "Get Fact Pack" },
  "ERP-01-BTN-GUARDRAILS": { "zh-TW": "取得產能 Guardrails", "zh-CN": "获取产能 Guardrails", en: "Get Capacity Guardrails" },
  "ERP-01-BTN-FORECAST": { "zh-TW": "取得 Forecast", "zh-CN": "获取 Forecast", en: "Get Forecast" },
  "ERP-01-BTN-EXPORT": { "zh-TW": "匯出目前投影", "zh-CN": "导出当前投影", en: "Export Current Projection" },
  "ERP-01-FLD-CONN-CONNECTOR-ID": { "zh-TW": "Connector ID", "zh-CN": "Connector ID", en: "Connector ID" },
  "ERP-01-FLD-CONN-PROVIDER-KEY": { "zh-TW": "Provider Key", "zh-CN": "Provider Key", en: "Provider Key" },
  "ERP-01-FLD-CONN-ADAPTER-KEY": { "zh-TW": "Adapter Key", "zh-CN": "Adapter Key", en: "Adapter Key" },
  "ERP-01-FLD-CONN-SECRET-REFERENCE-ID": { "zh-TW": "Secret Reference ID", "zh-CN": "Secret Reference ID", en: "Secret Reference ID" },
  "ERP-01-FLD-CONN-ENTITY-SCOPE": { "zh-TW": "Entity Scope", "zh-CN": "Entity Scope", en: "Entity Scope" },
  "ERP-01-FLD-CONN-CONNECTION-STATUS": { "zh-TW": "Connection Status", "zh-CN": "Connection Status", en: "Connection Status" },
  "ERP-01-FLD-CONN-MAPPING-VERSION": { "zh-TW": "Mapping Version", "zh-CN": "Mapping Version", en: "Mapping Version" },
  "ERP-01-BTN-CONNECTOR-CREATE": { "zh-TW": "新增 ERP 連接", "zh-CN": "新增 ERP 连接", en: "Create ERP Connection" },
  "ERP-01-BTN-CONNECTOR-UPDATE": { "zh-TW": "更新 ERP 連接", "zh-CN": "更新 ERP 连接", en: "Update ERP Connection" },
  "ERP-01-BTN-CONNECTOR-VALIDATE": { "zh-TW": "驗證 ERP 連接", "zh-CN": "验证 ERP 连接", en: "Validate ERP Connection" },
  "ERP-01-BTN-MAPPING-VALIDATE": { "zh-TW": "驗證 Mapping", "zh-CN": "验证 Mapping", en: "Validate Mapping" },
  "ERP-01-FLD-SYNC-SNAPSHOT-ID": { "zh-TW": "Snapshot ID", "zh-CN": "Snapshot ID", en: "Snapshot ID" },
  "ERP-01-FLD-SYNC-FRESHNESS-AT": { "zh-TW": "Freshness At", "zh-CN": "Freshness At", en: "Freshness At" },
  "ERP-01-FLD-SYNC-CURRENCY-TIMEZONE": { "zh-TW": "幣別 / 時區", "zh-CN": "币别 / 时区", en: "Currency / Timezone" },
  "ERP-01-FLD-SYNC-COMPLETENESS": { "zh-TW": "完整度", "zh-CN": "完整度", en: "Completeness" },
  "ERP-01-FLD-SYNC-LAST-SYNC-STATUS": { "zh-TW": "Last Sync Status", "zh-CN": "Last Sync Status", en: "Last Sync Status" },
  "ERP-01-FLD-SYNC-FAILURE-ID": { "zh-TW": "Failure ID", "zh-CN": "Failure ID", en: "Failure ID" },
  "ERP-01-BTN-SNAPSHOT-REFRESH": { "zh-TW": "更新 Snapshot", "zh-CN": "更新 Snapshot", en: "Refresh Snapshot" },
  "ERP-01-BTN-SYNC-CREATE": { "zh-TW": "建立同步工作", "zh-CN": "建立同步工作", en: "Create Sync Job" },
  "ERP-01-BTN-SYNC-STATUS": { "zh-TW": "查看同步狀態", "zh-CN": "查看同步状态", en: "View Sync Status" },
  "ERP-01-BTN-SYNC-RETRY": { "zh-TW": "重試失敗同步", "zh-CN": "重试失败同步", en: "Retry Failed Sync" },
  "ERP-01-BTN-FAILURE-GET": { "zh-TW": "查看失敗原因", "zh-CN": "查看失败原因", en: "View Failure Reason" },
  "ERP-01-FLD-READINESS": { "zh-TW": "目前狀態 / Blockers", "zh-CN": "当前状态 / Blockers", en: "Current State / Blockers" },
  "ERP-01-FLD-AUDIT-REF": { "zh-TW": "Audit Ref", "zh-CN": "Audit Ref", en: "Audit Ref" },
  "ERP-01-BTN-DETAIL": { "zh-TW": "查看詳細資料 / Audit", "zh-CN": "查看详细资料 / Audit", en: "View Detail / Audit" },
};

export function erpControlLabel(locale: Locale, id: string): string { return ERP_CONTROL_LABELS[id][locale]; }
