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

const CONTROL_ZH: Record<string, string> = {
  "VIEW-OVERVIEW": "知識總覽",
  "VIEW-SOURCE": "來源與蒐集",
  "VIEW-SEARCH": "搜尋 / Citation / Context",
  "VIEW-EXPERIENCE": "Experience / Replay",
  "VIEW-REVIEW": "Knowledge Review",
  "SEARCH-GLOBAL": "搜尋",
  "SOURCE-CREATE": "新增來源",
  "SOURCE-SAVE": "儲存來源設定",
  "SOURCE-PAUSE": "暫停",
  "SOURCE-RESUME": "恢復",
  "SOURCE-RETIRE": "退役",
  "INGEST-START": "開始蒐集 / Ingest",
  "INGEST-RETRY": "重試",
  "SEARCH": "搜尋",
  "CITATION-OPEN": "查看 Citation",
  "CONTEXT-ADD": "加入 Context",
  "CONTEXT-REMOVE": "移除",
  "CONTEXT-CREATE": "建立 Context Candidate",
  "REPLAY-OPEN": "查看 Replay",
  "REPLAY-COMPARE": "比較 Attempt / Version",
  "LEARNING-CREATE": "建立 Learning Candidate",
  "DRAFT-FROM-EXP": "建立 Knowledge Draft",
  "DRAFT-SAVE": "儲存 Draft",
  "VERSION-COMPARE": "比較前版",
  "APPROVE": "核准",
  "RETURN": "退回修改",
  "REJECT": "拒絕",
};

export function knowledgeControlLabel(locale: Locale, suffix: string): string {
  if (locale === "en") return suffix.replaceAll("-", " ");
  return CONTROL_ZH[suffix] || suffix;
}
