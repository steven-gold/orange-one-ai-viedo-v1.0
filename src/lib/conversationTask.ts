export const LARGE_TASK_BATCH_ITEMS = 20;
export const MAX_GENERATION_CONTINUATIONS = 3;
export const MAX_LOOP_REPAIRS = 1;
export const STREAM_LOOP_CHECK_MIN_CHARS = 80;
export const STREAM_LOOP_CHECK_EVERY_CHARS = 32;

export type ConversationTaskKind =
  | "question"
  | "knowledge"
  | "writing"
  | "code"
  | "analysis"
  | "creation"
  | "large"
  | "system"
  | "insufficient"
  | "restricted";

export type ConversationTaskStatus = "OPEN" | "PARTIAL" | "COMPLETE" | "FAILED" | "STOPPED";

export type GenerationStreamSink = {
  token: (text: string, alias?: string) => void;
  status: (status: ConversationTaskStatus) => void;
};

export type ConversationTaskObservation = {
  chars: number;
  durationMs: number;
  loop: boolean;
  truncated: boolean;
  failReason: string;
};

export type ConversationTaskContract = {
  taskId: string;
  thread: string;
  rawDemand: string;
  goal: string;
  kind: ConversationTaskKind;
  mustComplete: string[];
  quantity?: { count: number; unit: string };
  duration?: string;
  language: string;
  format?: string;
  constraints: string[];
  forbidden: string[];
  success: string[];
  batched: boolean;
  needsFile: boolean;
  needsExternal: boolean;
  status: ConversationTaskStatus;
  completedItems: string[];
  pendingItems: string[];
  nextBatch?: string;
  resumeCursor?: string;
  fileId?: string;
  fileName?: string;
  batchSize: number;
  version: number;
  observation?: ConversationTaskObservation;
};

export type GenerationMonitor = {
  loop: boolean;
  reason: string;
  validPrefix: string;
};

const CONTINUE_RE = /繼續(討論|生成|寫|作|產出)?|續寫|接著寫|下一[批批次集]/u;
const CATALOG_RE = /每一章|章節名稱|每集名稱|各集名稱|各章名稱|每一集/u;
const EPISODE_RE = /(?:大約|約)?(\d+)\s*集/u;
const MINUTE_RE = /每集\s*(?:約)?\s*(\d+)\s*分鐘/u;
const COUNT_RE = /(?:大約|約)?(\d+)\s*(章|回|篇|則|項|集)/u;

function clean(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function unique(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const value of values) {
    const item = clean(value);
    if (!item || seen.has(item)) continue;
    seen.add(item);
    out.push(item);
  }
  return out;
}

