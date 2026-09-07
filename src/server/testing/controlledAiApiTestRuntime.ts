import { isControlledTestMode } from "@/domain/testing/controlledTestData";

const TEST_METADATA = {
  data_classification: "TEST_ONLY",
  synthetic: true,
  test_dataset_id: "TEST-AIAPI-01",
  test_run_id: "TEST-RUN-AIAPI-01-CONTROLLED",
  created_for_validation: true,
  production_eligible: false,
} as const;

type CredentialStatus = "SET" | "NOT_SET" | "ROTATION_DUE" | "ERROR";
type ProviderProfileState = "ENABLED" | "DISABLED" | "RETIRED";
type ProviderProfile = {
  profile_id: string; provider_id: string; provider_name: string; model_id: string; model_name: string; capability: string; adapter_type: string;
  base_url_ref: string; endpoint_path: string; timeout_seconds: number; state: ProviderProfileState; credential_status: CredentialStatus;
  last_test_ref: string | null; version: number;
};
type ControlledState = { profiles: ProviderProfile[]; audit_counter: number; last_audit_ref: string | null };
const state: ControlledState = { profiles: [], audit_counter: 0, last_audit_ref: null };

function seedFixture() {
  if (state.profiles.length > 0) return;
  state.profiles.push(
    { profile_id: "TEST-AIAPI-PROFILE-001", provider_id: "TEST-AIAPI-PROVIDER-001", provider_name: "[TEST] Primary Provider", model_id: "TEST-AIAPI-MODEL-001", model_name: "[TEST] Primary Model", capability: "TEXT_CHAT", adapter_type: "OPENAI_COMPATIBLE_CHAT", base_url_ref: "TEST-AIAPI-BASEURL-001", endpoint_path: "/v1/test/chat", timeout_seconds: 30, state: "ENABLED", credential_status: "SET", last_test_ref: null, version: 2 },
    { profile_id: "TEST-AIAPI-PROFILE-002", provider_id: "TEST-AIAPI-PROVIDER-002", provider_name: "[TEST] Secondary Provider", model_id: "TEST-AIAPI-MODEL-002", model_name: "[TEST] Secondary Model", capability: "TEXT_CHAT", adapter_type: "OPENAI_COMPATIBLE_CHAT", base_url_ref: "TEST-AIAPI-BASEURL-002", endpoint_path: "/v1/test/chat", timeout_seconds: 45, state: "DISABLED", credential_status: "NOT_SET", last_test_ref: null, version: 1 },
  );
}

export function isControlledAiApiServerTestMode() { return isControlledTestMode(); }
function profileSummary(): string { return state.profiles.map((item) => `${item.provider_id}/${item.model_id} v${item.version} ${item.state} · credential ${item.credential_status}`).join(" | "); }

const VIEW_VALUES: Readonly<Record<string, string>> = {
  "Route summary": "No candidate groups registered · routing requires a registered operation",
  "Capability summary": "Capabilities derived from projection · unapproved capability routing disabled",
  "Job summary": "No jobs recorded · frontend cannot write job state",
  "Cost summary": "Cost derived from projection · pricing comes from registered metadata",
  "Health summary": "Health derived from projection · manual green override disabled",
  "Incident summary": "No incidents recorded",
  "Candidate Group": "No groups registered · creation requires a registered operation",
  "Fallback / limits": "Limits derived from projection · frontend override disabled",
  Preflight: "Registered input schema · purpose is route eligibility only",
  "Instruction Compile Audit": "6 registered sections · frontend rewrite disabled",
  Sandbox: "Execution requires a registered operation · production secrets blocked",
  "Route Simulation": "Registered input schema · frontend route override disabled",
  "Route Decision": "Decision requires a registered operation",
  "Quarantine / restore": "No quarantine records · restore requires a reason",
  Job: "No jobs recorded · 6 registered fields",
  Attempt: "No attempts recorded · retry preserves an independent attempt",
  Callback: "No callbacks recorded · unverified success is rejected",
  Artifact: "No artifacts recorded · silent overwrite is blocked",
  Cost: "Cost derived from projection · currency from registered metadata",
  Budget: "Budget derived from projection · frontend rate guessing disabled",
  Degradation: "Degradation derived from projection",
  Incident: "No incidents recorded",
  "Fallback Decision": "Fallback governed by backend · frontend override disabled",
  "Kill Switch": "Switch requires a registered operation · high-risk confirmation enforced",
};

