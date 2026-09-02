import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const manifest = await readFile("authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml", "utf8");
const system = await readFile("authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml", "utf8");

test("Current Authority contains exactly 18 unique page authorities", () => {
  const pages = [...manifest.matchAll(/^  - (authority\/pages\/[^\n]+)$/gm)].map((match) => match[1]);
  assert.equal(pages.length, 18);
  assert.equal(new Set(pages).size, 18);
  assert.match(manifest, /current_page_count:\s*18/);
});

test("Production Script V1.3 remains the current integration contract", () => {
  assert.match(manifest, /production_script_v1_3:/);
  assert.match(system, /ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1\.3\.yaml/);
  assert.doesNotMatch(manifest, /PRODUCTION_SCRIPT.*V1\.2/);
});

test("System implementation truth is not silently promoted", () => {
  assert.match(system, /api_binding:\s*NOT_EXECUTED/);
  assert.match(system, /database_binding:\s*NOT_EXECUTED/);
  assert.match(system, /deployment:\s*NOT_EXECUTED/);
});
