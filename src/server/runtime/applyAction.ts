import {
  ASSET_CORRECTION_RESPONSE_UID,
  EDIT_CORRECTION_CANDIDATE_UID,
  VIDEO_CORRECTION_RESPONSE_UID,
  unavailableBody,
  unavailableFromReason,
} from "@/lib/aiReply";
import { previewAiapiAction } from "@/lib/aiapiActionPreview";
import { applyDiscoveryCollection, previewDevAction } from "@/lib/devActionPreview";
import { previewSocAction } from "@/lib/socActionPreview";
import { kbAcquisitionPatchFromCollect, previewKbAction } from "@/lib/kbActionPreview";
import { collectDiscoverySignals } from "../acquisition/collect";
import { parseJson, type DevProfile } from "@/lib/devState";
import { previewAssetAction } from "@/lib/assetActionPreview";
import { resolveAssetInbound } from "@/lib/assetInbound";
import { parseCorrectionScript, serializeCorrectionScript, withCorrectionBody } from "@/lib/correctionScript";
import { parseAssetPatch, patchPrompt, serializeAssetPatch, withPatchPreview } from "@/lib/layerDocument";
import { buildEnrichedProjection } from "@/lib/canonicalViews";
import { buildBaseDna, buildDnaEnrichment, dnaRequiredMissing, parseBaseDna, serializeBaseDna, withDnaStatus } from "@/lib/dnaDocument";
import {
  buildChapterArchitecture,
  buildStoryCore,
  chapterArchRequiredMissing,
  parseChapterArchitecture,
  parseStoryCore,
  serializeChapterArchitecture,
  serializeStoryCore,
  storyCoreRequiredMissing,
  withChapterArchStatus,
  withStoryCoreStatus,
} from "@/lib/storyChapterDocument";
import {
  ASSET_CONVERSATION,
  CORE_CONVERSATION,
  EDIT_CONVERSATION,
  VIDEO_CONVERSATION,
  type ConversationBindings,
  activeThreadUidFor,
  appendAssistantMessageFor,
  formatConversationContext,
  messagesForThread as conversationMessagesForThread,
  parseMessageActionPayload as parseConversationMessageActionPayload,
  parseThreadRecords,
  persistConversationTasksFor,
  generationHistoryPayload as conversationGenerationHistory,
  refreshAssistantNotebookFor,
  resolveComposerTokensFor,
} from "@/lib/conversationCore";
import {
  attachFileToContract,
  buildConversationFile,
  conversationFilePage,
  conversationFileVerified,
  removeEpisodeBlocks,
} from "@/lib/conversationFile";
import {
  persistDeleteConversationFilesByThread,
  persistFindConversationFile,
  persistFindConversationFileByTask,
  persistUpsertConversationFile,
} from "../db/conversationFileStore";
import {
  annotateUnverifiedClaims,
  advanceFrontierContract,
  batchUnitPattern,
  buildTaskContract,
  collectEpisodeLabels,
  detectUnusableOutput,
  diagnoseGenerationFailure,
  finalizeEpisodes,
  formatDeliveryFooter,
  hashId,
  isContinueRequest,
  isCorrectionRequest,
  latestOpenTask,
  parseLabelRange,
  parseNotebookTasks,
  parseQuantity,
  rejectEpisodes,
  shouldAttachFooter,
  unverifiedExecutionClaims,
  updateContractAfterGeneration,
  withNotebookTasks,
  withTaskObservation,
  type ConversationTaskContract,
  type GenerationStreamSink,
} from "@/lib/conversationTask";
import {
  activeThreadUid,
  appendAssistantMessage,
  appendAssistantMessages,
  formatCoreChatContext,
  buildCanonicalScript,
  parseCanonicalScript,
  serializeCanonicalScript,
  isMultiAiMode,
  messagesForThread,
  parseMessageActionPayload,
  persistConversationTasks,
  previewCoreAction,
  exactName,
  generationHistoryPayload,
  refreshAssistantNotebook,
  resolveComposerTokens,
  targetedParticipantAliases,
} from "@/lib/coreActionPreview";
import { previewEditAction } from "@/lib/editActionPreview";
import { resolveEditInbound, effectiveVideoCurrent } from "@/lib/editInbound";
import { previewQaAction } from "@/lib/qaActionPreview";
import { resolveQaInbound } from "@/lib/qaInbound";
import { resolveVideoInbound } from "@/lib/videoInbound";
import { previewVideoAction } from "@/lib/videoActionPreview";
import { AiProviderError, assignedAiRouteSnapshot, generateIndependentPageReplies, generatePageReply, GenerationCancelled, type AiPageUid } from "../ai/llmClient";
import { clearAiapiCredential, setAiapiCredential } from "../db/aiapiCredential";
import { getSqlClient } from "../db/client";
import {
  runConnectionTest,
  runCreateProviderProfile,
  runQueueProbe,
  runRouteExecution,
  runSandboxTest,
  type AiapiOutcome,
} from "../aiapi/runtime";

export type WorkbenchPage =
  | "dashboard"
  | "core"
  | "asset"
  | "video"
  | "edit"
  | "qa"
  | "db"
  | "str"
  | "info"
  | "sys"
  | "iam"
  | "dev"
  | "soc"
  | "erp"
  | "aiapi"
  | "sg02"
  | "adminStr"
  | "kb";

const FIELD_TABLE: Record<Exclude<WorkbenchPage, "dashboard">, string> = {
  core: "ghsn_core_field_projection",
  asset: "ghsn_asset_field_projection",
  video: "ghsn_video_field_projection",
  edit: "ghsn_edit_field_projection",
  qa: "ghsn_qa_field_projection",
  db: "ghsn_db_field_projection",
  str: "ghsn_str_field_projection",
  info: "ghsn_info_field_projection",
  sys: "ghsn_sys_field_projection",
  iam: "ghsn_iam_field_projection",
  dev: "ghsn_dev_field_projection",
  soc: "ghsn_soc_field_projection",
  erp: "ghsn_erp_field_projection",
  aiapi: "ghsn_aiapi_field_projection",
  sg02: "ghsn_sg02_field_projection",
  adminStr: "ghsn_admin_str_field_projection",
  kb: "ghsn_kb_field_projection",
};

function statusFromAction(actionUid: string): string {
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

async function readField(table: string, controlUid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    `SELECT value_text FROM ${table} WHERE control_uid = ?`,
    [controlUid],
  );
  const value = rows[0]?.value_text;
  return value === "" ? null : (value ?? null);
}

function compact(seed: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(seed).filter(([, value]) => Boolean(value)));
}

async function writeField(table: string, controlUid: string, value: string): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ${table} (control_uid, value_text)
     VALUES (?, ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [controlUid, value],
  );
}



function promptFromValue(raw?: string): string {
  const text = (raw ?? "").trim();
  if (!text) return "";
  if (text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      const candidate = parsed.message ?? parsed.instruction ?? parsed.reference ?? parsed.prompt;
      if (typeof candidate === "string") return candidate.trim();
    } catch {
      return text;
    }
  }
  return text;
}

function resolveTaskContract(
  prompt: string,
  notebookRaw: string | null,
  messages: Array<{ role?: string; text?: unknown }>,
  thread: string,
): ConversationTaskContract | null {
  const tasks = parseNotebookTasks(notebookRaw);
  const prior = latestOpenTask(tasks, thread);
  if (prompt && isCorrectionRequest(prompt) && !isContinueRequest(prompt)) {
    const scoped = tasks.filter((row) => row.thread === thread);
    const target = prior ?? (scoped.length ? scoped[scoped.length - 1] : null);
    if (target) return buildTaskContract(prompt, target, thread);
  }
  const contract = prompt ? buildTaskContract(prompt, prior, thread) : prior;
  if (contract?.quantity?.count) return contract;
  return rebuildTaskContractFromThread(prompt, messages, thread, notebookRaw) ?? contract;
}

