import type { Locale } from "@/i18n/catalog";

export type KnowledgeViewKey = "overview" | "source" | "search" | "experience" | "review";

const COPY = {
  "zh-TW": {
    pageName: "知識庫",
    pageRole: "知識來源、蒐集、搜尋 Citation / Context、Experience Replay、Learning 與 Knowledge Review 的單頁治理工作台。",
    currentView: "目前 View",
    authorizedScope: "授權範圍",
    realDataOnly: "僅顯示真實、可追溯資料；缺值統一顯示 —。",
    runtimeBlocked: "Application / API / DB / Crawler Runtime 尚未執行，業務操作目前停用。",
    noData: "目前沒有可顯示的真實資料",
    fields: "Authority Fields",
    controls: "Governed Controls",
    status: "狀態 / Error / Audit",
    source: "來源",
    value: "值",
    eyebrow: "ADMIN · KB-01 · Knowledge / Experience 治理",
    viewLabels: {
      overview: "知識總覽",
      source: "來源與蒐集",
      search: "搜尋 / Citation / Context",
      experience: "Experience / Replay",
      review: "Knowledge Review",
    },
  },
  "zh-CN": {
    pageName: "知识库",
    pageRole: "知识来源、采集、搜索 Citation / Context、Experience Replay、Learning 与 Knowledge Review 的单页治理工作台。",
    currentView: "当前 View",
    authorizedScope: "授权范围",
    realDataOnly: "仅显示真实、可追溯数据；缺值统一显示 —。",
    runtimeBlocked: "Application / API / DB / Crawler Runtime 尚未执行，业务操作目前停用。",
    noData: "当前没有可显示的真实数据",
    fields: "Authority Fields",
    controls: "Governed Controls",
    status: "状态 / Error / Audit",
    source: "来源",
    value: "值",
    eyebrow: "ADMIN · KB-01 · Knowledge / Experience 治理",
    viewLabels: {
      overview: "知识总览",
      source: "来源与采集",
      search: "搜索 / Citation / Context",
      experience: "Experience / Replay",
      review: "Knowledge Review",
    },
  },
  en: {
    pageName: "Knowledge & Experience",
    pageRole: "Single-page governance workspace for knowledge sources, acquisition, search/citation/context, experience replay, learning and knowledge review.",
    currentView: "Current View",
    authorizedScope: "Authorized Scope",
    realDataOnly: "Authoritative traceable real data only; missing values render as —.",
    runtimeBlocked: "Application / API / DB / Crawler Runtime is not executed; business actions are disabled.",
    noData: "No authoritative real data is currently available",
    fields: "Authority Fields",
    controls: "Governed Controls",
    status: "Status / Error / Audit",
    source: "Source",
    value: "Value",
    eyebrow: "ADMIN · KB-01 · KNOWLEDGE & EXPERIENCE GOVERNANCE",
    viewLabels: {
      overview: "Knowledge Overview",
      source: "Sources & Acquisition",
      search: "Search / Citation / Context",
      experience: "Experience / Replay",
      review: "Knowledge Review",
    },
  },
} as const;

export function knowledgeText(locale: Locale, key: Exclude<keyof (typeof COPY)["zh-TW"], "viewLabels">): string {
  return String(COPY[locale][key]);
}

export function knowledgeViewLabel(locale: Locale, key: KnowledgeViewKey): string {
  return COPY[locale].viewLabels[key];
}

