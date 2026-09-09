import { createHash } from "node:crypto";
import { cookies } from "next/headers";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { configureCoreRuntime, type CoreRuntimeBindings } from "@/server/core/coreRuntime";
import type { CoreRuntimeRequest } from "@/domain/core/coreRuntimeContract";
import { configureDbReadModelRuntime, type DbReadRequest } from "@/server/database/dbReadModelRuntime";
import { configureIamRuntime, type IamRuntimeRequest } from "@/server/iam/iamRuntime";
import { executeProductionIamCommand } from "@/server/iam/productionIamCommandRuntime";
import { configureDevCommandRuntime, type DevRuntimeRequest } from "@/server/dev/devCommandRuntime";
import { executeProductionDevCommand } from "@/server/dev/productionDevCommandRuntime";
import { configureDepartmentOperationRuntime } from "@/server/shared/departmentOperationRuntime";
import { configureInfoCommandRuntime, type InfoRequest } from "@/server/info/infoCommandRuntime";
import { executeProductionInfoCommand, decideProductionInfoCandidate } from "@/server/info/productionInfoRuntime";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery, runRlsActorTransaction } from "@/server/database/rlsRuntime";
import { hashSessionToken, IDENTITY_COOKIE_NAME, resolveIdentityFromCookie, type IdentityActor } from "@/server/identity/identityRuntime";
import { CURRENT_PAGE_RESOURCE_KEYS } from "@/server/shared/pageCatalogProjectionRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import { configureQaRuntime, type QaRequest } from "@/server/qa/qaRuntime";
import { executeProductionQaLifecycle } from "@/server/qa/productionQaLifecycleRuntime";
import { configureKnowledgeRuntime } from "@/server/knowledge/knowledgeRuntime";
import { mutateProductionKnowledgeSource, transitionProductionKnowledgeSource } from "@/server/knowledge/productionKnowledgeSourceStateRuntime";
import type { KnowledgeRuntimeRequest } from "@/domain/knowledge/knowledgeRuntimeContract";
import { configureConversationRuntime, type ConversationRequest } from "@/server/shared/conversationRuntime";
import { configureCandidateDecisionRuntime, type CandidateDecisionRequest } from "@/server/shared/candidateDecisionRuntime";
import { configureStrategyDecisionRuntime, type StrategyDecisionRequest } from "@/server/strategy/strategyDecisionRuntime";
import { executeProductionStrategyDecision } from "@/server/strategy/productionStrategyDecisionRuntime";
import { configureSocCommandRuntime } from "@/server/social/socCommandRuntime";
import { saveProductionSocDraft, decideProductionSocCandidate } from "@/server/social/productionSocContentRuntime";
import { configureProductionSocTargetPolicy } from "@/server/social/productionSocPolicyRuntime";
import { requestProductionSocTargetPublish } from "@/server/social/productionSocPublishRuntime";
import type { SocRuntimeRequest } from "@/server/testing/controlledSocTestRuntime";
import { configureErpCommandRuntime } from "@/server/erp/erpCommandRuntime";
import { requestProductionErpSnapshotRefresh } from "@/server/erp/productionErpSnapshotRuntime";
import type { ErpRuntimeRequest } from "@/server/testing/controlledErpTestRuntime";
import { configureSystemLifecycleRuntime, type SysRequest } from "@/server/system/systemLifecycleRuntime";
import {
  resolveProductionSystemContinuityContext,
  executeProductionSystemLifecycleOperation,
  auditProductionSystemLifecycleOperation,
} from "@/server/system/productionSystemLifecycleRuntime";
import { configureAiApiCommandRuntime } from "@/server/aiApi/aiApiCommandRuntime";
import { executeProductionAiApiCommand, auditProductionAiApiCommand } from "@/server/aiApi/productionAiApiCommandRuntime";
import { executeProductionConversationTurn, requestProductionConversationStop } from "@/server/shared/productionConversationAiRuntime";
import { executeProductionCoreGovernedPort,isProductionCoreGovernedPort } from "@/server/core/productionCoreGovernedRuntime";
import { configureAssetRuntime } from "@/server/asset/assetRuntime";
import type { AssetRuntimeRequest } from "@/domain/asset/assetRuntimeContract";
import { configureVideoRuntime } from "@/server/video/videoRuntime";
import type { VideoRuntimeRequest } from "@/domain/video/videoRuntimeContract";
import { executeProductionDepartmentPort, auditProductionDepartmentPort } from "@/server/shared/productionDepartmentPortRuntime";
import { configureSharedProductionOperationRuntime, type SharedProductionOperationRequest } from "@/server/shared/sharedProductionOperationRuntime";
import { executeProductionSharedOperation, auditProductionSharedOperation } from "@/server/shared/productionSharedOperationRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;

let bound = false;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function asUuidText(value: unknown): string | null {
  const text = asText(value);
  return text && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(text) ? text : null;
}

function asJsonObject(value: unknown): Record<string, unknown> | null {
  if (typeof value === "string") {
    try {
      return asRecord(JSON.parse(value));
    } catch {
      return null;
    }
  }
  return asRecord(value);
}

function emptyObjectMatches(assignmentScope: unknown, requestScope: Record<string, never>): boolean {
  const scope = asJsonObject(assignmentScope);
  if (!scope) return false;
  return Object.keys(scope).every((key) => key in requestScope && Object.is(scope[key], requestScope[key as never]));
}

function conditionAllows(condition: unknown): boolean {
  const object = asJsonObject(condition);
  if (!object) return false;
  return Object.keys(object).length === 0;
}

function sha256(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}

function firstRow(rows: unknown): Record<string, unknown> | null {
  return Array.isArray(rows) ? asRecord(rows[0]) : null;
}

async function readSessionCookie(): Promise<string | undefined> {
  try {
    const jar = await cookies();
    return jar.get(IDENTITY_COOKIE_NAME)?.value;
  } catch {
    return undefined;
  }
}

type IdentityContext = {
  actor: IdentityActor;
  session_token_hash: string;
};

async function requireIdentityContext(): Promise<IdentityContext> {
  await ensureProductionNeonRuntime();
  const cookieValue = await readSessionCookie();
  const identity = await resolveIdentityFromCookie(cookieValue);
  if (!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  if (!cookieValue) throw new NamedRuntimeError("RLS_SESSION_CONTEXT_REQUIRED");
  return {
    actor: identity.actor,
    session_token_hash: hashSessionToken(cookieValue),
  };
}

async function requireActor(): Promise<IdentityActor> {
  return (await requireIdentityContext()).actor;
}

async function requireSql(): Promise<SqlClient> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  return sql;
}

async function evaluatePageView(resourceKey: string): Promise<{ allowed: true; actor: IdentityActor } | { allowed: false; reason_code: string }> {
  const sql = getProductionNeonSql();
  if (!sql) {
    await ensureProductionNeonRuntime();
  }
  const boundSql = getProductionNeonSql();
  if (!boundSql) return { allowed: false, reason_code: "DATABASE_RUNTIME_NOT_BOUND" };
  const cookieValue = await readSessionCookie();
  const identity = await resolveIdentityFromCookie(cookieValue);
  if (!identity.ok) return { allowed: false, reason_code: identity.reason_code };
  if (!cookieValue) return { allowed: false, reason_code: "RLS_SESSION_CONTEXT_REQUIRED" };
  try {
    const rows = await runRlsActorQuery(
      boundSql,
      hashSessionToken(cookieValue),
      boundSql`
        SELECT a.effect, a.scope, a.condition
        FROM account_permission_assignments a
        JOIN permission_resources r ON r.resource_id = a.resource_id
        WHERE a.user_id = ${identity.actor.user_id}
          AND r.resource_key = ${resourceKey}
          AND r.resource_type = 'PAGE'
          AND r.active = true
          AND a.action = 'VIEW'
          AND a.status = 'APPROVED'
          AND a.effective_from <= now()
          AND (a.effective_to IS NULL OR a.effective_to > now())
      `,
    );
    const requestScope = {} as Record<string, never>;
    const matched: string[] = [];
    for (const raw of Array.isArray(rows) ? rows : []) {
      const row = asRecord(raw);
      if (!row) continue;
      if (!emptyObjectMatches(row.scope, requestScope)) continue;
      if (!conditionAllows(row.condition)) continue;
      const effect = asText(row.effect);
      if (effect) matched.push(effect);
    }
    if (matched.includes("DENY")) return { allowed: false, reason_code: "PERMISSION_DENIED" };
    if (matched.includes("ALLOW")) return { allowed: true, actor: identity.actor };
    return { allowed: false, reason_code: "PERMISSION_OR_SCOPE_DENIED" };
  } catch {
    return { allowed: false, reason_code: "AUTHORIZATION_EVALUATION_FAILED" };
  }
}