function hashId(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function isContinueRequest(text: string): boolean {
  const body = clean(text);
  return CONTINUE_RE.test(body) || CATALOG_RE.test(body);
}

export function modelBlockedForLanguage(model: string, language = "zh-TW"): boolean {
  const id = clean(model).toLowerCase();
  if (!id) return false;
  return id.includes("allam") && language !== "en";
}

export function classifyTaskKind(text: string): ConversationTaskKind {
  const body = clean(text);
  if (!body) return "insufficient";
  if (isContinueRequest(body)) return "writing";
  if (/(刪除|部署|付款|權限|鎖)/u.test(body) && /(執行|送出|寫入)/u.test(body)) return "system";
  if (/(計算|比較|分析|統計|驗證)/u.test(body)) return "analysis";
  if (/(程式|代碼|code|function|修 bug)/iu.test(body)) return "code";
  if (EPISODE_RE.test(body) || /(完整故事|系列|長篇|全部集)/u.test(body)) return "large";
  if (/(寫|製作|創作|劇本|故事|影片|大綱)/u.test(body)) return "creation";
  if (/(什麼是|為什麼|如何定義|誰是)/u.test(body)) return "knowledge";
  if (body.length < 40 && /[?？]$/u.test(body)) return "question";
  return "question";
}

function parseQuantity(text: string): { count: number; unit: string } | undefined {
  const episode = EPISODE_RE.exec(text);
  if (episode) {
    const count = Number.parseInt(episode[1], 10);
    if (Number.isFinite(count) && count > 0) return { count, unit: "集" };
  }
  const generic = COUNT_RE.exec(text);
  if (generic) {
    const count = Number.parseInt(generic[1], 10);
    if (Number.isFinite(count) && count > 0) return { count, unit: generic[2] };
  }
  return undefined;
}

function parseDuration(text: string): string | undefined {
  const match = MINUTE_RE.exec(text);
  if (!match) return undefined;
  return `每集${match[1]}分鐘`;
}

function parseConstraints(text: string): string[] {
  const body = clean(text);
  const found: string[] = [];
  if (/搞笑/u.test(body)) found.push("語氣：搞笑");
  if (/80\s*年代/u.test(body)) found.push("時代：80年代網路遊戲");
  if (/天堂/u.test(body)) found.push("參考作品僅作靈感，必須原創角色與故事");
  if (/繁體|正體/u.test(body)) found.push("語言：繁體中文");
  return found;
}

function parseForbidden(text: string, kind: ConversationTaskKind): string[] {
  const forbidden = ["不得把分析當成執行", "未完成不得宣稱全部完成"];
  if (kind === "creation" || kind === "large") {
    forbidden.push("不得自行添加未指定的受眾、平台或限制");
    forbidden.push("不得只回覆通用製作建議");
  }
  if (/天堂/u.test(text)) forbidden.push("不得複製參考作品的角色與劇情");
  return unique(forbidden);
}

export function planQuantityBatches(
  quantity: { count: number; unit: string } | undefined,
  batchSize = LARGE_TASK_BATCH_ITEMS,
  completedThrough = 0,
): { completedItems: string[]; pendingItems: string[]; nextBatch?: string; batched: boolean } {
  if (!quantity || quantity.count <= 1) {
    return { completedItems: [], pendingItems: [], batched: false };
  }
  const size = Math.max(1, batchSize);
  const start = Math.min(Math.max(completedThrough, 0), quantity.count);
  if (start >= quantity.count) {
    return { completedItems: [`第1–${quantity.count}${quantity.unit}`], pendingItems: [], batched: true };
  }
  const end = Math.min(start + size, quantity.count);
  const nextBatch = `第${start + 1}–${end}${quantity.unit}`;
  const pending =
    end < quantity.count ? [`第${end + 1}–${quantity.count}${quantity.unit}`] : [];
  const completedItems = start > 0 ? [`第1–${start}${quantity.unit}`] : [];
  return {
    completedItems,
    pendingItems: [nextBatch, ...pending],
    nextBatch,
    batched: true,
  };
}

export function buildTaskContract(
  prompt: string,
  prior?: ConversationTaskContract | null,
  thread = "",
): ConversationTaskContract {
  const raw = clean(prompt);
  if (prior && isContinueRequest(raw)) {
    const restart = CATALOG_RE.test(raw) && !CONTINUE_RE.test(raw);
    const planned = planQuantityBatches(prior.quantity, prior.batchSize, restart ? 0 : completedCount(prior));
    return {
      ...prior,
      thread: prior.thread || thread,
      status: prior.status === "COMPLETE" && !restart ? "COMPLETE" : "PARTIAL",
      completedItems: planned.completedItems,
      pendingItems: planned.pendingItems.length ? planned.pendingItems : prior.pendingItems,
      nextBatch: planned.nextBatch ?? prior.nextBatch,
      version: prior.version + 1,
    };
  }

  const kind = classifyTaskKind(raw);
  const quantity = parseQuantity(raw) ?? prior?.quantity;
  const duration = parseDuration(raw) ?? prior?.duration;
  const constraints = unique([...(prior?.constraints ?? []), ...parseConstraints(raw)]);
  const batchedKind = kind === "large" || (quantity != null && quantity.count > LARGE_TASK_BATCH_ITEMS);
  const resolvedKind: ConversationTaskKind = batchedKind ? "large" : kind;
  const planned = planQuantityBatches(quantity, LARGE_TASK_BATCH_ITEMS, prior ? completedCount(prior) : 0);
  const language = /簡體/u.test(raw) ? "zh-CN" : "zh-TW";
  const format = duration && quantity?.unit === "集" ? "分集影片故事大綱" : prior?.format;
  const goal = raw || prior?.goal || "";
  const mustComplete = unique([
    ...(prior?.mustComplete ?? []),
    ...(quantity ? [`產出 ${quantity.count}${quantity.unit}`] : []),
    ...(duration ? [duration] : []),
    ...constraints,
  ]);
  const mergedRaw = prior && raw && !isContinueRequest(raw) && raw.length < prior.rawDemand.length && !quantity
    ? prior.rawDemand
    : raw || prior?.rawDemand || "";
  const finalRaw = quantity && prior?.rawDemand && parseQuantity(raw)
    ? raw
    : mergedRaw;
  const forbidden = parseForbidden(finalRaw, resolvedKind);
  const success = unique([
    "完成使用者要求的實際交付",
    ...(planned.batched ? ["分批產出並保留未完成範圍"] : []),
  ]);
  const taskId = prior?.taskId || `TASK-${hashId([thread, finalRaw])}`;
  return {
    taskId,
    thread: thread || prior?.thread || "",
    rawDemand: finalRaw,
    goal: parseQuantity(raw) && prior?.goal ? rewriteGoalQuantity(prior.goal, quantity) : goal || finalRaw,
    kind: resolvedKind,
    mustComplete,
    quantity,
    duration,
    language,
    format,
    constraints,
    forbidden,
    success,
    batched: planned.batched,
    needsFile: planned.batched || resolvedKind === "writing" || resolvedKind === "creation",
    needsExternal: false,
    status: planned.batched ? "OPEN" : "OPEN",
    completedItems: planned.completedItems,
    pendingItems: planned.pendingItems,
    nextBatch: planned.nextBatch,
    resumeCursor: prior?.resumeCursor,
    batchSize: LARGE_TASK_BATCH_ITEMS,
    version: (prior?.version ?? 0) + 1,
  };
}

function rewriteGoalQuantity(goal: string, quantity?: { count: number; unit: string }): string {
  if (!quantity) return goal;
  return goal.replace(EPISODE_RE, `${quantity.count}集`);
}

export function completedCount(contract: ConversationTaskContract): number {
  const last = contract.completedItems.join(" ");
  const match = /第\s*\d+\s*[–-]\s*(\d+)/u.exec(last);
  if (!match) return 0;
  const value = Number.parseInt(match[1], 10);
  return Number.isFinite(value) ? value : 0;
}

export function latestOpenTask(
  tasks: ConversationTaskContract[],
  thread?: string,
): ConversationTaskContract | null {
  const scoped = thread ? tasks.filter((row) => !row.thread || row.thread === thread) : tasks;
  for (let index = scoped.length - 1; index >= 0; index -= 1) {
    const row = scoped[index];
    if (row.status === "OPEN" || row.status === "PARTIAL" || row.status === "STOPPED" || row.status === "FAILED") return row;
  }
  return scoped[scoped.length - 1] ?? null;
}

export function formatContractForPrompt(contract: ConversationTaskContract): string {
  if (contract.kind === "question" && !contract.batched) return "";
  const lines = [
    `目標：${contract.goal}`,
    `類型：${contract.kind}`,
    contract.quantity ? `數量：${contract.quantity.count}${contract.quantity.unit}` : "",
    contract.duration ? `時長：${contract.duration}` : "",
    contract.format ? `格式：${contract.format}` : "",
    contract.constraints.length ? `限制：${contract.constraints.join("；")}` : "",
    contract.forbidden.length ? `禁止：${contract.forbidden.join("；")}` : "",
    contract.nextBatch ? `本批次只產出：${contract.nextBatch}` : "",
    contract.pendingItems.length ? `尚未完成：${contract.pendingItems.join("；")}` : "",
    contract.resumeCursor ? `從上次結尾續寫，禁止重複。` : "",
    "未完成範圍必須標示。禁止宣稱全部完成。",
  ];
  return lines.filter(Boolean).join("\n");
}

export function formatDeliveryFooter(contract: ConversationTaskContract): string {
  if (contract.kind === "question" && !contract.batched && contract.status === "COMPLETE") return "";
  if (!contract.batched && contract.status === "COMPLETE") return "";
  const lines = [
    `狀態：${statusLabel(contract.status)}`,
    contract.completedItems.length ? `已完成：${contract.completedItems.join("；")}` : "",
    contract.pendingItems.length ? `未完成：${contract.pendingItems.join("；")}` : "",
    contract.nextBatch && contract.status !== "COMPLETE" ? `下一合法批次：${contract.nextBatch}` : "",
    contract.status === "PARTIAL" || contract.status === "OPEN" || contract.status === "STOPPED" ? "可續寫；未完成不得視為全部完成。" : "",
    contract.fileName ? `成品：${contract.fileName}` : "",
    contract.fileId ? `檔案：${contract.fileId}` : "",
    formatObservationLine(contract.observation),
    contract.observation?.failReason ? `失敗原因：${contract.observation.failReason}` : "",
  ];
  return lines.filter(Boolean).join("\n");
}

function formatObservationLine(observation?: ConversationTaskObservation): string {
  if (!observation) return "";
  const seconds = Math.max(0, Math.round(observation.durationMs / 100) / 10);
  const parts = [`字數 ${observation.chars}`, `耗時 ${seconds} 秒`];
  if (observation.loop) parts.push("循環");
  if (observation.truncated) parts.push("截斷");
  return `觀測：${parts.join("；")}`;
}

export function diagnoseGenerationFailure(input: {
  failed?: boolean;
  empty?: boolean;
  loop?: boolean;
  truncated?: boolean;
  providerCode?: string;
}): string {
  if (input.providerCode === "AI_PROVIDER_NOT_CONFIGURED" || input.providerCode === "AI_PROVIDER_KILL_SWITCH") {
    return "供應商未設定或暫時無法使用";
  }
  if (input.providerCode === "AI_PROVIDER_TIMEOUT") return "供應商逾時";
  if (input.providerCode === "AI_PROVIDER_MULTI_SHORT") return "Multi 路由未滿 3 條";
  if (input.providerCode === "AI_PROVIDER_HTTP_ERROR" || input.providerCode === "AI_PROVIDER_UNREACHABLE") {
    return "供應商無法連線";
  }
  if (input.providerCode === "AI_PROVIDER_EMPTY_RESPONSE") return "空回應";
  if (input.providerCode === "AI_PROVIDER_UNUSABLE_OUTPUT") return "輸出無法使用";
  if (input.empty) return "空回應";
  if (input.loop) return "偵測到重複循環";
  if (input.truncated) return "輸出被截斷";
  if (input.failed) return "生成失敗";
  return "";
}

export function withTaskObservation(
  contract: ConversationTaskContract | null,
  observation: ConversationTaskObservation,
): ConversationTaskContract | null {
  if (!contract) return null;
  return { ...contract, observation };
}

export function conversationFileUid(accountUid: string, pageUid: string, taskId: string): string {
  return `FILE-${hashId([accountUid, pageUid, taskId])}`;
}

export function fileNameForContract(contract: ConversationTaskContract): string {
  const qty = contract.quantity ? `${contract.quantity.count}${contract.quantity.unit}` : "";
  const label = clean(contract.format || contract.goal).replace(/\s+/gu, "").slice(0, 24);
  const base = `${qty}${label || "成品"}`.replace(/[\\/:*?"<>|#]/gu, "_");
  return `${base.slice(0, 80)}.txt`;
}

export function stripDeliveryFooter(text: string): string {
  let body = text.trim();
  const claim = "\n\n聲明：";
  const claimIndex = body.lastIndexOf(claim);
  if (claimIndex >= 0) body = body.slice(0, claimIndex).trim();
  const marker = "\n\n狀態：";
  const index = body.lastIndexOf(marker);
  if (index >= 0) return body.slice(0, index).trim();
  return body;
}

export function parseConversationFileRef(text: string): { fileId: string; fileName: string } | null {
  const id = /檔案：\s*(FILE-[0-9a-f]+)/u.exec(text);
  if (!id) return null;
  const name = /成品：\s*([^\n]+)/u.exec(text);
  return { fileId: id[1], fileName: clean(name?.[1]) || "成品.txt" };
}

export function generationStatusKey(
  status: ConversationTaskStatus,
):
  | "conversation.stream.status.complete"
  | "conversation.stream.status.open"
  | "conversation.stream.status.partial"
  | "conversation.stream.status.stopped"
  | "conversation.stream.status.failed" {
  if (status === "COMPLETE") return "conversation.stream.status.complete";
  if (status === "OPEN") return "conversation.stream.status.open";
  if (status === "PARTIAL") return "conversation.stream.status.partial";
  if (status === "STOPPED") return "conversation.stream.status.stopped";
  return "conversation.stream.status.failed";
}

export function generationStatusLabel(status: ConversationTaskStatus): string {
  if (status === "COMPLETE") return "已完成";
  if (status === "OPEN") return "進行中";
  if (status === "PARTIAL") return "部分完成";
  if (status === "STOPPED") return "已停止";
  return "失敗";
}

function statusLabel(status: ConversationTaskStatus): string {
  return generationStatusLabel(status);
}

export function shouldAttachFooter(contract: ConversationTaskContract): boolean {
  return (
    contract.batched ||
    contract.status === "PARTIAL" ||
    contract.status === "FAILED" ||
    contract.status === "STOPPED" ||
    contract.needsFile
  );
}

export function splitDeliverableChunks(text: string, limit: number): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (trimmed.length <= limit) return [trimmed];
  const chunks: string[] = [];
  let rest = trimmed;
  while (rest.length > limit) {
    let cut = rest.lastIndexOf("\n", limit);
    if (cut < Math.floor(limit * 0.5)) cut = limit;
    chunks.push(rest.slice(0, cut).trim());
    rest = rest.slice(cut).trim();
  }
  if (rest) chunks.push(rest);
  return chunks;
}

export function detectUnusableOutput(text: string): boolean {
  const body = clean(text);
  if (!body) return true;
  const batchHits = body.match(/第\s*1\s*[–-]\s*20\s*[篇章集項則]/gu) ?? [];
  if (batchHits.length >= 6) return true;
  const han = body.match(/\p{Script=Han}/gu) ?? [];
  if (han.length >= 80) {
    const stops = (body.match(/[。！？]/gu) ?? []).length;
    const common = (body.match(/[的了是在有不我你他這那會為與及或但]/gu) ?? []).length;
    if (stops === 0 && common < 4) return true;
  }
  return false;
}

export function batchLooksDelivered(text: string, contract: ConversationTaskContract): boolean {
  if (!contract.batched || !contract.nextBatch) return Boolean(clean(text));
  const match = /第\s*(\d+)\s*[–-]\s*(\d+)\s*(集|章|篇|回)/u.exec(contract.nextBatch);
  if (!match) return Boolean(clean(text));
  const start = Number.parseInt(match[1], 10);
  const unit = match[3];
  const units = unit === "集" ? ["集", "章"] : [unit];
  let hits = 0;
  for (const label of units) {
    for (let index = start; index < start + 3; index += 1) {
      if (new RegExp(`第\\s*${index}\\s*${label}(?![–\\d])`, "u").test(text)) hits += 1;
    }
  }
  return hits >= 2;
}

export function detectGenerationLoop(text: string): GenerationMonitor {
  const body = clean(text);
  if (!body) return { loop: false, reason: "", validPrefix: body };
  const paragraphs = body.split(/\n{2,}/u).map((row) => row.trim()).filter(Boolean);
  if (paragraphs.length >= 4) {
    const last = paragraphs.slice(-4);
    if (last.every((row) => row === last[0])) {
      return { loop: true, reason: "repeated_paragraph", validPrefix: paragraphs.slice(0, -3).join("\n\n") };
    }
  }
  const sentences = body.split(/(?<=[。！？\n])/u).map((row) => row.trim()).filter((row) => row.length >= 3);
  if (sentences.length >= 6) {
    const window = sentences.slice(-8);
    const uniqueCount = new Set(window).size;
    if (uniqueCount <= 2) {
      const firstRepeat = sentences.findIndex((row, index) => index > 0 && row === sentences[index - 1]);
      const prefix = (firstRepeat > 0 ? sentences.slice(0, firstRepeat) : sentences.slice(0, 2)).join("");
      return { loop: true, reason: "repeated_sentence", validPrefix: prefix };
    }
  }
  const n = 16;
  if (body.length >= n * 8) {
    const counts = new Map<string, number>();
    let max = 0;
    let token = "";
    for (let index = 0; index <= body.length - n; index += 1) {
      const gram = body.slice(index, index + n);
      const next = (counts.get(gram) ?? 0) + 1;
      counts.set(gram, next);
      if (next > max) {
        max = next;
        token = gram;
      }
    }
    if (max >= 8) {
      const cut = body.indexOf(token);
      return { loop: true, reason: "repeated_ngram", validPrefix: body.slice(0, Math.max(cut, 0)) };
    }
  }
  return { loop: false, reason: "", validPrefix: body };
}

export function shouldCheckStreamLoop(length: number, lastChecked = 0): boolean {
  if (length < STREAM_LOOP_CHECK_MIN_CHARS) return false;
  return length - lastChecked >= STREAM_LOOP_CHECK_EVERY_CHARS;
}

export function splitSseFrames(buffer: string): { frames: string[]; rest: string } {
  const parts = buffer.split(/\r?\n\r?\n/u);
  const rest = parts.pop() ?? "";
  const frames: string[] = [];
  for (const part of parts) {
    for (const line of part.split(/\r?\n/u)) {
      const match = /^data:\s?(.*)$/u.exec(line);
      if (match) frames.push(match[1]);
    }
  }
  return { frames, rest };
}

export type GenerationStreamEvent =
  | { type: "token"; text: string; alias?: string }
  | { type: "status"; status: ConversationTaskStatus }
  | { type: "done" };

export function encodeGenerationSse(event: GenerationStreamEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

export function parseGenerationSseFrame(data: string): GenerationStreamEvent | null {
  const trimmed = clean(data);
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed) as { type?: unknown; text?: unknown; status?: unknown; alias?: unknown };
    if (parsed.type === "token" && typeof parsed.text === "string") {
      const alias = typeof parsed.alias === "string" ? parsed.alias.trim() : "";
      return alias ? { type: "token", text: parsed.text, alias } : { type: "token", text: parsed.text };
    }
    if (
      parsed.type === "status" &&
      (parsed.status === "OPEN" ||
        parsed.status === "PARTIAL" ||
        parsed.status === "COMPLETE" ||
        parsed.status === "FAILED" ||
        parsed.status === "STOPPED")
    ) {
      return { type: "status", status: parsed.status };
    }
    if (parsed.type === "done") return { type: "done" };
    return null;
  } catch {
    return null;
  }
}

export function isConversationGeneratingAction(actionUid: string): boolean {
  return actionUid.endsWith("-ACT-SEND") || actionUid.endsWith("-ACT-MSG-ANALYZE");
}

export function generationSseResponse(run: (sink: GenerationStreamSink) => Promise<void>): Response {
  const encoder = new TextEncoder();
  let closed = false;
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const push = (event: GenerationStreamEvent) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(encodeGenerationSse(event)));
        } catch {
          closed = true;
        }
      };
      const sink: GenerationStreamSink = {
        token: (text, alias) => push(alias ? { type: "token", text, alias } : { type: "token", text }),
        status: (status) => push({ type: "status", status }),
      };
      try {
        await run(sink);
      } catch {
        push({ type: "status", status: "FAILED" });
      } finally {
        push({ type: "done" });
        closed = true;
        try {
          controller.close();
        } catch {
          // Stream already closed after abort or natural end.
        }
      }
    },
  });
  return new Response(stream, {
    status: 202,
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-store",
      connection: "keep-alive",
    },
  });
}

