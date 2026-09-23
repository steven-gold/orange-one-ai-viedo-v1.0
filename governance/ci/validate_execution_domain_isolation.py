from pathlib import Path
import sys, yaml

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'governance/execution-domains'
DOMAINS=['BASIC_DESIGN','WORD_YAML','STAGE','AUDIT']
EXPECTED={
 'BASIC_DESIGN':('BASIC_DESIGN_GOVERNANCE_FLOW','WORD_YAML'),
 'WORD_YAML':('WORD_YAML_SOURCE_FLOW','STAGE'),
 'STAGE':('STAGE_LIFECYCLE_FLOW',None),
 'AUDIT':('AUDIT_CLOSURE_FLOW',None),
}
errors=[]
for name in DOMAINS:
 p=BASE/name/'DOMAIN.yaml'
 if not p.is_file(): errors.append(f'MISSING_DOMAIN_MANIFEST:{name}'); continue
 d=yaml.safe_load(p.read_text()) or {}
 uid,nxt=EXPECTED[name]
 if d.get('domain_uid')!=uid: errors.append(f'DOMAIN_UID_MISMATCH:{name}')
 if d.get('recursive_governance_tree_scan')!='FORBIDDEN': errors.append(f'RECURSIVE_SCAN_NOT_FORBIDDEN:{name}')
 if d.get('undeclared_rule_read')!='FORBIDDEN': errors.append(f'UNDECLARED_RULE_READ_NOT_FORBIDDEN:{name}')
 if d.get('execution_semantic')!='WEB-GOV-03-S062A': errors.append(f'STEPWISE_AUTHORITY_MISSING:{name}')
 if nxt and d.get('next_domain')!=nxt: errors.append(f'NEXT_DOMAIN_MISMATCH:{name}')
 refs=[]
 for k in ('authority','shared_required','audit_handoff'):
  v=d.get(k) or []
  refs.extend(v if isinstance(v,list) else [v])
 for ref in refs:
  if not (ROOT/ref).is_file(): errors.append(f'MISSING_DECLARED_RULE:{name}:{ref}')
if errors:
 print('\n'.join(errors)); sys.exit(1)
print('PASS: execution domains isolated; declared rule references resolve; stepwise authority bound')
