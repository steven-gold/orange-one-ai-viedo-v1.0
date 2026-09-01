import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { KNOWLEDGE_ERROR_UIDS, KNOWLEDGE_OPERATIONS, type KnowledgeErrorUid, type KnowledgeOperation, type KnowledgeRuntimeRequest, type KnowledgeRuntimeResult } from "@/domain/knowledge/knowledgeRuntimeContract";

const TEST_METADATA = {
  data_classification: "TEST_ONLY",
  synthetic: true,
  test_dataset_id: "TEST-KB-01",
  test_run_id: "TEST-RUN-KB-01-CONTROLLED",
  created_for_validation: true,
  production_eligible: false,
} as const;

type SourceState = "DRAFT" | "ACTIVE" | "PAUSED" | "RETIRED";
type RunState = "PENDING" | "RUNNING" | "NORMALIZING" | "COMPLETED" | "FAILED" | "RETRY_ELIGIBLE";
type ContextCandidateState = "DRAFT" | "READY_FOR_CONSUMER_REVIEW" | "ADOPTED" | "REJECTED" | "RETIRED";
type ExperienceState = "CAPTURED" | "OUTCOME_PENDING" | "OUTCOME_COMPLETE" | "REPLAY_READY";
type LearningState = "DRAFT" | "REVIEW" | "ADOPTED" | "REJECTED" | "SUPERSEDED";
type KnowledgeState = "DRAFT" | "REVIEW" | "APPROVED" | "RETURNED" | "REJECTED" | "SUPERSEDED" | "RETIRED";

type KnowledgeSource = {
  source_id: string; source_version: number; name: string; source_type: string; scope: string;
  rights: string; classification: string; collection_method: string; collection_config: unknown;
  freshness_policy: string; retention_policy: string; status: SourceState;
};
type IngestionRun = {
  run_id: string; source_ref: string; run_type: string; status: RunState; progress: number;
  started_at: string; ended_at: string | null; raw_output_refs: string[]; normalized_refs: string[];
  evidence_refs: string[]; failure_ref: string | null; retry_eligible: boolean;
};
type SearchResult = {
  result_ref: string; classification_type: string; title: string; scope: string; source_ref: string;
  source_time: string; source_version: number; freshness_state: string; review_state: string;
};
type Citation = {
  citation_id: string; source_ref: string; source_location: string; source_time: string;
  source_version: number; checksum: string; classification: string; evidence_ref: string;
};
type ContextCandidate = {
  context_candidate_id: string; version: number; purpose: string; scope: string;
  selected_refs: string[]; evidence_refs: string[]; state: ContextCandidateState; context_fingerprint: string;
};
type ExperienceRecord = {
  experience_id: string; domain: string; department: string; task_type: string;
  provider_model_ref: string; route_decision_ref: string; attempt_count: number; latency_ms: number;
  state: ExperienceState; lineage_complete: boolean;
};
type ReplayProjection = {
  experience_id: string; source_input_refs: string[]; instruction_refs: string[]; route_refs: string[];
  output_refs: string[]; evaluation_refs: string[]; correction_refs: string[]; outcome_refs: string[];
  root_cause: string;
};
type LearningCandidate = {
  learning_candidate_id: string; version: number; scope: string; pattern: string;
  proposed_improvement: string; evidence_refs: string[]; limitations: string; state: LearningState;
};
type KnowledgeVersion = {
  knowledge_id: string; draft_version: number; title: string; knowledge_type: string;
  summary: string; content: string; scope: string; classification: string; citation_refs: string[];
  outcome_refs: string[]; experience_refs: string[]; review_state: KnowledgeState;
  previous_approved_version_ref: string | null;
};
type AuditEntry = {
  audit_ref: string;
  event: string;
  subject_ref: string;
  correlation_id: string;
  outcome: "SUCCESS" | "DENIED" | "ERROR";
  reason_code?: string;
};

type ControlledState = {
  sources: KnowledgeSource[];
  runs: IngestionRun[];
  results: SearchResult[];
  citations: Citation[];
  contextCandidates: ContextCandidate[];
  experiences: ExperienceRecord[];
  learnings: LearningCandidate[];
  drafts: KnowledgeVersion[];
  audits: AuditEntry[];
  audit_counter: number;
  idempotency: Map<string, { ok: boolean; value?: unknown; reason_code?: string; error_uid?: string }>;
  entity_counter: number;
};

