import type { CanonicalScriptProjection } from "./coreActionPreview";

export type PackageSection = {
  section: string;
  ref: string;
  status: "RESOLVED" | "MISSING";
  blocker?: string;
};

export type ProductionPackage = {
  kind: "PRODUCTION_PACKAGE";
  version: string;
  project_id: string;
  topic_id: string;
  based_on_structure_ref: string;
  blueprint_ref: string;
  blueprint_lock_state: string;
  dna_refs: string[];
  script_refs: { human_canonical: string; machine_structured: string; machine_schema: string; output_hash: string };
  view_refs: string[];
  continuity: { starting_state: string; ending_state: string; open_loops: string; payoff_refs: string };
  requirements: { asset_manifest: string[]; anchors: string[] };
  policy: { naming_authority: string; rights: string; quality: string };
  readiness: { ASSET: string; VIDEO: string; EDIT: string; QA: string; missing_blockers: string[] };
  audit: { candidate_ref: string; human_decision: string; lock_state: string };
  sections: PackageSection[];
  status: "BUILDING" | "READY" | "BLOCKED";
  at: string;
};

function stableHash(parts: string[]): string {
  let hash = 2166136261;
  const joined = parts.join("\u0001");
  for (let index = 0; index < joined.length; index += 1) {
    hash ^= joined.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function section(ref: string, name: string, blocker?: string): PackageSection {
  return ref ? { section: name, ref, status: "RESOLVED" } : { section: name, ref: "", status: "MISSING", blocker: blocker ?? `${name} ref unresolved` };
}

export function buildProductionPackage(input: {
  projectId: string;
  topicId: string;
  basedOnStructureRef: string;
  blueprintRef: string;
  blueprintLockState: string;
  dnaRefs: string[];
  projection: CanonicalScriptProjection | null;
  preboundWorkspaces: { asset: string; video: string; edit: string };
  namingAuthority: string;
  candidateRef: string;
  humanDecision: string;
  lockState: string;
  at: string;
}): ProductionPackage {
  const projection = input.projection;
  const scriptVersion = projection?.version ?? "";
  const machineHash = projection?.machine?.output_hash ?? "";
  const viewRefs = (projection?.views?.views ?? []).map((row) => row.view_ref).filter(Boolean);
  const continuity = projection?.continuity;
  const dnaRefs = input.dnaRefs.filter(Boolean);

  const dnaBaseRef = input.dnaRefs[0] ?? "";
  const dnaEnrichmentRef = input.dnaRefs[1] ?? "";

  const sections = [
    section(input.projectId, "project", "project id unresolved"),
    section(input.topicId, "topic", "topic id unresolved"),
    section(input.blueprintRef, "blueprint", "blueprint version unresolved"),
    ...(["STORY", "WORLD", "CHARACTER", "NARRATIVE"] as const).map((name) =>
      section(dnaBaseRef, `dna:${name}`, `DNA ${name} locked ref missing`),
    ),
    section(dnaEnrichmentRef, "dna:enrichment", "DNA enrichment ref missing"),
    section(scriptVersion, "script:human_canonical", "canonical script version missing"),
    section(machineHash, "script:machine_structured", "machine projection output hash missing"),
    ...(viewRefs.length ? viewRefs.map((ref) => section(ref, "views")) : [{ section: "views", ref: "", status: "MISSING" as const, blocker: "media views missing" }]),
    section(continuity?.starting_state ? continuity.starting_state : "", "continuity:starting_state", "starting state missing"),
    section(continuity?.ending_state ? continuity.ending_state : "", "continuity:ending_state", "ending state missing"),
    section(input.namingAuthority, "policy:naming_authority", "naming authority unresolved"),
  ];

  const missingBlockers = sections.filter((row) => row.status === "MISSING").map((row) => row.blocker ?? row.section);
  const edgesReady = missingBlockers.length === 0;
  const version = stableHash([
    input.projectId,
    input.topicId,
    input.blueprintRef,
    ...dnaRefs,
    scriptVersion,
    machineHash,
    ...viewRefs,
    continuity?.starting_state ?? "",
    continuity?.ending_state ?? "",
    input.at,
  ]);

  return {
    kind: "PRODUCTION_PACKAGE",
    version: `PKG-${version}`,
    project_id: input.projectId,
    topic_id: input.topicId,
    based_on_structure_ref: input.basedOnStructureRef,
    blueprint_ref: input.blueprintRef,
    blueprint_lock_state: input.blueprintLockState,
    dna_refs: dnaRefs,
    script_refs: {
      human_canonical: scriptVersion,
      machine_structured: projection?.machine?.canonical_script_version_ref ?? "",
      machine_schema: projection?.machine?.schema ?? "",
      output_hash: machineHash,
    },
    view_refs: viewRefs,
    continuity: {
      starting_state: continuity?.starting_state ?? "",
      ending_state: continuity?.ending_state ?? "",
      open_loops: continuity?.unresolved_refs ?? "",
      payoff_refs: continuity?.payoff_refs ?? "",
    },
    requirements: {
      asset_manifest: (projection?.views?.views ?? []).flatMap((row) => row.items.map((item) => item.ref)).filter(Boolean),
      anchors: viewRefs,
    },
    policy: { naming_authority: input.namingAuthority, rights: "", quality: "" },
    readiness: {
      ASSET: edgesReady ? "CONSUMER_READY" : "BLOCKED",
      VIDEO: edgesReady ? "CONSUMER_READY" : "BLOCKED",
      EDIT: edgesReady ? "CONSUMER_READY" : "BLOCKED",
      QA: edgesReady && Boolean(scriptVersion) && Boolean(machineHash) ? "CONSUMER_READY" : "BLOCKED",
      missing_blockers: missingBlockers,
    },
    audit: { candidate_ref: input.candidateRef, human_decision: input.humanDecision, lock_state: input.lockState },
    sections,
    status: missingBlockers.length ? "BLOCKED" : "BUILDING",
    at: input.at,
  };
}

export function serializeProductionPackage(doc: ProductionPackage): string {
  return JSON.stringify(doc);
}

export function parseProductionPackage(raw: string | null | undefined): ProductionPackage | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as ProductionPackage;
    if (parsed && parsed.kind === "PRODUCTION_PACKAGE" && typeof parsed.version === "string") return parsed;
  } catch {
    return null;
  }
  return null;
}

export function formatPackageDigest(doc: ProductionPackage): string {
  const resolved = doc.sections.filter((row) => row.status === "RESOLVED").length;
  const edges = ["ASSET", "VIDEO", "EDIT", "QA"].map((edge) => `${edge}:${doc.readiness[edge as "ASSET" | "VIDEO" | "EDIT" | "QA"] === "CONSUMER_READY" ? "R" : "B"}`).join(",");
  return `${doc.version} ${doc.status} sections=${resolved}/${doc.sections.length} edges=${edges}`;
}
