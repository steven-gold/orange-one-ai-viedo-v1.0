"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { SysClientError, fetchSysReadModel, postSysAction, type SysFieldValue } from "@/lib/client";
import { displaySysValue } from "./sysFormat";
import { SYS_CONTROL_ACTIONS, SYS_VISIBLE_CONTROLS } from "./sysControls";
import styles from "./SysVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

type AiMode = "SINGLE" | "MULTI";
type CouncilMode = "DISCUSSION" | "PARALLEL";

const LIFECYCLE_STEPS: TranslationKey[] = [
  "sys.life-truth",
  "sys.life-question",
  "sys.life-decision",
  "sys.life-freeze",
  "sys.life-implement",
  "sys.life-validate",
  "sys.life-approve",
  "sys.life-release",
  "sys.life-health",
  "sys.life-close",
];

function Seg({
  uid,
  label,
  active,
  onAct,
  disabled,
}: {
  uid: string;
  label: string;
  active: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      className={`${styles.seg} ${active ? styles.segActive : ""}`}
      data-control-uid={uid}
      disabled={disabled}
      onClick={() => onAct(uid)}
    >
      {label}
    </button>
  );
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

export function SysVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<SysFieldValue[]>([]);
  const [aiMode, setAiMode] = useState<AiMode>("SINGLE");
  const [councilMode, setCouncilMode] = useState<CouncilMode>("DISCUSSION");
  const [draft, setDraft] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchSysReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : SYS_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof SysClientError ? cause.code : "SYS_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(SYS_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = SYS_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postSysAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displaySysValue(null, loading);
  const visibleUids = useMemo(() => new Set<string>(SYS_VISIBLE_CONTROLS), []);

  const selectAiMode = (next: AiMode) => {
    setAiMode(next);
    if (next === "MULTI") setCouncilMode("DISCUSSION");
    void act(next === "SINGLE" ? "SYS-01-BTN-SINGLE-AI" : "SYS-01-BTN-MULTI-AI");
  };

  const selectCouncil = (next: CouncilMode) => {
    if (aiMode !== "MULTI") return;
    setCouncilMode(next);
    void act(next === "DISCUSSION" ? "SYS-01-BTN-COUNCIL-DISCUSSION" : "SYS-01-BTN-COUNCIL-PARALLEL");
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:SYS-01"
      data-page-state={pageState}
      data-ai-mode={aiMode}
      data-council-mode={aiMode === "MULTI" ? councilMode : ""}
      data-component-count="8"
      data-control-count={visibleUids.size}
      aria-label={tx("sys.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("sys.error")}</div> : null}

      <header className={styles.heading}>
        <h1 className={styles.headingTitle}>{tx("sys.title")}</h1>
        <p className={styles.headingMeta}>{tx("sys.meta")}</p>
      </header>

      <section className={styles.context} data-section-uid="SEC-ADMIN-SYS-01-SYSTEM-CONTEXT">
        <div className={styles.ctx}>
          <span>{tx("sys.ctx-version")}</span>
          <strong>{dash}</strong>
        </div>
        <div className={styles.ctx}>
          <span>{tx("sys.ctx-change")}</span>
          <strong>{dash}</strong>
        </div>
        <div className={styles.ctx}>
          <span>{tx("sys.ctx-route")}</span>
          <strong>{dash}</strong>
        </div>
        <div className={styles.ctx}>
          <span>{tx("sys.ctx-life")}</span>
          <strong>{dash}</strong>
        </div>
      </section>

      <div className={styles.cols}>
        <aside className={styles.panel} data-section-uid="SEC-ADMIN-SYS-01-SOURCE-REFS">
          <h2>{tx("sys.system-context")}</h2>
          <div className={styles.card}>
            <h3>{tx("sys.inbox")}</h3>
            <p>{tx("sys.inbox-hint")}</p>
          </div>
          <div className={styles.card}>
            <h3>{tx("sys.change-context")}</h3>
            <p>{tx("sys.change-context-hint")}</p>
          </div>
          <div className={styles.card} data-section-uid="SEC-ADMIN-SYS-01-AUDIT">
            <h3>{tx("sys.decision-ledger")}</h3>
            <p>{tx("sys.decision-ledger-hint")}</p>
          </div>
          <div className={styles.card}>
            <h3>{tx("sys.reference")}</h3>
            <p>{tx("sys.reference-hint")}</p>
          </div>
          <div className={styles.card}>
            <h3>{tx("sys.provider-watch")}</h3>
            <p>{tx("sys.provider-watch-hint")}</p>
          </div>
        </aside>

        <section className={styles.panel} data-section-uid="SEC-ADMIN-SYS-01-CONVERSATION">
          <div className={styles.convHead} data-component-uid="SYS-01-CMP-DESIGN-CONVERSATION-HEADER" data-visual-uid="SYS-01-VIS-DESIGN-CONVERSATION-HEADER">
            <h2 className={styles.convTitle}>{tx("sys.conversation-title")}</h2>
            <div className={styles.modeRow}>
              <span className={styles.modeLabel}>{tx("sys.ai-mode")}</span>
              <Seg uid="SYS-01-BTN-SINGLE-AI" label={tx("sys.btn-single-ai")} active={aiMode === "SINGLE"} onAct={() => selectAiMode("SINGLE")} disabled={disabled} />
              <Seg uid="SYS-01-BTN-MULTI-AI" label={tx("sys.btn-multi-ai")} active={aiMode === "MULTI"} onAct={() => selectAiMode("MULTI")} disabled={disabled} />
              {aiMode === "MULTI" ? (
                <>
                  <span className={styles.spacer} />
                  <Seg uid="SYS-01-BTN-COUNCIL-DISCUSSION" label={tx("sys.btn-discussion")} active={councilMode === "DISCUSSION"} onAct={() => selectCouncil("DISCUSSION")} disabled={disabled} />
                  <Seg uid="SYS-01-BTN-COUNCIL-PARALLEL" label={tx("sys.btn-parallel")} active={councilMode === "PARALLEL"} onAct={() => selectCouncil("PARALLEL")} disabled={disabled} />
                </>
              ) : null}
            </div>
          </div>

          <div className={styles.thread} data-section-uid="SEC-ADMIN-SYS-01-CANDIDATE-CHANGE">
            <div className={styles.bubble}>{dash}</div>
            <div className={`${styles.bubble} ${styles.bubbleUser}`}>{dash}</div>
            <div className={styles.ledger}>{tx("sys.thread-ledger")} {dash}</div>
          </div>

          <div className={styles.composer} data-component-uid="SYS-01-CMP-CONVERSATION-COMPOSER" data-visual-uid="SYS-01-VIS-CONVERSATION-COMPOSER">
            <textarea
              className={styles.textarea}
              data-control-uid="SYS-01-INP-MESSAGE"
              disabled={disabled}
              value={draft}
              placeholder={tx("sys.inp-message")}
              onFocus={() => {
                void act("SYS-01-INP-MESSAGE");
              }}
              onChange={(event) => {
                setDraft(event.target.value);
              }}
            />
            <div className={styles.composerActions}>
              <Btn uid="SYS-01-BTN-ATTACH" label={tx("sys.btn-attach")} onAct={act} disabled={disabled} />
              <span className={styles.grow} />
              <Btn uid="SYS-01-BTN-STOP" label={tx("sys.btn-stop")} onAct={act} disabled={disabled} />
              <Btn uid="SYS-01-BTN-SEND" label={tx("sys.btn-send")} onAct={act} disabled={disabled} primary />
            </div>
          </div>

          <div className={styles.dock} data-section-uid="SEC-ADMIN-SYS-01-ACTION-DOCK" data-component-uid="SYS-01-CMP-ACTION-DOCK" data-visual-uid="SYS-01-VIS-ACTION-DOCK">
            <Btn uid="SYS-01-BTN-CANDIDATE-CREATE" label={tx("sys.btn-candidate-create")} onAct={act} disabled={disabled} primary />
            <Btn uid="SYS-01-BTN-CR-CREATE" label={tx("sys.btn-cr-create")} onAct={act} disabled={disabled} />
            <Btn uid="SYS-01-BTN-NAV-OPEN" label={tx("sys.btn-nav-open")} onAct={act} disabled={disabled} />
            <Btn uid="SYS-01-BTN-SANDBOX-TEST" label={tx("sys.btn-sandbox-test")} onAct={act} disabled={disabled} />
          </div>
        </section>

        <aside className={styles.panel} data-section-uid="SEC-ADMIN-SYS-01-IMPACT-PREVIEW">
          <h2>{tx("sys.decision-validation")}</h2>
          <div className={styles.card}>
            <h3>{tx("sys.p0p1")}</h3>
            <p>{tx("sys.p0p1-hint")}</p>
          </div>
          <div className={styles.card}>
            <h3>{tx("sys.duplicate")}</h3>
            <p>{tx("sys.duplicate-hint")}</p>
          </div>
          <div className={styles.card}>
            <h3>{tx("sys.impact")}</h3>
            <p>{tx("sys.impact-hint")}</p>
          </div>
          <div className={styles.card} data-section-uid="SEC-ADMIN-SYS-01-EXECUTION-PANEL" data-component-uid="SYS-01-CMP-EXECUTION-PANEL" data-visual-uid="SYS-01-VIS-EXECUTION-PANEL">
            <h3>{tx("sys.sandbox")}</h3>
            <p>{tx("sys.sandbox-hint")}</p>
          </div>
          <div className={styles.card}>
            <h3>{tx("sys.release")}</h3>
            <p>{tx("sys.release-hint")}</p>
          </div>
        </aside>
      </div>

      <section className={styles.life}>
        <h2>{tx("sys.lifecycle")}</h2>
        <div className={styles.steps}>
          {LIFECYCLE_STEPS.flatMap((key, index) => {
            const step = (
              <div key={key} className={styles.step}>
                {tx(key)}
              </div>
            );
            if (index === 0) return [step];
            return [
              <span key={`${key}-arrow`} className={styles.arrow}>
                →
              </span>,
              step,
            ];
          })}
        </div>
      </section>
    </div>
  );
}
