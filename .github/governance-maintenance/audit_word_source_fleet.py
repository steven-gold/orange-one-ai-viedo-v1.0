#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys, tempfile, zipfile, xml.etree.ElementTree as ET, importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'.github/governance-source/active/source'
GUARD=PKG/'09_TESTS/governance/governance_stage1_pipeline_guard.py'
spec=importlib.util.spec_from_file_location('stage1_guard',GUARD)
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
BRANCH='origin/0921acpos'

DOMAIN_PATTERNS={
 'IDENTITY_SCOPE':r'(page[_ -]?uid|system[_ -]?uid|scope|owner|version|版本|範圍|頁面.*uid|系統.*uid)',
 'VISUAL_LAYOUT':r'(visual|layout|ui\b|ux\b|geometry|drawer|sidebar|timeline|視覺|版面|佈局|介面|側欄|時間軸)',
 'INTERACTION_CONTROL':r'(control|button|action|interaction|menu|dialog|modal|按鈕|控制|操作|互動|選單|對話框)',
 'STATE_GATE_ERROR':r'(state|gate|error|status|transition|狀態|閘門|錯誤|狀態轉換)',
 'PERMISSION_ROLE':r'(permission|role|rls|authorization|權限|角色|授權)',
 'DATA_SCHEMA':r'(entity|payload|field|database|schema|table|column|資料庫|欄位|實體|資料表)',
 'INTEGRATION_RUNTIME':r'(api\b|integration|port|event|webhook|runtime|worker|queue|整合|接口|執行期|事件|佇列)',
 'WORKFLOW_LIFECYCLE':r'(workflow|stage|lifecycle|transition|operation|流程|階段|生命週期|作業)',
 'QA_ACCEPTANCE':r'(qa\b|audit|acceptance|review|validator|驗收|稽核|審查|驗證)',
 'LOCALIZATION_ACCESSIBILITY':r'(i18n|locale|zh-tw|zh-cn|accessibility|a11y|語系|繁體|簡體|無障礙)',
 'AI_CONVERSATION':r'(conversation|multi.?ai|memory|assistant|ai 對話|對話|記憶|助理)',
}
UNIVERSAL_PAGE_DOMAINS=['IDENTITY_SCOPE','VISUAL_LAYOUT','INTERACTION_CONTROL','STATE_GATE_ERROR','DATA_SCHEMA','INTEGRATION_RUNTIME','WORKFLOW_LIFECYCLE','QA_ACCEPTANCE']

def sh(*args, binary=False):
    cp=subprocess.run(args,cwd=ROOT,capture_output=True,text=not binary)
    if cp.returncode:
        raise RuntimeError((cp.stderr if not binary else cp.stderr.decode(errors='replace')) or 'command failed')
    return cp.stdout

def sha256(b): return hashlib.sha256(b).hexdigest()

def parse_docx_text_and_structure(data:bytes):
    out={'text':'','paragraph_count':0,'table_count':0,'drawing_count':0,'embedded_relation_ids':[],'heading_texts':[]}
    with zipfile.ZipFile(__import__('io').BytesIO(data),'r') as z:
        names=set(z.namelist())
        if 'word/document.xml' not in names: return out
        root=ET.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        texts=[]
        for p in root.iter():
            local=p.tag.rsplit('}',1)[-1] if '}' in p.tag else p.tag
            if local=='p': out['paragraph_count']+=1
            elif local=='tbl': out['table_count']+=1
            elif local=='drawing': out['drawing_count']+=1
            for ak,av in p.attrib.items():
                al=ak.rsplit('}',1)[-1] if '}' in ak else ak
                if al in {'embed','link'} and str(av).startswith('rId'): out['embedded_relation_ids'].append(str(av))
            if local=='t' and p.text:
                texts.append(p.text)
        out['text']='\n'.join(texts)
        # Heading-style paragraphs.
        for p in root.findall('.//w:p',ns):
            ppr=p.find('w:pPr',ns); sid=''
            if ppr is not None:
                ps=ppr.find('w:pStyle',ns)
                if ps is not None:
                    sid=next((v for k,v in ps.attrib.items() if k.endswith('}val') or k=='val'),'')
            if sid and re.search(r'(heading|title|標題)',sid,re.I):
                t=''.join((x.text or '') for x in p.findall('.//w:t',ns)).strip()
                if t: out['heading_texts'].append(t)
    out['embedded_relation_ids']=sorted(set(out['embedded_relation_ids']))
    return out

def source_part_for_rel(relpart:str)->str:
    p=Path(relpart)
    if relpart=='_rels/.rels': return ''
    parts=p.parts
    if len(parts)>=2 and parts[-2]=='_rels' and parts[-1].endswith('.rels'):
        return (Path(*parts[:-2]) / parts[-1][:-5]).as_posix()
    return ''

