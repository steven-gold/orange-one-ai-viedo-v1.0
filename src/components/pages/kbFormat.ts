import { displayBoundValue } from "./displayValue";

export function displayKbValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
