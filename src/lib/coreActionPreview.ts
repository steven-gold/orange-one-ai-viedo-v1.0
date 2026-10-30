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
import { evaluateCoreCandidate, QCP_CORE_PROFILE } from "./coreEvaluation";
import { appendCoreEvent, CORE_EVENT_NAMES } from "./coreEventLog";
import { parseChapterArchitecture, parseStoryCore, serializeChapterArchitecture, serializeStoryCore } from "./storyChapterDocument";
import { appendCoreError, buildCoreError } from "./coreErrorContract";
import { buildProductionPackage, parseProductionPackage, serializeProductionPackage } from "./productionPackage";

function nowStamp(): string {
  return new Date().toISOString().slice(0, 19).replace("T", " ");
}

function stableHash8(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export type IdempotencyEntry = { key: string; result_ref: string; at: string };

function parseIdempotencyLedger(raw: string | null | undefined): IdempotencyEntry[] {
  try {
    const parsed = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed)) {
      return parsed.filter((row) => row && typeof row === "object" && typeof row.key === "string") as IdempotencyEntry[];
    }
  } catch {
    return [];
  }
  return [];
}

function idempotencySeen(raw: string | null | undefined, key: string): boolean {
  return parseIdempotencyLedger(raw).some((row) => row.key === key);
}

function recordIdempotency(raw: string | null | undefined, key: string, resultRef: string, at: string): string {
  const ledger = parseIdempotencyLedger(raw).filter((row) => row.key !== key);
  ledger.push({ key, result_ref: resultRef, at });
  return JSON.stringify(ledger.slice(-50));
}

function parseExpectedVersion(nextValue: unknown): string {
  const raw = String(nextValue ?? "").trim();
  if (!raw.startsWith("{")) return "";
  try {
    const parsed = JSON.parse(raw) as { expected_version?: unknown };
    return typeof parsed.expected_version === "string" ? parsed.expected_version : "";
  } catch {
    return "";
  }
}

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

export function blueprintExactRef(value: string | null | undefined): string {
  const raw = value?.trim() ?? "";
  if (!raw || STATUS_TOKENS.has(raw)) return "";
  try {
    const parsed = JSON.parse(raw) as { version?: unknown; name?: unknown };
    if (parsed && typeof parsed.version === "string" && parsed.version.trim()) return parsed.version.trim();
    if (parsed && typeof parsed.name === "string" && parsed.name.trim()) return parsed.name.trim();
  } catch {
    return exactName(raw);
  }
  return exactName(raw);
}

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
            tension_state: boundaryText("tension_state"),
            hook_intent: boundaryText("hook_intent"),
            curiosity_gap: boundaryText("curiosity_gap"),
            cut_setup: boundaryText("cut_setup"),
            visual_buildup: boundaryText("visual_buildup"),
            audio_buildup: boundaryText("audio_buildup"),
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
  const blueprint = blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
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
  const result = previewCoreActionFields(controlUid, actionUid, current, nextValue);
  return withCoreEventLog(actionUid, current, result);
}

type CoreEventRule = { events: Array<{ name: string; when?: (current: (uid: string) => string | null) => boolean }>; require: string; reset?: boolean };

function changeRequestOpen(current: (uid: string) => string | null): boolean {
  try {
    const parsed = JSON.parse(current("CORE-01-FLD-CHANGE-REQUEST") || "null") as { status?: unknown } | null;
    return parsed?.status === "CHANGE_REQUESTED";
  } catch {
    return false;
  }
}

