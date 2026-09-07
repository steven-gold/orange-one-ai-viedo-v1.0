import type { SysServiceOperation, SystemContinuityContext } from "@/domain/system/systemRuntimeContract";
import { namedReason } from "@/server/shared/namedRuntimeError";

export type SysRequest = {
  operation_id: SysServiceOperation;
  correlation_id: string;
  context: SystemContinuityContext;
  payload?: unknown;
  generated_system_change_id: boolean;
};
export type SysBindings = {
  resolveContinuityContext: (system_change_id: string) => Promise<SystemContinuityContext>;
  authorize: (r: SysRequest) => Promise<{ allowed: true } | { allowed: false; reason_code?: string }>;
  execute: (r: SysRequest) => Promise<unknown>;
  audit: (e: SysRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string }) => Promise<void>;
};

let binding: SysBindings | null = null;

export function configureSystemLifecycleRuntime(n: SysBindings) {
  binding = n;
}

async function audit(b: SysBindings, e: Parameters<SysBindings["audit"]>[0]) {
  try { await b.audit(e); } catch { /* fail closed */ }
}

export async function executeSystemLifecycleOperation(input: {
  operation_id: SysServiceOperation;
  correlation_id: string;
  system_change_id?: string | null;
  payload?: unknown;
}) {
  if (!binding) {
    const { bindIdentityPageCommandRuntimes } = await import("@/server/shared/identityPageCommandRuntime");
    bindIdentityPageCommandRuntimes();
  }
  const b = binding;
  if (!b) return { ok: false as const, reason_code: "SYS01_RUNTIME_NOT_BOUND", correlation_id: input.correlation_id };
  const suppliedSystemChangeId = input.system_change_id?.trim() || null;
  if (!suppliedSystemChangeId && input.operation_id !== "createCandidate") {
    return { ok: false as const, reason_code: "SYSTEM_CHANGE_ID_REQUIRED", correlation_id: input.correlation_id };
  }
  const generated_system_change_id = suppliedSystemChangeId === null;
  const systemChangeId = suppliedSystemChangeId ?? crypto.randomUUID();
  const context = await b.resolveContinuityContext(systemChangeId).catch(() => null);
  if (!context) return { ok: false as const, reason_code: "SYSTEM_CONTINUITY_CONTEXT_UNRESOLVED", correlation_id: input.correlation_id };
  const r: SysRequest = { operation_id: input.operation_id, correlation_id: input.correlation_id, context, payload: input.payload, generated_system_change_id };
  const a = await b.authorize(r).catch(() => ({ allowed: false as const, reason_code: "AUTHORIZATION_EVALUATION_FAILED" }));
  if (!a.allowed) {
    const reason_code = a.reason_code ?? "PERMISSION_OR_GATE_DENIED";
    await audit(b, { ...r, outcome: "DENIED", reason_code });
    return { ok: false as const, reason_code, correlation_id: input.correlation_id };
  }
  await audit(b, { ...r, outcome: "ALLOWED" });
  try {
    const value = await b.execute(r);
    await audit(b, { ...r, outcome: "SUCCESS" });
    return { ok: true as const, value, correlation_id: input.correlation_id };
  } catch (error) {
    const reason_code = namedReason(error, "SYS01_SERVICE_OPERATION_FAILED");
    await audit(b, { ...r, outcome: "ERROR", reason_code });
    return { ok: false as const, reason_code, correlation_id: input.correlation_id };
  }
}
