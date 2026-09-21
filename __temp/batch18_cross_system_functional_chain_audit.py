from pathlib import Path
from docx import Document
import json,re,collections,subprocess,hashlib

BASE_HEAD="3e8d73368d340da6a081fa717d50aaf6013062ac"
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
COMPARE_FIELDS=["action","gate","permission","payload_schema","operation","method_path","runtime_owner","persistence_owner","runtime_status"]

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
            rec.update({"file":path,"table":ti+1,"row":ri})
            out.append(rec)
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
        base["_field_values"]=fv;base["_occurrences"]=len(rs);out[uid]=base
    return out

root=sorted(p.name for p in Path(".").glob("*.docx"))
assert len(root)==31,len(root)
assert subprocess.check_output(["git","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

page_rows={p:parse_controls(f) for p,f in PAGES.items()}
page_maps={p:compose(rows) for p,rows in page_rows.items()}
sys_rows={f:parse_controls(f) for f in SYSTEM_DOCS}
sys_maps={f:compose(rows) for f,rows in sys_rows.items()}

findings=[]

# 1) Physical duplicate Control UID across page documents.
uid_pages=collections.defaultdict(list)
for page,m in page_maps.items():
    for uid in m:uid_pages[uid].append(page)
for uid,pages in sorted(uid_pages.items()):
    if len(pages)>1:
        findings.append({"class":"CONTROL_UID_CROSS_PAGE_COLLISION","uid":uid,"pages":pages,"severity":"BLOCKER"})

# 2) Contradictory duplicate rows inside one page document.
for page,m in page_maps.items():
    for uid,r in m.items():
        for f in COMPARE_FIELDS:
            vals=r["_field_values"].get(f,[])
            if len(vals)>1:
                findings.append({"class":"PAGE_INTERNAL_FIELD_CONFLICT","page":page,"uid":uid,"field":f,"values":vals,"severity":"BLOCKER"})

# 3) Cross-system exact UID value drift. This is raw evidence; reference-only copies are reported separately, not auto-mutated.
for page,m in page_maps.items():
    for uid,pr in m.items():
        occ=[]
        for sf,sm in sys_maps.items():
            if uid in sm:occ.append((sf,sm[uid]))
        if not occ:continue
        for f in COMPARE_FIELDS:
            pv=pr.get(f,"")
            sysvals=collections.defaultdict(list)
            for sf,sr in occ:
                sv=sr.get(f,"")
                if not missing(sv):sysvals[sv].append(sf)
            if not missing(pv):
                different={v:fs for v,fs in sysvals.items() if v!=pv}
                if different:
                    findings.append({"class":"PAGE_SYSTEM_FIELD_DRIFT_RAW","page":page,"uid":uid,"field":f,"page_value":pv,"system_values":different,"severity":"REVIEW"})
            elif len(sysvals)>1:
                findings.append({"class":"SYSTEM_OWNER_FIELD_CONFLICT_RAW","page":page,"uid":uid,"field":f,"system_values":dict(sysvals),"severity":"REVIEW"})

# 4) Operation identity consistency across current page contracts.
ops=collections.defaultdict(list)
routes=collections.defaultdict(list)
for page,m in page_maps.items():
    for uid,r in m.items():
        op=r.get("operation","");mp=r.get("method_path","");ro=r.get("runtime_owner","")
        if not missing(op):ops[op].append((page,uid,r))
        if not missing(mp):routes[mp].append((page,uid,r))
for op,rows in sorted(ops.items()):
    methods=sorted(set(r.get("method_path","") for _,_,r in rows if not missing(r.get("method_path",""))))
    owners=sorted(set(r.get("runtime_owner","") for _,_,r in rows if not missing(r.get("runtime_owner",""))))
    if len(methods)>1:
        findings.append({"class":"OPERATION_METHOD_PATH_CONFLICT","operation":op,"methods":methods,"controls":[[p,u] for p,u,_ in rows],"severity":"BLOCKER"})
    if len(owners)>1:
        findings.append({"class":"OPERATION_RUNTIME_OWNER_CONFLICT","operation":op,"owners":owners,"controls":[[p,u] for p,u,_ in rows],"severity":"BLOCKER"})
for mp,rows in sorted(routes.items()):
    opvals=sorted(set(r.get("operation","") for _,_,r in rows if not missing(r.get("operation",""))))
    if len(opvals)>1:
        findings.append({"class":"METHOD_PATH_OPERATION_COLLISION","method_path":mp,"operations":opvals,"controls":[[p,u] for p,u,_ in rows],"severity":"BLOCKER"})

# 5) Transport/payload readiness inventory after definition closure.
transport=[]
payload=[]
persistence=[]
status_method=[]
for page,m in page_maps.items():
    for uid,r in m.items():
        st=r.get("runtime_status","");op=r.get("operation","");mp=r.get("method_path","")
        if st in {"EFFECTFUL_EXACT","READ_EXACT"} and not missing(op):
            if missing(mp):
                transport.append({"page":page,"uid":uid,"runtime_status":st,"operation":op,"runtime_owner":r.get("runtime_owner",""),"permission":r.get("permission",""),"gate":r.get("gate","")})
            if st=="EFFECTFUL_EXACT" and missing(r.get("payload_schema","")):
                payload.append({"page":page,"uid":uid,"operation":op,"runtime_owner":r.get("runtime_owner",""),"method_path":mp})
            if st=="EFFECTFUL_EXACT" and missing(r.get("persistence_owner","")):
                persistence.append({"page":page,"uid":uid,"operation":op,"runtime_owner":r.get("runtime_owner",""),"method_path":mp})
            if not missing(mp):
                verb=mp.split(" ",1)[0].upper()
                if st=="EFFECTFUL_EXACT" and verb=="GET":
                    status_method.append({"page":page,"uid":uid,"runtime_status":st,"method_path":mp,"operation":op,"class":"EFFECTFUL_GET_REVIEW"})
                if st=="READ_EXACT" and verb in {"DELETE","PATCH","PUT"}:
                    status_method.append({"page":page,"uid":uid,"runtime_status":st,"method_path":mp,"operation":op,"class":"READ_MUTATION_VERB_REVIEW"})

# 6) Action identity reused across multiple distinct operations (review, not auto blocker).
actions=collections.defaultdict(list)
for page,m in page_maps.items():
    for uid,r in m.items():
        a=r.get("action","");op=r.get("operation","")
        if not missing(a) and not missing(op):actions[a].append((page,uid,op))
action_multi=[]
for a,rows in sorted(actions.items()):
    opset=sorted(set(op for _,_,op in rows))
    if len(opset)>1:action_multi.append({"action":a,"operations":opset,"controls":[[p,u] for p,u,_ in rows]})

# 7) System document raw canonical duplication inventory.
uid_systems=collections.defaultdict(list)
for sf,m in sys_maps.items():
    for uid in m:uid_systems[uid].append(sf)
multi_system={uid:fs for uid,fs in uid_systems.items() if len(fs)>1}

summary={
"root_docx":len(root),"page_contracts":len(PAGES),"system_contracts":len(SYSTEM_DOCS),
"page_control_uids":sum(len(m) for m in page_maps.values()),
"unique_page_control_uids":len(uid_pages),
"cross_page_uid_collisions":sum(1 for f in findings if f["class"]=="CONTROL_UID_CROSS_PAGE_COLLISION"),
"page_internal_field_conflicts":sum(1 for f in findings if f["class"]=="PAGE_INTERNAL_FIELD_CONFLICT"),
"page_system_field_drift_raw":sum(1 for f in findings if f["class"]=="PAGE_SYSTEM_FIELD_DRIFT_RAW"),
"system_owner_field_conflict_raw":sum(1 for f in findings if f["class"]=="SYSTEM_OWNER_FIELD_CONFLICT_RAW"),
"operation_method_conflicts":sum(1 for f in findings if f["class"]=="OPERATION_METHOD_PATH_CONFLICT"),
"operation_owner_conflicts":sum(1 for f in findings if f["class"]=="OPERATION_RUNTIME_OWNER_CONFLICT"),
"route_operation_collisions":sum(1 for f in findings if f["class"]=="METHOD_PATH_OPERATION_COLLISION"),
"effectful_read_transport_unbound":len(transport),
"effectful_payload_unbound":len(payload),
"effectful_persistence_owner_unbound":len(persistence),
"status_method_reviews":len(status_method),
"action_multi_operation_review":len(action_multi),
"multi_system_uid_raw":len(multi_system),
}
summary["blocker_count"]=sum(1 for f in findings if f.get("severity")=="BLOCKER")
summary["review_count"]=sum(1 for f in findings if f.get("severity")=="REVIEW")+len(status_method)+len(action_multi)
report={
"marker":"ACPOS-20260922-BATCH-18-CROSS-SYSTEM-FUNCTIONAL-CHAIN-AUDIT-V1",
"base_head":BASE_HEAD,"summary":summary,"findings":findings,
"transport_unbound":transport,"payload_unbound":payload,"persistence_owner_unbound":persistence,
"status_method_reviews":status_method,"action_multi_operation_review":action_multi,
"multi_system_uid_raw":multi_system,
}
Path("__batch18_functional_chain_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch18_summary.txt").write_text("\n".join(f"{k}={v}" for k,v in summary.items())+"\n",encoding="utf-8")
print("BATCH18_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
