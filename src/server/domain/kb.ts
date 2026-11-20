export const KB_PERMISSION = "knowledge.read";
export const KB_PAGE_UID = "admin:KB-01";
export const KB_ROUTE = "/admin/knowledge";
export const KB_PROJECTION = "KbWorkbenchProjection";
export const KB_CHAIN = "ADMIN-KB-01-FWC-PAGE-01";

export const KB_VISIBLE_CONTROLS = [
  "CTRL-ADMIN-KB-01-VIEW-OVERVIEW",
  "CTRL-ADMIN-KB-01-VIEW-SOURCE",
  "CTRL-ADMIN-KB-01-VIEW-SEARCH",
  "CTRL-ADMIN-KB-01-VIEW-EXPERIENCE",
  "CTRL-ADMIN-KB-01-VIEW-REVIEW",
  "CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL",
  "CTRL-ADMIN-KB-01-ACT-SEARCH",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-PAUSE",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RESUME",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE",
  "CTRL-ADMIN-KB-01-ACT-INGEST-START",
  "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY",
  "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-COMPARE",
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE",
  "CTRL-ADMIN-KB-01-ACT-VERSION-COMPARE",
  "CTRL-ADMIN-KB-01-ACT-APPROVE",
  "CTRL-ADMIN-KB-01-ACT-RETURN",
  "CTRL-ADMIN-KB-01-ACT-REJECT",
] as const;

export const KB_CONTROL_ACTIONS: Record<string, string> = {
  "CTRL-ADMIN-KB-01-VIEW-OVERVIEW": "getUiProjection",
  "CTRL-ADMIN-KB-01-VIEW-SOURCE": "getUiProjection",
  "CTRL-ADMIN-KB-01-VIEW-SEARCH": "getUiProjection",
  "CTRL-ADMIN-KB-01-VIEW-EXPERIENCE": "getUiProjection",
  "CTRL-ADMIN-KB-01-VIEW-REVIEW": "getUiProjection",
  "CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL": "searchKnowledge",
  "CTRL-ADMIN-KB-01-ACT-SEARCH": "searchKnowledge",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE": "createKnowledgeSource",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE": "updateKnowledgeSource",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-PAUSE": "pauseKnowledgeSource",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RESUME": "resumeKnowledgeSource",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE": "retireKnowledgeSource",
  "CTRL-ADMIN-KB-01-ACT-INGEST-START": "createAcquisitionJob",
  "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY": "retryAcquisitionJob",
  "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN": "getCitation",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD": "addContextDraftItem",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE": "removeContextDraftItem",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE": "createContextCandidate",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN": "getExperienceReplay",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-COMPARE": "compareExperienceReplay",
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE": "createLearningCandidate",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP": "createKnowledgeDraftFromExperience",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE": "saveKnowledgeDraft",
  "CTRL-ADMIN-KB-01-ACT-VERSION-COMPARE": "compareKnowledgeVersions",
  "CTRL-ADMIN-KB-01-ACT-APPROVE": "approveKnowledgeDraft",
  "CTRL-ADMIN-KB-01-ACT-RETURN": "returnKnowledgeDraft",
  "CTRL-ADMIN-KB-01-ACT-REJECT": "rejectKnowledgeDraft",
};

export const KB_ACTION_SCOPES: Record<string, string> = {
  searchKnowledge: "knowledge.read",
  getCitation: "knowledge.read",
  createKnowledgeSource: "knowledge.source.configure",
  updateKnowledgeSource: "knowledge.source.configure",
  pauseKnowledgeSource: "knowledge.source.configure",
  resumeKnowledgeSource: "knowledge.source.configure",
  retireKnowledgeSource: "knowledge.source.configure",
  createAcquisitionJob: "knowledge.ingestion.execute",
  retryAcquisitionJob: "knowledge.ingestion.execute",
  addContextDraftItem: "knowledge.context.create",
  removeContextDraftItem: "knowledge.context.create",
  createContextCandidate: "knowledge.context.create",
  getExperienceReplay: "knowledge.experience.read",
  compareExperienceReplay: "knowledge.experience.read",
  createLearningCandidate: "knowledge.learning.create",
  createKnowledgeDraftFromExperience: "knowledge.draft.write",
  saveKnowledgeDraft: "knowledge.draft.write",
  compareKnowledgeVersions: "knowledge.read",
  approveKnowledgeDraft: "knowledge.review.approve",
  returnKnowledgeDraft: "knowledge.review.approve",
  rejectKnowledgeDraft: "knowledge.review.approve",
};

