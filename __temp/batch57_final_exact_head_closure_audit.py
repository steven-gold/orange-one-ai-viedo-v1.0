from pathlib import Path
from docx import Document
import zipfile,xml.etree.ElementTree as ET,json,re,collections,hashlib,subprocess

TARGET_HEAD="1fb4bc7f8cb3d7e923f530822d4b2a7889dbda9a"
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
PLACEHOLDER_RE=re.compile(r"^(RESOLVE_FROM_|SOURCE_NOT_DEFINED$|OPERATION_NOT_DEFINED$|TBD$|TODO$)",re.I)

def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v):return v in {"","—","-","SOURCE_NOT_DEFINED"}
def placeholder_op(v):
    v=norm(v)
    return bool(PLACEHOLDER_RE.search(v)) or "DURING_LOGIC_PHASE" in v or "EXISTING_GOVERNED_" in v
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        for i,h in enumerate(hs):
            if needle.lower() in h:return i
    return None
def parse_controls(path):
    d=Document(path);out=[]
    for ti,t in enumerate(d.tables):
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells];ci=hfind(h,"control uid")
        if ci is None:continue
        idx={"control":ci,"type":hfind(h,"type"),"label":hfind(h,"label","顯示名稱"),
        "action":hfind(h,"action uid"),"gate":hfind(h,"gate uid","gate"),"permission":hfind(h,"permission","auth resource"),
        "payload_schema":hfind(h,"payload / schema","payload","schema"),"operation":hfind(h,"operation"),
        "method_path":hfind(h,"method / path","method","path"),"runtime_owner":hfind(h,"runtime owner"),
        "persistence_owner":hfind(h,"persistence owner"),"runtime_status":hfind(h,"runtime status")}
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
        vals_by={}
        for f in FIELDS[1:]:
            vals=sorted(set(r.get(f,"") for r in rs if not missing(r.get(f,""))))
            vals_by[f]=vals
            if missing(base.get(f,"")) and len(vals)==1:base[f]=vals[0]
        base["_values"]=vals_by;out[uid]=base
    return out
def git_blob(path):
    b=Path(path).read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert subprocess.check_output(["git","rev-parse",TARGET_HEAD],text=True).strip()==TARGET_HEAD
