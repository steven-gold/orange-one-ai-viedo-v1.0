import type { CoreExactRefs } from "./coreClientState";

export type CoreProjectionExactRefs = CoreExactRefs;

export type CoreProjectionEnvelope = {
  page_uid: "CORE-01";
  exact_refs: CoreProjectionExactRefs;
  projection: unknown;
};

const CORE_REF_KEYS = [
  "project_id",
  "project_version_ref",
  "topic_id",
  "topic_version_ref",
  "blueprint_version_ref",
  "conversation_id",
  "candidate_ref",
] as const;

function stringOrNull(value: unknown): string | null | undefined {
  if (value === null) return null;
  if (typeof value === "string" && value.trim()) return value;
  return undefined;
}

export function parseCoreProjectionEnvelope(value: unknown): CoreProjectionEnvelope | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (record.page_uid !== "CORE-01") return null;
  const exact = record.exact_refs;
  if (!exact || typeof exact !== "object") return null;
  const exactRecord = exact as Record<string, unknown>;
  const refs: Partial<CoreProjectionExactRefs> = {};
  for (const key of CORE_REF_KEYS) {
    const parsed = stringOrNull(exactRecord[key]);
    if (parsed === undefined) return null;
    refs[key] = parsed;
  }
  return {
    page_uid: "CORE-01",
    exact_refs: refs as CoreProjectionExactRefs,
    projection: record.projection ?? null,
  };
}
