"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import {
  EditClientError,
  fetchEditReadModel,
  fetchVideoReadModel,
  postEditAction,
  type EditFieldValue,
} from "@/lib/client";
import { resolveEditInbound, type EditInbound } from "@/lib/editInbound";
import { previewEditAction } from "@/lib/editActionPreview";
import { parseCorrectionScript } from "@/lib/correctionScript";
import { dialogueTracksInUse, resolveDialogueTimingBinding } from "@/lib/dialogueTimingBinding";
import { isAiUnavailable } from "@/lib/aiReply";
import {
  EDIT_CONVERSATION,
  EDIT_CONVERSATION_HIDDEN,
  activeThreadUidFor,
  composerHasBlockingToken,
  messagesForThread,
  notebookTextForThread,
  quoteInsertText,
  resolveComposerTokensFor,
  threadsForWorkItem,
} from "@/lib/conversationCore";
import { displayEditValue } from "./editFormat";
import { EDIT_CONTROL_ACTIONS, EDIT_VISIBLE_CONTROLS } from "./editControls";
import { Icon, type IconName } from "@/components/ui/Icon";
import { IconButton } from "@/components/ui/IconButton";
import styles from "./EditVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

const MESSAGE_MENU: { uid: string; actionUid: string; key: TranslationKey }[] = [
  { uid: "EDIT-01-MENU-QUOTE", actionUid: "EDIT-01-ACT-MSG-QUOTE", key: "edit.menu.quote" },
  { uid: "EDIT-01-MENU-CONTINUE", actionUid: "EDIT-01-ACT-MSG-CONTINUE", key: "edit.menu.continue" },
  { uid: "EDIT-01-MENU-ANALYZE", actionUid: "EDIT-01-ACT-MSG-ANALYZE", key: "edit.menu.analyze" },
  { uid: "EDIT-01-MENU-DECISION", actionUid: "EDIT-01-ACT-MSG-DECISION", key: "edit.menu.decision" },
  { uid: "EDIT-01-MENU-BRANCH", actionUid: "EDIT-01-ACT-MSG-BRANCH", key: "edit.menu.branch" },
  { uid: "EDIT-01-MENU-COPY", actionUid: "EDIT-01-ACT-MSG-COPY", key: "edit.menu.copy" },
];

const EMPTY_INBOUND: EditInbound = {
  ready: false,
  standalone: false,
  mode: "PROJECT_TASK",
  project: "",
  topic: "",
  task: "",
  blueprint: "",
  childLock: "",
  dna: "",
  script: "",
  naming: "",
  videoVersion: "",
  handoffContract: "",
  sourceVersion: "",
  mediaRefs: "",
};

const CLIENT_FIELDS: string[] = [...EDIT_VISIBLE_CONTROLS, ...EDIT_CONVERSATION_HIDDEN];

function emptyFields(): EditFieldValue[] {
  return CLIENT_FIELDS.map((controlUid) => ({ controlUid, value: null }));
}

const TRACKS = [
  { id: "V1", labelKey: "edit.track_video" as const, clip: "clipV1" },
  { id: "V2", labelKey: "edit.track_overlay" as const, clip: "clipV2" },
  { id: "A1", labelKey: "edit.track_voice" as const, clip: "clipA1" },
  { id: "A2", labelKey: "edit.track_music" as const, clip: "clipA2" },
  { id: "A3", labelKey: "edit.track_sfx" as const, clip: "clipA3" },
  { id: "S1", labelKey: "edit.track_subtitle" as const, clip: "clipS1" },
  { id: "L1", labelKey: "edit.track_lipsync" as const, clip: "clipL1" },
] as const;

