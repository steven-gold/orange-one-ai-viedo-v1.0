export const DASHBOARD_SECTION_KEYS = [
  "company_project_count",
  "company_running_project_count",
  "company_pending_action_count",
  "company_pending_review_count",
  "company_completed_project_count",
  "company_average_progress",
  "project_progress_overview",
  "company_progress_summary",
  "production_summary",
  "notifications",
  "company_announcements",
  "industry_news",
  "system_status_summary",
  "recent_completions",
] as const;

export type DashboardSectionKey = (typeof DASHBOARD_SECTION_KEYS)[number];

export type DashboardScalar = { value: number | null };

export type DashboardProjectTask = {
  task_id?: string | null;
  display_name?: string | null;
  label?: string | null;
  code?: string | null;
  task_state?: string | null;
};

export type DashboardProjectTopic = {
  topic_id?: string | null;
  display_name?: string | null;
  label?: string | null;
  code?: string | null;
  status?: string | null;
  progress_percentage?: number | null;
  total_operation_time_seconds?: number | null;
  tasks?: DashboardProjectTask[] | null;
};

export type DashboardProject = {
  project_id?: string | null;
  display_name?: string | null;
  label?: string | null;
  code?: string | null;
  status?: string | null;
  progress_percentage?: number | null;
  topics?: DashboardProjectTopic[] | null;
};

export type ProjectProgressOverview = { projects?: DashboardProject[] | null };

export type CompanyProgressSummary = {
  overall_progress_percentage?: number | null;
  running_count?: number | null;
  pending_action_count?: number | null;
  pending_review_count?: number | null;
  completed_count?: number | null;
};

export type ProductionUnit = {
  unit_key?: string | null;
  unit_label?: string | null;
  state?: string | null;
  running_count?: number | null;
  pending_count?: number | null;
  review_count?: number | null;
  completed_count?: number | null;
};
export type ProductionSummary = { units?: ProductionUnit[] | null };

export type NotificationItem = {
  notification_id?: string | null;
  title?: string | null;
  category?: string | null;
  created_at?: string | null;
  read_state?: string | null;
};
export type NotificationsSummary = { items?: NotificationItem[] | null };

export type AnnouncementItem = {
  announcement_id?: string | null;
  title?: string | null;
  summary?: string | null;
  published_at?: string | null;
};
export type AnnouncementsSummary = { items?: AnnouncementItem[] | null };

export type IndustryNewsItem = {
  news_id?: string | null;
  title?: string | null;
  source_name?: string | null;
  summary?: string | null;
  published_at?: string | null;
};
export type IndustryNewsSummary = { items?: IndustryNewsItem[] | null };

export type SystemStatusSummary = {
  overall_status?: string | null;
  summary?: string | null;
  checked_at?: string | null;
};

export type RecentCompletionItem = {
  completion_id?: string | null;
  project_label?: string | null;
  topic_label?: string | null;
  item_label?: string | null;
  completion_kind?: string | null;
  completed_at?: string | null;
};
export type RecentCompletionsSummary = { items?: RecentCompletionItem[] | null };

export type DashboardReadModel = {
  read_model_version: string | null;
  correlation_id: string;
  company_project_count?: { company_project_count: DashboardScalar | null };
  company_running_project_count?: { company_running_project_count: DashboardScalar | null };
  company_pending_action_count?: { company_pending_action_count: DashboardScalar | null };
  company_pending_review_count?: { company_pending_review_count: DashboardScalar | null };
  company_completed_project_count?: { company_completed_project_count: DashboardScalar | null };
  company_average_progress?: { company_average_progress: DashboardScalar | null };
  project_progress_overview?: { project_progress_overview: ProjectProgressOverview | null };
  company_progress_summary?: { company_progress_summary: CompanyProgressSummary | null };
  production_summary?: { production_summary: ProductionSummary | null };
  notifications?: { notifications: NotificationsSummary | null };
  company_announcements?: { company_announcements: AnnouncementsSummary | null };
  industry_news?: { industry_news: IndustryNewsSummary | null };
  system_status_summary?: { system_status_summary: SystemStatusSummary | null };
  recent_completions?: { recent_completions: RecentCompletionsSummary | null };
};

