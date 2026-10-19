const PLACEHOLDER_NAMES = new Set([
  "新專題",
  "未命名專題",
  "New topic",
  "Untitled topic",
]);

const STATUS_TOKENS = new Set([
  "created",
  "selected",
  "validated",
  "confirmed",
  "approved",
  "locked",
  "sent",
  "queried",
  "open",
  "editing",
  "saved",
  "preview",
  "completed",
  "running",
  "retrying",
  "evaluated",
  "returned",
  "comparing",
  "attached",
  "recorded",
  "active",
  "idle",
  "ready",
  "PKG-READY",
  "PKG_READY",
]);

function usableName(value: string | undefined): string {
  const name = value?.trim();
  if (!name || STATUS_TOKENS.has(name) || PLACEHOLDER_NAMES.has(name)) return "";
  return name.slice(0, 80);
}

export function isPlaceholderName(value: string | null | undefined): boolean {
  const name = value?.trim() ?? "";
  return PLACEHOLDER_NAMES.has(name);
}

export function exactName(value: string | null | undefined): string {
  return usableName(value ?? undefined);
}

function projectValidated(current: (uid: string) => string | null): boolean {
  return current("CORE-01-BTN-PROJECT-VALIDATE") === "validated" && Boolean(exactName(current("CORE-01-CTL-PROJECT")));
}

function projectConfirmed(current: (uid: string) => string | null): boolean {
  const project = exactName(current("CORE-01-CTL-PROJECT"));
  if (!project) return false;
  return (
    current("CORE-01-BTN-PROJECT-CONFIRM") === "confirmed" ||
    current("CORE-01-BTN-PROJECT-LOCK") === project
  );
}

export function namedValue(nextValue: string | undefined, fallback: string): string {
  return usableName(nextValue) || usableName(fallback) || fallback.slice(0, 80);
}

export function namedList(raw: string | null | undefined, extra?: string | null): string[] {
  const items = parseThreadList(raw ?? null).filter((item) => Boolean(usableName(item)));
  const extraName = usableName(extra ?? undefined);
  if (extraName && !items.includes(extraName)) return [...items, extraName];
  return items;
}

export function parseThreadList(raw: string | null): string[] {
  if (!raw || raw === "created") return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) return parsed.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  } catch {
    return [raw];
  }
  return [raw];
}

const WORK_ITEMS = new Set([
  "STORY",
  "CHAPTER",
  "WORLD_SETTING",
  "DNA",
  "BLUEPRINT",
  "TOPIC_SCOPE",
  "PRODUCTION_SCRIPT",
]);

export type CoreThreadRecord = { title: string; workItem: string };

export function parseThreadRecords(raw: string | null): CoreThreadRecord[] {
  if (!raw || raw === "created") return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      const title = usableName(raw);
      return title ? [{ title, workItem: "" }] : [];
    }
    const records: CoreThreadRecord[] = [];
    for (const item of parsed) {
      if (typeof item === "string") {
        const title = usableName(item);
        if (title) records.push({ title, workItem: "" });
        continue;
      }
      if (!item || typeof item !== "object") continue;
      const rec = item as { title?: unknown; workItem?: unknown };
      const title = typeof rec.title === "string" ? usableName(rec.title) : "";
      if (!title) continue;
      records.push({
        title,
        workItem: typeof rec.workItem === "string" && WORK_ITEMS.has(rec.workItem) ? rec.workItem : "",
      });
    }
    return records;
  } catch {
    const title = usableName(raw);
    return title ? [{ title, workItem: "" }] : [];
  }
}

export function currentWorkItem(current: (uid: string) => string | null): string {
  const stored = current("CORE-01-LST-WORK-ITEMS") ?? "";
  if (WORK_ITEMS.has(stored)) return stored;
  if (!exactName(current("CORE-01-CTL-PROJECT"))) return "";
  const topicMode =
    current("CORE-01-FLD-PAGE-MODE") === "TOPIC_PRODUCTION" && Boolean(exactName(current("CORE-01-CTL-TOPIC")));
  return topicMode ? "TOPIC_SCOPE" : "STORY";
}

