import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0047 canonical script materializer follows Current exact request and no implicit latest",async()=>{
  const migration=await read("database/migrations/0047_canonical_script_version_runtime.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"7f9a709236c13482b67deeb63d09085eadcde1a0ae05920d39a31b0e67b8e19f");
  assert.ok(manifest.includes("7f9a709236c13482b67deeb63d09085eadcde1a0ae05920d39a31b0e67b8e19f"));
  const ceiling=Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\\d+)/)?.[1]??0);
  assert.ok(ceiling>=47,`migration ceiling must include 0047, found ${ceiling}`);
  assert.match(migration,/create_canonical_script_version/);
  assert.match(migration,/api:createCanonicalScriptVersion/);
  assert.match(migration,/script\.version_created/);
  assert.match(migration,/request_idempotency_key_hash/);
  assert.match(migration,/WHERE topic_id=p_topic_id AND version_no=v_expected/);
  assert.doesNotMatch(migration,/max\s*\(\s*version_no\s*\)/i);
  assert.doesNotMatch(migration,/ORDER BY[^;]*(DESC|latest|current)/i);
  assert.match(migration,/status','DRAFT'/);
});

test("Current CORE exposes createCanonicalScriptVersion through the registered route/runtime/permission",async()=>{
  const contract=await read("src/domain/core/coreRuntimeContract.ts");
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const route=await read("src/app/v1/topics/[id]/scripts/versions/route.ts");
  const page=await read("src/app/core/page.tsx");
  for(const token of [
    "CORE-01-ACT-CANONICAL-SCRIPT-CREATE","CORE_SCRIPT_WRITE","CORE-01-PORT-CANONICAL-SCRIPT-CREATE",
    "/v1/topics/{id}/scripts/versions"
  ])assert.ok(contract.includes(token),token);
  assert.match(identity,/CORE-01-PORT-CANONICAL-SCRIPT-CREATE":"api:createCanonicalScriptVersion"/);
  assert.match(route,/createCorePostRoute\("CORE-01-PORT-CANONICAL-SCRIPT-CREATE"\)/);
  assert.match(runtime,/createCanonicalScriptVersion/);
  assert.match(runtime,/acpos_runtime\.create_canonical_script_version/);
  for(const key of ["scope","expected_version","correlation_id","idempotency_key","project_id","topic_id","blueprint_version_id","content","source_script_ref","change_summary"]){
    assert.ok(runtime.includes(`"${key}"`),key);
  }
  assert.doesNotMatch(runtime,/const candidateRef=uuid\(lineage\.source_candidate_ref\)/);
  assert.match(page,/CORE_ACTION_UIDS\.length !== 35 \|\| CORE_PORT_UIDS\.length !== 21/);
});
