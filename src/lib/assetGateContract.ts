import { parseLayerDocument } from "./layerDocument";
import { nowStamp } from "./coreActionPreview";

export const ASSET_ERROR_CODES = [
  "ASSET-01-ERR-CONTEXT-001",
  "ASSET-01-ERR-BLUEPRINT-001",
  "ASSET-01-ERR-SCRIPT-001",
  "ASSET-01-ERR-DNA-001",
  "ASSET-01-ERR-MANIFEST-001",
  "ASSET-01-ERR-NAMING-001",
  "ASSET-01-ERR-ROUTE-001",
  "ASSET-01-ERR-PROVIDER-001",
  "ASSET-01-ERR-CANDIDATE-001",
  "ASSET-01-ERR-CRITERIA-001",
  "ASSET-01-ERR-CORRECTION-001",
  "ASSET-01-ERR-TRANSLATION-001",
  "ASSET-01-ERR-LAYER-001",
  "ASSET-01-ERR-PATCH-001",
  "ASSET-01-ERR-VERSION-001",
  "ASSET-01-ERR-HANDOFF-001",
  "ASSET-01-ERR-PERM-001",
] as const;

export type AssetErrorCode = (typeof ASSET_ERROR_CODES)[number];

export const ASSET_ERROR_CONTRACT: Record<AssetErrorCode, { condition: string; recovery: string }> = {
  "ASSET-01-ERR-CONTEXT-001": { condition: "Project/Topic/Task context missing/stale", recovery: "BLOCK; re-resolve exact task" },
  "ASSET-01-ERR-BLUEPRINT-001": { condition: "Child lock/Blueprint missing/hash mismatch", recovery: "BLOCK; return Core/Blueprint owner" },
  "ASSET-01-ERR-SCRIPT-001": { condition: "ASSET Script View/Section missing/hash mismatch", recovery: "BLOCK; no local script guess" },
  "ASSET-01-ERR-DNA-001": { condition: "DNA/continuity ref missing or mismatch", recovery: "BLOCK; no substitute" },
  "ASSET-01-ERR-MANIFEST-001": { condition: "Asset Manifest item/type/purpose/reuse status invalid", recovery: "BLOCK; re-resolve upstream manifest" },
  "ASSET-01-ERR-NAMING-001": { condition: "Canonical filename/output identity unavailable or mismatched", recovery: "BLOCK; wait ACPOS naming resolution; page cannot rename" },
  "ASSET-01-ERR-ROUTE-001": { condition: "Approved Provider Route unavailable", recovery: "BLOCK; wait ACPOS Core/API Router" },
  "ASSET-01-ERR-PROVIDER-001": { condition: "Provider job/callback failed", recovery: "Preserve task/candidate; show retry eligibility" },
  "ASSET-01-ERR-CANDIDATE-001": { condition: "Candidate provenance/checksum invalid", recovery: "BLOCK evaluation/decision" },
  "ASSET-01-ERR-CRITERIA-001": { condition: "ASSET criteria version missing/wrong department", recovery: "BLOCK evaluation; no generic default" },
  "ASSET-01-ERR-CORRECTION-001": { condition: "Correction context stale/candidate unapproved", recovery: "Return correction discussion; no execute" },
  "ASSET-01-ERR-TRANSLATION-001": { condition: "Shared Translation/Compiler failed", recovery: "BLOCK provider execution; preserve Chinese candidate" },
  "ASSET-01-ERR-LAYER-001": { condition: "Layer operation invalid/locked/cross-document", recovery: "BLOCK mutation" },
  "ASSET-01-ERR-PATCH-001": { condition: "Patch lineage/preserve/preview invalid", recovery: "BLOCK patch decision" },
  "ASSET-01-ERR-VERSION-001": { condition: "Overwrite/non-exact version attempt", recovery: "BLOCK; create new version only" },
  "ASSET-01-ERR-HANDOFF-001": { condition: "Exact handoff manifest/contract/hash incomplete", recovery: "BLOCK handoff; preserve locked version" },
  "ASSET-01-ERR-PERM-001": { condition: "Permission/scope denied", recovery: "Disable action + show real reason" },
};

