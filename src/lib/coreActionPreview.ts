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

const AI_MODE_TOKENS = new Set(["SINGLE", "MULTI"]);

export function assignedAiRouteLabel(value: string | null | undefined): string {
  const text = (value ?? "").trim();
  if (!text || AI_MODE_TOKENS.has(text) || STATUS_TOKENS.has(text) || PLACEHOLDER_NAMES.has(text)) return "";
  return text;
}

export function assignedAiRouteReady(current: (uid: string) => string | null): boolean {
  return Boolean(assignedAiRouteLabel(current("CORE-01-FLD-ASSIGNED-AI")));
}

export function isMultiAiMode(current: (uid: string) => string | null): boolean {
  return current("CORE-01-BTN-MULTI-AI") === "active";
}

export const MULTI_AI_ALIASES = ["A", "B", "C"] as const;

export function assignedParticipantAliases(current: (uid: string) => string | null): string[] {
  const parts = assignedAiRouteLabel(current("CORE-01-FLD-ASSIGNED-AI"))
    .split("、")
    .map((part) => part.trim())
    .filter(Boolean);
  return MULTI_AI_ALIASES.slice(0, Math.min(parts.length, MULTI_AI_ALIASES.length));
}

function usableMessage(value: string | undefined): string {
  const text = value?.trim();
  if (!text || STATUS_TOKENS.has(text)) return "";
  return text.slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS);
}

export function isPlaceholderName(value: string | null | undefined): boolean {
  const name = value?.trim() ?? "";
  return PLACEHOLDER_NAMES.has(name);
}

export function exactName(value: string | null | undefined): string {
  return usableName(value ?? undefined);
}

function projectValidated(current: (uid: string) => string | null): boolean {
  return current("CORE-01-BTN-PROJECT-VALIDATE") === "validated" && Boolean(exactName(current("CORE-01-CTL-PROJECT")));
}

function projectConfirmed(current: (uid: string) => string | null): boolean {
  const project = exactName(current("CORE-01-CTL-PROJECT"));
  if (!project) return false;
  return (
    current("CORE-01-BTN-PROJECT-CONFIRM") === "confirmed" ||
    current("CORE-01-BTN-PROJECT-LOCK") === project
  );
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

const WORK_ITEMS = new Set([
  "STORY",
  "CHAPTER",
  "WORLD_SETTING",
  "DNA",
  "BLUEPRINT",
  "TOPIC_SCOPE",
  "PRODUCTION_SCRIPT",
]);

export type CoreResumeStatus = "CURRENT" | "HISTORICAL" | "STALE" | "UNVERIFIED" | "BLOCKED";

export type CoreResumePointer = {
  conversation_id: string;
  thread_id: string;
  branch_id_optional: string;
  last_visible_server_sequence: number;
  context_snapshot_ref: string;
  context_fingerprint: string;
  extension_uid: string;
  scope_owner_ref: string;
  resume_reason: string;
  stale_resolution_status: CoreResumeStatus;
};

export type CoreThreadRecord = {
  title: string;
  workItem: string;
  parentThread?: string;
  sourceRef?: string;
  branchRef?: string;
  convRef?: string;
  resume?: CoreResumePointer;
};

export type CoreMessageRole = "user" | "assistant";

export type CoreMessageRecord = {
  thread: string;
  role: CoreMessageRole;
  text: string;
  seq: number;
  ref: string;
  alias?: string;
  at?: string;
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

export function ensureMessageIdentity(records: CoreMessageRecord[]): CoreMessageRecord[] {
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

export function parseMessageRecords(raw: string | null): CoreMessageRecord[] {
  if (!raw || raw === "sent" || STATUS_TOKENS.has(raw)) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      const text = usableMessage(raw);
      return text ? ensureMessageIdentity([{ thread: "", role: "user", text, seq: 0, ref: "" }]) : [];
    }
    const records: CoreMessageRecord[] = [];
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
      };
      const text = typeof rec.text === "string" ? rec.text.trim() : "";
      if (!text) continue;
      const role = rec.role === "assistant" ? "assistant" : rec.role === "user" ? "user" : null;
      if (!role) continue;
      const seq = typeof rec.seq === "number" && Number.isFinite(rec.seq) ? rec.seq : 0;
      const ref = typeof rec.ref === "string" ? rec.ref.trim() : "";
      const alias = typeof rec.alias === "string" ? rec.alias.trim() : "";
      const at = typeof rec.at === "string" ? rec.at.trim() : "";
      records.push({
        thread: typeof rec.thread === "string" ? rec.thread.trim() : "",
        role,
        text: text.slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS),
        seq,
        ref,
        ...(alias ? { alias } : {}),
        ...(at ? { at } : {}),
      });
    }
    return ensureMessageIdentity(records);
  } catch {
    const text = usableMessage(raw);
    return text ? ensureMessageIdentity([{ thread: "", role: "user", text, seq: 0, ref: "" }]) : [];
  }
}

