"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { DevClientError, fetchDevReadModel, postDevAction, type DevFieldValue } from "@/lib/client";
import { displayDevValue } from "./devFormat";
import { DEV_CONTROL_ACTIONS, DEV_STAGES, DEV_VISIBLE_CONTROLS, type DevStage } from "./devControls";
import styles from "./DevVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";
const EMPTY_ROWS = 3;

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

function EmptyRows({
  columns,
  dash,
  rowClass,
  lastCell,
}: {
  columns: number;
  dash: string;
  rowClass: string;
  lastCell?: string;
}) {
  return (
    <>
      {Array.from({ length: EMPTY_ROWS }, (_, index) => (
        <div className={`${styles.trow} ${rowClass}`} key={`empty-${index}`}>
          {Array.from({ length: columns }, (__, col) => (
            <span key={`c-${col}`} className={col === columns - 1 && lastCell ? styles.rowAct : undefined}>
              {col === columns - 1 && lastCell ? lastCell : dash}
            </span>
          ))}
        </div>
      ))}
    </>
  );
}

export function DevVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [, setFields] = useState<DevFieldValue[]>([]);
  const [stage, setStage] = useState<DevStage>(1);
  const [query, setQuery] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchDevReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : DEV_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof DevClientError ? cause.code : "DEV_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(DEV_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = DEV_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postDevAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayDevValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(DEV_VISIBLE_CONTROLS), []);
  const campaignView = stage === 4 || stage === 5;

  const selectStage = (next: DevStage, uid: string) => {
    setStage(next);
    void act(uid);
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:DEV-01"
      data-page-state={pageState}
      data-ui-stage={stage}
      data-component-count="15"
      data-control-count={visibleUids.size}
      aria-label={tx("dev.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("dev.error")}
        </div>
      ) : null}

      <header className={styles.heading} data-component-uid="DEV-01-CMP-CONTEXT" data-section-uid="DEV-01-SEC-01">
        <h1 className={styles.headingTitle}>{tx(campaignView ? "dev.campaign-title" : "dev.title")}</h1>
        <p className={styles.headingMeta}>{tx(campaignView ? "dev.campaign-meta" : "dev.meta")}</p>
      </header>

      <nav className={styles.stages} data-section-uid="DEV-01-SEC-02" data-component-uid="DEV-01-CMP-STAGE-NAV">
        {DEV_STAGES.map((item, index) => {
          const n = (index + 1) as DevStage;
          return (
            <button
              key={item.uid}
              type="button"
              className={`${styles.stageBtn} ${stage === n ? styles.stageActive : ""}`}
              data-control-uid={item.uid}
              disabled={disabled}
              onClick={() => selectStage(n, item.uid)}
            >
              {item.n} {tx(item.labelKey)}
            </button>
          );
        })}
      </nav>

      {campaignView ? null : (
        <section className={styles.context} data-section-uid="DEV-01-SEC-01">
          <div className={styles.ctx}>
            <span>{tx("dev.ctx-stage")}</span>
            <strong className={styles.ctxOk}>{tx("dev.ctx-stage-discovery")}</strong>
          </div>
          <div className={styles.ctx}>
            <span>{tx("dev.ctx-scope")}</span>
            <strong>{tx("dev.ctx-scope-value")}</strong>
          </div>
          <div className={styles.ctx}>
            <span>{tx("dev.ctx-run")}</span>
            <strong>{dash}</strong>
          </div>
          <div className={styles.ctx}>
            <span>{tx("dev.ctx-policy")}</span>
            <strong className={styles.ctxOk}>{tx("dev.ctx-policy-value")}</strong>
          </div>
        </section>
      )}

      {stage === 1 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-03" data-component-uid="DEV-01-CMP-DISCOVERY">
            <div className={styles.profile}>
              <div>
                <h3>{tx("dev.profile-title")}</h3>
                <p>{tx("dev.profile-hint")}</p>
              </div>
              <div className={styles.profileActions}>
                <button type="button" className={styles.btn} disabled={disabled} onClick={() => setDrawerOpen(true)}>
                  {tx("dev.btn-topic")}
                </button>
                <button type="button" className={styles.btn} disabled={disabled} onClick={() => setDrawerOpen(true)}>
                  {tx("dev.btn-source")}
                </button>
              </div>
            </div>
            <div className={styles.fields}>
              <label className={styles.field}>
                <span>{tx("dev.field-product")}</span>
                <div className={styles.fieldBox}>{dash}</div>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-industry")}</span>
                <div className={styles.fieldBox}>{dash}</div>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-market")}</span>
                <div className={styles.fieldBox}>{dash}</div>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-keywords")}</span>
                <div className={styles.fieldBox}>{dash}</div>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-exclude")}</span>
                <div className={styles.fieldBox}>{dash}</div>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-mode")}</span>
                <div className={styles.fieldBox}>{tx("dev.field-mode-value")}</div>
              </label>
            </div>
            <div className={styles.actions}>
              <button type="button" className={styles.btn} disabled={disabled} onClick={() => setDrawerOpen(true)}>
                {tx("dev.btn-profile-save")}
              </button>
              <Btn uid="DEV-01-BTN-DISCOVERY-START" label={tx("dev.btn-start")} onAct={act} disabled={disabled} primary />
              <Btn uid="DEV-01-BTN-DISCOVERY-PAUSE" label={tx("dev.btn-pause")} onAct={act} disabled={disabled} />
              <Btn uid="DEV-01-BTN-DISCOVERY-RESUME" label={tx("dev.btn-resume")} onAct={act} disabled={disabled} />
              <Btn uid="DEV-01-BTN-DISCOVERY-STOP" label={tx("dev.btn-stop")} onAct={act} disabled={disabled} danger />
            </div>
            <div className={styles.card}>
              <h3>{tx("dev.signal-title")}</h3>
              <div className={styles.table}>
                <div className={`${styles.thead} ${styles.signalHead}`}>
                  <span>{tx("dev.col-company")}</span>
                  <span>{tx("dev.col-intent")}</span>
                  <span>{tx("dev.col-evidence")}</span>
                  <span>{tx("dev.col-freshness")}</span>
                  <span>{tx("dev.col-match")}</span>
                  <span>{tx("dev.col-opportunity")}</span>
                  <span>{tx("dev.col-action")}</span>
                </div>
                <EmptyRows columns={7} dash={dash} rowClass={styles.signalRow} lastCell={tx("dev.row-qualify")} />
              </div>
            </div>
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} />
        </div>
      ) : null}

      {stage === 2 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-04" data-component-uid="DEV-01-CMP-DIRECTORY">
            <h2>{tx("dev.directory-title")}</h2>
            <p className={styles.note}>{tx("dev.directory-hint")}</p>
            <div className={styles.toolbar}>
              <input
                className={styles.search}
                data-control-uid="DEV-01-BTN-DIRECTORY-SEARCH"
                placeholder={tx("dev.search-company")}
                value={query}
                disabled={disabled}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void act("DEV-01-BTN-DIRECTORY-SEARCH");
                }}
              />
              <Btn uid="DEV-01-BTN-DIRECTORY-SEARCH" label={tx("dev.btn-search")} onAct={act} disabled={disabled} />
            </div>
            <div className={styles.table}>
              <div className={`${styles.thead} ${styles.dirHead}`}>
                <span>{tx("dev.col-identity")}</span>
                <span>{tx("dev.col-contact")}</span>
                <span>{tx("dev.col-evidence")}</span>
                <span>{tx("dev.col-opportunity")}</span>
                <span>{tx("dev.col-suppression")}</span>
                <span>{tx("dev.col-action")}</span>
              </div>
              <EmptyRows columns={6} dash={dash} rowClass={styles.dirRow} lastCell={tx("dev.row-open")} />
            </div>
            <div className={styles.actions}>
              <Btn uid="DEV-01-BTN-MERGE-PREVIEW" label={tx("dev.btn-merge-preview")} onAct={act} disabled={disabled} />
              <Btn uid="DEV-01-BTN-MERGE" label={tx("dev.btn-merge")} onAct={act} disabled={disabled} primary />
              <Btn uid="DEV-01-BTN-EXPORT" label={tx("dev.btn-export")} onAct={act} disabled={disabled} />
            </div>
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} />
        </div>
      ) : null}

      {stage === 3 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-05" data-component-uid="DEV-01-CMP-MESSAGE">
            <h2>{tx("dev.message-title")}</h2>
            <p className={styles.note}>{tx("dev.message-hint")}</p>
            <div className={styles.card}>
              <h3>{tx("dev.audience-context")}</h3>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-company")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-opportunity")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-contact")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-version")}</span>
                  <strong>{dash}</strong>
                </div>
              </div>
            </div>
            <div className={styles.table}>
              <div className={`${styles.thead} ${styles.msgHead}`}>
                <span>{tx("dev.col-candidate")}</span>
                <span>{tx("dev.col-personalization")}</span>
                <span>{tx("dev.col-policy")}</span>
                <span>{tx("dev.col-review")}</span>
                <span>{tx("dev.col-version")}</span>
                <span>{tx("dev.col-action")}</span>
              </div>
              <EmptyRows columns={6} dash={dash} rowClass={styles.msgRow} lastCell={tx("dev.row-open")} />
            </div>
            <div className={styles.actions}>
              <Btn uid="DEV-01-BTN-CANDIDATE-CREATE" label={tx("dev.btn-candidate-create")} onAct={act} disabled={disabled} primary />
              <Btn uid="DEV-01-BTN-CANDIDATE-DECIDE" label={tx("dev.btn-candidate-decide")} onAct={act} disabled={disabled} />
              <Btn uid="DEV-01-BTN-CR-CREATE" label={tx("dev.btn-cr")} onAct={act} disabled={disabled} />
            </div>
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} />
        </div>
      ) : null}

      {campaignView ? (
        <div className={styles.split}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-06" data-component-uid="DEV-01-CMP-CAMPAIGN">
            <h2>{tx("dev.campaign-stage")}</h2>
            <div className={styles.card}>
              <h3>{tx("dev.audience-filter")}</h3>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span>{tx("dev.filter-company")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.filter-contact")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.filter-suppression")}</span>
                  <strong>{tx("dev.filter-suppression-value")}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.filter-message")}</span>
                  <strong>{tx("dev.filter-message-value")}</strong>
                </div>
              </div>
            </div>
            <div className={styles.card}>
              <h3>{tx("dev.recipient-title")}</h3>
              <div className={styles.table}>
                <div className={`${styles.thead} ${styles.rcpHead}`}>
                  <span>{tx("dev.col-company")}</span>
                  <span>{tx("dev.col-contact")}</span>
                  <span>{tx("dev.col-suppression")}</span>
                  <span>{tx("dev.col-policy")}</span>
                  <span>{tx("dev.col-message")}</span>
                  <span>{tx("dev.col-result")}</span>
                </div>
                <EmptyRows columns={6} dash={dash} rowClass={styles.rcpRow} />
              </div>
            </div>
            <div className={styles.actions}>
              <Btn uid="DEV-01-BTN-CAMPAIGN-SEARCH" label={tx("dev.btn-audience-search")} onAct={act} disabled={disabled} />
              <Btn uid="DEV-01-BTN-CAMPAIGN-CREATE" label={tx("dev.btn-campaign-create")} onAct={act} disabled={disabled} primary />
              <Btn uid="DEV-01-BTN-CAMPAIGN-APPROVE" label={tx("dev.btn-campaign-approve")} onAct={act} disabled={disabled} />
            </div>
            <div className={styles.card}>
              <h3>{tx("dev.approval-title")}</h3>
              <p className={styles.note}>{tx("dev.approval-hint")}</p>
            </div>
          </section>
          <aside className={styles.rail} data-section-uid="DEV-01-SEC-07" data-component-uid="DEV-01-CMP-DELIVERY">
            <h2>{tx("dev.delivery-stage")}</h2>
            <div className={styles.railCard}>
              <span>{tx("dev.delivery-campaign")}</span>
              <strong>{tx("dev.delivery-campaign-value")}</strong>
            </div>
            <div className={styles.railCard}>
              <span>{tx("dev.delivery-policy")}</span>
              <strong>{tx("dev.delivery-policy-value")}</strong>
            </div>
            <div className={styles.railCard}>
              <span>{tx("dev.delivery-envelope")}</span>
              <strong>{tx("dev.delivery-envelope-value")}</strong>
            </div>
            <div className={styles.railCard}>
              <span>{tx("dev.col-suppression")}</span>
              <strong>{tx("dev.delivery-suppression-value")}</strong>
            </div>
            <div className={styles.railCard}>
              <span>{tx("dev.delivery-idempotency")}</span>
              <strong>{tx("dev.required")}</strong>
            </div>
            <div className={styles.railCard}>
              <span>{tx("dev.delivery-audit")}</span>
              <strong>{tx("dev.required")}</strong>
            </div>
            <div className={styles.actions}>
              <Btn uid="DEV-01-BTN-EMAIL-DISPATCH" label={tx("dev.btn-dispatch")} onAct={act} disabled={disabled} primary />
              <Btn uid="DEV-01-BTN-REFRESH" label={tx("dev.btn-refresh")} onAct={act} disabled={disabled} />
              <Btn uid="DEV-01-BTN-KILL-SWITCH" label={tx("dev.btn-kill")} onAct={act} disabled={disabled} danger />
            </div>
            <div className={styles.killNote}>{tx("dev.kill-note")}</div>
          </aside>
        </div>
      ) : null}

      {campaignView ? (
        <div className={styles.chain} data-section-uid="DEV-01-SEC-09">
          {tx("dev.chain")}
        </div>
      ) : (
        <div className={styles.dock} data-section-uid="DEV-01-SEC-02">
          <strong>{tx("dev.dock-title")}</strong>
          <p>{tx("dev.dock-hint")}</p>
        </div>
      )}

      {drawerOpen ? (
        <section className={styles.card} data-section-uid="DEV-01-SEC-09" data-component-uid="DEV-01-CMP-DRAWER">
          <h3>{tx("dev.drawer-title")}</h3>
          <p className={styles.note}>{tx("dev.drawer-hint")}</p>
          <div className={styles.metaGrid}>
            <div className={styles.metaItem}>
              <span>{tx("dev.col-evidence")}</span>
              <strong>{dash}</strong>
            </div>
            <div className={styles.metaItem}>
              <span>{tx("dev.col-version")}</span>
              <strong>{dash}</strong>
            </div>
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
  onDrawer,
}: {
  t: (key: TranslationKey) => string;
  dash: string;
  disabled: boolean;
  onDrawer: () => void;
}) {
  return (
    <aside className={styles.rail} data-section-uid="DEV-01-SEC-08" data-component-uid="DEV-01-CMP-GOVERNANCE">
      <h2>{t("dev.rail-title")}</h2>
      <div className={styles.railCard}>
        <span>{t("dev.rail-permission")}</span>
        <strong>{t("dev.rail-permission-value")}</strong>
      </div>
      <div className={styles.railCard}>
        <span>{t("dev.rail-source")}</span>
        <strong>{t("dev.rail-source-value")}</strong>
      </div>
      <div className={styles.railCard}>
        <span>{t("dev.rail-connector")}</span>
        <strong>{dash}</strong>
      </div>
      <div className={styles.railCard}>
        <span>{t("dev.rail-suppression")}</span>
        <strong>{t("dev.rail-suppression-value")}</strong>
      </div>
      <div className={styles.railCard}>
        <span>{t("dev.rail-blockers")}</span>
        <strong>{dash}</strong>
      </div>
      <div className={styles.railCard}>
        <span>{t("dev.rail-owner")}</span>
        <strong>{t("dev.rail-owner-value")}</strong>
      </div>
      <button type="button" className={styles.drawerBtn} disabled={disabled} onClick={onDrawer}>
        {t("dev.rail-drawer")}
      </button>
    </aside>
  );
}
