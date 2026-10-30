import { extractDnaContent } from "./dnaDocument";

export const STORY_CORE_FIELDS = [
  "core_premise",
  "logline",
  "genre",
  "tone",
  "theme",
  "emotional_promise",
  "core_conflict",
  "central_story_question",
  "stakes",
  "narrative_promise",
  "audience_experience",
  "story_boundary",
  "forbidden_changes",
  "series_expansion_logic",
] as const;

export type StoryCoreField = (typeof STORY_CORE_FIELDS)[number];

const STORY_CORE_ALIASES: Record<string, string[]> = {
  core_premise: ["核心前提", "故事前提", "前提", "premise"],
  logline: ["一句話大綱", "故事梗概", "梗概", "logline"],
  genre: ["類型", "genre"],
  tone: ["基調", "語調", "tone"],
  theme: ["主題", "theme"],
  emotional_promise: ["情感承諾", "emotional promise"],
  core_conflict: ["核心衝突", "主要衝突", "衝突", "conflict"],
  central_story_question: ["核心故事問題", "中心問題", "故事問題", "story question"],
  stakes: ["賭注", "stakes"],
  narrative_promise: ["敘事承諾", "narrative promise"],
  audience_experience: ["觀眾體驗", "受眾體驗", "audience experience"],
  story_boundary: ["故事邊界", "邊界", "boundary"],
  forbidden_changes: ["禁止改動", "禁改", "forbidden changes"],
  series_expansion_logic: ["系列擴展", "系列擴展邏輯", "series expansion"],
};

function normalizeHeading(text: string): string {
  return text.toLowerCase().replace(/[\s_\-—–·、:：,，.。/（）()【】\[\]「」]/g, "");
}

function matchStoryField(heading: string): string | undefined {
  const h = normalizeHeading(heading);
  if (!h) return undefined;
  for (const [key, aliases] of Object.entries(STORY_CORE_ALIASES)) {
    if (aliases.some((alias) => h.includes(normalizeHeading(alias)))) return key;
  }
  return undefined;
}