async function evaluateResourceAction(
  resourceKey: string,
  action: string,
): Promise<{ allowed: true; actor: IdentityActor } | { allowed: false; reason_code: string }> {
  if (!resourceKey || !action) return { allowed: false, reason_code: "OPERATION_PERMISSION_MAPPING_REQUIRED" };
  if (!getProductionNeonSql()) await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) return { allowed: false, reason_code: "DATABASE_RUNTIME_NOT_BOUND" };
  const cookieValue = await readSessionCookie();
  const identity = await resolveIdentityFromCookie(cookieValue);
  if (!identity.ok) return { allowed: false, reason_code: identity.reason_code };
  if (!cookieValue) return { allowed: false, reason_code: "RLS_SESSION_CONTEXT_REQUIRED" };
  try {
    const result = await runRlsActorQuery(
      sql,
      hashSessionToken(cookieValue),
      sql`
        SELECT a.effect,a.scope,a.condition
        FROM account_permission_assignments a
        JOIN permission_resources r ON r.resource_id=a.resource_id
        WHERE a.user_id=${identity.actor.user_id}
          AND r.resource_key=${resourceKey}
          AND r.resource_type IN ('ACTION','CONTROL','API','SENSITIVE_PERMISSION')
          AND r.active=true
          AND ${action}=ANY(
            SELECT jsonb_array_elements_text(
              CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
            )
          )
          AND a.action=${action}
          AND a.status='APPROVED'
          AND a.effective_from<=now()
          AND (a.effective_to IS NULL OR a.effective_to>now())
      `,
    );
    const requestScope={} as Record<string,never>;
    const matched:string[]=[];
    for(const raw of Array.isArray(result)?result:[]){
      const row=asRecord(raw);
      if(!row)continue;
      if(!emptyObjectMatches(row.scope,requestScope))continue;
      if(!conditionAllows(row.condition))continue;
      const effect=asText(row.effect);
      if(effect)matched.push(effect);
    }
    if(matched.includes("DENY"))return{allowed:false,reason_code:"PERMISSION_DENIED"};
    if(matched.includes("ALLOW"))return{allowed:true,actor:identity.actor};
    return{allowed:false,reason_code:"PERMISSION_OR_SCOPE_DENIED"};
  } catch {
    return{allowed:false,reason_code:"AUTHORIZATION_EVALUATION_FAILED"};
  }
}

const IAM_OPERATION_PERMISSION: Readonly<Record<string,{resource_key:string;action:string}>> = {
  searchProjection:{resource_key:"action:admin:IAM-01:ACT-SEARCH",action:"INVOKE"},
  saveDraft:{resource_key:"action:admin:IAM-02:ACT-DRAFT-SAVE",action:"INVOKE"},
  validateDraft:{resource_key:"action:admin:IAM-02:ACT-DRAFT-VALIDATE",action:"INVOKE"},
  previewAuthorizationImpact:{resource_key:"action:admin:IAM-02:ACT-ACCOUNT-PERMISSION-PREVIEW",action:"INVOKE"},
  assignAccountPermission:{resource_key:"action:admin:IAM-05:ACT-CONFIGURE",action:"INVOKE"},
  revokeAccountPermission:{resource_key:"action:admin:IAM-05:ACT-CONFIGURE",action:"INVOKE"},
};

const DEV_OPERATION_PERMISSION: Readonly<Record<string,{resource_key:string;action:string}>> = {
  startCompanyDiscovery:{resource_key:"action:admin:DEV-01:ACT-DISCOVERY-START",action:"INVOKE"},
  pauseCompanyDiscovery:{resource_key:"action:admin:DEV-01:ACT-DISCOVERY-PAUSE",action:"INVOKE"},
  resumeCompanyDiscovery:{resource_key:"action:admin:DEV-01:ACT-DISCOVERY-RESUME",action:"INVOKE"},
  stopCompanyDiscovery:{resource_key:"action:admin:DEV-01:ACT-DISCOVERY-STOP",action:"INVOKE"},
};

const SYSTEM_OPERATION_PERMISSION: Readonly<Record<string,readonly {resource_key:string;action:string}[]>> = {
  createCandidate:[
    {resource_key:"action:admin:SYS-01:ACT-CANDIDATE-CREATE",action:"INVOKE"},
    {resource_key:"api:createCandidate",action:"EXECUTE"},
  ],
  createChangeRequest:[
    {resource_key:"action:admin:SYS-01:ACT-CR-CREATE",action:"INVOKE"},
    {resource_key:"api:createChangeRequest",action:"EXECUTE"},
  ],
  runSandboxTest:[
    {resource_key:"api:runSandboxTest",action:"EXECUTE"},
  ],
};

const AIAPI_OPERATION_PERMISSION: Readonly<Record<string,{resource_key:string;action:string}>> = {
  createProviderModelProfile:{resource_key:"control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-CREATE-PROFILE",action:"INVOKE"},
  updateProviderModelProfile:{resource_key:"control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-UPDATE-PROFILE",action:"INVOKE"},
  getProviderModelProfile:{resource_key:"control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-VIEW-PROFILE",action:"INVOKE"},
  listProviderModelProfiles:{resource_key:"control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-LIST-PROFILES",action:"INVOKE"},
  testProviderModelProfile:{resource_key:"control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-TEST-PROFILE",action:"INVOKE"},
  retireProviderModelProfile:{resource_key:"control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-RETIRE-PROFILE",action:"INVOKE"},
  setProviderModelCredential:{resource_key:"control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-SET-CREDENTIAL",action:"INVOKE"},
  deleteProviderModelCredential:{resource_key:"control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-DELETE-CREDENTIAL",action:"INVOKE"},
  setKillSwitch:{resource_key:"control:CTRL-ADMIN-AIAPI-09-ACT-02-ACT-KILL-SWITCH",action:"INVOKE"},
  createProviderCandidateGroup:{resource_key:"control:CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-CREATE-GROUP",action:"INVOKE"},
  getProviderQuarantine:{resource_key:"control:CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-VIEW-QUARANTINE",action:"INVOKE"},
  restoreProviderFromQuarantine:{resource_key:"control:CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-RESTORE-PROVIDER",action:"INVOKE"},
  runSandboxTest:{resource_key:"action:admin:AIAPI-08:ACT-SYSTEM-TEST",action:"INVOKE"},
  executeProviderRoute:{resource_key:"control:CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-EXECUTE-ROUTE",action:"INVOKE"},
  getProviderRouteDecision:{resource_key:"control:CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-VIEW-ROUTE-DECISION",action:"INVOKE"},
};

const GOVERNANCE_PERMISSION_CONTEXT: Readonly<Record<string,{
  configure:{resource_key:string;action:string};
  approve:{resource_key:string;action:string};
}>> = {
  "admin:IAM-01":{
    configure:{resource_key:"action:admin:IAM-05:ACT-CONFIGURE",action:"INVOKE"},
    approve:{resource_key:"action:admin:IAM-05:ACT-APPROVE",action:"INVOKE"},
  },
  "admin:AIAPI-01":{
    configure:{resource_key:"action:admin:AIAPI-04:ACT-CONFIGURE",action:"INVOKE"},
    approve:{resource_key:"action:admin:AIAPI-04:ACT-APPROVE",action:"INVOKE"},
  },
  "admin:SG-02":{
    configure:{resource_key:"action:admin:SG-02:ACT-CONFIGURE",action:"INVOKE"},
    approve:{resource_key:"action:admin:SG-02:ACT-APPROVE",action:"INVOKE"},
  },
  "admin:STR-02":{
    configure:{resource_key:"action:admin:STR-02:ACT-CONFIGURE",action:"INVOKE"},
    approve:{resource_key:"action:admin:STR-02:ACT-APPROVE",action:"INVOKE"},
  },
};

async function authorizeDev(request:DevRuntimeRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:DEV-01"]);
  if(!page.allowed)return page;
  const permission=DEV_OPERATION_PERMISSION[request.operation_id];
  if(!permission)return{allowed:false,reason_code:"DEV01_OPERATION_PERMISSION_MAPPING_REQUIRED"};
  const gate=await evaluateResourceAction(permission.resource_key,permission.action);
  return gate.allowed?{allowed:true}:gate;
}

async function authorizeAiApi(request:{operation_id:string}):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:AIAPI-01"]);
  if(!page.allowed)return page;
  if(request.operation_id==="runProviderQueueProbe")return{allowed:true};
  const permission=AIAPI_OPERATION_PERMISSION[request.operation_id];
  if(!permission)return{allowed:false,reason_code:"AIAPI_OPERATION_PERMISSION_MAPPING_REQUIRED"};
  const gate=await evaluateResourceAction(permission.resource_key,permission.action);
  return gate.allowed?{allowed:true}:gate;
}

const ERP_SNAPSHOT_REFRESH_PERMISSIONS: readonly {resource_key:string;action:string}[] = [
  {resource_key:"control:CTRL-ADMIN-ERP-01-ACT-05-ERP-SNAPSHOT-REFRESH",action:"INVOKE"},
  {resource_key:"api:refreshERPSnapshot",action:"EXECUTE"},
];