const state: ControlledState = {
  sources: [], runs: [], results: [], citations: [], contextCandidates: [], experiences: [], learnings: [], drafts: [],
  audits: [], audit_counter: 0, idempotency: new Map(), entity_counter: 0,
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
function textList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
}
function seedFixture() {
  if (state.sources.length > 0) return;
  state.sources.push(
    { source_id: "TEST-KB-SOURCE-ACTIVE-001", source_version: 3, name: "Test Registered Knowledge Source", source_type: "WEB_CRAWL", scope: "SCOPE-KNOWLEDGE-PUBLIC", rights: "REGISTERED_CONNECTOR", classification: "INTERNAL", collection_method: "SCHEDULED_CRAWL", collection_config: { max_depth: 2 }, freshness_policy: "DAILY_REFRESH", retention_policy: "RETAIN_365D", status: "ACTIVE" },
    { source_id: "TEST-KB-SOURCE-DRAFT-001", source_version: 1, name: "Test Draft Knowledge Source", source_type: "WEB_FETCH", scope: "SCOPE-KNOWLEDGE-PUBLIC", rights: "REGISTERED_CONNECTOR", classification: "INTERNAL", collection_method: "MANUAL_FETCH", collection_config: null, freshness_policy: "WEEKLY_REFRESH", retention_policy: "RETAIN_90D", status: "DRAFT" },
  );
  state.runs.push(
    { run_id: "TEST-KB-RUN-RETRY-001", source_ref: "TEST-KB-SOURCE-ACTIVE-001", run_type: "WEB_CRAWL", status: "RETRY_ELIGIBLE", progress: 42, started_at: "2026-08-30T09:00:00Z", ended_at: "2026-08-30T09:05:00Z", raw_output_refs: ["TEST-KB-RAW-001"], normalized_refs: [], evidence_refs: [], failure_ref: "TEST-KB-FAIL-001", retry_eligible: true },
  );
  state.results.push(
    { result_ref: "TEST-KB-RESULT-KN-001", classification_type: "KNOWLEDGE", title: "Approved knowledge entry", scope: "SCOPE-KNOWLEDGE-PUBLIC", source_ref: "TEST-KB-SOURCE-ACTIVE-001", source_time: "2026-08-29T00:00:00Z", source_version: 2, freshness_state: "FRESH", review_state: "APPROVED" },
    { result_ref: "TEST-KB-RESULT-FACT-001", classification_type: "FACT", title: "Traceable fact with citation", scope: "SCOPE-KNOWLEDGE-PUBLIC", source_ref: "TEST-KB-SOURCE-ACTIVE-001", source_time: "2026-08-29T00:00:00Z", source_version: 2, freshness_state: "FRESH", review_state: "APPROVED" },
    { result_ref: "TEST-KB-RESULT-EVD-001", classification_type: "EVIDENCE", title: "Evidence snapshot", scope: "SCOPE-KNOWLEDGE-PUBLIC", source_ref: "TEST-KB-SOURCE-ACTIVE-001", source_time: "2026-08-29T00:00:00Z", source_version: 2, freshness_state: "FRESH", review_state: "APPROVED" },
  );
  state.citations.push(
    { citation_id: "TEST-KB-CIT-001", source_ref: "TEST-KB-SOURCE-ACTIVE-001", source_location: "page-3#section-2", source_time: "2026-08-29T00:00:00Z", source_version: 2, checksum: "sha256:TEST-CITATION-CHECKSUM", classification: "INTERNAL", evidence_ref: "TEST-KB-RESULT-EVD-001" },
  );
  state.experiences.push(
    { experience_id: "TEST-KB-EXP-001", domain: "VIDEO_PRODUCTION", department: "DEPT-ACPOS", task_type: "topic-to-script", provider_model_ref: "TEST-PROVIDER-REF-001", route_decision_ref: "TEST-ROUTE-REF-001", attempt_count: 2, latency_ms: 8200, state: "OUTCOME_COMPLETE", lineage_complete: true },
  );
  state.drafts.push(
    { knowledge_id: "TEST-KB-DRAFT-001", draft_version: 1, title: "Test knowledge draft", knowledge_type: "OPERATING_GUIDE", summary: "Test summary", content: "Test content", scope: "SCOPE-KNOWLEDGE-PUBLIC", classification: "INTERNAL", citation_refs: ["TEST-KB-CIT-001"], outcome_refs: [], experience_refs: ["TEST-KB-EXP-001"], review_state: "DRAFT", previous_approved_version_ref: "TEST-KB-KN-APPROVED-001" },
    { knowledge_id: "TEST-KB-DRAFT-REVIEW-001", draft_version: 2, title: "Test knowledge draft in review", knowledge_type: "OPERATING_GUIDE", summary: "Review summary", content: "Review content", scope: "SCOPE-KNOWLEDGE-PUBLIC", classification: "INTERNAL", citation_refs: ["TEST-KB-CIT-001"], outcome_refs: ["TEST-KB-OUTCOME-001"], experience_refs: ["TEST-KB-EXP-001"], review_state: "REVIEW", previous_approved_version_ref: "TEST-KB-KN-APPROVED-001" },
    { knowledge_id: "TEST-KB-KN-APPROVED-001", draft_version: 5, title: "Approved knowledge v5", knowledge_type: "OPERATING_GUIDE", summary: "Approved summary", content: "Approved content", scope: "SCOPE-KNOWLEDGE-PUBLIC", classification: "INTERNAL", citation_refs: ["TEST-KB-CIT-001"], outcome_refs: [], experience_refs: [], review_state: "APPROVED", previous_approved_version_ref: null },
  );
}
function appendAudit(entry: Omit<AuditEntry, "audit_ref">): AuditEntry {
  state.audit_counter += 1;
  const full: AuditEntry = { ...entry, audit_ref: `TEST-KB01-AUDIT-${String(state.audit_counter).padStart(3, "0")}` };
  state.audits = [full, ...state.audits].slice(0, 10);
  return full;
}
function nextEntityId(prefix: string): string {
  state.entity_counter += 1;
  return `TEST-KB-${prefix}-${String(state.entity_counter).padStart(3, "0")}`;
}
function findSource(id: string | null) { return id ? state.sources.find(item => item.source_id === id) ?? null : null; }
function findRun(id: string | null) { return id ? state.runs.find(item => item.run_id === id) ?? null : null; }
function findExperience(id: string | null) { return id ? state.experiences.find(item => item.experience_id === id) ?? null : null; }
function findDraft(id: string | null) { return id ? state.drafts.find(item => item.knowledge_id === id) ?? null : null; }
function selectedSource(): KnowledgeSource | null {
  return state.sources.find(item => item.status === "ACTIVE") ?? state.sources.find(item => item.status !== "RETIRED") ?? null;
}
function selectedRun(): IngestionRun | null {
  return state.runs.find(item => item.status === "RETRY_ELIGIBLE" && item.retry_eligible) ?? state.runs[state.runs.length - 1] ?? null;
}
function selectedExperience(): ExperienceRecord | null { return state.experiences[0] ?? null; }
function draftDraft(): KnowledgeVersion | null { return state.drafts.find(item => item.review_state === "DRAFT") ?? null; }
function reviewDraft(): KnowledgeVersion | null { return state.drafts.find(item => item.review_state === "REVIEW") ?? null; }
function approvedKnowledge(): KnowledgeVersion | null { return state.drafts.find(item => item.review_state === "APPROVED") ?? null; }
function hasActiveNonCancelableRun(): boolean { return state.runs.some(item => item.status === "RUNNING" || item.status === "NORMALIZING"); }

