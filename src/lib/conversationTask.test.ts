import {
  LARGE_TASK_BATCH_ITEMS,
  STREAM_LOOP_CHECK_EVERY_CHARS,
  STREAM_LOOP_CHECK_MIN_CHARS,
  annotateUnverifiedClaims,
  consumeGenerationStream,
  encodeGenerationSse,
  diagnoseGenerationFailure,
  generationStatusKey,
  generationStatusLabel,
  isConversationGeneratingAction,
  parseGenerationSseFrame,
  buildTaskContract,
  claimsFullCompletion,
  classifyTaskKind,
  completedCount,
  detectGenerationLoop,
  detectUnusableOutput,
  batchLooksDelivered,
  formatContractForPrompt,
  modelBlockedForLanguage,
  fileNameForContract,
  formatDeliveryFooter,
  inferTruncated,
  parseConversationFileRef,
  parseOpenAiSseFrame,
  shouldCheckStreamLoop,
  splitSseFrames,
  stripDeliveryFooter,
  isContinueRequest,
  latestOpenTask,
  mergeContinuation,
  planQuantityBatches,
  splitDeliverableChunks,
  unverifiedExecutionClaims,
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
  assert(prompt.includes("目標："), "prompt keeps the goal");
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
  assertEqual(isContinueRequest("我要每一章節名稱與內容"), true, "catalog continue");
  assertEqual(continued.taskId, prior.taskId, "continue keeps task");
  assertEqual(continued.quantity?.count, 500, "continue keeps 500");
  const advanced = { ...prior, completedItems: ["第1–20集"] };
  const catalog = buildTaskContract("我要每一章節名稱與內容", advanced, "對話 1");
  assertEqual(catalog.nextBatch, "第1–20集", "catalog restarts first batch");
  assertEqual(catalog.completedItems.length, 0, "catalog does not keep false complete");
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
  assertEqual(after.completedItems.length, 0, "thin output does not complete a batch");
  assertEqual(claimsFullCompletion("500集已全部完成", contract), true, "false complete detector");
  const delivered = "第1集 開場。第2集 進網咖。第3集 遇見對手。";
  assertEqual(batchLooksDelivered(delivered, contract), true, "episode headings look delivered");
  const done = updateContractAfterGeneration(contract, delivered, { truncated: false, loop: false });
  assertEqual(done.completedItems[0], "第1–20集", "delivered batch advances");
  const garbage = "第1–20篇".repeat(8);
  assertEqual(detectUnusableOutput(garbage), true, "repeated batch label is unusable");
  const failed = updateContractAfterGeneration(contract, garbage, { truncated: false, loop: false });
  assertEqual(failed.status, "FAILED", "unusable stays failed");
  assertEqual(failed.completedItems.length, 0, "unusable does not complete batch");
  assertEqual(modelBlockedForLanguage("allam-2-7b", "zh-TW"), true, "skip allam for zh-TW");
  assertEqual(modelBlockedForLanguage("gemini-2.5-flash", "zh-TW"), false, "keep gemini");
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
  const contract = buildTaskContract(SERIES, null, "對話 1");
  const after = updateContractAfterGeneration(contract, "第1集開頭", { truncated: true, loop: false, stopped: true });
  assertEqual(after.status, "STOPPED", "stopped status");
  assertEqual(latestOpenTask([after], "對話 1")?.status, "STOPPED", "stopped remains continuable");
  const footer = formatDeliveryFooter(after);
  assert(footer.includes("已停止"), "footer stopped label");
  assert(footer.includes("可續寫"), "stopped can continue");
  assertEqual(inferTruncated("有效前綴", "cancelled"), true, "cancelled is truncated");
}

{
  assertEqual(classifyTaskKind(""), "insufficient", "empty is insufficient");
  assertEqual(classifyTaskKind("什麼是 Canonical Script？"), "knowledge", "knowledge question");
  assertEqual(classifyTaskKind("比較這兩版腳本的風險"), "analysis", "analysis intent");
  assertEqual(classifyTaskKind("修 bug 這個 function"), "code", "code intent");
  assertEqual(classifyTaskKind("寫一份兩分鐘搞笑短片大綱"), "creation", "creation intent");
  assertEqual(classifyTaskKind("執行刪除這筆付款紀錄"), "system", "system side-effect intent");
}

