"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { KbClientError, fetchKbReadModel, postKbAction, type KbFieldValue } from "@/lib/client";
import type { AcquisitionResultItem, AcquisitionSourceRecord } from "@/lib/sharedAcquisition";
import {
  KB_ACQ_MODE_UID,
  KB_RESULTS_UID,
  KB_RUN_FAIL_UID,
  KB_RUN_ID_UID,
  KB_RUN_PROGRESS_UID,
  KB_RUN_STATUS_UID,
  KB_SOURCE_CLASS_UID,
  KB_SOURCE_NAME_UID,
  KB_SOURCE_RIGHTS_UID,
  KB_SOURCE_SCOPE_UID,
  KB_SOURCE_STATUS_UID,
  KB_SOURCE_TYPE_UID,
  KB_SOURCES_UID,
} from "@/lib/kbState";
import { displayKbValue } from "./kbFormat";
import {
  KB_CONTROL_ACTIONS,
  KB_DANGER_ACTIONS,
  KB_PRIMARY_ACTIONS,
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

const ACTION_LABELS: Record<string, TranslationKey> = {
  "CTRL-ADMIN-KB-01-ACT-SEARCH": "kb.act-search",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE": "kb.act-source-create",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE": "kb.act-source-save",
  "CTRL-ADMIN-KB-01-ACT-INGEST-START": "kb.act-ingest-start",
  "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN": "kb.act-citation-open",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE": "kb.act-context-create",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN": "kb.act-replay-open",
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE": "kb.act-learning-create",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP": "kb.act-draft-from-exp",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE": "kb.act-draft-save",
  "CTRL-ADMIN-KB-01-ACT-APPROVE": "kb.act-approve",
  "CTRL-ADMIN-KB-01-ACT-RETURN": "kb.act-return",
  "CTRL-ADMIN-KB-01-ACT-REJECT": "kb.act-reject",
};

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

  const act = useCallback(async (controlUid: string) => {
    const actionUid = KB_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postKbAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
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
  const fieldOf = (uid: string) => displayKbValue(fieldMap.get(uid) ?? null, loading);
  const sources = readJson<AcquisitionSourceRecord[]>(fieldMap.get(KB_SOURCES_UID), []);
  const results = readJson<AcquisitionResultItem[]>(fieldMap.get(KB_RESULTS_UID), []);
  const sourceName = fieldOf(KB_SOURCE_NAME_UID);
  const runStatus = fieldOf(KB_RUN_STATUS_UID);
  const runFail = fieldOf(KB_RUN_FAIL_UID);

  const switchView = (next: KbView) => {
    setView(next);
    setDrawer(null);
    setModalUid(null);
    void act(KB_VIEW_CONTROLS[next]);
  };

  const openDrawer = (next: KbDrawer, uid: string) => {
    setDrawer(next);
    void act(uid);
  };

  const openModal = (uid: string) => {
    setModalUid(uid);
    void act(uid);
  };

  const onAction = (uid: string) => {
    if (uid === "CTRL-ADMIN-KB-01-ACT-SEARCH") {
      openDrawer("search", uid);
      return;
    }
    if (uid === "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN") {
      openDrawer("citation", uid);
      return;
    }
    if (uid === "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN") {
      openDrawer("replay", uid);
      return;
    }
    if (uid === "CTRL-ADMIN-KB-01-ACT-INGEST-START") {
      openDrawer("ingestion", uid);
      return;
    }
    if (
      uid === "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE" ||
      uid === "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE" ||
      uid === "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE" ||
      uid === "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE" ||
      uid === "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP" ||
      uid === "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE" ||
      uid === "CTRL-ADMIN-KB-01-ACT-APPROVE" ||
      uid === "CTRL-ADMIN-KB-01-ACT-RETURN" ||
      uid === "CTRL-ADMIN-KB-01-ACT-REJECT"
    ) {
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
          <strong>{dash}</strong>
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
                   <strong>{sourceName === "—" ? dash : sourceName}</strong>
                 </article>
                 <article className={styles.card}>
                   <h3>{tx("kb.kpi-ingestion")}</h3>
                   <p className={styles.note}>{tx("kb.kpi-ingestion-hint")}</p>
                   <strong>{runStatus === "—" ? dash : runStatus}</strong>
                 </article>
                <article className={styles.card}>
                  <h3>{tx("kb.kpi-experience")}</h3>
                  <p className={styles.note}>{tx("kb.kpi-experience-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("kb.kpi-review")}</h3>
                  <p className={styles.note}>{tx("kb.kpi-review-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("kb.kpi-approved")}</h3>
                  <p className={styles.note}>{tx("kb.kpi-approved-hint")}</p>
                  <strong>{dash}</strong>
                </article>
              </div>
              <div className={styles.actions} data-section-uid="KB-01-SEC-ACTIONS">
                <span className={styles.actionsLabel}>{tx("kb.actions")}</span>
                {viewActions.map((uid) => (
                  <Btn key={uid} uid={uid} label={tx(ACTION_LABELS[uid])} onAct={onAction} disabled={disabled} primary={KB_PRIMARY_ACTIONS.has(uid)} />
                ))}
              </div>
            </section>
            <aside className={styles.rail} data-section-uid="KB-01-SEC-02-WARN" data-component-uid="KB-01-CMP-OVERVIEW-WARN">
               <h2>{tx("kb.warn-title")}</h2>
               <p className={styles.note}>{tx("kb.warn-hint")}</p>
               <strong>{runFail === "—" ? dash : runFail}</strong>
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
                           <td>{source.type}</td>
                           <td>{source.status === "ACTIVE" ? tx("kb.status-available") : tx("kb.status-unavailable")}</td>
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
                 <Kv uid={KB_SOURCE_NAME_UID} label={tx("kb.fld-name")} value={fieldOf(KB_SOURCE_NAME_UID)} />
                 <Kv uid={KB_SOURCE_TYPE_UID} label={tx("kb.fld-type")} value={fieldOf(KB_SOURCE_TYPE_UID)} />
                 <Kv uid={KB_SOURCE_SCOPE_UID} label={tx("kb.fld-scope")} value={fieldOf(KB_SOURCE_SCOPE_UID)} />
                 <Kv uid={KB_SOURCE_RIGHTS_UID} label={tx("kb.fld-rights")} value={fieldOf(KB_SOURCE_RIGHTS_UID)} />
                 <Kv uid={KB_SOURCE_CLASS_UID} label={tx("kb.fld-class")} value={fieldOf(KB_SOURCE_CLASS_UID)} />
                 <Kv uid={KB_ACQ_MODE_UID} label={tx("kb.fld-acq-mode")} value={fieldOf(KB_ACQ_MODE_UID)} />
                 <Kv uid={KB_SOURCE_STATUS_UID} label={tx("kb.fld-status")} value={fieldOf(KB_SOURCE_STATUS_UID)} />
               </div>
              <div className={styles.actions}>
                <span className={styles.actionsLabel}>{tx("kb.actions")}</span>
                {viewActions.map((uid) => (
                  <Btn key={uid} uid={uid} label={tx(ACTION_LABELS[uid])} onAct={onAction} disabled={disabled} primary={KB_PRIMARY_ACTIONS.has(uid)} />
                ))}
              </div>
            </section>
            <aside className={styles.rail} data-section-uid="KB-01-SEC-05" data-component-uid="KB-01-CMP-INGESTION">
              <h2>{tx("kb.ingest-title")}</h2>
              <p className={styles.note}>{tx("kb.ingest-hint")}</p>
               <div className={styles.kvList}>
                 <Kv uid={KB_RUN_ID_UID} label={tx("kb.fld-run-id")} value={fieldOf(KB_RUN_ID_UID)} />
                 <Kv uid={KB_RUN_STATUS_UID} label={tx("kb.fld-run-status")} value={fieldOf(KB_RUN_STATUS_UID)} />
                 <Kv uid={KB_RUN_PROGRESS_UID} label={tx("kb.fld-progress")} value={fieldOf(KB_RUN_PROGRESS_UID)} />
                 <Kv uid={KB_RUN_FAIL_UID} label={tx("kb.fld-failure")} value={fieldOf(KB_RUN_FAIL_UID)} />
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
                       results.map((item) => (
                         <tr key={item.identityValue}>
                           <td>{item.title}</td>
                           <td>{item.type}</td>
                           <td>{item.source}</td>
                           <td>{item.freshness}</td>
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
               <div className={styles.actions}>
                 <span className={styles.actionsLabel}>{tx("kb.actions")}</span>
                 {viewActions.map((uid) => (
                   <Btn key={uid} uid={uid} label={tx(ACTION_LABELS[uid])} onAct={onAction} disabled={disabled} primary={KB_PRIMARY_ACTIONS.has(uid)} />
                 ))}
               </div>
             </section>
             <section className={styles.workspace} data-section-uid="KB-01-SEC-07" data-component-uid="KB-01-CMP-CITATION">
              <div>
                <h2>{tx("kb.citation-title")}</h2>
                <p className={styles.note}>{tx("kb.citation-hint")}</p>
              </div>
              <div className={styles.kvList}>
                <Kv uid="KB-01-FLD-CIT-ID" label={tx("kb.fld-citation")} value={dash} />
                <Kv uid="KB-01-FLD-CIT-SOURCE" label={tx("kb.fld-source-ref")} value={dash} />
                <Kv uid="KB-01-FLD-CIT-LOC" label={tx("kb.fld-location")} value={dash} />
                <Kv uid="KB-01-FLD-CIT-VER" label={tx("kb.fld-version")} value={dash} />
                <Kv uid="KB-01-FLD-CIT-EVIDENCE" label={tx("kb.fld-evidence")} value={dash} />
              </div>
            </section>
            <aside className={styles.rail} data-section-uid="KB-01-SEC-08" data-component-uid="KB-01-CMP-CONTEXT-BASKET">
              <h2>{tx("kb.context-title")}</h2>
              <p className={styles.note}>{tx("kb.context-hint")}</p>
              <div className={styles.kvList}>
                <Kv uid="KB-01-FLD-CTX-CAND-ID" label={tx("kb.fld-candidate")} value={dash} />
                <Kv uid="KB-01-FLD-CTX-CAND-PURPOSE" label={tx("kb.fld-purpose")} value={dash} />
                <Kv uid="KB-01-FLD-CTX-CAND-ITEMS" label={tx("kb.fld-selected")} value={dash} />
                <Kv uid="KB-01-FLD-CTX-CAND-STATE" label={tx("kb.fld-state")} value={dash} />
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
                    <tr>
                      <td>{dash}</td>
                      <td>{dash}</td>
                      <td>{dash}</td>
                      <td>{dash}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className={styles.actions}>
                <span className={styles.actionsLabel}>{tx("kb.actions")}</span>
                {viewActions.map((uid) => (
                  <Btn key={uid} uid={uid} label={tx(ACTION_LABELS[uid])} onAct={onAction} disabled={disabled} primary={KB_PRIMARY_ACTIONS.has(uid)} />
                ))}
              </div>
            </section>
            <section className={styles.workspace} data-section-uid="KB-01-SEC-10" data-component-uid="KB-01-CMP-REPLAY">
              <div>
                <h2>{tx("kb.replay-title")}</h2>
                <p className={styles.note}>{tx("kb.replay-hint")}</p>
              </div>
              <div className={styles.kvList}>
                <Kv uid="KB-01-FLD-REPLAY-SOURCE" label={tx("kb.fld-input")} value={dash} />
                <Kv uid="KB-01-FLD-REPLAY-ROUTE" label={tx("kb.fld-route")} value={dash} />
                <Kv uid="KB-01-FLD-REPLAY-OUTPUT" label={tx("kb.fld-output")} value={dash} />
                <Kv uid="KB-01-FLD-REPLAY-EVAL" label={tx("kb.fld-eval")} value={dash} />
                <Kv uid="KB-01-FLD-REPLAY-CORRECTION" label={tx("kb.fld-correction")} value={dash} />
                <Kv uid="KB-01-FLD-REPLAY-OUTCOME" label={tx("kb.fld-outcome")} value={dash} />
              </div>
            </section>
            <aside className={styles.rail} data-section-uid="KB-01-SEC-11">
              <h2>{tx("kb.learning-title")}</h2>
              <p className={styles.note}>{tx("kb.learning-hint")}</p>
              <div className={styles.kvList}>
                <Kv uid="KB-01-FLD-REPLAY-ROOT" label={tx("kb.fld-root-cause")} value={dash} />
                <Kv uid="KB-01-FLD-LEARN-PATTERN" label={tx("kb.fld-pattern")} value={dash} />
                <Kv uid="KB-01-FLD-LEARN-PROPOSAL" label={tx("kb.fld-proposal")} value={dash} />
                <Kv uid="KB-01-FLD-LEARN-STATE" label={tx("kb.fld-state")} value={dash} />
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
                    <tr>
                      <td>{dash}</td>
                      <td>{dash}</td>
                      <td>{dash}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
            <section className={styles.workspace} data-section-uid="KB-01-SEC-13">
              <div>
                <h2>{tx("kb.draft-title")}</h2>
                <p className={styles.note}>{tx("kb.draft-hint")}</p>
              </div>
              <div className={styles.kvList}>
                <Kv uid="KB-01-FLD-KN-TITLE" label={tx("kb.fld-title")} value={dash} />
                <Kv uid="KB-01-FLD-KN-TYPE" label={tx("kb.fld-type")} value={dash} />
                <Kv uid="KB-01-FLD-KN-SUMMARY" label={tx("kb.fld-summary")} value={dash} />
                <Kv uid="KB-01-FLD-KN-CIT" label={tx("kb.fld-citations")} value={dash} />
                <Kv uid="KB-01-FLD-KN-OUTCOME" label={tx("kb.fld-outcomes")} value={dash} />
                <Kv uid="KB-01-FLD-REV-PREV" label={tx("kb.fld-prev-version")} value={dash} />
                <Kv uid="KB-01-FLD-REV-DIFF" label={tx("kb.fld-diff")} value={dash} />
                <Kv uid="KB-01-FLD-REV-CONFLICT" label={tx("kb.fld-conflict")} value={dash} />
              </div>
              <div className={styles.actions}>
                <span className={styles.actionsLabel}>{tx("kb.actions")}</span>
                {viewActions.map((uid) => (
                  <Btn
                    key={uid}
                    uid={uid}
                    label={tx(ACTION_LABELS[uid])}
                    onAct={onAction}
                    disabled={disabled}
                    primary={KB_PRIMARY_ACTIONS.has(uid)}
                    danger={KB_DANGER_ACTIONS.has(uid)}
                  />
                ))}
              </div>
            </section>
            <aside className={styles.rail} data-section-uid="KB-01-SEC-15" data-component-uid="KB-01-CMP-REVIEW-RAIL">
              <h2>{tx("kb.rail-decision")}</h2>
              <div className={styles.kvList}>
                <Kv uid="KB-01-FLD-REV-CHECK" label={tx("kb.fld-checks")} value={dash} />
                <Kv uid="KB-01-FLD-REV-RATIONALE" label={tx("kb.fld-rationale")} value={dash} />
                <Kv uid="KB-01-FLD-REV-DECISION" label={tx("kb.fld-decision")} value={dash} />
                <Kv uid="KB-01-FLD-REV-BY" label={tx("kb.fld-reviewer")} value={dash} />
              </div>
              <span className={`${styles.pill} ${styles.pillPurple}`}>{tx("kb.human-decision")}</span>
              <div className={styles.block}>{tx("kb.review-block")}</div>
            </aside>
          </>
        ) : null}
      </div>

      <div className={styles.statusStrip} data-section-uid="KB-01-SEC-16" data-component-uid="KB-01-CMP-STATUS">
        <span>
          {tx("kb.status-correlation")} <strong>{dash}</strong>
        </span>
        <span>
          {tx("kb.status-error")} <strong>{error ?? dash}</strong>
        </span>
        <span>
          {tx("kb.status-audit")} <strong>{dash}</strong>
        </span>
        <span>
          {tx("kb.status-disabled")} <strong>{disabled ? tx("kb.status-denied") : dash}</strong>
        </span>
      </div>

      {drawer ? (
        <aside className={styles.drawer} data-section-uid="KB-01-SEC-DRAWER">
          <h3>
            {drawer === "search"
              ? tx("kb.drawer-search")
              : drawer === "citation"
                ? tx("kb.drawer-citation")
                : drawer === "replay"
                  ? tx("kb.drawer-replay")
                  : tx("kb.drawer-ingestion")}
          </h3>
          <p className={styles.note}>{tx("kb.drawer-hint")}</p>
          <strong>{dash}</strong>
          <Btn uid="CTRL-ADMIN-KB-01-ACT-SEARCH" label={tx("global.common.close")} onAct={() => setDrawer(null)} disabled={false} />
        </aside>
      ) : null}

      {modalUid ? (
        <aside className={styles.modal} data-section-uid="KB-01-SEC-MODAL" role="dialog">
          <h3>{tx("kb.modal-title")}</h3>
          <p className={styles.note}>{tx("kb.modal-hint")}</p>
          <strong>{dash}</strong>
          <Btn uid={modalUid} label={tx("global.common.close")} onAct={() => setModalUid(null)} disabled={false} />
        </aside>
      ) : null}
    </div>
  );
}
