import { displayBoundValue } from "./displayValue";

export function displayInfoValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
