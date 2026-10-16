import type { TranslationKey } from "@/i18n/catalog";
import { displayBoundValue } from "./displayValue";

export function displayAiapiValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
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
