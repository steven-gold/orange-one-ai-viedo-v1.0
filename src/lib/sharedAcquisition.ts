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
  {
    sourceId: "SRC-GCIS-COMPANY-KEYWORD",
    name: "經濟部商業發展署公司登記資料",
    type: "JSON",
    scope: "全國公司登記（含非上市）",
    rights: "公開資料",
    classification: "公開",
    acquisitionMode: "WEB_FETCH",
    url: "https://data.gcis.nat.gov.tw/od/data/api/6BBA2268-1367-4B42-9CCA-BC17499EBE8C",
  },
  {
    sourceId: "SRC-GCIS-BUSINESS-KEYWORD",
    name: "經濟部商業發展署商業登記資料",
    type: "JSON",
    scope: "全國商業登記（獨資、合夥）",
    rights: "公開資料",
    classification: "公開",
    acquisitionMode: "WEB_FETCH",
    url: "https://data.gcis.nat.gov.tw/od/data/api/A1B4CBFF-2D3A-409B-8A78-2AD94F63AE4A",
  },
  {
    sourceId: "SRC-GCIS-COMPANY-ITEMS",
    name: "經濟部商業發展署公司營業項目",
    type: "JSON",
    scope: "公司登記營業項目",
    rights: "公開資料",
    classification: "公開",
    acquisitionMode: "WEB_FETCH",
    url: "https://data.gcis.nat.gov.tw/od/data/api/236EE382-4942-41A9-BD03-CA0709025E7C",
  },
] as const;

export const SHARED_SOURCE_IDS = {
  twse: "SRC-TWSE-T187AP03-L",
  gcisCompany: "SRC-GCIS-COMPANY-KEYWORD",
  gcisBusiness: "SRC-GCIS-BUSINESS-KEYWORD",
  gcisItems: "SRC-GCIS-COMPANY-ITEMS",
} as const;

export function sourceNameById(sourceId: string): string {
  return PUBLIC_JSON_SOURCES.find((source) => source.sourceId === sourceId)?.name ?? sourceId;
}

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
  nextCursor?: number;
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

function publicContact(value: string, kind: "EMAIL" | "PHONE" | "ADDRESS"): string {
  const text = value.trim();
  if (!text || text === "-" || text === "無" || text === "N/A") return "";
  if (kind === "EMAIL") return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text) ? text : "";
  return text.slice(0, 200);
}

const TOKEN_ALIASES: Record<string, string[]> = {
  媒體: ["文化創意", "電視", "廣播", "電影", "廣告", "出版"],
  影像: ["文化創意", "電視", "電影"],
  工作臺: [],
  企業開發: [],
};

export const PRODUCT_TOKEN_FAMILIES: Record<string, string[]> = {
  保養品: ["化粧品", "化妝品", "保養", "美容", "清潔用品", "彩妝", "護膚", "香皂", "洗護", "醫美"],
  化妝品: ["化粧品", "保養品", "美容", "清潔用品", "彩妝", "護膚", "香皂", "醫美"],
  化粧品: ["化妝品", "保養品", "美容", "清潔用品", "彩妝", "護膚", "香皂", "醫美"],
  彩妝: ["化粧品", "化妝品", "保養品", "美容"],
  美容: ["保養品", "化粧品", "醫美", "護膚"],
  醫美: ["美容", "保養品", "化粧品"],
  護膚: ["保養品", "化粧品", "美容"],
  保養: ["保養品", "化粧品", "美容", "護膚"],
  食品: ["餐飲", "烘焙", "食品製造", "罐頭", "飲料"],
  餐飲: ["食品", "烘焙", "餐廳"],
  軟體: ["資訊", "數位", "網路", "app", "程式"],
  資訊: ["軟體", "數位", "網路", "資料處理"],
  服飾: ["成衣", "紡織", "時尚", "內衣"],
  汽車: ["車輛", "汽車零件", "車用"],
  電子: ["半導體", "電子零件", "光電", "科技"],
};

export function expandTokenFamily(token: string): string[] {
  return PRODUCT_TOKEN_FAMILIES[token] ?? [];
}

const LANGUAGE_TOKEN = /^[a-z]{2,3}(-[a-z]{2,4})?$/i;

export function isSearchableToken(token: string): boolean {
  return token.length >= 2 && !LANGUAGE_TOKEN.test(token);
}

export function searchTokensOf(profile: DevProfile, limit = 6): string[] {
  const raw = [profile.product, profile.keywords, profile.industry, profile.market]
    .join(" ")
    .split(/[\s,，、]+/g)
    .map((item) => item.trim())
    .filter(isSearchableToken);
  const expanded = raw.flatMap((token) => [token, ...expandTokenFamily(token)]);
  return [...new Set(expanded)].slice(0, limit);
}