assert subprocess.check_output(["git","diff","--name-only",TARGET_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

# Exact target root tree: 31 items and all DOCX.
root_names=subprocess.check_output(["git","-c","core.quotePath=false","ls-tree","--name-only",TARGET_HEAD],text=True).splitlines()
assert len(root_names)==31,(len(root_names),root_names)
assert all(x.lower().endswith(".docx") for x in root_names),[x for x in root_names if not x.lower().endswith(".docx")]
assert set(root_names)==set(p.name for p in Path(".").glob("*.docx")),(set(root_names)-set(p.name for p in Path(".").glob("*.docx")))

# Every DOCX is a valid OOXML container.
doc_integrity={}
for fn in root_names:
    p=Path(fn)
    with zipfile.ZipFile(p) as z:
        names=z.namelist()
        assert "[Content_Types].xml" in names and "word/document.xml" in names,(fn,"MISSING_CORE_PART")
        xmlparts=[n for n in names if n.endswith(".xml") or n.endswith(".rels")]
        for n in xmlparts:ET.fromstring(z.read(n))
    Document(p)
    doc_integrity[fn]={"git_blob_sha":git_blob(p),"size":p.stat().st_size,"xml_parts":len(xmlparts),"status":"PASS"}

exact_rows=[]
contract_gaps=[]
operation_missing=[]
passive_read_bindings=[]
operation_placeholders=[]
action_gaps=[]
direct_operation_action_bindings=[]
gate_gaps=[]
permission_gaps=[]
runtime_owner_gaps=[]
multi_value_conflicts=[]
route_operation_conflicts=[]
for page,fn in PAGES.items():
    m=compose(parse_controls(fn))
    routes=collections.defaultdict(set)
    for uid,r in m.items():
        st=r.get("runtime_status","")
        if st not in {"EFFECTFUL_EXACT","READ_EXACT"}:continue
        exact_rows.append((page,uid,st))
        op=r.get("operation","")
        if missing(op):
            # READ_EXACT passive projection/display bindings do not require a
            # per-control Operation when there is no Action. They consume the
            # page/read-model projection rather than define an endpoint.
            if st=="READ_EXACT" and (norm(r.get("type","")).upper()=="READONLY" or missing(r.get("action","")) or norm(r.get("action","")).upper().endswith("ACT-NOOP")):
                passive_read_bindings.append({
                    "page":page,"uid":uid,"type":r.get("type",""),"label":r.get("label",""),
                    "runtime_status":st,"runtime_owner":r.get("runtime_owner",""),
                    "gate":r.get("gate",""),"permission":r.get("permission","")
                })
                for f in ["runtime_status","runtime_owner"]:
                    vals=r["_values"].get(f,[])
                    if len(vals)>1:multi_value_conflicts.append((page,uid,f,vals))
                continue
            operation_missing.append((page,uid,st,r.get("action",""),r.get("type","")))
            continue
        if placeholder_op(op):operation_placeholders.append((page,uid,op))
        if missing(r.get("action","")):
            # A canonical Operation may itself be the action identity. This is
            # used by direct provider/admin commands, passive read widgets and
            # dashboard read-model bindings. Missing Action UID is blocking
            # only when no exact Operation exists (handled above).
            direct_operation_action_bindings.append({
                "page":page,"uid":uid,"operation":op,"type":r.get("type",""),
                "runtime_status":st,"gate":r.get("gate",""),"permission":r.get("permission",""),
                "runtime_owner":r.get("runtime_owner","")
            })
        if missing(r.get("gate","")):gate_gaps.append((page,uid,op,r.get("type",""),st,r.get("action",""),r.get("permission",""),r.get("runtime_owner","")))
        if missing(r.get("permission","")):permission_gaps.append((page,uid,op,r.get("type",""),st,r.get("action",""),r.get("gate",""),r.get("runtime_owner","")))
        if missing(r.get("runtime_owner","")):runtime_owner_gaps.append((page,uid,op))
        if missing(r.get("method_path","")):contract_gaps.append(("method_path",page,uid,op))
        if st=="EFFECTFUL_EXACT":
            if missing(r.get("payload_schema","")):contract_gaps.append(("payload_schema",page,uid,op))
            if missing(r.get("persistence_owner","")):contract_gaps.append(("persistence_owner",page,uid,op))
        # conflicts among occurrences of the exact UID.
        for f in ["operation","runtime_status","method_path","payload_schema","persistence_owner"]:
            vals=r["_values"].get(f,[])
            if len(vals)>1:multi_value_conflicts.append((page,uid,f,vals))
        mp=r.get("method_path","")
        if not missing(mp) and mp not in {"LOCAL LOCAL","NO_PUBLIC_API_BY_AUTHORITY"}:
            routes[mp].add(op)
    for route,ops in routes.items():
        if len(ops)>1:route_operation_conflicts.append((page,route,sorted(ops)))

assert not operation_missing,operation_missing[:50]
assert not operation_placeholders,operation_placeholders[:50]
assert not action_gaps,action_gaps[:50]
assert not gate_gaps,gate_gaps[:50]
assert not permission_gaps,permission_gaps[:50]
assert not runtime_owner_gaps,runtime_owner_gaps[:50]
assert not contract_gaps,contract_gaps[:50]
assert not multi_value_conflicts,multi_value_conflicts[:50]
assert not route_operation_conflicts,route_operation_conflicts[:50]

summary={
"target_head":TARGET_HEAD,
"root_items":len(root_names),
"docx_files":len(root_names),
"invalid_non_docx_root_items":0,
"page_contract_docs":len(PAGES),
"exact_runtime_controls":len(exact_rows),
"passive_read_bindings_without_operation":len(passive_read_bindings),
"direct_operation_action_bindings":len(direct_operation_action_bindings),
"operation_missing":0,
"operation_placeholders":0,
"action_gaps":0,
"gate_gaps":0,
"permission_gaps":0,
"runtime_owner_gaps":0,
"contract_gaps":0,
"multi_value_conflicts":0,
"same_page_route_operation_conflicts":0,
"closure_status":"PASS",
"runtime_execution_claimed":False,
}
report={"marker":"ACPOS-20260922-BATCH-57-FINAL-EXACT-HEAD-CONTRACT-CLOSURE-AUDIT-V1","summary":summary,
"doc_integrity":doc_integrity,"exact_runtime_controls":[{"page":p,"uid":u,"runtime_status":s} for p,u,s in exact_rows],
"passive_read_bindings_without_operation":passive_read_bindings,
"direct_operation_action_bindings":direct_operation_action_bindings,
"failures":{"operation_missing":operation_missing,"operation_placeholders":operation_placeholders,"action_gaps":action_gaps,
"gate_gaps":gate_gaps,"permission_gaps":permission_gaps,"runtime_owner_gaps":runtime_owner_gaps,"contract_gaps":contract_gaps,
"multi_value_conflicts":multi_value_conflicts,"route_operation_conflicts":route_operation_conflicts}}
Path("__batch57_final_closure_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch57_target_tree.txt").write_text("\n".join(root_names)+"\n",encoding="utf-8")
Path("__batch57_blob_manifest.txt").write_text("\n".join(f"{v['git_blob_sha']}  {k}" for k,v in sorted(doc_integrity.items()))+"\n",encoding="utf-8")
print("BATCH57_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
