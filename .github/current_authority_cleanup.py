from pathlib import Path
import subprocess


def r(path: str) -> str:
    return Path(path).read_text()


def w(path: str, content: str) -> None:
    Path(path).write_text(content)


def replace_exact(path: str, old: str, new: str, count: int = 1) -> None:
    content = r(path)
    actual = content.count(old)
    if actual != count:
        raise SystemExit(f"{path}: expected {count}, got {actual}: {old[:100]}")
    w(path, content.replace(old, new, count))


# CORE-01: remove implementation-only pseudo UID.
replace_exact(
    "src/components/pages/CoreVisual.tsx",
    'data-layout="CORE-01-PRIMARY-GRID"',
    'data-layout="primary-grid"',
)

# EDIT-01: remove unregistered dead action mapping.
replace_exact(
    "src/components/pages/EditControlRuntime.tsx",
    ',"EDIT-01-ACT-EVAL-JUMP":"EDIT-01-CMP-TIMELINE"',
    "",
)

# QA-01: derive automatic progress from the registered field only.
path = "src/server/testing/controlledQaTestRuntime.ts"
content = r(path)
old = 'const done=(Number(next.values["QA-01-FLD-AUTO-PROGRESS-DONE"]??0)+1);next.values["QA-01-FLD-AUTO-PROGRESS-DONE"]=done;next.values["QA-01-FLD-AUTO-PROGRESS"]=`${done}/2`;'
new = 'const prior=String(next.values["QA-01-FLD-AUTO-PROGRESS"]??"0/2"),done=Math.min(2,(Number.parseInt(prior.split("/")[0]??"0",10)||0)+1);next.values["QA-01-FLD-AUTO-PROGRESS"]=`${done}/2`;'
if old not in content:
    raise SystemExit("QA pollution pattern missing")
w(path, content.replace(old, new, 1))

# ASSET-01: keep exact lock ref in controlled runtime memory, not projection values.
path = "src/domain/asset/controlledAssetClientTestRuntime.ts"
content = r(path)
content = content.replace(
    "let approvedCorrectionRef: string | null = null;",
    "let approvedCorrectionRef: string | null = null;\nlet lockedVersionRef: string | null = null;",
    1,
)
content = content.replace(
    'locked_version_ref: projection.values["ASSET-01-TEST-LOCK-REF"],',
    "locked_version_ref: lockedVersionRef,",
    1,
)
content = content.replace(
    'const lockRef = `TEST-ASSET-LOCK-${projection.output_version_id}`;\n    next.page_state = "LOCKED";',
    'const lockRef = `TEST-ASSET-LOCK-${projection.output_version_id}`;\n    lockedVersionRef = lockRef;\n    next.page_state = "LOCKED";',
    1,
)
content = content.replace('    next.values["ASSET-01-TEST-LOCK-REF"] = lockRef;\n', "", 1)
content = content.replace(
    "    next.output_version_id = restoredVersionRef;",
    "    lockedVersionRef = null;\n    next.output_version_id = restoredVersionRef;",
    1,
)
if "ASSET-01-TEST-LOCK-REF" in content:
    raise SystemExit("ASSET client pseudo field remains")
w(path, content)

path = "src/server/testing/controlledAssetTestRuntime.ts"
content = r(path)
content = content.replace(
    'test_run_id: "TEST-RUN-ASSET-01-CONTROLLED",',
    'test_run_id: "TEST-RUN-ASSET-CONTROLLED-01",',
    1,
)
content = content.replace(
    '  const lockedRef = state.output_version_id ? `TEST-ASSET-LOCK-${state.output_version_id}` : "—";\n',
    "",
    1,
)
old = '      "ASSET-01-TEST-LOCK-REF": lockedRef,\n      "ASSET-01-TEST-HANDOFF-REF": state.handoff_ref ?? "—",'
new = '      "ASSET-01-FLD-TRACE": state.handoff_ref ?? (state.job_counter ? `TEST-ASSET-TRACE-${state.job_counter}` : "—"),'
if old not in content:
    raise SystemExit("ASSET server pseudo fields missing")
content = content.replace(old, new, 1)
if "ASSET-01-TEST-" in content or "ASSET-01-CONTROLLED" in content:
    raise SystemExit("ASSET pseudo token remains")
w(path, content)

