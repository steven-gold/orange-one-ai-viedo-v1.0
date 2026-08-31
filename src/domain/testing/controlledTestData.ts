export type ControlledTestMetadata = {
  data_classification: "TEST_ONLY";
  synthetic: true;
  test_dataset_id: string;
  test_run_id: string;
  created_for_validation: true;
  production_eligible: false;
};

const TEST_MODE_DISABLED_VALUE = "PRODUCTION";

export function isControlledTestMode(): boolean {
  return process.env.NEXT_PUBLIC_ACPOS_RUNTIME_MODE !== TEST_MODE_DISABLED_VALUE;
}

function randomToken(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createControlledTestMetadata(scope: string): ControlledTestMetadata {
  const token = randomToken();
  return {
    data_classification: "TEST_ONLY",
    synthetic: true,
    test_dataset_id: `TEST-${scope}`,
    test_run_id: `TEST-RUN-${token}`,
    created_for_validation: true,
    production_eligible: false,
  };
}

export function createControlledTestFixtureLabel(kind: string): string {
  return `[TEST] ${kind} ${new Date().toISOString()}`;
}

export function createControlledTestRef(kind: string): string {
  const normalized = kind.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "-") || "REF";
  return `TEST-${normalized}-${randomToken()}`;
}
