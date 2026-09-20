from __future__ import annotations
from pathlib import Path
import hashlib, json, re, shutil
from copy import deepcopy
from docx import Document
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.enum.text import WD_BREAK
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path('.')
MARKER='ACPOS-20260921-EXACT-BINDING-CLOSURE'
REPORT_DIR=ROOT/'__authority_extract__'
REPORT_DIR.mkdir(exist_ok=True)

TARGETS={
'01_ACPOS_Global_Intelligent_Brain_Information_Lifecycle_Mother_Basic_Logic_Design_Normative_Contract_v4.docx':[
 'ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_INFO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_KB-01_知識庫_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_DB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_GLOBAL_HOME_SHELL_NAVIGATION_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx',
],
'02_ACPOS_AI_Conversation_Memory_MultiAI_Assistant_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':[
 'ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_ASSET-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_VIDEO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_QA-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_STR-01_WORKSPACE_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_SYS-01_系統維護與生命週期工作區_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_DEV-01_企業自動開發系統_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_SOC-01_社群發布_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_KB-01_知識庫_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx',
],
'03_ACPOS_AI_Execution_Script_Compiler_Tool_AIAPI_Runtime_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':[
 'ACPOS_AIAPI-01_AI_API管理_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_DB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
],
'04_ACPOS_CORE_AI_Blueprint_Canonical_Script_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':[
 'ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx',
],
'05_ACPOS_Creative_Production_AI_ASSET_VIDEO_EDIT_VOICE_QA_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':[
 'ACPOS_ASSET-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_VIDEO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_QA-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_SG-02_QA審查項目名單_Mother_Basic_Design_OPTIMIZED.docx',
],
'06_ACPOS_Enterprise_Business_Development_AI_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':[
 'ACPOS_DEV-01_企業自動開發系統_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_ERP-01_ERP與財務_Mother_Basic_Design_OPTIMIZED.docx',
],
'07_ACPOS_Social_Publishing_AI_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':[
 'ACPOS_SOC-01_社群發布_Mother_Basic_Design_OPTIMIZED.docx',
],
'08_ACPOS_Strategy_Intelligence_MultiAI_Decision_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':[
 'ACPOS_STR-01_WORKSPACE_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_admin_STR-01_戰略中心後台_Mother_Basic_Design_OPTIMIZED.docx',
],
'09_ACPOS_AI_System_Engineer_Self_Inspection_Evolution_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':[
 'ACPOS_SYS-01_系統維護與生命週期工作區_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_IAM-01_帳戶與權限_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_DB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
 'ACPOS_KB-01_知識庫_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_LOGIN_IDENTITY_ENTRY_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_SG-02_QA審查項目名單_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_AIAPI-01_AI_API管理_Mother_Basic_Design_OPTIMIZED.docx',
 'ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx',
],
}

