import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import {
  hashSessionToken,
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";
import type { UiProjectionRequest } from "@/server/shared/uiProjectionRuntime";

export const CURRENT_PAGE_RESOURCE_KEYS: Readonly<Record<string, string>> = {
  "CORE-01": "page:workspace:CORE-01",
  "ASSET-01": "page:workspace:ASSET-01",
  "VIDEO-01": "page:workspace:VIDEO-01",
  "EDIT-01": "page:workspace:EDIT-01",
  "QA-01": "page:workspace:QA-01",
  "admin:DB-01": "page:admin:DB-01",
  "workspace:STR-01": "page:workspace:STR-01",
  "workspace:INFO-01": "page:workspace:INFO-01",
  "admin:SYS-01": "page:admin:SYS-01",
  "admin:IAM-01": "page:admin:IAM-01",
  "admin:DEV-01": "page:admin:DEV-01",
  "admin:SOC-01": "page:admin:SOC-01",
  "admin:ERP-01": "page:admin:ERP-01",
  "admin:AIAPI-01": "page:admin:AIAPI-01",
  "admin:SG-02": "page:admin:SG-02",
  "admin:STR-01": "page:admin:STR-01",
  "admin:KB-01": "page:admin:KB-01",
};

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asText(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  return null;
}

function asJsonObject(value: unknown): Record<string, unknown> | null {
  if (typeof value === "string") {
    try {
      const parsed: unknown = JSON.parse(value);
      return asRecord(parsed);
    } catch {
      return null;
    }
  }
  return asRecord(value);
}

function emptyObjectMatches(assignmentScope: unknown, requestScope: Record<string, never>): boolean {
  const scope = asJsonObject(assignmentScope);
  if (!scope) return false;
  return Object.keys(scope).every((key) => key in requestScope && Object.is(scope[key], requestScope[key as never]));
}

function conditionAllows(condition: unknown): boolean {
  const object = asJsonObject(condition);
  if (!object) return false;
  return Object.keys(object).length === 0;
}

async function readSessionCookie(): Promise<string | undefined> {
  try {
    const jar = await cookies();
    return jar.get(IDENTITY_COOKIE_NAME)?.value;
  } catch {
    return undefined;
  }
}

type GateDecision =
  | { allowed: true; session_token_hash: string; actor_user_id: string }
  | { allowed: false; reason_code: string };

async function evaluatePageViewGate(resourceKey: string): Promise<GateDecision> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) return { allowed: false, reason_code: "DATABASE_RUNTIME_NOT_BOUND" };

  const cookieValue = await readSessionCookie();
  const identity = await resolveIdentityFromCookie(cookieValue);
  if (!identity.ok) return { allowed: false, reason_code: identity.reason_code };
  if (!cookieValue) return { allowed: false, reason_code: "RLS_SESSION_CONTEXT_REQUIRED" };
  const sessionTokenHash = hashSessionToken(cookieValue);

  try {
    const rows = await runRlsActorQuery(
      sql,
      sessionTokenHash,
      sql`
      SELECT a.account_permission_assignment_id::text AS account_permission_assignment_id,
             a.effect,
             a.status,
             a.scope,
             a.condition,
             a.gate_profile
      FROM account_permission_assignments a
      JOIN permission_resources r ON r.resource_id = a.resource_id
      WHERE a.user_id = ${identity.actor.user_id}
        AND r.resource_key = ${resourceKey}
        AND r.resource_type = 'PAGE'
        AND r.active = true
        AND a.action = 'VIEW'
        AND a.status = 'APPROVED'
        AND a.effective_from <= now()
        AND (a.effective_to IS NULL OR a.effective_to > now())
      `,
    );
    const list = Array.isArray(rows) ? rows : [];
    const requestScope = {} as Record<string, never>;
    const matched: Array<{ effect: string }> = [];
    for (const raw of list) {
      const row = asRecord(raw);
      if (!row) continue;
      if (!emptyObjectMatches(row.scope, requestScope)) continue;
      if (!conditionAllows(row.condition)) continue;
      const effect = asText(row.effect);
      if (!effect) continue;
      matched.push({ effect });
    }
    if (matched.some((row) => row.effect === "DENY")) return { allowed: false, reason_code: "PERMISSION_DENIED" };
    if (matched.some((row) => row.effect === "ALLOW")) return { allowed: true, session_token_hash: sessionTokenHash, actor_user_id: identity.actor.user_id };
    return { allowed: false, reason_code: "PERMISSION_OR_SCOPE_DENIED" };
  } catch {
    return { allowed: false, reason_code: "AUTHORIZATION_EVALUATION_FAILED" };
  }
}

async function evaluateCatalogResourceAction(
  sql: SqlClient,
  sessionTokenHash: string,
  actorUserId: string,
  resourceKey: string,
  action: string,
): Promise<boolean> {
  try {
    const rows = await runRlsActorQuery(
      sql,
      sessionTokenHash,
      sql`
        SELECT a.effect, a.scope, a.condition
        FROM account_permission_assignments a
        JOIN permission_resources r ON r.resource_id = a.resource_id
        WHERE a.user_id = ${actorUserId}
          AND r.resource_key = ${resourceKey}
          AND r.resource_type IN ('ACTION','CONTROL','API','SENSITIVE_PERMISSION')
          AND r.active = true
          AND ${action} = ANY(
            SELECT jsonb_array_elements_text(
              CASE WHEN jsonb_typeof(r.allowed_actions) = 'array' THEN r.allowed_actions ELSE '[]'::jsonb END
            )
          )
          AND a.action = ${action}
          AND a.status = 'APPROVED'
          AND a.effective_from <= now()
          AND (a.effective_to IS NULL OR a.effective_to > now())
      `,
    );
    const requestScope = {} as Record<string, never>;
    const effects: string[] = [];
    for (const raw of Array.isArray(rows) ? rows : []) {
      const row = asRecord(raw);
      if (!row) continue;
      if (!emptyObjectMatches(row.scope, requestScope)) continue;
      if (!conditionAllows(row.condition)) continue;
      const effect = asText(row.effect);
      if (effect) effects.push(effect);
    }
    if (effects.includes("DENY")) return false;
    return effects.includes("ALLOW");
  } catch {
    return false;
  }
}

const DASH = "—";

type RefItem = { ref: string; label: string };

function textOrDash(value: unknown): string {
  return asText(value) ?? DASH;
}

function jsonText(value: unknown): string {
  if (value === null || value === undefined) return DASH;
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : DASH;
  }
  try {
    return JSON.stringify(value);
  } catch {
    return DASH;
  }
}

async function safeRows(work: () => Promise<unknown>): Promise<Record<string, unknown>[]> {
  try {
    const rows = await work();
    return (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const row = asRecord(raw);
      return row ? [row] : [];
    });
  } catch {
    return [];
  }
}

function refList(rows: Record<string, unknown>[], refKey = "ref", labelKey = "label"): RefItem[] {
  return rows.flatMap((row) => {
    const ref = asText(row[refKey]);
    const label = asText(row[labelKey]);
    if (!ref || !label) return [];
    return [{ ref, label }];
  });
}

async function readProjectRefs(sql: SqlClient, sessionTokenHash: string): Promise<RefItem[]> {
  const rows = await runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
      SELECT p.project_id::text AS ref, p.title AS label
      FROM projects p
      WHERE p.archived_at IS NULL
      ORDER BY p.created_at DESC
    `,
  );
  return (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    const label = asText(row?.label);
    if (!ref || !label) return [];
    return [{ ref, label }];
  });
}

async function readTopicRefs(sql: SqlClient, sessionTokenHash: string): Promise<RefItem[]> {
  const rows = await runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
      SELECT t.topic_id::text AS ref, t.title AS label
      FROM topics t
      WHERE t.archived_at IS NULL
      ORDER BY t.created_at DESC
    `,
  );
  return (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    const label = asText(row?.label);
    if (!ref || !label) return [];
    return [{ ref, label }];
  });
}

type DepartmentTaskRow = {
  task_id: string;
  status: string;
  input_fingerprint: string | null;
  handed_off_output_version_id: string | null;
  project_id: string;
  project_label: string;
  topic_id: string;
  topic_label: string;
};

