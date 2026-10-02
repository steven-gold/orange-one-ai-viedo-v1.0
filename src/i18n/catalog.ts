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
  "global.brand.name": { "zh-TW": "ORANGE ONE", "zh-CN": "ORANGE ONE", en: "ORANGE ONE" },
  "global.shell.header": { "zh-TW": "全域頁首", "zh-CN": "全局页首", en: "Global Header" },
  "global.shell.primary_navigation": { "zh-TW": "主要導航", "zh-CN": "主要导航", en: "Primary Navigation" },
  "global.shell.page_content": { "zh-TW": "頁面內容", "zh-CN": "页面内容", en: "Page Content" },
  "global.shell.workspace": { "zh-TW": "Workspace", "zh-CN": "Workspace", en: "Workspace" },
  "global.header.notifications": { "zh-TW": "通知", "zh-CN": "通知", en: "Notification" },
  "global.header.todo": { "zh-TW": "待辦", "zh-CN": "待办", en: "To-do" },
  "global.header.running": { "zh-TW": "執行中", "zh-CN": "执行中", en: "Running" },
  "global.header.language": { "zh-TW": "語言", "zh-CN": "语言", en: "Language" },
  "global.header.account": { "zh-TW": "帳戶", "zh-CN": "账户", en: "Account" },
  "global.header.admin": { "zh-TW": "後台", "zh-CN": "后台", en: "Admin" },
  "global.header.frontend": { "zh-TW": "前台", "zh-CN": "前台", en: "Frontend" },
  "global.header.login": { "zh-TW": "登入", "zh-CN": "登录", en: "Login" },
  "global.nav.dashboard": { "zh-TW": "儀表板", "zh-CN": "仪表板", en: "Dashboard" },
  "global.nav.project_topic": { "zh-TW": "專案 / 專題", "zh-CN": "项目 / 专题", en: "Project / Topic" },
  "global.nav.asset": { "zh-TW": "素材", "zh-CN": "素材", en: "Assets" },
  "global.nav.video": { "zh-TW": "影片", "zh-CN": "影片", en: "Video" },
  "global.nav.edit_voice": { "zh-TW": "剪輯配音", "zh-CN": "剪辑配音", en: "Editing & Voice" },
  "global.nav.qa": { "zh-TW": "QA", "zh-CN": "QA", en: "QA" },
  "global.nav.database": { "zh-TW": "資料庫", "zh-CN": "数据库", en: "Database" },
  "global.nav.strategy": { "zh-TW": "戰略中心", "zh-CN": "战略中心", en: "Strategy Center" },
  "global.nav.latest_information": { "zh-TW": "最新資訊", "zh-CN": "最新资讯", en: "Latest Information" },
  "global.admin.system": { "zh-TW": "系統維護", "zh-CN": "系统维护", en: "System Maintenance" },
  "global.admin.iam": { "zh-TW": "帳戶與權限", "zh-CN": "账户与权限", en: "Account & Permission" },
  "global.admin.dev": { "zh-TW": "企業自動開發系統", "zh-CN": "企业自动开发系统", en: "Enterprise Automation" },
  "global.admin.social": { "zh-TW": "社群發布", "zh-CN": "社群发布", en: "Social Publishing" },
  "global.admin.erp": { "zh-TW": "ERP", "zh-CN": "ERP", en: "ERP & Finance" },
  "global.admin.aiapi": { "zh-TW": "AI API", "zh-CN": "AI API", en: "AI API" },
  "global.admin.qa_criteria": { "zh-TW": "QA 評分項目", "zh-CN": "QA 评分项目", en: "QA Review Criteria" },
  "global.admin.strategy": { "zh-TW": "戰略中心", "zh-CN": "战略中心", en: "Strategy Administration" },
  "global.admin.knowledge": { "zh-TW": "知識庫", "zh-CN": "知识库", en: "Knowledge & Experience" },
  "global.state.loading": { "zh-TW": "載入中", "zh-CN": "载入中", en: "Loading" },
  "workspace.row1.title": { "zh-TW": "Page Content Row 1", "zh-CN": "Page Content Row 1", en: "Page Content Row 1" },
  "workspace.row1.body": { "zh-TW": "內容區域自適應放大", "zh-CN": "内容区域自适应放大", en: "Content area expands with the workspace" },
  "workspace.row2.title": { "zh-TW": "Page Content Row 2", "zh-CN": "Page Content Row 2", en: "Page Content Row 2" },
  "workspace.row2.body": { "zh-TW": "內容區域同步縮窄／重新排版，不被遮住", "zh-CN": "内容区域同步缩窄／重新排版，不被遮住", en: "Content reflows with the sidebar and is never covered" },
  "workspace.row3.title": { "zh-TW": "Page Content Row 3", "zh-CN": "Page Content Row 3", en: "Page Content Row 3" },
  "workspace.row3.body": { "zh-TW": "Sidebar 與 Workspace 同一 Layout", "zh-CN": "Sidebar 与 Workspace 同一 Layout", en: "Sidebar and workspace share one layout" },
} as const;

export type TranslationKey = keyof typeof catalog;

export function translate(locale: Locale, key: TranslationKey): string {
  return catalog[key][locale];
}

export function isLocale(value: string | null): value is Locale {
  return value !== null && (LOCALES as readonly string[]).includes(value);
}
