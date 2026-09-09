import type { CoreRuntimeRequest, CoreRuntimeResult } from "@/domain/core/coreRuntimeContract";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { getControlledCoreTestRuntimeBindings } from "@/server/testing/controlledCoreTestRuntime";
import { namedReason } from "@/server/shared/namedRuntimeError";

export type CoreRuntimeBindings = {
  authorize: (request: CoreRuntimeRequest) => Promise<{ allowed: true } | { allowed: false; reason_code?: string }>;
  execute: (request: CoreRuntimeRequest) => Promise<unknown>;
  audit: (entry: CoreRuntimeRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string }) => Promise<void>;
};

let bindings: CoreRuntimeBindings | null = null;

export function configureCoreRuntime(next: CoreRuntimeBindings): void { bindings = next; }

async function audit(runtime: CoreRuntimeBindings, entry: Parameters<CoreRuntimeBindings["audit"]>[0]): Promise<void> {
  try { await runtime.audit(entry); } catch { /* audit failure never fabricates success */ }
}

export async function executeCorePort(request: CoreRuntimeRequest): Promise<CoreRuntimeResult> {
  if (!bindings && !isControlledTestMode()) {
    const { bindIdentityPageCommandRuntimes } = await import("@/server/shared/identityPageCommandRuntime");
    bindIdentityPageCommandRuntimes();
  }
  const runtime = bindings ?? (isControlledTestMode() ? getControlledCoreTestRuntimeBindings() : null);
  if (!runtime) {
    if (request.port_uid === "CORE-01-PORT-PROJECT-CREATE" || request.port_uid === "CORE-01-PORT-TOPIC-CREATE") {
      return { ok: false, error_uid: "CORE-01-ERR-PERM-001", reason_code: "IAM_ACCOUNT_PERMISSION_RUNTIME_NOT_BOUND", correlation_id: request.correlation_id, status: 403 };
    }
    return { ok: false, error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "CORE_RUNTIME_NOT_BOUND", correlation_id: request.correlation_id, status: 503 };
  }
  let decision: Awaited<ReturnType<CoreRuntimeBindings["authorize"]>>;
  try { decision = await runtime.authorize(request); }
  catch {
    await audit(runtime, { ...request, outcome: "DENIED", reason_code: "AUTHORIZATION_EVALUATION_FAILED" });
    return { ok: false, error_uid: "CORE-01-ERR-PERM-001", reason_code: "AUTHORIZATION_EVALUATION_FAILED", correlation_id: request.correlation_id, status: 403 };
  }
  if (!decision.allowed) {
    const reason_code = decision.reason_code ?? "PERMISSION_OR_SCOPE_DENIED";
    await audit(runtime, { ...request, outcome: "DENIED", reason_code });
    return { ok: false, error_uid: "CORE-01-ERR-PERM-001", reason_code, correlation_id: request.correlation_id, status: 403 };
  }
  await audit(runtime, { ...request, outcome: "ALLOWED" });
  try {
    const value = await runtime.execute(request);
    await audit(runtime, { ...request, outcome: "SUCCESS" });
    return { ok: true, value, correlation_id: request.correlation_id };
  } catch (error) {
    const reason_code = namedReason(error, "CORE_PORT_EXECUTION_FAILED");
    await audit(runtime, { ...request, outcome: "ERROR", reason_code });
    const status =
      reason_code.includes("PERMISSION") || reason_code.includes("AUTHORIZATION") || reason_code.includes("SEPARATION_OF_DUTIES") ? 403 :
      reason_code.includes("NOT_FOUND") ? 404 :
      reason_code.includes("VERSION_CONFLICT") || reason_code.includes("STATE_CONFLICT") || reason_code.includes("IDEMPOTENCY_CONFLICT") || reason_code.includes("MISMATCH") ? 409 :
      reason_code.includes("INVALID") || reason_code.includes("REQUIRED") || reason_code.includes("R9_CONTEXT") ? 400 :
      reason_code.includes("CONTRACT") ? 422 : 503;
    return { ok: false, error_uid: status===403 ? "CORE-01-ERR-PERM-001" : "CORE-01-ERR-CONTEXT-001", reason_code, correlation_id: request.correlation_id, status };
  }
}
