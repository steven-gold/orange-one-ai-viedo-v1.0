import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();
const targets=[
  ["DEV-01-BTN-STAGE-2","directory","DEV-01-SEC-04"],
  ["DEV-01-BTN-STAGE-3","message","DEV-01-SEC-05"],
  ["DEV-01-BTN-STAGE-4","campaign","DEV-01-SEC-06"],
  ["DEV-01-BTN-STAGE-5","delivery","DEV-01-SEC-07"],
  ["DEV-01-BTN-STAGE-1","discovery","DEV-01-SEC-03"],
];
function assert(condition,message){if(!condition)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}
assert(email&&password,"GATE25_DEV_PRODUCTION_CREDENTIAL_NOT_CONFIGURED");
assert(expectedSha,"GATE25_DEV_EXPECTED_RELEASE_SHA_NOT_CONFIGURED");
assert(targets.length===5,"GATE25_DEV_TARGET_COUNT_INVALID");
const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,`GATE25_DEV_HEALTH_HTTP_${health.status}`);
assert(healthBody?.environment==="production","GATE25_DEV_ENVIRONMENT_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`GATE25_DEV_RELEASE_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);
const browser=await chromium.launch({headless:true});
let context;
try{
  context=await browser.newContext({extraHTTPHeaders:protectionHeaders()});
  const login=await context.request.post(`${base}/v1/identity/session`,{headers:{"content-type":"application/json","x-correlation-id":crypto.randomUUID()},data:{email,password}});
  const loginBody=await login.json().catch(()=>null);
  assert(login.status()===200,`GATE25_DEV_LOGIN_HTTP_${login.status()}`);
  assert(loginBody?.ok===true&&loginBody?.logged_in===true,"GATE25_DEV_LOGIN_BODY_INVALID");
  const page=await context.newPage({viewport:{width:1440,height:1200}});
  const runtimeErrors=[];
  const effectfulRequests=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  page.on("request",request=>{if(["POST","PATCH","PUT","DELETE"].includes(request.method()))effectfulRequests.push(`${request.method()} ${new URL(request.url()).pathname}`)});
  const nav=await page.goto(`${base}/admin/dev`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`GATE25_DEV_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="admin:DEV-01"]');
  await root.waitFor({state:"attached",timeout:15000});
  await page.waitForFunction(()=>document.querySelector('[data-page-uid="admin:DEV-01"]')?.getAttribute("data-projection-status")!=="LOADING",{timeout:15000});
  assert(await root.getAttribute("data-projection-status")==="READY","GATE25_DEV_PROJECTION_NOT_READY");
  assert(await root.getAttribute("data-page-gate-ready")==="true","GATE25_DEV_PAGE_GATE_NOT_READY");
  const evidence=[];
  for(const [controlId,stage,sectionId] of targets){
    const button=page.locator(`[data-control-id="${controlId}"]`).first();
    await button.waitFor({state:"visible",timeout:10000});
    assert(await button.isEnabled(),`GATE25_DEV_CONTROL_DISABLED_${controlId}`);
    assert(await button.getAttribute("data-effect-type")==="UI_CONTEXT_STATE",`GATE25_DEV_EFFECT_TYPE_${controlId}`);
    assert(await button.getAttribute("data-runtime-binding")==="CLIENT_STATE_OR_VIEW_NO_API_REQUIRED",`GATE25_DEV_RUNTIME_BINDING_${controlId}`);
    assert((await button.getAttribute("data-method-path"))===null,`GATE25_DEV_METHOD_PATH_PRESENT_${controlId}`);
    const beforeEffectful=effectfulRequests.length;
    await button.click();
    await page.waitForFunction(expected=>document.querySelector('[data-page-uid="admin:DEV-01"]')?.getAttribute("data-active-stage")===expected,stage,{timeout:5000});
    assert(effectfulRequests.length===beforeEffectful,`GATE25_DEV_EFFECTFUL_REQUEST_${controlId}_${effectfulRequests.slice(beforeEffectful).join("|")}`);
    const section=page.locator(`[data-section-id="${sectionId}"]`).first();
    await section.waitFor({state:"visible",timeout:5000});
    evidence.push({resource_key:`control:${controlId}`,control_id:controlId,route:"/admin/dev",stage,section_id:sectionId,effect_type:"UI_CONTEXT_STATE",runtime_binding:"CLIENT_STATE_OR_VIEW_NO_API_REQUIRED",effectful_request_count:0,outcome:"PASS"});
  }
  assert(runtimeErrors.length===0,`GATE25_DEV_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  assert(effectfulRequests.length===0,`GATE25_DEV_EFFECTFUL_REQUESTS_${effectfulRequests.join("|")}`);
  assert(evidence.length===5,"GATE25_DEV_EVIDENCE_COUNT_INVALID");
  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200,`GATE25_DEV_LOGOUT_HTTP_${logout.status()}`);
  assert(logoutBody?.ok===true&&logoutBody?.logged_in===false,"GATE25_DEV_LOGOUT_BODY_INVALID");
  process.stdout.write(`GATE25_DEV_STAGE_PRODUCTION_PASS resources=${evidence.length} effectful_requests=0 release_sha=${expectedSha}\n`);
  process.stdout.write(`GATE25_DEV_STAGE_PRODUCTION_EVIDENCE ${JSON.stringify(evidence)}\n`);
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
