import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();
const expected=[
  {control_id:"SYS-01-BTN-CANDIDATE-CREATE",action_uid:"ACT-CANDIDATE-CREATE",operation_id:"createCandidate"},
  {control_id:"SYS-01-BTN-CR-CREATE",action_uid:"ACT-CR-CREATE",operation_id:"createChangeRequest"},
];
function assert(v,m){if(!v)throw new Error(m)}
function headers(){const s=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return s?{"x-vercel-protection-bypass":s}:{}}
function rec(v){return v&&typeof v==="object"&&!Array.isArray(v)?v:{}}
assert(base&&email&&password&&expectedSha,"SYS_PREREQ_ENV_MISSING");
const health=await fetch(`${base}/health`,{cache:"no-store",headers:headers()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,"SYS_PREREQ_HEALTH_FAILED");
assert(healthBody?.environment==="production","SYS_PREREQ_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`SYS_PREREQ_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);
const browser=await chromium.launch({headless:true});
let context;
try{
  context=await browser.newContext({extraHTTPHeaders:headers()});
  const login=await context.request.post(`${base}/v1/identity/session`,{headers:{"content-type":"application/json","x-correlation-id":crypto.randomUUID()},data:{email,password}});
  const loginBody=await login.json().catch(()=>null);
  assert(login.status()===200&&loginBody?.ok===true&&loginBody?.logged_in===true,"SYS_PREREQ_LOGIN_FAILED");
  const projection=await context.request.get(`${base}/v1/ui-projections/admin%3ASYS-01`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const projectionBody=await projection.json().catch(()=>null);
  assert(projection.status()===200,`SYS_PREREQ_PROJECTION_HTTP_${projection.status()}`);
  const pv=rec(rec(projectionBody).value??projectionBody);
  assert(!pv.test_metadata,"SYS_PREREQ_SYNTHETIC_FORBIDDEN");
  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const mutationRequests=[];
  page.on("request",request=>{const u=new URL(request.url());if(u.origin===new URL(base).origin&&u.pathname.startsWith('/v1/system/changes')&&request.method()!=="GET")mutationRequests.push(`${request.method()} ${u.pathname}`)});
  const nav=await page.goto(`${base}/admin/system`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`SYS_PREREQ_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="admin:SYS-01"]');
  await root.waitFor({state:"visible",timeout:15000});
  const controls=[];
  for(const e of expected){
    const n=page.locator(`#${e.control_id}`);
    await n.waitFor({state:"visible",timeout:10000});
    const actionUid=await n.getAttribute("data-action-uid");
    const serviceOperation=await n.getAttribute("data-service-operation");
    assert(actionUid===e.action_uid,`SYS_PREREQ_ACTION_MISMATCH_${e.control_id}_${actionUid}`);
    assert(serviceOperation===e.operation_id,`SYS_PREREQ_OPERATION_MISMATCH_${e.control_id}_${serviceOperation}`);
    controls.push({control_id:e.control_id,action_uid:actionUid,operation_id:serviceOperation,enabled:await n.isEnabled(),disabled_reason:await n.getAttribute("data-disabled-reason"),gate_uid:await n.getAttribute("data-gate-uid"),permission_uid:await n.getAttribute("data-permission-uid")});
  }
  assert(mutationRequests.length===0,`SYS_PREREQ_MUTATION_DETECTED_${mutationRequests.join('|')}`);
  const values=rec(pv.values);
  console.log(`SYS_PREREQUISITE_DIAGNOSTIC ${JSON.stringify({production_release_sha:expectedSha,projection_http:projection.status(),page_state:pv.page_state??await root.getAttribute('data-page-state'),system_change_id:pv.system_change_id??null,candidate_ref:values.candidate_ref??null,conversation_id:pv.conversation_id??null,controls,mutation_count:0})}`);
  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200&&logoutBody?.ok===true&&logoutBody?.logged_in===false,"SYS_PREREQ_LOGOUT_FAILED");
}finally{if(context)await context.close().catch(()=>{});await browser.close();}
