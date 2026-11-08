// EDIT-01 client-side timeline state machine.
// Pure functions over an immutable state; the UI layer owns the instance and
// mirrors key values (timecode / range / clip fields) into the read model.
// Exact-ref rule: every clip label must come from an inbound exact reference
// (media bin / music / sfx / voice asset / subtitle text) - never invented.

export const TRACK_IDS = ["V1", "V2", "A1", "A2", "A3", "S1", "L1"] as const;
export type TimelineTrackId = (typeof TRACK_IDS)[number];

export const FRAME_SECONDS = 1 / 30;
export const MIN_CLIP_SECONDS = 0.2;
export const INITIAL_DURATION = 30;

export interface TimelineClip {
  id: string;
  track: TimelineTrackId;
  label: string;
  start: number;
  inPoint: number;
  outPoint: number;
  speed: number;
  volume: number;
  fadeIn: number;
  fadeOut: number;
  transition: string | null;
}

export interface TimelineMarker {
  id: string;
  at: number;
  note: string;
}

export interface TimelineVersion {
  label: string;
  at: string;
  clips: TimelineClip[];
}

export interface TrackFlags {
  locked: boolean;
  muted: boolean;
  solo: boolean;
  visible: boolean;
}

export interface TimelineState {
  clips: TimelineClip[];
  markers: TimelineMarker[];
  playhead: number;
  duration: number;
  rangeIn: number | null;
  rangeOut: number | null;
  selectedClipId: string | null;
  zoom: number;
  tool: "select" | "razor";
  trackFlags: Record<TimelineTrackId, TrackFlags>;
  versions: TimelineVersion[];
  past: Pick<TimelineState, "clips" | "markers" | "rangeIn" | "rangeOut" | "selectedClipId" | "duration">[];
  future: Pick<TimelineState, "clips" | "markers" | "rangeIn" | "rangeOut" | "selectedClipId" | "duration">[];
}

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 8;

function emptyFlags(): Record<TimelineTrackId, TrackFlags> {
  const flags = {} as Record<TimelineTrackId, TrackFlags>;
  for (const id of TRACK_IDS) {
    flags[id] = { locked: false, muted: false, solo: false, visible: true };
  }
  return flags;
}

export function emptyTimeline(): TimelineState {
  return {
    clips: [],
    markers: [],
    playhead: 0,
    duration: INITIAL_DURATION,
    rangeIn: null,
    rangeOut: null,
    selectedClipId: null,
    zoom: 1,
    tool: "select",
    trackFlags: emptyFlags(),
    versions: [],
    past: [],
    future: [],
  };
}

function snapshot(state: TimelineState): TimelineState["past"][number] {
  return {
    clips: state.clips.map((clip) => ({ ...clip })),
    markers: state.markers.map((marker) => ({ ...marker })),
    rangeIn: state.rangeIn,
    rangeOut: state.rangeOut,
    selectedClipId: state.selectedClipId,
    duration: state.duration,
  };
}

function withHistory(state: TimelineState, patch: Partial<TimelineState>): TimelineState {
  return {
    ...state,
    ...patch,
    past: [...state.past.slice(-49), snapshot(state)],
    future: [],
  };
}

