import { displayBoundValue } from "./displayValue";

export function displayStrValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
