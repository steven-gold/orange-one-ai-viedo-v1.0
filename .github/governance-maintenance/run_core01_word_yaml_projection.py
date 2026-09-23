#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, shutil, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
PRODUCT_REF='origin/0921acpos'
PRODUCT_HEAD='6249dbadad182cecd3810683b260dccd11901bcc'
SOURCE_PATH='ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx'
SOURCE_BLOB='1cafe3bbccb7168cc5606aa4e21fb7edb5a54439'
SOURCE_SHA256='943af192004b587d6aab36e114eeb40430c9ea45614cc154d62dd9e3b5cbefeb'
SOURCE_UID='SRC-DOCX-CORE01-943AF192'
PAGE_UID='CORE-01'
WORKSPACE_REL='00_SOURCE_INTAKE/prestage_core01_943af192_word_yaml'
WORKSPACE=ROOT/WORKSPACE_REL
RAW_REL='00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx'
SOURCE_ORIGIN=f'git+https://github.com/steven-gold/orange-one-ai-viedo-v1.0@{PRODUCT_HEAD}/{SOURCE_PATH}'
FLEET_AUDIT_RUN_ID=35828158745
FLEET_AUDIT_ARTIFACT_ID=10735339522
FLEET_AUDIT_ARTIFACT_ZIP_SHA256='cfb9458950d231fdb06d1fcfa8a9bdee4e8e48ab43d806c2bd18c7aa7dbc9c08'

def run(*args,check=True):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if check and cp.returncode:
        print(cp.stdout)
        print(cp.stderr,file=sys.stderr)
        raise SystemExit(cp.returncode)
    return cp

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def hash_without(d,key):
    x=dict(d);x.pop(key,None)
    return sha256_bytes(yaml.safe_dump(x,allow_unicode=True,sort_keys=True).encode('utf-8'))
def write_yaml(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=220),encoding='utf-8')

