"use client";

import { useEffect, useMemo, useState } from "react";
import { getKnowledgeActionTrace, readKnowledgeProjection, type KnowledgeProjection } from "@/domain/knowledge/knowledgeRuntimePort";
import { useI18n } from "@/i18n/LocaleProvider";
import { knowledgeControlLabel, knowledgeText, knowledgeViewLabel, type KnowledgeViewKey } from "@/i18n/knowledgeAdminCatalog";
import styles from "./KnowledgeAdminVisual.module.css";

type FieldGroup = { section: number; component: string; object: string; fields: readonly string[] };
type ComponentSpec = { suffix: string; name: string };
type SectionSpec = { section: number; name: string; view: KnowledgeViewKey | "global"; components: readonly ComponentSpec[] };
type VisibilityRule = "always" | "view" | "sourceSelected" | "sourceActive" | "sourcePaused" | "retry" | "resultSelected" | "contextItem" | "experienceSelected" | "comparable" | "outcomeComplete" | "draftEditable" | "previousVersion" | "draftReview";
type ControlSpec = { uid: string; suffix: string; view: KnowledgeViewKey | "global"; action?: string; gate?: string; permission: string; visible: VisibilityRule };

const VIEWS: readonly { key: KnowledgeViewKey; uid: string; sections: readonly number[] }[] = [
  { key: "overview", uid: "KB-01-VIEW-OVERVIEW", sections: [2, 16] },
  { key: "source", uid: "KB-01-VIEW-SOURCE", sections: [3, 4, 5, 16] },
  { key: "search", uid: "KB-01-VIEW-SEARCH", sections: [6, 7, 8, 16] },
  { key: "experience", uid: "KB-01-VIEW-EXPERIENCE", sections: [9, 10, 11, 16] },
  { key: "review", uid: "KB-01-VIEW-REVIEW", sections: [12, 13, 14, 15, 16] },
] as const;

const SECTIONS: readonly SectionSpec[] = [
  { section: 1, name: "Page Context / View Navigation", view: "global", components: [{ suffix: "CONTEXT", name: "Page Context Bar" }, { suffix: "VIEW-TABS", name: "Five View Tabs" }] },
  { section: 2, name: "Knowledge Overview", view: "overview", components: [{ suffix: "OVERVIEW-KPI", name: "Knowledge / Experience KPI Summary" }, { suffix: "OVERVIEW-WARN", name: "Governance Warning Feed" }] },
  { section: 3, name: "Source Directory", view: "source", components: [{ suffix: "SOURCE-LIST", name: "Source Directory / Filter" }] },
  { section: 4, name: "Source Detail / Governance", view: "source", components: [{ suffix: "SOURCE-DETAIL", name: "Source Detail / Configuration" }] },
  { section: 5, name: "Research / Ingestion Queue", view: "source", components: [{ suffix: "INGESTION", name: "Research / Ingestion Queue" }, { suffix: "INGESTION-DRAWER", name: "Failure / Retry Detail Drawer" }] },
  { section: 6, name: "Search / Result Explorer", view: "search", components: [{ suffix: "SEARCH", name: "Knowledge Search / Filters" }, { suffix: "RESULTS", name: "Search Results" }] },
  { section: 7, name: "Citation / Evidence Detail", view: "search", components: [{ suffix: "CITATION", name: "Citation / Evidence Detail" }] },
  { section: 8, name: "Context Candidate Builder", view: "search", components: [{ suffix: "CONTEXT-BASKET", name: "ACPOS Context Candidate Basket" }] },
  { section: 9, name: "Experience Directory", view: "experience", components: [{ suffix: "EXP-LIST", name: "ACPOS Experience Directory" }] },
  { section: 10, name: "Experience Replay", view: "experience", components: [{ suffix: "REPLAY", name: "Experience Replay Timeline / Compare" }] },
  { section: 11, name: "Root Cause / Learning Candidate", view: "experience", components: [{ suffix: "ROOT-CAUSE", name: "Root Cause / Pattern" }, { suffix: "LEARNING", name: "ACPOS Learning Candidate Draft" }] },
  { section: 12, name: "Knowledge Review Queue", view: "review", components: [{ suffix: "REVIEW-QUEUE", name: "Knowledge Review Queue" }] },
  { section: 13, name: "Knowledge Draft / Evidence Review", view: "review", components: [{ suffix: "DRAFT", name: "Knowledge Draft" }, { suffix: "EVIDENCE-CHECK", name: "Evidence / Citation / Outcome Validation" }] },
  { section: 14, name: "Version Diff / Supersession", view: "review", components: [{ suffix: "VERSION-DIFF", name: "Knowledge Version Diff" }] },
  { section: 15, name: "Review Decision Rail", view: "review", components: [{ suffix: "REVIEW-RAIL", name: "Review Checklist / Decision" }] },
  { section: 16, name: "Status / Error / Audit", view: "global", components: [{ suffix: "STATUS", name: "Status / Error / Audit Strip" }] },
] as const;

