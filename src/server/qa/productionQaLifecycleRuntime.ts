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

  const qaGateRef = requireUuid(payload.qa_gate_ref, "QA01_QA_GATE_REF_REQUIRED");
  const rightsGateRef = requireUuid(payload.rights_gate_ref, "QA01_RELEASE_RIGHTS_POLICY_EVIDENCE_REQUIRED");
  const channelRaw = text(payload.channel_policy_ref);
  const channelPolicyRef = channelRaw && channelRaw !== "NOT_REQUIRED" && channelRaw !== "—"
    ? requireUuid(channelRaw, "QA01_RELEASE_CHANNEL_POLICY_REF_INVALID")
    : null;

  const { sql, actor_user_id, session_token_hash } = await requireContext();
  const rows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      WITH eligible AS (
        SELECT
          r.qa_review_run_id,
          r.qa_task_id,
          r.output_version_id,
          s.scorecard_id,
          o.artifact_checksum,
          o.production_contract_id,
          o.goal_id,
          o.blueprint_version_id,
          o.topic_id,
          COALESCE(o.project_id,r.project_id,t.project_id) AS project_id,
          b.release_policy_binding_id,
          b.channel_required,
          rp.rights_profile_id,
          rv.rights_policy_version_id,
          rv.version_no AS rights_version_no,
          rv.policy_scope AS rights_policy_scope,
          rv.policy_document AS rights_policy_document,
          btrim(rv.content_hash::text) AS rights_content_hash,
          cv.channel_policy_version_id,
          cv.version_no AS channel_version_no,
          cv.policy_scope AS channel_policy_scope,
          cv.policy_document AS channel_policy_document,
          btrim(cv.content_hash::text) AS channel_content_hash,
          ca.channel_account_id,
          ca.platform_key,
          ca.external_account_ref
        FROM public.qa_review_runs r
        JOIN public.department_tasks t ON t.task_id=r.qa_task_id
        JOIN public.task_outputs o ON o.output_version_id=r.output_version_id
        JOIN public.scorecards s
          ON s.scorecard_id=${qaGateRef}::uuid
         AND s.output_version_id=r.output_version_id
         AND s.task_id=r.qa_task_id
         AND s.criteria_version_id=r.criteria_version_id
         AND s.gate_status='PASS'
        JOIN public.release_policy_bindings b
          ON b.output_version_id=r.output_version_id
         AND b.project_id=COALESCE(o.project_id,r.project_id,t.project_id)
         AND b.status='APPROVED'
        JOIN public.rights_policy_versions rv
          ON rv.rights_policy_version_id=b.rights_policy_version_id
         AND rv.project_id=b.project_id
         AND rv.status='APPROVED'
         AND rv.gate_state='PASS'
        JOIN public.rights_profiles rp
          ON rp.rights_profile_id=rv.rights_profile_id
         AND rp.project_id=b.project_id
         AND rp.status='APPROVED'
        LEFT JOIN public.channel_policy_versions cv
          ON cv.channel_policy_version_id=b.channel_policy_version_id
         AND cv.project_id=b.project_id
         AND cv.status='APPROVED'
         AND cv.gate_state='PASS'
        LEFT JOIN public.channel_accounts ca
          ON ca.channel_account_id=cv.channel_account_id
         AND ca.status='APPROVED'
        JOIN LATERAL (
          SELECT h0.rights_profile_id
          FROM public.handoffs h0
          WHERE h0.target_task_id=r.qa_task_id
            AND h0.source_output_version_id=r.output_version_id
            AND h0.status IN ('HANDOFF_READY','HANDED_OFF')
          ORDER BY h0.created_at DESC,h0.handoff_id DESC
          LIMIT 1
        ) h ON true
        WHERE r.qa_review_run_id=${qaReviewId}::uuid
          AND r.status='PASS'
          AND r.output_version_id=${outputIds[0]}::uuid
          AND rv.rights_policy_version_id=${rightsGateRef}::uuid
          AND (h.rights_profile_id IS NULL OR h.rights_profile_id=rp.rights_profile_id)
          AND (
            (b.channel_required=false AND b.channel_policy_version_id IS NULL AND ${channelPolicyRef}::text IS NULL)
            OR
            (
              b.channel_required=true
              AND cv.channel_policy_version_id IS NOT NULL
              AND ca.channel_account_id IS NOT NULL
              AND cv.channel_policy_version_id::text=${channelPolicyRef}
            )
          )
          AND NOT EXISTS (
            SELECT 1 FROM public.findings f
            WHERE f.output_version_id=r.output_version_id AND f.closed_at IS NULL
          )
          AND NOT EXISTS (
            SELECT 1 FROM public.manual_review_cases m
            WHERE m.qa_review_run_id=r.qa_review_run_id AND m.decided_at IS NULL
          )
        LIMIT 1
      ),
      inserted AS (
        INSERT INTO public.release_packages(
          qa_review_run_id,
          output_version_id,
          rights_evidence,
          channel_policy_snapshot,
          approval_path,
          status,
          package_hash,
          production_contract_id,
          goal_id,
          blueprint_version_id,
          topic_id,
          project_id,
          release_policy_binding_id,
          rights_policy_version_id,
          channel_policy_version_id
        )
        SELECT
          e.qa_review_run_id,
          e.output_version_id,
          jsonb_build_object(
            'rights_profile_id',e.rights_profile_id,
            'rights_policy_version_id',e.rights_policy_version_id,
            'version_no',e.rights_version_no,
            'gate_state','PASS',
            'content_hash',e.rights_content_hash,
            'policy_scope',e.rights_policy_scope,
            'policy_document',e.rights_policy_document
          ),
          CASE WHEN e.channel_required THEN
            jsonb_build_object(
              'channel_required',true,
              'channel_policy_version_id',e.channel_policy_version_id,
              'channel_account_id',e.channel_account_id,
              'version_no',e.channel_version_no,
              'gate_state','PASS',
              'content_hash',e.channel_content_hash,
              'platform_key',e.platform_key,
              'external_account_ref',e.external_account_ref,
              'policy_scope',e.channel_policy_scope,
              'policy_document',e.channel_policy_document
            )
          ELSE jsonb_build_object('channel_required',false) END,
          jsonb_build_object(
            'qa_review_id',e.qa_review_run_id,
            'qa_gate_ref',e.scorecard_id,
            'release_policy_binding_id',e.release_policy_binding_id,
            'candidate_only',true,
            'publish',false
          ),
          'PENDING_APPROVAL',
          encode(digest(concat_ws('|',
            e.qa_review_run_id::text,
            e.output_version_id::text,
            btrim(e.artifact_checksum::text),
            e.scorecard_id::text,
            e.release_policy_binding_id::text,
            e.rights_policy_version_id::text,
            COALESCE(e.channel_policy_version_id::text,'NOT_REQUIRED'),
            e.rights_content_hash,
            COALESCE(e.channel_content_hash,'NOT_REQUIRED')
          ),'sha256'),'hex')::char(64),
          e.production_contract_id,
          e.goal_id,
          e.blueprint_version_id,
          e.topic_id,
          e.project_id,
          e.release_policy_binding_id,
          e.rights_policy_version_id,
          e.channel_policy_version_id
        FROM eligible e
        ON CONFLICT (qa_review_run_id) DO NOTHING
        RETURNING *
      ),
      audited AS (
        INSERT INTO public.audit_events(
          action,entity_type,entity_id,actor_id,actor_type,workspace_id,reason,correlation_id,payload_hash
        )
        SELECT
          'createReleasePackage',
          'QA-01',
          i.release_package_id,
          ${actor_user_id}::uuid,
          'USER',
          p.workspace_id,
          'Release candidate created from exact QA PASS and canonical policy binding; no approval or publish',
          ${request.correlation_id}::uuid,
          encode(digest(concat_ws('|',
            i.release_package_id::text,
            i.qa_review_run_id::text,
            i.release_policy_binding_id::text,
            i.rights_policy_version_id::text,
            COALESCE(i.channel_policy_version_id::text,'NOT_REQUIRED')
          ),'sha256'),'hex')
        FROM inserted i
        JOIN public.projects p ON p.project_id=i.project_id
        RETURNING audit_event_id,entity_id
      ),
      exact_existing AS (
        SELECT rp.*
        FROM public.release_packages rp
        JOIN eligible e
          ON e.qa_review_run_id=rp.qa_review_run_id
         AND e.output_version_id=rp.output_version_id
         AND e.release_policy_binding_id=rp.release_policy_binding_id
         AND e.rights_policy_version_id=rp.rights_policy_version_id
         AND rp.channel_policy_version_id IS NOT DISTINCT FROM e.channel_policy_version_id
        WHERE NOT EXISTS (SELECT 1 FROM inserted)
      )
      SELECT
        x.release_package_id::text AS release_package_id,
        x.qa_review_run_id::text AS qa_review_id,
        x.output_version_id::text AS target_output_version_id,
        x.release_policy_binding_id::text AS release_policy_binding_id,
        x.rights_policy_version_id::text AS rights_policy_version_id,
        x.channel_policy_version_id::text AS channel_policy_version_id,
        x.status::text AS state,
        false AS idempotent_replay,
        (SELECT audit_event_id::text FROM audited a WHERE a.entity_id=x.release_package_id LIMIT 1) AS audit_event_id
      FROM inserted x
      UNION ALL
      SELECT
        x.release_package_id::text,
        x.qa_review_run_id::text,
        x.output_version_id::text,
        x.release_policy_binding_id::text,
        x.rights_policy_version_id::text,
        x.channel_policy_version_id::text,
        x.status::text,
        true,
        NULL::text
      FROM exact_existing x
      LIMIT 1
    `,
  );

  const row = first(rows);
  if (!row) throw new NamedRuntimeError("QA01_RELEASE_POLICY_BINDING_OR_CONTEXT_CONFLICT");
  return {
    ...row,
    candidate_only: true,
    publish: false,
    release_approved: false,
    external_request_sent: false,
  };
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
