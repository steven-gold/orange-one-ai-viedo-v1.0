"use client";

import { useEffect, useReducer, useState, type MouseEvent as ReactMouseEvent } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { invokeCoreAction, readCoreProjection } from "@/domain/core/coreClientPort";
import { requestCoreDraftFormPayload } from "@/domain/core/coreDraftFormAdapter";
import { requestCoreMessageSendPayload, requestCoreThreadCreatePayload } from "@/domain/core/coreConversationPayloadAdapter";
import { requestCoreCandidateCreatePayload, requestCoreCandidateDecisionPayload } from "@/domain/core/coreCandidatePayloadAdapter";
import { requestCoreLockCommandPayload, type CoreLockCommandKind } from "@/domain/core/coreLockCommandPayloadAdapter";
import { INITIAL_CORE_CLIENT_STATE, reduceCoreClientState } from "@/domain/core/coreClientState";
import type { CoreActionUid } from "@/domain/core/coreRuntimeContract";
import styles from "./CoreVisual.module.css";

type LabelKey = TranslationKey;
type PageState = "LOADING" | "READY" | "ERROR";
type ConversationUiMessage = { id: string; role: "USER" | "STATUS"; text: string };
type ControlProps = { id: string; labelKey: LabelKey; primary?: boolean; compact?: boolean; disabled?: boolean; onClick?: () => void };

const CONTROL_ACTION_UID: Record<string, CoreActionUid> = {
  "CORE-01-CTL-PROJECT": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-BTN-PROJECT-CREATE": "CORE-01-ACT-PROJECT-CREATE",
  "CORE-01-CTL-TOPIC": "CORE-01-ACT-TOPIC-SELECT",
  "CORE-01-BTN-TOPIC-CREATE": "CORE-01-ACT-TOPIC-CREATE",
  "CORE-01-FLD-PAGE-MODE": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-FLD-NAMING-AUTHORITY": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-LST-WORK-ITEMS": "CORE-01-ACT-WORK-ITEM-SELECT",
  "CORE-01-BTN-NEW-THREAD": "CORE-01-ACT-THREAD-CREATE",
  "CORE-01-LST-THREADS": "CORE-01-ACT-THREAD-SELECT",
  "CORE-01-BTN-SINGLE-AI": "CORE-01-ACT-AI-MODE-SINGLE",
  "CORE-01-BTN-MULTI-AI": "CORE-01-ACT-AI-MODE-MULTI",
  "CORE-01-FLD-ASSIGNED-AI": "CORE-01-ACT-ASSISTANT-RECORD",
  "CORE-01-BTN-ASSISTANT-RECORD": "CORE-01-ACT-ASSISTANT-RECORD",
  "CORE-01-MENU-QUOTE": "CORE-01-ACT-MSG-QUOTE",
  "CORE-01-MENU-CONTINUE": "CORE-01-ACT-MSG-CONTINUE",
  "CORE-01-MENU-ANALYZE": "CORE-01-ACT-MSG-ANALYZE",
  "CORE-01-MENU-DECISION": "CORE-01-ACT-MSG-DECISION",
  "CORE-01-MENU-BRANCH": "CORE-01-ACT-MSG-BRANCH",
  "CORE-01-MENU-COPY": "CORE-01-ACT-MSG-COPY",
  "CORE-01-FLD-ASSISTANT-SUMMARY": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-FLD-EVALUATION": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-FLD-HUMAN-DECISION": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-FLD-STRUCTURED-DECISION": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-BTN-CANDIDATE-CREATE": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-BTN-CANDIDATE-CONFIRM": "CORE-01-ACT-CANDIDATE-ACCEPT",
  "CORE-01-BTN-RETURN-MODIFY": "CORE-01-ACT-CANDIDATE-RETURN",
  "CORE-01-FLD-RUNTIME-STAGE": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-BTN-ATTACHMENT": "CORE-01-ACT-ATTACHMENT",
  "CORE-01-BTN-REFERENCE": "CORE-01-ACT-REFERENCE-ATTACH",
  "CORE-01-FLD-MESSAGE": "CORE-01-ACT-SEND",
  "CORE-01-BTN-SEND": "CORE-01-ACT-SEND",
  "CORE-01-BTN-PROJECT-VALIDATE": "CORE-01-ACT-PROJECT-VALIDATE",
  "CORE-01-BTN-PROJECT-CONFIRM": "CORE-01-ACT-PROJECT-CONFIRM",
  "CORE-01-BTN-STORY-CANDIDATE": "CORE-01-ACT-STORY-CANDIDATE",
  "CORE-01-BTN-DNA-LOCK": "CORE-01-ACT-DNA-LOCK-REQUEST",
  "CORE-01-BTN-CORE-REVIEW": "CORE-01-ACT-CORE-REVIEW-SUBMIT",
  "CORE-01-BTN-PROJECT-LOCK": "CORE-01-ACT-MOTHER-LOCK-REQUEST",
  "CORE-01-BTN-BLUEPRINT-CREATE": "CORE-01-ACT-BLUEPRINT-CREATE",
  "CORE-01-BTN-BLUEPRINT-VALIDATE": "CORE-01-ACT-BLUEPRINT-VALIDATE",
  "CORE-01-BTN-BLUEPRINT-APPROVE": "CORE-01-ACT-BLUEPRINT-APPROVE",
  "CORE-01-BTN-CHILD-LOCK": "CORE-01-ACT-CHILD-LOCK-REQUEST",
  "CORE-01-FLD-TOPIC-SCOPE": "CORE-01-ACT-TOPIC-SELECT",
  "CORE-01-BTN-CANONICAL-SCRIPT": "CORE-01-ACT-CANONICAL-SCRIPT-VIEW",
  "CORE-01-FLD-PACKAGE": "CORE-01-ACT-CANONICAL-SCRIPT-VIEW",
  "CORE-01-FLD-DOWNSTREAM-ASSET": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-FLD-DOWNSTREAM-VIDEO": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-FLD-DOWNSTREAM-EDIT": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-BTN-CANDIDATE-COMPARE": "CORE-01-ACT-CANDIDATE-COMPARE",
  "CORE-01-FLD-VERSION-STATE": "CORE-01-ACT-CANDIDATE-COMPARE",
  "CORE-01-FLD-LOCK-REVIEW": "CORE-01-ACT-PROJECT-SELECT",
};

