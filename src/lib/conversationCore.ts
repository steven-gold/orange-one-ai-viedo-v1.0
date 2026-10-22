const PLACEHOLDER_NAMES = new Set([
  "新專題",
  "未命名專題",
  "New topic",
  "Untitled topic",
]);

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

function usableName(value: string | undefined): string {
  const name = value?.trim();
  if (!name || STATUS_TOKENS.has(name) || PLACEHOLDER_NAMES.has(name)) return "";
  return name.slice(0, 80);
}

export const CONVERSATION_RECENT_HISTORY_ROWS = 30;
export const CONVERSATION_RECENT_HISTORY_TEXT_CHARS = 2200;
export const CONVERSATION_STORED_MESSAGE_TEXT_CHARS = 4000;

export type CurrentFn = (uid: string) => string | null;

export type ConversationBindings = {
  prefix: string;
  extensionUid: string;
  messageUid: string;
  threadStoreUid: string;
  threadListUid: string;
  notebookUid: string;
  sendUid: string;
  assistantUid: string;
  assignedAiUid?: string;
  multiAiUid?: string;
  workItemUid?: string;
  defaultWorkItem: string;
  allowedWorkItems?: ReadonlySet<string>;
  scopeOwnerUid?: string;
  fingerprintUids?: readonly string[];
  humanDecisionUid?: string;
  runtimeStageUid?: string;
  composerUid?: string;
  resolveWorkItem?: (current: CurrentFn) => string;
  scopeReady?: (current: CurrentFn) => boolean;
  contextFingerprint?: (current: CurrentFn) => string;
  contextSnapshotRef?: (current: CurrentFn) => string;
  contextExtra?: (current: CurrentFn) => string[];
  defaultThreadTitle?: (scopedCount: number) => string;
  attachmentUids?: readonly string[];
  strictWorkItem?: boolean;
};

const AI_MODE_TOKENS = new Set(["SINGLE", "MULTI"]);

export function assignedAiRouteLabel(value: string | null | undefined): string {
  const text = (value ?? "").trim();
  if (!text || AI_MODE_TOKENS.has(text) || STATUS_TOKENS.has(text) || PLACEHOLDER_NAMES.has(text)) return "";
  return text;
}

export function conversationAssignedAiReady(bindings: ConversationBindings, current: CurrentFn): boolean {
  if (!bindings.assignedAiUid) return true;
  return Boolean(assignedAiRouteLabel(current(bindings.assignedAiUid)));
}

export function assignedAiRouteParts(value: string | null | undefined): string[] {
  const label = assignedAiRouteLabel(value);
  if (!label) return [];
  const seen = new Set<string>();
  const parts: string[] = [];
  for (const part of label.split("、")) {
    const item = part.trim();
    if (!item || seen.has(item)) continue;
    seen.add(item);
    parts.push(item);
  }
  return parts;
}

export function assignedAiRouteDisplay(value: string | null | undefined, limit = 2): string {
  const parts = assignedAiRouteParts(value);
  if (!parts.length) return "";
  if (parts.length <= limit) return parts.join("、");
  return `${parts.slice(0, limit).join("、")} 等 ${parts.length} 家`;
}

export function conversationIsMultiAi(bindings: ConversationBindings, current: CurrentFn): boolean {
  return Boolean(bindings.multiAiUid && current(bindings.multiAiUid) === "active");
}

export const MULTI_AI_ALIASES = ["A", "B", "C"] as const;

export function conversationMultiRouteReady(bindings: ConversationBindings, current: CurrentFn): boolean {
  if (!bindings.assignedAiUid) return false;
  return assignedAiRouteParts(current(bindings.assignedAiUid)).length >= MULTI_AI_ALIASES.length;
}

export function conversationParticipantAliases(bindings: ConversationBindings, current: CurrentFn): string[] {
  if (!conversationIsMultiAi(bindings, current)) return [];
  return [...MULTI_AI_ALIASES];
}

export function messageExceedsStoredLimit(value: string | undefined): boolean {
  return (value?.trim().length ?? 0) > CONVERSATION_STORED_MESSAGE_TEXT_CHARS;
}

function usableMessage(value: string | undefined): string {
  const text = value?.trim();
  if (!text || STATUS_TOKENS.has(text)) return "";
  if (text.length > CONVERSATION_STORED_MESSAGE_TEXT_CHARS) return "";
  return text;
}

export function isPlaceholderName(value: string | null | undefined): boolean {
  const name = value?.trim() ?? "";
  return PLACEHOLDER_NAMES.has(name);
}

export function exactName(value: string | null | undefined): string {
  return usableName(value ?? undefined);
}

function lineageRef(value: string | null | undefined): string {
  const raw = value?.trim() ?? "";
  if (!raw || STATUS_TOKENS.has(raw)) return "";
  try {
    const parsed = JSON.parse(raw) as { kind?: unknown; version?: unknown };
    if (parsed && parsed.kind === "CANONICAL_SCRIPT" && typeof parsed.version === "string" && parsed.version.trim()) {
      return parsed.version.trim();
    }
  } catch {
    return exactName(value);
  }
  return exactName(value);
}

export function namedValue(nextValue: string | undefined, fallback: string): string {
  return usableName(nextValue) || usableName(fallback) || fallback.slice(0, 80);
}

export function namedList(raw: string | null | undefined, extra?: string | null): string[] {
  const items = parseThreadList(raw ?? null).filter((item) => Boolean(usableName(item)));
  const extraName = usableName(extra ?? undefined);
  if (extraName && !items.includes(extraName)) return [...items, extraName];
  return items;
}

export function parseThreadList(raw: string | null): string[] {
  if (!raw || raw === "created") return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) return parsed.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  } catch {
    return [raw];
  }
  return [raw];
}

export type ConversationResumeStatus = "CURRENT" | "HISTORICAL" | "STALE" | "UNVERIFIED" | "BLOCKED";

export type ConversationResumePointer = {
  conversation_id: string;
  thread_id: string;
  branch_id_optional: string;
  last_visible_server_sequence: number;
  context_snapshot_ref: string;
  context_fingerprint: string;
  extension_uid: string;
  scope_owner_ref: string;
  resume_reason: string;
  stale_resolution_status: ConversationResumeStatus;
};

export type ConversationThreadRecord = {
  title: string;
  workItem: string;
  parentThread?: string;
  sourceRef?: string;
  branchRef?: string;
  convRef?: string;
  resume?: ConversationResumePointer;
};

export type ConversationMessageRole = "user" | "assistant";

export type ConversationMessageRecord = {
  thread: string;
  role: ConversationMessageRole;
  text: string;
  seq: number;
  ref: string;
  alias?: string;
  at?: string;
  route?: string;
};

function padRef(prefix: string, seq: number): string {
  return `${prefix}-${String(seq).padStart(6, "0")}`;
}

function refSeq(raw: string | undefined, prefixes: string[]): number {
  if (!raw) return 0;
  for (const prefix of prefixes) {
    if (raw.startsWith(prefix)) {
      const num = Number.parseInt(raw.slice(prefix.length).replace(/^0+/, "") || "0", 10);
      return Number.isFinite(num) ? num : 0;
    }
  }
  return 0;
}