PERSISTENCE_REGISTRY=[
('GLOBAL_CONTEXT','acpos_knowledge.context_snapshots','ContextSnapshot immutable execution context','01/02/03'),
('RAW_SOURCE','acpos_knowledge.raw_source_snapshots','Captured external/source evidence snapshot','01'),
('EVIDENCE','acpos_knowledge.evidence_records','Evidence lineage and acceptance refs','01/09'),
('EXPERIENCE','acpos_knowledge.experience_records','Validated/failed learning records','01/08/09'),
('CONVERSATION','acpos_conversation.conversations','Conversation canonical metadata','02'),
('THREAD','acpos_conversation.threads','Thread/branch identity and state','02'),
('MESSAGE','acpos_conversation.messages','Durable message sequence','02'),
('MESSAGE_RELATION','acpos_conversation.message_relations','reply/citation/branch/derived edges','02'),
('ASSISTANT_RECORD','acpos_conversation.assistant_records','Assistant response/summary derived versions','02'),
('CONVERSATION_SUMMARY','acpos_conversation.summaries','Versioned summary checkpoints','02'),
('EXECUTION_JOB','acpos_runtime.execution_jobs','Stable job identity','03'),
('EXECUTION_ATTEMPT','acpos_runtime.execution_attempts','Immutable attempt lineage','03'),
('PROVIDER_PROFILE','acpos_runtime.provider_model_profiles','Provider/model profile and timeout/context settings','03'),
('PROVIDER_ROUTE','acpos_runtime.provider_route_decisions','Exact route decision','03'),
('PROVIDER_CANDIDATE_GROUP','acpos_runtime.provider_candidate_groups','Ordered provider/model candidate refs','03'),
('PROVIDER_CALLBACK','acpos_runtime.provider_callbacks','Verified callback receipts','03'),
('PROVIDER_ARTIFACT','acpos_runtime.provider_artifacts','External/generated artifact refs','03/05'),
('TOOL_REGISTRY','acpos_runtime.tool_registry','Canonical tool schema/capability/permission owner','03'),
('IDEMPOTENCY','acpos_runtime.idempotency_keys','Semantic idempotency digest/result','01/02/03'),
('OUTBOX','acpos_runtime.outbox_events','Transactional event delivery','01/03'),
('DEAD_LETTER','acpos_runtime.dead_letters','Exhausted poison/nonretryable delivery evidence','01/03'),
('CORE_PROJECT','acpos_core.projects','Project canonical state','04'),
('CORE_TOPIC','acpos_core.topics','Topic canonical state','04'),
('CORE_BLUEPRINT','acpos_core.blueprint_versions','Append-only Blueprint versions','04'),
('CORE_SCRIPT','acpos_core.canonical_script_versions','Canonical Script versions','04'),
('CORE_DNA','acpos_core.dna_versions','Role/object/scene DNA versions','04'),
('DEPARTMENT_HANDOFF','acpos_core.department_handoffs','Exact cross-department package/handoff','04/05'),
('ASSET_VERSION','acpos_media.asset_versions','Asset candidate/locked versions','05'),
('LAYER_DOCUMENT','acpos_media.layer_documents','Layer/patch/composite document and layers','05'),
('VIDEO_VERSION','acpos_media.video_versions','Video/scenes/shots/time-range versions','05'),
('EDIT_VERSION','acpos_media.edit_versions','Timeline/edit output versions','05'),
('QA_RUN','acpos_qa.qa_runs','QA execution/evaluation result','05'),
('QA_FINDING','acpos_qa.qa_findings','QA finding and remediation state','05/09'),
('ENTERPRISE_PROFILE','acpos_enterprise.discovery_profiles','Enterprise discovery profile','06'),
('ENTERPRISE_SIGNAL','acpos_enterprise.market_signals','Market signal/evidence decision','06'),
('ENTERPRISE_COMPANY','acpos_enterprise.companies','Resolved company identity','06'),
('ENTERPRISE_OPPORTUNITY','acpos_enterprise.opportunities','Opportunity lifecycle','06'),
('ENTERPRISE_CAMPAIGN','acpos_enterprise.outreach_campaigns','Campaign and exact approved version','06'),
('ENTERPRISE_DELIVERY','acpos_enterprise.delivery_attempts','Per-recipient delivery attempt/result','06'),
('ERP_CONNECTOR','acpos_erp.connectors','ERP connector and mapping refs','06'),
('ERP_SYNC','acpos_erp.sync_jobs','ERP snapshot/sync lineage','06'),
('SOCIAL_ACCOUNT','acpos_social.account_bindings','Social account/credential references','07'),
('SOCIAL_TARGET','acpos_social.market_targets','Target identity/state/policy','07'),
('SOCIAL_DISCOVERY','acpos_social.target_discovery_jobs','Target discovery lineage','07'),
('SOCIAL_PUBLISH','acpos_social.publish_requests','Target-scoped publish request','07'),
('SOCIAL_ATTEMPT','acpos_social.publish_attempts','Provider/platform publish attempt','07'),
('SOCIAL_CALLBACK','acpos_social.platform_callbacks','External callback/result','07'),
('SOCIAL_METRIC','acpos_social.metrics_snapshots','Real analytics snapshot','07'),
('STRATEGY_TOPIC','acpos_strategy.strategy_topics','Strategy topic/context','08'),
('STRATEGY_CANDIDATE','acpos_strategy.strategy_candidates','Append-only strategy candidate versions','08'),
('STRATEGY_REVIEW','acpos_strategy.strategy_reviews','Human strategy review','08'),
('STRATEGY_DECISION','acpos_strategy.strategy_decisions','Decision ledger','08'),
('STRATEGY_FEEDBACK','acpos_strategy.strategy_feedback','Expected/actual/KPI/learning feedback','08'),
('SYSTEM_CHANGE','acpos_system.system_changes','Governed system change','09'),
('SYSTEM_CANDIDATE','acpos_system.change_candidates','Change candidate versions','09'),
('VALIDATION_RUN','acpos_system.validation_runs','Sandbox/test/regression evidence','09'),
('SYSTEM_FINDING','acpos_system.findings','Inspection finding lifecycle','09'),
('TRACE_EDGE','acpos_system.trace_edges','Forward/reverse functional trace graph','09'),
('INCIDENT','acpos_system.incidents','Incident/maintenance state','09'),
('CHECKPOINT','acpos_system.checkpoints','Resume/checkpoint state','09'),
('IAM_ACCOUNT','acpos_iam.accounts','Account identity','09'),
('IAM_PERMISSION','acpos_iam.permission_assignments','Exact permission assignments','09'),
('IAM_GRANT','acpos_iam.resource_grants','Resource/scope/condition grants','09'),
('AUDIT','acpos_audit.audit_events','Correlation/audit terminal truth','01-09'),
]

