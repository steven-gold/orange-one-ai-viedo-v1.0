import type { CanonicalScriptProjection } from "./coreActionPreview";

export const MACHINE_SCHEMA = "MSS-1";

export type ScriptBeat = { beat_id: string; action: string; dialogue: string; narration: string };
export type ScriptScene = { scene_id: string; title: string; beats: ScriptBeat[] };
export type ScriptBoundary = {
  tension_state: string;
  hook_intent: string;
  curiosity_gap: string;
  cut_setup: string;
  visual_buildup: string;
  audio_buildup: string;
  withheld: string;
  open_loop: string;
  expected_audience_effect: string;
  next_content_pull: string;
  next_start_state: string;
  payoff_target: string;
};
export type ScriptContinuity = {
  starting_state: string;
  ending_state: string;
  unresolved_refs: string;
  payoff_refs: string;
};
export type MachineScript = {
  kind: "MACHINE_SCRIPT";
  schema: string;
  canonical_script_version_ref: string;
  input_hash: string;
  producer: string;
  generated_at: string;
  output_hash: string;
  scene_count: number;
  ordering: string[];
  constraints_preserved: boolean;
};
export type MediaView = { view: "ASSET" | "VIDEO" | "EDIT"; view_ref: string; items: Array<{ ref: string; requirement: string }> };
export type MediaViews = { kind: "MEDIA_VIEWS"; canonical_script_version_ref: string; views: MediaView[]; output_hash: string };

function stableHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function excerpt(raw: string, max = 160): string {
  const text = raw.replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

const SCENE_HEADING = /^(#{1,4}\s*)?(第?\s*\d+\s*[集章話话幕回]|(?:Scene|SCENE|场景|場景)\s*\d+|EP\s*\d+)\s*[^\n]{0,40}$/;

export function parseScriptScenes(body: string, cap = 40): ScriptScene[] {
  const lines = body.split("\n");
  const scenes: ScriptScene[] = [];
  let current: ScriptScene | null = null;
  for (const line of lines) {
    const text = line.trim();
    if (!text) continue;
    const heading = SCENE_HEADING.test(text.replace(/^#+\s*/, "").trim()) ? text.replace(/^#+\s*/, "").trim() : "";
    if (heading) {
      if (scenes.length >= cap) break;
      const sceneId = `S${scenes.length + 1}`;
      current = { scene_id: sceneId, title: excerpt(heading, 60), beats: [] };
      scenes.push(current);
      continue;
    }
    if (!current) {
      if (scenes.length >= cap) break;
      current = { scene_id: `S${scenes.length + 1}`, title: excerpt(text, 60), beats: [] };
      scenes.push(current);
      continue;
    }
    if (current.beats.length >= 12) continue;
    const isDialogue = /^[—–-]\s*[^\n]{1,80}[:：]/.test(text) || /^[「『]/.test(text);
    const isNarration = /^(旁白|獨白|NARRATION)[:：]/.test(text);
    const beat: ScriptBeat = {
      beat_id: `${current.scene_id}-B${current.beats.length + 1}`,
      action: isDialogue || isNarration ? "" : excerpt(text),
      dialogue: isDialogue ? excerpt(text) : "",
      narration: isNarration ? excerpt(text) : "",
    };
    current.beats.push(beat);
  }
  return scenes;
}

function boundaryFrom(scenes: ScriptScene[]): ScriptBoundary {
  const last = scenes[scenes.length - 1];
  const lastBeat = last?.beats[last.beats.length - 1];
  const tail = lastBeat?.narration || lastBeat?.dialogue || lastBeat?.action || last?.title || "";
  return {
    tension_state: "",
    hook_intent: "",
    curiosity_gap: "",
    cut_setup: "",
    visual_buildup: "",
    audio_buildup: "",
    withheld: "",
    open_loop: "",
    expected_audience_effect: "",
    next_content_pull: tail ? excerpt(tail, 80) : "",
    next_start_state: last?.title || "",
    payoff_target: "",
  };
}

function continuityFrom(scenes: ScriptScene[]): ScriptContinuity {
  const first = scenes[0];
  const last = scenes[scenes.length - 1];
  const markers = (text: string) => (/(待續|未解|伏筆|payoff|open loop)/i.test(text) ? excerpt(text, 120) : "");
  const unresolved = scenes
    .flatMap((scene) => scene.beats.map((beat) => beat.action || beat.dialogue || beat.narration))
    .map(markers)
    .filter(Boolean)
    .slice(0, 3)
    .join("、");
  return {
    starting_state: first ? excerpt(`${first.title} ${first.beats[0]?.action || ""}`, 120) : "",
    ending_state: last ? excerpt(`${last.title} ${last.beats[last.beats.length - 1]?.action || ""}`, 120) : "",
    unresolved_refs: unresolved,
    payoff_refs: "",
  };
}

export function buildMachineScript(projection: CanonicalScriptProjection, generatedAt: string): MachineScript {
  const scenes = projection.structure?.scenes ?? [];
  const base = {
    kind: "MACHINE_SCRIPT" as const,
    schema: MACHINE_SCHEMA,
    canonical_script_version_ref: projection.version,
    input_hash: projection.hash,
    producer: "ACPOS-CORE",
    generated_at: generatedAt,
    scene_count: scenes.length,
    ordering: scenes.map((scene) => scene.scene_id),
    constraints_preserved: true,
  };
  const outputHash = stableHash([
    base.schema,
    base.canonical_script_version_ref,
    base.input_hash,
    base.scene_count.toString(),
    base.ordering.join(","),
  ]);
  return { ...base, output_hash: outputHash };
}

export function buildMediaViews(projection: CanonicalScriptProjection): MediaViews {
  const scenes = projection.structure?.scenes ?? [];
  const refHash = stableHash([projection.version, scenes.map((scene) => scene.scene_id).join(",")]);
  const views: MediaView[] = [
    {
      view: "ASSET",
      view_ref: `VIEW-${refHash}-ASSET`,
      items: scenes.slice(0, 20).map((scene) => ({ ref: scene.scene_id, requirement: scene.title })),
    },
    {
      view: "VIDEO",
      view_ref: `VIEW-${refHash}-VIDEO`,
      items: scenes.slice(0, 20).map((scene, index) => ({ ref: scene.scene_id, requirement: `鏡頭序 ${index + 1}` })),
    },
    {
      view: "EDIT",
      view_ref: `VIEW-${refHash}-EDIT`,
      items: scenes.slice(0, 20).map((scene) => ({
        ref: scene.scene_id,
        requirement: scene.beats.length ? `${scene.beats[0].beat_id}…${scene.beats[scene.beats.length - 1].beat_id}` : scene.scene_id,
      })),
    },
  ];
  const outputHash = stableHash([projection.version, ...views.map((view) => `${view.view}:${view.items.length}`)]);
  return { kind: "MEDIA_VIEWS", canonical_script_version_ref: projection.version, views, output_hash: outputHash };
}

export function buildEnrichedProjection(
  base: CanonicalScriptProjection,
  input: { fileBody?: string; priorVersionRef?: string; changeSummary?: string; reviewerRef?: string; generatedAt?: string },
): CanonicalScriptProjection {
  const generatedAt = input.generatedAt ?? new Date().toISOString().slice(0, 19).replace("T", " ");
  const scenes = input.fileBody ? parseScriptScenes(input.fileBody) : base.structure?.scenes ?? [];
  const withStructure: CanonicalScriptProjection = {
    ...base,
    structure: scenes.length ? { scenes, boundary: boundaryFrom(scenes) } : base.structure,
    continuity: continuityFrom(scenes),
    change_summary: input.changeSummary ?? base.change_summary ?? "",
    prior_version_ref: input.priorVersionRef ?? base.prior_version_ref ?? "",
    audit: {
      human_decision: "confirmed",
      candidate_ref: base.source_candidate_ref,
      reviewer_ref: input.reviewerRef ?? base.audit?.reviewer_ref ?? "",
      decided_at: generatedAt,
    },
  };
  return {
    ...withStructure,
    machine: buildMachineScript(withStructure, generatedAt),
    views: buildMediaViews(withStructure),
    coverage_gaps: scenes.length ? [] : ["scene_structure_unavailable"],
  };
}

export function parseMachineScriptField(value: unknown): MachineScript | undefined {
  if (!value || typeof value !== "object") return undefined;
  const rec = value as Record<string, unknown>;
  if (rec.kind !== "MACHINE_SCRIPT" || typeof rec.schema !== "string") return undefined;
  const text = (key: string) => (typeof rec[key] === "string" ? String(rec[key]).trim() : "");
  const number = (key: string) => (typeof rec[key] === "number" ? rec[key] : 0);
  const ordering = Array.isArray(rec.ordering) ? rec.ordering.filter((row): row is string => typeof row === "string") : [];
  return {
    kind: "MACHINE_SCRIPT",
    schema: rec.schema,
    canonical_script_version_ref: text("canonical_script_version_ref"),
    input_hash: text("input_hash"),
    producer: text("producer"),
    generated_at: text("generated_at"),
    output_hash: text("output_hash"),
    scene_count: number("scene_count"),
    ordering,
    constraints_preserved: rec.constraints_preserved === true,
  };
}

export function parseMediaViewsField(value: unknown): MediaViews | undefined {
  if (!value || typeof value !== "object") return undefined;
  const rec = value as Record<string, unknown>;
  if (rec.kind !== "MEDIA_VIEWS" || !Array.isArray(rec.views)) return undefined;
  const views: MediaView[] = [];
  for (const row of rec.views) {
    if (!row || typeof row !== "object") continue;
    const item = row as Record<string, unknown>;
    if (item.view !== "ASSET" && item.view !== "VIDEO" && item.view !== "EDIT") continue;
    if (typeof item.view_ref !== "string" || !Array.isArray(item.items)) continue;
    views.push({
      view: item.view,
      view_ref: item.view_ref,
      items: item.items
        .filter((entry): entry is Record<string, unknown> => Boolean(entry) && typeof entry === "object")
        .map((entry) => ({ ref: String(entry.ref ?? ""), requirement: String(entry.requirement ?? "") }))
        .filter((entry) => entry.ref),
    });
  }
  if (!views.length) return undefined;
  return {
    kind: "MEDIA_VIEWS",
    canonical_script_version_ref: typeof rec.canonical_script_version_ref === "string" ? rec.canonical_script_version_ref : "",
    views,
    output_hash: typeof rec.output_hash === "string" ? rec.output_hash : "",
  };
}

export function parseScenesField(value: unknown): ScriptScene[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const scenes: ScriptScene[] = [];
  for (const row of value) {
    if (!row || typeof row !== "object") continue;
    const rec = row as Record<string, unknown>;
    if (typeof rec.scene_id !== "string" || typeof rec.title !== "string") continue;
    const beats = Array.isArray(rec.beats)
      ? rec.beats
          .filter((beat): beat is Record<string, unknown> => Boolean(beat) && typeof beat === "object")
          .map((beat) => ({
            beat_id: String(beat.beat_id ?? ""),
            action: String(beat.action ?? ""),
            dialogue: String(beat.dialogue ?? ""),
            narration: String(beat.narration ?? ""),
          }))
      : [];
    scenes.push({ scene_id: rec.scene_id, title: rec.title, beats });
  }
  return scenes.length ? scenes : undefined;
}

export function appendDecisionLog(
  raw: string | null | undefined,
  entry: { at: string; actor: "HUMAN" | "ASSISTANT"; decision: string },
): string {
  let entries: Array<{ at: string; actor: string; decision: string }> = [];
  try {
    const parsed = JSON.parse(raw ?? "") as unknown;
    if (
      parsed &&
      typeof parsed === "object" &&
      (parsed as Record<string, unknown>).kind === "CORE_DECISION_LOG" &&
      Array.isArray((parsed as Record<string, unknown>).entries)
    ) {
      entries = ((parsed as Record<string, unknown>).entries as Array<Record<string, unknown>>)
        .filter((row) => row && typeof row === "object")
        .map((row) => ({ at: String(row.at ?? ""), actor: String(row.actor ?? ""), decision: String(row.decision ?? "") }))
        .slice(-19);
    }
  } catch {
    entries = [];
  }
  entries.push(entry);
  return JSON.stringify({ kind: "CORE_DECISION_LOG", entries });
}

export function formatScriptViewDigest(projection: CanonicalScriptProjection): string {
  const lines = [
    `正典腳本 ${projection.canonical_script_id} / ${projection.version}`,
    `專案 ${projection.project_id} / 專題 ${projection.topic_id}`,
    `藍圖 ${projection.blueprint_ref || "—"} / DNA ${projection.dna_ref || "—"} / hash ${projection.hash}`,
  ];
  const scenes = projection.structure?.scenes ?? [];
  if (scenes.length) {
    lines.push(`結構：${scenes.length} 場景（邊界起點 ${projection.structure?.boundary?.next_start_state || "—"}）`);
    for (const scene of scenes.slice(0, 6)) {
      lines.push(`  ${scene.scene_id} ${scene.title}（${scene.beats.length} 節拍）`);
    }
    if (scenes.length > 6) lines.push(`  …其餘 ${scenes.length - 6} 場景省略`);
  } else {
    lines.push("結構：無場景可解析（coverage gap）");
  }
  if (projection.continuity) {
    lines.push(
      `續接：起 ${projection.continuity.starting_state || "—"} → 迄 ${projection.continuity.ending_state || "—"}`,
    );
    if (projection.continuity.unresolved_refs) lines.push(`未解鉤子：${projection.continuity.unresolved_refs}`);
  }
  if (projection.machine) {
    lines.push(`機器腳本 ${projection.machine.schema} / 輸出hash ${projection.machine.output_hash} / 場景 ${projection.machine.scene_count}`);
  }
  if (projection.views) {
    lines.push(projection.views.views.map((view) => `${view.view} ${view.view_ref}(${view.items.length})`).join("、"));
  }
  if (projection.change_summary) lines.push(`變更：${projection.change_summary}`);
  if (projection.prior_version_ref) lines.push(`前版：${projection.prior_version_ref}`);
  return lines.join("\n");
}
