import {
  generateIndependentPageReplies,
  generatePageReply,
  resolveProviderConfigs,
  GenerationCancelled,
  AiProviderError,
  type ChatMessage,
} from "../ai/llmClient";
import { getSqlClient } from "../db/client";
import {
  STR_CONVERSATION_PERMISSION,
  STR_COMPARE_PERMISSION,
  STR_REVIEW_PERMISSION,
  STR_ADOPT_PERMISSION,
  STR_PERMISSION_SCOPES,
  STR_STATE_ERROR_UID,
} from "../domain/str";

// ACPOS STR-01 FINAL_LOCKED_ENCODING_PROVIDER_BOUND · actions (10) / gates (11)
// / errors (9) / stages (6). The conversation, topic, candidate and context
// state lives in projection-side STATE uids outside the 57-control denominator
// (same precedent as SYS-01-STATE-* / QA-01-STATE-ERROR). Every write is
// append-only; revisions create new versions (hard_locks §immutable history).

const TABLE = "ghsn_str_field_projection";
const TOPIC_UID = "STR-01-STATE-TOPIC";
const TOPICS_UID = "STR-01-STATE-TOPICS";
const CONVERSATION_UID = "STR-01-STATE-CONVERSATION";
const MODE_UID = "STR-01-STATE-MODE";
const CANDIDATES_UID = "STR-01-STATE-CANDIDATES";
const CONTEXT_UID = "STR-01-STATE-CONTEXT";
const FILTER_UID = "STR-01-STATE-FILTER";
const GENERATION_UID = "STR-01-STATE-GENERATION";

const STAGES = [
  "STR-01-STAGE-01-CONTEXT",
  "STR-01-STAGE-02-CONVERSE",
  "STR-01-STAGE-03-ANALYZE",
  "STR-01-STAGE-04-OUTPUT",
  "STR-01-STAGE-05-HUMAN",
  "STR-01-STAGE-06-FEEDBACK",
] as const;

interface StrTurn {
  id: string;
  role: "user" | "assistant" | "synthesis";
  alias?: string;
  text: string;
  route?: string;
  status: "SENT" | "FAILED" | "ABORTED";
  at: string;
}

interface StrTopic {
  topicId: string;
  title: string;
  scope: string;
  horizon: string;
  objective: string;
  selectedAt: string;
}

interface StrCandidate {
  candidateId: string;
  version: number;
  title: string;
  outputType: string;
  summary: string;
  basis: string;
  risk: string;
  uncertainty: string;
  evidence: string;
  state: "CANDIDATE" | "REVIEW_REQUIRED" | "ADOPTED";
  at: string;
}

async function readField(controlUid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    `SELECT value_text FROM ${TABLE} WHERE control_uid = ?`,
    [controlUid],
  );
  const value = rows[0]?.value_text;
  return value === "" ? null : (value ?? null);
}

async function writeField(controlUid: string, value: string | null): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ${TABLE} (control_uid, value_text) VALUES (?, ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [controlUid, value],
  );
}

async function hasScope(accountUid: string | undefined, scope: string): Promise<boolean> {
  if (!accountUid) return false;
  await seedStrScope();
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_str_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, scope],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

let scopeSeeded = false;
async function seedStrScope(): Promise<void> {
  if (scopeSeeded) return;
  const { seedScope } = await import("../db/seed");
  await seedScope("str");
  scopeSeeded = true;
}

function err(code: string, detail: string, recovery: string) {
  return { code, detail, recovery, at: new Date().toISOString() };
}

async function writeError(error: { code: string; detail: string; recovery: string; at: string }): Promise<void> {
  await writeField(STR_STATE_ERROR_UID, JSON.stringify(error));
}

