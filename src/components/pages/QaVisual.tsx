"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { QaClientError, fetchQaReadModel, postQaAction, type QaFieldValue } from "@/lib/client";
import { displayQaValue } from "./qaFormat";
import { QA_CONTROL_ACTIONS, QA_VISIBLE_CONTROLS } from "./qaControls";
import styles from "./QaVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

type QaSurface = "AUTO" | "MANUAL" | "FINDING" | "RECHECK" | "GATE";

const REVIEW_STATE: Record<QaSurface, string> = {
  AUTO: "IN_REVIEW",
  MANUAL: "NOT_STARTED",
  FINDING: "FINDING_OPEN",
  RECHECK: "RECHECK",
  GATE: "PASS",
};

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
      <span className={styles.value}>{displayQaValue(value, loading)}</span>
    </button>
  );
}

function VisualField({
  label,
  value,
  loading,
}: {
  label: string;
  value: string | null;
  loading: boolean;
}) {
  return (
    <div className={styles.field}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayQaValue(value, loading)}</span>
    </div>
  );
}

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
  icon = false,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  icon?: boolean;
}) {
  const className = [
    styles.btn,
    primary ? styles.btnPrimary : "",
    icon ? styles.iconBtn : "",
  ].filter(Boolean).join(" ");
  return (
    <button type="button" className={className} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      {label}
    </button>
  );
}

