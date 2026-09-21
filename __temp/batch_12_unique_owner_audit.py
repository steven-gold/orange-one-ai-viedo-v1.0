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

def norm(x): return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v): return v in {"","—","-","SOURCE_NOT_DEFINED"}
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None
def exact_col(headers,names):
    hs=[norm(x).lower() for x in headers]
    for name in names:
        n=name.lower()
        for i,h in enumerate(hs):
            if h==n:return i
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
        idx={
          "control":ci,"type":hfind(h,"type"),"label":hfind(h,"label","顯示名稱"),
          "action":hfind(h,"action uid"),"gate":hfind(h,"gate uid","gate"),
          "permission":hfind(h,"permission","auth resource"),"operation":hfind(h,"operation"),
          "runtime_owner":hfind(h,"runtime owner"),"runtime_status":hfind(h,"runtime status")
        }
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells]
            uid=vals[ci] if ci<len(vals) else ""
            if not uid or uid in {"—","-"}:continue
            rec={k:(vals[i] if i is not None and i<len(vals) else "") for k,i in idx.items()}
            rec.update({"source":path,"table":ti+1,"row":ri,"headers":h,"values":vals})
            out.append(rec)
    return out

def compose(rows):
    groups=collections.defaultdict(list)
    for r in rows:groups[r["control"]].append(r)
    out={}
    for uid,rs in groups.items():
        base=max(rs,key=lambda r:sum(not missing(r.get(f,"")) for f in FIELDS[1:])).copy()
        for f in FIELDS[1:]:
            vals=sorted(set(r.get(f,"") for r in rs if not missing(r.get(f,""))))
            if missing(base.get(f,"")) and len(vals)==1:base[f]=vals[0]
        base["same_uid_rows"]=rs
        out[uid]=base
    return out

def is_gap(field,r):
    v=r.get(field,"");st=r.get("runtime_status","")
    if not missing(v):return False
    if "UI_LOCAL_EXACT" in st:
        if field in {"operation","runtime_owner"}:return False
        if field=="action" and display_only_type(r.get("type","")):return False
    if "OWNER_ORCHESTRATED_RUNTIME_EXACT_NO_PUBLIC_ROUTE" in st and field=="operation":return False
    if "READ_EXACT" in st and display_only_type(r.get("type","")):
        if field=="action":return False
        if field=="operation" and not missing(r.get("runtime_owner","")):return False
    if field=="runtime_owner" and any(x in st for x in ["SPEC_EXACT_RUNTIME_BLOCKED","SPEC_EXACT_RUNTIME_NOT_EXECUTED","RUNTIME_IMPLEMENTATION_BLOCKED"]):return False
    if v=="SOURCE_NOT_DEFINED":return False
    return True

# Physical owner rows and generic exact-column rows.
owner_rows=collections.defaultdict(list)
generic=collections.defaultdict(list)
reference_only=collections.defaultdict(lambda:collections.defaultdict(list))
for sf in SYSTEMS:
    d=Document(sf)
    for ti,t in enumerate(d.tables):
        if not t.rows:continue
        headers=[norm(c.text) for c in t.rows[0].cells]
        vals_rows=[]
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells]
            if any(vals):
                rec={"source":sf,"table":ti+1,"row":ri,"headers":headers,"values":vals}
                generic[sf].append(rec)
                vals_rows.append((ri,vals))
        # Product-control registration.
        ci=hfind(headers,"control uid")
        if ci is not None:
            for ri,vals in vals_rows:
                if ci<len(vals):
                    uid=vals[ci]
                    if uid and uid not in {"—","-"}:
                        owner_rows[uid].append({"source":sf,"table":ti+1,"row":ri,"headers":headers,"values":vals})
        # Batch-10 reference-only supersession register.
        ri_uid=exact_col(headers,["Reference UID"])
        ci_owner=exact_col(headers,["Canonical Owner"])
        ci_field=exact_col(headers,["Missing Field"])
        ci_role=exact_col(headers,["Local Role"])
        if ri_uid is not None and ci_owner is not None:
            for rowno,vals in vals_rows:
                uid=vals[ri_uid] if ri_uid<len(vals) else ""
                owner=vals[ci_owner] if ci_owner<len(vals) else ""
                field=vals[ci_field] if ci_field is not None and ci_field<len(vals) else ""
                role=vals[ci_role] if ci_role is not None and ci_role<len(vals) else ""
                if uid and owner and ("REFERENCE" in role.upper() or "REFERENCE" in " ".join(headers).upper()):
                    reference_only[uid][field].append({"secondary":sf,"canonical_name":owner,"table":ti+1,"row":rowno})

