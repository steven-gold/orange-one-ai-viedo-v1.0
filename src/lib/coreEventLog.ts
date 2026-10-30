export const CORE_EVENT_LOG_CAP = 30;

export type CoreEventEntry = { event: string; at: string; ref: string };

export function appendCoreEvent(raw: string | null | undefined, event: string, ref: string, at: string): string {
  let list: CoreEventEntry[] = [];
  try {
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    if (Array.isArray(parsed)) list = parsed.filter((row): row is CoreEventEntry => Boolean(row) && typeof row === "object" && typeof (row as CoreEventEntry).event === "string");
  } catch {
    list = [];
  }
  const next: CoreEventEntry = { event, at, ref: String(ref || "").slice(0, 120) };
  list = [...list, next].slice(-CORE_EVENT_LOG_CAP);
  return JSON.stringify(list);
}

export function parseCoreEvents(raw: string | null | undefined): CoreEventEntry[] {
  try {
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    if (Array.isArray(parsed)) {
      return parsed.filter((row): row is CoreEventEntry => Boolean(row) && typeof row === "object" && typeof (row as CoreEventEntry).event === "string");
    }
  } catch {
    return [];
  }
  return [];
}

export function formatCoreEvents(raw: string | null | undefined): string {
  const rows = parseCoreEvents(raw);
  if (!rows.length) return "尚未記錄事件";
  return rows
    .slice(-3)
    .reverse()
    .map((row) => `${row.event} · ${row.ref || "—"} · ${row.at}`)
    .join("\n");
}

export const CORE_EVENT_NAMES = {
  project_created: "project.created",
  story_candidate_set_created: "story.candidate_set.created",
  story_candidates_compared: "story.candidates.compared",
  story_core_adopted: "story.core.adopted",
  story_revision_requested: "story.revision.requested",
  chapter_architecture_version_created: "chapter.architecture.version.created",
  world_bible_version_created: "world_bible.version.created",
  dna_candidate_created: "dna.candidate_created",
  dna_resolved: "dna.resolved",
  dna_lock_requested: "dna.lock.requested",
  script_version_created: "script.version_created",
  topic_scope_confirmed: "topic.scope.confirmed",
  topic_blueprint_candidate_created: "topic.blueprint.candidate.created",
  topic_child_lock_requested: "topic.child_lock.requested",
  topic_blueprint_locked: "topic.blueprint.locked",
  production_package_ready: "production.package.ready",
  core_change_requested: "core.change.requested",
  core_version_superseded: "core.version.superseded",
  project_lock_approved: "project.lock.approved",
} as const;
