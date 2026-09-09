import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(`../../${path}`, import.meta.url), "utf8");

test("Production conversation runtime routes real AI turns through governed AIAPI", async () => {
  const source = await read("src/server/shared/productionConversationAiRuntime.ts");
  assert.match(source, /operation_id:\s*"executeProviderRoute"/);
  assert.match(source, /operation_id:\s*"getProviderRouteDecision"/);
  assert.match(source, /executeTextRoute\([\s\S]{0,1600}?"ACPOS_CONVERSATION"/);
  assert.match(source, /use_case\s*=\s*'ACPOS_TEXT_CHAT'/);
  assert.match(source, /external_request_sent\s*!==\s*true/);
  assert.match(source, /payload\.normalized_result/);
  assert.match(source, /LIMIT 30/);
  assert.match(source, /ACPOS_AI_GOVERNANCE_POLICY_VERSION/);
  assert.match(source, /enforceAcposGovernanceEvidence/);
  assert.match(source, /enforceAcposDecisionConsistency/);
  assert.match(source, /conversation_generation_jobs/);
  assert.match(source, /meeting_participants/);
  assert.match(source, /meeting_rounds/);
  assert.match(source, /meeting_messages/);
  assert.match(source, /'USER'/);
  assert.match(source, /'PROVIDER'/);
  assert.doesNotMatch(source, /GROQ_API_KEY|GOOGLE_GEMINI_API_KEY|DEEPSEEK_API_KEY|OPENROUTER_API_KEY/);
});

test("Conversation generation jobs bind the Current canonical public conversation lineage", async () => {
  const migration = await read("database/migrations/0039_conversation_generation_job_canonical_lineage.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  assert.match(migration, /ALTER COLUMN conversation_id TYPE uuid/);
  assert.match(migration, /ALTER COLUMN user_message_id TYPE uuid/);
  assert.match(migration, /ALTER COLUMN result_message_id TYPE uuid/);
  assert.match(migration, /REFERENCES public\.conversations\(conversation_id\)/);
  assert.match(migration, /REFERENCES public\.conversation_messages\(conversation_message_id\)/);
  assert.match(migration, /CONV0039_CANONICAL_FK_COUNT_MISMATCH/);
  assert.match(migration, /384e62c682f00d7380c22d5c64a66e1a509b59e9d9bb9dd645474bbf689d6b9d/);
  assert.match(manifest, /0039_conversation_generation_job_canonical_lineage[\s\S]*d8e75fcbfafafab8a49155b5e3d44dc4e06651f9e775d105fcf22ca06ffd80eb/);
});

test("CORE and shared Strategy conversation sends reuse the same Production AI turn runtime", async () => {
  const source = await read("src/server/shared/identityPageCommandRuntime.ts");
  assert.match(source, /executeProductionConversationTurn/);
  assert.match(source, /case "CORE-01-PORT-MESSAGE-SEND"/);
  assert.match(source, /page_uid:\s*"CORE-01"/);
  assert.match(source, /async function executeConversation/);
  assert.match(source, /page_uid:\s*asText\(payload\.page_uid\) \?\? "workspace:STR-01"/);
});

test("CORE Production UI renders real assistant response and retains controlled-test fallback", async () => {
  const source = await read("src/components/pages/CoreVisual.tsx");
  assert.match(source, /role: "USER" \| "STATUS" \| "SYSTEM" \| "ASSISTANT" \| "SIMULATED_AI"/);
  assert.match(source, /assistant_response_text/);
  assert.match(source, /assistant_response_ref/);
  assert.match(source, /appendConversationMessage\("ASSISTANT"/);
  assert.match(source, /simulated_response_text/);
});

test("CORE canonical projection and conversation payloads are usable without test-only adapters", async () => {
  const projection = await read("src/domain/core/coreProjectionAdapter.ts");
  const conversation = await read("src/domain/core/coreConversationPayloadAdapter.ts");
  assert.match(projection, /if \(!current\) \{\s*return controlledTestProjection\(rawProjection\);\s*\}/);
  assert.match(conversation, /if \(!current\) \{[\s\S]*return \{ ok: true, payload: \{ \.\.\.context \} \};/);
  assert.doesNotMatch(projection, /CORE_PROJECTION_SCHEMA_ADAPTER_NOT_BOUND/);
});

test("Strategy conversation projection exposes persisted user and provider history", async () => {
  const source = await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  assert.match(source, /FROM conversation_messages/);
  assert.match(source, /actorType === "PROVIDER" \? "AI"/);
  assert.match(source, /"STR-01-VIEW-CONVERSATION": conversationText \|\| DASH/);
  assert.match(source, /"STR-01-FLD-ASSISTANT-SUMMARY": latestAssistantSummary \?\? DASH/);
  assert.match(source, /"STR-01-GATE-CONTEXT": Boolean\(firstConversation\)/);
  assert.match(source, /"STR-01-GATE-MESSAGE": Boolean\(firstConversation\)/);
});

test("Strategy send has an exact canonical Production request builder and clears composer after send", async () => {
  const port = await read("src/domain/strategy/strategyCommandPort.ts");
  const ui = await read("src/components/pages/StrategyControlRuntime.tsx");
  assert.match(port, /action==='STR-01-ACT-SEND'/);
  assert.match(port, /path_params:\{conversationId:input\.conversation_id\?\?''\}/);
  assert.match(port, /page_uid:'workspace:STR-01'/);
  assert.match(ui, /isStrategyRequestBuilderBound\(binding\.action_uid as StrategyFormalAction\)/);
  assert.match(ui, /action==='STR-01-ACT-SEND'\|\|action==='STR-01-ACT-STOP'/);
});

test("CORE projection restores persisted messages for each visible thread", async () => {
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const adapter = await read("src/domain/core/coreProjectionAdapter.ts");
  const ui = await read("src/components/pages/CoreVisual.tsx");
  assert.match(projection, /messages_by_thread/);
  assert.match(projection, /FROM conversation_messages/);
  assert.match(projection, /actor_type === "PROVIDER" \? "ASSISTANT"/);
  assert.match(adapter, /messages_by_thread\?/);
  assert.match(ui, /messagesForThread/);
  assert.match(ui, /setConversationMessages\(messagesForThread\(resolved\.projection/);
  assert.match(ui, /setConversationMessages\(messagesForThread\(projection, conversationId/);
});

test("Final Production conversation acceptance proves two real turns and persisted history", async () => {
  const script = await read("scripts/production-conversation-e2e.mjs");
  const workflow = await read(".github/workflows/conversation-acceptance.yml");
  assert.match(script, /assistant_response_text/);
  assert.match(script, /external_request_sent===true/);
  assert.match(script, /worker_succeeded===1/);
  assert.match(script, /What marker did I ask you to remember in the previous turn/);
  assert.match(script, /messages_by_thread/);
  assert.match(script, /\["USER","ASSISTANT","USER","ASSISTANT"\]/);
  assert.match(script, /history_recall=true/);
  assert.match(workflow, /branches:[\s\S]*- new[\s\S]*conversation-acceptance-trigger\.txt/);
  assert.match(workflow, /environment:\s*Production/);
  assert.match(workflow, /scripts\/production-conversation-e2e\.mjs/);
});