const FIELD_GROUPS: readonly FieldGroup[] = [
  { section: 1, component: "CONTEXT", object: "PAGE_AUTHORITY / PAGE_UI_STATE / ACPOS_PERMISSION_SCOPE", fields: ["PAGE-TITLE", "ACTIVE-VIEW", "SCOPE"] },
  { section: 4, component: "SOURCE-DETAIL", object: "KnowledgeSource", fields: ["SOURCE-ID", "SOURCE-VERSION", "SOURCE-NAME", "SOURCE-TYPE", "SOURCE-SCOPE", "SOURCE-RIGHTS", "SOURCE-CLASS", "SOURCE-COLLECT", "SOURCE-CONFIG", "SOURCE-FRESH", "SOURCE-RETENTION", "SOURCE-STATUS"] },
  { section: 5, component: "INGESTION", object: "KnowledgeIngestionRun", fields: ["RUN-ID", "RUN-SOURCE", "RUN-MODE", "RUN-STATUS", "RUN-PROGRESS", "RUN-START", "RUN-END", "RUN-RAW", "RUN-NORMALIZED", "RUN-EVIDENCE", "RUN-FAIL", "RUN-RETRY"] },
  { section: 6, component: "RESULTS", object: "KnowledgeSearchResult", fields: ["RESULT-ID", "RESULT-TYPE", "RESULT-TITLE", "RESULT-SCOPE", "RESULT-SOURCE", "RESULT-TIME", "RESULT-VERSION", "RESULT-FRESH", "RESULT-REVIEW"] },
  { section: 7, component: "CITATION", object: "KnowledgeCitation", fields: ["CIT-ID", "CIT-SOURCE", "CIT-LOC", "CIT-TIME", "CIT-VER", "CIT-CHECKSUM", "CIT-CLASS", "CIT-EVIDENCE"] },
  { section: 8, component: "CONTEXT-BASKET", object: "ACPOSContextCandidate", fields: ["CTX-CAND-ID", "CTX-CAND-VERSION", "CTX-CAND-PURPOSE", "CTX-CAND-SCOPE", "CTX-CAND-ITEMS", "CTX-CAND-EVIDENCE", "CTX-CAND-STATE", "CTX-CAND-FP"] },
  { section: 9, component: "EXP-LIST", object: "ACPOSExperienceRecord", fields: ["EXP-ID", "EXP-DOMAIN", "EXP-DEPT", "EXP-TASKTYPE", "EXP-SOURCECTX", "EXP-PROVIDER", "EXP-ROUTE", "EXP-ATTEMPT", "EXP-LATENCY", "EXP-COST", "EXP-EVAL", "EXP-QA", "EXP-CORR", "EXP-OUTCOME", "EXP-STATE"] },
  { section: 10, component: "REPLAY", object: "ACPOSExperienceReplayProjection", fields: ["REPLAY-SOURCE", "REPLAY-INSTRUCTION", "REPLAY-ROUTE", "REPLAY-OUTPUT", "REPLAY-EVAL", "REPLAY-CORRECTION", "REPLAY-OUTCOME", "REPLAY-ROOT"] },
  { section: 11, component: "LEARNING", object: "ACPOSLearningCandidate", fields: ["LEARN-ID", "LEARN-VERSION", "LEARN-SCOPE", "LEARN-PATTERN", "LEARN-PROPOSAL", "LEARN-EVIDENCE", "LEARN-LIMIT", "LEARN-STATE"] },
  { section: 13, component: "DRAFT", object: "KnowledgeVersion", fields: ["KN-ID", "KN-DRAFTVER", "KN-TITLE", "KN-TYPE", "KN-SUMMARY", "KN-CONTENT", "KN-SCOPE", "KN-CLASS", "KN-CIT", "KN-OUTCOME", "KN-SOURCEEXP", "KN-STATE"] },
  { section: 15, component: "REVIEW-RAIL", object: "KnowledgeReviewProjection", fields: ["REV-PREV", "REV-DIFF", "REV-CONFLICT", "REV-CHECK", "REV-BY", "REV-AT"] },
  { section: 15, component: "REVIEW-RAIL", object: "KnowledgeReviewDraft", fields: ["REV-RATIONALE", "REV-DECISION"] },
  { section: 4, component: "SOURCE-DETAIL", object: "KnowledgeAcquisitionIntent", fields: ["ACQ-MODE", "SEED", "ALLOW-DOMAINS", "DENY-DOMAINS", "PATH-POLICY", "SAME-DOMAIN", "MAX-DEPTH", "MAX-PAGES", "SITEMAP", "JS-RENDER", "CONTENT-TYPES", "LANGUAGE", "SCHEDULE", "RECRAWL", "RATE-PROFILE"] },
  { section: 5, component: "INGESTION", object: "KnowledgeAcquisitionResultProjection", fields: ["ACQ-JOB-ID", "ACQ-ATTEMPT-ID", "ACQ-HTTP", "ACQ-CANONICAL", "ACQ-HASH", "ACQ-LAST", "ACQ-NEXT", "ACQ-PARSER", "ACQ-RENDER"] },
] as const;

