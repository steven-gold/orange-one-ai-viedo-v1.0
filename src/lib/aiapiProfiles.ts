export const AIAPI_REGISTRY_UID = "AIAPI-01-PROFILE-REGISTRY";

export const AIAPI_LEGACY_PROFILE_ID = "AIAPI-01-CRED-ACTIVE";

export const AIAPI_LEGACY_CAPABILITY = "chat";

export interface AiapiProfile {
  profileId: string;
  provider: string;
  model: string;
  capability: string;
  adapter: string;
  baseUrl: string;
  endpoint: string;
  timeout: string;
  enabled: boolean;
  credentialSet: boolean;
  lastTest: string;
  seq: number;
}

export type FieldReader = (uid: string) => string | null;

function clean(value: unknown): string {
  return typeof value === "string" ? value.trim().slice(0, 240) : "";
}

function num(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

export function profileIdentity(profile: Pick<AiapiProfile, "provider" | "model">): string {
  return [profile.provider, profile.model].map((part) => clean(part)).filter(Boolean).join(" / ");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalize(value: unknown): AiapiProfile | null {
  if (!isRecord(value)) return null;
  const profileId = clean(value.profileId);
  const provider = clean(value.provider);
  if (!profileId || !provider) return null;
  return {
    profileId,
    provider,
    model: clean(value.model),
    capability: clean(value.capability),
    adapter: clean(value.adapter),
    baseUrl: clean(value.baseUrl),
    endpoint: clean(value.endpoint),
    timeout: clean(value.timeout),
    enabled: value.enabled !== false,
    credentialSet: value.credentialSet === true,
    lastTest: clean(value.lastTest),
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
    profiles.map((profile) => ({
      profileId: profile.profileId,
      provider: profile.provider,
      model: profile.model,
      capability: profile.capability,
      adapter: profile.adapter,
      baseUrl: profile.baseUrl,
      endpoint: profile.endpoint,
      timeout: profile.timeout,
      enabled: profile.enabled,
      credentialSet: profile.credentialSet,
      lastTest: profile.lastTest,
      seq: profile.seq,
    })),
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

  let provider = providerColumn;
  let model = "";
  const separator = identity.includes(" / ") ? " / " : identity.includes("/") ? "/" : "";
  if (separator) {
    const parts = identity.split(separator).map((part) => clean(part)).filter(Boolean);
    provider = provider || parts[0] || "";
    model = parts[parts.length - 1] ?? "";
    if (parts.length === 1) model = "";
  }

  const status = clean(read("AIAPI-01-PROFILE-GRP-STATUS"));
  return {
    profileId: AIAPI_LEGACY_PROFILE_ID,
    provider: provider || identity,
    model,
    capability: clean(read("AIAPI-01-PROFILE-GRP-CAPABILITY")) || AIAPI_LEGACY_CAPABILITY,
    adapter: clean(read("AIAPI-01-PROFILE-GRP-ADAPTER")),
    baseUrl: clean(read("AIAPI-01-PROFILE-GRP-CONNECTION")),
    endpoint: clean(read("AIAPI-01-PROFILE-GRP-DATA-CONTEXT")),
    timeout: clean(read("AIAPI-01-PRO-DESC-LIMITS")),
    enabled: status !== "RETIRED" && status !== "DISABLED",
    credentialSet: clean(read("AIAPI-01-FLD-OPS-CREDENTIAL")) === "SET",
    lastTest: clean(read("AIAPI-01-PRO-DESC-LAST-TEST")),
    seq: 1,
  };
}

export function readProfiles(read: FieldReader): AiapiProfile[] {
  const stored = parseProfiles(read(AIAPI_REGISTRY_UID));
  if (stored.length) return stored;
  const legacy = synthesizeLegacyProfile(read);
  return legacy ? [legacy] : [];
}

export function eligibleProfiles(profiles: AiapiProfile[], capability: string): AiapiProfile[] {
  const wanted = clean(capability);
  return profiles
    .filter((profile) => profile.enabled && profile.capability === wanted)
    .sort((left, right) => left.seq - right.seq);
}
