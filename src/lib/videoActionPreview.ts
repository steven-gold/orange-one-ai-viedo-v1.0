import { exactName, namedValue, statusFromAction } from "./coreActionPreview";
import {
  VIDEO_CONVERSATION,
  ensureConversationThread,
  previewConversationAction,
} from "./conversationCore";
import {
  buildCorrectionCandidate,
  parseCorrectionScript,
  serializeCorrectionScript,
  preserveCheckAfterExecute,
  sourceMatches,
  withCorrectionStatus,
  withPreserveCheck,
} from "./correctionScript";
import {
  buildVideoScorecard,
  videoGateContextFrom,
  videoHashOf,
} from "./videoGateContract";

function named(value: string | null | undefined): string {
  return exactName(value);
}

function keep(nextValue: string | undefined, current: string | null, fallback: string): string {
  return namedValue(nextValue, named(current) || fallback);
}

function toggleMode(current: string | null): string {
  return current === "MANUAL" ? "AUTO" : "MANUAL";
}

function toggle(current: string | null, on: string, off: string): string {
  return current === on ? off : on;
}

function inboundReady(current: (uid: string) => string | null): boolean {
  return Boolean(
    named(current("VIDEO-01-FLD-PROJECT")) &&
      named(current("VIDEO-01-FLD-TOPIC")) &&
      named(current("VIDEO-01-FLD-BLUEPRINT-REF")) &&
      named(current("VIDEO-01-FLD-DNA-REFS")) &&
      named(current("VIDEO-01-FLD-SCRIPT-SECTION")) &&
      named(current("VIDEO-01-FLD-ASSET-REFS")),
  );
}

function exactSource(current: (uid: string) => string | null): string {
  return (
    named(current("VIDEO-01-FLD-VIDEO-VERSION")) ||
    named(current("VIDEO-01-FLD-CURRENT-VERSION")) ||
    named(current("VIDEO-01-FLD-CANDIDATE-VERSION")) ||
    named(current("VIDEO-01-FLD-SCRIPT-SECTION"))
  );
}

const GATED_ACTIONS = new Set([
  "VIDEO-01-ACT-MODE-SET",
  "VIDEO-01-ACT-FLOW-START",
  "VIDEO-01-ACT-LIST-SEARCH",
  "VIDEO-01-ACT-LIST-FILTER",
  "VIDEO-01-ACT-SHOT-SELECT",
  "VIDEO-01-ACT-PREVIEW-PLAY",
  "VIDEO-01-ACT-PREVIEW-SEEK",
  "VIDEO-01-ACT-PREVIEW-VOLUME",
  "VIDEO-01-ACT-PREVIEW-FULLSCREEN",
  "VIDEO-01-ACT-COMPARE-TOGGLE",
  "VIDEO-01-ACT-COMPARE-A",
  "VIDEO-01-ACT-COMPARE-B",
  "VIDEO-01-ACT-EVALUATE",
  "VIDEO-01-ACT-CANDIDATE-CONFIRM",
  "VIDEO-01-ACT-CORRECTION-OPEN",
  "VIDEO-01-ACT-VERSION-LOCK",
  "VIDEO-01-ACT-HANDOFF",
  "VIDEO-01-ACT-TASK-RETRY",
  "VIDEO-01-ACT-CORRECTION-CONTEXT",
  "VIDEO-01-ACT-CORRECTION-SCOPE-SET",
  "VIDEO-01-ACT-CORRECTION-REQUEST-SET",
  "VIDEO-01-ACT-CORRECTION-GENERATE",
  "VIDEO-01-ACT-CORRECTION-APPROVE",
  "VIDEO-01-ACT-CORRECTION-EXECUTE",
  "VIDEO-01-ACT-FINDING-CREATE",
  "VIDEO-01-ACT-ISSUE-OPEN",
  "VIDEO-01-ACT-EVALUATION-VIEW",
  "VIDEO-01-ACT-RUNTIME-VIEW",
]);