export function ensureMessageIdentity(records: ConversationMessageRecord[]): ConversationMessageRecord[] {
  const aiMax = new Map<string, number>();
  const userMax = new Map<string, number>();
  for (const row of records) {
    if (row.role === "assistant") {
      const seq = row.seq || refSeq(row.ref, ["#AI-"]);
      aiMax.set(row.thread, Math.max(aiMax.get(row.thread) ?? 0, seq));
    } else {
      const seq = row.seq || refSeq(row.ref, ["#MSG-"]);
      userMax.set(row.thread, Math.max(userMax.get(row.thread) ?? 0, seq));
    }
  }
  return records.map((row) => {
    if (row.ref && row.seq) return row;
    if (row.role === "assistant") {
      const seq = row.seq || (aiMax.get(row.thread) ?? 0) + 1;
      aiMax.set(row.thread, seq);
      return { ...row, seq, ref: row.ref || padRef("#AI", seq) };
    }
    const seq = row.seq || (userMax.get(row.thread) ?? 0) + 1;
    userMax.set(row.thread, seq);
    return { ...row, seq, ref: row.ref || padRef("#MSG", seq) };
  });
}

export function parseMessageRecords(raw: string | null): ConversationMessageRecord[] {
  if (!raw || raw === "sent" || STATUS_TOKENS.has(raw)) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    const records: ConversationMessageRecord[] = [];
    for (const item of parsed) {
      if (!item || typeof item !== "object") continue;
      const rec = item as {
        thread?: unknown;
        role?: unknown;
        text?: unknown;
        seq?: unknown;
        ref?: unknown;
        alias?: unknown;
        at?: unknown;
        route?: unknown;
      };
      const text = typeof rec.text === "string" ? rec.text.trim() : "";
      if (!text) continue;
      const role = rec.role === "assistant" ? "assistant" : rec.role === "user" ? "user" : null;
      if (!role) continue;
      const seq = typeof rec.seq === "number" && Number.isFinite(rec.seq) ? rec.seq : 0;
      const ref = typeof rec.ref === "string" ? rec.ref.trim() : "";
      const alias = typeof rec.alias === "string" ? rec.alias.trim() : "";
      const at = typeof rec.at === "string" ? rec.at.trim() : "";
      const route = typeof rec.route === "string" ? rec.route.trim() : "";
      records.push({
        thread: typeof rec.thread === "string" ? rec.thread.trim() : "",
        role,
        text: text.slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS),
        seq,
        ref,
        ...(alias ? { alias } : {}),
        ...(at ? { at } : {}),
        ...(route ? { route } : {}),
      });
    }
    return ensureMessageIdentity(records);
  } catch {
    const trimmed = raw.trim();
    if (trimmed.startsWith("[") || trimmed.startsWith("{")) return [];
    const text = usableMessage(raw);
    return text ? ensureMessageIdentity([{ thread: "", role: "user", text, seq: 0, ref: "" }]) : [];
  }
}

export function messagesForThread(
  raw: string | null,
  thread: string,
  fallbackAssistant?: string | null,
): ConversationMessageRecord[] {
  if (!thread) return [];
  const records = parseMessageRecords(raw);
  const scoped = records.filter((row) => row.thread === thread);
  const unscoped = records.filter((row) => !row.thread).map((row) => ({ ...row, thread }));
  const merged = scoped.length ? [...unscoped, ...scoped] : unscoped;
  const extra = parseNotebookRecords(fallbackAssistant ?? null).length
    ? ""
    : usableMessage(fallbackAssistant ?? undefined);
  if (extra && extra !== merged[merged.length - 1]?.text) {
    return ensureMessageIdentity([...merged, { thread, role: "assistant", text: extra, seq: 0, ref: "" }]);
  }
  return merged;
}

export function recentHistoryPayload(
  records: ConversationMessageRecord[],
): Array<{ role: ConversationMessageRole; content: string }> {
  return records
    .slice(-CONVERSATION_RECENT_HISTORY_ROWS)
    .map((row) => ({
      role: row.role,
      content: row.text.slice(0, CONVERSATION_RECENT_HISTORY_TEXT_CHARS),
    }))
    .filter((row) => row.content.trim().length > 0);
}

export function lastAssistantText(raw: string | null, thread: string, fallback?: string | null): string {
  const records = messagesForThread(raw, thread, fallback);
  for (let index = records.length - 1; index >= 0; index -= 1) {
    if (records[index].role === "assistant") return records[index].text;
  }
  return "";
}

export function lastUserText(raw: string | null, thread: string): string {
  const records = messagesForThread(raw, thread);
  for (let index = records.length - 1; index >= 0; index -= 1) {
    if (records[index].role === "user") return records[index].text;
  }
  return "";
}

export type ConversationNotebookStatus = "CURRENT" | "STALE";

export type ConversationNotebookRecord = {
  thread: string;
  version: number;
  status: ConversationNotebookStatus;
  coveredCount: number;
  sourceHash: string;
  body: string;
};

function sourceHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function parseNotebookRecords(raw: string | null): ConversationNotebookRecord[] {
  if (!raw || STATUS_TOKENS.has(raw)) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return [];
    const payload = parsed as { kind?: unknown; records?: unknown };
    if (payload.kind !== "NOTEBOOK" || !Array.isArray(payload.records)) return [];
    const records: ConversationNotebookRecord[] = [];
    for (const item of payload.records) {
      if (!item || typeof item !== "object") continue;
      const rec = item as {
        thread?: unknown;
        version?: unknown;
        status?: unknown;
        coveredCount?: unknown;
        sourceHash?: unknown;
        body?: unknown;
      };
      const thread = typeof rec.thread === "string" ? rec.thread.trim() : "";
      const body = typeof rec.body === "string" ? rec.body.trim() : "";
      const hash = typeof rec.sourceHash === "string" ? rec.sourceHash.trim() : "";
      const version = typeof rec.version === "number" && Number.isFinite(rec.version) ? rec.version : 0;
      const coveredCount =
        typeof rec.coveredCount === "number" && Number.isFinite(rec.coveredCount) ? rec.coveredCount : 0;
      if (!thread || !body || !hash || version < 1) continue;
      records.push({
        thread,
        version,
        status: rec.status === "STALE" ? "STALE" : "CURRENT",
        coveredCount,
        sourceHash: hash,
        body: body.slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS),
      });
    }
    return records;
  } catch {
    return [];
  }
}

export function notebookTextForThread(raw: string | null, thread: string): string {
  if (!thread) return "";
  const match = parseNotebookRecords(raw).find((row) => row.thread === thread && row.status === "CURRENT");
  return match?.body ?? "";
}

function coveredForNotebook(records: ConversationMessageRecord[], mode: "overflow" | "record"): ConversationMessageRecord[] {
  if (mode === "overflow") {
    const prior = records.length ? records.slice(0, -1) : [];
    if (prior.length > CONVERSATION_RECENT_HISTORY_ROWS) {
      return prior.slice(0, prior.length - CONVERSATION_RECENT_HISTORY_ROWS);
    }
    return [];
  }
  return records;
}

export const ASSISTANT_OPERATIONS = [
  "MEETING_RECORD",
  "MESSAGE_RECORD",
  "SCOPE_SUMMARY",
  "DISCUSSION_NODE",
  "BRANCH_CREATE_ON_REQUEST",
  "BRANCH_SUMMARY",
  "CONSENSUS_LIST",
  "DISAGREEMENT_LIST",
  "OPEN_QUESTIONS",
  "FOLLOW_UPS",
  "SOURCE_INDEX",
  "IMPORTANT_REF_INDEX",
  "MEETING_SUMMARY",
  "CONFIRMED_CONCLUSION_RECORD",
  "MEMORY_PROJECTION_REFRESH",
  "CROSS_AI_COORDINATION",
] as const;

export type AssistantOperation = (typeof ASSISTANT_OPERATIONS)[number];

export type AssistantIntent = {
  operation: AssistantOperation;
  refs: string[];
};

