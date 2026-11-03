import { displayBoundValue } from "./displayValue";

type JsonRecord = { kind?: string; [key: string]: unknown };

function summarizeJson(parsed: unknown): string | null {
  if (Array.isArray(parsed)) return `${parsed.length} 項`;
  if (parsed === null || typeof parsed !== "object") return null;
  const record = parsed as JsonRecord;
  switch (record.kind) {
    case "ASSET_SCORECARD": {
      const dims = (record.dimensions as Array<{ score: number | null }> | undefined) ?? [];
      const scored = dims.filter((row) => typeof row.score === "number").length;
      const total = typeof record.weighted_total === "number" ? record.weighted_total : "—";
      return `${record.profile ?? "?"} · ${record.asset_type ?? "?"} · ${record.candidate_ref ?? "?"} · Total ${total} · ${record.overall ?? "?"}（已評 ${scored}/${dims.length} 維）`;
    }
    case "ASSET_FINDINGS": {
      const findings = (record.findings as unknown[] | undefined) ?? [];
      return `${findings.length} 項發現：${record.summary ?? ""}`;
    }
    case "ASSET_MANIFEST": {
      const items = (record.items as unknown[] | undefined) ?? [];
      const reuse = (record.reuse as unknown[] | undefined) ?? [];
      const missing = (record.missing as unknown[] | undefined) ?? [];
      return `${record.manifest_id ?? "?"} · ${items.length} 條目 · 可重用 ${reuse.length} · 缺件 ${missing.length}`;
    }
    case "ASSET_VERSION_HISTORY": {
      const versions = (record.versions as unknown[] | undefined) ?? [];
      return `${versions.length} 個歷史版本`;
    }
    case "VERSIONED_LAYER_DOCUMENT": {
      const layers = (record.layers as unknown[] | undefined) ?? [];
      return `${record.layer_doc_id ?? "?"} #v${record.version ?? "?"}（${layers.length} 圖層）`;
    }
    case "ASSET_PATCH_CANDIDATE": {
      const version = typeof record.resulting_asset_version === "string" ? record.resulting_asset_version : "";
      return `補丁 ${record.patch_id ?? ""} · ${record.status ?? "?"}${version ? ` · ${version}` : ""}`;
    }
    case "CORRECTION_SCRIPT_CANDIDATE":
      return `修正候選 ${record.candidate_id ?? ""} · ${record.status ?? "?"}`;
    case "ASSET_ERROR":
      return `${record.code ?? "ERR"}：${record.message ?? ""}`;
    default:
      return null;
  }
}

export function displayAssetValue(value: unknown, loading: boolean): string {
  if (value === null || value === undefined || value === "") return "—";
  const text = String(value);
  const head = text.trimStart()[0];
  if (head === "{" || head === "[") {
    try {
      const summarized = summarizeJson(JSON.parse(text));
      if (summarized) return summarized;
      const parsed = JSON.parse(text) as JsonRecord;
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed) && !parsed.kind) {
        const status = typeof parsed.status === "string" ? parsed.status : null;
        if (status) return `狀態 ${status}`;
      }
    } catch {
      return `${text.slice(0, 36)}…`;
    }
  }
  return displayBoundValue(text, loading);
}
