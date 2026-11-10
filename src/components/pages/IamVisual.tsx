"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { IamClientError, fetchIamReadModel, postIamAction, type IamFieldValue } from "@/lib/client";
import {
  IAM_BACK_L1_CATALOG,
  IAM_DEPT_PRESETS,
  IAM_FRONT_L1_CATALOG,
  IAM_STATE_ACCOUNTS_UID,
  IAM_STATE_APPLY_UID,
  IAM_STATE_DRAFT_UID,
  IAM_STATE_ERROR_UID,
  IAM_STATE_MATERIALIZED_UID,
  IAM_STATE_PREVIEW_UID,
  type IamAccountRow,
  type IamAssignmentDelta,
} from "@/lib/iamState";
import { displayIamValue } from "./iamFormat";
import { IAM_BACK_L1, IAM_CHAIN_STEPS, IAM_CONTROL_ACTIONS, IAM_FRONT_L1, IAM_VISIBLE_CONTROLS } from "./iamControls";
import styles from "./IamVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

type FlowStep = 1 | 2 | 3;

interface IamDraft {
  mode?: string;
  accountId?: string;
  basicData?: { displayName?: string; email?: string; department?: string };
  frontL1?: string[];
  backL1?: string[];
  correlationId?: string;
  savedAt?: string;
  version?: number;
}

interface IamPreview {
  added?: number;
  removed?: number;
  unchanged?: number;
  blocked?: number;
  deltas?: IamAssignmentDelta[];
  stamp?: string;
}

interface IamMaterialized {
  assigned?: number;
  revoked?: number;
  refused?: number;
  operator?: string;
  at?: string;
}

