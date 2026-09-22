from pathlib import Path
from docx import Document
import json,re,collections,subprocess

BASE_HEAD="9e20f1b7a080cb1ecc9795ab96b2428b8e794fcc"
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
    exact=[r for r in rows if r.get("runtime_status") in {"EFFECTFUL_EXACT","READ_EXACT"}]
    pool=exact if exact else rows
    base=max(pool,key=lambda r:sum(not missing(r.get(f,"")) for f in FIELDS)).copy()
    vals_by={}
    for f in FIELDS:
        vals=sorted(set(r.get(f,"") for r in pool if not missing(r.get(f,""))))
        vals_by[f]=vals
        if missing(base.get(f,"")) and len(vals)==1:base[f]=vals[0]
    base["_values"]=vals_by;base["_row_count"]=len(pool);base["_rows"]=pool
    return base
assert len(list(Path(".").glob("*.docx")))==31
assert subprocess.check_output(["git","-c","core.quotePath=false","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

sys_by_uid={f:collections.defaultdict(list) for f in SYSTEM_DOCS}
for f in SYSTEM_DOCS:
    for r in parse(f):sys_by_uid[f][r["uid"]].append(r)

page_by_uid={page:collections.defaultdict(list) for page in PAGE_DOCS}
for page,fn in PAGE_DOCS.items():
    for r in parse(fn):
        if r.get("runtime_status") in {"EFFECTFUL_EXACT","READ_EXACT"}:
            page_by_uid[page][r["uid"]].append(r)

effective_mismatches=[];unresolved_owner=[];owner_resolution=[]
raw_split_bindings=[];raw_conflicts=[];raw_duplicate_uids=[]
for page,uidmap in page_by_uid.items():
    for uid,rows in uidmap.items():
        pc=compose(rows)
        if len(rows)>1:
            raw_duplicate_uids.append({"page":page,"uid":uid,"count":len(rows),"rows":rows})
            for f in FIELDS:
                vals=pc["_values"][f]
                if len(vals)>1:
                    raw_conflicts.append({"scope":"PAGE","page":page,"uid":uid,"field":f,"values":vals,"rows":rows})
            # split binding if some exact rows are missing a value that another exact row provides.
            for f in FIELDS:
                vals=pc["_values"][f]
                if len(vals)==1 and any(missing(r.get(f,"")) for r in rows) and any(not missing(r.get(f,"")) for r in rows):
                    raw_split_bindings.append({"scope":"PAGE","page":page,"uid":uid,"field":f,"resolved_value":vals[0],"rows":rows})
        owners=[f for f in SYSTEM_DOCS if uid in sys_by_uid[f]]
        if not owners:
            unresolved_owner.append({"page":page,"uid":uid,"reason":"NO_SYSTEM_OWNER_ROW","page_composite":pc});continue
        chosen=None
        if len(owners)==1:chosen=owners[0]
        else:
            pair=tuple(sorted(owners))
            if pair in PAIR_PRECEDENCE:chosen=PAIR_PRECEDENCE[pair]
            else:
                exact_owners=[f for f in owners if any(r.get("runtime_status") in {"EFFECTFUL_EXACT","READ_EXACT"} for r in sys_by_uid[f][uid])]
                if len(exact_owners)==1:chosen=exact_owners[0]
        if chosen is None:
            unresolved_owner.append({"page":page,"uid":uid,"reason":"MULTI_OWNER_UNRESOLVED","owners":owners,"page_composite":pc});continue
        oc=compose(sys_by_uid[chosen][uid])
        owner_resolution.append({"page":page,"uid":uid,"owner":chosen,"owners_seen":owners})
        # raw owner ambiguity
        orows=[r for r in sys_by_uid[chosen][uid] if r.get("runtime_status") in {"EFFECTFUL_EXACT","READ_EXACT"}]
        if len(orows)>1:
            for f in FIELDS:
                vals=oc["_values"][f]
                if len(vals)>1:
                    raw_conflicts.append({"scope":"OWNER","page":page,"uid":uid,"owner":chosen,"field":f,"values":vals,"rows":orows})
                if len(vals)==1 and any(missing(r.get(f,"")) for r in orows) and any(not missing(r.get(f,"")) for r in orows):
                    raw_split_bindings.append({"scope":"OWNER","page":page,"uid":uid,"owner":chosen,"field":f,"resolved_value":vals[0],"rows":orows})
        for f in FIELDS:
            pv=pc.get(f,"");ov=oc.get(f,"")
            if missing(pv) and missing(ov):continue
            if missing(ov) and not missing(pv):
                effective_mismatches.append({"kind":"OWNER_MISSING_FIELD","page":page,"uid":uid,"field":f,"page_value":pv,"owner_value":ov,"owner":chosen})
            elif missing(pv) and not missing(ov):
                effective_mismatches.append({"kind":"PAGE_MISSING_FIELD","page":page,"uid":uid,"field":f,"page_value":pv,"owner_value":ov,"owner":chosen})
            elif pv!=ov:
                effective_mismatches.append({"kind":"VALUE_CONFLICT","page":page,"uid":uid,"field":f,"page_value":pv,"owner_value":ov,"owner":chosen})

summary={
 "page_unique_exact_controls":sum(len(m) for m in page_by_uid.values()),
 "owner_resolved":len(owner_resolution),
 "unresolved_owner_controls":len(unresolved_owner),
 "effective_mismatch_cells":len(effective_mismatches),
 "effective_by_kind":dict(collections.Counter(x["kind"] for x in effective_mismatches)),
 "effective_by_field":dict(collections.Counter(x["field"] for x in effective_mismatches)),
 "raw_duplicate_page_uids":len(raw_duplicate_uids),
 "raw_split_binding_cells":len(raw_split_bindings),
 "raw_multi_value_conflict_cells":len(raw_conflicts),
}
report={"marker":"ACPOS-20260922-BATCH-66-EFFECTIVE-PARITY-RAW-AMBIGUITY-AUDIT-V1","base_head":BASE_HEAD,
"summary":summary,"effective_mismatches":effective_mismatches,"unresolved_owner":unresolved_owner,
"raw_duplicate_page_uids":raw_duplicate_uids,"raw_split_bindings":raw_split_bindings,"raw_conflicts":raw_conflicts,
"owner_resolution":owner_resolution}
Path("__batch66_effective_parity_raw_ambiguity.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch66_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH66_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
