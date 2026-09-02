import{isControlledTestMode}from"@/domain/testing/controlledTestData";
import type{IamRuntimeRequest}from"@/server/iam/iamRuntime";
import type{InfoRequest}from"@/server/info/infoCommandRuntime";

const TEST_METADATA={data_classification:"TEST_ONLY",synthetic:true,test_dataset_id:"TEST-IAM-01",test_run_id:"TEST-RUN-IAM-01-CONTROLLED",created_for_validation:true,production_eligible:false}as const;
const PAGE_UID="admin:IAM-01";
const NEW_ACCOUNT_ID="TEST-IAM-ACCOUNT-NEW-001";
const FRONT_PAGE:Record<string,string>={"FRONT-L1-01":"workspace:WB-01","FRONT-L1-02":"CORE-01","FRONT-L1-03":"ASSET-01","FRONT-L1-04":"VIDEO-01","FRONT-L1-05":"EDIT-01","FRONT-L1-06":"QA-01","FRONT-L1-07":"admin:DB-01","FRONT-L1-08":"workspace:STR-01","FRONT-L1-09":"workspace:INFO-01"};
const ADMIN_PAGE:Record<string,string>={"ADMIN-L1-SYSTEM":"admin:SYS-01","ADMIN-L1-IAM":"admin:IAM-01","ADMIN-L1-DEV":"admin:DEV-01","ADMIN-L1-SOCIAL":"admin:SOC-01","ADMIN-L1-ERP":"admin:ERP-01","ADMIN-L1-AIAPI":"admin:AIAPI-01","ADMIN-L1-QA-CRITERIA":"admin:SG-02","ADMIN-L1-STRATEGY":"admin:STR-01","ADMIN-L1-KNOWLEDGE":"admin:KB-01"};

