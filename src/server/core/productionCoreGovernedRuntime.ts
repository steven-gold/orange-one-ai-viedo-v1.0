import { createHash } from "node:crypto";
import { cookies } from "next/headers";
import type { CoreRuntimeRequest } from "@/domain/core/coreRuntimeContract";
import { ensureProductionNeonRuntime,getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery,runRlsActorTransaction } from "@/server/database/rlsRuntime";
import { hashSessionToken,IDENTITY_COOKIE_NAME,resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";

type Sql=NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row=Record<string,unknown>;

const GOVERNED_PORTS=new Set<CoreRuntimeRequest["port_uid"]>([
  "CORE-01-PORT-PROJECT-CREATE",
  "CORE-01-PORT-PROJECT-VALIDATE",
  "CORE-01-PORT-PROJECT-CONFIRM",
  "CORE-01-PORT-CANDIDATE-CREATE",
  "CORE-01-PORT-CANDIDATE-COMPARE",
  "CORE-01-PORT-CANDIDATE-DECIDE",
  "CORE-01-PORT-DNA-LOCK",
  "CORE-01-PORT-CORE-REVIEW",
  "CORE-01-PORT-MOTHER-LOCK",
  "CORE-01-PORT-TOPIC-CREATE",
  "CORE-01-PORT-BLUEPRINT-CREATE",
  "CORE-01-PORT-BLUEPRINT-VALIDATE",
  "CORE-01-PORT-BLUEPRINT-APPROVE",
  "CORE-01-PORT-CHILD-LOCK",
  "CORE-01-PORT-LOCK-DECIDE",
  "CORE-01-PORT-CANONICAL-SCRIPT",
]);

function rec(value:unknown):Row{return value&&typeof value==="object"&&!Array.isArray(value)?value as Row:{};}
function text(value:unknown):string|null{return typeof value==="string"&&value.trim()?value.trim():null;}
function uuid(value:unknown):string|null{const v=text(value);return v&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)?v:null;}
function first(value:unknown):Row|null{return Array.isArray(value)?rec(value[0]):null;}
function stringArray(value:unknown):string[]{return Array.isArray(value)?[...new Set(value.flatMap((v)=>typeof v==="string"&&v.trim()?[v.trim()]:[]))]:[];}
function sha(value:unknown):string{return createHash("sha256").update(typeof value==="string"?value:JSON.stringify(value)).digest("hex");}
function required(value:unknown,reason:string):string{const v=text(value);if(!v)throw new NamedRuntimeError(reason);return v;}
function requiredUuid(value:unknown,reason:string):string{const v=uuid(value);if(!v)throw new NamedRuntimeError(reason);return v;}

function nonEmptyObject(value:unknown,reason:string):Row{
  const v=rec(value);
  if(Object.keys(v).length===0)throw new NamedRuntimeError(reason);
  return v;
}
function stableValue(value:unknown):unknown{
  if(Array.isArray(value))return value.map(stableValue);
  if(value&&typeof value==="object"){
    return Object.fromEntries(Object.entries(value as Row).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,stableValue(v)]));
  }
  return value;
}

async function context():Promise<{sql:Sql;actor_user_id:string;session_token_hash:string}>{
  await ensureProductionNeonRuntime();
  const sql=getProductionNeonSql();if(!sql)throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const token=(await cookies()).get(IDENTITY_COOKIE_NAME)?.value?.trim();
  if(!token)throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity=await resolveIdentityFromCookie(token);
  if(!identity.ok)throw new NamedRuntimeError(identity.reason_code);
  return{sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}

export function isProductionCoreGovernedPort(port_uid:CoreRuntimeRequest["port_uid"]):boolean{
  return GOVERNED_PORTS.has(port_uid);
}

async function createProjectDraft(request:CoreRuntimeRequest){
  const payload=rec(request.payload);
  const workspaceId=requiredUuid(payload.workspace_id,"PROJECT_DRAFT_REGISTERED_SCHEMA_PAYLOAD_REQUIRED");
  const projectCode=required(payload.project_code,"PROJECT_DRAFT_REGISTERED_SCHEMA_PAYLOAD_REQUIRED");
  const title=required(payload.title,"PROJECT_DRAFT_REGISTERED_SCHEMA_PAYLOAD_REQUIRED");
  const storyCore=nonEmptyObject(payload.story_core,"PROJECT_DRAFT_REGISTERED_SCHEMA_PAYLOAD_REQUIRED");
  if(payload.source_version_ref!==undefined&&payload.source_version_ref!==null&&payload.source_version_ref!==""){
    throw new NamedRuntimeError("PROJECT_DRAFT_REGISTERED_SCHEMA_PAYLOAD_REQUIRED");
  }
  const {sql,actor_user_id,session_token_hash}=await context();
  const workspace=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT workspace_id::text AS workspace_id,status::text AS status
    FROM public.workspaces
    WHERE workspace_id=${workspaceId}::uuid AND status='READY'
    LIMIT 1
  `));
  if(!workspace)throw new NamedRuntimeError("WORKSPACE_NOT_READY");

  const canonicalDocument=stableValue({
    workspace_id:workspaceId,
    project_code:projectCode,
    title,
    story_core:storyCore,
  });
  const contentHash=sha(canonicalDocument);

  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT p.project_id::text AS project_id,p.active_version_id::text AS project_version_ref,
           pv.content_hash::text AS content_hash,pv.story_core
    FROM public.projects p
    LEFT JOIN public.project_versions pv ON pv.project_version_id=p.active_version_id
    WHERE p.workspace_id=${workspaceId}::uuid AND p.project_code=${projectCode}
    LIMIT 1
  `));
  if(existing){
    if(
      text(existing.content_hash)!==contentHash
      ||JSON.stringify(stableValue(existing.story_core))!==JSON.stringify(stableValue(storyCore))
    ) throw new NamedRuntimeError("PROJECT_CODE_ALREADY_EXISTS_WITH_DIFFERENT_DRAFT");
    return{
      project_id:text(existing.project_id),project_version_ref:text(existing.project_version_ref),
      workspace_id:workspaceId,project_code:projectCode,title,state:"DRAFT",content_hash:contentHash,idempotent_replay:true,
    };
  }

  const projectId=crypto.randomUUID();
  const projectVersionId=crypto.randomUUID();
  const [projectRows,versionRows,activateRows]=await runRlsActorTransaction(sql,session_token_hash,[
    sql`
      INSERT INTO public.projects(project_id,workspace_id,project_code,title,owner_id,status)
      VALUES(${projectId}::uuid,${workspaceId}::uuid,${projectCode},${title},${actor_user_id}::uuid,'DRAFT')
      RETURNING project_id::text AS project_id
    `,
    sql`
      INSERT INTO public.project_versions(
        project_version_id,project_id,version_no,status,story_core,content_hash,created_by
      ) VALUES(
        ${projectVersionId}::uuid,${projectId}::uuid,1,'DRAFT',${JSON.stringify(storyCore)}::jsonb,${contentHash},${actor_user_id}::uuid
      )
      RETURNING project_version_id::text AS project_version_ref
    `,
    sql`
      UPDATE public.projects
      SET active_version_id=${projectVersionId}::uuid
      WHERE project_id=${projectId}::uuid AND owner_id=${actor_user_id}::uuid
      RETURNING project_id::text AS project_id
    `,
  ]);
  if(!first(projectRows)||!first(versionRows)||!first(activateRows))throw new NamedRuntimeError("PROJECT_CREATE_TRANSACTION_INCOMPLETE");
  return{
    project_id:projectId,project_version_ref:projectVersionId,workspace_id:workspaceId,
    project_code:projectCode,title,story_core:storyCore,state:"DRAFT",content_hash:contentHash,idempotent_replay:false,
  };
}

