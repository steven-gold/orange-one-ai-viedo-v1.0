export const KNOWLEDGE_OPERATIONS = [
  "searchKnowledge",
  "getCitation",
  "createKnowledgeSource",
  "updateKnowledgeSource",
  "pauseKnowledgeSource",
  "resumeKnowledgeSource",
  "retireKnowledgeSource",
  "createAcquisitionJob",
  "retryAcquisitionJob",
  "createContextCandidate",
  "getExperienceReplay",
  "compareExperienceReplay",
  "createLearningCandidate",
  "createKnowledgeDraftFromExperience",
  "saveKnowledgeDraft",
  "compareKnowledgeVersions",
  "approveKnowledgeDraft",
  "returnKnowledgeDraft",
  "rejectKnowledgeDraft",
] as const;

export type KnowledgeOperation = (typeof KNOWLEDGE_OPERATIONS)[number];

export type KnowledgeRuntimeRequest = {
  operation: KnowledgeOperation;
  correlation_id: string;
  path_params: Record<string, string>;
  payload?: unknown;
};

export type KnowledgeRuntimeResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; error_uid: string; reason_code: string; correlation_id: string; status: number };

export const KNOWLEDGE_ERROR_UIDS = {
  KB_PERMISSION_DENIED: "KB-01-ERR-001",
  KB_SCOPE_INVALID: "KB-01-ERR-002",
  KB_VERSION_CONFLICT: "KB-01-ERR-003",
  KB_SOURCE_RIGHTS_INVALID: "KB-01-ERR-004",
  KB_DUPLICATE_ACTIVE_RUN: "KB-01-ERR-005",
  KB_INGESTION_NOT_RETRYABLE: "KB-01-ERR-006",
  KB_CITATION_REQUIRED: "KB-01-ERR-007",
  KB_CONTEXT_CONFLICT: "KB-01-ERR-008",
  KB_OUTCOME_PENDING: "KB-01-ERR-009",
  KB_LINEAGE_INCOMPLETE: "KB-01-ERR-010",
  KB_REVIEW_CHECK_INCOMPLETE: "KB-01-ERR-011",
  KB_AUTHORITY_CONFLICT: "KB-01-ERR-012",
  KB_RAW_SECRET_FORBIDDEN: "KB-01-ERR-013",
  KB_UNSUPPORTED_OPERATION: "KB-01-ERR-014",
} as const;

export type KnowledgeErrorUid = (typeof KNOWLEDGE_ERROR_UIDS)[keyof typeof KNOWLEDGE_ERROR_UIDS];