// TEST-ONLY: simulates ACPOS_SHARED_EXTERNAL_DATA_ACQUISITION_RUNTIME driving the run
// state machine forward (PENDING->RUNNING->NORMALIZING->COMPLETED) between projection reads.
function advanceRuns() {
  for (const run of state.runs) {
    if (run.status === "RUNNING") run.status = "NORMALIZING";
    else if (run.status === "NORMALIZING") { run.status = "COMPLETED"; run.ended_at = new Date().toISOString(); }
  }
}

type GateFailure = { ok: false; error_uid: KnowledgeErrorUid; reason_code: string; status: number };

function fail(error_uid: KnowledgeErrorUid, reason_code: string, status = 403): GateFailure {
  return { ok: false, error_uid, reason_code, status };
}

function expectedVersionOf(payload: Record<string, unknown>, id: string | null): number | null {
  const raw = payload.expected_version ?? payload.expected_source_version;
  if (raw === undefined || raw === null) return null;
  const version = Number(raw);
  return Number.isFinite(version) ? version : -1;
}
function versionGuard(payload: Record<string, unknown>, id: string | null, actual: number | null): GateFailure | null {
  if (!id) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_ENTITY_REF_MISSING");
  const expected = expectedVersionOf(payload, id);
  if (expected === null) return fail(KNOWLEDGE_ERROR_UIDS.KB_VERSION_CONFLICT, "KB01_EXPECTED_VERSION_MISSING");
  if (actual === null || expected !== actual) return fail(KNOWLEDGE_ERROR_UIDS.KB_VERSION_CONFLICT, "KB_VERSION_CONFLICT");
  return null;
}
function idempotencyGuard(payload: Record<string, unknown>): GateFailure | null {
  if (!text(payload.idempotency_key)) return fail(KNOWLEDGE_ERROR_UIDS.KB_UNSUPPORTED_OPERATION, "KB01_IDEMPOTENCY_KEY_REQUIRED", 400);
  return null;
}

