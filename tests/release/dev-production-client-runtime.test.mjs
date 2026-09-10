import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const production = readFileSync("src/domain/dev/productionDevClientRuntime.ts", "utf8");
const controlRuntime = readFileSync("src/components/pages/DevControlRuntime.tsx", "utf8");

const supported = [
  "DEV-01-ACT-DISCOVERY-START",
  "DEV-01-ACT-DISCOVERY-PAUSE",
  "DEV-01-ACT-DISCOVERY-RESUME",
  "DEV-01-ACT-DISCOVERY-STOP",
];

test("DEV Production client binds the real projection resolver and only the four materialized discovery commands", () => {
  assert.match(production, /configureDevProjectionResolver\(\{ resolve: normalizeProductionProjection \}\)/);
  assert.match(production, /configureDevCommandAdapter\(/);
  for (const action of supported) assert.match(production, new RegExp(action));
  assert.match(production, /DEV_COMMAND_RUNTIME_NOT_BOUND/);
  assert.match(production, /DEV-01-FLD-JOB-REF/);
});

test("DEV governed controls require per-action client runtime support", () => {
  assert.match(controlRuntime, /isDevClientActionBound\(binding!\.action_uid\)/);
  assert.match(controlRuntime, /formal && !actionRuntimeReady/);
  assert.match(controlRuntime, /DEV_COMMAND_RUNTIME_NOT_BOUND/);
});

test("DEV page-level effectful readiness stays false until all Current effectful bindings are materialized", () => {
  assert.match(controlRuntime, /isDevEffectfulCoverageComplete\(\)/);
  assert.match(production, /effectful\.every\(\(binding\) => PRODUCTION_BOUND_ACTIONS\.has\(binding\.action_uid\)\)/);
});