const ASSISTANT_VERB_MAP: ReadonlyArray<{ op: AssistantOperation; pattern: RegExp }> = [
  { op: "MEMORY_PROJECTION_REFRESH", pattern: /整理筆記本|刷新記憶|MEMORY_PROJECTION_REFRESH/u },
  { op: "MEETING_SUMMARY", pattern: /會議摘要|會末摘要|MEETING_SUMMARY/u },
  { op: "BRANCH_CREATE_ON_REQUEST", pattern: /開分支|建立分支|BRANCH_CREATE_ON_REQUEST/u },
  { op: "BRANCH_SUMMARY", pattern: /分支摘要|BRANCH_SUMMARY/u },
  { op: "CONFIRMED_CONCLUSION_RECORD", pattern: /已確認結論|結論引用|CONFIRMED_CONCLUSION_RECORD/u },
  { op: "CROSS_AI_COORDINATION", pattern: /協調|CROSS_AI_COORDINATION/u },
  { op: "IMPORTANT_REF_INDEX", pattern: /重要引用|IMPORTANT_REF_INDEX/u },
  { op: "SOURCE_INDEX", pattern: /來源索引|來源|SOURCE_INDEX/u },
  { op: "OPEN_QUESTIONS", pattern: /未決|問題清單|OPEN_QUESTIONS/u },
  { op: "FOLLOW_UPS", pattern: /後續|待辦|FOLLOW_UPS/u },
  { op: "CONSENSUS_LIST", pattern: /共識|CONSENSUS_LIST/u },
  { op: "DISAGREEMENT_LIST", pattern: /分歧|衝突|DISAGREEMENT_LIST/u },
  { op: "DISCUSSION_NODE", pattern: /討論節點|DISCUSSION_NODE/u },
  { op: "SCOPE_SUMMARY", pattern: /範圍摘要|摘要|SCOPE_SUMMARY/u },
  { op: "MESSAGE_RECORD", pattern: /紀錄|記錄|MESSAGE_RECORD|MEETING_RECORD/u },
];

export function parseAssistantIntent(text: string, tokens: ConversationResolvedToken[]): AssistantIntent {
  const refs = tokens
    .filter((row) =>
      row.kind === "MESSAGE_REF" ||
      row.kind === "ASSISTANT_REF" ||
      row.kind === "CONVERSATION_REF" ||
      row.kind === "BRANCH_REF",
    )
    .map((row) => row.canonical)
    .filter(Boolean);
  const body = text.replace(/@助理/gu, "").trim();
  for (const row of ASSISTANT_VERB_MAP) {
    if (row.pattern.test(body)) {
      const operation = row.op === "MESSAGE_RECORD" && !refs.length ? "MEETING_RECORD" : row.op;
      return { operation, refs };
    }
  }
  return { operation: refs.length ? "MESSAGE_RECORD" : "MEETING_RECORD", refs };
}

function citedLine(refs: string[]): string {
  return refs.length ? refs.join("、") : "—";
}

function buildNotebookBody(
  covered: ConversationMessageRecord[],
  version: number,
  hash: string,
  intent?: AssistantIntent,
  extra?: { confirmedRefs?: string[]; aliases?: string[] },
): string {
  const operation = intent?.operation ?? "MEETING_RECORD";
  const exactRefs = citedLine(intent?.refs ?? []);
  const confirmed = citedLine(extra?.confirmedRefs ?? []);
  const aliases = extra?.aliases?.length ? extra.aliases.join("、") : "—";
  const cited = intent?.refs ?? [];
  const consensus = operation === "CONSENSUS_LIST" ? (cited.length ? `${citedLine(cited)}（待人工確認）` : "—") : "—";
  const disagreement = operation === "DISAGREEMENT_LIST" ? citedLine(cited) : "—";
  const openQuestions = operation === "OPEN_QUESTIONS" ? citedLine(cited) : "—";
  const followUps = operation === "FOLLOW_UPS" ? citedLine(cited) : "—";
  const sourceIndex = operation === "SOURCE_INDEX" || operation === "IMPORTANT_REF_INDEX" ? citedLine(cited) : exactRefs;
  const confirmedLine = operation === "CONFIRMED_CONCLUSION_RECORD" ? confirmed : "—";
  const header = [
    `會議紀錄 版本 ${version}`,
    `秘書動作：${operation}`,
    "狀態：現行",
    `涵蓋則數：${covered.length}`,
    `來源雜湊：${hash}`,
    `精確引用：${exactRefs}`,
    `參與者別名：${aliases}`,
    "重要引用：",
  ];
  const footer = [
    `共識：${consensus}`,
    `分歧：${disagreement}`,
    `未決問題：${openQuestions}`,
    `已確認結論引用：${confirmedLine}`,
    `後續事項：${followUps}`,
    `來源證據引用：${sourceIndex}`,
    operation === "CROSS_AI_COORDINATION" ? `協調對象：${aliases}` : "",
  ].filter(Boolean);
  const headerText = header.join("\n");
  const footerText = footer.join("\n");
  const budget = CONVERSATION_STORED_MESSAGE_TEXT_CHARS - headerText.length - footerText.length - 2;
  const refs: string[] = [];
  let used = 0;
  const preferred = intent?.refs.length
    ? covered.filter((row) => intent.refs.includes(row.ref))
    : covered;
  const rows = preferred.length ? preferred : covered;
  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    const role = row.role === "user" ? "使用者" : "AI";
    const line = `- ${row.ref || `第${index + 1}則`}（${role}）`;
    const piece = (refs.length ? 1 : 0) + line.length;
    if (used + piece > Math.max(budget, 0)) break;
    refs.push(line);
    used += piece;
  }
  if (!refs.length) refs.push("—");
  return `${headerText}\n${refs.join("\n")}\n${footerText}`.slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS);
}

function serializeNotebookRecords(records: ConversationNotebookRecord[]): string {
  const payload = JSON.stringify({ kind: "NOTEBOOK", records });
  if (payload.length <= CONVERSATION_STORED_MESSAGE_TEXT_CHARS) return payload;
  const shrunk = records.map((row) => ({
    ...row,
    body: row.body.slice(0, Math.max(200, Math.floor(CONVERSATION_STORED_MESSAGE_TEXT_CHARS / Math.max(records.length, 1) - 120))),
  }));
  return JSON.stringify({ kind: "NOTEBOOK", records: shrunk }).slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS);
}

function confirmedRefsFrom(bindings: ConversationBindings, current: CurrentFn): string[] {
  if (!bindings.humanDecisionUid) return [];
  const raw = usableMessage(current(bindings.humanDecisionUid) ?? undefined);
  if (!raw) return [];
  return raw.split(/[、,\s]+/u).map((part) => part.trim()).filter((part) => part.startsWith("#"));
}

export function refreshAssistantNotebookFor(
  bindings: ConversationBindings,
  current: CurrentFn,
  thread: string,
  records: ConversationMessageRecord[],
  mode: "overflow" | "record" = "overflow",
  intent?: AssistantIntent,
): Record<string, string> {
  if (!thread) return {};
  const covered = coveredForNotebook(records, mode);
  if (!covered.length) return {};
  const confirmedRefs = confirmedRefsFrom(bindings, current);
  const aliases = conversationParticipantAliases(bindings, current);
  const hash = sourceHash([
    intent?.operation ?? "MEETING_RECORD",
    ...(intent?.refs ?? []),
    ...confirmedRefs,
    ...aliases,
    ...covered.map((row) => `${row.role}:${row.ref}:${row.text}`),
  ]);
  const existing = parseNotebookRecords(current(bindings.notebookUid));
  const prior = existing.find((row) => row.thread === thread && row.status === "CURRENT");
  if (prior && prior.sourceHash === hash) return {};
  const version = (prior?.version ?? 0) + 1;
  const next: ConversationNotebookRecord = {
    thread,
    version,
    status: "CURRENT",
    coveredCount: covered.length,
    sourceHash: hash,
    body: buildNotebookBody(covered, version, hash, intent, { confirmedRefs, aliases }),
  };
  const others = existing.filter((row) => row.thread !== thread).map((row) => ({ ...row, status: "CURRENT" as const }));
  return { [bindings.notebookUid]: serializeNotebookRecords([...others, next]) };
}

