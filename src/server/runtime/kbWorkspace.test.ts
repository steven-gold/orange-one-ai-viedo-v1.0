import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { bootstrapDatabase } from "../db/migrate";
import { seedScope } from "../db/seed";
import { persistRecordKbAction, persistGetKbReadModel } from "../db/persist";
import { getSqlClient } from "../db/client";
import {
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
} from "../domain/kb";

const DEMO = "ACC-DEMO";
const READONLY = "ACC-KB-READONLY";

const ACT_SEARCH = "CTRL-ADMIN-KB-01-ACT-SEARCH";
const ACT_SEARCH_GLOBAL = "CTRL-ADMIN-KB-01-ACT-SEARCH-GLOBAL";
const ACT_SOURCE_CREATE = "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE";
const ACT_SOURCE_SAVE = "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE";
const ACT_SOURCE_PAUSE = "CTRL-ADMIN-KB-01-ACT-SOURCE-PAUSE";
const ACT_SOURCE_RESUME = "CTRL-ADMIN-KB-01-ACT-SOURCE-RESUME";
const ACT_SOURCE_RETIRE = "CTRL-ADMIN-KB-01-ACT-SOURCE-RETIRE";
const ACT_INGEST_START = "CTRL-ADMIN-KB-01-ACT-INGEST-START";
const ACT_INGEST_RETRY = "CTRL-ADMIN-KB-01-ACT-INGEST-RETRY";
const ACT_CITATION_OPEN = "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN";
const ACT_CONTEXT_ADD = "CTRL-ADMIN-KB-01-ACT-CONTEXT-ADD";
const ACT_CONTEXT_REMOVE = "CTRL-ADMIN-KB-01-ACT-CONTEXT-REMOVE";
const ACT_CONTEXT_CREATE = "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE";
const ACT_REPLAY_OPEN = "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN";
const ACT_REPLAY_COMPARE = "CTRL-ADMIN-KB-01-ACT-REPLAY-COMPARE";
const ACT_LEARNING_CREATE = "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE";
const ACT_DRAFT_FROM_EXP = "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP";
const ACT_DRAFT_SAVE = "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE";
const ACT_VERSION_COMPARE = "CTRL-ADMIN-KB-01-ACT-VERSION-COMPARE";
const ACT_APPROVE = "CTRL-ADMIN-KB-01-ACT-APPROVE";
const ACT_RETURN = "CTRL-ADMIN-KB-01-ACT-RETURN";
const ACT_REJECT = "CTRL-ADMIN-KB-01-ACT-REJECT";

// REVIEW view control carrying a SOURCE-PAUSE action: view-binding gate test.
const VIEW_BINDING_CONTROL = "CTRL-ADMIN-KB-01-VIEW-REVIEW";

const STATE_KEYS = [
  KB_STATE_ERROR_UID,
  KB_STATE_AUDIT_UID,
  KB_STATE_IDEMPOTENCY_UID,
  KB_STATE_SOURCES_UID,
  KB_STATE_RUNS_UID,
  KB_STATE_RESULTS_UID,
  KB_STATE_CITATIONS_UID,
  KB_STATE_BASKET_UID,
  KB_STATE_CANDIDATES_UID,
  KB_STATE_EXPERIENCE_UID,
  KB_STATE_REPLAY_UID,
  KB_STATE_LEARNING_UID,
  KB_STATE_DRAFTS_UID,
];

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

async function readState(uid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(
    "SELECT value_text FROM ghsn_kb_field_projection WHERE control_uid = ?",
    [uid],
  );
  const raw = rows[0]?.value_text ?? null;
  return raw === "" ? null : raw;
}

async function readError(): Promise<{ code?: string; message?: string } | null> {
  const raw = await readState(KB_STATE_ERROR_UID);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as { code?: string; message?: string };
  } catch {
    return null;
  }
}

async function readRegistry<T>(uid: string): Promise<T[]> {
  const raw = await readState(uid);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as T[];
  } catch {
    return [];
  }
}

interface SourceRow {
  sourceId: string;
  version: number;
  name: string;
  sourceType: string;
  scope: string;
  status: string;
  collectionConfig: Record<string, unknown>;
}

interface RunRow {
  runId: string;
  sourceRef: string;
  status: string;
  attempt: number;
  itemCount: number;
  failure: string | null;
  retryEligible: boolean;
}