function clampNumber(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function nextId(state: TimelineState, prefix: string): string {
  const used = new Set<string>();
  for (const clip of state.clips) used.add(clip.id);
  for (const marker of state.markers) used.add(marker.id);
  let index = 1;
  while (used.has(`${prefix}-${index}`)) index += 1;
  return `${prefix}-${index}`;
}

export function trackEditable(state: TimelineState, track: TimelineTrackId): boolean {
  const flags = state.trackFlags[track];
  if (flags.locked) return false;
  const soloed = TRACK_IDS.some((id) => state.trackFlags[id].solo);
  return !soloed || flags.solo;
}

export function findClip(state: TimelineState, clipId: string | null): TimelineClip | null {
  if (!clipId) return null;
  return state.clips.find((clip) => clip.id === clipId) ?? null;
}

export function selectedClip(state: TimelineState): TimelineClip | null {
  return findClip(state, state.selectedClipId);
}

export function trackEnd(state: TimelineState, track: TimelineTrackId): number {
  let end = 0;
  for (const clip of state.clips) {
    if (clip.track === track && clip.start + (clip.outPoint - clip.inPoint) > end) {
      end = clip.start + (clip.outPoint - clip.inPoint);
    }
  }
  return end;
}

export function timelineEnd(state: TimelineState): number {
  let end = 0;
  for (const id of TRACK_IDS) {
    const trackEndValue = trackEnd(state, id);
    if (trackEndValue > end) end = trackEndValue;
  }
  return Math.max(end, state.duration);
}

function growDuration(state: TimelineState, patch: Partial<TimelineState>): Partial<TimelineState> {
  const next = { ...state, ...patch };
  const end = timelineEnd(next);
  return end > next.duration ? { ...patch, duration: Math.ceil(end + 5) } : patch;
}

export function importClip(
  state: TimelineState,
  track: TimelineTrackId,
  label: string,
  lengthSeconds: number,
): TimelineState {
  if (!label) return state;
  if (!trackEditable(state, track)) return state;
  const length = clampNumber(Number.isFinite(lengthSeconds) ? lengthSeconds : 5, MIN_CLIP_SECONDS, 600);
  const start = snapValue(state, trackEnd(state, track));
  const clip: TimelineClip = {
    id: nextId(state, "CL"),
    track,
    label,
    start,
    inPoint: 0,
    outPoint: length,
    speed: 1,
    volume: 1,
    fadeIn: 0,
    fadeOut: 0,
    transition: null,
  };
  return withHistory(state, growDuration(state, {
    clips: [...state.clips, clip],
    selectedClipId: clip.id,
  }));
}

export function selectClip(state: TimelineState, clipId: string | null): TimelineState {
  if (clipId && !findClip(state, clipId)) return state;
  return { ...state, selectedClipId: clipId };
}

export function setTool(state: TimelineState, tool: TimelineState["tool"]): TimelineState {
  return { ...state, tool };
}

export function seek(state: TimelineState, at: number): TimelineState {
  const end = timelineEnd(state);
  const playhead = clampNumber(at, 0, end);
  return { ...state, playhead };
}

export function stepFrame(state: TimelineState, direction: 1 | -1): TimelineState {
  return seek(state, state.playhead + direction * FRAME_SECONDS);
}

export function snapValue(state: TimelineState, value: number): number {
  if (state.rangeIn == null && state.rangeOut == null) return Math.round(value * 100) / 100;
  const candidates: number[] = [state.playhead, 0];
  if (state.rangeIn != null) candidates.push(state.rangeIn);
  if (state.rangeOut != null) candidates.push(state.rangeOut);
  for (const clip of state.clips) {
    candidates.push(clip.start, clip.start + (clip.outPoint - clip.inPoint));
  }
  const threshold = 0.25;
  let best = value;
  let bestGap = threshold;
  for (const candidate of candidates) {
    const gap = Math.abs(candidate - value);
    if (gap < bestGap) {
      best = candidate;
      bestGap = gap;
    }
  }
  return Math.round(best * 100) / 100;
}

function splitClip(state: TimelineState, clip: TimelineClip, at: number): TimelineClip[] | null {
  const length = clip.outPoint - clip.inPoint;
  const offset = at - clip.start;
  if (offset < MIN_CLIP_SECONDS || length - offset < MIN_CLIP_SECONDS) return null;
  const left: TimelineClip = { ...clip, outPoint: clip.inPoint + offset };
  const right: TimelineClip = {
    ...clip,
    id: nextId(state, "CL"),
    start: clip.start + offset,
    inPoint: clip.inPoint + offset,
    fadeIn: 0,
    transition: null,
  };
  return [left, right];
}

export function splitSelected(state: TimelineState): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track)) return state;
  const pair = splitClip(state, clip, state.playhead);
  if (!pair) return state;
  return withHistory(state, {
    clips: state.clips.flatMap((row) => (row.id === clip.id ? pair : [row])),
    selectedClipId: pair[1].id,
  });
}

export function razorSplitAt(state: TimelineState, track: TimelineTrackId, at: number): TimelineState {
  if (!trackEditable(state, track)) return state;
  const clip = state.clips.find(
    (row) => row.track === track && at >= row.start && at <= row.start + (row.outPoint - row.inPoint),
  );
  if (!clip) return state;
  const pair = splitClip(state, clip, at);
  if (!pair) return state;
  return withHistory(state, {
    clips: state.clips.flatMap((row) => (row.id === clip.id ? pair : [row])),
    selectedClipId: pair[1].id,
  });
}

