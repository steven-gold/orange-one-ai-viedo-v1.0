"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import {
  selectDashboardSection,
  validateDashboardReadModel,
  type DashboardReadError,
  type DashboardReadModel,
  type DashboardSectionKey,
} from "@/domain/dashboard/readModelContract";
import styles from "./DashboardVisual.module.css";

type SectionKind = "kpi" | "kpi-progress" | "project" | "company-progress" | "production" | "notifications" | "information" | "recent";
type VisualState = "EMPTY" | "LOADING" | "ERROR" | "READ_ONLY";

type DashboardSection = {
  order: number;
  sectionId: string;
  componentUid: string;
  key: DashboardSectionKey;
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

const text = (value: unknown): string => value === undefined || value === null || value === "" ? "—" : String(value);
const percent = (value: unknown): string => typeof value === "number" ? `${value}%` : "—";
const displayName = (value: Record<string, unknown>): string => text(value.display_name ?? value.label ?? value.code ?? value.project_id ?? value.topic_id ?? value.task_id);
const hasOwn = (value: object, key: PropertyKey): boolean => Object.prototype.hasOwnProperty.call(value, key);

function duration(value: unknown): string {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) return "—";
  const hours = Math.floor(value / 3600).toString().padStart(3, "0");
  const minutes = Math.floor((value % 3600) / 60).toString().padStart(2, "0");
  const seconds = (value % 60).toString().padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function asRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(asRecord(item))) : [];
}

function ScalarBody({ value, progressLabel, progress = false }: { value: unknown; progressLabel: string; progress?: boolean }) {
  const number = asRecord(value)?.value;
  if (!progress) return <div className={styles.kpiValue}>{text(number)}</div>;
  const width = typeof number === "number" ? Math.max(0, Math.min(100, number)) : 0;
  return (
    <div className={styles.kpiProgressBody}>
      <div className={styles.kpiValue}>{percent(number)}</div>
      <div className={styles.progressTrack} aria-label={progressLabel}><span className={styles.progressFill} style={{ width: `${width}%` }} /></div>
    </div>
  );
}

function ProjectProgress({ value }: { value: unknown }) {
  const projects = asRecords(asRecord(value)?.projects);
  if (!projects.length) return <div className={styles.emptyState}>—</div>;
  return <div>{projects.map((project, projectIndex) => (
    <div key={projectIndex}>
      <strong>{displayName(project)}</strong> · {text(project.status)} · {percent(project.progress_percentage)}
      {asRecords(project.topics).map((topic, topicIndex) => (
        <div key={topicIndex}>↳ {displayName(topic)} · {text(topic.status)} · {percent(topic.progress_percentage)} · {duration(topic.total_operation_time_seconds)}
          {asRecords(topic.tasks).map((task, taskIndex) => <div key={taskIndex}>↳↳ {displayName(task)} · {text(task.task_state)}</div>)}
        </div>
      ))}
    </div>
  ))}</div>;
}

function CompanyProgress({ value, t }: { value: unknown; t: ReturnType<typeof useI18n>["t"] }) {
  const record = asRecord(value);
  if (!record) return <div className={styles.emptyState}>—</div>;
  return <div>
    <div>{percent(record.overall_progress_percentage)}</div>
    <div>{t("wb01.section.company_running_project_count")}: {text(record.running_count)}</div>
    <div>{t("wb01.section.company_pending_action_count")}: {text(record.pending_action_count)}</div>
    <div>{t("wb01.section.company_pending_review_count")}: {text(record.pending_review_count)}</div>
    <div>{t("wb01.section.company_completed_project_count")}: {text(record.completed_count)}</div>
  </div>;
}

function Production({ value, t }: { value: unknown; t: ReturnType<typeof useI18n>["t"] }) {
  const units = asRecords(asRecord(value)?.units);
  if (!units.length) return <div className={styles.emptyState}>—</div>;
  return <div>{units.map((unit, index) => <div key={index}>
    <strong>{text(unit.unit_label)}</strong> · {text(unit.state)} · {t("wb01.section.company_running_project_count")}: {text(unit.running_count)} · {t("wb01.section.company_pending_action_count")}: {text(unit.pending_count)} · {t("wb01.section.company_pending_review_count")}: {text(unit.review_count)} · {t("wb01.section.company_completed_project_count")}: {text(unit.completed_count)}
  </div>)}</div>;
}