function rebuildTaskContractFromThread(
  prompt: string,
  messages: Array<{ role?: string; text?: unknown }>,
  thread: string,
  notebookRaw: string | null,
): ConversationTaskContract | null {
  if (!prompt || !isContinueRequest(prompt)) return null;
  const demand = [...messages]
    .reverse()
    .find((row) => row.role === "user" && parseQuantity(String(row.text ?? "")));
  if (!demand) return null;
  const demandText = String(demand.text ?? "");
  const existing = parseNotebookTasks(notebookRaw).find(
    (row) => row.rawDemand === demandText || row.taskId === `TASK-${hashId([thread, demandText])}`,
  );
  const base = buildTaskContract(demandText, existing ?? null, thread);
  if (!base.quantity?.count) return null;
  if (existing?.quantity?.count === base.quantity.count) return base;
  const labels = new Set<number>(existing?.deliveredLabels ?? []);
  for (const row of messages) {
    if (row.role !== "assistant") continue;
    for (const value of collectEpisodeLabels(String(row.text ?? ""), "[集章]")) {
      if (value <= base.quantity.count) labels.add(value);
    }
  }
  if (!labels.size) return null;
  return advanceFrontierContract({ ...base, deliveredLabels: [...labels] }, "");
}

function applyGeneratedContract(
  contract: ConversationTaskContract | null,
  generated: { text: string; truncated?: boolean; loop?: boolean } | null,
  failed: boolean,
  stopped = false,
  startedAt = 0,
  providerCode = "",
): { reply: string; nextContract: ConversationTaskContract | null } {
  const text = generated?.text.trim() ?? "";
  const truncated = generated?.truncated ?? false;
  const loop = generated?.loop ?? false;
  const unusable = Boolean(text) && detectUnusableOutput(text);
  const empty = !text;
  const failReason = diagnoseGenerationFailure({
    failed: failed || unusable || (!stopped && empty),
    empty,
    loop,
    truncated,
    providerCode: unusable && !providerCode ? "AI_PROVIDER_UNUSABLE_OUTPUT" : providerCode,
  });
  const observation = {
    chars: text.length,
    durationMs: startedAt ? Date.now() - startedAt : 0,
    loop,
    truncated: truncated || stopped,
    failReason,
  };
  if (stopped) {
    const nextContract = withTaskObservation(
      contract ? updateContractAfterGeneration(contract, text, { truncated: true, loop: false, stopped: true }) : null,
      observation,
    );
    return { reply: text, nextContract };
  }
  let reply = text;
  let nextContract = contract;
  if (failed || unusable) {
    reply = unavailableBody({
      failed: true,
      empty,
      loop,
      truncated,
      providerCode: unusable && !providerCode ? "AI_PROVIDER_UNUSABLE_OUTPUT" : providerCode,
    });
    if (contract) {
      nextContract = updateContractAfterGeneration(contract, generated?.text ?? text, {
        truncated,
        loop,
        failed: true,
        unusable,
      });
    }
  } else if (!text) {
    reply = unavailableBody({ failed: true, empty: true, providerCode });
  } else if (contract && text) {
    nextContract = updateContractAfterGeneration(contract, generated?.text ?? text, {
      truncated,
      loop,
    });
  }
  return { reply, nextContract: withTaskObservation(nextContract ?? null, observation) };
}

function upsertTask(tasks: ConversationTaskContract[], next: ConversationTaskContract): ConversationTaskContract[] {
  const rest = tasks.filter((row) => row.taskId !== next.taskId);
  return [...rest, next];
}

function attachFooter(text: string, contract: ConversationTaskContract | null): string {
  const body = text.trim();
  const fallback =
    body || (contract?.status === "STOPPED" ? "" : unavailableFromReason(contract?.observation?.failReason ?? ""));
  const annotated = annotateUnverifiedClaims(
    fallback,
    unverifiedExecutionClaims(text, { fileWritten: Boolean(contract?.fileId) }),
  );
  if (!contract || !shouldAttachFooter(contract)) return annotated;
  const footer = formatDeliveryFooter(contract);
  if (footer && !annotated.includes(footer)) return annotated ? `${annotated}\n\n${footer}` : footer;
  return annotated;
}

async function applyConversationReviewAction(
  actionUid: string,
  nextValue: string | undefined,
  accountUid?: string,
): Promise<boolean> {
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    `SELECT control_uid, value_text FROM ${FIELD_TABLE.core}`,
  );
  const cache = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
  const current = (uid: string) => cache.get(uid) ?? null;
  const thread = activeThreadUid(current);
  const notebookUid = "CORE-01-FLD-ASSISTANT-SUMMARY";
  const tasks = parseNotebookTasks(current(notebookUid));
  const scoped = tasks.filter((row) => row.thread === thread);
  const contract = latestOpenTask(tasks, thread) ?? (scoped.length ? scoped[scoped.length - 1] : null);
  if (!contract) return false;
  const next =
    actionUid === "CORE-01-ACT-FINALIZE"
      ? finalizeEpisodes(contract, nextValue)
      : rejectEpisodes(contract, nextValue);
  if (next === contract) return false;
  if (actionUid === "CORE-01-ACT-REVIEW-REJECT" && accountUid) {
    const pageUid = conversationFilePage("core");
    const prior = pageUid ? await persistFindConversationFileByTask(accountUid, pageUid, contract.taskId) : null;
    if (prior?.body) {
      const range = parseLabelRange(nextValue ?? "") ?? parseLabelRange(contract.nextBatch ?? "");
      if (range) {
        const body = removeEpisodeBlocks(prior.body, range[0], range[1], batchUnitPattern(contract.quantity?.unit ?? "集"));
        if (body !== prior.body) await persistUpsertConversationFile({ ...prior, body, version: prior.version + 1, updatedAt: new Date().toISOString() });
      }
    }
  }
  const updated = tasks.map((row) => (row.taskId === contract.taskId ? next : row));
  await writeField(FIELD_TABLE.core, notebookUid, JSON.stringify(withNotebookTasks(current(notebookUid), updated)));
  if (actionUid === "CORE-01-ACT-REVIEW-REJECT") {
    await writeField(FIELD_TABLE.core, "CORE-01-FLD-LOCK-REVIEW", "rejected");
    await writeField(FIELD_TABLE.core, "CORE-01-FLD-LIFECYCLE-STAGE", "REVISION_REQUIRED");
  }
  return true;
}