export async function consumeGenerationStream(
  body: ReadableStream<Uint8Array>,
  sink: GenerationStreamSink,
  signal?: AbortSignal,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminal = false;
  const onAbort = () => {
    void reader.cancel();
  };
  if (signal?.aborted) {
    await reader.cancel();
    return;
  }
  signal?.addEventListener("abort", onAbort);
  const apply = (event: GenerationStreamEvent | null): boolean => {
    if (!event) return false;
    if (event.type === "token" && event.text) sink.token(event.text, event.alias);
    if (event.type === "status") {
      sink.status(event.status);
      if (event.status !== "OPEN") terminal = true;
    }
    if (event.type === "done") {
      terminal = true;
      return true;
    }
    return false;
  };
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const split = splitSseFrames(buffer);
      buffer = split.rest;
      for (const frame of split.frames) {
        if (apply(parseGenerationSseFrame(frame))) return;
      }
    }
    const leftover = splitSseFrames(buffer);
    for (const frame of leftover.frames) apply(parseGenerationSseFrame(frame));
  } catch {
    // Stream aborted or closed before a terminal frame.
  } finally {
    signal?.removeEventListener("abort", onAbort);
    try {
      await reader.cancel();
    } catch {
      // Stream already closed after abort or natural end.
    }
  }
  if (!terminal && !signal?.aborted) sink.status("FAILED");
}