export const ASSET_GATE_UIDS = [
  "ASSET-01-GATE-PAGE",
  "ASSET-01-GATE-CONTEXT",
  "ASSET-01-GATE-CHILD-LOCK",
  "ASSET-01-GATE-SCRIPT",
  "ASSET-01-GATE-MANIFEST",
  "ASSET-01-GATE-NAMING",
  "ASSET-01-GATE-ROUTE",
  "ASSET-01-GATE-EXECUTE",
  "ASSET-01-GATE-CANDIDATE",
  "ASSET-01-GATE-EVALUATION",
  "ASSET-01-GATE-WAIT-CONFIRM",
  "ASSET-01-GATE-CORRECTION",
  "ASSET-01-GATE-LAYER-ELIGIBLE",
  "ASSET-01-GATE-LAYER-WRITE",
  "ASSET-01-GATE-PATCH-PREVIEW",
  "ASSET-01-GATE-PATCH-DECISION",
  "ASSET-01-GATE-CONFIRM",
  "ASSET-01-GATE-LOCK",
  "ASSET-01-GATE-HANDOFF",
  "ASSET-01-GATE-RETRY",
  "ASSET-01-GATE-COMPARE",
] as const;

export type AssetGateUid = (typeof ASSET_GATE_UIDS)[number];
export type AssetGateState = { gate: AssetGateUid; state: "PASS" | "BLOCK"; reason: string };
export type AssetErrorEntry = { kind: "ASSET_ERROR"; code: AssetErrorCode; gate: string; detail: string; at: string; recovery: string };

export const ASSET_ERRORS_UID = "ASSET-01-FLD-ASSET-ERRORS";
export const ASSET_GATES_UID = "ASSET-01-FLD-GATES";

function assetHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function buildAssetError(code: AssetErrorCode, gate: string, detail: string, at = nowStamp()): AssetErrorEntry | null {
  const contract = ASSET_ERROR_CONTRACT[code];
  if (!contract) return null;
  return { kind: "ASSET_ERROR", code, gate, detail, at, recovery: contract.recovery };
}

export function parseAssetErrors(raw: string | null | undefined): AssetErrorEntry[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as AssetErrorEntry[]) : [];
  } catch {
    return [];
  }
}

export function serializeAssetErrors(entries: AssetErrorEntry[]): string {
  return JSON.stringify(entries.slice(-12));
}

export function appendAssetError(raw: string | null | undefined, code: AssetErrorCode, gate: string, detail: string): string {
  const entry = buildAssetError(code, gate, detail);
  if (!entry) return raw ?? "[]";
  return serializeAssetErrors([...parseAssetErrors(raw), entry]);
}

export type AssetManifestItemType = "SCENE" | "CHARACTER" | "OBJECT" | "VFX" | "TEXTURE" | "TEXT" | "VOICE" | "MUSIC" | "SFX" | "REFERENCE";

export type AssetManifestItem = {
  item_id: string;
  requirement: string;
  type: AssetManifestItemType;
  output_kind: string;
};
export type AssetManifest = {
  kind: "ASSET_MANIFEST";
  manifest_id: string;
  canonical_script_version_ref: string;
  items: AssetManifestItem[];
  reuse: string[];
  missing: string[];
  deferred: string[];
  completed: Array<{ item_id: string; output_ref: string }>;
  created_at: string;
};

function named(value: string | null | undefined): string {
  return typeof value === "string" ? value.trim() : "";
}


const AUDIO_ITEM_TYPES: ReadonlySet<AssetManifestItemType> = new Set<AssetManifestItemType>(["VOICE", "MUSIC", "SFX"]);
const TYPE_TAG_PATTERN = /\[(SFX|MUSIC|VOICE|CHARACTER|OBJECT|VFX|TEXTURE|TEXT|REFERENCE)\]\s*/i;

