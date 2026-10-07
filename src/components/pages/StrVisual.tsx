"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { StrClientError, fetchStrReadModel, postStrAction, type StrFieldValue } from "@/lib/client";
import { displayStrValue } from "./strFormat";
import { STR_CONTROL_ACTIONS, STR_VISIBLE_CONTROLS } from "./strControls";
import styles from "./StrVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

type StrMode = "SINGLE" | "MULTI";

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
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<StrFieldValue[]>([]);
  const [mode, setMode] = useState<StrMode>("SINGLE");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchStrReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : STR_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
  }, []);

  const valueOf = useCallback(
    (controlUid: string) => fields.find((row) => row.controlUid === controlUid)?.value ?? null,
    [fields],
  );

  const act = useCallback(async (controlUid: string) => {
    const actionUid = STR_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postStrAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayStrValue(null, loading);
  const v = (uid: string) => valueOf(uid);

  const visibleUids = useMemo(() => new Set<string>(STR_VISIBLE_CONTROLS), []);

  const toggleMode = (next: StrMode) => {
    setMode(next);
    void act("STR-01-TGL-MODE");
  };

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
            disabled={disabled}
            onClick={() => toggleMode("SINGLE")}
          >
            {tx("str.mode-single")}
          </button>
          <button
            type="button"
            className={`${styles.btn} ${mode === "MULTI" ? styles.btnPrimary : ""}`}
            disabled={disabled}
            onClick={() => toggleMode("MULTI")}
          >
            {tx("str.mode-multi")}
          </button>
        </div>
      </section>

      <div className={styles.grid}>
        <aside className={styles.col}>
          <section className={styles.panel} data-section-uid="STR-01-SEC-02" data-component-uid="STR-01-CMP-TOPICS" data-visual-uid="STR-01-VIS-LEFT-TOPIC">
            <h2 className={styles.title}>{tx("str.topics")}</h2>
            <button type="button" className={styles.search} data-control-uid="STR-01-INP-TOPIC-SEARCH" disabled={disabled} onClick={() => void act("STR-01-INP-TOPIC-SEARCH")}>
              {tx("str.inp-topic-search")}
            </button>
            <div className={styles.list} data-control-uid="STR-01-LST-TOPICS">
              {[0, 1, 2].map((index) => (
                <button
                  key={index}
                  type="button"
                  className={styles.item}
                  disabled={disabled}
                  onClick={() => void act("STR-01-LST-TOPICS")}
                >
                  {tx("str.topic-item")}
                  <span>{dash}</span>
                </button>
              ))}
            </div>
          </section>

          <section className={styles.panel} data-section-uid="STR-01-SEC-03" data-component-uid="STR-01-CMP-SOURCE-STACK" data-visual-uid="STR-01-VIS-LEFT-CONTEXT">
            <h2 className={styles.title}>{tx("str.context")}</h2>
            <div className={styles.list} data-control-uid="STR-01-LST-CONTEXT">
              {CONTEXT_SOURCES.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={styles.item}
                  disabled={disabled}
                  onClick={() => void act("STR-01-LST-CONTEXT")}
                >
                  {tx(key)}
                  <span>{dash}</span>
                </button>
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
              <button type="button" className={styles.item} disabled={disabled} onClick={() => void act("STR-01-LST-ALERTS")}>
                {tx("str.alert-item")}
                <span>{dash}</span>
              </button>
            </div>
          </section>
        </aside>

        <main className={styles.col}>
          <section className={styles.panel} data-section-uid="STR-01-SEC-05" data-component-uid="STR-01-CMP-CONVERSATION" data-visual-uid="STR-01-VIS-CONVERSATION">
            <h2 className={styles.title}>{tx("str.conversation")}</h2>
            <button type="button" className={styles.conversation} data-control-uid="STR-01-VIEW-CONVERSATION" disabled={disabled} onClick={() => void act("STR-01-VIEW-CONVERSATION")}>
              <p className={styles.conversationTitle}>{tx("str.conversation-empty")}</p>
              <span>{tx("str.conversation-meta")} {dash}</span>
            </button>
            <div className={styles.composer} data-component-uid="STR-01-CMP-COMPOSER">
              <Btn uid="STR-01-BTN-ATTACH" label={tx("str.btn-attach")} onAct={act} disabled={disabled} />
              <button type="button" className={styles.textarea} data-control-uid="STR-01-INP-MESSAGE" disabled={disabled} onClick={() => void act("STR-01-INP-MESSAGE")}>
                {tx("str.inp-message")}
              </button>
              <Btn uid="STR-01-BTN-SEND" label={tx("str.btn-send")} onAct={act} disabled={disabled} primary />
              <Btn uid="STR-01-BTN-STOP" label={tx("str.btn-stop")} onAct={act} disabled={disabled} />
            </div>
            <div className={styles.assistant} data-component-uid="STR-01-CMP-ASSISTANT">
              <Field uid="STR-01-FLD-ASSISTANT-SUMMARY" label={tx("str.fld-assistant-summary")} value={v("STR-01-FLD-ASSISTANT-SUMMARY")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="STR-01-FLD-OPEN-QUESTIONS" label={tx("str.fld-open-questions")} value={v("STR-01-FLD-OPEN-QUESTIONS")} loading={loading} onAct={act} disabled={disabled} />
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
              <button type="button" className={styles.card} data-control-uid="STR-01-CARD-RECOMMENDATION" disabled={disabled} onClick={() => void act("STR-01-CARD-RECOMMENDATION")}>
                <span className={styles.label}>{tx("str.card-recommendation")}</span>
                <span className={styles.value}>{displayStrValue(v("STR-01-CARD-RECOMMENDATION"), loading)}</span>
              </button>
              <button type="button" className={styles.card} data-control-uid="STR-01-CARD-ALERT" disabled={disabled} onClick={() => void act("STR-01-CARD-ALERT")}>
                <span className={styles.label}>{tx("str.card-alert")}</span>
                <span className={styles.value}>{displayStrValue(v("STR-01-CARD-ALERT"), loading)}</span>
              </button>
              <button type="button" className={styles.card} data-control-uid="STR-01-CARD-RESOURCE" disabled={disabled} onClick={() => void act("STR-01-CARD-RESOURCE")}>
                <span className={styles.label}>{tx("str.card-resource")}</span>
                <span className={styles.value}>{displayStrValue(v("STR-01-CARD-RESOURCE"), loading)}</span>
              </button>
              <button type="button" className={styles.card} data-control-uid="STR-01-CARD-BRIEF" disabled={disabled} onClick={() => void act("STR-01-CARD-BRIEF")}>
                <span className={styles.label}>{tx("str.card-brief")}</span>
                <span className={styles.value}>{displayStrValue(v("STR-01-CARD-BRIEF"), loading)}</span>
              </button>
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
              <Btn uid="STR-01-BTN-SUBMIT-REVIEW" label={tx("str.btn-submit-review")} onAct={act} disabled={disabled} primary />
              <Btn uid="STR-01-BTN-ADOPT" label={tx("str.btn-adopt")} onAct={act} disabled={disabled} primary />
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
            <button type="button" className={styles.trow} disabled={disabled} onClick={() => void act("STR-01-TBL-COMPARE")}>
              {COMPARE_COLUMNS.map((key) => (
                <span key={key}>{dash}</span>
              ))}
            </button>
          </div>
          <Btn uid="STR-01-BTN-COMPARE" label={tx("str.btn-compare")} onAct={act} disabled={disabled} />
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