export function parseOpenAiSseFrame(data: string): { delta: string; finishReason: string; done: boolean } {
  const trimmed = clean(data);
  if (trimmed === "[DONE]") return { delta: "", finishReason: "", done: true };
  if (!trimmed) return { delta: "", finishReason: "", done: false };
  try {
    const payload = JSON.parse(trimmed) as {
      choices?: Array<{
        delta?: { content?: string };
        message?: { content?: string };
        finish_reason?: string;
        finishReason?: string;
      }>;
    };
    const choice = payload.choices?.[0];
    const raw = choice?.delta?.content ?? choice?.message?.content;
    return {
      delta: typeof raw === "string" ? raw : "",
      finishReason: clean(choice?.finish_reason ?? choice?.finishReason),
      done: false,
    };
  } catch {
    return { delta: "", finishReason: "", done: false };
  }
}

export type UnverifiedClaimKind = "deploy" | "side_effect" | "github" | "file";

export function unverifiedExecutionClaims(
  text: string,
  verified: { fileWritten?: boolean } = {},
): UnverifiedClaimKind[] {
  const body = clean(text);
  const found: UnverifiedClaimKind[] = [];
  if (/已(經)?(成功)?部署(到|至|上線)?/u.test(body)) found.push("deploy");
  if (/已(經)?(成功)?(刪除|付款|轉帳)/u.test(body)) found.push("side_effect");
  if (/已(經)?(成功)?(推送|合併).{0,16}(GitHub|分支|main)/u.test(body)) found.push("github");
  if (!verified.fileWritten && /已(經)?(成功)?(建立|寫入|產生)(檔案|文件)/u.test(body)) found.push("file");
  return found;
}