const CONTROLS: readonly ControlSpec[] = [
  { uid: "KB-01-CTL-VIEW-OVERVIEW", suffix: "VIEW-OVERVIEW", view: "overview", permission: "knowledge.read", visible: "always" },
  { uid: "KB-01-CTL-VIEW-SOURCE", suffix: "VIEW-SOURCE", view: "source", permission: "knowledge.read", visible: "always" },
  { uid: "KB-01-CTL-VIEW-SEARCH", suffix: "VIEW-SEARCH", view: "search", permission: "knowledge.read", visible: "always" },
  { uid: "KB-01-CTL-VIEW-EXPERIENCE", suffix: "VIEW-EXPERIENCE", view: "experience", permission: "knowledge.read", visible: "always" },
  { uid: "KB-01-CTL-VIEW-REVIEW", suffix: "VIEW-REVIEW", view: "review", permission: "knowledge.read", visible: "always" },
  { uid: "KB-01-CTL-SEARCH-GLOBAL", suffix: "SEARCH-GLOBAL", view: "global", action: "KB-01-ACT-SEARCH", gate: "KB-01-GATE-READ", permission: "knowledge.read", visible: "always" },
  { uid: "KB-01-CTL-SOURCE-CREATE", suffix: "SOURCE-CREATE", view: "source", action: "KB-01-ACT-SOURCE-CREATE", gate: "KB-01-GATE-SOURCE-WRITE", permission: "knowledge.source.configure", visible: "view" },
  { uid: "KB-01-CTL-SOURCE-SAVE", suffix: "SOURCE-SAVE", view: "source", action: "KB-01-ACT-SOURCE-SAVE", gate: "KB-01-GATE-SOURCE-SAVE", permission: "knowledge.source.configure", visible: "sourceSelected" },
  { uid: "KB-01-CTL-SOURCE-PAUSE", suffix: "SOURCE-PAUSE", view: "source", action: "KB-01-ACT-SOURCE-PAUSE", gate: "KB-01-GATE-SOURCE-PAUSE", permission: "knowledge.source.configure", visible: "sourceActive" },
  { uid: "KB-01-CTL-SOURCE-RESUME", suffix: "SOURCE-RESUME", view: "source", action: "KB-01-ACT-SOURCE-RESUME", gate: "KB-01-GATE-SOURCE-RESUME", permission: "knowledge.source.configure", visible: "sourcePaused" },
  { uid: "KB-01-CTL-SOURCE-RETIRE", suffix: "SOURCE-RETIRE", view: "source", action: "KB-01-ACT-SOURCE-RETIRE", gate: "KB-01-GATE-SOURCE-RETIRE", permission: "knowledge.source.configure", visible: "sourceSelected" },
  { uid: "KB-01-CTL-INGEST-START", suffix: "INGEST-START", view: "source", action: "KB-01-ACT-INGEST-START", gate: "KB-01-GATE-INGEST-START", permission: "knowledge.ingestion.execute", visible: "sourceActive" },
  { uid: "KB-01-CTL-INGEST-RETRY", suffix: "INGEST-RETRY", view: "source", action: "KB-01-ACT-INGEST-RETRY", gate: "KB-01-GATE-INGEST-RETRY", permission: "knowledge.ingestion.execute", visible: "retry" },
  { uid: "KB-01-CTL-SEARCH", suffix: "SEARCH", view: "search", action: "KB-01-ACT-SEARCH", gate: "KB-01-GATE-READ", permission: "knowledge.read", visible: "view" },
  { uid: "KB-01-CTL-CITATION-OPEN", suffix: "CITATION-OPEN", view: "search", action: "KB-01-ACT-CITATION-OPEN", gate: "KB-01-GATE-READ", permission: "knowledge.read", visible: "resultSelected" },
  { uid: "KB-01-CTL-CONTEXT-ADD", suffix: "CONTEXT-ADD", view: "search", action: "KB-01-ACT-CONTEXT-ITEM-ADD", gate: "KB-01-GATE-CONTEXT-DRAFT", permission: "knowledge.context.create", visible: "resultSelected" },
  { uid: "KB-01-CTL-CONTEXT-REMOVE", suffix: "CONTEXT-REMOVE", view: "search", action: "KB-01-ACT-CONTEXT-ITEM-REMOVE", gate: "KB-01-GATE-CONTEXT-DRAFT", permission: "knowledge.context.create", visible: "contextItem" },
  { uid: "KB-01-CTL-CONTEXT-CREATE", suffix: "CONTEXT-CREATE", view: "search", action: "KB-01-ACT-CONTEXT-CANDIDATE-CREATE", gate: "KB-01-GATE-CONTEXT-CREATE", permission: "knowledge.context.create", visible: "view" },
  { uid: "KB-01-CTL-REPLAY-OPEN", suffix: "REPLAY-OPEN", view: "experience", action: "KB-01-ACT-REPLAY-OPEN", gate: "KB-01-GATE-EXPERIENCE-READ", permission: "knowledge.experience.read", visible: "experienceSelected" },
  { uid: "KB-01-CTL-REPLAY-COMPARE", suffix: "REPLAY-COMPARE", view: "experience", action: "KB-01-ACT-REPLAY-COMPARE", gate: "KB-01-GATE-REPLAY-COMPARE", permission: "knowledge.experience.read", visible: "comparable" },
  { uid: "KB-01-CTL-LEARNING-CREATE", suffix: "LEARNING-CREATE", view: "experience", action: "KB-01-ACT-LEARNING-CREATE", gate: "KB-01-GATE-LEARNING-CREATE", permission: "knowledge.learning.create", visible: "outcomeComplete" },
  { uid: "KB-01-CTL-DRAFT-FROM-EXP", suffix: "DRAFT-FROM-EXP", view: "experience", action: "KB-01-ACT-KNOWLEDGE-DRAFT-FROM-EXPERIENCE", gate: "KB-01-GATE-DRAFT-FROM-EXP", permission: "knowledge.draft.write", visible: "outcomeComplete" },
  { uid: "KB-01-CTL-DRAFT-SAVE", suffix: "DRAFT-SAVE", view: "review", action: "KB-01-ACT-KNOWLEDGE-DRAFT-SAVE", gate: "KB-01-GATE-DRAFT-SAVE", permission: "knowledge.draft.write", visible: "draftEditable" },
  { uid: "KB-01-CTL-VERSION-COMPARE", suffix: "VERSION-COMPARE", view: "review", action: "KB-01-ACT-KNOWLEDGE-VERSION-COMPARE", gate: "KB-01-GATE-READ", permission: "knowledge.read", visible: "previousVersion" },
  { uid: "KB-01-CTL-APPROVE", suffix: "APPROVE", view: "review", action: "KB-01-ACT-KNOWLEDGE-APPROVE", gate: "KB-01-GATE-KNOWLEDGE-APPROVE", permission: "knowledge.review.approve", visible: "draftReview" },
  { uid: "KB-01-CTL-RETURN", suffix: "RETURN", view: "review", action: "KB-01-ACT-KNOWLEDGE-RETURN", gate: "KB-01-GATE-KNOWLEDGE-REVIEW", permission: "knowledge.review.approve", visible: "draftReview" },
  { uid: "KB-01-CTL-REJECT", suffix: "REJECT", view: "review", action: "KB-01-ACT-KNOWLEDGE-REJECT", gate: "KB-01-GATE-KNOWLEDGE-REVIEW", permission: "knowledge.review.approve", visible: "draftReview" },
] as const;

