import { createHmac } from "node:crypto";
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
  description: string;
  inputHint: string;
  outputHint: string;
  restrictions: string;
  tags: string;
}

export type ProviderDiscovery =
  | { ok: true; entry: ProviderRegistryEntry; baseUrl: string; modules: DiscoveredModule[] }
  | { ok: false; code: string; matches: string[] };

/** The host and header scheme that actually accepted the key. */
export interface VerifiedSurface {
  baseUrl: string;
  headers: Record<string, string>;
}

const MODULE_LIMIT = 200;
const PAGE_LIMIT = 60;
const VERIFY_TIMEOUT_MS = 5000;
const PAGE_TIMEOUT_MS = 9000;
const CONCURRENCY = 4;

function trimBase(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, "");
}

/**
 * Kling's legacy credentials are an AccessKey/SecretKey pair that must be
 * signed into a short-lived HS256 JWT. New Kling API keys are already a Bearer
 * token, so a plain key is passed through unchanged.
 */
function signKlingToken(pair: string): string {
  const match = /^([^:\s]{6,}):(\S{6,})$/.exec(pair.trim());
  if (!match) return "";
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const now = Math.floor(Date.now() / 1000);
  const head = encode({ alg: "HS256", typ: "JWT" });
  const body = encode({ iss: match[1], exp: now + 1800, nbf: now - 5 });
  const signature = createHmac("sha256", match[2]).update(`${head}.${body}`).digest("base64url");
  return `${head}.${body}.${signature}`;
}

export function klingCredential(secret: string): string {
  return signKlingToken(secret) || secret;
}

function credentialFor(entry: ProviderRegistryEntry, secret: string): string {
  return entry.providerId === "kling" ? klingCredential(secret) : secret;
}

function headersForStyle(style: string, entry: ProviderRegistryEntry, secret: string): Record<string, string> {
  const credential = credentialFor(entry, secret);
  switch (style) {
    case "anthropic":
      return { "x-api-key": credential, "anthropic-version": "2023-06-01" };
    case "gemini":
      return { "x-goog-api-key": credential };
    case "x-api-key":
      return { "x-api-key": credential };
    case "api-key":
      return { "api-key": credential };
    case "raw":
      return { authorization: credential };
    default:
      return { authorization: `Bearer ${credential}` };
  }
}

/**
 * Providers disagree about how a key is carried. The declared style is tried
 * first, then the documented alternatives, so an unfamiliar key is discovered
 * instead of being rejected because the brand guess was wrong.
 */
export function authHeaderVariants(entry: ProviderRegistryEntry, secret: string): Record<string, string>[] {
  const styles = [entry.authStyle, ...(entry.authStyles ?? []), "bearer", "x-api-key", "api-key", "raw"];
  const seen = new Set<string>();
  const variants: Record<string, string>[] = [];
  for (const style of styles) {
    const headers = headersForStyle(style, entry, secret);
    const fingerprint = JSON.stringify(headers);
    if (seen.has(fingerprint)) continue;
    seen.add(fingerprint);
    variants.push(headers);
  }
  return variants;
}

function authHeaders(entry: ProviderRegistryEntry, secret: string): Record<string, string> {
  return authHeaderVariants(entry, secret)[0];
}

/** Every published host for a provider, primary first. */
export function baseVariants(entry: ProviderRegistryEntry): string[] {
  return Array.from(new Set([entry.baseUrl, ...(entry.baseUrls ?? [])].map((base) => trimBase(base))));
}

