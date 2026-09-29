import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();

const targets=[
  ["CTRL-ADMIN-ERP-01-CONNECTOR-OPEN","ERP-01-FLD-CONN-CONNECTOR-ID","connector"],
  ["CTRL-ADMIN-ERP-01-SNAPSHOT-OPEN","ERP-01-FLD-SNAPSHOT","finance"],
  ["CTRL-ADMIN-ERP-01-FRESHNESS-OPEN","ERP-01-FLD-FRESHNESS","finance"],
  ["CTRL-ADMIN-ERP-01-CURRENCY-TIMEZONE-OPEN","ERP-01-FLD-SYNC-CURRENCY-TIMEZONE","sync"],
  ["CTRL-ADMIN-ERP-01-COMPLETENESS-OPEN","ERP-01-FLD-SYNC-COMPLETENESS","sync"],
  ["CTRL-ADMIN-ERP-01-FAILURE-OPEN","ERP-01-FLD-SYNC-FAILURE-ID","sync"],
  ["CTRL-ADMIN-ERP-01-AUDIT-OPEN","ERP-01-FLD-AUDIT-REF","rail"],
  ["CTRL-ADMIN-ERP-02-COST-OPEN","ERP-01-FLD-FIN-COST","finance"],
  ["CTRL-ADMIN-ERP-02-REVENUE-OPEN","ERP-01-FLD-FIN-REVENUE","finance"],
  ["CTRL-ADMIN-ERP-02-CASHFLOW-OPEN","ERP-01-FLD-FIN-CASHFLOW","finance"],
  ["CTRL-ADMIN-ERP-02-CAPACITY-OPEN","ERP-01-FLD-FIN-CAPACITY","finance"],
  ["CTRL-ADMIN-ERP-02-FORECAST-OPEN","ERP-01-FLD-FIN-FORECAST","finance"],
  ["CTRL-ADMIN-ERP-02-GUARDRAILS-OPEN","ERP-01-FLD-FIN-GUARDRAILS","finance"],
  ["CTRL-ADMIN-ERP-02-RECOMMENDATION-BOUNDARY-OPEN","ERP-01-FLD-FIN-RECOMMENDATION-BOUNDARY","finance"],
];
const tab={finance:"ERP-01-BTN-TAB-FINANCE",connector:"ERP-01-BTN-TAB-CONNECTOR",sync:"ERP-01-BTN-TAB-SYNC"};
function assert(value,message){if(!value)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}

assert(email&&password,"GATE25_ERP_PRODUCTION_CREDENTIAL_NOT_CONFIGURED");
assert(expectedSha,"GATE25_ERP_EXPECTED_RELEASE_SHA_NOT_CONFIGURED");
assert(targets.length===14,"GATE25_ERP_TARGET_COUNT_INVALID");

const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,`GATE25_ERP_HEALTH_HTTP_${health.status}`);
assert(healthBody?.environment==="production","GATE25_ERP_ENVIRONMENT_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`GATE25_ERP_RELEASE_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);

const browser=await chromium.launch({headless:true});
let context;
const evidence=[];
try{
  context=await browser.newContext({extraHTTPHeaders:protectionHeaders()});
  const login=await context.request.post(`${base}/v1/identity/session`,{
    headers:{"content-type":"application/json","x-correlation-id":crypto.randomUUID()},
    data:{email,password},
  });
  const loginBody=await login.json().catch(()=>null);
  assert(login.status()===200,`GATE25_ERP_LOGIN_HTTP_${login.status()}`);
  assert(loginBody?.ok===true&&loginBody?.logged_in===true,"GATE25_ERP_LOGIN_BODY_INVALID");

  const projection=await context.request.get(`${base}/v1/ui-projections/admin%3AERP-01`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const projectionBody=await projection.json().catch(()=>null);
  assert(projection.status()===200,`GATE25_ERP_PROJECTION_HTTP_${projection.status()}`);
  assert(!projectionBody?.test_metadata,"GATE25_ERP_SYNTHETIC_PROJECTION_FORBIDDEN");

  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const runtimeErrors=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  const nav=await page.goto(`${base}/admin/erp`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`GATE25_ERP_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="admin:ERP-01"]');
  await root.waitFor({state:"visible",timeout:15000});
  await page.waitForFunction(()=>document.querySelector('[data-page-uid="admin:ERP-01"]')?.getAttribute("data-page-state")!=="LOADING",{timeout:15000});
  const pageState=await root.getAttribute("data-page-state");
  assert(pageState!=="ERROR",`GATE25_ERP_PAGE_STATE_${pageState}`);

  let active="finance";
  for(const [sourceId,currentId,view] of targets){
    if(view!=="rail"&&active!==view){
      const button=page.locator(`[data-control-id="${tab[view]}"]`).first();
      await button.waitFor({state:"visible",timeout:10000});
      assert(await button.isEnabled(),`GATE25_ERP_TAB_DISABLED_${view}`);
      await button.click();
      active=view;
    }
    const node=page.locator(`[data-control-id="${currentId}"]`).first();
    await node.waitFor({state:"visible",timeout:10000});
    const text=((await node.textContent())??"").trim();
    assert(text.length>0,`GATE25_ERP_CURRENT_CONTROL_EMPTY_${currentId}`);
    evidence.push({
      resource_key:`control:${sourceId}`,
      source_control_id:sourceId,
      current_control_id:currentId,
      current_view:view,
      route:"/admin/erp",
      projection_http:projection.status(),
      page_state:pageState,
      current_control_visible:true,
      synthetic_projection:false,
      outcome:"PASS",
    });
  }
  assert(runtimeErrors.length===0,`GATE25_ERP_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  assert(evidence.length===14,"GATE25_ERP_EVIDENCE_COUNT_INVALID");

  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200,`GATE25_ERP_LOGOUT_HTTP_${logout.status()}`);
  assert(logoutBody?.ok===true&&logoutBody?.logged_in===false,"GATE25_ERP_LOGOUT_BODY_INVALID");

  process.stdout.write(`GATE25_ERP_READONLY_PRODUCTION_PASS resources=${evidence.length} release_sha=${expectedSha}\n`);
  process.stdout.write(`GATE25_ERP_READONLY_PRODUCTION_EVIDENCE ${JSON.stringify(evidence)}\n`);
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
