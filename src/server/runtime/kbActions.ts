// admin:KB-01 runtime (ACPOS_KB-01_FINAL_LOCKED_ENCODING).
// server_gate_order: identity -> account_permission -> scope -> condition ->
// state_guard -> expected_version_when_write -> idempotency_when_side_effect -> audit.
// All refusals write the registered error registry object; nothing is inferred.

import { getSqlClient } from "../db/client";
import { seedScope } from "../db/seed";
import {
  KB_ACTION_SCOPES,
  KB_CONTROL_ACTIONS,
  KB_CONTROL_VIEWS,
  KB_STATE_AUDIT_UID,
  KB_STATE_BASKET_UID,
  KB_STATE_CANDIDATES_UID,
  KB_STATE_CITATIONS_UID,
  KB_STATE_DRAFTS_UID,
  KB_STATE_ERROR_UID,
  KB_STATE_EXPERIENCE_UID,
  KB_STATE_IDEMPOTENCY_UID,
  KB_STATE_LEARNING_UID,
  KB_STATE_RESULTS_UID,
  KB_STATE_REPLAY_UID,
  KB_STATE_RUNS_UID,
  KB_STATE_SOURCES_UID,
  KB_VIEW_OPERATIONS,
  type KbDraftState,
  type KbRunStatus,
  type KbSourceStatus,
} from "../domain/kb";
import { runAcquisition, type AcquisitionIntent, type CrawledItem } from "../acquisition/crawler";

function serialize(value: unknown): string {
  return JSON.stringify(value);
}

function parse<T>(raw: string | null | undefined, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

interface KbError {
  code: string;
  detail: string;
  recovery: string;
  at: string;
}

function err(code: string, detail: string, recovery: string): KbError {
  return { code, detail, recovery, at: new Date().toISOString() };
}

async function writeError(error: KbError): Promise<void> {
  await writeField(KB_STATE_ERROR_UID, serialize(error));
}

async function writeField(uid: string, value: string | null): Promise<void> {
  await getSqlClient().run(
    "INSERT INTO ghsn_kb_field_projection (control_uid, value_text) VALUES (?, ?) ON CONFLICT(control_uid) DO UPDATE SET value_text = excluded.value_text",
    [uid, value],
  );
}

async function readField(uid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    "SELECT value_text FROM ghsn_kb_field_projection WHERE control_uid = ?",
    [uid],
  );
  return rows[0]?.value_text ?? null;
}

async function appendAudit(accountUid: string, controlUid: string, actionUid: string, note: string): Promise<void> {
  const eventUid = `EVT-KB-ACTION-${Date.now()}-${Math.random().toString(36).slice(2, 8)}-${controlUid}`;
  await getSqlClient().run(
    "INSERT INTO ghsn_kb_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at) VALUES (?, ?, ?, ?, ?)",
    [eventUid, accountUid ?? "unknown", controlUid, actionUid, new Date().toISOString()],
  );
  const previous = await readField(KB_STATE_AUDIT_UID);
  const lines = previous ? previous.split("\n") : [];
  lines.push(`${new Date().toISOString()} ${actionUid} ${note}`);
  await writeField(KB_STATE_AUDIT_UID, lines.slice(-50).join("\n"));
}

async function hasScope(accountUid: string | undefined, scope: string): Promise<boolean> {
  if (!accountUid) return false;
  await seedScope("kb");
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_kb_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, scope],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