# Current 249 gap inventory.
current=[]
page_maps={}
for page,fn in PAGES.items():
    bm=compose(parse_controls(fn));page_maps[page]=bm
    for uid,r in bm.items():
        for field in ["action","gate","permission","operation","runtime_owner"]:
            if is_gap(field,r):
                current.append({
                    "page":page,"file":fn,"uid":uid,"field":field,
                    "type":r.get("type",""),"label":r.get("label",""),
                    "action":r.get("action",""),"gate":r.get("gate",""),
                    "permission":r.get("permission",""),"operation":r.get("operation",""),
                    "runtime_owner":r.get("runtime_owner",""),"runtime_status":r.get("runtime_status",""),
                })
assert len(current)==249,len(current)

sys_conf=[x for x in current if x["page"]=="SYS-01" and x["uid"]=="SYS-01-BTN-NAV-OPEN" and x["field"]=="gate"]
assert len(sys_conf)==1,sys_conf

# Effective owner resolution: remove Batch-10 reference-only secondary registrations.
resolved=[]
for q in current:
    physical=sorted(set(r["source"] for r in owner_rows.get(q["uid"],[])))
    refs=reference_only.get(q["uid"],{}).get(q["field"],[])
    secondary=set(r["secondary"] for r in refs)
    effective=[s for s in physical if s not in secondary]
    # If field-specific supersession absent but exactly one canonical name is recorded for same UID,
    # allow it only when all recorded rows agree.
    if len(effective)!=1 and reference_only.get(q["uid"]):
        canon_names=set()
        secondary_all=set()
        for rr in reference_only[q["uid"]].values():
            for item in rr:
                canon_names.add(item["canonical_name"])
                secondary_all.add(item["secondary"])
        eff2=[s for s in physical if s not in secondary_all]
        if len(eff2)==1:
            effective=eff2
    rec=q|{"physical_owners":physical,"effective_owners":effective,"reference_only_evidence":refs}
    resolved.append(rec)

ordinary=[r for r in resolved if not (r["page"]=="SYS-01" and r["uid"]=="SYS-01-BTN-NAV-OPEN" and r["field"]=="gate")]
assert len(ordinary)==248
assert all(len(r["effective_owners"])==1 for r in ordinary),[(r["page"],r["uid"],r["field"],r["physical_owners"],r["effective_owners"]) for r in ordinary if len(r["effective_owners"])!=1][:20]

# Canonical owner row-field state and exact relation candidates.
owner_field_state=collections.Counter()
owner_counts=collections.Counter()
field_counts=collections.Counter()
page_counts=collections.Counter()
for r in ordinary:
    owner=r["effective_owners"][0]
    owner_counts[owner]+=1;field_counts[r["field"]]+=1;page_counts[r["page"]]+=1
    rows=[x for x in owner_rows.get(r["uid"],[]) if x["source"]==owner]
    vals=[]
    for x in rows:
        headers=x["headers"];values=x["values"]
        col={
          "action":hfind(headers,"action uid"),
          "gate":hfind(headers,"gate uid","gate"),
          "permission":hfind(headers,"permission","auth resource"),
          "operation":hfind(headers,"operation"),
          "runtime_owner":hfind(headers,"runtime owner"),
        }[r["field"]]
        if col is not None and col<len(values) and not missing(values[col]):
            vals.append(values[col])
    vals=sorted(set(vals))
    if len(vals)==0:state="CANONICAL_OWNER_ROW_FIELD_UNDEFINED"
    elif len(vals)==1:state="CANONICAL_OWNER_ROW_FIELD_DEFINED"
    else:state="CANONICAL_OWNER_ROW_FIELD_CONFLICT"
    r["owner_field_state"]=state
    r["owner_field_values"]=vals
    owner_field_state[state]+=1

