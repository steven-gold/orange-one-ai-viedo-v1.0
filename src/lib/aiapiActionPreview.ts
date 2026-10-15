export const AIAPI_EXTRA_PROJECTION_KEYS = [
  "AIAPI-01-FLD-CANDIDATE-GROUP",
  "AIAPI-01-FLD-SANDBOX-EVIDENCE",
  "AIAPI-01-FLD-ROUTE-DECISION",
  "AIAPI-01-FLD-KILL-SWITCH",
  "AIAPI-01-FLD-GOVERNED-RESOURCE",
] as const;

interface AiapiPayload {
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

function join(parts: Array<string | undefined>): string {
  return parts.map((part) => usable(part)).filter(Boolean).join(" / ");
}

function profileIdentity(current: (uid: string) => string | null): string {
  return usable(current("AIAPI-01-PROFILE-GRP-IDENTITY"));
}

function profileExists(current: (uid: string) => string | null): boolean {
  const status = current("AIAPI-01-PROFILE-GRP-STATUS");
  if (!profileIdentity(current)) return false;
  return status !== "RETIRED";
}

function credentialSet(current: (uid: string) => string | null): boolean {
  return current("AIAPI-01-FLD-OPS-CREDENTIAL") === "SET";
}

function capabilityApproved(current: (uid: string) => string | null): boolean {
  return current("AIAPI-01-FLD-PF-RIGHTS") === "APPROVED";
}

export function previewAiapiAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const payload = parsePayload(nextValue);

  if (actionUid === "createProviderModelProfile") {
    const provider = usable(payload.provider);
    if (!provider) return {};
    const model = usable(payload.model);
    const identity = join([provider, model]);
    return {
      "AIAPI-01-FLD-OV-PROVIDER": provider,
      "AIAPI-01-FLD-OV-CAPABILITY": usable(payload.capability),
      "AIAPI-01-FLD-OV-ROUTE": "",
      "AIAPI-01-PROFILE-GRP-IDENTITY": identity,
      "AIAPI-01-PROFILE-GRP-CONNECTION": usable(payload.baseUrl),
      "AIAPI-01-PROFILE-GRP-ADAPTER": usable(payload.adapter),
      "AIAPI-01-PROFILE-GRP-CAPABILITY": usable(payload.capability),
      "AIAPI-01-PROFILE-GRP-DATA-CONTEXT": usable(payload.endpoint),
      "AIAPI-01-PROFILE-GRP-STATUS": usable(payload.enabled) || "ENABLED",
      "AIAPI-01-FLD-OPS-CREDENTIAL": "NOT_SET",
      "AIAPI-01-FLD-OPS-HEALTH": "UNKNOWN",
      "AIAPI-01-PRO-DESC-IDENTITY": identity,
      "AIAPI-01-PRO-DESC-CAPABILITIES": usable(payload.capability),
      "AIAPI-01-PRO-DESC-ENDPOINT": join([usable(payload.baseUrl), usable(payload.endpoint)]),
      "AIAPI-01-PRO-DESC-AUTH": "NOT_SET",
      "AIAPI-01-PRO-DESC-LIMITS": usable(payload.timeout),
      "AIAPI-01-PRO-DESC-LAST-TEST": "",
      "AIAPI-01-PRO-DESC-HEALTH": "UNKNOWN",
    };
  }

  if (actionUid === "updateProviderModelProfile") {
    if (!profileExists(current)) return {};
    const patch: Record<string, string> = {};
    const identity = join([usable(payload.provider), usable(payload.model)]);
    if (identity) {
      patch["AIAPI-01-PROFILE-GRP-IDENTITY"] = identity;
      patch["AIAPI-01-PRO-DESC-IDENTITY"] = identity;
      patch["AIAPI-01-FLD-OV-PROVIDER"] = usable(payload.provider) || identity;
    }
    if (usable(payload.baseUrl)) patch["AIAPI-01-PROFILE-GRP-CONNECTION"] = usable(payload.baseUrl);
    if (usable(payload.adapter)) patch["AIAPI-01-PROFILE-GRP-ADAPTER"] = usable(payload.adapter);
    if (usable(payload.capability)) {
      patch["AIAPI-01-PROFILE-GRP-CAPABILITY"] = usable(payload.capability);
      patch["AIAPI-01-PRO-DESC-CAPABILITIES"] = usable(payload.capability);
      patch["AIAPI-01-FLD-OV-CAPABILITY"] = usable(payload.capability);
    }
    if (usable(payload.endpoint)) {
      patch["AIAPI-01-PROFILE-GRP-DATA-CONTEXT"] = usable(payload.endpoint);
      patch["AIAPI-01-PRO-DESC-ENDPOINT"] = join([usable(payload.baseUrl), usable(payload.endpoint)]);
    }
    if (usable(payload.timeout)) patch["AIAPI-01-PRO-DESC-LIMITS"] = usable(payload.timeout);
    return patch;
  }

  if (actionUid === "testProviderModelProfile") {
    if (!profileExists(current)) return {};
    if (!credentialSet(current)) return {};
    if (!usable(current("AIAPI-01-PROFILE-GRP-ADAPTER"))) return {};
    return {
      "AIAPI-01-PRO-DESC-LAST-TEST": "PASS",
      "AIAPI-01-PRO-DESC-HEALTH": "HEALTHY",
      "AIAPI-01-FLD-OPS-HEALTH": "HEALTHY",
    };
  }

  if (actionUid === "retireProviderModelProfile") {
    if (!profileExists(current)) return {};
    return {
      "AIAPI-01-PROFILE-GRP-STATUS": "RETIRED",
      "AIAPI-01-FLD-OPS-HEALTH": "UNKNOWN",
      "AIAPI-01-PRO-DESC-HEALTH": "UNKNOWN",
      "AIAPI-01-FLD-OPS-CREDENTIAL": "NOT_SET",
    };
  }

  if (actionUid === "setProviderModelCredential") {
    if (!profileExists(current)) return {};
    return {
      "AIAPI-01-FLD-OPS-CREDENTIAL": "SET",
      "AIAPI-01-PRO-DESC-AUTH": "SET",
    };
  }

  if (actionUid === "deleteProviderModelCredential") {
    if (!credentialSet(current)) return {};
    return {
      "AIAPI-01-FLD-OPS-CREDENTIAL": "NOT_SET",
      "AIAPI-01-PRO-DESC-AUTH": "NOT_SET",
      "AIAPI-01-PRO-DESC-HEALTH": "UNKNOWN",
      "AIAPI-01-FLD-OPS-HEALTH": "UNKNOWN",
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