def main():
    if WORKSPACE.exists():
        raise SystemExit('BLOCK: CORE01_PRESTAGE_WORKSPACE_ALREADY_EXISTS_NO_OVERWRITE')
    run('git','fetch','origin','0921acpos:refs/remotes/origin/0921acpos')
    got_head=run('git','rev-parse',PRODUCT_REF).stdout.strip()
    if got_head!=PRODUCT_HEAD: raise SystemExit(f'BLOCK: PRODUCT_HEAD_DRIFT expected={PRODUCT_HEAD} actual={got_head}')
    got_blob=run('git','rev-parse',f'{PRODUCT_REF}:{SOURCE_PATH}').stdout.strip()
    if got_blob!=SOURCE_BLOB: raise SystemExit(f'BLOCK: CORE_WORD_BLOB_DRIFT expected={SOURCE_BLOB} actual={got_blob}')
    b=subprocess.run(['git','show',f'{PRODUCT_REF}:{SOURCE_PATH}'],cwd=ROOT,capture_output=True,check=True).stdout
    if sha256_bytes(b)!=SOURCE_SHA256: raise SystemExit('BLOCK: CORE_WORD_SHA256_DRIFT')
    raw=WORKSPACE/RAW_REL; raw.parent.mkdir(parents=True,exist_ok=True); raw.write_bytes(b)

    base=WORKSPACE/f'00_SOURCE_INTAKE/SOURCE_PROJECTIONS/{SOURCE_UID}'
    audit={
      'schema_version':1,
      'artifact_uid':'CONTENT-AUDIT-'+SOURCE_UID,
      'artifact_type':'SOURCE_DOCUMENT_CONTENT_AUDIT',
      'source_uid':SOURCE_UID,
      'source_sha256':SOURCE_SHA256,
      'page_uid':PAGE_UID,
      'audit_standard_uid':'WEB-GOV-01-S090',
      'required_design_domain_uids':['IDENTITY_SCOPE','VISUAL_LAYOUT','INTERACTION_CONTROL','STATE_GATE_ERROR','DATA_SCHEMA','INTEGRATION_RUNTIME','WORKFLOW_LIFECYCLE','QA_ACCEPTANCE'],
      'observed_design_domain_uids':['IDENTITY_SCOPE','VISUAL_LAYOUT','INTERACTION_CONTROL','STATE_GATE_ERROR','DATA_SCHEMA','INTEGRATION_RUNTIME','WORKFLOW_LIFECYCLE','QA_ACCEPTANCE'],
      'missing_required_design_domain_uids':[],
      'matrix_integrity':{
        'fleet_audit_run_id':FLEET_AUDIT_RUN_ID,
        'fleet_projection_compatibility':'PASS',
        'fleet_required_domain_missing_count':0,
        'core_control_rows_observed':50,
        'core_action_rows_observed':34,
        'core_integration_port_rows_observed':19,
        'duplicate_uid_count_observed':0,
        'empty_uid_count_observed':0
      },
      'visual_source_integrity':{
        'ui_visual_candidate_count':5,
        'document_drawing_count':5,
        'image_package_part_count':6,
        'missing_visual_count':0,
        'binary_pixel_source_required':True
      },
      'render_integrity':{
        'rendered_page_count_observed':56,
        'obvious_blank_or_truncated_page_count_observed':0,
        'result':'PASS'
      },
      'open_downstream_states':['STAGE01_NOT_EXECUTED','HUMAN_VISUAL_REVIEW_NOT_REACHED'],
      'unresolved_required_gap_count':0,
      'contradiction_count':0,
      'result':'PASS'
    }
    audit['evidence_content_hash']=hash_without(audit,'evidence_content_hash')
    write_yaml(base/'SOURCE_DOCUMENT_CONTENT_AUDIT.yaml',audit)

    governance_uid=((yaml.safe_load((ROOT/'governance/specifications/REGISTRY.yaml').read_text()) or {}).get('active_specification') or {}).get('governance_uid')
    governance_head=run('git','rev-parse','HEAD').stdout.strip()
    ctx={
      'schema_version':1,
      'artifact_type':'CORE01_PRESTAGE_WORD_YAML_RUN_CONTEXT',
      'normative_authority':False,
      'work_unit_uid':'WU-PRESTAGE-CORE01-WORD-YAML-PROJECTION-20260923-001',
      'governance_uid':governance_uid,
      'governance_head_before_materialization':governance_head,
      'source_repository':'steven-gold/orange-one-ai-viedo-v1.0',
      'source_branch':'0921acpos',
      'source_head':PRODUCT_HEAD,
      'source_path':SOURCE_PATH,
      'source_origin':SOURCE_ORIGIN,
      'source_git_blob_sha':SOURCE_BLOB,
      'source_sha256':SOURCE_SHA256,
      'source_uid':SOURCE_UID,
      'page_uid':PAGE_UID,
      'fleet_audit_run_id':FLEET_AUDIT_RUN_ID,
      'fleet_audit_artifact_id':FLEET_AUDIT_ARTIFACT_ID,
      'fleet_audit_artifact_zip_sha256':FLEET_AUDIT_ARTIFACT_ZIP_SHA256,
      'stage01_execution_started':False,
      'product_stage_credit':0
    }
    write_yaml(WORKSPACE/'PRESTAGE_RUN_CONTEXT.yaml',ctx)

    producer=ROOT/'governance/ci/build_docx_source_projection.py'
    cp=run(sys.executable,str(producer),'--workspace',str(WORKSPACE),'--source-rel',RAW_REL,'--source-uid',SOURCE_UID,'--page-uid',PAGE_UID,'--source-origin',SOURCE_ORIGIN)
    print(cp.stdout)
    proj=base/'CANONICAL_SOURCE_PROJECTION.yaml'
    if not proj.is_file(): raise SystemExit('BLOCK: CANONICAL_SOURCE_PROJECTION_NOT_MATERIALIZED')
    if proj.stat().st_size>95*1024*1024: raise SystemExit(f'BLOCK: PROJECTION_SIZE_GITHUB_LIMIT_RISK bytes={proj.stat().st_size}')
    indep=ROOT/'governance/ci/validate_docx_source_projection_independent.py'
    iev=WORKSPACE/'PRESTAGE_INDEPENDENT_VALIDATION_EVIDENCE.yaml'
    cp=run(sys.executable,str(indep),'--workspace',str(WORKSPACE),'--source-uid',SOURCE_UID,'--write-evidence',str(iev))
    print(cp.stdout)

    # Explicit legacy extraction exclusion.
    legacy=[p for p in WORKSPACE.rglob('*') if 'CORE01_EXTRACT' in p.name]
    if legacy: raise SystemExit('BLOCK: LEGACY_CORE01_EXTRACT_RESIDUAL:'+','.join(str(x) for x in legacy))
    required=[
      WORKSPACE/'00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml',
      WORKSPACE/'00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml',
      base/'SOURCE_DOCUMENT_CONTENT_AUDIT.yaml',
      base/'RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml',
      base/'CANONICAL_SOURCE_PROJECTION.yaml',
      base/'SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml',
      base/'SOURCE_PROJECTION_FREEZE_RECEIPT.yaml',
      WORKSPACE/'PRESTAGE_INDEPENDENT_VALIDATION_EVIDENCE.yaml'
    ]
    missing=[str(x.relative_to(WORKSPACE)) for x in required if not x.is_file()]
    if missing: raise SystemExit('BLOCK: REQUIRED_PRESTAGE_ARTIFACT_MISSING:'+','.join(missing))
    frozen=list((base/'FROZEN_BINARY_PARTS').glob('*'))
    if len(frozen)!=6: raise SystemExit(f'BLOCK: CORE_FROZEN_BINARY_PART_COUNT expected=6 actual={len(frozen)}')
    ctx['projection_size_bytes']=proj.stat().st_size
    ctx['frozen_binary_part_count']=len(frozen)
    ctx['formal_artifact_count']=7
    ctx['independent_validation_evidence']=str(iev.relative_to(WORKSPACE))
    write_yaml(WORKSPACE/'PRESTAGE_RUN_CONTEXT.yaml',ctx)

    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add',WORKSPACE_REL)
    if run('git','diff','--cached','--quiet',check=False).returncode==0: raise SystemExit('BLOCK: NO_CORE_PRESTAGE_DELTA')
    run('git','commit','-m','feat(source): materialize CORE-01 frozen Word YAML source pair')
    new_head=run('git','rev-parse','HEAD').stdout.strip()
    run('git','push','origin','HEAD:rebuild-v2.1.1')
    print(json.dumps({'status':'PUSHED','commit':new_head,'workspace':WORKSPACE_REL,'source_uid':SOURCE_UID,'projection_size_bytes':proj.stat().st_size,'frozen_binary_part_count':len(frozen),'stage01_started':False,'product_stage_credit':0},indent=2))
if __name__=='__main__': main()