function parseJson<T>(raw: string | null | undefined, fallback: T): T {
  const text = (raw ?? "").trim();
  if (!text) return fallback;
  try {
    return JSON.parse(text) as T;
  } catch {
    return fallback;
  }
}

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
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<IamFieldValue[]>([]);
  const [step, setStep] = useState<FlowStep>(1);
  const [query, setQuery] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [draftEmail, setDraftEmail] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
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
  }, [tick]);

  const valueOf = useCallback(
    (uid: string) => fields.find((row) => row.controlUid === uid)?.value ?? null,
    [fields],
  );

  const accounts = useMemo(() => parseJson<IamAccountRow[]>(valueOf(IAM_STATE_ACCOUNTS_UID), []), [valueOf]);
  const draft = useMemo(() => parseJson<IamDraft>(valueOf(IAM_STATE_DRAFT_UID), {}), [valueOf]);
  const preview = useMemo(() => parseJson<IamPreview>(valueOf(IAM_STATE_PREVIEW_UID), {}), [valueOf]);
  const runtimeError = useMemo(
    () => parseJson<{ code?: string; at?: string }>(valueOf(IAM_STATE_ERROR_UID), {}),
    [valueOf],
  );
  const materialized = useMemo(
    () => parseJson<IamMaterialized>(valueOf(IAM_STATE_MATERIALIZED_UID), {}),
    [valueOf],
  );
  const applyResult = useMemo(
    () => parseJson<{ accountId?: string; status?: string; applied?: string[]; failed?: string[] }>(valueOf(IAM_STATE_APPLY_UID), {}),
    [valueOf],
  );

  const act = useCallback(async (controlUid: string, nextValue?: string) => {
    const actionUid = IAM_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      const result = await postIamAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, nextValue);
      if (result.materialized) {
        setFields((prev) => prev.map((row) => (row.controlUid === IAM_STATE_MATERIALIZED_UID ? { ...row, value: result.materialized } : row)));
      }
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
    setTick((n) => n + 1);
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayIamValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(IAM_VISIBLE_CONTROLS), []);

  const frontSelected = new Set(draft.frontL1 ?? []);
  const backSelected = new Set(draft.backL1 ?? []);
  const frontAllChecked = frontSelected.size === IAM_FRONT_L1.length;
  const backAllChecked = backSelected.size === IAM_BACK_L1.length;
  const auditDrawerOpen = Boolean(runtimeError.code || materialized.at);

  const openCreate = () => {
    setStep(2);
    void act("IAM-01-BTN-ADD");
  };

  const openEdit = (accountId: string) => {
    setStep(2);
    void act("IAM-01-BTN-EDIT", JSON.stringify({ accountId }));
  };

  const openPreview = () => {
    setStep(3);
    void act("IAM-01-BTN-PREVIEW");
  };

  const toggleL1 = (side: "FRONT" | "BACK", key: string, checked: boolean) => {
    void act("IAM-01-GRP-FRONT-L1", JSON.stringify({ side, key, selected: !checked }));
  };

  const saveBasicData = () => {
    void act("IAM-01-CTL-BASIC-DATA", JSON.stringify({ displayName, email: draftEmail }));
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
      {runtimeError.code ? (
        <div className={styles.error} role="alert" data-runtime-error={runtimeError.code}>
          {runtimeError.code}
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
            <strong>{loading ? dash : accounts.length}</strong>
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
              <strong>{draft.accountId ?? dash}</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-mode")}</span>
              <strong>{draft.mode ?? dash}</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-version")}</span>
              <strong>{draft.version ?? dash}</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-draft")}</span>
              <strong>{(draft.frontL1?.length ?? 0) + (draft.backL1?.length ?? 0)} L1</strong>
            </div>
            <div className={styles.field}>
              <span>{tx("iam.preview-correlation")}</span>
              <strong>{draft.correlationId ?? dash}</strong>
            </div>
            <div className={styles.warnBox}>{tx("iam.preview-scope-note")}</div>
          </aside>

          <section className={styles.panel}>
            <h2>{tx("iam.preview-impact")}</h2>
            <div className={styles.deltaRow}>
              <div className={styles.delta}>
                <span className={styles.deltaAdded}>{tx("iam.delta-added")}</span>
                <strong className={styles.deltaAdded}>{preview.added ?? dash}</strong>
              </div>
              <div className={styles.delta}>
                <span className={styles.deltaRemoved}>{tx("iam.delta-removed")}</span>
                <strong className={styles.deltaRemoved}>{preview.removed ?? dash}</strong>
              </div>
              <div className={styles.delta}>
                <span>{tx("iam.delta-unchanged")}</span>
                <strong>{preview.unchanged ?? dash}</strong>
              </div>
              <div className={styles.delta}>
                <span className={styles.deltaBlocked}>{tx("iam.delta-blocked")}</span>
                <strong className={styles.deltaBlocked}>{preview.blocked ?? dash}</strong>
              </div>
            </div>
            <div className={styles.previewTable}>
              <div className={styles.phead}>
                <span>{tx("iam.col-l1")}</span>
                <span>{tx("iam.col-action")}</span>
                <span>{tx("iam.col-delta")}</span>
                <span>{tx("iam.col-preview-scope")}</span>
              </div>
              {(preview.deltas ?? []).length ? (
                (preview.deltas ?? []).map((row) => (
                  <div className={styles.prow} key={`${row.kind}-${row.permission}`}>
                    <span>{row.pageUid ?? dash}</span>
                    <span>{row.permission ?? dash}</span>
                    <span className={row.kind === "ADDED" ? styles.deltaAdded : row.kind === "REMOVED" ? styles.deltaRemoved : ""}>{row.kind}</span>
                    <span>{row.permissionTable ?? dash}</span>
                  </div>
                ))
              ) : (
                Array.from({ length: 4 }, (_, index) => (
                  <div className={styles.prow} key={`preview-${index}`}>
                    <span>{dash}</span>
                    <span>{dash}</span>
                    <span>{dash}</span>
                    <span>{dash}</span>
                  </div>
                ))
              )}
            </div>
            <div className={styles.warnBox}>{tx("iam.preview-block-note")}</div>
          </section>

          <aside className={styles.panel}>
            <h2>{tx("iam.preview-apply")}</h2>
            <div className={styles.card}>
              <h3>{tx("iam.apply-freshness")}</h3>
              <p>{preview.stamp ?? tx("iam.apply-freshness-hint")}</p>
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
              <p>
                {materialized.at
                  ? `assigned=${materialized.assigned ?? 0} revoked=${materialized.revoked ?? 0} refused=${materialized.refused ?? 0}`
                  : tx("iam.apply-audit-hint")}
                {applyResult?.status ? ` · ${applyResult.status}` : ""}
                {applyResult?.failed?.length ? ` · ${applyResult.failed[0]}` : ""}
              </p>
            </div>
            <div className={styles.card}>
              <h3>{tx("iam.apply-nav")}</h3>
              <p>{tx("iam.apply-nav-hint")}</p>
            </div>
            <div className={styles.previewActions}>
              <button type="button" className={styles.btn} disabled={disabled} onClick={() => setStep(2)}>
                {tx("iam.btn-back")}
              </button>
              <Btn
                uid="IAM-01-BTN-COMPLETE"
                label={tx("iam.btn-confirm")}
                onAct={(uid) => {
                  void act(uid, JSON.stringify({ confirm: true }));
                  setStep(1);
                }}
                disabled={disabled}
                primary
              />
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
                  setStep(1);
                  void act("IAM-01-CTL-SEARCH");
                }}
                onChange={(event) => {
                  setQuery(event.target.value);
                }}
                onBlur={() => {
                  void act("IAM-01-BTN-AUDIT", JSON.stringify({ query }));
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
              {accounts.length ? (
                accounts.map((row) => (
                  <div className={styles.trow} key={row.accountUid}>
                    <span>{row.email}</span>
                    <span>{row.status}</span>
                    <span>EXPLICIT</span>
                    <span>{dash}</span>
                    <span>{dash}</span>
                    <span>{(row.frontendL1?.length ?? 0) + (row.backendL1?.length ?? 0)} L1</span>
                    <span>
                      <button
                        type="button"
                        className={styles.link}
                        data-control-uid="IAM-01-BTN-EDIT"
                        disabled={disabled}
                        onClick={() => openEdit(row.accountUid)}
                      >
                        {tx("iam.btn-edit")}
                      </button>
                    </span>
                  </div>
                ))
              ) : (
                Array.from({ length: 2 }, (_, index) => (
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
                        onClick={() => openEdit("")}
                      >
                        {tx("iam.btn-edit")}
                      </button>
                    </span>
                  </div>
                ))
              )}
            </div>
            <div className={styles.detail} data-section-uid="IAM-01-SEC-03" data-component-uid="IAM-01-CMP-ACCOUNT-DETAIL">
              <h3>{tx("iam.detail")}</h3>
              <p>{draft.accountId ? `${draft.accountId} · ${(draft.frontL1?.length ?? 0) + (draft.backL1?.length ?? 0)} L1 · v${draft.version ?? 0}` : tx("iam.detail-hint")}</p>
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
              <div className={styles.schema} data-control-uid="IAM-01-CTL-BASIC-DATA">
                <input
                  aria-label="displayName"
                  placeholder="displayName"
                  value={displayName}
                  disabled={disabled}
                  onChange={(event) => setDisplayName(event.target.value)}
                  onBlur={saveBasicData}
                />
                <input
                  aria-label="email"
                  placeholder="email"
                  value={draftEmail}
                  disabled={disabled}
                  onChange={(event) => setDraftEmail(event.target.value)}
                  onBlur={saveBasicData}
                />
              </div>
            </div>

            <div className={styles.card} data-component-uid="IAM-01-CMP-PERMISSION-PRESET" data-control-uid="IAM-01-SEL-DEPT-PRESET">
              <div className={styles.preset}>
                <span>{tx("iam.preset")}</span>
                <select
                  aria-label={tx("iam.preset")}
                  disabled={disabled}
                  value=""
                  onChange={(event) => {
                    const presetId = event.target.value;
                    if (presetId) void act("IAM-01-SEL-DEPT-PRESET", JSON.stringify({ presetId }));
                  }}
                >
                  <option value="">{tx("iam.preset-empty")}</option>
                  {IAM_DEPT_PRESETS.map((preset) => (
                    <option key={preset.presetId} value={preset.presetId}>
                      {preset.presetId}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className={styles.l1Grid}>
              <div className={styles.card} data-component-uid="IAM-01-CMP-FRONT-L1" data-control-uid="IAM-01-GRP-FRONT-L1">
                <h3>{tx("iam.front-l1")}</h3>
                <label className={styles.check} data-control-uid="IAM-01-CHK-FRONT-ALL">
                  <input
                    type="checkbox"
                    disabled={disabled}
                    checked={frontAllChecked}
                    onChange={() => void act("IAM-01-CHK-FRONT-ALL")}
                  />
                  {tx("iam.front-all")}
                </label>
                {IAM_FRONT_L1.map((key) => (
                  <label className={styles.check} key={key}>
                    <input
                      type="checkbox"
                      disabled={disabled}
                      checked={frontSelected.has(key)}
                      onChange={() => toggleL1("FRONT", key, frontSelected.has(key))}
                    />
                    {tx(key)}
                  </label>
                ))}
              </div>
              <div className={styles.card} data-component-uid="IAM-01-CMP-BACK-L1" data-control-uid="IAM-01-GRP-BACK-L1">
                <h3>{tx("iam.back-l1")}</h3>
                <label className={styles.check} data-control-uid="IAM-01-CHK-BACK-ALL">
                  <input
                    type="checkbox"
                    disabled={disabled}
                    checked={backAllChecked}
                    onChange={() => void act("IAM-01-CHK-BACK-ALL")}
                  />
                  {tx("iam.back-all")}
                </label>
                {IAM_BACK_L1.map((key) => (
                  <label className={styles.check} key={key}>
                    <input
                      type="checkbox"
                      disabled={disabled}
                      checked={backSelected.has(key)}
                      onChange={() => toggleL1("BACK", key, backSelected.has(key))}
                    />
                    {tx(key)}
                  </label>
                ))}
              </div>
            </div>

            <div className={styles.dock}>
              <Btn uid="IAM-01-BTN-SAVE-DRAFT" label={tx("iam.btn-draft")} onAct={(uid) => void act(uid)} disabled={disabled} />
              <Btn uid="IAM-01-BTN-VALIDATE" label={tx("iam.btn-validate")} onAct={(uid) => void act(uid)} disabled={disabled} />
              <Btn uid="IAM-01-BTN-PREVIEW" label={tx("iam.btn-preview")} onAct={openPreview} disabled={disabled} />
              <Btn
                uid="IAM-01-BTN-COMPLETE"
                label={tx("iam.btn-complete")}
                onAct={(uid) => void act(uid, JSON.stringify({ confirm: true }))}
                disabled={disabled}
                primary
              />
            </div>
          </aside>
        </div>
      )}

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
        {auditDrawerOpen ? (
          <div className={styles.detail} data-audit-drawer="open">
            <p>
              {materialized.at
                ? `materialized: assigned=${materialized.assigned ?? 0} revoked=${materialized.revoked ?? 0} refused=${materialized.refused ?? 0} @ ${materialized.at}`
                : ""}
            </p>
          </div>
        ) : null}
      </section>
    </div>
  );
}
