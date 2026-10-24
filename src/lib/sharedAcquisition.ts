import { newUid, nowIso, type DevProfile, type DevSignal } from "./devState";

export const SHARED_ACQUISITION_UNAVAILABLE = "SHARED_ACQUISITION_UNAVAILABLE";

export const PUBLIC_JSON_SOURCES = [
  {
    sourceId: "SRC-TWSE-T187AP03-L",
    name: "臺灣證券交易所上市基本資料",
    type: "JSON",
    scope: "上市發行人基本資料",
    rights: "公開資料",
    classification: "公開",
    acquisitionMode: "WEB_FETCH",
    url: "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
  },
] as const;

export type PublicJsonSource = (typeof PUBLIC_JSON_SOURCES)[number];

export type AcquisitionSourceRecord = {
  sourceId: string;
  name: string;
  type: string;
  scope: string;
  rights: string;
  classification: string;
  acquisitionMode: string;
  status: "ACTIVE" | "UNAVAILABLE";
  url: string;
};

export type AcquisitionRun = {
  runId: string;
  status: "RUNNING" | "COMPLETE" | "EXTERNAL_PENDING";
  progress: string;
  failure: string;
  sourceId: string;
  itemCount: number;
  startedAt: string;
  updatedAt: string;
};

export type AcquisitionResultItem = {
  title: string;
  type: string;
  source: string;
  freshness: string;
  identityValue: string;
};

export type AcquisitionCollectOk = {
  ok: true;
  source: AcquisitionSourceRecord;
  run: AcquisitionRun;
  signals: DevSignal[];
  items: AcquisitionResultItem[];
};

export type AcquisitionCollectFail = {
  ok: false;
  source: AcquisitionSourceRecord;
  run: AcquisitionRun;
  reason: string;
};

export type AcquisitionCollectResult = AcquisitionCollectOk | AcquisitionCollectFail;

type TwseRow = Record<string, unknown>;

function textOf(row: TwseRow, keys: string[]): string {
  for (const key of keys) {
    const value = row[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

const TOKEN_ALIASES: Record<string, string[]> = {
  媒體: ["文化創意", "電視", "廣播", "電影", "廣告", "出版"],
  影像: ["文化創意", "電視", "電影"],
  工作臺: [],
  企業開發: [],
};

function tokensOf(profile: DevProfile): { include: string[]; exclude: string[] } {
  const raw = [profile.product, profile.industry, profile.keywords, profile.market]
    .join(" ")
    .split(/[\s,，、]+/g)
    .map((item) => item.trim())
    .filter((item) => item.length >= 2);
  const include = [...new Set(raw.flatMap((token) => [token, ...(TOKEN_ALIASES[token] ?? [])]))].filter((item) => item.length >= 2);
  const exclude = profile.exclude
    .split(/[\s,，、]+/g)
    .map((item) => item.trim())
    .filter((item) => item.length >= 2);
  return { include, exclude };
}

function rowMatches(haystack: string, include: string[], exclude: string[]): boolean {
  const hay = haystack.toLowerCase();
  if (exclude.some((token) => hay.includes(token.toLowerCase()))) return false;
  if (!include.length) return true;
  return include.some((token) => hay.includes(token.toLowerCase()));
}

export function sourceRecordFrom(source: PublicJsonSource, status: AcquisitionSourceRecord["status"]): AcquisitionSourceRecord {
  return {
    sourceId: source.sourceId,
    name: source.name,
    type: source.type,
    scope: source.scope,
    rights: source.rights,
    classification: source.classification,
    acquisitionMode: source.acquisitionMode,
    status,
    url: source.url,
  };
}

export function parsePublicCompanyRows(raw: unknown, profile: DevProfile, source: PublicJsonSource): DevSignal[] {
  const rows = Array.isArray(raw) ? raw : Array.isArray((raw as { data?: unknown })?.data) ? ((raw as { data: unknown[] }).data) : [];
  const { include, exclude } = tokensOf(profile);
  const freshness = nowIso().slice(0, 10);
  const signals: DevSignal[] = [];
  const seen = new Set<string>();
  for (const entry of rows) {
    if (!entry || typeof entry !== "object") continue;
    const row = entry as TwseRow;
    const name = textOf(row, ["公司名稱", "公司簡稱", "Name", "name"]);
    const code = textOf(row, ["公司代號", "CompanyCode", "code"]);
    const tax = textOf(row, ["營利事業統一編號", "統一編號", "TaxID"]);
    const industry = textOf(row, ["產業別", "Industry", "industry"]);
    if (!name || (!code && !tax)) continue;
    const haystack = [name, industry, code, tax].join(" ");
    if (!rowMatches(haystack, include, exclude)) continue;
    const identityValue = tax ? `TW-${tax}` : `TWSE-${code}`;
    if (seen.has(identityValue)) continue;
    seen.add(identityValue);
    signals.push({
      signalId: newUid("SIG"),
      companyName: name,
      intent: profile.product || profile.keywords || "公開上市資料",
      evidence: `${source.name} ${code || tax} ${industry}`.trim(),
      freshness,
      identityKind: "REGISTRATION",
      identityValue,
      match: "resolved",
      opportunity: "OPEN",
      status: "NEW",
      version: 1,
    });
    if (signals.length >= 12) break;
  }
  return signals;
}

export function mergeDiscoverySignals(existing: DevSignal[], incoming: DevSignal[]): DevSignal[] {
  const byIdentity = new Map(existing.map((item) => [item.identityValue, item]));
  for (const signal of incoming) {
    const prior = byIdentity.get(signal.identityValue);
    if (prior) continue;
    byIdentity.set(signal.identityValue, signal);
  }
  return [...byIdentity.values()];
}

export function itemsFromSignals(signals: DevSignal[], sourceName: string): AcquisitionResultItem[] {
  return signals.map((signal) => ({
    title: signal.companyName,
    type: "市場訊號",
    source: sourceName,
    freshness: signal.freshness,
    identityValue: signal.identityValue,
  }));
}

export function pendingRun(sourceId: string): AcquisitionRun {
  const at = nowIso();
  return {
    runId: newUid("RUN"),
    status: "RUNNING",
    progress: "已送出取得意圖",
    failure: "",
    sourceId,
    itemCount: 0,
    startedAt: at,
    updatedAt: at,
  };
}

export function failedRun(sourceId: string, reason: string): AcquisitionRun {
  const at = nowIso();
  return {
    runId: newUid("RUN"),
    status: "EXTERNAL_PENDING",
    progress: "等待外部來源",
    failure: reason,
    sourceId,
    itemCount: 0,
    startedAt: at,
    updatedAt: at,
  };
}

export function completedRun(sourceId: string, itemCount: number): AcquisitionRun {
  const at = nowIso();
  return {
    runId: newUid("RUN"),
    status: "COMPLETE",
    progress: itemCount ? `已取得 ${itemCount} 筆` : "來源可用，本次無符合條件資料",
    failure: "",
    sourceId,
    itemCount,
    startedAt: at,
    updatedAt: at,
  };
}