async function enrichCanonicalScriptProjection(accountUid: string, actionUid: string): Promise<void> {
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    `SELECT control_uid, value_text FROM ${FIELD_TABLE.core}`,
  );
  const cache = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
  const current = (uid: string) => cache.get(uid) ?? null;
  const existing = parseCanonicalScript(current("CORE-01-BTN-CANONICAL-SCRIPT"));
  const base = existing ?? buildCanonicalScript(current);
  if (!base) return;
  let fileBody = "";
  try {
    const notebookUid = "CORE-01-FLD-ASSISTANT-SUMMARY";
    const thread = activeThreadUid(current);
    const tasks = parseNotebookTasks(current(notebookUid));
    const scoped = tasks.filter((row) => row.thread === thread);
    const contract = latestOpenTask(tasks, thread) ?? (scoped.length ? scoped[scoped.length - 1] : null);
    if (contract) {
      const pageUid = conversationFilePage("core");
      const file = pageUid ? await persistFindConversationFileByTask(accountUid, pageUid, contract.taskId) : null;
      fileBody = file?.body ?? "";
    }
  } catch {}
  const isAccept = actionUid === "CORE-01-ACT-CANDIDATE-ACCEPT";
  const priorVersionRef =
    isAccept && existing && existing.version !== base.version ? existing.version : (existing?.prior_version_ref ?? "");
  const changeSummary = isAccept
    ? `候選定稿 ${current("CORE-01-FLD-VERSION-STATE") ?? ""}`
    : (existing?.change_summary ?? "");
  const enriched = buildEnrichedProjection(base, { fileBody: fileBody || undefined, priorVersionRef, changeSummary });
  const dnaDoc = parseBaseDna(current("CORE-01-BTN-DNA-LOCK"));
  const withDna = dnaDoc ? { ...enriched, dna_enrichment: buildDnaEnrichment(dnaDoc, { topic: base.topic_id }) } : enriched;
  await writeField(FIELD_TABLE.core, "CORE-01-BTN-CANONICAL-SCRIPT", serializeCanonicalScript(withDna));
  if (actionUid === "CORE-01-ACT-CANONICAL-SCRIPT-VIEW") {
    await writeField(FIELD_TABLE.core, "CORE-01-FLD-RUNTIME-STAGE", "SCRIPT_VIEW");
  }
}

type CoreFieldReader = (uid: string) => string | null;

async function loadCoreFields(): Promise<CoreFieldReader> {
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    `SELECT control_uid, value_text FROM ${FIELD_TABLE.core}`,
  );
  const cache = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
  return (uid: string) => cache.get(uid) ?? null;
}

function parseThreadWorkItems(raw: string | null): Map<string, string> {
  const out = new Map<string, string>();
  try {
    const parsed = JSON.parse(raw ?? "") as unknown;
    if (Array.isArray(parsed)) {
      for (const row of parsed) {
        if (!row || typeof row !== "object") continue;
        const rec = row as Record<string, unknown>;
        if (typeof rec.title === "string" && typeof rec.workItem === "string") out.set(rec.title, rec.workItem);
      }
    }
  } catch {}
  return out;
}

async function collectDnaThreadFiles(accountUid: string, current: CoreFieldReader, workItems: string[] = ["DNA", "WORLD_SETTING"]): Promise<{ fileBodies: string[]; sourceFiles: string[] }> {
  const fileBodies: string[] = [];
  const sourceFiles: string[] = [];
  const threadItems = parseThreadWorkItems(current("CORE-01-BTN-NEW-THREAD"));
  const wanted = new Set(workItems);
  const dnaThreads = new Set([...threadItems.entries()].filter(([, workItem]) => wanted.has(workItem)).map(([thread]) => thread));
  if (!dnaThreads.size) return { fileBodies, sourceFiles };
  const tasks = parseNotebookTasks(current("CORE-01-FLD-ASSISTANT-SUMMARY"));
  const pageUid = conversationFilePage("core");
  for (const task of tasks) {
    if (!dnaThreads.has(task.thread)) continue;
    const file = pageUid ? await persistFindConversationFileByTask(accountUid, pageUid, task.taskId) : null;
    if (file?.body) {
      fileBodies.push(file.body);
      sourceFiles.push(file.fileUid);
    }
  }
  return { fileBodies, sourceFiles };
}

async function enrichDnaDocument(accountUid: string): Promise<void> {
  const current = await loadCoreFields();
  const raw = current("CORE-01-BTN-DNA-LOCK") ?? "";
  if (parseBaseDna(raw)) return;
  const project = (current("CORE-01-CTL-PROJECT") ?? "").trim().slice(0, 80);
  if (!project) return;
  const { fileBodies, sourceFiles } = await collectDnaThreadFiles(accountUid, current);
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");
  const doc = buildBaseDna({
    project,
    fileBodies,
    sourceFiles,
    changeSummary: "DNA 候選建立（制式清單掃描定稿文件）",
    status: "CANDIDATE",
    createdAt: now,
  });
  await writeField(FIELD_TABLE.core, "CORE-01-BTN-DNA-LOCK", serializeBaseDna(doc));
}

async function enrichStoryCoreDocument(accountUid: string): Promise<void> {
  const current = await loadCoreFields();
  const raw = current("CORE-01-BTN-STORY-CORE") ?? "";
  if (parseStoryCore(raw)) return;
  const project = (current("CORE-01-CTL-PROJECT") ?? "").trim().slice(0, 80);
  if (!project) return;
  const { fileBodies, sourceFiles } = await collectDnaThreadFiles(accountUid, current, ["STORY"]);
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");
  const doc = buildStoryCore({
    project,
    fileBodies,
    sourceFiles,
    changeSummary: "故事核心候選建立（§9 制式掃描 STORY 線程定稿文件）",
    status: "CANDIDATE",
    createdAt: now,
  });
  await writeField(FIELD_TABLE.core, "CORE-01-BTN-STORY-CORE", serializeStoryCore(doc));
}

async function enrichChapterArchDocument(accountUid: string): Promise<void> {
  const current = await loadCoreFields();
  const raw = current("CORE-01-BTN-CHAPTER-ARCH") ?? "";
  if (parseChapterArchitecture(raw)) return;
  const project = (current("CORE-01-CTL-PROJECT") ?? "").trim().slice(0, 80);
  if (!project) return;
  const { fileBodies, sourceFiles } = await collectDnaThreadFiles(accountUid, current, ["CHAPTER"]);
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");
  const doc = buildChapterArchitecture({
    project,
    fileBodies,
    sourceFiles,
    changeSummary: "章節架構候選建立（§10 制式掃描 CHAPTER 線程定稿文件）",
    status: "CANDIDATE",
    createdAt: now,
  });
  await writeField(FIELD_TABLE.core, "CORE-01-BTN-CHAPTER-ARCH", serializeChapterArchitecture(doc));
}

