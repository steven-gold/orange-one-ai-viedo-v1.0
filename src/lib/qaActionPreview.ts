import { exactName, namedValue, statusFromAction } from "./coreActionPreview";

function named(value: string | null | undefined): string {
  return exactName(value);
}

function inboundReady(current: (uid: string) => string | null): boolean {
  return Boolean(
    named(current("QA-01-FLD-PROJECT")) &&
      named(current("QA-01-FLD-TOPIC")) &&
      named(current("QA-01-FLD-TARGET-OUTPUT")) &&
      named(current("QA-01-FLD-QA-SCRIPT")) &&
      named(current("QA-01-FLD-CRITERIA-VERSION")),
  );
}

const GATED_ACTIONS = new Set([
  "QA-01-ACT-START-REVIEW",
  "QA-01-ACT-AUTO-START",
  "QA-01-ACT-COMPARE-TOGGLE",
  "QA-01-ACT-CORRECTION-REQUEST",
  "QA-01-ACT-EVIDENCE-VIEW",
  "QA-01-ACT-EVIDENCE-RANGE-IN",
  "QA-01-ACT-EVIDENCE-RANGE-OUT",
  "QA-01-ACT-FINDING-CREATE",
  "QA-01-ACT-EVIDENCE-POINT",
  "QA-01-ACT-VIEWER-FULLSCREEN",
  "QA-01-ACT-MANUAL-MODIFY",
  "QA-01-ACT-MANUAL-PASS",
  "QA-01-ACT-MANUAL-VIEW",
  "QA-01-ACT-VIEWER-NEXT-FRAME",
  "QA-01-ACT-VIEWER-PLAY",
  "QA-01-ACT-VIEWER-PREV-FRAME",
  "QA-01-ACT-RECHECK-START",
  "QA-01-ACT-RELEASE-CREATE",
  "QA-01-ACT-SCRIPT-VIEW",
  "QA-01-ACT-VIEWER-VOLUME",
  "QA-01-ACT-VIEWER-SEEK",
  "QA-01-ACT-FINDING-SELECT",
]);

export function previewQaAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const ready = inboundReady(current);
  if (!ready && GATED_ACTIONS.has(actionUid)) return {};

  if (actionUid === "QA-01-ACT-SCRIPT-VIEW") {
    const script = named(current("QA-01-FLD-QA-SCRIPT"));
    return script ? { "QA-01-FLD-QA-SCRIPT": script, "QA-01-FLD-SCRIPT-HASH": named(current("QA-01-FLD-SCRIPT-HASH")) || script } : {};
  }
  if (actionUid === "QA-01-ACT-START-REVIEW") {
    if (!named(current("QA-01-FLD-TARGET-OUTPUT")) || !named(current("QA-01-FLD-CRITERIA-VERSION"))) return {};
    return {
      "QA-01-BTN-START-REVIEW": "open",
      "QA-01-FLD-REVIEW-STATE": "IN_REVIEW",
      "QA-01-FLD-QA-TASK": named(current("QA-01-FLD-QA-TASK")) || named(current("QA-01-FLD-TARGET-OUTPUT")),
    };
  }
  if (actionUid === "QA-01-ACT-AUTO-START") {
    if (!named(current("QA-01-FLD-TARGET-OUTPUT")) || !named(current("QA-01-FLD-CRITERIA-VERSION"))) return {};
    return {
      "QA-01-BTN-AUTO-START": "running",
      "QA-01-FLD-REVIEW-STATE": "IN_REVIEW",
      "QA-01-FLD-AUTO-PROGRESS": named(current("QA-01-FLD-AUTO-PROGRESS")) || "running",
    };
  }
  if (actionUid === "QA-01-ACT-FINDING-CREATE") {
    return {
      "QA-01-BTN-FINDING-CREATE": "created",
      "QA-01-FLD-OPEN-FINDINGS": namedValue(nextValue, named(current("QA-01-FLD-OPEN-FINDINGS")) || named(current("QA-01-FLD-TARGET-OUTPUT"))),
      "QA-01-FLD-REVIEW-STATE": "FINDING_OPEN",
    };
  }
  if (actionUid === "QA-01-ACT-CORRECTION-REQUEST") {
    const finding = named(current("QA-01-FLD-OPEN-FINDINGS"));
    if (!finding) return {};
    return {
      "QA-01-BTN-CORRECTION": "returned",
      "QA-01-FLD-REVIEW-STATE": "RECHECK",
      "QA-01-FLD-FAILED-VERSION": named(current("QA-01-FLD-TARGET-OUTPUT")),
    };
  }
  if (actionUid === "QA-01-ACT-RECHECK-START") {
    const output = named(current("QA-01-FLD-TARGET-OUTPUT"));
    const criteria = named(current("QA-01-FLD-CRITERIA-VERSION"));
    if (!output || !criteria) return {};
    return {
      "QA-01-BTN-RECHECK": "rechecked",
      "QA-01-FLD-RECHECK-STATUS": named(current("QA-01-FLD-RECHECK-STATUS")) || "rechecked",
      "QA-01-FLD-NEW-VERSION": named(current("QA-01-FLD-NEW-VERSION")) || output,
    };
  }
  if (actionUid === "QA-01-ACT-RELEASE-CREATE") {
    const output = named(current("QA-01-FLD-TARGET-OUTPUT"));
    const gate = named(current("QA-01-FLD-GATE-STATUS"));
    if (!output || gate === "BLOCKED") return {};
    return {
      "QA-01-BTN-RELEASE-CREATE": "created",
      "QA-01-FLD-REL-OUTPUTS": output,
      "QA-01-FLD-REL-PACKAGE": named(current("QA-01-FLD-REL-PACKAGE")) || output,
      "QA-01-FLD-REL-QA-GATE": named(current("QA-01-FLD-GATE-STATUS")),
    };
  }
  if (actionUid === "QA-01-ACT-NOOP-VIEW") {
    const existing = named(current(controlUid));
    return existing ? { [controlUid]: existing } : {};
  }
  const inboundOnly = new Set([
    "QA-01-FLD-PROJECT",
    "QA-01-FLD-TOPIC",
    "QA-01-FLD-TARGET-OUTPUT",
    "QA-01-FLD-QA-SCRIPT",
    "QA-01-FLD-SCRIPT-HASH",
    "QA-01-FLD-CRITERIA-VERSION",
    "QA-01-FLD-CHECKSUM",
    "QA-01-FLD-RIGHTS",
    "QA-01-FLD-PROVENANCE",
  ]);
  if (inboundOnly.has(controlUid)) {
    const existing = named(current(controlUid));
    return existing ? { [controlUid]: existing } : {};
  }
  if (!ready && !GATED_ACTIONS.has(actionUid)) {
    const existing = named(current(controlUid));
    return existing ? { [controlUid]: existing } : {};
  }
  return { [controlUid]: nextValue ?? statusFromAction(actionUid) };
}
