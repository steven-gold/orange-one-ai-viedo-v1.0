export const AI_UNAVAILABLE_ZH = "目前無法取得 AI 回應（供應商未設定或暫時無法使用）。";

export function isAiUnavailable(value: unknown): boolean {
  return typeof value === "string" && value.trim() === AI_UNAVAILABLE_ZH;
}

export const ASSET_CORRECTION_RESPONSE_UID = "ASSET-01-FLD-CORRECTION-RESPONSE";
export const VIDEO_CORRECTION_RESPONSE_UID = "VIDEO-01-FLD-CORRECTION-RESPONSE";
export const EDIT_CORRECTION_CANDIDATE_UID = "EDIT-01-PNL-API-CANDIDATE";
