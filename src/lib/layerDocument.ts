export const LAYER_DOC_KIND = "VERSIONED_LAYER_DOCUMENT";
export const ASSET_PATCH_KIND = "ASSET_PATCH_CANDIDATE";

export type LayerType = "background" | "character" | "prop" | "effect" | "text";
export type LayerHistoryEntry = { version: number; change: string; at: string };
export type LayerEntry = {
  layer_id: string;
  name: string;
  type: LayerType;
  opacity: number;
  blend: string;
  transform: string;
  mask: string;
  content: string;
  version: number;
  history: LayerHistoryEntry[];
};
export type LayerDocument = {
  kind: typeof LAYER_DOC_KIND;
  layer_doc_id: string;
  name: string;
  asset_ref: string;
  script_ref: string;
  dna_ref: string;
  version: number;
  selected_layer_id: string;
  layers: LayerEntry[];
  history: LayerHistoryEntry[];
  hash: string;
};

export type AssetPatchStatus = "CANDIDATE" | "PREVIEWED" | "ACCEPTED" | "REJECTED" | "REVISED";
export type AssetPatch = {
  kind: typeof ASSET_PATCH_KIND;
  patch_id: string;
  status: AssetPatchStatus;
  source_asset_version: string;
  target_layer_id: string;
  target_layer_name: string;
  region: string;
  requested_delta: string;
  blueprint_ref: string;
  dna_ref: string;
  preserve_constraints: string;
  allowed_side_effects: string;
  acceptance_checks: string;
  preview: string;
  decision: string;
  actor: string;
  fallback_policy: "BLOCK";
  revision_note: string;
  resulting_layer_doc_version: number;
  resulting_asset_version: string;
  hash: string;
};

const LAYER_TYPES = new Set<LayerType>(["background", "character", "prop", "effect", "text"]);
const PATCH_STATUSES = new Set<AssetPatchStatus>(["CANDIDATE", "PREVIEWED", "ACCEPTED", "REJECTED", "REVISED"]);

function nowStamp(): string {
  return new Date().toISOString().slice(0, 19).replace("T", " ");
}

function stableHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function docHash(doc: Omit<LayerDocument, "hash">): string {
  return stableHash([
    doc.layer_doc_id,
    String(doc.version),
    doc.asset_ref,
    doc.script_ref,
    doc.dna_ref,
    doc.selected_layer_id,
    ...doc.layers.flatMap((layer) => [
      layer.layer_id,
      layer.name,
      layer.type,
      String(layer.opacity),
      layer.blend,
      layer.transform,
      layer.mask,
      layer.content,
      String(layer.version),
    ]),
  ]);
}

function patchHash(patch: Omit<AssetPatch, "hash">): string {
  return stableHash([
    patch.patch_id,
    patch.status,
    patch.source_asset_version,
    patch.target_layer_id,
    patch.region,
    patch.requested_delta,
    patch.preserve_constraints,
    patch.preview,
    patch.decision,
    String(patch.resulting_layer_doc_version),
    patch.resulting_asset_version,
  ]);
}

function textOf(rec: Record<string, unknown>, key: string): string {
  return typeof rec[key] === "string" ? String(rec[key]).trim() : "";
}

function layerTypeOf(raw: string): LayerType {
  return LAYER_TYPES.has(raw as LayerType) ? (raw as LayerType) : "background";
}

