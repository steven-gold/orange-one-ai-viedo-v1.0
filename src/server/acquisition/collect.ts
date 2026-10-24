import {
  PUBLIC_JSON_SOURCES,
  SHARED_ACQUISITION_UNAVAILABLE,
  completedRun,
  failedRun,
  itemsFromSignals,
  parsePublicCompanyRows,
  sourceRecordFrom,
  type AcquisitionCollectResult,
} from "@/lib/sharedAcquisition";
import type { DevProfile } from "@/lib/devState";

const FETCH_MS = 12000;

export async function collectDiscoverySignals(profile: DevProfile): Promise<AcquisitionCollectResult> {
  const source = PUBLIC_JSON_SOURCES[0];
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_MS);
  try {
    const response = await fetch(source.url, {
      signal: controller.signal,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "User-Agent": "ACPOS-SharedAcquisition/1.0",
      },
    });
    if (!response.ok) {
      const record = sourceRecordFrom(source, "UNAVAILABLE");
      return {
        ok: false,
        source: record,
        run: failedRun(source.sourceId, SHARED_ACQUISITION_UNAVAILABLE),
        reason: SHARED_ACQUISITION_UNAVAILABLE,
      };
    }
    const raw: unknown = await response.json();
    const signals = parsePublicCompanyRows(raw, profile, source);
    const record = sourceRecordFrom(source, "ACTIVE");
    return {
      ok: true,
      source: record,
      run: completedRun(source.sourceId, signals.length),
      signals,
      items: itemsFromSignals(signals, source.name),
    };
  } catch {
    const record = sourceRecordFrom(source, "UNAVAILABLE");
    return {
      ok: false,
      source: record,
      run: failedRun(source.sourceId, SHARED_ACQUISITION_UNAVAILABLE),
      reason: SHARED_ACQUISITION_UNAVAILABLE,
    };
  } finally {
    clearTimeout(timer);
  }
}