function verifyUrl(entry: ProviderRegistryEntry, baseUrl = entry.baseUrl): string {
  const now = Date.now();
  const filled = (entry.verifyPath ?? "")
    .replace(/\{start\}/g, String(now - 30 * 24 * 3600 * 1000))
    .replace(/\{end\}/g, String(now));
  return `${trimBase(baseUrl)}${filled}`;
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
  verified?: VerifiedSurface,
): Promise<ModelDiscovery> {
  if (!entry.modelsPath) return { ok: false, code: "AIAPI_MODELS_NOT_PUBLISHED" };
  const bases = verified ? [verified.baseUrl] : baseVariants(entry);
  const headerVariants = verified ? [verified.headers] : authHeaderVariants(entry, secret);
  let denied = false;
  for (const base of bases) {
    for (const headers of headerVariants) {
      const url = `${trimBase(base)}${entry.modelsPath}`;
      try {
        const { status, text } = await fetchWithTimeout(
          url,
          { method: "GET", headers: { accept: "application/json", ...headers } },
          timeoutMs,
        );
        if (status === 401 || status === 403) {
          denied = true;
          continue;
        }
        if (!status.toString().startsWith("2")) continue;
        const models = parseModels(parseJson(text));
        if (!models.length) continue;
        return { ok: true, models };
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") continue;
        continue;
      }
    }
  }
  return { ok: false, code: denied ? "AIAPI_PROVIDER_KEY_INVALID" : "AIAPI_PROVIDER_HTTP_ERROR" };
}

/**
 * Confirms the key against a documented read-only call. The declared host and
 * header style are tried first, then every other published host and scheme,
 * so a key from a different region or client is discovered instead of being
 * rejected because the initial guess did not match.
 */
export async function verifyKeyAt(entry: ProviderRegistryEntry, secret: string): Promise<VerifiedSurface | null> {
  const headers = authHeaderVariants(entry, secret);
  if (!entry.verifyPath) {
    return { baseUrl: entry.baseUrl, headers: headers[0] };
  }
  const method = (entry.verifyMethod ?? "GET").toUpperCase();
  // Every published host and scheme is attempted at once. A ladder of guesses
  // run in sequence turns one unresponsive host into a minute of waiting, and
  // the first answer that actually proves the key is all we need.
  const attempt = async (baseUrl: string, header: Record<string, string>): Promise<VerifiedSurface> => {
    const init: RequestInit = {
      method,
      headers: { accept: "application/json", "content-type": "application/json", ...header },
    };
    if (method !== "GET") init.body = "{}";
    const { status } = await fetchWithTimeout(verifyUrl(entry, baseUrl), init, VERIFY_TIMEOUT_MS);
    // Only a 2xx from the authenticated call proves the key; a 404 or 5xx on a
    // misconfigured path must never be mistaken for acceptance.
    if (status >= 200 && status < 300) return { baseUrl, headers: header };
    throw new Error("rejected");
  };
  const tasks = baseVariants(entry).flatMap((baseUrl) => headers.map((header) => attempt(baseUrl, header)));
  try {
    return await Promise.any(tasks);
  } catch {
    return null;
  }
}

