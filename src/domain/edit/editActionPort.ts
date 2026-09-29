import type { EditActionResult } from "./editRuntimeContract";
import type { EditClientState } from "./editClientState";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";

export type EditActionInvokeInput = {
  action_uid: string;
  source_mode: EditClientState["source_mode"];
  state: Readonly<EditClientState>;
};

export type EditActionInvoker = {
  invoke: (input: EditActionInvokeInput) => Promise<EditActionResult>;
};

let invoker: EditActionInvoker | null = null;
let productionLoad: Promise<EditActionInvoker> | null = null;

export function configureEditActionInvoker(next: EditActionInvoker) {
  invoker = next;
}

async function productionInvoker(): Promise<EditActionInvoker> {
  if (invoker) return invoker;
  if (isControlledTestMode()) throw new Error("CONTROLLED_EDIT_ACTION_RUNTIME_NOT_CONFIGURED");
  productionLoad ??= import("./productionEditClientRuntime").then((module) => module.productionEditActionInvoker);
  const loaded = await productionLoad;
  if (!invoker) invoker = loaded;
  return invoker;
}

export function isEditActionInvokerBound() {
  return invoker !== null || !isControlledTestMode();
}

export async function invokeGovernedEditAction(input: EditActionInvokeInput): Promise<EditActionResult> {
  try {
    const current = invoker ?? await productionInvoker();
    return await current.invoke(input);
  } catch (error) {
    const reason_code = error instanceof Error && error.message ? error.message : "EDIT_ACTION_CLIENT_ADAPTER_FAILED";
    return {
      ok:false,
      error_uid:"EDIT-01-ERR-CONTEXT-001",
      reason_code,
      correlation_id:"unresolved",
    };
  }
}
