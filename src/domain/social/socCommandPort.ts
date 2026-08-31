import type{SocNormalizedProjection}from'./socProjectionPort';
export type SocCommandInput={action_uid:string;control_uid:string;projection:SocNormalizedProjection|null};
export type SocCommandResult={ok:true;projection:SocNormalizedProjection;correlation_id:string}|{ok:false;error_uid:string;reason_code:string;correlation_id:string};
export type SocCommandAdapter={invoke:(input:SocCommandInput)=>Promise<SocCommandResult>};
let adapter:SocCommandAdapter|null=null;
export function configureSocCommandAdapter(next:SocCommandAdapter){adapter=next;}
export function isSocCommandAdapterBound(){return adapter!==null;}
export async function invokeSocCommand(input:SocCommandInput):Promise<SocCommandResult>{if(!adapter)return{ok:false,error_uid:'SOC-01-ERR-UNDEFINED',reason_code:'SOC_COMMAND_RUNTIME_NOT_BOUND',correlation_id:'unresolved'};try{return await adapter.invoke(input)}catch{return{ok:false,error_uid:'SOC-01-ERR-UNDEFINED',reason_code:'SOC_COMMAND_RUNTIME_FAILED',correlation_id:'unresolved'}}}
