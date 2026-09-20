from pathlib import Path
import json,re,hashlib
from docx import Document
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path('.')
REPORT=json.loads((ROOT/'__temp_reports__/source_grounded_18page_closure.json').read_text(encoding='utf-8'))
MARK='ACPOS-20260921-SOURCE-GROUNDED-CONSTRUCTION-CLOSURE-V1'
OLD_MARKERS=[
 '2026-09-21 Construction Exact Binding Closure / 施工精確綁定封板',
 'Unified Page / Control / Action / API / DB / Runtime Construction Matrix',
 'ACPOS-20260921-UNIFIED-CONTROL-RUNTIME-MATRIX-V3',
 'ACPOS-20260921-UNIFIED-CONTROL-RUNTIME-MATRIX-V2',
 'ACPOS-20260921-UNIFIED-CONTROL-RUNTIME-MATRIX]',
]
PAGE_DOCS={
'WB-01':'ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'CORE-01':'ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'ASSET-01':'ACPOS_ASSET-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'VIDEO-01':'ACPOS_VIDEO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'EDIT-01':'ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'QA-01':'ACPOS_QA-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'DB-01':'ACPOS_DB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'STR-01':'ACPOS_STR-01_WORKSPACE_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'INFO-01':'ACPOS_INFO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx',
'SYS-01':'ACPOS_SYS-01_系統維護與生命週期工作區_Mother_Basic_Design_OPTIMIZED.docx',
'IAM-01':'ACPOS_IAM-01_帳戶與權限_Mother_Basic_Design_OPTIMIZED.docx',
'DEV-01':'ACPOS_DEV-01_企業自動開發系統_Mother_Basic_Design_OPTIMIZED.docx',
'SOC-01':'ACPOS_SOC-01_社群發布_Mother_Basic_Design_OPTIMIZED.docx',
'ERP-01':'ACPOS_ERP-01_ERP與財務_Mother_Basic_Design_OPTIMIZED.docx',
'AIAPI-01':'ACPOS_AIAPI-01_AI_API管理_Mother_Basic_Design_OPTIMIZED.docx',
'SG-02':'ACPOS_SG-02_QA審查項目名單_Mother_Basic_Design_OPTIMIZED.docx',
'ADMIN-STR-01':'ACPOS_admin_STR-01_戰略中心後台_Mother_Basic_Design_OPTIMIZED.docx',
'KB-01':'ACPOS_KB-01_知識庫_Mother_Basic_Design_OPTIMIZED.docx',
}
PARENTS={
'01_ACPOS_Global_Intelligent_Brain_Information_Lifecycle_Mother_Basic_Logic_Design_Normative_Contract_v4.docx':['WB-01','INFO-01','KB-01','DB-01'],
'02_ACPOS_AI_Conversation_Memory_MultiAI_Assistant_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':['CORE-01','ASSET-01','VIDEO-01','EDIT-01','QA-01','STR-01','SYS-01','DEV-01','SOC-01','KB-01'],
'03_ACPOS_AI_Execution_Script_Compiler_Tool_AIAPI_Runtime_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':['AIAPI-01'],
'04_ACPOS_CORE_AI_Blueprint_Canonical_Script_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':['CORE-01'],
'05_ACPOS_Creative_Production_AI_ASSET_VIDEO_EDIT_VOICE_QA_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':['ASSET-01','VIDEO-01','EDIT-01','QA-01','SG-02'],
'06_ACPOS_Enterprise_Business_Development_AI_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':['DEV-01','ERP-01'],
'07_ACPOS_Social_Publishing_AI_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':['SOC-01'],
'08_ACPOS_Strategy_Intelligence_MultiAI_Decision_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':['STR-01','ADMIN-STR-01'],
'09_ACPOS_AI_System_Engineer_Self_Inspection_Evolution_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx':['SYS-01','IAM-01','DB-01','KB-01','SG-02','AIAPI-01'],
}
RUNTIME_FACTS=[
('CONVERSATION_RECENT_HISTORY_ROWS','30','src/server/shared/productionConversationAiRuntime.ts · recentHistory LIMIT 30','SOURCE_EXACT'),
('CONVERSATION_RECENT_HISTORY_TEXT_CHARS','2200','same · left(message_content text, 2200)','SOURCE_EXACT'),
('CONVERSATION_DECISION_LEDGER_QUERY_LIMIT','80','same · DECISION_LEDGER LIMIT 80','SOURCE_EXACT'),
('CONVERSATION_EXACT_SOURCE_MESSAGE_TEXT_CHARS','4000','same · referenced source message left(...,4000)','SOURCE_EXACT'),
('CONVERSATION_MEETING_OBJECTIVE_MAX_CHARS','1200','same · persistMeetingStart truncate(message,1200)','SOURCE_EXACT'),
('CONVERSATION_MEETING_PROMPT_MAX_CHARS','4000','same · meeting round prompt truncate(message,4000)','SOURCE_EXACT'),
('IDENTITY_COOKIE_MAX_AGE_SECONDS','43200','authority/runtime/ACPOS_PRODUCTION_IDENTITY_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml','SOURCE_EXACT'),
('PROVIDER_QUEUE_CAPACITY','100','authority/runtime/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml','SOURCE_EXACT'),
('PROVIDER_QUEUE_MAX_ATTEMPTS','3','same queue policy','SOURCE_EXACT'),
('PROVIDER_QUEUE_LEASE_SECONDS','120','same queue policy','SOURCE_EXACT'),
('PROVIDER_QUEUE_BACKOFF_SECONDS','30,120,300','same queue policy','SOURCE_EXACT'),
('PROVIDER_WORKER_MAX_BATCH','10','same worker policy','SOURCE_EXACT'),
('PROVIDER_RECOVERY_CRON','0 0 * * *','same worker recovery cron','SOURCE_EXACT'),
('PROVIDER_PROFILE_TIMEOUT_SECONDS','DYNAMIC_REQUIRED_PROFILE_VALUE','AIAPI Provider Profile exact runtime field; no global fixed timeout','SOURCE_DYNAMIC'),
('PROVIDER_PROFILE_MAX_CONTEXT','DYNAMIC_PROFILE_VALUE','AIAPI Provider Profile exact runtime field; no global fixed max_context','SOURCE_DYNAMIC'),
('CONVERSATION_UI_INITIAL_VISIBLE_MESSAGES','SOURCE_NOT_DEFINED','No exact Current source binding found in audited authority/implementation','DECISION_REQUIRED'),
('CONVERSATION_UI_LAZY_LOAD_PAGE_SIZE','SOURCE_NOT_DEFINED','No exact Current source binding found','DECISION_REQUIRED'),
('CONVERSATION_UI_MAX_RENDERED_MESSAGES','SOURCE_NOT_DEFINED','No exact Current source binding found','DECISION_REQUIRED'),
('CONVERSATION_SUMMARY_TRIGGER','SOURCE_NOT_DEFINED','No deterministic summary threshold in current Production conversation runtime','DECISION_REQUIRED'),
('CONVERSATION_RETENTION_TTL','SOURCE_NOT_DEFINED','No exact retention duration in audited Current source','DECISION_REQUIRED'),
('CONVERSATION_COMPOSER_DRAFT_TTL','SOURCE_NOT_DEFINED','No exact TTL in audited Current source','DECISION_REQUIRED'),
('CONVERSATION_IDEMPOTENCY_TTL','SOURCE_NOT_DEFINED','No exact TTL in audited Current source','DECISION_REQUIRED'),
]

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def text_of(el):
    return ''.join(t.text or '' for t in el.iter() if t.tag==qn('w:t'))
