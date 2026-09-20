from pathlib import Path
import subprocess, yaml, json, re, hashlib

SOURCE_SHA="165c6440cb53b1b45ec96905241fb4d56dc3b867"
PAGES={
"WB-01":"authority/pages/workspace/WB-01/ACPOS_WB-01_FINAL_LOCKED_ENCODING.yaml",
"CORE-01":"authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml",
"ASSET-01":"authority/pages/workspace/ASSET-01/ASSET_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
"VIDEO-01":"authority/pages/workspace/VIDEO-01/VIDEO_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
"EDIT-01":"authority/pages/workspace/EDIT-01/ACPOS_EDIT-01_FINAL_LOCKED_ENCODING_SCRIPT_CONTENT_CLOSED_V1.1.yaml",
"QA-01":"authority/pages/workspace/QA-01/ACPOS_QA-01_FINAL_LOCKED_ENCODING_DEDUP_CLEAN.yaml",
"DB-01":"authority/pages/admin/DB-01/ACPOS_DB-01_FINAL_LOCKED_ENCODING.yaml",
"STR-01":"authority/pages/workspace/STR-01/ACPOS_STR-01_FINAL_LOCKED_ENCODING_PROVIDER_BOUND.yaml",
"INFO-01":"authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml",
"SYS-01":"authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml",
"IAM-01":"authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
"DEV-01":"authority/pages/admin/DEV-01/ACPOS_DEV-01_ENTERPRISE_AUTOMATION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
"SOC-01":"authority/pages/admin/SOC-01/ACPOS_SOC-01_SOCIAL_PUBLISHING_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
"ERP-01":"authority/pages/admin/ERP-01/ACPOS_ERP-01_ERP_FINANCE_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
"AIAPI-01":"authority/pages/admin/AIAPI-01/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml",
"SG-02":"authority/pages/admin/SG-02/ACPOS_SG-02_QA_REVIEW_STANDARD_FINAL_LOCKED_ENCODING.yaml",
"ADMIN-STR-01":"authority/pages/admin/STR-01/ACPOS_STRATEGY_CENTER_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml",
"KB-01":"authority/pages/admin/KB-01/ACPOS_KB-01_FINAL_LOCKED_ENCODING.yaml",
}

def show(path):
    return subprocess.check_output(["git","show",f"{SOURCE_SHA}:{path}"],text=True)

def walk(x,path=()):
    if isinstance(x,dict):
        yield path,x
        for k,v in x.items():
            yield from walk(v,path+(str(k),))
    elif isinstance(x,list):
        for i,v in enumerate(x):
            yield from walk(v,path+(str(i),))

def val(d,*keys):
    for k in keys:
        if k in d and d[k] not in (None,""):
            return d[k]
    return None

def flatten_runtime(v):
    if v is None: return ""
    if isinstance(v,(str,int,float,bool)): return str(v)
    if isinstance(v,dict):
        parts=[]
        for k,x in v.items():
            if isinstance(x,(str,int,float,bool)):
                parts.append(f"{k}={x}")
        return "; ".join(parts)
    if isinstance(v,list):
        return "; ".join(str(x) for x in v if isinstance(x,(str,int,float,bool)))
    return str(v)

