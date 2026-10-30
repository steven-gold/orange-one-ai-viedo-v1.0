import {
  CORE_CONVERSATION,
  type ConversationMessageRecord,
  type ConversationNotebookRecord,
  type ConversationResolvedToken,
  type ConversationResumePointer,
  type ConversationResumeStatus,
  type ConversationThreadRecord,
  type ConversationTokenKind,
  CONVERSATION_RECENT_HISTORY_ROWS as KERNEL_HISTORY_ROWS,
  CONVERSATION_RECENT_HISTORY_TEXT_CHARS as KERNEL_HISTORY_CHARS,
  CONVERSATION_STORED_MESSAGE_TEXT_CHARS as KERNEL_STORED_CHARS,
  activeThreadUidFor,
  appendAssistantMessageFor,
  appendAssistantMessagesFor,
  assignedAiRouteDisplay as kernelAssignedAiRouteDisplay,
  assignedAiRouteLabel as kernelAssignedAiRouteLabel,
  assignedAiRouteParts as kernelAssignedAiRouteParts,
  buildResumePointerFor,
  composerHasBlockingToken as kernelComposerHasBlockingToken,
  composerTokenTone as kernelComposerTokenTone,
  conversationAssignedAiReady,
  conversationFingerprint,
  conversationIsMultiAi,
  conversationMultiRouteReady,
  conversationParticipantAliases,
  conversationSnapshotRef,
  exactName as kernelExactName,
  formatConversationContext,
  hasSendableMessage as kernelHasSendableMessage,
  messageExceedsStoredLimit as kernelMessageExceedsStoredLimit,
  isPlaceholderName as kernelIsPlaceholderName,
  lastUserText as kernelLastUserText,
  messagesForThread as kernelMessagesForThread,
  MULTI_AI_ALIASES as KERNEL_MULTI_AI_ALIASES,
  namedList as kernelNamedList,
  namedValue as kernelNamedValue,
  notebookTextForThread as kernelNotebookTextForThread,
  parseAssistantIntent as kernelParseAssistantIntent,
  parseMessageActionPayload as kernelParseMessageActionPayload,
  parseMessageRecords as kernelParseMessageRecords,
  parseNotebookRecords as kernelParseNotebookRecords,
  parseThreadList as kernelParseThreadList,
  parseThreadRecords as kernelParseThreadRecords,
  persistConversationTasksFor as kernelPersistConversationTasksFor,
  persistResumeOnThreadsFor,
  previewConversationAction,
  previewMessageActionFor,
  quoteInsertText as kernelQuoteInsertText,
  generationHistoryPayload as kernelGenerationHistoryPayload,
  recentHistoryPayload as kernelRecentHistoryPayload,
  refreshAssistantNotebookFor,
  resolveComposerTokensFor,
  resolveResumePointerFor,
  targetedParticipantAliasesFor,
  threadScopeReadyFor,
  threadsForWorkItem,
  workItemFor,
  ASSISTANT_OPERATIONS as KERNEL_ASSISTANT_OPERATIONS,
} from "./conversationCore";
import {
  type MachineScript,
  type MediaViews,
  type ScriptBoundary,
  type ScriptContinuity,
  type ScriptScene,
  appendDecisionLog,
  parseMachineScriptField,
  parseMediaViewsField,
  parseScenesField,
} from "./canonicalViews";
import { dnaExactRef, parseBaseDna, parseDnaEnrichmentField, serializeBaseDna, type DnaEnrichment } from "./dnaDocument";

export const CONVERSATION_RECENT_HISTORY_ROWS = KERNEL_HISTORY_ROWS;
export const CONVERSATION_RECENT_HISTORY_TEXT_CHARS = KERNEL_HISTORY_CHARS;
export const CONVERSATION_STORED_MESSAGE_TEXT_CHARS = KERNEL_STORED_CHARS;

export const assignedAiRouteDisplay = kernelAssignedAiRouteDisplay;
export const assignedAiRouteLabel = kernelAssignedAiRouteLabel;
export const assignedAiRouteParts = kernelAssignedAiRouteParts;
export const isPlaceholderName = kernelIsPlaceholderName;
export const exactName = kernelExactName;
export const namedValue = kernelNamedValue;
export const namedList = kernelNamedList;
export const parseThreadList = kernelParseThreadList;
export const MULTI_AI_ALIASES = KERNEL_MULTI_AI_ALIASES;
export const quoteInsertText = kernelQuoteInsertText;
export const composerHasBlockingToken = kernelComposerHasBlockingToken;
export const composerTokenTone = kernelComposerTokenTone;
export const parseMessageActionPayload = kernelParseMessageActionPayload;
export const hasSendableMessage = kernelHasSendableMessage;
export const messageExceedsStoredLimit = kernelMessageExceedsStoredLimit;
export const parseAssistantIntent = kernelParseAssistantIntent;
export const ASSISTANT_OPERATIONS = KERNEL_ASSISTANT_OPERATIONS;
export const recentHistoryPayload = kernelRecentHistoryPayload;
export const generationHistoryPayload = kernelGenerationHistoryPayload;

