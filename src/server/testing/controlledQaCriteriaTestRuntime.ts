import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import type { IamRuntimeRequest } from "@/server/iam/iamRuntime";

const TEST_METADATA = {
  data_classification: "TEST_ONLY",
  synthetic: true,
  test_dataset_id: "TEST-SG-02",
  test_run_id: "TEST-RUN-SG-02-CONTROLLED",
  created_for_validation: true,
  production_eligible: false,
} as const;

const GOVERNED_RESOURCE_TYPES = ["quality_criteria_version", "quality_gate_policy", "dimension_library", "required_check", "threshold", "department_mapping"] as const;
type GovernedResourceType = (typeof GOVERNED_RESOURCE_TYPES)[number];
type ResourceState = "DRAFT" | "REVIEW" | "APPROVED" | "ACTIVE" | "SUPERSEDED" | "RETIRED";

type GovernedResource = {
  resource_type: GovernedResourceType;
  resource_id: string;
  state: ResourceState;
  version: number;
  config_patch_json: unknown;
  reason: string | null;
  rationale: string | null;
};

type AuditEntry = {
  audit_ref: string;
  event: "governance.configured" | "governance.approved";
  resource_id: string;
  correlation_id: string;
  outcome: "SUCCESS" | "DENIED" | "ERROR";
  reason_code?: string;
};

type GateResult = { ok: true } | { ok: false; reason_code: string };

type IdempotencyResult = { ok: boolean; reason_code?: string; value?: unknown };

type ControlledState = {
  resources: GovernedResource[];
  audits: AuditEntry[];
  audit_counter: number;
  idempotency: Map<string, IdempotencyResult>;
};

const state: ControlledState = { resources: [], audits: [], audit_counter: 0, idempotency: new Map() };

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
function seedFixture() {
  if (state.resources.length > 0) return;
  state.resources.push(
    { resource_type: "quality_criteria_version", resource_id: "TEST-CRITERIA-DRAFT-001", state: "DRAFT", version: 1, config_patch_json: null, reason: null, rationale: null },
    { resource_type: "quality_criteria_version", resource_id: "TEST-CRITERIA-REVIEW-001", state: "REVIEW", version: 3, config_patch_json: null, reason: null, rationale: null },
  );
}
function appendAudit(entry: Omit<AuditEntry, "audit_ref">): AuditEntry {
  state.audit_counter += 1;
  const full: AuditEntry = { ...entry, audit_ref: `TEST-SG02-AUDIT-${String(state.audit_counter).padStart(3, "0")}` };
  state.audits = [full, ...state.audits].slice(0, 10);
  return full;
}
function findResource(resourceId: string): GovernedResource | null {
  return state.resources.find(item => item.resource_id === resourceId) ?? null;
}
function eventOf(operation: string): "governance.configured" | "governance.approved" {
  return operation === "approveGovernedResource" ? "governance.approved" : "governance.configured";
}
function criteriaSummary(): string {
  return state.resources.map(item => `${item.resource_id} v${item.version} ${item.state}`).join(" | ");
}

export function isControlledQaCriteriaServerTestMode() { return isControlledTestMode(); }

export function readControlledQaCriteriaTestProjection() {
  seedFixture();
  const hasDraft = state.resources.some(item => item.state === "DRAFT");
  const hasReview = state.resources.some(item => item.state === "REVIEW");
  const lastAudit = state.audits[0] ?? null;
  const approvalAudit = state.audits.find(item => item.event === "governance.approved" && item.outcome === "SUCCESS") ?? null;
  return {
    page_state: state.resources.length === 0 ? "EMPTY" : "READY",
    values: {
      criteria_versions: criteriaSummary(),
      dimensions: "No dimensions registered yet",
      policies: "No gate policies registered yet",
      mappings: "No department mappings yet",
      approvals: approvalAudit ? `1 approval recorded · ${approvalAudit.resource_id}` : "No approvals recorded yet",
      dimension_library: "Dimension library empty",
      thresholds: "No thresholds registered yet",
      department_mapping: "No mappings configured",
      required_checks: "No required checks yet",
      gate_policy: "No gate policies configured",
      approval: lastAudit ? `Last action: ${lastAudit.event} ${lastAudit.resource_id} (${lastAudit.audit_ref})` : "No governance actions yet",
      impact: "No pending revalidation",
      audit_ref: lastAudit?.audit_ref ?? "—",
    } as Readonly<Record<string, string>>,
    control_enabled: {
      "CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN": true,
      "CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN": true,
      "CTRL-ADMIN-SG-02-THRESHOLDS-OPEN": true,
      "CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN": true,
      "CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN": true,
      "CTRL-ADMIN-SG-02-GATE-POLICY-OPEN": true,
      "CTRL-ADMIN-SG-02-APPROVAL-OPEN": true,
      "CTRL-ADMIN-SG-02-IMPACT-OPEN": true,
      "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE": hasDraft,
      "CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE": hasReview,
      "CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN": true,
    } as Readonly<Record<string, boolean>>,
    test_metadata: TEST_METADATA,
  };
}

