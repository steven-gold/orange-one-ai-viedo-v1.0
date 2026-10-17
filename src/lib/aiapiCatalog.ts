export interface AiapiCatalogEntry {
  provider: string;
  model: string;
  capability: string;
  adapter: string;
  baseUrl: string;
  endpoint: string;
  timeout: string;
  positioning: string;
  acposScope: string;
  inputReq: string;
  outputReq: string;
  billing: string;
  recommendedUse: string;
  restrictions: string;
  docs: string;
}

export const AIAPI_CATALOG: AiapiCatalogEntry[] = [
  {
    provider: "google",
    model: "gemini-flash-lite-latest",
    capability: "chat",
    adapter: "gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta",
    endpoint: "models/gemini-flash-lite-latest:generateContent",
    timeout: "30",
    positioning: "低成本、低延遲的文字對話與摘要",
    acposScope: "CORE 對話、VIDEO／ASSET 內容校正",
    inputReq: "純文字提示詞；可附短篇參考文字",
    outputReq: "文字回覆",
    billing: "依輸入／輸出 token 分開計價",
    recommendedUse: "客服回覆草稿、長文摘要、欄位校正",
    restrictions: "不支援語音克隆；長篇影像生成需改用專用模型",
    docs: "https://ai.google.dev/gemini-api/docs",
  },
  {
    provider: "google",
    model: "gemini-2.5-flash",
    capability: "chat",
    adapter: "gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta",
    endpoint: "models/gemini-2.5-flash:generateContent",
    timeout: "30",
    positioning: "平衡品質與速度的通用文字模型",
    acposScope: "CORE 對話、VIDEO／ASSET 內容校正",
    inputReq: "純文字提示詞；可附參考段落",
    outputReq: "文字回覆",
    billing: "依輸入／輸出 token 分開計價",
    recommendedUse: "一般問答、腳本潤飾、結構化輸出",
    restrictions: "高解析度影像理解需確認模型版本支援",
    docs: "https://ai.google.dev/gemini-api/docs",
  },
  {
    provider: "google",
    model: "gemini-2.5-pro",
    capability: "chat",
    adapter: "gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta",
    endpoint: "models/gemini-2.5-pro:generateContent",
    timeout: "60",
    positioning: "高複雜度推理與長文理解",
    acposScope: "CORE 對話、VIDEO／ASSET 內容校正",
    inputReq: "長篇文字或結構化資料",
    outputReq: "文字回覆",
    billing: "依輸入／輸出 token 分開計價（單價較高）",
    recommendedUse: "長篇劇本分析、複雜指令拆解",
    restrictions: "成本較高，不建議用於大量短問答",
    docs: "https://ai.google.dev/gemini-api/docs",
  },
  {
    provider: "openai",
    model: "gpt-4o-mini",
    capability: "chat",
    adapter: "openai",
    baseUrl: "https://api.openai.com/v1",
    endpoint: "/chat/completions",
    timeout: "30",
    positioning: "低成本的通用文字對話",
    acposScope: "CORE 對話、VIDEO／ASSET 內容校正",
    inputReq: "純文字訊息陣列",
    outputReq: "文字回覆",
    billing: "依輸入／輸出 token 分開計價",
    recommendedUse: "短問答、分類、文案初稿",
    restrictions: "長篇推理建議改用較大型號",
    docs: "https://platform.openai.com/docs",
  },
  {
    provider: "openai",
    model: "gpt-4o",
    capability: "chat",
    adapter: "openai",
    baseUrl: "https://api.openai.com/v1",
    endpoint: "/chat/completions",
    timeout: "60",
    positioning: "多模態通用模型，文字品質較高",
    acposScope: "CORE 對話、VIDEO／ASSET 內容校正",
    inputReq: "文字或文字加圖片",
    outputReq: "文字回覆",
    billing: "依輸入／輸出 token 分開計價（單價較高）",
    recommendedUse: "需要較高準確度的內容生成與審稿",
    restrictions: "成本較高，需設定預算閘門",
    docs: "https://platform.openai.com/docs",
  },
  {
    provider: "anthropic",
    model: "claude-sonnet-4",
    capability: "chat",
    adapter: "anthropic",
    baseUrl: "https://api.anthropic.com/v1",
    endpoint: "/messages",
    timeout: "60",
    positioning: "長文理解與寫作品質均衡",
    acposScope: "CORE 對話、VIDEO／ASSET 內容校正",
    inputReq: "文字訊息（可含長篇文件）",
    outputReq: "文字回覆",
    billing: "依輸入／輸出 token 分開計價",
    recommendedUse: "長文改寫、腳本審閱、語氣調整",
    restrictions: "需設定 max tokens 以避免長回覆成本",
    docs: "https://docs.anthropic.com",
  },
  {
    provider: "deepseek",
    model: "deepseek-chat",
    capability: "chat",
    adapter: "openai",
    baseUrl: "https://api.deepseek.com/v1",
    endpoint: "/chat/completions",
    timeout: "30",
    positioning: "低成本通用文字對話",
    acposScope: "CORE 對話、VIDEO／ASSET 內容校正",
    inputReq: "純文字訊息陣列",
    outputReq: "文字回覆",
    billing: "依輸入／輸出 token 分開計價",
    recommendedUse: "大量短問答、分類、草稿",
    restrictions: "尖峰時段回應時間可能較長",
    docs: "https://api-docs.deepseek.com",
  },
];

export const AIAPI_CATALOG_FIELDS = [
  "capability",
  "adapter",
  "baseUrl",
  "endpoint",
  "timeout",
  "positioning",
  "acposScope",
  "inputReq",
  "outputReq",
  "billing",
  "recommendedUse",
  "restrictions",
  "docs",
] as const;

export type AiapiCatalogField = (typeof AIAPI_CATALOG_FIELDS)[number];

export function catalogProviders(): string[] {
  return [...new Set(AIAPI_CATALOG.map((entry) => entry.provider))];
}

export function catalogModels(provider: string): string[] {
  const key = provider.trim().toLowerCase();
  if (!key) return [];
  return AIAPI_CATALOG.filter((entry) => entry.provider.toLowerCase() === key).map((entry) => entry.model);
}

export function catalogEntry(provider: string, model: string): AiapiCatalogEntry | null {
  const p = provider.trim().toLowerCase();
  const m = model.trim().toLowerCase();
  if (!p) return null;
  if (!m) {
    const first = AIAPI_CATALOG.find((entry) => entry.provider.toLowerCase() === p);
    return first ?? null;
  }
  return (
    AIAPI_CATALOG.find(
      (entry) => entry.provider.toLowerCase() === p && entry.model.toLowerCase() === m,
    ) ?? null
  );
}

export function catalogDefaults(
  provider: string,
  model: string,
): Partial<Record<AiapiCatalogField, string>> {
  const entry = catalogEntry(provider, model);
  if (!entry) return {};
  const out: Partial<Record<AiapiCatalogField, string>> = {};
  for (const field of AIAPI_CATALOG_FIELDS) out[field] = entry[field];
  return out;
}

export function catalogValue(
  provider: string,
  model: string,
  field: AiapiCatalogField,
): string {
  return catalogEntry(provider, model)?.[field] ?? "";
}
