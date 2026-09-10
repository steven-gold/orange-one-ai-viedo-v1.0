import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();

const targets=[
  ["CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN","criteria_table"],
  ["CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN","dimension_library"],
  ["CTRL-ADMIN-SG-02-THRESHOLDS-OPEN","thresholds"],
  ["CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN","department_mapping"],
  ["CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN","required_checks"],
  ["CTRL-ADMIN-SG-02-GATE-POLICY-OPEN","gate_policy"],
  ["CTRL-ADMIN-SG-02-APPROVAL-OPEN","approval"],
  ["CTRL-ADMIN-SG-02-IMPACT-OPEN","impact"],
  ["CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN","governance"],
];

function assert(condition,message){if(!condition)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}

assert(email&&password,"GATE25_SG02_PRODUCTION_CREDENTIAL_NOT_CONFIGURED");
assert(expectedSha,"GATE25_SG02_EXPECTED_RELEASE_SHA_NOT_CONFIGURED");
assert(targets.length===9,"GATE25_SG02_TARGET_COUNT_INVALID");

const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,`GATE25_SG02_HEALTH_HTTP_${health.status}`);
assert(healthBody?.environment==="production","GATE25_SG02_ENVIRONMENT_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`GATE25_SG02_RELEASE_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);

const browser=await chromium.launch({headless:true});
const evidence=[];
let context;
try{
  context=await browser.newContext({extraHTTPHeaders:protectionHeaders()});
  const login=await context.request.post(`${base}/v1/identity/session`,{
    headers:{"content-type":"application/json","x-correlation-id":crypto.randomUUID()},
    data:{email,password},
  });
  const loginBody=await login.json().catch(()=>null);
  assert(login.status()===200,`GATE25_SG02_LOGIN_HTTP_${login.status()}`);
  assert(loginBody?.ok===true&&loginBody?.logged_in===true,"GATE25_SG02_LOGIN_BODY_INVALID");

  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const runtimeErrors=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  const projectionPromise=page.waitForResponse(r=>decodeURIComponent(new URL(r.url()).pathname)==="/v1/ui-projections/admin:SG-02"&&r.request().method()==="GET",{timeout:15000});
  const nav=await page.goto(`${base}/admin/qa-criteria`,{waitUntil:"domcontentloaded",timeout:45000});
  assert(nav?.ok(),`GATE25_SG02_NAV_HTTP_${nav?.status()}`);
  const projectionResponse=await projectionPromise;
  assert(projectionResponse.status()===200,`GATE25_SG02_PROJECTION_HTTP_${projectionResponse.status()}`);
  assert(Boolean(projectionResponse.headers()["x-correlation-id"]),"GATE25_SG02_PROJECTION_CORRELATION_ID_MISSING");
  const root=page.locator('[data-page-uid="admin:SG-02"]');
  await root.waitFor({state:"attached",timeout:15000});
  await page.waitForFunction(()=>{
    const state=document.querySelector('[data-page-uid="admin:SG-02"]')?.getAttribute("data-page-state");
    return Boolean(state&&state!=="LOADING");
  },{timeout:15000});
  const pageState=await root.getAttribute("data-page-state");
  assert(pageState!=="ERROR",`GATE25_SG02_PAGE_STATE_${pageState}`);

  for(const [controlId,drawerKey] of targets){
    const button=page.locator(`[data-control-id="${controlId}"]`).first();
    await button.waitFor({state:"visible",timeout:10000});
    assert(await button.isEnabled(),`GATE25_SG02_CONTROL_DISABLED_${controlId}`);
    assert(await button.getAttribute("data-operation-id")==="getUiProjection",`GATE25_SG02_OPERATION_NOT_READONLY_${controlId}`);
    await button.click();
    const drawer=page.locator('[data-detail-drawer="SG-02"]').first();
    await drawer.waitFor({state:"visible",timeout:10000});
    const heading=(await drawer.locator("h3").first().textContent()??"").trim();
    assert(Boolean(heading),`GATE25_SG02_DRAWER_HEADING_EMPTY_${controlId}`);
    assert((await root.getAttribute("data-page-state"))!=="ERROR",`GATE25_SG02_RUNTIME_STATE_ERROR_${controlId}`);
    evidence.push({
      resource_key:`control:${controlId}`,
      control_id:controlId,
      drawer_key:drawerKey,
      route:"/admin/qa-criteria",
      projection_http:projectionResponse.status(),
      page_state:pageState,
      drawer_visible:true,
      heading_present:true,
      operation_id:"getUiProjection",
      outcome:"PASS",
    });
    const close=drawer.locator("button").first();
    await close.click();
    await drawer.waitFor({state:"detached",timeout:10000});
  }
  assert(runtimeErrors.length===0,`GATE25_SG02_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  assert(evidence.length===9,"GATE25_SG02_EVIDENCE_COUNT_INVALID");

  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200,`GATE25_SG02_LOGOUT_HTTP_${logout.status()}`);
  assert(logoutBody?.ok===true&&logoutBody?.logged_in===false,"GATE25_SG02_LOGOUT_BODY_INVALID");

  process.stdout.write(`GATE25_SG02_READONLY_PRODUCTION_PASS resources=${evidence.length} release_sha=${expectedSha}\n`);
  process.stdout.write(`GATE25_SG02_READONLY_PRODUCTION_EVIDENCE ${JSON.stringify(evidence)}\n`);
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
