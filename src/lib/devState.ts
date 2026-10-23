export const DEV_PROFILE_UID = "DEV-01-STATE-PROFILE";
export const DEV_JOB_UID = "DEV-01-STATE-JOB";
export const DEV_SIGNALS_UID = "DEV-01-STATE-SIGNALS";
export const DEV_COMPANIES_UID = "DEV-01-STATE-COMPANIES";
export const DEV_MERGE_UID = "DEV-01-STATE-MERGE";
export const DEV_QUERY_UID = "DEV-01-STATE-QUERY";
export const DEV_ERROR_UID = "DEV-01-STATE-ERROR";
export const DEV_EXPORT_UID = "DEV-01-STATE-EXPORT";
export const DEV_CANDIDATES_UID = "DEV-01-STATE-CANDIDATES";
export const DEV_CAMPAIGN_UID = "DEV-01-STATE-CAMPAIGN";
export const DEV_DELIVERIES_UID = "DEV-01-STATE-DELIVERIES";
export const DEV_AUDIENCE_UID = "DEV-01-STATE-AUDIENCE";

export const DEV_EXTRA_PROJECTION_KEYS = [
  DEV_PROFILE_UID,
  DEV_JOB_UID,
  DEV_SIGNALS_UID,
  DEV_COMPANIES_UID,
  DEV_MERGE_UID,
  DEV_QUERY_UID,
  DEV_ERROR_UID,
  DEV_EXPORT_UID,
  DEV_CANDIDATES_UID,
  DEV_CAMPAIGN_UID,
  DEV_DELIVERIES_UID,
  DEV_AUDIENCE_UID,
] as const;

export type DevProfileStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "RETIRED";
export type DevJobStatus = "RUNNING" | "PAUSED" | "STOPPED" | "EXTERNAL_PENDING";
export type DevSignalStatus = "NEW" | "QUALIFIED" | "IGNORED" | "ENGAGED" | "CONVERTED" | "SUPPRESSED";
export type DevOpportunityState =
  | "OPEN"
  | "QUALIFIED"
  | "CONTACTED"
  | "REPLIED"
  | "PROPOSAL"
  | "WON"
  | "LOST"
  | "SUPPRESSED";
export type DevMode = "SINGLE" | "CONTINUOUS";
export type DevIdentityKind = "REGISTRATION" | "JURISDICTION" | "NAME_ONLY";
export type DevContactType = "EMAIL" | "PHONE" | "ADDRESS";
export type DevCandidateStatus = "REVIEW" | "APPROVED" | "CHANGE_REQUEST";
export type DevCampaignStatus = "REVIEW" | "APPROVED" | "QUEUED" | "STOPPED";
export type DevDeliveryStatus = "QUEUED" | "EXTERNAL_PENDING" | "STOPPED";

export interface DevProfile {
  profileId: string;
  version: number;
  product: string;
  industry: string;
  market: string;
  keywords: string;
  exclude: string;
  mode: DevMode;
  status: DevProfileStatus;
}

export interface DevJob {
  jobId: string;
  profileId: string;
  profileVersion: number;
  status: DevJobStatus;
  mode: DevMode;
  blocker: string;
  startedAt: string;
  updatedAt: string;
}

export interface DevSignal {
  signalId: string;
  companyName: string;
  intent: string;
  evidence: string;
  freshness: string;
  identityKind: DevIdentityKind;
  identityValue: string;
  match: string;
  opportunity: string;
  status: DevSignalStatus;
  version: number;
}

export interface DevContact {
  contactId: string;
  type: DevContactType;
  value: string;
  source: string;
  status: "ACTIVE" | "DISABLED";
}

export interface DevOpportunity {
  opportunityId: string;
  state: DevOpportunityState;
}

export interface DevCompany {
  companyId: string;
  name: string;
  identityKind: DevIdentityKind;
  identityValue: string;
  aliases: string[];
  contacts: DevContact[];
  opportunity: DevOpportunity;
  suppression: string;
  evidence: string;
  mergedFrom: string[];
  version: number;
}

export interface DevMergePreview {
  previewId: string;
  survivorId: string;
  mergedIds: string[];
  conflicts: string[];
  version: number;
}

export interface DevErrorState {
  code: string;
  at: string;
}

export interface DevExportState {
  exportedAt: string;
  query: string;
  companyCount: number;
  payload: string;
}

export interface DevCandidate {
  candidateId: string;
  companyId: string;
  companyName: string;
  opportunityId: string;
  contactId: string;
  contactValue: string;
  personalization: string;
  policy: "PASS" | "BLOCKED";
  status: DevCandidateStatus;
  version: number;
  evidence: string;
}

export interface DevRecipient {
  recipientId: string;
  companyId: string;
  companyName: string;
  contactId: string;
  contactValue: string;
  suppression: string;
  candidateId: string;
  messageVersion: number;
}

export interface DevCampaign {
  campaignId: string;
  candidateId: string;
  candidateVersion: number;
  status: DevCampaignStatus;
  audienceQuery: string;
  recipients: DevRecipient[];
  previewed: boolean;
  killReason: string;
  version: number;
  updatedAt: string;
}

