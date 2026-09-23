#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, os, re, subprocess, sys, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
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
NS_CT='http://schemas.openxmlformats.org/package/2006/content-types'
NS_REL='http://schemas.openxmlformats.org/package/2006/relationships'

def run(*args,binary=False):
    cp=subprocess.run(args,cwd=ROOT,capture_output=True,text=not binary,check=True)
    return cp.stdout

def sha256(b): return hashlib.sha256(b).hexdigest()

def content_types(z):
    root=ET.fromstring(z.read('[Content_Types].xml')); defaults={}; overrides={}
    for e in root:
        ln=e.tag.rsplit('}',1)[-1]
        if ln=='Default': defaults[str(e.attrib.get('Extension','')).lower()]=e.attrib.get('ContentType','')
        elif ln=='Override': overrides[str(e.attrib.get('PartName','')).lstrip('/')]=e.attrib.get('ContentType','')
    out={}
    for n in z.namelist():
        if n.endswith('/'): continue
        out[n]=overrides.get(n,defaults.get(Path(n).suffix.lstrip('.').lower(),'application/octet-stream'))
    return out

def source_part_for_rel(relpart):
    if relpart=='_rels/.rels': return ''
    p=Path(relpart); parts=p.parts
    if len(parts)>=2 and parts[-2]=='_rels' and parts[-1].endswith('.rels'):
        return (Path(*parts[:-2])/parts[-1][:-5]).as_posix()
    return ''

def resolve_target(relpart,target):
    if not target: return ''
    if target.startswith('/'): return target.lstrip('/')
    src=source_part_for_rel(relpart); base=Path(src).parent if src else Path('.')
    return os.path.normpath((base/target).as_posix()).replace('\\','/').lstrip('./')

def classify(n):
    name=Path(n).name
    if name.startswith('00_INDEX_'): return 'INDEX'
    if re.match(r'0[1-9]_ACPOS_',name): return 'SYSTEM_LOGIC_NORMATIVE_CONTRACT'
    return 'PAGE_OR_SYSTEM_BASIC_DESIGN'

