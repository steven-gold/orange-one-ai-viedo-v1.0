import { previewSysAction } from "./sysActionPreview";
import { sysContextFingerprint, type SysContext } from "./sysState";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

function json<T>(text: string | null, fallback: T): T {
  const trimmed = (text ?? "").trim();
  if (!trimmed) return fallback;
  try {
    return JSON.parse(trimmed) as T;
  } catch {
    return fallback;
  }
}

const CONTEXT: SysContext = {
  systemTruth: { version: "acpos-workbench-current", services: ["admin:SYS-01"], authorities: ["system.change.propose"], providers: ["mock"] },
  conversation: { conversationId: "CONV-T1", threadId: "T-1", branchId: "B-MAIN" },
  fingerprint: "",
};

function store(seed: Record<string, string> = {}): {
  current: (uid: string) => string | null;
  apply: (controlUid: string, actionUid: string, nextValue?: string) => Record<string, string>;
} {
  const values = new Map<string, string>(Object.entries(seed));
  const current = (uid: string) => values.get(uid) ?? null;
  const apply = (controlUid: string, actionUid: string, nextValue?: string) => {
    const patch = previewSysAction(controlUid, actionUid, current, nextValue);
    for (const [uid, value] of Object.entries(patch)) values.set(uid, value);
    return patch;
  };
  return { current, apply };
}

{
  // Fingerprint is stable for the same context and no-throw on empty inputs.
  const a = sysContextFingerprint({ ...CONTEXT, fingerprint: "" });
  const b = sysContextFingerprint({ ...CONTEXT, fingerprint: "" });
  assert(a === b && a.startsWith("CTX-"), "fingerprint is deterministic");
}

{
  // Pre-response gate: SEND without a resolved context is refused.
  const s = store();
  const refused = s.apply("SYS-01-BTN-SEND", "SYS-01-ACT-CONVERSATION-SEND", JSON.stringify({ message: "評估影響" }));
  assert(json<{ code?: string }>(refused["SYS-01-STATE-ERROR"], {}).code === "SYS-01-ERR-AI-MODE-CONTEXT", "send blocked until context resolves");
  const seeded = store({ "SYS-01-STATE-CONTEXT": JSON.stringify({ ...CONTEXT, fingerprint: sysContextFingerprint(CONTEXT) }) });
  const ok = seeded.apply("SYS-01-BTN-SEND", "SYS-01-ACT-CONVERSATION-SEND", JSON.stringify({ message: "評估影響" }));
  const turns = json<Array<{ role: string; status: string }>>(ok["SYS-01-STATE-CONVERSATION"], []);
  assert(turns.length === 1 && turns[0].role === "user" && turns[0].status === "SENT", "resolved context accepts the send");
  assert(json<{ active: boolean }>(ok["SYS-01-STATE-GENERATION"], { active: false }).active, "generation flag set for the AI reply");
}

{
  // Empty message and concurrent generation are refused.
  const s = store({ "SYS-01-STATE-CONTEXT": JSON.stringify({ ...CONTEXT, fingerprint: "CTX-1" }) });
  const empty = s.apply("SYS-01-BTN-SEND", "SYS-01-ACT-CONVERSATION-SEND", JSON.stringify({ message: "  " }));
  assert(json<{ code?: string }>(empty["SYS-01-STATE-ERROR"], {}).code === "SYS_MESSAGE_REQUIRED", "empty draft refused");
  const busy = store({
    "SYS-01-STATE-CONTEXT": JSON.stringify({ ...CONTEXT, fingerprint: "CTX-1" }),
    "SYS-01-STATE-GENERATION": JSON.stringify({ active: true, startedAt: "t" }),
  });
  const concurrent = busy.apply("SYS-01-BTN-SEND", "SYS-01-ACT-CONVERSATION-SEND", JSON.stringify({ message: "x" }));
  assert(json<{ code?: string }>(concurrent["SYS-01-STATE-ERROR"], {}).code === "SYS_GENERATION_IN_PROGRESS", "concurrent send refused");
  const stop = busy.apply("SYS-01-BTN-STOP", "SYS-01-ACT-CONVERSATION-STOP");
  const stopGen = json<{ active?: boolean; cancelRequested?: boolean }>(stop["SYS-01-STATE-GENERATION"], {});
  assert(stopGen.cancelRequested === true && stopGen.active === true, "stop requests cancellation through the shared core");
  const turns = json<Array<{ status: string }>>(stop["SYS-01-STATE-CONVERSATION"], []);
  assert(json<{ code?: string }>(stop["SYS-01-STATE-ERROR"], {}).code === undefined, "stop of an active generation is legal");
  const idleStop = s.apply("SYS-01-BTN-STOP", "SYS-01-ACT-CONVERSATION-STOP");
  assert(json<{ code?: string }>(idleStop["SYS-01-STATE-ERROR"], {}).code === "SYS_NO_GENERATION_IN_PROGRESS", "stop without generation refused");
}

