import { displayBoundValue } from "./displayValue";

export function displayCoreValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
