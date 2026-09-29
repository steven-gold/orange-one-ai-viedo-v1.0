import { createControlledTestRef, isControlledTestMode } from "../testing/controlledTestData";

export type CoreComposerResourceKind = "ATTACHMENT" | "REFERENCE";

export type CoreComposerResourceContext = {
  kind: CoreComposerResourceKind;
  conversation_id: string;
};

export type CoreComposerResourceResult =
  | { ok: true; ref: string; data_classification?: "TEST_ONLY" }
  | { ok: false; reason_code: string };

export type CoreComposerResourceAdapter = {
  selectResource: (context: CoreComposerResourceContext) => Promise<CoreComposerResourceResult> | CoreComposerResourceResult;
};

let adapter: CoreComposerResourceAdapter | null = null;

export function configureCoreComposerResourceAdapter(next: CoreComposerResourceAdapter) {
  adapter = next;
}

function validRef(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export async function requestCoreComposerResource(context: CoreComposerResourceContext): Promise<CoreComposerResourceResult> {
  const current = adapter;
  if (!current) {
    if (isControlledTestMode()) {
      return { ok: true, ref: createControlledTestRef(`CORE-${context.kind}`), data_classification: "TEST_ONLY" };
    }
    return { ok: false, reason_code: `GLOBAL_${context.kind}_SELECTOR_NOT_BOUND` };
  }

  try {
    const result = await current.selectResource(context);
    if (!result.ok) return result;
    if (!validRef(result.ref)) return { ok: false, reason_code: `${context.kind}_REF_INVALID` };
    return result;
  } catch {
    return { ok: false, reason_code: `${context.kind}_SELECTOR_FAILED` };
  }
}
