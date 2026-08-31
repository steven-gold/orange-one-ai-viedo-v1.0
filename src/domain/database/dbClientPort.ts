import type{DbReadPortUid,DbErrorUid}from'./dbRuntimeContract';
export type DbProjectionItem={ref:string;label:string};
export type DbNormalizedProjection={page_state:string;values:Record<string,unknown>;lists:Record<string,DbProjectionItem[]>;tables:Record<string,unknown[]>;gates:Record<string,boolean>;filters:Record<string,DbProjectionItem[]>;graph:unknown;trace:unknown;audit:unknown;source_sync:string|null;};
export type DbReadInput={scope?:unknown;query?:unknown};
export type DbClientResult={ok:true;projection:DbNormalizedProjection;correlation_id:string}|{ok:false;error_uid:DbErrorUid;reason_code:string;correlation_id:string};
export type DbClientBindings={readProjection:()=>Promise<DbClientResult>;read:(port_uid:DbReadPortUid,input:DbReadInput)=>Promise<DbClientResult>;resolveSystemLifecycle:()=>Promise<{ok:true;href:string}|{ok:false;reason_code:string}>};
let binding:DbClientBindings|null=null;
export function configureDbClientRuntime(next:DbClientBindings){binding=next;}
export function isDbClientRuntimeBound(){return binding!==null;}
export async function readDbProjection():Promise<DbClientResult>{if(!binding)return{ok:false,error_uid:'DB-01-ERR-CONTEXT-001',reason_code:'DB_CLIENT_RUNTIME_NOT_BOUND',correlation_id:'unresolved'};try{return await binding.readProjection();}catch{return{ok:false,error_uid:'DB-01-ERR-CONTEXT-001',reason_code:'DB_PROJECTION_READ_FAILED',correlation_id:'unresolved'};}}
export async function invokeDbRead(port_uid:DbReadPortUid,input:DbReadInput):Promise<DbClientResult>{if(!binding)return{ok:false,error_uid:'DB-01-ERR-CONTEXT-001',reason_code:'DB_CLIENT_RUNTIME_NOT_BOUND',correlation_id:'unresolved'};try{return await binding.read(port_uid,input);}catch{return{ok:false,error_uid:'DB-01-ERR-CONTEXT-001',reason_code:'DB_READ_MODEL_QUERY_FAILED',correlation_id:'unresolved'};}}
export async function openDbSystemLifecycle(){if(!binding)return{ok:false as const,reason_code:'DB_CLIENT_RUNTIME_NOT_BOUND'};try{return await binding.resolveSystemLifecycle();}catch{return{ok:false as const,reason_code:'SYSTEM_LIFECYCLE_ROUTE_RESOLUTION_FAILED'};}}