async function readDepartmentTasks(sql: SqlClient, sessionTokenHash: string, department: string): Promise<DepartmentTaskRow[]> {
  const rows = await runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
      SELECT t.task_id::text AS task_id,
             t.status::text AS status,
             t.input_fingerprint,
             p.project_id::text AS project_id,
             p.title AS project_label,
             tp.topic_id::text AS topic_id,
             tp.title AS topic_label,
             h.source_output_version_id::text AS handed_off_output_version_id
      FROM department_tasks t
      JOIN child_locks cl ON cl.child_lock_id = t.child_lock_id
      JOIN topics tp ON tp.topic_id = cl.topic_id
      JOIN projects p ON p.project_id = tp.project_id
      LEFT JOIN LATERAL (
        SELECT h0.source_output_version_id
        FROM handoffs h0
        WHERE h0.target_task_id=t.task_id
          AND h0.status IN ('HANDOFF_READY','HANDED_OFF')
        ORDER BY h0.created_at DESC,h0.handoff_id DESC
        LIMIT 1
      ) h ON true
      WHERE t.department::text = ${department}
      ORDER BY t.created_at DESC
    `,
  );
  return (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const task_id = asText(row?.task_id);
    const status = asText(row?.status);
    const project_id = asText(row?.project_id);
    const project_label = asText(row?.project_label);
    const topic_id = asText(row?.topic_id);
    const topic_label = asText(row?.topic_label);
    if (!task_id || !status || !project_id || !project_label || !topic_id || !topic_label) return [];
    return [{
      task_id,
      status,
      input_fingerprint: asText(row?.input_fingerprint),
      handed_off_output_version_id: asText(row?.handed_off_output_version_id),
      project_id,
      project_label,
      topic_id,
      topic_label,
    }];
  });
}

async function readCoreProjection(sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
  const projectRows = await runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
    SELECT p.project_id::text AS project_id,
           p.active_version_id::text AS project_version_ref,
           p.title AS label,
           p.status::text AS status
    FROM projects p
    WHERE p.archived_at IS NULL
      ORDER BY p.created_at DESC
    `,
  );
  let topicRows: unknown = [];
  try {
    topicRows = await runRlsActorQuery(
      sql,
      sessionTokenHash,
      sql`
        SELECT t.topic_id::text AS topic_id,
               t.active_version_id::text AS topic_version_ref,
               t.title AS label,
               t.project_id::text AS project_id
        FROM topics t
        WHERE t.archived_at IS NULL
        ORDER BY t.created_at DESC
      `,
    );
  } catch {
    topicRows = [];
  }
  const projects = (Array.isArray(projectRows) ? projectRows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const project_id = asText(row?.project_id);
    const label = asText(row?.label);
    if (!project_id || !label) return [];
    return [{ project_id, project_version_ref: asText(row?.project_version_ref), label, status: asText(row?.status) ?? DASH }];
  });
  const first = projects[0] ?? null;
  const topics = (Array.isArray(topicRows) ? topicRows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const topic_id = asText(row?.topic_id);
    const label = asText(row?.label);
    const project_id = asText(row?.project_id);
    if (!topic_id || !label || !project_id) return [];
    if (first && project_id !== first.project_id) return [];
    return [{ topic_id, topic_version_ref: asText(row?.topic_version_ref), label }];
  });
  let threadRows: unknown = [];
  if (first) {
    try {
      threadRows = await runRlsActorQuery(
        sql,
        sessionTokenHash,
        sql`
          SELECT c.conversation_id::text AS conversation_id,
                 c.title AS label
          FROM conversations c
          WHERE c.project_id = ${first.project_id}::uuid
          ORDER BY c.created_at DESC
        `,
      );
    } catch {
      threadRows = [];
    }
  }
  const threads = (Array.isArray(threadRows) ? threadRows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const conversation_id = asText(row?.conversation_id);
    const label = asText(row?.label);
    if (!conversation_id || !label) return [];
    return [{ conversation_id, label }];
  });
  const messages_by_thread: Record<string, Array<{ message_ref: string; conversation_id: string; role: "USER" | "ASSISTANT" | "SYSTEM"; text: string }>> = {};
  if (threads.length) {
    const ids = threads.map((item) => item.conversation_id);
    const messageRows = await runRlsActorQuery(
      sql,
      sessionTokenHash,
      sql`
        SELECT conversation_message_id::text AS message_ref,
               conversation_id::text AS conversation_id,
               actor_type,
               COALESCE(message_content->>'text','') AS text,
               COALESCE(message_content->>'kind','') AS kind,
               message_content->>'assistant_summary' AS assistant_summary,
               message_content->>'response_mode' AS response_mode,
               message_content->'governance' AS governance
        FROM conversation_messages
        WHERE conversation_id = ANY(${ids}::uuid[])
          AND COALESCE(message_content->>'kind','') <> 'DECISION_LEDGER'
        ORDER BY conversation_id, sequence_no
      `,
    ).catch(() => []);
    for (const raw of Array.isArray(messageRows) ? messageRows : []) {
      const row = asRecord(raw);
      const message_ref = asText(row?.message_ref);
      const conversation_id = asText(row?.conversation_id);
      const actor_type = asText(row?.actor_type);
      const text = typeof row?.text === "string" ? row.text : "";
      if (!message_ref || !conversation_id || !text.trim()) continue;
      const role: "USER" | "ASSISTANT" | "SYSTEM" =
        actor_type === "USER" ? "USER" : actor_type === "PROVIDER" ? "ASSISTANT" : "SYSTEM";
      (messages_by_thread[conversation_id] ??= []).push({ message_ref, conversation_id, role, text });
    }
  }
  const currentConversationId = threads[0]?.conversation_id ?? null;
  const latestAssistantRows = currentConversationId
    ? await runRlsActorQuery(
        sql,
        sessionTokenHash,
        sql`
          SELECT message_content->>'assistant_summary' AS assistant_summary,
                 message_content->>'response_mode' AS response_mode,
                 message_content->'governance'->>'context_fingerprint' AS context_fingerprint,
                 actor_ref
          FROM conversation_messages
          WHERE conversation_id=${currentConversationId}::uuid
            AND actor_type='PROVIDER'
          ORDER BY sequence_no DESC
          LIMIT 1
        `,
      ).catch(() => [])
    : [];
  const latestAssistantMeta = asRecord(Array.isArray(latestAssistantRows) ? latestAssistantRows[0] : null);
  const aiGroupRows = await sql`
    SELECT g.id,
           count(*) FILTER (WHERE m.enabled=true AND p.enabled=true AND p.health_status='HEALTHY')::int AS healthy_members
    FROM acpos_runtime.provider_groups g
    LEFT JOIN acpos_runtime.provider_members m ON m.group_id=g.id
    LEFT JOIN acpos_runtime.provider_profiles p ON p.provider_id=m.provider_id AND p.model_id=m.model_id
    WHERE g.enabled=true AND g.use_case='ACPOS_TEXT_CHAT'
    GROUP BY g.id,g.updated_at
    ORDER BY g.updated_at DESC,g.id
    LIMIT 1
  `.catch(() => []);
  const aiGroup = asRecord(Array.isArray(aiGroupRows) ? aiGroupRows[0] : null);
  const assignedAiSet = asText(aiGroup?.id);
  const healthyAiMembers = Number(aiGroup?.healthy_members ?? 0);

  return {
    refs: {
      project_id: first?.project_id ?? null,
      project_version_ref: first?.project_version_ref ?? null,
      topic_id: topics[0]?.topic_id ?? null,
      topic_version_ref: topics[0]?.topic_version_ref ?? null,
      dna_version_ref: null,
      blueprint_version_ref: null,
      conversation_id: currentConversationId,
      candidate_ref: null,
    },
    work_item: null,
    projects: projects.map((item) => ({
      project_id: item.project_id,
      project_version_ref: item.project_version_ref,
      label: item.label,
    })),
    topics,
    work_items: ["STORY", "CHAPTER", "WORLD_SETTING", "DNA", "BLUEPRINT"].map((work_item) => ({ work_item, label: work_item })),
    threads,
    messages_by_thread,
    display_values: {
      page_mode: "PROJECT_CORE",
      assigned_ai_set: assignedAiSet ?? DASH,
      project_state: first?.status ?? DASH,
      story_candidate_set: DASH,
      dna_state: DASH,
      blueprint_state: DASH,
      assistant_summary: asText(latestAssistantMeta?.assistant_summary) ?? DASH,
      evaluation: DASH,
      structured_decision: DASH,
      runtime_stage: asText(latestAssistantMeta?.response_mode) ?? "READY",
      topic_scope: DASH,
      canonical_script: DASH,
      package: DASH,
      downstream_asset: DASH,
      downstream_video: DASH,
      downstream_edit: DASH,
      version_state: DASH,
      candidate_compare: DASH,
      lock_review: DASH,
      governance_policy: "ACPOS_AI_GOVERNANCE_V1.0",
      governance_context_fingerprint: asText(latestAssistantMeta?.context_fingerprint) ?? DASH,
      healthy_ai_members: String(healthyAiMembers),
    },
  };
}

async function readIamProjection(sql: SqlClient): Promise<unknown> {
  const rows = await sql`
    SELECT u.user_id::text AS account_id,
           u.display_name AS label,
           u.status::text AS status,
           u.email::text AS email
    FROM app_users u
    ORDER BY u.created_at DESC
  `;
  const accounts = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const account_id = asText(row?.account_id);
    const label = asText(row?.label);
    if (!account_id || !label) return [];
    return [{
      account_id,
      label,
      status: asText(row?.status) ?? DASH,
      identity_source: "LOCAL_PASSWORD",
      organization_scope: DASH,
      mfa: DASH,
      risk: DASH,
      session: DASH,
      front_l1: [],
      admin_l1: [],
      basic_data: { email: asText(row?.email) ?? DASH },
    }];
  });
  return {
    page_state: "LIST",
    values: {},
    gate_state: {
      "IAM-01-GATE-PAGE": true,
      "IAM-01-GATE-MANAGE": true,
      "IAM-01-GATE-DRAFT": true,
      "IAM-01-GATE-PREVIEW": false,
      "IAM-01-GATE-COMPLETE": false,
    },
    authorized_account_count: accounts.length,
    accounts,
    identity_schema: [],
    department_presets: [],
    preview: null,
    audit_entries: [],
  };
}

function emptyAsset(): unknown {
  return {
    page_state: "READY",
    task_id: null,
    output_version_id: null,
    layer_document_id: null,
    layer_id: null,
    patch_id: null,
    current_asset_type_uid: null,
    candidate_uri: null,
    candidate_media_kind: null,
    candidate_versions: [],
    values: {},
    lists: {},
    filters: {},
    gate_state: { "ASSET-01-GATE-PAGE": true },
  };
}

function emptyVideo(): unknown {
  return {
    page_state: "READY",
    task_id: null,
    current_version_id: null,
    candidate_version_id: null,
    current_uri: null,
    candidate_uri: null,
    versions: [],
    values: {},
    lists: {},
    filters: {},
    gate_state: { "VIDEO-01-GATE-PAGE": true },
  };
}

function emptyEdit(): unknown {
  return {
    project_id: null,
    topic_id: null,
    task_id: null,
    locked_blueprint_ref: null,
    production_package_ref: null,
    input_manifest_ref: null,
    input_fingerprint: null,
    working_draft_ref: null,
    editing_run_id: null,
    voice_run_id: null,
    saved_edit_version_id: null,
    output_version_id: null,
    dialogue_timing_binding_ref: null,
    page_state_uid: "EDIT-01-ST-READY",
    current_stage_uid: null,
    current_stage_phase: null,
    current_error_uid: null,
    preview_uri: null,
    final_preview_uri: null,
    current_stage_score: null,
    values: {},
    lists: {},
    gate_state: { "EDIT-01-GATE-PAGE": true },
  };
}

function emptyQa(): unknown {
  return {
    page_state_uid: "QA-01-ST-NOT-STARTED",
    current_stage_uid: "QA-01-STAGE-01-RESOLVE",
    project_id: null,
    topic_id: null,
    qa_task_ref: null,
    target_output_version_id: null,
    qa_review_ref: null,
    viewer_uri: null,
    failed_output_version_id: null,
    verified_new_output_version_id: null,
    manual_review_case_ref: null,
    scorecard_ref: null,
    release_package_ref: null,
    values: {},
    lists: {},
    gate_state: { "QA-01-GATE-PAGE": true },
    correlation_id: null,
    audit_ref: null,
  };
}

