export type StrategyAdminView='overview'|'intelligence'|'playbook'|'opportunity'|'decision';
export type StrategyAdminProjection={page_state:string|null;values:Readonly<Record<string,string>>;evidence:Readonly<Record<string,string>>;states:Readonly<Record<string,string>>;action_enabled:Readonly<Record<string,boolean>>;selected_resource_id:string|null};
export type StrategyAdminProjectionResolver={resolve:(raw:unknown)=>StrategyAdminProjection|Promise<StrategyAdminProjection>};
let projectionResolver:StrategyAdminProjectionResolver|null=null;
export function configureStrategyAdminProjectionResolver(next:StrategyAdminProjectionResolver){projectionResolver=next;}
export async function readStrategyAdminProjection(signal?:AbortSignal){let response:Response;try{response=await fetch('/v1/ui-projections/admin%3ASTR-01',{method:'GET',cache:'no-store',signal});}catch{return{ok:false as const,reason_code:'STR_ADMIN_PROJECTION_REQUEST_FAILED',correlation_id:'unresolved'}}const correlation_id=response.headers.get('x-correlation-id')??'unresolved';const raw:unknown=await response.json().catch(()=>null);if(!response.ok)return{ok:false as const,reason_code:'STR_ADMIN_PROJECTION_READ_FAILED',correlation_id};if(!projectionResolver)return{ok:false as const,reason_code:'STR_ADMIN_PROJECTION_ADAPTER_NOT_BOUND',correlation_id};try{return{ok:true as const,projection:await projectionResolver.resolve(raw),correlation_id}}catch{return{ok:false as const,reason_code:'STR_ADMIN_PROJECTION_ADAPTER_REJECTED',correlation_id}}}

export type StrategyAdminOperation='refreshProjection'|'searchProjection'|'configureGovernedResource'|'approveGovernedResource'|'exportProjection'|'saveDraft'|'createCandidate'|'compareCandidates'|'adoptAsContextCandidate';
export const STRATEGY_ADMIN_ACTION_OPERATION={
  'ACT-REFRESH':'refreshProjection','ACT-SEARCH':'searchProjection','ACT-CONFIGURE':'configureGovernedResource','ACT-APPROVE':'approveGovernedResource','ACT-EXPORT':'exportProjection','ACT-DRAFT-SAVE':'saveDraft','ACT-CANDIDATE-CREATE':'createCandidate','ACT-CANDIDATE-COMPARE':'compareCandidates','ACT-ADOPT-CONTEXT':'adoptAsContextCandidate'
}as const satisfies Readonly<Record<string,StrategyAdminOperation>>;
export type StrategyAdminMappedAction=keyof typeof STRATEGY_ADMIN_ACTION_OPERATION;
export type StrategyAdminCommandInput={action_id:StrategyAdminMappedAction;operation:StrategyAdminOperation;view:StrategyAdminView;projection:StrategyAdminProjection};
export type StrategyAdminCommandAdapter={invoke:(input:StrategyAdminCommandInput)=>Promise<{ok:true;value:unknown;correlation_id?:string}|{ok:false;reason_code:string;correlation_id?:string}>};
let commandAdapter:StrategyAdminCommandAdapter|null=null;
export function configureStrategyAdminCommandAdapter(next:StrategyAdminCommandAdapter){commandAdapter=next;}
export function isStrategyAdminCommandAdapterBound(){return commandAdapter!==null;}
export async function invokeStrategyAdminAction(action_id:StrategyAdminMappedAction,view:StrategyAdminView,projection:StrategyAdminProjection){const current=commandAdapter;if(!current)return{ok:false as const,reason_code:'STR_ADMIN_REGISTERED_OPERATION_ADAPTER_NOT_BOUND',correlation_id:'unresolved'};return current.invoke({action_id,operation:STRATEGY_ADMIN_ACTION_OPERATION[action_id],view,projection});}
