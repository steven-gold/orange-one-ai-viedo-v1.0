#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, os, re, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.github/governance-source/active/source'
BASE_PATH=ROOT/'.github/governance-maintenance/promote_blueprint_traceability_governance.py'
spec=importlib.util.spec_from_file_location('acpos_promotion_base',BASE_PATH)
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

OLD_UID='GOV-REV-20260919-BASIC-DESIGN-ATOMIC-MATERIALIZATION-HARDENING'
NEW_UID='GOV-REV-20260919-ASSET-STAGE01-STAGE02-SHARED-CONTRACT-HARDENING'
OLD_DISPLAY='v2.2.12'
NEW_DISPLAY='v2.2.13'
NEW_SOURCE_REV='v2.2.13-asset-stage01-stage02-shared-contract-hardening'
AUTH_UID='USR-DIRECTIVE-20260920-ASSET-STAGE01-STAGE02-SHARED-CONTRACT-HARDENING-R3'
WORK_UNIT='WU-GOV-ASSET-STAGE01-STAGE02-SHARED-CONTRACT-HARDENING-001'
NEW_PACKAGE='AI_WEB_GOVERNANCE_FULL_LIFECYCLE_v2.2.13_ASSET_STAGE01_STAGE02_SHARED_CONTRACT_HARDENING_LOCAL_VERIFIED.zip'

for k,v in {
 'OLD_UID':OLD_UID,'NEW_UID':NEW_UID,'OLD_DISPLAY':OLD_DISPLAY,'NEW_DISPLAY':NEW_DISPLAY,
 'NEW_SOURCE_REV':NEW_SOURCE_REV,'AUTH_UID':AUTH_UID,'WORK_UNIT':WORK_UNIT,'NEW_PACKAGE':NEW_PACKAGE
}.items(): setattr(base,k,v)

def load(p):
    return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}