async function readDbCatalogProjection(sql: SqlClient): Promise<unknown> {
  const rows = await sql`
    SELECT table_name::text AS ref
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
  `;
  const entities = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const ref = asText(asRecord(raw)?.ref);
    if (!ref) return [];
    return [{ ref, label: ref, meta: { entity_type: "TABLE", domain: "public" } }];
  });
  let migrations: Array<{ ref: string; label: string }> = [];
  try {
    const history = await sql`
      SELECT migration_id AS ref
      FROM schema_migration_history
      ORDER BY applied_at
    `;
    migrations = (Array.isArray(history) ? history : []).flatMap((raw) => {
      const ref = asText(asRecord(raw)?.ref);
      if (!ref) return [];
      return [{ ref, label: ref }];
    });
  } catch {
    migrations = [];
  }
  return {
    page_state: entities.length ? "READY" : "EMPTY",
    values: {
      "DB-01-FLD-ENV": "wild-wave",
      "DB-01-FLD-SCOPE": "public",
      "DB-01-FLD-HEALTH": "BOUND",
      "DB-01-FLD-MIGRATION-HEAD": String(migrations.length),
    },
    lists: { "DB-01-LIST-ENTITIES": entities, "DB-01-LIST-FINDINGS": [] },
    tables: { "DB-01-TBL-MIGRATIONS": migrations },
    gates: {
      "DB-01-GATE-PAGE": true,
      "DB-01-GATE-CONTEXT": true,
      "DB-01-GATE-ENTITY": true,
      "DB-01-GATE-SCHEMA": true,
      "DB-01-GATE-TRACE": true,
      "DB-01-GATE-MIGRATION": true,
      "DB-01-GATE-INTEGRITY": true,
      "DB-01-GATE-AUDIT": true,
    },
    filters: {},
    graph: null,
    trace: [],
    audit: [],
    source_sync: "neon:wild-wave",
  };
}

function emptyStrategy(): unknown {
  return {
    page_state: "EMPTY",
    conversation_id: null,
    candidate_ref: null,
    candidate_version_ref: null,
    values: {},
    lists: {},
    blocks: {},
    gate_state: {},
    owner_type: null,
    owner_context_ref: null,
  };
}

function emptyInfo(): unknown {
  return {
    page_state: "EMPTY",
    projection_version: null,
    authorized_scope: null,
    last_refresh: null,
    values: {},
    lists: {},
    filters: {},
    gate_state: {},
  };
}

function emptySystem(): unknown {
  return {
    page_state: "EMPTY",
    system_change_id: null,
    conversation_id: null,
    thread_id: null,
    branch_id: null,
    multi_ai_route_available: false,
    values: {
      current_system_version: DASH,
      current_goal: DASH,
      scope: "admin:SYS-01",
      candidate_ref: DASH,
      context_snapshot_ref: DASH,
      dependency_graph_ref: DASH,
      latest_context_fingerprint: DASH,
    },
  };
}

function emptyDev(): unknown {
  return { page_state: "EMPTY", authorized_scope: null, run_status: null, values: {}, gate_state: {} };
}

function emptySoc(): unknown {
  return { page_state: "EMPTY", values: {}, gate_state: {} };
}

function emptyErp(): unknown {
  return { page_state: "EMPTY", values: {}, gate_state: {}, selected: {}, form_schemas: {} };
}

function emptyAiApi(): unknown {
  return { page_state: "EMPTY", values: {}, control_enabled: {}, provider_rows: [], selected_resource_id: null };
}

function emptySg02(): unknown {
  return { page_state: "EMPTY", values: {}, control_enabled: {} };
}

function emptyStrategyAdmin(): unknown {
  return { page_state: "EMPTY", values: {}, evidence: {}, states: {}, action_enabled: {}, selected_resource_id: null };
}

function emptyKnowledge(): unknown {
  return { page_state: "EMPTY", values: {}, control_enabled: {} };
}

async function readAssetFromDb(sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
  const [projects, topics, tasks] = await Promise.all([
    readProjectRefs(sql, sessionTokenHash),
    readTopicRefs(sql, sessionTokenHash),
    readDepartmentTasks(sql, sessionTokenHash, "ASSET"),
  ]);
  const first = tasks[0] ?? null;
  const empty = emptyAsset() as Record<string, unknown>;
  return {
    ...empty,
    task_id: first?.task_id ?? null,
    values: {
      "ASSET-01-FLD-TASK": first?.task_id ?? DASH,
      "ASSET-01-FLD-TASK-STATUS": first?.status ?? DASH,
      "ASSET-01-FLD-STAGE": first?.status ?? DASH,
      "ASSET-01-FLD-INPUT-FINGERPRINT": first?.input_fingerprint ?? DASH,
    },
    lists: {
      "ASSET-01-CTL-PROJECT": projects,
      "ASSET-01-CTL-TOPIC": topics,
      "ASSET-01-LST-ASSET": tasks.map((item) => ({ ref: item.task_id, label: item.status })),
    },
  };
}

async function readVideoFromDb(sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
  const [projects, topics, tasks] = await Promise.all([
    readProjectRefs(sql, sessionTokenHash),
    readTopicRefs(sql, sessionTokenHash),
    readDepartmentTasks(sql, sessionTokenHash, "VIDEO"),
  ]);
  const first = tasks[0] ?? null;
  const empty = emptyVideo() as Record<string, unknown>;
  return {
    ...empty,
    task_id: first?.task_id ?? null,
    values: {
      "VIDEO-01-FLD-STATUS": first?.status ?? DASH,
      "VIDEO-01-FLD-TASK-STATE": first?.status ?? DASH,
      "VIDEO-01-FLD-PAGE-STATE": "READY",
      "VIDEO-01-FLD-INPUT-FINGERPRINT": first?.input_fingerprint ?? DASH,
    },
    lists: {
      "VIDEO-01-FLD-PROJECT": projects,
      "VIDEO-01-FLD-TOPIC": topics,
      "VIDEO-01-FLD-TASK": tasks.map((item) => ({ ref: item.task_id, label: item.status })),
    },
  };
}

async function readEditFromDb(sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
  const [projects, topics, tasks] = await Promise.all([
    readProjectRefs(sql, sessionTokenHash),
    readTopicRefs(sql, sessionTokenHash),
    readDepartmentTasks(sql, sessionTokenHash, "EDITING"),
  ]);
  const first = tasks[0] ?? null;
  const empty = emptyEdit() as Record<string, unknown>;
  return {
    ...empty,
    project_id: first?.project_id ?? projects[0]?.ref ?? null,
    topic_id: first?.topic_id ?? topics[0]?.ref ?? null,
    task_id: first?.task_id ?? null,
    input_fingerprint: first?.input_fingerprint ?? null,
    lists: {
      "EDIT-01-CTL-PROJECT": projects,
      "EDIT-01-CTL-TOPIC": topics,
      "EDIT-01-LST-TASK": tasks.map((item) => ({ ref: item.task_id, label: item.status })),
    },
    values: {
      "EDIT-01-FLD-TASK": first?.task_id ?? DASH,
      "EDIT-01-FLD-STATUS": first?.status ?? DASH,
    },
  };
}

async function readQaFromDb(sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
  const [projects, topics, tasks] = await Promise.all([
    readProjectRefs(sql, sessionTokenHash),
    readTopicRefs(sql, sessionTokenHash),
    readDepartmentTasks(sql, sessionTokenHash, "QA"),
  ]);
  const first = tasks[0] ?? null;
  const approvedCriteria = (await safeRows(() => sql`
    SELECT criteria_version_id::text AS ref,
           criteria_key AS label,
           version_no::text AS version_no,
           gate_policy,
           required_checks,
           content_hash::text AS content_hash
    FROM quality_criteria_versions
    WHERE status='APPROVED'
      AND (department::text='QA' OR department IS NULL)
    ORDER BY version_no DESC,criteria_version_id DESC
    LIMIT 20
  `));
  const criteria = approvedCriteria[0] ?? null;
  const reviews = refList(await safeRows(() => sql`
    SELECT r.qa_review_run_id::text AS ref, r.status::text AS label
    FROM qa_review_runs r
    ORDER BY r.created_at DESC
  `));
  const findings = refList(await safeRows(() => sql`
    SELECT f.finding_id::text AS ref, (f.severity || ' ' || f.category) AS label
    FROM findings f
    ORDER BY f.created_at DESC
  `));
  const scorecards = await safeRows(() => sql`
    SELECT s.scorecard_id::text AS scorecard_id, s.output_version_id::text AS output_version_id, s.total_score::text AS total_score
    FROM scorecards s
    ORDER BY s.created_at DESC
  `);
  const reviewRow = (await safeRows(() => sql`
    SELECT r.qa_review_run_id::text AS qa_review_ref,
           r.qa_task_id::text AS qa_task_ref,
           r.output_version_id::text AS target_output_version_id,
           r.status::text AS status
    FROM qa_review_runs r
    ORDER BY r.created_at DESC
    LIMIT 1
  `))[0] ?? null;
  const empty = emptyQa() as Record<string, unknown>;
  return {
    ...empty,
    page_state_uid: first || reviewRow ? "QA-01-ST-READY" : "QA-01-ST-NOT-STARTED",
    project_id: first?.project_id ?? projects[0]?.ref ?? null,
    topic_id: first?.topic_id ?? topics[0]?.ref ?? null,
    qa_task_ref: asText(reviewRow?.qa_task_ref) ?? first?.task_id ?? null,
    qa_review_ref: asText(reviewRow?.qa_review_ref) ?? null,
    target_output_version_id: asText(reviewRow?.target_output_version_id) ?? asText(first?.handed_off_output_version_id) ?? asText(scorecards[0]?.output_version_id) ?? null,
    scorecard_ref: asText(scorecards[0]?.scorecard_id) ?? null,
    values: {
      "QA-01-FLD-PROJECT": first?.project_label ?? projects[0]?.label ?? DASH,
      "QA-01-FLD-TOPIC": first?.topic_label ?? topics[0]?.label ?? DASH,
      "QA-01-FLD-QA-TASK": first?.task_id ?? DASH,
      "QA-01-FLD-TARGET-OUTPUT": asText(reviewRow?.target_output_version_id) ?? asText(first?.handed_off_output_version_id) ?? DASH,
      "QA-01-FLD-REVIEW-STATE": asText(reviewRow?.status) ?? first?.status ?? DASH,
      "QA-01-FLD-CRITERIA-VERSION": asText(criteria?.ref) ?? DASH,
      "QA-01-FLD-GATE-POLICY": criteria?.gate_policy ?? DASH,
      "QA-01-FLD-REQUIRED-CHECKS": criteria?.required_checks ?? DASH,
      "QA-01-FLD-SCRIPT-HASH": asText(criteria?.content_hash) ?? DASH,
    },
    lists: {
      "QA-01-LIST-REVIEWS": reviews,
      "QA-01-LIST-SCORE-DIMENSIONS": scorecards.map((row) => ({
        ref: asText(row.scorecard_id) ?? "",
        label: asText(row.total_score) ?? DASH,
      })).filter((item) => item.ref),
      "QA-01-LIST-FINDINGS": findings,
      "QA-01-CTL-PROJECT": projects,
      "QA-01-CTL-TOPIC": topics,
      "QA-01-LST-TASK": tasks.map((item) => ({ ref: item.task_id, label: item.status })),
    },
    gate_state: {
      "QA-01-GATE-PAGE": true,
      "QA-01-GATE-START": Boolean(first?.task_id && first?.handed_off_output_version_id && criteria?.ref),
      "QA-01-GATE-CRITERIA": Boolean(criteria?.ref),
    },
  };
}

