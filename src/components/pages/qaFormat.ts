import { displayBoundValue } from "./displayValue";

export function displayQaValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
