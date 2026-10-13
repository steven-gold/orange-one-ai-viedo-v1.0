import { namedList, parseThreadList } from "./coreActionPreview";
import { DASHBOARD_SECTION_SEEDS } from "@/server/domain/dashboard";
import type { DashboardSectionValue } from "@/server/domain/types";

const STATUS_OR_MODE = new Set([
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
  "PROJECT_CORE",
  "TOPIC_PRODUCTION",
  "SINGLE",
  "MULTI",
  "ACPOS_SYSTEM",
  "AI_RESPONSES",
  "ASSISTANT_SUMMARY",
  "CORE_EVALUATION",
  "HUMAN_DECISION",
  "CANDIDATE",
  "STORY",
  "CHAPTER",
  "WORLD_SETTING",
  "DNA",
  "BLUEPRINT",
  "TOPIC_SCOPE",
  "PRODUCTION_SCRIPT",
  "PKG_READY",
  "PKG-READY",
  "REVIEW",
]);

function named(value: string | null | undefined): string {
  const text = value?.trim() ?? "";
  if (!text || STATUS_OR_MODE.has(text)) return "";
  return text;
}

function locked(current: (uid: string) => string | null): boolean {
  const lock = current("CORE-01-FLD-LOCK-REVIEW");
  const projectLock = current("CORE-01-BTN-PROJECT-LOCK");
  return lock === "ready" || lock === "locked" || projectLock === "locked";
}

export function projectDashboardFromCore(current: (uid: string) => string | null): DashboardSectionValue[] {
  const project = named(current("CORE-01-CTL-PROJECT"));
  const topic = named(current("CORE-01-CTL-TOPIC"));
  const projects = namedList(current("CORE-01-BTN-PROJECT-CREATE"), project);
  const topics = namedList(current("CORE-01-BTN-TOPIC-CREATE"), topic);
  const threads = parseThreadList(current("CORE-01-BTN-NEW-THREAD"));
  const review = current("CORE-01-BTN-CORE-REVIEW");
  const work = current("CORE-01-LST-WORK-ITEMS");
  const pkg = named(current("CORE-01-FLD-PACKAGE"));
  const candidate = named(current("CORE-01-FLD-VERSION-STATE"));
  const names = [...projects, ...topics];
  const total = names.length;
  const completed = total > 0 && locked(current) ? 1 : 0;
  const running = Math.max(total - completed, 0);
  const pendingReview = total > 0 && !locked(current) && review !== "sent" ? 1 : 0;
  const pendingAction = total > 0 && threads.length === 0 ? 1 : 0;
  const progress = total === 0 ? 0 : Math.round((completed / total) * 100);
  const notifications = pendingAction + pendingReview;
  const byUid: Record<string, { value: string | null; detail: string }> = {
    "WB-01-CMP-KPI-PROJECT-COUNT": { value: String(total), detail: names.join("、") },
    "WB-01-CMP-KPI-RUNNING": { value: String(running), detail: running ? names.join("、") : "" },
    "WB-01-CMP-KPI-PENDING-ACTION": { value: String(pendingAction), detail: pendingAction ? names.join("、") : "" },
    "WB-01-CMP-KPI-PENDING-REVIEW": { value: String(pendingReview), detail: pendingReview ? candidate || names.join("、") : "" },
    "WB-01-CMP-KPI-COMPLETED": { value: String(completed), detail: completed ? names.join("、") : "" },
    "WB-01-CMP-KPI-AVERAGE-PROGRESS": { value: `${progress}%`, detail: names.join("、") },
    "WB-01-CMP-PROJECT-PROGRESS": { value: project || null, detail: work ?? "" },
    "WB-01-CMP-COMPANY-PROGRESS": { value: `${progress}%`, detail: names.join("、") },
    "WB-01-CMP-PRODUCTION-SUMMARY": { value: topic || pkg || null, detail: pkg },
    "WB-01-CMP-NOTIFICATIONS": { value: String(notifications), detail: names.join("、") },
    "WB-01-CMP-ANNOUNCEMENTS": { value: null, detail: "" },
    "WB-01-CMP-INDUSTRY-NEWS": { value: null, detail: "" },
    "WB-01-CMP-SYSTEM-STATUS": { value: "ready", detail: "" },
    "WB-01-CMP-RECENT-COMPLETIONS": { value: completed ? project || topic || null : null, detail: completed ? names.join("、") : "" },
  };

  return DASHBOARD_SECTION_SEEDS.map((seed) => {
    const row = byUid[seed.sectionUid] ?? { value: null, detail: "" };
    return {
      sectionUid: seed.sectionUid,
      controlUid: seed.controlUid,
      value: row.value,
      detail: row.detail,
    };
  });
}