async function readStrategyFromDb(sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
  const topics = await readTopicRefs(sql, sessionTokenHash);
  const conversations = refList(await safeRows(() => runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
      SELECT c.conversation_id::text AS ref, c.title AS label
      FROM conversations c
      ORDER BY c.created_at DESC
    `,
  )));
  const candidateRows = await safeRows(() => runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
      SELECT
        s.strategy_candidate_id::text AS ref,
        s.decision_status::text AS label,
        encode(digest(concat_ws('|',
          s.source_fact_pack_ids::text,
          s.strategy_document::text,
          s.citations::text,
          s.freshness_at::text,
          s.confidence::text
        ),'sha256'),'hex') AS version_ref,
        COALESCE(NULLIF(s.strategy_document->>'analysis_basis',''),NULLIF(s.strategy_document->>'basis',''),NULLIF(s.strategy_document->>'analysis','')) AS analysis_basis,
        COALESCE(NULLIF(s.strategy_document->>'risk',''),NULLIF((s.strategy_document->'risks')::text,'')) AS risk,
        COALESCE(NULLIF(s.strategy_document->>'uncertainty',''),NULLIF((s.strategy_document->'uncertainty')::text,'')) AS uncertainty,
        s.confidence::text AS confidence,
        s.freshness_at::text AS freshness_at
      FROM strategy_candidates s
      ORDER BY s.created_at DESC
    `,
  ));
  const candidates = candidateRows.flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    const label = asText(row?.label);
    const version_ref = asText(row?.version_ref);
    if (!ref || !label || !version_ref) return [];
    return [{
      ref,
      label,
      version_ref,
      analysis_basis: asText(row?.analysis_basis),
      risk: asText(row?.risk),
      uncertainty: asText(row?.uncertainty),
      confidence: asText(row?.confidence),
      freshness_at: asText(row?.freshness_at),
    }];
  });
  const firstConversation = conversations[0] ?? null;
  const firstCandidate = candidates[0] ?? null;

  const decisionRows = firstCandidate
    ? await safeRows(() => runRlsActorQuery(
        sql,
        sessionTokenHash,
        sql`
          SELECT
            d.strategy_decision_id::text AS decision_id,
            d.decision,
            d.rationale,
            d.decider_id::text AS decider_id,
            d.created_at::text AS decided_at
          FROM strategy_decisions d
          WHERE d.strategy_candidate_id=${firstCandidate.ref}::uuid
          ORDER BY d.created_at DESC
          LIMIT 1
        `,
      ))
    : [];
  const decisionRow = asRecord(decisionRows[0] ?? null);

  const reviewRequestRows = firstCandidate
    ? await safeRows(() => runRlsActorQuery(
        sql,
        sessionTokenHash,
        sql`
          SELECT
            d.decision_request_id::text AS decision_request_ref,
            d.state,
            d.decision_reason,
            d.decided_by_user_id::text AS decided_by_user_id,
            d.decided_at::text AS decided_at,
            CASE
              WHEN d.state='APPROVED'
               AND d.decided_by_user_id IS NOT NULL
               AND NULLIF(d.decision_reason,'') IS NOT NULL
               AND d.evidence_refs<>'[]'::jsonb
               AND d.evidence_refs<>'{}'::jsonb
              THEN true ELSE false
            END AS approved_review_ready
          FROM decision_requests d
          JOIN permission_resources r
            ON r.resource_id=d.required_resource_id
           AND r.resource_key='api:adoptAsContextCandidate'
           AND r.active=true
          WHERE d.required_scope->>'candidate_ref'=${firstCandidate.ref}
            AND d.condition_snapshot->>'candidate_version_ref'=${firstCandidate.version_ref}
          ORDER BY d.created_at DESC
          LIMIT 1
        `,
      ))
    : [];
  const reviewRequestRow = asRecord(reviewRequestRows[0] ?? null);
  const approvedReviewReady = reviewRequestRow?.approved_review_ready === true;

  const messageRows = firstConversation
    ? await safeRows(() => runRlsActorQuery(
        sql,
        sessionTokenHash,
        sql`
          SELECT sequence_no, actor_type, actor_ref,
                 left(COALESCE(message_content->>'text',''), 4000) AS text,
                 message_content->>'assistant_summary' AS assistant_summary,
                 message_content->'governance'->>'context_fingerprint' AS context_fingerprint,
                 COALESCE(message_content->>'kind','') AS kind
          FROM conversation_messages
          WHERE conversation_id = ${firstConversation.ref}::uuid
            AND COALESCE(message_content->>'kind','') <> 'DECISION_LEDGER'
          ORDER BY sequence_no DESC
          LIMIT 20
        `,
      ))
    : [];
  const orderedMessages = [...messageRows].reverse();
  const conversationText = orderedMessages.map((row) => {
    const actorType = asText(row.actor_type);
    const label = actorType === "USER" ? "User"
      : actorType === "PROVIDER" ? "AI"
      : actorType === "SYSTEM" ? "System"
      : "Service";
    return `${label}: ${asText(row.text) ?? ""}`;
  }).filter((value) => !value.endsWith(": ")).join("\n");
  const latestAssistant = [...orderedMessages].reverse().find((row) => asText(row.actor_type) === "PROVIDER");
  const latestAssistantText = asText(latestAssistant?.text);
  const latestAssistantSummary = asText(latestAssistant?.assistant_summary) ?? latestAssistantText;
  const strategyAiRouteRows = await sql`
    SELECT g.id,
           count(*) FILTER (WHERE m.enabled=true AND p.enabled=true AND p.health_status='HEALTHY')::int AS healthy_members
    FROM acpos_runtime.provider_groups g
    LEFT JOIN acpos_runtime.provider_members m ON m.group_id=g.id
    LEFT JOIN acpos_runtime.provider_profiles p ON p.provider_id=m.provider_id AND p.model_id=m.model_id
    WHERE g.enabled=true AND g.use_case='ACPOS_TEXT_CHAT'
    GROUP BY g.id,g.updated_at
    ORDER BY g.updated_at DESC,g.id
    LIMIT 1
  `.catch(() => []);
  const strategyAiRoute = asRecord(Array.isArray(strategyAiRouteRows) ? strategyAiRouteRows[0] : null);
  const strategyMultiReady = Number(strategyAiRoute?.healthy_members ?? 0) > 0;

  const candidateState = firstCandidate?.label ?? null;
  const page_state = candidateState === "DECISION_PENDING"
    ? "REVIEW_REQUIRED"
    : candidateState === "APPROVED"
      ? "ADOPTED_CONTEXT"
      : firstCandidate
        ? "CANDIDATE_READY"
        : firstConversation || topics.length
          ? "READY"
          : "EMPTY";
  return {
    page_state,
    conversation_id: firstConversation?.ref ?? null,
    candidate_ref: firstCandidate?.ref ?? null,
    candidate_version_ref: firstCandidate?.version_ref ?? null,
    values: {
      "STR-01-FLD-TOPIC": topics[0]?.label ?? DASH,
      "STR-01-FLD-SCOPE": "workspace:STR-01",
      "STR-01-FLD-HORIZON": DASH,
      "STR-01-FLD-STATE": page_state,
      "STR-01-FLD-DECISION-STATE": page_state,
      "STR-01-FLD-BASIS": firstCandidate?.analysis_basis ?? DASH,
      "STR-01-FLD-RISKS": firstCandidate?.risk ?? DASH,
      "STR-01-FLD-UNCERTAINTY": firstCandidate?.uncertainty ?? DASH,
      "STR-01-FLD-CANDIDATE-REF": firstCandidate ? `${firstCandidate.ref} · ${firstCandidate.version_ref}` : DASH,
      "STR-01-FLD-REVIEW-STATE": asText(reviewRequestRow?.state) ?? page_state,
      "STR-01-FLD-DECISION-ID": asText(decisionRow?.decision_id) ?? DASH,
      "STR-01-FLD-DECISION-RESULT": asText(decisionRow?.decision) ?? DASH,
      "STR-01-FLD-DECISION-REASON": asText(decisionRow?.rationale) ?? asText(reviewRequestRow?.decision_reason) ?? DASH,
      "STR-01-FLD-EXECUTION-STATE": firstCandidate ? "OWNER_EXECUTION_NOT_PERFORMED" : DASH,
      "STR-01-FLD-ASSISTANT-SUMMARY": latestAssistantSummary ?? DASH,
      "STR-01-FLD-PROVIDER-BRAND": asText(latestAssistant?.actor_ref) ?? DASH,
    },
    lists: {
      "STR-01-LST-TOPICS": topics,
      "STR-01-LST-CONTEXT": conversations,
      "STR-01-LST-ALERTS": [],
      "STR-01-LST-PATTERNS": [],
      "STR-01-LST-EXPERIMENTS": [],
      "STR-01-LST-BASELINES": [],
      "STR-01-LST-LEARNING": [],
      "STR-01-LST-CANDIDATES": candidates,
    },
    blocks: {
      "STR-01-VIEW-CONVERSATION": conversationText || DASH,
      "STR-01-BLK-ASSISTANT": latestAssistantSummary ?? DASH,
    },
    gate_state: {
      "STR-01-GATE-PAGE": true,
      "STR-01-GATE-TOPIC": topics.length > 0,
      "STR-01-GATE-CONTEXT": Boolean(firstConversation),
      "STR-01-GATE-MESSAGE": Boolean(firstConversation),
      "STR-01-GATE-ANALYSIS": Boolean(latestAssistantText || firstCandidate?.analysis_basis),
      "STR-01-GATE-MULTI": strategyMultiReady,
      "STR-01-GATE-COMPARE": candidates.length >= 2,
      "STR-01-GATE-REVIEW": candidateState === "CANDIDATE",
      "STR-01-GATE-ADOPT": candidateState === "DECISION_PENDING" && approvedReviewReady,
    },
    owner_type: firstConversation ? "CONVERSATION" : null,
    owner_context_ref: firstConversation?.ref ?? null,
  };
}

