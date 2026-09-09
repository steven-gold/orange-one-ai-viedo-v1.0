import { createHash, randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import type { AssetRuntimeRequest } from "@/domain/asset/assetRuntimeContract";
import type { VideoRuntimeRequest } from "@/domain/video/videoRuntimeContract";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { hashSessionToken, IDENTITY_COOKIE_NAME, resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { executeProductionAiApiCommand } from "@/server/aiApi/productionAiApiCommandRuntime";
import { NamedRuntimeError, namedReason } from "@/server/shared/namedRuntimeError";

type Family="ASSET"|"VIDEO";
type Request=AssetRuntimeRequest|VideoRuntimeRequest;
type Sql=NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row=Record<string,unknown>;

function record(v:unknown):Row{return v&&typeof v==="object"&&!Array.isArray(v)?v as Row:{};}
function list(v:unknown):Row[]{return Array.isArray(v)?v.filter((x):x is Row=>Boolean(x)&&typeof x==="object"&&!Array.isArray(x)):[];}
function first(v:unknown):Row|null{return list(v)[0]??null;}
function str(v:unknown):string|null{if(typeof v!=="string")return null;const x=v.trim();return x||null;}
function uuid(v:unknown):string|null{const x=str(v);return x&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x)?x:null;}
function requireUuid(v:unknown,reason:string){const x=uuid(v);if(!x)throw new NamedRuntimeError(reason);return x;}
function json(v:unknown):Row|null{return v&&typeof v==="object"&&!Array.isArray(v)?v as Row:null;}
function reason(f:Family,r:string){return r.startsWith(f+"_")?r:`${f}_${r}`;}
function sha(v:string){return createHash("sha256").update(v).digest("hex");}

async function context():Promise<{sql:Sql;actor_user_id:string;session_token_hash:string}>{
  await ensureProductionNeonRuntime();
  const sql=getProductionNeonSql();
  if(!sql)throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const token=(await cookies()).get(IDENTITY_COOKIE_NAME)?.value?.trim();
  if(!token)throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity=await resolveIdentityFromCookie(token);
  if(!identity.ok)throw new NamedRuntimeError(identity.reason_code);
  return{sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}

async function resolveExecutionContext(f:Family,taskId:string,sql:Sql,session:string){
  const rows=await runRlsActorQuery(sql,session,sql`
    SELECT t.task_id::text,t.department::text,t.status::text AS task_status,
           t.project_id::text,t.topic_id::text,t.production_contract_id::text,t.goal_id::text,
           t.production_goal_id::text,t.topic_production_contract_id::text,
           btrim(t.output_contract_hash::text) AS output_contract_hash,
           btrim(t.input_fingerprint::text) AS input_fingerprint,
           m.task_input_manifest_id::text,btrim(m.manifest_hash::text) AS manifest_hash,m.status::text AS manifest_status,
           sv.department_script_view_id::text,btrim(sv.view_hash::text) AS script_hash,sv.status::text AS script_status,
           cl.blueprint_version_id::text,cl.status::text AS child_lock_status,
           btrim(cl.blueprint_hash::text) AS blueprint_hash
    FROM public.department_tasks t
    JOIN public.task_input_manifests m ON m.task_id=t.task_id
    JOIN public.department_script_views sv ON sv.department_script_view_id=m.department_script_view_id
    JOIN public.child_locks cl ON cl.child_lock_id=t.child_lock_id
    WHERE t.task_id=${taskId}::uuid AND t.department::text=${f}
    LIMIT 1
  `);
  const task=first(rows);
  if(!task)throw new NamedRuntimeError(reason(f,"EXECUTION_CONTEXT_NOT_READY"));
  if(str(task.child_lock_status)!=="CHILD_LOCKED")throw new NamedRuntimeError(reason(f,"CHILD_LOCK_NOT_READY"));
  if(!["READY","APPROVED"].includes(str(task.script_status)??""))throw new NamedRuntimeError(reason(f,"SCRIPT_NOT_READY"));
  if(str(task.manifest_status)!=="READY")throw new NamedRuntimeError(reason(f,"INPUT_MANIFEST_NOT_READY"));
  if(!str(task.input_fingerprint))throw new NamedRuntimeError(reason(f,"INPUT_FINGERPRINT_REQUIRED"));

  const instructionRows=await runRlsActorQuery(sql,session,sql`
    SELECT instruction_package_id::text,provider_neutral_intent,btrim(package_hash::text) AS package_hash
    FROM public.instruction_packages
    WHERE task_id=${taskId}::uuid
      AND task_input_manifest_id=${str(task.task_input_manifest_id)}::uuid
      AND status='APPROVED' AND approved_by IS NOT NULL AND approved_at IS NOT NULL
    ORDER BY approved_at DESC,instruction_package_id
    LIMIT 2
  `);
  const instructions=list(instructionRows);
  if(instructions.length===0)throw new NamedRuntimeError(reason(f,"INSTRUCTION_PACKAGE_NOT_READY"));
  if(instructions.length>1)throw new NamedRuntimeError(reason(f,"INSTRUCTION_PACKAGE_AMBIGUOUS"));
  const instruction=instructions[0]!;
  const intent=json(instruction.provider_neutral_intent);
  const canonical=str(intent?.canonical_instruction_zh_tw);
  const capability=str(intent?.capability_requirement);
  const classification=str(intent?.data_classification);
  const intentType=str(intent?.intent_type);
  if(!canonical)throw new NamedRuntimeError(reason(f,"CANONICAL_INSTRUCTION_ZH_TW_REQUIRED"));
  if(!capability)throw new NamedRuntimeError(reason(f,"CAPABILITY_REQUIREMENT_REQUIRED"));
  if(!classification)throw new NamedRuntimeError(reason(f,"DATA_CLASSIFICATION_REQUIRED"));
  if(!intentType)throw new NamedRuntimeError(reason(f,"ROUTE_INTENT_TYPE_REQUIRED"));

  const routeRows=await runRlsActorQuery(sql,session,sql`
    SELECT rp.route_policy_id::text,btrim(rp.policy_hash::text) AS policy_hash,rp.fallback_policy,
           pc.provider_key,pc.model_key,pc.status::text AS capability_status
    FROM public.route_policies rp
    JOIN public.provider_capabilities pc ON pc.provider_capability_id=rp.provider_capability_id
    WHERE rp.status='APPROVED' AND pc.status='APPROVED'
      AND rp.department::text=${f}
      AND rp.intent_type=${intentType}
      AND rp.classification::text=${classification}
    ORDER BY rp.route_policy_id
    LIMIT 2
  `);
  const routes=list(routeRows);
  if(routes.length===0)throw new NamedRuntimeError(reason(f,"ROUTE_POLICY_NOT_READY"));
  if(routes.length>1)throw new NamedRuntimeError(reason(f,"ROUTE_POLICY_AMBIGUOUS"));
  const route=routes[0]!;
  const groupId=str(json(route.fallback_policy)?.candidate_group_id);
  if(!groupId)throw new NamedRuntimeError(reason(f,"ROUTE_CANDIDATE_GROUP_BINDING_REQUIRED"));
  return{task,instruction,route,canonical,capability,classification,groupId};
}

async function runExecution(f:Family,request:Request,retry:boolean){
  const taskId=requireUuid(request.path_params?.taskId,reason(f,"TASK_ID_REQUIRED"));
  const payload=record(request.payload);
  const correctionMode=str(payload.mode)==="CORRECTION"||Boolean(uuid(payload.approved_candidate_ref));
  const approvedCandidateId=correctionMode?requireUuid(payload.approved_candidate_ref,reason(f,"APPROVED_CORRECTION_CANDIDATE_REQUIRED")):null;
  const {sql,session_token_hash}=await context();
  const resolved=await resolveExecutionContext(f,taskId,sql,session_token_hash);
  const taskStatus=str(resolved.task.task_status);
  const canonicalFingerprint=str(resolved.task.input_fingerprint);
  const supplied=str(payload.input_fingerprint)??str(payload.expected_input_fingerprint);
  if(supplied&&supplied!==canonicalFingerprint)throw new NamedRuntimeError(reason(f,"INPUT_FINGERPRINT_MISMATCH"));

  let correctionCandidate:Row|null=null;
  let canonicalInstruction=resolved.canonical;
  let instructionPackageId=str(resolved.instruction.instruction_package_id);
  let instructionPackageHash=str(resolved.instruction.package_hash);
  let correctionSourceOutputId:string|null=null;
  let correctionRunId:string|null=null;

  if(correctionMode){
    if(retry)throw new NamedRuntimeError(reason(f,"CORRECTION_RETRY_MUST_USE_APPROVED_CANDIDATE_EXECUTE"));
    if(!["BLOCKED","CANDIDATE_OUTPUT","SCORE_PENDING","HANDOFF_READY"].includes(taskStatus??"")){
      throw new NamedRuntimeError(reason(f,"CORRECTION_STATE_NOT_ELIGIBLE"));
    }
    correctionCandidate=first(await runRlsActorQuery(sql,session_token_hash,sql`
      SELECT c.correction_script_version_id::text,c.correction_request_id::text,c.correction_instruction,c.status,c.content_hash::text,
             c.source_instruction_package_id::text,c.source_blueprint_version_id::text,c.decided_by::text,c.decision_reason,c.decided_at::text,
             cr.source_output_version_id::text,cr.original_owner_task_id::text,cr.revalidation_requirements,
             ip.package_hash::text AS source_package_hash
      FROM public.correction_script_versions c
      JOIN public.correction_requests cr ON cr.correction_request_id=c.correction_request_id
      JOIN public.instruction_packages ip ON ip.instruction_package_id=c.source_instruction_package_id AND ip.task_id=cr.original_owner_task_id AND ip.status='APPROVED'
      WHERE c.correction_script_version_id=${approvedCandidateId}::uuid
        AND cr.original_owner_task_id=${taskId}::uuid
        AND c.target_department=${f}
      LIMIT 1
    `));
    if(!correctionCandidate)throw new NamedRuntimeError(reason(f,"APPROVED_CORRECTION_CANDIDATE_NOT_FOUND"));
    if(str(correctionCandidate.status)!=="APPROVED"||!uuid(correctionCandidate.decided_by)||!str(correctionCandidate.decision_reason)||!str(correctionCandidate.decided_at)){
      throw new NamedRuntimeError(reason(f,"HUMAN_APPROVED_CORRECTION_REQUIRED"));
    }
    const revalidation=json(correctionCandidate.revalidation_requirements);
    if(str(revalidation?.input_fingerprint)!==canonicalFingerprint)throw new NamedRuntimeError(reason(f,"CORRECTION_INPUT_FINGERPRINT_STALE"));
    if(str(correctionCandidate.source_instruction_package_id)!==instructionPackageId||str(correctionCandidate.source_package_hash)!==instructionPackageHash){
      throw new NamedRuntimeError(reason(f,"CORRECTION_INSTRUCTION_LINEAGE_STALE"));
    }
    if(str(correctionCandidate.source_blueprint_version_id)!==str(resolved.task.blueprint_version_id)){
      throw new NamedRuntimeError(reason(f,"CORRECTION_BLUEPRINT_LINEAGE_STALE"));
    }
    const instruction=json(correctionCandidate.correction_instruction);
    canonicalInstruction=str(instruction?.generated_instruction)??"";
    if(!canonicalInstruction)throw new NamedRuntimeError(reason(f,"APPROVED_CORRECTION_INSTRUCTION_REQUIRED"));
    correctionSourceOutputId=requireUuid(correctionCandidate.source_output_version_id,reason(f,"CORRECTION_SOURCE_OUTPUT_REQUIRED"));
    const locked=first(await runRlsActorQuery(sql,session_token_hash,sql`
      SELECT production_output_version_lock_id::text FROM public.production_output_version_locks
      WHERE output_version_id=${correctionSourceOutputId}::uuid AND status='LOCKED' LIMIT 1
    `));
    if(locked)throw new NamedRuntimeError(reason(f,"LOCKED_SOURCE_OUTPUT_CORRECTION_FORBIDDEN"));
  }else if(retry){
    if(taskStatus!=="FAILED"&&taskStatus!=="BLOCKED")throw new NamedRuntimeError(reason(f,"RETRY_STATE_NOT_ELIGIBLE"));
  }else if(taskStatus!=="READY"){
    throw new NamedRuntimeError(reason(f,"EXECUTE_STATE_NOT_READY"));
  }

  const executionKind=correctionMode?"CORRECTION":retry?"RETRY":"EXECUTE";
  const correctionHash=str(correctionCandidate?.content_hash);
  const idempotency=sha([f,taskId,executionKind,canonicalFingerprint,instructionPackageId,instructionPackageHash,str(resolved.route.route_policy_id),str(resolved.route.policy_hash),approvedCandidateId,correctionHash].join("|"));
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT provider_job_id::text,status::text,external_job_ref
    FROM public.provider_jobs
    WHERE btrim(idempotency_key::text)=${idempotency}
    LIMIT 1
  `));
  if(existing)throw new NamedRuntimeError(reason(f,`PROVIDER_JOB_${str(existing.status)??"EXISTS"}`));

  const created=first(await runRlsActorQuery(sql,session_token_hash,sql`
    WITH moved AS(
      UPDATE public.department_tasks
      SET status='ROUTING',started_at=COALESCE(started_at,now())
      WHERE task_id=${taskId}::uuid AND status=${taskStatus}
      RETURNING *
    )
    INSERT INTO public.provider_jobs(
      task_id,instruction_package_id,route_policy_id,idempotency_key,status,
      production_contract_id,goal_id,output_contract_hash,blueprint_version_id,topic_id,project_id
    )
    SELECT task_id,${instructionPackageId}::uuid,${str(resolved.route.route_policy_id)}::uuid,
           ${idempotency}::char(64),'ROUTING',production_contract_id,COALESCE(goal_id,production_goal_id),
           output_contract_hash,${str(resolved.task.blueprint_version_id)}::uuid,topic_id,project_id
    FROM moved
    RETURNING provider_job_id::text
  `));
  const jobId=requireUuid(created?.provider_job_id,reason(f,"PROVIDER_JOB_CREATE_FAILED"));

  if(correctionMode&&approvedCandidateId&&correctionSourceOutputId){
    correctionRunId=randomUUID();
    try{
      await sql`
        INSERT INTO acpos_runtime.correction_runs(
          id,correction_script_id,task_id,provider_candidate_group_id,source_output_version_id,
          execution_mode,status,evidence_json
        ) VALUES(
          ${correctionRunId},${approvedCandidateId},${taskId},${resolved.groupId},${correctionSourceOutputId},
          'CORRECTION','ROUTING',
          ${JSON.stringify({approved_candidate_ref:approvedCandidateId,candidate_content_hash:correctionHash,input_fingerprint:canonicalFingerprint,provider_job_id:jobId})}::jsonb
        )
      `;
    }catch{
      await runRlsActorQuery(sql,session_token_hash,sql`
        UPDATE public.provider_jobs SET status='BLOCKED',completed_at=now() WHERE provider_job_id=${jobId}::uuid RETURNING provider_job_id
      `).catch(()=>[]);
      await runRlsActorQuery(sql,session_token_hash,sql`
        UPDATE public.department_tasks SET status='BLOCKED' WHERE task_id=${taskId}::uuid AND status='ROUTING' RETURNING task_id
      `).catch(()=>[]);
      throw new NamedRuntimeError(reason(f,"CORRECTION_RUNTIME_TRACE_CREATE_FAILED"));
    }
  }

  try{
    const routed=record(await executeProductionAiApiCommand({
      operation_id:"executeProviderRoute",
      correlation_id:request.correlation_id,
      path_params:{},
      payload:{
        candidate_group_id:resolved.groupId,
        required_capability:resolved.capability,
        data_classification:resolved.classification,
        use_case:`ACPOS_${f}_PRODUCTION`,
        canonical_instruction:canonicalInstruction,
        canonical_instruction_id:correctionMode?`CORRECTION:${approvedCandidateId}`:`${f}:${taskId}:${instructionPackageId}`,
        scoped_context:{
          task_id:taskId,
          task_input_manifest_id:str(resolved.task.task_input_manifest_id),
          manifest_hash:str(resolved.task.manifest_hash),
          script_view_id:str(resolved.task.department_script_view_id),
          script_hash:str(resolved.task.script_hash),
          input_fingerprint:canonicalFingerprint,
          route_policy_id:str(resolved.route.route_policy_id),
          route_policy_hash:str(resolved.route.policy_hash),
          execution_mode:executionKind,
          approved_correction_candidate_ref:approvedCandidateId,
          correction_source_output_version_id:correctionSourceOutputId,
        }
      }
    }));
    const routeDecisionId=requireUuid(routed.route_decision_id,reason(f,"ROUTE_DECISION_ID_REQUIRED"));
    if(str(routed.status)!=="SUCCESS"||routed.external_request_sent!==true){
      throw new NamedRuntimeError(reason(f,`PROVIDER_ROUTE_${str(routed.status)??"BLOCKED"}`));
    }
    const decision=first(await sql`
      SELECT provider_id,model_id,payload
      FROM acpos_runtime.provider_route_decisions
      WHERE id=${routeDecisionId}
      LIMIT 1
    `);
    const decisionPayload=json(decision?.payload);
    const normalized=str(decisionPayload?.normalized_result);
    const resultHash=str(decisionPayload?.result_hash);
    if(!normalized||!resultHash)throw new NamedRuntimeError(reason(f,"PROVIDER_RESULT_NOT_MATERIALIZED"));
    if(!/^(https?|s3|gs):\/\//i.test(normalized))throw new NamedRuntimeError(reason(f,"PROVIDER_RESULT_URI_REQUIRED"));

    const output=first(await runRlsActorQuery(sql,session_token_hash,sql`
      WITH output_row AS(
        INSERT INTO public.task_outputs(
          task_id,provider_job_id,production_goal_id,output_contract_hash,output_uri,artifact_checksum,provenance,status,
          production_contract_id,goal_id,blueprint_version_id,topic_id,project_id
        )
        SELECT t.task_id,${jobId}::uuid,t.production_goal_id,t.output_contract_hash,${normalized},${resultHash}::char(64),
          jsonb_build_object(
            'source','ACPOS_DEPARTMENT_RUNTIME','family',${f},'external_request_sent',true,
            'instruction_package_id',${instructionPackageId},
            'route_policy_id',${str(resolved.route.route_policy_id)},'route_decision_id',${routeDecisionId},
            'provider_id',${str(decision?.provider_id)},'model_id',${str(decision?.model_id)},
            'input_fingerprint',btrim(t.input_fingerprint::text),
            'execution_mode',${executionKind},
            'approved_correction_candidate_ref',${approvedCandidateId},
            'correction_source_output_version_id',${correctionSourceOutputId}
          ),
          'CANDIDATE',t.production_contract_id,COALESCE(t.goal_id,t.production_goal_id),
          ${str(resolved.task.blueprint_version_id)}::uuid,t.topic_id,t.project_id
        FROM public.department_tasks t
        WHERE t.task_id=${taskId}::uuid AND t.status='ROUTING'
        ON CONFLICT(task_id,artifact_checksum) DO NOTHING
        RETURNING *
      ),
      resolved_output AS(
        SELECT * FROM output_row
        UNION ALL
        SELECT o.* FROM public.task_outputs o
        WHERE o.task_id=${taskId}::uuid AND btrim(o.artifact_checksum::text)=${resultHash}
          AND NOT EXISTS(SELECT 1 FROM output_row)
        LIMIT 1
      ),
      job_done AS(
        UPDATE public.provider_jobs SET status='CANDIDATE_OUTPUT',external_job_ref=${routeDecisionId},completed_at=now()
        WHERE provider_job_id=${jobId}::uuid RETURNING provider_job_id
      ),
      task_done AS(
        UPDATE public.department_tasks SET status='CANDIDATE_OUTPUT'
        WHERE task_id=${taskId}::uuid AND EXISTS(SELECT 1 FROM resolved_output) AND EXISTS(SELECT 1 FROM job_done)
        RETURNING task_id
      )
      SELECT output_version_id::text,output_uri,btrim(artifact_checksum::text) AS artifact_checksum
      FROM resolved_output WHERE EXISTS(SELECT 1 FROM task_done)
    `));
    if(!output)throw new NamedRuntimeError(reason(f,"CANDIDATE_OUTPUT_PERSIST_FAILED"));

    if(correctionMode&&correctionRunId&&approvedCandidateId&&correctionCandidate){
      await sql`
        UPDATE acpos_runtime.correction_runs
        SET new_output_version_id=${str(output.output_version_id)},route_decision_id=${routeDecisionId},
            provider_id=${str(decision?.provider_id)},model_id=${str(decision?.model_id)},
            status='COMPLETED',evidence_json=evidence_json||${JSON.stringify({external_request_sent:true,result_hash:resultHash,provider_job_id:jobId})}::jsonb,
            updated_at=now(),completed_at=now()
        WHERE id=${correctionRunId}
      `;
      await runRlsActorQuery(sql,session_token_hash,sql`
        UPDATE public.correction_requests
        SET status='RECHECK'
        WHERE correction_request_id=${str(correctionCandidate.correction_request_id)}::uuid
          AND status='CORRECTION_REQUIRED'
        RETURNING correction_request_id
      `);
      await sql`
        UPDATE acpos_runtime.correction_requests_runtime
        SET status='RECHECK',updated_at=now()
        WHERE id=${str(correctionCandidate.correction_request_id)}
      `;
    }

    return{...output,provider_job_id:jobId,route_decision_id:routeDecisionId,external_request_sent:true,execution_mode:executionKind,correction_run_id:correctionRunId};
  }catch(error){
    const code=namedReason(error,reason(f,"PROVIDER_ROUTE_FAILED"));
    if(correctionRunId){
      await sql`UPDATE acpos_runtime.correction_runs SET status='BLOCKED',evidence_json=evidence_json||${JSON.stringify({reason_code:code})}::jsonb,updated_at=now(),completed_at=now() WHERE id=${correctionRunId}`.catch(()=>[]);
    }
    await runRlsActorQuery(sql,session_token_hash,sql`
      WITH j AS(
        UPDATE public.provider_jobs SET status='BLOCKED',completed_at=now()
        WHERE provider_job_id=${jobId}::uuid RETURNING provider_job_id
      )
      UPDATE public.department_tasks SET status='BLOCKED'
      WHERE task_id=${taskId}::uuid AND EXISTS(SELECT 1 FROM j)
      RETURNING task_id::text
    `).catch(()=>[]);
    throw new NamedRuntimeError(code);
  }
}

async function score(f:Family,request:Request){
  const p=record(request.payload);
  const taskId=requireUuid(p.task_id??p.task_ref??request.path_params?.taskId,reason(f,"SCORE_TASK_ID_REQUIRED"));
  const outputId=requireUuid(p.output_version_id??p.target_output_version_id,reason(f,"SCORE_OUTPUT_ID_REQUIRED"));
  const criteriaId=requireUuid(p.criteria_version_id??p.criteria_version_ref,reason(f,"CRITERIA_VERSION_ID_REQUIRED"));
  const dimensions=json(p.dimensions),evidence=p.evidence_refs,total=Number(p.total_score),gate=str(p.gate_status);
  if(!dimensions||!Array.isArray(evidence)||!Number.isFinite(total)||!["PASS","FAIL","BLOCKED"].includes(gate??"")){
    throw new NamedRuntimeError(reason(f,"EVALUATION_RESULT_REQUIRED"));
  }
  if(f==="VIDEO"&&gate==="PASS"&&total<95)throw new NamedRuntimeError("VIDEO_SCORE_BELOW_CONFIRM_THRESHOLD");
  const {sql,actor_user_id,session_token_hash}=await context();
  const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    WITH eligible AS(
      SELECT t.*,o.output_version_id,q.criteria_version_id
      FROM public.department_tasks t
      JOIN public.task_outputs o ON o.task_id=t.task_id AND o.output_version_id=${outputId}::uuid AND o.status='CANDIDATE'
      JOIN public.quality_criteria_versions q ON q.criteria_version_id=${criteriaId}::uuid
        AND q.status='APPROVED' AND (q.department::text=${f} OR q.department IS NULL)
      WHERE t.task_id=${taskId}::uuid AND t.department::text=${f} AND t.status='CANDIDATE_OUTPUT'
    ),
    inserted AS(
      INSERT INTO public.scorecards(
        output_version_id,criteria_version_id,task_id,production_goal_id,output_contract_hash,
        dimensions,evidence_refs,total_score,gate_status,scored_by,
        production_contract_id,goal_id,topic_id,project_id
      )
      SELECT output_version_id,criteria_version_id,task_id,production_goal_id,output_contract_hash,
        ${JSON.stringify(dimensions)}::jsonb,${JSON.stringify(evidence)}::jsonb,${total},${gate},${actor_user_id}::uuid,
        production_contract_id,COALESCE(goal_id,production_goal_id),topic_id,project_id
      FROM eligible
      RETURNING scorecard_id,task_id
    ),
    moved AS(
      UPDATE public.department_tasks
      SET status=CASE WHEN ${gate}='PASS' THEN 'SCORE_PENDING'::acpos_status ELSE 'BLOCKED'::acpos_status END
      WHERE task_id=${taskId}::uuid AND EXISTS(SELECT 1 FROM inserted)
      RETURNING status
    )
    SELECT scorecard_id::text,(SELECT status::text FROM moved LIMIT 1) AS task_status FROM inserted
  `));
  if(!row)throw new NamedRuntimeError(reason(f,"SCORECARD_CONTEXT_CONFLICT"));
  return row;
}

