import { displayBoundValue } from "./displayValue";

export function displayDashboardValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}

export function isDashboardEmpty(value: unknown, loading: boolean): boolean {
  if (loading) return false;
  return value === null || value === undefined || value === "";
}