def remove_element(el):
    parent=el.getparent()
    if parent is not None: parent.remove(el)
def strip_old_closure(doc):
    body=doc._element.body
    children=list(body)
    start_idx=None
    for i,ch in enumerate(children):
        txt=text_of(ch)
        if any(m in txt for m in OLD_MARKERS):
            start_idx=i;break
    if start_idx is not None:
        # Remove the immediately preceding empty section-break paragraph created by old annex.
        if start_idx>0:
            prev=children[start_idx-1]
            if prev.tag==qn('w:p') and not text_of(prev).strip() and prev.find('.//'+qn('w:sectPr')) is not None:
                remove_element(prev)
        for ch in list(body)[start_idx:]:
            if ch.tag!=qn('w:sectPr'): remove_element(ch)
    # Remove old top notice paragraphs regardless of location.
    for p in list(doc.paragraphs):
        if 'ACPOS-20260921-EXACT-BINDING-CLOSURE' in p.text:
            remove_element(p._element)
def repeat_header(row):
    trPr=row._tr.get_or_add_trPr()
    x=OxmlElement('w:tblHeader');x.set(qn('w:val'),'true');trPr.append(x)
def shade(cell,fill='EDE9FE'):
    tcPr=cell._tc.get_or_add_tcPr();x=OxmlElement('w:shd');x.set(qn('w:fill'),fill);tcPr.append(x)
