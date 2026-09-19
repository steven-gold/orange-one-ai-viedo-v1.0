#!/usr/bin/env python3
from pathlib import Path
import ast

p=Path('.github/governance-maintenance/promote_blueprint_traceability_governance.py')
s=p.read_text(encoding='utf-8')
tree=ast.parse(s)
fn=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='apply'),None)
if fn is None:
    raise SystemExit('APPLY_FUNCTION_NOT_FOUND')
target=None
for n in ast.walk(fn):
    if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='mutate_stage_and_semantic':
        target=n
        break
if target is None or target.end_lineno is None:
    raise SystemExit('MUTATE_STAGE_SEMANTIC_ASSIGNMENT_NOT_FOUND')
lines=s.splitlines()
insert=[
"    rp=SOURCE/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'",
"    ref=load(rp)",
"    bt_ref=ref.setdefault('blueprint_type_identities',[])",
"    if not any((x or {}).get('blueprint_type_uid')=='BPTYPE-GOV-007' for x in bt_ref):",
"        bt_ref.append({'blueprint_type_uid':'BPTYPE-GOV-007','canonical_name':'CONSTRUCTION_BLUEPRINT_PACKAGE','planning_domain':'NON_OWNING_BINDING','created_stage_uid':'STAGE-04'})",
"    dump(rp,ref)",
"    sp=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'",
"    sem=load(sp)",
"    bt_sem=sem['semantic_snapshot'].setdefault('blueprint_type_identities',[])",
"    if not any((x or {}).get('blueprint_type_uid')=='BPTYPE-GOV-007' for x in bt_sem):",
"        bt_sem.append({'blueprint_type_uid':'BPTYPE-GOV-007','canonical_name':'CONSTRUCTION_BLUEPRINT_PACKAGE','planning_domain':'NON_OWNING_BINDING','created_stage_uid':'STAGE-04'})",
"    sem['content_hash']=hobj(sem)",
"    dump(sp,sem)",
"    semantic_hash=sem['content_hash']",
]
lines[target.end_lineno:target.end_lineno]=insert
patched='\n'.join(lines)+'\n'
ast.parse(patched)
p.write_text(patched,encoding='utf-8')
print('PASS: AST blueprint type identity projection patch inserted')
