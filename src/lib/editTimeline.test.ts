import assert from "node:assert/strict";
import { test } from "node:test";
import {
  addMarker,
  clearRange,
  deleteSelected,
  dragClipTo,
  duplicateSelected,
  emptyTimeline,
  findClip,
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
  seek,
  selectedClip,
  selectClip,
  setRangeIn,
  setRangeOut,
  setTool,
  splitSelected,
  stepFrame,
  timecodeToSeconds,
  toggleTrackFlag,
  trackEditable,
  trimSelectedEnd,
  trimSelectedStart,
  undo,
  zoomFit,
  zoomIn,
  zoomOut,
} from "./editTimeline";

function seeded() {
  let state = emptyTimeline();
  state = importClip(state, "V1", "session-media", 10);
  state = seek(state, 4);
  return state;
}

test("import places clip at track end and selects it", () => {
  let state = seeded();
  state = importClip(state, "V1", "session-media", 6);
  const clip = selectedClip(state);
  assert.ok(clip);
  assert.equal(clip.track, "V1");
  assert.equal(clip.start, 10);
  assert.equal(clip.inPoint, 0);
  assert.equal(clip.outPoint, 6);
});

test("import is blocked on locked tracks", () => {
  let state = seeded();
  state = toggleTrackFlag(state, "V1", "locked");
  assert.equal(trackEditable(state, "V1"), false);
  const before = state.clips.length;
  state = importClip(state, "V1", "session-media", 5);
  assert.equal(state.clips.length, before);
});

test("split divides selected clip at playhead", () => {
  let state = seeded();
  state = splitSelected(state);
  const clips = state.clips.filter((clip) => clip.track === "V1");
  assert.equal(clips.length, 2);
  const [left, right] = clips;
  assert.equal(left.outPoint, 4);
  assert.equal(right.inPoint, 4);
  assert.equal(right.start, 4);
  assert.equal(state.selectedClipId, right.id);
});

test("split outside clip bounds is a no-op", () => {
  let state = seeded();
  state = seek(state, 12);
  const untouched = state.clips.length;
  state = splitSelected(state);
  assert.equal(state.clips.length, untouched);
});

test("razor splits the clip under the cursor without selection", () => {
  let state = seeded();
  state = selectClip(state, null);
  state = razorSplitAt(state, "V1", 6);
  assert.equal(state.clips.filter((clip) => clip.track === "V1").length, 2);
});

test("trim start and end respect playhead and min length", () => {
  let state = seeded();
  state = seek(state, 3);
  state = trimSelectedStart(state);
  let clip = selectedClip(state);
  assert.ok(clip);
  assert.equal(clip.start, 3);
  assert.equal(clip.inPoint, 3);
  state = seek(state, 5);
  state = trimSelectedEnd(state);
  clip = selectedClip(state);
  assert.ok(clip);
  assert.equal(clip.outPoint, 5);
  state = seek(state, 4.9);
  state = trimSelectedEnd(state);
  assert.equal(selectedClip(state)?.outPoint, 4.9);
});

test("move clamps at zero and snaps", () => {
  let state = seeded();
  state = moveSelected(state, -8);
  assert.equal(selectedClip(state)?.start, 0);
  state = moveSelected(state, 3);
  assert.equal(selectedClip(state)?.start, 3);
});

test("reorder swaps with neighbor on same track", () => {
  let state = seeded();
  state = seek(state, 4);
  state = splitSelected(state);
  state = selectClip(state, findClip(state, state.selectedClipId)!.id);
  const [left, right] = state.clips.filter((clip) => clip.track === "V1");
  state = selectClip(state, left.id);
  state = reorderSelected(state, 1);
  const moved = state.clips.find((clip) => clip.id === left.id)!;
  assert.equal(moved.start, right.start);
});

test("delete and duplicate act on selection", () => {
  let state = seeded();
  state = duplicateSelected(state);
  assert.equal(state.clips.length, 2);
  assert.ok(state.selectedClipId);
  state = deleteSelected(state);
  assert.equal(state.clips.length, 1);
  assert.equal(state.selectedClipId, null);
});

test("replace swaps the exact ref label", () => {
  let state = seeded();
  state = replaceSelected(state, "session-spec");
  assert.equal(selectedClip(state)?.label, "session-spec");
  state = replaceSelected(state, "");
  assert.equal(selectedClip(state)?.label, "session-spec");
});