async function parseJson<T>(uid: string, fallback: T): Promise<T> {
  const raw = await readField(uid);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function turnsOfThread(thread: string, store: Array<{ topicId: string; turns: StrTurn[] }>): StrTurn[] {
  return store.find((row) => row.topicId === thread)?.turns ?? [];
}

async function writeThreadTurns(thread: string, turns: StrTurn[], store: Array<{ topicId: string; turns: StrTurn[] }>): Promise<void> {
  const next = store.filter((row) => row.topicId !== thread);
  next.push({ topicId: thread, turns });
  await writeField(CONVERSATION_UID, JSON.stringify(next));
}

function historyOf(turns: StrTurn[], prompt: string): ChatMessage[] {
  return turns
    .filter((row) => row.status === "SENT" && row.text.trim().length > 0 && row.text.trim() !== prompt.trim())
    .slice(-6)
    .map((row) => ({ role: row.role === "user" ? ("user" as const) : ("assistant" as const), content: row.text }));
}

// Strategic context resolved from real governed projections only; missing
// modules display — (data_and_truth_rules: real projection only).
async function buildContextBundle(topic: StrTopic | null): Promise<Record<string, string>> {
  const cross: Record<string, string | null> = {};
  const sources: Array<[string, string, string]> = [
    ["core", "ghsn_core_field_projection", "CORE-01-FLD-DOWNSTREAM-EDIT"],
    ["edit_stage", "ghsn_edit_field_projection", "EDIT-01-LBL-STAGE-SCORE"],
    ["video_score", "ghsn_video_field_projection", "VIDEO-01-FLD-OVERALL-SCORE"],
    ["qa_baseline", "ghsn_qa_field_projection", "QA-01-FLD-CRITERIA-VERSION"],
  ];
  for (const [key, table, uid] of sources) {
    try {
      const rows = await getSqlClient().all<{ value_text: string | null }>(
        `SELECT value_text FROM ${table} WHERE control_uid = ?`,
        [uid],
      );
      cross[key] = rows[0]?.value_text === "" ? null : (rows[0]?.value_text ?? null);
    } catch {
      cross[key] = null;
    }
  }
  const bundle: Record<string, string> = {
    topic: topic ? `${topic.topicId} · ${topic.title}` : "—",
    scope: topic?.scope ?? "—",
    horizon: topic?.horizon ?? "—",
    priority: "P0 instruction; P1 confirmed decisions; P2 internal data; P3 historical; P4 external",
    core_receipt: cross.core ?? "—",
    edit_stage_score: cross.edit_stage ?? "—",
    video_overall_score: cross.video_score ?? "—",
    qa_baseline: cross.qa_baseline ?? "—",
  };
  return bundle;
}

function contextText(bundle: Record<string, string>): string {
  return Object.entries(bundle)
    .map(([key, value]) => `${key}: ${value}`)
    .join("\n");
}

const ANALYSIS_PROMPT = [
  "你是戰略中心分析器。依據使用者訊息與策略脈絡產出結構化分析。",
  "只輸出一個 JSON 物件，不得輸出其他文字，欄位如下：",
  '{"assistant_summary":"繁中摘要","open_questions":["..."],"meeting_record":"討論記錄","analysis_basis":"...","assumptions":["..."],"opportunities":["..."],"risks":["..."],"uncertainties":["..."],"pattern_baseline_forecast":"...","recommendation_reason":"...","evidence_refs":["..."],',
  '"outputs":[{"type":"STRATEGY_RECOMMENDATION|STRATEGY_ALERT|RESOURCE_PROPOSAL|DECISION_BRIEF","title":"...","summary":"...","risk":"...","uncertainty":"...","evidence":"..."}]}',
  "缺漏值用「—」，禁止編造財務、資源、KPI 或執行數據。",
].join("\n");

interface StrAnalysis {
  assistant_summary?: string;
  open_questions?: string[];
  meeting_record?: string;
  analysis_basis?: string;
  assumptions?: string[];
  opportunities?: string[];
  risks?: string[];
  uncertainties?: string[];
  pattern_baseline_forecast?: string;
  recommendation_reason?: string;
  evidence_refs?: string[];
  outputs?: Array<{ type?: string; title?: string; summary?: string; risk?: string; uncertainty?: string; evidence?: string }>;
}

function parseAnalysis(body: string): StrAnalysis | null {
  const start = body.indexOf("{");
  const end = body.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    const parsed = JSON.parse(body.slice(start, end + 1)) as StrAnalysis;
    return typeof parsed === "object" && parsed !== null ? parsed : null;
  } catch {
    return null;
  }
}

const OUTPUT_TYPE_BY_INDEX = ["STRATEGY_RECOMMENDATION", "STRATEGY_ALERT", "RESOURCE_PROPOSAL", "DECISION_BRIEF"] as const;
const OUTPUT_CARD_UIDS = ["STR-01-CARD-RECOMMENDATION", "STR-01-CARD-ALERT", "STR-01-CARD-RESOURCE", "STR-01-CARD-BRIEF"] as const;

