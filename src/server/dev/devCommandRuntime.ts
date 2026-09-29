import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { namedReason } from "@/server/shared/namedRuntimeError";

export type DevCommandOperation =
  | "startCompanyDiscovery"
  | "pauseCompanyDiscovery"
  | "resumeCompanyDiscovery"
  | "stopCompanyDiscovery";

export type DevRuntimeRequest = {
  operation_id: DevCommandOperation;
  correlation_id: string;
  path_params: Record<string, string>;
  payload: unknown;
};

export type DevCommandResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; status: number; reason_code: string; correlation_id: string };

type Binding = {
  authorize: (request: DevRuntimeRequest) => Promise<{ allowed: true } | { allowed: false; reason_code?: string }>;
  execute: (request: DevRuntimeRequest) => Promise<unknown>;
  audit: (entry: DevRuntimeRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string }) => Promise<void>;
};

let binding: Binding | null = null;

export function configureDevCommandRuntime(next: Binding) {
  binding = next;
}

async function audit(bindingValue: Binding, entry: Parameters<Binding["audit"]>[0]) {
  try {
    await bindingValue.audit(entry);
  } catch {
    /* audit failure must not turn an already denied request into an allow */
  }
}

export async function runDevCommand(request: DevRuntimeRequest): Promise<DevCommandResult> {
  if (!binding) {
    const { bindIdentityPageCommandRuntimes } = await import("@/server/shared/identityPageCommandRuntime");
    bindIdentityPageCommandRuntimes();
  }
  const current = binding;
  if (!current) {
    return {
      ok: false,
      status: isControlledTestMode() ? 503 : 503,
      reason_code: "DEV_COMMAND_RUNTIME_NOT_BOUND",
      correlation_id: request.correlation_id,
    };
  }

  const authorization = await current.authorize(request).catch(() => ({
    allowed: false as const,
    reason_code: "DEV01_AUTHORIZATION_EVALUATION_FAILED",
  }));
  if (!authorization.allowed) {
    const reason_code = authorization.reason_code ?? "DEV01_PERMISSION_OR_GATE_DENIED";
    await audit(current, { ...request, outcome: "DENIED", reason_code });
    return { ok: false, status: 403, reason_code, correlation_id: request.correlation_id };
  }

  await audit(current, { ...request, outcome: "ALLOWED" });
  try {
    const value = await current.execute(request);
    await audit(current, { ...request, outcome: "SUCCESS" });
    return { ok: true, value, correlation_id: request.correlation_id };
  } catch (error) {
    const reason_code = namedReason(error, "DEV01_OPERATION_FAILED");
    await audit(current, { ...request, outcome: "ERROR", reason_code });
    const status = reason_code.includes("REQUIRED") || reason_code.includes("INVALID") || reason_code.includes("STATE_CONFLICT") ? 409 : 503;
    return { ok: false, status, reason_code, correlation_id: request.correlation_id };
  }
}
