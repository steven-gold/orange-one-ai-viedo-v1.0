import { ASSET_ACTION_PORT, type AssetPortUid, type AssetRuntimeRequest, type AssetRuntimeResult } from "@/domain/asset/assetRuntimeContract";
import type { AssetNormalizedProjection, AssetProjectionCandidateVersion } from "@/domain/asset/assetProjectionPort";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";

const PROJECT_REF = "TEST-ASSET-PROJECT-001";
const TOPIC_REF = "TEST-ASSET-TOPIC-001";
const TASK_ID = "TEST-ASSET-TASK-001";
const BLUEPRINT_REF = "TEST-BLUEPRINT-VERSION-001";
const SCRIPT_REF = "TEST-ASSET-SCRIPT-001";
const DNA_REF = "TEST-DNA-VERSION-001";
const MANIFEST_REF = "TEST-ASSET-MANIFEST-001";
const INPUT_FINGERPRINT = "TEST-ASSET-INPUT-FINGERPRINT-001";
const NAMING_POLICY = "ACPOS_SYSTEM@TEST";
const CRITERIA_REF = "TEST-ASSET-CRITERIA-001";
const RIGHTS_REF = "TEST-RIGHTS-POLICY-001";
const INSTRUCTION_REF = "TEST-ASSET-INSTRUCTION-001";
const ROUTE_REF = "TEST-ROUTE-IMAGE-001";
const TEST_METADATA = {
  data_classification: "TEST_ONLY",
  synthetic: true,
  test_dataset_id: "TEST-ASSET-01",
  test_run_id: "TEST-RUN-ASSET-01-CONTROLLED",
  created_for_validation: true,
  production_eligible: false,
} as const;

type PageState = "READY" | "EXECUTING" | "CANDIDATE_OUTPUT" | "WAIT_CONFIRMATION" | "CORRECTION_REQUIRED" | "CONFIRMED" | "LOCKED" | "HANDOFF" | "ERROR";
type PatchState = "NONE" | "DRAFT" | "PREVIEW_READY" | "ACCEPTED" | "REJECTED";

type ControlledState = {
  page_state: PageState;
  stage: string;
  output_version_id: string | null;
  candidates: AssetProjectionCandidateVersion[];
  layer_document_id: string | null;
  layer_id: string | null;
  patch_id: string | null;
  patch_state: PatchState;
  evaluation_complete: boolean;
  finding_open: boolean;
  handoff_ref: string | null;
  version_counter: number;
  layer_counter: number;
  job_counter: number;
};

const state: ControlledState = {
  page_state: "READY",
  stage: "ASSET-01-STAGE-01-RESOLVE",
  output_version_id: null,
  candidates: [],
  layer_document_id: null,
  layer_id: null,
  patch_id: null,
  patch_state: "NONE",
  evaluation_complete: false,
  finding_open: false,
  handoff_ref: null,
  version_counter: 0,
  layer_counter: 0,
  job_counter: 0,
};

function imageData(version: number) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><rect width="960" height="540" fill="#12172d"/><circle cx="480" cy="230" r="130" fill="#7b61ff"/><text x="480" y="430" text-anchor="middle" font-family="Arial" font-size="42" fill="white">ASSET TEST v${version}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function checksum(version: number) { return `TEST-SHA256-ASSET-${String(version).padStart(4, "0")}`; }
function canonicalFilename(version: number) { return `TEST_ASSET_CHARACTER_V${String(version).padStart(3, "0")}.png`; }
function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" ? value as Record<string, unknown> : {}; }
function text(value: unknown) { return typeof value === "string" && value.trim() ? value : null; }

function fail(request: AssetRuntimeRequest, error_uid: AssetRuntimeResult extends { ok: false; error_uid: infer E } ? E : never, reason_code: string, status: number): AssetRuntimeResult {
  return { ok: false, error_uid, reason_code, correlation_id: request.correlation_id, status };
}

