#!/usr/bin/env python3
from pathlib import Path
import json,re,yaml,sys,hashlib,copy
import ast
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
SEMANTIC_BASELINE_CONTENT_HASH = '59f56fab490f0724d66055259ae0424529ce3ba83bdedd7e77b526a1807ee716'

_YAML_CACHE={}
_FRONTMATTER_CACHE={}
def load(p):
    raw=Path(p).read_bytes(); key=hashlib.sha256(raw).digest()
    if key not in _YAML_CACHE: _YAML_CACHE[key]=yaml.safe_load(raw.decode('utf-8')) or {}
    return _YAML_CACHE[key]
def hobj(d):
    x=copy.deepcopy(d); x.pop('content_hash',None)
    return hashlib.sha256(yaml.safe_dump(x,allow_unicode=True,sort_keys=True,width=180).encode()).hexdigest()
def parse_frontmatter(path):
    raw=Path(path).read_bytes(); key=hashlib.sha256(raw).digest()
    if key in _FRONTMATTER_CACHE: return _FRONTMATTER_CACHE[key]
    text=raw.decode('utf-8')
    if not text.startswith('---\n'): out={}
    else:
        end=text.find('\n---\n',4); out={} if end<0 else (yaml.safe_load(text[4:end]) or {})
    _FRONTMATTER_CACHE[key]=out; return out
