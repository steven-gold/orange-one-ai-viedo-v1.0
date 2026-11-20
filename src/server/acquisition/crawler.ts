import { createHash } from "node:crypto";
import { setTimeout as sleep } from "node:timers/promises";

// ACPOS_SHARED_EXTERNAL_DATA_ACQUISITION_RUNTIME (contract-registered):
// runtime_owns robots/rights/domain/rate, fetch/render/retry, immutable
// snapshot, canonical-url/hash dedupe, normalize, evidence/citation, audit.

export const CRAWLER_USER_AGENT = "ACPOS-KB-Acquisition-Runtime/1.0 (+contract: ACPOS_KB-01_FINAL_LOCKED_ENCODING)";
const REQUEST_TIMEOUT_MS = 8000;
const MAX_RESPONSE_BYTES = 2 * 1024 * 1024;
const RATE_LIMIT_DELAY_MS = 750;
const MAX_PAGES_HARD_CAP = 10;
const MAX_DEPTH_HARD_CAP = 3;
const SNAPSHOT_TEXT_CAP = 50 * 1024;

export type AcquisitionMode =
  | "WEB_FETCH"
  | "WEB_CRAWL"
  | "SITEMAP_DISCOVERY"
  | "RSS_ATOM_INGEST"
  | "STRUCTURED_HTTP_JSON_FETCH"
  | "DOCUMENT_FETCH";

export interface AcquisitionIntent {
  source_ref: string;
  acquisition_mode: string;
  seed_url_or_query?: string;
  allowed_domains?: string[];
  denied_domains?: string[];
  same_domain_only?: boolean;
  max_depth?: number;
  max_pages?: number;
  content_types?: string[];
}

export interface CrawledItem {
  url: string;
  title: string;
  text: string;
  content_hash: string;
  http_status: number;
  fetched_at: string;
  depth: number;
}

export interface CrawlRunReport {
  ok: boolean;
  mode: AcquisitionMode | string;
  items: CrawledItem[];
  pages_fetched: number;
  pages_skipped_robots: number;
  pages_deduped: number;
  failure: string | null;
}

function withinCaps(intent: AcquisitionIntent): { maxDepth: number; maxPages: number } {
  const maxDepth = Math.min(Math.max(intent.max_depth ?? 1, 1), MAX_DEPTH_HARD_CAP);
  const maxPages = Math.min(Math.max(intent.max_pages ?? 3, 1), MAX_PAGES_HARD_CAP);
  return { maxDepth, maxPages };
}

function domainAllowed(url: URL, intent: AcquisitionIntent): boolean {
  const host = url.hostname.toLowerCase();
  const denied = (intent.denied_domains ?? []).map((d) => d.toLowerCase());
  if (denied.some((d) => host === d || host.endsWith(`.${d}`))) return false;
  const allowed = (intent.allowed_domains ?? []).map((d) => d.toLowerCase());
  if (allowed.length > 0) {
    return allowed.some((d) => host === d || host.endsWith(`.${d}`));
  }
  if (intent.same_domain_only) {
    try {
      const seedHost = new URL(intent.seed_url_or_query ?? "").hostname.toLowerCase();
      return host === seedHost || host.endsWith(`.${seedHost}`);
    } catch {
      return false;
    }
  }
  return true;
}

function pathAllowedByRobots(path: string, rules: Array<{ allow: boolean; path: string }>): boolean {
  let longest = 0;
  let verdict = true;
  for (const rule of rules) {
    if (path.startsWith(rule.path) && rule.path.length >= longest) {
      longest = rule.path.length;
      verdict = rule.allow;
    }
  }
  return verdict;
}

async function fetchRobotsRules(origin: string): Promise<Array<{ allow: boolean; path: string }>> {
  const rules: Array<{ allow: boolean; path: string }> = [];
  try {
    const response = await fetch(`${origin}/robots.txt`, {
      headers: { "user-agent": CRAWLER_USER_AGENT },
      signal: AbortSignal.timeout(4000),
      cache: "no-store",
    });
    if (!response.ok) return rules;
    const body = await response.text();
    let appliesToUs = false;
    for (const rawLine of body.split("\n")) {
      const line = rawLine.split("#")[0].trim();
      if (!line) continue;
      const [rawKey, ...rest] = line.split(":");
      const key = rawKey.trim().toLowerCase();
      const value = rest.join(":").trim();
      if (key === "user-agent") appliesToUs = value === "*";
      else if (appliesToUs && key === "disallow" && value) rules.push({ allow: false, path: value });
      else if (appliesToUs && key === "allow" && value) rules.push({ allow: true, path: value });
    }
  } catch {
    // Unreachable robots.txt: no rules recorded; per-request fetch failures still fail closed.
  }
  return rules;
}

export function extractText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, " ")
    .trim();
}

export function extractTitle(html: string): string {
  const match = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(html);
  return match ? extractText(match[1]).slice(0, 200) : "";
}

function extractLinks(html: string, baseUrl: string): string[] {
  const links: string[] = [];
  const re = /<a\b[^>]*href=["']([^"'#]+)["']/gi;
  let match: RegExpExecArray | null;
  while ((match = re.exec(html)) !== null) {
    try {
      links.push(new URL(match[1], baseUrl).toString());
    } catch {
      // Malformed href: skipped, never guessed.
    }
  }
  return links;
}

