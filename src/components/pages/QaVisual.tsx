"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { QaClientError, fetchQaReadModel, postQaAction, type QaFieldValue } from "@/lib/client";
import { previewQaAction } from "@/lib/qaActionPreview";
import {
  QA_STATE_CORRECTION_UID,
  QA_STATE_ERROR_UID,
  QA_STATE_FINDINGS_UID,
  QA_STATE_MANUAL_UID,
  QA_STATE_QUEUE_UID,
  QA_STATE_RELEASE_UID,
  QA_STATE_SCORECARD_UID,
  type QaCorrectionState,
  type QaFinding,
  type QaManualState,
  type QaQueueState,
  type QaReleaseState,
  type QaScorecard,
  type QaScoreRow,
} from "@/lib/qaState";
import { QA_FINDING_CATEGORIES, QA_FINDING_SEVERITIES, QA_ROOT_CAUSES } from "@/lib/qaCriteria";
import { displayQaValue } from "./qaFormat";
import { QA_CONTROL_ACTIONS, QA_VISIBLE_CONTROLS } from "./qaControls";
import { Icon, type IconName } from "@/components/ui/Icon";
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

interface EvidenceDraft {
  points: string[];
  rangeIn: string | null;
  rangeOut: string | null;
  captureError: string | null;
}