RUNTIME_NUMERIC=[
('CONV_UI_INITIAL_LOAD_MESSAGES','50','Initial visible history page','02'),
('CONV_UI_LAZY_LOAD_MESSAGES','50','Each older-history fetch','02'),
('CONV_UI_MAX_RENDERED_MESSAGES','200','Virtualize/unmount older DOM rows; never delete persistence','02'),
('CONV_AI_RECENT_VERBATIM_MESSAGES','24','Newest durable messages kept verbatim when budget permits','02'),
('CONV_SUMMARY_CHECKPOINT_MESSAGES','50','Create versioned summary at 50 durable messages or earlier pressure trigger','02'),
('CONV_SUMMARY_TRIGGER_INPUT_RATIO','0.80','Summarize/dedupe P2-P7 before request when candidate input exceeds 80% of computed input budget','02'),
('CONV_CONTEXT_INPUT_RATIO','0.70','70% of provider max_context reserved for input; hard cap below','02'),
('CONV_CONTEXT_OUTPUT_RESERVE_RATIO','0.20','20% of provider max_context reserved for model output','02'),
('CONV_CONTEXT_SAFETY_RESERVE_RATIO','0.10','10% reserved for tool/system expansion','02'),
('CONV_CONTEXT_INPUT_HARD_CAP_TOKENS','96000','Provider-neutral maximum input budget','02'),
('CONV_OUTPUT_HARD_CAP_TOKENS','16000','Provider-neutral output reserve cap','02'),
('CONV_ACTIVE_GENERATION_PER_THREAD','1','No silent interleave','02'),
('CONV_PENDING_MESSAGE_QUEUE_DEPTH','8','9th concurrent submission returns CONVERSATION_BUSY','02'),
('CONV_STREAM_HEARTBEAT_SECONDS','15','Streaming liveness heartbeat','02/03'),
('CONV_STREAM_IDLE_TIMEOUT_SECONDS','60','No chunk/heartbeat beyond this = transient failure','02/03'),
('CONV_COMPOSER_DRAFT_TTL_HOURS','24','Transient composer state only','02'),
('CONV_SEND_IDEMPOTENCY_TTL_HOURS','24','Duplicate SEND_MESSAGE suppression window','02'),
('CONV_RETENTION_AFTER_PROJECT_CLOSE_DAYS','365','Conversation/message metadata/content if unreferenced; references extend retention','01/02'),
('CONV_ARCHIVE_HARD_DELETE_ELIGIBLE_DAYS','365','After archive and only when no decision/evidence/audit dependency remains','02'),
('HTTP_CONNECT_TIMEOUT_SECONDS','10','Shared outbound HTTP connect timeout','03'),
('HTTP_SYNC_RESPONSE_TIMEOUT_SECONDS','60','Synchronous text/tool request upper bound','03'),
('PROVIDER_SUBMIT_TIMEOUT_SECONDS','30','Async provider submit/ack request','03'),
('JOB_TEXT_HARD_TIMEOUT_SECONDS','180','TEXT/TEXT_CHAT capability job','03'),
('JOB_IMAGE_HARD_TIMEOUT_SECONDS','900','IMAGE capability job','03/05'),
('JOB_AUDIO_HARD_TIMEOUT_SECONDS','1800','AUDIO/VOICE capability job','03/05'),
('JOB_VIDEO_HARD_TIMEOUT_SECONDS','7200','VIDEO capability job','03/05'),
('RUNTIME_MAX_ATTEMPTS','3','1 initial + at most 2 automatic retries','01/03'),
('RUNTIME_BACKOFF_BASE_SECONDS','2','Exponential backoff base','01/03'),
('RUNTIME_BACKOFF_FACTOR','2','Backoff factor','01/03'),
('RUNTIME_BACKOFF_MAX_SECONDS','30','Backoff cap excluding Retry-After','01/03'),
('RUNTIME_RETRY_AFTER_MAX_SECONDS','120','Maximum honored provider Retry-After before async reschedule','03'),
('RUNTIME_JITTER','FULL_JITTER','random(0,min(cap,base*factor^(attempt-1)))','03'),
('CIRCUIT_FAILURE_THRESHOLD','5','Retryable failures','03'),
('CIRCUIT_FAILURE_WINDOW_SECONDS','60','Window for threshold','03'),
('CIRCUIT_OPEN_COOLDOWN_SECONDS','60','Open to half-open','03'),
('CIRCUIT_HALF_OPEN_PROBES','1','Concurrent half-open probe','03'),
('CIRCUIT_CLOSE_SUCCESS_COUNT','2','Consecutive successful probes/executions to close','03'),
('WORKER_HEARTBEAT_SECONDS','15','Worker lease heartbeat','03'),
('WORKER_LEASE_GRACE_SECONDS','60','Missed heartbeat grace before stale lease handling','03'),
('CALLBACK_DEDUPE_TTL_DAYS','7','Callback replay/dedupe evidence','03'),
('EXECUTION_IDEMPOTENCY_TTL_DAYS','7','Execution job semantic duplicate suppression','03'),
('BUSINESS_EFFECT_IDEMPOTENCY_TTL_DAYS','30','External publish/delivery/handoff/mutation duplicate suppression','01/03/06/07/08/09'),
('OUTBOX_DELIVERED_RETENTION_DAYS','30','Delivered outbox audit retention when otherwise unreferenced','01/03'),
('DEAD_LETTER_RETENTION_DAYS','90','DLQ/quarantine minimum retention','01/03/09'),
('CANDIDATE_UNREFERENCED_TTL_DAYS','30','Generic unadopted candidate cleanup','01'),
('CONTEXT_SNAPSHOT_UNREFERENCED_TTL_DAYS','90','After last dependent lineage closes','01'),
('RAW_SOURCE_UNREFERENCED_TTL_DAYS','180','Subject to rights/legal/privacy override','01'),
('EVIDENCE_MIN_RETENTION_AFTER_CLOSE_DAYS','365','References/legal hold extend','01/09'),
('EXPERIENCE_RETIRED_RETENTION_DAYS','365','Retired/unreferenced experience','01/08/09'),
('SEMANTIC_INDEX_REBUILD_TTL_DAYS','30','Derivative index; source retention separate','01'),
('RECRAWL_CRITICAL_MINUTES','15','Freshness class CRITICAL','01/06'),
('RECRAWL_HIGH_MINUTES','60','Freshness class HIGH','01/06'),
('RECRAWL_NORMAL_MINUTES','360','Freshness class NORMAL','01/06'),
('RECRAWL_LOW_MINUTES','1440','Freshness class LOW','01/06'),
('EXPERIENCE_AUTO_USE_MIN_VALIDATED_RECORDS','3','Before repeated pattern may influence automated recommendation','01/08'),
('EXPERIENCE_AUTO_USE_MIN_INDEPENDENT_CONTEXTS','2','Avoid single-run overfit','01/08'),
]

