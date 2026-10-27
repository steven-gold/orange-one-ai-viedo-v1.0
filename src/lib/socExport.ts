import type { SocRequest, SocTarget } from "./socState";

function csvCell(value: string): string {
  if (/[",\n\r]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

export function socTargetsCsv(targets: SocTarget[]): string {
  const header = ["平台", "名稱", "類型", "狀態", "訊號", "佐證"];
  const rows = targets.map((t) =>
    [t.platformKey, t.name, t.targetType, t.status, t.signal, t.evidence].map(csvCell).join(","),
  );
  return `\uFEFF${[header.join(","), ...rows].join("\r\n")}`;
}

export function socRequestsCsv(requests: SocRequest[]): string {
  const header = ["請求", "目標", "帳號", "內容包", "狀態", "外部", "互動數據", "互動", "回執", "事件", "建立時間"];
  const rows = requests.map((r) =>
    [
      r.requestId,
      r.targetId,
      r.accountId,
      r.packageId,
      r.status,
      r.external,
      r.metrics,
      r.interaction,
      r.callback,
      r.incident,
      r.createdAt,
    ]
      .map(csvCell)
      .join(","),
  );
  return `\uFEFF${[header.join(","), ...rows].join("\r\n")}`;
}

export function downloadSocCsv(csv: string, filename: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