# VIDEO-01: remove pseudo projection lock/handoff fields and preserve exact lock operation output in runtime memory.
path = "src/domain/video/controlledVideoClientTestRuntime.ts"
content = r(path)
old = 'values={...base.values,"VIDEO-01-FLD-PAGE-STATE":"LOCKED","VIDEO-01-FLD-TASK-STATE":"LOCKED","VIDEO-01-TEST-LOCK-REF":lockRef}'
new = 'values={...base.values,"VIDEO-01-FLD-PAGE-STATE":"LOCKED","VIDEO-01-FLD-TASK-STATE":"LOCKED"}'
if old not in content:
    raise SystemExit("VIDEO client pseudo lock missing")
content = content.replace(old, new, 1)
if "VIDEO-01-TEST-" in content:
    raise SystemExit("VIDEO client pseudo token remains")
w(path, content)

path = "src/server/testing/controlledVideoTestRuntime.ts"
content = r(path)
content = content.replace(
    'test_run_id:"TEST-RUN-VIDEO-01-CONTROLLED"',
    'test_run_id:"TEST-RUN-VIDEO-CONTROLLED-01"',
    1,
)
old = ',"VIDEO-01-TEST-LOCK-REF":"—","VIDEO-01-TEST-HANDOFF-REF":state.handoff_ref??"—"'
if old not in content:
    raise SystemExit("VIDEO server pseudo fields missing")
content = content.replace(old, "", 1)
if "VIDEO-01-TEST-" in content or "VIDEO-01-CONTROLLED" in content:
    raise SystemExit("VIDEO server pseudo token remains")
w(path, content)

path = "src/components/pages/VideoVisual.tsx"
content = r(path)
old = '[busy,setBusy]=useState<VideoActionUid|null>(null),viewerRef=useRef<HTMLDivElement|null>(null);'
new = '[busy,setBusy]=useState<VideoActionUid|null>(null),lockedVersionRef=useRef<string|null>(null),viewerRef=useRef<HTMLDivElement|null>(null);'
if old not in content:
    raise SystemExit("VIDEO runtime ref insertion point missing")
content = content.replace(old, new, 1)
old = 'case"VIDEO-01-ACT-VERSION-LOCK":{const current=projection?.current_version_id;if(!current){block("VIDEO-01-ERR-VERSION-001:EXACT_VIDEO_VERSION_REQUIRED");return;}void server(action,undefined,{video_version_id:current,manifest_hash:projection?.values["VIDEO-01-FLD-HANDOFF-CONTRACT"]},false);return;}'
new = 'case"VIDEO-01-ACT-VERSION-LOCK":{const current=projection?.current_version_id;if(!current){block("VIDEO-01-ERR-VERSION-001:EXACT_VIDEO_VERSION_REQUIRED");return;}lockedVersionRef.current=null;void server(action,undefined,{video_version_id:current,manifest_hash:projection?.values["VIDEO-01-FLD-HANDOFF-CONTRACT"]},false).then(result=>{const payload=result as {value?:unknown}|null,value=payload?.value;if(!value||typeof value!=="object"||typeof (value as Record<string,unknown>).locked_version_ref!=="string"){block("VIDEO-01-ERR-VERSION-001:EXACT_LOCKED_VERSION_REF_NOT_RETURNED");return;}lockedVersionRef.current=(value as Record<string,unknown>).locked_version_ref as string;});return;}'
if old not in content:
    raise SystemExit("VIDEO lock case missing")
content = content.replace(old, new, 1)
old = 'case"VIDEO-01-ACT-HANDOFF":{const current=projection?.current_version_id,lockRef=projection?.values["VIDEO-01-TEST-LOCK-REF"];'
new = 'case"VIDEO-01-ACT-HANDOFF":{const current=projection?.current_version_id,lockRef=lockedVersionRef.current;'
if old not in content:
    raise SystemExit("VIDEO handoff hidden ref missing")
content = content.replace(old, new, 1)
if "VIDEO-01-TEST-" in content:
    raise SystemExit("VIDEO UI pseudo token remains")
w(path, content)

# EDIT-01: remove hidden projection diagnostics and keep exact lock ref in controlled runtime memory.
path = "src/domain/edit/controlledEditClientTestRuntime.ts"
content = r(path)
content = content.replace(
    "let correctionApprovedRef: string | null = null;",
    "let correctionApprovedRef: string | null = null;\nlet lockedVersionRef: string | null = null;",
    1,
)
content = content.replace(
    'test_run_id:"TEST-RUN-EDIT-01-CONTROLLED"',
    'test_run_id:"TEST-RUN-EDIT-CONTROLLED-01"',
    1,
)
content = content.replace('  next.values={...next.values,"EDIT-01-TEST-LAST-ACTION":input.action_uid};\n', "", 1)
old = 'next.values={...next.values,"EDIT-01-LBL-API-JOB":correctionCandidateRef,"EDIT-01-TEST-INTERNAL-CORRECTION-ACTION":"EDIT-01-ACT-CORRECTION-TRANSLATE"};'
if old not in content:
    raise SystemExit("EDIT hidden correction action missing")