export type CoreResumeStatus = ConversationResumeStatus;
export type CoreResumePointer = ConversationResumePointer;
export type CoreThreadRecord = ConversationThreadRecord;
export type CoreMessageRole = ConversationMessageRecord["role"];
export type CoreMessageRecord = ConversationMessageRecord;
export type CoreNotebookStatus = ConversationNotebookRecord["status"];
export type CoreNotebookRecord = ConversationNotebookRecord;
export type CoreTokenKind = ConversationTokenKind;
export type CoreResolvedToken = ConversationResolvedToken;
export type CoreMessageActionPayload = ReturnType<typeof kernelParseMessageActionPayload>;

const STATUS_TOKENS = new Set([
  "created",
  "selected",
  "validated",
  "confirmed",
  "approved",
  "locked",
  "sent",
  "queried",
  "open",
  "editing",
  "saved",
  "preview",
  "completed",
  "running",
  "retrying",
  "evaluated",
  "returned",
  "comparing",
  "attached",
  "recorded",
  "active",
  "idle",
  "ready",
  "PKG-READY",
  "PKG_READY",
]);

const WORK_ITEMS = new Set([
  "STORY",
  "CHAPTER",
  "WORLD_SETTING",
  "DNA",
  "BLUEPRINT",
  "TOPIC_SCOPE",
  "PRODUCTION_SCRIPT",
]);

export function assignedAiRouteReady(current: (uid: string) => string | null): boolean {
  return conversationAssignedAiReady(CORE_CONVERSATION, current);
}

export function assignedMultiRouteReady(current: (uid: string) => string | null): boolean {
  return conversationMultiRouteReady(CORE_CONVERSATION, current);
}

export function isMultiAiMode(current: (uid: string) => string | null): boolean {
  return conversationIsMultiAi(CORE_CONVERSATION, current);
}

export function assignedParticipantAliases(current: (uid: string) => string | null): string[] {
  return conversationParticipantAliases(CORE_CONVERSATION, current);
}

export function ensureMessageIdentity(records: CoreMessageRecord[]): CoreMessageRecord[] {
  return kernelParseMessageRecords(JSON.stringify(records));
}

export function parseMessageRecords(raw: string | null): CoreMessageRecord[] {
  return kernelParseMessageRecords(raw);
}

export function messagesForThread(
  raw: string | null,
  thread: string,
  fallbackAssistant?: string | null,
): CoreMessageRecord[] {
  return kernelMessagesForThread(raw, thread, fallbackAssistant);
}

export function lastAssistantText(raw: string | null, thread: string, fallback?: string | null): string {
  const records = kernelMessagesForThread(raw, thread, fallback);
  for (let index = records.length - 1; index >= 0; index -= 1) {
    if (records[index].role === "assistant") return records[index].text;
  }
  return "";
}

export function lastUserText(raw: string | null, thread: string): string {
  return kernelLastUserText(raw, thread);
}

function sourceHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export type CanonicalScriptProjection = {
  kind: "CANONICAL_SCRIPT";
  canonical_script_id: string;
  version: string;
  project_id: string;
  topic_id: string;
  blueprint_ref: string;
  topic_scope_ref: string;
  canon_refs: string;
  dna_ref: string;
  source_candidate_ref: string;
  hash: string;
  change_summary?: string;
  prior_version_ref?: string;
  structure?: { scenes: ScriptScene[]; boundary: ScriptBoundary };
  continuity?: ScriptContinuity;
  audit?: { human_decision: string; candidate_ref?: string; reviewer_ref?: string; decided_at: string };
  machine?: MachineScript;
  views?: MediaViews;
  dna_enrichment?: DnaEnrichment;
  coverage_gaps?: string[];
};

