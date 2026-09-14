#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json, re, sys, yaml

FORBIDDEN_EXPECTATION_KEYS={"should_fail","is_invalid","expected_status","expected_result","precomputed_blocker_count","expected_pass"}
FORBIDDEN_PARTS={"__pycache__",".next","dist","build","coverage","playwright-report","test-results","node_modules"}
FORBIDDEN_SUFFIXES={".pyc",".pyo",".tmp",".bak",".swp"}
FORBIDDEN_FILENAME_TOKENS={"new","final","latest","fixed","backup","copy","temp","old"}
REQUIRED_SOURCE_FACT_FILES={"SOURCE_CONTEXT_MANIFEST":"00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml","CONTENT_SUPERSESSION_CONFLICT_LEDGER":"00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml","SOURCE_DEPENDENCY_MAP":"00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml"}
DOMAINS={"PAGE_CONSTRUCTION","VISUAL_CONSTRUCTION"}
LEGAL_DISPOSITIONS={"CLASSIFIED","SHARED_FACT_REFERENCE","REFERENCE_ONLY","NOT_APPLICABLE"}
BLUEPRINT_BY_DOMAIN={"PAGE_CONSTRUCTION":"PAGE_BASE_BLUEPRINT","VISUAL_CONSTRUCTION":"VISUAL_BASE_BLUEPRINT"}
RAW_CAPTURE_MANIFEST='00_SOURCE_INTAKE/RAW_SOURCE_REFERENCE_MANIFEST.yaml'
RAW_CAPTURE_STATE='00_SOURCE_INTAKE/RAW_SOURCE_CAPTURE_STATE.yaml'
RAW_SOURCE_ROOT='00_SOURCE_INTAKE/RAW_SOURCE'
MIXED_SOURCE_SCOPE='MIXED_PAGE_VISUAL'
MIXED_SOURCE_ROLE='MIXED_PAGE_VISUAL_SOURCE_INPUT'

def load_yaml(p:Path): return yaml.safe_load(p.read_text(encoding='utf-8')) or {}
def sha256_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def file_sha(p:Path)->str: return sha256_bytes(p.read_bytes())
def git_blob_sha(p:Path)->str:
    b=p.read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def stable_hash_obj(obj)->str: return sha256_bytes(yaml.safe_dump(obj,allow_unicode=True,sort_keys=True).encode('utf-8'))
def content_hash(doc:dict)->str:
    d=dict(doc)
    for k in ('content_hash','artifact_hash','blueprint_hash','binding_hash','structure_manifest_hash'): d.pop(k,None)
    return stable_hash_obj(d)
def normative_hash(package_root:Path)->str|None:
    files=[package_root/f'12_DOCS/mother-spec/0{i}_{name}.md' for i,name in [(1,'BLUEPRINT_DESIGN_GOVERNANCE'),(2,'IMPLEMENTATION_DELIVERY_STANDARD'),(3,'EXECUTION_CONTROL_STANDARD'),(4,'AUDIT_PROGRESS_STANDARD')]]
    if not all(p.exists() for p in files): return None
    rows=[f"{p.relative_to(package_root).as_posix()}\0{file_sha(p)}" for p in files]
    return sha256_bytes("\n".join(rows).encode())
def walk_keys(obj):
    if isinstance(obj,dict):
        for k,v in obj.items(): yield str(k); yield from walk_keys(v)
    elif isinstance(obj,list):
        for v in obj: yield from walk_keys(v)
def fail_if_expectation_keys(obj,where,failures):
    for k in sorted({k for k in walk_keys(obj) if k in FORBIDDEN_EXPECTATION_KEYS}): failures.append(f'validator_directed_expectation:{where}:{k}')
def list_current_files(workspace:Path): return [p.relative_to(workspace).as_posix() for p in sorted(workspace.rglob('*')) if p.is_file()]