def dump(p,obj):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(yaml.safe_dump(obj,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')

def replace_once(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}:expected_one_target actual={n}')
    return text.replace(old,new,1)

def insert_before(path,anchor,marker,body):
    p=Path(path); s=p.read_text(encoding='utf-8')
    if marker in s: return
    if anchor not in s: raise RuntimeError(f'anchor missing:{anchor}:{path}')
    p.write_text(s.replace(anchor,body.rstrip()+'\n\n'+anchor,1),encoding='utf-8')

def mutate_mother():
    insert_before(SOURCE/'12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md',
      '<!-- SECTION_UID: WEB-GOV-01-S072 -->',
      'COMMON_STAGE12_CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION',
      '''COMMON_STAGE12_CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION

For any required Action with no visible Control, the functional-contract capability MUST execute CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION before classifying the absence as an Authority Gap. The resolver MUST use structured Current evidence, not labels or similarity: existing user-intent/control bindings; runtime_binding decision/source semantics; exact Gate and Permission; exactly resolved Runtime/Port and registered Operation; current State/Event or success transition; Journey/Workbench intent; and whether adding a Control would create a user behavior not present in Current Authority.

When the combined Current evidence uniquely proves a system-owned/derived operation and no Current Authority defines explicit user initiation, the result MUST be SYSTEM_TRIGGER_BINDING_MISSING with AUTO_REMEDIABLE disposition. The owning functional-contract capability MUST materialize an explicit system_trigger contract into the single Current functional-contract owner and MUST_NOT create a new visual Control. Port exposure or result state_event alone is insufficient; the deterministic proof is the complete structured evidence set.

Only when Current Authority materially supports two or more distinct viable initiation behaviors MAY the item become AUTHORITY_GAP / USER_DECISION_REQUIRED. Missing explicit trigger syntax by itself MUST_NOT manufacture a user-vs-system product choice.''')

    insert_before(SOURCE/'12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md',
      '<!-- SECTION_UID: WEB-GOV-02-S070 -->',
      'COMMON_STAGE12_PRODUCER_CONSUMER_SCHEMA_IDENTITY',
      '''COMMON_STAGE12_PRODUCER_CONSUMER_SCHEMA_IDENTITY

Every generated or materialized Stage output consumed by another registered operation MUST satisfy an exact Producer/Consumer Schema Identity contract before the consumer may mutate Current product state. The contract MUST bind artifact_type, schema_version, canonical field names, required/optional status, field types, producer owner, consumer owner, and accepted schema revision.

A consumer MUST_NOT silently accept a renamed, legacy, approximate, or alias field when the canonical producer field is missing. Such drift is PRODUCER_CONSUMER_SCHEMA_MISMATCH and MUST block before materialization. For the functional-contract audit-event binding role, audit_event_uid is the canonical field identity; event_uid MUST_NOT be used as a compatibility fallback for that field role.''')

    insert_before(SOURCE/'12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md',
      '<!-- SECTION_UID: WEB-GOV-03-S063 -->',
      'COMMON_STAGE12_ORDER_AND_NO_HISTORY_FALLBACK',
      '''COMMON_STAGE12_ORDER_AND_NO_HISTORY_FALLBACK

Effectful Product Stage execution MUST preserve the governed task-layer order: terminalize or legally suspend the current Work Unit -> persist Resume -> execute WORK_UNIT_RESOLUTION_GATE when the primary Work Unit changes -> activate the resolved Work Unit -> rerun SESSION_BOOTSTRAP_RESUME_GATE -> execute. A materializer, validator, workflow input, environment variable, retry path, or nearby Stage identity MUST_NOT bypass this order or force a product Work Unit into the foreground.

Historical commits, historical Stage outputs, superseded candidates, prior generated artifacts, and old run directories MAY be used only for provenance or registered negative regression. They MUST_NOT supply a missing Current product value, contract field, trigger, Authority binding, denominator, or completion credit. Fresh replay MUST begin from registered immutable inputs and Current Authority; if those Current inputs are insufficient, execution must expose the owning gap instead of reading history to manufacture the missing product data.''')

    insert_before(SOURCE/'12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md',
      '<!-- SECTION_UID: WEB-GOV-04-S079 -->',
      'COMMON_STAGE12_TRIGGER_SCHEMA_AUDIT',
      '''COMMON_STAGE12_TRIGGER_SCHEMA_AUDIT

Audit MUST verify CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION occurred before any no-Control Action was escalated to Authority Gap, and MUST distinguish deterministic system-trigger binding gaps from genuinely ambiguous product choices. A deterministic system-only operation MUST have no invented visual Control and must reach the Current functional-contract owner through an explicit system_trigger materialization before receiving closure credit.

Audit MUST also verify exact Producer/Consumer Schema Identity for every generated-to-consumer edge, including canonical field names/types/schema versions and owners. Alias fallback that hides schema drift is blocking. Reusable Stage consumers MUST contain no fixed product/page identity or historical run default as their implicit Current scope. Historical product values may not satisfy Current missing data. Task-layer activation must follow persisted terminal/resume/WUR order and may not be overridden by executor-local environment state.''')

def mutate_invariants():
    p=SOURCE/'10_REGISTRY/STAGE_EXECUTION_INVARIANT_REGISTRY.yaml'
    d=load(p); inv=d.setdefault('invariants',{})
    inv['CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION']={
      'required_before_no_control_action_gap_escalation':True,
      'structured_evidence_required':['USER_INTENT_OR_CONTROL_BINDING','RUNTIME_DECISION_SOURCE','GATE','PERMISSION','EXACT_RUNTIME_PORT','REGISTERED_OPERATION','SUCCESS_STATE_OR_EVENT','JOURNEY_OR_WORKBENCH_INTENT'],
      'port_exposure_or_state_event_alone_is_trigger':False,
      'deterministic_system_owned_outcome':'SYSTEM_TRIGGER_BINDING_MISSING_AUTO_REMEDIABLE',
      'explicit_system_trigger_materialization_required':True,
      'new_visual_control_for_system_only_operation':False,
      'authority_gap_minimum_materially_distinct_viable_behaviors':2,
      'missing_trigger_syntax_alone_is_authority_gap':False,
    }
    inv['PRODUCER_CONSUMER_SCHEMA_IDENTITY']={
      'artifact_type_exact':True,'schema_version_exact':True,'canonical_field_name_exact':True,
      'field_type_exact':True,'required_optional_contract_exact':True,'producer_owner_required':True,
      'consumer_owner_required':True,'alias_or_legacy_field_fallback':False,
      'mismatch':'PRODUCER_CONSUMER_SCHEMA_MISMATCH',
      'stage02_audit_event_canonical_field':'audit_event_uid',
      'stage02_audit_event_legacy_alias_forbidden':'event_uid',
    }
    inv['NO_HISTORY_PRODUCT_VALUE_FALLBACK']={
      'history_role':['PROVENANCE','NEGATIVE_REGRESSION'],
      'historical_commit_or_generated_output_may_fill_current_product_value':False,
      'historical_stage_result_may_receive_current_completion_credit':False,
      'fresh_replay_source':'REGISTERED_IMMUTABLE_INPUTS_PLUS_CURRENT_AUTHORITY',
      'missing_current_input':'EXPOSE_OWNING_GAP_NOT_HISTORY_FALLBACK',
    }
    inv['TASK_LAYER_EFFECTFUL_TRANSITION_ORDER']={
      'required_order':['TERMINALIZE_OR_LEGALLY_SUSPEND_CURRENT_WORK_UNIT','PERSIST_RESUME','WORK_UNIT_RESOLUTION_GATE_WHEN_PRIMARY_WORK_UNIT_CHANGES','ACTIVATE_RESOLVED_WORK_UNIT','SESSION_BOOTSTRAP_RESUME_GATE','EFFECTFUL_EXECUTION'],
      'materializer_or_environment_may_force_primary_task_layer':False,
      'nearby_stage_or_retry_may_skip_resolution':False,
      'violation':'BLOCK',
    }
    d['governance_revision']=NEW_SOURCE_REV
    dump(p,d)

    p=SOURCE/'10_REGISTRY/GOVERNANCE_ACCEPTANCE_AUDIT_BLUEPRINT.yaml'
    d=load(p); c=d.setdefault('stage_execution_invariant_contract',{})
    c['control_vs_system_trigger_resolution_required']=True
    c['deterministic_system_trigger_materialization_required']=True
    c['producer_consumer_schema_identity_required']=True
    c['producer_consumer_alias_fallback_blocked']=True
    c['no_history_product_value_fallback_required']=True
    c['task_layer_effectful_transition_order_required']=True
    if 'governance_revision' in d: d['governance_revision']=NEW_SOURCE_REV
    dump(p,d)

def mutate_current_components():
    p=ROOT/'governance/specifications/current/BOUNDED_FUNCTIONAL_COMPLETION.yaml'
    d=load(p); rules=d.setdefault('rules',{})
    rules['CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION']={
      'activation':'ACTION_HAS_NO_VISIBLE_CONTROL_AND_NO_EXPLICIT_TRIGGER_BINDING',
      'structured_current_evidence_required':True,
      'deterministic_system_owned_operation':'SYSTEM_TRIGGER_BINDING_MISSING_AUTO_REMEDIABLE',
      'explicit_system_trigger_materialization_required':True,
      'new_visual_control_for_system_only_operation':'FORBIDDEN',
      'two_or_more_materially_distinct_viable_initiations':'AUTHORITY_GAP',
      'missing_explicit_trigger_syntax_alone':'NOT_AUTHORITY_GAP',
    }
    d['schema_version']=7
    dump(p,d)

    p=ROOT/'governance/specifications/current/EXECUTION_CYCLE_CONTROL.yaml'
    d=load(p)
    d['producer_consumer_schema_identity']={
      'required_before_materialization':True,
      'required_identity':['artifact_type','schema_version','canonical_field_names','required_optional_status','field_types','producer_owner','consumer_owner','accepted_schema_revision'],
      'alias_fallback':False,
      'mismatch':'PRODUCER_CONSUMER_SCHEMA_MISMATCH',
      'stage02_audit_event_canonical_field':'audit_event_uid',
    }
    d['no_history_product_value_fallback']={
      'historical_values_are_current_product_inputs':False,
      'fresh_replay_source':'REGISTERED_IMMUTABLE_INPUTS_PLUS_CURRENT_AUTHORITY',
      'missing_current_value':'EXPOSE_OWNING_GAP',
    }
    d['task_layer_effectful_transition_order']={
      'required_order':['TERMINALIZE_OR_LEGALLY_SUSPEND_CURRENT_WORK_UNIT','PERSIST_RESUME','WORK_UNIT_RESOLUTION_GATE_WHEN_PRIMARY_WORK_UNIT_CHANGES','ACTIVATE_RESOLVED_WORK_UNIT','SESSION_BOOTSTRAP_RESUME_GATE','EFFECTFUL_EXECUTION'],
      'environment_override':False,'materializer_override':False,
    }
    d['schema_version']=5
    dump(p,d)

def mutate_source_validator_and_regression():
    p=SOURCE/'09_TESTS/governance/validate_stage_execution_invariants.py'
    s=p.read_text(encoding='utf-8')
    old="'COMMON_ENGINE_DEFECT_INTERRUPT','GENERATED_OUTPUT_PERSISTENCE']"
    new="'COMMON_ENGINE_DEFECT_INTERRUPT','GENERATED_OUTPUT_PERSISTENCE','CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION','PRODUCER_CONSUMER_SCHEMA_IDENTITY','NO_HISTORY_PRODUCT_VALUE_FALLBACK','TASK_LAYER_EFFECTFUL_TRANSITION_ORDER']"
    s=replace_once(s,old,new,'validator required invariants')
    anchor="    rv=inv.get('REVIEW_VS_CLOSURE_SEPARATION') or {}\n"
    extra="""    trig=inv.get('CONTROL_VS_SYSTEM_TRIGGER_RESOLUTION') or {}
    if trig.get('required_before_no_control_action_gap_escalation') is not True or trig.get('port_exposure_or_state_event_alone_is_trigger') is not False or trig.get('deterministic_system_owned_outcome')!='SYSTEM_TRIGGER_BINDING_MISSING_AUTO_REMEDIABLE' or trig.get('explicit_system_trigger_materialization_required') is not True or trig.get('new_visual_control_for_system_only_operation') is not False or trig.get('authority_gap_minimum_materially_distinct_viable_behaviors')!=2 or trig.get('missing_trigger_syntax_alone_is_authority_gap') is not False: failures.append('control_vs_system_trigger_resolution_incomplete')
    pcs=inv.get('PRODUCER_CONSUMER_SCHEMA_IDENTITY') or {}
    if pcs.get('canonical_field_name_exact') is not True or pcs.get('field_type_exact') is not True or pcs.get('alias_or_legacy_field_fallback') is not False or pcs.get('mismatch')!='PRODUCER_CONSUMER_SCHEMA_MISMATCH' or pcs.get('stage02_audit_event_canonical_field')!='audit_event_uid' or pcs.get('stage02_audit_event_legacy_alias_forbidden')!='event_uid': failures.append('producer_consumer_schema_identity_incomplete')
    hist=inv.get('NO_HISTORY_PRODUCT_VALUE_FALLBACK') or {}
    if hist.get('historical_commit_or_generated_output_may_fill_current_product_value') is not False or hist.get('historical_stage_result_may_receive_current_completion_credit') is not False or hist.get('fresh_replay_source')!='REGISTERED_IMMUTABLE_INPUTS_PLUS_CURRENT_AUTHORITY': failures.append('no_history_product_value_fallback_incomplete')
    order=inv.get('TASK_LAYER_EFFECTFUL_TRANSITION_ORDER') or {}
    if order.get('materializer_or_environment_may_force_primary_task_layer') is not False or order.get('nearby_stage_or_retry_may_skip_resolution') is not False or len(order.get('required_order') or [])!=6: failures.append('task_layer_effectful_transition_order_incomplete')
"""
    if extra.strip() not in s:
        s=replace_once(s,anchor,extra+anchor,'validator insert')
    p.write_text(s,encoding='utf-8')

    p=SOURCE/'09_TESTS/governance/test_v2_1_13_stage_execution_invariants.py'
    s=p.read_text(encoding='utf-8')
    helper="""\n# v2.2.13 shared contract hardening helpers.
def trigger_resolution(has_control=False,source_derived=False,exact_port=False,gate=False,permission=False,success=False,explicit=False):
    if has_control: return 'CONTROL_BOUND'
    if explicit: return 'EXPLICIT_TRIGGER_BOUND'
    if source_derived and exact_port and gate and permission and success: return 'SYSTEM_TRIGGER_BINDING_MISSING_AUTO_REMEDIABLE'
    return 'UNRESOLVED'
def schema_identity(producer_field,consumer_field,producer_type='string',consumer_type='string',version_ok=True):
    return producer_field==consumer_field and producer_type==consumer_type and version_ok
def history_fallback_allowed(role):
    return role in {'PROVENANCE','NEGATIVE_REGRESSION'}
def task_layer_transition_allowed(current_terminal,resume_persisted,wur_passed,resolved_active,bootstrap_passed):
    return all((current_terminal,resume_persisted,wur_passed,resolved_active,bootstrap_passed))
"""
    helper_anchor="# v2.1.15 canonical execution optimization regressions."
    if 'def trigger_resolution(' not in s:
        s=replace_once(s,helper_anchor,helper+'\n'+helper_anchor,'regression helper insert')
    replacements={
      "res.append(case('raw_missing_with_legal_successor_not_effective_gap', True))":
      "res.append(case('deterministic_system_trigger_is_auto_remediable', trigger_resolution(source_derived=True,exact_port=True,gate=True,permission=True,success=True)=='SYSTEM_TRIGGER_BINDING_MISSING_AUTO_REMEDIABLE'))",
      "res.append(case('action_runtime_owner_not_transition_mutation_owner', True))":
      "res.append(case('audit_event_uid_schema_identity_rejects_event_uid_alias', schema_identity('audit_event_uid','audit_event_uid') and not schema_identity('audit_event_uid','event_uid')))",
      "res.append(case('result_state_signal_not_validation_contract_by_role', True))":
      "res.append(case('historical_product_value_fallback_forbidden', history_fallback_allowed('CURRENT_PRODUCT_VALUE') is False))",
      "res.append(case('untracked_generated_output_requires_status_aware_persistence', True))":
      "res.append(case('task_layer_transition_requires_terminal_resume_wur_active_bootstrap', task_layer_transition_allowed(True,True,True,True,True) and not task_layer_transition_allowed(False,True,True,True,True)))"
    }
    for old,new in replacements.items():
        s=replace_once(s,old,new,'replace placeholder regression')
    if "out['total']==26 and out['passed_expectations']==26" not in s:
        raise RuntimeError('mandatory denominator drift before write')
    p.write_text(s,encoding='utf-8')

def mutate_scanner():
    p=ROOT/'governance/ci/run_current_stage2_actual_test.py'
    s=p.read_text(encoding='utf-8')
    s=s.replace("SELF_TEST_APPLICABILITY_PROJECTION = '--self-test-applicability-projection' in sys.argv\nRUN_ROOT_ENV",
                "SELF_TEST_APPLICABILITY_PROJECTION = '--self-test-applicability-projection' in sys.argv\nSELF_TEST_SHARED_CONTRACT = '--self-test-shared-contract-hardening' in sys.argv\nRUN_ROOT_ENV")
    s=s.replace("if not RUN_ROOT_ENV and not (SELF_TEST_REVALIDATION_AUTHORITY or SELF_TEST_APPLICABILITY_PROJECTION):",
                "if not RUN_ROOT_ENV and not (SELF_TEST_REVALIDATION_AUTHORITY or SELF_TEST_APPLICABILITY_PROJECTION or SELF_TEST_SHARED_CONTRACT):")
    marker="def fresh_scan(page: str, raw: dict, unresolved_authority_by_ref: dict):\n"
    helper="""def control_vs_system_trigger_resolution(aid: str, action: dict, controls_by_action: dict, transitions_by_action: dict, ports: dict):
    if controls_by_action.get(aid):
        return {'status':'CONTROL_BOUND'}
    if present(action, 'trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind') or bool(transitions_by_action.get(aid)):
        return {'status':'EXPLICIT_TRIGGER_BOUND'}
    rb=action.get('runtime_binding') or {}
    decision=str(rb.get('decision') or '')
    if decision not in {'SOURCE_DERIVED','SOURCE_DERIVED_CLOSURE'}:
        return {'status':'UNRESOLVED'}
    refs=[]
    for field in ('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid'):
        puid=rb.get(field)
        if puid and puid in ports:
            refs.append((field,puid,ports[puid]))
    uniq={puid:(field,port) for field,puid,port in refs}
    if len(uniq)!=1:
        return {'status':'UNRESOLVED'}
    puid,(field,port)=next(iter(uniq.items()))
    operation=port.get('operation') or port.get('registered_operation')
    permission=port.get('permission') or port.get('registered_permission')
    state_event=str(port.get('state_event') or '')
    if not operation or not permission or not state_event or not action.get('gate_uid') or not action.get('permission_uid'):
        return {'status':'UNRESOLVED'}
    return {'status':'DETERMINISTIC_SYSTEM_TRIGGER_REQUIRED','contract':{
        'trigger_kind':'SYSTEM_DERIVED_GOVERNED_OPERATION',
        'source_decision':decision,
        'gate_uid':action.get('gate_uid'),
        'runtime_port_uid':puid,
        'runtime_port_binding_field':field,
        'registered_operation':operation,
        'success_state_event':state_event,
        'user_control_required':False,
    }}

def _self_test_shared_contract_hardening():
    controls=defaultdict(list); transitions=defaultdict(list)
    ports={'PORT-1':{'registered_operation':'createDerivedRecord','registered_permission':'record.write','state_event':'REVIEW->OPEN | record.created'}}
    action={'permission_uid':'PERM-1','gate_uid':'GATE-1','effect_type':'CREATE','runtime_binding':{'binding_kind':'SOURCE_INTEGRATION_PORT','port_uid':'PORT-1','decision':'SOURCE_DERIVED'}}
    exact=control_vs_system_trigger_resolution('ACT-1',action,controls,transitions,ports)
    assert exact.get('status')=='DETERMINISTIC_SYSTEM_TRIGGER_REQUIRED', exact
    assert exact['contract']['user_control_required'] is False
    ambiguous={**action,'runtime_binding':dict(action['runtime_binding'])}; ambiguous['runtime_binding'].pop('decision')
    assert control_vs_system_trigger_resolution('ACT-2',ambiguous,controls,transitions,ports).get('status')=='UNRESOLVED'
    controls['ACT-3'].append('CTRL-1')
    assert control_vs_system_trigger_resolution('ACT-3',action,controls,transitions,ports).get('status')=='CONTROL_BOUND'
    print('PASS: control-vs-system-trigger shared semantic resolution self-test')

"""
    if 'def control_vs_system_trigger_resolution' not in s:
        s=replace_once(s,marker,helper+marker,'scanner helper insert')
    old="""        explicit_trigger = present(action, 'trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind') or bool(transitions_by_action.get(aid))
        if not controls_by_action.get(aid) and not explicit_trigger:
            add(gaps, page, 'ARCHITECTURE_GAP', 'ACTION_WITHOUT_CONTROL_OR_TRIGGER', aid, 'no registered control or exact transition/system trigger')
"""
    new="""        trigger_resolution = control_vs_system_trigger_resolution(aid, action, controls_by_action, transitions_by_action, ports)
        if not controls_by_action.get(aid) and trigger_resolution.get('status') not in {'EXPLICIT_TRIGGER_BOUND','CONTROL_BOUND'}:
            if trigger_resolution.get('status') == 'DETERMINISTIC_SYSTEM_TRIGGER_REQUIRED':
                add(gaps, page, 'ARCHITECTURE_GAP', 'SYSTEM_TRIGGER_BINDING_MISSING', aid, json.dumps(trigger_resolution.get('contract') or {}, ensure_ascii=False, sort_keys=True), 'AUTO_REMEDIABLE_FUNCTIONAL_CLOSURE')
            else:
                add(gaps, page, 'ARCHITECTURE_GAP', 'ACTION_WITHOUT_CONTROL_OR_TRIGGER', aid, 'no registered control or deterministic system-trigger proof')
"""
    if old not in s: raise RuntimeError('scanner trigger block drift')
    s=s.replace(old,new,1)
    branch="""if SELF_TEST_SHARED_CONTRACT:
    _self_test_shared_contract_hardening()
    raise SystemExit(0)
"""
    anchor="if SELF_TEST_APPLICABILITY_PROJECTION:\n    _self_test_applicability_and_contract_projection()\n    raise SystemExit(0)\n"
    if branch not in s:
        s=replace_once(s,anchor,anchor+branch,'scanner self-test branch')
    p.write_text(s,encoding='utf-8')

def mutate_materializer():
    p=ROOT/'governance/ci/materialize_current_stage2_closure_artifacts.py'
    s=p.read_text(encoding='utf-8')
    # remove active legacy constants; Current dynamic path does not consume them.
    start=s.index('ROOT = Path(__file__).resolve().parents[2]\n')
    ctx=s.index('\ndef die(',start)
    header="""ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"

"""
    s=s[:start]+header+s[ctx+1:]
    # exact schema helper and deterministic trigger resolver.
    anchor='def _current_design_context():\n'
    helper="""def _require_record_schema(record: dict, required: dict, context: str) -> None:
    for field, typ in required.items():
        if field not in record or record.get(field) in (None, ''):
            raise SystemExit(f'BLOCK: PRODUCER_CONSUMER_SCHEMA_MISMATCH:{context}:missing:{field}')
        if typ is not None and not isinstance(record.get(field), typ):
            raise SystemExit(f'BLOCK: PRODUCER_CONSUMER_SCHEMA_MISMATCH:{context}:type:{field}')
    if context == 'STAGE02_AUDIT_EVENT_BINDING' and 'event_uid' in record and 'audit_event_uid' not in record:
        raise SystemExit('BLOCK: PRODUCER_CONSUMER_SCHEMA_MISMATCH:STAGE02_AUDIT_EVENT_BINDING:event_uid_alias_forbidden')

def _deterministic_system_trigger(action_uid: str, action: dict, raw_reg: dict):
    controls=[x for x in (raw_reg.get('controls') or []) if isinstance(x,dict) and x.get('action_uid')==action_uid]
    if controls:
        return None
    rb=action.get('runtime_binding') or {}
    decision=str(rb.get('decision') or '')
    if decision not in {'SOURCE_DERIVED','SOURCE_DERIVED_CLOSURE'}:
        return None
    ports=index(raw_reg.get('integration_ports'),'port_uid')
    refs=[]
    for field in ('port_uid','persist_via_port_uid','execute_port_uid','decision_port_uid'):
        puid=rb.get(field)
        if puid and puid in ports:
            refs.append((field,puid,ports[puid]))
    uniq={puid:(field,port) for field,puid,port in refs}
    if len(uniq)!=1:
        return None
    puid,(field,port)=next(iter(uniq.items()))
    operation=port.get('operation') or port.get('registered_operation')
    permission=port.get('permission') or port.get('registered_permission')
    state_event=str(port.get('state_event') or '')
    if not operation or not permission or not state_event or not action.get('gate_uid') or not action.get('permission_uid'):
        return None
    return {'trigger_kind':'SYSTEM_DERIVED_GOVERNED_OPERATION','source_decision':decision,'gate_uid':action.get('gate_uid'),'runtime_port_uid':puid,'runtime_port_binding_field':field,'registered_operation':operation,'success_state_event':state_event,'user_control_required':False}

def _self_test_shared_contract_hardening():
    good={'action_uid':'ACT-1','gate_uid':'GATE-1','permission_uid':'PERM-1','runtime_binding':{'port_uid':'PORT-1','decision':'SOURCE_DERIVED'}}
    reg={'controls':[],'integration_ports':[{'port_uid':'PORT-1','registered_operation':'createRecord','registered_permission':'record.write','state_event':'REVIEW->OPEN | record.created'}]}
    assert _deterministic_system_trigger('ACT-1',good,reg)
    bad=copy.deepcopy(good); bad['runtime_binding'].pop('decision')
    assert _deterministic_system_trigger('ACT-1',bad,reg) is None
    _require_record_schema({'action_uid':'ACT-1','audit_event_uid':'audit.record.created'},{'action_uid':str,'audit_event_uid':str},'STAGE02_AUDIT_EVENT_BINDING')
    try:
        _require_record_schema({'action_uid':'ACT-1','event_uid':'audit.record.created'},{'action_uid':str,'audit_event_uid':str},'STAGE02_AUDIT_EVENT_BINDING')
    except SystemExit:
        pass
    else:
        raise AssertionError('event_uid alias unexpectedly accepted')
    print('PASS: Stage-02 materializer shared trigger/schema self-test')

"""
    if 'def _require_record_schema' not in s:
        s=replace_once(s,anchor,helper+anchor,'materializer helper insert')
    old="""    blockers = semantic.get("blocking_authority_selection") or []
    if len(blockers) != 1 or not blockers[0].get("target_uid"):
        die(f"CURRENT_DESIGN_AUTHORITY_SELECTION_DENOMINATOR_DRIFT:{blockers!r}")
    authority_target = str(blockers[0]["target_uid"])
    rows = list(problem.get("problems") or [])
    if int(problem.get("open_problem_count") or 0) != len(rows):
        die("CURRENT_PROBLEM_REGISTER_OPEN_DENOMINATOR_DRIFT")
    finding_trigger_rows = [x for x in rows if str(x.get("target_uid") or "") == authority_target and x.get("category") == "ACTION_WITHOUT_CONTROL_OR_TRIGGER"]
    if len(finding_trigger_rows) != 1:
        die(f"CURRENT_AUTHORITY_GAP_PROBLEM_IDENTITY_DRIFT:{[(x.get('problem_uid'),x.get('category'),x.get('target_uid')) for x in finding_trigger_rows]!r}")
    finding_decision = os.environ.get("STAGE02_FINDING_CREATE_TRIGGER_DECISION", "").strip()
    if finding_decision != "SYSTEM_TRIGGER_FROM_EVALUATION_FINDING_DETECTION":
        die(f"ASSET01_FINDING_CREATE_EXPLICIT_SYSTEM_TRIGGER_DECISION_REQUIRED:{finding_decision!r}")
    remaining_uids = set()
    approved_rows = list(rows)
    approved_uids = {str(x.get("problem_uid") or "") for x in approved_rows}
"""
    new="""    blockers = semantic.get("blocking_authority_selection") or []
    rows = list(problem.get("problems") or [])
    if int(problem.get("open_problem_count") or 0) != len(rows):
        die("CURRENT_PROBLEM_REGISTER_OPEN_DENOMINATOR_DRIFT")
    approved_rows = list(rows)
    approved_uids = {str(x.get("problem_uid") or "") for x in approved_rows}
    remaining_uids = set()
"""
    if old not in s: raise RuntimeError('materializer authority block drift')
    s=s.replace(old,new,1)
    s=s.replace("""    candidate_review_count = sum(
        int((boundaries.get(key) or {}).get("problem_count") or 0)
        for key in (
            "failure_error_binding", "payload_input_contract", "audit_event_binding",
            "transition_required_fields", "post_action_validation_remaining", "finding_create_trigger", "stage02_planning_completeness",
        )
    )
    if candidate_review_count != len(approved_uids):
        die(f"APPROVED_DESIGN_CANDIDATE_DENOMINATOR_DRIFT:{candidate_review_count}:{len(approved_uids)}")
""","")
    oldaudit="""    for proposal in audit_rows:
        aid = str(proposal.get("action_uid") or "")
        event_uid = str(proposal.get("audit_event_uid") or "")
"""
    newaudit="""    for proposal in audit_rows:
        _require_record_schema(proposal, {"action_uid": str, "audit_event_uid": str}, "STAGE02_AUDIT_EVENT_BINDING")
        aid = str(proposal.get("action_uid") or "")
        event_uid = str(proposal.get("audit_event_uid") or "")
"""
    if oldaudit not in s: raise RuntimeError('audit proposal block drift')
    s=s.replace(oldaudit,newaudit,1)
    oldfind="""    finding_boundary = boundaries.get("finding_create_trigger") or {}
    if finding_boundary.get("status") != "AUTHORITY_SELECTION_REQUIRED" or str(finding_boundary.get("action_uid") or "") != authority_target:
        die("FINDING_CREATE_AUTHORITY_GAP_BOUNDARY_DRIFT")
    alternatives = finding_boundary.get("alternatives") or []
    selected = [x for x in alternatives if isinstance(x, dict) and x.get("behavior") == finding_decision]
    if len(selected) != 1 or selected[0].get("new_visual_control") is not False:
        die("FINDING_CREATE_SYSTEM_TRIGGER_SELECTION_NOT_EXACT")
    finding_action = actions.get(authority_target)
    if not finding_action:
        die("FINDING_CREATE_ACTION_MISSING")
    for field in ("trigger_event_uid", "trigger_uid", "system_trigger", "trigger_kind"):
        if finding_action.get(field):
            die(f"FINDING_CREATE_TRIGGER_CONFLICT:{field}")
    prior_invocation = finding_action.get("invocation")
    if prior_invocation not in (None, "", finding_decision):
        die(f"FINDING_CREATE_INVOCATION_CONFLICT:{prior_invocation!r}")
    finding_action["invocation"] = finding_decision
    finding_action["trigger_authority"] = {
        "source": "EXPLICIT_USER_DIRECTIVE",
        "authorization_uid": str(state.get("current_primary_task_authorization_uid") or ""),
        "bug_ref": "FIND-20260919-015",
        "new_visual_control": False,
    }
"""
    newfind="""    trigger_rows = [x for x in rows if x.get("category") in {"SYSTEM_TRIGGER_BINDING_MISSING","ACTION_WITHOUT_CONTROL_OR_TRIGGER"}]
    system_trigger_materializations=[]
    for row in trigger_rows:
        aid=str(row.get("target_uid") or row.get("uid") or "")
        action=actions.get(aid)
        contract=_deterministic_system_trigger(aid, action or {}, raw_reg) if action else None
        if contract is None:
            remaining_uids.add(str(row.get("problem_uid") or ""))
            continue
        if action.get("system_trigger") not in (None, {}, contract):
            die(f"SYSTEM_TRIGGER_CONFLICT:{aid}")
        action["system_trigger"]=contract
        action["trigger_authority"]={"source":"CURRENT_AUTHORITY_DETERMINISTIC_RESOLUTION","new_visual_control":False}
        system_trigger_materializations.append({"action_uid":aid,"system_trigger":contract})
    approved_uids -= remaining_uids
"""
    if oldfind not in s: raise RuntimeError('finding trigger block drift')
    s=s.replace(oldfind,newfind,1)
    s=s.replace('"materialization_scope": "APPROVED_COHERENT_CANDIDATE_PLUS_EXPLICIT_SYSTEM_TRIGGER_SELECTION",','"materialization_scope": "APPROVED_COHERENT_CANDIDATE_PLUS_DETERMINISTIC_SYSTEM_TRIGGER_RESOLUTION",')
    s=s.replace('"approval_kind": "EXPLICIT_USER_APPROVAL_COHERENT_CANDIDATE_PLUS_EXPLICIT_SYSTEM_TRIGGER_SELECTION",','"approval_kind": "EXPLICIT_USER_APPROVAL_COHERENT_CANDIDATE_PLUS_GOVERNED_AUTO_REMEDIATION",')
    s=s.replace('"decision": "APPROVE_COHERENT_CANDIDATE_PLUS_SYSTEM_TRIGGER_SELECTION",','"decision": "APPROVE_COHERENT_CANDIDATE_WITH_GOVERNED_AUTO_REMEDIATION",')
    # Remove product-specific authority_selection block from review evidence.
    s=re.sub(r'\n        "authority_selection": \{\n            "target_uid": authority_target,\n            "decision": finding_decision,\n            "new_visual_control": False,\n            "bug_ref": "FIND-20260919-015",\n        \},','\n        "system_trigger_materializations": system_trigger_materializations,',s,count=1)
    s=s.replace('"excluded_authority_selection_target_uids": [],','"excluded_authority_selection_target_uids": sorted({str(x.get("target_uid") or x.get("uid") or "") for x in rows if str(x.get("problem_uid") or "") in remaining_uids}),')
    s=s.replace('"remaining_authority_gap_target_uids": [],','"remaining_authority_gap_target_uids": sorted({str(x.get("target_uid") or x.get("uid") or "") for x in rows if str(x.get("problem_uid") or "") in remaining_uids}),')
    # Remove all executable legacy fallback after Current dynamic mode.
    legacy=s.index('if "--approved-design-current" in sys.argv:')
    s=s[:legacy]+"""if __name__ == "__main__":
    if "--self-test-shared-contract-hardening" in sys.argv:
        _self_test_shared_contract_hardening()
        raise SystemExit(0)
    if "--approved-design-current" in sys.argv:
        materialize_current_approved_design_contract()
        raise SystemExit(0)
    die("CURRENT_DYNAMIC_MATERIALIZATION_MODE_REQUIRED")
"""
    # remove unused os import after environment override removal.
    s=s.replace('import os\n','')
    p.write_text(s,encoding='utf-8')

def mutate_workflow():
    p=ROOT/'.github/workflows/stage02-actual-test.yml'
    s=p.read_text(encoding='utf-8')
    required=[
      'Regression test control-vs-system-trigger semantic resolution',
      'python governance/ci/run_current_stage2_actual_test.py --self-test-shared-contract-hardening',
      'Regression test producer-consumer schema identity in materializer',
      'python governance/ci/materialize_current_stage2_closure_artifacts.py --self-test-shared-contract-hardening',
      'git commit -m "test(stage02): persist current bounded revalidation result"',
    ]
    missing=[x for x in required if x not in s]
    if missing:
        raise RuntimeError(f'pre-applied stage02 workflow contract missing:{missing}')
    if 'default: CORE-01' in s or '- CORE-01' in s:
        raise RuntimeError('pre-applied stage02 workflow still has fixed CORE-01 dispatch scope')
def mutate_semantic_baseline():
    p=SOURCE/'10_REGISTRY/SEMANTIC_AUTHORITY_BASELINE.yaml'
    d=load(p)
    d['governance_revision']=NEW_SOURCE_REV
    for rec in d.get('mandatory_regression_assets') or []:
        if rec.get('path')=='09_TESTS/governance/test_v2_1_13_stage_execution_invariants.py':
            if (rec.get('expected_total'), rec.get('expected_passed')) != (26, 26):
                raise RuntimeError('mandatory stage invariant denominator drift')
    d['content_hash']=base.hobj(d)
    dump(p,d)
    return d['content_hash']

def update_projection(semantic_hash,bundle_hash,zip_hash,checksums_hash):
    p=ROOT/'governance/specifications/current/SPECIFICATION_MANIFEST.yaml'; d=load(p)
    old_sl=copy.deepcopy(d.get('source_lineage') or {})
    d['artifact_uid']=NEW_UID; d['display_version']=NEW_DISPLAY
    sl=d.setdefault('source_lineage',{})
    sl.update({'verified_package_filename':NEW_PACKAGE,'verified_package_sha256':zip_hash,'predecessor_governance_uid':OLD_UID,'promotion_authorization_uid':AUTH_UID,'source_bytes_changed_by_this_successor':True,'source_identity_reused_only_because_source_bytes_are_unchanged':False,'deterministic_source_bundle_sha256':bundle_hash,'checksum_manifest_sha256':checksums_hash,'semantic_authority_content_hash':semantic_hash,'verified_source_revision':NEW_SOURCE_REV,'predecessor_verified_package_filename':old_sl.get('verified_package_filename'),'predecessor_verified_package_sha256':old_sl.get('verified_package_sha256'),'post_promotion_projector_sync_authorization_uid':AUTH_UID})
    dump(p,d)

    p=ROOT/'governance/specifications/REGISTRY.yaml'; d=load(p)
    d['active_specification']['governance_uid']=NEW_UID; d['active_specification']['display_version']=NEW_DISPLAY
    aliases=d['active_specification'].setdefault('aliases',[])
    if 'asset-stage01-stage02-shared-contract-hardening' not in aliases: aliases.append('asset-stage01-stage02-shared-contract-hardening')
    d['immediate_predecessor']={'governance_uid':OLD_UID,'display_version':OLD_DISPLAY,'version_role':'SUPERSEDED_CURRENT_GOVERNANCE_HISTORY','status':'SUPERSEDED_HISTORY_ONLY_AFTER_ASSET_STAGE01_STAGE02_SHARED_CONTRACT_HARDENING'}
    dump(p,d)

    p=ROOT/'GOVERNANCE_CURRENT.yaml'; d=load(p)
    d['active_governance_uid']=NEW_UID; d['display_version']=NEW_DISPLAY
    d.setdefault('source_identity',{}).update({'verified_package_sha256':zip_hash,'deterministic_source_bundle_sha256':bundle_hash,'checksum_manifest_sha256':checksums_hash,'semantic_authority_content_hash':semantic_hash,'verified_source_revision':NEW_SOURCE_REV,'source_bytes_changed_by_current_successor':True})
    dump(p,d)

    p=ROOT/'governance/test/ACTIVE_STATE.yaml'; d=load(p)
    if (d.get('active_work_unit') or {}).get('work_unit_uid')!=WORK_UNIT: raise RuntimeError('active work unit drift')
    d['specification_uid']=NEW_UID
    d['status']='ACTIVE_ASSET_STAGE01_STAGE02_SHARED_CONTRACT_HARDENING_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED'
    d['next_action']='RUN_V2_2_13_EXACT_HEAD_VALIDATION_THEN_CLEAN_ASSET01_STAGE01_STAGE02_FRESH_REPLAY'
    d['current_primary_task_layer']='GOVERNANCE_MAINTENANCE'
    d['current_primary_task_authorization_uid']=AUTH_UID
    d['current_primary_task_product_stage_credit']=0
    work=d['active_work_unit']; work['current_status']='PROMOTION_MATERIALIZED_EXACT_HEAD_REVALIDATION_REQUIRED'; d['active_work_unit']=work
    gt=d.setdefault('governance_revision_transition',{})
    gt.update({'predecessor_governance_uid':OLD_UID,'current_governance_uid':NEW_UID,'fresh_revalidation_required':True,'fresh_revalidation_scope':'CONTROL_VS_SYSTEM_TRIGGER_PRODUCER_CONSUMER_SCHEMA_PRODUCT_NEUTRAL_STAGE02_CONSUMERS','mother_machine_revalidation_complete':False,'mother_machine_revalidation_run_id':None,'mother_machine_revalidation_head':None,'mother_machine_revalidation_result':'REVALIDATION_REQUIRED','selected_execution_profile_preserved':True,'selected_execution_profile_run_id':None,'website_construction_remains_blocked':True,'deployment_remains_blocked':True})
    d['resume_control']={'current_resume_point':'ASSET_STAGE01_STAGE02_SHARED_CONTRACT_SUCCESSOR_PROMOTED_EXACT_HEAD_REVALIDATION_REQUIRED','current_work_unit_uid':WORK_UNIT,'current_owner':'.github/governance-source/active/source/12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md','historical_stage2_results_are_current_state':False,'stage2_execution_requires_fresh_entry_resolution':True,'exact_next_action':'RUN_V2_2_13_EXACT_HEAD_VALIDATION_THEN_CLEAN_ASSET01_STAGE01_STAGE02_FRESH_REPLAY','parent_work_unit_uid':'WU-GOV-BASIC-DESIGN-ATOMIC-MATERIALIZATION-001','parent_primary_task_layer':'GOVERNANCE_MAINTENANCE','preserved_product_work_unit_uid':'WU-STAGE02-ASSET01-8133839F-REPLAY','preserved_product_resume_point':'ASSET01_STAGE2_EXACT_CLOSURES_REVALIDATED_REVIEW_ONLY_PRODUCT_AUTHORITY_REQUIRED','preserved_product_next_action':'CLEAN_ASSET01_STAGE01_STAGE02_GENERATED_OUTPUT_AND_FRESH_REPLAY_AFTER_SHARED_GOVERNANCE_SUCCESSOR'}
    dump(p,d)

    p=ROOT/'governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml'; d=load(p)
    d['governance_uid']=NEW_UID; d['fresh_revalidation_required']=True; d['stage_exit_credit_allowed']=False
    x=copy.deepcopy(d); x.pop('content_hash',None)
    d['content_hash']=hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    dump(p,d)

def source_revision_aux():
    for rel in ['10_REGISTRY/REVIEW_PROGRESS_LEDGER.yaml','11_EVIDENCE/audit/GOVERNANCE_CANDIDATE_STATE.yaml']:
        p=SOURCE/rel
        if not p.exists(): continue
        d=load(p)
        if 'governance_revision' in d: d['governance_revision']=NEW_SOURCE_REV
        if rel.endswith('GOVERNANCE_CANDIDATE_STATE.yaml'):
            d['candidate']='v2.2.13_ASSET_STAGE01_STAGE02_SHARED_CONTRACT_HARDENING_CANDIDATE'
            d['status']='CANDIDATE_UNDER_FRESH_SUCCESSOR_REVALIDATION'
            fr=d.setdefault('fresh_revalidation',{}); fr.update({'required':True,'current_source_revision':NEW_SOURCE_REV,'current_closure_credit':False,'predecessor_evidence_current_closure_credit':False,'historical_evidence_may_close_successor':False,'persisted_head_full_line_required':True})
        dump(p,d)
    p=SOURCE/'README.md'
    marker='## v2.2.13 ASSET Stage-01/02 shared contract hardening'
    if marker not in p.read_text(encoding='utf-8'):
        p.write_text(p.read_text(encoding='utf-8').rstrip()+f"\n\n{marker}\nThis successor hardens product-neutral Stage-02 control-vs-system-trigger resolution, exact producer/consumer field-schema identity, no-history product-value fallback, legal task-layer transition order, and reusable Stage-02 consumer neutrality. It does not change ASSET product Authority.\n",encoding='utf-8')
    p=SOURCE/'VERSIONING_RULE.md'
    marker='## v2.2.13 shared Stage-01/02 contract hardening rule'
    if marker not in p.read_text(encoding='utf-8'):
        p.write_text(p.read_text(encoding='utf-8').rstrip()+f"\n\n{marker}\n- v2.2.12 remains immutable predecessor history.\n- Missing explicit trigger syntax is not automatically a product Authority choice when structured Current evidence uniquely proves a system-owned operation.\n- Producer/consumer field-schema drift fails before materialization; alias fallback cannot hide the defect.\n- Historical product values cannot fill Current missing contracts.\n- Reusable Stage consumers remain product-neutral and task-layer order is not bypassable.\n",encoding='utf-8')

def cleanup_promotion_scaffold():
    # Workflow/promoter cleanup is intentionally deferred to a connector-authored
    # post-promotion commit because the Actions token does not have workflows permission.
    # Exact-head validation is run only after that cleanup commit.
    return
def static_current_consumer_assertions():
    mat=(ROOT/'governance/ci/materialize_current_stage2_closure_artifacts.py').read_text(encoding='utf-8')
    for forbidden in ['fresh_run_003','"CORE-01"','"ASSET-01"','STAGE02_PRODUCT_REENTRY_AUTHORIZATION_UID','deferred_foreground']:
        if forbidden in mat: raise RuntimeError('active materializer still product/history coupled:'+forbidden)
    wf=(ROOT/'.github/workflows/stage02-actual-test.yml').read_text(encoding='utf-8')
    if 'default: CORE-01' in wf or '- CORE-01' in wf: raise RuntimeError('stage02 workflow still has fixed CORE-01 dispatch scope')
    scan=(ROOT/'governance/ci/run_current_stage2_actual_test.py').read_text(encoding='utf-8')
    if 'SYSTEM_TRIGGER_BINDING_MISSING' not in scan or 'control_vs_system_trigger_resolution' not in scan: raise RuntimeError('semantic trigger resolver missing')
    if 'STAGE02_PRODUCT_REENTRY_AUTHORIZATION_UID' in mat: raise RuntimeError('task layer environment override remains')

def apply():
    current=load(ROOT/'GOVERNANCE_CURRENT.yaml')
    if current.get('active_governance_uid') not in (OLD_UID,NEW_UID): raise RuntimeError('unexpected Current governance UID')
    auth=ROOT/f'governance/test/spec_change_authorizations/{AUTH_UID}.yaml'
    if not auth.is_file() or load(auth).get('status')!='APPROVED_FOR_EXACT_SCOPE': raise RuntimeError('preexisting authorization missing')
    mutate_mother()
    mutate_invariants()
    mutate_current_components()
    mutate_source_validator_and_regression()
    mutate_scanner()
    mutate_materializer()
    mutate_workflow()
    source_revision_aux()
    semantic_hash=mutate_semantic_baseline()
    checks,bundle,zips=base.refresh_source(semantic_hash)
    update_projection(semantic_hash,bundle,zips,checks)
    cleanup_promotion_scaffold()
    static_current_consumer_assertions()
    return {'semantic_hash':semantic_hash,'checksums_hash':checks,'bundle_hash':bundle,'zip_hash':zips}

def main():
    result=apply()
    env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPYCACHEPREFIX']='/tmp/acpos-stage12-shared-pycache'
    for cmd in [
      [sys.executable,str(ROOT/'governance/ci/run_current_stage2_actual_test.py'),'--self-test-shared-contract-hardening'],
      [sys.executable,str(ROOT/'governance/ci/materialize_current_stage2_closure_artifacts.py'),'--self-test-shared-contract-hardening'],
      [sys.executable,str(SOURCE/'09_TESTS/governance/validate_stage_execution_invariants.py')],
      [sys.executable,str(SOURCE/'09_TESTS/governance/test_v2_1_13_stage_execution_invariants.py')],
    ]:
        cp=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env)
        print('$',' '.join(map(str,cmd))); print(cp.stdout[-8000:])
        if cp.returncode:
            print(cp.stderr[-8000:],file=sys.stderr); raise SystemExit(cp.returncode)
    base.validate_all()
    subprocess.run(['git','fetch','origin','rebuild-v2.1.1'],cwd=ROOT,check=True)
    if subprocess.check_output(['git','rev-parse','origin/rebuild-v2.1.1'],cwd=ROOT,text=True).strip()!=os.environ.get('GITHUB_SHA',''):
        raise RuntimeError('branch moved during governance promotion')
    subprocess.run(['git','config','user.name','github-actions[bot]'],cwd=ROOT,check=True)
    subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],cwd=ROOT,check=True)
    subprocess.run(['git','add','-A'],cwd=ROOT,check=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0: raise RuntimeError('no promotion delta')
    msg='feat(governance): promote ASSET Stage-01/02 shared contract hardening\n\nSpec-Change-Authorization: '+AUTH_UID+'\nSpec-Change-Scope: CONTROL_VS_SYSTEM_TRIGGER_SCHEMA_IDENTITY_PRODUCT_NEUTRAL_STAGE02'
    subprocess.run(['git','commit','-m',msg],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(ROOT/'governance/ci/specification_mutation_guard.py')],cwd=ROOT,check=True,env=env)
    subprocess.run(['git','push','origin','HEAD:rebuild-v2.1.1'],cwd=ROOT,check=True)
    print(json.dumps({'status':'PROMOTED','governance_uid':NEW_UID,'display_version':NEW_DISPLAY,**result},indent=2))
if __name__=='__main__':
    main()
