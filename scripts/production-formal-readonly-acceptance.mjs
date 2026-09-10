const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const routeDecisionId=(process.env.ACPOS_ACCEPTANCE_ROUTE_DECISION_ID??"").trim();

function assert(condition,message){if(!condition)throw new Error(message);}
function protectionHeaders(){
  const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
  return secret?{"x-vercel-protection-bypass":secret}:{};
}
function cookieHeaders(cookie){return{...protectionHeaders(),cookie};}
async function json(response,code){
  const body=await response.json().catch(()=>null);
  assert(body&&typeof body==="object",`${code}_RESPONSE_NOT_JSON`);
  return body;
}
async function callGet(cookie,resourceKey,operationId,path,validate){
  const correlationId=crypto.randomUUID();
  const response=await fetch(`${base}${path}`,{
    method:"GET",cache:"no-store",
    headers:{...cookieHeaders(cookie),"x-correlation-id":correlationId},
  });
  const body=await json(response,operationId);
  assert(response.status===200,`${operationId}_HTTP_${response.status}`);
  assert(body?.ok===true,`${operationId}_BODY_NOT_OK`);
  assert(body?.correlation_id===correlationId,`${operationId}_CORRELATION_MISMATCH`);
  validate(body.value);
  process.stdout.write(`FORMAL_RESOURCE_ACCEPTANCE_PASS resource_key=${resourceKey} operation_id=${operationId} correlation_id=${correlationId} method=GET path=${path}\n`);
  return body.value;
}

assert(email&&password,"FORMAL_READONLY_ACCEPTANCE_CREDENTIAL_NOT_CONFIGURED");
assert(routeDecisionId,"FORMAL_READONLY_ROUTE_DECISION_ID_REQUIRED");

const loginCorrelation=crypto.randomUUID();
const login=await fetch(`${base}/v1/identity/session`,{
  method:"POST",cache:"no-store",redirect:"manual",
  headers:{...protectionHeaders(),"content-type":"application/json","x-correlation-id":loginCorrelation},
  body:JSON.stringify({email,password}),
});
const loginBody=await json(login,"FORMAL_LOGIN");
assert(login.status===200,"FORMAL_LOGIN_HTTP_"+login.status);
assert(loginBody?.ok===true&&loginBody?.logged_in===true,"FORMAL_LOGIN_INVALID");
const setCookie=login.headers.get("set-cookie")??"";
const cookie=setCookie.split(";")[0].trim();
assert(cookie.startsWith("acpos_session="),"FORMAL_LOGIN_SESSION_COOKIE_MISSING");

const profiles=await callGet(
  cookie,
  "control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-LIST-PROFILES",
  "listProviderModelProfiles",
  "/v1/aiapi/provider-profiles",
  (value)=>assert(Array.isArray(value?.profiles)&&value.profiles.length>0,"FORMAL_PROVIDER_PROFILE_LIST_EMPTY"),
);
const profileId=String(profiles.profiles[0]?.profile_id??"").trim();
assert(profileId,"FORMAL_PROVIDER_PROFILE_ID_MISSING");

await callGet(
  cookie,
  "control:CTRL-ADMIN-AIAPI-06-PROVIDER-MODEL-PROFILES-VIEW-PROFILE",
  "getProviderModelProfile",
  `/v1/aiapi/provider-profiles/${encodeURIComponent(profileId)}`,
  (value)=>assert(String(value?.profile_id??"")===profileId,"FORMAL_PROVIDER_PROFILE_READBACK_MISMATCH"),
);

await callGet(
  cookie,
  "control:CTRL-ADMIN-AIAPI-05-PROVIDER-CANDIDATE-GROUPS-VIEW-QUARANTINE",
  "getProviderQuarantine",
  "/v1/aiapi/quarantine",
  (value)=>assert(Array.isArray(value?.quarantine),"FORMAL_PROVIDER_QUARANTINE_SHAPE_INVALID"),
);

await callGet(
  cookie,
  "control:CTRL-ADMIN-AIAPI-08-ROUTE-SIMULATION-VIEW-ROUTE-DECISION",
  "getProviderRouteDecision",
  `/v1/aiapi/routes/${encodeURIComponent(routeDecisionId)}`,
  (value)=>assert(String(value?.id??"")===routeDecisionId,"FORMAL_ROUTE_DECISION_READBACK_MISMATCH"),
);

const logout=await fetch(`${base}/v1/identity/session`,{
  method:"DELETE",cache:"no-store",headers:cookieHeaders(cookie)
});
const logoutBody=await json(logout,"FORMAL_LOGOUT");
assert(logout.status===200&&logoutBody?.ok===true&&logoutBody?.logged_in===false,"FORMAL_LOGOUT_FAILED");
process.stdout.write("PRODUCTION_FORMAL_READONLY_ACCEPTANCE_PASS resources=4 mutations=0 external_provider_calls=0\n");
