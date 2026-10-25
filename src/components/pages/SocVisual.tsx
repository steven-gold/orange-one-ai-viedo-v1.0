"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { SocClientError, fetchSocReadModel, postSocAction, type SocFieldValue } from "@/lib/client";
import {
  boundAccountForPlatform,
  filterRequests,
  filterTargets,
  highRiskActive,
  packageApproved,
  targetReadyToPost,
  type SocAccount,
  type SocAccountBinding,
  type SocCandidateState,
  type SocCredentialStatus,
  type SocDiscoveryMode,
  type SocDiscoveryStatus,
  type SocEnableState,
  type SocPlatform,
  type SocRequestStatus,
  type SocTarget,
  type SocTargetStatus,
  workbenchFromFields,
} from "@/lib/socState";
import { displaySocValue } from "./socFormat";
import { SOC_CONTROL_ACTIONS, SOC_STAGES, SOC_VISIBLE_CONTROLS, type SocStage } from "./socControls";
import styles from "./SocVisual.module.css";

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

const ENABLE_LABEL: Record<SocEnableState, TranslationKey> = {
  ENABLED: "soc.enable-enabled",
  DISABLED: "soc.enable-disabled",
};

const BINDING_LABEL: Record<SocAccountBinding, TranslationKey> = {
  UNBOUND: "soc.binding-unbound",
  CONFIGURED: "soc.binding-configured",
  BOUND_LOCKED: "soc.binding-locked",
  REAUTH_REQUIRED: "soc.binding-reauth",
};

const CREDENTIAL_LABEL: Record<SocCredentialStatus, TranslationKey> = {
  NOT_SET: "soc.credential-unset",
  SET: "soc.credential-set",
  REAUTH_REQUIRED: "soc.credential-reauth",
};

const DISCOVERY_LABEL: Record<SocDiscoveryStatus, TranslationKey> = {
  RUNNING: "soc.discovery-running",
  EXTERNAL_PENDING: "soc.discovery-pending",
  STOPPED: "soc.discovery-stopped",
};

const TARGET_LABEL: Record<SocTargetStatus, TranslationKey> = {
  DISCOVERED: "soc.target-discovered",
  READY_TO_JOIN: "soc.target-ready-join",
  MANUAL_ACTION_REQUIRED: "soc.target-manual",
  PENDING_ADMIN_APPROVAL: "soc.target-admin",
  JOINED: "soc.target-joined",
  READY_TO_POST: "soc.target-ready-post",
  PENDING_EXTERNAL: "soc.target-pending",
  POSTED: "soc.target-posted",
  COOLDOWN: "soc.target-cooldown",
  UNAVAILABLE: "soc.target-unavailable",
};

const CANDIDATE_LABEL: Record<SocCandidateState, TranslationKey> = {
  DRAFT: "soc.candidate-draft",
  REVIEW: "soc.candidate-review",
  APPROVED: "soc.candidate-approved",
  REJECTED: "soc.candidate-rejected",
  RETURN: "soc.candidate-return",
};

const REQUEST_LABEL: Record<SocRequestStatus, TranslationKey> = {
  PENDING_EXTERNAL: "soc.request-pending",
  STOPPED: "soc.request-stopped",
};

function errorKey(code: string | null | undefined): TranslationKey | null {
  if (!code) return null;
  return `soc.err.${code}` as TranslationKey;
}

