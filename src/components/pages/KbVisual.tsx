"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { KbClientError, fetchKbReadModel, postKbAction, type KbFieldValue } from "@/lib/client";
import {
  displayKbValue,
} from "./kbFormat";
import {
  KB_ACTION_LABELS,
  KB_CONTROL_ACTIONS,
  KB_DANGER_ACTIONS,
  KB_FORM_SCHEMAS,
  KB_PRIMARY_ACTIONS,
  KB_STATE_AUDIT_UID,
  KB_STATE_BASKET_UID,
  KB_STATE_CANDIDATES_UID,
  KB_STATE_CITATIONS_UID,
  KB_STATE_DRAFTS_UID,
  KB_STATE_ERROR_UID,
  KB_STATE_EXPERIENCE_UID,
  KB_STATE_IDEMPOTENCY_UID,
  KB_STATE_LEARNING_UID,
  KB_STATE_RESULTS_UID,
  KB_STATE_REPLAY_UID,
  KB_STATE_RUNS_UID,
  KB_STATE_SOURCES_UID,
  KB_VIEW_ACTIONS,
  KB_VIEW_CONTROLS,
  KB_VIEWS,
  KB_VISIBLE_CONTROLS,
  type KbDrawer,
  type KbView,
} from "./kbControls";
import styles from "./KbVisual.module.css";

function readJson<T>(raw: string | null | undefined, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
  danger = false,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  danger?: boolean;
}) {
  const className = [styles.btn, primary ? styles.btnPrimary : "", danger ? styles.btnDanger : ""]
    .filter(Boolean)
    .join(" ");
  return (
    <button type="button" className={className} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      {label}
    </button>
  );
}

