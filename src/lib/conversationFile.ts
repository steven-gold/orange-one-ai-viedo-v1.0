import {
  conversationFileUid,
  fileNameForContract,
  stripDeliveryFooter,
  type ConversationTaskContract,
} from "./conversationTask";

export const CONVERSATION_FILE_TABLE = "ghsn_conversation_file";

export type ConversationFilePage = "core" | "asset" | "video" | "edit";

export type ConversationFileRecord = {
  fileUid: string;
  accountUid: string;
  pageUid: ConversationFilePage;
  taskId: string;
  thread: string;
  fileName: string;
  mimeType: string;
  body: string;
  version: number;
  updatedAt: string;
};

export function conversationFilePage(page: string): ConversationFilePage | null {
  if (page === "core" || page === "asset" || page === "video" || page === "edit") return page;
  return null;
}

export function buildConversationFile(
  accountUid: string,
  pageUid: ConversationFilePage,
  contract: ConversationTaskContract,
  rawBody: string,
  prior?: ConversationFileRecord | null,
): ConversationFileRecord | null {
  if (!contract.needsFile || !accountUid || !contract.taskId) return null;
  const body = stripDeliveryFooter(rawBody);
  if (!body) return null;
  const nextBody = prior?.body ? mergeFileBody(prior.body, body) : body;
  return {
    fileUid: prior?.fileUid || conversationFileUid(accountUid, pageUid, contract.taskId),
    accountUid,
    pageUid,
    taskId: contract.taskId,
    thread: contract.thread,
    fileName: prior?.fileName || fileNameForContract(contract),
    mimeType: "text/plain; charset=utf-8",
    body: nextBody,
    version: (prior?.version ?? 0) + 1,
    updatedAt: new Date().toISOString(),
  };
}

export function mergeFileBody(previous: string, next: string): string {
  const left = previous.trimEnd();
  const right = next.trim();
  if (!left) return right;
  if (!right) return left;
  if (left.includes(right)) return left;
  if (right.includes(left)) return right;
  const probe = Math.min(left.length, 240);
  for (let size = probe; size >= 8; size -= 1) {
    const tail = left.slice(-size);
    if (right.startsWith(tail)) return `${left}${right.slice(size)}`;
  }
  const gap = left.endsWith("\n") || right.startsWith("\n") ? "\n" : "\n\n";
  return `${left}${gap}${right}`;
}

export function attachFileToContract(
  contract: ConversationTaskContract,
  file: ConversationFileRecord | null,
): ConversationTaskContract {
  if (!file) return contract;
  return { ...contract, fileId: file.fileUid, fileName: file.fileName };
}

export function conversationFileVerified(
  expected: ConversationFileRecord,
  stored: ConversationFileRecord | null,
): boolean {
  if (!stored) return false;
  return (
    stored.fileUid === expected.fileUid &&
    stored.accountUid === expected.accountUid &&
    stored.pageUid === expected.pageUid &&
    stored.taskId === expected.taskId &&
    stored.fileName === expected.fileName &&
    stored.body === expected.body
  );
}