{
  // Mode invariants: switching modes never touches turns/ledger/change.
  const base = {
    "SYS-01-STATE-CONTEXT": JSON.stringify({ ...CONTEXT, fingerprint: "CTX-1" }),
    "SYS-01-STATE-CONVERSATION": JSON.stringify([{ id: "T1", role: "user", text: "x", status: "SENT", at: "t" }]),
    "SYS-01-STATE-LEDGER": JSON.stringify([{ id: "D1", status: "CONFIRMED", priority: "P1", question: "q", resolution: "r", at: "t" }]),
    "SYS-01-STATE-CHANGE": JSON.stringify({ changeId: "CHG-1", goal: "g", scope: "s", status: "CANDIDATE" }),
    "SYS-01-STATE-ROUTE": JSON.stringify({ ready: 2, routes: ["mock/m1", "mock/m2"] }),
  };
  const s = store(base);
  const multi = s.apply("SYS-01-BTN-MULTI-AI", "SYS-01-ACT-AI-MODE-MULTI");
  assert(json<{ aiMode: string }>(multi["SYS-01-STATE-MODE"], { aiMode: "" }).aiMode === "MULTI_AI", "multi accepted with a resolvable route");
  assert(json<Array<unknown>>(multi["SYS-01-STATE-CONVERSATION"], []).length === 1, "mode switch preserves conversation");
  assert(json<Array<unknown>>(multi["SYS-01-STATE-LEDGER"], []).length === 1, "mode switch preserves ledger");
  assert(json<{ changeId: string }>(multi["SYS-01-STATE-CHANGE"], { changeId: "" }).changeId === "CHG-1", "mode switch preserves active change");
  const council = s.apply("SYS-01-BTN-COUNCIL-PARALLEL", "SYS-01-ACT-COUNCIL-MODE-PARALLEL");
  assert(json<{ councilMode: string }>(council["SYS-01-STATE-MODE"], { councilMode: "" }).councilMode === "PARALLEL", "council mode under MULTI accepted");
  const single = store(base);
  single.apply("SYS-01-BTN-SINGLE-AI", "SYS-01-ACT-AI-MODE-SINGLE");
  const councilBlocked = single.apply("SYS-01-BTN-COUNCIL-PARALLEL", "SYS-01-ACT-COUNCIL-MODE-PARALLEL");
  assert(json<{ code?: string }>(councilBlocked["SYS-01-STATE-ERROR"], {}).code === "SYS-01-ERR-COUNCIL-MODE", "council mode outside MULTI refused");
  const noRoute = store({
    "SYS-01-STATE-CONTEXT": JSON.stringify({ ...CONTEXT, fingerprint: "CTX-1" }),
    "SYS-01-STATE-ROUTE": JSON.stringify({ ready: 0, reason: "AI_PROVIDER_NOT_CONFIGURED" }),
  });
  const multiRefused = noRoute.apply("SYS-01-BTN-MULTI-AI", "SYS-01-ACT-AI-MODE-MULTI");
  assert(json<{ code?: string }>(multiRefused["SYS-01-STATE-ERROR"], {}).code === "SYS-01-ERR-MULTI-AI-ROUTE", "multi without a live route refused");
  assert(json<{ aiMode: string }>(multiRefused["SYS-01-STATE-MODE"], { aiMode: "MULTI_AI" }).aiMode === "SINGLE_AI", "stays SINGLE_AI with the real reason");
}