export function parseLayerDocument(raw: string | null | undefined): LayerDocument | undefined {
  if (!raw || !raw.startsWith("{")) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;
    const rec = parsed as Record<string, unknown>;
    if (rec.kind !== LAYER_DOC_KIND) return undefined;
    const version = Number(rec.version);
    if (!Number.isFinite(version) || version < 1) return undefined;
    const layers = Array.isArray(rec.layers) ? rec.layers : [];
    const mapped: LayerEntry[] = layers
      .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
      .map((item, index) => ({
        layer_id: textOf(item, "layer_id") || `L${index + 1}`,
        name: textOf(item, "name") || `圖層 ${index + 1}`,
        type: layerTypeOf(textOf(item, "type")),
        opacity: Number.isFinite(Number(item.opacity)) ? Math.min(Math.max(Number(item.opacity), 0), 100) : 100,
        blend: textOf(item, "blend") || "normal",
        transform: textOf(item, "transform"),
        mask: textOf(item, "mask"),
        content: textOf(item, "content"),
        version: Number.isFinite(Number(item.version)) && Number(item.version) >= 1 ? Number(item.version) : 1,
        history: Array.isArray(item.history)
          ? (item.history as unknown[])
              .filter((entry): entry is Record<string, unknown> => Boolean(entry) && typeof entry === "object")
              .map((entry, entryIndex) => ({
                version: Number.isFinite(Number(entry.version)) ? Number(entry.version) : entryIndex + 1,
                change: textOf(entry, "change"),
                at: textOf(entry, "at"),
              }))
          : [],
      }));
    const history = Array.isArray(rec.history)
      ? (rec.history as unknown[])
          .filter((entry): entry is Record<string, unknown> => Boolean(entry) && typeof entry === "object")
          .map((entry, index) => ({
            version: Number.isFinite(Number(entry.version)) ? Number(entry.version) : index + 1,
            change: textOf(entry, "change"),
            at: textOf(entry, "at"),
          }))
      : [];
    const candidate: Omit<LayerDocument, "hash"> = {
      kind: LAYER_DOC_KIND,
      layer_doc_id: textOf(rec, "layer_doc_id") || "LDOC-1",
      name: textOf(rec, "name") || "圖層文件",
      asset_ref: textOf(rec, "asset_ref"),
      script_ref: textOf(rec, "script_ref"),
      dna_ref: textOf(rec, "dna_ref"),
      version,
      selected_layer_id: textOf(rec, "selected_layer_id"),
      layers: mapped,
      history,
    };
    return { ...candidate, hash: textOf(rec, "hash") || docHash(candidate) };
  } catch {
    return undefined;
  }
}

export function serializeLayerDocument(doc: LayerDocument): string {
  return JSON.stringify(doc);
}

export function createLayerDocument(input: {
  name?: string;
  asset_ref?: string;
  script_ref?: string;
  dna_ref?: string;
}): LayerDocument {
  const base: Omit<LayerDocument, "hash"> = {
    kind: LAYER_DOC_KIND,
    layer_doc_id: `LDOC-${stableHash([input.name ?? "", nowStamp()])}`,
    name: input.name?.trim() || "圖層文件",
    asset_ref: input.asset_ref ?? "",
    script_ref: input.script_ref ?? "",
    dna_ref: input.dna_ref ?? "",
    version: 1,
    selected_layer_id: "",
    layers: [],
    history: [{ version: 1, change: `建立圖層文件 ${input.name?.trim() || "圖層文件"}`, at: nowStamp() }],
  };
  return { ...base, hash: docHash(base) };
}

function bumpDoc(doc: LayerDocument, change: string): LayerDocument {
  const version = doc.version + 1;
  return {
    ...doc,
    version,
    history: [...doc.history, { version, change, at: nowStamp() }],
    hash: "",
  };
}

function sealDoc(doc: LayerDocument): LayerDocument {
  return { ...doc, hash: docHash(doc) };
}

function bumpLayer(layer: LayerEntry, change: string): LayerEntry {
  const version = layer.version + 1;
  return { ...layer, version, history: [...layer.history, { version, change, at: nowStamp() }] };
}

function selectedLayer(doc: LayerDocument): LayerEntry | undefined {
  return doc.layers.find((layer) => layer.layer_id === doc.selected_layer_id);
}

export function withLayerSelected(doc: LayerDocument, layerId: string): LayerDocument {
  if (!doc.layers.some((layer) => layer.layer_id === layerId)) return doc;
  return sealDoc(bumpDoc({ ...doc, selected_layer_id: layerId }, `選取圖層 ${layerId}`));
}

export function withLayerDocTouched(doc: LayerDocument, change: string): LayerDocument {
  return sealDoc(bumpDoc(doc, change));
}

export function withLayerAdded(doc: LayerDocument, name: string, type: LayerType = "background"): LayerDocument {
  const layerId = `L${doc.layers.length + 1}-${stableHash([name, String(doc.layers.length), nowStamp()])}`;
  const layer: LayerEntry = {
    layer_id: layerId,
    name: name.trim() || `圖層 ${doc.layers.length + 1}`,
    type,
    opacity: 100,
    blend: "normal",
    transform: "",
    mask: "",
    content: "",
    version: 1,
    history: [{ version: 1, change: "新增圖層", at: nowStamp() }],
  };
  return sealDoc({
    ...bumpDoc({ ...doc, layers: [...doc.layers, layer], selected_layer_id: layerId }, `新增圖層 ${layer.name}`),
  });
}