function tokensOf(profile: DevProfile): { include: string[]; exclude: string[] } {
  const raw = [profile.product, profile.industry, profile.keywords, profile.market, profile.language, profile.sourceScope]
    .join(" ")
    .split(/[\s,，、]+/g)
    .map((item) => item.trim())
    .filter((item) => item.length >= 2);
  const include = [...new Set(raw.flatMap((token) => [token, ...(TOKEN_ALIASES[token] ?? []), ...expandTokenFamily(token)]))].filter(
    (item) => item.length >= 2,
  );
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
    const email = publicContact(
      textOf(row, ["電子郵件信箱", "投資人關係電子郵件", "電子郵件", "Email", "email"]),
      "EMAIL",
    );
    const phone = publicContact(
      textOf(row, ["總機電話", "投資人關係聯絡電話", "過戶電話", "電話", "Telephone", "phone"]),
      "PHONE",
    );
    const address = publicContact(textOf(row, ["住址", "過戶地址", "英文通訊地址", "地址", "Address", "address"]), "ADDRESS");
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
      ...(email ? { email } : {}),
      ...(phone ? { phone } : {}),
      ...(address ? { address } : {}),
    });
    if (signals.length >= 12) break;
  }
  return signals;
}

function mergeEvidence(a: string, b: string): string {
  if (!a) return b;
  if (!b || b === a) return a;
  const parts = [...new Set([...a.split("；"), ...b.split("；")].filter(Boolean))];
  return parts.join("；").slice(0, 240);
}

function fillPublicContact(prior: DevSignal, incoming: DevSignal): DevSignal {
  if (prior.status !== "NEW") return prior;
  return {
    ...prior,
    email: prior.email || incoming.email,
    phone: prior.phone || incoming.phone,
    address: prior.address || incoming.address,
    evidence: mergeEvidence(prior.evidence, incoming.evidence),
    freshness: incoming.freshness || prior.freshness,
  };
}

type GcisCompanyRow = Record<string, unknown>;

export function parseGcisCompanyRows(raw: unknown, profile: DevProfile, sourceId: string): DevSignal[] {
  const rows = Array.isArray(raw) ? raw : [];
  const freshness = nowIso().slice(0, 10);
  const signals: DevSignal[] = [];
  const seen = new Set<string>();
  for (const entry of rows) {
    if (!entry || typeof entry !== "object") continue;
    const row = entry as GcisCompanyRow;
    const name = textOf(row, ["Company_Name", "Business_Name"]);
    const no = textOf(row, ["Business_Accounting_NO"]);
    const status = textOf(row, ["Company_Status_Desc", "Business_Current_Status_Desc", "Current_Status_Desc"]);
    if (!name || !no) continue;
    const identityValue = `TW-${no}`;
    if (seen.has(identityValue)) continue;
    seen.add(identityValue);
    const address = publicContact(textOf(row, ["Company_Location", "Business_Location"]), "ADDRESS");
    const agency = textOf(row, ["Register_Organization_Desc", "Authority_Name"]);
    const capital = textOf(row, ["Capital_Stock_Amount", "Capital_Amount"]);
    const evidence = [sourceNameById(sourceId), no, agency, status, capital ? `資本額 ${capital}` : ""].filter(Boolean).join(" ");
    signals.push({
      signalId: newUid("SIG"),
      companyName: name,
      intent: profile.product || profile.keywords || "登記資料",
      evidence,
      freshness,
      identityKind: "REGISTRATION",
      identityValue,
      match: "resolved",
      opportunity: "OPEN",
      status: "NEW",
      version: 1,
      ...(address ? { address } : {}),
    });
  }
  return signals;
}

type GcisItemsRow = Record<string, unknown>;

export function parseGcisBusinessItems(raw: unknown): { identityValue: string; items: string[] }[] {
  const rows = Array.isArray(raw) ? raw : [];
  const results: { identityValue: string; items: string[] }[] = [];
  for (const entry of rows) {
    if (!entry || typeof entry !== "object") continue;
    const row = entry as GcisItemsRow;
    const no = textOf(row, ["Business_Accounting_NO"]);
    if (!no) continue;
    const cmp = row["Cmp_Business"];
    const items: string[] = [];
    if (Array.isArray(cmp)) {
      for (const item of cmp) {
        if (!item || typeof item !== "object") continue;
        const desc = (item as GcisItemsRow)["Business_Item_Desc"];
        if (typeof desc === "string" && desc.trim()) items.push(desc.trim());
      }
    }
    results.push({ identityValue: `TW-${no}`, items });
  }
  return results;
}

export function mergeDiscoverySignals(existing: DevSignal[], incoming: DevSignal[]): DevSignal[] {
  const byIdentity = new Map(existing.map((item) => [item.identityValue, item]));
  for (const signal of incoming) {
    const prior = byIdentity.get(signal.identityValue);
    if (prior) {
      byIdentity.set(signal.identityValue, fillPublicContact(prior, signal));
      continue;
    }
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
