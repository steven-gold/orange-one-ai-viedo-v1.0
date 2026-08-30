import type { CoreRuntimeRequest, CoreRuntimeResult } from "@/domain/core/coreRuntimeContract";

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
  const runtime = bindings;
  if (!runtime) return { ok: false, error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "CORE_RUNTIME_NOT_BOUND", correlation_id: request.correlation_id, status: 503 };
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
  } catch {
    await audit(runtime, { ...request, outcome: "ERROR", reason_code: "CORE_PORT_EXECUTION_FAILED" });
    return { ok: false, error_uid: "CORE-01-ERR-CONTEXT-001", reason_code: "CORE_PORT_EXECUTION_FAILED", correlation_id: request.correlation_id, status: 503 };
  }
}
