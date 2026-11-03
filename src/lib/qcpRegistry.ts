// Canonical Quality Governance registry (QA-SYNC-01..03, spec doc
// ACPOS-20260921-NINE-SYSTEM-QA-SYNC-V1): static canonical catalog with
// concrete profile rows. Pages MUST resolve an exact approved profile from
// here - generic/default/latest resolution is forbidden.

export const QGP_POLICY_VERSION = "QGP-V1";

export type QcpDimensionSpec = { uid: string; label: string; weight: number; hard_block: boolean };

export type QcpProfileRow = {
  uid: string;
  owner: "CORE" | "ASSET" | "VIDEO" | "EDITING" | "QA";
  applicability: string;
  threshold: 95;
  dimensions: QcpDimensionSpec[] | null;
};

const RIGHTS_DIMENSION: QcpDimensionSpec = { uid: "QA-DIM-RIGHTS-POLICY", label: "Rights / Policy", weight: 5, hard_block: true };

export const QCP_REGISTRY: QcpProfileRow[] = [
  {
    uid: "QCP-CORE-BASELINE-V1",
    owner: "CORE",
    applicability: "CORE / Blueprint / Canonical Script",
    threshold: 95,
    dimensions: null,
  },
  {
    uid: "QCP-ASSET-IMAGE-V1",
    owner: "ASSET",
    applicability: "IMAGE asset outputs",
    threshold: 95,
    dimensions: [
      { uid: "QA-DIM-ASSET-SCRIPT", label: "Script / Manifest Compliance", weight: 15, hard_block: false },
      { uid: "QA-DIM-ASSET-IDENTITY", label: "Character / Identity DNA Fidelity", weight: 20, hard_block: false },
      { uid: "QA-DIM-ASSET-OBJECT", label: "Object Fidelity", weight: 10, hard_block: false },
      { uid: "QA-DIM-ASSET-SCENE", label: "Scene / Environment Fidelity", weight: 10, hard_block: false },
      { uid: "QA-DIM-ASSET-COMPOSITION", label: "Composition / Framing", weight: 10, hard_block: false },
      { uid: "QA-DIM-ASSET-GEOMETRY", label: "Anatomy / Geometry / Artifact Integrity", weight: 15, hard_block: false },
      { uid: "QA-DIM-ASSET-STYLE", label: "Style / Color / Lighting Consistency", weight: 10, hard_block: false },
      { uid: "QA-DIM-ASSET-TECH", label: "Technical Image Quality", weight: 5, hard_block: false },
      RIGHTS_DIMENSION,
    ],
  },
  {
    uid: "QCP-ASSET-AUDIO-V1",
    owner: "ASSET",
    applicability: "VOICE / MUSIC / SFX outputs",
    threshold: 95,
    dimensions: [
      { uid: "QA-DIM-AUDIO-SCRIPT", label: "Script / Manifest Compliance", weight: 15, hard_block: false },
      { uid: "QA-DIM-AUDIO-IDENTITY", label: "Voice Identity / Semantic Fit", weight: 20, hard_block: false },
      { uid: "QA-DIM-AUDIO-CONTENT", label: "Pronunciation / Content Accuracy", weight: 15, hard_block: false },
      { uid: "QA-DIM-AUDIO-TIMING", label: "Timing / Duration", weight: 10, hard_block: false },
      { uid: "QA-DIM-AUDIO-NOISE", label: "Noise / Clipping / Distortion", weight: 15, hard_block: false },
      { uid: "QA-DIM-AUDIO-LEVEL", label: "Level / Dynamics", weight: 10, hard_block: false },
      { uid: "QA-DIM-AUDIO-TECH", label: "Technical Audio Format", weight: 10, hard_block: false },
      RIGHTS_DIMENSION,
    ],
  },
  {
    uid: "QCP-VIDEO-BASELINE-V1",
    owner: "VIDEO",
    applicability: "VIDEO candidate outputs",
    threshold: 95,
    dimensions: [
      { uid: "QA-DIM-VIDEO-SCRIPT", label: "Script / Manifest Compliance", weight: 15, hard_block: false },
      { uid: "QA-DIM-VIDEO-IDENTITY", label: "Identity / DNA Fidelity", weight: 20, hard_block: false },
      { uid: "QA-DIM-VIDEO-MOTION", label: "Motion / Body Mechanics", weight: 10, hard_block: false },
      { uid: "QA-DIM-VIDEO-CAMERA", label: "Camera / Gaze Intent", weight: 10, hard_block: false },
      { uid: "QA-DIM-VIDEO-SCENE", label: "Scene / Continuity", weight: 10, hard_block: false },
      { uid: "QA-DIM-VIDEO-TIMING", label: "Timing / Duration", weight: 10, hard_block: false },
      { uid: "QA-DIM-VIDEO-TECH", label: "Technical Quality", weight: 10, hard_block: false },
      { uid: "QA-DIM-VIDEO-ASSET", label: "Asset / DNA Fidelity", weight: 10, hard_block: false },
      RIGHTS_DIMENSION,
    ],
  },
  {
    uid: "QCP-EDIT-FINAL-V1",
    owner: "EDITING",
    applicability: "EDIT stage / final outputs",
    threshold: 95,
    dimensions: [
      { uid: "QA-DIM-EDIT-ASSEMBLY", label: "Assembly", weight: 10, hard_block: false },
      { uid: "QA-DIM-EDIT-PACING", label: "Pacing", weight: 10, hard_block: false },
      { uid: "QA-DIM-EDIT-CONTINUITY", label: "Visual/Frame Continuity", weight: 10, hard_block: false },
      { uid: "QA-DIM-EDIT-VOICE", label: "Voice", weight: 10, hard_block: false },
      { uid: "QA-DIM-EDIT-BGM", label: "BGM", weight: 5, hard_block: false },
      { uid: "QA-DIM-EDIT-SFX", label: "SFX", weight: 5, hard_block: false },
      { uid: "QA-DIM-EDIT-AV-SYNC", label: "AV Sync", weight: 10, hard_block: false },
      { uid: "QA-DIM-EDIT-LIP-SYNC", label: "Lip Sync", weight: 10, hard_block: false },
      { uid: "QA-DIM-EDIT-SUBTITLE-CONTENT", label: "Subtitle Content", weight: 10, hard_block: false },
      { uid: "QA-DIM-EDIT-SUBTITLE-TIMING", label: "Subtitle Timing/Readability", weight: 10, hard_block: false },
      { uid: "QA-DIM-EDIT-TECH", label: "Technical", weight: 5, hard_block: false },
      RIGHTS_DIMENSION,
    ],
  },
  {
    uid: "QCP-QA-FINAL-OUTPUT-V1",
    owner: "QA",
    applicability: "Final output / release-candidate review",
    threshold: 95,
    dimensions: null,
  },
];

// Resolve an exact approved profile by UID. Registry rows are the approved
// baseline; rows with dimensions === null have dimension authority pending
// and resolve as metadata only.
export function resolveApprovedCriteria(profileUid: string): QcpProfileRow | null {
  return QCP_REGISTRY.find((row) => row.uid === profileUid) ?? null;
}
