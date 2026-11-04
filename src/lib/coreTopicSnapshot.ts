// Topic-level snapshot store (spec ACPOS_CORE-01 Canonical Production Script
// Contract): the Production Script belongs to Topic production scope, so
// topic-bound fields switch with the selected topic inside one project.
// Continuity Bridge: a fresh topic inherits a read-only bridge line pointing
// at the previous topic it continues from.

export const CORE_TOPIC_SNAPSHOT_FIELD_UID = "CORE-01-FLD-TOPIC-SNAPSHOTS";
export const CORE_TOPIC_SNAPSHOT_CAP = 40;

export const CORE_TOPIC_SNAPSHOT_UIDS = [
  "CORE-01-BTN-CANONICAL-SCRIPT",
  "CORE-01-BTN-CANDIDATE-CREATE",
  "CORE-01-BTN-CANDIDATE-CONFIRM",
  "CORE-01-BTN-CANDIDATE-COMPARE",
  "CORE-01-BTN-CORE-REVIEW",
  "CORE-01-FLD-TOPIC-SCOPE",
  "CORE-01-FLD-EVALUATION",
  "CORE-01-FLD-VERSION-STATE",
  "CORE-01-FLD-LOCK-REVIEW",
  "CORE-01-FLD-STRUCTURED-DECISION",
  "CORE-01-FLD-HUMAN-DECISION",
  "CORE-01-FLD-LIFECYCLE-STAGE",
  "CORE-01-FLD-PACKAGE",
  "CORE-01-FLD-CHANGE-REQUEST",
  "CORE-01-BTN-RETURN-MODIFY",
] as const;

export type CoreTopicSnapshots = Record<string, Record<string, string>>;

export function parseTopicSnapshots(raw: string | null | undefined): CoreTopicSnapshots {
  if (!raw || !raw.trim()) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const entries = Object.entries(parsed as Record<string, unknown>)
      .filter(([key, value]) => key.includes("/") && value && typeof value === "object" && !Array.isArray(value))
      .map(([key, value]) => {
        const state: Record<string, string> = {};
        for (const [uid, text] of Object.entries(value as Record<string, unknown>)) {
          if (typeof text === "string") state[uid] = text;
        }
        return [key, state] as const;
      });
    return Object.fromEntries(entries);
  } catch {
    return {};
  }
}

export function serializeTopicSnapshots(snapshots: CoreTopicSnapshots): string {
  return JSON.stringify(snapshots);
}

export function captureTopicSnapshot(current: (uid: string) => string | null): Record<string, string> {
  const state: Record<string, string> = {};
  for (const uid of CORE_TOPIC_SNAPSHOT_UIDS) {
    state[uid] = current(uid) ?? "";
  }
  return state;
}

export function topicKey(project: string, topic: string): string {
  return `${project}/${topic}`;
}

export function saveTopicSnapshot(
  snapshots: CoreTopicSnapshots,
  project: string,
  topic: string,
  state: Record<string, string>,
): CoreTopicSnapshots {
  const key = topicKey(project, topic);
  const next: CoreTopicSnapshots = { ...snapshots, [key]: state };
  const keys = Object.keys(next);
  if (keys.length > CORE_TOPIC_SNAPSHOT_CAP) {
    for (const stale of keys.slice(0, keys.length - CORE_TOPIC_SNAPSHOT_CAP)) delete next[stale];
  }
  return next;
}

export function restoreTopicPatch(
  snapshots: CoreTopicSnapshots,
  project: string,
  topic: string,
): Record<string, string> {
  const state = snapshots[topicKey(project, topic)];
  const patch: Record<string, string> = {};
  for (const uid of CORE_TOPIC_SNAPSHOT_UIDS) patch[uid] = state?.[uid] ?? "";
  return patch;
}

export function renameProjectTopicSnapshots(snapshots: CoreTopicSnapshots, from: string, to: string): CoreTopicSnapshots {
  const next: CoreTopicSnapshots = {};
  const prefix = `${from}/`;
  for (const [key, state] of Object.entries(snapshots)) {
    if (key.startsWith(prefix)) next[`${to}/${key.slice(prefix.length)}`] = state;
    else next[key] = state;
  }
  return next;
}

export function dropProjectTopicSnapshots(snapshots: CoreTopicSnapshots, project: string): CoreTopicSnapshots {
  const next: CoreTopicSnapshots = {};
  const prefix = `${project}/`;
  for (const [key, state] of Object.entries(snapshots)) {
    if (!key.startsWith(prefix)) next[key] = state;
  }
  return next;
}

export function dropTopicSnapshot(
  snapshots: CoreTopicSnapshots,
  project: string,
  topic: string,
): CoreTopicSnapshots {
  if (!project || !topic) return snapshots;
  const next = { ...snapshots };
  delete next[topicKey(project, topic)];
  return next;
}

export function topicBridgeLine(previousTopic: string, previousState: Record<string, string> | undefined): string {
  const script = previousState?.["CORE-01-BTN-CANONICAL-SCRIPT"] ?? "";
  const lineage = script ? script.slice(0, 60) : "";
  return lineage
    ? `前序專題：${previousTopic}｜橋接腳本 ref：${lineage}`
    : `前序專題：${previousTopic}`;
}
