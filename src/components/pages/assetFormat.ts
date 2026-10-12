import { displayBoundValue } from "./displayValue";

export function displayAssetValue(value: unknown, loading: boolean): string {
  return displayBoundValue(value, loading);
}