async function authorizeErp(request:ErpRuntimeRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:ERP-01"]);
  if(!page.allowed)return page;
  if([
    "refreshProjection",
    "getERPSyncStatus",
    "getERPFailure",
    "getERPFinanceFactPack",
    "getERPCapacityGuardrails",
    "getERPForecast",
  ].includes(request.operation_id))return{allowed:true};
  if(request.operation_id==="refreshERPSnapshot"){
    for(const permission of ERP_SNAPSHOT_REFRESH_PERMISSIONS){
      const gate=await evaluateResourceAction(permission.resource_key,permission.action);
      if(!gate.allowed)return gate;
    }
    return{allowed:true};
  }
  return{allowed:false,reason_code:"ERP01_OPERATION_PERMISSION_MAPPING_REQUIRED"};
}

const SOC_TARGET_POLICY_PERMISSIONS: readonly {resource_key:string;action:string}[] = [
  {resource_key:"action:admin:SOC-04:ACT-SOCIAL-TARGET-POLICY",action:"INVOKE"},
  {resource_key:"control:CTRL-ADMIN-SOC-04-ACT-01-ACT-SOCIAL-TARGET-POLICY",action:"INVOKE"},
  {resource_key:"api:configureSocialTargetPolicy",action:"EXECUTE"},
];

const SOC_PUBLISH_REQUEST_PERMISSIONS: readonly {resource_key:string;action:string}[] = [
  {resource_key:"action:admin:SOC-04:ACT-SOCIAL-TARGET-PUBLISH",action:"INVOKE"},
  {resource_key:"control:CTRL-ADMIN-SOC-04-ACT-02-ACT-SOCIAL-TARGET-PUBLISH",action:"INVOKE"},
  {resource_key:"api:requestSocialTargetPublish",action:"EXECUTE"},
];

async function authorizeSoc(request:SocRuntimeRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:SOC-01"]);
  if(!page.allowed)return page;
  if(request.operation_id==="searchProjection"||request.operation_id==="refreshProjection")return{allowed:true};
  if(request.operation_id==="saveDraft"){
    const gate=await evaluateResourceAction("api:saveDraft","EXECUTE");
    return gate.allowed?{allowed:true}:gate;
  }
  if(request.operation_id==="configureSocialTargetPolicy"){
    for(const permission of SOC_TARGET_POLICY_PERMISSIONS){
      const gate=await evaluateResourceAction(permission.resource_key,permission.action);
      if(!gate.allowed)return gate;
    }
    return{allowed:true};
  }
  if(request.operation_id==="requestSocialTargetPublish"){
    for(const permission of SOC_PUBLISH_REQUEST_PERMISSIONS){
      const gate=await evaluateResourceAction(permission.resource_key,permission.action);
      if(!gate.allowed)return gate;
    }
    return{allowed:true};
  }
  return{allowed:false,reason_code:"SOC01_OPERATION_PERMISSION_MAPPING_REQUIRED"};
}

async function authorizeCandidateDecision(request:CandidateDecisionRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const payload=asRecord(request.payload)??{};
  const pageUid=asText(payload.page_uid);
  if(pageUid==="admin:SOC-01"){
    const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:SOC-01"]);
    if(!page.allowed)return page;
    const gate=await evaluateResourceAction("api:decideCandidate","EXECUTE");
    return gate.allowed?{allowed:true}:gate;
  }
  if(pageUid==="workspace:INFO-01"){
    const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["workspace:INFO-01"]);
    if(!page.allowed)return page;
    const gate=await evaluateResourceAction("api:decideCandidate","EXECUTE");
    return gate.allowed?{allowed:true}:gate;
  }
  return{allowed:false,reason_code:"CANDIDATE_DECISION_OWNER_CONTEXT_UNREGISTERED"};
}

async function decideRegisteredCandidate(request:CandidateDecisionRequest):Promise<unknown>{
  const payload=asRecord(request.payload)??{};
  const pageUid=asText(payload.page_uid);
  if(pageUid==="admin:SOC-01")return decideProductionSocCandidate(request);
  if(pageUid==="workspace:INFO-01")return decideProductionInfoCandidate(request);
  throw new NamedRuntimeError("CANDIDATE_DECISION_OWNER_CONTEXT_UNREGISTERED");
}

async function authorizeSystemLifecycle(request:SysRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:SYS-01"]);
  if(!page.allowed)return page;
  const permissions=SYSTEM_OPERATION_PERMISSION[request.operation_id];
  if(!permissions?.length)return{allowed:false,reason_code:"SYS01_OPERATION_PERMISSION_MAPPING_REQUIRED"};
  for(const permission of permissions){
    const gate=await evaluateResourceAction(permission.resource_key,permission.action);
    if(!gate.allowed)return gate;
  }
  return{allowed:true};
}

async function authorizeIam(request:IamRuntimeRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  if(request.operation==="configureGovernedResource"||request.operation==="approveGovernedResource"){
    const payload=asRecord(request.payload)??{};
    const currentPageUid=asText(payload.current_page_uid)??asText(payload.page_uid);
    const sourcePageUid=asText(payload.source_page_uid)??asText(payload.page_uid);
    if(!currentPageUid||!sourcePageUid)return{allowed:false,reason_code:"IAM_OPERATION_PERMISSION_CONTEXT_REQUIRED"};
    const currentPageResource=CURRENT_PAGE_RESOURCE_KEYS[currentPageUid as keyof typeof CURRENT_PAGE_RESOURCE_KEYS];
    if(!currentPageResource)return{allowed:false,reason_code:"IAM_CURRENT_PAGE_PERMISSION_CONTEXT_UNREGISTERED"};
    const page=await evaluatePageView(currentPageResource);
    if(!page.allowed)return page;
    const context=GOVERNANCE_PERMISSION_CONTEXT[sourcePageUid as keyof typeof GOVERNANCE_PERMISSION_CONTEXT];
    if(!context)return{allowed:false,reason_code:"IAM_OPERATION_PERMISSION_CONTEXT_UNREGISTERED"};
    const permission=request.operation==="configureGovernedResource"?context.configure:context.approve;
    const gate=await evaluateResourceAction(permission.resource_key,permission.action);
    return gate.allowed?{allowed:true}:gate;
  }
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:IAM-01"]);
  if(!page.allowed)return page;
  if(request.operation==="getUiProjection")return{allowed:true};
  const permission=IAM_OPERATION_PERMISSION[request.operation];
  if(!permission)return{allowed:false,reason_code:"IAM_OPERATION_PERMISSION_MAPPING_REQUIRED"};
  const gate=await evaluateResourceAction(permission.resource_key,permission.action);
  return gate.allowed?{allowed:true}:gate;
}

const INFO_WORKSPACE_OPERATION_PERMISSION: Readonly<Record<string,{resource_key:string;action:string}>> = {
  refreshProjection:{resource_key:"api:refreshProjection",action:"EXECUTE"},
  searchProjection:{resource_key:"api:searchProjection",action:"EXECUTE"},
  exportProjection:{resource_key:"api:exportProjection",action:"EXECUTE"},
  adoptContextCandidate:{resource_key:"api:adoptContextCandidate",action:"EXECUTE"},
};

async function authorizeInfoCommand(request: InfoRequest): Promise<{ allowed: true } | { allowed: false; reason_code: string }> {
  const payload = asRecord(request.payload) ?? {};
  const currentPageUid = asText(payload.current_page_uid) ?? asText(payload.page_uid);
  const sourcePageUid = asText(payload.source_page_uid);

  if (currentPageUid === "admin:STR-01" || sourcePageUid?.startsWith("admin:STR-")) {
    const pageGate = await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:STR-01"]);
    if (!pageGate.allowed) return pageGate;

    let resourceKey: string | null = null;
    if (request.operation_id === "searchProjection") {
      resourceKey = sourcePageUid === "admin:STR-04"
        ? "action:admin:STR-04:ACT-SEARCH"
        : sourcePageUid === "admin:STR-01"
          ? "action:admin:STR-01:ACT-SEARCH"
          : null;
    } else if (request.operation_id === "refreshProjection" && sourcePageUid === "admin:STR-01") {
      resourceKey = "action:admin:STR-01:ACT-REFRESH";
    } else if (request.operation_id === "exportProjection" && sourcePageUid === "admin:STR-04") {
      resourceKey = "action:admin:STR-04:ACT-EXPORT";
    }
    if (!resourceKey) return { allowed: false, reason_code: "STR_ADMIN_SOURCE_ACTION_CONTEXT_REQUIRED" };
    const actionGate = await evaluateResourceAction(resourceKey, "INVOKE");
    return actionGate.allowed ? { allowed: true } : actionGate;
  }

  if (currentPageUid === "admin:IAM-01") {
    const pageGate = await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:IAM-01"]);
    if (!pageGate.allowed) return pageGate;
    if (request.operation_id !== "searchProjection") {
      return { allowed: false, reason_code: "IAM_INFO_OPERATION_NOT_REGISTERED" };
    }
    const actionGate = await evaluateResourceAction("action:admin:IAM-01:ACT-SEARCH", "INVOKE");
    return actionGate.allowed ? { allowed: true } : actionGate;
  }

  if (currentPageUid !== "workspace:INFO-01") {
    return { allowed: false, reason_code: "INFO01_OWNER_CONTEXT_REQUIRED" };
  }
  const pageGate = await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["workspace:INFO-01"]);
  if (!pageGate.allowed) return pageGate;
  const permission = INFO_WORKSPACE_OPERATION_PERMISSION[request.operation_id];
  if (!permission) return { allowed: false, reason_code: "INFO01_OPERATION_PERMISSION_MAPPING_REQUIRED" };
  const actionGate = await evaluateResourceAction(permission.resource_key, permission.action);
  return actionGate.allowed ? { allowed: true } : actionGate;
}

