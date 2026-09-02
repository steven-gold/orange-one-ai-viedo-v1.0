import{isControlledTestMode}from'@/domain/testing/controlledTestData';
export type StrategyOwnerNavigationInput={owner_type:string;context_ref:string|null};
export type StrategyOwnerNavigationResolver={resolve:(input:StrategyOwnerNavigationInput)=>Promise<{ok:true;href:string}|{ok:false;reason_code:string}>};
let resolver:StrategyOwnerNavigationResolver|null=null;
export function configureStrategyOwnerNavigationResolver(next:StrategyOwnerNavigationResolver){resolver=next;}
function controlledHref(input:StrategyOwnerNavigationInput){if(!isControlledTestMode())return null;if(input.owner_type==='ERP')return'/admin/erp';return null;}
export function isStrategyOwnerNavigationResolverBound(){return resolver!==null||isControlledTestMode();}
export async function resolveStrategyOwnerNavigation(input:StrategyOwnerNavigationInput){if(!resolver){const href=controlledHref(input);return href?{ok:true as const,href}:{ok:false as const,reason_code:'STRATEGY_OWNER_ROUTE_NOT_BOUND'};}try{return await resolver.resolve(input);}catch{return{ok:false as const,reason_code:'STRATEGY_OWNER_ROUTE_RESOLUTION_FAILED'};}}
