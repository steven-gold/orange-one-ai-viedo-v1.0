from __future__ import annotations
import copy, hashlib, importlib.util, yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TARGET=ROOT/'.github/governance-maintenance/promote_basic_design_atomic_materialization.py'
spec=importlib.util.spec_from_file_location('atomic_promote',TARGET)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
orig_stage=m.mutate_stage_refs
orig_rev=m.update_source_revisions

def hobj(d):
    x=copy.deepcopy(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()

def patched_stage_refs():
    orig_stage()
    mapping={'STAGE-02':['WEB-GOV-01-S084'],'STAGE-03':['WEB-GOV-01-S084'],'STAGE-04':['WEB-GOV-01-S084','WEB-GOV-01-S085','WEB-GOV-01-S086']}
    p=m.SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'; d=m.load(p)
    for uid,vals in mapping.items(): m.unique_extend(d['semantic_snapshot']['stage_reference_rules'][uid]['exact_required_normative_section_uids'],vals)
    d['governance_revision']=m.NEW_SOURCE_REV; d['content_hash']=hobj(d); m.dump(p,d)

def patched_source_revisions():
    orig_rev()
    p=m.SOURCE/'11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml'; d=m.load(p)
    d['candidate']='v2.2.12_BASIC_DESIGN_ATOMIC_MATERIALIZATION_CANDIDATE'
    d['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'
    fr=d.setdefault('fresh_revalidation',{})
    fr['required']=True
    fr['current_source_revision']=m.NEW_SOURCE_REV
    fr['current_closure_credit']=False
    fr['predecessor_evidence_current_closure_credit']=False
    fr['embedded_preformal_execution_role']='HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'
    fr['predecessor_wrapper_result_role']='HISTORICAL_PREDECESSOR_EVIDENCE_ONLY'
    fr['persisted_head_full_line_required']=True
    fr['historical_evidence_may_close_successor']=False
    m.dump(p,d)

m.mutate_stage_refs=patched_stage_refs
m.update_source_revisions=patched_source_revisions
m.main()