async function enforceCoreCoverageGate(accountUid: string, transition: "REVIEW" | "MOTHER_LOCK"): Promise<{ ok: boolean; missing: string[] }> {
  const current = await loadCoreFields();
  const project = (current("CORE-01-CTL-PROJECT") ?? "").trim().slice(0, 80);
  if (!project) return { ok: false, missing: ["NO_PROJECT"] };
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");

  const dnaRaw = current("CORE-01-BTN-DNA-LOCK") ?? "";
  let dnaDoc = parseBaseDna(dnaRaw);
  if (!dnaDoc) {
    const { fileBodies, sourceFiles } = await collectDnaThreadFiles(accountUid, current);
    dnaDoc = buildBaseDna({ project, fileBodies, sourceFiles, changeSummary: "門禁掃描", status: "CANDIDATE", createdAt: now });
  }
  const storyRaw = current("CORE-01-BTN-STORY-CORE") ?? "";
  let storyDoc = parseStoryCore(storyRaw);
  if (!storyDoc) {
    const { fileBodies, sourceFiles } = await collectDnaThreadFiles(accountUid, current, ["STORY"]);
    storyDoc = buildStoryCore({ project, fileBodies, sourceFiles, changeSummary: "門禁掃描（§9）", status: "CANDIDATE", createdAt: now });
  }
  const chapterRaw = current("CORE-01-BTN-CHAPTER-ARCH") ?? "";
  let chapterDoc = parseChapterArchitecture(chapterRaw);
  if (!chapterDoc) {
    const { fileBodies, sourceFiles } = await collectDnaThreadFiles(accountUid, current, ["CHAPTER"]);
    chapterDoc = buildChapterArchitecture({ project, fileBodies, sourceFiles, changeSummary: "門禁掃描（§10）", status: "CANDIDATE", createdAt: now });
  }
  if (!dnaDoc || !storyDoc || !chapterDoc) return { ok: false, missing: ["NO_CORE_DOCUMENT"] };

  const missing = [
    ...dnaRequiredMissing(dnaDoc),
    ...storyCoreRequiredMissing(storyDoc).map((row) => `STORY_CORE:${row}`),
    ...chapterArchRequiredMissing(chapterDoc).map((row) => `CHAPTER_ARCHITECTURE:${row}`),
  ];
  if (missing.length) {
    await writeField(
      FIELD_TABLE.core,
      "CORE-01-BTN-DNA-LOCK",
      serializeBaseDna({ ...dnaDoc, coverage_gaps: [...new Set([...dnaDoc.coverage_gaps, `mother_lock_blocked:${missing.join(";")}`])] }),
    );
    if (!parseStoryCore(storyRaw)) await writeField(FIELD_TABLE.core, "CORE-01-BTN-STORY-CORE", serializeStoryCore(storyDoc));
    if (!parseChapterArchitecture(chapterRaw)) await writeField(FIELD_TABLE.core, "CORE-01-BTN-CHAPTER-ARCH", serializeChapterArchitecture(chapterDoc));
    await writeField(FIELD_TABLE.core, "CORE-01-FLD-RUNTIME-STAGE", "DNA_BLOCKED");
    if (transition === "MOTHER_LOCK") await writeField(FIELD_TABLE.core, "CORE-01-FLD-LIFECYCLE-STAGE", "REVISION_REQUIRED");
    return { ok: false, missing };
  }
  if (!parseBaseDna(dnaRaw)) await writeField(FIELD_TABLE.core, "CORE-01-BTN-DNA-LOCK", serializeBaseDna(dnaDoc));
  if (!parseStoryCore(storyRaw)) await writeField(FIELD_TABLE.core, "CORE-01-BTN-STORY-CORE", serializeStoryCore(storyDoc));
  if (!parseChapterArchitecture(chapterRaw)) await writeField(FIELD_TABLE.core, "CORE-01-BTN-CHAPTER-ARCH", serializeChapterArchitecture(chapterDoc));
  return { ok: true, missing: [] };
}

async function persistGeneratedFile(
  accountUid: string | undefined,
  page: AiPageUid,
  contract: ConversationTaskContract | null,
  reply: string,
): Promise<ConversationTaskContract | null> {
  if (!accountUid || !contract?.needsFile || contract.status === "FAILED") return contract;
  if (contract.status === "STOPPED" && !reply.trim()) return contract;
  const pageUid = conversationFilePage(page);
  if (!pageUid) return contract;
  try {
    const prior = await persistFindConversationFileByTask(accountUid, pageUid, contract.taskId);
    const file = buildConversationFile(accountUid, pageUid, contract, reply, prior);
    if (!file) return contract;
    await persistUpsertConversationFile(file);
    const stored = await persistFindConversationFile(file.fileUid, accountUid);
    if (!conversationFileVerified(file, stored)) return contract;
    return attachFileToContract(contract, stored ?? file);
  } catch {
    return contract;
  }
}

async function buildUpstreamDeliverableContext(
  bindings: ConversationBindings,
  page: AiPageUid,
  accountUid: string | undefined,
  current: (uid: string) => string | null,
  thread: string,
): Promise<string> {
  if (!accountUid || !thread) return "";
  const pageUid = conversationFilePage(page);
  if (!pageUid) return "";
  const currentWorkItem = bindings.workItemUid ? String(current(bindings.workItemUid) ?? "").trim() : "";
  const workItemByThread = new Map<string, string>();
  for (const row of parseThreadRecords(current(bindings.threadStoreUid))) {
    workItemByThread.set(row.title, String(row.workItem ?? ""));
  }
  const candidates = parseNotebookTasks(current(bindings.notebookUid)).filter((row) => {
    if (!row.fileId || row.thread === thread) return false;
    if (!row.finalizedDoc && !(row.finalizedLabels ?? []).length) return false;
    const workItem = workItemByThread.get(row.thread) ?? "";
    return !currentWorkItem || !workItem || workItem !== currentWorkItem;
  });
  if (!candidates.length) return "";
  const parts: string[] = [];
  let budget = 9000;
  for (const row of candidates.slice(0, 3)) {
    if (budget <= 0) break;
    const fileId = row.fileId ?? "";
    if (!fileId) continue;
    const file = await persistFindConversationFile(fileId, accountUid ?? "").catch(() => null);
    if (!file?.body) continue;
    const body = file.body.slice(0, Math.min(3200, budget));
    budget -= body.length;
    parts.push(`【上游成品參考｜${workItemByThread.get(row.thread) || "其他工作項"}｜對話：${row.thread}】\n${body}`);
  }
  return parts.length
    ? `以下為同一專案其他工作項已定稿的成品，本次產出必須與其世界觀、人物與設定保持一致：\n${parts.join("\n\n")}`
    : "";
}

async function buildThreadContinuityContext(
  bindings: ConversationBindings,
  page: AiPageUid,
  accountUid: string | undefined,
  current: (uid: string) => string | null,
  thread: string,
): Promise<string> {
  if (!accountUid || !thread) return "";
  const pageUid = conversationFilePage(page);
  if (!pageUid) return "";
  const tasks = parseNotebookTasks(current(bindings.notebookUid)).filter((row) => row.thread === thread);
  const task = [...tasks].reverse().find((row) => (row.fileId ?? "").trim());
  const fileId = task?.fileId?.trim();
  if (!fileId) return "";
  const file = await persistFindConversationFile(fileId, accountUid).catch(() => null);
  const body = (file?.body ?? "").trim();
  if (body.length < 80) return "";
  const head = body.slice(0, 2000);
  const tail = body.length > 2400 ? body.slice(-1600) : "";
  const gap = body.length - head.length - tail.length;
  const middle = gap > 0 ? `\n……（中段省略 ${gap} 字）……\n` : "";
  return [
    `以下為本對話先前已交付的成品節錄（開頭與最新進度），本次回覆必須延續其設定、人物、情節與風格，禁止與既有內容產生矛盾：`,
    `【既有成品｜${file?.fileName ?? fileId}】`,
    `${head}${middle}${tail}`,
  ].join("\n");
}

