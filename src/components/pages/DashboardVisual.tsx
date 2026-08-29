"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./DashboardVisual.module.css";

type SectionKind = "kpi" | "kpi-progress" | "project" | "company-progress" | "production" | "notifications" | "information" | "recent";
type VisualState = "EMPTY" | "LOADING" | "ERROR";

type DashboardSection = {
  order: number;
  sectionId: string;
  componentUid: string;
  key: string;
  title: string;
  controlId: string;
  controlLabel: string;
  kind: SectionKind;
};

const SECTIONS: readonly DashboardSection[] = [
  { order: 1, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-PROJECT-COUNT", key: "company_project_count", title: "專案總數", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT-OPEN", controlLabel: "查看專案總數", kind: "kpi" },
  { order: 2, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-RUNNING", key: "company_running_project_count", title: "執行中", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT-OPEN", controlLabel: "查看執行中", kind: "kpi" },
  { order: 3, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT", componentUid: "WB-01-CMP-KPI-PENDING-ACTION", key: "company_pending_action_count", title: "待處理", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT-OPEN", controlLabel: "查看待處理", kind: "kpi" },
  { order: 4, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT", componentUid: "WB-01-CMP-KPI-PENDING-REVIEW", key: "company_pending_review_count", title: "待審查", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT-OPEN", controlLabel: "查看待審查", kind: "kpi" },
  { order: 5, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT", componentUid: "WB-01-CMP-KPI-COMPLETED", key: "company_completed_project_count", title: "已完成", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT-OPEN", controlLabel: "查看已完成", kind: "kpi" },
  { order: 6, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS", componentUid: "WB-01-CMP-KPI-AVERAGE-PROGRESS", key: "company_average_progress", title: "平均進度", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS-OPEN", controlLabel: "查看平均進度", kind: "kpi-progress" },
  { order: 7, sectionId: "SEC-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW", componentUid: "WB-01-CMP-PROJECT-PROGRESS", key: "project_progress_overview", title: "專案進度", controlId: "CTRL-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW-OPEN", controlLabel: "查看專案進度", kind: "project" },
  { order: 8, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY", componentUid: "WB-01-CMP-COMPANY-PROGRESS", key: "company_progress_summary", title: "公司整體進度", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY-OPEN", controlLabel: "查看公司整體進度", kind: "company-progress" },
  { order: 9, sectionId: "SEC-WORKSPACE-WB-01-PRODUCTION-SUMMARY", componentUid: "WB-01-CMP-PRODUCTION-SUMMARY", key: "production_summary", title: "生產總覽", controlId: "CTRL-WORKSPACE-WB-01-PRODUCTION-SUMMARY-OPEN", controlLabel: "查看生產總覽", kind: "production" },
  { order: 10, sectionId: "SEC-WORKSPACE-WB-01-NOTIFICATIONS", componentUid: "WB-01-CMP-NOTIFICATIONS", key: "notifications", title: "通知", controlId: "CTRL-WORKSPACE-WB-01-NOTIFICATIONS-OPEN", controlLabel: "查看通知", kind: "notifications" },
  { order: 11, sectionId: "SEC-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS", componentUid: "WB-01-CMP-ANNOUNCEMENTS", key: "company_announcements", title: "公司公告", controlId: "CTRL-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS-OPEN", controlLabel: "查看公司公告", kind: "information" },
  { order: 12, sectionId: "SEC-WORKSPACE-WB-01-INDUSTRY-NEWS", componentUid: "WB-01-CMP-INDUSTRY-NEWS", key: "industry_news", title: "AI / 產業新聞", controlId: "CTRL-WORKSPACE-WB-01-INDUSTRY-NEWS-OPEN", controlLabel: "查看 AI / 產業新聞", kind: "information" },
  { order: 13, sectionId: "SEC-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY", componentUid: "WB-01-CMP-SYSTEM-STATUS", key: "system_status_summary", title: "系統狀態", controlId: "CTRL-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY-OPEN", controlLabel: "查看系統狀態", kind: "information" },
  { order: 14, sectionId: "SEC-WORKSPACE-WB-01-RECENT-COMPLETIONS", componentUid: "WB-01-CMP-RECENT-COMPLETIONS", key: "recent_completions", title: "近期完成", controlId: "CTRL-WORKSPACE-WB-01-RECENT-COMPLETIONS-OPEN", controlLabel: "查看近期完成", kind: "recent" },
] as const;

function EmptyBody({ kind }: { kind: SectionKind }) {
  if (kind === "kpi") return <div className={styles.kpiValue}>—</div>;
  if (kind === "kpi-progress") {
    return (
      <div className={styles.kpiProgressBody}>
        <div className={styles.kpiValue}>—</div>
        <div className={styles.progressTrack} aria-label="平均進度目前無資料"><span className={styles.progressFill} style={{ width: 0 }} /></div>
      </div>
    );
  }
  return <div className={styles.emptyState}>目前無資料</div>;
}

function LoadingBody({ kind }: { kind: SectionKind }) {
  return (
    <div className={kind.startsWith("kpi") ? styles.loadingKpi : styles.loadingBody} aria-label="載入中">
      <span className={styles.skeletonLine} />
      {!kind.startsWith("kpi") && <span className={styles.skeletonLineShort} />}
    </div>
  );
}

function ErrorBody() {
  return <div className={styles.errorState}>資料載入失敗</div>;
}

function DashboardCard({ section, state, onOpen }: { section: DashboardSection; state: VisualState; onOpen: (section: DashboardSection, trigger: HTMLButtonElement) => void }) {
  const isKpi = section.kind === "kpi" || section.kind === "kpi-progress";
  const classNames = [styles.card, isKpi ? styles.kpiCard : styles[section.kind]];

  return (
    <section
      className={classNames.join(" ")}
      data-order={section.order}
      data-section-id={section.sectionId}
      data-component-uid={section.componentUid}
      data-state={state}
    >
      <header className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>{section.title}</h2>
        <button
          type="button"
          className={styles.viewButton}
          aria-label={section.controlLabel}
          data-control-id={section.controlId}
          onClick={(event) => onOpen(section, event.currentTarget)}
        >
          查看
        </button>
      </header>
      <div className={styles.cardBody}>
        {state === "LOADING" ? <LoadingBody kind={section.kind} /> : state === "ERROR" ? <ErrorBody /> : <EmptyBody kind={section.kind} />}
      </div>
    </section>
  );
}

export function DashboardVisual() {
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

  return (
    <div className={styles.page} data-page-uid="workspace:WB-01" data-vis-step="VIS-01" aria-label="儀表板">
      <div className={styles.grid}>
        {SECTIONS.map((section) => <DashboardCard key={section.sectionId} section={section} state={state} onOpen={openDrawer} />)}
      </div>

      {drawerSection && (
        <div className={styles.drawerLayer} data-component-uid="WB-01-CMP-DRAWER-PROJECTION">
          <button className={styles.backdrop} type="button" aria-label="關閉" onClick={closeDrawer} />
          <aside className={styles.drawer} role="dialog" aria-modal="true" aria-labelledby="wb01-drawer-title">
            <header className={styles.drawerHeader}>
              <h2 id="wb01-drawer-title" className={styles.drawerTitle}>{drawerSection.title}</h2>
              <button ref={closeRef} className={styles.closeButton} type="button" onClick={closeDrawer}>關閉</button>
            </header>
            <div className={styles.drawerBody}>
              <div className={styles.emptyState}>目前無資料</div>
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
