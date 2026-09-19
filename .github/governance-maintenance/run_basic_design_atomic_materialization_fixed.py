from __future__ import annotations
import copy, hashlib, importlib.util, yaml
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TARGET=ROOT/'.github/governance-maintenance/promote_basic_design_atomic_materialization.py'
spec=importlib.util.spec_from_file_location('atomic_promote',TARGET)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
original=m.mutate_stage_refs

def hobj(d):
    x=copy.deepcopy(d)
    x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()

def patched_stage_refs():
    original()
    mapping={'STAGE-02':['WEB-GOV-01-S084'],'STAGE-03':['WEB-GOV-01-S084'],'STAGE-04':['WEB-GOV-01-S084','WEB-GOV-01-S085','WEB-GOV-01-S086']}
    p=m.SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    d=m.load(p)
    for uid,vals in mapping.items():
        m.unique_extend(d['semantic_snapshot']['stage_reference_rules'][uid]['exact_required_normative_section_uids'],vals)
    d['governance_revision']=m.NEW_SOURCE_REV
    d['content_hash']=hobj(d)
    m.dump(p,d)

m.mutate_stage_refs=patched_stage_refs
m.main()
