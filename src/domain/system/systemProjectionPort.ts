import { isControlledTestMode } from "@/domain/testing/controlledTestData";

export type SystemProjectionTestMetadata = {
  data_classification: "TEST_ONLY";
  synthetic: true;
  test_dataset_id: string;
  test_run_id: string;
  created_for_validation: true;
  production_eligible: false;
};

export type SystemConversationProjectionMessage = {
  message_ref: string;
  role: "USER" | "ASSISTANT" | "SYSTEM";
  text: string;
  assistant_summary: string | null;
  response_mode: string | null;
  governance_status: string | null;
};

export type SystemNormalizedProjection = {
  page_state: "READY" | "EMPTY" | "ERROR/BLOCKED";
  system_change_id: string | null;
  conversation_id: string | null;
  thread_id: string | null;
  branch_id: string | null;
  multi_ai_route_available: boolean;
  messages: SystemConversationProjectionMessage[];
  values: Record<string, string>;
  test_metadata?: SystemProjectionTestMetadata;
};

export type SystemProjectionResult =
  | { ok: true; projection: SystemNormalizedProjection; correlation_id: string | null }
  | { ok: false; status: number; reason_code: string; correlation_id: string | null };

function rec(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function nullable(value: unknown): boolean {
  return value === null || typeof value === "string";
}

function normalizeMessage(value: unknown): SystemConversationProjectionMessage | null {
  const item = rec(value);
  if (!item) return null;
  if (
    typeof item.message_ref !== "string"
    || !["USER", "ASSISTANT", "SYSTEM"].includes(String(item.role))
    || typeof item.text !== "string"
    || !nullable(item.assistant_summary)
    || !nullable(item.response_mode)
    || !nullable(item.governance_status)
  ) return null;
  return {
    message_ref: item.message_ref,
    role: item.role as SystemConversationProjectionMessage["role"],
    text: item.text,
    assistant_summary: item.assistant_summary as string | null,
    response_mode: item.response_mode as string | null,
    governance_status: item.governance_status as string | null,
  };
}

function normalize(raw: unknown): SystemNormalizedProjection | null {
  const value = rec(raw);
  if (!value) return null;
  if (
    !(value.page_state === "READY" || value.page_state === "EMPTY" || value.page_state === "ERROR/BLOCKED")
    || !nullable(value.system_change_id)
    || !nullable(value.conversation_id)
    || !nullable(value.thread_id)
    || !nullable(value.branch_id)
    || typeof value.multi_ai_route_available !== "boolean"
  ) return null;

  const values = rec(value.values);
  if (!values || !Object.values(values).every((item) => typeof item === "string")) return null;

  const messagesRaw = Array.isArray(value.messages) ? value.messages : [];
  const messages = messagesRaw.map(normalizeMessage);
  if (messages.some((item) => item === null)) return null;

  let test_metadata: SystemProjectionTestMetadata | undefined;
  if (value.test_metadata !== undefined) {
    const metadata = rec(value.test_metadata);
    if (
      !metadata
      || metadata.data_classification !== "TEST_ONLY"
      || metadata.synthetic !== true
      || typeof metadata.test_dataset_id !== "string"
      || typeof metadata.test_run_id !== "string"
      || metadata.created_for_validation !== true
      || metadata.production_eligible !== false
      || !isControlledTestMode()
    ) return null;
    test_metadata = metadata as unknown as SystemProjectionTestMetadata;
  }

  return {
    page_state: value.page_state,
    system_change_id: value.system_change_id as string | null,
    conversation_id: value.conversation_id as string | null,
    thread_id: value.thread_id as string | null,
    branch_id: value.branch_id as string | null,
    multi_ai_route_available: value.multi_ai_route_available,
    messages: messages as SystemConversationProjectionMessage[],
    values: values as Record<string, string>,
    test_metadata,
  };
}

export async function readSystemProjection(signal?: AbortSignal): Promise<SystemProjectionResult> {
  try {
    const response = await fetch("/v1/ui-projections/admin%3ASYS-01", {
      method: "GET",
      cache: "no-store",
      credentials: "include",
      signal,
      headers: { accept: "application/json" },
    });
    const correlation_id = response.headers.get("x-correlation-id");
    const raw: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const body = rec(raw);
      return {
        ok: false,
        status: response.status,
        reason_code: typeof body?.reason_code === "string" ? body.reason_code : "UI_PROJECTION_READ_FAILED",
        correlation_id,
      };
    }
    const projection = normalize(raw);
    return projection
      ? { ok: true, projection, correlation_id }
      : { ok: false, status: 503, reason_code: "SYS_PROJECTION_CONTRACT_REJECTED", correlation_id };
  } catch {
    return { ok: false, status: 503, reason_code: "UI_PROJECTION_READ_FAILED", correlation_id: null };
  }
}
