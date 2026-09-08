import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import {
  hashSessionToken,
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { QaRequest } from "@/server/qa/qaRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

function record(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) && rows.length > 0 && rows[0] && typeof rows[0] === "object"
    ? rows[0] as Row
    : null;
}
function uuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}
function requireUuid(value: unknown, reason: string): string {
  const resolved = text(value);
  if (!uuid(resolved)) throw new NamedRuntimeError(reason);
  return resolved;
}

async function requireContext(): Promise<{
  sql: SqlClient;
  actor_user_id: string;
  session_token_hash: string;
}> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const store = await cookies();
  const token = store.get(IDENTITY_COOKIE_NAME)?.value?.trim() ?? "";
  if (!token) throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity = await resolveIdentityFromCookie(token);
  if (!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  return {
    sql,
    actor_user_id: identity.actor.user_id,
    session_token_hash: hashSessionToken(token),
  };
}

async function startReview(request: QaRequest): Promise<unknown> {
  const payload = record(request.payload);
  const qaTaskId = requireUuid(payload.qa_task_ref, "QA01_QA_TASK_REQUIRED");
  const explicitOutput = text(payload.output_version_id);
  const targetOutput = text(payload.target_output_version_id);
  if (explicitOutput && targetOutput && explicitOutput !== targetOutput) {
    throw new NamedRuntimeError("QA01_EXACT_OUTPUT_MISMATCH");
  }
  const outputVersionId = requireUuid(explicitOutput || targetOutput, "QA01_EXACT_OUTPUT_REQUIRED");
  const criteriaVersionId = requireUuid(payload.qa_profile_id, "QA01_APPROVED_CRITERIA_REQUIRED");
  const projectId = text(payload.project_id);
  const topicId = text(payload.topic_id);

  const { sql, actor_user_id, session_token_hash } = await requireContext();
  const rows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      WITH canonical AS (
        SELECT
          t.task_id AS qa_task_id,
          h.source_output_version_id AS output_version_id,
          q.criteria_version_id,
          COALESCE(t.production_contract_id,h.production_contract_id) AS production_contract_id,
          COALESCE(t.goal_id,t.production_goal_id,h.goal_id,h.production_goal_id) AS goal_id,
          h.blueprint_version_id,
          COALESCE(t.topic_id,h.topic_id) AS topic_id,
          COALESCE(t.project_id,h.project_id,acpos_runtime.project_id_for_output(h.source_output_version_id)) AS project_id
        FROM public.department_tasks t
        JOIN public.handoffs h
          ON h.target_task_id=t.task_id
         AND h.source_output_version_id=${outputVersionId}::uuid
         AND h.status IN ('HANDOFF_READY','HANDED_OFF')
        JOIN public.quality_criteria_versions q
          ON q.criteria_version_id=${criteriaVersionId}::uuid
         AND q.status='APPROVED'
         AND (q.department::text='QA' OR q.department IS NULL)
        WHERE t.task_id=${qaTaskId}::uuid
          AND t.department::text='QA'
        ORDER BY h.created_at DESC,h.handoff_id DESC
        LIMIT 1
      ),
      inserted AS (
        INSERT INTO public.qa_review_runs(
          qa_task_id,
          output_version_id,
          criteria_version_id,
          status,
          reviewer_id,
          production_contract_id,
          goal_id,
          blueprint_version_id,
          topic_id,
          project_id
        )
        SELECT
          c.qa_task_id,
          c.output_version_id,
          c.criteria_version_id,
          'IN_REVIEW',
          ${actor_user_id}::uuid,
          c.production_contract_id,
          c.goal_id,
          c.blueprint_version_id,
          c.topic_id,
          c.project_id
        FROM canonical c
        WHERE (${projectId || null}::text IS NULL OR c.project_id::text=${projectId || null})
          AND (${topicId || null}::text IS NULL OR c.topic_id::text=${topicId || null})
        ON CONFLICT (qa_task_id,output_version_id) DO NOTHING
        RETURNING qa_review_run_id,qa_task_id,output_version_id,criteria_version_id,status,project_id,topic_id
      )
      SELECT
        i.qa_review_run_id::text AS qa_review_id,
        i.qa_task_id::text AS qa_task_ref,
        i.output_version_id::text AS target_output_version_id,
        i.criteria_version_id::text AS criteria_version_id,
        i.status::text AS state,
        i.project_id::text AS project_id,
        i.topic_id::text AS topic_id,
        false AS idempotent_replay
      FROM inserted i
      UNION ALL
      SELECT
        r.qa_review_run_id::text,
        r.qa_task_id::text,
        r.output_version_id::text,
        r.criteria_version_id::text,
        r.status::text,
        r.project_id::text,
        r.topic_id::text,
        true
      FROM public.qa_review_runs r
      WHERE r.qa_task_id=${qaTaskId}::uuid
        AND r.output_version_id=${outputVersionId}::uuid
        AND NOT EXISTS (SELECT 1 FROM inserted)
      LIMIT 1
    `,
  );

  const row = first(rows);
  if (!row) throw new NamedRuntimeError("QA01_CANONICAL_REVIEW_CONTEXT_NOT_READY");
  if (text(row.criteria_version_id) !== criteriaVersionId) {
    throw new NamedRuntimeError("QA01_REVIEW_CRITERIA_CONFLICT");
  }
  return {
    qa_review_id: text(row.qa_review_id),
    qa_task_ref: text(row.qa_task_ref),
    target_output_version_id: text(row.target_output_version_id),
    criteria_version_id: text(row.criteria_version_id),
    state: text(row.state),
    project_id: text(row.project_id),
    topic_id: text(row.topic_id),
    idempotent_replay: row.idempotent_replay === true,
    provider_execution: false,
  };
}

async function startRecheck(request: QaRequest): Promise<unknown> {
  const payload = record(request.payload);
  const qaReviewId = requireUuid(payload.qa_review_id, "QA01_REVIEW_REQUIRED");
  const failedOutputId = requireUuid(payload.failed_output_version_id, "QA01_FAILED_OUTPUT_REQUIRED");
  const newOutputId = requireUuid(payload.verified_new_output_version_id, "QA01_VERIFIED_NEW_OUTPUT_REQUIRED");
  if (failedOutputId === newOutputId) throw new NamedRuntimeError("QA01_RECHECK_SAME_OUTPUT_FORBIDDEN");

  const { sql, session_token_hash } = await requireContext();

  const duplicateRows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      SELECT existing.qa_review_run_id::text AS conflicting_review_id
      FROM public.qa_review_runs current
      JOIN public.qa_review_runs existing
        ON existing.qa_task_id=current.qa_task_id
       AND existing.output_version_id=${newOutputId}::uuid
       AND existing.qa_review_run_id<>current.qa_review_run_id
      WHERE current.qa_review_run_id=${qaReviewId}::uuid
      LIMIT 1
    `,
  );
  if (first(duplicateRows)) throw new NamedRuntimeError("QA01_RECHECK_REVIEW_ALREADY_EXISTS");

  const rows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      WITH eligible AS (
        SELECT
          r.qa_review_run_id,
          r.qa_task_id,
          r.output_version_id AS failed_output_version_id,
          cr.correction_request_id,
          h.source_output_version_id AS verified_new_output_version_id
        FROM public.qa_review_runs r
        JOIN public.correction_requests cr
          ON cr.source_output_version_id=r.output_version_id
         AND cr.status='CORRECTION_REQUIRED'
        JOIN public.handoffs h
          ON h.target_task_id=r.qa_task_id
         AND h.source_task_id=cr.original_owner_task_id
         AND h.source_output_version_id=${newOutputId}::uuid
         AND h.status IN ('HANDOFF_READY','HANDED_OFF')
         AND h.created_at>=cr.created_at
        WHERE r.qa_review_run_id=${qaReviewId}::uuid
          AND r.output_version_id=${failedOutputId}::uuid
          AND r.status IN ('FAIL','CORRECTION_REQUIRED')
        ORDER BY cr.created_at DESC,h.created_at DESC
        LIMIT 1
      )
      UPDATE public.qa_review_runs r
      SET output_version_id=e.verified_new_output_version_id,
          status='RECHECK',
          decision_reason='recheck:' || e.correction_request_id::text,
          decided_at=NULL
      FROM eligible e
      WHERE r.qa_review_run_id=e.qa_review_run_id
      RETURNING
        r.qa_review_run_id::text AS qa_review_id,
        r.qa_task_id::text AS qa_task_ref,
        e.failed_output_version_id::text AS failed_output_version_id,
        r.output_version_id::text AS target_output_version_id,
        e.correction_request_id::text AS correction_request_ref,
        r.status::text AS state
    `,
  );
  const row = first(rows);
  if (!row) throw new NamedRuntimeError("QA01_VERIFIED_NEW_EXACT_OUTPUT_REQUIRED");
  return {
    ...row,
    provider_execution: false,
  };
}

async function decide(request: QaRequest, decision: "PASS" | "FAIL"): Promise<unknown> {
  const payload = record(request.payload);
  const qaReviewId = requireUuid(payload.qa_review_id, "QA01_REVIEW_REQUIRED");
  const requestedScorecardId = text(payload.scorecard_ref);
  if (requestedScorecardId && !uuid(requestedScorecardId)) {
    throw new NamedRuntimeError("QA01_SCORECARD_REF_INVALID");
  }

  const { sql, session_token_hash } = await requireContext();
  const rows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      WITH score AS (
        SELECT DISTINCT ON (s.output_version_id,s.task_id)
          s.scorecard_id,
          s.output_version_id,
          s.task_id,
          s.criteria_version_id,
          s.gate_status
        FROM public.scorecards s
        JOIN public.qa_review_runs r
          ON r.output_version_id=s.output_version_id
         AND r.qa_task_id=s.task_id
         AND r.criteria_version_id=s.criteria_version_id
        WHERE r.qa_review_run_id=${qaReviewId}::uuid
          AND r.status IN ('IN_REVIEW','RECHECK')
          AND s.gate_status=${decision}
          AND (${requestedScorecardId || null}::text IS NULL OR s.scorecard_id::text=${requestedScorecardId || null})
        ORDER BY s.output_version_id,s.task_id,s.created_at DESC
      ),
      guard AS (
        SELECT
          r.qa_review_run_id,
          r.output_version_id,
          s.scorecard_id
        FROM public.qa_review_runs r
        JOIN score s ON s.output_version_id=r.output_version_id AND s.task_id=r.qa_task_id
        WHERE r.qa_review_run_id=${qaReviewId}::uuid
          AND (
            ${decision}='FAIL'
            OR (
              NOT EXISTS (
                SELECT 1 FROM public.findings f
                WHERE f.output_version_id=r.output_version_id
                  AND f.closed_at IS NULL
              )
              AND NOT EXISTS (
                SELECT 1 FROM public.manual_review_cases m
                WHERE m.qa_review_run_id=r.qa_review_run_id
                  AND m.decided_at IS NULL
                  AND m.status='IN_REVIEW'
              )
            )
          )
      )
      UPDATE public.qa_review_runs r
      SET status=${decision},
          decision_reason=${decision.toLowerCase()} || ':scorecard:' || g.scorecard_id::text,
          decided_at=now()
      FROM guard g
      WHERE r.qa_review_run_id=g.qa_review_run_id
      RETURNING
        r.qa_review_run_id::text AS qa_review_id,
        r.output_version_id::text AS target_output_version_id,
        g.scorecard_id::text AS scorecard_ref,
        r.status::text AS decision,
        r.decided_at::text AS decided_at
    `,
  );
  const row = first(rows);
  if (!row) {
    if (decision === "PASS") throw new NamedRuntimeError("QA01_PASS_GATE_NOT_SATISFIED");
    throw new NamedRuntimeError("QA01_FAIL_GATE_NOT_SATISFIED");
  }
  return {
    ...row,
    system_scorecard_required: true,
    provider_execution: false,
  };
}

