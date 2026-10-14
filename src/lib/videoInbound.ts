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

// The VIDEO page is unlocked by the same Project + Topic context as ASSET.
// Asset handoff refs are resolved independently and stay fail-closed per action.
export function resolveVideoInbound(
  coreCurrent: (uid: string) => string | null,
  assetCurrent: (uid: string) => string | null,
): VideoInbound {
  const core = resolveAssetInbound(coreCurrent);
  const assetVersion =
    exactName(assetCurrent("ASSET-01-FLD-HANDOFF-ASSET-VERSION")) || exactName(assetCurrent("ASSET-01-FLD-MANIFEST"));
  const filename =
    exactName(assetCurrent("ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME")) ||
    exactName(assetCurrent("ASSET-01-FLD-CANONICAL-FILENAME"));
  const checksum =
    exactName(assetCurrent("ASSET-01-FLD-HANDOFF-CHECKSUM")) || exactName(assetCurrent("ASSET-01-FLD-CHECKSUM"));
  const instruction = exactName(assetCurrent("ASSET-01-FLD-HANDOFF-CONTRACT-HASH"));
  const rights = exactName(assetCurrent("ASSET-01-FLD-HANDOFF-RIGHTS")) || exactName(assetCurrent("ASSET-01-FLD-RIGHTS"));
  const ready = core.ready;
  return {
    ready,
    project: core.project,
    topic: core.topic,
    task: core.project && core.topic ? `${core.project} / ${core.topic}` : "",
    blueprint: core.blueprint,
    childLock: core.childLock,
    dna: core.dna,
    script: core.script,
    assetVersion,
    filename,
    checksum,
    instruction,
    rights,
    naming: core.naming,
  };
}
