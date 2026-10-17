import type { ProviderRegistryEntry } from "@/lib/aiapiProviderCatalog";
import { capabilityFromModule, endpointForModel } from "@/lib/aiapiProviderCatalog";

export interface ProviderModel {
  id: string;
  contextWindow?: string;
  billing?: string;
}

export type ModelDiscovery =
  | { ok: true; models: ProviderModel[] }
  | { ok: false; code: string };

export interface DiscoveredModule {
  moduleId: string;
  title: string;
  capability: string;
  method: string;
  path: string;
  docs: string;
  source: "model" | "operation";
  contextWindow: string;
  billing: string;
}

export type ProviderDiscovery =
  | { ok: true; entry: ProviderRegistryEntry; modules: DiscoveredModule[] }
  | { ok: false; code: string; matches: string[] };

const MODULE_LIMIT = 200;
const PAGE_LIMIT = 60;
const PAGE_TIMEOUT_MS = 9000;
const CONCURRENCY = 4;

function trimBase(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, "");
}

function authHeaders(entry: ProviderRegistryEntry, secret: string): Record<string, string> {
  if (entry.authStyle === "anthropic") {
    return { "x-api-key": secret, "anthropic-version": "2023-06-01" };
  }
  if (entry.authStyle === "gemini") return { "x-goog-api-key": secret };
  return { authorization: `Bearer ${secret}` };
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<{ status: number; text: string }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal, cache: "no-store" });
    const text = await response.text().catch(() => "");
    return { status: response.status, text };
  } finally {
    clearTimeout(timer);
  }
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

export function parseModels(payload: unknown): ProviderModel[] {
  if (!payload || typeof payload !== "object") return [];
  const record = payload as { data?: unknown; models?: unknown };
  const rows = Array.isArray(record.data) ? record.data : Array.isArray(record.models) ? record.models : [];
  const models: ProviderModel[] = [];
  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const item = row as {
      id?: unknown;
      name?: unknown;
      supportedGenerationMethods?: unknown;
      context_length?: unknown;
      context_window?: unknown;
      max_context_length?: unknown;
      pricing?: { prompt?: unknown; completion?: unknown };
    };
    const methods = Array.isArray(item.supportedGenerationMethods) ? item.supportedGenerationMethods : [];
    if (methods.length && !methods.includes("generateContent")) continue;
    const raw = typeof item.id === "string" ? item.id : typeof item.name === "string" ? item.name : "";
    const id = raw.trim().replace(/^models\//, "");
    if (!id) continue;
    const context = item.context_length ?? item.context_window ?? item.max_context_length;
    const prompt = item.pricing?.prompt;
    models.push({
      id,
      contextWindow: typeof context === "number" ? String(context) : "",
      billing: typeof prompt === "string" && prompt !== "0" ? `prompt ${prompt} / completion ${String(item.pricing?.completion ?? "")}` : "",
    });
  }
  return models;
}

/**
 * Reads the provider's own model list with the supplied key. This is the only
 * source for model ids, context windows and pricing.
 */
export async function listProviderModels(
  entry: ProviderRegistryEntry,
  secret: string,
  timeoutMs = PAGE_TIMEOUT_MS,
): Promise<ModelDiscovery> {
  if (!entry.modelsPath) return { ok: false, code: "AIAPI_MODELS_NOT_PUBLISHED" };
  const url = `${trimBase(entry.baseUrl)}${entry.modelsPath}`;
  try {
    const { status, text } = await fetchWithTimeout(
      url,
      { method: "GET", headers: { accept: "application/json", ...authHeaders(entry, secret) } },
      timeoutMs,
    );
    if (status === 401 || status === 403) return { ok: false, code: "AIAPI_PROVIDER_KEY_INVALID" };
    if (!status.toString().startsWith("2")) return { ok: false, code: "AIAPI_PROVIDER_HTTP_ERROR" };
    const models = parseModels(parseJson(text));
    if (!models.length) return { ok: false, code: "AIAPI_MODEL_UNAVAILABLE" };
    return { ok: true, models };
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") return { ok: false, code: "AIAPI_PROVIDER_TIMEOUT" };
    return { ok: false, code: "AIAPI_PROVIDER_UNREACHABLE" };
  }
}

/** Confirms the key against one documented read-only call. */
export async function verifyKey(entry: ProviderRegistryEntry, secret: string): Promise<boolean> {
  if (!entry.verifyPath) return true;
  const url = `${trimBase(entry.baseUrl)}${entry.verifyPath}`;
  const method = (entry.verifyMethod ?? "GET").toUpperCase();
  const init: RequestInit = {
    method,
    headers: { accept: "application/json", "content-type": "application/json", ...authHeaders(entry, secret) },
  };
  if (method !== "GET") init.body = "{}";
  try {
    const { status } = await fetchWithTimeout(url, init, PAGE_TIMEOUT_MS);
    // Only a 2xx from the authenticated call proves the key; a 404 or 5xx on a
    // misconfigured path must never be mistaken for acceptance.
    return status >= 200 && status < 300;
  } catch {
    return false;
  }
}

interface DocLink {
  title: string;
  url: string;
}

export function parseDocsIndex(markdown: string): DocLink[] {
  const links: DocLink[] = [];
  for (const line of markdown.split("\n")) {
    const match = /^\s*-\s*\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/.exec(line);
    if (!match) continue;
    const url = match[2];
    if (!/\.md($|\?)/.test(url)) continue;
    links.push({ title: match[1].replace(/\s+/g, " ").trim(), url });
  }
  return links;
}

export type DocOperation = Omit<DiscoveredModule, "moduleId" | "capability" | "source">;

/**
 * One documented page can describe several calls (create, query, list), so
 * every Method/Path pair on the page becomes its own module.
 */