report={"source_sha":SOURCE_SHA,"pages":{}}
for page,path in PAGES.items():
    raw=show(path)
    data=yaml.safe_load(raw)
    controls={};actions={};ports={};gates={};perms={};runtime_records=[];claims=[]
    allnodes=list(walk(data))
    for p,d in allnodes:
        ps="/".join(p).lower()
        # denominator / status claims
        for k,v in d.items():
            kl=str(k).lower()
            if any(t in kl for t in ["count","coverage","unbound","unresolved","status"]) and isinstance(v,(str,int,float,bool)):
                if any(t in ps+kl for t in ["control","action","port","runtime","binding","gap","validation","final"]):
                    claims.append({"path":"/".join(p+(str(k),)),"value":v})
        cu=val(d,"control_uid")
        if cu:
            controls[str(cu)]={**controls.get(str(cu),{}),**d,"__path":"/".join(p)}
        au=val(d,"action_uid")
        if au:
            actions[str(au)]={**actions.get(str(au),{}),**d,"__path":"/".join(p)}
        pu=val(d,"port_uid","integration_port_uid")
        if pu:
            ports[str(pu)]={**ports.get(str(pu),{}),**d,"__path":"/".join(p)}
        gu=val(d,"gate_uid")
        if gu:
            gates[str(gu)]={**gates.get(str(gu),{}),**d,"__path":"/".join(p)}
        pm=val(d,"permission_uid")
        if pm:
            perms[str(pm)]={**perms.get(str(pm),{}),**d,"__path":"/".join(p)}
        if any(k in d for k in ["runtime_binding","method_effective_path","method_path","method / path","api_path"]):
            runtime_records.append({"path":"/".join(p),"data":d})
    # additional binding records may contain control/action refs
    bindings=[]
    for p,d in allnodes:
        cu=val(d,"control_uid","control")
        au=val(d,"action_uid","action")
        if cu and au:
            bindings.append({"control_uid":str(cu),"action_uid":str(au),"data":d,"path":"/".join(p)})
    # build operation index from any node
    op_index={}
    for p,d in allnodes:
        op=val(d,"registered_operation","operation","operation_uid")
        method=val(d,"method_effective_path","method_path","method / path","method","route","api_path","endpoint")
        if op:
            rec=op_index.setdefault(str(op),{"methods":[],"records":[]})
            if method and str(method) not in rec["methods"]: rec["methods"].append(str(method))
            rec["records"].append({"path":"/".join(p),"data":d})
    # control closure
    rows=[]; unresolved=[]
    ui_effects={"UI_ONLY","CONTEXT_STATE","READ","READ_ONLY","READONLY","NAVIGATION_ONLY","LOCAL_STATE","UI_STATE"}
    for uid,c in controls.items():
        au=str(val(c,"action_uid","action") or "")
        if not au:
            for b in bindings:
                if b["control_uid"]==uid:
                    au=b["action_uid"];break
        a=actions.get(au,{}) if au else {}
        gate=str(val(c,"gate_uid","gate") or val(a,"gate_uid","gate") or "")
        perm=str(val(c,"permission_uid","permission") or val(a,"permission_uid","permission") or "")
        effect=str(val(a,"effect_type","effect","effect_class") or val(c,"effect_type","effect","effect_class") or "")
        port=str(val(a,"port_uid","port","integration_port_uid") or val(c,"port_uid","port","integration_port_uid") or "")
        runtime=flatten_runtime(val(c,"runtime_binding")) or flatten_runtime(val(a,"runtime_binding"))
        operation=str(val(c,"registered_operation","operation") or val(a,"registered_operation","operation") or "")
        method=""
        if port and port in ports:
            pr=ports[port]
            operation=operation or str(val(pr,"registered_operation","operation") or "")
            method=str(val(pr,"method_effective_path","method_path","method / path","method","route","api_path","endpoint") or "")
            runtime=runtime or flatten_runtime(val(pr,"runtime_binding"))
            perm=perm or str(val(pr,"registered_permission","permission_uid","permission") or "")
        if operation and not method and operation in op_index and op_index[operation]["methods"]:
            method=op_index[operation]["methods"][0]
        # parse runtime binding text for endpoint-like path
        if not method and runtime:
            m=re.search(r"\b(GET|POST|PATCH|PUT|DELETE)\s+(/[^ ;,]+)",runtime,re.I)
            if m: method=f"{m.group(1).upper()} {m.group(2)}"
        et=effect.upper().strip()
        is_effectful=bool(et and not any(x in et for x in ui_effects))
        # action/permission semantics may identify effectful control even if effect_type absent
        if not effect and au and any(w in au.upper() for w in ["CREATE","SAVE","UPDATE","DELETE","EXECUTE","RUN","START","STOP","RETRY","APPROVE","DECIDE","LOCK","PUBLISH","DISPATCH","ASSIGN","REVOKE","CONFIG","TEST","HANDOFF","APPLY","COMPLETE","RETIRE","RESTORE","MERGE"]):
            is_effectful=True
        status="SOURCE_EXACT"
        missing=[]
        if not au: missing.append("action_uid")
        if not gate: missing.append("gate_uid")
        if not perm: missing.append("permission")
        if is_effectful and not (port or operation or method or runtime): missing.append("runtime_binding")
        if missing:
            status="UNRESOLVED"
            unresolved.append({"control_uid":uid,"missing":missing,"action_uid":au,"effect":effect,"source_path":c.get("__path","")})
        rows.append({
          "control_uid":uid,
          "label":str(val(c,"label","name","display_name","title","control_label") or ""),
          "type":str(val(c,"type","control_type","ui_type") or ""),
          "section":str(val(c,"section_uid","section","sec") or ""),
          "action_uid":au,"gate_uid":gate,"permission":perm,"effect":effect,
          "port_uid":port,"operation":operation,"method_path":method,"runtime_binding":runtime,
          "status":status,"source_path":c.get("__path","")
        })
    report["pages"][page]={
      "authority_path":path,
      "authority_sha256":hashlib.sha256(raw.encode()).hexdigest(),
      "counts":{"controls":len(controls),"actions":len(actions),"ports":len(ports),"gates":len(gates),"permissions":len(perms),"operations":len(op_index)},
      "claims":claims,
      "unresolved_controls":unresolved,
      "controls":rows,
      "sample_actions":[{"uid":u,**{k:v for k,v in a.items() if k in ["label","trigger_semantics","effect_type","owner","port_uid","runtime_binding","gate_uid","permission_uid"]}} for u,a in list(actions.items())[:40]],
      "sample_ports":[{"uid":u,**{k:v for k,v in p.items() if k in ["registered_operation","operation","method_effective_path","method_path","registered_permission","permission_uid","runtime_binding"]}} for u,p in list(ports.items())[:40]],
    }
Path("__temp_reports__/machine_authority_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({p:{"counts":v["counts"],"unresolved":len(v["unresolved_controls"])} for p,v in report["pages"].items()},ensure_ascii=False,indent=2))
