from pathlib import Path
from docx import Document
import json,re,collections,hashlib,subprocess

BASE_HEAD="fda43701a3ff71c2eef918beeb115c41aee4c6cc"
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
LOGIC="ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx"
PAGES={
"DEV-01":"ACPOS_DEV-01_企業自動開發系統_Mother_Basic_Design_OPTIMIZED.docx",
"EDIT-01":"ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"KB-01":"ACPOS_KB-01_知識庫_Mother_Basic_Design_OPTIMIZED.docx",
"SYS-01":"ACPOS_SYS-01_系統維護與生命週期工作區_Mother_Basic_Design_OPTIMIZED.docx",
}
TARGETS=[
("DEV-01","DEV-01-BTN-STAGE-1","permission"),
("DEV-01","DEV-01-BTN-STAGE-2","permission"),
("DEV-01","DEV-01-BTN-STAGE-3","permission"),
("DEV-01","DEV-01-BTN-STAGE-4","permission"),
("DEV-01","DEV-01-BTN-STAGE-5","permission"),
("EDIT-01","EDIT-01-PNL-API-CANDIDATE","action"),
("EDIT-01","EDIT-01-PNL-FINAL-PREVIEW","action"),
("KB-01","KB-01-CTL-VIEW-EXPERIENCE","action"),
("KB-01","KB-01-CTL-VIEW-EXPERIENCE","gate"),
("KB-01","KB-01-CTL-VIEW-OVERVIEW","action"),
("KB-01","KB-01-CTL-VIEW-OVERVIEW","gate"),
("KB-01","KB-01-CTL-VIEW-REVIEW","action"),
("KB-01","KB-01-CTL-VIEW-REVIEW","gate"),
("KB-01","KB-01-CTL-VIEW-SEARCH","action"),
("KB-01","KB-01-CTL-VIEW-SEARCH","gate"),
("KB-01","KB-01-CTL-VIEW-SOURCE","action"),
("KB-01","KB-01-CTL-VIEW-SOURCE","gate"),
("SYS-01","SYS-01-BTN-CR-CREATE","gate"),
("SYS-01","SYS-01-BTN-NAV-OPEN","gate"),
("SYS-01","SYS-01-BTN-SANDBOX-TEST","gate"),
]
FIELDS=["control","type","label","action","gate","permission","payload_schema","operation","method_path","runtime_owner","persistence_owner","runtime_status"]

def norm(x): return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v): return v in {"","—","-","SOURCE_NOT_DEFINED"}
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
        idx={
          "control":ci,"type":hfind(h,"type"),"label":hfind(h,"label","顯示名稱"),
          "action":hfind(h,"action uid"),"gate":hfind(h,"gate uid","gate"),
          "permission":hfind(h,"permission","auth resource"),
          "payload_schema":hfind(h,"payload / schema","payload","schema"),
          "operation":hfind(h,"operation"),"method_path":hfind(h,"method / path","method","path"),
          "runtime_owner":hfind(h,"runtime owner"),"persistence_owner":hfind(h,"persistence owner"),
          "runtime_status":hfind(h,"runtime status"),
        }
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells];uid=vals[ci] if ci<len(vals) else ""
            if not uid or uid in {"—","-"}:continue
            rec={k:(vals[i] if i is not None and i<len(vals) else "") for k,i in idx.items()}
            rec.update({"file":path,"table":ti+1,"row":ri,"headers":h})
            out.append(rec)
    return out
def compose(rows):
    g=collections.defaultdict(list)
    for r in rows:g[r["control"]].append(r)
    out={}
    for uid,rs in g.items():
        base=max(rs,key=lambda r:sum(not missing(r.get(f,"")) for f in FIELDS[1:])).copy()
        conflicts={}
        for f in FIELDS[1:]:
            vals=sorted(set(r.get(f,"") for r in rs if not missing(r.get(f,""))))
            if missing(base.get(f,"")) and len(vals)==1:base[f]=vals[0]
            if len(vals)>1:conflicts[f]=vals
        base["occurrence_count"]=len(rs);base["conflicts"]=conflicts
        out[uid]=base
    return out