function Items({ value, kind }: { value: unknown; kind: "notifications" | "announcements" | "news" | "recent" }) {
  const items = asRecords(asRecord(value)?.items);
  if (!items.length) return <div className={styles.emptyState}>—</div>;
  return <div>{items.map((item, index) => {
    if (kind === "notifications") return <div key={index}><strong>{text(item.title)}</strong> · {text(item.category)} · {text(item.created_at)} · {text(item.read_state)}</div>;
    if (kind === "announcements") return <div key={index}><strong>{text(item.title)}</strong> · {text(item.summary)} · {text(item.published_at)}</div>;
    if (kind === "news") return <div key={index}><strong>{text(item.title)}</strong> · {text(item.source_name)} · {text(item.summary)} · {text(item.published_at)}</div>;
    return <div key={index}>{text(item.project_label)} · {text(item.topic_label)} · {text(item.item_label)} · {text(item.completion_kind)} · {text(item.completed_at)}</div>;
  })}</div>;
}

function SystemStatus({ value }: { value: unknown }) {
  const record = asRecord(value);
  if (!record) return <div className={styles.emptyState}>—</div>;
  return <div><strong>{text(record.overall_status)}</strong><div>{text(record.summary)}</div><div>{text(record.checked_at)}</div></div>;
}

function SectionBody({ section, value, t }: { section: DashboardSection; value: unknown; t: ReturnType<typeof useI18n>["t"] }) {
  const title = t(section.titleKey);
  switch (section.key) {
    case "company_project_count":
    case "company_running_project_count":
    case "company_pending_action_count":
    case "company_pending_review_count":
    case "company_completed_project_count": return <ScalarBody value={value} progressLabel={title} />;
    case "company_average_progress": return <ScalarBody value={value} progressLabel={title} progress />;
    case "project_progress_overview": return <ProjectProgress value={value} />;
    case "company_progress_summary": return <CompanyProgress value={value} t={t} />;
    case "production_summary": return <Production value={value} t={t} />;
    case "notifications": return <Items value={value} kind="notifications" />;
    case "company_announcements": return <Items value={value} kind="announcements" />;
    case "industry_news": return <Items value={value} kind="news" />;
    case "system_status_summary": return <SystemStatus value={value} />;
    case "recent_completions": return <Items value={value} kind="recent" />;
  }
}

function LoadingBody({ kind, loading }: { kind: SectionKind; loading: string }) {
  return <div className={kind.startsWith("kpi") ? styles.loadingKpi : styles.loadingBody} aria-label={loading}><span className={styles.skeletonLine} />{!kind.startsWith("kpi") && <span className={styles.skeletonLineShort} />}</div>;
}

function ErrorBody({ error }: { error: DashboardReadError | null }) {
  return <div className={styles.errorState}>{error ? `${error.error_uid}: ${error.reason_code}` : "—"}</div>;
}

