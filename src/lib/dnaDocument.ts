export const DNA_CLASSES: Record<string, string[]> = {
  STORY: [
    "premise",
    "logline",
    "genre",
    "tone",
    "theme",
    "emotional_promise",
    "conflict",
    "story_question",
    "stakes",
    "narrative_promise",
    "audience_experience",
    "boundary",
    "forbidden_changes",
    "series_expansion",
  ],
  WORLD: [
    "time_era",
    "geography",
    "locations",
    "society",
    "culture",
    "factions",
    "economy",
    "technology",
    "ability_rules",
    "religion_belief",
    "law_taboo",
    "historical_events",
    "timeline",
    "causal_rules",
    "world_constraints",
    "forbidden_contradictions",
  ],
  CHARACTER: [
    "id",
    "role",
    "goals",
    "need",
    "motivation",
    "fear",
    "weakness",
    "values",
    "moral_boundary",
    "personality",
    "behavior_decision_speech_patterns",
    "relationship_map",
    "state_arc",
    "immutable_changeable_traits",
    "appearance_equipment_ability_limits",
  ],
  NARRATIVE: [
    "pov",
    "narrative_distance",
    "story_arc_structure",
    "chapter_episode_rhythm",
    "hook",
    "escalation",
    "reveal",
    "suspense",
    "cliffhanger",
    "emotional_curve",
    "information_order",
    "foreshadow_payoff",
    "ending_pattern",
  ],
  VISUAL: [
    "art_direction",
    "character_environment_rules",
    "composition_camera_language",
    "lighting",
    "texture",
    "color",
    "motion",
    "motif_symbol",
    "subtitle_ui_compatibility",
    "forbidden_patterns",
    "reference_boundary",
  ],
  AUDIO: [
    "voice_identity",
    "music_identity",
    "atmosphere",
    "sfx_language",
    "silence_rules",
    "intensity_curve",
    "forbidden_audio_pattern",
  ],
  STRATEGY: [
    "strategy_direction",
    "objectives",
    "kpi",
    "content_role",
    "market_opportunity",
    "strategic_need",
    "revenue_growth_ip_role",
    "success_pattern",
    "risk",
    "priority",
    "evidence_confidence",
  ],
  PLATFORM: [
    "platform",
    "region",
    "language",
    "format",
    "target_duration",
    "discovery_relationship_revenue_role",
    "cta_strategy",
    "release_variant",
  ],
  ACCOUNT: [
    "account_id",
    "stage",
    "audience",
    "current_need",
    "content_territory",
    "channel_role",
    "baseline",
    "traffic_relationship",
    "cross_channel_role",
    "risk",
  ],
  PRODUCTION: [
    "quality_profile",
    "output_format",
    "aspect_ratio",
    "resolution",
    "asset_anchor_requirement",
    "provider_constraint",
    "rendering_requirements",
    "continuity_requirements",
    "cost_requirements",
    "reproducibility_requirements",
    "qa_requirements",
  ],
};

export const REQUIRED_BASE_CLASSES = ["STORY", "WORLD", "CHARACTER", "NARRATIVE"];

export const WORLD_BIBLE_FIELDS: Array<{ key: string; required: boolean }> = [
  { key: "world_name", required: true },
  { key: "era", required: false },
  { key: "geography", required: false },
  { key: "society", required: false },
  { key: "culture", required: false },
  { key: "technology", required: false },
  { key: "economy", required: false },
  { key: "politics", required: false },
  { key: "world_rules", required: true },
  { key: "supernatural_rules", required: false },
  { key: "visual_language", required: false },
  { key: "timeline", required: false },
  { key: "historical_events", required: false },
  { key: "world_conflicts", required: false },
  { key: "hard_canon", required: false },
  { key: "soft_canon", required: false },
  { key: "reference_ids", required: false },
];

export const WORLD_BIBLE_SEMANTIC_DIMENSIONS = [
  "time_era",
  "geography",
  "locations",
  "society",
  "culture",
  "factions",
  "economy",
  "technology",
  "magic_ability_rules",
  "religion_belief",
  "law_taboo",
  "historical_events",
  "timeline",
  "causal_rules",
  "world_constraints",
  "forbidden_contradictions",
];