const CONTROL_LABELS: Record<string, Record<Locale, string>> = {
  "VIEW-OVERVIEW": {"zh-TW":"知識總覽","zh-CN":"知识总览",en:"Knowledge Overview"},
  "VIEW-SOURCE": {"zh-TW":"來源與蒐集","zh-CN":"来源与采集",en:"Sources & Acquisition"},
  "VIEW-SEARCH": {"zh-TW":"搜尋 / Citation / Context","zh-CN":"搜索 / Citation / Context",en:"Search / Citation / Context"},
  "VIEW-EXPERIENCE": {"zh-TW":"Experience / Replay","zh-CN":"Experience / Replay",en:"Experience / Replay"},
  "VIEW-REVIEW": {"zh-TW":"Knowledge Review","zh-CN":"Knowledge Review",en:"Knowledge Review"},
  "SEARCH-GLOBAL": {"zh-TW":"搜尋","zh-CN":"搜索",en:"Search"},
  "SOURCE-CREATE": {"zh-TW":"新增來源","zh-CN":"新增来源",en:"Add Source"},
  "SOURCE-SAVE": {"zh-TW":"儲存來源設定","zh-CN":"保存来源设置",en:"Save Source Settings"},
  "SOURCE-PAUSE": {"zh-TW":"暫停","zh-CN":"暂停",en:"Pause"},
  "SOURCE-RESUME": {"zh-TW":"恢復","zh-CN":"恢复",en:"Resume"},
  "SOURCE-RETIRE": {"zh-TW":"退役","zh-CN":"退役",en:"Retire"},
  "INGEST-START": {"zh-TW":"開始蒐集 / Ingest","zh-CN":"开始采集 / Ingest",en:"Start Ingestion"},
  "INGEST-RETRY": {"zh-TW":"重試","zh-CN":"重试",en:"Retry"},
  "SEARCH": {"zh-TW":"搜尋","zh-CN":"搜索",en:"Search"},
  "CITATION-OPEN": {"zh-TW":"查看 Citation","zh-CN":"查看 Citation",en:"View Citation"},
  "CONTEXT-ADD": {"zh-TW":"加入 Context","zh-CN":"加入 Context",en:"Add to Context"},
  "CONTEXT-REMOVE": {"zh-TW":"移除","zh-CN":"移除",en:"Remove"},
  "CONTEXT-CREATE": {"zh-TW":"建立 Context Candidate","zh-CN":"建立 Context Candidate",en:"Create Context Candidate"},
  "REPLAY-OPEN": {"zh-TW":"查看 Replay","zh-CN":"查看 Replay",en:"View Replay"},
  "REPLAY-COMPARE": {"zh-TW":"比較 Attempt / Version","zh-CN":"比较 Attempt / Version",en:"Compare Attempt / Version"},
  "LEARNING-CREATE": {"zh-TW":"建立 Learning Candidate","zh-CN":"建立 Learning Candidate",en:"Create Learning Candidate"},
  "DRAFT-FROM-EXP": {"zh-TW":"建立 Knowledge Draft","zh-CN":"建立 Knowledge Draft",en:"Create Knowledge Draft"},
  "DRAFT-SAVE": {"zh-TW":"儲存 Draft","zh-CN":"保存 Draft",en:"Save Draft"},
  "VERSION-COMPARE": {"zh-TW":"比較前版","zh-CN":"比较前版",en:"Compare Previous Version"},
  "APPROVE": {"zh-TW":"核准","zh-CN":"批准",en:"Approve"},
  "RETURN": {"zh-TW":"退回修改","zh-CN":"退回修改",en:"Return for Revision"},
  "REJECT": {"zh-TW":"拒絕","zh-CN":"拒绝",en:"Reject"},
};

