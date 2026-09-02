import { isControlledTestMode } from "@/domain/testing/controlledTestData";

export type KnowledgePageState =
  | "LOADING"
  | "READY"
  | "EMPTY"
  | "ERROR"
  | "POLICY_BLOCKED"
  | "VERSION_CONFLICT"
  | "EXTERNAL_PENDING"
  | "READ_ONLY"
  | "ARCHIVED";

export type KnowledgeProjectionTestMetadata = {
  data_classification: "TEST_ONLY";
  synthetic: true;
  test_dataset_id: string;
  test_run_id: string;
  created_for_validation: true;
  production_eligible: false;
};

export type KnowledgeProjection = {
  page_state: KnowledgePageState | null;
  values: Readonly<Record<string, string>>;
  control_enabled: Readonly<Record<string, boolean>>;
  test_metadata?: KnowledgeProjectionTestMetadata;
};

export type KnowledgeActionTrace = {
  uid: string;
  effect: string;
  owner: string;
  operation: string;
  method: string;
  path: string;
  permission: string;
  errors: readonly string[];
  audit_event: string;
};

const ALLOWED_PAGE_STATES = new Set<KnowledgePageState>([
  "LOADING",
  "READY",
  "EMPTY",
  "ERROR",
  "POLICY_BLOCKED",
  "VERSION_CONFLICT",
  "EXTERNAL_PENDING",
  "READ_ONLY",
  "ARCHIVED",
]);