export function messagesForThread(
  raw: string | null,
  thread: string,
  fallbackAssistant?: string | null,
): CoreMessageRecord[] {
  if (!thread) return [];
  const records = parseMessageRecords(raw);
  const scoped = records.filter((row) => row.thread === thread);
  if (scoped.length) return scoped;
  const unscoped = records.filter((row) => !row.thread).map((row) => ({ ...row, thread }));
  const extra = parseNotebookRecords(fallbackAssistant ?? null).length
    ? ""
    : usableMessage(fallbackAssistant ?? undefined);
  if (extra && extra !== unscoped[unscoped.length - 1]?.text) {
    return ensureMessageIdentity([...unscoped, { thread, role: "assistant", text: extra, seq: 0, ref: "" }]);
  }
  return unscoped;
}

export function recentHistoryPayload(
  records: CoreMessageRecord[],
): Array<{ role: CoreMessageRole; content: string }> {
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

export type CoreNotebookStatus = "CURRENT" | "STALE";

export type CoreNotebookRecord = {
  thread: string;
  version: number;
  status: CoreNotebookStatus;
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

export function parseNotebookRecords(raw: string | null): CoreNotebookRecord[] {
  if (!raw || STATUS_TOKENS.has(raw)) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return [];
    const payload = parsed as { kind?: unknown; records?: unknown };
    if (payload.kind !== "NOTEBOOK" || !Array.isArray(payload.records)) return [];
    const records: CoreNotebookRecord[] = [];
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

function coveredForNotebook(records: CoreMessageRecord[], mode: "overflow" | "record"): CoreMessageRecord[] {
  if (mode === "overflow") {
    const prior = records.length ? records.slice(0, -1) : [];
    if (prior.length > CONVERSATION_RECENT_HISTORY_ROWS) {
      return prior.slice(0, prior.length - CONVERSATION_RECENT_HISTORY_ROWS);
    }
    return [];
  }
  return records;
}

function buildNotebookBody(covered: CoreMessageRecord[], version: number, hash: string): string {
  const header = [
    `會議紀錄 版本 ${version}`,
    "狀態：現行",
    `涵蓋則數：${covered.length}`,
    `來源雜湊：${hash}`,
    "重要引用：",
  ];
  const footer = ["共識：—", "分歧：—", "未決問題：—", "後續事項：—"];
  const headerText = header.join("\n");
  const footerText = footer.join("\n");
  const budget = CONVERSATION_STORED_MESSAGE_TEXT_CHARS - headerText.length - footerText.length - 2;
  const refs: string[] = [];
  let used = 0;
  for (let index = 0; index < covered.length; index += 1) {
    const row = covered[index];
    const role = row.role === "user" ? "使用者" : "AI";
    const line = `- 第${index + 1}則（${role}）：${row.text.replace(/\s+/g, " ").trim()}`;
    const piece = (refs.length ? 1 : 0) + line.length;
    if (used + piece > Math.max(budget, 0)) break;
    refs.push(line);
    used += piece;
  }
  if (!refs.length) refs.push("—");
  return `${headerText}\n${refs.join("\n")}\n${footerText}`.slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS);
}

function serializeNotebookRecords(records: CoreNotebookRecord[]): string {
  const payload = JSON.stringify({ kind: "NOTEBOOK", records });
  if (payload.length <= CONVERSATION_STORED_MESSAGE_TEXT_CHARS) return payload;
  const shrunk = records.map((row) => ({
    ...row,
    body: row.body.slice(0, Math.max(200, Math.floor(CONVERSATION_STORED_MESSAGE_TEXT_CHARS / Math.max(records.length, 1) - 120))),
  }));
  return JSON.stringify({ kind: "NOTEBOOK", records: shrunk }).slice(0, CONVERSATION_STORED_MESSAGE_TEXT_CHARS);
}

export function refreshAssistantNotebook(
  current: (uid: string) => string | null,
  thread: string,
  records: CoreMessageRecord[],
  mode: "overflow" | "record" = "overflow",
): Record<string, string> {
  if (!thread) return {};
  const covered = coveredForNotebook(records, mode);
  if (!covered.length) return {};
  const hash = sourceHash(covered.map((row) => `${row.role}:${row.text}`));
  const existing = parseNotebookRecords(current("CORE-01-FLD-ASSISTANT-SUMMARY"));
  const prior = existing.find((row) => row.thread === thread && row.status === "CURRENT");
  if (prior && prior.sourceHash === hash) return {};
  const version = (prior?.version ?? 0) + 1;
  const next: CoreNotebookRecord = {
    thread,
    version,
    status: "CURRENT",
    coveredCount: covered.length,
    sourceHash: hash,
    body: buildNotebookBody(covered, version, hash),
  };
  const others = existing.filter((row) => row.thread !== thread).map((row) => ({ ...row, status: "CURRENT" as const }));
  return { "CORE-01-FLD-ASSISTANT-SUMMARY": serializeNotebookRecords([...others, next]) };
}

export function formatCoreChatContext(current: (uid: string) => string | null): string {
  const lines: string[] = [];
  const project = exactName(current("CORE-01-CTL-PROJECT"));
  const topic = exactName(current("CORE-01-CTL-TOPIC"));
  const workItem = currentWorkItem(current);
  const thread = activeThreadUid(current);
  if (project) lines.push(`專案：${project}`);
  if (topic) lines.push(`專題：${topic}`);
  if (workItem) lines.push(`工作項目：${workItem}`);
  if (thread) lines.push(`對話：${thread}`);
  const notebook = notebookTextForThread(current("CORE-01-FLD-ASSISTANT-SUMMARY"), thread);
  if (notebook) lines.push(`筆記本：\n${notebook}`);
  return lines.join("\n");
}

export function appendAssistantMessage(
  current: (uid: string) => string | null,
  thread: string,
  reply: string,
  alias?: string,
  at?: string,
): Record<string, string> {
  const text = reply.trim();
  if (!thread || !text) return {};
  const records = parseMessageRecords(current("CORE-01-FLD-MESSAGE"));
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
    },
  ]);
  const patched = (uid: string) => (uid === "CORE-01-FLD-MESSAGE" ? JSON.stringify(nextMessages) : current(uid));
  return {
    "CORE-01-FLD-MESSAGE": JSON.stringify(nextMessages),
    ...persistResumeOnThreads(patched, thread, "RESPONSE"),
  };
}