async function fillConversationReply(
  table: string,
  bindings: ConversationBindings,
  page: AiPageUid,
  actionUid: string,
  nextValue?: string,
  accountUid?: string,
  signal?: AbortSignal,
  stream?: GenerationStreamSink,
): Promise<void> {
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    `SELECT control_uid, value_text FROM ${table}`,
  );
  const cache = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
  const current = (uid: string) => cache.get(uid) ?? null;
  const analyze = actionUid === `${bindings.prefix}-ACT-MSG-ANALYZE`;
  const prompt = analyze
    ? `分析此內容 ${parseConversationMessageActionPayload(nextValue).messageRef ?? ""}`.trim()
    : promptFromValue(nextValue);
  const tokens = resolveComposerTokensFor(bindings, prompt, current);
  if (tokens.some((row) => row.kind === "TARGET_ASSISTANT")) return;
  const thread = activeThreadUidFor(bindings, current);
  if (!thread) return;
  const history = conversationGenerationHistory(conversationMessagesForThread(current(bindings.messageUid), thread), prompt);
  const context = formatConversationContext(bindings, current);
  const contract = resolveTaskContract(
    prompt,
    current(bindings.notebookUid),
    conversationMessagesForThread(current(bindings.messageUid), thread),
    thread,
  );
  if (contract) stream?.status(contract.status);
  let generated: { text: string; truncated: boolean; loop: boolean; route: string } | null = null;
  let failed = false;
  let stopped = false;
  let providerCode = "";
  const startedAt = Date.now();
  try {
    if (prompt) {
      generated = await generatePageReply(page, prompt, context, history, {
        contract: contract ?? undefined,
        kind: contract?.kind,
        signal,
        onToken: stream ? (text) => stream.token(text) : undefined,
      });
    }
  } catch (error) {
    if (error instanceof GenerationCancelled) {
      generated = { text: error.partial, truncated: true, loop: false, route: "" };
      stopped = true;
    } else {
      failed = true;
      if (error instanceof AiProviderError) providerCode = error.code;
    }
  }
  const generatedContract = applyGeneratedContract(contract, generated, failed, stopped, startedAt, providerCode);
  const nextContract = await persistGeneratedFile(accountUid, page, generatedContract.nextContract, generatedContract.reply);
  if (nextContract) stream?.status(nextContract.status);
  else if (stopped) stream?.status("STOPPED");
  else if (failed) stream?.status("FAILED");
  const reply = attachFooter(generatedContract.reply, nextContract);
  if (stopped && !reply.trim() && !nextContract) return;
  const patch = appendAssistantMessageFor(
    bindings,
    current,
    thread,
    reply,
    undefined,
    new Date().toISOString(),
    generated?.route ?? "",
  );
  const patchedCurrent = (uid: string) => patch[uid] ?? current(uid);
  const notebookPatch = refreshAssistantNotebookFor(
    bindings,
    patchedCurrent,
    thread,
    conversationMessagesForThread(patchedCurrent(bindings.messageUid), thread),
    "record",
  );
  const afterNote = (uid: string) => notebookPatch[uid] ?? patchedCurrent(uid);
  const taskPatch = nextContract
    ? persistConversationTasksFor(bindings, afterNote, upsertTask(parseNotebookTasks(afterNote(bindings.notebookUid)), nextContract))
    : {};
  for (const [uid, value] of Object.entries({ ...patch, ...notebookPatch, ...taskPatch })) await writeField(table, uid, value);
}

async function fillCorrectionScriptBody(
  table: string,
  uid: string,
  page: "asset" | "video" | "edit",
  prompt: string,
  signal?: AbortSignal,
): Promise<void> {
  const candidate = parseCorrectionScript(await readField(table, uid));
  if (!candidate || candidate.status !== "CANDIDATE") return;
  let body = "";
  try {
    if (prompt) body = (await generatePageReply(page, prompt, "", [], { signal })).text;
  } catch (error) {
    if (error instanceof GenerationCancelled) body = error.partial;
    else {
      const code = error instanceof AiProviderError ? error.code : "AI_PROVIDER_UNREACHABLE";
      body = unavailableBody({ failed: true, empty: true, providerCode: code });
    }
  }
  await writeField(table, uid, serializeCorrectionScript(withCorrectionBody(candidate, body)));
}

async function fillAssetPatchPreview(table: string, uid: string, signal?: AbortSignal): Promise<void> {
  const patch = parseAssetPatch(await readField(table, uid));
  if (!patch || patch.status !== "PREVIEWED" || patch.preview) return;
  let body = "";
  try {
    body = (await generatePageReply("asset", patchPrompt(patch), "", [], { signal })).text;
  } catch (error) {
    if (error instanceof GenerationCancelled) body = error.partial;
    else {
      const code = error instanceof AiProviderError ? error.code : "AI_PROVIDER_UNREACHABLE";
      body = unavailableBody({ failed: true, empty: true, providerCode: code });
    }
  }
  await writeField(table, uid, serializeAssetPatch(withPatchPreview(patch, body)));
}

async function credentialFromValue(raw?: string): Promise<string> {
  const text = (raw ?? "").trim();
  if (text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      const candidate = parsed.reference ?? parsed.credential ?? parsed.secret;
      if (typeof candidate === "string") return candidate.trim();
    } catch {
      return "";
    }
  }
  return text;
}

function profileIdFromValue(raw?: string): string {
  const text = (raw ?? "").trim();
  if (!text.startsWith("{")) return "";
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    const candidate = parsed.profileId;
    return typeof candidate === "string" ? candidate.trim() : "";
  } catch {
    return "";
  }
}

async function applyProjectedAction(
  table: string,
  preview: (
    controlUid: string,
    actionUid: string,
    current: (uid: string) => string | null,
    nextValue?: string,
  ) => Record<string, string>,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
  seed?: Record<string, string | null>,
): Promise<boolean> {
  const cache = new Map<string, string | null>();
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    `SELECT control_uid, value_text FROM ${table}`,
  );
  for (const row of rows) cache.set(row.control_uid, row.value_text === "" ? null : row.value_text);
  for (const [uid, value] of Object.entries(seed ?? {})) cache.set(uid, value);
  const patch = preview(controlUid, actionUid, (uid) => cache.get(uid) ?? null, nextValue);
  const keys = Object.keys(patch);
  for (const [uid, value] of Object.entries(patch)) {
    await writeField(table, uid, value);
  }
  return keys.length > 0;
}