SHARED_API=[
('CONVERSATION_CREATE','POST /v1/conversations','acpos_conversation.conversations','conversation.create'),
('CONVERSATION_MESSAGE_SEND','POST /v1/conversations/{conversationId}/messages','acpos_conversation.messages','conversation.write'),
('CONVERSATION_GENERATION_STOP','POST /v1/conversations/{conversationId}/generation/stop','acpos_conversation.messages + acpos_runtime.execution_jobs','conversation.write'),
('CONVERSATION_BRANCH_CREATE','POST /v1/conversations/{conversationId}/branches','acpos_conversation.threads','conversation.branch.create'),
('CONVERSATION_SUMMARY_CREATE','POST /v1/conversations/{conversationId}/summaries','acpos_conversation.summaries','conversation.summary.create'),
('EXECUTION_JOB_CREATE','POST /v1/execution-jobs','acpos_runtime.execution_jobs','runtime.execute'),
('EXECUTION_JOB_RETRY','POST /v1/execution-jobs/{jobId}/retry','acpos_runtime.execution_attempts','runtime.retry'),
('EXECUTION_JOB_CANCEL','POST /v1/execution-jobs/{jobId}/cancel','acpos_runtime.execution_jobs','runtime.cancel'),
('PROVIDER_CALLBACK','POST /v1/provider-callbacks/{providerKey}','acpos_runtime.provider_callbacks','runtime.callback.accept'),
('TOOL_EXECUTE','POST /v1/tools/{toolUid}/execute','acpos_runtime.execution_attempts','tool.execute'),
('CONTEXT_SNAPSHOT_CREATE','POST /v1/context-snapshots','acpos_knowledge.context_snapshots','context.snapshot.create'),
('AUDIT_APPEND','POST /v1/audit-events','acpos_audit.audit_events','audit.append'),
('SYSTEM_CHANGE_CREATE','POST /v1/system-changes','acpos_system.system_changes','system.change.create'),
('SYSTEM_CANDIDATE_CREATE','POST /v1/system-changes/{changeId}/candidates','acpos_system.change_candidates','system.change.propose'),
('VALIDATION_RUN_CREATE','POST /v1/validation-runs','acpos_system.validation_runs','system.test.execute'),
]

ENV_BINDINGS=[
('DATABASE_URL','PostgreSQL connection for all acpos_* schemas','Secret manager / deployment environment','Required'),
('REDIS_URL','Queue/worker/DLQ runtime','Secret manager / deployment environment','Required for async execution'),
('OBJECT_STORAGE_URL','Artifact/media object store base','Deployment environment','Required for media artifacts'),
('OBJECT_STORAGE_SIGNING_KEY_REF','Signed URI key reference, never plaintext in Word/UI','Secret manager','Required'),
('ACPOS_SECRET_BACKEND','Credential resolver backend identity','Deployment environment','Required'),
('ACPOS_DEPLOYMENT_TARGET_ID','Production deployment target/project identity','Deployment environment','Required for release execution'),
('ACPOS_PRODUCTION_BASE_URL','Production acceptance target','Deployment environment','Required for post-deploy acceptance'),
]

KEYWORDS=re.compile(r'(uid|control|action|gate|permission|port|operation|method|path|payload|data|state|error|handoff|runtime|route|api|entity|section|component|field|binding|acceptance|workflow|transition|owner|persistence|database|provider|event|audit|recovery|next)',re.I)

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def norm(s):
    return re.sub(r'\s+',' ',str(s or '').strip())

def slug(s):
    s=re.sub(r'([a-z0-9])([A-Z])',r'\1-\2',s)
    s=re.sub(r'[^A-Za-z0-9]+','-',s).strip('-').upper()
    return s[:72] or 'OP'

def kebab(s):
    s=re.sub(r'([a-z0-9])([A-Z])',r'\1-\2',s)
    return re.sub(r'[^A-Za-z0-9]+','-',s).strip('-').lower()

def page_uid_from_doc(doc:Document,name:str):
    for t in doc.tables:
        for row in t.rows[:10]:
            vals=[norm(c.text) for c in row.cells]
            if len(vals)>=2 and vals[0].lower().replace(' ','')=='pageuid':
                return vals[1]
    m=re.search(r'ACPOS_([^_]+)',name)
    return m.group(1) if m else Path(name).stem

def table_rows(t):
    return [[norm(c.text) for c in row.cells] for row in t.rows]

def is_relevant_table(rows):
    if not rows:return False
    text=' | '.join(' | '.join(r) for r in rows[:4])
    return bool(KEYWORDS.search(text))

def set_repeat_table_header(row):
    trPr=row._tr.get_or_add_trPr()
    tblHeader=OxmlElement('w:tblHeader')
    tblHeader.set(qn('w:val'),'true')
    trPr.append(tblHeader)

def shade(cell,fill='EDE9FE'):
    tcPr=cell._tc.get_or_add_tcPr()
    shd=OxmlElement('w:shd');shd.set(qn('w:fill'),fill);tcPr.append(shd)

def add_table(doc, headers, rows, font_size=7):
    tbl=doc.add_table(rows=1, cols=len(headers))
    tbl.style='Table Grid'
    hdr=tbl.rows[0]
    set_repeat_table_header(hdr)
    for i,h in enumerate(headers):
        hdr.cells[i].text=str(h)
        shade(hdr.cells[i])
    for row in rows:
        cells=tbl.add_row().cells
        for i,v in enumerate(row):
            if i<len(cells): cells[i].text=str(v)
    for row in tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size=Pt(font_size)
    return tbl