export function appendAssistantMessages(
  current: (uid: string) => string | null,
  thread: string,
  replies: Array<{ text: string; alias?: string; at?: string }>,
): Record<string, string> {
  if (!thread || !replies.length) return {};
  let records = parseMessageRecords(current("CORE-01-FLD-MESSAGE"));
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
      },
    ]);
    const patched = (uid: string) => (uid === "CORE-01-FLD-MESSAGE" ? JSON.stringify(records) : current(uid));
    lastPatch = {
      "CORE-01-FLD-MESSAGE": JSON.stringify(records),
      ...persistResumeOnThreads(patched, thread, "RESPONSE"),
    };
  }
  return lastPatch;
}

const RESUME_STATUSES = new Set<CoreResumeStatus>(["CURRENT", "HISTORICAL", "STALE", "UNVERIFIED", "BLOCKED"]);

function parseResumePointer(raw: unknown): CoreResumePointer | undefined {
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
    extension_uid: typeof rec.extension_uid === "string" ? rec.extension_uid.trim() : "CORE-01",
    scope_owner_ref: typeof rec.scope_owner_ref === "string" ? rec.scope_owner_ref.trim() : "",
    resume_reason: typeof rec.resume_reason === "string" ? rec.resume_reason.trim() : "",
    stale_resolution_status: RESUME_STATUSES.has(status as CoreResumeStatus) ? (status as CoreResumeStatus) : "UNVERIFIED",
  };
}

export function contextFingerprint(current: (uid: string) => string | null): string {
  return sourceHash([
    exactName(current("CORE-01-CTL-PROJECT")),
    exactName(current("CORE-01-CTL-TOPIC")),
    currentWorkItem(current),
    exactName(current("CORE-01-BTN-DNA-LOCK")),
    exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE")),
    exactName(current("CORE-01-BTN-CANONICAL-SCRIPT")),
    current("CORE-01-BTN-PROJECT-CONFIRM") ?? "",
    current("CORE-01-BTN-PROJECT-LOCK") ?? "",
  ]);
}