function addCandidate(): AssetProjectionCandidateVersion {
  state.version_counter += 1;
  const ref = `TEST-ASSET-VERSION-${String(state.version_counter).padStart(3, "0")}`;
  const candidate: AssetProjectionCandidateVersion = {
    ref,
    label: `[TEST] Character ${state.version_counter}`,
    uri: imageData(state.version_counter),
    media_kind: "IMAGE",
  };
  state.output_version_id = ref;
  state.candidates = [candidate, ...state.candidates].slice(0, 3);
  state.evaluation_complete = false;
  return candidate;
}

function gates() {
  const hasCandidate = Boolean(state.output_version_id);
  const imageEligible = hasCandidate;
  const confirmed = state.page_state === "CONFIRMED" || state.page_state === "LOCKED" || state.page_state === "HANDOFF";
  const waitConfirm = state.page_state === "WAIT_CONFIRMATION";
  const locked = state.page_state === "LOCKED" || state.page_state === "HANDOFF";
  return {
    "ASSET-01-GATE-PAGE": true,
    "ASSET-01-GATE-CONTEXT": true,
    "ASSET-01-GATE-CHILD-LOCK": true,
    "ASSET-01-GATE-SCRIPT": true,
    "ASSET-01-GATE-MANIFEST": true,
    "ASSET-01-GATE-NAMING": true,
    "ASSET-01-GATE-ROUTE": true,
    "ASSET-01-GATE-EXECUTE": state.page_state === "READY" || state.page_state === "CANDIDATE_OUTPUT" || state.page_state === "CORRECTION_REQUIRED",
    "ASSET-01-GATE-CANDIDATE": hasCandidate,
    "ASSET-01-GATE-EVALUATION": hasCandidate,
    "ASSET-01-GATE-WAIT-CONFIRM": waitConfirm,
    "ASSET-01-GATE-CORRECTION": waitConfirm || state.page_state === "CORRECTION_REQUIRED",
    "ASSET-01-GATE-LAYER-ELIGIBLE": imageEligible,
    "ASSET-01-GATE-LAYER-WRITE": imageEligible && !locked,
    "ASSET-01-GATE-PATCH-PREVIEW": state.patch_state === "DRAFT" || state.patch_state === "PREVIEW_READY",
    "ASSET-01-GATE-PATCH-DECISION": state.patch_state === "PREVIEW_READY",
    "ASSET-01-GATE-CONFIRM": waitConfirm && state.evaluation_complete,
    "ASSET-01-GATE-LOCK": confirmed && state.page_state === "CONFIRMED",
    "ASSET-01-GATE-HANDOFF": locked,
    "ASSET-01-GATE-RETRY": state.page_state === "ERROR",
    "ASSET-01-GATE-COMPARE": state.candidates.length >= 1 && state.candidates.length <= 3,
  } satisfies Readonly<Record<string, boolean>>;
}

export function isControlledAssetServerTestMode() { return isControlledTestMode(); }