test("inspector patch clamps values", () => {
  let state = seeded();
  state = patchSelected(state, { volume: 9, speed: 100, fadeIn: 3, fadeOut: 3 });
  const clip = selectedClip(state)!;
  assert.equal(clip.volume, 1.5);
  assert.equal(clip.speed, 4);
  assert.equal(clip.fadeIn, 3);
  assert.equal(clip.fadeOut, 3);
  state = patchSelected(state, { transition: "cross" });
  assert.equal(selectedClip(state)?.transition, "cross");
});

test("range in/out keep in <= out and clear resets", () => {
  let state = seeded();
  state = setRangeIn(state);
  assert.equal(state.rangeIn, 4);
  state = seek(state, 8);
  state = setRangeOut(state);
  assert.equal(state.rangeOut, 8);
  state = seek(state, 2);
  state = setRangeOut(state);
  assert.equal(state.rangeOut, 8);
  state = clearRange(state);
  assert.equal(state.rangeIn, null);
  assert.equal(state.rangeOut, null);
});

test("markers add and nearest jump works", () => {
  let state = seeded();
  state = addMarker(state, "hook");
  state = seek(state, 9);
  state = addMarker(state, "cta");
  state = seek(state, 0);
  state = jumpToNearestMarker(state);
  assert.equal(state.playhead, 4);
  state = seek(state, 8.2);
  state = jumpToNearestMarker(state);
  assert.equal(state.playhead, 9);
});

test("frame step uses 1/30s and timecode round-trips", () => {
  let state = seeded();
  state = stepFrame(state, 1);
  assert.ok(Math.abs(state.playhead - (4 + 1 / 30)) < 1e-9);
  assert.equal(formatTimecode(4 + 1 / 30), "00:00:04:01");
  assert.equal(timecodeToSeconds("00:00:04:01"), 4 + 1 / 30);
  assert.equal(timecodeToSeconds("99:99:99:99"), null);
  assert.equal(timecodeToSeconds("00:00:04:30"), null);
  assert.equal(timecodeToSeconds("bogus"), null);
});

test("undo restores previous state and redo re-applies", () => {
  let state = seeded();
  const afterImport = state.clips.length;
  state = deleteSelected(state);
  assert.equal(state.clips.length, 0);
  state = undo(state);
  assert.equal(state.clips.length, afterImport);
  assert.ok(state.selectedClipId);
  state = redo(state);
  assert.equal(state.clips.length, 0);
  state = undo(state);
  assert.equal(state.clips.length, 1);
});

test("zoom clamps to bounds and fit resets", () => {
  let state = emptyTimeline();
  state = zoomIn(state);
  state = zoomIn(state);
  state = zoomIn(state);
  assert.ok(state.zoom > 3);
  state = zoomFit(state);
  assert.equal(state.zoom, 1);
  for (let i = 0; i < 20; i += 1) state = zoomOut(state);
  assert.ok(state.zoom >= 0.5);
});

test("version save and restore round-trips with undo", () => {
  let state = seeded();
  state = splitSelected(state);
  state = saveVersion(state, "draft-1");
  assert.equal(state.versions.length, 1);
  state = deleteSelected(state);
  assert.equal(state.clips.length, 1);
  state = restoreVersion(state, 0);
  assert.equal(state.clips.length, 2);
  state = undo(state);
  assert.equal(state.clips.length, 1);
});

test("toggle track flags", () => {
  let state = emptyTimeline();
  state = toggleTrackFlag(state, "A2", "solo");
  assert.equal(trackEditable(state, "V1"), false);
  assert.equal(trackEditable(state, "A2"), true);
  state = toggleTrackFlag(state, "A2", "solo");
  assert.equal(trackEditable(state, "V1"), true);
  state = toggleTrackFlag(state, "V1", "visible");
  assert.equal(state.trackFlags.V1.visible, false);
});

test("seek clamps to timeline end", () => {
  let state = seeded();
  state = seek(state, 999);
  assert.equal(state.playhead, 30);
  state = seek(state, -5);
  assert.equal(state.playhead, 0);
});

test("drag moves clip to snapped position and respects locks", () => {
  let state = seeded();
  state = dragClipTo(state, "CL-1", 5.13);
  assert.equal(selectedClip(state)?.start, 5.13);
  state = dragClipTo(state, "CL-1", 4.15);
  assert.equal(selectedClip(state)?.start, 4);
  state = dragClipTo(state, "CL-1", -3);
  assert.equal(selectedClip(state)?.start, 0);
  state = toggleTrackFlag(state, "V1", "locked");
  state = dragClipTo(state, "CL-1", 9);
  assert.equal(selectedClip(state)?.start, 0);
});

test("tool switch", () => {
  let state = emptyTimeline();
  state = setTool(state, "razor");
  assert.equal(state.tool, "razor");
  state = setTool(state, "select");
  assert.equal(state.tool, "select");
});
