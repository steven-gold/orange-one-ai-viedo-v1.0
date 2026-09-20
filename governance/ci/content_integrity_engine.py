#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import yaml

def nonempty(value):
    if value is None:return False
    if isinstance(value,str):return bool(value.strip())
    if isinstance(value,(list,dict)):return bool(value)
    return True

def unique_rows(rows,key):
    if not isinstance(rows,list):return False
    vals=[str((row or {}).get(key) or "") for row in rows if isinstance(row,dict)]
    return len(vals)==len(rows) and len(vals)==len(set(vals)) and all(vals)

def set_differences(authority_values,implementation_values):
    a=set(map(str,authority_values or []));i=set(map(str,implementation_values or []))
    return {"missing_in_implementation":sorted(a-i),"extra_in_implementation":sorted(i-a)}

class ContentIntegrityEngine:
    def __init__(self,scope_uid):
        self.scope_uid=str(scope_uid);self.checks=[];self.findings=[]
    def record(self,uid,ok,category,detail,evidence=None,severity="BLOCKER"):
        row={"check_uid":str(uid),"category":str(category),"result":"PASS" if ok else "FAIL","detail":str(detail)}
        if evidence is not None:row["evidence"]=evidence
        if not ok:row["severity"]=severity;self.findings.append(row)
        self.checks.append(row);return ok
    def required_rows(self,name,rows,uid_key,required_fields):
        self.record(name+"-NONEMPTY",isinstance(rows,list) and bool(rows),"REQUIRED_ROWS",name+" is non-empty",len(rows) if isinstance(rows,list) else None)
        self.record(name+"-UNIQUE",unique_rows(rows,uid_key),"REQUIRED_ROWS",name+" has unique non-empty "+uid_key)
        missing=[]
        for row in rows if isinstance(rows,list) else []:
            if not isinstance(row,dict):missing.append({"row":row,"missing":list(required_fields)});continue
            miss=[f for f in required_fields if not nonempty(row.get(f))]
            if miss:missing.append({"uid":row.get(uid_key),"missing":miss})
        self.record(name+"-FIELDS",not missing,"REQUIRED_FIELDS",name+" rows contain required fields",missing)
        return missing
    def references(self,name,rows,source_uid_key,bindings):
        failures=[];universes={k:set(map(str,v or [])) for k,v in bindings.items()}
        for row in rows or []:
            if not isinstance(row,dict):continue
            miss=[field for field,universe in universes.items() if str(row.get(field)) not in universe]
            if miss:failures.append({"uid":row.get(source_uid_key),"unresolved":miss})
        self.record(name+"-REFERENCES",not failures,"REFERENTIAL_INTEGRITY",name+" references resolve",failures);return failures
    def bidirectional(self,name,authority_values,implementation_values):
        diff=set_differences(authority_values,implementation_values)
        self.record(name+"-A2I",not diff["missing_in_implementation"],"AUTHORITY_TO_IMPLEMENTATION",name+" Authority set is implemented",diff["missing_in_implementation"])
        self.record(name+"-I2A",not diff["extra_in_implementation"],"IMPLEMENTATION_TO_AUTHORITY",name+" implementation set has Authority",diff["extra_in_implementation"]);return diff
    def functional_chains(self,rows,required_nodes):
        incomplete=[]
        for row in rows or []:
            nodes=(row or {}).get("nodes") or {};miss=[n for n in required_nodes if nodes.get(n) is not True]
            if miss:incomplete.append({"chain_uid":(row or {}).get("chain_uid") or (row or {}).get("action_uid"),"missing_nodes":miss})
        self.record("FUNCTIONAL-CHAINS",not incomplete,"FUNCTIONAL_CHAIN_CONTENT","All applicable functional-chain nodes are complete or formally proven non-applicable",incomplete);return incomplete
    def result(self,extra=None):
        blockers=[x for x in self.findings if x.get("severity")=="BLOCKER"]
        out={"artifact_type":"NON_NORMATIVE_PRODUCT_NEUTRAL_CONTENT_INTEGRITY_RESULT","scope_uid":self.scope_uid,"content_complete":not blockers,"result":"PASS" if not blockers else "BLOCKED","check_total":len(self.checks),"pass_total":sum(x["result"]=="PASS" for x in self.checks),"fail_total":len(self.findings),"blocker_total":len(blockers),"checks":self.checks,"findings":self.findings,"product_stage_credit":0}
        if isinstance(extra,dict):out.update(extra)
        return out

def validate_contract(contract):
    if not contract.get("scope_uid"):raise ValueError("scope_uid required")
    eng=ContentIntegrityEngine(contract["scope_uid"])
    for name,spec in (contract.get("row_sets") or {}).items():eng.required_rows(name,spec.get("rows") or [],str(spec.get("uid_key") or "uid"),spec.get("required_fields") or [])
    for name,spec in (contract.get("reference_sets") or {}).items():eng.references(name,spec.get("rows") or [],str(spec.get("uid_key") or "uid"),spec.get("bindings") or {})
    for name,spec in (contract.get("bidirectional_sets") or {}).items():eng.bidirectional(name,spec.get("authority") or [],spec.get("implementation") or [])
    if contract.get("functional_chains") or contract.get("required_functional_chain_nodes"):eng.functional_chains(contract.get("functional_chains") or [],contract.get("required_functional_chain_nodes") or [])
    return eng.result({"contract_kind":contract.get("contract_kind") or "GENERIC_TYPED_CONTENT_INTEGRITY"})

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--contract",required=True);ap.add_argument("--report",required=True);args=ap.parse_args()
    p=Path(args.contract);raw=p.read_text(encoding="utf-8");contract=json.loads(raw) if p.suffix.lower()==".json" else (yaml.safe_load(raw) or {})
    result=validate_contract(contract);Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("scope_uid","result","content_complete","check_total","blocker_total")},ensure_ascii=False));return 0 if result["content_complete"] else 2
if __name__=="__main__":raise SystemExit(main())