export const KB_PERMISSIONS = {
  READ: "knowledge.read",
  SOURCE_READ: "knowledge.source.read",
  SOURCE_CONFIGURE: "knowledge.source.configure",
  INGESTION_READ: "knowledge.ingestion.read",
  INGESTION_EXECUTE: "knowledge.ingestion.execute",
  CONTEXT_CREATE: "knowledge.context.create",
  EXPERIENCE_READ: "knowledge.experience.read",
  LEARNING_CREATE: "knowledge.learning.create",
  DRAFT_WRITE: "knowledge.draft.write",
  REVIEW_APPROVE: "knowledge.review.approve",
} as const;

// Contract layout: views and their registered operations
// (A: lists in layout.views + T:SEARCH-GLOBAL in S:01).
export const KB_VIEWS = [
  "KB-01-VIEW-OVERVIEW",
  "KB-01-VIEW-SOURCE",
  "KB-01-VIEW-SEARCH",
  "KB-01-VIEW-EXPERIENCE",
  "KB-01-VIEW-REVIEW",
] as const;

export type KbView = (typeof KB_VIEWS)[number];

export const KB_VIEW_CONTROLS: Record<KbView, string> = {
  "KB-01-VIEW-OVERVIEW": "CTRL-ADMIN-KB-01-VIEW-OVERVIEW",
  "KB-01-VIEW-SOURCE": "CTRL-ADMIN-KB-01-VIEW-SOURCE",
  "KB-01-VIEW-SEARCH": "CTRL-ADMIN-KB-01-VIEW-SEARCH",
  "KB-01-VIEW-EXPERIENCE": "CTRL-ADMIN-KB-01-VIEW-EXPERIENCE",
  "KB-01-VIEW-REVIEW": "CTRL-ADMIN-KB-01-VIEW-REVIEW",
};

export const KB_VIEW_OPERATIONS: Record<string, string[]> = {
  "KB-01-VIEW-OVERVIEW": ["getUiProjection", "searchKnowledge"],
  "KB-01-VIEW-SOURCE": [
    "getUiProjection",
    "createKnowledgeSource",
    "updateKnowledgeSource",
    "pauseKnowledgeSource",
    "resumeKnowledgeSource",
    "retireKnowledgeSource",
    "createAcquisitionJob",
    "retryAcquisitionJob",
  ],
  "KB-01-VIEW-SEARCH": [
    "getUiProjection",
    "searchKnowledge",
    "getCitation",
    "addContextDraftItem",
    "removeContextDraftItem",
    "createContextCandidate",
  ],
  "KB-01-VIEW-EXPERIENCE": [
    "getUiProjection",
    "getExperienceReplay",
    "compareExperienceReplay",
    "createLearningCandidate",
    "createKnowledgeDraftFromExperience",
  ],
  "KB-01-VIEW-REVIEW": [
    "getUiProjection",
    "saveKnowledgeDraft",
    "compareKnowledgeVersions",
    "approveKnowledgeDraft",
    "returnKnowledgeDraft",
    "rejectKnowledgeDraft",
  ],
};