const SEMANTIC_TYPE_HINTS: Array<[AssetManifestItemType, RegExp]> = [
  ["SFX", /(?:SFX|音效|聲音效果|音效說明)/g],
  ["VOICE", /(?:旁白|配音|獨白|畫外音)/g],
  ["MUSIC", /(?:配樂|背景音樂|主題曲|音樂)/g],
  ["VFX", /(?:VFX|特效|視覺效果)/g],
  ["TEXT", /(?:字幕|標題卡|片頭|片尾)/g],
];

function itemTypeFromRequirement(requirement: string): AssetManifestItemType {
  const match = TYPE_TAG_PATTERN.exec(requirement);
  if (match) return match[1].toUpperCase() as AssetManifestItemType;
  const counts = new Map<AssetManifestItemType, number>();
  for (const [type, pattern] of SEMANTIC_TYPE_HINTS) {
    const hits = requirement.match(pattern);
    if (hits?.length) counts.set(type, hits.length);
  }
  if (counts.size) {
    const order: AssetManifestItemType[] = ["SFX", "VOICE", "MUSIC", "VFX", "TEXT"];
    let best: AssetManifestItemType = "SCENE";
    let bestCount = 0;
    for (const type of order) {
      const count = counts.get(type) ?? 0;
      if (count > bestCount) {
        best = type;
        bestCount = count;
      }
    }
    if (bestCount > 0) return best;
  }
  return "SCENE";
}

export function assetIsAudioType(type: string): boolean {
  return AUDIO_ITEM_TYPES.has(type as AssetManifestItemType);
}

export function assetLayerEligible(type: string): boolean {
  return type !== "UNRESOLVED" && !assetIsAudioType(type) && type !== "REFERENCE";
}

export function assetProfileOf(type: string): "QCP-ASSET-IMAGE-V1" | "QCP-ASSET-AUDIO-V1" {
  return assetIsAudioType(type) ? "QCP-ASSET-AUDIO-V1" : "QCP-ASSET-IMAGE-V1";
}

function parseScriptProjection(raw: string | null | undefined): { version: string; assetItems: Array<{ ref: string; requirement: string; type: AssetManifestItemType }> } | null {
  if (!raw) return null;
  try {
    const projection = JSON.parse(raw) as {
      version?: string;
      views?: { views?: Array<{ view?: string; items?: Array<{ ref?: string; requirement?: string; type?: string }> }> };
      structure?: { scenes?: Array<{ scene_id?: string; title?: string; beats?: Array<{ action?: string; dialogue?: string; narration?: string }> }> };
    };
    const assetView = projection.views?.views?.find((view) => view?.view === "ASSET");
    let items = (assetView?.items ?? [])
      .map((item) => {
        const requirement = String(item?.requirement ?? "").trim();
        const declared = String(item?.type ?? "").trim().toUpperCase();
        const type = (["SCENE", "CHARACTER", "OBJECT", "VFX", "TEXTURE", "TEXT", "VOICE", "MUSIC", "SFX", "REFERENCE"].includes(declared) ? declared : itemTypeFromRequirement(requirement)) as AssetManifestItemType;
        return { ref: String(item?.ref ?? "").trim(), requirement, type };
      })
      .filter((item) => item.ref.length > 0);
    if (!items.length) {
      items = (projection.structure?.scenes ?? [])
        .map((scene) => {
          const beatsText = (scene?.beats ?? [])
            .map((beat) => `${beat?.action ?? ""} ${beat?.dialogue ?? ""} ${beat?.narration ?? ""}`)
            .join(" ");
          const requirement = [String(scene?.title ?? "").trim(), beatsText.trim()].filter(Boolean).join("\n");
          return { ref: String(scene?.scene_id ?? "").trim(), requirement, type: itemTypeFromRequirement(requirement) };
        })
        .filter((item) => item.ref.length > 0);
    }
    if (!items.length) return null;
    return { version: String(projection.version ?? ""), assetItems: items };
  } catch {
    return null;
  }
}