root_docx=sorted(p.name for p in Path(".").glob("*.docx"))
assert len(root_docx)==31,len(root_docx)
assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()!=BASE_HEAD, "audit harness commit expected above content base"
assert subprocess.check_output(["git","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

all_rows={}
all_maps={}
for fn in root_docx:
    rows=parse_controls(fn);all_rows[fn]=rows;all_maps[fn]=compose(rows)

def same_relation_candidates(target,field,rows):
    # Require exact agreement on all available stable execution dimensions except the missing field.
    stable=["type","action","gate","permission","payload_schema","operation","method_path","runtime_owner","runtime_status"]
    keys=[k for k in stable if k!=field and not missing(target.get(k,""))]
    scored=[]
    for r in rows:
        v=r.get(field,"")
        if missing(v):continue
        exact=[k for k in keys if r.get(k,"")==target.get(k,"")]
        mismatch=[k for k in keys if not missing(r.get(k,"")) and r.get(k,"")!=target.get(k,"")]
        # Exact-relation candidate requires no contradiction and at least 3 stable equal keys,
        # or exact Operation+RuntimeStatus plus one authorization/owner dimension.
        qualifies=(not mismatch and len(exact)>=3) or (
            not mismatch and "operation" in exact and "runtime_status" in exact and
            any(k in exact for k in ["permission","gate","runtime_owner","payload_schema"])
        )
        if qualifies:
            scored.append({"value":v,"uid":r["control"],"file":r["file"],"exact_keys":exact,"table":r["table"],"row":r["row"]})
    return scored

report={"base_head":BASE_HEAD,"target_count":len(TARGETS),"targets":[]}
for page,uid,field in TARGETS:
    pfile=PAGES[page];target=all_maps[pfile][uid]
    assert missing(target.get(field,"")),(page,uid,field,target.get(field))
    occurrences=[]
    for fn,m in all_maps.items():
        if uid in m:
            x=m[uid].copy();x["file"]=fn;occurrences.append(x)
    candidates=[]
    for fn in SYSTEM_DOCS+[LOGIC,pfile]:
        candidates.extend(same_relation_candidates(target,field,all_rows[fn]))
    vals=collections.Counter(c["value"] for c in candidates)
    # Textual owner presence: documents containing exact UID anywhere, beyond control tables.
    text_presence=[]
    for fn in SYSTEM_DOCS+[LOGIC]:
        d=Document(fn)
        txt="\n".join([p.text for p in d.paragraphs]+[c.text for t in d.tables for row in t.rows for c in row.cells])
        if uid in txt:text_presence.append(fn)
    report["targets"].append({
      "page":page,"uid":uid,"field":field,
      "current":{k:target.get(k,"") for k in FIELDS[1:]},
      "current_conflicts":target.get("conflicts",{}),
      "occurrences":occurrences,
      "candidate_values":dict(vals),
      "candidates":candidates,
      "system_text_presence":text_presence,
    })

# Global summaries.
report["summary"]={
 "by_field":dict(collections.Counter(f for _,_,f in TARGETS)),
 "by_page":dict(collections.Counter(p for p,_,_ in TARGETS)),
 "unique_candidate":sum(1 for t in report["targets"] if len(t["candidate_values"])==1),
 "candidate_conflict":sum(1 for t in report["targets"] if len(t["candidate_values"])>1),
 "no_candidate":sum(1 for t in report["targets"] if len(t["candidate_values"])==0),
}
Path("__batch17_remaining20_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

# Human-readable ledger
lines=[]
for t in report["targets"]:
    lines.append(f'{t["page"]}\t{t["uid"]}\t{t["field"]}\tstatus={t["current"].get("runtime_status")}\top={t["current"].get("operation")}\towner={t["current"].get("runtime_owner")}\taction={t["current"].get("action")}\tgate={t["current"].get("gate")}\tperm={t["current"].get("permission")}\tcandidates={json.dumps(t["candidate_values"],ensure_ascii=False)}\tpresence={";".join(t["system_text_presence"])}')
Path("__batch17_remaining20_audit.tsv").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("BATCH17_AUDIT_SUMMARY="+json.dumps(report["summary"],ensure_ascii=False,sort_keys=True))
