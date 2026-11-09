export const SYS_STATE_CONTEXT_UID = "SYS-01-STATE-CONTEXT";
export const SYS_STATE_CONVERSATION_UID = "SYS-01-STATE-CONVERSATION";
export const SYS_STATE_LEDGER_UID = "SYS-01-STATE-LEDGER";
export const SYS_STATE_CHANGE_UID = "SYS-01-STATE-CHANGE";
export const SYS_STATE_SANDBOX_UID = "SYS-01-STATE-SANDBOX";
export const SYS_STATE_MODE_UID = "SYS-01-STATE-MODE";
export const SYS_STATE_GENERATION_UID = "SYS-01-STATE-GENERATION";
export const SYS_STATE_ERROR_UID = "SYS-01-STATE-ERROR";

export type SysAiMode = "SINGLE_AI" | "MULTI_AI";
export type SysCouncilMode = "DISCUSSION" | "PARALLEL";

export interface SysMode {
  aiMode: SysAiMode;
  councilMode: SysCouncilMode;
  multiRouteReason?: string;
}

export interface SysTurn {
  id: string;
  role: "user" | "assistant" | "synthesis";
  alias?: string;
  text: string;
  route?: string;
  status: "SENT" | "PENDING" | "ABORTED" | "FAILED";
  at: string;
}

export interface SysDecision {
  id: string;
  status: "CONFIRMED" | "REJECTED" | "OPEN_P0" | "OPEN_P1" | "SUPERSEDED";
  priority: "P0" | "P1" | "P2" | "P3";
  question: string;
  resolution: string;
  at: string;
}

export interface SysChange {
  changeId: string;
  goal: string;
  scope: string;
  status: "CANDIDATE" | "REQUESTED" | "SANDBOX_RUNNING" | "SANDBOX_PASS" | "SANDBOX_FAIL";
  candidateAt?: string;
  requestedAt?: string;
}

export interface SysSandboxResult {
  changeId: string;
  dimensions: Array<{ dimension: string; outcome: "PASS" | "FAIL"; detail: string }>;
  verdict: "PASS" | "FAIL";
  at: string;
}

// System Continuity Context (word §pre_response_gate): the seven resolved
// groups the assistant must resolve before any design mutation.
export interface SysContext {
  systemTruth: {
    version: string;
    services: string[];
    authorities: string[];
    providers: string[];
  };
  conversation: {
    conversationId: string;
    threadId: string;
    branchId: string;
  };
  fingerprint: string;
}

export function sysContextFingerprint(context: SysContext): string {
  const raw = JSON.stringify({
    version: context.systemTruth.version,
    services: context.systemTruth.services,
    authorities: context.systemTruth.authorities,
    providers: context.systemTruth.providers,
    conversation: context.conversation,
  });
  let hash = 2166136261;
  for (let index = 0; index < raw.length; index += 1) {
    hash ^= raw.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `CTX-${(hash >>> 0).toString(16).toUpperCase()}`;
}

export interface SysWorkbench {
  context: SysContext | null;
  turns: SysTurn[];
  ledger: SysDecision[];
  change: SysChange | null;
  sandbox: SysSandboxResult | null;
  mode: SysMode;
  generation: { active: boolean; startedAt: string } | null;
  error: { code: string; at: string } | null;
  routeRaw?: string | null;
}

export function readSysWorkbench(read: (uid: string) => string | null): SysWorkbench {
  const parse = <T,>(uid: string, fallback: T): T => {
    const text = (read(uid) ?? "").trim();
    if (!text) return fallback;
    try {
      return JSON.parse(text) as T;
    } catch {
      return fallback;
    }
  };
  return {
    context: parse<SysContext | null>(SYS_STATE_CONTEXT_UID, null),
    turns: parse<SysTurn[]>(SYS_STATE_CONVERSATION_UID, []),
    ledger: parse<SysDecision[]>(SYS_STATE_LEDGER_UID, []),
    change: parse<SysChange | null>(SYS_STATE_CHANGE_UID, null),
    sandbox: parse<SysSandboxResult | null>(SYS_STATE_SANDBOX_UID, null),
    mode: parse<SysMode>(SYS_STATE_MODE_UID, { aiMode: "SINGLE_AI", councilMode: "DISCUSSION" }),
    generation: parse<{ active: boolean; startedAt: string } | null>(SYS_STATE_GENERATION_UID, null),
    error: parse<{ code: string; at: string } | null>(SYS_STATE_ERROR_UID, null),
  };
}

export function writeSysWorkbench(workbench: SysWorkbench): Record<string, string> {
  const output: Record<string, string> = {};
  output[SYS_STATE_CONTEXT_UID] = workbench.context ? JSON.stringify(workbench.context) : "";
  output[SYS_STATE_CONVERSATION_UID] = JSON.stringify(workbench.turns);
  output[SYS_STATE_LEDGER_UID] = JSON.stringify(workbench.ledger);
  output[SYS_STATE_CHANGE_UID] = workbench.change ? JSON.stringify(workbench.change) : "";
  output[SYS_STATE_SANDBOX_UID] = workbench.sandbox ? JSON.stringify(workbench.sandbox) : "";
  output[SYS_STATE_MODE_UID] = JSON.stringify(workbench.mode);
  output[SYS_STATE_GENERATION_UID] = workbench.generation ? JSON.stringify(workbench.generation) : "";
  output[SYS_STATE_ERROR_UID] = workbench.error ? JSON.stringify(workbench.error) : "";
  return output;
}

export function failSys(workbench: SysWorkbench, code: string): SysWorkbench {
  return { ...workbench, error: { code, at: new Date().toISOString() } };
}

export function clearSysError(workbench: SysWorkbench): SysWorkbench {
  return { ...workbench, error: null };
}

export const SYS_SANDBOX_DIMENSIONS = [
  "functional",
  "ui",
  "api",
  "database",
  "runtime",
  "permission",
  "provider",
  "cross_system",
] as const;
