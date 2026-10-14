import { exactName } from "./coreActionPreview";
import { resolveVideoInbound } from "./videoInbound";

export type EditInbound = {
  ready: boolean;
  project: string;
  topic: string;
  task: string;
  blueprint: string;
  childLock: string;
  dna: string;
  script: string;
  naming: string;
  videoVersion: string;
  handoffContract: string;
  sourceVersion: string;
  mediaRefs: string;
};

const VIDEO_DERIVED_FROM_INBOUND: readonly string[] = [
  "VIDEO-01-FLD-PROJECT",
  "VIDEO-01-FLD-TOPIC",
  "VIDEO-01-FLD-BLUEPRINT-REF",
  "VIDEO-01-FLD-DNA-REFS",
  "VIDEO-01-FLD-SCRIPT-SECTION",
  "VIDEO-01-FLD-ASSET-REFS",
];

export function effectiveVideoCurrent(
  coreCurrent: (uid: string) => string | null,
  assetCurrent: (uid: string) => string | null,
  videoRaw: (uid: string) => string | null,
): (uid: string) => string | null {
  const video = resolveVideoInbound(coreCurrent, assetCurrent);
  const derived: Record<string, string> = {
    "VIDEO-01-FLD-PROJECT": video.project,
    "VIDEO-01-FLD-TOPIC": video.topic,
    "VIDEO-01-FLD-BLUEPRINT-REF": video.blueprint,
    "VIDEO-01-FLD-DNA-REFS": video.dna,
    "VIDEO-01-FLD-SCRIPT-SECTION": video.script,
    "VIDEO-01-FLD-ASSET-REFS": video.assetVersion,
  };
  return (uid) => {
    if (VIDEO_DERIVED_FROM_INBOUND.includes(uid)) return derived[uid] || null;
    return videoRaw(uid);
  };
}

export function resolveEditInbound(
  videoCurrent: (uid: string) => string | null,
  coreCurrent: (uid: string) => string | null = () => null,
): EditInbound {
  const project = exactName(videoCurrent("VIDEO-01-FLD-PROJECT"));
  const topic = exactName(videoCurrent("VIDEO-01-FLD-TOPIC"));
  const blueprint = exactName(videoCurrent("VIDEO-01-FLD-BLUEPRINT-REF"));
  const dna = exactName(videoCurrent("VIDEO-01-FLD-DNA-REFS"));
  const script = exactName(videoCurrent("VIDEO-01-FLD-SCRIPT-SECTION"));
  const mediaRefs = exactName(videoCurrent("VIDEO-01-FLD-ASSET-REFS"));
  const handoffSent =
    videoCurrent("VIDEO-01-BTN-HANDOFF") === "sent" || videoCurrent("VIDEO-01-BTN-LOCK") === "locked";
  const videoVersion =
    exactName(videoCurrent("VIDEO-01-FLD-VIDEO-VERSION")) ||
    exactName(coreCurrent("CORE-01-FLD-DOWNSTREAM-VIDEO"));
  const handoffContract = exactName(videoCurrent("VIDEO-01-FLD-HANDOFF-CONTRACT")) || videoVersion;
  const ready =
    Boolean(project && topic && blueprint && dna && script) && handoffSent && Boolean(videoVersion);
  return {
    ready,
    project: ready ? project : "",
    topic: ready ? topic : "",
    task: ready && project && topic ? `${project} / ${topic}` : "",
    blueprint: ready ? blueprint : "",
    childLock: "",
    dna: ready ? dna : "",
    script: ready ? script : "",
    naming: "",
    videoVersion: ready ? videoVersion : "",
    handoffContract: ready ? handoffContract : "",
    sourceVersion: ready ? videoVersion : "",
    mediaRefs: ready ? mediaRefs : "",
  };
}
