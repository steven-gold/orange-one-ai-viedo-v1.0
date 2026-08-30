import { CORE_CATALOG, type CoreTranslationKey } from "./coreCatalog";

export type Locale = "zh-TW" | "zh-CN" | "en";

export const LOCALES: readonly Locale[] = ["zh-TW", "zh-CN", "en"] as const;

export const LOCALE_LABELS: Record<Locale, string> = {
  "zh-TW": "繁體中文",
  "zh-CN": "简体中文",
  en: "English",
};

export const LOCALE_HTML_LANG: Record<Locale, string> = {
  "zh-TW": "zh-Hant-TW",
  "zh-CN": "zh-Hans-CN",
  en: "en",
};

const catalog = {
  "global.brand.name": {
    "zh-TW": "ORANGE ONE",
    "zh-CN": "ORANGE ONE",
    en: "ORANGE ONE",
  },
  "global.header.notifications": {
    "zh-TW": "通知",
    "zh-CN": "通知",
    en: "Notification",
  },
  "global.header.todo": {
    "zh-TW": "待辦",
    "zh-CN": "待办",
    en: "To-do",
  },
  "global.header.running": {
    "zh-TW": "執行中",
    "zh-CN": "执行中",
    en: "Running",
  },
  "global.header.language": {
    "zh-TW": "語言",
    "zh-CN": "语言",
    en: "Language",
  },
  "global.header.account": {
    "zh-TW": "帳戶",
    "zh-CN": "账户",
    en: "Account",
  },
  "global.header.admin": {
    "zh-TW": "進入後台",
    "zh-CN": "进入后台",
    en: "Open Admin",
  },
  "global.header.frontend": {
    "zh-TW": "返回前台",
    "zh-CN": "返回前台",
    en: "Back to Front",
  },
  "global.admin.system": {
    "zh-TW": "系統維護",
    "zh-CN": "系统维护",
    en: "System Maintenance",
  },
  "global.admin.iam": {
    "zh-TW": "帳戶與權限",
    "zh-CN": "账户与权限",
    en: "Account & Permission",
  },
  "global.admin.dev": {
    "zh-TW": "企業自動開發系統",
    "zh-CN": "企业自动开发系统",
    en: "Enterprise Automation",
  },
  "global.admin.social": {
    "zh-TW": "社群發布",
    "zh-CN": "社群发布",
    en: "Social Publishing",
  },
  "global.admin.erp": {
    "zh-TW": "ERP",
    "zh-CN": "ERP",
    en: "ERP & Finance",
  },
  "global.admin.aiapi": {
    "zh-TW": "AI API",
    "zh-CN": "AI API",
    en: "AI API",
  },
  "global.admin.qa_criteria": {
    "zh-TW": "QA 評分項目",
    "zh-CN": "QA 评分项目",
    en: "QA Review Criteria",
  },
  "global.admin.strategy": {
    "zh-TW": "戰略中心",
    "zh-CN": "战略中心",
    en: "Strategy Administration",
  },
  "global.admin.knowledge": {
    "zh-TW": "知識庫",
    "zh-CN": "知识库",
    en: "Knowledge & Experience",
  },
  "global.nav.dashboard": {
    "zh-TW": "儀表板",
    "zh-CN": "仪表板",
    en: "Dashboard",
  },
  "global.nav.project_topic": {
    "zh-TW": "專案 / 專題",
    "zh-CN": "项目 / 专题",
    en: "Project / Topic",
  },
  "global.nav.asset": {
    "zh-TW": "素材",
    "zh-CN": "素材",
    en: "Assets",
  },
  "global.nav.video": {
    "zh-TW": "影片",
    "zh-CN": "影片",
    en: "Video",
  },
  "global.nav.edit_voice": {
    "zh-TW": "剪輯配音",
    "zh-CN": "剪辑配音",
    en: "Editing & Voice",
  },
  "global.nav.qa": {
    "zh-TW": "QA",
    "zh-CN": "QA",
    en: "QA",
  },
  "global.nav.database": {
    "zh-TW": "資料庫",
    "zh-CN": "数据库",
    en: "Database",
  },
  "global.nav.strategy": {
    "zh-TW": "戰略中心",
    "zh-CN": "战略中心",
    en: "Strategy Center",
  },
  "global.nav.latest_information": {
    "zh-TW": "最新資訊",
    "zh-CN": "最新资讯",
    en: "Latest Information",
  },
  "global.common.view": {
    "zh-TW": "查看",
    "zh-CN": "查看",
    en: "View",
  },
  "global.common.close": {
    "zh-TW": "關閉",
    "zh-CN": "关闭",
    en: "Close",
  },
  "global.state.loading": {
    "zh-TW": "載入中",
    "zh-CN": "载入中",
    en: "Loading",
  },
  "global.state.no_data": {
    "zh-TW": "目前無資料",
    "zh-CN": "目前无数据",
    en: "No data",
  },
  "global.state.load_failed": {
    "zh-TW": "資料載入失敗",
    "zh-CN": "数据载入失败",
    en: "Data load failed",
  },
  "wb01.page.name": {
    "zh-TW": "儀表板",
    "zh-CN": "仪表板",
    en: "Dashboard",
  },
  "wb01.section.company_project_count": {
    "zh-TW": "專案總數",
    "zh-CN": "专案总数",
    en: "Company Project Count",
  },
  "wb01.section.company_running_project_count": {
    "zh-TW": "執行中",
    "zh-CN": "执行中",
    en: "Running Projects",
  },
  "wb01.section.company_pending_action_count": {
    "zh-TW": "待處理",
    "zh-CN": "待处理",
    en: "Pending Actions",
  },
  "wb01.section.company_pending_review_count": {
    "zh-TW": "待審查",
    "zh-CN": "待审查",
    en: "Pending Reviews",
  },
  "wb01.section.company_completed_project_count": {
    "zh-TW": "已完成",
    "zh-CN": "已完成",
    en: "Completed Projects",
  },
  "wb01.section.company_average_progress": {
    "zh-TW": "平均進度",
    "zh-CN": "平均进度",
    en: "Average Progress",
  },
  "wb01.section.project_progress_overview": {
    "zh-TW": "專案進度",
    "zh-CN": "专案进度",
    en: "Project Progress",
  },
  "wb01.section.company_progress_summary": {
    "zh-TW": "公司整體進度",
    "zh-CN": "公司整体进度",
    en: "Company Progress",
  },
  "wb01.section.production_summary": {
    "zh-TW": "生產總覽",
    "zh-CN": "生产总览",
    en: "Production Summary",
  },
  "wb01.section.notifications": {
    "zh-TW": "通知",
    "zh-CN": "通知",
    en: "Notifications",
  },
  "wb01.section.company_announcements": {
    "zh-TW": "公司公告",
    "zh-CN": "公司公告",
    en: "Company Announcements",
  },
  "wb01.section.industry_news": {
    "zh-TW": "AI / 產業新聞",
    "zh-CN": "AI / 产业新闻",
    en: "AI / Industry News",
  },
  "wb01.section.system_status_summary": {
    "zh-TW": "系統狀態",
    "zh-CN": "系统状态",
    en: "System Status",
  },
  "wb01.section.recent_completions": {
    "zh-TW": "近期完成",
    "zh-CN": "近期完成",
    en: "Recent Completions",
  },
  "wb01.control.company_project_count_open": {
    "zh-TW": "查看專案總數",
    "zh-CN": "查看专案总数",
    en: "View Project Count",
  },
  "wb01.control.company_running_project_count_open": {
    "zh-TW": "查看執行中",
    "zh-CN": "查看执行中",
    en: "View Running Projects",
  },
  "wb01.control.company_pending_action_count_open": {
    "zh-TW": "查看待處理",
    "zh-CN": "查看待处理",
    en: "View Pending Actions",
  },
  "wb01.control.company_pending_review_count_open": {
    "zh-TW": "查看待審查",
    "zh-CN": "查看待审查",
    en: "View Pending Reviews",
  },
  "wb01.control.company_completed_project_count_open": {
    "zh-TW": "查看已完成",
    "zh-CN": "查看已完成",
    en: "View Completed Projects",
  },
  "wb01.control.company_average_progress_open": {
    "zh-TW": "查看平均進度",
    "zh-CN": "查看平均进度",
    en: "View Average Progress",
  },
  "wb01.control.project_progress_overview_open": {
    "zh-TW": "查看專案進度",
    "zh-CN": "查看专案进度",
    en: "View Project Progress",
  },
  "wb01.control.company_progress_summary_open": {
    "zh-TW": "查看公司整體進度",
    "zh-CN": "查看公司整体进度",
    en: "View Company Progress",
  },
  "wb01.control.production_summary_open": {
    "zh-TW": "查看生產總覽",
    "zh-CN": "查看生产总览",
    en: "View Production Summary",
  },
  "wb01.control.notifications_open": {
    "zh-TW": "查看通知",
    "zh-CN": "查看通知",
    en: "View Notifications",
  },
  "wb01.control.company_announcements_open": {
    "zh-TW": "查看公司公告",
    "zh-CN": "查看公司公告",
    en: "View Company Announcements",
  },
  "wb01.control.industry_news_open": {
    "zh-TW": "查看 AI / 產業新聞",
    "zh-CN": "查看 AI / 产业新闻",
    en: "View AI / Industry News",
  },
  "wb01.control.system_status_summary_open": {
    "zh-TW": "查看系統狀態",
    "zh-CN": "查看系统状态",
    en: "View System Status",
  },
  "wb01.control.recent_completions_open": {
    "zh-TW": "查看近期完成",
    "zh-CN": "查看近期完成",
    en: "View Recent Completions",
  },
} as const;

type BaseTranslationKey = keyof typeof catalog;
export type TranslationKey = BaseTranslationKey | CoreTranslationKey;

export function translate(locale: Locale, key: TranslationKey): string {
  if (key in CORE_CATALOG) return CORE_CATALOG[key as CoreTranslationKey][locale];
  return catalog[key as BaseTranslationKey][locale];
}

export function isLocale(value: string | null): value is Locale {
  return value !== null && (LOCALES as readonly string[]).includes(value);
}
