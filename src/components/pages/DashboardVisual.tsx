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

type ReadOutcome =
  | { ok: true; model: DashboardReadModel }
  | { ok: false; error: DashboardReadError };

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

const display = (value: unknown): string => value === null || value === undefined || value === "" ? "—" : String(value);
const nameOf = (value: { display_name?: string | null; label?: string | null; code?: string | null; project_id?: string | null; topic_id?: string | null; task_id?: string | null }): string =>
  value.display_name ?? value.label ?? value.code ?? value.project_id ?? value.topic_id ?? value.task_id ?? "—";

function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remain = seconds % 60;
  return `${String(hours).padStart(3, "0")}:${String(minutes).padStart(2, "0")}:${String(remain).padStart(2, "0")}`;
}

async function readDashboard(signal?: AbortSignal): Promise<ReadOutcome> {
  try {
    const response = await fetch("/v1/dashboard/read-model", { method: "GET", cache: "no-store", signal });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const candidate = payload as Partial<DashboardReadError> | null;
      return {
        ok: false,
        error: {
          error_uid: candidate?.error_uid ?? "WB-01-ERR-READ-001",
          reason_code: candidate?.reason_code ?? "DASHBOARD_READ_FAILED",
          correlation_id: candidate?.correlation_id ?? response.headers.get("x-correlation-id") ?? "unresolved",
        } as DashboardReadError,
      };
    }
    const validated = validateDashboardReadModel(payload, response.headers.get("x-correlation-id") ?? "unresolved");
    return validated.ok ? { ok: true, model: validated.value } : validated;
  } catch {
    return { ok: false, error: { error_uid: "WB-01-ERR-READ-001", reason_code: "DASHBOARD_READ_FAILED", correlation_id: "unresolved" } };
  }
}

function hasVisibleData(model: DashboardReadModel): boolean {
  return SECTIONS.some((section) => Object.prototype.hasOwnProperty.call(model, section.key) && selectDashboardSection(model, section.key) !== null);
}

function EmptyBody({ kind, noData, progressLabel }: { kind: SectionKind; noData: string; progressLabel: string }) {
  if (kind === "kpi") return <div className={styles.kpiValue}>—</div>;
  if (kind === "kpi-progress") return <div className={styles.kpiProgressBody}><div className={styles.kpiValue}>—</div><div className={styles.progressTrack} aria-label={progressLabel}><span className={styles.progressFill} style={{ width: 0 }} /></div></div>;
  return <div className={styles.emptyState}>{noData}</div>;
}

function LoadingBody({ kind, loading }: { kind: SectionKind; loading: string }) {
  return <div className={kind.startsWith("kpi") ? styles.loadingKpi : styles.loadingBody} aria-label={loading}><span className={styles.skeletonLine} />{!kind.startsWith("kpi") && <span className={styles.skeletonLineShort} />}</div>;
}

function ErrorBody({ message }: { message: string }) { return <div className={styles.errorState}>{message}</div>; }

