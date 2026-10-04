"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import {
  DashboardClientError,
  fetchDashboardReadModel,
  openDashboardSection,
  type DashboardSectionValue,
} from "@/lib/client";
import { displayDashboardValue, isDashboardEmpty } from "./dashboardFormat";
import { SectionDrawer } from "./SectionDrawer";
import styles from "./DashboardVisual.module.css";

type SectionKind =
  | "kpi"
  | "kpi-progress"
  | "project"
  | "company-progress"
  | "production"
  | "notifications"
  | "information"
  | "recent";

type DashboardSection = {
  order: number;
  sectionId: string;
  componentUid: string;
  titleKey: TranslationKey;
  controlId: string;
  kind: SectionKind;
};

const SECTIONS: readonly DashboardSection[] = [
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

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

export function DashboardVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [sections, setSections] = useState<DashboardSectionValue[]>([]);
  const [openSectionUid, setOpenSectionUid] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchDashboardReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setSections(model.sections);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof DashboardClientError ? cause.code : "DASHBOARD_READ_UNAVAILABLE");
        setAuthorized(false);
        setSections([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const valueOf = useCallback(
    (sectionUid: string) => sections.find((row) => row.sectionUid === sectionUid),
    [sections],
  );

  const open = useCallback(async (sectionUid: string, controlUid: string) => {
    setOpenSectionUid(sectionUid);
    try {
      await openDashboardSection(DEFAULT_ACCOUNT, sectionUid, controlUid, DEFAULT_SESSION);
    } catch {
      // SECTION_OPEN remains readable even if the audit post is unavailable.
    }
  }, []);

  const close = useCallback(() => setOpenSectionUid(null), []);

  const visibleSections = useMemo(() => {
    if (loading) return SECTIONS;
    if (!authorized) return [];
    const allowed = new Set(sections.map((row) => row.sectionUid));
    return SECTIONS.filter((section) => allowed.has(section.componentUid));
  }, [authorized, loading, sections]);

  const openDef = SECTIONS.find((row) => row.componentUid === openSectionUid);
  const openValue = openSectionUid ? valueOf(openSectionUid) : undefined;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";

  return (
    <div
      className={styles.page}
      data-page-uid="workspace:WB-01"
      data-page-state={pageState}
      data-authority-section-count="14"
      data-authority-control-count="14"
      aria-label={t("wb01.page.name")}
    >
      {error ? (
        <div className={styles.errorBanner} role="alert">
          {t("global.state.load_failed")}
        </div>
      ) : null}
      <div className={styles.grid}>
        {visibleSections.map((section) => {
          const row = valueOf(section.componentUid);
          const value = row?.value ?? null;
          const empty = isDashboardEmpty(value, loading);
          const cardState = loading ? "LOADING" : empty ? "EMPTY" : "READY";
          return (
            <section
              key={section.sectionId}
              className={[styles.card, section.kind === "kpi" || section.kind === "kpi-progress" ? styles.kpiCard : styles[section.kind]].join(" ")}
              data-order={section.order}
              data-section-id={section.sectionId}
              data-component-uid={section.componentUid}
              data-state={cardState}
            >
              <header className={styles.cardHeader}>
                <h2 className={styles.cardTitle}>{t(section.titleKey)}</h2>
                <button
                  type="button"
                  className={styles.viewButton}
                  aria-label={t("global.common.view")}
                  data-control-id={section.controlId}
                  onClick={() => void open(section.componentUid, section.controlId)}
                >
                  {t("global.common.view")}
                </button>
              </header>
              <div className={styles.cardBody}>
                <div className={empty || loading ? styles.emptyState : styles.valueState}>
                  {loading ? t("global.state.empty_value") : empty ? t("global.state.no_data") : displayDashboardValue(value, loading)}
                </div>
              </div>
            </section>
          );
        })}
      </div>
      <SectionDrawer
        open={Boolean(openDef)}
        label={openDef ? t(openDef.titleKey) : ""}
        value={openValue?.value ?? null}
        detail={openValue?.detail ?? ""}
        loading={loading}
        onClose={close}
      />
    </div>
  );
}