export type DashboardErrorUid =
  | "WB-01-ERR-READ-001"
  | "WB-01-ERR-POLICY-001"
  | "WB-01-ERR-SCHEMA-001"
  | "WB-01-ERR-UNDEFINED-001";

export type DashboardReadError = {
  error_uid: DashboardErrorUid;
  reason_code: string;
  correlation_id: string;
};

export type DashboardReadResult =
  | { ok: true; value: DashboardReadModel }
  | { ok: false; error: DashboardReadError };

const TOP_LEVEL_KEYS = new Set<string>(["read_model_version", "correlation_id", ...DASHBOARD_SECTION_KEYS]);
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const onlyKeys = (value: Record<string, unknown>, allowed: readonly string[]) => Object.keys(value).every((key) => allowed.includes(key));
const nullableString = (value: unknown) => value === undefined || value === null || typeof value === "string";
const nullableInt = (value: unknown) => value === undefined || value === null || (Number.isInteger(value) && (value as number) >= 0);
const nullablePercentage = (value: unknown) => value === undefined || value === null || (typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100);
const list = (value: unknown, validate: (item: unknown) => boolean) => value === undefined || value === null || (Array.isArray(value) && value.every(validate));

function scalar(value: unknown, percentage = false): boolean {
  return isRecord(value) && onlyKeys(value, ["value"]) && (percentage ? nullablePercentage(value.value) : nullableInt(value.value));
}
function task(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["task_id", "display_name", "label", "code", "task_state"]) &&
    nullableString(value.task_id) && nullableString(value.display_name) && nullableString(value.label) && nullableString(value.code) && nullableString(value.task_state);
}
function topic(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["topic_id", "display_name", "label", "code", "status", "progress_percentage", "total_operation_time_seconds", "tasks"]) &&
    nullableString(value.topic_id) && nullableString(value.display_name) && nullableString(value.label) && nullableString(value.code) && nullableString(value.status) &&
    nullablePercentage(value.progress_percentage) && nullableInt(value.total_operation_time_seconds) && list(value.tasks, task);
}
function project(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["project_id", "display_name", "label", "code", "status", "progress_percentage", "topics"]) &&
    nullableString(value.project_id) && nullableString(value.display_name) && nullableString(value.label) && nullableString(value.code) && nullableString(value.status) &&
    nullablePercentage(value.progress_percentage) && list(value.topics, topic);
}
function projectOverview(value: unknown): boolean { return isRecord(value) && onlyKeys(value, ["projects"]) && list(value.projects, project); }
function companyProgress(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["overall_progress_percentage", "running_count", "pending_action_count", "pending_review_count", "completed_count"]) &&
    nullablePercentage(value.overall_progress_percentage) && nullableInt(value.running_count) && nullableInt(value.pending_action_count) && nullableInt(value.pending_review_count) && nullableInt(value.completed_count);
}
function productionUnit(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["unit_key", "unit_label", "state", "running_count", "pending_count", "review_count", "completed_count"]) &&
    nullableString(value.unit_key) && nullableString(value.unit_label) && nullableString(value.state) && nullableInt(value.running_count) && nullableInt(value.pending_count) && nullableInt(value.review_count) && nullableInt(value.completed_count);
}
function production(value: unknown): boolean { return isRecord(value) && onlyKeys(value, ["units"]) && list(value.units, productionUnit); }
function notification(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["notification_id", "title", "category", "created_at", "read_state"]) &&
    nullableString(value.notification_id) && nullableString(value.title) && nullableString(value.category) && nullableString(value.created_at) && nullableString(value.read_state);
}
function announcement(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["announcement_id", "title", "summary", "published_at"]) &&
    nullableString(value.announcement_id) && nullableString(value.title) && nullableString(value.summary) && nullableString(value.published_at);
}
function news(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["news_id", "title", "source_name", "summary", "published_at"]) &&
    nullableString(value.news_id) && nullableString(value.title) && nullableString(value.source_name) && nullableString(value.summary) && nullableString(value.published_at);
}
function systemStatus(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["overall_status", "summary", "checked_at"]) && nullableString(value.overall_status) && nullableString(value.summary) && nullableString(value.checked_at);
}
function recent(value: unknown): boolean {
  return isRecord(value) && onlyKeys(value, ["completion_id", "project_label", "topic_label", "item_label", "completion_kind", "completed_at"]) &&
    nullableString(value.completion_id) && nullableString(value.project_label) && nullableString(value.topic_label) && nullableString(value.item_label) && nullableString(value.completion_kind) && nullableString(value.completed_at);
}
function items(value: unknown, validate: (item: unknown) => boolean): boolean { return isRecord(value) && onlyKeys(value, ["items"]) && list(value.items, validate); }
function wrapper(value: unknown, key: DashboardSectionKey, validate: (inner: unknown) => boolean): boolean {
  return isRecord(value) && onlyKeys(value, [key]) && (value[key] === null || validate(value[key]));
}

