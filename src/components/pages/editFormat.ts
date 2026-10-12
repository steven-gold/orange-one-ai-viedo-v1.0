import { displayBoundValue } from "./displayValue";

export function displayEditValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
