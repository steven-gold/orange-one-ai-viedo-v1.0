import { openSqlClient } from "../db/client";
import { bootstrapDatabase } from "../db/migrate";
import { seedScope } from "../db/seed";
import { applyStrWorkbenchAction } from "./strActions";
import { persistRecordStrAction } from "../db/persist";
import { STR_STATE_ERROR_UID } from "../domain/str";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

async function readField(controlUid: string): Promise<string | null> {
  const client = await openSqlClient();
  const rows = await client.all<{ value_text: string | null }>(
    "SELECT value_text FROM ghsn_str_field_projection WHERE control_uid = ?",
    [controlUid],
  );
  const value = rows[0]?.value_text;
  return value === undefined || value === "" ? null : value;
}

async function readError(): Promise<{ code?: string; detail?: string } | null> {
  const raw = await readField(STR_STATE_ERROR_UID);
  if (!raw) return null;
  return JSON.parse(raw) as { code?: string; detail?: string };
}

const DEMO = "ACC-DEMO";

// Deterministic start: blank the STR-01 projection state (shared sandbox file).
const STR_STATE_CONTROLS = [
  STR_STATE_ERROR_UID,
  "STR-01-FLD-TOPIC",
  "STR-01-FLD-SCOPE",
  "STR-01-FLD-HORIZON",
  "STR-01-FLD-STATE",
  "STR-01-FLD-DECISION-STATE",
  "STR-01-TGL-MODE",
  "STR-01-LST-TOPICS",
  "STR-01-VIEW-CONVERSATION",
  "STR-01-FLD-ASSISTANT-SUMMARY",
  "STR-01-FLD-OPEN-QUESTIONS",
  "STR-01-FLD-MEETING-RECORD",
  "STR-01-FLD-BASIS",
  "STR-01-FLD-ASSUMPTIONS",
  "STR-01-FLD-OPPORTUNITIES",
  "STR-01-FLD-RISKS",
  "STR-01-FLD-UNCERTAINTY",
  "STR-01-FLD-PATTERN",
  "STR-01-TBL-COMPARE",
  "STR-01-CARD-RECOMMENDATION",
  "STR-01-CARD-ALERT",
  "STR-01-CARD-RESOURCE",
  "STR-01-CARD-BRIEF",
  "STR-01-FLD-CANDIDATE-REF",
  "STR-01-FLD-REVIEW-STATE",
  "STR-01-FLD-DECISION-ID",
  "STR-01-FLD-DECISION-RESULT",
  "STR-01-FLD-DECISION-REASON",
  "STR-01-FLD-EXECUTION-STATE",
  "STR-01-FLD-PROVIDER-BRAND",
  "STR-01-FLD-CORRELATION",
  "STR-01-FLD-OWNER-BOUNDARY",
  "STR-01-STATE-TOPIC",
  "STR-01-STATE-TOPICS",
  "STR-01-STATE-CONVERSATION",
  "STR-01-STATE-MODE",
  "STR-01-STATE-CANDIDATES",
  "STR-01-STATE-CONTEXT",
  "STR-01-STATE-FILTER",
  "STR-01-STATE-GENERATION",
];

