#!/usr/bin/env python3
from pathlib import Path
import ast

PROMOTION=Path('.github/governance-maintenance/promote_blueprint_traceability_governance.py')
s=PROMOTION.read_text(encoding='utf-8')
old_auth='USR-DIRECTIVE-20260919-BLUEPRINT-CONSTRUCTION-TRACEABILITY-HARDENING-R1'
new_auth='USR-DIRECTIVE-20260919-BLUEPRINT-CONSTRUCTION-TRACEABILITY-HARDENING-R9'
if old_auth not in s:
    raise SystemExit('PROMOTION_AUTH_UID_R1_NOT_FOUND')
s=s.replace(old_auth,new_auth)

tree=ast.parse(s)
apply_fn=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='apply'),None)
main_fn=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main'),None)
if apply_fn is None or main_fn is None:
    raise SystemExit('APPLY_OR_MAIN_FUNCTION_NOT_FOUND')

semantic_target=None
for n in ast.walk(apply_fn):
    if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='mutate_stage_and_semantic':
        semantic_target=n
        break
if semantic_target is None or semantic_target.end_lineno is None:
    raise SystemExit('MUTATE_STAGE_SEMANTIC_ASSIGNMENT_NOT_FOUND')

cleanup_target=None
for n in ast.walk(main_fn):
    if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='run':
        args=n.value.args
        vals=[a.value for a in args[:2] if isinstance(a,ast.Constant)]
        if vals==['git','config']:
            cleanup_target=n
            break
if cleanup_target is None or cleanup_target.lineno is None:
    raise SystemExit('PROMOTION_PRECOMMIT_GIT_CONFIG_CALL_NOT_FOUND')

lines=s.splitlines()
insertions=[
    (semantic_target.end_lineno,[
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
    ]),
    (cleanup_target.lineno-1,[
        "    for extra in [ROOT/'.github/governance-maintenance/patch_blueprint_type_identity.py', ROOT/'.github/governance-maintenance/promote_blueprint_traceability_governance.py.gz']:",
        "        if extra.exists(): extra.unlink()",
    ]),
]
for idx,chunk in sorted(insertions,key=lambda x:x[0],reverse=True):
    lines[idx:idx]=chunk
patched='\n'.join(lines)+'\n'
ast.parse(patched)
PROMOTION.write_text(patched,encoding='utf-8')
print('PASS: one-shot promotion helper patched semantic identity, R9 authorization, and cleanup lifecycle')
