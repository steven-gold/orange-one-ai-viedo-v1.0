import type { KnowledgeRuntimeRequest, KnowledgeRuntimeResult } from "@/domain/knowledge/knowledgeRuntimeContract";
import { executeControlledKnowledgePort, isControlledKnowledgeServerTestMode } from "@/server/testing/controlledKnowledgeTestRuntime";
import { namedReason } from "@/server/shared/namedRuntimeError";

export type KnowledgeRuntimeBindings = {
  authorize: (request: KnowledgeRuntimeRequest) => Promise<{ allowed: true } | { allowed: false; reason_code?: string }>;
  execute: (request: KnowledgeRuntimeRequest) => Promise<unknown>;
  audit: (entry: KnowledgeRuntimeRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string }) => Promise<void>;
};

let bindings: KnowledgeRuntimeBindings | null = null;

export function configureKnowledgeRuntime(next: KnowledgeRuntimeBindings): void { bindings = next; }

function statusForReason(reason_code: string): number {
  if (reason_code.includes("PERMISSION") || reason_code.includes("AUTHORIZATION") || reason_code.includes("DENIED")) return 403;
  if (reason_code.includes("NOT_FOUND")) return 404;
  if (reason_code.includes("VERSION_CONFLICT") || reason_code.includes("STATE_GUARD") || reason_code.includes("IDEMPOTENCY_CONFLICT")) return 409;
  if (
    reason_code.includes("REQUIRED")
    || reason_code.includes("INVALID")
    || reason_code.includes("MISMATCH")
    || reason_code.includes("SCHEMA")
  ) return 400;
  return 503;
}

export async function executeKnowledgePort(request: KnowledgeRuntimeRequest): Promise<KnowledgeRuntimeResult> {
  if (!bindings) {
    const { bindIdentityPageCommandRuntimes } = await import("@/server/shared/identityPageCommandRuntime");
    bindIdentityPageCommandRuntimes();
  }
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
  } catch (error) {
    const reason_code = namedReason(error, "KB_PORT_EXECUTION_FAILED");
    await runtime.audit({ ...request, outcome: "ERROR", reason_code }).catch(() => undefined);
    return { ok: false, error_uid: "KB-01-ERR-001", reason_code, correlation_id: request.correlation_id, status: statusForReason(reason_code) };
  }
}
