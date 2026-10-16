import {
  AIAPI_REGISTRY_UID,
  type AiapiProfile,
  nextProfileId,
  nextSeq,
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
  provider?: string;
  model?: string;
  capability?: string;
  adapter?: string;
  baseUrl?: string;
  endpoint?: string;
  timeout?: string;
  enabled?: string;
  group?: string;
  members?: string;
  reason?: string;
  reference?: string;
  rights?: string;
  data?: string;
  budget?: string;
}

function parsePayload(raw: string | undefined): AiapiPayload {
  const text = (raw ?? "").trim();
  if (!text) return {};
  if (text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (parsed && typeof parsed === "object") return parsed as AiapiPayload;
    } catch {
      return { provider: text };
    }
  }
  return { provider: text };
}

function usable(value: string | null | undefined): string {
  return (value ?? "").trim().slice(0, 120);
}

const SECRET_PATTERN = /^(gsk_|sk-|sk_|xai-|AIza|glpat-|hf_|Bearer\s)/i;

function safeName(value: string | undefined): string {
  const name = usable(value);
  return SECRET_PATTERN.test(name) ? "" : name;
}

function join(parts: Array<string | undefined>): string {
  return parts.map((part) => usable(part)).filter(Boolean).join(" / ");
}

function profileExists(current: (uid: string) => string | null): boolean {
  const status = current("AIAPI-01-PROFILE-GRP-STATUS");
  if (!usable(current("AIAPI-01-PROFILE-GRP-IDENTITY"))) return false;
  return status !== "RETIRED";
}

function credentialSet(current: (uid: string) => string | null): boolean {
  return current("AIAPI-01-FLD-OPS-CREDENTIAL") === "SET";
}

