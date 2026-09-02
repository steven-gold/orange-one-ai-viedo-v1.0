import { executeControlledSocCommand, isControlledSocServerTestMode, type SocCommandOperation, type SocRuntimeRequest } from "@/server/testing/controlledSocTestRuntime";

export type SocCommandResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; status: number; reason_code: string; correlation_id: string };

type Binding = {
  authorize: (r: SocRuntimeRequest) => Promise<{ allowed: true } | { allowed: false; reason_code?: string }>;
  execute: (r: SocRuntimeRequest) => Promise<unknown>;
  audit: (e: SocRuntimeRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string }) => Promise<void>;
};

let binding: Binding | null = null;

export function configureSocCommandRuntime(next: Binding) { binding = next; }

async function audit(b: Binding, e: Parameters<Binding["audit"]>[0]) { try { await b.audit(e); } catch { /* fail closed */ } }

export async function runSocCommand(request: SocRuntimeRequest): Promise<SocCommandResult> {
  const b = binding;
  if (!b) {
    if (isControlledSocServerTestMode()) return executeControlledSocCommand(request);
    return { ok: false as const, status: 503, reason_code: "SOC_COMMAND_RUNTIME_NOT_BOUND", correlation_id: request.correlation_id };
  }
  const a = await b.authorize(request).catch(() => ({ allowed: false as const, reason_code: "SOC01_AUTHORIZATION_EVALUATION_FAILED" }));
  if (!a.allowed) {
    await audit(b, { ...request, outcome: "DENIED", reason_code: a.reason_code ?? "SOC01_PERMISSION_OR_GATE_DENIED" });
    return { ok: false as const, status: 403, reason_code: a.reason_code ?? "SOC01_PERMISSION_OR_GATE_DENIED", correlation_id: request.correlation_id };
  }
  await audit(b, { ...request, outcome: "ALLOWED" });
  try {
    const value = await b.execute(request);
    await audit(b, { ...request, outcome: "SUCCESS" });
    return { ok: true as const, value, correlation_id: request.correlation_id };
  } catch {
    await audit(b, { ...request, outcome: "ERROR", reason_code: "SOC01_OPERATION_FAILED" });
    return { ok: false as const, status: 503, reason_code: "SOC01_OPERATION_FAILED", correlation_id: request.correlation_id };
  }
}

export function isSocOperation(operation: string): operation is SocCommandOperation {
  return [
    "configureGovernedResource", "setKillSwitch", "bindSocialAccount", "revealSocialCredential",
    "unbindSocialAccount", "createSocialTargetDiscovery", "requestSocialTargetJoin", "completeSocialManualAction",
    "saveDraft", "decideCandidate", "configureSocialTargetPolicy", "requestSocialTargetPublish",
    "searchProjection", "refreshProjection",
  ].includes(operation);
}
