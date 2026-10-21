import { displayBoundValue } from "./displayValue";
import { dialogueBindingStatusLabel, parseDialogueTimingBinding } from "@/lib/dialogueTimingBinding";

export function displayEditValue(value: unknown, loading: boolean): string {
  if (typeof value === "string") {
    const binding = parseDialogueTimingBinding(value);
    if (binding) return dialogueBindingStatusLabel(binding.status) || "—";
  }
  return displayBoundValue(value, loading);
}