async function validateProjectDraft(request:CoreRuntimeRequest){
  const projectVersionId=requiredUuid(request.path_params?.projectVersionId,"REQUIRED_PATH_REFERENCE_MISSING:projectVersionId");
  const {sql,session_token_hash}=await context();
  const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT pv.project_version_id::text AS project_version_ref,pv.project_id::text AS project_id,pv.version_no,
           pv.status::text AS status,pv.story_core,pv.content_hash::text AS content_hash,
           p.workspace_id::text AS workspace_id,p.project_code,p.title,w.status::text AS workspace_status
    FROM public.project_versions pv
    JOIN public.projects p ON p.project_id=pv.project_id
    JOIN public.workspaces w ON w.workspace_id=p.workspace_id
    WHERE pv.project_version_id=${projectVersionId}::uuid
    LIMIT 1
  `));
  if(!row)throw new NamedRuntimeError("PROJECT_VERSION_NOT_FOUND");
  if(text(row.status)!=="DRAFT")throw new NamedRuntimeError("PROJECT_VERSION_NOT_IN_DRAFT");
  if(text(row.workspace_status)!=="READY")throw new NamedRuntimeError("WORKSPACE_NOT_READY");
  const workspaceId=requiredUuid(row.workspace_id,"WORKSPACE_NOT_READY");
  const projectCode=required(row.project_code,"PROJECT_DRAFT_REGISTERED_SCHEMA_INVALID");
  const title=required(row.title,"PROJECT_DRAFT_REGISTERED_SCHEMA_INVALID");
  const storyCore=nonEmptyObject(row.story_core,"PROJECT_DRAFT_REGISTERED_SCHEMA_INVALID");
  const expectedHash=sha(stableValue({
    workspace_id:workspaceId,
    project_code:projectCode,
    title,
    story_core:storyCore,
  }));
  if(text(row.content_hash)!==expectedHash)throw new NamedRuntimeError("PROJECT_DRAFT_CONTENT_HASH_MISMATCH");
  const updated=await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.project_versions
    SET decision_reason='VALIDATED'
    WHERE project_version_id=${projectVersionId}::uuid
      AND status='DRAFT'
      AND content_hash=${expectedHash}
    RETURNING project_version_id::text AS project_version_ref,project_id::text AS project_id,version_no
  `);
  const validated=first(updated);
  if(!validated)throw new NamedRuntimeError("PROJECT_DRAFT_VALIDATION_WRITE_FAILED");
  return{
    project_id:text(validated.project_id),project_version_ref:text(validated.project_version_ref),
    expected_version:Number(validated.version_no),state:"VALIDATED",content_hash:expectedHash,
  };
}

async function confirmProjectDraft(_request:CoreRuntimeRequest){
  throw new NamedRuntimeError("PROJECT_CONFIRM_ADOPT_CONTRACT_NOT_BOUND");
}

