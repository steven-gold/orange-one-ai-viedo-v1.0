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

def norm(x): return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None
def get(vals,i): return "" if i is None or i>=len(vals) else norm(vals[i])
def is_missing(v): return v in {"","—","-","SOURCE_NOT_DEFINED"}

DISPLAY_ONLY_TYPES={"READONLY","LABEL","TEXT","BADGE","STATUS","METRIC","KPI","DIVIDER","ICON","PANEL","CARD","VIEW","LIST","TABLE","CHIP","TAG","DISPLAY"}
def display_only(r):
    typ=r.get("type","").upper()
    return typ in DISPLAY_ONLY_TYPES or any(x in typ for x in ["READONLY","LABEL","DISPLAY","METRIC","KPI","STATUS"])

FIELDS=["control","type","label","action","gate","permission","operation","runtime_owner","runtime_status"]
def parse_rows(path,require_control=False):
    d=Document(path);out=[]
    for ti,t in enumerate(d.tables):
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells]
        idx={
          "control":hfind(h,"control uid"),
          "type":hfind(h,"type"),
          "label":hfind(h,"label","顯示名稱"),
          "action":hfind(h,"action uid"),
          "gate":hfind(h,"gate uid","gate"),
          "permission":hfind(h,"permission","auth resource"),
          "operation":hfind(h,"operation"),
          "runtime_owner":hfind(h,"runtime owner"),
          "runtime_status":hfind(h,"runtime status")
        }
        if require_control and idx["control"] is None:continue
        if not require_control and all(idx[k] is None for k in ["control","action","gate","permission","operation","runtime_owner"]):continue
        for ri,r in enumerate(t.rows[1:],2):
            vals=[c.text for c in r.cells]
            rec={k:get(vals,idx[k]) for k in FIELDS}
            if require_control:
                uid=rec["control"]
                if not uid or uid in {"—","-"} or not re.search(r"[A-Za-z0-9]",uid):continue
            else:
                if not any(not is_missing(rec[k]) for k in ["control","action","gate","permission","operation","runtime_owner"]):continue
            rec.update({"source":str(path),"table":ti+1,"row":ri})
            out.append(rec)
    return out

def classify(field,row):
    val=row.get(field,"");status=row.get("runtime_status","")
    if not is_missing(val):return "BOUND"
    if "UI_LOCAL_EXACT" in status:
        if field in {"operation","runtime_owner"}:return "LEGITIMATE_NA_UI_LOCAL"
        if field=="action" and display_only(row):return "LEGITIMATE_NA_UI_LOCAL"
    if "OWNER_ORCHESTRATED_RUNTIME_EXACT_NO_PUBLIC_ROUTE" in status and field=="operation":return "CLOSED_BY_OWNER_LOCAL_COMMAND"
    if "READ_EXACT" in status and display_only(row):
        if field=="action":return "LEGITIMATE_NA_READ_PRESENTATION"
        if field=="operation" and not is_missing(row.get("runtime_owner","")):return "READ_OWNER_BOUND_OPERATION_UNSPECIFIED"
    if field=="runtime_owner" and any(x in status for x in ["SPEC_EXACT_RUNTIME_BLOCKED","SPEC_EXACT_RUNTIME_NOT_EXECUTED","RUNTIME_IMPLEMENTATION_BLOCKED"]):return "KNOWN_RUNTIME_BLOCKER"
    if val=="SOURCE_NOT_DEFINED":return "SOURCE_RESOLUTION_REQUIRED"
    return "DEFINITION_BINDING_GAP"

def best(rows):
    b={}
    for r in rows:
        uid=r["control"];score=sum(1 for k in FIELDS[1:] if not is_missing(r.get(k,"")))
        if uid not in b or score>b[uid][0]:b[uid]=(score,r)
    return {k:v[1] for k,v in b.items()}

# All canonical source records (01-09).
src=[]
for f in SYSTEMS:
    assert Path(f).exists(),f
    src += parse_rows(f,False)

# Index exact keys. Do not infer backward from permission or labels.
idx=collections.defaultdict(lambda:collections.defaultdict(list))
for r in src:
    for key in ["control","action","gate","operation"]:
        v=r.get(key,"")
        if not is_missing(v): idx[key][v].append(r)

