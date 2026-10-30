import { displayBoundValue } from "./displayValue";

export function displayCoreValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}

function compactJson(value: string): Record<string, unknown> | undefined {
  if (!value.startsWith("{")) return undefined;
  try {
    const parsed = JSON.parse(value) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : undefined;
  } catch {
    return undefined;
  }
}

export function formatCoreStructured(value: unknown, loading: boolean): string {
  const raw = displayBoundValue(value, loading);
  const parsed = compactJson(raw);
  if (!parsed) return raw;
  if (parsed.kind === "CORE_EVALUATION") {
    const evidence = Array.isArray(parsed.evidence) ? (parsed.evidence as Array<Record<string, unknown>>) : [];
    const rows = evidence.map((row) => `${String(row.item)}:${String(row.result)}`).join("、");
    return `[核心評估 ${String(parsed.criteria_version ?? "")}] ${String(parsed.candidate ?? "")} → ${String(parsed.verdict ?? "")}（${rows}）`;
  }
  if (parsed.kind === "CORE_COMPARE") {
    const diffs = Array.isArray(parsed.differences) ? (parsed.differences as Array<Record<string, unknown>>) : [];
    const rows = diffs.map((row) => `${String(row.field)}: ${String(row.candidate_value)} ≠ ${String(row.canonical_value)}`).join("、");
    return `[候選比對] ${String(parsed.candidate ?? "")} vs ${String(parsed.canonical_version ?? "無投影")}${rows ? `（${rows}）` : "（無差異）"}`;
  }
  return raw;
}

export function formatCoreDecisionLog(value: unknown, loading: boolean): string {
  const raw = displayBoundValue(value, loading);
  const parsed = compactJson(raw);
  if (!parsed || parsed.kind !== "CORE_DECISION_LOG" || !Array.isArray(parsed.entries)) return raw;
  const entries = parsed.entries as Array<Record<string, unknown>>;
  if (!entries.length) return "無決策記錄";
  const last = entries[entries.length - 1];
  return `[決策記錄 ${entries.length} 筆] 最新：${String(last.actor ?? "")} ${String(last.decision ?? "")} @ ${String(last.at ?? "")}`;
}