content = content.replace(old, 'next.values={...next.values,"EDIT-01-LBL-API-JOB":correctionCandidateRef};', 1)
old = 'if(input.action_uid==="EDIT-01-ACT-VERSION-LOCK"){if(next.page_state_uid!=="EDIT-01-ST-PAGE-OUTPUT_READY"||!next.saved_edit_version_id||!next.output_version_id)return fail("OUTPUT_READY_EXACT_VERSION_REQUIRED","EDIT-01-ERR-VERSION-001");next.page_state_uid="EDIT-01-ST-PAGE-LOCKED";next.current_stage_uid="EDIT-01-STAGE-05-QA-HANDOFF";next.current_stage_phase="READY";setGate(next,"EDIT-01-GATE-CONTEXT-MUTABLE",false);setGate(next,"EDIT-01-GATE-HANDOFF",true);return ok(next,input.action_uid,{locked_version_ref:`TEST-LOCK-${next.saved_edit_version_id}`});}'
new = 'if(input.action_uid==="EDIT-01-ACT-VERSION-LOCK"){if(next.page_state_uid!=="EDIT-01-ST-PAGE-OUTPUT_READY"||!next.saved_edit_version_id||!next.output_version_id)return fail("OUTPUT_READY_EXACT_VERSION_REQUIRED","EDIT-01-ERR-VERSION-001");const lockRef=`TEST-LOCK-${next.saved_edit_version_id}`;lockedVersionRef=lockRef;next.page_state_uid="EDIT-01-ST-PAGE-LOCKED";next.current_stage_uid="EDIT-01-STAGE-05-QA-HANDOFF";next.current_stage_phase="READY";setGate(next,"EDIT-01-GATE-CONTEXT-MUTABLE",false);setGate(next,"EDIT-01-GATE-HANDOFF",true);return ok(next,input.action_uid,{locked_version_ref:lockRef});}'
if old not in content:
    raise SystemExit("EDIT lock case missing")
content = content.replace(old, new, 1)
content = content.replace(
    'if(input.action_uid==="EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT"){const draft=ref("EDIT-WORKING-DRAFT");',
    'if(input.action_uid==="EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT"){lockedVersionRef=null;const draft=ref("EDIT-WORKING-DRAFT");',
    1,
)
old = 'if(input.action_uid==="EDIT-01-ACT-HANDOFF")return invokePort(input,"EDIT-01-PORT-VOICE-QA-HANDOFF",{runId:voiceRunId},{task_id:taskId,saved_edit_version_id:p.saved_edit_version_id,output_version_id:p.output_version_id,locked_version_ref:p.values["EDIT-01-TEST-LOCK-REF"]??`TEST-LOCK-${p.saved_edit_version_id??"MISSING"}`});'
new = 'if(input.action_uid==="EDIT-01-ACT-HANDOFF"){if(!lockedVersionRef)return fail("LOCKED_VERSION_REF_REQUIRED","EDIT-01-ERR-VERSION-001");return invokePort(input,"EDIT-01-PORT-VOICE-QA-HANDOFF",{runId:voiceRunId},{task_id:taskId,saved_edit_version_id:p.saved_edit_version_id,output_version_id:p.output_version_id,locked_version_ref:lockedVersionRef});}'
if old not in content:
    raise SystemExit("EDIT handoff hidden ref missing")
content = content.replace(old, new, 1)
if "EDIT-01-TEST-" in content or "EDIT-01-CONTROLLED" in content:
    raise SystemExit("EDIT client pseudo token remains")
w(path, content)

path = "src/server/testing/controlledEditTestRuntime.ts"
content = r(path)
content = content.replace(
    'test_run_id:"TEST-RUN-EDIT-01-CONTROLLED"',
    'test_run_id:"TEST-RUN-EDIT-CONTROLLED-01"',
    1,
)
content = content.replace('  "EDIT-01-TEST-HANDOFF-REF":state.handoff_ref??"—",\n', "", 1)
if "EDIT-01-TEST-" in content or "EDIT-01-CONTROLLED" in content:
    raise SystemExit("EDIT server pseudo token remains")
w(path, content)

