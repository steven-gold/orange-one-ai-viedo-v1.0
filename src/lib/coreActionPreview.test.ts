import { previewCoreAction } from "./coreActionPreview";
import { unavailableBody, isAiUnavailable } from "./aiReply";
import { CORE_VISIBLE_CONTROLS } from "../server/domain/core";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

function currentFrom(map: Record<string, string | null>): (uid: string) => string | null {
  return (uid) => map[uid] ?? null;
}

{
  assert(CORE_VISIBLE_CONTROLS.includes("CORE-01-FLD-TOPIC-SNAPSHOTS"), "topic snapshot field registered");
  assertEqual(CORE_VISIBLE_CONTROLS.length, 71, "CORE stays at 71 controls");
}

{
  const empty = currentFrom({});
  assertEqual(Object.keys(previewCoreAction("CORE-01-BTN-STORY-CANDIDATE", "CORE-01-ACT-STORY-CANDIDATE", empty)).length, 0, "story candidate needs project");
  const withProject = currentFrom({ "CORE-01-CTL-PROJECT": "示範專案" });
  const story = previewCoreAction("CORE-01-BTN-STORY-CANDIDATE", "CORE-01-ACT-STORY-CANDIDATE", withProject);
  assertEqual(story["CORE-01-BTN-STORY-CANDIDATE"], "created", "story candidate writes created");
  assertEqual(story["CORE-01-FLD-VERSION-STATE"], "故事候選", "story candidate names version");
  assertEqual(story["CORE-01-FLD-RUNTIME-STAGE"], "CANDIDATE", "story candidate moves stage");
  assertEqual(story["CORE-01-LST-WORK-ITEMS"], "STORY", "story candidate selects STORY");
}

{
  const empty = currentFrom({});
  assertEqual(Object.keys(previewCoreAction("CORE-01-BTN-RETURN-MODIFY", "CORE-01-ACT-CANDIDATE-RETURN", empty)).length, 0, "return needs candidate");
  const withCandidate = currentFrom({ "CORE-01-FLD-VERSION-STATE": "故事候選", "CORE-01-BTN-CANDIDATE-CONFIRM": "confirmed" });
  const returned = previewCoreAction("CORE-01-BTN-RETURN-MODIFY", "CORE-01-ACT-CANDIDATE-RETURN", withCandidate);
  assertEqual(returned["CORE-01-BTN-RETURN-MODIFY"], "returned", "return writes returned");
  assertEqual(returned["CORE-01-BTN-CANDIDATE-CONFIRM"], "", "return clears confirm");
  assertEqual(returned["CORE-01-FLD-RUNTIME-STAGE"], "HUMAN_DECISION", "return moves to human decision");
}

{
  const empty = currentFrom({});
  assertEqual(Object.keys(previewCoreAction("CORE-01-BTN-CANDIDATE-COMPARE", "CORE-01-ACT-CANDIDATE-COMPARE", empty)).length, 0, "compare needs candidate");
  const withCandidate = currentFrom({ "CORE-01-FLD-VERSION-STATE": "故事候選" });
  const compared = previewCoreAction("CORE-01-BTN-CANDIDATE-COMPARE", "CORE-01-ACT-CANDIDATE-COMPARE", withCandidate);
  assertEqual(compared["CORE-01-BTN-CANDIDATE-COMPARE"], "comparing", "compare writes comparing");
  const evaluation = JSON.parse(compared["CORE-01-FLD-EVALUATION"] ?? "{}") as { kind?: string };
  assertEqual(evaluation.kind, "CORE_COMPARE", "compare writes evaluation contract");
  assertEqual(compared["CORE-01-FLD-RUNTIME-STAGE"], "CORE_EVALUATION", "compare moves to evaluation");
}

{
  const recorded = previewCoreAction("CORE-01-FLD-HUMAN-DECISION", "CORE-01-ACT-HUMAN-DECISION-RECORD", currentFrom({}));
  assertEqual(recorded["CORE-01-FLD-HUMAN-DECISION"], "recorded", "human decision records");
  assertEqual(recorded["CORE-01-FLD-RUNTIME-STAGE"], "HUMAN_DECISION", "human decision moves stage");
  const structured = previewCoreAction("CORE-01-FLD-STRUCTURED-DECISION", "CORE-01-ACT-ASSISTANT-STRUCTURED-DECISION-CREATE", currentFrom({}));
  const decisionLog = JSON.parse(structured["CORE-01-FLD-STRUCTURED-DECISION"] ?? "{}") as { kind?: string };
  assertEqual(decisionLog.kind, "CORE_DECISION_LOG", "structured decision records log");
}

