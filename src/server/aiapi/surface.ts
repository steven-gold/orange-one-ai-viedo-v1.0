import { capabilityFromModule } from "@/lib/aiapiProviderCatalog";

/**
 * A provider surface is whatever the provider itself publishes about its own
 * API: an OpenAI-compatible model list, and optionally a machine-readable
 * manifest (endpoint catalogue) plus a typed model catalogue. Nothing here is
 * inferred from the key format or guessed from a model name.
 */
export interface SurfaceModel {
  id: string;
  title: string;
  type: string;
  apiFormat: string;
  apiEndpoint: string;
  contextWindow: string;
  billing: string;
  description: string;
  inputHint: string;
  tags: string;
}

export interface SurfaceOperation {
  method: string;
  path: string;
  title: string;
  description: string;
}

export interface ProviderSurface {
  baseUrl: string;
  apiBase: string;
  providerId: string;
  providerName: string;
  models: SurfaceModel[];
  operations: SurfaceOperation[];
  mediaEndpoint: string;
  mediaStatusPath: string;
}

export type SurfaceResult =
  | { ok: true; surface: ProviderSurface }
  | { ok: false; code: string };

export interface ResolvedBase {
  ok: true;
  baseUrl: string;
  providerName: string;
}
export type BaseResult = ResolvedBase | { ok: false; code: string };

const PROBE_TIMEOUT_MS = 8000;
const SURFACE_TIMEOUT_MS = 12000;

const TYPE_CAPABILITY: Record<string, string> = {
  chat: "chat",
  image: "image-generation",
  video: "video-generation",
  audio: "audio-generation",
};

function trimBase(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

/**
 * The same key is carried differently by different gateways. Probing tries
 * every documented scheme so an unfamiliar key is discovered rather than
 * rejected because the first guess was wrong.
 */
function authVariants(secret: string): Record<string, string>[] {
  return [
    { authorization: `Bearer ${secret}` },
    { authorization: secret },
    { "x-api-key": secret },
    { "api-key": secret },
    { "x-goog-api-key": secret },
  ];
}

function authHeaders(secret: string): Record<string, string> {
  return { accept: "application/json", ...authVariants(secret)[0] };
}

/** Returns the first response that is not an auth rejection. */
async function fetchAccepted(
  url: string,
  secret: string,
  timeoutMs: number,
): Promise<{ status: number; text: string; contentType: string }> {
  let denied: { status: number; text: string; contentType: string } | null = null;
  for (const headers of authVariants(secret)) {
    const response = await fetchWithTimeout(
      url,
      { method: "GET", headers: { accept: "application/json", ...headers } },
      timeoutMs,
    );
    if (response.status === 401 || response.status === 403) {
      denied = response;
      continue;
    }
    return response;
  }
  return denied ?? { status: 0, text: "", contentType: "" };
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<{ status: number; text: string; contentType: string }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal, cache: "no-store" });
    const text = await response.text().catch(() => "");
    return { status: response.status, text, contentType: response.headers.get("content-type") ?? "" };
  } finally {
    clearTimeout(timer);
  }
}

function readJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

function modelRows(payload: unknown): unknown[] {
  if (!payload || typeof payload !== "object") return [];
  const record = payload as { data?: unknown; models?: unknown };
  if (Array.isArray(record.models)) return record.models;
  if (Array.isArray(record.data)) return record.data;
  if (Array.isArray(payload)) return payload as unknown[];
  return [];
}

function normalizeBase(input: string): URL | null {
  const raw = /^https?:\/\//i.test(input) ? input : `https://${input}`;
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" && url.protocol !== "http:") return null;
    return url;
  } catch {
    return null;
  }
}

function providerIdFromHost(host: string): string {
  const clean = host.toLowerCase().replace(/^www\./, "");
  const withoutApi = clean.replace(/^api\./, "");
  const parts = withoutApi.split(".").filter(Boolean);
  const label = parts.length > 1 ? parts[parts.length - 2] : parts[0] ?? clean;
  return label.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "provider";
}

async function probeBase(base: string, secret: string): Promise<{ name: string } | "DENIED" | null> {
  let denied = false;
  for (const path of ["/skills/models", "/models"]) {
    try {
      const { status, text, contentType } = await fetchAccepted(
        `${trimBase(base)}${path}`,
        secret,
        PROBE_TIMEOUT_MS,
      );
      if (status === 401 || status === 403) {
        denied = true;
        continue;
      }
      if (status !== 200) continue;
      if (!/json/i.test(contentType)) continue;
      const rows = modelRows(readJson(text));
      if (!rows.length) continue;
      return { name: "" };
    } catch {
      // try the next candidate
    }
  }
  return denied ? "DENIED" : null;
}

