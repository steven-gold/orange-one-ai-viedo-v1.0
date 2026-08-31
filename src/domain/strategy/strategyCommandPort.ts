import{STRATEGY_PORTS}from'./strategyRuntimeContract';
export type StrategyFormalAction='STR-01-ACT-SEND'|'STR-01-ACT-STOP'|'STR-01-ACT-COMPARE'|'STR-01-ACT-REVIEW'|'STR-01-ACT-ADOPT';
export type StrategyFormalBuildInput={action_uid:StrategyFormalAction;conversation_id:string|null;topic_ref:string|null;message:string;attachment_refs:readonly string[];mode:'SINGLE_AI'|'MULTI_AI';compare_candidate_refs:readonly string[];candidate_ref:string|null;candidate_version_ref:string|null};
export type StrategyRequestBuilder={build:(input:StrategyFormalBuildInput)=>Promise<{path_params?:Record<string,string>;payload?:unknown;query?:Record<string,string>}>|{path_params?:Record<string,string>;payload?:unknown;query?:Record<string,string>}};
let builder:StrategyRequestBuilder|null=null;
export function configureStrategyRequestBuilder(next:StrategyRequestBuilder){builder=next;}
export function isStrategyRequestBuilderBound(){return builder!==null;}
const CONTRACT={
 'STR-01-ACT-SEND':STRATEGY_PORTS.conversation,
 'STR-01-ACT-STOP':STRATEGY_PORTS.stop,
 'STR-01-ACT-COMPARE':STRATEGY_PORTS.compare,
 'STR-01-ACT-REVIEW':STRATEGY_PORTS.review,
 'STR-01-ACT-ADOPT':STRATEGY_PORTS.adopt,
}as const;
function pathOf(template:string,params:Record<string,string>){let out=template;for(const token of template.match(/\{[^}]+\}/g)??[]){const key=token.slice(1,-1),value=params[key];if(!value)return null;out=out.replace(token,encodeURIComponent(value));}return out;}
function errorUid(action:StrategyFormalAction){if(action==='STR-01-ACT-SEND'||action==='STR-01-ACT-STOP')return'STR-01-ERR-CONVERSATION-001';if(action==='STR-01-ACT-COMPARE')return'STR-01-ERR-CANDIDATE-001';if(action==='STR-01-ACT-REVIEW')return'STR-01-ERR-REVIEW-001';return'STR-01-ERR-ADOPT-001';}
export async function buildAndInvokeStrategyAction(input:StrategyFormalBuildInput){
 if(!builder)return{ok:false as const,error_uid:errorUid(input.action_uid),reason_code:'STRATEGY_REQUEST_ADAPTER_NOT_BOUND',correlation_id:'unresolved'};
 let built:Awaited<ReturnType<StrategyRequestBuilder['build']>>;try{built=await builder.build(input);}catch{return{ok:false as const,error_uid:errorUid(input.action_uid),reason_code:'STRATEGY_REQUEST_ADAPTER_FAILED',correlation_id:'unresolved'};}
 const contract=CONTRACT[input.action_uid],path=pathOf(contract.path,built.path_params??{});if(!path)return{ok:false as const,error_uid:errorUid(input.action_uid),reason_code:'REQUIRED_EXACT_PATH_REFERENCE_MISSING',correlation_id:'unresolved'};
 const qs=contract.method==='GET'&&built.query?new URLSearchParams(built.query).toString():'';const url=qs?`${path}?${qs}`:path;
 try{const response=await fetch(url,{method:contract.method,cache:'no-store',headers:contract.method==='POST'?{'content-type':'application/json'}:undefined,body:contract.method==='POST'?JSON.stringify(built.payload??null):undefined}),correlation_id=response.headers.get('x-correlation-id')??'unresolved',value:unknown=await response.json().catch(()=>null);if(!response.ok){const body=typeof value==='object'&&value!==null?value as Record<string,unknown>:null;return{ok:false as const,error_uid:errorUid(input.action_uid),reason_code:typeof body?.reason_code==='string'?body.reason_code:'STRATEGY_REQUEST_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}return{ok:true as const,value,correlation_id};}catch{return{ok:false as const,error_uid:errorUid(input.action_uid),reason_code:'STRATEGY_REQUEST_FAILED',correlation_id:'unresolved'};}
}