def add_heading(doc,text,level=1):
    p=doc.add_paragraph(style=f'Heading {min(level,9)}')
    p.add_run(text)
    return p

def add_landscape_section(doc):
    sec=doc.add_section(WD_SECTION.NEW_PAGE)
    sec.orientation=WD_ORIENT.LANDSCAPE
    sec.page_width,sec.page_height=sec.page_height,sec.page_width
    sec.top_margin=Inches(0.45);sec.bottom_margin=Inches(0.45)
    sec.left_margin=Inches(0.45);sec.right_margin=Inches(0.45)
    return sec

def insert_notice(doc):
    marker_text=f'[{MARKER}] Construction Authority Notice'
    if any(MARKER in p.text for p in doc.paragraphs):
        return False
    p0=doc.paragraphs[0] if doc.paragraphs else doc.add_paragraph()
    n=p0.insert_paragraph_before()
    n.style='Intense Quote' if 'Intense Quote' in [s.name for s in doc.styles] else doc.styles['Normal']
    n.add_run(marker_text+'\n').bold=True
    n.add_run('本文件已加入 2026-09-21 Exact Binding Closure。施工時 MUST 讀取文末 Closure Annex；文中較早的 REQUIRE_EXACT_BINDING 對已列入 Resolution Ledger 的項目視為已被本次 closure 精確綁定。外部 secret/provider/platform 的實際值只可由已註冊 Runtime Profile / Environment Binding 解析，缺值 = BLOCK，不得猜。')
    return True

def operation_api_rows(doc):
    out=[]
    for t in doc.tables:
        rr=table_rows(t)
        for row in rr:
            for i,c in enumerate(row):
                if re.match(r'^(GET|POST|PATCH|PUT|DELETE)\s+/',c,re.I):
                    op=row[i-1] if i>0 else ''
                    if op and not re.match(r'^(GET|POST|PATCH|PUT|DELETE)',op,re.I):
                        out.append((op,c,row))
    return out

def control_rows(doc):
    out=[]
    for t in doc.tables:
        rr=table_rows(t)
        if not rr:continue
        header=[x.lower() for x in rr[0]]
        if any('control uid' in x for x in header) or (header and header[0]=='control'):
            for row in rr[1:]:
                if row and row[0]:
                    out.append(row)
    return out

def persistence_for(page_uid,op,path=''):
    s=(op+' '+path).lower()
    rules=[
      (r'conversation.*message|sendconversationmessage','acpos_conversation.messages'),
      (r'conversation.*branch','acpos_conversation.threads'),
      (r'conversation.*summary','acpos_conversation.summaries'),
      (r'provider.*credential|credential','secret-manager://provider-credentials + acpos_runtime.provider_credential_refs'),
      (r'provider.*profile','acpos_runtime.provider_model_profiles'),
      (r'candidategroup','acpos_runtime.provider_candidate_groups'),
      (r'providerroute|route decision|executeproviderroute','acpos_runtime.provider_route_decisions + acpos_runtime.execution_jobs'),
      (r'quarantine','acpos_runtime.provider_quarantine'),
      (r'sandboxtest|sandbox','acpos_runtime.sandbox_runs'),
      (r'queueprobe','acpos_runtime.queue_probe_runs'),
      (r'killswitch','acpos_runtime.kill_switch_states'),
      (r'project','acpos_core.projects'),
      (r'topic','acpos_core.topics'),
      (r'blueprint','acpos_core.blueprint_versions'),
      (r'canonicalscript|scriptversion','acpos_core.canonical_script_versions'),
      (r'dna','acpos_core.dna_versions'),
      (r'handoff','acpos_core.department_handoffs'),
      (r'layer','acpos_media.layer_documents'),
      (r'asset','acpos_media.asset_versions'),
      (r'video|scene|shot','acpos_media.video_versions'),
      (r'edit|timeline','acpos_media.edit_versions'),
      (r'qa|finding|reviewstandard','acpos_qa.qa_runs + acpos_qa.qa_findings'),
      (r'discoveryprofile','acpos_enterprise.discovery_profiles'),
      (r'signal','acpos_enterprise.market_signals'),
      (r'company|contact','acpos_enterprise.companies'),
      (r'opportunity','acpos_enterprise.opportunities'),
      (r'outreachcampaign|campaign','acpos_enterprise.outreach_campaigns'),
      (r'dispatch|delivery','acpos_enterprise.delivery_attempts'),
      (r'erp.*connector|erpmapping','acpos_erp.connectors'),
      (r'erpsnapshot|erpsync','acpos_erp.sync_jobs'),
      (r'financefact|forecast|capacity','READ_MODEL / acpos_erp.sync_jobs'),
      (r'social.*account|accountbinding','acpos_social.account_bindings'),
      (r'social.*target|targetdiscovery|targetjoin','acpos_social.market_targets + acpos_social.target_discovery_jobs'),
      (r'publish','acpos_social.publish_requests + acpos_social.publish_attempts'),
      (r'draft|candidate','acpos_system.change_candidates' if 'sys' in page_uid.lower() else 'domain_candidate_store'),
      (r'strategyreview|strategycandidate|adoptascontextcandidate','acpos_strategy.strategy_candidates + acpos_strategy.strategy_reviews'),
      (r'systemchange|changerequest|candidate','acpos_system.system_changes + acpos_system.change_candidates'),
      (r'validation|test','acpos_system.validation_runs'),
      (r'permission|grant|account','acpos_iam.permission_assignments + acpos_iam.resource_grants'),
      (r'knowledge|experience','acpos_knowledge.knowledge_items + acpos_knowledge.experience_records'),
      (r'contextcandidate','acpos_knowledge.context_candidates'),
      (r'export|search|refresh|getui|get.*projection|compare','READ_MODEL / N/A_WRITE'),
    ]
    for pat,val in rules:
        if re.search(pat,s):
            return val
    defaults={
      'CORE-01':'acpos_core.projects',
      'ASSET-01':'acpos_media.asset_versions','VIDEO-01':'acpos_media.video_versions','EDIT-01':'acpos_media.edit_versions',
      'QA-01':'acpos_qa.qa_runs','admin:DEV-01':'acpos_enterprise.opportunities','admin:ERP-01':'acpos_erp.connectors',
      'admin:SOC-01':'acpos_social.publish_requests','workspace:STR-01':'acpos_strategy.strategy_candidates','admin:STR-01':'acpos_strategy.strategy_candidates',
      'admin:SYS-01':'acpos_system.system_changes','admin:IAM-01':'acpos_iam.resource_grants','admin:DB-01':'acpos_system.trace_edges',
      'admin:KB-01':'acpos_knowledge.knowledge_items','workspace:INFO-01':'acpos_knowledge.context_candidates',
      'admin:AIAPI-01':'acpos_runtime.provider_model_profiles','identity:login':'acpos_iam.accounts','workspace:WB-01':'READ_MODEL / N/A_WRITE'
    }
    return defaults.get(page_uid,'DOMAIN_OWNER_TABLE_FROM_EMBEDDED_BINDING')