export function DashboardVisual() {
  const { t } = useI18n();
  const [model, setModel] = useState<DashboardReadModel | null>(null);
  const [state, setState] = useState<VisualState>("LOADING");
  const [error, setError] = useState<DashboardReadError | null>(null);
  const [pageDenied, setPageDenied] = useState(false);
  const [drawerSection, setDrawerSection] = useState<DashboardSection | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const openerRef = useRef<HTMLButtonElement | null>(null);

  const readDashboard = useCallback(async (): Promise<DashboardReadModel | null> => {
    let response: Response;
    try {
      response = await fetch("/v1/dashboard/read-model", { method: "GET", cache: "no-store" });
    } catch {
      setError({ error_uid: "WB-01-ERR-READ-001", reason_code: "DASHBOARD_READ_FAILED", correlation_id: "unresolved" });
      return null;
    }
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const readError = asRecord(payload);
      const nextError: DashboardReadError = {
        error_uid: typeof readError?.error_uid === "string" ? readError.error_uid as DashboardReadError["error_uid"] : "WB-01-ERR-READ-001",
        reason_code: typeof readError?.reason_code === "string" ? readError.reason_code : "DASHBOARD_READ_FAILED",
        correlation_id: typeof readError?.correlation_id === "string" ? readError.correlation_id : response.headers.get("x-correlation-id") ?? "unresolved",
      };
      if (response.status === 403) setPageDenied(true);
      setError(nextError);
      return null;
    }
    const validated = validateDashboardReadModel(payload, response.headers.get("x-correlation-id") ?? "unresolved");
    if (!validated.ok) {
      setError(validated.error);
      return null;
    }
    setPageDenied(false);
    setError(null);
    setModel(validated.value);
    return validated.value;
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      setState("LOADING");
      try {
        const next = await readDashboard();
        if (!active) return;
        if (!next) setState("ERROR");
        else setState(SECTIONS.some((section) => hasOwn(next, section.key)) ? "READ_ONLY" : "EMPTY");
      } catch {
        if (!active) return;
        setError({ error_uid: "WB-01-ERR-READ-001", reason_code: "DASHBOARD_READ_FAILED", correlation_id: "unresolved" });
        setState("ERROR");
      }
    })();
    return () => { active = false; };
  }, [readDashboard]);

  const closeDrawer = () => {
    setDrawerSection(null);
    queueMicrotask(() => openerRef.current?.focus());
  };

  const openDrawer = async (section: DashboardSection, trigger: HTMLButtonElement) => {
    openerRef.current = trigger;
    setDrawerSection(section);
    setDrawerLoading(true);
    try { await readDashboard(); } finally { setDrawerLoading(false); }
  };

  useEffect(() => {
    if (!drawerSection) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); closeDrawer(); return; }
      if (event.key === "Tab") { event.preventDefault(); closeRef.current?.focus(); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerSection]);

  if (pageDenied) return null;

  const loading = t("global.state.loading");
  const view = t("global.common.view");
  const close = t("global.common.close");

  if (state === "LOADING") {
    return (
      <div className={styles.page} data-page-uid="workspace:WB-01" data-vis-step="VIS-01" data-state={state} aria-label={t("wb01.page.name")}>
        <div className={styles.emptyState}>{loading}</div>
      </div>
    );
  }

  const visibleSections = model
    ? SECTIONS.filter((section) => hasOwn(model, section.key))
    : state === "ERROR"
      ? SECTIONS
      : [];

  return (
    <div className={styles.page} data-page-uid="workspace:WB-01" data-vis-step="VIS-01" data-state={state} aria-label={t("wb01.page.name")}>
      <div className={styles.grid}>
        {visibleSections.map((section) => {
          const sectionValue = model ? selectDashboardSection(model, section.key) : null;
          return (
            <section key={section.sectionId} className={[styles.card, section.kind === "kpi" || section.kind === "kpi-progress" ? styles.kpiCard : styles[section.kind]].join(" ")} data-order={section.order} data-section-id={section.sectionId} data-component-uid={section.componentUid} data-state={state}>
              <header className={styles.cardHeader}>
                <h2 className={styles.cardTitle}>{t(section.titleKey)}</h2>
                <button type="button" className={styles.viewButton} aria-label={t(section.controlKey)} data-control-id={section.controlId} onClick={(event) => void openDrawer(section, event.currentTarget)}>{view}</button>
              </header>
              <div className={styles.cardBody}>{state === "ERROR" ? <ErrorBody error={error} /> : <SectionBody section={section} value={sectionValue} t={t} />}</div>
            </section>
          );
        })}
      </div>

      {drawerSection && (
        <div className={styles.drawerLayer} data-component-uid="WB-01-CMP-DRAWER-PROJECTION" data-state={drawerLoading ? "LOADING" : error ? "ERROR" : "READ_ONLY"}>
          <button className={styles.backdrop} type="button" aria-label={close} onClick={closeDrawer} />
          <aside className={styles.drawer} role="dialog" aria-modal="true" aria-labelledby="wb01-drawer-title">
            <header className={styles.drawerHeader}>
              <h2 id="wb01-drawer-title" className={styles.drawerTitle}>{t(drawerSection.titleKey)}</h2>
              <button ref={closeRef} className={styles.closeButton} type="button" onClick={closeDrawer}>{close}</button>
            </header>
            <div className={styles.drawerBody}>{drawerLoading ? <LoadingBody kind={drawerSection.kind} loading={loading} /> : error ? <ErrorBody error={error} /> : <SectionBody section={drawerSection} value={model ? selectDashboardSection(model, drawerSection.key) : null} t={t} />}</div>
            <footer className={styles.drawerFooter}>
              <span>read_model_version: {text(model?.read_model_version)}</span>
              <span>correlation_id: {text(model?.correlation_id ?? error?.correlation_id)}</span>
            </footer>
          </aside>
        </div>
      )}
    </div>
  );
}