async function decide(f:Family,request:Request){
  const taskId=requireUuid(request.path_params?.taskId,reason(f,"TASK_ID_REQUIRED"));
  const outputId=requireUuid(request.path_params?.outputVersionId,reason(f,"OUTPUT_VERSION_ID_REQUIRED"));
  if(str(record(request.payload).decision)!=="CONFIRM")throw new NamedRuntimeError(reason(f,"CONFIRM_DECISION_REQUIRED"));
  const {sql,session_token_hash}=await context();
  const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    WITH pass_score AS(
      SELECT s.scorecard_id,s.total_score
      FROM public.scorecards s JOIN public.department_tasks t ON t.task_id=s.task_id
      WHERE s.task_id=${taskId}::uuid AND s.output_version_id=${outputId}::uuid
        AND s.gate_status='PASS' AND t.department::text=${f} AND t.status='SCORE_PENDING'
        AND (${f}<>'VIDEO' OR s.total_score>=95)
      ORDER BY s.created_at DESC LIMIT 1
    ),
    output_done AS(
      UPDATE public.task_outputs SET status='ACCEPTED',immutable_at=COALESCE(immutable_at,now())
      WHERE output_version_id=${outputId}::uuid AND task_id=${taskId}::uuid AND status='CANDIDATE'
        AND EXISTS(SELECT 1 FROM pass_score)
      RETURNING output_version_id
    ),
    task_done AS(
      UPDATE public.department_tasks SET status='HANDOFF_READY'
      WHERE task_id=${taskId}::uuid AND department::text=${f} AND status='SCORE_PENDING'
        AND EXISTS(SELECT 1 FROM output_done)
      RETURNING task_id
    )
    SELECT output_version_id::text,(SELECT scorecard_id::text FROM pass_score LIMIT 1) AS scorecard_id
    FROM output_done WHERE EXISTS(SELECT 1 FROM task_done)
  `));
  if(!row)throw new NamedRuntimeError(reason(f,"CONFIRM_GATE_NOT_SATISFIED"));
  return{...row,decision:"ACCEPTED",task_status:"HANDOFF_READY"};
}

async function finding(f:Family,request:Request){
  const p=record(request.payload);
  const outputId=requireUuid(p.output_version_id??p.target_output_version_id,reason(f,"FINDING_OUTPUT_ID_REQUIRED"));
  const severity=str(p.severity),category=str(p.category),scope=json(p.affected_scope);
  const evidence=json(p.evidence)??(Array.isArray(p.evidence_refs)?{refs:p.evidence_refs}:null);
  if(!severity||!category||!scope||!evidence)throw new NamedRuntimeError(reason(f,"EXACT_FINDING_PAYLOAD_REQUIRED"));
  const scorecardId=uuid(p.scorecard_id??p.scorecard_ref);
  const {sql,actor_user_id,session_token_hash}=await context();
  const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.findings(output_version_id,scorecard_id,severity,category,affected_scope,evidence,status,created_by)
    SELECT o.output_version_id,${scorecardId}::uuid,${severity},${category},
           ${JSON.stringify(scope)}::jsonb,${JSON.stringify(evidence)}::jsonb,'FINDING_OPEN',${actor_user_id}::uuid
    FROM public.task_outputs o JOIN public.department_tasks t ON t.task_id=o.task_id
    WHERE o.output_version_id=${outputId}::uuid AND t.department::text=${f}
    RETURNING finding_id::text,status::text
  `));
  if(!row)throw new NamedRuntimeError(reason(f,"FINDING_CONTEXT_CONFLICT"));
  return row;
}