function Field({
  uid,
  label,
  value,
  loading,
  onAct,
  disabled,
  readonly = false,
  readout = false,
}: {
  uid: string;
  label: string;
  value: string | null;
  loading: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
  readonly?: boolean;
  readout?: boolean;
}) {
  if (readonly || readout) {
    return (
      <div className={styles.field} data-control-uid={readout ? undefined : uid}>
        <span className={styles.label}>{label}</span>
        <span className={styles.value}>{displayEditValue(value, loading)}</span>
      </div>
    );
  }
  return (
    <button type="button" className={styles.field} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayEditValue(value, loading)}</span>
    </button>
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

export function EditVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(true);
  const [fields, setFields] = useState<EditFieldValue[]>(emptyFields);
  const [inbound, setInbound] = useState<EditInbound>(EMPTY_INBOUND);
  const [correctionDraft, setCorrectionDraft] = useState("");
  const [tick, setTick] = useState(0);
  const [menu, setMenu] = useState<{ x: number; y: number; ref: string; text: string } | null>(null);
  const fieldsRef = useRef(fields);
  fieldsRef.current = fields;

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
      fetchEditReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal),
      fetchVideoReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal).catch(() => null),
    ])
      .then(([model, video]) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        const resolved = resolveEditInbound(
          (uid) => video?.fields.find((row) => row.controlUid === uid)?.value ?? null,
          () => null,
          (uid) => model.fields.find((row) => row.controlUid === uid)?.value ?? null,
        );
        setInbound(resolved);
        const map = new Map(emptyFields().map((row) => [row.controlUid, row.value] as const));
        for (const row of model.fields) {
          if (row.value != null && row.value !== "") map.set(row.controlUid, row.value);
        }
        if (resolved.ready) {
          map.set("EDIT-01-FLD-PROJECT", resolved.project);
          map.set("EDIT-01-FLD-TOPIC", resolved.topic);
          map.set("EDIT-01-FLD-TASK", resolved.task);
          map.set("EDIT-01-FLD-SOURCE-VERSION", resolved.sourceVersion);
          map.set("EDIT-01-LBL-BINDING-FINGERPRINT", resolved.handoffContract);
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
        setError(cause instanceof EditClientError ? cause.code : "EDIT_READ_UNAVAILABLE");
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

  useEffect(() => {
    const value = fields.find((row) => row.controlUid === "EDIT-01-FLD-API-INSTRUCTION")?.value;
    if (value) setCorrectionDraft(value);
  }, [fields]);

  const valueOf = useCallback(
    (controlUid: string) => fields.find((row) => row.controlUid === controlUid)?.value ?? null,
    [fields],
  );

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
      const actionUid = EDIT_CONTROL_ACTIONS[controlUid];
      if (!actionUid) return;
      const patch = previewEditAction(
        controlUid,
        actionUid,
        (uid) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null,
        nextValue,
      );
      if (!Object.keys(patch).length) return;
      applyPatch(patch);
      try {
        await postEditAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, nextValue);
        if (
          actionUid === "EDIT-01-ACT-CORRECTION-CANDIDATE-GENERATE" ||
          actionUid === "EDIT-01-ACT-SEND" ||
          actionUid === "EDIT-01-ACT-MSG-ANALYZE"
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
    if (!activeThreadUidFor(EDIT_CONVERSATION, current)) return;
    const text = correctionDraft.trim();
    const tokens = resolveComposerTokensFor(EDIT_CONVERSATION, text, current);
    if (composerHasBlockingToken(tokens)) return;
    if (!text) return;
    setCorrectionDraft("");
    void act("EDIT-01-BTN-SEND", text);
  }, [act, correctionDraft]);

  const runMessageAction = useCallback((actionUid: string, messageRef: string, text: string) => {
    setMenu(null);
    if (actionUid === "EDIT-01-ACT-MSG-QUOTE") {
      insertQuote(messageRef);
      return;
    }
    if (actionUid === "EDIT-01-ACT-MSG-CONTINUE") {
      insertQuote(messageRef, "繼續討論");
      return;
    }
    if (actionUid === "EDIT-01-ACT-MSG-COPY") {
      void navigator.clipboard?.writeText(text);
      return;
    }
    const controlUid = MESSAGE_MENU.find((row) => row.actionUid === actionUid)?.uid;
    if (!controlUid) return;
    void act(controlUid, JSON.stringify({ actionUid, messageRef }));
  }, [act, insertQuote]);

  const v = (uid: string) => valueOf(uid);
  const standalone = v("EDIT-01-CTL-SOURCE-MODE") === "STANDALONE_UPLOAD";
  const inboundReady = inbound.ready;
  const disabled = !(standalone || inboundReady);
  const correctionOpen = v("EDIT-01-BTN-STAGE-MODIFY") === "returned";
  const correctionCandidate = parseCorrectionScript(v("EDIT-01-PNL-API-CANDIDATE"));
  const generateDisabled = disabled || !correctionOpen || !correctionDraft.trim();
  const approveDisabled = disabled || !correctionOpen || correctionCandidate?.status !== "CANDIDATE";
  const executeDisabled = disabled || !correctionOpen || correctionCandidate?.status !== "APPROVED";
  const dialogueBinding = resolveDialogueTimingBinding((uid) => valueOf(uid));
  const dialogueBlocked = dialogueTracksInUse((uid) => valueOf(uid)) && dialogueBinding.status !== "CURRENT";
  const dialogueWarnKey =
    dialogueBinding.status === "CURRENT"
      ? "edit.dialogue_current"
      : dialogueBinding.status === "STALE"
        ? "edit.dialogue_stale"
        : dialogueBinding.status === "REVERIFY_REQUIRED"
          ? "edit.dialogue_reverify"
          : dialogueBinding.status === "MISMATCH"
            ? "edit.dialogue_mismatch"
            : "edit.dialogue_unbound";
  const currentFields = (uid: string) => valueOf(uid);
  const threadItems = threadsForWorkItem(EDIT_CONVERSATION, currentFields);
  const activeThread = activeThreadUidFor(EDIT_CONVERSATION, currentFields) || null;
  const conversation = messagesForThread(valueOf("EDIT-01-FLD-CORRECTION-MESSAGES"), activeThread ?? "");
  const notebookText = notebookTextForThread(valueOf("EDIT-01-FLD-CORRECTION-NOTEBOOK"), activeThread ?? "");
  const composerTokens = resolveComposerTokensFor(EDIT_CONVERSATION, correctionDraft, currentFields);
  const parserBlocked = composerHasBlockingToken(composerTokens);
  const canSend = Boolean(activeThread) && Boolean(correctionDraft.trim()) && !parserBlocked;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayEditValue(null, loading);
  const modeValue = v("EDIT-01-CTL-EXECUTION-MODE");
  const modeLabel = modeValue === "AUTO" ? tx("edit.auto") : tx("edit.ctl-execution-mode");
  const sourceLabel = v("EDIT-01-CTL-SOURCE-MODE") === "STANDALONE_UPLOAD" ? tx("edit.source_standalone") : tx("edit.source_value");

  return (
    <div
      className={styles.page}
      data-page-uid="EDIT-01"
      data-page-state={pageState}
      data-component-count="24"
      data-control-count="170"
      aria-label={tx("edit.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("edit.error")}</div> : null}

      <section className={`${styles.panel} ${styles.source}`} data-component-uid="EDIT-01-CMP-SOURCE-BAR">
        <Field uid="EDIT-01-CTL-SOURCE-MODE" label={tx("edit.ctl-source-mode")} value={sourceLabel} loading={false} onAct={act} disabled={loading || !authorized} />
        <Field uid="EDIT-01-FLD-PROJECT" label={tx("edit.fld-project")} value={v("EDIT-01-FLD-PROJECT")} loading={loading} onAct={act} disabled={disabled} readonly />
        <Field uid="EDIT-01-FLD-TOPIC" label={tx("edit.fld-topic")} value={v("EDIT-01-FLD-TOPIC")} loading={loading} onAct={act} disabled={disabled} readonly />
        <Field uid="EDIT-01-FLD-TASK" label={tx("edit.fld-task")} value={v("EDIT-01-FLD-TASK")} loading={loading} onAct={act} disabled={disabled} readonly />
        <Field uid="EDIT-01-LBL-CURRENT-STAGE" label={tx("edit.lbl-current-stage")} value={v("EDIT-01-LBL-CURRENT-STAGE") || tx("edit.stage_assembly")} loading={loading} onAct={act} disabled={disabled} readonly />
        <Field uid="EDIT-01-LBL-PENDING-TASK" label={tx("edit.lbl-pending-task")} value={v("EDIT-01-LBL-PENDING-TASK")} loading={loading} onAct={act} disabled={disabled} readonly />
        <div className={styles.modePair}>
          <button type="button" className={styles.btn} disabled={disabled} onClick={() => void act("EDIT-01-CTL-EXECUTION-MODE")}>{tx("edit.auto")}</button>
          <Btn uid="EDIT-01-CTL-EXECUTION-MODE" label={modeLabel} onAct={act} disabled={disabled} primary />
        </div>
        <Btn uid="EDIT-01-BTN-FLOW-START" label={tx("edit.btn-flow-start")} onAct={act} disabled={disabled} primary />
        <Btn uid="EDIT-01-BTN-BLUEPRINT-VIEW" label={tx("edit.btn-blueprint-view")} onAct={act} disabled={disabled} icon="blueprint" />
        <Btn uid="EDIT-01-BTN-PACKAGE-VIEW" label={tx("edit.btn-package-view")} onAct={act} disabled={disabled} icon="package" />
        <Btn uid="EDIT-01-BTN-RETURN-BLUEPRINT" label={tx("edit.btn-return-blueprint")} onAct={act} disabled={disabled} icon="back" />
        <Btn uid="EDIT-01-BTN-MANIFEST-VIEW" label={tx("edit.btn-manifest-view")} onAct={act} disabled={disabled} icon="manifest" />
      </section>

      <div className={styles.body}>
        <aside className={`${styles.panel} ${styles.left}`}>
          <section data-component-uid="EDIT-01-CMP-MEDIA-BIN">
            <h2 className={styles.title}>{tx("edit.media_bin")}</h2>
            <Field uid="EDIT-01-LBL-BINDING-FINGERPRINT" label={tx("edit.locked_blueprint")} value={v("EDIT-01-LBL-BINDING-FINGERPRINT")} loading={loading} onAct={act} disabled={disabled} readout />
            <Field uid="EDIT-01-LBL-CURRENT-SCRIPT-SECTION" label={tx("edit.lbl-current-script-section")} value={v("EDIT-01-LBL-CURRENT-SCRIPT-SECTION")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="EDIT-01-FLD-SOURCE-VERSION" label={tx("edit.fld-source-version")} value={v("EDIT-01-FLD-SOURCE-VERSION")} loading={loading} onAct={act} disabled={disabled} readonly />
            <Field uid="EDIT-01-FLD-VOICE-ASSET" label={tx("edit.fld-voice-asset")} value={v("EDIT-01-FLD-VOICE-ASSET")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="EDIT-01-FLD-MUSIC-ASSET" label={tx("edit.fld-music-asset")} value={v("EDIT-01-FLD-MUSIC-ASSET")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="EDIT-01-FLD-SFX-ASSET" label={tx("edit.fld-sfx-asset")} value={v("EDIT-01-FLD-SFX-ASSET")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="EDIT-01-LBL-SUB-SYNC-BINDING" label={tx("edit.subtitle_binding")} value={v("EDIT-01-LBL-SUB-SYNC-BINDING")} loading={loading} onAct={act} disabled={disabled} readonly />
            <label className={styles.search}>
              <span className={styles.label}>{tx("edit.fld-media-search")}</span>
              <input data-control-uid="EDIT-01-FLD-MEDIA-SEARCH" disabled={disabled} placeholder={tx("edit.fld-media-search")} defaultValue="" onBlur={() => void act("EDIT-01-FLD-MEDIA-SEARCH")} />
            </label>
            <Btn uid="EDIT-01-CTL-MEDIA-TYPE-FILTER" label={tx("edit.ctl-media-type-filter")} onAct={act} disabled={disabled} />
            <div className={styles.list} data-control-uid="EDIT-01-LST-MEDIA">
              <button type="button" className={`${styles.item} ${styles.itemActive}`} disabled={disabled} onClick={() => void act("EDIT-01-LST-MEDIA")}>
                <span>{v("EDIT-01-LST-MEDIA") || tx("edit.unbound_media")}</span>
                <span>{v("EDIT-01-LST-MEDIA") ? tx("edit.session_media") : dash}</span>
              </button>
            </div>
            <div className={styles.toolbar}>
              <Btn uid="EDIT-01-BTN-ADD-MEDIA" label={tx("edit.btn-add-media")} onAct={act} disabled={disabled} icon="upload" />
              <Btn uid="EDIT-01-BTN-UPLOAD-SPEC" label={tx("edit.btn-upload-spec")} onAct={act} disabled={disabled} icon="upload" />
            </div>
            <div className={styles.list} data-control-uid="EDIT-01-LST-IMPORT-QUEUE">
              <div className={styles.item}>
                <span>{v("EDIT-01-LST-IMPORT-QUEUE") || tx("edit.unbound_queue")}</span>
                <span>{v("EDIT-01-LST-IMPORT-QUEUE") ? tx("edit.imported") : dash}</span>
              </div>
            </div>
            <p className={styles.warn}>{tx("edit.asset_picker_forbidden")}</p>
            <p className={styles.note}>{tx("edit.grid_note")}</p>
            <p className={styles.warn}>{tx("edit.exact_refs_only")}</p>
          </section>
        </aside>

        <main className={styles.right}>
          <section className={styles.panel} data-component-uid="EDIT-01-CMP-PREVIEW">
            <h2 className={styles.title}>{tx("edit.preview")}</h2>
            <div className={styles.preview} data-control-uid="EDIT-01-PNL-FINAL-PREVIEW">
              <p className={styles.previewTitle}>{tx("edit.preview_unbound")}</p>
              <span>{tx("edit.exact_source_ref")} {dash}</span>
            </div>
            <div className={styles.transport} data-component-uid="EDIT-01-CMP-TRANSPORT">
              <Btn uid="EDIT-01-BTN-PLAY" label={tx("edit.btn-play")} onAct={act} disabled={disabled} icon="play" />
              <Btn uid="EDIT-01-BTN-PAUSE" label={tx("edit.btn-pause")} onAct={act} disabled={disabled} icon="pause" />
              <Btn uid="EDIT-01-BTN-PREV-FRAME" label={tx("edit.btn-prev-frame")} onAct={act} disabled={disabled} icon="prev" />
              <Btn uid="EDIT-01-BTN-NEXT-FRAME" label={tx("edit.btn-next-frame")} onAct={act} disabled={disabled} icon="next" />
              <div className={styles.timecode}>
                <Field uid="EDIT-01-FLD-TIMECODE" label={tx("edit.fld-timecode")} value={v("EDIT-01-FLD-TIMECODE")} loading={loading} onAct={act} disabled={disabled} />
              </div>
              <Btn uid="EDIT-01-CTL-PLAYBACK-RATE" label={tx("edit.ctl-playback-rate")} onAct={act} disabled={disabled} icon="rate" />
              <Btn uid="EDIT-01-CTL-LOOP" label={tx("edit.loop")} onAct={act} disabled={disabled} icon="loop" />
              <Btn uid="EDIT-01-BTN-MUTE" label={tx("edit.mute")} onAct={act} disabled={disabled} icon="mute" />
              <Btn uid="EDIT-01-BTN-FULLSCREEN" label={tx("edit.btn-fullscreen")} onAct={act} disabled={disabled} icon="fullscreen" />
              <Btn uid="EDIT-01-CTL-VOLUME" label={tx("edit.ctl-volume")} onAct={act} disabled={disabled} icon="volume" />
              <Btn uid="EDIT-01-CTL-AUDIO-MONITOR" label={tx("edit.ctl-audio-monitor")} onAct={act} disabled={disabled} icon="audition" />
              <Btn uid="EDIT-01-CTL-SUBTITLE-TOGGLE" label={tx("edit.ctl-subtitle-toggle")} onAct={act} disabled={disabled} icon="subtitle" />
              <Btn uid="EDIT-01-BTN-SET-IN" label={tx("edit.set_in")} onAct={act} disabled={disabled} icon="set-in" />
              <Btn uid="EDIT-01-BTN-SET-OUT" label={tx("edit.set_out")} onAct={act} disabled={disabled} icon="set-out" />
              <Btn uid="EDIT-01-BTN-CLEAR-RANGE" label={tx("edit.btn-clear-range")} onAct={act} disabled={disabled} icon="clear" />
              <Btn uid="EDIT-01-CTL-IN-OUT" label={tx("edit.ctl-in-out")} onAct={act} disabled={disabled} icon="range" />
            </div>
          </section>

          <section className={styles.panel} data-component-uid="EDIT-01-CMP-MANUAL-TOOLS">
            <div className={styles.toolbar}>
              <Btn uid="EDIT-01-BTN-UNDO" label={tx("edit.btn-undo")} onAct={act} disabled={disabled} icon="undo" />
              <Btn uid="EDIT-01-BTN-REDO" label={tx("edit.btn-redo")} onAct={act} disabled={disabled} icon="redo" />
              <Btn uid="EDIT-01-TOOL-SELECT" label={tx("edit.tool-select")} onAct={act} disabled={disabled} icon="select" />
              <Btn uid="EDIT-01-TOOL-RAZOR" label={tx("edit.tool-razor")} onAct={act} disabled={disabled} icon="razor" />
              <Btn uid="EDIT-01-BTN-SPLIT" label={tx("edit.btn-split")} onAct={act} disabled={disabled} icon="split" />
              <Btn uid="EDIT-01-BTN-TRIM-START" label={tx("edit.btn-trim-start")} onAct={act} disabled={disabled} icon="trim-start" />
              <Btn uid="EDIT-01-BTN-TRIM-END" label={tx("edit.btn-trim-end")} onAct={act} disabled={disabled} icon="trim-end" />
              <Btn uid="EDIT-01-BTN-MOVE" label={tx("edit.btn-move")} onAct={act} disabled={disabled} icon="move" />
              <Btn uid="EDIT-01-BTN-REORDER" label={tx("edit.btn-reorder")} onAct={act} disabled={disabled} icon="reorder" />
              <Btn uid="EDIT-01-BTN-DELETE" label={tx("edit.btn-delete")} onAct={act} disabled={disabled} icon="delete" />
              <Btn uid="EDIT-01-BTN-DUPLICATE" label={tx("edit.btn-duplicate")} onAct={act} disabled={disabled} icon="duplicate" />
              <Btn uid="EDIT-01-CTL-TRANSITION" label={tx("edit.ctl-transition")} onAct={act} disabled={disabled} icon="transition" />
              <Btn uid="EDIT-01-CTL-SPEED" label={tx("edit.ctl-speed")} onAct={act} disabled={disabled} icon="speed" />
              <Btn uid="EDIT-01-BTN-REPLACE" label={tx("edit.btn-replace")} onAct={act} disabled={disabled} icon="replace" />
              <Btn uid="EDIT-01-CTL-CLIP-VOLUME" label={tx("edit.ctl-clip-volume")} onAct={act} disabled={disabled} icon="clip-volume" />
              <Btn uid="EDIT-01-CTL-FADE" label={tx("edit.ctl-fade")} onAct={act} disabled={disabled} icon="fade" />
            </div>
          </section>

          <section className={styles.panel} data-component-uid="EDIT-01-CMP-MINI-TIMELINE">
            <div className={styles.toolbar}>
              <Btn uid="EDIT-01-BTN-MARKER" label={tx("edit.btn-marker")} onAct={act} disabled={disabled} icon="marker" />
              <Btn uid="EDIT-01-CTL-SNAP" label={tx("edit.ctl-snap")} onAct={act} disabled={disabled} primary icon="snap" />
              <Btn uid="EDIT-01-BTN-ZOOM-OUT" label={tx("edit.btn-zoom-out")} onAct={act} disabled={disabled} icon="zoom-out" />
              <Btn uid="EDIT-01-BTN-ZOOM-IN" label={tx("edit.btn-zoom-in")} onAct={act} disabled={disabled} icon="zoom-in" />
              <Btn uid="EDIT-01-BTN-ZOOM-FIT" label={tx("edit.btn-zoom-fit")} onAct={act} disabled={disabled} icon="fit" />
              <span className={styles.note}>{tx("edit.playhead_note")}</span>
            </div>
            <button type="button" className={styles.rail} data-control-uid="EDIT-01-CTL-MINI-TIMELINE" disabled={disabled} onClick={() => void act("EDIT-01-CTL-MINI-TIMELINE")}>{dash}</button>
          </section>

          <section className={styles.panel} data-component-uid="EDIT-01-CMP-TIMELINE">
            <h3 className={styles.sub}>{tx("edit.timeline")}</h3>
            <div className={styles.timeline}>
              <div className={styles.rulerRow} data-component-uid="EDIT-01-CMP-RULER">
                <span />
                <button type="button" className={styles.rulerMarks} data-control-uid="EDIT-01-CTL-RULER" disabled={disabled} onClick={() => void act("EDIT-01-CTL-RULER")}>
                  <span>0s</span><span>5s</span><span>10s</span><span>15s</span><span>20s</span><span>25s</span><span>30s</span>
                </button>
              </div>
              <div data-component-uid="EDIT-01-CMP-MARKER-RAIL">
                <button type="button" className={styles.rail} data-control-uid="EDIT-01-CTL-MARKER-RAIL" disabled={disabled} onClick={() => void act("EDIT-01-CTL-MARKER-RAIL")}>{dash}</button>
              </div>
              {TRACKS.map((track) => (
                <div key={track.id} className={styles.track}>
                  <div className={styles.trackMeta}>
                    <span>{track.id}</span>
                    <span>{tx(track.labelKey)}</span>
                  </div>
                  <div className={styles.trackLane}>
                    <span className={`${styles.clip} ${styles[track.clip]}`}>{tx("edit.exact_ref")}</span>
                  </div>
                </div>
              ))}
              <div className={styles.playheadLine} />
              <button type="button" className={styles.drop} data-control-uid="EDIT-01-CTL-DROP-TIMELINE" disabled={disabled} onClick={() => void act("EDIT-01-CTL-DROP-TIMELINE")}>{tx("edit.ctl-drop-timeline")} {dash}</button>
              <button type="button" className={styles.playheadCtrl} data-control-uid="EDIT-01-CTL-PLAYHEAD" disabled={disabled} onClick={() => void act("EDIT-01-CTL-PLAYHEAD")} aria-label={tx("edit.ctl-playhead")} />
              <div className={styles.toolbar}>
                <Btn uid="EDIT-01-CTL-TRACK-LOCK" label={tx("edit.ctl-track-lock")} onAct={act} disabled={disabled} icon="lock" />
                <Btn uid="EDIT-01-CTL-TRACK-MUTE" label={tx("edit.ctl-track-mute")} onAct={act} disabled={disabled} icon="mute" />
                <Btn uid="EDIT-01-CTL-TRACK-SOLO" label={tx("edit.ctl-track-solo")} onAct={act} disabled={disabled} icon="solo" />
                <Btn uid="EDIT-01-CTL-TRACK-VISIBLE" label={tx("edit.ctl-track-visible")} onAct={act} disabled={disabled} icon="visible" />
              </div>
            </div>
          </section>

          <section className={styles.panel} data-component-uid="EDIT-01-CMP-PRECISION">
            <h3 className={styles.sub}>{tx("edit.precision")}</h3>
            <div className={styles.toolbar}>
              <Field uid="EDIT-01-FLD-CLIP-IN" label={tx("edit.fld-clip-in")} value={v("EDIT-01-FLD-CLIP-IN")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="EDIT-01-FLD-CLIP-OUT" label={tx("edit.fld-clip-out")} value={v("EDIT-01-FLD-CLIP-OUT")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="EDIT-01-FLD-CLIP-POSITION" label={tx("edit.fld-clip-position")} value={v("EDIT-01-FLD-CLIP-POSITION")} loading={loading} onAct={act} disabled={disabled} />
            </div>
          </section>
        </main>
      </div>

      <div className={styles.lower}>
        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-API" hidden={!correctionOpen}>
          <h3 className={styles.sub}>{tx("edit.api")}</h3>
          <Field uid="EDIT-01-FLD-API-SCOPE" label={tx("edit.fld-api-scope")} value={v("EDIT-01-FLD-API-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
          <div className={styles.toolbar}>
            <button type="button" className={styles.btn} data-control-uid="EDIT-01-BTN-CORR-GENERATE" disabled={generateDisabled} onClick={() => void act("EDIT-01-BTN-CORR-GENERATE", correctionDraft.trim() || undefined)}>{tx("edit.btn-corr-generate")}</button>
            <Btn uid="EDIT-01-BTN-CORR-APPROVE" label={tx("edit.btn-corr-approve")} onAct={act} disabled={approveDisabled} />
            <Btn uid="EDIT-01-BTN-CORR-EXECUTE" label={tx("edit.btn-corr-execute")} onAct={act} disabled={executeDisabled} primary />
            <Btn uid="EDIT-01-BTN-API-COMPARE" label={tx("edit.btn-api-compare")} onAct={act} disabled={disabled || correctionCandidate?.status !== "EXECUTED"} icon="compare" />
            <Btn uid="EDIT-01-BTN-API-APPLY" label={tx("edit.btn-api-apply")} onAct={act} disabled={disabled} primary />
            <Btn uid="EDIT-01-BTN-API-DISCARD" label={tx("edit.btn-api-discard")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-API-CANCEL" label={tx("edit.btn-api-cancel")} onAct={act} disabled={disabled} />
            <button type="button" className={styles.btn} data-control-uid="EDIT-01-BTN-NEW-THREAD" disabled={disabled} onClick={() => void act("EDIT-01-BTN-NEW-THREAD")}>{tx("edit.new_thread")}</button>
            <IconButton uid="EDIT-01-BTN-ASSISTANT" label={tx("edit.assistant_record")} icon="record" onAct={act} disabled={disabled} className={`${styles.btn} ${styles.iconBtn}`} />
          </div>
          <div className={styles.threadsLabel}>{tx("edit.threads")}</div>
          <div className={styles.threadList} data-control-uid="EDIT-01-LST-THREADS">
            {threadItems.length === 0 ? <p className={styles.threadEmpty}>{tx("edit.no_threads")}</p> : null}
            {threadItems.map((row) => {
              const selected = activeThread === row.title;
              return (
                <button key={row.title} type="button" className={selected ? `${styles.thread} ${styles.active}` : styles.thread} disabled={disabled} onClick={() => void act("EDIT-01-LST-THREADS", row.title)}>
                  <span>{row.title}</span>
                </button>
              );
            })}
          </div>
          <div className={styles.messagesHead}>
            <h2 className={styles.title}>{tx("edit.messages")}</h2>
            <span>{tx("edit.right_click_only")}</span>
          </div>
          <div className={styles.messageTimeline}>
            {conversation.length === 0 ? (
              <p className={styles.threadEmpty}>{tx("edit.conversation_empty")}</p>
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
                    {row.role === "user" ? tx("edit.user_message") : tx("edit.ai_response_n")}
                    {row.alias ? ` @${row.alias}` : ""}
                    {row.ref ? ` ${row.ref}` : ""}
                    {row.at ? ` ${row.at}` : ""}
                  </div>
                  <p>{row.role === "assistant" && isAiUnavailable(row.text) ? tx("ai.unavailable") : row.text}</p>
                </article>
              ))
            )}
          </div>
          <div className={styles.summaryInline}>
            <span className={styles.summaryLabel}>{tx("edit.summary_inline")}</span>
            <p>{notebookText || tx("edit.summary_hint")}</p>
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
            <span className={styles.srOnly}>{tx("edit.fld-api-instruction")}</span>
            <textarea
              data-control-uid="EDIT-01-FLD-API-INSTRUCTION"
              disabled={disabled}
              value={correctionDraft}
              placeholder={tx("edit.correction_hint")}
              rows={3}
              onChange={(event) => setCorrectionDraft(event.target.value)}
              onBlur={() => void act("EDIT-01-FLD-API-INSTRUCTION", correctionDraft.trim() || undefined)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
            />
            <IconButton uid="EDIT-01-BTN-SEND" label={parserBlocked ? tx("edit.parser_blocked") : canSend ? tx("edit.send") : tx("edit.gate-message")} icon="send" onAct={() => sendMessage()} disabled={disabled || !canSend} className={`${styles.btn} ${styles.iconBtn} ${styles.btnSend}`} />
          </div>
          {parserBlocked ? <p className={styles.error} role="alert">{tx("edit.parser_blocked")}</p> : null}
          <Field uid="EDIT-01-FLD-API-MODEL" label={tx("edit.fld-api-model")} value={v("EDIT-01-FLD-API-MODEL")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-API-PROVIDER" label={tx("edit.fld-api-provider")} value={v("EDIT-01-FLD-API-PROVIDER")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-LBL-API-JOB" label={tx("edit.lbl-api-job")} value={v("EDIT-01-LBL-API-JOB")} loading={loading} onAct={act} disabled={disabled} readonly />
          <div className={styles.previewSm} data-control-uid="EDIT-01-PNL-API-CANDIDATE">
            {correctionCandidate ? (
              <>
                <p>{tx("edit.correction_status")}: {displayEditValue(correctionCandidate.status, false)}</p>
                <p>{tx("edit.correction_source")}: {displayEditValue(correctionCandidate.exact_source_version, false)}</p>
                <p>{tx("edit.correction_scope_value")}: {displayEditValue(correctionCandidate.target_scope, false)}</p>
                <p>{tx("edit.correction_preserve")}: {displayEditValue(correctionCandidate.preserve_constraints, false)}</p>
                <p>{displayEditValue(correctionCandidate.requested_delta, false)}</p>
              </>
            ) : (
              dash
            )}
          </div>
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-MICRO-ADJUSTMENT">
          <h3 className={styles.sub}>{tx("edit.micro_adjustment")}</h3>
          <Field uid="EDIT-01-FLD-CLIP-ID" label={tx("edit.range_clip_track")} value={v("EDIT-01-FLD-CLIP-ID")} loading={loading} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-CLIP-DURATION" label={tx("edit.drag_move")} value={v("EDIT-01-FLD-CLIP-DURATION")} loading={loading} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-TRACK-ID" label={tx("edit.frame_nudge")} value={v("EDIT-01-FLD-TRACK-ID")} loading={loading} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-INSPECTOR-VOLUME" label={tx("edit.volume_fade")} value={v("EDIT-01-FLD-INSPECTOR-VOLUME")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-SUB-TIMECODE" label={tx("edit.subtitle_offset")} value={v("EDIT-01-FLD-SUB-TIMECODE")} loading={loading} onAct={act} disabled={disabled} />
        </section>
      </div>

      <div className={styles.lower3}>
        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-INSPECTOR">
          <h2 className={styles.title}>{tx("edit.inspector")}</h2>
          <div className={styles.tabs}>
            <Btn uid="EDIT-01-TAB-CLIP" label={tx("edit.tab-clip")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-TAB-VOICE" label={tx("edit.tab-voice")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-TAB-AUDIO" label={tx("edit.tab-audio")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-TAB-LIPSYNC" label={tx("edit.tab-lipsync")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-TAB-SUBTITLE" label={tx("edit.tab-subtitle")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-TAB-API" label={tx("edit.tab-api")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-TAB-EVALUATION" label={tx("edit.tab-evaluation")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-TAB-VERSION" label={tx("edit.tab-version")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-TAB-OUTPUT" label={tx("edit.tab-output")} onAct={act} disabled={disabled} />
          </div>
          <Field uid="EDIT-01-FLD-INSPECTOR-FADE-IN" label={tx("edit.selected_context")} value={v("EDIT-01-FLD-INSPECTOR-FADE-IN")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-INSPECTOR-FADE-OUT" label={tx("edit.exact_source_version")} value={v("EDIT-01-FLD-INSPECTOR-FADE-OUT")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-INSPECTOR-SPEED" label={tx("edit.in_out_position")} value={v("EDIT-01-FLD-INSPECTOR-SPEED")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-INSPECTOR-TRANSITION" label={tx("edit.volume_fade_speed")} value={v("EDIT-01-FLD-INSPECTOR-TRANSITION")} loading={loading} onAct={act} disabled={disabled} />
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-VERSION">
          <h3 className={styles.sub}>{tx("edit.version")}</h3>
          <Field uid="EDIT-01-LBL-EVAL-SUMMARY" label={tx("edit.baseline")} value={v("EDIT-01-LBL-EVAL-SUMMARY")} loading={loading} onAct={act} disabled={disabled} readout />
          <div className={styles.list} data-control-uid="EDIT-01-LST-VERSION-HISTORY">
            <button type="button" className={styles.item} disabled={disabled} onClick={() => void act("EDIT-01-LST-VERSION-HISTORY")}>
              <span>{tx("edit.candidate")}</span>
              <span>{dash}</span>
            </button>
          </div>
          <Field uid="EDIT-01-LBL-STAGE-SCORE" label={tx("edit.score")} value={v("EDIT-01-LBL-STAGE-SCORE")} loading={loading} onAct={act} disabled={disabled} readonly />
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-VERSION-SAVE" label={tx("edit.btn-version-save")} onAct={act} disabled={disabled} primary />
            <Btn uid="EDIT-01-BTN-VERSION-RESTORE" label={tx("edit.btn-version-restore")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-VERSION-LOCK" label={tx("edit.btn-version-lock")} onAct={act} disabled={disabled || dialogueBlocked} />
            <Btn uid="EDIT-01-BTN-VERSION-COMPARE" label={tx("edit.diff")} onAct={act} disabled={disabled} icon="compare" />
          </div>
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-OUTPUT">
          <h3 className={styles.sub}>{tx("edit.output")}</h3>
          <Field uid="EDIT-01-LBL-PAGE-STATE" label={tx("edit.stage_job")} value={v("EDIT-01-LBL-PAGE-STATE")} loading={loading} onAct={act} disabled={disabled} readout />
          <Field uid="EDIT-01-LBL-BINDING-FINGERPRINT" label={tx("edit.lbl-binding-fingerprint")} value={v("EDIT-01-LBL-BINDING-FINGERPRINT")} loading={loading} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-LBL-RENDER-JOB" label={tx("edit.lbl-render-job")} value={v("EDIT-01-LBL-RENDER-JOB")} loading={loading} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-LBL-ERROR-STATE" label={tx("edit.output_checksum")} value={v("EDIT-01-LBL-ERROR-STATE")} loading={loading} onAct={act} disabled={disabled} readout />
          <div className={styles.list} data-control-uid="EDIT-01-LST-JOB-STATUS">
            <div className={styles.item}>
              <span>{tx("edit.blocking_error")}</span>
              <span>{dash}</span>
            </div>
          </div>
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-RENDER-SETTINGS" label={tx("edit.btn-render-settings")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-RENDER-EXECUTE" label={tx("edit.btn-render-execute")} onAct={act} disabled={disabled || dialogueBlocked} primary />
            <Btn uid="EDIT-01-BTN-RENDER-CANCEL" label={tx("edit.btn-render-cancel")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-OUTPUT-SAVE" label={tx("edit.btn-output-save")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-DOWNLOAD" label={tx("edit.btn-download")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-HANDOFF-2" label={tx("edit.btn-handoff-2")} onAct={act} disabled={disabled || dialogueBlocked} primary />
          </div>
        </section>
      </div>

      <div className={styles.lower3}>
        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-VOICE">
          <h3 className={styles.sub}>{tx("edit.voice")}</h3>
          <Field uid="EDIT-01-FLD-VOICE-MODEL" label={tx("edit.fld-voice-model")} value={v("EDIT-01-FLD-VOICE-MODEL")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-VOICE-PROVIDER" label={tx("edit.fld-voice-provider")} value={v("EDIT-01-FLD-VOICE-PROVIDER")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-VOICE-SCRIPT" label={tx("edit.fld-voice-script")} value={v("EDIT-01-FLD-VOICE-SCRIPT")} loading={loading} onAct={act} disabled={disabled} />
          <div className={styles.list} data-control-uid="EDIT-01-LST-VOICE-TAKES">
            <div className={styles.item}>
              <span>{tx("edit.unbound_take")}</span>
              <span>{dash}</span>
            </div>
          </div>
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-VOICE-GENERATE" label={tx("edit.btn-voice-generate")} onAct={act} disabled={disabled} primary />
            <Btn uid="EDIT-01-BTN-VOICE-PREVIEW" label={tx("edit.btn-voice-preview")} onAct={act} disabled={disabled} icon="audition" />
            <Btn uid="EDIT-01-BTN-VOICE-COMPARE" label={tx("edit.btn-voice-compare")} onAct={act} disabled={disabled} icon="compare" />
            <Btn uid="EDIT-01-BTN-VOICE-APPLY" label={tx("edit.btn-voice-apply")} onAct={act} disabled={disabled} primary />
          </div>
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-AUDIO">
          <h3 className={styles.sub}>{tx("edit.audio")}</h3>
          <Btn uid="EDIT-01-CTL-MASTER-LEVEL" label={tx("edit.ctl-master-level")} onAct={act} disabled={disabled} />
          <Btn uid="EDIT-01-CTL-TRACK-LEVEL" label={tx("edit.ctl-track-level")} onAct={act} disabled={disabled} />
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-MUSIC-ADD" label={tx("edit.btn-music-add")} onAct={act} disabled={disabled} icon="upload" />
            <Btn uid="EDIT-01-BTN-SFX-ADD" label={tx("edit.btn-sfx-add")} onAct={act} disabled={disabled} icon="upload" />
            <Btn uid="EDIT-01-BTN-MIX-PREVIEW" label={tx("edit.btn-mix-preview")} onAct={act} disabled={disabled} icon="audition" />
            <Btn uid="EDIT-01-BTN-MIX-EXECUTE" label={tx("edit.btn-mix-execute")} onAct={act} disabled={disabled} primary />
          </div>
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-LIPSYNC">
          <h3 className={styles.sub}>{tx("edit.lipsync")}</h3>
          <Field uid="EDIT-01-FLD-LIPSYNC-TARGET" label={tx("edit.fld-lipsync-target")} value={v("EDIT-01-FLD-LIPSYNC-TARGET")} loading={loading} onAct={act} disabled={disabled} />
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-LIPSYNC-PREVIEW" label={tx("edit.btn-lipsync-preview")} onAct={act} disabled={disabled} icon="audition" />
            <Btn uid="EDIT-01-BTN-LIPSYNC-EXECUTE" label={tx("edit.btn-lipsync-execute")} onAct={act} disabled={disabled} primary />
            <Btn uid="EDIT-01-BTN-LIPSYNC-MARK" label={tx("edit.btn-lipsync-mark")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-LIPSYNC-RETRY" label={tx("edit.btn-lipsync-retry")} onAct={act} disabled={disabled} />
          </div>
        </section>
      </div>

      <div className={styles.lower3}>
        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-SUBTITLE">
          <h3 className={styles.sub}>{tx("edit.subtitle")}</h3>
          <label className={styles.composer}>
            <span className={styles.label}>{tx("edit.fld-sub-text")}</span>
            <textarea data-control-uid="EDIT-01-FLD-SUB-TEXT" disabled={disabled} defaultValue="" onBlur={() => void act("EDIT-01-FLD-SUB-TEXT")} />
          </label>
          <Field uid="EDIT-01-FLD-SUB-LANG" label={tx("edit.fld-sub-lang")} value={v("EDIT-01-FLD-SUB-LANG")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-SUB-FORMAT" label={tx("edit.fld-sub-format")} value={v("EDIT-01-FLD-SUB-FORMAT")} loading={loading} onAct={act} disabled={disabled} />
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-SUB-CREATE" label={tx("edit.btn-sub-create")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-SUB-IMPORT" label={tx("edit.btn-sub-import")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-SUB-API-SYNC" label={tx("edit.btn-sub-api-sync")} onAct={act} disabled={disabled} primary />
            <Btn uid="EDIT-01-BTN-SUB-MANUAL-SYNC" label={tx("edit.btn-sub-manual-sync")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-SUB-MERGE" label={tx("edit.btn-sub-merge")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-SUB-SPLIT" label={tx("edit.btn-sub-split")} onAct={act} disabled={disabled} />
          </div>
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-QA">
          <h3 className={styles.sub}>{tx("edit.qa")}</h3>
          <div className={styles.list} data-control-uid="EDIT-01-LST-EVAL-ISSUES">
            <button type="button" className={styles.item} disabled={disabled} onClick={() => void act("EDIT-01-LST-EVAL-ISSUES")}>
              <span>{tx("edit.unbound_issue")}</span>
              <span>{dash}</span>
            </button>
          </div>
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-EVAL-JUMP" label={tx("edit.btn-eval-jump")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-EVAL-LOAD-RANGE" label={tx("edit.btn-eval-load-range")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-EVAL-EVIDENCE" label={tx("edit.btn-eval-evidence")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-EVAL-RECHECK-SELECTED" label={tx("edit.btn-eval-recheck-selected")} onAct={act} disabled={disabled || dialogueBlocked} primary />
            <Btn uid="EDIT-01-BTN-EVAL-RECHECK-FULL" label={tx("edit.btn-eval-recheck-full")} onAct={act} disabled={disabled || dialogueBlocked} />
          </div>
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-STAGE-RAIL">
          <h3 className={styles.sub}>{tx("edit.stage_rail")}</h3>
          <div className={styles.gateList}>
            <div className={styles.gateItem}>{tx("edit.gate_01")}</div>
            <div className={styles.gateItem}>{tx("edit.gate_02")}</div>
            <div className={styles.gateItem}>{tx("edit.gate_03")}</div>
            <div className={styles.gateItem}>{tx("edit.gate_04")}</div>
            <div className={styles.gateItem}>{tx("edit.gate_05")}</div>
            <div className={styles.gateItem}>{tx("edit.gate_06")}</div>
          </div>
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-STAGE-CONFIRM" label={tx("edit.btn-stage-confirm")} onAct={act} disabled={disabled} primary />
            <Btn uid="EDIT-01-BTN-STAGE-MODIFY" label={tx("edit.btn-stage-modify")} onAct={act} disabled={disabled} />
          </div>
          <p className={styles.warn}>{tx("edit.finalize_warn")}</p>
        </section>
      </div>

      <div className={styles.lower}>
        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-DIALOGUE-BINDING">
          <h3 className={styles.sub}>{tx("edit.dialogue_binding")}</h3>
          <Field uid="EDIT-01-LBL-LIPSYNC-SYNC-BINDING" label={tx("edit.lbl-lipsync-sync-binding")} value={v("EDIT-01-LBL-LIPSYNC-SYNC-BINDING")} loading={loading} onAct={act} disabled={disabled} readonly />
          <div className={styles.dialogueCard}>
            <p className={styles.warn}>{tx(dialogueWarnKey)}</p>
          </div>
        </section>
        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-STAGE-EVALUATION">
          <h3 className={styles.sub}>{tx("edit.stage_evaluation")}</h3>
          <Field uid="EDIT-01-LBL-EVAL-SUMMARY" label={tx("edit.lbl-eval-summary")} value={v("EDIT-01-LBL-EVAL-SUMMARY")} loading={loading} onAct={act} disabled={disabled} readonly />
        </section>
        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-STATUS">
          <h3 className={styles.sub}>{tx("edit.status")}</h3>
          <Field uid="EDIT-01-LBL-PAGE-STATE" label={tx("edit.lbl-page-state")} value={v("EDIT-01-LBL-PAGE-STATE")} loading={loading} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-LBL-ERROR-STATE" label={tx("edit.lbl-error-state")} value={v("EDIT-01-LBL-ERROR-STATE")} loading={loading} onAct={act} disabled={disabled} readonly />
        </section>
      </div>
    </div>
  );
}
