import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();
const controls=[
  {source_id:"CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE",operation_id:"configureGovernedResource"},
  {source_id:"CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE",operation_id:"approveGovernedResource"},
];
function assert(value,message){if(!value)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}
function asObject(value){return value&&typeof value==="object"&&!Array.isArray(value)?value:null}
function unwrap(body){const root=asObject(body)??{};return asObject(root.value)??root}
function hasRealCriteria(value){
  const root=unwrap(value);
  const values=asObject(root.values)??root;
  const criteria=values.criteria_versions;
  if(Array.isArray(criteria))return criteria.length>0;
  if(criteria&&typeof criteria==="object")return Object.keys(criteria).length>0;
  if(typeof criteria==="string")return criteria.trim()!==""&&criteria.trim()!=="—";
  return criteria!==null&&criteria!==undefined;
}
assert(base&&email&&password&&expectedSha,"SG02_DIAGNOSTIC_ENV_MISSING");
const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,"SG02_DIAGNOSTIC_HEALTH_FAILED");
assert(healthBody?.environment==="production","SG02_DIAGNOSTIC_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`SG02_DIAGNOSTIC_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);

const browser=await chromium.launch({headless:true});
let context;
try{
  context=await browser.newContext({extraHTTPHeaders:protectionHeaders()});
  const login=await context.request.post(`${base}/v1/identity/session`,{headers:{"content-type":"application/json","x-correlation-id":crypto.randomUUID()},data:{email,password}});
  const loginBody=await login.json().catch(()=>null);
  assert(login.status()===200&&loginBody?.ok===true&&loginBody?.logged_in===true,"SG02_DIAGNOSTIC_LOGIN_FAILED");
  const projection=await context.request.get(`${base}/v1/ui-projections/admin%3ASG-02`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const projectionBody=await projection.json().catch(()=>null);
  assert(projection.status()===200,`SG02_DIAGNOSTIC_PROJECTION_HTTP_${projection.status()}`);
  const projectionValue=unwrap(projectionBody);
  assert(!projectionValue.test_metadata,"SG02_DIAGNOSTIC_SYNTHETIC_FORBIDDEN");

  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const runtimeErrors=[];
  const effectful=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  page.on("request",request=>{
    const url=new URL(request.url());
    if(url.origin===new URL(base).origin&&request.method()!=="GET"&&url.pathname!=="/v1/identity/session")effectful.push(`${request.method()} ${url.pathname}`);
  });
  const nav=await page.goto(`${base}/admin/qa-criteria`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`SG02_DIAGNOSTIC_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="admin:SG-02"]');
  await root.waitFor({state:"visible",timeout:15000});
  await page.waitForFunction(()=>document.querySelector('[data-page-uid="admin:SG-02"]')?.getAttribute("data-page-state")!=="LOADING",{timeout:15000});
  const result=[];
  for(const expected of controls){
    const node=page.locator(`[data-control-id="${expected.source_id}"]`).first();
    await node.waitFor({state:"visible",timeout:10000});
    result.push({
      control_id:expected.source_id,
      enabled:await node.isEnabled(),
      disabled_reason:await node.getAttribute("data-disabled-reason"),
      operation_id:await node.getAttribute("data-operation-id"),
      method_path:await node.getAttribute("data-method-path"),
    });
  }
  assert(effectful.length===0,`SG02_DIAGNOSTIC_EFFECTFUL_REQUEST_${effectful.join("|")}`);
  assert(runtimeErrors.length===0,`SG02_DIAGNOSTIC_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  for(const c of result){
    const expected=controls.find(x=>x.source_id===c.control_id);
    assert(c.enabled===false,`SG02_DIAGNOSTIC_CONTROL_UNEXPECTEDLY_ENABLED_${c.control_id}`);
    assert(c.disabled_reason===`SG02_CONTROL_GATE_BLOCKED:${c.control_id}`,`SG02_DIAGNOSTIC_DISABLED_REASON_${c.control_id}_${c.disabled_reason}`);
    assert(c.operation_id===expected.operation_id,`SG02_DIAGNOSTIC_OPERATION_MISMATCH_${c.control_id}`);
  }
  console.log(`SG02_EFFECTFUL_CONTROL_DIAGNOSTIC ${JSON.stringify({production_release_sha:expectedSha,projection_http:projection.status(),page_state:await root.getAttribute("data-page-state"),real_criteria_present:hasRealCriteria(projectionBody),controls:result,mutation_count:0})}`);
  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200&&logoutBody?.ok===true&&logoutBody?.logged_in===false,"SG02_DIAGNOSTIC_LOGOUT_FAILED");
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
