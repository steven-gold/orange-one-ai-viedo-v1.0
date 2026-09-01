import type { KnowledgeRuntimeRequest, KnowledgeRuntimeResult } from "@/domain/knowledge/knowledgeRuntimeContract";
import { executeControlledKnowledgePort, isControlledKnowledgeServerTestMode } from "@/server/testing/controlledKnowledgeTestRuntime";

export type KnowledgeRuntimeBindings = {
  authorize: (request: KnowledgeRuntimeRequest) => Promise<{ allowed: true } | { allowed: false; reason_code?: string }>;
  execute: (request: KnowledgeRuntimeRequest) => Promise<unknown>;
  audit: (entry: KnowledgeRuntimeRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string }) => Promise<void>;
};

let bindings: KnowledgeRuntimeBindings | null = null;

export function configureKnowledgeRuntime(next: KnowledgeRuntimeBindings): void { bindings = next; }

export async function executeKnowledgePort(request: KnowledgeRuntimeRequest): Promise<KnowledgeRuntimeResult> {
  const runtime = bindings;
  if (!runtime) {
    if (isControlledKnowledgeServerTestMode()) return executeControlledKnowledgePort(request);
    return { ok: false, error_uid: "KB-01-ERR-001", reason_code: "KB_RUNTIME_NOT_BOUND", correlation_id: request.correlation_id, status: 503 };
  }
  let decision: Awaited<ReturnType<KnowledgeRuntimeBindings["authorize"]>>;
  try { decision = await runtime.authorize(request); }
  catch {
    await runtime.audit({ ...request, outcome: "DENIED", reason_code: "AUTHORIZATION_EVALUATION_FAILED" }).catch(() => undefined);
    return { ok: false, error_uid: "KB-01-ERR-001", reason_code: "AUTHORIZATION_EVALUATION_FAILED", correlation_id: request.correlation_id, status: 403 };
  }
  if (!decision.allowed) {
    const reason_code = decision.reason_code ?? "PERMISSION_OR_SCOPE_DENIED";
    await runtime.audit({ ...request, outcome: "DENIED", reason_code }).catch(() => undefined);
    return { ok: false, error_uid: "KB-01-ERR-001", reason_code, correlation_id: request.correlation_id, status: 403 };
  }
  await runtime.audit({ ...request, outcome: "ALLOWED" }).catch(() => undefined);
  try {
    const value = await runtime.execute(request);
    await runtime.audit({ ...request, outcome: "SUCCESS" }).catch(() => undefined);
    return { ok: true, value, correlation_id: request.correlation_id };
  } catch {
    await runtime.audit({ ...request, outcome: "ERROR", reason_code: "KB_PORT_EXECUTION_FAILED" }).catch(() => undefined);
    return { ok: false, error_uid: "KB-01-ERR-001", reason_code: "KB_PORT_EXECUTION_FAILED", correlation_id: request.correlation_id, status: 503 };
  }
}
