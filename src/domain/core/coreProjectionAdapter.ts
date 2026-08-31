import type { CoreExactRefs } from "./coreClientState";
import { isControlledTestMode } from "../testing/controlledTestData";

export type CoreProjectOption = { project_id: string; project_version_ref: string | null; label: string };
export type CoreTopicOption = { topic_id: string; topic_version_ref: string | null; label: string };
export type CoreWorkItemOption = { work_item: string; label: string };
export type CoreThreadOption = { conversation_id: string; label: string };

export type CoreNormalizedProjection = {
  refs: Partial<CoreExactRefs>;
  work_item: string | null;
  projects: readonly CoreProjectOption[];
  topics: readonly CoreTopicOption[];
  work_items: readonly CoreWorkItemOption[];
  threads: readonly CoreThreadOption[];
  display_values: Readonly<Record<string, string>>;
};

export type CoreProjectionResolver = {
  resolve: (rawProjection: unknown) => Promise<CoreNormalizedProjection> | CoreNormalizedProjection;
};

export type CoreProjectionResolveResult =
  | { ok: true; projection: CoreNormalizedProjection }
  | { ok: false; reason_code: string };

let resolver: CoreProjectionResolver | null = null;

export function configureCoreProjectionResolver(next: CoreProjectionResolver) {
  resolver = next;
}

export function isCoreProjectionResolverBound() {
  return resolver !== null;
}

function validText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validNullableText(value: unknown): value is string | null | undefined {
  return value === undefined || value === null || validText(value);
}

function validateProjection(value: CoreNormalizedProjection): boolean {
  if (!value || typeof value !== "object") return false;
  const refs = value.refs ?? {};
  for (const ref of Object.values(refs)) if (!validNullableText(ref)) return false;
  if (!validNullableText(value.work_item)) return false;
  if (!Array.isArray(value.projects) || value.projects.some(item => !validText(item.project_id) || !validNullableText(item.project_version_ref) || !validText(item.label))) return false;
  if (!Array.isArray(value.topics) || value.topics.some(item => !validText(item.topic_id) || !validNullableText(item.topic_version_ref) || !validText(item.label))) return false;
  if (!Array.isArray(value.work_items) || value.work_items.some(item => !validText(item.work_item) || !validText(item.label))) return false;
  if (!Array.isArray(value.threads) || value.threads.some(item => !validText(item.conversation_id) || !validText(item.label))) return false;
  if (!value.display_values || typeof value.display_values !== "object" || Object.values(value.display_values).some(item => typeof item !== "string")) return false;
  return true;
}

function controlledTestProjection(rawProjection: unknown): CoreProjectionResolveResult {
  if (!rawProjection || typeof rawProjection !== "object") return { ok: false, reason_code: "CORE_TEST_PROJECTION_INVALID" };
  const projection = rawProjection as CoreNormalizedProjection;
  if (!validateProjection(projection)) return { ok: false, reason_code: "CORE_TEST_PROJECTION_SCHEMA_REJECTED" };
  return { ok: true, projection };
}

export async function resolveCoreProjection(rawProjection: unknown): Promise<CoreProjectionResolveResult> {
  const current = resolver;
  if (!current) {
    if (isControlledTestMode()) return controlledTestProjection(rawProjection);
    return { ok: false, reason_code: "CORE_PROJECTION_SCHEMA_ADAPTER_NOT_BOUND" };
  }
  try {
    const projection = await current.resolve(rawProjection);
    if (!validateProjection(projection)) return { ok: false, reason_code: "CORE_PROJECTION_SCHEMA_ADAPTER_REJECTED" };
    return { ok: true, projection };
  } catch {
    return { ok: false, reason_code: "CORE_PROJECTION_SCHEMA_ADAPTER_FAILED" };
  }
}
