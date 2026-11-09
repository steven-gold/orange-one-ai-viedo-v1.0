import { exactName } from "./coreActionPreview";
import { resolveEditInbound, effectiveVideoCurrent } from "./editInbound";
import { resolveVideoInbound } from "./videoInbound";

export type QaInbound = {
  ready: boolean;
  project: string;
  topic: string;
  task: string;
  targetOutput: string;
  scriptView: string;
  scriptHash: string;
  criteriaVersion: string;
  checksum: string;
  rights: string;
  provenance: string;
  policy: string;
  requiredChecks: string;
  gateStatus: string;
  hardBlock: string;
};

function named(value: string | null | undefined): string {
  return exactName(value);
}

// The binding fingerprint carries the full handoff manifest JSON as evidence;
// gate matching needs the exact checksum hash, so extract it from the JSON and
// keep plain values (legacy checksum strings) untouched.
function fingerprintChecksum(value: string | null | undefined): string {
  const raw = (value ?? "").trim();
  if (!raw) return "";
  if (raw.startsWith("{")) {
    try {
      const checksum = (JSON.parse(raw) as { checksum?: unknown }).checksum;
      return typeof checksum === "string" ? checksum : "";
    } catch {
      return "";
    }
  }
  return raw;
}

export function resolveQaInbound(
  coreCurrent: (uid: string) => string | null,
  assetCurrent: (uid: string) => string | null,
  videoCurrent: (uid: string) => string | null,
  editCurrent: (uid: string) => string | null,
): QaInbound {
  const inbound = resolveEditInbound(
    effectiveVideoCurrent(coreCurrent, assetCurrent, videoCurrent),
    coreCurrent,
    editCurrent,
  );
  const video = resolveVideoInbound(coreCurrent, assetCurrent);
  const locked = editCurrent("EDIT-01-BTN-VERSION-LOCK") === "locked";
  const handed = editCurrent("EDIT-01-BTN-HANDOFF-2") === "sent";
  const targetOutput =
    named(editCurrent("EDIT-01-FLD-SOURCE-VERSION")) ||
    named(coreCurrent("CORE-01-FLD-DOWNSTREAM-EDIT")) ||
    inbound.sourceVersion;
  const scriptView =
    named(editCurrent("EDIT-01-LBL-CURRENT-SCRIPT-SECTION")) || inbound.script;
  const checksum =
    fingerprintChecksum(editCurrent("EDIT-01-LBL-BINDING-FINGERPRINT")) ||
    fingerprintChecksum(inbound.handoffContract);
  const criteriaVersion =
    named(editCurrent("EDIT-01-LBL-EVAL-SUMMARY")) || (locked && handed ? targetOutput || checksum : "");
  const rights = named(videoCurrent("VIDEO-01-FLD-RIGHTS")) || video.rights;
  const provenance = checksum;
  const ready = Boolean(inbound.ready && locked && handed && targetOutput && scriptView && criteriaVersion);
  // Release gate contract: fixed rule version + mandatory checks; the gate is
  // BLOCKED only on missing exact evidence (checksum / rights), otherwise OPEN.
  const policy = ready ? "QA-GATE-V1" : "";
  const requiredChecks = ready ? "SCORE_BASELINE,CHECKSUM,RIGHTS" : "";
  const blockers = [!checksum && "CHECKSUM_MISSING", !rights && "RIGHTS_MISSING"].filter(Boolean).join(",");
  const hardBlock = ready ? blockers || "none" : "";
  const gateStatus = ready ? (blockers ? "BLOCKED" : "OPEN") : "";
  return {
    ready,
    project: inbound.project,
    topic: inbound.topic,
    task: inbound.project && inbound.topic ? `${inbound.project} / ${inbound.topic}` : "",
    targetOutput,
    scriptView,
    scriptHash: scriptView,
    criteriaVersion,
    checksum,
    rights,
    provenance,
    policy,
    requiredChecks,
    gateStatus,
    hardBlock,
  };
}