export function parseCanonicalScript(raw: string | null | undefined): CanonicalScriptProjection | undefined {
  if (!raw || STATUS_TOKENS.has(raw)) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;
    const rec = parsed as Record<string, unknown>;
    if (rec.kind !== "CANONICAL_SCRIPT") return undefined;
    const version = typeof rec.version === "string" ? rec.version.trim() : "";
    const hash = typeof rec.hash === "string" ? rec.hash.trim() : "";
    if (!version || !hash) return undefined;
    const text = (key: string) => (typeof rec[key] === "string" ? String(rec[key]).trim() : "");
    const structureRec = rec.structure && typeof rec.structure === "object" ? (rec.structure as Record<string, unknown>) : undefined;
    const scenes = parseScenesField(structureRec?.scenes);
    const boundaryRec = structureRec?.boundary && typeof structureRec.boundary === "object" ? (structureRec.boundary as Record<string, unknown>) : undefined;
    const boundaryText = (key: string) => (boundaryRec && typeof boundaryRec[key] === "string" ? String(boundaryRec[key]) : "");
    const structure = scenes
      ? {
          scenes,
          boundary: {
            withheld: boundaryText("withheld"),
            open_loop: boundaryText("open_loop"),
            expected_audience_effect: boundaryText("expected_audience_effect"),
            next_content_pull: boundaryText("next_content_pull"),
            next_start_state: boundaryText("next_start_state"),
            payoff_target: boundaryText("payoff_target"),
          },
        }
      : undefined;
    const continuityRec = rec.continuity && typeof rec.continuity === "object" ? (rec.continuity as Record<string, unknown>) : undefined;
    const continuityText = (key: string) => (continuityRec && typeof continuityRec[key] === "string" ? String(continuityRec[key]) : "");
    const continuity = continuityRec
      ? {
          starting_state: continuityText("starting_state"),
          ending_state: continuityText("ending_state"),
          unresolved_refs: continuityText("unresolved_refs"),
          payoff_refs: continuityText("payoff_refs"),
        }
      : undefined;
    const auditRec = rec.audit && typeof rec.audit === "object" ? (rec.audit as Record<string, unknown>) : undefined;
    const audit = auditRec
      ? {
          human_decision: typeof auditRec.human_decision === "string" ? auditRec.human_decision : "",
          candidate_ref: typeof auditRec.candidate_ref === "string" ? auditRec.candidate_ref : undefined,
          reviewer_ref: typeof auditRec.reviewer_ref === "string" ? auditRec.reviewer_ref : undefined,
          decided_at: typeof auditRec.decided_at === "string" ? auditRec.decided_at : "",
        }
      : undefined;
    const coverageGaps = Array.isArray(rec.coverage_gaps)
      ? rec.coverage_gaps.filter((row): row is string => typeof row === "string")
      : undefined;
    return {
      kind: "CANONICAL_SCRIPT",
      canonical_script_id: text("canonical_script_id"),
      version,
      project_id: text("project_id"),
      topic_id: text("topic_id"),
      blueprint_ref: text("blueprint_ref"),
      topic_scope_ref: text("topic_scope_ref"),
      canon_refs: text("canon_refs"),
      dna_ref: text("dna_ref"),
      source_candidate_ref: text("source_candidate_ref"),
      hash,
      change_summary: text("change_summary") || undefined,
      prior_version_ref: text("prior_version_ref") || undefined,
      structure,
      continuity,
      audit,
      machine: parseMachineScriptField(rec.machine),
      views: parseMediaViewsField(rec.views),
      dna_enrichment: parseDnaEnrichmentField(rec.dna_enrichment),
      coverage_gaps: coverageGaps,
    };
  } catch {
    return undefined;
  }
}

export function canonicalScriptRef(value: string | null | undefined): string {
  const parsed = parseCanonicalScript(value);
  if (parsed) return parsed.version;
  return exactName(value);
}

export function serializeCanonicalScript(script: CanonicalScriptProjection): string {
  return JSON.stringify(script);
}

function projectValidated(current: (uid: string) => string | null): boolean {
  return current("CORE-01-BTN-PROJECT-VALIDATE") === "validated" && Boolean(exactName(current("CORE-01-CTL-PROJECT")));
}

function projectConfirmed(current: (uid: string) => string | null): boolean {
  const project = exactName(current("CORE-01-CTL-PROJECT"));
  if (!project) return false;
  return current("CORE-01-BTN-PROJECT-CONFIRM") === "confirmed" || current("CORE-01-BTN-PROJECT-LOCK") === project;
}

export function buildCanonicalScript(current: (uid: string) => string | null): CanonicalScriptProjection | undefined {
  const project = exactName(current("CORE-01-CTL-PROJECT"));
  const topic = exactName(current("CORE-01-CTL-TOPIC"));
  const candidate = exactName(current("CORE-01-FLD-VERSION-STATE"));
  if (!project || !topic || !candidate || !projectConfirmed(current)) return undefined;
  const blueprint = exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
  const topicScope = exactName(current("CORE-01-FLD-TOPIC-SCOPE")) || topic;
  const dna = dnaExactRef(current("CORE-01-BTN-DNA-LOCK")) || exactName(current("CORE-01-BTN-DNA-LOCK"));
  const canon = [project, topic, blueprint, dna].filter(Boolean).join("、");
  const hash = sourceHash([project, topic, topicScope, blueprint, dna, candidate, canon]);
  return {
    kind: "CANONICAL_SCRIPT",
    canonical_script_id: `CS-${hash}`,
    version: `CSV-${hash}`,
    project_id: project,
    topic_id: topic,
    blueprint_ref: blueprint,
    topic_scope_ref: topicScope,
    canon_refs: canon,
    dna_ref: dna,
    source_candidate_ref: candidate,
    hash,
  };
}

export function parseNotebookRecords(raw: string | null): CoreNotebookRecord[] {
  return kernelParseNotebookRecords(raw);
}

export function notebookTextForThread(raw: string | null, thread: string): string {
  return kernelNotebookTextForThread(raw, thread);
}

export function refreshAssistantNotebook(
  current: (uid: string) => string | null,
  thread: string,
  records: CoreMessageRecord[],
  mode: "overflow" | "record" = "overflow",
): Record<string, string> {
  return refreshAssistantNotebookFor(CORE_CONVERSATION, current, thread, records, mode);
}

export function formatCoreChatContext(current: (uid: string) => string | null): string {
  return formatConversationContext(CORE_CONVERSATION, current);
}

export function appendAssistantMessage(
  current: (uid: string) => string | null,
  thread: string,
  reply: string,
  alias?: string,
  at?: string,
  route?: string,
): Record<string, string> {
  return appendAssistantMessageFor(CORE_CONVERSATION, current, thread, reply, alias, at, route);
}