function trimPatch(state: TimelineState, clipId: string, patch: (clip: TimelineClip) => TimelineClip): Partial<TimelineState> {
  return {
    clips: state.clips.map((row) => (row.id === clipId ? patch(row) : row)),
  };
}

export function trimSelectedStart(state: TimelineState): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track)) return state;
  const offset = state.playhead - clip.start;
  if (offset < 0 || clip.outPoint - clip.inPoint - offset < MIN_CLIP_SECONDS) return state;
  return withHistory(state, trimPatch(state, clip.id, (row) => ({
    ...row,
    start: state.playhead,
    inPoint: row.inPoint + offset,
    fadeIn: Math.max(0, row.fadeIn - offset),
  })));
}

export function trimSelectedEnd(state: TimelineState): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track)) return state;
  const offset = state.playhead - clip.start;
  const length = clip.outPoint - clip.inPoint;
  if (offset < MIN_CLIP_SECONDS || offset >= length) return state;
  return withHistory(state, growDuration(state, trimPatch(state, clip.id, (row) => ({
    ...row,
    outPoint: row.inPoint + offset,
    fadeOut: Math.min(row.fadeOut, Math.max(0, length - offset)),
  }))));
}

export function moveSelected(state: TimelineState, deltaSeconds: number): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track)) return state;
  const start = Math.max(0, snapValue(state, clip.start + deltaSeconds));
  if (start === clip.start) return state;
  return withHistory(state, growDuration(state, trimPatch(state, clip.id, (row) => ({ ...row, start }))));
}

export function reorderSelected(state: TimelineState, direction: 1 | -1): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track)) return state;
  const siblings = state.clips
    .filter((row) => row.track === clip.track)
    .sort((a, b) => a.start - b.start);
  const index = siblings.findIndex((row) => row.id === clip.id);
  const neighbor = siblings[index + direction];
  if (!neighbor) return state;
  const neighborLength = neighbor.outPoint - neighbor.inPoint;
  return withHistory(state, growDuration(state, {
    clips: state.clips.map((row) => {
      if (row.id === clip.id) return { ...row, start: neighbor.start };
      if (row.id === neighbor.id) return { ...row, start: clip.start };
      return row;
    }),
    duration: Math.max(state.duration, neighbor.start + neighborLength + (clip.outPoint - clip.inPoint) + 1),
  }));
}

export function deleteSelected(state: TimelineState): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track)) return state;
  return withHistory(state, {
    clips: state.clips.filter((row) => row.id !== clip.id),
    selectedClipId: null,
  });
}

export function duplicateSelected(state: TimelineState): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track)) return state;
  const copy: TimelineClip = {
    ...clip,
    id: nextId(state, "CL"),
    start: snapValue(state, clip.start + (clip.outPoint - clip.inPoint)),
  };
  return withHistory(state, growDuration(state, {
    clips: [...state.clips, copy],
    selectedClipId: copy.id,
  }));
}

export function replaceSelected(state: TimelineState, label: string): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track) || !label) return state;
  return withHistory(state, trimPatch(state, clip.id, (row) => ({ ...row, label })));
}

export function patchSelected(
  state: TimelineState,
  patch: Partial<Pick<TimelineClip, "speed" | "volume" | "fadeIn" | "fadeOut" | "transition">>,
): TimelineState {
  const clip = selectedClip(state);
  if (!clip || !trackEditable(state, clip.track)) return state;
  const safe: Partial<TimelineClip> = {};
  if (patch.speed != null) safe.speed = clampNumber(patch.speed, 0.25, 4);
  if (patch.volume != null) safe.volume = clampNumber(patch.volume, 0, 1.5);
  if (patch.fadeIn != null) safe.fadeIn = clampNumber(patch.fadeIn, 0, clip.outPoint - clip.inPoint);
  if (patch.fadeOut != null) safe.fadeOut = clampNumber(patch.fadeOut, 0, clip.outPoint - clip.inPoint);
  if (patch.transition !== undefined) safe.transition = patch.transition;
  return withHistory(state, trimPatch(state, clip.id, (row) => ({ ...row, ...safe })));
}

export function setRangeIn(state: TimelineState): TimelineState {
  const inPoint = state.playhead;
  if (state.rangeOut != null && inPoint > state.rangeOut) return state;
  return withHistory(state, { rangeIn: inPoint });
}