function parsePayload(nextValue: string | undefined): Record<string, unknown> | null {
  const raw = (nextValue ?? "").trim();
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

// Contract audit defaults: idempotency_key true for effectful operations.
const SIDE_EFFECT_OPERATIONS = new Set([
  "createKnowledgeSource",
  "updateKnowledgeSource",
  "pauseKnowledgeSource",
  "resumeKnowledgeSource",
  "retireKnowledgeSource",
  "createAcquisitionJob",
  "retryAcquisitionJob",
  "createContextCandidate",
  "createLearningCandidate",
  "createKnowledgeDraftFromExperience",
  "saveKnowledgeDraft",
  "approveKnowledgeDraft",
  "returnKnowledgeDraft",
  "rejectKnowledgeDraft",
]);

async function recordIdempotency(accountUid: string, controlUid: string, actionUid: string, idempotencyKey: string): Promise<void> {
  await appendAudit(accountUid, controlUid, actionUid, `IDEMPOTENT-REPLAY key=${idempotencyKey}`);
}

interface KbSource {
  sourceId: string;
  version: number;
  name: string;
  sourceType: string;
  scope: string;
  rights: string;
  classification: string;
  collectionMethod: string;
  collectionConfig: Record<string, unknown>;
  freshnessPolicy: string;
  retentionPolicy: string;
  status: KbSourceStatus;
}

interface KbRun {
  runId: string;
  sourceRef: string;
  runType: string;
  status: KbRunStatus;
  progress: string;
  startedAt: string;
  endedAt: string | null;
  failure: string | null;
  retryEligible: boolean;
  attempt: number;
  itemCount: number;
}

async function readSourcesAsync(): Promise<KbSource[]> {
  return parse<KbSource[]>(await readField(KB_STATE_SOURCES_UID), []);
}

async function writeSources(sources: KbSource[]): Promise<void> {
  await writeField(KB_STATE_SOURCES_UID, serialize(sources));
}

async function readRuns(): Promise<KbRun[]> {
  return parse<KbRun[]>(await readField(KB_STATE_RUNS_UID), []);
}

async function writeRuns(runs: KbRun[]): Promise<void> {
  await writeField(KB_STATE_RUNS_UID, serialize(runs));
}

async function persistSnapshots(runId: string, sourceRef: string, items: CrawledItem[]): Promise<void> {
  for (const item of items) {
    await getSqlClient().run(
      "INSERT OR IGNORE INTO ghsn_kb_acquisition_snapshot (snapshot_uid, run_id, source_ref, url, http_status, content_hash, fetched_at, depth, content_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
      [`SNAP-${item.content_hash}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, runId, sourceRef, item.url, item.http_status, item.content_hash, item.fetched_at, item.depth, item.text],
    );
  }
}

function itemsToResults(items: CrawledItem[]): Array<Record<string, string>> {
  return items.map((item) => ({
    result_ref: item.url,
    classification_type: "EVIDENCE",
    title: item.title || item.url,
    source_ref: item.url,
    source_time: item.fetched_at,
    source_version: item.content_hash,
    freshness_state: "FRESH",
    review_state: "TRACEABLE",
    text_excerpt: item.text.slice(0, 300),
  }));
}

function itemsToCitations(items: CrawledItem[]): Array<Record<string, string>> {
  return items.map((item) => ({
    citation_id: `CIT-${item.content_hash.slice(0, 12)}`,
    source_ref: item.url,
    source_location: `depth=${item.depth}`,
    source_time: item.fetched_at,
    source_version: item.content_hash,
    checksum: item.content_hash,
    classification: "公開",
    evidence_ref: item.url,
  }));
}

// ACPOSExperienceEngine capture: REAL_EXECUTION_ONLY — experience records are
// registered from real acquisition run outcomes, never synthesized.
function itemsToExperience(
  run: KbRun,
  items: CrawledItem[],
  report: { pages_fetched: number; pages_skipped_robots: number; pages_deduped: number },
): Array<Record<string, unknown>> {
  const citations = itemsToCitations(items);
  return items.map((item) => ({
    experience_id: `EXP-${item.content_hash.slice(0, 12)}-${run.runId.replace("RUN-", "")}`,
    domain: "acquisition",
    department: "system",
    task_type: run.runType,
    source_context_refs: [run.sourceRef],
    provider_model_ref: "runtime:acquisition-crawler",
    route_decision_ref: run.runType,
    attempt_count: run.attempt,
    latency_ms: Math.max(0, new Date(run.endedAt ?? run.startedAt).getTime() - new Date(run.startedAt).getTime()),
    cost_ref: null,
    evaluation_refs: [citations.find((c) => c.source_ref === item.url)?.citation_id ?? `CIT-${item.content_hash.slice(0, 12)}`],
    qa_outcome_refs: [] as string[],
    correction_refs: [] as string[],
    business_human_outcome: {
      status: "REAL_RUN_COMPLETED",
      item_count: items.length,
      pages_fetched: report.pages_fetched,
      pages_skipped_robots: report.pages_skipped_robots,
      pages_deduped: report.pages_deduped,
    },
    state: "OUTCOME_COMPLETE",
    run_id: run.runId,
    source_ref: item.url,
  }));
}

function requireFields(payload: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = payload[key];
    if (value === undefined || value === null || (typeof value === "string" && !value.trim())) {
      return key;
    }
  }
  return null;
}

function hasForbiddenSecret(payload: Record<string, unknown>): boolean {
  return "raw_secret" in payload || "credential_plaintext" in payload;
}

export async function applyKbAction(
  accountUid: string | undefined,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<void> {
  const requiredScope = KB_ACTION_SCOPES[actionUid];
  if (!requiredScope) {
    await writeError(err("KB_UNSUPPORTED_OPERATION", `Unregistered operation requested: ${actionUid}`, "BLOCK_AND_REPORT_AUTHORITY_GAP"));
    return;
  }
  if (!(await hasScope(accountUid, requiredScope))) {
    await writeError(err("KB_PERMISSION_DENIED", `${requiredScope} required for ${actionUid}`, "HIDE_PROTECTED_CONTENT_AND_ACTION"));
    return;
  }
  // View-to-operation binding: invoking control must belong to a view whose
  // registered operations include this action (unknown binding => BLOCK).
  const owningViews = KB_CONTROL_VIEWS[controlUid];
  const viewBound = Array.isArray(owningViews) && owningViews.some((view) => KB_VIEW_OPERATIONS[view]?.includes(actionUid));
  if (!viewBound) {
    await writeError(err("KB_UNSUPPORTED_OPERATION", `Operation ${actionUid} is not registered for control ${controlUid}`, "BLOCK_AND_REPORT_AUTHORITY_GAP"));
    return;
  }
  const payload = parsePayload(nextValue);
  if (payload === null) {
    await writeError(err("KB_UNSUPPORTED_OPERATION", "Payload is not a JSON object", "BLOCK_AND_REPORT_AUTHORITY_GAP"));
    return;
  }
  const idempotencyKey = String(payload.idempotency_key ?? "");
  if (SIDE_EFFECT_OPERATIONS.has(actionUid)) {
    if (!idempotencyKey) {
      await writeError(err("KB_UNSUPPORTED_OPERATION", `${actionUid} requires idempotency_key per contract audit defaults`, "RESEND_WITH_IDEMPOTENCY_KEY"));
      return;
    }
    const registry = parse<Record<string, string>>(await readField(KB_STATE_IDEMPOTENCY_UID), {});
    const fingerprint = `${actionUid}:${idempotencyKey}`;
    if (registry[fingerprint]) {
      await recordIdempotency(accountUid ?? "unknown", controlUid, actionUid, idempotencyKey);
      await writeField(KB_STATE_ERROR_UID, null);
      return;
    }
    registry[fingerprint] = new Date().toISOString();
    const entries = Object.entries(registry).slice(-50);
    await writeField(KB_STATE_IDEMPOTENCY_UID, serialize(Object.fromEntries(entries)));
  }
  if (hasForbiddenSecret(payload)) {
    await writeError(err("KB_RAW_SECRET_FORBIDDEN", "raw_secret/credential_plaintext are forbidden fields", "USE_SECRET_REFERENCE_OR_REGISTERED_CONNECTOR"));
    return;
  }

  switch (actionUid) {
    case "searchKnowledge":
      await searchKnowledge(payload);
      break;
    case "getCitation":
      await getCitation(payload);
      break;
    case "createKnowledgeSource":
      await createKnowledgeSource(accountUid ?? "unknown", controlUid, payload);
      break;
    case "updateKnowledgeSource":
      await updateKnowledgeSource(accountUid ?? "unknown", controlUid, payload);
      break;
    case "pauseKnowledgeSource":
      await changeSourceState(accountUid ?? "unknown", controlUid, payload, "PAUSED", "ACTIVE");
      break;
    case "resumeKnowledgeSource":
      await changeSourceState(accountUid ?? "unknown", controlUid, payload, "ACTIVE", "PAUSED");
      break;
    case "retireKnowledgeSource":
      await retireSource(accountUid ?? "unknown", controlUid, payload);
      break;
    case "createAcquisitionJob":
      await createAcquisitionJob(accountUid ?? "unknown", controlUid, payload);
      break;
    case "retryAcquisitionJob":
      await retryAcquisitionJob(accountUid ?? "unknown", controlUid, payload);
      break;
    case "addContextDraftItem":
      await addContextDraftItem(payload);
      break;
    case "removeContextDraftItem":
      await removeContextDraftItem(payload);
      break;
    case "createContextCandidate":
      await createContextCandidate(accountUid ?? "unknown", controlUid, payload);
      break;
    case "getExperienceReplay":
      await getExperienceReplay(payload);
      break;
    case "compareExperienceReplay":
      await compareExperienceReplay(payload);
      break;
    case "createLearningCandidate":
      await createLearningCandidate(accountUid ?? "unknown", controlUid, payload);
      break;
    case "createKnowledgeDraftFromExperience":
      await createKnowledgeDraftFromExperience(accountUid ?? "unknown", controlUid, payload);
      break;
    case "saveKnowledgeDraft":
      await saveKnowledgeDraft(accountUid ?? "unknown", controlUid, payload);
      break;
    case "compareKnowledgeVersions":
      await compareKnowledgeVersions(payload);
      break;
    case "approveKnowledgeDraft":
      await reviewKnowledgeDraft(accountUid ?? "unknown", controlUid, payload, "APPROVED");
      break;
    case "returnKnowledgeDraft":
      await reviewKnowledgeDraft(accountUid ?? "unknown", controlUid, payload, "RETURNED");
      break;
    case "rejectKnowledgeDraft":
      await reviewKnowledgeDraft(accountUid ?? "unknown", controlUid, payload, "REJECTED");
      break;
    default:
      await writeError(err("KB_UNSUPPORTED_OPERATION", `No runtime branch for ${actionUid}`, "BLOCK_AND_REPORT_AUTHORITY_GAP"));
  }
}

async function searchKnowledge(payload: Record<string, unknown>): Promise<void> {
  const query = String(payload.query ?? "").trim().toLowerCase();
  const sources = await readSourcesAsync();
  const results = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_RESULTS_UID), []);
  const drafts = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_DRAFTS_UID), []);
  const pool: Array<{ title: string; kind: string; row: Record<string, unknown> }> = [
    ...results.map((r) => ({ title: String(r.title ?? ""), kind: "RESULT", row: r })),
    ...drafts.filter((d) => d.state === "APPROVED").map((d) => ({ title: String(d.title ?? ""), kind: "APPROVED_KNOWLEDGE", row: d })),
    ...sources.map((s) => ({ title: s.name, kind: "SOURCE", row: s as unknown as Record<string, unknown> })),
  ];
  const matched = query ? pool.filter((entry) => entry.title.toLowerCase().includes(query)) : pool;
  await writeField(KB_STATE_RESULTS_UID, serialize(matched.map((entry) => ({ ...entry.row, __kind: entry.kind }))));
  await appendAudit("system", "CTRL-ADMIN-KB-01-ACT-SEARCH", "searchKnowledge", `query="${query}" matched=${matched.length}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function getCitation(payload: Record<string, unknown>): Promise<void> {
  const citationId = String(payload.citation_id ?? "").trim();
  const citations = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_CITATIONS_UID), []);
  const found = citations.find((c) => String(c.citation_id ?? "") === citationId);
  if (!found) {
    await writeError(err("KB_PERMISSION_DENIED", `Citation ${citationId} not registered`, "HIDE_PROTECTED_CONTENT_AND_ACTION"));
    return;
  }
  await writeField(KB_STATE_CITATIONS_UID, serialize([found]));
  await appendAudit("system", "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN", "getCitation", `citation=${citationId}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function createKnowledgeSource(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const missing = requireFields(payload, ["name", "source_type", "scope", "rights", "classification", "collection_method", "freshness_policy", "retention_policy"]);
  if (missing) {
    await writeError(err("KB_SCOPE_INVALID", `Missing required source field: ${missing}`, "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  const sources = await readSourcesAsync();
  const source: KbSource = {
    sourceId: `SRC-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    version: 1,
    name: String(payload.name),
    sourceType: String(payload.source_type),
    scope: String(payload.scope),
    rights: String(payload.rights),
    classification: String(payload.classification),
    collectionMethod: String(payload.collection_method),
    collectionConfig: parse<Record<string, unknown>>(serialize(payload.collection_config ?? {}), {}),
    freshnessPolicy: String(payload.freshness_policy),
    retentionPolicy: String(payload.retention_policy),
    status: "DRAFT",
  };
  sources.push(source);
  await writeSources(sources);
  await appendAudit(accountUid, controlUid, "createKnowledgeSource", `source=${source.sourceId} status=DRAFT`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function updateKnowledgeSource(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const sources = await readSourcesAsync();
  const source = sources.find((s) => s.sourceId === String(payload.source_id ?? ""));
  if (!source) {
    await writeError(err("KB_SCOPE_INVALID", "source_id does not match a registered source", "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  const expected = Number(payload.expected_version ?? -1);
  if (expected !== source.version) {
    await writeError(err("KB_VERSION_CONFLICT", `expected_version=${expected} actual=${source.version}`, "REFRESH_EXACT_VERSION_AND_REVIEW_DIFF"));
    return;
  }
  if (source.status === "RETIRED") {
    await writeError(err("KB_SOURCE_RIGHTS_INVALID", "retired sources are immutable", "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  const patchable = ["name", "source_type", "scope", "rights", "classification", "collection_method", "collection_config", "freshness_policy", "retention_policy"] as const;
  for (const key of patchable) {
    if (payload[key] !== undefined) {
      if (key === "collection_config") source.collectionConfig = parse<Record<string, unknown>>(serialize(payload[key]), {});
      else (source as unknown as Record<string, unknown>)[key] = payload[key];
    }
  }
  // State machine: DRAFT -> ACTIVE happens through SOURCE-SAVE (G:SOURCE-SAVE).
  if (source.status === "DRAFT") source.status = "ACTIVE";
  source.version += 1;
  await writeSources(sources);
  await appendAudit(accountUid, controlUid, "updateKnowledgeSource", `source=${source.sourceId} v${source.version} status=${source.status}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function changeSourceState(accountUid: string, controlUid: string, payload: Record<string, unknown>, next: KbSourceStatus, required: KbSourceStatus): Promise<void> {
  const sources = await readSourcesAsync();
  const source = sources.find((s) => s.sourceId === String(payload.source_id ?? ""));
  if (!source) {
    await writeError(err("KB_SCOPE_INVALID", "source_id does not match a registered source", "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  const expected = Number(payload.expected_version ?? -1);
  if (expected !== source.version) {
    await writeError(err("KB_VERSION_CONFLICT", `expected_version=${expected} actual=${source.version}`, "REFRESH_EXACT_VERSION_AND_REVIEW_DIFF"));
    return;
  }
  if (source.status !== required) {
    await writeError(err("KB_SOURCE_RIGHTS_INVALID", `transition requires status ${required}, actual ${source.status}`, "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  source.status = next;
  source.version += 1;
  await writeSources(sources);
  await appendAudit(accountUid, controlUid, controlUid.includes("PAUSE") ? "pauseKnowledgeSource" : "resumeKnowledgeSource", `source=${source.sourceId} status=${next}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function retireSource(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const sources = await readSourcesAsync();
  const source = sources.find((s) => s.sourceId === String(payload.source_id ?? ""));
  if (!source) {
    await writeError(err("KB_SCOPE_INVALID", "source_id does not match a registered source", "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  const expected = Number(payload.expected_version ?? -1);
  if (expected !== source.version) {
    await writeError(err("KB_VERSION_CONFLICT", `expected_version=${expected} actual=${source.version}`, "REFRESH_EXACT_VERSION_AND_REVIEW_DIFF"));
    return;
  }
  const runs = await readRuns();
  if (runs.some((r) => r.sourceRef === source.sourceId && (r.status === "RUNNING" || r.status === "NORMALIZING" || r.status === "PENDING"))) {
    await writeError(err("KB_DUPLICATE_ACTIVE_RUN", "active non-cancelable run blocks retire", "OPEN_EXISTING_RUN"));
    return;
  }
  source.status = "RETIRED";
  source.version += 1;
  await writeSources(sources);
  await appendAudit(accountUid, controlUid, "retireKnowledgeSource", `source=${source.sourceId} status=RETIRED`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function intentFromSource(source: KbSource, runType: string): Promise<{ intent: AcquisitionIntent } | { failure: KbError }> {
  const config = source.collectionConfig ?? {};
  const seed = String(config.seed_url_or_query ?? config.url ?? "").trim();
  if (!seed) {
    return { failure: err("KB_SOURCE_RIGHTS_INVALID", `source ${source.sourceId} has no seed_url_or_query in collection_config`, "FIX_SOURCE_GOVERNANCE") };
  }
  return {
    intent: {
      source_ref: source.sourceId,
      acquisition_mode: runType,
      seed_url_or_query: seed,
      allowed_domains: Array.isArray(config.allowed_domains) ? (config.allowed_domains as string[]) : [],
      denied_domains: Array.isArray(config.denied_domains) ? (config.denied_domains as string[]) : [],
      same_domain_only: config.same_domain_only === true,
      max_depth: Number(config.max_depth ?? 1),
      max_pages: Number(config.max_pages ?? 3),
      content_types: Array.isArray(config.content_types) ? (config.content_types as string[]) : [],
    },
  };
}

async function createAcquisitionJob(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const missing = requireFields(payload, ["source_ref", "scope", "run_type"]);
  if (missing) {
    await writeError(err("KB_SCOPE_INVALID", `Missing required run field: ${missing}`, "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  const sources = await readSourcesAsync();
  const source = sources.find((s) => s.sourceId === String(payload.source_ref));
  if (!source) {
    await writeError(err("KB_SCOPE_INVALID", "source_ref does not match a registered source", "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  if (source.status !== "ACTIVE") {
    await writeError(err("KB_SOURCE_RIGHTS_INVALID", `ingest requires status ACTIVE, actual ${source.status}`, "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  const runs = await readRuns();
  if (runs.some((r) => r.sourceRef === source.sourceId && (r.status === "RUNNING" || r.status === "NORMALIZING" || r.status === "PENDING"))) {
    await writeError(err("KB_DUPLICATE_ACTIVE_RUN", "duplicate active run for source", "OPEN_EXISTING_RUN"));
    return;
  }
  const runType = String(payload.run_type);
  const prepared = await intentFromSource(source, runType);
  if ("failure" in prepared) {
    await writeError(prepared.failure);
    return;
  }
  const run: KbRun = {
    runId: `RUN-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    sourceRef: source.sourceId,
    runType,
    status: "RUNNING",
    progress: "0%",
    startedAt: new Date().toISOString(),
    endedAt: null,
    failure: null,
    retryEligible: false,
    attempt: 1,
    itemCount: 0,
  };
  runs.push(run);
  await writeRuns(runs);
  await appendAudit(accountUid, controlUid, "createAcquisitionJob", `run=${run.runId} source=${source.sourceId} RUNNING`);
  const report = await runAcquisition(prepared.intent);
  run.status = report.ok ? "COMPLETED" : report.failure === "NO_ITEMS_COLLECTED" ? "FAILED" : "FAILED";
  run.progress = report.ok ? "100%" : "0%";
  run.endedAt = new Date().toISOString();
  run.failure = report.failure;
  run.retryEligible = report.ok === false && report.failure !== "SEED_URL_MISSING_OR_INVALID";
  run.itemCount = report.items.length;
  await writeRuns(runs);
  if (report.ok) {
    await persistSnapshots(run.runId, source.sourceId, report.items);
    await writeField(KB_STATE_RESULTS_UID, serialize(itemsToResults(report.items)));
    await writeField(KB_STATE_CITATIONS_UID, serialize(itemsToCitations(report.items)));
    const experience = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_EXPERIENCE_UID), []);
    experience.push(...itemsToExperience(run, report.items, report));
    await writeField(KB_STATE_EXPERIENCE_UID, serialize(experience));
    await appendAudit(accountUid, controlUid, "createAcquisitionJob", `run=${run.runId} COMPLETED items=${report.items.length} fetched=${report.pages_fetched} robotsSkipped=${report.pages_skipped_robots} deduped=${report.pages_deduped}`);
  } else {
    await appendAudit(accountUid, controlUid, "createAcquisitionJob", `run=${run.runId} FAILED ${report.failure ?? "unknown"}`);
  }
  await writeField(KB_STATE_ERROR_UID, report.ok ? null : serialize(err("KB_INGESTION_NOT_RETRYABLE", report.failure ?? "acquisition failed", "OPEN_FAILURE_DETAIL_AND_RESOLVE_CAUSE")));
}

async function retryAcquisitionJob(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const runId = String(payload.run_id ?? "");
  const runs = await readRuns();
  const run = runs.find((r) => r.runId === runId);
  if (!run) {
    await writeError(err("KB_SCOPE_INVALID", `run ${runId} not registered`, "OPEN_FAILURE_DETAIL_AND_RESOLVE_CAUSE"));
    return;
  }
  if (run.status !== "FAILED" || !run.retryEligible) {
    await writeError(err("KB_INGESTION_NOT_RETRYABLE", `run ${runId} status=${run.status} retry_eligible=${run.retryEligible}`, "OPEN_FAILURE_DETAIL_AND_RESOLVE_CAUSE"));
    return;
  }
  const sources = await readSourcesAsync();
  const source = sources.find((s) => s.sourceId === run.sourceRef);
  if (!source || source.status === "RETIRED") {
    await writeError(err("KB_SOURCE_RIGHTS_INVALID", "source retired; retry blocked", "FIX_SOURCE_GOVERNANCE"));
    return;
  }
  const prepared = await intentFromSource(source, run.runType);
  if ("failure" in prepared) {
    await writeError(prepared.failure);
    return;
  }
  run.status = "RUNNING";
  run.attempt += 1;
  run.progress = "0%";
  run.endedAt = null;
  await writeRuns(runs);
  await appendAudit(accountUid, controlUid, "retryAcquisitionJob", `run=${run.runId} attempt=${run.attempt} RUNNING`);
  const report = await runAcquisition(prepared.intent);
  run.status = report.ok ? "COMPLETED" : "FAILED";
  run.progress = report.ok ? "100%" : "0%";
  run.endedAt = new Date().toISOString();
  run.failure = report.failure;
  run.retryEligible = !report.ok && report.failure !== "SEED_URL_MISSING_OR_INVALID";
  run.itemCount = report.items.length;
  await writeRuns(runs);
  if (report.ok) {
    await persistSnapshots(run.runId, source.sourceId, report.items);
    await writeField(KB_STATE_RESULTS_UID, serialize(itemsToResults(report.items)));
    await writeField(KB_STATE_CITATIONS_UID, serialize(itemsToCitations(report.items)));
    const experience = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_EXPERIENCE_UID), []);
    experience.push(...itemsToExperience(run, report.items, report));
    await writeField(KB_STATE_EXPERIENCE_UID, serialize(experience));
  }
  await appendAudit(accountUid, controlUid, "retryAcquisitionJob", `run=${run.runId} ${run.status} items=${report.items.length}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function addContextDraftItem(payload: Record<string, unknown>): Promise<void> {
  const ref = String(payload.ref ?? "").trim();
  if (!ref) {
    await writeError(err("KB_SCOPE_INVALID", "ref required for context draft item", "CORRECT_SCOPE"));
    return;
  }
  const basket = parse<Array<Record<string, string>>>(await readField(KB_STATE_BASKET_UID), []);
  if (!basket.some((item) => item.ref === ref)) basket.push({ ref, added_at: new Date().toISOString() });
  await writeField(KB_STATE_BASKET_UID, serialize(basket));
  await appendAudit("system", "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD", "addContextDraftItem", `ref=${ref} basket=${basket.length}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function removeContextDraftItem(payload: Record<string, unknown>): Promise<void> {
  const ref = String(payload.ref ?? "").trim();
  const basket = parse<Array<Record<string, string>>>(await readField(KB_STATE_BASKET_UID), []);
  const next = basket.filter((item) => item.ref !== ref);
  await writeField(KB_STATE_BASKET_UID, serialize(next));
  await appendAudit("system", "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE", "removeContextDraftItem", `ref=${ref} basket=${next.length}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function createContextCandidate(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const missing = requireFields(payload, ["purpose", "scope"]);
  if (missing) {
    await writeError(err("KB_SCOPE_INVALID", `Missing required context field: ${missing}`, "CORRECT_SCOPE"));
    return;
  }
  const basket = parse<Array<Record<string, string>>>(await readField(KB_STATE_BASKET_UID), []);
  const explicitRefs = Array.isArray(payload.selected_refs) ? (payload.selected_refs as string[]) : [];
  const selectedRefs = explicitRefs.length > 0 ? explicitRefs : basket.map((item) => item.ref);
  if (selectedRefs.length === 0) {
    await writeError(err("KB_SCOPE_INVALID", "selected_refs >= 1 required (empty selection)", "CORRECT_SCOPE"));
    return;
  }
  const citations = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_CITATIONS_UID), []);
  const results = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_RESULTS_UID), []);
  const citationRefs = new Set(
    citations.flatMap((c) => [String(c.evidence_ref ?? ""), String(c.source_ref ?? "")]).filter((ref) => ref),
  );
  const resultRefs = new Set(results.map((r) => String(r.result_ref ?? r.url ?? "")));
  // Every factual ref must resolve to citation evidence or a registered result;
  // system refs (KB-*) are internal lineage, not external claims.
  const untraceable = selectedRefs.filter((ref) => !citationRefs.has(ref) && !resultRefs.has(ref) && !ref.startsWith("KB-"));
  if (untraceable.length > 0) {
    await writeError(err("KB_CITATION_REQUIRED", `factual refs lack citation/evidence: ${untraceable.join(", ")}`, "ADD_VALID_CITATION_OR_RECLASSIFY"));
    return;
  }
  const candidate: Record<string, unknown> = {
    context_candidate_id: `CTX-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    version: 1,
    purpose: String(payload.purpose),
    scope: String(payload.scope),
    selected_refs: selectedRefs,
    evidence_refs: citations.map((c) => String(c.citation_id ?? "")),
    state: "READY_FOR_CONSUMER_REVIEW",
    context_fingerprint: `${selectedRefs.length}refs-${Date.now()}`,
  };
  const candidates = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_CANDIDATES_UID), []);
  candidates.push(candidate);
  await writeField(KB_STATE_CANDIDATES_UID, serialize(candidates));
  await writeField(KB_STATE_BASKET_UID, serialize([]));
  await appendAudit(accountUid, controlUid, "createContextCandidate", `candidate=${candidate.context_candidate_id} refs=${selectedRefs.length}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function getExperienceReplay(payload: Record<string, unknown>): Promise<void> {
  const experienceId = String(payload.experience_id ?? "").trim();
  const experience = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_EXPERIENCE_UID), []);
  const record = experience.find((e) => String(e.experience_id ?? "") === experienceId);
  if (!record) {
    await writeError(err("KB_PERMISSION_DENIED", `experience ${experienceId} not registered`, "HIDE_PROTECTED_CONTENT_AND_ACTION"));
    return;
  }
  await writeField(KB_STATE_REPLAY_UID, serialize(record));
  await appendAudit("system", "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN", "getExperienceReplay", `experience=${experienceId}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function compareExperienceReplay(payload: Record<string, unknown>): Promise<void> {
  const compareRefs = Array.isArray(payload.compare_refs) ? (payload.compare_refs as string[]) : [];
  if (compareRefs.length < 2) {
    await writeError(err("KB_LINEAGE_INCOMPLETE", "at least two comparable attempts/versions required", "RESOLVE_SOURCE_LINEAGE"));
    return;
  }
  const experience = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_EXPERIENCE_UID), []);
  const records = experience.filter((e) => compareRefs.includes(String(e.experience_id ?? "")));
  if (records.length < 2) {
    await writeError(err("KB_LINEAGE_INCOMPLETE", "comparable experience records missing", "RESOLVE_SOURCE_LINEAGE"));
    return;
  }
  await writeField(KB_STATE_REPLAY_UID, serialize({ compare_mode: String(payload.compare_mode ?? "ATTEMPT"), records }));
  await appendAudit("system", "CTRL-ADMIN-KB-01-ACT-REPLAY-COMPARE", "compareExperienceReplay", `refs=${compareRefs.length}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function createLearningCandidate(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const missing = requireFields(payload, ["scope", "pattern", "proposed_improvement"]);
  if (missing) {
    await writeError(err("KB_SCOPE_INVALID", `Missing required learning field: ${missing}`, "CORRECT_SCOPE"));
    return;
  }
  const experienceRefs = Array.isArray(payload.experience_refs) ? (payload.experience_refs as string[]) : [];
  const experience = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_EXPERIENCE_UID), []);
  const incomplete = experienceRefs.filter((ref) => {
    const record = experience.find((e) => String(e.experience_id ?? "") === ref);
    return !record || record.state !== "OUTCOME_COMPLETE";
  });
  if (experienceRefs.length > 0 && incomplete.length > 0) {
    await writeError(err("KB_OUTCOME_PENDING", `experience not OUTCOME_COMPLETE: ${incomplete.join(", ")}`, "WAIT_FOR_REAL_OUTCOME"));
    return;
  }
  const learning: Record<string, unknown> = {
    learning_candidate_id: `LEARN-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    version: 1,
    scope: String(payload.scope),
    pattern: String(payload.pattern),
    proposed_improvement: String(payload.proposed_improvement),
    evidence_refs: Array.isArray(payload.evidence_refs) ? payload.evidence_refs : experienceRefs,
    limitations: String(payload.limitations ?? ""),
    state: "DRAFT",
  };
  const learnings = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_LEARNING_UID), []);
  learnings.push(learning);
  await writeField(KB_STATE_LEARNING_UID, serialize(learnings));
  await appendAudit(accountUid, controlUid, "createLearningCandidate", `learning=${learning.learning_candidate_id}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function createKnowledgeDraftFromExperience(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const missing = requireFields(payload, ["scope", "knowledge_type"]);
  if (missing) {
    await writeError(err("KB_SCOPE_INVALID", `Missing required draft field: ${missing}`, "CORRECT_SCOPE"));
    return;
  }
  const experienceRefs = Array.isArray(payload.experience_refs) ? (payload.experience_refs as string[]) : [];
  const experience = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_EXPERIENCE_UID), []);
  const pending = experienceRefs.filter((ref) => {
    const record = experience.find((e) => String(e.experience_id ?? "") === ref);
    return !record || record.state !== "OUTCOME_COMPLETE";
  });
  if (experienceRefs.length > 0 && pending.length > 0) {
    await writeError(err("KB_OUTCOME_PENDING", `experience not OUTCOME_COMPLETE: ${pending.join(", ")}`, "WAIT_FOR_REAL_OUTCOME"));
    return;
  }
  const draft: Record<string, unknown> = {
    knowledge_id: `KN-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    draft_version: 1,
    title: String(payload.title_seed ?? "Draft from experience"),
    knowledge_type: String(payload.knowledge_type),
    scope: String(payload.scope),
    classification: String(payload.classification ?? ""),
    citation_refs: [] as string[],
    outcome_refs: [] as string[],
    experience_refs: experienceRefs,
    state: "DRAFT",
  };
  const drafts = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_DRAFTS_UID), []);
  drafts.push(draft);
  await writeField(KB_STATE_DRAFTS_UID, serialize(drafts));
  await appendAudit(accountUid, controlUid, "createKnowledgeDraftFromExperience", `draft=${draft.knowledge_id}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function saveKnowledgeDraft(accountUid: string, controlUid: string, payload: Record<string, unknown>): Promise<void> {
  const missing = requireFields(payload, ["knowledge_id", "expected_version", "title", "knowledge_type", "scope", "classification"]);
  if (missing) {
    await writeError(err("KB_SCOPE_INVALID", `Missing required draft field: ${missing}`, "FIX_DRAFT"));
    return;
  }
  const drafts = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_DRAFTS_UID), []);
  const draft = drafts.find((d) => String(d.knowledge_id ?? "") === String(payload.knowledge_id));
  if (!draft) {
    await writeError(err("KB_SCOPE_INVALID", "knowledge_id does not match a registered draft", "FIX_DRAFT"));
    return;
  }
  const expected = Number(payload.expected_version ?? -1);
  if (expected !== Number(draft.draft_version ?? 0)) {
    await writeError(err("KB_VERSION_CONFLICT", `expected_version=${expected} actual=${draft.draft_version}`, "REFRESH_EXACT_VERSION_AND_REVIEW_DIFF"));
    return;
  }
  if (draft.state !== "DRAFT" && draft.state !== "RETURNED") {
    await writeError(err("KB_REVIEW_CHECK_INCOMPLETE", `draft state ${draft.state} is not editable`, "FIX_DRAFT"));
    return;
  }
  for (const key of ["title", "knowledge_type", "summary", "content", "scope", "classification"] as const) {
    if (payload[key] !== undefined) draft[key] = payload[key];
  }
  for (const key of ["citation_refs", "outcome_refs", "experience_refs"] as const) {
    if (Array.isArray(payload[key])) draft[key] = payload[key];
  }
  draft.draft_version = Number(draft.draft_version ?? 0) + 1;
  draft.state = "DRAFT" as KbDraftState;
  await writeField(KB_STATE_DRAFTS_UID, serialize(drafts));
  await appendAudit(accountUid, controlUid, "saveKnowledgeDraft", `draft=${draft.knowledge_id} v${draft.draft_version}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

async function compareKnowledgeVersions(payload: Record<string, unknown>): Promise<void> {
  const knowledgeId = String(payload.knowledge_id ?? "");
  const left = String(payload.left_version ?? "");
  const right = String(payload.right_version ?? "");
  const drafts = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_DRAFTS_UID), []);
  const draft = drafts.find((d) => String(d.knowledge_id ?? "") === knowledgeId);
  if (!draft) {
    await writeError(err("KB_SCOPE_INVALID", `knowledge ${knowledgeId} not registered`, "FIX_DRAFT"));
    return;
  }
  await appendAudit("system", "CTRL-ADMIN-KB-01-ACT-VERSION-COMPARE", "compareKnowledgeVersions", `knowledge=${knowledgeId} ${left}..${right}`);
  await writeField(
    KB_STATE_DRAFTS_UID,
    serialize(
      drafts.map((d) =>
        d === draft ? { ...d, __version_diff: { left_version: left, right_version: right, fields: Object.keys(d).filter((k) => !k.startsWith("__")) } } : d,
      ),
    ),
  );
  await writeField(KB_STATE_ERROR_UID, null);
}

async function reviewKnowledgeDraft(accountUid: string, controlUid: string, payload: Record<string, unknown>, decision: "APPROVED" | "RETURNED" | "REJECTED"): Promise<void> {
  const missing = requireFields(payload, ["knowledge_id", "expected_version", "review_rationale"]);
  if (missing) {
    await writeError(err("KB_REVIEW_CHECK_INCOMPLETE", `Missing required review field: ${missing}`, "COMPLETE_REVIEW_CHECKLIST"));
    return;
  }
  const drafts = parse<Array<Record<string, unknown>>>(await readField(KB_STATE_DRAFTS_UID), []);
  const draft = drafts.find((d) => String(d.knowledge_id ?? "") === String(payload.knowledge_id));
  if (!draft) {
    await writeError(err("KB_SCOPE_INVALID", "knowledge_id does not match a registered draft", "FIX_DRAFT"));
    return;
  }
  const expected = Number(payload.expected_version ?? -1);
  if (expected !== Number(draft.draft_version ?? 0)) {
    await writeError(err("KB_VERSION_CONFLICT", `expected_version=${expected} actual=${draft.draft_version}`, "REFRESH_EXACT_VERSION_AND_REVIEW_DIFF"));
    return;
  }
  if (draft.state !== "REVIEW") {
    await writeError(err("KB_REVIEW_CHECK_INCOMPLETE", `draft state ${draft.state} is not REVIEW`, "COMPLETE_REVIEW_CHECKLIST"));
    return;
  }
  const checks = payload.mandatory_check_results;
  if (decision === "APPROVED") {
    if (!checks || typeof checks !== "object") {
      await writeError(err("KB_REVIEW_CHECK_INCOMPLETE", "mandatory_check_results required for APPROVE", "COMPLETE_REVIEW_CHECKLIST"));
      return;
    }
    const values = Object.values(checks as Record<string, unknown>);
    if (values.length === 0 || values.some((v) => v !== true)) {
      await writeError(err("KB_REVIEW_CHECK_INCOMPLETE", "all mandatory checks must be true for APPROVE", "COMPLETE_REVIEW_CHECKLIST"));
      return;
    }
    const citationRefs = Array.isArray(draft.citation_refs) ? (draft.citation_refs as string[]) : [];
    if (draft.knowledge_type === "FACT" && citationRefs.length === 0) {
      await writeError(err("KB_CITATION_REQUIRED", "FACT approval requires traceable citation/evidence", "ADD_VALID_CITATION_OR_RECLASSIFY"));
      return;
    }
  }
  const previousApproved = drafts.find((d) => d.state === "APPROVED" && d.knowledge_type === draft.knowledge_type && d.knowledge_id !== draft.knowledge_id);
  draft.state = decision;
  draft.reviewed_by = accountUid;
  draft.reviewed_at = new Date().toISOString();
  draft.review_rationale = String(payload.review_rationale);
  if (decision === "APPROVED" && previousApproved) {
    previousApproved.state = "SUPERSEDED";
    draft.supersedes = previousApproved.knowledge_id;
  }
  await writeField(KB_STATE_DRAFTS_UID, serialize(drafts));
  await appendAudit(accountUid, controlUid, controlUid.includes("APPROVE") ? "approveKnowledgeDraft" : controlUid.includes("RETURN") ? "returnKnowledgeDraft" : "rejectKnowledgeDraft", `draft=${draft.knowledge_id} -> ${decision}${previousApproved && decision === "APPROVED" ? ` supersedes=${previousApproved.knowledge_id}` : ""}`);
  await writeField(KB_STATE_ERROR_UID, null);
}

export async function persistRecordKbAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<string> {
  await applyKbAction(accountUid, controlUid, actionUid, nextValue);
  return `EVT-KB-ACTION-${Date.now()}-${Math.random().toString(36).slice(2, 8)}-${controlUid}`;
}
