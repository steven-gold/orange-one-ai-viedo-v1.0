import { displayBoundValue } from "./displayValue";

export function displaySocValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