export function threadScopeReady(current: (uid: string) => string | null): boolean {
  return Boolean(exactName(current("CORE-01-CTL-PROJECT")) && currentWorkItem(current));
}

export function threadsForCurrentWorkItem(current: (uid: string) => string | null): CoreThreadRecord[] {
  const workItem = currentWorkItem(current);
  if (!workItem) return [];
  return parseThreadRecords(current("CORE-01-BTN-NEW-THREAD")).filter((row) => row.workItem === workItem);
}

export function activeThreadUid(current: (uid: string) => string | null): string {
  const scoped = threadsForCurrentWorkItem(current);
  const stored = current("CORE-01-LST-THREADS");
  if (stored && !["created", "selected"].includes(stored) && scoped.some((row) => row.title === stored)) {
    return stored;
  }
  return scoped[0]?.title ?? "";
}

export function hasSendableMessage(nextValue?: string, stored?: string | null): boolean {
  return Boolean(usableName(nextValue) || usableName(stored ?? undefined));
}

export function statusFromAction(actionUid: string): string {
  const token = actionUid.split("-").pop() ?? actionUid;
  const map: Record<string, string> = {
    CREATE: "created",
    SELECT: "selected",
    VALIDATE: "validated",
    CONFIRM: "confirmed",
    APPROVE: "approved",
    LOCK: "locked",
    SEND: "sent",
    SEARCH: "queried",
    OPEN: "open",
    EDIT: "editing",
    SAVE: "saved",
    PREVIEW: "preview",
    COMPLETE: "completed",
    EXECUTE: "running",
    RETRY: "retrying",
    EVALUATE: "evaluated",
    MODIFY: "returned",
    COMPARE: "comparing",
    ATTACHMENT: "attached",
    RECORD: "recorded",
    VIEW: "preview",
    ATTACH: "attached",
    SUBMIT: "sent",
    RETURN: "returned",
    CANDIDATE: "created",
  };
  const tokens = new Set(actionUid.split("-"));
  for (const [key, value] of Object.entries(map)) {
    if (tokens.has(key)) return value;
  }
  return token.toLowerCase();
}

