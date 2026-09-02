import { executeControlledErpCommand, isControlledErpServerTestMode, type ErpCommandOperation, type ErpRuntimeRequest } from "@/server/testing/controlledErpTestRuntime";

export type ErpCommandResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; status: number; reason_code: string; correlation_id: string };

type Binding = {
  authorize: (r: ErpRuntimeRequest) => Promise<{ allowed: true } | { allowed: false; reason_code?: string }>;
  execute: (r: ErpRuntimeRequest) => Promise<unknown>;
  audit: (e: ErpRuntimeRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string }) => Promise<void>;
};

let binding: Binding | null = null;

export function configureErpCommandRuntime(next: Binding) { binding = next; }

async function audit(b: Binding, e: Parameters<Binding["audit"]>[0]) { try { await b.audit(e); } catch { /* fail closed */ } }

export async function runErpCommand(request: ErpRuntimeRequest): Promise<ErpCommandResult> {
  const b = binding;
  if (!b) {
    if (isControlledErpServerTestMode()) return executeControlledErpCommand(request);
    return { ok: false as const, status: 503, reason_code: "ERP_COMMAND_RUNTIME_NOT_BOUND", correlation_id: request.correlation_id };
  }
  const a = await b.authorize(request).catch(() => ({ allowed: false as const, reason_code: "ERP01_AUTHORIZATION_EVALUATION_FAILED" }));
  if (!a.allowed) {
    await audit(b, { ...request, outcome: "DENIED", reason_code: a.reason_code ?? "ERP01_PERMISSION_OR_GATE_DENIED" });
    return { ok: false as const, status: 403, reason_code: a.reason_code ?? "ERP01_PERMISSION_OR_GATE_DENIED", correlation_id: request.correlation_id };
  }
  await audit(b, { ...request, outcome: "ALLOWED" });
  try {
    const value = await b.execute(request);
    await audit(b, { ...request, outcome: "SUCCESS" });
    return { ok: true as const, value, correlation_id: request.correlation_id };
  } catch {
    await audit(b, { ...request, outcome: "ERROR", reason_code: "ERP01_OPERATION_FAILED" });
    return { ok: false as const, status: 503, reason_code: "ERP01_OPERATION_FAILED", correlation_id: request.correlation_id };
  }
}

export function isErpOperation(operation: string): operation is ErpCommandOperation {
  return [
    "createERPConnector", "updateERPConnector", "validateERPConnector", "validateERPMapping",
    "refreshERPSnapshot", "createERPSyncJob", "getERPSyncStatus", "retryERPSync", "getERPFailure",
    "getERPFinanceFactPack", "getERPCapacityGuardrails", "getERPForecast",
    "exportProjection", "refreshProjection",
  ].includes(operation);
}
