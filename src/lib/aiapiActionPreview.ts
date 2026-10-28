import {
  AIAPI_PROMPT_TEMPLATE_TOKEN,
  AIAPI_REGISTRY_UID,
  type AiapiProfile,
  findDuplicateProfile,
  isAiapiCapability,
  isCapabilityToken,
  profileIdentity,
  readProfiles,
  serializeProfiles,
} from "./aiapiProfiles";

export const AIAPI_EXTRA_PROJECTION_KEYS = [
  AIAPI_REGISTRY_UID,
  "AIAPI-01-FLD-CANDIDATE-GROUP",
  "AIAPI-01-FLD-SANDBOX-EVIDENCE",
  "AIAPI-01-FLD-ROUTE-DECISION",
  "AIAPI-01-FLD-KILL-SWITCH",
  "AIAPI-01-FLD-GOVERNED-RESOURCE",
] as const;

interface AiapiPayload {
  profileId?: string;
  expectedVersion?: string | number;
  providerId?: string;
  providerName?: string;
  modelId?: string;
  modelName?: string;
  baseUrl?: string;
  endpointPath?: string;
  httpMethod?: string;
  timeoutSeconds?: string;
  adapterType?: string;
  requestTemplate?: string;
  responseTextPath?: string;
  promptTemplate?: string;
  capabilityType?: string;
  additionalCapabilities?: string;
  supportsReferences?: string;
  rightsCompatible?: string;
  dataClassifications?: string;
  preferredLanguage?: string;
  maxContext?: string;
  enabled?: string;
  secret?: string;
  credential?: string;
  reference?: string;
  group?: string;
  members?: string;
  reason?: string;
  rights?: string;
  capability?: string;
  data?: string;
  budget?: string;
  instruction?: string;
}

function parsePayload(raw: string | undefined): AiapiPayload {
  const text = (raw ?? "").trim();
  if (!text) return {};
  if (text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (parsed && typeof parsed === "object") return parsed as AiapiPayload;
    } catch {
      return {};
    }
  }
  return { secret: text };
}

function usable(value: string | null | undefined): string {
  return (value ?? "").trim().slice(0, 400);
}

const SECRET_PATTERN = /^(gsk_|sk-|sk_|xai-|AIza|glpat-|hf_|Bearer\s)/i;

function safeName(value: string | undefined): string {
  const name = usable(value);
  return SECRET_PATTERN.test(name) ? "" : name;
}

function join(parts: Array<string | undefined>): string {
  return parts.map((part) => usable(part)).filter(Boolean).join(" / ");
}

function targetProfile(
  profiles: AiapiProfile[],
  payload: AiapiPayload,
  current: (uid: string) => string | null,
): AiapiProfile | undefined {
  const wantedId = usable(payload.profileId);
  if (wantedId) return profiles.find((profile) => profile.profileId === wantedId);
  if (profiles.length === 1) return profiles[0];
  const identity = usable(current("AIAPI-01-PROFILE-GRP-IDENTITY"));
  return profiles.find((profile) => profileIdentity(profile) === identity);
}

function replaceProfile(profiles: AiapiProfile[], updated: AiapiProfile): AiapiProfile[] {
  return profiles.map((profile) => (profile.profileId === updated.profileId ? updated : profile));
}