export function withLayerRemoved(doc: LayerDocument, layerId: string): LayerDocument {
  const target = doc.layers.find((layer) => layer.layer_id === layerId);
  if (!target) return doc;
  return sealDoc(
    bumpDoc(
      {
        ...doc,
        layers: doc.layers.filter((layer) => layer.layer_id !== layerId),
        selected_layer_id: doc.selected_layer_id === layerId ? "" : doc.selected_layer_id,
      },
      `刪除圖層 ${target.name}`,
    ),
  );
}

export function withLayerDuplicated(doc: LayerDocument, layerId: string): LayerDocument {
  const target = doc.layers.find((layer) => layer.layer_id === layerId);
  if (!target) return doc;
  const copy: LayerEntry = {
    ...target,
    layer_id: `L${doc.layers.length + 1}-${stableHash([target.name, "copy", nowStamp()])}`,
    name: `${target.name} 副本`,
    version: 1,
    history: [{ version: 1, change: `複製自 ${target.name} v${target.version}`, at: nowStamp() }],
  };
  const index = doc.layers.findIndex((layer) => layer.layer_id === layerId);
  const layers = [...doc.layers];
  layers.splice(index + 1, 0, copy);
  return sealDoc(bumpDoc({ ...doc, layers, selected_layer_id: copy.layer_id }, `複製圖層 ${target.name}`));
}

export function withLayerReordered(doc: LayerDocument): LayerDocument {
  if (doc.layers.length < 2) return doc;
  const layers = [doc.layers[doc.layers.length - 1], ...doc.layers.slice(0, -1)];
  return sealDoc(bumpDoc({ ...doc, layers }, "圖層順序調整"));
}

export function withLayerProperties(
  doc: LayerDocument,
  layerId: string,
  properties: { opacity?: number; blend?: string; transform?: string },
): LayerDocument {
  const target = doc.layers.find((layer) => layer.layer_id === layerId);
  if (!target) return doc;
  const layers = doc.layers.map((layer) =>
    layer.layer_id === layerId
      ? bumpLayer(
          {
            ...layer,
            opacity:
              typeof properties.opacity === "number"
                ? Math.min(Math.max(Math.round(properties.opacity), 0), 100)
                : layer.opacity,
            blend: properties.blend?.trim() || layer.blend,
            transform: properties.transform?.trim() ?? layer.transform,
          },
          `屬性調整（不透明度 ${properties.opacity ?? layer.opacity}%）`,
        )
      : layer,
  );
  return sealDoc(bumpDoc({ ...doc, layers }, `圖層 ${target.name} 屬性調整`));
}

export function withLayerMask(doc: LayerDocument, layerId: string, mask: string): LayerDocument {
  const target = doc.layers.find((layer) => layer.layer_id === layerId);
  if (!target) return doc;
  const layers = doc.layers.map((layer) =>
    layer.layer_id === layerId ? bumpLayer({ ...layer, mask: mask.trim() }, `遮罩調整 ${mask.trim()}`) : layer,
  );
  return sealDoc(bumpDoc({ ...doc, layers }, `圖層 ${target.name} 遮罩調整`));
}

export function withLayerContent(doc: LayerDocument, layerId: string, content: string, change: string): LayerDocument {
  const target = doc.layers.find((layer) => layer.layer_id === layerId);
  if (!target) return doc;
  const layers = doc.layers.map((layer) =>
    layer.layer_id === layerId ? bumpLayer({ ...layer, content: content.trim() }, change) : layer,
  );
  return sealDoc(bumpDoc({ ...doc, layers }, `圖層 ${target.name} 內容更新`));
}

export function selectedLayerOf(doc: LayerDocument): LayerEntry | undefined {
  return selectedLayer(doc);
}

