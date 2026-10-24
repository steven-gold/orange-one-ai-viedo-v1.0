import { kbAcquisitionPatchFromCollect, previewKbAction } from "./kbActionPreview";
import { completedRun, failedRun, sourceRecordFrom, PUBLIC_JSON_SOURCES } from "./sharedAcquisition";
import { KB_RESULTS_UID, KB_RUN_FAIL_UID, KB_RUN_ID_UID, KB_RUN_STATUS_UID, KB_SOURCE_NAME_UID, KB_SOURCE_STATUS_UID } from "./kbState";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

{
  const values = new Map<string, string>();
  const current = (uid: string) => values.get(uid) ?? null;
  const patch = previewKbAction("CTRL-ADMIN-KB-01-ACT-INGEST-START", "createAcquisitionJob", current);
  assert(patch[KB_SOURCE_NAME_UID] === "臺灣證券交易所上市基本資料", "ingest binds the allowed public JSON source");
  assert(patch[KB_SOURCE_STATUS_UID] === "可用", "ingest records source intent as available before fetch");
  assert(Boolean(patch[KB_RUN_ID_UID]), "ingest writes a run id");
}

{
  const patch = previewKbAction("CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE", "createKnowledgeSource", () => null);
  assert(patch[KB_SOURCE_NAME_UID].includes("臺灣證券交易所"), "source create reuses shared acquisition source");
}

{
  const source = sourceRecordFrom(PUBLIC_JSON_SOURCES[0], "ACTIVE");
  const ok = kbAcquisitionPatchFromCollect({
    ok: true,
    source,
    run: completedRun(source.sourceId, 1),
    items: [{ title: "中華電視股份有限公司", type: "市場訊號", source: source.name, freshness: "2026-10-24", identityValue: "TW-03793901" }],
  });
  assert(ok[KB_RUN_STATUS_UID] === "完成", "successful collect marks run complete");
  assert(JSON.parse(ok[KB_RESULTS_UID]).length === 1, "successful collect writes result items");
  const blocked = kbAcquisitionPatchFromCollect({
    ok: false,
    source: sourceRecordFrom(PUBLIC_JSON_SOURCES[0], "UNAVAILABLE"),
    run: failedRun(PUBLIC_JSON_SOURCES[0].sourceId, "SHARED_ACQUISITION_UNAVAILABLE"),
    reason: "SHARED_ACQUISITION_UNAVAILABLE",
  });
  assert(blocked[KB_SOURCE_STATUS_UID] === "無法使用", "failed collect marks source unavailable");
  assert(blocked[KB_RUN_FAIL_UID] === "SHARED_ACQUISITION_UNAVAILABLE", "failed collect records blocker");
}

console.log("kbActionPreview.test.ts PASS");
