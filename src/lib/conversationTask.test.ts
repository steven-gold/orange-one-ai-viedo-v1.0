import {
  LARGE_TASK_BATCH_ITEMS,
  buildTaskContract,
  claimsFullCompletion,
  classifyTaskKind,
  completedCount,
  detectGenerationLoop,
  formatContractForPrompt,
  fileNameForContract,
  formatDeliveryFooter,
  inferTruncated,
  parseConversationFileRef,
  stripDeliveryFooter,
  isContinueRequest,
  latestOpenTask,
  mergeContinuation,
  planQuantityBatches,
  splitDeliverableChunks,
  updateContractAfterGeneration,
} from "./conversationTask";

const SERIES =
  "我想用天堂網路遊戲參考，以80年代的網路遊戲瘋狂時代，製作一份新的故事大約500集每集2分鐘的搞笑影片。";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

{
  assertEqual(classifyTaskKind(SERIES), "large", "500-episode case is large");
  const contract = buildTaskContract(SERIES, null, "對話 1");
  assertEqual(contract.kind, "large", "contract kind");
  assertEqual(contract.quantity?.count, 500, "quantity count");
  assertEqual(contract.quantity?.unit, "集", "quantity unit");
  assertEqual(contract.duration, "每集2分鐘", "duration");
  assert(contract.constraints.some((row) => row.includes("搞笑")), "keep funny tone");
  assert(contract.constraints.some((row) => row.includes("80年代")), "keep era");
  assert(contract.constraints.some((row) => row.includes("靈感")), "treat 天堂 as inspiration");
  assert(contract.forbidden.some((row) => row.includes("受眾")), "do not invent audience");
  assert(contract.forbidden.some((row) => row.includes("通用製作建議")), "do not answer with generic advice");
  assertEqual(contract.batched, true, "batched");
  assertEqual(contract.needsFile, true, "large task needs file");
  assertEqual(fileNameForContract(contract), "500集分集影片故事大綱.txt", "deliverable file name");
  assertEqual(contract.nextBatch, `第1–${LARGE_TASK_BATCH_ITEMS}集`, "first batch");
  assert(contract.pendingItems.includes("第21–500集") || contract.pendingItems.some((row) => row.includes("500")), "remaining range");
  const prompt = formatContractForPrompt(contract);
  assert(prompt.includes("500集"), "prompt keeps 500");
  assert(prompt.includes("本批次"), "prompt scopes the batch");
  assert(prompt.includes("禁止宣稱全部完成"), "prompt forbids false complete");
}

{
  const prior = buildTaskContract(SERIES, null, "對話 1");
  const changed = buildTaskContract("改成大約300集，其他條件不變。", prior, "對話 1");
  assertEqual(changed.quantity?.count, 300, "later quantity override");
  assertEqual(changed.duration, "每集2分鐘", "duration survives partial rewrite");
  assert(changed.constraints.some((row) => row.includes("搞笑")), "tone survives");
  assertEqual(changed.taskId, prior.taskId, "same task identity");
}

{
  const prior = buildTaskContract(SERIES, null, "對話 1");
  const continued = buildTaskContract("繼續寫", prior, "對話 1");
  assertEqual(isContinueRequest("繼續寫"), true, "continue detector");
  assertEqual(continued.taskId, prior.taskId, "continue keeps task");
  assertEqual(continued.quantity?.count, 500, "continue keeps 500");
}

{
  const planned = planQuantityBatches({ count: 500, unit: "集" }, 20, 20);
  assertEqual(planned.nextBatch, "第21–40集", "second batch");
  assertEqual(completedCount({ ...buildTaskContract(SERIES), completedItems: ["第1–20集"] }), 20, "completedCount");
}

{
  const contract = buildTaskContract(SERIES);
  const after = updateContractAfterGeneration(contract, "第1集……", { truncated: false, loop: false });
  assertEqual(after.status, "PARTIAL", "one batch is not complete");
  assert(after.pendingItems.length > 0, "pending remains");
  assertEqual(claimsFullCompletion("500集已全部完成", contract), true, "false complete detector");
}

{
  const loop = detectGenerationLoop("哈哈。哈哈。哈哈。哈哈。哈哈。哈哈。哈哈。哈哈。");
  assertEqual(loop.loop, true, "sentence loop");
  const ok = detectGenerationLoop("第一集介紹角色。第二集進入網咖。第三集遇見對手。");
  assertEqual(ok.loop, false, "normal prose is not a loop");
}

{
  assertEqual(inferTruncated("第12集", "stop"), true, "hanging episode heading is truncated");
  assertEqual(inferTruncated("完整一句。", "stop"), false, "stopped complete sentence");
  assertEqual(inferTruncated("內容", "length"), true, "finish_reason length");
}

{
  const merged = mergeContinuation("前文尾段ABC", "ABC後文");
  assertEqual(merged, "前文尾段ABC後文", "overlap merge");
  const chunks = splitDeliverableChunks("AAAA\nBBBB\nCCCC", 6);
  assert(chunks.length >= 2, "chunk split");
  assert(chunks.every((row) => row.length <= 6), "chunk size");
}

{
  const first = buildTaskContract("簡單問題？");
  assertEqual(first.kind, "question", "short question");
  const after = updateContractAfterGeneration(first, "答案。", { truncated: false, loop: false });
  assertEqual(after.status, "COMPLETE", "short answer complete");
  assertEqual(formatDeliveryFooter(after), "", "short answers stay in chat without footer");
}

{
  const tasks = [buildTaskContract(SERIES, null, "對話 1")];
  const open = latestOpenTask(tasks, "對話 1");
  assert(open, "latest open");
}

{
  const contract = buildTaskContract(SERIES);
  const after = updateContractAfterGeneration(contract, "第1集……", { truncated: false, loop: false });
  const withFile = { ...after, fileId: "FILE-ab12cd34", fileName: fileNameForContract(after) };
  const footer = formatDeliveryFooter(withFile);
  assert(footer.includes("成品：500集分集影片故事大綱.txt"), "footer names the file");
  assert(footer.includes("檔案：FILE-ab12cd34"), "footer keeps file id");
  const packed = `第1集正文\n\n${footer}`;
  assertEqual(stripDeliveryFooter(packed), "第1集正文", "strip footer before file persist");
  const parsed = parseConversationFileRef(packed);
  assertEqual(parsed?.fileId, "FILE-ab12cd34", "parse file id");
  assertEqual(parsed?.fileName, "500集分集影片故事大綱.txt", "parse file name");
}

console.log("conversationTask.test.ts PASS");
