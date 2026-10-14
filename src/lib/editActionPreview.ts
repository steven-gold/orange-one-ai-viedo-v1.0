import { exactName, namedValue, statusFromAction } from "./coreActionPreview";

function named(value: string | null | undefined): string {
  return exactName(value);
}

function keep(nextValue: string | undefined, current: string | null, fallback: string): string {
  return namedValue(nextValue, named(current) || fallback);
}

function toggle(current: string | null, on: string, off: string): string {
  return current === on ? off : on;
}

function inboundReady(current: (uid: string) => string | null): boolean {
  return Boolean(
    named(current("EDIT-01-FLD-PROJECT")) &&
      named(current("EDIT-01-FLD-TOPIC")) &&
      named(current("EDIT-01-FLD-TASK")) &&
      named(current("EDIT-01-FLD-SOURCE-VERSION")),
  );
}

const READONLY_ACTIONS = new Set([
  "EDIT-01-ACT-CONTEXT-PROJECT-SET",
  "EDIT-01-ACT-CONTEXT-TOPIC-SET",
  "EDIT-01-ACT-CONTEXT-TASK-SET",
  "EDIT-01-ACT-NOOP-VIEW",
]);

const VIEW_ACTIONS = new Set([
  "EDIT-01-ACT-BLUEPRINT-VIEW",
  "EDIT-01-ACT-PACKAGE-VIEW",
  "EDIT-01-ACT-MANIFEST-VIEW",
  "EDIT-01-ACT-UI-INSPECTOR-TAB",
  "EDIT-01-ACT-UI-VIEWPORT-PAN",
  "EDIT-01-ACT-UI-ZOOM-FIT",
  "EDIT-01-ACT-UI-ZOOM-IN",
  "EDIT-01-ACT-UI-ZOOM-OUT",
  "EDIT-01-ACT-UI-TOOL-SELECT",
  "EDIT-01-ACT-UI-TOOL-RAZOR",
  "EDIT-01-ACT-UI-MEDIA-FILTER",
  "EDIT-01-ACT-UI-SUBTITLE-TOGGLE",
  "EDIT-01-ACT-UI-AUDIO-MONITOR",
  "EDIT-01-ACT-UI-PREVIEW-MUTE",
  "EDIT-01-ACT-UI-PREVIEW-VOLUME",
  "EDIT-01-ACT-UI-FULLSCREEN",
  "EDIT-01-ACT-MEDIA-SELECT",
  "EDIT-01-ACT-VERSION-SELECT",
  "EDIT-01-ACT-EVAL-ISSUE-SELECT",
  "EDIT-01-ACT-MARKER-ADD",
  "EDIT-01-ACT-MARKER-JUMP",
]);