export function previewVideoAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const ready = inboundReady(current);
  if (!ready && GATED_ACTIONS.has(actionUid)) return {};
  const conversation = previewConversationAction(VIDEO_CONVERSATION, controlUid, actionUid, current, nextValue);
  if (conversation) return ready ? conversation : {};

  if (actionUid === "VIDEO-01-ACT-MODE-SET") {
    return { "VIDEO-01-CTL-MODE": toggleMode(current("VIDEO-01-CTL-MODE")) };
  }
  if (actionUid === "VIDEO-01-ACT-FLOW-START") {
    const inboundScript = named(current("VIDEO-01-FLD-SCRIPT-SECTION"));
    if (!inboundScript) return {};
    const ctx = videoGateContextFrom(current);
    return {
      "VIDEO-01-BTN-EXECUTE": "running",
      "VIDEO-01-FLD-STATUS": "running",
      "VIDEO-01-FLD-PAGE-STATE": "running",
      "VIDEO-01-FLD-TASK-STATE": "running",
      "VIDEO-01-FLD-JOB-STATE": "running",
      "VIDEO-01-FLD-SCRIPT-SECTION": inboundScript,
      "VIDEO-01-FLD-INPUT-FINGERPRINT": `VFP-${videoHashOf([ctx.project ?? "", ctx.topic ?? "", ctx.blueprint ?? "", ctx.script ?? "", ctx.assetVersion ?? ""])}`,
      "VIDEO-01-FLD-ROUTE": keep(undefined, current("VIDEO-01-FLD-ROUTE"), "就緒"),
    };
  }
  if (actionUid === "VIDEO-01-ACT-LIST-SEARCH") {
    return { "VIDEO-01-FLD-SEARCH": keep(nextValue, current("VIDEO-01-FLD-SEARCH"), "搜尋") };
  }
  if (actionUid === "VIDEO-01-ACT-LIST-FILTER") {
    const order = ["ALL", "REQUIRED", "MISSING", "DEFERRED"];
    const index = order.indexOf(current("VIDEO-01-CTL-FILTER") ?? "ALL");
    return { "VIDEO-01-CTL-FILTER": order[(index + 1) % order.length] };
  }
  if (actionUid === "VIDEO-01-ACT-SHOT-SELECT") {
    const shot = keep(nextValue, current("VIDEO-01-CTL-SHOT-SELECT"), "鏡頭 —");
    return { "VIDEO-01-CTL-SHOT-SELECT": shot };
  }
  if (actionUid === "VIDEO-01-ACT-PREVIEW-PLAY") {
    return { "VIDEO-01-BTN-PLAY": toggle(current("VIDEO-01-BTN-PLAY"), "active", "idle") };
  }
  if (actionUid === "VIDEO-01-ACT-PREVIEW-SEEK") {
    return { "VIDEO-01-FLD-TIMECODE": keep(nextValue, current("VIDEO-01-FLD-TIMECODE"), "00:00:00") };
  }
  if (actionUid === "VIDEO-01-ACT-PREVIEW-VOLUME") {
    return { "VIDEO-01-BTN-VOLUME": current("VIDEO-01-BTN-VOLUME") === "muted" ? "active" : "muted" };
  }
  if (actionUid === "VIDEO-01-ACT-PREVIEW-FULLSCREEN") {
    return { "VIDEO-01-BTN-FULLSCREEN": toggle(current("VIDEO-01-BTN-FULLSCREEN"), "active", "idle") };
  }
  if (actionUid === "VIDEO-01-ACT-COMPARE-TOGGLE") {
    return { "VIDEO-01-CTL-COMPARE": toggle(current("VIDEO-01-CTL-COMPARE"), "active", "idle") };
  }
  if (actionUid === "VIDEO-01-ACT-COMPARE-A") {
    return { "VIDEO-01-CTL-COMPARE": "idle", "VIDEO-01-CTL-VERSION-A": "active", "VIDEO-01-CTL-VERSION-B": "idle" };
  }
  if (actionUid === "VIDEO-01-ACT-COMPARE-B") {
    return { "VIDEO-01-CTL-COMPARE": "active", "VIDEO-01-CTL-VERSION-A": "idle", "VIDEO-01-CTL-VERSION-B": "active" };
  }
  if (actionUid === "VIDEO-01-ACT-BLUEPRINT-VIEW") {
    const blueprint = named(current("VIDEO-01-FLD-BLUEPRINT-REF"));
    return blueprint ? { "VIDEO-01-FLD-BLUEPRINT-REF": blueprint } : {};
  }
  if (actionUid === "VIDEO-01-ACT-SCRIPT-VIEW") {
    const script = named(current("VIDEO-01-FLD-SCRIPT-SECTION"));
    return script ? { "VIDEO-01-FLD-SCRIPT-SECTION": script } : {};
  }
  if (actionUid === "VIDEO-01-ACT-EVALUATE") {
    const ctx = videoGateContextFrom(current);
    const scorecard = buildVideoScorecard(ctx);
    if (!scorecard) return {};
    const dimensionScore = (uid: string): string => {
      const row = scorecard.dimensions.find((item) => item.uid === uid);
      if (!row) return "—";
      return row.score == null ? "PENDING" : String(row.score);
    };
    return {
      "VIDEO-01-BTN-EVALUATE": "evaluated",
      "VIDEO-01-FLD-SCORECARD": JSON.stringify(scorecard),
      "VIDEO-01-FLD-OVERALL-SCORE": `${scorecard.overall} · Total ${scorecard.weighted_total}`,
      "VIDEO-01-FLD-CRITERIA-VERSION": scorecard.criteria_version,
      "VIDEO-01-FLD-ISSUE-SUMMARY": scorecard.issues.join("；") || "無阻擋",
      "VIDEO-01-FLD-SCORE-SCRIPT": dimensionScore("QA-DIM-VIDEO-SCRIPT"),
      "VIDEO-01-FLD-SCORE-IDENTITY": dimensionScore("QA-DIM-VIDEO-IDENTITY"),
      "VIDEO-01-FLD-SCORE-MOTION": dimensionScore("QA-DIM-VIDEO-MOTION"),
      "VIDEO-01-FLD-SCORE-CAMERA": dimensionScore("QA-DIM-VIDEO-CAMERA"),
      "VIDEO-01-FLD-SCORE-SCENE": dimensionScore("QA-DIM-VIDEO-SCENE"),
      "VIDEO-01-FLD-SCORE-TIMING": dimensionScore("QA-DIM-VIDEO-TIMING"),
      "VIDEO-01-FLD-SCORE-TECH": dimensionScore("QA-DIM-VIDEO-TECH"),
      "VIDEO-01-FLD-SCORE-ASSET": dimensionScore("QA-DIM-VIDEO-ASSET"),
      "VIDEO-01-FLD-SCORE-RIGHTS": dimensionScore("QA-DIM-RIGHTS-POLICY"),
    };
  }
  if (actionUid === "VIDEO-01-ACT-CANDIDATE-CONFIRM") {
    const ctx = videoGateContextFrom(current);
    if (ctx.scorecard?.overall !== "PASS") {
      const pendingDims = (ctx.scorecard?.dimensions ?? []).filter((row) => row.score === null).map((row) => row.uid);
      const reason = pendingDims.length ? `reviewer scores pending: ${pendingDims.join(", ")}` : "evaluation must PASS per bound criteria";
      return {
        "VIDEO-01-FLD-ERROR": reason,
        "VIDEO-01-FLD-DISABLED-REASON": reason,
      };
    }
    return {
      "VIDEO-01-BTN-CONFIRM": "confirmed",
      "VIDEO-01-FLD-CANDIDATE-VERSION": keep(undefined, current("VIDEO-01-FLD-CANDIDATE-VERSION"), "候選版本"),
    };
  }
  if (actionUid === "VIDEO-01-ACT-CORRECTION-OPEN") {
    return {
      "VIDEO-01-BTN-MODIFY": "open",
      "VIDEO-01-FLD-SCENE": keep(undefined, current("VIDEO-01-FLD-SCENE"), ""),
      ...ensureConversationThread(VIDEO_CONVERSATION, current),
    };
  }
  if (actionUid === "VIDEO-01-ACT-VERSION-LOCK") {
    const ctx = videoGateContextFrom(current);
    if (ctx.confirmed !== "confirmed") return {};
    const source = ctx.outputVersion || ctx.candidateVersion || "video-output";
    const checksum = `VCKS-${videoHashOf([source, ctx.script ?? "", ctx.assetVersion ?? ""])}`;
    return {
      "VIDEO-01-BTN-LOCK": "locked",
      "VIDEO-01-FLD-VIDEO-VERSION": keep(undefined, current("VIDEO-01-FLD-VIDEO-VERSION"), source),
      "VIDEO-01-FLD-CHECKSUM": checksum,
      "VIDEO-01-FLD-SCRIPT-HASH": `SH-${videoHashOf([ctx.script ?? ""])}`,
      "VIDEO-01-FLD-ASSET-FINGERPRINT": `AFP-${videoHashOf([ctx.assetVersion ?? "", ctx.layerComposite ?? ""])}`,
      "VIDEO-01-FLD-OUTPUT-URI": `acpos://video/${source}`,
    };
  }
  if (actionUid === "VIDEO-01-ACT-HANDOFF") {
    const ctx = videoGateContextFrom(current);
    if (ctx.locked !== "locked") return {};
    const source = ctx.outputVersion || ctx.candidateVersion || "video-output";
    const manifest = {
      kind: "EXACT_VIDEO_HANDOFF_MANIFEST",
      manifest_id: `VHM-${videoHashOf([source, ctx.checksum ?? ""])}`,
      video_version: source,
      shot_versions: [source],
      layer_versions: ctx.layerComposite ? [ctx.layerComposite] : [],
      script_hash: named(current("VIDEO-01-FLD-SCRIPT-HASH")) || `SH-${videoHashOf([ctx.script ?? ""])}`,
      asset_fingerprint: named(current("VIDEO-01-FLD-ASSET-FINGERPRINT")) || `AFP-${videoHashOf([ctx.assetVersion ?? ""])}`,
      output_uri: named(current("VIDEO-01-FLD-OUTPUT-URI")) || `acpos://video/${source}`,
      checksum: ctx.checksum ?? "",
      scorecard: named(current("VIDEO-01-FLD-CRITERIA-VERSION")) || "",
      evidence: ctx.scorecard ? `${ctx.scorecard.profile} ${ctx.scorecard.overall} Total ${ctx.scorecard.weighted_total}` : "",
      handoff_contract: `EDIT-HANDOFF-${videoHashOf([source, ctx.assetVersion ?? ""])}`,
    };
    return {
      "VIDEO-01-BTN-HANDOFF": "sent",
      "VIDEO-01-FLD-VIDEO-VERSION": source,
      "VIDEO-01-FLD-SHOT-VERSIONS": manifest.shot_versions.join("、"),
      "VIDEO-01-FLD-LAYER-VERSIONS": manifest.layer_versions.join("、") || "—",
      "VIDEO-01-FLD-SCRIPT-HASH": manifest.script_hash,
      "VIDEO-01-FLD-ASSET-FINGERPRINT": manifest.asset_fingerprint,
      "VIDEO-01-FLD-OUTPUT-URI": manifest.output_uri,
      "VIDEO-01-FLD-CHECKSUM": manifest.checksum,
      "VIDEO-01-FLD-SCORECARD": manifest.scorecard || named(current("VIDEO-01-FLD-SCORECARD")) || "",
      "VIDEO-01-FLD-EVIDENCE": manifest.evidence || "—",
      "VIDEO-01-FLD-HANDOFF-CONTRACT": JSON.stringify(manifest),
    };
  }
  if (actionUid === "VIDEO-01-ACT-TASK-RETRY") {
    return {
      "VIDEO-01-BTN-RETRY": "retrying",
      "VIDEO-01-FLD-ATTEMPT": String((Number.parseInt(current("VIDEO-01-FLD-ATTEMPT") ?? "0", 10) || 0) + 1),
      "VIDEO-01-FLD-JOB-STATE": "retrying",
    };
  }
  if (actionUid === "VIDEO-01-ACT-CORRECTION-CONTEXT") {
    return { "VIDEO-01-FLD-ISSUE-REF": keep(undefined, current("VIDEO-01-FLD-ISSUE-REF"), "已建立修正內容") };
  }
  if (actionUid === "VIDEO-01-ACT-CORRECTION-SCOPE-SET") {
    return { [controlUid]: keep(nextValue, current(controlUid), named(current("VIDEO-01-FLD-SCENE")) || "當前場景") };
  }
  if (actionUid === "VIDEO-01-ACT-CORRECTION-REQUEST-SET") {
    const request = namedValue(nextValue, named(current("VIDEO-01-TXT-CORRECTION")));
    return request ? { "VIDEO-01-TXT-CORRECTION": request } : {};
  }
  if (actionUid === "VIDEO-01-ACT-CORRECTION-GENERATE") {
    const request = namedValue(nextValue, named(current("VIDEO-01-TXT-CORRECTION")));
    const source = exactSource(current);
    const scope =
      named(current("VIDEO-01-FLD-SHOT")) ||
      named(current("VIDEO-01-FLD-SCENE")) ||
      named(current("VIDEO-01-CTL-SHOT-SELECT")) ||
      source;
    const candidate = buildCorrectionCandidate({
      department: "VIDEO",
      exact_source_version: source,
      target_scope: scope,
      requested_delta: request,
      expected_output_kind: "OutputVersion",
    });
    if (!candidate) return {};
    return {
      "VIDEO-01-BTN-MODIFY": "open",
      "VIDEO-01-BTN-GEN-CORRECTION": "created",
      "VIDEO-01-BTN-APPROVE-CORRECTION": "idle",
      "VIDEO-01-BTN-EXEC-CORRECTION": "idle",
      "VIDEO-01-TXT-CORRECTION": request,
      "VIDEO-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(candidate),
    };
  }
  if (actionUid === "VIDEO-01-ACT-CORRECTION-APPROVE") {
    const source = exactSource(current);
    const candidate = parseCorrectionScript(current("VIDEO-01-FLD-CORRECTION-RESPONSE"));
    if (!sourceMatches(candidate, source) || candidate?.status !== "CANDIDATE") return {};
    return {
      "VIDEO-01-BTN-APPROVE-CORRECTION": "approved",
      "VIDEO-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(withCorrectionStatus(candidate, "APPROVED")),
    };
  }
  if (actionUid === "VIDEO-01-ACT-CORRECTION-EXECUTE") {
    const source = exactSource(current);
    const candidate = parseCorrectionScript(current("VIDEO-01-FLD-CORRECTION-RESPONSE"));
    if (!sourceMatches(candidate, source) || candidate?.status !== "APPROVED") return {};
    const check = preserveCheckAfterExecute(candidate, source);
    if (!check.passed) {
      return {
        "VIDEO-01-BTN-EXEC-CORRECTION": "idle",
        "VIDEO-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(withPreserveCheck(candidate, check)),
      };
    }
    return {
      "VIDEO-01-BTN-EXEC-CORRECTION": "running",
      "VIDEO-01-FLD-TASK-STATE": "running",
      "VIDEO-01-FLD-CORRECTION-RESPONSE": serializeCorrectionScript(withPreserveCheck(candidate, check)),
    };
  }
  if (actionUid === "VIDEO-01-ACT-FINDING-CREATE") {
    return { "VIDEO-01-BTN-FINDING": "created" };
  }
  if (actionUid === "VIDEO-01-ACT-ISSUE-OPEN") {
    return { "VIDEO-01-BTN-ISSUE-OPEN": "open" };
  }
  if (actionUid === "VIDEO-01-ACT-EVALUATION-VIEW") {
    return { "VIDEO-01-BTN-SCORE-DETAIL": "active" };
  }
  if (actionUid === "VIDEO-01-ACT-RUNTIME-VIEW") {
    return {
      "VIDEO-01-BTN-RUNTIME-DETAIL": "active",
      "VIDEO-01-FLD-ROUTE": keep(undefined, current("VIDEO-01-FLD-ROUTE"), "就緒"),
    };
  }
  if (actionUid === "VIDEO-01-ACT-NOOP-VIEW") {
    return {};
  }
  if (
    actionUid === "VIDEO-01-ACT-PROJECT-SET" ||
    actionUid === "VIDEO-01-ACT-TOPIC-SET" ||
    actionUid === "VIDEO-01-ACT-TASK-SET"
  ) {
    return {};
  }
  if (!ready) return {};
  const inboundOnly = new Set([
    "VIDEO-01-FLD-SCRIPT-SECTION",
    "VIDEO-01-FLD-BLUEPRINT-REF",
    "VIDEO-01-FLD-DNA-REFS",
    "VIDEO-01-FLD-INSTRUCTION",
    "VIDEO-01-FLD-ASSET-REFS",
  ]);
  if (inboundOnly.has(controlUid)) {
    const existing = named(current(controlUid));
    return existing ? { [controlUid]: existing } : {};
  }
  return { [controlUid]: nextValue ?? statusFromAction(actionUid) };
}
