from pathlib import Path
import os

ROOT = Path('.')
AUTH = ROOT / 'authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml'
TSX = ROOT / 'src/components/pages/SystemVisual.tsx'
CSS = ROOT / 'src/components/pages/SystemVisual.module.css'
CAT = ROOT / 'src/i18n/systemCatalog.ts'
TRACKER = ROOT / 'docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly 1 match, got {count}')
    return text.replace(old, new, 1)

# ---------- Authority closure ----------
s = AUTH.read_text()
composer_contract = '''conversation_composer_contract:
  purpose: Close the missing user-input surface required by the existing ACPOS AI Conversation Core contract; this is not a new AI backend or parallel conversation system.
  user_decision_ref: 2026-08-30-USER-APPROVED-SYS01-CONVERSATION-COMPOSER
  section_id: SEC-ADMIN-SYS-01-CONVERSATION
  component_uid: SYS-01-CMP-CONVERSATION-COMPOSER
  visual_uid: SYS-01-VIS-CONVERSATION-COMPOSER
  placement: Bottom of Design Conversation panel after the conversation timeline/context strip; composer remains visually attached to the same conversation/thread/change context.
  sizing:
    conversation_panel_priority: DOMINANT
    conversation_body_min_height_px: 360
    composer_min_height_px: 96
    textarea_min_height_px: 82
    textarea_vertical_resize: ALLOWED
  controls:
  - control_uid: SYS-01-INP-MESSAGE
    type: TEXTAREA
    label_zh: 訊息輸入
    action_uid: SYS-01-ACT-MESSAGE-DRAFT
    gate_uid: SYS-01-GATE-CONVERSATION-COMPOSER
    permission_uid: system.ai.use
    enabled_in_visual_phase: true
    runtime_binding:
      binding_kind: LOCAL_DRAFT_STATE_ONLY_IN_VISUAL_PHASE
      api_required: false
    rule: Edit the draft bound to the current SYSTEM_CHANGE_ID/conversation/thread context; typing alone never sends or mutates business state.
  - control_uid: SYS-01-BTN-ATTACH
    type: COMPACT_BUTTON
    label_zh: 附件 / 引用
    action_uid: SYS-01-ACT-CONVERSATION-ATTACH
    gate_uid: SYS-01-GATE-CONVERSATION-COMPOSER
    permission_uid: system.ai.use
    enabled_in_visual_phase: false
    runtime_binding:
      binding_kind: REUSE_ACPOS_AI_CONVERSATION_CORE_ATTACHMENT
      exact_operation_uid: RESOLVE_FROM_CURRENT_CONVERSATION_CORE_DURING_LOGIC_PHASE
      api_required_in_visual_phase: false
    rule: Reuse current Conversation Core source/file/reference attachment capability; do not invent a second uploader, storage owner or endpoint.
  - control_uid: SYS-01-BTN-SEND
    type: PRIMARY_BUTTON
    label_zh: 送出
    action_uid: SYS-01-ACT-CONVERSATION-SEND
    gate_uid: SYS-01-GATE-CONVERSATION-SEND
    permission_uid: system.ai.use
    enabled_in_visual_phase: false
    runtime_binding:
      binding_kind: REUSE_ACPOS_AI_CONVERSATION_CORE_MESSAGE_SUBMIT
      exact_operation_uid: RESOLVE_FROM_CURRENT_CONVERSATION_CORE_DURING_LOGIC_PHASE
      api_required_in_visual_phase: false
    rule: Submit only through the shared Conversation Core under the same SYSTEM_CHANGE_ID/conversation/thread/context; no direct provider call.
  - control_uid: SYS-01-BTN-STOP
    type: SECONDARY_BUTTON
    label_zh: 停止
    action_uid: SYS-01-ACT-CONVERSATION-STOP
    gate_uid: SYS-01-GATE-CONVERSATION-STOP
    permission_uid: system.ai.use
    enabled_in_visual_phase: false
    runtime_binding:
      binding_kind: REUSE_ACPOS_AI_CONVERSATION_CORE_GENERATION_STOP
      exact_operation_uid: RESOLVE_FROM_CURRENT_CONVERSATION_CORE_DURING_LOGIC_PHASE
      api_required_in_visual_phase: false
    rule: Stop only the current generation; never delete/reset SYSTEM_CHANGE_ID, conversation, thread, Decision Ledger, draft or source refs.
  actions:
  - action_uid: SYS-01-ACT-MESSAGE-DRAFT
    effect_type: UI_DRAFT_STATE
    api_required: false
    state_effect: update conversation draft only
  - action_uid: SYS-01-ACT-CONVERSATION-ATTACH
    effect_type: SHARED_CONVERSATION_CORE_OPERATION
    visual_phase_execution: FORBIDDEN
  - action_uid: SYS-01-ACT-CONVERSATION-SEND
    effect_type: SHARED_CONVERSATION_CORE_OPERATION
    visual_phase_execution: FORBIDDEN
  - action_uid: SYS-01-ACT-CONVERSATION-STOP
    effect_type: SHARED_CONVERSATION_CORE_OPERATION
    visual_phase_execution: FORBIDDEN
  gates:
  - gate_uid: SYS-01-GATE-CONVERSATION-COMPOSER
    requires:
    - page:admin:SYS-01 VIEW
    - section:admin:SYS-01:conversation VIEW
    - system.ai.use
    failure_behavior: Preserve local draft and show actual context/permission state; do not fabricate runtime readiness.
  - gate_uid: SYS-01-GATE-CONVERSATION-SEND
    requires:
    - SYS-01-GATE-CONVERSATION-COMPOSER
    - system_context_resolved
    - active_conversation_context_resolved
    - non_empty_message
    - shared_conversation_core_submit_binding_resolved
    failure_behavior: Keep draft unsent and surface the exact blocker.
  - gate_uid: SYS-01-GATE-CONVERSATION-STOP
    requires:
    - SYS-01-GATE-CONVERSATION-COMPOSER
    - generation_in_progress
    - shared_conversation_core_stop_binding_resolved
    failure_behavior: Keep current valid state; never clear conversation context.
  invariants:
  - composer_must_not_create_parallel_conversation_backend
  - composer_send_must_not_call_provider_directly
  - composer_must_preserve_SYSTEM_CHANGE_ID_conversation_thread_branch_context
  - visual_phase_typing_is_local_draft_only
  - attachment_send_stop_business_execution_remains_blocked_until_logic_phase_exact_binding
'''
s = replace_once(s, 'requirement_convergence_contract:\n', composer_contract + 'requirement_convergence_contract:\n', 'insert composer contract')
s = replace_once(s, '- acceptance_uid: SYS-01-ACC-LIFE-01\n', '''- acceptance_uid: SYS-01-ACC-CONV-01
  item: Real Conversation Composer
  condition: Design Conversation includes a multi-line message input plus Attach / Send / Stop controls bound to the existing ACPOS AI Conversation Core; input can resize vertically and no direct provider/backend path is invented.
- acceptance_uid: SYS-01-ACC-LIFE-01
''', 'composer acceptance')
s = replace_once(s, '- Single AI / Multi AI must be interactive segmented controls in the Design Conversation header.\n', '- Single AI / Multi AI must be interactive segmented controls in the Design Conversation header.\n- Design Conversation must include a real resizable text composer with Attach / Send / Stop controls that reuse the existing ACPOS AI Conversation Core.\n', 'composer hard lock')
s = replace_once(s, '  count: 8\n  explicit_mode_controls:\n', '  count: 12\n  explicit_mode_controls:\n', 'registry count')
registry_insert = '''  conversation_composer_controls:
  - control_uid: SYS-01-INP-MESSAGE
    source: conversation_composer_contract.controls
  - control_uid: SYS-01-BTN-ATTACH
    source: conversation_composer_contract.controls
  - control_uid: SYS-01-BTN-SEND
    source: conversation_composer_contract.controls
  - control_uid: SYS-01-BTN-STOP
    source: conversation_composer_contract.controls
'''
s = replace_once(s, '  current_action_controls:\n', registry_insert + '  current_action_controls:\n', 'registry composer controls')
s = replace_once(s, '    current_registered_controls: 8\n', '    current_registered_controls: 12\n', 'derived control count')
s = replace_once(s, '    acceptance_items: 11\n', '    acceptance_items: 12\n', 'acceptance count')
s = replace_once(s, '    Current registry is exact and current-only: true\n', '    Current registry is exact and current-only: true\n    Conversation composer has exact 4-control current registry: true\n', 'derived check')
AUTH.write_text(s)

