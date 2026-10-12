import { displayBoundValue } from "./displayValue";

export function displayAiapiValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
