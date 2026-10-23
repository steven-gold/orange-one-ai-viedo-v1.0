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
  assertEqual(CORE_VISIBLE_CONTROLS.length, 50, "CORE stays at 50 controls");
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
  assertEqual(compared["CORE-01-FLD-EVALUATION"], "evaluated", "compare writes evaluation");
  assertEqual(compared["CORE-01-FLD-RUNTIME-STAGE"], "CORE_EVALUATION", "compare moves to evaluation");
}

{
  const recorded = previewCoreAction("CORE-01-FLD-HUMAN-DECISION", "CORE-01-ACT-HUMAN-DECISION-RECORD", currentFrom({}));
  assertEqual(recorded["CORE-01-FLD-HUMAN-DECISION"], "recorded", "human decision records");
  assertEqual(recorded["CORE-01-FLD-RUNTIME-STAGE"], "HUMAN_DECISION", "human decision moves stage");
  const structured = previewCoreAction("CORE-01-FLD-STRUCTURED-DECISION", "CORE-01-ACT-ASSISTANT-STRUCTURED-DECISION-CREATE", currentFrom({}));
  assertEqual(structured["CORE-01-FLD-STRUCTURED-DECISION"], "recorded", "structured decision records");
}

{
  const unreachable = unavailableBody({ failed: true, empty: true, providerCode: "AI_PROVIDER_UNREACHABLE" });
  assertEqual(unreachable, "目前無法取得 AI 回應（供應商無法連線）。", "unreachable body");
  assert(isAiUnavailable(unreachable), "unreachable counts as unavailable");
  const missing = unavailableBody({ providerCode: "AI_PROVIDER_NOT_CONFIGURED" });
  assertEqual(missing, "目前無法取得 AI 回應（供應商未設定或暫時無法使用）。", "not configured body");
  assert(isAiUnavailable(missing), "not configured counts as unavailable");
}

console.log("coreActionPreview.test.ts PASS");
