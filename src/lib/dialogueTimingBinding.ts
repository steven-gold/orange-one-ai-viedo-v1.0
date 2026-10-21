import { exactName } from "./conversationCore";

export const DIALOGUE_TIMING_KIND = "DIALOGUE_TIMING_BINDING";

export type DialogueBindingStatus = "CURRENT" | "STALE" | "REVERIFY_REQUIRED" | "MISMATCH" | "UNBOUND";

export type DialogueTimingBinding = {
  kind: typeof DIALOGUE_TIMING_KIND;
  status: DialogueBindingStatus;
  dialogue_script_ref: string;
  voice_segment_ref: string;
  subtitle_cue_ref: string;
  lipsync_target_ref: string;
  source_version: string;
  hash: string;
};

const STATUS_SET = new Set<DialogueBindingStatus>([
  "CURRENT",
  "STALE",
  "REVERIFY_REQUIRED",
  "MISMATCH",
  "UNBOUND",
]);

export const DIALOGUE_LIPSYNC_BINDING_UID = "EDIT-01-LBL-LIPSYNC-SYNC-BINDING";
export const DIALOGUE_SUBTITLE_BINDING_UID = "EDIT-01-LBL-SUB-SYNC-BINDING";

type CurrentFn = (uid: string) => string | null;

function sourceHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function textOf(rec: Record<string, unknown>, key: string): string {
  return typeof rec[key] === "string" ? String(rec[key]).trim() : "";
}

function named(value: string | null | undefined): string {
  return exactName(value);
}

export function parseDialogueTimingBinding(raw: string | null | undefined): DialogueTimingBinding | undefined {
  if (!raw) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;
    const rec = parsed as Record<string, unknown>;
    if (rec.kind !== DIALOGUE_TIMING_KIND) return undefined;
    const status = textOf(rec, "status");
    if (!STATUS_SET.has(status as DialogueBindingStatus)) return undefined;
    return {
      kind: DIALOGUE_TIMING_KIND,
      status: status as DialogueBindingStatus,
      dialogue_script_ref: textOf(rec, "dialogue_script_ref"),
      voice_segment_ref: textOf(rec, "voice_segment_ref"),
      subtitle_cue_ref: textOf(rec, "subtitle_cue_ref"),
      lipsync_target_ref: textOf(rec, "lipsync_target_ref"),
      source_version: textOf(rec, "source_version"),
      hash: textOf(rec, "hash"),
    };
  } catch {
    return undefined;
  }
}

export function serializeDialogueTimingBinding(binding: DialogueTimingBinding): string {
  return JSON.stringify(binding);
}

export function dialogueTracksInUse(current: CurrentFn): boolean {
  return Boolean(
    named(current("EDIT-01-FLD-VOICE-SCRIPT")) ||
      named(current("EDIT-01-FLD-VOICE-ASSET")) ||
      named(current("EDIT-01-LST-VOICE-TAKES")) ||
      named(current("EDIT-01-FLD-LIPSYNC-TARGET")) ||
      named(current("EDIT-01-FLD-SUB-TEXT")) ||
      named(current("EDIT-01-FLD-SUB-TIMECODE")),
  );
}

function liveRefs(current: CurrentFn): {
  dialogue_script_ref: string;
  voice_segment_ref: string;
  subtitle_cue_ref: string;
  lipsync_target_ref: string;
  source_version: string;
} {
  return {
    dialogue_script_ref: named(current("EDIT-01-FLD-VOICE-SCRIPT")) || named(current("EDIT-01-LBL-CURRENT-SCRIPT-SECTION")),
    voice_segment_ref: named(current("EDIT-01-FLD-VOICE-ASSET")) || named(current("EDIT-01-LST-VOICE-TAKES")),
    subtitle_cue_ref: named(current("EDIT-01-FLD-SUB-TEXT")) || named(current("EDIT-01-FLD-SUB-TIMECODE")),
    lipsync_target_ref: named(current("EDIT-01-FLD-LIPSYNC-TARGET")),
    source_version: named(current("EDIT-01-FLD-SOURCE-VERSION")),
  };
}

function withHash(input: Omit<DialogueTimingBinding, "kind" | "hash">): DialogueTimingBinding {
  const hash = sourceHash([
    input.status,
    input.dialogue_script_ref,
    input.voice_segment_ref,
    input.subtitle_cue_ref,
    input.lipsync_target_ref,
    input.source_version,
  ]);
  return { kind: DIALOGUE_TIMING_KIND, ...input, hash };
}

