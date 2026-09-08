import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import {
  hashSessionToken,
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { StrategyDecisionRequest } from "@/server/strategy/strategyDecisionRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

function rec(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) && rows.length && rows[0] && typeof rows[0] === "object"
    ? rows[0] as Row
    : null;
}
function requireUuid(value: unknown, reason: string): string {
  const resolved = text(value);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(resolved)) {
    throw new NamedRuntimeError(reason);
  }
  return resolved;
}
function requireFingerprint(value: unknown): string {
  const resolved = text(value);
  if (!/^[0-9a-f]{64}$/i.test(resolved)) throw new NamedRuntimeError("STR01_EXACT_CANDIDATE_VERSION_REQUIRED");
  return resolved.toLowerCase();
}

async function context(): Promise<{sql:SqlClient; actor_user_id:string; session_token_hash:string}> {
  await ensureProductionNeonRuntime();
  const sql=getProductionNeonSql();
  if(!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const store=await cookies();
  const token=store.get(IDENTITY_COOKIE_NAME)?.value?.trim() ?? "";
  if(!token) throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity=await resolveIdentityFromCookie(token);
  if(!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  return {sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}

async function submitReview(request:StrategyDecisionRequest):Promise<unknown>{
  const payload=rec(request.payload);
  if(text(payload.page_uid)!=="workspace:STR-01") throw new NamedRuntimeError("STR01_PAGE_CONTEXT_REQUIRED");
  const candidateRef=requireUuid(payload.candidate_ref,"STR01_EXACT_CANDIDATE_REF_REQUIRED");
  const versionRef=requireFingerprint(payload.candidate_version_ref);
  const {sql,actor_user_id,session_token_hash}=await context();

  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    WITH candidate AS (
      SELECT
        s.strategy_candidate_id,
        s.workspace_id,
        s.source_fact_pack_ids,
        s.strategy_document,
        s.citations,
        s.freshness_at,
        s.confidence,
        encode(digest(concat_ws('|',
          s.source_fact_pack_ids::text,
          s.strategy_document::text,
          s.citations::text,
          s.freshness_at::text,
          s.confidence::text
        ),'sha256'),'hex') AS version_ref
      FROM public.strategy_candidates s
      WHERE s.strategy_candidate_id=${candidateRef}::uuid
        AND s.decision_status='CANDIDATE'
        AND jsonb_typeof(s.source_fact_pack_ids)='array'
        AND jsonb_array_length(s.source_fact_pack_ids)>0
        AND jsonb_typeof(s.strategy_document)='object'
        AND s.strategy_document<>'{}'::jsonb
        AND (
          NULLIF(s.strategy_document->>'analysis_basis','') IS NOT NULL
          OR NULLIF(s.strategy_document->>'basis','') IS NOT NULL
          OR NULLIF(s.strategy_document->>'analysis','') IS NOT NULL
        )
        AND (s.strategy_document ? 'risk' OR s.strategy_document ? 'risks')
        AND s.strategy_document ? 'uncertainty'
        AND s.citations<>'[]'::jsonb
        AND s.citations<>'{}'::jsonb
      LIMIT 1
    ),
    required_resource AS (
      SELECT r.resource_id
      FROM public.permission_resources r
      WHERE r.resource_key='api:adoptAsContextCandidate'
        AND r.resource_type='API'
        AND r.active=true
      LIMIT 1
    ),
    request_row AS (
      INSERT INTO public.decision_requests(
        workspace_id,
        required_resource_id,
        required_action,
        required_scope,
        condition_snapshot,
        reason,
        evidence_refs,
        impact_scope,
        state,
        correlation_id,
        created_by_actor_type,
        created_by_user_id,
        created_by_service_identity_id
      )
      SELECT
        c.workspace_id,
        rr.resource_id,
        'EXECUTE',
        jsonb_build_object(
          'page_uid','workspace:STR-01',
          'candidate_ref',c.strategy_candidate_id::text,
          'workspace_id',c.workspace_id::text
        ),
        jsonb_build_object(
          'candidate_version_ref',c.version_ref,
          'expected_candidate_state','CANDIDATE',
          'owner_execution_performed',false
        ),
        'STRATEGY_CANDIDATE_HUMAN_REVIEW_REQUIRED',
        c.citations,
        jsonb_build_object(
          'candidate_ref',c.strategy_candidate_id::text,
          'downstream_owner_execution','SEPARATE'
        ),
        'OPEN',
        ${request.correlation_id}::uuid,
        'USER',
        ${actor_user_id}::uuid,
        NULL
      FROM candidate c
      CROSS JOIN required_resource rr
      WHERE c.version_ref=${versionRef}
      RETURNING decision_request_id,workspace_id
    ),
    updated AS (
      UPDATE public.strategy_candidates s
      SET decision_status='DECISION_PENDING'
      FROM candidate c,request_row dr
      WHERE s.strategy_candidate_id=c.strategy_candidate_id
        AND s.strategy_candidate_id=${candidateRef}::uuid
        AND s.decision_status='CANDIDATE'
        AND c.version_ref=${versionRef}
      RETURNING s.strategy_candidate_id,s.workspace_id
    )
    SELECT
      u.strategy_candidate_id::text AS candidate_ref,
      ${versionRef}::text AS candidate_version_ref,
      dr.decision_request_id::text AS decision_request_ref,
      'REVIEW_REQUIRED'::text AS state,
      true AS human_review_required,
      false AS owner_execution_performed
    FROM updated u
    JOIN request_row dr ON dr.workspace_id=u.workspace_id
    LIMIT 1
  `);

  const row=first(rows);
  if(row)return row;

  const replay=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT
      s.strategy_candidate_id::text AS candidate_ref,
      ${versionRef}::text AS candidate_version_ref,
      d.decision_request_id::text AS decision_request_ref,
      'REVIEW_REQUIRED'::text AS state,
      true AS human_review_required,
      false AS owner_execution_performed,
      true AS idempotent_replay
    FROM public.strategy_candidates s
    JOIN public.decision_requests d
      ON d.workspace_id=s.workspace_id
     AND d.required_scope->>'candidate_ref'=s.strategy_candidate_id::text
     AND d.condition_snapshot->>'candidate_version_ref'=${versionRef}
     AND d.state IN ('OPEN','NOTIFIED','APPROVED')
    WHERE s.strategy_candidate_id=${candidateRef}::uuid
      AND s.decision_status='DECISION_PENDING'
      AND encode(digest(concat_ws('|',
        s.source_fact_pack_ids::text,
        s.strategy_document::text,
        s.citations::text,
        s.freshness_at::text,
        s.confidence::text
      ),'sha256'),'hex')=${versionRef}
    ORDER BY d.created_at DESC
    LIMIT 1
  `);
  const replayRow=first(replay);
  if(replayRow)return replayRow;
  throw new NamedRuntimeError("STR01_REVIEW_GATE_REJECTED");
}

async function adopt(request:StrategyDecisionRequest):Promise<unknown>{
  const payload=rec(request.payload);
  if(text(payload.page_uid)!=="workspace:STR-01") throw new NamedRuntimeError("STR01_PAGE_CONTEXT_REQUIRED");
  const candidateRef=requireUuid(payload.candidate_ref,"STR01_EXACT_CANDIDATE_REF_REQUIRED");
  const versionRef=requireFingerprint(payload.candidate_version_ref);
  const {sql,session_token_hash}=await context();

  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    WITH approved_review AS (
      SELECT
        s.strategy_candidate_id,
        s.workspace_id,
        s.source_fact_pack_ids,
        s.strategy_document,
        s.citations,
        s.freshness_at,
        s.confidence,
        d.decision_request_id,
        d.decided_by_user_id,
        d.decision_reason,
        d.evidence_refs,
        encode(digest(concat_ws('|',
          s.source_fact_pack_ids::text,
          s.strategy_document::text,
          s.citations::text,
          s.freshness_at::text,
          s.confidence::text
        ),'sha256'),'hex') AS version_ref
      FROM public.strategy_candidates s
      JOIN public.decision_requests d
        ON d.workspace_id=s.workspace_id
       AND d.required_scope->>'candidate_ref'=s.strategy_candidate_id::text
       AND d.condition_snapshot->>'candidate_version_ref'=${versionRef}
       AND d.state='APPROVED'
       AND d.required_action='EXECUTE'
      JOIN public.permission_resources r
        ON r.resource_id=d.required_resource_id
       AND r.resource_key='api:adoptAsContextCandidate'
       AND r.active=true
      WHERE s.strategy_candidate_id=${candidateRef}::uuid
        AND s.decision_status='DECISION_PENDING'
        AND d.decided_by_user_id IS NOT NULL
        AND NULLIF(d.decision_reason,'') IS NOT NULL
        AND d.evidence_refs<>'[]'::jsonb
        AND d.evidence_refs<>'{}'::jsonb
      ORDER BY d.decided_at DESC NULLS LAST,d.created_at DESC
      LIMIT 1
    ),
    updated AS (
      UPDATE public.strategy_candidates s
      SET decision_status='APPROVED'
      FROM approved_review a
      WHERE s.strategy_candidate_id=a.strategy_candidate_id
        AND a.version_ref=${versionRef}
        AND s.decision_status='DECISION_PENDING'
      RETURNING s.strategy_candidate_id
    ),
    ledger AS (
      INSERT INTO public.strategy_decisions(
        strategy_candidate_id,
        decision,
        decider_id,
        rationale,
        context_candidate_id
      )
      SELECT
        a.strategy_candidate_id,
        'ADOPT_CONTEXT',
        a.decided_by_user_id,
        a.decision_reason,
        NULL
      FROM approved_review a
      JOIN updated u ON u.strategy_candidate_id=a.strategy_candidate_id
      WHERE NOT EXISTS (
        SELECT 1
        FROM public.strategy_decisions d
        WHERE d.strategy_candidate_id=a.strategy_candidate_id
          AND d.decision='ADOPT_CONTEXT'
      )
      RETURNING strategy_decision_id,strategy_candidate_id,decider_id,rationale
    )
    SELECT
      l.strategy_decision_id::text AS decision_id,
      l.strategy_candidate_id::text AS candidate_ref,
      ${versionRef}::text AS candidate_version_ref,
      l.decider_id::text AS decider_id,
      l.rationale AS decision_reason,
      'ADOPTED_CONTEXT'::text AS state,
      false AS owner_execution_performed
    FROM ledger l
    LIMIT 1
  `);

  const row=first(rows);
  if(row)return row;

  const replay=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT
      d.strategy_decision_id::text AS decision_id,
      s.strategy_candidate_id::text AS candidate_ref,
      ${versionRef}::text AS candidate_version_ref,
      d.decider_id::text AS decider_id,
      d.rationale AS decision_reason,
      'ADOPTED_CONTEXT'::text AS state,
      false AS owner_execution_performed,
      true AS idempotent_replay
    FROM public.strategy_candidates s
    JOIN public.strategy_decisions d
      ON d.strategy_candidate_id=s.strategy_candidate_id
     AND d.decision='ADOPT_CONTEXT'
    WHERE s.strategy_candidate_id=${candidateRef}::uuid
      AND s.decision_status='APPROVED'
      AND encode(digest(concat_ws('|',
        s.source_fact_pack_ids::text,
        s.strategy_document::text,
        s.citations::text,
        s.freshness_at::text,
        s.confidence::text
      ),'sha256'),'hex')=${versionRef}
    ORDER BY d.created_at DESC
    LIMIT 1
  `);
  const replayRow=first(replay);
  if(replayRow)return replayRow;
  throw new NamedRuntimeError("STR01_ADOPT_REQUIRES_APPROVED_HUMAN_REVIEW");
}

export async function executeProductionStrategyDecision(request:StrategyDecisionRequest):Promise<unknown>{
  switch(request.operation_id){
    case "submitStrategyReview":return submitReview(request);
    case "adoptAsContextCandidate":return adopt(request);
    default:throw new NamedRuntimeError("STR01_DECISION_OPERATION_NOT_REGISTERED");
  }
}