def main():
    contract=yaml.safe_load((ROOT/'.github/governance-source/active/source/10_REGISTRY/STAGE1_SOURCE_FACT_CONTRACTS.yaml').read_text()) or {}
    sc=contract.get('structured_document_source_projection_contract') or {}
    global_fail=[]
    for k in ['source_document_content_readiness_audit','raw_source_lock','projection','frozen_binary_source_part_materialization','reconciliation','pair_freeze','stage01_consumption','semantic_preservation']:
        if not sc.get(k): global_fail.append('CURRENT_PROJECTION_CONTRACT_MISSING:'+k)
    pp=(sc.get('projection') or {}).get('package_part_row_field_order') or []
    for k in ['package_part_path','content_type','size_bytes','part_sha256']:
        if k not in pp: global_fail.append('PACKAGE_PART_SCHEMA_MISSING:'+k)
    if (sc.get('stage01_consumption') or {}).get('binary_source_access')!='EXACT_FROZEN_BINARY_PART_RESOLVED_FROM_PROJECTION_ONLY':
        global_fail.append('STAGE01_BINARY_SOURCE_ACCESS_NOT_FROZEN_PROJECTION_ONLY')
    subprocess.run(['git','fetch','origin','0921acpos:refs/remotes/origin/0921acpos'],cwd=ROOT,check=True)
    listing=run('git','ls-tree','-r','-l',BRANCH)
    docs=[]
    for line in listing.splitlines():
        if '\t' not in line: continue
        meta,path=line.split('\t',1)
        if not path.lower().endswith('.docx'): continue
        blob=meta.split()[2]
        data=subprocess.run(['git','show',f'{BRANCH}:{path}'],cwd=ROOT,capture_output=True,check=True).stdout
        failures=[]; warnings=[]; row={'path':path,'git_blob_sha':blob,'size_bytes':len(data),'sha256':sha256(data),'document_kind':classify(path)}
        try:
            z=zipfile.ZipFile(io.BytesIO(data),'r')
            names=[n for n in z.namelist() if not n.endswith('/')]
            name_set=set(names)
            if len(name_set)!=len(names): failures.append('DUPLICATE_ZIP_MEMBER')
            for req in ['[Content_Types].xml','_rels/.rels','word/document.xml']:
                if req not in name_set: failures.append('DOCX_REQUIRED_PART_MISSING:'+req)
            ct=content_types(z)
            binaries=[n for n in names if not n.lower().endswith(('.xml','.rels'))]
            row['package_part_count']=len(names); row['binary_part_count']=len(binaries)
            row['image_part_count']=sum(1 for n in binaries if str(ct.get(n,'')).startswith('image/'))
            row['binary_suffixes']=sorted(set(Path(n).suffix.lower() for n in binaries))
            row['binary_hashes']=[{'part':n,'sha256':sha256(z.read(n)),'size_bytes':len(z.read(n)),'content_type':ct.get(n,'')} for n in binaries]
            rels=[]; image_rels=[]
            for rp in sorted(n for n in names if n.endswith('.rels')):
                try: rr=ET.fromstring(z.read(rp))
                except Exception as e: failures.append('RELATIONSHIP_XML_PARSE_FAILED:'+rp+':'+type(e).__name__); continue
                ids=set()
                for e in rr:
                    rid=e.attrib.get('Id',''); typ=e.attrib.get('Type',''); tgt=e.attrib.get('Target',''); mode=e.attrib.get('TargetMode','')
                    if rid in ids: failures.append('DUPLICATE_RELATIONSHIP_ID:'+rp+':'+rid)
                    ids.add(rid); rels.append((rp,rid,typ,tgt,mode))
                    if mode.lower()!='external':
                        resolved=resolve_target(rp,tgt)
                        if resolved and resolved not in name_set: failures.append('REL_TARGET_MISSING:'+rp+':'+rid+':'+resolved)
                    if typ.lower().endswith('/image'): image_rels.append((rp,rid,tgt,mode))
            row['relationship_count']=len(rels); row['image_relationship_count']=len(image_rels)
            xml_nodes=0; texts=[]; drawings=0; embeds=[]
            for xp in sorted(n for n in names if n.lower().endswith(('.xml','.rels'))):
                try: xr=ET.fromstring(z.read(xp))
                except Exception as e: failures.append('XML_PARSE_FAILED:'+xp+':'+type(e).__name__); continue
                for e in xr.iter():
                    xml_nodes+=1
                    local=e.tag.rsplit('}',1)[-1]
                    if local=='t' and e.text: texts.append(e.text)
                    if local=='drawing': drawings+=1
                    for ak,av in e.attrib.items():
                        al=ak.rsplit('}',1)[-1]
                        if al in {'embed','link'} and str(av).startswith('rId'): embeds.append(str(av))
            row['xml_node_count']=xml_nodes; row['drawing_count']=drawings
            text='\n'.join(texts); row['text_char_count']=len(text)
            row['domain_presence']={k:bool(re.search(p,text,re.I)) for k,p in DOMAIN_PATTERNS.items()}
            miss=[]
            if row['document_kind']=='PAGE_OR_SYSTEM_BASIC_DESIGN':
                miss=[k for k in UNIVERSAL_PAGE_DOMAINS if not row['domain_presence'][k]]
            elif row['document_kind']=='SYSTEM_LOGIC_NORMATIVE_CONTRACT':
                req=['IDENTITY_SCOPE','DATA_SCHEMA','INTEGRATION_RUNTIME','WORKFLOW_LIFECYCLE','QA_ACCEPTANCE']; miss=[k for k in req if not row['domain_presence'][k]]
            elif row['document_kind']=='INDEX' and len(text)<100:
                failures.append('INDEX_CONTENT_TOO_SPARSE')
            row['missing_universal_domains']=miss
            if miss: warnings.append('CONTENT_DOMAIN_REVIEW:'+','.join(miss))
            image_ids={rid for _,rid,_,_ in image_rels}
            missing=[rid for rid in sorted(set(embeds)) if rid not in image_ids]
            if missing: failures.append('DRAWING_EMBED_NOT_IMAGE_REL:'+','.join(missing))
            for rp,rid,tgt,mode in image_rels:
                if mode.lower()=='external': continue
                resolved=resolve_target(rp,tgt)
                if resolved in name_set and not str(ct.get(resolved,'')).startswith('image/'):
                    failures.append('IMAGE_REL_TARGET_NOT_IMAGE_CONTENT_TYPE:'+resolved)
            if drawings>0 and row['image_part_count']==0: failures.append('DRAWING_WITHOUT_BINARY_IMAGE_PART')
            row['projection_schema_compatibility']='PASS' if not failures else 'FAIL'
        except Exception as e:
            failures.append('DOCX_OPEN_OR_PARSE_EXCEPTION:'+type(e).__name__+':'+str(e)[:240]); row['projection_schema_compatibility']='FAIL'
        row['failures']=failures;row['warnings']=warnings;row['content_review_status']='REVIEW_REQUIRED' if warnings else 'NO_MACHINE_DETECTED_REQUIRED_DOMAIN_GAP'
        docs.append(row)
    docs.sort(key=lambda x:x['path'])
    fail=[d for d in docs if d['failures']]; review=[d for d in docs if d['warnings']]
    report={'artifact_type':'WORD_SOURCE_FLEET_FAST_FULL_DENOMINATOR_COMPATIBILITY_AUDIT','normative_authority':False,'governance_uid':((yaml.safe_load((ROOT/'governance/specifications/REGISTRY.yaml').read_text()) or {}).get('active_specification') or {}).get('governance_uid'),'source_branch':'0921acpos','source_head':run('git','rev-parse',BRANCH).strip(),'document_count':len(docs),'global_contract_failures':global_fail,'projection_compatibility_pass_count':len(docs)-len(fail),'projection_compatibility_fail_count':len(fail),'content_review_candidate_count':len(review),'result':'PASS' if not fail and not global_fail else 'FAIL','documents':docs}
    Path('/tmp/word_source_fleet_fast_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='documents'},ensure_ascii=False))
    for d in docs:
        print(json.dumps({'path':d['path'],'kind':d['document_kind'],'projection':d['projection_schema_compatibility'],'parts':d.get('package_part_count'),'xml_nodes':d.get('xml_node_count'),'rels':d.get('relationship_count'),'binary':d.get('binary_part_count'),'images':d.get('image_part_count'),'drawings':d.get('drawing_count'),'text_chars':d.get('text_char_count'),'missing_domains':d.get('missing_universal_domains'),'failures':d['failures']},ensure_ascii=False))
    if fail or global_fail: raise SystemExit(1)
if __name__=='__main__': main()
