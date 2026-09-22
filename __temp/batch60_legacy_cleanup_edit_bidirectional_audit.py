from pathlib import Path
from docx import Document
import json,re,collections,subprocess

MARK="ACPOS-20260922-BATCH-60-LEGACY-CLEANUP-EDIT-BIDIRECTIONAL-AUDIT-V1"
BASE_HEAD="883594dc703d1e3f97c2f5510ff801a0e1c2e512"
DOCS=sorted(Path(".").glob("*.docx"))
assert len(DOCS)==31
assert subprocess.check_output(["git","-c","core.quotePath=false","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

EDIT="ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx"
S05="05_ACPOS_Creative_Production_AI_ASSET_VIDEO_EDIT_VOICE_QA_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx"
TARGET_UID="EDIT-01-BTN-FLOW-START"
ACTION_UID="EDIT-01-ACT-FLOW-START-CONTINUE"
GATE_UID="EDIT-01-GATE-CONTEXT-INTEGRITY"
PORTS=["EDIT-01-PORT-EDIT-RUN-CREATE","EDIT-01-PORT-ASSEMBLY-COMPLETE"]
OPS=["createEditingRuntimeRun","completeAssembly"]
ROUTES=["POST /v1/editing-runtime-runs","POST /v1/editing-runtime-runs/{runId}/assembly"]
SCHEMAS=["CreateEditingRuntimeRunRequest","CompleteEditingAssemblyRequest"]
PERMS=["EDITING_USE","editing.task.execute"]
PERSIST=["acpos_runtime.editing_runtime_runs_runtime","acpos_runtime.editing_runtime_steps_runtime","public.editing_timelines"]
TOKENS=[TARGET_UID,ACTION_UID,GATE_UID,*PORTS,*OPS,*ROUTES,*SCHEMAS,*PERMS,*PERSIST,
        "editing runtime","assembly","input fingerprint","source versions","runId","START","CONTINUE","READY","RUNNING","ASSEMBLY","COMPLETE"]

def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def hfind(h,*ns):
    hs=[norm(x).lower() for x in h]
    for n in ns:
        for i,x in enumerate(hs):
            if n.lower() in x:return i
    return None
def missing(v):return v in {"","—","-","SOURCE_NOT_DEFINED","UNCHANGED"}

legacy=[]
locator=[]
edit_hits=[]
exact_rows=[]
compound_rows=[]
action_map=collections.defaultdict(set)
route_map=collections.defaultdict(set)
permission_context=[]
port_rows=[]

rx=re.compile("|".join(re.escape(x) for x in sorted(set(TOKENS),key=len,reverse=True)),re.I)
legacy_rx=re.compile(r"(?<![A-Za-z0-9])R\\s*(?:9(?:\\.0\\.1)?|5)(?![A-Za-z0-9])",re.I)
locator_rx=re.compile(r"\\bt\\d+/r\\d+\\b",re.I)

for path in DOCS:
    d=Document(path)
    for pi,p in enumerate(d.paragraphs):
        t=norm(p.text)
        if not t:continue
        if legacy_rx.search(t):legacy.append({"file":path.name,"kind":"paragraph","index":pi,"text":t})
        if locator_rx.search(t):locator.append({"file":path.name,"kind":"paragraph","index":pi,"text":t,"matches":locator_rx.findall(t)})
        if rx.search(t):edit_hits.append({"file":path.name,"kind":"paragraph","index":pi,"text":t[:6000]})
    for ti,t in enumerate(d.tables,1):
        if not t.rows:continue
        headers=[norm(c.text) for c in t.rows[0].cells]
        ci=hfind(headers,"control uid");ai=hfind(headers,"action uid");oi=hfind(headers,"operation")
        mi=hfind(headers,"method / path","method","path");pii=hfind(headers,"payload / schema","payload","schema")
        ri=hfind(headers,"runtime status");perm_i=hfind(headers,"permission","auth resource")
        port_i=hfind(headers,"port uid")
        for rno,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells];joined=" | ".join(vals)
            if legacy_rx.search(joined):legacy.append({"file":path.name,"kind":"table_row","table":ti,"row":rno,"headers":headers,"values":vals,"matches":legacy_rx.findall(joined)})
            if locator_rx.search(joined):locator.append({"file":path.name,"kind":"table_row","table":ti,"row":rno,"headers":headers,"values":vals,"matches":locator_rx.findall(joined)})
            if rx.search(joined):edit_hits.append({"file":path.name,"kind":"table_row","table":ti,"row":rno,"headers":headers,"values":vals})
            if port_i is not None and port_i<len(vals) and vals[port_i] in PORTS:
                port_rows.append({"file":path.name,"table":ti,"row":rno,"headers":headers,"values":vals})
            if ci is not None and ci<len(vals) and vals[ci] not in {"","—","-"}:
                uid=vals[ci];st=vals[ri] if ri is not None and ri<len(vals) else ""
                op=vals[oi] if oi is not None and oi<len(vals) else ""
                act=vals[ai] if ai is not None and ai<len(vals) else ""
                mp=vals[mi] if mi is not None and mi<len(vals) else ""
                ps=vals[pii] if pii is not None and pii<len(vals) else ""
                perm=vals[perm_i] if perm_i is not None and perm_i<len(vals) else ""
                if st in {"EFFECTFUL_EXACT","READ_EXACT"}:
                    exact_rows.append({"file":path.name,"table":ti,"row":rno,"uid":uid,"runtime_status":st,"action":act,"operation":op,"method_path":mp,"payload_schema":ps,"permission":perm,"headers":headers,"values":vals})
                    if act and not missing(act) and op and not missing(op):action_map[act].add(op)
                    if mp and not missing(mp) and op and not missing(op):
                        for one in [x.strip() for x in mp.split(" | ") if x.strip()]:route_map[one].add(op)
                    comp=[]
                    if " | " in op:comp.append("operation")
                    if " | " in mp:comp.append("method_path")
                    if " | " in ps:comp.append("payload_schema")
                    if comp:compound_rows.append({"file":path.name,"table":ti,"row":rno,"uid":uid,"runtime_status":st,"compound_fields":comp,"action":act,"operation":op,"method_path":mp,"payload_schema":ps,"permission":perm})
            if any(p in joined for p in PERMS):
                permission_context.append({"file":path.name,"table":ti,"row":rno,"headers":headers,"values":vals})

# Exact target rows and page-owner comparison.
target_exact=[x for x in exact_rows if x["uid"]==TARGET_UID]
page_target=[x for x in target_exact if x["file"]==EDIT]
owner_target=[x for x in target_exact if x["file"]==S05]

# Reverse references per identifier.
reverse={}
for token in [TARGET_UID,ACTION_UID,GATE_UID,*PORTS,*OPS,*ROUTES,*SCHEMAS,*PERMS,*PERSIST]:
    rr=[]
    for h in edit_hits:
        txt=h.get("text") or " | ".join(h.get("values",[]))
        if token in txt:rr.append(h)
    reverse[token]=rr

# Look for lifecycle/state vocabulary tied to the same editing runtime domain.
state_evidence=[]
state_rx=re.compile(r"(editing|assembly|runtime|timeline).*(state|status)|(?:state|status).*(editing|assembly|runtime|timeline)|READY|RUNNING|ASSEMBLY|COMPLET|BLOCK|FAIL|PENDING",re.I)
for h in edit_hits:
    txt=h.get("text") or " | ".join(h.get("values",[]))
    if state_rx.search(txt):state_evidence.append(h)

# Unique action mapping conflicts across all exact controls.
action_conflicts={k:sorted(v) for k,v in action_map.items() if len(v)>1}
route_conflicts={k:sorted(v) for k,v in route_map.items() if len(v)>1}

# Port consumer checks: operation/route/schema from each port must be referenced in target or orchestration text.
port_contracts={}
for pr in port_rows:
    vals=pr["values"];h=pr["headers"]
    def at(*needles):
        i=hfind(h,*needles);return vals[i] if i is not None and i<len(vals) else ""
    pu=at("port uid")
    port_contracts[pu]={"file":pr["file"],"table":pr["table"],"row":pr["row"],"boundary":at("boundary","stage"),"operation":at("operation"),"method_path":at("method","path"),"permission":at("permission"),"values":vals}

target_text=" ".join(" | ".join(x["values"]) for x in target_exact)
port_reverse_status={}
for pu,pv in port_contracts.items():
    port_reverse_status[pu]={
      "operation_present_in_target":pv["operation"] in target_text,
      "method_present_in_target":pv["method_path"] in target_text,
      "permission_present_in_target":pv["permission"] in target_text,
      "reverse_reference_count":len(reverse.get(pu,[])),
    }

summary={
 "legacy_r9_r5_hits":len(legacy),
 "table_row_locator_hits":len(locator),
 "target_exact_rows":len(target_exact),
 "page_target_rows":len(page_target),
 "owner_target_rows":len(owner_target),
 "port_contract_count":len(port_contracts),
 "compound_exact_rows_total":len(compound_rows),
 "compound_target_rows":sum(x["uid"]==TARGET_UID for x in compound_rows),
 "other_compound_exact_rows":sum(x["uid"]!=TARGET_UID for x in compound_rows),
 "action_operation_conflicts":len(action_conflicts),
 "route_operation_conflicts":len(route_conflicts),
 "permission_context_rows":len(permission_context),
 "state_evidence_hits":len(state_evidence),
}
report={
 "marker":MARK,"base_head":BASE_HEAD,"summary":summary,
 "legacy_r9_r5_hits":legacy,"table_row_locator_hits":locator,
 "target_exact_rows":target_exact,"port_contracts":port_contracts,"port_reverse_status":port_reverse_status,
 "reverse_references":{k:len(v) for k,v in reverse.items()},
 "reverse_reference_evidence":reverse,
 "permission_context":permission_context,
 "state_evidence":state_evidence,
 "compound_exact_rows":compound_rows,
 "action_operation_conflicts":action_conflicts,
 "route_operation_conflicts":route_conflicts,
}
Path("__batch60_bidirectional_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
Path("__batch60_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH60_SUMMARY="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
