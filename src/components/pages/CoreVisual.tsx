"use client";

import { useReducer, useState, type MouseEvent as ReactMouseEvent } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { INITIAL_CORE_CLIENT_STATE, reduceCoreClientState } from "@/domain/core/coreClientState";
import { invokeCoreAction } from "@/domain/core/coreClientPort";
import type { CoreActionUid } from "@/domain/core/coreRuntimeContract";
import styles from "./CoreVisual.module.css";

type LabelKey = TranslationKey;

type ControlProps = {
  id: string;
  labelKey: LabelKey;
  actionUid?: CoreActionUid;
  primary?: boolean;
  compact?: boolean;
  disabled?: boolean;
  onClick?: () => void;
};

function ActionButton({ id, labelKey, actionUid, primary = false, compact = false, disabled = false, onClick }: ControlProps) {
  const { t } = useI18n();
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      data-control-id={id}
      data-action-uid={actionUid}
      className={`${styles.button} ${primary ? styles.primaryButton : ""} ${compact ? styles.compactButton : ""}`}
    >
      {t(labelKey)}
    </button>
  );
}

function ReadonlyField({ id, labelKey, actionUid, value = "—" }: ControlProps & { value?: string }) {
  const { t } = useI18n();
  return (
    <div className={styles.readonlyField} data-control-id={id} data-action-uid={actionUid}>
      <span className={styles.fieldLabel}>{t(labelKey)}</span>
      <span className={styles.fieldValue}>{value}</span>
    </div>
  );
}

function EmptyList({ id, labelKey, actionUid }: ControlProps) {
  const { t } = useI18n();
  return (
    <div className={styles.listControl} data-control-id={id} data-action-uid={actionUid}>
      <div className={styles.subheading}>{t(labelKey)}</div>
      <div className={styles.emptyValue}>—</div>
    </div>
  );
}

function PanelTitle({ labelKey }: { labelKey: LabelKey }) {
  const { t } = useI18n();
  return <h2 className={styles.panelTitle}>{t(labelKey)}</h2>;
}

const MESSAGE_MENU: readonly { id: string; key: LabelKey; actionUid: CoreActionUid }[] = [
  { id: "CORE-01-MENU-QUOTE", key: "core01.control.quote", actionUid: "CORE-01-ACT-MSG-QUOTE" },
  { id: "CORE-01-MENU-CONTINUE", key: "core01.control.continue", actionUid: "CORE-01-ACT-MSG-CONTINUE" },
  { id: "CORE-01-MENU-ANALYZE", key: "core01.control.analyze", actionUid: "CORE-01-ACT-MSG-ANALYZE" },
  { id: "CORE-01-MENU-DECISION", key: "core01.control.decision_list", actionUid: "CORE-01-ACT-MSG-DECISION" },
  { id: "CORE-01-MENU-BRANCH", key: "core01.control.branch", actionUid: "CORE-01-ACT-MSG-BRANCH" },
  { id: "CORE-01-MENU-COPY", key: "core01.control.copy", actionUid: "CORE-01-ACT-MSG-COPY" },
] as const;

