import { getSqlClient } from "../db/client";
import { listAiapiCredentials } from "../db/aiapiCredential";
import { AIAPI_PROMPT_TEMPLATE_TOKEN, eligibleProfiles, readProfiles, type AiapiProfile } from "@/lib/aiapiProfiles";

export type AiPageUid = "core" | "asset" | "video" | "edit";

export const AI_CAPABILITY_BY_PAGE: Record<AiPageUid, string> = {
  core: "chat",
  asset: "correction",
  video: "correction",
  edit: "correction",
};

export interface ProviderConfig {
  profileId: string;
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
    profileId: profile.profileId,
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
    "你是 ACPOS 影音生產作業系統 CORE 工作台的分析型 AI。",
    "ACPOS 處理專案、專題、藍圖、Canonical Script、素材、影片與剪輯。禁止解釋成收銀機、POS 或零售結帳。",
    "禁止自稱會議秘書。不要反問使用者現在在哪個專案或哪個模組。",
    "使用者問目前頁面或模組時：這是 CORE 工作台。若脈絡有工作項目，一併說明目前工作項目（故事／章節／世界觀／DNA／藍圖）；那是 CORE 內的工作項目，不是另一套產品。",
    "沒有產品版本號時不要編造，也不要把「無法確認版本」當唯一答案；直接說明這是 CORE 工作台與目前工作項目。",
    "脈絡區已有的專案／專題／工作項目／正式腳本必須沿用。",
    "直接回答本則問題，以繁體中文精簡、可執行；只產出分析與候選，不把回覆當成正式腳本。",
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

type CachedConfigs = { at: number; configs: ProviderConfig[]; grouped: boolean };

const CONFIG_CACHE_MS = 15_000;
const configCache = new Map<string, CachedConfigs>();
const UNGROUPED_FALLBACK_LIMIT = 2;

function uniqueProviders(configs: ProviderConfig[]): ProviderConfig[] {
  const seen = new Set<string>();
  const unique: ProviderConfig[] = [];
  for (const config of configs) {
    const key = config.provider.trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    unique.push(config);
  }
  return unique;
}

function cacheKey(
  capability: string,
  groupRaw: string,
  quarantineRaw: string,
  rights: string,
  data: string,
  budget: string,
): string {
  return [capability, groupRaw, quarantineRaw, rights, data, budget].join("\u0001");
}

const KILL_SWITCH_UID = "AIAPI-01-FLD-KILL-SWITCH";
const ROUTE_DECISION_UID = "AIAPI-01-FLD-ROUTE-DECISION";

async function writeRouteDecision(value: string): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ghsn_aiapi_field_projection (control_uid, value_text)
     VALUES (?, ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [ROUTE_DECISION_UID, value],
  );
}

function routeDecisionValue(configs: ProviderConfig[], blocked: string): string {
  if (!configs.length) return blocked;
  return `ROUTE_READY ${configs.map((config) => config.profileId).join(" ")}`.trim();
}

async function resolveRoute(capability: string): Promise<{ configs: ProviderConfig[]; grouped: boolean }> {
  const fields = await readAiapiFields();
  const groupRaw = clean(fields.get("AIAPI-01-FLD-CANDIDATE-GROUP"));
  const quarantineRaw = clean(fields.get("AIAPI-01-FLD-OPS-QUARANTINE"));
  const rights = clean(fields.get("AIAPI-01-FLD-PF-RIGHTS"));
  const data = clean(fields.get("AIAPI-01-FLD-PF-DATA"));
  const budget = clean(fields.get("AIAPI-01-FLD-PF-BUDGET"));
  const key = cacheKey(capability, groupRaw, quarantineRaw, rights, data, budget);
  const cached = configCache.get(key);
  if (cached && Date.now() - cached.at < CONFIG_CACHE_MS) {
    return { configs: cached.configs, grouped: cached.grouped };
  }
  const profiles = readProfiles((uid) => fields.get(uid) ?? null);
  const admitted = eligibleProfiles(profiles, capability, {
    groupRaw,
    quarantineRaw,
    rights,
    data,
    budget,
  });
  const secrets = await listAiapiCredentials();
  const configs: ProviderConfig[] = [];
  for (const profile of admitted.profiles) {
    const credential = secrets.get(profile.profileId);
    if (!credential) continue;
    const config = toProviderConfig(profile, credential);
    if (config) configs.push(config);
  }
  const ordered = admitted.grouped ? configs : uniqueProviders(configs);
  configCache.set(key, { at: Date.now(), configs: ordered, grouped: admitted.grouped });
  return { configs: ordered, grouped: admitted.grouped };
}

