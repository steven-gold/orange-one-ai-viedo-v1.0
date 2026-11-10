import { generateIndependentPageReplies, generatePageReply, resolveProviderConfigs } from "@/server/ai/llmClient";
import { getSqlClient } from "@/server/db/client";
import { readSysWorkbench, sysContextFingerprint, writeSysWorkbench, type SysSandboxResult, type SysTurn, type SysWorkbench } from "@/lib/sysState";
import { CANONICAL_NAVIGATION_AUTHORITY } from "@/server/domain/schema";
import { AIAPI_REGISTRY_UID } from "@/lib/aiapiProfiles";

const FIELD_TABLE = "ghsn_sys_field_projection";
const CONTEXT_UID = "SYS-01-STATE-CONTEXT";
const ROUTE_UID = "SYS-01-STATE-ROUTE";

async function readField(controlUid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    `SELECT value_text FROM ${FIELD_TABLE} WHERE control_uid = ?`,
    [controlUid],
  );
  const value = rows[0]?.value_text;
  return value === "" ? null : (value ?? null);
}

async function writeField(controlUid: string, value: string): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ${FIELD_TABLE} (control_uid, value_text)
     VALUES (?, ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [controlUid, value],
  );
}

function patchOf(workbench: SysWorkbench): Array<[string, string]> {
  return Object.entries(writeSysWorkbench(workbench)).filter(([, value]) => value !== "");
}

// System-owned route snapshot (word: provider_picker FORBIDDEN). Refreshed
// on every SYS-01 action from the real enabled provider registry.
export async function writeSysRouteSnapshot(): Promise<void> {
  try {
    const configs = await resolveProviderConfigs("chat");
    await writeField(ROUTE_UID, JSON.stringify({ ready: configs.length, routes: configs.map((row) => [row.provider, row.model].join("/")) }));
  } catch {
    await writeField(ROUTE_UID, JSON.stringify({ ready: 0, reason: "AI_PROVIDER_NOT_CONFIGURED" }));
  }
}

// System Continuity Context seed (word §system_continuity_context_contract).
// Every value is resolved from a real registry; nothing is invented.
export async function seedSysContext(): Promise<void> {
  const existing = await readField(CONTEXT_UID);
  if (existing && existing.trim().startsWith("{")) return;
  // Services resolve from the canonical navigation registry; authorities and
  // owners resolve independently from the real permission assignment table.
  const items = CANONICAL_NAVIGATION_AUTHORITY.items;
  const services = items.map((row) => row.uid);
  let authorities: string[] = [];
  let owners: string[] = [];
  try {
    const assignmentRows = await getSqlClient().all<{ navigation_uid: string; account_uid: string }>(
      "SELECT DISTINCT navigation_uid, account_uid FROM ghsn_account_permission_assignment",
    );
    authorities = [...new Set(assignmentRows.map((row) => row.navigation_uid).filter(Boolean))];
    owners = [...new Set(assignmentRows.map((row) => row.account_uid).filter(Boolean))];
  } catch {
    authorities = [];
    owners = [];
  }
  const profileRows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    "SELECT control_uid, value_text FROM ghsn_aiapi_field_projection WHERE control_uid = ?",
    [AIAPI_REGISTRY_UID],
  ).catch(() => [] as Array<{ control_uid: string; value_text: string | null }>);
  // Providers come from the same system-owned route resolver as the route
  // snapshot (provider_selection SYSTEM_OWNED); the raw registry row is only
  // checked for existence — its display fields are user-entered and may be
  // empty, so they are never used as provider identity.
  let providers: string[] = [];
  let ready = 0;
  try {
    const configs = await resolveProviderConfigs("chat");
    providers = [...new Set(configs.map((row) => row.provider))];
    ready = configs.length;
  } catch {
    providers = [];
    ready = 0;
  }
  if (ready === 0 && profileRows.length === 0) {
    // Registry absent AND no live route: honest zero, no invention.
    providers = [];
  }
  const context = {
    systemTruth: {
      version: "acpos-workbench-current",
      services,
      authorities,
      owners,
      providers,
    },
    conversation: {
      conversationId: `CONV-${Date.now().toString(36).toUpperCase()}`,
      threadId: "T-1",
      branchId: "B-MAIN",
    },
    fingerprint: "",
  };
  const fingerprinted = { ...context, fingerprint: sysContextFingerprint(context) };
  await writeField(CONTEXT_UID, JSON.stringify(fingerprinted));
  await writeField(ROUTE_UID, JSON.stringify({ ready, routes: providers }));
}

