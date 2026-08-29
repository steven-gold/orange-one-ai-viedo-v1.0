"use client";

import { useEffect, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import styles from "./DashboardVisual.module.css";

type SectionKind = "kpi" | "kpi-progress" | "project" | "company-progress" | "production" | "notifications" | "information" | "recent";
type VisualState = "EMPTY" | "LOADING" | "ERROR";

type DashboardSection = {
  order: number;
  sectionId: string;
  componentUid: string;
  key: string;
  titleKey: TranslationKey;
  controlId: string;
  controlKey: TranslationKey;
  kind: SectionKind;
};

const SECTIONS: readonly DashboardSection[] = [
  { order: 1, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-PROJECT-COUNT", key: "company_project_count", titleKey: "wb01.section.company_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT-OPEN", controlKey: "wb01.control.company_project_count_open", kind: "kpi" },
  { order: 2, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-RUNNING", key: "company_running_project_count", titleKey: "wb01.section.company_running_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT-OPEN", controlKey: "wb01.control.company_running_project_count_open", kind: "kpi" },
  { order: 3, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT", componentUid: "WB-01-CMP-KPI-PENDING-ACTION", key: "company_pending_action_count", titleKey: "wb01.section.company_pending_action_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT-OPEN", controlKey: "wb01.control.company_pending_action_count_open", kind: "kpi" },
  { order: 4, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT", componentUid: "WB-01-CMP-KPI-PENDING-REVIEW", key: "company_pending_review_count", titleKey: "wb01.section.company_pending_review_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT-OPEN", controlKey: "wb01.control.company_pending_review_count_open", kind: "kpi" },
  { order: 5, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-COMPLETED", key: "company_completed_project_count", titleKey: "wb01.section.company_completed_project_count", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT-OPEN", controlKey: "wb01.control.company_completed_project_count_open", kind: "kpi" },
  { order: 6, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS", componentUid: "WB-01-CMP-KPI-AVERAGE-PROGRESS", key: "company_average_progress", titleKey: "wb01.section.company_average_progress", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS-OPEN", controlKey: "wb01.control.company_average_progress_open", kind: "kpi-progress" },
  { order: 7, sectionId: "SEC-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW", componentUid: "WB-01-CMP-PROJECT-PROGRESS", key: "project_progress_overview", titleKey: "wb01.section.project_progress_overview", controlId: "CTRL-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW-OPEN", controlKey: "wb01.control.project_progress_overview_open", kind: "project" },
  { order: 8, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY", componentUid: "WB-01-CMP-COMPANY-PROGRESS", key: "company_progress_summary", titleKey: "wb01.section.company_progress_summary", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY-OPEN", controlKey: "wb01.control.company_progress_summary_open", kind: "company-progress" },
  { order: 9, sectionId: "SEC-WORKSPACE-WB-01-PRODUCTION-SUMMARY", componentUid: "WB-01-CMP-PRODUCTION-SUMMARY", key: "production_summary", titleKey: "wb01.section.production_summary", controlId: "CTRL-WORKSPACE-WB-01-PRODUCTION-SUMMARY-OPEN", controlKey: "wb01.control.production_summary_open", kind: "production" },
  { order: 10, sectionId: "SEC-WORKSPACE-WB-01-NOTIFICATIONS", componentUid: "WB-01-CMP-NOTIFICATIONS", key: "notifications", titleKey: "wb01.section.notifications", controlId: "CTRL-WORKSPACE-WB-01-NOTIFICATIONS-OPEN", controlKey: "wb01.control.notifications_open", kind: "notifications" },
  { order: 11, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS", componentUid: "WB-01-CMP-ANNOUNCEMENTS", key: "company_announcements", titleKey: "wb01.section.company_announcements", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS-OPEN", controlKey: "wb01.control.company_announcements_open", kind: "information" },
  { order: 12, sectionId: "SEC-WORKSPACE-WB-01-INDUSTRY-NEWS", componentUid: "WB-01-CMP-INDUSTRY-NEWS", key: "industry_news", titleKey: "wb01.section.industry_news", controlId: "CTRL-WORKSPACE-WB-01-INDUSTRY-NEWS-OPEN", controlKey: "wb01.control.industry_news_open", kind: "information" },
  { order: 13, sectionId: "SEC-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY", componentUid: "WB-01-CMP-SYSTEM-STATUS", key: "system_status_summary", titleKey: "wb01.section.system_status_summary", controlId: "CTRL-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY-OPEN", controlKey: "wb01.control.system_status_summary_open", kind: "information" },
  { order: 14, sectionId: "SEC-WORKSPACE-WB-01-RECENT-COMPLETIONS", componentUid: "WB-01-CMP-RECENT-COMPLETIONS", key: "recent_completions", titleKey: "wb01.section.recent_completions", controlId: "CTRL-WORKSPACE-WB-01-RECENT-COMPLETIONS-OPEN", controlKey: "wb01.control.recent_completions_open", kind: "recent" },
] as const;

function EmptyBody({ kind, noData, progressLabel }: { kind: SectionKind; noData: string; progressLabel: string }) {
  if (kind === "kpi") return <div className={styles.kpiValue}>—</div>;
  if (kind === "kpi-progress") {
    return (
      <div className={styles.kpiProgressBody}>
        <div className={styles.kpiValue}>—</div>
        <div className={styles.progressTrack} aria-label={progressLabel}><span className={styles.progressFill} style={{ width: 0 }} /></div>
      </div>
    );
  }
  return <div className={styles.emptyState}>{noData}</div>;
}

function LoadingBody({ kind, loading }: { kind: SectionKind; loading: string }) {
  return (
    <div className={kind.startsWith("kpi") ? styles.loadingKpi : styles.loadingBody} aria-label={loading}>
      <span className={styles.skeletonLine} />
      {!kind.startsWith("kpi") && <span className={styles.skeletonLineShort} />}
    </div>
  );
}

function ErrorBody({ message }: { message: string }) {
  return <div className={styles.errorState}>{message}</div>;
}

export function DashboardVisual() {
  const { t } = useI18n();
  const [drawerSection, setDrawerSection] = useState<DashboardSection | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const openerRef = useRef<HTMLButtonElement | null>(null);
  const state: VisualState = "EMPTY";

  const closeDrawer = () => {
    setDrawerSection(null);
    queueMicrotask(() => openerRef.current?.focus());
  };

  const openDrawer = (section: DashboardSection, trigger: HTMLButtonElement) => {
    openerRef.current = trigger;
    setDrawerSection(section);
  };

  useEffect(() => {
    if (!drawerSection) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDrawer();
        return;
      }
      if (event.key === "Tab") {
        event.preventDefault();
        closeRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerSection]);

  const noData = t("global.state.no_data");
  const loading = t("global.state.loading");
  const loadFailed = t("global.state.load_failed");
  const view = t("global.common.view");
  const close = t("global.common.close");

  return (
    <div className={styles.page} data-page-uid="workspace:WB-01" data-vis-step="VIS-01" aria-label={t("wb01.page.name")}>
      <div className={styles.grid}>
        {SECTIONS.map((section) => {
          const title = t(section.titleKey);
          return (
            <section
              key={section.sectionId}
              className={[styles.card, section.kind === "kpi" || section.kind === "kpi-progress" ? styles.kpiCard : styles[section.kind]].join(" ")}
              data-order={section.order}
              data-section-id={section.sectionId}
              data-component-uid={section.componentUid}
              data-state={state}
            >
              <header className={styles.cardHeader}>
                <h2 className={styles.cardTitle}>{title}</h2>
                <button
                  type="button"
                  className={styles.viewButton}
                  aria-label={t(section.controlKey)}
                  data-control-id={section.controlId}
                  onClick={(event) => openDrawer(section, event.currentTarget)}
                >
                  {view}
                </button>
              </header>
              <div className={styles.cardBody}>
                {state === "LOADING" ? (
                  <LoadingBody kind={section.kind} loading={loading} />
                ) : state === "ERROR" ? (
                  <ErrorBody message={loadFailed} />
                ) : (
                  <EmptyBody kind={section.kind} noData={noData} progressLabel={`${title} — ${noData}`} />
                )}
              </div>
            </section>
          );
        })}
      </div>

      {drawerSection && (
        <div className={styles.drawerLayer} data-component-uid="WB-01-CMP-DRAWER-PROJECTION">
          <button className={styles.backdrop} type="button" aria-label={close} onClick={closeDrawer} />
          <aside className={styles.drawer} role="dialog" aria-modal="true" aria-labelledby="wb01-drawer-title">
            <header className={styles.drawerHeader}>
              <h2 id="wb01-drawer-title" className={styles.drawerTitle}>{t(drawerSection.titleKey)}</h2>
              <button ref={closeRef} className={styles.closeButton} type="button" onClick={closeDrawer}>{close}</button>
            </header>
            <div className={styles.drawerBody}>
              <div className={styles.emptyState}>{noData}</div>
            </div>
            <footer className={styles.drawerFooter}>
              <span>read_model_version: —</span>
              <span>correlation_id: —</span>
            </footer>
          </aside>
        </div>
      )}
    </div>
  );
}