{
  const split = splitSseFrames('data: {"choices":[{"delta":{"content":"第"}}]}\n\ndata: {"choices":[{"delta":{"content":"一集"}}]}\n\npartial');
  assertEqual(split.frames.length, 2, "two sse frames");
  assertEqual(split.rest, "partial", "keep incomplete frame");
  const first = parseOpenAiSseFrame(split.frames[0]);
  assertEqual(first.delta, "第", "keep untrimmed delta");
  const done = parseOpenAiSseFrame("[DONE]");
  assertEqual(done.done, true, "done frame");
  assertEqual(shouldCheckStreamLoop(STREAM_LOOP_CHECK_MIN_CHARS - 1, 0), false, "below min");
  assertEqual(shouldCheckStreamLoop(STREAM_LOOP_CHECK_MIN_CHARS, 0), true, "at min");
  assertEqual(shouldCheckStreamLoop(STREAM_LOOP_CHECK_MIN_CHARS + STREAM_LOOP_CHECK_EVERY_CHARS - 1, STREAM_LOOP_CHECK_MIN_CHARS), false, "inside interval");
  assertEqual(inferTruncated("有效前綴", "loop_stopped"), true, "stream loop is truncated");
}

{
  const encoded = `${encodeGenerationSse({ type: "token", text: "第" })}${encodeGenerationSse({ type: "status", status: "STOPPED" })}${encodeGenerationSse({ type: "done" })}partial`;
  const split = splitSseFrames(encoded);
  assertEqual(split.frames.length, 3, "generation sse frames");
  assertEqual(split.rest, "partial", "keep incomplete generation frame");
  const token = parseGenerationSseFrame(split.frames[0]);
  const status = parseGenerationSseFrame(split.frames[1]);
  const done = parseGenerationSseFrame(split.frames[2]);
  assertEqual(token?.type, "token", "token event");
  assertEqual(token && token.type === "token" ? token.text : "", "第", "keep token text");
  assertEqual(status?.type, "status", "status event");
  assertEqual(status && status.type === "status" ? status.status : "", "STOPPED", "stopped status event");
  assertEqual(done?.type, "done", "done event");
  assertEqual(parseGenerationSseFrame("not-json"), null, "reject provider sse as generation event");
  const aliased = parseGenerationSseFrame(JSON.stringify({ type: "token", text: "甲", alias: "A" }));
  assertEqual(aliased && aliased.type === "token" ? aliased.alias : "", "A", "token alias");
}

async function testConsumeGenerationStream(): Promise<void> {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      const encoded = `${encodeGenerationSse({ type: "token", text: "甲" })}${encodeGenerationSse({ type: "status", status: "PARTIAL" })}${encodeGenerationSse({ type: "done" })}`;
      controller.enqueue(new TextEncoder().encode(encoded));
      controller.close();
    },
  });
  const tokens: string[] = [];
  const statuses: string[] = [];
  await consumeGenerationStream(body, {
    token: (text) => tokens.push(text),
    status: (status) => statuses.push(status),
  });
  assertEqual(tokens.join(""), "甲", "consume token");
  assertEqual(statuses.join(""), "PARTIAL", "consume status");

  const failed: string[] = [];
  await consumeGenerationStream(
    new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(encodeGenerationSse({ type: "token", text: "乙" })));
        controller.close();
      },
    }),
    {
      token: () => undefined,
      status: (status) => failed.push(status),
    },
  );
  assertEqual(failed.join(""), "FAILED", "unterminated stream is failed");
}

