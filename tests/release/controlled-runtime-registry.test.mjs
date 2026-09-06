import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("controlled runtime registry covers every current page family and shared operation", async () => {
  const source = await read("src/server/testing/controlledRuntimeRegistry.ts");
  for (const pageUid of [
    "CORE-01", "ASSET-01", "VIDEO-01", "EDIT-01", "QA-01", "admin:DB-01",
    "workspace:STR-01", "workspace:INFO-01", "admin:SYS-01", "admin:IAM-01",
    "admin:DEV-01", "admin:SOC-01", "admin:ERP-01", "admin:AIAPI-01",
    "admin:SG-02", "admin:KB-01",
  ]) assert.match(source, new RegExp(`page_uids: \\[\\"[^\\]]*${pageUid.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`));
  for (const family of ["CONVERSATION", "CANDIDATE", "DEPARTMENT"]) assert.match(source, new RegExp(`family: \\"${family}\\"`));
  assert.match(source, /isControlledTestMode\(\)/);
  assert.match(source, /createControlledTestMetadata/);
});

test("controlled runtime registry marks every registration test-only", async () => {
  const source = await read("src/server/testing/controlledRuntimeRegistry.ts");
  assert.doesNotMatch(source, /production_eligible:\s*true/);
  assert.match(source, /test_only: true/);
  assert.match(source, /return isControlledTestMode\(\) \? createControlledTestMetadata/);
});