def resolve_target(relpart,target):
    if not target: return ''
    if str(target).startswith('/'): return str(target).lstrip('/')
    src=source_part_for_rel(relpart)
    base=Path(src).parent if src else Path('.')
    return os.path.normpath((base/target).as_posix()).replace('\\','/').lstrip('./')

def classify(path):
    n=Path(path).name
    if n.startswith('00_INDEX_'): return 'INDEX'
    if re.match(r'0[1-9]_ACPOS_',n): return 'SYSTEM_LOGIC_NORMATIVE_CONTRACT'
    return 'PAGE_OR_SYSTEM_BASIC_DESIGN'

def audit_one(path, blob_sha, data):
    row={'path':path,'git_blob_sha':blob_sha,'size_bytes':len(data),'sha256':sha256(data),'document_kind':classify(path)}
    failures=[]; warnings=[]
    try:
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'source.docx'; p.write_bytes(data)
            inv=g.derive_docx_inventory(p)
        row['package_part_count']=len(inv.get('package_parts') or [])
        row['relationship_count']=len(inv.get('relationships') or [])
        row['xml_node_count']=len(inv.get('source_nodes') or [])
        parts={x.get('package_part_path'):x for x in inv.get('package_parts') or []}
        if len(parts)!=row['package_part_count']: failures.append('DUPLICATE_PACKAGE_PART_PATH')
        relkeys=[(x.get('relationship_part_path'),x.get('relationship_id')) for x in inv.get('relationships') or []]
        if len(set(relkeys))!=len(relkeys): failures.append('DUPLICATE_RELATIONSHIP_ID_WITHIN_PART')
        uids=[x.get('source_node_uid') for x in inv.get('source_nodes') or []]
        if None in uids or '' in uids: failures.append('SOURCE_NODE_UID_MISSING')
        if len(set(uids))!=len(uids): failures.append('DUPLICATE_SOURCE_NODE_UID')
        orders=[x.get('projection_order_index') for x in inv.get('source_nodes') or []]
        if orders!=list(range(1,len(orders)+1)): failures.append('PROJECTION_ORDER_NOT_CONTIGUOUS')
        binary=[x for x in inv.get('package_parts') or [] if not str(x.get('package_part_path') or '').lower().endswith(('.xml','.rels'))]
        row['binary_part_count']=len(binary)
        row['binary_suffixes']=sorted(set(Path(str(x.get('package_part_path'))).suffix.lower() for x in binary))
        row['image_part_count']=sum(1 for x in binary if str(x.get('content_type') or '').startswith('image/'))
        with zipfile.ZipFile(__import__('io').BytesIO(data),'r') as z:
            zn=set(z.namelist())
            if len(zn)!=len(z.namelist()): failures.append('DUPLICATE_ZIP_MEMBER')
            for b in binary:
                pp=str(b.get('package_part_path') or '')
                if pp not in zn: failures.append('BINARY_PACKAGE_PART_MISSING:'+pp); continue
                bb=z.read(pp)
                if len(bb)!=b.get('size_bytes'): failures.append('BINARY_SIZE_MISMATCH:'+pp)
                if sha256(bb)!=b.get('part_sha256'): failures.append('BINARY_HASH_MISMATCH:'+pp)
            for rel in inv.get('relationships') or []:
                if str(rel.get('target_mode') or '').lower()=='external': continue
                tgt=resolve_target(str(rel.get('relationship_part_path') or ''),str(rel.get('target') or ''))
                if tgt and tgt not in zn:
                    failures.append('RELATIONSHIP_TARGET_MISSING:'+str(rel.get('relationship_part_path'))+':'+str(rel.get('relationship_id'))+':'+tgt)
        ds=parse_docx_text_and_structure(data)
        row.update({k:v for k,v in ds.items() if k!='text'})
        row['text_char_count']=len(ds['text'])
        row['domain_presence']={k:bool(re.search(pat,ds['text'],re.I)) for k,pat in DOMAIN_PATTERNS.items()}
        row['missing_universal_domains']=[]
        if row['document_kind']=='PAGE_OR_SYSTEM_BASIC_DESIGN':
            row['missing_universal_domains']=[k for k in UNIVERSAL_PAGE_DOMAINS if not row['domain_presence'][k]]
            if row['missing_universal_domains']:
                warnings.append('CONTENT_DOMAIN_REVIEW:'+','.join(row['missing_universal_domains']))
        elif row['document_kind']=='SYSTEM_LOGIC_NORMATIVE_CONTRACT':
            req=['IDENTITY_SCOPE','DATA_SCHEMA','INTEGRATION_RUNTIME','WORKFLOW_LIFECYCLE','QA_ACCEPTANCE']
            miss=[k for k in req if not row['domain_presence'][k]]
            row['missing_universal_domains']=miss
            if miss: warnings.append('LOGIC_CONTRACT_DOMAIN_REVIEW:'+','.join(miss))
        elif row['document_kind']=='INDEX':
            if row['text_char_count']<100: failures.append('INDEX_CONTENT_TOO_SPARSE')
        # Visual semantic continuity.
        image_rels=[x for x in inv.get('relationships') or [] if str(x.get('relationship_type') or '').lower().endswith('/image')]
        row['image_relationship_count']=len(image_rels)
        rel_ids={x.get('relationship_id') for x in image_rels}
        missing_embed=[rid for rid in ds['embedded_relation_ids'] if rid not in rel_ids]
        if missing_embed: failures.append('DRAWING_EMBED_RELATIONSHIP_MISSING:'+','.join(missing_embed))
        # Any image rel must point to a projected package part and exact binary bytes.
        for rel in image_rels:
            tgt=resolve_target(str(rel.get('relationship_part_path') or ''),str(rel.get('target') or ''))
            if tgt not in parts: failures.append('IMAGE_REL_TARGET_NOT_IN_PACKAGE_PROJECTION:'+tgt)
            elif not str(parts[tgt].get('content_type') or '').startswith('image/'):
                failures.append('IMAGE_REL_TARGET_CONTENT_TYPE_NOT_IMAGE:'+tgt)
        if ds['drawing_count']>0 and row['image_part_count']==0:
            failures.append('DRAWING_WITHOUT_PROJECTABLE_IMAGE_BINARY')
        # Generic projection schema should carry every XML element and binary part.
        row['projection_schema_compatibility']='PASS' if not failures else 'FAIL'
    except Exception as exc:
        failures.append('DOCX_PARSE_OR_INVENTORY_EXCEPTION:'+type(exc).__name__+':'+str(exc)[:300])
        row['projection_schema_compatibility']='FAIL'
    row['failures']=failures
    row['warnings']=warnings
    row['content_review_status']='REVIEW_REQUIRED' if warnings else 'NO_MACHINE_DETECTED_REQUIRED_DOMAIN_GAP'
    return row