{
  assertEqual(isConversationGeneratingAction("CORE-01-ACT-SEND"), true, "send streams");
  assertEqual(isConversationGeneratingAction("CORE-01-ACT-MSG-ANALYZE"), true, "analyze streams");
  assertEqual(isConversationGeneratingAction("CORE-01-ACT-MSG-QUOTE"), false, "quote stays json");
  assertEqual(generationStatusLabel("STOPPED"), "已停止", "status label stopped");
  assertEqual(generationStatusLabel("PARTIAL"), "部分完成", "status label partial");
  assertEqual(generationStatusLabel("OPEN"), "進行中", "status label open");
  assertEqual(generationStatusLabel("COMPLETE"), "已完成", "status label complete");
  assertEqual(generationStatusLabel("FAILED"), "失敗", "status label failed");
  assertEqual(generationStatusKey("OPEN"), "conversation.stream.status.open", "status key open");
  assertEqual(generationStatusKey("FAILED"), "conversation.stream.status.failed", "status key failed");
  assertEqual(diagnoseGenerationFailure({ failed: true, empty: true }), "空回應", "empty fail");
  assertEqual(diagnoseGenerationFailure({ providerCode: "AI_PROVIDER_TIMEOUT" }), "供應商逾時", "timeout fail");
  assertEqual(diagnoseGenerationFailure({ providerCode: "AI_PROVIDER_UNREACHABLE" }), "供應商無法連線", "unreachable fail");
  assertEqual(diagnoseGenerationFailure({ providerCode: "AI_PROVIDER_HTTP_ERROR" }), "供應商無法連線", "http fail");
  assertEqual(diagnoseGenerationFailure({ providerCode: "AI_PROVIDER_EMPTY_RESPONSE" }), "空回應", "empty response code");
  assertEqual(diagnoseGenerationFailure({ providerCode: "AI_PROVIDER_MULTI_SHORT" }), "Multi 路由未滿 3 條", "multi short");
  assertEqual(diagnoseGenerationFailure({ providerCode: "AI_PROVIDER_NOT_CONFIGURED" }), "供應商未設定或暫時無法使用", "not configured");
  assertEqual(diagnoseGenerationFailure({ providerCode: "AI_PROVIDER_UNUSABLE_OUTPUT" }), "輸出無法使用", "unusable output");
}

{
  assertEqual(unverifiedExecutionClaims("已成功部署到正式站").includes("deploy"), true, "deploy claim");
  assertEqual(unverifiedExecutionClaims("已刪除該檔案").includes("side_effect"), true, "delete claim");
  assertEqual(unverifiedExecutionClaims("已成功建立檔案").includes("file"), true, "unverified file claim");
  assertEqual(unverifiedExecutionClaims("已成功建立檔案", { fileWritten: true }).includes("file"), false, "verified file claim");
  const annotated = annotateUnverifiedClaims("已成功部署到正式站", ["deploy"]);
  assert(annotated.includes("尚未驗證"), "annotate unverified");
  assertEqual(annotateUnverifiedClaims("普通回答。", []), "普通回答。", "no annotation when clean");
}

{
  const contract = buildTaskContract(SERIES);
  const after = updateContractAfterGeneration(contract, "第1集……", { truncated: false, loop: false });
  const withFile = { ...after, fileId: "FILE-ab12cd34", fileName: fileNameForContract(after) };
  const footer = formatDeliveryFooter({
    ...withFile,
    observation: { chars: 12, durationMs: 1500, loop: false, truncated: false, failReason: "" },
  });
  assert(footer.includes("成品：500集分集影片故事大綱.txt"), "footer names the file");
  assert(footer.includes("檔案：FILE-ab12cd34"), "footer keeps file id");
  assert(footer.includes("觀測：字數 12；耗時 1.5 秒"), "footer keeps observation");
  const packed = `第1集正文\n\n${footer}`;
  assertEqual(stripDeliveryFooter(packed), "第1集正文", "strip footer before file persist");
  const withClaim = annotateUnverifiedClaims(`第1集正文\n\n${footer}`, ["deploy"]);
  assertEqual(stripDeliveryFooter(withClaim), "第1集正文", "strip unverified claim before file persist");
  const parsed = parseConversationFileRef(packed);
  assertEqual(parsed?.fileId, "FILE-ab12cd34", "parse file id");
  assertEqual(parsed?.fileName, "500集分集影片故事大綱.txt", "parse file name");
}

testConsumeGenerationStream()
  .then(() => {
    console.log("conversationTask.test.ts PASS");
  })
  .catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