def validate_stage1_phase_boundary_state(state:dict):
    failures=[]
    segment_done=state.get('source_segment_mapping_completed') is True
    sf_started=state.get('source_fact_materialization_started') is True
    sf_done=state.get('source_fact_materialization_completed') is True
    cls_started=state.get('responsibility_classification_started') is True
    cls_done=state.get('responsibility_classification_completed') is True
    page_started=state.get('page_base_blueprint_started') is True
    page_done=state.get('page_base_blueprint_completed') is True
    visual_started=state.get('visual_base_blueprint_started') is True
    visual_done=state.get('visual_base_blueprint_completed') is True
    binding_started=state.get('blueprint_binding_started') is True
    binding_done=state.get('blueprint_binding_completed') is True
    ci=state.get('github_ci') or {}
    class_gate=ci.get('current_classification_gate')=='SUCCESS' or state.get('classification_gate_passed') is True
    page_gate=ci.get('current_page_blueprint_gate')=='SUCCESS' or state.get('page_base_blueprint_gate_passed') is True
    visual_gate=ci.get('current_visual_blueprint_gate')=='SUCCESS' or state.get('visual_base_blueprint_gate_passed') is True
    if sf_started and not segment_done: failures.append('source_fact_started_before_segment_mapping_closed')
    if sf_done and not sf_started: failures.append('source_fact_completed_without_start')
    early_before_sf=['domain_extraction_started','responsibility_classification_started','page_base_blueprint_started','visual_base_blueprint_started','blueprint_materialization_started','blueprint_binding_started']
    if not sf_done:
        for k in early_before_sf:
            if state.get(k) is True: failures.append('downstream_started_before_source_fact_closed:'+k)
    if cls_done and not cls_started: failures.append('classification_completed_without_start')
    if page_done and not page_started: failures.append('page_blueprint_completed_without_start')
    if visual_done and not visual_started: failures.append('visual_blueprint_completed_without_start')
    if binding_done and not binding_started: failures.append('blueprint_binding_completed_without_start')
    if page_started and not (cls_done and class_gate): failures.append('page_blueprint_started_without_classification_gate')
    if visual_started and not (page_done and page_gate): failures.append('visual_blueprint_started_without_page_blueprint_gate')
    if binding_started and not (page_done and page_gate and visual_done and visual_gate): failures.append('blueprint_binding_started_without_page_and_visual_gates')
    for k in ['website_construction_started','deployment_started']:
        if state.get(k) is True: failures.append('stage1_forbidden_phase_started:'+k)
    return failures

def validate_unresolved_authority_gaps(dep:dict, raw_source_uids:set[str]|None=None, expected_authority_refs:set[str]|None=None):
    failures=[]; gaps=dep.get('unresolved_authority_gaps') or []
    seen_uid=set(); seen_ref=set()
    if dep.get('invented_dependency_count',0)!=0: failures.append('invented_dependency_count_nonzero')
    for g in gaps:
        uid=g.get('gap_uid'); ref=g.get('authority_ref'); consumers=g.get('consumer_source_uids') or []; disp=g.get('disposition'); ev=g.get('authority_evidence_ref')
        if not uid or not ref or not consumers or not ev: failures.append('unresolved_authority_gap_required_identity_missing:'+str(uid or ref or '?'))
        if uid in seen_uid: failures.append('unresolved_authority_gap_uid_duplicate:'+str(uid))
        if ref in seen_ref: failures.append('unresolved_authority_ref_duplicate:'+str(ref))
        if uid: seen_uid.add(uid)
        if ref: seen_ref.add(ref)
        if disp!='UNRESOLVED_AUTHORITY_GAP': failures.append('unresolved_authority_gap_false_resolution:'+str(uid)+':'+str(disp))
        if g.get('resolved') is True or g.get('satisfied') is True or g.get('auto_filled') is True or g.get('inferred') is True or g.get('substitute_authority_ref'):
            failures.append('unresolved_authority_gap_silent_or_synthetic_resolution:'+str(uid))
        if raw_source_uids is not None:
            for suid in consumers:
                if suid not in raw_source_uids: failures.append('unresolved_authority_gap_unknown_consumer:'+str(uid)+':'+str(suid))
    if expected_authority_refs is not None and seen_ref!=set(expected_authority_refs):
        failures.append('unresolved_authority_gap_count_or_identity_drift:missing='+str(sorted(set(expected_authority_refs)-seen_ref))+':extra='+str(sorted(seen_ref-set(expected_authority_refs))))
    return failures

