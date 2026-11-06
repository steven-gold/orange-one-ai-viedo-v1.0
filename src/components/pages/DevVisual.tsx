"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { DevClientError, fetchDevReadModel, postDevAction, type DevFieldValue } from "@/lib/client";
import { downloadDevCsv } from "@/lib/devExport";
import {
  activeEmailContact,
  companyEligibleForMessage,
  searchAudienceProjection,
  searchDirectoryProjection,
  type DevCampaignStatus,
  type DevCandidate,
  type DevCandidateStatus,
  type DevCompany,
  type DevDelivery,
  type DevDeliveryStatus,
  type DevIdentityKind,
  type DevJobStatus,
  type DevMode,
  type DevOpportunityState,
  type DevProfile,
  type DevSignal,
  type DevSignalStatus,
  profileIsReady,
  workbenchFromFields,
} from "@/lib/devState";
import { displayDevValue } from "./devFormat";
import { DEV_CONTROL_ACTIONS, DEV_STAGES, DEV_VISIBLE_CONTROLS, type DevStage } from "./devControls";
import styles from "./DevVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";
const EMPTY_PROFILE: DevProfile = {
  profileId: "",
  version: 0,
  product: "",
  industry: "",
  market: "",
  keywords: "",
  exclude: "",
  language: "zh-TW",
  priority: "NORMAL",
  sourceScope: "ALLOWED",
  mode: "SINGLE",
  status: "DRAFT",
};

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
  danger = false,
  title,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  danger?: boolean;
  title?: string;
}) {
  const className = [styles.btn, primary ? styles.btnPrimary : "", danger ? styles.btnDanger : ""].filter(Boolean).join(" ");
  return (
    <button type="button" className={className} data-control-uid={uid} disabled={disabled} title={title} onClick={() => onAct(uid)}>
      {label}
    </button>
  );
}

const JOB_LABEL: Record<DevJobStatus, TranslationKey> = {
  RUNNING: "dev.job-running",
  PAUSED: "dev.job-paused",
  STOPPED: "dev.job-stopped",
  COMPLETE: "dev.job-complete",
  EXTERNAL_PENDING: "dev.job-pending",
};

const PAGE_SIZE = 20;
const CONTINUOUS_PULL_INTERVAL_MS = 15000;
const JOB_IDLE_AFTER_MS = CONTINUOUS_PULL_INTERVAL_MS * 2;

const OPP_LABEL: Record<DevOpportunityState, TranslationKey> = {
  OPEN: "dev.opp-open",
  QUALIFIED: "dev.opp-qualified",
  CONTACTED: "dev.opp-contacted",
  REPLIED: "dev.opp-replied",
  PROPOSAL: "dev.opp-proposal",
  WON: "dev.opp-won",
  LOST: "dev.opp-lost",
  SUPPRESSED: "dev.opp-suppressed",
};

const OPP_NEXT: Record<DevOpportunityState, DevOpportunityState[]> = {
  OPEN: ["QUALIFIED", "SUPPRESSED"],
  QUALIFIED: ["CONTACTED", "SUPPRESSED"],
  CONTACTED: ["REPLIED", "SUPPRESSED"],
  REPLIED: ["PROPOSAL", "SUPPRESSED"],
  PROPOSAL: ["WON", "LOST", "SUPPRESSED"],
  WON: [],
  LOST: [],
  SUPPRESSED: [],
};

const CANDIDATE_LABEL: Record<DevCandidateStatus, TranslationKey> = {
  REVIEW: "dev.candidate-review",
  APPROVED: "dev.candidate-approved",
  CHANGE_REQUEST: "dev.candidate-cr",
};

const CAMPAIGN_LABEL: Record<DevCampaignStatus, TranslationKey> = {
  REVIEW: "dev.campaign-review",
  APPROVED: "dev.campaign-approved",
  QUEUED: "dev.campaign-queued",
  STOPPED: "dev.campaign-stopped",
};

const DELIVERY_LABEL: Record<DevDeliveryStatus, TranslationKey> = {
  QUEUED: "dev.delivery-queued",
  EXTERNAL_PENDING: "dev.delivery-pending",
  STOPPED: "dev.delivery-stopped",
  SENT: "dev.delivery-sent",
  FAILED: "dev.delivery-failed",
};

const SIGNAL_LABEL: Record<DevSignalStatus, TranslationKey> = {
  NEW: "dev.signal-new",
  QUALIFIED: "dev.signal-qualified",
  IGNORED: "dev.signal-ignored",
  ENGAGED: "dev.signal-engaged",
  CONVERTED: "dev.signal-converted",
  SUPPRESSED: "dev.signal-suppressed",
};

const IDENTITY_LABEL: Record<DevIdentityKind, TranslationKey> = {
  REGISTRATION: "dev.identity-registration",
  JURISDICTION: "dev.identity-jurisdiction",
  NAME_ONLY: "dev.identity-name-only",
};

function errorKey(code: string | null | undefined): TranslationKey | null {
  if (!code) return null;
  const key = `dev.err.${code}` as TranslationKey;
  return key;
}