const FIELD_COUNT = FIELD_GROUPS.reduce((sum, group) => sum + group.fields.length, 0);
const EFFECTFUL_RUNTIME_READY = false;

function fieldsFor(section: number, component: string) { return FIELD_GROUPS.filter((group) => group.section === section && group.component === component); }
function projectionValue(projection: KnowledgeProjection | null, suffix: string) { return projection?.values[`KB-01-FLD-${suffix}`] ?? projection?.values[suffix] ?? "—"; }
function hasProjectionValue(projection: KnowledgeProjection | null, suffix: string) { const value = projectionValue(projection, suffix); return value !== "—" && value.trim() !== ""; }
function isVisible(control: ControlSpec, active: KnowledgeViewKey, projection: KnowledgeProjection | null) {
  if (control.visible === "always") return true;
  if (control.visible === "view") return control.view === active;
  if (control.view !== active) return false;
  if (control.visible === "sourceSelected") return hasProjectionValue(projection, "SOURCE-ID");
  if (control.visible === "sourceActive") return projectionValue(projection, "SOURCE-STATUS") === "ACTIVE";
  if (control.visible === "sourcePaused") return projectionValue(projection, "SOURCE-STATUS") === "PAUSED";
  if (control.visible === "retry") return projectionValue(projection, "RUN-STATUS") === "RETRY_ELIGIBLE" || projectionValue(projection, "RUN-RETRY") === "true";
  if (control.visible === "resultSelected") return hasProjectionValue(projection, "RESULT-ID");
  if (control.visible === "contextItem") return hasProjectionValue(projection, "CTX-CAND-ITEMS");
  if (control.visible === "experienceSelected") return hasProjectionValue(projection, "EXP-ID");
  if (control.visible === "comparable") return projection?.control_enabled[control.uid] === true;
  if (control.visible === "outcomeComplete") return projectionValue(projection, "EXP-STATE") === "OUTCOME_COMPLETE";
  if (control.visible === "draftEditable") return projectionValue(projection, "KN-STATE") === "DRAFT";
  if (control.visible === "previousVersion") return hasProjectionValue(projection, "REV-PREV");
  if (control.visible === "draftReview") return projectionValue(projection, "KN-STATE") === "REVIEW";
  return false;
}

