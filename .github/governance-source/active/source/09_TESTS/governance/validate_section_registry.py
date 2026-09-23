#!/usr/bin/env python3
from pathlib import Path
import json,re,sys,yaml,hashlib
ROOT=Path(__file__).resolve().parents[2]

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def binding_hash(uid,document_id,path,heading):
    return hashlib.sha256(f'{uid}\n{document_id}\n{path}\n{heading}\n'.encode()).hexdigest()

def validate(root=ROOT):
    failures=[]
    regp=root/'10_REGISTRY/SECTION_NUMBER_REGISTRY.yaml'
    if not regp.exists(): return {'status':'FAIL','failures':['section_registry_missing']}
    d=load(regp); entries={}
    for doc in d.get('documents',[]):
        rel=doc.get('path',''); p=root/rel
        if not p.exists(): failures.append('normative_doc_missing:'+str(rel)); continue
        text=p.read_text(encoding='utf-8'); lines=text.splitlines(); numeric=[]
        for i,l in enumerate(lines):
            m=re.match(r'^##\s+(\d+)([A-Z]?)\.?\s+',l)
            if m: numeric.append((m.group(1)+m.group(2),i,l))
        nums=[x[0] for x in numeric]
        if len(nums)!=len(set(nums)): failures.append('duplicate_numeric_h2:'+doc.get('document_id',''))
        for s in doc.get('sections',[]):
            uid=s.get('section_uid')
            if not uid or uid in entries: failures.append('duplicate_or_missing_section_uid:'+str(uid)); continue
            entries[uid]=s
            anchor=f'<!-- SECTION_UID: {uid} -->'; heading=s.get('heading') or ''
            anchor_idx=[i for i,l in enumerate(lines) if l.strip()==anchor]
            heading_idx=[i for i,l in enumerate(lines) if l==heading]
            if len(anchor_idx)!=1: failures.append(f'section_anchor_occurrence_not_one:{uid}:{len(anchor_idx)}'); continue
            if len(heading_idx)!=1: failures.append(f'section_heading_occurrence_not_one:{uid}:{len(heading_idx)}'); continue
            ai=anchor_idx[0]; hi=heading_idx[0]
            if hi != ai+1: failures.append(f'section_anchor_heading_not_adjacent:{uid}:anchor_line={ai+1}:heading_line={hi+1}')
            if ai+1>=len(lines) or lines[ai+1]!=heading: failures.append('section_anchor_bound_to_wrong_heading:'+uid)
            level=int(s.get('level') or 0)
            if not heading.startswith('#'*level+' '): failures.append('section_heading_level_mismatch:'+uid)
            if s.get('path')!=rel: failures.append('section_path_document_mismatch:'+uid)
            expected=binding_hash(uid,doc.get('document_id',''),rel,heading)
            if s.get('binding_sha256')!=expected: failures.append('section_binding_hash_mismatch:'+uid)
        # Every numeric H2/H3 must have exactly one immediate registered UID anchor.
        for i,l in enumerate(lines):
            if re.match(r'^##\s+\d+[A-Z]?\.?\s+',l) or re.match(r'^###\s+\d+\.\d+\s+',l):
                if i==0 or not re.fullmatch(r'<!-- SECTION_UID: ([A-Z0-9-]+) -->',lines[i-1].strip()):
                    failures.append(f'unanchored_numeric_heading:{doc.get("document_id")}:{i+1}')
                else:
                    uid=re.fullmatch(r'<!-- SECTION_UID: ([A-Z0-9-]+) -->',lines[i-1].strip()).group(1)
                    rec=entries.get(uid)
                    # if entry appears later in registry loop order, resolve directly from document section list
                    if rec is None: rec=next((x for x in doc.get('sections',[]) if x.get('section_uid')==uid),None)
                    if rec is None or rec.get('heading')!=l: failures.append(f'heading_preceded_by_wrong_registered_uid:{doc.get("document_id")}:{i+1}:{uid}')
    pol=d.get('policy') or {}
    if d.get('historical_duplicate_group_count')!=16: failures.append('historical_duplicate_group_count_not_16')
    if pol.get('free_text_heading_reference_forbidden') is not True: failures.append('free_text_heading_reference_not_forbidden')
    for k in ['exact_anchor_heading_adjacency_required','exactly_one_anchor_occurrence_required','exactly_one_heading_occurrence_required','section_binding_hash_required']:
        if pol.get(k) is not True: failures.append('section_binding_policy_not_true:'+k)
    return {'status':'PASS' if not failures else 'FAIL','section_count':len(entries),'failures':failures,'section_uids':sorted(entries)}

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