export interface DevDelivery {
  deliveryId: string;
  campaignId: string;
  recipientId: string;
  companyId: string;
  to: string;
  cc: number;
  bcc: number;
  status: DevDeliveryStatus;
  result: string;
  idempotencyKey: string;
  version: number;
}

export interface DevWorkbench {
  profile: DevProfile | null;
  job: DevJob | null;
  signals: DevSignal[];
  companies: DevCompany[];
  merge: DevMergePreview | null;
  query: string;
  error: DevErrorState | null;
  exported: DevExportState | null;
  candidates: DevCandidate[];
  campaign: DevCampaign | null;
  deliveries: DevDelivery[];
  audienceQuery: string;
}

export interface DevActionPayload {
  product?: string;
  industry?: string;
  market?: string;
  keywords?: string;
  exclude?: string;
  mode?: string;
  signalId?: string;
  query?: string;
  companyIds?: string[];
  survivorId?: string;
  mergedIds?: string[];
  companyId?: string;
  contactType?: string;
  contactValue?: string;
  contactSource?: string;
  opportunityId?: string;
  nextState?: string;
  reason?: string;
  candidateId?: string;
  audienceQuery?: string;
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

export function parsePayload(raw: string | undefined): DevActionPayload {
  const parsed = parseJson<DevActionPayload>(raw, {});
  return parsed && typeof parsed === "object" ? parsed : {};
}

export function readDevWorkbench(current: (uid: string) => string | null): DevWorkbench {
  return {
    profile: parseJson<DevProfile | null>(current(DEV_PROFILE_UID), null),
    job: parseJson<DevJob | null>(current(DEV_JOB_UID), null),
    signals: parseJson<DevSignal[]>(current(DEV_SIGNALS_UID), []),
    companies: parseJson<DevCompany[]>(current(DEV_COMPANIES_UID), []),
    merge: parseJson<DevMergePreview | null>(current(DEV_MERGE_UID), null),
    query: (current(DEV_QUERY_UID) ?? "").trim(),
    error: parseJson<DevErrorState | null>(current(DEV_ERROR_UID), null),
    exported: parseJson<DevExportState | null>(current(DEV_EXPORT_UID), null),
    candidates: parseJson<DevCandidate[]>(current(DEV_CANDIDATES_UID), []),
    campaign: parseJson<DevCampaign | null>(current(DEV_CAMPAIGN_UID), null),
    deliveries: parseJson<DevDelivery[]>(current(DEV_DELIVERIES_UID), []),
    audienceQuery: (current(DEV_AUDIENCE_UID) ?? "").trim(),
  };
}

export function profileIsReady(profile: DevProfile | null): boolean {
  if (!profile) return false;
  return Boolean(profile.product.trim() || profile.industry.trim() || profile.keywords.trim());
}

export function identityResolved(kind: DevIdentityKind): boolean {
  return kind === "REGISTRATION" || kind === "JURISDICTION";
}

const OPPORTUNITY_NEXT: Record<DevOpportunityState, DevOpportunityState[]> = {
  OPEN: ["QUALIFIED", "SUPPRESSED"],
  QUALIFIED: ["CONTACTED", "SUPPRESSED"],
  CONTACTED: ["REPLIED", "SUPPRESSED"],
  REPLIED: ["PROPOSAL", "SUPPRESSED"],
  PROPOSAL: ["WON", "LOST", "SUPPRESSED"],
  WON: [],
  LOST: [],
  SUPPRESSED: [],
};

export function opportunityTransitionAllowed(from: DevOpportunityState, to: DevOpportunityState): boolean {
  return OPPORTUNITY_NEXT[from]?.includes(to) ?? false;
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

export function filterCompanies(companies: DevCompany[], query: string): DevCompany[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return companies;
  return companies.filter((company) => {
    const hay = [company.name, company.identityValue, ...company.aliases, ...company.contacts.map((item) => item.value)]
      .join(" ")
      .toLowerCase();
    return hay.includes(needle);
  });
}

export function activeEmailContact(company: DevCompany): DevContact | null {
  return company.contacts.find((item) => item.status === "ACTIVE" && item.type === "EMAIL") ?? null;
}

export function companyEligibleForMessage(company: DevCompany): boolean {
  return Boolean(activeEmailContact(company)) && company.opportunity.state !== "SUPPRESSED" && !company.suppression;
}

export function eligibleAudience(companies: DevCompany[], query: string): Array<{ company: DevCompany; contact: DevContact }> {
  return filterCompanies(companies, query).flatMap((company) => {
    if (!companyEligibleForMessage(company)) return [];
    const contact = activeEmailContact(company);
    return contact ? [{ company, contact }] : [];
  });
}

export function fieldMap(fields: Array<{ controlUid: string; value: string | null }>): (uid: string) => string | null {
  const byUid = new Map(fields.map((field) => [field.controlUid, field.value]));
  return (uid) => byUid.get(uid) ?? null;
}

export function workbenchFromFields(fields: Array<{ controlUid: string; value: string | null }>): DevWorkbench {
  return readDevWorkbench(fieldMap(fields));
}