export async function resolveProviderConfigs(capability: string): Promise<ProviderConfig[]> {
  return (await resolveRoute(capability)).configs;
}

function fallbackLimit(route: { configs: ProviderConfig[]; grouped: boolean }): number {
  return route.grouped ? route.configs.length : UNGROUPED_FALLBACK_LIMIT;
}

export async function assignedAiRouteSnapshot(capability = AI_CAPABILITY_BY_PAGE.core): Promise<string> {
  const fields = await readAiapiFields();
  if (fields.get(KILL_SWITCH_UID) === "ON") return "";
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

async function assertKillSwitchOff(): Promise<void> {
  const fields = await readAiapiFields();
  if (fields.get(KILL_SWITCH_UID) === "ON") {
    await writeRouteDecision("ROUTE_BLOCKED");
    throw new AiProviderError("AI_PROVIDER_KILL_SWITCH", "Kill switch is on");
  }
}

async function admitRoute(capability: string): Promise<{ configs: ProviderConfig[]; grouped: boolean }> {
  await assertKillSwitchOff();
  const route = await resolveRoute(capability);
  await writeRouteDecision(routeDecisionValue(route.configs, "ROUTE_BLOCKED"));
  return route;
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
  const route = await admitRoute(capability);
  if (!route.configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${capability} provider with a stored credential`);
  }
  let lastError: AiProviderError | null = null;
  for (const config of route.configs.slice(0, fallbackLimit(route))) {
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
  const route = await admitRoute(AI_CAPABILITY_BY_PAGE[page]);
  if (!route.configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${AI_CAPABILITY_BY_PAGE[page]} provider with a stored credential`);
  }
  const user = context ? `${prompt}\n\n[脈絡]\n${context}` : prompt;
  const recent = history.filter((row) => row.content.trim().length > 0);
  let lastError: AiProviderError | null = null;
  for (const config of route.configs.slice(0, fallbackLimit(route))) {
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
  const route = await admitRoute(AI_CAPABILITY_BY_PAGE[page]);
  if (!route.configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${AI_CAPABILITY_BY_PAGE[page]} provider with a stored credential`);
  }
  const user = context ? `${prompt}\n\n[脈絡]\n${context}` : prompt;
  const recent = history.filter((row) => row.content.trim().length > 0);
  if (aliases.length > route.configs.length) {
    throw new AiProviderError(
      "AI_PROVIDER_MULTI_SHORT",
      `Multi needs ${aliases.length} ${AI_CAPABILITY_BY_PAGE[page]} providers; ${route.configs.length} ready`,
    );
  }
  return Promise.all(
    aliases.map(async (alias, index) => {
      const config = route.configs[index];
      if (!config) return { alias, text: "", route: "" };
      const independentUser = [
        user,
        `[本則由場次別名 @${alias} 獨立作答。A／B／C 只是場次別名，不是固定供應商。必須提出與其他參與者不同的觀點、理由或風險，禁止複述或同文。]`,
      ].join("\n\n");
      const messages: ChatMessage[] = [
        { role: "system", content: systemPromptFor(page, config.promptTemplate, alias) },
        ...recent,
        { role: "user", content: independentUser },
      ];
      try {
        const text = await callProvider(config, messages, 0.8);
        return { alias, text, route: routeLabelFor(config) };
      } catch {
        return { alias, text: "", route: routeLabelFor(config) };
      }
    }),
  );
}