def main():
    subprocess.run(['git','fetch','origin','0921acpos:refs/remotes/origin/0921acpos'],cwd=ROOT,check=True)
    raw=sh('git','-c','core.quotePath=false','ls-tree','-r','-l',BRANCH)
    docs=[]
    for line in raw.splitlines():
        if '\t' not in line: continue
        meta,path=line.split('\t',1)
        if not path.lower().endswith('.docx'): continue
        parts=meta.split()
        blob=parts[2]
        data=subprocess.run(['git','show',f'{BRANCH}:{path}'],cwd=ROOT,capture_output=True,check=True).stdout
        docs.append(audit_one(path,blob,data))
    docs.sort(key=lambda x:x['path'])
    fail=[d for d in docs if d['failures']]
    review=[d for d in docs if d['warnings']]
    report={
      'artifact_type':'WORD_SOURCE_FLEET_CONTENT_AND_PROJECTION_COMPATIBILITY_AUDIT',
      'normative_authority':False,
      'governance_uid':load_governance_uid(),
      'source_branch':'0921acpos',
      'source_head':sh('git','rev-parse',BRANCH).strip(),
      'document_count':len(docs),
      'projection_compatibility_pass_count':len(docs)-len(fail),
      'projection_compatibility_fail_count':len(fail),
      'content_review_candidate_count':len(review),
      'result':'PASS_ALL_PROJECTION_COMPATIBLE' if not fail else 'FAIL_PROJECTION_INCOMPATIBILITY',
      'documents':docs
    }
    Path('/tmp/word_source_fleet_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='documents'},ensure_ascii=False,indent=2))
    for d in docs:
        print(json.dumps({
          'path':d['path'],'kind':d['document_kind'],'projection':d['projection_schema_compatibility'],
          'paragraphs':d.get('paragraph_count'),'tables':d.get('table_count'),'drawings':d.get('drawing_count'),
          'binary_parts':d.get('binary_part_count'),'images':d.get('image_part_count'),
          'text_chars':d.get('text_char_count'),'missing_universal_domains':d.get('missing_universal_domains'),
          'failures':d['failures'],'warnings':d['warnings']
        },ensure_ascii=False))
    if fail: raise SystemExit(1)

def load_governance_uid():
    import yaml
    d=yaml.safe_load((ROOT/'governance/specifications/REGISTRY.yaml').read_text()) or {}
    return (d.get('active_specification') or {}).get('governance_uid')

if __name__=='__main__': main()
