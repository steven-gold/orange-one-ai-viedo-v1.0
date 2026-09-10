import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();
const controls=["ERP-01-BTN-FACTPACK","ERP-01-BTN-GUARDRAILS","ERP-01-BTN-FORECAST"];

function assert(value,message){if(!value)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}
function safeProjection(body){
  const root=body&&typeof body==="object"?body:{};
  const value=root.value&&typeof root.value==="object"?root.value:root;
  const gates=value.gate_state&&typeof value.gate_state==="object"?value.gate_state:{};
  return {
    page_state:typeof value.page_state==="string"?value.page_state:null,
    finance_gate:gates["ERP-01-GATE-FINANCE"]===true,
    page_gate:gates["ERP-01-GATE-PAGE"]===true,
    connector_read_gate:gates["ERP-01-GATE-CONNECTOR-READ"]===true,
    sync_read_gate:gates["ERP-01-GATE-SYNC-READ"]===true,
    synthetic:Boolean(value.test_metadata),
  };
}

assert(base&&email&&password&&expectedSha,"ERP_FINANCE_GATE_DIAGNOSTIC_ENV_MISSING");
const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,"ERP_FINANCE_GATE_DIAGNOSTIC_HEALTH_FAILED");
assert(healthBody?.environment==="production","ERP_FINANCE_GATE_DIAGNOSTIC_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`ERP_FINANCE_GATE_DIAGNOSTIC_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);

const browser=await chromium.launch({headless:true});
let context;
try{
  context=await browser.newContext({extraHTTPHeaders:protectionHeaders()});
  const login=await context.request.post(`${base}/v1/identity/session`,{
    headers:{"content-type":"application/json","x-correlation-id":crypto.randomUUID()},
    data:{email,password},
  });
  const loginBody=await login.json().catch(()=>null);
  assert(login.status()===200&&loginBody?.ok===true&&loginBody?.logged_in===true,"ERP_FINANCE_GATE_DIAGNOSTIC_LOGIN_FAILED");

  const projection=await context.request.get(`${base}/v1/ui-projections/admin%3AERP-01`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const projectionBody=await projection.json().catch(()=>null);
  assert(projection.status()===200,`ERP_FINANCE_GATE_DIAGNOSTIC_PROJECTION_HTTP_${projection.status()}`);
  const projectionSafe=safeProjection(projectionBody);
  assert(!projectionSafe.synthetic,"ERP_FINANCE_GATE_DIAGNOSTIC_SYNTHETIC_FORBIDDEN");

  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const runtimeErrors=[];
  const effectful=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  page.on("request",request=>{
    const url=new URL(request.url());
    if(url.origin===new URL(base).origin&&request.method()!=="GET"&&url.pathname!=="/v1/identity/session") effectful.push(`${request.method()} ${url.pathname}`);
  });
  const nav=await page.goto(`${base}/admin/erp`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`ERP_FINANCE_GATE_DIAGNOSTIC_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="admin:ERP-01"]');
  await root.waitFor({state:"visible",timeout:15000});
  await page.waitForFunction(()=>document.querySelector('[data-page-uid="admin:ERP-01"]')?.getAttribute("data-page-state")!=="LOADING",{timeout:15000});
  const pageState=await root.getAttribute("data-page-state");

  const results=[];
  for(const controlId of controls){
    const node=page.locator(`[data-control-id="${controlId}"]`).first();
    await node.waitFor({state:"visible",timeout:10000});
    results.push({
      control_id:controlId,
      enabled:await node.isEnabled(),
      disabled_reason:await node.getAttribute("data-disabled-reason"),
      action_uid:await node.getAttribute("data-action-uid"),
      gate_uid:await node.getAttribute("data-gate-uid"),
      permission_uid:await node.getAttribute("data-permission-uid"),
    });
  }
  assert(effectful.length===0,`ERP_FINANCE_GATE_DIAGNOSTIC_EFFECTFUL_REQUEST_${effectful.join("|")}`);
  assert(runtimeErrors.length===0,`ERP_FINANCE_GATE_DIAGNOSTIC_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  console.log(`ERP_FINANCE_GATE_DIAGNOSTIC ${JSON.stringify({production_release_sha:expectedSha,projection_http:projection.status(),projection:projectionSafe,page_state:pageState,controls:results,mutation_count:0})}`);

  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200&&logoutBody?.ok===true&&logoutBody?.logged_in===false,"ERP_FINANCE_GATE_DIAGNOSTIC_LOGOUT_FAILED");
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