def add_runtime_policy(doc,target_name):
    add_heading(doc,'A. Shared Runtime Quantitative Policy / 共用 Runtime 定量政策',2)
    doc.add_paragraph('Authority Status: CLOSURE_DECISION_NEW_AUTHORITY_PER_USER_DIRECTIVE_20260921_AFTER_FULL_SOURCE_AUDIT. 這些數值僅補足原文件明確標示的 numeric REQUIRE_EXACT_BINDING；Provider/Platform 自身限制仍由 registered profile/policy 解析，無 profile 值時 BLOCK。')
    rows=[r for r in RUNTIME_NUMERIC if any(x.strip() in target_name[:2] or x.strip() in target_name for x in [])]
    # Include all shared policies in 01-03; scoped subset elsewhere for standalone construction readability.
    prefix=target_name[:2]
    if prefix in {'01','02','03'}:
        chosen=RUNTIME_NUMERIC
    elif prefix=='05':
        chosen=[r for r in RUNTIME_NUMERIC if r[0].startswith(('JOB_','HTTP_','PROVIDER_','RUNTIME_','CIRCUIT_','WORKER_','CALLBACK_','EXECUTION_','BUSINESS_'))]
    elif prefix in {'06','07','08','09'}:
        chosen=[r for r in RUNTIME_NUMERIC if r[0].startswith(('HTTP_','RUNTIME_','CIRCUIT_','BUSINESS_','OUTBOX_','DEAD_','WORKER_'))]
    else:
        chosen=[r for r in RUNTIME_NUMERIC if r[3] in prefix or prefix in r[3]]
    add_table(doc,['Policy UID','Exact Value','Semantics','Primary Owner'],chosen,7)

def add_persistence(doc,target_name):
    add_heading(doc,'B. Canonical Persistence / Provider Registry',2)
    prefix=target_name[:2]
    chosen=[r for r in PERSISTENCE_REGISTRY if prefix in r[3] or r[3]=='01-09']
    if prefix in {'01','03','09'}:
        chosen=PERSISTENCE_REGISTRY
    add_table(doc,['Binding','Exact Persistence / Provider Owner','Purpose','Document Owner'],chosen,7)
    doc.add_paragraph('DB naming is normative for this design closure. All tables are PostgreSQL logical owners under the shown schema. RLS/permission checks remain server-enforced. Secret values are never stored in these Word files; only secret references are persisted.')

def add_shared_api(doc,target_name):
    add_heading(doc,'C. Shared Exact API / Permission Bindings',2)
    prefix=target_name[:2]
    chosen=SHARED_API if prefix in {'01','02','03','09'} else [r for r in SHARED_API if ('CONVERSATION' in r[0] and prefix in {'04','05','08'}) or ('AUDIT' in r[0])]
    add_table(doc,['Operation UID','Exact Method / Path','Persistence Owner','Permission'],chosen,7)
    if prefix in {'03','09'}:
        add_heading(doc,'C.1 Environment / Secret / Deployment Bindings',3)
        add_table(doc,['Binding Key','Meaning','Owner','Required'],ENV_BINDINGS,7)

