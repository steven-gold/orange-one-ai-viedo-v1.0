import { displayBoundValue } from "./displayValue";

export function displaySg02Value(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
