import { displayBoundValue } from "./displayValue";

export function displaySysValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
