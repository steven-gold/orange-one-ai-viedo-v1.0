from pathlib import Path
from docx import Document
import json,re,collections,subprocess

BASE_HEAD="199b77eee06722b546702214aa64587f46ea3b60"
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
S02=SYSTEM_DOCS[1];S03=SYSTEM_DOCS[2];S04=SYSTEM_DOCS[3];S05=SYSTEM_DOCS[4];S06=SYSTEM_DOCS[5];S08=SYSTEM_DOCS[7];S09=SYSTEM_DOCS[8]
PAIR_PRECEDENCE={
 tuple(sorted((S03,S09))):S03,
 tuple(sorted((S02,S04))):S02,
 tuple(sorted((S02,S06))):S06,
 tuple(sorted((S02,S08))):S02,
 tuple(sorted((S02,S09))):S02,
}
FIELDS=["control","type","label","action","gate","permission","payload_schema","operation","method_path","runtime_owner","persistence_owner","runtime_status"]
PLACEHOLDER_RE=re.compile(r"^(RESOLVE_FROM_|SOURCE_NOT_DEFINED$|OPERATION_NOT_DEFINED$|TBD$|TODO$)",re.I)

def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v):return v in {"","—","-","SOURCE_NOT_DEFINED"}
def is_placeholder_op(v):
    v=norm(v)
    return bool(PLACEHOLDER_RE.search(v)) or "DURING_LOGIC_PHASE" in v or "EXISTING_GOVERNED_" in v
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
            rec.update({"file":path,"table":ti+1,"row":ri});out.append(rec)
    return out
def compose(rows):
    g=collections.defaultdict(list)
    for r in rows:g[r["control"]].append(r)
    out={}
    for uid,rs in g.items():
        base=max(rs,key=lambda r:sum(not missing(r.get(f,"")) for f in FIELDS[1:])).copy()
        fv={}
        for f in FIELDS[1:]:
            vals=sorted(set(r.get(f,"") for r in rs if not missing(r.get(f,""))))
            fv[f]=vals
            if missing(base.get(f,"")) and len(vals)==1:base[f]=vals[0]
        base["_field_values"]=fv;out[uid]=base
    return out

assert len(list(Path(".").glob("*.docx")))==31
assert subprocess.check_output(["git","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

page_maps={p:compose(parse_controls(fn)) for p,fn in PAGES.items()}
sys_rows={sf:parse_controls(sf) for sf in SYSTEM_DOCS}
sys_maps={sf:compose(rows) for sf,rows in sys_rows.items()}

targets=[]
for page,m in page_maps.items():
    for uid,r in m.items():
        if is_placeholder_op(r.get("operation","")):
            targets.append((page,uid,r))
summary_pre=collections.Counter(page for page,_,_ in targets)
assert len(targets)==3,(len(targets),[(p,u,r.get("operation")) for p,u,r in targets])

rows=[]
for page,uid,r in targets:
    sources=sorted(sf for sf,sm in sys_maps.items() if uid in sm)
    if len(sources)==1: owner=sources[0]
    else:
        pair=tuple(sources);assert pair in PAIR_PRECEDENCE,(page,uid,sources);owner=PAIR_PRECEDENCE[pair]
    owner_exact=sys_maps[owner].get(uid)
    exact_owner_op=owner_exact.get("operation","") if owner_exact else ""
    # Find relation candidates inside the same owner. Require exact Action+Gate+Permission+RuntimeStatus match.
    candidates=[]
    for sr in sys_rows[owner]:
        op=sr.get("operation","")
        if missing(op) or is_placeholder_op(op):continue
        if sr.get("runtime_status","")!=r.get("runtime_status",""):continue
        dims=["action","gate","permission"]
        comparable=[d for d in dims if not missing(r.get(d,""))]
        if not comparable:continue
        if all(sr.get(d,"")==r.get(d,"") for d in comparable):
            candidates.append({"operation":op,"control":sr["control"],"table":sr["table"],"row":sr["row"],
              "action":sr.get("action",""),"gate":sr.get("gate",""),"permission":sr.get("permission",""),
              "runtime_status":sr.get("runtime_status",""),"runtime_owner":sr.get("runtime_owner","")})
    vals=collections.defaultdict(list)
    for c in candidates:vals[c["operation"]].append(c)
    if owner_exact and not missing(exact_owner_op) and not is_placeholder_op(exact_owner_op):
        cls="EXACT_UID_OWNER_REAL_OPERATION";candidate=exact_owner_op
    elif len(vals)==1:
        cls="STRONG_RELATION_OPERATION_CANDIDATE";candidate=next(iter(vals))
    elif len(vals)>1:
        cls="OPERATION_RELATION_CONFLICT";candidate=None
    else:
        cls="CANONICAL_OPERATION_REMEDIATION_REQUIRED";candidate=None
    rows.append({
      "page":page,"uid":uid,"placeholder_operation":r.get("operation",""),
      "runtime_status":r.get("runtime_status",""),"action":r.get("action",""),"gate":r.get("gate",""),
      "permission":r.get("permission",""),"runtime_owner":r.get("runtime_owner",""),
      "canonical_owner":owner,"owner_exact_uid_operation":exact_owner_op,
      "classification":cls,"candidate":candidate,"candidate_values":dict(vals),
    })

summary={
"placeholder_controls":len(rows),
"by_page":dict(summary_pre),
"exact_uid_owner_real_operation":sum(1 for x in rows if x["classification"]=="EXACT_UID_OWNER_REAL_OPERATION"),
"strong_relation_operation_candidate":sum(1 for x in rows if x["classification"]=="STRONG_RELATION_OPERATION_CANDIDATE"),
"operation_relation_conflict":sum(1 for x in rows if x["classification"]=="OPERATION_RELATION_CONFLICT"),
"canonical_operation_remediation_required":sum(1 for x in rows if x["classification"]=="CANONICAL_OPERATION_REMEDIATION_REQUIRED"),
}
assert sum(summary[k] for k in ["exact_uid_owner_real_operation","strong_relation_operation_candidate","operation_relation_conflict","canonical_operation_remediation_required"])==3
report={"marker":"ACPOS-20260922-BATCH-30-OPERATION-SEMANTIC-PLACEHOLDER-AUDIT-V1","base_head":BASE_HEAD,"summary":summary,"rows":rows}
Path("__batch30_operation_placeholder_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch30_summary.txt").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("BATCH30_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