const ZH_ALIASES: Record<string, string[]> = {
  world_name: ["世界觀名稱", "世界名稱", "作品名稱"],
  world_rules: ["世界規則", "規則", "核心規則"],
  era: ["時代背景", "時代"],
  time_era: ["時間背景", "時代背景", "時代"],
  geography: ["地理"],
  locations: ["地點", "場景地點"],
  society: ["社會"],
  culture: ["文化"],
  politics: ["政治"],
  technology: ["科技"],
  economy: ["經濟"],
  supernatural_rules: ["超自然規則"],
  visual_language: ["視覺語言"],
  timeline: ["時間線"],
  historical_events: ["歷史事件", "歷史"],
  world_conflicts: ["世界衝突"],
  hard_canon: ["硬性正典", "正典"],
  soft_canon: ["軟性正典"],
  reference_ids: ["參照清單", "引用清單"],
  factions: ["陣營", "派系"],
  ability_rules: ["能力規則"],
  religion_belief: ["信仰", "宗教"],
  law_taboo: ["律法禁忌", "禁忌"],
  causal_rules: ["因果規則"],
  world_constraints: ["世界約束", "約束"],
  forbidden_contradictions: ["禁止矛盾", "矛盾禁區"],
  premise: ["前提", "故事前提"],
  logline: ["一句話大綱", "故事梗概"],
  genre: ["類型"],
  tone: ["基調", "語調"],
  theme: ["主題"],
  emotional_promise: ["情感承諾"],
  conflict: ["衝突"],
  story_question: ["故事問題"],
  stakes: ["賭注"],
  narrative_promise: ["敘事承諾"],
  audience_experience: ["觀眾體驗"],
  forbidden_changes: ["禁止改動", "禁改"],
  series_expansion: ["系列擴展"],
  pov: ["視角", "敘事視角"],
  narrative_distance: ["敘事距離"],
  story_arc_structure: ["故事結構", "弧線結構"],
  chapter_episode_rhythm: ["章節節奏", "集數節奏"],
  hook: ["鉤子"],
  escalation: ["升級", "層層升級"],
  reveal: ["揭露", "揭示"],
  suspense: ["懸念"],
  cliffhanger: ["斷點", "懸崖邊"],
  emotional_curve: ["情感曲線"],
  information_order: ["資訊順序", "信息順序"],
  foreshadow_payoff: ["伏筆回收", "伏筆"],
  ending_pattern: ["收尾模式", "結尾模式"],
  id: ["角色編號", "角色ID"],
  role: ["角色定位", "定位"],
  goals: ["目標"],
  need: ["需求", "內在需求"],
  motivation: ["動機"],
  fear: ["恐懼"],
  weakness: ["弱點"],
  values: ["價值觀"],
  moral_boundary: ["道德底線", "底線"],
  personality: ["性格"],
  behavior_decision_speech_patterns: ["行為模式", "行為語言模式"],
  relationship_map: ["關係圖", "人物關係"],
  state_arc: ["狀態弧線", "成長弧線"],
  immutable_changeable_traits: ["可變與不可變特質", "不可變特質"],
  appearance_equipment_ability_limits: ["外觀裝備能力限制", "外觀限制"],
};

function stableHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function normalizeHeading(text: string): string {
  return text.toLowerCase().replace(/[\s_\-—–·、:：,，.。/（）()【】\[\]「」]/g, "");
}

const CLASS_HEADING_HINTS: Record<string, string[]> = {
  STORY: ["story"],
  WORLD: ["world"],
  CHARACTER: ["character"],
  NARRATIVE: ["narrative"],
  VISUAL: ["visual"],
  AUDIO: ["audio"],
  STRATEGY: ["strategy"],
  PLATFORM: ["platform"],
  ACCOUNT: ["account"],
  PRODUCTION: ["production"],
};

function matchClassHeading(heading: string): string | undefined {
  const h = normalizeHeading(heading);
  if (!h) return undefined;
  for (const [className, hints] of Object.entries(CLASS_HEADING_HINTS)) {
    if (!hints.some((hint) => h.includes(hint))) continue;
    if (h.includes("dna") || h.includes("bible")) return className;
  }
  return undefined;
}

function matchDimInClass(heading: string, className: string): string | undefined {
  const h = normalizeHeading(heading);
  for (const dim of DNA_CLASSES[className] ?? []) {
    if (h.includes(normalizeHeading(dim))) return dim;
  }
  return undefined;
}

function matchWorldField(heading: string): string | undefined {
  const h = normalizeHeading(heading);
  if (!h) return undefined;
  for (const [key, aliases] of Object.entries(ZH_ALIASES)) {
    if (aliases.some((alias) => h.includes(normalizeHeading(alias)))) return key;
  }
  for (const key of Object.keys(ZH_ALIASES)) {
    if (h.includes(normalizeHeading(key))) return key;
  }
  return undefined;
}

