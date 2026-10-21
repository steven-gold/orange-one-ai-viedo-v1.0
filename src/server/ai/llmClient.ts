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
  core: [
    "你是 ACPOS 影音生產作業系統的 CORE 分析型 AI。",
    "ACPOS 處理專案、專題、藍圖、Canonical Script、素材、影片與剪輯。",
    "禁止把 ACPOS 解釋成收銀機、POS、電子商務銷售或任何零售結帳系統。",
    "禁止自稱會議秘書、核心設計助理，或再問使用者在哪個專案、哪個模組。",
    "若使用者問目前模組、頁面或系統是什麼，直接回答：這是 ACPOS 影音生產作業系統的 CORE 模組。",
    "脈絡區若已有專案／專題／工作項目／正式腳本，直接沿用。",
    "以繁體中文精簡作答，延續本則剛送出的內容，只產出分析與候選，不把回覆當成正式腳本。",
  ].join(""),
  asset: "你是 ACPOS 素材部門的修正分析型 AI。以繁體中文產出可套用的素材修正內容。禁止解釋成收銀或 POS。",
  video: "你是 ACPOS 影片部門的修正分析型 AI。以繁體中文產出可套用的鏡頭修正內容。禁止解釋成收銀或 POS。",
  edit: "你是 ACPOS 剪輯部門的修正分析型 AI。以繁體中文產出可套用的語意修正內容。禁止解釋成收銀或 POS。",
};

function systemPromptFor(page: AiPageUid, template: string, alias?: string): string {
  const instruction = alias
    ? `${SYSTEM_PROMPTS[page]}你是本場次 Multi 參與者 @${alias}。必須獨立作答，提出與其他參與者不同的觀點、理由或風險，禁止複述或同文。`
    : SYSTEM_PROMPTS[page];
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

const KILL_SWITCH_UID = "AIAPI-01-FLD-KILL-SWITCH";

async function assertKillSwitchOff(): Promise<void> {
  const fields = await readAiapiFields();
  if (fields.get(KILL_SWITCH_UID) === "ON") {
    throw new AiProviderError("AI_PROVIDER_KILL_SWITCH", "Kill switch is on");
  }
}

async function callProvider(config: ProviderConfig, messages: ChatMessage[], temperature = 0.2): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.timeoutMs);
  try {
    const response = await fetch(config.url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${config.credential}`,
      },
      body: JSON.stringify({ model: config.model, messages, temperature }),
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
  await assertKillSwitchOff();
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

export function routeLabelFor(config: Pick<ProviderConfig, "provider" | "model">): string {
  return [config.provider, config.model].filter((part) => part.trim()).join(" / ");
}

export type PageReply = { text: string; route: string };

export async function generatePageReply(
  page: AiPageUid,
  prompt: string,
  context?: string,
  history: ChatMessage[] = [],
): Promise<PageReply> {
  await assertKillSwitchOff();
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
      return { text: await callProvider(config, messages), route: routeLabelFor(config) };
    } catch (error) {
      lastError = error instanceof AiProviderError ? error : new AiProviderError("AI_PROVIDER_UNREACHABLE", "Provider call failed");
    }
  }
  throw lastError ?? new AiProviderError("AI_PROVIDER_UNREACHABLE", "All candidate providers failed");
}

export type IndependentReply = { alias: string; text: string; route: string };

export async function generateIndependentPageReplies(
  page: AiPageUid,
  prompt: string,
  context: string | undefined,
  history: ChatMessage[],
  aliases: string[],
): Promise<IndependentReply[]> {
  await assertKillSwitchOff();
  const configs = await resolveProviderConfigs(AI_CAPABILITY_BY_PAGE[page]);
  if (!configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${AI_CAPABILITY_BY_PAGE[page]} provider with a stored credential`);
  }
  const user = context ? `${prompt}\n\n[脈絡]\n${context}` : prompt;
  const recent = history.filter((row) => row.content.trim().length > 0);
  const replies: IndependentReply[] = [];
  for (const [index, alias] of aliases.entries()) {
    const config = configs[index] ?? configs[0];
    if (!config) {
      replies.push({ alias, text: "", route: "" });
      continue;
    }
    const prior = replies
      .filter((row) => row.text.trim())
      .map((row) => `@${row.alias}：${row.text.trim().slice(0, 400)}`)
      .join("\n");
    const independentUser = [
      user,
      `[本則由參與者 @${alias} 獨立作答。必須提出與其他參與者不同的觀點、理由或風險，禁止複述或同文。]`,
      prior ? `[其他參與者已說過，請勿重複]\n${prior}` : "",
    ].filter(Boolean).join("\n\n");
    const messages: ChatMessage[] = [
      { role: "system", content: systemPromptFor(page, config.promptTemplate, alias) },
      ...recent,
      { role: "user", content: independentUser },
    ];
    const normalize = (value: string) => value.replace(/\s+/g, "").slice(0, 240);
    try {
      let text = await callProvider(config, messages, 0.8);
      const duplicated = replies.some((row) => row.text && normalize(row.text) === normalize(text));
      if (duplicated) {
        text = await callProvider(
          config,
          [
            ...messages,
            {
              role: "user",
              content: `上一則與 @${replies.map((row) => row.alias).join("、")} 同文。請改從不同風險、不同取捨或不同下一步重寫，禁止複述。`,
            },
          ],
          0.95,
        );
      }
      replies.push({ alias, text, route: routeLabelFor(config) });
    } catch {
      replies.push({ alias, text: "", route: routeLabelFor(config) });
    }
  }
  return replies;
}
