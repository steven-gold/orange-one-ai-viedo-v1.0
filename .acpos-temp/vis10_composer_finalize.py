from pathlib import Path
import os
p = Path('docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml')
s = p.read_text()
old = '      current_registered_controls: 8\n'
if s.count(old) != 1:
    raise RuntimeError(f'expected one VIS-10 control count, got {s.count(old)}')
s = s.replace(old, '      current_registered_controls: 12\n', 1)
marker = '      global_active_nav_state: PASS\n'
if s.count(marker) != 1:
    raise RuntimeError(f'expected one VIS-10 marker, got {s.count(marker)}')
run_id = os.environ.get('GITHUB_RUN_ID', 'UNKNOWN')
insert = f'''      global_active_nav_state: PASS
      conversation_composer_remediation:
        user_decision_ref: 2026-08-30-USER-APPROVED-SYS01-CONVERSATION-COMPOSER
        validation_run_id: {run_id}
        controls_added: 4
        current_registered_controls: 12
        message_input_resizable: true
        conversation_panel_enlarged: true
        visual_phase_message_typing: LOCAL_DRAFT_ONLY
        attach_send_stop_business_execution: BLOCKED_UNTIL_LOGIC_PHASE_EXACT_CONVERSATION_CORE_BINDING
        shared_shell_regression: PASS
        business_requests_during_validation: 0
        manual_visual_inspection: PENDING_ARTIFACT_REVIEW_BEFORE_MERGE
'''
s = s.replace(marker, insert, 1)
p.write_text(s)
