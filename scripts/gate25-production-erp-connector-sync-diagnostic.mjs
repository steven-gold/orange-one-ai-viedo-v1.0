import { chromium } from "playwright";

const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";
const expectedSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();

const connectorControls=[
  "ERP-01-BTN-CONNECTOR-CREATE",
  "ERP-01-BTN-CONNECTOR-UPDATE",
  "ERP-01-BTN-CONNECTOR-VALIDATE",
  "ERP-01-BTN-MAPPING-VALIDATE",
];
const syncControls=[
  "ERP-01-BTN-SNAPSHOT-REFRESH",
  "ERP-01-BTN-SYNC-CREATE",
  "ERP-01-BTN-SYNC-STATUS",
  "ERP-01-BTN-SYNC-RETRY",
  "ERP-01-BTN-FAILURE-GET",
];
const gateIds=[
  "ERP-01-GATE-PAGE",
  "ERP-01-GATE-CONNECTOR-READ",
  "ERP-01-GATE-CONNECTOR-WRITE",
  "ERP-01-GATE-CONNECTOR-VALIDATE",
  "ERP-01-GATE-MAPPING-VALIDATE",
  "ERP-01-GATE-SYNC-READ",
  "ERP-01-GATE-SNAPSHOT-REFRESH",
  "ERP-01-GATE-SYNC-CREATE",
  "ERP-01-GATE-SYNC-RETRY",
];

function assert(value,message){if(!value)throw new Error(message)}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{}}
function unwrapProjection(body){
  const root=body&&typeof body==="object"?body:{};
  return root.value&&typeof root.value==="object"?root.value:root;
}
function present(value){return value!==null&&value!==undefined&&value!==""&&value!=="—"}
function findPresence(root,names){
  const wanted=new Set(names.map(name=>name.toLowerCase()));
  let found=false;
  const seen=new Set();
  const walk=(value)=>{
    if(found||value===null||value===undefined)return;
    if(typeof value!=="object")return;
    if(seen.has(value))return;
    seen.add(value);
    if(Array.isArray(value)){for(const item of value)walk(item);return;}
    for(const [key,item] of Object.entries(value)){
      if(wanted.has(key.toLowerCase())&&present(item)){found=true;return;}
      walk(item);
      if(found)return;
    }
  };
  walk(root);
  return found;
}
async function inspectControl(page,controlId){
  const node=page.locator(`[data-control-id="${controlId}"]`).first();
  await node.waitFor({state:"visible",timeout:10000});
  return {
    control_id:controlId,
    enabled:await node.isEnabled(),
    disabled_reason:await node.getAttribute("data-disabled-reason"),
    action_uid:await node.getAttribute("data-action-uid"),
    gate_uid:await node.getAttribute("data-gate-uid"),
    permission_uid:await node.getAttribute("data-permission-uid"),
  };
}

assert(base&&email&&password&&expectedSha,"ERP_CONNECTOR_SYNC_DIAGNOSTIC_ENV_MISSING");
const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
const healthBody=await health.json().catch(()=>null);
assert(health.status===200,"ERP_CONNECTOR_SYNC_DIAGNOSTIC_HEALTH_FAILED");
assert(healthBody?.environment==="production","ERP_CONNECTOR_SYNC_DIAGNOSTIC_NOT_PRODUCTION");
assert(healthBody?.release_sha===expectedSha,`ERP_CONNECTOR_SYNC_DIAGNOSTIC_SHA_MISMATCH_${healthBody?.release_sha??"MISSING"}`);

