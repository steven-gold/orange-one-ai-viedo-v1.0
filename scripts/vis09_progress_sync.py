from pathlib import Path
p=Path('docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml')
s=p.read_text()
s=s.replace('- Visual construction order is Home -> Front Workspace -> Supporting Workspace -> Admin.','- Visual construction order is Home -> Front Workspace -> Admin.',1)
old='''  current_task: VIS-05_FRONT_EDIT-01_VISUAL_POSITIONING
  last_completed_task: VIS-04_FRONT_VIDEO-01_VISUAL_POSITIONING
'''
new='''  current_task: VIS-10_ADMIN_SYS-01_VISUAL_POSITIONING
  last_completed_task: VIS-09_FRONT_INFO-01_VISUAL_POSITIONING
  current_front_l1_count: 9
  navigation_revision: 2026-08-30-USER-APPROVED-INFO-NAV09
  navigation_history_note: VIS-00 through VIS-08 retain their historical render evidence. VIS-09 regression supersedes the current Global Shell navigation count from 8 to 9 without rewriting prior evidence.
'''
if old not in s: raise SystemExit('current state anchor missing')
s=s.replace(old,new,1)
old='''  - id: VIS-05
    group: FRONT
    page_uid: EDIT-01
    name: 剪輯配音
    status: NOT_STARTED
  - id: VIS-06
    group: FRONT
    page_uid: QA-01
    name: QA
    status: NOT_STARTED
  - id: VIS-07
    group: FRONT
    page_uid: admin:DB-01
    name: 資料庫
    status: NOT_STARTED
    note: Page UID is ADMIN but canonical Front L1 navigation exposes it as the Database workspace entry.
  - id: VIS-08
    group: FRONT
    page_uid: workspace:STR-01
    name: 戰略中心
    status: NOT_STARTED
  - id: VIS-09
    group: SUPPORTING_WORKSPACE
    page_uid: workspace:INFO-01
    name: 最新資訊工作區
    status: NOT_STARTED
'''
new='''  - id: VIS-05
    group: FRONT
    page_uid: EDIT-01
    name: 剪輯配音
    status: COMPLETE
    evidence:
      final_validation_run_id: 33273554069
      evidence_directory: docs/construction/evidence/VIS-05
      validation_record: docs/construction/evidence/VIS-05/vis05-validation.json
      typecheck: PASS
      next_build: PASS
      production_server: PASS
      chromium_render_and_geometry: PASS
      manual_visual_inspection: PASS
  - id: VIS-06
    group: FRONT
    page_uid: QA-01
    name: QA
    status: COMPLETE
    evidence:
      final_validation_run_id: 33275590962
      evidence_directory: docs/construction/evidence/VIS-06
      typecheck: PASS
      next_build: PASS
      production_server: PASS
      chromium_render_and_geometry: PASS
      manual_visual_inspection: PASS
  - id: VIS-07
    group: FRONT
    page_uid: admin:DB-01
    name: 資料庫
    status: COMPLETE
    note: Page UID is ADMIN but canonical Front L1 navigation exposes it as the Database workspace entry.
    evidence:
      final_validation_run_id: 33276294897
      evidence_directory: docs/construction/evidence/VIS-07
      typecheck: PASS
      next_build: PASS
      production_server: PASS
      chromium_render_and_geometry: PASS
      manual_visual_inspection: PASS
  - id: VIS-08
    group: FRONT
    page_uid: workspace:STR-01
    name: 戰略中心
    status: COMPLETE
    evidence:
      final_validation_run_id: 33278244242
      evidence_directory: docs/construction/evidence/VIS-08
      typecheck: PASS
      next_build: PASS
      production_server: PASS
      chromium_render_and_geometry: PASS
      manual_visual_inspection: PASS
  - id: VIS-09
    group: FRONT
    page_uid: workspace:INFO-01
    name: 最新資訊工作區
    status: COMPLETE
    scope: User-approved promotion of the existing INFO-01 authority to NAV-09 plus exact 12-section / 12-visual / 20-component / 66-control visual positioning; no business mutation/runtime execution.
    evidence:
      final_validation_run_id: 33280678519
      manual_evidence_export_run_id: 33280753917
      manual_evidence_artifact_id: 9722905545
      artifact_sha256: 2d9895108b97fe7f8fdef1f118b3163d5d81b90340db837aba76eb9595237a6e
      evidence_directory: docs/construction/evidence/VIS-09
      validation_record: docs/construction/evidence/VIS-09/vis09-validation.json
      typecheck: PASS
      next_build: PASS
      production_server: PASS
      chromium_render_and_geometry: PASS
      all_front_routes_nav09_regression: PASS
      locale_switch_runtime: PASS
      business_requests_during_validation: 0
      manual_visual_inspection: PASS
      verified_contract:
        route: /info
        front_l1_count: 9
        active_nav: NAV-09
        sections: 12
        visuals: 12
        components: 20
        controls: 66
        workspace_origin_x: 78px
        sidebar_collapsed_width: 64px
        sidebar_expanded_width: 221px
        workspace_reflow_on_expand: false
        desktop_1600_horizontal_overflow: false
        desktop_1440_horizontal_overflow: false
        below_1280_horizontal_scroll: true
        fact_inference_visibly_separated: true
        unregistered_start_cancel_research: false
'''
if old not in s: raise SystemExit('VIS05-09 block anchor missing')
s=s.replace(old,new,1)
s=s.replace('  visual_steps_complete: 5\n','  visual_steps_complete: 10\n',1)
old_note='  truthful_progress_note: VIS-00 Global Shell, VIS-01 WB-01, VIS-02 CORE-01, VIS-03 ASSET-01, and VIS-04 VIDEO-01 visual positioning are implemented and verified. VIS-04 final exact-tree evidence includes TypeScript/Next build, production-server Chromium validation, exact 10-section/17-component/85-control registry closure, 71 empty-state visible controls plus 14 condition-gated controls, one measured 16:9 Current Viewer with no Candidate B, no premature correction controls, 260/720/280 minimum three-column geometry, read-only Provider Runtime, zero business requests, zh-TW/zh-CN/en switching, 1280px minimum-width behavior, sidebar no-reflow verification, persisted render evidence, and byte-identical final render verification against the manually inspected set. VIS-05 EDIT-01 is current. Page business/runtime logic remains blocked until VIS-00 through VIS-18 are complete.'
new_note='  truthful_progress_note: VIS-00 through VIS-09 visual positioning are implemented and verified. On 2026-08-30 the user approved promotion of the existing workspace:INFO-01 to front NAV-09 最新資訊; VIS-09 revalidated all nine existing front routes against the nine-item shared shell while preserving NAV-01 through NAV-08 order and workspace geometry. Historical VIS-00 through VIS-08 evidence retains the nav count that existed when each run was captured and is not rewritten. VIS-10 SYS-01 is current. Page business/runtime logic remains blocked until VIS-00 through VIS-18 are complete.'
if old_note not in s: raise SystemExit('truth note anchor missing')
s=s.replace(old_note,new_note,1)
p.write_text(s)
print('progress sync ready')