function textList(value: string[] | undefined, fallback: string): string {
  return value && value.length > 0 ? value.join("；") : fallback;
}

async function writeStage(): Promise<void> {
  const [topicRaw, turnsRaw, basis, candidateRaw, adopted, feedback] = await Promise.all([
    readField(TOPIC_UID),
    readField(CONVERSATION_UID),
    readField("STR-01-FLD-BASIS"),
    readField(CANDIDATES_UID),
    readField("STR-01-FLD-DECISION-RESULT"),
    readField("STR-01-FLD-ACTUAL"),
  ]);
  let stage: (typeof STAGES)[number] = "STR-01-STAGE-01-CONTEXT";
  if (topicRaw) stage = "STR-01-STAGE-01-CONTEXT";
  const turns = turnsRaw ? (JSON.parse(turnsRaw) as Array<{ topicId: string; turns: StrTurn[] }>) : [];
  if (turns.some((row) => row.turns.length > 0)) stage = "STR-01-STAGE-02-CONVERSE";
  if (basis) stage = "STR-01-STAGE-03-ANALYZE";
  if (candidateRaw && (JSON.parse(candidateRaw) as StrCandidate[]).length > 0) stage = "STR-01-STAGE-04-OUTPUT";
  if (adopted) stage = "STR-01-STAGE-05-HUMAN";
  if (feedback) stage = "STR-01-STAGE-06-FEEDBACK";
  await writeField("STR-01-FLD-STATE", stage);
}

async function refreshTopicPanels(): Promise<void> {
  const topics = await parseJson<Array<StrTopic & { turns?: number }>>(TOPICS_UID, []);
  const filter = ((await readField(FILTER_UID)) ?? "").trim().toLowerCase();
  const visible = topics.filter((topic) => !filter || topic.title.toLowerCase().includes(filter));
  await writeField(
    "STR-01-LST-TOPICS",
    visible.map((topic) => `${topic.topicId} · ${topic.title}`).join("\n") || null,
  );
}

// GATE-MEMORY: only real authorized sources render. Pattern/case history
// comes from the append-only candidate ledger; baselines come from governed
// cross-module projections. Sources without registered data stay —.
async function refreshMemoryFields(): Promise<void> {
  const candidates = await parseJson<StrCandidate[]>(CANDIDATES_UID, []);
  const patternLines = candidates
    .filter((row) => row.state === "ADOPTED")
    .map((row) => `${row.candidateId} · v${row.version} · ${row.title} · ${row.summary} · ADOPTED`);
  const currentPattern = await readField("STR-01-FLD-PATTERN");
  if (currentPattern) patternLines.push(`ANALYSIS · ${currentPattern}`);
  await writeField("STR-01-LST-PATTERNS", patternLines.join("\n") || null);
  const cross = await buildContextBundle(null);
  const baselineLines = Object.entries(cross)
    .filter(([key, value]) => key !== "topic" && key !== "scope" && key !== "horizon" && key !== "priority" && value !== "—")
    .map(([key, value]) => `BASELINE · ${key}: ${value}`);
  await writeField("STR-01-LST-BASELINES", baselineLines.join("\n") || null);
  await writeField("STR-01-LST-EXPERIMENTS", null);
  await writeField("STR-01-LST-LEARNING", null);
}

// GATE-FEEDBACK: read-only. Expected comes from the adopted ledger entry;
// Actual lands only when the owner module writes a real RESULT ref. Missing
// execution data stays — (hard lock: AI must not invent performance).
async function refreshFeedbackFields(): Promise<void> {
  const result = await readField("STR-01-FLD-DECISION-RESULT");
  if (result !== "ADOPTED_CONTEXT") {
    await writeField("STR-01-FLD-EXPECTED", null);
    await writeField("STR-01-FLD-ACTUAL", null);
    await writeField("STR-01-FLD-DIFFERENCE", null);
    await writeField("STR-01-FLD-KPI", null);
    return;
  }
  const candidates = await parseJson<StrCandidate[]>(CANDIDATES_UID, []);
  const adopted = [...candidates].reverse().find((row) => row.state === "ADOPTED");
  await writeField("STR-01-FLD-EXPECTED", adopted ? `${adopted.candidateId} · v${adopted.version} · ${adopted.title} · ${adopted.summary}` : null);
  const execution = (await readField("STR-01-FLD-EXECUTION-STATE")) ?? "";
  const resultRef = execution.split("RESULT:")[1]?.trim();
  await writeField("STR-01-FLD-ACTUAL", resultRef ? `RESULT: ${resultRef}` : null);
  await writeField("STR-01-FLD-DIFFERENCE", null);
  await writeField("STR-01-FLD-KPI", null);
}

