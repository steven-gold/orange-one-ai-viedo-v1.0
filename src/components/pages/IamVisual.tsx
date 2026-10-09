"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { IamClientError, fetchIamReadModel, postIamAction, type IamFieldValue } from "@/lib/client";
import { displayIamValue } from "./iamFormat";
import { IAM_BACK_L1, IAM_CHAIN_STEPS, IAM_CONTROL_ACTIONS, IAM_FRONT_L1, IAM_VISIBLE_CONTROLS } from "./iamControls";
import styles from "./IamVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";
const DIRECTORY_ROWS = 5;
const PREVIEW_ROWS = 6;

type FlowStep = 1 | 2 | 3;

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

export function IamVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [, setFields] = useState<IamFieldValue[]>([]);
  const [step, setStep] = useState<FlowStep>(1);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchIamReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : IAM_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof IamClientError ? cause.code : "IAM_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(IAM_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = IAM_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postIamAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayIamValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(IAM_VISIBLE_CONTROLS), []);

  const openCreate = () => {
    setStep(1);
    void act("IAM-01-BTN-ADD");
  };

  const openEdit = () => {
    setStep(1);
    void act("IAM-01-BTN-EDIT");
  };

  const openPreview = () => {
    setStep(3);
    void act("IAM-01-BTN-PREVIEW");
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:IAM-01"
      data-page-state={pageState}
      data-flow-step={step}
      data-component-count="10"
      data-control-count={visibleUids.size}
      aria-label={tx("iam.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("iam.error")}
        </div>
      ) : null}

      <header className={styles.heading} data-component-uid="IAM-01-CMP-CONTEXT" data-section-uid="IAM-01-SEC-01">
        <h1 className={styles.headingTitle}>{tx(step === 3 ? "iam.preview-title" : "iam.title")}</h1>
        <p className={styles.headingMeta}>{tx(step === 3 ? "iam.preview-meta" : "iam.meta")}</p>
      </header>

      {step === 3 ? null : (
        <section className={styles.context} data-section-uid="IAM-01-SEC-01">
          <div className={styles.ctx}>
            <span>{tx("iam.ctx-count")}</span>
            <strong>{dash}</strong>
          </div>
          <div className={styles.ctx}>
            <span>{tx("iam.ctx-model")}</span>
            <strong className={styles.ctxOk}>{tx("iam.ctx-model-value")}</strong>
          </div>
          <div className={styles.ctx}>
            <span>{tx("iam.ctx-grain")}</span>
            <strong>{tx("iam.ctx-grain-value")}</strong>
          </div>
          <Btn uid="IAM-01-BTN-ADD" label={tx("iam.btn-add")} onAct={openCreate} disabled={disabled} primary />
        </section>
      )}

      {step === 3 ? (
        <div className={styles.preview} data-section-uid="IAM-01-SEC-05" data-component-uid="IAM-01-CMP-PREVIEW">
          <aside className={styles.panel}>
            <h2>{tx("iam.preview-context")}</h2>
            <div className={styles.field}>
              <span>{tx("iam.preview-account")}</span>
              <strong>{dash}</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-mode")}</span>
              <strong>{tx("iam.preview-mode-value")}</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-version")}</span>
              <strong>{dash}</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-draft")}</span>
              <strong>{tx("iam.preview-draft-value")}</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-preset")}</span>
              <strong>{dash}</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-correlation")}</span>
              <strong>{dash}</strong>
            </div>
            <div className={styles.warnBox}>{tx("iam.preview-scope-note")}</div>
          </aside>

          <section className={styles.panel}>
            <h2>{tx("iam.preview-impact")}</h2>
            <div className={styles.deltaRow}>
              <div className={styles.delta}>
                <span className={styles.deltaAdded}>{tx("iam.delta-added")}</span>
                <strong className={styles.deltaAdded}>{dash}</strong>
              </div>
              <div className={styles.delta}>
                <span className={styles.deltaRemoved}>{tx("iam.delta-removed")}</span>
                <strong className={styles.deltaRemoved}>{dash}</strong>
              </div>
              <div className={styles.delta}>
                <span>{tx("iam.delta-unchanged")}</span>
                <strong>{dash}</strong>
              </div>
              <div className={styles.delta}>
                <span className={styles.deltaBlocked}>{tx("iam.delta-blocked")}</span>
                <strong className={styles.deltaBlocked}>{dash}</strong>
              </div>
            </div>
            <div className={styles.previewTable}>
              <div className={styles.phead}>
                <span>{tx("iam.col-l1")}</span>
                <span>{tx("iam.col-action")}</span>
                <span>{tx("iam.col-delta")}</span>
                <span>{tx("iam.col-preview-scope")}</span>
              </div>
              {Array.from({ length: PREVIEW_ROWS }, (_, index) => (
                <div className={styles.prow} key={`preview-${index}`}>
                  <span>{dash}</span>
                  <span>{dash}</span>
                  <span>{dash}</span>
                  <span>{dash}</span>
                </div>
              ))}
            </div>
            <div className={styles.warnBox}>{tx("iam.preview-block-note")}</div>
          </section>

          <aside className={styles.panel}>
            <h2>{tx("iam.preview-apply")}</h2>
            <div className={styles.card}>
              <h3>{tx("iam.apply-freshness")}</h3>
              <p>{tx("iam.apply-freshness-hint")}</p>
            </div>
            <div className={styles.card}>
              <h3>{tx("iam.apply-confirm")}</h3>
              <p>{tx("iam.apply-confirm-hint")}</p>
            </div>
            <div className={styles.card}>
              <h3>{tx("iam.apply-idempotency")}</h3>
              <p>{tx("iam.apply-idempotency-hint")}</p>
            </div>
            <div className={styles.card}>
              <h3>{tx("iam.apply-guard")}</h3>
              <p>{tx("iam.apply-guard-hint")}</p>
            </div>
            <div className={styles.card}>
              <h3>{tx("iam.apply-audit")}</h3>
              <p>{tx("iam.apply-audit-hint")}</p>
            </div>
            <div className={styles.card}>
              <h3>{tx("iam.apply-nav")}</h3>
              <p>{tx("iam.apply-nav-hint")}</p>
            </div>
            <div className={styles.previewActions}>
              <button type="button" className={styles.btn} disabled={disabled} onClick={() => setStep(2)}>
                {tx("iam.btn-back")}
              </button>
              <Btn uid="IAM-01-BTN-COMPLETE" label={tx("iam.btn-confirm")} onAct={act} disabled={disabled} primary />
            </div>
          </aside>
        </div>
      ) : (
        <div className={styles.cols}>
          <section className={styles.panel} data-section-uid="IAM-01-SEC-02" data-component-uid="IAM-01-CMP-ACCOUNT-LIST">
            <h2>{tx("iam.directory")}</h2>
            <div className={styles.toolbar}>
              <input
                className={styles.search}
                data-control-uid="IAM-01-CTL-SEARCH"
                disabled={disabled}
                value={query}
                placeholder={tx("iam.search")}
                onFocus={() => {
                  void act("IAM-01-CTL-SEARCH");
                }}
                onChange={(event) => {
                  setQuery(event.target.value);
                }}
              />
              <span className={styles.filter}>{tx("iam.filter-status")}</span>
              <span className={styles.filter}>{tx("iam.filter-identity")}</span>
              <span className={styles.filter}>{tx("iam.filter-risk")}</span>
            </div>
            <div className={styles.table}>
              <div className={styles.thead}>
                <span>{tx("iam.col-account")}</span>
                <span>{tx("iam.col-status")}</span>
                <span>{tx("iam.col-source")}</span>
                <span>{tx("iam.col-mfa")}</span>
                <span>{tx("iam.col-risk")}</span>
                <span>{tx("iam.col-scope")}</span>
                <span>{tx("iam.col-ops")}</span>
              </div>
              {Array.from({ length: DIRECTORY_ROWS }, (_, index) => (
                <div className={styles.trow} key={`row-${index}`}>
                  <span>{dash}</span>
                  <span>{dash}</span>
                  <span>{dash}</span>
                  <span>{dash}</span>
                  <span>{dash}</span>
                  <span>{dash}</span>
                  <span>
                    <button
                      type="button"
                      className={styles.link}
                      data-control-uid="IAM-01-BTN-EDIT"
                      disabled={disabled}
                      onClick={openEdit}
                    >
                      {tx("iam.btn-edit")}
                    </button>
                  </span>
                </div>
              ))}
            </div>
            <div className={styles.detail} data-section-uid="IAM-01-SEC-03" data-component-uid="IAM-01-CMP-ACCOUNT-DETAIL">
              <h3>{tx("iam.detail")}</h3>
              <p>{tx("iam.detail-hint")}</p>
            </div>
          </section>

          <aside className={styles.panel} data-section-uid="IAM-01-SEC-04" data-component-uid="IAM-01-CMP-STEPPER">
            <h2>{tx("iam.flow")}</h2>
            <div className={styles.steps}>
              <button
                type="button"
                className={`${styles.step} ${step === 1 ? styles.stepActive : ""}`}
                disabled={disabled}
                onClick={() => setStep(1)}
              >
                1 {tx("iam.step-1")}
              </button>
              <button
                type="button"
                className={`${styles.step} ${step === 2 ? styles.stepActive : ""}`}
                disabled={disabled}
                onClick={() => setStep(2)}
              >
                2 {tx("iam.step-2")}
              </button>
              <button type="button" className={styles.step} disabled={disabled} onClick={openPreview}>
                3 {tx("iam.step-3")}
              </button>
            </div>

            <div className={styles.card} data-component-uid="IAM-01-CMP-BASIC-DATA">
              <h3>{tx("iam.schema")}</h3>
              <p>{tx("iam.schema-hint")}</p>
              <div className={styles.schema} data-control-uid="IAM-01-CTL-BASIC-DATA" onClick={() => void act("IAM-01-CTL-BASIC-DATA")}>
                {tx("iam.schema-placeholder")}
              </div>
            </div>

            <div className={styles.card} data-component-uid="IAM-01-CMP-PERMISSION-PRESET" data-control-uid="IAM-01-SEL-DEPT-PRESET">
              <div className={styles.preset}>
                <span>{tx("iam.preset")}</span>
                <strong>{tx("iam.preset-empty")}</strong>
              </div>
            </div>

            <div className={styles.l1Grid}>
              <div className={styles.card} data-component-uid="IAM-01-CMP-FRONT-L1" data-control-uid="IAM-01-GRP-FRONT-L1">
                <h3>{tx("iam.front-l1")}</h3>
                <label className={styles.check} data-control-uid="IAM-01-CHK-FRONT-ALL">
                  <span className={styles.box} />
                  {tx("iam.front-all")}
                </label>
                {IAM_FRONT_L1.map((key) => (
                  <label className={styles.check} key={key}>
                    <span className={styles.box} />
                    {tx(key)}
                  </label>
                ))}
              </div>
              <div className={styles.card} data-component-uid="IAM-01-CMP-BACK-L1" data-control-uid="IAM-01-GRP-BACK-L1">
                <h3>{tx("iam.back-l1")}</h3>
                <label className={styles.check} data-control-uid="IAM-01-CHK-BACK-ALL">
                  <span className={styles.box} />
                  {tx("iam.back-all")}
                </label>
                {IAM_BACK_L1.map((key) => (
                  <label className={styles.check} key={key}>
                    <span className={styles.box} />
                    {tx(key)}
                  </label>
                ))}
              </div>
            </div>

            <div className={styles.dock}>
              <Btn uid="IAM-01-BTN-SAVE-DRAFT" label={tx("iam.btn-draft")} onAct={act} disabled={disabled} />
              <Btn uid="IAM-01-BTN-VALIDATE" label={tx("iam.btn-validate")} onAct={act} disabled={disabled} />
              <Btn uid="IAM-01-BTN-PREVIEW" label={tx("iam.btn-preview")} onAct={openPreview} disabled={disabled} />
              <Btn uid="IAM-01-BTN-COMPLETE" label={tx("iam.btn-complete")} onAct={act} disabled={disabled} primary />
            </div>
          </aside>
        </div>
      )}

      {step === 3 ? (
        <section className={styles.chain}>
          <div className={styles.warnBox}>{tx("iam.materialize")}</div>
        </section>
      ) : (
        <section className={styles.chain} data-section-uid="IAM-01-SEC-06" data-component-uid="IAM-01-CMP-AUDIT">
          <h2>{tx("iam.chain")}</h2>
          <div className={styles.chainRow}>
            {IAM_CHAIN_STEPS.flatMap((key, index) => {
              const node = (
                <div key={key} className={styles.chainStep}>
                  {tx(key)}
                </div>
              );
              if (index === 0) return [node];
              return [
                <span key={`${key}-arrow`} className={styles.arrow}>
                  →
                </span>,
                node,
              ];
            })}
          </div>
          <p className={styles.note}>{tx("iam.chain-note")}</p>
        </section>
      )}
    </div>
  );
}
