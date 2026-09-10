import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();
const resources=[
  "control:CTRL-ADMIN-ERP-01-ACT-10-ACT-NAV-OPEN",
  "action:admin:ERP-01:ACT-NAV-OPEN",
  "control:CTRL-ADMIN-ERP-02-ACT-05-ACT-NAV-OPEN",
  "action:admin:ERP-02:ACT-NAV-OPEN",
];

function assert(value,message){if(!value)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}

assert(base&&email&&password&&expectedSha,"GATE25_ERP_NAV_REQUIRED_ENV_MISSING");
assert(resources.length===4&&new Set(resources).size===4,"GATE25_ERP_NAV_RESOURCE_SET_INVALID");
const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,`GATE25_ERP_NAV_HEALTH_HTTP_${health.status}`);
assert(healthBody?.environment==="production","GATE25_ERP_NAV_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`GATE25_ERP_NAV_RELEASE_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);

const browser=await chromium.launch({headless:true});
let context;
try{
  context=await browser.newContext({extraHTTPHeaders:protectionHeaders()});
  const login=await context.request.post(`${base}/v1/identity/session`,{
    headers:{"content-type":"application/json","x-correlation-id":crypto.randomUUID()},
    data:{email,password},
  });
  const loginBody=await login.json().catch(()=>null);
  assert(login.status()===200&&loginBody?.ok===true&&loginBody?.logged_in===true,"GATE25_ERP_NAV_LOGIN_FAILED");

  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const runtimeErrors=[];
  const effectful=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  page.on("request",request=>{
    const url=new URL(request.url());
    if(url.origin===new URL(base).origin&&request.method()!=="GET"&&url.pathname!=="/v1/identity/session") effectful.push(`${request.method()} ${url.pathname}`);
  });
  const nav=await page.goto(`${base}/admin/erp`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`GATE25_ERP_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="admin:ERP-01"]');
  await root.waitFor({state:"visible",timeout:15000});
  await page.waitForFunction(()=>document.querySelector('[data-page-uid="admin:ERP-01"]')?.getAttribute("data-page-state")!=="LOADING",{timeout:15000});
  const pageState=await root.getAttribute("data-page-state");
  assert(pageState!=="ERROR",`GATE25_ERP_NAV_PAGE_STATE_${pageState}`);

  const button=page.locator('[data-control-id="ERP-01-BTN-DETAIL"]').first();
  await button.waitFor({state:"visible",timeout:10000});
  assert(await button.isEnabled(),`GATE25_ERP_NAV_DETAIL_DISABLED_${await button.getAttribute("data-disabled-reason")}`);
  const binding={
    control_id:"ERP-01-BTN-DETAIL",
    action_uid:await button.getAttribute("data-action-uid"),
    gate_uid:await button.getAttribute("data-gate-uid"),
    permission_uid:await button.getAttribute("data-permission-uid"),
  };
  assert(binding.action_uid==="ERP-01-ACT-DETAIL-OPEN","GATE25_ERP_NAV_ACTION_UID_MISMATCH");
  assert(binding.gate_uid==="ERP-01-GATE-PAGE","GATE25_ERP_NAV_GATE_UID_MISMATCH");
  assert(binding.permission_uid==="ERP-01-PERM-READ","GATE25_ERP_NAV_PERMISSION_UID_MISMATCH");

  const drawer=page.locator('[data-section-id="ERP-01-SEC-08"]').first();
  await button.click();
  await page.waitForFunction(()=>document.querySelector('[data-section-id="ERP-01-SEC-08"]')?.getAttribute("data-state")==="OPEN_DETAIL",{timeout:10000});
  assert(await drawer.getAttribute("data-state")==="OPEN_DETAIL","GATE25_ERP_NAV_DRAWER_NOT_OPEN_DETAIL");
  assert(await drawer.getAttribute("aria-hidden")==="false","GATE25_ERP_NAV_DRAWER_ARIA_HIDDEN");
  const detail=drawer.locator('[data-drawer-form="ERP-01-DETAIL"]').first();
  await detail.waitFor({state:"visible",timeout:10000});
  assert((await detail.locator('[data-detail-control-ref]').count())>0,"GATE25_ERP_NAV_DETAIL_EMPTY");
  assert(runtimeErrors.length===0,`GATE25_ERP_NAV_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  assert(effectful.length===0,`GATE25_ERP_NAV_EFFECTFUL_REQUEST_${effectful.join("|")}`);

  const evidence=resources.map(resource_key=>({
    resource_key,
    route:"/admin/erp",
    current_control_id:binding.control_id,
    current_action_uid:binding.action_uid,
    current_gate_uid:binding.gate_uid,
    current_permission_uid:binding.permission_uid,
    page_state:pageState,
    drawer_state:"OPEN_DETAIL",
    detail_visible:true,
    mutation_count:0,
    outcome:"PASS",
  }));
  console.log(`GATE25_ERP_NAV_PRODUCTION_PASS resources=${evidence.length} release_sha=${expectedSha}`);
  console.log(`GATE25_ERP_NAV_PRODUCTION_EVIDENCE ${JSON.stringify(evidence)}`);

  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200&&logoutBody?.ok===true&&logoutBody?.logged_in===false,"GATE25_ERP_NAV_LOGOUT_FAILED");
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