# Exact relation policies; only deterministic equality and unanimous target values.
RELATIONS={
  "gate":[("operation",["Operation","Operation ID","operationId","API Operation","Service Operation"]),
          ("action",["Action UID","Action ID"])],
  "permission":[("operation",["Operation","Operation ID","operationId","API Operation","Service Operation"]),
                ("gate",["Gate","Gate UID"])],
  "operation":[("action",["Action UID","Action ID"])],
  "runtime_owner":[("operation",["Operation","Operation ID","operationId","API Operation","Service Operation"]),
                   ("gate",["Gate","Gate UID"])],
  "action":[("operation",["Operation","Operation ID","operationId","API Operation","Service Operation"])],
}
TARGET_HEADERS={
 "action":["Action UID","Action ID"],
 "gate":["Gate","Gate UID"],
 "permission":["Permission","Permission / Auth Resource","Auth Resource","Authorization Resource"],
 "operation":["Operation","Operation ID","operationId","API Operation","Service Operation"],
 "runtime_owner":["Runtime Owner","Runtime Service Owner","Service Owner"],
}
def cols_exact(headers,names):
    hs=[norm(h).lower() for h in headers]
    out=[]
    for i,h in enumerate(hs):
        if any(h==n.lower() for n in names):out.append(i)
    return out

relation_counts=collections.Counter()
relation_rows=[]
for q in ordinary:
    owner=q["effective_owners"][0]
    target=q["field"]
    candidates=collections.defaultdict(list)
    for anchor_field,anchor_headers in RELATIONS[target]:
        anchor=q.get(anchor_field,"")
        if missing(anchor):continue
        for row in generic[owner]:
            a_cols=cols_exact(row["headers"],anchor_headers)
            if not a_cols:continue
            if not any(i<len(row["values"]) and row["values"][i]==anchor for i in a_cols):continue
            t_cols=cols_exact(row["headers"],TARGET_HEADERS[target])
            for ti in t_cols:
                if ti>=len(row["values"]):continue
                val=row["values"][ti]
                if missing(val):continue
                candidates[val].append({"anchor_field":anchor_field,"anchor":anchor,"table":row["table"],"row":row["row"],"target_header":row["headers"][ti]})
    if len(candidates)==1:
        status="UNIQUE_EXACT_RELATION"
        value=next(iter(candidates))
        q["relation_status"]=status;q["relation_value"]=value;q["relation_evidence"]=candidates[value]
    elif len(candidates)>1:
        status="EXACT_RELATION_CONFLICT"
        q["relation_status"]=status;q["relation_values"]=dict(candidates)
    else:
        status="NO_EXACT_RELATION"
        q["relation_status"]=status
    relation_counts[status]+=1
    relation_rows.append(q)

payload={
 "denominator_total":249,
 "unique_owner_remediation":248,
 "preserved_sys_gate_conflict":1,
 "owner_counts":dict(owner_counts),
 "field_counts":dict(field_counts),
 "page_counts":dict(page_counts),
 "owner_field_state":dict(owner_field_state),
 "relation_counts":dict(relation_counts),
 "rows":relation_rows,
}
Path("__batch12_unique_owner_audit.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH12_AUDIT="+json.dumps({
 "denominator_total":249,
 "unique_owner_remediation":248,
 "preserved_sys_gate_conflict":1,
 "owner_counts":dict(owner_counts),
 "field_counts":dict(field_counts),
 "page_counts":dict(page_counts),
 "owner_field_state":dict(owner_field_state),
 "relation_counts":dict(relation_counts),
},ensure_ascii=False,sort_keys=True))
print("BATCH12_RELATION_BEGIN")
for r in relation_rows:
    if r["relation_status"]!="NO_EXACT_RELATION":
        print(json.dumps({
          "page":r["page"],"uid":r["uid"],"field":r["field"],
          "owner":r["effective_owners"][0],
          "owner_field_state":r["owner_field_state"],
          "relation_status":r["relation_status"],
          "relation_value":r.get("relation_value"),
          "relation_values":list(r.get("relation_values",{}).keys()),
          "relation_evidence":r.get("relation_evidence",[])
        },ensure_ascii=False,sort_keys=True))
print("BATCH12_RELATION_END")