export function formatConversationContext(
  bindings: ConversationBindings,
  current: CurrentFn,
  extra: string[] = [],
): string {
  const lines = [...(bindings.contextExtra?.(current) ?? []), ...extra];
  const thread = activeThreadUidFor(bindings, current);
  if (thread) lines.push(`對話：${thread}`);
  const notebook = notebookTextForThread(current(bindings.notebookUid), thread);
  if (notebook) lines.push(`筆記本：\n${notebook}`);
  return lines.filter(Boolean).join("\n");
}

export function appendAssistantMessageFor(
  bindings: ConversationBindings,
  current: CurrentFn,
  thread: string,
  reply: string,
  alias?: string,
  at?: string,
  route?: string,
): Record<string, string> {
  const text = reply.trim();
  if (!thread || !text) return {};
  const records = parseMessageRecords(current(bindings.messageUid));
  const nextMessages = ensureMessageIdentity([
    ...records,
    {
      thread,
      role: "assistant",
      text: text.slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS),
      seq: 0,
      ref: "",
      ...(alias ? { alias } : {}),
      ...(at ? { at } : {}),
      ...(route?.trim() ? { route: route.trim() } : {}),
    },
  ]);
  const patched = (uid: string) => (uid === bindings.messageUid ? JSON.stringify(nextMessages) : current(uid));
  return {
    [bindings.messageUid]: JSON.stringify(nextMessages),
    ...persistResumeOnThreadsFor(bindings, patched, thread, "RESPONSE"),
  };
}

export function appendAssistantMessagesFor(
  bindings: ConversationBindings,
  current: CurrentFn,
  thread: string,
  replies: Array<{ text: string; alias?: string; at?: string; route?: string }>,
): Record<string, string> {
  if (!thread || !replies.length) return {};
  let records = parseMessageRecords(current(bindings.messageUid));
  let lastPatch: Record<string, string> = {};
  for (const reply of replies) {
    const text = reply.text.trim();
    if (!text) continue;
    records = ensureMessageIdentity([
      ...records,
      {
        thread,
        role: "assistant",
        text: text.slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS),
        seq: 0,
        ref: "",
        ...(reply.alias ? { alias: reply.alias } : {}),
        ...(reply.at ? { at: reply.at } : {}),
        ...(reply.route?.trim() ? { route: reply.route.trim() } : {}),
      },
    ]);
    const patched = (uid: string) => (uid === bindings.messageUid ? JSON.stringify(records) : current(uid));
    lastPatch = {
      [bindings.messageUid]: JSON.stringify(records),
      ...persistResumeOnThreadsFor(bindings, patched, thread, "RESPONSE"),
    };
  }
  return lastPatch;
}

const RESUME_STATUSES = new Set<ConversationResumeStatus>(["CURRENT", "HISTORICAL", "STALE", "UNVERIFIED", "BLOCKED"]);

function parseResumePointer(raw: unknown): ConversationResumePointer | undefined {
  if (!raw || typeof raw !== "object") return undefined;
  const rec = raw as Record<string, unknown>;
  const conversation_id = typeof rec.conversation_id === "string" ? rec.conversation_id.trim() : "";
  const thread_id = typeof rec.thread_id === "string" ? rec.thread_id.trim() : "";
  if (!conversation_id || !thread_id) return undefined;
  const status = typeof rec.stale_resolution_status === "string" ? rec.stale_resolution_status : "";
  return {
    conversation_id,
    thread_id,
    branch_id_optional: typeof rec.branch_id_optional === "string" ? rec.branch_id_optional.trim() : "",
    last_visible_server_sequence:
      typeof rec.last_visible_server_sequence === "number" && Number.isFinite(rec.last_visible_server_sequence)
        ? rec.last_visible_server_sequence
        : 0,
    context_snapshot_ref: typeof rec.context_snapshot_ref === "string" ? rec.context_snapshot_ref.trim() : "",
    context_fingerprint: typeof rec.context_fingerprint === "string" ? rec.context_fingerprint.trim() : "",
    extension_uid: typeof rec.extension_uid === "string" ? rec.extension_uid.trim() : "",
    scope_owner_ref: typeof rec.scope_owner_ref === "string" ? rec.scope_owner_ref.trim() : "",
    resume_reason: typeof rec.resume_reason === "string" ? rec.resume_reason.trim() : "",
    stale_resolution_status: RESUME_STATUSES.has(status as ConversationResumeStatus)
      ? (status as ConversationResumeStatus)
      : "UNVERIFIED",
  };
}

export function conversationFingerprint(bindings: ConversationBindings, current: CurrentFn): string {
  if (bindings.contextFingerprint) return bindings.contextFingerprint(current);
  const parts = (bindings.fingerprintUids ?? []).map((uid) => exactName(current(uid)) || current(uid) || "");
  parts.push(workItemFor(bindings, current), activeThreadUidFor(bindings, current));
  return sourceHash(parts);
}

export function conversationSnapshotRef(bindings: ConversationBindings, current: CurrentFn): string {
  if (bindings.contextSnapshotRef) return bindings.contextSnapshotRef(current);
  const owner = bindings.scopeOwnerUid ? exactName(current(bindings.scopeOwnerUid)) || "UNBOUND" : "UNBOUND";
  const work = workItemFor(bindings, current) || "NONE";
  return `SNAP:${owner}/${work}`;
}

function lastVisibleSequence(bindings: ConversationBindings, current: CurrentFn, thread: string): number {
  const messages = messagesForThread(current(bindings.messageUid), thread);
  return messages.reduce((max, row) => Math.max(max, row.seq || 0), 0);
}

export function buildResumePointerFor(
  bindings: ConversationBindings,
  current: CurrentFn,
  thread: ConversationThreadRecord,
  reason: string,
  status: ConversationResumeStatus = "CURRENT",
): ConversationResumePointer {
  return {
    conversation_id: thread.convRef || "",
    thread_id: thread.title,
    branch_id_optional: thread.branchRef || "",
    last_visible_server_sequence: lastVisibleSequence(bindings, current, thread.title),
    context_snapshot_ref: conversationSnapshotRef(bindings, current),
    context_fingerprint: conversationFingerprint(bindings, current),
    extension_uid: bindings.extensionUid,
    scope_owner_ref: bindings.scopeOwnerUid ? exactName(current(bindings.scopeOwnerUid)) : "",
    resume_reason: reason,
    stale_resolution_status: status,
  };
}

export function persistResumeOnThreadsFor(
  bindings: ConversationBindings,
  current: CurrentFn,
  threadTitle: string,
  reason: string,
  records?: ConversationThreadRecord[],
): Record<string, string> {
  const identified = ensureThreadIdentity(records ?? parseThreadRecords(current(bindings.threadStoreUid)));
  const next = identified.map((row) =>
    row.title === threadTitle ? { ...row, resume: buildResumePointerFor(bindings, current, row, reason) } : row,
  );
  return { [bindings.threadStoreUid]: JSON.stringify(next) };
}

export function resolveResumePointerFor(
  bindings: ConversationBindings,
  current: CurrentFn,
  threadTitle?: string,
): ConversationResumePointer | null {
  const title = threadTitle || activeThreadUidFor(bindings, current);
  if (!title) return null;
  const thread = parseThreadRecords(current(bindings.threadStoreUid)).find((row) => row.title === title);
  if (!thread?.resume) return null;
  const fingerprint = conversationFingerprint(bindings, current);
  const drifted = Boolean(thread.resume.context_fingerprint && thread.resume.context_fingerprint !== fingerprint);
  return {
    ...thread.resume,
    context_snapshot_ref: conversationSnapshotRef(bindings, current),
    stale_resolution_status: drifted ? "STALE" : thread.resume.stale_resolution_status,
  };
}