async function createCandidate(request:CoreRuntimeRequest){
  const payload=rec(request.payload);
  const projectId=requiredUuid(payload.project_id,"PROJECT_ID_REQUIRED");
  const topicId=payload.topic_id==null||payload.topic_id===""?null:requiredUuid(payload.topic_id,"TOPIC_ID_INVALID");
  const workItem=required(payload.work_item,"REQUIRED_WORK_ITEM_MISSING");
  const humanDecision=required(payload.human_decision,"HUMAN_DECISION_REQUIRED");
  const evidenceRefs=stringArray(payload.evidence_refs);
  const {sql,actor_user_id,session_token_hash}=await context();

  const lineage=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT sd.core_structured_decision_id::text AS structured_decision_id,
           sd.structured_document,
           sd.content_hash::text AS structured_content_hash,
           hd.core_human_decision_id::text AS human_decision_id,
           hd.core_evaluation_id::text AS core_evaluation_id,
           hd.conversation_id::text AS conversation_id,
           hd.context_fingerprint::text AS context_fingerprint,
           e.assistant_message_id::text AS assistant_message_id,
           e.result,
           e.project_id::text AS project_id,
           e.topic_id::text AS topic_id,
           e.work_item
    FROM public.core_structured_decisions sd
    JOIN public.core_human_decisions hd ON hd.core_human_decision_id=sd.core_human_decision_id
    JOIN public.core_evaluations e ON e.core_evaluation_id=hd.core_evaluation_id
    WHERE e.project_id=${projectId}::uuid
      AND ((${topicId}::uuid IS NULL AND e.topic_id IS NULL) OR e.topic_id=${topicId}::uuid)
      AND e.work_item=${workItem}
      AND e.result='PASS'
      AND hd.decision_text=${humanDecision}
    ORDER BY hd.created_at DESC
    LIMIT 1
  `));
  if(!lineage)throw new NamedRuntimeError("CORE_STRUCTURED_DECISION_REQUIRED");

  const structuredId=requiredUuid(lineage.structured_decision_id,"CORE_STRUCTURED_DECISION_REQUIRED");
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT candidate_version_id::text AS candidate_ref,version_no,content_hash::text AS content_hash
    FROM public.candidate_versions
    WHERE core_structured_decision_id=${structuredId}::uuid
    LIMIT 1
  `));
  if(existing)return{candidate_ref:text(existing.candidate_ref),version_no:Number(existing.version_no),content_hash:text(existing.content_hash),idempotent_replay:true};

  const prior=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT candidate_version_id::text AS candidate_ref,version_no
    FROM public.candidate_versions
    WHERE project_id=${projectId}::uuid
      AND ((${topicId}::uuid IS NULL AND topic_id IS NULL) OR topic_id=${topicId}::uuid)
      AND work_item=${workItem}
    ORDER BY version_no DESC
    LIMIT 1
  `));
  const versionNo=Math.max(1,Number(prior?.version_no??0)+1);
  const parentCandidate=uuid(prior?.candidate_ref);
  const candidateDocument=rec(lineage.structured_document);
  if(Object.keys(candidateDocument).length===0)throw new NamedRuntimeError("CORE_STRUCTURED_DECISION_EMPTY");
  const sourceRefs=[
    requiredUuid(lineage.core_evaluation_id,"CORE_EVALUATION_REQUIRED"),
    requiredUuid(lineage.human_decision_id,"CORE_HUMAN_DECISION_REQUIRED"),
    structuredId,
    requiredUuid(lineage.assistant_message_id,"CORE_ASSISTANT_MESSAGE_REQUIRED"),
    ...evidenceRefs,
  ];
  const contentHash=sha({project_id:projectId,topic_id:topicId,work_item:workItem,version_no:versionNo,parent_candidate_version_id:parentCandidate,candidate_document:candidateDocument,source_refs:sourceRefs});
  const candidateId=crypto.randomUUID();
  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.candidate_versions(
      candidate_version_id,project_id,topic_id,work_item,version_no,parent_candidate_version_id,
      source_conversation_id,source_assistant_message_id,core_evaluation_id,core_human_decision_id,
      core_structured_decision_id,candidate_document,source_refs,context_fingerprint,content_hash,created_by
    ) VALUES(
      ${candidateId}::uuid,${projectId}::uuid,${topicId}::uuid,${workItem},${versionNo},${parentCandidate}::uuid,
      ${requiredUuid(lineage.conversation_id,"CORE_CONVERSATION_REQUIRED")}::uuid,
      ${requiredUuid(lineage.assistant_message_id,"CORE_ASSISTANT_MESSAGE_REQUIRED")}::uuid,
      ${requiredUuid(lineage.core_evaluation_id,"CORE_EVALUATION_REQUIRED")}::uuid,
      ${requiredUuid(lineage.human_decision_id,"CORE_HUMAN_DECISION_REQUIRED")}::uuid,
      ${structuredId}::uuid,${JSON.stringify(candidateDocument)}::jsonb,${JSON.stringify(sourceRefs)}::jsonb,
      ${required(lineage.context_fingerprint,"CORE_CONTEXT_FINGERPRINT_REQUIRED")}::char(64),${contentHash}::char(64),${actor_user_id}::uuid
    )
    RETURNING candidate_version_id::text AS candidate_ref,version_no,content_hash::text
  `);
  const row=first(rows);if(!row)throw new NamedRuntimeError("CORE_CANDIDATE_INSERT_FAILED");
  return{candidate_ref:text(row.candidate_ref),version_no:Number(row.version_no),content_hash:text(row.content_hash),idempotent_replay:false};
}

async function compareCandidates(request:CoreRuntimeRequest){
  const payload=rec(request.payload);
  const raw=text(request.query?.candidate_refs)??text(payload.candidate_refs);
  const refs=[...new Set((raw??"").split(",").map((v)=>v.trim()).filter(Boolean))];
  if(!refs.length||refs.some((v)=>!uuid(v)))throw new NamedRuntimeError("EXACT_CANDIDATE_SET_REQUIRED");
  const {sql,session_token_hash}=await context();
  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT c.candidate_version_id::text AS candidate_ref,c.project_id::text AS project_id,c.topic_id::text AS topic_id,
           c.work_item,c.version_no,c.parent_candidate_version_id::text AS parent_candidate_ref,
           c.candidate_document,c.source_refs,c.context_fingerprint::text,c.content_hash::text,
           d.decision,d.reason,d.evidence_refs,d.decided_at::text
    FROM public.candidate_versions c
    LEFT JOIN public.candidate_decisions d ON d.candidate_version_id=c.candidate_version_id
    WHERE c.candidate_version_id=ANY(${refs}::uuid[])
  `);
  const found=new Map((Array.isArray(rows)?rows:[]).map((row)=>[text(rec(row).candidate_ref),rec(row)]));
  if(found.size!==refs.length)throw new NamedRuntimeError("CANDIDATE_SET_MISMATCH");
  const comparison=refs.map((ref)=>found.get(ref)!);
  const projects=new Set(comparison.map((r)=>text(r.project_id)));
  if(projects.size!==1)throw new NamedRuntimeError("CANDIDATE_SET_SCOPE_MISMATCH");
  return{exact_candidate_refs:refs,comparison,read_only:true,version_mutation:false};
}

async function decideCandidate(request:CoreRuntimeRequest){
  const payload=rec(request.payload);
  const candidateId=requiredUuid(request.path_params?.id??payload.candidate_ref,"REQUIRED_PATH_REFERENCE_MISSING:id");
  const decisionInput=required(payload.decision,"CANDIDATE_DECISION_INVALID").toUpperCase();
  const decision=decisionInput==="ACCEPT"?"ACCEPTED":decisionInput==="RETURN"?"MODIFY_REQUESTED":null;
  if(!decision)throw new NamedRuntimeError("CANDIDATE_DECISION_INVALID");
  const reason=required(payload.reason_text,"CANDIDATE_DECISION_REASON_REQUIRED");
  const evidenceRefs=stringArray(payload.evidence_refs);
  const {sql,actor_user_id,session_token_hash}=await context();
  const candidate=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT candidate_version_id::text AS candidate_ref,project_id::text AS project_id,content_hash::text AS content_hash
    FROM public.candidate_versions WHERE candidate_version_id=${candidateId}::uuid LIMIT 1
  `));
  if(!candidate)throw new NamedRuntimeError("CANDIDATE_NOT_FOUND");
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT candidate_decision_id::text AS decision_id,decision,reason,evidence_refs,decided_at::text
    FROM public.candidate_decisions WHERE candidate_version_id=${candidateId}::uuid LIMIT 1
  `));
  if(existing){
    if(text(existing.decision)!==decision||text(existing.reason)!==reason)throw new NamedRuntimeError("CANDIDATE_DECISION_ALREADY_RECORDED");
    return{candidate_ref:candidateId,decision,state:decision,decision_id:text(existing.decision_id),idempotent_replay:true};
  }
  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.candidate_decisions(
      candidate_version_id,decision,reason,evidence_refs,candidate_content_hash,decided_by
    ) VALUES(
      ${candidateId}::uuid,${decision},${reason},${JSON.stringify(evidenceRefs)}::jsonb,
      ${required(candidate.content_hash,"CANDIDATE_CONTENT_HASH_REQUIRED")}::char(64),${actor_user_id}::uuid
    )
    RETURNING candidate_decision_id::text AS decision_id,decided_at::text
  `);
  const row=first(rows);if(!row)throw new NamedRuntimeError("CANDIDATE_DECISION_INSERT_FAILED");
  return{candidate_ref:candidateId,project_id:text(candidate.project_id),decision,state:decision,decision_id:text(row.decision_id),idempotent_replay:false};
}

