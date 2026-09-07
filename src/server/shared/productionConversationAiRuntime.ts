import { executeProductionAiApiCommand } from "@/server/aiApi/productionAiApiCommandRuntime";
import { getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

export type ProductionConversationTurnInput = {
  conversation_id: string;
  actor_user_id: string;
  session_token_hash: string;
  message: string;
  correlation_id: string;
  instruction_kind?: string | null;
  source_message_id?: string | null;
  attachment_refs?: readonly string[];
  reference_refs?: readonly string[];
  page_uid?: string | null;
};

function asRecord(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}

function asText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function first(rows: unknown): Row | null {
  return Array.isArray(rows) ? (asRecord(rows[0]) ?? null) : null;
}

async function requireConversationContext(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
) {
  const rows = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT
        c.conversation_id::text AS conversation_id,
        c.project_id::text AS project_id,
        c.topic_id::text AS topic_id,
        c.workspace_id::text AS workspace_id,
        c.title
      FROM conversations c
      WHERE c.conversation_id = ${input.conversation_id}::uuid
      LIMIT 1
    `,
  );
  const row = first(rows);
  if (!asText(row?.conversation_id)) throw new NamedRuntimeError("CONVERSATION_NOT_FOUND");
  return {
    project_id: asText(row?.project_id),
    topic_id: asText(row?.topic_id),
    workspace_id: asText(row?.workspace_id),
    title: asText(row?.title),
  };
}

async function nextSequence(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<number> {
  const rows = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT COALESCE(MAX(sequence_no), 0)::int AS seq
      FROM conversation_messages
      WHERE conversation_id = ${input.conversation_id}::uuid
    `,
  );
  return Number(first(rows)?.seq ?? 0) + 1;
}

async function insertUserMessage(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<string> {
  const messageRef = crypto.randomUUID();
  const seq = await nextSequence(sql, input);
  const content = JSON.stringify({
    text: input.message,
    instruction_kind: input.instruction_kind ?? "MESSAGE",
    source_message_id: input.source_message_id ?? null,
    attachment_refs: [...(input.attachment_refs ?? [])],
    reference_refs: [...(input.reference_refs ?? [])],
  });
  const rows = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      INSERT INTO conversation_messages(
        conversation_message_id, conversation_id, sequence_no, actor_type, actor_ref, message_content
      ) VALUES(
        ${messageRef}::uuid,
        ${input.conversation_id}::uuid,
        ${seq},
        'USER',
        ${input.actor_user_id},
        ${content}::jsonb
      )
      RETURNING conversation_message_id::text AS message_ref
    `,
  );
  if (!asText(first(rows)?.message_ref)) throw new NamedRuntimeError("MESSAGE_INSERT_FAILED");
  return messageRef;
}

async function sourceMessageText(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<string | null> {
  if (!input.source_message_id) return null;
  const rows = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT left(COALESCE(message_content->>'text',''), 4000) AS text
      FROM conversation_messages
      WHERE conversation_id = ${input.conversation_id}::uuid
        AND conversation_message_id = ${input.source_message_id}::uuid
      LIMIT 1
    `,
  );
  return asText(first(rows)?.text);
}

