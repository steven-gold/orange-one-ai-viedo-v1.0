"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { isAiUnavailable } from "@/lib/aiReply";
import { CoreClientError, fetchCoreReadModel, postCoreAction, type CoreFieldValue } from "@/lib/client";
import {
  activeThreadUid,
  assignedAiRouteReady,
  canonicalScriptRef,
  composerHasBlockingToken,
  exactName,
  messageExceedsStoredLimit,
  parseCanonicalScript,
  messagesForThread,
  notebookTextForThread,
  previewCoreAction,
  quoteInsertText,
  resolveComposerTokens,
  resolveResumePointer,
  threadScopeReady,
  threadsForCurrentWorkItem,
} from "@/lib/coreActionPreview";
import { displayCoreValue } from "./coreFormat";
import {
  CORE_CONTROL_ACTIONS,
  CORE_VISIBLE_CONTROLS,
  PROJECT_WORK_ITEMS,
  TOPIC_WORK_ITEMS,
} from "./coreControls";
import styles from "./CoreVisual.module.css";
import { IconButton } from "@/components/ui/IconButton";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";
const FILE_STATUS = new Set(["attached", "created", "selected", "已附加", "已上傳", "參考資料", "已引用", "Attached", "Reference"]);

type NameDialogKind = "project" | "topic" | "thread" | "blueprint" | "rename-project" | "rename-topic";

const WORK_ITEM_KEYS: Record<string, TranslationKey> = {
  STORY: "core.work.story",
  CHAPTER: "core.work.chapter",
  WORLD_SETTING: "core.work.world",
  DNA: "core.work.dna",
  BLUEPRINT: "core.work.blueprint",
  TOPIC_SCOPE: "core.work.topic_scope",
  PRODUCTION_SCRIPT: "core.work.production_script",
};

const RUNTIME_STAGES: { id: string; key: TranslationKey }[] = [
  { id: "AI_RESPONSES", key: "core.stage.ai_responses" },
  { id: "ASSISTANT_SUMMARY", key: "core.stage.assistant_summary" },
  { id: "CORE_EVALUATION", key: "core.stage.core_evaluation" },
  { id: "HUMAN_DECISION", key: "core.stage.human_decision" },
  { id: "CANDIDATE", key: "core.stage.candidate" },
];

const MESSAGE_MENU: { uid: string; actionUid: string; key: TranslationKey }[] = [
  { uid: "CORE-01-MENU-QUOTE", actionUid: "CORE-01-ACT-MSG-QUOTE", key: "core.menu.quote" },
  { uid: "CORE-01-MENU-CONTINUE", actionUid: "CORE-01-ACT-MSG-CONTINUE", key: "core.menu.continue" },
  { uid: "CORE-01-MENU-ANALYZE", actionUid: "CORE-01-ACT-MSG-ANALYZE", key: "core.menu.analyze" },
  { uid: "CORE-01-MENU-DECISION", actionUid: "CORE-01-ACT-MSG-DECISION", key: "core.menu.decision" },
  { uid: "CORE-01-MENU-BRANCH", actionUid: "CORE-01-ACT-MSG-BRANCH", key: "core.menu.branch" },
  { uid: "CORE-01-MENU-COPY", actionUid: "CORE-01-ACT-MSG-COPY", key: "core.menu.copy" },
];

function emptyFields(): CoreFieldValue[] {
  return CORE_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null }));
}

function Field({
  uid,
  label,
  value,
  loading,
  onAct,
  disabled,
  readonly = false,
  hint,
}: {
  uid: string;
  label: string;
  value: string | null;
  loading: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
  readonly?: boolean;
  hint?: string;
}) {
  if (readonly) {
    return (
      <div className={`${styles.field} ${styles.fieldReadonly}`} data-control-uid={uid}>
        <span className={styles.label}>{label}</span>
        <span className={styles.value}>{displayCoreValue(value, loading)}</span>
        {hint ? <span className={styles.meta}>{hint}</span> : null}
      </div>
    );
  }
  return (
    <button type="button" className={styles.field} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayCoreValue(value, loading)}</span>
    </button>
  );
}

