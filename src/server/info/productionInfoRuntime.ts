import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import {
  hashSessionToken,
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { InfoRequest } from "@/server/info/infoCommandRuntime";
import type { CandidateDecisionRequest } from "@/server/shared/candidateDecisionRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

function rec(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function uuid(value: unknown): string {
  const resolved = text(value);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(resolved)) {
    throw new NamedRuntimeError("INFO01_EXACT_CONTEXT_CANDIDATE_REQUIRED");
  }
  return resolved;
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) && rows.length && rows[0] && typeof rows[0] === "object"
    ? rows[0] as Row
    : null;
}

async function context(): Promise<{sql:SqlClient;actor_user_id:string;session_token_hash:string}> {
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

async function searchInfo(request:InfoRequest):Promise<unknown>{
  const payload=rec(request.payload);
  if(text(payload.page_uid)!=="workspace:INFO-01") throw new NamedRuntimeError("INFO01_PAGE_CONTEXT_REQUIRED");
  const needle=text(payload.query).toLowerCase();
  const {sql,session_token_hash}=await context();
  const q=`%${needle}%`;
  const [packs,candidates]=await Promise.all([
    runRlsActorQuery(sql,session_token_hash,sql`
      SELECT
        f.fact_pack_id::text AS ref,
        concat('FACT_PACK · ',f.status::text,' · ',f.completeness::text,'%') AS label
      FROM public.fact_packs f
      WHERE ${q}='%%'
         OR f.fact_pack_id::text ILIKE ${q}
         OR f.scope::text ILIKE ${q}
         OR f.status::text ILIKE ${q}
      ORDER BY f.freshness_at DESC
      LIMIT 50
    `),
    runRlsActorQuery(sql,session_token_hash,sql`
      SELECT
        c.context_candidate_id::text AS ref,
        concat('CONTEXT_CANDIDATE · ',c.decision_status::text) AS label
      FROM public.context_candidates c
      WHERE ${q}='%%'
         OR c.context_candidate_id::text ILIKE ${q}
         OR c.target_scope::text ILIKE ${q}
         OR c.decision_status::text ILIKE ${q}
      ORDER BY c.created_at DESC
      LIMIT 50
    `),
  ]);
  const normalize=(rows:unknown)=>Array.isArray(rows)?rows.flatMap((raw)=>{
    const row=rec(raw),ref=text(row.ref),label=text(row.label);
    return ref&&label?[{ref,label}]:[];
  }):[];
  return{
    operation:"searchProjection",
    results:[...normalize(packs),...normalize(candidates)],
    page_uid:"workspace:INFO-01",
    external_request_sent:false,
  };
}

async function refreshInfo(request:InfoRequest):Promise<unknown>{
  const payload=rec(request.payload);
  if(text(payload.page_uid)!=="workspace:INFO-01") throw new NamedRuntimeError("INFO01_PAGE_CONTEXT_REQUIRED");
  const {sql,session_token_hash}=await context();
  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT
      f.fact_pack_id::text AS fact_pack_ref,
      f.content_hash::text AS projection_version,
      f.freshness_at::text AS last_refresh
    FROM public.fact_packs f
    ORDER BY f.freshness_at DESC
    LIMIT 1
  `);
  const row=first(rows);
  return{
    operation:"refreshProjection",
    projection_version:text(row?.projection_version)||"info:empty",
    last_refresh:text(row?.last_refresh)||null,
    source_ref:text(row?.fact_pack_ref)||null,
    mutation_scope:"PROJECTION_ONLY",
    external_request_sent:false,
  };
}

async function adoptInfo(request:InfoRequest):Promise<unknown>{
  const payload=rec(request.payload);
  if(text(payload.page_uid)!=="workspace:INFO-01") throw new NamedRuntimeError("INFO01_PAGE_CONTEXT_REQUIRED");
  const pathId=uuid(request.path_params.id);
  const bodyId=uuid(payload.context_candidate_id);
  if(pathId!==bodyId) throw new NamedRuntimeError("INFO01_CONTEXT_CANDIDATE_PATH_BODY_MISMATCH");
  const reason=text(payload.decision_reason);
  if(!reason) throw new NamedRuntimeError("INFO01_DECISION_REASON_REQUIRED");
  const {sql,actor_user_id,session_token_hash}=await context();

  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    WITH current AS (
      SELECT c.context_candidate_id,c.fact_pack_id,c.decision_status,f.workspace_id
      FROM public.context_candidates c
      JOIN public.fact_packs f ON f.fact_pack_id=c.fact_pack_id
      WHERE c.context_candidate_id=${pathId}::uuid
        AND c.decision_status='CANDIDATE'
        AND f.classification <= 'INTERNAL'::classification_level
      LIMIT 1
    ),
    updated AS (
      UPDATE public.context_candidates c
      SET decision_status='APPROVED',
          decided_by=${actor_user_id}::uuid,
          decision_reason=${reason}
      FROM current x
      WHERE c.context_candidate_id=x.context_candidate_id
        AND c.decision_status='CANDIDATE'
      RETURNING c.context_candidate_id,c.fact_pack_id,c.decision_status,c.decided_by,c.decision_reason
    ),
    audited AS (
      INSERT INTO public.audit_events(
        action,entity_type,entity_id,actor_id,actor_type,workspace_id,
        before_version,after_version,reason,correlation_id,payload_hash
      )
      SELECT
        'context.adoption_requested',
        'workspace:INFO-01',
        u.context_candidate_id,
        ${actor_user_id}::uuid,
        'USER',
        x.workspace_id,
        jsonb_build_object('decision_status','CANDIDATE'),
        jsonb_build_object('decision_status',u.decision_status::text,'direct_owner_mutation',false),
        ${reason},
        ${request.correlation_id}::uuid,
        encode(digest(jsonb_build_object(
          'context_candidate_id',u.context_candidate_id::text,
          'decision_status',u.decision_status::text,
          'reason',${reason}
        )::text,'sha256'),'hex')
      FROM updated u
      JOIN current x ON x.context_candidate_id=u.context_candidate_id
      RETURNING audit_event_id
    )
    SELECT
      u.context_candidate_id::text AS context_candidate_id,
      u.decision_status::text AS database_state,
      'ADOPTED'::text AS state,
      (SELECT audit_event_id::text FROM audited LIMIT 1) AS audit_ref,
      false AS direct_owner_mutation
    FROM updated u
    LIMIT 1
  `);
  const row=first(rows);
  if(row)return row;

  const replay=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT
      c.context_candidate_id::text AS context_candidate_id,
      c.decision_status::text AS database_state,
      'ADOPTED'::text AS state,
      true AS idempotent_replay,
      false AS direct_owner_mutation
    FROM public.context_candidates c
    WHERE c.context_candidate_id=${pathId}::uuid
      AND c.decision_status='APPROVED'
      AND c.decided_by=${actor_user_id}::uuid
      AND c.decision_reason=${reason}
    LIMIT 1
  `);
  const replayRow=first(replay);
  if(replayRow)return replayRow;
  throw new NamedRuntimeError("INFO01_CONTEXT_ADOPTION_GATE_REJECTED");
}

export async function executeProductionInfoCommand(request:InfoRequest):Promise<unknown>{
  switch(request.operation_id){
    case"refreshProjection":return refreshInfo(request);
    case"searchProjection":return searchInfo(request);
    case"adoptContextCandidate":return adoptInfo(request);
    case"exportProjection":throw new NamedRuntimeError("INFO01_EXPORT_OWNER_NOT_MATERIALIZED");
    default:throw new NamedRuntimeError("INFO01_OPERATION_NOT_REGISTERED");
  }
}

export async function decideProductionInfoCandidate(request:CandidateDecisionRequest):Promise<unknown>{
  const payload=rec(request.payload);
  if(text(payload.page_uid)!=="workspace:INFO-01") throw new NamedRuntimeError("INFO01_CANDIDATE_OWNER_CONTEXT_REQUIRED");
  const pathId=uuid(request.candidate_id);
  const bodyId=uuid(payload.candidate_id);
  if(pathId!==bodyId) throw new NamedRuntimeError("INFO01_CANDIDATE_PATH_BODY_MISMATCH");
  const decision=text(payload.decision);
  if(decision!=="ACCEPTED"&&decision!=="REJECTED") throw new NamedRuntimeError("INFO01_REGISTERED_DECISION_REQUIRED");
  const reason=text(payload.decision_reason)||null;
  const {sql,actor_user_id,session_token_hash}=await context();

  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    WITH current AS (
      SELECT c.context_candidate_id,c.fact_pack_id,c.decision_status,f.workspace_id
      FROM public.context_candidates c
      JOIN public.fact_packs f ON f.fact_pack_id=c.fact_pack_id
      WHERE c.context_candidate_id=${pathId}::uuid
        AND c.decision_status='CANDIDATE'
        AND f.classification <= 'INTERNAL'::classification_level
      LIMIT 1
    ),
    updated AS (
      UPDATE public.context_candidates c
      SET decision_status=${decision}::decision_status,
          decided_by=${actor_user_id}::uuid,
          decision_reason=${reason}
      FROM current x
      WHERE c.context_candidate_id=x.context_candidate_id
        AND c.decision_status='CANDIDATE'
      RETURNING c.context_candidate_id,c.decision_status,c.decided_by,c.decision_reason
    ),
    audited AS (
      INSERT INTO public.audit_events(
        action,entity_type,entity_id,actor_id,actor_type,workspace_id,
        before_version,after_version,reason,correlation_id,payload_hash
      )
      SELECT
        'candidate.decided',
        'workspace:INFO-01',
        u.context_candidate_id,
        ${actor_user_id}::uuid,
        'USER',
        x.workspace_id,
        jsonb_build_object('decision_status','CANDIDATE'),
        jsonb_build_object('decision_status',u.decision_status::text,'direct_owner_mutation',false),
        ${reason},
        ${request.correlation_id}::uuid,
        encode(digest(jsonb_build_object(
          'candidate_id',u.context_candidate_id::text,
          'decision_status',u.decision_status::text
        )::text,'sha256'),'hex')
      FROM updated u
      JOIN current x ON x.context_candidate_id=u.context_candidate_id
      RETURNING audit_event_id
    )
    SELECT
      u.context_candidate_id::text AS candidate_id,
      u.decision_status::text AS decision,
      (SELECT audit_event_id::text FROM audited LIMIT 1) AS audit_ref,
      false AS direct_owner_mutation
    FROM updated u
    LIMIT 1
  `);
  const row=first(rows);
  if(row)return row;

  const replay=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT
      c.context_candidate_id::text AS candidate_id,
      c.decision_status::text AS decision,
      true AS idempotent_replay,
      false AS direct_owner_mutation
    FROM public.context_candidates c
    WHERE c.context_candidate_id=${pathId}::uuid
      AND c.decision_status=${decision}::decision_status
      AND c.decided_by=${actor_user_id}::uuid
      AND c.decision_reason IS NOT DISTINCT FROM ${reason}
    LIMIT 1
  `);
  const replayRow=first(replay);
  if(replayRow)return replayRow;
  throw new NamedRuntimeError("INFO01_CANDIDATE_DECISION_GATE_REJECTED");
}
