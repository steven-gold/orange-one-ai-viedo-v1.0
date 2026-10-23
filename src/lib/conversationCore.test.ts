import {
  CORE_CONVERSATION,
  formatConversationContext,
  parseNotebookRecords,
  previewAssistantRecordFor,
  projectConversationMemory,
  refreshAssistantNotebookFor,
  type ConversationMessageRecord,
} from "./conversationCore";

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
  const thread = "對話 1";
  const firstMessages: ConversationMessageRecord[] = [
    { thread, role: "user", text: "第一則使用者", seq: 1, ref: "#MSG-000001" },
    { thread, role: "assistant", text: "第一則回覆", seq: 1, ref: "#AI-000001" },
  ];
  const first = refreshAssistantNotebookFor(CORE_CONVERSATION, currentFrom({}), thread, firstMessages, "record");
  const records1 = parseNotebookRecords(first["CORE-01-FLD-ASSISTANT-SUMMARY"]);
  assertEqual(records1.length, 1, "first notebook row");
  assertEqual(records1[0]?.status, "CURRENT", "first current");
  assertEqual(records1[0]?.version, 1, "first version");

  const nextMessages: ConversationMessageRecord[] = [
    ...firstMessages,
    { thread, role: "user", text: "第二則使用者", seq: 2, ref: "#MSG-000002" },
  ];
  const second = refreshAssistantNotebookFor(CORE_CONVERSATION, currentFrom(first), thread, nextMessages, "record");
  const records2 = parseNotebookRecords(second["CORE-01-FLD-ASSISTANT-SUMMARY"]);
  assert(records2.some((row) => row.status === "STALE" && row.version === 1), "prior marked stale");
  assert(records2.some((row) => row.status === "CURRENT" && row.version === 2), "new current version");
  assertEqual(records2.filter((row) => row.status === "CURRENT").length, 1, "one current");

  const projection = projectConversationMemory(CORE_CONVERSATION, currentFrom(second), thread);
  assertEqual(projection?.notebookVersion, 2, "projection version");
  assertEqual(projection?.notebookStatus, "CURRENT", "projection current");
  const context = formatConversationContext(CORE_CONVERSATION, currentFrom({
    ...second,
    "CORE-01-LST-THREADS": thread,
    "CORE-01-BTN-NEW-THREAD": JSON.stringify([{ title: thread, workItem: "STORY" }]),
    "CORE-01-CTL-PROJECT": "示範專案",
    "CORE-01-LST-WORK-ITEMS": "STORY",
  }));
  assert(context.includes("記憶投影："), "context uses memory projection");
  assert(context.includes("版本 2"), "context keeps version");
}

{
  const recorded = previewAssistantRecordFor(
    CORE_CONVERSATION,
    currentFrom({
      "CORE-01-CTL-PROJECT": "示範專案",
      "CORE-01-LST-WORK-ITEMS": "STORY",
    }),
  );
  assertEqual(recorded["CORE-01-BTN-ASSISTANT-RECORD"], "recorded", "assistant writes recorded without messages");
  assert(Boolean(recorded["CORE-01-BTN-NEW-THREAD"]), "assistant ensures a thread");
  assertEqual(recorded["CORE-01-FLD-RUNTIME-STAGE"], "ASSISTANT_SUMMARY", "assistant moves runtime stage");
}

console.log("conversationCore.test.ts PASS");
