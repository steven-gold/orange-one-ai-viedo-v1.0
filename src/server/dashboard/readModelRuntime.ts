import {
  type DashboardReadError,
  type DashboardReadModel,
  type DashboardReadResult,
  validateDashboardReadModel,
} from "@/domain/dashboard/readModelContract";

export type DashboardAccessRequest = {
  correlation_id: string;
};

export type DashboardAuthorizationDecision =
  | { allowed: true }
  | { allowed: false; discloseable_reason_code?: string };

export type DashboardRuntimeBindings = {
  authorize: (request: DashboardAccessRequest) => Promise<DashboardAuthorizationDecision>;
  readProjection: (request: DashboardAccessRequest) => Promise<unknown>;
  audit: (entry: {
    correlation_id: string;
    outcome: "ALLOWED" | "DENIED" | "READ_ERROR" | "SCHEMA_ERROR" | "SUCCESS";
    reason_code?: string;
  }) => Promise<void>;
};

let bindings: DashboardRuntimeBindings | null = null;

export function configureDashboardRuntime(next: DashboardRuntimeBindings): void {
  bindings = next;
}

function error(error_uid: DashboardReadError["error_uid"], reason_code: string, correlation_id: string): DashboardReadResult {
  return { ok: false, error: { error_uid, reason_code, correlation_id } };
}

async function safeAudit(
  runtime: DashboardRuntimeBindings,
  entry: Parameters<DashboardRuntimeBindings["audit"]>[0],
): Promise<void> {
  try {
    await runtime.audit(entry);
  } catch {
    // Audit failure must never fabricate a successful business read.
  }
}

export async function getDashboardReadModel(request: DashboardAccessRequest): Promise<DashboardReadResult> {
  const runtime = bindings;
  if (!runtime) {
    return error("WB-01-ERR-READ-001", "DASHBOARD_RUNTIME_NOT_BOUND", request.correlation_id);
  }

  let decision: DashboardAuthorizationDecision;
  try {
    decision = await runtime.authorize(request);
  } catch {
    await safeAudit(runtime, { ...request, outcome: "DENIED", reason_code: "AUTHORIZATION_EVALUATION_FAILED" });
    return error("WB-01-ERR-POLICY-001", "AUTHORIZATION_EVALUATION_FAILED", request.correlation_id);
  }

  if (!decision.allowed) {
    const reason = decision.discloseable_reason_code ?? "POLICY_BLOCKED";
    await safeAudit(runtime, { ...request, outcome: "DENIED", reason_code: reason });
    return error("WB-01-ERR-POLICY-001", reason, request.correlation_id);
  }

  await safeAudit(runtime, { ...request, outcome: "ALLOWED" });

  let projection: unknown;
  try {
    projection = await runtime.readProjection(request);
  } catch {
    await safeAudit(runtime, { ...request, outcome: "READ_ERROR", reason_code: "DASHBOARD_PROJECTION_READ_FAILED" });
    return error("WB-01-ERR-READ-001", "DASHBOARD_PROJECTION_READ_FAILED", request.correlation_id);
  }

  const validated = validateDashboardReadModel(projection, request.correlation_id);
  if (!validated.ok) {
    await safeAudit(runtime, { ...request, outcome: "SCHEMA_ERROR", reason_code: validated.error.reason_code });
    return validated;
  }

  const value: DashboardReadModel = validated.value;
  await safeAudit(runtime, { ...request, outcome: "SUCCESS" });
  return { ok: true, value };
}
