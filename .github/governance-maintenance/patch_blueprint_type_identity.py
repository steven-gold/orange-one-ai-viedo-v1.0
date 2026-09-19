#!/usr/bin/env python3
from pathlib import Path
import ast, re

PROMOTION=Path('.github/governance-maintenance/promote_blueprint_traceability_governance.py')
s=PROMOTION.read_text(encoding='utf-8')
auth_pat=re.compile(r'USR-DIRECTIVE-20260919-BLUEPRINT-CONSTRUCTION-TRACEABILITY-HARDENING-R\d+')
found=sorted(set(auth_pat.findall(s)))
if not found:
    raise SystemExit('PROMOTION_AUTH_UID_PATTERN_NOT_FOUND')
s=auth_pat.sub('USR-DIRECTIVE-20260919-BLUEPRINT-CONSTRUCTION-TRACEABILITY-HARDENING-R12',s)

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
        vals=[a.value for a in n.value.args[:2] if isinstance(a,ast.Constant)]
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
        "    csp=SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'",
        "    cs=load(csp)",
        "    cs['candidate']='v2.2.10_BLUEPRINT_CONSTRUCTION_TRACEABILITY_HARDENING_CANDIDATE'",
        "    cs['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'",
        "    fresh=cs.setdefault('fresh_revalidation',{})",
        "    fresh['required']=True",
        "    fresh['current_source_revision']=NEW_SOURCE_REV",
        "    fresh['current_closure_credit']=False",
        "    fresh['predecessor_evidence_current_closure_credit']=False",
        "    fresh['embedded_preformal_execution_role']='HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'",
        "    fresh['predecessor_wrapper_result_role']='HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'",
        "    fresh['persisted_head_full_line_required']=True",
        "    fresh['historical_evidence_may_close_successor']=False",
        "    dump(csp,cs)",
        "    rvp=SOURCE/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml'",
        "    rv=load(rvp)",
        "    rv['governance_revision']=NEW_SOURCE_REV",
        "    dump(rvp,rv)",
    ]),
    (cleanup_target.lineno-1,[
        "    for extra in [ROOT/'.github/governance-maintenance/patch_blueprint_type_identity.py', ROOT/'.github/governance-maintenance/promote_blueprint_traceability_governance.py.gz']:",
        "        if extra.exists(): extra.unlink()",
    ]),
]
for idx,chunk in sorted(insertions,key=lambda x:x[0],reverse=True):
    lines[idx:idx]=chunk
s='\n'.join(lines)+'\n'

tree=ast.parse(s)
class ReplaceHardener(ast.NodeTransformer):
    def __init__(self): self.count=0
    def visit_Call(self,node):
        self.generic_visit(node)
        if isinstance(node.func,ast.Attribute) and node.func.attr=='replace' and isinstance(node.func.value,ast.Name) and node.func.value.id=='s':
            self.count+=1
            return ast.copy_location(ast.Call(func=ast.Name(id='replace_exact_once',ctx=ast.Load()),args=[node.func.value,*node.args[:2]],keywords=[]),node)
        return node
hardener=ReplaceHardener()
tree=hardener.visit(tree)
ast.fix_missing_locations(tree)
if hardener.count!=2:
    raise SystemExit('RAW_TEXT_REPLACE_TARGET_COUNT='+str(hardener.count))
helper_def=ast.parse("""def replace_exact_once(text, old, new):
    count=text.count(old)
    if count != 1:
        raise RuntimeError(f'BOUNDED_REPLACE_TARGET_COUNT expected=1 actual={count}')
    idx=text.index(old)
    return text[:idx] + new + text[idx+len(old):]
""").body[0]
insert_at=0
while insert_at < len(tree.body) and isinstance(tree.body[insert_at],(ast.Import,ast.ImportFrom)):
    insert_at+=1
tree.body.insert(insert_at,helper_def)
ast.fix_missing_locations(tree)
patched=ast.unparse(tree)+'\n'
ast.parse(patched)
PROMOTION.write_text(patched,encoding='utf-8')
print(f'PASS: auth {found}->R12; successor candidate/review identities synchronized; raw replacements hardened={hardener.count}')