def section_uids(root):
    reg=load(root/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'); out=set()
    for doc in reg.get('documents') or []:
        for s in doc.get('sections') or []: out.add(s.get('section_uid'))
    return out

def semantic_hash_literal_owner_errors(root=ROOT):
    errors=[]; owners=[]
    test_root=root/'09_TESTS/governance'
    for path in sorted(test_root.glob('*.py')):
        try: tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
        except SyntaxError as exc:
            errors.append(f'semantic_hash_owner_python_parse_failed:{path.name}:{exc.lineno}'); continue
        for node in tree.body:
            targets=node.targets if isinstance(node,ast.Assign) else ([node.target] if isinstance(node,ast.AnnAssign) else [])
            if not any(isinstance(t,ast.Name) and t.id=='SEMANTIC_BASELINE_CONTENT_HASH' for t in targets): continue
            value=getattr(node,'value',None)
            if isinstance(value,ast.Constant) and isinstance(value.value,str): owners.append((path.name,value.value))
    if owners!=[('validate_reference_semantics.py',SEMANTIC_BASELINE_CONTENT_HASH)]:
        errors.append('semantic_baseline_literal_owner_not_exactly_one_canonical:'+repr(owners))
    return errors

def validate(root=ROOT):
    failures=[]
    failures += semantic_hash_literal_owner_errors(root)
    rp=root/'10_REGISTRY/REFERENCE_RULE_REGISTRY.yaml'; bp0=root/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    if not rp.exists(): return {'status':'FAIL','failures':['reference_rule_registry_missing']}
    if not bp0.exists(): return {'status':'FAIL','failures':['semantic_authority_baseline_missing']}
    ref=load(rp); anchor=load(bp0)
    if anchor.get('content_hash')!=SEMANTIC_BASELINE_CONTENT_HASH or hobj(anchor)!=SEMANTIC_BASELINE_CONTENT_HASH:
        failures.append('semantic_authority_baseline_invalid_or_mutated')
    snap=anchor.get('semantic_snapshot') or {}
    for key in ['program_profile_reference_rules','stage_reference_rules','common_bundle_reference_rules','validator_identities','audit_type_identities','review_type_identities','blueprint_type_identities','normative_document_rules','naming_registry_contract']:
        if ref.get(key)!=snap.get(key): failures.append('reference_rule_registry_drift_from_immutable_baseline:'+key)

    idx=load(root/'10_REGISTRY/CONSTRUCTION_ARTIFACT_INDEX.yaml'); life=load(root/'10_REGISTRY/GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml')
    naming=load(root/'10_REGISTRY/NAMING_REGISTRY.yaml'); cat=load(root/'10_REGISTRY/AUDIT_CATALOG.yaml'); review=load(root/'10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml')
    bpr=load(root/'10_REGISTRY/BLUEPRINT_REGISTRY.yaml'); bp=load(root/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml')
    known_sections=section_uids(root)
    if ref.get('artifact_uid')!='REG-REFERENCE-RULE-001': failures.append('reference_rule_registry_uid_invalid')
    rules=ref.get('rules') or {}
    for k in ['legal_uid_is_not_sufficient','semantic_binding_must_match_registered_rule']:
        if rules.get(k) is not True: failures.append('reference_semantic_rule_not_true:'+k)
    for k in ['free_string_identity','unknown_typed_identity','profile_reference_drift','stage_reference_drift','common_bundle_reference_drift','normative_document_classification_drift']:
        if rules.get(k)!='BLOCK': failures.append('reference_semantic_rule_not_block:'+k)

    # Operational registry + consumer must both match the immutable baseline.
    prules=snap.get('program_profile_reference_rules') or {}; profiles=idx.get('program_construction_profiles') or {}
    if set(prules)!=set(profiles): failures.append('profile_reference_rule_set_mismatch')
    for name,p in profiles.items():
        actual=p.get('required_normative_section_uids') or []; expected=(prules.get(name) or {}).get('exact_required_normative_section_uids') or []
        if actual!=expected: failures.append('profile_semantic_reference_mismatch:'+name)
        for uid in actual:
            if uid not in known_sections: failures.append('profile_semantic_section_unresolved:'+name+':'+str(uid))
    srules=snap.get('stage_reference_rules') or {}; stages={s.get('stage_uid'):s for s in life.get('stages') or []}
    if set(srules)!=set(stages): failures.append('stage_reference_rule_set_mismatch')
    for uid,st in stages.items():
        actual=st.get('required_normative_section_uids') or []; expected=(srules.get(uid) or {}).get('exact_required_normative_section_uids') or []
        if actual!=expected: failures.append('stage_semantic_reference_mismatch:'+str(uid))
        for sec in actual:
            if sec not in known_sections: failures.append('stage_semantic_section_unresolved:'+str(uid)+':'+str(sec))
    brules=snap.get('common_bundle_reference_rules') or {}; bundles=idx.get('mandatory_common_normative_bundles') or {}
    if set(brules)!=set(bundles): failures.append('common_bundle_reference_rule_set_mismatch')
    for bid,b in bundles.items():
        actual=b.get('section_uids') or []; expected=(brules.get(bid) or {}).get('exact_section_uids') or []
        if actual!=expected: failures.append('common_bundle_semantic_reference_mismatch:'+bid)

    # Typed validator identities are baseline-anchored and usage-scoped.
    vals=snap.get('validator_identities') or []; vuids=[v.get('validator_uid') for v in vals]; vnames=[v.get('canonical_name') for v in vals]
    if len(vuids)!=len(set(vuids)) or None in vuids: failures.append('validator_uid_duplicate_or_missing')
    if len(vnames)!=len(set(vnames)) or None in vnames: failures.append('validator_name_duplicate_or_missing')
    vmap={v['validator_uid']:v for v in vals if v.get('validator_uid')}
    for st in life.get('stages') or []:
        for uid in st.get('validators') or []:
            rec=vmap.get(uid)
            if not rec: failures.append('lifecycle_validator_uid_unknown:'+str(uid))
            elif 'LIFECYCLE_STAGE' not in (rec.get('allowed_usage') or []): failures.append('lifecycle_validator_usage_invalid:'+str(uid))
        names=st.get('validator_names') or []
        if names and len(names)!=len(st.get('validators') or []): failures.append('lifecycle_validator_name_count_mismatch:'+str(st.get('stage_uid')))
        for uid,name in zip(st.get('validators') or [],names):
            if (vmap.get(uid) or {}).get('canonical_name')!=name: failures.append('lifecycle_validator_name_mismatch:'+str(uid))

    amap={x.get('audit_type_uid'):x for x in snap.get('audit_type_identities') or []}
    for item in cat.get('items') or []:
        v=vmap.get(item.get('validator_uid'))
        if not v: failures.append('audit_validator_uid_unknown:'+str(item.get('audit_item_uid')))
        else:
            if 'AUDIT_CATALOG' not in (v.get('allowed_usage') or []): failures.append('audit_validator_usage_invalid:'+str(item.get('validator_uid')))
            if item.get('validator_name')!=v.get('canonical_name'): failures.append('audit_validator_name_mismatch:'+str(item.get('audit_item_uid')))
        at=amap.get(item.get('audit_type_uid'))
        if not at: failures.append('audit_type_uid_unknown:'+str(item.get('audit_item_uid')))
        else:
            if at.get('canonical_name')!=item.get('audit_type'): failures.append('audit_type_name_mismatch:'+str(item.get('audit_item_uid')))
            if item.get('stage_uid') not in (at.get('allowed_stage_uids') or []): failures.append('audit_type_stage_usage_invalid:'+str(item.get('audit_item_uid')))
            if bool(item.get('denominator_eligible'))!=bool(at.get('denominator_eligible')): failures.append('audit_type_denominator_eligibility_mismatch:'+str(item.get('audit_item_uid')))

    rmap={x.get('review_type_uid'):x for x in snap.get('review_type_identities') or []}
    for item in review.get('required_review_plan') or []:
        rec=rmap.get(item.get('review_type_uid'))
        if not rec: failures.append('review_type_uid_unknown:'+str(item.get('review_item_uid')))
        elif rec.get('canonical_name')!=item.get('review_type'): failures.append('review_type_name_mismatch:'+str(item.get('review_item_uid')))
    btmap={x.get('blueprint_type_uid'):x for x in snap.get('blueprint_type_identities') or []}
    for item in bpr.get('blueprint_types') or []:
        rec=btmap.get(item.get('blueprint_type_uid'))
        if not rec: failures.append('blueprint_type_uid_unknown:'+str(item.get('blueprint_type')))
        elif rec.get('canonical_name')!=item.get('blueprint_type'): failures.append('blueprint_type_name_mismatch:'+str(item.get('blueprint_type')))
        else:
            if rec.get('planning_domain')!=item.get('planning_domain'): failures.append('blueprint_type_planning_domain_mismatch:'+str(item.get('blueprint_type')))
            if rec.get('created_stage_uid')!=item.get('created_stage_uid'): failures.append('blueprint_type_created_stage_mismatch:'+str(item.get('blueprint_type')))
    if (btmap.get(bp.get('blueprint_type_uid')) or {}).get('canonical_name')!=bp.get('blueprint_type'): failures.append('acceptance_blueprint_type_identity_invalid')

    if 'audit_items' in bp: failures.append('acceptance_blueprint_second_embedded_audit_logic_present')
    cat_uids=[x.get('audit_item_uid') for x in cat.get('items') or []]
    if bp.get('audit_item_uids')!=cat_uids: failures.append('acceptance_blueprint_catalog_denominator_mismatch')

    nc=snap.get('naming_registry_contract') or {}; required=nc.get('required_item_fields') or []; pattern=re.compile(nc.get('canonical_name_pattern') or r'^$')
    items=naming.get('items') or []; seen_uid=set();seen_name=set();seen_path=set()
    for item in items:
        tag=item.get('uid') or '<missing>'
        for f in required:
            if f not in item or item.get(f) in (None,''): failures.append('naming_required_field_missing:'+tag+':'+f)
        uid=item.get('uid'); name=item.get('canonical_name'); path=item.get('canonical_path')
        if uid in seen_uid: failures.append('naming_duplicate_uid:'+str(uid))
        if name in seen_name: failures.append('naming_duplicate_canonical_name:'+str(name))
        if path in seen_path: failures.append('naming_duplicate_canonical_path:'+str(path))
        seen_uid.add(uid);seen_name.add(name);seen_path.add(path)
        if not isinstance(name,str) or not pattern.fullmatch(name): failures.append('naming_canonical_name_format_invalid:'+str(name))
        if item.get('filename_policy')=='REGISTERED_GOVERNANCE_FIXED_NAME':
            if item.get('entity_type') not in ('GOVERNANCE_REGISTRY','GOVERNANCE_BLUEPRINT'): failures.append('naming_filename_exception_entity_invalid:'+tag)
            if item.get('filename_exception_authority')!=nc.get('governance_fixed_filename_exception_authority'): failures.append('naming_filename_exception_authority_invalid:'+tag)
            if Path(item.get('canonical_path','')).name!=item.get('canonical_file_name'): failures.append('naming_filename_path_mismatch:'+tag)

    for rec in snap.get('normative_document_rules') or []:
        p=root/rec.get('canonical_path',''); fm=parse_frontmatter(p) if p.exists() else {}
        if not p.exists(): failures.append('normative_document_missing:'+str(rec.get('document_id'))); continue
        for k,actual in [('document_id',fm.get('document_id')),('expected_category',fm.get('category')),('required_before_execution',fm.get('required_before_execution')),('status',fm.get('status'))]:
            expected=rec.get(k)
            if actual!=expected: failures.append('normative_document_'+k+'_mismatch:'+str(rec.get('document_id')))
    return {'status':'PASS' if not failures else 'FAIL','failures':failures,'profiles':len(profiles),'stages':len(stages),'validator_identities':len(vals),'audit_types':len(amap),'naming_items':len(items),'semantic_anchor_hash':SEMANTIC_BASELINE_CONTENT_HASH}

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
