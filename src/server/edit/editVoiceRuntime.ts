import type { EditVoiceOperationId } from "@/domain/edit/editRuntimeContract";
export type EditVoiceRequest={operation_id:EditVoiceOperationId;correlation_id:string;path_params:Record<string,string>;payload:unknown};
export type EditVoiceBindings={
  authorize:(request:EditVoiceRequest)=>Promise<{allowed:true}|{allowed:false;reason_code?:string}>;
  execute:(request:EditVoiceRequest)=>Promise<unknown>;
  audit:(entry:EditVoiceRequest&{outcome:"ALLOWED"|"DENIED"|"SUCCESS"|"ERROR";reason_code?:string})=>Promise<void>;
};
let bindings:EditVoiceBindings|null=null;
export function configureEditVoiceRuntime(next:EditVoiceBindings){bindings=next;}
async function audit(r:EditVoiceBindings,e:Parameters<EditVoiceBindings["audit"]>[0]){try{await r.audit(e);}catch{/* runtime stays fail-closed */}}
export async function executeEditVoiceOperation(request:EditVoiceRequest){
  const r=bindings;if(!r)return{ok:false as const,status:503,error_uid:"EDIT-01-ERR-CONTEXT-001",reason_code:"EDIT_VOICE_RUNTIME_NOT_BOUND",correlation_id:request.correlation_id};
  let d:Awaited<ReturnType<EditVoiceBindings["authorize"]>>;
  try{d=await r.authorize(request);}catch{return{ok:false as const,status:403,error_uid:"EDIT-01-ERR-PERM-001",reason_code:"AUTHORIZATION_EVALUATION_FAILED",correlation_id:request.correlation_id};}
  if(!d.allowed){const reason_code=d.reason_code??"PERMISSION_OR_SCOPE_DENIED";await audit(r,{...request,outcome:"DENIED",reason_code});return{ok:false as const,status:403,error_uid:"EDIT-01-ERR-PERM-001",reason_code,correlation_id:request.correlation_id};}
  await audit(r,{...request,outcome:"ALLOWED"});
  try{const value=await r.execute(request);await audit(r,{...request,outcome:"SUCCESS"});return{ok:true as const,value,correlation_id:request.correlation_id};}
  catch{await audit(r,{...request,outcome:"ERROR",reason_code:"EDIT_VOICE_OPERATION_FAILED"});return{ok:false as const,status:503,error_uid:"EDIT-01-ERR-STAGE-001",reason_code:"EDIT_VOICE_OPERATION_FAILED",correlation_id:request.correlation_id};}
}