const UI_LABELS: Record<string, Record<Locale, string>> = {
  "Summary": {"zh-TW":"摘要","zh-CN":"摘要",en:"Summary"},
  "Source": {"zh-TW":"來源","zh-CN":"来源",en:"Source"},
  "Ingestion": {"zh-TW":"蒐集","zh-CN":"采集",en:"Ingestion"},
  "Experience": {"zh-TW":"Experience","zh-CN":"Experience",en:"Experience"},
  "Review": {"zh-TW":"審查","zh-CN":"审查",en:"Review"},
  "Approved Knowledge": {"zh-TW":"已核准 Knowledge","zh-CN":"已批准 Knowledge",en:"Approved Knowledge"},
  "Page Context / View Navigation": {"zh-TW":"頁面 Context / View 導航","zh-CN":"页面 Context / View 导航",en:"Page Context / View Navigation"},
  "Knowledge Overview": {"zh-TW":"Knowledge 總覽","zh-CN":"Knowledge 总览",en:"Knowledge Overview"},
  "Source Directory": {"zh-TW":"來源目錄","zh-CN":"来源目录",en:"Source Directory"},
  "Source Detail / Governance": {"zh-TW":"來源詳細資料 / 治理","zh-CN":"来源详细数据 / 治理",en:"Source Detail / Governance"},
  "Research / Ingestion Queue": {"zh-TW":"Research / Ingestion 佇列","zh-CN":"Research / Ingestion 队列",en:"Research / Ingestion Queue"},
  "Search / Result Explorer": {"zh-TW":"搜尋 / 結果瀏覽","zh-CN":"搜索 / 结果浏览",en:"Search / Result Explorer"},
  "Citation / Evidence Detail": {"zh-TW":"Citation / Evidence 詳細資料","zh-CN":"Citation / Evidence 详细数据",en:"Citation / Evidence Detail"},
  "Context Candidate Builder": {"zh-TW":"Context Candidate 建立器","zh-CN":"Context Candidate 建立器",en:"Context Candidate Builder"},
  "Experience Directory": {"zh-TW":"Experience 目錄","zh-CN":"Experience 目录",en:"Experience Directory"},
  "Experience Replay": {"zh-TW":"Experience Replay","zh-CN":"Experience Replay",en:"Experience Replay"},
  "Root Cause / Learning Candidate": {"zh-TW":"Root Cause / Learning Candidate","zh-CN":"Root Cause / Learning Candidate",en:"Root Cause / Learning Candidate"},
  "Knowledge Review Queue": {"zh-TW":"Knowledge 審查佇列","zh-CN":"Knowledge 审查队列",en:"Knowledge Review Queue"},
  "Knowledge Draft / Evidence Review": {"zh-TW":"Knowledge Draft / Evidence 審查","zh-CN":"Knowledge Draft / Evidence 审查",en:"Knowledge Draft / Evidence Review"},
  "Version Diff / Supersession": {"zh-TW":"版本差異 / Supersession","zh-CN":"版本差异 / Supersession",en:"Version Diff / Supersession"},
  "Review Decision Rail": {"zh-TW":"審查決策區","zh-CN":"审查决策区",en:"Review Decision Rail"},
  "Status / Error / Audit": {"zh-TW":"狀態 / Error / Audit","zh-CN":"状态 / Error / Audit",en:"Status / Error / Audit"},
  "Page Context Bar": {"zh-TW":"頁面 Context Bar","zh-CN":"页面 Context Bar",en:"Page Context Bar"},
  "Five View Tabs": {"zh-TW":"五個 View 分頁","zh-CN":"五个 View 标签",en:"Five View Tabs"},
  "Knowledge / Experience KPI Summary": {"zh-TW":"Knowledge / Experience KPI 摘要","zh-CN":"Knowledge / Experience KPI 摘要",en:"Knowledge / Experience KPI Summary"},
  "Governance Warning Feed": {"zh-TW":"治理警示 Feed","zh-CN":"治理警示 Feed",en:"Governance Warning Feed"},
  "Source Directory / Filter": {"zh-TW":"來源目錄 / 篩選","zh-CN":"来源目录 / 筛选",en:"Source Directory / Filter"},
  "Source Detail / Configuration": {"zh-TW":"來源詳細資料 / 設定","zh-CN":"来源详细数据 / 设置",en:"Source Detail / Configuration"},
  "Failure / Retry Detail Drawer": {"zh-TW":"失敗 / Retry 詳細資料","zh-CN":"失败 / Retry 详细数据",en:"Failure / Retry Detail Drawer"},
  "Knowledge Search / Filters": {"zh-TW":"Knowledge 搜尋 / 篩選","zh-CN":"Knowledge 搜索 / 筛选",en:"Knowledge Search / Filters"},
  "Search Results": {"zh-TW":"搜尋結果","zh-CN":"搜索结果",en:"Search Results"},
  "ACPOS Context Candidate Basket": {"zh-TW":"ACPOS Context Candidate 清單","zh-CN":"ACPOS Context Candidate 列表",en:"ACPOS Context Candidate Basket"},
  "ACPOS Experience Directory": {"zh-TW":"ACPOS Experience 目錄","zh-CN":"ACPOS Experience 目录",en:"ACPOS Experience Directory"},
  "Experience Replay Timeline / Compare": {"zh-TW":"Experience Replay Timeline / 比較","zh-CN":"Experience Replay Timeline / 比较",en:"Experience Replay Timeline / Compare"},
  "Root Cause / Pattern": {"zh-TW":"Root Cause / Pattern","zh-CN":"Root Cause / Pattern",en:"Root Cause / Pattern"},
  "ACPOS Learning Candidate Draft": {"zh-TW":"ACPOS Learning Candidate Draft","zh-CN":"ACPOS Learning Candidate Draft",en:"ACPOS Learning Candidate Draft"},
  "Knowledge Draft": {"zh-TW":"Knowledge Draft","zh-CN":"Knowledge Draft",en:"Knowledge Draft"},
  "Evidence / Citation / Outcome Validation": {"zh-TW":"Evidence / Citation / Outcome 驗證","zh-CN":"Evidence / Citation / Outcome 验证",en:"Evidence / Citation / Outcome Validation"},
  "Knowledge Version Diff": {"zh-TW":"Knowledge 版本差異","zh-CN":"Knowledge 版本差异",en:"Knowledge Version Diff"},
  "Review Checklist / Decision": {"zh-TW":"審查 Checklist / 決策","zh-CN":"审查 Checklist / 决策",en:"Review Checklist / Decision"},
  "Status / Error / Audit Strip": {"zh-TW":"狀態 / Error / Audit 列","zh-CN":"状态 / Error / Audit 栏",en:"Status / Error / Audit Strip"},
  "fields": {"zh-TW":"欄位","zh-CN":"字段",en:"fields"},
  "registrySummary": {"zh-TW":"27 Controls · 21 Actions · 17 Gates · 14 Errors","zh-CN":"27 Controls · 21 Actions · 17 Gates · 14 Errors",en:"27 Controls · 21 Actions · 17 Gates · 14 Errors"},
  "Authority": {"zh-TW":"Authority","zh-CN":"Authority",en:"Authority"},
  "Application": {"zh-TW":"Application","zh-CN":"Application",en:"Application"},
  "API / DB": {"zh-TW":"API / DB","zh-CN":"API / DB",en:"API / DB"},
  "Crawler / E2E": {"zh-TW":"Crawler / E2E","zh-CN":"Crawler / E2E",en:"Crawler / E2E"},
  "Deploy": {"zh-TW":"部署","zh-CN":"部署",en:"Deploy"},
  "Projection": {"zh-TW":"Projection","zh-CN":"Projection",en:"Projection"},
  "Correlation": {"zh-TW":"關聯","zh-CN":"关联",en:"Correlation"},
  "State / Disabled Reason": {"zh-TW":"狀態 / 停用原因","zh-CN":"状态 / 禁用原因",en:"State / Disabled Reason"},
  "Audit": {"zh-TW":"Audit","zh-CN":"Audit",en:"Audit"},
};

export function knowledgeControlLabel(locale: Locale, suffix: string): string {
  return CONTROL_LABELS[suffix]?.[locale] ?? suffix;
}

export function knowledgeUiLabel(locale: Locale, key: string): string {
  return UI_LABELS[key]?.[locale] ?? key;
}