export function appendAssistantMessages(
  current: (uid: string) => string | null,
  thread: string,
  replies: Array<{ text: string; alias?: string; at?: string; route?: string }>,
): Record<string, string> {
  return appendAssistantMessagesFor(CORE_CONVERSATION, current, thread, replies);
}

export function persistConversationTasks(
  current: (uid: string) => string | null,
  tasks: import("./conversationTask").ConversationTaskContract[],
): Record<string, string> {
  return kernelPersistConversationTasksFor(CORE_CONVERSATION, current, tasks);
}

export function contextFingerprint(current: (uid: string) => string | null): string {
  return conversationFingerprint(CORE_CONVERSATION, current);
}

export function contextSnapshotRef(current: (uid: string) => string | null): string {
  return conversationSnapshotRef(CORE_CONVERSATION, current);
}

export function buildResumePointer(
  current: (uid: string) => string | null,
  thread: CoreThreadRecord,
  reason: string,
  status: CoreResumeStatus = "CURRENT",
): CoreResumePointer {
  return buildResumePointerFor(CORE_CONVERSATION, current, thread, reason, status);
}

export function persistResumeOnThreads(
  current: (uid: string) => string | null,
  threadTitle: string,
  reason: string,
  records?: CoreThreadRecord[],
): Record<string, string> {
  return persistResumeOnThreadsFor(CORE_CONVERSATION, current, threadTitle, reason, records);
}

export function resolveResumePointer(
  current: (uid: string) => string | null,
  threadTitle?: string,
): CoreResumePointer | null {
  return resolveResumePointerFor(CORE_CONVERSATION, current, threadTitle);
}

export function parseThreadRecords(raw: string | null): CoreThreadRecord[] {
  return kernelParseThreadRecords(raw);
}

export function currentWorkItem(current: (uid: string) => string | null): string {
  return workItemFor(CORE_CONVERSATION, current);
}

export function threadScopeReady(current: (uid: string) => string | null): boolean {
  return threadScopeReadyFor(CORE_CONVERSATION, current);
}

export function threadsForCurrentWorkItem(current: (uid: string) => string | null): CoreThreadRecord[] {
  return threadsForWorkItem(CORE_CONVERSATION, current);
}

export function activeThreadUid(current: (uid: string) => string | null): string {
  return activeThreadUidFor(CORE_CONVERSATION, current);
}

export function targetedParticipantAliases(
  tokens: CoreResolvedToken[],
  current: (uid: string) => string | null,
): string[] {
  return targetedParticipantAliasesFor(CORE_CONVERSATION, tokens, current);
}

export function resolveComposerTokens(text: string, current: (uid: string) => string | null): CoreResolvedToken[] {
  return resolveComposerTokensFor(CORE_CONVERSATION, text, current);
}

export function previewMessageAction(
  actionUid: string,
  current: (uid: string) => string | null,
  messageRef?: string,
): Record<string, string> {
  return previewMessageActionFor(CORE_CONVERSATION, actionUid, current, messageRef);
}

export function statusFromAction(actionUid: string): string {
  const token = actionUid.split("-").pop() ?? actionUid;
  const map: Record<string, string> = {
    CREATE: "created",
    SELECT: "selected",
    VALIDATE: "validated",
    CONFIRM: "confirmed",
    APPROVE: "approved",
    LOCK: "locked",
    SEND: "sent",
    SEARCH: "queried",
    OPEN: "open",
    EDIT: "editing",
    SAVE: "saved",
    PREVIEW: "preview",
    COMPLETE: "completed",
    EXECUTE: "running",
    RETRY: "retrying",
    EVALUATE: "evaluated",
    MODIFY: "returned",
    COMPARE: "comparing",
    ATTACHMENT: "attached",
    RECORD: "recorded",
    VIEW: "preview",
    ATTACH: "attached",
    SUBMIT: "sent",
    RETURN: "returned",
    CANDIDATE: "created",
  };
  const tokens = new Set(actionUid.split("-"));
  for (const [key, value] of Object.entries(map)) {
    if (tokens.has(key)) return value;
  }
  return token.toLowerCase();
}

