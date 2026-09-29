import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = readFile;

const pages = [
  ["CORE", "src/components/pages/CoreVisual.tsx", ["readCoreProjection", "invokeCoreAction", "runServerActionAndSync", "busyAction", "runtimeReason"]],
  ["ASSET", "src/components/pages/AssetControlRuntime.tsx", ["readAssetProjection", "buildAndInvokeAssetAction", "syncProjection", "RUNTIME-ERROR", "busy"]],
  ["VIDEO", "src/components/pages/VideoVisual.tsx", ["readVideoProjection", "invokeVideoAction", "refresh", "runtimeReason", "busy"]],
  ["EDIT", "src/components/pages/EditControlRuntime.tsx", ["readEditProjection", "invokeGovernedEditAction", "syncProjection", "RUNTIME_RESULT", "BUSY"]],
  ["QA", "src/components/pages/QaControlRuntime.tsx", ["readQaProjection", "invokeQaFormalAction", "refreshProjection", "RUNTIME_ERROR", "BUSY"]],
  ["DB", "src/components/pages/DbControlRuntime.tsx", ["readDbProjection", "invokeDbRead", "setRuntimeError", "disabled", "correlationId"]],
  ["STRATEGY", "src/components/pages/StrategyControlRuntime.tsx", ["readStrategyProjection", "buildAndInvokeStrategyAction", "refreshProjection", "RUNTIME_ERROR", "enabled"]],
  ["INFO", "src/components/pages/InfoControlRuntime.tsx", ["readInfoProjection", "buildAndInvokeInfoCommand", "refreshProjection", "RUNTIME_ERROR", "blockedReason"]],
];

test("all frontend page families expose controlled interaction lifecycle", async () => {
  for (const [family, path, markers] of pages) {
    const source = await read(path, "utf8");
    for (const marker of markers) {
      assert.match(source, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `${family} missing ${marker}`);
    }
  }
});

test("frontend page controls publish gate and permission diagnostics", async () => {
  for (const [family, path] of pages) {
    const source = await read(path, "utf8");
    assert.match(source, family === "CORE" ? /data-action-uid|runtimeReason/ : /data-(?:disabled-reason|gate-uid|permission-uid)/, `${family} missing runtime diagnostics`);
  }
});