function excerpt(raw: string, max = 400): string {
  const text = raw.replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export type DnaExtraction = { fields: Record<string, string>; classes: Record<string, Record<string, string>> };

export function extractDnaContent(fileBodies: string[]): DnaExtraction {
  const fields: Record<string, string> = {};
  const classes: Record<string, Record<string, string>> = {};
  for (const body of fileBodies) {
    if (!body) continue;
    const lines = body.split("\n");
    let currentClass: string | null = null;
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index].trim();
      if (!line) continue;
      const isHeading = /^(#{1,5}\s+.*|\*\*.+\*\*.*|.{1,30}[:：])$/.test(line);
      if (!isHeading) continue;
      const headingText = line.replace(/^#+\s*|\*\*/g, "").trim();
      const classHeading = matchClassHeading(headingText);
      if (classHeading) {
        currentClass = classHeading;
        continue;
      }
      if (currentClass) {
        const dim = matchDimInClass(headingText, currentClass);
        if (!dim) continue;
        const contentLines: string[] = [];
        for (let cursor = index + 1; cursor < lines.length; cursor += 1) {
          const next = lines[cursor].trim();
          if (!next) {
            if (contentLines.length) break;
            continue;
          }
          if (/^(#{1,5}\s+.*|\*\*.+\*\*.*|.{1,30}[:：])$/.test(next)) break;
          contentLines.push(next);
          if (contentLines.join("").length >= 400) break;
        }
        const content = excerpt(contentLines.join(" "));
        if (!content) continue;
        if (!classes[currentClass]) classes[currentClass] = {};
        if (!classes[currentClass][dim]) classes[currentClass][dim] = content;
        continue;
      }
      const fieldKey = matchWorldField(headingText);
      if (!fieldKey) continue;
      const contentLines: string[] = [];
      for (let cursor = index + 1; cursor < lines.length; cursor += 1) {
        const next = lines[cursor].trim();
        if (!next) {
          if (contentLines.length) break;
          continue;
        }
        if (/^(#{1,5}\s+.*|\*\*.+\*\*.*|.{1,30}[:：])$/.test(next)) break;
        contentLines.push(next);
        if (contentLines.join("").length >= 400) break;
      }
      const content = excerpt(contentLines.join(" "));
      if (!content) continue;
      if (!fields[fieldKey]) fields[fieldKey] = content;
    }
  }
  return { fields, classes };
}

export type WorldBibleVersion = {
  kind: "WORLD_BIBLE";
  world_bible_id: string;
  version: string;
  project_id: string;
  fields: Record<string, string>;
  missing_required: string[];
  hash: string;
  created_at: string;
};

export function buildWorldBible(project: string, fields: Record<string, string>, createdAt: string): WorldBibleVersion {
  const picked: Record<string, string> = {};
  for (const { key } of WORLD_BIBLE_FIELDS) {
    const value = fields[key];
    if (typeof value === "string" && value.trim()) picked[key] = value.trim();
  }
  const missing_required = WORLD_BIBLE_FIELDS.filter((field) => field.required && !picked[field.key]).map((field) => field.key);
  const hash = stableHash([project, ...WORLD_BIBLE_FIELDS.map((field) => `${field.key}=${picked[field.key] ?? ""}`)]);
  return {
    kind: "WORLD_BIBLE",
    world_bible_id: `WB-${hash}`,
    version: `WBV-${hash}`,
    project_id: project,
    fields: picked,
    missing_required,
    hash,
    created_at: createdAt,
  };
}

export type BaseDnaVersion = {
  kind: "BASE_DNA";
  base_dna_id: string;
  version: string;
  project_id: string;
  status: "CANDIDATE" | "LOCKED";
  world_bible: WorldBibleVersion | null;
  classes: Record<string, Record<string, string>>;
  covered: Record<string, string[]>;
  missing: Record<string, string[]>;
  source_files: string[];
  prior_version_ref: string;
  change_summary: string;
  reviewer_ref: string;
  locked_at: string;
  coverage_gaps: string[];
  hash: string;
  created_at: string;
};

export function buildBaseDna(input: {
  project: string;
  fileBodies: string[];
  sourceFiles?: string[];
  priorVersionRef?: string;
  changeSummary?: string;
  status?: "CANDIDATE" | "LOCKED";
  reviewerRef?: string;
  createdAt: string;
}): BaseDnaVersion {
  const extraction = extractDnaContent(input.fileBodies);
  const classes: Record<string, Record<string, string>> = {};
  const covered: Record<string, string[]> = {};
  const missing: Record<string, string[]> = {};
  for (const [className, dims] of Object.entries(DNA_CLASSES)) {
    classes[className] = {};
    covered[className] = [];
    missing[className] = [];
    for (const dim of dims) {
      const content = extraction.classes[className]?.[dim] ?? (className === "WORLD" ? extraction.fields[dim] : "");
      if (content) {
        classes[className][dim] = content;
        covered[className].push(dim);
      } else {
        missing[className].push(dim);
      }
    }
  }
  const worldBible = buildWorldBible(input.project, extraction.fields, input.createdAt);
  const coverageGaps: string[] = [];
  if (!input.fileBodies.length) coverageGaps.push("no_dna_thread_files");
  if (worldBible.missing_required.length) coverageGaps.push(`world_bible_missing:${worldBible.missing_required.join(",")}`);
  const hash = stableHash([
    input.project,
    worldBible.hash,
    ...Object.entries(classes).flatMap(([className, content]) => [className, stableHash(Object.entries(content).map(([k, v]) => `${k}=${v}`))]),
    input.priorVersionRef ?? "",
  ]);
  return {
    kind: "BASE_DNA",
    base_dna_id: `DNA-${hash}`,
    version: `DNAV-${hash}`,
    project_id: input.project,
    status: input.status ?? "CANDIDATE",
    world_bible: worldBible,
    classes,
    covered,
    missing,
    source_files: input.sourceFiles ?? [],
    prior_version_ref: input.priorVersionRef ?? "",
    change_summary: input.changeSummary ?? "",
    reviewer_ref: input.reviewerRef ?? "",
    locked_at: input.status === "LOCKED" ? input.createdAt : "",
    coverage_gaps: coverageGaps,
    hash,
    created_at: input.createdAt,
  };
}

export function parseBaseDna(raw: string | null | undefined): BaseDnaVersion | undefined {
  if (!raw || !raw.trim().startsWith("{")) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;
    const rec = parsed as Record<string, unknown>;
    if (rec.kind !== "BASE_DNA") return undefined;
    const version = typeof rec.version === "string" ? rec.version.trim() : "";
    const hash = typeof rec.hash === "string" ? rec.hash.trim() : "";
    if (!version || !hash) return undefined;
    const text = (key: string) => (typeof rec[key] === "string" ? String(rec[key]).trim() : "");
    const classes: Record<string, Record<string, string>> = {};
    if (rec.classes && typeof rec.classes === "object") {
      for (const [className, dims] of Object.entries(rec.classes as Record<string, unknown>)) {
        if (!dims || typeof dims !== "object") continue;
        classes[className] = {};
        for (const [dim, content] of Object.entries(dims as Record<string, unknown>)) {
          if (typeof content === "string" && content.trim()) classes[className][dim] = content.trim();
        }
      }
    }
    const wb = rec.world_bible && typeof rec.world_bible === "object" ? (rec.world_bible as Record<string, unknown>) : undefined;
    const worldBible: WorldBibleVersion | null = wb
      ? {
          kind: "WORLD_BIBLE",
          world_bible_id: typeof wb.world_bible_id === "string" ? wb.world_bible_id : "",
          version: typeof wb.version === "string" ? wb.version : "",
          project_id: typeof wb.project_id === "string" ? wb.project_id : "",
          fields: wb.fields && typeof wb.fields === "object" ? (wb.fields as Record<string, string>) : {},
          missing_required: Array.isArray(wb.missing_required) ? wb.missing_required.filter((row): row is string => typeof row === "string") : [],
          hash: typeof wb.hash === "string" ? wb.hash : "",
          created_at: typeof wb.created_at === "string" ? wb.created_at : "",
        }
      : null;
    const stringList = (value: unknown) => (Array.isArray(value) ? value.filter((row): row is string => typeof row === "string") : []);
    return {
      kind: "BASE_DNA",
      base_dna_id: text("base_dna_id"),
      version,
      project_id: text("project_id"),
      status: rec.status === "LOCKED" ? "LOCKED" : "CANDIDATE",
      world_bible: worldBible,
      classes,
      covered: sanitizeCovered(rec.covered, classes),
      missing: sanitizeMissing(rec.missing),
      source_files: stringList(rec.source_files),
      prior_version_ref: text("prior_version_ref"),
      change_summary: text("change_summary"),
      reviewer_ref: text("reviewer_ref"),
      locked_at: text("locked_at"),
      coverage_gaps: stringList(rec.coverage_gaps),
      hash,
      created_at: text("created_at"),
    };
  } catch {
    return undefined;
  }
}

function sanitizeCovered(value: unknown, classes: Record<string, Record<string, string>>): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  const rec = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  for (const className of Object.keys(DNA_CLASSES)) {
    const list = Array.isArray(rec[className]) ? rec[className].filter((row): row is string => typeof row === "string") : [];
    out[className] = list.length ? list : Object.keys(classes[className] ?? {});
  }
  return out;
}

function sanitizeMissing(value: unknown): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  const rec = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  for (const className of Object.keys(DNA_CLASSES)) {
    const list = Array.isArray(rec[className]) ? rec[className].filter((row): row is string => typeof row === "string") : [];
    out[className] = list;
  }
  return out;
}

export function withDnaStatus(doc: BaseDnaVersion, status: "CANDIDATE" | "LOCKED", reviewerRef: string, at: string): BaseDnaVersion {
  return { ...doc, status, reviewer_ref: reviewerRef || doc.reviewer_ref, locked_at: status === "LOCKED" ? at : "" };
}

export function dnaRequiredMissing(doc: BaseDnaVersion): string[] {
  const out: string[] = [];
  for (const className of REQUIRED_BASE_CLASSES) {
    const missing = doc.missing[className] ?? [];
    if (missing.length) out.push(`${className}:${missing.join(",")}`);
  }
  if (doc.world_bible?.missing_required.length) out.push(`WORLD_BIBLE:${doc.world_bible.missing_required.join(",")}`);
  return out;
}

const DNA_STATUS_TOKENS = new Set([
  "locked",
  "created",
  "confirmed",
  "validated",
  "approved",
  "sent",
  "returned",
  "recorded",
  "comparing",
  "evaluated",
  "ready",
  "rejected",
]);

export function dnaExactRef(value: string | null | undefined): string {
  const raw = value?.trim() ?? "";
  if (!raw || DNA_STATUS_TOKENS.has(raw)) return "";
  if (raw.startsWith("{")) {
    const doc = parseBaseDna(raw);
    if (doc) return doc.version;
    return "";
  }
  return raw.slice(0, 80);
}

export type DnaEnrichment = {
  kind: "DNA_ENRICHMENT";
  base_dna_ref: string;
  topic_id: string;
  prior_version_ref: string;
  enriched_classes: string[];
  hash: string;
};

export function buildDnaEnrichment(base: BaseDnaVersion, input: { topic: string; priorVersionRef?: string }): DnaEnrichment {
  const enrichedClasses = Object.keys(base.classes).filter((className) => (base.covered[className] ?? []).length > 0);
  const hash = stableHash([base.version, input.topic, input.priorVersionRef ?? "", enrichedClasses.join(",")]);
  return {
    kind: "DNA_ENRICHMENT",
    base_dna_ref: base.version,
    topic_id: input.topic,
    prior_version_ref: input.priorVersionRef ?? "",
    enriched_classes: enrichedClasses,
    hash,
  };
}

export function parseDnaEnrichmentField(value: unknown): DnaEnrichment | undefined {
  if (!value || typeof value !== "object") return undefined;
  const rec = value as Record<string, unknown>;
  if (rec.kind !== "DNA_ENRICHMENT" || typeof rec.base_dna_ref !== "string") return undefined;
  return {
    kind: "DNA_ENRICHMENT",
    base_dna_ref: rec.base_dna_ref,
    topic_id: typeof rec.topic_id === "string" ? rec.topic_id : "",
    prior_version_ref: typeof rec.prior_version_ref === "string" ? rec.prior_version_ref : "",
    enriched_classes: Array.isArray(rec.enriched_classes) ? rec.enriched_classes.filter((row): row is string => typeof row === "string") : [],
    hash: typeof rec.hash === "string" ? rec.hash : "",
  };
}

export function serializeBaseDna(doc: BaseDnaVersion): string {
  return JSON.stringify(doc);
}

export function formatDnaDigest(doc: BaseDnaVersion): string {
  const lines = [
    `${doc.status === "LOCKED" ? "已鎖定" : "候選"} DNA ${doc.version} / hash ${doc.hash}`,
    `世界觀 ${doc.world_bible ? `${doc.world_bible.version}${doc.world_bible.missing_required.length ? `（缺必填：${doc.world_bible.missing_required.join("、")}）` : "（必填齊）"}` : "缺席"}`,
  ];
  for (const className of Object.keys(DNA_CLASSES)) {
    const covered = (doc.covered[className] ?? []).length;
    const total = DNA_CLASSES[className].length;
    const mark = REQUIRED_BASE_CLASSES.includes(className) ? "必" : "選";
    lines.push(`  ${mark} ${className} ${covered}/${total}`);
  }
  if (doc.coverage_gaps.length) lines.push(`覆蓋缺口：${doc.coverage_gaps.join("、")}`);
  return lines.join("\n");
}
