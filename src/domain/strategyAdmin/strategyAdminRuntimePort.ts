import { isControlledTestMode } from "@/domain/testing/controlledTestData";

export type StrategyAdminView =
  | "overview"
  | "intelligence"
  | "playbook"
  | "opportunity"
  | "decision";

export type StrategyAdminPageState =
  | "LOADING"
  | "READY"
  | "EMPTY"
  | "ERROR"
  | "POLICY_BLOCKED"
  | "VERSION_CONFLICT"
  | "REVIEW_REQUIRED"
  | "EXTERNAL_PENDING"
  | "READ_ONLY"
  | "ARCHIVED";

export type StrategyAdminProjectionTestMetadata = {
  data_classification: "TEST_ONLY";
  synthetic: true;
  test_dataset_id: string;
  test_run_id: string;
  created_for_validation: true;
  production_eligible: false;
};

export type StrategyAdminProjection = {
  page_state: StrategyAdminPageState | null;
  values: Readonly<Record<string, string>>;
  evidence: Readonly<Record<string, string>>;
  states: Readonly<Record<string, string>>;
  action_enabled: Readonly<Record<string, boolean>>;
  selected_resource_id: string | null;
  test_metadata?: StrategyAdminProjectionTestMetadata;
};

export type StrategyAdminProjectionResolver = {
  resolve: (
    raw: unknown,
  ) => StrategyAdminProjection | Promise<StrategyAdminProjection>;
};

const ALLOWED_PAGE_STATES = new Set<StrategyAdminPageState>([
  "LOADING",
  "READY",
  "EMPTY",
  "ERROR",
  "POLICY_BLOCKED",
  "VERSION_CONFLICT",
  "REVIEW_REQUIRED",
  "EXTERNAL_PENDING",
  "READ_ONLY",
  "ARCHIVED",
]);

let projectionResolver: StrategyAdminProjectionResolver | null = null;

export function configureStrategyAdminProjectionResolver(
  next: StrategyAdminProjectionResolver,
) {
  projectionResolver = next;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function stringsOnly(value: unknown): Record<string, string> {
  const source = asRecord(value) ?? {};
  const result: Record<string, string> = {};
  for (const [key, entry] of Object.entries(source)) {
    if (typeof entry === "string") result[key] = entry;
  }
  return result;
}

function booleansOnly(value: unknown): Record<string, boolean> {
  const source = asRecord(value) ?? {};
  const result: Record<string, boolean> = {};
  for (const [key, entry] of Object.entries(source)) {
    if (typeof entry === "boolean") result[key] = entry;
  }
  return result;
}

function normalizeTestMetadata(
  value: unknown,
): StrategyAdminProjectionTestMetadata | undefined {
  const metadata = asRecord(value);
  if (!metadata) return undefined;
  if (!isControlledTestMode()) {
    throw new Error("STR_ADMIN_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION");
  }
  if (
    metadata.data_classification !== "TEST_ONLY" ||
    metadata.synthetic !== true ||
    metadata.created_for_validation !== true ||
    metadata.production_eligible !== false ||
    typeof metadata.test_dataset_id !== "string" ||
    typeof metadata.test_run_id !== "string"
  ) {
    throw new Error("STR_ADMIN_TEST_PROJECTION_METADATA_INVALID");
  }
  return metadata as unknown as StrategyAdminProjectionTestMetadata;
}

function normalizeStrategyAdminProjection(raw: unknown): StrategyAdminProjection {
  const record = asRecord(raw);
  if (!record) throw new Error("STR_ADMIN_PROJECTION_NOT_OBJECT");

  let page_state: StrategyAdminPageState | null = null;
  if (record.page_state !== null && record.page_state !== undefined) {
    if (
      typeof record.page_state !== "string" ||
      !ALLOWED_PAGE_STATES.has(record.page_state as StrategyAdminPageState)
    ) {
      throw new Error("STR_ADMIN_PROJECTION_STATE_UNREGISTERED");
    }
    page_state = record.page_state as StrategyAdminPageState;
  }

  return {
    page_state,
    values: stringsOnly(record.values),
    evidence: stringsOnly(record.evidence),
    states: stringsOnly(record.states),
    action_enabled: booleansOnly(record.action_enabled),
    selected_resource_id:
      typeof record.selected_resource_id === "string"
        ? record.selected_resource_id
        : null,
    ...(record.test_metadata
      ? { test_metadata: normalizeTestMetadata(record.test_metadata) }
      : {}),
  };
}

export async function readStrategyAdminProjection(signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/admin%3ASTR-01", {
      method: "GET",
      cache: "no-store",
      signal,
    });
  } catch {
    return {
      ok: false as const,
      reason_code: "STR_ADMIN_PROJECTION_REQUEST_FAILED",
      correlation_id: "unresolved",
    };
  }

  const headerCorrelationId =
    response.headers.get("x-correlation-id") ?? "unresolved";
  const raw: unknown = await response.json().catch(() => null);
  const body = asRecord(raw);
  const correlation_id =
    typeof body?.correlation_id === "string"
      ? body.correlation_id
      : headerCorrelationId;

  if (!response.ok) {
    return {
      ok: false as const,
      reason_code:
        typeof body?.reason_code === "string"
          ? body.reason_code
          : "STR_ADMIN_PROJECTION_READ_FAILED",
      correlation_id,
    };
  }

  try {
    const resolved = projectionResolver
      ? await projectionResolver.resolve(raw)
      : raw;
    return {
      ok: true as const,
      projection: normalizeStrategyAdminProjection(resolved),
      correlation_id,
    };
  } catch {
    return {
      ok: false as const,
      reason_code: "STR_ADMIN_PROJECTION_ADAPTER_REJECTED",
      correlation_id,
    };
  }
}

