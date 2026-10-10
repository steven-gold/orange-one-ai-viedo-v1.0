"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { AiapiClientError, fetchAiapiReadModel, postAiapiAction, type AiapiFieldValue } from "@/lib/client";
import { displayAiapiValue } from "./aiapiFormat";
import {
  AIAPI_CONTROL_ACTIONS,
  AIAPI_PRO_DESC_FIELDS,
  AIAPI_PROFILE_GROUPS,
  AIAPI_TABLE_COLUMNS,
  AIAPI_VIEWS,
  AIAPI_VISIBLE_CONTROLS,
  type AiapiView,
} from "./aiapiControls";
import styles from "./AiapiVisual.module.css";

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
  const className = [styles.btn, primary ? styles.btnPrimary : "", danger ? styles.btnDanger : ""].filter(Boolean).join(" ");
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
}: {
  uid: string;
  label: string;
  value: string;
}) {
  return (
    <div className={styles.kvRow} data-control-uid={uid}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function AiapiVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [, setFields] = useState<AiapiFieldValue[]>([]);
  const [view, setView] = useState<AiapiView>("provider_api");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [modalUid, setModalUid] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchAiapiReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : AIAPI_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof AiapiClientError ? cause.code : "AIAPI_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(AIAPI_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = AIAPI_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postAiapiAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayAiapiValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(AIAPI_VISIBLE_CONTROLS), []);

  const selectView = (next: AiapiView, uid: string) => {
    setView(next);
    void act(uid);
  };

  const openDrawer = (uid: string) => {
    setDrawerOpen(true);
    void act(uid);
  };

  const openModal = (uid: string) => {
    setModalUid(uid);
    void act(uid);
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:AIAPI-01"
      data-page-state={pageState}
      data-ui-view={view}
      data-component-count="10"
      data-control-count={visibleUids.size}
      aria-label={tx("aiapi.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("aiapi.error")}
        </div>
      ) : null}

      <header className={styles.heading} data-component-uid="AIAPI-01-CMP-CONTEXT" data-section-uid="AIAPI-01-SEC-01">
        <h1 className={styles.headingTitle}>{tx("aiapi.title")}</h1>
        <p className={styles.headingMeta}>{tx("aiapi.meta")}</p>
      </header>

      <nav className={styles.views} data-section-uid="AIAPI-01-SEC-02" data-component-uid="AIAPI-01-CMP-VIEW-BAR">
        {AIAPI_VIEWS.map((item) => (
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

      {view === "overview" || view === "provider_api" ? (
        <div className={styles.toolbar} data-section-uid="AIAPI-01-SEC-03" data-component-uid="AIAPI-01-CMP-QUICK-ACTIONS">
          <div className={styles.actions}>
            <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-CREATE-PROFILE" label={tx("aiapi.btn-create")} onAct={openModal} disabled={disabled} primary />
            <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-SET-CREDENTIAL" label={tx("aiapi.btn-set-key")} onAct={openModal} disabled={disabled} />
            <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE" label={tx("aiapi.btn-test")} onAct={act} disabled={disabled} />
            <Btn uid="AIAPI-01-BTN-RUN-SANDBOX-TEST" label={tx("aiapi.btn-sandbox")} onAct={openModal} disabled={disabled} />
          </div>
          <input
            className={styles.search}
            data-control-uid="AIAPI-01-FLD-SEARCH"
            disabled={disabled}
            placeholder={tx("aiapi.search-placeholder")}
            readOnly
          />
        </div>
      ) : null}

      <div className={styles.cols}>
        {view === "overview" ? (
          <section className={styles.workspace} data-section-uid="AIAPI-01-SEC-04" data-component-uid="AIAPI-01-CMP-OVERVIEW">
            <h2>{tx("aiapi.overview-title")}</h2>
            <p className={styles.note}>{tx("aiapi.overview-hint")}</p>
            <div className={styles.statusBar}>
              <div className={styles.statusItem} data-control-uid="AIAPI-01-FLD-OV-PROVIDER">
                <span>{tx("aiapi.ov-provider")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.statusItem} data-control-uid="AIAPI-01-FLD-OV-ROUTE">
                <span>{tx("aiapi.ov-route")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.statusItem} data-control-uid="AIAPI-01-FLD-OV-CAPABILITY">
                <span>{tx("aiapi.ov-capability")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.statusItem} data-control-uid="AIAPI-01-FLD-OV-JOB">
                <span>{tx("aiapi.ov-job")}</span>
                <strong>{dash}</strong>
              </div>
            </div>
            <div className={styles.metricGrid}>
              <Field uid="AIAPI-01-FLD-OV-COST" label={tx("aiapi.ov-cost")} value={dash} />
              <Field uid="AIAPI-01-FLD-OV-HEALTH" label={tx("aiapi.ov-health")} value={dash} />
              <Field uid="AIAPI-01-FLD-OV-INCIDENT" label={tx("aiapi.ov-incident")} value={dash} />
              <Field uid="AIAPI-01-FLD-OPS-QUEUE" label={tx("aiapi.ops-queue")} value={dash} />
            </div>
          </section>
        ) : null}

        {view === "provider_api" ? (
          <section className={styles.workspace} data-section-uid="AIAPI-01-SEC-05" data-component-uid="AIAPI-01-CMP-PROVIDER">
            <h2>{tx("aiapi.provider-title")}</h2>
            <p className={styles.note}>{tx("aiapi.provider-hint")}</p>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {AIAPI_TABLE_COLUMNS.map((col) => (
                      <th key={col}>{tx(col)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className={styles.emptyRow}>
                    <td colSpan={AIAPI_TABLE_COLUMNS.length}>{dash}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className={styles.actions}>
              <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-VIEW-PROFILE" label={tx("aiapi.btn-view")} onAct={openDrawer} disabled={disabled} />
              <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-UPDATE-PROFILE" label={tx("aiapi.btn-edit")} onAct={openModal} disabled={disabled} />
              <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE" label={tx("aiapi.btn-row-test")} onAct={act} disabled={disabled} />
              <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-RETIRE-PROFILE" label={tx("aiapi.btn-retire")} onAct={openModal} disabled={disabled} />
              <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-SET-CREDENTIAL" label={tx("aiapi.btn-set-key")} onAct={openModal} disabled={disabled} />
              <Btn uid="CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-DELETE-CREDENTIAL" label={tx("aiapi.btn-delete-key")} onAct={openModal} disabled={disabled} danger />
            </div>
            <div className={styles.card} data-section-uid="AIAPI-01-SEC-06">
              <h3>{tx("aiapi.editor-title")}</h3>
              <p className={styles.note}>{tx("aiapi.editor-hint")}</p>
              <div className={styles.groupGrid}>
                {AIAPI_PROFILE_GROUPS.map((group) => (
                  <div key={group.uid} className={styles.groupChip} data-control-uid={group.uid}>
                    {tx(group.labelKey)}
                  </div>
                ))}
              </div>
              <div className={styles.actions}>
                <Btn uid="AIAPI-01-BTN-CONFIGURE-GOVERNED-RESOURCE" label={tx("aiapi.btn-configure")} onAct={openModal} disabled={disabled} />
                <Btn uid="AIAPI-01-BTN-APPROVE-GOVERNED-RESOURCE" label={tx("aiapi.btn-approve")} onAct={openModal} disabled={disabled} />
              </div>
            </div>
          </section>
        ) : null}

        {view === "routing_test" ? (
          <section className={styles.workspace} data-section-uid="AIAPI-01-SEC-07" data-component-uid="AIAPI-01-CMP-ROUTING">
            <h2>{tx("aiapi.routing-title")}</h2>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("aiapi.candidate-title")}</h3>
                <p className={styles.note}>{tx("aiapi.candidate-hint")}</p>
                <div className={styles.kvList}>
                  <Kv uid="AIAPI-01-FLD-OV-PROVIDER" label={tx("aiapi.col-provider")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-OV-CAPABILITY" label={tx("aiapi.col-capability")} value={dash} />
                </div>
                <Btn uid="CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-CREATE-GROUP" label={tx("aiapi.btn-create-group")} onAct={openModal} disabled={disabled} primary />
              </div>
              <div className={styles.card}>
                <h3>{tx("aiapi.preflight-title")}</h3>
                <div className={styles.kvList}>
                  <Kv uid="AIAPI-01-FLD-PF-CAPABILITY" label={tx("aiapi.pf-capability")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-PF-RIGHTS" label={tx("aiapi.pf-rights")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-PF-DATA" label={tx("aiapi.pf-data")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-PF-REFERENCE" label={tx("aiapi.pf-reference")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-PF-BUDGET" label={tx("aiapi.pf-budget")} value={dash} />
                </div>
              </div>
            </div>
            <div className={styles.card}>
              <h3>{tx("aiapi.flow-title")}</h3>
              <div className={styles.flow}>
                <div className={styles.flowCard}>
                  <h4>{tx("aiapi.flow-instruction")}</h4>
                  <p>{tx("aiapi.flow-instruction-hint")}</p>
                </div>
                <div className={styles.flowCard}>
                  <h4>{tx("aiapi.flow-compile")}</h4>
                  <p>{tx("aiapi.flow-compile-hint")}</p>
                </div>
                <div className={styles.flowCard}>
                  <h4>{tx("aiapi.flow-sandbox")}</h4>
                  <p>{tx("aiapi.flow-sandbox-hint")}</p>
                </div>
                <div className={styles.flowCard}>
                  <h4>{tx("aiapi.flow-decision")}</h4>
                  <p>{tx("aiapi.flow-decision-hint")}</p>
                </div>
              </div>
              <div className={styles.actions}>
                <Btn uid="CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-EXECUTE-ROUTE" label={tx("aiapi.btn-execute-route")} onAct={openModal} disabled={disabled} primary />
                <Btn uid="AIAPI-01-BTN-RUN-SANDBOX-TEST" label={tx("aiapi.btn-sandbox")} onAct={openModal} disabled={disabled} />
                <Btn uid="AIAPI-01-BTN-RUN-PROVIDER-QUEUE-PROBE" label={tx("aiapi.btn-queue-probe")} onAct={act} disabled={disabled} />
                <Btn uid="CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-VIEW-ROUTE-DECISION" label={tx("aiapi.btn-view-decision")} onAct={openDrawer} disabled={disabled} />
              </div>
            </div>
          </section>
        ) : null}

        {view === "operations" ? (
          <section className={styles.workspace} data-section-uid="AIAPI-01-SEC-08" data-component-uid="AIAPI-01-CMP-OPERATIONS">
            <h2>{tx("aiapi.ops-title")}</h2>
            <p className={styles.note}>{tx("aiapi.ops-hint")}</p>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("aiapi.job-title")}</h3>
                <div className={styles.kvList}>
                  <Kv uid="AIAPI-01-FLD-JOB-ID" label={tx("aiapi.field-job-id")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-JOB-STATUS" label={tx("aiapi.field-job-status")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-ATTEMPT-ID" label={tx("aiapi.field-attempt-id")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-CALLBACK" label={tx("aiapi.field-callback")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-ARTIFACT" label={tx("aiapi.field-artifact")} value={dash} />
                </div>
              </div>
              <div className={styles.card}>
                <h3>{tx("aiapi.budget-title")}</h3>
                <div className={styles.kvList}>
                  <Kv uid="AIAPI-01-FLD-OV-COST" label={tx("aiapi.ov-cost")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-OPS-COST" label={tx("aiapi.ops-cost")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-OPS-INCIDENT" label={tx("aiapi.ops-incident")} value={dash} />
                  <Kv uid="AIAPI-01-FLD-OPS-QUEUE" label={tx("aiapi.ops-queue")} value={dash} />
                </div>
              </div>
            </div>
          </section>
        ) : null}

        <ProfessionalRail t={tx} dash={dash} disabled={disabled} view={view} onDrawer={openDrawer} onModal={openModal} />
      </div>

      {drawerOpen ? (
        <section className={styles.drawer} data-section-uid="AIAPI-01-SEC-09" data-component-uid="AIAPI-01-CMP-DRAWER">
          <h3>{tx("aiapi.drawer-title")}</h3>
          <p className={styles.note}>{tx("aiapi.drawer-hint")}</p>
          <div className={styles.kvList}>
            <Kv uid="AIAPI-01-PRO-DESC-IDENTITY" label={tx("aiapi.pro-identity")} value={dash} />
            <Kv uid="AIAPI-01-PRO-DESC-ENDPOINT" label={tx("aiapi.pro-endpoint")} value={dash} />
            <Kv uid="AIAPI-01-PRO-DESC-AUTH" label={tx("aiapi.pro-auth")} value={dash} />
            <Kv uid="AIAPI-01-PRO-DESC-LAST-TEST" label={tx("aiapi.pro-last-test")} value={dash} />
          </div>
          <button type="button" className={styles.btn} onClick={() => setDrawerOpen(false)}>
            {tx("global.common.close")}
          </button>
        </section>
      ) : null}

      {modalUid ? (
        <section className={styles.modal} data-section-uid="AIAPI-01-SEC-10" data-component-uid="AIAPI-01-CMP-MODAL" data-control-uid={modalUid}>
          <h3>{tx("aiapi.modal-title")}</h3>
          <p className={styles.note}>{tx("aiapi.modal-hint")}</p>
          <button type="button" className={styles.btn} onClick={() => setModalUid(null)}>
            {tx("global.common.close")}
          </button>
        </section>
      ) : null}
    </div>
  );
}

function ProfessionalRail({
  t,
  dash,
  disabled,
  view,
  onDrawer,
  onModal,
}: {
  t: (key: TranslationKey) => string;
  dash: string;
  disabled: boolean;
  view: AiapiView;
  onDrawer: (uid: string) => void;
  onModal: (uid: string) => void;
}) {
  if (view === "overview" || view === "provider_api") {
    return (
      <aside className={styles.rail} data-section-uid="AIAPI-01-SEC-06" data-component-uid="AIAPI-01-PANEL-API-PROFESSIONAL-DESCRIPTION">
        <h2>{t("aiapi.panel-title")}</h2>
        <p className={styles.note}>{t("aiapi.panel-hint")}</p>
        <div className={styles.kvList}>
          {AIAPI_PRO_DESC_FIELDS.map((field) => (
            <Kv key={field.uid} uid={field.uid} label={t(field.labelKey)} value={dash} />
          ))}
        </div>
        <div className={styles.actions}>
          <button type="button" className={`${styles.btn} ${styles.btnOk}`} disabled>
            {t("aiapi.badge-no-secret")}
          </button>
          <button type="button" className={styles.btn} disabled>
            {t("aiapi.badge-missing")}
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className={styles.rail} data-section-uid="AIAPI-01-SEC-08" data-component-uid="AIAPI-01-CMP-OPS-RAIL">
      <h2>{t("aiapi.ops-rail-title")}</h2>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-HEALTH">
        <span>{t("aiapi.ops-health")}</span>
        <strong>{dash}</strong>
      </div>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-CREDENTIAL">
        <span>{t("aiapi.ops-credential")}</span>
        <strong>{dash}</strong>
      </div>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-QUEUE">
        <span>{t("aiapi.ops-queue")}</span>
        <strong>{dash}</strong>
      </div>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-COST">
        <span>{t("aiapi.ops-cost")}</span>
        <strong>{dash}</strong>
      </div>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-INCIDENT">
        <span>{t("aiapi.ops-incident")}</span>
        <strong>{dash}</strong>
      </div>
      <div className={styles.railCard} data-control-uid="AIAPI-01-FLD-OPS-QUARANTINE">
        <span>{t("aiapi.ops-quarantine")}</span>
        <strong>{dash}</strong>
      </div>
      <p className={styles.note}>{t("aiapi.high-risk-hint")}</p>
      <div className={styles.actions}>
        <Btn uid="CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-VIEW-QUARANTINE" label={t("aiapi.btn-view-quarantine")} onAct={onDrawer} disabled={disabled} />
        <Btn uid="CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-RESTORE-PROVIDER" label={t("aiapi.btn-restore")} onAct={onModal} disabled={disabled} danger />
        <Btn uid="CTRL-ADMIN-AIAPI-09-ACT-02-ACT-KILL-SWITCH" label={t("aiapi.btn-kill-switch")} onAct={onModal} disabled={disabled} danger />
      </div>
    </aside>
  );
}
