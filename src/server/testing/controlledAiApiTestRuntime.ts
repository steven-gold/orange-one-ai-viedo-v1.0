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
  provider_id: string;
  provider_name: string;
  model_id: string;
  model_name: string;
  capability: string;
  adapter_type: string;
  base_url_ref: string;
  endpoint_path: string;
  timeout_seconds: number;
  state: ProviderProfileState;
  credential_status: CredentialStatus;
  last_test_ref: string | null;
  version: number;
};

type ControlledState = {
  profiles: ProviderProfile[];
  audit_counter: number;
  last_audit_ref: string | null;
};

const state: ControlledState = { profiles: [], audit_counter: 0, last_audit_ref: null };

function seedFixture() {
  if (state.profiles.length > 0) return;
  state.profiles.push(
    { provider_id: "TEST-AIAPI-PROVIDER-001", provider_name: "[TEST] Primary Provider", model_id: "TEST-AIAPI-MODEL-001", model_name: "[TEST] Primary Model", capability: "text_generation", adapter_type: "openai_compatible", base_url_ref: "TEST-AIAPI-BASEURL-001", endpoint_path: "/v1/test/chat", timeout_seconds: 30, state: "ENABLED", credential_status: "SET", last_test_ref: null, version: 2 },
    { provider_id: "TEST-AIAPI-PROVIDER-002", provider_name: "[TEST] Secondary Provider", model_id: "TEST-AIAPI-MODEL-002", model_name: "[TEST] Secondary Model", capability: "text_generation", adapter_type: "openai_compatible", base_url_ref: "TEST-AIAPI-BASEURL-002", endpoint_path: "/v1/test/chat", timeout_seconds: 45, state: "DISABLED", credential_status: "NOT_SET", last_test_ref: null, version: 1 },
  );
}

export function isControlledAiApiServerTestMode() {
  return isControlledTestMode();
}

function profileSummary(): string {
  return state.profiles.map((item) => `${item.provider_id}/${item.model_id} v${item.version} ${item.state} · credential ${item.credential_status}`).join(" | ");
}

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
  "AIAPI-01-PRO-DESC-AUTH": "Credential stored as reference · plaintext never displayed",
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
      ...VIEW_VALUES,
      "Provider summary": profileSummary(),
      ...PRO_DESC_VALUES,
      "provider.profile": profileSummary(),
      "provider.selected": `${primary.provider_id}/${primary.model_id}`,
    } as Readonly<Record<string, string>>,
    evidence: Object.fromEntries(Object.keys({ ...VIEW_VALUES, ...PRO_DESC_VALUES }).map((key) => [key, "projection_bound · TEST_ONLY"])),
    states: Object.fromEntries(Object.keys({ ...VIEW_VALUES, ...PRO_DESC_VALUES }).map((key) => [key, "READY"])),
    action_enabled: {
      "ACT-REFRESH": true,
      "ACT-SEARCH": true,
      "ACT-EXPORT": true,
      "ACT-CONFIGURE": true,
      "ACT-APPROVE": true,
      createProviderModelProfile: true,
      updateProviderModelProfile: true,
      getProviderModelProfile: true,
      listProviderModelProfiles: true,
      testProviderModelProfile: true,
      retireProviderModelProfile: true,
      setProviderModelCredential: true,
      deleteProviderModelCredential: true,
      setKillSwitch: true,
      createProviderCandidateGroup: true,
      getProviderQuarantine: true,
      restoreProviderFromQuarantine: true,
      runSandboxTest: true,
      executeProviderRoute: true,
      getProviderRouteDecision: true,
    } as Readonly<Record<string, boolean>>,
    selected_resource_id: primary.provider_id,
    test_metadata: TEST_METADATA,
  };
}