function Kv({ uid, label, value }: { uid?: string; label: string; value: string }) {
  return (
    <div className={styles.kvRow} data-control-uid={uid}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

const VIEW_LABELS: Record<KbView, TranslationKey> = {
  "KB-01-VIEW-OVERVIEW": "kb.view-overview",
  "KB-01-VIEW-SOURCE": "kb.view-source",
  "KB-01-VIEW-SEARCH": "kb.view-search",
  "KB-01-VIEW-EXPERIENCE": "kb.view-experience",
  "KB-01-VIEW-REVIEW": "kb.view-review",
};

interface KbSourceState {
  sourceId: string;
  version: number;
  name: string;
  sourceType: string;
  scope: string;
  rights: string;
  classification: string;
  collectionMethod: string;
  freshnessPolicy: string;
  retentionPolicy: string;
  status: string;
}

interface KbRunState {
  runId: string;
  sourceRef: string;
  runType: string;
  status: string;
  progress: string;
  failure: string | null;
  retryEligible: boolean;
  attempt: number;
  itemCount: number;
}

interface KbErrorState {
  code: string;
  message: string;
  remediation: string;
}

const SIDE_EFFECT_ACTIONS = new Set([
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-PAUSE",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RESUME",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE",
  "CTRL-ADMIN-KB-01-ACT-INGEST-START",
  "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE",
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE",
  // CompareKnowledgeVersionsRequest / CompareExperienceReplayRequest are
  // READ_COMPARE operations: additionalProperties false, no idempotency_key.
  "CTRL-ADMIN-KB-01-ACT-APPROVE",
  "CTRL-ADMIN-KB-01-ACT-RETURN",
  "CTRL-ADMIN-KB-01-ACT-REJECT",
]);

export function KbVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<KbFieldValue[]>([]);
  const [view, setView] = useState<KbView>("KB-01-VIEW-OVERVIEW");
  const [drawer, setDrawer] = useState<KbDrawer | null>(null);
  const [modalUid, setModalUid] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const lastFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
    fetchKbReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : KB_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof KbClientError ? cause.code : "KB_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(KB_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [tick]);

  const act = useCallback(async (controlUid: string, payload?: string) => {
    const actionUid = KB_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postKbAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, payload);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
    setTick((n) => n + 1);
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayKbValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(KB_VISIBLE_CONTROLS), []);
  const viewActions = KB_VIEW_ACTIONS[view];
  const fieldMap = useMemo(() => new Map(fields.map((item) => [item.controlUid, item.value])), [fields]);

  const sources = readJson<KbSourceState[]>(fieldMap.get(KB_STATE_SOURCES_UID), []);
  const runs = readJson<KbRunState[]>(fieldMap.get(KB_STATE_RUNS_UID), []);
  const results = readJson<Array<Record<string, string>>>(fieldMap.get(KB_STATE_RESULTS_UID), []);
  const citations = readJson<Array<Record<string, string>>>(fieldMap.get(KB_STATE_CITATIONS_UID), []);
  const basket = readJson<Array<Record<string, string>>>(fieldMap.get(KB_STATE_BASKET_UID), []);
  const candidates = readJson<Array<Record<string, unknown>>>(fieldMap.get(KB_STATE_CANDIDATES_UID), []);
  const experience = readJson<Array<Record<string, unknown>>>(fieldMap.get(KB_STATE_EXPERIENCE_UID), []);
  const replay = readJson<Record<string, unknown> | null>(fieldMap.get(KB_STATE_REPLAY_UID), null);
  const learning = readJson<Array<Record<string, unknown>>>(fieldMap.get(KB_STATE_LEARNING_UID), []);
  const drafts = readJson<Array<Record<string, unknown>>>(fieldMap.get(KB_STATE_DRAFTS_UID), []);
  const contractError = readJson<KbErrorState | null>(fieldMap.get(KB_STATE_ERROR_UID), null);
  const auditRaw = fieldMap.get(KB_STATE_AUDIT_UID) ?? "";
  const auditLines = auditRaw ? auditRaw.split("\n").slice(-4) : [];
  const idempotency = readJson<Record<string, string>>(fieldMap.get(KB_STATE_IDEMPOTENCY_UID), {});

  const latestRun = runs.length ? runs[runs.length - 1] : null;
  const latestSource = sources.length ? sources[sources.length - 1] : null;
  const candidate = candidates.length ? candidates[candidates.length - 1] : null;
  const learningRecord = learning.length ? learning[learning.length - 1] : null;
  const reviewDrafts = drafts.filter((d) => d.state === "REVIEW");
  const queueDrafts = reviewDrafts.length ? reviewDrafts : drafts;
  const selectedDraft = drafts.length ? drafts[drafts.length - 1] : null;
  const replayRecords = replay && Array.isArray(replay.records) ? (replay.records as Array<Record<string, unknown>>) : replay ? [replay] : [];
  const lastAudit = auditLines.length ? auditLines[auditLines.length - 1] : "";

  // Focus management: focus first focusable element when drawer/modal opens;
  // restore focus to the invoking element when it closes.
  useEffect(() => {
    if (!drawer && !modalUid) return;
    const host = drawer ? drawerRef.current : modalRef.current;
    if (host) {
      const target = host.querySelector<HTMLElement>("input, textarea, button, select");
      if (target) target.focus();
    }
    return () => {
      const prior = lastFocusedRef.current;
      if (prior && document.contains(prior)) prior.focus();
    };
  }, [drawer, modalUid]);

  const switchView = (next: KbView) => {
    setView(next);
    setDrawer(null);
    setModalUid(null);
    void act(KB_VIEW_CONTROLS[next]);
  };

  const openModal = (uid: string) => {
    lastFocusedRef.current = document.activeElement as HTMLElement | null;
    setModalUid(uid);
    setFormValues({});
    void act(uid);
  };

  const closeModal = () => {
    setModalUid(null);
    setFormValues({});
  };

  const submitModal = (uid: string) => {
    const schema = KB_FORM_SCHEMAS[uid] ?? [];
    const payload: Record<string, unknown> = {};
    for (const field of schema) {
      const raw = (formValues[field.key] ?? "").trim();
      if (!raw) continue;
      if (field.list) payload[field.key] = raw.split(",").map((part) => part.trim()).filter(Boolean);
      else if (field.key.endsWith("_config") || field.key === "mandatory_check_results") {
        try {
          payload[field.key] = JSON.parse(raw) as unknown;
        } catch {
          payload[field.key] = raw;
        }
      } else payload[field.key] = raw;
    }
    if (SIDE_EFFECT_ACTIONS.has(uid)) payload.idempotency_key = `idem-${uid}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    closeModal();
    const drawer = DRAWER_FOR_CONTROL[uid];
    if (drawer) {
      setDrawer(drawer);
      void act(uid, JSON.stringify(payload));
      return;
    }
    void act(uid, JSON.stringify(payload));
  };

  // Drawer-bound controls collect their request payload through the modal,
  // then the drawer displays the projection the operation produced.
  const DRAWER_FOR_CONTROL: Record<string, KbDrawer> = {
    "CTRL-ADMIN-KB-01-ACT-SEARCH": "search",
    "CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL": "search",
    "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN": "citation",
    "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN": "replay",
    "CTRL-ADMIN-KB-01-ACT-INGEST-START": "ingestion",
    "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY": "ingestion",
    "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD": "basket",
    "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE": "basket",
  };

  const onAction = (uid: string) => {
    if (KB_FORM_SCHEMAS[uid]) {
      openModal(uid);
      return;
    }
    void act(uid);
  };

  const bodyClass =
    view === "KB-01-VIEW-SOURCE"
      ? styles.colsThree
      : view === "KB-01-VIEW-SEARCH"
        ? styles.colsSearch
        : view === "KB-01-VIEW-EXPERIENCE"
          ? styles.colsExperience
          : view === "KB-01-VIEW-REVIEW"
            ? styles.colsReview
            : styles.cols;

  const actionButtons = (
    <div className={styles.actions}>
      <span className={styles.actionsLabel}>{tx("kb.actions")}</span>
      {viewActions.map((uid) => (
        <Btn
          key={uid}
          uid={uid}
          label={tx(KB_ACTION_LABELS[uid] ?? "kb.act-search")}
          onAct={onAction}
          disabled={disabled}
          primary={KB_PRIMARY_ACTIONS.has(uid)}
          danger={KB_DANGER_ACTIONS.has(uid)}
        />
      ))}
    </div>
  );

  return (
    <div
      className={styles.page}
      data-page-uid="admin:KB-01"
      data-page-state={pageState}
      data-ui-view={view}
      data-component-count="5"
      data-control-count={visibleUids.size}
      aria-label={tx("kb.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("kb.error")}
        </div>
      ) : null}

      <div className={styles.contextBar} data-section-uid="KB-01-SEC-01">
        <div className={styles.contextItem}>
          <span>{tx("kb.page-title")}</span>
          <strong>{tx("kb.title")}</strong>
        </div>
        <div className={styles.contextItem}>
          <span>{tx("kb.scope")}</span>
          <strong>{tx("kb.scope-value")}</strong>
        </div>
        <div className={styles.contextItem}>
          <span>{tx("kb.selected")}</span>
          <strong>{selectedDraft ? String(selectedDraft.knowledge_id) : dash}</strong>
        </div>
        <span className={styles.pill}>{tx("kb.truth-value")}</span>
        <span className={`${styles.pill} ${styles.pillWarn}`}>{tx("kb.runtime-block")}</span>
      </div>

      <nav className={styles.tabs} data-section-uid="KB-01-SEC-01-TABS" aria-label={tx("kb.views")}>
        {KB_VIEWS.map((uid) => (
          <button
            key={uid}
            type="button"
            className={`${styles.tab} ${view === uid ? styles.tabActive : ""}`}
            data-control-uid={KB_VIEW_CONTROLS[uid]}
            disabled={disabled}
            onClick={() => switchView(uid)}
          >
            {tx(VIEW_LABELS[uid])}
          </button>
        ))}
      </nav>

      <div className={bodyClass}>
        {view === "KB-01-VIEW-OVERVIEW" ? (
          <>
            <section className={styles.workspace} data-section-uid="KB-01-SEC-02">
              <div>
                <h2>{tx("kb.overview-title")}</h2>
                <p className={styles.note}>{tx("kb.overview-hint")}</p>
              </div>
               <div className={styles.cardGridFive}>
                 <article className={styles.card} data-component-uid="KB-01-CMP-OVERVIEW-KPI">
                   <h3>{tx("kb.kpi-source")}</h3>
                   <p className={styles.note}>{tx("kb.kpi-source-hint")}</p>
                   <strong>{sources.length ? `${sources.length} (${latestSource?.name ?? dash})` : dash}</strong>
                 </article>
                 <article className={styles.card}>
                   <h3>{tx("kb.kpi-ingestion")}</h3>
                   <p className={styles.note}>{tx("kb.kpi-ingestion-hint")}</p>
                   <strong>{runs.length ? `${runs.length} (${latestRun?.status ?? dash})` : dash}</strong>
                 </article>
                <article className={styles.card}>
                  <h3>{tx("kb.kpi-experience")}</h3>
                  <p className={styles.note}>{tx("kb.kpi-experience-hint")}</p>
                  <strong>{experience.length ? String(experience.length) : dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("kb.kpi-review")}</h3>
                  <p className={styles.note}>{tx("kb.kpi-review-hint")}</p>
                  <strong>{reviewDrafts.length ? String(reviewDrafts.length) : dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("kb.kpi-approved")}</h3>
                  <p className={styles.note}>{tx("kb.kpi-approved-hint")}</p>
                  <strong>{drafts.filter((d) => d.state === "APPROVED").length || dash}</strong>
                </article>
              </div>
              {actionButtons}
            </section>
            <aside className={styles.rail} data-section-uid="KB-01-SEC-02-WARN" data-component-uid="KB-01-CMP-OVERVIEW-WARN">
               <h2>{tx("kb.warn-title")}</h2>
               <p className={styles.note}>{tx("kb.warn-hint")}</p>
               <strong>{contractError ? contractError.code : latestRun?.failure ? latestRun.failure : dash}</strong>
              <div className={styles.railPills}>
                <span className={styles.pill}>{tx("kb.rail-real-only")}</span>
                <span className={`${styles.pill} ${styles.pillWarn}`}>{tx("kb.rail-no-fake")}</span>
              </div>
            </aside>
          </>
        ) : null}

        {view === "KB-01-VIEW-SOURCE" ? (
          <>
            <section className={styles.workspace} data-section-uid="KB-01-SEC-03" data-component-uid="KB-01-CMP-SOURCE-LIST">
              <div>
                <h2>{tx("kb.source-dir")}</h2>
                <p className={styles.note}>{tx("kb.source-dir-hint")}</p>
              </div>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>{tx("kb.col-source")}</th>
                      <th>{tx("kb.col-type")}</th>
                      <th>{tx("kb.col-status")}</th>
                      <th>{tx("kb.col-scope")}</th>
                    </tr>
                  </thead>
                   <tbody>
                     {sources.length ? (
                       sources.map((source) => (
                         <tr key={source.sourceId}>
                           <td>{source.name}</td>
                           <td>{source.sourceType}</td>
                           <td>{source.status}</td>
                           <td>{source.scope}</td>
                         </tr>
                       ))
                     ) : (
                       <tr>
                         <td>{dash}</td>
                         <td>{dash}</td>
                         <td>{dash}</td>
                         <td>{dash}</td>
                       </tr>
                     )}
                   </tbody>
                 </table>
               </div>
             </section>
             <section className={styles.workspace} data-section-uid="KB-01-SEC-04" data-component-uid="KB-01-CMP-SOURCE-DETAIL">
              <div>
                <h2>{tx("kb.source-gov")}</h2>
                <p className={styles.note}>{tx("kb.source-gov-hint")}</p>
              </div>
               <div className={styles.kvList}>
                 <Kv label={tx("kb.fld-name")} value={latestSource?.name ?? dash} />
                 <Kv label={tx("kb.fld-type")} value={latestSource?.sourceType ?? dash} />
                 <Kv label={tx("kb.fld-scope")} value={latestSource?.scope ?? dash} />
                 <Kv label={tx("kb.fld-rights")} value={latestSource?.rights ?? dash} />
                 <Kv label={tx("kb.fld-class")} value={latestSource?.classification ?? dash} />
                 <Kv label={tx("kb.fld-acq-mode")} value={latestSource?.collectionMethod ?? dash} />
                 <Kv label={tx("kb.fld-status")} value={latestSource?.status ?? dash} />
                 <Kv label="version" value={latestSource ? String(latestSource.version) : dash} />
               </div>
              {actionButtons}
            </section>
            <aside className={styles.rail} data-section-uid="KB-01-SEC-05" data-component-uid="KB-01-CMP-INGESTION">
              <h2>{tx("kb.ingest-title")}</h2>
              <p className={styles.note}>{tx("kb.ingest-hint")}</p>
               <div className={styles.kvList}>
                 <Kv label={tx("kb.fld-run-id")} value={latestRun?.runId ?? dash} />
                 <Kv label={tx("kb.fld-run-status")} value={latestRun ? `${latestRun.status} (attempt ${latestRun.attempt})` : dash} />
                 <Kv label={tx("kb.fld-progress")} value={latestRun?.progress ?? dash} />
                 <Kv label={tx("kb.fld-failure")} value={latestRun?.failure ?? dash} />
                 <Kv label="retry_eligible" value={latestRun ? (latestRun.retryEligible ? "true" : "false") : dash} />
                 <Kv label="item_count" value={latestRun ? String(latestRun.itemCount) : dash} />
               </div>
              <span className={`${styles.pill} ${styles.pillPurple}`}>{tx("kb.shared-runtime")}</span>
            </aside>
          </>
        ) : null}

        {view === "KB-01-VIEW-SEARCH" ? (
          <>
            <section className={styles.workspace} data-section-uid="KB-01-SEC-06" data-component-uid="KB-01-CMP-RESULTS">
              <div>
                <h2>{tx("kb.search-title")}</h2>
                <p className={styles.note}>{tx("kb.search-hint")}</p>
              </div>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>{tx("kb.col-title")}</th>
                      <th>{tx("kb.col-type")}</th>
                      <th>{tx("kb.col-source")}</th>
                      <th>{tx("kb.col-fresh")}</th>
                    </tr>
                  </thead>
                   <tbody>
                     {results.length ? (
                       results.map((item, index) => (
                         <tr key={item.result_ref ?? item.url ?? index}>
                           <td>{item.title ?? dash}</td>
                           <td>{item.__kind ?? item.classification_type ?? item.type ?? dash}</td>
                           <td>{item.source_ref ?? item.source ?? dash}</td>
                           <td>{item.source_time ?? item.freshness ?? dash}</td>
                         </tr>
                       ))
                     ) : (
                       <tr>
                         <td>{dash}</td>
                         <td>{dash}</td>
                         <td>{dash}</td>
                         <td>{dash}</td>
                       </tr>
                     )}
                   </tbody>
                 </table>
               </div>
              {actionButtons}
             </section>
             <section className={styles.workspace} data-section-uid="KB-01-SEC-07" data-component-uid="KB-01-CMP-CITATION">
              <div>
                <h2>{tx("kb.citation-title")}</h2>
                <p className={styles.note}>{tx("kb.citation-hint")}</p>
              </div>
              <div className={styles.kvList}>
                <Kv label={tx("kb.fld-citation")} value={citations.length ? citations.map((c) => c.citation_id).join(", ") : dash} />
                <Kv label={tx("kb.fld-source-ref")} value={citations.length ? citations.map((c) => c.source_ref).join(" | ") : dash} />
                <Kv label={tx("kb.fld-location")} value={citations.length ? citations.map((c) => c.source_location).join(" | ") : dash} />
                <Kv label={tx("kb.fld-version")} value={citations.length ? citations.map((c) => c.source_version).join(" | ") : dash} />
                <Kv label={tx("kb.fld-evidence")} value={citations.length ? citations.map((c) => c.evidence_ref).join(" | ") : dash} />
              </div>
             </section>
             <aside className={styles.rail} data-section-uid="KB-01-SEC-08" data-component-uid="KB-01-CMP-CONTEXT-BASKET">
              <h2>{tx("kb.context-title")}</h2>
              <p className={styles.note}>{tx("kb.context-hint")}</p>
              <div className={styles.kvList}>
                <Kv label={tx("kb.fld-candidate")} value={candidate ? String(candidate.context_candidate_id) : dash} />
                <Kv label={tx("kb.fld-purpose")} value={candidate ? String(candidate.purpose) : dash} />
                <Kv label={tx("kb.fld-selected")} value={basket.length ? basket.map((b) => b.ref).join(" | ") : candidate ? (candidate.selected_refs as string[])?.join(" | ") ?? dash : dash} />
                <Kv label={tx("kb.fld-state")} value={candidate ? String(candidate.state) : dash} />
              </div>
              <div className={styles.block}>{tx("kb.context-no-adopt")}</div>
            </aside>
          </>
        ) : null}

        {view === "KB-01-VIEW-EXPERIENCE" ? (
          <>
            <section className={styles.workspace} data-section-uid="KB-01-SEC-09" data-component-uid="KB-01-CMP-EXP-LIST">
              <div>
                <h2>{tx("kb.exp-title")}</h2>
                <p className={styles.note}>{tx("kb.exp-hint")}</p>
              </div>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>{tx("kb.col-experience")}</th>
                      <th>{tx("kb.col-domain")}</th>
                      <th>{tx("kb.col-outcome")}</th>
                      <th>{tx("kb.col-state")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {experience.length ? (
                      experience.map((record) => (
                        <tr key={String(record.experience_id)}>
                          <td>{String(record.experience_id)}</td>
                          <td>{String(record.domain ?? dash)}</td>
                          <td>{String((record.business_human_outcome as Record<string, unknown> | undefined)?.status ?? dash)}</td>
                          <td>{String(record.state ?? dash)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td>{dash}</td>
                        <td>{dash}</td>
                        <td>{dash}</td>
                        <td>{dash}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {actionButtons}
             </section>
             <section className={styles.workspace} data-section-uid="KB-01-SEC-10" data-component-uid="KB-01-CMP-REPLAY">
              <div>
                <h2>{tx("kb.replay-title")}</h2>
                <p className={styles.note}>{tx("kb.replay-hint")}</p>
              </div>
              <div className={styles.kvList}>
                <Kv label={tx("kb.fld-input")} value={replayRecords.length ? replayRecords.map((r) => ((r.source_context_refs as string[]) ?? []).join(",") || String(r.experience_id)).join(" | ") : dash} />
                <Kv label={tx("kb.fld-route")} value={replayRecords.length ? replayRecords.map((r) => String(r.route_decision_ref ?? dash)).join(" | ") : dash} />
                <Kv label={tx("kb.fld-output")} value={replayRecords.length ? replayRecords.map((r) => String((r.business_human_outcome as Record<string, unknown> | undefined)?.status ?? dash)).join(" | ") : dash} />
                <Kv label={tx("kb.fld-eval")} value={replayRecords.length ? replayRecords.map((r) => ((r.evaluation_refs as string[]) ?? []).join(",")).join(" | ") : dash} />
                <Kv label={tx("kb.fld-correction")} value={replayRecords.length ? replayRecords.map((r) => ((r.correction_refs as string[]) ?? []).join(",") || "—").join(" | ") : dash} />
                <Kv label={tx("kb.fld-outcome")} value={replay ? String(replay.compare_mode ?? replay.state ?? dash) : dash} />
              </div>
             </section>
             <aside className={styles.rail} data-section-uid="KB-01-SEC-11">
              <h2>{tx("kb.learning-title")}</h2>
              <p className={styles.note}>{tx("kb.learning-hint")}</p>
              <div className={styles.kvList}>
                <Kv label={tx("kb.fld-root-cause")} value={replayRecords.length ? String((replayRecords[0].root_cause as string | undefined) ?? "—") : dash} />
                <Kv label={tx("kb.fld-pattern")} value={learningRecord ? String(learningRecord.pattern) : dash} />
                <Kv label={tx("kb.fld-proposal")} value={learningRecord ? String(learningRecord.proposed_improvement) : dash} />
                <Kv label={tx("kb.fld-state")} value={learningRecord ? String(learningRecord.state) : dash} />
              </div>
              <div className={styles.block}>{tx("kb.learning-no-canon")}</div>
            </aside>
          </>
        ) : null}

        {view === "KB-01-VIEW-REVIEW" ? (
          <>
            <section className={styles.workspace} data-section-uid="KB-01-SEC-12" data-component-uid="KB-01-CMP-REVIEW-QUEUE">
              <div>
                <h2>{tx("kb.queue-title")}</h2>
                <p className={styles.note}>{tx("kb.queue-hint")}</p>
              </div>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>{tx("kb.col-draft")}</th>
                      <th>{tx("kb.col-type")}</th>
                      <th>{tx("kb.col-state")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queueDrafts.length ? (
                      queueDrafts.map((draft) => (
                        <tr key={String(draft.knowledge_id)}>
                          <td>{`${String(draft.knowledge_id)} v${String(draft.draft_version)}`}</td>
                          <td>{String(draft.knowledge_type ?? dash)}</td>
                          <td>{String(draft.state ?? dash)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td>{dash}</td>
                        <td>{dash}</td>
                        <td>{dash}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {actionButtons}
            </section>
            <section className={styles.workspace} data-section-uid="KB-01-SEC-13">
              <div>
                <h2>{tx("kb.draft-title")}</h2>
                <p className={styles.note}>{tx("kb.draft-hint")}</p>
              </div>
              <div className={styles.kvList}>
                <Kv label={tx("kb.fld-title")} value={selectedDraft ? String(selectedDraft.title) : dash} />
                <Kv label={tx("kb.fld-type")} value={selectedDraft ? String(selectedDraft.knowledge_type) : dash} />
                <Kv label={tx("kb.fld-summary")} value={selectedDraft?.summary ? String(selectedDraft.summary) : dash} />
                <Kv label={tx("kb.fld-citations")} value={selectedDraft ? ((selectedDraft.citation_refs as string[]) ?? []).join(", ") || dash : dash} />
                <Kv label={tx("kb.fld-outcomes")} value={selectedDraft ? ((selectedDraft.outcome_refs as string[]) ?? []).join(", ") || dash : dash} />
                <Kv label={tx("kb.fld-prev-version")} value={selectedDraft?.supersedes_knowledge_id ? String(selectedDraft.supersedes_knowledge_id) : dash} />
                <Kv label={tx("kb.fld-diff")} value={selectedDraft?.version_diff ? String(selectedDraft.version_diff) : dash} />
                <Kv label={tx("kb.fld-conflict")} value={contractError?.code === "KB_VERSION_CONFLICT" ? contractError.message : dash} />
              </div>
              {actionButtons}
            </section>
            <aside className={styles.rail} data-section-uid="KB-01-SEC-15" data-component-uid="KB-01-CMP-REVIEW-RAIL">
              <h2>{tx("kb.rail-decision")}</h2>
              <div className={styles.kvList}>
                <Kv label={tx("kb.fld-checks")} value={selectedDraft?.mandatory_check_results ? JSON.stringify(selectedDraft.mandatory_check_results) : dash} />
                <Kv label={tx("kb.fld-rationale")} value={selectedDraft?.review_rationale ? String(selectedDraft.review_rationale) : dash} />
                <Kv label={tx("kb.fld-decision")} value={selectedDraft ? String(selectedDraft.state) : dash} />
                <Kv label={tx("kb.fld-reviewer")} value={selectedDraft?.reviewed_by ? String(selectedDraft.reviewed_by) : dash} />
              </div>
              <span className={`${styles.pill} ${styles.pillPurple}`}>{tx("kb.human-decision")}</span>
              <div className={styles.block}>{tx("kb.review-block")}</div>
            </aside>
          </>
        ) : null}
      </div>

      <div className={styles.statusStrip} data-section-uid="KB-01-SEC-16" data-component-uid="KB-01-CMP-STATUS">
        <span>
          {tx("kb.status-correlation")} <strong>{lastAudit ? lastAudit.slice(0, 10) : dash}</strong>
        </span>
        <span>
          {tx("kb.status-error")} <strong>{contractError ? `${contractError.code} ${contractError.message} → ${contractError.remediation}` : dash}</strong>
        </span>
        <span>
          {tx("kb.status-audit")} <strong>{auditLines.length ? auditLines.join(" / ") : dash}</strong>
        </span>
        <span>
          {tx("kb.status-disabled")} <strong>{disabled ? tx("kb.status-denied") : dash}</strong>
        </span>
        <span>
          idempotency registry <strong>{Object.keys(idempotency).length ? `${Object.keys(idempotency).length} keys` : dash}</strong>
        </span>
      </div>

      {drawer ? (
        <aside className={styles.drawer} data-section-uid="KB-01-SEC-DRAWER" ref={drawerRef}>
          <h3>
            {drawer === "search"
              ? tx("kb.drawer-search")
              : drawer === "citation"
                ? tx("kb.drawer-citation")
                : drawer === "replay"
                  ? tx("kb.drawer-replay")
                  : drawer === "basket"
                    ? tx("kb.context-title")
                    : tx("kb.drawer-ingestion")}
          </h3>
          <p className={styles.note}>{tx("kb.drawer-hint")}</p>
          {drawer === "search" || drawer === "citation" ? (
            <strong>{results.length ? `${results.length} matched` : dash}</strong>
          ) : drawer === "replay" ? (
            <strong>{replayRecords.length ? String(replayRecords[0].experience_id ?? dash) : dash}</strong>
          ) : drawer === "basket" ? (
            <strong>{basket.length ? basket.map((b) => b.ref).join(" | ") : dash}</strong>
          ) : (
            <strong>{runs.length ? `${latestRun?.runId} ${latestRun?.status}` : dash}</strong>
          )}
          <Btn uid="CTRL-ADMIN-KB-01-ACT-SEARCH" label={tx("global.common.close")} onAct={() => setDrawer(null)} disabled={false} />
        </aside>
      ) : null}

      {modalUid ? (
        <aside
          className={styles.modal}
          data-section-uid="KB-01-SEC-MODAL"
          role="dialog"
          aria-modal="true"
          tabIndex={-1}
          ref={modalRef}
        >
          <h3>{tx(KB_ACTION_LABELS[modalUid] ?? "kb.modal-title")}</h3>
          <p className={styles.note}>{tx("kb.modal-hint")}</p>
          <div className={styles.kvList}>
            {(KB_FORM_SCHEMAS[modalUid] ?? []).map((field) => (
              <label key={field.key} className={styles.kvRow}>
                <span>
                  {field.label}
                  {field.required ? " *" : ""}
                </span>
                {field.area ? (
                  <textarea
                    value={formValues[field.key] ?? ""}
                    onChange={(event) => setFormValues((prev) => ({ ...prev, [field.key]: event.target.value }))}
                    rows={3}
                  />
                ) : (
                  <input
                    value={formValues[field.key] ?? ""}
                    onChange={(event) => setFormValues((prev) => ({ ...prev, [field.key]: event.target.value }))}
                  />
                )}
              </label>
            ))}
          </div>
          <div className={styles.actions}>
            <Btn uid={modalUid} label={tx("kb.modal-submit")} onAct={() => submitModal(modalUid)} disabled={disabled} primary />
            <Btn uid={`${modalUid}-CLOSE`} label={tx("global.common.close")} onAct={closeModal} disabled={false} />
          </div>
        </aside>
      ) : null}
    </div>
  );
}