export function contextSnapshotRef(current: (uid: string) => string | null): string {
  const project = exactName(current("CORE-01-CTL-PROJECT")) || "UNBOUND";
  const topic = exactName(current("CORE-01-CTL-TOPIC")) || "NONE";
  const work = currentWorkItem(current) || "NONE";
  return `SNAP:${project}/${topic}/${work}`;
}

function lastVisibleSequence(current: (uid: string) => string | null, thread: string): number {
  const messages = messagesForThread(current("CORE-01-FLD-MESSAGE"), thread);
  return messages.reduce((max, row) => Math.max(max, row.seq || 0), 0);
}

export function buildResumePointer(
  current: (uid: string) => string | null,
  thread: CoreThreadRecord,
  reason: string,
  status: CoreResumeStatus = "CURRENT",
): CoreResumePointer {
  return {
    conversation_id: thread.convRef || "",
    thread_id: thread.title,
    branch_id_optional: thread.branchRef || "",
    last_visible_server_sequence: lastVisibleSequence(current, thread.title),
    context_snapshot_ref: contextSnapshotRef(current),
    context_fingerprint: contextFingerprint(current),
    extension_uid: "CORE-01",
    scope_owner_ref: exactName(current("CORE-01-CTL-PROJECT")),
    resume_reason: reason,
    stale_resolution_status: status,
  };
}

export function persistResumeOnThreads(
  current: (uid: string) => string | null,
  threadTitle: string,
  reason: string,
  records?: CoreThreadRecord[],
): Record<string, string> {
  const identified = ensureThreadIdentity(records ?? parseThreadRecords(current("CORE-01-BTN-NEW-THREAD")));
  const next = identified.map((row) =>
    row.title === threadTitle ? { ...row, resume: buildResumePointer(current, row, reason) } : row,
  );
  return { "CORE-01-BTN-NEW-THREAD": JSON.stringify(next) };
}

export function resolveResumePointer(
  current: (uid: string) => string | null,
  threadTitle?: string,
): CoreResumePointer | null {
  const title = threadTitle || activeThreadUid(current);
  if (!title) return null;
  const thread = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD")).find((row) => row.title === title);
  if (!thread?.resume) return null;
  const fingerprint = contextFingerprint(current);
  const drifted = Boolean(thread.resume.context_fingerprint && thread.resume.context_fingerprint !== fingerprint);
  return {
    ...thread.resume,
    context_snapshot_ref: contextSnapshotRef(current),
    stale_resolution_status: drifted ? "STALE" : thread.resume.stale_resolution_status,
  };
}

