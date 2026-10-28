export type AdapterFamily = "openai" | "gemini" | "anthropic";

export type AdapterChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

export type AdapterRequest = {
  url: string;
  init: RequestInit;
};

export type AdapterTurn = {
  content: string;
  finishReason: string;
};

export function adapterFamily(adapterType: string, url = ""): AdapterFamily | null {
  const adapter = adapterType.trim().toLowerCase();
  const target = `${adapter} ${url}`;
  if (adapter.includes("gemini") || adapter.includes("google") || /:generateContent|:streamGenerateContent|\/v1beta\//i.test(target)) {
    return "gemini";
  }
  if (adapter.includes("anthropic") || adapter.includes("claude") || /\/messages(\?|$)/i.test(url)) {
    return "anthropic";
  }
  if (
    adapter.includes("openai") ||
    adapter.includes("deepseek") ||
    adapter.includes("groq") ||
    adapter.includes("openrouter") ||
    adapter.includes("baizhi") ||
    adapter.includes("lingke") ||
    /\/chat\/completions/i.test(url)
  ) {
    return "openai";
  }
  return null;
}

function clean(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function geminiUrl(url: string, stream: boolean): string {
  if (!stream) return url.replace(/:streamGenerateContent/gi, ":generateContent");
  let next = url.replace(/:generateContent/gi, ":streamGenerateContent");
  if (!/[?&]alt=sse\b/i.test(next)) next += next.includes("?") ? "&alt=sse" : "?alt=sse";
  return next;
}

function geminiContents(messages: AdapterChatMessage[]): {
  systemInstruction?: { parts: Array<{ text: string }> };
  contents: Array<{ role: "user" | "model"; parts: Array<{ text: string }> }>;
} {
  const systems: string[] = [];
  const contents: Array<{ role: "user" | "model"; parts: Array<{ text: string }> }> = [];
  for (const message of messages) {
    const text = message.content;
    if (!text) continue;
    if (message.role === "system") {
      systems.push(text);
      continue;
    }
    const role = message.role === "assistant" ? "model" : "user";
    const last = contents[contents.length - 1];
    if (last?.role === role) {
      last.parts[0].text = `${last.parts[0].text}\n\n${text}`;
      continue;
    }
    contents.push({ role, parts: [{ text }] });
  }
  if (contents[0]?.role === "model") {
    contents.unshift({ role: "user", parts: [{ text: " " }] });
  }
  if (!contents.length) contents.push({ role: "user", parts: [{ text: " " }] });
  const system = systems.join("\n\n").trim();
  return system ? { systemInstruction: { parts: [{ text: system }] }, contents } : { contents };
}

function openaiMessages(messages: AdapterChatMessage[]): AdapterChatMessage[] {
  return messages.filter((message) => message.content);
}

function anthropicPayload(messages: AdapterChatMessage[], model: string, temperature: number, stream: boolean, maxTokens: number) {
  const systems: string[] = [];
  const turns: Array<{ role: "user" | "assistant"; content: string }> = [];
  for (const message of messages) {
    const text = message.content;
    if (!text) continue;
    if (message.role === "system") {
      systems.push(text);
      continue;
    }
    const role = message.role === "assistant" ? "assistant" : "user";
    const last = turns[turns.length - 1];
    if (last?.role === role) {
      last.content = `${last.content}\n\n${text}`;
      continue;
    }
    turns.push({ role, content: text });
  }
  if (turns[0]?.role === "assistant") turns.unshift({ role: "user", content: " " });
  if (!turns.length) turns.push({ role: "user", content: " " });
  const system = systems.join("\n\n").trim();
  return {
    model,
    max_tokens: maxTokens,
    temperature,
    stream,
    ...(system ? { system } : {}),
    messages: turns,
  };
}

export function buildProviderRequest(input: {
  url: string;
  credential: string;
  adapterType?: string;
  model: string;
  messages: AdapterChatMessage[];
  temperature: number;
  stream: boolean;
  httpMethod?: string;
  maxTokens?: number;
}): AdapterRequest | null {
  const url = input.url.trim();
  const credential = input.credential.trim();
  if (!url || !credential) return null;
  const family = adapterFamily(input.adapterType ?? "", url);
  if (!family) return null;
  const method = (input.httpMethod || "POST").toUpperCase();
  if (family === "gemini") {
    const packed = geminiContents(input.messages);
    return {
      url: geminiUrl(url, input.stream),
      init: {
        method,
        headers: { accept: "application/json", "content-type": "application/json", "x-goog-api-key": credential },
        body: JSON.stringify({
          ...packed,
          generationConfig: {
            temperature: input.temperature,
            ...(input.maxTokens ? { maxOutputTokens: input.maxTokens } : {}),
          },
        }),
      },
    };
  }
  if (family === "anthropic") {
    return {
      url,
      init: {
        method,
        headers: {
          accept: "application/json",
          "content-type": "application/json",
          "x-api-key": credential,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify(anthropicPayload(input.messages, input.model, input.temperature, input.stream, input.maxTokens ?? 4096)),
      },
    };
  }
  return {
    url,
    init: {
      method,
      headers: { accept: "application/json", "content-type": "application/json", authorization: `Bearer ${credential}` },
      body: JSON.stringify({
        model: input.model,
        messages: openaiMessages(input.messages),
        temperature: input.temperature,
        stream: input.stream,
        ...(input.maxTokens ? { max_tokens: input.maxTokens } : {}),
      }),
    },
  };
}

function finishOf(reason: string): string {
  const value = clean(reason).toLowerCase();
  if (value === "max_tokens" || value === "length" || value === "maxoutputtokens") return "length";
  if (value === "stop" || value === "end_turn" || value === "stop_sequence" || value === "end") return "stop";
  return clean(reason);
}

function geminiParts(payload: unknown): { content: string; finishReason: string } {
  const data = payload as {
    candidates?: Array<{ content?: { parts?: Array<{ text?: string }> }; finishReason?: string; finish_reason?: string }>;
  };
  const candidate = data.candidates?.[0];
  const content = (candidate?.content?.parts ?? []).map((part) => part.text ?? "").join("");
  return { content, finishReason: finishOf(candidate?.finishReason ?? candidate?.finish_reason ?? "") };
}

export function readProviderText(payload: unknown, family: AdapterFamily): AdapterTurn {
  if (family === "gemini") {
    const turn = geminiParts(payload);
    return { content: clean(turn.content), finishReason: turn.finishReason };
  }
  if (family === "anthropic") {
    const data = payload as { content?: Array<{ text?: string }>; stop_reason?: string };
    return {
      content: clean((data.content ?? []).map((part) => part.text ?? "").join("")),
      finishReason: finishOf(data.stop_reason ?? ""),
    };
  }
  const data = payload as {
    choices?: Array<{ message?: { content?: string; reasoning?: string }; finish_reason?: string; finishReason?: string }>;
  };
  const choice = data.choices?.[0];
  return {
    content: clean(choice?.message?.content) || clean(choice?.message?.reasoning),
    finishReason: finishOf(choice?.finish_reason ?? choice?.finishReason ?? ""),
  };
}

export function parseProviderSseFrame(
  data: string,
  family: AdapterFamily,
): { delta: string; finishReason: string; done: boolean } {
  const trimmed = clean(data);
  if (!trimmed) return { delta: "", finishReason: "", done: false };
  if (trimmed === "[DONE]") return { delta: "", finishReason: "", done: true };
  try {
    const payload = JSON.parse(trimmed) as Record<string, unknown>;
    if (family === "gemini") {
      const turn = geminiParts(payload);
      return { delta: turn.content, finishReason: turn.finishReason, done: false };
    }
    if (family === "anthropic") {
      const type = typeof payload.type === "string" ? payload.type : "";
      if (type === "message_stop") return { delta: "", finishReason: "", done: true };
      if (type === "content_block_delta") {
        const delta = payload.delta as { text?: string } | undefined;
        return { delta: typeof delta?.text === "string" ? delta.text : "", finishReason: "", done: false };
      }
      if (type === "message_delta") {
        const delta = payload.delta as { stop_reason?: string } | undefined;
        return { delta: "", finishReason: finishOf(delta?.stop_reason ?? ""), done: false };
      }
      return { delta: "", finishReason: "", done: false };
    }
    const choice = (payload.choices as Array<{
      delta?: { content?: string };
      message?: { content?: string };
      finish_reason?: string;
      finishReason?: string;
    }> | undefined)?.[0];
    const raw = choice?.delta?.content ?? choice?.message?.content;
    return {
      delta: typeof raw === "string" ? raw : "",
      finishReason: finishOf(choice?.finish_reason ?? choice?.finishReason ?? ""),
      done: false,
    };
  } catch {
    return { delta: "", finishReason: "", done: false };
  }
}
