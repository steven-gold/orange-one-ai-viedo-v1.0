from pathlib import Path
import os
p = Path('docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml')
s = p.read_text()

def replace_once(old: str, new: str, label: str):
    global s
    count=s.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected 1 match got {count}')
    s=s.replace(old,new,1)

replace_once('exact eight canonical sections and eight registered controls; visual/empty/disabled presentation only, no business runtime mutation.', 'exact eight canonical sections and twelve registered controls including the user-approved conversation composer; visual/empty/disabled presentation only, no business runtime mutation.', 'scope count')
replace_once('      current_registered_controls: 8\n', '      current_registered_controls: 12\n', 'authority closure count')
replace_once('        controls: 8\n', '        controls: 12\n', 'verified control count')
marker='        global_active_nav_state: PASS\n'
if s.count(marker) != 1:
    raise RuntimeError(f'VIS-10 marker expected 1 got {s.count(marker)}')
run_id=os.environ.get('GITHUB_RUN_ID','UNKNOWN')
insert=f'''        global_active_nav_state: PASS
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
s=s.replace(marker,insert,1)
p.write_text(s)
