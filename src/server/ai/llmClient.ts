import { getSqlClient } from "../db/client";
import { getAiapiCredential } from "../db/aiapiCredential";
import { AIAPI_PROMPT_TEMPLATE_TOKEN, eligibleProfiles, readProfiles, type AiapiProfile } from "@/lib/aiapiProfiles";

export type AiPageUid = "core" | "asset" | "video" | "edit";

export const AI_CAPABILITY_BY_PAGE: Record<AiPageUid, string> = {
  core: "chat",
  asset: "correction",
  video: "correction",
  edit: "correction",
};

export interface ProviderConfig {
  url: string;
  model: string;
  provider: string;
  credential: string;
  timeoutMs: number;
  promptTemplate: string;
}

function clean(value: string | null | undefined): string {
  return (value ?? "").trim();
}

async function readAiapiFields(): Promise<Map<string, string | null>> {
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    "SELECT control_uid, value_text FROM ghsn_aiapi_field_projection",
  );
  return new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
}

function toProviderConfig(profile: AiapiProfile, credential: string): ProviderConfig | null {
  const provider = clean(profile.providerId);
  const base = clean(profile.baseUrl).replace(/\/+$/, "");
  const rawEndpoint = clean(profile.endpointPath);
  if (!provider || !base || !rawEndpoint) return null;
  const endpoint = rawEndpoint.startsWith("/") ? rawEndpoint : `/${rawEndpoint}`;

  const model = clean(profile.modelId);
  if (!model) return null;
  const timeoutSeconds = Number.parseInt(clean(profile.timeoutSeconds), 10);
  const timeoutMs = Number.isFinite(timeoutSeconds) && timeoutSeconds > 0 ? timeoutSeconds * 1000 : 20000;

  return {
    url: `${base}${endpoint}`,
    model,
    provider,
    credential,
    timeoutMs,
    promptTemplate: clean(profile.promptTemplate),
  };
}

const SYSTEM_PROMPTS: Record<AiPageUid, string> = {
  core: "你是 ACPOS 核心製作助理。以繁體中文、精簡且可執行地回覆使用者在專案／專題對話中的需求。請延續同一條對話的上下文，不要忽略使用者剛說的內容。",
  asset: "你是 ACPOS 素材製作助理。以繁體中文回覆素材修正需求，輸出可直接套用的修正內容。",
  video: "你是 ACPOS 影片剪輯助理。以繁體中文回覆鏡頭修正需求，輸出可直接套用的修正內容。",
  edit: "你是 ACPOS 後期剪輯助理。以繁體中文回覆語意修正需求，輸出可直接套用的修正內容。",
};

function systemPromptFor(page: AiPageUid, template: string): string {
  const instruction = SYSTEM_PROMPTS[page];
  if (template.includes(AIAPI_PROMPT_TEMPLATE_TOKEN)) {
    return template.split(AIAPI_PROMPT_TEMPLATE_TOKEN).join(instruction);
  }
  return instruction;
}

export async function resolveProviderConfigs(capability: string): Promise<ProviderConfig[]> {
  const fields = await readAiapiFields();
  const profiles = readProfiles((uid) => fields.get(uid) ?? null);
  const candidates = eligibleProfiles(profiles, capability);

  const configs: ProviderConfig[] = [];
  for (const profile of candidates) {
    const credential = await getAiapiCredential(profile.profileId);
    if (!credential) continue;
    const config = toProviderConfig(profile, credential);
    if (config) configs.push(config);
  }
  return configs;
}

export async function assignedAiRouteSnapshot(capability = AI_CAPABILITY_BY_PAGE.core): Promise<string> {
  const configs = await resolveProviderConfigs(capability);
  return configs
    .map((config) => [config.provider, config.model].filter((part) => part.trim()).join(" / "))
    .filter(Boolean)
    .join("、");
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

async function callProvider(config: ProviderConfig, messages: ChatMessage[]): Promise<string> {
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

export async function callChat(messages: ChatMessage[], capability: string): Promise<string> {
  const configs = await resolveProviderConfigs(capability);
  if (!configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${capability} provider with a stored credential`);
  }
  let lastError: AiProviderError | null = null;
  for (const config of configs) {
    try {
      return await callProvider(config, messages);
    } catch (error) {
      lastError = error instanceof AiProviderError ? error : new AiProviderError("AI_PROVIDER_UNREACHABLE", "Provider call failed");
    }
  }
  throw lastError ?? new AiProviderError("AI_PROVIDER_UNREACHABLE", "All candidate providers failed");
}

export async function generatePageReply(
  page: AiPageUid,
  prompt: string,
  context?: string,
  history: ChatMessage[] = [],
): Promise<string> {
  const configs = await resolveProviderConfigs(AI_CAPABILITY_BY_PAGE[page]);
  if (!configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${AI_CAPABILITY_BY_PAGE[page]} provider with a stored credential`);
  }
  const user = context ? `${prompt}\n\n[脈絡]\n${context}` : prompt;
  const recent = history.filter((row) => row.content.trim().length > 0);
  let lastError: AiProviderError | null = null;
  for (const config of configs) {
    const messages: ChatMessage[] = [
      { role: "system", content: systemPromptFor(page, config.promptTemplate) },
      ...recent,
      { role: "user", content: user },
    ];
    try {
      return await callProvider(config, messages);
    } catch (error) {
      lastError = error instanceof AiProviderError ? error : new AiProviderError("AI_PROVIDER_UNREACHABLE", "Provider call failed");
    }
  }
  throw lastError ?? new AiProviderError("AI_PROVIDER_UNREACHABLE", "All candidate providers failed");
}

export type IndependentReply = { alias: string; text: string };

export async function generateIndependentPageReplies(
  page: AiPageUid,
  prompt: string,
  context: string | undefined,
  history: ChatMessage[],
  aliases: string[],
): Promise<IndependentReply[]> {
  const configs = await resolveProviderConfigs(AI_CAPABILITY_BY_PAGE[page]);
  if (!configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${AI_CAPABILITY_BY_PAGE[page]} provider with a stored credential`);
  }
  const user = context ? `${prompt}\n\n[脈絡]\n${context}` : prompt;
  const recent = history.filter((row) => row.content.trim().length > 0);
  const replies: IndependentReply[] = [];
  for (const [index, alias] of aliases.entries()) {
    const config = configs[index];
    if (!config) {
      replies.push({ alias, text: "" });
      continue;
    }
    const messages: ChatMessage[] = [
      { role: "system", content: systemPromptFor(page, config.promptTemplate) },
      ...recent,
      { role: "user", content: user },
    ];
    try {
      replies.push({ alias, text: await callProvider(config, messages) });
    } catch {
      replies.push({ alias, text: "" });
    }
  }
  return replies;
}