ALLOWED={
 "action":{"gate":["action"],"permission":["action","gate"],"operation":["action"],"runtime_owner":["action","operation"]},
 "gate":{},
 "permission":{},
 "operation":{},
 "runtime_owner":{}
}

def candidate_records(target,field,page_rows):
    candidates=[]
    # Same-page exact records are also valid source rows.
    pool=src+page_rows
    keys=[]
    if not is_missing(target.get("control","")): keys.append(("control",target["control"]))
    if field in {"gate","permission","operation","runtime_owner"} and not is_missing(target.get("action","")):keys.append(("action",target["action"]))
    if field=="permission" and not is_missing(target.get("gate","")):keys.append(("gate",target["gate"]))
    if field=="runtime_owner" and not is_missing(target.get("operation","")):keys.append(("operation",target["operation"]))
    seen=set()
    for key,val in keys:
        for r in pool:
            if r.get(key,"")!=val:continue
            fv=r.get(field,"")
            if is_missing(fv):continue
            sig=(fv,r["source"],r["table"],r["row"],key,val)
            if sig not in seen:
                seen.add(sig);candidates.append({"value":fv,"source":r["source"],"table":r["table"],"row":r["row"],"matched_by":key,"matched_value":val})
    return candidates

report={"total_definition_gaps":0,"resolvable":0,"unresolved":0,"conflict":0,"by_field":{},"pages":{},"resolvable_rows":[],"unresolved_rows":[],"conflict_rows":[]}
for page,fn in PAGES.items():
    rows=parse_rows(fn,True);bm=best(rows)
    pc={"definition_gaps":0,"resolvable":0,"unresolved":0,"conflict":0}
    for uid,t in sorted(bm.items()):
        for field in ["action","gate","permission","operation","runtime_owner"]:
            if classify(field,t)!="DEFINITION_BINDING_GAP":continue
            report["total_definition_gaps"]+=1;pc["definition_gaps"]+=1
            bf=report["by_field"].setdefault(field,{"definition_gaps":0,"resolvable":0,"unresolved":0,"conflict":0});bf["definition_gaps"]+=1
            cs=candidate_records(t,field,rows)
            vals=collections.defaultdict(list)
            for c in cs:vals[c["value"]].append(c)
            base={"page":page,"file":fn,"uid":uid,"field":field,"type":t.get("type",""),"label":t.get("label",""),"action":t.get("action",""),"gate":t.get("gate",""),"permission":t.get("permission",""),"operation":t.get("operation",""),"runtime_owner":t.get("runtime_owner",""),"runtime_status":t.get("runtime_status","")}
            if len(vals)==1:
                value=next(iter(vals)); rec=base|{"value":value,"sources":vals[value]}
                report["resolvable"]+=1;pc["resolvable"]+=1;bf["resolvable"]+=1;report["resolvable_rows"].append(rec)
            elif len(vals)==0:
                report["unresolved"]+=1;pc["unresolved"]+=1;bf["unresolved"]+=1;report["unresolved_rows"].append(base)
            else:
                rec=base|{"candidate_values":dict(vals)}
                report["conflict"]+=1;pc["conflict"]+=1;bf["conflict"]+=1;report["conflict_rows"].append(rec)
    report["pages"][page]=pc

assert report["total_definition_gaps"]==346,report["total_definition_gaps"]
Path("__batch05_authority_graph_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH05_AUTHORITY_GRAPH="+json.dumps({
 "total_definition_gaps":report["total_definition_gaps"],"resolvable":report["resolvable"],"unresolved":report["unresolved"],"conflict":report["conflict"],"by_field":report["by_field"],"pages":report["pages"]
},ensure_ascii=False,sort_keys=True))
print("GRAPH_RESOLVABLE_BEGIN")
for r in report["resolvable_rows"]:print(json.dumps(r,ensure_ascii=False,sort_keys=True))
print("GRAPH_RESOLVABLE_END")
print("GRAPH_CONFLICT_BEGIN")
for r in report["conflict_rows"]:print(json.dumps(r,ensure_ascii=False,sort_keys=True))
print("GRAPH_CONFLICT_END")
