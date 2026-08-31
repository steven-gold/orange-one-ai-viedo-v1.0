export type StrategyOwnerNavigationInput={owner_type:string;context_ref:string|null};
export type StrategyOwnerNavigationResolver={resolve:(input:StrategyOwnerNavigationInput)=>Promise<{ok:true;href:string}|{ok:false;reason_code:string}>};
let resolver:StrategyOwnerNavigationResolver|null=null;
export function configureStrategyOwnerNavigationResolver(next:StrategyOwnerNavigationResolver){resolver=next;}
export function isStrategyOwnerNavigationResolverBound(){return resolver!==null;}
export async function resolveStrategyOwnerNavigation(input:StrategyOwnerNavigationInput){if(!resolver)return{ok:false as const,reason_code:'STRATEGY_OWNER_ROUTE_NOT_BOUND'};try{return await resolver.resolve(input);}catch{return{ok:false as const,reason_code:'STRATEGY_OWNER_ROUTE_RESOLUTION_FAILED'};}}
