from docx import Document
from pathlib import Path
import json,re,collections

WB="ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx"
S01="01_ACPOS_Global_Intelligent_Brain_Information_Lifecycle_Mother_Basic_Logic_Design_Normative_Contract_v4.docx"

def norm(x): return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v): return v in {"","—","-","SOURCE_NOT_DEFINED"}
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None

def parse(path):
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
            rec.update({"table":ti+1,"row":ri,"headers":h,"values":vals})
            out.append(rec)
    return out

wb=parse(WB);s01=parse(S01)
wb14=[]
for r in wb:
    if missing(r["action"]) and missing(r["gate"]) and r["permission"]=="workspace.dashboard.view" and r["operation"]=="getDashboardReadModel" and r["runtime_owner"]=="DASHBOARD_READ_MODEL":
        wb14.append(r)
assert len(wb14)==14,len(wb14)

canon=[r for r in s01 if r["permission"]=="workspace.dashboard.view" and r["operation"]=="getDashboardReadModel" and r["runtime_owner"]=="DASHBOARD_READ_MODEL"]
# dedupe exact control IDs while keeping richest row
cg=collections.defaultdict(list)
for r in canon:cg[r["control"]].append(r)
canon_best={}
for uid,rs in cg.items():
    canon_best[uid]=max(rs,key=lambda x:sum(not missing(x.get(k,"")) for k in ["action","gate","permission","operation","runtime_owner","runtime_status"]))
assert len(canon_best)>=14,len(canon_best)

maps=[]
for w in sorted(wb14,key=lambda x:x["control"]):
    compact=w["control"]
    if "…" in compact:
        suffix=compact.split("…",1)[1]
    elif "..." in compact:
        suffix=compact.split("...",1)[1]
    else:
        suffix=compact
    matches=[]
    for uid,r in canon_best.items():
        # Exact anchor triple + exact suffix only. No label or fuzzy similarity.
        if uid.endswith(suffix):
            matches.append(r)
    maps.append({
      "compact_uid":compact,"suffix":suffix,
      "matches":[{
         "canonical_uid":m["control"],"type":m["type"],"label":m["label"],
         "action":m["action"],"gate":m["gate"],"permission":m["permission"],
         "operation":m["operation"],"runtime_owner":m["runtime_owner"],"runtime_status":m["runtime_status"],
         "table":m["table"],"row":m["row"],"headers":m["headers"],"values":m["values"]
      } for m in matches]
    })

assert all(len(x["matches"])==1 for x in maps),[(x["compact_uid"],len(x["matches"])) for x in maps]
full=[x["matches"][0]["canonical_uid"] for x in maps]
assert len(set(full))==14,full

summary={
  "compact_controls":14,
  "unique_canonical_mappings":14,
  "canonical_owner":S01,
  "action_values":dict(collections.Counter(x["matches"][0]["action"] for x in maps)),
  "gate_values":dict(collections.Counter(x["matches"][0]["gate"] for x in maps)),
  "action_missing_count":sum(1 for x in maps if missing(x["matches"][0]["action"])),
  "gate_missing_count":sum(1 for x in maps if missing(x["matches"][0]["gate"])),
  "canonical_tables":dict(collections.Counter(str(x["matches"][0]["table"]) for x in maps)),
}
Path("__batch11_wb_mapping_validation.json").write_text(json.dumps({"summary":summary,"mappings":maps},ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH11_MAPPING="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
print("BATCH11_MAPPINGS_BEGIN")
for x in maps: print(json.dumps(x,ensure_ascii=False,sort_keys=True))
print("BATCH11_MAPPINGS_END")