export function CoreVisual() {
  const { t } = useI18n();
  const [state, dispatch] = useReducer(reduceCoreClientState, INITIAL_CORE_CLIENT_STATE);
  const [menuOpen, setMenuOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [humanDecision, setHumanDecision] = useState("");
  const [runtimeStage, setRuntimeStage] = useState("READY");

  const hasProject = Boolean(state.project_ref);
  const hasTopic = Boolean(state.topic_ref);
  const hasWorkItem = Boolean(state.work_item);
  const hasThread = Boolean(state.thread_ref);
  const pageMode = hasTopic ? "TOPIC_PRODUCTION" : hasProject ? "PROJECT_CORE" : "—";

  const runServerAction = async (actionUid: CoreActionUid, options?: Parameters<typeof invokeCoreAction>[0]) => {
    setRuntimeStage("REQUESTING");
    const result = await invokeCoreAction({ action_uid: actionUid, ...options });
    setRuntimeStage(result.ok ? "READY" : `BLOCKED · ${result.reason_code}`);
    return result;
  };

  const openContextMenu = (event: ReactMouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (hasThread) setMenuOpen(true);
  };

  const handleMessageMenu = async (actionUid: CoreActionUid) => {
    if (!hasThread || !state.thread_ref) return;
    const messageRef = "current-message";
    if (actionUid === "CORE-01-ACT-MSG-QUOTE") dispatch({ action_uid: actionUid, message_ref: messageRef });
    else if (actionUid === "CORE-01-ACT-MSG-CONTINUE") dispatch({ action_uid: actionUid, message_ref: messageRef });
    else if (actionUid === "CORE-01-ACT-MSG-DECISION") dispatch({ action_uid: actionUid, message_ref: messageRef });
    else if (actionUid === "CORE-01-ACT-MSG-COPY") await navigator.clipboard?.writeText(messageRef);
    else if (actionUid === "CORE-01-ACT-MSG-ANALYZE") {
      await runServerAction(actionUid, { path_params: { conversationId: state.thread_ref }, payload: { source_message_id: messageRef, instruction: "ANALYZE" } });
    } else if (actionUid === "CORE-01-ACT-MSG-BRANCH" && state.project_ref) {
      await runServerAction(actionUid, { path_params: { projectId: state.project_ref }, payload: { parent_thread_ref: state.thread_ref, work_item: state.work_item, source_message_id: messageRef } });
    }
    setMenuOpen(false);
  };

  const sendMessage = async () => {
    if (!hasThread || !state.thread_ref || !message.trim()) return;
    const result = await runServerAction("CORE-01-ACT-SEND", { path_params: { conversationId: state.thread_ref }, payload: { message: message.trim(), attachment_refs: state.attachment_refs, reference_refs: state.reference_refs, message_refs: state.composer_message_refs } });
    if (result.ok) setMessage("");
  };

  const noExternalContext = true;

  return (
    <div
      className={styles.page}
      data-page-uid="CORE-01"
      data-vis-step="VIS-02"
      data-page-state={hasProject ? "BOUND" : "EMPTY"}
      onClick={() => menuOpen && setMenuOpen(false)}
    >
      <section className={styles.contextBar} data-section-id="CORE-01-SEC-01" data-visual-id="CORE-01-VIS-CONTEXT">
        <div className={styles.contextComponent} data-component-uid="CORE-01-CMP-CONTEXT">
          <label className={styles.selectField}>
            <span>{t("core01.control.project")}</span>
            <select disabled={noExternalContext} data-control-id="CORE-01-CTL-PROJECT" data-action-uid="CORE-01-ACT-PROJECT-SELECT" aria-label={t("core01.control.project")}><option>—</option></select>
          </label>
          <ActionButton id="CORE-01-BTN-PROJECT-CREATE" labelKey="core01.control.create_project" actionUid="CORE-01-ACT-PROJECT-CREATE" primary disabled={noExternalContext} />
          <label className={styles.selectField}>
            <span>{t("core01.control.topic")}</span>
            <select disabled={!hasProject || noExternalContext} data-control-id="CORE-01-CTL-TOPIC" data-action-uid="CORE-01-ACT-TOPIC-SELECT" aria-label={t("core01.control.topic")}><option>—</option></select>
          </label>
          <ActionButton id="CORE-01-BTN-TOPIC-CREATE" labelKey="core01.control.create_topic" actionUid="CORE-01-ACT-TOPIC-CREATE" primary disabled={!hasProject || noExternalContext} />
          <ReadonlyField id="CORE-01-FLD-PAGE-MODE" labelKey="core01.control.page_mode" actionUid="CORE-01-ACT-PROJECT-SELECT" value={pageMode} />
          <ReadonlyField id="CORE-01-FLD-NAMING-AUTHORITY" labelKey="core01.control.naming_authority" actionUid="CORE-01-ACT-PROJECT-SELECT" />
        </div>
      </section>

      <div className={styles.primaryGrid} data-layout="CORE-01-PRIMARY-GRID">
        <aside className={styles.leftRail}>
          <section className={styles.panel} data-section-id="CORE-01-SEC-02" data-visual-id="CORE-01-VIS-LEFT">
            <div data-component-uid="CORE-01-CMP-NAV"><EmptyList id="CORE-01-LST-WORK-ITEMS" labelKey="core01.control.work_items" actionUid="CORE-01-ACT-WORK-ITEM-SELECT" /></div>
            <div className={styles.divider} />
            <div data-component-uid="CORE-01-CMP-THREADS">
              <div className={styles.threadHeader}>
                <PanelTitle labelKey="core01.group.conversation_threads" />
                <ActionButton id="CORE-01-BTN-NEW-THREAD" labelKey="core01.control.new_thread" actionUid="CORE-01-ACT-THREAD-CREATE" compact disabled={!hasProject || !hasWorkItem || noExternalContext} />
              </div>
              <div className={styles.threadListScroll}><EmptyList id="CORE-01-LST-THREADS" labelKey="core01.control.threads" actionUid="CORE-01-ACT-THREAD-SELECT" /></div>
            </div>
          </section>
        </aside>

        <main className={styles.centerColumn}>
          <section className={`${styles.panel} ${styles.conversationHeader}`} data-section-id="CORE-01-SEC-03" data-visual-id="CORE-01-VIS-CENTER-HEADER">
            <div className={styles.conversationHeaderInner} data-component-uid="CORE-01-CMP-CONV-HEADER">
              <PanelTitle labelKey="core01.group.conversation" />
              <div className={styles.aiModeGroup}>
                <ActionButton id="CORE-01-BTN-SINGLE-AI" labelKey="core01.control.single_ai" actionUid="CORE-01-ACT-AI-MODE-SINGLE" compact disabled={!hasWorkItem} onClick={() => dispatch({ action_uid: "CORE-01-ACT-AI-MODE-SINGLE" })} />
                <ActionButton id="CORE-01-BTN-MULTI-AI" labelKey="core01.control.multi_ai" actionUid="CORE-01-ACT-AI-MODE-MULTI" compact disabled={!hasWorkItem || noExternalContext} onClick={() => dispatch({ action_uid: "CORE-01-ACT-AI-MODE-MULTI" })} />
              </div>
              <ReadonlyField id="CORE-01-FLD-ASSIGNED-AI" labelKey="core01.control.assigned_ai" actionUid="CORE-01-ACT-ASSISTANT-RECORD" />
              <ActionButton id="CORE-01-BTN-ASSISTANT-RECORD" labelKey="core01.control.assistant_record" actionUid="CORE-01-ACT-ASSISTANT-RECORD" compact onClick={() => dispatch({ action_uid: "CORE-01-ACT-ASSISTANT-RECORD", open: !state.assistant_record_open })} />
            </div>
          </section>

          <section className={`${styles.panel} ${styles.messagesPanel}`} data-section-id="CORE-01-SEC-04" data-visual-id="CORE-01-VIS-MESSAGES">
            <div className={styles.messageWorkspace} data-component-uid="CORE-01-CMP-MESSAGES" onContextMenu={openContextMenu}>
              <PanelTitle labelKey="core01.group.message_workspace" />
              <div className={styles.messageEmpty}>—</div>
              {menuOpen && (
                <div className={styles.contextMenu} data-component-uid="CORE-01-CMP-MESSAGE-MENU" onClick={(event) => event.stopPropagation()}>
                  {MESSAGE_MENU.map((item) => (
                    <button key={item.id} type="button" disabled={!hasThread} onClick={() => void handleMessageMenu(item.actionUid)} className={styles.contextMenuItem} data-control-id={item.id} data-action-uid={item.actionUid}>{t(item.key)}</button>
                  ))}
                </div>
              )}
              {!menuOpen && <div className={styles.menuComponentSentinel} data-component-uid="CORE-01-CMP-MESSAGE-MENU" aria-hidden="true" />}
            </div>
          </section>

          <section className={`${styles.panel} ${styles.decisionPanel}`} data-section-id="CORE-01-SEC-05" data-visual-id="CORE-01-VIS-DECISION">
            <PanelTitle labelKey="core01.group.decision" />
            <div className={styles.decisionGrid}>
              <div data-component-uid="CORE-01-CMP-SUMMARY"><ReadonlyField id="CORE-01-FLD-ASSISTANT-SUMMARY" labelKey="core01.control.assistant_summary" actionUid="CORE-01-ACT-CANDIDATE-CREATE" /></div>
              <div data-component-uid="CORE-01-CMP-EVALUATION"><ReadonlyField id="CORE-01-FLD-EVALUATION" labelKey="core01.control.evaluation" actionUid="CORE-01-ACT-CANDIDATE-CREATE" /></div>
              <div className={styles.humanDecision} data-component-uid="CORE-01-CMP-HUMAN-DECISION">
                <label className={styles.textareaField}>
                  <span>{t("core01.control.human_decision")}</span>
                  <textarea disabled={!hasThread} data-control-id="CORE-01-FLD-HUMAN-DECISION" data-action-uid="CORE-01-ACT-CANDIDATE-CREATE" value={humanDecision} onChange={(event) => setHumanDecision(event.target.value)} aria-label={t("core01.control.human_decision")} />
                </label>
                <ReadonlyField id="CORE-01-FLD-STRUCTURED-DECISION" labelKey="core01.control.structured_decision" actionUid="CORE-01-ACT-CANDIDATE-CREATE" />
                <div className={styles.actionRow}>
                  <ActionButton id="CORE-01-BTN-CANDIDATE-CREATE" labelKey="core01.control.create_candidate" actionUid="CORE-01-ACT-CANDIDATE-CREATE" primary disabled={!hasThread || !humanDecision.trim() || noExternalContext} />
                  <ActionButton id="CORE-01-BTN-CANDIDATE-CONFIRM" labelKey="core01.control.confirm_candidate" actionUid="CORE-01-ACT-CANDIDATE-ACCEPT" primary disabled={noExternalContext} />
                  <ActionButton id="CORE-01-BTN-RETURN-MODIFY" labelKey="core01.control.return_modify" actionUid="CORE-01-ACT-CANDIDATE-RETURN" disabled={noExternalContext} />
                </div>
              </div>
            </div>
          </section>

          <section className={styles.runtimeStrip} data-section-id="CORE-01-SEC-06" data-visual-id="CORE-01-VIS-RUNTIME">
            <div className={styles.runtimeComponent} data-component-uid="CORE-01-CMP-RUNTIME" data-control-id="CORE-01-FLD-RUNTIME-STAGE" data-action-uid="CORE-01-ACT-PROJECT-SELECT"><span>{t("core01.control.runtime_stage")}</span><strong>{runtimeStage}</strong></div>
          </section>

          <section className={`${styles.panel} ${styles.composerPanel}`} data-section-id="CORE-01-SEC-07" data-visual-id="CORE-01-VIS-COMPOSER">
            <div className={styles.composer} data-component-uid="CORE-01-CMP-COMPOSER">
              <div className={styles.composerTools}>
                <ActionButton id="CORE-01-BTN-ATTACHMENT" labelKey="core01.control.attachment" actionUid="CORE-01-ACT-ATTACHMENT" compact disabled={!hasThread || noExternalContext} />
                <ActionButton id="CORE-01-BTN-REFERENCE" labelKey="core01.control.reference" actionUid="CORE-01-ACT-REFERENCE-ATTACH" compact disabled={!hasThread || noExternalContext} />
              </div>
              <textarea disabled={!hasThread} data-control-id="CORE-01-FLD-MESSAGE" data-action-uid="CORE-01-ACT-SEND" aria-label={t("core01.control.message")} placeholder={t("core01.control.message")} value={message} onChange={(event) => setMessage(event.target.value)} />
              <ActionButton id="CORE-01-BTN-SEND" labelKey="core01.control.send" actionUid="CORE-01-ACT-SEND" primary disabled={!hasThread || !message.trim()} onClick={() => void sendMessage()} />
            </div>
          </section>
        </main>

        <aside className={styles.rightRail}>
          <section className={styles.panel} data-section-id="CORE-01-SEC-08" data-visual-id="CORE-01-VIS-RIGHT-CORE">
            <div className={styles.stateBlock} data-component-uid="CORE-01-CMP-PROJECT-STATE">
              <PanelTitle labelKey="core01.group.project_core_state" /><div className={styles.stateValue}>—</div>
              <div className={styles.stackActions}>
                <ActionButton id="CORE-01-BTN-PROJECT-VALIDATE" labelKey="core01.control.project_validate" actionUid="CORE-01-ACT-PROJECT-VALIDATE" disabled={noExternalContext} />
                <ActionButton id="CORE-01-BTN-PROJECT-CONFIRM" labelKey="core01.control.project_confirm" actionUid="CORE-01-ACT-PROJECT-CONFIRM" disabled={noExternalContext} />
                <ActionButton id="CORE-01-BTN-STORY-CANDIDATE" labelKey="core01.control.story_candidate" actionUid="CORE-01-ACT-STORY-CANDIDATE" disabled={noExternalContext} />
                <ActionButton id="CORE-01-BTN-DNA-LOCK" labelKey="core01.control.dna_lock" actionUid="CORE-01-ACT-DNA-LOCK-REQUEST" disabled={noExternalContext} />
                <ActionButton id="CORE-01-BTN-CORE-REVIEW" labelKey="core01.control.core_review" actionUid="CORE-01-ACT-CORE-REVIEW-SUBMIT" disabled={noExternalContext} />
                <ActionButton id="CORE-01-BTN-PROJECT-LOCK" labelKey="core01.control.project_lock" actionUid="CORE-01-ACT-MOTHER-LOCK-REQUEST" disabled={noExternalContext} />
              </div>
            </div>
            <div className={styles.divider} />
            <div className={styles.stateBlock} data-component-uid="CORE-01-CMP-BLUEPRINT-STATE">
              <PanelTitle labelKey="core01.group.blueprint_state" /><div className={styles.stateValue}>—</div>
              <div className={styles.stackActions}>
                <ActionButton id="CORE-01-BTN-BLUEPRINT-CREATE" labelKey="core01.control.blueprint_create" actionUid="CORE-01-ACT-BLUEPRINT-CREATE" disabled={noExternalContext} />
                <ActionButton id="CORE-01-BTN-BLUEPRINT-VALIDATE" labelKey="core01.control.blueprint_validate" actionUid="CORE-01-ACT-BLUEPRINT-VALIDATE" disabled={noExternalContext} />
                <ActionButton id="CORE-01-BTN-BLUEPRINT-APPROVE" labelKey="core01.control.blueprint_approve" actionUid="CORE-01-ACT-BLUEPRINT-APPROVE" disabled={noExternalContext} />
                <ActionButton id="CORE-01-BTN-CHILD-LOCK" labelKey="core01.control.child_lock" actionUid="CORE-01-ACT-CHILD-LOCK-REQUEST" disabled={noExternalContext} />
              </div>
            </div>
          </section>

          <section className={styles.panel} data-section-id="CORE-01-SEC-09" data-visual-id="CORE-01-VIS-RIGHT-TOPIC">
            <div data-component-uid="CORE-01-CMP-TOPIC-PACKAGE">
              <PanelTitle labelKey="core01.group.topic_package" />
              <ReadonlyField id="CORE-01-FLD-TOPIC-SCOPE" labelKey="core01.control.topic_scope" actionUid="CORE-01-ACT-TOPIC-SELECT" />
              <ActionButton id="CORE-01-BTN-CANONICAL-SCRIPT" labelKey="core01.control.canonical_script" actionUid="CORE-01-ACT-CANONICAL-SCRIPT-VIEW" disabled={!hasTopic || noExternalContext} />
              <ReadonlyField id="CORE-01-FLD-PACKAGE" labelKey="core01.control.package" actionUid="CORE-01-ACT-CANONICAL-SCRIPT-VIEW" />
            </div>
            <div className={styles.divider} />
            <div data-component-uid="CORE-01-CMP-DOWNSTREAM">
              <PanelTitle labelKey="core01.group.downstream" />
              <ReadonlyField id="CORE-01-FLD-DOWNSTREAM-ASSET" labelKey="core01.control.downstream_asset" actionUid="CORE-01-ACT-CANONICAL-SCRIPT-VIEW" />
              <ReadonlyField id="CORE-01-FLD-DOWNSTREAM-VIDEO" labelKey="core01.control.downstream_video" actionUid="CORE-01-ACT-CANONICAL-SCRIPT-VIEW" />
              <ReadonlyField id="CORE-01-FLD-DOWNSTREAM-EDIT" labelKey="core01.control.downstream_edit" actionUid="CORE-01-ACT-CANONICAL-SCRIPT-VIEW" />
            </div>
          </section>

          <section className={styles.panel} data-section-id="CORE-01-SEC-10" data-visual-id="CORE-01-VIS-RIGHT-VERSION">
            <div data-component-uid="CORE-01-CMP-VERSION">
              <PanelTitle labelKey="core01.group.version" />
              <ActionButton id="CORE-01-BTN-CANDIDATE-COMPARE" labelKey="core01.control.candidate_compare" actionUid="CORE-01-ACT-CANDIDATE-COMPARE" disabled={noExternalContext} />
              <ReadonlyField id="CORE-01-FLD-VERSION-STATE" labelKey="core01.control.version_state" actionUid="CORE-01-ACT-CANDIDATE-COMPARE" />
            </div>
            <div className={styles.divider} />
            <div data-component-uid="CORE-01-CMP-LOCK-REVIEW">
              <PanelTitle labelKey="core01.group.lock_review" />
              <ReadonlyField id="CORE-01-FLD-LOCK-REVIEW" labelKey="core01.control.lock_review" actionUid="CORE-01-ACT-MOTHER-LOCK-REQUEST" />
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