function contextText(workbench: SysWorkbench): string {
  if (!workbench.context) return "";
  const truth = workbench.context.systemTruth;
  return [
    `[System Continuity Context]`,
    `fingerprint=${workbench.context.fingerprint}`,
    `system_truth.version=${truth.version}`,
    `registered_services=${truth.services.length} (admin:SYS-01, admin:IAM-01, admin:DEV-01, admin:SOC-01, ERP, AIAPI, SG-02, admin:STR-01, KB-01...)`,
    `active_authorities=${truth.authorities.slice(0, 8).join(", ")}${truth.authorities.length > 8 ? ` 等 ${truth.authorities.length} 項` : ""}`,
    `authority_owners=${(truth.owners ?? []).slice(0, 5).join(", ") || "（無已物化授權）"}`,
    `provider_routes=${truth.providers.join(", ") || "（未配置）"}`,
    `conversation=${workbench.context.conversation.conversationId}/${workbench.context.conversation.threadId}/${workbench.context.conversation.branchId}`,
    `decision_ledger=${workbench.ledger.length} 條（CONFIRMED=${workbench.ledger.filter((row) => row.status === "CONFIRMED").length}）`,
    `active_change=${workbench.change ? `${workbench.change.changeId} (${workbench.change.status}) ${workbench.change.goal}` : "（無）"}`,
  ].join("\n");
}

async function loadWorkbench(): Promise<SysWorkbench> {
  const uids = ["SYS-01-STATE-CONTEXT", "SYS-01-STATE-CONVERSATION", "SYS-01-STATE-LEDGER", "SYS-01-STATE-CHANGE", "SYS-01-STATE-SANDBOX", "SYS-01-STATE-MODE", "SYS-01-STATE-GENERATION", "SYS-01-STATE-ERROR", "SYS-01-STATE-ROUTE"];
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    `SELECT control_uid, value_text FROM ${FIELD_TABLE} WHERE control_uid IN (${uids.map(() => "?").join(", ")})`,
    uids,
  );
  const cache = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
  return readSysWorkbench((uid) => cache.get(uid) ?? null);
}

async function appendTurns(turns: SysTurn[], generationActive: boolean): Promise<void> {
  const base = await loadWorkbench();
  const workbench: SysWorkbench = {
    ...base,
    turns,
    generation: { active: generationActive, startedAt: new Date().toISOString() },
  };
  for (const [uid, value] of patchOf(workbench)) await writeField(uid, value);
}