async function authorizeCore(request: CoreRuntimeRequest): Promise<{ allowed: true } | { allowed: false; reason_code: string }> {
  if(request.port_uid==="CORE-01-PORT-LOCK-DECIDE"){
    const decisionGate=await evaluateResourceAction("api:decideLockReview","EXECUTE");
    return decisionGate.allowed?{allowed:true}:decisionGate;
  }
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["CORE-01"]);
  if(!page.allowed)return page;
  const governedPermission:Partial<Record<CoreRuntimeRequest["port_uid"],string>>={
    "CORE-01-PORT-PROJECT-CREATE":"api:createProjectDraft",
    "CORE-01-PORT-PROJECT-VALIDATE":"api:validateProjectDraft",
    "CORE-01-PORT-PROJECT-CONFIRM":"api:confirmProjectDraft",
    "CORE-01-PORT-STORY-CANDIDATE":"api:createStoryCandidateSet",
    "CORE-01-PORT-THREAD-CREATE":"api:createConversationThread",
    "CORE-01-PORT-MESSAGE-SEND":"api:sendConversationMessage",
    "CORE-01-PORT-CANDIDATE-CREATE":"api:createCandidate",
    "CORE-01-PORT-CANDIDATE-COMPARE":"api:compareCandidates",
    "CORE-01-PORT-CANDIDATE-DECIDE":"api:decideCandidate",
    "CORE-01-PORT-DNA-LOCK":"api:requestDNALock",
    "CORE-01-PORT-CORE-REVIEW":"api:submitCoreReview",
    "CORE-01-PORT-MOTHER-LOCK":"api:requestMotherLock",
    "CORE-01-PORT-TOPIC-CREATE":"api:createTopic",
    "CORE-01-PORT-BLUEPRINT-CREATE":"api:createBlueprint",
    "CORE-01-PORT-BLUEPRINT-VALIDATE":"api:validateBlueprint",
    "CORE-01-PORT-BLUEPRINT-APPROVE":"api:approveBlueprint",
    "CORE-01-PORT-CHILD-LOCK":"api:requestChildLock",
    "CORE-01-PORT-LOCK-DECIDE":"api:decideLockReview",
    "CORE-01-PORT-CANONICAL-SCRIPT":"api:getCanonicalScript",
  };
  const resource=governedPermission[request.port_uid];
  if(!resource)return{allowed:true};
  const operation=await evaluateResourceAction(resource,"EXECUTE");
  return operation.allowed?{allowed:true}:operation;
}

function payloadRecord(request: CoreRuntimeRequest): Record<string, unknown> {
  return asRecord(request.payload) ?? {};
}

function requirePayloadText(payload: Record<string, unknown>, key: string): string {
  const value = asText(payload[key]);
  if (!value) throw new NamedRuntimeError(`STORY_CANDIDATE_FIELD_REQUIRED:${key}`);
  return value;
}

function requirePayloadJson(payload: Record<string, unknown>, key: string): string {
  const value = payload[key];
  if (value === undefined || value === null) {
    throw new NamedRuntimeError(`STORY_CANDIDATE_FIELD_REQUIRED:${key}`);
  }
  try {
    return JSON.stringify(value);
  } catch {
    throw new NamedRuntimeError(`STORY_CANDIDATE_FIELD_INVALID:${key}`);
  }
}

function slugCode(title: string, prefix: string): string {
  const base = title.toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 20);
  return `${prefix}-${base || "ITEM"}-${Date.now().toString(36).toUpperCase()}`;
}

