import { displayBoundValue } from "./displayValue";

export function displayDevValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
