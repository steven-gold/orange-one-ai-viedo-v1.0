export const DASHBOARD_PERMISSION = "workspace.dashboard.view";
export const DASHBOARD_PAGE_UID = "workspace:WB-01";
export const DASHBOARD_ROUTE = "/";
export const DASHBOARD_PROJECTION = "CompanyDashboardProjection";
export const DASHBOARD_CHAIN = "WB-01-FWC-DASHBOARD-READ-01";

export interface DashboardSectionSeed {
  sectionUid: string;
  controlUid: string;
  label: string;
}

export const DASHBOARD_SECTION_SEEDS: DashboardSectionSeed[] = [
  { sectionUid: "WB-01-CMP-KPI-PROJECT-COUNT", controlUid: "CTRL-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT-OPEN", label: "專案總數" },
  { sectionUid: "WB-01-CMP-KPI-RUNNING", controlUid: "CTRL-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT-OPEN", label: "執行中" },
  { sectionUid: "WB-01-CMP-KPI-PENDING-ACTION", controlUid: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT-OPEN", label: "待處理" },
  { sectionUid: "WB-01-CMP-KPI-PENDING-REVIEW", controlUid: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT-OPEN", label: "待審查" },
  { sectionUid: "WB-01-CMP-KPI-COMPLETED", controlUid: "CTRL-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT-OPEN", label: "已完成" },
  { sectionUid: "WB-01-CMP-KPI-AVERAGE-PROGRESS", controlUid: "CTRL-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS-OPEN", label: "平均進度" },
  { sectionUid: "WB-01-CMP-PROJECT-PROGRESS", controlUid: "CTRL-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW-OPEN", label: "專案進度" },
  { sectionUid: "WB-01-CMP-COMPANY-PROGRESS", controlUid: "CTRL-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY-OPEN", label: "公司整體進度" },
  { sectionUid: "WB-01-CMP-PRODUCTION-SUMMARY", controlUid: "CTRL-WORKSPACE-WB-01-PRODUCTION-SUMMARY-OPEN", label: "生產總覽" },
  { sectionUid: "WB-01-CMP-NOTIFICATIONS", controlUid: "CTRL-WORKSPACE-WB-01-NOTIFICATIONS-OPEN", label: "通知" },
  { sectionUid: "WB-01-CMP-ANNOUNCEMENTS", controlUid: "CTRL-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS-OPEN", label: "公司公告" },
  { sectionUid: "WB-01-CMP-INDUSTRY-NEWS", controlUid: "CTRL-WORKSPACE-WB-01-INDUSTRY-NEWS-OPEN", label: "AI / 產業新聞" },
  { sectionUid: "WB-01-CMP-SYSTEM-STATUS", controlUid: "CTRL-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY-OPEN", label: "系統狀態" },
  { sectionUid: "WB-01-CMP-RECENT-COMPLETIONS", controlUid: "CTRL-WORKSPACE-WB-01-RECENT-COMPLETIONS-OPEN", label: "近期完成" },
];