function capabilityApproved(current: (uid: string) => string | null): boolean {
  return current("AIAPI-01-FLD-PF-RIGHTS") === "APPROVED";
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

function mirrorProfile(profile: AiapiProfile): Record<string, string> {
  return {
    "AIAPI-01-FLD-OV-PROVIDER": profile.provider,
    "AIAPI-01-FLD-OV-CAPABILITY": profile.capability,
    "AIAPI-01-PROFILE-GRP-IDENTITY": profileIdentity(profile),
    "AIAPI-01-PROFILE-GRP-CONNECTION": profile.baseUrl,
    "AIAPI-01-PROFILE-GRP-ADAPTER": profile.adapter,
    "AIAPI-01-PROFILE-GRP-CAPABILITY": profile.capability,
    "AIAPI-01-PROFILE-GRP-DATA-CONTEXT": profile.endpoint,
    "AIAPI-01-PROFILE-GRP-STATUS": profile.enabled ? "ENABLED" : "DISABLED",
    "AIAPI-01-FLD-OPS-CREDENTIAL": profile.credentialSet ? "SET" : "NOT_SET",
    "AIAPI-01-PRO-DESC-IDENTITY": profileIdentity(profile),
    "AIAPI-01-PRO-DESC-CAPABILITIES": profile.capability,
    "AIAPI-01-PRO-DESC-ENDPOINT": join([profile.baseUrl, profile.endpoint]),
    "AIAPI-01-PRO-DESC-AUTH": profile.credentialSet ? "SET" : "NOT_SET",
    "AIAPI-01-PRO-DESC-LIMITS": profile.timeout,
    "AIAPI-01-PRO-DESC-LAST-TEST": profile.lastTest,
    "AIAPI-01-PRO-DESC-HEALTH": profile.lastTest === "PASS" ? "HEALTHY" : "UNKNOWN",
  };
}

export function previewAiapiAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const payload = parsePayload(nextValue);

  if (actionUid === "createProviderModelProfile") {
    const provider = safeName(payload.provider);
    if (!provider) return {};
    const profiles = readProfiles(current);
    const profile: AiapiProfile = {
      profileId: nextProfileId(profiles),
      provider,
      model: usable(payload.model),
      capability: usable(payload.capability),
      adapter: usable(payload.adapter),
      baseUrl: usable(payload.baseUrl),
      endpoint: usable(payload.endpoint),
      timeout: usable(payload.timeout),
      enabled: (usable(payload.enabled) || "ENABLED") !== "DISABLED",
      credentialSet: false,
      lastTest: "",
      seq: nextSeq(profiles),
    };
    return {
      [AIAPI_REGISTRY_UID]: serializeProfiles([...profiles, profile]),
      "AIAPI-01-FLD-OV-ROUTE": "",
      "AIAPI-01-FLD-OPS-HEALTH": "UNKNOWN",
      ...mirrorProfile(profile),
    };
  }

  if (actionUid === "updateProviderModelProfile") {
    const profiles = readProfiles(current);
    const target = targetProfile(profiles, payload, current);
    if (!target) return {};
    const updated: AiapiProfile = {
      ...target,
      provider: safeName(payload.provider) || target.provider,
      model: usable(payload.model) || target.model,
      capability: usable(payload.capability) || target.capability,
      adapter: usable(payload.adapter) || target.adapter,
      baseUrl: usable(payload.baseUrl) || target.baseUrl,
      endpoint: usable(payload.endpoint) || target.endpoint,
      timeout: usable(payload.timeout) || target.timeout,
    };
    return { [AIAPI_REGISTRY_UID]: serializeProfiles(replaceProfile(profiles, updated)), ...mirrorProfile(updated) };
  }

  if (actionUid === "testProviderModelProfile") {
    const profiles = readProfiles(current);
    const target = targetProfile(profiles, payload, current);
    if (!target) return {};
    if (!target.credentialSet) return {};
    if (!usable(target.adapter)) return {};
    const updated: AiapiProfile = { ...target, lastTest: "PASS" };
    return {
      [AIAPI_REGISTRY_UID]: serializeProfiles(replaceProfile(profiles, updated)),
      "AIAPI-01-PRO-DESC-LAST-TEST": "PASS",
      "AIAPI-01-PRO-DESC-HEALTH": "HEALTHY",
      "AIAPI-01-FLD-OPS-HEALTH": "HEALTHY",
    };
  }

  if (actionUid === "retireProviderModelProfile") {
    const profiles = readProfiles(current);
    const target = targetProfile(profiles, payload, current);
    if (!target) return {};
    const updated: AiapiProfile = { ...target, enabled: false };
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
    const updated: AiapiProfile = { ...target, credentialSet: true };
    return { [AIAPI_REGISTRY_UID]: serializeProfiles(replaceProfile(profiles, updated)), ...mirrorProfile(updated) };
  }

  if (actionUid === "deleteProviderModelCredential") {
    const profiles = readProfiles(current);
    const target = targetProfile(profiles, payload, current);
    if (!target || !target.credentialSet) return {};
    const updated: AiapiProfile = { ...target, credentialSet: false, lastTest: "" };
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

  if (actionUid === "admin:AIAPI-08:ACT-SYSTEM-TEST") {
    if (!profileExists(current)) return {};
    return {
      "AIAPI-01-FLD-SANDBOX-EVIDENCE": "SANDBOX_PASS",
      "AIAPI-01-FLD-JOB-STATUS": "completed",
    };
  }

  if (actionUid === "executeProviderRoute") {
    if (!profileExists(current)) return {};
    if (!credentialSet(current)) return {};
    if (!capabilityApproved(current)) return {};
    return {
      "AIAPI-01-FLD-ROUTE-DECISION": "ROUTE_READY",
      "AIAPI-01-FLD-OV-ROUTE": "ROUTE_READY",
      "AIAPI-01-FLD-JOB-ID": `ROUTE-${Date.now().toString(36).toUpperCase()}`,
      "AIAPI-01-FLD-JOB-STATUS": "running",
      "AIAPI-01-FLD-ATTEMPT-ID": "ATT-1",
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

  if (actionUid === "runProviderQueueProbe") {
    return {
      "AIAPI-01-FLD-OPS-QUEUE": "PROBED",
      "AIAPI-01-FLD-OPS-COST": current("AIAPI-01-FLD-OPS-COST") ?? "",
    };
  }

  if (actionUid === "setKillSwitch") {
    const currentState = current("AIAPI-01-FLD-KILL-SWITCH");
    const next = currentState === "ON" ? "OFF" : "ON";
    return { "AIAPI-01-FLD-KILL-SWITCH": next };
  }

  if (actionUid.startsWith("AIAPI-01-ACT-VIEW-") || actionUid === "searchProjection") {
    return {};
  }

  return {};
}
