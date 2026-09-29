import type{DevNormalizedProjection}from'./devProjectionPort';
export type DevCommandInput={action_uid:string;control_uid:string;projection:DevNormalizedProjection|null};
export type DevCommandResult={ok:true;projection:DevNormalizedProjection;correlation_id:string}|{ok:false;error_uid:string;reason_code:string;correlation_id:string};
export type DevCommandAdapter={invoke:(input:DevCommandInput)=>Promise<DevCommandResult>};
let adapter:DevCommandAdapter|null=null;
export function configureDevCommandAdapter(next:DevCommandAdapter){adapter=next;}
export function isDevCommandAdapterBound(){return adapter!==null;}
export async function invokeDevCommand(input:DevCommandInput):Promise<DevCommandResult>{if(!adapter)return{ok:false,error_uid:'DEV-01-ERR-UNDEFINED',reason_code:'DEV_COMMAND_RUNTIME_NOT_BOUND',correlation_id:'unresolved'};try{return await adapter.invoke(input)}catch{return{ok:false,error_uid:'DEV-01-ERR-UNDEFINED',reason_code:'DEV_COMMAND_RUNTIME_FAILED',correlation_id:'unresolved'}}}
