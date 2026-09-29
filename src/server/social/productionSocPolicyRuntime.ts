import { randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { hashSessionToken, IDENTITY_COOKIE_NAME, resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { SocRuntimeRequest } from "@/server/testing/controlledSocTestRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

function record(value: unknown): Row {return value&&typeof value==="object"&&!Array.isArray(value)?value as Row:{}}
function text(value: unknown): string {return typeof value==="string"?value.trim():""}
function uuid(value:string):boolean{return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)}
function integer(value:unknown,required:boolean):number|null{if(value===undefined||value===null||value==="")return required?-1:null;const parsed=Number(value);return Number.isSafeInteger(parsed)&&parsed>=0?parsed:-1}
function positiveVersion(value:unknown):number|null{const parsed=Number(value);return Number.isSafeInteger(parsed)&&parsed>=1?parsed:null}
function jsonObject(value:unknown):Record<string,unknown>|null{if(value===undefined||value===null||value==="")return null;if(typeof value==="string"){try{const parsed:unknown=JSON.parse(value);return parsed&&typeof parsed==="object"&&!Array.isArray(parsed)?parsed as Record<string,unknown>:null}catch{return null}}return value&&typeof value==="object"&&!Array.isArray(value)?value as Record<string,unknown>:null}
function first(rows:unknown):Row|null{return Array.isArray(rows)&&rows[0]&&typeof rows[0]==="object"?rows[0] as Row:null}

async function requireContext():Promise<{sql:SqlClient;actor_user_id:string;session_token_hash:string}>{
  await ensureProductionNeonRuntime();
  const sql=getProductionNeonSql();if(!sql)throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const store=await cookies();const token=store.get(IDENTITY_COOKIE_NAME)?.value?.trim()??"";
  if(!token)throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity=await resolveIdentityFromCookie(token);if(!identity.ok)throw new NamedRuntimeError(identity.reason_code);
  return{sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}

export async function configureProductionSocTargetPolicy(request:SocRuntimeRequest):Promise<unknown>{
  const payload=record(request.payload);
  const targetId=text(request.path_params?.targetId)||text(request.path_params?.id);
  if(!uuid(targetId))throw new NamedRuntimeError("SOC01_TARGET_ID_INVALID");
  const bodyTarget=text(payload.target_id);if(bodyTarget&&bodyTarget!==targetId)throw new NamedRuntimeError("SOC01_EXACT_REF_MISMATCH");
  const expectedVersion=positiveVersion(payload.expected_version);if(!expectedVersion)throw new NamedRuntimeError("SOC01_EXPECTED_VERSION_MISSING");
  const clientKey=text(payload.idempotency_key);if(!clientKey)throw new NamedRuntimeError("SOC01_IDEMPOTENCY_KEY_REQUIRED");
  const minimumInterval=integer(payload.minimum_interval_hours,true),dailyLimit=integer(payload.daily_limit,true),weeklyLimit=integer(payload.weekly_limit,true);
  if(minimumInterval===null||minimumInterval<0||dailyLimit===null||dailyLimit<0||weeklyLimit===null||weeklyLimit<0)throw new NamedRuntimeError("SOC01_REQUIRED_POLICY_FIELD_MISSING");
  const sameCooldown=integer(payload.same_content_cooldown_hours,false),similarCooldown=integer(payload.similar_content_cooldown_hours,false);
  if(sameCooldown===-1||similarCooldown===-1)throw new NamedRuntimeError("SOC01_POLICY_INTEGER_INVALID");
  const allowedWindow=payload.allowed_time_window===undefined||payload.allowed_time_window===null||payload.allowed_time_window===""?null:jsonObject(payload.allowed_time_window);
  if(payload.allowed_time_window!==undefined&&payload.allowed_time_window!==null&&payload.allowed_time_window!==""&&!allowedWindow)throw new NamedRuntimeError("SOC01_ALLOWED_TIME_WINDOW_INVALID");
  const notes=typeof payload.target_rule_notes==="string"?payload.target_rule_notes.trim():null;
  const policyPatch:Record<string,unknown>={minimum_interval_hours:minimumInterval,daily_limit:dailyLimit,weekly_limit:weeklyLimit};
  if(sameCooldown!==null)policyPatch.same_content_cooldown_hours=sameCooldown;
  if(similarCooldown!==null)policyPatch.similar_content_cooldown_hours=similarCooldown;
  if(allowedWindow)policyPatch.allowed_time_window=allowedWindow;
  if(notes)policyPatch.target_rule_notes=notes;

  const{sql,actor_user_id,session_token_hash}=await requireContext();
  const internalKey=`${actor_user_id}:configureSocialTargetPolicy:${clientKey}`;
  const correlationId=uuid(request.correlation_id)?request.correlation_id:randomUUID();
  const results=await sql.transaction([
    sql`SELECT set_config('acpos.session_token_hash', ${session_token_hash}, true)`,
    sql`SET LOCAL ROLE acpos_app_runtime`,
    sql`SELECT pg_advisory_xact_lock(hashtextextended(${internalKey},0))`,
    sql`
      WITH existing AS (
        SELECT response_json FROM acpos_runtime.idempotency
        WHERE idempotency_key=${internalKey} AND operation_id='configureSocialTargetPolicy'
      ),
      candidate AS (
        SELECT social_target_id,join_status,posting_policy,version
        FROM public.social_market_targets WHERE social_target_id=${targetId}::uuid
      ),
      updated AS (
        UPDATE public.social_market_targets t
        SET posting_policy=t.posting_policy || ${JSON.stringify(policyPatch)}::jsonb,
            join_status='READY_TO_POST',
            version=t.version+1
        FROM candidate c
        WHERE t.social_target_id=c.social_target_id
          AND NOT EXISTS (SELECT 1 FROM existing)
          AND c.join_status='JOINED'
          AND c.version=${expectedVersion}
        RETURNING t.social_target_id,t.join_status,t.posting_policy,t.version,c.posting_policy AS before_policy,c.version AS before_version
      ),
      response AS (
        SELECT response_json || '{"idempotency_replayed":true}'::jsonb AS response_json FROM existing
        UNION ALL
        SELECT jsonb_build_object(
          'target_id',social_target_id::text,'state',join_status,'version',version,
          'event','social.target_policy.configured','external_request_sent',false,'publish_triggered',false,'idempotency_replayed',false
        ) FROM updated LIMIT 1
      ),
      stored AS (
        INSERT INTO acpos_runtime.idempotency(idempotency_key,operation_id,response_json)
        SELECT ${internalKey},'configureSocialTargetPolicy',response_json FROM response
        WHERE NOT EXISTS (SELECT 1 FROM existing)
        ON CONFLICT (idempotency_key) DO NOTHING RETURNING idempotency_key
      ),
      audited AS (
        INSERT INTO public.audit_events(action,entity_type,entity_id,actor_id,actor_type,before_version,after_version,reason,correlation_id,payload_hash)
        SELECT 'configureSocialTargetPolicy','admin:SOC-01',social_target_id,${actor_user_id}::uuid,'USER',
          jsonb_build_object('posting_policy',before_policy,'version',before_version,'state','JOINED'),
          jsonb_build_object('posting_policy',posting_policy,'version',version,'state',join_status),
          'SOC target posting policy configured',${correlationId}::uuid,
          encode(digest(${JSON.stringify(policyPatch)}::text,'sha256'),'hex')
        FROM updated RETURNING audit_event_id
      )
      SELECT response_json FROM response LIMIT 1
    `,
  ]);
  const response=first(results[3]);if(response?.response_json)return response.response_json;
  const diagnostic=await sql.transaction([
    sql`SELECT set_config('acpos.session_token_hash', ${session_token_hash}, true)`,
    sql`SET LOCAL ROLE acpos_app_runtime`,
    sql`SELECT social_target_id::text AS target_id,join_status,version FROM public.social_market_targets WHERE social_target_id=${targetId}::uuid LIMIT 1`,
  ]);
  const current=first(diagnostic[2]);
  if(!current)throw new NamedRuntimeError("SOC01_TARGET_NOT_FOUND");
  if(Number(current.version)!==expectedVersion)throw new NamedRuntimeError("SOC01_VERSION_CONFLICT");
  if(text(current.join_status)!=="JOINED")throw new NamedRuntimeError("SOC01_TARGET_NOT_POLICY_ELIGIBLE");
  throw new NamedRuntimeError("SOC01_POLICY_UPDATE_FAILED");
}
