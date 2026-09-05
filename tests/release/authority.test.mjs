import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const manifest = await readFile("authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml", "utf8");
const system = await readFile("authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml", "utf8");
const sysPage = await readFile("authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml", "utf8");
const sysClientState = await readFile("src/domain/system/systemClientState.ts", "utf8");
const corePage = await readFile("authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml", "utf8");
const coreClientState = await readFile("src/domain/core/coreClientState.ts", "utf8");
const editPage = await readFile("authority/pages/workspace/EDIT-01/ACPOS_EDIT-01_FINAL_LOCKED_ENCODING_SCRIPT_CONTENT_CLOSED_V1.1.yaml", "utf8");
const editClientState = await readFile("src/domain/edit/editClientState.ts", "utf8");
const editControlRuntime = await readFile("src/components/pages/EditControlRuntime.tsx", "utf8");
const assetPage = await readFile("authority/pages/workspace/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml", "utf8");
const assetClientState = await readFile("src/domain/asset/assetClientState.ts", "utf8");
const devPage = await readFile("authority/pages/admin/DEV-01/ACPOS_DEV-01_ENTERPRISE_AUTOMATION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml", "utf8");
const devVisual = await readFile("src/components/pages/DevVisual.tsx", "utf8");
const devControlRuntime = await readFile("src/components/pages/DevControlRuntime.tsx", "utf8");
const devCommandPort = await readFile("src/domain/dev/devCommandPort.ts", "utf8");
const controlledDevRuntime = await readFile("src/domain/dev/controlledDevClientTestRuntime.ts", "utf8");
const infoPage = await readFile("authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml", "utf8");
const infoClientState = await readFile("src/domain/info/infoClientState.ts", "utf8");
const infoCommandPort = await readFile("src/domain/info/infoCommandPort.ts", "utf8");
const qaPage = await readFile("authority/pages/workspace/QA-01/ACPOS_QA-01_FINAL_LOCKED_ENCODING_DEDUP_CLEAN.yaml", "utf8");
const qaProjectionPort = await readFile("src/domain/qa/qaProjectionPort.ts", "utf8");
const qaControlRuntime = await readFile("src/components/pages/QaControlRuntime.tsx", "utf8");
const iamPage = await readFile("authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml", "utf8");
const iamClientState = await readFile("src/domain/iam/iamClientState.ts", "utf8");
const iamControlRuntime = await readFile("src/components/pages/IamControlRuntime.tsx", "utf8");
const knowledgePage = await readFile("authority/pages/admin/KB-01/ACPOS_KB-01_FINAL_LOCKED_ENCODING.yaml", "utf8");
const knowledgeRuntimePort = await readFile("src/domain/knowledge/knowledgeRuntimePort.ts", "utf8");
const knowledgeVisual = await readFile("src/components/pages/KnowledgeAdminVisual.tsx", "utf8");

test("Current Authority contains exactly 18 unique page authorities", () => {
  const pages = [...manifest.matchAll(/^  - (authority\/pages\/[^\n]+)$/gm)].map((match) => match[1]);
  assert.equal(pages.length, 18);
  assert.equal(new Set(pages).size, 18);
  assert.match(manifest, /current_page_count:\s*18/);
});

test("Production Script V1.3 remains the current integration contract", () => {
  assert.match(manifest, /production_script_v1_3:/);
  assert.match(system, /ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1\.3\.yaml/);
  assert.doesNotMatch(manifest, /PRODUCTION_SCRIPT.*V1\.2/);
});

