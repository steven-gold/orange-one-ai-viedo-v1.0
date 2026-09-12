#!/usr/bin/env python3
from pathlib import Path
import hashlib, yaml

root=Path('.')
package='2bfeed2ec9bc6eac9f34fdd5eb43e2f76f1e78682c4b81bebb9e4a3e1084eecd'
trust='787b2be721c0d51e8fe595ceaeeb0c80a03e692952b6ff2fc139c6a914f089ee'

def die(msg): raise SystemExit(msg)
def gblob(p):
    b=p.read_bytes()
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def chash(d):
    x=dict(d)
    for k in ('content_hash','artifact_hash','blueprint_hash','binding_hash','structure_manifest_hash'):
        x.pop(k,None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True).encode()).hexdigest()

cur=yaml.safe_load((root/'GOVERNANCE_CURRENT.yaml').read_text())
base=yaml.safe_load((root/'REBUILD_BRANCH_BASELINE.yaml').read_text())
lock=yaml.safe_load((root/'11_EVIDENCE/audit/GOVERNANCE_STAGE_LOCK.yaml').read_text())
sealed=yaml.safe_load((root/'11_EVIDENCE/audit/SEALED_GOVERNANCE_TEST_BASELINE.yaml').read_text())
assert cur['normative_authority']['version']=='v2.1.5'
assert cur['normative_authority']['package_sha256']==package
assert cur['normative_authority']['external_trust_root_sha256']==trust
assert cur['normative_authority']['normative_edit_allowed'] is False
assert cur['test_runtime']['runtime_uid']=='ACPOS-GOV-TEST-v2.1.5-STAGE1'
assert cur['test_runtime']['expected_stage1_minimal_control']=='31/31_PASS'
assert base['governance_test']['version']=='v2.1.5'
assert base['prior_extraction_reuse']=='FORBIDDEN'
assert lock['lock_state']=='USER_FROZEN_READ_ONLY'
assert lock['normative_edit_after_lock']=='FORBIDDEN'
assert sealed['sealed_governance']['version']=='v2.1.5'
assert sealed['sealed_governance']['package_sha256']==package
assert sealed['normative_mutation_allowed'] is False
assert sealed['verified_test_summary']['stage1_minimal_control']=='31/31_PASS'

forbidden=[p for p in [root/'app',root/'src',root/'pages',root/'public'] if p.exists()]
if forbidden: die('premature website implementation: '+', '.join(map(str,forbidden)))
stale_names={'CORE_ASSET_SOURCE_INVENTORY.yaml','EXTRACTION_LEDGER_CORE_ASSET_001.yaml','GOVERNANCE_EXTRACTION_LEDGER_001.yaml','SOURCE_DOMAIN_DECOMPOSITION.yaml','GOVERNANCE_DEFECT_LEDGER.yaml','GOVERNANCE_TEST_RUNTIME_SYNC_v2.1.4.yaml','PHASE_CONTAMINATION_LEDGER.yaml','REBUILD_BRANCH_ISOLATION.yaml'}
stale=[str(p) for p in root.rglob('*') if p.is_file() and p.name in stale_names]
if stale: die('stale current-path artifacts remain: '+', '.join(stale))
legacy=[str(p) for p in root.rglob('*') if p.is_file() and ('legacy_new' in p.parts or 'stage1_runtime_bundle.tar.gz.b64' in p.name)]
if legacy: die('legacy transport/source residue remains: '+', '.join(legacy))
if (root/'governance/test-runtime/v2.1.4').exists(): die('superseded v2.1.4 runtime remains in current tree')

runroot=root/'00_SOURCE_INTAKE/fresh_run_002'
if not runroot.is_dir(): die('fresh_run_002 foundation missing')
siblings=[p.name for p in (root/'00_SOURCE_INTAKE').iterdir() if p.name!='fresh_run_002']
if siblings: die('unexpected current intake sibling: '+repr(siblings))
state=yaml.safe_load((runroot/'EXECUTION_STATE.yaml').read_text())
run=yaml.safe_load((runroot/'RUN_MANIFEST.yaml').read_text())
if run.get('governance',{}).get('version')!='v2.1.5': die('fresh run governance version mismatch')
if run.get('governance',{}).get('normative_edit_allowed') is not False: die('fresh run governance not frozen')

st=state.get('state')
if st=='FOUNDATION_READY_NOT_EXECUTED':
    if (runroot/'00_SOURCE_INTAKE/RAW_SOURCE').exists(): die('raw source exists before second extraction start')
