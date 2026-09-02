import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { configureDevCommandAdapter, type DevCommandInput } from "./devCommandPort";
import { configureDevProjectionResolver, type DevNormalizedProjection, type DevProjectionTestMetadata } from "./devProjectionPort";
import { DEV_CONTROL_BINDINGS, type DevControlUid } from "./devControlBindings";

const TEST_METADATA: DevProjectionTestMetadata = { data_classification: "TEST_ONLY", synthetic: true, test_dataset_id: "TEST-DEV-01", test_run_id: "TEST-RUN-DEV-CONTROLLED-01", created_for_validation: true, production_eligible: false };
let configured = false;

function record(value: unknown): Record<string, unknown> | null { return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null; }
function controlledProjection(raw: unknown): DevNormalizedProjection {
  const candidate = record(raw);
  if (!candidate) throw new Error("DEV_CONTROLLED_PROJECTION_INVALID");
  const metadata = record(candidate.test_metadata);
  if (metadata?.data_classification !== "TEST_ONLY" || metadata.production_eligible !== false) throw new Error("DEV_CONTROLLED_PROJECTION_CLASSIFICATION_INVALID");
  return candidate as unknown as DevNormalizedProjection;
}
function clone(input: DevNormalizedProjection): DevNormalizedProjection {
  return { ...input, values: { ...input.values }, gate_state: { ...input.gate_state }, test_metadata: TEST_METADATA };
}
function transition(input: DevCommandInput): DevNormalizedProjection | null {
  const current = input.projection;
  if (!current || current.test_metadata?.data_classification !== "TEST_ONLY" || current.test_metadata.production_eligible !== false) return null;
  const binding = DEV_CONTROL_BINDINGS[input.control_uid as DevControlUid];
  if (!binding || binding.action_uid !== input.action_uid || current.gate_state[binding.gate_uid as keyof typeof current.gate_state] !== true) return null;
  const next = clone(current);
  const gates = { ...next.gate_state };
  const values: Record<string, string> = { ...next.values, last_action_uid: input.action_uid };
  switch (input.action_uid) {
    case "DEV-01-ACT-DISCOVERY-START": next.run_status = "RUNNING"; gates["DEV-01-GATE-DISCOVERY-START"] = false; gates["DEV-01-GATE-DISCOVERY-RUNNING"] = true; gates["DEV-01-GATE-DISCOVERY-PAUSED"] = false; break;
    case "DEV-01-ACT-DISCOVERY-PAUSE": next.run_status = "PAUSED"; gates["DEV-01-GATE-DISCOVERY-RUNNING"] = false; gates["DEV-01-GATE-DISCOVERY-PAUSED"] = true; break;
    case "DEV-01-ACT-DISCOVERY-RESUME": next.run_status = "RUNNING"; gates["DEV-01-GATE-DISCOVERY-RUNNING"] = true; gates["DEV-01-GATE-DISCOVERY-PAUSED"] = false; break;
    case "DEV-01-ACT-DISCOVERY-STOP": next.run_status = "STOPPED"; gates["DEV-01-GATE-DISCOVERY-START"] = true; gates["DEV-01-GATE-DISCOVERY-RUNNING"] = false; gates["DEV-01-GATE-DISCOVERY-PAUSED"] = false; break;
    case "DEV-01-ACT-MERGE-PREVIEW": gates["DEV-01-GATE-MERGE-CONFIRM"] = true; values.merge_preview_ref = "TEST-DEV-MERGE-PREVIEW-001"; break;
    case "DEV-01-ACT-MERGE": gates["DEV-01-GATE-MERGE-CONFIRM"] = false; values.merge_result_ref = "TEST-DEV-MERGE-RESULT-001"; break;
    case "DEV-01-ACT-CANDIDATE-CREATE": gates["DEV-01-GATE-MESSAGE-REVIEW"] = true; values.message_candidate_state = "REVIEW_REQUIRED"; break;
    case "DEV-01-ACT-CANDIDATE-DECIDE": gates["DEV-01-GATE-MESSAGE-REVIEW"] = false; values.message_candidate_state = "APPROVED"; break;
    case "DEV-01-ACT-CR-CREATE": values.change_request_ref = "TEST-DEV-CR-001"; break;
    case "DEV-01-ACT-CAMPAIGN-CREATE": gates["DEV-01-GATE-CAMPAIGN-APPROVAL"] = true; values.campaign_state = "REVIEW_REQUIRED"; break;
    case "DEV-01-ACT-CAMPAIGN-APPROVE": gates["DEV-01-GATE-CAMPAIGN-APPROVAL"] = false; gates["DEV-01-GATE-DISPATCH"] = true; values.campaign_state = "APPROVED"; break;
    case "DEV-01-ACT-EMAIL-DISPATCH": gates["DEV-01-GATE-DISPATCH"] = false; gates["DEV-01-GATE-KILL-SWITCH"] = true; values.delivery_state = "QUEUED · ONE_TO_ONE"; break;
    case "DEV-01-ACT-KILL-SWITCH": gates["DEV-01-GATE-KILL-SWITCH"] = false; values.delivery_state = "STOPPED_BY_KILL_SWITCH"; break;
    case "DEV-01-ACT-DIRECTORY-SEARCH": values.directory_search_ref = "TEST-DEV-SEARCH-001"; break;
    case "DEV-01-ACT-EXPORT": values.export_ref = "TEST-DEV-EXPORT-001"; break;
    case "DEV-01-ACT-CAMPAIGN-SEARCH": values.campaign_search_ref = "TEST-DEV-CAMPAIGN-SEARCH-001"; break;
    case "DEV-01-ACT-REFRESH": values.refresh_ref = "TEST-DEV-REFRESH-001"; break;
    default: return null;
  }
  return { ...next, values, gate_state: gates, test_metadata: TEST_METADATA };
}

export function ensureControlledDevClientTestRuntime() {
  if (configured || !isControlledTestMode()) return;
  configureDevProjectionResolver({ resolve: controlledProjection });
  configureDevCommandAdapter({ invoke: async (input) => {
    const projection = transition(input);
    if (!projection) return { ok: false as const, error_uid: "DEV-01-ERR-UNDEFINED", reason_code: "DEV_CONTROLLED_COMMAND_GATE_REJECTED", correlation_id: "TEST-DEV-CORR-REJECTED" };
    return { ok: true as const, projection, correlation_id: `TEST-DEV-CORR-${input.action_uid}` };
  }});
  configured = true;
}