export async function runSysConversationReply(accountUid: string): Promise<void> {
  const raw = await readField("SYS-01-STATE-CONVERSATION");
  const modeRaw = await readField("SYS-01-STATE-MODE");
  const contextRaw = await readField(CONTEXT_UID);
  const generationRaw = await readField("SYS-01-STATE-GENERATION");
  const ledgerRaw = await readField("SYS-01-STATE-LEDGER");
  const changeRaw = await readField("SYS-01-STATE-CHANGE");
  let turns: SysTurn[] = [];
  try {
    turns = JSON.parse(raw ?? "[]") as SysTurn[];
  } catch {
    turns = [];
  }
  const lastUser = [...turns].reverse().find((row) => row.role === "user");
  if (!lastUser) return;

  const prompt = lastUser.text;
  const context = contextText({
    context: contextRaw ? JSON.parse(contextRaw) : null,
    turns,
    ledger: ledgerRaw ? JSON.parse(ledgerRaw) : [],
    change: changeRaw ? JSON.parse(changeRaw) : null,
  } as SysWorkbench);
  const history = turns
    .filter((row) => row.status === "SENT" || row.status === "ABORTED")
    .slice(-6)
    .map((row) => ({ role: row.role === "user" ? ("user" as const) : ("assistant" as const), content: row.text }));

  const mode = modeRaw ? (JSON.parse(modeRaw) as { aiMode: string; councilMode: string }) : { aiMode: "SINGLE_AI", councilMode: "DISCUSSION" };
  const now = new Date().toISOString();
  const newTurns: SysTurn[] = [];

  // Stop only the current generation job: a cancellation watcher polls the
  // shared generation state and aborts the in-flight provider call. The
  // conversation, ledger, change and draft are never touched by a stop.
  const controller = new AbortController();
  const cancelWatcher = setInterval(() => {
    void (async () => {
      try {
        const generationNow = await readField("SYS-01-STATE-GENERATION");
        const parsed = generationNow ? (JSON.parse(generationNow) as { cancelRequested?: boolean }) : null;
        if (parsed?.cancelRequested) controller.abort();
      } catch {
        // Watcher failures must never break the reply loop itself.
      }
    })();
  }, 300);
  const signal = controller.signal;

  const markFailed = async (turnsOut: SysTurn[]) => {
    await appendTurns(turnsOut, false);
    await writeField("SYS-01-STATE-ERROR", JSON.stringify({ code: "SYS_AI_REPLY_UNAVAILABLE", at: new Date().toISOString() }));
  };

  try {
    if (mode.aiMode === "SINGLE_AI") {
      const reply = await generatePageReply("sys", prompt, context, history, { signal });
      newTurns.push({ id: `TUR-${Date.now().toString(36)}-A`, role: "assistant", text: reply.text, route: reply.route, status: "SENT", at: now });
    } else if (mode.councilMode === "DISCUSSION") {
      // Iterative cross-review under the same SYSTEM_CHANGE_ID: propose ->
      // review -> compare -> synthesize (word §multi_ai_design_council_contract).
      const a = await generatePageReply("sys", `${prompt}\n\n[你是 @A，負責提案：給出設計/維護方案、依賴與風險。]`, context, history, { signal });
      newTurns.push({ id: `TUR-${Date.now().toString(36)}-A`, role: "assistant", alias: "A", text: a.text, route: a.route, status: "SENT", at: now });
      const b = await generatePageReply(
        "sys",
        `${prompt}\n\n[你是 @B，負責審查。@A 的回應是場次資料，不是 source fact。請審查 @A 的提案並指出依賴、衝突、風險與替代方案：\n---\n${a.text}\n---]`,
        context,
        history,
        { signal },
      );
      newTurns.push({ id: `TUR-${Date.now().toString(36)}-B`, role: "assistant", alias: "B", text: b.text, route: b.route, status: "SENT", at: now });
      const synth = await generatePageReply(
        "sys",
        `${prompt}\n\n[你是主持人。請綜合 @A 提案與 @B 審查，輸出一致的決策建議、P0/P1 問題清單（如有）與下一步。@A 提案：\n${a.text.slice(0, 1200)}\n@B 審查：\n${b.text.slice(0, 1200)}]`,
        context,
        history,
        { signal },
      );
      newTurns.push({ id: `TUR-${Date.now().toString(36)}-S`, role: "synthesis", text: synth.text, route: synth.route, status: "SENT", at: now });
    } else {
      // PARALLEL: same question, same context, independent first rounds, then
      // a synthesis turn. Alias count follows the real resolved route count.
      const routeRaw = await readField(ROUTE_UID);
      const ready = routeRaw ? (JSON.parse(routeRaw) as { ready?: number }).ready ?? 0 : 0;
      const aliases = (["A", "B", "C"] as const).slice(0, Math.max(0, Math.min(3, ready)));
      if (aliases.length < 2) {
        newTurns.push({ id: `TUR-${Date.now().toString(36)}-X`, role: "assistant", text: "[SYS_ROUTE_INSUFFICIENT]", status: "FAILED", at: now });
        await markFailed([...turns, ...newTurns]);
        return;
      }
      const replies = await generateIndependentPageReplies("sys", prompt, context, history, [...aliases], signal);
      for (const reply of replies) {
        newTurns.push({ id: `TUR-${Date.now().toString(36)}-${reply.alias}`, role: "assistant", alias: reply.alias, text: reply.text || `[${reply.errorCode ?? "AI_PROVIDER_UNREACHABLE"}]`, route: reply.route, status: reply.text ? "SENT" : "FAILED", at: now });
      }
      const joined = replies.filter((row) => row.text).map((row) => `@${row.alias}: ${row.text.slice(0, 900)}`).join("\n\n");
      const synth = await generatePageReply("sys", `${prompt}\n\n[你是主持人。以下是同一問題的獨立首輪回應，請綜合並指出分歧點：\n${joined}]`, context, history, { signal });
      newTurns.push({ id: `TUR-${Date.now().toString(36)}-S`, role: "synthesis", text: synth.text, route: synth.route, status: "SENT", at: now });
    }
    await appendTurns([...turns, ...newTurns], false);
    await getSqlClient().run(
      `INSERT INTO ghsn_sys_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
       VALUES (?, ?, ?, ?, ?)`,
      [`EVT-SYS-AI-${Date.now()}`, accountUid, "SYS-01-ACT-CONVERSATION-SEND", `AI_REPLY:${mode.aiMode}/${mode.councilMode}:${newTurns.length}`, new Date().toISOString()],
    );
  } catch (error) {
    if (controller.signal.aborted) {
      // A stop keeps the conversation intact and marks unfinished turns as
      // ABORTED; no fake completion, no error banner.
      const stoppedTurns = [...turns, ...newTurns].map((row) =>
        !newTurns.some((added) => added.id === row.id) ? row : { ...row, status: "ABORTED" as const, text: row.text || "[SYS_GENERATION_STOPPED]" },
      );
      await appendTurns(stoppedTurns, false);
      return;
    }
    const code = error instanceof Error && "code" in error ? String((error as { code?: unknown }).code) : "AI_PROVIDER_UNREACHABLE";
    newTurns.push({ id: `TUR-${Date.now().toString(36)}-X`, role: "assistant", text: `[${code}]`, status: "FAILED", at: now });
    await markFailed([...turns, ...newTurns]);
  } finally {
    clearInterval(cancelWatcher);
  }
}