function evaluateGates(operation: KnowledgeOperation, request: KnowledgeRuntimeRequest): GateFailure | null {
  const payload = record(request.payload);
  const pathId = text(request.path_params.sourceId) ?? text(request.path_params.jobId) ?? text(request.path_params.experienceId) ?? text(request.path_params.knowledgeId) ?? text(request.path_params.citationId);
  switch (operation) {
    case "searchKnowledge": {
      if (!text(payload.query) || !text(payload.scope)) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_SEARCH_QUERY_AND_SCOPE_REQUIRED", 400);
      return null;
    }
    case "getCitation": {
      const citation = state.citations.find(item => item.citation_id === pathId);
      if (!citation) return fail(KNOWLEDGE_ERROR_UIDS.KB_PERMISSION_DENIED, "KB01_CITATION_NOT_FOUND");
      return null;
    }
    case "createKnowledgeSource": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      for (const key of ["name", "source_type", "scope", "rights", "classification", "collection_method", "freshness_policy", "retention_policy"]) {
        if (!text(payload[key])) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_REQUIRED_SOURCE_FIELD_MISSING", 400);
      }
      if (payload.raw_secret !== undefined || payload.credential_plaintext !== undefined) return fail(KNOWLEDGE_ERROR_UIDS.KB_RAW_SECRET_FORBIDDEN, "KB_RAW_SECRET_FORBIDDEN");
      return null;
    }
    case "updateKnowledgeSource": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const source = findSource(text(payload.source_id) ?? pathId);
      if (!source) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_SOURCE_NOT_FOUND");
      const guard = versionGuard(payload, source.source_id, source.source_version); if (guard) return guard;
      if (source.status === "RETIRED") return fail(KNOWLEDGE_ERROR_UIDS.KB_SOURCE_RIGHTS_INVALID, "KB01_SOURCE_RETIRED_IMMUTABLE");
      if (payload.raw_secret !== undefined || payload.credential_plaintext !== undefined || payload.status_direct_write !== undefined) return fail(KNOWLEDGE_ERROR_UIDS.KB_RAW_SECRET_FORBIDDEN, "KB_RAW_SECRET_FORBIDDEN");
      return null;
    }
    case "pauseKnowledgeSource": case "resumeKnowledgeSource": case "retireKnowledgeSource": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const source = findSource(text(payload.source_id) ?? pathId);
      if (!source) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_SOURCE_NOT_FOUND");
      const guard = versionGuard(payload, source.source_id, source.source_version); if (guard) return guard;
      if (operation === "pauseKnowledgeSource" && source.status !== "ACTIVE") return fail(KNOWLEDGE_ERROR_UIDS.KB_SOURCE_RIGHTS_INVALID, source.status === "PAUSED" ? "KB01_SOURCE_ALREADY_PAUSED" : "KB01_SOURCE_STATE_GUARD_REJECTED");
      if (operation === "resumeKnowledgeSource") {
        if (source.status !== "PAUSED") return fail(KNOWLEDGE_ERROR_UIDS.KB_SOURCE_RIGHTS_INVALID, "KB01_SOURCE_NOT_PAUSED");
      }
      if (operation === "retireKnowledgeSource" && hasActiveNonCancelableRun()) return fail(KNOWLEDGE_ERROR_UIDS.KB_DUPLICATE_ACTIVE_RUN, "KB_DUPLICATE_ACTIVE_RUN");
      return null;
    }
    case "createAcquisitionJob": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const source = findSource(text(payload.source_ref));
      if (!source) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_SOURCE_REF_NOT_FOUND");
      if (source.status !== "ACTIVE") return fail(KNOWLEDGE_ERROR_UIDS.KB_SOURCE_RIGHTS_INVALID, "KB01_SOURCE_NOT_ACTIVE");
      if (hasActiveNonCancelableRun()) return fail(KNOWLEDGE_ERROR_UIDS.KB_DUPLICATE_ACTIVE_RUN, "KB_DUPLICATE_ACTIVE_RUN");
      return null;
    }
    case "retryAcquisitionJob": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const run = findRun(text(payload.run_id) ?? pathId);
      if (!run) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_RUN_NOT_FOUND");
      if (run.status !== "RETRY_ELIGIBLE" || !run.retry_eligible) return fail(KNOWLEDGE_ERROR_UIDS.KB_INGESTION_NOT_RETRYABLE, "KB_INGESTION_NOT_RETRYABLE");
      return null;
    }
    case "createContextCandidate": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      if (!text(payload.purpose) || !text(payload.scope)) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_CONTEXT_PURPOSE_AND_SCOPE_REQUIRED");
      const selectedRefs = textList(payload.selected_refs);
      if (selectedRefs.length === 0) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_CONTEXT_EMPTY_SELECTION");
      const traceable = new Set([...state.results.map(item => item.result_ref), ...state.citations.map(item => item.citation_id)]);
      if (!selectedRefs.every(ref => traceable.has(ref))) return fail(KNOWLEDGE_ERROR_UIDS.KB_CITATION_REQUIRED, "KB_CITATION_REQUIRED");
      return null;
    }
    case "getExperienceReplay": {
      const experience = findExperience(pathId);
      if (!experience) return fail(KNOWLEDGE_ERROR_UIDS.KB_PERMISSION_DENIED, "KB01_EXPERIENCE_NOT_FOUND");
      if (!experience.lineage_complete) return fail(KNOWLEDGE_ERROR_UIDS.KB_LINEAGE_INCOMPLETE, "KB_LINEAGE_INCOMPLETE");
      return null;
    }
    case "compareExperienceReplay": {
      const refs = textList(payload.compare_refs);
      if (refs.length < 2) return fail(KNOWLEDGE_ERROR_UIDS.KB_LINEAGE_INCOMPLETE, "KB01_REPLAY_INSUFFICIENT_COMPARABLE_ITEMS");
      return null;
    }
    case "createLearningCandidate": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const refs = textList(payload.experience_refs);
      if (refs.length === 0) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_LEARNING_EXPERIENCE_REF_REQUIRED", 400);
      for (const ref of refs) {
        const experience = findExperience(ref);
        if (!experience) return fail(KNOWLEDGE_ERROR_UIDS.KB_PERMISSION_DENIED, "KB01_EXPERIENCE_NOT_FOUND");
        if (experience.state !== "OUTCOME_COMPLETE" && experience.state !== "REPLAY_READY") return fail(KNOWLEDGE_ERROR_UIDS.KB_OUTCOME_PENDING, "KB_OUTCOME_PENDING");
        if (!experience.lineage_complete) return fail(KNOWLEDGE_ERROR_UIDS.KB_LINEAGE_INCOMPLETE, "KB_LINEAGE_INCOMPLETE");
      }
      for (const key of ["scope", "pattern", "proposed_improvement", "evidence_refs", "limitations"]) {
        if (payload[key] === undefined || payload[key] === null || (typeof payload[key] === "string" && !text(payload[key]))) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_REQUIRED_LEARNING_FIELD_MISSING", 400);
      }
      return null;
    }
    case "createKnowledgeDraftFromExperience": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const refs = textList(payload.experience_refs);
      if (refs.length === 0 || !text(payload.scope) || !text(payload.knowledge_type)) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_DRAFT_FROM_EXP_REQUIRED_FIELDS_MISSING", 400);
      for (const ref of refs) {
        const experience = findExperience(ref);
        if (!experience) return fail(KNOWLEDGE_ERROR_UIDS.KB_PERMISSION_DENIED, "KB01_EXPERIENCE_NOT_FOUND");
        if (experience.state !== "OUTCOME_COMPLETE" && experience.state !== "REPLAY_READY") return fail(KNOWLEDGE_ERROR_UIDS.KB_OUTCOME_PENDING, "KB_OUTCOME_PENDING");
        if (!experience.lineage_complete) return fail(KNOWLEDGE_ERROR_UIDS.KB_LINEAGE_INCOMPLETE, "KB_LINEAGE_INCOMPLETE");
      }
      return null;
    }
    case "saveKnowledgeDraft": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const draft = findDraft(text(payload.knowledge_id) ?? pathId);
      if (!draft) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_DRAFT_NOT_FOUND");
      const guard = versionGuard(payload, draft.knowledge_id, draft.draft_version); if (guard) return guard;
      if (draft.review_state !== "DRAFT") return fail(KNOWLEDGE_ERROR_UIDS.KB_REVIEW_CHECK_INCOMPLETE, draft.review_state === "APPROVED" ? "KB01_APPROVED_VERSION_IMMUTABLE" : "KB01_DRAFT_NOT_EDITABLE");
      for (const key of ["title", "knowledge_type", "scope", "classification"]) {
        if (!text(payload[key])) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_REQUIRED_DRAFT_FIELD_MISSING", 400);
      }
      return null;
    }
    case "compareKnowledgeVersions": {
      const draft = findDraft(text(payload.knowledge_id));
      if (!draft) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_DRAFT_NOT_FOUND");
      if (!text(payload.left_version) || !text(payload.right_version)) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_COMPARE_VERSIONS_REQUIRED", 400);
      return null;
    }
    case "approveKnowledgeDraft": case "returnKnowledgeDraft": case "rejectKnowledgeDraft": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const draft = findDraft(text(payload.knowledge_id) ?? pathId);
      if (!draft) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_DRAFT_NOT_FOUND");
      const guard = versionGuard(payload, draft.knowledge_id, draft.draft_version); if (guard) return guard;
      if (draft.review_state !== "REVIEW") return fail(KNOWLEDGE_ERROR_UIDS.KB_REVIEW_CHECK_INCOMPLETE, draft.review_state === "APPROVED" ? "KB01_APPROVED_VERSION_IMMUTABLE" : "KB01_DRAFT_NOT_IN_REVIEW");
      if (!text(payload.review_rationale)) return fail(KNOWLEDGE_ERROR_UIDS.KB_REVIEW_CHECK_INCOMPLETE, "KB01_REVIEW_RATIONALE_REQUIRED");
      if (operation === "approveKnowledgeDraft") {
        const decision = text(payload.decision);
        if (decision && decision !== "APPROVE") return fail(KNOWLEDGE_ERROR_UIDS.KB_UNSUPPORTED_OPERATION, "KB01_DECISION_OPERATION_MISMATCH");
        if (!text(payload.decision)) return fail(KNOWLEDGE_ERROR_UIDS.KB_SCOPE_INVALID, "KB01_REVIEW_DECISION_REQUIRED", 400);
        const checks = record(payload.mandatory_check_results);
        if (Object.keys(checks).length === 0) return fail(KNOWLEDGE_ERROR_UIDS.KB_REVIEW_CHECK_INCOMPLETE, "KB_REVIEW_CHECK_INCOMPLETE");
        if (draft.citation_refs.length === 0) return fail(KNOWLEDGE_ERROR_UIDS.KB_CITATION_REQUIRED, "KB_CITATION_REQUIRED");
      }
      return null;
    }
    default:
      return fail(KNOWLEDGE_ERROR_UIDS.KB_UNSUPPORTED_OPERATION, "KB_UNSUPPORTED_OPERATION");
  }
}

