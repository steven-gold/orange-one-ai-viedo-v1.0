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
};

function named(value: string | null | undefined): string {
  return exactName(value);
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
    named(editCurrent("EDIT-01-LBL-BINDING-FINGERPRINT")) || inbound.handoffContract;
  const criteriaVersion =
    named(editCurrent("EDIT-01-LBL-EVAL-SUMMARY")) || (locked && handed ? targetOutput || checksum : "");
  const rights = named(videoCurrent("VIDEO-01-FLD-RIGHTS")) || video.rights;
  const provenance = checksum;
  const ready = Boolean(inbound.ready && locked && handed && targetOutput && scriptView && criteriaVersion);
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
  };
}
