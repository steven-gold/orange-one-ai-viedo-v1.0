import { namedReason } from "@/server/shared/namedRuntimeError";
import { executeControlledAiApiCommand, isControlledAiApiServerTestMode } from "@/server/testing/controlledAiApiTestRuntime";

export type AiApiOperation =
  | "createProviderModelProfile"
  | "updateProviderModelProfile"
  | "getProviderModelProfile"
  | "listProviderModelProfiles"
  | "testProviderModelProfile"
  | "retireProviderModelProfile"
  | "setProviderModelCredential"
  | "deleteProviderModelCredential"
  | "setKillSwitch"
  | "createProviderCandidateGroup"
  | "getProviderQuarantine"
  | "restoreProviderFromQuarantine"
  | "runSandboxTest"
  | "executeProviderRoute"
  | "getProviderRouteDecision"
  | "runProviderQueueProbe";

export type AiApiRuntimeRequest = {
  operation_id: AiApiOperation;
  correlation_id: string;
  path_params: Record<string, string>;
  payload: unknown;
};

type Decision = { allowed: true } | { allowed: false; reason_code?: string };
type Binding = {
  authorize: (request: AiApiRuntimeRequest) => Promise<Decision>;
  execute: (request: AiApiRuntimeRequest) => Promise<unknown>;
  audit: (entry: AiApiRuntimeRequest & {
    outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR";
    reason_code?: string;
  }) => Promise<void>;
};

export type AiApiCommandResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; status: number; reason_code: string; correlation_id: string };

let binding: Binding | null = null;

export function configureAiApiCommandRuntime(next: Binding): void {
  binding = next;
}

async function safeAudit(
  current: Binding,
  entry: Parameters<Binding["audit"]>[0],
): Promise<void> {
  try {
    await current.audit(entry);
  } catch {
    // Audit failure is intentionally non-disclosing; business operation remains fail-closed elsewhere.
  }
}

function statusFor(reason: string): number {
  if (reason.includes("REQUIRED") || reason.includes("INVALID") || reason.includes("FORBIDDEN_FIELD")) return 400;
  if (reason.includes("NOT_FOUND")) return 404;
  if (reason.includes("VERSION_CONFLICT")) return 409;
  if (reason.includes("PERMISSION") || reason.includes("AUTHORIZATION") || reason.includes("IDENTITY")) return 403;
  if (reason.includes("NOT_BOUND") || reason.includes("NOT_MATERIALIZED") || reason.includes("BLOCKED")) return 503;
  return 503;
}

export async function runAiApiCommand(request: AiApiRuntimeRequest): Promise<AiApiCommandResult> {
  if (!binding) {
    const { bindIdentityPageCommandRuntimes } = await import("@/server/shared/identityPageCommandRuntime");
    bindIdentityPageCommandRuntimes();
  }
  const current = binding;
  if (!current) {
    if (isControlledAiApiServerTestMode()) return executeControlledAiApiCommand(request);
    return {
      ok: false,
      status: 503,
      reason_code: "AIAPI_COMMAND_RUNTIME_NOT_BOUND",
      correlation_id: request.correlation_id,
    };
  }

  let decision: Decision;
  try {
    decision = await current.authorize(request);
  } catch {
    decision = { allowed: false, reason_code: "AIAPI01_AUTHORIZATION_EVALUATION_FAILED" };
  }

  if (!decision.allowed) {
    const reason_code = decision.reason_code ?? "AIAPI01_PERMISSION_OR_GATE_DENIED";
    await safeAudit(current, { ...request, outcome: "DENIED", reason_code });
    return { ok: false, status: 403, reason_code, correlation_id: request.correlation_id };
  }

  await safeAudit(current, { ...request, outcome: "ALLOWED" });
  try {
    const value = await current.execute(request);
    await safeAudit(current, { ...request, outcome: "SUCCESS" });
    return { ok: true, value, correlation_id: request.correlation_id };
  } catch (error) {
    const reason_code = namedReason(error, "AIAPI01_OPERATION_FAILED");
    await safeAudit(current, { ...request, outcome: "ERROR", reason_code });
    return {
      ok: false,
      status: statusFor(reason_code),
      reason_code,
      correlation_id: request.correlation_id,
    };
  }
}