const PRO_DESC_VALUES: Readonly<Record<string, string>> = {
  "AIAPI-01-PRO-DESC-IDENTITY": "TEST-AIAPI-PROVIDER-001 / TEST-AIAPI-MODEL-001 v2",
  "AIAPI-01-PRO-DESC-POSITIONING": "Capability registry derived from projection · TEST_ONLY",
  "AIAPI-01-PRO-DESC-ACPOS-SCOPE": "Registered route policy · permission gated",
  "AIAPI-01-PRO-DESC-CAPABILITIES": "text generation · references supported (derived)",
  "AIAPI-01-PRO-DESC-INPUT": "Registered request template adapter",
  "AIAPI-01-PRO-DESC-OUTPUT": "Registered response text path",
  "AIAPI-01-PRO-DESC-LIMITS": "30 second timeout · limits from registered metadata",
  "AIAPI-01-PRO-DESC-ENDPOINT": "POST /v1/test/chat · base URL TEST-AIAPI-BASEURL-001",
  "AIAPI-01-PRO-DESC-AUTH": "Credential status SET · plaintext never displayed",
  "AIAPI-01-PRO-DESC-BILLING": "Billing from registered metadata · pricing not guessed",
  "AIAPI-01-PRO-DESC-HEALTH": "Health derived from projection · manual green override disabled",
  "AIAPI-01-PRO-DESC-LAST-TEST": "No tests recorded yet",
  "AIAPI-01-PRO-DESC-RECOMMENDED-USE": "Derived from approved capabilities and route policy · TEST_ONLY",
  "AIAPI-01-PRO-DESC-RESTRICTIONS": "Rights compatibility derived from projection",
  "AIAPI-01-PRO-DESC-DOCS": "Registered documentation reference only",
};

export function readControlledAiApiTestProjection() {
  seedFixture();
  const primary = state.profiles[0];
  return {
    page_state: "READY",
    values: {
      ...VIEW_VALUES, "Provider summary": profileSummary(), ...PRO_DESC_VALUES,
      "provider.profile": profileSummary(), "provider.selected": `${primary.provider_id}/${primary.model_id}`,
    } as Readonly<Record<string, string>>,
    provider_rows: state.profiles.map((item, index) => ({
      profile_id: item.profile_id,
      provider_id: item.provider_id,
      provider_name: item.provider_name,
      model_id: item.model_id,
      model_name: item.model_name,
      capability: item.capability,
      adapter: item.adapter_type,
      base_url: item.base_url_ref,
      endpoint: item.endpoint_path,
      timeout: `${item.timeout_seconds}s`,
      enabled: item.state,
      credential_status: item.credential_status,
      last_test: item.last_test_ref ?? "—",
      health_status: item.state === "ENABLED" ? "HEALTHY" : "UNKNOWN",
      capability_status: index === 0 ? "APPROVED" : "NOT_REGISTERED",
      capability_version: index === 0 ? "TEST-CAP-V1" : "—",
      version: item.version,
    })),
    evidence: Object.fromEntries(Object.keys({ ...VIEW_VALUES, ...PRO_DESC_VALUES }).map((key) => [key, "projection_bound · TEST_ONLY"])),
    states: Object.fromEntries(Object.keys({ ...VIEW_VALUES, ...PRO_DESC_VALUES }).map((key) => [key, "READY"])),
    action_enabled: {
      "ACT-REFRESH": true, "ACT-SEARCH": true, "ACT-EXPORT": true, "ACT-CONFIGURE": true, "ACT-APPROVE": true,
      createProviderModelProfile: true, updateProviderModelProfile: true, getProviderModelProfile: true, listProviderModelProfiles: true,
      testProviderModelProfile: true, retireProviderModelProfile: true, setProviderModelCredential: true, deleteProviderModelCredential: true,
      setKillSwitch: true, createProviderCandidateGroup: true, getProviderQuarantine: true, restoreProviderFromQuarantine: true,
      runSandboxTest: true, executeProviderRoute: true, getProviderRouteDecision: true,
    } as Readonly<Record<string, boolean>>,
    selected_resource_id: primary.profile_id,
    test_metadata: TEST_METADATA,
  };
}


type ControlledAiApiRequest = {
  operation_id: string;
  correlation_id: string;
  path_params: Record<string, string>;
  payload: unknown;
};

export type ControlledAiApiCommandResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; status: number; reason_code: string; correlation_id: string };

function payloadRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function textValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function executeControlledAiApiCommand(request: ControlledAiApiRequest): ControlledAiApiCommandResult {
  if (!isControlledTestMode()) {
    return { ok: false, status: 503, reason_code: "AIAPI_CONTROLLED_RUNTIME_FORBIDDEN", correlation_id: request.correlation_id };
  }
  seedFixture();

  const profileView = (profile: ProviderProfile) => ({
    profile_id: profile.profile_id,
    provider_id: profile.provider_id,
    model_id: profile.model_id,
    capability_type: profile.capability,
    adapter_type: profile.adapter_type,
    base_url: profile.base_url_ref,
    endpoint_path: profile.endpoint_path,
    http_method: "POST",
    secret_env_ref: "TEST_ONLY_SECRET_REFERENCE",
    credential_status: profile.credential_status,
    preferred_language: "zh-TW",
    max_context: null,
    timeout_seconds: profile.timeout_seconds,
    request_template: { prompt_template: "{{canonical_instruction}}" },
    response_text_path: "choices.0.message.content",
    enabled: profile.state === "ENABLED",
    health_status: profile.state === "ENABLED" ? "HEALTHY" : "UNKNOWN",
    version: profile.version,
    test_metadata: TEST_METADATA,
  });
  const findProfile = (ref: string | null) => state.profiles.find((item) =>
    item.profile_id === ref || item.provider_id === ref || item.model_id === ref
  ) ?? null;

  if (request.operation_id === "listProviderModelProfiles") {
    return { ok: true, value: { profiles: state.profiles.map(profileView), test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }
  if (request.operation_id === "getProviderModelProfile") {
    const profile = findProfile(textValue(request.path_params.profileId));
    return profile
      ? { ok: true, value: profileView(profile), correlation_id: request.correlation_id }
      : { ok: false, status: 404, reason_code: "AIAPI_PROFILE_NOT_FOUND", correlation_id: request.correlation_id };
  }
  if (request.operation_id === "testProviderModelProfile") {
    const profile = findProfile(textValue(request.path_params.profileId));
    if (!profile) return { ok: false, status: 404, reason_code: "AIAPI_PROFILE_NOT_FOUND", correlation_id: request.correlation_id };
    state.audit_counter += 1;
    profile.last_test_ref = `TEST-AIAPI-PROFILE-TEST-${String(state.audit_counter).padStart(3, "0")}`;
    return {
      ok: true,
      value: {
        test_id: profile.last_test_ref,
        status: "TEST_ONLY_PASS",
        dry_run: true,
        external_request_sent: false,
        plaintext_persisted: false,
        test_metadata: TEST_METADATA,
      },
      correlation_id: request.correlation_id,
    };
  }
  if (request.operation_id === "getProviderQuarantine") {
    return { ok: true, value: { quarantine: [], test_metadata: TEST_METADATA }, correlation_id: request.correlation_id };
  }
  if (request.operation_id !== "setKillSwitch") {
    return { ok: false, status: 503, reason_code: "AIAPI_CONTROLLED_OPERATION_NOT_MATERIALIZED", correlation_id: request.correlation_id };
  }

  const payload = payloadRecord(request.payload);
  if (textValue(payload.confirmation) !== "CONFIRM") {
    return { ok: false, status: 400, reason_code: "AIAPI_HIGH_RISK_CONFIRMATION_REQUIRED", correlation_id: request.correlation_id };
  }
  if (textValue(payload.target_type)?.toUpperCase() !== "PROFILE") {
    return { ok: false, status: 400, reason_code: "AIAPI_KILL_SWITCH_TARGET_INVALID", correlation_id: request.correlation_id };
  }
  const targetRef = textValue(payload.target_ref);
  const reason = textValue(payload.reason);
  if (!targetRef) {
    return { ok: false, status: 400, reason_code: "AIAPI_FIELD_REQUIRED:target_ref", correlation_id: request.correlation_id };
  }
  if (!reason) {
    return { ok: false, status: 400, reason_code: "AIAPI_FIELD_REQUIRED:reason", correlation_id: request.correlation_id };
  }
  if (typeof payload.enabled !== "boolean") {
    return { ok: false, status: 400, reason_code: "AIAPI_FIELD_REQUIRED:enabled", correlation_id: request.correlation_id };
  }

  const profile = state.profiles.find((item) => item.profile_id === targetRef || item.provider_id === targetRef || item.model_id === targetRef);
  if (!profile) {
    return { ok: false, status: 404, reason_code: "AIAPI_PROFILE_NOT_FOUND", correlation_id: request.correlation_id };
  }

  profile.state = payload.enabled ? "ENABLED" : "DISABLED";
  profile.version += 1;
  state.audit_counter += 1;
  state.last_audit_ref = `TEST-AIAPI-AUDIT-${String(state.audit_counter).padStart(3, "0")}:setKillSwitch:${profile.provider_id}`;

  return {
    ok: true,
    value: {
      target_type: "PROFILE",
      target_ref: profile.provider_id,
      enabled: payload.enabled,
      version: profile.version,
      audit_ref: state.last_audit_ref,
      test_metadata: TEST_METADATA,
      external_request_sent: false,
    },
    correlation_id: request.correlation_id,
  };
}
