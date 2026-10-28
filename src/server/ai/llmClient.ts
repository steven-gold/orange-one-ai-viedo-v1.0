import { getSqlClient } from "../db/client";
import { listAiapiCredentials } from "../db/aiapiCredential";
import {
  adapterFamily,
  buildProviderRequest,
  parseProviderSseFrame,
  readProviderText,
  type AdapterFamily,
} from "@/lib/aiapiAdapter";
import { AIAPI_PROMPT_TEMPLATE_TOKEN, eligibleProfiles, readProfiles, type AiapiProfile } from "@/lib/aiapiProfiles";
import {
  MAX_BATCH_CONTINUATIONS,
  MAX_GENERATION_CONTINUATIONS,
  MAX_LOOP_REPAIRS,
  batchRangeNeedsMore,
  continuationUserMessage,
  detectGenerationLoop,
  detectUnusableOutput,
  formatContractForPrompt,
  modelBlockedForLanguage,
  inferTruncated,
  loopRepairUserMessage,
  mergeContinuation,
  shouldCheckStreamLoop,
  splitSseFrames,
  temperatureFor,
  type ConversationTaskContract,
  type ConversationTaskKind,
} from "@/lib/conversationTask";

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
  adapterType: string;
  family: AdapterFamily;
  httpMethod: string;
  maxContext: number;
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
  const url = `${base}${endpoint}`;
  const family = adapterFamily(profile.adapterType, url);
  if (!family) return null;

  const model = clean(profile.modelId);
  if (!model) return null;
  const timeoutSeconds = Number.parseInt(clean(profile.timeoutSeconds), 10);
  const timeoutMs = Number.isFinite(timeoutSeconds) && timeoutSeconds > 0 ? timeoutSeconds * 1000 : 20000;
  const maxContext = Number.parseInt(clean(profile.maxContext), 10);

  return {
    profileId: profile.profileId,
    url,
    model,
    provider,
    credential,
    timeoutMs,
    promptTemplate: clean(profile.promptTemplate),
    adapterType: clean(profile.adapterType),
    family,
    httpMethod: clean(profile.httpMethod) || "POST",
    maxContext: Number.isFinite(maxContext) && maxContext > 0 ? maxContext : 0,
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
    "直接完成使用者要求的動作，以繁體中文可執行地回答。要求實際交付時產出該交付物；大型任務只寫本批次並標示未完成範圍。禁止把分析當成執行，禁止未完成卻宣稱全部完成。",
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

type ProviderTurn = { content: string; finishReason: string; loopStopped?: boolean; cancelled?: boolean };

export class GenerationCancelled extends Error {
  constructor(readonly partial = "") {
    super("Generation cancelled");
    this.name = "GenerationCancelled";
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

function mergeAbort(timeoutMs: number, external?: AbortSignal): { signal: AbortSignal; stop: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onExternal = () => controller.abort();
  if (external?.aborted) controller.abort();
  else external?.addEventListener("abort", onExternal);
  return {
    signal: controller.signal,
    stop: () => {
      clearTimeout(timer);
      external?.removeEventListener("abort", onExternal);
    },
  };
}

async function readJsonTurn(response: Response, family: AdapterFamily, onToken?: (text: string) => void): Promise<ProviderTurn> {
  const payload = (await response.json()) as unknown;
  const turn = readProviderText(payload, family);
  if (!turn.content) throw new AiProviderError("AI_PROVIDER_EMPTY_RESPONSE", "Provider returned no message content");
  onToken?.(turn.content);
  return { content: turn.content, finishReason: turn.finishReason };
}

async function readSseTurn(
  response: Response,
  family: AdapterFamily,
  userSignal?: AbortSignal,
  onToken?: (text: string) => void,
): Promise<ProviderTurn> {
  const body = response.body;
  if (!body) throw new AiProviderError("AI_PROVIDER_EMPTY_RESPONSE", "Provider returned no stream body");
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let content = "";
  let finishReason = "";
  let lastChecked = 0;
  const stopLoop = (prefix: string): ProviderTurn => ({
    content: prefix.trim() || content,
    finishReason: finishReason || "loop_stopped",
    loopStopped: true,
  });
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const split = splitSseFrames(buffer);
      buffer = split.rest;
      for (const frame of split.frames) {
        const parsed = parseProviderSseFrame(frame, family);
        if (parsed.done) {
          if (!content) throw new AiProviderError("AI_PROVIDER_EMPTY_RESPONSE", "Provider returned no message content");
          const looped = detectGenerationLoop(content);
          if (looped.loop) return stopLoop(looped.validPrefix);
          return { content, finishReason };
        }
        if (parsed.delta) {
          content += parsed.delta;
          onToken?.(parsed.delta);
        }
        if (parsed.finishReason) finishReason = parsed.finishReason;
        if (shouldCheckStreamLoop(content.length, lastChecked)) {
          lastChecked = content.length;
          const looped = detectGenerationLoop(content);
          if (looped.loop) return stopLoop(looped.validPrefix);
        }
      }
    }
  } catch (error) {
    if (content) {
      if (userSignal?.aborted) return { content, finishReason: "cancelled", cancelled: true };
      const looped = detectGenerationLoop(content);
      if (looped.loop) return stopLoop(looped.validPrefix);
      return { content, finishReason: finishReason || "stop" };
    }
    throw error;
  } finally {
    try {
      await reader.cancel();
    } catch {
      // Stream already closed after abort or natural end.
    }
  }
  const leftover = splitSseFrames(buffer);
  for (const frame of leftover.frames) {
    const parsed = parseProviderSseFrame(frame, family);
    if (parsed.delta) {
      content += parsed.delta;
      onToken?.(parsed.delta);
    }
    if (parsed.finishReason) finishReason = parsed.finishReason;
  }
  if (!content) throw new AiProviderError("AI_PROVIDER_EMPTY_RESPONSE", "Provider returned no message content");
  const looped = detectGenerationLoop(content);
  if (looped.loop) return stopLoop(looped.validPrefix);
  return { content, finishReason };
}

function fitMessages(messages: ChatMessage[], maxContext: number): ChatMessage[] {
  if (!maxContext || maxContext >= 32000) return messages;
  const budget = Math.max(800, Math.floor(maxContext * 2));
  const system = messages.filter((row) => row.role === "system");
  const rest = messages.filter((row) => row.role !== "system");
  const kept: ChatMessage[] = [];
  let used = system.reduce((sum, row) => sum + row.content.length, 0);
  for (let index = rest.length - 1; index >= 0; index -= 1) {
    const row = rest[index];
    const size = row.content.length;
    if (kept.length && used + size > budget) break;
    kept.unshift(row);
    used += size;
  }
  return [...system, ...kept];
}

function shouldRetryWithoutStream(status: number): boolean {
  return status >= 400 && status < 500 && status !== 401 && status !== 403;
}

function lastTurn(messages: ChatMessage[]): ChatMessage[] {
  const system = messages.filter((row) => row.role === "system");
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === "user") return [...system, messages[index]];
  }
  return messages;
}

