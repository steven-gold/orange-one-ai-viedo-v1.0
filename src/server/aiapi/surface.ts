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

function authHeaders(secret: string): Record<string, string> {
  return { accept: "application/json", authorization: `Bearer ${secret}` };
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
  for (const path of ["/skills/models", "/models"]) {
    try {
      const { status, text, contentType } = await fetchWithTimeout(
        `${trimBase(base)}${path}`,
        { method: "GET", headers: authHeaders(secret) },
        PROBE_TIMEOUT_MS,
      );
      if (status === 401 || status === 403) return "DENIED";
      if (status !== 200) continue;
      if (!/json/i.test(contentType)) continue;
      const rows = modelRows(readJson(text));
      if (!rows.length) continue;
      return { name: "" };
    } catch {
      // try the next candidate
    }
  }
  return null;
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
    const hosts = new Set<string>();
    for (const match of page.text.matchAll(/https:\/\/api\.[a-z0-9-]+(?:\.[a-z0-9-]+)+/gi)) {
      hosts.add(match[0].toLowerCase());
    }
    for (const host of hosts) {
      for (const base of [host, `${host}/v1`]) {
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

export function adapterForEndpoint(path: string, declaredFormat = ""): string {
  const format = declaredFormat.trim().toLowerCase();
  if (format === "gemini" || format === "anthropic" || format === "openai") return format;
  if (/:generateContent/i.test(path) || /\/v1beta\//i.test(path)) return "gemini";
  if (/\/messages(\?|$)/i.test(path)) return "anthropic";
  if (/\/(media|video|image|audio|music)\//i.test(path)) return "http-json";
  return "openai";
}

/**
 * Reads the surface the provider publishes at the resolved base. A JSON model
 * list is mandatory; the manifest and the typed catalogue are used when the
 * provider exposes them.
 */
export async function fetchSurface(baseUrl: string, secret: string): Promise<SurfaceResult> {
  const base = trimBase(baseUrl);
  const [manifestRes, skillsRes] = await Promise.all([
    fetchWithTimeout(`${base}/skills`, { method: "GET", headers: authHeaders(secret) }, SURFACE_TIMEOUT_MS).catch(
      () => null,
    ),
    fetchWithTimeout(`${base}/skills/models`, { method: "GET", headers: authHeaders(secret) }, SURFACE_TIMEOUT_MS).catch(
      () => null,
    ),
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
      const list = await fetchWithTimeout(
        `${base}/models`,
        { method: "GET", headers: authHeaders(secret) },
        SURFACE_TIMEOUT_MS,
      );
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

  const mediaEndpoint =
    manifest.operations.find((operation) => /\/media\/generate$/i.test(operation.path))?.path ?? "";

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
    modules.push({
      moduleId: `model-${model.id}`.toLowerCase().replace(/[^a-z0-9-]+/g, "-").slice(0, 60),
      title: model.title,
      capability,
      method: "POST",
      path,
      adapterType: isChat ? adapterForEndpoint(path, model.apiFormat) : "http-json",
      modelId: model.id,
      docs: `${surface.apiBase}/skills/models/${encodeURIComponent(model.id)}`,
      source: "model",
      contextWindow: model.contextWindow,
      billing: model.billing,
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
    });
  }
  return modules;
}
