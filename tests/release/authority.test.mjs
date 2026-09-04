import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const manifest = await readFile("authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml", "utf8");
const system = await readFile("authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml", "utf8");
const sysPage = await readFile("authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml", "utf8");
const sysClientState = await readFile("src/domain/system/systemClientState.ts", "utf8");
const editPage = await readFile("authority/pages/workspace/EDIT-01/ACPOS_EDIT-01_FINAL_LOCKED_ENCODING_SCRIPT_CONTENT_CLOSED_V1.1.yaml", "utf8");
const editClientState = await readFile("src/domain/edit/editClientState.ts", "utf8");

test("Current Authority contains exactly 18 unique page authorities", () => {
  const pages = [...manifest.matchAll(/^  - (authority\/pages\/[^\n]+)$/gm)].map((match) => match[1]);
  assert.equal(pages.length, 18);
  assert.equal(new Set(pages).size, 18);
  assert.match(manifest, /current_page_count:\s*18/);
});

test("Production Script V1.3 remains the current integration contract", () => {
  assert.match(manifest, /production_script_v1_3:/);
  assert.match(system, /ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1\.3\.yaml/);
  assert.doesNotMatch(manifest, /PRODUCTION_SCRIPT.*V1\.2/);
});

test("System implementation truth is not silently promoted", () => {
  assert.match(system, /api_binding:\s*NOT_EXECUTED/);
  assert.match(system, /database_binding:\s*NOT_EXECUTED/);
  assert.match(system, /deployment:\s*NOT_EXECUTED/);
});

test("SYS-01 mode switching remains Authority-defined client state with continuity preservation", () => {
  for (const controlId of [
    "SYS-01-BTN-SINGLE-AI",
    "SYS-01-BTN-MULTI-AI",
    "SYS-01-BTN-COUNCIL-DISCUSSION",
    "SYS-01-BTN-COUNCIL-PARALLEL",
  ]) {
    const control = sysPage.match(new RegExp(`- control_uid: ${controlId}([\\s\\S]*?)(?=\\n  - control_uid:|\\n  actions:)`));
    assert.ok(control, `${controlId} must remain in current SYS-01 Authority`);
    assert.match(control[1], /api_required:\s*false/);
  }

  assert.match(sysPage, /binding_kind:\s*CLIENT_STATE_OR_VIEW_NO_API_REQUIRED/);
  assert.match(sysPage, /mode_switch_must_not_change_SYSTEM_CHANGE_ID/);
  assert.match(sysPage, /mode_switch_must_not_create_new_conversation_or_thread/);
  assert.match(sysPage, /mode_switch_must_preserve_draft_and_source_refs/);

  for (const action of ["AI_MODE_SINGLE", "AI_MODE_MULTI", "COUNCIL_DISCUSSION", "COUNCIL_PARALLEL"]) {
    const branch = sysClientState.match(new RegExp(`case ["']${action}["']:\\s*([\\s\\S]*?)(?=\\n    case |\\n  \\})`));
    assert.ok(branch, `${action} reducer branch must remain materialized`);
    assert.match(branch[1], /\.\.\.state|return state/);
    assert.doesNotMatch(branch[1], /system_change_id\s*:|conversation_id\s*:|thread_id\s*:|branch_id\s*:|draft\s*:|attachment_refs\s*:|selected_reference_ref\s*:/);
  }

  assert.match(sysClientState, /case ["']COUNCIL_DISCUSSION["']:\s*return state\.ai_mode === ["']MULTI_AI["']/);
  assert.match(sysClientState, /case ["']COUNCIL_PARALLEL["']:\s*return state\.ai_mode === ["']MULTI_AI["']/);
});

test("SYS-01 draft remains local-only state and mode changes do not clear it", () => {
  const draftControl = sysPage.match(/- control_uid: SYS-01-INP-MESSAGE([\s\S]*?)(?=\n  - control_uid:|\n  actions:)/);
  assert.ok(draftControl, "SYS-01 message draft control must remain in current Authority");
  assert.match(draftControl[1], /binding_kind:\s*LOCAL_DRAFT_STATE_ONLY_IN_VISUAL_PHASE/);
  assert.match(draftControl[1], /api_required:\s*false/);
  assert.match(sysClientState, /case ["']DRAFT["']:\s*return \{ \.\.\.state, draft: action\.value \};/);
});

test("EDIT-01 UI-only actions remain client-only and cannot mutate governed production objects", () => {
  const uiOnly = editPage.match(/- effect_type: UI_ONLY([\s\S]*?)(?=\n  - effect_type:)/);
  assert.ok(uiOnly, "EDIT-01 UI_ONLY authority contract must remain present");
  assert.match(uiOnly[1], /allowed_changes:\s*Selection \/ Viewport \/ Playhead \/ Range \/ Preview \/ Compare/);
  assert.match(uiOnly[1], /forbidden:\s*不得修改 Working Draft、Version、Output、Evidence/);

  for (const action of [
    "PLAY",
    "PAUSE",
    "SEEK",
    "RANGE_IN",
    "RANGE_OUT",
    "RANGE_CLEAR",
    "RATE",
    "LOOP",
    "MUTE",
    "PREVIEW_VOLUME",
    "SNAP",
    "ZOOM_IN",
    "ZOOM_OUT",
    "ZOOM_FIT",
    "INSPECTOR_TAB",
    "MEDIA_SEARCH",
    "MEDIA_FILTER",
    "MEDIA_SELECT",
    "ISSUE_SELECT",
    "VERSION_SELECT",
    "TRACK_SELECT",
    "CLIP_SELECT",
    "SUBTITLE_TOGGLE",
    "AUDIO_MONITOR",
    "VIEW_ACTION",
  ]) {
    const branch = editClientState.match(new RegExp(`case["']${action}["']:\\s*([\\s\\S]*?)(?=case["']|\\n  \\})`));
    assert.ok(branch, `${action} reducer branch must remain materialized`);
    assert.doesNotMatch(branch[1], /working_draft_ref\s*:|saved_edit_version_id\s*:|output_version_id\s*:|draft_dirty\s*:\s*true|page_state_uid\s*:\s*["']EDIT-01-ST-PAGE-EVAL_REQUIRED["']/);
  }
});

test("EDIT-01 UI-only reducer stays separated from draft mutation helper", () => {
  assert.match(editClientState, /case["']LOCAL_ACTION["'][\s\S]*?draft_dirty:action\.dirty\?true:state\.draft_dirty/);
  assert.match(editClientState, /action\.dirty\?\{\.\.\.state\.resolved,page_state_uid:["']EDIT-01-ST-PAGE-EVAL_REQUIRED["']\}:state\.resolved/);
  assert.doesNotMatch(editClientState, /case["'](?:PLAY|PAUSE|SEEK|RANGE_IN|RANGE_OUT|RANGE_CLEAR|RATE|LOOP|MUTE|PREVIEW_VOLUME|SNAP|ZOOM_IN|ZOOM_OUT|ZOOM_FIT)["'][\s\S]{0,240}?LOCAL_ACTION/);
});