# ---------- UI ----------
s = TSX.read_text()
old = '''          <div className={styles.conversationBody}>
            <div className={styles.assistantBadge}>{t("assistant")}</div>
            <div className={styles.emptyConversation}>
              <div className={styles.emptyGlyph}>◇</div>
              <strong>{t("noData")}</strong>
              <p>{t("emptyConversation")}</p>
            </div>
          </div>

          <div className={styles.contextStrip}>
            <DataRow label="conversation_id" />
            <DataRow label="thread_id" />
            <DataRow label="branch_id" />
            <DataRow label="context_snapshot_ref" />
          </div>
'''
new = '''          <div className={styles.conversationBody}>
            <div className={styles.assistantBadge}>{t("assistant")}</div>
            <div className={styles.emptyConversation}>
              <div className={styles.emptyGlyph}>◇</div>
              <strong>{t("noData")}</strong>
              <p>{t("emptyConversation")}</p>
            </div>
          </div>

          <div className={styles.contextStrip}>
            <DataRow label="conversation_id" />
            <DataRow label="thread_id" />
            <DataRow label="branch_id" />
            <DataRow label="context_snapshot_ref" />
          </div>

          <div
            className={styles.composer}
            data-component-uid="SYS-01-CMP-CONVERSATION-COMPOSER"
            data-visual-uid="SYS-01-VIS-CONVERSATION-COMPOSER"
          >
            <textarea
              id="SYS-01-INP-MESSAGE"
              data-control-id="SYS-01-INP-MESSAGE"
              className={styles.composerInput}
              aria-label={t("messageInput")}
              placeholder={t("messagePlaceholder")}
              rows={3}
            />
            <div className={styles.composerActions}>
              <button id="SYS-01-BTN-ATTACH" data-control-id="SYS-01-BTN-ATTACH" className={styles.composerButton} type="button" disabled>{t("attach")}</button>
              <button id="SYS-01-BTN-STOP" data-control-id="SYS-01-BTN-STOP" className={styles.composerButton} type="button" disabled>{t("stop")}</button>
              <button id="SYS-01-BTN-SEND" data-control-id="SYS-01-BTN-SEND" className={`${styles.composerButton} ${styles.composerSend}`} type="button" disabled>{t("send")}</button>
            </div>
          </div>
'''
s = replace_once(s, old, new, 'tsx composer insertion')
TSX.write_text(s)