export function validateDashboardReadModel(value: unknown, correlationFallback = "unresolved"): DashboardReadResult {
  if (!isRecord(value)) return { ok: false, error: { error_uid: "WB-01-ERR-SCHEMA-001", reason_code: "READ_MODEL_NOT_OBJECT", correlation_id: correlationFallback } };
  if (!Object.keys(value).every((key) => TOP_LEVEL_KEYS.has(key))) return { ok: false, error: { error_uid: "WB-01-ERR-SCHEMA-001", reason_code: "UNSUPPORTED_TOP_LEVEL_KEY", correlation_id: correlationFallback } };
  const correlationId = typeof value.correlation_id === "string" && value.correlation_id.length > 0 ? value.correlation_id : correlationFallback;
  if (!(value.read_model_version === null || typeof value.read_model_version === "string") || typeof value.correlation_id !== "string" || value.correlation_id.length === 0) {
    return { ok: false, error: { error_uid: "WB-01-ERR-SCHEMA-001", reason_code: "READ_MODEL_METADATA_INVALID", correlation_id: correlationId } };
  }
  const checks: Array<[DashboardSectionKey, (inner: unknown) => boolean]> = [
    ["company_project_count", (inner) => scalar(inner)],
    ["company_running_project_count", (inner) => scalar(inner)],
    ["company_pending_action_count", (inner) => scalar(inner)],
    ["company_pending_review_count", (inner) => scalar(inner)],
    ["company_completed_project_count", (inner) => scalar(inner)],
    ["company_average_progress", (inner) => scalar(inner, true)],
    ["project_progress_overview", projectOverview],
    ["company_progress_summary", companyProgress],
    ["production_summary", production],
    ["notifications", (inner) => items(inner, notification)],
    ["company_announcements", (inner) => items(inner, announcement)],
    ["industry_news", (inner) => items(inner, news)],
    ["system_status_summary", systemStatus],
    ["recent_completions", (inner) => items(inner, recent)],
  ];
  for (const [key, validate] of checks) {
    const section = value[key];
    if (section !== undefined && !wrapper(section, key, validate)) {
      return { ok: false, error: { error_uid: "WB-01-ERR-SCHEMA-001", reason_code: `INVALID_SECTION_${key.toUpperCase()}`, correlation_id: correlationId } };
    }
  }
  return { ok: true, value: value as DashboardReadModel };
}

export function selectDashboardSection(model: DashboardReadModel, key: DashboardSectionKey): unknown {
  const wrapperValue = model[key] as Record<string, unknown> | undefined;
  return wrapperValue?.[key] ?? null;
}