export function mirrorProfile(profile: AiapiProfile): Record<string, string> {
  return {
    "AIAPI-01-FLD-OV-PROVIDER": profile.providerName || profile.providerId,
    "AIAPI-01-FLD-OV-CAPABILITY": profile.capabilityType,
    "AIAPI-01-PROFILE-GRP-IDENTITY": profileIdentity(profile),
    "AIAPI-01-PROFILE-GRP-CONNECTION": profile.baseUrl,
    "AIAPI-01-PROFILE-GRP-ADAPTER": profile.adapterType,
    "AIAPI-01-PROFILE-GRP-CAPABILITY": profile.capabilityType,
    "AIAPI-01-PROFILE-GRP-DATA-CONTEXT": profile.endpointPath,
    "AIAPI-01-PROFILE-GRP-STATUS": profile.enabled ? "ENABLED" : "DISABLED",
    "AIAPI-01-FLD-OPS-CREDENTIAL": profile.credentialSet ? "SET" : "NOT_SET",
    "AIAPI-01-PRO-DESC-IDENTITY": profileIdentity(profile),
    "AIAPI-01-PRO-DESC-CAPABILITIES": join([profile.capabilityType, profile.additionalCapabilities]),
    "AIAPI-01-PRO-DESC-INPUT": profile.requestTemplate,
    "AIAPI-01-PRO-DESC-OUTPUT": profile.responseTextPath,
    "AIAPI-01-PRO-DESC-LIMITS": join([profile.timeoutSeconds, profile.maxContext]),
    "AIAPI-01-PRO-DESC-ENDPOINT": join([profile.baseUrl, profile.endpointPath, profile.httpMethod]),
    "AIAPI-01-PRO-DESC-AUTH": profile.credentialSet ? "SET" : "NOT_SET",
    "AIAPI-01-PRO-DESC-LAST-TEST": profile.lastTestDetail
      ? join([profile.lastTest, profile.lastTestDetail])
      : profile.lastTest,
    "AIAPI-01-PRO-DESC-HEALTH": profile.lastTest === "PASS" ? "HEALTHY" : "UNKNOWN",
  };
}

type ProfileText = Omit<
  AiapiProfile,
  "profileId" | "version" | "enabled" | "credentialSet" | "lastTest" | "lastTestAt" | "lastTestDetail" | "seq"
>;

function textFrom(payload: AiapiPayload, base: AiapiProfile | null): ProfileText {
  const pick = (key: keyof ProfileText): string =>
    usable(payload[key as keyof AiapiPayload] as string | undefined) || (base ? usable(base[key]) : "");
  const providerId = safeName(payload.providerId) || (base ? base.providerId : "");
  return {
    providerId,
    providerName: pick("providerName"),
    modelId: pick("modelId"),
    modelName: pick("modelName"),
    baseUrl: pick("baseUrl"),
    endpointPath: pick("endpointPath"),
    httpMethod: pick("httpMethod"),
    timeoutSeconds: pick("timeoutSeconds"),
    adapterType: pick("adapterType"),
    requestTemplate: pick("requestTemplate"),
    responseTextPath: pick("responseTextPath"),
    promptTemplate: pick("promptTemplate"),
    capabilityType: pick("capabilityType"),
    additionalCapabilities: pick("additionalCapabilities"),
    supportsReferences: pick("supportsReferences"),
    rightsCompatible: pick("rightsCompatible"),
    dataClassifications: pick("dataClassifications"),
    preferredLanguage: pick("preferredLanguage"),
    maxContext: pick("maxContext"),
  };
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\/[^\s]+$/i.test(value);
}

export type AiapiValidationResult = { ok: true } | { ok: false; code: string };

function validateFields(profile: Omit<AiapiProfile, "profileId" | "version" | "enabled" | "credentialSet" | "lastTest" | "lastTestAt" | "lastTestDetail" | "seq">): AiapiValidationResult {
  if (!profile.providerId) return { ok: false, code: "AIAPI_PROFILE_PROVIDER_REQUIRED" };
  if (!profile.modelId) return { ok: false, code: "AIAPI_PROFILE_MODEL_REQUIRED" };
  if (!isAiapiCapability(profile.capabilityType) && !isCapabilityToken(profile.capabilityType)) {
    return { ok: false, code: "AIAPI_PROFILE_CAPABILITY_INVALID" };
  }
  if (!profile.adapterType) return { ok: false, code: "AIAPI_PROFILE_ADAPTER_REQUIRED" };
  if (!isHttpUrl(profile.baseUrl)) return { ok: false, code: "AIAPI_PROFILE_BASE_URL_INVALID" };
  if (!profile.endpointPath) return { ok: false, code: "AIAPI_PROFILE_ENDPOINT_REQUIRED" };
  if (!profile.promptTemplate.includes(AIAPI_PROMPT_TEMPLATE_TOKEN)) {
    return { ok: false, code: "AIAPI_PROFILE_PROMPT_TEMPLATE_INVALID" };
  }
  return { ok: true };
}