# ---------- CSS ----------
s = CSS.read_text()
s = replace_once(s, '''.primaryGrid {
  display: grid;
  grid-template-columns: minmax(310px, 0.92fr) minmax(820px, 2.4fr);
  gap: 16px;
  align-items: stretch;
}
''', '''.primaryGrid {
  display: grid;
  grid-template-columns: minmax(290px, 0.72fr) minmax(880px, 2.7fr);
  gap: 16px;
  align-items: stretch;
}
''', 'primary grid')
s = replace_once(s, '''.conversationPanel {
  min-height: 490px;
  display: flex;
  flex-direction: column;
}
''', '''.conversationPanel {
  min-height: 610px;
  display: flex;
  flex-direction: column;
}
''', 'conversation size')
s = replace_once(s, '  min-height: 330px;\n', '  min-height: 360px;\n', 'conversation body size')
composer_css = '''
.composer {
  min-height: 112px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 10px;
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--border-normal);
  border-radius: 10px;
  background: rgba(7, 11, 29, 0.94);
}

.composerInput {
  width: 100%;
  min-height: 82px;
  max-height: 220px;
  resize: vertical;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-input);
  color: var(--text-primary);
  padding: 10px 12px;
  font: inherit;
  font-size: 12px;
  line-height: 1.5;
  outline: none;
}

.composerInput::placeholder { color: var(--text-muted); }
.composerInput:focus { border-color: var(--border-active); box-shadow: 0 0 0 2px rgba(139, 92, 255, 0.12); }

.composerActions {
  display: flex;
  align-items: center;
  gap: 7px;
  padding-bottom: 1px;
}

.composerButton {
  min-height: 40px;
  min-width: 64px;
  padding: 0 11px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-input);
  color: var(--text-secondary);
  font-size: 11px;
}

.composerSend {
  min-width: 76px;
  border-color: var(--border-active);
  background: var(--purple-active);
  color: var(--text-primary);
}

.composerButton:disabled { opacity: 0.58; cursor: not-allowed; }
'''
s = replace_once(s, '\n.secondaryGrid,\n.bottomGrid {\n', composer_css + '\n.secondaryGrid,\n.bottomGrid {\n', 'composer css')
s = replace_once(s, '@media (max-width: 1439px) {\n  .primaryGrid { grid-template-columns: 310px minmax(0, 1fr); }\n', '@media (max-width: 1439px) {\n  .primaryGrid { grid-template-columns: 290px minmax(0, 1fr); }\n', 'responsive grid')
CSS.write_text(s)

# ---------- i18n ----------
s = CAT.read_text()
s = replace_once(s, '  emptyConversation: { "zh-TW": "系統上下文解析完成後，設計對話會在此進行。", "zh-CN": "系统上下文解析完成后，设计对话会在此进行。", en: "Design conversation becomes available after system context is resolved." },\n', '  emptyConversation: { "zh-TW": "系統上下文解析完成後，設計對話會在此進行。", "zh-CN": "系统上下文解析完成后，设计对话会在此进行。", en: "Design conversation becomes available after system context is resolved." },\n  messageInput: { "zh-TW": "AI 對話輸入", "zh-CN": "AI 对话输入", en: "AI conversation input" },\n  messagePlaceholder: { "zh-TW": "輸入系統設計、維護或變更問題…", "zh-CN": "输入系统设计、维护或变更问题…", en: "Enter a system design, maintenance, or change question…" },\n  attach: { "zh-TW": "附件", "zh-CN": "附件", en: "Attach" },\n  send: { "zh-TW": "送出", "zh-CN": "发送", en: "Send" },\n  stop: { "zh-TW": "停止", "zh-CN": "停止", en: "Stop" },\n', 'catalog composer labels')
CAT.write_text(s)

# ---------- Optional tracker update after successful validation ----------
if os.environ.get('ACPOS_FINALIZE_TRACKER') == '1':
    s = TRACKER.read_text()
    s = replace_once(s, '      current_registered_controls: 8\n', '      current_registered_controls: 12\n', 'tracker control count')
    marker = '      global_active_nav_state: PASS\n'
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
        manual_visual_inspection: PASS
'''
    s = replace_once(s, marker, insert, 'tracker composer remediation')
    TRACKER.write_text(s)