function ensureThreadIdentity(records: ConversationThreadRecord[]): ConversationThreadRecord[] {
  let convMax = 0;
  let branchMax = 0;
  for (const row of records) {
    convMax = Math.max(convMax, refSeq(row.convRef, ["#CONV-"]));
    branchMax = Math.max(branchMax, refSeq(row.branchRef, ["#BR-"]));
  }
  return records.map((row) => {
    let convRef = row.convRef;
    let branchRef = row.branchRef;
    if (!convRef) {
      convMax += 1;
      convRef = padRef("#CONV", convMax);
    }
    if (row.parentThread && !branchRef) {
      branchMax += 1;
      branchRef = padRef("#BR", branchMax);
    }
    return { ...row, convRef, ...(branchRef ? { branchRef } : {}) };
  });
}

export function parseThreadRecords(raw: string | null): ConversationThreadRecord[] {
  if (!raw || raw === "created") return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      const title = usableName(raw);
      return title ? ensureThreadIdentity([{ title, workItem: "" }]) : [];
    }
    const records: ConversationThreadRecord[] = [];
    for (const item of parsed) {
      if (typeof item === "string") {
        const title = usableName(item);
        if (title) records.push({ title, workItem: "" });
        continue;
      }
      if (!item || typeof item !== "object") continue;
      const rec = item as {
        title?: unknown;
        workItem?: unknown;
        parentThread?: unknown;
        sourceRef?: unknown;
        branchRef?: unknown;
        convRef?: unknown;
        resume?: unknown;
      };
      const title = typeof rec.title === "string" ? usableName(rec.title) : "";
      if (!title) continue;
      const resume = parseResumePointer(rec.resume);
      const workItem = typeof rec.workItem === "string" ? rec.workItem : "";
      records.push({
        title,
        workItem,
        parentThread: typeof rec.parentThread === "string" ? rec.parentThread.trim() : undefined,
        sourceRef: typeof rec.sourceRef === "string" ? rec.sourceRef.trim() : undefined,
        branchRef: typeof rec.branchRef === "string" ? rec.branchRef.trim() : undefined,
        convRef: typeof rec.convRef === "string" ? rec.convRef.trim() : undefined,
        ...(resume ? { resume } : {}),
      });
    }
    return ensureThreadIdentity(records);
  } catch {
    const title = usableName(raw);
    return title ? ensureThreadIdentity([{ title, workItem: "" }]) : [];
  }
}

function threadMatchesWorkItem(bindings: ConversationBindings, rowWorkItem: string, workItem: string): boolean {
  if (rowWorkItem === workItem) return true;
  if (!rowWorkItem && workItem === bindings.defaultWorkItem) return true;
  if (bindings.strictWorkItem) return false;
  return !rowWorkItem;
}

export function workItemFor(bindings: ConversationBindings, current: CurrentFn): string {
  if (bindings.resolveWorkItem) return bindings.resolveWorkItem(current);
  const stored = bindings.workItemUid ? current(bindings.workItemUid) ?? "" : "";
  if (bindings.allowedWorkItems?.has(stored)) return stored;
  return bindings.defaultWorkItem;
}

export function threadScopeReadyFor(bindings: ConversationBindings, current: CurrentFn): boolean {
  if (bindings.scopeReady) return bindings.scopeReady(current);
  return Boolean(workItemFor(bindings, current));
}

export function threadsForWorkItem(bindings: ConversationBindings, current: CurrentFn): ConversationThreadRecord[] {
  const workItem = workItemFor(bindings, current);
  if (!workItem) return [];
  return parseThreadRecords(current(bindings.threadStoreUid)).filter((row) =>
    threadMatchesWorkItem(bindings, row.workItem, workItem),
  );
}

export function activeThreadUidFor(bindings: ConversationBindings, current: CurrentFn): string {
  const scoped = threadsForWorkItem(bindings, current);
  const stored = current(bindings.threadListUid);
  if (stored && !["created", "selected"].includes(stored) && scoped.some((row) => row.title === stored)) {
    return stored;
  }
  if (scoped.length === 1) return scoped[0].title;
  const resumed = scoped.filter((row) => row.resume?.conversation_id && row.resume.thread_id === row.title);
  if (resumed.length === 1) return resumed[0].title;
  return "";
}

export function hasSendableMessage(nextValue?: string, stored?: string | null): boolean {
  return Boolean(usableMessage(nextValue) || usableMessage(stored ?? undefined));
}

export type ConversationTokenKind =
  | "TARGET_PARTICIPANT"
  | "TARGET_ALL_PARTICIPANTS"
  | "TARGET_ASSISTANT"
  | "MESSAGE_REF"
  | "ASSISTANT_REF"
  | "CONVERSATION_REF"
  | "BRANCH_REF"
  | "PARSER_ERROR"
  | "AMBIGUOUS_REF";

export type ConversationResolvedToken = {
  raw: string;
  kind: ConversationTokenKind;
  canonical: string;
};

export function targetedParticipantAliasesFor(
  bindings: ConversationBindings,
  tokens: ConversationResolvedToken[],
  current: CurrentFn,
): string[] {
  const aliases = conversationParticipantAliases(bindings, current);
  if (!aliases.length) return [];
  const named = tokens
    .filter((row) => row.kind === "TARGET_PARTICIPANT")
    .map((row) => row.canonical.replace(/^@/, ""))
    .filter((alias) => aliases.includes(alias));
  if (tokens.some((row) => row.kind === "TARGET_ALL_PARTICIPANTS") || named.length === 0) return aliases;
  return aliases.filter((alias) => named.includes(alias));
}

