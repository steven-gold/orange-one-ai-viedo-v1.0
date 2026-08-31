import { INFO_PORTS } from './infoRuntimeContract';
export type InfoCommandAction='INFO-01-ACT-REFRESH'|'INFO-01-ACT-SEARCH'|'INFO-01-ACT-EXPORT'|'INFO-01-ACT-ADOPT-CONTEXT'|'INFO-01-ACT-CANDIDATE-DECIDE';
export type InfoCommandInput={action_uid:InfoCommandAction;path_params?:Record<string,string>;payload:unknown;signal?:AbortSignal};
export type InfoCommandResult={ok:true;value:unknown;correlation_id:string}|{ok:false;error_uid:string;reason_code:string;correlation_id:string};
const ACTION_PORT={
  'INFO-01-ACT-REFRESH':INFO_PORTS.refresh,
  'INFO-01-ACT-SEARCH':INFO_PORTS.search,
  'INFO-01-ACT-EXPORT':INFO_PORTS.export,
  'INFO-01-ACT-ADOPT-CONTEXT':INFO_PORTS.adopt,
  'INFO-01-ACT-CANDIDATE-DECIDE':INFO_PORTS.decide,
}as const;
function pathOf(template:string,params:Record<string,string>){let path=template;for(const token of template.match(/\{[^}]+\}/g)??[]){const key=token.slice(1,-1),value=params[key];if(!value)return null;path=path.replace(token,encodeURIComponent(value));}return path;}
function errorUid(action:InfoCommandAction){if(action==='INFO-01-ACT-SEARCH')return'INFO-01-ERR-SEARCH-001';if(action==='INFO-01-ACT-EXPORT')return'INFO-01-ERR-EXPORT-001';if(action==='INFO-01-ACT-ADOPT-CONTEXT'||action==='INFO-01-ACT-CANDIDATE-DECIDE')return'INFO-01-ERR-CANDIDATE-001';return'INFO-01-ERR-CONTEXT-001';}
export async function invokeInfoCommand(input:InfoCommandInput):Promise<InfoCommandResult>{
  const contract=ACTION_PORT[input.action_uid],path=pathOf(contract.path,input.path_params??{});
  if(!path)return{ok:false,error_uid:errorUid(input.action_uid),reason_code:'REQUIRED_EXACT_PATH_REFERENCE_MISSING',correlation_id:'unresolved'};
  try{const response=await fetch(path,{method:'POST',cache:'no-store',signal:input.signal,headers:{'content-type':'application/json'},body:JSON.stringify(input.payload)}),correlation_id=response.headers.get('x-correlation-id')??'unresolved',value:unknown=await response.json().catch(()=>null);if(!response.ok){const body=typeof value==='object'&&value!==null?value as Record<string,unknown>:null;return{ok:false,error_uid:errorUid(input.action_uid),reason_code:typeof body?.reason_code==='string'?body.reason_code:'INFO_COMMAND_REQUEST_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}return{ok:true,value,correlation_id};}
  catch{return{ok:false,error_uid:errorUid(input.action_uid),reason_code:'INFO_COMMAND_REQUEST_FAILED',correlation_id:'unresolved'};}
}
export type InfoCommandPayloadBuilder={build:(input:{action_uid:InfoCommandAction;candidate_ref:string|null;scope_filter:string|null;projection_version:string|null;authorized_scope:string|null})=>Promise<{payload:unknown;path_params?:Record<string,string>}>|{payload:unknown;path_params?:Record<string,string>}};
let builder:InfoCommandPayloadBuilder|null=null;
export function configureInfoCommandPayloadBuilder(next:InfoCommandPayloadBuilder){builder=next;}
export function isInfoCommandPayloadBuilderBound(){return builder!==null;}
export async function buildAndInvokeInfoCommand(input:{action_uid:InfoCommandAction;candidate_ref:string|null;scope_filter:string|null;projection_version:string|null;authorized_scope:string|null}){if(!builder)return{ok:false as const,error_uid:errorUid(input.action_uid),reason_code:'INFO_COMMAND_PAYLOAD_ADAPTER_NOT_BOUND',correlation_id:'unresolved'};try{const built=await builder.build(input);return invokeInfoCommand({...built,action_uid:input.action_uid});}catch{return{ok:false as const,error_uid:errorUid(input.action_uid),reason_code:'INFO_COMMAND_PAYLOAD_ADAPTER_FAILED',correlation_id:'unresolved'};}}
