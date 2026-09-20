#!/usr/bin/env python3
from content_integrity_engine import validate_contract
def fixture(scope,prefix,count):
    rows=[{"uid":f"{prefix}-{i}","name":f"row-{i}","owner":"OWNER"} for i in range(1,count+1)]
    return {"scope_uid":scope,"row_sets":{"objects":{"uid_key":"uid","required_fields":["uid","name","owner"],"rows":rows}},"bidirectional_sets":{"objects":{"authority":[x["uid"] for x in rows],"implementation":[x["uid"] for x in rows]}},"required_functional_chain_nodes":["entry","action","runtime","audit","success","failure","recovery"],"functional_chains":[{"chain_uid":f"{prefix}-CHAIN-{i}","nodes":{"entry":True,"action":True,"runtime":True,"audit":True,"success":True,"failure":True,"recovery":True}} for i in range(1,count+1)]}
for case in [fixture("CATALOG-SCOPE","CAT",2),fixture("BILLING-SCOPE","BILL",5)]: assert validate_contract(case)["result"]=="PASS"
bad=fixture("OPERATIONS-SCOPE","OPS",3);bad["row_sets"]["objects"]["rows"][1]["owner"]="";assert validate_contract(bad)["result"]=="BLOCKED"
bad=fixture("KNOWLEDGE-SCOPE","KN",4);bad["bidirectional_sets"]["objects"]["implementation"].append("UNAUTHORIZED");out=validate_contract(bad);assert out["result"]=="BLOCKED" and any(x["category"]=="IMPLEMENTATION_TO_AUTHORITY" for x in out["findings"])
bad=fixture("SUPPORT-SCOPE","SUP",1);bad["functional_chains"][0]["nodes"]["audit"]=False;out=validate_contract(bad);assert out["result"]=="BLOCKED" and any(x["category"]=="FUNCTIONAL_CHAIN_CONTENT" for x in out["findings"])
print("PASS: product-neutral content integrity engine supports different scopes and denominators; negative field/set/chain cases fail closed")