export function parseDocPage(markdown: string, title: string): DocOperation[] {
  const heading = /^#\s+(.+)$/m.exec(markdown)?.[1]?.trim() ?? title;
  const operations: DocOperation[] = [];
  const seen = new Set<string>();
  const pair = /Method:\s*`(GET|POST|PUT|PATCH|DELETE)`[\s\S]{0,160}?Path:\s*`(\/[^`\s]*)`/gi;
  for (const match of markdown.matchAll(pair)) {
    const method = match[1].toUpperCase();
    const path = match[2];
    const key = `${method} ${path}`;
    if (seen.has(key)) continue;
    seen.add(key);
    operations.push({ title: heading, method, path, docs: "", contextWindow: "", billing: "" });
  }
  return operations;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

async function mapLimit<T, R>(items: readonly T[], limit: number, worker: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let cursor = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor++;
      results[index] = await worker(items[index]);
    }
  });
  await Promise.all(runners);
  return results;
}

async function discoverFromModels(entry: ProviderRegistryEntry, secret: string): Promise<DiscoveredModule[]> {
  const discovery = await listProviderModels(entry, secret);
  if (!discovery.ok) return [];
  return discovery.models.slice(0, MODULE_LIMIT).map((model) => {
    // A model-list entry is a text model unless its own name marks another
    // modality, so embeddings/audio never land in the chat lane.
    const derived = capabilityFromModule(model.id, "");
    const capability = derived === "operation" ? "chat" : derived;
    const id = slugify(model.id) || "model";
    return {
      moduleId: id,
      title: model.id,
      capability,
      method: "POST",
      path: endpointForModel(entry, model.id, capability),
      docs: entry.docs,
      source: "model" as const,
      contextWindow: model.contextWindow ?? "",
      billing: model.billing ?? "",
    };
  });
}

async function discoverFromDocs(entry: ProviderRegistryEntry): Promise<DiscoveredModule[]> {
  if (!entry.docsIndex) return [];
  let index: string;
  try {
    const { status, text } = await fetchWithTimeout(entry.docsIndex, { method: "GET" }, PAGE_TIMEOUT_MS);
    if (status !== 200) return [];
    index = text;
  } catch {
    return [];
  }
  const links = parseDocsIndex(index).slice(0, PAGE_LIMIT);
  const pages = await mapLimit(links, CONCURRENCY, async (link) => {
    // Providers rate limit or reset connections under parallel scraping; one
    // retry keeps a slow page from silently dropping its modules.
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const { status, text } = await fetchWithTimeout(link.url, { method: "GET" }, PAGE_TIMEOUT_MS);
        if (status === 200) {
          return parseDocPage(text, link.title).map((operation) => ({ ...operation, link }));
        }
        if (status < 500) return [];
      } catch {
        // retry once, then give up on this page
      }
    }
    return [];
  });

  const seen = new Set<string>();
  const modules: DiscoveredModule[] = [];
  for (const page of pages.flat()) {
    const key = `${page.method} ${page.path}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const capability = capabilityFromModule(page.title, page.path);
    const moduleId = slugify(`${page.title}-${page.path}`) || `module-${modules.length + 1}`;
    modules.push({
      moduleId,
      title: page.title,
      capability,
      method: page.method,
      path: page.path,
      docs: page.link.url,
      source: "operation",
      contextWindow: "",
      billing: "",
    });
    if (modules.length >= MODULE_LIMIT) break;
  }
  return modules;
}

async function discoverEntry(entry: ProviderRegistryEntry, secret: string): Promise<DiscoveredModule[] | null> {
  const [fromModels, fromDocs] = await Promise.all([discoverFromModels(entry, secret), discoverFromDocs(entry)]);
  const modules = [...fromModels, ...fromDocs];
  if (!modules.length) return null;
  const accepted = await verifyKey(entry, secret);
  return accepted ? modules : null;
}

/**
 * Resolves the provider that accepts this key and returns every module it
 * publishes. Prefixes only decide probe order; an unrecognised prefix falls
 * back to the whole registry so no brand is hardcoded into the key format.
 */
export async function identifyProvider(
  secret: string,
  entries: readonly ProviderRegistryEntry[],
  probeAll: readonly ProviderRegistryEntry[],
): Promise<ProviderDiscovery> {
  const ordered = [...entries];
  const results = await mapLimit(ordered, 3, async (entry) => ({ entry, modules: await discoverEntry(entry, secret) }));
  const winners = results.filter(
    (result): result is { entry: ProviderRegistryEntry; modules: DiscoveredModule[] } => result.modules !== null,
  );
  if (winners.length === 1) return { ok: true, entry: winners[0].entry, modules: winners[0].modules };
  if (winners.length > 1) {
    return { ok: false, code: "AIAPI_PROVIDER_AMBIGUOUS", matches: winners.map((winner) => winner.entry.providerId) };
  }

  if (entries.length && probeAll.length) {
    const remaining = probeAll.filter((candidate) => !entries.some((entry) => entry.providerId === candidate.providerId));
    if (remaining.length) {
      const fallback = await mapLimit(remaining, 3, async (entry) => ({ entry, modules: await discoverEntry(entry, secret) }));
      const hits = fallback.filter(
        (result): result is { entry: ProviderRegistryEntry; modules: DiscoveredModule[] } => result.modules !== null,
      );
      if (hits.length === 1) return { ok: true, entry: hits[0].entry, modules: hits[0].modules };
      if (hits.length > 1) return { ok: false, code: "AIAPI_PROVIDER_AMBIGUOUS", matches: hits.map((hit) => hit.entry.providerId) };
    }
  }

  return { ok: false, code: "AIAPI_PROVIDER_KEY_INVALID", matches: [] };
}