export function annotateUnverifiedClaims(text: string, claims: UnverifiedClaimKind[]): string {
  const body = text.trim();
  if (!body || !claims.length) return body;
  return `${body}\n\n聲明：以上執行結果尚未驗證，僅視為建議或計畫。`;
}

export function inferTruncated(content: string, finishReason: string): boolean {
  const reason = clean(finishReason).toLowerCase();
  if (reason === "length" || reason === "max_tokens" || reason === "loop_stopped" || reason === "cancelled") return true;
  const body = clean(content);
  if (!body) return false;
  if (/[：:、,，]\s*$/u.test(body)) return true;
  if (/第\s*\d+\s*集\s*$/u.test(body)) return true;
  if (/(未完|待續|接下)/u.test(body.slice(-20))) return true;
  if (reason === "stop" || reason === "end" || reason === "stop_sequence") return false;
  return false;
}

export function mergeContinuation(previous: string, next: string): string {
  const left = previous.trimEnd();
  const right = next.trim();
  if (!left) return right;
  if (!right) return left;
  const probe = Math.min(left.length, 200);
  for (let size = probe; size >= 3; size -= 1) {
    const tail = left.slice(-size);
    if (right.startsWith(tail)) return `${left}${right.slice(size)}`;
  }
  const gap = left.endsWith("\n") || right.startsWith("\n") ? "" : "\n";
  return `${left}${gap}${right}`;
}

