import { createControlledTestFixtureLabel, createControlledTestMetadata, isControlledTestMode } from "../testing/controlledTestData";

export type CoreDraftFormKind = "PROJECT" | "TOPIC";

export type CoreDraftFormContext = {
  kind: CoreDraftFormKind;
  project_id?: string;
};

export type CoreDraftFormResult =
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; reason_code: string };

export type CoreDraftFormAdapter = {
  openRegisteredForm: (context: CoreDraftFormContext) => Promise<CoreDraftFormResult> | CoreDraftFormResult;
};

let adapter: CoreDraftFormAdapter | null = null;

export function configureCoreDraftFormAdapter(next: CoreDraftFormAdapter) {
  adapter = next;
}

export function isCoreDraftFormAdapterBound() {
  return adapter !== null;
}

function isNonEmptyObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) && Object.keys(value).length > 0;
}

function controlledTestPayload(context: CoreDraftFormContext): CoreDraftFormResult {
  const metadata = createControlledTestMetadata(`CORE-${context.kind}`);
  return {
    ok: true,
    payload: {
      ...metadata,
      fixture_kind: context.kind,
      fixture_label: createControlledTestFixtureLabel(context.kind === "PROJECT" ? "Project" : "Topic"),
      ...(context.project_id ? { project_id: context.project_id } : {}),
    },
  };
}

export async function requestCoreDraftFormPayload(context: CoreDraftFormContext): Promise<CoreDraftFormResult> {
  const current = adapter;
  if (!current) {
    if (isControlledTestMode()) return controlledTestPayload(context);
    return {
      ok: false,
      reason_code: context.kind === "PROJECT"
        ? "PROJECT_DRAFT_REGISTERED_SCHEMA_ADAPTER_NOT_BOUND"
        : "TOPIC_DRAFT_REGISTERED_SCHEMA_ADAPTER_NOT_BOUND",
    };
  }

  try {
    const result = await current.openRegisteredForm(context);
    if (!result.ok) return result;
    if (!isNonEmptyObject(result.payload)) {
      return {
        ok: false,
        reason_code: context.kind === "PROJECT"
          ? "PROJECT_DRAFT_REGISTERED_SCHEMA_PAYLOAD_EMPTY"
          : "TOPIC_DRAFT_REGISTERED_SCHEMA_PAYLOAD_EMPTY",
      };
    }
    return result;
  } catch {
    return {
      ok: false,
      reason_code: context.kind === "PROJECT"
        ? "PROJECT_DRAFT_REGISTERED_SCHEMA_ADAPTER_FAILED"
        : "TOPIC_DRAFT_REGISTERED_SCHEMA_ADAPTER_FAILED",
    };
  }
}
