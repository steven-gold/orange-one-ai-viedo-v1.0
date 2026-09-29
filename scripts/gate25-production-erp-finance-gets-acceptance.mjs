import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();

const targets=[
  {resource_key:"control:CTRL-ADMIN-ERP-02-ACT-01-ERP-FINANCE-GET-FACTPACK",control_id:"ERP-01-BTN-FACTPACK",path:"/v1/erp/finance/fact-pack",operation_id:"getERPFinanceFactPack"},
  {resource_key:"control:CTRL-ADMIN-ERP-02-ACT-02-ERP-CAPACITY-GET-GUARDRAILS",control_id:"ERP-01-BTN-GUARDRAILS",path:"/v1/erp/capacity/guardrails",operation_id:"getERPCapacityGuardrails"},
  {resource_key:"control:CTRL-ADMIN-ERP-02-ACT-03-ERP-FORECAST-GET",control_id:"ERP-01-BTN-FORECAST",path:"/v1/erp/forecasts",operation_id:"getERPForecast"},
];

function assert(value,message){if(!value)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}

assert(base&&email&&password&&expectedSha,"GATE25_ERP_FINANCE_GET_REQUIRED_ENV_MISSING");
assert(targets.length===3,"GATE25_ERP_FINANCE_GET_TARGET_COUNT_INVALID");

const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,`GATE25_ERP_FINANCE_GET_HEALTH_HTTP_${health.status}`);
assert(healthBody?.environment==="production","GATE25_ERP_FINANCE_GET_ENVIRONMENT_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`GATE25_ERP_FINANCE_GET_RELEASE_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);

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
  assert(login.status()===200,`GATE25_ERP_FINANCE_GET_LOGIN_HTTP_${login.status()}`);
  assert(loginBody?.ok===true&&loginBody?.logged_in===true,"GATE25_ERP_FINANCE_GET_LOGIN_BODY_INVALID");

  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const runtimeErrors=[];
  const forbiddenEffectful=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  page.on("request",request=>{
    const url=new URL(request.url());
    if(url.origin===new URL(base).origin && request.method()!=="GET" && url.pathname!=="/v1/identity/session"){
      forbiddenEffectful.push(`${request.method()} ${url.pathname}`);
    }
  });

  const nav=await page.goto(`${base}/admin/erp`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`GATE25_ERP_FINANCE_GET_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="admin:ERP-01"]');
  await root.waitFor({state:"visible",timeout:15000});
  await page.waitForFunction(()=>document.querySelector('[data-page-uid="admin:ERP-01"]')?.getAttribute("data-page-state")!=="LOADING",{timeout:15000});
  const pageState=await root.getAttribute("data-page-state");
  assert(pageState!=="ERROR",`GATE25_ERP_FINANCE_GET_PAGE_STATE_${pageState}`);

  const financeTab=page.locator('[data-control-id="ERP-01-BTN-TAB-FINANCE"]').first();
  await financeTab.waitFor({state:"visible",timeout:10000});
  assert(await financeTab.isEnabled(),"GATE25_ERP_FINANCE_TAB_DISABLED");
  await financeTab.click();

  for(const target of targets){
    const button=page.locator(`[data-control-id="${target.control_id}"]`).first();
    await button.waitFor({state:"visible",timeout:10000});
    assert(await button.isEnabled(),`GATE25_ERP_FINANCE_GET_CONTROL_DISABLED_${target.control_id}`);
    const responsePromise=page.waitForResponse(response=>{
      const url=new URL(response.url());
      return url.pathname===target.path && response.request().method()==="GET";
    },{timeout:15000});
    await button.click();
    const response=await responsePromise;
    const body=await response.json().catch(()=>null);
    assert(response.status()===200,`GATE25_ERP_FINANCE_GET_HTTP_${target.control_id}_${response.status()}`);
    assert(body!==null,`GATE25_ERP_FINANCE_GET_BODY_INVALID_${target.control_id}`);
    evidence.push({
      resource_key:target.resource_key,
      control_id:target.control_id,
      operation_id:target.operation_id,
      method:"GET",
      path:target.path,
      http_status:response.status(),
      page_state:pageState,
      runtime_control_enabled:true,
      outcome:"PASS",
    });
  }

  assert(runtimeErrors.length===0,`GATE25_ERP_FINANCE_GET_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  assert(forbiddenEffectful.length===0,`GATE25_ERP_FINANCE_GET_EFFECTFUL_REQUEST_DETECTED_${forbiddenEffectful.join("|")}`);
  assert(evidence.length===3,"GATE25_ERP_FINANCE_GET_EVIDENCE_COUNT_INVALID");

  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200,`GATE25_ERP_FINANCE_GET_LOGOUT_HTTP_${logout.status()}`);
  assert(logoutBody?.ok===true&&logoutBody?.logged_in===false,"GATE25_ERP_FINANCE_GET_LOGOUT_BODY_INVALID");

  process.stdout.write(`GATE25_ERP_FINANCE_GET_PRODUCTION_PASS resources=${evidence.length} release_sha=${expectedSha}\n`);
  process.stdout.write(`GATE25_ERP_FINANCE_GET_PRODUCTION_EVIDENCE ${JSON.stringify(evidence)}\n`);
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
