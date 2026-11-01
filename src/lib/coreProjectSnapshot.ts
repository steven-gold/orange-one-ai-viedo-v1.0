export const CORE_SNAPSHOT_FIELD_UID = "CORE-01-FLD-PROJECT-SNAPSHOTS";
export const CORE_SNAPSHOT_PROJECT_CAP = 20;

export const CORE_SNAPSHOT_UIDS = [
  "CORE-01-BTN-ASSISTANT-RECORD",
  "CORE-01-BTN-ATTACHMENT",
  "CORE-01-BTN-BLUEPRINT-APPROVE",
  "CORE-01-BTN-BLUEPRINT-CREATE",
  "CORE-01-BTN-BLUEPRINT-VALIDATE",
  "CORE-01-BTN-CANDIDATE-COMPARE",
  "CORE-01-BTN-CANDIDATE-CONFIRM",
  "CORE-01-BTN-CANDIDATE-CREATE",
  "CORE-01-BTN-CANONICAL-SCRIPT",
  "CORE-01-BTN-CHAPTER-ARCH",
  "CORE-01-BTN-CHILD-LOCK",
  "CORE-01-BTN-CORE-REVIEW",
  "CORE-01-BTN-DNA-LOCK",
  "CORE-01-BTN-MULTI-AI",
  "CORE-01-BTN-NEW-THREAD",
  "CORE-01-BTN-PROJECT-CONFIRM",
  "CORE-01-BTN-PROJECT-LOCK",
  "CORE-01-BTN-PROJECT-VALIDATE",
  "CORE-01-BTN-REFERENCE",
  "CORE-01-BTN-RETURN-MODIFY",
  "CORE-01-BTN-SINGLE-AI",
  "CORE-01-BTN-STORY-CANDIDATE",
  "CORE-01-BTN-STORY-CORE",
  "CORE-01-BTN-TOPIC-CREATE",
  "CORE-01-CTL-TOPIC",
  "CORE-01-FLD-ASSISTANT-SUMMARY",
  "CORE-01-FLD-CHANGE-REQUEST",
  "CORE-01-FLD-CORE-ERRORS",
  "CORE-01-FLD-DOWNSTREAM-ASSET",
  "CORE-01-FLD-DOWNSTREAM-EDIT",
  "CORE-01-FLD-DOWNSTREAM-VIDEO",
  "CORE-01-FLD-EVALUATION",
  "CORE-01-FLD-EVENT-LOG",
  "CORE-01-FLD-HUMAN-DECISION",
  "CORE-01-FLD-IDEMPOTENCY",
  "CORE-01-FLD-LIFECYCLE-STAGE",
  "CORE-01-FLD-LOCK-REVIEW",
  "CORE-01-FLD-MESSAGE",
  "CORE-01-FLD-NAMING-AUTHORITY",
  "CORE-01-FLD-PACKAGE",
  "CORE-01-FLD-PAGE-MODE",
  "CORE-01-FLD-PROJECT",
  "CORE-01-FLD-RUNTIME-STAGE",
  "CORE-01-FLD-STRUCTURED-DECISION",
  "CORE-01-FLD-TOPIC",
  "CORE-01-FLD-TOPIC-LOCK",
  "CORE-01-FLD-TOPIC-SCOPE",
  "CORE-01-FLD-VERSION-STATE",
  "CORE-01-LST-THREADS",
  "CORE-01-LST-WORK-ITEMS",
] as const;

export type CoreProjectSnapshots = Record<string, Record<string, string>>;

export function parseProjectSnapshots(raw: string | null | undefined): CoreProjectSnapshots {
  try {
    const parsed = raw ? (JSON.parse(raw) as unknown) : {};
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      const out: CoreProjectSnapshots = {};
      for (const [name, value] of Object.entries(parsed as Record<string, unknown>)) {
        if (!name || !value || typeof value !== "object" || Array.isArray(value)) continue;
        const state: Record<string, string> = {};
        for (const [uid, field] of Object.entries(value as Record<string, unknown>)) {
          if (typeof field === "string") state[uid] = field;
        }
        out[name] = state;
      }
      return out;
    }
  } catch {}
  return {};
}

export function serializeProjectSnapshots(snapshots: CoreProjectSnapshots): string {
  const names = Object.keys(snapshots).slice(-CORE_SNAPSHOT_PROJECT_CAP);
  const trimmed: CoreProjectSnapshots = {};
  for (const name of names) trimmed[name] = snapshots[name];
  return JSON.stringify(trimmed);
}

export function captureProjectSnapshot(current: (uid: string) => string | null): Record<string, string> {
  const state: Record<string, string> = {};
  for (const uid of CORE_SNAPSHOT_UIDS) {
    const value = current(uid);
    if (value !== null && value !== "") state[uid] = value;
  }
  return state;
}

export function saveProjectSnapshot(snapshots: CoreProjectSnapshots, project: string, state: Record<string, string>): CoreProjectSnapshots {
  if (!project) return snapshots;
  return { ...snapshots, [project]: state };
}

export function dropProjectSnapshot(snapshots: CoreProjectSnapshots, project: string): CoreProjectSnapshots {
  if (!project || !(project in snapshots)) return snapshots;
  const next = { ...snapshots };
  delete next[project];
  return next;
}

export function renameProjectSnapshot(snapshots: CoreProjectSnapshots, from: string, to: string): CoreProjectSnapshots {
  if (!from || !to || from === to || !(from in snapshots)) return snapshots;
  const next = dropProjectSnapshot(snapshots, to);
  next[to] = snapshots[from];
  return next;
}

export function restoreProjectPatch(snapshots: CoreProjectSnapshots, project: string): Record<string, string> {
  const state = project ? snapshots[project] : undefined;
  const patch: Record<string, string> = {};
  for (const uid of CORE_SNAPSHOT_UIDS) patch[uid] = state?.[uid] ?? "";
  return patch;
}
