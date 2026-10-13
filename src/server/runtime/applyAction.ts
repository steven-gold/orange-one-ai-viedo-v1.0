import { previewCoreAction } from "@/lib/coreActionPreview";
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
  const needed = [
    "CORE-01-CTL-PROJECT",
    "CORE-01-CTL-TOPIC",
    "CORE-01-FLD-PAGE-MODE",
    "CORE-01-FLD-TOPIC-SCOPE",
    "CORE-01-FLD-NAMING-AUTHORITY",
    "CORE-01-LST-WORK-ITEMS",
    "CORE-01-LST-THREADS",
    "CORE-01-BTN-NEW-THREAD",
  ];
  const cache = new Map<string, string | null>();
  await Promise.all(
    needed.map(async (uid) => {
      cache.set(uid, await readField(table, uid));
    }),
  );
  const patch = previewCoreAction(controlUid, actionUid, (uid) => cache.get(uid) ?? null, nextValue);
  for (const [uid, value] of Object.entries(patch)) {
    await writeField(table, uid, value);
  }
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
