import {
  foldedMessagePreview,
  parseConversationMarkdown,
  parseInlineMarkdown,
  shouldFoldMessage,
} from "./conversationMarkdown";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

{
  const nodes = parseConversationMarkdown("# 標題\n\n一段**粗體**與`碼`\n\n- 甲\n- 乙\n\n1. 一\n2. 二\n\n> 引用\n\n```\ncode\n```\n\n| A | B |\n| --- | --- |\n| 1 | 2 |");
  assertEqual(nodes[0]?.type, "h", "heading");
  assertEqual(nodes.some((row) => row.type === "ul"), true, "ul");
  assertEqual(nodes.some((row) => row.type === "ol"), true, "ol");
  assertEqual(nodes.some((row) => row.type === "pre"), true, "pre");
  assertEqual(nodes.some((row) => row.type === "quote"), true, "quote");
  assertEqual(nodes.some((row) => row.type === "table"), true, "table");
  const inline = parseInlineMarkdown("一段**粗體**與`碼`");
  assert(inline.some((row) => row.type === "strong" && row.text === "粗體"), "strong");
  assert(inline.some((row) => row.type === "code" && row.text === "碼"), "code");
}

{
  const long = `${"甲".repeat(900)}\n${"乙\n".repeat(20)}`;
  assertEqual(shouldFoldMessage(long), true, "fold long");
  assertEqual(shouldFoldMessage("短"), false, "keep short");
  assert(foldedMessagePreview(long).length <= 800, "preview truncated");
}

console.log("conversationMarkdown.test.ts PASS");