export function claimsFullCompletion(text: string, contract: ConversationTaskContract): boolean {
  if (!contract.batched || !contract.quantity) return false;
  return /全部完成|已完成全部|已全部完成/.test(text) || new RegExp(`${contract.quantity.count}\\s*${contract.quantity.unit}.*全部`).test(text);
}

export function updateContractAfterGeneration(
  contract: ConversationTaskContract,
  output: string,
  flags: { truncated: boolean; loop: boolean; failed?: boolean; stopped?: boolean; unusable?: boolean },
): ConversationTaskContract {
  const unusable = Boolean(flags.unusable) || detectUnusableOutput(output);
  if (flags.stopped) {
    return {
      ...contract,
      status: "STOPPED",
      resumeCursor: clean(output).slice(-80) || contract.resumeCursor,
    };
  }
  if (flags.failed || unusable) {
    return { ...contract, status: "FAILED" };
  }
  if (flags.loop) {
    return {
      ...contract,
      status: "PARTIAL",
      resumeCursor: clean(output).slice(-80) || contract.resumeCursor,
    };
  }
  if (contract.kind === "question" && !contract.batched) {
    return { ...contract, status: flags.truncated ? "PARTIAL" : "COMPLETE", pendingItems: [], nextBatch: undefined };
  }
  if (!contract.batched) {
    return {
      ...contract,
      status: flags.truncated ? "PARTIAL" : "COMPLETE",
      resumeCursor: flags.truncated ? output.slice(-80) : undefined,
    };
  }
  if (!batchLooksDelivered(output, contract)) {
    return {
      ...contract,
      status: "PARTIAL",
      resumeCursor: clean(output).slice(-80) || contract.resumeCursor,
    };
  }
  const through = Math.min(completedCount(contract) + contract.batchSize, contract.quantity?.count ?? 0);
  const planned = planQuantityBatches(contract.quantity, contract.batchSize, through);
  const falseComplete = claimsFullCompletion(output, contract) && (planned.pendingItems.length > 0 || flags.truncated);
  const status: ConversationTaskStatus = planned.pendingItems.length || flags.truncated || falseComplete
    ? "PARTIAL"
    : "COMPLETE";
  return {
    ...contract,
    status,
    completedItems: planned.completedItems.length ? planned.completedItems : contract.completedItems,
    pendingItems: status === "COMPLETE" ? [] : planned.pendingItems,
    nextBatch: status === "COMPLETE" ? undefined : planned.nextBatch,
    resumeCursor: flags.truncated ? output.slice(-80) : undefined,
  };
}