function registrableDomain(host: string): string {
  const parts = host.toLowerCase().split(".").filter(Boolean);
  if (parts.length <= 2) return parts.join(".");
  const twoLevel = /^(com|net|org|gov|edu)\.(cn|hk|tw|jp|uk)$/;
  const tail = parts.slice(-2).join(".");
  return twoLevel.test(tail) ? parts.slice(-3).join(".") : tail;
}

const THIRD_PARTY = /(^|\.)(googletagmanager|google-analytics|doubleclick|bootcdn|jsdelivr|unpkg|cloudflare|sentry|segment|mixpanel|hotjar|w3\.org|schema\.org)$/;

/**
 * Hosts the vendor page itself references: same-domain hosts, plus explicitly
 * named API hosts on another domain (a portal often serves its API from a
 * separate api.* host). Known third-party CDNs and analytics are skipped so
 * the key is never sent to them.
 */
function apiHostsFromPage(page: URL, html: string): string[] {
  const hosts = new Set<string>();
  const domain = registrableDomain(page.hostname);
  for (const match of html.matchAll(/https?:\/\/([a-z0-9.-]+)/gi)) {
    const host = match[1].toLowerCase().replace(/\.$/, "");
    if (!host || host === page.hostname) continue;
    if (THIRD_PARTY.test(host)) continue;
    if (registrableDomain(host) === domain) {
      hosts.add(host);
      continue;
    }
    if (/^(api|openapi|gateway)[.-]/.test(host) || /(^|[.-])(ai-models|ai-api-gateway)([.-]|$)/.test(host)) {
      hosts.add(host);
    }
  }
  return Array.from(hosts);
}

function baseCandidates(host: string): string[] {
  return [
    `https://${host}`,
    `https://${host}/v1`,
    `https://${host}/api/v1`,
    `https://${host}/api`,
    `https://${host}/openai/v1`,
    `https://${host}/api/openai/v1`,
  ];
}

/**
 * Accepts what a user actually has: an API base, an OpenAI-compatible host, or
 * a vendor website address. A website is only used to locate the API host that
 * its own page references; the returned base is then verified with the key.
 */
export async function resolveApiBase(input: string, secret: string): Promise<BaseResult> {
  const url = normalizeBase(input);
  if (!url) return { ok: false, code: "AIAPI_PROFILE_BASE_URL_INVALID" };
  const origin = url.origin;
  const candidates = new Set<string>();
  if (/\/v\d+$/i.test(url.pathname.replace(/\/+$/, ""))) {
    candidates.add(`${origin}${url.pathname.replace(/\/+$/, "")}`);
  }
  candidates.add(origin);
  candidates.add(`${origin}/v1`);
  candidates.add(`${origin}/api/v1`);
  candidates.add(`${origin}/api`);
  candidates.add(`${origin}/api/openai/v1`);
  candidates.add(`${origin}/openai/v1`);

  let denied = false;
  for (const base of candidates) {
    const probe = await probeBase(base, secret);
    if (probe === "DENIED") {
      denied = true;
      continue;
    }
    if (probe) return { ok: true, baseUrl: trimBase(base), providerName: probe.name };
  }

  // The address may be a front-end page that talks to a separate API host.
  // Read the page once and try only the API origins it publishes itself.
  try {
    const page = await fetchWithTimeout(url.toString(), { method: "GET" }, PROBE_TIMEOUT_MS);
    for (const host of apiHostsFromPage(url, page.text)) {
      for (const base of baseCandidates(host)) {
        const probe = await probeBase(base, secret);
        if (probe === "DENIED") {
          denied = true;
          continue;
        }
        if (probe) return { ok: true, baseUrl: base, providerName: probe.name };
      }
    }
  } catch {
    // fall through to the unreachable result
  }

  return { ok: false, code: denied ? "AIAPI_PROVIDER_KEY_INVALID" : "AIAPI_PROVIDER_SURFACE_UNREACHABLE" };
}