def add_table(doc,headers,rows,fs=6.2):
    t=doc.add_table(rows=1,cols=len(headers));t.style='Table Grid';repeat_header(t.rows[0])
    for i,h in enumerate(headers):
        t.rows[0].cells[i].text=str(h);shade(t.rows[0].cells[i])
    for r in rows:
        cells=t.add_row().cells
        for i,v in enumerate(r): cells[i].text=str(v if v not in (None,'') else '—')
    for row in t.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs:run.font.size=Pt(fs)
    return t
def landscape(doc):
    sec=doc.add_section(WD_SECTION.NEW_PAGE)
    sec.orientation=WD_ORIENT.LANDSCAPE
    sec.page_width,sec.page_height=sec.page_height,sec.page_width
    sec.top_margin=Inches(.4);sec.bottom_margin=Inches(.4);sec.left_margin=Inches(.35);sec.right_margin=Inches(.35)
def add_title(doc,title):
    doc.add_heading(title,level=1)
    p=doc.add_paragraph()
    p.add_run(f'[{MARK}] ').bold=True
    p.add_run('Source-grounded only. Existing Current source wins; missing source values remain blocked/decision-required. This closure supersedes the prior generic 2026-09-21 V1/V3 annex only, not the original domain logic or human visual review gates.')
def rows_for(page):
    return REPORT['pages'][page]['bindings']
def binding_table(doc,page,rows):
    v=REPORT['pages'][page]
    doc.add_heading(f'{page} · Exact Construction Binding',level=2)
    add_table(doc,['Authority','Value'],[
      ['Source Commit',REPORT['source_commit']],
      ['Machine Authority',v['authority_path']],
      ['Authority SHA-256',v['authority_sha256']],
      ['Expected Control Denominator',v['expected_control_denominator']],
      ['Unique Control Rows',v['actual_unique_controls']],
      ['Denominator Gate','PASS' if v['denominator_pass'] else 'FAIL'],
    ],7)
    data=[]
    for x in rows:
        data.append([
          x.get('control_uid',''),x.get('control_uid_status','EXISTING_SOURCE_UID'),x.get('label',''),x.get('type',''),
          x.get('action_uid',''),x.get('gate_uid',''),x.get('permission',''),x.get('payload_schema',''),
          x.get('operation',''),x.get('method_path',''),x.get('runtime_owner',''),x.get('persistence_owner',''),
          x.get('classification','')
        ])
    add_table(doc,['Control UID','UID Status','Label','Type','Action UID','Gate','Permission / Auth Resource','Payload / Schema','Operation','Method / Path','Runtime Owner','Persistence Owner','Runtime Status'],data,5.2)
    if v.get('blockers'):
        doc.add_heading(f'{page} · Truthful Remaining Runtime / Governance Status',level=3)
        br=[]
        for b in v['blockers']:
            br.append([b.get('type',''),json.dumps({k:v for k,v in b.items() if k!='type'},ensure_ascii=False)])
        add_table(doc,['Finding','Source-grounded status'],br,6.5)
