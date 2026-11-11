"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { StrClientError, fetchStrReadModel, postStrAction, type StrFieldValue } from "@/lib/client";
import { deriveStrPageState, displayStrValue } from "./strFormat";
import { STR_CONTROL_ACTIONS, STR_VISIBLE_CONTROLS } from "./strControls";
import styles from "./StrVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

const COMPARE_COLUMNS = [
  "str.col-candidate",
  "str.col-title",
  "str.col-benefit",
  "str.col-cost",
  "str.col-risk",
  "str.col-horizon",
  "str.col-dependency",
  "str.col-evidence",
  "str.col-uncertainty",
  "str.col-recommend",
] as const;

const CONTEXT_SOURCES = [
  "str.src-market",
  "str.src-industry",
  "str.src-competition",
  "str.src-internal",
  "str.src-resource",
  "str.src-cost",
  "str.src-risk",
  "str.src-governance",
] as const;

interface StrTurnView {
  id: string;
  role: "user" | "assistant" | "synthesis";
  alias?: string;
  text: string;
  route?: string;
  status: "SENT" | "FAILED" | "ABORTED";
  at: string;
}

function parseTurns(raw: string | null): StrTurnView[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as { turns?: StrTurnView[] };
    return Array.isArray(parsed.turns) ? parsed.turns : [];
  } catch {
    return [];
  }
}

function parseCard(raw: string | null): { title?: string; summary?: string; risk?: string; uncertainty?: string; evidence?: string } | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as { title?: string; summary?: string; risk?: string; uncertainty?: string; evidence?: string };
  } catch {
    return null;
  }
}