elif st in {'RAW_SOURCE_REFERENCE_CAPTURED','SOURCE_STRUCTURE_ENUMERATION_COMPLETED'}:
    intake=runroot/'00_SOURCE_INTAKE'
    refs=yaml.safe_load((intake/'RAW_SOURCE_REFERENCE_MANIFEST.yaml').read_text())
    cap=yaml.safe_load((intake/'RAW_SOURCE_CAPTURE_STATE.yaml').read_text())
    if cap.get('state')!='CAPTURE_CLOSED': die('raw capture not terminal closed')
    if cap.get('next_step')!='SOURCE_STRUCTURE_ENUMERATION': die('raw capture next step mismatch')
    if cap.get('recapture_allowed') is not False: die('closed raw capture remains writable')
    records=refs.get('records') or []
    expected=[]; rec_by_uid={}
    for rec in records:
        uid=rec.get('source_uid')
        if not uid or uid in rec_by_uid: die('duplicate/missing raw source uid: '+str(uid))
        rec_by_uid[uid]=rec
        if rec.get('source_domain_scope')=='MIXED_PAGE_VISUAL' and rec.get('source_role')!='MIXED_PAGE_VISUAL_SOURCE_INPUT':
            die('mixed source role not neutral: '+str(uid))
        p=runroot/rec['target_path']
        if not p.is_file(): die('missing raw source: '+str(p))
        got=gblob(p)
        if got!=rec.get('source_git_blob_sha') or got!=rec.get('target_git_blob_sha'): die('exact blob mismatch: '+str(p))
        if rec.get('content_mutated') is not False: die('raw source marked mutated: '+str(uid))
        expected.append(rec['target_path'])
    rawroot=runroot/'00_SOURCE_INTAKE/RAW_SOURCE'
    actual=sorted(p.relative_to(runroot).as_posix() for p in rawroot.rglob('*') if p.is_file())
    if sorted(expected)!=actual: die('raw source directory purity mismatch: '+repr(actual))

    if st=='SOURCE_STRUCTURE_ENUMERATION_COMPLETED':
        if run.get('status')!='SOURCE_STRUCTURE_ENUMERATION_COMPLETED': die('run manifest status mismatch')
        pol=run.get('execution_policy') or {}
        if pol.get('source_structure_enumeration')!='COMPLETED_34_OF_34_FULL_SOURCE_PROVEN': die('structure completion mismatch')
        if pol.get('source_segment_mapping')!='NOT_EXECUTED': die('segment mapping started early')
        if pol.get('source_domain_decomposition')!='NOT_EXECUTED': die('domain decomposition started early')
        if state.get('source_structure_enumeration_started') is not True or state.get('source_structure_enumeration_completed') is not True:
            die('execution state does not close enumeration')
        if state.get('source_segment_mapping_started') is not False: die('segment mapping contamination')
        if (intake/'SOURCE_SEGMENT_MAP.yaml').exists(): die('SOURCE_SEGMENT_MAP exists before explicit start')

        struct=yaml.safe_load((intake/'SOURCE_STRUCTURE_MANIFEST.yaml').read_text())
        if struct.get('artifact_type')!='SOURCE_STRUCTURE_MANIFEST': die('structure artifact type mismatch')
        if struct.get('run_uid')!='FRESH-RUN-002' or struct.get('step_uid')!='SOURCE_STRUCTURE_ENUMERATION': die('structure identity mismatch')
        if struct.get('classification_started') is not False or struct.get('segment_mapping_started') is not False: die('classification contamination')
        sources=struct.get('sources') or []
        by_uid={s.get('source_uid'):s for s in sources if s.get('source_uid')}
        if len(by_uid)!=len(sources): die('duplicate/missing source uid in structure')
        if set(by_uid)!=set(rec_by_uid): die('structure source set mismatch')

        ids=set(); total=req_count=ref_count=0
        forbidden_node_fields={'planning_domain','responsibility_uid','disposition','target_artifact_uids','classification'}
        for uid,rec in rec_by_uid.items():
            s=by_uid[uid]
            if s.get('source_revision')!=refs.get('source_revision'): die('source revision mismatch: '+uid)
            if s.get('source_git_blob_sha')!=rec.get('source_git_blob_sha'): die('source blob mismatch: '+uid)
            if s.get('raw_source_path')!=rec.get('target_path'): die('raw path mismatch: '+uid)
            if s.get('enumeration_method')!='PYYAML_SAFE_LOAD_TOP_LEVEL_MAPPING_ENUMERATION': die('enumeration method mismatch: '+uid)
            if s.get('enumeration_tool')!='PyYAML==6.0.2': die('enumeration tool mismatch: '+uid)
            if s.get('enumeration_state')!='FULL_SOURCE_ENUMERATION_PROVEN': die('enumeration not proven: '+uid)
            if not (runroot/s.get('evidence_ref','')).is_file(): die('enumeration evidence missing: '+uid)
            if s.get('structure_manifest_hash')!=chash(s): die('structure hash mismatch: '+uid)

            parsed=yaml.safe_load((runroot/rec['target_path']).read_text(encoding='utf-8'))
            if not isinstance(parsed,dict): die('raw YAML top-level is not mapping: '+uid)
            actual_keys=list(parsed.keys())
            nodes=s.get('observed_nodes') or []
            if s.get('observed_node_count')!=len(nodes): die('observed count mismatch: '+uid)
            declared=[n.get('source_top_level_key') for n in nodes]
            if declared!=actual_keys: die('top-level enumeration mismatch: '+uid+' declared='+repr(declared)+' actual='+repr(actual_keys))
            for n in nodes:
                nid=n.get('source_node_uid'); key=n.get('source_top_level_key')
                if not nid or nid in ids: die('duplicate/missing source_node_uid: '+str(nid))
                ids.add(nid)
                if n.get('source_ref')!='$.'+str(key): die('source_ref mismatch: '+str(nid))
                if n.get('classification_state')!='UNCLASSIFIED_OBSERVED_SOURCE': die('premature classification: '+str(nid))
                relevance=n.get('governance_relevance')
                if relevance not in {'REQUIRED','REFERENCE_ONLY','NON_NORMATIVE'}: die('invalid relevance: '+str(nid))
                if relevance=='REQUIRED': req_count+=1
                elif relevance=='REFERENCE_ONLY': ref_count+=1
                if forbidden_node_fields.intersection(n): die('classification fields present during enumeration: '+str(nid))
            total+=len(nodes)

        comp=struct.get('completion') or {}
        if struct.get('source_count')!=3 or len(sources)!=3: die('source count is not exact 3')
        if struct.get('observed_node_count')!=34 or total!=34: die('node count is not exact 34: '+str(total))
        if req_count!=29 or ref_count!=5: die(f'relevance count mismatch required={req_count} reference={ref_count}')
        if comp.get('enumeration_state')!='FULL_SOURCE_ENUMERATION_PROVEN': die('completion state mismatch')
        if comp.get('required_nodes')!=29 or comp.get('reference_only_nodes')!=5: die('completion relevance counters mismatch')
        if comp.get('unclassified_observed_nodes')!=34 or comp.get('classified_nodes')!=0: die('classification contamination')
        if comp.get('missing_nodes')!=0 or comp.get('extra_nodes')!=0 or comp.get('duplicate_source_node_uids')!=0: die('completeness counters not zero-clean')
        if comp.get('next_step')!='SOURCE_SEGMENT_MAPPING': die('structure next step mismatch')

        ev=yaml.safe_load((intake/'evidence/SOURCE_STRUCTURE_ENUMERATION_EVIDENCE.yaml').read_text())
        if ev.get('status')!='OBSERVED_FULL_SOURCE_STRUCTURE': die('evidence status mismatch')
        if ev.get('raw_source_count')!=3 or ev.get('observed_node_count')!=34: die('evidence count mismatch')
        if ev.get('next_step')!='SOURCE_SEGMENT_MAPPING': die('evidence next step mismatch')
        proof=ev.get('boundary_proof') or {}
        for k in ('raw_source_bytes_mutated','page_visual_classification_started','source_segment_mapping_started','domain_extraction_started','blueprint_materialization_started','website_construction_started','deployment_started'):
            if proof.get(k) is not False: die('boundary proof failed: '+k)
        print('PASS: SOURCE_STRUCTURE_ENUMERATION 34/34; required=29; reference_only=5; classified=0')
else:
    die('unexpected fresh-run state: '+str(st))

garbage=[]
for p in root.rglob('*'):
    if not p.is_file() or '.git' in p.parts: continue
    if p.name=='.DS_Store' or p.suffix in {'.pyc','.pyo'} or '__pycache__' in p.parts or p.name.endswith(('.tmp','.bak','~')):
        garbage.append(str(p))
if garbage: die('garbage detected: '+', '.join(garbage))
print('PASS: v2.1.5 seal/current/fresh-workspace contract valid')