export function QaVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<QaFieldValue[]>([]);
  const [surface, setSurface] = useState<QaSurface>("AUTO");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchQaReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : QA_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof QaClientError ? cause.code : "QA_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(QA_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = QA_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postQaAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayQaValue(null, loading);
  const v = (uid: string) => valueOf(uid);
  const reviewState = v("QA-01-FLD-REVIEW-STATE") ?? REVIEW_STATE[surface];
  const queueMode = surface === "AUTO" ? "AUTO" : "MANUAL";
  const showQueue = surface === "AUTO" || surface === "MANUAL" || surface === "RECHECK";
  const showViewer = surface !== "GATE";
  const showScore = surface === "AUTO" || surface === "MANUAL" || surface === "RECHECK";
  const showCompare = surface === "RECHECK";
  const startPrimary = surface === "MANUAL";

  const go = (next: QaSurface, uid?: string) => {
    setSurface(next);
    if (uid) void act(uid);
  };

  const visibleUids = useMemo(() => {
    const uids = new Set<string>([
      "QA-01-FLD-PROJECT",
      "QA-01-FLD-TOPIC",
      "QA-01-FLD-QA-TASK",
      "QA-01-FLD-TARGET-OUTPUT",
      "QA-01-FLD-REVIEW-STATE",
      "QA-01-BTN-START-REVIEW",
    ]);
    if (showQueue) {
      uids.add("QA-01-FLD-AUTO-PROGRESS");
      if (surface === "AUTO") uids.add("QA-01-BTN-AUTO-START");
    }
    if (showViewer) {
      [
        "QA-01-BTN-PREV-FRAME",
        "QA-01-BTN-NEXT-FRAME",
        "QA-01-FLD-CURRENT-TIMECODE",
        "QA-01-BTN-FINDING-POINT",
        "QA-01-BTN-EVIDENCE-IN",
        "QA-01-BTN-EVIDENCE-OUT",
        "QA-01-BTN-PLAY",
        "QA-01-CTL-SEEK",
        "QA-01-BTN-VOLUME",
        "QA-01-BTN-FULLSCREEN",
      ].forEach((uid) => uids.add(uid));
    }
    if (showScore) {
      [
        "QA-01-FLD-CRITERIA-VERSION",
        "QA-01-FLD-GATE-POLICY",
        "QA-01-FLD-TOTAL-SCORE",
        "QA-01-FLD-HARD-BLOCK",
        "QA-01-FLD-GATE-STATUS",
        "QA-01-FLD-OPEN-FINDINGS",
        "QA-01-FLD-MANUAL-STATE",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "AUTO") {
      [
        "QA-01-FLD-SCRIPT-HASH",
        "QA-01-FLD-QA-SCRIPT",
        "QA-01-FLD-EVIDENCE",
        "QA-01-FLD-CHECKSUM",
        "QA-01-FLD-RIGHTS",
        "QA-01-FLD-POLICY",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "FINDING") {
      [
        "QA-01-FLD-OPEN-FINDINGS",
        "QA-01-FLD-REQUIRED-CHECKS",
        "QA-01-FLD-EVIDENCE",
        "QA-01-FLD-PROVENANCE",
        "QA-01-BTN-FINDING-CREATE",
        "QA-01-FLD-MANUAL-CASE",
        "QA-01-FLD-MANUAL-OWNER",
        "QA-01-FLD-MANUAL-BLOCKER",
        "QA-01-FLD-MANUAL-DECISION",
        "QA-01-BTN-MANUAL-MODIFY",
        "QA-01-BTN-MANUAL-PASS",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "RECHECK") {
      [
        "QA-01-FLD-OPEN-FINDINGS",
        "QA-01-FLD-FAILED-VERSION",
        "QA-01-FLD-NEW-VERSION",
        "QA-01-FLD-RECHECK-STATUS",
        "QA-01-FLD-DISABLED",
        "QA-01-FLD-REQUIRED-CHECKS",
        "QA-01-BTN-RECHECK",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "GATE") {
      [
        "QA-01-FLD-REL-QA-PASS",
        "QA-01-FLD-REL-FINDINGS",
        "QA-01-FLD-REL-MANUAL",
        "QA-01-FLD-REL-RIGHTS",
        "QA-01-FLD-REL-POLICY",
        "QA-01-FLD-REL-CHANNEL",
        "QA-01-FLD-REL-PACKAGE",
        "QA-01-FLD-REL-OUTPUTS",
        "QA-01-FLD-REL-QA-GATE",
        "QA-01-FLD-REL-RIGHTS-GATE",
        "QA-01-FLD-CORRELATION",
        "QA-01-BTN-RELEASE-CREATE",
        "QA-01-FLD-ERROR",
        "QA-01-FLD-DISABLED",
        "QA-01-FLD-AUDIT",
      ].forEach((uid) => uids.add(uid));
    }
    return uids;
  }, [showQueue, showScore, showViewer, surface]);

  const queue = (
    <aside className={`${styles.panel} ${styles.queue}`} data-component-uid="QA-01-CMP-QUEUE">
      <h2 className={styles.title}>{tx("qa.queue")}</h2>
      <div className={styles.modePair} data-component-uid="QA-01-CMP-REVIEW-MODE">
        <button
          type="button"
          className={`${styles.btn} ${queueMode === "AUTO" ? styles.btnPrimary : ""}`}
          disabled={disabled}
          onClick={() => go("AUTO", "QA-01-BTN-AUTO-START")}
        >
          {tx("qa.auto")}
        </button>
        <button
          type="button"
          className={`${styles.btn} ${queueMode === "MANUAL" ? styles.btnPrimary : ""}`}
          disabled={disabled}
          onClick={() => go("MANUAL")}
        >
          {tx("qa.manual")}
        </button>
      </div>
      {surface === "AUTO" ? (
        <>
          <Btn uid="QA-01-BTN-AUTO-START" label={tx("qa.btn-auto-start")} onAct={(uid) => go("AUTO", uid)} disabled={disabled} primary />
          <div data-component-uid="QA-01-CMP-AUTO-PROGRESS">
            <Field uid="QA-01-FLD-AUTO-PROGRESS" label={tx("qa.fld-auto-progress")} value={v("QA-01-FLD-AUTO-PROGRESS")} loading={loading} onAct={act} disabled={disabled} />
          </div>
        </>
      ) : (
        <Field uid="QA-01-FLD-AUTO-PROGRESS" label={tx("qa.queue-search")} value={v("QA-01-FLD-AUTO-PROGRESS")} loading={loading} onAct={act} disabled={disabled} />
      )}
      <div className={styles.filterRow}>
        <div className={styles.field}>
          <span className={styles.label}>{tx("qa.filter-state")}</span>
          <span className={styles.value}>{tx("qa.filter-all")}</span>
        </div>
        <div className={styles.field}>
          <span className={styles.label}>{tx("qa.filter-dept")}</span>
          <span className={styles.value}>{tx("qa.filter-all")}</span>
        </div>
      </div>
      <div className={styles.list}>
        {[0, 1, 2, 3, 4].map((index) => (
          <button
            key={index}
            type="button"
            className={`${styles.item} ${index === 0 ? styles.itemActive : ""}`}
            disabled={disabled}
            onClick={() => void act("QA-01-FLD-QA-TASK")}
          >
            {tx("qa.queue-item")}
            <span>{tx("qa.queue-meta")} {dash}</span>
          </button>
        ))}
      </div>
    </aside>
  );

  const transport = (
    <div className={styles.transport} data-component-uid="QA-01-CMP-EVIDENCE-CAPTURE">
      <Btn uid="QA-01-BTN-PREV-FRAME" label="◀" onAct={act} disabled={disabled} icon />
      <Btn uid="QA-01-BTN-NEXT-FRAME" label="▶" onAct={act} disabled={disabled} icon />
      <Field uid="QA-01-FLD-CURRENT-TIMECODE" label={tx("qa.fld-current-timecode")} value={v("QA-01-FLD-CURRENT-TIMECODE")} loading={loading} onAct={act} disabled={disabled} className={styles.timecode} />
      <Btn uid="QA-01-BTN-FINDING-POINT" label={tx("qa.btn-finding-point")} onAct={(uid) => go("FINDING", uid)} disabled={disabled} />
      <Btn uid="QA-01-BTN-EVIDENCE-IN" label={tx("qa.btn-evidence-in")} onAct={act} disabled={disabled} />
      <Btn uid="QA-01-BTN-EVIDENCE-OUT" label={tx("qa.btn-evidence-out")} onAct={act} disabled={disabled} />
      <Btn uid="QA-01-BTN-PLAY" label={tx("qa.btn-play")} onAct={act} disabled={disabled} />
      <button type="button" className={`${styles.field} ${styles.seek}`} data-control-uid="QA-01-CTL-SEEK" disabled={disabled} onClick={() => void act("QA-01-CTL-SEEK")}>
        <span className={styles.label}>{tx("qa.ctl-seek")}</span>
        <span className={styles.value}>{dash}</span>
      </button>
      <Btn uid="QA-01-BTN-VOLUME" label={tx("qa.btn-volume")} onAct={act} disabled={disabled} />
      <Btn uid="QA-01-BTN-FULLSCREEN" label={tx("qa.btn-fullscreen")} onAct={act} disabled={disabled} />
    </div>
  );

  const viewer = (
    <section className={styles.panel} data-component-uid="QA-01-CMP-VIEWER">
      <h2 className={styles.title}>{tx("qa.viewer")}</h2>
      {showCompare ? (
        <div className={styles.compare} data-component-uid="QA-01-CMP-COMPARE">
          <div className={styles.comparePane}>
            <p className={styles.compareTitle}>{tx("qa.before")}</p>
            <span>{tx("qa.exact-ref")} {dash}</span>
          </div>
          <div className={styles.comparePane}>
            <p className={styles.compareTitle}>{tx("qa.after")}</p>
            <span>{tx("qa.exact-ref")} {dash}</span>
          </div>
        </div>
      ) : (
        <div className={styles.preview}>
          <p className={styles.previewTitle}>{tx("qa.preview-title")}</p>
          <span>{tx("qa.preview-meta")} {dash}</span>
        </div>
      )}
      {transport}
    </section>
  );

  const score = (
    <aside className={`${styles.panel} ${styles.score}`} data-component-uid="QA-01-CMP-SCORE">
      <h2 className={styles.title}>{tx("qa.scorecard")}</h2>
      <div className={styles.scoreStack} data-component-uid="QA-01-CMP-CRITERIA">
        <Field uid="QA-01-FLD-CRITERIA-VERSION" label={tx("qa.fld-criteria-version")} value={v("QA-01-FLD-CRITERIA-VERSION")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="QA-01-FLD-GATE-POLICY" label={tx("qa.fld-gate-policy")} value={v("QA-01-FLD-GATE-POLICY")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="QA-01-FLD-TOTAL-SCORE" label={tx("qa.fld-total-score")} value={v("QA-01-FLD-TOTAL-SCORE")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="QA-01-FLD-HARD-BLOCK" label={tx("qa.fld-hard-block")} value={v("QA-01-FLD-HARD-BLOCK")} loading={loading} onAct={act} disabled={disabled} />
        <div data-component-uid="QA-01-CMP-GATE">
          <Field uid="QA-01-FLD-GATE-STATUS" label={tx("qa.fld-gate-status")} value={v("QA-01-FLD-GATE-STATUS")} loading={loading} onAct={(uid) => go("GATE", uid)} disabled={disabled} />
        </div>
        <div data-component-uid="QA-01-CMP-FINDING-LIST">
          <Field uid="QA-01-FLD-OPEN-FINDINGS" label={tx("qa.fld-open-findings")} value={v("QA-01-FLD-OPEN-FINDINGS")} loading={loading} onAct={(uid) => go("FINDING", uid)} disabled={disabled} />
        </div>
        <Field uid="QA-01-FLD-MANUAL-STATE" label={tx("qa.fld-manual-state")} value={v("QA-01-FLD-MANUAL-STATE")} loading={loading} onAct={act} disabled={disabled} />
        <div className={styles.criteriaBox}>
          <h3>{tx("qa.criteria-title")}</h3>
          <p className={styles.warn}>{tx("qa.criteria-warn")}</p>
        </div>
      </div>
    </aside>
  );

  return (
    <div
      className={styles.page}
      data-page-uid="QA-01"
      data-page-state={pageState}
      data-qa-surface={surface}
      data-component-count="21"
      data-control-count="66"
      aria-label={tx("qa.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("qa.error")}</div> : null}

      <section className={`${styles.panel} ${styles.context}`} data-component-uid="QA-01-CMP-CONTEXT">
        <Field uid="QA-01-FLD-PROJECT" label={tx("qa.fld-project")} value={v("QA-01-FLD-PROJECT")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="QA-01-FLD-TOPIC" label={tx("qa.fld-topic")} value={v("QA-01-FLD-TOPIC")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="QA-01-FLD-QA-TASK" label={tx("qa.fld-qa-task")} value={v("QA-01-FLD-QA-TASK")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="QA-01-FLD-TARGET-OUTPUT" label={tx("qa.fld-target-output")} value={v("QA-01-FLD-TARGET-OUTPUT")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="QA-01-FLD-REVIEW-STATE" label={tx("qa.fld-review-state")} value={reviewState} loading={false} onAct={act} disabled={disabled} />
        <Btn uid="QA-01-BTN-START-REVIEW" label={tx("qa.btn-start-review")} onAct={(uid) => go(surface === "MANUAL" ? "FINDING" : surface, uid)} disabled={disabled} primary={startPrimary} />
      </section>

      {surface === "FINDING" ? (
        <>
          <div className={styles.findingGrid}>
            <div className={styles.viewerCol}>{viewer}</div>
            <section className={`${styles.panel} ${styles.score}`} data-component-uid="QA-01-CMP-FINDING-FORM">
              <h2 className={styles.title}>{tx("qa.finding")}</h2>
              <div className={styles.scoreStack}>
                <Field uid="QA-01-FLD-OPEN-FINDINGS" label={tx("qa.finding-severity")} value={v("QA-01-FLD-OPEN-FINDINGS")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="QA-01-FLD-REQUIRED-CHECKS" label={tx("qa.finding-category")} value={v("QA-01-FLD-REQUIRED-CHECKS")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="QA-01-FLD-EVIDENCE" label={tx("qa.finding-scope")} value={v("QA-01-FLD-EVIDENCE")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="QA-01-FLD-PROVENANCE" label={tx("qa.finding-evidence")} value={v("QA-01-FLD-PROVENANCE")} loading={loading} onAct={act} disabled={disabled} />
                <Btn uid="QA-01-BTN-FINDING-CREATE" label={tx("qa.btn-finding-create")} onAct={(uid) => go("FINDING", uid)} disabled={disabled} primary />
              </div>
            </section>
          </div>
          <section className={styles.panel} data-component-uid="QA-01-CMP-MANUAL">
            <h2 className={styles.title}>{tx("qa.manual-case")}</h2>
            <div className={styles.manualRow}>
              <Field uid="QA-01-FLD-MANUAL-CASE" label={tx("qa.fld-manual-case")} value={v("QA-01-FLD-MANUAL-CASE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-MANUAL-OWNER" label={tx("qa.fld-manual-owner")} value={v("QA-01-FLD-MANUAL-OWNER")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-MANUAL-BLOCKER" label={tx("qa.fld-manual-blocker")} value={v("QA-01-FLD-MANUAL-BLOCKER")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-MANUAL-DECISION" label={tx("qa.fld-manual-decision")} value={v("QA-01-FLD-MANUAL-DECISION")} loading={loading} onAct={act} disabled={disabled} />
            </div>
            <p className={styles.note}>{tx("qa.manual-note")}</p>
            <div className={styles.manualActions} data-component-uid="QA-01-CMP-MANUAL-DECISION">
              <Btn uid="QA-01-BTN-MANUAL-MODIFY" label={tx("qa.btn-manual-modify")} onAct={(uid) => go("RECHECK", uid)} disabled={disabled} />
              <Btn uid="QA-01-BTN-MANUAL-PASS" label={tx("qa.btn-manual-pass")} onAct={(uid) => go("GATE", uid)} disabled={disabled} primary />
              <p className={styles.warn}>{tx("qa.manual-warn")}</p>
            </div>
          </section>
        </>
      ) : null}

      {surface === "GATE" ? (
        <>
          <section className={styles.panel} data-component-uid="QA-01-CMP-RELEASE-READY">
            <h2 className={styles.title}>{tx("qa.release-ready")}</h2>
            <div className={styles.eligibility}>
              <button type="button" className={styles.gateChip} data-control-uid="QA-01-FLD-REL-QA-PASS" disabled={disabled} onClick={() => void act("QA-01-FLD-REL-QA-PASS")}>{tx("qa.rel-qa-pass")}</button>
              <button type="button" className={styles.gateChip} data-control-uid="QA-01-FLD-REL-FINDINGS" disabled={disabled} onClick={() => void act("QA-01-FLD-REL-FINDINGS")}>{tx("qa.rel-findings")}</button>
              <button type="button" className={styles.gateChip} data-control-uid="QA-01-FLD-REL-MANUAL" disabled={disabled} onClick={() => void act("QA-01-FLD-REL-MANUAL")}>{tx("qa.rel-manual")}</button>
              <button type="button" className={styles.gateChip} data-control-uid="QA-01-FLD-REL-RIGHTS" disabled={disabled} onClick={() => void act("QA-01-FLD-REL-RIGHTS")}>{tx("qa.rel-rights")}</button>
              <button type="button" className={styles.gateChip} data-control-uid="QA-01-FLD-REL-POLICY" disabled={disabled} onClick={() => void act("QA-01-FLD-REL-POLICY")}>{tx("qa.rel-policy")}</button>
              <button type="button" className={styles.gateChip} data-control-uid="QA-01-FLD-REL-CHANNEL" disabled={disabled} onClick={() => void act("QA-01-FLD-REL-CHANNEL")}>{tx("qa.rel-channel")}</button>
            </div>
          </section>
          <section className={styles.panel} data-component-uid="QA-01-CMP-RELEASE">
            <h2 className={styles.title}>{tx("qa.release")}</h2>
            <div className={styles.releaseGrid}>
              <Field uid="QA-01-FLD-REL-PACKAGE" label={tx("qa.fld-rel-package")} value={v("QA-01-FLD-REL-PACKAGE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-REL-OUTPUTS" label={tx("qa.fld-rel-outputs")} value={v("QA-01-FLD-REL-OUTPUTS")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-REL-QA-GATE" label={tx("qa.fld-rel-qa-gate")} value={v("QA-01-FLD-REL-QA-GATE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-REL-RIGHTS-GATE" label={tx("qa.fld-rel-rights-gate")} value={v("QA-01-FLD-REL-RIGHTS-GATE")} loading={loading} onAct={act} disabled={disabled} />
              <VisualField label={tx("qa.fld-rel-channel-ref")} value={v("QA-01-FLD-REL-CHANNEL")} loading={loading} />
              <Field uid="QA-01-FLD-CORRELATION" label={tx("qa.fld-correlation")} value={v("QA-01-FLD-CORRELATION")} loading={loading} onAct={act} disabled={disabled} />
            </div>
            <div className={styles.releaseAction}>
              <Btn uid="QA-01-BTN-RELEASE-CREATE" label={tx("qa.btn-release-create")} onAct={act} disabled={disabled} primary />
              <p className={styles.warn}>{tx("qa.release-warn")}</p>
            </div>
          </section>
          <section className={styles.panel} data-component-uid="QA-01-CMP-STATUS">
            <h2 className={styles.title}>{tx("qa.status")}</h2>
            <div className={styles.statusRow}>
              <Field uid="QA-01-FLD-ERROR" label={tx("qa.fld-page-state")} value={v("QA-01-FLD-ERROR")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-DISABLED" label={tx("qa.fld-disabled")} value={v("QA-01-FLD-DISABLED")} loading={loading} onAct={act} disabled={disabled} />
              <VisualField label={tx("qa.fld-idempotency")} value={v("QA-01-FLD-CORRELATION")} loading={loading} />
              <Field uid="QA-01-FLD-AUDIT" label={tx("qa.fld-audit")} value={v("QA-01-FLD-AUDIT")} loading={loading} onAct={act} disabled={disabled} />
            </div>
          </section>
        </>
      ) : null}

      {showQueue ? (
        <div className={styles.body}>
          {queue}
          {showViewer ? <main className={styles.viewerCol}>{viewer}</main> : null}
          {showScore ? score : null}
        </div>
      ) : null}

      {surface === "AUTO" ? (
        <section className={`${styles.panel} ${styles.scriptHead}`} data-component-uid="QA-01-CMP-SCRIPT">
          <h2 className={styles.title}>{tx("qa.script")}</h2>
          <div className={styles.script} data-component-uid="QA-01-CMP-EVIDENCE">
            <Field uid="QA-01-FLD-SCRIPT-HASH" label={tx("qa.fld-script-hash")} value={v("QA-01-FLD-SCRIPT-HASH")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-QA-SCRIPT" label={tx("qa.fld-qa-script")} value={v("QA-01-FLD-QA-SCRIPT")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-EVIDENCE" label={tx("qa.fld-evidence")} value={v("QA-01-FLD-EVIDENCE")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-CHECKSUM" label={tx("qa.fld-checksum")} value={v("QA-01-FLD-CHECKSUM")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-RIGHTS" label={tx("qa.fld-rights")} value={v("QA-01-FLD-RIGHTS")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-POLICY" label={tx("qa.fld-policy")} value={v("QA-01-FLD-POLICY")} loading={loading} onAct={act} disabled={disabled} />
          </div>
        </section>
      ) : null}

      {surface === "MANUAL" ? (
        <section className={styles.panel}>
          <h2 className={styles.title}>{tx("qa.manual-select")}</h2>
          <p className={styles.note}>{tx("qa.manual-start-note")}</p>
        </section>
      ) : null}

      {surface === "RECHECK" ? (
        <section className={styles.panel} data-component-uid="QA-01-CMP-CORRECTION">
          <h2 className={styles.title}>{tx("qa.correction")}</h2>
          <div className={styles.recheckGrid} data-component-uid="QA-01-CMP-RECHECK">
            <VisualField label={tx("qa.fld-finding-ids")} value={v("QA-01-FLD-OPEN-FINDINGS")} loading={loading} />
            <Field uid="QA-01-FLD-FAILED-VERSION" label={tx("qa.fld-failed-version")} value={v("QA-01-FLD-FAILED-VERSION")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-NEW-VERSION" label={tx("qa.fld-new-version")} value={v("QA-01-FLD-NEW-VERSION")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-RECHECK-STATUS" label={tx("qa.fld-root-cause")} value={v("QA-01-FLD-RECHECK-STATUS")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-DISABLED" label={tx("qa.fld-target-dept")} value={v("QA-01-FLD-DISABLED")} loading={loading} onAct={act} disabled={disabled} />
          </div>
          <div className={styles.recheckRow}>
            <Field uid="QA-01-FLD-REQUIRED-CHECKS" label={tx("qa.fld-required-action")} value={v("QA-01-FLD-REQUIRED-CHECKS")} loading={loading} onAct={act} disabled={disabled} />
            <VisualField label={tx("qa.fld-revalidation")} value={v("QA-01-FLD-RECHECK-STATUS")} loading={loading} />
            <Btn uid="QA-01-BTN-RECHECK" label={tx("qa.btn-recheck")} onAct={(uid) => go("RECHECK", uid)} disabled={disabled} primary />
          </div>
        </section>
      ) : null}

      <div className={styles.inventory} aria-hidden="true">
        {QA_VISIBLE_CONTROLS.filter((uid) => !visibleUids.has(uid)).map((uid) => (
          uid.startsWith("QA-01-BTN") || uid === "QA-01-CTL-SEEK" ? (
            <button
              key={uid}
              type="button"
              data-control-uid={uid}
              disabled={disabled}
              onClick={() => {
                if (uid === "QA-01-BTN-COMPARE" || uid === "QA-01-BTN-CORRECTION") go("RECHECK", uid);
                else if (uid === "QA-01-BTN-MANUAL-VIEW" || uid === "QA-01-BTN-FINDING-CREATE") go("FINDING", uid);
                else if (uid === "QA-01-BTN-RELEASE-CREATE") go("GATE", uid);
                else void act(uid);
              }}
            >
              {uid}
            </button>
          ) : (
            <button key={uid} type="button" data-control-uid={uid} disabled={disabled} onClick={() => void act(uid)}>
              {uid}
            </button>
          )
        ))}
        {surface === "AUTO" ? null : <div data-component-uid="QA-01-CMP-AUTO-PROGRESS" />}
        {showQueue ? null : (
          <>
            <div data-component-uid="QA-01-CMP-QUEUE" />
            <div data-component-uid="QA-01-CMP-REVIEW-MODE" />
          </>
        )}
        {showViewer ? null : (
          <>
            <div data-component-uid="QA-01-CMP-VIEWER" />
            <div data-component-uid="QA-01-CMP-EVIDENCE-CAPTURE" />
          </>
        )}
        {showCompare ? null : <div data-component-uid="QA-01-CMP-COMPARE" />}
        {showScore ? null : (
          <>
            <div data-component-uid="QA-01-CMP-SCORE" />
            <div data-component-uid="QA-01-CMP-CRITERIA" />
            <div data-component-uid="QA-01-CMP-GATE" />
            <div data-component-uid="QA-01-CMP-FINDING-LIST" />
          </>
        )}
        {surface === "AUTO" ? null : (
          <>
            <div data-component-uid="QA-01-CMP-SCRIPT" />
            <div data-component-uid="QA-01-CMP-EVIDENCE" />
          </>
        )}
        {surface === "FINDING" ? null : (
          <>
            <div data-component-uid="QA-01-CMP-FINDING-FORM" />
            <div data-component-uid="QA-01-CMP-MANUAL" />
            <div data-component-uid="QA-01-CMP-MANUAL-DECISION" />
          </>
        )}
        {surface === "RECHECK" ? null : (
          <>
            <div data-component-uid="QA-01-CMP-CORRECTION" />
            <div data-component-uid="QA-01-CMP-RECHECK" />
          </>
        )}
        {surface === "GATE" ? null : (
          <>
            <div data-component-uid="QA-01-CMP-RELEASE-READY" />
            <div data-component-uid="QA-01-CMP-RELEASE" />
            <div data-component-uid="QA-01-CMP-STATUS" />
          </>
        )}
      </div>
    </div>
  );
}