function ensureThreadIdentity(records: CoreThreadRecord[]): CoreThreadRecord[] {
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

export function parseThreadRecords(raw: string | null): CoreThreadRecord[] {
  if (!raw || raw === "created") return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      const title = usableName(raw);
      return title ? ensureThreadIdentity([{ title, workItem: "" }]) : [];
    }
    const records: CoreThreadRecord[] = [];
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
      records.push({
        title,
        workItem: typeof rec.workItem === "string" && WORK_ITEMS.has(rec.workItem) ? rec.workItem : "",
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

export function currentWorkItem(current: (uid: string) => string | null): string {
  const stored = current("CORE-01-LST-WORK-ITEMS") ?? "";
  if (WORK_ITEMS.has(stored)) return stored;
  if (!exactName(current("CORE-01-CTL-PROJECT"))) return "";
  const topicMode =
    current("CORE-01-FLD-PAGE-MODE") === "TOPIC_PRODUCTION" && Boolean(exactName(current("CORE-01-CTL-TOPIC")));
  return topicMode ? "TOPIC_SCOPE" : "STORY";
}

export function threadScopeReady(current: (uid: string) => string | null): boolean {
  return Boolean(exactName(current("CORE-01-CTL-PROJECT")) && currentWorkItem(current));
}

export function threadsForCurrentWorkItem(current: (uid: string) => string | null): CoreThreadRecord[] {
  const workItem = currentWorkItem(current);
  if (!workItem) return [];
  return parseThreadRecords(current("CORE-01-BTN-NEW-THREAD")).filter((row) => row.workItem === workItem);
}

export function activeThreadUid(current: (uid: string) => string | null): string {
  const scoped = threadsForCurrentWorkItem(current);
  const stored = current("CORE-01-LST-THREADS");
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

export type CoreTokenKind =
  | "TARGET_PARTICIPANT"
  | "TARGET_ALL_PARTICIPANTS"
  | "TARGET_ASSISTANT"
  | "MESSAGE_REF"
  | "ASSISTANT_REF"
  | "CONVERSATION_REF"
  | "BRANCH_REF"
  | "PARSER_ERROR"
  | "AMBIGUOUS_REF";

export type CoreResolvedToken = {
  raw: string;
  kind: CoreTokenKind;
  canonical: string;
};

export function targetedParticipantAliases(
  tokens: CoreResolvedToken[],
  current: (uid: string) => string | null,
): string[] {
  const aliases = assignedParticipantAliases(current);
  if (!aliases.length) return [];
  const named = tokens
    .filter((row) => row.kind === "TARGET_PARTICIPANT")
    .map((row) => row.canonical.replace(/^@/, ""))
    .filter((alias) => aliases.includes(alias));
  if (tokens.some((row) => row.kind === "TARGET_ALL_PARTICIPANTS") || named.length === 0) return aliases;
  return aliases.filter((alias) => named.includes(alias));
}

const COMPOSER_TOKEN = /(@全部AI|@助理|@[ABC]|#AI-\d+|#AST-\d+|#CONV-\d+|#BR-\d+|#MSG-\d+|#\d+)/gu;

function assistantRefForThread(current: (uid: string) => string | null, thread: string): string {
  const notes = parseNotebookRecords(current("CORE-01-FLD-ASSISTANT-SUMMARY"));
  const match = notes.find((row) => row.thread === thread);
  return match ? padRef("#AST", match.version) : "";
}

function shortNumber(raw: string): string {
  const digits = raw.replace(/\D/g, "").replace(/^0+/, "") || "0";
  return digits;
}

export function resolveComposerTokens(
  text: string,
  current: (uid: string) => string | null,
): CoreResolvedToken[] {
  const thread = activeThreadUid(current);
  const messages = messagesForThread(current("CORE-01-FLD-MESSAGE"), thread);
  const threads = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD"));
  const multi = isMultiAiMode(current);
  const tokens: CoreResolvedToken[] = [];
  COMPOSER_TOKEN.lastIndex = 0;
  let match: RegExpExecArray | null = COMPOSER_TOKEN.exec(text);
  while (match) {
    const raw = match[0];
    if (raw === "@A" || raw === "@B" || raw === "@C") {
      const alias = raw.slice(1);
      tokens.push(
        multi && assignedParticipantAliases(current).includes(alias)
          ? { raw, kind: "TARGET_PARTICIPANT", canonical: raw }
          : { raw, kind: "PARSER_ERROR", canonical: "" },
      );
    } else if (raw === "@全部AI") {
      tokens.push({ raw, kind: "TARGET_ALL_PARTICIPANTS", canonical: raw });
    } else if (raw === "@助理") {
      tokens.push({ raw, kind: "TARGET_ASSISTANT", canonical: raw });
    } else if (raw.startsWith("#AST-")) {
      const ast = assistantRefForThread(current, thread);
      tokens.push(
        ast && ast === padRef("#AST", Number.parseInt(raw.slice(5).replace(/^0+/, "") || "0", 10) || 0)
          ? { raw, kind: "ASSISTANT_REF", canonical: ast }
          : { raw, kind: "PARSER_ERROR", canonical: "" },
      );
    } else if (raw.startsWith("#CONV-")) {
      const hit = threads.find((row) => row.convRef === padRef("#CONV", Number.parseInt(raw.slice(6).replace(/^0+/, "") || "0", 10) || 0));
      tokens.push(hit?.convRef ? { raw, kind: "CONVERSATION_REF", canonical: hit.convRef } : { raw, kind: "PARSER_ERROR", canonical: "" });
    } else if (raw.startsWith("#BR-")) {
      const hit = threads.find((row) => row.branchRef === padRef("#BR", Number.parseInt(raw.slice(4).replace(/^0+/, "") || "0", 10) || 0));
      tokens.push(hit?.branchRef ? { raw, kind: "BRANCH_REF", canonical: hit.branchRef } : { raw, kind: "PARSER_ERROR", canonical: "" });
    } else {
      const num = shortNumber(raw);
      const prefix = raw.startsWith("#AI-") ? "#AI" : raw.startsWith("#MSG-") ? "#MSG" : "";
      const hits = prefix
        ? messages.filter((row) => row.ref === padRef(prefix, Number.parseInt(num, 10) || 0))
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

export function composerHasBlockingToken(tokens: CoreResolvedToken[]): boolean {
  return tokens.some((row) => row.kind === "PARSER_ERROR" || row.kind === "AMBIGUOUS_REF");
}

export function quoteInsertText(ref: string): string {
  return ref ? `${ref} ` : "";
}

export type CoreMessageActionPayload = {
  actionUid: string;
  messageRef?: string;
};

export function parseMessageActionPayload(nextValue?: string): CoreMessageActionPayload {
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
  current: (uid: string) => string | null,
  messageRef?: string,
): CoreMessageRecord | null {
  const thread = activeThreadUid(current);
  if (!thread || !messageRef) return null;
  const tokens = resolveComposerTokens(messageRef, current);
  const resolved = tokens.find((row) => row.kind === "MESSAGE_REF")?.canonical ?? messageRef;
  return messagesForThread(current("CORE-01-FLD-MESSAGE"), thread).find((row) => row.ref === resolved) ?? null;
}

export function previewMessageAction(
  actionUid: string,
  current: (uid: string) => string | null,
  messageRef?: string,
): Record<string, string> {
  const thread = activeThreadUid(current);
  if (!thread) return {};
  const message = findThreadMessage(current, messageRef);
  if (!message) return {};
  if (actionUid === "CORE-01-ACT-MSG-QUOTE" || actionUid === "CORE-01-ACT-MSG-CONTINUE" || actionUid === "CORE-01-ACT-MSG-COPY") {
    return {};
  }
  if (actionUid === "CORE-01-ACT-MSG-ANALYZE") {
    const prompt = `分析此內容 ${message.ref}`;
    return previewCoreAction("CORE-01-BTN-SEND", "CORE-01-ACT-SEND", current, prompt);
  }
  if (actionUid === "CORE-01-ACT-MSG-DECISION") {
    const existing = usableMessage(current("CORE-01-FLD-HUMAN-DECISION") ?? undefined);
    const next = existing && existing !== "confirmed" && existing !== "recorded"
      ? (existing.includes(message.ref) ? existing : `${existing}、${message.ref}`)
      : message.ref;
    return {
      "CORE-01-FLD-HUMAN-DECISION": next,
      "CORE-01-FLD-RUNTIME-STAGE": "HUMAN_DECISION",
    };
  }
  if (actionUid === "CORE-01-ACT-MSG-BRANCH") {
    const records = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD"));
    const workItem = currentWorkItem(current);
    const scoped = records.filter((row) => row.workItem === workItem);
    const title = namedValue(undefined, `分支 ${scoped.length + 1}`);
    const nextRecords = ensureThreadIdentity([
      ...records,
      { title, workItem, parentThread: thread, sourceRef: message.ref },
    ]);
    const patched = (uid: string) => (uid === "CORE-01-LST-THREADS" ? title : current(uid));
    return {
      "CORE-01-LST-THREADS": title,
      ...persistResumeOnThreads(patched, title, "BRANCH", nextRecords),
    };
  }
  return {};
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
      ...(pkg ? { "CORE-01-FLD-PACKAGE": pkg } : {}),
      "CORE-01-LST-WORK-ITEMS": "TOPIC_SCOPE",
      "CORE-01-BTN-TOPIC-CREATE": JSON.stringify(nextList),
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
    const list = namedList(current("CORE-01-BTN-PROJECT-CREATE"), previous).map((item) => (item === previous ? project : item));
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
    const list = namedList(current("CORE-01-BTN-TOPIC-CREATE"), previous).map((item) => (item === previous ? topic : item));
    const nextList = list.includes(topic) ? list : [...list, topic];
    return {
      "CORE-01-CTL-TOPIC": topic,
      "CORE-01-FLD-PAGE-MODE": "TOPIC_PRODUCTION",
      "CORE-01-FLD-TOPIC-SCOPE": topic,
      "CORE-01-LST-WORK-ITEMS": "TOPIC_SCOPE",
      "CORE-01-BTN-TOPIC-CREATE": JSON.stringify(nextList),
    };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-FLD-TOPIC-SCOPE") {
    if (!projectConfirmed(current)) return {};
    const topic = exactName(nextValue) || exactName(current("CORE-01-CTL-TOPIC")) || exactName(current("CORE-01-FLD-TOPIC-SCOPE"));
    return topic ? { "CORE-01-FLD-TOPIC-SCOPE": topic } : {};
  }
  if (actionUid === "CORE-01-ACT-AI-MODE-SINGLE") {
    return {
      "CORE-01-BTN-SINGLE-AI": "active",
      "CORE-01-BTN-MULTI-AI": "idle",
    };
  }
  if (actionUid === "CORE-01-ACT-AI-MODE-MULTI") {
    if (!assignedAiRouteReady(current)) return {};
    return {
      "CORE-01-BTN-MULTI-AI": "active",
      "CORE-01-BTN-SINGLE-AI": "idle",
    };
  }
  if (actionUid === "CORE-01-ACT-THREAD-CREATE") {
    if (!threadScopeReady(current)) return {};
    const workItem = currentWorkItem(current);
    const records = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD"));
    const scoped = records.filter((row) => row.workItem === workItem);
    const title = namedValue(nextValue, `對話 ${scoped.length + 1}`);
    const exists = records.some((row) => row.title === title && row.workItem === workItem);
    const nextRecords = ensureThreadIdentity(exists ? records : [...records, { title, workItem }]);
    const patched = (uid: string) => (uid === "CORE-01-LST-THREADS" ? title : current(uid));
    return {
      "CORE-01-LST-THREADS": title,
      ...persistResumeOnThreads(patched, title, "CREATE", nextRecords),
    };
  }
  if (actionUid.startsWith("CORE-01-ACT-MSG-")) {
    const payload = parseMessageActionPayload(nextValue);
    return previewMessageAction(actionUid, current, payload.messageRef || nextValue);
  }
  if (actionUid === "CORE-01-ACT-SEND") {
    const thread = activeThreadUid(current);
    if (!thread || !hasSendableMessage(nextValue)) return {};
    const message = usableMessage(nextValue);
    if (!message) return {};
    const tokens = resolveComposerTokens(message, current);
    if (composerHasBlockingToken(tokens)) return {};
    if (!tokens.some((row) => row.kind === "TARGET_ASSISTANT") && !assignedAiRouteReady(current)) return {};
    if (tokens.some((row) => row.kind === "TARGET_ASSISTANT")) {
      const records = parseMessageRecords(current("CORE-01-FLD-MESSAGE"));
      const nextRecords = ensureMessageIdentity([...records, { thread, role: "user", text: message, seq: 0, ref: "" }]);
      const notebookPatch = refreshAssistantNotebook(
        (uid) => (uid === "CORE-01-FLD-MESSAGE" ? JSON.stringify(nextRecords) : current(uid)),
        thread,
        messagesForThread(JSON.stringify(nextRecords), thread),
        "record",
      );
      const patched = (uid: string) => (uid === "CORE-01-FLD-MESSAGE" ? JSON.stringify(nextRecords) : current(uid));
      return {
        "CORE-01-FLD-MESSAGE": JSON.stringify(nextRecords),
        "CORE-01-BTN-SEND": "sent",
        "CORE-01-BTN-ASSISTANT-RECORD": "recorded",
        "CORE-01-FLD-RUNTIME-STAGE": "ASSISTANT_SUMMARY",
        ...notebookPatch,
        ...persistResumeOnThreads(patched, thread, "ASSISTANT"),
      };
    }
    const attachment = usableName(current("CORE-01-BTN-ATTACHMENT") ?? undefined);
    const reference = usableName(current("CORE-01-BTN-REFERENCE") ?? undefined);
    const files = [attachment, reference].filter(Boolean);
    const summary = files.length ? `${message} · ${files.join("、")}` : message;
    let records = parseMessageRecords(current("CORE-01-FLD-MESSAGE"));
    if (!records.some((row) => row.thread === thread)) {
      records = records.map((row) => (row.thread ? row : { ...row, thread }));
      const priorSummary = current("CORE-01-FLD-ASSISTANT-SUMMARY");
      const priorNotebook = parseNotebookRecords(priorSummary ?? null);
      const prior = priorNotebook.length ? "" : usableMessage(priorSummary ?? undefined);
      const scopedMessages = records.filter((row) => row.thread === thread);
      const last = scopedMessages[scopedMessages.length - 1]?.text;
      if (prior && prior !== last && prior !== summary) {
        records = [...records, { thread, role: "assistant", text: prior, seq: 0, ref: "" }];
      }
    }
    const nextRecords = ensureMessageIdentity([...records, { thread, role: "user", text: summary, seq: 0, ref: "" }]);
    const notebookPatch = refreshAssistantNotebook(current, thread, nextRecords, "overflow");
    const patched = (uid: string) => (uid === "CORE-01-FLD-MESSAGE" ? JSON.stringify(nextRecords) : current(uid));
    return {
      "CORE-01-FLD-MESSAGE": JSON.stringify(nextRecords),
      "CORE-01-FLD-RUNTIME-STAGE": "AI_RESPONSES",
      "CORE-01-BTN-SEND": "sent",
      ...notebookPatch,
      ...persistResumeOnThreads(patched, thread, "SEND"),
    };
  }
  if (actionUid === "CORE-01-ACT-ASSISTANT-RECORD") {
    const thread = activeThreadUid(current);
    if (!thread) return {};
    const records = messagesForThread(current("CORE-01-FLD-MESSAGE"), thread);
    if (!records.length) return {};
    const notebookPatch = refreshAssistantNotebook(current, thread, records, "record");
    if (!Object.keys(notebookPatch).length) {
      return { "CORE-01-BTN-ASSISTANT-RECORD": "recorded" };
    }
    return {
      ...notebookPatch,
      "CORE-01-BTN-ASSISTANT-RECORD": "recorded",
      "CORE-01-FLD-RUNTIME-STAGE": "ASSISTANT_SUMMARY",
      ...persistResumeOnThreads(current, thread, "ASSISTANT_RECORD"),
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
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-ACCEPT") {
    return {
      "CORE-01-BTN-CANDIDATE-CONFIRM": "confirmed",
      "CORE-01-FLD-LOCK-REVIEW": "ready",
      "CORE-01-FLD-HUMAN-DECISION": "confirmed",
    };
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
    const dna = exactName(nextValue) || exactName(current("CORE-01-BTN-DNA-LOCK"));
    if (dna) return { "CORE-01-BTN-DNA-LOCK": dna };
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    return project ? { "CORE-01-BTN-DNA-LOCK": "locked" } : {};
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
  if (actionUid === "CORE-01-ACT-CANONICAL-SCRIPT-VIEW") {
    const script = exactName(nextValue) || exactName(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    if (!script) return {};
    const pkg = exactName(current("CORE-01-FLD-PACKAGE"));
    return {
      "CORE-01-BTN-CANONICAL-SCRIPT": script,
      ...(pkg ? { "CORE-01-FLD-PACKAGE": pkg } : {}),
    };
  }
  if (actionUid === "CORE-01-ACT-CORE-REVIEW-SUBMIT") {
    return {
      "CORE-01-BTN-CORE-REVIEW": "sent",
      "CORE-01-FLD-LOCK-REVIEW": current("CORE-01-FLD-LOCK-REVIEW") || "ready",
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
    const pkg = exactName(nextValue) || exactName(current("CORE-01-FLD-PACKAGE")) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    return pkg ? { "CORE-01-FLD-PACKAGE": pkg } : {};
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid.startsWith("CORE-01-FLD-DOWNSTREAM")) {
    const existing = usableName(current(controlUid) ?? undefined);
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
  if (actionUid === "CORE-01-ACT-THREAD-SELECT") {
    const workItem = currentWorkItem(current);
    if (!workItem) return {};
    const title = exactName(nextValue) || exactName(current("CORE-01-LST-THREADS"));
    if (!title) return {};
    const match = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD")).find(
      (row) => row.title === title && row.workItem === workItem,
    );
    if (!match) return {};
    const patched = (uid: string) => (uid === "CORE-01-LST-THREADS" ? title : current(uid));
    return {
      "CORE-01-LST-THREADS": title,
      ...persistResumeOnThreads(patched, title, "SELECT"),
    };
  }
  if (controlUid === "CORE-01-FLD-RUNTIME-STAGE") {
    return { "CORE-01-FLD-RUNTIME-STAGE": nextValue || current("CORE-01-FLD-RUNTIME-STAGE") || "AI_RESPONSES" };
  }
  const existing = current(controlUid);
  if (!nextValue && existing && !STATUS_TOKENS.has(existing) && actionUid.includes("-SELECT")) {
    return { [controlUid]: existing };
  }
  return { [controlUid]: nextValue ?? statusFromAction(actionUid) };
}
