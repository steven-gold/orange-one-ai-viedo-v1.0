export const CORE_ERROR_CODES = [
  "CORE_CONTEXT_INVALID",
  "CORE_STORY_CONTRACT_INCOMPLETE",
  "CORE_CHAPTER_CONTRACT_INVALID",
  "CORE_WORLD_CONTRACT_INVALID",
  "CORE_DNA_CONTRACT_INVALID",
  "CORE_BLUEPRINT_INCOMPLETE",
  "CORE_SCRIPT_INVALID",
  "CORE_MACHINE_PROJECTION_LOSSY",
  "CORE_DECISION_MISSING",
  "CORE_VERSION_CONFLICT",
  "CORE_LOCK_EVIDENCE_MISSING",
  "CORE_NAMING_AUTHORITY_MISSING",
  "CORE_PACKAGE_NOT_READY",
  "CORE_PERMISSION_DENIED",
  "CORE_UNDEFINED_AUTHORITY_GAP",
] as const;

export type CoreErrorCode = (typeof CORE_ERROR_CODES)[number];

export const CORE_ERROR_CONTRACT: Record<CoreErrorCode, { condition: string; recovery: string }> = {
  CORE_CONTEXT_INVALID: {
    condition: "Project/Topic/context mismatch",
    recovery: "preserve draft; reselect exact context",
  },
  CORE_STORY_CONTRACT_INCOMPLETE: {
    condition: "required Story dimensions missing",
    recovery: "return to Story work item; no autofill",
  },
  CORE_CHAPTER_CONTRACT_INVALID: {
    condition: "required chapter fields/lineage invalid",
    recovery: "preserve last valid version",
  },
  CORE_WORLD_CONTRACT_INVALID: {
    condition: "world rules/canon inconsistent",
    recovery: "block version/review; resolve contradiction",
  },
  CORE_DNA_CONTRACT_INVALID: {
    condition: "DNA type/category/ref invalid",
    recovery: "block candidate/resolve/lock; no latest fallback",
  },
  CORE_BLUEPRINT_INCOMPLETE: {
    condition: "Project/Topic blueprint required refs missing",
    recovery: "block review/lock",
  },
  CORE_SCRIPT_INVALID: {
    condition: "script exact refs/provider-neutral content invalid",
    recovery: "block version/readiness",
  },
  CORE_MACHINE_PROJECTION_LOSSY: {
    condition: "machine schema cannot represent canonical meaning",
    recovery: "block projection; open schema gap",
  },
  CORE_DECISION_MISSING: {
    condition: "human decision missing/stale",
    recovery: "return to decision; no candidate adoption",
  },
  CORE_VERSION_CONFLICT: {
    condition: "expected version/hash mismatch",
    recovery: "reload/compare/reapply as new candidate",
  },
  CORE_LOCK_EVIDENCE_MISSING: {
    condition: "reviewer/evidence/hash unresolved",
    recovery: "block lock; never fabricate",
  },
  CORE_NAMING_AUTHORITY_MISSING: {
    condition: "naming authority ref unresolved",
    recovery: "block package readiness",
  },
  CORE_PACKAGE_NOT_READY: {
    condition: "one or more required handoff edges not consumer-ready",
    recovery: "show exact blockers; no navigation bypass",
  },
  CORE_PERMISSION_DENIED: {
    condition: "permission/scope denied",
    recovery: "server deny + visible reason",
  },
  CORE_UNDEFINED_AUTHORITY_GAP: {
    condition: "unlisted required behavior/ref",
    recovery: "BLOCK + report authority gap",
  },
};

export type CoreErrorRecord = {
  kind: "CORE_ERROR";
  code: CoreErrorCode;
  condition: string;
  recovery: string;
  detail: string;
  at: string;
};

export function buildCoreError(code: string, detail: string, at: string): CoreErrorRecord | null {
  const canonical = (CORE_ERROR_CODES as readonly string[]).includes(code)
    ? (code as CoreErrorCode)
    : "CORE_UNDEFINED_AUTHORITY_GAP";
  const contract = CORE_ERROR_CONTRACT[canonical];
  return {
    kind: "CORE_ERROR",
    code: canonical,
    condition: contract.condition,
    recovery: contract.recovery,
    detail: detail.slice(0, 400),
    at,
  };
}

export function appendCoreError(raw: string | null | undefined, error: CoreErrorRecord, cap = 20): string {
  let log: CoreErrorRecord[] = [];
  try {
    const parsed = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed)) log = parsed.filter((row) => row && typeof row === "object" && typeof row.code === "string");
  } catch {
    log = [];
  }
  log.push(error);
  return JSON.stringify(log.slice(-cap));
}

export function parseCoreErrors(raw: string | null | undefined): CoreErrorRecord[] {
  try {
    const parsed = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed)) {
      return parsed.filter((row) => row && typeof row === "object" && row.kind === "CORE_ERROR") as CoreErrorRecord[];
    }
  } catch {
    return [];
  }
  return [];
}

export function latestCoreErrorCode(raw: string | null | undefined): string {
  const log = parseCoreErrors(raw);
  return log.length ? log[log.length - 1].code : "";
}