# DB-01: remove invented HTTP read-model route and DB-specific controlled projection injection.
base = "875224a9401d576104eabc1a6e5507869cb3c644"
subprocess.run(
    ["git", "rm", "-f", "src/app/v1/database/read-model/route.ts", "src/server/testing/controlledDbTestRuntime.ts"],
    check=True,
)
for path in ["src/server/database/dbReadModelRuntime.ts", "src/server/shared/uiProjectionRuntime.ts"]:
    w(path, subprocess.check_output(["git", "show", f"{base}:{path}"], text=True))

db_lines = [
    "import type{DbReadPortUid,DbErrorUid}from'./dbRuntimeContract';",
    "export type DbProjectionItem={ref:string;label:string;meta?:Record<string,unknown>};",
    "export type DbNormalizedProjection={page_state:string;values:Record<string,unknown>;lists:Record<string,DbProjectionItem[]>;tables:Record<string,unknown[]>;gates:Record<string,boolean>;filters:Record<string,DbProjectionItem[]>;graph:unknown;trace:unknown;audit:unknown;source_sync:string|null;};",
    "export type DbReadInput={scope?:unknown;query?:unknown};",
    "export type DbClientResult={ok:true;projection:DbNormalizedProjection;correlation_id:string}|{ok:false;error_uid:DbErrorUid;reason_code:string;correlation_id:string};",
    "export type DbClientBindings={readProjection:()=>Promise<DbClientResult>;read:(port_uid:DbReadPortUid,input:DbReadInput)=>Promise<DbClientResult>;resolveSystemLifecycle:()=>Promise<{ok:true;href:string}|{ok:false;reason_code:string}>};",
    "let binding:DbClientBindings|null=null;",
    "export function configureDbClientRuntime(next:DbClientBindings){binding=next;}",
    "export function isDbClientRuntimeBound(){return binding!==null;}",
    "export async function readDbProjection():Promise<DbClientResult>{if(!binding)return{ok:false,error_uid:'DB-01-ERR-CONTEXT-001',reason_code:'DB_CLIENT_RUNTIME_NOT_BOUND',correlation_id:'unresolved'};try{return await binding.readProjection();}catch{return{ok:false,error_uid:'DB-01-ERR-CONTEXT-001',reason_code:'DB_PROJECTION_READ_FAILED',correlation_id:'unresolved'};}}",
    "export async function invokeDbRead(port_uid:DbReadPortUid,input:DbReadInput):Promise<DbClientResult>{if(!binding)return{ok:false,error_uid:'DB-01-ERR-CONTEXT-001',reason_code:'DB_CLIENT_RUNTIME_NOT_BOUND',correlation_id:'unresolved'};try{return await binding.read(port_uid,input);}catch{return{ok:false,error_uid:'DB-01-ERR-CONTEXT-001',reason_code:'DB_READ_MODEL_QUERY_FAILED',correlation_id:'unresolved'};}}",
    "export async function openDbSystemLifecycle(){if(binding){try{return await binding.resolveSystemLifecycle();}catch{return{ok:false as const,reason_code:'SYSTEM_LIFECYCLE_ROUTE_RESOLUTION_FAILED'};}}return{ok:true as const,href:'/admin/system'};}",
]
w("src/domain/database/dbClientPort.ts", "\n".join(db_lines) + "\n")

# Hard assertions against confirmed pollution.
banned = [
    "CORE-01-PRIMARY-GRID",
    "EDIT-01-ACT-EVAL-JUMP",
    "QA-01-FLD-AUTO-PROGRESS-DONE",
    "ASSET-01-TEST-LOCK-REF",
    "ASSET-01-TEST-HANDOFF-REF",
    "VIDEO-01-TEST-LOCK-REF",
    "VIDEO-01-TEST-HANDOFF-REF",
    "EDIT-01-TEST-LAST-ACTION",
    "EDIT-01-TEST-INTERNAL-CORRECTION-ACTION",
    "EDIT-01-TEST-LOCK-REF",
    "EDIT-01-TEST-HANDOFF-REF",
    "/v1/database/read-model",
]
corpus = "\n".join(
    file.read_text(errors="ignore")
    for file in Path("src").rglob("*")
    if file.is_file() and file.suffix in {".ts", ".tsx", ".css"}
)
remaining = [token for token in banned if token in corpus]
if remaining:
    raise SystemExit("banned pollution remains: " + ",".join(remaining))

print("CURRENT_AUTHORITY_POLLUTION_PATCH_APPLIED")
