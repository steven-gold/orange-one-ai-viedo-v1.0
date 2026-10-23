import { diagnoseGenerationFailure } from "./conversationTask";

export const AI_UNAVAILABLE_ZH = "目前無法取得 AI 回應（供應商未設定或暫時無法使用）。";

const UNAVAILABLE_BY_REASON: Record<string, string> = {
  "供應商未設定或暫時無法使用": AI_UNAVAILABLE_ZH,
  "供應商逾時": "目前無法取得 AI 回應（供應商逾時）。",
  "Multi 路由未滿 3 條": "目前無法取得 AI 回應（Multi 路由未滿 3 條）。",
  "供應商無法連線": "目前無法取得 AI 回應（供應商無法連線）。",
  "空回應": "目前無法取得 AI 回應（空回應）。",
  "輸出無法使用": "目前無法取得 AI 回應（輸出無法使用）。",
  "偵測到重複循環": "目前無法取得 AI 回應（偵測到重複循環）。",
  "輸出被截斷": "目前無法取得 AI 回應（輸出被截斷）。",
  "生成失敗": "目前無法取得 AI 回應（生成失敗）。",
};

export function unavailableFromReason(reason: string): string {
  const key = reason.trim();
  if (!key) return AI_UNAVAILABLE_ZH;
  return UNAVAILABLE_BY_REASON[key] ?? `目前無法取得 AI 回應（${key}）。`;
}

export function unavailableBody(input: {
  failed?: boolean;
  empty?: boolean;
  loop?: boolean;
  truncated?: boolean;
  providerCode?: string;
}): string {
  return unavailableFromReason(diagnoseGenerationFailure(input));
}

export function isAiUnavailable(value: unknown): boolean {
  return typeof value === "string" && /^目前無法取得 AI 回應（.+）。?$/u.test(value.trim());
}

export function displayAiReply(text: string, genericUnavailable: string): string {
  const body = text.trim();
  if (body === AI_UNAVAILABLE_ZH || body === AI_UNAVAILABLE_ZH.replace(/。$/u, "")) return genericUnavailable;
  return text;
}

export const ASSET_CORRECTION_RESPONSE_UID = "ASSET-01-FLD-CORRECTION-RESPONSE";
export const VIDEO_CORRECTION_RESPONSE_UID = "VIDEO-01-FLD-CORRECTION-RESPONSE";
export const EDIT_CORRECTION_CANDIDATE_UID = "EDIT-01-PNL-API-CANDIDATE";
