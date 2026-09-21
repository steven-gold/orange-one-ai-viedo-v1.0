from pathlib import Path
from docx import Document
import json,re,collections

SYSTEMS=[
"01_ACPOS_Global_Intelligent_Brain_Information_Lifecycle_Mother_Basic_Logic_Design_Normative_Contract_v4.docx",
"02_ACPOS_AI_Conversation_Memory_MultiAI_Assistant_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx",
"03_ACPOS_AI_Execution_Script_Compiler_Tool_AIAPI_Runtime_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx",
"04_ACPOS_CORE_AI_Blueprint_Canonical_Script_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx",
"05_ACPOS_Creative_Production_AI_ASSET_VIDEO_EDIT_VOICE_QA_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx",
"06_ACPOS_Enterprise_Business_Development_AI_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx",
"07_ACPOS_Social_Publishing_AI_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx",
"08_ACPOS_Strategy_Intelligence_MultiAI_Decision_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx",
"09_ACPOS_AI_System_Engineer_Self_Inspection_Evolution_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx",
]
PAGES={
"AIAPI-01":"ACPOS_AIAPI-01_AI_API管理_Mother_Basic_Design_OPTIMIZED.docx",
"ASSET-01":"ACPOS_ASSET-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"CORE-01":"ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"DB-01":"ACPOS_DB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"DEV-01":"ACPOS_DEV-01_企業自動開發系統_Mother_Basic_Design_OPTIMIZED.docx",
"EDIT-01":"ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"ERP-01":"ACPOS_ERP-01_ERP與財務_Mother_Basic_Design_OPTIMIZED.docx",
"IAM-01":"ACPOS_IAM-01_帳戶與權限_Mother_Basic_Design_OPTIMIZED.docx",
"INFO-01":"ACPOS_INFO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"KB-01":"ACPOS_KB-01_知識庫_Mother_Basic_Design_OPTIMIZED.docx",
"QA-01":"ACPOS_QA-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"SG-02":"ACPOS_SG-02_QA審查項目名單_Mother_Basic_Design_OPTIMIZED.docx",
"SOC-01":"ACPOS_SOC-01_社群發布_Mother_Basic_Design_OPTIMIZED.docx",
"STR-01":"ACPOS_STR-01_WORKSPACE_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"SYS-01":"ACPOS_SYS-01_系統維護與生命週期工作區_Mother_Basic_Design_OPTIMIZED.docx",
"VIDEO-01":"ACPOS_VIDEO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"WB-01":"ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"ADMIN-STR-01":"ACPOS_admin_STR-01_戰略中心後台_Mother_Basic_Design_OPTIMIZED.docx",
}

def norm(x):
    return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())

def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None

def get(vals,i):
    if i is None or i>=len(vals):return ""
    return norm(vals[i])

def is_missing(v):
    return v in {"","—","-","SOURCE_NOT_DEFINED"}

def rows_from(path):
    doc=Document(path)
    out=[]
    for ti,t in enumerate(doc.tables):
        if not t.rows:continue
        headers=[norm(c.text) for c in t.rows[0].cells]
        ci=hfind(headers,"control uid")
        if ci is None:continue
        idx={
          "uid":ci,"type":hfind(headers,"type"),"label":hfind(headers,"label","顯示名稱"),
          "action":hfind(headers,"action uid"),"gate":hfind(headers,"gate"),
          "permission":hfind(headers,"permission","auth resource"),
          "operation":hfind(headers,"operation"),"runtime_owner":hfind(headers,"runtime owner"),
          "runtime_status":hfind(headers,"runtime status")
        }
        for ri,r in enumerate(t.rows[1:],2):
            vals=[c.text for c in r.cells]
            uid=get(vals,ci)
            if not uid or uid in {"—","-"} or not re.search(r"[A-Za-z0-9]",uid):continue
            rec={k:get(vals,v) for k,v in idx.items()}
            rec.update({"source":str(path),"table":ti+1,"row":ri,"headers":headers})
            out.append(rec)
    return out

DISPLAY_KEYS=("READONLY","LABEL","DISPLAY","METRIC","KPI","STATUS")
def display_only(r):
    typ=r.get("type","").upper()
    return any(k in typ for k in DISPLAY_KEYS)

