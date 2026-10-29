import {
  batchUnitPattern,
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
  const nextBody = prior?.body
    ? contract.mode === "correction"
      ? patchConversationFileBody(prior.body, body, batchUnitPattern(contract.quantity?.unit ?? "集"))
      : mergeFileBody(prior.body, body)
    : body;
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

export function patchConversationFileBody(previous: string, patchText: string, unit = "集"): string {
  const body = patchText.trim();
  if (!body) return previous;
  const headingRe = new RegExp(`^\\s*(?:#{1,4}\\s*)?[*_\`]{0,3}\\s*第\\s*(\\d+)\\s*${unit}[*_\`]{0,3}[^\\n]*`, "gmu");
  const patchBlocks: Array<{ label: number; text: string }> = [];
  const matches = [...body.matchAll(headingRe)];
  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index];
    const start = match.index ?? 0;
    const end = index + 1 < matches.length ? matches[index + 1].index ?? body.length : body.length;
    const label = Number.parseInt(match[1], 10);
    if (Number.isFinite(label) && label > 0) patchBlocks.push({ label, text: body.slice(start, end).trim() });
  }
  if (!patchBlocks.length) return mergeFileBody(previous, body);
  let out = previous;
  for (const block of patchBlocks) {
    const spans = [...out.matchAll(headingRe)];
    const foundIndex = spans.findIndex((m) => Number.parseInt(m[1], 10) === block.label);
    if (foundIndex < 0) {
      out = mergeFileBody(out, block.text);
      continue;
    }
    const start = spans[foundIndex].index ?? 0;
    const end = foundIndex + 1 < spans.length ? spans[foundIndex + 1].index ?? out.length : out.length;
    out = `${out.slice(0, start)}${block.text}\n\n${out.slice(end).replace(/^\n+/, "")}`;
  }
  return out;
}

export function removeEpisodeBlocks(previous: string, from: number, to: number, unit = "集"): string {
  const headingRe = new RegExp(`^\\s*(?:#{1,4}\\s*)?[*_\`]{0,3}\\s*第\\s*(\\d+)\\s*${unit}[*_\`]{0,3}[^\\n]*`, "gmu");
  const matches = [...previous.matchAll(headingRe)];
  if (!matches.length) return previous;
  const cuts: Array<[number, number]> = [];
  for (let index = 0; index < matches.length; index += 1) {
    const label = Number.parseInt(matches[index][1], 10);
    if (!Number.isFinite(label) || label < from || label > to) continue;
    const start = matches[index].index ?? 0;
    const end = index + 1 < matches.length ? matches[index + 1].index ?? previous.length : previous.length;
    cuts.push([start, end]);
  }
  if (!cuts.length) return previous;
  let out = "";
  let cursor = 0;
  for (const [start, end] of cuts) {
    out += previous.slice(cursor, start);
    cursor = end;
  }
  out += previous.slice(cursor);
  return out.replace(/\n{3,}/g, "\n\n");
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