test("WB-01 UI projection mapping locks page-gate authorize and keeps adapter bind closed", async () => {
  const mapping = await readFile("authority/runtime/ACPOS_WB01_UI_PROJECTION_SQL_PERMISSION_MAPPING_FINAL_LOCKED_V1.0.yaml", "utf8");
  assert.match(manifest, /ACPOS_WB01_UI_PROJECTION_SQL_PERMISSION_MAPPING_FINAL_LOCKED_V1\.0\.yaml/);
  assert.match(mapping, /page_permission_label: workspace\.dashboard\.view/);
  assert.match(mapping, /catalog_resource_key: page:workspace:WB-01/);
  assert.match(mapping, /required_action: VIEW/);
  assert.match(mapping, /inheritance: FORBIDDEN/);
  assert.match(mapping, /account_permission_assignments/);
  assert.match(mapping, /permission_resources/);
  assert.match(mapping, /section_sql_mapping: AUTHORITY_GAP/);
  assert.match(mapping, /adapter_bind_allowed: false/);
  assert.match(mapping, /identity_transport: INTERNAL_COOKIE_SESSION/);
  assert.match(mapping, /account_permission_assignments.status = APPROVED/);
  assert.match(mapping, /AND a.status = 'APPROVED'/);
  assert.match(mapping, /precedence: DENY_WINS/);
  assert.match(mapping, /SCOPE_CONDITION_EVALUATOR_NOT_DEFINED/);
  assert.match(mapping, /Infer company_project_count from COUNT\(projects\)/);
});

test("Production identity runtime names app_users actor and internal cookie session", async () => {
  const identity = await readFile("authority/runtime/ACPOS_PRODUCTION_IDENTITY_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml", "utf8");
  assert.match(manifest, /ACPOS_PRODUCTION_IDENTITY_RUNTIME_CONTRACT_FINAL_LOCKED_V1\.0\.yaml/);
  assert.match(identity, /table: app_users/);
  assert.match(identity, /user_id_column: user_id/);
  assert.match(identity, /port_uid: GHS-PORT-IDENTITY/);
  assert.match(identity, /operation: resolveIdentityAccountAuthority/);
  assert.match(identity, /identity_transport: INTERNAL_COOKIE_SESSION/);
  assert.match(identity, /cookie_name: acpos_session/);
  assert.match(identity, /mapping_to_app_users: EMAIL_JOIN/);
  assert.match(identity, /Use NEON_AUTH_BASE_URL or VITE_NEON_AUTH_URL as application identity/);
  assert.match(identity, /Treat acpos_runtime.sessions as app_users identity without the email join/);
  assert.match(identity, /adapter_bind_allowed: false/);
  assert.match(identity, /IDENTITY_OPERATION_REGISTRY_ABSENT/);
  assert.match(identity, /lookup_by_external_subject_sql:/);
  assert.match(identity, /operation_registry_file_in_app_repo: ABSENT/);
  assert.match(identity, /catalog_registration: NOT_PRESENT/);
  assert.match(identity, /reason_code: IDENTITY_RUNTIME_NOT_BOUND/);
  assert.match(identity, /CLOSE_WB01_PROJECTION_MAPPING_GAPS/);
});

test("System implementation truth is not silently promoted", () => {
  assert.match(system, /api_binding:\s*NOT_EXECUTED/);
  assert.match(system, /database_binding:\s*NOT_EXECUTED/);
  assert.match(system, /deployment:\s*NOT_EXECUTED/);
});

