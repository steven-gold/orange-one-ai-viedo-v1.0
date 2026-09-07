import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const payloadPath = "03_api/business_payload_registry.yaml";
const interactionPath = "07_ui/interaction_registry.yaml";
const payload = fs.readFileSync(payloadPath, "utf8");
const interaction = fs.readFileSync(interactionPath, "utf8");

const expectedSchemas = [
  ["searchProjection", "SearchProjectionRequest", "/v1/search"],
  ["refreshProjection", "RefreshProjectionRequest", "/v1/projections/refresh"],
  ["configureGovernedResource", "ConfigureGovernedResourceRequest", "/v1/governance/resources/{id}"],
  ["approveGovernedResource", "ApproveGovernedResourceRequest", "/v1/governance/resources/{id}/approve"],
  ["saveDraft", "SaveDraftRequest", "/v1/drafts"],
  ["exportProjection", "ExportProjectionRequest", "/v1/exports"],
  ["createCandidate", "CreateCandidateRequest", "/v1/candidates"],
  ["rejectStrategyCandidate", "RejectStrategyCandidateRequest", "/v1/ai/strategy/candidates/{strategyCandidateId}/reject"],
  ["adoptAsContextCandidate", "AdoptAsContextCandidateRequest", "/v1/state-commands/strategycandidate/adoptascontextcandidate"],
];

test("Current Strategy business payload recovery keeps exact operation/schema/path bindings", () => {
  for (const [operation, schema, path] of expectedSchemas) {
    assert.match(payload, new RegExp(`operation_id: ${operation.replace(/[.*+?^$\{\}()|[\]\\]/g, "\\$&")}`));
    assert.match(payload, new RegExp(`request_schema_id: ${schema.replace(/[.*+?^$\{\}()|[\]\\]/g, "\\$&")}`));
    assert.ok(payload.includes(`path: ${path}`), `missing path for ${operation}: ${path}`);
  }
  assert.match(payload, /operation_id: compareCandidates[\s\S]*interaction_type: DRAWER/);
  assert.match(payload, /Cross-source payload union inference is forbidden/);
});

test("Current Strategy interaction recovery materializes exactly 19 action controls without claiming full 58 remap", () => {
  const controls = [...interaction.matchAll(/^\s*- \{ control_id: (CTRL-ADMIN-STR-[^,]+),/gm)].map((match) => match[1]);
  assert.equal(controls.length, 19);
  assert.equal(new Set(controls).size, 19);
  assert.match(interaction, /source_control_whitelist_total: 58/);
  assert.match(interaction, /action_controls_materialized_here: 19/);
  assert.match(interaction, /full_58_control_remap_status: PARTIAL/);

  for (const sourcePage of ["STR-01","STR-02","STR-03","STR-04","STR-05","STR-06"]) {
    assert.ok(interaction.includes(`source_page_uid: admin:${sourcePage}`), `missing source page ${sourcePage}`);
  }
});

test("Strategy decision actions retain exact R9 owners", () => {
  assert.match(interaction, /CTRL-ADMIN-STR-06-ACT-01-ACT-CANDIDATE-COMPARE[^\n]*operation_id: compareCandidates[^\n]*method: GET[^\n]*path: \/v1\/candidates\/compare/);
  assert.match(interaction, /CTRL-ADMIN-STR-06-ACT-02-ACT-CANDIDATE-DECIDE[^\n]*operation_id: rejectStrategyCandidate[^\n]*method: POST[^\n]*path: "\/v1\/ai\/strategy\/candidates\/\{strategyCandidateId\}\/reject"/);
  assert.match(interaction, /CTRL-ADMIN-STR-06-ACT-03-ACT-ADOPT-CONTEXT[^\n]*operation_id: adoptAsContextCandidate[^\n]*method: POST[^\n]*path: \/v1\/state-commands\/strategycandidate\/adoptascontextcandidate/);
});
