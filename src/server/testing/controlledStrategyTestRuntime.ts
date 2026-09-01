import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import type { IamRuntimeRequest } from "@/server/iam/iamRuntime";
import type { InfoRequest } from "@/server/info/infoCommandRuntime";

const TEST_METADATA = {
  data_classification: "TEST_ONLY",
  synthetic: true,
  test_dataset_id: "TEST-STR-01",
  test_run_id: "TEST-RUN-STR-01-CONTROLLED",
  created_for_validation: true,
  production_eligible: false,
} as const;

type StrategySourceState = "ACTIVE" | "PAUSED" | "RETIRED";
type StrategyFactState = "DRAFT" | "REVIEW" | "APPROVED" | "RETIRED";
type StrategyPlaybookState = "DRAFT" | "REVIEW" | "APPROVED";
type StrategyCandidateState = "OPEN" | "ADOPTED_AS_CONTEXT" | "REJECTED";

type StrategySource = { source_id: string; state: StrategySourceState; version: number };
type StrategyFact = { fact_id: string; state: StrategyFactState; version: number };
type StrategyPlaybookDraft = { draft_id: string; draft_type: "playbook"; title: string; state: StrategyPlaybookState; version: number };
type StrategyCandidate = { candidate_ref: string; state: StrategyCandidateState; version: number };

type StrategyAuditEntry = {
  audit_ref: string;
  event: "strategy.searched" | "strategy.refreshed" | "strategy.exported" | "strategy.context_adopted" | "strategy.draft_saved";
  subject_ref: string;
  correlation_id: string;
  outcome: "SUCCESS" | "DENIED" | "ERROR";
  reason_code?: string;
};

type IdempotencyResult = { ok: boolean; reason_code?: string; value?: unknown };

type ControlledState = {
  sources: StrategySource[];
  facts: StrategyFact[];
  playbook_drafts: StrategyPlaybookDraft[];
  candidates: StrategyCandidate[];
  audits: StrategyAuditEntry[];
  audit_counter: number;
  idempotency: Map<string, IdempotencyResult>;
  last_search_query: string | null;
  last_refresh_ref: string | null;
  last_export_ref: string | null;
};