type Account={account_id:string;label:string;status:string;identity_source:string;organization_scope:string;mfa:string;risk:string;session:string;front_l1:string[];admin_l1:string[]};
type Preview={preview_ref:string;account_id:string;added:string[];removed:string[];unchanged:string[];blocked:string[];approval_required:boolean};
type Draft={draft_id:string;basic_data:Record<string,string>;front_l1:string[];admin_l1:string[];validated:boolean};
type State={accounts:Account[];search_query:string;draft:Draft|null;preview:Preview|null;configured:boolean;applied_add:Set<string>;applied_remove:Set<string>;completed:boolean;audits:string[]};
const initialAccounts:Account[]=[
 {account_id:"TEST-IAM-ACCOUNT-001",label:"[TEST] Existing operator A",status:"ACTIVE",identity_source:"TEST_IDENTITY_SOURCE",organization_scope:"TEST_SCOPE_A",mfa:"ENFORCED",risk:"LOW",session:"1 ACTIVE TEST SESSION",front_l1:["FRONT-L1-01","FRONT-L1-03"],admin_l1:["ADMIN-L1-IAM"]},
 {account_id:"TEST-IAM-ACCOUNT-002",label:"[TEST] Existing operator B",status:"ACTIVE",identity_source:"TEST_IDENTITY_SOURCE",organization_scope:"TEST_SCOPE_B",mfa:"ENFORCED",risk:"LOW",session:"0 ACTIVE TEST SESSION",front_l1:["FRONT-L1-06"],admin_l1:[]},
];
const state:State={accounts:initialAccounts.map(x=>({...x,front_l1:[...x.front_l1],admin_l1:[...x.admin_l1]})),search_query:"",draft:null,preview:null,configured:false,applied_add:new Set(),applied_remove:new Set(),completed:false,audits:[]};
function rec(v:unknown):Record<string,unknown>{return v&&typeof v==="object"&&!Array.isArray(v)?v as Record<string,unknown>:{};}
function text(v:unknown){return typeof v==="string"&&v.trim()?v.trim():null;}
function strings(v:unknown){return Array.isArray(v)?v.filter((x):x is string=>typeof x==="string"):[];}
function pagePayload(v:unknown){return text(rec(v).page_uid);}
function audit(message:string){state.audits=[`[TEST] ${message}`,...state.audits].slice(0,12);}
function assignmentForL1(key:string){const page=FRONT_PAGE[key]??ADMIN_PAGE[key];return page?`TEST-PERM:${page}:PAGE_VIEW`:null;}
function assignmentSet(front:readonly string[],admin:readonly string[]){return new Set([...front,...admin].flatMap(key=>{const ref=assignmentForL1(key);return ref?[ref]:[]}));}
function currentAssignmentSet(accountId:string){const account=state.accounts.find(x=>x.account_id===accountId);return account?assignmentSet(account.front_l1,account.admin_l1):new Set<string>();}
function projectionState(){if(state.completed)return"COMPLETE";if(state.preview)return"CREATE_PREVIEW";if(state.draft?.validated)return"CREATE_PERMISSION";if(state.draft)return"CREATE_BASIC";return"LIST";}
export function isControlledIamServerTestMode(){return isControlledTestMode();}
export function readControlledIamTestProjection(){
 const query=state.search_query.toLowerCase();
 const accounts=state.accounts.filter(a=>!query||a.account_id.toLowerCase().includes(query)||a.label.toLowerCase().includes(query));
 return{page_state:projectionState(),values:{},gate_state:{"IAM-01-GATE-PAGE":true,"IAM-01-GATE-MANAGE":true,"IAM-01-GATE-DRAFT":true,"IAM-01-GATE-PREVIEW":Boolean(state.draft?.validated),"IAM-01-GATE-COMPLETE":Boolean(state.preview)&&!state.completed},authorized_account_count:state.accounts.length,accounts,identity_schema:[{field_uid:"TEST-IAM-FIELD-IDENTITY-CANDIDATE",label:"[TEST] Identity Candidate Ref",type:"TEXT",required:true},{field_uid:"TEST-IAM-FIELD-ORG-SCOPE",label:"[TEST] Organization Scope Ref",type:"TEXT",required:true}],department_presets:[{ref:"TEST-IAM-PRESET-EDITING",label:"[TEST] Editing preset",front_l1:["FRONT-L1-05","FRONT-L1-06"],admin_l1:[]}],preview:state.preview,audit_entries:state.audits,test_metadata:TEST_METADATA};
}
function ok(value:unknown,correlation_id:string){return{ok:true as const,value:{...rec(value),test_metadata:TEST_METADATA},correlation_id};}
function fail(reason_code:string,correlation_id:string){return{ok:false as const,reason_code,correlation_id};}
export async function executeControlledIamOperation(r:IamRuntimeRequest):Promise<{ok:true;value:unknown;correlation_id:string}|{ok:false;reason_code:string;correlation_id:string}|null>{
 if(!isControlledIamServerTestMode()||pagePayload(r.payload)!==PAGE_UID)return null;
 const p=rec(r.payload);
 if(r.operation==="saveDraft"){
  const basic=rec(p.basic_data);const required=["TEST-IAM-FIELD-IDENTITY-CANDIDATE","TEST-IAM-FIELD-ORG-SCOPE"];
  if(required.some(k=>!text(basic[k])))return fail("IAM-01-ERR-IDENTITY-SCHEMA",r.correlation_id);
  state.draft={draft_id:text(p.draft_id)??"TEST-IAM-DRAFT-001",basic_data:Object.fromEntries(Object.entries(basic).filter(([,v])=>typeof v==="string")) as Record<string,string>,front_l1:strings(p.front_l1),admin_l1:strings(p.admin_l1),validated:false};state.preview=null;state.completed=false;audit(`draft saved ${state.draft.draft_id}`);return ok({draft_id:state.draft.draft_id,state:"CREATE_BASIC"},r.correlation_id);
 }
 if(r.operation==="validateDraft"){
  if(!state.draft||r.draft_id!==state.draft.draft_id)return fail("IAM-01-ERR-UNDEFINED",r.correlation_id);state.draft.validated=true;audit(`draft validated ${state.draft.draft_id}`);return ok({draft_id:state.draft.draft_id,state:"CREATE_PERMISSION"},r.correlation_id);
 }
 if(r.operation==="previewAuthorizationImpact"){
  if(!state.draft?.validated)return fail("IAM-01-ERR-L1-EXPANSION",r.correlation_id);const front=strings(p.front_l1),admin=strings(p.admin_l1);if(front.length+admin.length===0)return fail("IAM-01-ERR-L1-EXPANSION",r.correlation_id);
  const accountId=r.account_id??NEW_ACCOUNT_ID,desired=assignmentSet(front,admin),current=currentAssignmentSet(accountId),added=[...desired].filter(x=>!current.has(x)),removed=[...current].filter(x=>!desired.has(x)),unchanged=[...desired].filter(x=>current.has(x));
  state.draft.front_l1=front;state.draft.admin_l1=admin;state.preview={preview_ref:"TEST-IAM-PREVIEW-001",account_id:accountId,added,removed,unchanged,blocked:[],approval_required:true};state.configured=false;state.applied_add.clear();state.applied_remove.clear();audit(`authorization preview ${state.preview.preview_ref}`);return ok(state.preview,r.correlation_id);
 }
 if(r.operation==="configureGovernedResource"){
  if(!state.preview||p.explicit_confirmation!==true)return fail("IAM01_EXPLICIT_CONFIRMATION_REQUIRED",r.correlation_id);state.configured=true;audit(`governed account configured ${r.resource_id??state.preview.account_id}`);return ok({resource_id:r.resource_id??state.preview.account_id,state:"PENDING_PERMISSION_APPLY"},r.correlation_id);
 }
 if(r.operation==="assignAccountPermission"){
  const ref=text(p.permission_ref);if(!state.preview||!state.configured||!ref||!state.preview.added.includes(ref))return fail("IAM-01-ERR-AUTH-DENIED",r.correlation_id);state.applied_add.add(ref);audit(`permission assigned ${ref}`);return ok({permission_ref:ref,state:"ASSIGNED"},r.correlation_id);
 }
 if(r.operation==="revokeAccountPermission"){
  const ref=text(p.permission_ref);if(!state.preview||!state.configured||!ref||!state.preview.removed.includes(ref))return fail("IAM-01-ERR-AUTH-DENIED",r.correlation_id);state.applied_remove.add(ref);audit(`permission revoked ${ref}`);return ok({permission_ref:ref,state:"REVOKED"},r.correlation_id);
 }
 if(r.operation==="approveGovernedResource"){
  if(!state.preview||!state.configured||state.applied_add.size!==state.preview.added.length||state.applied_remove.size!==state.preview.removed.length)return fail("IAM-01-ERR-PARTIAL-APPLY",r.correlation_id);
  const accountId=state.preview.account_id;let account=state.accounts.find(x=>x.account_id===accountId);if(!account){account={account_id:accountId,label:"[TEST] Newly governed account",status:"ACTIVE",identity_source:"TEST_IDENTITY_SOURCE",organization_scope:"TEST_SCOPE_NEW",mfa:"ENFORCED",risk:"LOW",session:"0 ACTIVE TEST SESSION",front_l1:[],admin_l1:[]};state.accounts.push(account);}account.front_l1=[...(state.draft?.front_l1??[])];account.admin_l1=[...(state.draft?.admin_l1??[])];state.completed=true;audit(`governed account approved ${accountId}`);return ok({resource_id:r.resource_id??accountId,state:"COMPLETE"},r.correlation_id);
 }
 return null;
}
export async function executeControlledIamInfoCommand(r:InfoRequest):Promise<{ok:true;value:unknown}|{ok:false;status:number;reason_code:string}|null>{
 if(!isControlledIamServerTestMode()||r.operation_id!=="searchProjection"||pagePayload(r.payload)!==PAGE_UID)return null;const q=text(rec(r.payload).query)??"";state.search_query=q;audit(`account directory searched ${q||"all"}`);return{ok:true as const,value:{query:q,matches:readControlledIamTestProjection().accounts.map(x=>x.account_id),test_metadata:TEST_METADATA}};
}