async function readInfoFromDb(sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
  const packRows = await safeRows(() => runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
      SELECT
        f.fact_pack_id::text AS ref,
        f.workspace_id::text AS workspace_id,
        f.status::text AS status,
        f.scope::text AS scope,
        f.freshness_at::text AS freshness_at,
        f.completeness::text AS completeness,
        f.confidence::text AS confidence,
        f.classification::text AS classification,
        f.content_hash::text AS content_hash
      FROM fact_packs f
      ORDER BY f.freshness_at DESC
      LIMIT 50
    `,
  ));
  const packs = packRows.flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    const workspace_id = asText(row?.workspace_id);
    if (!ref || !workspace_id) return [];
    return [{
      ref,
      label: `FACT_PACK · ${asText(row?.status) ?? "APPROVED"} · ${asText(row?.completeness) ?? "0"}%`,
      workspace_id,
      status: asText(row?.status),
      scope: asText(row?.scope),
      freshness_at: asText(row?.freshness_at),
      completeness: asText(row?.completeness),
      confidence: asText(row?.confidence),
      classification: asText(row?.classification),
      content_hash: asText(row?.content_hash),
    }];
  });

  const candidateRows = await safeRows(() => runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
      SELECT
        c.context_candidate_id::text AS ref,
        c.decision_status::text AS status,
        c.target_scope::text AS target_scope,
        c.decision_reason,
        c.created_at::text AS created_at,
        f.workspace_id::text AS workspace_id,
        f.fact_pack_id::text AS fact_pack_ref,
        f.evidence_refs::text AS evidence_refs,
        f.classification::text AS classification
      FROM context_candidates c
      JOIN fact_packs f ON f.fact_pack_id=c.fact_pack_id
      ORDER BY c.created_at DESC
      LIMIT 50
    `,
  ));
  const candidates = candidateRows.flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    if (!ref) return [];
    return [{
      ref,
      label: `CONTEXT_CANDIDATE · ${asText(row?.status) ?? "CANDIDATE"}`,
      status: asText(row?.status),
      target_scope: asText(row?.target_scope),
      decision_reason: asText(row?.decision_reason),
      created_at: asText(row?.created_at),
      workspace_id: asText(row?.workspace_id),
      fact_pack_ref: asText(row?.fact_pack_ref),
      evidence_refs: asText(row?.evidence_refs),
      classification: asText(row?.classification),
    }];
  });

  const firstPack = packs[0] ?? null;
  const firstCandidate = candidates[0] ?? null;
  const page_state = firstCandidate
    ? "CONTEXT_CANDIDATE"
    : firstPack
      ? "READY"
      : "EMPTY";
  const projectionVersion = firstPack?.content_hash ?? "info:empty";
  const authorizedScope = firstPack?.workspace_id ?? "workspace:INFO-01";
  const workspaceFilters = [...new Map(
    packs.map((item) => [item.workspace_id, { ref: item.workspace_id, label: item.workspace_id }]),
  ).values()];

  return {
    page_state,
    projection_version: projectionVersion,
    authorized_scope: authorizedScope,
    last_refresh: firstPack?.freshness_at ?? null,
    values: {
      "INFO-01-FLD-SCOPE": authorizedScope,
      "INFO-01-FLD-PROJECTION-VERSION": projectionVersion,
      "INFO-01-FLD-PAGE-STATE": page_state,
      "INFO-01-FLD-LAST-REFRESH": firstPack?.freshness_at ?? DASH,
      "INFO-01-FLD-SOURCE-REF": DASH,
      "INFO-01-FLD-FACTPACK-REF": firstPack?.ref ?? DASH,
      "INFO-01-FLD-FACTPACK-SCOPE": firstPack?.scope ?? DASH,
      "INFO-01-FLD-FACTPACK-STATE": firstPack?.status ?? DASH,
      "INFO-01-FLD-FRESHNESS": firstPack?.freshness_at ?? DASH,
      "INFO-01-FLD-COMPLETENESS": firstPack?.completeness ?? DASH,
      "INFO-01-FLD-CONFIDENCE": firstPack?.confidence ?? DASH,
      "INFO-01-FLD-CANDIDATE-ID": firstCandidate?.ref ?? DASH,
      "INFO-01-FLD-CANDIDATE-SCOPE": firstCandidate?.target_scope ?? DASH,
      "INFO-01-FLD-CANDIDATE-CITATIONS": firstCandidate?.evidence_refs ?? DASH,
      "INFO-01-FLD-CANDIDATE-STATE": firstCandidate?.status ?? DASH,
      "INFO-01-FLD-ADOPTION-REVIEW": firstCandidate?.decision_reason ?? DASH,
      "INFO-01-FLD-DISABLED": "Evidence/source lineage and Export owner stay fail-closed until materialized",
    },
    lists: {
      "INFO-01-LST-SOURCES": [],
      "INFO-01-LST-ALERTS": [],
      "INFO-01-LST-FACTPACKS": packs.map(({ ref, label }) => ({ ref, label })),
      "INFO-01-LST-FACTS": [],
      "INFO-01-LST-INFERENCES": [],
      "INFO-01-LST-EVIDENCE": [],
      "INFO-01-LST-RESEARCH": [],
      "INFO-01-LST-CANDIDATES": candidates.map(({ ref, label }) => ({ ref, label })),
    },
    filters: {
      "INFO-01-SEL-SCOPE": workspaceFilters,
    },
    gate_state: {
      "INFO-01-GATE-PAGE": true,
      "INFO-01-GATE-READ": true,
      "INFO-01-GATE-FACTPACK": packs.length > 0,
      "INFO-01-GATE-EVIDENCE": false,
      "INFO-01-GATE-REFRESH": true,
      "INFO-01-GATE-SEARCH": true,
      "INFO-01-GATE-EXPORT": false,
      "INFO-01-GATE-CANDIDATE": candidates.length > 0,
      "INFO-01-GATE-ADOPT": firstCandidate?.status === "CANDIDATE",
      "INFO-01-GATE-DECIDE": firstCandidate?.status === "CANDIDATE",
    },
  };
}