function evaluateTestScopedGates(request: IamRuntimeRequest): GateResult {
  const payload = record(request.payload);
  const resourceId = text(payload.resource_id);
  const resourceType = text(payload.resource_type);
  if (request.operation === "configureGovernedResource") {
    if (!resourceType || !resourceId || payload.config_patch_json === undefined || payload.config_patch_json === null || !text(payload.reason)) return { ok: false, reason_code: "SG02_REQUIRED_FIELDS_MISSING" };
  } else if (request.operation === "approveGovernedResource") {
    if (!resourceType || !resourceId || !text(payload.rationale)) return { ok: false, reason_code: "SG02_REQUIRED_FIELDS_MISSING" };
  } else {
    return { ok: false, reason_code: "IAM01_RUNTIME_NOT_BOUND" };
  }
  if (!(GOVERNED_RESOURCE_TYPES as readonly string[]).includes(resourceType as string)) return { ok: false, reason_code: "SG02_RESOURCE_TYPE_OUT_OF_PAGE_DOMAIN" };
  const resource = findResource(resourceId as string);
  if (!resource) return { ok: false, reason_code: "SG02_RESOURCE_NOT_FOUND" };
  if (resource.resource_type !== resourceType) return { ok: false, reason_code: "SG02_EXACT_REF_MISMATCH" };
  if (request.operation === "approveGovernedResource") {
    const expected = text(payload.expected_resource_version);
    if (expected && Number(expected) !== resource.version) return { ok: false, reason_code: "SG02_VERSION_CONFLICT" };
    if (resource.state !== "REVIEW") return { ok: false, reason_code: resource.state === "APPROVED" || resource.state === "ACTIVE" ? "SG02_ACTIVE_RESOURCE_IMMUTABLE" : "SG02_STATE_GUARD_REJECTED" };
  } else {
    if (resource.state !== "DRAFT") return { ok: false, reason_code: resource.state === "APPROVED" || resource.state === "ACTIVE" ? "SG02_ACTIVE_RESOURCE_IMMUTABLE" : "SG02_STATE_GUARD_REJECTED" };
  }
  return { ok: true };
}

function executeGovernedCommand(request: IamRuntimeRequest): unknown {
  const payload = record(request.payload);
  const resourceId = text(payload.resource_id) as string;
  const resource = findResource(resourceId) as GovernedResource;
  if (request.operation === "configureGovernedResource") {
    resource.version += 1;
    resource.config_patch_json = payload.config_patch_json;
    resource.reason = text(payload.reason);
    const audit = appendAudit({ event: "governance.configured", resource_id: resourceId, correlation_id: request.correlation_id, outcome: "SUCCESS" });
    return { resource_id: resourceId, state: resource.state, version: resource.version, event: "governance.configured", audit_ref: audit.audit_ref, test_metadata: TEST_METADATA };
  }
  resource.state = "APPROVED";
  resource.rationale = text(payload.rationale);
  const audit = appendAudit({ event: "governance.approved", resource_id: resourceId, correlation_id: request.correlation_id, outcome: "SUCCESS" });
  return { resource_id: resourceId, state: resource.state, version: resource.version, event: "governance.approved", audit_ref: audit.audit_ref, test_metadata: TEST_METADATA };
}

export async function executeControlledQaCriteriaGovernance(request: IamRuntimeRequest): Promise<{ ok: true; value: unknown; correlation_id: string } | { ok: false; reason_code: string; correlation_id: string } | null> {
  if ((request.operation !== "configureGovernedResource" && request.operation !== "approveGovernedResource") || !isControlledQaCriteriaServerTestMode()) return null;
  const payload = record(request.payload);
  const resourceType = text(payload.resource_type);
  const resourceId = text(payload.resource_id) ?? request.resource_id ?? null;
  if (resourceType === "social_platform" || (typeof resourceId === "string" && resourceId.startsWith("TEST-SOC-PLATFORM"))) return null;
  const cached = state.idempotency.get(request.correlation_id);
  if (cached) return cached.ok ? { ok: true as const, value: cached.value, correlation_id: request.correlation_id } : { ok: false as const, reason_code: cached.reason_code as string, correlation_id: request.correlation_id };
  seedFixture();
  const gate = evaluateTestScopedGates(request);
  if (!gate.ok) {
    state.idempotency.set(request.correlation_id, { ok: false, reason_code: gate.reason_code });
    appendAudit({ event: eventOf(request.operation), resource_id: text(record(request.payload).resource_id) ?? "unresolved", correlation_id: request.correlation_id, outcome: "DENIED", reason_code: gate.reason_code });
    return { ok: false as const, reason_code: gate.reason_code, correlation_id: request.correlation_id };
  }
  const value = executeGovernedCommand(request);
  state.idempotency.set(request.correlation_id, { ok: true, value });
  return { ok: true as const, value, correlation_id: request.correlation_id };
}