export function buildDialogueTimingBinding(
  current: CurrentFn,
  status: DialogueBindingStatus,
  overrides: Partial<Omit<DialogueTimingBinding, "kind" | "hash" | "status">> = {},
): DialogueTimingBinding {
  const live = liveRefs(current);
  return withHash({
    status,
    dialogue_script_ref: overrides.dialogue_script_ref ?? live.dialogue_script_ref,
    voice_segment_ref: overrides.voice_segment_ref ?? live.voice_segment_ref,
    subtitle_cue_ref: overrides.subtitle_cue_ref ?? live.subtitle_cue_ref,
    lipsync_target_ref: overrides.lipsync_target_ref ?? live.lipsync_target_ref,
    source_version: overrides.source_version ?? live.source_version,
  });
}

export function resolveDialogueTimingBinding(current: CurrentFn): DialogueTimingBinding {
  const stored =
    parseDialogueTimingBinding(current(DIALOGUE_LIPSYNC_BINDING_UID)) ||
    parseDialogueTimingBinding(current(DIALOGUE_SUBTITLE_BINDING_UID));
  const live = liveRefs(current);
  if (!dialogueTracksInUse(current) && !stored) {
    return withHash({
      status: "UNBOUND",
      dialogue_script_ref: live.dialogue_script_ref,
      voice_segment_ref: live.voice_segment_ref,
      subtitle_cue_ref: live.subtitle_cue_ref,
      lipsync_target_ref: live.lipsync_target_ref,
      source_version: live.source_version,
    });
  }
  if (!stored) {
    const mismatch = Boolean(live.voice_segment_ref && live.lipsync_target_ref && live.voice_segment_ref !== live.lipsync_target_ref);
    return withHash({
      status: mismatch ? "MISMATCH" : live.voice_segment_ref || live.lipsync_target_ref || live.subtitle_cue_ref ? "STALE" : "UNBOUND",
      ...live,
    });
  }
  if (live.source_version && stored.source_version && live.source_version !== stored.source_version) {
    return withHash({ ...stored, ...live, status: "STALE" });
  }
  const voiceDrift = Boolean(live.voice_segment_ref && stored.voice_segment_ref && live.voice_segment_ref !== stored.voice_segment_ref);
  const lipsyncDrift = Boolean(live.lipsync_target_ref && stored.lipsync_target_ref && live.lipsync_target_ref !== stored.lipsync_target_ref);
  const scriptDrift = Boolean(live.dialogue_script_ref && stored.dialogue_script_ref && live.dialogue_script_ref !== stored.dialogue_script_ref);
  if (scriptDrift || (voiceDrift && (stored.lipsync_target_ref || stored.subtitle_cue_ref))) {
    return withHash({ ...stored, ...live, status: voiceDrift || scriptDrift ? "REVERIFY_REQUIRED" : stored.status });
  }
  if (lipsyncDrift && stored.voice_segment_ref && live.lipsync_target_ref !== stored.voice_segment_ref) {
    return withHash({ ...stored, ...live, status: "MISMATCH" });
  }
  return stored;
}

export function dialogueBindingPatch(binding: DialogueTimingBinding): Record<string, string> {
  const raw = serializeDialogueTimingBinding(binding);
  return {
    [DIALOGUE_LIPSYNC_BINDING_UID]: raw,
    [DIALOGUE_SUBTITLE_BINDING_UID]: raw,
  };
}

export function dialogueBindingAllowsSyncPass(current: CurrentFn): boolean {
  if (!dialogueTracksInUse(current)) return true;
  return resolveDialogueTimingBinding(current).status === "CURRENT";
}

export function dialogueBindingAllowsLock(current: CurrentFn): boolean {
  return dialogueBindingAllowsSyncPass(current);
}

export function dialogueBindingAllowsRender(current: CurrentFn): boolean {
  return dialogueBindingAllowsSyncPass(current);
}

export function dialogueBindingStatusLabel(status: DialogueBindingStatus): string {
  if (status === "CURRENT") return "目前有效";
  if (status === "STALE") return "已過期";
  if (status === "REVERIFY_REQUIRED") return "須重新核對";
  if (status === "MISMATCH") return "不符";
  return "";
}
