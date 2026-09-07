import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const adapter = fs.readFileSync("src/domain/catalog/identityClientCommandAdapters.ts", "utf8");
const server = fs.readFileSync("src/server/shared/identityPageCommandRuntime.ts", "utf8");
const port = fs.readFileSync("src/domain/strategyAdmin/strategyAdminRuntimePort.ts", "utf8");
const visual = fs.readFileSync("src/components/pages/StrategyAdminVisual.tsx", "utf8");
const controlled = fs.readFileSync("src/server/testing/controlledStrategyTestRuntime.ts", "utf8");

test("Strategy Admin materialized operations use registered routes with source identity", () => {
  assert.match(adapter, /input\.operation === "searchProjection" \|\| input\.operation === "refreshProjection"/);
  assert.match(adapter, /"\/v1\/search"/);
  assert.match(adapter, /"\/v1\/projections\/refresh"/);
  assert.match(adapter, /input\.operation === "configureGovernedResource" \|\| input\.operation === "approveGovernedResource"/);
  assert.match(adapter, /\/v1\/governance\/resources\//);
  assert.match(adapter, /encodeURIComponent\(resourceId\)/);
  assert.match(adapter, /current_page_uid: "admin:STR-01"/);
  assert.match(adapter, /source_page_uid: input\.source_page_uid/);
});

test("Strategy Admin server authorization checks current page plus exact source action", () => {
  assert.match(server, /CURRENT_PAGE_RESOURCE_KEYS\["admin:STR-01"\]/);
  assert.match(server, /action:admin:STR-01:ACT-SEARCH/);
  assert.match(server, /action:admin:STR-01:ACT-REFRESH/);
  assert.match(server, /action:admin:STR-04:ACT-SEARCH/);
  assert.match(server, /action:admin:STR-02:ACT-CONFIGURE/);
  assert.match(server, /action:admin:STR-02:ACT-APPROVE/);
  assert.match(server, /current_page_uid/);
  assert.match(server, /source_page_uid/);
  assert.match(server, /evaluateResourceAction\(resourceKey, "INVOKE"\)/);
});

test("Strategy Admin marks Search, Refresh, Configure and Approve runtime-ready only", () => {
  assert.match(port, /STRATEGY_ADMIN_MATERIALIZED_OPERATIONS[\s\S]*"searchProjection"[\s\S]*"refreshProjection"[\s\S]*"configureGovernedResource"[\s\S]*"approveGovernedResource"/);
  assert.doesNotMatch(port, /STRATEGY_ADMIN_MATERIALIZED_OPERATIONS[\s\S]*"exportProjection"[\s\S]*\]\);/);
  assert.doesNotMatch(port, /STRATEGY_ADMIN_MATERIALIZED_OPERATIONS[\s\S]*"saveDraft"[\s\S]*\]\);/);
});

test("Strategy Admin materializes registered Search, Refresh, Configure and Approve forms", () => {
  assert.match(visual, /SearchProjectionRequest/);
  assert.match(visual, /RefreshProjectionRequest/);
  assert.match(visual, /ConfigureGovernedResourceRequest/);
  assert.match(visual, /ApproveGovernedResourceRequest/);
  assert.match(visual, /data-effectful-runtime-ready="true"/);
  assert.match(visual, /data-runtime-binding-validation="PARTIAL_SEARCH_REFRESH_CONFIGURE_APPROVE_MATERIALIZED"/);
  assert.match(visual, /data-runtime-materialized-operations="searchProjection,refreshProjection,configureGovernedResource,approveGovernedResource"/);
  assert.match(controlled, /r\.operation === "configureGovernedResource" \|\| r\.operation === "approveGovernedResource"/);
  assert.match(controlled, /sourcePageUid !== "admin:STR-02"/);
});