export async function applyWorkbenchAction(
  page: WorkbenchPage,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
  accountUid?: string,
  signal?: AbortSignal,
  stream?: GenerationStreamSink,
): Promise<AiapiOutcome | void> {
  if (page === "dashboard") {
    return;
  }
  if (page === "core") {
    if (actionUid === "CORE-01-ACT-FINALIZE" || actionUid === "CORE-01-ACT-REVIEW-REJECT") {
      await applyConversationReviewAction(actionUid, nextValue, accountUid);
      return;
    }
    if (accountUid && (actionUid === "CORE-01-ACT-MOTHER-LOCK-REQUEST" || actionUid === "CORE-01-ACT-CORE-REVIEW-SUBMIT")) {
      const gate = await enforceCoreCoverageGate(accountUid, actionUid === "CORE-01-ACT-MOTHER-LOCK-REQUEST" ? "MOTHER_LOCK" : "REVIEW");
      if (!gate.ok) return;
    }
    const assigned = await assignedAiRouteSnapshot().catch(() => "");
    const written = await applyProjectedAction(
      FIELD_TABLE.core,
      previewCoreAction,
      controlUid,
      actionUid,
      nextValue,
      { "CORE-01-FLD-ASSIGNED-AI": assigned },
    );
    if (accountUid && actionUid === "CORE-01-ACT-DNA-LOCK-REQUEST") {
      await enrichDnaDocument(accountUid);
    }
    if (accountUid && actionUid === "CORE-01-ACT-STORY-CORE-REQUEST") {
      await enrichStoryCoreDocument(accountUid);
    }
    if (accountUid && actionUid === "CORE-01-ACT-CHAPTER-ARCH-REQUEST") {
      await enrichChapterArchDocument(accountUid);
    }
    if (accountUid && written && actionUid === "CORE-01-ACT-MOTHER-LOCK-REQUEST") {
      const current = await loadCoreFields();
      const now = new Date().toISOString().slice(0, 19).replace("T", " ");
      const reviewer = exactName(current("CORE-01-BTN-PROJECT-LOCK"));
      const doc = parseBaseDna(current("CORE-01-BTN-DNA-LOCK"));
      if (doc && doc.status === "CANDIDATE") {
        await writeField(FIELD_TABLE.core, "CORE-01-BTN-DNA-LOCK", serializeBaseDna(withDnaStatus(doc, "LOCKED", reviewer, now)));
      }
      const storyDoc = parseStoryCore(current("CORE-01-BTN-STORY-CORE"));
      if (storyDoc && storyDoc.status === "CANDIDATE") {
        await writeField(FIELD_TABLE.core, "CORE-01-BTN-STORY-CORE", serializeStoryCore(withStoryCoreStatus(storyDoc, "LOCKED", reviewer, now)));
      }
      const chapterDoc = parseChapterArchitecture(current("CORE-01-BTN-CHAPTER-ARCH"));
      if (chapterDoc && chapterDoc.status === "CANDIDATE") {
        await writeField(FIELD_TABLE.core, "CORE-01-BTN-CHAPTER-ARCH", serializeChapterArchitecture(withChapterArchStatus(chapterDoc, "LOCKED", reviewer, now)));
      }
    }
    if (accountUid && (actionUid === "CORE-01-ACT-CANDIDATE-ACCEPT" || actionUid === "CORE-01-ACT-CANONICAL-SCRIPT-VIEW")) {
      await enrichCanonicalScriptProjection(accountUid, actionUid);
    }
    if (actionUid === "CORE-01-ACT-THREAD-DELETE" && accountUid) {
      const threadTitle = String(nextValue ?? "").trim();
      if (threadTitle) {
        await persistDeleteConversationFilesByThread(accountUid, threadTitle).catch(() => 0);
        const notebookUid = "CORE-01-FLD-ASSISTANT-SUMMARY";
        const notebookRows = await getSqlClient().all<{ value_text: string | null }>(
          `SELECT value_text FROM ${FIELD_TABLE.core} WHERE control_uid = ?`,
          [notebookUid],
        );
        const notebookRaw = notebookRows[0]?.value_text ?? null;
        if (notebookRaw && notebookRaw.startsWith("{")) {
          try {
            const parsed = JSON.parse(notebookRaw) as {
              kind?: string;
              records?: Array<{ thread?: string }>;
              tasks?: Array<{ thread?: string }>;
            };
            if (parsed.kind === "NOTEBOOK") {
              const records = (parsed.records ?? []).filter((row) => row?.thread !== threadTitle);
              const tasks = (parsed.tasks ?? []).filter((row) => row?.thread !== threadTitle);
              await writeField(
                FIELD_TABLE.core,
                notebookUid,
                JSON.stringify({ kind: "NOTEBOOK", records, ...(tasks.length ? { tasks } : {}) }),
              );
            }
          } catch {}
        }
      }
    }
    const analyze = actionUid === "CORE-01-ACT-MSG-ANALYZE";
    if ((actionUid === "CORE-01-ACT-SEND" || analyze) && written) {
      const prompt = analyze
        ? `分析此內容 ${parseMessageActionPayload(nextValue).messageRef ?? ""}`.trim()
        : promptFromValue(nextValue);
      const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
        `SELECT control_uid, value_text FROM ${FIELD_TABLE.core}`,
      );
      const cache = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
      if (assigned) cache.set("CORE-01-FLD-ASSIGNED-AI", assigned);
      const current = (uid: string) => cache.get(uid) ?? null;
      const tokens = resolveComposerTokens(prompt, current);
      if (tokens.some((row) => row.kind === "TARGET_ASSISTANT")) return;
      const thread = activeThreadUid(current);
      const history = generationHistoryPayload(messagesForThread(current("CORE-01-FLD-MESSAGE"), thread), prompt);
      const upstreamContext = await buildUpstreamDeliverableContext(CORE_CONVERSATION, page, accountUid, current, thread);
      const continuityContext = await buildThreadContinuityContext(CORE_CONVERSATION, page, accountUid, current, thread);
      const context = [formatCoreChatContext(current), upstreamContext, continuityContext].filter(Boolean).join("\n\n");
      const notebookUid = "CORE-01-FLD-ASSISTANT-SUMMARY";
      const contract = resolveTaskContract(
        prompt,
        current(notebookUid),
        messagesForThread(current("CORE-01-FLD-MESSAGE"), thread),
        thread,
      );
      if (contract) stream?.status(contract.status);
      if (isMultiAiMode(current)) {
        const aliases = targetedParticipantAliases(tokens, current);
        let replies: Array<{ alias: string; text: string; route: string; errorCode?: string }> = aliases.map((alias) => ({
          alias,
          text: "",
          route: "",
        }));
        let nextContract = contract;
        let multiFailed = false;
        let multiStopped = false;
        let multiCode = "";
        const startedAt = Date.now();
        try {
          if (prompt) {
            replies = await generateIndependentPageReplies(
              "core",
              prompt,
              context,
              history,
              aliases,
              signal,
              stream ? (text, alias) => stream.token(text, alias) : undefined,
              contract ?? undefined,
            );
          }
        } catch (error) {
          if (error instanceof GenerationCancelled) {
            replies = aliases.map((alias) => ({ alias, text: error.partial, route: "" }));
            multiStopped = true;
            if (contract) {
              nextContract = updateContractAfterGeneration(contract, error.partial, {
                truncated: true,
                loop: false,
                stopped: true,
              });
            }
          } else {
            replies = aliases.map((alias) => ({ alias, text: "", route: "" }));
            multiFailed = true;
            if (error instanceof AiProviderError) multiCode = error.code;
            if (contract) nextContract = { ...contract, status: "FAILED" };
          }
        }
        const joined = replies.map((row) => row.text).join("\n");
        const firstCode = replies.find((row) => row.errorCode)?.errorCode || multiCode;
        if (!multiStopped && !joined.trim()) {
          multiFailed = true;
          multiCode = firstCode;
          if (contract) nextContract = { ...contract, status: "FAILED" };
        } else if (!multiStopped && contract) {
          const unusable = detectUnusableOutput(joined);
          if (unusable) {
            multiFailed = true;
            multiCode = firstCode || "AI_PROVIDER_UNUSABLE_OUTPUT";
          }
          nextContract = updateContractAfterGeneration(contract, joined, {
            truncated: false,
            loop: false,
            failed: unusable,
            unusable,
          });
        }
        nextContract = withTaskObservation(nextContract ?? null, {
          chars: joined.length,
          durationMs: Date.now() - startedAt,
          loop: false,
          truncated: multiStopped,
          failReason: diagnoseGenerationFailure({
            failed: multiFailed,
            empty: !joined.trim(),
            truncated: multiStopped,
            providerCode: multiCode,
          }),
        });
        nextContract = await persistGeneratedFile(accountUid, "core", nextContract, joined);
        if (nextContract) stream?.status(nextContract.status);
        const patch = appendAssistantMessages(
          current,
          thread,
          replies.map((row) => ({
            text: attachFooter(
              row.text.trim()
                ? row.text
                : unavailableBody({ failed: !multiStopped, empty: true, providerCode: row.errorCode || multiCode }),
              nextContract,
            ),
            alias: row.alias,
            at: new Date().toISOString(),
            route: row.route,
          })),
        );
        const patchedCurrent = (uid: string) => patch[uid] ?? current(uid);
        const notebookPatch = refreshAssistantNotebook(
          patchedCurrent,
          thread,
          messagesForThread(patchedCurrent("CORE-01-FLD-MESSAGE"), thread),
          "record",
        );
        const afterNote = (uid: string) => notebookPatch[uid] ?? patchedCurrent(uid);
        const taskPatch = nextContract
          ? persistConversationTasks(afterNote, upsertTask(parseNotebookTasks(current(notebookUid)), nextContract))
          : {};
        for (const [uid, value] of Object.entries({ ...patch, ...notebookPatch, ...taskPatch })) await writeField(FIELD_TABLE.core, uid, value);
        return;
      }
      let generated: { text: string; truncated: boolean; loop: boolean; route: string } | null = null;
      let failed = false;
      let stopped = false;
      let providerCode = "";
      const startedAt = Date.now();
      try {
        if (prompt) {
          generated = await generatePageReply("core", prompt, context, history, {
            contract: contract ?? undefined,
            kind: contract?.kind,
            signal,
            onToken: stream ? (text) => stream.token(text) : undefined,
          });
        }
      } catch (error) {
        if (error instanceof GenerationCancelled) {
          generated = { text: error.partial, truncated: true, loop: false, route: "" };
          stopped = true;
        } else {
          failed = true;
          if (error instanceof AiProviderError) providerCode = error.code;
        }
      }
      const generatedContract = applyGeneratedContract(contract, generated, failed, stopped, startedAt, providerCode);
      const nextContract = await persistGeneratedFile(accountUid, "core", generatedContract.nextContract, generatedContract.reply);
      if (nextContract) stream?.status(nextContract.status);
      else if (stopped) stream?.status("STOPPED");
      else if (failed) stream?.status("FAILED");
      const reply = attachFooter(generatedContract.reply, nextContract);
      if (stopped && !reply.trim() && !nextContract) return;
      const patch = appendAssistantMessage(current, thread, reply, undefined, new Date().toISOString(), generated?.route ?? "");
      const patchedCurrent = (uid: string) => patch[uid] ?? current(uid);
      const notebookPatch = refreshAssistantNotebook(
        patchedCurrent,
        thread,
        messagesForThread(patchedCurrent("CORE-01-FLD-MESSAGE"), thread),
        "record",
      );
      const afterNote = (uid: string) => notebookPatch[uid] ?? patchedCurrent(uid);
      const taskPatch = nextContract
        ? persistConversationTasks(afterNote, upsertTask(parseNotebookTasks(current(notebookUid)), nextContract))
        : {};
      for (const [uid, value] of Object.entries({ ...patch, ...notebookPatch, ...taskPatch })) await writeField(FIELD_TABLE.core, uid, value);
    }
    return;
  }
  if (page === "asset") {
    const coreRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_core_field_projection",
    );
    const coreByUid = new Map(
      coreRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const inbound = resolveAssetInbound((uid) => coreByUid.get(uid) ?? null);
    const seed: Record<string, string> = compact({
      "ASSET-01-CTL-PROJECT": inbound.project,
      "ASSET-01-CTL-TOPIC": inbound.topic,
      "ASSET-01-FLD-TASK": inbound.task,
      "ASSET-01-FLD-BLUEPRINT": inbound.blueprint,
      "ASSET-01-FLD-DNA": inbound.dna,
      "ASSET-01-FLD-SCRIPT": inbound.script,
      "ASSET-01-FLD-NAMING-AUTHORITY": inbound.naming,
    });
    const written = await applyProjectedAction(FIELD_TABLE.asset, previewAssetAction, controlUid, actionUid, nextValue, seed);
    if ((actionUid === "ASSET-01-ACT-SEND" || actionUid === "ASSET-01-ACT-MSG-ANALYZE") && written) {
      await fillConversationReply(FIELD_TABLE.asset, ASSET_CONVERSATION, "asset", actionUid, nextValue, accountUid, signal, stream);
    }
    if (actionUid === "ASSET-01-ACT-CORRECTION-GENERATE" && written) {
      const prompt = promptFromValue(nextValue) || (await readField(FIELD_TABLE.asset, "ASSET-01-TXT-CORRECTION-REQUEST")) || "";
      await fillCorrectionScriptBody(FIELD_TABLE.asset, ASSET_CORRECTION_RESPONSE_UID, "asset", prompt, signal);
    }
    if (actionUid === "ASSET-01-ACT-PATCH-PREVIEW" && written) {
      await fillAssetPatchPreview(FIELD_TABLE.asset, "ASSET-01-BTN-PATCH-CREATE", signal);
    }
    if (actionUid === "ASSET-01-ACT-HANDOFF") {
      const locked = await readField(FIELD_TABLE.asset, "ASSET-01-BTN-LOCK");
      const version = await readField(FIELD_TABLE.asset, "ASSET-01-FLD-HANDOFF-ASSET-VERSION");
      if (locked === "locked" && version) await writeField(FIELD_TABLE.core, "CORE-01-FLD-DOWNSTREAM-ASSET", version);
    }
    return;
  }
  if (page === "video") {
    const coreRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_core_field_projection",
    );
    const coreByUid = new Map(
      coreRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const assetRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_asset_field_projection",
    );
    const assetByUid = new Map(
      assetRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const inbound = resolveVideoInbound((uid) => coreByUid.get(uid) ?? null, (uid) => assetByUid.get(uid) ?? null);
    const seed: Record<string, string> = compact({
      "VIDEO-01-FLD-PROJECT": inbound.project,
      "VIDEO-01-FLD-TOPIC": inbound.topic,
      "VIDEO-01-FLD-TASK": inbound.task,
      "VIDEO-01-FLD-BLUEPRINT-REF": inbound.blueprint,
      "VIDEO-01-FLD-DNA-REFS": inbound.dna,
      "VIDEO-01-FLD-SCRIPT-SECTION": inbound.script,
      "VIDEO-01-FLD-ASSET-REFS": inbound.assetVersion,
      "VIDEO-01-FLD-LAYER-VERSIONS": inbound.layerComposite,
      "VIDEO-01-FLD-FILENAME-CHECKSUM": [inbound.filename, inbound.checksum].filter(Boolean).join(" / "),
      "VIDEO-01-FLD-RIGHTS": inbound.rights,
      "VIDEO-01-FLD-INSTRUCTION": inbound.instruction,
    });
    const written = await applyProjectedAction(FIELD_TABLE.video, previewVideoAction, controlUid, actionUid, nextValue, seed);
    if ((actionUid === "VIDEO-01-ACT-SEND" || actionUid === "VIDEO-01-ACT-MSG-ANALYZE") && written) {
      await fillConversationReply(FIELD_TABLE.video, VIDEO_CONVERSATION, "video", actionUid, nextValue, accountUid, signal, stream);
    }
    if (actionUid === "VIDEO-01-ACT-CORRECTION-GENERATE" && written) {
      const prompt = promptFromValue(nextValue) || (await readField(FIELD_TABLE.video, "VIDEO-01-TXT-CORRECTION")) || "";
      await fillCorrectionScriptBody(FIELD_TABLE.video, VIDEO_CORRECTION_RESPONSE_UID, "video", prompt, signal);
    }
    if (actionUid === "VIDEO-01-ACT-HANDOFF") {
      const locked = await readField(FIELD_TABLE.video, "VIDEO-01-BTN-LOCK");
      const contract = await readField(FIELD_TABLE.video, "VIDEO-01-FLD-HANDOFF-CONTRACT");
      if (locked === "locked" && contract) await writeField(FIELD_TABLE.core, "CORE-01-FLD-DOWNSTREAM-VIDEO", contract);
    }
    return;
  }
  if (page === "edit") {
    const coreRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_core_field_projection",
    );
    const coreByUid = new Map(
      coreRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const assetRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_asset_field_projection",
    );
    const assetByUid = new Map(
      assetRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const videoRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_video_field_projection",
    );
    const videoByUid = new Map(
      videoRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const coreCurrent = (uid: string) => coreByUid.get(uid) ?? null;
    const inbound = resolveEditInbound(
      effectiveVideoCurrent(coreCurrent, (uid) => assetByUid.get(uid) ?? null, (uid) => videoByUid.get(uid) ?? null),
      coreCurrent,
    );
    const seed: Record<string, string> = compact({
      "EDIT-01-FLD-PROJECT": inbound.project,
      "EDIT-01-FLD-TOPIC": inbound.topic,
      "EDIT-01-FLD-TASK": inbound.task,
      "EDIT-01-FLD-SOURCE-VERSION": inbound.sourceVersion,
      "EDIT-01-LBL-BINDING-FINGERPRINT": inbound.handoffContract,
      "EDIT-01-LBL-CURRENT-SCRIPT-SECTION": inbound.script,
    });
    const written = await applyProjectedAction(FIELD_TABLE.edit, previewEditAction, controlUid, actionUid, nextValue, seed);
    if ((actionUid === "EDIT-01-ACT-SEND" || actionUid === "EDIT-01-ACT-MSG-ANALYZE") && written) {
      await fillConversationReply(FIELD_TABLE.edit, EDIT_CONVERSATION, "edit", actionUid, nextValue, accountUid, signal, stream);
    }
    if (actionUid === "EDIT-01-ACT-CORRECTION-CANDIDATE-GENERATE" && written) {
      const prompt = promptFromValue(nextValue) || (await readField(FIELD_TABLE.edit, "EDIT-01-FLD-API-INSTRUCTION")) || "";
      await fillCorrectionScriptBody(FIELD_TABLE.edit, EDIT_CORRECTION_CANDIDATE_UID, "edit", prompt, signal);
    }
    if (actionUid === "EDIT-01-ACT-HANDOFF") {
      const locked = await readField(FIELD_TABLE.edit, "EDIT-01-BTN-VERSION-LOCK");
      const version = await readField(FIELD_TABLE.edit, "EDIT-01-FLD-SOURCE-VERSION");
      if (locked === "locked" && version) await writeField(FIELD_TABLE.core, "CORE-01-FLD-DOWNSTREAM-EDIT", version);
    }
    return;
  }
  if (page === "qa") {
    const coreRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_core_field_projection",
    );
    const coreByUid = new Map(
      coreRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const assetRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_asset_field_projection",
    );
    const assetByUid = new Map(
      assetRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const videoRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_video_field_projection",
    );
    const videoByUid = new Map(
      videoRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const editRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
      "SELECT control_uid, value_text FROM ghsn_edit_field_projection",
    );
    const editByUid = new Map(
      editRows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const),
    );
    const inbound = resolveQaInbound(
      (uid) => coreByUid.get(uid) ?? null,
      (uid) => assetByUid.get(uid) ?? null,
      (uid) => videoByUid.get(uid) ?? null,
      (uid) => editByUid.get(uid) ?? null,
    );
    const seed: Record<string, string | null> = {
      "QA-01-FLD-PROJECT": inbound.project || null,
      "QA-01-FLD-TOPIC": inbound.topic || null,
      "QA-01-FLD-QA-TASK": inbound.task || null,
      "QA-01-FLD-TARGET-OUTPUT": inbound.targetOutput || null,
      "QA-01-FLD-QA-SCRIPT": inbound.scriptView || null,
      "QA-01-FLD-SCRIPT-HASH": inbound.scriptHash || null,
      "QA-01-FLD-CRITERIA-VERSION": inbound.criteriaVersion || null,
      "QA-01-FLD-CHECKSUM": inbound.checksum || null,
      "QA-01-FLD-RIGHTS": inbound.rights || null,
      "QA-01-FLD-PROVENANCE": inbound.provenance || null,
    };
    await applyProjectedAction(FIELD_TABLE.qa, previewQaAction, controlUid, actionUid, nextValue, seed);
    return;
  }
  if (page === "soc") {
    await applyProjectedAction(FIELD_TABLE.soc, previewSocAction, controlUid, actionUid, nextValue);
    return;
  }
  if (page === "dev") {
    const written = await applyProjectedAction(FIELD_TABLE.dev, previewDevAction, controlUid, actionUid, nextValue);
    const errorRaw = await readField(FIELD_TABLE.dev, "DEV-01-STATE-ERROR");
    const triggersCollection =
      written &&
      !errorRaw &&
      (actionUid === "DEV-01-ACT-DISCOVERY-START" ||
        actionUid === "DEV-01-ACT-DISCOVERY-RESUME" ||
        (actionUid === "DEV-01-ACT-REFRESH" && nextValue === "CONTINUOUS_PULL"));
    if (triggersCollection) {
      const jobRaw = await readField(FIELD_TABLE.dev, "DEV-01-STATE-JOB");
      const job = parseJson<{ status?: string; cursor?: number }>(jobRaw, {});
      if (job.status === "RUNNING") {
        const profile = parseJson<DevProfile | null>(await readField(FIELD_TABLE.dev, "DEV-01-STATE-PROFILE"), null);
        if (profile) {
          const collected = await collectDiscoverySignals(profile, job.cursor ?? 0);
          const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
            `SELECT control_uid, value_text FROM ${FIELD_TABLE.dev}`,
          );
          const cache = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
          const patch = applyDiscoveryCollection((uid) => cache.get(uid) ?? null, collected);
          for (const [uid, value] of Object.entries(patch)) await writeField(FIELD_TABLE.dev, uid, value);
        }
      }
    }
    return;
  }
  if (page === "kb") {
    await applyProjectedAction(FIELD_TABLE.kb, previewKbAction, controlUid, actionUid, nextValue);
    if (actionUid === "createAcquisitionJob") {
      const profile = parseJson<DevProfile | null>(await readField(FIELD_TABLE.dev, "DEV-01-STATE-PROFILE"), null) ?? {
        profileId: "",
        version: 0,
        product: "",
        industry: "",
        market: "",
        keywords: "",
        exclude: "",
        language: "zh-TW",
        priority: "NORMAL" as const,
        sourceScope: "ALLOWED",
        mode: "SINGLE" as const,
        status: "DRAFT" as const,
      };
      const collected = await collectDiscoverySignals(profile);
      const patch = kbAcquisitionPatchFromCollect(collected);
      for (const [uid, value] of Object.entries(patch)) await writeField(FIELD_TABLE.kb, uid, value);
    }
    return;
  }
  if (page === "aiapi") {
    if (actionUid === "createProviderModelProfile") return runCreateProviderProfile(nextValue);
    if (actionUid === "testProviderModelProfile") return runConnectionTest(nextValue);
    if (actionUid === "admin:AIAPI-08:ACT-SYSTEM-TEST") return runSandboxTest(nextValue);
    if (actionUid === "executeProviderRoute") return runRouteExecution(nextValue);
    if (actionUid === "runProviderQueueProbe") return runQueueProbe();
    await applyProjectedAction(FIELD_TABLE.aiapi, previewAiapiAction, controlUid, actionUid, nextValue);
    if (actionUid === "setProviderModelCredential") {
      const secret = await credentialFromValue(nextValue);
      const profileId = profileIdFromValue(nextValue);
      if (secret && profileId) await setAiapiCredential(profileId, secret);
    } else if (actionUid === "deleteProviderModelCredential") {
      const profileId = profileIdFromValue(nextValue);
      if (profileId) await clearAiapiCredential(profileId);
    }
    return;
  }
  await writeField(FIELD_TABLE[page], controlUid, statusFromAction(actionUid));
}
