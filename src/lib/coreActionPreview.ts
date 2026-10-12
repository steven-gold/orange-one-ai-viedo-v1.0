function stampId(prefix: string): string {
  const now = new Date();
  const y = now.getUTCFullYear();
  const m = String(now.getUTCMonth() + 1).padStart(2, "0");
  const d = String(now.getUTCDate()).padStart(2, "0");
  const t = String(now.getUTCHours()).padStart(2, "0") + String(now.getUTCMinutes()).padStart(2, "0");
  return `${prefix}-${y}${m}${d}-${t}`;
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
  for (const [key, value] of Object.entries(map)) {
    if (actionUid.includes(key)) return value;
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
    const project = stampId("P");
    return {
      "CORE-01-CTL-PROJECT": project,
      "CORE-01-FLD-PAGE-MODE": "PROJECT_CORE",
      "CORE-01-FLD-NAMING-AUTHORITY": "ACPOS_SYSTEM",
      "CORE-01-FLD-RUNTIME-STAGE": "AI_RESPONSES",
      "CORE-01-LST-WORK-ITEMS": "STORY",
      "CORE-01-BTN-PROJECT-CREATE": "created",
    };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-CREATE") {
    const topic = stampId("T");
    return {
      "CORE-01-CTL-TOPIC": topic,
      "CORE-01-FLD-PAGE-MODE": "TOPIC_PRODUCTION",
      "CORE-01-FLD-TOPIC-SCOPE": topic,
      "CORE-01-FLD-PACKAGE": "PKG-READY",
      "CORE-01-LST-WORK-ITEMS": "TOPIC_SCOPE",
      "CORE-01-BTN-TOPIC-CREATE": "created",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-PAGE-MODE") {
    const mode = current("CORE-01-FLD-PAGE-MODE");
    const next = mode === "TOPIC_PRODUCTION" ? "PROJECT_CORE" : "TOPIC_PRODUCTION";
    return {
      "CORE-01-FLD-PAGE-MODE": next,
      "CORE-01-LST-WORK-ITEMS": next === "TOPIC_PRODUCTION" ? "TOPIC_SCOPE" : "STORY",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-CTL-PROJECT") {
    return {
      "CORE-01-CTL-PROJECT": current("CORE-01-CTL-PROJECT") || stampId("P"),
      "CORE-01-FLD-PAGE-MODE": current("CORE-01-FLD-PAGE-MODE") || "PROJECT_CORE",
    };
  }
  if (actionUid === "CORE-01-ACT-PROJECT-SELECT" && controlUid === "CORE-01-FLD-NAMING-AUTHORITY") {
    return { "CORE-01-FLD-NAMING-AUTHORITY": current("CORE-01-FLD-NAMING-AUTHORITY") || "ACPOS_SYSTEM" };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-CTL-TOPIC") {
    return { "CORE-01-CTL-TOPIC": current("CORE-01-CTL-TOPIC") || stampId("T") };
  }
  if (actionUid === "CORE-01-ACT-TOPIC-SELECT" && controlUid === "CORE-01-FLD-TOPIC-SCOPE") {
    return {
      "CORE-01-FLD-TOPIC-SCOPE": current("CORE-01-CTL-TOPIC") || current("CORE-01-FLD-TOPIC-SCOPE") || stampId("T"),
    };
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
    const thread = stampId("TH");
    return {
      "CORE-01-LST-THREADS": thread,
      "CORE-01-BTN-NEW-THREAD": "created",
    };
  }
  if (actionUid === "CORE-01-ACT-SEND") {
    return {
      "CORE-01-FLD-MESSAGE": "sent",
      "CORE-01-FLD-ASSISTANT-SUMMARY": "recorded",
      "CORE-01-FLD-RUNTIME-STAGE": "ASSISTANT_SUMMARY",
      "CORE-01-BTN-SEND": "sent",
    };
  }
  if (actionUid === "CORE-01-ACT-CANDIDATE-CREATE") {
    const candidate = stampId("CAND");
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
    const blueprint = stampId("BP");
    return {
      "CORE-01-BTN-BLUEPRINT-CREATE": blueprint,
      "CORE-01-FLD-PACKAGE": blueprint,
    };
  }
  if (actionUid === "CORE-01-ACT-WORK-ITEM-SELECT") {
    return { "CORE-01-LST-WORK-ITEMS": nextValue ?? current("CORE-01-LST-WORK-ITEMS") ?? "STORY" };
  }
  if (actionUid === "CORE-01-ACT-THREAD-SELECT") {
    return { "CORE-01-LST-THREADS": nextValue ?? current("CORE-01-LST-THREADS") ?? "selected" };
  }
  if (controlUid === "CORE-01-FLD-RUNTIME-STAGE" && nextValue) {
    return { "CORE-01-FLD-RUNTIME-STAGE": nextValue };
  }
  return { [controlUid]: statusFromAction(actionUid) };
}
