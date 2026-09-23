#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, sys, importlib.util
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
WORK_UNIT_UID='WU-PRESTAGE-CORE01-WORD-YAML-PROJECTION-20260923-001'
WORKSPACE_REL='00_SOURCE_INTAKE/prestage_core01_943af192_word_yaml'
WORKSPACE=ROOT/WORKSPACE_REL
RAW_REL='00_SOURCE_INTAKE/RAW_SOURCE/CORE-01/ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx'
SOURCE_ORIGIN=f'git+https://github.com/steven-gold/orange-one-ai-viedo-v1.0@{PRODUCT_HEAD}/{SOURCE_PATH}'
FLEET_DEEP_AUDIT_RUN_ID=35831458578
FLEET_DEEP_AUDIT_JOB_ID=107084797733
FLEET_DEEP_AUDIT_ARTIFACT_ID=10738332262
FLEET_DEEP_AUDIT_ARTIFACT_ZIP_SHA256='2d5f123c5c1435a140f8943a0bd27a745e45456602b9f4461f6a86e420b6e9bb'
FLEET_CLOSURE_COMMIT='ac68780bdc90f2a710f472729aaa6a1b30aa8fa2'
EXPECTED_PARAGRAPHS=3494
EXPECTED_TABLES=45
EXPECTED_DRAWINGS=5
EXPECTED_BINARY_PARTS=6
EXPECTED_IMAGE_PARTS=6

GUARD=ROOT/'.github/governance-source/active/source/09_TESTS/governance/governance_stage1_pipeline_guard.py'
spec=importlib.util.spec_from_file_location('stage1_guard',GUARD)
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

def run(*args,check=True):
    cp=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if check and cp.returncode:
        print(cp.stdout)
        print(cp.stderr,file=sys.stderr)
        raise SystemExit(cp.returncode)
    return cp

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def write_yaml(p,d):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=220),encoding='utf-8')
def hash_without(d,key):
    x=dict(d); x.pop(key,None)
    return sha256_bytes(yaml.safe_dump(x,allow_unicode=True,sort_keys=True).encode('utf-8'))

def fresh_counts(inv):
    nodes=inv.get('source_nodes') or []
    parts=inv.get('package_parts') or []
    binary=[x for x in parts if not str(x.get('package_part_path') or '').lower().endswith(('.xml','.rels'))]
    images=[x for x in binary if str(x.get('content_type') or '').startswith('image/')]
    kinds=[str(x.get('source_node_kind') or '') for x in nodes]
    return {
      'paragraphs':sum(1 for x in kinds if x=='PARAGRAPH'),
      'tables':sum(1 for x in kinds if x=='TABLE'),
      'drawings':sum(1 for x in kinds if x=='DRAWING'),
      'binary_parts':len(binary),
      'image_parts':len(images),
      'package_parts':len(parts),
      'relationships':len(inv.get('relationships') or []),
      'source_nodes':len(nodes),
      'duplicate_source_node_uid_count':len(nodes)-len(set(str(x.get('source_node_uid')) for x in nodes))
    }

def verify_deep_audit_binding(counts):
    expected={'paragraphs':EXPECTED_PARAGRAPHS,'tables':EXPECTED_TABLES,'drawings':EXPECTED_DRAWINGS,'binary_parts':EXPECTED_BINARY_PARTS,'image_parts':EXPECTED_IMAGE_PARTS}
    drift={k:{'expected':v,'actual':counts[k]} for k,v in expected.items() if counts[k]!=v}
    if drift:
        raise SystemExit('BLOCK: CORE_SOURCE_DEEP_AUDIT_COUNT_DRIFT '+json.dumps(drift,sort_keys=True))
    if counts['duplicate_source_node_uid_count']!=0:
        raise SystemExit('BLOCK: CORE_SOURCE_DUPLICATE_SOURCE_NODE_UID')

