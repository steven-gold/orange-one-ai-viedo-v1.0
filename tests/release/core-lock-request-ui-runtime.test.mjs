import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("CORE lock request UI uses explicit Current projection context and formal modal",async()=>{
  const projection=await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const adapter=await read("src/domain/core/coreProjectionAdapter.ts");
  const payload=await read("src/domain/core/coreLockCommandPayloadAdapter.ts");
  const visual=await read("src/components/pages/CoreVisual.tsx");
  const catalog=await read("src/i18n/coreCatalog.ts");
  for(const token of ["project_version_no","workspace_id","blueprint_version_no","approved_criteria","eligible_reviewer_count"]){
    assert.ok(projection.includes(token),token);
    assert.ok(adapter.includes(token),token);
  }
  assert.match(projection,/count_lock_reviewer_candidates/);
  assert.match(projection,/WHERE status='APPROVED'/);
  for(const key of ["scope","expected_version","correlation_id","idempotency_key","target_ref","request_reason","requested_scope_refs"]){
    assert.ok(payload.includes(key),key);
  }
  assert.match(payload,/requested_scope_refs:\[criteria_version_id,\.\.\.evidence_refs\]/);
  assert.match(visual,/role="dialog"/);
  assert.match(visual,/aria-modal="true"/);
  assert.match(visual,/lockRequestReason/);
  assert.match(visual,/lockCriteriaVersionId/);
  assert.match(visual,/LOCK_CRITERIA_VERSION_REQUIRED/);
  assert.match(visual,/LOCK_EVIDENCE_REQUIRED/);
  assert.match(visual,/CORE_LOCK_REVIEWER_PATH_UNRESOLVED/);
  assert.match(visual,/selected\.blueprint_version_ref/);
  for(const key of ["core01.lock_modal.title_mother","core01.lock_modal.title_child","core01.lock_modal.request_reason","core01.lock_modal.criteria_version","core01.lock_modal.cancel","core01.lock_modal.execute"]){
    assert.ok(catalog.includes(key),key);
  }
});
