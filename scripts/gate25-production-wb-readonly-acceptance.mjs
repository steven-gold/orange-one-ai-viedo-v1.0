import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();

const targets=[
  ["CTRL-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT-OPEN","company_project_count"],
  ["CTRL-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT-OPEN","company_running_project_count"],
  ["CTRL-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT-OPEN","company_pending_action_count"],
  ["CTRL-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT-OPEN","company_pending_review_count"],
  ["CTRL-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT-OPEN","company_completed_project_count"],
  ["CTRL-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS-OPEN","company_average_progress"],
  ["CTRL-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW-OPEN","project_progress_overview"],
  ["CTRL-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY-OPEN","company_progress_summary"],
  ["CTRL-WORKSPACE-WB-01-PRODUCTION-SUMMARY-OPEN","production_summary"],
  ["CTRL-WORKSPACE-WB-01-NOTIFICATIONS-OPEN","notifications"],
  ["CTRL-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS-OPEN","company_announcements"],
  ["CTRL-WORKSPACE-WB-01-INDUSTRY-NEWS-OPEN","industry_news"],
  ["CTRL-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY-OPEN","system_status_summary"],
  ["CTRL-WORKSPACE-WB-01-RECENT-COMPLETIONS-OPEN","recent_completions"],
];

function assert(condition,message){if(!condition)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}

assert(email&&password,"GATE25_WB_PRODUCTION_CREDENTIAL_NOT_CONFIGURED");
assert(expectedSha,"GATE25_WB_EXPECTED_RELEASE_SHA_NOT_CONFIGURED");
assert(targets.length===14,"GATE25_WB_TARGET_COUNT_INVALID");

const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,`GATE25_WB_HEALTH_HTTP_${health.status}`);
assert(healthBody?.environment==="production","GATE25_WB_ENVIRONMENT_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`GATE25_WB_RELEASE_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);

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
  assert(login.status()===200,`GATE25_WB_LOGIN_HTTP_${login.status()}`);
  assert(loginBody?.ok===true&&loginBody?.logged_in===true,"GATE25_WB_LOGIN_BODY_INVALID");

  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const runtimeErrors=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  const nav=await page.goto(`${base}/`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`GATE25_WB_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="workspace:WB-01"]');
  await root.waitFor({state:"attached",timeout:15000});
  await page.waitForFunction(()=>document.querySelector('[data-page-uid="workspace:WB-01"]')?.getAttribute("data-page-state")!=="LOADING",{timeout:15000});

  for(const [controlId,sectionKey] of targets){
    const button=page.locator(`[data-control-id="${controlId}"]`).first();
    await button.waitFor({state:"visible",timeout:10000});
    assert(await button.isEnabled(),`GATE25_WB_CONTROL_DISABLED_${controlId}`);
    const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname==="/v1/dashboard/read-model"&&r.request().method()==="GET",{timeout:15000});
    await button.click();
    const readResponse=await responsePromise;
    assert(readResponse.status()===200,`GATE25_WB_READ_HTTP_${controlId}_${readResponse.status()}`);
    const drawer=page.locator(`[data-drawer-section-key="${sectionKey}"]`).first();
    await drawer.waitFor({state:"visible",timeout:10000});
    await page.waitForFunction(key=>{
      const node=document.querySelector(`[data-drawer-section-key="${key}"]`);
      const state=node?.getAttribute("data-drawer-state");
      return Boolean(state&&state!=="LOADING");
    },sectionKey,{timeout:15000});
    const drawerState=await drawer.getAttribute("data-drawer-state");
    assert(drawerState==="READ_ONLY"||drawerState==="EMPTY",`GATE25_WB_DRAWER_STATE_${controlId}_${drawerState}`);
    const dialog=drawer.locator('[role="dialog"]');
    assert(await dialog.isVisible(),`GATE25_WB_DIALOG_NOT_VISIBLE_${controlId}`);
    const title=(await dialog.locator("h2").first().textContent()??"").trim();
    assert(Boolean(title),`GATE25_WB_TITLE_EMPTY_${controlId}`);
    evidence.push({
      resource_key:`control:${controlId}`,
      control_id:controlId,
      section_key:sectionKey,
      route:"/",
      dashboard_read_http:readResponse.status(),
      drawer_state:drawerState,
      dialog_visible:true,
      title_present:true,
      outcome:"PASS",
    });
    const close=dialog.locator("button").first();
    await close.click();
    await drawer.waitFor({state:"detached",timeout:10000});
    await page.waitForFunction(id=>document.activeElement?.getAttribute("data-control-id")===id,controlId,{timeout:5000});
  }
  assert(runtimeErrors.length===0,`GATE25_WB_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  assert(evidence.length===14,"GATE25_WB_EVIDENCE_COUNT_INVALID");

  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200,`GATE25_WB_LOGOUT_HTTP_${logout.status()}`);
  assert(logoutBody?.ok===true&&logoutBody?.logged_in===false,"GATE25_WB_LOGOUT_BODY_INVALID");

  process.stdout.write(`GATE25_WB_READONLY_PRODUCTION_PASS resources=${evidence.length} release_sha=${expectedSha}\n`);
  process.stdout.write(`GATE25_WB_READONLY_PRODUCTION_EVIDENCE ${JSON.stringify(evidence)}\n`);
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