export function validateAiapiAction(
  _controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): AiapiValidationResult {
  const payload = parsePayload(nextValue);
  const profiles = readProfiles(current);

  // createProviderModelProfile is authoritative in the server runtime: it derives
  // the provider/model/connection from the supplied key before validating.
  if (actionUid === "createProviderModelProfile") return { ok: true };

  if (actionUid === "updateProviderModelProfile") {
    const target = targetProfile(profiles, payload, current);
    if (!target) return { ok: false, code: "AIAPI_PROFILE_NOT_FOUND" };
    const expected = Number.parseInt(String(payload.expectedVersion ?? ""), 10);
    if (!Number.isFinite(expected) || expected !== target.version) {
      return { ok: false, code: "AIAPI_PROFILE_VERSION_CONFLICT" };
    }
    const fields = textFrom(payload, target);
    const invalid = validateFields(fields);
    if (!invalid.ok) return invalid;
    const candidate = { ...target, ...fields };
    if (findDuplicateProfile(profiles, candidate, target.profileId)) {
      return { ok: false, code: "AIAPI_PROFILE_DUPLICATE" };
    }
    return { ok: true };
  }

  if (actionUid === "configureGovernedResource") {
    if (!usable(payload.reference)) return { ok: false, code: "AIAPI_GOVERNED_REFERENCE_REQUIRED" };
    return { ok: true };
  }

  if (actionUid === "approveGovernedResource") {
    if (!usable(current("AIAPI-01-FLD-PF-REFERENCE"))) return { ok: false, code: "AIAPI_GOVERNED_REFERENCE_REQUIRED" };
    return { ok: true };
  }

  if (actionUid === "createProviderCandidateGroup") {
    if (!usable(payload.group)) return { ok: false, code: "AIAPI_CANDIDATE_GROUP_REQUIRED" };
    return { ok: true };
  }

  if (
    actionUid === "retireProviderModelProfile" ||
    actionUid === "restoreProviderFromQuarantine" ||
    actionUid === "setKillSwitch" ||
    actionUid === "deleteProviderModelCredential"
  ) {
    if (!usable(payload.reason)) return { ok: false, code: "AIAPI_REASON_REQUIRED" };
  }

  if (actionUid === "setProviderModelCredential") {
    const target = targetProfile(profiles, payload, current);
    if (!target) return { ok: false, code: "AIAPI_PROFILE_NOT_FOUND" };
    const secret = usable(payload.secret) || usable(payload.credential) || usable(payload.reference);
    if (!secret) return { ok: false, code: "AIAPI_CREDENTIAL_REQUIRED" };
    return { ok: true };
  }

  if (actionUid === "deleteProviderModelCredential") {
    const target = targetProfile(profiles, payload, current);
    if (!target) return { ok: false, code: "AIAPI_PROFILE_NOT_FOUND" };
    if (!target.credentialSet) return { ok: false, code: "AIAPI_CREDENTIAL_NOT_SET" };
    return { ok: true };
  }

  if (
    actionUid === "testProviderModelProfile" ||
    actionUid === "retireProviderModelProfile" ||
    actionUid === "admin:AIAPI-08:ACT-SYSTEM-TEST"
  ) {
    const target = targetProfile(profiles, payload, current);
    if (!target && profiles.length) return { ok: false, code: "AIAPI_PROFILE_NOT_FOUND" };
    if (!target) return { ok: false, code: "AIAPI_PROFILE_REQUIRED" };
    if (actionUid === "testProviderModelProfile") {
      if (!target.credentialSet) return { ok: false, code: "AIAPI_CREDENTIAL_REQUIRED" };
      if (!target.adapterType) return { ok: false, code: "AIAPI_PROFILE_ADAPTER_REQUIRED" };
    }
    return { ok: true };
  }

  return { ok: true };
}