function Field({
  uid,
  label,
  value,
  loading,
  onAct,
  disabled,
  className,
}: {
  uid: string;
  label: string;
  value: string | null;
  loading: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
  className?: string;
}) {
  return (
    <button type="button" className={`${styles.field} ${className ?? ""}`} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayStrValue(value, loading)}</span>
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

export function StrVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [contractError, setContractError] = useState<{ code: string; detail: string; recovery?: string } | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<StrFieldValue[]>([]);
  const [draft, setDraft] = useState("");
  const [search, setSearch] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
    fetchStrReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : STR_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setContractError(model.errorState);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof StrClientError ? cause.code : "STR_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(STR_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    (controlUid: string) => fields.find((row) => row.controlUid === controlUid)?.value ?? null,
    [fields],
  );

  const act = useCallback(async (controlUid: string, nextValue?: string, signal?: AbortSignal) => {
    const actionUid = STR_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postStrAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, nextValue, signal);
    } catch (cause: unknown) {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
    setTick((n) => n + 1);
  }, []);

  const send = useCallback(async () => {
    const message = draft.trim();
    if (!message || sending) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setSending(true);
    try {
      await postStrAction(DEFAULT_ACCOUNT, "STR-01-INP-MESSAGE", "STR-01-ACT-SEND", DEFAULT_SESSION, message, controller.signal);
    } catch (cause: unknown) {
      if (!(cause instanceof DOMException && cause.name === "AbortError")) {
        await postStrAction(DEFAULT_ACCOUNT, "STR-01-BTN-STOP", "STR-01-ACT-STOP", DEFAULT_SESSION).catch(() => undefined);
      }
    } finally {
      abortRef.current = null;
      setSending(false);
      setDraft("");
      setTick((n) => n + 1);
    }
  }, [draft, sending]);

  const stop = useCallback(async () => {
    abortRef.current?.abort();
    await act("STR-01-BTN-STOP");
  }, [act]);

  const disabled = !authorized && !loading;
  const busy = loading || sending;
  const v = (uid: string) => valueOf(uid);
  const mode = (v("STR-01-TGL-MODE") ?? "SINGLE") === "MULTI" ? "MULTI" : "SINGLE";
  const pageState = loading
    ? "LOADING"
    : deriveStrPageState({
        authorized,
        sending,
        mode,
        topic: v("STR-01-FLD-TOPIC"),
        candidates: v("STR-01-FLD-CANDIDATE-REF") ? v("STR-01-STATE-CANDIDATES") : null,
        reviewState: v("STR-01-FLD-REVIEW-STATE"),
        decisionResult: v("STR-01-FLD-DECISION-RESULT"),
        feedbackActual: v("STR-01-FLD-ACTUAL"),
        feedbackLearning: v("STR-01-FLD-LEARNING"),
        error: error ?? (contractError ? contractError.code : null),
      });
  const tx = (key: TranslationKey) => t(key);
  const dash = displayStrValue(null, loading);

  const visibleUids = useMemo(() => new Set<string>(STR_VISIBLE_CONTROLS), []);

  const turns = parseTurns(v("STR-01-VIEW-CONVERSATION"));
  const topicLines = (v("STR-01-LST-TOPICS") ?? "").split("\n").map((line) => line.trim()).filter(Boolean);
  const compareRows = (v("STR-01-TBL-COMPARE") ?? "").split("\n").map((line) => line.trim()).filter(Boolean);
  const openQuestions = v("STR-01-FLD-OPEN-QUESTIONS");

  return (
    <div
      className={styles.page}
      data-page-uid="workspace:STR-01"
      data-page-state={pageState}
      data-str-mode={mode}
      data-component-count="16"
      data-control-count="57"
      aria-label={tx("str.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("str.error")}</div> : null}
      {contractError ? (
        <div className={styles.error} role="alert">
          {contractError.code} · {contractError.detail}
          {contractError.recovery ? ` · ${contractError.recovery}` : ""}
        </div>
      ) : null}

      <section className={`${styles.panel} ${styles.context}`} data-section-uid="STR-01-SEC-01" data-component-uid="STR-01-CMP-CONTEXT" data-visual-uid="STR-01-VIS-CONTEXT">
        <Field uid="STR-01-FLD-TOPIC" label={tx("str.fld-topic")} value={v("STR-01-FLD-TOPIC")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="STR-01-FLD-SCOPE" label={tx("str.fld-scope")} value={v("STR-01-FLD-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="STR-01-FLD-HORIZON" label={tx("str.fld-horizon")} value={v("STR-01-FLD-HORIZON")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="STR-01-FLD-STATE" label={tx("str.fld-state")} value={v("STR-01-FLD-STATE")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="STR-01-FLD-DECISION-STATE" label={tx("str.fld-decision-state")} value={v("STR-01-FLD-DECISION-STATE")} loading={loading} onAct={act} disabled={disabled} />
        <div className={styles.modePair} data-component-uid="STR-01-CMP-MODE">
          <button
            type="button"
            className={`${styles.btn} ${mode === "SINGLE" ? styles.btnPrimary : ""}`}
            data-control-uid="STR-01-TGL-MODE"
            disabled={busy || disabled}
            onClick={() => void act("STR-01-TGL-MODE", "SINGLE")}
          >
            {tx("str.mode-single")}
          </button>
          <button
            type="button"
            className={`${styles.btn} ${mode === "MULTI" ? styles.btnPrimary : ""}`}
            disabled={busy || disabled}
            onClick={() => void act("STR-01-TGL-MODE", "MULTI")}
          >
            {tx("str.mode-multi")}
          </button>
        </div>
      </section>

      <div className={styles.grid}>
        <aside className={styles.col}>
          <section className={styles.panel} data-section-uid="STR-01-SEC-02" data-component-uid="STR-01-CMP-TOPICS" data-visual-uid="STR-01-VIS-LEFT-TOPIC">
            <h2 className={styles.title}>{tx("str.topics")}</h2>
            <input
              type="text"
              className={styles.searchInput}
              data-control-uid="STR-01-INP-TOPIC-SEARCH"
              placeholder={tx("str.inp-topic-search")}
              value={search}
              disabled={busy || disabled}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void act("STR-01-INP-TOPIC-SEARCH", search);
                }
              }}
            />
            <div className={styles.list} data-control-uid="STR-01-LST-TOPICS">
              {topicLines.length === 0 ? (
                <button
                  type="button"
                  className={styles.item}
                  disabled={busy || disabled}
                  onClick={() => void act("STR-01-LST-TOPICS", search)}
                >
                  {tx("str.topic-create-hint")}
                  <span>{dash}</span>
                </button>
              ) : (
                topicLines.map((line) => (
                  <button
                    key={line}
                    type="button"
                    className={styles.item}
                    disabled={busy || disabled}
                    onClick={() => void act("STR-01-LST-TOPICS", line)}
                  >
                    {line}
                  </button>
                ))
              )}
            </div>
          </section>

          <section className={styles.panel} data-section-uid="STR-01-SEC-03" data-component-uid="STR-01-CMP-SOURCE-STACK" data-visual-uid="STR-01-VIS-LEFT-CONTEXT">
            <h2 className={styles.title}>{tx("str.context")}</h2>
            <div className={styles.list} data-control-uid="STR-01-LST-CONTEXT">
              {CONTEXT_SOURCES.map((key) => (
                <div
                  key={key}
                  className={styles.item}
                >
                  {tx(key)}
                  <span>{dash}</span>
                </div>
              ))}
            </div>
            <div className={styles.stack}>
              <Field uid="STR-01-FLD-CONTEXT-PRIORITY" label={tx("str.fld-context-priority")} value={v("STR-01-FLD-CONTEXT-PRIORITY")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-CONTEXT-SOURCE" label={tx("str.fld-context-source")} value={v("STR-01-FLD-CONTEXT-SOURCE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-CONTEXT-TIME" label={tx("str.fld-context-time")} value={v("STR-01-FLD-CONTEXT-TIME")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-CONTEXT-CONFIDENCE" label={tx("str.fld-context-confidence")} value={v("STR-01-FLD-CONTEXT-CONFIDENCE")} loading={loading} onAct={act} disabled={disabled} />
            </div>
          </section>

          <section className={styles.panel} data-section-uid="STR-01-SEC-04" data-component-uid="STR-01-CMP-ALERTS" data-visual-uid="STR-01-VIS-LEFT-ALERT">
            <h2 className={styles.title}>{tx("str.alerts")}</h2>
            <div className={styles.list} data-control-uid="STR-01-LST-ALERTS">
              <div className={styles.item}>
                {openQuestions && openQuestions !== "—" ? openQuestions : tx("str.alert-item")}
                <span>{openQuestions && openQuestions !== "—" ? "" : dash}</span>
              </div>
            </div>
          </section>
        </aside>

        <main className={styles.col}>
          <section className={styles.panel} data-section-uid="STR-01-SEC-05" data-component-uid="STR-01-CMP-CONVERSATION" data-visual-uid="STR-01-VIS-CONVERSATION">
            <h2 className={styles.title}>{tx("str.conversation")}</h2>
            <div className={styles.transcript} data-control-uid="STR-01-VIEW-CONVERSATION">
              {turns.length === 0 ? (
                <p className={styles.conversationTitle}>
                  {tx("str.conversation-empty")} · {tx("str.conversation-meta")} {dash}
                </p>
              ) : (
                turns.map((turn) => (
                  <div key={turn.id} className={`${styles.bubble} ${turn.role === "user" ? styles.bubbleUser : ""}`} data-turn-status={turn.status}>
                    <span className={styles.bubbleRole}>
                      {turn.role === "user" ? tx("str.role-user") : turn.role === "synthesis" ? tx("str.role-synthesis") : `${tx("str.role-assistant")}${turn.alias ? ` @${turn.alias}` : ""}`}
                      {turn.route ? ` · ${turn.route}` : ""}
                      {turn.status === "FAILED" ? ` · ${tx("str.status-failed")}` : ""}
                      {turn.status === "ABORTED" ? ` · ${tx("str.status-aborted")}` : ""}
                    </span>
                    <span className={styles.bubbleText}>{turn.text}</span>
                  </div>
                ))
              )}
            </div>
            <div className={styles.composer} data-component-uid="STR-01-CMP-COMPOSER">
              <Btn uid="STR-01-BTN-ATTACH" label={tx("str.btn-attach")} onAct={act} disabled={busy || disabled} />
              <textarea
                className={styles.textareaInput}
                data-control-uid="STR-01-INP-MESSAGE"
                placeholder={tx("str.inp-message")}
                value={draft}
                disabled={busy || disabled}
                rows={2}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                    event.preventDefault();
                    void send();
                  }
                }}
              />
              <Btn uid="STR-01-BTN-SEND" label={tx("str.btn-send")} onAct={() => void send()} disabled={busy || disabled || draft.trim() === ""} primary />
              <Btn uid="STR-01-BTN-STOP" label={tx("str.btn-stop")} onAct={() => void stop()} disabled={disabled || !sending} />
            </div>
            <div className={styles.assistant} data-component-uid="STR-01-CMP-ASSISTANT">
              <Field uid="STR-01-FLD-ASSISTANT-SUMMARY" label={tx("str.fld-assistant-summary")} value={v("STR-01-FLD-ASSISTANT-SUMMARY")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-OPEN-QUESTIONS" label={tx("str.fld-open-questions")} value={openQuestions} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-MEETING-RECORD" label={tx("str.fld-meeting-record")} value={v("STR-01-FLD-MEETING-RECORD")} loading={loading} onAct={act} disabled={disabled} />
            </div>
          </section>

          <section className={styles.panel} data-section-uid="STR-01-SEC-06" data-component-uid="STR-01-CMP-ANALYSIS" data-visual-uid="STR-01-VIS-ANALYSIS">
            <h2 className={styles.title}>{tx("str.analysis")}</h2>
            <div className={styles.analysis}>
              <Field uid="STR-01-FLD-BASIS" label={tx("str.fld-basis")} value={v("STR-01-FLD-BASIS")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-ASSUMPTIONS" label={tx("str.fld-assumptions")} value={v("STR-01-FLD-ASSUMPTIONS")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-OPPORTUNITIES" label={tx("str.fld-opportunities")} value={v("STR-01-FLD-OPPORTUNITIES")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-RISKS" label={tx("str.fld-risks")} value={v("STR-01-FLD-RISKS")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-UNCERTAINTY" label={tx("str.fld-uncertainty")} value={v("STR-01-FLD-UNCERTAINTY")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-PATTERN" label={tx("str.fld-pattern")} value={v("STR-01-FLD-PATTERN")} loading={loading} onAct={act} disabled={disabled} />
            </div>
          </section>
        </main>

        <aside className={styles.col}>
          <section className={styles.panel} data-section-uid="STR-01-SEC-08" data-component-uid="STR-01-CMP-OUTPUTS" data-visual-uid="STR-01-VIS-RIGHT-OUTPUT">
            <h2 className={styles.title}>{tx("str.outputs")}</h2>
            <div className={styles.cards}>
              {(["STR-01-CARD-RECOMMENDATION", "STR-01-CARD-ALERT", "STR-01-CARD-RESOURCE", "STR-01-CARD-BRIEF"] as const).map((uid, index) => {
                const card = parseCard(v(uid));
                const label = tx(["str.card-recommendation", "str.card-alert", "str.card-resource", "str.card-brief"][index] as TranslationKey);
                return (
                  <div key={uid} className={styles.card} data-control-uid={uid}>
                    <span className={styles.label}>{label}</span>
                    <span className={styles.value}>
                      {card ? `${card.title ?? "—"} · ${card.summary ?? "—"}` : displayStrValue(null, loading)}
                    </span>
                    {card ? <span className={styles.cardMeta}>{`risk: ${card.risk ?? "—"} · uncertainty: ${card.uncertainty ?? "—"} · evidence: ${card.evidence ?? "—"}`}</span> : null}
                  </div>
                );
              })}
            </div>
          </section>

          <section className={styles.panel} data-section-uid="STR-01-SEC-09" data-visual-uid="STR-01-VIS-RIGHT-DECISION">
            <h2 className={styles.title}>{tx("str.ledger")}</h2>
            <div className={styles.stack} data-component-uid="STR-01-CMP-LEDGER">
              <Field uid="STR-01-FLD-CANDIDATE-REF" label={tx("str.fld-candidate-ref")} value={v("STR-01-FLD-CANDIDATE-REF")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-REVIEW-STATE" label={tx("str.fld-review-state")} value={v("STR-01-FLD-REVIEW-STATE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-DECISION-ID" label={tx("str.fld-decision-id")} value={v("STR-01-FLD-DECISION-ID")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-DECISION-RESULT" label={tx("str.fld-decision-result")} value={v("STR-01-FLD-DECISION-RESULT")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-DECISION-REASON" label={tx("str.fld-decision-reason")} value={v("STR-01-FLD-DECISION-REASON")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-EXECUTION-STATE" label={tx("str.fld-execution-state")} value={v("STR-01-FLD-EXECUTION-STATE")} loading={loading} onAct={act} disabled={disabled} />
            </div>
            <div className={styles.actions} data-component-uid="STR-01-CMP-REVIEW">
              <Btn uid="STR-01-BTN-SUBMIT-REVIEW" label={tx("str.btn-submit-review")} onAct={act} disabled={busy || disabled} primary />
              <Btn
                uid="STR-01-BTN-ADOPT"
                label={tx("str.btn-adopt")}
                onAct={() => {
                  const reason = typeof window !== "undefined" ? window.prompt(tx("str.btn-adopt")) ?? "" : "";
                  if (reason.trim()) void act("STR-01-BTN-ADOPT", reason.trim());
                }}
                disabled={busy || disabled}
                primary
              />
              <Btn uid="STR-01-BTN-OPEN-OWNER" label={tx("str.btn-open-owner")} onAct={act} disabled={disabled} />
            </div>
          </section>
        </aside>
      </div>

      <section className={styles.panel} data-section-uid="STR-01-SEC-07" data-component-uid="STR-01-CMP-COMPARE" data-visual-uid="STR-01-VIS-COMPARE">
        <div className={styles.compare}>
          <h2 className={styles.title}>{tx("str.compare")}</h2>
          <div className={styles.table} data-control-uid="STR-01-TBL-COMPARE">
            <div className={styles.thead}>
              {COMPARE_COLUMNS.map((key) => (
                <span key={key}>{tx(key)}</span>
              ))}
            </div>
            {compareRows.length === 0 ? (
              <div className={styles.trow}>
                {COMPARE_COLUMNS.map((key) => (
                  <span key={key}>{dash}</span>
                ))}
              </div>
            ) : (
              compareRows.map((row) => (
                <div key={row} className={styles.trow}>
                  {row.split(" · ").map((cell, index) => (
                    <span key={`${row}-${index}`}>{cell}</span>
                  ))}
                </div>
              ))
            )}
          </div>
          <Btn uid="STR-01-BTN-COMPARE" label={tx("str.btn-compare")} onAct={act} disabled={busy || disabled} />
        </div>
      </section>

      <div className={styles.lower}>
        <section className={styles.panel} data-section-uid="STR-01-SEC-10" data-component-uid="STR-01-CMP-MEMORY" data-visual-uid="STR-01-VIS-MEMORY">
          <h2 className={styles.title}>{tx("str.memory")}</h2>
          <div className={styles.memoryGrid}>
            <button type="button" className={styles.item} data-control-uid="STR-01-LST-PATTERNS" disabled={disabled} onClick={() => void act("STR-01-LST-PATTERNS")}>
              {tx("str.lst-patterns")}
              <span>{dash}</span>
            </button>
            <button type="button" className={styles.item} data-control-uid="STR-01-LST-EXPERIMENTS" disabled={disabled} onClick={() => void act("STR-01-LST-EXPERIMENTS")}>
              {tx("str.lst-experiments")}
              <span>{dash}</span>
            </button>
            <button type="button" className={styles.item} data-control-uid="STR-01-LST-BASELINES" disabled={disabled} onClick={() => void act("STR-01-LST-BASELINES")}>
              {tx("str.lst-baselines")}
              <span>{dash}</span>
            </button>
            <button type="button" className={styles.item} data-control-uid="STR-01-LST-LEARNING" disabled={disabled} onClick={() => void act("STR-01-LST-LEARNING")}>
              {tx("str.lst-learning")}
              <span>{dash}</span>
            </button>
          </div>
        </section>

        <section className={styles.panel} data-section-uid="STR-01-SEC-11" data-component-uid="STR-01-CMP-FEEDBACK" data-visual-uid="STR-01-VIS-FEEDBACK">
          <h2 className={styles.title}>{tx("str.feedback")}</h2>
          <div className={styles.feedback}>
            <Field uid="STR-01-FLD-EXPECTED" label={tx("str.fld-expected")} value={v("STR-01-FLD-EXPECTED")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="STR-01-FLD-ACTUAL" label={tx("str.fld-actual")} value={v("STR-01-FLD-ACTUAL")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="STR-01-FLD-DIFFERENCE" label={tx("str.fld-difference")} value={v("STR-01-FLD-DIFFERENCE")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="STR-01-FLD-KPI" label={tx("str.fld-kpi")} value={v("STR-01-FLD-KPI")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="STR-01-FLD-LEARNING" label={tx("str.fld-learning")} value={v("STR-01-FLD-LEARNING")} loading={loading} onAct={act} disabled={disabled} />
          </div>
        </section>
      </div>

      <section className={`${styles.panel} ${styles.status}`} data-section-uid="STR-01-SEC-12" data-component-uid="STR-01-CMP-STATUS" data-visual-uid="STR-01-VIS-STATUS">
        <Field uid="STR-01-FLD-PROVIDER-BRAND" label={tx("str.fld-provider-brand")} value={v("STR-01-FLD-PROVIDER-BRAND")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="STR-01-FLD-CORRELATION" label={tx("str.fld-correlation")} value={v("STR-01-FLD-CORRELATION")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="STR-01-FLD-DISABLED" label={tx("str.fld-disabled")} value={v("STR-01-FLD-DISABLED")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="STR-01-FLD-OWNER-BOUNDARY" label={tx("str.fld-owner-boundary")} value={v("STR-01-FLD-OWNER-BOUNDARY")} loading={loading} onAct={act} disabled={disabled} />
        <Btn uid="STR-01-BTN-AUDIT" label={tx("str.btn-audit")} onAct={act} disabled={disabled} />
      </section>

      <div className={styles.inventory} aria-hidden="true">
        {STR_VISIBLE_CONTROLS.filter((uid) => !visibleUids.has(uid)).map((uid) => (
          <button key={uid} type="button" data-control-uid={uid} disabled={disabled} onClick={() => void act(uid)}>
            {uid}
          </button>
        ))}
      </div>
    </div>
  );
}
