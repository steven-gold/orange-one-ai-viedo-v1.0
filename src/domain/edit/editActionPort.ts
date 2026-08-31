import type { EditActionResult } from "./editRuntimeContract";
import type { EditClientState } from "./editClientState";

export type EditActionInvokeInput = {
  action_uid: string;
  source_mode: EditClientState["source_mode"];
  state: Readonly<EditClientState>;
};

export type EditActionInvoker = {
  invoke: (input: EditActionInvokeInput) => Promise<EditActionResult>;
};

let invoker: EditActionInvoker | null = null;

export function configureEditActionInvoker(next: EditActionInvoker) {
  invoker = next;
}

export function isEditActionInvokerBound() {
  return invoker !== null;
}

export async function invokeGovernedEditAction(input: EditActionInvokeInput): Promise<EditActionResult> {
  const current = invoker;
  if (!current) {
    return {
      ok:false,
      error_uid:"EDIT-01-ERR-CONTEXT-001",
      reason_code:"EDIT_ACTION_CLIENT_ADAPTER_NOT_BOUND",
      correlation_id:"unresolved",
    };
  }
  try {
    return await current.invoke(input);
  } catch {
    return {
      ok:false,
      error_uid:"EDIT-01-ERR-CONTEXT-001",
      reason_code:"EDIT_ACTION_CLIENT_ADAPTER_FAILED",
      correlation_id:"unresolved",
    };
  }
}
