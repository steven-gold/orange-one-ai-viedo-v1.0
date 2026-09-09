import { createHash } from "node:crypto";
import { cookies } from "next/headers";
import type { IamRuntimeRequest } from "@/server/iam/iamRuntime";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import {
  hashSessionToken,
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";
import { CURRENT_PAGE_RESOURCE_KEYS } from "@/server/shared/pageCatalogProjectionRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

const FRONT_BUNDLE_PAGE: Readonly<Record<string,string>> = {
  "FRONT-L1-01":"workspace:WB-01",
  "FRONT-L1-02":"CORE-01",
  "FRONT-L1-03":"ASSET-01",
  "FRONT-L1-04":"VIDEO-01",
  "FRONT-L1-05":"EDIT-01",
  "FRONT-L1-06":"QA-01",
  "FRONT-L1-07":"admin:DB-01",
  "FRONT-L1-08":"workspace:STR-01",
  "FRONT-L1-09":"workspace:INFO-01",
};
const ADMIN_BUNDLE_PAGE: Readonly<Record<string,string>> = {
  "ADMIN-L1-SYSTEM":"admin:SYS-01",
  "ADMIN-L1-IAM":"admin:IAM-01",
  "ADMIN-L1-DEV":"admin:DEV-01",
  "ADMIN-L1-SOCIAL":"admin:SOC-01",
  "ADMIN-L1-ERP":"admin:ERP-01",
  "ADMIN-L1-AIAPI":"admin:AIAPI-01",
  "ADMIN-L1-QA-CRITERIA":"admin:SG-02",
  "ADMIN-L1-STRATEGY":"admin:STR-01",
  "ADMIN-L1-KNOWLEDGE":"admin:KB-01",
};
const BUNDLE_PAGE = {...FRONT_BUNDLE_PAGE,...ADMIN_BUNDLE_PAGE};

function rec(value:unknown):Row{
  return value&&typeof value==="object"&&!Array.isArray(value)?value as Row:{};
}
function text(value:unknown):string|null{
  if(typeof value!=="string")return null;
  const normalized=value.trim();
  return normalized||null;
}
function strings(value:unknown):string[]{
  return Array.isArray(value)?value.flatMap((item)=>typeof item==="string"&&item.trim()?[item.trim()]:[]):[];
}
function rows(value:unknown):Row[]{
  return Array.isArray(value)?value.flatMap((item)=>item&&typeof item==="object"&&!Array.isArray(item)?[item as Row]:[]):[];
}
function first(value:unknown):Row|null{return rows(value)[0]??null;}
function sha256(value:string){return createHash("sha256").update(value).digest("hex");}
function stableValue(value:unknown):unknown{
  if(Array.isArray(value))return value.map(stableValue);
  if(value&&typeof value==="object"){
    return Object.fromEntries(Object.entries(value as Row).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,stableValue(item)]));
  }
  return value;
}
function stableJson(value:unknown){return JSON.stringify(stableValue(value));}
function object(value:unknown):Row|null{return value&&typeof value==="object"&&!Array.isArray(value)?value as Row:null;}
function integer(value:unknown):number|null{const parsed=typeof value==="number"?value:Number(value);return Number.isInteger(parsed)?parsed:null;}
const AIAPI_PAGE_UID="admin:AIAPI-01";
const SG02_PAGE_UID="admin:SG-02";
const SG02_CRITERIA_RESOURCE_TYPE="quality_criteria_version";
const SG02_DEPARTMENTS=new Set(["CORE","ASSET","VIDEO","EDITING","QA","RELEASE","STRATEGY","SYSTEM"]);
const AIAPI_CLASSIFICATIONS=new Set(["PUBLIC","INTERNAL","RESTRICTED","RESTRICTED_FINANCE"]);
type AiApiCapabilityConfig={
  provider_key:string;model_key:string;capability_version:string;accepted_classifications:string[];
  input_schema:Row;output_schema:Row;limits:Row;
};
function aiApiCapabilityConfig(payload:Row):AiApiCapabilityConfig|null{
  if(text(payload.page_uid)!==AIAPI_PAGE_UID)return null;
  if(!text(payload.resource_type))throw new NamedRuntimeError("AIAPI_CAPABILITY_RESOURCE_TYPE_REQUIRED");
  const patch=object(payload.config_patch_json);
  if(!patch)throw new NamedRuntimeError("AIAPI_CAPABILITY_CONFIG_PATCH_REQUIRED");
  const provider_key=text(patch.provider_key),model_key=text(patch.model_key),capability_version=text(patch.capability_version);
  const accepted_classifications=strings(patch.accepted_classifications).map((value)=>value.toUpperCase());
  const input_schema=object(patch.input_schema),output_schema=object(patch.output_schema),limits=object(patch.limits);
  if(!provider_key)throw new NamedRuntimeError("AIAPI_CAPABILITY_PROVIDER_KEY_REQUIRED");
  if(!model_key)throw new NamedRuntimeError("AIAPI_CAPABILITY_MODEL_KEY_REQUIRED");
  if(!capability_version)throw new NamedRuntimeError("AIAPI_CAPABILITY_VERSION_REQUIRED");
  if(!accepted_classifications.length||accepted_classifications.some((value)=>!AIAPI_CLASSIFICATIONS.has(value))){
    throw new NamedRuntimeError("AIAPI_CAPABILITY_CLASSIFICATION_INVALID");
  }
  if(!input_schema)throw new NamedRuntimeError("AIAPI_CAPABILITY_INPUT_SCHEMA_REQUIRED");
  if(!output_schema)throw new NamedRuntimeError("AIAPI_CAPABILITY_OUTPUT_SCHEMA_REQUIRED");
  if(!limits)throw new NamedRuntimeError("AIAPI_CAPABILITY_LIMITS_REQUIRED");
  return{provider_key,model_key,capability_version,accepted_classifications,input_schema,output_schema,limits};
}

