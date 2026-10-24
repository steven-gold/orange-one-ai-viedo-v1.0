import {
  completedRun,
  failedRun,
  pendingRun,
  PUBLIC_JSON_SOURCES,
  sourceRecordFrom,
  type AcquisitionResultItem,
  type AcquisitionRun,
  type AcquisitionSourceRecord,
} from "./sharedAcquisition";
import {
  KB_ACQ_MODE_UID,
  KB_RESULTS_UID,
  KB_RUN_FAIL_UID,
  KB_RUN_ID_UID,
  KB_RUN_PROGRESS_UID,
  KB_RUN_STATUS_UID,
  KB_RUN_UID,
  KB_SOURCE_CLASS_UID,
  KB_SOURCE_NAME_UID,
  KB_SOURCE_RIGHTS_UID,
  KB_SOURCE_SCOPE_UID,
  KB_SOURCE_STATUS_UID,
  KB_SOURCE_TYPE_UID,
  KB_SOURCES_UID,
} from "./kbState";
import { parseJson } from "./devState";

function serialize(value: unknown): string {
  return JSON.stringify(value);
}

function patchSource(source: AcquisitionSourceRecord, run: AcquisitionRun, results: AcquisitionResultItem[] = []): Record<string, string> {
  return {
    [KB_SOURCE_NAME_UID]: source.name,
    [KB_SOURCE_TYPE_UID]: source.type,
    [KB_SOURCE_SCOPE_UID]: source.scope,
    [KB_SOURCE_RIGHTS_UID]: source.rights,
    [KB_SOURCE_CLASS_UID]: source.classification,
    [KB_ACQ_MODE_UID]: source.acquisitionMode,
    [KB_SOURCE_STATUS_UID]: source.status === "ACTIVE" ? "可用" : "無法使用",
    [KB_RUN_ID_UID]: run.runId,
    [KB_RUN_STATUS_UID]: run.status === "COMPLETE" ? "完成" : run.status === "RUNNING" ? "執行中" : "外部待處理",
    [KB_RUN_PROGRESS_UID]: run.progress,
    [KB_RUN_FAIL_UID]: run.failure,
    [KB_SOURCES_UID]: serialize([source]),
    [KB_RESULTS_UID]: serialize(results),
    [KB_RUN_UID]: serialize(run),
  };
}

export function previewKbAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  _nextValue?: string,
): Record<string, string> {
  const source = PUBLIC_JSON_SOURCES[0];
  const existing = parseJson<AcquisitionSourceRecord[]>(current(KB_SOURCES_UID), []);
  if (actionUid === "createKnowledgeSource" || actionUid === "updateKnowledgeSource") {
    const record = existing[0] ?? sourceRecordFrom(source, "ACTIVE");
    const run = parseJson<AcquisitionRun | null>(current(KB_RUN_UID), null) ?? pendingRun(record.sourceId);
    return patchSource(record, run, parseJson<AcquisitionResultItem[]>(current(KB_RESULTS_UID), []));
  }
  if (actionUid === "createAcquisitionJob") {
    const record = existing[0] ?? sourceRecordFrom(source, "ACTIVE");
    return patchSource(record, pendingRun(record.sourceId));
  }
  void controlUid;
  return {};
}

export function kbAcquisitionPatchFromCollect(result: {
  ok: boolean;
  source: AcquisitionSourceRecord;
  run: AcquisitionRun;
  items?: AcquisitionResultItem[];
  reason?: string;
}): Record<string, string> {
  if (!result.ok) {
    return patchSource(result.source, result.run.status === "EXTERNAL_PENDING" ? result.run : failedRun(result.source.sourceId, result.reason || "SHARED_ACQUISITION_UNAVAILABLE"));
  }
  return patchSource(result.source, result.run.status === "COMPLETE" ? result.run : completedRun(result.source.sourceId, result.items?.length ?? 0), result.items ?? []);
}