export function buildAssetManifest(
  scriptJson: string | null | undefined,
  existingAssets: string[],
  outputId: string | null | undefined,
  at = nowStamp(),
  completed: Array<{ item_id: string; output_ref: string }> = [],
): AssetManifest | null {
  const projection = parseScriptProjection(scriptJson);
  if (!projection) return null;
  const itemIds = new Set(projection.assetItems.map((item) => item.ref));
  const done = new Map(completed.filter((row) => itemIds.has(row.item_id)).map((row) => [row.item_id, row.output_ref]));
  const items: AssetManifestItem[] = projection.assetItems.map((item) => ({
    item_id: item.ref,
    requirement: item.requirement,
    type: item.type,
    output_kind: assetIsAudioType(item.type) ? "AUDIO_WAVEFORM" : item.type === "REFERENCE" ? "IMAGE_OR_METADATA" : "IMAGE",
  }));
  const reuse = items.filter((item) => done.has(item.item_id)).map((item) => item.item_id);
  const missing = items.filter((item) => !done.has(item.item_id)).map((item) => item.item_id);
  return {
    kind: "ASSET_MANIFEST",
    manifest_id: `ASM-${assetHash([projection.version, items.map((item) => item.item_id).join(",")])}`,
    canonical_script_version_ref: projection.version,
    items,
    reuse,
    missing,
    deferred: [],
    completed: [...done.entries()].map(([item_id, output_ref]) => ({ item_id, output_ref })),
    created_at: at,
  };
}

export function parseAssetManifest(raw: string | null | undefined): AssetManifest | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as AssetManifest;
    return parsed?.kind === "ASSET_MANIFEST" && Array.isArray(parsed.items)
      ? { ...parsed, completed: Array.isArray(parsed.completed) ? parsed.completed : [] }
      : null;
  } catch {
    return null;
  }
}

export function assetContractHash(parts: { blueprint: string; dna: string; script: string }): string {
  return `AFP-${assetHash([parts.blueprint, parts.dna, parts.script])}`;
}

export function assetChecksumOf(parts: { outputId: string; manifestId: string; layerDocVersion: string }): string {
  return `CKS-${assetHash([parts.outputId, parts.manifestId, parts.layerDocVersion])}`;
}

function layerDocFrom(raw: string | null | undefined) {
  return parseLayerDocument(raw ?? null);
}

export type AssetGateContext = {
  project: string;
  topic: string;
  blueprint: string;
  dna: string;
  script: string;
  naming: string;
  route: string;
  manifest: AssetManifest | null;
  assets: string[];
  outputId: string;
  manifestSelected: string;
  canonicalFilename: string;
  checksum: string;
  fingerprint: string;
  rights: string;
  evaluated: string;
  scorecard: AssetScorecard | null;
  confirmed: string;
  locked: string;
  handoff: string;
  correctionOpen: string;
  correctionApproved: string;
  retryEligibility: string;
  job: string;
  layerDocJson: string;
  patchJson: string;
  executing: string;
  compareSelection: string;
  assetType: string;
};

export function assetTypeFrom(current: (uid: string) => string | null): string {
  const manifest = parseAssetManifest(current("ASSET-01-FLD-MANIFEST-REQUIRED"));
  const selectedRef = named(current("ASSET-01-FLD-MANIFEST")) || named(current("ASSET-01-FLD-OUTPUT-ID"));
  const item = manifest?.items.find((row) => row.item_id === selectedRef) ?? manifest?.items[0];
  return item?.type ?? "UNRESOLVED";
}

