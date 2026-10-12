import { displayBoundValue } from "./displayValue";

export function displayDbValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
