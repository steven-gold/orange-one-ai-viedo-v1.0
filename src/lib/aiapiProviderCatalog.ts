import { AIAPI_PROMPT_TEMPLATE_TOKEN } from "./aiapiProfiles";

export type AuthStyle = "bearer" | "anthropic" | "gemini";

export type ModuleKind = "model" | "operation";

export interface ProviderRegistryEntry {
  providerId: string;
  providerName: string;
  adapterType: string;
  baseUrl: string;
  authStyle: AuthStyle;
  /** OpenAI-compatible model list. Empty when the provider does not expose one. */
  modelsPath: string;
  /** Machine-readable documentation index published by the provider itself. */
  docsIndex?: string;
  /** A documented read-only call used only to confirm the key is accepted. */
  verifyPath?: string;
  verifyMethod?: string;
  keyPrefixes: readonly string[];
  docs: string;
}

/**
 * Registry of providers with a published, machine-readable surface. Every URL
 * here is the provider's own documented endpoint or docs index; no endpoint is
 * synthesized from a model name or a user supplied key.
 */
export const AIAPI_PROVIDER_REGISTRY: readonly ProviderRegistryEntry[] = [
  {
    providerId: "openai",
    providerName: "OpenAI",
    adapterType: "openai",
    baseUrl: "https://api.openai.com/v1",
    authStyle: "bearer",
    modelsPath: "/models",
    verifyPath: "/models",
    verifyMethod: "GET",
    keyPrefixes: ["sk-proj-", "sk-svcacct-", "sk-"],
    docs: "https://platform.openai.com/docs",
  },
  {
    providerId: "anthropic",
    providerName: "Anthropic",
    adapterType: "anthropic",
    baseUrl: "https://api.anthropic.com",
    authStyle: "anthropic",
    modelsPath: "/v1/models",
    verifyPath: "/v1/models",
    verifyMethod: "GET",
    keyPrefixes: ["sk-ant-"],
    docs: "https://docs.anthropic.com/en/api",
  },
  {
    providerId: "google",
    providerName: "Google Gemini",
    adapterType: "gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta",
    authStyle: "gemini",
    modelsPath: "/models",
    verifyPath: "/models",
    verifyMethod: "GET",
    keyPrefixes: ["AIza"],
    docs: "https://ai.google.dev/gemini-api/docs",
  },
  {
    providerId: "deepseek",
    providerName: "DeepSeek",
    adapterType: "openai",
    baseUrl: "https://api.deepseek.com/v1",
    authStyle: "bearer",
    modelsPath: "/models",
    verifyPath: "/models",
    verifyMethod: "GET",
    keyPrefixes: ["sk-"],
    docs: "https://api-docs.deepseek.com",
  },
  {
    providerId: "openrouter",
    providerName: "OpenRouter",
    adapterType: "openai",
    baseUrl: "https://openrouter.ai/api/v1",
    authStyle: "bearer",
    modelsPath: "/models",
    // OpenRouter publishes /models publicly, so it cannot prove a key; /key
    // is the authenticated endpoint that answers 401 for a bad key.
    verifyPath: "/key",
    verifyMethod: "GET",
    keyPrefixes: ["sk-or-v1-"],
    docs: "https://openrouter.ai/docs",
  },
  {
    providerId: "groq",
    providerName: "Groq",
    adapterType: "openai",
    baseUrl: "https://api.groq.com/openai/v1",
    authStyle: "bearer",
    modelsPath: "/models",
    verifyPath: "/models",
    verifyMethod: "GET",
    keyPrefixes: ["gsk_"],
    docs: "https://console.groq.com/docs",
  },
  {
    providerId: "xai",
    providerName: "xAI",
    adapterType: "openai",
    baseUrl: "https://api.x.ai/v1",
    authStyle: "bearer",
    modelsPath: "/models",
    verifyPath: "/models",
    verifyMethod: "GET",
    keyPrefixes: ["xai-"],
    docs: "https://docs.x.ai",
  },
  {
    providerId: "mistral",
    providerName: "Mistral AI",
    adapterType: "openai",
    baseUrl: "https://api.mistral.ai/v1",
    authStyle: "bearer",
    modelsPath: "/models",
    verifyPath: "/models",
    verifyMethod: "GET",
    keyPrefixes: [],
    docs: "https://docs.mistral.ai",
  },
  {
    providerId: "together",
    providerName: "Together AI",
    adapterType: "openai",
    baseUrl: "https://api.together.xyz/v1",
    authStyle: "bearer",
    modelsPath: "/models",
    verifyPath: "/models",
    verifyMethod: "GET",
    keyPrefixes: [],
    docs: "https://docs.together.ai",
  },
  {
    providerId: "kling",
    providerName: "Kling AI",
    adapterType: "http-json",
    baseUrl: "https://api-singapore.klingai.com",
    authStyle: "bearer",
    modelsPath: "",
    docsIndex: "https://kling.ai/document-api/llms.txt",
    verifyPath: "/account/costs?start_time={start}&end_time={end}",
    verifyMethod: "GET",
    keyPrefixes: ["api-key-kling-"],
    docs: "https://klingai.com/document-api/",
  },
] as const;