const CORE_EVENT_RULES: Record<string, CoreEventRule> = {
  "CORE-01-ACT-PROJECT-CREATE": { events: [{ name: CORE_EVENT_NAMES.project_created }], require: "CORE-01-BTN-PROJECT-CREATE", reset: true },
  "CORE-01-ACT-TOPIC-CREATE": { events: [{ name: CORE_EVENT_NAMES.topic_scope_confirmed }], require: "CORE-01-BTN-TOPIC-CREATE" },
  "CORE-01-ACT-CANDIDATE-CREATE": { events: [{ name: CORE_EVENT_NAMES.story_candidate_set_created }], require: "CORE-01-BTN-CANDIDATE-CREATE" },
  "CORE-01-ACT-STORY-CANDIDATE": { events: [{ name: CORE_EVENT_NAMES.story_candidate_set_created }], require: "CORE-01-BTN-STORY-CANDIDATE" },
  "CORE-01-ACT-CANDIDATE-COMPARE": { events: [{ name: CORE_EVENT_NAMES.story_candidates_compared }], require: "CORE-01-FLD-EVALUATION" },
  "CORE-01-ACT-CANDIDATE-ACCEPT": { events: [{ name: CORE_EVENT_NAMES.story_core_adopted }, { name: CORE_EVENT_NAMES.script_version_created }], require: "CORE-01-BTN-CANONICAL-SCRIPT" },
  "CORE-01-ACT-CANDIDATE-RETURN": { events: [{ name: CORE_EVENT_NAMES.story_revision_requested }], require: "CORE-01-BTN-RETURN-MODIFY" },
  "CORE-01-ACT-CHAPTER-ARCH-REQUEST": { events: [{ name: CORE_EVENT_NAMES.chapter_architecture_version_created }], require: "CORE-01-BTN-CHAPTER-ARCH" },
  "CORE-01-ACT-DNA-LOCK-REQUEST": { events: [{ name: CORE_EVENT_NAMES.dna_candidate_created }, { name: CORE_EVENT_NAMES.dna_lock_requested }], require: "CORE-01-BTN-DNA-LOCK" },
  "CORE-01-ACT-MOTHER-LOCK-APPROVE": { events: [{ name: CORE_EVENT_NAMES.project_lock_approved }, { name: CORE_EVENT_NAMES.dna_resolved }], require: "CORE-01-BTN-PROJECT-LOCK" },
  "CORE-01-ACT-CHILD-LOCK-REQUEST": { events: [{ name: CORE_EVENT_NAMES.topic_child_lock_requested }], require: "CORE-01-BTN-CHILD-LOCK" },
  "CORE-01-ACT-CHILD-LOCK-APPROVE": { events: [{ name: CORE_EVENT_NAMES.topic_blueprint_locked }], require: "CORE-01-BTN-CHILD-LOCK" },
  "CORE-01-ACT-BLUEPRINT-CREATE": { events: [{ name: CORE_EVENT_NAMES.topic_blueprint_candidate_created }], require: "CORE-01-BTN-BLUEPRINT-CREATE" },
  "CORE-01-ACT-PACKAGE-BUILD": { events: [{ name: CORE_EVENT_NAMES.production_package_ready }], require: "CORE-01-FLD-PACKAGE" },
  "CORE-01-ACT-CHANGE-REQUEST": { events: [{ name: CORE_EVENT_NAMES.core_change_requested }], require: "CORE-01-FLD-CHANGE-REQUEST" },
  "CORE-01-ACT-MOTHER-LOCK-REQUEST": { events: [{ name: CORE_EVENT_NAMES.core_version_superseded, when: changeRequestOpen }], require: "CORE-01-BTN-PROJECT-LOCK" },
};

function withCoreEventLog(
  actionUid: string,
  current: (uid: string) => string | null,
  result: Record<string, string>,
): Record<string, string> {
  const rule = CORE_EVENT_RULES[actionUid];
  if (!rule) return result;
  if (Object.keys(result).length === 0) return result;
  if (!Object.prototype.hasOwnProperty.call(result, rule.require)) return result;
  const at = nowStamp();
  let log = rule.reset ? "" : current("CORE-01-FLD-EVENT-LOG") ?? "";
  for (const entry of rule.events) {
    if (entry.when && !entry.when(current)) continue;
    log = appendCoreEvent(log, entry.name, String(result[rule.require] ?? ""), at);
  }
  if (result["CORE-01-FLD-EVENT-LOG"] === log) return result;
  return { ...result, "CORE-01-FLD-EVENT-LOG": log };
}

