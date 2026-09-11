import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("CORE Project and Topic selection do not invent an undefined default work item", async () => {
  const state = await read("src/domain/core/coreClientState.ts");

  assert.match(
    state,
    /case "CORE-01-ACT-PROJECT-SELECT":[\s\S]*?work_item: null/,
    "Project selection must clear dependent work-item state unless Current Authority defines a unique default",
  );

  assert.match(
    state,
    /case "CORE-01-ACT-TOPIC-SELECT":[\s\S]*?work_item: null/,
    "Topic selection must not invent TOPIC_SCOPE or any other default work item without Current Authority",
  );
});

test("CORE context switches clear stale downstream interaction state", async () => {
  const state = await read("src/domain/core/coreClientState.ts");

  for (const expected of [
    "conversation_id: null",
    "thread_ref: null",
    "candidate_ref: null",
    "composer_message_refs: []",
    "decision_evidence_refs: []",
    "attachment_refs: []",
    "reference_refs: []",
  ]) {
    assert.ok(state.includes(expected), expected);
  }
});

test("CORE pilot does not bypass unresolved formal Project Confirm or Blueprint materializer blockers", async () => {
  const visual = await read("src/components/pages/CoreVisual.tsx");
  const runtime = await read("src/server/core/productionCoreGovernedRuntime.ts");

  assert.match(visual, /PROJECT_CONFIRM_ADOPT_CONTRACT_NOT_BOUND/);
  assert.match(runtime, /PROJECT_CONFIRM_ADOPT_CONTRACT_NOT_BOUND/);
  assert.match(visual, /CORE_BLUEPRINT_DOCUMENT_MATERIALIZER_NOT_BOUND/);
});

test("CORE route and runtime registry remain aligned at the current 35-action and 21-port boundary", async () => {
  const page = await read("src/app/core/page.tsx");
  const contract = await read("src/domain/core/coreRuntimeContract.ts");

  const actionBlock = contract.match(/export const CORE_ACTION_UIDS = \[([\s\S]*?)\] as const;/)?.[1] ?? "";
  const portBlock = contract.match(/export const CORE_PORT_UIDS = \[([\s\S]*?)\] as const;/)?.[1] ?? "";
  const actionCount = (actionBlock.match(/"CORE-01-ACT-/g) ?? []).length;
  const portCount = (portBlock.match(/"CORE-01-PORT-/g) ?? []).length;

  assert.equal(actionCount, 35);
  assert.equal(portCount, 21);
  assert.match(page, /CORE_ACTION_UIDS\.length !== 35/);
  assert.match(page, /CORE_PORT_UIDS\.length !== 21/);
});