def add_source_snapshot(doc,source_path:Path):
    sdoc=Document(source_path)
    page_uid=page_uid_from_doc(sdoc,source_path.name)
    add_heading(doc,f'Source Authority Snapshot — {page_uid}',3)
    doc.add_paragraph(f'Source File: {source_path.name}')
    doc.add_paragraph(f'Source SHA-256: {sha256(source_path)}')
    relevant=[]
    for i,t in enumerate(sdoc.tables,1):
        rr=table_rows(t)
        if is_relevant_table(rr):
            relevant.append((i,rr))
    doc.add_paragraph(f'Included binding/data/state tables: {len(relevant)}. These rows are copied verbatim in text value from the uploaded Basic Design source; no UID/value renaming is performed.')
    for idx,rr in relevant:
        if not rr:continue
        add_heading(doc,f'{page_uid} · Source Table {idx}',4)
        maxcols=max(len(r) for r in rr)
        hdr=rr[0]+['']*(maxcols-len(rr[0]))
        data=[r+['']*(maxcols-len(r)) for r in rr[1:]]
        if len(hdr)>12:
            # avoid unreadable tables; serialize wide source rows losslessly.
            for row in rr:
                doc.add_paragraph(' | '.join(row),style='Normal')
        else:
            add_table(doc,hdr,data,6.5)

    # Build exact effectful operation -> API -> persistence rows.
    api=operation_api_rows(sdoc)
    controls=control_rows(sdoc)
    existing_ops=set()
    exact=[]
    for row in controls:
        uid=row[0]
        op=''
        for c in row[1:]:
            if re.match(r'^[a-z][A-Za-z0-9]+$',c) and re.match(r'^(get|create|update|delete|set|run|execute|approve|decide|request|save|refresh|search|export|adopt|restore|retire|dispatch|stop|retry|configure|validate|complete|start|pause|resume)',c):
                op=c;break
            if re.match(r'^[A-Z0-9]+-\d+-ACT-',c):
                op=c;break
        if op:
            existing_ops.add(op)
    api_map={op:path for op,path,_ in api}
    # Source exact controls where direct operation name is known.
    for row in controls:
        uid=row[0]
        op=''
        permission=''
        gate=''
        for c in row[1:]:
            if re.match(r'^[a-z][A-Za-z0-9]+$',c) and re.match(r'^(get|create|update|delete|set|run|execute|approve|decide|request|save|refresh|search|export|adopt|restore|retire|dispatch|stop|retry|configure|validate|complete|start|pause|resume)',c):
                op=c
            if 'GATE-' in c: gate=c
        permission=row[-1] if len(row)>=2 else ''
        if op:
            path=api_map.get(op,'SOURCE_ACTION_PORT_TABLE')
            exact.append((page_uid,uid,'EXISTING_CONTROL_UID',op,path,persistence_for(page_uid,op,path),gate,permission,'SOURCE_AUTHORITY'))
    # Materialize a stable control UID only for effectful/API operations not already mapped to an explicit control.
    verbs=re.compile(r'^(create|update|delete|set|run|execute|approve|decide|request|save|refresh|search|export|adopt|restore|retire|dispatch|stop|retry|configure|validate|complete|start|pause|resume)',re.I)
    page_prefix=re.sub(r'^(workspace:|admin:|identity:)','',page_uid).replace(':','-').upper()
    for op,path,_ in api:
        if op in existing_ops or op=='getUiProjection': continue
        method=path.split(' ',1)[0].upper()
        if method=='GET' and not verbs.match(op): continue
        uid=f'{page_prefix}-BTN-{slug(op)}'
        exact.append((page_uid,uid,'NEW_UID_FROM_EXISTING_OPERATION',op,path,persistence_for(page_uid,op,path),'SERVER_STATE_GATE','SOURCE_PERMISSION_OR_OPERATION_SCOPE','CLOSURE_MATERIALIZED'))
    # de-dupe
    seen=set(); rows=[]
    for r in exact:
        k=(r[0],r[1],r[3],r[4])
        if k in seen:continue
        seen.add(k);rows.append(r)
    if rows:
        add_heading(doc,f'{page_uid} · Effectful Control → API → DB Closure Matrix',4)
        add_table(doc,['Page UID','Control UID','UID Status','Operation/Action','Method / Path','DB / Provider Owner','Gate','Permission','Binding Status'],rows,6.3)
    return {'page_uid':page_uid,'source':source_path.name,'sha256':sha256(source_path),'binding_rows':len(rows),'source_tables':len(relevant)}

def add_resolution_ledger(doc,target_name):
    add_heading(doc,'D. Legacy REQUIRE_EXACT_BINDING Resolution Ledger',2)
    prefix=target_name[:2]
    rows=[
      ('API / Route identities','RESOLVED','Embedded Page/Port tables + Shared Exact API table; where an uploaded page exposed an operation without Control UID, this closure materializes a UID from that existing operation only.'),
      ('DB / Persistence identities','RESOLVED','Canonical Persistence / Provider Registry in this annex.'),
      ('Permission / Gate identities','RESOLVED_FOR_DOCUMENT_SCOPE','Embedded source Permission/Gate tables; server re-check mandatory. Environment/provider-specific grants resolve from registered IAM/Profile, missing = BLOCK.'),
      ('Event transport / outbox','RESOLVED','PostgreSQL acpos_runtime.outbox_events + worker delivery; at-least-once + idempotent consumer.'),
      ('Queue / Worker / DLQ','RESOLVED','Redis-backed shared runtime via REDIS_URL; dead-letter evidence in acpos_runtime.dead_letters.'),
      ('Canonical digest','RESOLVED','RFC 8785 JSON Canonicalization Scheme + SHA-256 for semantic payload/context digests.'),
      ('Idempotency store / TTL','RESOLVED','acpos_runtime.idempotency_keys + exact TTL rows in Runtime Quantitative Policy.'),
      ('Retry / Backoff / Circuit numeric values','RESOLVED','Exact values in Runtime Quantitative Policy.'),
      ('Conversation display/context/summary numbers','RESOLVED' if prefix=='02' else 'RESOLVED_BY_AI02','AI-02 annex provides exact UI/history/context/compression values.'),
      ('Retention durations','RESOLVED','Artifact-class values in Runtime Quantitative Policy; references/legal/privacy holds extend retention and never shorten below legal/domain requirement.'),
      ('Secret backend','RESOLVED','ACPOS_SECRET_BACKEND + secret reference only; plaintext never persisted in Word/UI/general DB.'),
      ('Provider/model exact selection','RESOLVED_RUNTIME_PROFILE','Exact provider_model_profile_id and route decision from AIAPI-01 registered profile; no page-level picker.'),
      ('External platform/provider rate limits','RESOLVED_PROFILE_REQUIRED','Exact value comes from registered provider/platform/target policy fields; no global guessed fallback; missing profile value blocks effectful execution.'),
      ('Production deployment target','RESOLVED_ENV_BINDING','ACPOS_DEPLOYMENT_TARGET_ID + ACPOS_PRODUCTION_BASE_URL; values supplied by deployment environment, not hardcoded in design.'),
    ]
    add_table(doc,['Legacy Gap Class','2026-09-21 Status','Exact Resolution'],rows,7)
    doc.add_paragraph('Interpretation Rule: earlier REQUIRE_EXACT_BINDING text remains a generic anti-invention invariant for future unknowns. It MUST NOT be interpreted as an open gap for rows marked RESOLVED/RESOLVED_* in this ledger.')

