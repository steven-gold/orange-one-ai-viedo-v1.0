from pathlib import Path
p=Path('docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml')
s=p.read_text()
old='''  current_task: VIS-10_ADMIN_SYS-01_VISUAL_POSITIONING
  current_task_state: AUTHORITY_CLOSED_READY_FOR_VISUAL_IMPLEMENTATION
  current_task_blockers: []
  last_completed_task: VIS-09_FRONT_INFO-01_VISUAL_POSITIONING
'''
new='''  current_task: VIS-11_ADMIN_IAM-01_VISUAL_POSITIONING
  current_task_state: NOT_STARTED
  current_task_blockers: []
  last_completed_task: VIS-10_ADMIN_SYS-01_VISUAL_POSITIONING
'''
if old not in s: raise SystemExit('current state anchor missing')
s=s.replace(old,new,1)
old2='''  - id: VIS-10
    group: ADMIN
    page_uid: admin:SYS-01
    name: 系統維護
    status: NOT_STARTED
    authority_closure:
      route: /admin/system
      legacy_25_control_count: REMOVED_AS_MIGRATION_RESIDUE
      current_registered_controls: 8
      current_sections: 8
      rule: Current-only SYS-01 controls are defined from current functional contracts; no R9/master count padding.
      status: READY_FOR_VISUAL_IMPLEMENTATION
'''
new2='''  - id: VIS-10
    group: ADMIN
    page_uid: admin:SYS-01
    name: 系統維護
    status: COMPLETE
    scope: Current-only SYS-01 visual implementation at /admin/system with one shared Global Shell, frontend Account -> Admin entry, nine-item Admin navigation, exact eight canonical sections and eight registered controls; visual/empty/disabled presentation only, no business runtime mutation.
    authority_closure:
      route: /admin/system
      legacy_25_control_count: REMOVED_AS_MIGRATION_RESIDUE
      current_registered_controls: 8
      current_sections: 8
      rule: Current-only SYS-01 controls are defined from current functional contracts; no R9/master count padding.
      status: CLOSED
    evidence:
      implementation_commit: 3bc7edcb6ee209e3352d6170f53d8ff4d18497be
      final_validation_run_id: 33284782877
      final_evidence_artifact_id: 9724069583
      artifact_sha256: 66778fc3fe64bce81b36f57064b0adcecd87bd82957d328b5bef84831a210889
      evidence_directory: docs/construction/evidence/VIS-10
      validation_record: docs/construction/evidence/VIS-10/vis10-final-regression.json
      typecheck: PASS
      next_build: PASS
      production_server: PASS
      chromium_render_and_geometry: PASS
      all_front_routes_shared_shell_regression: PASS
      admin_navigation_regression: PASS
      locale_switch_runtime: PASS
      business_requests_during_validation: 0
      manual_visual_inspection: PASS
      manual_visual_inspection_basis: Final collapsed, expanded overlay, lower workspace and frontend Account/Admin-entry screenshots were directly inspected after correcting Council hidden state and Global Shell active navigation state; no unintended clipping, overlap or workspace reflow remained.
      verified_contract:
        route: /admin/system
        admin_l1_count: 9
        active_admin_nav: ADMIN-NAV-01
        front_l1_count_preserved: 9
        sections: 8
        controls: 8
        council_controls_hidden_in_single_ai: true
        enabled_business_controls_in_visual_phase: 0
        production_deploy_control_rendered: false
        provider_model_picker_rendered: false
        workspace_origin_x: 78px
        sidebar_collapsed_width: 64px
        sidebar_expanded_width: 221px
        workspace_reflow_on_expand: false
        desktop_1440_horizontal_overflow: false
        below_1280_horizontal_scroll: true
        account_front_to_admin_entry: PASS
        account_admin_to_front_return: PASS
        global_active_nav_state: PASS
'''
if old2 not in s: raise SystemExit('VIS10 anchor missing')
s=s.replace(old2,new2,1)
s=s.replace('''  visual_steps_complete: 10
''','''  visual_steps_complete: 11
''',1)
oldnote='''  truthful_progress_note: VIS-00 through VIS-09 visual positioning are implemented and verified. On 2026-08-30 the user approved promotion of the existing workspace:INFO-01 to front NAV-09 最新資訊; VIS-09 revalidated all nine existing front routes against the nine-item shared shell while preserving NAV-01 through NAV-08 order and workspace geometry. Historical VIS-00 through VIS-08 evidence retains the nav count that existed when each run was captured and is not rewritten. VIS-10 SYS-01 is current. Page business/runtime logic remains blocked until VIS-00 through VIS-18 are complete.
'''
newnote='''  truthful_progress_note: VIS-00 through VIS-10 visual positioning are implemented and verified. VIS-09 promoted the existing workspace:INFO-01 to front NAV-09 最新資訊. VIS-10 established the shared Admin surface entry under Account, implemented admin:SYS-01 at /admin/system, and revalidated all nine front routes plus SYS-01 after restoring the Global Shell active navigation state. Historical evidence is not rewritten. VIS-11 IAM-01 is next but has not started. Page business/runtime logic remains blocked until VIS-00 through VIS-18 are complete.
'''
if oldnote not in s: raise SystemExit('metrics note anchor missing')
s=s.replace(oldnote,newnote,1)
p.write_text(s)