function startFixture(): Promise<{ server: Server; port: number }> {
  const server = createServer((req, res) => {
    const url = req.url ?? "/";
    if (url === "/robots.txt") {
      res.writeHead(200, { "content-type": "text/plain" });
      res.end("User-agent: *\nAllow: /\nDisallow: /secret\n");
      return;
    }
    if (url === "/doc1") {
      res.writeHead(200, { "content-type": "text/html" });
      res.end('<html><head><title>Doc One</title></head><body><p>ACPOS fixture paragraph one with governance text.</p><a href="/doc2">next</a><a href="/secret">blocked</a></body></html>');
      return;
    }
    if (url === "/doc2") {
      res.writeHead(200, { "content-type": "text/html" });
      res.end('<html><head><title>Doc Two</title></head><body><p>ACPOS fixture paragraph two with acquisition text.</p></body></html>');
      return;
    }
    if (url === "/secret") {
      res.writeHead(200, { "content-type": "text/html" });
      res.end("<html><body>secret content that must never be crawled</body></html>");
      return;
    }
    res.writeHead(404, { "content-type": "text/plain" });
    res.end("not found");
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const port = (server.address() as AddressInfo).port;
      resolve({ server, port });
    });
  });
}

async function main(): Promise<void> {
  await bootstrapDatabase();
  await seedScope("kb");
  const client = getSqlClient();

  // The persistent sandbox DB records all migrations as applied; ensure the
  // snapshot table exists for runs of tests against an older sandbox file.
  await client.exec(`CREATE TABLE IF NOT EXISTS ghsn_kb_acquisition_snapshot (
    snapshot_uid TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    url TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    depth INTEGER NOT NULL,
    content_text TEXT
  )`);

  for (const uid of STATE_KEYS) {
    await client.run(
      "INSERT INTO ghsn_kb_field_projection (control_uid, value_text) VALUES (?, NULL) ON CONFLICT (control_uid) DO UPDATE SET value_text = NULL",
      [uid],
    );
  }
  await client.run(
    "INSERT INTO ghsn_account_kb_permission (account_uid, permission_uid) VALUES (?, 'knowledge.read') ON CONFLICT (account_uid, permission_uid) DO NOTHING",
    [READONLY],
  );
  await client.run("DELETE FROM ghsn_account_kb_permission WHERE account_uid = ? AND permission_uid <> 'knowledge.read'", [READONLY]);

  const { server, port } = await startFixture();
  const base = `http://127.0.0.1:${port}`;
  const idem = (tag: string) => `idem-kbtest-${tag}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  let passed = 0;
  const ok = (message: string) => {
    passed += 1;
    console.log(`  ok ${passed} - ${message}`);
  };

  try {
    // 1. Scope gate: READONLY lacks source.configure.
    await persistRecordKbAction(READONLY, ACT_SOURCE_CREATE, "createKnowledgeSource", JSON.stringify({ name: "x", source_type: "WEB", scope: "governance", rights: "PUBLIC", classification: "公開", collection_method: "WEB_FETCH", freshness_policy: "DAILY", retention_policy: "PERSIST" }));
    assertEqual((await readError())?.code, "KB_PERMISSION_DENIED", "readonly lacks source.configure");
    ok("scope gate denies source.configure for READONLY");

    // 2. READONLY knowledge.read search is allowed.
    await persistRecordKbAction(READONLY, ACT_SEARCH, "searchKnowledge", JSON.stringify({ query: "probe", scope: "governance" }));
    assertEqual((await readError())?.code, undefined, "readonly search allowed");
    ok("READONLY knowledge.read search allowed");

    // 3. Unregistered operation -> contract refusal.
    await persistRecordKbAction(DEMO, ACT_SEARCH, "destroyProjection");
    assertEqual((await readError())?.code, "KB_UNSUPPORTED_OPERATION", "unregistered operation");
    ok("unregistered operation -> KB_UNSUPPORTED_OPERATION");

    // 4. View-binding gate: SOURCE-PAUSE invoked via REVIEW view control.
    await persistRecordKbAction(DEMO, VIEW_BINDING_CONTROL, "pauseKnowledgeSource", JSON.stringify({ source_id: "SRC-x", expected_version: 1, reason: "binding probe", idempotency_key: idem("binding") }));
    assertEqual((await readError())?.code, "KB_UNSUPPORTED_OPERATION", "view-binding gate");
    ok("view-binding gate rejects foreign control/action pair");

    // 5. Source create: required fields gate.
    await persistRecordKbAction(DEMO, ACT_SOURCE_CREATE, "createKnowledgeSource", JSON.stringify({ source_type: "WEB", scope: "governance", rights: "PUBLIC", classification: "公開", collection_method: "WEB_FETCH", freshness_policy: "DAILY", retention_policy: "PERSIST", idempotency_key: idem("missing") }));
    assertEqual((await readError())?.code, "KB_SCOPE_INVALID", "missing name gate");
    ok("missing required source field -> KB_SCOPE_INVALID");

    // 6. Source create success -> DRAFT.
    await persistRecordKbAction(DEMO, ACT_SOURCE_CREATE, "createKnowledgeSource", JSON.stringify({ name: "ACPOS Fixture Docs", source_type: "WEB", scope: "governance", rights: "PUBLIC", classification: "公開", collection_method: "WEB_CRAWL", freshness_policy: "DAILY", retention_policy: "PERSIST", collection_config: { seed_url_or_query: `${base}/doc1`, same_domain_only: true, max_depth: 2, max_pages: 5 }, idempotency_key: "idem-kbtest-create1-fixed" }));
    assertEqual((await readError())?.code, undefined, "source create clears error");
    let sources = await readRegistry<SourceRow>(KB_STATE_SOURCES_UID);
    assertEqual(sources.length, 1, "one source registered");
    assertEqual(sources[0].status, "DRAFT", "new source starts DRAFT");
    ok("source created in DRAFT state");

    // 7. Idempotent replay: same key must not duplicate.
    await persistRecordKbAction(DEMO, ACT_SOURCE_CREATE, "createKnowledgeSource", JSON.stringify({ name: "ACPOS Fixture Docs", source_type: "WEB", scope: "governance", rights: "PUBLIC", classification: "公開", collection_method: "WEB_CRAWL", freshness_policy: "DAILY", retention_policy: "PERSIST", idempotency_key: "idem-kbtest-create1-fixed" }));
    sources = await readRegistry<SourceRow>(KB_STATE_SOURCES_UID);
    assertEqual(sources.length, 1, "idempotent replay does not duplicate");
    assertEqual(Object.keys(JSON.parse((await readState(KB_STATE_IDEMPOTENCY_UID)) ?? "{}")).length >= 1, true, "idempotency registry populated");
    ok("idempotency replay recorded without side effect");

    // 8. Raw secret forbidden.
    await persistRecordKbAction(DEMO, ACT_SOURCE_CREATE, "createKnowledgeSource", JSON.stringify({ name: "x2", source_type: "WEB", scope: "governance", rights: "PUBLIC", classification: "公開", collection_method: "WEB_FETCH", freshness_policy: "DAILY", retention_policy: "PERSIST", raw_secret: "hunter2", idempotency_key: idem("secret") }));
    assertEqual((await readError())?.code, "KB_RAW_SECRET_FORBIDDEN", "raw secret gate");
    ok("raw_secret rejected with KB_RAW_SECRET_FORBIDDEN");

    // 9. Source save version conflict.
    await persistRecordKbAction(DEMO, ACT_SOURCE_SAVE, "updateKnowledgeSource", JSON.stringify({ source_id: sources[0].sourceId, expected_version: 9, name: "Renamed", idempotency_key: idem("save-conflict") }));
    assertEqual((await readError())?.code, "KB_VERSION_CONFLICT", "save version conflict");
    ok("stale expected_version -> KB_VERSION_CONFLICT");

    // 10. Source save success -> ACTIVE.
    await persistRecordKbAction(DEMO, ACT_SOURCE_SAVE, "updateKnowledgeSource", JSON.stringify({ source_id: sources[0].sourceId, expected_version: 1, name: "ACPOS Fixture Docs", scope: "governance", rights: "PUBLIC", classification: "公開", freshness_policy: "DAILY", retention_policy: "PERSIST", idempotency_key: idem("save1") }));
    sources = await readRegistry<SourceRow>(KB_STATE_SOURCES_UID);
    assertEqual(sources[0].status, "ACTIVE", "save activates source");
    assertEqual(sources[0].version, 2, "save bumps version");
    ok("source save -> ACTIVE, version bumped");

    // 11. Ingest retry without failed run -> not retryable.
    await persistRecordKbAction(DEMO, ACT_INGEST_RETRY, "retryAcquisitionJob", JSON.stringify({ run_id: "RUN-missing", failure_ref: "probe", idempotency_key: idem("retry-missing") }));
    assertEqual((await readError())?.code, "KB_SCOPE_INVALID", "retry unknown run");
    ok("retry on unknown run -> KB_SCOPE_INVALID");

    // 12. Ingest start: real crawl of local fixture (depth 2).
    await persistRecordKbAction(DEMO, ACT_INGEST_START, "createAcquisitionJob", JSON.stringify({ source_ref: sources[0].sourceId, scope: "governance", run_type: "WEB_CRAWL", idempotency_key: idem("crawl1") }));
    assertEqual((await readError())?.code, undefined, "ingest completed without error");
    let runs = await readRegistry<RunRow>(KB_STATE_RUNS_UID);
    assertEqual(runs.length, 1, "one run registered");
    assertEqual(runs[0].status, "COMPLETED", "run completed");
    assert(runs[0].itemCount >= 2, `crawl collected doc1+doc2 (${runs[0].itemCount})`);
    const results = await readRegistry<Record<string, string>>(KB_STATE_RESULTS_UID);
    assert(results.length >= 2, `results registry written (${results.length})`);
    assert(results.every((row) => row.classification_type === "EVIDENCE" && row.source_version), "results carry contract fields");
    const citations = await readRegistry<Record<string, string>>(KB_STATE_CITATIONS_UID);
    assert(citations.length >= 2, `citations registry written (${citations.length})`);
    const blocked = results.some((row) => String(row.source_ref).includes("/secret"));
    assertEqual(blocked, false, "robots-disallowed page excluded");
    ok("WEB_CRAWL run completed; robots disallow excluded");

    // 13. Experience capture: REAL_EXECUTION_ONLY from run items.
    const experience = await readRegistry<Record<string, unknown>>(KB_STATE_EXPERIENCE_UID);
    assert(experience.length >= 2, `experience captured from real run (${experience.length})`);
    assert(experience.every((record) => record.state === "OUTCOME_COMPLETE" && record.run_id === runs[0].runId), "experience records traceable to run");
    ok("experience registry populated from real crawl");

    // 14. Second ingest on same source (previous run completed) still allowed.
    await persistRecordKbAction(DEMO, ACT_INGEST_START, "createAcquisitionJob", JSON.stringify({ source_ref: sources[0].sourceId, scope: "governance", run_type: "WEB_FETCH", idempotency_key: idem("fetch1") }));
    runs = await readRegistry<RunRow>(KB_STATE_RUNS_UID);
    assertEqual(runs[1].status, "COMPLETED", "second run completed");
    assertEqual(runs[1].itemCount, 1, "WEB_FETCH single page");
    ok("WEB_FETCH run completed with single item");

    // 15. Context add from real result ref.
    const realRef = results[0].source_ref;
    await persistRecordKbAction(DEMO, ACT_CONTEXT_ADD, "addContextDraftItem", JSON.stringify({ ref: realRef }));
    let basket = await readRegistry<{ ref: string }>(KB_STATE_BASKET_UID);
    assertEqual(basket.length, 1, "basket holds ref");
    // 16. Context add untraceable ref -> citation gate on create.
    await persistRecordKbAction(DEMO, ACT_CONTEXT_ADD, "addContextDraftItem", JSON.stringify({ ref: "https://untraceable.example/no-evidence" }));
    await persistRecordKbAction(DEMO, ACT_CONTEXT_CREATE, "createContextCandidate", JSON.stringify({ purpose: "Probe", scope: "governance", evidence_refs: ["CIT-fixture"], idempotency_key: idem("ctx-probe") }));
    assertEqual((await readError())?.code, "KB_CITATION_REQUIRED", "citation gate");
    ok("untraceable context -> KB_CITATION_REQUIRED");
    // 17. Remove untraceable, create candidate with traceable basket.
    await persistRecordKbAction(DEMO, ACT_CONTEXT_REMOVE, "removeContextDraftItem", JSON.stringify({ ref: "https://untraceable.example/no-evidence" }));
    basket = await readRegistry<{ ref: string }>(KB_STATE_BASKET_UID);
    assertEqual(basket.length, 1, "untraceable ref removed");
    await persistRecordKbAction(DEMO, ACT_CONTEXT_CREATE, "createContextCandidate", JSON.stringify({ purpose: "Governance probe", scope: "governance", evidence_refs: ["CIT-fixture"], idempotency_key: idem("ctx-real") }));
    assertEqual((await readError())?.code, undefined, "candidate created");
    const candidates = await readRegistry<Record<string, unknown>>(KB_STATE_CANDIDATES_UID);
    assertEqual(candidates.length, 1, "one candidate");
    assertEqual(candidates[0].state, "READY_FOR_CONSUMER_REVIEW", "candidate state");
    assertEqual((await readRegistry<{ ref: string }>(KB_STATE_BASKET_UID)).length, 0, "basket cleared after candidate");
    ok("context candidate READY_FOR_CONSUMER_REVIEW; basket cleared");

    // 18. Replay open unknown experience -> gate; known -> registry.
    await persistRecordKbAction(DEMO, ACT_REPLAY_OPEN, "getExperienceReplay", JSON.stringify({ experience_id: "EXP-missing" }));
    assertEqual((await readError())?.code, "KB_PERMISSION_DENIED", "replay unknown id");
    const experienceId = String(experience[0].experience_id);
    await persistRecordKbAction(DEMO, ACT_REPLAY_OPEN, "getExperienceReplay", JSON.stringify({ experience_id: experienceId }));
    assertEqual((await readError())?.code, undefined, "replay opens");
    assertEqual(String(JSON.parse((await readState(KB_STATE_REPLAY_UID)) ?? "{}").experience_id), experienceId, "replay registry written");
    ok("experience replay projection written");

    // 19. Replay compare needs >= 2 records.
    await persistRecordKbAction(DEMO, ACT_REPLAY_COMPARE, "compareExperienceReplay", JSON.stringify({ experience_id: experienceId, compare_refs: [experienceId] }));
    assertEqual((await readError())?.code, "KB_LINEAGE_INCOMPLETE", "compare lineage gate");
    await persistRecordKbAction(DEMO, ACT_REPLAY_COMPARE, "compareExperienceReplay", JSON.stringify({ experience_id: experienceId, compare_refs: [experienceId, String(experience[1].experience_id)] }));
    const replay = JSON.parse((await readState(KB_STATE_REPLAY_UID)) ?? "{}") as { compare_mode: string; records: unknown[] };
    assertEqual(replay.records.length, 2, "compare records");
    ok("replay compare with two records");

    // 20. Learning gate: missing limitations -> schema refusal; fake experience ref -> OUTCOME_PENDING.
    await persistRecordKbAction(DEMO, ACT_LEARNING_CREATE, "createLearningCandidate", JSON.stringify({ scope: "governance", pattern: "p", proposed_improvement: "i", experience_refs: ["EXP-fake"], idempotency_key: idem("learn-schema") }));
    assertEqual((await readError())?.code, "KB_SCOPE_INVALID", "learning schema requires limitations");
    ok("learning request schema requires limitations (contract)");
    await persistRecordKbAction(DEMO, ACT_LEARNING_CREATE, "createLearningCandidate", JSON.stringify({ scope: "governance", pattern: "p", proposed_improvement: "i", limitations: "probe", experience_refs: ["EXP-fake"], idempotency_key: idem("learn-fake") }));
    assertEqual((await readError())?.code, "KB_OUTCOME_PENDING", "learning outcome gate");
    await persistRecordKbAction(DEMO, ACT_LEARNING_CREATE, "createLearningCandidate", JSON.stringify({ scope: "governance", pattern: "Crawl same-domain only", proposed_improvement: "Raise depth cap for fixture docs", limitations: "Probe fixture scope only", experience_refs: [experienceId], idempotency_key: idem("learn-real") }));
    assertEqual((await readError())?.code, undefined, "learning created");
    const learning = await readRegistry<Record<string, unknown>>(KB_STATE_LEARNING_UID);
    assertEqual(learning.length, 1, "learning registered");
    assertEqual(learning[0].state, "DRAFT", "learning DRAFT");
    ok("learning candidate created from real experience");

    // 21. Draft from experience.
    await persistRecordKbAction(DEMO, ACT_DRAFT_FROM_EXP, "createKnowledgeDraftFromExperience", JSON.stringify({ scope: "governance", knowledge_type: "GUIDE", title_seed: "Fixture guide", experience_refs: [experienceId], idempotency_key: idem("draft-exp") }));
    let drafts = await readRegistry<Record<string, unknown>>(KB_STATE_DRAFTS_UID);
    assertEqual(drafts.length, 1, "draft registered");
    assertEqual(drafts[0].state, "DRAFT", "draft DRAFT");
    ok("knowledge draft created from experience");

    // 22. Draft save version conflict.
    const knowledgeId = String(drafts[0].knowledge_id);
    await persistRecordKbAction(DEMO, ACT_DRAFT_SAVE, "saveKnowledgeDraft", JSON.stringify({ knowledge_id: knowledgeId, expected_version: 99, title: "T", knowledge_type: "GUIDE", scope: "governance", classification: "公開", idempotency_key: idem("draft-conflict") }));
    assertEqual((await readError())?.code, "KB_VERSION_CONFLICT", "draft version conflict");
    ok("draft save stale version -> KB_VERSION_CONFLICT");

    // 23. Backend service transition DRAFT -> REVIEW (ACPOSKnowledgeService).
    drafts = await readRegistry<Record<string, unknown>>(KB_STATE_DRAFTS_UID);
    drafts[0].state = "REVIEW";
    await client.run("UPDATE ghsn_kb_field_projection SET value_text = ? WHERE control_uid = ?", [JSON.stringify(drafts), KB_STATE_DRAFTS_UID]);

    // 24. Approve without mandatory checks -> review gate.
    await persistRecordKbAction(DEMO, ACT_APPROVE, "approveKnowledgeDraft", JSON.stringify({ knowledge_id: knowledgeId, expected_version: 1, review_rationale: "probe", mandatory_check_results: { truth_verified: false }, idempotency_key: idem("approve-partial") }));
    assertEqual((await readError())?.code, "KB_REVIEW_CHECK_INCOMPLETE", "mandatory check gate");
    ok("approve with incomplete checks -> KB_REVIEW_CHECK_INCOMPLETE");

    // 25. Approve with all checks -> APPROVED.
    await persistRecordKbAction(DEMO, ACT_APPROVE, "approveKnowledgeDraft", JSON.stringify({ knowledge_id: knowledgeId, expected_version: 1, review_rationale: "All checks verified against fixture evidence", mandatory_check_results: { truth_verified: true, citation_complete: true, scope_valid: true, rights_valid: true }, idempotency_key: idem("approve-full") }));
    assertEqual((await readError())?.code, undefined, "approve clears error");
    drafts = await readRegistry<Record<string, unknown>>(KB_STATE_DRAFTS_UID);
    assertEqual(drafts[0].state, "APPROVED", "draft approved");
    assertEqual(String(drafts[0].reviewed_by), DEMO, "reviewer recorded");
    ok("human review approves draft with rationale");

    // 26. Source lifecycle: pause blocks ingest; resume restores; retire blocks.
    await persistRecordKbAction(DEMO, ACT_SOURCE_PAUSE, "pauseKnowledgeSource", JSON.stringify({ source_id: sources[0].sourceId, expected_version: sources[0].version, reason: "probe pause", idempotency_key: idem("pause") }));
    sources = await readRegistry<SourceRow>(KB_STATE_SOURCES_UID);
    assertEqual(sources[0].status, "PAUSED", "source paused");
    await persistRecordKbAction(DEMO, ACT_INGEST_START, "createAcquisitionJob", JSON.stringify({ source_ref: sources[0].sourceId, scope: "governance", run_type: "WEB_FETCH", idempotency_key: idem("ingest1") }));
    assertEqual((await readError())?.code, "KB_SOURCE_RIGHTS_INVALID", "ingest blocked while paused");
    await persistRecordKbAction(DEMO, ACT_SOURCE_RESUME, "resumeKnowledgeSource", JSON.stringify({ source_id: sources[0].sourceId, expected_version: sources[0].version, reason: "probe resume", idempotency_key: idem("resume") }));
    sources = await readRegistry<SourceRow>(KB_STATE_SOURCES_UID);
    assertEqual(sources[0].status, "ACTIVE", "source resumed");
    await persistRecordKbAction(DEMO, ACT_SOURCE_RETIRE, "retireKnowledgeSource", JSON.stringify({ source_id: sources[0].sourceId, expected_version: sources[0].version, reason: "probe retire", idempotency_key: idem("retire") }));
    sources = await readRegistry<SourceRow>(KB_STATE_SOURCES_UID);
    assertEqual(sources[0].status, "RETIRED", "source retired");
    await persistRecordKbAction(DEMO, ACT_INGEST_START, "createAcquisitionJob", JSON.stringify({ source_ref: sources[0].sourceId, scope: "governance", run_type: "WEB_FETCH", idempotency_key: idem("ingest2") }));
    assertEqual((await readError())?.code, "KB_SOURCE_RIGHTS_INVALID", "ingest blocked after retire");
    ok("source lifecycle pause/resume/retire enforced");

    // 27. Source rights invalid: source without seed config cannot ingest.
    await persistRecordKbAction(DEMO, ACT_SOURCE_CREATE, "createKnowledgeSource", JSON.stringify({ name: "No Seed", source_type: "WEB", scope: "governance", rights: "PUBLIC", classification: "公開", collection_method: "WEB_FETCH", freshness_policy: "DAILY", retention_policy: "PERSIST", idempotency_key: idem("noseed") }));
    sources = await readRegistry<SourceRow>(KB_STATE_SOURCES_UID);
    const noSeed = sources.find((s) => s.name === "No Seed");
    await persistRecordKbAction(DEMO, ACT_SOURCE_SAVE, "updateKnowledgeSource", JSON.stringify({ source_id: noSeed?.sourceId, expected_version: 1, idempotency_key: idem("noseed-save") }));
    await persistRecordKbAction(DEMO, ACT_INGEST_START, "createAcquisitionJob", JSON.stringify({ source_ref: noSeed?.sourceId, scope: "governance", run_type: "WEB_FETCH", idempotency_key: idem("ingest3") }));
    assertEqual((await readError())?.code, "KB_SOURCE_RIGHTS_INVALID", "missing seed gate");
    ok("source without seed_url -> KB_SOURCE_RIGHTS_INVALID");

    // 28. Search: approved knowledge included with __kind (KBSearchRequest requires query+scope).
    await persistRecordKbAction(DEMO, ACT_SEARCH_GLOBAL, "searchKnowledge", JSON.stringify({ query: "fixture" }));
    assertEqual((await readError())?.code, "KB_SCOPE_INVALID", "search schema requires scope");
    ok("KBSearchRequest scope required (contract)");
    await persistRecordKbAction(DEMO, ACT_SEARCH_GLOBAL, "searchKnowledge", JSON.stringify({ query: "fixture", scope: "governance" }));
    const searched = await readRegistry<Record<string, string>>(KB_STATE_RESULTS_UID);
    assert(searched.some((row) => row.__kind === "APPROVED_KNOWLEDGE"), "approved knowledge searchable");
    ok("global search matches approved knowledge");

    // 29. Citation open: unknown -> gate (contract E:001); real citation id -> registry.
    await persistRecordKbAction(DEMO, ACT_CITATION_OPEN, "getCitation", JSON.stringify({ citation_id: "CIT-missing" }));
    assertEqual((await readError())?.code, "KB_PERMISSION_DENIED", "citation unknown");
    await persistRecordKbAction(DEMO, ACT_CITATION_OPEN, "getCitation", JSON.stringify({ citation_id: citations[0].citation_id }));
    const cited = JSON.parse((await readState(KB_STATE_CITATIONS_UID)) ?? "[]") as Array<Record<string, string>>;
    assertEqual(cited.length, 1, "citation registry narrowed to found");
    ok("citation lookup verified");

    // 30. Version compare: unknown draft -> gate.
    await persistRecordKbAction(DEMO, ACT_VERSION_COMPARE, "compareKnowledgeVersions", JSON.stringify({ knowledge_id: "KN-missing", left_version: "1", right_version: "2" }));
    assertEqual((await readError())?.code, "KB_SCOPE_INVALID", "version compare unknown");
    ok("version compare gate for unknown draft");

    // 31. Return / reject paths on fresh drafts (Approved Knowledge is immutable).
    const makeReviewDraft = async (tag: string): Promise<string> => {
      await persistRecordKbAction(DEMO, ACT_DRAFT_FROM_EXP, "createKnowledgeDraftFromExperience", JSON.stringify({ scope: "governance", knowledge_type: "GUIDE", title_seed: `Fixture guide ${tag}`, experience_refs: [experienceId], idempotency_key: idem(`draft-${tag}`) }));
      const registry = await readRegistry<Record<string, unknown>>(KB_STATE_DRAFTS_UID);
      const last = registry[registry.length - 1];
      last.state = "REVIEW";
      await client.run("UPDATE ghsn_kb_field_projection SET value_text = ? WHERE control_uid = ?", [JSON.stringify(registry), KB_STATE_DRAFTS_UID]);
      return String(last.knowledge_id);
    };
    const returnId = await makeReviewDraft("return");
    await persistRecordKbAction(DEMO, ACT_RETURN, "returnKnowledgeDraft", JSON.stringify({ knowledge_id: returnId, expected_version: 1, review_rationale: "Needs more evidence", idempotency_key: idem("return-nocheck") }));
    assertEqual((await readError())?.code, "KB_REVIEW_CHECK_INCOMPLETE", "review schema requires mandatory_check_results");
    ok("ReviewKnowledgeDraftRequest mandatory_check_results required (contract)");
    await persistRecordKbAction(DEMO, ACT_RETURN, "returnKnowledgeDraft", JSON.stringify({ knowledge_id: returnId, expected_version: 1, review_rationale: "Needs more evidence", mandatory_check_results: { checklist_reviewed: true }, idempotency_key: idem("return") }));
    drafts = await readRegistry<Record<string, unknown>>(KB_STATE_DRAFTS_UID);
    assertEqual(drafts.find((d) => String(d.knowledge_id) === returnId)?.state, "RETURNED", "draft returned");
    const rejectId = await makeReviewDraft("reject");
    await persistRecordKbAction(DEMO, ACT_REJECT, "rejectKnowledgeDraft", JSON.stringify({ knowledge_id: rejectId, expected_version: 1, review_rationale: "Duplicate of canon", mandatory_check_results: { duplicate_check: true }, idempotency_key: idem("reject") }));
    drafts = await readRegistry<Record<string, unknown>>(KB_STATE_DRAFTS_UID);
    assertEqual(drafts.find((d) => String(d.knowledge_id) === rejectId)?.state, "REJECTED", "draft rejected");
    ok("return and reject review paths enforced");

    // 30. Contract request-schema gates (KB-01 locked encoding).
    // SourceStateChangeRequest: source_id + expected_version + reason required.
    const pauseSource = JSON.parse((await readState(KB_STATE_SOURCES_UID)) ?? "[]").find(
      (s: Record<string, unknown>) => s.name === "No Seed",
    ) as Record<string, unknown> | undefined;
    await persistRecordKbAction(DEMO, ACT_SOURCE_PAUSE, "pauseKnowledgeSource", JSON.stringify({ source_id: pauseSource?.sourceId, expected_version: pauseSource?.version, idempotency_key: idem("pause-noreason") }));
    assertEqual((await readError())?.code, "KB_SCOPE_INVALID", "state change schema requires reason");
    ok("SourceStateChangeRequest reason required (contract)");
    await persistRecordKbAction(DEMO, ACT_SOURCE_PAUSE, "pauseKnowledgeSource", JSON.stringify({ source_id: pauseSource?.sourceId, expected_version: pauseSource?.version, reason: "probe", idempotency_key: idem("pause-real") }));
    assertEqual((await readError())?.code, undefined, "pause applied");
    const pausedSource = JSON.parse((await readState(KB_STATE_SOURCES_UID)) ?? "[]").find(
      (s: Record<string, unknown>) => s.sourceId === pauseSource?.sourceId,
    ) as Record<string, unknown> | undefined;
    await persistRecordKbAction(DEMO, ACT_SOURCE_RESUME, "resumeKnowledgeSource", JSON.stringify({ source_id: pausedSource?.sourceId, expected_version: pausedSource?.version, reason: "probe", idempotency_key: idem("resume-real") }));
    assertEqual((await readError())?.code, undefined, "resume applied");
    ok("pause/resume honored with reason");

    // 31. CreateACPOSContextCandidateRequest requires evidence_refs.
    await persistRecordKbAction(DEMO, ACT_CONTEXT_CREATE, "createContextCandidate", JSON.stringify({ purpose: "probe", scope: "governance", selected_refs: ["https://fixture.example/a"], idempotency_key: idem("ctx-noevidence") }));
    assertEqual((await readError())?.code, "KB_SCOPE_INVALID", "context schema requires evidence_refs");
    ok("context candidate evidence_refs required (contract)");

    // 32. CreateKnowledgeDraftFromExperienceRequest requires experience_refs.
    await persistRecordKbAction(DEMO, ACT_DRAFT_FROM_EXP, "createKnowledgeDraftFromExperience", JSON.stringify({ scope: "governance", knowledge_type: "GUIDE", idempotency_key: idem("draft-norefs") }));
    assertEqual((await readError())?.code, "KB_SCOPE_INVALID", "draft schema requires experience_refs");
    ok("draft from experience requires experience_refs (contract)");

    // 33. CompareKnowledgeVersionsRequest is READ_COMPARE: no idempotency_key needed.
    await persistRecordKbAction(DEMO, ACT_VERSION_COMPARE, "compareKnowledgeVersions", JSON.stringify({ knowledge_id: String(drafts[0].knowledge_id), left_version: "1", right_version: "2" }));
    assertEqual((await readError())?.code, undefined, "version compare without idempotency_key");
    ok("READ_COMPARE version compare accepts payload without idempotency_key");

    // 32. Read model: fields include all STATE keys; account separation lives in
    // the permission table (page reachability is site-wide by design; effectful
    // scope enforcement is the runtime gate layer, proven by assertion 1).
    const model = await persistGetKbReadModel(DEMO);
    assertEqual(model.authorized, true, "demo authorized");
    const modelUids = new Set(model.fields.map((field) => field.controlUid));
    for (const uid of STATE_KEYS) assert(modelUids.has(uid), `read model includes ${uid}`);
    const readonlyRows = await getSqlClient().all<{ n: number }>(
      "SELECT count(*)::int AS n FROM ghsn_account_kb_permission WHERE account_uid = ?",
      [READONLY],
    );
    assertEqual(Number(readonlyRows[0]?.n ?? 0), 1, "readonly holds exactly knowledge.read");
    ok("read model projection + permission table separation");

    // 33. Audit trail present.
    const auditRaw = (await readState(KB_STATE_AUDIT_UID)) ?? "";
    assert(auditRaw.includes("approveKnowledgeDraft") && auditRaw.includes("IDEMPOTENT-REPLAY"), "audit records actions and replays");
    ok("audit trail records actions and idempotent replays");
  } finally {
    server.close();
  }

  console.log(`KB-01 workspace: ${passed} assertions passed`);
}

main()
  .then(() => process.exit(0))
  .catch((error: unknown) => {
    console.error(error);
    process.exit(1);
  });