def add_special_notes(doc,page):
    if page=='CORE-01':
        doc.add_heading('CORE LockReview Exact Contract Clarification',level=3)
        doc.add_paragraph('Earlier text that says the LockReview contract is unresolved is superseded for construction binding by migration 0042 and productionCoreGovernedRuntime. A MOTHER/CHILD request accepts scope + expected_version + correlation_id + idempotency_key + target_ref + request_reason + requested_scope_refs. requested_scope_refs MUST resolve exactly one APPROVED quality_criteria_version and at least one evidence ref. reviewer_path is derived by the database from APPROVED ALLOW account permission assignments for resource api:decideLockReview / EXECUTE, scope-compatible and excluding the requester. reviewer_count < 1 remains a runtime fail-closed condition; the AI MUST NOT invent a reviewer. expected_target_hash is persisted by the governed lock service.')
        add_table(doc,['Item','Exact Source Rule'],[
          ['Criteria','Exactly one APPROVED quality_criteria_version resolved from requested_scope_refs'],
          ['Evidence','At least 1 resolvable evidence ref; otherwise LOCK_EVIDENCE_REQUIRED'],
          ['Reviewer Path','Derived from account_permission_assignments for api:decideLockReview / EXECUTE / ALLOW / APPROVED'],
          ['Separation of Duties','Requester excluded; requester cannot decide own lock'],
          ['Reviewer Missing','CORE_LOCK_REVIEWER_PATH_UNRESOLVED'],
          ['Request Endpoints','POST /v1/locks/mother-requests ; POST /v1/locks/child-requests ; DNA request uses registered state-command route'],
        ],6.5)
    elif page=='EDIT-01':
        doc.add_heading('EDIT Registry Denominator Precedence',level=3)
        doc.add_paragraph('Construction denominator is the actual Current registry: 160 Controls / 124 Actions / 22 Integration Ports / 20 unique port operations. The older derived_validation 15 ports / 13 operations is stale diagnostic material and MUST NOT be used as the Current denominator. This closure does not invent a replacement registry; it binds the existing controls_fields + action_to_permission_gate_effect + integration_ports.')
    elif page=='ERP-01':
        doc.add_heading('ERP Denominator Clarification',level=3)
        doc.add_paragraph('42 is the complete current page-control denominator. The separate “17 + 12 = 29 source controls” acceptance statement is a source-control coverage slice, not the full page denominator. It MUST NOT replace the 42-control registry.')
    elif page=='SG-02':
        doc.add_heading('SG-02 Runtime Truth',level=3)
        doc.add_paragraph('The 11-control design binding is exact. Machine authority still records runtime_binding_validation = NOT_EXECUTED / effectful_runtime_ready = false. Construction may implement only the exact registered operations; it MUST NOT claim runtime acceptance until execution evidence exists.')
    elif page=='KB-01':
        doc.add_heading('KB-01 Runtime Truth',level=3)
        doc.add_paragraph('The 27 controls and 21 action contracts are exact, including method/path. Machine authority still records application/api/db/crawler_execution/e2e/deploy = NOT_EXECUTED. Therefore the specification is construction-complete while Production implementation acceptance remains open.')
    elif page=='ADMIN-STR-01':
        doc.add_heading('Strategy Admin Runtime Materialization Boundary',level=3)
        doc.add_paragraph('All 19 source-preserving interaction controls are exact. Current implementation materializes searchProjection, refreshProjection, configureGovernedResource and approveGovernedResource. saveDraft, exportProjection, createCandidate, compareCandidates, rejectStrategyCandidate and adoptAsContextCandidate remain spec-bound but runtime-blocked; exportProjection additionally has BLOCKED_NO_CANONICAL_EXPORT_PERSISTENCE_OWNER in the operation registry. Do not enable those controls until their exact runtime owner/persistence/authorization path is materialized and tested.')
    elif page=='AIAPI-01':
        doc.add_heading('AIAPI Control UID Provenance',level=3)
        doc.add_paragraph('Where the operation registry already supplies a control:* authorization resource, that exact control resource is reused. For current single-page UI operations that exist in the page UI + operation registry but expose only an action/page authorization resource, this closure creates a deterministic AIAPI-01-BTN-<OPERATION> construction UID and marks UID Status as NEW_CONSTRUCTION_UID_FROM_EXISTING_CURRENT_UI_OPERATION. The operation, path, authorization owner, payload fields and runtime are not changed.')
def add_runtime_truth(doc,scope):
    doc.add_heading('Source-backed Runtime Quantitative Truth',level=2)
    if scope=='02':
        chosen=[r for r in RUNTIME_FACTS if r[0].startswith('CONVERSATION_') or r[0].startswith('IDENTITY_') or r[0].startswith('PROVIDER_PROFILE_')]
    elif scope=='03':
        chosen=[r for r in RUNTIME_FACTS if r[0].startswith('PROVIDER_')]
    elif scope in ('01','09'):
        chosen=RUNTIME_FACTS
    else:
        chosen=[r for r in RUNTIME_FACTS if r[3]=='SOURCE_EXACT' and (r[0].startswith('PROVIDER_QUEUE_') or r[0].startswith('PROVIDER_WORKER_'))]
    add_table(doc,['Runtime Policy','Exact Value / Binding','Source','Status'],chosen,6.3)
    doc.add_paragraph('Rule: SOURCE_NOT_DEFINED is not a default value. It is an explicit unresolved design parameter. Construction MUST preserve fail-closed behavior or request a formal policy decision; it MUST NOT restore the removed 50/50/200, 24, 96k, 365-day or other generic values without a new authority decision.')
