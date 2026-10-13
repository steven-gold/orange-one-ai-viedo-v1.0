import { namedValue, parseThreadList, statusFromAction } from "./coreActionPreview";

export { parseThreadList };

export function usableList(raw: string | null): string[] {
  return parseThreadList(raw).filter((item) => Boolean(namedValue(item, "")));
}

function named(value: string | null | undefined): string {
  return namedValue(value ?? undefined, "") ? String(value).trim() : "";
}

function keepName(nextValue: string | undefined, currentValue: string | null, fallback: string): string {
  return namedValue(nextValue, named(currentValue) || fallback);
}

function toggleMode(current: string | null): string {
  return current === "MANUAL" ? "AUTO" : "MANUAL";
}

function nextFilter(current: string | null): string {
  const order = ["ALL", "REQUIRED", "REUSE", "MISSING", "DEFERRED"];
  const index = order.indexOf(current ?? "ALL");
  return order[(index + 1) % order.length];
}

function nextZoom(actionUid: string, current: string | null): string {
  const raw = Number.parseInt(String(current ?? "100").replace("%", ""), 10);
  const base = Number.isFinite(raw) ? raw : 100;
  if (actionUid.endsWith("ZOOM-IN")) return `${Math.min(base + 25, 200)}%`;
  if (actionUid.endsWith("ZOOM-OUT")) return `${Math.max(base - 25, 50)}%`;
  return "100%";
}

function inboundReady(current: (uid: string) => string | null): boolean {
  return Boolean(
    named(current("ASSET-01-CTL-PROJECT")) &&
      named(current("ASSET-01-CTL-TOPIC")) &&
      named(current("ASSET-01-FLD-BLUEPRINT")) &&
      named(current("ASSET-01-FLD-DNA")) &&
      named(current("ASSET-01-FLD-SCRIPT")),
  );
}

