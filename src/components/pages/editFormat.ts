import { displayBoundValue } from "./displayValue";
import { dialogueBindingStatusLabel, parseDialogueTimingBinding } from "@/lib/dialogueTimingBinding";

type JsonRecord = { kind?: string; [key: string]: unknown };

function summarizeJson(parsed: unknown): string | null {
  if (Array.isArray(parsed)) return `${parsed.length} 項`;
  if (parsed === null || typeof parsed !== "object") return null;
  const record = parsed as JsonRecord;
  switch (record.kind) {
    case "EXACT_VIDEO_HANDOFF_MANIFEST": {
      const shots = (record.shot_versions as unknown[] | undefined) ?? [];
      const layers = (record.layer_versions as unknown[] | undefined) ?? [];
      return `影片交接 ${record.manifest_id ?? "?"} · ${record.video_version ?? "?"} · 證據 ${record.evidence ?? "—"}`;
    }
    default:
      return null;
  }
}

export function displayEditValue(value: unknown, loading: boolean): string {
  if (typeof value === "string") {
    const binding = parseDialogueTimingBinding(value);
    if (binding) return dialogueBindingStatusLabel(binding.status) || "—";
    const head = value.trimStart()[0];
    if (head === "{") {
      try {
        const summarized = summarizeJson(JSON.parse(value));
        if (summarized) return summarized;
      } catch {
        return `${value.slice(0, 36)}…`;
      }
    }
  }
  return displayBoundValue(value, loading);
}
