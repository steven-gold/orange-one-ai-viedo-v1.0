import { AI_UNAVAILABLE_ZH, ASSET_CORRECTION_RESPONSE_UID, VIDEO_CORRECTION_RESPONSE_UID } from "@/lib/aiReply";
import { previewAiapiAction } from "@/lib/aiapiActionPreview";
import { previewAssetAction } from "@/lib/assetActionPreview";
import { resolveAssetInbound } from "@/lib/assetInbound";
import {
  activeThreadUid,
  appendAssistantMessage,
  formatCoreChatContext,
  messagesForThread,
  previewCoreAction,
} from "@/lib/coreActionPreview";
import { previewEditAction } from "@/lib/editActionPreview";
import { resolveEditInbound, effectiveVideoCurrent } from "@/lib/editInbound";
import { resolveVideoInbound } from "@/lib/videoInbound";
import { previewVideoAction } from "@/lib/videoActionPreview";
import { generatePageReply } from "../ai/llmClient";
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

async function writeGeneratedReply(
  table: string,
  targetUids: string[],
  page: "core" | "asset" | "video",
  prompt: string,
  context: string,
): Promise<void> {
  if (!prompt) return;
  try {
    const reply = await generatePageReply(page, prompt, context);
    for (const uid of targetUids) await writeField(table, uid, reply);
  } catch {
    for (const uid of targetUids) await writeField(table, uid, AI_UNAVAILABLE_ZH);
  }
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
  seed?: Record<string, string>,
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
): Promise<AiapiOutcome | void> {
  if (page === "dashboard") {
    return;
  }
  if (page === "core") {
    const written = await applyProjectedAction(FIELD_TABLE.core, previewCoreAction, controlUid, actionUid, nextValue);
    if (actionUid === "CORE-01-ACT-SEND" && written) {
      const prompt = promptFromValue(nextValue);
      const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
        `SELECT control_uid, value_text FROM ${FIELD_TABLE.core}`,
      );
      const cache = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
      const current = (uid: string) => cache.get(uid) ?? null;
      const thread = activeThreadUid(current);
      const history = messagesForThread(current("CORE-01-FLD-MESSAGE"), thread)
        .slice(0, -1)
        .map((row) => ({ role: row.role, content: row.text }));
      const context = formatCoreChatContext(current);
      let reply = AI_UNAVAILABLE_ZH;
      try {
        if (prompt) reply = await generatePageReply("core", prompt, context, history);
      } catch {
        reply = AI_UNAVAILABLE_ZH;
      }
      const patch = appendAssistantMessage(current, thread, reply);
      for (const [uid, value] of Object.entries(patch)) await writeField(FIELD_TABLE.core, uid, value);
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
    await applyProjectedAction(FIELD_TABLE.asset, previewAssetAction, controlUid, actionUid, nextValue, seed);
    if (actionUid === "ASSET-01-ACT-CORRECTION-GENERATE") {
      const prompt = promptFromValue(nextValue) || (await readField(FIELD_TABLE.asset, "ASSET-01-TXT-CORRECTION-REQUEST")) || "";
      await writeGeneratedReply(FIELD_TABLE.asset, [ASSET_CORRECTION_RESPONSE_UID], "asset", prompt, "");
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
      "VIDEO-01-FLD-FILENAME-CHECKSUM": [inbound.filename, inbound.checksum].filter(Boolean).join(" / "),
      "VIDEO-01-FLD-RIGHTS": inbound.rights,
      "VIDEO-01-FLD-INSTRUCTION": inbound.instruction,
    });
    await applyProjectedAction(FIELD_TABLE.video, previewVideoAction, controlUid, actionUid, nextValue, seed);
    if (actionUid === "VIDEO-01-ACT-CORRECTION-GENERATE") {
      const prompt = promptFromValue(nextValue) || (await readField(FIELD_TABLE.video, "VIDEO-01-TXT-CORRECTION")) || "";
      await writeGeneratedReply(FIELD_TABLE.video, [VIDEO_CORRECTION_RESPONSE_UID], "video", prompt, "");
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
    await applyProjectedAction(FIELD_TABLE.edit, previewEditAction, controlUid, actionUid, nextValue, seed);
    if (actionUid === "EDIT-01-ACT-HANDOFF") {
      const locked = await readField(FIELD_TABLE.edit, "EDIT-01-BTN-VERSION-LOCK");
      const version = await readField(FIELD_TABLE.edit, "EDIT-01-FLD-SOURCE-VERSION");
      if (locked === "locked" && version) await writeField(FIELD_TABLE.core, "CORE-01-FLD-DOWNSTREAM-EDIT", version);
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
