import {
  PUBLIC_JSON_SOURCES,
  SHARED_ACQUISITION_UNAVAILABLE,
  SHARED_SOURCE_IDS,
  completedRun,
  failedRun,
  itemsFromSignals,
  parseGcisBusinessItems,
  parseGcisCompanyRows,
  parsePublicCompanyRows,
  searchTokensOf,
  sourceRecordFrom,
  sourceNameById,
  type AcquisitionCollectResult,
  type AcquisitionResultItem,
  type AcquisitionSourceRecord,
} from "@/lib/sharedAcquisition";
import type { DevProfile, DevSignal } from "@/lib/devState";

const FETCH_MS = 12000;
const GCIS_QUERY_TOP = 100;
const GCIS_CALL_CONCURRENCY = 2;
const GCIS_ITEMS_ENRICH_LIMIT = 6;
const GCIS_CURSOR_WRAP = 1000;

function timeoutSignal(ms: number): { signal: AbortSignal; done: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, done: () => clearTimeout(timer) };
}

function gcisUrl(endpointId: string, filter: string, top: number, skip = 0): string {
  const source = PUBLIC_JSON_SOURCES.find((item) => item.sourceId === endpointId);
  if (!source) throw new Error(`UNKNOWN_SOURCE:${endpointId}`);
  const params = [`$format=json`, `$filter=${encodeURIComponent(filter)}`, `$skip=${skip}`, `$top=${top}`].join("&");
  return `${source.url}?${params}`;
}

async function fetchJson(url: string): Promise<unknown> {
  const { signal, done } = timeoutSignal(FETCH_MS);
  try {
    const response = await fetch(url, {
      signal,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "User-Agent": "ACPOS-SharedAcquisition/1.0",
      },
    });
    if (!response.ok) throw new Error(`HTTP_${response.status}`);
    const text = await response.text();
    if (!text.trim() || text.trim().startsWith("<")) throw new Error("NON_JSON_RESPONSE");
    return JSON.parse(text);
  } finally {
    done();
  }
}

type CollectedBatch = { sourceId: string; signals: DevSignal[] };

async function collectTwse(profile: DevProfile): Promise<CollectedBatch> {
  const source = PUBLIC_JSON_SOURCES[0];
  const raw = await fetchJson(source.url);
  return { sourceId: source.sourceId, signals: parsePublicCompanyRows(raw, profile, source) };
}

function chunk<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += size) chunks.push(items.slice(index, index + size));
  return chunks;
}

async function queryGcisKeyword(
  endpointId: string,
  keywordField: string,
  statusField: string,
  statusCode: string,
  token: string,
  skip: number,
): Promise<unknown> {
  const filter = `${keywordField} like ${token} and ${statusField} eq ${statusCode}`;
  return fetchJson(gcisUrl(endpointId, filter, GCIS_QUERY_TOP, skip));
}

async function collectGcisKeywordBatch(
  endpointId: string,
  profile: DevProfile,
  tokens: string[],
  skip: number,
  statusFilter: { keywordField: string; statusField: string; statusCode: string },
): Promise<CollectedBatch> {
  const batches: unknown[] = [];
  for (const slice of chunk(tokens, GCIS_CALL_CONCURRENCY)) {
    const settled = await Promise.allSettled(
      slice.map((token) =>
        queryGcisKeyword(endpointId, statusFilter.keywordField, statusFilter.statusField, statusFilter.statusCode, token, skip),
      ),
    );
    for (const item of settled) {
      if (item.status === "fulfilled") batches.push(item.value);
    }
  }
  if (!batches.length) throw new Error("GCIS_NO_RESULTS");
  const collected = batches.flatMap((raw) => parseGcisCompanyRows(raw, profile, endpointId));
  const deduped = new Map(collected.map((signal) => [signal.identityValue, signal]));
  return { sourceId: endpointId, signals: [...deduped.values()] };
}

