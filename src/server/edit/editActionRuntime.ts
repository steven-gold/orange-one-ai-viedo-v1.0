import type{EditActionRequest,EditActionResult}from"@/domain/edit/editRuntimeContract";
export type EditActionAuthorityBinding={
  resolve:(action_uid:string)=>Promise<{registered:true;effect_type:string}|{registered:false}>;
  authorize:(request:EditActionRequest)=>Promise<{allowed:true}|{allowed:false;reason_code?:string}>;
  execute:(request:EditActionRequest,effect_type:string)=>Promise<unknown>;
  audit:(entry:EditActionRequest&{outcome:"BLOCKED"|"SUCCESS"|"ERROR";reason_code?:string})=>Promise<void>;
};
let binding:EditActionAuthorityBinding|null=null;
export function configureEditActionRuntime(next:EditActionAuthorityBinding){binding=next;}
export async function executeEditAction(request:EditActionRequest):Promise<EditActionResult>{
  const r=binding;if(!r)return{ok:false,error_uid:"EDIT-01-ERR-CONTEXT-001",reason_code:"EDIT_ACTION_AUTHORITY_RUNTIME_NOT_BOUND",correlation_id:request.correlation_id};
  const resolved=await r.resolve(request.action_uid).catch(()=>({registered:false as const}));
  if(!resolved.registered){await r.audit({...request,outcome:"BLOCKED",reason_code:"UNREGISTERED_EDIT_ACTION"}).catch(()=>{});return{ok:false,error_uid:"EDIT-01-ERR-CONTEXT-001",reason_code:"UNREGISTERED_EDIT_ACTION",correlation_id:request.correlation_id};}
  const auth=await r.authorize(request).catch(()=>({allowed:false as const,reason_code:"AUTHORIZATION_EVALUATION_FAILED"}));
  if(!auth.allowed){const reason_code=auth.reason_code??"PERMISSION_OR_GATE_DENIED";await r.audit({...request,outcome:"BLOCKED",reason_code}).catch(()=>{});return{ok:false,error_uid:"EDIT-01-ERR-PERM-001",reason_code,correlation_id:request.correlation_id};}
  try{const value=await r.execute(request,resolved.effect_type);await r.audit({...request,outcome:"SUCCESS"}).catch(()=>{});return{ok:true,value,correlation_id:request.correlation_id};}
  catch{await r.audit({...request,outcome:"ERROR",reason_code:"EDIT_ACTION_EXECUTION_FAILED"}).catch(()=>{});return{ok:false,error_uid:"EDIT-01-ERR-CONTEXT-001",reason_code:"EDIT_ACTION_EXECUTION_FAILED",correlation_id:request.correlation_id};}
}