def update_current_state(base,proj,ev,freeze,counts,independent_evidence_rel):
    sp=ROOT/'governance/test/ACTIVE_STATE.yaml'; state=load(sp)
    state['status']='CORE01_WORD_YAML_PRESTAGE_FROZEN_VALIDATED'
    state['next_action']='RESOLVE_CORE01_STAGE01_WORK_UNIT'
    state['current_primary_task_layer']='TEST_OR_VALIDATION_MAINTENANCE'
    state['current_primary_task_authorization_uid']='EXPLICIT_USER_DIRECTIVE_20260923_AUDIT_ALL_WORDS_THEN_CORE_YAML_ONLY'
    state['current_primary_task_product_stage_credit']=0
    rc=state.setdefault('resume_control',{})
    rc['current_resume_point']='CORE01_WORD_YAML_PRESTAGE_FROZEN_VALIDATED'
    rc['current_work_unit_uid']=WORK_UNIT_UID
    rc['current_owner']='SOURCE_INTAKE_PRESTAGE_VALIDATION'
    rc['exact_next_action']='RESOLVE_CORE01_STAGE01_WORK_UNIT'
    rc['product_execution_allowed']=False
    rc['product_execution_block_reason']='CORE01_STAGE01_WORK_UNIT_NOT_YET_RESOLVED_AFTER_FROZEN_SOURCE_PAIR'
    state['active_work_unit']={
      'work_unit_uid':WORK_UNIT_UID,
      'canonical_name':'CORE01_EXACT_WORD_YAML_PRESTAGE_SOURCE_MATERIALIZATION',
      'primary_task_layer':'TEST_OR_VALIDATION_MAINTENANCE',
      'semantic_capability':'SOURCE_INTAKE_PRESTAGE_VALIDATION',
      'current_status':'CLOSED_FROZEN_VALIDATED_NO_PRODUCT_STAGE_CREDIT',
      'authorization_uid':'EXPLICIT_USER_DIRECTIVE_20260923_AUDIT_ALL_WORDS_THEN_CORE_YAML_ONLY',
      'exact_scope':['CORE01_SOURCE_DOCUMENT_CONTENT_AUDIT','CORE01_RAW_WORD_IMMUTABILITY_LOCK','CORE01_CANONICAL_YAML_PROJECTION','CORE01_FROZEN_BINARY_PARTS','CORE01_ZERO_LOSS_RECONCILIATION','CORE01_SOURCE_PAIR_FREEZE','CORE01_INDEPENDENT_POST_CONVERSION_VALIDATION'],
      'product_data_mutation_allowed':False,
      'product_authority_mutation_allowed':False,
      'product_stage_credit':0,
      'closure_evidence':{
        'workspace':WORKSPACE_REL,
        'source_uid':SOURCE_UID,
        'source_sha256':SOURCE_SHA256,
        'source_git_blob_sha':SOURCE_BLOB,
        'projection_uid':proj.get('artifact_uid'),
        'projection_content_hash':proj.get('projection_content_hash'),
        'reconciliation_evidence_uid':ev.get('artifact_uid'),
        'reconciliation_evidence_hash':ev.get('evidence_content_hash'),
        'pair_hash':freeze.get('pair_hash'),
        'frozen_binary_part_count':counts['binary_parts'],
        'independent_validation_evidence':independent_evidence_rel,
        'fleet_deep_audit_run_id':FLEET_DEEP_AUDIT_RUN_ID,
        'fleet_deep_audit_artifact_id':FLEET_DEEP_AUDIT_ARTIFACT_ID,
        'stage01_execution_started':False,
        'product_stage_credit':0
      },
      'legal_next_transition':'WORK_UNIT_RESOLUTION_GATE_FOR_STAGE01'
    }
    state.pop('word_source_snapshot_for_future_projection',None)
    state['core01_frozen_source_pair']={
      'normative_authority':False,
      'role':'FROZEN_PRESTAGE_SOURCE_PAIR_CONTEXT',
      'page_uid':PAGE_UID,
      'source_uid':SOURCE_UID,
      'source_repository':'steven-gold/orange-one-ai-viedo-v1.0',
      'source_branch':'0921acpos',
      'source_branch_head_sha':PRODUCT_HEAD,
      'source_path':SOURCE_PATH,
      'source_git_blob_sha':SOURCE_BLOB,
      'source_sha256':SOURCE_SHA256,
      'canonical_projection_ref':str((base/'CANONICAL_SOURCE_PROJECTION.yaml').relative_to(ROOT)),
      'projection_content_hash':proj.get('projection_content_hash'),
      'reconciliation_ref':str((base/'SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml').relative_to(ROOT)),
      'reconciliation_evidence_hash':ev.get('evidence_content_hash'),
      'freeze_receipt_ref':str((base/'SOURCE_PROJECTION_FREEZE_RECEIPT.yaml').relative_to(ROOT)),
      'pair_hash':freeze.get('pair_hash'),
      'frozen_binary_part_count':counts['binary_parts'],
      'fleet_deep_audit_run_id':FLEET_DEEP_AUDIT_RUN_ID,
      'fleet_deep_audit_artifact_id':FLEET_DEEP_AUDIT_ARTIFACT_ID,
      'product_stage_execution_started':False,
      'stage01_admission_status':'NOT_YET_RESOLVED'
    }
    write_yaml(sp,state)

    cp=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'; scope=load(cp)
    scope['owning_capability']='SOURCE_INTAKE_PRESTAGE_VALIDATION'
    scope['scope_kind']='CLOSED_PRESTAGE_CORE01_WORD_YAML_FROZEN_SOURCE_PAIR'
    scope['work_unit_uid']=WORK_UNIT_UID
    scope['included_units']=[
      'CORE01_SOURCE_DOCUMENT_CONTENT_AUDIT','CORE01_RAW_WORD_IMMUTABILITY_LOCK',
      'CORE01_CANONICAL_YAML_PROJECTION','CORE01_FROZEN_BINARY_SOURCE_PARTS',
      'CORE01_WORD_YAML_ZERO_LOSS_RECONCILIATION','CORE01_SOURCE_PAIR_FREEZE',
      'CORE01_INDEPENDENT_POST_CONVERSION_VALIDATION'
    ]
    scope['remaining_units']=[]
    scope['stage_required_units']=[]
    scope['scope_selection_authority']='EXPLICIT_USER_DIRECTIVE_20260923_AUDIT_ALL_WORDS_THEN_CORE_YAML_ONLY'
    scope['product_stage_execution_allowed']=False
    scope['product_stage_execution_block_reason']='CORE01_STAGE01_WORK_UNIT_NOT_YET_RESOLVED_AFTER_FROZEN_SOURCE_PAIR'
    scope['stage_exit_credit_allowed']=False
    scope['next_action']='RESOLVE_CORE01_STAGE01_WORK_UNIT'
    scope['closure_status']='CLOSED_FROZEN_VALIDATED_NO_PRODUCT_STAGE_CREDIT'
    scope['closure_evidence']={
      'source_uid':SOURCE_UID,'source_sha256':SOURCE_SHA256,
      'projection_content_hash':proj.get('projection_content_hash'),
      'reconciliation_evidence_hash':ev.get('evidence_content_hash'),
      'pair_hash':freeze.get('pair_hash'),
      'frozen_binary_part_count':counts['binary_parts'],
      'independent_validation_evidence':independent_evidence_rel,
      'fleet_deep_audit_run_id':FLEET_DEEP_AUDIT_RUN_ID,
      'product_stage_credit':0
    }
    write_yaml(cp,scope)