async function postProvider(
  config: ProviderConfig,
  messages: ChatMessage[],
  temperature: number,
  stream: boolean,
  signal: AbortSignal,
): Promise<Response> {
  const request = buildProviderRequest({
    url: config.url,
    credential: config.credential,
    adapterType: config.adapterType,
    model: config.model,
    messages,
    temperature,
    stream,
    maxTokens: 4096,
    httpMethod: config.httpMethod,
  });
  if (!request) throw new AiProviderError("AI_PROVIDER_UNREACHABLE", `${config.provider} adapter is unsupported`);
  return fetch(request.url, { ...request.init, signal, cache: "no-store" });
}

async function callProvider(
  config: ProviderConfig,
  messages: ChatMessage[],
  temperature = 0.2,
  signal?: AbortSignal,
  onToken?: (text: string) => void,
): Promise<ProviderTurn> {
  if (signal?.aborted) throw new GenerationCancelled("");
  const merged = mergeAbort(config.timeoutMs, signal);
  try {
    const packed = fitMessages(messages, config.maxContext);
    let response = await postProvider(config, packed, temperature, true, merged.signal);
    if (!response.ok && shouldRetryWithoutStream(response.status)) {
      response = await postProvider(config, packed, temperature, false, merged.signal);
    }
    if (!response.ok && shouldRetryWithoutStream(response.status) && packed.length > lastTurn(packed).length) {
      response = await postProvider(config, lastTurn(packed), temperature, false, merged.signal);
    }
    if (!response.ok) {
      const detail = (await response.text().catch(() => "")).slice(0, 200);
      throw new AiProviderError("AI_PROVIDER_HTTP_ERROR", `${config.provider} responded ${response.status}: ${detail}`);
    }
    const contentType = (response.headers.get("content-type") ?? "").toLowerCase();
    if (contentType.includes("text/event-stream") && response.body) {
      return await readSseTurn(response, config.family, signal, onToken);
    }
    return await readJsonTurn(response, config.family, onToken);
  } catch (error) {
    if (error instanceof AiProviderError) throw error;
    if (error instanceof GenerationCancelled) throw error;
    if (isAbortError(error)) {
      if (signal?.aborted) throw new GenerationCancelled("");
      throw new AiProviderError("AI_PROVIDER_TIMEOUT", `Provider call exceeded ${config.timeoutMs}ms`);
    }
    throw new AiProviderError("AI_PROVIDER_UNREACHABLE", error instanceof Error ? error.message : "Provider call failed");
  } finally {
    merged.stop();
  }
}