{
  // Visual-phase locks: ATTACH and NAV-OPEN stay blocked.
  const s = store({ "SYS-01-STATE-CONTEXT": JSON.stringify({ ...CONTEXT, fingerprint: "CTX-1" }) });
  const attach = s.apply("SYS-01-BTN-ATTACH", "SYS-01-ACT-CONVERSATION-ATTACH");
  assert(json<{ code?: string }>(attach["SYS-01-STATE-ERROR"], {}).code === "SYS_ATTACH_VISUAL_PHASE_BLOCKED", "attach blocked in visual phase");
  const nav = s.apply("SYS-01-BTN-NAV-OPEN", "ACT-NAV-OPEN");
  assert(json<{ code?: string }>(nav["SYS-01-STATE-ERROR"], {}).code === "SYS_NAV_OPEN_VISUAL_PHASE_BLOCKED", "nav-open blocked in visual phase");
}

{
  // Change lifecycle: candidate -> request -> sandbox; fail-closed on gaps.
  const s = store({ "SYS-01-STATE-CONTEXT": JSON.stringify({ ...CONTEXT, fingerprint: "CTX-1" }) });
  const noGoal = s.apply("SYS-01-BTN-CANDIDATE-CREATE", "ACT-CANDIDATE-CREATE", JSON.stringify({}));
  assert(json<{ code?: string }>(noGoal["SYS-01-STATE-ERROR"], {}).code === "SYS_GOAL_REQUIRED", "candidate requires a goal");
  const created = s.apply("SYS-01-BTN-CANDIDATE-CREATE", "ACT-CANDIDATE-CREATE", JSON.stringify({ goal: "升級 QA criteria v3" }));
  const change = json<{ changeId: string; status: string }>(created["SYS-01-STATE-CHANGE"], { changeId: "", status: "" });
  assert(change.status === "CANDIDATE" && change.changeId.startsWith("CHG-"), "candidate created with a change id");
  const duplicate = s.apply("SYS-01-BTN-CANDIDATE-CREATE", "ACT-CANDIDATE-CREATE", JSON.stringify({ goal: "another" }));
  assert(json<{ code?: string }>(duplicate["SYS-01-STATE-ERROR"], {}).code === "SYS_CHANGE_ALREADY_ACTIVE", "second active candidate refused");
  const earlySandbox = s.apply("SYS-01-BTN-SANDBOX-TEST", "SYS-01-ACT-SANDBOX-TEST");
  assert(json<{ code?: string }>(earlySandbox["SYS-01-STATE-ERROR"], {}).code === "SYS_CHANGE_REQUEST_REQUIRED", "sandbox before request refused");
  const requested = s.apply("SYS-01-BTN-CR-CREATE", "ACT-CR-CREATE");
  assert(json<{ status: string }>(requested["SYS-01-STATE-CHANGE"], { status: "" }).status === "REQUESTED", "CR moves candidate to requested");
  const sandboxing = s.apply("SYS-01-BTN-SANDBOX-TEST", "SYS-01-ACT-SANDBOX-TEST");
  assert(json<{ status: string }>(sandboxing["SYS-01-STATE-CHANGE"], { status: "" }).status === "SANDBOX_RUNNING", "sandbox runs on a requested change");
}