export function DevVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<DevFieldValue[]>([]);
  const [stage, setStage] = useState<DevStage>(1);
  const [query, setQuery] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<DevProfile>(EMPTY_PROFILE);
  const [selectedSignalId, setSelectedSignalId] = useState("");
  const [selectedSignalIds, setSelectedSignalIds] = useState<string[]>([]);
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<string[]>([]);
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<string[]>([]);
  const [selectedRecipientIds, setSelectedRecipientIds] = useState<string[]>([]);
  const [contactType, setContactType] = useState<"EMAIL" | "PHONE" | "ADDRESS">("EMAIL");
  const [contactValue, setContactValue] = useState("");
  const [contactSource, setContactSource] = useState("人工");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [audienceQuery, setAudienceQuery] = useState("");
  const [signalPage, setSignalPage] = useState(0);
  const [signalFilter, setSignalFilter] = useState<"ALL" | "NEW" | "HANDLED">("ALL");
  const [dirPage, setDirPage] = useState(0);
  const [candSubject, setCandSubject] = useState("");
  const [candBody, setCandBody] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
    fetchDevReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        const nextFields = model.fields.length ? model.fields : DEV_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null }));
        setFields(nextFields);
        const workbench = workbenchFromFields(nextFields);
        if (workbench.profile) setDraft(workbench.profile);
        if (workbench.query) setQuery(workbench.query);
        if (workbench.audienceQuery) setAudienceQuery(workbench.audienceQuery);
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
  }, [tick]);

  const act = useCallback(async (controlUid: string, payload?: Record<string, unknown>) => {
    const actionUid = DEV_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    setBusy(true);
    try {
      await postDevAction(
        DEFAULT_ACCOUNT,
        controlUid,
        actionUid,
        DEFAULT_SESSION,
        payload ? JSON.stringify(payload) : undefined,
      );
      if (controlUid === "DEV-01-BTN-SOURCE-MANAGE") {
        window.location.assign("/admin/knowledge");
        return;
      }
      if (controlUid === "DEV-01-BTN-COMPANY-DELETE") {
        setSelectedCompanyIds([]);
      }
      if (controlUid === "DEV-01-BTN-CANDIDATE-DELETE") {
        setSelectedCandidateIds([]);
      }
      if (controlUid === "DEV-01-BTN-DELIVERY-SEND" || controlUid === "DEV-01-BTN-DELIVERY-ACK") {
        setSelectedRecipientIds([]);
      }
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
    setBusy(false);
    setTick((n) => n + 1);
  }, []);

  const ignoreSelectedSignals = useCallback(async () => {
    if (!selectedSignalIds.length) return;
    setBusy(true);
    try {
      for (const signalId of selectedSignalIds) {
        await postDevAction(
          DEFAULT_ACCOUNT,
          "DEV-01-BTN-SIGNAL-IGNORE",
          "DEV-01-ACT-SIGNAL-IGNORE",
          DEFAULT_SESSION,
          JSON.stringify({ signalId }),
        );
      }
      setSelectedSignalIds([]);
    } catch {
      // Fail-closed: per-signal failures surface via the read model state error.
    }
    setBusy(false);
    setTick((n) => n + 1);
  }, [selectedSignalIds]);

  const disabled = (!authorized && !loading) || busy;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey, params?: Record<string, string | number>) => t(key, params);
  const dash = displayDevValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(DEV_VISIBLE_CONTROLS), []);
  const workbench = useMemo(() => workbenchFromFields(fields), [fields]);
  const actionError = errorKey(workbench.error?.code);
  const jobStatus = workbench.job?.status ?? null;
  const jobPolling = jobStatus === "RUNNING" || jobStatus === "EXTERNAL_PENDING";
  const jobCollected = workbench.job?.collected ?? 0;
  const jobCursor = workbench.job?.cursor ?? 0;
  const [jobIdle, setJobIdle] = useState(false);
  useEffect(() => {
    if (!jobPolling) {
      setJobIdle(false);
      return;
    }
    const timer = setTimeout(() => setJobIdle(true), JOB_IDLE_AFTER_MS);
    return () => clearTimeout(timer);
  }, [jobPolling, jobCollected, jobCursor]);
  useEffect(() => {
    if (!jobPolling) return;
    const timer = setInterval(() => {
      postDevAction(DEFAULT_ACCOUNT, "DEV-01-BTN-REFRESH", "DEV-01-ACT-REFRESH", DEFAULT_SESSION, "CONTINUOUS_PULL")
        .then(() => setTick((n) => n + 1))
        .catch(() => {
          // Fail-closed: the next interval retries the continuous pull.
        });
    }, CONTINUOUS_PULL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [jobPolling]);
  const jobLabel = jobStatus
    ? jobStatus === "RUNNING" && jobIdle
      ? tx("dev.job-running-idle")
      : tx(JOB_LABEL[jobStatus])
    : loading
      ? dash
      : tx("dev.job-idle");
  const companies = searchDirectoryProjection(workbench.companies, query);
  const audiencePreview = searchAudienceProjection(workbench.companies, workbench.audienceQuery);
  const filteredSignals = workbench.signals.filter((signal) =>
    signalFilter === "ALL" ? true : signalFilter === "NEW" ? signal.status === "NEW" : signal.status !== "NEW",
  );
  const signalTotal = filteredSignals.length;
  const signalPages = Math.max(1, Math.ceil(signalTotal / PAGE_SIZE));
  const safeSignalPage = Math.min(signalPage, signalPages - 1);
  const signalSlice = filteredSignals.slice(safeSignalPage * PAGE_SIZE, (safeSignalPage + 1) * PAGE_SIZE);
  const dirTotal = companies.length;
  const dirPages = Math.max(1, Math.ceil(dirTotal / PAGE_SIZE));
  const safeDirPage = Math.min(dirPage, dirPages - 1);
  const dirSlice = companies.slice(safeDirPage * PAGE_SIZE, (safeDirPage + 1) * PAGE_SIZE);
  const selectedCompanyId = selectedCompanyIds[0] ?? companies[0]?.companyId ?? "";
  const selectedCompany = workbench.companies.find((company) => company.companyId === selectedCompanyId) ?? null;
  const selectedHasEmail = selectedCompany ? Boolean(activeEmailContact(selectedCompany)) : false;
  const selectedCanMessage = selectedCompany ? companyEligibleForMessage(selectedCompany) : false;
  const selectedCandidate =
    workbench.candidates.find((item) => item.candidateId === selectedCandidateId) ??
    workbench.candidates.find((item) => item.status === "REVIEW") ??
    workbench.candidates[workbench.candidates.length - 1] ??
    null;
  const approvedCandidate = workbench.candidates.find((item) => item.status === "APPROVED") ?? null;
  const campaign = workbench.campaign;
  const campaignCandidate = campaign
    ? workbench.candidates.find((item) => item.candidateId === campaign.candidateId) ?? null
    : null;
  const deliveries = workbench.deliveries;

  const selectStage = (next: DevStage, uid: string) => {
    setStage(next);
    void act(uid);
  };

  const toggleCompany = (companyId: string) => {
    setSelectedCompanyIds((current) =>
      current.includes(companyId) ? current.filter((id) => id !== companyId) : [...current, companyId],
    );
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
      {actionError ? (
        <div className={styles.error} role="alert">
          {workbench.error?.code === "DEV_ACTION_UNDEFINED" && workbench.error.detail
            ? `${tx(actionError)} [${workbench.error.detail} · ${workbench.error.errUid}]`
            : tx(actionError)}
        </div>
      ) : null}
      {busy ? (
        <div className={styles.busyBar} role="status" aria-busy="true">
          {tx("dev.busy")}
        </div>
      ) : null}

      <header className={styles.heading} data-component-uid="DEV-01-CMP-CONTEXT" data-section-uid="DEV-01-SEC-01">
        <h1 className={styles.headingTitle}>{tx("dev.title")}</h1>
        <p className={styles.headingMeta}>{tx("dev.meta")}</p>
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

      <section className={styles.context} data-section-uid="DEV-01-SEC-01">
          <div className={styles.ctx}>
            <span>{tx("dev.ctx-stage")}</span>
            <strong className={styles.ctxOk}>{tx(DEV_STAGES[stage - 1].labelKey)}</strong>
          </div>
          <div className={styles.ctx}>
            <span>{tx("dev.ctx-scope")}</span>
            <strong>{tx("dev.ctx-scope-value")}</strong>
          </div>
          <div className={styles.ctx}>
            <span>{tx("dev.ctx-run")}</span>
            <strong>{jobLabel}</strong>
          </div>
          <div className={styles.ctx}>
            <span>{tx("dev.ctx-policy")}</span>
            <strong className={styles.ctxOk}>{tx("dev.ctx-policy-value")}</strong>
          </div>
        </section>

      {stage === 1 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-03">
            <div data-component-uid="DEV-01-CMP-DISCOVERY-SETUP">
            <div className={styles.profile}>
              <div>
                <h3>{tx("dev.profile-title")}</h3>
                <p>{tx("dev.profile-hint")}</p>
              </div>
              <div className={styles.profileActions}>
                <button type="button" className={styles.btn} disabled={disabled} onClick={() => setDrawerOpen(true)}>
                  {tx("dev.btn-topic")}
                </button>
                <button
                  type="button"
                  className={styles.btn}
                  disabled={disabled}
                  onClick={() => void act("DEV-01-BTN-SOURCE-MANAGE")}
                >
                  {tx("dev.btn-source")}
                </button>
              </div>
            </div>
            <div className={styles.fields}>
              <label className={styles.field}>
                <span>{tx("dev.field-product")}</span>
                <input
                  className={styles.fieldInput}
                  value={draft.product}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, product: event.target.value }))}
                />
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-industry")}</span>
                <input
                  className={styles.fieldInput}
                  value={draft.industry}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, industry: event.target.value }))}
                />
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-market")}</span>
                <input
                  className={styles.fieldInput}
                  value={draft.market}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, market: event.target.value }))}
                />
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-keywords")}</span>
                <input
                  className={styles.fieldInput}
                  value={draft.keywords}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, keywords: event.target.value }))}
                />
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-exclude")}</span>
                <input
                  className={styles.fieldInput}
                  value={draft.exclude}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, exclude: event.target.value }))}
                />
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-language")}</span>
                <select
                  className={styles.fieldSelect}
                  value={draft.language}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, language: event.target.value }))}
                >
                  <option value="zh-TW">{tx("dev.language-zh-tw")}</option>
                  <option value="zh-CN">{tx("dev.language-zh-cn")}</option>
                  <option value="en">{tx("dev.language-en")}</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-priority")}</span>
                <select
                  className={styles.fieldSelect}
                  value={draft.priority}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, priority: event.target.value as DevProfile["priority"] }))}
                >
                  <option value="HIGH">{tx("dev.priority-high")}</option>
                  <option value="NORMAL">{tx("dev.priority-normal")}</option>
                  <option value="LOW">{tx("dev.priority-low")}</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-source-scope")}</span>
                <select
                  className={styles.fieldSelect}
                  value={draft.sourceScope}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, sourceScope: event.target.value }))}
                >
                  <option value="ALLOWED">{tx("dev.source-scope-allowed")}</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.field-mode")}</span>
                <select
                  className={styles.fieldSelect}
                  value={draft.mode}
                  disabled={disabled}
                  onChange={(event) => setDraft((current) => ({ ...current, mode: event.target.value as DevMode }))}
                >
                  <option value="SINGLE">{tx("dev.mode-single")}</option>
                  <option value="CONTINUOUS">{tx("dev.mode-continuous")}</option>
                </select>
              </label>
            </div>
            </div>
            <div data-component-uid="DEV-01-CMP-DISCOVERY-RUNTIME">
            <div className={styles.card}>
              <h3>{tx("dev.runtime-title")}</h3>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span>{tx("dev.ctx-run")}</span>
                  <strong>{jobLabel}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.rail-connector")}</span>
                  <strong>{jobStatus === "EXTERNAL_PENDING" ? tx("dev.connector-pending") : jobStatus === "RUNNING" ? (jobIdle ? tx("dev.job-running-idle") : tx("dev.job-running")) : dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.signal-title")}</span>
                  <strong>{tx("dev.runtime-summary", { n: workbench.signals.length })}</strong>
                </div>
              </div>
            </div>
            <div className={styles.card}>
              <h3 className={styles.cardHead}>
                {tx("dev.signal-title")}
                <span className={styles.filterChips}>
                  {(["ALL", "NEW", "HANDLED"] as const).map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      className={`${styles.chip} ${signalFilter === chip ? styles.chipActive : ""}`}
                      disabled={disabled}
                      onClick={() => {
                        setSignalFilter(chip);
                        setSignalPage(0);
                      }}
                    >
                      {tx(chip === "ALL" ? "dev.filter-all" : chip === "NEW" ? "dev.filter-new" : "dev.filter-handled")}
                    </button>
                  ))}
                </span>
              </h3>
              <div className={styles.table}>
                <div className={`${styles.thead} ${styles.signalHead}`}>
                  <span className={styles.check}>
                    <input
                      type="checkbox"
                      aria-label={tx("dev.col-select-all")}
                      checked={signalSlice.length > 0 && signalSlice.every((signal) => selectedSignalIds.includes(signal.signalId))}
                      disabled={disabled || !signalTotal}
                      onChange={() => {
                        const allSelected = signalSlice.every((signal) => selectedSignalIds.includes(signal.signalId));
                        setSelectedSignalIds(
                          allSelected
                            ? selectedSignalIds.filter((id) => !signalSlice.some((signal) => signal.signalId === id))
                            : [...new Set([...selectedSignalIds, ...signalSlice.map((signal) => signal.signalId)])],
                        );
                      }}
                    />
                    {tx("dev.col-company")}
                  </span>
                  <span>{tx("dev.col-contact")}</span>
                  <span>{tx("dev.col-intent")}</span>
                  <span>{tx("dev.col-evidence")}</span>
                  <span>{tx("dev.col-freshness")}</span>
                  <span>{tx("dev.col-match")}</span>
                  <span>{tx("dev.col-opportunity")}</span>
                  <span>{tx("dev.col-action")}</span>
                </div>
                {signalTotal ? (
                  <div className={styles.signalScroll}>
                    {signalSlice.map((signal: DevSignal) => (
                      <div
                        className={`${styles.trow} ${styles.signalRow} ${selectedSignalId === signal.signalId ? styles.trowSelected : ""}`}
                        key={signal.signalId}
                        onClick={() => setSelectedSignalId(signal.signalId)}
                      >
                        <span className={styles.check}>
                          <input
                            type="checkbox"
                            checked={selectedSignalIds.includes(signal.signalId)}
                            disabled={disabled}
                            onChange={(event) => {
                              event.stopPropagation();
                              setSelectedSignalIds((current) =>
                                current.includes(signal.signalId)
                                  ? current.filter((id) => id !== signal.signalId)
                                  : [...current, signal.signalId],
                              );
                            }}
                          />
                          <span className={styles.checkText} title={signal.companyName}>
                            {signal.companyName}
                          </span>
                        </span>
                        <span title={[signal.email, signal.phone, signal.address].filter(Boolean).join("、")}>
                          {[signal.email, signal.phone, signal.address].filter(Boolean).join("、") || dash}
                        </span>
                        <span title={signal.intent}>{signal.intent}</span>
                        <span title={signal.evidence}>{signal.evidence}</span>
                        <span>{signal.freshness}</span>
                        <span>{signal.match}</span>
                        <span>{tx(OPP_LABEL[(Object.prototype.hasOwnProperty.call(OPP_LABEL, signal.opportunity) ? signal.opportunity : "OPEN") as DevOpportunityState])}</span>
                        <span className={styles.rowAct}>
                          {selectedSignalId === signal.signalId
                            ? tx("dev.row-selected")
                            : Object.prototype.hasOwnProperty.call(SIGNAL_LABEL, signal.status)
                              ? tx(SIGNAL_LABEL[signal.status])
                              : signal.status}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className={styles.empty}>{loading ? dash : tx("dev.empty-signals")}</p>
                )}
                {signalTotal ? (
                  <div className={styles.pager}>
                    <button
                      type="button"
                      className={styles.btn}
                      disabled={safeSignalPage === 0}
                      onClick={() => setSignalPage(safeSignalPage - 1)}
                    >
                      {tx("dev.page-prev")}
                    </button>
                    <span className={styles.pagerStatus}>
                      {tx("dev.page-status-total", { total: signalTotal, x: safeSignalPage + 1, y: signalPages })}
                    </span>
                    <button
                      type="button"
                      className={styles.btn}
                      disabled={safeSignalPage >= signalPages - 1}
                      onClick={() => setSignalPage(safeSignalPage + 1)}
                    >
                      {tx("dev.page-next")}
                    </button>
                  </div>
                ) : null}
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.btn}
                  disabled={disabled || !selectedSignalId}
                  onClick={() => void act("DEV-01-BTN-SIGNAL-QUALIFY", { signalId: selectedSignalId })}
                >
                  {tx("dev.btn-qualify")}
                </button>
                <button
                  type="button"
                  className={styles.btn}
                  disabled={disabled || !selectedSignalId}
                  onClick={() => void act("DEV-01-BTN-SIGNAL-IGNORE", { signalId: selectedSignalId })}
                >
                  {tx("dev.btn-ignore")}
                </button>
                <button
                  type="button"
                  className={styles.btn}
                  disabled={disabled || !selectedSignalIds.length}
                  onClick={() => void ignoreSelectedSignals()}
                  title={tx("dev.qualify-hint")}
                >
                  {tx("dev.btn-ignore-selected", { n: selectedSignalIds.length })}
                </button>
                <span className={styles.note}>{tx("dev.qualify-hint")}</span>
              </div>
            </div>
            </div>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.btn}
                disabled={disabled}
                onClick={() =>
                  void act("DEV-01-BTN-PROFILE-SAVE", {
                    product: draft.product,
                    industry: draft.industry,
                    market: draft.market,
                    keywords: draft.keywords,
                    exclude: draft.exclude,
                    language: draft.language,
                    priority: draft.priority,
                    sourceScope: draft.sourceScope,
                    mode: draft.mode,
                  })
                }
              >
                {tx("dev.btn-profile-save")}
              </button>
            </div>
          </section>
          <GovernanceRail
            t={tx}
            dash={dash}
            disabled={disabled}
            onDrawer={() => setDrawerOpen(true)}
            connector={jobStatus === "EXTERNAL_PENDING" ? tx("dev.connector-pending") : dash}
            blocker={workbench.job?.blocker === "SHARED_ACQUISITION_UNAVAILABLE" ? tx("dev.blocker-acquisition") : dash}
          />
        </div>
      ) : null}

      {stage === 2 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-04">
            <div data-component-uid="DEV-01-CMP-DIRECTORY">
            <h2>{tx("dev.directory-title")}</h2>
            <p className={styles.note}>{tx("dev.directory-hint")}</p>
            <div className={styles.toolbar}>
              <input
                className={styles.search}
                placeholder={tx("dev.search-company")}
                value={query}
                disabled={disabled}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void act("DEV-01-BTN-DIRECTORY-SEARCH", { query });
                }}
              />
              <Btn
                uid="DEV-01-BTN-COMPANY-DELETE"
                label={tx("dev.btn-company-delete")}
                onAct={() => void act("DEV-01-BTN-COMPANY-DELETE", { companyIds: selectedCompanyIds })}
                disabled={disabled || !selectedCompanyIds.length}
                danger
              />
              <Btn
                uid="DEV-01-BTN-COMPANY-SUPPRESS"
                label={tx("dev.btn-company-suppress")}
                onAct={() => void act("DEV-01-BTN-COMPANY-SUPPRESS", { companyIds: selectedCompanyIds, suppress: true })}
                disabled={disabled || !selectedCompanyIds.length}
                title={tx("dev.suppress-hint")}
              />
              <Btn
                uid="DEV-01-BTN-COMPANY-SUPPRESS"
                label={tx("dev.btn-company-unsuppress")}
                onAct={() => void act("DEV-01-BTN-COMPANY-SUPPRESS", { companyIds: selectedCompanyIds, suppress: false })}
                disabled={disabled || !selectedCompanyIds.length}
              />
              {query ? (
                <button
                  type="button"
                  className={styles.btn}
                  disabled={disabled}
                  onClick={() => {
                    setQuery("");
                    void act("DEV-01-BTN-DIRECTORY-SEARCH", { query: "" });
                  }}
                >
                  {tx("dev.btn-clear-search")}
                </button>
              ) : null}
            </div>
            <div className={styles.table}>
              <div className={`${styles.thead} ${styles.dirHead}`}>
                <span>
                  <input
                    type="checkbox"
                    aria-label={tx("dev.col-select-all")}
                    checked={dirSlice.length > 0 && dirSlice.every((company) => selectedCompanyIds.includes(company.companyId))}
                    disabled={disabled || !dirTotal}
                    onChange={() => {
                      const allSelected = dirSlice.every((company) => selectedCompanyIds.includes(company.companyId));
                      setSelectedCompanyIds(
                        allSelected
                          ? selectedCompanyIds.filter((id) => !dirSlice.some((company) => company.companyId === id))
                          : [...new Set([...selectedCompanyIds, ...dirSlice.map((company) => company.companyId)])],
                      );
                    }}
                  />
                  {tx("dev.col-identity")}
                </span>
                <span>{tx("dev.col-aliases")}</span>
                <span>{tx("dev.col-contact")}</span>
                <span>{tx("dev.col-evidence")}</span>
                <span>{tx("dev.col-opportunity")}</span>
                <span>{tx("dev.col-suppression")}</span>
                <span>{tx("dev.col-action")}</span>
              </div>
              {dirTotal ? (
                <div className={styles.signalScroll}>
                  {dirSlice.map((company: DevCompany) => (
                    <div
                      className={`${styles.trow} ${styles.dirRow} ${selectedCompanyIds.includes(company.companyId) ? styles.trowSelected : ""}`}
                      key={company.companyId}
                    >
                      <span className={styles.check}>
                        <input
                          type="checkbox"
                          checked={selectedCompanyIds.includes(company.companyId)}
                          disabled={disabled}
                          onChange={() => toggleCompany(company.companyId)}
                        />
                        <span
                          className={styles.checkText}
                          title={`${company.name}／${t(IDENTITY_LABEL[company.identityKind])}`}
                        >
                          {company.name}／{tx(IDENTITY_LABEL[company.identityKind])}
                        </span>
                      </span>
                      <span title={company.aliases.join("、")}>{company.aliases.join("、") || dash}</span>
                      <span title={company.contacts.map((item) => item.value).join("、")}>
                        {company.contacts.map((item) => item.value).join("、") || dash}
                      </span>
                      <span title={company.evidence}>{company.evidence || dash}</span>
                      <span>{tx(OPP_LABEL[company.opportunity.state])}</span>
                      <span title={company.suppression}>{company.suppression || dash}</span>
                      <span className={styles.rowAct}>{tx("dev.row-open")}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className={styles.empty}>{loading ? dash : tx("dev.empty-companies")}</p>
              )}
              {dirTotal ? (
                <div className={styles.pager}>
                  <button
                    type="button"
                    className={styles.btn}
                    disabled={safeDirPage === 0}
                    onClick={() => setDirPage(safeDirPage - 1)}
                  >
                    {tx("dev.page-prev")}
                  </button>
                  <span className={styles.pagerStatus}>
                    {tx("dev.page-status-total", { total: dirTotal, x: safeDirPage + 1, y: dirPages })}
                    {selectedCompanyIds.length ? (
                      <span className={styles.selectedBadge}>{tx("dev.selected-count", { n: selectedCompanyIds.length })}</span>
                    ) : null}
                  </span>
                  <button
                    type="button"
                    className={styles.btn}
                    disabled={safeDirPage >= dirPages - 1}
                    onClick={() => setDirPage(safeDirPage + 1)}
                  >
                    {tx("dev.page-next")}
                  </button>
                </div>
              ) : null}
            </div>
            <p className={styles.note}>{tx("dev.selected-count", { n: selectedCompanyIds.length })}</p>
            {selectedCompany && !selectedHasEmail ? <p className={styles.note}>{tx("dev.contact-missing-email")}</p> : null}
            {workbench.exported ? <p className={styles.note}>{tx("dev.export-done", { n: workbench.exported.companyCount })}</p> : null}
            </div>
            <div data-component-uid="DEV-01-CMP-MERGE">
            <p className={styles.note}>{tx("dev.merge-hint")}</p>
            {workbench.merge ? <p className={styles.note}>{tx("dev.merge-ready")}</p> : null}
            </div>
            <div className={styles.fields}>
              <label className={styles.field}>
                <span>{tx("dev.contact-type")}</span>
                <select className={styles.fieldSelect} value={contactType} disabled={disabled} onChange={(event) => setContactType(event.target.value as "EMAIL" | "PHONE" | "ADDRESS")}>
                  <option value="EMAIL">{tx("dev.contact-email")}</option>
                  <option value="PHONE">{tx("dev.contact-phone")}</option>
                  <option value="ADDRESS">{tx("dev.contact-address")}</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>{tx("dev.contact-value")}</span>
                <input className={styles.fieldInput} value={contactValue} disabled={disabled} onChange={(event) => setContactValue(event.target.value)} />
              </label>
              <label className={styles.field}>
                <span>{tx("dev.contact-source")}</span>
                <input className={styles.fieldInput} value={contactSource} disabled={disabled} onChange={(event) => setContactSource(event.target.value)} />
              </label>
            </div>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.btn}
                disabled={disabled || !selectedCompanyId || !contactValue}
                onClick={() =>
                  void act("DEV-01-BTN-CONTACT-UPSERT", {
                    companyId: selectedCompanyId,
                    contactType,
                    contactValue,
                    contactSource,
                  })
                }
              >
                {tx("dev.btn-contact")}
              </button>
              <select
                className={styles.fieldSelect}
                disabled={disabled || !selectedCompany}
                value=""
                onChange={(event) => {
                  const nextState = event.target.value as DevOpportunityState;
                  if (nextState) void act("DEV-01-BTN-OPPORTUNITY-STATE", { companyId: selectedCompanyId, nextState });
                }}
              >
                <option value="">{selectedCompany ? tx(OPP_LABEL[selectedCompany.opportunity.state]) : tx("dev.col-opportunity")}</option>
                {(selectedCompany ? OPP_NEXT[selectedCompany.opportunity.state] : []).map((state) => (
                  <option key={state} value={state}>
                    {tx(OPP_LABEL[state])}
                  </option>
                ))}
              </select>
            </div>
          </section>
          <GovernanceRail
            t={tx}
            dash={dash}
            disabled={disabled}
            onDrawer={() => setDrawerOpen(true)}
            connector={dash}
            blocker={dash}
          />
        </div>
      ) : null}

      {stage === 3 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-05">
            <div data-component-uid="DEV-01-CMP-MESSAGE">
            <h2>{tx("dev.message-title")}</h2>
            <p className={styles.note}>{tx("dev.message-hint")}</p>
            <div className={styles.card}>
              <h3>{tx("dev.audience-context")}</h3>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-company")}</span>
                  <strong>{selectedCompany?.name || dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-opportunity")}</span>
                  <strong>{selectedCompany ? tx(OPP_LABEL[selectedCompany.opportunity.state]) : dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-contact")}</span>
                  <strong>{selectedCompany?.contacts.find((item) => item.type === "EMAIL")?.value || dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-version")}</span>
                  <strong>{selectedCandidate ? String(selectedCandidate.version) : dash}</strong>
                </div>
              </div>
            </div>
            <div className={styles.table}>
              <div className={`${styles.thead} ${styles.msgHead}`}>
                <span className={styles.check}>
                  <input
                    type="checkbox"
                    aria-label={tx("dev.col-select-all")}
                    checked={
                      workbench.candidates.length > 0 &&
                      workbench.candidates.every((candidate) => selectedCandidateIds.includes(candidate.candidateId))
                    }
                    disabled={disabled || !workbench.candidates.length}
                    onChange={() => {
                      const allSelected = workbench.candidates.every((candidate) =>
                        selectedCandidateIds.includes(candidate.candidateId),
                      );
                      setSelectedCandidateIds(
                        allSelected ? [] : workbench.candidates.map((candidate) => candidate.candidateId),
                      );
                    }}
                  />
                  {tx("dev.col-candidate")}
                </span>
                <span>{tx("dev.col-personalization")}</span>
                <span>{tx("dev.col-policy")}</span>
                <span>{tx("dev.col-review")}</span>
                <span>{tx("dev.col-version")}</span>
                <span>{tx("dev.col-action")}</span>
              </div>
              {workbench.candidates.length ? (
                workbench.candidates.map((candidate: DevCandidate) => (
                  <div
                    className={`${styles.trow} ${styles.msgRow} ${selectedCandidate?.candidateId === candidate.candidateId ? styles.trowSelected : ""}`}
                    key={candidate.candidateId}
                    onClick={() => setSelectedCandidateId(candidate.candidateId)}
                  >
                    <span className={styles.check}>
                      <input
                        type="checkbox"
                        checked={selectedCandidateIds.includes(candidate.candidateId)}
                        disabled={disabled}
                        onChange={(event) => {
                          event.stopPropagation();
                          setSelectedCandidateIds((current) =>
                            current.includes(candidate.candidateId)
                              ? current.filter((id) => id !== candidate.candidateId)
                              : [...current, candidate.candidateId],
                          );
                        }}
                      />
                      <span className={styles.checkText} title={candidate.companyName}>
                        {candidate.companyName}
                      </span>
                    </span>
                    <span>{candidate.personalization}</span>
                    <span>{candidate.policy === "PASS" ? tx("dev.policy-pass") : tx("dev.policy-blocked")}</span>
                    <span>{tx(CANDIDATE_LABEL[candidate.status])}</span>
                    <span>
                      {`v${candidate.version}`}
                      {candidate.history.length > 1 ? ` · ${candidate.history.map((entry) => `v${entry.version}${entry.at ? ` ${entry.at.slice(0, 10)}` : ""}`).join(" / ")}` : ""}
                    </span>
                    <span className={styles.rowAct}>{selectedCandidate?.candidateId === candidate.candidateId ? tx("dev.row-open") : tx(CANDIDATE_LABEL[candidate.status])}</span>
                  </div>
                ))
              ) : (
                <p className={styles.empty}>{loading ? dash : tx("dev.empty-candidates")}</p>
              )}
            </div>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.btn}
                disabled={disabled || !selectedCandidateIds.length}
                onClick={() => void act("DEV-01-BTN-CANDIDATE-DELETE", { candidateIds: selectedCandidateIds })}
              >
                {tx("dev.btn-candidate-delete", { n: selectedCandidateIds.length })}
              </button>
              <span className={styles.note}>{tx("dev.candidate-delete-hint")}</span>
            </div>
            {selectedCompany && !selectedHasEmail ? <p className={styles.note}>{tx("dev.contact-missing-email")}</p> : null}
            <div className={styles.fields}>
              <label className={styles.field}>
                <span className={styles.fieldHead}>
                  {tx("dev.cand-subject")}
                  <em className={styles.charCount}>{tx("dev.char-count", { n: candSubject.length })}</em>
                </span>
                <input
                  className={styles.fieldInput}
                  value={candSubject}
                  disabled={disabled}
                  onChange={(event) => setCandSubject(event.target.value)}
                  placeholder={tx("dev.cand-subject")}
                />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldHead}>
                  {tx("dev.cand-body")}
                  <em className={styles.charCount}>{tx("dev.char-count", { n: candBody.length })}</em>
                </span>
                <textarea
                  className={`${styles.fieldInput} ${styles.fieldArea}`}
                  value={candBody}
                  disabled={disabled}
                  rows={10}
                  onChange={(event) => setCandBody(event.target.value)}
                  placeholder={tx("dev.cand-body")}
                />
              </label>
            </div>
            {selectedCandidate ? (
              <div className={styles.card}>
                <h3>{tx("dev.cand-view")}</h3>
                <p className={styles.note}>{selectedCandidate.subject}</p>
                <p className={styles.note} style={{ whiteSpace: "pre-wrap" }}>{selectedCandidate.body}</p>
              </div>
            ) : null}
            </div>
            <div data-component-uid="DEV-01-CMP-MESSAGE-REVIEW" />
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} connector={dash} blocker={dash} />
        </div>
      ) : null}

      {stage === 4 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-06">
            <div data-component-uid="DEV-01-CMP-CAMPAIGN">
            <h2>{tx("dev.campaign-stage")}</h2>
            <div className={styles.card}>
              <h3>{tx("dev.audience-filter")}</h3>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span>{tx("dev.filter-company")}</span>
                  <strong>{audienceQuery || dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.filter-contact")}</span>
                  <strong>{String(audiencePreview.length)}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.filter-suppression")}</span>
                  <strong>{tx("dev.filter-suppression-value")}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.filter-message")}</span>
                  <strong>{approvedCandidate ? `${approvedCandidate.candidateId} v${approvedCandidate.version}` : tx("dev.filter-message-value")}</strong>
                </div>
              </div>
            </div>
            <div className={styles.toolbar}>
              <input
                className={styles.search}
                placeholder={tx("dev.search-audience")}
                value={audienceQuery}
                disabled={disabled}
                onChange={(event) => setAudienceQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void act("DEV-01-BTN-CAMPAIGN-SEARCH", { audienceQuery });
                }}
              />
              {audienceQuery ? (
                <button
                  type="button"
                  className={styles.btn}
                  disabled={disabled}
                  onClick={() => {
                    setAudienceQuery("");
                    void act("DEV-01-BTN-CAMPAIGN-SEARCH", { audienceQuery: "" });
                  }}
                >
                  {tx("dev.btn-clear-search")}
                </button>
              ) : null}
            </div>
            <div className={styles.card}>
              <h3>
                {tx("dev.recipient-title")}
                <span className={styles.countBadge}>
                  {tx("dev.recipient-count", { n: campaign?.recipients.length || audiencePreview.length })}
                </span>
              </h3>
              <div className={styles.table}>
                <div className={`${styles.thead} ${styles.rcpHead}`}>
                  <span>{tx("dev.col-company")}</span>
                  <span>{tx("dev.col-contact")}</span>
                  <span>{tx("dev.col-suppression")}</span>
                  <span>{tx("dev.col-policy")}</span>
                  <span>{tx("dev.col-message")}</span>
                  <span>{tx("dev.col-result")}</span>
                </div>
                <div className={styles.listScroll}>
                {(campaign?.recipients.length ? campaign.recipients : audiencePreview.map(({ company, contact }) => ({
                  recipientId: company.companyId,
                  companyName: company.name,
                  contactValue: contact.value,
                  suppression: company.suppression,
                  messageVersion: approvedCandidate?.version ?? 0,
                  previewed: false,
                }))).length ? (
                  (campaign?.recipients.length ? campaign.recipients.map((recipient) => (
                    <div className={`${styles.trow} ${styles.rcpRow}`} key={recipient.recipientId}>
                      <span>{recipient.companyName}</span>
                      <span>{recipient.contactValue}</span>
                      <span>{recipient.suppression || dash}</span>
                      <span>{recipient.suppression ? tx("dev.policy-blocked") : tx("dev.policy-pass")}</span>
                      <span>{`v${recipient.messageVersion}`}</span>
                      <span>{campaign.previewed ? tx("dev.preview-ready") : dash}</span>
                    </div>
                  )) : audiencePreview.map(({ company, contact }) => (
                    <div className={`${styles.trow} ${styles.rcpRow}`} key={`${company.companyId}-${contact.contactId}`}>
                      <span>{company.name}</span>
                      <span>{contact.value}</span>
                      <span>{dash}</span>
                      <span>{tx("dev.policy-pass")}</span>
                      <span>{approvedCandidate ? `v${approvedCandidate.version}` : dash}</span>
                      <span>{dash}</span>
                    </div>
                  )))
                ) : (
                  <p className={styles.empty}>{loading ? dash : tx("dev.empty-recipients")}</p>
                )}
                </div>
              </div>
            </div>
            </div>
            <div data-component-uid="DEV-01-CMP-CAMPAIGN-REVIEW">
            <div className={styles.card}>
              <h3>{tx("dev.approval-title")}</h3>
              <p className={styles.note}>{campaign ? tx(CAMPAIGN_LABEL[campaign.status]) : tx("dev.approval-hint")}</p>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span>{tx("dev.letter-preview")}</span>
                  <strong>{campaignCandidate?.subject || approvedCandidate?.subject || dash}</strong>
                </div>
              </div>
              <p className={styles.note}>{campaignCandidate?.body || approvedCandidate?.body || tx("dev.empty-recipients")}</p>
              <p className={styles.note}>{`${tx("dev.col-personalization")}: ${campaignCandidate?.personalization || approvedCandidate?.personalization || dash}`}</p>
            </div>
            </div>
          </section>
          <GovernanceRail t={tx} dash={dash} disabled={disabled} onDrawer={() => setDrawerOpen(true)} connector={dash} blocker={dash} />
        </div>
      ) : null}

      {stage === 5 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="DEV-01-SEC-07">
            <div data-component-uid="DEV-01-CMP-DELIVERY">
            <h2>{tx("dev.delivery-stage")}</h2>
            <div className={styles.card}>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span>{tx("dev.delivery-campaign")}</span>
                  <strong>{campaign ? tx(CAMPAIGN_LABEL[campaign.status]) : tx("dev.delivery-campaign-value")}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.delivery-policy")}</span>
                  <strong title={tx("dev.delivery-policy-value")}>{tx("dev.delivery-policy-value")}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.delivery-envelope")}</span>
                  <strong>{deliveries.length ? tx("dev.delivery-envelope-count", { n: deliveries.length }) : tx("dev.delivery-envelope-value")}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.col-suppression")}</span>
                  <strong>{campaign?.recipients.some((item) => item.suppression) ? tx("dev.policy-blocked") : tx("dev.delivery-suppression-value")}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.delivery-idempotency")}</span>
                  <strong>{deliveries.length ? tx("dev.delivery-idempotency-count", { n: deliveries.length }) : tx("dev.required")}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.delivery-audit")}</span>
                  <strong>{deliveries.length ? tx(DELIVERY_LABEL[deliveries[0].status]) : tx("dev.required")}</strong>
                </div>
              </div>
            </div>
            {deliveries.some((item) => item.status === "EXTERNAL_PENDING") ? (
              <p className={styles.note}>{tx("dev.blocker-delivery")}</p>
            ) : null}
            <div className={styles.card}>
              <h3>{tx("dev.letter-preview")}</h3>
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span>{tx("dev.cand-subject")}</span>
                  <strong>{campaignCandidate?.subject || dash}</strong>
                </div>
                <div className={styles.metaItem}>
                  <span>{tx("dev.delivery-mix")}</span>
                  <strong>{`${tx(DELIVERY_LABEL.QUEUED)} ${deliveries.filter((item) => item.status === "QUEUED").length} · ${tx(DELIVERY_LABEL.EXTERNAL_PENDING)} ${deliveries.filter((item) => item.status === "EXTERNAL_PENDING").length} · ${tx(DELIVERY_LABEL.STOPPED)} ${deliveries.filter((item) => item.status === "STOPPED").length}`}</strong>
                </div>
              </div>
              <p className={styles.note}>{campaignCandidate?.body || tx("dev.empty-recipients")}</p>
              <p className={styles.note}>{`${tx("dev.col-personalization")}: ${campaignCandidate?.personalization || dash}`}</p>
            </div>
            <div className={styles.card}>
              <h3>{tx("dev.recipient-result-title")}</h3>
              {campaign?.recipients.length ? (
                <div className={styles.table}>
                  <div className={`${styles.thead} ${styles.dlvHead}`}>
                    <span className={styles.check}>
                      <input
                        type="checkbox"
                        aria-label={tx("dev.col-select-all")}
                        checked={campaign.recipients.every((recipient) => selectedRecipientIds.includes(recipient.recipientId))}
                        disabled={disabled}
                        onChange={() => {
                          const allSelected = campaign.recipients.every((recipient) => selectedRecipientIds.includes(recipient.recipientId));
                          setSelectedRecipientIds(allSelected ? [] : campaign.recipients.map((recipient) => recipient.recipientId));
                        }}
                      />
                      {tx("dev.col-recipient")}
                    </span>
                    <span>{tx("dev.col-contact")}</span>
                    <span>{tx("dev.col-result")}</span>
                    <span>{tx("dev.col-sent-at")}</span>
                    <span>{tx("dev.col-action")}</span>
                  </div>
                  {campaign.recipients.map((recipient) => {
                    const history = deliveries.filter((item) => item.recipientId === recipient.recipientId);
                    const latest = history.reduce<DevDelivery | null>((acc, item) => (!acc || item.version > acc.version ? item : acc), null);
                    const resendable = !latest || latest.status === "STOPPED" || latest.status === "FAILED";
                    return (
                      <div className={`${styles.trow} ${styles.dlvRow}`} key={recipient.recipientId}>
                        <span className={styles.check}>
                          <input
                            type="checkbox"
                            checked={selectedRecipientIds.includes(recipient.recipientId)}
                            disabled={disabled}
                            onChange={() =>
                              setSelectedRecipientIds((current) =>
                                current.includes(recipient.recipientId)
                                  ? current.filter((id) => id !== recipient.recipientId)
                                  : [...current, recipient.recipientId],
                              )
                            }
                          />
                          <span className={styles.checkText} title={recipient.companyName}>
                            {recipient.companyName}
                          </span>
                        </span>
                        <span title={recipient.contactValue}>{recipient.contactValue}</span>
                        <span>
                          {latest ? tx(DELIVERY_LABEL[latest.status]) : tx("dev.delivery-not-sent")}
                          {history.length > 1 ? ` · ×${history.length}` : ""}
                        </span>
                        <span>{latest?.sentAt ? latest.sentAt.slice(0, 19).replace("T", " ") : dash}</span>
                        <span className={styles.rowAct}>
                          {resendable ? (
                            <button
                              type="button"
                              className={styles.linkBtn}
                              disabled={disabled}
                              onClick={() => void act("DEV-01-BTN-DELIVERY-SEND", { recipientIds: [recipient.recipientId] })}
                            >
                              {latest ? tx("dev.row-resend") : tx("dev.row-send")}
                            </button>
                          ) : (
                            dash
                          )}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className={styles.empty}>{tx("dev.empty-recipients")}</p>
              )}
              {selectedRecipientIds.length ? (
                <div className={styles.actions}>
                  <button
                    type="button"
                    className={styles.btn}
                    disabled={disabled || campaign?.status === "REVIEW"}
                    title={campaign?.status === "REVIEW" ? tx("dev.need-approved-campaign") : undefined}
                    onClick={() => void act("DEV-01-BTN-DELIVERY-SEND", { recipientIds: selectedRecipientIds })}
                  >
                    {tx("dev.btn-delivery-send", { n: selectedRecipientIds.length })}
                  </button>
                  {(() => {
                    const ackIds = deliveries
                      .filter((item) => selectedRecipientIds.includes(item.recipientId) && item.status === "EXTERNAL_PENDING")
                      .map((item) => item.deliveryId);
                    return (
                      <>
                        <button
                          type="button"
                          className={styles.btn}
                          disabled={disabled || !ackIds.length}
                          onClick={() => void act("DEV-01-BTN-DELIVERY-ACK", { deliveryIds: ackIds, result: "SENT" })}
                        >
                          {tx("dev.btn-delivery-ack-sent", { n: ackIds.length })}
                        </button>
                        <button
                          type="button"
                          className={styles.btn}
                          disabled={disabled || !ackIds.length}
                          onClick={() => void act("DEV-01-BTN-DELIVERY-ACK", { deliveryIds: ackIds, result: "FAILED" })}
                        >
                          {tx("dev.btn-delivery-ack-failed", { n: ackIds.length })}
                        </button>
                      </>
                    );
                  })()}
                </div>
              ) : null}
            </div>
            </div>
            <div data-component-uid="DEV-01-CMP-KILL-SWITCH">
              <div className={styles.card}>
                <h3>{tx("dev.btn-kill")}</h3>
                <p className={styles.note}>{tx("dev.kill-note")}</p>
              </div>
            </div>
          </section>
          <GovernanceRail
            t={tx}
            dash={dash}
            disabled={disabled}
            onDrawer={() => setDrawerOpen(true)}
            connector={dash}
            blocker={deliveries.some((item) => item.status === "EXTERNAL_PENDING") ? tx("dev.blocker-delivery") : dash}
          />
        </div>
      ) : null}

      <div
        className={styles.dock}
        data-section-uid="DEV-01-SEC-03"
        data-component-uid="DEV-01-CMP-DISCOVERY-ACTION"
        data-visual-uid="DEV-01-VIS-ACTION-DOCK"
      >
        {stage === 1 ? (
          <>
            <Btn
              uid="DEV-01-BTN-DISCOVERY-START"
              label={tx("dev.btn-start")}
              onAct={(uid) => void act(uid)}
              disabled={disabled || jobStatus === "RUNNING" || jobStatus === "EXTERNAL_PENDING"}
              primary={jobStatus !== "RUNNING" && jobStatus !== "EXTERNAL_PENDING"}
              title={workbench.profile && !profileIsReady(workbench.profile) ? tx("dev.need-profile") : undefined}
            />
            <Btn
              uid="DEV-01-BTN-DISCOVERY-PAUSE"
              label={tx("dev.btn-pause")}
              onAct={(uid) => void act(uid)}
              disabled={disabled || jobStatus !== "RUNNING"}
            />
            <Btn
              uid="DEV-01-BTN-DISCOVERY-RESUME"
              label={tx("dev.btn-resume")}
              onAct={(uid) => void act(uid)}
              disabled={disabled || jobStatus !== "PAUSED"}
            />
            <Btn
              uid="DEV-01-BTN-DISCOVERY-STOP"
              label={tx("dev.btn-stop")}
              onAct={(uid) => void act(uid)}
              disabled={disabled || (jobStatus !== "RUNNING" && jobStatus !== "EXTERNAL_PENDING")}
              danger
            />
          </>
        ) : null}
        {stage === 2 ? (
          <>
            <Btn uid="DEV-01-BTN-DIRECTORY-SEARCH" label={tx("dev.btn-search")} onAct={() => void act("DEV-01-BTN-DIRECTORY-SEARCH", { query })} disabled={disabled} primary />
            <Btn
              uid="DEV-01-BTN-MERGE-PREVIEW"
              label={tx("dev.btn-merge-preview")}
              onAct={() => void act("DEV-01-BTN-MERGE-PREVIEW", { companyIds: selectedCompanyIds })}
              disabled={disabled}
            />
            <Btn uid="DEV-01-BTN-MERGE" label={tx("dev.btn-merge")} onAct={(uid) => void act(uid)} disabled={disabled || !workbench.merge} />
            <Btn
              uid="DEV-01-BTN-EXPORT"
              label={tx("dev.btn-export")}
              onAct={(uid) => {
                void act(uid);
                downloadDevCsv(searchDirectoryProjection(workbench.companies, workbench.query));
              }}
              disabled={disabled}
            />
          </>
        ) : null}
        {stage === 3 ? (
          <>
            <Btn
              uid="DEV-01-BTN-CANDIDATE-CREATE"
              label={tx("dev.btn-candidate-create")}
              onAct={() =>
                void act("DEV-01-BTN-CANDIDATE-CREATE", {
                  companyId: selectedCompanyId,
                  subject: candSubject,
                  body: candBody,
                })
              }
              disabled={disabled || !selectedCanMessage || !candSubject || !candBody}
              primary
            />
            <Btn
              uid="DEV-01-BTN-CANDIDATE-DECIDE"
              label={tx("dev.btn-candidate-decide")}
              onAct={() => void act("DEV-01-BTN-CANDIDATE-DECIDE", { candidateId: selectedCandidate?.candidateId })}
              disabled={disabled || selectedCandidate?.status !== "REVIEW"}
            />
            <Btn
              uid="DEV-01-BTN-CR-CREATE"
              label={tx("dev.btn-cr")}
              onAct={() => void act("DEV-01-BTN-CR-CREATE", { candidateId: selectedCandidate?.candidateId })}
              disabled={disabled || selectedCandidate?.status !== "REVIEW"}
            />
          </>
        ) : null}
        {stage === 4 ? (
          <>
            <Btn
              uid="DEV-01-BTN-CAMPAIGN-SEARCH"
              label={tx("dev.btn-audience-search")}
              onAct={() => void act("DEV-01-BTN-CAMPAIGN-SEARCH", { audienceQuery })}
              disabled={disabled}
              primary={campaign?.status === "REVIEW" && campaign?.previewed === false}
              title={campaign?.status === "REVIEW" && campaign?.previewed === false ? tx("dev.need-audience-search") : undefined}
            />
            <Btn
              uid="DEV-01-BTN-CAMPAIGN-CREATE"
              label={tx("dev.btn-campaign-create")}
              onAct={() => void act("DEV-01-BTN-CAMPAIGN-CREATE", { candidateId: approvedCandidate?.candidateId })}
              disabled={disabled || !approvedCandidate}
              primary={!campaign || campaign.status !== "REVIEW"}
              title={!approvedCandidate ? tx("dev.need-approved-candidate") : undefined}
            />
            <Btn
              uid="DEV-01-BTN-CAMPAIGN-APPROVE"
              label={tx("dev.btn-campaign-approve")}
              onAct={(uid) => void act(uid)}
              disabled={disabled || campaign?.status !== "REVIEW" || campaign?.previewed === false}
              primary={campaign?.status === "REVIEW" && campaign?.previewed !== false}
              title={campaign?.previewed === false ? tx("dev.need-audience-search") : undefined}
            />
            <Btn
              uid="DEV-01-BTN-CAMPAIGN-DELETE"
              label={tx("dev.btn-campaign-delete")}
              onAct={(uid) => {
                if (!window.confirm(tx("dev.campaign-delete-confirm"))) return;
                void act(uid);
              }}
              disabled={disabled || !campaign || campaign.status === "APPROVED"}
              title={campaign?.status === "APPROVED" ? tx("dev.campaign-locked-hint") : undefined}
            />
          </>
        ) : null}
        {stage === 5 ? (
          <>
            <Btn
              uid="DEV-01-BTN-EMAIL-DISPATCH"
              label={tx("dev.btn-dispatch")}
              onAct={() => {
                const count = campaign?.recipients.length ?? 0;
                if (!window.confirm(tx("dev.dispatch-confirm", { n: count }))) return;
                void act("DEV-01-BTN-EMAIL-DISPATCH");
              }}
              disabled={disabled || campaign?.status !== "APPROVED"}
              primary={campaign?.status === "APPROVED"}
              title={campaign?.status !== "APPROVED" ? tx("dev.need-approved-campaign") : undefined}
            />
            <Btn uid="DEV-01-BTN-REFRESH" label={tx("dev.btn-refresh")} onAct={(uid) => void act(uid)} disabled={disabled} />
            <Btn
              uid="DEV-01-BTN-KILL-SWITCH"
              label={tx("dev.btn-kill")}
              onAct={() => {
                if (!window.confirm(tx("dev.kill-confirm"))) return;
                const reason = window.prompt(tx("dev.kill-reason-prompt"), "OPERATOR_STOP");
                if (!reason || !reason.trim()) return;
                void act("DEV-01-BTN-KILL-SWITCH", { reason: reason.trim() });
              }}
              disabled={disabled || (campaign?.status !== "QUEUED" && campaign?.status !== "APPROVED")}
              danger
            />
          </>
        ) : null}
      </div>

      <aside
        className={styles.drawer}
        data-section-uid="DEV-01-SEC-09"
        data-component-uid="DEV-01-CMP-DETAIL-DRAWER"
        hidden={!drawerOpen}
        aria-label={tx("dev.drawer-title")}
      >
        <div className={styles.drawerHead}>
          <h3>{tx("dev.drawer-title")}</h3>
          <button type="button" className={styles.btn} onClick={() => setDrawerOpen(false)}>
            {tx("global.common.close")}
          </button>
        </div>
        <p className={styles.note}>{tx("dev.drawer-hint")}</p>
        <div className={styles.metaGrid}>
          <div className={styles.metaItem}>
            <span>{tx("dev.col-evidence")}</span>
            <strong>{workbench.profile?.product || dash}</strong>
          </div>
          <div className={styles.metaItem}>
            <span>{tx("dev.col-version")}</span>
            <strong>{workbench.profile ? String(workbench.profile.version) : dash}</strong>
          </div>
        </div>
        {workbench.merge ? (
          <>
            <h4>{tx("dev.merge-detail")}</h4>
            <div className={styles.metaGrid}>
              <div className={styles.metaItem}>
                <span>{tx("dev.merge-survivor")}</span>
                <strong>{workbench.merge.survivorId}</strong>
              </div>
              <div className={styles.metaItem}>
                <span>{tx("dev.merge-merged")}</span>
                <strong>{workbench.merge.mergedIds.join(", ") || dash}</strong>
              </div>
              <div className={styles.metaItem}>
                <span>{tx("dev.merge-conflicts")}</span>
                <strong>{workbench.merge.conflicts.join(", ") || dash}</strong>
              </div>
            </div>
          </>
        ) : null}
        <h4>{tx("dev.delivery-history")}</h4>
        {deliveries.length ? (
          <div className={styles.table}>
            <div className={`${styles.thead} ${styles.histHead}`}>
              <span>{tx("dev.col-contact")}</span>
              <span>{tx("dev.col-result")}</span>
              <span>{tx("dev.col-sent-at")}</span>
              <span>{tx("dev.delivery-idempotency")}</span>
            </div>
            {deliveries.map((delivery) => (
              <div className={`${styles.trow} ${styles.histRow}`} key={delivery.deliveryId}>
                <span>{delivery.to}</span>
                <span>{tx(DELIVERY_LABEL[delivery.status])}</span>
                <span>{delivery.sentAt ? delivery.sentAt.slice(0, 19).replace("T", " ") : dash}</span>
                <span>{delivery.idempotencyKey}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className={styles.empty}>{tx("dev.empty-deliveries")}</p>
        )}
      </aside>

      {stage === 1 ? null : (
        <>
          <div data-component-uid="DEV-01-CMP-DISCOVERY-SETUP" hidden />
          <div data-component-uid="DEV-01-CMP-DISCOVERY-RUNTIME" hidden />
        </>
      )}
      {stage === 2 ? null : (
        <>
          <div data-component-uid="DEV-01-CMP-DIRECTORY" hidden />
          <div data-component-uid="DEV-01-CMP-MERGE" hidden />
        </>
      )}
      {stage === 3 ? null : (
        <>
          <div data-component-uid="DEV-01-CMP-MESSAGE" hidden />
          <div data-component-uid="DEV-01-CMP-MESSAGE-REVIEW" hidden />
        </>
      )}
      {stage === 4 ? null : (
        <>
          <div data-component-uid="DEV-01-CMP-CAMPAIGN" hidden />
          <div data-component-uid="DEV-01-CMP-CAMPAIGN-REVIEW" hidden />
        </>
      )}
      {stage === 5 ? null : (
        <>
          <div data-component-uid="DEV-01-CMP-DELIVERY" hidden />
          <div data-component-uid="DEV-01-CMP-KILL-SWITCH" hidden />
        </>
      )}
    </div>
  );
}

function GovernanceRail({
  t,
  dash,
  disabled,
  onDrawer,
  connector,
  blocker,
}: {
  t: (key: TranslationKey) => string;
  dash: string;
  disabled: boolean;
  onDrawer: () => void;
  connector: string;
  blocker: string;
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
        <strong>{connector}</strong>
      </div>
      <div className={styles.railCard}>
        <span>{t("dev.rail-suppression")}</span>
        <strong>{t("dev.rail-suppression-value")}</strong>
      </div>
      <div className={styles.railCard}>
        <span>{t("dev.rail-blockers")}</span>
        <strong>{blocker}</strong>
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
