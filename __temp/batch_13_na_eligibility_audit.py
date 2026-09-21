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
FIELDS=["control","type","label","action","gate","permission","operation","runtime_owner","runtime_status"]

def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v):return v in {"","—","-","SOURCE_NOT_DEFINED"}
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None
def display_only_type(t):
    u=(t or "").upper()
    return u in {"READONLY","LABEL","TEXT","BADGE","STATUS","METRIC","KPI","DIVIDER","ICON","PANEL","CARD","VIEW","LIST","TABLE","CHIP","TAG","DISPLAY"} or any(x in u for x in ["READONLY","LABEL","DISPLAY","METRIC","KPI","STATUS"])

def parse_controls(path):
    d=Document(path);out=[]
    for ti,t in enumerate(d.tables):
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells]
        ci=hfind(h,"control uid")
        if ci is None:continue
        idx={"control":ci,"type":hfind(h,"type"),"label":hfind(h,"label","顯示名稱"),"action":hfind(h,"action uid"),"gate":hfind(h,"gate uid","gate"),"permission":hfind(h,"permission","auth resource"),"operation":hfind(h,"operation"),"runtime_owner":hfind(h,"runtime owner"),"runtime_status":hfind(h,"runtime status")}
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells]
            uid=vals[ci] if ci<len(vals) else ""
            if not uid or uid in {"—","-"}:continue
            rec={k:(vals[i] if i is not None and i<len(vals) else "") for k,i in idx.items()}
            rec.update({"source":path,"table":ti+1,"row":ri,"headers":h})
            out.append(rec)
    return out

def compose(rows):
    g=collections.defaultdict(list)
    for r in rows:g[r["control"]].append(r)
    out={}
    for uid,rs in g.items():
        base=max(rs,key=lambda r:sum(not missing(r.get(f,"")) for f in FIELDS[1:])).copy()
        for f in FIELDS[1:]:
            vals=sorted(set(r.get(f,"") for r in rs if not missing(r.get(f,""))))
            if missing(base.get(f,"")) and len(vals)==1:base[f]=vals[0]
        base["same_uid_rows"]=rs;out[uid]=base
    return out

def classify(field,r):
    v=r.get(field,"");st=r.get("runtime_status","")
    if not missing(v):return "BOUND"
    if "UI_LOCAL_EXACT" in st:
        if field in {"operation","runtime_owner"}:return "LEGITIMATE_NA_UI_LOCAL"
        if field=="action" and display_only_type(r.get("type","")):return "LEGITIMATE_NA_UI_LOCAL"
    if "OWNER_ORCHESTRATED_RUNTIME_EXACT_NO_PUBLIC_ROUTE" in st and field=="operation":return "CLOSED_BY_OWNER_LOCAL_COMMAND"
    if "READ_EXACT" in st and display_only_type(r.get("type","")):
        if field=="action":return "LEGITIMATE_NA_READ_PRESENTATION"
        if field=="operation" and not missing(r.get("runtime_owner","")):return "READ_OWNER_BOUND_OPERATION_UNSPECIFIED"
    if field=="runtime_owner" and any(x in st for x in ["SPEC_EXACT_RUNTIME_BLOCKED","SPEC_EXACT_RUNTIME_NOT_EXECUTED","RUNTIME_IMPLEMENTATION_BLOCKED"]):return "KNOWN_RUNTIME_BLOCKER"
    if v=="SOURCE_NOT_DEFINED":return "SOURCE_RESOLUTION_REQUIRED"
    return "DEFINITION_BINDING_GAP"

# current 239 gaps
gaps=[]
all_rows=[]
for page,fn in PAGES.items():
    bm=compose(parse_controls(fn))
    for uid,r in bm.items():
        for field in ["action","gate","permission","operation","runtime_owner"]:
            cls=classify(field,r)
            all_rows.append((page,uid,field,cls,r))
            if cls=="DEFINITION_BINDING_GAP":
                gaps.append({"page":page,"file":fn,"uid":uid,"field":field,**{k:r.get(k,"") for k in FIELDS[1:]}})
assert len(gaps)==239,len(gaps)
ordinary=[g for g in gaps if not (g["page"]=="SYS-01" and g["uid"]=="SYS-01-BTN-NAV-OPEN" and g["field"]=="gate")]
assert len(ordinary)==238

