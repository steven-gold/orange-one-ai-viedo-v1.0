from pathlib import Path
from docx import Document
import json,re,collections,subprocess

BASE_HEAD="a110c6510d4d460ada6eb20f1cf0b54b93017184"
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
FIELDS=["control","type","label","action","gate","permission","payload_schema","operation","method_path","runtime_owner","persistence_owner","runtime_status"]

def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v):return v in {"","—","-","SOURCE_NOT_DEFINED"}
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None
def parse_controls(path):
    d=Document(path);out=[]
    for ti,t in enumerate(d.tables):
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells];ci=hfind(h,"control uid")
        if ci is None:continue
        idx={"control":ci,"type":hfind(h,"type"),"label":hfind(h,"label","顯示名稱"),
          "action":hfind(h,"action uid"),"gate":hfind(h,"gate uid","gate"),
          "permission":hfind(h,"permission","auth resource"),
          "payload_schema":hfind(h,"payload / schema","payload","schema"),
          "operation":hfind(h,"operation"),"method_path":hfind(h,"method / path","method","path"),
          "runtime_owner":hfind(h,"runtime owner"),"persistence_owner":hfind(h,"persistence owner"),
          "runtime_status":hfind(h,"runtime status")}
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells];uid=vals[ci] if ci<len(vals) else ""
            if not uid or uid in {"—","-"}:continue
            rec={k:(vals[i] if i is not None and i<len(vals) else "") for k,i in idx.items()}
            rec.update({"file":path,"table":ti+1,"row":ri,"field_columns":{k:(i is not None) for k,i in idx.items()}})
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
        base["_rows"]=rs
        out[uid]=base
    return out

assert len(list(Path(".").glob("*.docx")))==31
assert subprocess.check_output(["git","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

page_rows={p:parse_controls(fn) for p,fn in PAGES.items()}
page_maps={p:compose(rows) for p,rows in page_rows.items()}
sys_rows=[]
for sf in SYSTEM_DOCS:
    for r in parse_controls(sf):
        r["system_file"]=sf;sys_rows.append(r)

targets=[]
for page,m in page_maps.items():
    for uid,r in m.items():
        st=r.get("runtime_status","");op=r.get("operation","")
        if st in {"EFFECTFUL_EXACT","READ_EXACT"} and not missing(op) and missing(r.get("method_path","")):
            targets.append(("method_path",page,uid,r))
        if st=="EFFECTFUL_EXACT" and not missing(op) and missing(r.get("payload_schema","")):
            targets.append(("payload_schema",page,uid,r))
        if st=="EFFECTFUL_EXACT" and not missing(op) and missing(r.get("persistence_owner","")):
            targets.append(("persistence_owner",page,uid,r))
counts=collections.Counter(f for f,_,_,_ in targets)
assert counts=={"method_path":80,"payload_schema":137,"persistence_owner":124},counts

rows=[]
for field,page,uid,r in targets:
    exact_uid=[s for s in sys_rows if s["control"]==uid]
    vals=collections.defaultdict(list)
    for s in exact_uid:
        v=s.get(field,"")
        if not missing(v):
            vals[v].append({"system_file":s["system_file"],"table":s["table"],"row":s["row"],"operation":s.get("operation",""),"runtime_owner":s.get("runtime_owner",""),"runtime_status":s.get("runtime_status","")})
    if len(vals)==1:
        cls="EXACT_UID_UNIQUE_SOURCE"
        candidate=next(iter(vals))
    elif len(vals)>1:
        cls="EXACT_UID_SOURCE_CONFLICT"
        candidate=None
    else:
        cls="EXACT_UID_NO_SOURCE"
        candidate=None
    field_present=any(pr["field_columns"].get(field,False) for pr in r["_rows"])
    rows.append({
      "field":field,"page":page,"uid":uid,"runtime_status":r.get("runtime_status",""),"operation":r.get("operation",""),
      "runtime_owner":r.get("runtime_owner",""),"gate":r.get("gate",""),"permission":r.get("permission",""),
      "page_field_column_present":field_present,"classification":cls,"candidate":candidate,
      "source_values":dict(vals),
    })

summary={
"target_cells":len(rows),
"method_path":counts["method_path"],"payload_schema":counts["payload_schema"],"persistence_owner":counts["persistence_owner"],
"exact_uid_unique_source":sum(1 for x in rows if x["classification"]=="EXACT_UID_UNIQUE_SOURCE"),
"exact_uid_source_conflict":sum(1 for x in rows if x["classification"]=="EXACT_UID_SOURCE_CONFLICT"),
"exact_uid_no_source":sum(1 for x in rows if x["classification"]=="EXACT_UID_NO_SOURCE"),
"page_schema_field_absent":sum(1 for x in rows if not x["page_field_column_present"]),
}
summary["by_field_class"]={}
for field in ["method_path","payload_schema","persistence_owner"]:
    summary["by_field_class"][field]=dict(collections.Counter(x["classification"] for x in rows if x["field"]==field))
summary["by_page"]=dict(collections.Counter(x["page"] for x in rows))
report={
"marker":"ACPOS-20260922-BATCH-21-EXACT-UID-TRANSPORT-PAYLOAD-PERSISTENCE-AUDIT-V1",
"base_head":BASE_HEAD,"summary":summary,"rows":rows,
}
Path("__batch21_exact_uid_applicability_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch21_summary.txt").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("BATCH21_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