export const KNOWLEDGE_ACTIONS: readonly KnowledgeActionTrace[] = [
  { uid: "KB-01-ACT-SEARCH", effect: "READ_SEARCH", owner: "FactPackService + KnowledgeExperienceService", operation: "searchKnowledge", method: "POST", path: "/v1/knowledge/search", permission: "knowledge.read", errors: ["KB-01-ERR-001", "KB-01-ERR-002"], audit_event: "knowledge.search" },
  { uid: "KB-01-ACT-CITATION-OPEN", effect: "READ", owner: "FactPackService + KnowledgeExperienceService", operation: "getCitation", method: "GET", path: "/v1/knowledge/citations/{citationId}", permission: "knowledge.read", errors: ["KB-01-ERR-001"], audit_event: "knowledge.citation.view" },
  { uid: "KB-01-ACT-SOURCE-CREATE", effect: "CREATE", owner: "KnowledgeExperienceService", operation: "createKnowledgeSource", method: "POST", path: "/v1/knowledge/sources", permission: "knowledge.source.configure", errors: ["KB-01-ERR-002", "KB-01-ERR-004", "KB-01-ERR-013"], audit_event: "knowledge.source.created" },
  { uid: "KB-01-ACT-SOURCE-SAVE", effect: "UPDATE", owner: "KnowledgeExperienceService", operation: "updateKnowledgeSource", method: "PATCH", path: "/v1/knowledge/sources/{sourceId}", permission: "knowledge.source.configure", errors: ["KB-01-ERR-002", "KB-01-ERR-003", "KB-01-ERR-004", "KB-01-ERR-013"], audit_event: "knowledge.source.updated" },
  { uid: "KB-01-ACT-SOURCE-PAUSE", effect: "STATE_TRANSITION", owner: "KnowledgeExperienceService", operation: "pauseKnowledgeSource", method: "POST", path: "/v1/knowledge/sources/{sourceId}/pause", permission: "knowledge.source.configure", errors: ["KB-01-ERR-003"], audit_event: "knowledge.source.paused" },
  { uid: "KB-01-ACT-SOURCE-RESUME", effect: "STATE_TRANSITION", owner: "KnowledgeExperienceService", operation: "resumeKnowledgeSource", method: "POST", path: "/v1/knowledge/sources/{sourceId}/resume", permission: "knowledge.source.configure", errors: ["KB-01-ERR-003", "KB-01-ERR-004"], audit_event: "knowledge.source.resumed" },
  { uid: "KB-01-ACT-SOURCE-RETIRE", effect: "STATE_TRANSITION", owner: "KnowledgeExperienceService", operation: "retireKnowledgeSource", method: "POST", path: "/v1/knowledge/sources/{sourceId}/retire", permission: "knowledge.source.configure", errors: ["KB-01-ERR-003", "KB-01-ERR-005"], audit_event: "knowledge.source.retired" },
  { uid: "KB-01-ACT-INGEST-START", effect: "CREATE_JOB", owner: "ACPOS_SHARED_EXTERNAL_DATA_ACQUISITION_RUNTIME", operation: "createAcquisitionJob", method: "POST", path: "/v1/acpos/acquisition/jobs", permission: "knowledge.ingestion.execute", errors: ["KB-01-ERR-004", "KB-01-ERR-005"], audit_event: "knowledge.ingestion.started" },
  { uid: "KB-01-ACT-INGEST-RETRY", effect: "RETRY", owner: "ACPOS_SHARED_EXTERNAL_DATA_ACQUISITION_RUNTIME", operation: "retryAcquisitionJob", method: "POST", path: "/v1/acpos/acquisition/jobs/{jobId}/retry", permission: "knowledge.ingestion.execute", errors: ["KB-01-ERR-006"], audit_event: "knowledge.ingestion.retry" },
  { uid: "KB-01-ACT-CONTEXT-ITEM-ADD", effect: "LOCAL_DRAFT_MUTATION", owner: "PAGE_UI_STATE", operation: "addContextDraftItem", method: "LOCAL", path: "LOCAL", permission: "knowledge.context.create", errors: [], audit_event: "" },
  { uid: "KB-01-ACT-CONTEXT-ITEM-REMOVE", effect: "LOCAL_DRAFT_MUTATION", owner: "PAGE_UI_STATE", operation: "removeContextDraftItem", method: "LOCAL", path: "LOCAL", permission: "knowledge.context.create", errors: [], audit_event: "" },
  { uid: "KB-01-ACT-CONTEXT-CANDIDATE-CREATE", effect: "CREATE", owner: "ACPOSContextEngine", operation: "createContextCandidate", method: "POST", path: "/v1/acpos/context-candidates", permission: "knowledge.context.create", errors: ["KB-01-ERR-002", "KB-01-ERR-007", "KB-01-ERR-008"], audit_event: "acpos.context_candidate.created" },
  { uid: "KB-01-ACT-REPLAY-OPEN", effect: "READ", owner: "ACPOSExperienceEngine", operation: "getExperienceReplay", method: "GET", path: "/v1/acpos/experience/{experienceId}/replay", permission: "knowledge.experience.read", errors: ["KB-01-ERR-001", "KB-01-ERR-010"], audit_event: "acpos.experience.replay.view" },
  { uid: "KB-01-ACT-REPLAY-COMPARE", effect: "READ_COMPARE", owner: "ACPOSExperienceEngine", operation: "compareExperienceReplay", method: "POST", path: "/v1/acpos/experience/replay/compare", permission: "knowledge.experience.read", errors: ["KB-01-ERR-010"], audit_event: "acpos.experience.replay.compare" },
  { uid: "KB-01-ACT-LEARNING-CREATE", effect: "CREATE", owner: "ACPOSEvolutionEngine", operation: "createLearningCandidate", method: "POST", path: "/v1/acpos/learning-candidates", permission: "knowledge.learning.create", errors: ["KB-01-ERR-009", "KB-01-ERR-010"], audit_event: "acpos.learning_candidate.created" },
  { uid: "KB-01-ACT-KNOWLEDGE-DRAFT-FROM-EXPERIENCE", effect: "CREATE", owner: "KnowledgeExperienceService", operation: "createKnowledgeDraftFromExperience", method: "POST", path: "/v1/knowledge/drafts/from-experience", permission: "knowledge.draft.write", errors: ["KB-01-ERR-009", "KB-01-ERR-010"], audit_event: "knowledge.draft.from_experience" },
  { uid: "KB-01-ACT-KNOWLEDGE-DRAFT-SAVE", effect: "UPDATE", owner: "KnowledgeExperienceService", operation: "saveKnowledgeDraft", method: "PATCH", path: "/v1/knowledge/drafts/{knowledgeId}", permission: "knowledge.draft.write", errors: ["KB-01-ERR-003", "KB-01-ERR-007", "KB-01-ERR-012"], audit_event: "knowledge.draft.saved" },
  { uid: "KB-01-ACT-KNOWLEDGE-VERSION-COMPARE", effect: "READ_COMPARE", owner: "KnowledgeExperienceService", operation: "compareKnowledgeVersions", method: "POST", path: "/v1/knowledge/versions/compare", permission: "knowledge.read", errors: ["KB-01-ERR-001"], audit_event: "knowledge.version.compare" },
  { uid: "KB-01-ACT-KNOWLEDGE-APPROVE", effect: "APPROVE", owner: "KnowledgeExperienceService", operation: "approveKnowledgeDraft", method: "POST", path: "/v1/knowledge/drafts/{knowledgeId}/approve", permission: "knowledge.review.approve", errors: ["KB-01-ERR-003", "KB-01-ERR-007", "KB-01-ERR-011", "KB-01-ERR-012"], audit_event: "knowledge.approved" },
  { uid: "KB-01-ACT-KNOWLEDGE-RETURN", effect: "REVIEW_DECISION", owner: "KnowledgeExperienceService", operation: "returnKnowledgeDraft", method: "POST", path: "/v1/knowledge/drafts/{knowledgeId}/return", permission: "knowledge.review.approve", errors: ["KB-01-ERR-003", "KB-01-ERR-011"], audit_event: "knowledge.returned" },
  { uid: "KB-01-ACT-KNOWLEDGE-REJECT", effect: "REVIEW_DECISION", owner: "KnowledgeExperienceService", operation: "rejectKnowledgeDraft", method: "POST", path: "/v1/knowledge/drafts/{knowledgeId}/reject", permission: "knowledge.review.approve", errors: ["KB-01-ERR-003", "KB-01-ERR-011"], audit_event: "knowledge.rejected" },
] as const;

