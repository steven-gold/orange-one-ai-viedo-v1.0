import {
  adapterFamily,
  buildProviderRequest,
  parseProviderSseFrame,
  readProviderText,
} from "./aiapiAdapter";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

{
  assertEqual(adapterFamily("gemini", ""), "gemini", "declared gemini");
  assertEqual(
    adapterFamily("", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"),
    "gemini",
    "gemini url",
  );
  assertEqual(adapterFamily("openai", "https://api.groq.com/openai/v1/chat/completions"), "openai", "groq openai");
  assertEqual(adapterFamily("openai", "https://api.deepseek.com/v1/chat/completions"), "openai", "deepseek openai");
  assertEqual(adapterFamily("anthropic", "https://api.anthropic.com/v1/messages"), "anthropic", "anthropic");
}

{
  const gemini = buildProviderRequest({
    url: "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    credential: "AIza-test",
    adapterType: "gemini",
    model: "gemini-2.5-flash",
    messages: [
      { role: "system", content: "你是 CORE。" },
      { role: "user", content: "現在是什麼模組" },
    ],
    temperature: 0.2,
    stream: false,
  });
  assert(gemini, "gemini request");
  const headers = gemini!.init.headers as Record<string, string>;
  assertEqual(headers["x-goog-api-key"], "AIza-test", "gemini uses goog key");
  assertEqual("authorization" in headers, false, "gemini omits bearer");
  const body = JSON.parse(String(gemini!.init.body)) as {
    systemInstruction?: { parts: Array<{ text: string }> };
    contents: Array<{ role: string; parts: Array<{ text: string }> }>;
    generationConfig: { temperature: number };
  };
  assertEqual(body.systemInstruction?.parts[0]?.text, "你是 CORE。", "gemini system");
  assertEqual(body.contents[0]?.role, "user", "gemini user role");
  assertEqual(body.contents[0]?.parts[0]?.text, "現在是什麼模組", "gemini user text");
  assertEqual("model" in body, false, "gemini body omits openai model field");
}

{
  const streamed = buildProviderRequest({
    url: "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    credential: "AIza-test",
    adapterType: "gemini",
    model: "gemini-2.5-flash",
    messages: [{ role: "user", content: "hi" }],
    temperature: 0.2,
    stream: true,
  });
  assert(streamed, "gemini stream request");
  assert(streamed!.url.includes(":streamGenerateContent"), "gemini stream action");
  assert(streamed!.url.includes("alt=sse"), "gemini sse alt");
}

{
  const openai = buildProviderRequest({
    url: "https://api.groq.com/openai/v1/chat/completions",
    credential: "gsk_test",
    adapterType: "openai",
    model: "allam-2-7b",
    messages: [{ role: "user", content: "hi" }],
    temperature: 0.2,
    stream: true,
  });
  assert(openai, "openai request");
  const headers = openai!.init.headers as Record<string, string>;
  assertEqual(headers.authorization, "Bearer gsk_test", "openai bearer");
  const body = JSON.parse(String(openai!.init.body)) as { model: string; stream: boolean; messages: Array<{ role: string }> };
  assertEqual(body.model, "allam-2-7b", "openai model");
  assertEqual(body.stream, true, "openai stream flag");
  assertEqual(body.messages[0]?.role, "user", "openai messages");
}

{
  const turn = readProviderText(
    { candidates: [{ content: { parts: [{ text: "這是 CORE 工作台" }] }, finishReason: "STOP" }] },
    "gemini",
  );
  assertEqual(turn.content, "這是 CORE 工作台", "gemini json text");
  assertEqual(turn.finishReason, "stop", "gemini stop");
  const empty = readProviderText({ choices: [{ message: { content: "" } }] }, "openai");
  assertEqual(empty.content, "", "openai empty");
  const groq = readProviderText({ choices: [{ message: { content: "ok" }, finish_reason: "stop" }] }, "openai");
  assertEqual(groq.content, "ok", "openai json text");
}

{
  const geminiDelta = parseProviderSseFrame(
    JSON.stringify({ candidates: [{ content: { parts: [{ text: "第" }] } }] }),
    "gemini",
  );
  assertEqual(geminiDelta.delta, "第", "gemini sse delta");
  const openaiDelta = parseProviderSseFrame(JSON.stringify({ choices: [{ delta: { content: "一集" } }] }), "openai");
  assertEqual(openaiDelta.delta, "一集", "openai sse delta");
  const done = parseProviderSseFrame("[DONE]", "openai");
  assertEqual(done.done, true, "openai done");
}

console.log("aiapiAdapter.test.ts PASS");
