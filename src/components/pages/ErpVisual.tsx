"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { ErpClientError, fetchErpReadModel, postErpAction, type ErpFieldValue } from "@/lib/client";
import { displayErpValue } from "./erpFormat";
import { ERP_CONTROL_ACTIONS, ERP_VIEWS, ERP_VISIBLE_CONTROLS, type ErpView } from "./erpControls";
import styles from "./ErpVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
}) {
  const className = [styles.btn, primary ? styles.btnPrimary : ""].filter(Boolean).join(" ");
  return (
    <button type="button" className={className} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      {label}
    </button>
  );
}

function Field({
  uid,
  label,
  value,
}: {
  uid: string;
  label: string;
  value: string;
}) {
  return (
    <div className={styles.metric} data-control-uid={uid}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Kv({
  uid,
  label,
  value,
  action,
}: {
  uid: string;
  label: string;
  value: string;
  action?: string;
}) {
  return (
    <div className={styles.kvRow} data-control-uid={uid}>
      <span>{label}</span>
      <strong>{value}</strong>
      {action ? <em>{action}</em> : null}
    </div>
  );
}

export function ErpVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [, setFields] = useState<ErpFieldValue[]>([]);
  const [view, setView] = useState<ErpView>("finance_overview");
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchErpReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : ERP_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof ErpClientError ? cause.code : "ERP_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(ERP_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = ERP_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postErpAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayErpValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(ERP_VISIBLE_CONTROLS), []);

  const selectView = (next: ErpView, uid: string) => {
    setView(next);
    void act(uid);
  };

  const openDrawer = (uid = "ERP-01-BTN-DETAIL") => {
    setDrawerOpen(true);
    void act(uid);
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:ERP-01"
      data-page-state={pageState}
      data-ui-view={view}
      data-component-count="8"
      data-control-count={visibleUids.size}
      aria-label={tx("erp.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("erp.error")}
        </div>
      ) : null}

      <header className={styles.heading} data-component-uid="ERP-01-CMP-CONTEXT" data-section-uid="ERP-01-SEC-01" data-control-uid="ERP-01-FLD-SCOPE">
        <h1 className={styles.headingTitle}>{tx("erp.title")}</h1>
        <p className={styles.headingMeta}>{tx("erp.meta")}</p>
      </header>

      <nav className={styles.views} data-section-uid="ERP-01-SEC-02" data-component-uid="ERP-01-CMP-VIEW-BAR">
        {ERP_VIEWS.map((item) => (
          <button
            key={item.uid}
            type="button"
            className={`${styles.viewBtn} ${view === item.key ? styles.viewActive : ""}`}
            data-control-uid={item.uid}
            disabled={disabled}
            onClick={() => selectView(item.key, item.uid)}
          >
            {tx(item.labelKey)}
          </button>
        ))}
      </nav>

      <div className={styles.cols}>
        {view === "finance_overview" ? (
          <section className={styles.workspace} data-section-uid="ERP-01-SEC-03" data-component-uid="ERP-01-CMP-FINANCE">
            <h2>{tx("erp.finance-title")}</h2>
            <p className={styles.note}>{tx("erp.finance-hint")}</p>
            <div className={styles.statusBar} data-control-uid="ERP-01-FLD-SNAPSHOT">
              <div className={styles.statusItem}>
                <span>{tx("erp.status-scope")}</span>
                <strong>{tx("erp.status-scope-value")}</strong>
                <i className={`${styles.dot} ${styles.dotOk}`} />
              </div>
              <div className={styles.statusItem} data-control-uid="ERP-01-FLD-SNAPSHOT">
                <span>{tx("erp.status-snapshot")}</span>
                <strong>{dash}</strong>
                <i className={`${styles.dot} ${styles.dotInfo}`} />
              </div>
              <div className={styles.statusItem} data-control-uid="ERP-01-FLD-FRESHNESS">
                <span>{tx("erp.status-freshness")}</span>
                <strong>{dash}</strong>
                <i className={`${styles.dot} ${styles.dotWarn}`} />
              </div>
              <div className={styles.statusItem}>
                <span>{tx("erp.status-completeness")}</span>
                <strong>{dash}</strong>
                <i className={`${styles.dot} ${styles.dotWarn}`} />
              </div>
            </div>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("erp.actual-title")}</h3>
                <div className={styles.metricGrid}>
                  <Field uid="ERP-01-FLD-FIN-COST" label={tx("erp.field-cost")} value={dash} />
                  <Field uid="ERP-01-FLD-FIN-REVENUE" label={tx("erp.field-revenue")} value={dash} />
                  <Field uid="ERP-01-FLD-FIN-CASHFLOW" label={tx("erp.field-cashflow")} value={dash} />
                  <Field uid="ERP-01-FLD-FIN-CAPACITY" label={tx("erp.field-capacity")} value={dash} />
                </div>
              </div>
              <div className={styles.card}>
                <h3>{tx("erp.decision-title")}</h3>
                <div className={styles.decisionList}>
                  <div className={styles.decisionRow} data-control-uid="ERP-01-FLD-FIN-FORECAST">
                    <span>{tx("erp.field-forecast")}</span>
                    <strong>{dash}</strong>
                    <i className={`${styles.dot} ${styles.dotInfo}`} />
                  </div>
                  <div className={styles.decisionRow} data-control-uid="ERP-01-FLD-FIN-GUARDRAILS">
                    <span>{tx("erp.field-guardrails")}</span>
                    <strong>{dash}</strong>
                    <i className={`${styles.dot} ${styles.dotWarn}`} />
                  </div>
                  <div className={styles.decisionRow} data-control-uid="ERP-01-FLD-FIN-RECOMMENDATION-BOUNDARY">
                    <span>{tx("erp.field-boundary")}</span>
                    <strong>{tx("erp.field-boundary-value")}</strong>
                    <i className={`${styles.dot} ${styles.dotOk}`} />
                  </div>
                </div>
              </div>
            </div>
            <div className={styles.card} data-section-uid="ERP-01-SEC-07">
              <h3>{tx("erp.export-title")}</h3>
              <p className={styles.note}>{tx("erp.export-hint")}</p>
              <div className={styles.actions}>
                <Btn uid="ERP-01-BTN-FACTPACK" label={tx("erp.btn-factpack")} onAct={act} disabled={disabled} primary />
                <Btn uid="ERP-01-BTN-GUARDRAILS" label={tx("erp.btn-guardrails")} onAct={act} disabled={disabled} />
                <Btn uid="ERP-01-BTN-FORECAST" label={tx("erp.btn-forecast")} onAct={act} disabled={disabled} />
                <Btn uid="ERP-01-BTN-EXPORT" label={tx("erp.btn-export")} onAct={act} disabled={disabled} />
              </div>
            </div>
          </section>
        ) : null}

        {view === "connector_mapping" || view === "sync_quality" ? (
          <section
            className={styles.workspace}
            data-section-uid={view === "connector_mapping" ? "ERP-01-SEC-04" : "ERP-01-SEC-05"}
            data-component-uid={view === "connector_mapping" ? "ERP-01-CMP-CONNECTOR" : "ERP-01-CMP-SYNC"}
          >
            <h2>{tx("erp.connector-title")}</h2>
            <p className={styles.note}>{tx("erp.connector-hint")}</p>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("erp.connector-card")}</h3>
                <div className={styles.kvList}>
                  <Kv uid="ERP-01-FLD-CONN-CONNECTOR-ID" label={tx("erp.field-connector-id")} value={dash} />
                  <Kv uid="ERP-01-FLD-CONN-PROVIDER-KEY" label={tx("erp.field-provider")} value={dash} />
                  <Kv uid="ERP-01-FLD-CONN-ADAPTER-KEY" label={tx("erp.field-adapter")} value={dash} />
                  <Kv uid="ERP-01-FLD-CONN-SECRET-REFERENCE-ID" label={tx("erp.field-secret-ref")} value={dash} />
                  <Kv uid="ERP-01-FLD-CONN-ENTITY-SCOPE" label={tx("erp.field-entity-scope")} value={dash} />
                  <Kv uid="ERP-01-FLD-CONN-CONNECTION-STATUS" label={tx("erp.field-connection-status")} value={dash} />
                  <Kv uid="ERP-01-FLD-CONN-MAPPING-VERSION" label={tx("erp.field-mapping-version")} value={dash} />
                </div>
                <div className={styles.actions}>
                  <Btn uid="ERP-01-BTN-CONNECTOR-CREATE" label={tx("erp.btn-connector-create")} onAct={act} disabled={disabled} primary />
                  <Btn uid="ERP-01-BTN-CONNECTOR-UPDATE" label={tx("erp.btn-connector-update")} onAct={act} disabled={disabled} />
                  <Btn uid="ERP-01-BTN-CONNECTOR-VALIDATE" label={tx("erp.btn-connector-validate")} onAct={act} disabled={disabled} />
                </div>
              </div>
              <div className={styles.card}>
                <h3>{tx("erp.quality-card")}</h3>
                <div className={`${styles.kvRow} ${styles.kvHead}`}>
                  <span>{tx("erp.col-item")}</span>
                  <strong>{tx("erp.col-state")}</strong>
                  <em>{tx("erp.col-action")}</em>
                </div>
                <Kv uid="ERP-01-FLD-CONN-MAPPING-VERSION" label={tx("erp.row-mapping")} value={dash} action={tx("erp.btn-mapping-validate")} />
                <Kv uid="ERP-01-FLD-SYNC-SNAPSHOT-ID" label={tx("erp.row-snapshot")} value={dash} action={tx("erp.btn-snapshot-refresh")} />
                <Kv uid="ERP-01-FLD-SYNC-FRESHNESS-AT" label={tx("erp.row-freshness")} value={dash} action={tx("erp.action-read")} />
                <Kv uid="ERP-01-FLD-SYNC-COMPLETENESS" label={tx("erp.row-completeness")} value={dash} action={tx("erp.action-read")} />
                <Kv uid="ERP-01-FLD-SYNC-LAST-SYNC-STATUS" label={tx("erp.row-last-sync")} value={dash} action={tx("erp.btn-sync-status")} />
                <div className={styles.actions}>
                  <Btn uid="ERP-01-BTN-MAPPING-VALIDATE" label={tx("erp.btn-mapping-validate")} onAct={act} disabled={disabled} />
                  <Btn uid="ERP-01-BTN-SNAPSHOT-REFRESH" label={tx("erp.btn-snapshot-refresh")} onAct={act} disabled={disabled} />
                  <Btn uid="ERP-01-BTN-SYNC-CREATE" label={tx("erp.btn-sync-create")} onAct={act} disabled={disabled} primary />
                  <Btn uid="ERP-01-BTN-SYNC-STATUS" label={tx("erp.btn-sync-status")} onAct={act} disabled={disabled} />
                  <Btn uid="ERP-01-BTN-SYNC-RETRY" label={tx("erp.btn-sync-retry")} onAct={act} disabled={disabled} />
                  <Btn uid="ERP-01-BTN-FAILURE-GET" label={tx("erp.btn-failure-get")} onAct={openDrawer} disabled={disabled} />
                </div>
              </div>
            </div>
            <div className={styles.card}>
              <h3>{tx("erp.recovery-title")}</h3>
              <p className={styles.note}>{tx("erp.recovery-hint")}</p>
            </div>
          </section>
        ) : null}

        <GovernanceRail t={tx} dash={dash} disabled={disabled} view={view} onDrawer={openDrawer} />
      </div>

      {drawerOpen ? (
        <section className={styles.drawer} data-section-uid="ERP-01-SEC-08" data-component-uid="ERP-01-CMP-DRAWER">
          <h3>{tx("erp.drawer-title")}</h3>
          <p className={styles.note}>{tx("erp.drawer-hint")}</p>
          <div className={styles.kvList}>
            <Kv uid="ERP-01-FLD-SYNC-FAILURE-ID" label={tx("erp.field-failure-id")} value={dash} />
            <Kv uid="ERP-01-FLD-AUDIT-REF" label={tx("erp.field-audit-ref")} value={dash} />
            <Kv uid="ERP-01-FLD-READINESS" label={tx("erp.field-readiness")} value={dash} />
            <Kv uid="ERP-01-FLD-SYNC-CURRENCY-TIMEZONE" label={tx("erp.field-currency-timezone")} value={dash} />
          </div>
          <button type="button" className={styles.btn} onClick={() => setDrawerOpen(false)}>
            {tx("global.common.close")}
          </button>
        </section>
      ) : null}
    </div>
  );
}