function actionUid(id: string): CoreActionUid { return CONTROL_ACTION_UID[id]; }
function ActionButton({ id, labelKey, primary = false, compact = false, disabled = false, onClick }: ControlProps) {
  const { t } = useI18n();
  return <button type="button" disabled={disabled} onClick={onClick} data-control-id={id} data-action-uid={actionUid(id)} data-runtime-binding={disabled ? "BUSY" : "ACTION_BOUND"} className={`${styles.button} ${primary ? styles.primaryButton : ""} ${compact ? styles.compactButton : ""}`}>{t(labelKey)}</button>;
}
function ReadonlyField({ id, labelKey, value = "—" }: ControlProps & { value?: string }) {
  const { t } = useI18n();
  return <div className={styles.readonlyField} data-control-id={id} data-action-uid={actionUid(id)}><span className={styles.fieldLabel}>{t(labelKey)}</span><span className={styles.fieldValue}>{value}</span></div>;
}
function EmptyList({ id, labelKey }: ControlProps) {
  const { t } = useI18n();
  return <div className={styles.listControl} data-control-id={id} data-action-uid={actionUid(id)}><div className={styles.subheading}>{t(labelKey)}</div><div className={styles.emptyValue}>—</div></div>;
}
function PanelTitle({ labelKey }: { labelKey: LabelKey }) { const { t } = useI18n(); return <h2 className={styles.panelTitle}>{t(labelKey)}</h2>; }

const MESSAGE_MENU: readonly { id: string; key: LabelKey }[] = [
  { id: "CORE-01-MENU-QUOTE", key: "core01.control.quote" }, { id: "CORE-01-MENU-CONTINUE", key: "core01.control.continue" },
  { id: "CORE-01-MENU-ANALYZE", key: "core01.control.analyze" }, { id: "CORE-01-MENU-DECISION", key: "core01.control.decision_list" },
  { id: "CORE-01-MENU-BRANCH", key: "core01.control.branch" }, { id: "CORE-01-MENU-COPY", key: "core01.control.copy" },
] as const;