async function correction(f:Family,request:Request){
  const p=record(request.payload);
  const findingId=requireUuid(p.finding_id??p.finding_ref,reason(f,"CORRECTION_FINDING_ID_REQUIRED"));
  const outputId=requireUuid(p.source_output_version_id??p.output_version_id,reason(f,"CORRECTION_OUTPUT_ID_REQUIRED"));
  const instructionId=requireUuid(p.source_instruction_package_id??p.instruction_package_id,reason(f,"CORRECTION_INSTRUCTION_ID_REQUIRED"));
  const taskId=requireUuid(p.original_owner_task_id??p.task_id??p.task_ref,reason(f,"CORRECTION_OWNER_TASK_ID_REQUIRED"));
  const scope=json(p.affected_scope),revalidation=json(p.revalidation_requirements);
  if(!scope||!revalidation)throw new NamedRuntimeError(reason(f,"CORRECTION_CONTEXT_REQUIRED"));
  const scorecardId=uuid(p.source_scorecard_id??p.scorecard_ref);
  const {sql,session_token_hash}=await context();
  const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.correction_requests(
      finding_id,source_output_version_id,source_instruction_package_id,source_scorecard_id,
      original_owner_task_id,affected_scope,revalidation_requirements,status
    )
    SELECT fnd.finding_id,o.output_version_id,ip.instruction_package_id,${scorecardId}::uuid,
           t.task_id,${JSON.stringify(scope)}::jsonb,${JSON.stringify(revalidation)}::jsonb,'CORRECTION_REQUIRED'
    FROM public.findings fnd
    JOIN public.task_outputs o ON o.output_version_id=fnd.output_version_id
    JOIN public.department_tasks t ON t.task_id=o.task_id
    JOIN public.instruction_packages ip ON ip.instruction_package_id=${instructionId}::uuid AND ip.task_id=t.task_id AND ip.status='APPROVED'
    WHERE fnd.finding_id=${findingId}::uuid AND o.output_version_id=${outputId}::uuid
      AND t.task_id=${taskId}::uuid AND t.department::text=${f}
    RETURNING correction_request_id::text,status::text
  `));
  if(!row)throw new NamedRuntimeError(reason(f,"CORRECTION_CONTEXT_CONFLICT"));
  return row;
}

async function handoff(f:Family,request:Request){
  const p=record(request.payload);
  const sourceTaskId=requireUuid(p.source_task_id??p.task_id??p.task_ref??request.path_params?.taskId,reason(f,"HANDOFF_SOURCE_TASK_ID_REQUIRED"));
  const targetTaskId=requireUuid(p.target_task_id,reason(f,"HANDOFF_TARGET_TASK_ID_REQUIRED"));
  const outputId=requireUuid(p.source_output_version_id??p.output_version_id??p.video_version_id,reason(f,"HANDOFF_OUTPUT_ID_REQUIRED"));
  const scorecardId=requireUuid(p.scorecard_id??p.scorecard_ref,reason(f,"HANDOFF_SCORECARD_ID_REQUIRED"));
  const targetDepartment=f==="ASSET"?"VIDEO":"EDITING";
  const rightsProfileId=uuid(p.rights_profile_id);
  const {sql,session_token_hash}=await context();
  const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    WITH eligible AS(
      SELECT s.*,o.output_version_id,sc.scorecard_id,t.task_id AS target_task_id
      FROM public.department_tasks s
      JOIN public.task_outputs o ON o.task_id=s.task_id AND o.output_version_id=${outputId}::uuid AND o.status='ACCEPTED'
      JOIN public.scorecards sc ON sc.scorecard_id=${scorecardId}::uuid AND sc.task_id=s.task_id AND sc.output_version_id=o.output_version_id AND sc.gate_status='PASS'
      JOIN public.department_tasks t ON t.task_id=${targetTaskId}::uuid AND t.department::text=${targetDepartment} AND t.status='WAITING_DEPENDENCY'
      WHERE s.task_id=${sourceTaskId}::uuid AND s.department::text=${f} AND s.status='HANDOFF_READY'
    ),
    inserted AS(
      INSERT INTO public.handoffs(
        source_task_id,target_task_id,source_output_version_id,scorecard_id,
        topic_production_contract_id,production_goal_id,output_contract_hash,rights_profile_id,status,
        production_contract_id,goal_id,topic_id,project_id
      )
      SELECT task_id,target_task_id,output_version_id,scorecard_id,topic_production_contract_id,production_goal_id,
             output_contract_hash,${rightsProfileId}::uuid,'HANDOFF_READY',production_contract_id,COALESCE(goal_id,production_goal_id),topic_id,project_id
      FROM eligible
      ON CONFLICT(source_task_id,target_task_id,source_output_version_id) DO NOTHING
      RETURNING *
    ),
    resolved AS(
      SELECT * FROM inserted
      UNION ALL
      SELECT h.* FROM public.handoffs h
      WHERE h.source_task_id=${sourceTaskId}::uuid AND h.target_task_id=${targetTaskId}::uuid AND h.source_output_version_id=${outputId}::uuid
        AND NOT EXISTS(SELECT 1 FROM inserted)
      LIMIT 1
    ),
    source_done AS(
      UPDATE public.department_tasks SET status='HANDED_OFF'
      WHERE task_id=${sourceTaskId}::uuid AND EXISTS(SELECT 1 FROM resolved)
      RETURNING task_id
    ),
    target_ready AS(
      UPDATE public.department_tasks SET status='READY'
      WHERE task_id=${targetTaskId}::uuid AND EXISTS(SELECT 1 FROM resolved) AND EXISTS(SELECT 1 FROM source_done)
      RETURNING task_id
    )
    SELECT handoff_id::text,status::text,EXISTS(SELECT 1 FROM target_ready) AS target_ready FROM resolved
  `));
  if(!row||row.target_ready!==true)throw new NamedRuntimeError(reason(f,"HANDOFF_GATE_NOT_SATISFIED"));
  return row;
}