function excerpt(raw: string, max = 400): string {
  const text = raw.replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function collectUntilNextHeading(lines: string[], start: number): string {
  const contentLines: string[] = [];
  for (let cursor = start; cursor < lines.length; cursor += 1) {
    const next = lines[cursor].trim();
    if (!next) {
      if (contentLines.length) break;
      continue;
    }
    if (/^(#{1,5}\s+.*|\*\*.+\*\*.*|.{1,30}[:：])$/.test(next)) break;
    contentLines.push(next);
    if (contentLines.join("").length >= 400) break;
  }
  return excerpt(contentLines.join(" "));
}

export function extractStoryCoreContent(fileBodies: string[]): Record<string, string> {
  const fields: Record<string, string> = {};
  const put = (key: string, value: string) => {
    if (value && !fields[key]) fields[key] = value;
  };
  for (const body of fileBodies) {
    if (!body) continue;
    const lines = body.split("\n");
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index].trim();
      if (!line) continue;
      const stripped = line.replace(/^#+\s*/, "");
      const inlineMatch = stripped.match(/^([^:：]{1,20})[:：]\s*(.+)$/);
      if (inlineMatch) {
        const fieldKey = matchStoryField(inlineMatch[1]);
        if (fieldKey) put(fieldKey, excerpt(inlineMatch[2]));
        continue;
      }
      const isHeading = /^(#{1,5}\s+.*|\*\*.+\*\*.*|.{1,30}[:：])$/.test(line);
      if (!isHeading) continue;
      const headingText = line.replace(/^#+\s*|\*\*/g, "").trim();
      const fieldKey = matchStoryField(headingText);
      if (fieldKey) put(fieldKey, collectUntilNextHeading(lines, index + 1));
    }
  }
  const inline = extractDnaContent(fileBodies);
  const dnaStory = inline.classes.STORY ?? {};
  const bridge: Record<string, string> = {
    premise: "core_premise",
    conflict: "core_conflict",
    story_question: "central_story_question",
    boundary: "story_boundary",
    series_expansion: "series_expansion_logic",
  };
  for (const [dim, content] of Object.entries(dnaStory)) {
    const key = (STORY_CORE_FIELDS as readonly string[]).includes(dim) ? dim : bridge[dim];
    if (key) put(key, content);
  }
  for (const [dim, content] of Object.entries(inline.fields)) {
    const key = (STORY_CORE_FIELDS as readonly string[]).includes(dim) ? dim : bridge[dim];
    if (key) put(key, content);
  }
  return fields;
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

export type StoryCoreVersion = {
  kind: "STORY_CORE";
  story_core_id: string;
  version: string;
  project_id: string;
  status: "CANDIDATE" | "LOCKED";
  fields: Record<string, string>;
  covered: string[];
  missing: string[];
  source_files: string[];
  prior_version_ref: string;
  change_summary: string;
  reviewer_ref: string;
  locked_at: string;
  coverage_gaps: string[];
  hash: string;
  created_at: string;
};

export function buildStoryCore(input: {
  project: string;
  fileBodies: string[];
  sourceFiles?: string[];
  priorVersionRef?: string;
  changeSummary?: string;
  status?: "CANDIDATE" | "LOCKED";
  reviewerRef?: string;
  createdAt: string;
}): StoryCoreVersion {
  const extraction = extractStoryCoreContent(input.fileBodies);
  const fields: Record<string, string> = {};
  const covered: string[] = [];
  const missing: string[] = [];
  for (const key of STORY_CORE_FIELDS) {
    const content = extraction[key];
    if (content) {
      fields[key] = content;
      covered.push(key);
    } else {
      missing.push(key);
    }
  }
  const coverageGaps: string[] = [];
  if (!input.fileBodies.length) coverageGaps.push("no_story_thread_files");
  const hash = stableHash([input.project, ...STORY_CORE_FIELDS.map((key) => `${key}=${fields[key] ?? ""}`), input.priorVersionRef ?? ""]);
  return {
    kind: "STORY_CORE",
    story_core_id: `SC-${hash}`,
    version: `SCV-${hash}`,
    project_id: input.project,
    status: input.status ?? "CANDIDATE",
    fields,
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

function sanitizeStringRecord(value: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (!value || typeof value !== "object") return out;
  for (const [key, content] of Object.entries(value as Record<string, unknown>)) {
    if (typeof content === "string" && content.trim()) out[key] = content.trim();
  }
  return out;
}

export function parseStoryCore(raw: string | null | undefined): StoryCoreVersion | undefined {
  if (!raw || !raw.trim().startsWith("{")) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;
    const rec = parsed as Record<string, unknown>;
    if (rec.kind !== "STORY_CORE") return undefined;
    const version = typeof rec.version === "string" ? rec.version.trim() : "";
    const hash = typeof rec.hash === "string" ? rec.hash.trim() : "";
    if (!version || !hash) return undefined;
    const text = (key: string) => (typeof rec[key] === "string" ? String(rec[key]).trim() : "");
    const stringList = (value: unknown) => (Array.isArray(value) ? value.filter((row): row is string => typeof row === "string") : []);
    const fields = sanitizeStringRecord(rec.fields);
    return {
      kind: "STORY_CORE",
      story_core_id: text("story_core_id"),
      version,
      project_id: text("project_id"),
      status: rec.status === "LOCKED" ? "LOCKED" : "CANDIDATE",
      fields,
      covered: stringList(rec.covered).length ? stringList(rec.covered) : STORY_CORE_FIELDS.filter((key) => fields[key]),
      missing: stringList(rec.missing),
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

export function serializeStoryCore(doc: StoryCoreVersion): string {
  return JSON.stringify(doc);
}

export function withStoryCoreStatus(doc: StoryCoreVersion, status: "CANDIDATE" | "LOCKED", reviewerRef: string, at: string): StoryCoreVersion {
  return { ...doc, status, reviewer_ref: reviewerRef || doc.reviewer_ref, locked_at: status === "LOCKED" ? at : "" };
}

export function storyCoreRequiredMissing(doc: StoryCoreVersion): string[] {
  return STORY_CORE_FIELDS.filter((key) => !doc.fields[key]);
}

export const STORY_CORE_STATUS_TOKENS = new Set([
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

export function storyCoreExactRef(value: string | null | undefined): string {
  const raw = value?.trim() ?? "";
  if (!raw || STORY_CORE_STATUS_TOKENS.has(raw)) return "";
  if (raw.startsWith("{")) {
    const doc = parseStoryCore(raw);
    return doc ? doc.version : "";
  }
  return raw.slice(0, 80);
}

export function formatStoryCoreDigest(doc: StoryCoreVersion): string {
  const lines = [
    `${doc.status === "LOCKED" ? "已鎖定" : "候選"} 故事核心 ${doc.version} / hash ${doc.hash}`,
    `欄位覆蓋 ${doc.covered.length}/${STORY_CORE_FIELDS.length}`,
  ];
  if (doc.missing.length) lines.push(`缺：${doc.missing.join("、")}`);
  if (doc.coverage_gaps.length) lines.push(`覆蓋缺口：${doc.coverage_gaps.join("、")}`);
  return lines.join("\n");
}

export const CHAPTER_FIELDS: Array<{ key: string; required: boolean }> = [
  { key: "chapter_number", required: true },
  { key: "title", required: true },
  { key: "chapter_goal", required: true },
  { key: "opening_hook", required: false },
  { key: "main_conflict", required: true },
  { key: "character_progress", required: false },
  { key: "world_reveal", required: false },
  { key: "turning_point", required: false },
  { key: "climax", required: false },
  { key: "resolution", required: false },
  { key: "ending_hook", required: false },
  { key: "foreshadowing", required: false },
  { key: "payoff_refs", required: false },
  { key: "production_complexity", required: true },
];

export const CHAPTER_REQUIRED_FIELDS = CHAPTER_FIELDS.filter((field) => field.required).map((field) => field.key);

export type ChapterEntry = {
  chapter_number: number;
  title: string;
  chapter_goal: string;
  opening_hook?: string;
  main_conflict: string;
  character_progress?: string;
  world_reveal?: string;
  turning_point?: string;
  climax?: string;
  resolution?: string;
  ending_hook?: string;
  foreshadowing?: string;
  payoff_refs?: string;
  production_complexity: string;
};

const CHAPTER_ALIASES: Record<string, string[]> = {
  title: ["標題", "章名", "title"],
  chapter_goal: ["章節目標", "目標", "goal"],
  opening_hook: ["開場鉤子", "開場", "hook"],
  main_conflict: ["主要衝突", "核心衝突", "衝突", "conflict"],
  character_progress: ["角色進展", "人物進展"],
  world_reveal: ["世界揭露", "世界觀揭露"],
  turning_point: ["轉折點", "轉折"],
  climax: ["高潮"],
  resolution: ["收束", "解決"],
  ending_hook: ["結尾鉤子", "結尾", "下集鉤子"],
  foreshadowing: ["伏筆"],
  payoff_refs: ["回收參照", "回收"],
  production_complexity: ["製作複雜度", "複雜度"],
};

function matchChapterField(heading: string): string | undefined {
  const h = normalizeHeading(heading);
  if (!h) return undefined;
  for (const [key, aliases] of Object.entries(CHAPTER_ALIASES)) {
    if (aliases.some((alias) => h.includes(normalizeHeading(alias)))) return key;
  }
  return undefined;
}

const CHAPTER_HEADING = /^(?:第\s*(\d+)\s*[章集回話]|EP\.?\s*(\d+)|Chapter\s*(\d+))\s*[:：\-–—]?\s*(.*)$/i;

export type ChapterExtraction = { chapters: Array<Partial<ChapterEntry> & { chapter_number: number }> };

export function extractChapterArchitecture(fileBodies: string[]): ChapterExtraction {
  const chapters: Array<Partial<ChapterEntry> & { chapter_number: number }> = [];
  const byNumber = new Map<number, Partial<ChapterEntry> & { chapter_number: number }>();
  const touch = (number: number): Partial<ChapterEntry> & { chapter_number: number } => {
    const existing = byNumber.get(number);
    if (existing) return existing;
    const created = { chapter_number: number } as Partial<ChapterEntry> & { chapter_number: number };
    byNumber.set(number, created);
    chapters.push(created);
    return created;
  };
  const put = (entry: Partial<ChapterEntry>, key: string, value: string) => {
    if (!value) return;
    const rec = entry as Record<string, unknown>;
    if (typeof rec[key] !== "string" || !rec[key]) rec[key] = value;
  };
  for (const body of fileBodies) {
    if (!body) continue;
    const lines = body.split("\n");
    let current: (Partial<ChapterEntry> & { chapter_number: number }) | null = null;
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index].trim();
      if (!line) continue;
      const chapterMatch = line.replace(/^#+\s*/, "").match(CHAPTER_HEADING);
      if (chapterMatch) {
        const number = Number(chapterMatch[1] ?? chapterMatch[2] ?? chapterMatch[3] ?? 0);
        if (!Number.isFinite(number) || number <= 0) continue;
        current = touch(number);
        const title = (chapterMatch[4] ?? "").replace(/^#+\s*/, "").trim();
        if (title && !/^(#{1,5}|\*\*)$/.test(title)) put(current, "title", excerpt(title, 120));
        continue;
      }
      const stripped = line.replace(/^#+\s*/, "");
      const inlineMatch = current ? stripped.match(/^([^:：]{1,20})[:：]\s*(.+)$/) : null;
      if (inlineMatch && current) {
        const fieldKey = matchChapterField(inlineMatch[1]);
        if (fieldKey) put(current, fieldKey, excerpt(inlineMatch[2]));
        continue;
      }
      const isHeading = /^(#{1,5}\s+.*|\*\*.+\*\*.*|.{1,30}[:：])$/.test(line);
      if (!isHeading || !current) continue;
      const headingText = line.replace(/^#+\s*|\*\*/g, "").trim();
      const fieldKey = matchChapterField(headingText);
      if (fieldKey) {
        const inlineValue = headingText.split(/[:：]/).slice(1).join("：").trim();
        put(current, fieldKey, inlineValue ? excerpt(inlineValue) : collectUntilNextHeading(lines, index + 1));
      }
    }
  }
  return { chapters };
}

export type ChapterArchitectureVersion = {
  kind: "CHAPTER_ARCHITECTURE";
  chapter_architecture_id: string;
  version: string;
  project_id: string;
  status: "CANDIDATE" | "LOCKED";
  chapters: ChapterEntry[];
  missing: string[];
  source_files: string[];
  prior_version_ref: string;
  change_summary: string;
  reviewer_ref: string;
  locked_at: string;
  coverage_gaps: string[];
  hash: string;
  created_at: string;
};

function sanitizeChapters(value: unknown): ChapterEntry[] {
  if (!Array.isArray(value)) return [];
  const out: ChapterEntry[] = [];
  for (const row of value) {
    if (!row || typeof row !== "object") continue;
    const rec = row as Record<string, unknown>;
    const number = Number(rec.chapter_number);
    if (!Number.isFinite(number) || number <= 0) continue;
    const text = (key: string) => (typeof rec[key] === "string" && rec[key].trim() ? String(rec[key]).trim() : undefined);
    const entry: ChapterEntry = {
      chapter_number: number,
      title: text("title") ?? "",
      chapter_goal: text("chapter_goal") ?? "",
      main_conflict: text("main_conflict") ?? "",
      production_complexity: text("production_complexity") ?? "",
      opening_hook: text("opening_hook"),
      character_progress: text("character_progress"),
      world_reveal: text("world_reveal"),
      turning_point: text("turning_point"),
      climax: text("climax"),
      resolution: text("resolution"),
      ending_hook: text("ending_hook"),
      foreshadowing: text("foreshadowing"),
      payoff_refs: text("payoff_refs"),
    };
    out.push(entry);
  }
  out.sort((a, b) => a.chapter_number - b.chapter_number);
  return out;
}

export function buildChapterArchitecture(input: {
  project: string;
  fileBodies: string[];
  sourceFiles?: string[];
  priorVersionRef?: string;
  changeSummary?: string;
  status?: "CANDIDATE" | "LOCKED";
  reviewerRef?: string;
  createdAt: string;
}): ChapterArchitectureVersion {
  const extraction = extractChapterArchitecture(input.fileBodies);
  const chapters: ChapterEntry[] = extraction.chapters
    .map((row) => ({
      chapter_number: row.chapter_number,
      title: row.title ?? "",
      chapter_goal: row.chapter_goal ?? "",
      opening_hook: row.opening_hook,
      main_conflict: row.main_conflict ?? "",
      character_progress: row.character_progress,
      world_reveal: row.world_reveal,
      turning_point: row.turning_point,
      climax: row.climax,
      resolution: row.resolution,
      ending_hook: row.ending_hook,
      foreshadowing: row.foreshadowing,
      payoff_refs: row.payoff_refs,
      production_complexity: row.production_complexity ?? "",
    }))
    .sort((a, b) => a.chapter_number - b.chapter_number);
  const missing: string[] = [];
  for (const chapter of chapters) {
    for (const field of CHAPTER_REQUIRED_FIELDS) {
      if (field === "chapter_number") {
        if (!Number.isFinite(chapter.chapter_number) || chapter.chapter_number <= 0) missing.push(`chapter ${chapter.chapter_number}: ${field}`);
        continue;
      }
      const value = (chapter as unknown as Record<string, unknown>)[field];
      if (typeof value !== "string" || !value.trim()) missing.push(`chapter ${chapter.chapter_number}: ${field}`);
    }
  }
  const coverageGaps: string[] = [];
  if (!input.fileBodies.length) coverageGaps.push("no_chapter_thread_files");
  if (!chapters.length) coverageGaps.push("chapters:empty");
  const hash = stableHash([
    input.project,
    ...chapters.map((chapter) => stableHash([String(chapter.chapter_number), chapter.title, chapter.chapter_goal, chapter.main_conflict, chapter.production_complexity, chapter.opening_hook ?? "", chapter.ending_hook ?? ""])),
    input.priorVersionRef ?? "",
  ]);
  return {
    kind: "CHAPTER_ARCHITECTURE",
    chapter_architecture_id: `CH-${hash}`,
    version: `CHV-${hash}`,
    project_id: input.project,
    status: input.status ?? "CANDIDATE",
    chapters,
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

export function parseChapterArchitecture(raw: string | null | undefined): ChapterArchitectureVersion | undefined {
  if (!raw || !raw.trim().startsWith("{")) return undefined;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;
    const rec = parsed as Record<string, unknown>;
    if (rec.kind !== "CHAPTER_ARCHITECTURE") return undefined;
    const version = typeof rec.version === "string" ? rec.version.trim() : "";
    const hash = typeof rec.hash === "string" ? rec.hash.trim() : "";
    if (!version || !hash) return undefined;
    const text = (key: string) => (typeof rec[key] === "string" ? String(rec[key]).trim() : "");
    const stringList = (value: unknown) => (Array.isArray(value) ? value.filter((row): row is string => typeof row === "string") : []);
    return {
      kind: "CHAPTER_ARCHITECTURE",
      chapter_architecture_id: text("chapter_architecture_id"),
      version,
      project_id: text("project_id"),
      status: rec.status === "LOCKED" ? "LOCKED" : "CANDIDATE",
      chapters: sanitizeChapters(rec.chapters),
      missing: stringList(rec.missing),
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

export function serializeChapterArchitecture(doc: ChapterArchitectureVersion): string {
  return JSON.stringify(doc);
}

export function withChapterArchStatus(doc: ChapterArchitectureVersion, status: "CANDIDATE" | "LOCKED", reviewerRef: string, at: string): ChapterArchitectureVersion {
  return { ...doc, status, reviewer_ref: reviewerRef || doc.reviewer_ref, locked_at: status === "LOCKED" ? at : "" };
}

export function chapterArchRequiredMissing(doc: ChapterArchitectureVersion): string[] {
  if (!doc.chapters.length) return ["chapters:empty"];
  return doc.missing;
}

export const CHAPTER_ARCH_STATUS_TOKENS = STORY_CORE_STATUS_TOKENS;

export function chapterArchExactRef(value: string | null | undefined): string {
  const raw = value?.trim() ?? "";
  if (!raw || CHAPTER_ARCH_STATUS_TOKENS.has(raw)) return "";
  if (raw.startsWith("{")) {
    const doc = parseChapterArchitecture(raw);
    return doc ? doc.version : "";
  }
  return raw.slice(0, 80);
}

export function formatChapterDigest(doc: ChapterArchitectureVersion): string {
  const lines = [
    `${doc.status === "LOCKED" ? "已鎖定" : "候選"} 章節架構 ${doc.version} / hash ${doc.hash}`,
    `章節 ${doc.chapters.length} 章；必填缺 ${doc.missing.length} 項`,
  ];
  if (doc.missing.length) lines.push(`缺：${doc.missing.slice(0, 4).join("、")}${doc.missing.length > 4 ? "…" : ""}`);
  if (doc.coverage_gaps.length) lines.push(`覆蓋缺口：${doc.coverage_gaps.join("、")}`);
  return lines.join("\n");
}