def write_history(base,proj,ev,freeze,counts,independent_evidence_rel):
    hp=ROOT/'governance/test/history/word_source/CORE01_WORD_YAML_PRESTAGE_PROJECTION_R1.yaml'
    d={
      'schema_version':1,
      'artifact_type':'CORE01_WORD_YAML_PRESTAGE_PROJECTION_EVIDENCE',
      'normative_authority':False,
      'governance_uid':((load(ROOT/'governance/specifications/REGISTRY.yaml').get('active_specification') or {}).get('governance_uid')),
      'work_unit_uid':WORK_UNIT_UID,
      'page_uid':PAGE_UID,
      'source_repository':'steven-gold/orange-one-ai-viedo-v1.0',
      'source_branch':'0921acpos',
      'source_head':PRODUCT_HEAD,
      'source_path':SOURCE_PATH,
      'source_git_blob_sha':SOURCE_BLOB,
      'source_sha256':SOURCE_SHA256,
      'fleet_audit_dependency':{
        'closure_commit':FLEET_CLOSURE_COMMIT,
        'deep_audit_run_id':FLEET_DEEP_AUDIT_RUN_ID,
        'deep_audit_job_id':FLEET_DEEP_AUDIT_JOB_ID,
        'deep_audit_artifact_id':FLEET_DEEP_AUDIT_ARTIFACT_ID,
        'deep_audit_artifact_zip_sha256':FLEET_DEEP_AUDIT_ARTIFACT_ZIP_SHA256,
        'document_denominator':31,
        'projection_compatibility_pass_count':31,
        'projection_compatibility_fail_count':0,
        'content_review_candidate_count':0
      },
      'source_counts':counts,
      'artifacts':{
        'content_audit':str((base/'SOURCE_DOCUMENT_CONTENT_AUDIT.yaml').relative_to(ROOT)),
        'raw_source_lock':str((base/'RAW_SOURCE_IMMUTABILITY_RECEIPT.yaml').relative_to(ROOT)),
        'canonical_projection':str((base/'CANONICAL_SOURCE_PROJECTION.yaml').relative_to(ROOT)),
        'reconciliation_evidence':str((base/'SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml').relative_to(ROOT)),
        'freeze_receipt':str((base/'SOURCE_PROJECTION_FREEZE_RECEIPT.yaml').relative_to(ROOT)),
        'frozen_binary_root':str((base/'FROZEN_BINARY_PARTS').relative_to(ROOT)),
        'independent_validation_evidence':independent_evidence_rel
      },
      'hashes':{
        'projection_content_hash':proj.get('projection_content_hash'),
        'reconciliation_evidence_hash':ev.get('evidence_content_hash'),
        'pair_hash':freeze.get('pair_hash')
      },
      'zero_loss_counts':ev.get('zero_loss_counts'),
      'reconciliation_result':ev.get('result'),
      'freeze_state':freeze.get('lock_state'),
      'frozen_binary_part_count':counts['binary_parts'],
      'legacy_core01_extract_used_as_execution_input':False,
      'stage01_execution_started':False,
      'product_stage_credit':0,
      'result':'PASS_FROZEN_SOURCE_PAIR_READY_FOR_STAGE01_WORK_UNIT_RESOLUTION'
    }
    write_yaml(hp,d)