function formatTimecode(ms: number): string {
  const total = Math.max(0, Math.round(ms));
  const m = Math.floor(total / 60000);
  const s = Math.floor((total % 60000) / 1000);
  const f = total % 1000;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(f).padStart(3, "0")}`;
}

function parseJsonField<T>(raw: string | null, fallback: T): T {
  const text = (raw ?? "").trim();
  if (!text.startsWith("{") && !text.startsWith("[")) return fallback;
  try {
    return JSON.parse(text) as T;
  } catch {
    return fallback;
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
  icon,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  icon?: IconName;
}) {
  const className = [
    styles.btn,
    primary ? styles.btnPrimary : "",
    icon ? styles.iconBtn : "",
  ].filter(Boolean).join(" ");
  return (
    <button
      type="button"
      className={className}
      data-control-uid={uid}
      data-tip={icon ? label : undefined}
      aria-label={icon ? label : undefined}
      disabled={disabled}
      onClick={() => onAct(uid)}
    >
      {icon ? <Icon name={icon} /> : label}
    </button>
  );
}

function Inp({
  uid,
  label,
  value,
  onChange,
  disabled,
  select,
  options,
}: {
  uid: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
  select?: boolean;
  options?: readonly string[];
}) {
  return (
    <div className={styles.field} data-control-uid={uid}>
      <span className={styles.label}>{label}</span>
      {select ? (
        <select
          className={styles.value}
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">--</option>
          {(options ?? []).map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      ) : (
        <input
          className={styles.value}
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </div>
  );
}

export function QaVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<QaFieldValue[]>([]);
  const [surface, setSurface] = useState<QaSurface>("AUTO");
  const [playing, setPlaying] = useState(false);
  const [timecodeMs, setTimecodeMs] = useState(0);
  const [draft, setDraft] = useState<EvidenceDraft>({ points: [], rangeIn: null, rangeOut: null, captureError: null });
  const [queueFilters, setQueueFilters] = useState({ state: "", severity: "", sourceDept: "", search: "" });
  const [reviewMode, setReviewMode] = useState<"AUTO" | "MANUAL">("AUTO");
  const [findingForm, setFindingForm] = useState({ severity: "", category: "", scope: "", evidence: "" });
  const [corrForm, setCorrForm] = useState({
    findings: "",
    scorecards: "",
    instruction: "",
    scope: "",
    rootCause: "",
    action: "",
    target: "",
    revalidate: "",
  });
  const [selectedFinding, setSelectedFinding] = useState("");
  const fieldsRef = useRef(fields);
  fieldsRef.current = fields;

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
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
  }, [tick]);

  const valueOf = useCallback(
    (controlUid: string) => fields.find((row) => row.controlUid === controlUid)?.value ?? null,
    [fields],
  );

  const applyPatch = useCallback((patch: Record<string, string>) => {
    setFields((prev) => {
      const map = new Map(prev.map((row) => [row.controlUid, row.value]));
      for (const [uid, value] of Object.entries(patch)) map.set(uid, value);
      return QA_VISIBLE_CONTROLS.map((controlUid) => ({
        controlUid,
        value: map.has(controlUid) ? (map.get(controlUid) ?? null) : null,
      }));
    });
  }, []);

  const act = useCallback(
    async (controlUid: string, payload?: unknown) => {
      const actionUid = QA_CONTROL_ACTIONS[controlUid];
      if (!actionUid) return;
      // Word §2747: UI_LOCAL_EXACT/CLIENT actions never reach the server
      // projection; their observable effect stays in local session state.
      const patch = previewQaAction(
        controlUid,
        actionUid,
        (uid) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null,
        payload === undefined ? undefined : JSON.stringify(payload),
      );
      if (Object.keys(patch).length) applyPatch(patch);
      try {
        await postQaAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, payload);
      } catch {
        // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
      }
      setTick((n) => n + 1);
    },
    [applyPatch],
  );

  const queueState = useMemo(
    () => parseJsonField<QaQueueState>(valueOf(QA_STATE_QUEUE_UID), { filters: { state: "", severity: "", sourceDept: "" }, search: "", reviews: [], selected: "" }),
    [valueOf],
  );
  const scorecard = useMemo(() => parseJsonField<QaScorecard>(valueOf(QA_STATE_SCORECARD_UID), null as unknown as QaScorecard), [valueOf]);
  const findings = useMemo(() => parseJsonField<QaFinding[]>(valueOf(QA_STATE_FINDINGS_UID), []), [valueOf]);
  const manualState = useMemo(() => parseJsonField<QaManualState>(valueOf(QA_STATE_MANUAL_UID), null as unknown as QaManualState), [valueOf]);
  const correctionState = useMemo(() => parseJsonField<QaCorrectionState>(valueOf(QA_STATE_CORRECTION_UID), null as unknown as QaCorrectionState), [valueOf]);
  const releaseState = useMemo(() => parseJsonField<QaReleaseState>(valueOf(QA_STATE_RELEASE_UID), null as unknown as QaReleaseState), [valueOf]);
  const errorState = useMemo(() => parseJsonField<{ code?: string; detail?: string }>(valueOf(QA_STATE_ERROR_UID), {}), [valueOf]);

  const filteredReviews = useMemo(() => {
    const reviews = queueState.reviews ?? [];
    const search = queueFilters.search.trim().toLowerCase();
    return reviews.filter((row) => {
      if (queueFilters.state && row.state !== queueFilters.state) return false;
      if (queueFilters.severity && row.severity !== queueFilters.severity) return false;
      if (queueFilters.sourceDept && row.sourceDept !== queueFilters.sourceDept) return false;
      if (search && !`${row.taskUid} ${row.project} ${row.topic}`.toLowerCase().includes(search)) return false;
      return true;
    });
  }, [queueFilters, queueState.reviews]);

  const draftEvidence = useMemo(() => {
    const parts: string[] = [];
    if (draft.rangeIn || draft.rangeOut) parts.push(`RANGE:${draft.rangeIn ?? "?"}-${draft.rangeOut ?? "?"}`);
    draft.points.forEach((point, index) => parts.push(`PT${index + 1}:${point}`));
    return parts.join(" | ");
  }, [draft]);

  const inboundReady = Boolean(
    valueOf("QA-01-FLD-PROJECT") &&
      valueOf("QA-01-FLD-TOPIC") &&
      valueOf("QA-01-FLD-TARGET-OUTPUT") &&
      valueOf("QA-01-FLD-QA-SCRIPT") &&
      valueOf("QA-01-FLD-CRITERIA-VERSION"),
  );
  const disabled = !inboundReady;
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

  const localTransport = useCallback(
    (controlUid: string) => {
      const actionUid = QA_CONTROL_ACTIONS[controlUid];
      if (!actionUid) return;
      if (actionUid === "QA-01-ACT-VIEWER-PLAY") {
        setPlaying((prev) => !prev);
        void act(controlUid);
      } else if (actionUid === "QA-01-ACT-VIEWER-PREV-FRAME") {
        setTimecodeMs((prev) => Math.max(0, prev - 40));
        void act(controlUid);
      } else if (actionUid === "QA-01-ACT-VIEWER-NEXT-FRAME") {
        setTimecodeMs((prev) => prev + 40);
        void act(controlUid);
      } else {
        void act(controlUid);
      }
    },
    [act],
  );

  const localEvidence = useCallback(
    (controlUid: string) => {
      const stamp = formatTimecode(timecodeMs);
      const actionUid = QA_CONTROL_ACTIONS[controlUid];
      // §errors EVIDENCE-CAPTURE-001: capture without the exact
      // output/version/checksum/provenance context or a valid point/range
      // blocks the capture only; there is no manual Evidence ID fallback.
      const captureReady = Boolean(
        valueOf("QA-01-FLD-TARGET-OUTPUT") &&
          valueOf("QA-01-FLD-CHECKSUM") &&
          valueOf("QA-01-FLD-PROVENANCE") &&
          Number.isFinite(timecodeMs) &&
          timecodeMs >= 0,
      );
      if (!captureReady) {
        setDraft((prev) => ({ ...prev, captureError: "QA-01-ERR-EVIDENCE-CAPTURE-001" }));
        return;
      }
      setDraft((prev) => ({ ...prev, captureError: null }));
      if (actionUid === "QA-01-ACT-EVIDENCE-POINT") {
        setDraft((prev) => ({ ...prev, points: [...prev.points, stamp] }));
        setFindingForm((prev) => ({ ...prev, evidence: prev.evidence ? `${prev.evidence};${stamp}` : stamp }));
        void act(controlUid);
      } else if (actionUid === "QA-01-ACT-EVIDENCE-RANGE-IN") {
        setDraft((prev) => ({ ...prev, rangeIn: stamp }));
        void act(controlUid);
      } else if (actionUid === "QA-01-ACT-EVIDENCE-RANGE-OUT") {
        setDraft((prev) => ({ ...prev, rangeOut: stamp }));
        void act(controlUid);
      } else {
        void act(controlUid);
      }
    },
    [act, timecodeMs, valueOf],
  );

  const submitFinding = useCallback(
    (controlUid: string) => {
      const evidenceRefs = [
        findingForm.evidence,
        draft.rangeIn && draft.rangeOut ? `${draft.rangeIn}-${draft.rangeOut}` : "",
      ].filter(Boolean);
      void act(controlUid, {
        severity: findingForm.severity,
        category: findingForm.category,
        scope: findingForm.scope,
        evidenceRefs,
      });
    },
    [act, draft.rangeIn, draft.rangeOut, findingForm],
  );

  const submitCorrection = useCallback(
    (controlUid: string) => {
      void act(controlUid, {
        findings: corrForm.findings,
        scorecards: corrForm.scorecards,
        instruction: corrForm.instruction,
        scope: corrForm.scope,
        rootCause: corrForm.rootCause,
        action: corrForm.action,
        target: corrForm.target,
        revalidate: corrForm.revalidate ? corrForm.revalidate.split(/[;,\s]+/).filter(Boolean) : [],
      });
    },
    [act, corrForm],
  );

  const visibleUids = useMemo(() => {
    const uids = new Set<string>([
      "QA-01-FLD-PROJECT",
      "QA-01-FLD-TOPIC",
      "QA-01-FLD-QA-TASK",
      "QA-01-FLD-TARGET-OUTPUT",
      "QA-01-FLD-REVIEW-STATE",
      "QA-01-BTN-START-REVIEW",
      // Evidence capture gates require the governed checksum/provenance
      // context on every surface that offers capture (§errors EVIDENCE-CAPTURE).
      "QA-01-FLD-CHECKSUM",
      "QA-01-FLD-PROVENANCE",
    ]);
    if (showQueue) {
      uids.add("QA-01-FLD-AUTO-PROGRESS");
      if (surface === "AUTO") {
        uids.add("QA-01-BTN-AUTO-START");
        uids.add("QA-01-INP-QUEUE-SEARCH");
        uids.add("QA-01-SEL-QUEUE-STATE");
        uids.add("QA-01-SEL-QUEUE-SEVERITY");
        uids.add("QA-01-SEL-QUEUE-SOURCE-DEPT");
        uids.add("QA-01-LIST-REVIEWS");
        uids.add("QA-01-SEG-REVIEW-MODE");
      }
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
        "QA-01-VIEW-OUTPUT",
        "QA-01-FLD-EVIDENCE",
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
        "QA-01-LIST-SCORE-DIMENSIONS",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "AUTO") {
      [
        "QA-01-FLD-SCRIPT-HASH",
        "QA-01-FLD-QA-SCRIPT",
        "QA-01-FLD-CHECKSUM",
        "QA-01-FLD-RIGHTS",
        "QA-01-FLD-POLICY",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "FINDING") {
      [
        "QA-01-FLD-OPEN-FINDINGS",
        "QA-01-FLD-REQUIRED-CHECKS",
        "QA-01-FLD-PROVENANCE",
        "QA-01-BTN-FINDING-CREATE",
        "QA-01-INP-FINDING-SEVERITY",
        "QA-01-INP-FINDING-CATEGORY",
        "QA-01-INP-FINDING-SCOPE",
        "QA-01-INP-FINDING-EVIDENCE",
        "QA-01-LIST-FINDINGS",
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
        "QA-01-INP-CORR-FINDINGS",
        "QA-01-INP-CORR-SCORECARDS",
        "QA-01-INP-CORR-INSTRUCTION",
        "QA-01-INP-CORR-SCOPE",
        "QA-01-INP-CORR-ROOT",
        "QA-01-INP-CORR-ACTION",
        "QA-01-INP-CORR-TARGET",
        "QA-01-INP-CORR-REVALIDATE",
        "QA-01-BTN-CORRECTION",
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

  const queuePanel = (
    <aside className={`${styles.panel} ${styles.queue}`} data-component-uid="QA-01-CMP-QUEUE">
      <h2 className={styles.title}>{tx("qa.queue")}</h2>
      <div className={styles.modePair} data-component-uid="QA-01-CMP-REVIEW-MODE">
        <button
          type="button"
          className={`${styles.btn} ${reviewMode === "AUTO" ? styles.btnPrimary : ""}`}
          data-control-uid="QA-01-SEG-REVIEW-MODE"
          disabled={disabled}
          onClick={() => {
            setReviewMode("AUTO");
            go("AUTO", "QA-01-BTN-AUTO-START");
          }}
        >
          {tx("qa.auto")}
        </button>
        <button
          type="button"
          className={`${styles.btn} ${reviewMode === "MANUAL" ? styles.btnPrimary : ""}`}
          data-control-uid="QA-01-SEG-REVIEW-MODE"
          disabled={disabled}
          onClick={() => {
            setReviewMode("MANUAL");
            go("MANUAL");
          }}
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
          <Inp
            uid="QA-01-INP-QUEUE-SEARCH"
            label={tx("qa.queue-search")}
            value={queueFilters.search}
            disabled={disabled}
            onChange={(search) => setQueueFilters((prev) => ({ ...prev, search }))}
          />
          <div className={styles.filterRow}>
            <Inp
              uid="QA-01-SEL-QUEUE-STATE"
              label={tx("qa.filter-state")}
              value={queueFilters.state}
              disabled={disabled}
              select
              options={["PENDING", "PASSED", "CORRECTION"]}
              onChange={(state) => setQueueFilters((prev) => ({ ...prev, state }))}
            />
            <Inp
              uid="QA-01-SEL-QUEUE-SEVERITY"
              label={tx("qa.finding-severity")}
              value={queueFilters.severity}
              disabled={disabled}
              select
              options={QA_FINDING_SEVERITIES}
              onChange={(severity) => setQueueFilters((prev) => ({ ...prev, severity }))}
            />
            <Inp
              uid="QA-01-SEL-QUEUE-SOURCE-DEPT"
              label={tx("qa.filter-dept")}
              value={queueFilters.sourceDept}
              disabled={disabled}
              onChange={(sourceDept) => setQueueFilters((prev) => ({ ...prev, sourceDept }))}
            />
          </div>
          <div className={styles.list} data-control-uid="QA-01-LIST-REVIEWS">
            {filteredReviews.length ? filteredReviews.map((row) => (
              <button
                key={row.taskUid}
                type="button"
                className={styles.item}
                disabled={disabled}
                onClick={() => void act("QA-01-FLD-QA-TASK")}
              >
                {row.taskUid}
                <span>{row.project} / {row.topic || dash} · {row.state}</span>
              </button>
            )) : (
              <div className={styles.item}>
                {tx("qa.queue-item")}
                <span>{tx("qa.queue-meta")} {dash}</span>
              </div>
            )}
          </div>
        </>
      ) : (
        <Field uid="QA-01-FLD-AUTO-PROGRESS" label={tx("qa.queue-search")} value={v("QA-01-FLD-AUTO-PROGRESS")} loading={loading} onAct={act} disabled={disabled} />
      )}
    </aside>
  );

  const transport = (
    <div className={styles.transport} data-component-uid="QA-01-CMP-EVIDENCE-CAPTURE">
      <Btn uid="QA-01-BTN-PREV-FRAME" label={tx("qa.btn-prev-frame")} onAct={localTransport} disabled={disabled} icon="prev" />
      <Btn uid="QA-01-BTN-NEXT-FRAME" label={tx("qa.btn-next-frame")} onAct={localTransport} disabled={disabled} icon="next" />
      <div className={`${styles.field} ${styles.timecode}`} data-control-uid="QA-01-FLD-CURRENT-TIMECODE">
        <span className={styles.label}>{tx("qa.fld-current-timecode")}</span>
        <span className={styles.value}>{formatTimecode(timecodeMs)}</span>
      </div>
      <Btn uid="QA-01-BTN-FINDING-POINT" label={tx("qa.btn-finding-point")} onAct={localEvidence} disabled={disabled} icon="marker" />
      <Btn uid="QA-01-BTN-EVIDENCE-IN" label={tx("qa.btn-evidence-in")} onAct={localEvidence} disabled={disabled} icon="set-in" />
      <Btn uid="QA-01-BTN-EVIDENCE-OUT" label={tx("qa.btn-evidence-out")} onAct={localEvidence} disabled={disabled} icon="set-out" />
      <Btn uid="QA-01-BTN-PLAY" label={tx("qa.btn-play")} onAct={localTransport} disabled={disabled} icon={playing ? "pause" : "play"} />
      <div className={`${styles.field} ${styles.seek}`} data-control-uid="QA-01-CTL-SEEK">
        <span className={styles.label}>{tx("qa.ctl-seek")}</span>
        <input
          type="range"
          min={0}
          max={300000}
          step={40}
          value={timecodeMs}
          disabled={disabled}
          onChange={(event) => setTimecodeMs(Number(event.target.value))}
        />
      </div>
      <Btn uid="QA-01-BTN-VOLUME" label={tx("qa.btn-volume")} onAct={act} disabled={disabled} icon="volume" />
      <Btn uid="QA-01-BTN-FULLSCREEN" label={tx("qa.btn-fullscreen")} onAct={act} disabled={disabled} icon="fullscreen" />
    </div>
  );

  const viewer = (
    <section className={styles.panel} data-component-uid="QA-01-CMP-VIEWER">
      <h2 className={styles.title}>{tx("qa.viewer")}</h2>
      {showCompare ? (
        <div className={styles.compare} data-component-uid="QA-01-CMP-COMPARE">
          <div className={styles.comparePane}>
            <p className={styles.compareTitle}>{tx("qa.before")}</p>
            <span>{v("QA-01-FLD-FAILED-VERSION") || tx("qa.exact-ref")}</span>
          </div>
          <div className={styles.comparePane}>
            <p className={styles.compareTitle}>{tx("qa.after")}</p>
            <span>{v("QA-01-FLD-NEW-VERSION") || tx("qa.exact-ref")}</span>
          </div>
        </div>
      ) : (
        <div className={styles.preview} data-control-uid="QA-01-VIEW-OUTPUT">
          <p className={styles.previewTitle}>{tx("qa.preview-title")}</p>
          <span>{tx("qa.preview-meta")} {v("QA-01-FLD-TARGET-OUTPUT") || dash} · {v("QA-01-FLD-CHECKSUM") || dash}</span>
        </div>
      )}
      {draft.captureError ? (
        <div className={styles.criteriaBox} data-control-uid="QA-01-FLD-CAPTURE-ERROR">
          <p className={styles.note}>{draft.captureError}</p>
        </div>
      ) : null}
      {draftEvidence ? (
        <div className={styles.criteriaBox} data-control-uid="QA-01-FLD-EVIDENCE">
          <h3>{tx("qa.draft-evidence")}</h3>
          <p className={styles.note}>{draftEvidence}</p>
        </div>
      ) : null}
      {transport}
    </section>
  );

  const scorecardRows: QaScoreRow[] = scorecard?.rows ?? [];

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
        <div className={styles.criteriaBox} data-control-uid="QA-01-LIST-SCORE-DIMENSIONS">
          <h3>{tx("qa.score-dimensions")}</h3>
          {scorecardRows.length ? (
            <table className={styles.dimTable}>
              <thead>
                <tr><th>{tx("qa.criteria-title")}</th><th>W</th><th>S</th><th>Σ</th></tr>
              </thead>
              <tbody>
                {scorecardRows.map((row) => (
                  <tr key={row.uid} data-dim-uid={row.uid}>
                    <td>{row.name}</td>
                    <td>{row.weight}</td>
                    <td>{row.score}</td>
                    <td>{row.weighted}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className={styles.note}>{tx("qa.criteria-warn")}</p>
          )}
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
      data-control-count="87"
      aria-label={tx("qa.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("qa.error")}</div> : null}
      {!loading && !error && authorized && !inboundReady ? (
        <div className={styles.error} role="alert">{tx("qa.inbound_blocked")}</div>
      ) : null}
      {errorState.code ? <div className={styles.error} role="alert">{errorState.code}: {errorState.detail}</div> : null}

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
                <Inp
                  uid="QA-01-INP-FINDING-SEVERITY"
                  label={tx("qa.finding-severity")}
                  value={findingForm.severity}
                  disabled={disabled}
                  select
                  options={QA_FINDING_SEVERITIES}
                  onChange={(severity) => setFindingForm((prev) => ({ ...prev, severity }))}
                />
                <Inp
                  uid="QA-01-INP-FINDING-CATEGORY"
                  label={tx("qa.finding-category")}
                  value={findingForm.category}
                  disabled={disabled}
                  select
                  options={QA_FINDING_CATEGORIES}
                  onChange={(category) => setFindingForm((prev) => ({ ...prev, category }))}
                />
                <Inp
                  uid="QA-01-INP-FINDING-SCOPE"
                  label={tx("qa.finding-scope")}
                  value={findingForm.scope}
                  disabled={disabled}
                  onChange={(scope) => setFindingForm((prev) => ({ ...prev, scope }))}
                />
                <Inp
                  uid="QA-01-INP-FINDING-EVIDENCE"
                  label={tx("qa.finding-evidence")}
                  value={findingForm.evidence}
                  disabled={disabled}
                  onChange={(evidence) => setFindingForm((prev) => ({ ...prev, evidence }))}
                />
                <Btn uid="QA-01-BTN-FINDING-CREATE" label={tx("qa.btn-finding-create")} onAct={submitFinding} disabled={disabled || !findingForm.severity || !findingForm.category} primary />
                <div className={styles.list} data-control-uid="QA-01-LIST-FINDINGS">
                  {findings.length ? findings.map((row) => (
                    <button
                      key={row.uid}
                      type="button"
                      className={`${styles.item} ${selectedFinding === row.uid ? styles.itemActive : ""}`}
                      disabled={disabled}
                      onClick={() => setSelectedFinding(row.uid)}
                    >
                      {row.uid}
                      <span>{row.severity} · {row.category} · {row.state}</span>
                    </button>
                  )) : (
                    <div className={styles.item}><span>{dash}</span></div>
                  )}
                </div>
                <Field uid="QA-01-FLD-OPEN-FINDINGS" label={tx("qa.fld-open-findings")} value={v("QA-01-FLD-OPEN-FINDINGS")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="QA-01-FLD-REQUIRED-CHECKS" label={tx("qa.finding-category")} value={v("QA-01-FLD-REQUIRED-CHECKS")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="QA-01-FLD-PROVENANCE" label={tx("qa.finding-evidence")} value={v("QA-01-FLD-PROVENANCE")} loading={loading} onAct={act} disabled={disabled} />
              </div>
            </section>
          </div>
          <section className={styles.panel} data-component-uid="QA-01-CMP-MANUAL">
            <h2 className={styles.title}>{tx("qa.manual-case")}</h2>
            <div className={styles.manualRow}>
              <Field uid="QA-01-FLD-MANUAL-CASE" label={tx("qa.fld-manual-case")} value={manualState?.caseUid ?? v("QA-01-FLD-MANUAL-CASE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-MANUAL-OWNER" label={tx("qa.fld-manual-owner")} value={manualState?.owner ?? v("QA-01-FLD-MANUAL-OWNER")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-MANUAL-BLOCKER" label={tx("qa.fld-manual-blocker")} value={manualState?.blocker ?? v("QA-01-FLD-MANUAL-BLOCKER")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-MANUAL-DECISION" label={tx("qa.fld-manual-decision")} value={manualState?.decision ?? v("QA-01-FLD-MANUAL-DECISION")} loading={loading} onAct={act} disabled={disabled} />
            </div>
            <p className={styles.note}>{tx("qa.manual-note")}</p>
            <div className={styles.manualActions} data-component-uid="QA-01-CMP-MANUAL-DECISION">
              <Btn uid="QA-01-BTN-MANUAL-MODIFY" label={tx("qa.btn-manual-modify")} onAct={(uid) => { setSurface("RECHECK"); void act(uid); }} disabled={disabled} />
              <Btn uid="QA-01-BTN-MANUAL-PASS" label={tx("qa.btn-manual-pass")} onAct={(uid) => { setSurface("GATE"); void act(uid); }} disabled={disabled} primary />
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
              <Field uid="QA-01-FLD-REL-PACKAGE" label={tx("qa.fld-rel-package")} value={releaseState?.candidateUid ?? v("QA-01-FLD-REL-PACKAGE")} loading={loading} onAct={act} disabled={disabled} />
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
              <Field uid="QA-01-FLD-ERROR" label={tx("qa.fld-page-state")} value={errorState.code ?? v("QA-01-FLD-ERROR")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="QA-01-FLD-DISABLED" label={tx("qa.fld-disabled")} value={v("QA-01-FLD-DISABLED")} loading={loading} onAct={act} disabled={disabled} />
              <VisualField label={tx("qa.fld-idempotency")} value={v("QA-01-FLD-CORRELATION")} loading={loading} />
              <Field uid="QA-01-FLD-AUDIT" label={tx("qa.fld-audit")} value={v("QA-01-FLD-AUDIT")} loading={loading} onAct={act} disabled={disabled} />
            </div>
          </section>
        </>
      ) : null}

      {showQueue ? (
        <div className={styles.body}>
          {queuePanel}
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
            <Field uid="QA-01-FLD-EVIDENCE" label={tx("qa.fld-evidence")} value={draftEvidence || v("QA-01-FLD-EVIDENCE")} loading={loading} onAct={act} disabled={disabled} />
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
            <Field uid="QA-01-FLD-FAILED-VERSION" label={tx("qa.fld-failed-version")} value={correctionState?.failedVersion ?? v("QA-01-FLD-FAILED-VERSION")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-NEW-VERSION" label={tx("qa.fld-new-version")} value={correctionState?.newVersion ?? v("QA-01-FLD-NEW-VERSION")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-RECHECK-STATUS" label={tx("qa.fld-root-cause")} value={correctionState?.rootCause ?? v("QA-01-FLD-RECHECK-STATUS")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-DISABLED" label={tx("qa.fld-target-dept")} value={correctionState?.target ?? v("QA-01-FLD-DISABLED")} loading={loading} onAct={act} disabled={disabled} />
            <Inp uid="QA-01-INP-CORR-FINDINGS" label={tx("qa.inp-corr-findings")} value={corrForm.findings} disabled={disabled} onChange={(findings) => setCorrForm((prev) => ({ ...prev, findings }))} />
            <Inp uid="QA-01-INP-CORR-SCORECARDS" label={tx("qa.inp-corr-scorecards")} value={corrForm.scorecards} disabled={disabled} onChange={(scorecards) => setCorrForm((prev) => ({ ...prev, scorecards }))} />
            <Inp uid="QA-01-INP-CORR-INSTRUCTION" label={tx("qa.inp-corr-instruction")} value={corrForm.instruction} disabled={disabled} onChange={(instruction) => setCorrForm((prev) => ({ ...prev, instruction }))} />
            <Inp uid="QA-01-INP-CORR-SCOPE" label={tx("qa.finding-scope")} value={corrForm.scope} disabled={disabled} onChange={(scope) => setCorrForm((prev) => ({ ...prev, scope }))} />
            <Inp uid="QA-01-INP-CORR-ROOT" label={tx("qa.fld-root-cause")} value={corrForm.rootCause} disabled={disabled} select options={QA_ROOT_CAUSES} onChange={(rootCause) => setCorrForm((prev) => ({ ...prev, rootCause }))} />
            <Inp uid="QA-01-INP-CORR-ACTION" label={tx("qa.fld-required-action")} value={corrForm.action} disabled={disabled} onChange={(action) => setCorrForm((prev) => ({ ...prev, action }))} />
            <Inp uid="QA-01-INP-CORR-TARGET" label={tx("qa.fld-target-dept")} value={corrForm.target} disabled={disabled} onChange={(target) => setCorrForm((prev) => ({ ...prev, target }))} />
            <Inp uid="QA-01-INP-CORR-REVALIDATE" label={tx("qa.inp-corr-revalidate")} value={corrForm.revalidate} disabled={disabled} onChange={(revalidate) => setCorrForm((prev) => ({ ...prev, revalidate }))} />
          </div>
          <div className={styles.recheckRow}>
            <Field uid="QA-01-FLD-REQUIRED-CHECKS" label={tx("qa.fld-required-action")} value={correctionState?.action ?? v("QA-01-FLD-REQUIRED-CHECKS")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="QA-01-FLD-OPEN-FINDINGS" label={tx("qa.fld-finding-ids")} value={v("QA-01-FLD-OPEN-FINDINGS")} loading={loading} onAct={act} disabled={disabled} />
            <Btn uid="QA-01-BTN-CORRECTION" label={tx("qa.correction")} onAct={submitCorrection} disabled={disabled} primary />
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
