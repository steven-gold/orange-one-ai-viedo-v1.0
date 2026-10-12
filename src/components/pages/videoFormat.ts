import { displayBoundValue } from "./displayValue";

export function displayVideoValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