async function executeCore(request: CoreRuntimeRequest): Promise<unknown> {
  const sql = await requireSql();
  const identityContext = await requireIdentityContext();
  const actor = identityContext.actor;
  const payload = payloadRecord(request);

  if(isProductionCoreGovernedPort(request.port_uid)) return executeProductionCoreGovernedPort(request);

  switch (request.port_uid) {



    case "CORE-01-PORT-THREAD-CREATE": {
      const projectId = asUuidText(request.path_params?.projectId);
      if (!projectId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:projectId");
      const work_item = asText(payload.work_item);
      if (!work_item) throw new NamedRuntimeError("REQUIRED_WORK_ITEM_MISSING");
      const topicRaw = payload.topic_id;
      const topic_id = topicRaw == null || topicRaw === "" ? null : asUuidText(topicRaw);
      if (topicRaw != null && topicRaw !== "" && !topic_id) throw new NamedRuntimeError("TOPIC_ID_INVALID");

      const projectWorkItems = new Set(["STORY","CHAPTER","WORLD_SETTING","DNA","BLUEPRINT"]);
      const topicWorkItems = new Set(["TOPIC_SCOPE","PRODUCTION_SCRIPT"]);
      if ((topic_id === null && !projectWorkItems.has(work_item)) || (topic_id !== null && !topicWorkItems.has(work_item))) {
        throw new NamedRuntimeError("WORK_ITEM_NOT_ALLOWED_IN_CURRENT_MODE");
      }

      const relation_kind = asText(payload.relation_kind) ?? "ROOT";
      if (relation_kind !== "ROOT" && relation_kind !== "BRANCH") throw new NamedRuntimeError("THREAD_RELATION_KIND_INVALID");
      const parent_conversation_id = payload.parent_conversation_id == null || payload.parent_conversation_id === "" ? null : asUuidText(payload.parent_conversation_id);
      const source_message_id = payload.source_message_id == null || payload.source_message_id === "" ? null : asUuidText(payload.source_message_id);
      if (relation_kind === "ROOT" && (parent_conversation_id || source_message_id)) throw new NamedRuntimeError("ROOT_THREAD_RELATION_REFS_FORBIDDEN");
      if (relation_kind === "BRANCH" && (!parent_conversation_id || !source_message_id)) throw new NamedRuntimeError("BRANCH_THREAD_RELATION_REFS_REQUIRED");

      const projectRows = topic_id
        ? await runRlsActorQuery(
            sql,
            identityContext.session_token_hash,
            sql`
              SELECT p.workspace_id::text AS workspace_id
              FROM projects p
              JOIN topics t ON t.project_id=p.project_id
              WHERE p.project_id=${projectId}::uuid
                AND t.topic_id=${topic_id}::uuid
              LIMIT 1
            `,
          )
        : await runRlsActorQuery(
            sql,
            identityContext.session_token_hash,
            sql`
              SELECT p.workspace_id::text AS workspace_id
              FROM projects p
              WHERE p.project_id=${projectId}::uuid
              LIMIT 1
            `,
          );
      const workspace_id = asUuidText(firstRow(projectRows)?.workspace_id);
      if (!workspace_id) throw new NamedRuntimeError(topic_id ? "TOPIC_PROJECT_LINEAGE_MISMATCH" : "PROJECT_NOT_FOUND");

      if (relation_kind === "BRANCH") {
        const branchRows = await runRlsActorQuery(
          sql,
          identityContext.session_token_hash,
          sql`
            SELECT b.conversation_id::text AS parent_conversation_id
            FROM core_conversation_thread_bindings b
            JOIN conversation_messages m
              ON m.conversation_id=b.conversation_id
             AND m.conversation_message_id=${source_message_id}::uuid
            WHERE b.conversation_id=${parent_conversation_id}::uuid
              AND b.project_id=${projectId}::uuid
              AND b.work_item=${work_item}
              AND (
                (${topic_id}::uuid IS NULL AND b.topic_id IS NULL)
                OR b.topic_id=${topic_id}::uuid
              )
            LIMIT 1
          `,
        );
        if (!firstRow(branchRows)) throw new NamedRuntimeError("BRANCH_THREAD_SCOPE_MISMATCH");
      }

      const conversation_id = crypto.randomUUID();
      const title = work_item;
      const [conversationRows,bindingRows] = await runRlsActorTransaction(
        sql,
        identityContext.session_token_hash,
        [
          topic_id
            ? sql`
                INSERT INTO conversations (conversation_id, workspace_id, project_id, topic_id, title, created_by)
                VALUES (${conversation_id}::uuid, ${workspace_id}::uuid, ${projectId}::uuid, ${topic_id}::uuid, ${title}, ${actor.user_id}::uuid)
                RETURNING conversation_id::text AS conversation_id
              `
            : sql`
                INSERT INTO conversations (conversation_id, workspace_id, project_id, title, created_by)
                VALUES (${conversation_id}::uuid, ${workspace_id}::uuid, ${projectId}::uuid, ${title}, ${actor.user_id}::uuid)
                RETURNING conversation_id::text AS conversation_id
              `,
          sql`
            INSERT INTO core_conversation_thread_bindings(
              conversation_id,project_id,topic_id,work_item,parent_conversation_id,source_message_id,relation_kind,created_by
            ) VALUES(
              ${conversation_id}::uuid,${projectId}::uuid,${topic_id}::uuid,${work_item},
              ${parent_conversation_id}::uuid,${source_message_id}::uuid,${relation_kind},${actor.user_id}::uuid
            )
            RETURNING conversation_id::text AS conversation_id
          `,
        ],
      );
      if (!asText(firstRow(conversationRows)?.conversation_id) || !asText(firstRow(bindingRows)?.conversation_id)) {
        throw new NamedRuntimeError("CONVERSATION_THREAD_BINDING_INSERT_FAILED");
      }
      return { conversation_id, project_id: projectId, work_item, topic_id, relation_kind, parent_conversation_id, source_message_id };
    }

    case "CORE-01-PORT-MESSAGE-SEND": {
      const conversationId = asText(request.path_params?.conversationId);
      if (!conversationId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:conversationId");
      const message = asText(payload.message);
      if (!message) throw new NamedRuntimeError("MESSAGE_REQUIRED");
      return executeProductionConversationTurn({
        conversation_id: conversationId,
        actor_user_id: actor.user_id,
        session_token_hash: identityContext.session_token_hash,
        message,
        correlation_id: request.correlation_id,
        instruction_kind: asText(payload.instruction_kind),
        source_message_id: asText(payload.source_message_id),
        attachment_refs: Array.isArray(payload.attachment_refs)
          ? payload.attachment_refs.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
          : [],
        reference_refs: Array.isArray(payload.reference_refs)
          ? payload.reference_refs.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
          : [],
        page_uid: "CORE-01",
        ai_mode: asText(payload.ai_mode),
        council_mode: asText(payload.council_mode),
        system_change_id: asText(payload.system_change_id),
      });
    }

    case "CORE-01-PORT-STORY-CANDIDATE": {
      const projectId = asText(request.path_params?.projectId);
      if (!projectId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:projectId");
      const projectRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT project_id::text AS project_id, status::text AS status
          FROM projects
          WHERE project_id = ${projectId}::uuid
          LIMIT 1
        `,
      );
      const project = firstRow(projectRows);
      if (!project) throw new NamedRuntimeError("PROJECT_NOT_FOUND");
      if (asText(project.status) !== "CORE_MODELING") throw new NamedRuntimeError("PROJECT_NOT_CONFIRMED");
      const candidate_key = requirePayloadText(payload, "candidate_key");
      const content = requirePayloadJson(payload, "content");
      const strengths = requirePayloadJson(payload, "strengths");
      const weaknesses = requirePayloadJson(payload, "weaknesses");
      const market_positioning = requirePayloadText(payload, "market_positioning");
      const character_space = requirePayloadText(payload, "character_space");
      const long_form_extension = requirePayloadText(payload, "long_form_extension");
      const foreshadowing_capacity = requirePayloadText(payload, "foreshadowing_capacity");
      const production_cost = requirePayloadText(payload, "production_cost");
      const production_risk = requirePayloadText(payload, "production_risk");
      const recommendation = requirePayloadText(payload, "recommendation");
      const wizard_session_id = asText(payload.wizard_session_id);
      const storyRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          INSERT INTO story_candidates (
            story_candidate_id, project_id, candidate_key, content, status, wizard_session_id,
            strengths, weaknesses, market_positioning, character_space, long_form_extension,
            foreshadowing_capacity, production_cost, production_risk, recommendation,
            generated_by_subject_type
          ) VALUES (
            gen_random_uuid(), ${projectId}::uuid, ${candidate_key}, ${content}::jsonb, 'CANDIDATE',
            ${wizard_session_id}::uuid, ${strengths}::jsonb, ${weaknesses}::jsonb,
            ${market_positioning}, ${character_space}, ${long_form_extension},
            ${foreshadowing_capacity}, ${production_cost}, ${production_risk},
            ${recommendation}, 'USER'
          )
          RETURNING story_candidate_id::text AS story_candidate_set_ref
        `,
      );
      const story_candidate_set_ref = asText(firstRow(storyRows)?.story_candidate_set_ref);
      if (!story_candidate_set_ref) throw new NamedRuntimeError("STORY_CANDIDATE_INSERT_FAILED");
      return { story_candidate_set_ref, project_id: projectId };
    }


    case "CORE-01-PORT-PROJECTION":
      return { reason_code: "USE_UI_PROJECTION_ROUTE" };

    default:
      throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
  }
}

const coreBindings: CoreRuntimeBindings = {
  authorize: authorizeCore,
  execute: executeCore,
  audit: async () => undefined,
};

async function authorizePage(resourceKey: string): Promise<{ allowed: true } | { allowed: false; reason_code: string }> {
  const gate = await evaluatePageView(resourceKey);
  if (!gate.allowed) return gate;
  return { allowed: true };
}

function dbProjection(partial: Record<string, unknown>) {
  return {
    page_state: "READY",
    values: {},
    lists: {},
    tables: {},
    gates: {
      "DB-01-GATE-PAGE": true,
      "DB-01-GATE-CONTEXT": true,
      "DB-01-GATE-ENTITY": true,
      "DB-01-GATE-SCHEMA": true,
      "DB-01-GATE-TRACE": true,
      "DB-01-GATE-MIGRATION": true,
      "DB-01-GATE-INTEGRITY": true,
      "DB-01-GATE-AUDIT": true,
    },
    filters: {},
    graph: null,
    trace: null,
    audit: null,
    source_sync: "neon:wild-wave",
    ...partial,
  };
}

async function readDb(request: DbReadRequest): Promise<unknown> {
  const sql = await requireSql();
  const query = asRecord(request.query) ?? {};
  const client = asRecord(query.client_state) ?? {};
  const search = asText(query.value) ?? asText(client.search) ?? "";

  if (request.port_uid === "DB-01-PORT-ENTITY-LIST") {
    const rows = await sql`
      SELECT table_name::text AS ref
      FROM information_schema.tables
      WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
      ORDER BY table_name
    `;
    const entities = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const ref = asText(asRecord(raw)?.ref);
      if (!ref) return [];
      if (search && !ref.toLowerCase().includes(search.toLowerCase())) return [];
      return [{ ref, label: ref, meta: { entity_type: "TABLE", domain: "public" } }];
    });
    return dbProjection({
      lists: { "DB-01-LIST-ENTITIES": entities },
      values: { "DB-01-FLD-ENV": "wild-wave", "DB-01-FLD-SCOPE": "public", "DB-01-FLD-HEALTH": "BOUND" },
    });
  }

  if (request.port_uid === "DB-01-PORT-SCHEMA") {
    const table = asText(client.entity_ref) ?? asText(query.value);
    if (!table) throw new NamedRuntimeError("ENTITY_REF_REQUIRED");
    const rows = await sql`
      SELECT column_name::text AS column_name, data_type::text AS data_type
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = ${table}
      ORDER BY ordinal_position
    `;
    const columns = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const row = asRecord(raw);
      const column_name = asText(row?.column_name);
      const data_type = asText(row?.data_type);
      if (!column_name || !data_type) return [];
      return [{ ref: column_name, label: `${column_name} ${data_type}` }];
    });
    return dbProjection({
      values: { "DB-01-FLD-ENTITY": table, "DB-01-FLD-TABLE": table },
      tables: { "DB-01-TBL-COLUMNS": columns },
    });
  }

  if (request.port_uid === "DB-01-PORT-MIGRATION") {
    const needle = asText(client.migration_search) ?? search;
    const rows = await sql`
      SELECT migration_id AS ref, applied_at::text AS applied_at, applied_by, approval_ref
      FROM schema_migration_history
      ORDER BY applied_at
    `;
    const migrations = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const row = asRecord(raw);
      const ref = asText(row?.ref);
      if (!ref) return [];
      if (needle && !ref.toLowerCase().includes(needle.toLowerCase())) return [];
      return [{ ref, label: ref, applied_at: asText(row?.applied_at), applied_by: asText(row?.applied_by), approval_ref: asText(row?.approval_ref) }];
    });
    return dbProjection({
      tables: { "DB-01-TBL-MIGRATIONS": migrations },
      values: { "DB-01-FLD-MIGRATION-HEAD": String(migrations.length) },
    });
  }

  if (request.port_uid === "DB-01-PORT-TRACE" || request.port_uid === "DB-01-PORT-INTEGRITY" || request.port_uid === "DB-01-PORT-AUDIT") {
    return dbProjection({
      lists: { "DB-01-LIST-FINDINGS": [] },
      trace: [],
      audit: [],
    });
  }

  throw new NamedRuntimeError("DB_READ_PORT_UNSUPPORTED");
}

