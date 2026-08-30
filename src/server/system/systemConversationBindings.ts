export type SystemConversationAttachmentRequest = {
  system_change_id: string;
  conversation_id: string;
  thread_id: string | null;
  branch_id: string | null;
  source_ref: string;
};

export type SystemConversationAttachmentBinding = {
  resolveAndAttach: (request: SystemConversationAttachmentRequest) => Promise<{ ok: true; attachment_ref: string } | { ok: false; reason_code: string }>;
};

let attachmentBinding: SystemConversationAttachmentBinding | null = null;

export function configureSystemConversationAttachmentBinding(next: SystemConversationAttachmentBinding): void {
  attachmentBinding = next;
}

export async function attachSystemConversationReference(request: SystemConversationAttachmentRequest) {
  if (!attachmentBinding) {
    return { ok: false as const, reason_code: "CONVERSATION_ATTACHMENT_BINDING_NOT_RESOLVED" };
  }
  return attachmentBinding.resolveAndAttach(request).catch(() => ({ ok: false as const, reason_code: "CONVERSATION_ATTACHMENT_FAILED" }));
}

export async function sendSystemConversationMessage(input: {
  conversation_id: string;
  system_change_id: string;
  thread_id: string | null;
  branch_id: string | null;
  draft: string;
  attachment_refs: string[];
  signal?: AbortSignal;
}) {
  if (!input.conversation_id || !input.system_change_id || !input.draft.trim()) {
    return { ok: false as const, reason_code: "SYSTEM_CONVERSATION_CONTEXT_OR_MESSAGE_MISSING" };
  }
  try {
    const response = await fetch(`/v1/conversations/${encodeURIComponent(input.conversation_id)}/messages`, {
      method: "POST",
      cache: "no-store",
      signal: input.signal,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        system_change_id: input.system_change_id,
        thread_id: input.thread_id,
        branch_id: input.branch_id,
        message: input.draft,
        attachment_refs: input.attachment_refs,
      }),
    });
    const value: unknown = await response.json().catch(() => null);
    return response.ok ? { ok: true as const, value } : { ok: false as const, reason_code: "SYSTEM_CONVERSATION_SEND_FAILED", value };
  } catch {
    return { ok: false as const, reason_code: "SYSTEM_CONVERSATION_SEND_FAILED" };
  }
}

export async function stopSystemConversationGeneration(input: { conversation_id: string; signal?: AbortSignal }) {
  if (!input.conversation_id) return { ok: false as const, reason_code: "ACTIVE_CONVERSATION_CONTEXT_MISSING" };
  try {
    const response = await fetch(`/v1/conversations/${encodeURIComponent(input.conversation_id)}/generation/stop`, {
      method: "POST",
      cache: "no-store",
      signal: input.signal,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    const value: unknown = await response.json().catch(() => null);
    return response.ok ? { ok: true as const, value } : { ok: false as const, reason_code: "SYSTEM_CONVERSATION_STOP_FAILED", value };
  } catch {
    return { ok: false as const, reason_code: "SYSTEM_CONVERSATION_STOP_FAILED" };
  }
}