def validate_blueprint_external_authority_carry(blueprint:dict, dep:dict, raw_sources:dict):
    failures=[]; page=blueprint.get('page_uid')
    relevant=[]
    for g in dep.get('unresolved_authority_gaps') or []:
        if any((raw_sources.get(suid) or {}).get('page_uid')==page for suid in (g.get('consumer_source_uids') or [])):
            relevant.append(g)
    expected={(g.get('gap_uid'),g.get('authority_ref'),'UNRESOLVED_AUTHORITY_GAP') for g in relevant}
    carry=blueprint.get('unresolved_external_authority_refs') or []
    actual={(x.get('gap_uid'),x.get('authority_ref'),x.get('disposition')) for x in carry if isinstance(x,dict)}
    if actual!=expected: failures.append('blueprint_unresolved_external_authority_carry_mismatch:'+str(blueprint.get('blueprint_uid')))
    for x in carry:
        if not isinstance(x,dict): failures.append('blueprint_unresolved_external_authority_carry_invalid_record'); continue
        if x.get('resolved') is True or x.get('satisfied') is True or x.get('auto_filled') is True or x.get('inferred') is True or x.get('substitute_authority_ref'):
            failures.append('blueprint_unresolved_external_authority_false_resolution:'+str(x.get('gap_uid')))
    return failures

