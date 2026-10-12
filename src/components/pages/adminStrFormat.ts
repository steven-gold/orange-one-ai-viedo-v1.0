import { displayBoundValue } from "./displayValue";

export function displayAdminStrValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