export async function verifyKey(entry: ProviderRegistryEntry, secret: string): Promise<boolean> {
  return (await verifyKeyAt(entry, secret)) !== null;
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
 * Providers put the human description of an operation in a "Description"
 * blockquote. Reading only that keeps table rows and schema noise out.
 */
function docDescription(markdown: string): string {
  const sections = markdown.split(/^#{2,4}\s+/m);
  const section = sections.find((part) => /^Description\b/i.test(part));
  const scope = section ? section.replace(/^Description[^\n]*\n/, "") : markdown.slice(0, 1200);
  for (const line of scope.split("\n")) {
    const quoted = /^>\s*(.+)$/.exec(line.trim());
    if (!quoted) continue;
    const text = quoted[1].replace(/^Note:\s*/i, "").trim();
    if (text.length >= 20) return text.slice(0, 400);
  }
  return "";
}

/** Required parameter names from the documented request tables. */
function docInputHint(markdown: string): string {
  const sections = markdown.split(/^#{2,4}\s+/m);
  const parts: string[] = [];
  for (const section of sections) {
    const name = /^(Body|Query|Path) Params\b/i.exec(section)?.[1];
    if (!name) continue;
    const required: string[] = [];
    for (const line of section.split("\n")) {
      const cells = line.split("|").map((cell) => cell.trim());
      if (cells.length < 5) continue;
      const field = /^`([^`]+)`$/.exec(cells[1])?.[1];
      const isRequired = /^yes$/i.test(cells[3] ?? "");
      if (field && isRequired) required.push(field);
    }
    if (required.length) parts.push(`${name}: ${required.join(", ")}`);
  }
  return parts.join(" · ").slice(0, 300);
}

/**
 * One documented page can describe several calls (create, query, list), so
 * every Method/Path pair on the page becomes its own module.
 */
export function parseDocPage(markdown: string, title: string): DocOperation[] {
  const heading = /^#\s+(.+)$/m.exec(markdown)?.[1]?.trim() ?? title;
  const description = docDescription(markdown);
  const inputHint = docInputHint(markdown);
  const operations: DocOperation[] = [];
  const seen = new Set<string>();
  const pair = /Method:\s*`(GET|POST|PUT|PATCH|DELETE)`[\s\S]{0,160}?Path:\s*`(\/[^`\s]*)`/gi;
  for (const match of markdown.matchAll(pair)) {
    const method = match[1].toUpperCase();
    const path = match[2];
    const key = `${method} ${path}`;
    if (seen.has(key)) continue;
    seen.add(key);
    operations.push({
      title: heading,
      method,
      path,
      docs: "",
      contextWindow: "",
      billing: "",
      description,
      inputHint,
      outputHint: "",
      restrictions: "",
      tags: "",
    });
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

async function discoverFromModels(
  entry: ProviderRegistryEntry,
  secret: string,
  verified?: VerifiedSurface,
): Promise<DiscoveredModule[]> {
  const discovery = await listProviderModels(entry, secret, PAGE_TIMEOUT_MS, verified);
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
      description: "",
      inputHint: "",
      outputHint: "",
      restrictions: "",
      tags: "",
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
      description: page.description,
      inputHint: page.inputHint,
      outputHint: page.outputHint,
      restrictions: page.restrictions,
      tags: page.tags,
    });
    if (modules.length >= MODULE_LIMIT) break;
  }
  return modules;
}

async function discoverEntry(
  entry: ProviderRegistryEntry,
  secret: string,
): Promise<{ modules: DiscoveredModule[]; baseUrl: string } | null> {
  // Prove the key before spending time on the documentation index: an
  // unaccepted key must not trigger a sixty-page crawl.
  const verified = await verifyKeyAt(entry, secret);
  if (!verified) return null;
  const [fromModels, fromDocs] = await Promise.all([
    discoverFromModels(entry, secret, verified),
    discoverFromDocs(entry),
  ]);
  const modules = [...fromModels, ...fromDocs];
  if (!modules.length) return null;
  return { modules, baseUrl: verified.baseUrl };
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
  const results = await mapLimit(ordered, 3, async (entry) => ({ entry, found: await discoverEntry(entry, secret) }));
  const winners = results.filter(
    (result): result is { entry: ProviderRegistryEntry; found: { modules: DiscoveredModule[]; baseUrl: string } } =>
      result.found !== null,
  );
  if (winners.length === 1) {
    return {
      ok: true,
      entry: winners[0].entry,
      baseUrl: winners[0].found.baseUrl,
      modules: winners[0].found.modules,
    };
  }
  if (winners.length > 1) {
    return { ok: false, code: "AIAPI_PROVIDER_AMBIGUOUS", matches: winners.map((winner) => winner.entry.providerId) };
  }

  if (entries.length && probeAll.length) {
    const remaining = probeAll.filter((candidate) => !entries.some((entry) => entry.providerId === candidate.providerId));
    if (remaining.length) {
      const fallback = await mapLimit(remaining, 3, async (entry) => ({ entry, found: await discoverEntry(entry, secret) }));
      const hits = fallback.filter(
        (result): result is { entry: ProviderRegistryEntry; found: { modules: DiscoveredModule[]; baseUrl: string } } =>
          result.found !== null,
      );
      if (hits.length === 1) {
        return {
          ok: true,
          entry: hits[0].entry,
          baseUrl: hits[0].found.baseUrl,
          modules: hits[0].found.modules,
        };
      }
      if (hits.length > 1) return { ok: false, code: "AIAPI_PROVIDER_AMBIGUOUS", matches: hits.map((hit) => hit.entry.providerId) };
    }
  }

  return { ok: false, code: "AIAPI_PROVIDER_KEY_INVALID", matches: [] };
}