export function assetGateContextFrom(current: (uid: string) => string | null): AssetGateContext {
  const list = (uid: string): string[] => {
    try {
      const parsed = JSON.parse(current(uid) || "[]") as unknown;
      return Array.isArray(parsed) ? parsed.filter((row): row is string => typeof row === "string" && row.trim().length > 0) : [];
    } catch {
      return [];
    }
  };
  let scorecard: AssetScorecard | null = null;
  const scorecardRaw = named(current("ASSET-01-FLD-CRITERIA"));
  if (scorecardRaw.startsWith("{")) {
    try {
      const parsed = JSON.parse(scorecardRaw) as AssetScorecard;
      scorecard = parsed?.kind === "ASSET_SCORECARD" ? parsed : null;
    } catch {
      scorecard = null;
    }
  }
  const manifest = parseAssetManifest(current("ASSET-01-FLD-MANIFEST-REQUIRED"));
  const assetType = assetTypeFrom(current);
  return {
    project: named(current("ASSET-01-CTL-PROJECT")),
    topic: named(current("ASSET-01-CTL-TOPIC")),
    blueprint: named(current("ASSET-01-FLD-BLUEPRINT")),
    dna: named(current("ASSET-01-FLD-DNA")),
    script: named(current("ASSET-01-FLD-SCRIPT")),
    naming: named(current("ASSET-01-FLD-NAMING-AUTHORITY")),
    route: named(current("ASSET-01-FLD-ROUTE")),
    manifest,
    assets: list("ASSET-01-LST-ASSET"),
    outputId: named(current("ASSET-01-FLD-OUTPUT-ID")),
    manifestSelected: named(current("ASSET-01-FLD-MANIFEST")),
    canonicalFilename: named(current("ASSET-01-FLD-CANONICAL-FILENAME")),
    checksum: named(current("ASSET-01-FLD-CHECKSUM")),
    fingerprint: named(current("ASSET-01-FLD-INPUT-FINGERPRINT")),
    rights: named(current("ASSET-01-FLD-RIGHTS")),
    evaluated: named(current("ASSET-01-BTN-EVALUATE")),
    scorecard,
    confirmed: named(current("ASSET-01-BTN-CONFIRM")),
    locked: named(current("ASSET-01-BTN-LOCK")),
    handoff: named(current("ASSET-01-BTN-HANDOFF")),
    correctionOpen: named(current("ASSET-01-BTN-CORRECTION-OPEN")),
    correctionApproved: named(current("ASSET-01-BTN-CORRECTION-APPROVE")),
    retryEligibility: named(current("ASSET-01-FLD-RETRY-ELIGIBILITY")),
    job: named(current("ASSET-01-FLD-JOB")),
    layerDocJson: named(current("ASSET-01-BTN-LAYER-ADD")),
    patchJson: named(current("ASSET-01-BTN-PATCH-CREATE")),
    executing: named(current("ASSET-01-BTN-EXECUTE")),
    compareSelection: named(current("ASSET-01-LST-COMPARE-VERSIONS")),
    assetType,
  };
}

export type AssetScoreDimension = {
  uid: string;
  label: string;
  weight: number;
  score: number | null;
  hard_block: boolean;
  evidence: string;
};

export type AssetScorecard = {
  kind: "ASSET_SCORECARD";
  criteria_version: string;
  profile: string;
  asset_type: string;
  candidate_ref: string;
  dimensions: AssetScoreDimension[];
  overall: "PASS" | "BLOCKED";
  issues: string[];
  evaluated_at: string;
};

type QcpDimensionSpec = { uid: string; label: string; weight: number; hard_block: boolean };

const QCP_IMAGE_PROFILE: QcpDimensionSpec[] = [
  { uid: "QA-DIM-ASSET-SCRIPT", label: "Script / Manifest Compliance", weight: 15, hard_block: false },
  { uid: "QA-DIM-ASSET-IDENTITY", label: "Character / Identity DNA Fidelity", weight: 20, hard_block: false },
  { uid: "QA-DIM-ASSET-OBJECT", label: "Object Fidelity", weight: 10, hard_block: false },
  { uid: "QA-DIM-ASSET-SCENE", label: "Scene / Environment Fidelity", weight: 10, hard_block: false },
  { uid: "QA-DIM-ASSET-COMPOSITION", label: "Composition / Framing", weight: 10, hard_block: false },
  { uid: "QA-DIM-ASSET-GEOMETRY", label: "Anatomy / Geometry / Artifact Integrity", weight: 15, hard_block: false },
  { uid: "QA-DIM-ASSET-STYLE", label: "Style / Color / Lighting Consistency", weight: 10, hard_block: false },
  { uid: "QA-DIM-ASSET-TECH", label: "Technical Image Quality", weight: 5, hard_block: false },
  { uid: "QA-DIM-RIGHTS-POLICY", label: "Rights / Policy", weight: 5, hard_block: true },
];