async function refreshTopicFields(topic: StrTopic | null, bundle: Record<string, string>): Promise<void> {
  await writeField("STR-01-FLD-TOPIC", topic ? `${topic.topicId} · ${topic.title}` : null);
  await writeField("STR-01-FLD-SCOPE", topic?.scope ?? null);
  await writeField("STR-01-FLD-HORIZON", topic?.horizon ?? null);
  await writeField("STR-01-FLD-CONTEXT-PRIORITY", bundle.priority);
  await writeField("STR-01-FLD-CONTEXT-SOURCE", `core/edit/video/qa governed projections`);
  await writeField("STR-01-FLD-CONTEXT-TIME", new Date().toISOString().slice(0, 19).replace("T", " "));
  await writeField("STR-01-FLD-CONTEXT-CONFIDENCE", "governed projection · real data only");
  await writeField(CONTEXT_UID, JSON.stringify(bundle));
}

async function clearAnalysisPanel(): Promise<void> {
  for (const uid of [
    "STR-01-FLD-BASIS",
    "STR-01-FLD-ASSUMPTIONS",
    "STR-01-FLD-OPPORTUNITIES",
    "STR-01-FLD-RISKS",
    "STR-01-FLD-UNCERTAINTY",
    "STR-01-FLD-PATTERN",
    "STR-01-FLD-ASSISTANT-SUMMARY",
    "STR-01-FLD-OPEN-QUESTIONS",
    "STR-01-FLD-MEETING-RECORD",
    "STR-01-CARD-RECOMMENDATION",
    "STR-01-CARD-ALERT",
    "STR-01-CARD-RESOURCE",
    "STR-01-CARD-BRIEF",
  ]) {
    await writeField(uid, null);
  }
}

function routeBrand(route: string | undefined): string | null {
  const label = (route ?? "").trim();
  return label === "" ? null : label;
}