export function readControlledAssetTestProjection(): AssetNormalizedProjection {
  const current = state.candidates.find(item => item.ref === state.output_version_id) ?? state.candidates[0] ?? null;
  const versionNumber = state.version_counter || 1;
  const lockedRef = state.output_version_id ? `TEST-ASSET-LOCK-${state.output_version_id}` : "—";
  return {
    page_state: state.page_state,
    task_id: TASK_ID,
    output_version_id: state.output_version_id,
    layer_document_id: state.layer_document_id,
    layer_id: state.layer_id,
    patch_id: state.patch_id,
    current_asset_type_uid: "ASSET-01-TYPE-CHARACTER",
    candidate_uri: current?.uri ?? null,
    candidate_media_kind: current?.media_kind ?? null,
    candidate_versions: [...state.candidates],
    values: {
      "ASSET-01-FLD-TASK-STATUS": state.page_state,
      "ASSET-01-FLD-STAGE": state.stage,
      "ASSET-01-FLD-MANIFEST-REQUIRED": "2",
      "ASSET-01-FLD-MANIFEST-REUSE": "1",
      "ASSET-01-FLD-MANIFEST-MISSING": state.output_version_id ? "0" : "1",
      "ASSET-01-FLD-MANIFEST-DEFERRED": "0",
      "ASSET-01-FLD-BLUEPRINT": BLUEPRINT_REF,
      "ASSET-01-FLD-SCRIPT": SCRIPT_REF,
      "ASSET-01-FLD-DNA": DNA_REF,
      "ASSET-01-FLD-MANIFEST": MANIFEST_REF,
      "ASSET-01-FLD-INPUT-FINGERPRINT": INPUT_FINGERPRINT,
      "ASSET-01-FLD-NAMING-AUTHORITY": NAMING_POLICY,
      "ASSET-01-FLD-CANONICAL-FILENAME": state.output_version_id ? canonicalFilename(versionNumber) : "—",
      "ASSET-01-FLD-OUTPUT-ID": state.output_version_id ?? "—",
      "ASSET-01-FLD-CHECKSUM": state.output_version_id ? checksum(versionNumber) : "—",
      "ASSET-01-FLD-RIGHTS": RIGHTS_REF,
      "ASSET-01-FLD-INSTRUCTION": INSTRUCTION_REF,
      "ASSET-01-FLD-ROUTE": ROUTE_REF,
      "ASSET-01-FLD-PROVIDER": state.output_version_id ? "SIMULATED_EXTERNAL" : "—",
      "ASSET-01-FLD-JOB": state.job_counter ? `TEST-ASSET-JOB-${state.job_counter}` : "—",
      "ASSET-01-FLD-ATTEMPT": state.job_counter ? "1" : "—",
      "ASSET-01-FLD-CALLBACK": state.output_version_id ? "NORMALIZED_RESULT_RECEIVED" : "—",
      "ASSET-01-FLD-RETRY-ELIGIBILITY": state.page_state === "ERROR" ? "ELIGIBLE" : "NOT_REQUIRED",
      "ASSET-01-FLD-CRITERIA": CRITERIA_REF,
      "ASSET-01-FLD-DIMENSIONS": state.evaluation_complete ? "identity=98; continuity=97; technical=99" : "—",
      "ASSET-01-FLD-OVERALL": state.evaluation_complete ? "98" : "—",
      "ASSET-01-FLD-ISSUES": state.finding_open ? "TEST_FINDING_OPEN" : "NONE",
      "ASSET-01-FLD-HANDOFF-ASSET-VERSION": state.output_version_id ?? "—",
      "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE": state.layer_document_id ?? "—",
      "ASSET-01-FLD-HANDOFF-BLUEPRINT": BLUEPRINT_REF,
      "ASSET-01-FLD-HANDOFF-SCRIPT-HASH": "TEST-SCRIPT-HASH-001",
      "ASSET-01-FLD-HANDOFF-DNA": DNA_REF,
      "ASSET-01-FLD-HANDOFF-MANIFEST-ITEMS": MANIFEST_REF,
      "ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME": state.output_version_id ? canonicalFilename(versionNumber) : "—",
      "ASSET-01-FLD-HANDOFF-CHECKSUM": state.output_version_id ? checksum(versionNumber) : "—",
      "ASSET-01-FLD-HANDOFF-SCORECARD": state.evaluation_complete ? CRITERIA_REF : "—",
      "ASSET-01-FLD-HANDOFF-RIGHTS": RIGHTS_REF,
      "ASSET-01-FLD-HANDOFF-CONTRACT-HASH": "TEST-ASSET-HANDOFF-CONTRACT-001",
      "ASSET-01-TEST-LOCK-REF": lockedRef,
      "ASSET-01-TEST-HANDOFF-REF": state.handoff_ref ?? "—",
    },
    lists: {
      "ASSET-01-CTL-PROJECT": [{ ref: PROJECT_REF, label: "[TEST] ORANGE ONE Project" }],
      "ASSET-01-CTL-TOPIC": [{ ref: TOPIC_REF, label: "[TEST] Topic 001" }],
      "ASSET-01-LST-ASSET": [
        { ref: "TEST-MANIFEST-CHARACTER-001", label: "Character · Missing → Generate" },
        { ref: "TEST-MANIFEST-SCENE-001", label: "Scene · Reuse exact version" },
      ],
      "ASSET-01-LST-COMPARE-VERSIONS": state.candidates.map(item => ({ ref: item.ref, label: item.label })),
    },
    filters: {
      "ASSET-01-CTL-FILTER": [
        { ref: "ALL", label: "All" },
        { ref: "MISSING", label: "Missing" },
        { ref: "REUSE", label: "Reuse" },
      ],
      "ASSET-01-CTL-LAYER-PROPERTIES": [
        { ref: "OPACITY_100", label: "Opacity 100%" },
        { ref: "BLEND_NORMAL", label: "Blend NORMAL" },
      ],
      "ASSET-01-CTL-LAYER-MASK": [
        { ref: "MASK_ENABLED", label: "Mask Enabled" },
        { ref: "MASK_DISABLED", label: "Mask Disabled" },
      ],
    },
    gate_state: gates(),
  };
}

