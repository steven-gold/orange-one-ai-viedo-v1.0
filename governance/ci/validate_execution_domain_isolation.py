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
SCHEMA_REF='governance/execution-domains/STEP_CONTRACT_SCHEMA.yaml'
AUDIT_REF='governance/execution-domains/AUDIT_PROFILE.yaml'
BINDING_REF='governance/execution-domains/AUTHORITY_BINDINGS.yaml'
bindings=yaml.safe_load((ROOT/BINDING_REF).read_text()) or {}
errors=[]
schema=yaml.safe_load((ROOT/SCHEMA_REF).read_text()) or {}
required=schema.get('required_step_fields') or []
if not required: errors.append('UNIVERSAL_STEP_REQUIRED_FIELDS_EMPTY')
if schema.get('fixed_structure_across_all_pages_and_systems') is not True:
 errors.append('FIXED_STRUCTURE_NOT_ENFORCED')
if schema.get('page_specific_schema_variation')!='FORBIDDEN':
 errors.append('PAGE_SPECIFIC_SCHEMA_VARIATION_NOT_FORBIDDEN')

def validate_step(name, step, label):
 for key in required:
  if key not in step:
   errors.append(f'MISSING_STEP_FIELD:{name}:{label}:{key}')
  elif step[key] is None or step[key]=='' or step[key]==[]:
   errors.append(f'EMPTY_STEP_FIELD:{name}:{label}:{key}')

for name in DOMAINS:
 p=BASE/name/'DOMAIN.yaml'
 if not p.is_file(): errors.append(f'MISSING_DOMAIN_MANIFEST:{name}'); continue
 d=yaml.safe_load(p.read_text()) or {}
 uid,nxt=EXPECTED[name]
 if d.get('domain_uid')!=uid: errors.append(f'DOMAIN_UID_MISMATCH:{name}')
 if d.get('recursive_governance_tree_scan')!='FORBIDDEN': errors.append(f'RECURSIVE_SCAN_NOT_FORBIDDEN:{name}')
 if d.get('undeclared_rule_read')!='FORBIDDEN': errors.append(f'UNDECLARED_RULE_READ_NOT_FORBIDDEN:{name}')
 if d.get('execution_semantic')!='WEB-GOV-03-S062A': errors.append(f'STEPWISE_AUTHORITY_MISSING:{name}')
 if d.get('step_contract_schema')!=SCHEMA_REF: errors.append(f'STEP_SCHEMA_REF_MISMATCH:{name}')
 if d.get('audit_profile')!=AUDIT_REF: errors.append(f'AUDIT_PROFILE_REF_MISMATCH:{name}')
 if d.get('fixed_structure_across_pages_and_systems') is not True: errors.append(f'FIXED_STRUCTURE_NOT_BOUND:{name}')
 if d.get('page_specific_step_shape_variation')!='FORBIDDEN': errors.append(f'PAGE_STEP_VARIATION_NOT_FORBIDDEN:{name}')
 if nxt and d.get('next_domain')!=nxt: errors.append(f'NEXT_DOMAIN_MISMATCH:{name}')
 refs=[]
 for k in ('authority','shared_required','audit_handoff'):
  v=d.get(k) or []
  refs.extend(v if isinstance(v,list) else [v])
 refs.extend([d.get('step_contract_schema'),d.get('audit_profile'),d.get('step_registry')])
 for ref in [x for x in refs if x]:
  if not (ROOT/ref).is_file(): errors.append(f'MISSING_DECLARED_RULE:{name}:{ref}')
 sp=ROOT/(d.get('step_registry') or '')
 if sp.is_file():
  sd=yaml.safe_load(sp.read_text()) or {}
  if sd.get('domain_uid')!=uid: errors.append(f'STEP_REGISTRY_DOMAIN_MISMATCH:{name}')
  if sd.get('step_schema_ref')!=SCHEMA_REF: errors.append(f'STEP_REGISTRY_SCHEMA_MISMATCH:{name}')
  if sd.get('audit_profile_ref')!=AUDIT_REF: errors.append(f'STEP_REGISTRY_AUDIT_MISMATCH:{name}')
  if sd.get('authority_binding_registry_ref')!=BINDING_REF: errors.append(f'AUTHORITY_BINDING_REF_MISMATCH:{name}')
  if sd.get('authority_mode')!='EXECUTION_PROJECTION_ONLY': errors.append(f'AUTHORITY_MODE_INVALID:{name}')
  if sd.get('may_create_new_normative_requirement') is not False: errors.append(f'NORMATIVE_DUPLICATION_NOT_FORBIDDEN:{name}')
  binding_key={'BASIC_DESIGN':'basic_design','WORD_YAML':'word_yaml','STAGE':'stage','AUDIT':'audit'}[name]
  bmap=bindings.get(binding_key) or {}
  if name=='STAGE':
   op=sd.get('operation_contract') or {}
   cl=sd.get('stage_closure_contract') or {}
   validate_step(name,op,'operation_contract')
   validate_step(name,cl,'stage_closure_contract')
   for label in ('operation_contract','stage_closure_contract'):
    if not bmap.get(label): errors.append(f'MISSING_AUTHORITY_BINDING:{name}:{label}')
   if sd.get('execution_rules',{}).get('every_registered_operation_must_instantiate_operation_contract') is not True:
    errors.append('STAGE_OPERATION_TEMPLATE_NOT_MANDATORY')
  else:
   steps=sd.get('steps') or []
   if not steps: errors.append(f'NO_STEPS:{name}')
   for step in steps:
    label=step.get('step_uid','UNKNOWN')
    validate_step(name,step,label)
    if not bmap.get(label): errors.append(f'MISSING_AUTHORITY_BINDING:{name}:{label}')
   step_ids={s.get('step_uid') for s in steps}
   for label in bmap:
    if label not in step_ids: errors.append(f'ORPHAN_AUTHORITY_BINDING:{name}:{label}')

audit=yaml.safe_load((ROOT/AUDIT_REF).read_text()) or {}
if audit.get('fixed_audit_dimensions') is None: errors.append('AUDIT_DIMENSIONS_MISSING')
if audit.get('applies_to_every_page_system_and_execution_step') is not True: errors.append('AUDIT_NOT_UNIVERSAL')
if errors:
 print('\n'.join(errors)); sys.exit(1)
print(f'PASS: 4 domains isolated; fixed step schema fields={len(required)}; universal audit profile bound; all declared steps structurally complete')
