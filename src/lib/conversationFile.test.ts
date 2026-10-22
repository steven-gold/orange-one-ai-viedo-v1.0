import { buildTaskContract, updateContractAfterGeneration } from "./conversationTask";
import { attachFileToContract, buildConversationFile, mergeFileBody } from "./conversationFile";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

const SERIES = "我想用天堂網路遊戲參考，以80年代的網路遊戲瘋狂時代，製作一份新的故事大約500集每集2分鐘的搞笑影片。";

{
  const contract = updateContractAfterGeneration(buildTaskContract(SERIES, null, "對話 1"), "第1集……", {
    truncated: false,
    loop: false,
  });
  const file = buildConversationFile("ACC-DEMO", "core", contract, "第1集正文\n\n狀態：部分完成");
  assert(file, "large task writes a file");
  assertEqual(file?.fileName, "500集分集影片故事大綱.txt", "file name");
  assertEqual(file?.body, "第1集正文", "footer stripped from file body");
  assertEqual(file?.mimeType, "text/plain; charset=utf-8", "plain text");
  const bound = attachFileToContract(contract, file);
  assertEqual(bound.fileId, file?.fileUid, "contract keeps file id");
  assertEqual(bound.fileName, file?.fileName, "contract keeps file name");
}

{
  const first = mergeFileBody("第1–20集\nA", "第21–40集\nB");
  assertEqual(first, "第1–20集\nA\n\n第21–40集\nB", "append next batch");
  const overlap = mergeFileBody("前文尾段這是一段足夠長的重疊內容ABC", "這是一段足夠長的重疊內容ABC後文");
  assertEqual(overlap, "前文尾段這是一段足夠長的重疊內容ABC後文", "overlap merge");
}

{
  const short = buildTaskContract("簡單問題？");
  assertEqual(buildConversationFile("ACC-DEMO", "core", short, "答案。"), null, "short answers stay in chat");
}

console.log("conversationFile.test.ts PASS");
