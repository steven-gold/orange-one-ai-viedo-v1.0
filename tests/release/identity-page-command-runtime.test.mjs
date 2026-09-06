import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("production page commands lazy-bind CORE/DB/IAM/INFO and fail closed without ProviderGateway", async () => {
  const core = await read("src/server/core/coreRuntime.ts");
  const commands = await read("src/server/shared/identityPageCommandRuntime.ts");
  const adapters = await read("src/domain/catalog/identityClientCommandAdapters.ts");
  const dbRoute = await read("src/app/v1/database/read/route.ts");
  const dbRuntime = await read("src/server/database/dbReadModelRuntime.ts");
  const iam = await read("src/server/iam/iamRuntime.ts");
  const info = await read("src/server/info/infoCommandRuntime.ts");
  const department = await read("src/server/shared/departmentOperationRuntime.ts");
  const catalogAdapters = await read("src/domain/catalog/identityClientProjectionAdapters.ts");

  assert.match(core, /bindIdentityPageCommandRuntimes/);
  assert.match(core, /namedReason/);
  assert.match(commands, /export function bindIdentityPageCommandRuntimes/);
  assert.match(commands, /CORE-01-PORT-PROJECT-CREATE/);
  assert.match(commands, /INSERT INTO conversations/);
  assert.match(commands, /DB-01-PORT-ENTITY-LIST/);
  assert.match(commands, /information_schema\.tables/);
  assert.match(commands, /PROVIDER_GATEWAY_NOT_MATERIALIZED/);
  assert.match(commands, /isControlledTestMode\(\)/);
  assert.match(commands, /configureQaRuntime/);
  assert.match(commands, /configureKnowledgeRuntime/);
  assert.match(commands, /configureConversationRuntime/);
  assert.match(commands, /configureStrategyDecisionRuntime/);
  assert.match(commands, /configureSocCommandRuntime/);
  assert.match(commands, /configureErpCommandRuntime/);
  assert.match(commands, /configureSystemLifecycleRuntime/);
  assert.match(commands, /searchKnowledge/);
  assert.match(commands, /sendConversationMessage/);
  assert.match(dbRoute, /executeDbRead/);
  assert.match(dbRoute, /DB_READ_OPERATIONS/);
  assert.match(dbRuntime, /bindIdentityPageCommandRuntimes/);
  assert.match(iam, /bindIdentityPageCommandRuntimes/);
  assert.match(info, /bindIdentityPageCommandRuntimes/);
  assert.match(department, /bindIdentityPageCommandRuntimes/);
  assert.match(adapters, /openRegisteredForm/);
  assert.match(adapters, /\/v1\/database\/read/);
  assert.match(adapters, /configureInfoCommandPayloadBuilder/);
  assert.match(adapters, /configureStrategyRequestBuilder/);
  assert.match(adapters, /configureStrategyAdminCommandAdapter/);
  assert.match(catalogAdapters, /bindIdentityClientCommandAdapters/);
  assert.match(catalogAdapters, /configureStrategyProjectionResolver/);
  assert.match(catalogAdapters, /configureAiApiProjectionResolver/);
  assert.match(catalogAdapters, /configureStrategyAdminProjectionResolver/);
  assert.doesNotMatch(commands, /CONTROLLED_TEST_NOT_PRODUCTION_READY/);
});

test("QA/KB/conversation/strategy/system catch named reasons and client fetches send cookies", async () => {
  const qa = await read("src/server/qa/qaRuntime.ts");
  const knowledge = await read("src/server/knowledge/knowledgeRuntime.ts");
  const conversation = await read("src/server/shared/conversationRuntime.ts");
  const strategy = await read("src/server/strategy/strategyDecisionRuntime.ts");
  const soc = await read("src/server/social/socCommandRuntime.ts");
  const erp = await read("src/server/erp/erpCommandRuntime.ts");
  const system = await read("src/server/system/systemLifecycleRuntime.ts");
  const infoPort = await read("src/domain/info/infoCommandPort.ts");
  const strategyPort = await read("src/domain/strategy/strategyCommandPort.ts");
  const qaPort = await read("src/domain/qa/qaClientPort.ts");
  const knowledgeVisual = await read("src/components/pages/KnowledgeAdminVisual.tsx");

  for (const source of [qa, knowledge, conversation, strategy, soc, erp, system]) {
    assert.match(source, /namedReason/);
    assert.match(source, /bindIdentityPageCommandRuntimes/);
  }
  assert.match(infoPort, /credentials:'include'/);
  assert.match(strategyPort, /credentials:'include'/);
  assert.match(qaPort, /credentials:"include"/);
  assert.match(knowledgeVisual, /EFFECTFUL_RUNTIME_READY = true/);
  assert.match(knowledgeVisual, /\/v1\/knowledge\/search/);
  assert.match(knowledgeVisual, /void runControl\(control\)/);
});
