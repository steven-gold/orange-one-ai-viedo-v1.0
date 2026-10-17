import { AIAPI_PROMPT_TEMPLATE_TOKEN } from "./aiapiProfiles";

export type ProviderAdapterType = "openai" | "anthropic" | "gemini";

export interface ProviderCatalogEntry {
  providerId: string;
  providerName: string;
  adapterType: ProviderAdapterType;
  baseUrl: string;
  endpointTemplate: string;
  modelsPath: string;
  responseTextPath: string;
  timeoutSeconds: string;
  docs: string;
  keyPrefixes: readonly string[];
  preferredModels: readonly string[];
}

/**
 * Registered provider endpoints. Every value below is the provider's published
 * API surface; nothing here is derived from a user supplied key. Keys are only
 * matched to an entry by prefix so the browser never invents a provider alias.
 */
export const AIAPI_PROVIDER_CATALOG: readonly ProviderCatalogEntry[] = [
  {
    providerId: "openai",
    providerName: "OpenAI",
    adapterType: "openai",
    baseUrl: "https://api.openai.com/v1",
    endpointTemplate: "/chat/completions",
    modelsPath: "/models",
    responseTextPath: "choices[0].message.content",
    timeoutSeconds: "30",
    docs: "https://platform.openai.com/docs",
    keyPrefixes: ["sk-proj-", "sk-svcacct-", "sk-"],
    preferredModels: ["gpt-4.1-mini", "gpt-4o-mini", "gpt-4.1", "gpt-4o"],
  },
  {
    providerId: "anthropic",
    providerName: "Anthropic",
    adapterType: "anthropic",
    baseUrl: "https://api.anthropic.com",
    endpointTemplate: "/v1/messages",
    modelsPath: "/v1/models",
    responseTextPath: "content[0].text",
    timeoutSeconds: "30",
    docs: "https://docs.anthropic.com/en/api",
    keyPrefixes: ["sk-ant-"],
    preferredModels: ["claude-sonnet-4", "claude-3-7-sonnet", "claude-3-5-sonnet", "claude-3-5-haiku"],
  },
  {
    providerId: "google",
    providerName: "Google Gemini",
    adapterType: "gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta",
    endpointTemplate: "/models/{model}:generateContent",
    modelsPath: "/models",
    responseTextPath: "candidates[0].content.parts[0].text",
    timeoutSeconds: "30",
    docs: "https://ai.google.dev/gemini-api/docs",
    keyPrefixes: ["AIza"],
    preferredModels: ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash"],
  },
  {
    providerId: "deepseek",
    providerName: "DeepSeek",
    adapterType: "openai",
    baseUrl: "https://api.deepseek.com/v1",
    endpointTemplate: "/chat/completions",
    modelsPath: "/models",
    responseTextPath: "choices[0].message.content",
    timeoutSeconds: "30",
    docs: "https://api-docs.deepseek.com",
    keyPrefixes: ["sk-"],
    preferredModels: ["deepseek-chat", "deepseek-reasoner"],
  },
  {
    providerId: "openrouter",
    providerName: "OpenRouter",
    adapterType: "openai",
    baseUrl: "https://openrouter.ai/api/v1",
    endpointTemplate: "/chat/completions",
    modelsPath: "/models",
    responseTextPath: "choices[0].message.content",
    timeoutSeconds: "30",
    docs: "https://openrouter.ai/docs",
    keyPrefixes: ["sk-or-v1-"],
    preferredModels: ["gpt-4o-mini", "claude-3.5-sonnet"],
  },
  {
    providerId: "groq",
    providerName: "Groq",
    adapterType: "openai",
    baseUrl: "https://api.groq.com/openai/v1",
    endpointTemplate: "/chat/completions",
    modelsPath: "/models",
    responseTextPath: "choices[0].message.content",
    timeoutSeconds: "30",
    docs: "https://console.groq.com/docs",
    keyPrefixes: ["gsk_"],
    preferredModels: ["llama-3.3-70b", "llama-3.1-8b"],
  },
  {
    providerId: "xai",
    providerName: "xAI",
    adapterType: "openai",
    baseUrl: "https://api.x.ai/v1",
    endpointTemplate: "/chat/completions",
    modelsPath: "/models",
    responseTextPath: "choices[0].message.content",
    timeoutSeconds: "30",
    docs: "https://docs.x.ai",
    keyPrefixes: ["xai-"],
    preferredModels: ["grok-2", "grok-beta"],
  },
  {
    providerId: "mistral",
    providerName: "Mistral AI",
    adapterType: "openai",
    baseUrl: "https://api.mistral.ai/v1",
    endpointTemplate: "/chat/completions",
    modelsPath: "/models",
    responseTextPath: "choices[0].message.content",
    timeoutSeconds: "30",
    docs: "https://docs.mistral.ai",
    keyPrefixes: [],
    preferredModels: ["mistral-small-latest", "mistral-large-latest"],
  },
  {
    providerId: "together",
    providerName: "Together AI",
    adapterType: "openai",
    baseUrl: "https://api.together.xyz/v1",
    endpointTemplate: "/chat/completions",
    modelsPath: "/models",
    responseTextPath: "choices[0].message.content",
    timeoutSeconds: "30",
    docs: "https://docs.together.ai",
    keyPrefixes: [],
    preferredModels: ["llama-3.3-70b"],
  },
] as const;

export const AIAPI_DETECTABLE_PROVIDERS = AIAPI_PROVIDER_CATALOG.filter(
  (entry) => entry.keyPrefixes.length > 0,
);

export function catalogEntry(providerId: string): ProviderCatalogEntry | null {
  const wanted = providerId.trim().toLowerCase();
  if (!wanted) return null;
  return AIAPI_PROVIDER_CATALOG.find((entry) => entry.providerId === wanted) ?? null;
}

/** Deterministic prefix match. Longest prefix wins so `sk-or-v1-` beats `sk-`. */
export function detectProviders(secret: string): ProviderCatalogEntry[] {
  const key = secret.trim();
  if (!key) return [];
  let best = 0;
  const matches: ProviderCatalogEntry[] = [];
  for (const entry of AIAPI_DETECTABLE_PROVIDERS) {
    for (const prefix of entry.keyPrefixes) {
      if (!key.startsWith(prefix)) continue;
      if (prefix.length > best) {
        best = prefix.length;
        matches.length = 0;
        matches.push(entry);
      } else if (prefix.length === best && !matches.includes(entry)) {
        matches.push(entry);
      }
    }
  }
  return matches;
}

const NON_CHAT_MODEL = /embed|tts|whisper|dall-e|moderation|image|audio|realtime|transcribe|rerank|guard|ocr|vision-only/i;

export function pickDefaultModel(entry: ProviderCatalogEntry, models: readonly string[]): string {
  const usable = models.map((model) => model.trim()).filter((model) => model && !NON_CHAT_MODEL.test(model));
  if (!usable.length) return "";
  for (const preferred of entry.preferredModels) {
    const exact = usable.find((model) => model === preferred);
    if (exact) return exact;
    const partial = usable.find((model) => model.startsWith(preferred));
    if (partial) return partial;
  }
  for (const hint of ["mini", "flash", "haiku", "lite", "small"]) {
    const match = usable.find((model) => model.toLowerCase().includes(hint));
    if (match) return match;
  }
  return usable.sort()[0] ?? "";
}

export function endpointForModel(entry: ProviderCatalogEntry, model: string): string {
  return entry.endpointTemplate.split("{model}").join(model);
}

export function promptTemplateForProvider(): string {
  return AIAPI_PROMPT_TEMPLATE_TOKEN;
}