const GATED_ACTIONS = new Set([
  "EDIT-01-ACT-FLOW-START-CONTINUE",
  "EDIT-01-ACT-STAGE-CONFIRM",
  "EDIT-01-ACT-STAGE-MODIFY",
  "EDIT-01-ACT-EVAL-RECHECK-SELECTED",
  "EDIT-01-ACT-EVAL-RECHECK-FULL",
  "EDIT-01-ACT-EVAL-EVIDENCE-VIEW",
  "EDIT-01-ACT-EVAL-MARK-LIPSYNC",
  "EDIT-01-ACT-EVAL-MARKER-JUMP",
  "EDIT-01-ACT-EVAL-RANGE-LOAD",
  "EDIT-01-ACT-VERSION-SAVE",
  "EDIT-01-ACT-VERSION-LOCK",
  "EDIT-01-ACT-VERSION-COMPARE",
  "EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT",
  "EDIT-01-ACT-RENDER-START",
  "EDIT-01-ACT-RENDER-CANCEL",
  "EDIT-01-ACT-RENDER-SETTINGS",
  "EDIT-01-ACT-OUTPUT-VERSION-SAVE",
  "EDIT-01-ACT-OUTPUT-DOWNLOAD",
  "EDIT-01-ACT-HANDOFF",
  "EDIT-01-ACT-RETURN-BLUEPRINT",
  "EDIT-01-ACT-MIX-EXECUTE",
  "EDIT-01-ACT-MIX-PREVIEW",
  "EDIT-01-ACT-MIX-MASTER-LEVEL",
  "EDIT-01-ACT-MIX-TRACK-LEVEL",
  "EDIT-01-ACT-LIPSYNC-EXECUTE",
  "EDIT-01-ACT-LIPSYNC-PREVIEW",
  "EDIT-01-ACT-LIPSYNC-RETRY-RANGE",
  "EDIT-01-ACT-LIPSYNC-TARGET-SET",
  "EDIT-01-ACT-SUB-API-SYNC",
  "EDIT-01-ACT-SUB-CREATE",
  "EDIT-01-ACT-SUB-IMPORT",
  "EDIT-01-ACT-SUB-MANUAL-SYNC",
  "EDIT-01-ACT-SUB-MERGE",
  "EDIT-01-ACT-SUB-SPLIT",
  "EDIT-01-ACT-SUB-FORMAT",
  "EDIT-01-ACT-SUB-LANGUAGE",
  "EDIT-01-ACT-SUB-TEXT-EDIT",
  "EDIT-01-ACT-SUB-TIMECODE",
  "EDIT-01-ACT-VOICE-GENERATE",
  "EDIT-01-ACT-VOICE-PREVIEW",
  "EDIT-01-ACT-VOICE-COMPARE",
  "EDIT-01-ACT-VOICE-APPLY",
  "EDIT-01-ACT-VOICE-ASSET-SET",
  "EDIT-01-ACT-VOICE-MODEL-SET",
  "EDIT-01-ACT-VOICE-PROVIDER-SET",
  "EDIT-01-ACT-VOICE-SCRIPT-BIND",
  "EDIT-01-ACT-MUSIC-ADD",
  "EDIT-01-ACT-MUSIC-SET",
  "EDIT-01-ACT-SFX-ADD",
  "EDIT-01-ACT-SFX-SET",
  "EDIT-01-ACT-MEDIA-IMPORT",
  "EDIT-01-ACT-STANDALONE-SPEC-IMPORT",
  "EDIT-01-ACT-CLIP-INSERT",
  "EDIT-01-ACT-CLIP-DELETE",
  "EDIT-01-ACT-CLIP-DUPLICATE",
  "EDIT-01-ACT-CLIP-MOVE",
  "EDIT-01-ACT-CLIP-REORDER",
  "EDIT-01-ACT-CLIP-REPLACE",
  "EDIT-01-ACT-CLIP-SPLIT",
  "EDIT-01-ACT-CLIP-TRIM-START",
  "EDIT-01-ACT-CLIP-TRIM-END",
  "EDIT-01-ACT-CLIP-SPEED",
  "EDIT-01-ACT-CLIP-TRANSITION",
  "EDIT-01-ACT-CLIP-FADE",
  "EDIT-01-ACT-CLIP-VOLUME",
  "EDIT-01-ACT-API-APPLY",
  "EDIT-01-ACT-API-CANCEL",
  "EDIT-01-ACT-API-COMPARE",
  "EDIT-01-ACT-API-DISCARD",
  "EDIT-01-ACT-API-INSTRUCTION-SET",
  "EDIT-01-ACT-API-MODEL-SET",
  "EDIT-01-ACT-API-PROVIDER-SET",
  "EDIT-01-ACT-API-SCOPE-SET",
  "EDIT-01-ACT-CORRECTION-CANDIDATE-GENERATE",
  "EDIT-01-ACT-CORRECTION-CANDIDATE-APPROVE",
  "EDIT-01-ACT-CORRECTION-EXECUTE",
  "EDIT-01-ACT-TRACK-LOCK",
  "EDIT-01-ACT-TRACK-MUTE",
  "EDIT-01-ACT-TRACK-SOLO",
  "EDIT-01-ACT-TRACK-VISIBLE",
  "EDIT-01-ACT-SNAP-TOGGLE",
  "EDIT-01-ACT-LOOP-TOGGLE",
  "EDIT-01-ACT-UNDO",
  "EDIT-01-ACT-REDO",
  "EDIT-01-ACT-PLAY",
  "EDIT-01-ACT-PAUSE",
  "EDIT-01-ACT-FRAME-NEXT",
  "EDIT-01-ACT-FRAME-PREV",
  "EDIT-01-ACT-SEEK-SCRUB",
  "EDIT-01-ACT-SEEK-POINTER",
  "EDIT-01-ACT-SEEK-TIMECODE",
  "EDIT-01-ACT-PLAYBACK-RATE",
  "EDIT-01-ACT-RANGE-SET",
  "EDIT-01-ACT-RANGE-SET-IN",
  "EDIT-01-ACT-RANGE-SET-OUT",
  "EDIT-01-ACT-RANGE-CLEAR",
  "EDIT-01-ACT-SOURCE-MODE-SET",
  "EDIT-01-ACT-EXECUTION-MODE-SET",
]);