def conv_relevant(x):
    blob=' '.join(str(x.get(k,'')) for k in ['control_uid','label','action_uid','effect','operation','runtime_binding','runtime_owner']).lower()
    keys=['conversation','message','thread','send','stop','single-ai','multi-ai','single ai','multi ai','council','attach','assistant','meeting']
    return any(k in blob for k in keys)
def add_parent(doc,name,pages):
    strip_old_closure(doc)
    landscape(doc);add_title(doc,'2026-09-21 Source-Grounded Construction Closure / 來源實證施工封板')
    scope=name[:2]
    add_runtime_truth(doc,scope)
    doc.add_heading('Page / Control Exact Binding',level=2)
    for page in pages:
        rr=rows_for(page)
        if scope=='02':
            rr=[x for x in rr if conv_relevant(x)]
            if not rr:
                continue
        binding_table(doc,page,rr)
        add_special_notes(doc,page)
    doc.add_heading('Construction Resolution Rule',level=2)
    doc.add_paragraph('施工 AI MUST resolve UI behavior from this order: page machine authority → exact control row → action/gate/permission → payload/schema → operation/method/path → runtime/persistence owner → source runtime status. If a row is SPEC_EXACT_RUNTIME_BLOCKED or SPEC_EXACT_RUNTIME_NOT_EXECUTED, the UI definition is known but effectful enablement is forbidden until implementation evidence closes. If a quantitative value is SOURCE_NOT_DEFINED, do not choose a “reasonable” number.')
def add_page_doc(doc,page):
    # Remove any duplicate new marker only if rerun.
    if any(MARK in p.text for p in doc.paragraphs): return False
    landscape(doc);add_title(doc,'2026-09-21 Machine Authority Construction Closure / 機器權威施工綁定封板')
    binding_table(doc,page,rows_for(page))
    add_special_notes(doc,page)
    doc.add_heading('Page Construction Invariant',level=2)
    doc.add_paragraph('The exact control denominator above is the only construction denominator for this page. Components/fields/visual IDs are not counted as additional controls. Existing source UIDs are preserved. A control classified UI_LOCAL_EXACT MUST NOT create a server write. A control classified SPEC_EXACT_RUNTIME_BLOCKED / NOT_EXECUTED MUST remain disabled or fail-closed until its runtime evidence exists.')

# Page docs.
updated=[]
for page,file in PAGE_DOCS.items():
    p=ROOT/file
    d=Document(p)
    if add_page_doc(d,page):
        d.save(p);Document(p);updated.append(file)

# Parent 01-09.
for file,pages in PARENTS.items():
    p=ROOT/file;d=Document(p);add_parent(d,file,pages);d.save(p);Document(p);updated.append(file)

# Index summary.
idx=ROOT/'00_INDEX_ACPOS_Mother_Compliant_Basic_Design_Master.docx'
d=Document(idx)
if not any(MARK in p.text for p in d.paragraphs):
    landscape(d);add_title(d,'2026-09-21 Source-Grounded Construction Closure Index')
    add_table(d,['Page','Expected Controls','Exact Rows','Denominator','True Runtime / Governance Status'],[
      [page,v['expected_control_denominator'],v['actual_unique_controls'],'PASS' if v['denominator_pass'] else 'FAIL',
       '; '.join(b.get('type','') for b in v.get('blockers',[])) or 'NO_DEFINITION_GAP']
      for page,v in REPORT['pages'].items()
    ],6.5)
    d.add_paragraph('This index records construction definition status only. Human Visual Review / Design Freeze and Production runtime acceptance remain independent gates.')
    d.save(idx);Document(idx);updated.append(idx.name)

out={'marker':MARK,'source_commit':REPORT['source_commit'],'updated_files':updated,'updated_count':len(updated),
     'page_denominators':{p:{'expected':v['expected_control_denominator'],'actual':v['actual_unique_controls'],'pass':v['denominator_pass']} for p,v in REPORT['pages'].items()},
     'true_blockers':REPORT['true_blockers']}
(ROOT/'__temp_reports__/word_patch_report.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
