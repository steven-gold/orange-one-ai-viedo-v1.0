import { executeControlledSocCandidateDecision } from "@/server/testing/controlledSocTestRuntime";
import { executeControlledInfoCandidateDecision } from "@/server/testing/controlledInfoTestRuntime";
import { namedReason } from "@/server/shared/namedRuntimeError";

export type CandidateDecisionRequest = {
  correlation_id: string;
  candidate_id: string;
  payload: unknown;
};

export type CandidateDecisionBindings = {
  authorize: (request: CandidateDecisionRequest) => Promise<{ allowed: true } | { allowed: false; reason_code?: string }>;
  decide: (request: CandidateDecisionRequest) => Promise<unknown>;
  audit: (entry: CandidateDecisionRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string }) => Promise<void>;
};

let binding: CandidateDecisionBindings | null = null;

export function configureCandidateDecisionRuntime(next: CandidateDecisionBindings) {
  binding = next;
}

async function audit(current: CandidateDecisionBindings, entry: Parameters<CandidateDecisionBindings["audit"]>[0]) {
  try {
    await current.audit(entry);
  } catch {
    /* a failed audit sink must never turn a denied request into an allow */
  }
}

function statusFor(reason_code: string): number {
  if (reason_code.includes("VERSION_CONFLICT")) return 409;
  if (reason_code.includes("REQUIRED") || reason_code.includes("INVALID")) return 400;
  if (reason_code.includes("PERMISSION") || reason_code.includes("DENIED") || reason_code.includes("AUTHORIZATION")) return 403;
  return 503;
}

export async function decideCandidate(request: CandidateDecisionRequest) {
  if (!binding) {
    const { bindIdentityPageCommandRuntimes } = await import("@/server/shared/identityPageCommandRuntime");
    bindIdentityPageCommandRuntimes();
  }

  const current = binding;
  if (!current) {
    const soc = await executeControlledSocCandidateDecision(request);
    if (soc) {
      return soc.ok
        ? { ok: true as const, value: soc.value, correlation_id: request.correlation_id }
        : { ok: false as const, status: soc.status, reason_code: soc.reason_code, correlation_id: request.correlation_id };
    }
    const info = await executeControlledInfoCandidateDecision(request);
    if (info) {
      return info.ok
        ? { ok: true as const, value: info.value, correlation_id: request.correlation_id }
        : { ok: false as const, status: info.status, reason_code: info.reason_code, correlation_id: request.correlation_id };
    }
    return {
      ok: false as const,
      status: 503,
      reason_code: "CANDIDATE_DECISION_RUNTIME_NOT_BOUND",
      correlation_id: request.correlation_id,
    };
  }

  const authorization = await current.authorize(request).catch(() => ({
    allowed: false as const,
    reason_code: "AUTHORIZATION_EVALUATION_FAILED",
  }));
  if (!authorization.allowed) {
    const reason_code = authorization.reason_code ?? "PERMISSION_OR_GATE_DENIED";
    await audit(current, { ...request, outcome: "DENIED", reason_code });
    return { ok: false as const, status: 403, reason_code, correlation_id: request.correlation_id };
  }

  await audit(current, { ...request, outcome: "ALLOWED" });
  try {
    const value = await current.decide(request);
    await audit(current, { ...request, outcome: "SUCCESS" });
    return { ok: true as const, value, correlation_id: request.correlation_id };
  } catch (error) {
    const reason_code = namedReason(error, "CANDIDATE_DECISION_FAILED");
    await audit(current, { ...request, outcome: "ERROR", reason_code });
    return { ok: false as const, status: statusFor(reason_code), reason_code, correlation_id: request.correlation_id };
  }
}