function executeCommand(operation: KnowledgeOperation, request: KnowledgeRuntimeRequest): unknown {
  const payload = record(request.payload);
  const pathId = text(request.path_params.sourceId) ?? text(request.path_params.jobId) ?? text(request.path_params.experienceId) ?? text(request.path_params.knowledgeId) ?? text(request.path_params.citationId);
  switch (operation) {
    case "searchKnowledge": {
      const query = text(payload.query) as string;
      const matches = state.results.filter(item => !query || item.title.toLowerCase().includes(query.toLowerCase()) || item.classification_type.toLowerCase().includes(query.toLowerCase()));
      return { results: matches, result_count: matches.length, query, test_metadata: TEST_METADATA };
    }
    case "getCitation": {
      return { citation: state.citations.find(item => item.citation_id === pathId) ?? null, test_metadata: TEST_METADATA };
    }
    case "createKnowledgeSource": {
      const source: KnowledgeSource = {
        source_id: nextEntityId("SOURCE"), source_version: 1,
        name: text(payload.name) as string, source_type: text(payload.source_type) as string,
        scope: text(payload.scope) as string, rights: text(payload.rights) as string,
        classification: text(payload.classification) as string, collection_method: text(payload.collection_method) as string,
        collection_config: payload.collection_config ?? null, freshness_policy: text(payload.freshness_policy) as string,
        retention_policy: text(payload.retention_policy) as string, status: "DRAFT",
      };
      state.sources.push(source);
      appendAudit({ event: "knowledge.source.created", subject_ref: source.source_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { source_id: source.source_id, status: source.status, version: source.source_version, event: "knowledge.source.created", test_metadata: TEST_METADATA };
    }
    case "updateKnowledgeSource": {
      const source = findSource(text(payload.source_id) ?? pathId) as KnowledgeSource;
      for (const key of ["name", "source_type", "scope", "rights", "classification", "collection_method", "freshness_policy", "retention_policy"] as const) {
        const value = text(payload[key]);
        if (value) source[key] = value;
      }
      if (payload.collection_config !== undefined) source.collection_config = payload.collection_config;
      source.source_version += 1;
      appendAudit({ event: "knowledge.source.updated", subject_ref: source.source_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { source_id: source.source_id, status: source.status, version: source.source_version, event: "knowledge.source.updated", test_metadata: TEST_METADATA };
    }
    case "pauseKnowledgeSource": case "resumeKnowledgeSource": case "retireKnowledgeSource": {
      const source = findSource(text(payload.source_id) ?? pathId) as KnowledgeSource;
      const next: SourceState = operation === "pauseKnowledgeSource" ? "PAUSED" : operation === "resumeKnowledgeSource" ? "ACTIVE" : "RETIRED";
      source.status = next;
      source.source_version += 1;
      const event = operation === "pauseKnowledgeSource" ? "knowledge.source.paused" : operation === "resumeKnowledgeSource" ? "knowledge.source.resumed" : "knowledge.source.retired";
      appendAudit({ event, subject_ref: source.source_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { source_id: source.source_id, status: source.status, version: source.source_version, event, test_metadata: TEST_METADATA };
    }
    case "createAcquisitionJob": {
      const run: IngestionRun = {
        run_id: nextEntityId("RUN"), source_ref: text(payload.source_ref) as string, run_type: text(payload.run_type) ?? "WEB_CRAWL",
        status: "RUNNING", progress: 0, started_at: new Date().toISOString(), ended_at: null,
        raw_output_refs: [], normalized_refs: [], evidence_refs: [], failure_ref: null, retry_eligible: false,
      };
      state.runs.push(run);
      appendAudit({ event: "knowledge.ingestion.started", subject_ref: run.run_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { run_id: run.run_id, status: run.status, event: "knowledge.ingestion.started", test_metadata: TEST_METADATA };
    }
    case "retryAcquisitionJob": {
      const run = findRun(text(payload.run_id) ?? pathId) as IngestionRun;
      run.status = "PENDING";
      run.retry_eligible = false;
      run.failure_ref = null;
      run.progress = 0;
      run.started_at = new Date().toISOString();
      run.ended_at = null;
      appendAudit({ event: "knowledge.ingestion.retry", subject_ref: run.run_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { run_id: run.run_id, status: run.status, event: "knowledge.ingestion.retry", test_metadata: TEST_METADATA };
    }
    case "createContextCandidate": {
      const selectedRefs = textList(payload.selected_refs);
      const candidate: ContextCandidate = {
        context_candidate_id: nextEntityId("CONTEXT"), version: 1,
        purpose: text(payload.purpose) as string, scope: text(payload.scope) as string,
        selected_refs: selectedRefs, evidence_refs: textList(payload.evidence_refs),
        state: "READY_FOR_CONSUMER_REVIEW", context_fingerprint: `sha256:TEST-CONTEXT-FP-${state.entity_counter}`,
      };
      state.contextCandidates.push(candidate);
      appendAudit({ event: "acpos.context_candidate.created", subject_ref: candidate.context_candidate_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { context_candidate_id: candidate.context_candidate_id, state: candidate.state, version: candidate.version, event: "acpos.context_candidate.created", test_metadata: TEST_METADATA };
    }
    case "getExperienceReplay": {
      const experience = findExperience(pathId) as ExperienceRecord;
      const replay: ReplayProjection = {
        experience_id: experience.experience_id,
        source_input_refs: ["TEST-KB-INPUT-REF-001"], instruction_refs: ["TEST-KB-INSTRUCTION-REF-001"],
        route_refs: [experience.route_decision_ref], output_refs: ["TEST-KB-OUTPUT-REF-001"],
        evaluation_refs: ["TEST-KB-EVAL-REF-001"], correction_refs: ["TEST-KB-CORRECTION-REF-001"],
        outcome_refs: ["TEST-KB-OUTCOME-REF-001"], root_cause: "TEST-ROOT-CAUSE-RECORDED",
      };
      return { replay, test_metadata: TEST_METADATA };
    }
    case "compareExperienceReplay": {
      return { experience_id: text(payload.experience_id), compare_refs: textList(payload.compare_refs), diff: "TEST-REPLAY-COMPARE-DIFF", test_metadata: TEST_METADATA };
    }
    case "createLearningCandidate": {
      const learning: LearningCandidate = {
        learning_candidate_id: nextEntityId("LEARNING"), version: 1,
        scope: text(payload.scope) as string, pattern: text(payload.pattern) as string,
        proposed_improvement: text(payload.proposed_improvement) as string,
        evidence_refs: textList(payload.evidence_refs), limitations: text(payload.limitations) as string, state: "DRAFT",
      };
      state.learnings.push(learning);
      appendAudit({ event: "acpos.learning_candidate.created", subject_ref: learning.learning_candidate_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { learning_candidate_id: learning.learning_candidate_id, state: learning.state, version: learning.version, event: "acpos.learning_candidate.created", test_metadata: TEST_METADATA };
    }
    case "createKnowledgeDraftFromExperience": {
      const draft: KnowledgeVersion = {
        knowledge_id: nextEntityId("DRAFT"), draft_version: 1,
        title: text(payload.title_seed) ?? `Knowledge draft from ${textList(payload.experience_refs).join("+")}`,
        knowledge_type: text(payload.knowledge_type) as string, summary: "", content: "",
        scope: text(payload.scope) as string, classification: "INTERNAL",
        citation_refs: ["TEST-KB-CIT-001"], outcome_refs: [], experience_refs: textList(payload.experience_refs),
        review_state: "DRAFT", previous_approved_version_ref: approvedKnowledge()?.knowledge_id ?? null,
      };
      state.drafts.push(draft);
      appendAudit({ event: "knowledge.draft.from_experience", subject_ref: draft.knowledge_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { knowledge_id: draft.knowledge_id, review_state: draft.review_state, version: draft.draft_version, event: "knowledge.draft.from_experience", test_metadata: TEST_METADATA };
    }
    case "saveKnowledgeDraft": {
      const draft = findDraft(text(payload.knowledge_id) ?? pathId) as KnowledgeVersion;
      for (const key of ["title", "knowledge_type", "summary", "content", "scope", "classification"] as const) {
        const value = text(payload[key]);
        if (value) draft[key] = value;
      }
      const citationRefs = textList(payload.citation_refs);
      if (citationRefs.length > 0) draft.citation_refs = citationRefs;
      const outcomeRefs = textList(payload.outcome_refs);
      if (outcomeRefs.length > 0) draft.outcome_refs = outcomeRefs;
      const experienceRefs = textList(payload.experience_refs);
      if (experienceRefs.length > 0) draft.experience_refs = experienceRefs;
      draft.draft_version += 1;
      appendAudit({ event: "knowledge.draft.saved", subject_ref: draft.knowledge_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { knowledge_id: draft.knowledge_id, review_state: draft.review_state, version: draft.draft_version, event: "knowledge.draft.saved", test_metadata: TEST_METADATA };
    }
    case "compareKnowledgeVersions": {
      const draft = findDraft(text(payload.knowledge_id)) as KnowledgeVersion;
      return { knowledge_id: draft.knowledge_id, left_version: text(payload.left_version), right_version: text(payload.right_version), diff: "TEST-KNOWLEDGE-VERSION-DIFF", previous_approved_version_ref: draft.previous_approved_version_ref, test_metadata: TEST_METADATA };
    }
    case "approveKnowledgeDraft": case "returnKnowledgeDraft": case "rejectKnowledgeDraft": {
      const draft = findDraft(text(payload.knowledge_id) ?? pathId) as KnowledgeVersion;
      const event = operation === "approveKnowledgeDraft" ? "knowledge.approved" : operation === "returnKnowledgeDraft" ? "knowledge.returned" : "knowledge.rejected";
      if (operation === "approveKnowledgeDraft") {
        for (const item of state.drafts) {
          if (item.review_state === "APPROVED" && item.knowledge_id !== draft.knowledge_id) item.review_state = "SUPERSEDED";
        }
        draft.review_state = "APPROVED";
      } else if (operation === "returnKnowledgeDraft") {
        draft.review_state = "RETURNED";
      } else {
        draft.review_state = "REJECTED";
      }
      draft.draft_version += 1;
      appendAudit({ event, subject_ref: draft.knowledge_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { knowledge_id: draft.knowledge_id, review_state: draft.review_state, version: draft.draft_version, event, test_metadata: TEST_METADATA };
    }
    default:
      return { error: KNOWLEDGE_ERROR_UIDS.KB_UNSUPPORTED_OPERATION, test_metadata: TEST_METADATA };
  }
}

export function isControlledKnowledgeServerTestMode() { return isControlledTestMode(); }

export function readControlledKnowledgeTestProjection() {
  seedFixture();
  advanceRuns();
  const source = selectedSource();
  const run = selectedRun();
  const experience = selectedExperience();
  const draft = draftDraft();
  const review = reviewDraft();
  const approved = approvedKnowledge();
  const lastAudit = state.audits[0] ?? null;
  const activeSource = state.sources.find(item => item.status === "ACTIVE") ?? null;
  const pausedSource = state.sources.find(item => item.status === "PAUSED") ?? null;
  const retireCandidate = state.sources.find(item => item.status !== "RETIRED") ?? null;
  const values: Record<string, string> = {
    overview_kpi: `${state.sources.length} sources · ${state.runs.length} runs · ${state.experiences.length} experiences · ${review ? 1 : 0} in review · ${approved ? 1 : 0} approved`,
    overview_warn: hasActiveNonCancelableRun() ? "1 conflicting run in progress" : "No warnings",
    source_list: state.sources.map(item => `${item.source_id} v${item.source_version} ${item.status}`).join(" | ") || "—",
    source_detail: source ? `${source.source_id} · ${source.name} · ${source.source_type} · ${source.classification} · ${source.rights} · refresh ${source.freshness_policy} · retain ${source.retention_policy}` : "—",
    ingestion: state.runs.map(item => `${item.run_id} · ${item.status} · ${item.progress}% · ${item.source_ref}`).join(" | ") || "—",
    ingestion_drawer: run ? `Failure: ${run.failure_ref ?? "none"} · retry ${run.retry_eligible ? "available" : "unavailable"}` : "—",
    search: `${state.results.length} results · ${state.results.filter(item => item.review_state === "APPROVED").length} approved`,
    results: state.results.map(item => `${item.result_ref} ${item.classification_type} ${item.review_state}`).join(" | ") || "—",
    citation: state.citations.map(item => `${item.citation_id} · ${item.source_ref} · evidence ${item.evidence_ref}`).join(" | ") || "—",
    context_basket: `${state.contextCandidates.length} candidates · local selection basket`,
    exp_list: state.experiences.map(item => `${item.experience_id} · ${item.state} · ${item.attempt_count} attempts`).join(" | ") || "—",
    replay: experience ? `${experience.attempt_count} attempts · lineage ${experience.lineage_complete ? "complete" : "pending"}` : "—",
    root_cause: "Root cause recorded · pattern identified",
    learning: `${state.learnings.length} learning candidates`,
    review_queue: state.drafts.filter(item => item.review_state === "REVIEW" || item.review_state === "DRAFT").map(item => `${item.knowledge_id} v${item.draft_version} ${item.review_state}`).join(" | ") || "—",
    draft: draft ? `${draft.knowledge_id} v${draft.draft_version} · ${draft.citation_refs.length} citations` : "—",
    evidence_check: `${state.citations.length} citations traced · outcomes validated`,
    version_diff: approved ? `Against ${approved.knowledge_id} · supersession preserved` : "—",
    review_rail: review ? "Mandatory checks pending · awaiting decision" : "—",
    status: lastAudit ? `${lastAudit.audit_ref} · ${lastAudit.event} · ${lastAudit.subject_ref} · ${lastAudit.outcome}` : "No governance actions yet",
  };
  const control_enabled: Record<string, boolean> = {
    "KB-01-CTL-VIEW-OVERVIEW": true, "KB-01-CTL-VIEW-SOURCE": true, "KB-01-CTL-VIEW-SEARCH": true,
    "KB-01-CTL-VIEW-EXPERIENCE": true, "KB-01-CTL-VIEW-REVIEW": true,
    "KB-01-CTL-SEARCH-GLOBAL": true,
    "KB-01-CTL-SOURCE-CREATE": true,
    "KB-01-CTL-SOURCE-SAVE": retireCandidate !== null,
    "KB-01-CTL-SOURCE-PAUSE": activeSource !== null,
    "KB-01-CTL-SOURCE-RESUME": pausedSource !== null,
    "KB-01-CTL-SOURCE-RETIRE": retireCandidate !== null,
    "KB-01-CTL-INGEST-START": activeSource !== null,
    "KB-01-CTL-INGEST-RETRY": state.runs.some(item => item.status === "RETRY_ELIGIBLE" && item.retry_eligible),
    "KB-01-CTL-SEARCH": true,
    "KB-01-CTL-CITATION-OPEN": state.results.length > 0,
    "KB-01-CTL-CONTEXT-ADD": state.results.length > 0,
    "KB-01-CTL-CONTEXT-REMOVE": true,
    "KB-01-CTL-CONTEXT-CREATE": true,
    "KB-01-CTL-REPLAY-OPEN": experience !== null,
    "KB-01-CTL-REPLAY-COMPARE": experience !== null && experience.attempt_count >= 2,
    "KB-01-CTL-LEARNING-CREATE": experience !== null && (experience.state === "OUTCOME_COMPLETE" || experience.state === "REPLAY_READY"),
    "KB-01-CTL-DRAFT-FROM-EXP": experience !== null && (experience.state === "OUTCOME_COMPLETE" || experience.state === "REPLAY_READY"),
    "KB-01-CTL-DRAFT-SAVE": draft !== null,
    "KB-01-CTL-VERSION-COMPARE": approved !== null && draft !== null,
    "KB-01-CTL-APPROVE": review !== null,
    "KB-01-CTL-RETURN": review !== null,
    "KB-01-CTL-REJECT": review !== null,
  };
  const entities: Record<string, Record<string, string>> = {
    selected_source: source ? { source_id: source.source_id, source_version: String(source.source_version), status: source.status } : {},
    selected_run: run ? { run_id: run.run_id, status: run.status, retry_eligible: String(run.retry_eligible) } : {},
    selected_result: state.results[0] ? { result_ref: state.results[0].result_ref } : {},
    selected_citation: state.citations[0] ? { citation_id: state.citations[0].citation_id } : {},
    selected_experience: experience ? { experience_id: experience.experience_id, state: experience.state, attempt_count: String(experience.attempt_count) } : {},
    selected_draft: draft ? { knowledge_id: draft.knowledge_id, draft_version: String(draft.draft_version), review_state: draft.review_state } : {},
    selected_review_draft: review ? { knowledge_id: review.knowledge_id, draft_version: String(review.draft_version), review_state: review.review_state } : {},
    previous_approved: approved ? { knowledge_id: approved.knowledge_id, draft_version: String(approved.draft_version), review_state: approved.review_state } : {},
  };
  return { page_state: "READY", values, control_enabled, entities, test_metadata: TEST_METADATA };
}

export async function executeControlledKnowledgePort(request: KnowledgeRuntimeRequest): Promise<KnowledgeRuntimeResult> {
  if (!isControlledKnowledgeServerTestMode()) {
    return { ok: false, error_uid: "KB-01-ERR-001", reason_code: "KB_TEST_RUNTIME_DISABLED", correlation_id: request.correlation_id, status: 503 };
  }
  if (!KNOWLEDGE_OPERATIONS.includes(request.operation)) {
    return { ok: false, error_uid: KNOWLEDGE_ERROR_UIDS.KB_UNSUPPORTED_OPERATION, reason_code: "KB_UNSUPPORTED_OPERATION", correlation_id: request.correlation_id, status: 400 };
  }
  const isMutation = !["searchKnowledge", "getCitation", "getExperienceReplay", "compareExperienceReplay", "compareKnowledgeVersions"].includes(request.operation);
  if (isMutation) {
    const cached = state.idempotency.get(request.correlation_id);
    if (cached) {
      return cached.ok
        ? { ok: true, value: cached.value, correlation_id: request.correlation_id }
        : { ok: false, error_uid: cached.error_uid as string, reason_code: cached.reason_code as string, correlation_id: request.correlation_id, status: 403 };
    }
  }
  seedFixture();
  const gate = evaluateGates(request.operation, request);
  if (gate) {
    const denied: KnowledgeRuntimeResult = { ...gate, correlation_id: request.correlation_id };
    if (isMutation) {
      state.idempotency.set(request.correlation_id, { ok: false, reason_code: denied.reason_code, error_uid: denied.error_uid });
      const subject = text(record(request.payload).source_id) ?? text(record(request.payload).knowledge_id) ?? text(record(request.payload).run_id) ?? "unresolved";
      appendAudit({ event: `knowledge.gate.denied`, subject_ref: subject, correlation_id: request.correlation_id, outcome: "DENIED", reason_code: denied.reason_code });
    }
    return denied;
  }
  const value = executeCommand(request.operation, request);
  if (isMutation) state.idempotency.set(request.correlation_id, { ok: true, value });
  return { ok: true, value, correlation_id: request.correlation_id };
}