async function releasePreflight(request: QaRequest): Promise<unknown> {
  const payload = record(request.payload);
  const qaReviewId = requireUuid(payload.qa_review_id, "QA01_REVIEW_REQUIRED");
  if (payload.candidate_only !== true || payload.publish !== false) {
    throw new NamedRuntimeError("QA01_RELEASE_CANDIDATE_ONLY_REQUIRED");
  }

  const outputIds = Array.isArray(payload.output_version_ids)
    ? payload.output_version_ids.filter((value): value is string => typeof value === "string" && uuid(value))
    : [];
  if (outputIds.length !== 1) throw new NamedRuntimeError("QA01_RELEASE_EXACT_OUTPUT_REQUIRED");

  const qaGateRef = text(payload.qa_gate_ref);
  const rightsGateRef = text(payload.rights_gate_ref);
  const channelPolicyRef = text(payload.channel_policy_ref);
  if (!qaGateRef) throw new NamedRuntimeError("QA01_QA_GATE_REF_REQUIRED");
  if (!rightsGateRef || !channelPolicyRef) {
    throw new NamedRuntimeError("QA01_RELEASE_RIGHTS_POLICY_EVIDENCE_REQUIRED");
  }

  const { sql, session_token_hash } = await requireContext();
  const rows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      SELECT
        r.qa_review_run_id::text AS qa_review_id,
        r.output_version_id::text AS target_output_version_id,
        s.scorecard_id::text AS scorecard_ref,
        h.rights_profile_id::text AS rights_profile_ref
      FROM public.qa_review_runs r
      JOIN LATERAL (
        SELECT s0.scorecard_id
        FROM public.scorecards s0
        WHERE s0.output_version_id=r.output_version_id
          AND s0.task_id=r.qa_task_id
          AND s0.criteria_version_id=r.criteria_version_id
          AND s0.gate_status='PASS'
        ORDER BY s0.created_at DESC
        LIMIT 1
      ) s ON true
      JOIN public.handoffs h
        ON h.target_task_id=r.qa_task_id
       AND h.source_output_version_id=r.output_version_id
       AND h.status IN ('HANDOFF_READY','HANDED_OFF')
      WHERE r.qa_review_run_id=${qaReviewId}::uuid
        AND r.status='PASS'
        AND r.output_version_id=${outputIds[0]}::uuid
        AND s.scorecard_id::text=${qaGateRef}
        AND NOT EXISTS (
          SELECT 1 FROM public.findings f
          WHERE f.output_version_id=r.output_version_id AND f.closed_at IS NULL
        )
        AND NOT EXISTS (
          SELECT 1 FROM public.manual_review_cases m
          WHERE m.qa_review_run_id=r.qa_review_run_id AND m.decided_at IS NULL
        )
      ORDER BY h.created_at DESC
      LIMIT 1
    `,
  );
  const row = first(rows);
  if (!row) throw new NamedRuntimeError("QA01_RELEASE_GATE_NOT_SATISFIED");
  if (!text(row.rights_profile_ref)) {
    throw new NamedRuntimeError("QA01_RELEASE_RIGHTS_PROFILE_NOT_VERIFIABLE");
  }

  // Current schema has no canonical rights-profile relation and no channel-policy relation
  // that can prove the user-provided refs. Keep ReleaseService fail-closed rather than
  // materializing unverifiable evidence into release_packages.
  throw new NamedRuntimeError("QA01_RELEASE_EVIDENCE_OWNER_NOT_MATERIALIZED");
}

export async function executeProductionQaLifecycle(request: QaRequest): Promise<unknown> {
  switch (request.operation_id) {
    case "startQaReview":
      return startReview(request);
    case "startRecheck":
      return startRecheck(request);
    case "decidePass":
      return decide(request, "PASS");
    case "decideFail":
      return decide(request, "FAIL");
    case "createReleasePackage":
      return releasePreflight(request);
    default:
      throw new NamedRuntimeError("QA01_LIFECYCLE_OPERATION_NOT_REGISTERED");
  }
}
