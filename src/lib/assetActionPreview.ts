import { namedValue, parseThreadList, statusFromAction } from "./coreActionPreview";
import {
  ASSET_CONVERSATION,
  ensureConversationThread,
  previewConversationAction,
} from "./conversationCore";
import {
  buildCorrectionCandidate,
  parseCorrectionScript,
  serializeCorrectionScript,
  preserveCheckAfterExecute,
  sourceMatches,
  withCorrectionStatus,
  withPreserveCheck,
} from "./correctionScript";
import {
  createAssetPatch,
  createLayerDocument,
  parseAssetPatch,
  parseLayerDocument,
  serializeAssetPatch,
  serializeLayerDocument,
  withLayerAdded,
  withLayerContent,
  withLayerDuplicated,
  withLayerMask,
  withLayerProperties,
  withLayerRemoved,
  withLayerReordered,
  withLayerSelected,
  withLayerDocTouched,
  withPatchPreview,
  withPatchStatus,
  type LayerDocument,
} from "./layerDocument";

export { parseThreadList };

export function usableList(raw: string | null): string[] {
  return parseThreadList(raw).filter((item) => Boolean(namedValue(item, "")));
}

function layerDocFrom(current: (uid: string) => string | null): LayerDocument | undefined {
  return parseLayerDocument(current("ASSET-01-BTN-LAYER-ADD"));
}

function propertiesText(layer: { opacity: number; blend: string; transform: string }): string {
  return [layer.transform?.trim(), `不透明度 ${layer.opacity}% / ${layer.blend}`]
    .filter(Boolean)
    .join(" / ");
}

function parsePropertiesInput(raw: string): { opacity?: number; blend?: string; transform?: string } {
  const segments = raw.split("/").map((part) => part.trim()).filter(Boolean);
  const parsed: { opacity?: number; blend?: string; transform?: string } = {};
  for (const segment of segments) {
    const opacityMatch = segment.match(/(\d{1,3})\s*%/);
    if (opacityMatch && parsed.opacity === undefined) {
      parsed.opacity = Math.min(Number.parseInt(opacityMatch[1], 10), 100);
      continue;
    }
    if (/^(x|y|scale|rotate|translate)/i.test(segment) || /\d/.test(segment)) {
      parsed.transform = parsed.transform ? `${parsed.transform} ${segment}` : segment;
      continue;
    }
    if (parsed.blend === undefined) parsed.blend = segment;
  }
  return parsed;
}

function inspectorSync(doc: LayerDocument): Record<string, string> {
  const layer = doc.layers.find((item) => item.layer_id === doc.selected_layer_id);
  if (!layer) return { "ASSET-01-CTL-LAYER-PROPERTIES": "", "ASSET-01-CTL-LAYER-MASK": "" };
  return {
    "ASSET-01-CTL-LAYER-PROPERTIES": propertiesText(layer),
    "ASSET-01-CTL-LAYER-MASK": layer.mask,
  };
}