export async function applyStrWorkbenchAction(
  accountUid: string | undefined,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
  signal?: AbortSignal,
): Promise<void> {
  switch (actionUid) {
    case "STR-01-ACT-NOOP":
      return;

    case "STR-01-ACT-FILTER": {
      // GATE-PAGE: UI_ONLY topic filter (word §input_behavior).
      await writeField(FILTER_UID, (nextValue ?? "").trim() || null);
      await refreshTopicPanels();
      return;
    }

    case "STR-01-ACT-MODE": {
      // GATE-TOPIC: mode is UI_LOCAL, provider routing stays system-owned.
      const next = (nextValue ?? "").trim().toUpperCase() === "MULTI" ? "MULTI" : "SINGLE";
      await writeField(MODE_UID, next);
      await writeField("STR-01-TGL-MODE", next);
      return;
    }

    case "STR-01-ACT-TOPIC-SELECT": {
      // GATE-PAGE: exact strategy topic selection; stale dependent state is
      // cleared (success_contract). A new title registers a new topic.
      const title = (nextValue ?? "").trim();
      if (!title) {
        await writeError(err("STR-01-ERR-CONTEXT-001", "Strategy topic title missing", "Select or register an exact topic"));
        return;
      }
      const topics = await parseJson<StrTopic[]>(TOPICS_UID, []);
      let topic = topics.find((row) => row.title === title || row.topicId === title);
      if (!topic) {
        topic = {
          topicId: `STR-TOPIC-${Date.now().toString(36).toUpperCase()}`,
          title,
          scope: "enterprise strategy",
          horizon: "—",
          objective: title,
          selectedAt: new Date().toISOString(),
        };
        topics.push(topic);
        await writeField(TOPICS_UID, JSON.stringify(topics));
      }
      await writeField(TOPIC_UID, JSON.stringify(topic));
      const bundle = await buildContextBundle(topic);
      await refreshTopicFields(topic, bundle);
      await refreshTopicPanels();
      await refreshMemoryFields();
      await refreshFeedbackFields();
      await writeField(STR_STATE_ERROR_UID, null);
      const turns = turnsOfThread(topic.topicId, await parseJson<Array<{ topicId: string; turns: StrTurn[] }>>(CONVERSATION_UID, []));
      await writeField(
        "STR-01-VIEW-CONVERSATION",
        JSON.stringify({ topicId: topic.topicId, turns }),
      );
      await clearAnalysisPanel();
      await writeStage();
      return;
    }

    case "STR-01-ACT-SEND": {
      // GATE-MESSAGE: conversation.write + active topic + non-empty message
      // (word §gates). Each failure preserves topic/context and surfaces the
      // registered error.
      if (!(await hasScope(accountUid, STR_CONVERSATION_PERMISSION))) {
        await writeError(err("STR-01-ERR-PERM-001", `${STR_CONVERSATION_PERMISSION} required`, "Hide/disable according to actual server result"));
        return;
      }
      const topicRaw = await readField(TOPIC_UID);
      if (!topicRaw) {
        await writeError(err("STR-01-ERR-CONVERSATION-001", "No active strategy topic", "Select a topic before sending"));
        return;
      }
      const message = (nextValue ?? "").trim();
      if (!message) {
        await writeError(err("STR-01-ERR-CONVERSATION-001", "Message is empty", "Enter a strategy question or instruction"));
        return;
      }
      const topic = JSON.parse(topicRaw) as StrTopic;
      const store = await parseJson<Array<{ topicId: string; turns: StrTurn[] }>>(CONVERSATION_UID, []);
      const turns = turnsOfThread(topic.topicId, store);
      const now = new Date().toISOString();
      const userTurn: StrTurn = { id: `TUR-${Date.now().toString(36)}-U`, role: "user", text: message, status: "SENT", at: now };
      const history = historyOf(turns, message);
      const bundle = await buildContextBundle(topic);
      const context = contextText(bundle);
      const mode = ((await readField(MODE_UID)) ?? "SINGLE") === "MULTI" ? "MULTI" : "SINGLE";
      const newTurns: StrTurn[] = [userTurn];
      let analysis: StrAnalysis | null = null;
      let routeForBrand: string | null = null;
      try {
        if (mode === "SINGLE") {
          const reply = await generatePageReply(
            "str",
            `${message}\n\n${ANALYSIS_PROMPT}`,
            context,
            history,
            { signal },
          );
          routeForBrand = routeBrand(reply.route);
          newTurns.push({ id: `TUR-${Date.now().toString(36)}-A`, role: "assistant", text: reply.text, route: reply.route, status: "SENT", at: now });
          analysis = parseAnalysis(reply.text);
        } else {
          const configs = await resolveProviderConfigs("chat").catch(() => []);
          const aliases = (["A", "B", "C"] as const).slice(0, Math.max(2, Math.min(3, configs.length)));
          const replies = await generateIndependentPageReplies("str", `${message}\n\n${ANALYSIS_PROMPT}`, context, history, [...aliases], signal);
          for (const reply of replies) {
            newTurns.push({
              id: `TUR-${Date.now().toString(36)}-${reply.alias}`,
              role: "assistant",
              alias: reply.alias,
              text: reply.text || `[${reply.errorCode ?? "AI_PROVIDER_UNREACHABLE"}]`,
              route: reply.route,
              status: reply.text ? "SENT" : "FAILED",
              at: now,
            });
          }
          const good = replies.filter((row) => row.text);
          routeForBrand = routeBrand(good[0]?.route);
          if (good.length > 0) {
            const joined = good.map((row) => `@${row.alias}: ${row.text.slice(0, 1200)}`).join("\n\n");
            const synth = await generatePageReply(
              "str",
              `${message}\n\n[你是主持人。以下是同一策略問題的獨立觀點，請綜合為 Assistant Summary，指出分歧與風險：\n${joined}]\n\n${ANALYSIS_PROMPT}`,
              context,
              history,
              { signal },
            );
            routeForBrand = routeForBrand ?? routeBrand(synth.route);
            newTurns.push({ id: `TUR-${Date.now().toString(36)}-S`, role: "synthesis", text: synth.text, route: synth.route, status: "SENT", at: now });
            analysis = parseAnalysis(synth.text);
          }
        }
      } catch (error) {
        if (signal?.aborted || error instanceof GenerationCancelled) {
          // Stop keeps the conversation intact; unfinished work is ABORTED,
          // no fake completion (word §STR-01-BTN-STOP success contract).
          const partial = error instanceof GenerationCancelled ? error.partial : "";
          if (partial.trim()) newTurns.push({ id: `TUR-${Date.now().toString(36)}-X`, role: "assistant", text: partial, status: "ABORTED", at: now });
          await writeThreadTurns(topic.topicId, [...turns, ...newTurns], store);
          await writeField("STR-01-VIEW-CONVERSATION", JSON.stringify({ topicId: topic.topicId, turns: [...turns, ...newTurns] }));
          await writeField(GENERATION_UID, JSON.stringify({ cancelRequested: false }));
          return;
        }
        const code = error instanceof AiProviderError ? error.code : "AI_PROVIDER_UNREACHABLE";
        newTurns.push({ id: `TUR-${Date.now().toString(36)}-X`, role: "assistant", text: `[${code}]`, status: "FAILED", at: now });
        await writeThreadTurns(topic.topicId, [...turns, ...newTurns], store);
        await writeField("STR-01-VIEW-CONVERSATION", JSON.stringify({ topicId: topic.topicId, turns: [...turns, ...newTurns] }));
        await writeField("STR-01-FLD-DISABLED", `[${code}] provider unavailable for this request`);
        await writeError(err("STR-01-ERR-CONVERSATION-001", `AI provider unavailable: ${code}`, "Preserve topic/context; show registered error/retry eligibility"));
        return;
      }
      const allTurns = [...turns, ...newTurns];
      await writeThreadTurns(topic.topicId, allTurns, store);
      await writeField("STR-01-VIEW-CONVERSATION", JSON.stringify({ topicId: topic.topicId, turns: allTurns }));
      if (analysis) {
        await writeField("STR-01-FLD-ASSISTANT-SUMMARY", analysis.assistant_summary?.trim() || null);
        await writeField("STR-01-FLD-OPEN-QUESTIONS", textList(analysis.open_questions, "—"));
        await writeField("STR-01-FLD-MEETING-RECORD", analysis.meeting_record?.trim() || null);
        await writeField("STR-01-FLD-BASIS", analysis.analysis_basis?.trim() || null);
        await writeField("STR-01-FLD-ASSUMPTIONS", textList(analysis.assumptions, "—"));
        await writeField("STR-01-FLD-OPPORTUNITIES", textList(analysis.opportunities, "—"));
        await writeField("STR-01-FLD-RISKS", textList(analysis.risks, "—"));
        await writeField("STR-01-FLD-UNCERTAINTY", textList(analysis.uncertainties, "—"));
        await writeField("STR-01-FLD-PATTERN", analysis.pattern_baseline_forecast?.trim() || null);
        const outputs = analysis.outputs ?? [];
        for (let index = 0; index < OUTPUT_CARD_UIDS.length; index += 1) {
          const uid = OUTPUT_CARD_UIDS[index];
          const row = outputs.find((item) => (item.type ?? "").toUpperCase() === OUTPUT_TYPE_BY_INDEX[index]) ?? outputs[index];
          if (!row) {
            await writeField(uid, null);
            continue;
          }
          await writeField(
            uid,
            JSON.stringify({
              type: OUTPUT_TYPE_BY_INDEX[index],
              title: row.title ?? "—",
              summary: row.summary ?? "—",
              risk: row.risk ?? "—",
              uncertainty: row.uncertainty ?? "—",
              evidence: row.evidence ?? "—",
            }),
          );
        }
        const recommendation = outputs.find((item) => (item.type ?? "").toUpperCase() === "STRATEGY_RECOMMENDATION") ?? outputs[0];
        if (recommendation) {
          const candidates = await parseJson<StrCandidate[]>(CANDIDATES_UID, []);
          const prior = candidates.filter((row) => row.title === (recommendation.title ?? "")).length;
          candidates.push({
            candidateId: `STR-CAND-${Date.now().toString(36).toUpperCase()}`,
            version: prior + 1,
            title: recommendation.title ?? "—",
            outputType: "STRATEGY_RECOMMENDATION",
            summary: recommendation.summary ?? "—",
            basis: analysis.analysis_basis?.trim() || "—",
            risk: recommendation.risk ?? "—",
            uncertainty: recommendation.uncertainty ?? "—",
            evidence: (analysis.evidence_refs ?? []).join("；") || recommendation.evidence || "—",
            state: "CANDIDATE",
            at: now,
          });
          await writeField(CANDIDATES_UID, JSON.stringify(candidates));
          await writeField("STR-01-FLD-CANDIDATE-REF", `${candidates[candidates.length - 1].candidateId} · v${candidates[candidates.length - 1].version} · CANDIDATE`);
          await writeField("STR-01-FLD-REVIEW-STATE", "CANDIDATE");
        }
      } else {
        // Unparseable output stays honest: raw text is the meeting record and
        // the analysis panel shows the limitation (strategy_analysis_contract).
        const raw = newTurns.filter((row) => row.role !== "user").map((row) => row.text).join("\n\n");
        await writeField("STR-01-FLD-MEETING-RECORD", raw.slice(0, 4000) || null);
        await writeField("STR-01-FLD-ASSISTANT-SUMMARY", "結構化分析未解析，僅保留原始回覆於討論記錄");
      }
      await writeField("STR-01-FLD-PROVIDER-BRAND", routeForBrand);
      await writeField("STR-01-FLD-CORRELATION", `${topic.topicId} · ${userTurn.id}`);
      await writeField("STR-01-FLD-OWNER-BOUNDARY", "AI proposal only · budget/workflow/governance/production in owner modules");
      await writeField(GENERATION_UID, JSON.stringify({ cancelRequested: false }));
      await writeField(STR_STATE_ERROR_UID, null);
      await writeField("STR-01-FLD-DISABLED", null);
      await refreshMemoryFields();
      await writeStage();
      return;
    }

    case "STR-01-ACT-STOP": {
      // GATE-MESSAGE: flags the cancel watcher; the in-flight provider call
      // aborts on its next poll. Conversation/topic/context untouched.
      await writeField(GENERATION_UID, JSON.stringify({ cancelRequested: true, at: new Date().toISOString() }));
      return;
    }

    case "STR-01-ACT-COMPARE": {
      // GATE-COMPARE: at least 2 exact candidate refs (word §gates).
      if (!(await hasScope(accountUid, STR_COMPARE_PERMISSION))) {
        await writeError(err("STR-01-ERR-PERM-001", `${STR_COMPARE_PERMISSION} required`, "Hide/disable according to actual server result"));
        return;
      }
      const candidates = await parseJson<StrCandidate[]>(CANDIDATES_UID, []);
      if (candidates.length < 2) {
        await writeError(err("STR-01-ERR-CANDIDATE-001", `Only ${candidates.length} candidate ref(s) available`, "BLOCK compare until at least 2 exact refs exist"));
        return;
      }
      const rows = candidates.map(
        (row) => `${row.candidateId} · v${row.version} · ${row.title} · risk:${row.risk} · uncertainty:${row.uncertainty} · ${row.state}`,
      );
      await writeField("STR-01-TBL-COMPARE", rows.join("\n"));
      await writeField(STR_STATE_ERROR_UID, null);
      await writeStage();
      return;
    }

    case "STR-01-ACT-REVIEW": {
      // GATE-REVIEW: CANDIDATE state + analysis basis/risk/uncertainty/evidence
      // + strategy.decision.propose (word §gates).
      if (!(await hasScope(accountUid, STR_REVIEW_PERMISSION))) {
        await writeError(err("STR-01-ERR-PERM-001", `${STR_REVIEW_PERMISSION} required`, "Hide/disable according to actual server result"));
        return;
      }
      const candidates = await parseJson<StrCandidate[]>(CANDIDATES_UID, []);
      const candidate = [...candidates].reverse().find((row) => row.state === "CANDIDATE");
      if (!candidate) {
        await writeError(err("STR-01-ERR-REVIEW-001", "No CANDIDATE strategy candidate available", "BLOCK submit review; preserve candidate"));
        return;
      }
      if ([candidate.basis, candidate.risk, candidate.uncertainty, candidate.evidence].some((value) => !value || value === "—")) {
        await writeError(err("STR-01-ERR-REVIEW-001", `Candidate ${candidate.candidateId} lacks analysis basis/risk/uncertainty/evidence`, "BLOCK submit review; preserve candidate"));
        return;
      }
      candidate.state = "REVIEW_REQUIRED";
      await writeField(CANDIDATES_UID, JSON.stringify(candidates));
      await writeField("STR-01-FLD-CANDIDATE-REF", `${candidate.candidateId} · v${candidate.version} · REVIEW_REQUIRED`);
      await writeField("STR-01-FLD-REVIEW-STATE", "REVIEW_REQUIRED");
      await writeField(STR_STATE_ERROR_UID, null);
      await writeStage();
      return;
    }

    case "STR-01-ACT-ADOPT": {
      // GATE-ADOPT: REVIEW_REQUIRED + human decision/reason + evidence +
      // strategy.decision.approve. Adoption is governed context only; owner
      // modules execute later (word §decision_ledger_contract).
      if (!(await hasScope(accountUid, STR_ADOPT_PERMISSION))) {
        await writeError(err("STR-01-ERR-PERM-001", `${STR_ADOPT_PERMISSION} required`, "Hide/disable according to actual server result"));
        return;
      }
      const reason = (nextValue ?? "").trim();
      const candidates = await parseJson<StrCandidate[]>(CANDIDATES_UID, []);
      const candidate = [...candidates].reverse().find((row) => row.state === "REVIEW_REQUIRED");
      if (!candidate) {
        await writeError(err("STR-01-ERR-ADOPT-001", "No REVIEW_REQUIRED candidate available", "BLOCK adoption; no auto-approval"));
        return;
      }
      if (!reason) {
        await writeError(err("STR-01-ERR-ADOPT-001", "Human decision reason missing", "BLOCK adoption; provide the review decision reason"));
        return;
      }
      candidate.state = "ADOPTED";
      await writeField(CANDIDATES_UID, JSON.stringify(candidates));
      const decisionId = `STR-DEC-${Date.now().toString(36).toUpperCase()}`;
      await writeField("STR-01-FLD-DECISION-ID", decisionId);
      await writeField("STR-01-FLD-DECISION-RESULT", "ADOPTED_CONTEXT");
      await writeField("STR-01-FLD-DECISION-REASON", reason);
      await writeField("STR-01-FLD-EXECUTION-STATE", "PENDING_OWNER_MODULE");
      await writeField("STR-01-FLD-REVIEW-STATE", "ADOPTED");
      await writeField("STR-01-FLD-CANDIDATE-REF", `${candidate.candidateId} · v${candidate.version} · ADOPTED`);
      await writeField(STR_STATE_ERROR_UID, null);
      await refreshMemoryFields();
      await refreshFeedbackFields();
      await writeStage();
      return;
    }

    case "STR-01-ACT-OPEN-OWNER":
      // UI_NAVIGATION: the owner module navigation is owned by the shell.
      return;

    case "STR-01-ACT-AUDIT": {
      const rows = await getSqlClient()
        .all<{ event_uid: string; action_uid: string; occurred_at: string }>(
          "SELECT event_uid, action_uid, occurred_at FROM ghsn_str_audit_event ORDER BY occurred_at DESC, event_uid DESC LIMIT 8",
        )
        .catch(() => []);
      await refreshMemoryFields();
      await refreshFeedbackFields();
      const lines = rows.map((row) => `${row.event_uid} · ${row.action_uid} · ${row.occurred_at}`);
      // REPORT_AUTHORITY_GAP trace: registered section gaps surface here so
      // unavailable projections stay visible instead of silent.
      const memoryAvailable = (await readField("STR-01-LST-PATTERNS")) !== null || (await readField("STR-01-LST-BASELINES")) !== null;
      if (!memoryAvailable) lines.push("STR-01-ERR-MEMORY-001 · authorized strategic memory projection unavailable (showing unavailable state)");
      const adopted = (await readField("STR-01-FLD-DECISION-RESULT")) === "ADOPTED_CONTEXT";
      if (adopted && !(await readField("STR-01-FLD-ACTUAL"))) {
        lines.push("STR-01-ERR-FEEDBACK-001 · execution result/KPI refs missing (showing pending feedback)");
      }
      await writeField("STR-01-FLD-CORRELATION", lines.join("\n") || null);
      return;
    }

    default:
      // Word §errors: unlisted action is BLOCK + REPORT_AUTHORITY_GAP.
      await writeError(err("STR-01-ERR-UNDEFINED-001", `Unlisted control/action requested: ${controlUid}/${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
      return;
  }
}

export async function hasStrScope(accountUid: string | undefined, actionUid: string): Promise<boolean> {
  const scope = STR_PERMISSION_SCOPES[actionUid];
  if (!scope) return true;
  return hasScope(accountUid, scope);
}
