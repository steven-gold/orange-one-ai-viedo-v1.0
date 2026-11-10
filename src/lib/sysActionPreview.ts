import {
  clearSysError,
  failSys,
  readSysWorkbench,
  sysContextFingerprint,
  writeSysWorkbench,
  type SysChange,
  type SysDecision,
  type SysMode,
  type SysTurn,
  type SysWorkbench,
} from "./sysState";

function parsePayload<T>(raw: string | undefined, fallback: T): T {
  const text = (raw ?? "").trim();
  if (!text) return fallback;
  try {
    return JSON.parse(text) as T;
  } catch {
    return fallback;
  }
}

function turnId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// SYS-01-GATE-AI-MODE / GATE-MULTI-AI: switching the presentation mode must
// never create a new change, conversation, thread, ledger reset or route.
// The shared conversation core must resolve a live provider route (system
// owned) before MULTI_AI is accepted.
function applyMode(
  workbench: SysWorkbench,
  next: Partial<SysMode>,
  opts: { requireRoute?: boolean; requireCouncil?: boolean } = {},
): SysWorkbench {
  const mode = { ...workbench.mode };
  const route = parsePayload<{ ready: number; reason?: string }>(workbench.routeRaw ?? undefined, { ready: 0 });
  if (opts.requireRoute && (route.ready ?? 0) < 1) {
    return failSys(workbench, "SYS-01-ERR-MULTI-AI-ROUTE");
  }
  if (opts.requireCouncil && mode.aiMode !== "MULTI_AI") {
    return failSys(workbench, "SYS-01-ERR-COUNCIL-MODE");
  }
  return clearSysError({ ...workbench, mode: { ...mode, ...next } });
}

// SYS-01-GATE-CONVERSATION-SEND: pre_response_gate — the System Continuity
// Context must be resolved before a design conversation message is accepted.
function contextResolved(workbench: SysWorkbench): boolean {
  return Boolean(
    workbench.context?.systemTruth.version &&
      workbench.context.systemTruth.services.length &&
      workbench.context.conversation.conversationId,
  );
}