def validate(package_root:Path,workspace:Path):
    failures=[]; package_root=package_root.resolve(); workspace=workspace.resolve(); nh=normative_hash(package_root)
    def need(rel,label):
        p=workspace/rel
        if not p.exists(): failures.append(label+'_missing'); return {}
        d=load_yaml(p); fail_if_expectation_keys(d,label,failures); return d
    ctx=need('RUN_CONTEXT.yaml','run_context')
    struct=need('00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml','source_structure_manifest')
    sm=need('00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml','source_segment_map')
    rawcap=need(RAW_CAPTURE_MANIFEST,'raw_source_reference_manifest')
    capstate=need(RAW_CAPTURE_STATE,'raw_source_capture_state')
    manifest=need('CURRENT_RUN_MANIFEST.yaml','current_run_manifest')
    if capstate:
        if capstate.get('state')!='CAPTURE_CLOSED': failures.append('raw_source_capture_not_closed')
        if capstate.get('next_step')!='SOURCE_STRUCTURE_ENUMERATION': failures.append('raw_source_capture_next_step_not_exact_source_structure_enumeration')
        if capstate.get('recapture_allowed') is not False: failures.append('closed_raw_source_capture_still_writable')
    if rawcap:
        if rawcap.get('artifact_type')!='RAW_SOURCE_REFERENCE_MANIFEST': failures.append('raw_source_manifest_type_mismatch')
        if rawcap.get('status')!='CURRENT_RAW_SOURCE_CAPTURE': failures.append('raw_source_manifest_not_current')
        if rawcap.get('capture_root')!=RAW_SOURCE_ROOT: failures.append('raw_source_capture_root_mismatch')
        recs=rawcap.get('records') or []
        target_paths=[]; capture_uids=set()
        for rec in recs:
            uid=rec.get('source_uid'); target=rec.get('target_path'); capture_uids.add(uid)
            if not uid or not target: failures.append('raw_source_manifest_record_missing_identity'); continue
            if not str(target).startswith(RAW_SOURCE_ROOT+'/'): failures.append(f'raw_source_target_outside_raw_root:{uid}:{target}'); continue
            target_paths.append(str(target)); fp=workspace/str(target)
            if not fp.is_file(): failures.append(f'raw_source_target_missing:{uid}:{target}'); continue
            got=git_blob_sha(fp)
            if rec.get('source_git_blob_sha')!=got or rec.get('target_git_blob_sha')!=got: failures.append(f'raw_source_exact_blob_mismatch:{uid}')
            if rec.get('content_mutated') is not False: failures.append(f'raw_source_content_mutation_not_false:{uid}')
            scope=rec.get('source_domain_scope'); role=rec.get('source_role')
            if scope==MIXED_SOURCE_SCOPE and role!=MIXED_SOURCE_ROLE: failures.append(f'mixed_source_role_not_neutral:{uid}:{role}')
        rawroot=workspace/RAW_SOURCE_ROOT
        physical=sorted(p.relative_to(workspace).as_posix() for p in rawroot.rglob('*') if p.is_file()) if rawroot.exists() else []
        if sorted(target_paths)!=physical:
            for x in sorted(set(physical)-set(target_paths)): failures.append('raw_source_directory_unregistered_file:'+x)
            for x in sorted(set(target_paths)-set(physical)): failures.append('raw_source_directory_registered_file_missing:'+x)
    if ctx:
        if ctx.get('candidate_normative_hash')!=nh: failures.append('candidate_normative_hash_mismatch')
        if ctx.get('clean_start_verified') is not True: failures.append('clean_start_not_verified')
        if ctx.get('website_reconstruction') is not False: failures.append('formal_website_reconstruction_not_blocked')
        if ctx.get('stage_uid')!='STAGE-01': failures.append('invalid_stage_uid:'+str(ctx.get('stage_uid')))
    if manifest and ctx and manifest.get('run_uid')!=ctx.get('run_uid'): failures.append('run_uid_mismatch_context_manifest')
    actual_files=list_current_files(workspace)
    for rel in actual_files:
        p=Path(rel)
        if any(x in FORBIDDEN_PARTS for x in p.parts) or p.suffix in FORBIDDEN_SUFFIXES or p.name.endswith('~'): failures.append(f'forbidden_garbage:{rel}')
        if p.parts and p.parts[0] in {'01_CLASSIFIED','02_BASE_BLUEPRINT','03_BLUEPRINT_BINDING'}:
            tokens={t.lower() for t in re.split(r'[^A-Za-z0-9]+',p.stem) if t}
            bad=sorted(tokens & FORBIDDEN_FILENAME_TOKENS)
            if bad: failures.append(f'forbidden_generated_filename_token:{rel}:{bad[0]}')
    declared=sorted(manifest.get('current_files') or [])
    if sorted(actual_files)!=declared:
        for x in sorted(set(actual_files)-set(declared)): failures.append(f'unreferenced_residual:{x}')
        for x in sorted(set(declared)-set(actual_files)): failures.append(f'manifest_missing_physical:{x}')

    raw_sources={s.get('source_uid'):s for s in (sm.get('raw_sources') or []) if s.get('source_uid')}
    if rawcap:
        cap_by_uid={x.get('source_uid'):x for x in (rawcap.get('records') or []) if x.get('source_uid')}
        if set(cap_by_uid)!=set(raw_sources): failures.append('raw_capture_segment_map_source_set_mismatch')
    for suid,rs in raw_sources.items():
        if not rs.get('page_uid'): failures.append(f'raw_source_page_uid_missing:{suid}')
        if rawcap and suid in cap_by_uid:
            rec=cap_by_uid[suid]
            for key in ('page_uid','source_role','source_domain_scope'):
                if rs.get(key)!=rec.get(key): failures.append(f'raw_source_capture_segment_metadata_mismatch:{suid}:{key}')
    structure_sources={s.get('source_uid'):s for s in (struct.get('sources') or []) if s.get('source_uid')}
    if set(raw_sources)!=set(structure_sources): failures.append('raw_source_structure_source_set_mismatch')
    required_nodes={}; all_nodes={}
    for suid,s in structure_sources.items():
        if not s.get('enumeration_method') or not s.get('evidence_ref'): failures.append(f'source_enumeration_evidence_missing:{suid}')
        elif not (workspace/str(s.get('evidence_ref'))).exists(): failures.append(f'source_enumeration_evidence_not_physical:{suid}:{s.get("evidence_ref")}')
        if s.get('enumeration_state') not in {'FULL_SOURCE_ENUMERATION_PROVEN','PARTIAL_SOURCE_ENUMERATION_PILOT','SOURCE_ENUMERATION_NOT_PROVEN'}: failures.append(f'invalid_enumeration_state:{suid}')
        if ctx.get('formal_source_intake_closure_claim') is True and s.get('enumeration_state')!='FULL_SOURCE_ENUMERATION_PROVEN': failures.append(f'full_source_closure_claim_without_full_enumeration:{suid}')
        nodes=s.get('observed_nodes') or []
        ids=[]
        for n in nodes:
            nid=n.get('source_node_uid')
            if not nid or nid in ids: failures.append(f'duplicate_or_missing_source_node:{suid}:{nid}')
            if not n.get('source_ref'): failures.append(f'source_node_source_ref_missing:{suid}:{nid}')
            if n.get('terminality_state')!='TERMINAL_HOMOGENEOUS': failures.append(f'unresolved_container_or_nonterminal_source_node:{suid}:{nid}:{n.get("terminality_state")}')
            if n.get('semantic_responsibility_count')!=1: failures.append(f'mixed_terminal_source_node:{suid}:{nid}:{n.get("semantic_responsibility_count")}')
            if n.get('unresolved_child_responsibility_count')!=0: failures.append(f'unresolved_child_responsibility:{suid}:{nid}:{n.get("unresolved_child_responsibility_count")}')
            ids.append(nid); all_nodes[nid]=(suid,n)
            if n.get('governance_relevance')=='REQUIRED': required_nodes[nid]=(suid,n)
        declared_hash=s.get('structure_manifest_hash')
        if declared_hash!=content_hash(s): failures.append(f'structure_manifest_hash_mismatch:{suid}')
    segments=sm.get('source_segments') or []; seg_by_uid={}; node_to_segments={}
    for s in segments:
        uid=s.get('segment_uid'); node=s.get('source_node_uid')
        if not uid or uid in seg_by_uid: failures.append(f'duplicate_or_missing_segment_uid:{uid}')
        else: seg_by_uid[uid]=s
        if node not in all_nodes: failures.append(f'unknown_source_node:{uid}:{node}')
        else: node_to_segments.setdefault(node,[]).append(uid)
        if s.get('planning_domain') not in DOMAINS: failures.append(f'invalid_segment_domain:{uid}')
        if s.get('source_uid') not in raw_sources: failures.append(f'unknown_segment_source:{uid}')
        else:
            if s.get('page_uid')!=raw_sources[s.get('source_uid')].get('page_uid'): failures.append(f'segment_page_uid_source_mismatch:{uid}')
        if node in all_nodes and all_nodes[node][0]!=s.get('source_uid'): failures.append(f'source_node_source_mismatch:{uid}')
        disp=s.get('disposition')
        if disp not in LEGAL_DISPOSITIONS: failures.append(f'illegal_segment_disposition:{uid}')
        if s.get('required') is True:
            targets=s.get('target_artifact_uids') or []
            if disp=='CLASSIFIED':
                if len(targets)==0: failures.append(f'unmapped_required_segment:{uid}')
                if len(targets)>1: failures.append(f'multi_mapped_required_segment:{uid}')
            elif not s.get('authority_evidence_ref'): failures.append(f'justification_missing:{uid}')
    for nid in required_nodes:
        c=len(node_to_segments.get(nid,[]))
        if c==0: failures.append(f'required_source_node_unenumerated_in_segments:{nid}')
        elif c>1: failures.append(f'required_source_node_multi_segment:{nid}:{c}')

    source_facts={}
    for ftype,rel in REQUIRED_SOURCE_FACT_FILES.items():
        p=workspace/rel
        if not p.exists(): failures.append(f'source_fact_missing:{ftype}'); continue
        d=load_yaml(p); source_facts[ftype]=d
        if d.get('artifact_type')!=ftype: failures.append(f'source_fact_type_mismatch:{ftype}')
        if d.get('status')!='CURRENT_SOURCE_FACT': failures.append(f'source_fact_not_current:{ftype}')
        if d.get('content_hash')!=content_hash(d): failures.append(f'source_fact_hash_mismatch:{ftype}')
        pages_sf=set(d.get('page_uids') or ([d.get('page_uid')] if d.get('page_uid') else []))
        raw_pages={x.get('page_uid') for x in raw_sources.values()}
        if not raw_pages.issubset(pages_sf): failures.append(f'source_fact_page_scope_incomplete:{ftype}')

    dep_doc=source_facts.get('SOURCE_DEPENDENCY_MAP') or {}
    failures.extend(validate_unresolved_authority_gaps(dep_doc,set(raw_sources)))
    for gap in dep_doc.get('unresolved_authority_gaps') or []:
        ev=gap.get('authority_evidence_ref')
        if ev and not (workspace/str(ev)).exists(): failures.append('unresolved_authority_gap_evidence_not_physical:'+str(gap.get('gap_uid')))

    statep=workspace/'EXECUTION_STATE.yaml'
    if statep.exists(): failures.extend(validate_stage1_phase_boundary_state(load_yaml(statep)))

    artifacts={}; owner_resp={}; duplicate_payload={}
    classroot=workspace/'01_CLASSIFIED'
    for p in sorted(classroot.rglob('*.yaml')) if classroot.exists() else []:
        d=load_yaml(p); fail_if_expectation_keys(d,p.name,failures); uid=d.get('artifact_uid'); rel=p.relative_to(workspace).as_posix()
        if not uid or uid in artifacts: failures.append(f'duplicate_or_missing_artifact_uid:{uid}')
        else: artifacts[uid]=d
        if d.get('target_path')!=rel: failures.append(f'artifact_target_path_mismatch:{uid}')
        if d.get('planning_domain') not in DOMAINS: failures.append(f'invalid_artifact_domain:{uid}')
        if d.get('status')!='CURRENT_CLASSIFICATION': failures.append(f'classification_not_current:{uid}')
        for key in ['responsibility_uid','responsibility_class','canonical_owner_uid','lifecycle_uid','approval_scope_uid','version_scope_uid','test_scope_uid']:
            if not d.get(key): failures.append(f'artifact_missing_{key}:{uid}')
        resp=d.get('responsibilities') or ([d.get('responsibility_uid')] if d.get('responsibility_uid') else [])
        if len(resp)>1:
            proof=d.get('mixed_allowed_proof') or {}
            if d.get('mixed_allowed') is not True or not all(proof.get(k) is True for k in ['same_owner','same_lifecycle','same_approval','same_version','same_test_scope']): failures.append(f'unresolved_mixed_responsibility:{uid}')
        for r in resp: owner_resp.setdefault((d.get('page_uid'),r),[]).append(d.get('canonical_owner_uid'))
        lin=d.get('source_lineage') or []
        if not lin: failures.append(f'artifact_lineage_missing:{uid}')
        for rec in lin:
            segs=rec.get('source_segment_uids') or []
            if not segs: failures.append(f'artifact_segment_lineage_missing:{uid}')
            if rec.get('source_uid') not in raw_sources: failures.append(f'artifact_unknown_source_uid:{uid}:{rec.get("source_uid")}')
            for seg in segs:
                if seg not in seg_by_uid: failures.append(f'artifact_unknown_segment:{uid}:{seg}')
                else:
                    if seg_by_uid[seg].get('planning_domain')!=d.get('planning_domain'): failures.append(f'page_visual_cross_contamination:{uid}:{seg}')
                    if seg_by_uid[seg].get('page_uid')!=d.get('page_uid'): failures.append(f'artifact_page_uid_segment_mismatch:{uid}:{seg}')
                    if rec.get('source_uid')!=seg_by_uid[seg].get('source_uid'): failures.append(f'artifact_lineage_source_mismatch:{uid}:{seg}')
        if d.get('content_hash')!=content_hash(d): failures.append(f'artifact_hash_mismatch:{uid}')
        duplicate_payload.setdefault(content_hash(d),[]).append(uid)
    if not artifacts: failures.append('no_classification_artifacts')
    for suid,s in seg_by_uid.items():
        if s.get('required') is True and s.get('disposition')=='SHARED_FACT_REFERENCE':
            targets=s.get('target_artifact_uids') or []
            if not targets: failures.append(f'shared_fact_target_missing:{suid}')
            for t in targets:
                if t not in artifacts: failures.append(f'shared_fact_target_not_physical:{suid}:{t}')
    for key,owners in owner_resp.items():
        if len(set(o for o in owners if o))>1: failures.append(f'duplicate_canonical_owner:{key[0]}:{key[1]}')
    for h,uids in duplicate_payload.items():
        if len(uids)>1: failures.append('duplicate_classification_payload:'+','.join(sorted(uids)))
    seg_targets={uid:[] for uid in seg_by_uid}
    for auid,a in artifacts.items():
        for rec in a.get('source_lineage') or []:
            for suid in rec.get('source_segment_uids') or []: seg_targets.setdefault(suid,[]).append(auid)
    for suid,s in seg_by_uid.items():
        if s.get('required') is True and s.get('disposition')=='CLASSIFIED' and sorted(seg_targets.get(suid,[]))!=sorted(s.get('target_artifact_uids') or []): failures.append(f'segment_mapping_physical_mismatch:{suid}')

    blueprints={}; by_page_type={}
    bproot=workspace/'02_BASE_BLUEPRINT'
    for p in sorted(bproot.rglob('*.yaml')) if bproot.exists() else []:
        d=load_yaml(p); fail_if_expectation_keys(d,p.name,failures); uid=d.get('blueprint_uid'); rel=p.relative_to(workspace).as_posix(); btype=d.get('blueprint_type'); domain=d.get('planning_domain')
        if not uid or uid in blueprints: failures.append(f'duplicate_or_missing_blueprint_uid:{uid}')
        else: blueprints[uid]=d
        if btype not in BLUEPRINT_BY_DOMAIN.values(): failures.append(f'invalid_blueprint_type:{uid}:{btype}')
        if BLUEPRINT_BY_DOMAIN.get(domain)!=btype: failures.append(f'blueprint_domain_type_mismatch:{uid}')
        if d.get('target_path')!=rel: failures.append(f'blueprint_target_path_mismatch:{uid}')
        if d.get('status')!='CURRENT_BASE_BLUEPRINT': failures.append(f'blueprint_not_current:{uid}')
        if d.get('raw_source_inputs'): failures.append(f'blueprint_direct_raw_source_input:{uid}')
        if d.get('embedded_classification_payloads'): failures.append(f'blueprint_embeds_classification_payload:{uid}')
        inputs=d.get('input_artifacts') or []; seen=set(); covered=set()
        for rec in inputs:
            auid=rec.get('artifact_uid')
            if auid in seen: failures.append(f'blueprint_duplicate_input:{uid}:{auid}')
            seen.add(auid)
            if auid not in artifacts: failures.append(f'blueprint_unknown_artifact:{uid}:{auid}'); continue
            a=artifacts[auid]
            if a.get('planning_domain')!=domain: failures.append(f'blueprint_cross_domain_input:{uid}:{auid}')
            if rec.get('content_hash')!=a.get('content_hash'): failures.append(f'blueprint_stale_input_hash:{uid}:{auid}')
            covered.add(a.get('responsibility_uid'))
        sfrefs=d.get('source_fact_refs') or []
        expected_sf={(v.get('artifact_uid'),v.get('content_hash')) for v in source_facts.values()}
        actual_sf={(x.get('artifact_uid'),x.get('content_hash')) for x in sfrefs}
        if expected_sf and actual_sf!=expected_sf: failures.append(f'blueprint_source_fact_refs_incomplete_or_stale:{uid}')
        failures.extend(validate_blueprint_external_authority_carry(d,dep_doc,raw_sources))
        for sr in d.get('shared_refs') or []:
            suid=sr.get('artifact_uid') if isinstance(sr,dict) else sr
            if suid not in artifacts: failures.append(f'blueprint_unresolved_shared_ref:{uid}:{suid}')
        required=set(d.get('required_responsibility_uids') or [])
        if not required: failures.append(f'blueprint_required_responsibilities_empty:{uid}')
        for r in sorted(required-covered): failures.append(f'blueprint_missing_responsibility:{uid}:{r}')
        for r in sorted(covered-required): failures.append(f'blueprint_unexpected_responsibility:{uid}:{r}')
        if d.get('blueprint_hash')!=content_hash(d): failures.append(f'blueprint_hash_mismatch:{uid}')
        by_page_type.setdefault((d.get('page_uid'),btype),[]).append(uid)
    pages=set(s.get('page_uid') for s in segments if s.get('page_uid'))
    for page in pages:
        for btype in BLUEPRINT_BY_DOMAIN.values():
            c=len(by_page_type.get((page,btype),[]))
            if c!=1: failures.append(f'base_blueprint_count:{page}:{btype}:{c}')

    bindings={}; bindroot=workspace/'03_BLUEPRINT_BINDING'
    for p in sorted(bindroot.rglob('*.yaml')) if bindroot.exists() else []:
        d=load_yaml(p); uid=d.get('binding_uid'); page=d.get('page_uid'); rel=p.relative_to(workspace).as_posix()
        if not uid or uid in bindings: failures.append(f'duplicate_or_missing_binding_uid:{uid}')
        else: bindings[uid]=d
        if d.get('target_path')!=rel: failures.append(f'binding_target_path_mismatch:{uid}')
        if d.get('status')!='CURRENT_BLUEPRINT_BINDING': failures.append(f'binding_not_current:{uid}')
        if d.get('embedded_blueprint_payloads'): failures.append(f'binding_embeds_payload:{uid}')
        for key,btype in [('page_blueprint','PAGE_BASE_BLUEPRINT'),('visual_blueprint','VISUAL_BASE_BLUEPRINT')]:
            rec=d.get(key) or {}; buid=rec.get('blueprint_uid')
            if buid not in blueprints: failures.append(f'binding_unknown_blueprint:{uid}:{key}:{buid}')
            else:
                b=blueprints[buid]
                if b.get('page_uid')!=page or b.get('blueprint_type')!=btype: failures.append(f'binding_wrong_blueprint:{uid}:{key}')
                if rec.get('blueprint_hash')!=b.get('blueprint_hash'): failures.append(f'binding_stale_blueprint_hash:{uid}:{key}')
        if d.get('binding_hash')!=content_hash(d): failures.append(f'binding_hash_mismatch:{uid}')
    for page in pages:
        c=sum(1 for d in bindings.values() if d.get('page_uid')==page)
        if c!=1: failures.append(f'blueprint_binding_count:{page}:{c}')
    return {'status':'PASS' if not failures else 'FAIL','failures':failures,'candidate_normative_hash':nh,'artifact_count':len(artifacts),'blueprint_count':len(blueprints),'binding_count':len(bindings),'required_source_node_count':len(required_nodes)}

if __name__=='__main__':
    if len(sys.argv)!=3: print('usage: governance_stage1_pipeline_guard.py <package_root> <workspace_root>',file=sys.stderr); raise SystemExit(2)
    out=validate(Path(sys.argv[1]),Path(sys.argv[2])); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