function nextAssetVersion(assets: string[]): string {
  let max = 0;
  for (const item of assets) {
    const match = item.match(/ASSET-v(\d+)/i);
    if (match) max = Math.max(max, Number.parseInt(match[1], 10));
  }
  return `ASSET-v${max + 1}`;
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

function exactSource(current: (uid: string) => string | null): string {
  return (
    named(current("ASSET-01-FLD-OUTPUT-ID")) ||
    named(current("ASSET-01-FLD-MANIFEST")) ||
    named(current("ASSET-01-FLD-SCRIPT"))
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
  const conversation = previewConversationAction(ASSET_CONVERSATION, controlUid, actionUid, current, nextValue);
  if (conversation) return ready ? conversation : {};

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
    const inboundScript = named(current("ASSET-01-FLD-SCRIPT"));
    if (!inboundScript) return {};
    const selected = named(current("ASSET-01-FLD-MANIFEST")) || assets[assets.length - 1] || "";
    return {
      "ASSET-01-BTN-EXECUTE": "running",
      "ASSET-01-FLD-TASK": named(current("ASSET-01-FLD-TASK")) || `${project} / ${topic}`,
      "ASSET-01-FLD-TASK-STATUS": "running",
      "ASSET-01-FLD-STAGE": "running",
      "ASSET-01-CTL-PROJECT": project,
      "ASSET-01-CTL-TOPIC": topic,
      "ASSET-01-FLD-SCRIPT": inboundScript,
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
      "ASSET-01-BTN-MODIFY": "open",
      "ASSET-01-TXT-CORRECTION-REQUEST": keepName(nextValue, current("ASSET-01-TXT-CORRECTION-REQUEST"), ""),
      ...ensureConversationThread(ASSET_CONVERSATION, current),
    };
  }
  if (actionUid === "ASSET-01-ACT-CORRECTION-GENERATE") {
    const request = keepName(nextValue, current("ASSET-01-TXT-CORRECTION-REQUEST"), "");
    const source = exactSource(current);
    const candidate = buildCorrectionCandidate({
      department: "ASSET",
      exact_source_version: source,
      target_scope: named(current("ASSET-01-CTL-LAYER-PROPERTIES")) || source,
      requested_delta: request,
      expected_output_kind: "PatchVersion",
    });
    if (!candidate) return {};
    return {
      "ASSET-01-BTN-CORRECTION-OPEN": "open",
      "ASSET-01-BTN-MODIFY": "open",
      "ASSET-01-BTN-CORRECTION-GENERATE": "created",
      "ASSET-01-BTN-CORRECTION-APPROVE": "idle",
      "ASSET-01-BTN-CORRECTION-EXECUTE": "idle",
      "ASSET-01-TXT-CORRECTION-REQUEST": request,
      "ASSET-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(candidate),
    };
  }
  if (actionUid === "ASSET-01-ACT-CORRECTION-APPROVE") {
    const source = exactSource(current);
    const candidate = parseCorrectionScript(current("ASSET-01-FLD-CORRECTION-RESPONSE"));
    if (!sourceMatches(candidate, source) || candidate?.status !== "CANDIDATE") return {};
    return {
      "ASSET-01-BTN-CORRECTION-APPROVE": "approved",
      "ASSET-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(withCorrectionStatus(candidate, "APPROVED")),
    };
  }
  if (actionUid === "ASSET-01-ACT-CORRECTION-EXECUTE") {
    const source = exactSource(current);
    const candidate = parseCorrectionScript(current("ASSET-01-FLD-CORRECTION-RESPONSE"));
    if (!sourceMatches(candidate, source) || candidate?.status !== "APPROVED") return {};
    const check = preserveCheckAfterExecute(candidate, source);
    if (!check.passed) {
      return {
        "ASSET-01-BTN-CORRECTION-EXECUTE": "idle",
        "ASSET-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(withPreserveCheck(candidate, check)),
      };
    }
    return {
      "ASSET-01-BTN-CORRECTION-EXECUTE": "running",
      "ASSET-01-FLD-TASK-STATUS": "running",
      "ASSET-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(withPreserveCheck(candidate, check)),
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DOC-CREATE") {
    if (!named(current("ASSET-01-FLD-SCRIPT"))) return {};
    const name = keepName(nextValue, current("ASSET-01-BTN-LAYER-DOC-CREATE"), "圖層文件");
    const doc = createLayerDocument({
      name,
      asset_ref: named(current("ASSET-01-FLD-OUTPUT-ID")) || named(current("ASSET-01-FLD-MANIFEST")),
      script_ref: named(current("ASSET-01-FLD-SCRIPT")),
      dna_ref: named(current("ASSET-01-FLD-DNA")),
    });
    return {
      "ASSET-01-BTN-LAYER-DOC-CREATE": name,
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(doc),
      ...inspectorSync(doc),
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DOC-UPDATE") {
    const doc = layerDocFrom(current);
    if (!doc) return {};
    const selection = doc.layers.find(
      (layer) => layer.layer_id === String(nextValue ?? "").trim() || layer.name === String(nextValue ?? "").trim(),
    );
    if (selection) {
      const nextDoc = withLayerSelected(doc, selection.layer_id);
      return {
        "ASSET-01-BTN-LAYER-DOC-UPDATE": "saved",
        "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(nextDoc),
        ...inspectorSync(nextDoc),
      };
    }
    const nextDoc = withLayerDocTouched(doc, "圖層文件更新");
    return {
      "ASSET-01-BTN-LAYER-DOC-UPDATE": "saved",
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(nextDoc),
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-ADD") {
    const doc = layerDocFrom(current);
    if (!doc) return {};
    const name = named(nextValue) || `圖層 ${doc.layers.length + 1}`;
    const nextDoc = withLayerAdded(doc, name);
    return {
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(nextDoc),
      "ASSET-01-CTL-LAYER-PROPERTIES": propertiesText(nextDoc.layers[nextDoc.layers.length - 1]),
      "ASSET-01-CTL-LAYER-MASK": "",
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DELETE") {
    const doc = layerDocFrom(current);
    if (!doc || doc.layers.length === 0) return {};
    const target = doc.layers.find((layer) => layer.layer_id === doc.selected_layer_id) ?? doc.layers[doc.layers.length - 1];
    const nextDoc = withLayerRemoved(doc, target.layer_id);
    return {
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(nextDoc),
      ...inspectorSync(nextDoc),
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DUPLICATE") {
    const doc = layerDocFrom(current);
    if (!doc || doc.layers.length === 0) return {};
    const target = doc.layers.find((layer) => layer.layer_id === doc.selected_layer_id) ?? doc.layers[doc.layers.length - 1];
    const nextDoc = withLayerDuplicated(doc, target.layer_id);
    return {
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(nextDoc),
      ...inspectorSync(nextDoc),
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-REORDER") {
    const doc = layerDocFrom(current);
    if (!doc || doc.layers.length < 2) return {};
    return { "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(withLayerReordered(doc)) };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-PROPERTIES") {
    const doc = layerDocFrom(current);
    if (!doc) return {};
    const raw = String(nextValue ?? "").trim();
    const selection = doc.layers.find((layer) => raw.startsWith(`選取:${layer.layer_id}`));
    if (selection) {
      const nextDoc = withLayerSelected(doc, selection.layer_id);
      return {
        "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(nextDoc),
        ...inspectorSync(nextDoc),
      };
    }
    const target = doc.layers.find((layer) => layer.layer_id === doc.selected_layer_id);
    if (!target || !raw) return {};
    const properties = parsePropertiesInput(raw);
    const nextDoc = withLayerProperties(doc, target.layer_id, properties);
    const updated = nextDoc.layers.find((layer) => layer.layer_id === target.layer_id);
    return {
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(nextDoc),
      "ASSET-01-CTL-LAYER-PROPERTIES": updated ? propertiesText(updated) : raw,
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-MASK") {
    const doc = layerDocFrom(current);
    if (!doc) return {};
    const target = doc.layers.find((layer) => layer.layer_id === doc.selected_layer_id);
    const mask = String(nextValue ?? "").trim();
    if (!target || !mask) return {};
    const nextDoc = withLayerMask(doc, target.layer_id, mask);
    return {
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(nextDoc),
      "ASSET-01-CTL-LAYER-MASK": mask,
    };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-CREATE") {
    const doc = layerDocFrom(current);
    if (!doc) return {};
    const target = doc.layers.find((layer) => layer.layer_id === doc.selected_layer_id);
    const delta = String(nextValue ?? "").trim();
    if (!target || !delta) return {};
    const patch = createAssetPatch({
      source_asset_version: named(current("ASSET-01-FLD-OUTPUT-ID")),
      target_layer_id: target.layer_id,
      target_layer_name: target.name,
      region: target.mask,
      requested_delta: delta,
      blueprint_ref: named(current("ASSET-01-FLD-BLUEPRINT")),
      dna_ref: named(current("ASSET-01-FLD-DNA")),
    });
    return { "ASSET-01-BTN-PATCH-CREATE": serializeAssetPatch(patch) };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-PREVIEW") {
    const patch = parseAssetPatch(current("ASSET-01-BTN-PATCH-CREATE"));
    if (!patch || patch.status === "ACCEPTED" || patch.status === "REJECTED") return {};
    return {
      "ASSET-01-BTN-PATCH-CREATE": serializeAssetPatch(withPatchPreview(patch, "")),
      "ASSET-01-BTN-PATCH-PREVIEW": "preview",
    };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-ACCEPT") {
    const patch = parseAssetPatch(current("ASSET-01-BTN-PATCH-CREATE"));
    const doc = layerDocFrom(current);
    if (!patch || !doc || patch.status !== "PREVIEWED" || !patch.preview) return {};
    const target = doc.layers.find((layer) => layer.layer_id === patch.target_layer_id);
    if (!target) return {};
    const versionedDoc = withLayerContent(
      doc,
      target.layer_id,
      [target.content, `[補丁 ${patch.patch_id}] ${patch.requested_delta}`].filter(Boolean).join("\n"),
      `接受補丁 ${patch.patch_id}（${patch.requested_delta}）`,
    );
    const assetVersion = nextAssetVersion(assets);
    const accepted = withPatchStatus({ ...patch, resulting_layer_doc_version: versionedDoc.version, resulting_asset_version: assetVersion }, "ACCEPTED", "人工接受補丁");
    const nextAssets = assets.includes(assetVersion) ? assets : [...assets, assetVersion];
    return {
      "ASSET-01-BTN-PATCH-CREATE": serializeAssetPatch(accepted),
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(versionedDoc),
      "ASSET-01-LST-ASSET": JSON.stringify(nextAssets),
      "ASSET-01-FLD-OUTPUT-ID": assetVersion,
      "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE": `${versionedDoc.layer_doc_id}#v${versionedDoc.version}`,
      "ASSET-01-BTN-PATCH-ACCEPT": "confirmed",
    };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-REJECT") {
    const patch = parseAssetPatch(current("ASSET-01-BTN-PATCH-CREATE"));
    if (!patch || patch.status === "ACCEPTED" || patch.status === "REJECTED") return {};
    return {
      "ASSET-01-BTN-PATCH-CREATE": serializeAssetPatch(withPatchStatus(patch, "REJECTED", "人工拒絕補丁")),
      "ASSET-01-BTN-PATCH-REJECT": "returned",
    };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-REVISE") {
    const patch = parseAssetPatch(current("ASSET-01-BTN-PATCH-CREATE"));
    if (!patch || patch.status === "ACCEPTED" || patch.status === "REJECTED") return {};
    const note = String(nextValue ?? "").trim() || "人工要求修改補丁";
    return {
      "ASSET-01-BTN-PATCH-CREATE": serializeAssetPatch(withPatchStatus(patch, "REVISED", note)),
      "ASSET-01-BTN-PATCH-REVISE": "editing",
    };
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
  const inboundOnly = new Set([
    "ASSET-01-FLD-SCRIPT",
    "ASSET-01-FLD-BLUEPRINT",
    "ASSET-01-FLD-DNA",
    "ASSET-01-FLD-NAMING-AUTHORITY",
  ]);
  if (inboundOnly.has(controlUid)) {
    const existing = named(current(controlUid));
    return existing ? { [controlUid]: existing } : {};
  }
  const existing = current(controlUid);
  if (!nextValue && named(existing)) return { [controlUid]: existing as string };
  return { [controlUid]: nextValue ?? statusFromAction(actionUid) };
}
