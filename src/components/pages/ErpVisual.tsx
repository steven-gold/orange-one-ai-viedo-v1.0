"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { ErpClientError, fetchErpReadModel, postErpAction, type ErpFieldValue } from "@/lib/client";
import { deriveErpPageState, displayErpValue } from "./erpFormat";
import { ERP_CONTROL_ACTIONS, ERP_VIEWS, ERP_VISIBLE_CONTROLS, type ErpView } from "./erpControls";
import styles from "./ErpVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

const CONNECTOR_PAYLOAD_PROMPT = JSON.stringify(
  {
    provider_key: "",
    adapter_key: "",
    secret_reference_id: "",
    entity_scope: "",
    mapping_version: 1,
    mapping_entity_name: "",
    mapping_source_schema: "",
    mapping_target_schema: "",
    mapping_transform_spec: "",
    data_classification: "",
  },
  null,
  2,
);

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
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [contractError, setContractError] = useState<{ code: string; detail: string; recovery?: string } | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<ErpFieldValue[]>([]);
  const [view, setView] = useState<ErpView>("finance_overview");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const valueOf = useCallback(
    (uid: string): string | null => fields.find((row) => row.controlUid === uid)?.value ?? null,
    [fields],
  );

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
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
  }, [tick]);

  const act = useCallback(
    async (controlUid: string, payload?: string) => {
      const actionUid = ERP_CONTROL_ACTIONS[controlUid];
      if (!actionUid) return;
      try {
        await postErpAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, payload);
      } catch {
        // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
      }
      setTick((n) => n + 1);
    },
    [],
  );

  const runSchemaAction = useCallback(
    async (controlUid: string, payloadTemplate: string) => {
      const raw = window.prompt("JSON payload（registered schema）", payloadTemplate);
      if (raw === null) return;
      await act(controlUid, raw);
    },
    [act],
  );

  const disabled = !authorized && !loading;
  const tx = (key: TranslationKey) => t(key);
  const dash = displayErpValue(null, loading);
  const v = valueOf;
  const visibleUids = useMemo(() => new Set<string>(ERP_VISIBLE_CONTROLS), []);

  useEffect(() => {
    const raw = v("ERP-01-STATE-ERROR");
    if (!raw) {
      setContractError(null);
      return;
    }
    try {
      setContractError(JSON.parse(raw) as { code: string; detail: string; recovery?: string });
    } catch {
      setContractError(null);
    }
  }, [v]);

  const connectorStatus = v("ERP-01-FLD-CONN-CONNECTION-STATUS");
  const syncJobsRaw = v("ERP-01-STATE-SYNC-JOBS");
  const snapshotRaw = v("ERP-01-STATE-SNAPSHOT");
  const pageState = deriveErpPageState({
    loading,
    authorized,
    errorCode: contractError?.code ?? null,
    connectorStatus,
    syncJobsRaw,
    snapshotRaw,
    completenessRaw: v("ERP-01-FLD-SYNC-COMPLETENESS"),
  });

  // Real drawer references: connector version/correlation and the actual
  // retry eligibility (registered FAILED job recovery or the exact
  // contract recovery text).
  let connectorRef = dash;
  let retryEligibility = dash;
  try {
    const raw = v("ERP-01-STATE-CONNECTOR");
    const connector = raw ? (JSON.parse(raw) as { connectorId?: string; version?: number }) : null;
    if (connector?.connectorId) connectorRef = `${connector.connectorId} · v${connector.version ?? "—"}`;
  } catch {
    connectorRef = dash;
  }
  try {
    const jobs = syncJobsRaw ? (JSON.parse(syncJobsRaw) as Array<{ jobId?: string; status?: string }>) : [];
    const failed = [...jobs].reverse().find((job) => job.status === "FAILED");
    retryEligibility = failed?.jobId ? `RETRY-ELIGIBLE · ${failed.jobId}` : (contractError?.recovery ?? dash);
  } catch {
    retryEligibility = contractError?.recovery ?? dash;
  }

  const selectView = (next: ErpView, uid: string) => {
    setView(next);
    void act(uid);
  };

  const openDrawer = (uid = "ERP-01-BTN-DETAIL") => {
    setDrawerOpen(true);
    void act(uid);
  };

  const readiness = v("ERP-01-FLD-READINESS");
  const factPack = v("ERP-01-STATE-FACTPACK");

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
      {contractError ? (
        <div className={styles.error} role="alert">
          {contractError.code} · {contractError.detail}
          {contractError.recovery ? ` · ${contractError.recovery}` : ""}
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
              <div className={styles.statusItem} data-control-uid="ERP-01-FLD-SCOPE">
                <span>{tx("erp.status-scope")}</span>
                <strong>{v("ERP-01-FLD-SCOPE") ?? dash}</strong>
                <i className={`${styles.dot} ${styles.dotOk}`} />
              </div>
              <div className={styles.statusItem} data-control-uid="ERP-01-FLD-SNAPSHOT">
                <span>{tx("erp.status-snapshot")}</span>
                <strong>{v("ERP-01-FLD-SNAPSHOT") ?? dash}</strong>
                <i className={`${styles.dot} ${styles.dotInfo}`} />
              </div>
              <div className={styles.statusItem} data-control-uid="ERP-01-FLD-FRESHNESS">
                <span>{tx("erp.status-freshness")}</span>
                <strong>{v("ERP-01-FLD-FRESHNESS") ?? dash}</strong>
                <i className={`${styles.dot} ${styles.dotWarn}`} />
              </div>
              <div className={styles.statusItem} data-control-uid="ERP-01-FLD-SYNC-COMPLETENESS">
                <span>{tx("erp.status-completeness")}</span>
                <strong>{v("ERP-01-FLD-SYNC-COMPLETENESS") ?? dash}</strong>
                <i className={`${styles.dot} ${styles.dotWarn}`} />
              </div>
            </div>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("erp.actual-title")}</h3>
                <div className={styles.metricGrid}>
                  <Field uid="ERP-01-FLD-FIN-COST" label={tx("erp.field-cost")} value={v("ERP-01-FLD-FIN-COST") ?? dash} />
                  <Field uid="ERP-01-FLD-FIN-REVENUE" label={tx("erp.field-revenue")} value={v("ERP-01-FLD-FIN-REVENUE") ?? dash} />
                  <Field uid="ERP-01-FLD-FIN-CASHFLOW" label={tx("erp.field-cashflow")} value={v("ERP-01-FLD-FIN-CASHFLOW") ?? dash} />
                  <Field uid="ERP-01-FLD-FIN-CAPACITY" label={tx("erp.field-capacity")} value={v("ERP-01-FLD-FIN-CAPACITY") ?? dash} />
                </div>
              </div>
              <div className={styles.card}>
                <h3>{tx("erp.decision-title")}</h3>
                <div className={styles.decisionList}>
                  <div className={styles.decisionRow} data-control-uid="ERP-01-FLD-FIN-FORECAST">
                    <span>{tx("erp.field-forecast")}</span>
                    <strong>{v("ERP-01-FLD-FIN-FORECAST") ?? dash}</strong>
                    <i className={`${styles.dot} ${styles.dotInfo}`} />
                  </div>
                  <div className={styles.decisionRow} data-control-uid="ERP-01-FLD-FIN-GUARDRAILS">
                    <span>{tx("erp.field-guardrails")}</span>
                    <strong>{v("ERP-01-FLD-FIN-GUARDRAILS") ?? dash}</strong>
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
                  <Kv uid="ERP-01-FLD-CONN-CONNECTOR-ID" label={tx("erp.field-connector-id")} value={v("ERP-01-FLD-CONN-CONNECTOR-ID") ?? dash} />
                  <Kv uid="ERP-01-FLD-CONN-PROVIDER-KEY" label={tx("erp.field-provider")} value={v("ERP-01-FLD-CONN-PROVIDER-KEY") ?? dash} />
                  <Kv uid="ERP-01-FLD-CONN-ADAPTER-KEY" label={tx("erp.field-adapter")} value={v("ERP-01-FLD-CONN-ADAPTER-KEY") ?? dash} />
                  <Kv uid="ERP-01-FLD-CONN-SECRET-REFERENCE-ID" label={tx("erp.field-secret-ref")} value={v("ERP-01-FLD-CONN-SECRET-REFERENCE-ID") ?? dash} />
                  <Kv uid="ERP-01-FLD-CONN-ENTITY-SCOPE" label={tx("erp.field-entity-scope")} value={v("ERP-01-FLD-CONN-ENTITY-SCOPE") ?? dash} />
                  <Kv uid="ERP-01-FLD-CONN-CONNECTION-STATUS" label={tx("erp.field-connection-status")} value={v("ERP-01-FLD-CONN-CONNECTION-STATUS") ?? dash} />
                  <Kv uid="ERP-01-FLD-CONN-MAPPING-VERSION" label={tx("erp.field-mapping-version")} value={v("ERP-01-FLD-CONN-MAPPING-VERSION") ?? dash} />
                </div>
                <div className={styles.actions}>
                  <Btn uid="ERP-01-BTN-CONNECTOR-CREATE" label={tx("erp.btn-connector-create")} onAct={(uid) => void runSchemaAction(uid, CONNECTOR_PAYLOAD_PROMPT)} disabled={disabled} primary />
                  <Btn uid="ERP-01-BTN-CONNECTOR-UPDATE" label={tx("erp.btn-connector-update")} onAct={(uid) => void runSchemaAction(uid, '{"expected_version":1}')} disabled={disabled} />
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
                <Kv uid="ERP-01-FLD-CONN-MAPPING-VERSION" label={tx("erp.row-mapping")} value={v("ERP-01-FLD-CONN-MAPPING-VERSION") ?? dash} action={tx("erp.btn-mapping-validate")} />
                <Kv uid="ERP-01-FLD-SYNC-SNAPSHOT-ID" label={tx("erp.row-snapshot")} value={v("ERP-01-FLD-SYNC-SNAPSHOT-ID") ?? dash} action={tx("erp.btn-snapshot-refresh")} />
                <Kv uid="ERP-01-FLD-SYNC-FRESHNESS-AT" label={tx("erp.row-freshness")} value={v("ERP-01-FLD-SYNC-FRESHNESS-AT") ?? dash} action={tx("erp.action-read")} />
                <Kv uid="ERP-01-FLD-SYNC-COMPLETENESS" label={tx("erp.row-completeness")} value={v("ERP-01-FLD-SYNC-COMPLETENESS") ?? dash} action={tx("erp.action-read")} />
                <Kv uid="ERP-01-FLD-SYNC-LAST-SYNC-STATUS" label={tx("erp.row-last-sync")} value={v("ERP-01-FLD-SYNC-LAST-SYNC-STATUS") ?? dash} action={tx("erp.btn-sync-status")} />
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

        <GovernanceRail t={tx} dash={dash} disabled={disabled} view={view} onDrawer={openDrawer} readiness={readiness} connectorState={connectorStatus ?? dash} snapshotState={v("ERP-01-FLD-SYNC-COMPLETENESS") ?? dash} />
      </div>

      {drawerOpen ? (
        <section className={styles.drawer} data-section-uid="ERP-01-SEC-08" data-component-uid="ERP-01-CMP-DRAWER">
          <h3>{tx("erp.drawer-title")}</h3>
          <p className={styles.note}>{tx("erp.drawer-hint")}</p>
          <div className={styles.kvList}>
            <Kv uid="ERP-01-FLD-SYNC-FAILURE-ID" label={tx("erp.field-failure-id")} value={v("ERP-01-FLD-SYNC-FAILURE-ID") ?? dash} />
            <Kv uid="ERP-01-FLD-AUDIT-REF" label={tx("erp.field-audit-ref")} value={v("ERP-01-FLD-AUDIT-REF") ?? dash} />
            <Kv uid="ERP-01-FLD-READINESS" label={tx("erp.field-readiness")} value={readiness ?? dash} />
            <Kv uid="ERP-01-FLD-CONN-CONNECTOR-ID" label={tx("erp.drawer-version")} value={connectorRef} />
            <Kv uid="ERP-01-FLD-SYNC-LAST-SYNC-STATUS" label={tx("erp.drawer-retry")} value={retryEligibility} />
            <Kv uid="ERP-01-FLD-SYNC-CURRENCY-TIMEZONE" label={tx("erp.field-currency-timezone")} value={v("ERP-01-FLD-SYNC-CURRENCY-TIMEZONE") ?? dash} />
          </div>
          {factPack ? <pre className={styles.note}>{factPack.slice(0, 800)}</pre> : null}
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
  readiness,
  connectorState,
  snapshotState,
}: {
  t: (key: TranslationKey) => string;
  dash: string;
  disabled: boolean;
  view: ErpView;
  onDrawer: () => void;
  readiness: string | null;
  connectorState: string;
  snapshotState: string;
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
            <strong data-control-uid="ERP-01-FLD-CONN-CONNECTION-STATUS">{connectorState || t("erp.rail-connector-state-value")}</strong>
            <i className={`${styles.dot} ${styles.dotInfo}`} />
          </div>
          <div className={styles.railCard}>
            <span>{t("erp.rail-snapshot-state")}</span>
            <strong data-control-uid="ERP-01-FLD-SYNC-COMPLETENESS">{snapshotState || t("erp.rail-snapshot-state-value")}</strong>
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
        {t("erp.field-readiness")}: {readiness ?? dash}
      </p>
    </aside>
  );
}