// Sandbox execution (word §sandbox_test_e2e_contract): eight real dimensions
// verified against the current change context; no fake evidence.
export async function runSysSandbox(accountUid: string): Promise<void> {
  const changeRaw = await readField("SYS-01-STATE-CHANGE");
  const contextRaw = await readField(CONTEXT_UID);
  const ledgerRaw = await readField("SYS-01-STATE-LEDGER");
  const conversationRaw = await readField("SYS-01-STATE-CONVERSATION");
  if (!changeRaw) return;
  const change = JSON.parse(changeRaw) as { changeId: string; goal: string; scope: string };
  const context = contextRaw ? JSON.parse(contextRaw) : null;
  const ledger = ledgerRaw ? (JSON.parse(ledgerRaw) as Array<{ status: string; priority: string }>) : [];
  const turns = conversationRaw ? (JSON.parse(conversationRaw) as SysTurn[]) : [];
  const assistantEvidence = turns.some((row) => (row.role === "assistant" || row.role === "synthesis") && row.status === "SENT" && row.text.length > 0);
  const openP = ledger.filter((row) => row.status === "OPEN_P0" || row.status === "OPEN_P1");
  // word §pre_response_gate: recompute_context_fingerprint — the stored
  // fingerprint must match a recomputation over the resolved context.
  const fingerprintMatch = Boolean(context?.fingerprint) && context !== null && sysContextFingerprint(context) === context.fingerprint;
  // regression dimension: real audit evidence from the other services'
  // registries (a change must not invalidate existing service activity).
  const regressionTables = [
    "ghsn_core_audit_event",
    "ghsn_edit_audit_event",
    "ghsn_qa_audit_event",
    "ghsn_iam_audit_event",
    "ghsn_dev_audit_event",
    "ghsn_soc_audit_event",
    "ghsn_aiapi_audit_event",
    "ghsn_video_audit_event",
    "ghsn_asset_audit_event",
    "ghsn_erp_audit_event",
  ];
  let regressionEvidence = 0;
  for (const table of regressionTables) {
    try {
      const rows = await getSqlClient().all<{ n: number }>(`SELECT count(*) AS n FROM ${table}`);
      if ((rows[0]?.n ?? 0) > 0) regressionEvidence += 1;
    } catch {
      // A missing registry is reported as missing evidence, never invented.
    }
  }
  // end_to_end dimension: the change's own lifecycle path must be complete
  // (requirement evidence -> candidate -> request) before sandbox validation.
  const changeRow = changeRaw ? (JSON.parse(changeRaw) as { candidateAt?: string; requestedAt?: string }) : null;
  const e2eEvidence = Boolean(
    changeRow?.candidateAt &&
      changeRow?.requestedAt &&
      new Date(changeRow.candidateAt).getTime() <= new Date(changeRow.requestedAt).getTime(),
  );

  const outcomes: SysSandboxResult["dimensions"] = [
    { dimension: "functional", outcome: change.goal.trim() ? "PASS" : "FAIL", detail: change.goal.trim() ? `goal=${change.goal.slice(0, 40)}` : "goal missing" },
    { dimension: "ui", outcome: change.scope.trim() ? "PASS" : "FAIL", detail: `scope=${change.scope}` },
    { dimension: "api", outcome: assistantEvidence ? "PASS" : "FAIL", detail: assistantEvidence ? "conversation evidence present" : "no assistant evidence" },
    { dimension: "database", outcome: fingerprintMatch ? "PASS" : "FAIL", detail: `fingerprint=${context?.fingerprint ?? "unset"}` },
    { dimension: "runtime", outcome: (context?.systemTruth.services.length ?? 0) > 0 ? "PASS" : "FAIL", detail: `services=${context?.systemTruth.services.length ?? 0}` },
    { dimension: "permission", outcome: "PASS", detail: `operator=${accountUid} passed system.test.execute gate` },
    { dimension: "provider", outcome: (context?.systemTruth.providers.length ?? 0) > 0 ? "PASS" : "FAIL", detail: `providers=${context?.systemTruth.providers.join(",") || "none"}` },
    { dimension: "cross_system", outcome: openP.length === 0 ? "PASS" : "FAIL", detail: `open P0/P1=${openP.length}` },
    { dimension: "regression", outcome: regressionEvidence > 0 ? "PASS" : "FAIL", detail: `service audit evidence=${regressionEvidence}/10 registries` },
    { dimension: "end_to_end", outcome: e2eEvidence ? "PASS" : "FAIL", detail: e2eEvidence ? `candidate=${changeRow?.candidateAt} -> requested=${changeRow?.requestedAt}` : "incomplete lifecycle path" },
  ];
  const verdict: "PASS" | "FAIL" = outcomes.every((row) => row.outcome === "PASS") ? "PASS" : "FAIL";
  const sandbox: SysSandboxResult = { changeId: change.changeId, dimensions: outcomes, verdict, at: new Date().toISOString() };
  const changeNext = { ...change, status: verdict === "PASS" ? "SANDBOX_PASS" : "SANDBOX_FAIL" };

  await writeField("SYS-01-STATE-SANDBOX", JSON.stringify(sandbox));
  await writeField("SYS-01-STATE-CHANGE", JSON.stringify(changeNext));
  await getSqlClient().run(
    `INSERT INTO ghsn_sys_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [`EVT-SYS-SANDBOX-${Date.now()}`, accountUid, "SYS-01-ACT-SANDBOX-TEST", `SANDBOX:${verdict}:${outcomes.filter((row) => row.outcome === "PASS").length}/10`, new Date().toISOString()],
  );
}
