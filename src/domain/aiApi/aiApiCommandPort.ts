export type AiApiClientOperation =
  | "createProviderModelProfile"
  | "updateProviderModelProfile"
  | "getProviderModelProfile"
  | "listProviderModelProfiles"
  | "testProviderModelProfile"
  | "retireProviderModelProfile"
  | "setProviderModelCredential"
  | "deleteProviderModelCredential"
  | "configureGovernedResource"
  | "approveGovernedResource"
  | "setKillSwitch"
  | "createProviderCandidateGroup"
  | "getProviderQuarantine"
  | "restoreProviderFromQuarantine"
  | "runSandboxTest"
  | "executeProviderRoute"
  | "getProviderRouteDecision"
  | "runProviderQueueProbe";

export type AiApiCommandRefs = {
  profileId?: string;
  quarantineId?: string;
  routeDecisionId?: string;
  resourceId?: string;
};

export type AiApiCommandResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; status: number; reason_code: string; correlation_id: string };

function newCorrelationId() {
  try { return crypto.randomUUID(); } catch { return `aiapi-${Date.now()}`; }
}

function required(value: string | undefined, reason: string) {
  const normalized = value?.trim();
  if (!normalized) throw new Error(reason);
  return encodeURIComponent(normalized);
}

function routeFor(operation: AiApiClientOperation, refs: AiApiCommandRefs): { method: string; path: string } {
  switch (operation) {
    case "createProviderModelProfile": return { method: "POST", path: "/v1/aiapi/provider-profiles" };
    case "listProviderModelProfiles": return { method: "GET", path: "/v1/aiapi/provider-profiles" };
    case "getProviderModelProfile": return { method: "GET", path: `/v1/aiapi/provider-profiles/${required(refs.profileId, "AIAPI_PROFILE_SELECTION_REQUIRED")}` };
    case "updateProviderModelProfile": return { method: "PATCH", path: `/v1/aiapi/provider-profiles/${required(refs.profileId, "AIAPI_PROFILE_SELECTION_REQUIRED")}` };
    case "testProviderModelProfile": return { method: "POST", path: `/v1/aiapi/provider-profiles/${required(refs.profileId, "AIAPI_PROFILE_SELECTION_REQUIRED")}/test` };
    case "retireProviderModelProfile": return { method: "POST", path: `/v1/aiapi/provider-profiles/${required(refs.profileId, "AIAPI_PROFILE_SELECTION_REQUIRED")}/retire` };
    case "setProviderModelCredential": return { method: "PUT", path: `/v1/aiapi/provider-profiles/${required(refs.profileId, "AIAPI_PROFILE_SELECTION_REQUIRED")}/credential` };
    case "deleteProviderModelCredential": return { method: "DELETE", path: `/v1/aiapi/provider-profiles/${required(refs.profileId, "AIAPI_PROFILE_SELECTION_REQUIRED")}/credential` };
    case "createProviderCandidateGroup": return { method: "POST", path: "/v1/aiapi/provider-groups" };
    case "getProviderQuarantine": return { method: "GET", path: "/v1/aiapi/quarantine" };
    case "restoreProviderFromQuarantine": return { method: "POST", path: `/v1/aiapi/quarantine/${required(refs.quarantineId, "AIAPI_QUARANTINE_SELECTION_REQUIRED")}/restore` };
    case "runSandboxTest": return { method: "POST", path: "/v1/aiapi/sandbox-tests" };
    case "executeProviderRoute": return { method: "POST", path: "/v1/aiapi/routes" };
    case "getProviderRouteDecision": return { method: "GET", path: `/v1/aiapi/routes/${required(refs.routeDecisionId, "AIAPI_ROUTE_DECISION_SELECTION_REQUIRED")}` };
    case "setKillSwitch": return { method: "POST", path: "/v1/aiapi/kill-switch" };
    case "runProviderQueueProbe": return { method: "POST", path: "/v1/aiapi/queue/probe" };
    case "configureGovernedResource": return { method: "PATCH", path: `/v1/governance/resources/${required(refs.resourceId, "AIAPI_GOVERNED_RESOURCE_REQUIRED")}` };
    case "approveGovernedResource": return { method: "POST", path: `/v1/governance/resources/${required(refs.resourceId, "AIAPI_GOVERNED_RESOURCE_REQUIRED")}/approve` };
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

export async function invokeAiApiCommand(
  operation: AiApiClientOperation,
  refs: AiApiCommandRefs = {},
  payload: unknown = {},
): Promise<AiApiCommandResult> {
  const correlation_id = newCorrelationId();
  let route: { method: string; path: string };
  try {
    route = routeFor(operation, refs);
  } catch (error) {
    return {
      ok: false,
      status: 400,
      reason_code: error instanceof Error && error.message ? error.message : "AIAPI_COMMAND_REFERENCE_REQUIRED",
      correlation_id,
    };
  }

  let response: Response;
  try {
    response = await fetch(route.path, {
      method: route.method,
      credentials: "include",
      cache: "no-store",
      headers: {
        "content-type": "application/json",
        "x-correlation-id": correlation_id,
      },
      body: route.method === "GET" || route.method === "DELETE" ? undefined : JSON.stringify(payload),
    });
  } catch {
    return { ok: false, status: 503, reason_code: "AIAPI_COMMAND_REQUEST_FAILED", correlation_id };
  }

  const raw: unknown = await response.json().catch(() => null);
  const record = asRecord(raw);
  const serverCorrelation =
    typeof record?.correlation_id === "string"
      ? record.correlation_id
      : response.headers.get("x-correlation-id") ?? correlation_id;

  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      reason_code: typeof record?.reason_code === "string" ? record.reason_code : "AIAPI_COMMAND_REJECTED",
      correlation_id: serverCorrelation,
    };
  }

  return {
    ok: true,
    value: record && "value" in record ? record.value : raw,
    correlation_id: serverCorrelation,
  };
}