function GovernanceRail({
  t,
  dash,
  disabled,
  view,
  onDrawer,
}: {
  t: (key: TranslationKey) => string;
  dash: string;
  disabled: boolean;
  view: ErpView;
  onDrawer: () => void;
}) {
  return (
    <aside className={styles.rail} data-section-uid="ERP-01-SEC-06" data-component-uid="ERP-01-CMP-GOVERNANCE">
      <h2>{t("erp.rail-title")}</h2>
      {view === "finance_overview" ? (
        <>
          <div className={styles.railCard}>
            <span>{t("erp.rail-finance-perm")}</span>
            <strong>{t("erp.rail-finance-perm-value")}</strong>
            <i className={`${styles.dot} ${styles.dotOk}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-data-truth")}</span>
            <strong>{t("erp.rail-data-truth-value")}</strong>
            <i className={`${styles.dot} ${styles.dotWarn}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-write-boundary")}</span>
            <strong>{t("erp.rail-write-boundary-value")}</strong>
            <i className={`${styles.dot} ${styles.dotDanger}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-external")}</span>
            <strong>{t("erp.rail-external-value")}</strong>
            <i className={`${styles.dot} ${styles.dotDanger}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-truthful")}</span>
            <strong>{t("erp.rail-truthful-value")}</strong>
            <i className={`${styles.dot} ${styles.dotInfo}`} />
          </div>
        </>
      ) : (
        <>
          <div className={styles.railCard}>
            <span>{t("erp.rail-secret")}</span>
            <strong>{t("erp.rail-secret-value")}</strong>
            <i className={`${styles.dot} ${styles.dotOk}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-connector-state")}</span>
            <strong>{t("erp.rail-connector-state-value")}</strong>
            <i className={`${styles.dot} ${styles.dotInfo}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-snapshot-state")}</span>
            <strong>{t("erp.rail-snapshot-state-value")}</strong>
            <i className={`${styles.dot} ${styles.dotWarn}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-retry")}</span>
            <strong>{t("erp.rail-retry-value")}</strong>
            <i className={`${styles.dot} ${styles.dotWarn}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-audit")}</span>
            <strong>{t("erp.rail-audit-value")}</strong>
            <i className={`${styles.dot} ${styles.dotOk}`} />
          </div>
        </>
      )}
      <div className={styles.railActions}>
        <button type="button" className={styles.btn} data-control-uid="ERP-01-BTN-DETAIL" disabled={disabled} onClick={onDrawer}>
          {t("erp.btn-detail")}
        </button>
      </div>
      <p className={styles.note} data-control-uid="ERP-01-FLD-READINESS">
        {t("erp.field-readiness")}: {dash}
      </p>
    </aside>
  );
}
