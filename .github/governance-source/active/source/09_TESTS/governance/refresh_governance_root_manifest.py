#!/usr/bin/env python3
from pathlib import Path
import yaml,hashlib,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]; P=ROOT/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    d=yaml.safe_load(P.read_text()) or {}
    for group in ('current_artifacts','validators'):
        for rec in d.get(group) or []:
            p=ROOT/rec['path']
            if rec['path']=='10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml':
                rec['artifact_uid']='REG-GOVERNANCE-ROOT-MANIFEST-001'; rec['sha256']='SELF_EXCLUDED'; rec['hash_policy']='SELF_EXCLUDED_TO_AVOID_SELF_REFERENCE'; continue
            if not p.exists(): print('missing',rec['path'],file=sys.stderr); return 2
            obj={}
            if p.suffix in ('.yaml','.yml'):
                obj=yaml.safe_load(p.read_text()) or {}
            rec['artifact_uid']=obj.get('artifact_uid') or obj.get('registry_uid') or rec.get('artifact_uid') or ('DOC-'+p.stem if p.suffix=='.md' else None)
            rec['sha256']=sha(p)
    P.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=160))
    return 0
if __name__=='__main__': raise SystemExit(main())