function SectionData({ section, value }: { section: DashboardSection; value: unknown }) {
  if (value === null || value === undefined) return null;
  if (section.kind === "kpi" || section.kind === "kpi-progress") {
    const scalar = value as { value?: number | null };
    const current = scalar.value;
    return section.kind === "kpi-progress" ? (
      <div className={styles.kpiProgressBody}>
        <div className={styles.kpiValue}>{current === null || current === undefined ? "—" : `${current}%`}</div>
        <div className={styles.progressTrack}><span className={styles.progressFill} style={{ width: `${current ?? 0}%` }} /></div>
      </div>
    ) : <div className={styles.kpiValue}>{display(current)}</div>;
  }

  if (section.key === "project_progress_overview") {
    const projects = (value as { projects?: Array<any> | null }).projects ?? [];
    return <div className={styles.dataList}>{projects.map((project, pi) => <div className={styles.dataGroup} key={project.project_id ?? `${nameOf(project)}-${pi}`}><div className={styles.dataPrimary}>{nameOf(project)}</div><div className={styles.dataMeta}>{display(project.status)} · {project.progress_percentage === null || project.progress_percentage === undefined ? "—" : `${project.progress_percentage}%`}</div>{(project.topics ?? []).map((topic: any, ti: number) => <div className={styles.dataNested} key={topic.topic_id ?? `${nameOf(topic)}-${ti}`}><div className={styles.dataPrimary}>{nameOf(topic)}</div><div className={styles.dataMeta}>{display(topic.status)} · {topic.progress_percentage === null || topic.progress_percentage === undefined ? "—" : `${topic.progress_percentage}%`} · {duration(topic.total_operation_time_seconds)}</div>{(topic.tasks ?? []).map((task: any, xi: number) => <div className={styles.dataTask} key={task.task_id ?? `${nameOf(task)}-${xi}`}><span>{nameOf(task)}</span><span>{display(task.task_state)}</span></div>)}</div>)}</div>)}</div>;
  }

  if (section.key === "company_progress_summary") {
    const item = value as Record<string, number | null | undefined>;
    const values = [item.overall_progress_percentage, item.running_count, item.pending_action_count, item.pending_review_count, item.completed_count];
    return <div className={styles.metricStrip}>{values.map((entry, index) => <span data-field-index={index} key={index}>{index === 0 && entry !== null && entry !== undefined ? `${entry}%` : display(entry)}</span>)}</div>;
  }

  if (section.key === "production_summary") {
    const units = (value as { units?: Array<any> | null }).units ?? [];
    return <div className={styles.dataList}>{units.map((unit, index) => <div className={styles.dataRow} key={unit.unit_key ?? `${unit.unit_label ?? "unit"}-${index}`}><div><div className={styles.dataPrimary}>{display(unit.unit_label)}</div><div className={styles.dataMeta}>{display(unit.state)}</div></div><div className={styles.dataCounts}><span>{display(unit.running_count)}</span><span>{display(unit.pending_count)}</span><span>{display(unit.review_count)}</span><span>{display(unit.completed_count)}</span></div></div>)}</div>;
  }

  if (section.key === "notifications") {
    const items = (value as { items?: Array<any> | null }).items ?? [];
    return <div className={styles.dataList}>{items.map((item, index) => <div className={styles.dataRow} key={item.notification_id ?? `${item.title ?? "notification"}-${index}`}><div><div className={styles.dataPrimary}>{display(item.title)}</div><div className={styles.dataMeta}>{display(item.category)} · {display(item.created_at)}</div></div><span className={styles.dataMeta}>{display(item.read_state)}</span></div>)}</div>;
  }

  if (section.key === "company_announcements" || section.key === "industry_news") {
    const items = (value as { items?: Array<any> | null }).items ?? [];
    return <div className={styles.dataList}>{items.map((item, index) => <div className={styles.dataGroup} key={item.announcement_id ?? item.news_id ?? `${item.title ?? "item"}-${index}`}><div className={styles.dataPrimary}>{display(item.title)}</div>{section.key === "industry_news" && <div className={styles.dataMeta}>{display(item.source_name)}</div>}<div className={styles.dataSecondary}>{display(item.summary)}</div><div className={styles.dataMeta}>{display(item.published_at)}</div></div>)}</div>;
  }

  if (section.key === "system_status_summary") {
    const item = value as any;
    return <div className={styles.dataGroup}><div className={styles.dataPrimary}>{display(item.overall_status)}</div><div className={styles.dataSecondary}>{display(item.summary)}</div><div className={styles.dataMeta}>{display(item.checked_at)}</div></div>;
  }

  const items = (value as { items?: Array<any> | null }).items ?? [];
  return <div className={styles.dataList}>{items.map((item, index) => <div className={styles.dataRow} key={item.completion_id ?? `${item.item_label ?? "completion"}-${index}`}><div><div className={styles.dataPrimary}>{display(item.item_label)}</div><div className={styles.dataMeta}>{display(item.project_label)} · {display(item.topic_label)} · {display(item.completion_kind)}</div></div><span className={styles.dataMeta}>{display(item.completed_at)}</span></div>)}</div>;
}