const state: ControlledState = {
  sources: [],
  facts: [],
  playbook_drafts: [],
  candidates: [],
  audits: [],
  audit_counter: 0,
  idempotency: new Map(),
  last_search_query: null,
  last_refresh_ref: null,
  last_export_ref: null,
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
function seedFixture() {
  if (state.sources.length > 0) return;
  state.sources.push(
    { source_id: "TEST-STR-SOURCE-001", state: "ACTIVE", version: 2 },
    { source_id: "TEST-STR-SOURCE-002", state: "PAUSED", version: 1 },
  );
  state.facts.push({ fact_id: "TEST-STR-FACT-001", state: "REVIEW", version: 2 });
  state.playbook_drafts.push({ draft_id: "TEST-STR-PLAYBOOK-DRAFT-001", draft_type: "playbook", title: "[TEST] Platform Playbook Draft", state: "DRAFT", version: 1 });
  state.candidates.push(
    { candidate_ref: "TEST-STR-CAND-A", state: "OPEN", version: 1 },
    { candidate_ref: "TEST-STR-CAND-B", state: "OPEN", version: 1 },
    { candidate_ref: "TEST-STR-OPP-001", state: "OPEN", version: 1 },
  );
}
function appendAudit(entry: Omit<StrategyAuditEntry, "audit_ref">): StrategyAuditEntry {
  state.audit_counter += 1;
  const full: StrategyAuditEntry = { ...entry, audit_ref: `TEST-STR01-AUDIT-${String(state.audit_counter).padStart(3, "0")}` };
  state.audits = [full, ...state.audits].slice(0, 10);
  return full;
}
function lastAuditRef(): string {
  return state.audits[0]?.audit_ref ?? "—";
}

const VIEW_VALUES: Readonly<Record<string, string>> = {
  "Intelligence Summary": "Projection engine ready · 2 sources tracked",
  "Source Health": "TEST-STR-SOURCE-001 v2 ACTIVE | TEST-STR-SOURCE-002 v1 PAUSED",
  "Fact Quality": "TEST-STR-FACT-001 v2 REVIEW · quality derived from projection",
  Watchlist: "TEST-STR-WATCH-001 · watch rules applied",
  "Risk Alert": "No alerts recorded",
  "Candidate Queue": "TEST-STR-CAND-A v1 OPEN | TEST-STR-CAND-B v1 OPEN",
  "Source Registry": "2 sources registered · strategic intelligence acquisition",
  "Scope Policy": "Scope derived from projection",
  "Source Quality": "Quality derived from projection",
  Retention: "Retention policy active · scheduled recrawl allowed",
  "Fact Registry": "TEST-STR-FACT-001 v2 REVIEW",
  "Cohort Builder": "No cohorts registered",
  "Market Map": "Market map derived from projection",
  Completeness: "Completeness derived from projection",
  Confidence: "Confidence derived from projection",
  Citation: "Citations bound · TEST-STR-FACT-001",
  "Platform Profile": "Profile derived from projection",
  "Account Scope": "Permission-gated account scope",
  Playbook: "TEST-STR-PLAYBOOK-DRAFT-001 v1 DRAFT · publish via governed flow",
  Hypothesis: "Hypothesis derived from projection · fact rules enforced",
  Evidence: "Evidence bound · audit ref —",
  "Version History": "1 draft · versions derived from projection",
  Approval: "No approvals recorded",
  "Trend Engine": "Trend engine registered",
  "Momentum Engine": "Momentum engine registered",
  "Forecast Engine": "Forecast engine registered",
  "Opportunity Queue": "TEST-STR-CAND-A v1 OPEN · budget changes via governed flow",
  "Decision Context": "2 candidates open",
  "Option Comparison": "Registered comparison operation required",
  "Risk / Cost / Capacity": "Permission-gated · finance guardrail enforced",
  "Decision Gate": "Decision gate registered",
  "Core Review Handoff": "Governed handoff required",
  Audit: "No governance actions yet",
};

function projectionValues(): Record<string, string> {
  const values: Record<string, string> = { ...VIEW_VALUES };
  values["Evidence"] = `Evidence bound · audit ref ${lastAuditRef()}`;
  values["Audit"] = lastAuditRef() === "—" ? "No governance actions yet" : `${lastAuditRef()} · ${state.audits[0]?.event ?? ""} · ${state.audits[0]?.outcome ?? ""}`;
  values["Approval"] = state.audits.find(item => item.event === "strategy.context_adopted") ? `Context adopted · ${lastAuditRef()}` : "No approvals recorded";
  return values;
}

const PROJECTION_EVIDENCE: Readonly<Record<string, string>> = Object.fromEntries(
  Object.keys(VIEW_VALUES).map(key => [key, "projection_bound · TEST_ONLY"]),
);
const PROJECTION_STATES: Readonly<Record<string, string>> = Object.fromEntries(
  Object.keys(VIEW_VALUES).map(key => [key, "READY"]),
);

export function isControlledStrategyServerTestMode() {
  return isControlledTestMode();
}

export function readControlledStrategyTestProjection() {
  seedFixture();
  return {
    page_state: "READY",
    values: projectionValues(),
    evidence: PROJECTION_EVIDENCE,
    states: PROJECTION_STATES,
    action_enabled: {
      "ACT-SEARCH": true,
      "ACT-REFRESH": true,
      "ACT-CONFIGURE": true,
      "ACT-APPROVE": true,
      "ACT-EXPORT": true,
      "ACT-DRAFT-SAVE": true,
      "ACT-CANDIDATE-CREATE": true,
      "ACT-CANDIDATE-COMPARE": true,
      "ACT-ADOPT-CONTEXT": true,
      "ACT-NAV-OPEN": true,
    } as Readonly<Record<string, boolean>>,
    selected_resource_id: "TEST-STR-FACT-001",
    test_metadata: TEST_METADATA,
  };
}

function cachedIam(r: IamRuntimeRequest) {
  const cached = state.idempotency.get(r.correlation_id);
  if (!cached) return null;
  return cached.ok
    ? { ok: true as const, value: cached.value, correlation_id: r.correlation_id }
    : { ok: false as const, reason_code: cached.reason_code as string, correlation_id: r.correlation_id };
}

function cachedInfo(r: InfoRequest) {
  const cached = state.idempotency.get(r.correlation_id);
  if (!cached) return null;
  return cached.ok
    ? { ok: true as const, value: cached.value }
    : { ok: false as const, status: 403, reason_code: cached.reason_code as string };
}

export async function executeControlledStrategyInfoCommand(r: InfoRequest):
  Promise<{ ok: true; value: unknown } | { ok: false; status: number; reason_code: string } | null> {
  if (!isControlledStrategyServerTestMode()) return null;
  const pagePayload = record(r.payload);
  if (text(pagePayload.page_uid) === "admin:SOC-01") return null;
  if (text(pagePayload.page_uid) === "admin:ERP-01") return null;
  const cached = cachedInfo(r);
  if (cached) return cached;
  seedFixture();

  if (r.operation_id === "searchProjection") {
    const payload = record(r.payload);
    const query = text(payload.query);
    if (!query) {
      state.idempotency.set(r.correlation_id, { ok: false, reason_code: "STR01_REQUIRED_FIELDS_MISSING" });
      appendAudit({ event: "strategy.searched", subject_ref: "unresolved", correlation_id: r.correlation_id, outcome: "DENIED", reason_code: "STR01_REQUIRED_FIELDS_MISSING" });
      return { ok: false, status: 400, reason_code: "STR01_REQUIRED_FIELDS_MISSING" };
    }
    state.last_search_query = query;
    const value = {
      query,
      matches: state.sources.filter(item => item.source_id.includes("SOURCE")).map(item => `${item.source_id} v${item.version} ${item.state}`),
      fact_refs: state.facts.map(item => item.fact_id),
      test_metadata: TEST_METADATA,
    };
    appendAudit({ event: "strategy.searched", subject_ref: query, correlation_id: r.correlation_id, outcome: "SUCCESS" });
    state.idempotency.set(r.correlation_id, { ok: true, value });
    return { ok: true, value };
  }

  if (r.operation_id === "refreshProjection") {
    state.last_refresh_ref = `TEST-STR-REFRESH-${String(state.audit_counter + 1).padStart(3, "0")}`;
    const value = { refresh_ref: state.last_refresh_ref, projection_state: "READY", test_metadata: TEST_METADATA };
    appendAudit({ event: "strategy.refreshed", subject_ref: state.last_refresh_ref, correlation_id: r.correlation_id, outcome: "SUCCESS" });
    state.idempotency.set(r.correlation_id, { ok: true, value });
    return { ok: true, value };
  }

  if (r.operation_id === "exportProjection") {
    if (text(pagePayload.page_uid) !== "admin:STR-01") return null;
    state.last_export_ref = `TEST-STR-EXPORT-${String(state.audit_counter + 1).padStart(3, "0")}`;
    const value = { export_ref: state.last_export_ref, format: "projection_snapshot", test_metadata: TEST_METADATA };
    appendAudit({ event: "strategy.exported", subject_ref: state.last_export_ref, correlation_id: r.correlation_id, outcome: "SUCCESS" });
    state.idempotency.set(r.correlation_id, { ok: true, value });
    return { ok: true, value };
  }

  if (r.operation_id === "adoptContextCandidate") {
    const candidateRef = text(r.path_params.id);
    if (!candidateRef) {
      state.idempotency.set(r.correlation_id, { ok: false, reason_code: "STR01_REQUIRED_FIELDS_MISSING" });
      appendAudit({ event: "strategy.context_adopted", subject_ref: "unresolved", correlation_id: r.correlation_id, outcome: "DENIED", reason_code: "STR01_REQUIRED_FIELDS_MISSING" });
      return { ok: false, status: 400, reason_code: "STR01_REQUIRED_FIELDS_MISSING" };
    }
    const candidate = state.candidates.find(item => item.candidate_ref === candidateRef);
    if (!candidate) {
      state.idempotency.set(r.correlation_id, { ok: false, reason_code: "STR01_CANDIDATE_NOT_FOUND" });
      appendAudit({ event: "strategy.context_adopted", subject_ref: candidateRef, correlation_id: r.correlation_id, outcome: "DENIED", reason_code: "STR01_CANDIDATE_NOT_FOUND" });
      return { ok: false, status: 403, reason_code: "STR01_CANDIDATE_NOT_FOUND" };
    }
    if (candidate.state !== "OPEN") {
      state.idempotency.set(r.correlation_id, { ok: false, reason_code: "STR01_CANDIDATE_STATE_GUARD_REJECTED" });
      appendAudit({ event: "strategy.context_adopted", subject_ref: candidateRef, correlation_id: r.correlation_id, outcome: "DENIED", reason_code: "STR01_CANDIDATE_STATE_GUARD_REJECTED" });
      return { ok: false, status: 403, reason_code: "STR01_CANDIDATE_STATE_GUARD_REJECTED" };
    }
    candidate.state = "ADOPTED_AS_CONTEXT";
    const audit = appendAudit({ event: "strategy.context_adopted", subject_ref: candidateRef, correlation_id: r.correlation_id, outcome: "SUCCESS" });
    const value = { candidate_ref: candidateRef, state: candidate.state, audit_ref: audit.audit_ref, note: "adopted_as_context_candidate · not_an_approved_decision", test_metadata: TEST_METADATA };
    state.idempotency.set(r.correlation_id, { ok: true, value });
    return { ok: true, value };
  }

  return null;
}

export async function executeControlledStrategyIamCommand(r: IamRuntimeRequest):
  Promise<{ ok: true; value: unknown; correlation_id: string } | { ok: false; reason_code: string; correlation_id: string } | null> {
  if (r.operation !== "saveDraft" || !isControlledStrategyServerTestMode()) return null;
  const cached = cachedIam(r);
  if (cached) return cached;
  seedFixture();

  const payload = record(r.payload);
  const draftId = text(payload.draft_id) ?? text(r.draft_id ?? null);
  const draftType = text(payload.draft_type);
  if (draftType !== "playbook") return null;
  if (!draftId || !text(payload.title)) {
    state.idempotency.set(r.correlation_id, { ok: false, reason_code: "STR01_REQUIRED_FIELDS_MISSING" });
    appendAudit({ event: "strategy.draft_saved", subject_ref: draftId ?? "unresolved", correlation_id: r.correlation_id, outcome: "DENIED", reason_code: "STR01_REQUIRED_FIELDS_MISSING" });
    return { ok: false as const, reason_code: "STR01_REQUIRED_FIELDS_MISSING", correlation_id: r.correlation_id };
  }
  const draft = state.playbook_drafts.find(item => item.draft_id === draftId);
  if (!draft) {
    state.idempotency.set(r.correlation_id, { ok: false, reason_code: "STR01_DRAFT_NOT_FOUND" });
    appendAudit({ event: "strategy.draft_saved", subject_ref: draftId, correlation_id: r.correlation_id, outcome: "DENIED", reason_code: "STR01_DRAFT_NOT_FOUND" });
    return { ok: false as const, reason_code: "STR01_DRAFT_NOT_FOUND", correlation_id: r.correlation_id };
  }
  const expected = text(payload.expected_version);
  if (expected && Number(expected) !== draft.version) {
    state.idempotency.set(r.correlation_id, { ok: false, reason_code: "STR01_VERSION_CONFLICT" });
    appendAudit({ event: "strategy.draft_saved", subject_ref: draftId, correlation_id: r.correlation_id, outcome: "DENIED", reason_code: "STR01_VERSION_CONFLICT" });
    return { ok: false as const, reason_code: "STR01_VERSION_CONFLICT", correlation_id: r.correlation_id };
  }
  if (draft.state === "APPROVED") {
    state.idempotency.set(r.correlation_id, { ok: false, reason_code: "STR01_APPROVED_PLAYBOOK_IMMUTABLE" });
    appendAudit({ event: "strategy.draft_saved", subject_ref: draftId, correlation_id: r.correlation_id, outcome: "DENIED", reason_code: "STR01_APPROVED_PLAYBOOK_IMMUTABLE" });
    return { ok: false as const, reason_code: "STR01_APPROVED_PLAYBOOK_IMMUTABLE", correlation_id: r.correlation_id };
  }
  draft.version += 1;
  draft.title = text(payload.title) as string;
  const audit = appendAudit({ event: "strategy.draft_saved", subject_ref: draftId, correlation_id: r.correlation_id, outcome: "SUCCESS" });
  const value = { draft_id: draftId, draft_type: draft.draft_type, state: draft.state, version: draft.version, event: "strategy.draft_saved", audit_ref: audit.audit_ref, test_metadata: TEST_METADATA };
  state.idempotency.set(r.correlation_id, { ok: true, value });
  return { ok: true as const, value, correlation_id: r.correlation_id };
}
