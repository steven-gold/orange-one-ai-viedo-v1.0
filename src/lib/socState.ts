export const SOC_PLATFORMS_UID = "SOC-01-STATE-PLATFORMS";
export const SOC_ACCOUNTS_UID = "SOC-01-STATE-ACCOUNTS";
export const SOC_DISCOVERY_UID = "SOC-01-STATE-DISCOVERY";
export const SOC_TARGETS_UID = "SOC-01-STATE-TARGETS";
export const SOC_PACKAGE_UID = "SOC-01-STATE-PACKAGE";
export const SOC_POLICY_UID = "SOC-01-STATE-POLICY";
export const SOC_REQUESTS_UID = "SOC-01-STATE-REQUESTS";
export const SOC_QUERY_UID = "SOC-01-STATE-QUERY";
export const SOC_RECORD_QUERY_UID = "SOC-01-STATE-RECORD-QUERY";
export const SOC_ERROR_UID = "SOC-01-STATE-ERROR";
export const SOC_KILL_UID = "SOC-01-STATE-KILL";
export const SOC_REVEAL_UID = "SOC-01-STATE-REVEAL";

export const SOC_EXTRA_PROJECTION_KEYS = [
  SOC_PLATFORMS_UID,
  SOC_ACCOUNTS_UID,
  SOC_DISCOVERY_UID,
  SOC_TARGETS_UID,
  SOC_PACKAGE_UID,
  SOC_POLICY_UID,
  SOC_REQUESTS_UID,
  SOC_QUERY_UID,
  SOC_RECORD_QUERY_UID,
  SOC_ERROR_UID,
  SOC_KILL_UID,
  SOC_REVEAL_UID,
] as const;

export type SocEnableState = "ENABLED" | "DISABLED";
export type SocAccountBinding = "UNBOUND" | "CONFIGURED" | "BOUND_LOCKED" | "REAUTH_REQUIRED";
export type SocCredentialStatus = "NOT_SET" | "SET" | "REAUTH_REQUIRED";
export type SocDiscoveryMode = "SINGLE_RUN" | "CONTINUOUS";
export type SocDiscoveryStatus = "RUNNING" | "EXTERNAL_PENDING" | "STOPPED";
export type SocTargetStatus =
  | "DISCOVERED"
  | "READY_TO_JOIN"
  | "MANUAL_ACTION_REQUIRED"
  | "PENDING_ADMIN_APPROVAL"
  | "JOINED"
  | "READY_TO_POST"
  | "PENDING_EXTERNAL"
  | "POSTED"
  | "COOLDOWN"
  | "UNAVAILABLE";
export type SocCandidateState = "DRAFT" | "REVIEW" | "APPROVED" | "REJECTED" | "RETURN";
export type SocPolicyCheck = "PASS" | "BLOCKED" | "";
export type SocRequestStatus = "PENDING_EXTERNAL" | "STOPPED" | "POSTED";
export type SocCandidateDecision = "APPROVE" | "REJECT" | "RETURN";

export interface SocPlatform {
  platformKey: string;
  displayName: string;
  capability: string;
  policy: string;
  health: string;
  enable: SocEnableState;
  version: number;
}

export interface SocAccount {
  accountId: string;
  platformKey: string;
  displayName: string;
  loginIdentifier: string;
  authMode: string;
  binding: SocAccountBinding;
  credentialStatus: SocCredentialStatus;
  credentialMasked: string;
  version: number;
}

export interface SocDiscovery {
  jobId: string;
  jobName: string;
  platformKey: string;
  targetTypes: string;
  categories: string;
  keywords: string;
  mode: SocDiscoveryMode;
  status: SocDiscoveryStatus;
  blocker: string;
  version: number;
  startedAt: string;
  updatedAt: string;
}

export interface SocTarget {
  targetId: string;
  platformKey: string;
  name: string;
  targetType: string;
  capability: string;
  status: SocTargetStatus;
  signal: string;
  evidence: string;
  version: number;
}

export interface SocPackage {
  packageId: string;
  releaseSource: string;
  platformKey: string;
  variant: string;
  policyCheck: SocPolicyCheck;
  candidate: SocCandidateState;
  hash: string;
  version: number;
}

export interface SocPolicy {
  targetId: string;
  minIntervalHours: number;
  dailyLimit: number;
  weeklyLimit: number;
  sameCooldownHours: number;
  similarCooldownHours: number;
  allowedWindow: string;
  notes: string;
  version: number;
}

export interface SocRequest {
  requestId: string;
  targetId: string;
  accountId: string;
  packageId: string;
  packageVersion: number;
  packageHash: string;
  status: SocRequestStatus;
  external: string;
  metrics: string;
  interaction: string;
  callback: string;
  incident: string;
  idempotencyKey: string;
  version: number;
  createdAt: string;
}

export interface SocErrorState {
  code: string;
  at: string;
}

export interface SocKillState {
  active: boolean;
  reason: string;
  at: string;
}

export interface SocRevealState {
  accountId: string;
  at: string;
}

export interface SocWorkbench {
  platforms: SocPlatform[];
  accounts: SocAccount[];
  discovery: SocDiscovery | null;
  targets: SocTarget[];
  content: SocPackage | null;
  policy: SocPolicy | null;
  requests: SocRequest[];
  query: string;
  recordQuery: string;
  error: SocErrorState | null;
  kill: SocKillState | null;
  reveal: SocRevealState | null;
}