export function registryEntry(providerId: string): ProviderRegistryEntry | null {
  const wanted = providerId.trim().toLowerCase();
  if (!wanted) return null;
  return AIAPI_PROVIDER_REGISTRY.find((entry) => entry.providerId === wanted) ?? null;
}

/** Longest-prefix match. A prefix only narrows the probe order, never the identity. */
export function prefixCandidates(secret: string): ProviderRegistryEntry[] {
  const key = secret.trim();
  if (!key) return [];
  let best = 0;
  let matches: ProviderRegistryEntry[] = [];
  for (const entry of AIAPI_PROVIDER_REGISTRY) {
    for (const prefix of entry.keyPrefixes) {
      if (!key.startsWith(prefix)) continue;
      if (prefix.length > best) {
        best = prefix.length;
        matches = [entry];
      } else if (prefix.length === best && !matches.includes(entry)) {
        matches.push(entry);
      }
    }
  }
  return matches;
}

const NON_CHAT_MODEL =
  /embed|tts|whisper|dall-e|moderation|image|audio|realtime|transcribe|rerank|guard|ocr/i;

export function pickDefaultModel(_entry: ProviderRegistryEntry, models: readonly string[]): string {
  const usable = models.map((model) => model.trim()).filter((model) => model && !NON_CHAT_MODEL.test(model));
  if (!usable.length) return "";
  for (const hint of ["mini", "flash", "haiku", "lite", "small"]) {
    const match = usable.find((model) => model.toLowerCase().includes(hint));
    if (match) return match;
  }
  return usable.sort()[0] ?? "";
}

export function endpointForModel(entry: ProviderRegistryEntry, model: string, capability = "chat"): string {
  if (entry.providerId === "google") {
    return capability === "embedding" ? `/models/${model}:embedContent` : `/models/${model}:generateContent`;
  }
  if (entry.providerId === "anthropic") return "/v1/messages";
  switch (capability) {
    case "embedding":
      return "/embeddings";
    case "moderation":
      return "/moderations";
    case "transcription":
      return "/audio/transcriptions";
    case "audio-generation":
      return "/audio/speech";
    default:
      return "/chat/completions";
  }
}

export function promptTemplateForProvider(): string {
  return AIAPI_PROMPT_TEMPLATE_TOKEN;
}

const MODULE_CAPABILITY_RULES: ReadonlyArray<{ capability: string; pattern: RegExp }> = [
  { capability: "embedding", pattern: /(embed|vector|rerank)/i },
  { capability: "moderation", pattern: /(moderation|guard)/i },
  { capability: "transcription", pattern: /(transcri|whisper|stt)/i },
  { capability: "chat", pattern: /(chat|completion|conversation|messages|responses)/i },
  { capability: "correction", pattern: /(correct|proofread|rewrite|grammar)/i },
  { capability: "text-to-video", pattern: /(text[- ]to[- ]video|t2v|wensheng)/i },
  { capability: "image-to-video", pattern: /(image[- ]to[- ]video|i2v|image2video)/i },
  {
    capability: "video-generation",
    pattern:
      /(video|motion|lip[- ]?sync|avatar|seedance|kling|hailuo|vidu|pixverse|wan\d|happyhorse|sora|veo|grok-video)/i,
  },
  {
    capability: "image-generation",
    pattern:
      /(image|outpaint|upscal|try[- ]on|apparel|goods|commerce|banana|seedream|imagine|midjourney|flux|dall-e)/i,
  },
  { capability: "audio-generation", pattern: /(audio|voice|speech|tts|suno|music|sound)/i },
  { capability: "element-management", pattern: /(element|asset|voice[- ]custom)/i },
  { capability: "billing", pattern: /(billing|balance|account|usage|cost)/i },
];

/** Derives a capability token from the provider's own path and title text. */
export function capabilityFromModule(title: string, path: string): string {
  const haystack = `${title} ${path}`;
  for (const rule of MODULE_CAPABILITY_RULES) {
    if (rule.pattern.test(haystack)) return rule.capability;
  }
  return "operation";
}