async function executeIam(request: IamRuntimeRequest): Promise<unknown> {
  return executeProductionIamCommand(request);
}

async function executeInfo(request: InfoRequest): Promise<unknown> {
  const payload = asRecord(request.payload) ?? {};
  const pageUid = asText(payload.current_page_uid) ?? asText(payload.page_uid);
  const sourcePageUid = asText(payload.source_page_uid);

  if (pageUid === "workspace:INFO-01") {
    return executeProductionInfoCommand(request);
  }
  if (request.operation_id === "refreshProjection") {
    return { refreshed: true, page_uid: pageUid, source_page_uid: sourcePageUid };
  }
  if (request.operation_id !== "searchProjection") {
    throw new NamedRuntimeError("INFO_WRITE_RUNTIME_NOT_MATERIALIZED");
  }
  const sql = await requireSql();
  const identityContext = await requireIdentityContext();
  if (pageUid === "admin:STR-01" || sourcePageUid?.startsWith("admin:STR-")) {
    const needle = (asText(payload.query) ?? "").toLowerCase();
    const [candidateRows, factRows, sourceRows] = await Promise.all([
      runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT strategy_candidate_id::text AS ref,
                 decision_status::text AS label
          FROM strategy_candidates
          ORDER BY created_at DESC
          LIMIT 50
        `,
      ),
      runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT fact_pack_id::text AS ref,
                 status::text AS label
          FROM fact_packs
          ORDER BY created_at DESC
          LIMIT 50
        `,
      ),
      runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT knowledge_source_id::text AS ref,
                 source_key AS label
          FROM knowledge_sources
          ORDER BY created_at DESC
          LIMIT 50
        `,
      ),
    ]);
    const results = [...refItems(candidateRows), ...refItems(factRows), ...refItems(sourceRows)].filter((item) => {
      if (!needle) return true;
      return item.ref.toLowerCase().includes(needle) || item.label.toLowerCase().includes(needle);
    });
    return { results, source_page_uid: sourcePageUid, page_uid: "admin:STR-01" };
  }

  if (pageUid === "admin:IAM-01") {
    const needle = (asText(payload.query) ?? "").toLowerCase();
    const rows = await runRlsActorQuery(
      sql,
      identityContext.session_token_hash,
      sql`
        SELECT u.user_id::text AS ref, u.display_name AS label, u.email::text AS email
        FROM app_users u
        ORDER BY u.created_at DESC
      `,
    );
    const results = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const row = asRecord(raw);
      const ref = asText(row?.ref);
      const label = asText(row?.label);
      const email = asText(row?.email) ?? "";
      if (!ref || !label) return [];
      if (needle && !ref.toLowerCase().includes(needle) && !label.toLowerCase().includes(needle) && !email.toLowerCase().includes(needle)) return [];
      return [{ ref, label }];
    });
    return { results, matches: results.map((item) => item.ref) };
  }
  const q = `%${asText(payload.query) ?? ""}%`;
  const rows = await runRlsActorQuery(
    sql,
    identityContext.session_token_hash,
    sql`
      SELECT p.project_id::text AS ref, p.title AS label
      FROM projects p
      WHERE p.archived_at IS NULL
        AND (${q} = '%%' OR p.title ILIKE ${q} OR p.project_code ILIKE ${q})
      ORDER BY p.created_at DESC
      LIMIT 50
    `,
  );
  const results = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    const label = asText(row?.label);
    if (!ref || !label) return [];
    return [{ ref, label }];
  });
  return { results };
}

function refItems(rows: unknown) {
  return (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    const label = asText(row?.label) ?? ref;
    if (!ref || !label) return [];
    return [{ ref, label }];
  });
}


type DepartmentPermission={action_resource:string;control_resource:string;api_resource:string};
const DEPARTMENT_PERMISSION:Readonly<Record<string,DepartmentPermission>>={
  "ASSET:ASSET-01-PORT-EXECUTE":{action_resource:"action:workspace:ASSET-01:ACT-TASK-EXECUTE",control_resource:"control:CTRL-WORKSPACE-ASSET-01-ACT-01-ACT-TASK-EXECUTE",api_resource:"api:requestTaskExecution"},
  "ASSET:ASSET-01-PORT-RETRY":{action_resource:"action:workspace:ASSET-01:ACT-TASK-RETRY",control_resource:"control:CTRL-WORKSPACE-ASSET-01-ACT-02-ACT-TASK-RETRY",api_resource:"api:retryTaskExecution"},
  "ASSET:ASSET-01-PORT-DECISION":{action_resource:"action:workspace:ASSET-01:ACT-OUTPUT-SELECT",control_resource:"control:CTRL-WORKSPACE-ASSET-01-ACT-03-ACT-OUTPUT-SELECT",api_resource:"api:decideOutputCandidate"},
  "ASSET:ASSET-01-PORT-SCORECARD":{action_resource:"action:workspace:ASSET-01:ACT-SCORECARD-SUBMIT",control_resource:"control:CTRL-WORKSPACE-ASSET-01-ACT-04-ACT-SCORECARD-SUBMIT",api_resource:"api:submitScorecard"},
  "ASSET:ASSET-01-PORT-FINDING":{action_resource:"action:workspace:ASSET-01:ACT-FINDING-CREATE",control_resource:"control:CTRL-WORKSPACE-ASSET-01-ACT-05-ACT-FINDING-CREATE",api_resource:"api:createFinding"},
  "ASSET:ASSET-01-PORT-CORRECTION":{action_resource:"action:workspace:ASSET-01:ACT-CORRECTION-REQUEST",control_resource:"control:CTRL-WORKSPACE-ASSET-01-ACT-06-ACT-CORRECTION-REQUEST",api_resource:"api:createCorrectionRequest"},
  "ASSET:ASSET-01-PORT-OUT-VIDEO":{action_resource:"action:workspace:ASSET-01:ACT-HANDOFF-CREATE",control_resource:"control:CTRL-WORKSPACE-ASSET-01-ACT-07-ACT-HANDOFF-CREATE",api_resource:"api:createDepartmentHandoff"},
  "VIDEO:VIDEO-01-PORT-EXECUTE":{action_resource:"action:workspace:VIDEO-01:ACT-TASK-EXECUTE",control_resource:"control:CTRL-WORKSPACE-VIDEO-01-ACT-01-ACT-TASK-EXECUTE",api_resource:"api:requestTaskExecution"},
  "VIDEO:VIDEO-01-PORT-RETRY":{action_resource:"action:workspace:VIDEO-01:ACT-TASK-RETRY",control_resource:"control:CTRL-WORKSPACE-VIDEO-01-ACT-02-ACT-TASK-RETRY",api_resource:"api:retryTaskExecution"},
  "VIDEO:VIDEO-01-PORT-DECISION":{action_resource:"action:workspace:VIDEO-01:ACT-OUTPUT-SELECT",control_resource:"control:CTRL-WORKSPACE-VIDEO-01-ACT-03-ACT-OUTPUT-SELECT",api_resource:"api:decideOutputCandidate"},
  "VIDEO:VIDEO-01-PORT-SCORECARD":{action_resource:"action:workspace:VIDEO-01:ACT-SCORECARD-SUBMIT",control_resource:"control:CTRL-WORKSPACE-VIDEO-01-ACT-04-ACT-SCORECARD-SUBMIT",api_resource:"api:submitScorecard"},
  "VIDEO:VIDEO-01-PORT-FINDING":{action_resource:"action:workspace:VIDEO-01:ACT-FINDING-CREATE",control_resource:"control:CTRL-WORKSPACE-VIDEO-01-ACT-05-ACT-FINDING-CREATE",api_resource:"api:createFinding"},
  "VIDEO:VIDEO-01-PORT-CORRECTION":{action_resource:"action:workspace:VIDEO-01:ACT-CORRECTION-REQUEST",control_resource:"control:CTRL-WORKSPACE-VIDEO-01-ACT-06-ACT-CORRECTION-REQUEST",api_resource:"api:createCorrectionRequest"},
  "VIDEO:VIDEO-01-PORT-OUT-EDIT":{action_resource:"action:workspace:VIDEO-01:ACT-HANDOFF-CREATE",control_resource:"control:CTRL-WORKSPACE-VIDEO-01-ACT-07-ACT-HANDOFF-CREATE",api_resource:"api:createDepartmentHandoff"},
};
async function authorizeDepartmentPort(family:"ASSET"|"VIDEO",request:AssetRuntimeRequest|VideoRuntimeRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS[family==="ASSET"?"ASSET-01":"VIDEO-01"]);
  if(!page.allowed)return page;
  const permission=DEPARTMENT_PERMISSION[`${family}:${request.port_uid}`];
  if(!permission)return{allowed:false,reason_code:`${family}_PORT_PERMISSION_MAPPING_REQUIRED`};
  for(const [resource,action] of [[permission.action_resource,"INVOKE"],[permission.control_resource,"INVOKE"],[permission.api_resource,"EXECUTE"]] as const){
    const gate=await evaluateResourceAction(resource,action);
    if(!gate.allowed)return gate;
  }
  return{allowed:true};
}

type SharedPermission={family:"ASSET"|"VIDEO";action_resource:string;control_resource:string;api_resource:string};
const SHARED_OPERATION_PERMISSION:Readonly<Record<string,readonly SharedPermission[]>>={
  generateCorrectionScriptCandidate:[
    {family:"ASSET",action_resource:"action:workspace:ASSET-01:ACT-CORRECTION-GENERATE",control_resource:"control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-GENERATE",api_resource:"api:generateCorrectionScriptCandidate"},
    {family:"VIDEO",action_resource:"action:workspace:VIDEO-01:ACT-CORRECTION-GENERATE",control_resource:"control:workspace:VIDEO-01:VIDEO-01-BTN-GEN-CORRECTION",api_resource:"api:generateCorrectionScriptCandidate"},
  ],
  approveCorrectionScriptCandidate:[
    {family:"ASSET",action_resource:"action:workspace:ASSET-01:ACT-CORRECTION-APPROVE",control_resource:"control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-APPROVE",api_resource:"api:approveCorrectionScriptCandidate"},
    {family:"VIDEO",action_resource:"action:workspace:VIDEO-01:ACT-CORRECTION-APPROVE",control_resource:"control:workspace:VIDEO-01:VIDEO-01-BTN-APPROVE-CORRECTION",api_resource:"api:approveCorrectionScriptCandidate"},
  ],
  restoreAssetVersionAsNewDraft:[
    {family:"ASSET",action_resource:"action:workspace:ASSET-01:ACT-RESTORE-AS-NEW",control_resource:"control:workspace:ASSET-01:ASSET-01-BTN-RESTORE-AS-NEW",api_resource:"api:restoreAssetVersionAsNewDraft"},
  ],
  lockAssetVersion:[
    {family:"ASSET",action_resource:"action:workspace:ASSET-01:ACT-VERSION-LOCK",control_resource:"control:workspace:ASSET-01:ASSET-01-BTN-LOCK",api_resource:"api:lockAssetVersion"},
  ],
  lockVideoVersion:[
    {family:"VIDEO",action_resource:"action:workspace:VIDEO-01:ACT-VERSION-LOCK",control_resource:"control:workspace:VIDEO-01:VIDEO-01-BTN-LOCK",api_resource:"api:lockVideoVersion"},
  ],
};
async function authorizeSharedProductionOperation(request:SharedProductionOperationRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const payload=asRecord(request.payload)??{};
  const family=asText(payload.family);
  if(family!=="ASSET"&&family!=="VIDEO")return{allowed:false,reason_code:"SHARED_OPERATION_FAMILY_REQUIRED"};
  const candidates=SHARED_OPERATION_PERMISSION[request.operation_id]??[];
  const permission=candidates.find((item)=>item.family===family);
  if(!permission)return{allowed:false,reason_code:"SHARED_OPERATION_PERMISSION_MAPPING_REQUIRED"};
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS[family==="ASSET"?"ASSET-01":"VIDEO-01"]);
  if(!page.allowed)return page;
  for(const [resource,action] of [[permission.action_resource,"INVOKE"],[permission.control_resource,"INVOKE"],[permission.api_resource,"EXECUTE"]] as const){
    const gate=await evaluateResourceAction(resource,action);
    if(!gate.allowed)return gate;
  }
  return{allowed:true};
}

const QA_LIFECYCLE_PERMISSION: Readonly<Record<string,{resource_key:string;action:string}>> = {
  startQaReview:{resource_key:"api:startQaReview",action:"EXECUTE"},
  startRecheck:{resource_key:"api:startRecheck",action:"EXECUTE"},
  decidePass:{resource_key:"api:decidePass",action:"EXECUTE"},
  decideFail:{resource_key:"api:decideFail",action:"EXECUTE"},
  createReleasePackage:{resource_key:"api:createReleasePackage",action:"EXECUTE"},
};

async function authorizeQa(request:QaRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["QA-01"]);
  if(!page.allowed)return page;
  const permission=QA_LIFECYCLE_PERMISSION[request.operation_id];
  if(!permission)return{allowed:false,reason_code:"QA01_OPERATION_PERMISSION_MAPPING_REQUIRED"};
  const gate=await evaluateResourceAction(permission.resource_key,permission.action);
  return gate.allowed?{allowed:true}:gate;
}

const STRATEGY_DECISION_PERMISSION: Readonly<Record<string,{resource_key:string;action:string}>> = {
  submitStrategyReview:{resource_key:"api:submitStrategyReview",action:"EXECUTE"},
  adoptAsContextCandidate:{resource_key:"api:adoptAsContextCandidate",action:"EXECUTE"},
};

async function authorizeStrategyDecision(request:StrategyDecisionRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["workspace:STR-01"]);
  if(!page.allowed)return page;
  const permission=STRATEGY_DECISION_PERMISSION[request.operation_id];
  if(!permission)return{allowed:false,reason_code:"STR01_OPERATION_PERMISSION_MAPPING_REQUIRED"};
  const gate=await evaluateResourceAction(permission.resource_key,permission.action);
  return gate.allowed?{allowed:true}:gate;
}

async function executeQa(request: QaRequest): Promise<unknown> {
  return executeProductionQaLifecycle(request);
}

async function authorizeKnowledge(request:KnowledgeRuntimeRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:KB-01"]);
  if(!page.allowed)return page;
  if(request.operation==="searchKnowledge"||request.operation==="getCitation")return{allowed:true};
  if(
    request.operation==="createKnowledgeSource"
    ||request.operation==="updateKnowledgeSource"
    ||request.operation==="pauseKnowledgeSource"
    ||request.operation==="resumeKnowledgeSource"
    ||request.operation==="retireKnowledgeSource"
  ){
    const gate=await evaluateResourceAction("permission:knowledge.source.configure","EXECUTE");
    return gate.allowed?{allowed:true}:gate;
  }
  return{allowed:false,reason_code:"KB01_OPERATION_PERMISSION_MAPPING_REQUIRED"};
}

async function executeKnowledge(request: KnowledgeRuntimeRequest): Promise<unknown> {
  if (request.operation === "searchKnowledge") {
    const sql = await requireSql();
    const payload = asRecord(request.payload) ?? {};
    const q = `%${asText(payload.query) ?? ""}%`;
    const sources = await sql`
      SELECT knowledge_source_id::text AS ref, source_key AS label, status::text AS status
      FROM knowledge_sources
      WHERE ${q} = '%%' OR source_key ILIKE ${q} OR source_uri ILIKE ${q}
      ORDER BY created_at DESC
      LIMIT 50
    `;
    const evidence = await sql`
      SELECT evidence_record_id::text AS ref, source_uri AS label
      FROM evidence_records
      WHERE ${q} = '%%' OR source_uri ILIKE ${q}
      ORDER BY retrieved_at DESC
      LIMIT 50
    `;
    return { results: [...refItems(sources), ...refItems(evidence)] };
  }
  if (request.operation === "createKnowledgeSource" || request.operation === "updateKnowledgeSource") {
    return mutateProductionKnowledgeSource(request);
  }
  if (request.operation === "pauseKnowledgeSource" || request.operation === "resumeKnowledgeSource" || request.operation === "retireKnowledgeSource") {
    return transitionProductionKnowledgeSource(request);
  }
  if (request.operation === "getCitation") {
    const sql = await requireSql();
    const citationId = asText(request.path_params?.citationId);
    if (!citationId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:citationId");
    const rows = await sql`
      SELECT evidence_record_id::text AS ref, source_uri AS label, citation, classification::text AS classification
      FROM evidence_records
      WHERE evidence_record_id = ${citationId}::uuid
      LIMIT 1
    `;
    const row = firstRow(rows);
    if (!row) throw new NamedRuntimeError("CITATION_NOT_FOUND");
    return row;
  }
  throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
}

async function authorizeConversation(
  request: ConversationRequest,
): Promise<{ allowed: true } | { allowed: false; reason_code: string }> {
  const payload = asRecord(request.payload) ?? {};
  const requestedPage = asText(payload.page_uid);
  const pageUid = requestedPage === "admin:SYS-01"
    ? "admin:SYS-01"
    : requestedPage === "CORE-01"
      ? "CORE-01"
      : "workspace:STR-01";
  const pageKey = CURRENT_PAGE_RESOURCE_KEYS[pageUid];
  if (!pageKey) return { allowed: false, reason_code: "CONVERSATION_PAGE_AUTHORITY_UNRESOLVED" };
  const page = await evaluatePageView(pageKey);
  if (!page.allowed) return page;
  const permission = request.operation_id === "stopConversationGeneration"
    ? { resource_key: "api:stopConversationGeneration", action: "EXECUTE" }
    : { resource_key: "api:sendConversationMessage", action: "EXECUTE" };
  const operation = await evaluateResourceAction(permission.resource_key, permission.action);
  return operation.allowed ? { allowed: true } : operation;
}

async function executeConversation(request: ConversationRequest): Promise<unknown> {
  const conversationId = asText(request.conversation_id);
  if (!conversationId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:conversationId");
  if (request.operation_id === "stopConversationGeneration") {
    return requestProductionConversationStop(conversationId);
  }
  if (request.operation_id !== "sendConversationMessage") {
    throw new NamedRuntimeError("CONVERSATION_OPERATION_NOT_REGISTERED");
  }
  const identityContext = await requireIdentityContext();
  const payload = asRecord(request.payload) ?? {};
  const message = asText(payload.message);
  if (!message) throw new NamedRuntimeError("MESSAGE_REQUIRED");
  return executeProductionConversationTurn({
    conversation_id: conversationId,
    actor_user_id: identityContext.actor.user_id,
    session_token_hash: identityContext.session_token_hash,
    message,
    correlation_id: request.correlation_id,
    instruction_kind: asText(payload.instruction_kind),
    source_message_id: asText(payload.source_message_id),
    attachment_refs: Array.isArray(payload.attachment_refs)
      ? payload.attachment_refs.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
      : [],
    reference_refs: Array.isArray(payload.reference_refs)
      ? payload.reference_refs.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
      : [],
    page_uid: asText(payload.page_uid) ?? "workspace:STR-01",
    ai_mode: asText(payload.ai_mode) ?? asText(payload.mode),
    council_mode: asText(payload.council_mode),
    system_change_id: asText(payload.system_change_id),
  });
}

async function executeSoc(request: SocRuntimeRequest): Promise<unknown> {
  if (request.operation_id === "saveDraft") return saveProductionSocDraft(request);
  if (request.operation_id === "configureSocialTargetPolicy") return configureProductionSocTargetPolicy(request);
  if (request.operation_id === "requestSocialTargetPublish") return requestProductionSocTargetPublish(request);
  if (request.operation_id === "refreshProjection") return { refreshed: true };
  if (request.operation_id === "searchProjection") {
    const sql = await requireSql();
    const payload = asRecord(request.payload) ?? {};
    const q = `%${asText(payload.query) ?? ""}%`;
    const rows = await sql`
      SELECT channel_account_id::text AS ref, platform_key AS label, status::text AS status
      FROM channel_accounts
      WHERE ${q} = '%%' OR platform_key ILIKE ${q} OR external_account_ref ILIKE ${q}
      ORDER BY platform_key
      LIMIT 50
    `;
    return { results: refItems(rows) };
  }
  throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
}

async function executeErp(request: ErpRuntimeRequest): Promise<unknown> {
  if (request.operation_id === "refreshERPSnapshot") {
    return requestProductionErpSnapshotRefresh(request);
  }
  if (request.operation_id === "refreshProjection") {
    return { refreshed: true };
  }
  const sql = await requireSql();
  if (request.operation_id === "getERPSyncStatus") {
    const jobId = asUuidText(request.path_params?.id);
    if (!jobId) throw new NamedRuntimeError("ERP01_SYNC_JOB_ID_INVALID");
    const rows = await sql`
      SELECT erp_sync_job_id::text AS job_id,
             erp_connector_id::text AS erp_connector_id,
             status::text AS state,
             requested_scope,
             data_classification,
             snapshot_type,
             attempt_no,
             external_evidence_refs,
             requested_at::text AS requested_at,
             started_at::text AS started_at,
             completed_at::text AS completed_at
      FROM erp_sync_jobs
      WHERE erp_sync_job_id = ${jobId}::uuid
      LIMIT 1
    `;
    const job = firstRow(rows);
    if (!job) throw new NamedRuntimeError("ERP01_SYNC_JOB_NOT_FOUND");
    return { ...job, event: "erp.sync.status_read" };
  }
  if (request.operation_id === "getERPFailure") {
    const failureId = asUuidText(request.path_params?.id);
    if (!failureId) throw new NamedRuntimeError("ERP01_FAILURE_ID_INVALID");
    const rows = await sql`
      SELECT erp_failure_id::text AS failure_id,
             erp_connector_id::text AS erp_connector_id,
             erp_sync_job_id::text AS sync_job_ref,
             failure_code,
             failure_detail,
             retryable,
             status::text AS state,
             occurred_at::text AS occurred_at,
             resolved_at::text AS resolved_at
      FROM erp_failures
      WHERE erp_failure_id = ${failureId}::uuid
      LIMIT 1
    `;
    const failure = firstRow(rows);
    if (!failure) throw new NamedRuntimeError("ERP01_FAILURE_NOT_FOUND");
    return { ...failure, event: "erp.failure.read" };
  }
  if (
    request.operation_id === "getERPFinanceFactPack"
    || request.operation_id === "getERPCapacityGuardrails"
    || request.operation_id === "getERPForecast"
  ) {
    const rows = await sql`
      SELECT erp_snapshot_id::text AS ref, snapshot_type AS label, completeness::text AS completeness
      FROM erp_snapshots
      ORDER BY created_at DESC
      LIMIT 20
    `;
    return { snapshots: refItems(rows) };
  }
  throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
}

export function bindIdentityPageCommandRuntimes(): void {
  if (bound || isControlledTestMode()) return;
  bound = true;
  configureCoreRuntime(coreBindings);
  configureDbReadModelRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["admin:DB-01"]),
    read: readDb,
    audit: async () => undefined,
  });
  configureIamRuntime({
    authorize: authorizeIam,
    execute: executeIam,
    audit: async () => undefined,
  });
  configureInfoCommandRuntime({
    authorize: authorizeInfoCommand,
    execute: executeInfo,
    audit: async () => undefined,
  });
  configureDepartmentOperationRuntime({
    authorize: async () => {
      const identity = await resolveIdentityFromCookie(await readSessionCookie());
      if (!identity.ok) return { allowed: false, reason_code: identity.reason_code };
      return { allowed: true };
    },
    execute: async () => {
      throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
    },
    audit: async () => undefined,
  });
  configureAssetRuntime({
    authorize:(request)=>authorizeDepartmentPort("ASSET",request),
    execute:(request)=>executeProductionDepartmentPort("ASSET",request),
    audit:(entry)=>auditProductionDepartmentPort("ASSET",entry),
  });
  configureVideoRuntime({
    authorize:(request)=>authorizeDepartmentPort("VIDEO",request),
    execute:(request)=>executeProductionDepartmentPort("VIDEO",request),
    audit:(entry)=>auditProductionDepartmentPort("VIDEO",entry),
  });
  configureSharedProductionOperationRuntime({
    authorize:authorizeSharedProductionOperation,
    execute:executeProductionSharedOperation,
    audit:auditProductionSharedOperation,
  });
  configureQaRuntime({
    authorize: authorizeQa,
    execute: executeQa,
    audit: async () => undefined,
  });
  configureKnowledgeRuntime({
    authorize: authorizeKnowledge,
    execute: executeKnowledge,
    audit: async () => undefined,
  });
  configureConversationRuntime({
    authorize: authorizeConversation,
    execute: executeConversation,
    audit: async () => undefined,
  });
  configureStrategyDecisionRuntime({
    authorize: authorizeStrategyDecision,
    execute: executeProductionStrategyDecision,
    audit: async () => undefined,
  });
  configureDevCommandRuntime({
    authorize: authorizeDev,
    execute: executeProductionDevCommand,
    audit: async () => undefined,
  });
  configureSocCommandRuntime({
    authorize: authorizeSoc,
    execute: executeSoc,
    audit: async () => undefined,
  });
  configureCandidateDecisionRuntime({
    authorize: authorizeCandidateDecision,
    decide: decideRegisteredCandidate,
    audit: async () => undefined,
  });
  configureErpCommandRuntime({
    authorize: authorizeErp,
    execute: executeErp,
    audit: async () => undefined,
  });
  configureAiApiCommandRuntime({
    authorize: authorizeAiApi,
    execute: executeProductionAiApiCommand,
    audit: auditProductionAiApiCommand,
  });
  configureSystemLifecycleRuntime({
    resolveContinuityContext: async (system_change_id) => {
      const identity = await requireIdentityContext();
      return resolveProductionSystemContinuityContext(system_change_id, identity.session_token_hash);
    },
    authorize: authorizeSystemLifecycle,
    execute: async (request) => {
      const identity = await requireIdentityContext();
      return executeProductionSystemLifecycleOperation(request, {
        actor_user_id: identity.actor.user_id,
        session_token_hash: identity.session_token_hash,
      });
    },
    audit: async (entry) => {
      const identity = await requireIdentityContext().catch(() => null);
      if (!identity) return;
      await auditProductionSystemLifecycleOperation(entry, identity.actor.user_id);
    },
  });
}

export function isIdentityPageCommandRuntimeBound(): boolean {
  return bound;
}
