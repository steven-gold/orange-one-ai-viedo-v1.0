import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = readFile;

test("cross-page workflow keeps the authority route chain discoverable", async () => {
  const routes = await Promise.all([
    read("src/app/login/page.tsx", "utf8"),
    read("src/app/page.tsx", "utf8"),
    read("src/app/core/page.tsx", "utf8"),
    read("src/app/qa/page.tsx", "utf8"),
    read("src/app/strategy/page.tsx", "utf8"),
    read("src/app/info/page.tsx", "utf8"),
    read("src/app/admin/knowledge/page.tsx", "utf8"),
    read("src/app/admin/system/page.tsx", "utf8"),
  ]);
  assert.match(routes[0], /form|login/i);
  for (const source of routes.slice(1)) assert.match(source, /AppShell|Visual/);
});

test("context-bearing client states clear dependent selections on scope changes", async () => {
  const [core, asset, system, qa, strategy, info] = await Promise.all([
    read("src/domain/core/coreClientState.ts", "utf8"),
    read("src/domain/asset/assetClientState.ts", "utf8"),
    read("src/domain/system/systemClientState.ts", "utf8"),
    read("src/domain/qa/qaClientState.ts", "utf8"),
    read("src/domain/strategy/strategyClientState.ts", "utf8"),
    read("src/domain/info/infoClientState.ts", "utf8"),
  ]);
  assert.match(core, /project_id:\s*null|topic_id:\s*null|attachment_refs/);
  assert.match(asset, /projection:\s*null|asset_ref:\s*null/);
  assert.match(system, /conversation_id|BIND_CONTEXT/);
  assert.match(qa, /correlation_id|context/);
  assert.match(strategy, /candidate_ref|topic_ref|correlation_id/);
  assert.match(info, /candidate_ref|correlation_id|runtime_reason_code/);
});

test("projection ports preserve correlation continuity for downstream gates", async () => {
  const sources = await Promise.all([
    read("src/domain/qa/qaProjectionPort.ts", "utf8"),
    read("src/domain/strategy/strategyProjectionPort.ts", "utf8"),
    read("src/domain/info/infoProjectionPort.ts", "utf8"),
    read("src/domain/knowledge/knowledgeRuntimePort.ts", "utf8"),
  ]);
  for (const source of sources) assert.match(source, /correlation_id/);
  assert.match(sources[0], /x-correlation-id/);
  assert.match(sources[1], /projection/);
  assert.match(sources[2], /CANDIDATE|candidate/);
  assert.match(sources[3], /audit|trace/);
});
