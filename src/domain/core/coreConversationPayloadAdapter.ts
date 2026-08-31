import { createControlledTestMetadata, isControlledTestMode } from "../testing/controlledTestData";

export type CoreThreadPayloadContext = {
  project_id: string;
  topic_id: string | null;
  work_item: string;
  ai_mode: "SINGLE" | "MULTI";
};

export type CoreMessagePayloadContext = {
  conversation_id: string;
  message: string;
  ai_mode: "SINGLE" | "MULTI";
  attachment_refs: readonly string[];
  reference_refs: readonly string[];
};

export type CoreConversationPayloadResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; reason_code: string };

export type CoreConversationPayloadAdapter = {
  buildThreadCreatePayload: (context: CoreThreadPayloadContext) => Promise<CoreConversationPayloadResult> | CoreConversationPayloadResult;
  buildMessageSendPayload: (context: CoreMessagePayloadContext) => Promise<CoreConversationPayloadResult> | CoreConversationPayloadResult;
};

let adapter: CoreConversationPayloadAdapter | null = null;

export function configureCoreConversationPayloadAdapter(next: CoreConversationPayloadAdapter) {
  adapter = next;
}

function validPayload(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) && Object.keys(value).length > 0;
}

function controlledTestPayload(operation: "THREAD_CREATE" | "MESSAGE_SEND", context: CoreThreadPayloadContext | CoreMessagePayloadContext): CoreConversationPayloadResult {
  return {
    ok: true,
    payload: {
      ...createControlledTestMetadata(`CORE-CONVERSATION-${operation}`),
      ...context,
    },
  };
}

async function normalize(
  operation: "THREAD_CREATE" | "MESSAGE_SEND",
  context: CoreThreadPayloadContext | CoreMessagePayloadContext,
  build: (current: CoreConversationPayloadAdapter) => Promise<CoreConversationPayloadResult> | CoreConversationPayloadResult,
): Promise<CoreConversationPayloadResult> {
  const current = adapter;
  if (!current) {
    if (isControlledTestMode()) return controlledTestPayload(operation, context);
    return { ok: false, reason_code: `CONVERSATION_${operation}_REGISTERED_SCHEMA_ADAPTER_NOT_BOUND` };
  }
  try {
    const result = await build(current);
    if (!result.ok) return result;
    if (!validPayload(result.payload)) return { ok: false, reason_code: `CONVERSATION_${operation}_REGISTERED_SCHEMA_PAYLOAD_EMPTY` };
    return result;
  } catch {
    return { ok: false, reason_code: `CONVERSATION_${operation}_REGISTERED_SCHEMA_ADAPTER_FAILED` };
  }
}

export function requestCoreThreadCreatePayload(context: CoreThreadPayloadContext) {
  return normalize("THREAD_CREATE", context, (current) => current.buildThreadCreatePayload(context));
}

export function requestCoreMessageSendPayload(context: CoreMessagePayloadContext) {
  return normalize("MESSAGE_SEND", context, (current) => current.buildMessageSendPayload(context));
}