type QualityCriteriaConfig={
  criteria_key:string;
  version_no:number;
  department:string;
  dimensions:unknown;
  required_checks:unknown;
  gate_policy:Row;
};
function qaCriteriaConfig(payload:Row):QualityCriteriaConfig|null{
  if(text(payload.page_uid)!==SG02_PAGE_UID)return null;
  if(text(payload.resource_type)!==SG02_CRITERIA_RESOURCE_TYPE)return null;
  const patch=object(payload.config_patch_json);
  if(!patch)throw new NamedRuntimeError("SG02_CRITERIA_CONFIG_PATCH_REQUIRED");
  const criteria_key=text(patch.criteria_key);
  const version_no=integer(patch.version_no);
  const department=(text(patch.department)??"").toUpperCase();
  const dimensions=patch.dimensions;
  const required_checks=patch.required_checks;
  const gate_policy=object(patch.gate_policy);
  if(!criteria_key)throw new NamedRuntimeError("SG02_CRITERIA_KEY_REQUIRED");
  if(!version_no||version_no<1)throw new NamedRuntimeError("SG02_CRITERIA_VERSION_REQUIRED");
  if(!SG02_DEPARTMENTS.has(department))throw new NamedRuntimeError("SG02_CRITERIA_DEPARTMENT_INVALID");
  if(dimensions===undefined||dimensions===null||(!Array.isArray(dimensions)&&!object(dimensions)))throw new NamedRuntimeError("SG02_CRITERIA_DIMENSIONS_REQUIRED");
  if(required_checks===undefined||required_checks===null||(!Array.isArray(required_checks)&&!object(required_checks)))throw new NamedRuntimeError("SG02_CRITERIA_REQUIRED_CHECKS_REQUIRED");
  if(!gate_policy)throw new NamedRuntimeError("SG02_CRITERIA_GATE_POLICY_REQUIRED");
  return{criteria_key,version_no,department,dimensions,required_checks,gate_policy};
}
function permissionRef(resourceId:string,action:string){return `${resourceId}|${action}`;}
function parsePermissionRef(value:unknown){
  const ref=text(value);
  if(!ref)return null;
  const split=ref.lastIndexOf("|");
  if(split<=0||split===ref.length-1)return null;
  const resource_id=ref.slice(0,split);
  const action=ref.slice(split+1);
  if(!/^[0-9a-f-]{36}$/i.test(resource_id)||!action)return null;
  return{resource_id,action};
}
async function readSessionCookie():Promise<string|undefined>{
  try{return (await cookies()).get(IDENTITY_COOKIE_NAME)?.value;}catch{return undefined;}
}
async function requireContext(){
  await ensureProductionNeonRuntime();
  const sql=getProductionNeonSql();
  if(!sql)throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const cookie=await readSessionCookie();
  const identity=await resolveIdentityFromCookie(cookie);
  if(!identity.ok)throw new NamedRuntimeError(identity.reason_code);
  if(!cookie)throw new NamedRuntimeError("RLS_SESSION_CONTEXT_REQUIRED");
  return{sql,actor:identity.actor,session_token_hash:hashSessionToken(cookie)};
}
async function loadEntity(sql:SqlClient,kind:string,id:string){
  return first(await sql`
    SELECT kind,id,parent_id,status,version,payload,created_at,updated_at
    FROM acpos_runtime.entities
    WHERE kind=${kind} AND id=${id}
    LIMIT 1
  `);
}
async function upsertEntity(sql:SqlClient,input:{kind:string;id:string;parent_id?:string|null;status:string;payload:Row}){
  const result=await sql`
    INSERT INTO acpos_runtime.entities(kind,id,parent_id,status,version,payload)
    VALUES(${input.kind},${input.id},${input.parent_id??null},${input.status},1,${JSON.stringify(input.payload)}::jsonb)
    ON CONFLICT(kind,id) DO UPDATE
    SET parent_id=EXCLUDED.parent_id,
        status=EXCLUDED.status,
        version=acpos_runtime.entities.version+1,
        payload=EXCLUDED.payload,
        updated_at=now()
    RETURNING kind,id,parent_id,status,version,payload
  `;
  const row=first(result);
  if(!row)throw new NamedRuntimeError("IAM_ENTITY_WRITE_FAILED");
  return row;
}
async function audit(sql:SqlClient,input:{
  operation:string;actorId:string;correlationId:string;entityId:string;payload:unknown;entityType?:string;
}){
  const correlation=/^[0-9a-f-]{36}$/i.test(input.correlationId)?input.correlationId:crypto.randomUUID();
  const entity=/^[0-9a-f-]{36}$/i.test(input.entityId)?input.entityId:crypto.randomUUID();
  await sql`
    INSERT INTO audit_events(action,entity_type,entity_id,actor_id,actor_type,correlation_id,payload_hash)
    VALUES(
      ${input.operation},${input.entityType??"admin:IAM-01"},${entity}::uuid,${input.actorId}::uuid,'USER',
      ${correlation}::uuid,${sha256(stableJson(input.payload))}
    )
  `;
}
async function expandBundles(sql:SqlClient,bundles:string[]){
  const invalid=bundles.filter((bundle)=>!BUNDLE_PAGE[bundle]);
  if(invalid.length)throw new NamedRuntimeError(`IAM-01-ERR-L1-EXPANSION:${invalid.join(",")}`);
  const output=new Map<string,{resource_id:string;resource_key:string;action:string;bundle:string;page_uid:string;risk_tier:string|null}>();
  for(const bundle of bundles){
    const pageUid=BUNDLE_PAGE[bundle];
    const pageResource=CURRENT_PAGE_RESOURCE_KEYS[pageUid];
    if(!pageResource)throw new NamedRuntimeError(`IAM-01-ERR-L1-EXPANSION:${bundle}`);
    const expanded=rows(await sql`
      WITH RECURSIVE resource_tree AS (
        SELECT resource_id,resource_key,parent_resource_key,allowed_actions,risk_tier,active
        FROM permission_resources
        WHERE resource_key=${pageResource} AND active=true
        UNION ALL
        SELECT child.resource_id,child.resource_key,child.parent_resource_key,child.allowed_actions,child.risk_tier,child.active
        FROM permission_resources child
        JOIN resource_tree parent ON child.parent_resource_key=parent.resource_key
        WHERE child.active=true
      )
      SELECT resource_id::text AS resource_id,resource_key,risk_tier,action
      FROM resource_tree
      CROSS JOIN LATERAL jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(allowed_actions)='array' THEN allowed_actions ELSE '[]'::jsonb END
      ) AS action
      ORDER BY resource_key,action
    `);
    if(!expanded.length)throw new NamedRuntimeError(`IAM-01-ERR-L1-EXPANSION:${bundle}`);
    for(const item of expanded){
      const resource_id=text(item.resource_id),resource_key=text(item.resource_key),action=text(item.action);
      if(!resource_id||!resource_key||!action)continue;
      output.set(permissionRef(resource_id,action),{
        resource_id,resource_key,action,bundle,page_uid:pageUid,risk_tier:text(item.risk_tier),
      });
    }
  }
  return output;
}
async function currentAssignments(sql:SqlClient,sessionTokenHash:string,accountId:string){
  const result=await runRlsActorQuery(sql,sessionTokenHash,sql`
    SELECT DISTINCT ON (a.resource_id,a.action)
      a.account_permission_assignment_id::text AS assignment_id,
      a.resource_id::text AS resource_id,
      r.resource_key,
      r.risk_tier,
      a.action,a.effect,a.status::text AS status,a.version_no
    FROM account_permission_assignments a
    JOIN permission_resources r ON r.resource_id=a.resource_id
    WHERE a.user_id=${accountId}::uuid
      AND a.status='APPROVED'
      AND a.effective_from<=now()
      AND (a.effective_to IS NULL OR a.effective_to>now())
    ORDER BY a.resource_id,a.action,a.version_no DESC
  `);
  const map=new Map<string,Row>();
  for(const row of rows(result)){
    const resourceId=text(row.resource_id),action=text(row.action);
    if(!resourceId||!action)continue;
    if(text(row.effect)==="ALLOW")map.set(permissionRef(resourceId,action),row);
    else map.delete(permissionRef(resourceId,action));
  }
  return map;
}
async function requireDraft(sql:SqlClient,draftId:string){
  const draft=await loadEntity(sql,"IAM_ACCOUNT_DRAFT",draftId);
  if(!draft)throw new NamedRuntimeError("IAM_DRAFT_REQUIRED");
  return draft;
}
async function saveDraft(request:IamRuntimeRequest){
  const {sql,actor}=await requireContext();
  const payload=rec(request.payload);
  const draftId=text(request.draft_id)??text(payload.draft_id);
  if(!draftId||!/^[0-9a-f-]{36}$/i.test(draftId))throw new NamedRuntimeError("IAM_DRAFT_ID_INVALID");
  const mode=text(payload.mode);
  if(mode!=="CREATE"&&mode!=="EDIT")throw new NamedRuntimeError("IAM_DRAFT_MODE_REQUIRED");
  const accountId=text(payload.account_id);
  if(mode==="EDIT"&&(!accountId||!/^[0-9a-f-]{36}$/i.test(accountId)))throw new NamedRuntimeError("IAM_ACCOUNT_SELECTION_REQUIRED");
  const basicData=rec(payload.basic_data);
  const frontL1=strings(payload.front_l1);
  const adminL1=strings(payload.admin_l1);
  for(const key of [...frontL1,...adminL1])if(!BUNDLE_PAGE[key])throw new NamedRuntimeError(`IAM-01-ERR-L1-EXPANSION:${key}`);
  const row=await upsertEntity(sql,{
    kind:"IAM_ACCOUNT_DRAFT",id:draftId,parent_id:accountId,status:"DRAFT",
    payload:{page_uid:"admin:IAM-01",mode,account_id:accountId,basic_data:basicData,front_l1:frontL1,admin_l1:adminL1,validated:false},
  });
  await audit(sql,{operation:"saveDraft",actorId:actor.user_id,correlationId:request.correlation_id,entityId:draftId,payload:row.payload});
  return{draft_id:draftId,state:"DRAFT",version:row.version};
}
async function validateDraft(request:IamRuntimeRequest){
  const {sql,actor}=await requireContext();
  const draftId=text(request.draft_id);
  if(!draftId)throw new NamedRuntimeError("IAM_DRAFT_REQUIRED");
  const draft=await requireDraft(sql,draftId);
  const payload=rec(draft.payload);
  const mode=text(payload.mode);
  if(mode!=="CREATE"&&mode!=="EDIT")throw new NamedRuntimeError("IAM_DRAFT_MODE_REQUIRED");
  const frontL1=strings(payload.front_l1),adminL1=strings(payload.admin_l1);
  await expandBundles(sql,[...frontL1,...adminL1]);
  const next={...payload,validated:true,validated_at:new Date().toISOString()};
  const row=await upsertEntity(sql,{kind:"IAM_ACCOUNT_DRAFT",id:draftId,parent_id:text(draft.parent_id),status:"VALIDATED",payload:next});
  await audit(sql,{operation:"validateDraft",actorId:actor.user_id,correlationId:request.correlation_id,entityId:draftId,payload:{version:row.version}});
  return{draft_id:draftId,state:"VALIDATED",version:row.version};
}
async function previewAuthorizationImpact(request:IamRuntimeRequest){
  const {sql,actor,session_token_hash}=await requireContext();
  const payload=rec(request.payload);
  const accountId=text(request.account_id)??text(payload.account_id);
  if(!accountId||!/^[0-9a-f-]{36}$/i.test(accountId))throw new NamedRuntimeError("IAM_ACCOUNT_ID_INVALID");
  const draftId=text(payload.draft_id);
  if(!draftId)throw new NamedRuntimeError("IAM_DRAFT_REQUIRED");
  const draft=await requireDraft(sql,draftId);
  if(text(draft.status)!=="VALIDATED")throw new NamedRuntimeError("IAM_DRAFT_NOT_VALIDATED");
  const draftPayload=rec(draft.payload);
  const frontL1=strings(payload.front_l1).length?strings(payload.front_l1):strings(draftPayload.front_l1);
  const adminL1=strings(payload.admin_l1).length?strings(payload.admin_l1):strings(draftPayload.admin_l1);
  const desired=await expandBundles(sql,[...frontL1,...adminL1]);
  const current=await currentAssignments(sql,session_token_hash,accountId);
  const added=[...desired.keys()].filter((ref)=>!current.has(ref));
  const removed=[...current.keys()].filter((ref)=>!desired.has(ref));
  const unchanged=[...desired.keys()].filter((ref)=>current.has(ref));
  const blocked:string[]=[];
  const approvalRequired=added.some((ref)=>desired.get(ref)?.risk_tier==="HIGH");
  const previewId=crypto.randomUUID();
  const previewPayload={
    preview_ref:previewId,account_id:accountId,draft_id:draftId,
    front_l1:frontL1,admin_l1:adminL1,added,removed,unchanged,blocked,
    approval_required:approvalRequired,
    desired_metadata:Object.fromEntries([...desired.entries()]),
  };
  await upsertEntity(sql,{kind:"IAM_AUTH_PREVIEW",id:previewId,parent_id:accountId,status:"READY",payload:previewPayload});
  await audit(sql,{operation:"previewAuthorizationImpact",actorId:actor.user_id,correlationId:request.correlation_id,entityId:previewId,payload:{added:added.length,removed:removed.length,unchanged:unchanged.length,approval_required:approvalRequired}});
  return previewPayload;
}
async function configureResource(request:IamRuntimeRequest){
  const {sql,actor}=await requireContext();
  const resourceId=text(request.resource_id);
  if(!resourceId)throw new NamedRuntimeError("IAM_GOVERNED_RESOURCE_ID_REQUIRED");
  const payload=rec(request.payload);
  if(payload.explicit_confirmation!==true&&text(payload.page_uid)==="admin:IAM-01")throw new NamedRuntimeError("IAM01_EXPLICIT_CONFIRMATION_REQUIRED");
  if(text(payload.page_uid)===AIAPI_PAGE_UID){
    if(!text(payload.reason))throw new NamedRuntimeError("AIAPI_CAPABILITY_CONFIG_REASON_REQUIRED");
    aiApiCapabilityConfig(payload);
  }
  const criteria=qaCriteriaConfig(payload);
  if(criteria){
    if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(resourceId))throw new NamedRuntimeError("SG02_CRITERIA_RESOURCE_ID_INVALID");
    if(!text(payload.reason))throw new NamedRuntimeError("SG02_CRITERIA_CONFIG_REASON_REQUIRED");
    const existing=first(await sql`
      SELECT criteria_version_id::text AS criteria_version_id,status::text AS status
      FROM quality_criteria_versions
      WHERE criteria_version_id=${resourceId}::uuid
      LIMIT 1
    `);
    if(existing)throw new NamedRuntimeError("SG02_ACTIVE_RESOURCE_IMMUTABLE");
  }
  const row=await upsertEntity(sql,{kind:"GOVERNED_RESOURCE",id:resourceId,status:"CONFIGURED",payload:{...payload,configured_by:actor.user_id,configured_at:new Date().toISOString()}});
  await audit(sql,{operation:"configureGovernedResource",actorId:actor.user_id,correlationId:request.correlation_id,entityId:resourceId,payload:{version:row.version},entityType:criteria?SG02_PAGE_UID:undefined});
  return{resource_id:resourceId,state:"CONFIGURED",version:row.version};
}
async function approveResource(request:IamRuntimeRequest){
  const {sql,actor}=await requireContext();
  const resourceId=text(request.resource_id);
  if(!resourceId)throw new NamedRuntimeError("IAM_GOVERNED_RESOURCE_ID_REQUIRED");
  const existing=await loadEntity(sql,"GOVERNED_RESOURCE",resourceId);
  if(!existing)throw new NamedRuntimeError("IAM_GOVERNED_RESOURCE_NOT_CONFIGURED");
  const requestPayload=rec(request.payload);
  const existingPayload=rec(existing.payload);
  const currentVersion=integer(existing.version);
  const approvalRef=`IAM-APPROVAL:${request.correlation_id}`;

  const criteria=qaCriteriaConfig(existingPayload);
  if(criteria){
    const expectedVersion=integer(requestPayload.expected_resource_version);
    if(expectedVersion!==null&&(!currentVersion||expectedVersion!==currentVersion))throw new NamedRuntimeError("SG02_CRITERIA_RESOURCE_VERSION_CONFLICT");
    if(!text(requestPayload.rationale))throw new NamedRuntimeError("SG02_CRITERIA_APPROVAL_RATIONALE_REQUIRED");
    const approvedType=text(requestPayload.resource_type);
    if(approvedType!==SG02_CRITERIA_RESOURCE_TYPE)throw new NamedRuntimeError("SG02_CRITERIA_RESOURCE_TYPE_MISMATCH");
    if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(resourceId))throw new NamedRuntimeError("SG02_CRITERIA_RESOURCE_ID_INVALID");

    const canonical={
      criteria_key:criteria.criteria_key,
      version_no:criteria.version_no,
      department:criteria.department,
      dimensions:criteria.dimensions,
      required_checks:criteria.required_checks,
      gate_policy:criteria.gate_policy,
    };
    const contentHash=sha256(stableJson(canonical));
    const collision=first(await sql`
      SELECT criteria_version_id::text AS criteria_version_id,criteria_key,version_no,status::text AS status,content_hash
      FROM quality_criteria_versions
      WHERE criteria_version_id=${resourceId}::uuid
         OR (criteria_key=${criteria.criteria_key} AND version_no=${criteria.version_no})
      LIMIT 1
    `);
    if(collision)throw new NamedRuntimeError(
      text(collision.criteria_version_id)===resourceId?"SG02_ACTIVE_RESOURCE_IMMUTABLE":"SG02_CRITERIA_VERSION_CONFLICT"
    );
    const approvedPayload={
      ...existingPayload,
      approved_by:actor.user_id,
      approved_at:new Date().toISOString(),
      approval_ref:approvalRef,
      approval_rationale:text(requestPayload.rationale),
      criteria_content_hash:contentHash,
    };
    await sql.transaction([
      sql`
        INSERT INTO quality_criteria_versions(
          criteria_version_id,criteria_key,version_no,department,dimensions,required_checks,gate_policy,status,content_hash
        ) VALUES(
          ${resourceId}::uuid,${criteria.criteria_key},${criteria.version_no},${criteria.department}::department_code,
          ${JSON.stringify(criteria.dimensions)}::jsonb,${JSON.stringify(criteria.required_checks)}::jsonb,
          ${JSON.stringify(criteria.gate_policy)}::jsonb,'APPROVED',${contentHash}
        )
      `,
      sql`
        INSERT INTO acpos_runtime.entities(kind,id,parent_id,status,version,payload)
        VALUES('GOVERNED_RESOURCE',${resourceId},${text(existing.parent_id)},'APPROVED',1,${JSON.stringify(approvedPayload)}::jsonb)
        ON CONFLICT(kind,id) DO UPDATE
        SET parent_id=EXCLUDED.parent_id,
            status='APPROVED',
            version=acpos_runtime.entities.version+1,
            payload=EXCLUDED.payload,
            updated_at=now()
      `,
    ]);
    const row=await loadEntity(sql,"GOVERNED_RESOURCE",resourceId);
    const materialized=first(await sql`
      SELECT criteria_version_id::text AS criteria_version_id,criteria_key,version_no::int,department::text AS department,status::text AS status,content_hash
      FROM quality_criteria_versions
      WHERE criteria_version_id=${resourceId}::uuid
      LIMIT 1
    `);
    if(!row||!materialized)throw new NamedRuntimeError("SG02_CRITERIA_MATERIALIZATION_FAILED");
    await audit(sql,{operation:"approveGovernedResource",actorId:actor.user_id,correlationId:request.correlation_id,entityId:resourceId,payload:{version:row.version,approval_ref:approvalRef,criteria_version_id:resourceId,content_hash:contentHash},entityType:SG02_PAGE_UID});
    return{
      resource_id:resourceId,state:"APPROVED",version:row.version,approval_ref:approvalRef,
      criteria_version_id:text(materialized.criteria_version_id),
      criteria_key:text(materialized.criteria_key),
      criteria_version_no:integer(materialized.version_no),
      criteria_department:text(materialized.department),
      criteria_status:text(materialized.status),
      criteria_content_hash:text(materialized.content_hash),
    };
  }

  if(text(existingPayload.page_uid)===AIAPI_PAGE_UID){
    const expectedVersion=integer(requestPayload.expected_resource_version);
    if(!expectedVersion||!currentVersion||expectedVersion!==currentVersion)throw new NamedRuntimeError("AIAPI_CAPABILITY_RESOURCE_VERSION_CONFLICT");
    if(!text(requestPayload.rationale))throw new NamedRuntimeError("AIAPI_CAPABILITY_APPROVAL_RATIONALE_REQUIRED");
    const configuredType=text(existingPayload.resource_type),approvedType=text(requestPayload.resource_type);
    if(!configuredType||!approvedType||configuredType!==approvedType)throw new NamedRuntimeError("AIAPI_CAPABILITY_RESOURCE_TYPE_MISMATCH");
    const capability=aiApiCapabilityConfig(existingPayload);
    if(!capability)throw new NamedRuntimeError("AIAPI_CAPABILITY_CONFIG_REQUIRED");
    const capabilityHash=sha256(JSON.stringify({
      provider_key:capability.provider_key,
      model_key:capability.model_key,
      capability_version:capability.capability_version,
      accepted_classifications:capability.accepted_classifications,
      input_schema:capability.input_schema,
      output_schema:capability.output_schema,
      limits:capability.limits,
    }));
    const approvedPayload={
      ...existingPayload,
      approved_by:actor.user_id,
      approved_at:new Date().toISOString(),
      approval_ref:approvalRef,
      approval_rationale:text(requestPayload.rationale),
      provider_capability_hash:capabilityHash,
    };
    await sql.transaction([
      sql`
        INSERT INTO provider_capabilities(
          provider_key,model_key,capability_version,accepted_classifications,input_schema,output_schema,limits,status,capability_hash
        ) VALUES(
          ${capability.provider_key},${capability.model_key},${capability.capability_version},
          ${capability.accepted_classifications}::classification_level[],
          ${JSON.stringify(capability.input_schema)}::jsonb,${JSON.stringify(capability.output_schema)}::jsonb,
          ${JSON.stringify(capability.limits)}::jsonb,'APPROVED',${capabilityHash}
        )
        ON CONFLICT(provider_key,model_key,capability_version) DO UPDATE
        SET accepted_classifications=EXCLUDED.accepted_classifications,
            input_schema=EXCLUDED.input_schema,
            output_schema=EXCLUDED.output_schema,
            limits=EXCLUDED.limits,
            status='APPROVED',
            capability_hash=EXCLUDED.capability_hash
      `,
      sql`
        INSERT INTO acpos_runtime.entities(kind,id,parent_id,status,version,payload)
        VALUES('GOVERNED_RESOURCE',${resourceId},${text(existing.parent_id)},'APPROVED',1,${JSON.stringify(approvedPayload)}::jsonb)
        ON CONFLICT(kind,id) DO UPDATE
        SET parent_id=EXCLUDED.parent_id,
            status='APPROVED',
            version=acpos_runtime.entities.version+1,
            payload=EXCLUDED.payload,
            updated_at=now()
      `,
    ]);
    const row=await loadEntity(sql,"GOVERNED_RESOURCE",resourceId);
    const materialized=first(await sql`
      SELECT provider_capability_id::text AS provider_capability_id,status::text AS status,capability_hash
      FROM provider_capabilities
      WHERE provider_key=${capability.provider_key}
        AND model_key=${capability.model_key}
        AND capability_version=${capability.capability_version}
      LIMIT 1
    `);
    if(!row||!materialized)throw new NamedRuntimeError("AIAPI_CAPABILITY_MATERIALIZATION_FAILED");
    await audit(sql,{operation:"approveGovernedResource",actorId:actor.user_id,correlationId:request.correlation_id,entityId:resourceId,payload:{version:row.version,approval_ref:approvalRef,provider_capability_id:text(materialized.provider_capability_id)}});
    return{
      resource_id:resourceId,state:"APPROVED",version:row.version,approval_ref:approvalRef,
      provider_capability_id:text(materialized.provider_capability_id),
      capability_status:text(materialized.status),
      capability_hash:text(materialized.capability_hash),
    };
  }

  const payload={...existingPayload,approved_by:actor.user_id,approved_at:new Date().toISOString(),approval_ref:approvalRef};
  const row=await upsertEntity(sql,{kind:"GOVERNED_RESOURCE",id:resourceId,parent_id:text(existing.parent_id),status:"APPROVED",payload});
  await audit(sql,{operation:"approveGovernedResource",actorId:actor.user_id,correlationId:request.correlation_id,entityId:resourceId,payload:{version:row.version,approval_ref:approvalRef}});
  return{resource_id:resourceId,state:"APPROVED",version:row.version,approval_ref:approvalRef};
}
async function assignPermission(request:IamRuntimeRequest){
  const {sql,actor,session_token_hash}=await requireContext();
  const accountId=text(request.account_id);
  if(!accountId)throw new NamedRuntimeError("IAM_ACCOUNT_ID_INVALID");
  const payload=rec(request.payload);
  if(payload.explicit_confirmation!==true)throw new NamedRuntimeError("IAM01_EXPLICIT_CONFIRMATION_REQUIRED");
  const parsed=parsePermissionRef(payload.permission_ref);
  if(!parsed)throw new NamedRuntimeError("IAM_PERMISSION_REF_INVALID");
  const resource=first(await sql`
    SELECT resource_id::text AS resource_id,resource_key,risk_tier
    FROM permission_resources
    WHERE resource_id=${parsed.resource_id}::uuid AND active=true
    LIMIT 1
  `);
  if(!resource)throw new NamedRuntimeError("IAM_PERMISSION_RESOURCE_NOT_FOUND");
  const current=await currentAssignments(sql,session_token_hash,accountId);
  if(current.has(permissionRef(parsed.resource_id,parsed.action)))return{permission_ref:permissionRef(parsed.resource_id,parsed.action),state:"UNCHANGED"};
  const risk=text(resource.risk_tier);
  const approvalRef=risk==="HIGH"?text(payload.approval_ref):text(payload.approval_ref);
  if(risk==="HIGH"&&!approvalRef)throw new NamedRuntimeError("ACCOUNT_PERMISSION_HIGH_RISK_APPROVAL_REQUIRED");
  const versionRow=first(await sql`
    SELECT COALESCE(MAX(version_no),0)::int+1 AS version_no
    FROM account_permission_assignments
    WHERE user_id=${accountId}::uuid AND resource_id=${parsed.resource_id}::uuid AND action=${parsed.action}
  `);
  const version=Number(versionRow?.version_no??1);
  const inserted=await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO account_permission_assignments(
      user_id,resource_id,action,effect,scope,condition,gate_profile,status,granted_by_user_id,approval_ref,version_no
    ) VALUES(
      ${accountId}::uuid,${parsed.resource_id}::uuid,${parsed.action},'ALLOW','{}'::jsonb,'{}'::jsonb,'{}'::jsonb,
      'APPROVED',${actor.user_id}::uuid,${approvalRef},${version}
    )
    RETURNING account_permission_assignment_id::text AS assignment_id
  `);
  const assignmentId=text(first(inserted)?.assignment_id);
  if(!assignmentId)throw new NamedRuntimeError("IAM_PERMISSION_ASSIGN_FAILED");
  await audit(sql,{operation:"assignAccountPermission",actorId:actor.user_id,correlationId:request.correlation_id,entityId:assignmentId,payload:{account_id:accountId,resource_id:parsed.resource_id,action:parsed.action}});
  return{permission_ref:permissionRef(parsed.resource_id,parsed.action),state:"ASSIGNED",assignment_id:assignmentId};
}
async function revokePermission(request:IamRuntimeRequest){
  const {sql,actor,session_token_hash}=await requireContext();
  const accountId=text(request.account_id);
  if(!accountId)throw new NamedRuntimeError("IAM_ACCOUNT_ID_INVALID");
  const payload=rec(request.payload);
  if(payload.explicit_confirmation!==true)throw new NamedRuntimeError("IAM01_EXPLICIT_CONFIRMATION_REQUIRED");
  const parsed=parsePermissionRef(payload.permission_ref);
  if(!parsed)throw new NamedRuntimeError("IAM_PERMISSION_REF_INVALID");
  const current=await currentAssignments(sql,session_token_hash,accountId);
  if(!current.has(permissionRef(parsed.resource_id,parsed.action)))return{permission_ref:permissionRef(parsed.resource_id,parsed.action),state:"UNCHANGED"};
  const versionRow=first(await sql`
    SELECT COALESCE(MAX(version_no),0)::int+1 AS version_no
    FROM account_permission_assignments
    WHERE user_id=${accountId}::uuid AND resource_id=${parsed.resource_id}::uuid AND action=${parsed.action}
  `);
  const version=Number(versionRow?.version_no??1);
  const inserted=await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO account_permission_assignments(
      user_id,resource_id,action,effect,scope,condition,gate_profile,status,granted_by_user_id,approval_ref,version_no
    ) VALUES(
      ${accountId}::uuid,${parsed.resource_id}::uuid,${parsed.action},'DENY','{}'::jsonb,'{}'::jsonb,'{}'::jsonb,
      'APPROVED',${actor.user_id}::uuid,NULL,${version}
    )
    RETURNING account_permission_assignment_id::text AS assignment_id
  `);
  const assignmentId=text(first(inserted)?.assignment_id);
  if(!assignmentId)throw new NamedRuntimeError("IAM_PERMISSION_REVOKE_FAILED");
  await audit(sql,{operation:"revokeAccountPermission",actorId:actor.user_id,correlationId:request.correlation_id,entityId:assignmentId,payload:{account_id:accountId,resource_id:parsed.resource_id,action:parsed.action}});
  return{permission_ref:permissionRef(parsed.resource_id,parsed.action),state:"REVOKED",assignment_id:assignmentId};
}

export async function executeProductionIamCommand(request:IamRuntimeRequest):Promise<unknown>{
  switch(request.operation){
    case"saveDraft":return saveDraft(request);
    case"validateDraft":return validateDraft(request);
    case"previewAuthorizationImpact":return previewAuthorizationImpact(request);
    case"configureGovernedResource":return configureResource(request);
    case"approveGovernedResource":return approveResource(request);
    case"assignAccountPermission":return assignPermission(request);
    case"revokeAccountPermission":return revokePermission(request);
    case"searchProjection":throw new NamedRuntimeError("USE_SEARCH_PROJECTION_ROUTE");
    case"getUiProjection":return{reason_code:"USE_UI_PROJECTION_ROUTE"};
  }
}

export function iamBundlePageMap(){return BUNDLE_PAGE;}