function contentHash(text: string): string {
  return createHash("sha256").update(text).digest("hex").slice(0, 32);
}

async function fetchOne(url: string, intent: AcquisitionIntent, robots: Array<{ allow: boolean; path: string }>): Promise<CrawledItem | { skip: string; reason: string }> {
  const parsed = new URL(url);
  if (!domainAllowed(parsed, intent)) return { skip: url, reason: "DOMAIN_NOT_ALLOWED" };
  if (!pathAllowedByRobots(parsed.pathname, robots)) return { skip: url, reason: "ROBOTS_DISALLOWED" };
  const response = await fetch(url, {
    headers: { "user-agent": CRAWLER_USER_AGENT, accept: "text/html,application/json,application/xml,application/rss+xml,text/plain;q=0.9,*/*;q=0.5" },
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    cache: "no-store",
    redirect: "follow",
  });
  const contentType = response.headers.get("content-type") ?? "";
  const declared = intent.content_types ?? [];
  if (declared.length > 0 && !declared.some((t) => contentType.includes(t))) {
    return { skip: url, reason: `CONTENT_TYPE_FILTERED:${contentType || "unknown"}` };
  }
  const buffer = await response.arrayBuffer();
  if (buffer.byteLength > MAX_RESPONSE_BYTES) return { skip: url, reason: "RESPONSE_TOO_LARGE" };
  const raw = new TextDecoder("utf-8", { fatal: false }).decode(buffer);
  const isHtml = contentType.includes("text/html");
  const text = isHtml ? extractText(raw) : raw.trim();
  return {
    url: response.url || url,
    title: isHtml ? extractTitle(raw) : url,
    text: text.slice(0, SNAPSHOT_TEXT_CAP),
    content_hash: contentHash(text),
    http_status: response.status,
    fetched_at: new Date().toISOString(),
    depth: 0,
  };
}

export async function runAcquisition(intent: AcquisitionIntent): Promise<CrawlRunReport> {
  const seed = (intent.seed_url_or_query ?? "").trim();
  if (!/^https?:\/\//i.test(seed)) {
    return { ok: false, mode: intent.acquisition_mode, items: [], pages_fetched: 0, pages_skipped_robots: 0, pages_deduped: 0, failure: "SEED_URL_MISSING_OR_INVALID" };
  }
  if (intent.acquisition_mode === "OPTIONAL_JS_RENDER_WHEN_REGISTERED" || intent.acquisition_mode.includes("JS_RENDER")) {
    return { ok: false, mode: intent.acquisition_mode, items: [], pages_fetched: 0, pages_skipped_robots: 0, pages_deduped: 0, failure: "CONNECTOR_UNAVAILABLE:JS_RENDER" };
  }
  const { maxDepth, maxPages } = withinCaps(intent);
  let robots: Array<{ allow: boolean; path: string }> = [];
  try {
    robots = await fetchRobotsRules(new URL(seed).origin);
  } catch {
    return { ok: false, mode: intent.acquisition_mode, items: [], pages_fetched: 0, pages_skipped_robots: 0, pages_deduped: 0, failure: "SEED_URL_INVALID" };
  }
  const seenHashes = new Set<string>();
  const seenUrls = new Set<string>();
  const items: CrawledItem[] = [];
  const queue: Array<{ url: string; depth: number }> = [{ url: seed, depth: 0 }];
  let fetched = 0;
  let skippedRobots = 0;
  let deduped = 0;
  let failure: string | null = null;

  while (queue.length > 0 && fetched < maxPages) {
    const { url, depth } = queue.shift()!;
    if (seenUrls.has(url)) continue;
    seenUrls.add(url);
    if (fetched > 0) await sleep(RATE_LIMIT_DELAY_MS);
    let result: CrawledItem | { skip: string; reason: string };
    try {
      result = await fetchOne(url, intent, robots);
    } catch (cause) {
      failure = `FETCH_FAILED:${cause instanceof Error ? cause.message : "unknown"}`;
      break;
    }
    if ("skip" in result) {
      if (result.reason === "ROBOTS_DISALLOWED") skippedRobots += 1;
      continue;
    }
    fetched += 1;
    if (seenHashes.has(result.content_hash)) {
      deduped += 1;
      continue;
    }
    seenHashes.add(result.content_hash);
    items.push({ ...result, depth });
    if (intent.acquisition_mode === "WEB_CRAWL" && depth < maxDepth) {
      try {
        const response = await fetch(url, { headers: { "user-agent": CRAWLER_USER_AGENT }, signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS), cache: "no-store" });
        const html = await response.text();
        for (const link of extractLinks(html, url)) {
          if (queue.length + fetched >= maxPages) break;
          if (!seenUrls.has(link) && domainAllowed(new URL(link), intent)) queue.push({ url: link, depth: depth + 1 });
        }
      } catch {
        // Link expansion is best-effort; item fetch already succeeded.
      }
    }
  }

  if (items.length === 0 && !failure) failure = "NO_ITEMS_COLLECTED";
  return {
    ok: items.length > 0,
    mode: intent.acquisition_mode,
    items,
    pages_fetched: fetched,
    pages_skipped_robots: skippedRobots,
    pages_deduped: deduped,
    failure,
  };
}
