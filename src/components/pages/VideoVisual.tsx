"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import {
  VideoClientError,
  fetchAssetReadModel,
  fetchCoreReadModel,
  fetchVideoReadModel,
  postVideoAction,
  type VideoFieldValue,
} from "@/lib/client";
import { VIDEO_CORRECTION_RESPONSE_UID, isAiUnavailable } from "@/lib/aiReply";
import { resolveVideoInbound, type VideoInbound } from "@/lib/videoInbound";
import { previewVideoAction } from "@/lib/videoActionPreview";
import { parseCorrectionScript } from "@/lib/correctionScript";
import {
  VIDEO_CONVERSATION,
  VIDEO_CONVERSATION_HIDDEN,
  activeThreadUidFor,
  composerHasBlockingToken,
  composerTokenTone,
  messageExceedsStoredLimit,
  messagesForThread,
  notebookTextForThread,
  quoteInsertText,
  resolveComposerTokensFor,
  threadsForWorkItem,
} from "@/lib/conversationCore";
import { ConversationFileActions } from "./ConversationFileActions";
import { displayVideoValue } from "./videoFormat";
import { Icon } from "@/components/ui/Icon";
import { IconButton } from "@/components/ui/IconButton";
import {
  VIDEO_CONTROL_ACTIONS,
  VIDEO_MANIFEST_FIELDS,
  VIDEO_RUNTIME_FIELDS,
  VIDEO_SCOPE_FIELDS,
  VIDEO_SCORE_FIELDS,
  VIDEO_STATUS_FIELDS,
  VIDEO_VISIBLE_CONTROLS,
} from "./videoControls";
import styles from "./VideoVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

const MESSAGE_MENU: { uid: string; actionUid: string; key: TranslationKey }[] = [
  { uid: "VIDEO-01-MENU-QUOTE", actionUid: "VIDEO-01-ACT-MSG-QUOTE", key: "video.menu.quote" },
  { uid: "VIDEO-01-MENU-CONTINUE", actionUid: "VIDEO-01-ACT-MSG-CONTINUE", key: "video.menu.continue" },
  { uid: "VIDEO-01-MENU-ANALYZE", actionUid: "VIDEO-01-ACT-MSG-ANALYZE", key: "video.menu.analyze" },
  { uid: "VIDEO-01-MENU-DECISION", actionUid: "VIDEO-01-ACT-MSG-DECISION", key: "video.menu.decision" },
  { uid: "VIDEO-01-MENU-BRANCH", actionUid: "VIDEO-01-ACT-MSG-BRANCH", key: "video.menu.branch" },
  { uid: "VIDEO-01-MENU-COPY", actionUid: "VIDEO-01-ACT-MSG-COPY", key: "video.menu.copy" },
];

const SCORE_IDS: Record<string, TranslationKey> = {
  "VIDEO-01-FLD-SCORE-SCRIPT": "video.score_id_script",
  "VIDEO-01-FLD-SCORE-IDENTITY": "video.score_id_identity",
  "VIDEO-01-FLD-SCORE-MOTION": "video.score_id_motion",
  "VIDEO-01-FLD-SCORE-CAMERA": "video.score_id_camera",
  "VIDEO-01-FLD-SCORE-SCENE": "video.score_id_scene",
  "VIDEO-01-FLD-SCORE-TIMING": "video.score_id_timing",
  "VIDEO-01-FLD-SCORE-TECH": "video.score_id_tech",
  "VIDEO-01-FLD-SCORE-ASSET": "video.score_id_asset",
  "VIDEO-01-FLD-SCORE-RIGHTS": "video.score_id_rights",
};

const EMPTY_INBOUND: VideoInbound = {
  ready: false,
  project: "",
  topic: "",
  task: "",
  blueprint: "",
  childLock: "",
  dna: "",
  script: "",
  assetVersion: "",
  filename: "",
  checksum: "",
  instruction: "",
  rights: "",
  naming: "",
};

const CLIENT_FIELDS: string[] = [...VIDEO_VISIBLE_CONTROLS, VIDEO_CORRECTION_RESPONSE_UID, ...VIDEO_CONVERSATION_HIDDEN];

function emptyFields(): VideoFieldValue[] {
  return CLIENT_FIELDS.map((controlUid) => ({ controlUid, value: null }));
}