export const KB_CONTROL_VIEWS: Record<string, string[]> = {
  "CTRL-ADMIN-KB-01-VIEW-OVERVIEW": ["KB-01-VIEW-OVERVIEW"],
  "CTRL-ADMIN-KB-01-VIEW-SOURCE": ["KB-01-VIEW-SOURCE"],
  "CTRL-ADMIN-KB-01-VIEW-SEARCH": ["KB-01-VIEW-SEARCH"],
  "CTRL-ADMIN-KB-01-VIEW-EXPERIENCE": ["KB-01-VIEW-EXPERIENCE"],
  "CTRL-ADMIN-KB-01-VIEW-REVIEW": ["KB-01-VIEW-REVIEW"],
  "CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL": ["KB-01-VIEW-OVERVIEW"],
  "CTRL-ADMIN-KB-01-ACT-SEARCH": ["KB-01-VIEW-SEARCH"],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE": ["KB-01-VIEW-SOURCE"],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE": ["KB-01-VIEW-SOURCE"],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-PAUSE": ["KB-01-VIEW-SOURCE"],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RESUME": ["KB-01-VIEW-SOURCE"],
  "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE": ["KB-01-VIEW-SOURCE"],
  "CTRL-ADMIN-KB-01-ACT-INGEST-START": ["KB-01-VIEW-SOURCE"],
  "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY": ["KB-01-VIEW-SOURCE"],
  "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN": ["KB-01-VIEW-SEARCH"],
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD": ["KB-01-VIEW-SEARCH"],
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE": ["KB-01-VIEW-SEARCH"],
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE": ["KB-01-VIEW-SEARCH"],
  "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN": ["KB-01-VIEW-EXPERIENCE"],
  "CTRL-ADMIN-KB-01-ACT-REPLAY-COMPARE": ["KB-01-VIEW-EXPERIENCE"],
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE": ["KB-01-VIEW-EXPERIENCE"],
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP": ["KB-01-VIEW-EXPERIENCE"],
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE": ["KB-01-VIEW-REVIEW"],
  "CTRL-ADMIN-KB-01-ACT-VERSION-COMPARE": ["KB-01-VIEW-REVIEW"],
  "CTRL-ADMIN-KB-01-ACT-APPROVE": ["KB-01-VIEW-REVIEW"],
  "CTRL-ADMIN-KB-01-ACT-RETURN": ["KB-01-VIEW-REVIEW"],
  "CTRL-ADMIN-KB-01-ACT-REJECT": ["KB-01-VIEW-REVIEW"],
};

export type KbSourceStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "RETIRED";
export type KbRunStatus = "PENDING" | "RUNNING" | "NORMALIZING" | "COMPLETED" | "FAILED" | "RETRY_ELIGIBLE";
export type KbContextState = "DRAFT" | "READY_FOR_CONSUMER_REVIEW" | "ADOPTED" | "REJECTED" | "RETIRED";
export type KbExperienceState = "CAPTURED" | "OUTCOME_PENDING" | "OUTCOME_COMPLETE" | "REPLAY_READY";
export type KbLearningState = "DRAFT" | "REVIEW" | "ADOPTED" | "REJECTED" | "SUPERSEDED";
export type KbDraftState = "DRAFT" | "REVIEW" | "APPROVED" | "RETURNED" | "REJECTED" | "SUPERSEDED" | "RETIRED";

export const KB_STATE_ERROR_UID = "KB-01-STATE-ERROR";
export const KB_STATE_AUDIT_UID = "KB-01-STATE-AUDIT";
export const KB_STATE_IDEMPOTENCY_UID = "KB-01-STATE-IDEMPOTENCY";
export const KB_STATE_SOURCES_UID = "KB-01-STATE-SOURCES";
export const KB_STATE_RUNS_UID = "KB-01-STATE-RUNS";
export const KB_STATE_RESULTS_UID = "KB-01-STATE-RESULTS";
export const KB_STATE_CITATIONS_UID = "KB-01-STATE-CITATIONS";
export const KB_STATE_BASKET_UID = "KB-01-STATE-BASKET";
export const KB_STATE_CANDIDATES_UID = "KB-01-STATE-CANDIDATES";
export const KB_STATE_EXPERIENCE_UID = "KB-01-STATE-EXPERIENCE";
export const KB_STATE_REPLAY_UID = "KB-01-STATE-REPLAY";
export const KB_STATE_LEARNING_UID = "KB-01-STATE-LEARNING";
export const KB_STATE_DRAFTS_UID = "KB-01-STATE-DRAFTS";

export interface KbFieldValue {
  controlUid: string;
  value: string | null;
}

export interface KbReadModel {
  projectionUid: typeof KB_PROJECTION;
  pageUid: typeof KB_PAGE_UID;
  route: typeof KB_ROUTE;
  permission: typeof KB_PERMISSION;
  chainUid: typeof KB_CHAIN;
  authorized: boolean;
  fields: KbFieldValue[];
}