export async function executeControlledAssetTestPort(request: AssetRuntimeRequest): Promise<AssetRuntimeResult> {
  if (!isControlledAssetServerTestMode()) return fail(request, "ASSET-01-ERR-CONTEXT-001", "ASSET_TEST_RUNTIME_DISABLED", 503);
  if (request.action_uid && ASSET_ACTION_PORT[request.action_uid] !== request.port_uid) return fail(request, "ASSET-01-ERR-CONTEXT-001", "ACTION_PORT_BINDING_MISMATCH", 400);
  const payload = record(request.payload);
  const port: AssetPortUid = request.port_uid;

  if (port === "ASSET-01-PORT-IN-CORE-HANDOFF") return { ok: true, value: { accepted: true, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };

  if (port === "ASSET-01-PORT-EXECUTE" || port === "ASSET-01-PORT-RETRY") {
    state.page_state = "EXECUTING";
    state.job_counter += 1;
    addCandidate();
    state.page_state = "CANDIDATE_OUTPUT";
    state.stage = "ASSET-01-STAGE-03-LAYER-COMPOSITE";
    state.patch_id = null;
    state.patch_state = "NONE";
    return { ok: true, value: { output_version_id: state.output_version_id, provider_execution: "SIMULATED_EXTERNAL", test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-FINDING") {
    state.finding_open = true;
    state.page_state = "CORRECTION_REQUIRED";
    return { ok: true, value: { finding_ref: "TEST-ASSET-FINDING-001", test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-CORRECTION") {
    state.page_state = "CORRECTION_REQUIRED";
    return { ok: true, value: { correction_request_ref: "TEST-ASSET-CORRECTION-001", test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-SCORECARD") {
    if (!state.output_version_id) return fail(request, "ASSET-01-ERR-CANDIDATE-001", "CANDIDATE_REQUIRED", 409);
    state.evaluation_complete = true;
    state.page_state = "WAIT_CONFIRMATION";
    state.stage = "ASSET-01-STAGE-04-EVALUATE-DECIDE";
    return { ok: true, value: { scorecard_ref: "TEST-ASSET-SCORECARD-001", overall_score: 98, hard_block: false, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-DECISION") {
    const outputVersionId = request.path_params?.outputVersionId;
    if (!state.output_version_id || outputVersionId !== state.output_version_id) return fail(request, "ASSET-01-ERR-VERSION-001", "EXACT_OUTPUT_VERSION_MISMATCH", 409);
    const decision = text(payload.decision) ?? "CONFIRM";
    if (decision !== "CONFIRM") return fail(request, "ASSET-01-ERR-CANDIDATE-001", "UNSUPPORTED_TEST_DECISION", 400);
    if (!state.evaluation_complete) return fail(request, "ASSET-01-ERR-CRITERIA-001", "EVALUATION_REQUIRED", 409);
    state.page_state = "CONFIRMED";
    state.stage = "ASSET-01-STAGE-05-FINALIZE";
    return { ok: true, value: { decision: "CONFIRM", output_version_id: state.output_version_id, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-OUT-VIDEO") {
    if (!state.output_version_id) return fail(request, "ASSET-01-ERR-HANDOFF-001", "LOCKED_VERSION_REQUIRED", 409);
    const lockedVersionRef = text(payload.locked_version_ref);
    if (lockedVersionRef !== `TEST-ASSET-LOCK-${state.output_version_id}`) return fail(request, "ASSET-01-ERR-HANDOFF-001", "LOCKED_VERSION_REF_MISMATCH", 409);
    state.page_state = "HANDOFF";
    state.handoff_ref = `TEST-ASSET-VIDEO-HANDOFF-${state.output_version_id}`;
    return { ok: true, value: { handoff_ref: state.handoff_ref, exact_asset_version: state.output_version_id, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-LAYER-DOC-CREATE") {
    if (!state.output_version_id) return fail(request, "ASSET-01-ERR-LAYER-001", "ASSET_VERSION_REQUIRED", 409);
    state.layer_document_id = `TEST-LAYER-DOC-${state.output_version_id}`;
    return { ok: true, value: { layer_document_id: state.layer_document_id, version: 1, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-LAYER-DOC-UPDATE") {
    if (!state.layer_document_id || request.path_params?.layerDocumentId !== state.layer_document_id) return fail(request, "ASSET-01-ERR-LAYER-001", "LAYER_DOCUMENT_MISMATCH", 409);
    return { ok: true, value: { layer_document_id: state.layer_document_id, version_incremented: true, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-LAYER-ADD") {
    if (!state.layer_document_id) return fail(request, "ASSET-01-ERR-LAYER-001", "LAYER_DOCUMENT_REQUIRED", 409);
    state.layer_counter += 1;
    state.layer_id = `TEST-LAYER-${state.layer_counter}`;
    return { ok: true, value: { layer_id: state.layer_id, layer_type: "CHARACTER_BODY", z_index: state.layer_counter, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (["ASSET-01-PORT-LAYER-DELETE", "ASSET-01-PORT-LAYER-DUP", "ASSET-01-PORT-LAYER-REORDER", "ASSET-01-PORT-LAYER-PROPS", "ASSET-01-PORT-LAYER-MASK"].includes(port)) {
    if (!state.layer_document_id || !state.layer_id) return fail(request, "ASSET-01-ERR-LAYER-001", "LAYER_REFERENCE_REQUIRED", 409);
    if (port === "ASSET-01-PORT-LAYER-DELETE") state.layer_id = null;
    if (port === "ASSET-01-PORT-LAYER-DUP") { state.layer_counter += 1; state.layer_id = `TEST-LAYER-${state.layer_counter}`; }
    return { ok: true, value: { layer_document_id: state.layer_document_id, layer_id: state.layer_id, operation: port, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-PATCH-CREATE") {
    if (!state.output_version_id) return fail(request, "ASSET-01-ERR-PATCH-001", "SOURCE_ASSET_VERSION_REQUIRED", 409);
    state.patch_id = `TEST-ASSET-PATCH-${state.version_counter}`;
    state.patch_state = "DRAFT";
    return { ok: true, value: { patch_id: state.patch_id, patch_state: state.patch_state, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-PATCH-PREVIEW") {
    if (!state.patch_id || request.path_params?.patchId !== state.patch_id) return fail(request, "ASSET-01-ERR-PATCH-001", "PATCH_REF_MISMATCH", 409);
    state.patch_state = "PREVIEW_READY";
    return { ok: true, value: { patch_id: state.patch_id, patch_state: state.patch_state, preview_uri: imageData(state.version_counter + 1), test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }

  if (port === "ASSET-01-PORT-PATCH-DECIDE") {
    if (!state.patch_id || request.path_params?.patchId !== state.patch_id) return fail(request, "ASSET-01-ERR-PATCH-001", "PATCH_REF_MISMATCH", 409);
    const decision = text(payload.decision);
    if (decision === "ACCEPT") {
      state.patch_state = "ACCEPTED";
      addCandidate();
      state.page_state = "CANDIDATE_OUTPUT";
      return { ok: true, value: { decision, new_asset_version_id: state.output_version_id, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
    }
    if (decision === "REJECT") {
      state.patch_state = "REJECTED";
      return { ok: true, value: { decision, source_asset_version_id: state.output_version_id, test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
    }
    return fail(request, "ASSET-01-ERR-PATCH-001", "PATCH_DECISION_REQUIRED", 400);
  }

  return fail(request, "ASSET-01-ERR-CONTEXT-001", "CONTROLLED_ASSET_PORT_NOT_IMPLEMENTED", 501);
}
