export const AIAPI_REGISTRY_UID = "AIAPI-01-PROFILE-REGISTRY";

export const AIAPI_LEGACY_PROFILE_ID = "AIAPI-01-CRED-ACTIVE";

export const AIAPI_PROMPT_TEMPLATE_TOKEN = "{{canonical_instruction}}";

export const AIAPI_CAPABILITIES = ["chat", "correction"] as const;

export type AiapiCapability = (typeof AIAPI_CAPABILITIES)[number];

export function isAiapiCapability(value: string): value is AiapiCapability {
  return AIAPI_CAPABILITIES.includes(value as AiapiCapability);
}

/**
 * Provider Model Profile field contract (AIAPI-01 section 13).
 * Groups: Identity / Connection / Adapter / Capability / Data-Context / Status.
 */
export interface AiapiProfile {
  profileId: string;
  version: number;

  providerId: string;
  providerName: string;
  modelId: string;
  modelName: string;

  baseUrl: string;
  endpointPath: string;
  httpMethod: string;
  timeoutSeconds: string;

  adapterType: string;
  requestTemplate: string;
  responseTextPath: string;
  promptTemplate: string;

  capabilityType: string;
  additionalCapabilities: string;
  supportsReferences: string;
  rightsCompatible: string;

  dataClassifications: string;
  preferredLanguage: string;
  maxContext: string;

  enabled: boolean;
  credentialSet: boolean;
  lastTest: string;
  lastTestAt: string;
  seq: number;
}

export interface AiapiProfileField {
  group: string;
  name: keyof AiapiProfile;
  required?: boolean;
}

export const AIAPI_PROFILE_FIELD_GROUPS: ReadonlyArray<{
  group: string;
  labelKey:
    | "aiapi.grp-identity"
    | "aiapi.grp-connection"
    | "aiapi.grp-adapter"
    | "aiapi.grp-capability"
    | "aiapi.grp-data"
    | "aiapi.grp-status";
  fields: ReadonlyArray<keyof AiapiProfile>;
}> = [
  {
    group: "Identity",
    labelKey: "aiapi.grp-identity",
    fields: ["providerId", "providerName", "modelId", "modelName"],
  },
  {
    group: "Connection",
    labelKey: "aiapi.grp-connection",
    fields: ["baseUrl", "endpointPath", "httpMethod", "timeoutSeconds"],
  },
  {
    group: "Adapter",
    labelKey: "aiapi.grp-adapter",
    fields: ["adapterType", "requestTemplate", "responseTextPath", "promptTemplate"],
  },
  {
    group: "Capability",
    labelKey: "aiapi.grp-capability",
    fields: ["capabilityType", "additionalCapabilities", "supportsReferences", "rightsCompatible"],
  },
  {
    group: "Data / Context",
    labelKey: "aiapi.grp-data",
    fields: ["dataClassifications", "preferredLanguage", "maxContext"],
  },
  {
    group: "Status",
    labelKey: "aiapi.grp-status",
    fields: ["enabled"],
  },
];

const TEXT_FIELDS = [
  "providerId",
  "providerName",
  "modelId",
  "modelName",
  "baseUrl",
  "endpointPath",
  "httpMethod",
  "timeoutSeconds",
  "adapterType",
  "requestTemplate",
  "responseTextPath",
  "promptTemplate",
  "capabilityType",
  "additionalCapabilities",
  "supportsReferences",
  "rightsCompatible",
  "dataClassifications",
  "preferredLanguage",
  "maxContext",
  "lastTest",
  "lastTestAt",
] as const satisfies readonly (keyof AiapiProfile)[];

export type FieldReader = (uid: string) => string | null;

function clean(value: unknown): string {
  return typeof value === "string" ? value.trim().slice(0, 400) : "";
}