const QCP_AUDIO_PROFILE: QcpDimensionSpec[] = [
  { uid: "QA-DIM-AUDIO-SCRIPT", label: "Script / Manifest Compliance", weight: 15, hard_block: false },
  { uid: "QA-DIM-AUDIO-IDENTITY", label: "Voice Identity / Semantic Fit", weight: 20, hard_block: false },
  { uid: "QA-DIM-AUDIO-CONTENT", label: "Pronunciation / Content Accuracy", weight: 15, hard_block: false },
  { uid: "QA-DIM-AUDIO-TIMING", label: "Timing / Duration", weight: 10, hard_block: false },
  { uid: "QA-DIM-AUDIO-NOISE", label: "Noise / Clipping / Distortion", weight: 15, hard_block: false },
  { uid: "QA-DIM-AUDIO-LEVEL", label: "Level / Dynamics", weight: 10, hard_block: false },
  { uid: "QA-DIM-AUDIO-TECH", label: "Technical Audio Format", weight: 10, hard_block: false },
  { uid: "QA-DIM-RIGHTS-POLICY", label: "Rights / Policy", weight: 5, hard_block: true },
];

const REVIEW_PENDING = "評審待輸入（本頁僅結構性判定）";

export function buildAssetScorecard(ctx: AssetGateContext, at = nowStamp()): AssetScorecard | null {
  const candidateRef = ctx.outputId || ctx.manifestSelected;
  if (!candidateRef) return null;
  const doc = layerDocFrom(ctx.layerDocJson);
  const upstreamOk = Boolean(ctx.blueprint && ctx.dna && ctx.script);
  const completedRow = (ctx.manifest?.completed ?? []).find((row) => row.output_ref === candidateRef);
  const manifestItem =
    ctx.manifest?.items.find((item) => item.item_id === candidateRef || item.requirement === candidateRef) ??
    (completedRow ? ctx.manifest?.items.find((item) => item.item_id === completedRow.item_id) : undefined);
  const assetType = manifestItem?.type ?? (ctx.assetType !== "UNRESOLVED" ? ctx.assetType : "SCENE");
  const profile = assetProfileOf(assetType);
  const specs = assetIsAudioType(assetType) ? QCP_AUDIO_PROFILE : QCP_IMAGE_PROFILE;
  const scriptOk = upstreamOk && Boolean(manifestItem);
  const scriptEvidence = `${scriptOk ? "PASS" : "FAIL"}: ${ctx.blueprint || "BP?"} / ${ctx.dna || "DNA?"} / ${ctx.script || "CS?"}${manifestItem ? ` / item ${manifestItem.item_id}` : ctx.manifest ? " / candidate outside upstream manifest items" : ""}`;
  const layerEvidence = doc ? `${doc.layer_doc_id}#v${doc.version} hash=${doc.hash}` : "no layer document";
  const dimensions: AssetScoreDimension[] = specs.map((spec) => {
    if (spec.hard_block) {
      return { uid: spec.uid, label: spec.label, weight: spec.weight, score: ctx.rights ? 100 : 0, hard_block: true, evidence: ctx.rights ? ctx.rights : "rights basis not resolved" };
    }
    if (spec.uid.endsWith("-SCRIPT")) {
      return { uid: spec.uid, label: spec.label, weight: spec.weight, score: scriptOk ? 100 : 0, hard_block: false, evidence: scriptEvidence };
    }
    if (spec.uid.endsWith("-TECH")) {
      return { uid: spec.uid, label: spec.label, weight: spec.weight, score: ctx.checksum ? 100 : null, hard_block: false, evidence: ctx.checksum ? `checksum ${ctx.checksum}` : `checksum pending lock; layer: ${layerEvidence}` };
    }
    return { uid: spec.uid, label: spec.label, weight: spec.weight, score: null, hard_block: false, evidence: REVIEW_PENDING };
  });
  const issues = dimensions.filter((row) => row.score === 0).map((row) => `${row.uid}: ${row.hard_block ? row.evidence : `${row.label} — ${row.evidence}`}`);
  return {
    kind: "ASSET_SCORECARD",
    criteria_version: `ASSET-CRITERIA-${assetHash([ctx.project, ctx.topic, ctx.script])}`,
    profile,
    asset_type: assetType,
    candidate_ref: candidateRef,
    dimensions,
    overall: issues.length ? "BLOCKED" : "PASS",
    issues,
    evaluated_at: at,
  };
}

