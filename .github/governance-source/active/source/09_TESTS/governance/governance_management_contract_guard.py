#!/usr/bin/env python3
from pathlib import Path
import json,yaml
ROOT=Path(__file__).resolve().parents[2]
REQ={
 'NAMING_REGISTRY.yaml':'REG-NAMING-001','BLUEPRINT_REGISTRY.yaml':'REG-BLUEPRINT-001','AUDIT_CATALOG.yaml':'REG-AUDIT-CATALOG-001',
 'REVIEW_PROGRESS_LEDGER.yaml':'REG-REVIEW-PROGRESS-001','GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml':'BP-GOVERNANCE-ACCEPTANCE-001',
 'SECTION_NUMBER_REGISTRY.yaml':'REG-NORMATIVE-SECTION-001','PROTECTED_CURRENT_ARTIFACT_REGISTRY.yaml':'REG-PROTECTED-CURRENT-ARTIFACT-001',
 'GOVERNANCE_ROOT_MANIFEST.yaml':'REG-GOVERNANCE-ROOT-MANIFEST-001','CONSTRUCTION_ARTIFACT_INDEX.yaml':'REG-CONSTRUCTION-ARTIFACT-001',
 'GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml':'REG-LIFECYCLE-STAGE-001','STAGE1_SOURCE_FACT_CONTRACTS.yaml':'REG-STAGE1-SOURCE-FACT-CONTRACTS-001','REFERENCE_RULE_REGISTRY.yaml':'REG-REFERENCE-RULE-001'}
def load(p): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def validate(root=ROOT):
    failures=[]; uids={}
    for fn,uid in REQ.items():
        p=root/'10_REGISTRY'/fn
        if not p.exists(): failures.append('management_artifact_missing:'+fn); continue
        d=load(p)
        if d.get('artifact_uid')!=uid and d.get('registry_uid')!=uid: failures.append('artifact_uid_mismatch:'+fn)
        found=d.get('artifact_uid') or d.get('registry_uid')
        if found in uids: failures.append('duplicate_management_uid:'+str(found))
        uids[found]=fn
        if d.get('status') not in ('CURRENT_CANDIDATE','CANDIDATE_PREFORMAL'): failures.append('management_not_current_candidate:'+fn)
        if d.get('canonical_path') and d.get('canonical_path')!=f'10_REGISTRY/{fn}': failures.append('canonical_path_mismatch:'+fn)
    # closed-loop checks
    bp=load(root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml') if (root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml').exists() else {}
    cat=load(root/'10_REGISTRY/AUDIT_CATALOG.yaml') if (root/'10_REGISTRY/AUDIT_CATALOG.yaml').exists() else {}
    cat_uids={x.get('audit_item_uid') for x in cat.get('items') or []}
    if set(bp.get('audit_item_uids') or [])!=cat_uids: failures.append('acceptance_blueprint_catalog_denominator_mismatch')
    if bp.get('baseline_compiler',{}).get('output')!='11_EVIDENCE/audit/AUDIT_BASELINE.yaml': failures.append('baseline_output_contract_invalid')
    rev=load(root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml') if (root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml').exists() else {}
    if rev.get('progress',{}).get('approved',0)>rev.get('progress',{}).get('required',0): failures.append('review_progress_impossible')
    mp=rev.get('machine_review_progress') or {}
    if (mp.get('required'),mp.get('approved'),mp.get('pending'),mp.get('percentage'))!=(1,1,0,100): failures.append('machine_review_progress_not_closed')
    sync=bp.get('current_test_evidence_sync_contract') or {}
    if sync.get('validator_uid')!='VAL-GOV-032' or sync.get('required') is not True: failures.append('current_test_evidence_sync_contract_missing')
    return {'status':'PASS' if not failures else 'FAIL','management_artifacts':len(REQ),'failures':failures}
if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