export function setRangeOut(state: TimelineState): TimelineState {
  const outPoint = state.playhead;
  if (state.rangeIn != null && outPoint < state.rangeIn) return state;
  return withHistory(state, growDuration(state, { rangeOut: outPoint }));
}

export function clearRange(state: TimelineState): TimelineState {
  if (state.rangeIn == null && state.rangeOut == null) return state;
  return withHistory(state, { rangeIn: null, rangeOut: null });
}

export function addMarker(state: TimelineState, note: string): TimelineState {
  const marker: TimelineMarker = {
    id: nextId(state, "MK"),
    at: state.playhead,
    note: note || `mark`,
  };
  return withHistory(state, {
    markers: [...state.markers.filter((row) => row.id !== marker.id || Math.abs(row.at - marker.at) > 0.01), marker].sort((a, b) => a.at - b.at),
  });
}

export function jumpToNearestMarker(state: TimelineState): TimelineState {
  if (!state.markers.length) return state;
  const nearest = [...state.markers].sort(
    (a, b) => Math.abs(a.at - state.playhead) - Math.abs(b.at - state.playhead),
  )[0];
  return seek(state, nearest.at);
}

export function setZoom(state: TimelineState, zoom: number): TimelineState {
  return { ...state, zoom: clampNumber(zoom, MIN_ZOOM, MAX_ZOOM) };
}

export function zoomIn(state: TimelineState): TimelineState {
  return setZoom(state, state.zoom * 1.5);
}

export function zoomOut(state: TimelineState): TimelineState {
  return setZoom(state, state.zoom / 1.5);
}

export function zoomFit(state: TimelineState): TimelineState {
  return setZoom(state, 1);
}

export function toggleTrackFlag(
  state: TimelineState,
  track: TimelineTrackId,
  key: keyof Omit<TrackFlags, never>,
): TimelineState {
  const flags = state.trackFlags[track];
  return {
    ...state,
    trackFlags: { ...state.trackFlags, [track]: { ...flags, [key]: !flags[key] } },
  };
}

export function saveVersion(state: TimelineState, label: string): TimelineState {
  const version: TimelineVersion = {
    label,
    at: new Date().toISOString().slice(0, 19).replace("T", " "),
    clips: state.clips.map((clip) => ({ ...clip })),
  };
  return { ...state, versions: [...state.versions, version] };
}

export function restoreVersion(state: TimelineState, index: number): TimelineState {
  const version = state.versions[index];
  if (!version) return state;
  return withHistory(state, {
    clips: version.clips.map((clip) => ({ ...clip })),
    markers: state.markers,
    selectedClipId: null,
  });
}

export function undo(state: TimelineState): TimelineState {
  const previous = state.past[state.past.length - 1];
  if (!previous) return state;
  return {
    ...state,
    clips: previous.clips,
    markers: previous.markers,
    rangeIn: previous.rangeIn,
    rangeOut: previous.rangeOut,
    selectedClipId: previous.selectedClipId,
    duration: previous.duration,
    past: state.past.slice(0, -1),
    future: [snapshot(state), ...state.future].slice(0, 50),
  };
}

export function redo(state: TimelineState): TimelineState {
  const next = state.future[0];
  if (!next) return state;
  return {
    ...state,
    clips: next.clips,
    markers: next.markers,
    rangeIn: next.rangeIn,
    rangeOut: next.rangeOut,
    selectedClipId: next.selectedClipId,
    duration: next.duration,
    past: [...state.past, snapshot(state)],
    future: state.future.slice(1),
  };
}

export function formatTimecode(seconds: number): string {
  const safe = Number.isFinite(seconds) && seconds >= 0 ? seconds : 0;
  const total = Math.floor(safe);
  const frames = Math.round((safe - total) * 30);
  const hh = String(Math.floor(total / 3600)).padStart(2, "0");
  const mm = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  const ff = String(Math.min(29, frames)).padStart(2, "0");
  return `${hh}:${mm}:${ss}:${ff}`;
}

export function timecodeToSeconds(value: string): number | null {
  const match = /^(\d{1,2}):(\d{2}):(\d{2}):(\d{2})$/.exec(value.trim());
  if (!match) return null;
  const [, hh, mm, ss, ff] = match;
  return Number(hh) * 3600 + Number(mm) * 60 + Number(ss) + Number(ff) / 30;
}
