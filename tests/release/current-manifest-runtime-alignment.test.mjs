import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const manifest=await readFile("authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml","utf8");
const identity=await readFile("authority/runtime/ACPOS_PRODUCTION_IDENTITY_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml","utf8");
test("Current manifest and identity runtime agree that the adapter binding is allowed",()=>{
  const block=manifest.match(/production_identity_runtime_contract:([\s\S]*?)wb01_ui_projection_sql_permission_mapping:/);
  assert.ok(block);
  assert.match(block[1],/adapter_bind_allowed:\s*true/);
  assert.match(identity,/^adapter_bind_allowed:\s*true$/m);
});
