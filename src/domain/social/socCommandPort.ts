import type { SocNormalizedProjection } from "./socProjectionPort";

export type SocCommandInput = {
  action_uid: string;
  control_uid: string;
  projection: SocNormalizedProjection | null;
};

export type SocCommandResult =
  | { ok: true; projection: SocNormalizedProjection; correlation_id: string }
  | { ok: false; error_uid: string; reason_code: string; correlation_id: string };

export type SocCommandAdapter = {
  invoke: (input: SocCommandInput) => Promise<SocCommandResult>;
  supports?: (action_uid: string) => boolean;
};

let adapter: SocCommandAdapter | null = null;

export function configureSocCommandAdapter(next: SocCommandAdapter) {
  adapter = next;
}

export function isSocCommandAdapterBound() {
  return adapter !== null;
}

export function isSocCommandActionBound(action_uid: string) {
  return Boolean(adapter && (!adapter.supports || adapter.supports(action_uid)));
}

export async function invokeSocCommand(input: SocCommandInput): Promise<SocCommandResult> {
  if (!adapter || (adapter.supports && !adapter.supports(input.action_uid))) {
    return {
      ok: false,
      error_uid: "SOC-01-ERR-UNDEFINED",
      reason_code: "SOC_COMMAND_RUNTIME_NOT_BOUND",
      correlation_id: "unresolved",
    };
  }
  try {
    return await adapter.invoke(input);
  } catch {
    return {
      ok: false,
      error_uid: "SOC-01-ERR-UNDEFINED",
      reason_code: "SOC_COMMAND_RUNTIME_FAILED",
      correlation_id: "unresolved",
    };
  }
}