const COMPOSER_TOKEN = /(@全部AI|@助理|@[ABC]|#AI-\d+|#AST-\d+|#CONV-\d+|#BR-\d+|#MSG-\d+|#\d+)/gu;

function assistantRefForThread(bindings: ConversationBindings, current: CurrentFn, thread: string): string {
  const notes = parseNotebookRecords(current(bindings.notebookUid));
  const match = notes.find((row) => row.thread === thread);
  return match ? padRef("#AST", match.version) : "";
}

function shortNumber(raw: string): string {
  const digits = raw.replace(/\D/g, "").replace(/^0+/, "") || "0";
  return digits;
}

export function resolveComposerTokensFor(
  bindings: ConversationBindings,
  text: string,
  current: CurrentFn,
): ConversationResolvedToken[] {
  const thread = activeThreadUidFor(bindings, current);
  const messages = messagesForThread(current(bindings.messageUid), thread);
  const threads = parseThreadRecords(current(bindings.threadStoreUid));
  const multi = conversationIsMultiAi(bindings, current);
  const tokens: ConversationResolvedToken[] = [];
  COMPOSER_TOKEN.lastIndex = 0;
  let match: RegExpExecArray | null = COMPOSER_TOKEN.exec(text);
  while (match) {
    const raw = match[0];
    if (raw === "@A" || raw === "@B" || raw === "@C") {
      const alias = raw.slice(1);
      tokens.push(
        multi && conversationParticipantAliases(bindings, current).includes(alias)
          ? { raw, kind: "TARGET_PARTICIPANT", canonical: raw }
          : { raw, kind: "PARSER_ERROR", canonical: "" },
      );
    } else if (raw === "@全部AI") {
      tokens.push({ raw, kind: "TARGET_ALL_PARTICIPANTS", canonical: raw });
    } else if (raw === "@助理") {
      tokens.push({ raw, kind: "TARGET_ASSISTANT", canonical: raw });
    } else if (raw.startsWith("#AST-")) {
      const ast = assistantRefForThread(bindings, current, thread);
      tokens.push(
        ast && ast === padRef("#AST", Number.parseInt(raw.slice(5).replace(/^0+/, "") || "0", 10) || 0)
          ? { raw, kind: "ASSISTANT_REF", canonical: ast }
          : { raw, kind: "PARSER_ERROR", canonical: "" },
      );
    } else if (raw.startsWith("#CONV-")) {
      const hit = threads.find(
        (row) => row.convRef === padRef("#CONV", Number.parseInt(raw.slice(6).replace(/^0+/, "") || "0", 10) || 0),
      );
      tokens.push(hit?.convRef ? { raw, kind: "CONVERSATION_REF", canonical: hit.convRef } : { raw, kind: "PARSER_ERROR", canonical: "" });
    } else if (raw.startsWith("#BR-")) {
      const hit = threads.find(
        (row) => row.branchRef === padRef("#BR", Number.parseInt(raw.slice(4).replace(/^0+/, "") || "0", 10) || 0),
      );
      tokens.push(hit?.branchRef ? { raw, kind: "BRANCH_REF", canonical: hit.branchRef } : { raw, kind: "PARSER_ERROR", canonical: "" });
    } else {
      const num = shortNumber(raw);
      const tokenPrefix = raw.startsWith("#AI-") ? "#AI" : raw.startsWith("#MSG-") ? "#MSG" : "";
      const hits = tokenPrefix
        ? messages.filter((row) => row.ref === padRef(tokenPrefix, Number.parseInt(num, 10) || 0))
        : messages.filter((row) => shortNumber(row.ref) === num);
      if (hits.length === 1) {
        tokens.push({ raw, kind: "MESSAGE_REF", canonical: hits[0].ref });
      } else if (hits.length > 1) {
        tokens.push({ raw, kind: "AMBIGUOUS_REF", canonical: "" });
      } else {
        tokens.push({ raw, kind: "PARSER_ERROR", canonical: "" });
      }
    }
    match = COMPOSER_TOKEN.exec(text);
  }
  return tokens;
}

export function composerHasBlockingToken(tokens: ConversationResolvedToken[]): boolean {
  return tokens.some((row) => row.kind === "PARSER_ERROR" || row.kind === "AMBIGUOUS_REF");
}

export function composerTokenTone(kind: ConversationTokenKind): "ok" | "error" | "ambiguous" {
  if (kind === "PARSER_ERROR") return "error";
  if (kind === "AMBIGUOUS_REF") return "ambiguous";
  return "ok";
}

export function quoteInsertText(ref: string): string {
  return ref ? `${ref} ` : "";
}

export type ConversationMessageActionPayload = {
  actionUid: string;
  messageRef?: string;
};

export function parseMessageActionPayload(nextValue?: string): ConversationMessageActionPayload {
  const text = (nextValue ?? "").trim();
  if (!text) return { actionUid: "" };
  if (text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text) as { actionUid?: unknown; messageRef?: unknown };
      return {
        actionUid: typeof parsed.actionUid === "string" ? parsed.actionUid : "",
        messageRef: typeof parsed.messageRef === "string" ? parsed.messageRef : undefined,
      };
    } catch {
      return { actionUid: "" };
    }
  }
  return { actionUid: "", messageRef: text };
}

function findThreadMessage(
  bindings: ConversationBindings,
  current: CurrentFn,
  messageRef?: string,
): ConversationMessageRecord | null {
  const thread = activeThreadUidFor(bindings, current);
  if (!thread || !messageRef) return null;
  const tokens = resolveComposerTokensFor(bindings, messageRef, current);
  const resolved = tokens.find((row) => row.kind === "MESSAGE_REF")?.canonical ?? messageRef;
  return messagesForThread(current(bindings.messageUid), thread).find((row) => row.ref === resolved) ?? null;
}

export function previewThreadCreateFor(
  bindings: ConversationBindings,
  current: CurrentFn,
  nextValue?: string,
): Record<string, string> {
  if (!threadScopeReadyFor(bindings, current)) return {};
  const workItem = workItemFor(bindings, current);
  const records = parseThreadRecords(current(bindings.threadStoreUid));
  const scoped = records.filter((row) => threadMatchesWorkItem(bindings, row.workItem, workItem));
  const title = namedValue(nextValue, (bindings.defaultThreadTitle ?? ((count) => `修正 ${count}`))(scoped.length + 1));
  const exists = records.some((row) => row.title === title && threadMatchesWorkItem(bindings, row.workItem, workItem));
  const nextRecords = ensureThreadIdentity(exists ? records : [...records, { title, workItem }]);
  const patched = (uid: string) => (uid === bindings.threadListUid ? title : current(uid));
  return {
    [bindings.threadListUid]: title,
    ...persistResumeOnThreadsFor(bindings, patched, title, "CREATE", nextRecords),
  };
}

export function previewThreadSelectFor(
  bindings: ConversationBindings,
  current: CurrentFn,
  nextValue?: string,
): Record<string, string> {
  const workItem = workItemFor(bindings, current);
  if (!workItem) return {};
  const title = exactName(nextValue) || exactName(current(bindings.threadListUid));
  if (!title) return {};
  const match = parseThreadRecords(current(bindings.threadStoreUid)).find(
    (row) => row.title === title && threadMatchesWorkItem(bindings, row.workItem, workItem),
  );
  if (!match) return {};
  const patched = (uid: string) => (uid === bindings.threadListUid ? title : current(uid));
  return {
    [bindings.threadListUid]: title,
    ...persistResumeOnThreadsFor(bindings, patched, title, "SELECT"),
  };
}

export function ensureConversationThread(
  bindings: ConversationBindings,
  current: CurrentFn,
): Record<string, string> {
  const existing = activeThreadUidFor(bindings, current);
  if (existing) {
    return persistResumeOnThreadsFor(bindings, current, existing, "OPEN");
  }
  const records = threadsForWorkItem(bindings, current);
  if (records.length) {
    return previewThreadSelectFor(bindings, current, records[0].title);
  }
  return previewThreadCreateFor(bindings, current);
}

export function previewAssistantRecordFor(
  bindings: ConversationBindings,
  current: CurrentFn,
): Record<string, string> {
  const thread = activeThreadUidFor(bindings, current);
  if (!thread) return {};
  const records = messagesForThread(current(bindings.messageUid), thread);
  if (!records.length) return {};
  const intent: AssistantIntent = { operation: "MEETING_RECORD", refs: [] };
  const notebookPatch = refreshAssistantNotebookFor(bindings, current, thread, records, "record", intent);
  if (!Object.keys(notebookPatch).length) {
    return { [bindings.assistantUid]: "recorded" };
  }
  return {
    ...notebookPatch,
    [bindings.assistantUid]: "recorded",
    ...(bindings.runtimeStageUid ? { [bindings.runtimeStageUid]: "ASSISTANT_SUMMARY" } : {}),
    ...persistResumeOnThreadsFor(bindings, current, thread, "ASSISTANT_RECORD"),
  };
}