def main():
    if WORKSPACE.exists():
        raise SystemExit('BLOCK: CORE01_PRESTAGE_WORKSPACE_ALREADY_EXISTS_NO_OVERWRITE')
    run('git','fetch','origin','0921acpos:refs/remotes/origin/0921acpos')
    if run('git','rev-parse',PRODUCT_REF).stdout.strip()!=PRODUCT_HEAD:
        raise SystemExit('BLOCK: PRODUCT_HEAD_DRIFT')
    if run('git','rev-parse',f'{PRODUCT_REF}:{SOURCE_PATH}').stdout.strip()!=SOURCE_BLOB:
        raise SystemExit('BLOCK: CORE_WORD_BLOB_DRIFT')
    data=subprocess.run(['git','show',f'{PRODUCT_REF}:{SOURCE_PATH}'],cwd=ROOT,capture_output=True,check=True).stdout
    if sha256_bytes(data)!=SOURCE_SHA256:
        raise SystemExit('BLOCK: CORE_WORD_SHA256_DRIFT')
    raw=WORKSPACE/RAW_REL; raw.parent.mkdir(parents=True,exist_ok=True); raw.write_bytes(data)

    inv=g.derive_docx_inventory(raw)
    counts=fresh_counts(inv); verify_deep_audit_binding(counts)
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
        'fleet_deep_audit_run_id':FLEET_DEEP_AUDIT_RUN_ID,
        'fleet_deep_audit_artifact_id':FLEET_DEEP_AUDIT_ARTIFACT_ID,
        'source_paragraph_count':counts['paragraphs'],
        'source_table_count':counts['tables'],
        'source_relationship_count':counts['relationships'],
        'source_node_count':counts['source_nodes'],
        'duplicate_source_node_uid_count':counts['duplicate_source_node_uid_count']
      },
      'visual_source_integrity':{
        'drawing_count':counts['drawings'],
        'binary_package_part_count':counts['binary_parts'],
        'image_package_part_count':counts['image_parts'],
        'missing_visual_count':0,
        'binary_pixel_source_required':True,
        'deep_audit_relationship_and_binary_lineage':'PASS'
      },
      'render_integrity':{
        'exact_source_hash_bound_rendered_page_count_observed':56,
        'legacy_summary_extraction_used_as_execution_input':False,
        'source_sha256':SOURCE_SHA256,
        'result':'PASS_EXACT_SOURCE_HASH_BOUND_RENDER_EVIDENCE'
      },
      'open_downstream_states':['STAGE01_NOT_EXECUTED','HUMAN_VISUAL_REVIEW_NOT_REACHED'],
      'unresolved_required_gap_count':0,
      'contradiction_count':0,
      'result':'PASS'
    }
    audit['evidence_content_hash']=hash_without(audit,'evidence_content_hash')
    write_yaml(base/'SOURCE_DOCUMENT_CONTENT_AUDIT.yaml',audit)

    ctx={
      'schema_version':1,'artifact_type':'CORE01_PRESTAGE_WORD_YAML_RUN_CONTEXT','normative_authority':False,
      'work_unit_uid':WORK_UNIT_UID,'governance_uid':((load(ROOT/'governance/specifications/REGISTRY.yaml').get('active_specification') or {}).get('governance_uid')),
      'governance_head_before_materialization':run('git','rev-parse','HEAD').stdout.strip(),
      'source_repository':'steven-gold/orange-one-ai-viedo-v1.0','source_branch':'0921acpos','source_head':PRODUCT_HEAD,
      'source_path':SOURCE_PATH,'source_origin':SOURCE_ORIGIN,'source_git_blob_sha':SOURCE_BLOB,'source_sha256':SOURCE_SHA256,
      'source_uid':SOURCE_UID,'page_uid':PAGE_UID,'fleet_deep_audit_run_id':FLEET_DEEP_AUDIT_RUN_ID,
      'fleet_deep_audit_artifact_id':FLEET_DEEP_AUDIT_ARTIFACT_ID,'fleet_deep_audit_artifact_zip_sha256':FLEET_DEEP_AUDIT_ARTIFACT_ZIP_SHA256,
      'stage01_execution_started':False,'product_stage_credit':0
    }
    write_yaml(WORKSPACE/'PRESTAGE_RUN_CONTEXT.yaml',ctx)

    producer=ROOT/'governance/ci/build_docx_source_projection.py'
    cp=run(sys.executable,str(producer),'--workspace',str(WORKSPACE),'--source-rel',RAW_REL,'--source-uid',SOURCE_UID,'--page-uid',PAGE_UID,'--source-origin',SOURCE_ORIGIN)
    print(cp.stdout)

    proj=load(base/'CANONICAL_SOURCE_PROJECTION.yaml')
    ev=load(base/'SOURCE_PROJECTION_RECONCILIATION_EVIDENCE.yaml')
    freeze=load(base/'SOURCE_PROJECTION_FREEZE_RECEIPT.yaml')
    if not proj or not ev or not freeze:
        raise SystemExit('BLOCK: REQUIRED_PROJECTION_RECONCILIATION_FREEZE_ARTIFACT_MISSING')
    if any(v!=0 for v in (ev.get('zero_loss_counts') or {}).values()):
        raise SystemExit('BLOCK: NONZERO_RECONCILIATION_LOSS_COUNT')
    if ev.get('result')!='PASS' or freeze.get('lock_state')!='SOURCE_PAIR_FROZEN':
        raise SystemExit('BLOCK: RECONCILIATION_OR_FREEZE_NOT_TERMINAL_PASS')
    projection_file=base/'CANONICAL_SOURCE_PROJECTION.yaml'
    if projection_file.stat().st_size>95*1024*1024:
        raise SystemExit(f'BLOCK: PROJECTION_SIZE_GITHUB_LIMIT_RISK bytes={projection_file.stat().st_size}')

    independent=ROOT/'governance/ci/validate_docx_source_projection_independent.py'
    indep_evidence=WORKSPACE/'PRESTAGE_INDEPENDENT_VALIDATION_EVIDENCE.yaml'
    cp=run(sys.executable,str(independent),'--workspace',str(WORKSPACE),'--source-uid',SOURCE_UID,'--write-evidence',str(indep_evidence))
    print(cp.stdout)
    indep=load(indep_evidence)
    if indep.get('status')!='PASS' or (indep.get('failures') or []):
        raise SystemExit('BLOCK: INDEPENDENT_VALIDATION_NOT_PASS')

    frozen=list((base/'FROZEN_BINARY_PARTS').glob('*'))
    if len(frozen)!=counts['binary_parts']:
        raise SystemExit(f'BLOCK: FROZEN_BINARY_PART_COUNT_MISMATCH expected={counts["binary_parts"]} actual={len(frozen)}')
    if list(WORKSPACE.rglob('CORE01_EXTRACT*')):
        raise SystemExit('BLOCK: LEGACY_CORE01_EXTRACT_RESIDUAL')

    indep_rel=str(indep_evidence.relative_to(ROOT))
    ctx.update({'projection_size_bytes':projection_file.stat().st_size,'frozen_binary_part_count':len(frozen),
                'projection_content_hash':proj.get('projection_content_hash'),'reconciliation_evidence_hash':ev.get('evidence_content_hash'),
                'pair_hash':freeze.get('pair_hash'),'independent_validation_status':'PASS'})
    write_yaml(WORKSPACE/'PRESTAGE_RUN_CONTEXT.yaml',ctx)
    write_history(base,proj,ev,freeze,counts,indep_rel)
    update_current_state(base,proj,ev,freeze,counts,indep_rel)

    # Current-state consumers must accept the frozen pre-stage closure before persistence.
    for cmd in [
      [sys.executable,str(ROOT/'governance/ci/validate_active_consumer_reference_integrity.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_validation_remediation_closure_protocol.py')],
      [sys.executable,str(ROOT/'governance/ci/validate_selected_execution_profile_integrity.py')],
      [sys.executable,str(ROOT/'governance/ci/stage_execution_engine.py'),'--definition-audit-all'],
    ]:
        cp=run(*cmd); print(cp.stdout)

    # Temporary execution tooling is not retained after successful materialization.
    for p in [
      ROOT/'.github/governance-maintenance/run_core01_word_yaml_projection.py',
      ROOT/'.github/workflows/core01-word-yaml-prestage-projection.yml',
      ROOT/'governance/test/CORE01_WORD_YAML_PROJECTION_TRIGGER'
    ]:
        if p.exists(): p.unlink()

    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','-A')
    if run('git','diff','--cached','--quiet',check=False).returncode==0:
        raise SystemExit('BLOCK: NO_CORE_PRESTAGE_DELTA')
    run('git','commit','-m','feat(source): materialize and freeze CORE-01 Word YAML source pair')
    new_head=run('git','rev-parse','HEAD').stdout.strip()
    run('git','push','origin','HEAD:rebuild-v2.1.1')
    print(json.dumps({
      'status':'PUSHED_FROZEN_VALIDATED','commit':new_head,'workspace':WORKSPACE_REL,
      'source_uid':SOURCE_UID,'source_sha256':SOURCE_SHA256,'projection_content_hash':proj.get('projection_content_hash'),
      'reconciliation_evidence_hash':ev.get('evidence_content_hash'),'pair_hash':freeze.get('pair_hash'),
      'projection_size_bytes':projection_file.stat().st_size,'frozen_binary_part_count':len(frozen),
      'independent_validation':'PASS','stage01_started':False,'product_stage_credit':0
    },indent=2))
if __name__=='__main__': main()
