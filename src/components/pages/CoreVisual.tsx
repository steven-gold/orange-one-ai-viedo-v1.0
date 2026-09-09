"use client";

import { useEffect, useReducer, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { invokeCoreAction, readCoreProjection } from "@/domain/core/coreClientPort";
import { requestCoreDraftFormPayload } from "@/domain/core/coreDraftFormAdapter";
import { requestCoreCreationPermission } from "@/domain/core/coreCreationPermissionAdapter";
import { requestCoreMessageSendPayload, requestCoreThreadCreatePayload } from "@/domain/core/coreConversationPayloadAdapter";
import { requestCoreCandidateCreatePayload, requestCoreCandidateDecisionPayload } from "@/domain/core/coreCandidatePayloadAdapter";
import { requestCoreLockCommandPayload, type CoreLockCommandKind } from "@/domain/core/coreLockCommandPayloadAdapter";
import { requestCoreComposerResource } from "@/domain/core/coreComposerResourceAdapter";
import { resolveCoreProjection, type CoreNormalizedProjection } from "@/domain/core/coreProjectionAdapter";
import { INITIAL_CORE_CLIENT_STATE, reduceCoreClientState } from "@/domain/core/coreClientState";
import type { CoreActionUid } from "@/domain/core/coreRuntimeContract";
import styles from "./CoreVisual.module.css";

type LabelKey = TranslationKey;
type PageState = "LOADING" | "READY" | "ERROR";
type ConversationUiMessage = { id: string; role: "USER" | "STATUS" | "SYSTEM" | "ASSISTANT" | "SIMULATED_AI"; text: string };
type ControlProps = { id: string; labelKey: LabelKey; primary?: boolean; compact?: boolean; disabled?: boolean; disabledReason?: string; onClick?: () => void };

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
function ActionButton({ id, labelKey, primary = false, compact = false, disabled = false, disabledReason, onClick }: ControlProps) {
  const { t } = useI18n();
  return <button type="button" disabled={disabled} onClick={onClick} data-control-id={id} data-action-uid={actionUid(id)} data-runtime-binding={disabled ? "BLOCKED" : "ACTION_BOUND"} data-disabled-reason={disabled ? disabledReason ?? "GATE_NOT_SATISFIED" : undefined} className={`${styles.button} ${primary ? styles.primaryButton : ""} ${compact ? styles.compactButton : ""}`}>{t(labelKey)}</button>;
}
function ReadonlyField({ id, labelKey, value = "—" }: ControlProps & { value?: string }) {
  const { t } = useI18n();
  return <div className={styles.readonlyField} data-control-id={id} data-action-uid={actionUid(id)}><span className={styles.fieldLabel}>{t(labelKey)}</span><span className={styles.fieldValue}>{value}</span></div>;
}
function SelectionList({ id, labelKey, value, options, onChange, disabled = false, disabledReason }: ControlProps & { value: string; options: readonly { value: string; label: string }[]; onChange: (value: string) => void }) {
  const { t } = useI18n();
  return <label className={styles.listControl} data-control-id={id} data-action-uid={actionUid(id)} data-disabled-reason={disabled ? disabledReason ?? "GATE_NOT_SATISFIED" : undefined}><div className={styles.subheading}>{t(labelKey)}</div><select value={value} disabled={disabled} data-disabled-reason={disabled ? disabledReason ?? "GATE_NOT_SATISFIED" : undefined} onChange={(event) => onChange(event.target.value)} aria-label={t(labelKey)}><option value="">—</option>{options.map((item) => <option key={`${item.value}:${item.label}`} value={item.value}>{item.label}</option>)}</select></label>;
}
function PanelTitle({ labelKey }: { labelKey: LabelKey }) { const { t } = useI18n(); return <h2 className={styles.panelTitle}>{t(labelKey)}</h2>; }

const PROJECT_CORE_WORK_ITEMS = new Set(["STORY","CHAPTER","WORLD_SETTING","DNA","BLUEPRINT"]);
const TOPIC_PRODUCTION_WORK_ITEMS = new Set(["TOPIC_SCOPE","PRODUCTION_SCRIPT"]);

const MESSAGE_MENU: readonly { id: string; key: LabelKey }[] = [
  { id: "CORE-01-MENU-QUOTE", key: "core01.control.quote" }, { id: "CORE-01-MENU-CONTINUE", key: "core01.control.continue" },
  { id: "CORE-01-MENU-ANALYZE", key: "core01.control.analyze" }, { id: "CORE-01-MENU-DECISION", key: "core01.control.decision_list" },
  { id: "CORE-01-MENU-BRANCH", key: "core01.control.branch" }, { id: "CORE-01-MENU-COPY", key: "core01.control.copy" },
] as const;

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function text(value: unknown): string | null { return typeof value === "string" && value.trim() ? value.trim() : null; }
function mentionTokens(value: string): string[] { return Array.from(new Set(value.match(/@[^\s@]+/g) ?? [])); }

async function copyVisibleText(value: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch { /* use local fallback */ }
  try {
    const node = document.createElement("textarea");
    node.value = value;
    node.setAttribute("readonly", "true");
    node.style.position = "fixed";
    node.style.opacity = "0";
    document.body.appendChild(node);
    node.select();
    const copied = document.execCommand("copy");
    node.remove();
    return copied;
  } catch {
    return false;
  }
}

export function CoreVisual() {
  const { t } = useI18n();
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [contextMessageId, setContextMessageId] = useState<string | null>(null);
  const [pageState, setPageState] = useState<PageState>("LOADING");
  const [runtimeReason, setRuntimeReason] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<CoreActionUid | null>(null);
  const [message, setMessage] = useState("");
  const [conversationMessages, setConversationMessages] = useState<ConversationUiMessage[]>([]);
  const [humanDecision, setHumanDecision] = useState("");
  const [lockDialog, setLockDialog] = useState<"MOTHER_LOCK" | "CHILD_LOCK" | null>(null);
  const [lockRequestReason, setLockRequestReason] = useState("");
  const [lockCriteriaVersionId, setLockCriteriaVersionId] = useState("");
  const [lockCorrelationId, setLockCorrelationId] = useState("");
  const [lockIdempotencyKey, setLockIdempotencyKey] = useState("");
  const [clientState, dispatchClient] = useReducer(reduceCoreClientState, INITIAL_CORE_CLIENT_STATE);
  const [projection, setProjection] = useState<CoreNormalizedProjection | null>(null);

  const display = (key: string) => projection?.display_values[key] ?? "—";
  const messagesForThread = (source: CoreNormalizedProjection | null, conversationId: string | null | undefined): ConversationUiMessage[] => {
    if (!source || !conversationId) return [];
    return (source.messages_by_thread?.[conversationId] ?? []).map((entry) => ({
      id: entry.message_ref,
      role: entry.role,
      text: entry.text,
    }));
  };
  const applyRawProjection = async (rawProjection: unknown) => {
    const resolved = await resolveCoreProjection(rawProjection);
    if (!resolved.ok) {
      setProjection(null);
      setPageState("ERROR");
      setRuntimeReason(`CORE-01-ERR-CONTEXT-001:${resolved.reason_code}`);
      return false;
    }
    setProjection(resolved.projection);
    dispatchClient({ type: "CORE_INTERNAL_PROJECTION_SYNC", refs: resolved.projection.refs, work_item: resolved.projection.work_item });
    setConversationMessages(messagesForThread(resolved.projection, resolved.projection.refs.conversation_id));
    setPageState("READY");
    setRuntimeReason(null);
    return true;
  };

  const syncProjection = async () => {
    const projectionResult = await readCoreProjection();
    if (!projectionResult.ok) {
      setProjection(null);
      setPageState("ERROR");
      setRuntimeReason(`${projectionResult.error_uid}:${projectionResult.reason_code}`);
      return false;
    }
    return applyRawProjection(projectionResult.value);
  };

  useEffect(() => {
    const controller = new AbortController();
    void readCoreProjection(controller.signal).then(async (result) => {
      if (controller.signal.aborted) return;
      if (!result.ok) { setProjection(null); setPageState("ERROR"); setRuntimeReason(`${result.error_uid}:${result.reason_code}`); return; }
      await applyRawProjection(result.value);
    });
    return () => controller.abort();
  }, []);

  const reportBlock = (reason: string) => { setPageState("ERROR"); setRuntimeReason(reason); };
  const reportLocalSuccess = (reason: string) => { setPageState("READY"); setRuntimeReason(reason); };
  const appendConversationMessage = (role: ConversationUiMessage["role"], textValue: string, exactId?: string) => {
    const id = exactId ?? crypto.randomUUID();
    setConversationMessages((current) => [...current, { id, role, text: textValue }]);
    return id;
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
  const runServerActionAndSync = async (action_uid: CoreActionUid, options: { path_params?: Record<string, string>; query?: Record<string, string>; payload?: unknown } = {}) => {
    const result = await runServerAction(action_uid, options);
    if (result?.ok) await syncProjection();
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
    const permission = await requestCoreCreationPermission({ kind });
    if (!permission.allowed) {
      reportBlock(`CORE-01-ERR-PERM-001:${permission.reason_code}:${permission.required_permission_uid}`);
      return;
    }
    const projectId = kind === "TOPIC" ? requireProjectId() : null;
    if (kind === "TOPIC" && !projectId) return;
    const form = await requestCoreDraftFormPayload(kind === "PROJECT" ? { kind } : { kind, project_id: projectId! });
    if (!form.ok) {
      reportBlock(`${kind === "PROJECT" ? "CORE-01-ERR-CONTEXT-001" : "CORE-01-ERR-TOPIC-LINEAGE-001"}:${form.reason_code}`);
      return;
    }
    await runServerActionAndSync(action, kind === "PROJECT"
      ? { payload: form.payload }
      : { path_params: { projectId: projectId! }, payload: form.payload });
  };

  const openLockDialog = (kind: "MOTHER_LOCK" | "CHILD_LOCK") => {
    setLockDialog(kind);
    setLockRequestReason("");
    setLockCriteriaVersionId("");
    setLockCorrelationId(crypto.randomUUID());
    setLockIdempotencyKey(`lock-${crypto.randomUUID()}`);
  };
  const closeLockDialog = () => {
    if (busyAction) return;
    setLockDialog(null);
    setLockRequestReason("");
    setLockCriteriaVersionId("");
    setLockCorrelationId("");
    setLockIdempotencyKey("");
  };
  const runLockCommand = async (action: CoreActionUid, kind: CoreLockCommandKind) => {
    if (kind === "DNA_LOCK" && !requireDnaVersionRef()) return;
    if (kind === "CORE_REVIEW" && !requireProjectVersionRef()) return;
    const selectedProject=projection?.projects.find(item=>item.project_id===clientState.project_id)??null;
    const selectedTopic=projection?.topics.find(item=>item.topic_id===clientState.topic_id&&item.project_id===clientState.project_id)??null;
    const targetRef=kind==="MOTHER_LOCK"?selectedProject?.project_version_ref??null:kind==="CHILD_LOCK"?selectedTopic?.blueprint_version_ref??null:null;
    const expectedVersionNo=kind==="MOTHER_LOCK"?selectedProject?.project_version_no??null:kind==="CHILD_LOCK"?selectedTopic?.blueprint_version_no??null:null;
    const payload = await requestCoreLockCommandPayload({
      kind,project_id:clientState.project_id,project_version_ref:clientState.project_version_ref,
      dna_version_ref:clientState.dna_version_ref,blueprint_version_ref:clientState.blueprint_version_ref,
      topic_id:clientState.topic_id,evidence_refs:clientState.decision_evidence_refs,
      workspace_id:selectedProject?.workspace_id??null,target_ref:targetRef,expected_version_no:expectedVersionNo,
      request_reason:lockRequestReason,criteria_version_id:lockCriteriaVersionId,
      correlation_id:lockCorrelationId,idempotency_key:lockIdempotencyKey,
    });
    if (!payload.ok) {
      const error = kind === "DNA_LOCK" ? "CORE-01-ERR-DNA-LOCK-001" : kind === "CORE_REVIEW" ? "CORE-01-ERR-CONTEXT-001" : "CORE-01-ERR-LOCK-CONTRACT-001";
      reportBlock(`${error}:${payload.reason_code}`);
      return;
    }
    const result=await runServerActionAndSync(action,{payload:payload.payload});
    if(result?.ok&&(kind==="MOTHER_LOCK"||kind==="CHILD_LOCK"))closeLockDialog();
  };
  const submitLockDialog = () => {
    if(lockDialog==="MOTHER_LOCK")void runLockCommand("CORE-01-ACT-MOTHER-LOCK-REQUEST","MOTHER_LOCK");
    else if(lockDialog==="CHILD_LOCK")void runLockCommand("CORE-01-ACT-CHILD-LOCK-REQUEST","CHILD_LOCK");
  };

  const runComposerResource = async (kind: "ATTACHMENT" | "REFERENCE") => {
    const conversationId = requireConversationId();
    if (!conversationId) return;
    const selected = await requestCoreComposerResource({ kind, conversation_id: conversationId });
    if (!selected.ok) {
      reportBlock(`CORE-01-ERR-UNDEFINED-001:${selected.reason_code}`);
      return;
    }
    if (kind === "ATTACHMENT") dispatchClient({ action_uid: "CORE-01-ACT-ATTACHMENT", attachment_ref: selected.ref });
    else dispatchClient({ action_uid: "CORE-01-ACT-REFERENCE-ATTACH", reference_ref: selected.ref });
    reportLocalSuccess(`${kind}_ATTACHED:${selected.ref}`);
    composerRef.current?.focus();
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
          const result = await runServerAction(action, { path_params: { projectId }, payload: payload.payload });
          if (!result?.ok) return;
          const created = text(asRecord(result.value).conversation_id);
          if (!created) { reportBlock("CORE-01-ERR-THREAD-001:CONVERSATION_THREAD_REF_MISSING"); return; }
          await syncProjection();
          dispatchClient({ action_uid: "CORE-01-ACT-THREAD-SELECT", thread_ref: created, conversation_id: created });
          setConversationMessages([]);
        })(); return;
      }
      case "CORE-01-ACT-AI-MODE-SINGLE": {
        if (!requireWorkItem()) return;
        dispatchClient({ action_uid: action });
        reportLocalSuccess("AI_MODE=SINGLE");
        return;
      }
      case "CORE-01-ACT-AI-MODE-MULTI": {
        if (!requireWorkItem()) return;
        if (display("assigned_ai_set") === "—") { reportBlock("CORE-01-ERR-AI-ROUTE-001:ASSIGNED_AI_SET_REQUIRED"); return; }
        dispatchClient({ action_uid: action });
        reportLocalSuccess("AI_MODE=MULTI");
        return;
      }
      case "CORE-01-ACT-ASSISTANT-RECORD":
        dispatchClient({ action_uid: action, open: !clientState.assistant_record_open });
        reportLocalSuccess(clientState.assistant_record_open ? "ASSISTANT_RECORD_CLOSED" : "ASSISTANT_RECORD_OPEN");
        return;
      case "CORE-01-ACT-SEND": {
        const submitted = message.trim();
        if (!submitted) { reportBlock("CORE-01-ERR-CONVERSATION-001:MESSAGE_REQUIRED"); return; }
        const conversationId = requireConversationId();
        if (!conversationId) return;
        void (async () => {
          const payload = await requestCoreMessageSendPayload({ conversation_id: conversationId, message: submitted, ai_mode: clientState.ai_mode, attachment_refs: clientState.attachment_refs, reference_refs: clientState.reference_refs, mention_tokens: mentionTokens(submitted) });
          if (!payload.ok) { reportBlock(`CORE-01-ERR-CONVERSATION-001:${payload.reason_code}`); return; }
          const result = await runServerAction(action, { path_params: { conversationId }, payload: payload.payload });
          if (!result) return;
          if (result.ok) {
            const value = asRecord(result.value);
            appendConversationMessage("USER", submitted, text(value.message_ref) ?? undefined);
            const assistantText = text(value.assistant_response_text);
            const simulatedText = text(value.simulated_response_text);
            if (assistantText) {
              appendConversationMessage("ASSISTANT", assistantText, text(value.assistant_response_ref) ?? undefined);
            } else if (simulatedText) {
              appendConversationMessage("SIMULATED_AI", simulatedText, text(value.simulated_response_ref) ?? undefined);
            }
            setMessage("");
            await syncProjection();
          } else {
            appendConversationMessage("STATUS", `${result.error_uid}:${result.reason_code}`);
          }
        })(); return;
      }
      case "CORE-01-ACT-CANDIDATE-CREATE": {
        const decisionText=humanDecision.trim();
        if (!decisionText) { reportBlock("CORE-01-ERR-DECISION-001:HUMAN_DECISION_REQUIRED"); return; }
        void (async()=>{
          const payload=await requestCoreCandidateCreatePayload({ human_decision:decisionText, evidence_refs:clientState.decision_evidence_refs, project_id:clientState.project_id, topic_id:clientState.topic_id, work_item:clientState.work_item });
          if(!payload.ok){ reportBlock(`CORE-01-ERR-CANDIDATE-001:${payload.reason_code}`); return; }
          await runServerActionAndSync(action,{payload:payload.payload});
        })(); return;
      }
      case "CORE-01-ACT-CANDIDATE-ACCEPT": case "CORE-01-ACT-CANDIDATE-RETURN": {
        const candidateRef=requireCandidateRef(); if(!candidateRef)return;
        const decisionText=humanDecision.trim();
        void (async()=>{
          const payload=await requestCoreCandidateDecisionPayload({ candidate_ref:candidateRef, decision:action==="CORE-01-ACT-CANDIDATE-ACCEPT"?"ACCEPT":"RETURN", reason_text:decisionText, evidence_refs:clientState.decision_evidence_refs });
          if(!payload.ok){ reportBlock(`CORE-01-ERR-DECISION-001:${payload.reason_code}`); return; }
          await runServerActionAndSync(action,{path_params:{id:candidateRef},payload:payload.payload});
        })(); return;
      }
      case "CORE-01-ACT-CANDIDATE-COMPARE": {
        const candidateRef = requireCandidateRef(); if (!candidateRef) return;
        void runServerActionAndSync(action, { query: { candidate_refs: candidateRef } });
        return;
      }
      case "CORE-01-ACT-PROJECT-VALIDATE": { const projectVersionId = requireProjectVersionRef(); if (projectVersionId) void runServerActionAndSync(action, { path_params: { projectVersionId } }); return; }
      case "CORE-01-ACT-PROJECT-CONFIRM": { const projectVersionRef = requireProjectVersionRef(); if (projectVersionRef) void runServerActionAndSync(action, { path_params: { id: projectVersionRef } }); return; }
      case "CORE-01-ACT-STORY-CANDIDATE": { const projectId = requireProjectId(); if (projectId) void runServerActionAndSync(action, { path_params: { projectId } }); return; }
      case "CORE-01-ACT-DNA-LOCK-REQUEST": void runLockCommand(action,"DNA_LOCK"); return;
      case "CORE-01-ACT-CORE-REVIEW-SUBMIT": void runLockCommand(action,"CORE_REVIEW"); return;
      case "CORE-01-ACT-MOTHER-LOCK-REQUEST": openLockDialog("MOTHER_LOCK"); return;
      case "CORE-01-ACT-CHILD-LOCK-REQUEST": openLockDialog("CHILD_LOCK"); return;
      case "CORE-01-ACT-BLUEPRINT-CREATE": { const topicId = requireTopicId(); if (topicId) void runServerActionAndSync(action, { path_params: { id: topicId } }); return; }
      case "CORE-01-ACT-BLUEPRINT-VALIDATE": case "CORE-01-ACT-BLUEPRINT-APPROVE": { const blueprintVersionRef = requireBlueprintVersionRef(); if (blueprintVersionRef) void runServerActionAndSync(action, { path_params: { id: blueprintVersionRef } }); return; }
      case "CORE-01-ACT-CANONICAL-SCRIPT-VIEW": { const topicId = requireTopicId(); if (topicId) void runServerActionAndSync(action, { path_params: { id: topicId } }); return; }
      case "CORE-01-ACT-ATTACHMENT": void runComposerResource("ATTACHMENT"); return;
      case "CORE-01-ACT-REFERENCE-ATTACH": void runComposerResource("REFERENCE"); return;
      default: reportBlock("CORE-01-ERR-UNDEFINED-001:ACTION_REQUIRES_EXACT_RUNTIME_CONTEXT");
    }
  };

  const selectProject = (projectId: string) => {
    setConversationMessages([]); setContextMessageId(null); setMenuOpen(false);
    if (!projectId) { dispatchClient({ action_uid: "CORE-01-ACT-PROJECT-SELECT", project_ref: null, project_id: null, project_version_ref: null }); return; }
    const matches = projection?.projects.filter((item) => item.project_id === projectId) ?? [];
    if (matches.length !== 1) { reportBlock("CORE-01-ERR-CONTEXT-001:PROJECT_PROJECTION_SELECTION_AMBIGUOUS"); return; }
    const selected = matches[0];
    dispatchClient({ action_uid: "CORE-01-ACT-PROJECT-SELECT", project_ref: selected.project_id, project_id: selected.project_id, project_version_ref: selected.project_version_ref });
    reportLocalSuccess(`PROJECT_SELECTED:${selected.project_id}`);
  };
  const selectTopic = (topicId: string) => {
    setConversationMessages([]); setContextMessageId(null); setMenuOpen(false);
    if (!topicId) { dispatchClient({ action_uid: "CORE-01-ACT-TOPIC-SELECT", topic_ref: null, topic_id: null, topic_version_ref: null }); return; }
    const matches = projection?.topics.filter((item) => item.topic_id === topicId && item.project_id === clientState.project_id) ?? [];
    if (matches.length !== 1) { reportBlock("CORE-01-ERR-TOPIC-LINEAGE-001:TOPIC_PROJECTION_SELECTION_AMBIGUOUS"); return; }
    const selected = matches[0];
    dispatchClient({ action_uid: "CORE-01-ACT-TOPIC-SELECT", topic_ref: selected.topic_id, topic_id: selected.topic_id, topic_version_ref: selected.topic_version_ref, blueprint_version_ref: selected.blueprint_version_ref });
    reportLocalSuccess(`TOPIC_SELECTED:${selected.topic_id}`);
  };
  const selectWorkItem = (workItem: string) => {
    const modeSet = clientState.topic_id ? TOPIC_PRODUCTION_WORK_ITEMS : PROJECT_CORE_WORK_ITEMS;
    const registered = projection?.work_items.some((item) => item.work_item === workItem) ?? false;
    if (workItem && (!registered || !modeSet.has(workItem))) { reportBlock("CORE-01-ERR-WORK-ITEM-001:WORK_ITEM_NOT_ALLOWED_IN_CURRENT_MODE"); return; }
    dispatchClient({ action_uid: "CORE-01-ACT-WORK-ITEM-SELECT", work_item: workItem || null });
    setConversationMessages([]); setContextMessageId(null); setMenuOpen(false);
    reportLocalSuccess(workItem ? `WORK_ITEM_SELECTED:${workItem}` : "WORK_ITEM_CLEARED");
  };
  const selectThread = (conversationId: string) => {
    if (conversationId) {
      const matches = projection?.threads.filter((item) =>
        item.conversation_id === conversationId
        && item.project_id === clientState.project_id
        && item.work_item === clientState.work_item
        && (clientState.topic_id ? item.topic_id === clientState.topic_id : item.topic_id === null)
      ) ?? [];
      if (matches.length !== 1) { reportBlock("CORE-01-ERR-THREAD-001:THREAD_NOT_IN_CURRENT_CONTEXT"); return; }
    }
    dispatchClient({ action_uid: "CORE-01-ACT-THREAD-SELECT", thread_ref: conversationId || null, conversation_id: conversationId || null });
    setConversationMessages(messagesForThread(projection, conversationId || null)); setContextMessageId(null); setMenuOpen(false);
    reportLocalSuccess(conversationId ? `THREAD_SELECTED:${conversationId}` : "THREAD_CLEARED");
  };

  const openContextMenu = (event: ReactMouseEvent<HTMLDivElement>, messageId: string) => {
    event.preventDefault();
    event.stopPropagation();
    setContextMessageId(messageId);
    setMenuOpen(true);
  };

  const runMessageMenu = (id: string) => {
    const action = actionUid(id);
    const conversationId = requireConversationId();
    if (!conversationId) return;
    const selected = conversationMessages.find((entry) => entry.id === contextMessageId);
    if (!selected) { reportBlock("CORE-01-ERR-THREAD-001:EXACT_MESSAGE_REF_REQUIRED"); return; }
    setMenuOpen(false);

    switch (action) {
      case "CORE-01-ACT-MSG-QUOTE":
        dispatchClient({ action_uid: action, message_ref: selected.id });
        reportLocalSuccess(`MESSAGE_QUOTED:${selected.id}`);
        composerRef.current?.focus();
        return;
      case "CORE-01-ACT-MSG-CONTINUE":
        dispatchClient({ action_uid: action, message_ref: selected.id });
        reportLocalSuccess(`MESSAGE_CONTEXT_CONTINUED:${selected.id}`);
        composerRef.current?.focus();
        return;
      case "CORE-01-ACT-MSG-DECISION":
        dispatchClient({ action_uid: action, message_ref: selected.id });
        reportLocalSuccess(`DECISION_EVIDENCE_ADDED:${selected.id}`);
        return;
      case "CORE-01-ACT-MSG-COPY":
        void (async () => {
          if (await copyVisibleText(selected.text)) reportLocalSuccess(`MESSAGE_COPIED:${selected.id}`);
          else reportBlock("CORE-01-ERR-THREAD-001:CLIPBOARD_WRITE_FAILED");
        })();
        return;
      case "CORE-01-ACT-MSG-ANALYZE":
        void (async () => {
          const payload = await requestCoreMessageSendPayload({ conversation_id: conversationId, message: "ANALYZE_EXACT_SOURCE_MESSAGE", ai_mode: clientState.ai_mode, attachment_refs: clientState.attachment_refs, reference_refs: clientState.reference_refs, source_message_id: selected.id, instruction_kind: "ANALYZE" });
          if (!payload.ok) { reportBlock(`CORE-01-ERR-CONVERSATION-001:${payload.reason_code}`); return; }
          const result = await runServerAction(action, { path_params: { conversationId }, payload: payload.payload });
          if (result?.ok) {
            const value = asRecord(result.value);
            const assistantText = text(value.assistant_response_text);
            const simulatedText = text(value.simulated_response_text);
            if (assistantText) {
              appendConversationMessage("ASSISTANT", assistantText, text(value.assistant_response_ref) ?? undefined);
            } else if (simulatedText) {
              appendConversationMessage("SIMULATED_AI", simulatedText, text(value.simulated_response_ref) ?? undefined);
            }
            await syncProjection();
          }
        })();
        return;
      case "CORE-01-ACT-MSG-BRANCH": {
        const projectId = requireProjectId(); if (!projectId) return;
        const workItem = requireWorkItem(); if (!workItem) return;
        void (async () => {
          const payload = await requestCoreThreadCreatePayload({ project_id: projectId, topic_id: clientState.topic_id, work_item: workItem, ai_mode: clientState.ai_mode, parent_conversation_id: conversationId, source_message_id: selected.id, relation_kind: "BRANCH" });
          if (!payload.ok) { reportBlock(`CORE-01-ERR-THREAD-001:${payload.reason_code}`); return; }
          const result = await runServerAction(action, { path_params: { projectId }, payload: payload.payload });
          if (!result?.ok) return;
          const created = text(asRecord(result.value).conversation_id);
          if (!created) { reportBlock("CORE-01-ERR-THREAD-001:CONVERSATION_THREAD_REF_MISSING"); return; }
          await syncProjection();
          dispatchClient({ action_uid: "CORE-01-ACT-THREAD-SELECT", thread_ref: created, conversation_id: created });
          setConversationMessages([]);
        })();
        return;
      }
      default:
        reportBlock("CORE-01-ERR-UNDEFINED-001:MESSAGE_ACTION_NOT_REGISTERED");
    }
  };

  const runtimeDisplay = runtimeReason?.startsWith("CORE-01-ERR-PERM-001:") ? `${t("core01.notice.creation_permission_denied")} (${runtimeReason.split(":").slice(1).join(":")})` : runtimeReason ?? display("runtime_stage");
  const candidateReady = display("story_candidate_set") !== "—";
  const coreStage = !clientState.conversation_id ? 1 : conversationMessages.length === 0 ? 2 : !humanDecision.trim() ? 3 : !candidateReady ? 4 : 5;
  const stageMeta = coreStage === 1
    ? { control: "CORE-01-BTN-NEW-THREAD", key: "core01.control.new_thread" as LabelKey }
    : coreStage === 2
      ? { control: "CORE-01-BTN-SEND", key: "core01.control.send" as LabelKey }
      : coreStage === 3
        ? { control: "CORE-01-FLD-HUMAN-DECISION", key: "core01.control.human_decision" as LabelKey }
        : coreStage === 4
          ? { control: "CORE-01-BTN-CANDIDATE-CREATE", key: "core01.control.create_candidate" as LabelKey }
          : { control: "CORE-01-BTN-CANDIDATE-CONFIRM", key: "core01.control.confirm_candidate" as LabelKey };
  const isBusy = busyAction !== null;
  const visibleTopics = (projection?.topics ?? []).filter((item) => item.project_id === clientState.project_id);
  const activeWorkItems = (projection?.work_items ?? []).filter((item) =>
    (clientState.topic_id ? TOPIC_PRODUCTION_WORK_ITEMS : PROJECT_CORE_WORK_ITEMS).has(item.work_item)
  );
  const visibleThreads = (projection?.threads ?? []).filter((item) =>
    item.project_id === clientState.project_id
    && item.work_item === clientState.work_item
    && (clientState.topic_id ? item.topic_id === clientState.topic_id : item.topic_id === null)
  );

  const coreControlDisabledReason = (id: string): string | null => {
    if (isBusy) return `BUSY:${busyAction}`;
    const project = Boolean(clientState.project_id);
    const projectVersion = Boolean(clientState.project_version_ref);
    const topic = Boolean(clientState.topic_id);
    const workItem = Boolean(clientState.work_item);
    const thread = Boolean(clientState.conversation_id);
    const candidate = Boolean(clientState.candidate_ref);
    const blueprint = Boolean(clientState.blueprint_version_ref);
    const dna = Boolean(clientState.dna_version_ref);
    const selectedProject=projection?.projects.find(item=>item.project_id===clientState.project_id)??null;
    const selectedTopic=projection?.topics.find(item=>item.topic_id===clientState.topic_id&&item.project_id===clientState.project_id)??null;
    const criteriaReady=(projection?.lock_context.approved_criteria.length??0)>0;
    const reviewerReady=(projection?.lock_context.eligible_reviewer_count??0)>0;
    const evidenceReady=clientState.decision_evidence_refs.length>0;
    const lockPrerequisite=(targetReady:boolean,versionReady:boolean):string|null=>{
      if(!targetReady)return "LOCK_TARGET_NOT_READY";
      if(!versionReady)return "EXPECTED_VERSION_INVALID";
      if(!criteriaReady)return "LOCK_CRITERIA_VERSION_REQUIRED";
      if(!evidenceReady)return "LOCK_EVIDENCE_REQUIRED";
      if(!reviewerReady)return "CORE_LOCK_REVIEWER_PATH_UNRESOLVED";
      return null;
    };
    switch (id) {
      case "CORE-01-BTN-PROJECT-CREATE": return null;
      case "CORE-01-BTN-TOPIC-CREATE": return project && projectVersion ? null : "PROJECT_VERSION_REQUIRED";
      case "CORE-01-BTN-NEW-THREAD": return project && workItem ? null : "PROJECT_AND_WORK_ITEM_REQUIRED";
      case "CORE-01-BTN-SINGLE-AI": return workItem ? null : "WORK_ITEM_REQUIRED";
      case "CORE-01-BTN-MULTI-AI": return !workItem ? "WORK_ITEM_REQUIRED" : display("assigned_ai_set") === "—" ? "ASSIGNED_AI_SET_REQUIRED" : null;
      case "CORE-01-BTN-ASSISTANT-RECORD": return thread ? null : "CONVERSATION_REQUIRED";
      case "CORE-01-BTN-CANDIDATE-CREATE": return !thread ? "CONVERSATION_REQUIRED" : !humanDecision.trim() ? "HUMAN_DECISION_REQUIRED" : null;
      case "CORE-01-BTN-CANDIDATE-CONFIRM":
      case "CORE-01-BTN-RETURN-MODIFY":
      case "CORE-01-BTN-CANDIDATE-COMPARE": return candidate ? null : "EXACT_CANDIDATE_REF_REQUIRED";
      case "CORE-01-BTN-ATTACHMENT":
      case "CORE-01-BTN-REFERENCE": return thread ? null : "CONVERSATION_REQUIRED";
      case "CORE-01-BTN-SEND": return !thread ? "CONVERSATION_REQUIRED" : !message.trim() ? "MESSAGE_REQUIRED" : null;
      case "CORE-01-BTN-PROJECT-VALIDATE": return projectVersion ? null : "PROJECT_VERSION_REQUIRED";
      case "CORE-01-BTN-PROJECT-CONFIRM": return "PROJECT_CONFIRM_ADOPT_CONTRACT_NOT_BOUND";
      case "CORE-01-BTN-STORY-CANDIDATE": return project ? null : "PROJECT_REQUIRED";
      case "CORE-01-BTN-DNA-LOCK": return dna ? null : "EXACT_DNA_VERSION_REF_REQUIRED";
      case "CORE-01-BTN-CORE-REVIEW": return projectVersion ? null : "PROJECT_VERSION_REQUIRED";
      case "CORE-01-BTN-PROJECT-LOCK": return projectVersion ? lockPrerequisite(selectedProject?.status==="READY_FOR_MOTHER_REVIEW",Boolean(selectedProject?.project_version_no)) : "PROJECT_VERSION_REQUIRED";
      case "CORE-01-BTN-BLUEPRINT-CREATE": return "CORE_BLUEPRINT_DOCUMENT_MATERIALIZER_NOT_BOUND";
      case "CORE-01-BTN-BLUEPRINT-VALIDATE":
      case "CORE-01-BTN-BLUEPRINT-APPROVE": return blueprint ? null : "EXACT_BLUEPRINT_VERSION_REF_REQUIRED";
      case "CORE-01-BTN-CHILD-LOCK": return topic&&blueprint ? lockPrerequisite(selectedTopic?.blueprint_status==="READY_FOR_CHILD_REVIEW",Boolean(selectedTopic?.blueprint_version_no)) : "EXACT_BLUEPRINT_VERSION_REF_REQUIRED";
      case "CORE-01-BTN-CANONICAL-SCRIPT": return topic ? null : "TOPIC_REQUIRED";
      default: return null;
    }
  };
  const GatedAction = (props: ControlProps) => {
    const reason = coreControlDisabledReason(props.id);
    return <ActionButton {...props} disabled={Boolean(reason)} disabledReason={reason ?? undefined} />;
  };

  return (
    <div className={styles.page} data-page-uid="CORE-01" data-vis-step="VIS-02" data-page-state={pageState} data-runtime-reason={runtimeReason ?? undefined} onClick={() => { if (menuOpen) setMenuOpen(false); }}>
      <section className={styles.contextBar} data-section-id="CORE-01-SEC-01" data-visual-id="CORE-01-VIS-CONTEXT"><div className={styles.contextComponent} data-component-uid="CORE-01-CMP-CONTEXT">
        <label className={styles.selectField}><span>{t("core01.control.project")}</span><select value={clientState.project_id ?? ""} disabled={isBusy || (projection?.projects.length ?? 0) === 0} data-disabled-reason={isBusy ? `BUSY:${busyAction}` : (projection?.projects.length ?? 0) === 0 ? "NO_PROJECT_OPTIONS" : undefined} onChange={(event) => selectProject(event.target.value)} data-control-id="CORE-01-CTL-PROJECT" data-action-uid={actionUid("CORE-01-CTL-PROJECT")} aria-label={t("core01.control.project")}><option value="">—</option>{(projection?.projects ?? []).map((item) => <option key={`${item.project_id}:${item.project_version_ref ?? ""}`} value={item.project_id}>{item.label}</option>)}</select></label>
        <GatedAction id="CORE-01-BTN-PROJECT-CREATE" labelKey="core01.control.create_project" primary onClick={() => runControl("CORE-01-BTN-PROJECT-CREATE")} />
        <label className={styles.selectField}><span>{t("core01.control.topic")}</span><select value={clientState.topic_id ?? ""} disabled={isBusy || !clientState.project_id || visibleTopics.length === 0} data-disabled-reason={isBusy ? `BUSY:${busyAction}` : !clientState.project_id ? "PROJECT_REQUIRED" : visibleTopics.length === 0 ? "NO_TOPIC_OPTIONS" : undefined} onChange={(event) => selectTopic(event.target.value)} data-control-id="CORE-01-CTL-TOPIC" data-action-uid={actionUid("CORE-01-CTL-TOPIC")} aria-label={t("core01.control.topic")}><option value="">—</option>{visibleTopics.map((item) => <option key={`${item.topic_id}:${item.topic_version_ref ?? ""}`} value={item.topic_id}>{item.label}</option>)}</select></label>
        <GatedAction id="CORE-01-BTN-TOPIC-CREATE" labelKey="core01.control.create_topic" primary onClick={() => runControl("CORE-01-BTN-TOPIC-CREATE")} />
        <ReadonlyField id="CORE-01-FLD-PAGE-MODE" labelKey="core01.control.page_mode" value={clientState.topic_id ? "TOPIC_PRODUCTION" : "PROJECT_CORE"} /><ReadonlyField id="CORE-01-FLD-NAMING-AUTHORITY" labelKey="core01.control.naming_authority" value="ACPOS_SYSTEM" />
      </div></section>

      <div className={styles.primaryGrid} data-layout="primary-grid" data-layout-grid="workspace-three-column">
        <aside className={styles.leftRail} data-layout-column="left"><section className={styles.panel} data-section-id="CORE-01-SEC-02" data-visual-id="CORE-01-VIS-LEFT">
          <div data-component-uid="CORE-01-CMP-NAV"><SelectionList id="CORE-01-LST-WORK-ITEMS" labelKey="core01.control.work_items" value={clientState.work_item ?? ""} options={activeWorkItems.map((item) => ({ value: item.work_item, label: item.label }))} disabled={isBusy || !clientState.project_id || activeWorkItems.length === 0} disabledReason={isBusy ? `BUSY:${busyAction}` : !clientState.project_id ? "PROJECT_REQUIRED" : "NO_WORK_ITEM_OPTIONS"} onChange={selectWorkItem} /></div><div className={styles.divider} />
          <div data-component-uid="CORE-01-CMP-THREADS"><div className={styles.threadHeader}><PanelTitle labelKey="core01.group.conversation_threads" /><GatedAction id="CORE-01-BTN-NEW-THREAD" labelKey="core01.control.new_thread" compact onClick={() => runControl("CORE-01-BTN-NEW-THREAD")} /></div><div className={styles.threadListScroll}><SelectionList id="CORE-01-LST-THREADS" labelKey="core01.control.threads" value={clientState.conversation_id ?? ""} options={visibleThreads.map((item) => ({ value: item.conversation_id, label: item.label }))} disabled={isBusy || !clientState.work_item || visibleThreads.length === 0} disabledReason={isBusy ? `BUSY:${busyAction}` : !clientState.work_item ? "WORK_ITEM_REQUIRED" : "NO_THREAD_OPTIONS"} onChange={selectThread} /></div></div>
        </section></aside>

        <main className={styles.centerColumn} data-layout-column="center">
          <section className={`${styles.panel} ${styles.conversationHeader}`} data-section-id="CORE-01-SEC-03" data-visual-id="CORE-01-VIS-CENTER-HEADER"><div className={styles.conversationHeaderInner} data-component-uid="CORE-01-CMP-CONV-HEADER"><PanelTitle labelKey="core01.group.conversation" /><div className={styles.aiModeGroup}><GatedAction id="CORE-01-BTN-SINGLE-AI" labelKey="core01.control.single_ai" compact onClick={() => runControl("CORE-01-BTN-SINGLE-AI")} /><GatedAction id="CORE-01-BTN-MULTI-AI" labelKey="core01.control.multi_ai" compact onClick={() => runControl("CORE-01-BTN-MULTI-AI")} /></div><ReadonlyField id="CORE-01-FLD-ASSIGNED-AI" labelKey="core01.control.assigned_ai" value={display("assigned_ai_set")} /><GatedAction id="CORE-01-BTN-ASSISTANT-RECORD" labelKey="core01.control.assistant_record" compact onClick={() => runControl("CORE-01-BTN-ASSISTANT-RECORD")} /></div></section>
          <section className={`${styles.panel} ${styles.messagesPanel}`} data-section-id="CORE-01-SEC-04" data-visual-id="CORE-01-VIS-MESSAGES"><div className={styles.messageWorkspace} data-component-uid="CORE-01-CMP-MESSAGES"><PanelTitle labelKey="core01.group.message_workspace" />{clientState.assistant_record_open && <div className={styles.readonlyField} data-assistant-record-overlay="true"><span className={styles.fieldLabel}>{t("core01.control.assistant_record")}</span><span className={styles.fieldValue}>{display("assistant_summary")} | {display("structured_decision")}</span></div>}{conversationMessages.length ? <div data-conversation-local-log="true">{conversationMessages.map((entry) => <div key={entry.id} className={styles.readonlyField} data-message-role={entry.role} data-message-ref={entry.id} aria-label={entry.role} onContextMenu={(event) => openContextMenu(event, entry.id)}><span className={styles.fieldValue}>{entry.text}</span></div>)}</div> : <div className={styles.messageEmpty}>—</div>}{menuOpen && contextMessageId && <div className={styles.contextMenu} data-component-uid="CORE-01-CMP-MESSAGE-MENU" data-message-ref={contextMessageId} onClick={(event) => event.stopPropagation()}>{MESSAGE_MENU.map((item) => <button key={item.id} type="button" className={styles.contextMenuItem} data-control-id={item.id} data-action-uid={actionUid(item.id)} data-runtime-binding="ACTION_BOUND" onClick={() => runMessageMenu(item.id)}>{t(item.key)}</button>)}</div>}{!menuOpen && <div className={styles.menuComponentSentinel} data-component-uid="CORE-01-CMP-MESSAGE-MENU" aria-hidden="true" />}</div></section>
          <section className={`${styles.panel} ${styles.decisionPanel}`} data-section-id="CORE-01-SEC-05" data-visual-id="CORE-01-VIS-DECISION"><PanelTitle labelKey="core01.group.decision" /><div className={styles.decisionGrid}><div data-component-uid="CORE-01-CMP-SUMMARY"><ReadonlyField id="CORE-01-FLD-ASSISTANT-SUMMARY" labelKey="core01.control.assistant_summary" value={display("assistant_summary")} /></div><div data-component-uid="CORE-01-CMP-EVALUATION"><ReadonlyField id="CORE-01-FLD-EVALUATION" labelKey="core01.control.evaluation" value={display("evaluation")} /></div><div className={styles.humanDecision} data-component-uid="CORE-01-CMP-HUMAN-DECISION"><label className={styles.textareaField}><span>{t("core01.control.human_decision")}</span><textarea data-control-id="CORE-01-FLD-HUMAN-DECISION" data-action-uid={actionUid("CORE-01-FLD-HUMAN-DECISION")} disabled={isBusy || !clientState.conversation_id} data-disabled-reason={isBusy ? `BUSY:${busyAction}` : !clientState.conversation_id ? "CONVERSATION_REQUIRED" : undefined} value={humanDecision} onChange={(event) => setHumanDecision(event.target.value)} aria-label={t("core01.control.human_decision")} /></label><ReadonlyField id="CORE-01-FLD-STRUCTURED-DECISION" labelKey="core01.control.structured_decision" value={display("structured_decision")} /><div className={styles.actionRow}><GatedAction id="CORE-01-BTN-CANDIDATE-CREATE" labelKey="core01.control.create_candidate" primary onClick={() => runControl("CORE-01-BTN-CANDIDATE-CREATE")} /><GatedAction id="CORE-01-BTN-CANDIDATE-CONFIRM" labelKey="core01.control.confirm_candidate" primary onClick={() => runControl("CORE-01-BTN-CANDIDATE-CONFIRM")} /><GatedAction id="CORE-01-BTN-RETURN-MODIFY" labelKey="core01.control.return_modify" onClick={() => runControl("CORE-01-BTN-RETURN-MODIFY")} /></div></div></div></section>
          <section className={styles.runtimeStrip} data-section-id="CORE-01-SEC-06" data-visual-id="CORE-01-VIS-RUNTIME"><div className={styles.runtimeComponent} data-component-uid="CORE-01-CMP-RUNTIME" data-control-id="CORE-01-FLD-RUNTIME-STAGE" data-action-uid={actionUid("CORE-01-FLD-RUNTIME-STAGE")}><span>{t("core01.control.runtime_stage")}</span><strong>{runtimeDisplay}</strong></div></section>
          <section className={`${styles.panel} ${styles.composerPanel}`} data-section-id="CORE-01-SEC-07" data-visual-id="CORE-01-VIS-COMPOSER"><div className={styles.composer} data-component-uid="CORE-01-CMP-COMPOSER"><div className={styles.composerTools}><GatedAction id="CORE-01-BTN-ATTACHMENT" labelKey="core01.control.attachment" compact onClick={() => runControl("CORE-01-BTN-ATTACHMENT")} /><GatedAction id="CORE-01-BTN-REFERENCE" labelKey="core01.control.reference" compact onClick={() => runControl("CORE-01-BTN-REFERENCE")} /></div><textarea ref={composerRef} data-control-id="CORE-01-FLD-MESSAGE" data-action-uid={actionUid("CORE-01-FLD-MESSAGE")} disabled={isBusy || !clientState.conversation_id} data-disabled-reason={isBusy ? `BUSY:${busyAction}` : !clientState.conversation_id ? "CONVERSATION_REQUIRED" : undefined} aria-label={t("core01.control.message")} placeholder={t("core01.control.message")} value={message} onChange={(event) => setMessage(event.target.value)} /><GatedAction id="CORE-01-BTN-SEND" labelKey="core01.control.send" primary onClick={() => runControl("CORE-01-BTN-SEND")} /></div></section>
        </main>

        <aside className={styles.rightRail} data-layout-column="right">
          <section className={styles.panel} data-section-id="CORE-01-SEC-08" data-visual-id="CORE-01-VIS-RIGHT-CORE"><div className={styles.stateBlock} data-component-uid="CORE-01-CMP-PROJECT-STATE"><PanelTitle labelKey="core01.group.project_core_state" /><div className={styles.stateValue}>{display("project_state")} | {display("story_candidate_set")} | {display("dna_state")}</div><details className={styles.auxiliaryDetails}><summary>{t("core01.group.project_core_state")}</summary><div className={styles.stackActions}><GatedAction id="CORE-01-BTN-PROJECT-VALIDATE" labelKey="core01.control.project_validate" onClick={() => runControl("CORE-01-BTN-PROJECT-VALIDATE")} /><GatedAction id="CORE-01-BTN-PROJECT-CONFIRM" labelKey="core01.control.project_confirm" onClick={() => runControl("CORE-01-BTN-PROJECT-CONFIRM")} /><GatedAction id="CORE-01-BTN-STORY-CANDIDATE" labelKey="core01.control.story_candidate" onClick={() => runControl("CORE-01-BTN-STORY-CANDIDATE")} /><GatedAction id="CORE-01-BTN-DNA-LOCK" labelKey="core01.control.dna_lock" onClick={() => runControl("CORE-01-BTN-DNA-LOCK")} /><GatedAction id="CORE-01-BTN-CORE-REVIEW" labelKey="core01.control.core_review" onClick={() => runControl("CORE-01-BTN-CORE-REVIEW")} /><GatedAction id="CORE-01-BTN-PROJECT-LOCK" labelKey="core01.control.project_lock" onClick={() => runControl("CORE-01-BTN-PROJECT-LOCK")} /></div></details></div><div className={styles.divider} /><div className={styles.stateBlock} data-component-uid="CORE-01-CMP-BLUEPRINT-STATE"><PanelTitle labelKey="core01.group.blueprint_state" /><div className={styles.stateValue}>{display("blueprint_state")}</div><details className={styles.auxiliaryDetails}><summary>{t("core01.group.blueprint_state")}</summary><div className={styles.stackActions}><GatedAction id="CORE-01-BTN-BLUEPRINT-CREATE" labelKey="core01.control.blueprint_create" onClick={() => runControl("CORE-01-BTN-BLUEPRINT-CREATE")} /><GatedAction id="CORE-01-BTN-BLUEPRINT-VALIDATE" labelKey="core01.control.blueprint_validate" onClick={() => runControl("CORE-01-BTN-BLUEPRINT-VALIDATE")} /><GatedAction id="CORE-01-BTN-BLUEPRINT-APPROVE" labelKey="core01.control.blueprint_approve" onClick={() => runControl("CORE-01-BTN-BLUEPRINT-APPROVE")} /><GatedAction id="CORE-01-BTN-CHILD-LOCK" labelKey="core01.control.child_lock" onClick={() => runControl("CORE-01-BTN-CHILD-LOCK")} /></div></details></div></section>
          <section className={styles.panel} data-section-id="CORE-01-SEC-09" data-visual-id="CORE-01-VIS-RIGHT-TOPIC"><div data-component-uid="CORE-01-CMP-TOPIC-PACKAGE"><PanelTitle labelKey="core01.group.topic_package" /><ReadonlyField id="CORE-01-FLD-TOPIC-SCOPE" labelKey="core01.control.topic_scope" value={display("topic_scope")} /><GatedAction id="CORE-01-BTN-CANONICAL-SCRIPT" labelKey="core01.control.canonical_script" onClick={() => runControl("CORE-01-BTN-CANONICAL-SCRIPT")} /><ReadonlyField id="CORE-01-FLD-PACKAGE" labelKey="core01.control.package" value={display("package")} /></div><div className={styles.divider} /><div data-component-uid="CORE-01-CMP-DOWNSTREAM"><PanelTitle labelKey="core01.group.downstream" /><ReadonlyField id="CORE-01-FLD-DOWNSTREAM-ASSET" labelKey="core01.control.downstream_asset" value={display("downstream_asset")} /><ReadonlyField id="CORE-01-FLD-DOWNSTREAM-VIDEO" labelKey="core01.control.downstream_video" value={display("downstream_video")} /><ReadonlyField id="CORE-01-FLD-DOWNSTREAM-EDIT" labelKey="core01.control.downstream_edit" value={display("downstream_edit")} /></div></section>
          <section className={styles.panel} data-section-id="CORE-01-SEC-10" data-visual-id="CORE-01-VIS-RIGHT-VERSION"><div data-component-uid="CORE-01-CMP-VERSION"><PanelTitle labelKey="core01.group.version" /><GatedAction id="CORE-01-BTN-CANDIDATE-COMPARE" labelKey="core01.control.candidate_compare" onClick={() => runControl("CORE-01-BTN-CANDIDATE-COMPARE")} /><ReadonlyField id="CORE-01-FLD-VERSION-STATE" labelKey="core01.control.version_state" value={display("version_state")} /><div className={styles.stateValue} data-candidate-compare-read-model="true">{display("candidate_compare")}</div></div><div className={styles.divider} /><div data-component-uid="CORE-01-CMP-LOCK-REVIEW"><PanelTitle labelKey="core01.group.lock_review" /><ReadonlyField id="CORE-01-FLD-LOCK-REVIEW" labelKey="core01.control.lock_review" value={display("lock_review")} /></div></section>
        </aside>
      </div>
      {lockDialog ? <div className={styles.modalBackdrop} role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)closeLockDialog();}}>
        <form className={styles.lockModal} role="dialog" aria-modal="true" aria-labelledby="core-lock-modal-title" onSubmit={(event)=>{event.preventDefault();submitLockDialog();}}>
          <h2 id="core-lock-modal-title">{t(lockDialog==="MOTHER_LOCK"?"core01.lock_modal.title_mother":"core01.lock_modal.title_child")}</h2>
          <label className={styles.modalField}><span>{t("core01.lock_modal.request_reason")}</span><textarea value={lockRequestReason} disabled={Boolean(busyAction)} onChange={(event)=>setLockRequestReason(event.target.value)} required /></label>
          <label className={styles.modalField}><span>{t("core01.lock_modal.criteria_version")}</span><select value={lockCriteriaVersionId} disabled={Boolean(busyAction)} onChange={(event)=>setLockCriteriaVersionId(event.target.value)} required><option value="">—</option>{(projection?.lock_context.approved_criteria??[]).map(item=><option key={item.criteria_version_id} value={item.criteria_version_id}>{item.label}</option>)}</select></label>
          <div className={styles.modalReadOnly}><span>{t("core01.lock_modal.evidence_refs")}</span><strong>{clientState.decision_evidence_refs.length}</strong></div>
          <div className={styles.modalReadOnly}><span>{t("core01.lock_modal.reviewer_ready")}</span><strong>{projection?.lock_context.eligible_reviewer_count??0}</strong></div>
          <div className={styles.modalActions}><button type="button" className={styles.button} disabled={Boolean(busyAction)} onClick={closeLockDialog}>{t("core01.lock_modal.cancel")}</button><button type="submit" className={`${styles.button} ${styles.primaryButton}`} disabled={Boolean(busyAction)||!lockRequestReason.trim()||!lockCriteriaVersionId}>{t("core01.lock_modal.execute")}</button></div>
        </form>
      </div> : null}
      <section className={styles.stageActionDock} data-current-stage-action-dock="true" data-current-stage={String(coreStage)} data-primary-control-ref={stageMeta.control}>
        <div className={styles.stageSummary}><span>{t("core01.control.runtime_stage")}</span><strong>{runtimeDisplay}</strong></div>
        <div className={styles.stagePrimaryHint}><span>{t("core01.control.runtime_stage")}</span><strong>{t(stageMeta.key)}</strong></div>
      </section>
    </div>
  );
}
