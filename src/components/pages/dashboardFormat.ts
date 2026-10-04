export function displayDashboardValue(value: unknown, loading: boolean): string {
  if (loading) return "—";
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export function isDashboardEmpty(value: unknown, loading: boolean): boolean {
  if (loading) return false;
  return value === null || value === undefined || value === "";
}
