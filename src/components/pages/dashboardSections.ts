import type { TranslationKey } from "@/i18n/catalog";

export type SectionKind =
  | "kpi"
  | "kpi-progress"
  | "project"
  | "company-progress"
  | "production"
  | "notifications"
  | "information"
  | "recent";

export type DashboardSection = {
  order: number;
  sectionId: string;
  componentUid: string;
  titleKey: TranslationKey;
  controlId: string;
  kind: SectionKind;
};

export const DASHBOARD_SECTIONS: readonly DashboardSection[] = [
  { order: 1, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-PROJECT-COUNT", titleKey: "wb01.section.company_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT-OPEN", kind: "kpi" },
  { order: 2, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-RUNNING", titleKey: "wb01.section.company_running_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT-OPEN", kind: "kpi" },
  { order: 3, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT", componentUid: "WB-01-CMP-KPI-PENDING-ACTION", titleKey: "wb01.section.company_pending_action_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT-OPEN", kind: "kpi" },
  { order: 4, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT", componentUid: "WB-01-CMP-KPI-PENDING-REVIEW", titleKey: "wb01.section.company_pending_review_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT-OPEN", kind: "kpi" },
  { order: 5, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-COMPLETED", titleKey: "wb01.section.company_completed_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT-OPEN", kind: "kpi" },
  { order: 6, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS", componentUid: "WB-01-CMP-KPI-AVERAGE-PROGRESS", titleKey: "wb01.section.company_average_progress", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS-OPEN", kind: "kpi-progress" },
  { order: 7, sectionId: "SEC-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW", componentUid: "WB-01-CMP-PROJECT-PROGRESS", titleKey: "wb01.section.project_progress_overview", controlId: "CTRL-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW-OPEN", kind: "project" },
  { order: 8, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY", componentUid: "WB-01-CMP-COMPANY-PROGRESS", titleKey: "wb01.section.company_progress_summary", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY-OPEN", kind: "company-progress" },
  { order: 9, sectionId: "SEC-WORKSPACE-WB-01-PRODUCTION-SUMMARY", componentUid: "WB-01-CMP-PRODUCTION-SUMMARY", titleKey: "wb01.section.production_summary", controlId: "CTRL-WORKSPACE-WB-01-PRODUCTION-SUMMARY-OPEN", kind: "production" },
  { order: 10, sectionId: "SEC-WORKSPACE-WB-01-NOTIFICATIONS", componentUid: "WB-01-CMP-NOTIFICATIONS", titleKey: "wb01.section.notifications", controlId: "CTRL-WORKSPACE-WB-01-NOTIFICATIONS-OPEN", kind: "notifications" },
  { order: 11, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS", componentUid: "WB-01-CMP-ANNOUNCEMENTS", titleKey: "wb01.section.company_announcements", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS-OPEN", kind: "information" },
  { order: 12, sectionId: "SEC-WORKSPACE-WB-01-INDUSTRY-NEWS", componentUid: "WB-01-CMP-INDUSTRY-NEWS", titleKey: "wb01.section.industry_news", controlId: "CTRL-WORKSPACE-WB-01-INDUSTRY-NEWS-OPEN", kind: "information" },
  { order: 13, sectionId: "SEC-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY", componentUid: "WB-01-CMP-SYSTEM-STATUS", titleKey: "wb01.section.system_status_summary", controlId: "CTRL-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY-OPEN", kind: "information" },
  { order: 14, sectionId: "SEC-WORKSPACE-WB-01-RECENT-COMPLETIONS", componentUid: "WB-01-CMP-RECENT-COMPLETIONS", titleKey: "wb01.section.recent_completions", controlId: "CTRL-WORKSPACE-WB-01-RECENT-COMPLETIONS-OPEN", kind: "recent" },
];

export const DASHBOARD_HEADER_PEEK = {
  notifications: {
    componentUid: "WB-01-CMP-NOTIFICATIONS",
    controlId: "CTRL-WORKSPACE-WB-01-NOTIFICATIONS-OPEN",
  },
  todo: {
    componentUid: "WB-01-CMP-KPI-PENDING-ACTION",
    controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT-OPEN",
  },
  running: {
    componentUid: "WB-01-CMP-KPI-RUNNING",
    controlId: "CTRL-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT-OPEN",
  },
} as const;

export type DashboardPeekKey = keyof typeof DASHBOARD_HEADER_PEEK;