export function previewConversationSend(
  bindings: ConversationBindings,
  current: CurrentFn,
  nextValue?: string,
): Record<string, string> {
  const thread = activeThreadUidFor(bindings, current);
  if (!thread || !hasSendableMessage(nextValue)) return {};
  const message = usableMessage(nextValue);
  if (!message) return {};
  const tokens = resolveComposerTokensFor(bindings, message, current);
  if (composerHasBlockingToken(tokens)) return {};
  if (!tokens.some((row) => row.kind === "TARGET_ASSISTANT") && !conversationAssignedAiReady(bindings, current)) {
    return {};
  }
  if (
    !tokens.some((row) => row.kind === "TARGET_ASSISTANT") &&
    conversationIsMultiAi(bindings, current) &&
    !conversationMultiRouteReady(bindings, current)
  ) {
    return {};
  }
  if (tokens.some((row) => row.kind === "TARGET_ASSISTANT")) {
    const intent = parseAssistantIntent(message, tokens);
    const records = parseMessageRecords(current(bindings.messageUid));
    const nextRecords = ensureMessageIdentity([...records, { thread, role: "user", text: message, seq: 0, ref: "" }]);
    const patched = (uid: string) => (uid === bindings.messageUid ? JSON.stringify(nextRecords) : current(uid));
    const notebookPatch = refreshAssistantNotebookFor(
      bindings,
      patched,
      thread,
      messagesForThread(JSON.stringify(nextRecords), thread),
      "record",
      intent,
    );
    const branchPatch =
      intent.operation === "BRANCH_CREATE_ON_REQUEST" && intent.refs[0]
        ? previewMessageActionFor(bindings, `${bindings.prefix}-ACT-MSG-BRANCH`, current, intent.refs[0])
        : {};
    return {
      [bindings.messageUid]: JSON.stringify(nextRecords),
      [bindings.sendUid]: "sent",
      [bindings.assistantUid]: "recorded",
      ...(bindings.runtimeStageUid ? { [bindings.runtimeStageUid]: "ASSISTANT_SUMMARY" } : {}),
      ...notebookPatch,
      ...persistResumeOnThreadsFor(bindings, patched, thread, "ASSISTANT"),
      ...branchPatch,
    };
  }
  const files = (bindings.attachmentUids ?? []).map((uid) => exactName(current(uid))).filter(Boolean);
  const payload = files.length ? `${message} · ${files.join("、")}` : message;
  let records = parseMessageRecords(current(bindings.messageUid)).map((row) =>
    row.thread ? row : { ...row, thread },
  );
  if (!records.some((row) => row.thread === thread && row.role === "assistant")) {
    const priorSummary = current(bindings.notebookUid);
    const priorNotebook = parseNotebookRecords(priorSummary ?? null);
    const prior = priorNotebook.length ? "" : usableMessage(priorSummary ?? undefined);
    const scopedMessages = records.filter((row) => row.thread === thread);
    const last = scopedMessages[scopedMessages.length - 1]?.text;
    if (prior && prior !== last && prior !== payload) {
      records = [...records, { thread, role: "assistant", text: prior, seq: 0, ref: "" }];
    }
  }
  const nextRecords = ensureMessageIdentity([...records, { thread, role: "user", text: payload, seq: 0, ref: "" }]);
  const notebookPatch = refreshAssistantNotebookFor(bindings, current, thread, nextRecords, "overflow");
  const patched = (uid: string) => (uid === bindings.messageUid ? JSON.stringify(nextRecords) : current(uid));
  return {
    [bindings.messageUid]: JSON.stringify(nextRecords),
    ...(bindings.runtimeStageUid ? { [bindings.runtimeStageUid]: "AI_RESPONSES" } : {}),
    [bindings.sendUid]: "sent",
    ...notebookPatch,
    ...persistResumeOnThreadsFor(bindings, patched, thread, "SEND"),
  };
}

export function previewMessageActionFor(
  bindings: ConversationBindings,
  actionUid: string,
  current: CurrentFn,
  messageRef?: string,
): Record<string, string> {
  const thread = activeThreadUidFor(bindings, current);
  if (!thread) return {};
  const message = findThreadMessage(bindings, current, messageRef);
  if (!message) return {};
  if (
    actionUid === `${bindings.prefix}-ACT-MSG-QUOTE` ||
    actionUid === `${bindings.prefix}-ACT-MSG-CONTINUE` ||
    actionUid === `${bindings.prefix}-ACT-MSG-COPY`
  ) {
    return {};
  }
  if (actionUid === `${bindings.prefix}-ACT-MSG-ANALYZE`) {
    const prompt = `分析此內容 ${message.ref}`;
    return previewConversationSend(bindings, current, prompt);
  }
  if (actionUid === `${bindings.prefix}-ACT-MSG-DECISION`) {
    if (!bindings.humanDecisionUid) return {};
    const existing = usableMessage(current(bindings.humanDecisionUid) ?? undefined);
    const next =
      existing && existing !== "confirmed" && existing !== "recorded"
        ? existing.includes(message.ref)
          ? existing
          : `${existing}、${message.ref}`
        : message.ref;
    return {
      [bindings.humanDecisionUid]: next,
      ...(bindings.runtimeStageUid ? { [bindings.runtimeStageUid]: "HUMAN_DECISION" } : {}),
    };
  }
  if (actionUid === `${bindings.prefix}-ACT-MSG-BRANCH`) {
    const records = parseThreadRecords(current(bindings.threadStoreUid));
    const workItem = workItemFor(bindings, current);
    const scoped = records.filter((row) => threadMatchesWorkItem(bindings, row.workItem, workItem));
    const title = namedValue(undefined, `分支 ${scoped.length + 1}`);
    const nextRecords = ensureThreadIdentity([
      ...records,
      { title, workItem, parentThread: thread, sourceRef: message.ref },
    ]);
    const patched = (uid: string) => (uid === bindings.threadListUid ? title : current(uid));
    return {
      [bindings.threadListUid]: title,
      ...persistResumeOnThreadsFor(bindings, patched, title, "BRANCH", nextRecords),
    };
  }
  return {};
}

export function composerRequestFrom(
  bindings: ConversationBindings,
  current: CurrentFn,
  nextValue?: string,
): string {
  const composer = bindings.composerUid ? usableMessage(current(bindings.composerUid) ?? undefined) : "";
  const thread = activeThreadUidFor(bindings, current);
  const last = lastUserText(current(bindings.messageUid), thread);
  return usableMessage(nextValue) || composer || last;
}

export function isConversationAction(bindings: ConversationBindings, actionUid: string): boolean {
  return (
    actionUid === `${bindings.prefix}-ACT-SEND` ||
    actionUid === `${bindings.prefix}-ACT-THREAD-CREATE` ||
    actionUid === `${bindings.prefix}-ACT-THREAD-SELECT` ||
    actionUid === `${bindings.prefix}-ACT-ASSISTANT-RECORD` ||
    actionUid.startsWith(`${bindings.prefix}-ACT-MSG-`)
  );
}

export function previewConversationAction(
  bindings: ConversationBindings,
  controlUid: string,
  actionUid: string,
  current: CurrentFn,
  nextValue?: string,
): Record<string, string> | null {
  if (actionUid === `${bindings.prefix}-ACT-THREAD-CREATE`) {
    return previewThreadCreateFor(bindings, current, nextValue);
  }
  if (actionUid === `${bindings.prefix}-ACT-THREAD-SELECT`) {
    return previewThreadSelectFor(bindings, current, nextValue);
  }
  if (actionUid.startsWith(`${bindings.prefix}-ACT-MSG-`)) {
    const payload = parseMessageActionPayload(nextValue);
    return previewMessageActionFor(bindings, actionUid, current, payload.messageRef || nextValue);
  }
  if (actionUid === `${bindings.prefix}-ACT-SEND`) {
    return previewConversationSend(bindings, current, nextValue);
  }
  if (actionUid === `${bindings.prefix}-ACT-ASSISTANT-RECORD`) {
    return previewAssistantRecordFor(bindings, current);
  }
  return null;
}