const ACTION_BY_UID = new Map(KNOWLEDGE_ACTIONS.map((action) => [action.uid, action]));

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function normalizeTestMetadata(value: unknown): KnowledgeProjectionTestMetadata | undefined {
  const metadata = asRecord(value);
  if (!metadata) return undefined;
  if (!isControlledTestMode()) throw new Error("KB01_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION");
  if (
    metadata.data_classification !== "TEST_ONLY" ||
    metadata.synthetic !== true ||
    metadata.created_for_validation !== true ||
    metadata.production_eligible !== false ||
    typeof metadata.test_dataset_id !== "string" ||
    typeof metadata.test_run_id !== "string"
  ) throw new Error("KB01_TEST_PROJECTION_METADATA_INVALID");
  return metadata as unknown as KnowledgeProjectionTestMetadata;
}

function normalizeKnowledgeProjection(raw: unknown): KnowledgeProjection {
  const record = asRecord(raw);
  if (!record) throw new Error("KB01_PROJECTION_NOT_OBJECT");

  const valuesRaw = asRecord(record.values) ?? {};
  const controlsRaw = asRecord(record.control_enabled) ?? {};
  const values: Record<string, string> = {};
  const control_enabled: Record<string, boolean> = {};

  for (const [key, value] of Object.entries(valuesRaw)) if (typeof value === "string") values[key] = value;
  for (const [key, value] of Object.entries(controlsRaw)) if (typeof value === "boolean") control_enabled[key] = value;

  let page_state: KnowledgePageState | null = null;
  if (record.page_state !== null && record.page_state !== undefined) {
    if (typeof record.page_state !== "string" || !ALLOWED_PAGE_STATES.has(record.page_state as KnowledgePageState)) {
      throw new Error("KB01_PROJECTION_STATE_UNREGISTERED");
    }
    page_state = record.page_state as KnowledgePageState;
  }

  return {
    page_state,
    values,
    control_enabled,
    ...(record.test_metadata ? { test_metadata: normalizeTestMetadata(record.test_metadata) } : {}),
  };
}

export function getKnowledgeActionTrace(actionUid?: string): KnowledgeActionTrace | null {
  return actionUid ? ACTION_BY_UID.get(actionUid) ?? null : null;
}

export async function readKnowledgeProjection(signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/admin%3AKB-01", { method: "GET", cache: "no-store", signal });
  } catch {
    return { ok: false as const, reason_code: "KB01_PROJECTION_REQUEST_FAILED", correlation_id: "unresolved" };
  }

  const headerCorrelation = response.headers.get("x-correlation-id") ?? "unresolved";
  const raw: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const body = asRecord(raw);
    return {
      ok: false as const,
      reason_code: typeof body?.reason_code === "string" ? body.reason_code : "KB01_PROJECTION_READ_FAILED",
      correlation_id: typeof body?.correlation_id === "string" ? body.correlation_id : headerCorrelation,
    };
  }

  try {
    return { ok: true as const, projection: normalizeKnowledgeProjection(raw), correlation_id: headerCorrelation };
  } catch {
    return { ok: false as const, reason_code: "KB01_PROJECTION_ADAPTER_REJECTED", correlation_id: headerCorrelation };
  }
}