async function readSystemFromDb(
  sql: SqlClient,
  sessionTokenHash: string,
): Promise<unknown> {
  const migrations = await safeRows(() => sql`
    SELECT migration_id AS ref, checksum, applied_at::text AS applied_at
    FROM schema_migration_history
    ORDER BY applied_at
  `);
  const snapshots = await safeRows(() => sql`
    SELECT context_snapshot_id::text AS ref, context_snapshot_hash AS hash
    FROM multi_ai_context_snapshots
    ORDER BY version_no DESC
    LIMIT 1
  `);
  const changes = await safeRows(() => runRlsActorQuery(
    sql,
    sessionTokenHash,
    sql`
      SELECT system_change_id::text AS system_change_id,current_goal,scope,status,
             current_candidate_id::text AS candidate_ref,updated_at::text AS updated_at
      FROM public.system_changes
      WHERE status <> 'CLOSED'
      ORDER BY updated_at DESC
      LIMIT 1
    `,
  ));
  const active = changes[0] ?? null;
  const systemChangeId = asText(active?.system_change_id);

  const candidate = systemChangeId && active?.candidate_ref
    ? (await safeRows(() => runRlsActorQuery(
        sql,
        sessionTokenHash,
        sql`
          SELECT context_fingerprint,status
          FROM public.system_change_candidates
          WHERE system_change_candidate_id=${asText(active.candidate_ref)}::uuid
            AND system_change_id=${systemChangeId}::uuid
          LIMIT 1
        `,
      )))[0] ?? null
    : null;

  let conversationId: string | null = null;
  let threadId: string | null = null;
  let messages: Array<{
    message_ref: string;
    role: "USER" | "ASSISTANT" | "SYSTEM";
    text: string;
    assistant_summary: string | null;
    response_mode: string | null;
    governance_status: string | null;
  }> = [];

  if (systemChangeId) {
    const conversationRows = await runRlsActorQuery(
      sql,
      sessionTokenHash,
      sql`
        SELECT conversation_id::text AS conversation_id
        FROM conversations
        WHERE conversation_id=${systemChangeId}::uuid
        LIMIT 1
      `,
    ).catch(() => []);
    conversationId = asText(asRecord(Array.isArray(conversationRows) ? conversationRows[0] : null)?.conversation_id);
    threadId = conversationId;

    if (conversationId) {
      const messageRows = await runRlsActorQuery(
        sql,
        sessionTokenHash,
        sql`
          SELECT conversation_message_id::text AS message_ref,
                 actor_type,
                 COALESCE(message_content->>'text','') AS text,
                 message_content->>'assistant_summary' AS assistant_summary,
                 message_content->>'response_mode' AS response_mode,
                 message_content->'governance'->>'status' AS governance_status,
                 COALESCE(message_content->>'kind','') AS kind
          FROM conversation_messages
          WHERE conversation_id=${conversationId}::uuid
            AND COALESCE(message_content->>'kind','') <> 'DECISION_LEDGER'
          ORDER BY sequence_no ASC
          LIMIT 80
        `,
      ).catch(() => []);
      messages = (Array.isArray(messageRows) ? messageRows : []).flatMap((raw) => {
        const row = asRecord(raw);
        const message_ref = asText(row?.message_ref);
        const text = asText(row?.text);
        if (!message_ref || !text) return [];
        const actorType = asText(row?.actor_type);
        const role: "USER" | "ASSISTANT" | "SYSTEM" =
          actorType === "USER" ? "USER" : actorType === "PROVIDER" ? "ASSISTANT" : "SYSTEM";
        return [{
          message_ref,
          role,
          text,
          assistant_summary: asText(row?.assistant_summary),
          response_mode: asText(row?.response_mode),
          governance_status: asText(row?.governance_status),
        }];
      });
    }
  }

  const generationRows = conversationId
    ? await sql`
        SELECT id,status,cancel_requested,updated_at::text AS updated_at
        FROM acpos_runtime.conversation_generation_jobs
        WHERE conversation_id=${conversationId}
        ORDER BY created_at DESC
        LIMIT 1
      `.catch(() => [])
    : [];
  const generation = asRecord(Array.isArray(generationRows) ? generationRows[0] : null);

  const aiGroupRows = await sql`
    SELECT g.id,
           count(*) FILTER (WHERE m.enabled=true AND p.enabled=true AND p.health_status='HEALTHY')::int AS healthy_members
    FROM acpos_runtime.provider_groups g
    LEFT JOIN acpos_runtime.provider_members m ON m.group_id=g.id
    LEFT JOIN acpos_runtime.provider_profiles p ON p.provider_id=m.provider_id AND p.model_id=m.model_id
    WHERE g.enabled=true AND g.use_case='ACPOS_TEXT_CHAT'
    GROUP BY g.id,g.updated_at
    ORDER BY g.updated_at DESC,g.id
    LIMIT 1
  `.catch(() => []);
  const aiGroup = asRecord(Array.isArray(aiGroupRows) ? aiGroupRows[0] : null);
  const healthyMembers = Number(aiGroup?.healthy_members ?? 0);
  const latestAssistant = [...messages].reverse().find((item) => item.role === "ASSISTANT");

  const head = migrations[migrations.length - 1] ?? null;
  const page_state = migrations.length || systemChangeId ? "READY" : "EMPTY";
  return {
    page_state,
    system_change_id: systemChangeId,
    conversation_id: conversationId,
    thread_id: threadId,
    branch_id: null,
    multi_ai_route_available: Boolean(conversationId && healthyMembers > 0),
    messages,
    values: {
      current_system_version: asText(head?.ref) ?? DASH,
      current_goal: asText(active?.current_goal) ?? DASH,
      scope: active?.scope ? JSON.stringify(active.scope) : "admin:SYS-01",
      candidate_ref: asText(active?.candidate_ref) ?? DASH,
      context_snapshot_ref: asText(snapshots[0]?.ref) ?? DASH,
      dependency_graph_ref: DASH,
      latest_context_fingerprint: asText(candidate?.context_fingerprint) ?? asText(head?.checksum) ?? asText(snapshots[0]?.hash) ?? DASH,
      assigned_ai_set: asText(aiGroup?.id) ?? DASH,
      healthy_ai_members: String(healthyMembers),
      assistant_summary: latestAssistant?.assistant_summary ?? DASH,
      response_mode: latestAssistant?.response_mode ?? DASH,
      conversation_runtime: conversationId ? "BOUND_SHARED_CONVERSATION_CORE" : "NOT_BOUND",
      generation_job_ref: asText(generation?.id) ?? DASH,
      generation_status: asText(generation?.status) ?? "IDLE",
      generation_cancel_requested: generation?.cancel_requested === true ? "true" : "false",
    },
  };
}

async function readDevFromDb(sql: SqlClient): Promise<unknown> {
  const jobs = await safeRows(() => sql`
    SELECT discovery_job_id::text AS ref, job_name AS label, status::text AS status, mode::text AS mode
    FROM outreach_discovery_jobs
    WHERE coalesce(stats->>'acceptance_scope','') <> 'GATE_24_DEV'
    ORDER BY created_at DESC
  `);
  const companies = await safeRows(() => sql`
    SELECT company_master_id::text AS ref, current_name AS label
    FROM company_master_entities
    ORDER BY created_at DESC
  `);
  const first = jobs[0] ?? null;
  const status = asText(first?.status);
  const run_status = status === "RUNNING" || status === "PAUSED" || status === "STOPPED" ? status : null;
  return {
    page_state: jobs.length || companies.length ? "READY" : "EMPTY",
    authorized_scope: "admin:DEV-01",
    run_status,
    values: {
      "DEV-01-FLD-JOB": asText(first?.label) ?? DASH,
      "DEV-01-FLD-JOB-REF": asText(first?.ref) ?? DASH,
      "DEV-01-FLD-JOB-STATUS": status ?? DASH,
      "DEV-01-FLD-MODE": asText(first?.mode) ?? DASH,
      "DEV-01-FLD-DIRECTORY": String(companies.length),
    },
    gate_state: {
      "DEV-01-GATE-PAGE": true,
      "DEV-01-GATE-DISCOVERY-START": run_status === null || run_status === "STOPPED",
      "DEV-01-GATE-DISCOVERY-RUNNING": run_status === "RUNNING",
      "DEV-01-GATE-DISCOVERY-PAUSED": run_status === "PAUSED",
      "DEV-01-GATE-DIRECTORY-READ": companies.length > 0,
    },
  };
}

async function readSocFromDb(sql: SqlClient): Promise<unknown> {
  const accounts = await safeRows(() => sql`
    SELECT channel_account_id::text AS ref, platform_key AS label, status::text AS status
    FROM channel_accounts
    ORDER BY channel_account_id
  `);
  const bindings = await safeRows(() => sql`
    SELECT social_account_binding_id::text AS ref, display_name AS label, status::text AS status, platform_key
    FROM social_account_bindings
    ORDER BY created_at DESC
  `);
  const targets = await safeRows(() => sql`
    SELECT social_target_id::text AS ref, target_name AS label, status::text AS status
    FROM social_market_targets
    ORDER BY social_target_id
  `);
  const packages = await safeRows(() => sql`
    SELECT content_package_id::text AS ref,
           release_package_id::text AS release_ref,
           channel_account_id::text AS channel_account_ref,
           status::text AS status,
           package_hash::text AS package_hash
    FROM content_packages
    ORDER BY created_at DESC
    LIMIT 20
  `);
  const drafts = await safeRows(() => sql`
    SELECT id::text AS ref,status,version::text AS version,payload
    FROM acpos_runtime.entities
    WHERE kind='SOC_CONTENT_DRAFT'
    ORDER BY updated_at DESC
    LIMIT 20
  `);
  const first = bindings[0] ?? accounts[0] ?? null;
  const contentPackage = packages[0] ?? null;
  const packageRef = asText(contentPackage?.ref);
  const candidate = packageRef
    ? drafts.find((row) => asText(asRecord(row.payload)?.content_package_id) === packageRef) ?? null
    : null;
  const candidateStatus = asText(candidate?.status);
  return {
    page_state: first || contentPackage ? "READY" : "EMPTY",
    values: {
      "SOC-01-FLD-PLATFORM": asText(first && "platform_key" in first ? first.platform_key : first?.label) ?? DASH,
      "SOC-01-FLD-ACCOUNT": asText(first?.label) ?? DASH,
      "SOC-01-FLD-ACCOUNT-STATUS": asText(first?.status) ?? DASH,
      "SOC-01-FLD-TARGET-COUNT": String(targets.length),
      "SOC-01-FLD-RELEASE-SOURCE": asText(contentPackage?.release_ref) ?? DASH,
      "SOC-01-FLD-CONTENT-PACKAGE": packageRef ?? DASH,
      "SOC-01-FLD-CHANNEL-ACCOUNT": asText(contentPackage?.channel_account_ref) ?? DASH,
      "SOC-01-FLD-APPROVAL": candidate ? `${asText(candidate.ref) ?? DASH} · ${candidateStatus ?? "DRAFT"}` : "DRAFT_NOT_CREATED",
      "SOC-01-FLD-CANDIDATE-REF": asText(candidate?.ref) ?? DASH,
      "SOC-01-FLD-CANDIDATE-VERSION": asText(candidate?.version) ?? DASH,
    },
    gate_state: {
      "SOC-01-GATE-PAGE": true,
      "SOC-01-GATE-READ": true,
      "SOC-01-GATE-CONTENT": Boolean(contentPackage),
      "SOC-01-GATE-CANDIDATE": candidateStatus === "REVIEW",
      "SOC-01-GATE-PUBLISH": candidateStatus === "APPROVED" && targets.length > 0,
      "SOC-01-GATE-RECORDS": true,
    },
  };
}

