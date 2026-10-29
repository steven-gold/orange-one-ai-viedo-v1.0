import {
  CONVERSATION_FILE_TABLE,
  type ConversationFilePage,
  type ConversationFileRecord,
} from "@/lib/conversationFile";
import { getSqlClient } from "./client";

type ConversationFileRow = {
  file_uid: string;
  account_uid: string;
  page_uid: string;
  task_id: string;
  thread: string;
  file_name: string;
  mime_type: string;
  body_text: string;
  version: number;
  updated_at: string;
};

function fromRow(row: ConversationFileRow): ConversationFileRecord {
  return {
    fileUid: row.file_uid,
    accountUid: row.account_uid,
    pageUid: row.page_uid as ConversationFilePage,
    taskId: row.task_id,
    thread: row.thread,
    fileName: row.file_name,
    mimeType: row.mime_type,
    body: row.body_text,
    version: Number(row.version ?? 0),
    updatedAt: row.updated_at,
  };
}

export async function persistFindConversationFile(
  fileUid: string,
  accountUid: string,
): Promise<ConversationFileRecord | null> {
  const rows = await getSqlClient().all<ConversationFileRow>(
    `SELECT file_uid, account_uid, page_uid, task_id, thread, file_name, mime_type, body_text, version, updated_at
     FROM ${CONVERSATION_FILE_TABLE}
     WHERE file_uid = ? AND account_uid = ?`,
    [fileUid, accountUid],
  );
  return rows[0] ? fromRow(rows[0]) : null;
}

export async function persistFindConversationFileByTask(
  accountUid: string,
  pageUid: ConversationFilePage,
  taskId: string,
): Promise<ConversationFileRecord | null> {
  const rows = await getSqlClient().all<ConversationFileRow>(
    `SELECT file_uid, account_uid, page_uid, task_id, thread, file_name, mime_type, body_text, version, updated_at
     FROM ${CONVERSATION_FILE_TABLE}
     WHERE account_uid = ? AND page_uid = ? AND task_id = ?`,
    [accountUid, pageUid, taskId],
  );
  return rows[0] ? fromRow(rows[0]) : null;
}

export async function persistUpsertConversationFile(file: ConversationFileRecord): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ${CONVERSATION_FILE_TABLE} (
       file_uid, account_uid, page_uid, task_id, thread, file_name, mime_type, body_text, version, updated_at
     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT (file_uid) DO UPDATE SET
       thread = EXCLUDED.thread,
       file_name = EXCLUDED.file_name,
       mime_type = EXCLUDED.mime_type,
       body_text = EXCLUDED.body_text,
       version = EXCLUDED.version,
       updated_at = EXCLUDED.updated_at`,
    [
      file.fileUid,
      file.accountUid,
      file.pageUid,
      file.taskId,
      file.thread,
      file.fileName,
      file.mimeType,
      file.body,
      file.version,
      file.updatedAt,
    ],
  );
}

export async function persistDeleteConversationFilesByThread(accountUid: string, thread: string): Promise<number> {
  if (!accountUid || !thread) return 0;
  const result = await getSqlClient().run(
    `DELETE FROM ${CONVERSATION_FILE_TABLE} WHERE account_uid = ? AND thread = ?`,
    [accountUid, thread],
  );
  return result?.changes ?? 0;
}