export function previewEditAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const ready = inboundReady(current);

  if (READONLY_ACTIONS.has(actionUid)) {
    return {};
  }
  if (VIEW_ACTIONS.has(actionUid)) {
    return {};
  }

  if (actionUid === "EDIT-01-ACT-EXECUTION-MODE-SET") {
    return { "EDIT-01-CTL-EXECUTION-MODE": current("EDIT-01-CTL-EXECUTION-MODE") === "MANUAL" ? "AUTO" : "MANUAL" };
  }
  if (actionUid === "EDIT-01-ACT-SOURCE-MODE-SET") {
    return { "EDIT-01-CTL-SOURCE-MODE": toggle(current("EDIT-01-CTL-SOURCE-MODE"), "STANDALONE_UPLOAD", "PROJECT_TASK") };
  }
  if (actionUid === "EDIT-01-ACT-SNAP-TOGGLE") {
    return { "EDIT-01-CTL-SNAP": toggle(current("EDIT-01-CTL-SNAP"), "active", "idle") };
  }
  if (actionUid === "EDIT-01-ACT-LOOP-TOGGLE") {
    return { "EDIT-01-CTL-LOOP": toggle(current("EDIT-01-CTL-LOOP"), "active", "idle") };
  }

  if (!ready) return {};

  if (actionUid === "EDIT-01-ACT-FLOW-START-CONTINUE") {
    return {
      "EDIT-01-BTN-FLOW-START": "running",
      "EDIT-01-LBL-PAGE-STATE": "running",
      "EDIT-01-LBL-PENDING-TASK": keep(undefined, current("EDIT-01-LBL-PENDING-TASK"), "ASSEMBLY"),
    };
  }
  if (actionUid === "EDIT-01-ACT-STAGE-CONFIRM") {
    if (current("EDIT-01-BTN-FLOW-START") !== "running") return {};
    return {
      "EDIT-01-BTN-STAGE-CONFIRM": "confirmed",
      "EDIT-01-LBL-CURRENT-STAGE": keep(undefined, current("EDIT-01-LBL-CURRENT-STAGE"), "STAGE 02 · AUDIO"),
      "EDIT-01-LBL-STAGE-SCORE": keep(undefined, current("EDIT-01-LBL-STAGE-SCORE"), "95"),
    };
  }
  if (actionUid === "EDIT-01-ACT-STAGE-MODIFY") {
    return {
      "EDIT-01-BTN-STAGE-MODIFY": "returned",
      "EDIT-01-LBL-PAGE-STATE": "editing",
    };
  }
  if (actionUid === "EDIT-01-ACT-EVAL-RECHECK-SELECTED" || actionUid === "EDIT-01-ACT-EVAL-RECHECK-FULL") {
    return {
      [controlUid]: "rechecked",
      "EDIT-01-LBL-EVAL-SUMMARY": keep(undefined, current("EDIT-01-LBL-EVAL-SUMMARY"), "PASS"),
      "EDIT-01-LBL-STAGE-SCORE": keep(undefined, current("EDIT-01-LBL-STAGE-SCORE"), "95"),
    };
  }
  if (actionUid === "EDIT-01-ACT-VERSION-SAVE") {
    if (current("EDIT-01-BTN-STAGE-CONFIRM") !== "confirmed") return {};
    return {
      "EDIT-01-BTN-VERSION-SAVE": "saved",
      "EDIT-01-LST-VERSION-HISTORY": keep(undefined, current("EDIT-01-LST-VERSION-HISTORY"), "draft"),
    };
  }
  if (actionUid === "EDIT-01-ACT-VERSION-LOCK") {
    if (current("EDIT-01-BTN-VERSION-SAVE") !== "saved") return {};
    return {
      "EDIT-01-BTN-VERSION-LOCK": "locked",
      "EDIT-01-FLD-SOURCE-VERSION": keep(undefined, current("EDIT-01-FLD-SOURCE-VERSION"), "LOCKED"),
    };
  }
  if (actionUid === "EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT") {
    return {
      "EDIT-01-BTN-VERSION-LOCK": "idle",
      "EDIT-01-LBL-PAGE-STATE": "editing",
    };
  }
  if (actionUid === "EDIT-01-ACT-RENDER-START") {
    if (current("EDIT-01-BTN-VERSION-LOCK") !== "locked") return {};
    return {
      "EDIT-01-BTN-RENDER-EXECUTE": "running",
      "EDIT-01-LBL-RENDER-JOB": "running",
    };
  }
  if (actionUid === "EDIT-01-ACT-RENDER-CANCEL") {
    return { "EDIT-01-LBL-RENDER-JOB": "cancelled" };
  }
  if (actionUid === "EDIT-01-ACT-OUTPUT-VERSION-SAVE") {
    if (current("EDIT-01-BTN-RENDER-EXECUTE") !== "running") return {};
    return {
      "EDIT-01-BTN-OUTPUT-SAVE": "saved",
      "EDIT-01-LBL-ERROR-STATE": keep(undefined, current("EDIT-01-LBL-ERROR-STATE"), "none"),
    };
  }
  if (actionUid === "EDIT-01-ACT-HANDOFF") {
    if (current("EDIT-01-BTN-VERSION-LOCK") !== "locked") return {};
    return {
      "EDIT-01-BTN-HANDOFF-2": "sent",
      "EDIT-01-LBL-PAGE-STATE": "handed_off",
    };
  }
  if (actionUid === "EDIT-01-ACT-RETURN-BLUEPRINT") {
    return { "EDIT-01-LBL-PAGE-STATE": "returned" };
  }

  if (GATED_ACTIONS.has(actionUid)) {
    return { [controlUid]: nextValue ?? statusFromAction(actionUid) };
  }
  return {};
}