async function completeTurn(
  config: ProviderConfig,
  messages: ChatMessage[],
  temperature: number,
  contract?: ConversationTaskContract,
  signal?: AbortSignal,
  onToken?: (text: string) => void,
): Promise<{ text: string; truncated: boolean; loop: boolean; finishReason: string }> {
  const first = await callProvider(config, messages, temperature, signal, onToken);
  let text = first.content;
  let finishReason = first.finishReason;
  if (first.cancelled) throw new GenerationCancelled(text);
  let truncated = inferTruncated(text, finishReason);
  const loopCheck = first.loopStopped ? { loop: true, validPrefix: text, reason: "stream_loop" } : detectGenerationLoop(text);
  if (loopCheck.loop) {
    text = loopCheck.validPrefix.trim();
    truncated = true;
    if (text && MAX_LOOP_REPAIRS > 0) {
      try {
        const repaired = await callProvider(
          config,
          [...messages, { role: "assistant", content: text }, { role: "user", content: loopRepairUserMessage() }],
          temperature,
          signal,
          onToken,
        );
        if (repaired.cancelled) throw new GenerationCancelled(mergeContinuation(text, repaired.content));
        const merged = mergeContinuation(text, repaired.content);
        const again = repaired.loopStopped ? { loop: true, validPrefix: merged } : detectGenerationLoop(merged);
        text = again.loop ? again.validPrefix.trim() || text : merged;
        finishReason = repaired.finishReason;
        truncated = again.loop || inferTruncated(text, finishReason);
      } catch (error) {
        if (error instanceof GenerationCancelled) throw new GenerationCancelled(error.partial || text);
        throw error;
      }
    }
    return { text, truncated, loop: true, finishReason };
  }
  let continuations = 0;
  const maxContinuations = contract?.batched ? MAX_BATCH_CONTINUATIONS : MAX_GENERATION_CONTINUATIONS;
  while ((truncated || (contract?.batched ? batchRangeNeedsMore(contract, text) : false)) && continuations < maxContinuations) {
    continuations += 1;
    const follow = contract ? continuationUserMessage(contract) : "從上次結尾繼續寫，不要重複已寫內容。未完成不得宣稱全部完成。";
    try {
      const next = await callProvider(
        config,
        [...messages, { role: "assistant", content: text }, { role: "user", content: follow }],
        temperature,
        signal,
        onToken,
      );
      if (next.cancelled) throw new GenerationCancelled(mergeContinuation(text, next.content));
      text = mergeContinuation(text, next.content);
      finishReason = next.finishReason;
      const looped = next.loopStopped ? { loop: true, validPrefix: text } : detectGenerationLoop(text);
      if (looped.loop) {
        text = looped.validPrefix.trim() || text;
        return { text, truncated: true, loop: true, finishReason };
      }
      truncated = inferTruncated(next.content, next.finishReason);
    } catch (error) {
      if (error instanceof GenerationCancelled) throw new GenerationCancelled(error.partial || text);
      throw error;
    }
  }
  return { text, truncated, loop: false, finishReason };
}

