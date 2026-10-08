export function displaySysValue(value: unknown, loading: boolean): string {
  if (loading) return "—";
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}