async function requestDnaLock(request:CoreRuntimeRequest){
  const payload=rec(request.payload);
  const dnaId=requiredUuid(payload.dna_version_ref,"REQUIRED_DNA_VERSION_REF_MISSING");
  const evidenceRefs=stringArray(payload.evidence_refs);
  const {sql,actor_user_id,session_token_hash}=await context();
  const dna=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT dv.dna_version_id::text AS dna_version_ref,dv.project_id::text AS project_id,dv.status,
           dv.lock_decision_request_id::text AS lock_decision_request_id,dv.checksum::text AS checksum,
           p.workspace_id::text AS workspace_id
    FROM public.dna_versions dv JOIN public.projects p ON p.project_id=dv.project_id
    WHERE dv.dna_version_id=${dnaId}::uuid LIMIT 1
  `));
  if(!dna)throw new NamedRuntimeError("DNA_VERSION_NOT_FOUND");
  if(text(dna.status)!=="CANDIDATE")throw new NamedRuntimeError("DNA_NOT_CANDIDATE");
  const existing=uuid(dna.lock_decision_request_id);
  if(existing)return{dna_version_ref:dnaId,project_id:text(dna.project_id),lock_decision_request_id:existing,lock_state:"REVIEW_REQUESTED",final_lock_granted:false,idempotent_replay:true};
  const projectId=requiredUuid(dna.project_id,"PROJECT_ID_REQUIRED");
  if(payload.project_id&&uuid(payload.project_id)!==projectId)throw new NamedRuntimeError("DNA_PROJECT_SCOPE_MISMATCH");
  const resource=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT resource_id::text AS resource_id FROM public.permission_resources
    WHERE resource_key='api:requestDNALock' AND resource_type='API' AND active=true LIMIT 1
  `));
  const resourceId=requiredUuid(resource?.resource_id,"PERMISSION_RESOURCE_NOT_FOUND");
  const scope={project_id:projectId,dna_version_ref:dnaId};
  const condition={expected_status:"CANDIDATE",expected_checksum:required(dna.checksum,"DNA_CHECKSUM_REQUIRED")};
  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.decision_requests(
      workspace_id,required_resource_id,required_action,required_scope,condition_snapshot,reason,evidence_refs,
      impact_scope,state,correlation_id,created_by_actor_type,created_by_user_id
    ) VALUES(
      ${requiredUuid(dna.workspace_id,"WORKSPACE_ID_REQUIRED")}::uuid,${resourceId}::uuid,'EXECUTE',
      ${JSON.stringify(scope)}::jsonb,${JSON.stringify(condition)}::jsonb,'requestDNALock',
      ${JSON.stringify(evidenceRefs)}::jsonb,${JSON.stringify(scope)}::jsonb,'OPEN',
      ${request.correlation_id}::uuid,'USER',${actor_user_id}::uuid
    )
    RETURNING decision_request_id::text AS lock_decision_request_id
  `);
  const requestId=requiredUuid(first(rows)?.lock_decision_request_id,"DNA_LOCK_REQUEST_INSERT_FAILED");
  const updated=await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.dna_versions SET lock_decision_request_id=${requestId}::uuid
    WHERE dna_version_id=${dnaId}::uuid AND status='CANDIDATE' AND lock_decision_request_id IS NULL
    RETURNING dna_version_id::text
  `);
  if(!first(updated))throw new NamedRuntimeError("DNA_LOCK_BIND_FAILED");
  return{dna_version_ref:dnaId,project_id:projectId,lock_decision_request_id:requestId,lock_state:"REVIEW_REQUESTED",final_lock_granted:false,idempotent_replay:false};
}