# signature grouping
sig_counts=collections.Counter()
page_field=collections.Counter()
status_field=collections.Counter()
type_field=collections.Counter()
for g in ordinary:
    sig=(g["field"],g["type"],g["runtime_status"],g["gate"],g["permission"])
    sig_counts[sig]+=1
    page_field[(g["page"],g["field"])]+=1
    status_field[(g["runtime_status"],g["field"])]+=1
    type_field[(g["type"],g["field"])]+=1

# Strong N/A evidence: within same PAGE, another control with same exact type + runtime_status + gate + permission
# has same target field missing and is already classified by existing rules as a legitimate N/A / owner-local closure.
closed_examples=[]
by_page_controls={p:compose(parse_controls(fn)) for p,fn in PAGES.items()}
for g in ordinary:
    peers=[]
    for uid,r in by_page_controls[g["page"]].items():
        if uid==g["uid"]:continue
        if r.get("type","")!=g["type"]:continue
        if r.get("runtime_status","")!=g["runtime_status"]:continue
        if r.get("gate","")!=g["gate"]:continue
        if r.get("permission","")!=g["permission"]:continue
        cls=classify(g["field"],r)
        if cls in {"LEGITIMATE_NA_UI_LOCAL","LEGITIMATE_NA_READ_PRESENTATION","READ_OWNER_BOUND_OPERATION_UNSPECIFIED","CLOSED_BY_OWNER_LOCAL_COMMAND"}:
            peers.append({"uid":uid,"class":cls,"operation":r.get("operation",""),"runtime_owner":r.get("runtime_owner",""),"action":r.get("action","")})
    if peers:
        closed_examples.append({**g,"peer_evidence":peers})

# Explicit semantic definitions from all 31 docs: rows/paragraphs mentioning runtime statuses and N/A/not required/local/presentation/read semantics.
semantic_terms=[
 "UI_LOCAL_EXACT","READ_EXACT","OWNER_ORCHESTRATED_RUNTIME_EXACT_NO_PUBLIC_ROUTE",
 "LEGITIMATE_NA_UI_LOCAL","LEGITIMATE_NA_READ_PRESENTATION","READ_OWNER_BOUND_OPERATION_UNSPECIFIED",
 "not required","not applicable","n/a","presentation","read-only","readonly","local interaction","no public route"
]
contexts=[]
for fn in list(SYSTEMS)+list(PAGES.values())+["ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx"]:
    d=Document(fn)
    for i,p in enumerate(d.paragraphs,1):
        t=norm(p.text)
        if t and any(term.lower() in t.lower() for term in semantic_terms):
            contexts.append({"file":fn,"kind":"paragraph","index":i,"text":t})
    for ti,tb in enumerate(d.tables,1):
        for ri,row in enumerate(tb.rows,1):
            text=" | ".join(norm(c.text) for c in row.cells)
            if text and any(term.lower() in text.lower() for term in semantic_terms):
                contexts.append({"file":fn,"kind":"table","table":ti,"row":ri,"text":text})

payload={
 "denominator":238,
 "page_field":{" | ".join(k):v for k,v in page_field.items()},
 "status_field":{" | ".join(k):v for k,v in status_field.items()},
 "type_field":{" | ".join(k):v for k,v in type_field.items()},
 "top_signatures":[{"signature":list(k),"count":v} for k,v in sig_counts.most_common(80)],
 "same_page_closed_peer_candidates":closed_examples,
 "semantic_contexts":contexts,
 "rows":ordinary,
}
Path("__batch13_na_eligibility_audit.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH13_AUDIT="+json.dumps({
 "denominator":238,
 "same_page_closed_peer_candidates":len(closed_examples),
 "page_field":{" | ".join(k):v for k,v in page_field.items()},
 "status_field":{" | ".join(k):v for k,v in status_field.items()},
 "type_field":{" | ".join(k):v for k,v in type_field.items()},
},ensure_ascii=False,sort_keys=True))
print("BATCH13_PEERS_BEGIN")
for x in closed_examples:
    print(json.dumps(x,ensure_ascii=False,sort_keys=True))
print("BATCH13_PEERS_END")
print("BATCH13_CONTEXT_BEGIN")
for x in contexts[:300]:
    print(json.dumps(x,ensure_ascii=False,sort_keys=True))
print("BATCH13_CONTEXT_END")
