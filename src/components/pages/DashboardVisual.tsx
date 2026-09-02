"use client";

import { useEffect, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import type { DashboardReadError, DashboardReadModel, DashboardSectionKey } from "@/domain/dashboard/readModelContract";
import { selectDashboardSection } from "@/domain/dashboard/readModelContract";
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

const dash = (v: unknown) => v === null || v === undefined || v === "" ? "—" : String(v);
const pct = (v: unknown) => typeof v === "number" ? `${v}%` : "—";
const time = (v: unknown) => {
  if (typeof v !== "number" || !Number.isInteger(v) || v < 0) return "—";
  const h = Math.floor(v / 3600), m = Math.floor((v % 3600) / 60), s = v % 60;
  return `${String(h).padStart(3,"0")}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
};

function Rows({ rows }: { rows: Array<Array<[string, unknown]>> }) {
  return <div className={styles.rows}>{rows.map((row, i) => <div className={styles.dataRow} key={i}>{row.map(([label,value]) => <div className={styles.dataCell} key={label}><span>{label}</span><strong>{dash(value)}</strong></div>)}</div>)}</div>;
}

function SectionData({ section, value }: { section: DashboardSection; value: unknown }) {
  if (value === null || value === undefined) return <div className={styles.emptyState}>—</div>;
  const data = value as Record<string, unknown>;
  if (section.kind === "kpi" || section.kind === "kpi-progress") {
    const valueNumber = typeof data.value === "number" ? data.value : null;
    return <div className={section.kind === "kpi-progress" ? styles.kpiProgressBody : undefined}><div className={styles.kpiValue}>{section.kind === "kpi-progress" ? pct(valueNumber) : dash(valueNumber)}</div>{section.kind === "kpi-progress" && <div className={styles.progressTrack}><span className={styles.progressFill} style={{ width: `${valueNumber ?? 0}%` }} /></div>}</div>;
  }
  if (section.key === "project_progress_overview") {
    const projects = Array.isArray(data.projects) ? data.projects as Array<Record<string, unknown>> : [];
    return <div className={styles.rows}>{projects.map((p, pi) => <div className={styles.groupBlock} key={String(p.project_id ?? pi)}><Rows rows={[[["Project", p.display_name ?? p.label ?? p.code],["Status",p.status],["Progress",pct(p.progress_percentage)]]]} />{Array.isArray(p.topics) && (p.topics as Array<Record<string,unknown>>).map((t,ti)=><div className={styles.nestedBlock} key={String(t.topic_id ?? ti)}><Rows rows={[[["Topic",t.display_name ?? t.label ?? t.code],["Status",t.status],["Progress",pct(t.progress_percentage)],["Total operation time",time(t.total_operation_time_seconds)]]]} />{Array.isArray(t.tasks) && <Rows rows={(t.tasks as Array<Record<string,unknown>>).map(task=>[["Task",task.display_name ?? task.label ?? task.code],["State",task.task_state]])} />}</div>)}</div>)}</div>;
  }
  if (section.key === "company_progress_summary") return <Rows rows={[[["Overall progress",pct(data.overall_progress_percentage)],["Running",data.running_count],["Pending",data.pending_action_count],["Review",data.pending_review_count],["Completed",data.completed_count]]]} />;
  if (section.key === "production_summary") return <Rows rows={(Array.isArray(data.units)?data.units:[]).map((u)=>{const x=u as Record<string,unknown>;return [["Unit",x.unit_label],["State",x.state],["Running",x.running_count],["Pending",x.pending_count],["Review",x.review_count],["Completed",x.completed_count]]})} />;
  if (section.key === "notifications") return <Rows rows={(Array.isArray(data.items)?data.items:[]).map((u)=>{const x=u as Record<string,unknown>;return [["Title",x.title],["Category",x.category],["Created",x.created_at],["Read",x.read_state]]})} />;
  if (section.key === "company_announcements") return <Rows rows={(Array.isArray(data.items)?data.items:[]).map((u)=>{const x=u as Record<string,unknown>;return [["Title",x.title],["Summary",x.summary],["Published",x.published_at]]})} />;
  if (section.key === "industry_news") return <Rows rows={(Array.isArray(data.items)?data.items:[]).map((u)=>{const x=u as Record<string,unknown>;return [["Title",x.title],["Source",x.source_name],["Summary",x.summary],["Published",x.published_at]]})} />;
  if (section.key === "system_status_summary") return <Rows rows={[[["Status",data.overall_status],["Summary",data.summary],["Checked",data.checked_at]]]} />;
  if (section.key === "recent_completions") return <Rows rows={(Array.isArray(data.items)?data.items:[]).map((u)=>{const x=u as Record<string,unknown>;return [["Project",x.project_label],["Topic",x.topic_label],["Item",x.item_label],["Kind",x.completion_kind],["Completed",x.completed_at]]})} />;
  return <div className={styles.emptyState}>—</div>;
}

function LoadingBody({ kind, loading }: { kind: SectionKind; loading: string }) {
  return <div className={kind.startsWith("kpi") ? styles.loadingKpi : styles.loadingBody} aria-label={loading}><span className={styles.skeletonLine} />{!kind.startsWith("kpi") && <span className={styles.skeletonLineShort} />}</div>;
}

export function DashboardVisual() {
  const { t } = useI18n();
  const [model, setModel] = useState<DashboardReadModel | null>(null);
  const [state, setState] = useState<VisualState>("LOADING");
  const [error, setError] = useState<DashboardReadError | null>(null);
  const [drawerSection, setDrawerSection] = useState<DashboardSection | null>(null);
  const [drawerState, setDrawerState] = useState<VisualState>("EMPTY");
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const openerRef = useRef<HTMLButtonElement | null>(null);

  const read = async (): Promise<DashboardReadModel | null> => {
    const response = await fetch("/v1/dashboard/read-model", { cache: "no-store" });
    const body = await response.json() as DashboardReadModel | DashboardReadError;
    if (!response.ok) throw body;
    return body as DashboardReadModel;
  };

  useEffect(() => {
    let active = true;
    setState("LOADING");
    read().then((next)=>{if(!active)return;setModel(next);setError(null);setState(SECTIONS.some(s=>selectDashboardSection(next,s.key)!=null)?"READ_ONLY":"EMPTY")}).catch((reason:DashboardReadError)=>{if(!active)return;setError(reason);setState("ERROR")});
    return ()=>{active=false};
  }, []);

  const closeDrawer = () => { setDrawerSection(null); queueMicrotask(() => openerRef.current?.focus()); };
  const openDrawer = async (section: DashboardSection, trigger: HTMLButtonElement) => {
    openerRef.current = trigger; setDrawerSection(section); setDrawerState("LOADING");
    try { const next=await read(); setModel(next); setError(null); setDrawerState(next && selectDashboardSection(next,section.key)!=null?"READ_ONLY":"EMPTY"); }
    catch(reason){ setError(reason as DashboardReadError); setDrawerState("ERROR"); }
  };

  useEffect(() => {
    if (!drawerSection) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); closeDrawer(); return; }
      if (event.key === "Tab") { event.preventDefault(); closeRef.current?.focus(); }
    };
    window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerSection]);

  const loading = t("global.state.loading"), view = t("global.common.view"), close = t("global.common.close");
  const errorText = error ? `${error.error_uid} · ${error.reason_code}` : t("global.state.load_failed");

  return (
    <div className={styles.page} data-page-uid="workspace:WB-01" data-page-state={state} data-authority-section-count="14" data-authority-control-count="14" aria-label={t("wb01.page.name")}>
      <div className={styles.grid}>
        {SECTIONS.map((section) => {
          const value = model ? selectDashboardSection(model, section.key) : null;
          return <section key={section.sectionId} className={[styles.card, section.kind === "kpi" || section.kind === "kpi-progress" ? styles.kpiCard : styles[section.kind]].join(" ")} data-order={section.order} data-section-id={section.sectionId} data-component-uid={section.componentUid} data-state={state}>
            <header className={styles.cardHeader}><h2 className={styles.cardTitle}>{t(section.titleKey)}</h2><button type="button" className={styles.viewButton} aria-label={t(section.controlKey)} data-control-id={section.controlId} data-operation-id="getDashboardReadModel" disabled={state === "LOADING"} onClick={(event)=>void openDrawer(section,event.currentTarget)}>{view}</button></header>
            <div className={styles.cardBody}>{state === "LOADING" ? <LoadingBody kind={section.kind} loading={loading}/> : state === "ERROR" ? <div className={styles.errorState}>{errorText}</div> : <SectionData section={section} value={value}/>}</div>
          </section>;
        })}
      </div>
      {drawerSection && <div className={styles.drawerLayer} data-component-uid="WB-01-CMP-DRAWER-PROJECTION" data-drawer-section-key={drawerSection.key} data-drawer-state={drawerState}>
        <button className={styles.backdrop} type="button" aria-label={close} onClick={closeDrawer}/>
        <aside className={styles.drawer} role="dialog" aria-modal="true" aria-labelledby="wb01-drawer-title"><header className={styles.drawerHeader}><h2 id="wb01-drawer-title" className={styles.drawerTitle}>{t(drawerSection.titleKey)}</h2><button ref={closeRef} className={styles.closeButton} type="button" onClick={closeDrawer}>{close}</button></header>
          <div className={styles.drawerBody}>{drawerState === "LOADING" ? <LoadingBody kind={drawerSection.kind} loading={loading}/> : drawerState === "ERROR" ? <div className={styles.errorState}>{errorText}</div> : <SectionData section={drawerSection} value={model ? selectDashboardSection(model,drawerSection.key):null}/>}</div>
          <footer className={styles.drawerFooter}><span>read_model_version: {dash(model?.read_model_version)}</span><span>correlation_id: {dash(model?.correlation_id)}</span></footer>
        </aside>
      </div>}
    </div>
  );
}
