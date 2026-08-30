"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import styles from "./DashboardVisual.module.css";

type SectionKind = "kpi" | "kpi-progress" | "project" | "company-progress" | "production" | "notifications" | "information" | "recent";

type DashboardSection = {
  order: number;
  sectionId: string;
  componentUid: string;
  titleKey: string;
  controlId: string;
  controlKey: string;
  kind: SectionKind;
};

const SECTIONS: readonly DashboardSection[] = [
  { order: 1, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-PROJECT-COUNT", titleKey: "wb01.section.company_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT-OPEN", controlKey: "wb01.control.company_project_count_open", kind: "kpi" },
  { order: 2, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-RUNNING", titleKey: "wb01.section.company_running_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT-OPEN", controlKey: "wb01.control.company_running_project_count_open", kind: "kpi" },
  { order: 3, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT", componentUid: "WB-01-CMP-KPI-PENDING-ACTION", titleKey: "wb01.section.company_pending_action_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT-OPEN", controlKey: "wb01.control.company_pending_action_count_open", kind: "kpi" },
  { order: 4, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT", componentUid: "WB-01-CMP-KPI-PENDING-REVIEW", titleKey: "wb01.section.company_pending_review_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT-OPEN", controlKey: "wb01.control.company_pending_review_count_open", kind: "kpi" },
  { order: 5, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-COMPLETED", titleKey: "wb01.section.company_completed_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT-OPEN", controlKey: "wb01.control.company_completed_project_count_open", kind: "kpi" },
  { order: 6, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS", componentUid: "WB-01-CMP-KPI-AVERAGE-PROGRESS", titleKey: "wb01.section.company_average_progress", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS-OPEN", controlKey: "wb01.control.company_average_progress_open", kind: "kpi-progress" },
  { order: 7, sectionId: "SEC-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW", componentUid: "WB-01-CMP-PROJECT-PROGRESS", titleKey: "wb01.section.project_progress_overview", controlId: "CTRL-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW-OPEN", controlKey: "wb01.control.project_progress_overview_open", kind: "project" },
  { order: 8, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY", componentUid: "WB-01-CMP-COMPANY-PROGRESS", titleKey: "wb01.section.company_progress_summary", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY-OPEN", controlKey: "wb01.control.company_progress_summary_open", kind: "company-progress" },
  { order: 9, sectionId: "SEC-WORKSPACE-WB-01-PRODUCTION-SUMMARY", componentUid: "WB-01-CMP-PRODUCTION-SUMMARY", titleKey: "wb01.section.production_summary", controlId: "CTRL-WORKSPACE-WB-01-PRODUCTION-SUMMARY-OPEN", controlKey: "wb01.control.production_summary_open", kind: "production" },
  { order: 10, sectionId: "SEC-WORKSPACE-WB-01-NOTIFICATIONS", componentUid: "WB-01-CMP-NOTIFICATIONS", titleKey: "wb01.section.notifications", controlId: "CTRL-WORKSPACE-WB-01-NOTIFICATIONS-OPEN", controlKey: "wb01.control.notifications_open", kind: "notifications" },
  { order: 11, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS", componentUid: "WB-01-CMP-ANNOUNCEMENTS", titleKey: "wb01.section.company_announcements", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS-OPEN", controlKey: "wb01.control.company_announcements_open", kind: "information" },
  { order: 12, sectionId: "SEC-WORKSPACE-WB-01-INDUSTRY-NEWS", componentUid: "WB-01-CMP-INDUSTRY-NEWS", titleKey: "wb01.section.industry_news", controlId: "CTRL-WORKSPACE-WB-01-INDUSTRY-NEWS-OPEN", controlKey: "wb01.control.industry_news_open", kind: "information" },
  { order: 13, sectionId: "SEC-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY", componentUid: "WB-01-CMP-SYSTEM-STATUS", titleKey: "wb01.section.system_status_summary", controlId: "CTRL-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY-OPEN", controlKey: "wb01.control.system_status_summary_open", kind: "information" },
  { order: 14, sectionId: "SEC-WORKSPACE-WB-01-RECENT-COMPLETIONS", componentUid: "WB-01-CMP-RECENT-COMPLETIONS", titleKey: "wb01.section.recent_completions", controlId: "CTRL-WORKSPACE-WB-01-RECENT-COMPLETIONS-OPEN", controlKey: "wb01.control.recent_completions_open", kind: "recent" },
] as const;

export function DashboardVisual() {
  const { t } = useI18n();
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className={styles.page} data-page-uid="WB-01" data-vis-step="VIS-01" data-page-state="EMPTY">
      <div className={styles.grid}>
        {SECTIONS.map((section) => (
          <section
            key={section.sectionId}
            className={`${styles.card} ${styles[section.kind]}`}
            data-order={section.order}
            data-section-id={section.sectionId}
            data-component-uid={section.componentUid}
          >
            <div className={styles.cardHeader}>
              <h2>{t(section.titleKey as Parameters<typeof t>[0])}</h2>
              <button
                type="button"
                data-control-id={section.controlId}
                onClick={section.order === 7 ? () => setDrawerOpen(true) : undefined}
                disabled={section.order !== 7}
              >
                {t(section.controlKey as Parameters<typeof t>[0])}
              </button>
            </div>

            <div className={styles.cardBody}>
              {section.kind === "kpi" && <div className={styles.kpiValue}>—</div>}
              {section.kind === "kpi-progress" && (
                <div className={styles.kpiProgressBody}>
                  <div className={styles.kpiValue}>—</div>
                  <div className={styles.progressTrack} aria-label={t("wb01.visual.progress_track")}>
                    <span className={styles.progressFill} />
                  </div>
                </div>
              )}
              {!section.kind.startsWith("kpi") && <div className={styles.emptyState}>{t("wb01.state.no_data")}</div>}
            </div>
          </section>
        ))}
      </div>

      {drawerOpen && (
        <div className={styles.drawerBackdrop} data-state="EMPTY" role="presentation" onClick={() => setDrawerOpen(false)}>
          <aside className={styles.drawer} role="dialog" aria-modal="true" data-control-id="CTRL-WORKSPACE-WB-01-PROJECT-PROGRESS-DRAWER">
            <div className={styles.drawerHeader}>
              <h2>{t("wb01.drawer.project_progress")}</h2>
              <button type="button" onClick={() => setDrawerOpen(false)} data-control-id="CTRL-WORKSPACE-WB-01-PROJECT-PROGRESS-DRAWER-CLOSE">
                {t("common.close")}
              </button>
            </div>
            <div className={styles.drawerBody}>{t("wb01.state.no_data")}</div>
          </aside>
        </div>
      )}
    </div>
  );
}
