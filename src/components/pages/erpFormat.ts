import { displayBoundValue } from "./displayValue";

export function displayErpValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