async function submitCoreReview(request:CoreRuntimeRequest){
  const payload=rec(request.payload);
  const projectId=requiredUuid(payload.project_id,"PROJECT_ID_REQUIRED");
  const versionId=requiredUuid(payload.project_version_ref,"REQUIRED_PROJECT_VERSION_REF_MISSING");
  const {sql,session_token_hash}=await context();
  const accepted=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT c.candidate_version_id::text AS candidate_ref,d.candidate_decision_id::text AS decision_id
    FROM public.candidate_versions c JOIN public.candidate_decisions d ON d.candidate_version_id=c.candidate_version_id
    WHERE c.project_id=${projectId}::uuid AND d.decision='ACCEPTED'
    ORDER BY d.decided_at DESC LIMIT 1
  `));
  if(!accepted)throw new NamedRuntimeError("CORE_PROJECT_CANDIDATE_REQUIRED");
  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.project_versions SET status='CORE_REVIEW'
    WHERE project_version_id=${versionId}::uuid AND project_id=${projectId}::uuid AND status IN('CORE_MODELING','CORE_REVIEW')
    RETURNING project_version_id::text
  `);
  if(!first(rows))throw new NamedRuntimeError("PROJECT_NOT_IN_CORE_MODELING");
  await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.projects SET status='CORE_REVIEW'
    WHERE project_id=${projectId}::uuid AND status IN('CORE_MODELING','CORE_REVIEW')
    RETURNING project_id
  `);
  return{project_id:projectId,project_version_ref:versionId,candidate_ref:text(accepted.candidate_ref),state:"CORE_REVIEW",final_approval_granted:false};
}

function lockRequestInput(payload:Record<string,unknown>){
  const allowedKeys=new Set(["scope","expected_version","correlation_id","idempotency_key","target_ref","request_reason","requested_scope_refs"]);
  if(Object.keys(payload).some((key)=>!allowedKeys.has(key)))throw new NamedRuntimeError("LOCK_REQUEST_SCHEMA_INVALID");
  const scope=nonEmptyObject(payload.scope,"R9_CONTEXT_REQUIRED");
  const expectedVersion=required(payload.expected_version,"EXPECTED_VERSION_INVALID");
  if(!/^v[1-9][0-9]*$/.test(expectedVersion))throw new NamedRuntimeError("EXPECTED_VERSION_INVALID");
  const correlationId=requiredUuid(payload.correlation_id,"CORRELATION_ID_INVALID");
  const idempotencyKey=required(payload.idempotency_key,"IDEMPOTENCY_KEY_INVALID");
  if(idempotencyKey.length<16||idempotencyKey.length>128)throw new NamedRuntimeError("IDEMPOTENCY_KEY_INVALID");
  const targetRef=requiredUuid(payload.target_ref,"TARGET_REF_INVALID");
  const requestReason=required(payload.request_reason,"REQUEST_REASON_INVALID");
  const requestedScopeRefs=payload.requested_scope_refs===undefined?[]:stringArray(payload.requested_scope_refs);
  if(payload.requested_scope_refs!==undefined&&(!Array.isArray(payload.requested_scope_refs)||requestedScopeRefs.length!==(payload.requested_scope_refs as unknown[]).length)){
    throw new NamedRuntimeError("REQUESTED_SCOPE_REFS_INVALID");
  }
  return{scope,expectedVersion,correlationId,idempotencyKey,targetRef,requestReason,requestedScopeRefs};
}

async function requestLockReview(request:CoreRuntimeRequest,kind:"MOTHER"|"CHILD"){
  const input=lockRequestInput(rec(request.payload));
  const {sql,session_token_hash}=await context();
  try{
    const rows=await runRlsActorQuery(sql,session_token_hash,sql`
      SELECT lock_review_id::text,lock_kind,review_status,review_version,target_ref::text,
             criteria_version_id::text,reviewer_count,evidence_count,idempotent_replay
      FROM acpos_runtime.request_lock_review(
        ${kind},
        ${JSON.stringify(input.scope)}::jsonb,
        ${input.expectedVersion},
        ${input.correlationId}::uuid,
        ${input.idempotencyKey},
        ${input.targetRef}::uuid,
        ${input.requestReason},
        ${JSON.stringify(input.requestedScopeRefs)}::jsonb
      )
    `);
    const row=first(rows);
    if(!row)throw new NamedRuntimeError("LOCK_REVIEW_REQUEST_WRITE_FAILED");
    return{
      lock_review_id:text(row.lock_review_id),
      lock_kind:text(row.lock_kind),
      lock_state:text(row.review_status),
      review_version:Number(row.review_version),
      target_ref:text(row.target_ref),
      criteria_version_id:text(row.criteria_version_id),
      reviewer_count:Number(row.reviewer_count),
      evidence_count:Number(row.evidence_count),
      final_lock_granted:false,
      idempotent_replay:row.idempotent_replay===true,
      correlation_id:input.correlationId,
    };
  }catch(error){
    const message=error instanceof Error?error.message:String(error);
    for(const code of [
      "PERMISSION_OR_SCOPE_DENIED","R9_CONTEXT_REQUIRED","EXPECTED_VERSION_INVALID","CORRELATION_ID_INVALID",
      "IDEMPOTENCY_KEY_INVALID","TARGET_REF_INVALID","REQUEST_REASON_INVALID","REQUESTED_SCOPE_REFS_INVALID",
      "IDEMPOTENCY_CONFLICT","LOCK_TARGET_NOT_READY","VERSION_CONFLICT","SCOPE_WORKSPACE_MISMATCH",
      "SCOPE_PROJECT_MISMATCH","SCOPE_TOPIC_MISMATCH","LOCK_CRITERIA_AMBIGUOUS","LOCK_CRITERIA_VERSION_REQUIRED",
      "LOCK_EVIDENCE_REQUIRED","CORE_LOCK_REVIEWER_PATH_UNRESOLVED"
    ])if(message.includes(code))throw new NamedRuntimeError(code);
    if(message.includes("REQUESTED_SCOPE_REF_NOT_RESOLVED"))throw new NamedRuntimeError("REQUESTED_SCOPE_REF_NOT_RESOLVED");
    throw error;
  }
}

async function requestMotherLock(request:CoreRuntimeRequest){
  return requestLockReview(request,"MOTHER");
}

async function createTopic(request:CoreRuntimeRequest){
  const payload=rec(request.payload);
  const projectId=requiredUuid(request.path_params?.projectId,"REQUIRED_PATH_REFERENCE_MISSING:projectId");
  if(payload.project_id!==undefined&&requiredUuid(payload.project_id,"TOPIC_CANONICAL_LINEAGE_INCOMPLETE")!==projectId){
    throw new NamedRuntimeError("TOPIC_CANONICAL_LINEAGE_INCOMPLETE");
  }
  const title=required(payload.title,"TOPIC_CANONICAL_LINEAGE_INCOMPLETE");
  const topicCode=required(payload.topic_code,"TOPIC_CANONICAL_LINEAGE_INCOMPLETE");
  const motherLockRef=requiredUuid(payload.mother_lock_ref,"TOPIC_CANONICAL_LINEAGE_INCOMPLETE");
  const motherProjectVersionRef=requiredUuid(payload.mother_project_version_ref,"TOPIC_CANONICAL_LINEAGE_INCOMPLETE");
  const boundary=nonEmptyObject(payload.boundary,"TOPIC_CANONICAL_LINEAGE_INCOMPLETE");
  const bridge=nonEmptyObject(payload.bridge,"TOPIC_CANONICAL_LINEAGE_INCOMPLETE");
  if(payload.source_version_ref!==undefined&&payload.source_version_ref!==null&&payload.source_version_ref!==""){
    throw new NamedRuntimeError("TOPIC_CANONICAL_LINEAGE_INCOMPLETE");
  }

  const {sql,actor_user_id,session_token_hash}=await context();
  const lock=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT ml.mother_lock_id::text AS mother_lock_ref,ml.project_id::text AS project_id,
           ml.project_version_id::text AS mother_project_version_ref,ml.project_hash::text AS project_hash,
           ml.status::text AS lock_status,pv.status::text AS project_version_status
    FROM public.mother_locks ml
    JOIN public.project_versions pv ON pv.project_version_id=ml.project_version_id
    WHERE ml.mother_lock_id=${motherLockRef}::uuid
      AND ml.project_id=${projectId}::uuid
      AND ml.project_version_id=${motherProjectVersionRef}::uuid
      AND ml.status='MOTHER_LOCKED'
    LIMIT 1
  `));
  if(!lock)throw new NamedRuntimeError("TOPIC_CANONICAL_LINEAGE_INCOMPLETE");

  const canonicalDocument=stableValue({
    project_id:projectId,
    mother_lock_ref:motherLockRef,
    mother_project_version_ref:motherProjectVersionRef,
    topic_code:topicCode,
    title,
    boundary,
    bridge,
  });
  const contentHash=sha(canonicalDocument);

  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT t.topic_id::text AS topic_id,t.active_version_id::text AS topic_version_ref,
           tv.content_hash::text AS content_hash,tv.boundary,tv.bridge,
           tv.mother_project_version_id::text AS mother_project_version_ref
    FROM public.topics t
    LEFT JOIN public.topic_versions tv ON tv.topic_version_id=t.active_version_id
    WHERE t.project_id=${projectId}::uuid AND t.topic_code=${topicCode}
    LIMIT 1
  `));
  if(existing){
    if(
      text(existing.content_hash)!==contentHash
      ||text(existing.mother_project_version_ref)!==motherProjectVersionRef
      ||JSON.stringify(stableValue(existing.boundary))!==JSON.stringify(stableValue(boundary))
      ||JSON.stringify(stableValue(existing.bridge))!==JSON.stringify(stableValue(bridge))
    ) throw new NamedRuntimeError("TOPIC_CODE_ALREADY_EXISTS_WITH_DIFFERENT_LINEAGE");
    return{
      topic_id:text(existing.topic_id),topic_version_ref:text(existing.topic_version_ref),project_id:projectId,
      topic_code:topicCode,title,state:"DRAFT",content_hash:contentHash,idempotent_replay:true,
    };
  }

  const topicId=crypto.randomUUID();
  const topicVersionId=crypto.randomUUID();
  const [topicRows,versionRows,activateRows]=await runRlsActorTransaction(sql,session_token_hash,[
    sql`
      INSERT INTO public.topics(topic_id,project_id,topic_code,title,mother_lock_id,status)
      VALUES(${topicId}::uuid,${projectId}::uuid,${topicCode},${title},${motherLockRef}::uuid,'DRAFT')
      RETURNING topic_id::text AS topic_id
    `,
    sql`
      INSERT INTO public.topic_versions(
        topic_version_id,topic_id,version_no,mother_project_version_id,boundary,bridge,status,content_hash,created_by
      ) VALUES(
        ${topicVersionId}::uuid,${topicId}::uuid,1,${motherProjectVersionRef}::uuid,
        ${JSON.stringify(boundary)}::jsonb,${JSON.stringify(bridge)}::jsonb,'DRAFT',${contentHash},${actor_user_id}::uuid
      )
      RETURNING topic_version_id::text AS topic_version_ref
    `,
    sql`
      UPDATE public.topics
      SET active_version_id=${topicVersionId}::uuid
      WHERE topic_id=${topicId}::uuid AND project_id=${projectId}::uuid
      RETURNING topic_id::text AS topic_id
    `,
  ]);
  if(!first(topicRows)||!first(versionRows)||!first(activateRows))throw new NamedRuntimeError("TOPIC_CREATE_TRANSACTION_INCOMPLETE");
  return{
    topic_id:topicId,topic_version_ref:topicVersionId,project_id:projectId,topic_code:topicCode,title,
    mother_lock_ref:motherLockRef,mother_project_version_ref:motherProjectVersionRef,
    boundary,bridge,state:"DRAFT",content_hash:contentHash,idempotent_replay:false,
  };
}

async function createBlueprint(request:CoreRuntimeRequest){
  const topicId=requiredUuid(request.path_params?.id,"REQUIRED_PATH_REFERENCE_MISSING:id");
  const {sql,session_token_hash}=await context();
  const source=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT t.topic_id::text AS topic_id,t.project_id::text AS project_id,t.active_version_id::text AS topic_version_id,
           pc.topic_production_contract_id::text AS topic_production_contract_id,pc.contract_hash::text AS contract_hash,pc.status::text AS contract_status
    FROM public.topics t
    JOIN public.topic_production_contracts pc ON pc.topic_version_id=t.active_version_id
    WHERE t.topic_id=${topicId}::uuid
    ORDER BY pc.contract_version DESC LIMIT 1
  `));
  if(!source)throw new NamedRuntimeError("TOPIC_PRODUCTION_CONTRACT_REQUIRED");
  const masterRows=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT master_blueprint_id::text AS master_blueprint_id,blueprint_key,version_no,schema,content_hash::text
    FROM public.master_blueprints
    WHERE status='APPROVED' AND COALESCE(schema->>'purpose','')<>'TEST_ONLY'
    ORDER BY created_at DESC
    LIMIT 2
  `);
  const masters=Array.isArray(masterRows)?masterRows:[];
  if(masters.length===0)throw new NamedRuntimeError("MASTER_BLUEPRINT_AUTHORITY_NOT_READY");
  if(masters.length!==1)throw new NamedRuntimeError("MASTER_BLUEPRINT_AUTHORITY_AMBIGUOUS");
  throw new NamedRuntimeError("CORE_BLUEPRINT_DOCUMENT_MATERIALIZER_NOT_BOUND");
}

async function validateBlueprint(request:CoreRuntimeRequest){
  const id=requiredUuid(request.path_params?.id,"REQUIRED_PATH_REFERENCE_MISSING:id");
  const {sql,session_token_hash}=await context();
  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.blueprint_versions SET status='BLUEPRINT_REVIEW'
    WHERE blueprint_version_id=${id}::uuid AND status='BLUEPRINT_DRAFT'
    RETURNING blueprint_version_id::text AS blueprint_version_ref,topic_blueprint_id::text AS topic_blueprint_id
  `);
  const row=first(rows);if(!row)throw new NamedRuntimeError("BLUEPRINT_NOT_DRAFT");
  const topicBlueprintId=requiredUuid(row.topic_blueprint_id,"TOPIC_BLUEPRINT_REQUIRED");
  await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.topic_blueprints SET status='BLUEPRINT_REVIEW'
    WHERE topic_blueprint_id=${topicBlueprintId}::uuid
    RETURNING topic_blueprint_id
  `);
  return{blueprint_version_ref:text(row.blueprint_version_ref),state:"BLUEPRINT_REVIEW"};
}

async function approveBlueprint(request:CoreRuntimeRequest){
  const id=requiredUuid(request.path_params?.id,"REQUIRED_PATH_REFERENCE_MISSING:id");
  const {sql,session_token_hash}=await context();
  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.blueprint_versions SET status='READY_FOR_CHILD_REVIEW',frozen_at=now()
    WHERE blueprint_version_id=${id}::uuid AND status='BLUEPRINT_REVIEW'
    RETURNING blueprint_version_id::text AS blueprint_version_ref,topic_blueprint_id::text AS topic_blueprint_id
  `);
  const row=first(rows);if(!row)throw new NamedRuntimeError("BLUEPRINT_NOT_IN_REVIEW");
  const topicBlueprintId=requiredUuid(row.topic_blueprint_id,"TOPIC_BLUEPRINT_REQUIRED");
  await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.topic_blueprints SET status='READY_FOR_CHILD_REVIEW',active_version_id=${id}::uuid
    WHERE topic_blueprint_id=${topicBlueprintId}::uuid
    RETURNING topic_blueprint_id
  `);
  return{blueprint_version_ref:text(row.blueprint_version_ref),state:"READY_FOR_CHILD_REVIEW"};
}

async function requestChildLock(request:CoreRuntimeRequest){
  return requestLockReview(request,"CHILD");
}

async function decideLockReview(request:CoreRuntimeRequest){
  const payload=rec(request.payload);
  const allowedKeys=new Set(["scope","expected_version","correlation_id","idempotency_key","lock_review_id","decision","reason"]);
  if(Object.keys(payload).some((key)=>!allowedKeys.has(key)))throw new NamedRuntimeError("LOCK_REVIEW_REQUEST_SCHEMA_INVALID");
  const pathId=requiredUuid(request.path_params?.id,"REQUIRED_PATH_REFERENCE_MISSING:id");
  const bodyId=requiredUuid(payload.lock_review_id,"LOCK_REVIEW_ID_INVALID");
  if(pathId!==bodyId)throw new NamedRuntimeError("PATH_BODY_ID_MISMATCH");
  const scope=nonEmptyObject(payload.scope,"R9_CONTEXT_REQUIRED");
  const expectedVersion=required(payload.expected_version,"EXPECTED_VERSION_INVALID");
  if(!/^v[1-9][0-9]*$/.test(expectedVersion))throw new NamedRuntimeError("EXPECTED_VERSION_INVALID");
  const correlationId=requiredUuid(payload.correlation_id,"CORRELATION_ID_INVALID");
  const idempotencyKey=required(payload.idempotency_key,"IDEMPOTENCY_KEY_INVALID");
  if(idempotencyKey.length<16||idempotencyKey.length>128)throw new NamedRuntimeError("IDEMPOTENCY_KEY_INVALID");
  const decision=required(payload.decision,"DECISION_INVALID");
  if(decision!=="APPROVE"&&decision!=="REJECT")throw new NamedRuntimeError("DECISION_INVALID");
  const reason=required(payload.reason,"REASON_INVALID");
  const {sql,session_token_hash}=await context();
  try{
    const rows=await runRlsActorQuery(sql,session_token_hash,sql`
      SELECT
        lock_review_id::text,
        lock_kind,
        decision_status,
        review_version,
        lock_ref::text,
        idempotent_replay
      FROM acpos_runtime.decide_lock_review(
        ${pathId}::uuid,
        ${expectedVersion},
        ${JSON.stringify(scope)}::jsonb,
        ${decision},
        ${reason},
        ${correlationId}::uuid,
        ${idempotencyKey}
      )
    `);
    const row=first(rows);
    if(!row)throw new NamedRuntimeError("LOCK_REVIEW_DECISION_WRITE_FAILED");
    return{
      lock_review_id:text(row.lock_review_id),
      lock_kind:text(row.lock_kind),
      decision_status:text(row.decision_status),
      review_version:Number(row.review_version),
      lock_ref:text(row.lock_ref),
      idempotent_replay:row.idempotent_replay===true,
      correlation_id:correlationId,
    };
  }catch(error){
    const message=error instanceof Error?error.message:String(error);
    for(const code of [
      "PERMISSION_OR_SCOPE_DENIED","SEPARATION_OF_DUTIES_VIOLATION","LOCK_REVIEW_NOT_FOUND",
      "LOCK_REVIEW_STATE_CONFLICT","VERSION_CONFLICT","IDEMPOTENCY_CONFLICT","EXPECTED_VERSION_INVALID",
      "DECISION_INVALID","REASON_INVALID","IDEMPOTENCY_KEY_INVALID","R9_CONTEXT_REQUIRED",
      "SCOPE_WORKSPACE_MISMATCH","SCOPE_PROJECT_MISMATCH","SCOPE_TOPIC_MISMATCH","LOCK_REVIEW_TARGET_LINEAGE_INVALID",
    ])if(message.includes(code))throw new NamedRuntimeError(code);
    throw error;
  }
}

async function canonicalScript(request:CoreRuntimeRequest){
  const topicId=requiredUuid(request.path_params?.id,"REQUIRED_PATH_REFERENCE_MISSING:id");
  const {sql,session_token_hash}=await context();
  const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT csv.canonical_script_version_id::text AS canonical_script_ref,csv.topic_id::text AS topic_id,
           csv.source_topic_version_id::text AS topic_version_id,csv.version_no,csv.status::text AS status,
           csv.script_document,csv.content_hash::text AS content_hash,t.project_id::text AS project_id
    FROM public.canonical_script_versions csv JOIN public.topics t ON t.topic_id=csv.topic_id
    WHERE csv.topic_id=${topicId}::uuid
    ORDER BY csv.version_no DESC LIMIT 1
  `));
  if(!row)throw new NamedRuntimeError("CANONICAL_SCRIPT_NOT_FOUND");
  const document=rec(row.script_document);
  const lineage=rec(document.identity_and_lineage);
  const projectId=requiredUuid(row.project_id,"PROJECT_ID_REQUIRED");
  const blueprintRef=uuid(lineage.project_blueprint_ref);
  const scopeRef=uuid(lineage.topic_production_scope_ref);
  const candidateRef=uuid(lineage.source_candidate_ref);
  const scriptHash=text(lineage.canonical_script_hash);
  const projectCanonRefs=stringArray(lineage.project_canon_refs);
  const dnaRefs=stringArray(lineage.dna_refs);
  if(uuid(lineage.project_id)!==projectId||uuid(lineage.topic_id)!==topicId||!blueprintRef||!scopeRef||!candidateRef||!scriptHash){
    throw new NamedRuntimeError("CANONICAL_SCRIPT_LINEAGE_UNRESOLVED");
  }
  if(scriptHash!==text(row.content_hash))throw new NamedRuntimeError("CANONICAL_SCRIPT_HASH_MISMATCH");
  const lineageCheck=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT
      EXISTS(
        SELECT 1 FROM public.blueprint_versions bv
        JOIN public.topic_blueprints tb ON tb.topic_blueprint_id=bv.topic_blueprint_id
        JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
        JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
        WHERE bv.blueprint_version_id=${blueprintRef}::uuid AND tv.topic_id=${topicId}::uuid
      ) AS blueprint_ok,
      EXISTS(
        SELECT 1 FROM public.topic_production_contracts pc
        JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
        WHERE pc.topic_production_contract_id=${scopeRef}::uuid AND tv.topic_id=${topicId}::uuid
      ) AS scope_ok,
      EXISTS(
        SELECT 1 FROM public.candidate_versions c
        JOIN public.candidate_decisions d ON d.candidate_version_id=c.candidate_version_id
        WHERE c.candidate_version_id=${candidateRef}::uuid AND c.project_id=${projectId}::uuid AND d.decision='ACCEPTED'
      ) AS candidate_ok
  `));
  if(lineageCheck?.blueprint_ok!==true||lineageCheck?.scope_ok!==true||lineageCheck?.candidate_ok!==true){
    throw new NamedRuntimeError("CANONICAL_SCRIPT_LINEAGE_UNRESOLVED");
  }
  return{
    canonical_script_ref:text(row.canonical_script_ref),topic_id:topicId,project_id:projectId,
    topic_version_id:text(row.topic_version_id),version_no:Number(row.version_no),status:text(row.status),
    content_hash:text(row.content_hash),script_document:document,
    project_blueprint_ref:blueprintRef,topic_production_scope_ref:scopeRef,source_candidate_ref:candidateRef,
    project_canon_refs:projectCanonRefs,dna_refs:dnaRefs,lineage_complete:true,read_only:true,
  };
}

export async function executeProductionCoreGovernedPort(request:CoreRuntimeRequest):Promise<unknown>{
  switch(request.port_uid){
    case "CORE-01-PORT-PROJECT-CREATE":return createProjectDraft(request);
    case "CORE-01-PORT-PROJECT-VALIDATE":return validateProjectDraft(request);
    case "CORE-01-PORT-PROJECT-CONFIRM":return confirmProjectDraft(request);
    case "CORE-01-PORT-CANDIDATE-CREATE":return createCandidate(request);
    case "CORE-01-PORT-CANDIDATE-COMPARE":return compareCandidates(request);
    case "CORE-01-PORT-CANDIDATE-DECIDE":return decideCandidate(request);
    case "CORE-01-PORT-DNA-LOCK":return requestDnaLock(request);
    case "CORE-01-PORT-CORE-REVIEW":return submitCoreReview(request);
    case "CORE-01-PORT-MOTHER-LOCK":return requestMotherLock(request);
    case "CORE-01-PORT-TOPIC-CREATE":return createTopic(request);
    case "CORE-01-PORT-BLUEPRINT-CREATE":return createBlueprint(request);
    case "CORE-01-PORT-BLUEPRINT-VALIDATE":return validateBlueprint(request);
    case "CORE-01-PORT-BLUEPRINT-APPROVE":return approveBlueprint(request);
    case "CORE-01-PORT-CHILD-LOCK":return requestChildLock(request);
    case "CORE-01-PORT-LOCK-DECIDE":return decideLockReview(request);
    case "CORE-01-PORT-CANONICAL-SCRIPT":return canonicalScript(request);
    default:throw new NamedRuntimeError("CORE_GOVERNED_PORT_NOT_REGISTERED");
  }
}
