from pathlib import Path
from docx import Document
import json,re,collections,subprocess

BASE_HEAD="7c16720b138ffcca9563d703e8e74879f2eb59d3"
DOCS=sorted(Path(".").glob("*.docx"))
assert len(DOCS)==31
assert subprocess.check_output(["git","-c","core.quotePath=false","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

LEGACY_RE=re.compile(r"(?<![A-Za-z0-9])R(?:9(?:\.0\.1)?|5)(?![A-Za-z0-9])",re.I)
AMBIG_LOCATOR_RE=re.compile(r"\bt\d+/r(?:5|9)\b",re.I)

def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v):return v in {"","—","-","SOURCE_NOT_DEFINED","UNCHANGED"}
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None

active_rows=[]
reference_rows=[]
all_text=[]
for p in DOCS:
    d=Document(p)
    all_text.extend(norm(x.text) for x in d.paragraphs if norm(x.text))
    for ti,t in enumerate(d.tables,1):
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells]
        ci=hfind(h,"control uid")
        ai=hfind(h,"action uid")
        oi=hfind(h,"operation")
        mi=hfind(h,"method / path","method","path")
        si=hfind(h,"runtime status")
        ui=hfind(h,"uid status")
        if ci is None: 
            for row in t.rows:
                all_text.append(" | ".join(norm(c.text) for c in row.cells))
            continue
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells]
            all_text.append(" | ".join(vals))
            uid=vals[ci] if ci<len(vals) else ""
            if not uid or uid in {"—","-"}:continue
            rec={
              "file":p.name,"table":ti,"row":ri,"uid":uid,
              "action":vals[ai] if ai is not None and ai<len(vals) else "",
              "operation":vals[oi] if oi is not None and oi<len(vals) else "",
              "method":vals[mi] if mi is not None and mi<len(vals) else "",
              "runtime_status":vals[si] if si is not None and si<len(vals) else "",
              "uid_status":vals[ui] if ui is not None and ui<len(vals) else "",
              "headers":h,"values":vals
            }
            if rec["runtime_status"] in {"EFFECTFUL_EXACT","READ_EXACT"}:
                active_rows.append(rec)
            else:
                reference_rows.append(rec)

legacy=[];locators=[]
joined="\n".join(all_text)
for m in LEGACY_RE.finditer(joined):legacy.append({"match":m.group(0),"context":joined[max(0,m.start()-120):m.end()+180]})
for m in AMBIG_LOCATOR_RE.finditer(joined):locators.append({"match":m.group(0),"context":joined[max(0,m.start()-120):m.end()+180]})

# active exact rows only
action_map=collections.defaultdict(list)
route_map=collections.defaultdict(list)
operation_map=collections.defaultdict(list)
for r in active_rows:
    if not missing(r["action"]) and not missing(r["operation"]):action_map[r["action"]].append(r)
    if not missing(r["method"]) and r["method"] not in {"LOCAL LOCAL","NO_PUBLIC_API_BY_AUTHORITY","NO_PUBLIC_API_ID_IN_CURRENT_AUTHORITY"} and not missing(r["operation"]):
        route_map[r["method"]].append(r)
    if not missing(r["operation"]):operation_map[r["operation"]].append(r)

active_action_conflicts={}
for act,rows in action_map.items():
    ops=sorted(set(r["operation"] for r in rows))
    if len(ops)>1:active_action_conflicts[act]={"operations":ops,"rows":rows}

active_route_conflicts={}
for route,rows in route_map.items():
    ops=sorted(set(r["operation"] for r in rows))
    if len(ops)>1:active_route_conflicts[route]={"operations":ops,"rows":rows}

# operation -> routes/action multiplicity can be legitimate across pages but report exact contexts.
operation_route_multi={}
operation_action_multi={}
for op,rows in operation_map.items():
    routes=sorted(set(r["method"] for r in rows if not missing(r["method"]) and r["method"] not in {"LOCAL LOCAL","NO_PUBLIC_API_BY_AUTHORITY","NO_PUBLIC_API_ID_IN_CURRENT_AUTHORITY"}))
    actions=sorted(set(r["action"] for r in rows if not missing(r["action"])))
    if len(routes)>1:operation_route_multi[op]={"routes":routes,"rows":rows}
    if len(actions)>1:operation_action_multi[op]={"actions":actions,"rows":rows}

# inspect the four Batch60 candidates in both active and nonactive contexts
candidates=["SYS-01-ACT-CONVERSATION-ATTACH","CORE-01-ACT-CANDIDATE-CREATE","STR-01-ACT-NOOP"]
candidate_context={}
for act in candidates:
    candidate_context[act]={
      "active":[r for r in active_rows if r["action"]==act],
      "nonactive":[r for r in reference_rows if r["action"]==act],
    }

local_local=[r for r in active_rows if r["method"]=="LOCAL LOCAL"]

# target edit orchestration recheck
edit_target=[r for r in active_rows if r["uid"]=="EDIT-01-BTN-FLOW-START"]
assert len(edit_target)==2,edit_target
assert set(r["operation"] for r in edit_target)=={"dispatchEditingFlowStartContinue"},edit_target

summary={
 "docx_files":31,
 "legacy_r9_r5_hits":len(legacy),
 "ambiguous_locator_hits":len(locators),
 "active_exact_rows":len(active_rows),
 "active_action_operation_conflicts":len(active_action_conflicts),
 "active_route_operation_conflicts":len(active_route_conflicts),
 "operation_multi_route_groups":len(operation_route_multi),
 "operation_multi_action_groups":len(operation_action_multi),
 "local_local_active_rows":len(local_local),
 "edit_target_rows":len(edit_target),
}
report={
 "marker":"ACPOS-20260922-BATCH-64-GLOBAL-ACTION-ROUTE-BIDIRECTIONAL-CLASSIFICATION-AUDIT-V1",
 "base_head":BASE_HEAD,"summary":summary,
 "legacy_hits":legacy,"ambiguous_locator_hits":locators,
 "active_action_conflicts":active_action_conflicts,
 "active_route_conflicts":active_route_conflicts,
 "operation_route_multi":operation_route_multi,
 "operation_action_multi":operation_action_multi,
 "candidate_context":candidate_context,
 "local_local_active_rows":local_local,
 "edit_target_rows":edit_target,
}
Path("__batch64_global_bidirectional_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch64_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH64_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
