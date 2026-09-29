import type { CoreExactRefs } from "./coreClientState";

export type CoreProjectOption = { project_id: string; project_version_ref: string | null; project_version_no: number | null; workspace_id: string; status: string; label: string };
export type CoreTopicOption = { topic_id: string; topic_version_ref: string | null; project_id: string; label: string; blueprint_version_ref: string | null; blueprint_version_no: number | null; blueprint_status: string | null; topic_scope_ref: string | null };
export type CoreLockCriteriaOption = { criteria_version_id: string; label: string };
export type CoreWorkItemOption = { work_item: string; label: string };
export type CoreThreadOption = { conversation_id: string; label: string; project_id: string; topic_id: string | null; work_item: string; parent_conversation_id?: string | null; source_message_id?: string | null; relation_kind?: "ROOT" | "BRANCH" };
export type CoreConversationProjectionMessage = {
  message_ref: string;
  conversation_id: string;
  role: "USER" | "ASSISTANT" | "SYSTEM";
  text: string;
};

export type CoreNormalizedProjection = {
  refs: Partial<CoreExactRefs>;
  work_item: string | null;
  projects: readonly CoreProjectOption[];
  topics: readonly CoreTopicOption[];
  work_items: readonly CoreWorkItemOption[];
  threads: readonly CoreThreadOption[];
  messages_by_thread?: Readonly<Record<string, readonly CoreConversationProjectionMessage[]>>;
  lock_context: {
    approved_criteria: readonly CoreLockCriteriaOption[];
    eligible_reviewer_count: number;
  };
  display_values: Readonly<Record<string, string>>;
};

export type CoreProjectionResolver = {
  resolve: (rawProjection: unknown) => Promise<CoreNormalizedProjection> | CoreNormalizedProjection;
};

export type CoreProjectionResolveResult =
  | { ok: true; projection: CoreNormalizedProjection }
  | { ok: false; reason_code: string };

let resolver: CoreProjectionResolver | null = null;

export function configureCoreProjectionResolver(next: CoreProjectionResolver) {
  resolver = next;
}

export function isCoreProjectionResolverBound() {
  return resolver !== null;
}

function validText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validNullableText(value: unknown): value is string | null | undefined {
  return value === undefined || value === null || validText(value);
}

function validateProjection(value: CoreNormalizedProjection): boolean {
  if (!value || typeof value !== "object") return false;
  const refs = value.refs ?? {};
  for (const ref of Object.values(refs)) if (!validNullableText(ref)) return false;
  if (!validNullableText(value.work_item)) return false;
  if (!Array.isArray(value.projects) || value.projects.some(item => !validText(item.project_id) || !validNullableText(item.project_version_ref) || (item.project_version_no !== null && (!Number.isInteger(item.project_version_no) || item.project_version_no < 1)) || !validText(item.workspace_id) || !validText(item.status) || !validText(item.label))) return false;
  if (!Array.isArray(value.topics) || value.topics.some(item => !validText(item.topic_id) || !validNullableText(item.topic_version_ref) || !validText(item.project_id) || !validText(item.label) || !validNullableText(item.blueprint_version_ref) || (item.blueprint_version_no !== null && (!Number.isInteger(item.blueprint_version_no) || item.blueprint_version_no < 1)) || !validNullableText(item.blueprint_status) || !validNullableText(item.topic_scope_ref))) return false;
  if (!Array.isArray(value.work_items) || value.work_items.some(item => !validText(item.work_item) || !validText(item.label))) return false;
  if (!Array.isArray(value.threads) || value.threads.some(item => !validText(item.conversation_id) || !validText(item.label) || !validText(item.project_id) || !validText(item.work_item) || !validNullableText(item.topic_id) || (item.relation_kind !== undefined && !["ROOT","BRANCH"].includes(item.relation_kind)))) return false;
  if (!value.lock_context || !Array.isArray(value.lock_context.approved_criteria) || value.lock_context.approved_criteria.some(item => !validText(item.criteria_version_id) || !validText(item.label)) || !Number.isInteger(value.lock_context.eligible_reviewer_count) || value.lock_context.eligible_reviewer_count < 0) return false;
  if (value.messages_by_thread !== undefined) {
    if (!value.messages_by_thread || typeof value.messages_by_thread !== "object" || Array.isArray(value.messages_by_thread)) return false;
    for (const [conversationId, messages] of Object.entries(value.messages_by_thread)) {
      if (!validText(conversationId) || !Array.isArray(messages)) return false;
      if (messages.some((item) =>
        !validText(item.message_ref)
        || item.conversation_id !== conversationId
        || !["USER", "ASSISTANT", "SYSTEM"].includes(item.role)
        || typeof item.text !== "string"
      )) return false;
    }
  }
  if (!value.display_values || typeof value.display_values !== "object" || Object.values(value.display_values).some(item => typeof item !== "string")) return false;
  return true;
}

function controlledTestProjection(rawProjection: unknown): CoreProjectionResolveResult {
  if (!rawProjection || typeof rawProjection !== "object") return { ok: false, reason_code: "CORE_TEST_PROJECTION_INVALID" };
  const projection = rawProjection as CoreNormalizedProjection;
  if (!validateProjection(projection)) return { ok: false, reason_code: "CORE_TEST_PROJECTION_SCHEMA_REJECTED" };
  return { ok: true, projection };
}

export async function resolveCoreProjection(rawProjection: unknown): Promise<CoreProjectionResolveResult> {
  const current = resolver;
  if (!current) {
    return controlledTestProjection(rawProjection);
  }
  try {
    const projection = await current.resolve(rawProjection);
    if (!validateProjection(projection)) return { ok: false, reason_code: "CORE_PROJECTION_SCHEMA_ADAPTER_REJECTED" };
    return { ok: true, projection };
  } catch {
    return { ok: false, reason_code: "CORE_PROJECTION_SCHEMA_ADAPTER_FAILED" };
  }
}
