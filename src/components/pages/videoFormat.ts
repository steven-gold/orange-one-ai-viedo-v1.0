import { displayBoundValue } from "./displayValue";

type JsonRecord = { kind?: string; [key: string]: unknown };

function summarizeJson(parsed: unknown): string | null {
  if (Array.isArray(parsed)) return `${parsed.length} 項`;
  if (parsed === null || typeof parsed !== "object") return null;
  const record = parsed as JsonRecord;
  switch (record.kind) {
    case "VIDEO_SCORECARD": {
      const dims = (record.dimensions as Array<{ score: number | null }> | undefined) ?? [];
      const scored = dims.filter((row) => typeof row.score === "number").length;
      const total = typeof record.weighted_total === "number" ? record.weighted_total : "—";
      return `${record.profile ?? "?"} · ${record.candidate ?? "?"} · Total ${total} · ${record.overall ?? "?"}（已評 ${scored}/${dims.length} 維）`;
    }
    case "EXACT_VIDEO_HANDOFF_MANIFEST": {
      const shots = (record.shot_versions as unknown[] | undefined) ?? [];
      const layers = (record.layer_versions as unknown[] | undefined) ?? [];
      return `交接 ${record.manifest_id ?? "?"} · 影片 ${record.video_version ?? "?"} · 鏡頭 ${shots.length} · 圖層 ${layers.length}`;
    }
    case "VIDEO_CORRECTION_CANDIDATE":
      return `修正候選 ${record.candidate_id ?? ""} · ${record.status ?? "?"}`;
    case "VIDEO_ERROR":
      return `${record.code ?? "ERR"}：${record.message ?? ""}`;
    default:
      return null;
  }
}

export function displayVideoValue(value: unknown, loading: boolean): string {
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