export function previewCoreAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  if (actionUid === "CORE-01-ACT-PROJECT-CREATE") {
    const project = namedValue(nextValue, "新專案");
    const list = namedList(current("CORE-01-BTN-PROJECT-CREATE"), current("CORE-01-CTL-PROJECT"));
    const nextList = list.includes(project) ? list : [...list, project];
    return {
      "CORE-01-CTL-PROJECT": project,
      "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
      "CORE-01-FLD-NAMING-AUTHORITY": "ACPOS_SYSTEM",
      "CORE-01-FLD-RUNTIME-STAGE": "AI_RESPONSES",
      "CORE-01-LST-WORK-ITEMS": "STORY",
      "CORE-01-BTN-PROJECT-CREATE": JSON.stringify(nextList),
      "CORE-01-BTN-PROJECT-CONFIRM": "",
      "CORE-01-BTN-PROJECT-VALIDATE": "",
      "CORE-01-CTL-TOPIC": "",
      "CORE-01-BTN-TOPIC-CREATE": "[]",
      "CORE-01-FLD-TOPIC-SCOPE": "",
    };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-CREATE") {
    if (!projectConfirmed(current)) {
      return { "CORE-01-FLD-RUNTIME-STAGE": "TOPIC_LINEAGE_BLOCKED" };
    }
    const topic = exactName(nextValue);
    if (!topic) return {};
    const list = namedList(current("CORE-01-BTN-TOPIC-CREATE"), current("CORE-01-CTL-TOPIC"));
    const nextList = list.includes(topic) ? list : [...list, topic];
    const pkg = exactName(current("CORE-01-FLD-PACKAGE")) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    return {
      "CORE-01-CTL-TOPIC": topic,
      "CORE-01-FLD-PAGE-MODE": "TOPIC_PRODUCTION",
      "CORE-01-FLD-TOPIC-SCOPE": topic,
      ...(pkg ? { "CORE-01-FLD-PACKAGE": pkg } : {}),
      "CORE-01-LST-WORK-ITEMS": "TOPIC_SCOPE",
      "CORE-01-BTN-TOPIC-CREATE": JSON.stringify(nextList),
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-PAGE-MODE") {
    const topic = exactName(current("CORE-01-CTL-TOPIC"));
    if (!topic || !projectConfirmed(current)) {
      return {
        "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
        "CORE-01-LST-WORK-ITEMS": "STORY",
      };
    }
    const mode = current("CORE-01-FLD-PAGE-MODE");
    const next = mode === "TOPIC_PRODUCTION" ? "PROJECT_CORE" : "TOPIC_PRODUCTION";
    return {
      "CORE-01-FLD-PAGE-MODE": next,
      "CORE-01-LST-WORK-ITEMS": next === "TOPIC_PRODUCTION" ? "TOPIC_SCOPE" : "STORY",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-CTL-PROJECT") {
    const previous = current("CORE-01-CTL-PROJECT");
    const project = namedValue(nextValue, previous || "新專案");
    const list = namedList(current("CORE-01-BTN-PROJECT-CREATE"), previous).map((item) => (item === previous ? project : item));
    const nextList = list.includes(project) ? list : [...list, project];
    return {
      "CORE-01-CTL-PROJECT": project,
      "CORE-01-FLD-PAGE-MODE": current("CORE-01-FLD-PAGE-MODE") || "PROJECT_CORE",
      "CORE-01-BTN-PROJECT-CREATE": JSON.stringify(nextList),
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-NAMING-AUTHORITY") {
    return { "CORE-01-FLD-NAMING-AUTHORITY": current("CORE-01-FLD-NAMING-AUTHORITY") || "ACPOS_SYSTEM" };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-CTL-TOPIC") {
    if (!projectConfirmed(current)) return {};
    const previous = current("CORE-01-CTL-TOPIC");
    const topic = exactName(nextValue) || exactName(previous);
    if (!topic) return {};
    const list = namedList(current("CORE-01-BTN-TOPIC-CREATE"), previous).map((item) => (item === previous ? topic : item));
    const nextList = list.includes(topic) ? list : [...list, topic];
    return {
      "CORE-01-CTL-TOPIC": topic,
      "CORE-01-FLD-PAGE-MODE": "TOPIC_PRODUCTION",
      "CORE-01-FLD-TOPIC-SCOPE": topic,
      "CORE-01-LST-WORK-ITEMS": "TOPIC_SCOPE",
      "CORE-01-BTN-TOPIC-CREATE": JSON.stringify(nextList),
    };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-FLD-TOPIC-SCOPE") {
    if (!projectConfirmed(current)) return {};
    const topic = exactName(nextValue) || exactName(current("CORE-01-CTL-TOPIC")) || exactName(current("CORE-01-FLD-TOPIC-SCOPE"));
    return topic ? { "CORE-01-FLD-TOPIC-SCOPE": topic } : {};
  }
  if (actionUid === "CORE-01-ACT-AI-MODE-SINGLE") {
    return {
      "CORE-01-BTN-SINGLE-AI": "active",
      "CORE-01-BTN-MULTI-AI": "idle",
      "CORE-01-FLD-ASSIGNED-AI": "SINGLE",
    };
  }
  if (actionUid === "CORE-01-ACT-AI-MODE-MULTI") {
    return {
      "CORE-01-BTN-MULTI-AI": "active",
      "CORE-01-BTN-SINGLE-AI": "idle",
      "CORE-01-FLD-ASSIGNED-AI": "MULTI",
    };
  }
  if (actionUid === "CORE-01-ACT-THREAD-CREATE") {
    if (!threadScopeReady(current)) return {};
    const workItem = currentWorkItem(current);
    const records = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD"));
    const scoped = records.filter((row) => row.workItem === workItem);
    const title = namedValue(nextValue, `對話 ${scoped.length + 1}`);
    const exists = records.some((row) => row.title === title && row.workItem === workItem);
    const nextRecords = exists ? records : [...records, { title, workItem }];
    return {
      "CORE-01-LST-THREADS": title,
      "CORE-01-BTN-NEW-THREAD": JSON.stringify(nextRecords),
    };
  }
  if (actionUid === "CORE-01-ACT-SEND") {
    if (!activeThreadUid(current) || !hasSendableMessage(nextValue)) return {};
    const message = namedValue(nextValue, current("CORE-01-FLD-MESSAGE") || "已送出");
    const attachment = usableName(current("CORE-01-BTN-ATTACHMENT") ?? undefined);
    const reference = usableName(current("CORE-01-BTN-REFERENCE") ?? undefined);
    const files = [attachment, reference].filter(Boolean);
    const summary = files.length ? `${message} · ${files.join("、")}` : message;
    return {
      "CORE-01-FLD-MESSAGE": summary,
      "CORE-01-FLD-ASSISTANT-SUMMARY": summary,
      "CORE-01-FLD-RUNTIME-STAGE": "ASSISTANT_SUMMARY",
      "CORE-01-BTN-SEND": "sent",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-VALIDATE") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    return project ? { "CORE-01-BTN-PROJECT-VALIDATE": "validated" } : {};
  }
  if (actionUid === "CORE-01-ACT-PROJECT-CONFIRM") {
    if (!projectValidated(current)) return {};
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    return project
      ? {
          "CORE-01-BTN-PROJECT-CONFIRM": "confirmed",
          "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
          ...(current("CORE-01-FLD-RUNTIME-STAGE") === "TOPIC_LINEAGE_BLOCKED"
            ? { "CORE-01-FLD-RUNTIME-STAGE": "AI_RESPONSES" }
            : {}),
        }
      : {};
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-CREATE") {
    const candidate = namedValue(nextValue, "候選版本");
    return {
      "CORE-01-FLD-VERSION-STATE": candidate,
      "CORE-01-BTN-CANDIDATE-CREATE": "created",
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-ACCEPT") {
    return {
      "CORE-01-BTN-CANDIDATE-CONFIRM": "confirmed",
      "CORE-01-FLD-LOCK-REVIEW": "ready",
      "CORE-01-FLD-HUMAN-DECISION": "confirmed",
    };
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-CREATE") {
    const blueprint = namedValue(nextValue, current("CORE-01-BTN-BLUEPRINT-CREATE") || "新藍圖");
    return {
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprint,
      "CORE-01-FLD-PACKAGE": blueprint,
    };
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-VALIDATE") {
    const blueprint = exactName(nextValue) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    if (!blueprint) return {};
    const pkg = exactName(current("CORE-01-FLD-PACKAGE")) || blueprint;
    return {
      "CORE-01-BTN-BLUEPRINT-VALIDATE": "validated",
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprint,
      "CORE-01-FLD-PACKAGE": pkg,
    };
  }
  if (actionUid === "CORE-01-ACT-BLUEPRINT-APPROVE") {
    const blueprint = exactName(nextValue) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    if (!blueprint) return {};
    return {
      "CORE-01-BTN-BLUEPRINT-APPROVE": "approved",
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprint,
      "CORE-01-FLD-PACKAGE": blueprint,
    };
  }
  if (actionUid === "CORE-01-ACT-DNA-LOCK-REQUEST") {
    const dna = exactName(nextValue) || exactName(current("CORE-01-BTN-DNA-LOCK"));
    if (dna) return { "CORE-01-BTN-DNA-LOCK": dna };
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    return project ? { "CORE-01-BTN-DNA-LOCK": "locked" } : {};
  }
  if (actionUid === "CORE-01-ACT-CHILD-LOCK-REQUEST") {
    const blueprint = exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
    if (!blueprint) return {};
    return {
      "CORE-01-BTN-CHILD-LOCK": blueprint,
      "CORE-01-FLD-LOCK-REVIEW": "locked",
      "CORE-01-FLD-PACKAGE": blueprint,
      "CORE-01-BTN-BLUEPRINT-CREATE": exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || blueprint,
    };
  }
  if (actionUid === "CORE-01-ACT-CANONICAL-SCRIPT-VIEW") {
    const script = exactName(nextValue) || exactName(current("CORE-01-BTN-CANONICAL-SCRIPT"));
    if (!script) return {};
    const pkg = exactName(current("CORE-01-FLD-PACKAGE"));
    return {
      "CORE-01-BTN-CANONICAL-SCRIPT": script,
      ...(pkg ? { "CORE-01-FLD-PACKAGE": pkg } : {}),
    };
  }
  if (actionUid === "CORE-01-ACT-CORE-REVIEW-SUBMIT") {
    return {
      "CORE-01-BTN-CORE-REVIEW": "sent",
      "CORE-01-FLD-LOCK-REVIEW": current("CORE-01-FLD-LOCK-REVIEW") || "ready",
    };
  }
  if (actionUid === "CORE-01-ACT-MOTHER-LOCK-REQUEST") {
    const project = exactName(current("CORE-01-CTL-PROJECT"));
    if (!project) return {};
    return {
      "CORE-01-BTN-PROJECT-LOCK": project,
      "CORE-01-FLD-LOCK-REVIEW": "locked",
    };
  }
  if (actionUid === "CORE-01-ACT-ATTACHMENT") {
    return { "CORE-01-BTN-ATTACHMENT": namedValue(nextValue, current("CORE-01-BTN-ATTACHMENT") || "已上傳") };
  }
  if (actionUid === "CORE-01-ACT-REFERENCE-ATTACH") {
    return { "CORE-01-BTN-REFERENCE": namedValue(nextValue, current("CORE-01-BTN-REFERENCE") || "已引用") };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-FLD-PACKAGE") {
    const pkg = exactName(nextValue) || exactName(current("CORE-01-FLD-PACKAGE")) || exactName(current("CORE-01-BTN-BLUEPRINT-CREATE"));
    return pkg ? { "CORE-01-FLD-PACKAGE": pkg } : {};
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid.startsWith("CORE-01-FLD-DOWNSTREAM")) {
    const existing = usableName(current(controlUid) ?? undefined);
    return existing ? { [controlUid]: existing } : {};
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-VERSION-STATE") {
    return {
      "CORE-01-FLD-VERSION-STATE": namedValue(nextValue, current("CORE-01-FLD-VERSION-STATE") || "候選版本"),
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-LOCK-REVIEW") {
    return { "CORE-01-FLD-LOCK-REVIEW": namedValue(nextValue, current("CORE-01-FLD-LOCK-REVIEW") || "ready") };
  }
  if (actionUid === "CORE-01-ACT-WORK-ITEM-SELECT") {
    const nextWork = nextValue ?? current("CORE-01-LST-WORK-ITEMS") ?? "STORY";
    if (!WORK_ITEMS.has(nextWork)) return {};
    const matching = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD")).filter((row) => row.workItem === nextWork);
    const stored = current("CORE-01-LST-THREADS");
    const keep = stored && matching.some((row) => row.title === stored) ? stored : matching[0]?.title ?? "";
    return {
      "CORE-01-LST-WORK-ITEMS": nextWork,
      "CORE-01-LST-THREADS": keep,
    };
  }
  if (actionUid === "CORE-01-ACT-THREAD-SELECT") {
    const workItem = currentWorkItem(current);
    if (!workItem) return {};
    const title = exactName(nextValue) || exactName(current("CORE-01-LST-THREADS"));
    if (!title) return {};
    const match = parseThreadRecords(current("CORE-01-BTN-NEW-THREAD")).some(
      (row) => row.title === title && row.workItem === workItem,
    );
    return match ? { "CORE-01-LST-THREADS": title } : {};
  }
  if (controlUid === "CORE-01-FLD-RUNTIME-STAGE") {
    return { "CORE-01-FLD-RUNTIME-STAGE": nextValue || current("CORE-01-FLD-RUNTIME-STAGE") || "AI_RESPONSES" };
  }
  const existing = current(controlUid);
  if (!nextValue && existing && !STATUS_TOKENS.has(existing) && actionUid.includes("-SELECT")) {
    return { [controlUid]: existing };
  }
  return { [controlUid]: nextValue ?? statusFromAction(actionUid) };
}
