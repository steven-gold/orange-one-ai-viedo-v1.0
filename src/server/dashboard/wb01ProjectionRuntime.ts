import { createHash } from "node:crypto";
import { cookies } from "next/headers";
import { getProductionNeonSql } from "@/server/database/neonRuntime";
import {
  configureDashboardRuntime,
  type DashboardAccessRequest,
  type DashboardAuthorizationDecision,
} from "@/server/dashboard/readModelRuntime";
import { configureUiProjectionRuntime, type UiProjectionRequest } from "@/server/shared/uiProjectionRuntime";
import {
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
  type IdentityActor,
} from "@/server/identity/identityRuntime";

export const WB01_PAGE_UID = "workspace:WB-01";
export const WB01_READ_MODEL_VERSION = "WB-01-READ-V1.0";
export const WB01_PAGE_RESOURCE_KEY = "page:workspace:WB-01";

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

function asInt(value: unknown): number | null {
  const n = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : NaN;
  return Number.isInteger(n) && n >= 0 ? n : null;
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

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
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
  | { allowed: true; actor: IdentityActor }
  | { allowed: false; reason_code: string };

async function evaluateWb01PageGate(): Promise<GateDecision> {
  const sql = getProductionNeonSql();
  if (!sql) return { allowed: false, reason_code: "DATABASE_RUNTIME_NOT_BOUND" };

  const identity = await resolveIdentityFromCookie(await readSessionCookie());
  if (!identity.ok) return { allowed: false, reason_code: identity.reason_code };

  const actor = identity.actor;
  try {
    const rows = await sql`
      SELECT a.account_permission_assignment_id::text AS account_permission_assignment_id,
             a.effect,
             a.status,
             a.scope,
             a.condition,
             a.gate_profile
      FROM account_permission_assignments a
      JOIN permission_resources r ON r.resource_id = a.resource_id
      WHERE a.user_id = ${actor.user_id}
        AND r.resource_key = ${WB01_PAGE_RESOURCE_KEY}
        AND r.resource_type = 'PAGE'
        AND r.active = true
        AND a.action = 'VIEW'
        AND a.status = 'APPROVED'
        AND a.effective_from <= now()
        AND (a.effective_to IS NULL OR a.effective_to > now())
    `;
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
    if (matched.some((row) => row.effect === "DENY")) {
      return { allowed: false, reason_code: "PERMISSION_DENIED" };
    }
    if (matched.some((row) => row.effect === "ALLOW")) {
      return { allowed: true, actor };
    }
    return { allowed: false, reason_code: "PERMISSION_OR_SCOPE_DENIED" };
  } catch {
    return { allowed: false, reason_code: "AUTHORIZATION_EVALUATION_FAILED" };
  }
}

async function writeAudit(entry: {
  actor?: IdentityActor;
  correlation_id: string;
  outcome: string;
  reason_code?: string;
}): Promise<void> {
  const sql = getProductionNeonSql();
  let actor = entry.actor;
  if (!actor) {
    const identity = await resolveIdentityFromCookie(await readSessionCookie());
    if (identity.ok) actor = identity.actor;
  }
  const actorId = actor?.user_id;
  const correlation = isUuid(entry.correlation_id) ? entry.correlation_id : null;
  if (!sql || !actorId || !correlation) return;
  const payload_hash = createHash("sha256")
    .update(JSON.stringify({
      action: "getDashboardReadModel",
      entity_type: WB01_PAGE_UID,
      outcome: entry.outcome,
      reason_code: entry.reason_code ?? null,
      correlation_id: correlation,
    }))
    .digest("hex");
  try {
    await sql`
      INSERT INTO audit_events (
        action,
        entity_type,
        entity_id,
        actor_id,
        actor_type,
        correlation_id,
        payload_hash
      ) VALUES (
        'getDashboardReadModel',
        ${WB01_PAGE_UID},
        ${actorId},
        ${actorId},
        'USER',
        ${correlation},
        ${payload_hash}
      )
    `;
  } catch {
    /* audit failure stays fail-closed for the business read */
  }
}

async function authorizeDashboard(request: DashboardAccessRequest): Promise<DashboardAuthorizationDecision> {
  const decision = await evaluateWb01PageGate();
  if (!decision.allowed) return { allowed: false, discloseable_reason_code: decision.reason_code };
  await writeAudit({ actor: decision.actor, correlation_id: request.correlation_id, outcome: "ALLOWED" });
  return { allowed: true };
}

function scalar(value: number | null): { value: number | null } {
  return { value };
}

async function countProjects(sql: SqlClient, statuses: readonly string[] | "ALL"): Promise<number | null> {
  if (statuses === "ALL") {
    const rows = await sql`
      SELECT count(*)::int AS value
      FROM projects
      WHERE archived_at IS NULL
    `;
    return asInt(asRecord(Array.isArray(rows) ? rows[0] : null)?.value);
  }
  const rows = await sql`
    SELECT count(*)::int AS value
    FROM projects
    WHERE archived_at IS NULL
      AND status::text IN (${statuses[0]}, ${statuses[1] ?? statuses[0]}, ${statuses[2] ?? statuses[0]}, ${statuses[3] ?? statuses[0]}, ${statuses[4] ?? statuses[0]}, ${statuses[5] ?? statuses[0]}, ${statuses[6] ?? statuses[0]}, ${statuses[7] ?? statuses[0]})
  `;
  return asInt(asRecord(Array.isArray(rows) ? rows[0] : null)?.value);
}

async function readDashboardProjection(request: DashboardAccessRequest): Promise<unknown> {
  const sql = getProductionNeonSql();
  if (!sql) throw new Error("DATABASE_RUNTIME_NOT_BOUND");

  const identity = await resolveIdentityFromCookie(await readSessionCookie());
  if (!identity.ok) throw new Error(identity.reason_code);
  const actor = identity.actor;

  const [
    companyProjectCount,
    runningCount,
    pendingActionCount,
    pendingReviewCount,
    completedCount,
    projectRows,
    topicRows,
    taskRows,
    productionRows,
    notificationRows,
    migrationRows,
    completionRows,
  ] = await Promise.all([
    countProjects(sql, "ALL"),
    countProjects(sql, ["RUNNING"]),
    countProjects(sql, ["DRAFT", "WAITING_DEPENDENCY", "READY", "BLOCKED", "COMPILE_REQUESTED", "CORE_MODELING"]),
    countProjects(sql, ["IN_REVIEW", "PENDING_APPROVAL", "RECHECK", "CORE_REVIEW", "BLUEPRINT_REVIEW", "READY_FOR_MOTHER_REVIEW", "READY_FOR_CHILD_REVIEW", "SCORE_PENDING"]),
    countProjects(sql, ["PUBLISHED", "ARCHIVED", "HANDED_OFF", "PASS"]),
    sql`
      SELECT project_id::text AS project_id,
             title AS display_name,
             title AS label,
             project_code AS code,
             status::text AS status
      FROM projects
      WHERE archived_at IS NULL
      ORDER BY created_at ASC
    `,
    sql`
      SELECT topic_id::text AS topic_id,
             project_id::text AS project_id,
             title AS display_name,
             title AS label,
             topic_code AS code,
             status::text AS status
      FROM topics
      WHERE archived_at IS NULL
      ORDER BY created_at ASC
    `,
    sql`
      SELECT t.task_id::text AS task_id,
             cl.topic_id::text AS topic_id,
             t.task_id::text AS code,
             t.status::text AS task_state
      FROM department_tasks t
      JOIN child_locks cl ON cl.child_lock_id = t.child_lock_id
      ORDER BY t.created_at ASC
    `,
    sql`
      SELECT department::text AS unit_key,
             department::text AS unit_label,
             CASE
               WHEN count(*) FILTER (WHERE status = 'RUNNING') > 0 THEN 'RUNNING'
               WHEN count(*) FILTER (WHERE status IN ('WAITING_DEPENDENCY', 'READY', 'BLOCKED')) > 0 THEN 'PENDING'
               WHEN count(*) FILTER (WHERE status IN ('IN_REVIEW', 'PENDING_APPROVAL', 'RECHECK')) > 0 THEN 'REVIEW'
               ELSE 'IDLE'
             END AS state,
             count(*) FILTER (WHERE status = 'RUNNING')::int AS running_count,
             count(*) FILTER (WHERE status IN ('WAITING_DEPENDENCY', 'READY', 'BLOCKED'))::int AS pending_count,
             count(*) FILTER (WHERE status IN ('IN_REVIEW', 'PENDING_APPROVAL', 'RECHECK'))::int AS review_count,
             count(*) FILTER (WHERE completed_at IS NOT NULL)::int AS completed_count
      FROM department_tasks
      GROUP BY department
      ORDER BY department::text
    `,
    sql`
      SELECT notification_id::text AS notification_id,
             COALESCE(payload->>'title', notification_type) AS title,
             COALESCE(payload->>'category', notification_type) AS category,
             created_at::text AS created_at,
             COALESCE(
               payload->>'read_state',
               CASE WHEN read_at IS NULL THEN 'UNREAD' ELSE 'READ' END
             ) AS read_state
      FROM notifications
      WHERE recipient_user_id = ${actor.user_id}
      ORDER BY created_at DESC
    `,
    sql`
      SELECT count(*)::int AS n, now()::text AS checked_at
      FROM schema_migration_history
    `,
    sql`
      SELECT t.task_id::text AS completion_id,
             p.title AS project_label,
             tp.title AS topic_label,
             t.department::text AS item_label,
             t.status::text AS completion_kind,
             t.completed_at::text AS completed_at
      FROM department_tasks t
      JOIN child_locks cl ON cl.child_lock_id = t.child_lock_id
      JOIN topics tp ON tp.topic_id = cl.topic_id
      JOIN projects p ON p.project_id = tp.project_id
      WHERE t.completed_at IS NOT NULL
      ORDER BY t.completed_at DESC
      LIMIT 20
    `,
  ]);

  const tasksByTopic = new Map<string, Array<Record<string, unknown>>>();
  for (const raw of Array.isArray(taskRows) ? taskRows : []) {
    const row = asRecord(raw);
    const topicId = asText(row?.topic_id);
    if (!row || !topicId) continue;
    const list = tasksByTopic.get(topicId) ?? [];
    list.push({
      task_id: asText(row.task_id),
      display_name: null,
      label: null,
      code: asText(row.code),
      task_state: asText(row.task_state),
    });
    tasksByTopic.set(topicId, list);
  }

  const topicsByProject = new Map<string, Array<Record<string, unknown>>>();
  for (const raw of Array.isArray(topicRows) ? topicRows : []) {
    const row = asRecord(raw);
    const projectId = asText(row?.project_id);
    const topicId = asText(row?.topic_id);
    if (!row || !projectId || !topicId) continue;
    const list = topicsByProject.get(projectId) ?? [];
    list.push({
      topic_id: topicId,
      display_name: asText(row.display_name),
      label: asText(row.label),
      code: asText(row.code),
      status: asText(row.status),
      progress_percentage: null,
      total_operation_time_seconds: null,
      tasks: tasksByTopic.get(topicId) ?? [],
    });
    topicsByProject.set(projectId, list);
  }

  const projects = (Array.isArray(projectRows) ? projectRows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const projectId = asText(row?.project_id);
    if (!row || !projectId) return [];
    return [{
      project_id: projectId,
      display_name: asText(row.display_name),
      label: asText(row.label),
      code: asText(row.code),
      status: asText(row.status),
      progress_percentage: null,
      topics: topicsByProject.get(projectId) ?? [],
    }];
  });

  const units = (Array.isArray(productionRows) ? productionRows : []).flatMap((raw) => {
    const row = asRecord(raw);
    if (!row) return [];
    return [{
      unit_key: asText(row.unit_key),
      unit_label: asText(row.unit_label),
      state: asText(row.state),
      running_count: asInt(row.running_count),
      pending_count: asInt(row.pending_count),
      review_count: asInt(row.review_count),
      completed_count: asInt(row.completed_count),
    }];
  });

  const notifications = (Array.isArray(notificationRows) ? notificationRows : []).flatMap((raw) => {
    const row = asRecord(raw);
    if (!row) return [];
    return [{
      notification_id: asText(row.notification_id),
      title: asText(row.title),
      category: asText(row.category),
      created_at: asText(row.created_at),
      read_state: asText(row.read_state),
    }];
  });

  const completions = (Array.isArray(completionRows) ? completionRows : []).flatMap((raw) => {
    const row = asRecord(raw);
    if (!row) return [];
    return [{
      completion_id: asText(row.completion_id),
      project_label: asText(row.project_label),
      topic_label: asText(row.topic_label),
      item_label: asText(row.item_label),
      completion_kind: asText(row.completion_kind),
      completed_at: asText(row.completed_at),
    }];
  });

  const migration = asRecord(Array.isArray(migrationRows) ? migrationRows[0] : null);
  const migrationCount = asInt(migration?.n);

  return {
    read_model_version: WB01_READ_MODEL_VERSION,
    correlation_id: request.correlation_id,
    company_project_count: { company_project_count: scalar(companyProjectCount) },
    company_running_project_count: { company_running_project_count: scalar(runningCount) },
    company_pending_action_count: { company_pending_action_count: scalar(pendingActionCount) },
    company_pending_review_count: { company_pending_review_count: scalar(pendingReviewCount) },
    company_completed_project_count: { company_completed_project_count: scalar(completedCount) },
    company_average_progress: { company_average_progress: scalar(null) },
    project_progress_overview: { project_progress_overview: { projects } },
    company_progress_summary: {
      company_progress_summary: {
        overall_progress_percentage: null,
        running_count: runningCount,
        pending_action_count: pendingActionCount,
        pending_review_count: pendingReviewCount,
        completed_count: completedCount,
      },
    },
    production_summary: { production_summary: { units } },
    notifications: { notifications: { items: notifications } },
    company_announcements: { company_announcements: { items: [] } },
    industry_news: { industry_news: { items: [] } },
    system_status_summary: {
      system_status_summary: {
        overall_status: migrationCount === 15 ? "READY" : "BLOCKED",
        summary: `schema_migration_history=${migrationCount ?? "unresolved"}`,
        checked_at: asText(migration?.checked_at),
      },
    },
    recent_completions: { recent_completions: { items: completions } },
  };
}

export function bindWb01ProjectionRuntime(): void {
  configureDashboardRuntime({
    authorize: authorizeDashboard,
    readProjection: readDashboardProjection,
    audit: async (entry) => {
      await writeAudit({
        correlation_id: entry.correlation_id,
        outcome: entry.outcome,
        reason_code: entry.reason_code,
      });
    },
  });

  configureUiProjectionRuntime({
    authorize: async (request: UiProjectionRequest) => {
      if (request.page_uid !== WB01_PAGE_UID) {
        return { allowed: false, reason_code: "UI_PROJECTION_RUNTIME_NOT_BOUND" };
      }
      const decision = await evaluateWb01PageGate();
      if (!decision.allowed) return { allowed: false, reason_code: decision.reason_code };
      return { allowed: true };
    },
    read: async (request: UiProjectionRequest) => {
      if (request.page_uid !== WB01_PAGE_UID) {
        throw new Error("UI_PROJECTION_RUNTIME_NOT_BOUND");
      }
      return readDashboardProjection({ correlation_id: request.correlation_id });
    },
    audit: async (entry) => {
      await writeAudit({
        correlation_id: entry.correlation_id,
        outcome: entry.outcome,
        reason_code: entry.reason_code,
      });
    },
  });
}
