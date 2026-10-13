import { resolveAssetInbound } from "./assetInbound";
import { exactName } from "./coreActionPreview";

export type VideoInbound = {
  ready: boolean;
  project: string;
  topic: string;
  task: string;
  blueprint: string;
  childLock: string;
  dna: string;
  script: string;
  assetVersion: string;
  filename: string;
  checksum: string;
  instruction: string;
  rights: string;
  naming: string;
};

export function resolveVideoInbound(
  coreCurrent: (uid: string) => string | null,
  assetCurrent: (uid: string) => string | null,
): VideoInbound {
  const core = resolveAssetInbound(coreCurrent);
  const assetVersion =
    exactName(assetCurrent("ASSET-01-FLD-HANDOFF-ASSET-VERSION")) || exactName(assetCurrent("ASSET-01-FLD-MANIFEST"));
  const handoffSent =
    assetCurrent("ASSET-01-BTN-HANDOFF") === "sent" || assetCurrent("ASSET-01-BTN-LOCK") === "locked";
  const filename =
    exactName(assetCurrent("ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME")) ||
    exactName(assetCurrent("ASSET-01-FLD-CANONICAL-FILENAME"));
  const checksum =
    exactName(assetCurrent("ASSET-01-FLD-HANDOFF-CHECKSUM")) || exactName(assetCurrent("ASSET-01-FLD-CHECKSUM"));
  const instruction = exactName(assetCurrent("ASSET-01-FLD-HANDOFF-CONTRACT-HASH"));
  const rights = exactName(assetCurrent("ASSET-01-FLD-HANDOFF-RIGHTS")) || exactName(assetCurrent("ASSET-01-FLD-RIGHTS"));
  const ready =
    core.ready &&
    Boolean(assetVersion) &&
    handoffSent &&
    Boolean(core.blueprint) &&
    Boolean(core.dna) &&
    Boolean(core.script);
  const task = ready && core.project && core.topic ? `${core.project} / ${core.topic}` : "";
  return {
    ready,
    project: ready ? core.project : "",
    topic: ready ? core.topic : "",
    task,
    blueprint: ready ? core.blueprint : "",
    childLock: ready ? core.childLock : "",
    dna: ready ? core.dna : "",
    script: ready ? core.script : "",
    assetVersion: ready ? assetVersion : "",
    filename: ready ? filename : "",
    checksum: ready ? checksum : "",
    instruction: ready ? instruction : "",
    rights: ready ? rights : "",
    naming: ready ? core.naming : "",
  };
}
