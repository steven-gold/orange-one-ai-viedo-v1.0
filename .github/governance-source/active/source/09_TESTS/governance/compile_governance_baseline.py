#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys,yaml,json,hashlib
sys.dont_write_bytecode=True
from governance_common import extract_requirements
ROOT=Path(__file__).resolve().parents[2]
BASELINE=ROOT/'11_EVIDENCE/audit/AUDIT_BASELINE.yaml'
DETAIL_INDEX=ROOT/'11_EVIDENCE/audit/generated/GOVERNANCE_REQUIREMENT_INDEX.json'
BP=ROOT/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
CAT=ROOT/'10_REGISTRY/AUDIT_CATALOG.yaml'
SEC=ROOT/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def hobj(d):
    x=dict(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=160).encode()).hexdigest()
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def main():
    if not BP.exists() or not CAT.exists() or not SEC.exists():
        print('required management artifact missing',file=sys.stderr); return 2
    bp=load(BP); cat=load(CAT); sec=load(SEC)
    cat_uids=[x.get('audit_item_uid') for x in cat.get('items') or []]
    if bp.get('audit_item_uids')!=cat_uids:
        print('acceptance blueprint / audit catalog denominator mismatch',file=sys.stderr); return 3
    reqs,sources=extract_requirements(ROOT)
    counts={'total':len(reqs),'must':sum(r['modality']=='MUST' for r in reqs),'must_not':sum(r['modality']=='MUST_NOT' for r in reqs),'auto':sum(r['automation']=='AUTO' for r in reqs),'manual_evidence':sum(r['automation']=='MANUAL_EVIDENCE' for r in reqs)}
    compact=[{'id':r['requirement_id'],'src':r['source'],'line':r['line'],'mode':r['modality'],'hash':r['clause_hash'],'validator':r['validator_id'],'auto':r['automation'],'blocking':r['blocking']} for r in reqs]
    data={
      'schema_version':2,'artifact_uid':'AUDIT-BASELINE-GOV-001','artifact_type':'AUDIT_BASELINE','status':'CURRENT_COMPILED',
      'canonical_path':'11_EVIDENCE/audit/AUDIT_BASELINE.yaml','owner_uid':'OWNER-GOVERNANCE-AUDIT-BASELINE','governance_revision':load(ROOT/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml').get('governance_revision'),
      'compiled_from':{'acceptance_blueprint_uid':bp.get('artifact_uid'),'acceptance_blueprint_sha256':sha(BP),'audit_catalog_uid':cat.get('artifact_uid'),'audit_catalog_sha256':sha(CAT),'section_registry_uid':sec.get('artifact_uid') or sec.get('registry_uid'),'section_registry_sha256':sha(SEC)},
      'denominator':{'audit_item_uids':cat_uids,'required_count':len(cat_uids),'denominator_hash':hashlib.sha256('\n'.join(cat_uids).encode()).hexdigest()},
      'governance_compilation':{
        'schema_version':'2.0.0','policy':'COMPACT_REQUIREMENT_MANIFEST_ONLY; NORMATIVE_PROSE_REMAINS_IN_01_04','authority_role':'COMPILED_BASELINE_NOT_SECOND_ACCEPTANCE_AUTHORITY',
        'sources':sources,'counts':counts,'coverage_contract':{'uncompiled_must':0,'uncompiled_must_not':0,'unknown_baseline_requirement':0,'self_declared_pass_not_recomputed':0},
        'detail_index':'11_EVIDENCE/audit/generated/GOVERNANCE_REQUIREMENT_INDEX.json','result_output':'11_EVIDENCE/audit/generated/GOVERNANCE_VALIDATION_RESULT.json','requirements':compact,
      }
    }
    data['content_hash']=hobj(data)
    BASELINE.parent.mkdir(parents=True,exist_ok=True); BASELINE.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False,width=160),encoding='utf-8')
    DETAIL_INDEX.parent.mkdir(parents=True,exist_ok=True); DETAIL_INDEX.write_text(json.dumps({'document_id':'GOVERNANCE_REQUIREMENT_INDEX','authority':False,'normative_sources':sources,'counts':counts,'requirements':reqs},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"compiled_requirements={counts['total']} MUST={counts['must']} MUST_NOT={counts['must_not']} AUTO={counts['auto']} MANUAL={counts['manual_evidence']} audit_denominator={len(cat_uids)}")
    return 0
if __name__=='__main__': raise SystemExit(main())