async function enrichBusinessItems(signals: DevSignal[]): Promise<Map<string, string>> {
  const enriched = new Map<string, string>();
  const numbers = signals
    .slice(0, GCIS_ITEMS_ENRICH_LIMIT)
    .map((signal) => signal.identityValue.replace(/^TW-/, ""))
    .filter((no) => /^\d{8}$/.test(no));
  for (const slice of chunk(numbers, GCIS_CALL_CONCURRENCY)) {
    const settled = await Promise.allSettled(
      slice.map((no) => fetchJson(gcisUrl(SHARED_SOURCE_IDS.gcisItems, `Business_Accounting_NO eq ${no}`, 1))),
    );
    for (const item of settled) {
      if (item.status === "rejected") continue;
      for (const parsed of parseGcisBusinessItems(item.value)) {
        if (parsed.items.length) enriched.set(parsed.identityValue, parsed.items.join("、"));
      }
    }
  }
  return enriched;
}

export async function collectDiscoverySignals(profile: DevProfile, cursor = 0): Promise<AcquisitionCollectResult> {
  const tokens = searchTokensOf(profile);
  const tasks: Promise<CollectedBatch>[] = [
    collectTwse(profile),
    ...(tokens.length
      ? [
          collectGcisKeywordBatch(SHARED_SOURCE_IDS.gcisCompany, profile, tokens, cursor, {
            keywordField: "Company_Name",
            statusField: "Company_Status",
            statusCode: "01",
          }),
          collectGcisKeywordBatch(SHARED_SOURCE_IDS.gcisBusiness, profile, tokens, cursor, {
            keywordField: "Business_Name",
            statusField: "Business_Current_Status",
            statusCode: "1",
          }),
        ]
      : []),
  ];
  const settled = await Promise.allSettled(tasks);

  const batches: CollectedBatch[] = [];
  for (const item of settled) {
    if (item.status === "fulfilled") batches.push(item.value);
  }

  if (!batches.length) {
    const reason = SHARED_ACQUISITION_UNAVAILABLE;
    const record: AcquisitionSourceRecord = sourceRecordFrom(PUBLIC_JSON_SOURCES[0], "UNAVAILABLE");
    return {
      ok: false,
      source: record,
      run: failedRun(SHARED_SOURCE_IDS.twse, reason),
      reason,
    };
  }

  let merged: DevSignal[] = [];
  for (const batch of batches) {
    for (const signal of batch.signals) merged.push(signal);
  }
  const okSourceIds = [...new Set(batches.map((batch) => batch.sourceId))];

  if (okSourceIds.includes(SHARED_SOURCE_IDS.gcisCompany) || okSourceIds.includes(SHARED_SOURCE_IDS.gcisBusiness)) {
    try {
      const enriched = await enrichBusinessItems(merged);
      if (enriched.size) {
        merged = merged.map((signal) => {
          const items = enriched.get(signal.identityValue);
          return items ? { ...signal, evidence: `${signal.evidence} ${items}`.trim() } : signal;
        });
      }
    } catch {
      // Business-items enrichment is best-effort; signals stay usable without it.
    }
  }

  const deduped = new Map<string, DevSignal>();
  for (const signal of merged) {
    const prior = deduped.get(signal.identityValue);
    deduped.set(signal.identityValue, prior ?? signal);
  }
  const signals = [...deduped.values()];

  const nextCursor = (cursor + GCIS_QUERY_TOP) % GCIS_CURSOR_WRAP;
  const primaryLabel = okSourceIds.map((sourceId) => sourceNameById(sourceId)).join("、") || "公開來源";
  const items: AcquisitionResultItem[] = itemsFromSignals(signals, primaryLabel);
  return {
    ok: true,
    source: sourceRecordFrom(PUBLIC_JSON_SOURCES[0], "ACTIVE"),
    run: completedRun(okSourceIds[0], signals.length),
    signals,
    items,
    nextCursor,
  };
}