def add_conversation_cross_page(doc,sources):
    add_heading(doc,'E. Cross-page Shared Conversation Control Binding',2)
    rows=[]
    kw=re.compile(r'(conversation|message|assistant|multi.?ai|single.?ai|send|stop|thread|branch|summary|attach)',re.I)
    for sp in sources:
        sd=Document(sp)
        page=page_uid_from_doc(sd,sp.name)
        for t in sd.tables:
            rr=table_rows(t)
            for row in rr:
                if not row or not kw.search(' | '.join(row)): continue
                uid=next((c for c in row if re.search(r'-(BTN|CTL|INP|TGL|VIEW|FLD)-',c)), '')
                act=next((c for c in row if re.search(r'-ACT-',c) or (re.match(r'^[a-z][A-Za-z0-9]+$',c) and re.match(r'^(send|stop|create|adopt|prepare)',c,re.I))), '')
                if uid or act:
                    rows.append((page,uid or 'SOURCE_CONTROL_NOT_UID_MATERIALIZED',act,' | '.join(row[:8])))
    # de-dupe and cap duplicate echoes from related tables
    out=[];seen=set()
    for r in rows:
        k=(r[0],r[1],r[2],r[3])
        if k in seen:continue
        seen.add(k);out.append(r)
    add_table(doc,['Page UID','Control UID','Action / Operation','Source Binding Context'],out,6.2)

def main():
    report={'marker':MARKER,'targets':{},'new_authority_note':'User-directed exact binding closure after uploaded-source audit.'}
    for target,sources in TARGETS.items():
        tp=ROOT/target
        if not tp.exists():
            raise SystemExit(f'MISSING_TARGET:{target}')
        doc=Document(tp)
        if any(MARKER in p.text for p in doc.paragraphs):
            report['targets'][target]={'status':'ALREADY_APPLIED'}
            continue
        insert_notice(doc)
        add_landscape_section(doc)
        add_heading(doc,'2026-09-21 Construction Exact Binding Closure / 施工精確綁定封板',1)
        doc.add_paragraph(f'Closure UID: {MARKER}')
        doc.add_paragraph('Scope: 將 01～09 母級邏輯與已上傳 Basic Design 的 Page / Control / Action / Gate / Permission / API / Runtime / DB-Provider / State / Error / Handoff 做可施工 materialization。Source-derived rows are copied from uploaded Word values; newly created exact identities/numeric policy are explicitly marked as closure authority.')
        add_runtime_policy(doc,target)
        add_persistence(doc,target)
        add_shared_api(doc,target)
        add_resolution_ledger(doc,target)
        if target.startswith('02_'):
            add_conversation_cross_page(doc,[ROOT/x for x in sources if (ROOT/x).exists()])
        add_heading(doc,'F. Uploaded Basic Design Exact Binding Snapshots',2)
        sr=[]
        for s in sources:
            sp=ROOT/s
            if not sp.exists():
                doc.add_paragraph(f'MISSING SOURCE — {s}')
                sr.append({'source':s,'status':'MISSING'})
                continue
            sr.append(add_source_snapshot(doc,sp))
        add_heading(doc,'G. Construction Handoff Rule',2)
        doc.add_paragraph('施工 AI MUST resolve each UI control through this exact order: Page UID → Section/Region → Control UID → Trigger/Operation or Action UID → Gate → Permission → Input/Payload → Method/Path or shared Runtime Operation → Persistence/Provider Owner → Audit/Event → Success/Failure/Recovery → Next Page/Handoff. UI_ONLY/READ_ONLY controls MUST NOT create a write API. System-only operations MUST NOT cause a new visible button unless this closure/source explicitly materializes that control.')
        doc.add_paragraph('When a provider/platform/environment value is runtime-specific, the exact binding is the registered Profile/Policy/Environment key named in this annex. Missing required value is a deterministic BLOCK; it is not permission to guess.')
        doc.save(tp)
        # Re-open structural validation.
        Document(tp)
        report['targets'][target]={'status':'UPDATED','sha256':sha256(tp),'sources':sr}
    (REPORT_DIR/'SYSTEM_BINDING_CLOSURE_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    main()
