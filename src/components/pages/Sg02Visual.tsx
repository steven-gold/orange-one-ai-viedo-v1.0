"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { Sg02ClientError, fetchSg02ReadModel, postSg02Action, type Sg02FieldValue } from "@/lib/client";
import { displaySg02Value } from "./sg02Format";
import {
  SG02_CONTROL_ACTIONS,
  SG02_LIFECYCLE_ROWS,
  SG02_TABLE_COLUMNS,
  SG02_VISIBLE_CONTROLS,
  type Sg02Drawer,
  type Sg02Surface,
} from "./sg02Controls";
import styles from "./Sg02Visual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
  warn = false,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  warn?: boolean;
}) {
  const className = [styles.btn, primary ? styles.btnPrimary : "", warn ? styles.btnWarn : ""].filter(Boolean).join(" ");
  return (
    <button type="button" className={className} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      {label}
    </button>
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

function stateClass(state: (typeof SG02_LIFECYCLE_ROWS)[number]): string {
  if (state === "DRAFT") return styles.stateDraft;
  if (state === "REVIEW") return styles.stateReview;
  if (state === "ACTIVE") return styles.stateActive;
  return styles.stateSuperseded;
}

export function Sg02Visual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [, setFields] = useState<Sg02FieldValue[]>([]);
  const [surface, setSurface] = useState<Sg02Surface>("main");
  const [drawer, setDrawer] = useState<Sg02Drawer | null>(null);
  const [modalUid, setModalUid] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchSg02ReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : SG02_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof Sg02ClientError ? cause.code : "SG02_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(SG02_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = SG02_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postSg02Action(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displaySg02Value(null, loading);
  const visibleUids = useMemo(() => new Set<string>(SG02_VISIBLE_CONTROLS), []);

  const openDrawer = (next: Sg02Drawer, uid: string) => {
    setDrawer(next);
    void act(uid);
  };

  const openModal = (uid: string) => {
    setModalUid(uid);
    void act(uid);
  };

  const openApproval = (uid: string) => {
    setSurface("approval");
    setDrawer("approval");
    void act(uid);
  };

  const drawerTitle = (key: Sg02Drawer): TranslationKey => {
    if (key === "criteria_table") return "sg02.drawer-criteria";
    if (key === "dimension_library") return "sg02.drawer-dimension";
    if (key === "thresholds") return "sg02.drawer-thresholds";
    if (key === "department_mapping") return "sg02.drawer-department";
    if (key === "required_checks") return "sg02.drawer-checks";
    if (key === "gate_policy") return "sg02.drawer-gate";
    if (key === "approval") return "sg02.drawer-approval";
    if (key === "impact") return "sg02.drawer-impact";
    return "sg02.drawer-nav";
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:SG-02"
      data-page-state={pageState}
      data-ui-view={surface}
      data-component-count="9"
      data-control-count={visibleUids.size}
      aria-label={tx("sg02.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("sg02.error")}
        </div>
      ) : null}

      {surface === "main" ? (
        <>
          <header className={styles.heading} data-component-uid="SG-02-CMP-CONTEXT" data-section-uid="SEC-ADMIN-SG-02-CRITERIA-TABLE">
            <h1 className={styles.headingTitle}>{tx("sg02.title")}</h1>
            <p className={styles.headingMeta}>{tx("sg02.meta")}</p>
          </header>

          <div className={styles.statusBar} data-section-uid="SEC-ADMIN-SG-02-CRITERIA-TABLE" data-component-uid="SG-02-CMP-STATUS">
            <div className={styles.statusItem}>
              <span>{tx("sg02.status-current")}</span>
              <strong className={styles.chip}>{dash}</strong>
            </div>
            <div className={styles.statusItem}>
              <span>{tx("sg02.status-lifecycle")}</span>
              <strong className={styles.chip}>{dash}</strong>
            </div>
            <button
              type="button"
              className={styles.statusItem}
              data-control-uid="CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN"
              disabled={disabled}
              onClick={() => openDrawer("department_mapping", "CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN")}
            >
              <span>{tx("sg02.status-department")}</span>
              <strong className={styles.chip}>{dash}</strong>
            </button>
            <button
              type="button"
              className={styles.statusItem}
              data-control-uid="CTRL-ADMIN-SG-02-IMPACT-OPEN"
              disabled={disabled}
              onClick={() => openDrawer("impact", "CTRL-ADMIN-SG-02-IMPACT-OPEN")}
            >
              <span>{tx("sg02.status-impact")}</span>
              <strong className={styles.chip}>{dash}</strong>
            </button>
            <Btn
              uid="CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN"
              label={tx("sg02.btn-create")}
              onAct={(uid) => openDrawer("nav", uid)}
              disabled={disabled}
              primary
            />
          </div>

          <div className={styles.cols}>
            <section className={styles.workspace} data-section-uid="SEC-ADMIN-SG-02-CRITERIA-TABLE" data-component-uid="SG-02-CMP-TABLE">
              <h2>{tx("sg02.table-title")}</h2>
              <p className={styles.note}>{tx("sg02.table-hint")}</p>
              <div className={styles.tableWrap}>
                <table className={styles.table} data-control-uid="CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN">
                  <thead>
                    <tr>
                    {SG02_TABLE_COLUMNS.map((col) =>
                      col === "sg02.col-threshold" ? (
                        <th key={col}>
                          <button
                            type="button"
                            className={styles.headerBtn}
                            data-control-uid="CTRL-ADMIN-SG-02-GATE-POLICY-OPEN"
                            disabled={disabled}
                            onClick={() => openDrawer("gate_policy", "CTRL-ADMIN-SG-02-GATE-POLICY-OPEN")}
                          >
                            {tx(col)}
                          </button>
                        </th>
                      ) : (
                        <th key={col}>{tx(col)}</th>
                      ),
                    )}
                    </tr>
                  </thead>
                  <tbody>
                    {SG02_LIFECYCLE_ROWS.map((state) => (
                      <tr key={state}>
                        <td>{dash}</td>
                        <td className={stateClass(state)}>{state}</td>
                        <td>{dash}</td>
                        <td>{dash}</td>
                        <td>{dash}</td>
                        <td>{dash}</td>
                        <td>{dash}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className={styles.cardGrid}>
                <div className={styles.card} data-section-uid="SEC-ADMIN-SG-02-DIMENSION-LIBRARY">
                  <h3>{tx("sg02.card-dimension")}</h3>
                  <p className={styles.note}>{tx("sg02.card-dimension-hint")}</p>
                  <Btn uid="CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN" label={tx("sg02.btn-drawer")} onAct={(uid) => openDrawer("dimension_library", uid)} disabled={disabled} />
                </div>
                <div className={styles.card} data-section-uid="SEC-ADMIN-SG-02-THRESHOLDS">
                  <h3>{tx("sg02.card-thresholds")}</h3>
                  <p className={styles.note}>{tx("sg02.card-thresholds-hint")}</p>
                  <Btn uid="CTRL-ADMIN-SG-02-THRESHOLDS-OPEN" label={tx("sg02.btn-drawer")} onAct={(uid) => openDrawer("thresholds", uid)} disabled={disabled} />
                </div>
                <div className={styles.card} data-section-uid="SEC-ADMIN-SG-02-REQUIRED-CHECKS">
                  <h3>{tx("sg02.card-checks")}</h3>
                  <p className={styles.note}>{tx("sg02.card-checks-hint")}</p>
                  <Btn uid="CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN" label={tx("sg02.btn-drawer")} onAct={(uid) => openDrawer("required_checks", uid)} disabled={disabled} />
                </div>
              </div>
            </section>

            <aside className={styles.rail} data-section-uid="SEC-ADMIN-SG-02-ACTION-DOCK" data-component-uid="SG-02-CMP-RAIL">
              <h2>{tx("sg02.rail-title")}</h2>
              <div className={styles.railCard}>
                <span>{tx("sg02.rail-integrity")}</span>
                <strong>{dash}</strong>
              </div>
              <button
                type="button"
                className={styles.railCard}
                data-control-uid="CTRL-ADMIN-SG-02-APPROVAL-OPEN"
                disabled={disabled}
                onClick={() => openDrawer("approval", "CTRL-ADMIN-SG-02-APPROVAL-OPEN")}
              >
                <span>{tx("sg02.rail-approval")}</span>
                <strong>{dash}</strong>
              </button>
              <div className={styles.railCard}>
                <span>{tx("sg02.rail-impact")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.railCard}>
                <span>{tx("sg02.rail-revalidation")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.railCard}>
                <span>{tx("sg02.rail-history")}</span>
                <strong className={styles.required}>{tx("sg02.rail-history-value")}</strong>
              </div>
              <h3>{tx("sg02.dock-title")}</h3>
              <div className={styles.actions}>
                <Btn uid="CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE" label={tx("sg02.btn-configure")} onAct={openModal} disabled={disabled} primary />
                <Btn uid="CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE" label={tx("sg02.btn-approve")} onAct={openApproval} disabled={disabled} />
              </div>
            </aside>
          </div>
        </>
      ) : (
        <>
          <header className={styles.heading} data-component-uid="SG-02-CMP-APPROVAL-CONTEXT" data-section-uid="SEC-ADMIN-SG-02-APPROVAL">
            <h1 className={styles.headingTitle}>{tx("sg02.approval-title")}</h1>
            <p className={styles.headingMeta}>{tx("sg02.approval-meta")}</p>
          </header>

          <div className={styles.cols}>
            <section className={styles.workspace} data-section-uid="SEC-ADMIN-SG-02-APPROVAL" data-component-uid="SG-02-CMP-APPROVAL">
              <h2>{tx("sg02.selected-title")}</h2>
              <div className={styles.summary}>
                <div className={styles.summaryItem}>
                  <span>{tx("sg02.col-version")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.summaryItem}>
                  <span>{tx("sg02.col-state")}</span>
                  <strong className={styles.stateReview}>REVIEW</strong>
                </div>
                <div className={styles.summaryItem}>
                  <span>{tx("sg02.field-scope")}</span>
                  <strong>{dash}</strong>
                </div>
                <div className={styles.summaryItem}>
                  <span>{tx("sg02.field-base")}</span>
                  <strong>{dash}</strong>
                </div>
              </div>
              <h2>{tx("sg02.configure-title")}</h2>
              <div className={styles.kvList}>
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-resource-type")}</span>
                  <div className={styles.formField}>{tx("sg02.field-resource-type-value")}</div>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-resource-id")}</span>
                  <div className={styles.formField}>{dash}</div>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-patch")}</span>
                  <div className={styles.formField}>{dash}</div>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-reason")}</span>
                  <div className={styles.formField}>{dash}</div>
                </div>
              </div>
              <h2>{tx("sg02.impact-title")}</h2>
              <div className={styles.kvList}>
                <Kv uid="CTRL-ADMIN-SG-02-IMPACT-OPEN" label={tx("sg02.field-departments")} value={dash} />
                <Kv uid="CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN" label={tx("sg02.field-tasks")} value={dash} />
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-history")}</span>
                  <strong className={styles.required}>{tx("sg02.field-history-value")}</strong>
                </div>
              </div>
            </section>

            <aside className={styles.rail} data-section-uid="SEC-ADMIN-SG-02-APPROVAL" data-component-uid="SG-02-CMP-APPROVAL-RAIL">
              <h2>{tx("sg02.approval-drawer-title")}</h2>
              <p className={styles.note}>{tx("sg02.field-expected")}</p>
              <div className={styles.formField}>{dash}</div>
              <p className={styles.note}>{tx("sg02.field-rationale")}</p>
              <div className={`${styles.formField} ${styles.formArea}`}>{dash}</div>
              <h3>{tx("sg02.gate-title")}</h3>
              <div className={styles.gateList}>
                <button type="button" className={`${styles.btn} ${styles.btnWarn}`} disabled>
                  {tx("sg02.gate-review")}
                </button>
                <button type="button" className={`${styles.btn} ${styles.btnWarn}`} disabled>
                  {tx("sg02.gate-impact")}
                </button>
                <button type="button" className={`${styles.btn} ${styles.btnWarn}`} disabled>
                  {tx("sg02.gate-version")}
                </button>
                <button type="button" className={`${styles.btn} ${styles.btnWarn}`} disabled>
                  {tx("sg02.gate-audit")}
                </button>
              </div>
              <div className={styles.actions}>
                <button type="button" className={styles.btn} disabled={disabled} onClick={() => setSurface("main")}>
                  {tx("sg02.btn-back")}
                </button>
                <Btn uid="CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE" label={tx("sg02.btn-approve-version")} onAct={openModal} disabled={disabled} primary />
              </div>
              <p className={styles.note}>{tx("sg02.approval-hint")}</p>
            </aside>
          </div>
        </>
      )}

      {drawer ? (
        <section className={styles.drawer} data-section-uid="SEC-ADMIN-SG-02-ACTION-DOCK" data-component-uid="SG-02-CMP-DRAWER">
          <h3>{tx(drawerTitle(drawer))}</h3>
          <p className={styles.note}>{tx("sg02.drawer-hint")}</p>
          <div className={styles.kvList}>
            <Kv uid="CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN" label={tx("sg02.col-version")} value={dash} />
            <Kv uid="CTRL-ADMIN-SG-02-GATE-POLICY-OPEN" label={tx("sg02.col-threshold")} value={dash} />
            <Kv uid="CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN" label={tx("sg02.col-department")} value={dash} />
          </div>
          <button type="button" className={styles.btn} onClick={() => setDrawer(null)}>
            {tx("global.common.close")}
          </button>
        </section>
      ) : null}

      {modalUid ? (
        <section className={styles.modal} data-section-uid="SEC-ADMIN-SG-02-ACTION-DOCK" data-component-uid="SG-02-CMP-MODAL" data-control-uid={modalUid}>
          <h3>{tx("sg02.modal-title")}</h3>
          <p className={styles.note}>{tx("sg02.modal-hint")}</p>
          <div className={styles.kvList}>
            <div className={styles.kvRow}>
              <span>{tx("sg02.field-resource-type")}</span>
              <div className={styles.formField}>{tx("sg02.field-resource-type-value")}</div>
            </div>
            <div className={styles.kvRow}>
              <span>{tx("sg02.field-resource-id")}</span>
              <div className={styles.formField}>{dash}</div>
            </div>
            <div className={styles.kvRow}>
              <span>{tx("sg02.field-reason")}</span>
              <div className={`${styles.formField} ${styles.formArea}`}>{dash}</div>
            </div>
          </div>
          <button type="button" className={styles.btn} onClick={() => setModalUid(null)}>
            {tx("global.common.close")}
          </button>
        </section>
      ) : null}
    </div>
  );
}
