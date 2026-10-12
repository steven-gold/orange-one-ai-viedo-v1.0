import { getSqlClient } from "../db/client";

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

function stampId(prefix: string): string {
  const now = new Date();
  const y = now.getUTCFullYear();
  const m = String(now.getUTCMonth() + 1).padStart(2, "0");
  const d = String(now.getUTCDate()).padStart(2, "0");
  const t = String(now.getUTCHours()).padStart(2, "0") + String(now.getUTCMinutes()).padStart(2, "0");
  return `${prefix}-${y}${m}${d}-${t}`;
}

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
  };
  for (const [key, value] of Object.entries(map)) {
    if (actionUid.includes(key)) return value;
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

async function writeField(table: string, controlUid: string, value: string): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ${table} (control_uid, value_text)
     VALUES (?, ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [controlUid, value],
  );
}

async function applyCoreAction(controlUid: string, actionUid: string, nextValue?: string): Promise<void> {
  const table = FIELD_TABLE.core;
  if (actionUid === "CORE-01-ACT-PROJECT-CREATE") {
    const project = stampId("P");
    await writeField(table, "CORE-01-CTL-PROJECT", project);
    await writeField(table, "CORE-01-FLD-PAGE-MODE", "PROJECT_CORE");
    await writeField(table, "CORE-01-FLD-NAMING-AUTHORITY", "ACPOS_SYSTEM");
    await writeField(table, "CORE-01-FLD-RUNTIME-STAGE", "AI_RESPONSES");
    await writeField(table, "CORE-01-LST-WORK-ITEMS", "STORY");
    return;
  }
  if (actionUid === "CORE-01-ACT-TOPIC-CREATE") {
    const topic = stampId("T");
    await writeField(table, "CORE-01-CTL-TOPIC", topic);
    await writeField(table, "CORE-01-FLD-PAGE-MODE", "TOPIC_PRODUCTION");
    await writeField(table, "CORE-01-FLD-TOPIC-SCOPE", topic);
    await writeField(table, "CORE-01-FLD-PACKAGE", "PKG-READY");
    await writeField(table, "CORE-01-LST-WORK-ITEMS", "TOPIC_SCOPE");
    return;
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-PAGE-MODE") {
    const current = await readField(table, "CORE-01-FLD-PAGE-MODE");
    const next = current === "TOPIC_PRODUCTION" ? "PROJECT_CORE" : "TOPIC_PRODUCTION";
    await writeField(table, "CORE-01-FLD-PAGE-MODE", next);
    await writeField(table, "CORE-01-LST-WORK-ITEMS", next === "TOPIC_PRODUCTION" ? "TOPIC_SCOPE" : "STORY");
    return;
  }
  if (actionUid === "CORE-01-ACT-AI-MODE-SINGLE") {
    await writeField(table, "CORE-01-BTN-SINGLE-AI", "active");
    await writeField(table, "CORE-01-BTN-MULTI-AI", "idle");
    await writeField(table, "CORE-01-FLD-ASSIGNED-AI", "SINGLE");
    return;
  }
  if (actionUid === "CORE-01-ACT-AI-MODE-MULTI") {
    await writeField(table, "CORE-01-BTN-MULTI-AI", "active");
    await writeField(table, "CORE-01-BTN-SINGLE-AI", "idle");
    await writeField(table, "CORE-01-FLD-ASSIGNED-AI", "MULTI");
    return;
  }
  if (actionUid === "CORE-01-ACT-THREAD-CREATE") {
    await writeField(table, "CORE-01-LST-THREADS", stampId("TH"));
    await writeField(table, "CORE-01-BTN-NEW-THREAD", "created");
    return;
  }
  if (actionUid === "CORE-01-ACT-SEND") {
    await writeField(table, "CORE-01-FLD-MESSAGE", "sent");
    await writeField(table, "CORE-01-FLD-ASSISTANT-SUMMARY", "recorded");
    await writeField(table, "CORE-01-FLD-RUNTIME-STAGE", "ASSISTANT_SUMMARY");
    return;
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-CREATE") {
    await writeField(table, "CORE-01-FLD-VERSION-STATE", stampId("CAND"));
    await writeField(table, "CORE-01-BTN-CANDIDATE-CREATE", "created");
    return;
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-ACCEPT") {
    await writeField(table, "CORE-01-BTN-CANDIDATE-CONFIRM", "confirmed");
    await writeField(table, "CORE-01-FLD-LOCK-REVIEW", "ready");
    await writeField(table, "CORE-01-FLD-HUMAN-DECISION", "confirmed");
    return;
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-CREATE") {
    await writeField(table, "CORE-01-BTN-BLUEPRINT-CREATE", stampId("BP"));
    await writeField(table, "CORE-01-FLD-PACKAGE", stampId("BP"));
    return;
  }
  if (actionUid === "CORE-01-ACT-WORK-ITEM-SELECT") {
    await writeField(table, "CORE-01-LST-WORK-ITEMS", nextValue ?? "STORY");
    return;
  }
  if (actionUid === "CORE-01-ACT-THREAD-SELECT") {
    await writeField(table, "CORE-01-LST-THREADS", nextValue ?? "selected");
    return;
  }
  if (controlUid === "CORE-01-FLD-RUNTIME-STAGE" && nextValue) {
    await writeField(table, "CORE-01-FLD-RUNTIME-STAGE", nextValue);
    return;
  }
  await writeField(table, controlUid, statusFromAction(actionUid));
}

export async function applyWorkbenchAction(page: WorkbenchPage, controlUid: string, actionUid: string, nextValue?: string): Promise<void> {
  if (page === "dashboard") {
    return;
  }
  if (page === "core") {
    await applyCoreAction(controlUid, actionUid, nextValue);
    return;
  }
  await writeField(FIELD_TABLE[page], controlUid, statusFromAction(actionUid));
}
