"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { SocClientError, fetchSocReadModel, postSocAction, type SocFieldValue } from "@/lib/client";
import { displaySocValue } from "./socFormat";
import { SOC_CONTROL_ACTIONS, SOC_STAGES, SOC_VISIBLE_CONTROLS, type SocStage } from "./socControls";
import styles from "./SocVisual.module.css";

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
}: {
  columns: number;
  dash: string;
  rowClass: string;
}) {
  return (
    <>
      {Array.from({ length: EMPTY_ROWS }, (_, index) => (
        <div className={`${styles.trow} ${rowClass}`} key={`empty-${index}`}>
          {Array.from({ length: columns }, (__, col) => (
            <span key={`c-${col}`}>{dash}</span>
          ))}
        </div>
      ))}
    </>
  );
}

export function SocVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [, setFields] = useState<SocFieldValue[]>([]);
  const [stage, setStage] = useState<SocStage>(2);
  const [query, setQuery] = useState("");
  const [recordQuery, setRecordQuery] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchSocReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : SOC_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof SocClientError ? cause.code : "SOC_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(SOC_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = SOC_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postSocAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displaySocValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(SOC_VISIBLE_CONTROLS), []);
  const chainView = stage === 4 || stage === 5;

  const selectStage = (next: SocStage, uid: string) => {
    setStage(next);
    void act(uid);
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:SOC-01"
      data-page-state={pageState}
      data-ui-stage={stage}
      data-component-count="9"
      data-control-count={visibleUids.size}
      aria-label={tx("soc.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("soc.error")}
        </div>
      ) : null}

      <header className={styles.heading} data-component-uid="SOC-01-CMP-CONTEXT" data-section-uid="SOC-01-SEC-01">
        <h1 className={styles.headingTitle}>{tx("soc.title")}</h1>
        <p className={styles.headingMeta}>{tx("soc.meta")}</p>
      </header>

      <nav className={styles.stages} data-section-uid="SOC-01-SEC-02" data-component-uid="SOC-01-CMP-STAGES">
        {SOC_STAGES.map((item, index) => {
          const n = (index + 1) as SocStage;
          return (
            <button
              key={item.uid}
              type="button"
              className={`${styles.stageBtn} ${stage === n ? styles.stageActive : ""}`}
              data-control-uid={item.uid}
              disabled={disabled}
              onClick={() => selectStage(n, item.uid)}
            >
              {tx(item.labelKey)}
            </button>
          );
        })}
      </nav>

      {stage === 1 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="SOC-01-SEC-03" data-component-uid="SOC-01-CMP-PLATFORM">
            <h2>{tx("soc.platform-title")}</h2>
            <p className={styles.note}>{tx("soc.platform-hint")}</p>
            <div className={styles.table}>
              <div className={`${styles.thead} ${styles.platHead}`}>
                <span>{tx("soc.col-platform")}</span>
                <span>{tx("soc.col-capability")}</span>
                <span>{tx("soc.col-policy")}</span>
                <span>{tx("soc.col-health")}</span>
                <span>{tx("soc.col-enable")}</span>
              </div>
              <EmptyRows columns={5} dash={dash} rowClass={styles.platRow} />
            </div>
            <div className={styles.actions}>
              <Btn uid="SOC-01-BTN-PLATFORM-CONFIG" label={tx("soc.btn-platform-config")} onAct={act} disabled={disabled} primary />
              <Btn uid="SOC-01-BTN-KILL" label={tx("soc.btn-kill")} onAct={act} disabled={disabled} danger />
            </div>
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} onAct={act} variant="platform" />
        </div>
      ) : null}

      {stage === 2 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="SOC-01-SEC-04" data-component-uid="SOC-01-CMP-ACCOUNT-TARGET">
            <h2>{tx("soc.target-title")}</h2>
            <p className={styles.note}>{tx("soc.target-hint")}</p>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("soc.profile-title")}</h3>
                <label className={styles.field}>
                  <span>{tx("soc.field-topic")}</span>
                  <div className={styles.fieldBox}>{dash}</div>
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-platform")}</span>
                  <div className={styles.fieldBox}>{dash}</div>
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-target-types")}</span>
                  <div className={styles.fieldBox}>{dash}</div>
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-keywords")}</span>
                  <div className={styles.fieldBox}>{dash}</div>
                </label>
                <div className={styles.actions}>
                  <Btn uid="SOC-01-BTN-TARGET-DISCOVERY" label={tx("soc.btn-discovery")} onAct={act} disabled={disabled} primary />
                  <Btn uid="SOC-01-BTN-ACCOUNT-BIND" label={tx("soc.btn-bind")} onAct={act} disabled={disabled} />
                </div>
              </div>
              <div className={styles.card}>
                <h3>{tx("soc.directory-title")}</h3>
                <div className={styles.toolbar}>
                  <input
                    className={styles.search}
                    data-control-uid="SOC-01-INP-TARGET-SEARCH"
                    placeholder={tx("soc.search-target")}
                    value={query}
                    disabled={disabled}
                    onChange={(event) => setQuery(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") void act("SOC-01-INP-TARGET-SEARCH");
                    }}
                  />
                </div>
                <div className={styles.table}>
                  <div className={`${styles.thead} ${styles.targetHead}`}>
                    <span>{tx("soc.col-target")}</span>
                    <span>{tx("soc.col-capability")}</span>
                    <span>{tx("soc.col-status")}</span>
                    <span>{tx("soc.col-signal")}</span>
                  </div>
                  <EmptyRows columns={4} dash={dash} rowClass={styles.targetRow} />
                </div>
                <div className={styles.actions}>
                  <Btn uid="SOC-01-INP-TARGET-SEARCH" label={tx("soc.btn-search")} onAct={act} disabled={disabled} />
                  <Btn uid="SOC-01-BTN-TARGET-JOIN" label={tx("soc.btn-join")} onAct={act} disabled={disabled} />
                  <Btn uid="SOC-01-BTN-MANUAL-COMPLETE" label={tx("soc.btn-manual")} onAct={act} disabled={disabled} />
                  <Btn uid="SOC-01-BTN-DETAIL" label={tx("soc.btn-detail")} onAct={(uid) => { setDrawerOpen(true); void act(uid); }} disabled={disabled} />
                </div>
              </div>
            </div>
            <div className={styles.card}>
              <h3>{tx("soc.lineage-title")}</h3>
              <div className={styles.lineage}>
                <div className={styles.lineageItem}>
                  <span>{tx("soc.lineage-account")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.lineageItem}>
                  <span>{tx("soc.lineage-target")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.lineageItem}>
                  <span>{tx("soc.lineage-version")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.lineageItem}>
                  <span>{tx("soc.lineage-correlation")}</span>
                  <strong>{dash}</strong>
                </div>
              </div>
              <div className={styles.actions}>
                <Btn uid="SOC-01-BTN-CREDENTIAL-REVEAL" label={tx("soc.btn-reveal")} onAct={act} disabled={disabled} />
                <Btn uid="SOC-01-BTN-ACCOUNT-UNBIND" label={tx("soc.btn-unbind")} onAct={act} disabled={disabled} danger />
              </div>
            </div>
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} onAct={act} variant="account" />
        </div>
      ) : null}

      {stage === 3 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="SOC-01-SEC-05" data-component-uid="SOC-01-CMP-CONTENT">
            <h2>{tx("soc.content-title")}</h2>
            <p className={styles.note}>{tx("soc.content-hint")}</p>
            <div className={styles.card}>
              <h3>{tx("soc.package-title")}</h3>
              <div className={styles.kv}>
                <span>{tx("soc.field-release")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.kv}>
                <span>{tx("soc.field-variants")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.kv}>
                <span>{tx("soc.field-policy-check")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.kv}>
                <span>{tx("soc.field-candidate")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.kv}>
                <span>{tx("soc.field-version")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.actions}>
                <Btn uid="SOC-01-BTN-CONTENT-SAVE" label={tx("soc.btn-draft")} onAct={act} disabled={disabled} />
                <Btn uid="SOC-01-BTN-CANDIDATE-DECIDE" label={tx("soc.btn-candidate")} onAct={act} disabled={disabled} primary />
              </div>
            </div>
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} onAct={act} variant="content" />
        </div>
      ) : null}

      {chainView ? (
        <div className={styles.cols}>
          <section
            className={styles.workspace}
            data-section-uid={stage === 4 ? "SOC-01-SEC-06" : "SOC-01-SEC-07"}
            data-component-uid={stage === 4 ? "SOC-01-CMP-PUBLISH" : "SOC-01-CMP-RECORDS"}
          >
            <h2>{tx("soc.chain-title")}</h2>
            <p className={styles.note}>{tx("soc.chain-hint")}</p>
            <div className={styles.duo}>
              <div className={styles.card}>
                <h3>{tx("soc.package-title")}</h3>
                <div className={styles.kv}>
                  <span>{tx("soc.field-release")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-variants")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-policy-check")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-candidate")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-version")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.actions}>
                  <Btn uid="SOC-01-BTN-CONTENT-SAVE" label={tx("soc.btn-draft")} onAct={act} disabled={disabled} />
                  <Btn uid="SOC-01-BTN-CANDIDATE-DECIDE" label={tx("soc.btn-candidate")} onAct={act} disabled={disabled} primary />
                </div>
              </div>
              <div className={styles.card}>
                <h3>{tx("soc.plan-title")}</h3>
                <div className={styles.kv}>
                  <span>{tx("soc.field-target")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-account")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-content")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-interval")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-schedule")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.actions}>
                  <Btn uid="SOC-01-BTN-POLICY-CONFIG" label={tx("soc.btn-policy")} onAct={act} disabled={disabled} />
                  <Btn uid="SOC-01-BTN-PUBLISH" label={tx("soc.btn-publish")} onAct={act} disabled={disabled} primary />
                  <Btn uid="SOC-01-BTN-REFRESH" label={tx("soc.btn-refresh")} onAct={act} disabled={disabled} />
                </div>
              </div>
            </div>
            <div className={styles.card}>
              <h3>{tx("soc.records-title")}</h3>
              <div className={styles.toolbar}>
                <input
                  className={styles.search}
                  data-control-uid="SOC-01-INP-RECORD-SEARCH"
                  placeholder={tx("soc.search-record")}
                  value={recordQuery}
                  disabled={disabled}
                  onChange={(event) => setRecordQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void act("SOC-01-INP-RECORD-SEARCH");
                  }}
                />
                <Btn uid="SOC-01-INP-RECORD-SEARCH" label={tx("soc.btn-search")} onAct={act} disabled={disabled} />
              </div>
              <div className={styles.recordsGrid}>
                <div className={styles.recordsItem}>
                  <span>{tx("soc.col-request")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.recordsItem}>
                  <span>{tx("soc.col-external")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.recordsItem}>
                  <span>{tx("soc.col-metrics")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.recordsItem}>
                  <span>{tx("soc.col-interaction")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.recordsItem}>
                  <span>{tx("soc.col-callback")}</span>
                  <strong>{dash}</strong>
                </div>
              </div>
              <p className={styles.note}>{tx("soc.withdraw-note")}</p>
            </div>
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} onAct={act} variant="publish" />
        </div>
      ) : null}

      {drawerOpen ? (
        <section className={styles.card} data-section-uid="SOC-01-SEC-08" data-component-uid="SOC-01-CMP-GOVERNANCE">
          <h3>{tx("soc.drawer-title")}</h3>
          <p className={styles.note}>{tx("soc.drawer-hint")}</p>
          <div className={styles.lineage}>
            <div className={styles.lineageItem}>
              <span>{tx("soc.col-callback")}</span>
              <strong>{dash}</strong>
            </div>
            <div className={styles.lineageItem}>
              <span>{tx("soc.field-version")}</span>
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
  onAct,
  variant,
}: {
  t: (key: TranslationKey) => string;
  dash: string;
  disabled: boolean;
  onDrawer: () => void;
  onAct: (uid: string) => void;
  variant: "platform" | "account" | "content" | "publish";
}) {
  const openDetail = () => {
    onDrawer();
    void onAct("SOC-01-BTN-DETAIL");
  };
  return (
    <aside className={styles.rail} data-section-uid="SOC-01-SEC-08" data-component-uid="SOC-01-CMP-GOVERNANCE">
      <h2>{t("soc.rail-title")}</h2>
      {variant === "publish" ? (
        <>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotOk}`} />
            <span>{t("soc.rail-rights")}</span>
            <strong>{t("soc.rail-rights-value")}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotOk}`} />
            <span>{t("soc.rail-cooldown")}</span>
            <strong>{t("soc.rail-cooldown-value")}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotWarn}`} />
            <span>{t("soc.rail-approval")}</span>
            <strong>{t("soc.rail-approval-value")}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotInfo}`} />
            <span>{t("soc.rail-truth")}</span>
            <strong>{t("soc.rail-truth-value")}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotDanger}`} />
            <span>{t("soc.rail-kill")}</span>
            <strong>{t("soc.rail-kill-value")}</strong>
          </div>
        </>
      ) : (
        <>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotOk}`} />
            <span>{t("soc.rail-health")}</span>
            <strong>{dash}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotInfo}`} />
            <span>{t("soc.rail-capability")}</span>
            <strong>{t("soc.rail-capability-value")}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotOk}`} />
            <span>{t("soc.rail-policy")}</span>
            <strong>{t("soc.rail-policy-value")}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotWarn}`} />
            <span>{t("soc.rail-manual")}</span>
            <strong>{t("soc.rail-manual-value")}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotDanger}`} />
            <span>{t("soc.rail-blocker")}</span>
            <strong>{dash}</strong>
          </div>
        </>
      )}
      <div className={styles.railActions}>
        <button type="button" className={styles.btn} data-control-uid="SOC-01-BTN-DETAIL" disabled={disabled} onClick={openDetail}>
          {t("soc.btn-evidence")}
        </button>
        <button type="button" className={styles.btn} disabled={disabled} onClick={openDetail}>
          {t("soc.btn-audit")}
        </button>
      </div>
    </aside>
  );
}