async function main(): Promise<void> {
  await bootstrapDatabase();
  await seedScope("str");
  const client = await openSqlClient();
  for (const controlUid of STR_STATE_CONTROLS) {
    await client.run(
      `INSERT INTO ghsn_str_field_projection (control_uid, value_text) VALUES (?, NULL)
       ON CONFLICT (control_uid) DO UPDATE SET value_text = NULL`,
      [controlUid],
    );
  }

  // Unlisted action lands BLOCK + REPORT_AUTHORITY_GAP.
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-SEND", "STR-01-ACT-UNLISTED");
  assertEqual((await readError())?.code, "STR-01-ERR-UNDEFINED-001", "undefined action blocked");

  // GATE-MESSAGE: send without an active topic is blocked; topic/context preserved.
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-SEND", "STR-01-ACT-SEND", "企業明年應該擴張哪些市場？");
  assertEqual((await readError())?.code, "STR-01-ERR-CONVERSATION-001", "send without topic blocked");

  // GATE-MESSAGE: permission refusal for an account without conversation.write.
  await applyStrWorkbenchAction("ACC-STR-NOPE", "STR-01-BTN-SEND", "STR-01-ACT-SEND", "hello");
  assertEqual((await readError())?.code, "STR-01-ERR-PERM-001", "conversation.write required");

  // GATE-PAGE: topic selection registers the exact topic and resolves context.
  await applyStrWorkbenchAction(DEMO, "STR-01-LST-TOPICS", "STR-01-ACT-TOPIC-SELECT", "亞太市場擴張評估");
  const topic = await readField("STR-01-FLD-TOPIC");
  assert(topic !== null && topic.includes("亞太市場擴張評估"), "topic registered and selected");
  const contextRaw = await readField("STR-01-STATE-CONTEXT");
  assert(contextRaw !== null && contextRaw.includes("亞太市場擴張評估"), "context bundle carries the topic");
  assertEqual(await readField("STR-01-FLD-STATE"), "STR-01-STAGE-01-CONTEXT", "stage resolves context");
  const topicsRaw = await readField("STR-01-STATE-TOPICS");
  assert(topicsRaw !== null && topicsRaw.includes("亞太市場擴張評估"), "topic list keeps history");

  // Re-select is idempotent: the same title reuses the registered topic.
  await applyStrWorkbenchAction(DEMO, "STR-01-LST-TOPICS", "STR-01-ACT-TOPIC-SELECT", "亞太市場擴張評估");
  const topicsAgain = JSON.parse((await readField("STR-01-STATE-TOPICS")) ?? "[]") as Array<{ title: string }>;
  assertEqual(topicsAgain.filter((row) => row.title === "亞太市場擴張評估").length, 1, "topic registration is idempotent");

  // GATE-MESSAGE: empty message is blocked.
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-SEND", "STR-01-ACT-SEND", "   ");
  assertEqual((await readError())?.code, "STR-01-ERR-CONVERSATION-001", "empty message blocked");

  // ACT-SEND appends the user turn; provider outcomes stay honest:
  // success routes the analysis into fields, failure keeps [AI_PROVIDER_*].
  await applyStrWorkbenchAction(DEMO, "STR-01-INP-MESSAGE", "STR-01-ACT-SEND", "評估亞太擴張的風險與機會");
  const transcript = JSON.parse((await readField("STR-01-VIEW-CONVERSATION")) ?? "{}") as { turns?: Array<{ role: string; text: string; status?: string }> };
  const turns = transcript.turns ?? [];
  assert(turns.some((row) => row.role === "user" && row.text.includes("評估亞太擴張")), "user turn preserved");
  const assistant = turns.find((row) => row.role !== "user");
  assert(assistant !== undefined, "assistant turn registered");
  assert(assistant?.status === "SENT" || assistant?.status === "FAILED", "assistant turn status recorded");
  if (assistant?.status === "FAILED") {
    assert(assistant.text.startsWith("[AI_PROVIDER_"), "provider failure is honest, no fabricated reply");
    assertEqual((await readError())?.code, "STR-01-ERR-CONVERSATION-001", "conversation error recorded");
  } else {
    assertEqual(await readError(), null, "successful send clears the error banner");
  }

  // ACT-MODE persists the conversation mode.
  await applyStrWorkbenchAction(DEMO, "STR-01-TGL-MODE", "STR-01-ACT-MODE", "MULTI");
  assertEqual(await readField("STR-01-STATE-MODE"), "MULTI", "mode persisted");

  // GATE-COMPARE: fewer than 2 candidates is blocked.
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-COMPARE", "STR-01-ACT-COMPARE");
  assertEqual((await readError())?.code, "STR-01-ERR-CANDIDATE-001", "compare needs 2+ candidates");

  // GATE-REVIEW: nothing to review before a candidate exists.
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-SUBMIT-REVIEW", "STR-01-ACT-REVIEW");
  assertEqual((await readError())?.code, "STR-01-ERR-REVIEW-001", "review needs a CANDIDATE");

  // GATE-ADOPT: adoption without a reviewed candidate is blocked; no
  // auto-approval (word §human_gate).
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-ADOPT", "STR-01-ACT-ADOPT", "採用理由：風險可控");
  assertEqual((await readError())?.code, "STR-01-ERR-ADOPT-001", "adopt needs REVIEW_REQUIRED");

  // ADOPT with a reviewed candidate and reason moves the ledger forward.
  const candidates = [
    {
      candidateId: "STR-CAND-TEST-A",
      version: 1,
      title: "方案 A",
      outputType: "STRATEGY_RECOMMENDATION",
      summary: "先行單一市場試點",
      basis: "內部資料與歷史分析",
      risk: "匯率波動",
      uncertainty: "需求規模",
      evidence: "QA-01-FLD-CRITERIA-VERSION",
      state: "CANDIDATE" as const,
      at: new Date().toISOString(),
    },
  ];
  await client.run(
    `INSERT INTO ghsn_str_field_projection (control_uid, value_text) VALUES ('STR-01-STATE-CANDIDATES', ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [JSON.stringify(candidates)],
  );
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-SUBMIT-REVIEW", "STR-01-ACT-REVIEW");
  assert((await readField("STR-01-FLD-REVIEW-STATE")) === "REVIEW_REQUIRED", "review moves CANDIDATE to REVIEW_REQUIRED");
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-ADOPT", "STR-01-ACT-ADOPT", "採用理由：風險可控");
  assertEqual((await readError()), null, "adopt succeeds with reason");
  assertEqual(await readField("STR-01-FLD-DECISION-RESULT"), "ADOPTED_CONTEXT", "ledger records the adoption");
  assert((await readField("STR-01-FLD-DECISION-ID") ?? "").startsWith("STR-DEC-"), "decision id registered");
  assertEqual(await readField("STR-01-FLD-EXECUTION-STATE"), "PENDING_OWNER_MODULE", "execution stays with owner module");
  assertEqual(await readField("STR-01-FLD-STATE"), "STR-01-STAGE-05-HUMAN", "stage reaches human review");

  // Adopt again without a reviewed candidate is blocked (append-only ledger).
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-ADOPT", "STR-01-ACT-ADOPT", "再採用一次");
  assertEqual((await readError())?.code, "STR-01-ERR-ADOPT-001", "no second adoption without a reviewed candidate");

  // ACT-AUDIT surfaces real audit events (route layer records them).
  await persistRecordStrAction(DEMO, "STR-01-BTN-SEND", "STR-01-ACT-STOP");
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-AUDIT", "STR-01-ACT-AUDIT");
  assert((await readField("STR-01-FLD-CORRELATION")) !== null, "audit correlation populated");

  // ACT-STOP flags the cancel watcher only.
  await applyStrWorkbenchAction(DEMO, "STR-01-BTN-STOP", "STR-01-ACT-STOP");
  const generation = JSON.parse((await readField("STR-01-STATE-GENERATION")) ?? "{}") as { cancelRequested?: boolean };
  assertEqual(generation.cancelRequested, true, "stop requests cancellation");

  // ACT-FILTER narrows the visible topic list.
  await applyStrWorkbenchAction(DEMO, "STR-01-INP-TOPIC-SEARCH", "STR-01-ACT-FILTER", "不存在的議題");
  assertEqual(await readField("STR-01-LST-TOPICS"), null, "filter hides unmatched topics");
  await applyStrWorkbenchAction(DEMO, "STR-01-INP-TOPIC-SEARCH", "STR-01-ACT-FILTER", "");
  assert((await readField("STR-01-LST-TOPICS")) !== null, "clearing filter restores the list");

  console.log(`str-workbench: all assertions passed`);
  process.exit(0);
}

void main();