def classify(field,row):
    val=row.get(field,"");status=row.get("runtime_status","")
    if not is_missing(val):return "BOUND"
    if "UI_LOCAL_EXACT" in status:
        if field in {"operation","runtime_owner"}:return "LEGITIMATE_NA_UI_LOCAL"
        if field=="action" and display_only(row):return "LEGITIMATE_NA_UI_LOCAL"
    if "OWNER_ORCHESTRATED_RUNTIME_EXACT_NO_PUBLIC_ROUTE" in status and field=="operation":
        return "CLOSED_BY_OWNER_LOCAL_COMMAND"
    if "READ_EXACT" in status and display_only(row):
        if field=="action":return "LEGITIMATE_NA_READ_PRESENTATION"
        if field=="operation" and not is_missing(row.get("runtime_owner","")):
            return "READ_OWNER_BOUND_OPERATION_UNSPECIFIED"
    if field=="runtime_owner" and any(x in status for x in ["SPEC_EXACT_RUNTIME_BLOCKED","SPEC_EXACT_RUNTIME_NOT_EXECUTED","RUNTIME_IMPLEMENTATION_BLOCKED"]):
        return "KNOWN_RUNTIME_BLOCKER"
    if val=="SOURCE_NOT_DEFINED":return "SOURCE_RESOLUTION_REQUIRED"
    return "DEFINITION_BINDING_GAP"

def best_rows(rows):
    best={}
    for r in rows:
        score=sum(1 for k in ["type","label","action","gate","permission","operation","runtime_owner","runtime_status"] if not is_missing(r.get(k,"")))
        old=best.get(r["uid"])
        if old is None or score>old[0]:
            best[r["uid"]]=(score,r)
    return {k:v[1] for k,v in best.items()}

# Build exact UID authority index from 01-09.
sys_index=collections.defaultdict(lambda:collections.defaultdict(list))
for f in SYSTEMS:
    assert Path(f).exists(),f
    for r in rows_from(f):
        for field in ["action","gate","permission","operation","runtime_owner"]:
            v=r.get(field,"")
            if not is_missing(v):
                sys_index[r["uid"]][field].append((v,f,r["table"],r["row"]))

report={"total_definition_gaps":0,"resolvable":0,"unresolved":0,"conflict":0,"pages":{},"resolvable_rows":[],"unresolved_rows":[],"conflict_rows":[]}
for page,fn in PAGES.items():
    rows=rows_from(fn)
    best=best_rows(rows)
    by_uid=collections.defaultdict(list)
    for r in rows:by_uid[r["uid"]].append(r)
    pc={"definition_gaps":0,"resolvable":0,"unresolved":0,"conflict":0}
    for uid,row in sorted(best.items()):
        for field in ["action","gate","permission","operation","runtime_owner"]:
            if classify(field,row)!="DEFINITION_BINDING_GAP":continue
            report["total_definition_gaps"]+=1;pc["definition_gaps"]+=1
            candidates=[]
            # Exact same UID, other rows in same page.
            for rr in by_uid[uid]:
                v=rr.get(field,"")
                if not is_missing(v):
                    candidates.append((v,fn,rr["table"],rr["row"],"SAME_PAGE_EXACT_UID"))
            # Exact same UID in canonical system normative docs.
            for v,sf,ti,ri in sys_index.get(uid,{}).get(field,[]):
                candidates.append((v,sf,ti,ri,"SYSTEM_NORMATIVE_EXACT_UID"))
            vals=collections.defaultdict(list)
            for c in candidates:vals[c[0]].append(c[1:])
            base={"page":page,"file":fn,"uid":uid,"field":field,"type":row.get("type",""),"label":row.get("label",""),"runtime_status":row.get("runtime_status","")}
            if len(vals)==1:
                value=next(iter(vals))
                rec=base|{"value":value,"sources":vals[value]}
                report["resolvable"]+=1;pc["resolvable"]+=1;report["resolvable_rows"].append(rec)
            elif len(vals)==0:
                report["unresolved"]+=1;pc["unresolved"]+=1;report["unresolved_rows"].append(base)
            else:
                rec=base|{"candidate_values":{k:v for k,v in vals.items()}}
                report["conflict"]+=1;pc["conflict"]+=1;report["conflict_rows"].append(rec)
    report["pages"][page]=pc

assert report["total_definition_gaps"]==346,report["total_definition_gaps"]
Path("__batch05_authority_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH05_AUTHORITY_AUDIT="+json.dumps({
 "total_definition_gaps":report["total_definition_gaps"],
 "resolvable":report["resolvable"],
 "unresolved":report["unresolved"],
 "conflict":report["conflict"],
 "pages":report["pages"],
},ensure_ascii=False,sort_keys=True))
print("RESOLVABLE_ROWS_BEGIN")
for r in report["resolvable_rows"]:
    print(json.dumps(r,ensure_ascii=False,sort_keys=True))
print("RESOLVABLE_ROWS_END")
print("CONFLICT_ROWS_BEGIN")
for r in report["conflict_rows"]:
    print(json.dumps(r,ensure_ascii=False,sort_keys=True))
print("CONFLICT_ROWS_END")
