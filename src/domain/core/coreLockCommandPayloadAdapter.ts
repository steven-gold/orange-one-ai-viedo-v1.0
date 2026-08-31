import { createControlledTestMetadata, isControlledTestMode } from "../testing/controlledTestData";

export type CoreLockCommandKind = "DNA_LOCK" | "CORE_REVIEW" | "MOTHER_LOCK" | "CHILD_LOCK";

export type CoreLockCommandContext = {
  kind: CoreLockCommandKind;
  project_id: string | null;
  project_version_ref: string | null;
  dna_version_ref: string | null;
  blueprint_version_ref: string | null;
  topic_id: string | null;
  evidence_refs: readonly string[];
};

export type CoreLockCommandPayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; reason_code: string };

export type CoreLockCommandPayloadAdapter = {
  buildPayload: (context: CoreLockCommandContext) => Promise<CoreLockCommandPayloadResult> | CoreLockCommandPayloadResult;
};

let adapter: CoreLockCommandPayloadAdapter | null = null;

export function configureCoreLockCommandPayloadAdapter(next: CoreLockCommandPayloadAdapter) {
  adapter = next;
}

function valid(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) && Object.keys(value).length > 0;
}

function controlledTestPayload(context: CoreLockCommandContext): CoreLockCommandPayloadResult {
  return {
    ok: true,
    payload: {
      ...createControlledTestMetadata(`CORE-${context.kind}`),
      ...context,
    },
  };
}

export async function requestCoreLockCommandPayload(context: CoreLockCommandContext): Promise<CoreLockCommandPayloadResult> {
  const current = adapter;
  if (!current) {
    if (isControlledTestMode()) return controlledTestPayload(context);
    return { ok: false, reason_code: `${context.kind}_REGISTERED_COMMAND_SCHEMA_ADAPTER_NOT_BOUND` };
  }
  try {
    const result = await current.buildPayload(context);
    if (!result.ok) return result;
    if (!valid(result.payload)) return { ok: false, reason_code: `${context.kind}_REGISTERED_COMMAND_SCHEMA_PAYLOAD_EMPTY` };
    return result;
  } catch {
    return { ok: false, reason_code: `${context.kind}_REGISTERED_COMMAND_SCHEMA_ADAPTER_FAILED` };
  }
}