export function previewSysAction(
  controlUid: string,
  actionUid: string,
  read: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const workbench: SysWorkbench = {
    ...readSysWorkbench(read),
    routeRaw: read("SYS-01-STATE-ROUTE"),
  };
  const now = new Date().toISOString();

  if (actionUid === "SYS-01-ACT-AI-MODE-SINGLE") {
    const next = applyMode(workbench, { aiMode: "SINGLE_AI", councilMode: workbench.mode.councilMode });
    return writeSysWorkbench(next);
  }
  if (actionUid === "SYS-01-ACT-AI-MODE-MULTI") {
    const next = applyMode(workbench, { aiMode: "MULTI_AI", councilMode: "DISCUSSION" }, { requireRoute: true });
    return writeSysWorkbench(next);
  }
  if (actionUid === "SYS-01-ACT-COUNCIL-MODE-DISCUSSION") {
    const next = applyMode(workbench, { councilMode: "DISCUSSION" }, { requireCouncil: true });
    return writeSysWorkbench(next);
  }
  if (actionUid === "SYS-01-ACT-COUNCIL-MODE-PARALLEL") {
    const next = applyMode(workbench, { councilMode: "PARALLEL" }, { requireCouncil: true });
    return writeSysWorkbench(next);
  }

  if (actionUid === "SYS-01-ACT-MESSAGE-DRAFT") {
    // Visual phase: typing is a local draft only; nothing business-facing.
    return { "SYS-01-STATE-DRAFT": String(nextValue ?? "") };
  }

  if (actionUid === "SYS-01-ACT-CONVERSATION-SEND") {
    const payload = parsePayload<{ message?: string; aiMode?: string; councilMode?: string }>(nextValue, {});
    const message = String(payload.message ?? "").trim();
    if (!contextResolved(workbench)) {
      return writeSysWorkbench(failSys(workbench, "SYS-01-ERR-AI-MODE-CONTEXT"));
    }
    if (!message) {
      return writeSysWorkbench(failSys(workbench, "SYS_MESSAGE_REQUIRED"));
    }
    if (workbench.generation?.active) {
      return writeSysWorkbench(failSys(workbench, "SYS_GENERATION_IN_PROGRESS"));
    }
    const mode: SysMode = {
      aiMode: payload.aiMode === "MULTI_AI" ? "MULTI_AI" : workbench.mode.aiMode,
      councilMode: payload.councilMode === "PARALLEL" ? "PARALLEL" : workbench.mode.councilMode,
    };
    const turn: SysTurn = {
      id: turnId("TUR"),
      role: "user",
      text: message,
      status: "SENT",
      at: now,
    };
    const context = workbench.context!;
    const next = clearSysError({
      ...workbench,
      mode,
      turns: [...workbench.turns, turn],
      generation: { active: true, startedAt: now },
      context: { ...context, fingerprint: sysContextFingerprint(context) },
    });
    return writeSysWorkbench(next);
  }

  if (actionUid === "SYS-01-ACT-CONVERSATION-STOP") {
    if (!workbench.generation?.active) {
      return writeSysWorkbench(failSys(workbench, "SYS_NO_GENERATION_IN_PROGRESS"));
    }
    // Stop only the current generation: request cancellation via the shared
    // conversation core generation job; never delete/reset conversation,
    // ledger, draft or source refs (word: stop rule).
    const turns = workbench.turns.map((row) => (row.status === "PENDING" ? { ...row, status: "ABORTED" as const } : row));
    const next = clearSysError({
      ...workbench,
      turns,
      generation: { active: true, startedAt: workbench.generation.startedAt, cancelRequested: true },
    });
    return writeSysWorkbench(next);
  }

  if (actionUid === "SYS-01-ACT-CONVERSATION-ATTACH") {
    // conversation_composer_contract: attachment business execution stays
    // blocked until the global selector binding is registered.
    return writeSysWorkbench(failSys(workbench, "SYS_ATTACH_VISUAL_PHASE_BLOCKED"));
  }

  if (actionUid === "ACT-NAV-OPEN") {
    return writeSysWorkbench(failSys(workbench, "SYS_NAV_OPEN_VISUAL_PHASE_BLOCKED"));
  }

  if (actionUid === "ACT-CANDIDATE-CREATE") {
    const payload = parsePayload<{
      goal?: string;
      scope?: string;
      supersedeDecisionIds?: string[];
      conflictingDecisionIds?: string[];
    }>(nextValue, {});
    const goal = String(payload.goal ?? "").trim();
    if (!goal) return writeSysWorkbench(failSys(workbench, "SYS_GOAL_REQUIRED"));
    if (workbench.change && (workbench.change.status === "CANDIDATE" || workbench.change.status === "REQUESTED")) {
      return writeSysWorkbench(failSys(workbench, "SYS_CHANGE_ALREADY_ACTIVE"));
    }
    // decision_ledger_contract: conflicting proposals stay blocked until the
    // conflicting decision is explicitly reopened/superseded by an authorized
    // human decision. requirement_convergence_contract: P0/P1 must converge
    // before Design Freeze.
    const supersedeIds = (payload.supersedeDecisionIds ?? []).map(String);
    const conflictingIds = (payload.conflictingDecisionIds ?? []).map(String);
    const unknownSupersede = supersedeIds.find((id) => !workbench.ledger.some((row) => row.id === id));
    if (unknownSupersede) return writeSysWorkbench(failSys(workbench, "SYS_DECISION_UNRESOLVED"));
    const rejectedConflict = conflictingIds.find(
      (id) => workbench.ledger.some((row) => row.id === id && row.status === "REJECTED") && !supersedeIds.includes(id),
    );
    if (rejectedConflict) return writeSysWorkbench(failSys(workbench, "SYS_CONFLICTING_PROPOSAL"));
    const openLedger = workbench.ledger.filter((row) => row.status === "OPEN_P0" || row.status === "OPEN_P1");
    const unresolvedOpen = openLedger.find((row) => !supersedeIds.includes(row.id));
    if (unresolvedOpen) return writeSysWorkbench(failSys(workbench, "SYS_LEDGER_CONVERGENCE_REQUIRED"));
    const ledger = workbench.ledger.map((row) =>
      supersedeIds.includes(row.id)
        ? { ...row, status: "SUPERSEDED" as const, resolution: `${row.resolution} [superseded by ${goal.slice(0, 40)}]`.trim() }
        : row,
    );
    const change: SysChange = {
      changeId: `CHG-${Date.now().toString(36).toUpperCase()}`,
      goal,
      scope: String(payload.scope ?? "admin:SYS-01"),
      status: "CANDIDATE",
      candidateAt: now,
    };
    return writeSysWorkbench(clearSysError({ ...workbench, ledger, change }));
  }

  if (actionUid === "ACT-CR-CREATE") {
    if (!workbench.change || workbench.change.status !== "CANDIDATE") {
      return writeSysWorkbench(failSys(workbench, "SYS_CANDIDATE_REQUIRED"));
    }
    const change: SysChange = { ...workbench.change, status: "REQUESTED", requestedAt: now };
    return writeSysWorkbench(clearSysError({ ...workbench, change }));
  }

  if (actionUid === "SYS-01-ACT-SANDBOX-TEST") {
    if (!workbench.change || (workbench.change.status !== "REQUESTED" && workbench.change.status !== "SANDBOX_FAIL")) {
      return writeSysWorkbench(failSys(workbench, "SYS_CHANGE_REQUEST_REQUIRED"));
    }
    const change: SysChange = { ...workbench.change, status: "SANDBOX_RUNNING" };
    return writeSysWorkbench(clearSysError({ ...workbench, change }));
  }

  if (actionUid === "SYS-01-ACT-LEDGER-DECIDE") {
    // Decision Ledger state machine (word §decision_ledger_contract).
    const payload = parsePayload<{ decisionId?: string; status?: SysDecision["status"]; resolution?: string }>(nextValue, {});
    const decisionId = String(payload.decisionId ?? "");
    const target = workbench.ledger.find((row) => row.id === decisionId);
    if (!target) return writeSysWorkbench(failSys(workbench, "SYS_DECISION_UNRESOLVED"));
    const nextStatus = payload.status;
    if (!nextStatus || !["CONFIRMED", "REJECTED", "SUPERSEDED"].includes(nextStatus)) {
      return writeSysWorkbench(failSys(workbench, "SYS_DECISION_STATUS_INVALID"));
    }
    const ledger = workbench.ledger.map((row) =>
      row.id === decisionId ? { ...row, status: nextStatus, resolution: String(payload.resolution ?? row.resolution) } : row,
    );
    return writeSysWorkbench(clearSysError({ ...workbench, ledger }));
  }

  // Default: record-only projection for actions without a gate effect.
  return writeSysWorkbench(workbench);
}