export function parseAssetPatch(raw: string | null | undefined): AssetPatch | undefined {
  if (!raw || !raw.startsWith("{")) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;
    const rec = parsed as Record<string, unknown>;
    if (rec.kind !== ASSET_PATCH_KIND) return undefined;
    const status = textOf(rec, "status");
    const patchId = textOf(rec, "patch_id");
    const source = textOf(rec, "source_asset_version");
    const delta = textOf(rec, "requested_delta");
    const hash = textOf(rec, "hash");
    if (!PATCH_STATUSES.has(status as AssetPatchStatus)) return undefined;
    if (!patchId || !delta || !hash) return undefined;
    return {
      kind: ASSET_PATCH_KIND,
      patch_id: patchId,
      status: status as AssetPatchStatus,
      source_asset_version: source,
      target_layer_id: textOf(rec, "target_layer_id"),
      target_layer_name: textOf(rec, "target_layer_name"),
      region: textOf(rec, "region"),
      requested_delta: delta,
      blueprint_ref: textOf(rec, "blueprint_ref"),
      dna_ref: textOf(rec, "dna_ref"),
      preserve_constraints: textOf(rec, "preserve_constraints") || "未指明內容預設保留",
      allowed_side_effects: textOf(rec, "allowed_side_effects"),
      acceptance_checks: textOf(rec, "acceptance_checks"),
      preview: textOf(rec, "preview"),
      decision: textOf(rec, "decision"),
      actor: textOf(rec, "actor") || "人工",
      fallback_policy: "BLOCK",
      revision_note: textOf(rec, "revision_note"),
      resulting_layer_doc_version: Number.isFinite(Number(rec.resulting_layer_doc_version))
        ? Number(rec.resulting_layer_doc_version)
        : 0,
      resulting_asset_version: textOf(rec, "resulting_asset_version"),
      hash,
    };
  } catch {
    return undefined;
  }
}

export function serializeAssetPatch(patch: AssetPatch): string {
  return JSON.stringify(patch);
}

export function createAssetPatch(input: {
  source_asset_version: string;
  target_layer_id: string;
  target_layer_name: string;
  region: string;
  requested_delta: string;
  blueprint_ref: string;
  dna_ref: string;
  preserve_constraints?: string;
}): AssetPatch {
  const base: Omit<AssetPatch, "hash"> = {
    kind: ASSET_PATCH_KIND,
    patch_id: `PATCH-${stableHash([input.requested_delta, nowStamp()])}`,
    status: "CANDIDATE",
    source_asset_version: input.source_asset_version,
    target_layer_id: input.target_layer_id,
    target_layer_name: input.target_layer_name,
    region: input.region,
    requested_delta: input.requested_delta.trim(),
    blueprint_ref: input.blueprint_ref,
    dna_ref: input.dna_ref,
    preserve_constraints: input.preserve_constraints?.trim() || "未指明內容預設保留",
    allowed_side_effects: "僅目標圖層內容；不動其他圖層與既有版本",
    acceptance_checks: "目標圖層版本遞增；文件版本遞增；來源版本保留",
    preview: "",
    decision: "",
    actor: "人工",
    fallback_policy: "BLOCK",
    revision_note: "",
    resulting_layer_doc_version: 0,
    resulting_asset_version: "",
  };
  return { ...base, hash: patchHash(base) };
}

export function withPatchStatus(patch: AssetPatch, status: AssetPatchStatus, note?: string): AssetPatch {
  return {
    ...patch,
    status,
    decision: note ?? patch.decision,
    revision_note: status === "REVISED" ? note ?? "" : patch.revision_note,
    hash: patchHash({ ...patch, status, decision: note ?? patch.decision }),
  };
}

export function withPatchPreview(patch: AssetPatch, preview: string): AssetPatch {
  const body = preview.trim();
  const status: AssetPatchStatus = "PREVIEWED";
  return {
    ...patch,
    preview: body,
    status,
    hash: patchHash({ ...patch, preview: body, status }),
  };
}

export function patchPrompt(patch: AssetPatch): string {
  const lines = [
    "你是素材局部修補預覽助理。請依下列資訊產生補丁預覽說明（繁體中文，逐條描述修改效果與影響範圍，不要輸出圖片）：",
    `- 來源素材版本：${patch.source_asset_version || "未綁定（將於接受時建立新版本）"}`,
    `- 目標圖層：${patch.target_layer_name || patch.target_layer_id || "未指定"}`,
    `- 區域／遮罩：${patch.region || "未指定"}`,
    `- 要求差異：${patch.requested_delta}`,
    `- 保留約束：${patch.preserve_constraints}`,
    `- 允許副作用：${patch.allowed_side_effects}`,
    `- 驗收檢查：${patch.acceptance_checks}`,
  ];
  if (patch.revision_note) lines.push(`- 修改要求：${patch.revision_note}`);
  return lines.join("\n");
}
