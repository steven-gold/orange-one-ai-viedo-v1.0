import { exactName } from "./coreActionPreview";
import { resolveVideoInbound } from "./videoInbound";

export type EditInbound = {
  ready: boolean;
  standalone: boolean;
  mode: string;
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

// EDIT unlocks on the same Project + Topic context as ASSET/VIDEO when in
// PROJECT_TASK mode. STANDALONE_UPLOAD is a first-class Source Mode that needs no
// Project/Topic and never claims Blueprint/DNA (owner session media / uploaded spec).
export function resolveEditInbound(
  videoCurrent: (uid: string) => string | null,
  coreCurrent: (uid: string) => string | null = () => null,
  editCurrent: (uid: string) => string | null = () => null,
): EditInbound {
  const project = exactName(videoCurrent("VIDEO-01-FLD-PROJECT"));
  const topic = exactName(videoCurrent("VIDEO-01-FLD-TOPIC"));
  const blueprint = exactName(videoCurrent("VIDEO-01-FLD-BLUEPRINT-REF"));
  const dna = exactName(videoCurrent("VIDEO-01-FLD-DNA-REFS"));
  const script = exactName(videoCurrent("VIDEO-01-FLD-SCRIPT-SECTION"));
  const mediaRefs = exactName(videoCurrent("VIDEO-01-FLD-ASSET-REFS"));
  const videoVersion =
    exactName(videoCurrent("VIDEO-01-FLD-VIDEO-VERSION")) ||
    exactName(coreCurrent("CORE-01-FLD-DOWNSTREAM-VIDEO"));
  const handoffContract = exactName(videoCurrent("VIDEO-01-FLD-HANDOFF-CONTRACT")) || videoVersion;
  const mode = exactName(editCurrent("EDIT-01-CTL-SOURCE-MODE")) || "PROJECT_TASK";
  const standalone = mode === "STANDALONE_UPLOAD";
  const ready = Boolean(project && topic);
  return {
    ready,
    standalone,
    mode,
    project,
    topic,
    task: project && topic ? `${project} / ${topic}` : "",
    blueprint,
    childLock: "",
    dna,
    script,
    naming: "",
    videoVersion,
    handoffContract,
    sourceVersion: videoVersion,
    mediaRefs,
  };
}
