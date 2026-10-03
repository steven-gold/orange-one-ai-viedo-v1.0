#!/usr/bin/env python3
# GOVERNANCE_STANDALONE_REGRESSION_PYTEST_ISOLATION
# This asset is executed by the governance subprocess/JSON runner, not pytest collection.
# Successor regression for GOV-INV-FROZEN-DESIGN-PROGRAM-FIELD-BINDING-001.
# Kept out of the immutable v2.1.13 denominator; wired into CI directly.
import sys as _governance_runner_sys
if __name__ != "__main__" and "pytest" in _governance_runner_sys.modules:
    import pytest as _governance_pytest
    _governance_pytest.skip("standalone governance regression executable; use registered subprocess runner", allow_module_level=True)
from pathlib import Path
import json, tempfile, yaml, importlib.util, shutil
PKG=Path(__file__).resolve().parents[2]
VP=Path(__file__).resolve().parent/'validate_stage_execution_invariants.py'
spec=importlib.util.spec_from_file_location('v213',VP); v213=importlib.util.module_from_spec(spec); spec.loader.exec_module(v213)

def case(name,ok,detail=None): return {'case':name,'ok':bool(ok),'detail':detail or {}}

res=[]
invdoc=yaml.safe_load((PKG/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml').read_text(encoding='utf-8')) or {}
det=(invdoc.get('invariants') or {}).get('DETERMINISTIC_STAGE_AUDIT') or {}
fbind=(invdoc.get('invariants') or {}).get('FROZEN_DESIGN_PROGRAM_FIELD_BINDING') or {}
s5c=(det.get('stage_contracts') or {}).get('STAGE-05') or {}
s6c=(det.get('stage_contracts') or {}).get('STAGE-06') or {}

res.append(case('frozen_design_is_sole_implementation_authority', fbind.get('frozen_design_is_sole_implementation_authority') is True and fbind.get('generic_operation_template_may_replace_frozen_design') is False))
res.append(case('template_copy_and_file_presence_credit_zero', fbind.get('template_copy_identity_completion_credit')==0 and fbind.get('file_presence_or_artifact_count_completion_credit')==0 and fbind.get('scaffold_or_starter_program_completion_credit')==0))
res.append(case('omitted_frozen_row_and_count_only_diff_blocked', fbind.get('omitted_frozen_row')=='BLOCK' and fbind.get('count_only_implementation_diff_evidence')=='BLOCK'))
res.append(case('generic_geometry_theme_navigation_blocked', fbind.get('generic_geometry_theme_navigation_or_control_uid_remaining')=='BLOCK' and fbind.get('template_value_contradicting_frozen_design')=='BLOCK'))
res.append(case('frozen_vs_program_semantic_diff_required', fbind.get('stage06_frozen_vs_program_semantic_diff_required') is True and fbind.get('screenshot_or_build_success_may_substitute_semantic_diff') is False and s5c.get('generic_operation_template_substitution')=='BLOCK' and s6c.get('frozen_design_vs_program_semantic_diff_required') is True))

REGISTRY_FILES=['STAGE_EXECUTION_INVARIANT_REGISTRY.yaml','GOVERNANCE_ROOT_MANIFEST.yaml','GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml','AUDIT_CATALOG.yaml','STAGE_EXECUTION_MASTER_PLAN.yaml']
REPO=PKG.parents[3]
def mutate_validate(mutator):
    with tempfile.TemporaryDirectory() as td:
        repo=Path(td)/'rebuild'
        dst=repo/'.github/governance-source/active/source'
        (dst/'10_REGISTRY').mkdir(parents=True)
        for name in REGISTRY_FILES:
            shutil.copy2(PKG/'10_REGISTRY'/name, dst/'10_REGISTRY'/name)
        for rel in ['governance/execution-domains/AUDIT/STEPS.yaml','governance/execution-domains/AUDIT_PROFILE.yaml','governance/execution-domains/STAGE/STEPS.yaml']:
            src=REPO/rel
            target=repo/rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        mutator(dst)
        return v213.validate(dst)
def dump_inv(root, inv):
    (root/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml').write_text(yaml.safe_dump(inv,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
def load_inv(root):
    return yaml.safe_load((root/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml').read_text(encoding='utf-8')) or {}
def fail_template_copy(root):
    inv=load_inv(root); inv['invariants']['FROZEN_DESIGN_PROGRAM_FIELD_BINDING']['generic_operation_template_may_replace_frozen_design']=True; dump_inv(root,inv)
def fail_omitted_frozen_row(root):
    inv=load_inv(root); inv['invariants']['FROZEN_DESIGN_PROGRAM_FIELD_BINDING']['omitted_frozen_row']='ALLOW'; dump_inv(root,inv)
def fail_count_only_diff(root):
    inv=load_inv(root); inv['invariants']['FROZEN_DESIGN_PROGRAM_FIELD_BINDING']['count_only_implementation_diff_evidence']='ALLOW'; dump_inv(root,inv)
def fail_generic_geometry(root):
    inv=load_inv(root); inv['invariants']['FROZEN_DESIGN_PROGRAM_FIELD_BINDING']['generic_geometry_theme_navigation_or_control_uid_remaining']='ALLOW'; dump_inv(root,inv)
def fail_missing_visual_diff(root):
    inv=load_inv(root); inv['invariants']['FROZEN_DESIGN_PROGRAM_FIELD_BINDING']['user_visible_frozen_field_requires_computed_visual_evidence']=False; dump_inv(root,inv)
mut_template=mutate_validate(fail_template_copy)
res.append(case('template_copy_as_implementation_fails_closed', mut_template['status']=='FAIL' and any('frozen_design_sole_authority' in x for x in mut_template.get('failures') or []), mut_template))
mut_omit=mutate_validate(fail_omitted_frozen_row)
res.append(case('omitted_frozen_row_fails_closed', mut_omit['status']=='FAIL' and any(x=='frozen_design_fail_closed_missing:omitted_frozen_row' for x in mut_omit.get('failures') or []), mut_omit))
mut_count=mutate_validate(fail_count_only_diff)
res.append(case('count_only_implementation_diff_fails_closed', mut_count['status']=='FAIL' and any(x=='frozen_design_fail_closed_missing:count_only_implementation_diff_evidence' for x in mut_count.get('failures') or []), mut_count))
mut_geom=mutate_validate(fail_generic_geometry)
res.append(case('generic_geometry_token_remaining_fails_closed', mut_geom['status']=='FAIL' and any(x=='frozen_design_fail_closed_missing:generic_geometry_theme_navigation_or_control_uid_remaining' for x in mut_geom.get('failures') or []), mut_geom))
mut_visual=mutate_validate(fail_missing_visual_diff)
res.append(case('missing_computed_visual_diff_fails_closed', mut_visual['status']=='FAIL' and any('frozen_vs_program_semantic_diff_contract_incomplete' in x for x in mut_visual.get('failures') or []), mut_visual))

out={'suite':'v2.1.15 Frozen Design program-field binding successor regression','total':len(res),'passed_expectations':sum(x['ok'] for x in res),'results':res}
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['total']==10 and out['passed_expectations']==10 else 1)