async function transcript(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<string> {
  const rows = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT sequence_no, actor_type, actor_ref,
             left(COALESCE(message_content->>'text',''), 4000) AS text
      FROM conversation_messages
      WHERE conversation_id = ${input.conversation_id}::uuid
      ORDER BY sequence_no DESC
      LIMIT 20
    `,
  );
  const list = (Array.isArray(rows) ? rows : [])
    .map(asRecord)
    .filter((row) => asText(row.text))
    .reverse();
  return list.map((row) => {
    const actorType = asText(row.actor_type);
    const label = actorType === "USER" ? "User"
      : actorType === "PROVIDER" ? "Assistant"
      : actorType === "SYSTEM" ? "System"
      : "Service";
    return `${label}: ${asText(row.text) ?? ""}`;
  }).join("\n");
}

async function resolveTextChatGroup(sql: SqlClient): Promise<string> {
  const rows = await sql`
    SELECT id
    FROM acpos_runtime.provider_groups
    WHERE enabled = true
      AND use_case = 'ACPOS_TEXT_CHAT'
    ORDER BY updated_at DESC, id
    LIMIT 1
  `;
  const groupId = asText(first(rows)?.id);
  if (!groupId) throw new NamedRuntimeError("CONVERSATION_PROVIDER_GROUP_NOT_CONFIGURED");
  return groupId;
}

async function routeAssistant(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  conversationContext: Awaited<ReturnType<typeof requireConversationContext>>,
) {
  const history = await transcript(sql, input);
  const source = input.instruction_kind === "ANALYZE"
    ? await sourceMessageText(sql, input)
    : null;
  const groupId = await resolveTextChatGroup(sql);
  const task = source
    ? `Analyze this exact prior message and answer in the conversation context:\n${source}`
    : "Reply to the latest user message.";
  const canonicalInstruction = [
    "Continue the ACPOS conversation using the existing conversation history.",
    "Respond in the language used by the user unless the user asks for another language.",
    "Do not invent project facts that are absent from the supplied conversation context.",
    task,
    "",
    "Conversation history:",
    history,
  ].join("\n");

  const route = asRecord(await executeProductionAiApiCommand({
    operation_id: "executeProviderRoute",
    correlation_id: input.correlation_id,
    path_params: {},
    payload: {
      candidate_group_id: groupId,
      required_capability: "TEXT_CHAT",
      use_case: "ACPOS_CONVERSATION",
      data_classification: "INTERNAL",
      canonical_instruction: canonicalInstruction,
      scoped_context: {
        conversation_id: input.conversation_id,
        project_id: conversationContext.project_id,
        topic_id: conversationContext.topic_id,
        workspace_id: conversationContext.workspace_id,
        page_uid: input.page_uid ?? null,
        instruction_kind: input.instruction_kind ?? "MESSAGE",
      },
    },
  }));

  if (asText(route.status) !== "SUCCESS" || route.external_request_sent !== true) {
    throw new NamedRuntimeError(
      asText(route.reason) ?? "CONVERSATION_PROVIDER_ROUTE_NOT_SUCCESSFUL",
    );
  }
  const decisionId = asText(route.route_decision_id);
  if (!decisionId) throw new NamedRuntimeError("CONVERSATION_ROUTE_DECISION_ID_MISSING");

  const decision = asRecord(await executeProductionAiApiCommand({
    operation_id: "getProviderRouteDecision",
    correlation_id: input.correlation_id,
    path_params: { routeDecisionId: decisionId },
    payload: {},
  }));
  const payload = asRecord(decision.payload);
  const assistantText = asText(payload.normalized_result);
  const providerId = asText(decision.provider_id);
  const modelId = asText(decision.model_id);
  if (asText(decision.status) !== "SUCCESS" || payload.external_request_sent !== true) {
    throw new NamedRuntimeError("CONVERSATION_ROUTE_DECISION_NOT_SUCCESSFUL");
  }
  if (!assistantText || !providerId || !modelId) {
    throw new NamedRuntimeError("CONVERSATION_ASSISTANT_RESULT_MISSING");
  }
  return {
    assistantText,
    providerId,
    modelId,
    decisionId,
    resultHash: asText(payload.result_hash),
    workerSucceeded: asRecord(route.worker).succeeded === 1,
  };
}

async function insertAssistantMessage(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  userMessageRef: string,
  routed: Awaited<ReturnType<typeof routeAssistant>>,
): Promise<string> {
  const assistantRef = crypto.randomUUID();
  const seq = await nextSequence(sql, input);
  const content = JSON.stringify({
    text: routed.assistantText,
    route_decision_id: routed.decisionId,
    provider_id: routed.providerId,
    model_id: routed.modelId,
    result_hash: routed.resultHash,
    source_message_ref: userMessageRef,
    external_request_sent: true,
  });
  const rows = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      INSERT INTO conversation_messages(
        conversation_message_id, conversation_id, sequence_no, actor_type, actor_ref, message_content
      ) VALUES(
        ${assistantRef}::uuid,
        ${input.conversation_id}::uuid,
        ${seq},
        'PROVIDER',
        ${`${routed.providerId}:${routed.modelId}`},
        ${content}::jsonb
      )
      RETURNING conversation_message_id::text AS assistant_response_ref
    `,
  );
  if (!asText(first(rows)?.assistant_response_ref)) {
    throw new NamedRuntimeError("CONVERSATION_ASSISTANT_MESSAGE_INSERT_FAILED");
  }
  return assistantRef;
}

export async function executeProductionConversationTurn(
  input: ProductionConversationTurnInput,
): Promise<unknown> {
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const message = input.message.trim();
  if (!message) throw new NamedRuntimeError("MESSAGE_REQUIRED");

  const context = await requireConversationContext(sql, input);
  const messageRef = await insertUserMessage(sql, { ...input, message });
  const routed = await routeAssistant(sql, { ...input, message }, context);
  const assistantRef = await insertAssistantMessage(
    sql,
    { ...input, message },
    messageRef,
    routed,
  );

  return {
    conversation_id: input.conversation_id,
    message_ref: messageRef,
    accepted: true,
    assistant_response_ref: assistantRef,
    assistant_response_text: routed.assistantText,
    provider_id: routed.providerId,
    model_id: routed.modelId,
    route_decision_id: routed.decisionId,
    result_hash: routed.resultHash,
    external_request_sent: true,
    worker_succeeded: routed.workerSucceeded ? 1 : 0,
  };
}
