"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import {
  AdminStrClientError,
  fetchAdminStrReadModel,
  postAdminStrAction,
  type AdminStrFieldValue,
} from "@/lib/client";
import { displayAdminStrValue } from "./adminStrFormat";
import {
  ADMIN_STR_CONTROL_ACTIONS,
  ADMIN_STR_VIEW_ACTIONS,
  ADMIN_STR_VIEW_CONTROLS,
  ADMIN_STR_VIEWS,
  ADMIN_STR_VISIBLE_CONTROLS,
  type AdminStrDrawer,
  type AdminStrView,
} from "./adminStrControls";
import styles from "./AdminStrVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
  warn = false,
  danger = false,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  warn?: boolean;
  danger?: boolean;
}) {
  const className = [
    styles.btn,
    primary ? styles.btnPrimary : "",
    warn ? styles.btnWarn : "",
    danger ? styles.btnDanger : "",
  ]
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

const VIEW_LABELS: Record<AdminStrView, TranslationKey> = {
  "STR-CURRENT-VIEW-OVERVIEW": "adminStr.view-overview",
  "STR-CURRENT-VIEW-INTELLIGENCE-FACT": "adminStr.view-intelligence",
  "STR-CURRENT-VIEW-PLAYBOOK": "adminStr.view-playbook",
  "STR-CURRENT-VIEW-OPPORTUNITY": "adminStr.view-opportunity",
  "STR-CURRENT-VIEW-DECISION": "adminStr.view-decision",
};

const ACTION_LABELS: Record<string, TranslationKey> = {
  "CTRL-ADMIN-STR-01-ACT-SEARCH": "adminStr.act-search",
  "CTRL-ADMIN-STR-01-ACT-REFRESH": "adminStr.act-refresh",
  "CTRL-ADMIN-STR-01-ACT-NAV-OPEN": "adminStr.act-nav",
  "CTRL-ADMIN-STR-01-ACT-CONFIGURE": "adminStr.act-configure",
  "CTRL-ADMIN-STR-01-ACT-APPROVE": "adminStr.act-approve",
  "CTRL-ADMIN-STR-01-ACT-EXPORT": "adminStr.act-export",
  "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE": "adminStr.act-draft",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE": "adminStr.act-create",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE": "adminStr.act-compare",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE": "adminStr.act-decide",
  "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT": "adminStr.act-adopt",
};

export function AdminStrVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [, setFields] = useState<AdminStrFieldValue[]>([]);
  const [view, setView] = useState<AdminStrView>("STR-CURRENT-VIEW-OVERVIEW");
  const [drawer, setDrawer] = useState<AdminStrDrawer | null>(null);
  const [modalUid, setModalUid] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchAdminStrReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : ADMIN_STR_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof AdminStrClientError ? cause.code : "ADMIN_STR_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(ADMIN_STR_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const act = useCallback(async (controlUid: string) => {
    const actionUid = ADMIN_STR_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postAdminStrAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayAdminStrValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(ADMIN_STR_VISIBLE_CONTROLS), []);
  const viewActions = ADMIN_STR_VIEW_ACTIONS[view];

  const switchView = (next: AdminStrView) => {
    setView(next);
    setDrawer(null);
    setModalUid(null);
    void act(ADMIN_STR_VIEW_CONTROLS[next]);
  };

  const openDrawer = (next: AdminStrDrawer, uid: string) => {
    setDrawer(next);
    void act(uid);
  };

  const openModal = (uid: string) => {
    setModalUid(uid);
    void act(uid);
  };

  const onAction = (uid: string) => {
    if (uid === "CTRL-ADMIN-STR-01-ACT-NAV-OPEN") {
      openDrawer("nav", uid);
      return;
    }
    if (uid === "CTRL-ADMIN-STR-01-ACT-SEARCH") {
      openDrawer("search", uid);
      return;
    }
    if (
      uid === "CTRL-ADMIN-STR-01-ACT-CONFIGURE" ||
      uid === "CTRL-ADMIN-STR-01-ACT-APPROVE" ||
      uid === "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE" ||
      uid === "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE" ||
      uid === "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE" ||
      uid === "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE" ||
      uid === "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT" ||
      uid === "CTRL-ADMIN-STR-01-ACT-EXPORT"
    ) {
      openModal(uid);
      return;
    }
    void act(uid);
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:STR-01"
      data-page-state={pageState}
      data-ui-view={view}
      data-component-count="5"
      data-control-count={visibleUids.size}
      aria-label={tx("adminStr.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("adminStr.error")}
        </div>
      ) : null}

      <nav className={styles.tabs} data-section-uid="SEC-ADMIN-STR-01-VIEWS" aria-label={tx("adminStr.views")}>
        {ADMIN_STR_VIEWS.map((uid) => (
          <button
            key={uid}
            type="button"
            className={`${styles.tab} ${view === uid ? styles.tabActive : ""}`}
            data-control-uid={ADMIN_STR_VIEW_CONTROLS[uid]}
            disabled={disabled}
            onClick={() => switchView(uid)}
          >
            {tx(VIEW_LABELS[uid])}
          </button>
        ))}
      </nav>

      {view === "STR-CURRENT-VIEW-OVERVIEW" ? (
        <div className={styles.contextBar} data-section-uid="SEC-ADMIN-STR-01-OVERVIEW-CONTEXT">
          <div className={styles.contextItem}>
            <span>{tx("adminStr.scope")}</span>
            <strong>{tx("adminStr.scope-value")}</strong>
          </div>
          <div className={styles.contextItem}>
            <span>{tx("adminStr.selected")}</span>
            <strong>{dash}</strong>
          </div>
          <div className={styles.contextItem}>
            <span>{tx("adminStr.truth")}</span>
            <span className={styles.pill}>{tx("adminStr.truth-value")}</span>
          </div>
          <span className={`${styles.pill} ${styles.pillWarn}`}>{tx("adminStr.route-block")}</span>
        </div>
      ) : null}

      {view === "STR-CURRENT-VIEW-DECISION" ? (
        <div className={styles.contextBar} data-section-uid="SEC-ADMIN-STR-01-DECISION-CONTEXT">
          <div className={styles.contextItem}>
            <span>{tx("adminStr.decision-context")}</span>
            <strong>{tx("adminStr.decision-context-value")}</strong>
          </div>
          <span className={`${styles.pill} ${styles.pillPurple}`}>{tx("adminStr.human-decision")}</span>
        </div>
      ) : null}

      {view === "STR-CURRENT-VIEW-INTELLIGENCE-FACT" || view === "STR-CURRENT-VIEW-PLAYBOOK" || view === "STR-CURRENT-VIEW-OPPORTUNITY" ? (
        <div className={styles.contextBar} data-section-uid={`SEC-ADMIN-STR-01-${view}`}>
          <div className={styles.contextItem}>
            <span>{tx("adminStr.scope")}</span>
            <strong>{tx("adminStr.scope-value")}</strong>
          </div>
          <div className={styles.contextItem}>
            <span>{tx("adminStr.selected")}</span>
            <strong>{dash}</strong>
          </div>
        </div>
      ) : null}

      <div className={styles.cols}>
        <section className={styles.workspace} data-section-uid={`SEC-ADMIN-STR-01-${view}`}>
          {view === "STR-CURRENT-VIEW-OVERVIEW" ? (
            <>
              <div>
                <h2>{tx("adminStr.overview-title")}</h2>
                <p className={styles.note}>{tx("adminStr.overview-hint")}</p>
              </div>
              <div className={styles.cardGrid}>
                <article className={styles.card}>
                  <h3>{tx("adminStr.card-health")}</h3>
                  <p className={styles.note}>{tx("adminStr.card-health-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.card-quality")}</h3>
                  <p className={styles.note}>{tx("adminStr.card-quality-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.card-watchlist")}</h3>
                  <p className={styles.note}>{tx("adminStr.card-watchlist-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.card-risk")}</h3>
                  <p className={styles.note}>{tx("adminStr.card-risk-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.card-queue")}</h3>
                  <p className={styles.note}>{tx("adminStr.card-queue-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.card-pack")}</h3>
                  <p className={styles.note}>{tx("adminStr.card-pack-hint")}</p>
                  <strong>{dash}</strong>
                </article>
              </div>
            </>
          ) : null}

          {view === "STR-CURRENT-VIEW-INTELLIGENCE-FACT" ? (
            <>
              <div>
                <h2>{tx("adminStr.intel-title")}</h2>
                <p className={styles.note}>{tx("adminStr.intel-hint")}</p>
              </div>
              <div className={styles.cardGrid}>
                <article className={styles.card}>
                  <h3>{tx("adminStr.intel-source")}</h3>
                  <p className={styles.note}>{tx("adminStr.intel-source-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.intel-watchlist")}</h3>
                  <p className={styles.note}>{tx("adminStr.intel-watchlist-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.intel-fact")}</h3>
                  <p className={styles.note}>{tx("adminStr.intel-fact-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.intel-cohort")}</h3>
                  <p className={styles.note}>{tx("adminStr.intel-cohort-hint")}</p>
                  <strong>{dash}</strong>
                </article>
              </div>
            </>
          ) : null}

          {view === "STR-CURRENT-VIEW-PLAYBOOK" ? (
            <>
              <div>
                <h2>{tx("adminStr.playbook-title")}</h2>
                <p className={styles.note}>{tx("adminStr.playbook-hint")}</p>
              </div>
              <div className={styles.cardGrid}>
                <article className={styles.card}>
                  <h3>{tx("adminStr.playbook-profile")}</h3>
                  <p className={styles.note}>{tx("adminStr.playbook-profile-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.playbook-scope")}</h3>
                  <p className={styles.note}>{tx("adminStr.playbook-scope-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.playbook-hypothesis")}</h3>
                  <p className={styles.note}>{tx("adminStr.playbook-hypothesis-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.playbook-history")}</h3>
                  <p className={styles.note}>{tx("adminStr.playbook-history-hint")}</p>
                  <strong>{dash}</strong>
                </article>
              </div>
            </>
          ) : null}

          {view === "STR-CURRENT-VIEW-OPPORTUNITY" ? (
            <>
              <div>
                <h2>{tx("adminStr.opp-title")}</h2>
                <p className={styles.note}>{tx("adminStr.opp-hint")}</p>
              </div>
              <div className={styles.cardGrid}>
                <article className={styles.card}>
                  <h3>{tx("adminStr.opp-trend")}</h3>
                  <p className={styles.note}>{tx("adminStr.opp-trend-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.opp-momentum")}</h3>
                  <p className={styles.note}>{tx("adminStr.opp-momentum-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.opp-forecast")}</h3>
                  <p className={styles.note}>{tx("adminStr.opp-forecast-hint")}</p>
                  <strong>{dash}</strong>
                </article>
                <article className={styles.card}>
                  <h3>{tx("adminStr.opp-queue")}</h3>
                  <p className={styles.note}>{tx("adminStr.opp-queue-hint")}</p>
                  <strong>{dash}</strong>
                </article>
              </div>
            </>
          ) : null}

          {view === "STR-CURRENT-VIEW-DECISION" ? (
            <>
              <div>
                <h2>{tx("adminStr.decision-title")}</h2>
              </div>
              <article className={styles.card}>
                <h3>{tx("adminStr.compare-title")}</h3>
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>{tx("adminStr.col-option")}</th>
                        <th>{tx("adminStr.col-evidence")}</th>
                        <th>{tx("adminStr.col-risk")}</th>
                        <th>{tx("adminStr.col-cost")}</th>
                        <th>{tx("adminStr.col-uncertainty")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>{tx("adminStr.compare-option")}</td>
                        <td>{tx("adminStr.compare-evidence")}</td>
                        <td>{dash}</td>
                        <td>{tx("adminStr.compare-mask")}</td>
                        <td>{dash}</td>
                      </tr>
                      <tr>
                        <td>{tx("adminStr.compare-option")}</td>
                        <td>{tx("adminStr.compare-evidence")}</td>
                        <td>{dash}</td>
                        <td>{tx("adminStr.compare-mask")}</td>
                        <td>{dash}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </article>
              <p className={styles.note}>{tx("adminStr.flow-title")}</p>
              <div className={styles.flow}>
                <article className={styles.flowCard}>
                  <h3>{tx("adminStr.flow-evidence")}</h3>
                  <p className={styles.note}>{tx("adminStr.flow-evidence-hint")}</p>
                </article>
                <article className={styles.flowCard}>
                  <h3>{tx("adminStr.flow-boundary")}</h3>
                  <p className={styles.note}>{tx("adminStr.flow-boundary-hint")}</p>
                </article>
                <article className={styles.flowCard}>
                  <h3>{tx("adminStr.flow-gate")}</h3>
                  <p className={styles.note}>{tx("adminStr.flow-gate-hint")}</p>
                </article>
                <article className={styles.flowCard}>
                  <h3>{tx("adminStr.flow-handoff")}</h3>
                  <p className={styles.note}>{tx("adminStr.flow-handoff-hint")}</p>
                </article>
              </div>
            </>
          ) : null}

          <div className={styles.actions} data-section-uid="SEC-ADMIN-STR-01-ACTIONS">
            <span className={styles.actionsLabel}>{tx("adminStr.actions")}</span>
            {viewActions.map((uid) => (
              <Btn
                key={uid}
                uid={uid}
                label={tx(ACTION_LABELS[uid])}
                onAct={onAction}
                disabled={disabled}
                primary={uid === "CTRL-ADMIN-STR-01-ACT-SEARCH" || uid === "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE"}
                warn={uid === "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE"}
              />
            ))}
            {view === "STR-CURRENT-VIEW-DECISION" ? <span className={styles.btnDanger}>{tx("adminStr.forbidden-write")}</span> : null}
          </div>
        </section>

        <aside className={styles.rail} data-section-uid="SEC-ADMIN-STR-01-RAIL">
          {view === "STR-CURRENT-VIEW-DECISION" ? (
            <>
              <h2>{tx("adminStr.rail-decision")}</h2>
              <div className={styles.kvList}>
                <Kv label={tx("adminStr.rail-candidate")} value={dash} />
                <Kv label={tx("adminStr.rail-completeness")} value={dash} />
                <div className={styles.kvRow}>
                  <span>{tx("adminStr.rail-finance-visibility")}</span>
                  <span className={`${styles.pill} ${styles.pillWarn}`}>{tx("adminStr.rail-finance")}</span>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("adminStr.rail-operation")}</span>
                  <span className={`${styles.pill} ${styles.pillWarn}`}>{tx("adminStr.rail-binding")}</span>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("adminStr.rail-human-label")}</span>
                  <span className={`${styles.pill} ${styles.pillPurple}`}>{tx("adminStr.rail-human")}</span>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("adminStr.rail-audit-label")}</span>
                  <span className={`${styles.pill} ${styles.pillPurple}`}>{tx("adminStr.rail-audit")}</span>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("adminStr.rail-downstream")}</span>
                  <span className={styles.pill}>{tx("adminStr.rail-owner-module")}</span>
                </div>
              </div>
              <div className={styles.block}>{tx("adminStr.rail-block")}</div>
            </>
          ) : (
            <>
              <h2>{tx("adminStr.rail-title")}</h2>
              <div className={styles.kvList}>
                <Kv label={tx("adminStr.rail-owner")} value={tx("adminStr.rail-owner-value")} />
                <Kv label={tx("adminStr.rail-view")} value={tx(VIEW_LABELS[view])} />
                <Kv label={tx("adminStr.rail-fact")} value={tx("adminStr.rail-fact-value")} />
                <Kv label={tx("adminStr.rail-confidence")} value={tx("adminStr.rail-confidence-value")} />
                <Kv label={tx("adminStr.rail-finance-label")} value={tx("adminStr.rail-finance-value")} />
                <Kv label={tx("adminStr.rail-acquisition")} value={tx("adminStr.rail-acquisition-value")} />
                <Kv label={tx("adminStr.rail-missing")} value={dash} />
                <Kv label={tx("adminStr.rail-unknown")} value={tx("adminStr.rail-unknown-value")} />
              </div>
              <div className={styles.railPills}>
                <span className={styles.pill}>{tx("adminStr.rail-no-second")}</span>
                <span className={styles.pill}>{tx("adminStr.rail-no-fake")}</span>
              </div>
            </>
          )}
        </aside>
      </div>

      {drawer ? (
        <aside className={styles.drawer} data-section-uid="SEC-ADMIN-STR-01-DRAWER">
          <h3>{drawer === "search" ? tx("adminStr.drawer-search") : tx("adminStr.drawer-nav")}</h3>
          <p className={styles.note}>{tx("adminStr.drawer-hint")}</p>
          <strong>{dash}</strong>
          <Btn uid="CTRL-ADMIN-STR-01-ACT-NAV-OPEN" label={tx("global.common.close")} onAct={() => setDrawer(null)} disabled={false} />
        </aside>
      ) : null}

      {modalUid ? (
        <aside className={styles.modal} data-section-uid="SEC-ADMIN-STR-01-MODAL" role="dialog">
          <h3>{tx("adminStr.modal-title")}</h3>
          <p className={styles.note}>{tx("adminStr.modal-hint")}</p>
          <strong>{dash}</strong>
          <Btn uid={modalUid} label={tx("global.common.close")} onAct={() => setModalUid(null)} disabled={false} />
        </aside>
      ) : null}
    </div>
  );
}