export function CoreVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(true);
  const [fields, setFields] = useState<CoreFieldValue[]>(emptyFields);
  const [dialog, setDialog] = useState<NameDialogKind | null>(null);
  const [dialogName, setDialogName] = useState("");
  const [draftMessage, setDraftMessage] = useState("");
  const [tick, setTick] = useState(0);
  const [menu, setMenu] = useState<{ x: number; y: number; ref: string; text: string } | null>(null);
  const [scriptOpen, setScriptOpen] = useState(false);
  const fieldsRef = useRef(fields);
  const attachRef = useRef<HTMLInputElement>(null);
  const referenceRef = useRef<HTMLInputElement>(null);
  fieldsRef.current = fields;

  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    const timer = window.setTimeout(() => window.addEventListener("click", close), 0);
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("click", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [menu]);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    fetchCoreReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        if (model.fields.length) {
          setFields((prev) => {
            const map = new Map(prev.map((row) => [row.controlUid, row.value]));
            for (const row of model.fields) {
              if (row.controlUid === "CORE-01-FLD-ASSIGNED-AI") {
                map.set(row.controlUid, row.value);
                continue;
              }
              if (row.value != null && row.value !== "") map.set(row.controlUid, row.value);
            }
            return CORE_VISIBLE_CONTROLS.map((controlUid) => ({
              controlUid,
              value: map.get(controlUid) ?? null,
            }));
          });
        }
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof CoreClientError ? cause.code : "CORE_READ_UNAVAILABLE");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [tick]);

  const valueOf = useCallback(
    (controlUid: string) => fields.find((row) => row.controlUid === controlUid)?.value ?? null,
    [fields],
  );

  const applyPatch = useCallback((patch: Record<string, string>) => {
    setFields((prev) => {
      const map = new Map(prev.map((row) => [row.controlUid, row.value]));
      for (const [uid, value] of Object.entries(patch)) map.set(uid, value);
      return CORE_VISIBLE_CONTROLS.map((controlUid) => ({
        controlUid,
        value: map.has(controlUid) ? (map.get(controlUid) ?? null) : null,
      }));
    });
  }, []);

  const act = useCallback(async (controlUid: string, nextValue?: string) => {
    const actionUid = CORE_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    const patch = previewCoreAction(
      controlUid,
      actionUid,
      (uid) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null,
      nextValue,
    );
    if (!Object.keys(patch).length) return;
    applyPatch(patch);
    try {
      await postCoreAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, nextValue);
      if (actionUid === "CORE-01-ACT-SEND" || actionUid === "CORE-01-ACT-MSG-ANALYZE") setTick((value) => value + 1);
    } catch {
      // Optimistic projection stays visible when the write path is unbound.
    }
  }, [applyPatch]);

  const openNameDialog = useCallback((kind: NameDialogKind, preset = "") => {
    setDialogName(preset);
    setDialog(kind);
  }, []);

  const confirmNameDialog = useCallback(() => {
    if (!dialog) return;
    const name = dialogName.trim();
    const confirmed =
      fieldsRef.current.find((row) => row.controlUid === "CORE-01-BTN-PROJECT-CONFIRM")?.value === "confirmed" &&
      Boolean(exactName(fieldsRef.current.find((row) => row.controlUid === "CORE-01-CTL-PROJECT")?.value));
    if (dialog === "project") void act("CORE-01-BTN-PROJECT-CREATE", name || undefined);
    if (dialog === "topic") {
      const topic = exactName(name);
      if (confirmed && topic) void act("CORE-01-BTN-TOPIC-CREATE", topic);
    }
    if (dialog === "thread") {
      const current = (uid: string) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null;
      if (threadScopeReady(current)) void act("CORE-01-BTN-NEW-THREAD", name || undefined);
    }
    if (dialog === "blueprint") void act("CORE-01-BTN-BLUEPRINT-CREATE", name || undefined);
    if (dialog === "rename-project") void act("CORE-01-CTL-PROJECT", name || undefined);
    if (dialog === "rename-topic") {
      const topic = exactName(name);
      if (confirmed && topic) void act("CORE-01-CTL-TOPIC", topic);
    }
    setDialog(null);
    setDialogName("");
  }, [act, dialog, dialogName]);

  const pickFile = useCallback((kind: "attachment" | "reference", file: File | null) => {
    if (!file) return;
    void act(kind === "attachment" ? "CORE-01-BTN-ATTACHMENT" : "CORE-01-BTN-REFERENCE", file.name);
  }, [act]);

  const sendMessage = useCallback(() => {
    const current = (uid: string) => fieldsRef.current.find((row) => row.controlUid === uid)?.value ?? null;
    if (!activeThreadUid(current)) return;
    const text = draftMessage.trim();
    if (messageExceedsStoredLimit(text)) return;
    const tokens = resolveComposerTokens(text, current);
    if (composerHasBlockingToken(tokens)) return;
    if (!tokens.some((row) => row.kind === "TARGET_ASSISTANT") && !assignedAiRouteReady(current)) return;
    const attachment = current("CORE-01-BTN-ATTACHMENT");
    const reference = current("CORE-01-BTN-REFERENCE");
    const files = [attachment, reference].filter((name): name is string => typeof name === "string" && name.length > 0 && !FILE_STATUS.has(name));
    const payload = [text, ...files].filter(Boolean).join(" · ");
    if (!payload) return;
    setDraftMessage("");
    void act("CORE-01-BTN-SEND", payload);
  }, [act, draftMessage]);

  const insertQuote = useCallback((ref: string, prefix = "") => {
    const piece = quoteInsertText(ref);
    if (!piece && !prefix) return;
    setDraftMessage((prev) => {
      const lead = prefix && !prev.includes(prefix) ? `${prefix} ` : "";
      if (!prev) return `${lead}${piece}`.trimStart();
      const gap = /[\s\n]$/.test(prev) ? "" : " ";
      return `${lead}${prev}${gap}${piece}`;
    });
  }, []);

  const runMessageAction = useCallback((actionUid: string, messageRef: string, text: string) => {
    setMenu(null);
    if (actionUid === "CORE-01-ACT-MSG-QUOTE") {
      insertQuote(messageRef);
      return;
    }
    if (actionUid === "CORE-01-ACT-MSG-CONTINUE") {
      insertQuote(messageRef, "繼續討論");
      return;
    }
    if (actionUid === "CORE-01-ACT-MSG-COPY") {
      void navigator.clipboard?.writeText(text);
      return;
    }
    const controlUid = MESSAGE_MENU.find((row) => row.actionUid === actionUid)?.uid;
    if (!controlUid) return;
    void act(controlUid, JSON.stringify({ actionUid, messageRef }));
  }, [act, insertQuote]);

  const disabled = false;
  const tx = (key: TranslationKey) => t(key);
  const projectName = exactName(valueOf("CORE-01-CTL-PROJECT"));
  const topicName = exactName(valueOf("CORE-01-CTL-TOPIC"));
  const projectIsValidated = valueOf("CORE-01-BTN-PROJECT-VALIDATE") === "validated" && Boolean(projectName);
  const projectIsConfirmed =
    Boolean(projectName) &&
    (valueOf("CORE-01-BTN-PROJECT-CONFIRM") === "confirmed" ||
      valueOf("CORE-01-BTN-PROJECT-LOCK") === projectName);
  const topicBlocked = valueOf("CORE-01-FLD-RUNTIME-STAGE") === "TOPIC_LINEAGE_BLOCKED" && !projectIsConfirmed;
  const blueprintName = exactName(valueOf("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(valueOf("CORE-01-FLD-PACKAGE"));
  const scriptProjection = parseCanonicalScript(valueOf("CORE-01-BTN-CANONICAL-SCRIPT"));
  const scriptName = canonicalScriptRef(valueOf("CORE-01-BTN-CANONICAL-SCRIPT"));
  const topicMode = projectIsConfirmed && Boolean(topicName);
  const workItems = topicMode ? TOPIC_WORK_ITEMS : PROJECT_WORK_ITEMS;
  const storedWork = valueOf("CORE-01-LST-WORK-ITEMS");
  const activeWorkItem = (workItems as readonly string[]).includes(storedWork ?? "") ? storedWork! : workItems[0];
  const currentFields = (uid: string) => valueOf(uid);
  const canCreateThread = threadScopeReady(currentFields);
  const threadItems = threadsForCurrentWorkItem(currentFields).map((row) => row.title);
  const activeThread = activeThreadUid(currentFields) || null;
  const attachedFile = valueOf("CORE-01-BTN-ATTACHMENT");
  const referenceFile = valueOf("CORE-01-BTN-REFERENCE");
  const conversation = messagesForThread(valueOf("CORE-01-FLD-MESSAGE"), activeThread ?? "");
  const notebookText = notebookTextForThread(valueOf("CORE-01-FLD-ASSISTANT-SUMMARY"), activeThread ?? "");
  const pickedFileName = (stored: string | null) => (stored && !FILE_STATUS.has(stored) ? stored : "");
  const attachedName = pickedFileName(attachedFile);
  const referenceName = pickedFileName(referenceFile);
  const resume = resolveResumePointer(currentFields, activeThread ?? undefined);
  const resumeStatusKey: TranslationKey =
    resume?.stale_resolution_status === "STALE"
      ? "core.resume.stale"
      : resume?.stale_resolution_status === "HISTORICAL"
        ? "core.resume.historical"
        : resume?.stale_resolution_status === "BLOCKED"
          ? "core.resume.blocked"
          : resume?.stale_resolution_status === "CURRENT"
            ? "core.resume.current"
            : resume
              ? "core.resume.unverified"
              : "core.resume.missing";
  const composerTokens = resolveComposerTokens(draftMessage, currentFields);
  const parserBlocked = composerHasBlockingToken(composerTokens);
  const tooLong = messageExceedsStoredLimit(draftMessage);
  const routeReady = assignedAiRouteReady(currentFields);
  const assistantTarget = composerTokens.some((row) => row.kind === "TARGET_ASSISTANT");
  const hasDraft = Boolean(draftMessage.trim() || attachedName || referenceName);
  const routeBlocked = hasDraft && !assistantTarget && !routeReady;
  const canSend = Boolean(activeThread) && hasDraft && !parserBlocked && !routeBlocked && !tooLong;
  const dialogTitleKey: TranslationKey =
    dialog === "rename-topic"
      ? "core.dialog_rename_topic"
      : dialog === "topic"
        ? "core.dialog_topic"
        : dialog === "thread"
          ? "core.dialog_thread"
          : dialog === "blueprint"
            ? "core.dialog_blueprint"
            : dialog === "rename-project"
              ? "core.dialog_rename_project"
              : "core.dialog_project";
  const dialogDefault =
    dialog === "topic" || dialog === "rename-topic"
      ? tx("core.default_topic")
      : dialog === "thread"
        ? tx("core.default_thread")
        : dialog === "blueprint"
          ? tx("core.default_blueprint")
          : tx("core.default_project");
  const activeStage = valueOf("CORE-01-FLD-RUNTIME-STAGE") ?? "AI_RESPONSES";
  const multiActive = valueOf("CORE-01-BTN-MULTI-AI") === "active";
  const singleActive = !multiActive;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const workLabel = (item: string) => (WORK_ITEM_KEYS[item] ? tx(WORK_ITEM_KEYS[item]) : displayCoreValue(item, false));
  const currentWorkLabel = workLabel(activeWorkItem);

  return (
    <div
      className={styles.page}
      data-page-uid="CORE-01"
      data-page-state={pageState}
      data-component-count="17"
      data-control-count="50"
      aria-label={tx("core.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("core.error")}</div> : null}
      {topicBlocked ? <div className={styles.error} role="alert">{tx("core.topic_requires_confirmed_project")}</div> : null}

      <section className={styles.context} data-component-uid="CORE-01-CMP-CONTEXT">
        <Field uid="CORE-01-CTL-PROJECT" label={tx("core.project")} value={valueOf("CORE-01-CTL-PROJECT")} loading={loading} onAct={() => openNameDialog("rename-project", valueOf("CORE-01-CTL-PROJECT") ?? "")} disabled={disabled} />
        <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="CORE-01-BTN-PROJECT-CREATE" disabled={disabled} onClick={() => openNameDialog("project")}>{tx("core.create_project")}</button>
        <Field uid="CORE-01-CTL-TOPIC" label={tx("core.topic")} value={valueOf("CORE-01-CTL-TOPIC")} loading={loading} onAct={() => openNameDialog("rename-topic", valueOf("CORE-01-CTL-TOPIC") ?? "")} disabled={disabled || !projectIsConfirmed} />
        <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-TOPIC-CREATE" disabled={disabled} onClick={() => { if (projectIsConfirmed) openNameDialog("topic"); else void act("CORE-01-BTN-TOPIC-CREATE"); }}>{tx("core.create_topic")}</button>
        <button type="button" className={topicMode ? `${styles.btn} ${styles.active}` : styles.btn} data-control-uid="CORE-01-FLD-PAGE-MODE" disabled>
          {topicMode ? tx("core.page_mode_topic") : tx("core.page_mode_project")}
        </button>
        <Field uid="CORE-01-FLD-NAMING-AUTHORITY" label={tx("core.naming")} value={valueOf("CORE-01-FLD-NAMING-AUTHORITY")} loading={loading} onAct={act} disabled={disabled} />
        <div className={styles.field}>
          <span className={styles.label}>{tx("core.current_context")}</span>
          <span className={styles.value}>{[displayCoreValue(valueOf("CORE-01-CTL-PROJECT"), loading), displayCoreValue(valueOf("CORE-01-CTL-TOPIC"), loading), currentWorkLabel, activeThread ? displayCoreValue(activeThread, loading) : tx("core.thread_n")].join(" / ")}</span>
        </div>
      </section>

      <div className={styles.body}>
        <aside className={styles.nav} data-component-uid="CORE-01-CMP-NAV">
          <h2 className={styles.title}>{tx("core.work_item_thread")}</h2>
          <div className={styles.workList} data-control-uid="CORE-01-LST-WORK-ITEMS">
            {workItems.map((item) => (
              <button key={item} type="button" className={item === activeWorkItem ? `${styles.workItem} ${styles.active}` : styles.workItem} disabled={disabled} onClick={() => void act("CORE-01-LST-WORK-ITEMS", item)}>
                {workLabel(item)}
                <span>{item === activeWorkItem ? displayCoreValue("selected", loading) : displayCoreValue(null, loading)}</span>
              </button>
            ))}
          </div>
          <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-NEW-THREAD" disabled={disabled || !canCreateThread} onClick={() => openNameDialog("thread")}>{tx("core.new_thread")}</button>
          <div data-component-uid="CORE-01-CMP-THREADS">
            <div className={styles.threadsLabel}>{tx("core.threads")}</div>
            <div className={styles.threadList} data-control-uid="CORE-01-LST-THREADS">
              {threadItems.length === 0 ? <p className={styles.threadEmpty}>{canCreateThread ? tx("core.no_threads") : tx("core.gate-thread")}</p> : null}
              {threadItems.map((threadUid) => {
                const selected = activeThread === threadUid;
                return (
                  <button key={threadUid} type="button" className={selected ? `${styles.thread} ${styles.active}` : styles.thread} disabled={disabled} onClick={() => void act("CORE-01-LST-THREADS", threadUid)}>
                    <span>{threadUid}</span>
                    <small>{currentWorkLabel}</small>
                  </button>
                );
              })}
            </div>
          </div>
          <section className={styles.integrity}>
            <h3>{tx("core.integrity")}</h3>
            <div className={styles.integrityRow}><span>{tx("core.project_topic")}</span><span className={styles.ok}>{tx("core.exact_refs")}</span></div>
            <div className={styles.integrityRow}><span>{tx("core.work_item_thread")}</span><span className={styles.warn}>{tx("core.scoped")}</span></div>
            <div className={styles.integrityRow}><span>{tx("core.cross_mix")}</span><span className={styles.danger}>{tx("core.forbidden")}</span></div>
          </section>
        </aside>

        <main className={styles.center}>
          <section className={styles.convHeader} data-component-uid="CORE-01-CMP-CONV-HEADER">
            <div className={styles.headerRow}>
              <div>
                <div className={styles.label}>{tx("core.conv_header")}</div>
                <strong>{currentWorkLabel}</strong>
                <div className={styles.meta}>{tx(resumeStatusKey)}{resume?.conversation_id ? ` ${resume.conversation_id}` : ""}</div>
              </div>
              <div className={styles.headerControls}>
                <IconButton uid="CORE-01-BTN-SINGLE-AI" label={tx("core.single_ai")} icon="single-ai" onAct={act} disabled={disabled} className={[styles.btn, styles.iconBtn, singleActive ? styles.active : ""].filter(Boolean).join(" ")} />
                <IconButton uid="CORE-01-BTN-MULTI-AI" label={routeReady ? tx("core.multi_ai") : tx("core.route_blocked")} icon="multi-ai" onAct={act} disabled={disabled || !routeReady} className={[styles.btn, styles.iconBtn, multiActive ? styles.active : ""].filter(Boolean).join(" ")} />
                <Field uid="CORE-01-FLD-ASSIGNED-AI" label={tx("core.assigned_ai")} value={valueOf("CORE-01-FLD-ASSIGNED-AI")} loading={loading} onAct={act} disabled={disabled} readonly hint={tx("core.assigned_ai_hint")} />
                <IconButton uid="CORE-01-BTN-ASSISTANT-RECORD" label={tx("core.assistant_record")} icon="record" onAct={act} disabled={disabled} className={`${styles.btn} ${styles.iconBtn}`} />
              </div>
            </div>
          </section>

          <section className={styles.messages} data-component-uid="CORE-01-CMP-MESSAGES">
            <div className={styles.messagesHead}>
              <h2 className={styles.title}>{tx("core.messages")}</h2>
              <span>{tx("core.right_click_only")}</span>
            </div>
            <div className={styles.timeline}>
              {conversation.length === 0 ? (
                <p className={styles.threadEmpty}>{tx("core.conversation_empty")}</p>
              ) : (
                conversation.map((row, index) => (
                  <article
                    key={row.ref || `${row.role}-${index}`}
                    className={row.role === "user" ? styles.userMessage : styles.assistantMessage}
                    onContextMenu={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      if (!row.ref) return;
                      setMenu({ x: event.clientX, y: event.clientY, ref: row.ref, text: row.text });
                    }}
                  >
                    <div className={styles.bubbleRole}>
                      {row.role === "user" ? tx("core.user_message") : tx("core.ai_response_n")}
                      {row.alias ? ` @${row.alias}` : ""}
                      {row.ref ? ` ${row.ref}` : ""}
                      {row.at ? ` ${row.at}` : ""}
                    </div>
                    <p>{row.role === "assistant" && isAiUnavailable(row.text) ? tx("ai.unavailable") : row.text}</p>
                  </article>
                ))
              )}
            </div>
            <div className={styles.summaryInline}>
              <span className={styles.summaryLabel}>{tx("core.summary_inline")}</span>
              <p>{notebookText || tx("core.summary_hint")}</p>
            </div>
            <div
              className={menu ? styles.messageMenu : styles.messageMenuHidden}
              data-component-uid="CORE-01-CMP-MESSAGE-MENU"
              hidden={!menu}
              style={menu ? { left: menu.x, top: menu.y } : undefined}
              onClick={(event) => event.stopPropagation()}
            >
              {MESSAGE_MENU.map((item) => (
                <button
                  key={item.uid}
                  type="button"
                  className={styles.menuItem}
                  data-control-uid={item.uid}
                  data-action-uid={item.actionUid}
                  disabled={disabled || !menu}
                  onClick={() => menu && runMessageAction(item.actionUid, menu.ref, menu.text)}
                >
                  {tx(item.key)}
                </button>
              ))}
            </div>
          </section>

          <section className={styles.eval} hidden={topicMode}>
            <h2 className={styles.title}>{tx("core.evaluation_title")}</h2>
            <div className={styles.evalGrid}>
              <div className={styles.evalBox} data-component-uid="CORE-01-CMP-SUMMARY" data-control-uid="CORE-01-FLD-ASSISTANT-SUMMARY">
                <h3>{tx("core.assistant_summary")}</h3>
                <p>{notebookText || displayCoreValue(null, loading)}</p>
                <span className={styles.meta}>{tx("core.read_only")}</span>
              </div>
              <div className={styles.evalBox} data-component-uid="CORE-01-CMP-EVALUATION" data-control-uid="CORE-01-FLD-EVALUATION">
                <h3>{tx("core.evaluation")}</h3>
                <p>{tx("core.evaluation_meta")} {displayCoreValue(valueOf("CORE-01-FLD-EVALUATION"), loading)}</p>
                <span className={styles.meta}>{tx("core.read_only")}</span>
              </div>
              <button type="button" className={styles.evalBox} data-component-uid="CORE-01-CMP-HUMAN-DECISION" data-control-uid="CORE-01-FLD-HUMAN-DECISION" disabled={disabled} onClick={() => void act("CORE-01-FLD-HUMAN-DECISION")}>
                <h3>{tx("core.human_decision")}</h3>
                <p>{displayCoreValue(valueOf("CORE-01-FLD-HUMAN-DECISION"), loading)}</p>
                <span className={styles.meta}>{tx("core.editable")}</span>
              </button>
            </div>
            <div className={styles.structuredRow}>
              <button type="button" className={`${styles.btn} ${styles.structured}`} data-control-uid="CORE-01-FLD-STRUCTURED-DECISION" disabled={disabled} onClick={() => void act("CORE-01-FLD-STRUCTURED-DECISION")}>
                {tx("core.structured_decision")} {displayCoreValue(valueOf("CORE-01-FLD-STRUCTURED-DECISION"), loading)} {tx("core.no_self_approve")}
              </button>
            </div>
            <div className={styles.candidateRow}>
              <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="CORE-01-BTN-CANDIDATE-CREATE" disabled={disabled} onClick={() => void act("CORE-01-BTN-CANDIDATE-CREATE")}>{tx("core.create_candidate")}</button>
              <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="CORE-01-BTN-CANDIDATE-CONFIRM" disabled={disabled} onClick={() => void act("CORE-01-BTN-CANDIDATE-CONFIRM")}>{tx("core.confirm_candidate")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-RETURN-MODIFY" disabled={disabled} onClick={() => void act("CORE-01-BTN-RETURN-MODIFY")}>{tx("core.return_modify")}</button>
              <span className={styles.hint}>{tx("core.decision_flow")}</span>
            </div>
          </section>

          <section className={styles.eval} hidden={!topicMode}>
            <h2 className={styles.title}>{tx("core.topic_discussion")}</h2>
            <div className={styles.evalGridTwo}>
              <button type="button" className={styles.evalBox} data-control-uid="CORE-01-FLD-TOPIC-SCOPE" disabled={disabled} onClick={() => void act("CORE-01-FLD-TOPIC-SCOPE")}>
                <h3>{tx("core.topic_scope")}</h3>
                <p>{displayCoreValue(valueOf("CORE-01-FLD-TOPIC-SCOPE"), loading)}</p>
              </button>
              <div className={styles.evalBox}>
                <h3>{tx("core.canonical_script")}</h3>
                <p>{tx("core.canonical_hint")}</p>
              </div>
            </div>
            <div className={`${styles.evalBox} ${styles.constraintBox}`}>
              <h3>{tx("core.discussion_constraint")}</h3>
              <p>{tx("core.discussion_constraint_body")}</p>
            </div>
          </section>

          <section className={`${styles.runtime} ${styles.composerBar}`} data-component-uid="CORE-01-CMP-RUNTIME" data-control-uid="CORE-01-FLD-RUNTIME-STAGE">
            {RUNTIME_STAGES.map((stage) => (
              <button key={stage.id} type="button" className={stage.id === activeStage ? `${styles.btn} ${styles.runtimeBtn} ${styles.active}` : `${styles.btn} ${styles.runtimeBtn}`} disabled={disabled} onClick={() => void act("CORE-01-FLD-RUNTIME-STAGE", stage.id)}>
                {tx(stage.key)}
              </button>
            ))}
          </section>

          <section className={styles.composerBar} data-component-uid="CORE-01-CMP-COMPOSER">
            <div className={styles.composer}>
              <input ref={attachRef} className={styles.fileInput} type="file" onChange={(event) => { pickFile("attachment", event.target.files?.[0] ?? null); event.target.value = ""; }} />
              <input ref={referenceRef} className={styles.fileInput} type="file" onChange={(event) => { pickFile("reference", event.target.files?.[0] ?? null); event.target.value = ""; }} />
              <IconButton uid="CORE-01-BTN-ATTACHMENT" label={tx("core.attachment")} icon="attachment" onAct={() => attachRef.current?.click()} disabled={disabled} className={[styles.btn, styles.iconBtn, attachedName ? styles.active : ""].filter(Boolean).join(" ")} />
              <IconButton uid="CORE-01-BTN-REFERENCE" label={tx("core.reference")} icon="reference" onAct={() => referenceRef.current?.click()} disabled={disabled} className={[styles.btn, styles.iconBtn, referenceName ? styles.active : ""].filter(Boolean).join(" ")} />
              <label className={styles.composerInput}>
                <span className={styles.srOnly}>{tx("core.message")}</span>
                <textarea
                  data-control-uid="CORE-01-FLD-MESSAGE"
                  disabled={disabled}
                  placeholder={tx("core.message_placeholder")}
                  value={draftMessage}
                  rows={3}
                  onChange={(event) => setDraftMessage(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter") return;
                    if (event.nativeEvent.isComposing) return;
                    if (event.ctrlKey || event.metaKey) {
                      event.preventDefault();
                      sendMessage();
                      return;
                    }
                  }}
                />
              </label>
              <IconButton uid="CORE-01-BTN-SEND" label={tooLong ? tx("core.message_too_long") : parserBlocked ? tx("core.parser_blocked") : routeBlocked ? tx("core.route_blocked") : canSend ? tx("core.send") : tx("core.gate-message")} icon="send" onAct={() => sendMessage()} disabled={disabled || !canSend} className={`${styles.btn} ${styles.iconBtn} ${styles.btnSend}`} />
            </div>
            {tooLong ? <p className={styles.error} role="alert">{tx("core.message_too_long")}</p> : null}
            {parserBlocked ? <p className={styles.error} role="alert">{tx("core.parser_blocked")}</p> : null}
            {routeBlocked ? <p className={styles.error} role="alert">{tx("core.route_blocked")}</p> : null}
            {attachedName || referenceName ? (
              <p className={styles.composerFiles}>
                {attachedName ? `${tx("core.attached_file")} ${attachedName}` : null}
                {attachedName && referenceName ? " · " : null}
                {referenceName ? `${tx("core.reference_file")} ${referenceName}` : null}
              </p>
            ) : null}
          </section>
        </main>

        <aside className={styles.rail}>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-PROJECT-STATE" hidden={topicMode}>
            <h2 className={styles.title}>{tx("core.project_rail")}</h2>
            <h3>{tx("core.project_state")}</h3>
            <div className={styles.kv}><span>{tx("core.project_version_ref")}</span><span>{displayCoreValue(valueOf("CORE-01-CTL-PROJECT"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.story_world")}</span><span>{displayCoreValue(valueOf("CORE-01-LST-WORK-ITEMS"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.dna_version")}</span><span>{displayCoreValue(valueOf("CORE-01-BTN-DNA-LOCK"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.core_review_state")}</span><span>{displayCoreValue(valueOf("CORE-01-BTN-CORE-REVIEW"), loading)}</span></div>
            <div className={styles.railActions}>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-PROJECT-VALIDATE" disabled={disabled || !projectName} onClick={() => void act("CORE-01-BTN-PROJECT-VALIDATE")}>{tx("core.validate_project")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-PROJECT-CONFIRM" disabled={disabled || !projectIsValidated} onClick={() => void act("CORE-01-BTN-PROJECT-CONFIRM")}>{tx("core.confirm_project")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-STORY-CANDIDATE" disabled={disabled || !projectName} onClick={() => void act("CORE-01-BTN-STORY-CANDIDATE")}>{tx("core.story_candidate")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-DNA-LOCK" disabled={disabled || !projectName} onClick={() => void act("CORE-01-BTN-DNA-LOCK")}>{tx("core.dna_lock")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-CORE-REVIEW" disabled={disabled || !projectName} onClick={() => void act("CORE-01-BTN-CORE-REVIEW")}>{tx("core.core_review")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-PROJECT-LOCK" disabled={disabled || !projectName} onClick={() => void act("CORE-01-BTN-PROJECT-LOCK")}>{tx("core.project_lock")}</button>
            </div>
          </section>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-BLUEPRINT-STATE" hidden={topicMode}>
            <h3>{tx("core.blueprint_state")}</h3>
            <div className={styles.kv}><span>{tx("core.blueprint_version_ref")}</span><span>{displayCoreValue(valueOf("CORE-01-BTN-BLUEPRINT-CREATE"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.state_label")}</span><span>{displayCoreValue(valueOf("CORE-01-BTN-BLUEPRINT-VALIDATE") ?? valueOf("CORE-01-BTN-BLUEPRINT-APPROVE"), loading)}</span></div>
            <div className={styles.railActions}>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-BLUEPRINT-CREATE" disabled={disabled} onClick={() => openNameDialog("blueprint")}>{tx("core.create_blueprint")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-BLUEPRINT-VALIDATE" disabled={disabled || !blueprintName} onClick={() => void act("CORE-01-BTN-BLUEPRINT-VALIDATE")}>{tx("core.validate_blueprint")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-BLUEPRINT-APPROVE" disabled={disabled || !blueprintName} onClick={() => void act("CORE-01-BTN-BLUEPRINT-APPROVE")}>{tx("core.approve_blueprint")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-CHILD-LOCK" disabled={disabled || !blueprintName} onClick={() => void act("CORE-01-BTN-CHILD-LOCK")}>{tx("core.child_lock")}</button>
            </div>
          </section>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-TOPIC-PACKAGE" hidden={!topicMode}>
            <h2 className={styles.title}>{tx("core.topic_package_title")}</h2>
            <h3>{tx("core.topic_package")}</h3>
            <div className={styles.kv}><span>{tx("core.topic_scope")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-TOPIC-SCOPE"), loading)}</span></div>
            <div className={styles.kv} data-control-uid="CORE-01-FLD-PACKAGE"><span>{tx("core.blueprint_label")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-PACKAGE"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.dna_label")}</span><span>{displayCoreValue(valueOf("CORE-01-BTN-DNA-LOCK"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_script")}</span><span>{displayCoreValue(scriptName, loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.naming")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-NAMING-AUTHORITY"), loading)}</span></div>
            <button type="button" className={`${styles.btn} ${styles.btnWide}`} data-control-uid="CORE-01-BTN-CANONICAL-SCRIPT" disabled={disabled || !scriptName} onClick={() => setScriptOpen(true)}>{tx("core.view_canonical")}</button>
          </section>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-DOWNSTREAM" hidden={!topicMode}>
            <h3>{tx("core.downstream")}</h3>
            <div className={styles.kv}><span>{tx("core.downstream_asset")}</span><button type="button" className={styles.btn} data-control-uid="CORE-01-FLD-DOWNSTREAM-ASSET" disabled={disabled} onClick={() => void act("CORE-01-FLD-DOWNSTREAM-ASSET")}>{displayCoreValue(valueOf("CORE-01-FLD-DOWNSTREAM-ASSET"), loading)}</button></div>
            <div className={styles.kv}><span>{tx("core.downstream_video")}</span><button type="button" className={styles.btn} data-control-uid="CORE-01-FLD-DOWNSTREAM-VIDEO" disabled={disabled} onClick={() => void act("CORE-01-FLD-DOWNSTREAM-VIDEO")}>{displayCoreValue(valueOf("CORE-01-FLD-DOWNSTREAM-VIDEO"), loading)}</button></div>
            <div className={styles.kv}><span>{tx("core.downstream_edit")}</span><button type="button" className={styles.btn} data-control-uid="CORE-01-FLD-DOWNSTREAM-EDIT" disabled={disabled} onClick={() => void act("CORE-01-FLD-DOWNSTREAM-EDIT")}>{displayCoreValue(valueOf("CORE-01-FLD-DOWNSTREAM-EDIT"), loading)}</button></div>
          </section>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-VERSION">
            <h3>{tx("core.version_lock")}</h3>
            <div className={styles.kv} data-control-uid="CORE-01-FLD-VERSION-STATE"><span>{tx("core.current_candidate")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-VERSION-STATE"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.confirmed_version")}</span><span>{displayCoreValue(valueOf("CORE-01-BTN-CANDIDATE-CONFIRM"), loading)}</span></div>
            <div className={styles.kv} data-component-uid="CORE-01-CMP-LOCK-REVIEW" data-control-uid="CORE-01-FLD-LOCK-REVIEW"><span>{tx("core.lock_review")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-LOCK-REVIEW"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.block_reason")}</span><span>{displayCoreValue(valueOf("CORE-01-BTN-CHILD-LOCK"), loading)}</span></div>
            <button type="button" className={`${styles.btn} ${styles.btnWide}`} data-control-uid="CORE-01-BTN-CANDIDATE-COMPARE" disabled={disabled} onClick={() => void act("CORE-01-BTN-CANDIDATE-COMPARE")}>{tx("core.compare_candidate")}</button>
            <p className={styles.overwrite}>{tx("core.no_overwrite")}</p>
          </section>
        </aside>
      </div>
      {scriptOpen ? (
        <div className={styles.dialogScrim} role="presentation" onClick={() => setScriptOpen(false)}>
          <section className={`${styles.dialog} ${styles.scriptDialog}`} onClick={(event) => event.stopPropagation()}>
            <h2>{tx("core.canonical_script")}</h2>
            <p className={styles.meta}>{tx("core.canonical_readonly")}</p>
            <div className={styles.kv}><span>{tx("core.canonical_id")}</span><span>{displayCoreValue(scriptProjection?.canonical_script_id, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_version")}</span><span>{displayCoreValue(scriptProjection?.version || scriptName, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_project")}</span><span>{displayCoreValue(scriptProjection?.project_id, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_topic")}</span><span>{displayCoreValue(scriptProjection?.topic_id, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_blueprint")}</span><span>{displayCoreValue(scriptProjection?.blueprint_ref, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_topic_scope")}</span><span>{displayCoreValue(scriptProjection?.topic_scope_ref, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_canon")}</span><span>{displayCoreValue(scriptProjection?.canon_refs, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_dna")}</span><span>{displayCoreValue(scriptProjection?.dna_ref, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_candidate")}</span><span>{displayCoreValue(scriptProjection?.source_candidate_ref, false)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_hash")}</span><span>{displayCoreValue(scriptProjection?.hash, false)}</span></div>
            <div className={styles.dialogActions}>
              <button type="button" className={styles.btn} onClick={() => setScriptOpen(false)}>{tx("core.close")}</button>
            </div>
          </section>
        </div>
      ) : null}
      {dialog ? (
        <div className={styles.dialogScrim} role="presentation" onClick={() => setDialog(null)}>
          <form
            className={styles.dialog}
            onClick={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault();
              confirmNameDialog();
            }}
          >
            <h2>{tx(dialogTitleKey)}</h2>
            <label>
              <span className={styles.label}>{tx("core.name_placeholder")}</span>
              <input
                autoFocus
                value={dialogName}
                placeholder={dialogDefault}
                onChange={(event) => setDialogName(event.target.value)}
              />
            </label>
            <div className={styles.dialogActions}>
              <button type="button" className={styles.btn} onClick={() => setDialog(null)}>{tx("core.cancel")}</button>
              <button
                type="submit"
                className={`${styles.btn} ${styles.btnPrimary}`}
                disabled={(dialog === "topic" || dialog === "rename-topic") && !exactName(dialogName)}
              >{tx("core.confirm")}</button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