function parseSurfaceModels(payload: unknown): SurfaceModel[] {
  const models: SurfaceModel[] = [];
  for (const row of modelRows(payload)) {
    if (!row || typeof row !== "object") continue;
    const item = row as Record<string, unknown>;
    if (item.available_for_this_key === false) continue;
    const id = typeof item.name === "string" ? item.name : typeof item.id === "string" ? item.id : "";
    if (!id.trim()) continue;
    const rawId = id.trim().replace(/^models\//, "");
    const type = typeof item.type === "string" ? item.type.toLowerCase() : "";
    const context = item.context_length ?? item.context_window ?? item.max_context_length;
    const prompt = (item.pricing as { prompt?: unknown } | undefined)?.prompt;
    const tags = Array.isArray(item.tags)
      ? item.tags.filter((tag): tag is string => typeof tag === "string").join(", ")
      : "";
    models.push({
      id: rawId,
      title: typeof item.display_name === "string" && item.display_name.trim() ? item.display_name.trim() : rawId,
      type,
      apiFormat: typeof item.api_format === "string" ? item.api_format.toLowerCase() : "",
      apiEndpoint: typeof item.api_endpoint === "string" ? item.api_endpoint : "",
      contextWindow: typeof context === "number" ? String(context) : "",
      billing:
        typeof prompt === "string" && prompt !== "0"
          ? `prompt ${prompt} / completion ${String((item.pricing as { completion?: unknown } | undefined)?.completion ?? "")}`
          : "",
      description: typeof item.description === "string" ? item.description.trim().slice(0, 400) : "",
      inputHint: typeof item.input_hint === "string" ? item.input_hint.trim().slice(0, 300) : "",
      tags,
    });
  }
  return models;
}

function parseManifest(payload: unknown): { platform: string; operations: SurfaceOperation[] } {
  if (!payload || typeof payload !== "object") return { platform: "", operations: [] };
  const record = payload as { platform?: unknown; categories?: unknown };
  const platform = typeof record.platform === "string" ? record.platform.trim() : "";
  const operations: SurfaceOperation[] = [];
  const seen = new Set<string>();
  if (Array.isArray(record.categories)) {
    for (const category of record.categories) {
      if (!category || typeof category !== "object") continue;
      const endpoints = (category as { endpoints?: unknown }).endpoints;
      if (!Array.isArray(endpoints)) continue;
      for (const endpoint of endpoints) {
        if (!endpoint || typeof endpoint !== "object") continue;
        const item = endpoint as Record<string, unknown>;
        const method = typeof item.method === "string" ? item.method.toUpperCase() : "";
        const path = typeof item.path === "string" ? item.path.trim() : "";
        if (!method || !path.startsWith("/")) continue;
        // Templated paths need a concrete resource, so they stay documented
        // rather than becoming callable profiles.
        if (path.includes("{")) continue;
        const key = `${method} ${path}`;
        if (seen.has(key)) continue;
        seen.add(key);
        operations.push({
          method,
          path,
          title: typeof item.name === "string" ? item.name.trim() : path,
          description: typeof item.description === "string" ? item.description : "",
        });
      }
    }
  }
  return { platform, operations };
}

function isGenerationOperation(path: string): boolean {
  if (path.startsWith("/v1/skills") || path.startsWith("/skills")) return false;
  return /(generate|chat|messages|responses|media|video|image|audio)/i.test(path);
}

export function expandEndpoint(template: string, model: string): string {
  const withModel = template.trim().replace(/\{model(?:_name)?\}/gi, model);
  return withModel.replace(/\{action\}/gi, "generateContent");
}

const CHAT_OUTPUT: Record<string, string> = {
  openai: "choices[0].message.content",
  gemini: "candidates[0].content.parts[].text",
  anthropic: "content[].text",
};

export function adapterForEndpoint(path: string, declaredFormat = ""): string {
  const format = declaredFormat.trim().toLowerCase();
  if (format === "gemini" || format === "anthropic" || format === "openai") return format;
  if (/:generateContent/i.test(path) || /\/v1beta\//i.test(path)) return "gemini";
  if (/\/messages(\?|$)/i.test(path)) return "anthropic";
  if (/\/(media|video|image|audio|music)\//i.test(path)) return "http-json";
  return "openai";
}

interface PricingGroup {
  is_active?: unknown;
  billing_method?: unknown;
  base_price?: unknown;
  input_token_price?: unknown;
  output_token_price?: unknown;
  current_time_discount?: unknown;
  option_prices?: unknown;
}

function price(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function amount(value: number): string {
  return Number(value.toFixed(4)).toString();
}

/**
 * Formats the vendor's own active pricing group. Nothing is estimated: when
 * the vendor publishes no active group the field stays empty.
 */
export function formatPricing(json: unknown): string {
  const groups = (json as { channel_groups?: unknown } | null)?.channel_groups;
  if (!Array.isArray(groups)) return "";
  const live = (groups as PricingGroup[]).filter((group) => group?.is_active === true);
  const group = live[0];
  if (!group) return "";
  const method = typeof group.billing_method === "string" ? group.billing_method.trim() : "";
  const base = price(group.base_price);
  const input = price(group.input_token_price);
  const output = price(group.output_token_price);
  const discount = price(group.current_time_discount);
  let text = "";
  if (method === "按token" || method === "按 token") {
    const parts: string[] = [];
    if (input) parts.push(`輸入 ${amount(input)}`);
    if (output) parts.push(`輸出 ${amount(output)}`);
    text = parts.length ? `按 token：${parts.join("、")}` : "";
  } else if (method === "按次") {
    text = base ? `按次：每次 ${amount(base)}` : "";
  } else if (method === "按秒") {
    text = base ? `按秒：每秒 ${amount(base)}` : "";
  } else if (base) {
    text = method ? `${method}：${amount(base)}` : amount(base);
  }
  if (!text) return "";
  if (discount && discount !== 1) text += `（折扣 ${amount(discount)}）`;
  const options = Array.isArray(group.option_prices) ? (group.option_prices as Record<string, unknown>[]) : [];
  const notable = options
    .map((option) => ({
      label: typeof option.option_label === "string" ? option.option_label : "",
      value: price(option.final_output_token_price ?? option.final_price),
    }))
    .filter((option) => option.label && option.value && option.value !== (output || base));
  if (notable.length) {
    text += `；${notable
      .slice(0, 2)
      .map((option) => `${option.label} ${amount(option.value)}`)
      .join("、")}`;
  }
  return text;
}

async function readPricing(base: string, secret: string, modelId: string): Promise<string> {
  try {
    const response = await fetchAccepted(
      `${base}/skills/models/${encodeURIComponent(modelId)}/pricing`,
      secret,
      PROBE_TIMEOUT_MS,
    );
    if (response.status !== 200 || !/json/i.test(response.contentType)) return "";
    return formatPricing(readJson(response.text));
  } catch {
    return "";
  }
}

/** Fills the billing column from each model's own pricing endpoint. */
async function attachPricing(base: string, secret: string, models: SurfaceModel[]): Promise<SurfaceModel[]> {
  const queue = models.filter((model) => !model.billing && model.id);
  let cursor = 0;
  const worker = async (): Promise<void> => {
    while (cursor < queue.length) {
      const model = queue[cursor];
      cursor += 1;
      const billing = await readPricing(base, secret, model.id);
      if (billing) model.billing = billing;
    }
  };
  await Promise.all(Array.from({ length: Math.min(8, queue.length) }, worker));
  return models;
}

/**
 * Reads the surface the provider publishes at the resolved base. A JSON model
 * list is mandatory; the manifest and the typed catalogue are used when the
 * provider exposes them.
 */
export async function fetchSurface(baseUrl: string, secret: string): Promise<SurfaceResult> {
  const base = trimBase(baseUrl);
  const [manifestRes, skillsRes] = await Promise.all([
    fetchAccepted(`${base}/skills`, secret, SURFACE_TIMEOUT_MS).catch(() => null),
    fetchAccepted(`${base}/skills/models`, secret, SURFACE_TIMEOUT_MS).catch(() => null),
  ]);

  if (manifestRes && (manifestRes.status === 401 || manifestRes.status === 403)) {
    return { ok: false, code: "AIAPI_PROVIDER_KEY_INVALID" };
  }
  if (skillsRes && (skillsRes.status === 401 || skillsRes.status === 403)) {
    return { ok: false, code: "AIAPI_PROVIDER_KEY_INVALID" };
  }

  const manifest = manifestRes && manifestRes.status === 200 ? parseManifest(readJson(manifestRes.text)) : { platform: "", operations: [] };
  let models =
    skillsRes && skillsRes.status === 200 ? parseSurfaceModels(readJson(skillsRes.text)) : [];

  if (!models.length) {
    try {
      const list = await fetchAccepted(`${base}/models`, secret, SURFACE_TIMEOUT_MS);
      if (list.status === 401 || list.status === 403) return { ok: false, code: "AIAPI_PROVIDER_KEY_INVALID" };
      if (list.status !== 200 || !/json/i.test(list.contentType)) {
        return { ok: false, code: "AIAPI_MODELS_NOT_PUBLISHED" };
      }
      models = parseSurfaceModels(readJson(list.text));
    } catch {
      return { ok: false, code: "AIAPI_PROVIDER_UNREACHABLE" };
    }
  }

  if (!models.length) return { ok: false, code: "AIAPI_MODEL_UNAVAILABLE" };

  await attachPricing(base, secret, models);

  const mediaEndpoint =
    manifest.operations.find((operation) => /\/media\/generate$/i.test(operation.path))?.path ?? "";
  const mediaStatus =
    manifest.operations.find((operation) => /\/media\/(status|result|query)$/i.test(operation.path)) ?? null;
  const mediaStatusPath = mediaStatus
    ? `${mediaStatus.path}${/[?]/.test(mediaStatus.path) ? "&" : "?"}task_id=`
    : "";

  const host = (() => {
    try {
      return new URL(base).host;
    } catch {
      return base;
    }
  })();
  // Published endpoint paths are rooted at the host, so profiles store the
  // origin as their base and the full path as their endpoint.
  const origin = (() => {
    try {
      return new URL(base).origin;
    } catch {
      return base;
    }
  })();

  return {
    ok: true,
    surface: {
      baseUrl: origin,
      apiBase: base,
      providerId: providerIdFromHost(host),
      providerName: manifest.platform || host,
      models,
      operations: manifest.operations.filter((operation) => isGenerationOperation(operation.path)),
      mediaEndpoint,
      mediaStatusPath,
    },
  };
}

export interface SurfaceModule {
  moduleId: string;
  title: string;
  capability: string;
  method: string;
  path: string;
  adapterType: string;
  modelId: string;
  docs: string;
  source: "model" | "operation";
  contextWindow: string;
  billing: string;
  description: string;
  inputHint: string;
  outputHint: string;
  restrictions: string;
  tags: string;
}

/**
 * Turns the provider's own catalogue into one module per model, plus the
 * concrete generation endpoints from its manifest.
 */
export function surfaceModules(surface: ProviderSurface): SurfaceModule[] {
  const modules: SurfaceModule[] = [];
  const apiPath = (() => {
    try {
      const path = new URL(surface.apiBase).pathname.replace(/\/+$/, "");
      return path === "/" ? "" : path;
    } catch {
      return "";
    }
  })();
  const absolute = (path: string): string => {
    const value = path.trim();
    if (!value) return "";
    if (/^https?:\/\//i.test(value)) {
      try {
        const url = new URL(value);
        return `${url.pathname}${url.search}`;
      } catch {
        return "";
      }
    }
    if (value.startsWith("/")) return value;
    return `${apiPath}/${value}`;
  };
  for (const model of surface.models) {
    const kind = model.type || (capabilityFromModule(model.id, "") === "operation" ? "chat" : "");
    const capability =
      TYPE_CAPABILITY[kind] ?? (kind === "chat" ? "chat" : capabilityFromModule(`${model.title} ${model.id}`, ""));
    const isChat = capability === "chat" || capability === "correction";
    const chatPath = model.apiEndpoint || `${apiPath}/chat/completions`;
    const path = isChat ? absolute(expandEndpoint(chatPath, model.id)) : absolute(surface.mediaEndpoint);
    if (!path) continue;
    const adapterType = isChat ? adapterForEndpoint(path, model.apiFormat) : "http-json";
    modules.push({
      moduleId: `model-${model.id}`.toLowerCase().replace(/[^a-z0-9-]+/g, "-").slice(0, 60),
      title: model.title,
      capability,
      method: "POST",
      path,
      adapterType,
      modelId: model.id,
      docs: `${surface.apiBase}/skills/models/${encodeURIComponent(model.id)}`,
      source: "model",
      contextWindow: model.contextWindow,
      billing: model.billing,
      description: model.description,
      inputHint: model.inputHint,
      outputHint: isChat
        ? CHAT_OUTPUT[adapterType] ?? ""
        : surface.mediaStatusPath
          ? `建立任務後以 GET ${surface.mediaStatusPath} 查詢結果`
          : "",
      restrictions: "",
      tags: model.tags,
    });
  }

  for (const operation of surface.operations) {
    modules.push({
      moduleId: `op-${operation.title}-${operation.path}`.toLowerCase().replace(/[^a-z0-9-]+/g, "-").slice(0, 60),
      title: operation.title || operation.path,
      capability: capabilityFromModule(operation.title, operation.path),
      method: operation.method,
      path: absolute(operation.path),
      adapterType: "http-json",
      modelId: operation.path,
      docs: `${surface.apiBase}/skills`,
      source: "operation",
      contextWindow: "",
      billing: "",
      description: operation.description,
      inputHint: "",
      outputHint: "",
      restrictions: "",
      tags: "",
    });
  }
  return modules;
}
