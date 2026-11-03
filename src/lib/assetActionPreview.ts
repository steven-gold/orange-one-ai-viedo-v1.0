import { namedValue, nowStamp, parseThreadList, statusFromAction } from "./coreActionPreview";
import {
  ASSET_CONVERSATION,
  ensureConversationThread,
  previewConversationAction,
} from "./conversationCore";
import {
  appendAssetError,
  assetChecksumOf,
  assetContractHash,
  assetGateContextFrom,
  assetLayerEligible,
  assetTypeFrom,
  ASSET_ERRORS_UID,
  ASSET_GATES_UID,
  buildAssetManifest,
  buildAssetScorecard,
  deriveAssetPageState,
  evaluateAssetGates,
  parseAssetManifest,
  serializeAssetGates,
  type AssetErrorCode,
  type AssetGateContext,
} from "./assetGateContract";
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

function namedSelection(nextValue: string | undefined | null, currentValue: string | null): string {
  return namedValue(nextValue ?? undefined, named(currentValue) || "");
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

const WORKSPACE_RESET_UIDS = [
  "ASSET-01-BTN-EXECUTE",
  "ASSET-01-BTN-EVALUATE",
  "ASSET-01-BTN-CONFIRM",
  "ASSET-01-BTN-LOCK",
  "ASSET-01-BTN-HANDOFF",
  "ASSET-01-BTN-RETRY",
  "ASSET-01-BTN-SINGLE",
  "ASSET-01-BTN-AB",
  "ASSET-01-BTN-ABC",
  "ASSET-01-BTN-ZOOM-IN",
  "ASSET-01-BTN-ZOOM-OUT",
  "ASSET-01-BTN-FIT",
  "ASSET-01-BTN-REFERENCE",
  "ASSET-01-BTN-RESULT-DETAIL",
  "ASSET-01-BTN-SCRIPT",
  "ASSET-01-BTN-CORRECTION-OPEN",
  "ASSET-01-BTN-MODIFY",
  "ASSET-01-BTN-CORRECTION-GENERATE",
  "ASSET-01-BTN-CORRECTION-APPROVE",
  "ASSET-01-BTN-CORRECTION-EXECUTE",
  "ASSET-01-BTN-LAYER-DOC-CREATE",
  "ASSET-01-BTN-LAYER-DOC-UPDATE",
  "ASSET-01-BTN-LAYER-ADD",
  "ASSET-01-BTN-LAYER-DELETE",
  "ASSET-01-BTN-LAYER-DUPLICATE",
  "ASSET-01-BTN-LAYER-REORDER",
  "ASSET-01-BTN-PATCH-CREATE",
  "ASSET-01-BTN-PATCH-PREVIEW",
  "ASSET-01-BTN-PATCH-ACCEPT",
  "ASSET-01-BTN-PATCH-REJECT",
  "ASSET-01-BTN-PATCH-REVISE",
  "ASSET-01-BTN-RUNTIME-DETAIL",
  "ASSET-01-BTN-VERSION-HISTORY",
  "ASSET-01-BTN-RESTORE-AS-NEW",
  "ASSET-01-FLD-TASK-STATUS",
  "ASSET-01-FLD-JOB",
  "ASSET-01-FLD-RETRY-ELIGIBILITY",
  "ASSET-01-FLD-OUTPUT-ID",
  "ASSET-01-FLD-CANONICAL-FILENAME",
  "ASSET-01-FLD-MANIFEST",
  "ASSET-01-FLD-MANIFEST-REQUIRED",
  "ASSET-01-FLD-MANIFEST-REUSE",
  "ASSET-01-FLD-MANIFEST-MISSING",
  "ASSET-01-FLD-MANIFEST-DEFERRED",
  "ASSET-01-FLD-INPUT-FINGERPRINT",
  "ASSET-01-FLD-RIGHTS",
  "ASSET-01-FLD-ROUTE",
  "ASSET-01-FLD-CRITERIA",
  "ASSET-01-FLD-DIMENSIONS",
  "ASSET-01-FLD-OVERALL",
  "ASSET-01-FLD-ISSUES",
  "ASSET-01-FLD-CHECKSUM",
  "ASSET-01-FLD-CORRECTION-RESPONSE",
  "ASSET-01-FLD-HANDOFF-CHECKSUM",
  "ASSET-01-FLD-HANDOFF-CONTRACT-HASH",
  "ASSET-01-FLD-HANDOFF-RIGHTS",
  "ASSET-01-FLD-HANDOFF-SCORECARD",
  "ASSET-01-FLD-HANDOFF-ASSET-VERSION",
  "ASSET-01-FLD-HANDOFF-BLUEPRINT",
  "ASSET-01-FLD-HANDOFF-DNA",
  "ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME",
  "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE",
  "ASSET-01-FLD-HANDOFF-MANIFEST-ITEMS",
  "ASSET-01-FLD-HANDOFF-SCRIPT-HASH",
  "ASSET-01-FLD-SEARCH",
  "ASSET-01-FLD-STAGE",
  "ASSET-01-FLD-ASSET-ERRORS",
  "ASSET-01-FLD-GATES",
  "ASSET-01-LST-ASSET",
  "ASSET-01-LST-COMPARE-VERSIONS",
  "ASSET-01-LST-THREADS",
];

function resetAssetWorkspace(): Record<string, string> {
  const patch: Record<string, string> = {};
  for (const uid of WORKSPACE_RESET_UIDS) patch[uid] = "";
  return patch;
}

export type AssetFinding = {
  finding_id: string;
  issue_type: string;
  asset: string;
  layer: string;
  region: string;
  evidence: string;
};

function buildAssetFindings(
  scorecard: { candidate_ref: string; issues: string[] },
  manifest: ReturnType<typeof parseAssetManifest>,
  layerDocJson: string,
): AssetFinding[] {
  const doc = layerDocJson ? parseLayerDocument(layerDocJson) : null;
  const layerRef = doc ? `${doc.layer_doc_id}#v${doc.version}` : "";
  const findings: AssetFinding[] = [];
  for (const issue of scorecard.issues) {
    const [issueType, ...rest] = issue.split(": ");
    findings.push({
      finding_id: `FND-${assetContractHash({ blueprint: issue, dna: scorecard.candidate_ref, script: "" })}`,
      issue_type: issueType || "EVALUATION_ISSUE",
      asset: scorecard.candidate_ref,
      layer: layerRef,
      region: "",
      evidence: rest.join(": ") || issue,
    });
  }
  for (const itemId of manifest?.missing ?? []) {
    findings.push({
      finding_id: `FND-${assetContractHash({ blueprint: `MANIFEST_MISSING:${itemId}`, dna: manifest?.canonical_script_version_ref ?? "", script: "" })}`,
      issue_type: "MANIFEST_MISSING",
      asset: itemId,
      layer: "",
      region: "",
      evidence: "manifest item not produced yet",
    });
  }
  return findings;
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

export function previewAssetActionInner(
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
    const selected = namedSelection(nextValue, project);
    return selected
      ? {
          "ASSET-01-CTL-PROJECT": selected,
          "ASSET-01-CTL-TOPIC": "",
          "ASSET-01-FLD-TASK": "",
          "ASSET-01-FLD-BLUEPRINT": "",
          "ASSET-01-FLD-DNA": "",
          "ASSET-01-FLD-SCRIPT": "",
          "ASSET-01-FLD-CANONICAL-PROJECTION": "",
          ...resetAssetWorkspace(),
        }
      : {};
  }
  if (actionUid === "ASSET-01-ACT-TOPIC-SELECT") {
    const selected = namedSelection(nextValue, topic);
    return selected ? { "ASSET-01-CTL-TOPIC": selected, "ASSET-01-FLD-TASK": "", ...resetAssetWorkspace() } : {};
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
    const projectionJson = current("ASSET-01-FLD-CANONICAL-PROJECTION");
    const manifest = buildAssetManifest(projectionJson, assets, current("ASSET-01-FLD-OUTPUT-ID"));
    const fingerprint = assetContractHash({ blueprint: named(current("ASSET-01-FLD-BLUEPRINT")), dna: named(current("ASSET-01-FLD-DNA")), script: inboundScript });
    return {
      "ASSET-01-BTN-EXECUTE": "done",
      "ASSET-01-FLD-TASK": named(current("ASSET-01-FLD-TASK")) || `${project} / ${topic}`,
      "ASSET-01-FLD-TASK-STATUS": "done",
      "ASSET-01-FLD-STAGE": "running",
      "ASSET-01-CTL-PROJECT": project,
      "ASSET-01-CTL-TOPIC": topic,
      "ASSET-01-FLD-SCRIPT": inboundScript,
      ...(selected ? { "ASSET-01-FLD-MANIFEST": selected } : {}),
      "ASSET-01-FLD-JOB": "done",
      ...(manifest
        ? {
            "ASSET-01-FLD-MANIFEST-REQUIRED": JSON.stringify(manifest),
            "ASSET-01-FLD-MANIFEST-REUSE": JSON.stringify(manifest.reuse),
            "ASSET-01-FLD-MANIFEST-MISSING": JSON.stringify(manifest.missing),
            "ASSET-01-FLD-MANIFEST-DEFERRED": JSON.stringify(manifest.deferred),
          }
        : {}),
      "ASSET-01-FLD-INPUT-FINGERPRINT": fingerprint,
      "ASSET-01-FLD-RIGHTS": `ACPOS_SYSTEM / DNA:${named(current("ASSET-01-FLD-DNA"))} / script:${inboundScript}`,
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
      "ASSET-01-FLD-TASK-STATUS": "done",
      "ASSET-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(withPreserveCheck(candidate, check)),
    };
  }
  if (actionUid === "ASSET-01-ACT-LAYER-DOC-CREATE") {
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
    const patch = parseAssetPatch(current("ASSET-01-BTN-PATCH-CREATE"));
    if (!patch || patch.status === "ACCEPTED" || patch.status === "REJECTED") return {};
    return {
      "ASSET-01-BTN-PATCH-CREATE": serializeAssetPatch(withPatchPreview(patch, "")),
      "ASSET-01-BTN-PATCH-PREVIEW": "preview",
    };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-ACCEPT") {
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    const priorManifest = parseAssetManifest(current("ASSET-01-FLD-MANIFEST-REQUIRED"));
    const selectedRef = named(current("ASSET-01-FLD-MANIFEST"));
    const selectedItem = priorManifest?.items.find((item) => item.item_id === selectedRef);
    const completed = [
      ...(priorManifest?.completed ?? []),
      ...(selectedItem && !(priorManifest?.completed ?? []).some((row) => row.item_id === selectedItem.item_id)
        ? [{ item_id: selectedItem.item_id, output_ref: assetVersion }]
        : []),
    ];
    const manifest = buildAssetManifest(current("ASSET-01-FLD-CANONICAL-PROJECTION"), nextAssets, assetVersion, nowStamp(), completed);
    return {
      "ASSET-01-BTN-PATCH-CREATE": serializeAssetPatch(accepted),
      "ASSET-01-BTN-LAYER-ADD": serializeLayerDocument(versionedDoc),
      "ASSET-01-LST-ASSET": JSON.stringify(nextAssets),
      "ASSET-01-FLD-OUTPUT-ID": assetVersion,
      "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE": `${versionedDoc.layer_doc_id}#v${versionedDoc.version}`,
      "ASSET-01-BTN-PATCH-ACCEPT": "confirmed",
      ...(manifest
        ? {
            "ASSET-01-FLD-MANIFEST-REQUIRED": JSON.stringify(manifest),
            "ASSET-01-FLD-MANIFEST-REUSE": JSON.stringify(manifest.reuse),
            "ASSET-01-FLD-MANIFEST-MISSING": JSON.stringify(manifest.missing),
            "ASSET-01-FLD-MANIFEST-DEFERRED": JSON.stringify(manifest.deferred),
          }
        : {}),
    };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-REJECT") {
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
    const patch = parseAssetPatch(current("ASSET-01-BTN-PATCH-CREATE"));
    if (!patch || patch.status === "ACCEPTED" || patch.status === "REJECTED") return {};
    return {
      "ASSET-01-BTN-PATCH-CREATE": serializeAssetPatch(withPatchStatus(patch, "REJECTED", "人工拒絕補丁")),
      "ASSET-01-BTN-PATCH-REJECT": "returned",
    };
  }
  if (actionUid === "ASSET-01-ACT-PATCH-REVISE") {
    if (!assetLayerEligible(assetTypeFrom(current))) return {};
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
    if (named(current("ASSET-01-FLD-RETRY-ELIGIBILITY")) !== "eligible") return {};
    return {
      "ASSET-01-BTN-RETRY": "retrying",
      "ASSET-01-FLD-ATTEMPT": String((Number.parseInt(current("ASSET-01-FLD-ATTEMPT") ?? "0", 10) || 0) + 1),
      "ASSET-01-FLD-JOB": "retrying",
      "ASSET-01-FLD-RETRY-ELIGIBILITY": "",
    };
  }
  if (actionUid === "ASSET-01-ACT-EVALUATE") {
    if (!ready || !(named(current("ASSET-01-FLD-MANIFEST")) || named(current("ASSET-01-BTN-EXECUTE")))) return {};
    const ctx = assetGateContextFrom(current);
    const scorecard = buildAssetScorecard(ctx);
    if (!scorecard) return {};
    const manifest = parseAssetManifest(current("ASSET-01-FLD-MANIFEST-REQUIRED"));
    const findings = buildAssetFindings(scorecard, manifest, named(current("ASSET-01-BTN-LAYER-ADD")));
    return {
      "ASSET-01-BTN-EVALUATE": "evaluated",
      "ASSET-01-FLD-CRITERIA": JSON.stringify(scorecard),
      "ASSET-01-FLD-DIMENSIONS": JSON.stringify(scorecard.dimensions),
      "ASSET-01-FLD-OVERALL": scorecard.overall,
      "ASSET-01-FLD-ISSUES": JSON.stringify({
        kind: "ASSET_FINDINGS",
        summary: scorecard.issues.join("；") || "無阻擋",
        findings,
      }),
    };
  }
  if (actionUid === "ASSET-01-ACT-FINDING-CREATE") {
    const ctx = assetGateContextFrom(current);
    if (!ctx.scorecard) return {};
    const manifest = parseAssetManifest(current("ASSET-01-FLD-MANIFEST-REQUIRED"));
    const findings = buildAssetFindings(ctx.scorecard, manifest, named(current("ASSET-01-BTN-LAYER-ADD")));
    if (!findings.length) return {};
    return {
      "ASSET-01-FLD-ISSUES": JSON.stringify({
        kind: "ASSET_FINDINGS",
        summary: ctx.scorecard.issues.join("；") || "無阻擋",
        findings,
        created_at: nowStamp(),
      }),
    };
  }
  if (actionUid === "ASSET-01-ACT-CANDIDATE-CONFIRM") {
    const ctx = assetGateContextFrom(current);
    if (ctx.scorecard?.overall !== "PASS") return {};
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
    const restoredVersion = nextAssetVersion(nextList);
    const finalList = nextList.includes(restoredVersion) ? nextList : [...nextList, restoredVersion];
    return {
      "ASSET-01-BTN-RESTORE-AS-NEW": "created",
      "ASSET-01-LST-ASSET": JSON.stringify(finalList),
      "ASSET-01-FLD-MANIFEST": restored,
      "ASSET-01-FLD-OUTPUT-ID": restoredVersion,
      "ASSET-01-BTN-VERSION-HISTORY": keepName(undefined, current("ASSET-01-BTN-VERSION-HISTORY"), JSON.stringify({
        kind: "ASSET_VERSION_HISTORY",
        source_ref: restored,
        restored_as: restoredVersion,
        at: nowStamp(),
      })),
    };
  }
  if (actionUid === "ASSET-01-ACT-VERSION-LOCK") {
    if (current("ASSET-01-BTN-CONFIRM") !== "confirmed") return {};
    const manifest = parseAssetManifest(current("ASSET-01-FLD-MANIFEST-REQUIRED"));
    if (!manifest?.items.length || manifest.missing.length > 0) return {};
    const outputId = keepName(undefined, current("ASSET-01-FLD-OUTPUT-ID"), current("ASSET-01-FLD-MANIFEST") || "已鎖定版本");
    const doc = layerDocFrom(current);
    const checksum = assetChecksumOf({
      outputId,
      manifestId: manifest.manifest_id,
      layerDocVersion: doc ? `LDOCv${doc.version}` : "",
    });
    return {
      "ASSET-01-BTN-LOCK": "locked",
      "ASSET-01-FLD-OUTPUT-ID": outputId,
      "ASSET-01-FLD-HANDOFF-ASSET-VERSION": outputId,
      "ASSET-01-FLD-CHECKSUM": checksum,
    };
  }
  if (actionUid === "ASSET-01-ACT-HANDOFF") {
    if (current("ASSET-01-BTN-LOCK") !== "locked") return {};
    const ctx = assetGateContextFrom(current);
    const manifest = parseAssetManifest(current("ASSET-01-FLD-MANIFEST-REQUIRED"));
    const missing: string[] = [];
    if (!ctx.checksum) missing.push("checksum");
    if (!ctx.fingerprint) missing.push("input_fingerprint");
    if (!ctx.rights) missing.push("rights");
    if (!ctx.scorecard?.candidate_ref) missing.push("scorecard");
    if (!manifest?.items.length) missing.push("manifest_items");
    if (manifest?.items.length && manifest.missing.length > 0) missing.push(`manifest_missing:${manifest.missing.join(",")}`);
    if (missing.length) return {};
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
      "ASSET-01-FLD-HANDOFF-MANIFEST-ITEMS": manifest
        ? JSON.stringify({ manifest_id: manifest.manifest_id, reuse: manifest.reuse, missing: manifest.missing, items: manifest.items.map((item) => item.item_id) })
        : keepName(undefined, current("ASSET-01-FLD-MANIFEST"), assets.join("、")),
      ...(named(current("ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE")).includes("LDOC-")
        ? { "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE": named(current("ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE")) }
        : named(current("ASSET-01-BTN-LAYER-DOC-CREATE"))
          ? { "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE": named(current("ASSET-01-BTN-LAYER-DOC-CREATE")) }
          : {}),
      ...(named(current("ASSET-01-FLD-SCRIPT")) ? { "ASSET-01-FLD-HANDOFF-SCRIPT-HASH": named(current("ASSET-01-FLD-SCRIPT")) } : {}),
      ...(named(current("ASSET-01-FLD-INPUT-FINGERPRINT")) ? { "ASSET-01-FLD-HANDOFF-CONTRACT-HASH": named(current("ASSET-01-FLD-INPUT-FINGERPRINT")) } : {}),
    };
  }
  if (actionUid === "ASSET-01-ACT-BINDING-VIEW") {
    const explicit = (nextValue ?? "").trim();
    if (explicit) return { [controlUid]: explicit };
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

type HardGate = { gate: string; code: AssetErrorCode; reason: (ctx: AssetGateContext) => string };

const HARD_GATES: Record<string, HardGate> = {
  "ASSET-01-ACT-FLOW-START": {
    gate: "ASSET-01-GATE-EXECUTE",
    code: "ASSET-01-ERR-CONTEXT-001",
    reason: (ctx) =>
      !ctx.project || !ctx.topic
        ? "project/topic context missing"
        : !ctx.blueprint
          ? "blueprint binding missing"
          : !ctx.dna
            ? "DNA binding missing"
            : !ctx.script
              ? "canonical script ref missing"
              : "upstream manifest unresolved (script ASSET view empty)",
  },
  "ASSET-01-ACT-EVALUATE": { gate: "ASSET-01-GATE-EVALUATION", code: "ASSET-01-ERR-CANDIDATE-001", reason: () => "no candidate output to evaluate" },
  "ASSET-01-ACT-CANDIDATE-CONFIRM": {
    gate: "ASSET-01-GATE-CONFIRM",
    code: "ASSET-01-ERR-CRITERIA-001",
    reason: (ctx) => {
      const pending = (ctx.scorecard?.dimensions ?? []).filter((row) => row.score === null).map((row) => row.uid);
      return pending.length ? `reviewer scores pending: ${pending.join(", ")}` : "scorecard must PASS before confirmation";
    },
  },
  "ASSET-01-ACT-VERSION-LOCK": { gate: "ASSET-01-GATE-LOCK", code: "ASSET-01-ERR-VERSION-001", reason: () => "confirmation required before exact-version lock" },
  "ASSET-01-ACT-HANDOFF": {
    gate: "ASSET-01-GATE-HANDOFF",
    code: "ASSET-01-ERR-HANDOFF-001",
    reason: (ctx) => (ctx.locked !== "locked" ? "exact version must be locked before handoff" : "handoff manifest incomplete (checksum/contract/rights/scorecard)"),
  },
  "ASSET-01-ACT-TASK-RETRY": { gate: "ASSET-01-GATE-RETRY", code: "ASSET-01-ERR-PROVIDER-001", reason: () => "no failed provider job recorded; retry not eligible" },
  "ASSET-01-ACT-PATCH-ACCEPT": { gate: "ASSET-01-GATE-PATCH-DECISION", code: "ASSET-01-ERR-PATCH-001", reason: () => "patch must be PREVIEWED before acceptance" },
  "ASSET-01-ACT-CORRECTION-APPROVE": { gate: "ASSET-01-GATE-CORRECTION", code: "ASSET-01-ERR-CORRECTION-001", reason: () => "correction candidate source mismatch or status is not CANDIDATE" },
  "ASSET-01-ACT-CORRECTION-EXECUTE": { gate: "ASSET-01-GATE-CORRECTION", code: "ASSET-01-ERR-CORRECTION-001", reason: () => "correction candidate must be APPROVED before execute" },
  "ASSET-01-ACT-LAYER-DOC-CREATE": { gate: "ASSET-01-GATE-LAYER-ELIGIBLE", code: "ASSET-01-ERR-LAYER-001", reason: (ctx) => (ctx.assetType === "UNRESOLVED" ? "asset type unresolved (manifest item type required)" : `layer document Not Applicable for asset type ${ctx.assetType}`) },
  "ASSET-01-ACT-LAYER-ADD": { gate: "ASSET-01-GATE-LAYER-WRITE", code: "ASSET-01-ERR-LAYER-001", reason: (ctx) => (assetLayerEligible(ctx.assetType) ? "no versioned layer document; create one first" : `layer write Not Applicable for asset type ${ctx.assetType}`) },
  "ASSET-01-ACT-LAYER-DELETE": { gate: "ASSET-01-GATE-LAYER-WRITE", code: "ASSET-01-ERR-LAYER-001", reason: (ctx) => (assetLayerEligible(ctx.assetType) ? "no versioned layer document to mutate" : `layer write Not Applicable for asset type ${ctx.assetType}`) },
  "ASSET-01-ACT-LAYER-DUPLICATE": { gate: "ASSET-01-GATE-LAYER-WRITE", code: "ASSET-01-ERR-LAYER-001", reason: (ctx) => (assetLayerEligible(ctx.assetType) ? "no versioned layer document to mutate" : `layer write Not Applicable for asset type ${ctx.assetType}`) },
  "ASSET-01-ACT-LAYER-REORDER": { gate: "ASSET-01-GATE-LAYER-WRITE", code: "ASSET-01-ERR-LAYER-001", reason: (ctx) => (assetLayerEligible(ctx.assetType) ? "need at least two layers to reorder" : `layer write Not Applicable for asset type ${ctx.assetType}`) },
  "ASSET-01-ACT-PATCH-CREATE": { gate: "ASSET-01-GATE-LAYER-WRITE", code: "ASSET-01-ERR-PATCH-001", reason: (ctx) => (assetLayerEligible(ctx.assetType) ? "select a layer before creating a patch" : `patch Not Applicable for asset type ${ctx.assetType}`) },
  "ASSET-01-ACT-PATCH-PREVIEW": { gate: "ASSET-01-GATE-PATCH-PREVIEW", code: "ASSET-01-ERR-PATCH-001", reason: () => "no patch candidate to preview" },
};

export function previewAssetAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const patch = previewAssetActionInner(controlUid, actionUid, current, nextValue);
  const effective = (uid: string): string | null => (uid in patch ? (patch[uid] ?? null) : current(uid));
  const ctx = assetGateContextFrom(effective);
  const gates = evaluateAssetGates(ctx);
  const stage = deriveAssetPageState(ctx);
  const merged: Record<string, string> = { ...patch, [ASSET_GATES_UID]: serializeAssetGates(gates), "ASSET-01-FLD-STAGE": stage };
  if (Object.keys(patch).length === 0) {
    const hard = HARD_GATES[actionUid];
    if (hard) {
      const reason = hard.reason(ctx);
      const gateRow = gates.find((row) => row.gate === hard.gate);
      if (!gateRow || gateRow.state === "BLOCK") {
        merged[ASSET_ERRORS_UID] = appendAssetError(current(ASSET_ERRORS_UID), hard.code, hard.gate, reason);
      }
    }
  }
  return merged;
}