async function readErpFromDb(sql: SqlClient): Promise<unknown> {
  const connectors = await safeRows(() => sql`
    SELECT erp_connector_id::text AS ref,
           provider_key AS label,
           adapter_key,
           connection_status,
           configuration_version::text AS configuration_version,
           CASE
             WHEN jsonb_typeof(entity_scope)='string' THEN entity_scope #>> '{}'
             ELSE entity_scope::text
           END AS entity_scope_text
    FROM erp_connectors
    ORDER BY created_at DESC,erp_connector_id DESC
  `);
  const snapshots = await safeRows(() => sql`
    SELECT erp_snapshot_id::text AS ref,
           erp_connector_id::text AS connector_ref,
           snapshot_type,
           completeness::text AS completeness,
           freshness_at::text AS freshness_at,
           status::text AS status,
           floor(extract(epoch FROM created_at) * 1000)::bigint::text AS version
    FROM erp_snapshots
    ORDER BY created_at DESC,erp_snapshot_id DESC
  `);
  const jobs = await safeRows(() => sql`
    SELECT erp_sync_job_id::text AS ref,
           erp_connector_id::text AS connector_ref,
           status::text AS status,
           requested_scope,
           attempt_no::text AS attempt_no
    FROM erp_sync_jobs
    ORDER BY requested_at DESC,erp_sync_job_id DESC
  `);
  const failures = await safeRows(() => sql`
    SELECT erp_failure_id::text AS ref,
           erp_connector_id::text AS connector_ref,
           erp_sync_job_id::text AS job_ref,
           failure_code,
           retryable,
           status::text AS status
    FROM erp_failures
    ORDER BY occurred_at DESC,erp_failure_id DESC
  `);
  const first = connectors[0] ?? null;
  const connectorRef = asText(first?.ref);
  const snapshot = connectorRef
    ? snapshots.find((row) => asText(row.connector_ref) === connectorRef) ?? null
    : null;
  const latestJob = connectorRef
    ? jobs.find((row) => asText(row.connector_ref) === connectorRef) ?? null
    : null;
  const latestFailure = latestJob
    ? failures.find((row) => asText(row.job_ref) === asText(latestJob.ref)) ?? null
    : connectorRef
      ? failures.find((row) => asText(row.connector_ref) === connectorRef) ?? null
      : null;
  const connectionStatus = asText(first?.connection_status);
  const latestJobStatus = asText(latestJob?.status);
  const activeRefresh = latestJobStatus === "QUEUED" || latestJobStatus === "RUNNING" || latestJobStatus === "PENDING_EXTERNAL";
  const snapshotRefreshReady = Boolean(
    first
    && snapshot
    && (connectionStatus === "READY" || connectionStatus === "DEGRADED")
    && !activeRefresh
  );
  const requestedScope = asText(first?.entity_scope_text) ?? "";
  return {
    page_state: first || snapshot ? "READY" : "EMPTY",
    values: {
      "ERP-01-FLD-PROVIDER": asText(first?.label) ?? DASH,
      "ERP-01-FLD-ADAPTER": asText(first?.adapter_key) ?? DASH,
      "ERP-01-FLD-CONNECTION-STATUS": connectionStatus ?? DASH,
      "ERP-01-FLD-CONFIG-VERSION": asText(first?.configuration_version) ?? DASH,
      "ERP-01-FLD-SNAPSHOT": snapshot ? `${asText(snapshot.ref) ?? DASH} · ${asText(snapshot.status) ?? DASH}` : DASH,
      "ERP-01-FLD-FRESHNESS": asText(snapshot?.freshness_at) ?? DASH,
      "ERP-01-FLD-SYNC-SNAPSHOT-ID": asText(snapshot?.ref) ?? DASH,
      "ERP-01-FLD-SYNC-FRESHNESS-AT": asText(snapshot?.freshness_at) ?? DASH,
      "ERP-01-FLD-SYNC-COMPLETENESS": asText(snapshot?.completeness) ?? DASH,
      "ERP-01-FLD-SYNC-LAST-SYNC-STATUS": latestJobStatus ?? DASH,
      "ERP-01-FLD-SYNC-STATUS": latestJobStatus ?? DASH,
      "ERP-01-FLD-SYNC-FAILURE-ID": latestFailure
        ? `${asText(latestFailure.ref) ?? DASH} · ${asText(latestFailure.failure_code) ?? DASH}`
        : DASH,
    },
    gate_state: {
      "ERP-01-GATE-PAGE": true,
      "ERP-01-GATE-CONNECTOR-READ": Boolean(first),
      "ERP-01-GATE-SYNC-READ": Boolean(snapshot || latestJob),
      "ERP-01-GATE-SNAPSHOT-REFRESH": snapshotRefreshReady,
      "ERP-01-GATE-FINANCE": Boolean(snapshot),
    },
    selected: first ? {
      connector_id: connectorRef ?? "",
      connector_version: asText(first.configuration_version) ?? "",
      snapshot_id: asText(snapshot?.ref) ?? "",
      snapshot_version: asText(snapshot?.version) ?? "",
      sync_job_id: asText(latestJob?.ref) ?? "",
      sync_job_version: asText(latestJob?.attempt_no) ?? "",
      failure_id: asText(latestFailure?.ref) ?? "",
      failure_version: "1",
      requested_scope: requestedScope,
    } : {},
    form_schemas: snapshotRefreshReady ? {
      "ERP-01-BTN-SNAPSHOT-REFRESH": [
        { key: "requested_scope", type: "text", required: true },
      ],
    } : {},
  };
}

async function readAiApiFromDb(sql: SqlClient): Promise<unknown> {
  const profiles = await safeRows(() => sql`
    SELECT p.id AS profile_id,
           p.provider_id,
           p.provider_id AS provider_name,
           p.model_id,
           p.model_id AS model_name,
           p.capability_type AS capability,
           p.adapter_type AS adapter,
           p.base_url,
           p.endpoint_path AS endpoint,
           p.timeout_seconds,
           p.enabled,
           p.health_status,
           p.secret_env_ref,
           p.version,
           p.updated_at::text AS updated_at
    FROM acpos_runtime.provider_profiles p
    ORDER BY p.provider_id, p.model_id
  `);
  const tests = await safeRows(() => sql`
    SELECT DISTINCT ON (profile_id)
           profile_id,
           status,
           dry_run,
           error_code,
           created_at::text AS created_at
    FROM acpos_runtime.provider_profile_tests
    ORDER BY profile_id, created_at DESC
  `);
  const capabilities = await safeRows(() => sql`
    SELECT provider_key, model_key, capability_version, status::text AS status, limits
    FROM provider_capabilities
    ORDER BY provider_key, model_key, capability_version DESC
  `);
  const secretRefs = await safeRows(() => sql`
    SELECT secret_key, status::text AS status, provider_key
    FROM secret_references
    ORDER BY created_at DESC
  `);

  const provider_rows = profiles.map((row) => {
    const profile_id = asText(row.profile_id) ?? "";
    const provider_id = asText(row.provider_id) ?? "";
    const model_id = asText(row.model_id) ?? DASH;
    const secret_env_ref = asText(row.secret_env_ref);
    const secret = secret_env_ref
      ? secretRefs.find((item) => asText(item.secret_key) === secret_env_ref) ?? null
      : null;
    const environmentBound = secret_env_ref ? Boolean(process.env[secret_env_ref]) : false;
    const capability = capabilities.find((item) =>
      asText(item.provider_key) === provider_id && asText(item.model_key) === model_id
    ) ?? null;
    const lastTest = tests.find((item) => asText(item.profile_id) === profile_id) ?? null;
    return {
      profile_id,
      provider_id,
      provider_name: asText(row.provider_name) ?? provider_id,
      model_id,
      model_name: asText(row.model_name) ?? model_id,
      capability: asText(row.capability) ?? DASH,
      adapter: asText(row.adapter) ?? DASH,
      base_url: asText(row.base_url) ?? DASH,
      endpoint: asText(row.endpoint) ?? DASH,
      timeout: row.timeout_seconds == null ? DASH : `${String(row.timeout_seconds)}s`,
      enabled: row.enabled === true ? "ENABLED" : "DISABLED",
      credential_status: secret && environmentBound && asText(secret.status) === "APPROVED" ? "SET" : "NOT_SET",
      last_test: asText(lastTest?.created_at) ?? DASH,
      capability_status: asText(capability?.status) ?? "NOT_REGISTERED",
      capability_version: asText(capability?.capability_version) ?? DASH,
      health_status: asText(row.health_status) ?? "UNKNOWN",
      version: row.version ?? null,
    };
  }).filter((row) => row.profile_id && row.provider_id);

  const selected = provider_rows[0] ?? null;
  return {
    page_state: provider_rows.length ? "READY" : "EMPTY",
    values: {
      "AIAPI-01-FLD-PROVIDER-COUNT": String(provider_rows.length),
      "AIAPI-01-FLD-SELECTED": selected?.profile_id ?? DASH,
      "provider.selected": selected ? `${selected.provider_id}/${selected.model_id}` : DASH,
      "AIAPI-01-PRO-DESC-IDENTITY": selected ? `${selected.provider_id} / ${selected.model_id}` : DASH,
      "AIAPI-01-PRO-DESC-POSITIONING": selected?.capability ?? DASH,
      "AIAPI-01-PRO-DESC-ACPOS-SCOPE": selected?.capability_status ?? DASH,
      "AIAPI-01-PRO-DESC-CAPABILITIES": selected?.capability ?? DASH,
      "AIAPI-01-PRO-DESC-INPUT": selected?.adapter ?? DASH,
      "AIAPI-01-PRO-DESC-OUTPUT": selected?.adapter ?? DASH,
      "AIAPI-01-PRO-DESC-LIMITS": selected?.timeout ?? DASH,
      "AIAPI-01-PRO-DESC-ENDPOINT": selected ? `${selected.base_url}${selected.endpoint}` : DASH,
      "AIAPI-01-PRO-DESC-AUTH": selected?.credential_status ?? DASH,
      "AIAPI-01-PRO-DESC-BILLING": DASH,
      "AIAPI-01-PRO-DESC-HEALTH": selected?.health_status ?? DASH,
      "AIAPI-01-PRO-DESC-LAST-TEST": selected?.last_test ?? DASH,
      "AIAPI-01-PRO-DESC-RECOMMENDED-USE": selected?.capability_status === "APPROVED" ? selected.capability : DASH,
      "AIAPI-01-PRO-DESC-RESTRICTIONS": selected?.capability_status ?? DASH,
      "AIAPI-01-PRO-DESC-DOCS": DASH,
    },
    control_enabled: {
      createProviderModelProfile: true,
      listProviderModelProfiles: true,
      getProviderModelProfile: provider_rows.length > 0,
      updateProviderModelProfile: provider_rows.length > 0,
      retireProviderModelProfile: provider_rows.length > 0,
      setProviderModelCredential: provider_rows.length > 0,
      deleteProviderModelCredential: provider_rows.some((row) => row.credential_status === "SET"),
      testProviderModelProfile: provider_rows.some((row) => row.credential_status === "SET"),
      createProviderCandidateGroup: provider_rows.length > 0,
      getProviderQuarantine: true,
      restoreProviderFromQuarantine: true,
      runSandboxTest: provider_rows.length > 0,
      executeProviderRoute: provider_rows.length > 0,
      getProviderRouteDecision: true,
      setKillSwitch: provider_rows.length > 0,
    },
    provider_rows,
    selected_resource_id: selected?.profile_id ?? null,
  };
}

