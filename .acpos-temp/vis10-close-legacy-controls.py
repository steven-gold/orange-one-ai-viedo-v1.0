from pathlib import Path
import yaml

sys_path = Path('authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml')
progress_path = Path('docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml')
s = sys_path.read_text()

# Remove migration-era preservation wording/count while keeping the current 8-section functional contract.
s = s.replace('current_page_contract_preserved:\n', 'current_page_function_contract:\n', 1)
s = s.replace('  existing_registered_control_count_before_this_design_extension: 25\n', '', 1)
s = s.replace('  existing_allowed_action_ids:\n', '  current_allowed_action_ids:\n', 1)
s = s.replace('  existing_page_permission: system.change.propose\n', '  current_page_permission: system.change.propose\n', 1)
s = s.replace('  existing_service_permissions:\n', '  current_service_permissions:\n', 1)
s = s.replace('  existing_service_operations:\n', '  current_service_operations:\n', 1)
s = s.replace('  existing_forbidden:\n', '  current_forbidden:\n', 1)
s = s.replace('  existing_ai_scope_boundary:\n', '  current_ai_scope_boundary:\n', 1)

registry = '''\ncurrent_control_registry:\n  authority_closure: 2026-08-30-USER-APPROVED-CURRENT-ONLY\n  legacy_25_control_count_policy: REMOVED_AS_MIGRATION_RESIDUE_NOT_A_CURRENT_COUNT_CONSTRAINT\n  rule: Register only controls required by the Current SYS-01 functional contract. Do not reconstruct or pad to a legacy R9/master count. Read-only truth/ref/impact/audit projections are components, not business controls unless an explicit interaction is required.\n  count: 8\n  explicit_mode_controls:\n  - control_uid: SYS-01-BTN-SINGLE-AI\n    source: multi_ai_ui_control_correction.controls\n  - control_uid: SYS-01-BTN-MULTI-AI\n    source: multi_ai_ui_control_correction.controls\n  - control_uid: SYS-01-BTN-COUNCIL-DISCUSSION\n    source: multi_ai_ui_control_correction.controls\n  - control_uid: SYS-01-BTN-COUNCIL-PARALLEL\n    source: multi_ai_ui_control_correction.controls\n  current_action_controls:\n  - control_uid: SYS-01-BTN-CANDIDATE-CREATE\n    type: BUTTON\n    label_zh: 建立變更候選\n    section_id: SEC-ADMIN-SYS-01-ACTION-DOCK\n    component_uid: SYS-01-CMP-ACTION-DOCK\n    visual_uid: SYS-01-VIS-ACTION-DOCK\n    action_uid: ACT-CANDIDATE-CREATE\n    permission_uid: system.change.propose\n    service_operation: createCandidate\n    enabled_in_visual_phase: false\n  - control_uid: SYS-01-BTN-CR-CREATE\n    type: BUTTON\n    label_zh: 建立變更請求\n    section_id: SEC-ADMIN-SYS-01-ACTION-DOCK\n    component_uid: SYS-01-CMP-ACTION-DOCK\n    visual_uid: SYS-01-VIS-ACTION-DOCK\n    action_uid: ACT-CR-CREATE\n    permission_uid: core.change.create\n    service_operation: createChangeRequest\n    enabled_in_visual_phase: false\n  - control_uid: SYS-01-BTN-NAV-OPEN\n    type: BUTTON\n    label_zh: 開啟引用項目\n    section_id: SEC-ADMIN-SYS-01-SOURCE-REFS\n    component_uid: SYS-01-CMP-SOURCE-REFS\n    visual_uid: SYS-01-VIS-SOURCE-REFS\n    action_uid: ACT-NAV-OPEN\n    permission_uid: ops.read\n    service_operation: null\n    enabled_in_visual_phase: false\n  - control_uid: SYS-01-BTN-SANDBOX-TEST\n    type: BUTTON\n    label_zh: Sandbox 測試\n    section_id: SEC-ADMIN-SYS-01-EXECUTION-PANEL\n    component_uid: SYS-01-CMP-EXECUTION-PANEL\n    visual_uid: SYS-01-VIS-EXECUTION-PANEL\n    action_uid: SYS-01-ACT-SANDBOX-TEST\n    permission_uid: system.test.execute\n    service_operation: runSandboxTest\n    enabled_in_visual_phase: false\n  excluded_controls:\n  - production_deploy_button: NOT_REGISTERED_BECAUSE_EXPLICIT_SYS06_RELEASE_ACTION_PERMISSION_GATE_BINDING_IS_UNRESOLVED\n  - provider_model_picker: FORBIDDEN\n  - direct_code_deploy: FORBIDDEN\n  - direct_production_change: FORBIDDEN\n  supplemental_actions:\n  - action_uid: SYS-01-ACT-SANDBOX-TEST\n    effect_type: SERVICE_OPERATION\n    service_operation: runSandboxTest\n    permission_uid: system.test.execute\n    visual_phase_execution: FORBIDDEN\n'''
anchor = '\nderived_validation:\n'
if anchor not in s:
    raise SystemExit('derived_validation anchor missing')
s = s.replace(anchor, registry + anchor, 1)

s = s.replace('    preserved_master_sections: 8\n    existing_master_controls_referenced: 25\n', '    current_page_sections: 8\n    current_registered_controls: 8\n    legacy_25_control_count_preservation: REMOVED\n', 1)
s = s.replace('    Preserves 8 current master sections: true\n', '    Preserves 8 current page sections: true\n    Legacy 25-control count is not a current count constraint: true\n    Current registry is exact and current-only: true\n', 1)

if 'existing_registered_control_count_before_this_design_extension' in s or 'existing_master_controls_referenced: 25' in s:
    raise SystemExit('legacy 25-control residue still present')
if s.count('control_uid: SYS-01-BTN-') < 8:
    raise SystemExit('expected current controls not materialized')

yaml.safe_load(s)
sys_path.write_text(s)

p = progress_path.read_text()
p = p.replace('  current_task_state: BLOCKED_BY_AUTHORITY_GAP\n  current_task_blockers:\n  - PRESERVED_25_CONTROL_REGISTRY_UID_SOURCE_MISSING\n', '  current_task_state: AUTHORITY_CLOSED_READY_FOR_VISUAL_IMPLEMENTATION\n  current_task_blockers: []\n', 1)
p = p.replace('    status: BLOCKED_BY_AUTHORITY_GAP\n', '    status: NOT_STARTED\n', 1)
# Remove old blocker_detail through resume_gate block only for VIS-10.
start = p.find('    blocker_detail:\n', p.find('  - id: VIS-10\n'))
end = p.find('  - id: VIS-11\n', start)
if start != -1 and end != -1:
    prefix = p[:start]
    tail = p[end:]
    closure = '''    authority_closure:\n      route: /admin/system\n      legacy_25_control_count: REMOVED_AS_MIGRATION_RESIDUE\n      current_registered_controls: 8\n      current_sections: 8\n      rule: Current-only SYS-01 controls are defined from current functional contracts; no R9/master count padding.\n      status: READY_FOR_VISUAL_IMPLEMENTATION\n'''
    p = prefix + closure + tail

yaml.safe_load(p)
progress_path.write_text(p)
print('SYS-01 authority closure PASS')