export async function executeProductionDepartmentPort(f:Family,request:Request):Promise<unknown>{
  switch(request.port_uid){
    case "ASSET-01-PORT-EXECUTE":case "VIDEO-01-PORT-EXECUTE":return runExecution(f,request,false);
    case "ASSET-01-PORT-RETRY":case "VIDEO-01-PORT-RETRY":return runExecution(f,request,true);
    case "ASSET-01-PORT-SCORECARD":case "VIDEO-01-PORT-SCORECARD":return score(f,request);
    case "ASSET-01-PORT-DECISION":case "VIDEO-01-PORT-DECISION":return decide(f,request);
    case "ASSET-01-PORT-FINDING":case "VIDEO-01-PORT-FINDING":return finding(f,request);
    case "ASSET-01-PORT-CORRECTION":case "VIDEO-01-PORT-CORRECTION":return correction(f,request);
    case "ASSET-01-PORT-OUT-VIDEO":case "VIDEO-01-PORT-OUT-EDIT":return handoff(f,request);
    default:throw new NamedRuntimeError(reason(f,"PORT_RUNTIME_NOT_MATERIALIZED"));
  }
}

export async function auditProductionDepartmentPort(f:Family,entry:Request&{outcome:"ALLOWED"|"DENIED"|"SUCCESS"|"ERROR";reason_code?:string}){
  try{
    const {sql,actor_user_id}=await context();
    const correlation=uuid(entry.correlation_id)??randomUUID();
    const taskId=uuid(entry.path_params?.taskId)??uuid(record(entry.payload).task_id)??uuid(record(entry.payload).task_ref);
    const project=taskId?first(await sql`SELECT p.workspace_id::text FROM public.department_tasks t JOIN public.projects p ON p.project_id=t.project_id WHERE t.task_id=${taskId}::uuid LIMIT 1`):null;
    const entityId=taskId??correlation;
    await sql`
      INSERT INTO public.audit_events(action,entity_type,entity_id,actor_id,actor_type,workspace_id,reason,correlation_id,payload_hash)
      VALUES(${`${f}:${entry.port_uid}:${entry.outcome}`},${f},${entityId}::uuid,${actor_user_id}::uuid,'USER',
             ${uuid(project?.workspace_id)}::uuid,${entry.reason_code??entry.outcome},${correlation}::uuid,
             ${sha(JSON.stringify({port_uid:entry.port_uid,action_uid:entry.action_uid,outcome:entry.outcome,reason_code:entry.reason_code??null}))}::char(64))
    `;
  }catch{}
}
