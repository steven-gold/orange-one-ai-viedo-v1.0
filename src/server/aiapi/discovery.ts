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