const CORE_WORK_ITEMS = new Set([
  "STORY",
  "CHAPTER",
  "WORLD_SETTING",
  "DNA",
  "BLUEPRINT",
  "TOPIC_SCOPE",
  "PRODUCTION_SCRIPT",
]);

function coreWorkItem(current: CurrentFn): string {
  const stored = current("CORE-01-LST-WORK-ITEMS") ?? "";
  if (CORE_WORK_ITEMS.has(stored)) return stored;
  if (!exactName(current("CORE-01-CTL-PROJECT"))) return "";
  const topicMode =
    current("CORE-01-FLD-PAGE-MODE") === "TOPIC_PRODUCTION" && Boolean(exactName(current("CORE-01-CTL-TOPIC")));
  return topicMode ? "TOPIC_SCOPE" : "STORY";
}

export const CORE_CONVERSATION: ConversationBindings = {
  prefix: "CORE-01",
  extensionUid: "CORE-01",
  messageUid: "CORE-01-FLD-MESSAGE",
  threadStoreUid: "CORE-01-BTN-NEW-THREAD",
  threadListUid: "CORE-01-LST-THREADS",
  notebookUid: "CORE-01-FLD-ASSISTANT-SUMMARY",
  sendUid: "CORE-01-BTN-SEND",
  assistantUid: "CORE-01-BTN-ASSISTANT-RECORD",
  assignedAiUid: "CORE-01-FLD-ASSIGNED-AI",
  multiAiUid: "CORE-01-BTN-MULTI-AI",
  workItemUid: "CORE-01-LST-WORK-ITEMS",
  defaultWorkItem: "STORY",
  allowedWorkItems: CORE_WORK_ITEMS,
  scopeOwnerUid: "CORE-01-CTL-PROJECT",
  humanDecisionUid: "CORE-01-FLD-HUMAN-DECISION",
  runtimeStageUid: "CORE-01-FLD-RUNTIME-STAGE",
  resolveWorkItem: coreWorkItem,
  scopeReady: (current) => Boolean(exactName(current("CORE-01-CTL-PROJECT")) && coreWorkItem(current)),
  strictWorkItem: true,
  defaultThreadTitle: (count) => `對話 ${count}`,
  attachmentUids: ["CORE-01-BTN-ATTACHMENT", "CORE-01-BTN-REFERENCE"],
  contextFingerprint: (current) =>
    sourceHash([
      exactName(current("CORE-01-CTL-PROJECT")),
      exactName(current("CORE-01-CTL-TOPIC")),
      coreWorkItem(current),
      exactName(current("CORE-01-BTN-DNA-LOCK")),
      exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE")),
      lineageRef(current("CORE-01-BTN-CANONICAL-SCRIPT")),
      current("CORE-01-BTN-PROJECT-CONFIRM") ?? "",
      current("CORE-01-BTN-PROJECT-LOCK") ?? "",
    ]),
  contextSnapshotRef: (current) => {
    const project = exactName(current("CORE-01-CTL-PROJECT")) || "UNBOUND";
    const topic = exactName(current("CORE-01-CTL-TOPIC")) || "NONE";
    const work = coreWorkItem(current) || "NONE";
    return `SNAP:${project}/${topic}/${work}`;
  },
  contextExtra: (current) => {
    const lines: string[] = ["系統：ACPOS 影音生產作業系統（專案／專題／藍圖／Canonical Script）。禁止解釋成收銀、POS 或電子商務銷售。"];
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    const topic = exactName(current("CORE-01-CTL-TOPIC"));
    const workItem = coreWorkItem(current);
    if (project) lines.push(`專案：${project}`);
    if (topic) lines.push(`專題：${topic}`);
    if (workItem) lines.push(`工作項目：${workItem}`);
    const script = lineageRef(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    if (script) lines.push(`正式腳本：${script}`);
    return lines;
  },
};

export const ASSET_CONVERSATION: ConversationBindings = {
  prefix: "ASSET-01",
  extensionUid: "ASSET-01",
  messageUid: "ASSET-01-FLD-CORRECTION-MESSAGES",
  threadStoreUid: "ASSET-01-FLD-CORRECTION-THREADS",
  threadListUid: "ASSET-01-LST-THREADS",
  notebookUid: "ASSET-01-FLD-CORRECTION-NOTEBOOK",
  sendUid: "ASSET-01-BTN-SEND",
  assistantUid: "ASSET-01-BTN-ASSISTANT",
  defaultWorkItem: "CORRECTION",
  allowedWorkItems: new Set(["CORRECTION"]),
  scopeOwnerUid: "ASSET-01-CTL-PROJECT",
  fingerprintUids: ["ASSET-01-FLD-OUTPUT-ID", "ASSET-01-FLD-MANIFEST", "ASSET-01-FLD-SCRIPT"],
  composerUid: "ASSET-01-TXT-CORRECTION-REQUEST",
};

export const VIDEO_CONVERSATION: ConversationBindings = {
  prefix: "VIDEO-01",
  extensionUid: "VIDEO-01",
  messageUid: "VIDEO-01-FLD-CORRECTION-MESSAGES",
  threadStoreUid: "VIDEO-01-FLD-CORRECTION-THREADS",
  threadListUid: "VIDEO-01-LST-THREADS",
  notebookUid: "VIDEO-01-FLD-CORRECTION-NOTEBOOK",
  sendUid: "VIDEO-01-BTN-SEND",
  assistantUid: "VIDEO-01-BTN-ASSISTANT",
  defaultWorkItem: "CORRECTION",
  allowedWorkItems: new Set(["CORRECTION"]),
  scopeOwnerUid: "VIDEO-01-FLD-PROJECT",
  fingerprintUids: ["VIDEO-01-FLD-VIDEO-VERSION", "VIDEO-01-FLD-CURRENT-VERSION", "VIDEO-01-FLD-SCRIPT-SECTION"],
  composerUid: "VIDEO-01-TXT-CORRECTION",
};

export const EDIT_CONVERSATION: ConversationBindings = {
  prefix: "EDIT-01",
  extensionUid: "EDIT-01",
  messageUid: "EDIT-01-FLD-CORRECTION-MESSAGES",
  threadStoreUid: "EDIT-01-FLD-CORRECTION-THREADS",
  threadListUid: "EDIT-01-LST-THREADS",
  notebookUid: "EDIT-01-FLD-CORRECTION-NOTEBOOK",
  sendUid: "EDIT-01-BTN-SEND",
  assistantUid: "EDIT-01-BTN-ASSISTANT",
  defaultWorkItem: "CORRECTION",
  allowedWorkItems: new Set(["CORRECTION"]),
  scopeOwnerUid: "EDIT-01-FLD-PROJECT",
  fingerprintUids: ["EDIT-01-FLD-SOURCE-VERSION", "EDIT-01-LBL-CURRENT-SCRIPT-SECTION"],
  composerUid: "EDIT-01-FLD-API-INSTRUCTION",
};

export const ASSET_CONVERSATION_HIDDEN = [
  "ASSET-01-FLD-CORRECTION-MESSAGES",
  "ASSET-01-FLD-CORRECTION-THREADS",
  "ASSET-01-FLD-CORRECTION-NOTEBOOK",
] as const;

export const VIDEO_CONVERSATION_HIDDEN = [
  "VIDEO-01-FLD-CORRECTION-MESSAGES",
  "VIDEO-01-FLD-CORRECTION-THREADS",
  "VIDEO-01-FLD-CORRECTION-NOTEBOOK",
] as const;

export const EDIT_CONVERSATION_HIDDEN = [
  "EDIT-01-FLD-CORRECTION-MESSAGES",
  "EDIT-01-FLD-CORRECTION-THREADS",
  "EDIT-01-FLD-CORRECTION-NOTEBOOK",
] as const;