export async function callChat(messages: ChatMessage[], capability: string): Promise<string> {
  const route = await admitRoute(capability);
  if (!route.configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${capability} provider with a stored credential`);
  }
  let lastError: AiProviderError | null = null;
  for (const config of route.configs.slice(0, fallbackLimit(route))) {
    if (modelBlockedForLanguage(config.model)) {
      lastError = new AiProviderError("AI_PROVIDER_UNUSABLE_OUTPUT", "Provider blocked for language");
      continue;
    }
    try {
      const turn = await completeTurn(config, messages, 0.2);
      if (detectUnusableOutput(turn.text)) {
        lastError = new AiProviderError("AI_PROVIDER_UNUSABLE_OUTPUT", "Provider output unusable");
        continue;
      }
      return turn.text;
    } catch (error) {
      if (error instanceof GenerationCancelled) throw error;
      lastError = error instanceof AiProviderError ? error : new AiProviderError("AI_PROVIDER_UNREACHABLE", "Provider call failed");
    }
  }
  throw lastError ?? new AiProviderError("AI_PROVIDER_UNREACHABLE", "All candidate providers failed");
}

export function routeLabelFor(config: Pick<ProviderConfig, "provider" | "model">): string {
  return [config.provider, config.model].filter((part) => part.trim()).join(" / ");
}

export type PageReply = { text: string; route: string; truncated: boolean; loop: boolean };

export async function generatePageReply(
  page: AiPageUid,
  prompt: string,
  context?: string,
  history: ChatMessage[] = [],
  options?: { contract?: ConversationTaskContract; kind?: ConversationTaskKind; signal?: AbortSignal; onToken?: (text: string) => void },
): Promise<PageReply> {
  const route = await admitRoute(AI_CAPABILITY_BY_PAGE[page]);
  if (!route.configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${AI_CAPABILITY_BY_PAGE[page]} provider with a stored credential`);
  }
  const contractText = options?.contract ? formatContractForPrompt(options.contract) : "";
  const parts = [prompt];
  if (context) parts.push(`[脈絡]\n${context}`);
  if (contractText) parts.push(`[任務契約]\n${contractText}`);
  const user = parts.join("\n\n");
  const recent = history.filter((row) => row.content.trim().length > 0);
  const temperature = temperatureFor(options?.kind ?? options?.contract?.kind ?? "question");
  let lastError: AiProviderError | null = null;
  for (const config of route.configs.slice(0, fallbackLimit(route))) {
    if (modelBlockedForLanguage(config.model, options?.contract?.language)) {
      lastError = new AiProviderError("AI_PROVIDER_UNUSABLE_OUTPUT", "Provider blocked for language");
      continue;
    }
    const messages: ChatMessage[] = [
      { role: "system", content: systemPromptFor(page, config.promptTemplate) },
      ...recent,
      { role: "user", content: user },
    ];
    try {
      const turn = await completeTurn(config, messages, temperature, options?.contract, options?.signal, options?.onToken);
      if (detectUnusableOutput(turn.text)) {
        lastError = new AiProviderError("AI_PROVIDER_UNUSABLE_OUTPUT", "Provider output unusable");
        continue;
      }
      return { text: turn.text, route: routeLabelFor(config), truncated: turn.truncated, loop: turn.loop };
    } catch (error) {
      if (error instanceof GenerationCancelled) throw error;
      lastError = error instanceof AiProviderError ? error : new AiProviderError("AI_PROVIDER_UNREACHABLE", "Provider call failed");
    }
  }
  throw lastError ?? new AiProviderError("AI_PROVIDER_UNREACHABLE", "All candidate providers failed");
}

export type IndependentReply = { alias: string; text: string; route: string; errorCode?: string };

export async function generateIndependentPageReplies(
  page: AiPageUid,
  prompt: string,
  context: string | undefined,
  history: ChatMessage[],
  aliases: string[],
  signal?: AbortSignal,
  onToken?: (text: string, alias?: string) => void,
  contract?: ConversationTaskContract,
): Promise<IndependentReply[]> {
  const route = await admitRoute(AI_CAPABILITY_BY_PAGE[page]);
  if (!route.configs.length) {
    throw new AiProviderError("AI_PROVIDER_NOT_CONFIGURED", `No enabled ${AI_CAPABILITY_BY_PAGE[page]} provider with a stored credential`);
  }
  const contractText = contract ? formatContractForPrompt(contract) : "";
  const parts = [prompt];
  if (context) parts.push(`[脈絡]\n${context}`);
  if (contractText) parts.push(`[任務契約]\n${contractText}`);
  const user = parts.join("\n\n");
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
      if (modelBlockedForLanguage(config.model, contract?.language)) {
        return { alias, text: "", route: routeLabelFor(config), errorCode: "AI_PROVIDER_UNUSABLE_OUTPUT" };
      }
      try {
        const turn = await completeTurn(config, messages, 0.8, contract, signal, onToken ? (text) => onToken(text, alias) : undefined);
        if (detectUnusableOutput(turn.text)) {
          return { alias, text: "", route: routeLabelFor(config), errorCode: "AI_PROVIDER_UNUSABLE_OUTPUT" };
        }
        return { alias, text: turn.text, route: routeLabelFor(config) };
      } catch (error) {
        if (error instanceof GenerationCancelled) throw error;
        const errorCode = error instanceof AiProviderError ? error.code : "AI_PROVIDER_UNREACHABLE";
        return { alias, text: "", route: routeLabelFor(config), errorCode };
      }
    }),
  );
}
