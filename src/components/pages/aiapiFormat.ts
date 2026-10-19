import type { TranslationKey } from "@/i18n/catalog";
import { displayBoundValue } from "./displayValue";

export function displayAiapiValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}

const ADAPTER_KEYS: Record<string, TranslationKey> = {
  openai: "aiapi.adapter-openai",
  anthropic: "aiapi.adapter-anthropic",
  gemini: "aiapi.adapter-gemini",
  "http-json": "aiapi.adapter-http-json",
};

/** openai here is the published request protocol, not the OpenAI brand. */
export function displayAiapiAdapter(
  value: string | null | undefined,
  t: (key: TranslationKey) => string,
  loading = false,
): string {
  const token = (value ?? "").trim().toLowerCase();
  if (!token) return displayBoundValue(null, loading);
  const key = ADAPTER_KEYS[token];
  return key ? t(key) : displayBoundValue(value, loading);
}

const CAPABILITY_KEYS: Record<string, TranslationKey> = {
  chat: "aiapi.cap-chat",
  correction: "aiapi.cap-correction",
  "video-generation": "aiapi.cap-video-generation",
  "text-to-video": "aiapi.cap-text-to-video",
  "image-to-video": "aiapi.cap-image-to-video",
  "image-generation": "aiapi.cap-image-generation",
  "audio-generation": "aiapi.cap-audio-generation",
  embedding: "aiapi.cap-embedding",
  moderation: "aiapi.cap-moderation",
  transcription: "aiapi.cap-transcription",
  operation: "aiapi.cap-operation",
  "element-management": "aiapi.cap-element-management",
  billing: "aiapi.cap-billing",
};

export function displayAiapiCapability(
  value: string | null | undefined,
  t: (key: TranslationKey) => string,
  loading = false,
): string {
  const parts = (value ?? "")
    .split(/[/,]/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (!parts.length) return displayBoundValue(null, loading);
  return parts
    .map((part) => {
      const key = CAPABILITY_KEYS[part.toLowerCase()];
      return key ? t(key) : part;
    })
    .join("／");
}

export function displayAiapiTimeout(
  value: string | null | undefined,
  t: (key: TranslationKey, params?: Record<string, string | number>) => string,
  loading = false,
): string {
  const token = (value ?? "").trim();
  if (!token) return displayBoundValue(null, loading);
  const seconds = token.replace(/s$/i, "").trim();
  if (!/^\d+(\.\d+)?$/.test(seconds)) return displayBoundValue(value, loading);
  return t("aiapi.timeout-seconds", { seconds });
}

const STATUS_KEYS: Record<string, TranslationKey> = {
  ENABLED: "aiapi.status-enabled",
  DISABLED: "aiapi.status-disabled",
  SET: "aiapi.status-set",
  NOT_SET: "aiapi.status-not-set",
  HEALTHY: "aiapi.status-healthy",
  UNKNOWN: "aiapi.status-unknown",
  PASS: "aiapi.status-pass",
  FAIL: "aiapi.status-fail",
};

export function displayAiapiStatus(
  value: string | null | undefined,
  t: (key: TranslationKey) => string,
  loading = false,
): string {
  const token = (value ?? "").trim();
  if (!token) return displayBoundValue(null, loading);
  const key = STATUS_KEYS[token];
  return key ? t(key) : token;
}
