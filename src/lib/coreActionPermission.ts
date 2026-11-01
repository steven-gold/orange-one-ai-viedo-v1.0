export type CoreActionPermissionClass =
  | "core.read"
  | "core.write"
  | "core.candidate.create"
  | "core.candidate.decide"
  | "core.project"
  | "core.dna"
  | "core.blueprint.validate"
  | "core.blueprint.approve"
  | "core.lock.request"
  | "core.lock.approve"
  | "core.script.write"
  | "core.package"
  | "core.package.handoff";

const READ_ACTIONS = new Set([
  "CORE-01-ACT-CANONICAL-SCRIPT-VIEW",
  "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-ACT-TOPIC-SELECT",
  "CORE-01-ACT-WORK-ITEM-SELECT",
  "CORE-01-ACT-THREAD-CREATE",
  "CORE-01-ACT-THREAD-DELETE",
  "CORE-01-ACT-ATTACHMENT",
  "CORE-01-ACT-REFERENCE-ATTACH",
  "CORE-01-ACT-ASSISTANT-STRUCTURED-DECISION-CREATE",
  "CORE-01-ACT-HUMAN-DECISION-RECORD",
]);

const CANDIDATE_CREATE_ACTIONS = new Set(["CORE-01-ACT-CANDIDATE-CREATE", "CORE-01-ACT-STORY-CANDIDATE", "CORE-01-ACT-STORY-CORE-REQUEST", "CORE-01-ACT-CHAPTER-ARCH-REQUEST"]);

const CANDIDATE_DECIDE_ACTIONS = new Set([
  "CORE-01-ACT-CANDIDATE-COMPARE",
  "CORE-01-ACT-CANDIDATE-EVALUATE",
  "CORE-01-ACT-CANDIDATE-ACCEPT",
  "CORE-01-ACT-CANDIDATE-RETURN",
]);

const PROJECT_ACTIONS = new Set([
  "CORE-01-ACT-PROJECT-CREATE",
  "CORE-01-ACT-PROJECT-RENAME",
  "CORE-01-ACT-PROJECT-VALIDATE",
  "CORE-01-ACT-PROJECT-CONFIRM",
  "CORE-01-ACT-PROJECT-DELETE",
  "CORE-01-ACT-TOPIC-CREATE",
  "CORE-01-ACT-TOPIC-DELETE",
  "CORE-01-ACT-CORE-REVIEW-SUBMIT",
]);

export function requiredPermissionFor(actionUid: string): CoreActionPermissionClass {
  if (READ_ACTIONS.has(actionUid)) return "core.read";
  if (actionUid === "CORE-01-ACT-DNA-LOCK-REQUEST") return "core.dna";
  if (actionUid === "CORE-01-ACT-BLUEPRINT-CREATE") return "core.write";
  if (actionUid === "CORE-01-ACT-BLUEPRINT-VALIDATE") return "core.blueprint.validate";
  if (actionUid === "CORE-01-ACT-BLUEPRINT-APPROVE") return "core.blueprint.approve";
  if (actionUid === "CORE-01-ACT-MOTHER-LOCK-REQUEST" || actionUid === "CORE-01-ACT-CHILD-LOCK-REQUEST") return "core.lock.request";
  if (actionUid === "CORE-01-ACT-MOTHER-LOCK-APPROVE" || actionUid === "CORE-01-ACT-CHILD-LOCK-APPROVE") return "core.lock.approve";
  if (actionUid === "CORE-01-ACT-PACKAGE-BUILD" || actionUid === "CORE-01-ACT-PACKAGE-READINESS-VALIDATE") return "core.package";
  if (actionUid === "CORE-01-ACT-PACKAGE-HANDOFF") return "core.package.handoff";
  if (CANDIDATE_CREATE_ACTIONS.has(actionUid)) return "core.candidate.create";
  if (CANDIDATE_DECIDE_ACTIONS.has(actionUid)) return "core.candidate.decide";
  if (PROJECT_ACTIONS.has(actionUid)) return "core.project";
  return "core.write";
}

export const CORE_PERMISSION_ACCOUNT_TOKEN = "entity.write";

export const CORE_PERMISSION_REVIEWER_ONLY = new Set<CoreActionPermissionClass>(["core.lock.approve", "core.blueprint.approve"]);
