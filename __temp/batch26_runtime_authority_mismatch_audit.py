from pathlib import Path
from docx import Document
import json,re,collections,subprocess

BASE_HEAD="3efb960475948d7dff131fd0e83e5f0f7366b663"
S08="08_ACPOS_Strategy_Intelligence_MultiAI_Decision_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx"
S09="09_ACPOS_AI_System_Engineer_Self_Inspection_Evolution_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx"
STR="ACPOS_STR-01_WORKSPACE_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx"
IAM="ACPOS_IAM-01_帳戶與權限_Mother_Basic_Design_OPTIMIZED.docx"
FIELDS=["control","type","label","action","gate","permission","payload_schema","operation","method_path","runtime_owner","persistence_owner","runtime_status"]
TARGETS=[
("IAM-01",IAM,"IAM-01-BTN-AUDIT","method_path","getUiProjection",S09),
("STR-01",STR,"STR-01-TBL-COMPARE","method_path","compareCandidates",S08),
("STR-01",STR,"STR-01-TBL-COMPARE","payload_schema","compareCandidates",S08),
("STR-01",STR,"STR-01-TBL-COMPARE","persistence_owner","compareCandidates",S08),
("STR-01",STR,"STR-01-BTN-COMPARE","method_path","compareCandidates",S08),
("STR-01",STR,"STR-01-BTN-COMPARE","payload_schema","compareCandidates",S08),
("STR-01",STR,"STR-01-BTN-COMPARE","persistence_owner","compareCandidates",S08),
("STR-01",STR,"STR-01-BTN-ADOPT","method_path","adoptAsContextCandidate",S08),
("STR-01",STR,"STR-01-BTN-ADOPT","payload_schema","adoptAsContextCandidate",S08),
]

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
          "permission":hfind(h,"permission","auth resource"),"payload_schema":hfind(h,"payload / schema","payload","schema"),
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
        base["_field_values"]=fv;base["_rows"]=rs;out[uid]=base
    return out

assert len(list(Path(".").glob("*.docx")))==31
assert subprocess.check_output(["git","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""
maps={IAM:compose(parse_controls(IAM)),STR:compose(parse_controls(STR)),S08:compose(parse_controls(S08)),S09:compose(parse_controls(S09))}
rows=[]
for page,pfile,uid,field,op,owner in TARGETS:
    pr=maps[pfile][uid]
    assert pr["operation"]==op,(page,uid,pr["operation"],op)
    owner_rows=maps[owner].get(uid,{}).get("_rows",[])
    owner_status=sorted(set(r.get("runtime_status","") for r in owner_rows if not missing(r.get("runtime_status",""))))
    owner_op=sorted(set(r.get("operation","") for r in owner_rows if not missing(r.get("operation",""))))
    owner_gate=sorted(set(r.get("gate","") for r in owner_rows if not missing(r.get("gate",""))))
    owner_perm=sorted(set(r.get("permission","") for r in owner_rows if not missing(r.get("permission",""))))
    owner_target_field=sorted(set(r.get(field,"") for r in owner_rows if not missing(r.get(field,""))))
    sameop_rows=[r for r in parse_controls(owner) if r.get("operation")==op]
    sameop_status=sorted(set(r.get("runtime_status","") for r in sameop_rows if not missing(r.get("runtime_status",""))))
    sameop_values=sorted(set(r.get(field,"") for r in sameop_rows if not missing(r.get(field,""))))
    if len(owner_status)==1 and owner_status[0]!=pr.get("runtime_status",""):
        cls="EXACT_UID_RUNTIME_STATUS_DRIFT"
    elif len(owner_status)==1 and owner_status[0]==pr.get("runtime_status",""):
        if len(sameop_values)==1 and pr.get("runtime_status","") in sameop_status:
            cls="EXACT_UID_STATUS_MATCH_BUT_FIELD_SOURCE_MIXED"
        else:
            cls="EXACT_UID_STATUS_MATCH_FIELD_AUTHORITY_UNRESOLVED"
    elif len(owner_status)==0:
        cls="EXACT_UID_OWNER_STATUS_UNDEFINED"
    else:
        cls="EXACT_UID_OWNER_STATUS_CONFLICT"
    rows.append({
      "page":page,"uid":uid,"field":field,"operation":op,"canonical_owner":owner,
      "page_runtime_status":pr.get("runtime_status",""),"page_gate":pr.get("gate",""),"page_permission":pr.get("permission",""),
      "owner_runtime_status_values":owner_status,"owner_operation_values":owner_op,
      "owner_gate_values":owner_gate,"owner_permission_values":owner_perm,
      "owner_exact_uid_target_field_values":owner_target_field,
      "same_operation_runtime_status_values":sameop_status,"same_operation_target_field_values":sameop_values,
      "classification":cls,
    })
summary={
"target_cells":9,
"unique_controls":len(set(x["uid"] for x in rows)),
"exact_uid_runtime_status_drift":sum(1 for x in rows if x["classification"]=="EXACT_UID_RUNTIME_STATUS_DRIFT"),
"exact_uid_status_match_field_source_mixed":sum(1 for x in rows if x["classification"]=="EXACT_UID_STATUS_MATCH_BUT_FIELD_SOURCE_MIXED"),
"exact_uid_status_match_field_authority_unresolved":sum(1 for x in rows if x["classification"]=="EXACT_UID_STATUS_MATCH_FIELD_AUTHORITY_UNRESOLVED"),
"exact_uid_owner_status_undefined":sum(1 for x in rows if x["classification"]=="EXACT_UID_OWNER_STATUS_UNDEFINED"),
"exact_uid_owner_status_conflict":sum(1 for x in rows if x["classification"]=="EXACT_UID_OWNER_STATUS_CONFLICT"),
"by_control":{uid:dict(collections.Counter(x["classification"] for x in rows if x["uid"]==uid)) for uid in sorted(set(x["uid"] for x in rows))},
}
assert sum(summary[k] for k in [
"exact_uid_runtime_status_drift","exact_uid_status_match_field_source_mixed",
"exact_uid_status_match_field_authority_unresolved","exact_uid_owner_status_undefined","exact_uid_owner_status_conflict"])==9
report={"marker":"ACPOS-20260922-BATCH-26-RUNTIME-AUTHORITY-MISMATCH-AUDIT-V1","base_head":BASE_HEAD,"summary":summary,"rows":rows}
Path("__batch26_runtime_authority_mismatch_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch26_summary.txt").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("BATCH26_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