export interface SocActionPayload {
  platformKey?: string;
  displayName?: string;
  enable?: string;
  loginIdentifier?: string;
  authMode?: string;
  credentialValue?: string;
  accountId?: string;
  reason?: string;
  jobName?: string;
  targetTypes?: string;
  categories?: string;
  keywords?: string;
  mode?: string;
  targetId?: string;
  query?: string;
  releaseSource?: string;
  variant?: string;
  decision?: string;
  packageId?: string;
  minIntervalHours?: number | string;
  dailyLimit?: number | string;
  weeklyLimit?: number | string;
  sameCooldownHours?: number | string;
  similarCooldownHours?: number | string;
  allowedWindow?: string;
  notes?: string;
  channelAccountId?: string;
  contentPackageId?: string;
  name?: string;
  targetType?: string;
  requestId?: string;
  metrics?: string;
  interaction?: string;
}

export function parseJson<T>(raw: string | null | undefined, fallback: T): T {
  const text = (raw ?? "").trim();
  if (!text) return fallback;
  try {
    return JSON.parse(text) as T;
  } catch {
    return fallback;
  }
}

export function parseSocPayload(raw: string | undefined): SocActionPayload {
  const parsed = parseJson<SocActionPayload>(raw, {});
  return parsed && typeof parsed === "object" ? parsed : {};
}

export function readSocWorkbench(current: (uid: string) => string | null): SocWorkbench {
  return {
    platforms: parseJson<SocPlatform[]>(current(SOC_PLATFORMS_UID), []),
    accounts: parseJson<SocAccount[]>(current(SOC_ACCOUNTS_UID), []),
    discovery: parseJson<SocDiscovery | null>(current(SOC_DISCOVERY_UID), null),
    targets: parseJson<SocTarget[]>(current(SOC_TARGETS_UID), []),
    content: parseJson<SocPackage | null>(current(SOC_PACKAGE_UID), null),
    policy: parseJson<SocPolicy | null>(current(SOC_POLICY_UID), null),
    requests: parseJson<SocRequest[]>(current(SOC_REQUESTS_UID), []),
    query: (current(SOC_QUERY_UID) ?? "").trim(),
    recordQuery: (current(SOC_RECORD_QUERY_UID) ?? "").trim(),
    error: parseJson<SocErrorState | null>(current(SOC_ERROR_UID), null),
    kill: parseJson<SocKillState | null>(current(SOC_KILL_UID), null),
    reveal: parseJson<SocRevealState | null>(current(SOC_REVEAL_UID), null),
  };
}

export function newUid(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function nowIso(): string {
  return new Date().toISOString();
}

export function usable(value: string | null | undefined): string {
  return (value ?? "").trim().slice(0, 400);
}

export function fieldMap(fields: Array<{ controlUid: string; value: string | null }>): (uid: string) => string | null {
  const byUid = new Map(fields.map((field) => [field.controlUid, field.value]));
  return (uid) => byUid.get(uid) ?? null;
}

export function workbenchFromFields(fields: Array<{ controlUid: string; value: string | null }>): SocWorkbench {
  return readSocWorkbench(fieldMap(fields));
}

export function platformEnabled(platform: SocPlatform | undefined): boolean {
  return platform?.enable === "ENABLED";
}

export function boundAccountForPlatform(accounts: SocAccount[], platformKey: string): SocAccount | null {
  return (
    accounts.find(
      (account) =>
        account.platformKey === platformKey &&
        (account.binding === "BOUND_LOCKED" || account.binding === "CONFIGURED") &&
        account.credentialStatus === "SET",
    ) ?? null
  );
}

export function targetReadyToPost(target: SocTarget | undefined): boolean {
  return target?.status === "JOINED" || target?.status === "READY_TO_POST";
}

export function packageApproved(content: SocPackage | null): boolean {
  return Boolean(content && content.candidate === "APPROVED" && content.hash && content.version > 0);
}

export function filterTargets(targets: SocTarget[], query: string): SocTarget[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return targets;
  return targets.filter((target) => {
    const hay = [target.name, target.platformKey, target.targetType, target.status, target.signal, target.capability]
      .join(" ")
      .toLowerCase();
    return hay.includes(needle);
  });
}

export function filterRequests(requests: SocRequest[], query: string): SocRequest[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return requests;
  return requests.filter((request) => {
    const hay = [request.requestId, request.targetId, request.accountId, request.status, request.external, request.callback]
      .join(" ")
      .toLowerCase();
    return hay.includes(needle);
  });
}

export function packageHash(releaseSource: string, platformKey: string, variant: string, version: number): string {
  const raw = `${releaseSource}|${platformKey}|${variant}|${version}`;
  let hash = 2166136261;
  for (let index = 0; index < raw.length; index += 1) {
    hash ^= raw.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `pkg-${(hash >>> 0).toString(16)}`;
}

export function highRiskActive(workbench: SocWorkbench): boolean {
  if (workbench.kill?.active) return true;
  return workbench.requests.some((request) => request.status === "PENDING_EXTERNAL");
}
