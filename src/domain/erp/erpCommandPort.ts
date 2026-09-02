import type{ErpNormalizedProjection}from'./erpProjectionPort';
export type ErpCommandInput={action_uid:string;control_uid:string;projection:ErpNormalizedProjection|null;form?:Readonly<Record<string,unknown>>};
export type ErpCommandResult={ok:true;projection:ErpNormalizedProjection;correlation_id:string}|{ok:false;error_uid:string;reason_code:string;correlation_id:string};
export type ErpCommandAdapter={invoke:(input:ErpCommandInput)=>Promise<ErpCommandResult>};
let adapter:ErpCommandAdapter|null=null;
export function configureErpCommandAdapter(next:ErpCommandAdapter){adapter=next;}
export function isErpCommandAdapterBound(){return adapter!==null;}
export async function invokeErpCommand(input:ErpCommandInput):Promise<ErpCommandResult>{if(!adapter)return{ok:false,error_uid:'ERP-01-ERR-UNDEFINED',reason_code:'ERP_COMMAND_RUNTIME_NOT_BOUND',correlation_id:'unresolved'};try{return await adapter.invoke(input)}catch{return{ok:false,error_uid:'ERP-01-ERR-UNDEFINED',reason_code:'ERP_COMMAND_RUNTIME_FAILED',correlation_id:'unresolved'}}}
