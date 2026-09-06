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
  | { allowed: true; session_token_hash: string }
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
    if (matched.some((row) => row.effect === "ALLOW")) return { allowed: true, session_token_hash: sessionTokenHash };
    return { allowed: false, reason_code: "PERMISSION_OR_SCOPE_DENIED" };
  } catch {
    return { allowed: false, reason_code: "AUTHORIZATION_EVALUATION_FAILED" };
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
             tp.title AS topic_label
      FROM department_tasks t
      JOIN child_locks cl ON cl.child_lock_id = t.child_lock_id
      JOIN topics tp ON tp.topic_id = cl.topic_id
      JOIN projects p ON p.project_id = tp.project_id
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
  return {
    refs: {
      project_id: first?.project_id ?? null,
      project_version_ref: first?.project_version_ref ?? null,
      topic_id: topics[0]?.topic_id ?? null,
      topic_version_ref: topics[0]?.topic_version_ref ?? null,
      dna_version_ref: null,
      blueprint_version_ref: null,
      conversation_id: threads[0]?.conversation_id ?? null,
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
    display_values: {
      page_mode: "PROJECT_CORE",
      assigned_ai_set: DASH,
      project_state: first?.status ?? DASH,
      story_candidate_set: DASH,
      dna_state: DASH,
      blueprint_state: DASH,
      assistant_summary: DASH,
      evaluation: DASH,
      structured_decision: DASH,
      runtime_stage: "READY",
      topic_scope: DASH,
      canonical_script: DASH,
      package: DASH,
      downstream_asset: DASH,
      downstream_video: DASH,
      downstream_edit: DASH,
      version_state: DASH,
      candidate_compare: DASH,
      lock_review: DASH,
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
    target_output_version_id: asText(reviewRow?.target_output_version_id) ?? asText(scorecards[0]?.output_version_id) ?? null,
    scorecard_ref: asText(scorecards[0]?.scorecard_id) ?? null,
    values: {
      "QA-01-FLD-PROJECT": first?.project_label ?? projects[0]?.label ?? DASH,
      "QA-01-FLD-TOPIC": first?.topic_label ?? topics[0]?.label ?? DASH,
      "QA-01-FLD-QA-TASK": first?.task_id ?? DASH,
      "QA-01-FLD-TARGET-OUTPUT": asText(reviewRow?.target_output_version_id) ?? DASH,
      "QA-01-FLD-REVIEW-STATE": asText(reviewRow?.status) ?? first?.status ?? DASH,
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
    gate_state: { "QA-01-GATE-PAGE": true },
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
  const candidates = refList(await safeRows(() => sql`
    SELECT s.strategy_candidate_id::text AS ref, s.decision_status::text AS label
    FROM strategy_candidates s
    ORDER BY s.created_at DESC
  `));
  const firstConversation = conversations[0] ?? null;
  const firstCandidate = candidates[0] ?? null;
  const page_state = firstCandidate ? "CANDIDATE_READY" : firstConversation || topics.length ? "READY" : "EMPTY";
  return {
    page_state,
    conversation_id: firstConversation?.ref ?? null,
    candidate_ref: firstCandidate?.ref ?? null,
    candidate_version_ref: null,
    values: {
      "STR-01-FLD-TOPIC": topics[0]?.label ?? DASH,
      "STR-01-FLD-SCOPE": "workspace:STR-01",
      "STR-01-FLD-HORIZON": DASH,
      "STR-01-FLD-STATE": page_state,
      "STR-01-FLD-DECISION-STATE": firstCandidate?.label ?? DASH,
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
      "STR-01-BLK-ASSISTANT": DASH,
    },
    gate_state: {
      "STR-01-GATE-PAGE": true,
      "STR-01-GATE-TOPIC": topics.length > 0,
      "STR-01-GATE-MESSAGE": Boolean(firstConversation),
    },
    owner_type: firstConversation ? "CONVERSATION" : null,
    owner_context_ref: firstConversation?.ref ?? null,
  };
}

async function readInfoFromDb(sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
  const sources = refList(await safeRows(() => sql`
    SELECT k.knowledge_source_id::text AS ref, k.source_key AS label
    FROM knowledge_sources k
    ORDER BY k.created_at DESC
  `));
  const projects = await readProjectRefs(sql, sessionTokenHash);
  const packs = await safeRows(() => sql`
    SELECT f.fact_pack_id::text AS ref, f.freshness_at::text AS freshness_at
    FROM fact_packs f
    ORDER BY f.freshness_at DESC
    LIMIT 1
  `);
  const combined = sources.length ? sources : projects;
  const page_state = combined.length ? "READY" : "EMPTY";
  return {
    page_state,
    projection_version: "neon:wild-wave",
    authorized_scope: "workspace:INFO-01",
    last_refresh: asText(packs[0]?.freshness_at) ?? null,
    values: {
      "INFO-01-FLD-SCOPE": "workspace:INFO-01",
      "INFO-01-FLD-PROJECTION-VERSION": "neon:wild-wave",
      "INFO-01-FLD-PAGE-STATE": page_state,
      "INFO-01-FLD-LAST-REFRESH": asText(packs[0]?.freshness_at) ?? DASH,
      "INFO-01-FLD-SOURCE-REF": combined[0]?.ref ?? DASH,
    },
    lists: {
      "INFO-01-LST-SOURCES": combined,
    },
    filters: {},
    gate_state: {
      "INFO-01-GATE-PAGE": true,
      "INFO-01-GATE-SEARCH": true,
      "INFO-01-GATE-REFRESH": true,
    },
  };
}

async function readSystemFromDb(sql: SqlClient): Promise<unknown> {
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
  const head = migrations[migrations.length - 1] ?? null;
  const page_state = migrations.length ? "READY" : "EMPTY";
  return {
    page_state,
    system_change_id: null,
    conversation_id: null,
    thread_id: null,
    branch_id: null,
    multi_ai_route_available: false,
    values: {
      current_system_version: asText(head?.ref) ?? DASH,
      current_goal: DASH,
      scope: "admin:SYS-01",
      candidate_ref: DASH,
      context_snapshot_ref: asText(snapshots[0]?.ref) ?? DASH,
      dependency_graph_ref: DASH,
      latest_context_fingerprint: asText(head?.checksum) ?? asText(snapshots[0]?.hash) ?? DASH,
    },
  };
}

async function readDevFromDb(sql: SqlClient): Promise<unknown> {
  const jobs = await safeRows(() => sql`
    SELECT discovery_job_id::text AS ref, job_name AS label, status::text AS status, mode::text AS mode
    FROM outreach_discovery_jobs
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
      "DEV-01-FLD-JOB-STATUS": status ?? DASH,
      "DEV-01-FLD-MODE": asText(first?.mode) ?? DASH,
      "DEV-01-FLD-DIRECTORY": String(companies.length),
    },
    gate_state: {
      "DEV-01-GATE-PAGE": true,
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
  const first = bindings[0] ?? accounts[0] ?? null;
  return {
    page_state: first ? "READY" : "EMPTY",
    values: {
      "SOC-01-FLD-PLATFORM": asText(first && "platform_key" in first ? first.platform_key : first?.label) ?? DASH,
      "SOC-01-FLD-ACCOUNT": asText(first?.label) ?? DASH,
      "SOC-01-FLD-ACCOUNT-STATUS": asText(first?.status) ?? DASH,
      "SOC-01-FLD-TARGET-COUNT": String(targets.length),
    },
    gate_state: {
      "SOC-01-GATE-PAGE": true,
      "SOC-01-GATE-READ": true,
      "SOC-01-GATE-RECORDS": true,
    },
  };
}

async function readErpFromDb(sql: SqlClient): Promise<unknown> {
  const connectors = await safeRows(() => sql`
    SELECT erp_connector_id::text AS ref, provider_key AS label, adapter_key, connection_status, configuration_version::text AS configuration_version
    FROM erp_connectors
    ORDER BY created_at DESC
  `);
  const jobs = await safeRows(() => sql`
    SELECT erp_sync_job_id::text AS ref, status::text AS label
    FROM erp_sync_jobs
    ORDER BY requested_at DESC
  `);
  const first = connectors[0] ?? null;
  return {
    page_state: first ? "READY" : "EMPTY",
    values: {
      "ERP-01-FLD-PROVIDER": asText(first?.label) ?? DASH,
      "ERP-01-FLD-ADAPTER": asText(first?.adapter_key) ?? DASH,
      "ERP-01-FLD-CONNECTION-STATUS": asText(first?.connection_status) ?? DASH,
      "ERP-01-FLD-CONFIG-VERSION": asText(first?.configuration_version) ?? DASH,
      "ERP-01-FLD-SYNC-STATUS": asText(jobs[0]?.label) ?? DASH,
    },
    gate_state: { "ERP-01-GATE-PAGE": true },
    selected: first ? { connector_id: asText(first.ref) ?? "" } : {},
    form_schemas: {},
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

async function readSg02FromDb(sql: SqlClient): Promise<unknown> {
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
    control_enabled: {},
  };
}

async function readStrategyAdminFromDb(sql: SqlClient): Promise<unknown> {
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
    action_enabled: {},
    selected_resource_id: asText(first?.ref) ?? null,
  };
}

async function readKnowledgeFromDb(sql: SqlClient): Promise<unknown> {
  const sources = await safeRows(() => sql`
    SELECT knowledge_source_id::text AS ref, source_key AS label, status::text AS status, source_uri, classification::text AS classification
    FROM knowledge_sources
    ORDER BY created_at DESC
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
  const approved = sources.filter((row) => asText(row.status) === "APPROVED");
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
    },
  };
}

async function readPageValue(pageUid: string, sql: SqlClient, sessionTokenHash: string): Promise<unknown> {
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
      return readSystemFromDb(sql);
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
      return readSg02FromDb(sql);
    case "admin:STR-01":
      return readStrategyAdminFromDb(sql);
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
    const value = await readPageValue(request.page_uid, sql, decision.session_token_hash);
    if (value == null) return null;
    return { ok: true as const, value, correlation_id: request.correlation_id };
  } catch {
    return { ok: false as const, status: 503, reason_code: "UI_PROJECTION_READ_FAILED", correlation_id: request.correlation_id };
  }
}