export function previewAssetAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const project = named(current("ASSET-01-CTL-PROJECT"));
  const topic = named(current("ASSET-01-CTL-TOPIC"));
  const assets = usableList(current("ASSET-01-LST-ASSET"));
  const ready = inboundReady(current);
  const gated = new Set([
    "ASSET-01-ACT-FLOW-START",
    "ASSET-01-ACT-ASSET-SEARCH",
    "ASSET-01-ACT-ASSET-FILTER",
    "ASSET-01-ACT-ASSET-SELECT",
    "ASSET-01-ACT-COMPARE-SINGLE",
    "ASSET-01-ACT-COMPARE-AB",
    "ASSET-01-ACT-COMPARE-ABC",
    "ASSET-01-ACT-ZOOM-IN",
    "ASSET-01-ACT-ZOOM-OUT",
    "ASSET-01-ACT-FIT",
    "ASSET-01-ACT-REFERENCE-TOGGLE",
    "ASSET-01-ACT-RESULT-VIEW",
    "ASSET-01-ACT-CORRECTION-OPEN",
    "ASSET-01-ACT-CORRECTION-GENERATE",
    "ASSET-01-ACT-CORRECTION-APPROVE",
    "ASSET-01-ACT-CORRECTION-EXECUTE",
    "ASSET-01-ACT-LAYER-DOC-CREATE",
    "ASSET-01-ACT-LAYER-DOC-UPDATE",
    "ASSET-01-ACT-LAYER-ADD",
    "ASSET-01-ACT-LAYER-DELETE",
    "ASSET-01-ACT-LAYER-DUPLICATE",
    "ASSET-01-ACT-LAYER-REORDER",
    "ASSET-01-ACT-LAYER-PROPERTIES",
    "ASSET-01-ACT-LAYER-MASK",
    "ASSET-01-ACT-PATCH-CREATE",
    "ASSET-01-ACT-PATCH-PREVIEW",
    "ASSET-01-ACT-PATCH-ACCEPT",
    "ASSET-01-ACT-PATCH-REJECT",
    "ASSET-01-ACT-PATCH-REVISE",
    "ASSET-01-ACT-RUNTIME-VIEW",
    "ASSET-01-ACT-TASK-RETRY",
    "ASSET-01-ACT-EVALUATE",
    "ASSET-01-ACT-CANDIDATE-CONFIRM",
    "ASSET-01-ACT-VERSION-HISTORY",
    "ASSET-01-ACT-RESTORE-AS-NEW",
    "ASSET-01-ACT-VERSION-LOCK",
    "ASSET-01-ACT-HANDOFF",
  ]);
  if (!ready && gated.has(actionUid)) return {};

  if (actionUid === "ASSET-01-ACT-PROJECT-SELECT") {
    return project ? { "ASSET-01-CTL-PROJECT": project } : {};
  }
  if (actionUid === "ASSET-01-ACT-TOPIC-SELECT") {
    return topic ? { "ASSET-01-CTL-TOPIC": topic } : {};
  }
  if (actionUid === "ASSET-01-ACT-MODE-SET") {
    if (!ready) return {};
    return { "ASSET-01-CTL-MODE": toggleMode(current("ASSET-01-CTL-MODE")) };
  }
  if (actionUid === "ASSET-01-ACT-FLOW-START") {
    if (!ready) return {};
    const selected = named(current("ASSET-01-FLD-MANIFEST")) || assets[assets.length - 1] || "";
    return {
      "ASSET-01-BTN-EXECUTE": "running",
      "ASSET-01-FLD-TASK": named(current("ASSET-01-FLD-TASK")) || `${project} / ${topic}`,
      "ASSET-01-FLD-TASK-STATUS": "running",
      "ASSET-01-FLD-STAGE": "running",
      "ASSET-01-CTL-PROJECT": project,
      "ASSET-01-CTL-TOPIC": topic,
      ...(selected ? { "ASSET-01-FLD-MANIFEST": selected } : {}),
      "ASSET-01-FLD-JOB": "running",
      "ASSET-01-FLD-ROUTE": "ready",
    };
  }
  if (actionUid === "ASSET-01-ACT-ASSET-SEARCH") {
    if (!ready) return {};
    return { "ASSET-01-FLD-SEARCH": keepName(nextValue, current("ASSET-01-FLD-SEARCH"), "搜尋") };
  }
  if (actionUid === "ASSET-01-ACT-ASSET-FILTER") {
    if (!ready) return {};
    return { "ASSET-01-CTL-FILTER": nextFilter(current("ASSET-01-CTL-FILTER")) };
  }
  if (actionUid === "ASSET-01-ACT-ASSET-SELECT") {
    if (!ready) return {};
    const title = keepName(nextValue, current("ASSET-01-FLD-MANIFEST"), `素材 ${assets.length + 1}`);
    const nextList = assets.includes(title) ? assets : [...assets, title];
    return {
      "ASSET-01-LST-ASSET": JSON.stringify(nextList),
      "ASSET-01-FLD-MANIFEST": title,
      "ASSET-01-FLD-CANONICAL-FILENAME": `${title}.png`,
    };
  }
  if (actionUid === "ASSET-01-ACT-COMPARE-SINGLE") {
    return {
      "ASSET-01-BTN-SINGLE": "active",
      "ASSET-01-BTN-AB": "idle",
      "ASSET-01-BTN-ABC": "idle",
      "ASSET-01-LST-COMPARE-VERSIONS": keepName(nextValue, current("ASSET-01-FLD-MANIFEST"), "單張"),
    };
  }
  if (actionUid === "ASSET-01-ACT-COMPARE-AB") {
    return {
      "ASSET-01-BTN-AB": "active",
      "ASSET-01-BTN-SINGLE": "idle",
      "ASSET-01-BTN-ABC": "idle",
      "ASSET-01-LST-COMPARE-VERSIONS": "A/B",
    };
  }
  if (actionUid === "ASSET-01-ACT-COMPARE-ABC") {
    return {
      "ASSET-01-BTN-ABC": "active",
      "ASSET-01-BTN-SINGLE": "idle",
      "ASSET-01-BTN-AB": "idle",
      "ASSET-01-LST-COMPARE-VERSIONS": "A/B/C",
    };
  }
  if (actionUid === "ASSET-01-ACT-ZOOM-IN" || actionUid === "ASSET-01-ACT-ZOOM-OUT" || actionUid === "ASSET-01-ACT-FIT") {
    return { "ASSET-01-BTN-FIT": nextZoom(actionUid, current("ASSET-01-BTN-FIT")) };
  }
  if (actionUid === "ASSET-01-ACT-REFERENCE-TOGGLE") {
    return { "ASSET-01-BTN-REFERENCE": current("ASSET-01-BTN-REFERENCE") === "attached" ? "idle" : "attached" };
  }
  if (actionUid === "ASSET-01-ACT-RESULT-VIEW") {
    return {
      [controlUid]: keepName(nextValue, current(controlUid), current("ASSET-01-FLD-OVERALL") || "已評估"),
      "ASSET-01-FLD-OVERALL": keepName(undefined, current("ASSET-01-FLD-OVERALL"), "已評估"),
    };
  }
  if (actionUid === "ASSET-01-ACT-BLUEPRINT-VIEW") {
    const blueprint = named(current("ASSET-01-FLD-BLUEPRINT"));
    return blueprint ? { "ASSET-01-FLD-BLUEPRINT": blueprint } : {};
  }
  if (actionUid === "ASSET-01-ACT-SCRIPT-VIEW") {
    const script = named(current("ASSET-01-FLD-SCRIPT"));
    return script ? { "ASSET-01-FLD-SCRIPT": script } : {};
  }
  if (actionUid === "ASSET-01-ACT-CORRECTION-OPEN") {
    return {
      "ASSET-01-BTN-CORRECTION-OPEN": "open",
      "ASSET-01-TXT-CORRECTION-REQUEST": keepName(nextValue, current("ASSET-01-TXT-CORRECTION-REQUEST"), "請修正此素材"),
    };
  }
  if (actionUid === "ASSET-01-ACT-CORRECTION-GENERATE") {
    return {
      "ASSET-01-BTN-CORRECTION-GENERATE": "created",
      "ASSET-01-TXT-CORRECTION-REQUEST": keepName(nextValue, current("ASSET-01-TXT-CORRECTION-REQUEST"), "請修正此素材"),
    };
  }
  if (actionUid === "ASSET-01-ACT-CORRECTION-APPROVE") {
    return { "ASSET-01-BTN-CORRECTION-APPROVE": "approved" };
  }
  if (actionUid === "ASSET-01-ACT-CORRECTION-EXECUTE") {
    return {
      "ASSET-01-BTN-CORRECTION-EXECUTE": "running",
      "ASSET-01-FLD-TASK-STATUS": "running",
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DOC-CREATE") {
    return { "ASSET-01-BTN-LAYER-DOC-CREATE": keepName(nextValue, current("ASSET-01-BTN-LAYER-DOC-CREATE"), "圖層文件") };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DOC-UPDATE") {
    return { "ASSET-01-BTN-LAYER-DOC-UPDATE": "saved" };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-ADD") {
    const layers = usableList(current("ASSET-01-BTN-LAYER-ADD"));
    const title = keepName(nextValue, current("ASSET-01-CTL-LAYER-PROPERTIES"), `圖層 ${layers.length + 1}`);
    const nextList = [...layers, title];
    return {
      "ASSET-01-BTN-LAYER-ADD": JSON.stringify(nextList),
      "ASSET-01-CTL-LAYER-PROPERTIES": title,
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DELETE") {
    const layers = usableList(current("ASSET-01-BTN-LAYER-ADD"));
    const nextList = layers.slice(0, -1);
    return {
      "ASSET-01-BTN-LAYER-ADD": JSON.stringify(nextList),
      "ASSET-01-CTL-LAYER-PROPERTIES": nextList[nextList.length - 1] ?? "",
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DUPLICATE") {
    const layers = usableList(current("ASSET-01-BTN-LAYER-ADD"));
    const source = named(current("ASSET-01-CTL-LAYER-PROPERTIES")) || layers[layers.length - 1] || "圖層 1";
    const copy = `${source} 副本`;
    return {
      "ASSET-01-BTN-LAYER-ADD": JSON.stringify([...layers, copy]),
      "ASSET-01-CTL-LAYER-PROPERTIES": copy,
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-REORDER") {
    const layers = usableList(current("ASSET-01-BTN-LAYER-ADD"));
    const nextList = layers.length > 1 ? [layers[layers.length - 1], ...layers.slice(0, -1)] : layers;
    return { "ASSET-01-BTN-LAYER-ADD": JSON.stringify(nextList) };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-PROPERTIES") {
    return { "ASSET-01-CTL-LAYER-PROPERTIES": keepName(nextValue, current("ASSET-01-CTL-LAYER-PROPERTIES"), "不透明度 100%") };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-MASK") {
    return { "ASSET-01-CTL-LAYER-MASK": keepName(nextValue, current("ASSET-01-CTL-LAYER-MASK"), "語意遮罩") };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-CREATE") {
    return { "ASSET-01-BTN-PATCH-CREATE": keepName(nextValue, current("ASSET-01-BTN-PATCH-CREATE"), "局部修補") };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-PREVIEW") {
    return { "ASSET-01-BTN-PATCH-PREVIEW": "preview" };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-ACCEPT") {
    return { "ASSET-01-BTN-PATCH-ACCEPT": "confirmed" };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-REJECT") {
    return { "ASSET-01-BTN-PATCH-REJECT": "returned" };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-REVISE") {
    return { "ASSET-01-BTN-PATCH-REVISE": "editing" };
  }
  if (actionUid === "ASSET-01-ACT-RUNTIME-VIEW") {
    return {
      [controlUid]: keepName(nextValue, current(controlUid), current("ASSET-01-FLD-PROVIDER") || "就緒"),
      "ASSET-01-FLD-ROUTE": keepName(undefined, current("ASSET-01-FLD-ROUTE"), "就緒"),
    };
  }
  if (actionUid === "ASSET-01-ACT-TASK-RETRY") {
    return {
      "ASSET-01-BTN-RETRY": "retrying",
      "ASSET-01-FLD-ATTEMPT": String((Number.parseInt(current("ASSET-01-FLD-ATTEMPT") ?? "0", 10) || 0) + 1),
      "ASSET-01-FLD-JOB": "retrying",
    };
  }
  if (actionUid === "ASSET-01-ACT-EVALUATE") {
    if (!ready || !(named(current("ASSET-01-FLD-MANIFEST")) || current("ASSET-01-BTN-EXECUTE") === "running")) return {};
    return {
      "ASSET-01-BTN-EVALUATE": "evaluated",
      "ASSET-01-FLD-OVERALL": keepName(undefined, current("ASSET-01-FLD-OVERALL"), "通過"),
      "ASSET-01-FLD-ISSUES": keepName(undefined, current("ASSET-01-FLD-ISSUES"), "無阻擋"),
      "ASSET-01-FLD-CRITERIA": keepName(undefined, current("ASSET-01-FLD-CRITERIA"), "素材評分"),
    };
  }
  if (actionUid === "ASSET-01-ACT-CANDIDATE-CONFIRM") {
    if (current("ASSET-01-BTN-EVALUATE") !== "evaluated") return {};
    return {
      "ASSET-01-BTN-CONFIRM": "confirmed",
      "ASSET-01-FLD-OUTPUT-ID": keepName(undefined, current("ASSET-01-FLD-OUTPUT-ID"), current("ASSET-01-FLD-MANIFEST") || "已確認版本"),
    };
  }
  if (actionUid === "ASSET-01-ACT-VERSION-HISTORY") {
    return { "ASSET-01-BTN-VERSION-HISTORY": keepName(nextValue, current("ASSET-01-FLD-MANIFEST"), "版本歷史") };
  }
  if (actionUid === "ASSET-01-ACT-RESTORE-AS-NEW") {
    const restored = keepName(nextValue, current("ASSET-01-FLD-MANIFEST"), "還原版本");
    const nextList = assets.includes(restored) ? assets : [...assets, restored];
    return {
      "ASSET-01-BTN-RESTORE-AS-NEW": "created",
      "ASSET-01-LST-ASSET": JSON.stringify(nextList),
      "ASSET-01-FLD-MANIFEST": restored,
    };
  }
  if (actionUid === "ASSET-01-ACT-VERSION-LOCK") {
    if (current("ASSET-01-BTN-CONFIRM") !== "confirmed") return {};
    return {
      "ASSET-01-BTN-LOCK": "locked",
      "ASSET-01-FLD-HANDOFF-ASSET-VERSION": keepName(undefined, current("ASSET-01-FLD-OUTPUT-ID"), current("ASSET-01-FLD-MANIFEST") || "已鎖定版本"),
    };
  }
  if (actionUid === "ASSET-01-ACT-HANDOFF") {
    if (current("ASSET-01-BTN-LOCK") !== "locked") return {};
    return {
      "ASSET-01-BTN-HANDOFF": "sent",
      "ASSET-01-FLD-HANDOFF-ASSET-VERSION": keepName(undefined, current("ASSET-01-FLD-OUTPUT-ID"), current("ASSET-01-FLD-MANIFEST") || project),
      ...(named(current("ASSET-01-FLD-BLUEPRINT")) ? { "ASSET-01-FLD-HANDOFF-BLUEPRINT": named(current("ASSET-01-FLD-BLUEPRINT")) } : {}),
      ...(named(current("ASSET-01-FLD-DNA")) ? { "ASSET-01-FLD-HANDOFF-DNA": named(current("ASSET-01-FLD-DNA")) } : {}),
      ...(named(current("ASSET-01-FLD-CANONICAL-FILENAME")) || project
        ? { "ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME": keepName(undefined, current("ASSET-01-FLD-CANONICAL-FILENAME"), project ? `${project}.png` : "") }
        : {}),
      ...(named(current("ASSET-01-FLD-CHECKSUM")) ? { "ASSET-01-FLD-HANDOFF-CHECKSUM": named(current("ASSET-01-FLD-CHECKSUM")) } : {}),
      ...(named(current("ASSET-01-FLD-OVERALL")) ? { "ASSET-01-FLD-HANDOFF-SCORECARD": named(current("ASSET-01-FLD-OVERALL")) } : {}),
      ...(named(current("ASSET-01-FLD-RIGHTS")) ? { "ASSET-01-FLD-HANDOFF-RIGHTS": named(current("ASSET-01-FLD-RIGHTS")) } : {}),
      "ASSET-01-FLD-HANDOFF-MANIFEST-ITEMS": keepName(undefined, current("ASSET-01-FLD-MANIFEST"), assets.join("、")),
      ...(named(current("ASSET-01-BTN-LAYER-DOC-CREATE")) ? { "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE": named(current("ASSET-01-BTN-LAYER-DOC-CREATE")) } : {}),
      ...(named(current("ASSET-01-FLD-SCRIPT")) ? { "ASSET-01-FLD-HANDOFF-SCRIPT-HASH": named(current("ASSET-01-FLD-SCRIPT")) } : {}),
      ...(named(current("ASSET-01-FLD-INPUT-FINGERPRINT")) ? { "ASSET-01-FLD-HANDOFF-CONTRACT-HASH": named(current("ASSET-01-FLD-INPUT-FINGERPRINT")) } : {}),
    };
  }
  if (actionUid === "ASSET-01-ACT-BINDING-VIEW") {
    const existing = named(current(controlUid));
    if (existing) return { [controlUid]: existing };
    if (!ready) return {};
    const fallbacks: Record<string, string> = {
      "ASSET-01-FLD-TASK": `${project} / ${topic}`,
      "ASSET-01-FLD-NAMING-AUTHORITY": named(current("ASSET-01-FLD-NAMING-AUTHORITY")) || "ACPOS_SYSTEM",
      "ASSET-01-FLD-MANIFEST": assets[0] || "",
    };
    const fallback = fallbacks[controlUid] || "";
    return fallback ? { [controlUid]: fallback } : {};
  }
  const existing = current(controlUid);
  if (!nextValue && named(existing)) return { [controlUid]: existing as string };
  return { [controlUid]: nextValue ?? statusFromAction(actionUid) };
}