const browser=await chromium.launch({headless:true});
let context;
try{
  context=await browser.newContext({extraHTTPHeaders:protectionHeaders()});
  const login=await context.request.post(`${base}/v1/identity/session`,{
    headers:{"content-type":"application/json","x-correlation-id":crypto.randomUUID()},
    data:{email,password},
  });
  const loginBody=await login.json().catch(()=>null);
  assert(login.status()===200&&loginBody?.ok===true&&loginBody?.logged_in===true,"ERP_CONNECTOR_SYNC_DIAGNOSTIC_LOGIN_FAILED");

  const projection=await context.request.get(`${base}/v1/ui-projections/admin%3AERP-01`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const projectionBody=await projection.json().catch(()=>null);
  assert(projection.status()===200,`ERP_CONNECTOR_SYNC_DIAGNOSTIC_PROJECTION_HTTP_${projection.status()}`);
  const value=unwrapProjection(projectionBody);
  assert(!value.test_metadata,"ERP_CONNECTOR_SYNC_DIAGNOSTIC_SYNTHETIC_FORBIDDEN");
  const gates=value.gate_state&&typeof value.gate_state==="object"?value.gate_state:{};
  const gate_state=Object.fromEntries(gateIds.map(id=>[id,gates[id]===true]));
  const references={
    connector_id_present:findPresence(value,["connector_id","erp_connector_id","connectorId","erpConnectorId"]),
    mapping_version_present:findPresence(value,["mapping_version","mappingVersion"]),
    snapshot_id_present:findPresence(value,["snapshot_id","snapshotId"]),
    sync_job_id_present:findPresence(value,["sync_job_id","syncJobId","job_id","jobId"]),
    failure_id_present:findPresence(value,["failure_id","failureId"]),
  };

  const page=await context.newPage({viewport:{width:1440,height:1400}});
  const runtimeErrors=[];
  const effectful=[];
  page.on("pageerror",error=>runtimeErrors.push(error.message));
  page.on("request",request=>{
    const url=new URL(request.url());
    if(url.origin===new URL(base).origin&&request.method()!=="GET"&&url.pathname!=="/v1/identity/session") effectful.push(`${request.method()} ${url.pathname}`);
  });
  const nav=await page.goto(`${base}/admin/erp`,{waitUntil:"networkidle",timeout:45000});
  assert(nav?.ok(),`ERP_CONNECTOR_SYNC_DIAGNOSTIC_NAV_HTTP_${nav?.status()}`);
  const root=page.locator('[data-page-uid="admin:ERP-01"]');
  await root.waitFor({state:"visible",timeout:15000});
  await page.waitForFunction(()=>document.querySelector('[data-page-uid="admin:ERP-01"]')?.getAttribute("data-page-state")!=="LOADING",{timeout:15000});

  const connectorTab=page.locator('[data-control-id="ERP-01-BTN-TAB-CONNECTOR"]').first();
  await connectorTab.click();
  const connector=[];
  for(const id of connectorControls)connector.push(await inspectControl(page,id));

  const syncTab=page.locator('[data-control-id="ERP-01-BTN-TAB-SYNC"]').first();
  await syncTab.click();
  const sync=[];
  for(const id of syncControls)sync.push(await inspectControl(page,id));

  assert(effectful.length===0,`ERP_CONNECTOR_SYNC_DIAGNOSTIC_EFFECTFUL_REQUEST_${effectful.join("|")}`);
  assert(runtimeErrors.length===0,`ERP_CONNECTOR_SYNC_DIAGNOSTIC_RUNTIME_ERRORS_${runtimeErrors.join("|")}`);
  console.log(`ERP_CONNECTOR_SYNC_DIAGNOSTIC ${JSON.stringify({production_release_sha:expectedSha,projection_http:projection.status(),page_state:await root.getAttribute("data-page-state"),gate_state,references,connector,sync,mutation_count:0})}`);

  const logout=await context.request.delete(`${base}/v1/identity/session`,{headers:{"x-correlation-id":crypto.randomUUID()}});
  const logoutBody=await logout.json().catch(()=>null);
  assert(logout.status()===200&&logoutBody?.ok===true&&logoutBody?.logged_in===false,"ERP_CONNECTOR_SYNC_DIAGNOSTIC_LOGOUT_FAILED");
}finally{
  if(context)await context.close().catch(()=>{});
  await browser.close();
}