export function previewAiapiAction(
  _controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const payload = parsePayload(nextValue);

  if (actionUid === "updateProviderModelProfile") {
    const profiles = readProfiles(current);
    const target = targetProfile(profiles, payload, current);
    if (!target) return {};
    const updated: AiapiProfile = {
      ...target,
      ...textFrom(payload, target),
      version: target.version + 1,
      enabled: usable(payload.enabled) ? usable(payload.enabled) !== "DISABLED" : target.enabled,
    };
    return { [AIAPI_REGISTRY_UID]: serializeProfiles(replaceProfile(profiles, updated)), ...mirrorProfile(updated) };
  }

  if (actionUid === "retireProviderModelProfile") {
    const profiles = readProfiles(current);
    const target = targetProfile(profiles, payload, current);
    if (!target) return {};
    const updated: AiapiProfile = {
      ...target,
      version: target.version + 1,
      enabled: false,
      lastTest: "",
      lastTestAt: "",
    };
    return {
      [AIAPI_REGISTRY_UID]: serializeProfiles(replaceProfile(profiles, updated)),
      "AIAPI-01-FLD-OPS-HEALTH": "UNKNOWN",
      ...mirrorProfile(updated),
    };
  }

  if (actionUid === "setProviderModelCredential") {
    const profiles = readProfiles(current);
    const target = targetProfile(profiles, payload, current);
    if (!target) return {};
    const updated: AiapiProfile = { ...target, credentialSet: true, lastTest: "", lastTestAt: "" };
    return { [AIAPI_REGISTRY_UID]: serializeProfiles(replaceProfile(profiles, updated)), ...mirrorProfile(updated) };
  }

  if (actionUid === "deleteProviderModelCredential") {
    const profiles = readProfiles(current);
    const target = targetProfile(profiles, payload, current);
    if (!target || !target.credentialSet) return {};
    const updated: AiapiProfile = { ...target, credentialSet: false, lastTest: "", lastTestAt: "" };
    return {
      [AIAPI_REGISTRY_UID]: serializeProfiles(replaceProfile(profiles, updated)),
      "AIAPI-01-PRO-DESC-HEALTH": "UNKNOWN",
      "AIAPI-01-FLD-OPS-HEALTH": "UNKNOWN",
      ...mirrorProfile(updated),
    };
  }

  if (actionUid === "configureGovernedResource") {
    const reference = usable(payload.reference);
    if (!reference) return {};
    const patch: Record<string, string> = {
      "AIAPI-01-FLD-PF-REFERENCE": reference,
      "AIAPI-01-FLD-PF-RIGHTS": "CONFIGURED",
      "AIAPI-01-FLD-GOVERNED-RESOURCE": reference,
    };
    if (usable(payload.capability)) patch["AIAPI-01-FLD-PF-CAPABILITY"] = usable(payload.capability);
    if (usable(payload.rights)) patch["AIAPI-01-FLD-PF-RIGHTS"] = "CONFIGURED";
    if (usable(payload.data)) patch["AIAPI-01-FLD-PF-DATA"] = usable(payload.data);
    if (usable(payload.budget)) patch["AIAPI-01-FLD-PF-BUDGET"] = usable(payload.budget);
    return patch;
  }

  if (actionUid === "approveGovernedResource") {
    if (!usable(current("AIAPI-01-FLD-PF-REFERENCE"))) return {};
    return { "AIAPI-01-FLD-PF-RIGHTS": "APPROVED" };
  }

  if (actionUid === "createProviderCandidateGroup") {
    const group = usable(payload.group);
    if (!group) return {};
    const members = usable(payload.members);
    return {
      "AIAPI-01-FLD-CANDIDATE-GROUP": members ? `${group} · ${members}` : group,
    };
  }

  if (actionUid === "getProviderRouteDecision") {
    const decision = current("AIAPI-01-FLD-ROUTE-DECISION");
    return decision ? { "AIAPI-01-FLD-ROUTE-DECISION": decision } : {};
  }

  if (actionUid === "getProviderQuarantine") {
    const existing = usable(current("AIAPI-01-FLD-OPS-QUARANTINE"));
    return existing ? { "AIAPI-01-FLD-OPS-QUARANTINE": existing } : {};
  }

  if (actionUid === "restoreProviderFromQuarantine") {
    if (!usable(payload.reason)) return {};
    if (!usable(current("AIAPI-01-FLD-OPS-QUARANTINE"))) return {};
    return { "AIAPI-01-FLD-OPS-QUARANTINE": "RESTORED" };
  }

  if (actionUid === "setKillSwitch") {
    if (!usable(payload.reason)) return {};
    const currentState = current("AIAPI-01-FLD-KILL-SWITCH");
    return { "AIAPI-01-FLD-KILL-SWITCH": currentState === "ON" ? "OFF" : "ON" };
  }

  // Connection test, sandbox, route execution and queue probe are runtime
  // operations; they write real evidence from the server runtime only.
  return {};
}
