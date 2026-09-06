import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = readFile;
const pages = [
  ["SYS", "src/components/pages/SystemVisual.tsx", ["readSystemProjection", "data-action-uid", "data-permission-uid", "ProjectionState"]],
  ["IAM", "src/components/pages/IamVisual.tsx", ["IamRuntimeProvider", "invokeIamControl", "data-disabled-reason", "audit"]],
  ["DEV", "src/components/pages/DevVisual.tsx", ["DevRuntimeProvider", "runtimeErrorUid", "phaseDisplay", "audit"]],
  ["SOC", "src/components/pages/SocVisual.tsx", ["SocRuntimeProvider", "SocGovernedButton", "projection"]],
  ["ERP", "src/components/pages/ErpVisual.tsx", ["ErpRuntimeProvider", "invoke", "data-disabled-reason", "runtimeError"]],
  ["AIAPI", "src/components/pages/AiApiVisual.tsx", ["readAiApiProjection", "REMAP_REQUIRED_NOT_EXECUTED", "data-disabled-reason", "runtimeError"]],
  ["SG-02", "src/components/pages/QaCriteriaVisual.tsx", ["readQaCriteriaProjection", "configureQaCriteriaResource", "approveQaCriteriaResource", "runtimeError"]],
  ["ADMIN-STRATEGY", "src/components/pages/StrategyAdminVisual.tsx", ["StrategyAdminRuntimeProvider", "useStrategyAdminRuntime", "data-disabled-reason", "runtimeError"]],
  ["KB", "src/components/pages/KnowledgeAdminVisual.tsx", ["readKnowledgeProjection", "getKnowledgeActionTrace", "data-blocked-reason", "runtimeError"]],
];

test("all admin page families expose controlled or fail-closed interaction paths", async () => {
  for (const [family, path, markers] of pages) {
    const source = await read(path, "utf8");
    for (const marker of markers) {
      assert.match(source, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `${family} missing ${marker}`);
    }
  }
});

test("admin pages expose operation outcome or audit diagnostics", async () => {
  for (const [family, path] of pages) {
    const source = await read(path, "utf8");
    assert.match(source, /audit|correlation|runtimeError|disabled-reason/, `${family} missing outcome diagnostics`);
  }
});
