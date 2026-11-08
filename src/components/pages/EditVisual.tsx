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
import {
  EDIT_CONVERSATION,
  EDIT_CONVERSATION_HIDDEN,
  activeThreadUidFor,
  composerHasBlockingToken,
  composerTokenTone,
  messageExceedsStoredLimit,
  lastUserText,
  messagesForThread,
  notebookTextForThread,
  quoteInsertText,
  resolveComposerTokensFor,
  threadsForWorkItem,
} from "@/lib/conversationCore";
import { generationStatusKey, type ConversationTaskStatus } from "@/lib/conversationTask";
import { ConversationMarkdown } from "./ConversationMarkdown";
import { ConversationMessageBody } from "./ConversationMessageBody";
import { displayEditValue } from "./editFormat";
import { EDIT_CONTROL_ACTIONS, EDIT_VISIBLE_CONTROLS } from "./editControls";
import {
  addMarker,
  clearRange,
  deleteSelected,
  dragClipTo,
  duplicateSelected,
  emptyTimeline,
  formatTimecode,
  importClip,
  jumpToNearestMarker,
  moveSelected,
  patchSelected,
  redo,
  reorderSelected,
  replaceSelected,
  razorSplitAt,
  restoreVersion,
  saveVersion,
  seek as seekTimeline,
  selectedClip,
  selectClip,
  setRangeIn,
  setRangeOut,
  setTool,
  splitSelected,
  stepFrame,
  timecodeToSeconds,
  timelineEnd,
  toggleTrackFlag,
  trimSelectedEnd,
  trimSelectedStart,
  type TimelineState,
  undo,
  zoomFit,
  zoomIn,
  zoomOut,
} from "@/lib/editTimeline";
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