{
  // Decision Ledger state machine.
  const s = store({
    "SYS-01-STATE-LEDGER": JSON.stringify([{ id: "D1", status: "OPEN_P1", priority: "P1", question: "q", resolution: "", at: "t" }]),
  });
  const unknown = s.apply("SYS-01-BTN-AUDIT", "SYS-01-ACT-LEDGER-DECIDE", JSON.stringify({ decisionId: "D9", status: "CONFIRMED" }));
  assert(json<{ code?: string }>(unknown["SYS-01-STATE-ERROR"], {}).code === "SYS_DECISION_UNRESOLVED", "unknown decision refused");
  const bad = s.apply("SYS-01-BTN-AUDIT", "SYS-01-ACT-LEDGER-DECIDE", JSON.stringify({ decisionId: "D1", status: "OPEN_P0" }));
  assert(json<{ code?: string }>(bad["SYS-01-STATE-ERROR"], {}).code === "SYS_DECISION_STATUS_INVALID", "open status is not a human decision outcome");
  const confirmed = s.apply("SYS-01-BTN-AUDIT", "SYS-01-ACT-LEDGER-DECIDE", JSON.stringify({ decisionId: "D1", status: "CONFIRMED", resolution: "yes" }));
  const ledger = json<Array<{ id: string; status: string }>>(confirmed["SYS-01-STATE-LEDGER"], []);
  assert(ledger[0]?.status === "CONFIRMED", "decision confirmed into the ledger");
}

{
  // Ledger hard gates on candidate creation: P0/P1 convergence, conflicting
  // proposals blocked until explicitly superseded by an authorized decision.
  const base = { "SYS-01-STATE-CONTEXT": JSON.stringify({ ...CONTEXT, fingerprint: "CTX-1" }) };
  const open = store({
    ...base,
    "SYS-01-STATE-LEDGER": JSON.stringify([{ id: "D1", status: "OPEN_P0", priority: "P0", question: "q", resolution: "", at: "t" }]),
  });
  const blocked = open.apply("SYS-01-BTN-CANDIDATE-CREATE", "ACT-CANDIDATE-CREATE", JSON.stringify({ goal: "新候選變更" }));
  assert(json<{ code?: string }>(blocked["SYS-01-STATE-ERROR"], {}).code === "SYS_LEDGER_CONVERGENCE_REQUIRED", "open P0/P1 blocks design freeze");
  const superseded = open.apply(
    "SYS-01-BTN-CANDIDATE-CREATE",
    "ACT-CANDIDATE-CREATE",
    JSON.stringify({ goal: "新候選變更", supersedeDecisionIds: ["D1"] }),
  );
  assert(json<{ status: string }>(superseded["SYS-01-STATE-CHANGE"], { status: "" }).status === "CANDIDATE", "explicit supersede unblocks the candidate");
  const ledger = json<Array<{ id: string; status: string }>>(superseded["SYS-01-STATE-LEDGER"], []);
  assert(ledger[0]?.status === "SUPERSEDED", "superseded decision recorded immediately");
  const rejected = store({
    ...base,
    "SYS-01-STATE-LEDGER": JSON.stringify([{ id: "D2", status: "REJECTED", priority: "P1", question: "q", resolution: "", at: "t" }]),
  });
  const conflict = rejected.apply(
    "SYS-01-BTN-CANDIDATE-CREATE",
    "ACT-CANDIDATE-CREATE",
    JSON.stringify({ goal: "重提被拒方案", conflictingDecisionIds: ["D2"] }),
  );
  assert(json<{ code?: string }>(conflict["SYS-01-STATE-ERROR"], {}).code === "SYS_CONFLICTING_PROPOSAL", "conflicting proposal blocked");
  const conflictSuperseded = rejected.apply(
    "SYS-01-BTN-CANDIDATE-CREATE",
    "ACT-CANDIDATE-CREATE",
    JSON.stringify({ goal: "重提被拒方案", conflictingDecisionIds: ["D2"], supersedeDecisionIds: ["D2"] }),
  );
  assert(json<{ status: string }>(conflictSuperseded["SYS-01-STATE-CHANGE"], { status: "" }).status === "CANDIDATE", "conflict unblocked after explicit supersede");
  const ghost = store(base);
  const unknownSupersede = ghost.apply(
    "SYS-01-BTN-CANDIDATE-CREATE",
    "ACT-CANDIDATE-CREATE",
    JSON.stringify({ goal: "x", supersedeDecisionIds: ["D9"] }),
  );
  assert(json<{ code?: string }>(unknownSupersede["SYS-01-STATE-ERROR"], {}).code === "SYS_DECISION_UNRESOLVED", "supersede of unknown decision refused");
}