export function temperatureFor(kind: ConversationTaskKind, fallback = 0.2): number {
  if (kind === "creation" || kind === "large" || kind === "writing") return 0.7;
  return fallback;
}

export function continuationUserMessage(contract: ConversationTaskContract): string {
  const range = contract.nextBatch ? `本批次範圍：${contract.nextBatch}。` : "從上次結尾繼續。";
  return `從上次結尾繼續寫，不要重複已寫內容。${range}未完成不得宣稱全部完成。`;
}

export function loopRepairUserMessage(): string {
  return "上次輸出出現重複循環。請從有效結尾繼續，禁止重複句子或段落。";
}

export function parseNotebookTasks(raw: string | null | undefined): ConversationTaskContract[] {
  const text = clean(raw);
  if (!text) return [];
  try {
    const parsed = JSON.parse(text) as { kind?: unknown; tasks?: unknown };
    if (parsed.kind !== "NOTEBOOK" || !Array.isArray(parsed.tasks)) return [];
    const tasks: ConversationTaskContract[] = [];
    for (const item of parsed.tasks) {
      if (!item || typeof item !== "object") continue;
      const rec = item as Partial<ConversationTaskContract>;
      if (typeof rec.taskId !== "string" || typeof rec.rawDemand !== "string") continue;
      if (typeof rec.kind !== "string" || typeof rec.status !== "string") continue;
      tasks.push(rec as ConversationTaskContract);
    }
    return tasks;
  } catch {
    return [];
  }
}

export function withNotebookTasks(raw: string | null | undefined, tasks: ConversationTaskContract[]): Record<string, unknown> {
  let records: unknown[] = [];
  try {
    const parsed = JSON.parse(clean(raw) || "null") as { kind?: unknown; records?: unknown };
    if (parsed && parsed.kind === "NOTEBOOK" && Array.isArray(parsed.records)) records = parsed.records;
  } catch {
    records = [];
  }
  return { kind: "NOTEBOOK", records, tasks };
}