test("SYS-01 mode switching remains Authority-defined client state with continuity preservation", () => {
  for (const controlId of ["SYS-01-BTN-SINGLE-AI","SYS-01-BTN-MULTI-AI","SYS-01-BTN-COUNCIL-DISCUSSION","SYS-01-BTN-COUNCIL-PARALLEL"]) {
    const control = sysPage.match(new RegExp(`- control_uid: ${controlId}([\\s\\S]*?)(?=\\n  - control_uid:|\\n  actions:)`));
    assert.ok(control, `${controlId} must remain in current SYS-01 Authority`);
    assert.match(control[1], /api_required:\s*false/);
  }
  assert.match(sysPage, /binding_kind:\s*CLIENT_STATE_OR_VIEW_NO_API_REQUIRED/);
  assert.match(sysPage, /mode_switch_must_not_change_SYSTEM_CHANGE_ID/);
  assert.match(sysPage, /mode_switch_must_not_create_new_conversation_or_thread/);
  assert.match(sysPage, /mode_switch_must_preserve_draft_and_source_refs/);
  for (const action of ["AI_MODE_SINGLE", "AI_MODE_MULTI", "COUNCIL_DISCUSSION", "COUNCIL_PARALLEL"]) {
    const branch = sysClientState.match(new RegExp(`case ["']${action}["']:\\s*([\\s\\S]*?)(?=\\n    case |\\n  \\})`));
    assert.ok(branch, `${action} reducer branch must remain materialized`);
    assert.match(branch[1], /\.\.\.state|return state/);
    assert.doesNotMatch(branch[1], /system_change_id\s*:|conversation_id\s*:|thread_id\s*:|branch_id\s*:|draft\s*:|attachment_refs\s*:|selected_reference_ref\s*:/);
  }
  assert.match(sysClientState, /case ["']COUNCIL_DISCUSSION["']:\s*return state\.ai_mode === ["']MULTI_AI["']/);
  assert.match(sysClientState, /case ["']COUNCIL_PARALLEL["']:\s*return state\.ai_mode === ["']MULTI_AI["']/);
});

test("SYS-01 draft remains local-only state and mode changes do not clear it", () => {
  const draftControl = sysPage.match(/- control_uid: SYS-01-INP-MESSAGE([\s\S]*?)(?=\n  - control_uid:|\n  actions:)/);
  assert.ok(draftControl, "SYS-01 message draft control must remain in current Authority");
  assert.match(draftControl[1], /binding_kind:\s*LOCAL_DRAFT_STATE_ONLY_IN_VISUAL_PHASE/);
  assert.match(draftControl[1], /api_required:\s*false/);
  assert.match(sysClientState, /case ["']DRAFT["']:\s*return \{ \.\.\.state, draft: action\.value \};/);
});

test("CORE-01 context/thread switches cannot carry composer resources across scope", () => {
  assert.match(corePage, /CORE-01-GATE-THREAD[\s\S]*?thread scope matches current context/);
  assert.match(corePage, /CORE-01-ERR-THREAD-001[\s\S]*?Do not mix history; load matching thread or create new thread/);
  assert.match(corePage, /CORE-01-ACT-PROJECT-SELECT[\s\S]*?clear Topic\/work item\/thread dependent state/);
  for (const actionUid of ["CORE-01-ACT-PROJECT-SELECT","CORE-01-ACT-TOPIC-SELECT","CORE-01-ACT-WORK-ITEM-SELECT","CORE-01-ACT-THREAD-SELECT"]) {
    const branch = coreClientState.match(new RegExp(`case ["']${actionUid}["']:[\\s\\S]*?(?=\\n    case |\\n  \\})`));
    assert.ok(branch, `${actionUid} must remain materialized`);
    assert.match(branch[0], /attachment_refs:\s*\[\]/);
    assert.match(branch[0], /reference_refs:\s*\[\]/);
    assert.match(branch[0], /composer_message_refs:\s*\[\]/);
    assert.match(branch[0], /decision_evidence_refs:\s*\[\]/);
  }
});

test("EDIT-01 UI-only actions remain client-only and cannot mutate governed production objects", () => {
  const uiOnly = editPage.match(/- effect_type: UI_ONLY([\s\S]*?)(?=\n  - effect_type:)/);
  assert.ok(uiOnly, "EDIT-01 UI_ONLY authority contract must remain present");
  assert.match(uiOnly[1], /allowed_changes:\s*Selection \/ Viewport \/ Playhead \/ Range \/ Preview \/ Compare/);
  assert.match(uiOnly[1], /forbidden:\s*不得修改 Working Draft、Version、Output、Evidence/);
  for (const action of ["PLAY","PAUSE","SEEK","RANGE_IN","RANGE_OUT","RANGE_CLEAR","RATE","LOOP","MUTE","PREVIEW_VOLUME","SNAP","ZOOM_IN","ZOOM_OUT","ZOOM_FIT","INSPECTOR_TAB","MEDIA_SEARCH","MEDIA_FILTER","MEDIA_SELECT","ISSUE_SELECT","VERSION_SELECT","TRACK_SELECT","CLIP_SELECT","SUBTITLE_TOGGLE","AUDIO_MONITOR","VIEW_ACTION"]) {
    const branch = editClientState.match(new RegExp(`case["']${action}["']:\\s*([\\s\\S]*?)(?=case["']|\\n  \\})`));
    assert.ok(branch, `${action} reducer branch must remain materialized`);
    assert.doesNotMatch(branch[1], /working_draft_ref\s*:|saved_edit_version_id\s*:|output_version_id\s*:|draft_dirty\s*:\s*true|page_state_uid\s*:\s*["']EDIT-01-ST-PAGE-EVAL_REQUIRED["']/);
  }
});

test("EDIT-01 UI-only reducer stays separated from draft mutation helper", () => {
  assert.match(editClientState, /case["']LOCAL_ACTION["'][\s\S]*?draft_dirty:action\.dirty\?true:state\.draft_dirty/);
  assert.match(editClientState, /action\.dirty\?\{\.\.\.state\.resolved,page_state_uid:["']EDIT-01-ST-PAGE-EVAL_REQUIRED["']\}:state\.resolved/);
  assert.doesNotMatch(editClientState, /case["'](?:PLAY|PAUSE|SEEK|RANGE_IN|RANGE_OUT|RANGE_CLEAR|RATE|LOOP|MUTE|PREVIEW_VOLUME|SNAP|ZOOM_IN|ZOOM_OUT|ZOOM_FIT)["'][\s\S]{0,240}?LOCAL_ACTION/);
});

test("EDIT-01 frame nudge must fail closed until Project or Source Timebase is materialized", () => {
  assert.match(editPage, /Frame Nudge[\s\S]*?前\/後 1 frame 必須存在；長度與 FPS 由 Project\/Source Timebase 決定/);
  assert.match(editPage, /Timecode[\s\S]*?必須驗證 Project Timebase/);
  assert.match(editControlRuntime, /EDIT-01-BTN-PREV-FRAME[\s\S]*?EDIT-01-BTN-NEXT-FRAME[\s\S]*?PROJECT_OR_SOURCE_TIMEBASE_REQUIRED/);
  assert.doesNotMatch(editControlRuntime, /BTN-PREV-FRAME[\s\S]{0,180}?playhead\?\?0\)-1/);
  assert.doesNotMatch(editControlRuntime, /BTN-NEXT-FRAME[\s\S]{0,180}?playhead\?\?0\)\+1/);
});

test("EDIT-01 Final Preview renders the real resolved media URI instead of URI text", () => {
  assert.match(editPage, /EDIT-01-PNL-FINAL-PREVIEW[\s\S]*?type: preview[\s\S]*?action_or_behavior: READ_ONLY/);
  assert.match(editControlRuntime, /controlId==="EDIT-01-PNL-FINAL-PREVIEW"&&uri\?<video src=\{uri\}/);
});

test("ASSET-01 context changes clear stale resolved business projection before re-resolution", () => {
  assert.match(assetPage, /action_uid: ASSET-01-ACT-PROJECT-SELECT[\s\S]*?label: Select Project[\s\S]*?effect_type: CONTEXT_STATE[\s\S]*?binding_kind: CLIENT_STATE_OR_VIEW_NO_API_REQUIRED[\s\S]*?api_required: false/);
  assert.match(assetPage, /action_uid: ASSET-01-ACT-TOPIC-SELECT[\s\S]*?label: Select Topic[\s\S]*?effect_type: CONTEXT_STATE[\s\S]*?binding_kind: CLIENT_STATE_OR_VIEW_NO_API_REQUIRED[\s\S]*?api_required: false/);
  assert.match(assetPage, /error_uid: ASSET-01-ERR-CONTEXT-001[\s\S]*?context: Project\/Topic\/Task context missing\/stale[\s\S]*?recovery: BLOCK; re-resolve exact task/);
  const project = assetClientState.match(/case "ASSET-01-ACT-PROJECT-SELECT":([\s\S]*?)(?=\n    case )/);
  const topic = assetClientState.match(/case "ASSET-01-ACT-TOPIC-SELECT":([\s\S]*?)(?=\n    case )/);
  assert.ok(project); assert.ok(topic);
  assert.match(project[1], /topic_ref: null/); assert.match(project[1], /asset_ref: null/); assert.match(project[1], /projection: null/);
  assert.match(topic[1], /asset_ref: null/); assert.match(topic[1], /projection: null/);
});

test("DEV-01 five-stage navigation remains Authority-defined client state with no API requirement", () => {
  for (const index of [1, 2, 3, 4, 5]) {
    const actionUid = `DEV-01-ACT-STAGE-${index}-SELECT`;
    const action = devPage.match(new RegExp(`- action_uid: ${actionUid}([\\s\\S]*?)(?=\\n- action_uid:)`));
    assert.ok(action, `${actionUid} must remain in current DEV-01 Authority`);
    assert.match(action[1], /effect_type:\s*UI_CONTEXT_STATE/);
    assert.match(action[1], /binding_kind:\s*CLIENT_STATE_OR_VIEW_NO_API_REQUIRED/);
    assert.match(action[1], /api_required:\s*false/);
  }
  assert.match(devVisual, /const \[activeStage, setActiveStage\] = useState<StageKey>\("discovery"\)/);
  assert.match(devVisual, /onUiClick=\{\(\) => setActiveStage\(item\.key\)\}/);
  assert.match(devControlRuntime, /const formal = binding\?\.effect_type !== "UI_CONTEXT_STATE"/);
  assert.match(devControlRuntime, /if \(!formal\) \{\s*onUiClick\?\.\(\);\s*return;\s*\}/);
});

test("DEV-01 production commands remain fail-closed until a registered business-payload adapter is bound", () => {
  assert.match(devPage, /form_schema:\s*USE_EXISTING_REGISTERED_BUSINESS_PAYLOAD_SCHEMA; do not union or invent fields/);
  assert.match(devCommandPort, /let adapter:DevCommandAdapter\|null=null/);
  assert.match(devCommandPort, /if\(!adapter\)return\{ok:false,error_uid:'DEV-01-ERR-UNDEFINED',reason_code:'DEV_COMMAND_RUNTIME_NOT_BOUND'/);
  assert.doesNotMatch(devCommandPort, /fetch\s*\(/);
  assert.match(controlledDevRuntime, /if \(configured \|\| !isControlledTestMode\(\)\) return/);
  assert.match(controlledDevRuntime, /production_eligible: false/);
});

test("INFO-01 selection and presentation actions remain local read-only context state", () => {
  for (const actionUid of ["INFO-01-ACT-FILTER","INFO-01-ACT-SOURCE-SELECT","INFO-01-ACT-ALERT-SELECT","INFO-01-ACT-FACTPACK-SELECT","INFO-01-ACT-FACT-TYPE","INFO-01-ACT-EVIDENCE-SELECT","INFO-01-ACT-RESEARCH-SELECT","INFO-01-ACT-CANDIDATE-SELECT"]) {
    const action = infoPage.match(new RegExp(`- action_uid: ${actionUid}([\\s\\S]*?)(?=\\n  - action_uid:|\\nacceptance:|\\n  acceptance:)`));
    assert.ok(action, `${actionUid} must remain in current INFO-01 Authority`);
    assert.match(action[1], /effect_type:\s*(?:UI_ONLY|CONTEXT_STATE)/);
    assert.match(action[1], /operation:\s*null/);
    assert.match(action[1], /method_path:\s*null/);
    assert.match(action[1], /state_event:\s*NONE/);
  }
  for (const reducerAction of ["SCOPE", "SOURCE", "ALERT", "FACTPACK", "FACT_VIEW", "EVIDENCE", "RESEARCH", "CANDIDATE", "CITATION", "AUDIT"]) {
    const branch = infoClientState.match(new RegExp(`case['\"]${reducerAction}['\"]:\\s*([\\s\\S]*?)(?=case['\"]|\\n  \\})`));
    assert.ok(branch, `${reducerAction} reducer branch must remain materialized`);
    assert.doesNotMatch(branch[1], /projection\s*:|correlation_id\s*:|runtime_error\s*:|runtime_error_uid\s*:|runtime_reason_code\s*:/);
  }
});

test("INFO-01 effectful commands stay payload-adapter gated and cannot infer governed request fields", () => {
  assert.match(infoPage, /additional_fields:\s*Use registered Business Payload Registry only; do not infer page-union fields/);
  assert.match(infoPage, /additional_fields:\s*Use registered Business Payload Registry only; do not invent search parameters/);
  assert.match(infoCommandPort, /let builder:InfoCommandPayloadBuilder\|null=null/);
  assert.match(infoCommandPort, /if\(!builder\)return\{ok:false as const,error_uid:errorUid\(input\.action_uid\),reason_code:'INFO_COMMAND_PAYLOAD_ADAPTER_NOT_BOUND'/);
});

test("QA-01 projection correlation trace remains attached to resolved successful context", () => {
  assert.match(qaPage, /name:\s*Status \/ Audit/);
  assert.match(qaPage, /responsibility:\s*Current state, errors, disabled reason, audit\/correlation\/trace/);
  assert.match(qaProjectionPort, /const cid=r\.headers\.get\("x-correlation-id"\)/);
  assert.match(qaProjectionPort, /const tracedContext=context\.correlation_id\?context:\{\.\.\.context,correlation_id:cid\}/);
  assert.match(qaProjectionPort, /return\{ok:true,context:tracedContext,correlation_id:cid\}/);
});

test("QA-01 frame nudge fails closed until source/project timebase is materialized", () => {
  assert.match(qaPage, /QA-01-ACT-VIEWER-PREV-FRAME[\s\S]*?Move exact viewer -1 frame using source\/project timebase/);
  assert.match(qaPage, /QA-01-ACT-VIEWER-NEXT-FRAME[\s\S]*?Move exact viewer \+1 frame using source\/project timebase/);
  assert.match(qaControlRuntime, /QA-01-BTN-PREV-FRAME"\|\|id==="QA-01-BTN-NEXT-FRAME"\)\{dispatch\(\{type:"RUNTIME_ERROR",value:"QA-01-ERR-OUTPUT-001:SOURCE_OR_PROJECT_TIMEBASE_REQUIRED"\}\);return;\}/);
  assert.doesNotMatch(qaControlRuntime, /QA-01-BTN-PREV-FRAME[\s\S]{0,160}?current_timecode\?\?0\)-1/);
  assert.doesNotMatch(qaControlRuntime, /QA-01-BTN-NEXT-FRAME[\s\S]{0,160}?current_timecode\?\?0\)\+1/);
});

test("IAM-01 draft mutations invalidate authorization preview before Complete", () => {
  assert.match(iamPage, /condition: preview current \+ no blocking conflict/);
  assert.match(iamPage, /Require explicit confirmation/);
  assert.match(iamClientState, /selectAllFront[\s\S]*?preview_ref:null/);
  assert.match(iamClientState, /selectAllAdmin[\s\S]*?preview_ref:null/);
  assert.match(iamControlRuntime, /setIamFrontL1[\s\S]*?preview_ref:null/);
  assert.match(iamControlRuntime, /setIamAdminL1[\s\S]*?preview_ref:null/);
  assert.match(iamControlRuntime, /setIamBasicField[\s\S]*?preview_ref:null/);
  assert.match(iamControlRuntime, /setIamDepartmentPreset[\s\S]*?preview_ref:null/);
  assert.match(iamControlRuntime, /IAM-01-BTN-COMPLETE[\s\S]*?!runtime\.client\.preview_ref/);
});

test("KB-01 typed projection values are preserved and rendered without string-only loss", () => {
  assert.match(knowledgePage, /F:RUN-RETRY:retry_eligible:BOOLEAN/);
  assert.match(knowledgePage, /F:EXP-OUTCOME:business_human_outcome:OBJECT/);
  assert.match(knowledgePage, /F:REPLAY-ROOT:root_cause:OBJECT/);
  assert.match(knowledgePage, /F:REV-CHECK:mandatory_check_results:OBJECT_LIST/);
  assert.match(knowledgeRuntimePort, /values: Readonly<Record<string, unknown>>/);
  assert.match(knowledgeRuntimePort, /for \(const \[key, value\] of Object\.entries\(valuesRaw\)\) values\[key\] = value/);
  assert.doesNotMatch(knowledgeRuntimePort, /typeof value === "string"\) values\[key\] = value/);
  assert.match(knowledgeVisual, /function displayProjectionValue\(value: unknown\)/);
  assert.match(knowledgeVisual, /projectionValue\(projection, "RUN-RETRY"\) === true/);
});
