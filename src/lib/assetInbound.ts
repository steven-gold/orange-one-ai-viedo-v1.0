import { exactName } from "./coreActionPreview";

export type AssetInbound = {
  ready: boolean;
  project: string;
  topic: string;
  task: string;
  blueprint: string;
  childLock: string;
  dna: string;
  script: string;
  naming: string;
};

export function resolveAssetInbound(current: (uid: string) => string | null): AssetInbound {
  const project = exactName(current("CORE-01-CTL-PROJECT"));
  const topic = exactName(current("CORE-01-CTL-TOPIC"));
  const confirmed =
    Boolean(project) &&
    (current("CORE-01-BTN-PROJECT-CONFIRM") === "confirmed" || current("CORE-01-BTN-PROJECT-LOCK") === project);
  const blueprint =
    exactName(current("CORE-01-BTN-BLUEPRINT-CREATE")) || exactName(current("CORE-01-FLD-PACKAGE"));
  const childLock = exactName(current("CORE-01-BTN-CHILD-LOCK"));
  const dna = exactName(current("CORE-01-BTN-DNA-LOCK"));
  const script = exactName(current("CORE-01-BTN-CANONICAL-SCRIPT"));
  const naming = exactName(current("CORE-01-FLD-NAMING-AUTHORITY")) || "ACPOS_SYSTEM";
  const ready = Boolean(project && confirmed && topic && blueprint && childLock && dna && script);
  return {
    ready,
    project: ready ? project : "",
    topic: ready ? topic : "",
    task: ready ? `${project} / ${topic}` : "",
    blueprint: ready ? blueprint : "",
    childLock: ready ? childLock : "",
    dna: ready ? dna : "",
    script: ready ? script : "",
    naming: ready ? naming : "",
  };
}