export function CoreVisual() {
  const { t } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  const [pageState, setPageState] = useState<PageState>("LOADING");
  const [runtimeReason, setRuntimeReason] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<CoreActionUid | null>(null);
  const [message, setMessage] = useState("");
  const [conversationMessages, setConversationMessages] = useState<ConversationUiMessage[]>([]);
  const [humanDecision, setHumanDecision] = useState("");
  const [clientState, dispatchClient] = useReducer(reduceCoreClientState, INITIAL_CORE_CLIENT_STATE);

  useEffect(() => {
    const controller = new AbortController();
    void readCoreProjection(controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      if (result.ok) { setPageState("READY"); setRuntimeReason(null); }
      else { setPageState("ERROR"); setRuntimeReason(result.reason_code); }
    });
    return () => controller.abort();
  }, []);

  const reportBlock = (reason: string) => { setPageState("ERROR"); setRuntimeReason(reason); };
  const appendConversationMessage = (role: ConversationUiMessage["role"], text: string) => {
    setConversationMessages((current) => [...current, { id: crypto.randomUUID(), role, text }]);
  };
  const runServerAction = async (action_uid: CoreActionUid, options: { path_params?: Record<string, string>; query?: Record<string, string>; payload?: unknown } = {}) => {
    if (busyAction) return null;
    setBusyAction(action_uid);
    const result = await invokeCoreAction({ action_uid, ...options });
    setBusyAction(null);
    if (result.ok) { setPageState("READY"); setRuntimeReason(null); }
    else { setPageState("ERROR"); setRuntimeReason(`${result.error_uid}:${result.reason_code}`); }
    return result;
  };

  const requireProjectId = () => clientState.project_id || (reportBlock("CORE-01-ERR-CONTEXT-001:REQUIRED_PROJECT_ID_MISSING"), null);
  const requireProjectVersionRef = () => clientState.project_version_ref || (reportBlock("CORE-01-ERR-VERSION-001:REQUIRED_PROJECT_VERSION_REF_MISSING"), null);
  const requireTopicId = () => clientState.topic_id || (reportBlock("CORE-01-ERR-TOPIC-LINEAGE-001:REQUIRED_TOPIC_ID_MISSING"), null);
  const requireConversationId = () => clientState.conversation_id || (reportBlock("CORE-01-ERR-THREAD-001:REQUIRED_CONVERSATION_ID_MISSING"), null);
  const requireBlueprintVersionRef = () => clientState.blueprint_version_ref || (reportBlock("CORE-01-ERR-BLUEPRINT-001:EXACT_BLUEPRINT_VERSION_REF_REQUIRED"), null);
  const requireDnaVersionRef = () => clientState.dna_version_ref || (reportBlock("CORE-01-ERR-DNA-LOCK-001:EXACT_DNA_VERSION_REF_REQUIRED"), null);
  const requireCandidateRef = () => clientState.candidate_ref || (reportBlock("CORE-01-ERR-CANDIDATE-001:EXACT_CANDIDATE_REF_REQUIRED"), null);
  const requireWorkItem = () => clientState.work_item || (reportBlock("CORE-01-ERR-WORK-ITEM-001:REQUIRED_WORK_ITEM_MISSING"), null);

  const runDraftCreate = async (kind: "PROJECT" | "TOPIC") => {
    const action: CoreActionUid = kind === "PROJECT" ? "CORE-01-ACT-PROJECT-CREATE" : "CORE-01-ACT-TOPIC-CREATE";
    const projectId = kind === "TOPIC" ? requireProjectId() : null;
    if (kind === "TOPIC" && !projectId) return;
    const form = await requestCoreDraftFormPayload(kind === "PROJECT" ? { kind } : { kind, project_id: projectId! });
    if (!form.ok) {
      reportBlock(`${kind === "PROJECT" ? "CORE-01-ERR-CONTEXT-001" : "CORE-01-ERR-TOPIC-LINEAGE-001"}:${form.reason_code}`);
      return;
    }
    const result = await runServerAction(action, kind === "PROJECT"
      ? { payload: form.payload }
      : { path_params: { projectId: projectId! }, payload: form.payload });
    if (result?.ok) {
      const projection = await readCoreProjection();
      if (!projection.ok) reportBlock(`${projection.error_uid}:${projection.reason_code}`);
    }
  };

  const runLockCommand = async (action: CoreActionUid, kind: CoreLockCommandKind) => {
    if (kind === "DNA_LOCK" && !requireDnaVersionRef()) return;
    if ((kind === "CORE_REVIEW" || kind === "MOTHER_LOCK") && !requireProjectVersionRef()) return;
    if (kind === "CHILD_LOCK" && !requireBlueprintVersionRef()) return;
    const payload = await requestCoreLockCommandPayload({ kind, project_id: clientState.project_id, project_version_ref: clientState.project_version_ref, dna_version_ref: clientState.dna_version_ref, blueprint_version_ref: clientState.blueprint_version_ref, topic_id: clientState.topic_id, evidence_refs: clientState.decision_evidence_refs });
    if (!payload.ok) {
      const error = kind === "DNA_LOCK" ? "CORE-01-ERR-DNA-LOCK-001" : kind === "CORE_REVIEW" ? "CORE-01-ERR-CONTEXT-001" : "CORE-01-ERR-LOCK-CONTRACT-001";
      reportBlock(`${error}:${payload.reason_code}`);
      return;
    }
    await runServerAction(action, { payload: payload.payload });
  };

  const runControl = (id: string) => {
    const action = actionUid(id);
    switch (action) {
      case "CORE-01-ACT-PROJECT-CREATE": void runDraftCreate("PROJECT"); return;
      case "CORE-01-ACT-TOPIC-CREATE": void runDraftCreate("TOPIC"); return;
      case "CORE-01-ACT-THREAD-CREATE": {
        const projectId = requireProjectId(); if (!projectId) return;
        const work_item = requireWorkItem(); if (!work_item) return;
        void (async()=>{
          const payload = await requestCoreThreadCreatePayload({ project_id: projectId, topic_id: clientState.topic_id, work_item, ai_mode: clientState.ai_mode });
          if (!payload.ok) { reportBlock(`CORE-01-ERR-THREAD-001:${payload.reason_code}`); return; }
          await runServerAction(action, { path_params: { projectId }, payload: payload.payload });
        })(); return;
      }
      case "CORE-01-ACT-AI-MODE-SINGLE": case "CORE-01-ACT-AI-MODE-MULTI": if (!requireWorkItem()) return; dispatchClient({ action_uid: action }); setPageState("READY"); setRuntimeReason(null); return;
      case "CORE-01-ACT-ASSISTANT-RECORD": dispatchClient({ action_uid: action, open: !clientState.assistant_record_open }); setPageState("READY"); setRuntimeReason(null); return;
      case "CORE-01-ACT-SEND": {
        const submitted = message.trim();
        if (!submitted) { reportBlock("CORE-01-ERR-CONVERSATION-001:MESSAGE_REQUIRED"); return; }
        const conversationId = clientState.conversation_id;
        if (!conversationId) { reportBlock("CORE-01-ERR-THREAD-001:REQUIRED_CONVERSATION_ID_MISSING"); return; }
        void (async () => {
          const payload = await requestCoreMessageSendPayload({ conversation_id: conversationId, message: submitted, ai_mode: clientState.ai_mode, attachment_refs: clientState.attachment_refs, reference_refs: clientState.reference_refs });
          if (!payload.ok) { reportBlock(`CORE-01-ERR-CONVERSATION-001:${payload.reason_code}`); return; }
          const result = await runServerAction(action, { path_params: { conversationId }, payload: payload.payload });
          if (!result) return;
          if (result.ok) { appendConversationMessage("USER", submitted); setMessage(""); }
          appendConversationMessage("STATUS", result.ok ? `MESSAGE_ACCEPTED:${result.correlation_id}` : `${result.error_uid}:${result.reason_code}`);
        })(); return;
      }
      case "CORE-01-ACT-CANDIDATE-CREATE": {
        const decisionText=humanDecision.trim();
        if (!decisionText) { reportBlock("CORE-01-ERR-DECISION-001:HUMAN_DECISION_REQUIRED"); return; }
        void (async()=>{
          const payload=await requestCoreCandidateCreatePayload({ human_decision:decisionText, evidence_refs:clientState.decision_evidence_refs, project_id:clientState.project_id, topic_id:clientState.topic_id, work_item:clientState.work_item });
          if(!payload.ok){ reportBlock(`CORE-01-ERR-CANDIDATE-001:${payload.reason_code}`); return; }
          await runServerAction(action,{payload:payload.payload});
        })(); return;
      }
      case "CORE-01-ACT-CANDIDATE-ACCEPT": case "CORE-01-ACT-CANDIDATE-RETURN": {
        const candidateRef=requireCandidateRef(); if(!candidateRef)return;
        const decisionText=humanDecision.trim();
        void (async()=>{
          const payload=await requestCoreCandidateDecisionPayload({ candidate_ref:candidateRef, decision:action==="CORE-01-ACT-CANDIDATE-ACCEPT"?"ACCEPT":"RETURN", reason_text:decisionText, evidence_refs:clientState.decision_evidence_refs });
          if(!payload.ok){ reportBlock(`CORE-01-ERR-DECISION-001:${payload.reason_code}`); return; }
          await runServerAction(action,{path_params:{id:candidateRef},payload:payload.payload});
        })(); return;
      }
      case "CORE-01-ACT-CANDIDATE-COMPARE": reportBlock("CORE-01-ERR-CANDIDATE-001:EXACT_CANDIDATE_SET_REQUIRED"); return;
      case "CORE-01-ACT-PROJECT-VALIDATE": { const projectVersionId = requireProjectVersionRef(); if (projectVersionId) void runServerAction(action, { path_params: { projectVersionId } }); return; }
      case "CORE-01-ACT-PROJECT-CONFIRM": { const projectVersionRef = requireProjectVersionRef(); if (projectVersionRef) void runServerAction(action, { path_params: { id: projectVersionRef } }); return; }
      case "CORE-01-ACT-STORY-CANDIDATE": { const projectId = requireProjectId(); if (projectId) void runServerAction(action, { path_params: { projectId } }); return; }
      case "CORE-01-ACT-DNA-LOCK-REQUEST": void runLockCommand(action,"DNA_LOCK"); return;
      case "CORE-01-ACT-CORE-REVIEW-SUBMIT": void runLockCommand(action,"CORE_REVIEW"); return;
      case "CORE-01-ACT-MOTHER-LOCK-REQUEST": void runLockCommand(action,"MOTHER_LOCK"); return;
      case "CORE-01-ACT-CHILD-LOCK-REQUEST": void runLockCommand(action,"CHILD_LOCK"); return;
      case "CORE-01-ACT-BLUEPRINT-CREATE": { const topicId = requireTopicId(); if (topicId) void runServerAction(action, { path_params: { id: topicId } }); return; }
      case "CORE-01-ACT-BLUEPRINT-VALIDATE": case "CORE-01-ACT-BLUEPRINT-APPROVE": { const blueprintVersionRef = requireBlueprintVersionRef(); if (blueprintVersionRef) void runServerAction(action, { path_params: { id: blueprintVersionRef } }); return; }
      case "CORE-01-ACT-CANONICAL-SCRIPT-VIEW": { const topicId = requireTopicId(); if (topicId) void runServerAction(action, { path_params: { id: topicId } }); return; }
      case "CORE-01-ACT-ATTACHMENT": if (!requireConversationId()) return; reportBlock("CORE-01-ERR-UNDEFINED-001:GLOBAL_ATTACHMENT_SELECTOR_NOT_BOUND"); return;
      case "CORE-01-ACT-REFERENCE-ATTACH": if (!requireConversationId()) return; reportBlock("CORE-01-ERR-UNDEFINED-001:GLOBAL_REFERENCE_SELECTOR_NOT_BOUND"); return;
      default: reportBlock("CORE-01-ERR-UNDEFINED-001:ACTION_REQUIRES_EXACT_RUNTIME_CONTEXT");
    }
  };

  const openContextMenu = (event: ReactMouseEvent<HTMLDivElement>) => { event.preventDefault(); setMenuOpen(true); };
  const runMessageMenu = (id: string) => { const action = actionUid(id); if (!clientState.conversation_id) { reportBlock("CORE-01-ERR-THREAD-001:REQUIRED_CONVERSATION_ID_MISSING"); return; } reportBlock(`${action}:EXACT_MESSAGE_REF_REQUIRED`); };
  const runtimeDisplay = runtimeReason ?? (clientState.assistant_record_open ? "ASSISTANT_RECORD_OPEN" : "—");
  const isBusy = busyAction !== null;

  return (
    <div className={styles.page} data-page-uid="CORE-01" data-vis-step="VIS-02" data-page-state={pageState} data-runtime-reason={runtimeReason ?? undefined} onClick={() => menuOpen && setMenuOpen(false)}>
      <section className={styles.contextBar} data-section-id="CORE-01-SEC-01" data-visual-id="CORE-01-VIS-CONTEXT"><div className={styles.contextComponent} data-component-uid="CORE-01-CMP-CONTEXT">
        <label className={styles.selectField}><span>{t("core01.control.project")}</span><select value={clientState.project_id ?? ""} onChange={(event) => dispatchClient({ action_uid: "CORE-01-ACT-PROJECT-SELECT", project_ref: event.target.value || null, project_id: event.target.value || null })} data-control-id="CORE-01-CTL-PROJECT" data-action-uid={actionUid("CORE-01-CTL-PROJECT")} aria-label={t("core01.control.project")}><option value="">—</option></select></label>
        <ActionButton id="CORE-01-BTN-PROJECT-CREATE" labelKey="core01.control.create_project" primary disabled={isBusy} onClick={() => runControl("CORE-01-BTN-PROJECT-CREATE")} />
        <label className={styles.selectField}><span>{t("core01.control.topic")}</span><select value={clientState.topic_id ?? ""} onChange={(event) => dispatchClient({ action_uid: "CORE-01-ACT-TOPIC-SELECT", topic_ref: event.target.value || null, topic_id: event.target.value || null })} data-control-id="CORE-01-CTL-TOPIC" data-action-uid={actionUid("CORE-01-CTL-TOPIC")} aria-label={t("core01.control.topic")}><option value="">—</option></select></label>
        <ActionButton id="CORE-01-BTN-TOPIC-CREATE" labelKey="core01.control.create_topic" primary disabled={isBusy} onClick={() => runControl("CORE-01-BTN-TOPIC-CREATE")} />
        <ReadonlyField id="CORE-01-FLD-PAGE-MODE" labelKey="core01.control.page_mode" /><ReadonlyField id="CORE-01-FLD-NAMING-AUTHORITY" labelKey="core01.control.naming_authority" value="ACPOS_SYSTEM" />
      </div></section>

      <div className={styles.primaryGrid} data-layout="CORE-01-PRIMARY-GRID">
        <aside className={styles.leftRail}><section className={styles.panel} data-section-id="CORE-01-SEC-02" data-visual-id="CORE-01-VIS-LEFT">
          <div data-component-uid="CORE-01-CMP-NAV"><EmptyList id="CORE-01-LST-WORK-ITEMS" labelKey="core01.control.work_items" /></div><div className={styles.divider} />
          <div data-component-uid="CORE-01-CMP-THREADS"><div className={styles.threadHeader}><PanelTitle labelKey="core01.group.conversation_threads" /><ActionButton id="CORE-01-BTN-NEW-THREAD" labelKey="core01.control.new_thread" compact disabled={isBusy} onClick={() => runControl("CORE-01-BTN-NEW-THREAD")} /></div><div className={styles.threadListScroll}><EmptyList id="CORE-01-LST-THREADS" labelKey="core01.control.threads" /></div></div>
        </section></aside>

        <main className={styles.centerColumn}>
          <section className={`${styles.panel} ${styles.conversationHeader}`} data-section-id="CORE-01-SEC-03" data-visual-id="CORE-01-VIS-CENTER-HEADER"><div className={styles.conversationHeaderInner} data-component-uid="CORE-01-CMP-CONV-HEADER"><PanelTitle labelKey="core01.group.conversation" /><div className={styles.aiModeGroup}><ActionButton id="CORE-01-BTN-SINGLE-AI" labelKey="core01.control.single_ai" compact disabled={isBusy} onClick={() => runControl("CORE-01-BTN-SINGLE-AI")} /><ActionButton id="CORE-01-BTN-MULTI-AI" labelKey="core01.control.multi_ai" compact disabled={isBusy} onClick={() => runControl("CORE-01-BTN-MULTI-AI")} /></div><ReadonlyField id="CORE-01-FLD-ASSIGNED-AI" labelKey="core01.control.assigned_ai" /><ActionButton id="CORE-01-BTN-ASSISTANT-RECORD" labelKey="core01.control.assistant_record" compact disabled={isBusy} onClick={() => runControl("CORE-01-BTN-ASSISTANT-RECORD")} /></div></section>
          <section className={`${styles.panel} ${styles.messagesPanel}`} data-section-id="CORE-01-SEC-04" data-visual-id="CORE-01-VIS-MESSAGES"><div className={styles.messageWorkspace} data-component-uid="CORE-01-CMP-MESSAGES" onContextMenu={openContextMenu}><PanelTitle labelKey="core01.group.message_workspace" />{conversationMessages.length ? <div data-conversation-local-log="true">{conversationMessages.map((entry) => <div key={entry.id} className={styles.readonlyField} data-message-role={entry.role} aria-label={entry.role}><span className={styles.fieldValue}>{entry.text}</span></div>)}</div> : <div className={styles.messageEmpty}>—</div>}{menuOpen && <div className={styles.contextMenu} data-component-uid="CORE-01-CMP-MESSAGE-MENU" onClick={(event) => event.stopPropagation()}>{MESSAGE_MENU.map((item) => <button key={item.id} type="button" className={styles.contextMenuItem} data-control-id={item.id} data-action-uid={actionUid(item.id)} data-runtime-binding="ACTION_BOUND" onClick={() => runMessageMenu(item.id)}>{t(item.key)}</button>)}</div>}{!menuOpen && <div className={styles.menuComponentSentinel} data-component-uid="CORE-01-CMP-MESSAGE-MENU" aria-hidden="true" />}</div></section>
          <section className={`${styles.panel} ${styles.decisionPanel}`} data-section-id="CORE-01-SEC-05" data-visual-id="CORE-01-VIS-DECISION"><PanelTitle labelKey="core01.group.decision" /><div className={styles.decisionGrid}><div data-component-uid="CORE-01-CMP-SUMMARY"><ReadonlyField id="CORE-01-FLD-ASSISTANT-SUMMARY" labelKey="core01.control.assistant_summary" /></div><div data-component-uid="CORE-01-CMP-EVALUATION"><ReadonlyField id="CORE-01-FLD-EVALUATION" labelKey="core01.control.evaluation" /></div><div className={styles.humanDecision} data-component-uid="CORE-01-CMP-HUMAN-DECISION"><label className={styles.textareaField}><span>{t("core01.control.human_decision")}</span><textarea data-control-id="CORE-01-FLD-HUMAN-DECISION" data-action-uid={actionUid("CORE-01-FLD-HUMAN-DECISION")} value={humanDecision} onChange={(event) => setHumanDecision(event.target.value)} aria-label={t("core01.control.human_decision")} /></label><ReadonlyField id="CORE-01-FLD-STRUCTURED-DECISION" labelKey="core01.control.structured_decision" /><div className={styles.actionRow}><ActionButton id="CORE-01-BTN-CANDIDATE-CREATE" labelKey="core01.control.create_candidate" primary disabled={isBusy} onClick={() => runControl("CORE-01-BTN-CANDIDATE-CREATE")} /><ActionButton id="CORE-01-BTN-CANDIDATE-CONFIRM" labelKey="core01.control.confirm_candidate" primary disabled={isBusy} onClick={() => runControl("CORE-01-BTN-CANDIDATE-CONFIRM")} /><ActionButton id="CORE-01-BTN-RETURN-MODIFY" labelKey="core01.control.return_modify" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-RETURN-MODIFY")} /></div></div></div></section>
          <section className={styles.runtimeStrip} data-section-id="CORE-01-SEC-06" data-visual-id="CORE-01-VIS-RUNTIME"><div className={styles.runtimeComponent} data-component-uid="CORE-01-CMP-RUNTIME" data-control-id="CORE-01-FLD-RUNTIME-STAGE" data-action-uid={actionUid("CORE-01-FLD-RUNTIME-STAGE")}><span>{t("core01.control.runtime_stage")}</span><strong>{runtimeDisplay}</strong></div></section>
          <section className={`${styles.panel} ${styles.composerPanel}`} data-section-id="CORE-01-SEC-07" data-visual-id="CORE-01-VIS-COMPOSER"><div className={styles.composer} data-component-uid="CORE-01-CMP-COMPOSER"><div className={styles.composerTools}><ActionButton id="CORE-01-BTN-ATTACHMENT" labelKey="core01.control.attachment" compact disabled={isBusy} onClick={() => runControl("CORE-01-BTN-ATTACHMENT")} /><ActionButton id="CORE-01-BTN-REFERENCE" labelKey="core01.control.reference" compact disabled={isBusy} onClick={() => runControl("CORE-01-BTN-REFERENCE")} /></div><textarea data-control-id="CORE-01-FLD-MESSAGE" data-action-uid={actionUid("CORE-01-FLD-MESSAGE")} aria-label={t("core01.control.message")} placeholder={t("core01.control.message")} value={message} onChange={(event) => setMessage(event.target.value)} /><ActionButton id="CORE-01-BTN-SEND" labelKey="core01.control.send" primary disabled={isBusy} onClick={() => runControl("CORE-01-BTN-SEND")} /></div></section>
        </main>

        <aside className={styles.rightRail}>
          <section className={styles.panel} data-section-id="CORE-01-SEC-08" data-visual-id="CORE-01-VIS-RIGHT-CORE"><div className={styles.stateBlock} data-component-uid="CORE-01-CMP-PROJECT-STATE"><PanelTitle labelKey="core01.group.project_core_state" /><div className={styles.stateValue}>—</div><div className={styles.stackActions}><ActionButton id="CORE-01-BTN-PROJECT-VALIDATE" labelKey="core01.control.project_validate" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-PROJECT-VALIDATE")} /><ActionButton id="CORE-01-BTN-PROJECT-CONFIRM" labelKey="core01.control.project_confirm" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-PROJECT-CONFIRM")} /><ActionButton id="CORE-01-BTN-STORY-CANDIDATE" labelKey="core01.control.story_candidate" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-STORY-CANDIDATE")} /><ActionButton id="CORE-01-BTN-DNA-LOCK" labelKey="core01.control.dna_lock" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-DNA-LOCK")} /><ActionButton id="CORE-01-BTN-CORE-REVIEW" labelKey="core01.control.core_review" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-CORE-REVIEW")} /><ActionButton id="CORE-01-BTN-PROJECT-LOCK" labelKey="core01.control.project_lock" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-PROJECT-LOCK")} /></div></div><div className={styles.divider} /><div className={styles.stateBlock} data-component-uid="CORE-01-CMP-BLUEPRINT-STATE"><PanelTitle labelKey="core01.group.blueprint_state" /><div className={styles.stateValue}>—</div><div className={styles.stackActions}><ActionButton id="CORE-01-BTN-BLUEPRINT-CREATE" labelKey="core01.control.blueprint_create" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-BLUEPRINT-CREATE")} /><ActionButton id="CORE-01-BTN-BLUEPRINT-VALIDATE" labelKey="core01.control.blueprint_validate" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-BLUEPRINT-VALIDATE")} /><ActionButton id="CORE-01-BTN-BLUEPRINT-APPROVE" labelKey="core01.control.blueprint_approve" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-BLUEPRINT-APPROVE")} /><ActionButton id="CORE-01-BTN-CHILD-LOCK" labelKey="core01.control.child_lock" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-CHILD-LOCK")} /></div></div></section>
          <section className={styles.panel} data-section-id="CORE-01-SEC-09" data-visual-id="CORE-01-VIS-RIGHT-TOPIC"><div data-component-uid="CORE-01-CMP-TOPIC-PACKAGE"><PanelTitle labelKey="core01.group.topic_package" /><ReadonlyField id="CORE-01-FLD-TOPIC-SCOPE" labelKey="core01.control.topic_scope" /><ActionButton id="CORE-01-BTN-CANONICAL-SCRIPT" labelKey="core01.control.canonical_script" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-CANONICAL-SCRIPT")} /><ReadonlyField id="CORE-01-FLD-PACKAGE" labelKey="core01.control.package" /></div><div className={styles.divider} /><div data-component-uid="CORE-01-CMP-DOWNSTREAM"><PanelTitle labelKey="core01.group.downstream" /><ReadonlyField id="CORE-01-FLD-DOWNSTREAM-ASSET" labelKey="core01.control.downstream_asset" /><ReadonlyField id="CORE-01-FLD-DOWNSTREAM-VIDEO" labelKey="core01.control.downstream_video" /><ReadonlyField id="CORE-01-FLD-DOWNSTREAM-EDIT" labelKey="core01.control.downstream_edit" /></div></section>
          <section className={styles.panel} data-section-id="CORE-01-SEC-10" data-visual-id="CORE-01-VIS-RIGHT-VERSION"><div data-component-uid="CORE-01-CMP-VERSION"><PanelTitle labelKey="core01.group.version" /><ActionButton id="CORE-01-BTN-CANDIDATE-COMPARE" labelKey="core01.control.candidate_compare" disabled={isBusy} onClick={() => runControl("CORE-01-BTN-CANDIDATE-COMPARE")} /><ReadonlyField id="CORE-01-FLD-VERSION-STATE" labelKey="core01.control.version_state" /></div><div className={styles.divider} /><div data-component-uid="CORE-01-CMP-LOCK-REVIEW"><PanelTitle labelKey="core01.group.lock_review" /><ReadonlyField id="CORE-01-FLD-LOCK-REVIEW" labelKey="core01.control.lock_review" /></div></section>
        </aside>
      </div>
    </div>
  );
}