export function SocVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<SocFieldValue[]>([]);
  const [stage, setStage] = useState<SocStage>(2);
  const [query, setQuery] = useState("");
  const [recordQuery, setRecordQuery] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [selectedPlatformKey, setSelectedPlatformKey] = useState("");
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [selectedTargetId, setSelectedTargetId] = useState("");
  const [selectedRequestId, setSelectedRequestId] = useState("");
  const [platformKey, setPlatformKey] = useState("");
  const [platformName, setPlatformName] = useState("");
  const [platformEnable, setPlatformEnable] = useState<SocEnableState>("ENABLED");
  const [displayName, setDisplayName] = useState("");
  const [loginIdentifier, setLoginIdentifier] = useState("");
  const [authMode, setAuthMode] = useState("TOKEN");
  const [credentialValue, setCredentialValue] = useState("");
  const [jobName, setJobName] = useState("");
  const [targetTypes, setTargetTypes] = useState("");
  const [categories, setCategories] = useState("");
  const [keywords, setKeywords] = useState("");
  const [mode, setMode] = useState<SocDiscoveryMode>("SINGLE_RUN");
  const [releaseSource, setReleaseSource] = useState("");
  const [variant, setVariant] = useState("");
  const [decision, setDecision] = useState<"APPROVE" | "REJECT" | "RETURN">("APPROVE");
  const [minIntervalHours, setMinIntervalHours] = useState("24");
  const [dailyLimit, setDailyLimit] = useState("1");
  const [weeklyLimit, setWeeklyLimit] = useState("3");
  const [revealReason, setRevealReason] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
    fetchSocReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        const nextFields = model.fields.length ? model.fields : SOC_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null }));
        setFields(nextFields);
        const workbench = workbenchFromFields(nextFields);
        if (workbench.query) setQuery(workbench.query);
        if (workbench.recordQuery) setRecordQuery(workbench.recordQuery);
        if (workbench.discovery) {
          setJobName(workbench.discovery.jobName);
          setTargetTypes(workbench.discovery.targetTypes);
          setCategories(workbench.discovery.categories);
          setKeywords(workbench.discovery.keywords);
          setMode(workbench.discovery.mode);
          setPlatformKey((current) => current || workbench.discovery?.platformKey || "");
        }
        if (workbench.content) {
          setReleaseSource(workbench.content.releaseSource);
          setVariant(workbench.content.variant);
          setPlatformKey((current) => current || workbench.content?.platformKey || "");
        }
        if (workbench.policy) {
          setMinIntervalHours(String(workbench.policy.minIntervalHours));
          setDailyLimit(String(workbench.policy.dailyLimit));
          setWeeklyLimit(String(workbench.policy.weeklyLimit));
        }
        setCredentialValue("");
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
  }, [tick]);

  const act = useCallback(async (controlUid: string, payload?: Record<string, unknown>) => {
    const actionUid = SOC_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    setBusy(true);
    try {
      await postSocAction(
        DEFAULT_ACCOUNT,
        controlUid,
        actionUid,
        DEFAULT_SESSION,
        payload ? JSON.stringify(payload) : undefined,
      );
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
    setBusy(false);
    setTick((n) => n + 1);
  }, []);

  const disabled = (!authorized && !loading) || busy;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey, params?: Record<string, string | number>) => t(key, params);
  const dash = displaySocValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(SOC_VISIBLE_CONTROLS), []);
  const chainView = stage === 4 || stage === 5;
  const workbench = useMemo(() => workbenchFromFields(fields), [fields]);
  const actionError = errorKey(workbench.error?.code);
  const platforms = workbench.platforms;
  const selectedPlatform =
    platforms.find((item) => item.platformKey === selectedPlatformKey) ?? platforms[0] ?? null;
  const accounts = workbench.accounts;
  const selectedAccount =
    accounts.find((item) => item.accountId === selectedAccountId) ??
    (selectedPlatform ? boundAccountForPlatform(accounts, selectedPlatform.platformKey) : null) ??
    accounts[0] ??
    null;
  const targets = filterTargets(workbench.targets, query);
  const selectedTarget =
    workbench.targets.find((item) => item.targetId === selectedTargetId) ?? targets[0] ?? null;
  const requests = filterRequests(workbench.requests, recordQuery);
  const selectedRequest =
    workbench.requests.find((item) => item.requestId === selectedRequestId) ?? requests[requests.length - 1] ?? null;
  const content = workbench.content;
  const policy = workbench.policy;
  const discovery = workbench.discovery;
  const killOn = Boolean(workbench.kill?.active);
  const risky = highRiskActive(workbench);
  const boundAccount = selectedTarget ? boundAccountForPlatform(accounts, selectedTarget.platformKey) : selectedAccount;
  const publishAccount = boundAccount;
  const canJoin = selectedTarget?.status === "DISCOVERED" || selectedTarget?.status === "READY_TO_JOIN";
  const canManual = selectedTarget?.status === "MANUAL_ACTION_REQUIRED";
  const canPublish =
    targetReadyToPost(selectedTarget) &&
    packageApproved(content) &&
    Boolean(publishAccount) &&
    policy?.targetId === selectedTarget?.targetId &&
    !killOn;
  const activePlatformKey = platformKey || selectedPlatform?.platformKey || selectedTarget?.platformKey || content?.platformKey || "";

  const selectStage = (next: SocStage, uid: string) => {
    setStage(next);
    void act(uid);
  };

  const lineageAccount = selectedAccount?.accountId || dash;
  const lineageTarget = selectedTarget?.targetId || dash;
  const lineageVersion = selectedTarget ? String(selectedTarget.version) : content ? String(content.version) : dash;
  const lineageCorrelation = selectedRequest?.idempotencyKey || discovery?.jobId || dash;

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
      {actionError ? (
        <div className={styles.error} role="alert">
          {tx(actionError)}
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
            <div className={styles.fields}>
              <label className={styles.field}>
                <span>{tx("soc.field-platform")}</span>
                <input className={styles.fieldInput} value={platformKey} disabled={disabled} onChange={(event) => setPlatformKey(event.target.value)} />
              </label>
              <label className={styles.field}>
                <span>{tx("soc.field-display-name")}</span>
                <input className={styles.fieldInput} value={platformName} disabled={disabled} onChange={(event) => setPlatformName(event.target.value)} />
              </label>
              <label className={styles.field}>
                <span>{tx("soc.field-enable")}</span>
                <select
                  className={styles.fieldSelect}
                  value={platformEnable}
                  disabled={disabled}
                  onChange={(event) => setPlatformEnable(event.target.value as SocEnableState)}
                >
                  <option value="ENABLED">{tx("soc.enable-enabled")}</option>
                  <option value="DISABLED">{tx("soc.enable-disabled")}</option>
                </select>
              </label>
            </div>
            <div className={styles.table}>
              <div className={`${styles.thead} ${styles.platHead}`}>
                <span>{tx("soc.col-platform")}</span>
                <span>{tx("soc.col-capability")}</span>
                <span>{tx("soc.col-policy")}</span>
                <span>{tx("soc.col-health")}</span>
                <span>{tx("soc.col-enable")}</span>
              </div>
              {platforms.length ? (
                platforms.map((item: SocPlatform) => (
                  <div
                    className={`${styles.trow} ${styles.platRow} ${selectedPlatform?.platformKey === item.platformKey ? styles.trowSelected : ""}`}
                    key={item.platformKey}
                    onClick={() => {
                      setSelectedPlatformKey(item.platformKey);
                      setPlatformKey(item.platformKey);
                      setPlatformName(item.displayName);
                      setPlatformEnable(item.enable);
                    }}
                  >
                    <span>{item.displayName}</span>
                    <span>{item.capability === "REGISTERED" ? tx("soc.capability-registered") : item.capability}</span>
                    <span>{item.policy === "GOVERNED" ? tx("soc.policy-governed") : item.policy}</span>
                    <span>{item.health === "UNKNOWN" ? tx("soc.health-unknown") : item.health}</span>
                    <span>{tx(ENABLE_LABEL[item.enable])}</span>
                  </div>
                ))
              ) : (
                <p className={styles.empty}>{loading ? dash : tx("soc.empty-platform")}</p>
              )}
            </div>
            <div className={styles.actions}>
              <Btn
                uid="SOC-01-BTN-PLATFORM-CONFIG"
                label={tx("soc.btn-platform-config")}
                onAct={() =>
                  void act("SOC-01-BTN-PLATFORM-CONFIG", {
                    platformKey,
                    displayName: platformName,
                    enable: platformEnable,
                  })
                }
                disabled={disabled || !platformKey || !platformName}
                primary
              />
              <Btn
                uid="SOC-01-BTN-KILL"
                label={tx("soc.btn-kill")}
                onAct={() => void act("SOC-01-BTN-KILL", { reason: "OPERATOR_STOP" })}
                disabled={disabled || !risky}
                danger
              />
            </div>
            {!risky ? <p className={styles.note}>{tx("soc.kill-idle")}</p> : null}
          </section>
          <GovernanceRail
            t={tx}
            dash={dash}
            disabled={disabled}
            onDrawer={() => setDrawerOpen(true)}
            onAct={act}
            variant="platform"
            health={selectedPlatform ? (selectedPlatform.health === "UNKNOWN" ? tx("soc.health-unknown") : selectedPlatform.health) : dash}
            capability={selectedPlatform ? tx("soc.capability-registered") : dash}
            blocker={workbench.kill?.reason || discovery?.blocker || dash}
            manual={dash}
          />
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
                  <input className={styles.fieldInput} value={jobName} disabled={disabled} onChange={(event) => setJobName(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-platform")}</span>
                  <input className={styles.fieldInput} value={activePlatformKey} disabled={disabled} onChange={(event) => setPlatformKey(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-target-types")}</span>
                  <input className={styles.fieldInput} value={targetTypes} disabled={disabled} onChange={(event) => setTargetTypes(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-keywords")}</span>
                  <input className={styles.fieldInput} value={keywords} disabled={disabled} onChange={(event) => setKeywords(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-categories")}</span>
                  <input className={styles.fieldInput} value={categories} disabled={disabled} onChange={(event) => setCategories(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-mode")}</span>
                  <select className={styles.fieldSelect} value={mode} disabled={disabled} onChange={(event) => setMode(event.target.value as SocDiscoveryMode)}>
                    <option value="SINGLE_RUN">{tx("soc.mode-single")}</option>
                    <option value="CONTINUOUS">{tx("soc.mode-continuous")}</option>
                  </select>
                </label>
                {discovery ? (
                  <p className={styles.note}>
                    {tx(DISCOVERY_LABEL[discovery.status])}
                    {discovery.blocker ? ` · ${tx("soc.adapter-unavailable")}` : ""}
                  </p>
                ) : null}
                <div className={styles.actions}>
                  <Btn
                    uid="SOC-01-BTN-TARGET-DISCOVERY"
                    label={tx("soc.btn-discovery")}
                    onAct={() =>
                      void act("SOC-01-BTN-TARGET-DISCOVERY", {
                        jobName,
                        platformKey: activePlatformKey,
                        targetTypes,
                        categories,
                        keywords,
                        mode,
                      })
                    }
                    disabled={disabled || !activePlatformKey || !targetTypes || !categories || !keywords}
                    primary
                  />
                  <Btn
                    uid="SOC-01-BTN-ACCOUNT-BIND"
                    label={tx("soc.btn-bind")}
                    onAct={() =>
                      void act("SOC-01-BTN-ACCOUNT-BIND", {
                        platformKey: activePlatformKey,
                        displayName,
                        loginIdentifier,
                        authMode,
                        credentialValue,
                        accountId: selectedAccount?.accountId,
                      })
                    }
                    disabled={disabled || !activePlatformKey || !displayName || !loginIdentifier || !authMode || !credentialValue}
                  />
                </div>
                <label className={styles.field}>
                  <span>{tx("soc.field-display-name")}</span>
                  <input className={styles.fieldInput} value={displayName} disabled={disabled} onChange={(event) => setDisplayName(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-login")}</span>
                  <input className={styles.fieldInput} value={loginIdentifier} disabled={disabled} onChange={(event) => setLoginIdentifier(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-auth")}</span>
                  <input className={styles.fieldInput} value={authMode} disabled={disabled} onChange={(event) => setAuthMode(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-credential")}</span>
                  <input
                    className={styles.fieldInput}
                    type="password"
                    value={credentialValue}
                    disabled={disabled}
                    autoComplete="off"
                    onChange={(event) => setCredentialValue(event.target.value)}
                  />
                </label>
                <p className={styles.note}>{tx("soc.secret-hint")}</p>
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
                      if (event.key === "Enter") void act("SOC-01-INP-TARGET-SEARCH", { query });
                    }}
                  />
                  <button type="button" className={styles.btn} disabled={disabled} onClick={() => void act("SOC-01-INP-TARGET-SEARCH", { query })}>
                    {tx("soc.btn-search")}
                  </button>
                </div>
                <div className={styles.table}>
                  <div className={`${styles.thead} ${styles.targetHead}`}>
                    <span>{tx("soc.col-target")}</span>
                    <span>{tx("soc.col-capability")}</span>
                    <span>{tx("soc.col-status")}</span>
                    <span>{tx("soc.col-signal")}</span>
                  </div>
                  {targets.length ? (
                    targets.map((item: SocTarget) => (
                      <div
                        className={`${styles.trow} ${styles.targetRow} ${selectedTarget?.targetId === item.targetId ? styles.trowSelected : ""}`}
                        key={item.targetId}
                        onClick={() => setSelectedTargetId(item.targetId)}
                      >
                        <span>{item.name}</span>
                        <span>{item.capability === "GOVERNED" ? tx("soc.policy-governed") : item.capability}</span>
                        <span>{tx(TARGET_LABEL[item.status])}</span>
                        <span>{item.signal || dash}</span>
                      </div>
                    ))
                  ) : (
                    <p className={styles.empty}>{loading ? dash : tx("soc.empty-target")}</p>
                  )}
                </div>
                <div className={styles.actions}>
                  <Btn
                    uid="SOC-01-BTN-TARGET-JOIN"
                    label={tx("soc.btn-join")}
                    onAct={() => void act("SOC-01-BTN-TARGET-JOIN", { targetId: selectedTarget?.targetId })}
                    disabled={disabled || !canJoin}
                  />
                  <Btn
                    uid="SOC-01-BTN-MANUAL-COMPLETE"
                    label={tx("soc.btn-manual")}
                    onAct={() => void act("SOC-01-BTN-MANUAL-COMPLETE", { targetId: selectedTarget?.targetId })}
                    disabled={disabled || !canManual}
                  />
                </div>
                {!selectedTarget ? <p className={styles.note}>{tx("soc.missing-target")}</p> : null}
              </div>
            </div>
            <div className={styles.card}>
              <h3>{tx("soc.lineage-title")}</h3>
              <div className={styles.lineage}>
                <div className={styles.lineageItem}>
                  <span>{tx("soc.lineage-account")}</span>
                  <strong>{lineageAccount}</strong>
                </div>
                <div className={styles.lineageItem}>
                  <span>{tx("soc.lineage-target")}</span>
                  <strong>{lineageTarget}</strong>
                </div>
                <div className={styles.lineageItem}>
                  <span>{tx("soc.lineage-version")}</span>
                  <strong>{lineageVersion}</strong>
                </div>
                <div className={styles.lineageItem}>
                  <span>{tx("soc.lineage-correlation")}</span>
                  <strong>{lineageCorrelation}</strong>
                </div>
              </div>
              {selectedAccount ? (
                <p className={styles.note}>
                  {tx(BINDING_LABEL[selectedAccount.binding])} · {tx(CREDENTIAL_LABEL[selectedAccount.credentialStatus])}
                  {selectedAccount.credentialMasked ? ` · ${selectedAccount.credentialMasked}` : ""}
                </p>
              ) : (
                <p className={styles.note}>{tx("soc.missing-account")}</p>
              )}
              <label className={styles.field}>
                <span>{tx("soc.reveal-reason")}</span>
                <input className={styles.fieldInput} value={revealReason} disabled={disabled} onChange={(event) => setRevealReason(event.target.value)} />
              </label>
              <div className={styles.actions}>
                <Btn
                  uid="SOC-01-BTN-CREDENTIAL-REVEAL"
                  label={tx("soc.btn-reveal")}
                  onAct={() =>
                    void act("SOC-01-BTN-CREDENTIAL-REVEAL", { accountId: selectedAccount?.accountId, reason: revealReason })
                  }
                  disabled={disabled || selectedAccount?.credentialStatus !== "SET" || !revealReason}
                />
                <Btn
                  uid="SOC-01-BTN-ACCOUNT-UNBIND"
                  label={tx("soc.btn-unbind")}
                  onAct={() => void act("SOC-01-BTN-ACCOUNT-UNBIND", { accountId: selectedAccount?.accountId })}
                  disabled={disabled || !selectedAccount || selectedAccount.binding === "UNBOUND"}
                  danger
                />
              </div>
              {accounts.map((item: SocAccount) => (
                <button
                  type="button"
                  key={item.accountId}
                  className={`${styles.btn} ${selectedAccount?.accountId === item.accountId ? styles.btnPrimary : ""}`}
                  onClick={() => {
                    setSelectedAccountId(item.accountId);
                    setDisplayName(item.displayName);
                    setLoginIdentifier(item.loginIdentifier);
                    setAuthMode(item.authMode);
                    setPlatformKey(item.platformKey);
                  }}
                >
                  {item.displayName}
                </button>
              ))}
            </div>
          </section>
          <GovernanceRail
            t={tx}
            dash={dash}
            disabled={disabled}
            onDrawer={() => setDrawerOpen(true)}
            onAct={act}
            variant="account"
            health={selectedAccount ? tx(BINDING_LABEL[selectedAccount.binding]) : dash}
            capability={selectedTarget ? tx(TARGET_LABEL[selectedTarget.status]) : dash}
            blocker={discovery?.blocker || dash}
            manual={canManual ? tx("soc.target-manual") : dash}
          />
        </div>
      ) : null}

      {stage === 3 ? (
        <div className={styles.cols}>
          <section className={styles.workspace} data-section-uid="SOC-01-SEC-05" data-component-uid="SOC-01-CMP-CONTENT">
            <h2>{tx("soc.content-title")}</h2>
            <p className={styles.note}>{tx("soc.content-hint")}</p>
            <div className={styles.card}>
              <h3>{tx("soc.package-title")}</h3>
              <label className={styles.field}>
                <span>{tx("soc.field-release")}</span>
                <input className={styles.fieldInput} value={releaseSource} disabled={disabled} onChange={(event) => setReleaseSource(event.target.value)} />
              </label>
              <label className={styles.field}>
                <span>{tx("soc.field-platform")}</span>
                <input className={styles.fieldInput} value={activePlatformKey} disabled={disabled} onChange={(event) => setPlatformKey(event.target.value)} />
              </label>
              <label className={styles.field}>
                <span>{tx("soc.field-variants")}</span>
                <input className={styles.fieldInput} value={variant} disabled={disabled} onChange={(event) => setVariant(event.target.value)} />
              </label>
              <div className={styles.kv}>
                <span>{tx("soc.field-policy-check")}</span>
                <strong>{content?.policyCheck === "PASS" ? tx("soc.policy-pass") : content?.policyCheck === "BLOCKED" ? tx("soc.policy-blocked") : dash}</strong>
              </div>
              <div className={styles.kv}>
                <span>{tx("soc.field-candidate")}</span>
                <strong>{content ? tx(CANDIDATE_LABEL[content.candidate]) : dash}</strong>
              </div>
              <div className={styles.kv}>
                <span>{tx("soc.field-version")}</span>
                <strong>{content ? `${content.version} / ${content.hash}` : dash}</strong>
              </div>
              <label className={styles.field}>
                <span>{tx("soc.field-decision")}</span>
                <select
                  className={styles.fieldSelect}
                  value={decision}
                  disabled={disabled}
                  onChange={(event) => setDecision(event.target.value as "APPROVE" | "REJECT" | "RETURN")}
                >
                  <option value="APPROVE">{tx("soc.decision-approve")}</option>
                  <option value="REJECT">{tx("soc.decision-reject")}</option>
                  <option value="RETURN">{tx("soc.decision-return")}</option>
                </select>
              </label>
              <div className={styles.actions}>
                <Btn
                  uid="SOC-01-BTN-CONTENT-SAVE"
                  label={tx("soc.btn-draft")}
                  onAct={() =>
                    void act("SOC-01-BTN-CONTENT-SAVE", {
                      releaseSource,
                      platformKey: activePlatformKey,
                      variant,
                    })
                  }
                  disabled={disabled || !releaseSource || !activePlatformKey || !variant}
                />
                <Btn
                  uid="SOC-01-BTN-CANDIDATE-DECIDE"
                  label={tx("soc.btn-candidate")}
                  onAct={() =>
                    void act("SOC-01-BTN-CANDIDATE-DECIDE", {
                      packageId: content?.packageId,
                      decision,
                    })
                  }
                  disabled={disabled || content?.candidate !== "REVIEW"}
                  primary
                />
              </div>
            </div>
          </section>
          <GovernanceRail
            t={tx}
            dash={dash}
            disabled={disabled}
            onDrawer={() => setDrawerOpen(true)}
            onAct={act}
            variant="content"
            health={content ? tx(CANDIDATE_LABEL[content.candidate]) : dash}
            capability={content?.platformKey || dash}
            blocker={dash}
            manual={dash}
          />
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
                  <strong>{content?.releaseSource || dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-variants")}</span>
                  <strong>{content?.variant || dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-policy-check")}</span>
                  <strong>{content?.policyCheck === "PASS" ? tx("soc.policy-pass") : dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-candidate")}</span>
                  <strong>{content ? tx(CANDIDATE_LABEL[content.candidate]) : dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-version")}</span>
                  <strong>{content ? `${content.version} / ${content.hash}` : dash}</strong>
                </div>
                {!content ? <p className={styles.note}>{tx("soc.missing-package")}</p> : null}
              </div>
              <div className={styles.card}>
                <h3>{tx("soc.plan-title")}</h3>
                <div className={styles.kv}>
                  <span>{tx("soc.field-target")}</span>
                  <strong>{selectedTarget?.name || dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-account")}</span>
                  <strong>{publishAccount?.displayName || dash}</strong>
                </div>
                <div className={styles.kv}>
                  <span>{tx("soc.field-content")}</span>
                  <strong>{content?.packageId || dash}</strong>
                </div>
                <label className={styles.field}>
                  <span>{tx("soc.field-min-interval")}</span>
                  <input className={styles.fieldInput} value={minIntervalHours} disabled={disabled} onChange={(event) => setMinIntervalHours(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-daily")}</span>
                  <input className={styles.fieldInput} value={dailyLimit} disabled={disabled} onChange={(event) => setDailyLimit(event.target.value)} />
                </label>
                <label className={styles.field}>
                  <span>{tx("soc.field-weekly")}</span>
                  <input className={styles.fieldInput} value={weeklyLimit} disabled={disabled} onChange={(event) => setWeeklyLimit(event.target.value)} />
                </label>
                <div className={styles.kv}>
                  <span>{tx("soc.field-schedule")}</span>
                  <strong>{policy ? `${policy.minIntervalHours} / ${policy.dailyLimit} / ${policy.weeklyLimit}` : dash}</strong>
                </div>
                {!policy || policy.targetId !== selectedTarget?.targetId ? <p className={styles.note}>{tx("soc.missing-policy")}</p> : null}
                <div className={styles.actions}>
                  <Btn
                    uid="SOC-01-BTN-POLICY-CONFIG"
                    label={tx("soc.btn-policy")}
                    onAct={() =>
                      void act("SOC-01-BTN-POLICY-CONFIG", {
                        targetId: selectedTarget?.targetId,
                        minIntervalHours,
                        dailyLimit,
                        weeklyLimit,
                      })
                    }
                    disabled={disabled || !selectedTarget}
                  />
                  <Btn
                    uid="SOC-01-BTN-PUBLISH"
                    label={tx("soc.btn-publish")}
                    onAct={() =>
                      void act("SOC-01-BTN-PUBLISH", {
                        targetId: selectedTarget?.targetId,
                        channelAccountId: publishAccount?.accountId,
                        contentPackageId: content?.packageId,
                      })
                    }
                    disabled={disabled || !canPublish}
                    primary
                  />
                  <Btn uid="SOC-01-BTN-REFRESH" label={tx("soc.btn-refresh")} onAct={() => void act("SOC-01-BTN-REFRESH")} disabled={disabled} />
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
                    if (event.key === "Enter") void act("SOC-01-INP-RECORD-SEARCH", { query: recordQuery });
                  }}
                />
                <button type="button" className={styles.btn} disabled={disabled} onClick={() => void act("SOC-01-INP-RECORD-SEARCH", { query: recordQuery })}>
                  {tx("soc.btn-search")}
                </button>
              </div>
              <div className={styles.table}>
                <div className={`${styles.thead} ${styles.recHead}`}>
                  <span>{tx("soc.col-request")}</span>
                  <span>{tx("soc.col-external")}</span>
                  <span>{tx("soc.col-metrics")}</span>
                  <span>{tx("soc.col-interaction")}</span>
                  <span>{tx("soc.col-callback")}</span>
                </div>
                {requests.length ? (
                  requests.map((item) => (
                    <div
                      className={`${styles.trow} ${styles.recRow} ${selectedRequest?.requestId === item.requestId ? styles.trowSelected : ""}`}
                      key={item.requestId}
                      onClick={() => setSelectedRequestId(item.requestId)}
                    >
                      <span>{item.requestId}</span>
                      <span>{item.external === "PENDING_EXTERNAL" ? tx("soc.request-pending") : item.external === "STOPPED" ? tx("soc.request-stopped") : item.external || tx(REQUEST_LABEL[item.status])}</span>
                      <span>{item.metrics || dash}</span>
                      <span>{item.interaction || dash}</span>
                      <span>{item.callback === "SHARED_ADAPTER_UNAVAILABLE" ? tx("soc.adapter-unavailable") : item.callback || dash}</span>
                    </div>
                  ))
                ) : (
                  <p className={styles.empty}>{loading ? dash : tx("soc.empty-record")}</p>
                )}
              </div>
              <p className={styles.note}>{tx("soc.withdraw-note")}</p>
            </div>
          </section>
          <GovernanceRail
            t={tx}
            dash={dash}
            disabled={disabled}
            onDrawer={() => setDrawerOpen(true)}
            onAct={act}
            variant="publish"
            health={selectedRequest ? tx(REQUEST_LABEL[selectedRequest.status]) : dash}
            capability={selectedTarget ? tx(TARGET_LABEL[selectedTarget.status]) : dash}
            blocker={workbench.kill?.reason || selectedRequest?.callback || dash}
            manual={dash}
          />
        </div>
      ) : null}

      {drawerOpen ? (
        <section className={styles.card} data-section-uid="SOC-01-SEC-08" data-component-uid="SOC-01-CMP-GOVERNANCE">
          <h3>{tx("soc.drawer-title")}</h3>
          <p className={styles.note}>{tx("soc.drawer-hint")}</p>
          <div className={styles.lineage}>
            <div className={styles.lineageItem}>
              <span>{tx("soc.col-callback")}</span>
              <strong>
                {selectedRequest?.callback === "SHARED_ADAPTER_UNAVAILABLE"
                  ? tx("soc.adapter-unavailable")
                  : selectedRequest?.callback || discovery?.blocker || dash}
              </strong>
            </div>
            <div className={styles.lineageItem}>
              <span>{tx("soc.field-version")}</span>
              <strong>{lineageVersion}</strong>
            </div>
            <div className={styles.lineageItem}>
              <span>{tx("soc.lineage-account")}</span>
              <strong>{lineageAccount}</strong>
            </div>
            <div className={styles.lineageItem}>
              <span>{tx("soc.lineage-target")}</span>
              <strong>{lineageTarget}</strong>
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
  health,
  capability,
  blocker,
  manual,
}: {
  t: (key: TranslationKey) => string;
  dash: string;
  disabled: boolean;
  onDrawer: () => void;
  onAct: (uid: string, payload?: Record<string, unknown>) => void;
  variant: "platform" | "account" | "content" | "publish";
  health: string;
  capability: string;
  blocker: string;
  manual: string;
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
            <strong>{health === dash ? t("soc.rail-truth-value") : health}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotDanger}`} />
            <span>{t("soc.rail-kill")}</span>
            <strong>{blocker === dash ? t("soc.rail-kill-value") : blocker}</strong>
          </div>
        </>
      ) : (
        <>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotOk}`} />
            <span>{t("soc.rail-health")}</span>
            <strong>{health}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotInfo}`} />
            <span>{t("soc.rail-capability")}</span>
            <strong>{capability}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotOk}`} />
            <span>{t("soc.rail-policy")}</span>
            <strong>{t("soc.rail-policy-value")}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotWarn}`} />
            <span>{t("soc.rail-manual")}</span>
            <strong>{manual === dash ? t("soc.rail-manual-value") : manual}</strong>
          </div>
          <div className={styles.railCard}>
            <span className={`${styles.dot} ${styles.dotDanger}`} />
            <span>{t("soc.rail-blocker")}</span>
            <strong>{blocker}</strong>
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