export type StrategyAdminOperation =
  | "refreshProjection"
  | "searchProjection"
  | "configureGovernedResource"
  | "approveGovernedResource"
  | "exportProjection"
  | "saveDraft"
  | "createCandidate"
  | "compareCandidates"
  | "adoptAsContextCandidate";

export const STRATEGY_ADMIN_ACTION_OPERATION = {
  "ACT-REFRESH": "refreshProjection",
  "ACT-SEARCH": "searchProjection",
  "ACT-CONFIGURE": "configureGovernedResource",
  "ACT-APPROVE": "approveGovernedResource",
  "ACT-EXPORT": "exportProjection",
  "ACT-DRAFT-SAVE": "saveDraft",
  "ACT-CANDIDATE-CREATE": "createCandidate",
  "ACT-CANDIDATE-COMPARE": "compareCandidates",
  "ACT-ADOPT-CONTEXT": "adoptAsContextCandidate",
} as const satisfies Readonly<Record<string, StrategyAdminOperation>>;

export type StrategyAdminMappedAction =
  keyof typeof STRATEGY_ADMIN_ACTION_OPERATION;

export type StrategyAdminCommandInput = {
  action_id: StrategyAdminMappedAction;
  operation: StrategyAdminOperation;
  view: StrategyAdminView;
  projection: StrategyAdminProjection;
};

export type StrategyAdminCommandAdapter = {
  invoke: (
    input: StrategyAdminCommandInput,
  ) => Promise<
    | { ok: true; value: unknown; correlation_id?: string }
    | { ok: false; reason_code: string; correlation_id?: string }
  >;
};

let commandAdapter: StrategyAdminCommandAdapter | null = null;

export function configureStrategyAdminCommandAdapter(
  next: StrategyAdminCommandAdapter,
) {
  commandAdapter = next;
}

export function isStrategyAdminCommandAdapterBound() {
  return commandAdapter !== null;
}

export async function invokeStrategyAdminAction(
  action_id: StrategyAdminMappedAction,
  view: StrategyAdminView,
  projection: StrategyAdminProjection,
) {
  const current = commandAdapter;
  if (!current) {
    return {
      ok: false as const,
      reason_code: "STR_ADMIN_REGISTERED_OPERATION_ADAPTER_NOT_BOUND",
      correlation_id: "unresolved",
    };
  }
  return current.invoke({
    action_id,
    operation: STRATEGY_ADMIN_ACTION_OPERATION[action_id],
    view,
    projection,
  });
}
