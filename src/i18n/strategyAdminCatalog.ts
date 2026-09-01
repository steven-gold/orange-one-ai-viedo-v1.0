import type { Locale } from "@/i18n/catalog";

export type StrategyViewKey =
  | "overview"
  | "intelligence"
  | "playbook"
  | "opportunity"
  | "decision";

const COPY = {
  "zh-TW": {
    pageName: "戰略中心後台",
    pageRole: "單頁戰略治理工作台，用於情報、Fact、Playbook、趨勢機會與決策審查。",
    currentView: "目前 View",
    projection: "即時投影",
    value: "值",
    evidence: "來源 / Evidence",
    state: "狀態",
    noData: "目前沒有可顯示的真實投影資料",
    professionalInfo: "專業說明",
    owner: "Owner",
    permission: "權限資源",
    operations: "已註冊 Operations",
    actions: "Governed Actions",
    boundaries: "邊界",
    runtimeBlocked: "Runtime / resource remap 尚未完成，業務操作目前停用。",
    realDataOnly: "只顯示真實資料；缺值統一顯示 —。",
    statusLine: "FINAL_LOCKED · current-only · 單頁工作區 · 僅真實資料",
    summaryLabel: "摘要",
    projectionTable: "投影表格",
    governedActionsLabel: "受治理操作",
    bindingUnresolved: "Authority 的 Action-to-Operation 綁定尚未解析；禁止推測。",
    detailBindingRequired: "必須先有已註冊的 Drawer / Context 詳情綁定。",
    operationAdapterNotReady: "Projection gate 或已註冊 Operation adapter 尚未就緒。",
    views: {
      overview: {
        label: "戰略總覽",
        description: "集中檢視 Intelligence Summary、來源健康度、Fact 品質、Watchlist、風險提醒與候選佇列。",
        boundary: "不得把推論呈現為事實。來源健康度與 Confidence 必須來自已註冊的 Projection / Evidence 邏輯。",
      },
      intelligence: {
        label: "情報與 Fact",
        description: "管理 Source Registry、Watchlist、Scope Policy、品質、Retention、Fact Registry、Cohort、Market Map、Completeness、Confidence 與 Citation。",
        boundary: "所有 Action 必須保留原始 Service / Page / Schema 綁定；禁止推測並合併跨來源 Payload。",
      },
      playbook: {
        label: "平台 Playbook",
        description: "管理平台 Profile、Account Scope、Playbook、Hypothesis、Evidence、版本歷史與 Approval；不得直接作為發布命令。",
        boundary: "Playbook 是受治理的戰略產物，不得作為直接發布命令。",
      },
      opportunity: {
        label: "趨勢與機會",
        description: "檢視 Trend、Momentum、Forecast 與 Opportunity Queue；機會不得自動變更專案或預算。",
        boundary: "Opportunity 不得自動變更專案狀態或預算；Candidate 不等於已核准的戰略決策。",
      },
      decision: {
        label: "決策實驗室",
        description: "比較 Decision Context、候選方案、Evidence、Risk / Cost / Capacity 與 Gate；不得直接寫入 Canon Lock、Task、Budget 或 Publish。",
        boundary: "Decision Lab 不得直接寫入 Canon Lock、Task、Budget 或 Publish；Risk / Cost / Capacity 仍受權限控制，可能 MASK 或 DENY。",
      },
    },
    responsibilities: {
      "Intelligence Summary": "情報摘要",
      "Source Health": "來源健康度",
      "Fact Quality": "Fact 品質",
      Watchlist: "Watchlist",
      "Risk Alert": "風險提醒",
      "Candidate Queue": "候選佇列",
      "Source Registry": "來源 Registry",
      "Scope Policy": "Scope Policy",
      "Source Quality": "來源品質",
      Retention: "Retention",
      "Fact Registry": "Fact Registry",
      "Cohort Builder": "Cohort Builder",
      "Market Map": "Market Map",
      Completeness: "Completeness",
      Confidence: "Confidence",
      Citation: "Citation",
      "Platform Profile": "平台 Profile",
      "Account Scope": "Account Scope",
      Playbook: "Playbook",
      Hypothesis: "Hypothesis",
      Evidence: "Evidence",
      "Version History": "版本歷史",
      Approval: "Approval",
      "Trend Engine": "Trend Engine",
      "Momentum Engine": "Momentum Engine",
      "Forecast Engine": "Forecast Engine",
      "Opportunity Queue": "Opportunity Queue",
      Review: "Review",
      "Decision Context": "Decision Context",
      "Option Comparison": "方案比較",
      "Risk / Cost / Capacity": "Risk / Cost / Capacity",
      "Decision Gate": "Decision Gate",
      "Core Review Handoff": "Core Review Handoff",
      Audit: "Audit",
    },
    actionLabels: {
      "ACT-SEARCH": "搜尋",
      "ACT-REFRESH": "重新整理",
      "ACT-NAV-OPEN": "開啟詳情",
      "ACT-CONFIGURE": "設定",
      "ACT-APPROVE": "核准",
      "ACT-EXPORT": "匯出",
      "ACT-DRAFT-SAVE": "儲存草稿",
      "ACT-CANDIDATE-CREATE": "建立候選",
      "ACT-CANDIDATE-COMPARE": "比較候選",
      "ACT-CANDIDATE-DECIDE": "候選決策",
      "ACT-ADOPT-CONTEXT": "採用為 Context",
    },
  },
  "zh-CN": {
    pageName: "战略中心后台",
    pageRole: "单页战略治理工作台，用于情报、Fact、Playbook、趋势机会与决策审查。",
    currentView: "当前 View",
    projection: "实时投影",
    value: "值",
    evidence: "来源 / Evidence",
    state: "状态",
    noData: "当前没有可显示的真实投影数据",
    professionalInfo: "专业说明",
    owner: "Owner",
    permission: "权限资源",
    operations: "已注册 Operations",
    actions: "Governed Actions",
    boundaries: "边界",
    runtimeBlocked: "Runtime / resource remap 尚未完成，业务操作目前停用。",
    realDataOnly: "只显示真实数据；缺值统一显示 —。",
    statusLine: "FINAL_LOCKED · current-only · 单页工作区 · 仅真实数据",
    summaryLabel: "摘要",
    projectionTable: "投影表格",
    governedActionsLabel: "受治理操作",
    bindingUnresolved: "Authority 的 Action-to-Operation 绑定尚未解析；禁止推测。",
    detailBindingRequired: "必须先有已注册的 Drawer / Context 详情绑定。",
    operationAdapterNotReady: "Projection gate 或已注册 Operation adapter 尚未就绪。",
    views: {
      overview: {
        label: "战略总览",
        description: "集中查看 Intelligence Summary、来源健康度、Fact 质量、Watchlist、风险提醒与候选队列。",
        boundary: "不得把推论呈现为事实。来源健康度与 Confidence 必须来自已注册的 Projection / Evidence 逻辑。",
      },
      intelligence: {
        label: "情报与 Fact",
        description: "管理 Source Registry、Watchlist、Scope Policy、质量、Retention、Fact Registry、Cohort、Market Map、Completeness、Confidence 与 Citation。",
        boundary: "所有 Action 必须保留原始 Service / Page / Schema 绑定；禁止推测并合并跨来源 Payload。",
      },
      playbook: {
        label: "平台 Playbook",
        description: "管理平台 Profile、Account Scope、Playbook、Hypothesis、Evidence、版本历史与 Approval；不得直接作为发布命令。",
        boundary: "Playbook 是受治理的战略产物，不得作为直接发布命令。",
      },
      opportunity: {
        label: "趋势与机会",
        description: "查看 Trend、Momentum、Forecast 与 Opportunity Queue；机会不得自动变更项目或预算。",
        boundary: "Opportunity 不得自动变更项目状态或预算；Candidate 不等于已批准的战略决策。",
      },
      decision: {
        label: "决策实验室",
        description: "比较 Decision Context、候选方案、Evidence、Risk / Cost / Capacity 与 Gate；不得直接写入 Canon Lock、Task、Budget 或 Publish。",
        boundary: "Decision Lab 不得直接写入 Canon Lock、Task、Budget 或 Publish；Risk / Cost / Capacity 仍受权限控制，可能 MASK 或 DENY。",
      },
    },
    responsibilities: {
      "Intelligence Summary": "情报摘要",
      "Source Health": "来源健康度",
      "Fact Quality": "Fact 质量",
      Watchlist: "Watchlist",
      "Risk Alert": "风险提醒",
      "Candidate Queue": "候选队列",
      "Source Registry": "来源 Registry",
      "Scope Policy": "Scope Policy",
      "Source Quality": "来源质量",
      Retention: "Retention",
      "Fact Registry": "Fact Registry",
      "Cohort Builder": "Cohort Builder",
      "Market Map": "Market Map",
      Completeness: "Completeness",
      Confidence: "Confidence",
      Citation: "Citation",
      "Platform Profile": "平台 Profile",
      "Account Scope": "Account Scope",
      Playbook: "Playbook",
      Hypothesis: "Hypothesis",
      Evidence: "Evidence",
      "Version History": "版本历史",
      Approval: "Approval",
      "Trend Engine": "Trend Engine",
      "Momentum Engine": "Momentum Engine",
      "Forecast Engine": "Forecast Engine",
      "Opportunity Queue": "Opportunity Queue",
      Review: "Review",
      "Decision Context": "Decision Context",
      "Option Comparison": "方案比较",
      "Risk / Cost / Capacity": "Risk / Cost / Capacity",
      "Decision Gate": "Decision Gate",
      "Core Review Handoff": "Core Review Handoff",
      Audit: "Audit",
    },
    actionLabels: {
      "ACT-SEARCH": "搜索",
      "ACT-REFRESH": "刷新",
      "ACT-NAV-OPEN": "打开详情",
      "ACT-CONFIGURE": "设置",
      "ACT-APPROVE": "批准",
      "ACT-EXPORT": "导出",
      "ACT-DRAFT-SAVE": "保存草稿",
      "ACT-CANDIDATE-CREATE": "创建候选",
      "ACT-CANDIDATE-COMPARE": "比较候选",
      "ACT-CANDIDATE-DECIDE": "候选决策",
      "ACT-ADOPT-CONTEXT": "采用为 Context",
    },
  },
  en: {
    pageName: "Strategy Center Administration",
    pageRole: "Single-page strategy governance workspace for intelligence, Fact, Playbook, opportunities and decision review.",
    currentView: "Current View",
    projection: "Live Projection",
    value: "Value",
    evidence: "Source / Evidence",
    state: "State",
    noData: "No authoritative projection data is currently available",
    professionalInfo: "Professional Description",
    owner: "Owner",
    permission: "Permission Resource",
    operations: "Registered Operations",
    actions: "Governed Actions",
    boundaries: "Boundaries",
    runtimeBlocked: "Runtime / resource remap is not complete; business actions are disabled.",
    realDataOnly: "Authoritative real data only; missing values render as —.",
    statusLine: "FINAL_LOCKED · current-only · single-page workspace · real data only",
    summaryLabel: "Summary",
    projectionTable: "Projection Table",
    governedActionsLabel: "Governed Actions",
    bindingUnresolved: "Authority action-to-operation binding is unresolved; do not infer.",
    detailBindingRequired: "A registered Drawer / Context detail binding is required.",
    operationAdapterNotReady: "Projection gate or registered Operation adapter is not ready.",
    views: {
      overview: {
        label: "Strategy Overview",
        description: "Reviews Intelligence Summary, Source Health, Fact Quality, Watchlist, Risk Alert and Candidate Queue.",
        boundary: "Never present inference as fact. Source Health and Confidence must come from registered Projection / Evidence logic.",
      },
      intelligence: {
        label: "Intelligence & Fact",
        description: "Governs Source Registry, Watchlist, Scope Policy, quality, Retention, Fact Registry, Cohort, Market Map, Completeness, Confidence and Citation.",
        boundary: "Actions must retain their originating Service / Page / Schema binding. Cross-source payload union inference is forbidden.",
      },
      playbook: {
        label: "Platform Playbook",
        description: "Governs Platform Profile, Account Scope, Playbook, Hypothesis, Evidence, Version History and Approval; a playbook is not a direct publish command.",
        boundary: "Playbook is a governed strategy artifact and must not be used as a direct publish command.",
      },
      opportunity: {
        label: "Trends & Opportunity",
        description: "Reviews Trend, Momentum, Forecast and Opportunity Queue; opportunity cannot automatically change project or budget.",
        boundary: "Opportunity cannot automatically change project state or budget. Candidate does not equal an approved strategy decision.",
      },
      decision: {
        label: "Decision Lab",
        description: "Compares Decision Context, options, Evidence, Risk / Cost / Capacity and Decision Gate; it cannot directly write Canon Lock, Task, Budget or Publish state.",
        boundary: "Decision Lab cannot directly write Canon Lock, Task, Budget or Publish state. Risk / Cost / Capacity remains permission-gated and may MASK or DENY.",
      },
    },
    responsibilities: {} as Record<string, string>,
    actionLabels: {
      "ACT-SEARCH": "Search",
      "ACT-REFRESH": "Refresh",
      "ACT-NAV-OPEN": "Open details",
      "ACT-CONFIGURE": "Configure",
      "ACT-APPROVE": "Approve",
      "ACT-EXPORT": "Export",
      "ACT-DRAFT-SAVE": "Save draft",
      "ACT-CANDIDATE-CREATE": "Create candidate",
      "ACT-CANDIDATE-COMPARE": "Compare candidates",
      "ACT-CANDIDATE-DECIDE": "Candidate decision",
      "ACT-ADOPT-CONTEXT": "Adopt as Context",
    } as Record<string, string>,
  },
} as const;

const ZH_TW = COPY["zh-TW"];

export function strategyText(
  locale: Locale,
  key: Exclude<
    keyof typeof ZH_TW,
    "views" | "responsibilities" | "actionLabels"
  >,
): string {
  return String(COPY[locale][key]);
}

export function strategyViewCopy(locale: Locale, key: StrategyViewKey) {
  return COPY[locale].views[key];
}

export function strategyResponsibility(locale: Locale, source: string): string {
  if (locale === "en") return source;
  const translated = COPY[locale].responsibilities as Record<string, string>;
  return (
    translated[source] ||
    (ZH_TW.responsibilities as Record<string, string>)[source] ||
    source
  );
}

export function strategyActionLabel(locale: Locale, actionId: string): string {
  const translated = COPY[locale].actionLabels as Record<string, string>;
  return (
    translated[actionId] ||
    (ZH_TW.actionLabels as Record<string, string>)[actionId] ||
    actionId
  );
}