export function KnowledgeAdminVisual() {
  const { locale } = useI18n();
  const [active, setActive] = useState<KnowledgeViewKey>("overview");
  const [projection, setProjection] = useState<KnowledgeProjection | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    void readKnowledgeProjection(controller.signal).then((result) => {
      setCorrelationId(result.correlation_id);
      if (result.ok) { setProjection(result.projection); setRuntimeError(null); }
      else { setProjection(null); setRuntimeError(result.reason_code); }
      setLoading(false);
    });
    return () => controller.abort();
  }, []);

  const activeView = VIEWS.find((view) => view.key === active) ?? VIEWS[0];
  const activeSections = useMemo(() => SECTIONS.filter((section) => section.view === active || (section.view === "global" && section.section === 16)), [active]);
  const visibleControls = CONTROLS.filter((control) => control.action && isVisible(control, active, projection));
  const pageState = loading ? "LOADING" : runtimeError ? "ERROR" : projection?.page_state ?? "READ_ONLY";
  const blockedReason = loading ? "PROJECTION_LOADING" : runtimeError ?? "RUNTIME_NOT_EXECUTED";
  const fieldValue = (suffix: string) => projectionValue(projection, suffix);

  const actionButton = (control: ControlSpec) => {
    const trace = getKnowledgeActionTrace(control.action);
    const projectionEnabled = projection?.control_enabled[control.uid] === true;
    const disabled = !EFFECTFUL_RUNTIME_READY || !projectionEnabled;
    return (
      <button key={control.uid} type="button" data-control-uid={control.uid} data-action-id={control.action} data-gate-uid={control.gate} data-permission={control.permission}
        data-action-owner={trace?.owner ?? "UNRESOLVED"} data-action-operation={trace?.operation ?? "UNRESOLVED"} data-action-method={trace?.method ?? "UNRESOLVED"}
        data-action-path={trace?.path ?? "UNRESOLVED"} data-action-errors={trace?.errors.join(",") ?? "UNRESOLVED"} data-audit-event={trace?.audit_event ?? "UNRESOLVED"}
        data-runtime-binding="NOT_EXECUTED" data-required-context={control.visible} data-required-permission={control.permission} data-current-state={pageState}
        data-blocked-reason={disabled ? blockedReason : ""} data-control-enabled-from-projection={String(projectionEnabled)} disabled={disabled}>
        <span>{knowledgeControlLabel(locale, control.suffix)}</span><small>{control.action}</small>
      </button>
    );
  };

  return (
    <div className={styles.page} data-page-uid="admin:KB-01" data-vis-step="VIS-18" data-page-model="SINGLE_PAGE_5_VIEW"
      data-section-registry-count={SECTIONS.length} data-component-registry-count={SECTIONS.reduce((sum, section) => sum + section.components.length, 0)}
      data-field-registry-count={FIELD_COUNT} data-control-registry-count={CONTROLS.length} data-action-registry-count="21"
      data-effectful-runtime-ready={String(EFFECTFUL_RUNTIME_READY)} data-page-state={pageState} data-projection-status={loading ? "LOADING" : runtimeError ? "BLOCKED" : "BOUND"}>
      <section className={styles.contextBar} data-section-uid="KB-01-SEC-01">
        <div className={styles.identity} data-component-uid="KB-01-CMP-CONTEXT">
          <div className={styles.eyebrow}>ADMIN · KB-01 · KNOWLEDGE & EXPERIENCE GOVERNANCE</div><h1>{knowledgeText(locale, "pageName")}</h1><p>{knowledgeText(locale, "pageRole")}</p>
          <div className={styles.contextMeta}><span data-field-uid="KB-01-FLD-PAGE-TITLE">KB-01</span><span data-field-uid="KB-01-FLD-ACTIVE-VIEW">{activeView.uid}</span><span data-field-uid="KB-01-FLD-SCOPE">{knowledgeText(locale, "authorizedScope")}: {fieldValue("SCOPE")}</span></div>
        </div>
        <div className={styles.globalSearch} role="search"><input aria-label={knowledgeControlLabel(locale, "SEARCH-GLOBAL")} placeholder={knowledgeControlLabel(locale, "SEARCH-GLOBAL")} disabled />{actionButton(CONTROLS.find((control) => control.uid === "KB-01-CTL-SEARCH-GLOBAL")!)}</div>
      </section>

      <nav className={styles.tabs} data-component-uid="KB-01-CMP-VIEW-TABS" aria-label={knowledgeText(locale, "currentView")}>
        {VIEWS.map((view) => { const selected = view.key === active; const control = CONTROLS.find((item) => item.view === view.key && item.suffix.startsWith("VIEW-")); return <button key={view.uid} type="button" className={`${styles.tab} ${selected ? styles.tabActive : ""}`} data-view-uid={view.uid} data-control-uid={control?.uid} aria-pressed={selected} onClick={() => setActive(view.key)}>{knowledgeViewLabel(locale, view.key)}</button>; })}
      </nav>

      <section className={styles.kpis} aria-label={`${knowledgeViewLabel(locale, active)} Summary`}>{["Source", "Ingestion", "Experience", "Review", "Approved Knowledge"].map((label) => <article className={styles.kpi} key={label}><span>{label}</span><strong>{projection?.values[label] ?? "—"}</strong></article>)}</section>

      <div className={styles.workspace} data-current-view={activeView.uid}>
        <main className={styles.sectionStack}>
          {activeSections.map((section) => <section key={section.section} className={styles.sectionCard} data-section-uid={`KB-01-SEC-${String(section.section).padStart(2, "0")}`}>
            <div className={styles.sectionHead}><div><span>S:{String(section.section).padStart(2, "0")}</span><h2>{section.name}</h2></div><span className={styles.emptyState}>{projection ? pageState : runtimeError ?? knowledgeText(locale, "noData")}</span></div>
            <div className={styles.componentGrid}>{section.components.map((component) => { const groups = fieldsFor(section.section, component.suffix); return <article key={component.suffix} className={styles.component} data-component-uid={`KB-01-CMP-${component.suffix}`}>
              <div className={styles.componentHead}><strong>{component.name}</strong><span>{groups.reduce((sum, group) => sum + group.fields.length, 0)} fields</span></div>
              {groups.length === 0 ? <div className={styles.noProjection}>—</div> : groups.map((group) => <div key={group.object} className={styles.fieldGroup}><div className={styles.objectName}>{group.object}</div><div className={styles.fieldGrid}>{group.fields.map((field) => <div className={styles.field} key={field} data-field-uid={`KB-01-FLD-${field}`}><span>{field}</span><strong>{fieldValue(field)}</strong></div>)}</div></div>)}
            </article>; })}</div>
          </section>)}
        </main>

        <aside className={styles.rail}>
          <section className={styles.railCard}><h2>{knowledgeText(locale, "controls")}</h2><p>{knowledgeText(locale, "runtimeBlocked")}</p><div className={styles.actionList}>{visibleControls.filter((control) => control.uid !== "KB-01-CTL-SEARCH-GLOBAL").map(actionButton)}</div><div className={styles.registryNote}>27 Controls · 21 Actions · 17 Gates · 14 Errors</div></section>
          <section className={styles.railCard} data-section-uid="KB-01-SEC-16" data-component-uid="KB-01-CMP-STATUS"><h2>{knowledgeText(locale, "status")}</h2><dl className={styles.statusList}>
            <div><dt>Authority</dt><dd>FINAL_LOCKED</dd></div><div><dt>Application</dt><dd>NOT_EXECUTED</dd></div><div><dt>API / DB</dt><dd>NOT_EXECUTED</dd></div><div><dt>Crawler / E2E</dt><dd>NOT_EXECUTED</dd></div><div><dt>Deploy</dt><dd>NOT_EXECUTED</dd></div>
            <div><dt>Projection</dt><dd>{loading ? "LOADING" : runtimeError ?? "BOUND"}</dd></div><div><dt>Correlation</dt><dd>{correlationId ?? "—"}</dd></div><div><dt>State / Disabled Reason</dt><dd>{pageState} / {blockedReason}</dd></div><div><dt>Audit</dt><dd>—</dd></div>
          </dl></section>
        </aside>
      </div>
      <footer className={styles.truthBar}>{knowledgeText(locale, "realDataOnly")}</footer>
    </div>
  );
}