export function DashboardVisual() {
  const { t } = useI18n();
  const [state, setState] = useState<VisualState>("LOADING");
  const [model, setModel] = useState<DashboardReadModel | null>(null);
  const [policyDenied, setPolicyDenied] = useState(false);
  const [drawerSection, setDrawerSection] = useState<DashboardSection | null>(null);
  const [drawerState, setDrawerState] = useState<VisualState>("EMPTY");
  const [drawerModel, setDrawerModel] = useState<DashboardReadModel | null>(null);
  const [drawerError, setDrawerError] = useState<DashboardReadError | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const openerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    readDashboard(controller.signal).then((outcome) => {
      if (!outcome.ok) {
        if (outcome.error.error_uid === "WB-01-ERR-POLICY-001") setPolicyDenied(true);
        setState("ERROR");
        return;
      }
      setModel(outcome.model);
      setState(hasVisibleData(outcome.model) ? "READ_ONLY" : "EMPTY");
    });
    return () => controller.abort();
  }, []);

  const closeDrawer = useCallback(() => {
    setDrawerSection(null);
    setDrawerModel(null);
    setDrawerError(null);
    setDrawerState("EMPTY");
    queueMicrotask(() => openerRef.current?.focus());
  }, []);

  const openDrawer = useCallback(async (section: DashboardSection, trigger: HTMLButtonElement) => {
    openerRef.current = trigger;
    setDrawerSection(section);
    setDrawerState("LOADING");
    setDrawerModel(null);
    setDrawerError(null);
    const outcome = await readDashboard();
    if (!outcome.ok) {
      if (outcome.error.error_uid === "WB-01-ERR-POLICY-001") {
        closeDrawer();
        setPolicyDenied(true);
        return;
      }
      setDrawerError(outcome.error);
      setDrawerState("ERROR");
      return;
    }
    setDrawerModel(outcome.model);
    setDrawerState(selectDashboardSection(outcome.model, section.key) === null ? "EMPTY" : "READ_ONLY");
  }, [closeDrawer]);

  useEffect(() => {
    if (!drawerSection) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); closeDrawer(); return; }
      if (event.key === "Tab") { event.preventDefault(); closeRef.current?.focus(); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerSection, closeDrawer]);

  if (policyDenied) return null;

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
          const value = model ? selectDashboardSection(model, section.key) : null;
          return (
            <section key={section.sectionId} className={[styles.card, section.kind === "kpi" || section.kind === "kpi-progress" ? styles.kpiCard : styles[section.kind]].join(" ")} data-order={section.order} data-section-id={section.sectionId} data-component-uid={section.componentUid} data-state={state}>
              <header className={styles.cardHeader}>
                <h2 className={styles.cardTitle}>{title}</h2>
                <button type="button" className={styles.viewButton} aria-label={t(section.controlKey)} data-control-id={section.controlId} disabled={state === "LOADING"} onClick={(event) => void openDrawer(section, event.currentTarget)}>{view}</button>
              </header>
              <div className={styles.cardBody}>
                {state === "LOADING" ? <LoadingBody kind={section.kind} loading={loading} /> : state === "ERROR" ? <ErrorBody message={loadFailed} /> : value === null ? <EmptyBody kind={section.kind} noData={noData} progressLabel={`${title} — ${noData}`} /> : <SectionData section={section} value={value} />}
              </div>
            </section>
          );
        })}
      </div>

      {drawerSection && (
        <div className={styles.drawerLayer} data-component-uid="WB-01-CMP-DRAWER-PROJECTION">
          <button className={styles.backdrop} type="button" aria-label={close} onClick={closeDrawer} />
          <aside className={styles.drawer} role="dialog" aria-modal="true" aria-labelledby="wb01-drawer-title">
            <header className={styles.drawerHeader}><h2 id="wb01-drawer-title" className={styles.drawerTitle}>{t(drawerSection.titleKey)}</h2><button ref={closeRef} className={styles.closeButton} type="button" onClick={closeDrawer}>{close}</button></header>
            <div className={styles.drawerBody}>
              {drawerState === "LOADING" ? <LoadingBody kind={drawerSection.kind} loading={loading} /> : drawerState === "ERROR" ? <div className={styles.errorState}>{drawerError ? `${drawerError.error_uid} · ${drawerError.reason_code}` : loadFailed}</div> : drawerModel && selectDashboardSection(drawerModel, drawerSection.key) !== null ? <SectionData section={drawerSection} value={selectDashboardSection(drawerModel, drawerSection.key)} /> : <div className={styles.emptyState}>{noData}</div>}
            </div>
            <footer className={styles.drawerFooter}><span>read_model_version: {drawerModel?.read_model_version ?? "—"}</span><span>correlation_id: {drawerModel?.correlation_id ?? drawerError?.correlation_id ?? "—"}</span></footer>
          </aside>
        </div>
      )}
    </div>
  );
}
