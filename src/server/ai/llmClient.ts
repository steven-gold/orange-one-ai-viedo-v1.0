import { getSqlClient } from "../db/client";
import { getAiapiCredential } from "../db/aiapiCredential";

export type AiPageUid = "core" | "asset" | "video";

export interface ProviderConfig {
  url: string;
  model: string;
  provider: string;
  credential: string;
  timeoutMs: number;
}

const PROVIDER_DEFAULT_BASE: Array<[RegExp, string]> = [
  [/groq/i, "https://api.groq.com/openai/v1"],
  [/openrouter/i, "https://openrouter.ai/api/v1"],
  [/deepseek/i, "https://api.deepseek.com/v1"],
  [/openai/i, "https://api.openai.com/v1"],
];

function clean(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function defaultBase(provider: string, adapter: string): string {
  const haystack = `${provider} ${adapter}`;
  for (const [pattern, base] of PROVIDER_DEFAULT_BASE) {
    if (pattern.test(haystack)) return base;
  }
  return clean(process.env.ACPOS_LLM_BASE_URL);
}

async function readAiapiFields(): Promise<Map<string, string | null>> {
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    "SELECT control_uid, value_text FROM ghsn_aiapi_field_projection",
  );
  return new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
}

export async function resolveProviderConfig(): Promise<ProviderConfig | null> {
  const fields = await readAiapiFields();
  const provider = clean(fields.get("AIAPI-01-FLD-OV-PROVIDER"));
  const adapter = clean(fields.get("AIAPI-01-PROFILE-GRP-ADAPTER"));
  const status = clean(fields.get("AIAPI-01-PROFILE-GRP-STATUS"));
  if (!provider) return null;
  if (status === "RETIRED" || status === "DISABLED") return null;

  const base = (clean(fields.get("AIAPI-01-PROFILE-GRP-CONNECTION")) || defaultBase(provider, adapter)).replace(/\/+$/, "");
  if (!base) return null;
  const rawEndpoint = clean(fields.get("AIAPI-01-PROFILE-GRP-DATA-CONTEXT"));
  const endpoint = rawEndpoint ? (rawEndpoint.startsWith("/") ? rawEndpoint : `/${rawEndpoint}`) : "/chat/completions";

  const identity = clean(fields.get("AIAPI-01-PROFILE-GRP-IDENTITY"));
  const identityModel = identity.includes("/") ? clean(identity.split("/").pop()) : "";
  const model = identityModel || clean(process.env.ACPOS_LLM_MODEL) || "llama-3.1-8b-instant";

  const timeoutSeconds = Number.parseInt(clean(fields.get("AIAPI-01-PRO-DESC-LIMITS")), 10);
  const timeoutMs = Number.isFinite(timeoutSeconds) && timeoutSeconds > 0 ? timeoutSeconds * 1000 : 20000;

  const credential = await getAiapiCredential();
  if (!credential) return null;

  return { url: `${base}${endpoint}`, model, provider, credential, timeoutMs };
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export class AiProviderError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "AiProviderError";
  }
}

export async function callChat(messages: ChatMessage[]): Promise<string> {
  const config = await resolveProviderConfig();
  if (!config) throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", "No enabled AI provider with a stored credential");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.timeoutMs);
  try {
    const response = await fetch(config.url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${config.credential}`,
      },
      body: JSON.stringify({ model: config.model, messages, temperature: 0.2 }),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      const detail = (await response.text().catch(() => "")).slice(0, 200);
      throw new AiProviderError("AI_PROVIDER_HTTP_ERROR", `${config.provider} responded ${response.status}: ${detail}`);
    }
    const payload = (await response.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const content = clean(payload.choices?.[0]?.message?.content);
    if (!content) throw new AiProviderError("AI_PROVIDER_EMPTY_RESPONSE", "Provider returned no message content");
    return content;
  } catch (error) {
    if (error instanceof AiProviderError) throw error;
    if (error instanceof Error && error.name === "AbortError") {
      throw new AiProviderError("AI_PROVIDER_TIMEOUT", `Provider call exceeded ${config.timeoutMs}ms`);
    }
    throw new AiProviderError("AI_PROVIDER_UNREACHABLE", error instanceof Error ? error.message : "Provider call failed");
  } finally {
    clearTimeout(timer);
  }
}

const SYSTEM_PROMPTS: Record<AiPageUid, string> = {
  core: "你是 ACPOS 核心製作助理。以繁體中文、精簡且可執行地回覆使用者在專案／專題對話中的需求。",
  asset: "你是 ACPOS 素材製作助理。以繁體中文回覆素材修正需求，輸出可直接套用的修正內容。",
  video: "你是 ACPOS 影片剪輯助理。以繁體中文回覆鏡頭修正需求，輸出可直接套用的修正內容。",
};

export async function generatePageReply(page: AiPageUid, prompt: string, context?: string): Promise<string> {
  const user = context ? `${prompt}\n\n[脈絡]\n${context}` : prompt;
  return callChat([
    { role: "system", content: SYSTEM_PROMPTS[page] },
    { role: "user", content: user },
  ]);
}
