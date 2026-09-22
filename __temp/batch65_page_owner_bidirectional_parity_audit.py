from pathlib import Path
from docx import Document
import json,re,collections,subprocess

BASE_HEAD="b9449ee5c35db102195385927402e8e05b074e70"
SYSTEM_DOCS=[
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
PAGE_DOCS={
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
S01,S02,S03,S04,S05,S06,S07,S08,S09=SYSTEM_DOCS
PAIR_PRECEDENCE={
 tuple(sorted((S03,S09))):S03,
 tuple(sorted((S02,S04))):S02,
 tuple(sorted((S02,S06))):S06,
 tuple(sorted((S02,S08))):S02,
 tuple(sorted((S02,S09))):S02,
}
FIELDS=["action","gate","permission","payload","operation","method","runtime_owner","persistence","runtime_status"]
def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v):return v in {"","—","-","SOURCE_NOT_DEFINED","UNCHANGED"}
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None
def parse(path):
    d=Document(path);out=[]
    for ti,t in enumerate(d.tables,1):
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells];ci=hfind(h,"control uid","target uid")
        if ci is None:continue
        ix={"uid":ci,"action":hfind(h,"action uid"),"gate":hfind(h,"gate uid","gate"),
          "permission":hfind(h,"permission","auth resource"),"payload":hfind(h,"payload / schema","payload","schema"),
          "operation":hfind(h,"operation"),"method":hfind(h,"method / path","method","path"),
          "runtime_owner":hfind(h,"runtime owner"),"persistence":hfind(h,"persistence owner"),
          "runtime_status":hfind(h,"runtime status")}
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells]
            uid=vals[ci] if ci<len(vals) else ""
            if not uid or uid in {"—","-"}:continue
            rec={k:(vals[i] if i is not None and i<len(vals) else "") for k,i in ix.items()}
            rec.update({"file":path,"table":ti,"row":ri});out.append(rec)
    return out
def compose(rows):
    # Prefer exact runtime rows, then most complete row; fill only unique non-missing values.
    exact=[r for r in rows if r.get("runtime_status") in {"EFFECTFUL_EXACT","READ_EXACT"}]
    pool=exact if exact else rows
    base=max(pool,key=lambda r:sum(not missing(r.get(f,"")) for f in FIELDS)).copy()
    values={}
    for f in FIELDS:
        vals=sorted(set(r.get(f,"") for r in pool if not missing(r.get(f,""))))
        values[f]=vals
        if missing(base.get(f,"")) and len(vals)==1:base[f]=vals[0]
    base["_values"]=values
    return base
assert len(list(Path(".").glob("*.docx")))==31
assert subprocess.check_output(["git","-c","core.quotePath=false","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

sys_rows={f:parse(f) for f in SYSTEM_DOCS}
sys_by_uid={f:collections.defaultdict(list) for f in SYSTEM_DOCS}
for f,rows in sys_rows.items():
    for r in rows:sys_by_uid[f][r["uid"]].append(r)

page_rows={}
for page,fn in PAGE_DOCS.items():
    rows=parse(fn)
    page_rows[page]=[r for r in rows if r.get("runtime_status") in {"EFFECTFUL_EXACT","READ_EXACT"}]

mismatches=[];owner_resolution=[];unresolved_owner=[];page_count=0
for page,rows in page_rows.items():
    for pr in rows:
        page_count+=1;uid=pr["uid"]
        owners=[f for f in SYSTEM_DOCS if uid in sys_by_uid[f]]
        if not owners:
            unresolved_owner.append({"page":page,"uid":uid,"reason":"NO_SYSTEM_OWNER_ROW","page_row":pr});continue
        chosen=None
        if len(owners)==1:chosen=owners[0]
        else:
            pair=tuple(sorted(owners))
            if pair in PAIR_PRECEDENCE:chosen=PAIR_PRECEDENCE[pair]
            else:
                # if one owner has an exact row and others do not, use unique exact owner
                exact_owners=[f for f in owners if any(r.get("runtime_status") in {"EFFECTFUL_EXACT","READ_EXACT"} for r in sys_by_uid[f][uid])]
                if len(exact_owners)==1:chosen=exact_owners[0]
        if chosen is None:
            unresolved_owner.append({"page":page,"uid":uid,"reason":"MULTI_OWNER_UNRESOLVED","owners":owners,"page_row":pr});continue
        orow=compose(sys_by_uid[chosen][uid])
        owner_resolution.append({"page":page,"uid":uid,"owner":chosen,"owners_seen":owners})
        for f in FIELDS:
            pv=pr.get(f,"");ov=orow.get(f,"")
            if missing(pv) and missing(ov):continue
            if missing(ov) and not missing(pv):
                mismatches.append({"kind":"OWNER_MISSING_FIELD","page":page,"uid":uid,"field":f,"page_value":pv,"owner_value":ov,"owner":chosen,"page_row":pr,"owner_row":orow})
            elif missing(pv) and not missing(ov):
                mismatches.append({"kind":"PAGE_MISSING_FIELD","page":page,"uid":uid,"field":f,"page_value":pv,"owner_value":ov,"owner":chosen,"page_row":pr,"owner_row":orow})
            elif pv!=ov:
                mismatches.append({"kind":"VALUE_CONFLICT","page":page,"uid":uid,"field":f,"page_value":pv,"owner_value":ov,"owner":chosen,"page_row":pr,"owner_row":orow})

by_kind=collections.Counter(x["kind"] for x in mismatches)
by_field=collections.Counter(x["field"] for x in mismatches)
by_owner=collections.Counter(x["owner"] for x in mismatches)
by_page=collections.Counter(x["page"] for x in mismatches)
# concise unique mismatch keys
summary={
 "page_exact_rows":page_count,
 "owner_resolved":len(owner_resolution),
 "unresolved_owner_rows":len(unresolved_owner),
 "mismatch_cells":len(mismatches),
 "by_kind":dict(by_kind),"by_field":dict(by_field),"by_owner":dict(by_owner),"by_page":dict(by_page),
}
report={"marker":"ACPOS-20260922-BATCH-65-FULL-PAGE-OWNER-BIDIRECTIONAL-PARITY-AUDIT-V1","base_head":BASE_HEAD,
"summary":summary,"mismatches":mismatches,"unresolved_owner":unresolved_owner,"owner_resolution":owner_resolution}
Path("__batch65_page_owner_parity_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch65_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH65_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
