import { createHash } from "node:crypto";
import { executeProductionAiApiCommand } from "@/server/aiApi/productionAiApiCommandRuntime";
import { getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { getDeploymentMetadata } from "@/server/shared/deploymentMetadata";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import {
  ACPOS_AI_GOVERNANCE_POLICY_VERSION,
  ACPOS_AI_RESPONSE_POLICY,
  ACPOS_AI_RESPONSE_SCHEMA,
  parseAcposGovernedAiResponse,
  renderAcposGovernedAiResponse,
  validateDecisionUpdatesAgainstUserMessage,
  type AcposGovernedAiResponse,
} from "@/server/shared/acposAiGovernancePolicy";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;
type AiMode = "SINGLE_AI" | "MULTI_AI";
type CouncilMode = "DISCUSSION" | "PARALLEL";

type ConversationContext = {
  conversation_id: string;
  project_id: string | null;
  topic_id: string | null;
  workspace_id: string;
  title: string | null;
};

type EvidenceItem = {
  ref: string;
  kind: "MESSAGE" | "EVIDENCE_RECORD" | "REFERENCE" | "ATTACHMENT";
  resolved: boolean;
  content?: unknown;
};

type GovernanceContext = {
  policy_version: typeof ACPOS_AI_GOVERNANCE_POLICY_VERSION;
  system_truth: unknown;
  page_policy: readonly string[];
  page_context: unknown;
  conversation: {
    conversation_id: string;
    title: string | null;
    recent_history: Array<{ message_ref: string; role: string; text: string }>;
    source_refs: EvidenceItem[];
  };
  decisions: Array<{
    decision_key: string;
    status: string;
    statement: string;
    user_quote: string | null;
    decision_ref: string | null;
  }>;
  affected_scope: unknown;
  validation: unknown;
  deployment: unknown;
  latest_context_fingerprint: string;
};

type RoutedText = {
  text: string;
  providerId: string;
  modelId: string;
  decisionId: string;
  resultHash: string | null;
  workerSucceeded: boolean;
};

type GovernedRoute = RoutedText & {
  governed: AcposGovernedAiResponse;
  renderedText: string;
  governanceRepairUsed: boolean;
};

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
  ai_mode?: string | null;
  council_mode?: string | null;
  system_change_id?: string | null;
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

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

function truncate(value: string, max = 4000): string {
  return value.length <= max ? value : `${value.slice(0, max)}…`;
}

function stableHash(value: unknown): string {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function normalizeAiMode(value: string | null | undefined): AiMode {
  return value === "MULTI_AI" || value === "MULTI" ? "MULTI_AI" : "SINGLE_AI";
}

function normalizeCouncilMode(value: string | null | undefined): CouncilMode {
  return value === "PARALLEL" ? "PARALLEL" : "DISCUSSION";
}

function pagePolicy(pageUid: string | null | undefined): readonly string[] {
  if (pageUid === "admin:SYS-01") {
    return [
      "Maintain one SYSTEM_CHANGE_ID across discussion, requirement, decision, design, implementation, validation, approval/deploy boundary and closure.",
      "Resolve Current System Truth, active change, confirmed decisions, owners and context fingerprint before proposing a system mutation.",
      "Only true P0/P1 questions go to the human. P2 must be resolved from existing ACPOS truth; P3 uses an existing safe default and records the assumption.",
      "Do not merely execute a user statement: identify dependencies, conflicts, missing information, risks and alternatives first.",
      "Use existing-system resolution order and REUSE -> EXTEND -> MODIFY -> REPLACE -> CREATE_NEW. Parallel ACPOS systems are forbidden.",
      "MULTI_AI Discussion performs propose -> review -> compare -> revise -> synthesize -> decision questions under one context.",
      "MULTI_AI Parallel performs independent first-round answers from the same original question/context/evidence, then synthesis.",
      "AI may detect, diff, analyze impact and draft a candidate. AI may not substitute human approval or autonomously deploy to Production.",
    ];
  }
  if (pageUid === "CORE-01") {
    return [
      "Single AI and Multi AI share the same Project/Topic/work-item/thread context. Provider/model picking is system-owned.",
      "Raw AI responses are discussion material only and must not directly write formal CORE data.",
      "CORE decision flow is AI_RESPONSES -> ASSISTANT_SUMMARY -> CORE_EVALUATION -> HUMAN_DECISION -> ASSISTANT_STRUCTURED_DECISION -> CANDIDATE_CREATE -> CANDIDATE_DECISION -> DOMAIN_REVIEW if applicable.",
      "Assistant Summary must be traceable to source response refs. Human Decision remains human-owned.",
      "Do not mix another work item/thread context. Do not fabricate Project/Topic/version/lock/naming refs.",
    ];
  }
  if (pageUid === "workspace:STR-01" || pageUid === "admin:STR-01") {
    return [
      "Never present inference as Fact. Fact, Source Health and Confidence require registered evidence/projection truth.",
      "A Strategy Candidate is not an approved Strategy Decision.",
      "Playbook is not a publish command. Opportunity cannot automatically change Project or budget. Decision Lab cannot directly write canon lock/task/budget/publish state.",
      "Existing read-model context is carried forward; do not ask the user to retype known system data.",
      "Unresolved operations/owners are not inferred; resolve from Current registry or mark unresolved.",
    ];
  }
  return [
    "Preserve the exact current ACPOS page/project/topic/conversation context.",
    "No unregistered business mutation or parallel ACPOS owner may be created from a conversation response.",
  ];
}

async function requireConversationContext(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<ConversationContext> {
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
  const conversationId = asText(row?.conversation_id);
  const workspaceId = asText(row?.workspace_id);
  if (!conversationId || !workspaceId) throw new NamedRuntimeError("CONVERSATION_NOT_FOUND");
  return {
    conversation_id: conversationId,
    project_id: asText(row?.project_id),
    topic_id: asText(row?.topic_id),
    workspace_id: workspaceId,
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
    attachment_refs: [...(input.attachment_refs ?? [])],
    reference_refs: [...(input.reference_refs ?? [])],
    source_message_id: input.source_message_id ?? null,
    ai_mode: normalizeAiMode(input.ai_mode),
    council_mode: normalizeCouncilMode(input.council_mode),
    system_change_id: input.system_change_id ?? null,
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

async function recentHistory(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<Array<{ message_ref: string; role: string; text: string }>> {
  const rows = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT conversation_message_id::text AS message_ref,
             actor_type,
             left(COALESCE(message_content->>'text',''), 2200) AS text,
             COALESCE(message_content->>'kind','') AS kind
      FROM conversation_messages
      WHERE conversation_id = ${input.conversation_id}::uuid
      ORDER BY sequence_no DESC
      LIMIT 30
    `,
  );
  return (Array.isArray(rows) ? rows : [])
    .map(asRecord)
    .filter((row) => asText(row.kind) !== "DECISION_LEDGER")
    .filter((row) => asText(row.text))
    .slice(0, 20)
    .reverse()
    .map((row) => ({
      message_ref: asText(row.message_ref) ?? "UNRESOLVED",
      role: asText(row.actor_type) === "USER" ? "USER"
        : asText(row.actor_type) === "PROVIDER" ? "ASSISTANT"
        : "SYSTEM",
      text: asText(row.text) ?? "",
    }));
}

async function loadDecisionLedger(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<GovernanceContext["decisions"]> {
  const rows = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT conversation_message_id::text AS ledger_message_ref,
             message_content->'entries' AS entries
      FROM conversation_messages
      WHERE conversation_id = ${input.conversation_id}::uuid
        AND actor_type = 'SYSTEM'
        AND message_content->>'kind' = 'DECISION_LEDGER'
      ORDER BY sequence_no ASC
      LIMIT 80
    `,
  ).catch(() => []);

  const latest = new Map<string, GovernanceContext["decisions"][number]>();
  for (const raw of Array.isArray(rows) ? rows : []) {
    const row = asRecord(raw);
    const messageRef = asText(row.ledger_message_ref);
    const entries = Array.isArray(row.entries) ? row.entries : [];
    for (const rawEntry of entries) {
      const entry = asRecord(rawEntry);
      const key = asText(entry.decision_key);
      const status = asText(entry.status);
      const statement = asText(entry.statement);
      if (!key || !status || !statement) continue;
      latest.set(key, {
        decision_key: key,
        status,
        statement,
        user_quote: asText(entry.user_quote),
        decision_ref: asText(entry.decision_ref) ?? messageRef,
      });
    }
  }
  return [...latest.values()];
}

async function resolveEvidence(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<EvidenceItem[]> {
  const items: EvidenceItem[] = [];
  if (input.source_message_id && isUuid(input.source_message_id)) {
    const rows = await runRlsActorQuery(
      sql,
      input.session_token_hash,
      sql`
        SELECT conversation_message_id::text AS ref,
               left(COALESCE(message_content->>'text',''), 4000) AS text
        FROM conversation_messages
        WHERE conversation_id = ${input.conversation_id}::uuid
          AND conversation_message_id = ${input.source_message_id}::uuid
        LIMIT 1
      `,
    ).catch(() => []);
    const row = first(rows);
    items.push({
      ref: input.source_message_id,
      kind: "MESSAGE",
      resolved: Boolean(asText(row?.ref)),
      content: asText(row?.text) ?? undefined,
    });
  }

  const uniqueReferences = [...new Set(input.reference_refs ?? [])].slice(0, 10);
  for (const ref of uniqueReferences) {
    if (!isUuid(ref)) {
      items.push({ ref, kind: "REFERENCE", resolved: false });
      continue;
    }
    const rows = await runRlsActorQuery(
      sql,
      input.session_token_hash,
      sql`
        SELECT evidence_record_id::text AS ref,
               source_uri,
               classification::text AS classification,
               citation,
               normalized_content
        FROM evidence_records
        WHERE evidence_record_id = ${ref}::uuid
        LIMIT 1
      `,
    ).catch(() => []);
    const row = first(rows);
    items.push({
      ref,
      kind: "EVIDENCE_RECORD",
      resolved: Boolean(asText(row?.ref)),
      content: row
        ? {
            source_uri: asText(row.source_uri),
            classification: asText(row.classification),
            citation: row.citation ?? null,
            normalized_content: truncate(JSON.stringify(row.normalized_content ?? null), 5000),
          }
        : undefined,
    });
  }

  for (const ref of [...new Set(input.attachment_refs ?? [])].slice(0, 10)) {
    items.push({ ref, kind: "ATTACHMENT", resolved: false });
  }
  return items;
}

async function loadProjectTopicTruth(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  context: ConversationContext,
): Promise<unknown> {
  const project = context.project_id
    ? first(await runRlsActorQuery(
        sql,
        input.session_token_hash,
        sql`
          SELECT project_id::text AS project_id,project_code,title,status::text AS status,
                 active_version_id::text AS active_version_id,workspace_id::text AS workspace_id
          FROM projects
          WHERE project_id=${context.project_id}::uuid
          LIMIT 1
        `,
      ).catch(() => []))
    : null;
  const topic = context.topic_id
    ? first(await runRlsActorQuery(
        sql,
        input.session_token_hash,
        sql`
          SELECT topic_id::text AS topic_id,project_id::text AS project_id,topic_code,title,
                 status::text AS status,active_version_id::text AS active_version_id,
                 mother_lock_id::text AS mother_lock_id
          FROM topics
          WHERE topic_id=${context.topic_id}::uuid
          LIMIT 1
        `,
      ).catch(() => []))
    : null;
  return { project, topic };
}

async function loadSystemChangeTruth(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
): Promise<unknown> {
  if (!input.system_change_id || !isUuid(input.system_change_id)) return null;
  const changes = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT system_change_id::text AS system_change_id,current_goal,scope,status,
             current_candidate_id::text AS current_candidate_id,created_at::text AS created_at,updated_at::text AS updated_at
      FROM system_changes
      WHERE system_change_id=${input.system_change_id}::uuid
      LIMIT 1
    `,
  ).catch(() => []);
  const change = first(changes);
  if (!change) return null;
  const candidates = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT system_change_candidate_id::text AS candidate_ref,context_fingerprint,status,created_at::text AS created_at
      FROM system_change_candidates
      WHERE system_change_id=${input.system_change_id}::uuid
      ORDER BY created_at DESC
      LIMIT 5
    `,
  ).catch(() => []);
  const requests = await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      SELECT system_change_request_id::text AS request_ref,system_change_candidate_id::text AS candidate_ref,
             reason,impact_scope,status,created_at::text AS created_at
      FROM system_change_requests
      WHERE system_change_id=${input.system_change_id}::uuid
      ORDER BY created_at DESC
      LIMIT 5
    `,
  ).catch(() => []);
  return { change, candidates, requests };
}

async function loadRuntimeTruth(sql: SqlClient): Promise<unknown> {
  const deployment = getDeploymentMetadata();
  const [migrations, profiles, groups, routes] = await Promise.all([
    sql`
      SELECT count(*)::int AS count,
             (SELECT migration_id FROM schema_migration_history ORDER BY applied_at DESC LIMIT 1) AS latest_migration
      FROM schema_migration_history
    `.catch(() => []),
    sql`
      SELECT id,provider_id,model_id,enabled,health_status
      FROM acpos_runtime.provider_profiles
      WHERE enabled=true
      ORDER BY provider_id,model_id
    `.catch(() => []),
    sql`
      SELECT id,use_case,enabled
      FROM acpos_runtime.provider_groups
      WHERE enabled=true
      ORDER BY id
    `.catch(() => []),
    sql`
      SELECT status,provider_id,model_id,created_at::text AS created_at
      FROM acpos_runtime.provider_route_decisions
      ORDER BY created_at DESC
      LIMIT 5
    `.catch(() => []),
  ]);
  return {
    deployment,
    database: {
      migration_count: Number(first(migrations)?.count ?? 0),
      latest_migration: asText(first(migrations)?.latest_migration),
    },
    registered_owners: {
      conversation: "ACPOS AI Conversation Core / public.conversations + public.conversation_messages",
      provider: "AIAPI / acpos_runtime.provider_profiles + provider_capabilities + secret_references",
      queue_worker: "ACPOS async queue/worker runtime",
      permission: "Account Permission Assignment / permission_resources",
      audit: "audit_events",
      candidate: "existing domain Candidate owners only",
    },
    providers: Array.isArray(profiles) ? profiles : [],
    provider_groups: Array.isArray(groups) ? groups : [],
    recent_provider_routes: Array.isArray(routes) ? routes : [],
  };
}

async function buildGovernanceContext(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  context: ConversationContext,
): Promise<GovernanceContext> {
  const [history, decisions, evidence, projectTopic, systemChange, systemTruth] = await Promise.all([
    recentHistory(sql, input),
    loadDecisionLedger(sql, input),
    resolveEvidence(sql, input),
    loadProjectTopicTruth(sql, input, context),
    loadSystemChangeTruth(sql, input),
    loadRuntimeTruth(sql),
  ]);
  const deployment = getDeploymentMetadata();
  const payload = {
    policy_version: ACPOS_AI_GOVERNANCE_POLICY_VERSION,
    system_truth: systemTruth,
    page_policy: pagePolicy(input.page_uid),
    page_context: {
      page_uid: input.page_uid ?? null,
      project_topic: projectTopic,
      system_change: systemChange,
    },
    conversation: {
      conversation_id: context.conversation_id,
      title: context.title,
      recent_history: history,
      source_refs: evidence,
    },
    decisions,
    affected_scope: {
      workspace_id: context.workspace_id,
      project_id: context.project_id,
      topic_id: context.topic_id,
      system_change_id: input.system_change_id ?? null,
      page_uid: input.page_uid ?? null,
      attachment_refs: [...(input.attachment_refs ?? [])],
      reference_refs: [...(input.reference_refs ?? [])],
    },
    validation: {
      unresolved_source_refs: evidence.filter((item) => !item.resolved).map((item) => item.ref),
      source_evidence_count: evidence.filter((item) => item.resolved).length,
    },
    deployment: {
      environment: deployment.environment,
      release_sha: deployment.release_sha,
    },
  };
  return { ...payload, latest_context_fingerprint: stableHash(payload) };
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

async function executeTextRoute(
  groupId: string,
  input: ProductionConversationTurnInput,
  canonicalInstruction: string,
  useCase: string,
  scopedContext: Record<string, unknown>,
): Promise<RoutedText> {
  const route = asRecord(await executeProductionAiApiCommand({
    operation_id: "executeProviderRoute",
    correlation_id: input.correlation_id,
    path_params: {},
    payload: {
      candidate_group_id: groupId,
      required_capability: "TEXT_CHAT",
      use_case: useCase,
      data_classification: "INTERNAL",
      canonical_instruction: canonicalInstruction,
      scoped_context: scopedContext,
    },
  }));
  if (asText(route.status) !== "SUCCESS" || route.external_request_sent !== true) {
    throw new NamedRuntimeError(asText(route.reason) ?? "CONVERSATION_PROVIDER_ROUTE_NOT_SUCCESSFUL");
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
  const text = asText(payload.normalized_result);
  const providerId = asText(decision.provider_id);
  const modelId = asText(decision.model_id);
  if (asText(decision.status) !== "SUCCESS" || payload.external_request_sent !== true) {
    throw new NamedRuntimeError("CONVERSATION_ROUTE_DECISION_NOT_SUCCESSFUL");
  }
  if (!text || !providerId || !modelId) throw new NamedRuntimeError("CONVERSATION_ASSISTANT_RESULT_MISSING");
  return {
    text,
    providerId,
    modelId,
    decisionId,
    resultHash: asText(payload.result_hash),
    workerSucceeded: asRecord(route.worker).succeeded === 1,
  };
}

function governanceInstruction(
  input: ProductionConversationTurnInput,
  governanceContext: GovernanceContext,
  task: string,
): string {
  return [
    ...ACPOS_AI_RESPONSE_POLICY,
    "",
    "Page-specific ACPOS policy:",
    ...governanceContext.page_policy.map((rule) => `- ${rule}`),
    "",
    "The current ACPOS Governance Context below is supplied by runtime and is the only system/project truth you may treat as current:",
    JSON.stringify(governanceContext),
    "",
    "Current task:",
    task,
    "",
    "Return exactly one JSON object and no markdown fence. It MUST match this schema:",
    JSON.stringify(ACPOS_AI_RESPONSE_SCHEMA),
    "",
    "Rules for the JSON response:",
    "- Every facts[].evidence_refs item must refer to a ref present in the supplied Governance Context.",
    "- If a statement is not evidence-backed, put it in inferences or open_questions, not facts.",
    "- Only P0/P1 may appear in open_questions.",
    "- P2/P3 belong in resolved_items and may not be asked back to the human.",
    "- For CONFIRMED/REJECTED/SUPERSEDED decision_updates, user_quote must be an exact substring of the current user message.",
    "- OPEN_P0/OPEN_P1 may use user_quote=null.",
    "- candidate_ready never means approved; it means only that discussion context appears sufficient for a separate governed Candidate action.",
    "",
    "Current user message:",
    input.message,
  ].join("\n");
}

async function repairGovernedResponse(
  groupId: string,
  input: ProductionConversationTurnInput,
  raw: string,
  governanceContext: GovernanceContext,
): Promise<RoutedText> {
  const instruction = [
    "Repair the following ACPOS AI response into the exact required JSON schema without adding any new fact, decision, identifier, evidence, approval or conclusion.",
    "If a value was not present in the raw response or Governance Context, use an empty array, false, or a neutral unresolved wording rather than inventing it.",
    "Return JSON only; no markdown fence.",
    JSON.stringify(ACPOS_AI_RESPONSE_SCHEMA),
    "Governance Context:",
    JSON.stringify(governanceContext),
    "Raw response:",
    truncate(raw, 12000),
  ].join("\n");
  return executeTextRoute(
    groupId,
    input,
    instruction,
    "ACPOS_CONVERSATION_GOVERNANCE_REPAIR",
    {
      conversation_id: input.conversation_id,
      page_uid: input.page_uid ?? null,
      context_fingerprint: governanceContext.latest_context_fingerprint,
      repair_only: true,
    },
  );
}

async function executeGovernedSingle(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  governanceContext: GovernanceContext,
  task: string,
): Promise<GovernedRoute> {
  const groupId = await resolveTextChatGroup(sql);
  let routed = await executeTextRoute(
    groupId,
    input,
    governanceInstruction(input, governanceContext, task),
    "ACPOS_CONVERSATION",
    {
      conversation_id: input.conversation_id,
      page_uid: input.page_uid ?? null,
      project_id: asRecord(governanceContext.affected_scope).project_id ?? null,
      topic_id: asRecord(governanceContext.affected_scope).topic_id ?? null,
      system_change_id: input.system_change_id ?? null,
      context_fingerprint: governanceContext.latest_context_fingerprint,
      ai_mode: "SINGLE_AI",
    },
  );
  let governed = parseAcposGovernedAiResponse(routed.text);
  let governanceRepairUsed = false;
  if (!governed) {
    routed = await repairGovernedResponse(groupId, input, routed.text, governanceContext);
    governed = parseAcposGovernedAiResponse(routed.text);
    governanceRepairUsed = true;
  }
  if (!governed) throw new NamedRuntimeError("CONVERSATION_GOVERNANCE_RESPONSE_INVALID");
  governed = validateDecisionUpdatesAgainstUserMessage(governed, input.message);
  return {
    ...routed,
    governed,
    renderedText: renderAcposGovernedAiResponse(governed),
    governanceRepairUsed,
  };
}

const COUNCIL_PARTICIPANTS = [
  { alias: "A", perspective: "PRODUCT_SYSTEM_DESIGNER" },
  { alias: "B", perspective: "SYSTEM_ARCHITECT" },
  { alias: "C", perspective: "VALIDATION_REVIEWER" },
] as const;

async function persistMeetingStart(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  context: ConversationContext,
  governanceContext: GovernanceContext,
  councilMode: CouncilMode,
): Promise<{ meetingId: string; roundId: string; participantIds: Record<string, string> }> {
  const meetingId = crypto.randomUUID();
  const roundId = crypto.randomUUID();
  const participantIds = Object.fromEntries(
    COUNCIL_PARTICIPANTS.map((participant) => [participant.alias, crypto.randomUUID()]),
  );
  await sql`
    INSERT INTO acpos_runtime.meetings(
      id,project_id,topic_id,title,objective,agenda,context_snapshot_id,context_snapshot_hash,current_round,version,status
    ) VALUES(
      ${meetingId},
      ${context.project_id ?? "SYSTEM"},
      ${context.topic_id},
      ${`ACPOS AI Council ${input.conversation_id}`},
      ${truncate(input.message, 1200)},
      ${JSON.stringify({
        conversation_id: input.conversation_id,
        page_uid: input.page_uid ?? null,
        system_change_id: input.system_change_id ?? null,
        council_mode: councilMode,
        participant_aliases: COUNCIL_PARTICIPANTS.map((item) => item.alias),
      })}::jsonb,
      ${governanceContext.latest_context_fingerprint},
      ${governanceContext.latest_context_fingerprint},
      1,1,'RUNNING'
    )
  `;
  for (const participant of COUNCIL_PARTICIPANTS) {
    await sql`
      INSERT INTO acpos_runtime.meeting_participants(
        id,meeting_id,perspective,route_mode,candidate_group_id,allow_substitution,participant_status,preflight_status
      ) VALUES(
        ${participantIds[participant.alias]},
        ${meetingId},
        ${participant.perspective},
        'SYSTEM_OWNED',
        NULL,
        true,
        'READY',
        'PASS'
      )
    `;
  }
  await sql`
    INSERT INTO acpos_runtime.meeting_rounds(
      id,meeting_id,round_no,round_mode,context_snapshot_id,prompt,status
    ) VALUES(
      ${roundId},${meetingId},1,${councilMode},${governanceContext.latest_context_fingerprint},
      ${truncate(input.message, 4000)},'RUNNING'
    )
  `;
  return { meetingId, roundId, participantIds };
}

async function persistParticipantResult(
  sql: SqlClient,
  meetingId: string,
  roundId: string,
  participantId: string,
  routed: RoutedText,
  alias: string,
  contextFingerprint: string,
): Promise<string> {
  const messageId = crypto.randomUUID();
  await sql`
    UPDATE acpos_runtime.meeting_participants
    SET actual_provider_id=${routed.providerId},
        actual_model_id=${routed.modelId},
        participant_status='COMPLETED',
        updated_at=now()
    WHERE id=${participantId}
  `;
  await sql`
    INSERT INTO acpos_runtime.meeting_messages(
      id,meeting_id,round_id,participant_id,sender_type,content,provider_id,model_id,evidence_json,status
    ) VALUES(
      ${messageId},${meetingId},${roundId},${participantId},
      ${`AI_${alias}`},${routed.text},${routed.providerId},${routed.modelId},
      ${JSON.stringify({
        route_decision_id: routed.decisionId,
        result_hash: routed.resultHash,
        context_fingerprint: contextFingerprint,
        external_request_sent: true,
      })}::jsonb,
      'COMPLETED'
    )
  `;
  return messageId;
}

async function executeMultiAiCouncil(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  context: ConversationContext,
  governanceContext: GovernanceContext,
  task: string,
): Promise<GovernedRoute & { meetingId: string; participantResponses: number; councilMode: CouncilMode }> {
  const groupId = await resolveTextChatGroup(sql);
  const councilMode = normalizeCouncilMode(input.council_mode);
  const meeting = await persistMeetingStart(sql, input, context, governanceContext, councilMode);
  const responses: Array<{ alias: string; perspective: string; text: string; providerId: string; modelId: string }> = [];

  try {
    for (const participant of COUNCIL_PARTICIPANTS) {
      const prior = councilMode === "DISCUSSION" && responses.length
        ? [
            "",
            "Prior council responses are review material, NOT source facts:",
            ...responses.map((item) => `[${item.alias}/${item.perspective}] ${item.text}`),
          ].join("\n")
        : "";
      const independenceRule = councilMode === "PARALLEL"
        ? "This is an independent first-round response. Do not use or assume any other AI response."
        : "Review prior council responses for gaps/conflicts, but never treat them as verified facts.";
      const instruction = [
        ...ACPOS_AI_RESPONSE_POLICY,
        "",
        `You are council participant ${participant.alias} with perspective ${participant.perspective}.`,
        independenceRule,
        "Use the exact same Governance Context and evidence refs for every participant.",
        "Focus on dependencies, conflicts, missing information, risks, alternatives and simplification from your perspective.",
        "Do not make a human decision or approval. Do not invent Current System Truth.",
        "",
        "Governance Context:",
        JSON.stringify(governanceContext),
        "",
        "Current task:",
        task,
        prior,
        "",
        "Return concise analysis text. Explicitly label any inference as inference and any true P0/P1 question as P0 or P1.",
      ].join("\n");
      const routed = await executeTextRoute(
        groupId,
        input,
        instruction,
        "ACPOS_CONVERSATION_MULTI_AI_PARTICIPANT",
        {
          conversation_id: input.conversation_id,
          meeting_id: meeting.meetingId,
          participant_alias: participant.alias,
          perspective: participant.perspective,
          council_mode: councilMode,
          context_fingerprint: governanceContext.latest_context_fingerprint,
        },
      );
      await persistParticipantResult(
        sql,
        meeting.meetingId,
        meeting.roundId,
        meeting.participantIds[participant.alias],
        routed,
        participant.alias,
        governanceContext.latest_context_fingerprint,
      );
      responses.push({
        alias: participant.alias,
        perspective: participant.perspective,
        text: routed.text,
        providerId: routed.providerId,
        modelId: routed.modelId,
      });
    }

    const synthesisTask = [
      "Synthesize the council without voting in place of the human.",
      councilMode === "DISCUSSION"
        ? "Discussion mode: preserve the propose -> review -> compare/revise logic and surface the smallest coherent set of true P0/P1 decision questions."
        : "Parallel mode: compare the independent first-round responses, identify agreement/disagreement, then synthesize.",
      "Other AI responses are not source facts. Only Governance Context evidence can support facts.",
      "Council responses:",
      ...responses.map((item) => `[${item.alias}/${item.perspective}] ${item.text}`),
      "",
      "Original task:",
      task,
    ].join("\n\n");

    let synthesis = await executeTextRoute(
      groupId,
      input,
      governanceInstruction(input, governanceContext, synthesisTask),
      "ACPOS_CONVERSATION_MULTI_AI_SYNTHESIS",
      {
        conversation_id: input.conversation_id,
        meeting_id: meeting.meetingId,
        council_mode: councilMode,
        participant_count: responses.length,
        context_fingerprint: governanceContext.latest_context_fingerprint,
      },
    );
    let governed = parseAcposGovernedAiResponse(synthesis.text);
    let governanceRepairUsed = false;
    if (!governed) {
      synthesis = await repairGovernedResponse(groupId, input, synthesis.text, governanceContext);
      governed = parseAcposGovernedAiResponse(synthesis.text);
      governanceRepairUsed = true;
    }
    if (!governed) throw new NamedRuntimeError("CONVERSATION_GOVERNANCE_RESPONSE_INVALID");
    governed = validateDecisionUpdatesAgainstUserMessage(governed, input.message);

    const synthesisMessageId = crypto.randomUUID();
    await sql`
      INSERT INTO acpos_runtime.meeting_messages(
        id,meeting_id,round_id,participant_id,sender_type,content,provider_id,model_id,evidence_json,status
      ) VALUES(
        ${synthesisMessageId},${meeting.meetingId},${meeting.roundId},NULL,'ASSISTANT',
        ${renderAcposGovernedAiResponse(governed)},${synthesis.providerId},${synthesis.modelId},
        ${JSON.stringify({
          route_decision_id: synthesis.decisionId,
          result_hash: synthesis.resultHash,
          context_fingerprint: governanceContext.latest_context_fingerprint,
          participant_message_count: responses.length,
          external_request_sent: true,
        })}::jsonb,
        'COMPLETED'
      )
    `;
    await sql`
      UPDATE acpos_runtime.meeting_rounds SET status='COMPLETED',updated_at=now() WHERE id=${meeting.roundId}
    `;
    await sql`
      UPDATE acpos_runtime.meetings SET status='COMPLETED',updated_at=now() WHERE id=${meeting.meetingId}
    `;

    return {
      ...synthesis,
      governed,
      renderedText: renderAcposGovernedAiResponse(governed),
      governanceRepairUsed,
      meetingId: meeting.meetingId,
      participantResponses: responses.length,
      councilMode,
    };
  } catch (error) {
    await sql`UPDATE acpos_runtime.meeting_rounds SET status='FAILED',updated_at=now() WHERE id=${meeting.roundId}`.catch(() => undefined);
    await sql`UPDATE acpos_runtime.meetings SET status='FAILED',updated_at=now() WHERE id=${meeting.meetingId}`.catch(() => undefined);
    throw error;
  }
}

async function insertAssistantMessage(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  userMessageRef: string,
  routed: GovernedRoute & { meetingId?: string; participantResponses?: number; councilMode?: CouncilMode },
  governanceContext: GovernanceContext,
): Promise<string> {
  const assistantRef = crypto.randomUUID();
  const seq = await nextSequence(sql, input);
  const content = JSON.stringify({
    text: routed.renderedText,
    assistant_summary: routed.governed.assistant_summary,
    facts: routed.governed.facts,
    inferences: routed.governed.inferences,
    open_questions: routed.governed.open_questions,
    resolved_items: routed.governed.resolved_items,
    candidate_ready: routed.governed.candidate_ready,
    response_mode: routed.governed.response_mode,
    route_decision_id: routed.decisionId,
    provider_id: routed.providerId,
    model_id: routed.modelId,
    result_hash: routed.resultHash,
    source_message_ref: userMessageRef,
    external_request_sent: true,
    governance: {
      policy_version: ACPOS_AI_GOVERNANCE_POLICY_VERSION,
      status: "PASS",
      response_schema_valid: true,
      repair_used: routed.governanceRepairUsed,
      context_fingerprint: governanceContext.latest_context_fingerprint,
      ai_mode: normalizeAiMode(input.ai_mode),
      council_mode: routed.councilMode ?? null,
      meeting_id: routed.meetingId ?? null,
      participant_responses: routed.participantResponses ?? 0,
    },
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

async function persistDecisionLedger(
  sql: SqlClient,
  input: ProductionConversationTurnInput,
  userMessageRef: string,
  assistantMessageRef: string,
  response: AcposGovernedAiResponse,
  governanceContext: GovernanceContext,
): Promise<number> {
  if (!response.decision_updates.length) return 0;
  const entries = response.decision_updates.map((entry, index) => ({
    ...entry,
    decision_ref: stableHash({
      conversation_id: input.conversation_id,
      user_message_ref: userMessageRef,
      assistant_message_ref: assistantMessageRef,
      decision_key: entry.decision_key,
      index,
    }),
  }));
  const ledgerRef = crypto.randomUUID();
  const seq = await nextSequence(sql, input);
  const content = JSON.stringify({
    kind: "DECISION_LEDGER",
    text: "",
    policy_version: ACPOS_AI_GOVERNANCE_POLICY_VERSION,
    context_fingerprint: governanceContext.latest_context_fingerprint,
    source_user_message_ref: userMessageRef,
    source_assistant_message_ref: assistantMessageRef,
    entries,
  });
  await runRlsActorQuery(
    sql,
    input.session_token_hash,
    sql`
      INSERT INTO conversation_messages(
        conversation_message_id, conversation_id, sequence_no, actor_type, actor_ref, message_content
      ) VALUES(
        ${ledgerRef}::uuid,${input.conversation_id}::uuid,${seq},'SYSTEM',
        'ACPOS_DECISION_LEDGER',${content}::jsonb
      )
    `,
  );
  return entries.length;
}

export async function executeProductionConversationTurn(
  input: ProductionConversationTurnInput,
): Promise<unknown> {
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const message = input.message.trim();
  if (!message) throw new NamedRuntimeError("MESSAGE_REQUIRED");

  const context = await requireConversationContext(sql, input);
  const normalizedInput = { ...input, message };
  const messageRef = await insertUserMessage(sql, normalizedInput);
  const governanceContext = await buildGovernanceContext(sql, normalizedInput, context);
  const source = governanceContext.conversation.source_refs.find((item) =>
    item.kind === "MESSAGE" && item.resolved
  );
  const task = input.instruction_kind === "ANALYZE" && source?.content
    ? `Analyze the exact referenced message while preserving current ACPOS context. Referenced content: ${String(source.content)}`
    : "Review and respond to the latest user message under the ACPOS governance contract.";

  const aiMode = normalizeAiMode(input.ai_mode);
  const routed = aiMode === "MULTI_AI"
    ? await executeMultiAiCouncil(sql, normalizedInput, context, governanceContext, task)
    : await executeGovernedSingle(sql, normalizedInput, governanceContext, task);

  const assistantRef = await insertAssistantMessage(
    sql,
    normalizedInput,
    messageRef,
    routed,
    governanceContext,
  );
  const ledgerUpdates = await persistDecisionLedger(
    sql,
    normalizedInput,
    messageRef,
    assistantRef,
    routed.governed,
    governanceContext,
  );

  return {
    conversation_id: input.conversation_id,
    message_ref: messageRef,
    accepted: true,
    assistant_response_ref: assistantRef,
    assistant_response_text: routed.renderedText,
    assistant_summary: routed.governed.assistant_summary,
    facts: routed.governed.facts,
    inferences: routed.governed.inferences,
    open_questions: routed.governed.open_questions,
    resolved_items: routed.governed.resolved_items,
    candidate_ready: routed.governed.candidate_ready,
    response_mode: routed.governed.response_mode,
    decision_ledger_updates: ledgerUpdates,
    context_fingerprint: governanceContext.latest_context_fingerprint,
    governance_policy_version: ACPOS_AI_GOVERNANCE_POLICY_VERSION,
    governance_status: "PASS",
    governance_repair_used: routed.governanceRepairUsed,
    ai_mode: aiMode,
    council_mode: "councilMode" in routed ? routed.councilMode : null,
    multi_ai_meeting_id: "meetingId" in routed ? routed.meetingId : null,
    multi_ai_participant_responses: "participantResponses" in routed ? routed.participantResponses : 0,
    provider_id: routed.providerId,
    model_id: routed.modelId,
    route_decision_id: routed.decisionId,
    result_hash: routed.resultHash,
    external_request_sent: true,
    worker_succeeded: routed.workerSucceeded ? 1 : 0,
  };
}