function num(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

export function profileIdentity(profile: Pick<AiapiProfile, "providerId" | "providerName" | "modelId" | "modelName">): string {
  const provider = clean(profile.providerName) || clean(profile.providerId);
  const model = clean(profile.modelName) || clean(profile.modelId);
  return [provider, model].filter(Boolean).join(" / ");
}

export function profileCapabilities(profile: Pick<AiapiProfile, "capabilityType" | "additionalCapabilities">): string[] {
  return [
    clean(profile.capabilityType),
    ...clean(profile.additionalCapabilities)
      .split(",")
      .map((part) => clean(part)),
  ].filter(Boolean);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function readText(value: Record<string, unknown>, key: string): string {
  return clean(value[key]);
}

/**
 * Normalizes stored registry rows. Legacy rows (provider / model / capability /
 * adapter / endpoint / timeout) are migrated on read; the previously invented
 * description fields are intentionally dropped so they stop travelling through
 * the registry.
 */
function normalize(value: unknown): AiapiProfile | null {
  if (!isRecord(value)) return null;
  const profileId = clean(value.profileId);
  const providerId = clean(value.providerId) || clean(value.provider);
  if (!profileId || !providerId) return null;
  const text = (key: string, legacy?: string): string =>
    readText(value, key) || (legacy ? readText(value, legacy) : "");

  return {
    profileId,
    version: num(value.version) || 1,
    providerId,
    providerName: readText(value, "providerName"),
    modelId: text("modelId", "model"),
    modelName: readText(value, "modelName"),
    baseUrl: readText(value, "baseUrl"),
    endpointPath: text("endpointPath", "endpoint"),
    httpMethod: readText(value, "httpMethod"),
    timeoutSeconds: text("timeoutSeconds", "timeout"),
    adapterType: text("adapterType", "adapter"),
    requestTemplate: readText(value, "requestTemplate"),
    responseTextPath: readText(value, "responseTextPath"),
    promptTemplate: readText(value, "promptTemplate"),
    capabilityType: text("capabilityType", "capability"),
    additionalCapabilities: readText(value, "additionalCapabilities"),
    supportsReferences: readText(value, "supportsReferences"),
    rightsCompatible: readText(value, "rightsCompatible"),
    dataClassifications: readText(value, "dataClassifications"),
    preferredLanguage: readText(value, "preferredLanguage"),
    maxContext: readText(value, "maxContext"),
    enabled: value.enabled !== false,
    credentialSet: value.credentialSet === true,
    lastTest: readText(value, "lastTest"),
    lastTestAt: readText(value, "lastTestAt"),
    seq: num(value.seq),
  };
}

export function parseProfiles(raw: string | null | undefined): AiapiProfile[] {
  const text = (raw ?? "").trim();
  if (!text) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  return parsed
    .map(normalize)
    .filter((profile): profile is AiapiProfile => profile !== null)
    .sort((left, right) => left.seq - right.seq);
}

export function serializeProfiles(profiles: AiapiProfile[]): string {
  return JSON.stringify(
    profiles.map((profile) => {
      const row: Record<string, unknown> = { profileId: profile.profileId, version: profile.version };
      for (const field of TEXT_FIELDS) row[field] = profile[field];
      row.enabled = profile.enabled;
      row.credentialSet = profile.credentialSet;
      row.seq = profile.seq;
      return row;
    }),
  );
}

export function nextSeq(profiles: AiapiProfile[]): number {
  return profiles.reduce((max, profile) => Math.max(max, profile.seq), 0) + 1;
}

export function nextProfileId(profiles: AiapiProfile[]): string {
  let max = 0;
  for (const profile of profiles) {
    const match = /^AIAPI-01-PROFILE-(\d+)$/.exec(profile.profileId);
    if (match) max = Math.max(max, Number.parseInt(match[1], 10));
  }
  return `AIAPI-01-PROFILE-${max + 1}`;
}

export function synthesizeLegacyProfile(read: FieldReader): AiapiProfile | null {
  const identity = clean(read("AIAPI-01-PROFILE-GRP-IDENTITY"));
  const providerColumn = clean(read("AIAPI-01-FLD-OV-PROVIDER"));
  if (!identity && !providerColumn) return null;

  let providerId = providerColumn;
  let modelId = "";
  const separator = identity.includes(" / ") ? " / " : identity.includes("/") ? "/" : "";
  if (separator) {
    const parts = identity.split(separator).map((part) => clean(part)).filter(Boolean);
    providerId = providerId || parts[0] || "";
    modelId = parts[parts.length - 1] ?? "";
    if (parts.length === 1) modelId = "";
  }

  const status = clean(read("AIAPI-01-PROFILE-GRP-STATUS"));
  return {
    profileId: AIAPI_LEGACY_PROFILE_ID,
    version: 1,
    providerId: providerId || identity,
    providerName: "",
    modelId,
    modelName: "",
    baseUrl: clean(read("AIAPI-01-PROFILE-GRP-CONNECTION")),
    endpointPath: clean(read("AIAPI-01-PROFILE-GRP-DATA-CONTEXT")),
    httpMethod: "",
    timeoutSeconds: clean(read("AIAPI-01-PRO-DESC-LIMITS")),
    adapterType: clean(read("AIAPI-01-PROFILE-GRP-ADAPTER")),
    requestTemplate: "",
    responseTextPath: "",
    promptTemplate: AIAPI_PROMPT_TEMPLATE_TOKEN,
    capabilityType: clean(read("AIAPI-01-PROFILE-GRP-CAPABILITY")),
    additionalCapabilities: "",
    supportsReferences: "",
    rightsCompatible: "",
    dataClassifications: "",
    preferredLanguage: "",
    maxContext: "",
    enabled: status !== "RETIRED" && status !== "DISABLED",
    credentialSet: clean(read("AIAPI-01-FLD-OPS-CREDENTIAL")) === "SET",
    lastTest: clean(read("AIAPI-01-PRO-DESC-LAST-TEST")),
    lastTestAt: "",
    seq: 1,
  };
}

export function readProfiles(read: FieldReader): AiapiProfile[] {
  const stored = parseProfiles(read(AIAPI_REGISTRY_UID));
  if (stored.length) return stored;
  const legacy = synthesizeLegacyProfile(read);
  return legacy ? [legacy] : [];
}

export function profileFingerprint(
  profile: Pick<AiapiProfile, "providerId" | "modelId" | "capabilityType" | "baseUrl" | "endpointPath">,
): string {
  return [profile.providerId, profile.modelId, profile.capabilityType, profile.baseUrl, profile.endpointPath]
    .map((part) => clean(part).toLowerCase())
    .join("\u0001");
}

export function findDuplicateProfile(
  profiles: AiapiProfile[],
  candidate: Pick<AiapiProfile, "providerId" | "modelId" | "capabilityType" | "baseUrl" | "endpointPath">,
  excludeProfileId?: string,
): AiapiProfile | null {
  const wanted = profileFingerprint(candidate);
  return (
    profiles.find(
      (profile) => profile.profileId !== excludeProfileId && profileFingerprint(profile) === wanted,
    ) ?? null
  );
}

export function supportsCapability(profile: AiapiProfile, capability: string): boolean {
  const wanted = clean(capability);
  return Boolean(wanted) && profileCapabilities(profile).includes(wanted);
}

export function eligibleProfiles(profiles: AiapiProfile[], capability: string): AiapiProfile[] {
  return profiles
    .filter((profile) => profile.enabled && supportsCapability(profile, capability))
    .sort((left, right) => left.seq - right.seq);
}
