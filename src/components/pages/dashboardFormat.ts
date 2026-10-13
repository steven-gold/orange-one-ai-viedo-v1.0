import { displayBoundValue } from "./displayValue";

export function displayDashboardValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}

export function displayDashboardDetail(detail: string, loading: boolean): string {
  if (loading) return "";
  const text = detail.trim();
  if (!text || text.startsWith("Opened ") || text.startsWith("opened ")) return "";
  return displayBoundValue(text, false);
}

export function isDashboardEmpty(value: unknown, loading: boolean): boolean {
  if (loading) return false;
  return value === null || value === undefined || value === "";
}