function parseMediaRefs(raw: string | null): string[] {
  const value = (raw ?? "").trim();
  if (!value) return [];
  if (value.startsWith("[")) {
    try {
      const parsed: unknown = JSON.parse(value);
      if (Array.isArray(parsed)) {
        const items = parsed.filter((row): row is string => typeof row === "string" && row.trim().length > 0).map((row) => row.trim());
        if (items.length) return items;
      }
    } catch {
      // fall through to separator parsing
    }
  }
  const parts = value.split(/[,;\n]+/).map((row) => row.trim()).filter(Boolean);
  return parts.length ? parts : [value];
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
  const [generating, setGenerating] = useState(false);
  const [streamDrafts, setStreamDrafts] = useState<Record<string, string>>({});
  const [streamStatus, setStreamStatus] = useState<ConversationTaskStatus | null>(null);
  const [tl, setTl] = useState<TimelineState>(emptyTimeline);
  const [playing, setPlaying] = useState(false);
  const [rateIndex, setRateIndex] = useState(0);
  const [previewMuted, setPreviewMuted] = useState(false);
  const [masterVolumeIndex, setMasterVolumeIndex] = useState(0);
  const [subtitleOn, setSubtitleOn] = useState(true);
  const [monitorOn, setMonitorOn] = useState(false);
  const [loopOn, setLoopOn] = useState(false);
  const [snapOn, setSnapOn] = useState(false);
  const [mediaFilter, setMediaFilter] = useState(false);
  const [mixPreviewOn, setMixPreviewOn] = useState(false);
  const [mixResult, setMixResult] = useState<string | null>(null);
  const [masterLevelDb, setMasterLevelDb] = useState(0);
  const [trackLevelDb, setTrackLevelDb] = useState(0);
  const [transitionIndex, setTransitionIndex] = useState(0);
  const [speedIndex, setSpeedIndex] = useState(0);
  const [volumeIndex, setVolumeIndex] = useState(0);
  const [mediaQuery, setMediaQuery] = useState("");
  const [selectedMedia, setSelectedMedia] = useState<string | null>(null);
  const [subTextDraft, setSubTextDraft] = useState("");
  const [timecodeDraft, setTimecodeDraft] = useState<string | null>(null);
  const [timecodeInvalid, setTimecodeInvalid] = useState(false);
  const [dragging, setDragging] = useState<{ clipId: string; track: string; offsetSec: number; currentSec: number; moved: boolean } | null>(null);
  const [renderJobs, setRenderJobs] = useState<{ id: string; progress: number; status: "running" | "completed" | "cancelled" }[]>([]);
  const [autoNote, setAutoNote] = useState<string | null>(null);
  const [autoMode, setAutoMode] = useState(false);

  const laneClickSeconds = useCallback((event: React.MouseEvent<HTMLElement> | { clientX: number; currentTarget: HTMLElement }) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0;
    return Math.max(0, ratio * timelineEnd(tlRef.current));
  }, []);
  const [versionCompareNote, setVersionCompareNote] = useState<string | null>(null);
  const tlRef = useRef(tl);
  const rateRef = useRef(rateIndex);
  const loopRef = useRef(loopOn);
  const playingRef = useRef(playing);
  const fieldsRef = useRef(fields);
  const timelineRef = useRef<HTMLDivElement>(null);
  const sendAbortRef = useRef<AbortController | null>(null);
  const expectStreamRefreshRef = useRef(false);
  fieldsRef.current = fields;
  tlRef.current = tl;
  rateRef.current = rateIndex;
  loopRef.current = loopOn;
  playingRef.current = playing;

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setTl((prev) => {
        const end = timelineEnd(prev);
        const next = prev.playhead + 0.1 * [1, 1.5, 2, 0.5][rateRef.current];
        if (next >= end) {
          if (loopRef.current) return { ...prev, playhead: 0 };
          window.setTimeout(() => setPlaying(false), 0);
          return { ...prev, playhead: end };
        }
        return { ...prev, playhead: next };
      });
    }, 100);
    return () => window.clearInterval(id);
  }, [playing]);

  const run = useCallback((fn: (state: TimelineState) => TimelineState) => {
    setTl((prev) => fn(prev));
  }, []);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (event: MouseEvent) => {
      const lane = document.querySelector(`[data-drag-lane="${dragging.track}"]`) as HTMLElement | null;
      if (!lane) return;
      const rect = lane.getBoundingClientRect();
      const ratio = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0;
      const at = Math.max(0, ratio * timelineEnd(tlRef.current));
      setDragging((prev) => (prev ? { ...prev, currentSec: at, moved: true } : prev));
    };
    const onUp = () => {
      setDragging((prev) => {
        if (prev?.moved) {
          const start = Math.max(0, prev.currentSec - prev.offsetSec);
          setTl((state) => dragClipTo(state, prev.clipId, start));
        }
        return null;
      });
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragging]);

  useEffect(() => {
    const node = timelineRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [fields, tick, streamDrafts]);

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
        if (cancelled) {
          if (expectStreamRefreshRef.current) {
            expectStreamRefreshRef.current = false;
            setGenerating(false);
            setStreamDrafts({});
            setStreamStatus(null);
          }
          return;
        }
        setLoading(false);
        if (expectStreamRefreshRef.current) {
          expectStreamRefreshRef.current = false;
          setGenerating(false);
          setStreamDrafts({});
          setStreamStatus(null);
        }
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
      return CLIENT_FIELDS.map((controlUid) => ({
        controlUid,
        value: map.has(controlUid) ? (map.get(controlUid) ?? null) : null,
      }));
    });
  }, []);

  const act = useCallback(
    async (controlUid: string, nextValue?: string): Promise<Record<string, string>> => {
      const actionUid = EDIT_CONTROL_ACTIONS[controlUid];
      if (!actionUid) return {};
      const generatingTurn = actionUid === "EDIT-01-ACT-SEND" || actionUid === "EDIT-01-ACT-MSG-ANALYZE";
      if (generatingTurn && (sendAbortRef.current || generating)) return {};
      const patch = previewEditAction(
        controlUid,
        actionUid,
        (uid) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null,
        nextValue,
      );
      if (!Object.keys(patch).length) return {};
      applyPatch(patch);
      const controller = generatingTurn ? new AbortController() : null;
      if (controller) {
        sendAbortRef.current = controller;
        setGenerating(true);
        setStreamDrafts({});
        setStreamStatus("OPEN");
      }
      try {
        await postEditAction(
          DEFAULT_ACCOUNT,
          controlUid,
          actionUid,
          DEFAULT_SESSION,
          nextValue,
          controller?.signal,
          controller
            ? {
                token: (text, alias) =>
                  setStreamDrafts((prev) => {
                    const key = alias?.trim() || "_";
                    return { ...prev, [key]: (prev[key] ?? "") + text };
                  }),
                status: (status) => setStreamStatus(status),
              }
            : undefined,
        );
        if (generatingTurn) expectStreamRefreshRef.current = true;
        setTick((value) => value + 1);
      } catch {
        if (generatingTurn) expectStreamRefreshRef.current = true;
        setTick((value) => value + 1);
      } finally {
        if (controller && sendAbortRef.current === controller) sendAbortRef.current = null;
      }
      return patch;
    },
    [applyPatch, generating],
  );

  const startRender = useCallback(() => {
    renderDoneRef.current = false;
    setRenderJobs((prev) => [...prev, { id: `RND-${String(prev.length + 1).padStart(3, "0")}`, progress: 0, status: "running" }]);
    setAutoNote(null);
  }, []);
  const cancelRender = useCallback(() => {
    setRenderJobs((prev) => prev.map((job) => (job.status === "running" ? { ...job, status: "cancelled" } : job)));
  }, []);

  const actRef = useRef(act);
  actRef.current = act;
  const autoModeRef = useRef(autoMode);
  autoModeRef.current = autoMode;
  const renderJobsRef = useRef(renderJobs);
  renderJobsRef.current = renderJobs;
  const renderDoneRef = useRef(false);

  useEffect(() => {
    if (!renderJobs.some((job) => job.status === "running")) return;
    const timer = setInterval(() => {
      setRenderJobs((prev) =>
        prev.map((job) => {
          if (job.status !== "running") return job;
          const next = job.progress + 7 + Math.round(Math.random() * 8);
          if (next >= 100) return { ...job, progress: 100, status: "completed" };
          return { ...job, progress: next };
        }),
      );
    }, 320);
    return () => clearInterval(timer);
  }, [renderJobs]);

  useEffect(() => {
    const anyCompleted = renderJobs.some((job) => job.status === "completed");
    if (!anyCompleted || renderDoneRef.current) return;
    renderDoneRef.current = true;
    if (autoModeRef.current) {
      void actRef.current("EDIT-01-BTN-OUTPUT-SAVE").then((patch) => {
        if (patch["EDIT-01-BTN-OUTPUT-SAVE"] === "saved") setAutoNote(t("edit.render_auto_saved"));
      });
    } else {
      setAutoNote(null);
    }
  }, [renderJobs]);

  const runAutoStageConfirm = useCallback(() => {
    setTimeout(() => {
      const flow = fieldsRef.current.find((row) => row.controlUid === "EDIT-01-BTN-FLOW-START")?.value;
      if (tlRef.current.clips.length && flow === "running") {
        void actRef.current("EDIT-01-BTN-STAGE-CONFIRM").then((patch) => {
          if (patch["EDIT-01-BTN-STAGE-CONFIRM"] === "confirmed") setAutoNote(t("edit.render_auto_stage"));
        });
      }
    }, 700);
  }, []);

  const toggleMode = useCallback(() => {
    void actRef.current("EDIT-01-CTL-EXECUTION-MODE").then((patch) => {
      const next = patch["EDIT-01-CTL-EXECUTION-MODE"];
      setAutoMode(next === "AUTO");
      if (next === "AUTO") runAutoStageConfirm();
    });
  }, [runAutoStageConfirm]);

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
    if (sendAbortRef.current) {
      sendAbortRef.current.abort();
      return;
    }
    if (generating) return;
    const current = (uid: string) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null;
    if (!activeThreadUidFor(EDIT_CONVERSATION, current)) return;
    const text = correctionDraft.trim();
    if (messageExceedsStoredLimit(text)) return;
    const tokens = resolveComposerTokensFor(EDIT_CONVERSATION, text, current);
    if (composerHasBlockingToken(tokens)) return;
    if (!text) return;
    setCorrectionDraft("");
    void act("EDIT-01-BTN-SEND", text);
  }, [act, correctionDraft, generating]);

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
    if (generating || sendAbortRef.current) return;
    const controlUid = MESSAGE_MENU.find((row) => row.actionUid === actionUid)?.uid;
    if (!controlUid) return;
    void act(controlUid, JSON.stringify({ actionUid, messageRef }));
  }, [act, generating, insertQuote]);

  const v = (uid: string) => valueOf(uid);
  const mediaItems = (() => {
    const refs = parseMediaRefs(inbound.mediaRefs);
    if (refs.length) return refs;
    const queue = v("EDIT-01-LST-IMPORT-QUEUE");
    return queue ? [queue] : ["session-media"];
  })();
  const filteredMedia = mediaItems.filter((ref) => !mediaQuery || ref.toLowerCase().includes(mediaQuery.toLowerCase()));
  const activeMedia = selectedMedia && mediaItems.includes(selectedMedia) ? selectedMedia : mediaItems[0];
  const mediaLabel = activeMedia;
  const previewClip = tl.clips.find(
    (clip) => tl.playhead >= clip.start && tl.playhead <= clip.start + (clip.outPoint - clip.inPoint),
  ) ?? null;
  const previewRef = useRef<HTMLDivElement | null>(null);
  const toggleFullscreen = useCallback(() => {
    const node = previewRef.current;
    if (!node) return;
    if (document.fullscreenElement) void document.exitFullscreen();
    else void node.requestFullscreen?.();
  }, []);
  const sel = selectedClip(tl);
  const tlEnd = timelineEnd(tl);
  const pxPerSec = 24 * tl.zoom;
  const runAct = useCallback(
    (fn: (state: TimelineState) => TimelineState, controlUid: string, nextValue?: string) => {
      run(fn);
      void act(controlUid, nextValue);
    },
    [act, run],
  );
  const runOnly = useCallback(
    (fn: (state: TimelineState) => TimelineState, controlUid: string) => {
      run(fn);
      void act(controlUid);
    },
    [act, run],
  );
  const seekFromEvent = useCallback(
    (event: React.MouseEvent<HTMLElement>, actUid?: string) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const ratio = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0;
      const at = ratio * timelineEnd(tlRef.current);
      run((state) => seekTimeline(state, at));
      if (actUid) void act(actUid, String(Math.round(at * 100) / 100));
    },
    [act, run],
  );
  const trackClick = useCallback(
    (event: React.MouseEvent<HTMLElement>, track: string) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const ratio = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0;
      const at = ratio * timelineEnd(tlRef.current);
      if (tlRef.current.tool === "razor") run((state) => razorSplitAt(state, track as never, at));
      else run((state) => seekTimeline(state, at));
    },
    [run],
  );
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
  const tooLong = messageExceedsStoredLimit(correctionDraft);
  const canSend = Boolean(activeThread) && Boolean(correctionDraft.trim()) && !parserBlocked && !tooLong;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayEditValue(null, loading);
  const modeValue = v("EDIT-01-CTL-EXECUTION-MODE");
  const modeLabel = modeValue === "AUTO" ? tx("edit.auto") : tx("edit.ctl-execution-mode");
  const activeJob = [...renderJobs].reverse().find((job) => job.status === "running") ?? renderJobs[renderJobs.length - 1] ?? null;
  const renderLabel = activeJob
    ? activeJob.status === "running"
      ? `${tx("edit.job_running")} ${activeJob.progress}%`
      : activeJob.status === "completed"
        ? tx("edit.job_completed")
        : tx("edit.job_cancelled")
    : v("EDIT-01-LBL-RENDER-JOB");
  const sourceLabel = v("EDIT-01-CTL-SOURCE-MODE") === "STANDALONE_UPLOAD" ? tx("edit.source_standalone") : tx("edit.source_value");

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) return;
      if (disabled || sendAbortRef.current || generating) return;
      const type = (key: string, ctrl: boolean) => {
        switch (key) {
          case " ": return () => setPlaying((prev) => !prev);
          case "Delete":
          case "Backspace": return () => run(deleteSelected);
          case "ArrowLeft": return () => run((state) => stepFrame(state, -1));
          case "ArrowRight": return () => run((state) => stepFrame(state, 1));
          case "i": case "I": return () => run(setRangeIn);
          case "o": case "O": return () => run(setRangeOut);
          case "m": case "M": return () => run((state) => addMarker(state, mediaLabel));
          case "z": case "Z": return ctrl ? () => (event.shiftKey ? run(redo) : run(undo)) : null;
          case "y": case "Y": return ctrl ? () => run(redo) : null;
          case "+": case "=": return () => run(zoomIn);
          case "-": case "_": return () => run(zoomOut);
          default: return null;
        }
      };
      const handler = type(event.key, event.ctrlKey || event.metaKey);
      if (handler) {
        event.preventDefault();
        handler();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [disabled, generating, mediaLabel, run]);

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
          <button type="button" className={styles.btn} disabled={disabled} onClick={toggleMode}>{tx("edit.auto")}</button>
          <Btn uid="EDIT-01-CTL-EXECUTION-MODE" label={modeLabel} onAct={toggleMode} disabled={disabled} primary />
        </div>
        <Btn uid="EDIT-01-BTN-FLOW-START" label={tx("edit.btn-flow-start")} onAct={() => { void act("EDIT-01-BTN-FLOW-START").then((patch) => { if (patch["EDIT-01-BTN-FLOW-START"] === "running" && autoModeRef.current) runAutoStageConfirm(); }); }} disabled={disabled} primary />
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
              <input data-control-uid="EDIT-01-FLD-MEDIA-SEARCH" disabled={disabled} placeholder={tx("edit.fld-media-search")} value={mediaQuery} onChange={(event) => setMediaQuery(event.target.value)} onBlur={() => void act("EDIT-01-FLD-MEDIA-SEARCH", mediaQuery || undefined)} />
            </label>
            <Btn uid="EDIT-01-CTL-MEDIA-TYPE-FILTER" label={`${tx("edit.ctl-media-type-filter")}${mediaFilter ? ":on" : ""}`} onAct={() => { setMediaFilter((prev) => !prev); void act("EDIT-01-CTL-MEDIA-TYPE-FILTER"); }} disabled={disabled} />
            <div className={styles.list} data-control-uid="EDIT-01-LST-MEDIA">
              {(mediaFilter ? filteredMedia : filteredMedia.slice(0, 8)).map((ref) => (
                <button
                  key={ref}
                  type="button"
                  className={ref === activeMedia ? `${styles.item} ${styles.itemActive}` : styles.item}
                  disabled={disabled}
                  onClick={() => { setSelectedMedia(ref); void act("EDIT-01-LST-MEDIA", ref); }}
                >
                  <span>{ref}</span>
                  <span>{tx("edit.session_media")}</span>
                </button>
              ))}
              {!filteredMedia.length ? (
                <button type="button" className={styles.item} disabled={disabled} onClick={() => void act("EDIT-01-LST-MEDIA")}>
                  <span>{tx("edit.unbound_media")}</span>
                  <span>{dash}</span>
                </button>
              ) : null}
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
            <div ref={previewRef} className={styles.previewShell}>
            <div className={styles.preview} data-control-uid="EDIT-01-PNL-FINAL-PREVIEW">
              {previewClip ? (
                <>
                  <p className={styles.previewTitle}>{previewClip.label}</p>
                  <span>{tx("edit.preview_playing")}: {formatTimecode(tl.playhead)} · {previewClip.start.toFixed(1)}s → {(previewClip.outPoint - previewClip.inPoint).toFixed(1)}s</span>
                  <div className={styles.previewProgress}>
                    <span style={{ width: `${Math.min(100, Math.max(0, ((tl.playhead - previewClip.start) / Math.max(0.1, previewClip.outPoint - previewClip.inPoint)) * 100))}%` }} />
                  </div>
                </>
              ) : (
                <>
                  <p className={styles.previewTitle}>{tx("edit.preview_unbound")}</p>
                  <span>{tx("edit.exact_source_ref")} {dash}</span>
                </>
              )}
            </div>
            </div>
            <div className={styles.transport} data-component-uid="EDIT-01-CMP-TRANSPORT">
              <Btn uid="EDIT-01-BTN-PLAY" label={tx("edit.btn-play")} onAct={() => { setPlaying(true); void act("EDIT-01-BTN-PLAY"); }} disabled={disabled} icon="play" />
              <Btn uid="EDIT-01-BTN-PAUSE" label={tx("edit.btn-pause")} onAct={() => { setPlaying(false); void act("EDIT-01-BTN-PAUSE"); }} disabled={disabled} icon="pause" />
              <Btn uid="EDIT-01-BTN-PREV-FRAME" label={tx("edit.btn-prev-frame")} onAct={() => { setPlaying(false); runOnly((state) => stepFrame(state, -1), "EDIT-01-BTN-PREV-FRAME"); }} disabled={disabled} icon="prev" />
              <Btn uid="EDIT-01-BTN-NEXT-FRAME" label={tx("edit.btn-next-frame")} onAct={() => { setPlaying(false); runOnly((state) => stepFrame(state, 1), "EDIT-01-BTN-NEXT-FRAME"); }} disabled={disabled} icon="next" />
              <div className={styles.timecode}>
                <span className={styles.label}>{tx("edit.fld-timecode")}</span>
                <input
                  data-control-uid="EDIT-01-FLD-TIMECODE"
                  disabled={disabled}
                  value={timecodeDraft ?? formatTimecode(tl.playhead)}
                  onChange={(event) => { setTimecodeDraft(event.target.value); setTimecodeInvalid(false); }}
                  onBlur={() => {
                    if (timecodeDraft == null) return;
                    const seconds = timecodeToSeconds(timecodeDraft);
                    if (seconds == null) {
                      setTimecodeInvalid(true);
                    } else {
                      run((state) => seekTimeline(state, seconds));
                      void act("EDIT-01-FLD-TIMECODE", timecodeDraft);
                    }
                    setTimecodeDraft(null);
                  }}
                  onKeyDown={(event) => { if (event.key === "Enter") (event.target as HTMLInputElement).blur(); }}
                />
                {timecodeInvalid ? <span className={styles.value}>{tx("edit.timecode_invalid")}</span> : null}
              </div>
              <Btn uid="EDIT-01-CTL-PLAYBACK-RATE" label={`${tx("edit.ctl-playback-rate")} x${[1, 1.5, 2, 0.5][rateIndex]}`} onAct={() => { setRateIndex((prev) => (prev + 1) % 4); void act("EDIT-01-CTL-PLAYBACK-RATE"); }} disabled={disabled} icon="rate" />
              <Btn uid="EDIT-01-CTL-LOOP" label={tx("edit.loop")} onAct={() => { setLoopOn((prev) => !prev); void act("EDIT-01-CTL-LOOP"); }} disabled={disabled} icon="loop" />
              <Btn uid="EDIT-01-BTN-MUTE" label={tx("edit.mute")} onAct={() => { setPreviewMuted((prev) => !prev); void act("EDIT-01-BTN-MUTE"); }} disabled={disabled} icon="mute" />
              <Btn uid="EDIT-01-BTN-FULLSCREEN" label={tx("edit.btn-fullscreen")} onAct={() => { toggleFullscreen(); void act("EDIT-01-BTN-FULLSCREEN"); }} disabled={disabled} icon="fullscreen" />
              <Btn uid="EDIT-01-CTL-VOLUME" label={`${tx("edit.ctl-volume")} ${[100, 75, 50, 25][masterVolumeIndex]}%`} onAct={() => { setMasterVolumeIndex((prev) => (prev + 1) % 4); void act("EDIT-01-CTL-VOLUME"); }} disabled={disabled} icon="volume" />
              <Btn uid="EDIT-01-CTL-AUDIO-MONITOR" label={tx("edit.ctl-audio-monitor")} onAct={() => { setMonitorOn((prev) => !prev); void act("EDIT-01-CTL-AUDIO-MONITOR"); }} disabled={disabled} icon="audition" />
              <Btn uid="EDIT-01-CTL-SUBTITLE-TOGGLE" label={tx("edit.ctl-subtitle-toggle")} onAct={() => { setSubtitleOn((prev) => !prev); void act("EDIT-01-CTL-SUBTITLE-TOGGLE"); }} disabled={disabled} icon="subtitle" />
              <Btn uid="EDIT-01-BTN-SET-IN" label={tx("edit.set_in")} onAct={() => runOnly(setRangeIn, "EDIT-01-BTN-SET-IN")} disabled={disabled} icon="set-in" />
              <Btn uid="EDIT-01-BTN-SET-OUT" label={tx("edit.set_out")} onAct={() => runOnly(setRangeOut, "EDIT-01-BTN-SET-OUT")} disabled={disabled} icon="set-out" />
              <Btn uid="EDIT-01-BTN-CLEAR-RANGE" label={tx("edit.btn-clear-range")} onAct={() => runOnly(clearRange, "EDIT-01-BTN-CLEAR-RANGE")} disabled={disabled} icon="clear" />
              <Btn uid="EDIT-01-CTL-IN-OUT" label={tx("edit.ctl-in-out")} onAct={act} disabled={disabled} icon="range" />
            </div>
          </section>

          <section className={styles.panel} data-component-uid="EDIT-01-CMP-MANUAL-TOOLS">
            <div className={styles.toolbar}>
              <Btn uid="EDIT-01-BTN-UNDO" label={tx("edit.btn-undo")} onAct={() => runOnly(undo, "EDIT-01-BTN-UNDO")} disabled={disabled} icon="undo" />
              <Btn uid="EDIT-01-BTN-REDO" label={tx("edit.btn-redo")} onAct={() => runOnly(redo, "EDIT-01-BTN-REDO")} disabled={disabled} icon="redo" />
              <Btn uid="EDIT-01-TOOL-SELECT" label={tx("edit.tool-select")} onAct={() => { run((state) => setTool(state, "select")); void act("EDIT-01-TOOL-SELECT"); }} disabled={disabled} icon="select" />
              <Btn uid="EDIT-01-TOOL-RAZOR" label={tx("edit.tool-razor")} onAct={() => { run((state) => setTool(state, "razor")); void act("EDIT-01-TOOL-RAZOR"); }} disabled={disabled} icon="razor" />
              <Btn uid="EDIT-01-BTN-SPLIT" label={tx("edit.btn-split")} onAct={() => runOnly(splitSelected, "EDIT-01-BTN-SPLIT")} disabled={disabled || !sel} icon="split" />
              <Btn uid="EDIT-01-BTN-TRIM-START" label={tx("edit.btn-trim-start")} onAct={() => runOnly(trimSelectedStart, "EDIT-01-BTN-TRIM-START")} disabled={disabled || !sel} icon="trim-start" />
              <Btn uid="EDIT-01-BTN-TRIM-END" label={tx("edit.btn-trim-end")} onAct={() => runOnly(trimSelectedEnd, "EDIT-01-BTN-TRIM-END")} disabled={disabled || !sel} icon="trim-end" />
              <Btn uid="EDIT-01-BTN-MOVE" label={tx("edit.btn-move")} onAct={() => runOnly((state) => moveSelected(state, 1), "EDIT-01-BTN-MOVE")} disabled={disabled || !sel} icon="move" />
              <Btn uid="EDIT-01-BTN-REORDER" label={tx("edit.btn-reorder")} onAct={() => runOnly((state) => reorderSelected(state, 1), "EDIT-01-BTN-REORDER")} disabled={disabled || !sel} icon="reorder" />
              <Btn uid="EDIT-01-BTN-DELETE" label={tx("edit.btn-delete")} onAct={() => runOnly(deleteSelected, "EDIT-01-BTN-DELETE")} disabled={disabled || !sel} icon="delete" />
              <Btn uid="EDIT-01-BTN-DUPLICATE" label={tx("edit.btn-duplicate")} onAct={() => runOnly(duplicateSelected, "EDIT-01-BTN-DUPLICATE")} disabled={disabled || !sel} icon="duplicate" />
              <Btn uid="EDIT-01-CTL-TRANSITION" label={sel?.transition ? `${tx("edit.ctl-transition")}: ${sel.transition}` : tx("edit.ctl-transition")} onAct={() => { const next = ["cut", "cross", "fade", ""][transitionIndex]; setTransitionIndex((prev) => (prev + 1) % 4); run((state) => patchSelected(state, sel ? { transition: next || null } : {})); void act("EDIT-01-CTL-TRANSITION"); }} disabled={disabled || !sel} icon="transition" />
              <Btn uid="EDIT-01-CTL-SPEED" label={sel ? `${tx("edit.ctl-speed")} x${sel.speed}` : tx("edit.ctl-speed")} onAct={() => { const next = [1.25, 1.5, 2, 0.5, 1][speedIndex]; setSpeedIndex((prev) => (prev + 1) % 5); run((state) => patchSelected(state, { speed: next })); void act("EDIT-01-CTL-SPEED"); }} disabled={disabled || !sel} icon="speed" />
              <Btn uid="EDIT-01-BTN-REPLACE" label={tx("edit.btn-replace")} onAct={() => runAct((state) => replaceSelected(state, mediaLabel), "EDIT-01-BTN-REPLACE", mediaLabel)} disabled={disabled || !sel} icon="replace" />
              <Btn uid="EDIT-01-CTL-CLIP-VOLUME" label={sel ? `${tx("edit.ctl-clip-volume")} ${Math.round(sel.volume * 100)}%` : tx("edit.ctl-clip-volume")} onAct={() => { const next = [0.75, 0.5, 0, 1.25, 1][volumeIndex]; setVolumeIndex((prev) => (prev + 1) % 5); run((state) => patchSelected(state, { volume: next })); void act("EDIT-01-CTL-CLIP-VOLUME"); }} disabled={disabled || !sel} icon="clip-volume" />
              <Btn uid="EDIT-01-CTL-FADE" label={sel?.fadeIn || sel?.fadeOut ? `${tx("edit.ctl-fade")} ${sel.fadeIn}/${sel.fadeOut}s` : tx("edit.ctl-fade")} onAct={() => { const on = Boolean(sel?.fadeIn || sel?.fadeOut); run((state) => patchSelected(state, { fadeIn: on ? 0 : 1, fadeOut: on ? 0 : 1 })); void act("EDIT-01-CTL-FADE"); }} disabled={disabled || !sel} icon="fade" />
            </div>
          </section>

          <section className={styles.panel} data-component-uid="EDIT-01-CMP-MINI-TIMELINE">
            <div className={styles.toolbar}>
              <Btn uid="EDIT-01-BTN-MARKER" label={tx("edit.btn-marker")} onAct={() => runOnly((state) => addMarker(state, mediaLabel), "EDIT-01-BTN-MARKER")} disabled={disabled} icon="marker" />
              <Btn uid="EDIT-01-CTL-SNAP" label={tx("edit.ctl-snap")} onAct={() => { setSnapOn((prev) => !prev); void act("EDIT-01-CTL-SNAP"); }} disabled={disabled} primary icon="snap" />
              <Btn uid="EDIT-01-BTN-ZOOM-OUT" label={tx("edit.btn-zoom-out")} onAct={() => runOnly(zoomOut, "EDIT-01-BTN-ZOOM-OUT")} disabled={disabled} icon="zoom-out" />
              <Btn uid="EDIT-01-BTN-ZOOM-IN" label={tx("edit.btn-zoom-in")} onAct={() => runOnly(zoomIn, "EDIT-01-BTN-ZOOM-IN")} disabled={disabled} icon="zoom-in" />
              <Btn uid="EDIT-01-BTN-ZOOM-FIT" label={tx("edit.btn-zoom-fit")} onAct={() => runOnly(zoomFit, "EDIT-01-BTN-ZOOM-FIT")} disabled={disabled} icon="fit" />
              <span className={styles.note}>{tx("edit.playhead_note")}</span>
            </div>
            <button type="button" className={styles.rail} data-control-uid="EDIT-01-CTL-MINI-TIMELINE" disabled={disabled} onClick={(event) => seekFromEvent(event, "EDIT-01-CTL-MINI-TIMELINE")}>
              {tl.markers.length ? tl.markers.map((marker) => (
                <span key={marker.id} className={styles.miniMark} style={{ left: `${(marker.at / Math.max(1, tlEnd)) * 100}%` }} />
              )) : dash}
            </button>
          </section>

          <section className={styles.panel} data-component-uid="EDIT-01-CMP-TIMELINE">
            <h3 className={styles.sub}>{tx("edit.timeline")}</h3>
            <div className={styles.timeline}>
              <div className={styles.rulerRow} data-component-uid="EDIT-01-CMP-RULER">
                <span />
                <button type="button" className={styles.rulerMarks} data-control-uid="EDIT-01-CTL-RULER" disabled={disabled} onClick={(event) => seekFromEvent(event, "EDIT-01-CTL-RULER")}>
                  {Array.from({ length: Math.ceil(tlEnd / 5) + 1 }, (_, index) => (
                    <span key={index}>{index * 5}s</span>
                  ))}
                </button>
              </div>
              <div data-component-uid="EDIT-01-CMP-MARKER-RAIL">
                <button type="button" className={styles.rail} data-control-uid="EDIT-01-CTL-MARKER-RAIL" disabled={disabled} onClick={() => runOnly(jumpToNearestMarker, "EDIT-01-CTL-MARKER-RAIL")}>
                  {tl.markers.length ? tl.markers.map((marker) => (
                    <span key={marker.id} className={styles.markerDot} style={{ left: `${(marker.at / Math.max(1, tlEnd)) * 100}%` }} title={`${marker.id} ${marker.note}`} />
                  )) : dash}
                </button>
              </div>
              {TRACKS.map((track) => {
                const flags = tl.trackFlags[track.id];
                const trackClips = tl.clips.filter((clip) => clip.track === track.id);
                return (
                  <div key={track.id} className={styles.track}>
                    <div className={styles.trackMeta}>
                      <span>{track.id}</span>
                      <span>{tx(track.labelKey)}</span>
                    </div>
                    <div
                      className={`${styles.trackLane} ${flags.locked ? styles.trackLocked : ""} ${flags.muted ? styles.trackMuted : ""}`}
                      data-drag-lane={track.id}
                      onClick={(event) => { if (!disabled && !flags.locked) trackClick(event, track.id); }}
                    >
                      {trackClips.length ? trackClips.map((clip) => {
                        const dragOffset = dragging?.clipId === clip.id ? dragging.currentSec - dragging.offsetSec : null;
                        const dragStart = dragOffset != null && dragOffset >= 0 ? dragOffset : clip.start;
                        return (
                          <button
                            key={clip.id}
                            type="button"
                            className={`${styles.tlClip} ${clip.id === tl.selectedClipId ? styles.tlClipActive : ""} ${dragging?.clipId === clip.id ? styles.tlClipDragging : ""}`}
                            style={{ left: `${(dragStart / Math.max(1, tlEnd)) * 100}%`, width: `${Math.max(1.5, ((clip.outPoint - clip.inPoint) / Math.max(1, tlEnd)) * 100)}%` }}
                            onClick={(event) => { event.stopPropagation(); if (!disabled && !flags.locked) run((state) => selectClip(state, clip.id)); }}
                            onMouseDown={(event) => {
                              if (disabled || flags.locked) return;
                              const at = laneClickSeconds(event);
                              setDragging({ clipId: clip.id, track: track.id, offsetSec: at - clip.start, currentSec: at, moved: false });
                            }}
                          >
                            <span>{clip.label}</span>
                            <span>{dragStart.toFixed(1)}s → {(clip.outPoint - clip.inPoint).toFixed(1)}s</span>
                          </button>
                        );
                      }) : (
                        <span className={`${styles.clip} ${styles[track.clip]}`}>{tx("edit.exact_ref")}</span>
                      )}
                    </div>
                  </div>
                );
              })}
              {tl.rangeIn != null || tl.rangeOut != null ? (
                <div
                  className={styles.rangeShade}
                  style={{
                    left: `calc(88px + ${((tl.rangeIn ?? 0) / Math.max(1, tlEnd)).toFixed(4)} * (100% - 88px))`,
                    width: `calc(${(((tl.rangeOut ?? tlEnd) - (tl.rangeIn ?? 0)) / Math.max(1, tlEnd)).toFixed(4)} * (100% - 88px))`,
                  }}
                />
              ) : null}
              <div className={styles.playheadLine} style={{ left: `calc(88px + ${(tl.playhead / Math.max(1, tlEnd)).toFixed(4)} * (100% - 88px))` }} />
              <button type="button" className={styles.playheadCtrl} data-control-uid="EDIT-01-CTL-PLAYHEAD" disabled={disabled} onClick={(event) => seekFromEvent(event, "EDIT-01-CTL-PLAYHEAD")} aria-label={tx("edit.ctl-playhead")} />
              <button type="button" className={styles.drop} data-control-uid="EDIT-01-CTL-DROP-TIMELINE" disabled={disabled} onClick={() => runAct((state) => importClip(state, "V1", mediaLabel, 8), "EDIT-01-CTL-DROP-TIMELINE", mediaLabel)}>{tx("edit.ctl-drop-timeline")} {mediaLabel}</button>
              <div className={styles.toolbar}>
                <Btn uid="EDIT-01-CTL-TRACK-LOCK" label={sel ? `${tx("edit.ctl-track-lock")}:${sel.track}` : tx("edit.ctl-track-lock")} onAct={() => { if (sel) run((state) => toggleTrackFlag(state, sel.track, "locked")); void act("EDIT-01-CTL-TRACK-LOCK"); }} disabled={disabled || !sel} icon="lock" />
                <Btn uid="EDIT-01-CTL-TRACK-MUTE" label={sel ? `${tx("edit.ctl-track-mute")}:${sel.track}` : tx("edit.ctl-track-mute")} onAct={() => { if (sel) run((state) => toggleTrackFlag(state, sel.track, "muted")); void act("EDIT-01-CTL-TRACK-MUTE"); }} disabled={disabled || !sel} icon="mute" />
                <Btn uid="EDIT-01-CTL-TRACK-SOLO" label={sel ? `${tx("edit.ctl-track-solo")}:${sel.track}` : tx("edit.ctl-track-solo")} onAct={() => { if (sel) run((state) => toggleTrackFlag(state, sel.track, "solo")); void act("EDIT-01-CTL-TRACK-SOLO"); }} disabled={disabled || !sel} icon="solo" />
                <Btn uid="EDIT-01-CTL-TRACK-VISIBLE" label={sel ? `${tx("edit.ctl-track-visible")}:${sel.track}` : tx("edit.ctl-track-visible")} onAct={() => { if (sel) run((state) => toggleTrackFlag(state, sel.track, "visible")); void act("EDIT-01-CTL-TRACK-VISIBLE"); }} disabled={disabled || !sel} icon="visible" />
              </div>
            </div>
          </section>

          <section className={styles.panel} data-component-uid="EDIT-01-CMP-PRECISION">
            <h3 className={styles.sub}>{tx("edit.precision")}</h3>
            <div className={styles.toolbar}>
              <Field uid="EDIT-01-FLD-CLIP-IN" label={tx("edit.fld-clip-in")} value={sel ? formatTimecode(sel.inPoint) : null} loading={false} onAct={act} disabled={disabled} readonly />
              <Field uid="EDIT-01-FLD-CLIP-OUT" label={tx("edit.fld-clip-out")} value={sel ? formatTimecode(sel.outPoint) : null} loading={false} onAct={act} disabled={disabled} readonly />
              <Field uid="EDIT-01-FLD-CLIP-POSITION" label={tx("edit.fld-clip-position")} value={sel ? `${sel.start.toFixed(2)}s` : null} loading={false} onAct={act} disabled={disabled} readonly />
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
          <div className={styles.messageTimeline} ref={timelineRef}>
            {conversation.length === 0 && !generating ? (
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
                    {row.route ? ` ${row.route}` : ""}
                    {row.ref ? ` ${row.ref}` : ""}
                    {row.at ? ` ${row.at}` : ""}
                  </div>
                    <ConversationMessageBody
                      text={row.text}
                      role={row.role}
                      accountUid={DEFAULT_ACCOUNT}
                      sessionUid={DEFAULT_SESSION}
                      tx={tx}
                      busy={generating}
                      onRetry={
                        row.role === "assistant"
                          ? () => {
                              const prior = lastUserText(valueOf("EDIT-01-FLD-CORRECTION-MESSAGES"), activeThread ?? "");
                              if (prior) void act("EDIT-01-BTN-SEND", prior);
                            }
                          : undefined
                      }
                      onRegenerate={
                        row.role === "assistant"
                          ? () => {
                              const prior = lastUserText(valueOf("EDIT-01-FLD-CORRECTION-MESSAGES"), activeThread ?? "");
                              if (prior) void act("EDIT-01-BTN-SEND", prior);
                            }
                          : undefined
                      }
                    />
                  </article>
                ))
              )}
              {generating
                ? (Object.keys(streamDrafts).length ? Object.entries(streamDrafts) : [["_", " "]]).map(([alias, text]) => (
                    <article key={alias} className={styles.assistantMessage} data-stream="live">
                      <div className={styles.bubbleRole}>
                        {tx("edit.ai_response_n")}
                        {alias !== "_" ? ` @${alias}` : ""}
                        {streamStatus
                          ? ` ${tx("conversation.stream.status")}：${tx(generationStatusKey(streamStatus))}`
                          : ` ${tx("conversation.stream.generating")}`}
                      </div>
                      <ConversationMarkdown text={(text ?? "").trim() || tx("conversation.stream.generating")} />
                    </article>
                  ))
                : null}
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
                if (event.key !== "Enter") return;
                if (event.nativeEvent.isComposing) return;
                if (event.ctrlKey || event.metaKey) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
            />
            <IconButton uid="EDIT-01-BTN-SEND" label={generating ? tx("edit.stop") : tooLong ? tx("edit.message_too_long") : parserBlocked ? tx("edit.parser_blocked") : canSend ? tx("edit.send") : tx("edit.gate-message")} icon={generating ? "stop" : "send"} onAct={() => sendMessage()} disabled={generating ? false : disabled || !canSend} className={`${styles.btn} ${styles.iconBtn} ${styles.btnSend}`} />
          </div>
          {composerTokens.length ? (
            <div className={styles.tokenRow} aria-live="polite">
              {composerTokens.map((token, index) => (
                <span key={`${token.raw}-${index}`} className={composerTokenTone(token.kind) === "ok" ? styles.tokenOk : composerTokenTone(token.kind) === "ambiguous" ? styles.tokenAmbiguous : styles.tokenError} data-token-kind={token.kind}>
                  {token.canonical || token.raw}
                  {token.kind === "AMBIGUOUS_REF" ? ` ${tx("edit.token_ambiguous")}` : token.kind === "PARSER_ERROR" ? ` ${tx("edit.token_invalid")}` : token.canonical && token.canonical !== token.raw ? ` ${tx("edit.token_resolved")}` : ""}
                </span>
              ))}
            </div>
          ) : null}
          {tooLong ? <p className={styles.error} role="alert">{tx("edit.message_too_long")}</p> : null}
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
          <Field uid="EDIT-01-FLD-CLIP-ID" label={tx("edit.range_clip_track")} value={sel?.id ?? null} loading={false} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-CLIP-DURATION" label={tx("edit.drag_move")} value={sel ? `${(sel.outPoint - sel.inPoint).toFixed(2)}s` : null} loading={false} onAct={act} disabled={disabled} readonly />

          <Field uid="EDIT-01-FLD-TRACK-ID" label={tx("edit.frame_nudge")} value={sel?.track ?? null} loading={false} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-INSPECTOR-VOLUME" label={tx("edit.volume_fade")} value={sel ? `${Math.round(sel.volume * 100)}%` : null} loading={false} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-SUB-TIMECODE" label={tx("edit.subtitle_offset")} value={tl.rangeIn != null || tl.rangeOut != null ? `${tl.rangeIn ?? 0} → ${tl.rangeOut ?? tlEnd}` : v("EDIT-01-FLD-SUB-TIMECODE")} loading={loading} onAct={act} disabled={disabled} readonly />
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
          <Field uid="EDIT-01-FLD-INSPECTOR-FADE-IN" label={tx("edit.selected_context")} value={sel ? `${sel.fadeIn.toFixed(2)}s` : null} loading={false} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-INSPECTOR-FADE-OUT" label={tx("edit.exact_source_version")} value={sel ? `${sel.fadeOut.toFixed(2)}s` : null} loading={false} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-INSPECTOR-SPEED" label={tx("edit.in_out_position")} value={sel ? `x${sel.speed}` : null} loading={false} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-FLD-INSPECTOR-TRANSITION" label={tx("edit.volume_fade_speed")} value={sel?.transition ?? null} loading={false} onAct={act} disabled={disabled} readonly />
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-VERSION">
          <h3 className={styles.sub}>{tx("edit.version")}</h3>
          <Field uid="EDIT-01-LBL-EVAL-SUMMARY" label={tx("edit.baseline")} value={v("EDIT-01-LBL-EVAL-SUMMARY")} loading={loading} onAct={act} disabled={disabled} readout />
          <div className={styles.list} data-control-uid="EDIT-01-LST-VERSION-HISTORY">
            {tl.versions.length ? tl.versions.map((version, index) => (
              <button
                key={`${version.label}-${index}`}
                type="button"
                className={styles.item}
                disabled={disabled}
                onClick={() => { runAct((state) => restoreVersion(state, index), "EDIT-01-LST-VERSION-HISTORY", version.label); setVersionCompareNote(null); }}
              >
                <span>{version.label}</span>
                <span>{version.clips.length} · {version.at}</span>
              </button>
            )) : (
              <button type="button" className={styles.item} disabled={disabled} onClick={() => void act("EDIT-01-LST-VERSION-HISTORY")}>
                <span>{tx("edit.candidate")}</span>
                <span>{dash}</span>
              </button>
            )}
          </div>
          {versionCompareNote ? <p className={styles.note}>{versionCompareNote}</p> : null}
          <Field uid="EDIT-01-LBL-STAGE-SCORE" label={tx("edit.score")} value={v("EDIT-01-LBL-STAGE-SCORE")} loading={loading} onAct={act} disabled={disabled} readonly />
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-VERSION-SAVE" label={tx("edit.btn-version-save")} onAct={() => runAct((state) => saveVersion(state, `draft-${state.versions.length + 1}`), "EDIT-01-BTN-VERSION-SAVE", `draft-${tl.versions.length + 1}`)} disabled={disabled} primary />
            <Btn uid="EDIT-01-BTN-VERSION-RESTORE" label={tx("edit.btn-version-restore")} onAct={() => runAct((state) => restoreVersion(state, state.versions.length - 1), "EDIT-01-BTN-VERSION-RESTORE")} disabled={disabled || !tl.versions.length} />
            <Btn uid="EDIT-01-BTN-VERSION-LOCK" label={tx("edit.btn-version-lock")} onAct={act} disabled={disabled || dialogueBlocked} />
            <Btn uid="EDIT-01-BTN-VERSION-COMPARE" label={tx("edit.diff")} onAct={() => { const last = tl.versions[tl.versions.length - 1]; setVersionCompareNote(last ? `${last.label}: ${last.clips.length} → ${tl.clips.length}` : null); void act("EDIT-01-BTN-VERSION-COMPARE"); }} disabled={disabled || !tl.versions.length} icon="compare" />
          </div>
        </section>

        <section className={`${styles.panel} ${styles.block}`} data-component-uid="EDIT-01-CMP-OUTPUT">
          <h3 className={styles.sub}>{tx("edit.output")}</h3>
          <Field uid="EDIT-01-LBL-PAGE-STATE" label={tx("edit.stage_job")} value={v("EDIT-01-LBL-PAGE-STATE")} loading={loading} onAct={act} disabled={disabled} readout />
          <Field uid="EDIT-01-LBL-BINDING-FINGERPRINT" label={tx("edit.lbl-binding-fingerprint")} value={v("EDIT-01-LBL-BINDING-FINGERPRINT")} loading={loading} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-LBL-RENDER-JOB" label={tx("edit.lbl-render-job")} value={renderLabel} loading={loading} onAct={act} disabled={disabled} readonly />
          <Field uid="EDIT-01-LBL-ERROR-STATE" label={tx("edit.output_checksum")} value={v("EDIT-01-LBL-ERROR-STATE")} loading={loading} onAct={act} disabled={disabled} readout />
          {autoNote ? <div className={styles.note} role="status">{autoNote}</div> : null}
          <div className={styles.list} data-control-uid="EDIT-01-LST-JOB-STATUS">
            {renderJobs.length ? (
              [...renderJobs].reverse().slice(0, 6).map((job) => (
                <div className={styles.item} key={job.id}>
                  <span>{job.id}</span>
                  <span>{job.status === "running" ? `${tx("edit.job_running")} ${job.progress}%` : job.status === "completed" ? tx("edit.job_completed") : tx("edit.job_cancelled")}</span>
                </div>
              ))
            ) : (
              <div className={styles.item}>
                <span>{tx("edit.blocking_error")}</span>
                <span>{dash}</span>
              </div>
            )}
          </div>
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-RENDER-SETTINGS" label={tx("edit.btn-render-settings")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-RENDER-EXECUTE" label={tx("edit.btn-render-execute")} onAct={() => { void act("EDIT-01-BTN-RENDER-EXECUTE").then((patch) => { if (patch["EDIT-01-BTN-RENDER-EXECUTE"] === "running") startRender(); }); }} disabled={disabled || dialogueBlocked} primary />
            <Btn uid="EDIT-01-BTN-RENDER-CANCEL" label={tx("edit.btn-render-cancel")} onAct={() => { cancelRender(); void act("EDIT-01-BTN-RENDER-CANCEL"); }} disabled={disabled} />
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
            {v("EDIT-01-LST-VOICE-TAKES") ? (
              <button
                type="button"
                className={`${styles.item} ${styles.itemActive}`}
                disabled={disabled}
                onClick={() => void act("EDIT-01-LST-VOICE-TAKES")}
              >
                <span>{v("EDIT-01-LST-VOICE-TAKES")}</span>
                <span>{tx("edit.take_current")}</span>
              </button>
            ) : (
              <div className={styles.item}>
                <span>{tx("edit.unbound_take")}</span>
                <span>{dash}</span>
              </div>
            )}
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
          <Btn uid="EDIT-01-CTL-MASTER-LEVEL" label={`${tx("edit.ctl-master-level")} ${masterLevelDb <= 0 ? `${masterLevelDb}dB` : `+${masterLevelDb}dB`}`} onAct={() => { setMasterLevelDb((prev) => (prev <= 0 ? prev + 3 : 0)); void act("EDIT-01-CTL-MASTER-LEVEL"); }} disabled={disabled} />
          <Btn uid="EDIT-01-CTL-TRACK-LEVEL" label={`${tx("edit.ctl-track-level")} ${trackLevelDb <= 0 ? `${trackLevelDb}dB` : `+${trackLevelDb}dB`}`} onAct={() => { setTrackLevelDb((prev) => (prev <= 0 ? prev + 3 : 0)); void act("EDIT-01-CTL-TRACK-LEVEL"); }} disabled={disabled} />
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-MUSIC-ADD" label={tx("edit.btn-music-add")} onAct={() => runAct((state) => importClip(state, "A2", v("EDIT-01-FLD-MUSIC-ASSET") || mediaLabel, 12), "EDIT-01-BTN-MUSIC-ADD")} disabled={disabled} icon="upload" />
            <Btn uid="EDIT-01-BTN-SFX-ADD" label={tx("edit.btn-sfx-add")} onAct={() => runAct((state) => importClip(state, "A3", v("EDIT-01-FLD-SFX-ASSET") || mediaLabel, 3), "EDIT-01-BTN-SFX-ADD")} disabled={disabled} icon="upload" />
            <Btn uid="EDIT-01-BTN-MIX-PREVIEW" label={tx("edit.btn-mix-preview")} onAct={() => { setMixPreviewOn((prev) => !prev); setMixResult(null); void act("EDIT-01-BTN-MIX-PREVIEW"); }} disabled={disabled} icon="audition" />
            <Btn uid="EDIT-01-BTN-MIX-EXECUTE" label={tx("edit.btn-mix-execute")} onAct={() => { setMixPreviewOn(false); setMixResult(`A1+A2+A3 ${new Date().toISOString().slice(11, 19)}`); void act("EDIT-01-BTN-MIX-EXECUTE"); }} disabled={disabled} primary />
          </div>
          {mixPreviewOn ? <p className={styles.note}>{tx("edit.mix_previewing")}</p> : null}
          {mixResult ? <p className={styles.note}>{mixResult}</p> : null}
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
            <textarea
              data-control-uid="EDIT-01-FLD-SUB-TEXT"
              disabled={disabled}
              value={subTextDraft || v("EDIT-01-FLD-SUB-TEXT") || ""}
              placeholder={tx("edit.fld-sub-text")}
              rows={2}
              onChange={(event) => setSubTextDraft(event.target.value)}
              onBlur={() => { if (subTextDraft.trim()) void act("EDIT-01-FLD-SUB-TEXT", subTextDraft.trim()); }}
            />
          </label>
          <Field uid="EDIT-01-FLD-SUB-LANG" label={tx("edit.fld-sub-lang")} value={v("EDIT-01-FLD-SUB-LANG")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="EDIT-01-FLD-SUB-FORMAT" label={tx("edit.fld-sub-format")} value={v("EDIT-01-FLD-SUB-FORMAT")} loading={loading} onAct={act} disabled={disabled} />
          <div className={styles.toolbar}>
            <Btn uid="EDIT-01-BTN-SUB-CREATE" label={tx("edit.btn-sub-create")} onAct={() => runAct((state) => importClip(state, "S1", subTextDraft.trim() || "session-sub", 3), "EDIT-01-BTN-SUB-CREATE", subTextDraft.trim() || "session-sub")} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-SUB-IMPORT" label={tx("edit.btn-sub-import")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-SUB-API-SYNC" label={tx("edit.btn-sub-api-sync")} onAct={act} disabled={disabled} primary />
            <Btn uid="EDIT-01-BTN-SUB-MANUAL-SYNC" label={tx("edit.btn-sub-manual-sync")} onAct={act} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-SUB-MERGE" label={tx("edit.btn-sub-merge")} onAct={() => runAct((state) => {
              const clip = selectedClip(state);
              if (!clip || clip.track !== "S1") return state;
              const siblings = state.clips.filter((row) => row.track === "S1").sort((a, b) => a.start - b.start);
              const index = siblings.findIndex((row) => row.id === clip.id);
              const neighbor = siblings[index + 1];
              if (!neighbor) return state;
              return { ...state, clips: state.clips.filter((row) => row.id !== neighbor.id).map((row) => (row.id === clip.id ? { ...row, outPoint: row.inPoint + (neighbor.start + (neighbor.outPoint - neighbor.inPoint) - row.start) } : row)) };
            }, "EDIT-01-BTN-SUB-MERGE")} disabled={disabled || !sel || sel.track !== "S1"} />
            <Btn uid="EDIT-01-BTN-SUB-SPLIT" label={tx("edit.btn-sub-split")} onAct={() => runOnly(splitSelected, "EDIT-01-BTN-SUB-SPLIT")} disabled={disabled || !sel || sel.track !== "S1"} />
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
            <Btn uid="EDIT-01-BTN-EVAL-JUMP" label={tx("edit.btn-eval-jump")} onAct={() => runOnly(jumpToNearestMarker, "EDIT-01-BTN-EVAL-JUMP")} disabled={disabled} />
            <Btn uid="EDIT-01-BTN-EVAL-LOAD-RANGE" label={tx("edit.btn-eval-load-range")} onAct={() => { if (tl.rangeIn != null) { run((state) => seekTimeline(state, tl.rangeIn ?? 0)); } void act("EDIT-01-BTN-EVAL-LOAD-RANGE"); }} disabled={disabled} />
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
