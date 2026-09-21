from pathlib import Path
from docx import Document
import json,re,collections,subprocess

BASE_HEAD="4d07d19c74d6f1f74a4ed2889aeef73f5003fec2"
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
FIELDS=["control","operation","method_path","payload_schema","persistence_owner","runtime_owner","runtime_status","gate","permission"]
SENTINELS={"","—","-","SOURCE_NOT_DEFINED","NO_PUBLIC_API_BY_AUTHORITY","LOCAL LOCAL"}

def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None
def parse_rows(path):
    d=Document(path);out=[]
    for ti,t in enumerate(d.tables):
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells]
        oi=hfind(h,"operation")
        if oi is None:continue
        idx={
          "control":hfind(h,"control uid"),
          "operation":oi,
          "method_path":hfind(h,"method / path","method","path","route","endpoint"),
          "payload_schema":hfind(h,"payload / schema","payload","schema","request"),
          "persistence_owner":hfind(h,"persistence owner"),
          "runtime_owner":hfind(h,"runtime owner"),
          "runtime_status":hfind(h,"runtime status"),
          "gate":hfind(h,"gate uid","gate"),
          "permission":hfind(h,"permission","auth resource"),
        }
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells]
            if oi>=len(vals):continue
            op=vals[oi]
            if not op or op in {"—","-"}:continue
            rec={k:(vals[i] if i is not None and i<len(vals) else "") for k,i in idx.items()}
            rec.update({"file":path,"table":ti+1,"row":ri,"headers":h});out.append(rec)
    return out

assert len(list(Path(".").glob("*.docx")))==31
assert subprocess.check_output(["git","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

owners={}
for sf in SYSTEM_DOCS:
    rows=parse_rows(sf)
    routes=[];payloads=[];persist=[];statuses=[];verbs=collections.Counter();prefixes=collections.Counter();schema_shapes=collections.Counter()
    for r in rows:
        mp=r["method_path"]
        if mp and mp not in SENTINELS:
            routes.append({k:r[k] for k in FIELDS if k in r})
            m=re.match(r"^([A-Z]+)\s+(/\S+)$",mp)
            if m:
                verbs[m.group(1)]+=1
                path=m.group(2)
                seg=[x for x in path.split("/") if x]
                prefix="/" + "/".join(seg[:2]) if len(seg)>=2 else path
                prefixes[prefix]+=1
        ps=r["payload_schema"]
        if ps and ps not in SENTINELS:
            payloads.append({k:r[k] for k in FIELDS if k in r})
            if ps.endswith("Request"):schema_shapes["*Request"]+=1
            elif ps.endswith("Command"):schema_shapes["*Command"]+=1
            elif "No-form read contract" in ps:schema_shapes["No-form read contract"]+=1
            elif "Field Contract" in ps:schema_shapes["*Field Contract"]+=1
            else:schema_shapes["Other"]+=1
        po=r["persistence_owner"]
        if po and po not in SENTINELS:
            persist.append({k:r[k] for k in FIELDS if k in r})
        st=r["runtime_status"]
        if st and st not in SENTINELS:statuses.append(st)
    owners[sf]={
      "rows_with_operation":len(rows),
      "route_rows":len(routes),"payload_rows":len(payloads),"persistence_rows":len(persist),
      "verbs":dict(verbs),"route_prefixes":dict(prefixes.most_common()),
      "payload_shapes":dict(schema_shapes),
      "persistence_values":dict(collections.Counter(x["persistence_owner"] for x in persist)),
      "runtime_status_values":dict(collections.Counter(statuses)),
      "route_examples":routes[:80],
      "payload_examples":payloads[:80],
      "persistence_examples":persist[:80],
    }

summary={
"owners":len(SYSTEM_DOCS),
"owners_with_routes":sum(1 for v in owners.values() if v["route_rows"]>0),
"owners_with_payloads":sum(1 for v in owners.values() if v["payload_rows"]>0),
"owners_with_persistence":sum(1 for v in owners.values() if v["persistence_rows"]>0),
"total_route_rows":sum(v["route_rows"] for v in owners.values()),
"total_payload_rows":sum(v["payload_rows"] for v in owners.values()),
"total_persistence_rows":sum(v["persistence_rows"] for v in owners.values()),
}
report={"marker":"ACPOS-20260922-BATCH-34-OWNER-CONTRACT-VOCABULARY-AUDIT-V1","base_head":BASE_HEAD,"summary":summary,"owners":owners}
Path("__batch34_owner_contract_vocabulary_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch34_summary.txt").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("BATCH34_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