async function readSg02FromDb(
  sql: SqlClient,
  sessionTokenHash: string,
  actorUserId: string,
): Promise<unknown> {
  const versions = await safeRows(() => sql`
    SELECT criteria_version_id::text AS criteria_version_id,
           criteria_key,
           version_no::text AS version_no,
           department::text AS department,
           dimensions,
           required_checks,
           gate_policy,
           status::text AS status
    FROM quality_criteria_versions
    ORDER BY criteria_key, version_no DESC
  `);
  const first = versions[0] ?? null;
  const [canConfigure, canApprove] = await Promise.all([
    evaluateCatalogResourceAction(sql, sessionTokenHash, actorUserId, "action:admin:SG-02:ACT-CONFIGURE", "INVOKE"),
    evaluateCatalogResourceAction(sql, sessionTokenHash, actorUserId, "action:admin:SG-02:ACT-APPROVE", "INVOKE"),
  ]);
  return {
    page_state: versions.length ? "READY" : "EMPTY",
    values: {
      criteria_versions: versions.map((row) => ({
        ref: asText(row.criteria_version_id),
        key: asText(row.criteria_key),
        version_no: asText(row.version_no),
        department: asText(row.department),
        status: asText(row.status),
      })),
      dimensions: first?.dimensions ?? null,
      required_checks: first?.required_checks ?? null,
      gate_policy: first?.gate_policy ?? null,
      department_mapping: asText(first?.department) ?? DASH,
      thresholds: first?.gate_policy ?? null,
      policies: first?.gate_policy ?? null,
      mappings: asText(first?.department) ?? DASH,
      approvals: asText(first?.status) ?? DASH,
      audit_ref: DASH,
    },
    control_enabled: {
      "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE": canConfigure,
      "CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE": canApprove,
      "CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN": true,
    },
  };
}

async function readStrategyAdminFromDb(
  sql: SqlClient,
  sessionTokenHash: string,
  actorUserId: string,
): Promise<unknown> {
  const candidates = await safeRows(() => sql`
    SELECT s.strategy_candidate_id::text AS ref, s.decision_status::text AS status, s.confidence::text AS confidence, s.freshness_at::text AS freshness_at
    FROM strategy_candidates s
    ORDER BY s.created_at DESC
  `);
  const decisions = await safeRows(() => sql`
    SELECT d.strategy_decision_id::text AS ref, d.decision AS label, d.rationale
    FROM strategy_decisions d
    ORDER BY d.created_at DESC
  `);
  const packs = await safeRows(() => sql`
    SELECT f.fact_pack_id::text AS ref, f.completeness::text AS completeness, f.confidence::text AS confidence, f.freshness_at::text AS freshness_at
    FROM fact_packs f
    ORDER BY f.created_at DESC
  `);
  const sources = await safeRows(() => sql`
    SELECT k.knowledge_source_id::text AS ref, k.status::text AS status
    FROM knowledge_sources k
    ORDER BY k.created_at DESC
  `);
  const first = candidates[0] ?? null;
  const strategyActionResources = {
    "admin:STR-01::ACT-SEARCH": "action:admin:STR-01:ACT-SEARCH",
    "admin:STR-01::ACT-REFRESH": "action:admin:STR-01:ACT-REFRESH",
    "admin:STR-02::ACT-CONFIGURE": "action:admin:STR-02:ACT-CONFIGURE",
    "admin:STR-02::ACT-APPROVE": "action:admin:STR-02:ACT-APPROVE",
    "admin:STR-03::ACT-DRAFT-SAVE": "action:admin:STR-03:ACT-DRAFT-SAVE",
    "admin:STR-03::ACT-APPROVE": "action:admin:STR-03:ACT-APPROVE",
    "admin:STR-04::ACT-SEARCH": "action:admin:STR-04:ACT-SEARCH",
    "admin:STR-04::ACT-EXPORT": "action:admin:STR-04:ACT-EXPORT",
    "admin:STR-05::ACT-CANDIDATE-CREATE": "action:admin:STR-05:ACT-CANDIDATE-CREATE",
    "admin:STR-05::ACT-APPROVE": "action:admin:STR-05:ACT-APPROVE",
    "admin:STR-06::ACT-CANDIDATE-COMPARE": "action:admin:STR-06:ACT-CANDIDATE-COMPARE",
    "admin:STR-06::ACT-CANDIDATE-DECIDE": "action:admin:STR-06:ACT-CANDIDATE-DECIDE",
    "admin:STR-06::ACT-ADOPT-CONTEXT": "action:admin:STR-06:ACT-ADOPT-CONTEXT",
  } as const;
  const actionEnabledEntries = await Promise.all(
    Object.entries(strategyActionResources).map(async ([key, resourceKey]) => [
      key,
      await evaluateCatalogResourceAction(sql, sessionTokenHash, actorUserId, resourceKey, "INVOKE"),
    ] as const),
  );
  return {
    page_state: first || packs.length ? "READY" : "EMPTY",
    values: {
      "Intelligence Summary": asText(first?.status) ?? DASH,
      "Source Health": String(sources.length),
      "Fact Quality": asText(packs[0]?.completeness) ?? DASH,
      "Watchlist": DASH,
      "Risk Alert": DASH,
      "Candidate Queue": String(candidates.length),
    },
    evidence: {
      "Intelligence Summary": asText(first?.ref) ?? DASH,
      "Fact Quality": asText(packs[0]?.ref) ?? DASH,
      "Candidate Queue": asText(decisions[0]?.label) ?? DASH,
    },
    states: {
      candidate: asText(first?.status) ?? DASH,
      fact_pack: asText(packs[0]?.freshness_at) ?? DASH,
    },
    action_enabled: Object.fromEntries(actionEnabledEntries),
    selected_resource_id: asText(first?.ref) ?? null,
  };
}

async function readKnowledgeFromDb(sql: SqlClient): Promise<unknown> {
  const sources = await safeRows(() => sql`
    SELECT knowledge_source_id::text AS ref,
           source_key AS label,
           status::text AS status,
           source_uri,
           classification::text AS classification,
           source_version::text AS source_version
    FROM knowledge_sources
    ORDER BY created_at DESC,knowledge_source_id DESC
  `);
  const evidence = await safeRows(() => sql`
    SELECT evidence_record_id::text AS ref
    FROM evidence_records
    ORDER BY retrieved_at DESC
  `);
  const packs = await safeRows(() => sql`
    SELECT fact_pack_id::text AS ref, status::text AS status, completeness::text AS completeness
    FROM fact_packs
    ORDER BY created_at DESC
  `);
  const candidates = await safeRows(() => sql`
    SELECT context_candidate_id::text AS ref, decision_status::text AS status
    FROM context_candidates
    ORDER BY created_at DESC
  `);
  const first = sources[0] ?? null;
  const approved = sources.filter((row) => asText(row.status) === "ACTIVE");
  return {
    page_state: sources.length || packs.length ? "READY" : "EMPTY",
    values: {
      "KB-01-FLD-SCOPE": "admin:KB-01",
      "KB-01-FLD-SOURCE-ID": asText(first?.ref) ?? DASH,
      "KB-01-FLD-SOURCE-STATUS": asText(first?.status) ?? DASH,
      "KB-01-FLD-SOURCE-URI": asText(first?.source_uri) ?? DASH,
      "KB-01-FLD-CTX-CAND-ITEMS": candidates,
      Source: String(sources.length),
      Ingestion: String(evidence.length),
      Experience: DASH,
      Review: String(candidates.length),
      "Approved Knowledge": String(approved.length),
    },
    control_enabled: {
      "KB-01-CTL-SEARCH-GLOBAL": true,
      "KB-01-CTL-SOURCE-PAUSE": asText(first?.status) === "ACTIVE",
      "KB-01-CTL-SOURCE-RESUME": asText(first?.status) === "PAUSED",
    },
    entities: first ? {
      selected_source: {
        source_id: asText(first.ref) ?? "",
        source_version: asText(first.source_version) ?? "",
        name: asText(first.label) ?? "",
        source_uri: asText(first.source_uri) ?? "",
        classification: asText(first.classification) ?? "",
        status: asText(first.status) ?? "",
      },
    } : {},
  };
}

async function readPageValue(
  pageUid: string,
  sql: SqlClient,
  sessionTokenHash: string,
  actorUserId: string,
): Promise<unknown> {
  switch (pageUid) {
    case "CORE-01":
      return readCoreProjection(sql, sessionTokenHash);
    case "ASSET-01":
      return readAssetFromDb(sql, sessionTokenHash);
    case "VIDEO-01":
      return readVideoFromDb(sql, sessionTokenHash);
    case "EDIT-01":
      return readEditFromDb(sql, sessionTokenHash);
    case "QA-01":
      return readQaFromDb(sql, sessionTokenHash);
    case "admin:DB-01":
      return readDbCatalogProjection(sql);
    case "workspace:STR-01":
      return readStrategyFromDb(sql, sessionTokenHash);
    case "workspace:INFO-01":
      return readInfoFromDb(sql, sessionTokenHash);
    case "admin:SYS-01":
      return readSystemFromDb(sql, sessionTokenHash);
    case "admin:IAM-01":
      return readIamProjection(sql);
    case "admin:DEV-01":
      return readDevFromDb(sql);
    case "admin:SOC-01":
      return readSocFromDb(sql);
    case "admin:ERP-01":
      return readErpFromDb(sql);
    case "admin:AIAPI-01":
      return readAiApiFromDb(sql);
    case "admin:SG-02":
      return readSg02FromDb(sql, sessionTokenHash, actorUserId);
    case "admin:STR-01":
      return readStrategyAdminFromDb(sql, sessionTokenHash, actorUserId);
    case "admin:KB-01":
      return readKnowledgeFromDb(sql);
    default:
      return null;
  }
}

export async function readCatalogPageProjection(request: UiProjectionRequest) {
  const resourceKey = CURRENT_PAGE_RESOURCE_KEYS[request.page_uid];
  if (!resourceKey) return null;

  const decision = await evaluatePageViewGate(resourceKey);
  if (!decision.allowed) {
    const status = decision.reason_code === "DATABASE_RUNTIME_NOT_BOUND" ? 503 : 403;
    return { ok: false as const, status, reason_code: decision.reason_code, correlation_id: request.correlation_id };
  }

  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) {
    return { ok: false as const, status: 503, reason_code: "DATABASE_RUNTIME_NOT_BOUND", correlation_id: request.correlation_id };
  }

  try {
    const value = await readPageValue(
      request.page_uid,
      sql,
      decision.session_token_hash,
      decision.actor_user_id,
    );
    if (value == null) return null;
    return { ok: true as const, value, correlation_id: request.correlation_id };
  } catch {
    return { ok: false as const, status: 503, reason_code: "UI_PROJECTION_READ_FAILED", correlation_id: request.correlation_id };
  }
}