export function evaluateAssetGates(ctx: AssetGateContext): AssetGateState[] {
  const state = (gate: AssetGateUid, ok: boolean, reason: string): AssetGateState => ({ gate, state: ok ? "PASS" : "BLOCK", reason });
  const ready = Boolean(ctx.project && ctx.topic && ctx.blueprint && ctx.dna && ctx.script);
  const candidate = Boolean(ctx.outputId || ctx.manifestSelected || ctx.assets.length);
  const evaluatedPass = ctx.scorecard?.overall === "PASS";
  const doc = layerDocFrom(ctx.layerDocJson);
  const patch = (() => {
    if (!ctx.patchJson.startsWith("{")) return null;
    try {
      return JSON.parse(ctx.patchJson) as { status?: string };
    } catch {
      return null;
    }
  })();
  const handoffComplete = Boolean(ctx.checksum && ctx.fingerprint && ctx.rights && named(String(ctx.scorecard?.candidate_ref ?? "")) && (ctx.manifest?.items.length ?? 0) > 0);
  const lockComplete = Boolean(ctx.manifest?.items.length) && (ctx.manifest?.missing.length ?? 1) === 0;
  return [
    state("ASSET-01-GATE-PAGE", true, "workspace loaded"),
    state("ASSET-01-GATE-CONTEXT", Boolean(ctx.project && ctx.topic), ctx.project && ctx.topic ? `${ctx.project} / ${ctx.topic}` : "project/topic context missing"),
    state("ASSET-01-GATE-CHILD-LOCK", Boolean(ctx.blueprint), ctx.blueprint ? `blueprint binding ${ctx.blueprint}` : "locked blueprint binding required"),
    state("ASSET-01-GATE-SCRIPT", Boolean(ctx.script), ctx.script || "canonical script ref required"),
    state("ASSET-01-GATE-MANIFEST", Boolean(ctx.manifest?.items.length), ctx.manifest ? `${ctx.manifest.manifest_id} (${ctx.manifest.items.length} items)` : "upstream manifest unresolved"),
    state("ASSET-01-GATE-NAMING", ctx.naming === "ACPOS_SYSTEM" && Boolean(ctx.canonicalFilename), ctx.naming === "ACPOS_SYSTEM" ? (ctx.canonicalFilename || "canonical filename pending") : "naming authority must be ACPOS_SYSTEM"),
    state("ASSET-01-GATE-ROUTE", Boolean(ctx.route), ctx.route || "provider route snapshot absent (structural mode)"),
    state("ASSET-01-GATE-EXECUTE", ready && Boolean(ctx.manifest?.items.length), ready ? "inputs resolved" : "context/blueprint/DNA/script required"),
    state("ASSET-01-GATE-CANDIDATE", candidate, candidate ? (ctx.outputId || ctx.manifestSelected || ctx.assets[ctx.assets.length - 1]) : "no candidate output"),
    state("ASSET-01-GATE-EVALUATION", Boolean(ctx.scorecard), ctx.scorecard ? `scorecard ${ctx.scorecard.overall}` : "evaluation pending"),
    state("ASSET-01-GATE-WAIT-CONFIRM", Boolean(ctx.scorecard) && ctx.confirmed !== "confirmed", evaluatedPass ? "awaiting human confirmation" : "scorecard must PASS before confirmation"),
    state("ASSET-01-GATE-CORRECTION", ctx.correctionOpen === "open", ctx.correctionOpen === "open" ? (ctx.correctionApproved === "approved" ? "correction approved" : "correction discussion open") : "correction not opened"),
    state("ASSET-01-GATE-LAYER-ELIGIBLE", assetLayerEligible(ctx.assetType), ctx.assetType === "UNRESOLVED" ? "asset type unresolved (manifest item type required)" : assetLayerEligible(ctx.assetType) ? `image-compatible asset type ${ctx.assetType}` : `asset type ${ctx.assetType} skips LayerRuntime (Not Applicable)`),
    state("ASSET-01-GATE-LAYER-WRITE", assetLayerEligible(ctx.assetType) && Boolean(doc), doc ? `${doc.layer_doc_id}#v${doc.version}` : assetLayerEligible(ctx.assetType) ? "no layer document" : `layer write Not Applicable for ${ctx.assetType}`),
    state("ASSET-01-GATE-PATCH-PREVIEW", Boolean(patch && patch.status === "CANDIDATE"), patch ? `patch ${patch.status}` : "no patch candidate"),
    state("ASSET-01-GATE-PATCH-DECISION", Boolean(patch && (patch.status === "PREVIEWED" || patch.status === "CANDIDATE")), patch ? `patch ${patch.status}` : "no patch decision pending"),
    state("ASSET-01-GATE-CONFIRM", evaluatedPass && ctx.confirmed !== "confirmed", evaluatedPass ? "ready to confirm" : "evaluation must PASS"),
    state("ASSET-01-GATE-LOCK", ctx.confirmed === "confirmed" && ctx.locked !== "locked" && lockComplete, ctx.confirmed === "confirmed" ? (lockComplete ? "ready to lock exact version" : `manifest incomplete (${ctx.manifest?.missing.length ?? 0} missing of ${ctx.manifest?.items.length ?? 0})`) : "confirmation required"),
    state("ASSET-01-GATE-HANDOFF", ctx.locked === "locked" && handoffComplete, ctx.locked === "locked" ? (handoffComplete ? "handoff manifest complete" : "handoff manifest incomplete (checksum/contract/rights/scorecard)") : "lock exact version first"),
    state("ASSET-01-GATE-RETRY", ctx.retryEligibility === "eligible" && ctx.job === "failed" && Boolean(ctx.route), ctx.retryEligibility === "eligible" ? (ctx.route ? `job ${ctx.job} eligible for retry via ${ctx.route}` : "route snapshot absent") : "no failed provider job"),
    state("ASSET-01-GATE-COMPARE", Boolean(ctx.compareSelection) && ctx.assets.length >= 1 && ctx.assets.length <= 3, ctx.compareSelection ? `${ctx.assets.length} selected versions` : "no compare selection"),
  ];
}

export function serializeAssetGates(states: AssetGateState[]): string {
  return JSON.stringify(states);}

export function parseAssetGates(raw: string | null | undefined): AssetGateState[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as AssetGateState[]) : [];
  } catch {
    return [];
  }
}

export function deriveAssetPageState(ctx: AssetGateContext): string {
  if (ctx.handoff === "sent") return "HANDOFF";
  if (ctx.locked === "locked") return "LOCKED";
  if (ctx.confirmed === "confirmed") return "CONFIRMED";
  if (ctx.correctionOpen === "open" && ctx.correctionApproved !== "approved") return "CORRECTION_REQUIRED";
  if (ctx.executing === "running") return "EXECUTING";
  if (ctx.scorecard && ctx.confirmed !== "confirmed") return ctx.scorecard.overall === "PASS" ? "WAIT_CONFIRMATION" : "ERROR";
  if (ctx.outputId && ctx.evaluated !== "evaluated") return "CANDIDATE_OUTPUT";
  if (ctx.project && ctx.topic && ctx.blueprint && ctx.dna && ctx.script) return "READY";
  return "LOADING";
}