{
  const unreachable = unavailableBody({ failed: true, empty: true, providerCode: "AI_PROVIDER_UNREACHABLE" });
  assertEqual(unreachable, "目前無法取得 AI 回應（供應商無法連線）。", "unreachable body");
  assert(isAiUnavailable(unreachable), "unreachable counts as unavailable");
  const missing = unavailableBody({ providerCode: "AI_PROVIDER_NOT_CONFIGURED" });
  assertEqual(missing, "目前無法取得 AI 回應（供應商未設定或暫時無法使用）。", "not configured body");
  assert(isAiUnavailable(missing), "not configured counts as unavailable");
  const unusable = unavailableBody({ providerCode: "AI_PROVIDER_UNUSABLE_OUTPUT" });
  assertEqual(unusable, "目前無法取得 AI 回應（輸出無法使用）。", "unusable body");
  assert(isAiUnavailable(unusable), "unusable counts as unavailable");
}

// Topic-group mode (Canonical Production Script Contract): switching topics
// snapshots the outgoing topic and restores the incoming topic's own state.
{
  const baseMap: Record<string, string | null> = {
    "CORE-01-CTL-PROJECT": "雪國",
    "CORE-01-BTN-PROJECT-CONFIRM": "confirmed",
    "CORE-01-BTN-PROJECT-LOCK": "雪國",
    "CORE-01-CTL-TOPIC": "第一集",
    "CORE-01-FLD-PAGE-MODE": "TOPIC_PRODUCTION",
    "CORE-01-BTN-TOPIC-CREATE": JSON.stringify(["第一集", "第二集"]),
    "CORE-01-BTN-CANONICAL-SCRIPT": "ACPOS-SCRIPT-0001",
    "CORE-01-FLD-TOPIC-SCOPE": "第一集",
    "CORE-01-FLD-VERSION-STATE": "腳本候選",
    "CORE-01-FLD-LIFECYCLE-STAGE": "TOPIC_DRAFT",
  };
  const confirmedProject = currentFrom(baseMap);
  // Switch to a fresh topic: outgoing topic is snapshotted, incoming topic
  // starts clean and carries a Continuity Bridge line naming its predecessor.
  const toSecond = previewCoreAction("CORE-01-CTL-TOPIC", "CORE-01-ACT-TOPIC-SELECT", confirmedProject, "第二集");
  assertEqual(toSecond["CORE-01-CTL-TOPIC"], "第二集", "topic select switches topic");
  assertEqual(toSecond["CORE-01-BTN-CANONICAL-SCRIPT"], "", "fresh topic clears script");
  assertEqual(toSecond["CORE-01-FLD-VERSION-STATE"], "", "fresh topic clears version state");
  assert(
    (toSecond["CORE-01-FLD-TOPIC-SCOPE"] ?? "").startsWith("第二集｜前序專題：第一集"),
    "fresh topic carries continuity bridge",
  );
  const stored = JSON.parse(toSecond["CORE-01-FLD-TOPIC-SNAPSHOTS"] ?? "{}") as Record<string, Record<string, string>>;
  assertEqual(stored["雪國/第一集"]?.["CORE-01-BTN-CANONICAL-SCRIPT"], "ACPOS-SCRIPT-0001", "outgoing topic snapshotted");

  // Switch back: the first topic restores its own script and version state.
  const secondState = currentFrom({ ...baseMap, ...toSecond });
  const backToFirst = previewCoreAction("CORE-01-CTL-TOPIC", "CORE-01-ACT-TOPIC-SELECT", secondState, "第一集");
  assertEqual(backToFirst["CORE-01-BTN-CANONICAL-SCRIPT"], "ACPOS-SCRIPT-0001", "switch back restores script");
  assertEqual(backToFirst["CORE-01-FLD-VERSION-STATE"], "腳本候選", "switch back restores version state");
  assertEqual(backToFirst["CORE-01-CTL-TOPIC"], "第一集", "switch back restores topic");
  assertEqual(backToFirst["CORE-01-FLD-TOPIC-SCOPE"], "第一集", "restored topic keeps its own scope");

  // Selecting the current topic is a no-op.
  const sameState = currentFrom({ ...baseMap, ...toSecond, "CORE-01-CTL-TOPIC": "第二集" });
  const same = previewCoreAction("CORE-01-CTL-TOPIC", "CORE-01-ACT-TOPIC-SELECT", sameState, "第二集");
  assertEqual(Object.keys(same).length, 0, "same topic select is no-op");

  // Deleting a topic drops its snapshot and clears topic-bound fields.
  const deleteState = currentFrom({ ...baseMap, ...toSecond });
  const deleted = previewCoreAction("CORE-01-CTL-TOPIC", "CORE-01-ACT-TOPIC-DELETE", deleteState);
  assertEqual(deleted["CORE-01-CTL-TOPIC"], "", "topic delete clears topic");
  assertEqual(deleted["CORE-01-FLD-PAGE-MODE"], "PROJECT_CORE", "topic delete returns to project mode");
  const afterDelete = JSON.parse(deleted["CORE-01-FLD-TOPIC-SNAPSHOTS"] ?? "{}") as Record<string, unknown>;
  assertEqual(afterDelete["雪國/第二集"], undefined, "topic delete drops snapshot");
}

console.log("coreActionPreview.test.ts PASS");
