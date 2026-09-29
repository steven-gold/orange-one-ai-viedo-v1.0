type MutationFailure={ok:false;reason_code:string;correlation_id:string};
type MutationSuccess<T>={ok:true;value:T;correlation_id:string};
export type SystemMutationResult<T>=MutationSuccess<T>|MutationFailure;

async function post<T>(url:string,body:Record<string,unknown>):Promise<SystemMutationResult<T>>{
  let response:Response;
  try{
    response=await fetch(url,{method:"POST",credentials:"include",cache:"no-store",headers:{"content-type":"application/json",accept:"application/json"},body:JSON.stringify(body)});
  }catch{return{ok:false,reason_code:"SYS01_MUTATION_REQUEST_FAILED",correlation_id:"unresolved"};}
  const raw:unknown=await response.json().catch(()=>null);
  const record=raw&&typeof raw==="object"&&!Array.isArray(raw)?raw as Record<string,unknown>:{};
  const correlation_id=typeof record.correlation_id==="string"?record.correlation_id:response.headers.get("x-correlation-id")??"unresolved";
  if(!response.ok||record.ok!==true)return{ok:false,reason_code:typeof record.reason_code==="string"?record.reason_code:"SYS01_MUTATION_FAILED",correlation_id};
  return{ok:true,value:record.value as T,correlation_id};
}

export function createSystemCandidate(input:{system_change_id:string|null;current_goal:string;source_refs:string[]}){
  return post<{system_change_id:string;candidate_ref:string;status:string;context_fingerprint:string}>(
    "/v1/system/changes/candidates",
    {
      ...(input.system_change_id?{system_change_id:input.system_change_id}:{}),
      current_goal:input.current_goal,
      scope:{page_uid:"admin:SYS-01"},
      candidate_document:{requirement:input.current_goal,source_refs:input.source_refs,authority_scope:"admin:SYS-01"},
    },
  );
}
export function createSystemChangeRequest(input:{system_change_id:string;candidate_ref:string;reason:string}){
  return post<{system_change_id:string;candidate_ref:string;change_request_ref:string;status:string}>(
    `/v1/system/changes/${encodeURIComponent(input.system_change_id)}/requests`,
    {candidate_ref:input.candidate_ref,reason:input.reason,impact_scope:{page_uid:"admin:SYS-01"}},
  );
}
export function runSystemSandbox(input:{system_change_id:string}){
  return post<{system_change_id:string;candidate_ref:string;provider_profile_id:string;sandbox:Record<string,unknown>}>(
    `/v1/system/changes/${encodeURIComponent(input.system_change_id)}/sandbox-tests`,
    {},
  );
}
