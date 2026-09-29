const base=(process.env.ACPOS_DEPLOYMENT_URL??"https://orange-one-acpos-test.vercel.app").replace(/\/$/,"");
const expectedReleaseSha=(process.env.ACPOS_EXPECT_RELEASE_SHA??"").trim();
const email=(process.env.ACPOS_PRODUCTION_E2E_EMAIL??"").trim();
const password=process.env.ACPOS_PRODUCTION_E2E_PASSWORD??"";

function assert(condition,message){if(!condition)throw new Error(message);}
function protectionHeaders(){const secret=process.env.VERCEL_AUTOMATION_BYPASS_SECRET;return secret?{"x-vercel-protection-bypass":secret}:{};}
function cookieHeaders(cookie){return{...protectionHeaders(),cookie};}
async function body(response,stage){const text=await response.text();try{return JSON.parse(text);}catch{throw new Error(`${stage}_RESPONSE_NOT_JSON`);}}
async function logout(cookie){if(!cookie)return;await fetch(`${base}/v1/identity/session`,{method:"DELETE",cache:"no-store",headers:cookieHeaders(cookie)}).catch(()=>undefined);}

assert(email&&password,"PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED");

let cookie="";
try{
  const health=await fetch(`${base}/health`,{cache:"no-store",headers:protectionHeaders()});
  const healthBody=await body(health,"HEALTH");
  assert(health.status===200,`HEALTH_HTTP_${health.status}`);
  assert(healthBody?.environment==="production","HEALTH_ENVIRONMENT_NOT_PRODUCTION");
  if(expectedReleaseSha)assert(healthBody?.release_sha===expectedReleaseSha,`HEALTH_RELEASE_SHA_MISMATCH_${healthBody?.release_sha??"UNRESOLVED"}`);

  const login=await fetch(`${base}/v1/identity/session`,{
    method:"POST",cache:"no-store",redirect:"manual",
    headers:{...protectionHeaders(),"content-type":"application/json","x-correlation-id":crypto.randomUUID()},
    body:JSON.stringify({email,password}),
  });
  const loginBody=await body(login,"LOGIN");
  assert(login.status===200&&loginBody?.ok===true&&loginBody?.logged_in===true,`LOGIN_FAILED_${login.status}`);
  cookie=(login.headers.get("set-cookie")??"").split(";")[0].trim();
  assert(cookie.startsWith("acpos_session="),"LOGIN_SESSION_COOKIE_MISSING");

  const core=await fetch(`${base}/v1/ui-projections/CORE-01`,{method:"GET",cache:"no-store",headers:cookieHeaders(cookie)});
  const coreBody=await body(core,"CORE_PROJECTION");
  assert(core.status===200,`CORE_PROJECTION_HTTP_${core.status}`);
  assert(Array.isArray(coreBody?.projects)&&coreBody.projects.length>0,"CORE_PROJECT_NOT_AVAILABLE");
  const projectId=coreBody.projects[0]?.project_id;
  assert(typeof projectId==="string"&&projectId.length>0,"CORE_PROJECT_ID_MISSING");

  const thread=await fetch(`${base}/v1/projects/${encodeURIComponent(projectId)}/conversations`,{
    method:"POST",cache:"no-store",
    headers:{...cookieHeaders(cookie),"content-type":"application/json","x-correlation-id":crypto.randomUUID(),"x-core-action-uid":"CORE-01-ACT-THREAD-CREATE"},
    body:JSON.stringify({project_id:projectId,topic_id:null,work_item:"STORY",ai_mode:"SINGLE_AI",acceptance_scope:"PRODUCTION_AI_CONVERSATION_E2E"}),
  });
  const threadBody=await body(thread,"THREAD_CREATE");
  assert(thread.status===200,`THREAD_CREATE_HTTP_${thread.status}_${threadBody?.reason_code??"UNKNOWN"}`);
  const conversationId=threadBody?.conversation_id;
  assert(typeof conversationId==="string"&&conversationId.length>0,"THREAD_CONVERSATION_ID_MISSING");

  const marker=`ACPOS_CHAT_${Date.now().toString(36).toUpperCase()}`;
  const firstMessage=`This is an ACPOS Production conversation acceptance turn. Remember this marker: ${marker}. Reply briefly and include the marker.`;
  const turn1=await fetch(`${base}/v1/conversations/${encodeURIComponent(conversationId)}/messages`,{
    method:"POST",cache:"no-store",
    headers:{...cookieHeaders(cookie),"content-type":"application/json","x-correlation-id":crypto.randomUUID(),"x-core-action-uid":"CORE-01-ACT-SEND"},
    body:JSON.stringify({conversation_id:conversationId,message:firstMessage,ai_mode:"SINGLE_AI",attachment_refs:[],reference_refs:[],mention_tokens:[]}),
  });
  const turn1Body=await body(turn1,"TURN1");
  assert(turn1.status===200,`TURN1_HTTP_${turn1.status}_${turn1Body?.reason_code??"UNKNOWN"}`);
  assert(turn1Body?.accepted===true,"TURN1_NOT_ACCEPTED");
  assert(typeof turn1Body?.message_ref==="string"&&turn1Body.message_ref.length>0,"TURN1_USER_MESSAGE_REF_MISSING");
  assert(typeof turn1Body?.assistant_response_ref==="string"&&turn1Body.assistant_response_ref.length>0,"TURN1_ASSISTANT_REF_MISSING");
  assert(typeof turn1Body?.assistant_response_text==="string"&&turn1Body.assistant_response_text.trim().length>0,"TURN1_ASSISTANT_TEXT_MISSING");
  assert(turn1Body.assistant_response_text.includes(marker),"TURN1_MARKER_NOT_RETURNED");
  assert(turn1Body.external_request_sent===true,"TURN1_EXTERNAL_REQUEST_NOT_SENT");
  assert(turn1Body.worker_succeeded===1,"TURN1_WORKER_NOT_SUCCESSFUL");
  assert(typeof turn1Body.provider_id==="string"&&turn1Body.provider_id.length>0,"TURN1_PROVIDER_MISSING");
  assert(typeof turn1Body.model_id==="string"&&turn1Body.model_id.length>0,"TURN1_MODEL_MISSING");

  const turn2=await fetch(`${base}/v1/conversations/${encodeURIComponent(conversationId)}/messages`,{
    method:"POST",cache:"no-store",
    headers:{...cookieHeaders(cookie),"content-type":"application/json","x-correlation-id":crypto.randomUUID(),"x-core-action-uid":"CORE-01-ACT-SEND"},
    body:JSON.stringify({conversation_id:conversationId,message:"What marker did I ask you to remember in the previous turn? Include the exact marker in your answer.",ai_mode:"SINGLE_AI",attachment_refs:[],reference_refs:[],mention_tokens:[]}),
  });
  const turn2Body=await body(turn2,"TURN2");
  assert(turn2.status===200,`TURN2_HTTP_${turn2.status}_${turn2Body?.reason_code??"UNKNOWN"}`);
  assert(turn2Body?.accepted===true,"TURN2_NOT_ACCEPTED");
  assert(typeof turn2Body?.assistant_response_text==="string"&&turn2Body.assistant_response_text.includes(marker),"TURN2_HISTORY_MARKER_MISSING");
  assert(turn2Body.external_request_sent===true,"TURN2_EXTERNAL_REQUEST_NOT_SENT");
  assert(turn2Body.worker_succeeded===1,"TURN2_WORKER_NOT_SUCCESSFUL");

  const projected=await fetch(`${base}/v1/ui-projections/CORE-01`,{method:"GET",cache:"no-store",headers:cookieHeaders(cookie)});
  const projectedBody=await body(projected,"CORE_HISTORY_PROJECTION");
  assert(projected.status===200,`CORE_HISTORY_PROJECTION_HTTP_${projected.status}`);
  const messages=projectedBody?.messages_by_thread?.[conversationId];
  assert(Array.isArray(messages)&&messages.length>=4,`CORE_HISTORY_MESSAGE_COUNT_${Array.isArray(messages)?messages.length:0}`);
  const roles=messages.slice(-4).map((entry)=>entry?.role);
  assert(JSON.stringify(roles)===JSON.stringify(["USER","ASSISTANT","USER","ASSISTANT"]),`CORE_HISTORY_ROLE_SEQUENCE_${roles.join(",")}`);
  assert(messages.some((entry)=>entry?.message_ref===turn1Body.message_ref),"CORE_HISTORY_TURN1_USER_REF_MISSING");
  assert(messages.some((entry)=>entry?.message_ref===turn1Body.assistant_response_ref),"CORE_HISTORY_TURN1_ASSISTANT_REF_MISSING");
  assert(messages.some((entry)=>entry?.message_ref===turn2Body.assistant_response_ref),"CORE_HISTORY_TURN2_ASSISTANT_REF_MISSING");

  process.stdout.write(`PRODUCTION_AI_CONVERSATION_E2E_PASS release_sha=${healthBody.release_sha} project_id=${projectId} conversation_id=${conversationId} marker=${marker} turn1_provider=${turn1Body.provider_id} turn1_model=${turn1Body.model_id} turn2_provider=${turn2Body.provider_id} turn2_model=${turn2Body.model_id} persisted_messages=${messages.length} history_recall=true external_requests=2 worker_successes=2\n`);
}finally{
  await logout(cookie);
}