export function previewCoreAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  if (controlUid === "CORE-01-FLD-ASSIGNED-AI") return {};
  const conversation = previewConversationAction(CORE_CONVERSATION, controlUid, actionUid, current, nextValue);
  if (conversation) return conversation;
  if (actionUid === "CORE-01-ACT-PROJECT-RENAME") {
    let from = "";
    let to = "";
    try {
      const parsed = JSON.parse(nextValue || "null") as { from?: unknown; to?: unknown } | null;
      from = exactName(typeof parsed?.from === "string" ? parsed.from : "");
      to = exactName(typeof parsed?.to === "string" ? parsed.to : "");
    } catch {
      from = "";
      to = "";
    }
    if (!from || !to || from === to) return {};
    const list = namedList(current("CORE-01-BTN-PROJECT-CREATE"), current("CORE-01-CTL-PROJECT"));
    if (!list.includes(from)) return {};
    const nextList = [...new Set(list.map((row) => (row === from ? to : row)))];
    const active = exactName(current("CORE-01-CTL-PROJECT"));
    return {
      "CORE-01-BTN-PROJECT-CREATE": JSON.stringify(nextList),
      ...(active === from ? { "CORE-01-CTL-PROJECT": to } : {}),
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-DELETE") {
    const target = exactName(nextValue);
    if (!target) return {};
    const list = namedList(current("CORE-01-BTN-PROJECT-CREATE"), current("CORE-01-CTL-PROJECT"));
    if (!list.includes(target)) return {};
    const nextList = list.filter((row) => row !== target);
    const active = exactName(current("CORE-01-CTL-PROJECT"));
    if (active !== target) {
      return { "CORE-01-BTN-PROJECT-CREATE": JSON.stringify(nextList) };
    }
    return {
      "CORE-01-BTN-PROJECT-CREATE": JSON.stringify(nextList),
      "CORE-01-CTL-PROJECT": "",
      "CORE-01-FLD-PAGE-MODE": "",
      "CORE-01-FLD-NAMING-AUTHORITY": "",
      "CORE-01-FLD-RUNTIME-STAGE": "",
      "CORE-01-LST-WORK-ITEMS": "",
      "CORE-01-BTN-PROJECT-CONFIRM": "",
      "CORE-01-BTN-PROJECT-VALIDATE": "",
      "CORE-01-CTL-TOPIC": "",
      "CORE-01-FLD-TOPIC-SCOPE": "",
      "CORE-01-BTN-CANONICAL-SCRIPT": "",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-CREATE") {
    const project = namedValue(nextValue, "新專案");
    const list = namedList(current("CORE-01-BTN-PROJECT-CREATE"), current("CORE-01-CTL-PROJECT"));
    const nextList = list.includes(project) ? list : [...list, project];
    return {
      "CORE-01-CTL-PROJECT": project,
      "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
      "CORE-01-FLD-NAMING-AUTHORITY": "ACPOS_SYSTEM",
      "CORE-01-FLD-RUNTIME-STAGE": "AI_RESPONSES",
      "CORE-01-LST-WORK-ITEMS": "STORY",
      "CORE-01-BTN-PROJECT-CREATE": JSON.stringify(nextList),
      "CORE-01-BTN-PROJECT-CONFIRM": "",
      "CORE-01-BTN-PROJECT-VALIDATE": "",
      "CORE-01-CTL-TOPIC": "",
      "CORE-01-BTN-TOPIC-CREATE": "[]",
      "CORE-01-FLD-TOPIC-SCOPE": "",
      "CORE-01-BTN-CANONICAL-SCRIPT": "",
    };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-CREATE") {
    if (!projectConfirmed(current)) {
      return { "CORE-01-FLD-RUNTIME-STAGE": "TOPIC_LINEAGE_BLOCKED" };
    }
    const topic = exactName(nextValue);
    if (!topic) return {};
    const list = namedList(current("CORE-01-BTN-TOPIC-CREATE"), current("CORE-01-CTL-TOPIC"));
    const nextList = list.includes(topic) ? list : [...list, topic];
    const pkg = exactName(current("CORE-01-FLD-PACKAGE")) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    return {
      "CORE-01-CTL-TOPIC": topic,
      "CORE-01-FLD-PAGE-MODE": "TOPIC_PRODUCTION",
      "CORE-01-FLD-TOPIC-SCOPE": topic,
      "CORE-01-LST-WORK-ITEMS": "TOPIC_SCOPE",
      ...(pkg ? { "CORE-01-FLD-PACKAGE": pkg } : {}),
      "CORE-01-BTN-TOPIC-CREATE": JSON.stringify(nextList),
    };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-DELETE") {
    if (!projectConfirmed(current)) return {};
    const target = exactName(current("CORE-01-CTL-TOPIC"));
    if (!target) return {};
    const list = namedList(current("CORE-01-BTN-TOPIC-CREATE"), current("CORE-01-CTL-TOPIC"));
    if (!list.includes(target)) return {};
    return {
      "CORE-01-BTN-TOPIC-CREATE": JSON.stringify(list.filter((row) => row !== target)),
      "CORE-01-CTL-TOPIC": "",
      "CORE-01-FLD-TOPIC-SCOPE": "",
      "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
      "CORE-01-LST-WORK-ITEMS": "STORY",
      "CORE-01-BTN-CANONICAL-SCRIPT": "",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-PAGE-MODE") {
    const topic = exactName(current("CORE-01-CTL-TOPIC"));
    if (!topic || !projectConfirmed(current)) {
      return {
        "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
        "CORE-01-LST-WORK-ITEMS": "STORY",
      };
    }
    const mode = current("CORE-01-FLD-PAGE-MODE");
    const next = mode === "TOPIC_PRODUCTION" ? "PROJECT_CORE" : "TOPIC_PRODUCTION";
    return {
      "CORE-01-FLD-PAGE-MODE": next,
      "CORE-01-LST-WORK-ITEMS": next === "TOPIC_PRODUCTION" ? "TOPIC_SCOPE" : "STORY",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-CTL-PROJECT") {
    const previous = current("CORE-01-CTL-PROJECT");
    const project = namedValue(nextValue, previous || "新專案");
    const list = namedList(current("CORE-01-BTN-PROJECT-CREATE"), previous).map((item) =>
      item === previous ? project : item,
    );
    const nextList = list.includes(project) ? list : [...list, project];
    return {
      "CORE-01-CTL-PROJECT": project,
      "CORE-01-FLD-PAGE-MODE": current("CORE-01-FLD-PAGE-MODE") || "PROJECT_CORE",
      "CORE-01-BTN-PROJECT-CREATE": JSON.stringify(nextList),
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-NAMING-AUTHORITY") {
    return { "CORE-01-FLD-NAMING-AUTHORITY": current("CORE-01-FLD-NAMING-AUTHORITY") || "ACPOS_SYSTEM" };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-CTL-TOPIC") {
    if (!projectConfirmed(current)) return {};
    const previous = current("CORE-01-CTL-TOPIC");
    const topic = exactName(nextValue) || exactName(previous);
    if (!topic) return {};
    const list = namedList(current("CORE-01-BTN-TOPIC-CREATE"), previous).map((item) =>
      item === previous ? topic : item,
    );
    const nextList = list.includes(topic) ? list : [...list, topic];
    return {
      "CORE-01-CTL-TOPIC": topic,
      "CORE-01-FLD-PAGE-MODE": "TOPIC_PRODUCTION",
      "CORE-01-FLD-TOPIC-SCOPE": topic,
      "CORE-01-BTN-TOPIC-CREATE": JSON.stringify(nextList),
    };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-FLD-TOPIC-SCOPE") {
    if (!projectConfirmed(current)) return {};
    const topic =
      exactName(nextValue) || exactName(current("CORE-01-CTL-TOPIC")) || exactName(current("CORE-01-FLD-TOPIC-SCOPE"));
    return topic ? { "CORE-01-FLD-TOPIC-SCOPE": topic } : {};
  }
  if (actionUid === "CORE-01-ACT-AI-MODE-SINGLE") {
    return {
      "CORE-01-BTN-SINGLE-AI": "active",
      "CORE-01-BTN-MULTI-AI": "idle",
    };
  }
  if (actionUid === "CORE-01-ACT-AI-MODE-MULTI") {
    if (!assignedMultiRouteReady(current)) return {};
    return {
      "CORE-01-BTN-MULTI-AI": "active",
      "CORE-01-BTN-SINGLE-AI": "idle",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-VALIDATE") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    return project ? { "CORE-01-BTN-PROJECT-VALIDATE": "validated" } : {};
  }
  if (actionUid === "CORE-01-ACT-PROJECT-CONFIRM") {
    if (!projectValidated(current)) return {};
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    return project
      ? {
          "CORE-01-BTN-PROJECT-CONFIRM": "confirmed",
          "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
          ...(current("CORE-01-FLD-RUNTIME-STAGE") === "TOPIC_LINEAGE_BLOCKED"
            ? { "CORE-01-FLD-RUNTIME-STAGE": "AI_RESPONSES" }
            : {}),
        }
      : {};
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-CREATE") {
    const candidate = namedValue(nextValue, "候選版本");
    return {
      "CORE-01-FLD-VERSION-STATE": candidate,
      "CORE-01-BTN-CANDIDATE-CREATE": "created",
      "CORE-01-FLD-RUNTIME-STAGE": "CANDIDATE",
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-ACCEPT") {
    const candidate = exactName(current("CORE-01-FLD-VERSION-STATE"));
    if (!candidate) return {};
    const patched = (uid: string) => (uid === "CORE-01-BTN-CANDIDATE-CONFIRM" ? "confirmed" : current(uid));
    const script = buildCanonicalScript(patched);
    const priorDoc = parseCanonicalScript(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    const priorRef =
      priorDoc && script && priorDoc.version !== script.version ? priorDoc.version : priorDoc?.prior_version_ref;
    return {
      "CORE-01-BTN-CANDIDATE-CONFIRM": "confirmed",
      "CORE-01-FLD-LOCK-REVIEW": "ready",
      "CORE-01-FLD-HUMAN-DECISION": current("CORE-01-FLD-HUMAN-DECISION") || "confirmed",
      ...(script
        ? { "CORE-01-BTN-CANONICAL-SCRIPT": serializeCanonicalScript({ ...script, prior_version_ref: priorRef }) }
        : {}),
    };
  }
  if (actionUid === "CORE-01-ACT-STORY-CANDIDATE") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    if (!project) return {};
    const candidate = namedValue(nextValue, current("CORE-01-FLD-VERSION-STATE") || "故事候選");
    return {
      "CORE-01-BTN-STORY-CANDIDATE": "created",
      "CORE-01-FLD-VERSION-STATE": candidate,
      "CORE-01-LST-WORK-ITEMS": "STORY",
      "CORE-01-FLD-RUNTIME-STAGE": "CANDIDATE",
      "CORE-01-BTN-CANDIDATE-CREATE": current("CORE-01-BTN-CANDIDATE-CREATE") || "created",
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-RETURN") {
    const candidate = exactName(current("CORE-01-FLD-VERSION-STATE"));
    if (!candidate) return {};
    return {
      "CORE-01-BTN-RETURN-MODIFY": "returned",
      "CORE-01-BTN-CANDIDATE-CONFIRM": "",
      "CORE-01-FLD-LOCK-REVIEW": "",
      "CORE-01-FLD-RUNTIME-STAGE": "HUMAN_DECISION",
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-COMPARE") {
    const candidate = exactName(current("CORE-01-FLD-VERSION-STATE"));
    if (!candidate) return {};
    const projection = parseCanonicalScript(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    const at = new Date().toISOString().slice(0, 19).replace("T", " ");
    const lhs = [
      ["candidate", candidate, projection?.source_candidate_ref ?? ""],
      ["blueprint", exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE")), projection?.blueprint_ref ?? ""],
      ["dna_lock", dnaExactRef(current("CORE-01-BTN-DNA-LOCK")) || exactName(current("CORE-01-BTN-DNA-LOCK")), projection?.dna_ref ?? ""],
    ] as const;
    const differences = lhs
      .filter(([, candidateValue, canonicalValue]) => candidateValue && canonicalValue && candidateValue !== canonicalValue)
      .map(([field, candidateValue, canonicalValue]) => ({ field, candidate_value: candidateValue, canonical_value: canonicalValue }));
    const comparison = {
      kind: "CORE_COMPARE" as const,
      at,
      candidate,
      canonical_version: projection?.version ?? "",
      canonical_hash: projection?.hash ?? "",
      differences,
      coverage_gaps: projection ? [] : ["canonical_projection_missing"],
    };
    return {
      "CORE-01-BTN-CANDIDATE-COMPARE": "comparing",
      "CORE-01-FLD-EVALUATION": JSON.stringify(comparison),
      "CORE-01-FLD-RUNTIME-STAGE": "CORE_EVALUATION",
    };
  }
  if (actionUid === "CORE-01-ACT-HUMAN-DECISION-RECORD") {
    const decision = exactName(nextValue) || current("CORE-01-FLD-HUMAN-DECISION") || "recorded";
    const at = new Date().toISOString().slice(0, 19).replace("T", " ");
    return {
      "CORE-01-FLD-HUMAN-DECISION": decision,
      "CORE-01-FLD-STRUCTURED-DECISION": appendDecisionLog(current("CORE-01-FLD-STRUCTURED-DECISION"), { at, actor: "HUMAN", decision }),
      "CORE-01-FLD-RUNTIME-STAGE": "HUMAN_DECISION",
    };
  }
  if (actionUid === "CORE-01-ACT-ASSISTANT-STRUCTURED-DECISION-CREATE") {
    const decision = exactName(nextValue) || "recorded";
    const at = new Date().toISOString().slice(0, 19).replace("T", " ");
    return {
      "CORE-01-FLD-STRUCTURED-DECISION": appendDecisionLog(current("CORE-01-FLD-STRUCTURED-DECISION"), { at, actor: "ASSISTANT", decision }),
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-EVALUATE") {
    const candidate = exactName(current("CORE-01-FLD-VERSION-STATE"));
    const at = new Date().toISOString().slice(0, 19).replace("T", " ");
    if (!candidate) {
      return {
        "CORE-01-FLD-EVALUATION": exactName(nextValue) || current("CORE-01-FLD-EVALUATION") || "evaluated",
        "CORE-01-FLD-RUNTIME-STAGE": "CORE_EVALUATION",
      };
    }
    const projection = parseCanonicalScript(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    const blueprint = exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
  const dna = dnaExactRef(current("CORE-01-BTN-DNA-LOCK")) || exactName(current("CORE-01-BTN-DNA-LOCK"));
    const evidence = [
      { item: "canonical_script", result: projection ? `pass:${projection.version}` : "fail:missing" },
      { item: "blueprint", result: blueprint ? `pass:${blueprint}` : "fail:missing" },
      { item: "dna_lock", result: dna ? `pass:${dna}` : "fail:missing" },
    ];
    const verdict = evidence.every((row) => row.result.startsWith("pass")) ? "pass" : "blocked";
    const note = exactName(nextValue);
    const evaluation = {
      kind: "CORE_EVALUATION" as const,
      criteria_version: "CORE-CRITERIA-1",
      at,
      candidate,
      evidence,
      verdict,
      ...(note ? { note } : {}),
    };
    return {
      "CORE-01-FLD-EVALUATION": JSON.stringify(evaluation),
      "CORE-01-FLD-RUNTIME-STAGE": "CORE_EVALUATION",
    };
  }
  if (actionUid === "CORE-01-ACT-CANONICAL-SCRIPT-VIEW") {
    return {};
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-CREATE") {
    const blueprint = namedValue(nextValue, current("CORE-01-BTN-BLUEPRINT-CREATE") || "新藍圖");
    return {
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprint,
      "CORE-01-FLD-PACKAGE": blueprint,
    };
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-VALIDATE") {
    const blueprint = exactName(nextValue) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    if (!blueprint) return {};
    const pkg = exactName(current("CORE-01-FLD-PACKAGE")) || blueprint;
    return {
      "CORE-01-BTN-BLUEPRINT-VALIDATE": "validated",
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprint,
      "CORE-01-FLD-PACKAGE": pkg,
    };
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-APPROVE") {
    const blueprint = exactName(nextValue) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    if (!blueprint) return {};
    return {
      "CORE-01-BTN-BLUEPRINT-APPROVE": "approved",
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprint,
      "CORE-01-FLD-PACKAGE": blueprint,
    };
  }
  if (actionUid === "CORE-01-ACT-DNA-LOCK-REQUEST") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    if (!project) return {};
    const rawValue = String(nextValue ?? "").trim();
    const structured = parseBaseDna(rawValue);
    if (structured) {
      return {
        "CORE-01-BTN-DNA-LOCK": serializeBaseDna({ ...structured, status: "CANDIDATE", locked_at: "" }),
        "CORE-01-FLD-RUNTIME-STAGE": "DNA_CANDIDATE",
      };
    }
    const dna = exactName(rawValue) || exactName(current("CORE-01-BTN-DNA-LOCK"));
    if (!dna) return {};
    return { "CORE-01-BTN-DNA-LOCK": dna, "CORE-01-FLD-RUNTIME-STAGE": "DNA_CANDIDATE" };
  }
  if (actionUid === "CORE-01-ACT-CHILD-LOCK-REQUEST") {
    const blueprint = exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
    if (!blueprint) return {};
    return {
      "CORE-01-BTN-CHILD-LOCK": blueprint,
      "CORE-01-FLD-LOCK-REVIEW": "locked",
      "CORE-01-FLD-PACKAGE": blueprint,
      "CORE-01-BTN-BLUEPRINT-CREATE": exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || blueprint,
    };
  }
  if (actionUid === "CORE-01-ACT-CORE-REVIEW-SUBMIT") {
    const at = new Date().toISOString().slice(0, 19).replace("T", " ");
    return {
      "CORE-01-BTN-CORE-REVIEW": "sent",
      "CORE-01-FLD-LOCK-REVIEW": `submitted@${at}`,
      "CORE-01-FLD-RUNTIME-STAGE": "REVIEW",
    };
  }
  if (actionUid === "CORE-01-ACT-MOTHER-LOCK-REQUEST") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    if (!project) return {};
    return {
      "CORE-01-BTN-PROJECT-LOCK": project,
      "CORE-01-FLD-LOCK-REVIEW": "locked",
    };
  }
  if (actionUid === "CORE-01-ACT-ATTACHMENT") {
    return { "CORE-01-BTN-ATTACHMENT": namedValue(nextValue, current("CORE-01-BTN-ATTACHMENT") || "已上傳") };
  }
  if (actionUid === "CORE-01-ACT-REFERENCE-ATTACH") {
    return { "CORE-01-BTN-REFERENCE": namedValue(nextValue, current("CORE-01-BTN-REFERENCE") || "已引用") };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-FLD-PACKAGE") {
    const pkg =
      exactName(nextValue) || exactName(current("CORE-01-FLD-PACKAGE")) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    return pkg ? { "CORE-01-FLD-PACKAGE": pkg } : {};
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid.startsWith("CORE-01-FLD-DOWNSTREAM")) {
    const existing = exactName(current(controlUid));
    return existing ? { [controlUid]: existing } : {};
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-VERSION-STATE") {
    return {
      "CORE-01-FLD-VERSION-STATE": namedValue(nextValue, current("CORE-01-FLD-VERSION-STATE") || "候選版本"),
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-LOCK-REVIEW") {
    return { "CORE-01-FLD-LOCK-REVIEW": namedValue(nextValue, current("CORE-01-FLD-LOCK-REVIEW") || "ready") };
  }
  if (actionUid === "CORE-01-ACT-WORK-ITEM-SELECT") {
    const nextWork = nextValue ?? current("CORE-01-LST-WORK-ITEMS") ?? "STORY";
    if (!WORK_ITEMS.has(nextWork)) return {};
    const matching = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD")).filter((row) => row.workItem === nextWork);
    const stored = current("CORE-01-LST-THREADS");
    const keep =
      stored && matching.some((row) => row.title === stored)
        ? stored
        : matching.filter((row) => row.resume).length === 1
          ? matching.find((row) => row.resume)!.title
          : matching.length === 1
            ? matching[0].title
            : "";
    const patched = (uid: string) => {
      if (uid === "CORE-01-LST-WORK-ITEMS") return nextWork;
      if (uid === "CORE-01-LST-THREADS") return keep;
      return current(uid);
    };
    return {
      "CORE-01-LST-WORK-ITEMS": nextWork,
      "CORE-01-LST-THREADS": keep,
      ...(keep ? persistResumeOnThreads(patched, keep, "WORK_ITEM") : {}),
    };
  }
  if (controlUid === "CORE-01-FLD-RUNTIME-STAGE") {
    return { "CORE-01-FLD-RUNTIME-STAGE": nextValue || current("CORE-01-FLD-RUNTIME-STAGE") || "AI_RESPONSES" };
  }
  if (controlUid === "CORE-01-FLD-MESSAGE" || controlUid === "CORE-01-FLD-ASSISTANT-SUMMARY") {
    return {};
  }
  const existing = current(controlUid);
  if (!nextValue && existing && !STATUS_TOKENS.has(existing) && actionUid.includes("-SELECT")) {
    return { [controlUid]: existing };
  }
  return { [controlUid]: nextValue ?? statusFromAction(actionUid) };
}
