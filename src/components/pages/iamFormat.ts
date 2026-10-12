import { displayBoundValue } from "./displayValue";

export function displayIamValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