function Field({
  uid,
  label,
  value,
  loading,
  onAct,
  disabled,
  readonly = false,
}: {
  uid: string;
  label: string;
  value: string | null;
  loading: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
  readonly?: boolean;
}) {
  if (readonly) {
    return (
      <div className={styles.field} data-control-uid={uid}>
        <span className={styles.label}>{label}</span>
        <span className={styles.value}>{displayVideoValue(value, loading)}</span>
      </div>
    );
  }
  return (
    <button type="button" className={styles.field} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayVideoValue(value, loading)}</span>
    </button>
  );
}

export function VideoVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(true);
  const [fields, setFields] = useState<VideoFieldValue[]>(emptyFields);
  const [inbound, setInbound] = useState<VideoInbound>(EMPTY_INBOUND);
  const [compareOn, setCompareOn] = useState(false);
  const [correctionDraft, setCorrectionDraft] = useState("");
  const [tick, setTick] = useState(0);
  const [menu, setMenu] = useState<{ x: number; y: number; ref: string; text: string } | null>(null);
  const fieldsRef = useRef(fields);
  const timelineRef = useRef<HTMLDivElement>(null);
  fieldsRef.current = fields;

  useEffect(() => {
    const node = timelineRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [fields, tick]);

  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    const timer = window.setTimeout(() => window.addEventListener("click", close), 0);
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("click", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [menu]);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    Promise.all([
      fetchVideoReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal),
      fetchCoreReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal).catch(() => null),
      fetchAssetReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal).catch(() => null),
    ])
      .then(([model, core, asset]) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        const resolved = resolveVideoInbound(
          (uid) => core?.fields.find((row) => row.controlUid === uid)?.value ?? null,
          (uid) => asset?.fields.find((row) => row.controlUid === uid)?.value ?? null,
        );
        setInbound(resolved);
        const map = new Map(emptyFields().map((row) => [row.controlUid, row.value] as const));
        if (resolved.ready) {
          for (const row of model.fields) {
            if (row.value != null && row.value !== "") map.set(row.controlUid, row.value);
          }
          map.set("VIDEO-01-FLD-PROJECT", resolved.project);
          map.set("VIDEO-01-FLD-TOPIC", resolved.topic);
          map.set("VIDEO-01-FLD-TASK", resolved.task);
          map.set("VIDEO-01-FLD-BLUEPRINT-REF", resolved.blueprint);
          map.set("VIDEO-01-FLD-DNA-REFS", resolved.dna);
          map.set("VIDEO-01-FLD-SCRIPT-SECTION", resolved.script);
          map.set("VIDEO-01-FLD-ASSET-REFS", resolved.assetVersion);
          map.set("VIDEO-01-FLD-FILENAME-CHECKSUM", [resolved.filename, resolved.checksum].filter(Boolean).join(" / "));
          map.set("VIDEO-01-FLD-RIGHTS", resolved.rights);
          map.set("VIDEO-01-FLD-INSTRUCTION", resolved.instruction);
        }
        setFields(
          CLIENT_FIELDS.map((controlUid) => ({
            controlUid,
            value: map.get(controlUid) ?? null,
          })),
        );
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof VideoClientError ? cause.code : "VIDEO_READ_UNAVAILABLE");
        setAuthorized(false);
        setInbound(EMPTY_INBOUND);
        setFields(emptyFields());
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

  const correctionCandidate = parseCorrectionScript(valueOf(VIDEO_CORRECTION_RESPONSE_UID));
  const correctionBody = correctionCandidate?.script_body
    ? isAiUnavailable(correctionCandidate.script_body)
      ? t("ai.unavailable")
      : correctionCandidate.script_body
    : "";

  const applyPatch = useCallback((patch: Record<string, string>) => {
    setFields((prev) => {
      const map = new Map(prev.map((row) => [row.controlUid, row.value]));
      for (const [uid, value] of Object.entries(patch)) map.set(uid, value);
      return CLIENT_FIELDS.map((controlUid) => ({
        controlUid,
        value: map.has(controlUid) ? (map.get(controlUid) ?? null) : null,
      }));
    });
  }, []);

  const act = useCallback(
    async (controlUid: string, nextValue?: string) => {
      const actionUid = VIDEO_CONTROL_ACTIONS[controlUid];
      if (!actionUid) return;
      const patch = previewVideoAction(
        controlUid,
        actionUid,
        (uid) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null,
        nextValue,
      );
      if (!Object.keys(patch).length) return;
      applyPatch(patch);
      try {
        await postVideoAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, nextValue);
        if (
          actionUid === "VIDEO-01-ACT-CORRECTION-GENERATE" ||
          actionUid === "VIDEO-01-ACT-SEND" ||
          actionUid === "VIDEO-01-ACT-MSG-ANALYZE"
        ) {
          setTick((value) => value + 1);
        }
      } catch {
        // Optimistic projection stays visible when the write path is unbound.
      }
    },
    [applyPatch],
  );

  const insertQuote = useCallback((ref: string, prefix = "") => {
    const piece = quoteInsertText(ref);
    if (!piece && !prefix) return;
    setCorrectionDraft((prev) => {
      const lead = prefix && !prev.includes(prefix) ? `${prefix} ` : "";
      if (!prev) return `${lead}${piece}`.trimStart();
      const gap = /[\s\n]$/.test(prev) ? "" : " ";
      return `${lead}${prev}${gap}${piece}`;
    });
  }, []);

  const sendMessage = useCallback(() => {
    const current = (uid: string) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null;
    if (!activeThreadUidFor(VIDEO_CONVERSATION, current)) return;
    const text = correctionDraft.trim();
    if (messageExceedsStoredLimit(text)) return;
    const tokens = resolveComposerTokensFor(VIDEO_CONVERSATION, text, current);
    if (composerHasBlockingToken(tokens)) return;
    if (!text) return;
    setCorrectionDraft("");
    void act("VIDEO-01-BTN-SEND", text);
  }, [act, correctionDraft]);

  const runMessageAction = useCallback((actionUid: string, messageRef: string, text: string) => {
    setMenu(null);
    if (actionUid === "VIDEO-01-ACT-MSG-QUOTE") {
      insertQuote(messageRef);
      return;
    }
    if (actionUid === "VIDEO-01-ACT-MSG-CONTINUE") {
      insertQuote(messageRef, "繼續討論");
      return;
    }
    if (actionUid === "VIDEO-01-ACT-MSG-COPY") {
      void navigator.clipboard?.writeText(text);
      return;
    }
    const controlUid = MESSAGE_MENU.find((row) => row.actionUid === actionUid)?.uid;
    if (!controlUid) return;
    void act(controlUid, JSON.stringify({ actionUid, messageRef }));
  }, [act, insertQuote]);

  const inboundReady = inbound.ready;
  const evaluated = valueOf("VIDEO-01-BTN-EVALUATE") === "evaluated";
  const confirmed = valueOf("VIDEO-01-BTN-CONFIRM") === "confirmed";
  const locked = valueOf("VIDEO-01-BTN-LOCK") === "locked";
  const correctionOpen = valueOf("VIDEO-01-BTN-MODIFY") === "open";
  const disabled = !inboundReady;
  const generateDisabled = disabled || !correctionDraft.trim();
  const approveDisabled = disabled || correctionCandidate?.status !== "CANDIDATE";
  const executeDisabled = disabled || correctionCandidate?.status !== "APPROVED";
  const currentFields = (uid: string) => valueOf(uid);
  const threadItems = threadsForWorkItem(VIDEO_CONVERSATION, currentFields);
  const activeThread = activeThreadUidFor(VIDEO_CONVERSATION, currentFields) || null;
  const conversation = messagesForThread(valueOf("VIDEO-01-FLD-CORRECTION-MESSAGES"), activeThread ?? "");
  const notebookText = notebookTextForThread(valueOf("VIDEO-01-FLD-CORRECTION-NOTEBOOK"), activeThread ?? "");
  const composerTokens = resolveComposerTokensFor(VIDEO_CONVERSATION, correctionDraft, currentFields);
  const parserBlocked = composerHasBlockingToken(composerTokens);
  const tooLong = messageExceedsStoredLimit(correctionDraft);
  const canSend = Boolean(activeThread) && Boolean(correctionDraft.trim()) && !parserBlocked && !tooLong;
  const tx = (key: TranslationKey) => t(key);
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const dash = displayVideoValue(null, loading);
  const modeValue = valueOf("VIDEO-01-CTL-MODE");
  const modeLabel =
    modeValue === "MANUAL" ? tx("video.mode_manual") : modeValue === "AUTO" ? tx("video.mode_auto") : displayVideoValue(modeValue, loading);
  const compareActive = compareOn || valueOf("VIDEO-01-CTL-COMPARE") === "active";

  return (
    <div
      className={styles.page}
      data-page-uid="VIDEO-01"
      data-page-state={pageState}
      data-component-count="17"
      data-control-count="95"
      aria-label={tx("video.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("video.error")}</div> : null}
      {!loading && !error && authorized && !inboundReady ? (
        <div className={styles.error} role="alert">{tx("video.inbound_blocked")}</div>
      ) : null}

      <section className={`${styles.panel} ${styles.context}`} data-component-uid="VIDEO-01-CMP-CONTEXT">
        <Field uid="VIDEO-01-FLD-PROJECT" label={tx("video.project")} value={valueOf("VIDEO-01-FLD-PROJECT")} loading={loading} onAct={act} disabled={disabled} readonly />
        <Field uid="VIDEO-01-FLD-TOPIC" label={tx("video.topic")} value={valueOf("VIDEO-01-FLD-TOPIC")} loading={loading} onAct={act} disabled={disabled} readonly />
        <Field uid="VIDEO-01-FLD-TASK" label={tx("video.task")} value={valueOf("VIDEO-01-FLD-TASK")} loading={loading} onAct={act} disabled={disabled} readonly />
        <Field uid="VIDEO-01-FLD-STATUS" label={tx("video.status")} value={valueOf("VIDEO-01-FLD-STATUS")} loading={loading} onAct={act} disabled={disabled} readonly />
        <button type="button" className={styles.btn} data-control-uid="VIDEO-01-CTL-MODE" disabled={disabled} onClick={() => void act("VIDEO-01-CTL-MODE")}>
          {tx("video.mode")} {modeLabel}
        </button>
        <div className={styles.stageChip}>
          <span className={styles.label}>{tx("video.current_stage")}</span>
          <span className={styles.value}>{tx("video.stage_generate")}</span>
        </div>
        <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-EXECUTE" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-EXECUTE")}>{tx("video.execute")}</button>
        <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-BLUEPRINT" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-BLUEPRINT")}>{tx("video.view_blueprint")}</button>
        <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-PACKAGE" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-PACKAGE")}>{tx("video.view_package")}</button>
      </section>

      <div className={styles.body}>
        <aside className={`${styles.panel} ${styles.left}`}>
          <section data-component-uid="VIDEO-01-CMP-PRODUCTION-LIST">
            <h2 className={styles.title}>{tx("video.production_list")}</h2>
            <div className={styles.searchRow}>
              <label className={styles.search}>
                <span className={styles.label}>{tx("video.search")}</span>
                <input data-control-uid="VIDEO-01-FLD-SEARCH" disabled={disabled} placeholder={tx("video.search")} defaultValue="" onBlur={() => void act("VIDEO-01-FLD-SEARCH")} />
              </label>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-CTL-FILTER" disabled={disabled} onClick={() => void act("VIDEO-01-CTL-FILTER")}>{tx("video.filter")}</button>
            </div>
            <div className={styles.list} data-control-uid="VIDEO-01-CTL-SHOT-SELECT">
              {[0, 1, 2, 3].map((index) => (
                <button
                  key={index}
                  type="button"
                  className={index === 0 ? `${styles.item} ${styles.itemActive}` : styles.item}
                  disabled={disabled}
                  onClick={() => void act("VIDEO-01-CTL-SHOT-SELECT")}
                >
                  <span>{tx("video.unbound_shot")}</span>
                  <span>{tx("video.shot_ref")} {dash}</span>
                </button>
              ))}
            </div>
          </section>
          <section data-component-uid="VIDEO-01-CMP-BLUEPRINT-BIND">
            <Field uid="VIDEO-01-FLD-BLUEPRINT-REF" label={tx("video.blueprint_ref")} value={valueOf("VIDEO-01-FLD-BLUEPRINT-REF")} loading={loading} onAct={act} disabled={disabled} readonly />
          </section>
          <section data-component-uid="VIDEO-01-CMP-SCRIPT-BIND">
            <Field uid="VIDEO-01-FLD-SCRIPT-SECTION" label={tx("video.script_section")} value={valueOf("VIDEO-01-FLD-SCRIPT-SECTION")} loading={loading} onAct={act} disabled={disabled} readonly />
          </section>
          <section data-component-uid="VIDEO-01-CMP-DNA-BIND">
            <Field uid="VIDEO-01-FLD-DNA-REFS" label={tx("video.dna_refs")} value={valueOf("VIDEO-01-FLD-DNA-REFS")} loading={loading} onAct={act} disabled={disabled} readonly />
          </section>
          <section data-component-uid="VIDEO-01-CMP-ASSET-BIND">
            <Field uid="VIDEO-01-FLD-ASSET-REFS" label={tx("video.asset_refs")} value={valueOf("VIDEO-01-FLD-ASSET-REFS")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="VIDEO-01-FLD-FILENAME-CHECKSUM" label={tx("video.filename_checksum")} value={valueOf("VIDEO-01-FLD-FILENAME-CHECKSUM")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="VIDEO-01-FLD-INSTRUCTION" label={tx("video.instruction")} value={valueOf("VIDEO-01-FLD-INSTRUCTION")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="VIDEO-01-FLD-RIGHTS" label={tx("video.rights")} value={valueOf("VIDEO-01-FLD-RIGHTS")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="VIDEO-01-FLD-INPUT-FINGERPRINT" label={tx("video.input_fingerprint")} value={valueOf("VIDEO-01-FLD-INPUT-FINGERPRINT")} loading={loading} onAct={act} disabled={disabled} readonly />
          </section>
        </aside>

        <main className={`${styles.panel} ${styles.center}`}>
          <section data-component-uid="VIDEO-01-CMP-PREVIEW" className={styles.center}>
            <div className={styles.previewHead} data-component-uid="VIDEO-01-CMP-COMPARE">
              <h2 className={styles.title}>{tx("video.preview")}</h2>
              <button
                type="button"
                className={[styles.btn, compareActive ? "" : styles.active, styles.iconBtn].filter(Boolean).join(" ")}
                data-control-uid="VIDEO-01-CTL-VERSION-A"
                data-tip={tx("video.single")}
                aria-label={tx("video.single")}
                disabled={disabled}
                onClick={() => { setCompareOn(false); void act("VIDEO-01-CTL-VERSION-A"); }}
              >
                <Icon name="single" />
              </button>
              <button
                type="button"
                className={[styles.btn, compareActive ? styles.active : "", styles.iconBtn].filter(Boolean).join(" ")}
                data-control-uid="VIDEO-01-CTL-COMPARE"
                data-tip={tx("video.compare_toggle")}
                aria-label={tx("video.compare_toggle")}
                disabled={disabled}
                onClick={() => { setCompareOn(true); void act("VIDEO-01-CTL-COMPARE"); }}
              >
                <Icon name="compare" />
              </button>
            </div>
            {compareActive ? (
              <div className={styles.compareGrid}>
                <div className={styles.comparePane}>
                  <p className={styles.previewTitle}>{tx("video.version_a")}</p>
                  <span>{tx("video.exact_output_ref")} {dash}</span>
                </div>
                <button type="button" className={styles.comparePane} data-control-uid="VIDEO-01-CTL-VERSION-B" disabled={disabled} onClick={() => void act("VIDEO-01-CTL-VERSION-B")}>
                  <p className={styles.previewTitle}>{tx("video.version_b")}</p>
                  <span>{tx("video.exact_output_ref")} {dash}</span>
                </button>
              </div>
            ) : (
              <div className={styles.preview}>
                <p className={styles.previewTitle}>{tx("video.preview_unbound")}</p>
                <span>{tx("video.exact_output_ref")} {dash}</span>
              </div>
            )}
            <div className={styles.toolbar}>
              <IconButton uid="VIDEO-01-BTN-PLAY" label={tx("video.play")} icon="play" onAct={act} disabled={disabled} className={`${styles.btn} ${styles.iconBtn}`} />
              <Field uid="VIDEO-01-FLD-TIMECODE" label={tx("video.timecode")} value={valueOf("VIDEO-01-FLD-TIMECODE")} loading={loading} onAct={act} disabled={disabled} readonly />
              <input className={styles.seek} type="range" min="0" max="100" defaultValue="0" data-control-uid="VIDEO-01-CTL-SEEK" disabled={disabled} onChange={() => void act("VIDEO-01-CTL-SEEK")} />
              <IconButton uid="VIDEO-01-BTN-VOLUME" label={tx("video.volume")} icon="volume" onAct={act} disabled={disabled} className={`${styles.btn} ${styles.iconBtn}`} />
              <IconButton uid="VIDEO-01-BTN-FULLSCREEN" label={tx("video.fullscreen")} icon="fullscreen" onAct={act} disabled={disabled} className={`${styles.btn} ${styles.iconBtn}`} />
            </div>
            {compareActive ? <p className={styles.note}>{tx("video.compare_note")}</p> : null}
          </section>
        </main>

        <aside className={`${styles.panel} ${styles.right}`}>
          <section data-component-uid="VIDEO-01-CMP-VERSION">
            <h2 className={styles.title}>{tx("video.version")}</h2>
            <Field uid="VIDEO-01-FLD-CURRENT-VERSION" label={tx("video.current_version")} value={valueOf("VIDEO-01-FLD-CURRENT-VERSION")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="VIDEO-01-FLD-CANDIDATE-VERSION" label={tx("video.candidate_version")} value={valueOf("VIDEO-01-FLD-CANDIDATE-VERSION")} loading={loading} onAct={act} disabled={disabled} readonly />
          </section>
          <section data-component-uid="VIDEO-01-CMP-SCORE">
            <Field uid="VIDEO-01-FLD-CRITERIA-VERSION" label={tx("video.criteria_version")} value={valueOf("VIDEO-01-FLD-CRITERIA-VERSION")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="VIDEO-01-FLD-OVERALL-SCORE" label={tx("video.overall_score")} value={valueOf("VIDEO-01-FLD-OVERALL-SCORE")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="VIDEO-01-FLD-ISSUE-SUMMARY" label={tx("video.issue_summary")} value={valueOf("VIDEO-01-FLD-ISSUE-SUMMARY")} loading={loading} onAct={act} disabled={disabled} readonly />
            <button type="button" className={styles.statusBadge} data-control-uid="VIDEO-01-BTN-SCORE-DETAIL" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-SCORE-DETAIL")}>{tx("video.score_detail")}</button>
          </section>
          <section data-component-uid="VIDEO-01-CMP-DECISION">
            <div className={styles.decisionGrid}>
              <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-CONFIRM" disabled={disabled || !evaluated} onClick={() => void act("VIDEO-01-BTN-CONFIRM")}>{tx("video.confirm")}</button>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-MODIFY" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-MODIFY")}>{tx("video.modify")}</button>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-LOCK" disabled={disabled || !confirmed} onClick={() => void act("VIDEO-01-BTN-LOCK")}>{tx("video.lock")}</button>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-HANDOFF" disabled={disabled || !locked} onClick={() => void act("VIDEO-01-BTN-HANDOFF")}>{tx("video.handoff_edit")}</button>
            </div>
          </section>
        </aside>
      </div>

      <section className={`${styles.panel} ${styles.runtime}`} data-component-uid="VIDEO-01-CMP-PROVIDER-RUNTIME">
        <h3 className={styles.sub}>{tx("video.runtime")}</h3>
        <div className={styles.runtimeRow}>
          {VIDEO_RUNTIME_FIELDS.map(([uid, key]) => (
            <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} readonly />
          ))}
        </div>
        <div className={styles.runtimeActions}>
          <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-RETRY" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-RETRY")}>{tx("video.retry")}</button>
          <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-RUNTIME-DETAIL" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-RUNTIME-DETAIL")}>{tx("video.runtime_detail")}</button>
        </div>
      </section>

      <div className={styles.lower}>
        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-CORRECTION-SCOPE" hidden={!correctionOpen}>
          <h3 className={styles.sub}>{tx("video.correction_scope")}</h3>
          <div className={styles.scopeRow}>
            {VIDEO_SCOPE_FIELDS.map(([uid, key]) => (
              <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} readonly />
            ))}
            <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-CONTEXT-BUILD" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-CONTEXT-BUILD")}>{tx("video.context_build")}</button>
          </div>
        </section>

        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-AI-REVISION" hidden={!correctionOpen}>
          <h3 className={styles.sub}>{tx("video.ai_revision")}</h3>
          <div className={styles.composer}>
            <span className={styles.label}>{tx("video.source_script")}</span>
            <span className={styles.value}>{displayVideoValue(correctionCandidate?.exact_source_version, loading)}</span>
          </div>
          <div className={styles.corrActions}>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-GEN-CORRECTION" disabled={generateDisabled} onClick={() => void act("VIDEO-01-BTN-GEN-CORRECTION", correctionDraft.trim() || undefined)}>{tx("video.correction_generate")}</button>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-APPROVE-CORRECTION" disabled={approveDisabled} onClick={() => void act("VIDEO-01-BTN-APPROVE-CORRECTION")}>{tx("video.correction_approve")}</button>
            <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-EXEC-CORRECTION" disabled={executeDisabled} onClick={() => void act("VIDEO-01-BTN-EXEC-CORRECTION")}>{tx("video.correction_execute")}</button>
            <IconButton uid="VIDEO-01-BTN-COMPARE-CORRECTION" label={tx("video.correction_compare")} icon="compare" onAct={act} disabled={disabled || correctionCandidate?.status !== "EXECUTED"} className={`${styles.btn} ${styles.iconBtn}`} />
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-NEW-THREAD" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-NEW-THREAD")}>{tx("video.new_thread")}</button>
            <IconButton uid="VIDEO-01-BTN-ASSISTANT" label={tx("video.assistant_record")} icon="record" onAct={act} disabled={disabled} className={`${styles.btn} ${styles.iconBtn}`} />
          </div>
          <div className={styles.threadsLabel}>{tx("video.threads")}</div>
          <div className={styles.threadList} data-control-uid="VIDEO-01-LST-THREADS">
            {threadItems.length === 0 ? <p className={styles.threadEmpty}>{tx("video.no_threads")}</p> : null}
            {threadItems.map((row) => {
              const selected = activeThread === row.title;
              return (
                <button key={row.title} type="button" className={selected ? `${styles.thread} ${styles.active}` : styles.thread} disabled={disabled} onClick={() => void act("VIDEO-01-LST-THREADS", row.title)}>
                  <span>{row.title}</span>
                </button>
              );
            })}
          </div>
          <div className={styles.messagesHead}>
            <h2 className={styles.title}>{tx("video.messages")}</h2>
            <span>{tx("video.right_click_only")}</span>
          </div>
          <div className={styles.messageTimeline} ref={timelineRef}>
            {conversation.length === 0 ? (
              <p className={styles.threadEmpty}>{tx("video.conversation_empty")}</p>
            ) : (
              conversation.map((row, index) => (
                <article
                  key={row.ref || `${row.role}-${index}`}
                  className={row.role === "user" ? styles.userMessage : styles.assistantMessage}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    if (!row.ref) return;
                    setMenu({ x: event.clientX, y: event.clientY, ref: row.ref, text: row.text });
                  }}
                >
                  <div className={styles.bubbleRole}>
                    {row.role === "user" ? tx("video.user_message") : tx("video.ai_response_n")}
                    {row.alias ? ` @${row.alias}` : ""}
                    {row.route ? ` ${row.route}` : ""}
                    {row.ref ? ` ${row.ref}` : ""}
                    {row.at ? ` ${row.at}` : ""}
                  </div>
                  <p>{row.role === "assistant" && isAiUnavailable(row.text) ? tx("ai.unavailable") : row.text}</p>
                  {row.role === "assistant" ? (
                    <ConversationFileActions text={row.text} accountUid={DEFAULT_ACCOUNT} sessionUid={DEFAULT_SESSION} tx={tx} />
                  ) : null}
                </article>
              ))
            )}
          </div>
          <div className={styles.summaryInline}>
            <span className={styles.summaryLabel}>{tx("video.summary_inline")}</span>
            <p>{notebookText || tx("video.summary_hint")}</p>
          </div>
          <div
            className={menu ? styles.messageMenu : styles.messageMenuHidden}
            hidden={!menu}
            style={menu ? { left: menu.x, top: menu.y } : undefined}
            onClick={(event) => event.stopPropagation()}
          >
            {MESSAGE_MENU.map((item) => (
              <button
                key={item.uid}
                type="button"
                className={styles.menuItem}
                data-control-uid={item.uid}
                data-action-uid={item.actionUid}
                disabled={disabled || !menu}
                onClick={() => menu && runMessageAction(item.actionUid, menu.ref, menu.text)}
              >
                {tx(item.key)}
              </button>
            ))}
          </div>
          <div className={`${styles.composer} ${styles.composerBar}`}>
            <label className={styles.srOnly}>{tx("video.correction_request")}</label>
            <textarea
              data-control-uid="VIDEO-01-TXT-CORRECTION"
              disabled={disabled}
              value={correctionDraft}
              placeholder={tx("video.correction_hint")}
              rows={3}
              onChange={(event) => setCorrectionDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key !== "Enter") return;
                if (event.nativeEvent.isComposing) return;
                if (event.ctrlKey || event.metaKey) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
            />
            <IconButton uid="VIDEO-01-BTN-SEND" label={tooLong ? tx("video.message_too_long") : parserBlocked ? tx("video.parser_blocked") : canSend ? tx("video.send") : tx("video.gate-message")} icon="send" onAct={() => sendMessage()} disabled={disabled || !canSend} className={`${styles.btn} ${styles.iconBtn} ${styles.btnSend}`} />
          </div>
          {composerTokens.length ? (
            <div className={styles.tokenRow} aria-live="polite">
              {composerTokens.map((token, index) => (
                <span key={`${token.raw}-${index}`} className={composerTokenTone(token.kind) === "ok" ? styles.tokenOk : composerTokenTone(token.kind) === "ambiguous" ? styles.tokenAmbiguous : styles.tokenError} data-token-kind={token.kind}>
                  {token.canonical || token.raw}
                  {token.kind === "AMBIGUOUS_REF" ? ` ${tx("video.token_ambiguous")}` : token.kind === "PARSER_ERROR" ? ` ${tx("video.token_invalid")}` : token.canonical && token.canonical !== token.raw ? ` ${tx("video.token_resolved")}` : ""}
                </span>
              ))}
            </div>
          ) : null}
          {tooLong ? <p className={styles.error} role="alert">{tx("video.message_too_long")}</p> : null}
          {parserBlocked ? <p className={styles.error} role="alert">{tx("video.parser_blocked")}</p> : null}
          <div className={styles.aiResponse} data-ai-response-uid={VIDEO_CORRECTION_RESPONSE_UID} aria-live="polite">
            <span className={styles.label}>{tx("video.correction_response")}</span>
            {correctionCandidate ? (
              <>
                <p>{tx("video.correction_status")}: {displayVideoValue(correctionCandidate.status, false)}</p>
                <p>{tx("video.correction_source")}: {displayVideoValue(correctionCandidate.exact_source_version, false)}</p>
                <p>{tx("video.correction_scope_value")}: {displayVideoValue(correctionCandidate.target_scope, false)}</p>
                <p>{tx("video.correction_preserve")}: {displayVideoValue(correctionCandidate.preserve_constraints, false)}</p>
                <p>{correctionBody || tx("video.correction_response_placeholder")}</p>
              </>
            ) : (
              <p>{tx("video.correction_response_placeholder")}</p>
            )}
          </div>
        </section>

        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-EVALUATION">
          <h3 className={styles.sub}>{tx("video.evaluation")}</h3>
          <div className={styles.scoreGrid}>
            {VIDEO_SCORE_FIELDS.map(([uid, key]) => (
              <div key={uid} className={styles.scoreCard} data-control-uid={uid}>
                <strong>{tx(key)}</strong>
                <span className={styles.scoreId}>{tx(SCORE_IDS[uid])}</span>
                <span className={styles.scoreMeta}>{tx("video.score")}：{displayVideoValue(valueOf(uid), loading)} · {tx("video.evidence_short")}：{dash}</span>
                <span className={uid === "VIDEO-01-FLD-SCORE-RIGHTS" ? `${styles.scoreMeta} ${styles.warn}` : styles.scoreMeta}>
                  {uid === "VIDEO-01-FLD-SCORE-RIGHTS" ? tx("video.rights_hard") : `${tx("video.hard_block")}：${dash}`}
                </span>
              </div>
            ))}
          </div>
          <div className={styles.evalActions}>
            <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-EVALUATE" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-EVALUATE")}>{tx("video.evaluate")}</button>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-FINDING" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-FINDING")}>{tx("video.finding")}</button>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-ISSUE-OPEN" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-ISSUE-OPEN")}>{tx("video.issue_open")}</button>
          </div>
        </section>

        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-MANIFEST">
          <h3 className={styles.sub}>{tx("video.finalize_gate")}</h3>
          <div className={styles.gateRow}>
            <div className={styles.gateChip}>{tx("video.gate_confirm")}</div>
            <div className={styles.gateChip}>{tx("video.gate_score")}</div>
            <div className={styles.gateChip}>{tx("video.gate_hard")}</div>
            <div className={styles.gateChip}>{tx("video.gate_manifest")}</div>
            <div className={styles.gateChip}>{tx("video.gate_lock")}</div>
          </div>
          <h3 className={styles.sub}>{tx("video.manifest")}</h3>
          <div className={styles.manifestGrid}>
            {VIDEO_MANIFEST_FIELDS.map(([uid, key]) => (
              <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} readonly />
            ))}
          </div>
          <div className={styles.crossBody}>
            <strong>{tx("video.cross_page")}</strong>
            <span>{tx("video.cross_page_body")}</span>
            <span>{tx("video.cross_page_edit")}</span>
            <span className={styles.warn}>{tx("video.cross_page_warn")}</span>
          </div>
        </section>

        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-STATUS">
          <h3 className={styles.sub}>{tx("video.page_status")}</h3>
          <div className={styles.statusGrid}>
            {VIDEO_STATUS_FIELDS.map(([uid, key]) => (
              <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} readonly />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