function previewCoreActionFields(
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
      "CORE-01-FLD-LIFECYCLE-STAGE": "PROJECT_DRAFT",
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
      return {
        "CORE-01-FLD-RUNTIME-STAGE": "TOPIC_LINEAGE_BLOCKED",
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_CONTEXT_INVALID", "TOPIC-CREATE: project unconfirmed (lineage guard §24)", nowStamp())!,
        ),
      };
    }
    const topic = exactName(nextValue);
    if (!topic) return {};
    const list = namedList(current("CORE-01-BTN-TOPIC-CREATE"), current("CORE-01-CTL-TOPIC"));
    const nextList = list.includes(topic) ? list : [...list, topic];
    const pkg = exactName(current("CORE-01-FLD-PACKAGE")) || blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    return {
      "CORE-01-CTL-TOPIC": topic,
      "CORE-01-FLD-PAGE-MODE": "TOPIC_PRODUCTION",
      "CORE-01-FLD-TOPIC-SCOPE": topic,
      "CORE-01-LST-WORK-ITEMS": "TOPIC_SCOPE",
      "CORE-01-FLD-LIFECYCLE-STAGE": pkg ? "PACKAGE_READY" : "TOPIC_DRAFT",
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
    return project
      ? { "CORE-01-BTN-PROJECT-VALIDATE": "validated", "CORE-01-FLD-LIFECYCLE-STAGE": "PROJECT_VALIDATING" }
      : {};
  }
  if (actionUid === "CORE-01-ACT-PROJECT-CONFIRM") {
    if (!projectValidated(current)) return {};
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    return project
      ? {
          "CORE-01-BTN-PROJECT-CONFIRM": "confirmed",
          "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
          "CORE-01-FLD-LIFECYCLE-STAGE": "CORE_MODELING",
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
      "CORE-01-FLD-LIFECYCLE-STAGE": "SCRIPT_CANDIDATE",
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-ACCEPT") {
    const candidate = exactName(current("CORE-01-FLD-VERSION-STATE"));
    if (!candidate) return {};
    const priorDoc = parseCanonicalScript(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    const expected = parseExpectedVersion(nextValue);
    if (expected && priorDoc && expected !== priorDoc.version) {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_VERSION_CONFLICT", `CANDIDATE-ACCEPT: expected=${expected} current=${priorDoc.version}; recompare`, nowStamp())!,
        ),
      };
    }
    const patched = (uid: string) => (uid === "CORE-01-BTN-CANDIDATE-CONFIRM" ? "confirmed" : current(uid));
    const script = buildCanonicalScript(patched);
    if (priorDoc && script && script.version === priorDoc.version) {
      const versionKey = `ACCEPT:${script.version}`;
      const base = {
        "CORE-01-BTN-CANDIDATE-CONFIRM": "confirmed",
        "CORE-01-FLD-LOCK-REVIEW": "ready",
        "CORE-01-FLD-HUMAN-DECISION": current("CORE-01-FLD-HUMAN-DECISION") || "confirmed",
      };
      if (idempotencySeen(current("CORE-01-FLD-IDEMPOTENCY"), versionKey)) return base;
      return { ...base, "CORE-01-FLD-IDEMPOTENCY": recordIdempotency(current("CORE-01-FLD-IDEMPOTENCY"), versionKey, script.version, nowStamp()) };
    }
    const priorRef =
      priorDoc && script && priorDoc.version !== script.version ? priorDoc.version : priorDoc?.prior_version_ref;
    return {
      "CORE-01-BTN-CANDIDATE-CONFIRM": "confirmed",
      "CORE-01-FLD-LOCK-REVIEW": "ready",
      "CORE-01-FLD-HUMAN-DECISION": current("CORE-01-FLD-HUMAN-DECISION") || "confirmed",
      "CORE-01-FLD-IDEMPOTENCY": recordIdempotency(current("CORE-01-FLD-IDEMPOTENCY"), `ACCEPT:${script?.version ?? candidate}`, script?.version ?? "", nowStamp()),
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
      "CORE-01-FLD-LIFECYCLE-STAGE": "SCRIPT_CANDIDATE",
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
      "CORE-01-FLD-LIFECYCLE-STAGE": "REVISION_REQUIRED",
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-COMPARE") {
    const candidate = exactName(current("CORE-01-FLD-VERSION-STATE"));
    if (!candidate) return {};
    const projection = parseCanonicalScript(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    const at = new Date().toISOString().slice(0, 19).replace("T", " ");
    const lhs = [
      ["candidate", candidate, projection?.source_candidate_ref ?? ""],
      ["blueprint", blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE")), projection?.blueprint_ref ?? ""],
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
    const blueprint = blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
    const dna = current("CORE-01-BTN-DNA-LOCK");
    const namingAuthority = exactName(current("CORE-01-FLD-NAMING-AUTHORITY"));
    const note = exactName(nextValue);
    const evaluation = evaluateCoreCandidate({
      candidate,
      projection,
      blueprint,
      dnaRaw: dna,
      namingAuthority,
      at,
      ...(note ? { note } : {}),
    });
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
      "CORE-01-FLD-LIFECYCLE-STAGE": "BOUNDARY_DECISION",
    };
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-VALIDATE") {
    const blueprint = blueprintExactRef(nextValue) || blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    if (!blueprint) return {};
    const pkg = exactName(current("CORE-01-FLD-PACKAGE")) || blueprint;
    const existingRaw = current("CORE-01-BTN-BLUEPRINT-CREATE");
    let existing: { name?: unknown } | null = null;
    try {
      existing = existingRaw ? (JSON.parse(existingRaw) as { name?: unknown }) : null;
    } catch {
      existing = null;
    }
    const baseName = existing && typeof existing.name === "string" ? existing.name : blueprint;
    const projection = parseCanonicalScript(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    const layers = {
      project_structure: {
        project: exactName(current("CORE-01-FLD-PROJECT")) || "unset",
        structure_lock: current("CORE-01-FLD-LIFECYCLE-STAGE") === "PROJECT_LOCKED" ? "locked" : "unlocked",
        base_dna: current("CORE-01-BTN-DNA-LOCK") ? "present" : "unset",
        canon_rules: ["STORY", "WORLD", "CHARACTER", "NARRATIVE"],
      },
      topic_production: {
        topic: current("CORE-01-FLD-TOPIC-LOCK") || current("CORE-01-FLD-TOPIC") || "unset",
        topic_lock: current("CORE-01-FLD-LIFECYCLE-STAGE") === "TOPIC_LOCKED" ? "locked" : "unlocked",
        canonical_script: projection ? projection.version : "unset",
        views: (projection?.views?.views ?? []).map((view) => view.view),
        continuity: projection?.continuity ? "present" : "unset",
        qa_criteria: QCP_CORE_PROFILE,
        dependency_closure: "topic_exact_refs",
      },
    };
    const blueprintJson = JSON.stringify({ name: baseName, version: blueprint, layers });
    return {
      "CORE-01-BTN-BLUEPRINT-VALIDATE": "validated",
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprintJson,
      "CORE-01-FLD-PACKAGE": pkg,
      "CORE-01-FLD-LIFECYCLE-STAGE": "SCRIPT_DRAFT",
    };
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-APPROVE") {
    const blueprint = blueprintExactRef(nextValue) || blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    if (!blueprint) return {};
    return {
      "CORE-01-BTN-BLUEPRINT-APPROVE": "approved",
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprint,
      "CORE-01-FLD-PACKAGE": blueprint,
      "CORE-01-FLD-LIFECYCLE-STAGE": "TOPIC_BLUEPRINT_CANDIDATE",
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
  if (actionUid === "CORE-01-ACT-STORY-CORE-REQUEST") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    if (!project) return {};
    const rawValue = String(nextValue ?? "").trim();
    const structured = parseStoryCore(rawValue);
    if (structured) {
      return { "CORE-01-BTN-STORY-CORE": serializeStoryCore({ ...structured, status: "CANDIDATE", locked_at: "" }) };
    }
    const story = exactName(rawValue) || exactName(current("CORE-01-BTN-STORY-CORE"));
    if (!story) return {};
    return { "CORE-01-BTN-STORY-CORE": story };
  }
  if (actionUid === "CORE-01-ACT-CHAPTER-ARCH-REQUEST") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    if (!project) return {};
    const rawValue = String(nextValue ?? "").trim();
    const structured = parseChapterArchitecture(rawValue);
    if (structured) {
      return {
        "CORE-01-BTN-CHAPTER-ARCH": serializeChapterArchitecture({ ...structured, status: "CANDIDATE", locked_at: "" }),
      };
    }
    const chapters = exactName(rawValue) || exactName(current("CORE-01-BTN-CHAPTER-ARCH"));
    if (!chapters) return {};
    return { "CORE-01-BTN-CHAPTER-ARCH": chapters };
  }
  if (actionUid === "CORE-01-ACT-PACKAGE-BUILD") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    const topic = exactName(current("CORE-01-CTL-TOPIC"));
    if (!project || !topic) {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_CONTEXT_INVALID", "PACKAGE-BUILD: project/topic unresolved", nowStamp())!,
        ),
      };
    }
    if (current("CORE-01-FLD-LIFECYCLE-STAGE") !== "TOPIC_LOCKED") {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_BLUEPRINT_INCOMPLETE", `PACKAGE-BUILD: child lock required, lifecycle=${current("CORE-01-FLD-LIFECYCLE-STAGE") || "unset"}`, nowStamp())!,
        ),
      };
    }
    const changeRaw = current("CORE-01-FLD-CHANGE-REQUEST");
    if (changeRaw && changeRaw.startsWith("{")) {
      try {
        const change = JSON.parse(changeRaw) as { kind?: string; status?: string };
        if (change.kind === "CORE_CHANGE_REQUEST" && change.status === "CHANGE_REQUESTED") {
          return {
            "CORE-01-FLD-CORE-ERRORS": appendCoreError(
              current("CORE-01-FLD-CORE-ERRORS"),
              buildCoreError("CORE_VERSION_CONFLICT", "PACKAGE-BUILD: open change request blocks build until re-lock (REVERIFY_REQUIRED)", nowStamp())!,
            ),
          };
        }
      } catch {
        // malformed change request evidence is ignored for the guard
      }
    }
    const at = nowStamp();
    const blueprint = blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE")) || "";
    const dnaDoc = parseBaseDna(current("CORE-01-BTN-DNA-LOCK"));
    const projection = parseCanonicalScript(current("CORE-01-BTN-CANONICAL-SCRIPT")) ?? null;
    const enrichmentHash = projection?.dna_enrichment?.hash ?? "";
    const dnaRefs = [dnaDoc?.version ?? "", enrichmentHash ? `DNAE-${enrichmentHash}` : ""].filter(Boolean);
    const pkg = buildProductionPackage({
      projectId: project,
      topicId: topic,
      basedOnStructureRef: exactName(current("CORE-01-FLD-LOCK-REVIEW")) || "PROJECT_LOCKED",
      blueprintRef: blueprint,
      blueprintLockState: exactName(current("CORE-01-BTN-CHILD-LOCK")) ? "CHILD_LOCKED" : "UNLOCKED",
      dnaRefs: dnaRefs.length ? dnaRefs : [dnaDoc?.version ?? ""],
      projection,
      preboundWorkspaces: {
        asset: exactName(current("CORE-01-FLD-DOWNSTREAM-ASSET")) || "",
        video: exactName(current("CORE-01-FLD-DOWNSTREAM-VIDEO")) || "",
        edit: exactName(current("CORE-01-FLD-DOWNSTREAM-EDIT")) || "",
      },
      namingAuthority: exactName(current("CORE-01-FLD-NAMING-AUTHORITY")) || "",
      candidateRef: projection?.audit?.candidate_ref ?? exactName(current("CORE-01-FLD-VERSION-STATE")) ?? "",
      humanDecision: projection?.audit?.human_decision ?? "",
      lockState: String(current("CORE-01-FLD-LOCK-REVIEW") ?? ""),
      at,
    });
    const existingPkg = parseProductionPackage(current("CORE-01-FLD-PACKAGE"));
    if (existingPkg && existingPkg.version === pkg.version && existingPkg.status !== "BLOCKED") return {};
    return {
      "CORE-01-FLD-PACKAGE": serializeProductionPackage(pkg),
      "CORE-01-FLD-LIFECYCLE-STAGE": "PACKAGE_BUILDING",
      "CORE-01-FLD-CORE-ERRORS": pkg.status === "BLOCKED"
        ? appendCoreError(current("CORE-01-FLD-CORE-ERRORS"), buildCoreError("CORE_PACKAGE_NOT_READY", `PACKAGE-BUILD: ${pkg.readiness.missing_blockers.join(";")}`, at)!)
        : current("CORE-01-FLD-CORE-ERRORS") ?? "",
    };
  }
  if (actionUid === "CORE-01-ACT-PACKAGE-READINESS-VALIDATE") {
    const pkg = parseProductionPackage(current("CORE-01-FLD-PACKAGE"));
    if (!pkg) {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_PACKAGE_NOT_READY", "READINESS: no package built", nowStamp())!,
        ),
      };
    }
    if (pkg.readiness.missing_blockers.length) {
      return {
        "CORE-01-FLD-PACKAGE": serializeProductionPackage({ ...pkg, status: "BLOCKED" }),
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_PACKAGE_NOT_READY", `READINESS: ${pkg.readiness.missing_blockers.join(";")}`, nowStamp())!,
        ),
      };
    }
    return {
      "CORE-01-FLD-PACKAGE": serializeProductionPackage({ ...pkg, status: "READY" }),
      "CORE-01-FLD-LIFECYCLE-STAGE": "PACKAGE_READY",
    };
  }
  if (actionUid === "CORE-01-ACT-PACKAGE-HANDOFF") {
    const pkg = parseProductionPackage(current("CORE-01-FLD-PACKAGE"));
    if (!pkg || pkg.status !== "READY") {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_PACKAGE_NOT_READY", `HANDOFF: package ${pkg?.status ?? "missing"}`, nowStamp())!,
        ),
      };
    }
    if (current("CORE-01-FLD-LIFECYCLE-STAGE") === "HANDED_OFF") return {};
    return {
      "CORE-01-FLD-PACKAGE": serializeProductionPackage({ ...pkg, status: "READY" }),
      "CORE-01-FLD-DOWNSTREAM-ASSET": exactName(current("CORE-01-FLD-DOWNSTREAM-ASSET")) || `ASSET←${pkg.version}`,
      "CORE-01-FLD-DOWNSTREAM-VIDEO": exactName(current("CORE-01-FLD-DOWNSTREAM-VIDEO")) || `VIDEO←${pkg.version}`,
      "CORE-01-FLD-DOWNSTREAM-EDIT": exactName(current("CORE-01-FLD-DOWNSTREAM-EDIT")) || `EDIT←${pkg.version}`,
      "CORE-01-FLD-LIFECYCLE-STAGE": "HANDED_OFF",
      "CORE-01-FLD-CORE-ERRORS": current("CORE-01-FLD-CORE-ERRORS") ?? "",
    };
  }
  if (actionUid === "CORE-01-ACT-CHILD-LOCK-REQUEST") {
    const blueprint = blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
    if (!blueprint) return {};
    if (current("CORE-01-FLD-LIFECYCLE-STAGE") === "CHILD_LOCK_REVIEW") return {};
    return {
      "CORE-01-BTN-CHILD-LOCK": blueprint,
      "CORE-01-FLD-LOCK-REVIEW": `submitted@${nowStamp()}`,
      "CORE-01-FLD-PACKAGE": blueprint,
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE")) || blueprint,
      "CORE-01-FLD-LIFECYCLE-STAGE": "CHILD_LOCK_REVIEW",
    };
  }
  if (actionUid === "CORE-01-ACT-CHILD-LOCK-APPROVE") {
    const review = String(current("CORE-01-FLD-LOCK-REVIEW") ?? "");
    if (!review.startsWith("submitted@")) {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_LOCK_EVIDENCE_MISSING", `CHILD-LOCK-APPROVE: review=${review || "unset"}`, nowStamp())!,
        ),
      };
    }
    const blueprint = exactName(current("CORE-01-BTN-CHILD-LOCK")) || blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
    if (!blueprint) return {};
    return {
      "CORE-01-BTN-CHILD-LOCK": blueprint,
      "CORE-01-FLD-LOCK-REVIEW": "locked",
      "CORE-01-FLD-PACKAGE": blueprint,
      "CORE-01-FLD-LIFECYCLE-STAGE": "TOPIC_LOCKED",
    };
  }
  if (actionUid === "CORE-01-ACT-CHANGE-REQUEST") {
    const lifecycle = String(current("CORE-01-FLD-LIFECYCLE-STAGE") ?? "");
    if (lifecycle !== "PROJECT_LOCKED" && lifecycle !== "TOPIC_LOCKED") {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_VERSION_CONFLICT", `CHANGE-REQUEST: no locked artifact (lifecycle=${lifecycle || "unset"})`, nowStamp())!,
        ),
      };
    }
    const reason = exactName(nextValue);
    if (!reason) {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_DECISION_MISSING", "CHANGE-REQUEST: authorized reason required", nowStamp())!,
        ),
      };
    }
    const at = nowStamp();
    const impacted = [
      "CORE-01-BTN-BLUEPRINT-CREATE",
      "CORE-01-FLD-PACKAGE",
      "CORE-01-BTN-CANONICAL-SCRIPT",
      "CORE-01-BTN-CHILD-LOCK",
    ].filter((uid) => exactName(current(uid)));
    const changeId = `CR-${stableHash8([lifecycle, reason, at])}`;
    return {
      "CORE-01-FLD-CHANGE-REQUEST": JSON.stringify({
        kind: "CORE_CHANGE_REQUEST",
        change_id: changeId,
        change_class: lifecycle === "PROJECT_LOCKED" ? "CANON" : "TOPIC",
        reason,
        impacted,
        status: "CHANGE_REQUESTED",
        at,
      }),
      "CORE-01-FLD-LIFECYCLE-STAGE": "CHANGE_REQUESTED",
    };
  }
  if (actionUid === "CORE-01-ACT-CORE-REVIEW-SUBMIT") {
    const at = new Date().toISOString().slice(0, 19).replace("T", " ");
    return {
      "CORE-01-BTN-CORE-REVIEW": "sent",
      "CORE-01-FLD-LOCK-REVIEW": `submitted@${at}`,
      "CORE-01-FLD-RUNTIME-STAGE": "REVIEW",
      "CORE-01-FLD-LIFECYCLE-STAGE": "PROJECT_REVIEW_PENDING",
    };
  }
  if (actionUid === "CORE-01-ACT-MOTHER-LOCK-REQUEST") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    if (!project) return {};
    if (current("CORE-01-FLD-LIFECYCLE-STAGE") === "MOTHER_LOCK_REVIEW") return {};
    return {
      "CORE-01-BTN-PROJECT-LOCK": project,
      "CORE-01-FLD-LOCK-REVIEW": `submitted@${nowStamp()}`,
      "CORE-01-FLD-LIFECYCLE-STAGE": "MOTHER_LOCK_REVIEW",
    };
  }
  if (actionUid === "CORE-01-ACT-MOTHER-LOCK-APPROVE") {
    const review = String(current("CORE-01-FLD-LOCK-REVIEW") ?? "");
    const project = exactName(current("CORE-01-BTN-PROJECT-LOCK")) || exactName(current("CORE-01-CTL-PROJECT"));
    if (!review.startsWith("submitted@") || !project) {
      return {
        "CORE-01-FLD-CORE-ERRORS": appendCoreError(
          current("CORE-01-FLD-CORE-ERRORS"),
          buildCoreError("CORE_LOCK_EVIDENCE_MISSING", `MOTHER-LOCK-APPROVE: review=${review || "unset"}`, nowStamp())!,
        ),
      };
    }
    const changeRaw = current("CORE-01-FLD-CHANGE-REQUEST");
    let changePatch: Record<string, string> = {};
    if (changeRaw && changeRaw.startsWith("{")) {
      try {
        const change = JSON.parse(changeRaw) as { kind?: string; status?: string; change_id?: string; reason?: string };
        if (change.kind === "CORE_CHANGE_REQUEST" && change.status === "CHANGE_REQUESTED") {
          changePatch = {
            "CORE-01-FLD-CHANGE-REQUEST": JSON.stringify({
              ...change,
              status: "SUPERSEDED",
              superseded_by: project,
              superseded_at: nowStamp(),
            }),
          };
        }
      } catch {
        changePatch = {};
      }
    }
    return {
      "CORE-01-BTN-PROJECT-LOCK": project,
      "CORE-01-FLD-LOCK-REVIEW": "locked",
      "CORE-01-FLD-LIFECYCLE-STAGE": "PROJECT_LOCKED",
      ...changePatch,
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
      exactName(nextValue) || exactName(current("CORE-01-FLD-PACKAGE")) || blueprintExactRef(current("CORE-01-BTN-BLUEPRINT-CREATE"));
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
