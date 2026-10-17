import type { ProviderCatalogEntry } from "@/lib/aiapiProviderCatalog";

export type ModelDiscovery =
  | { ok: true; models: string[] }
  | { ok: false; code: string };

function trimBase(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, "");
}

function authHeaders(entry: ProviderCatalogEntry, secret: string): Record<string, string> {
  if (entry.adapterType === "anthropic") {
    return { "x-api-key": secret, "anthropic-version": "2023-06-01" };
  }
  if (entry.adapterType === "gemini") {
    return { "x-goog-api-key": secret };
  }
  return { authorization: `Bearer ${secret}` };
}

function parseModels(entry: ProviderCatalogEntry, payload: unknown): string[] {
  if (!payload || typeof payload !== "object") return [];
  const record = payload as { data?: unknown; models?: unknown };
  const rows = Array.isArray(record.data) ? record.data : Array.isArray(record.models) ? record.models : [];
  const models: string[] = [];
  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const item = row as {
      id?: unknown;
      name?: unknown;
      supportedGenerationMethods?: unknown;
    };
    const methodList = Array.isArray(item.supportedGenerationMethods) ? item.supportedGenerationMethods : [];
    if (methodList.length && !methodList.includes("generateContent")) continue;
    const raw = typeof item.id === "string" ? item.id : typeof item.name === "string" ? item.name : "";
    const model = raw.trim().replace(/^models\//, "");
    if (model) models.push(model);
  }
  return models;
}

/**
 * Reads the provider's own model list with the supplied key. This is the only
 * source for a default model id, so no model name is ever invented locally.
 */
export async function listProviderModels(
  entry: ProviderCatalogEntry,
  secret: string,
  timeoutMs = 20000,
): Promise<ModelDiscovery> {
  const url = `${trimBase(entry.baseUrl)}${entry.modelsPath}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { accept: "application/json", ...authHeaders(entry, secret) },
      signal: controller.signal,
      cache: "no-store",
    });
    if (response.status === 401 || response.status === 403) {
      return { ok: false, code: "AIAPI_PROVIDER_KEY_INVALID" };
    }
    if (!response.ok) return { ok: false, code: "AIAPI_PROVIDER_HTTP_ERROR" };
    const payload = (await response.json().catch(() => null)) as unknown;
    const models = parseModels(entry, payload);
    if (!models.length) return { ok: false, code: "AIAPI_MODEL_UNAVAILABLE" };
    return { ok: true, models };
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return { ok: false, code: "AIAPI_PROVIDER_TIMEOUT" };
    }
    return { ok: false, code: "AIAPI_PROVIDER_UNREACHABLE" };
  } finally {
    clearTimeout(timer);
  }
}

export type ProviderIdentification =
  | { ok: true; entry: ProviderCatalogEntry; models: string[] }
  | { ok: false; code: string; matches: string[] };

/**
 * Uses the key itself instead of trusting its prefix: every candidate is asked
 * for its own model list and the provider that answers with 200 wins. Only the
 * shortlisted candidates ever see the key, so an ambiguous prefix (e.g. `sk-`)
 * resolves without sending the secret to every registered provider.
 */
export async function identifyProvider(
  candidates: readonly ProviderCatalogEntry[],
  secret: string,
  timeoutMs = 15000,
): Promise<ProviderIdentification> {
  if (!candidates.length) return { ok: false, code: "AIAPI_PROVIDER_UNSUPPORTED", matches: [] };

  const outcomes = await Promise.all(
    candidates.map(async (entry) => ({ entry, result: await listProviderModels(entry, secret, timeoutMs) })),
  );
  const winners = outcomes.filter(
    (outcome): outcome is { entry: ProviderCatalogEntry; result: { ok: true; models: string[] } } => outcome.result.ok,
  );

  if (winners.length === 1) return { ok: true, entry: winners[0].entry, models: winners[0].result.models };
  if (winners.length > 1) {
    return { ok: false, code: "AIAPI_PROVIDER_AMBIGUOUS", matches: winners.map((winner) => winner.entry.providerId) };
  }

  const codes = outcomes.map((outcome) => (outcome.result.ok ? "" : outcome.result.code));
  if (codes.includes("AIAPI_PROVIDER_KEY_INVALID")) return { ok: false, code: "AIAPI_PROVIDER_KEY_INVALID", matches: [] };
  if (codes.every((code) => code === "AIAPI_PROVIDER_UNREACHABLE" || code === "AIAPI_PROVIDER_TIMEOUT")) {
    return { ok: false, code: "AIAPI_PROVIDER_UNREACHABLE", matches: [] };
  }
  return { ok: false, code: codes.find(Boolean) ?? "AIAPI_PROVIDER_HTTP_ERROR", matches: [] };
}
