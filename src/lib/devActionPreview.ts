import {
  DEV_AUDIENCE_UID,
  DEV_CAMPAIGN_UID,
  DEV_CANDIDATES_UID,
  DEV_COMPANIES_UID,
  DEV_DELIVERIES_UID,
  DEV_ERROR_UID,
  DEV_EXPORT_UID,
  DEV_JOB_UID,
  DEV_MERGE_UID,
  DEV_PROFILE_UID,
  DEV_QUERY_UID,
  DEV_SIGNALS_UID,
  activeEmailContact,
  companyEligibleForMessage,
  eligibleAudience,
  type DevCampaign,
  type DevCandidate,
  type DevCompany,
  type DevContact,
  type DevContactType,
  type DevDelivery,
  type DevJob,
  type DevMergePreview,
  type DevMode,
  type DevOpportunityState,
  type DevProfile,
  type DevRecipient,
  type DevSignal,
  type DevWorkbench,
  filterCompanies,
  identityResolved,
  newUid,
  nowIso,
  opportunityTransitionAllowed,
  parsePayload,
  profileIsReady,
  readDevWorkbench,
  usable,
} from "./devState";
import { acceptDeliveryIntent, acceptDiscoveryIntent } from "./devSharedOwners";
import { mergeDiscoverySignals, type AcquisitionCollectResult } from "./sharedAcquisition";

function serialize(value: unknown): string {
  return JSON.stringify(value);
}

function patchFrom(workbench: DevWorkbench, extra: Record<string, string> = {}): Record<string, string> {
  return {
    [DEV_PROFILE_UID]: workbench.profile ? serialize(workbench.profile) : "",
    [DEV_JOB_UID]: workbench.job ? serialize(workbench.job) : "",
    [DEV_SIGNALS_UID]: serialize(workbench.signals),
    [DEV_COMPANIES_UID]: serialize(workbench.companies),
    [DEV_MERGE_UID]: workbench.merge ? serialize(workbench.merge) : "",
    [DEV_QUERY_UID]: workbench.query,
    [DEV_ERROR_UID]: workbench.error ? serialize(workbench.error) : "",
    [DEV_EXPORT_UID]: workbench.exported ? serialize(workbench.exported) : "",
    [DEV_CANDIDATES_UID]: serialize(workbench.candidates),
    [DEV_CAMPAIGN_UID]: workbench.campaign ? serialize(workbench.campaign) : "",
    [DEV_DELIVERIES_UID]: serialize(workbench.deliveries),
    [DEV_AUDIENCE_UID]: workbench.audienceQuery,
    ...extra,
  };
}

function fail(workbench: DevWorkbench, code: string): Record<string, string> {
  return patchFrom({ ...workbench, error: { code, at: nowIso() } });
}

function clearError(workbench: DevWorkbench): DevWorkbench {
  return { ...workbench, error: null };
}

function modeFrom(raw: string | undefined, fallback: DevMode): DevMode {
  return raw === "CONTINUOUS" || raw === "SINGLE" ? raw : fallback;
}

function contactTypeFrom(raw: string | undefined): DevContactType | null {
  if (raw === "EMAIL" || raw === "PHONE" || raw === "ADDRESS") return raw;
  return null;
}

function opportunityFrom(raw: string | undefined): DevOpportunityState | null {
  if (
    raw === "OPEN" ||
    raw === "QUALIFIED" ||
    raw === "CONTACTED" ||
    raw === "REPLIED" ||
    raw === "PROPOSAL" ||
    raw === "WON" ||
    raw === "LOST" ||
    raw === "SUPPRESSED"
  ) {
    return raw;
  }
  return null;
}

function startJob(profile: DevProfile): DevJob {
  const accepted = acceptDiscoveryIntent();
  return {
    jobId: newUid("JOB"),
    profileId: profile.profileId,
    profileVersion: profile.version,
    status: accepted.status,
    mode: profile.mode,
    blocker: accepted.blocker,
    startedAt: nowIso(),
    updatedAt: nowIso(),
  };
}

export function applyDiscoveryCollection(
  current: (uid: string) => string | null,
  result: AcquisitionCollectResult,
): Record<string, string> {
  const workbench = readDevWorkbench(current);
  if (!workbench.job) return fail(workbench, "DEV_JOB_NOT_STOPPABLE");
  if (workbench.job.status !== "RUNNING" && workbench.job.status !== "EXTERNAL_PENDING") {
    return fail(workbench, "DEV_JOB_NOT_STOPPABLE");
  }
  if (!result.ok) {
    const job: DevJob = {
      ...workbench.job,
      status: "EXTERNAL_PENDING",
      blocker: result.reason || "SHARED_ACQUISITION_UNAVAILABLE",
      updatedAt: nowIso(),
    };
    return patchFrom(clearError({ ...workbench, job }));
  }
  const job: DevJob = {
    ...workbench.job,
    status: "RUNNING",
    blocker: "",
    updatedAt: nowIso(),
  };
  return patchFrom(
    clearError({
      ...workbench,
      job,
      signals: mergeDiscoverySignals(workbench.signals, result.signals),
    }),
  );
}

function qualifyCompany(signal: DevSignal, existing: DevCompany[]): DevCompany {
  const matched = existing.find(
    (company) =>
      identityResolved(signal.identityKind) &&
      identityResolved(company.identityKind) &&
      company.identityValue === signal.identityValue,
  );
  if (matched) {
    const aliases = matched.aliases.includes(signal.companyName)
      ? matched.aliases
      : [...matched.aliases, signal.companyName];
    return {
      ...matched,
      aliases,
      evidence: signal.evidence,
      version: matched.version + 1,
    };
  }
  return {
    companyId: newUid("CO"),
    name: signal.companyName,
    identityKind: signal.identityKind,
    identityValue: signal.identityValue,
    aliases: [signal.companyName],
    contacts: [],
    opportunity: { opportunityId: newUid("OPP"), state: "OPEN" },
    suppression: "",
    evidence: signal.evidence,
    mergedFrom: [],
    version: 1,
  };
}

function replaceCompany(companies: DevCompany[], next: DevCompany): DevCompany[] {
  return companies.map((company) => (company.companyId === next.companyId ? next : company));
}

function upsertCompany(companies: DevCompany[], next: DevCompany): DevCompany[] {
  return companies.some((company) => company.companyId === next.companyId)
    ? replaceCompany(companies, next)
    : [...companies, next];
}

export function previewDevAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const workbench = readDevWorkbench(current);
  const payload = parsePayload(nextValue);

  if (actionUid.startsWith("DEV-01-ACT-STAGE-")) {
    return patchFrom(clearError(workbench));
  }

  if (actionUid === "DEV-01-ACT-PROFILE-SAVE") {
    const prior = workbench.profile;
    const next: DevProfile = {
      profileId: prior?.profileId ?? newUid("PRF"),
      version: (prior?.version ?? 0) + 1,
      product: usable(payload.product) || prior?.product || "",
      industry: usable(payload.industry) || prior?.industry || "",
      market: usable(payload.market) || prior?.market || "",
      keywords: usable(payload.keywords) || prior?.keywords || "",
      exclude: usable(payload.exclude) || prior?.exclude || "",
      mode: modeFrom(payload.mode, prior?.mode ?? "SINGLE"),
      status: "DRAFT",
    };
    if (!profileIsReady(next)) return fail(workbench, "DEV_PROFILE_INCOMPLETE");
    return patchFrom(clearError({ ...workbench, profile: next }));
  }

  if (actionUid === "DEV-01-ACT-DISCOVERY-START") {
    if (!profileIsReady(workbench.profile)) return fail(workbench, "DEV_PROFILE_REQUIRED");
    if (workbench.job?.status === "RUNNING" || workbench.job?.status === "EXTERNAL_PENDING") {
      return fail(workbench, "DEV_JOB_ALREADY_ACTIVE");
    }
    const profile: DevProfile = { ...workbench.profile!, status: "ACTIVE" };
    const job = startJob(profile);
    return patchFrom(clearError({ ...workbench, profile, job }));
  }

  if (actionUid === "DEV-01-ACT-DISCOVERY-PAUSE") {
    if (workbench.job?.status !== "RUNNING") return fail(workbench, "DEV_JOB_NOT_RUNNING");
    const job: DevJob = { ...workbench.job, status: "PAUSED", updatedAt: nowIso() };
    const profile = workbench.profile ? { ...workbench.profile, status: "PAUSED" as const } : workbench.profile;
    return patchFrom(clearError({ ...workbench, job, profile }));
  }

  if (actionUid === "DEV-01-ACT-DISCOVERY-RESUME") {
    if (workbench.job?.status !== "PAUSED") return fail(workbench, "DEV_JOB_NOT_PAUSED");
    const accepted = acceptDiscoveryIntent();
    const job: DevJob = {
      ...workbench.job,
      status: accepted.status,
      blocker: accepted.blocker,
      updatedAt: nowIso(),
    };
    const profile = workbench.profile ? { ...workbench.profile, status: "ACTIVE" as const } : workbench.profile;
    return patchFrom(clearError({ ...workbench, job, profile }));
  }

  if (actionUid === "DEV-01-ACT-DISCOVERY-STOP") {
    if (workbench.job?.status !== "RUNNING" && workbench.job?.status !== "EXTERNAL_PENDING") {
      return fail(workbench, "DEV_JOB_NOT_STOPPABLE");
    }
    const job: DevJob = { ...workbench.job, status: "STOPPED", updatedAt: nowIso() };
    const profile = workbench.profile ? { ...workbench.profile, status: "PAUSED" as const } : workbench.profile;
    return patchFrom(clearError({ ...workbench, job, profile }));
  }

  if (actionUid === "DEV-01-ACT-SIGNAL-QUALIFY") {
    const signalId = usable(payload.signalId);
    const signal = workbench.signals.find((item) => item.signalId === signalId);
    if (!signal) return fail(workbench, "DEV_SIGNAL_REQUIRED");
    if (signal.status !== "NEW") return fail(workbench, "DEV_SIGNAL_NOT_NEW");
    const nextSignal: DevSignal = { ...signal, status: "QUALIFIED", version: signal.version + 1 };
    const company = qualifyCompany(nextSignal, workbench.companies);
    return patchFrom(
      clearError({
        ...workbench,
        signals: workbench.signals.map((item) => (item.signalId === signalId ? nextSignal : item)),
        companies: upsertCompany(workbench.companies, company),
      }),
    );
  }

  if (actionUid === "DEV-01-ACT-SIGNAL-IGNORE") {
    const signalId = usable(payload.signalId);
    const signal = workbench.signals.find((item) => item.signalId === signalId);
    if (!signal) return fail(workbench, "DEV_SIGNAL_REQUIRED");
    if (signal.status !== "NEW") return fail(workbench, "DEV_SIGNAL_NOT_NEW");
    const nextSignal: DevSignal = { ...signal, status: "IGNORED", version: signal.version + 1 };
    return patchFrom(
      clearError({
        ...workbench,
        signals: workbench.signals.map((item) => (item.signalId === signalId ? nextSignal : item)),
      }),
    );
  }

  if (actionUid === "DEV-01-ACT-DIRECTORY-SEARCH") {
    const query = usable(payload.query);
    return patchFrom(clearError({ ...workbench, query }));
  }

  if (actionUid === "DEV-01-ACT-MERGE-PREVIEW") {
    const ids = (payload.companyIds ?? []).map((id) => usable(id)).filter(Boolean);
    const selected = workbench.companies.filter((company) => ids.includes(company.companyId));
    if (selected.length < 2) return fail(workbench, "DEV_MERGE_SELECTION_REQUIRED");
    const resolved = selected.filter((company) => identityResolved(company.identityKind) && company.identityValue);
    if (resolved.length < 2) return fail(workbench, "DEV_MERGE_NAME_ONLY_BLOCKED");
    const identityValues = new Set(resolved.map((company) => company.identityValue));
    if (identityValues.size !== 1) return fail(workbench, "DEV_MERGE_IDENTITY_CONFLICT");
    const survivor = resolved[0];
    const preview: DevMergePreview = {
      previewId: newUid("MRG"),
      survivorId: survivor.companyId,
      mergedIds: resolved.slice(1).map((company) => company.companyId),
      conflicts: [],
      version: 1,
    };
    return patchFrom(clearError({ ...workbench, merge: preview }));
  }

  if (actionUid === "DEV-01-ACT-MERGE") {
    const preview = workbench.merge;
    if (!preview) return fail(workbench, "DEV_MERGE_PREVIEW_REQUIRED");
    const survivor = workbench.companies.find((company) => company.companyId === preview.survivorId);
    const merged = workbench.companies.filter((company) => preview.mergedIds.includes(company.companyId));
    if (!survivor || merged.length !== preview.mergedIds.length) return fail(workbench, "DEV_MERGE_STALE");
    if (!identityResolved(survivor.identityKind)) return fail(workbench, "DEV_MERGE_NAME_ONLY_BLOCKED");
    const aliases = [...new Set([survivor.name, ...survivor.aliases, ...merged.flatMap((company) => [company.name, ...company.aliases])])];
    const contacts = [...survivor.contacts];
    for (const company of merged) {
      for (const contact of company.contacts) {
        if (!contacts.some((item) => item.type === contact.type && item.value === contact.value)) contacts.push(contact);
      }
    }
    const nextSurvivor: DevCompany = {
      ...survivor,
      aliases,
      contacts,
      evidence: [survivor.evidence, ...merged.map((company) => company.evidence)].filter(Boolean).join(" | "),
      mergedFrom: [...survivor.mergedFrom, ...merged.map((company) => company.companyId)],
      version: survivor.version + 1,
    };
    const remaining = workbench.companies
      .filter((company) => !preview.mergedIds.includes(company.companyId))
      .map((company) => (company.companyId === nextSurvivor.companyId ? nextSurvivor : company));
    return patchFrom(clearError({ ...workbench, companies: remaining, merge: null }));
  }

  if (actionUid === "DEV-01-ACT-EXPORT") {
    const matched = filterCompanies(workbench.companies, workbench.query);
    return patchFrom(
      clearError({
        ...workbench,
        exported: {
          exportedAt: nowIso(),
          query: workbench.query,
          companyCount: matched.length,
          payload: serialize(matched),
        },
      }),
    );
  }

  if (actionUid === "DEV-01-ACT-CONTACT-UPSERT") {
    const companyId = usable(payload.companyId);
    const company = workbench.companies.find((item) => item.companyId === companyId);
    const type = contactTypeFrom(payload.contactType);
    const value = usable(payload.contactValue);
    if (!company || !type || !value) return fail(workbench, "DEV_CONTACT_REQUIRED");
    const existing = company.contacts.find((item) => item.type === type && item.value === value);
    const nextContact: DevContact = existing
      ? { ...existing, source: usable(payload.contactSource) || existing.source, status: "ACTIVE" }
      : {
          contactId: newUid("CT"),
          type,
          value,
          source: usable(payload.contactSource) || "MANUAL",
          status: "ACTIVE",
        };
    const contacts = existing
      ? company.contacts.map((item) => (item.contactId === existing.contactId ? nextContact : item))
      : [...company.contacts, nextContact];
    return patchFrom(
      clearError({
        ...workbench,
        companies: replaceCompany(workbench.companies, { ...company, contacts, version: company.version + 1 }),
      }),
    );
  }

  if (actionUid === "DEV-01-ACT-OPPORTUNITY-STATE") {
    const companyId = usable(payload.companyId);
    const company = workbench.companies.find((item) => item.companyId === companyId);
    const nextState = opportunityFrom(payload.nextState);
    if (!company || !nextState) return fail(workbench, "DEV_OPPORTUNITY_REQUIRED");
    if (!opportunityTransitionAllowed(company.opportunity.state, nextState)) {
      return fail(workbench, "DEV_OPPORTUNITY_ILLEGAL");
    }
    return patchFrom(
      clearError({
        ...workbench,
        companies: replaceCompany(workbench.companies, {
          ...company,
          opportunity: { ...company.opportunity, state: nextState },
          version: company.version + 1,
        }),
      }),
    );
  }

  if (actionUid === "DEV-01-ACT-SOURCE-MANAGE") {
    return patchFrom(clearError(workbench), { "DEV-01-BTN-SOURCE-MANAGE": "kb-source" });
  }

  if (actionUid === "DEV-01-ACT-CANDIDATE-CREATE") {
    const companyId = usable(payload.companyId) || workbench.companies.find((item) => companyEligibleForMessage(item))?.companyId || "";
    const company = workbench.companies.find((item) => item.companyId === companyId);
    if (!company) return fail(workbench, "DEV_CANDIDATE_COMPANY_REQUIRED");
    if (!companyEligibleForMessage(company)) return fail(workbench, "DEV_CANDIDATE_CONTACT_REQUIRED");
    const contact = activeEmailContact(company)!;
    const existing = workbench.candidates.find(
      (item) => item.companyId === company.companyId && item.status === "REVIEW",
    );
    if (existing) return fail(workbench, "DEV_CANDIDATE_ALREADY_OPEN");
    const next: DevCandidate = {
      candidateId: newUid("CAN"),
      companyId: company.companyId,
      companyName: company.name,
      opportunityId: company.opportunity.opportunityId,
      contactId: contact.contactId,
      contactValue: contact.value,
      personalization: company.name,
      policy: "PASS",
      status: "REVIEW",
      version: 1,
      evidence: company.evidence,
    };
    return patchFrom(clearError({ ...workbench, candidates: [...workbench.candidates, next] }));
  }

  if (actionUid === "DEV-01-ACT-CANDIDATE-DECIDE") {
    const candidateId = usable(payload.candidateId);
    const candidate = workbench.candidates.find((item) => item.candidateId === candidateId) ?? workbench.candidates.find((item) => item.status === "REVIEW");
    if (!candidate) return fail(workbench, "DEV_CANDIDATE_REQUIRED");
    if (candidate.status !== "REVIEW") return fail(workbench, "DEV_CANDIDATE_NOT_REVIEW");
    const next: DevCandidate = { ...candidate, status: "APPROVED", version: candidate.version + 1 };
    return patchFrom(
      clearError({
        ...workbench,
        candidates: workbench.candidates.map((item) => (item.candidateId === next.candidateId ? next : item)),
      }),
    );
  }

  if (actionUid === "DEV-01-ACT-CR-CREATE") {
    const candidateId = usable(payload.candidateId);
    const candidate = workbench.candidates.find((item) => item.candidateId === candidateId) ?? workbench.candidates.find((item) => item.status === "REVIEW");
    if (!candidate) return fail(workbench, "DEV_CANDIDATE_REQUIRED");
    if (candidate.status !== "REVIEW") return fail(workbench, "DEV_CANDIDATE_NOT_REVIEW");
    const next: DevCandidate = { ...candidate, status: "CHANGE_REQUEST", version: candidate.version + 1 };
    const campaign = workbench.campaign?.candidateId === next.candidateId && workbench.campaign.status === "REVIEW" ? null : workbench.campaign;
    return patchFrom(
      clearError({
        ...workbench,
        candidates: workbench.candidates.map((item) => (item.candidateId === next.candidateId ? next : item)),
        campaign,
      }),
    );
  }

  if (actionUid === "DEV-01-ACT-CAMPAIGN-SEARCH") {
    const audienceQuery = usable(payload.audienceQuery ?? payload.query);
    return patchFrom(clearError({ ...workbench, audienceQuery }));
  }

  if (actionUid === "DEV-01-ACT-CAMPAIGN-CREATE") {
    const approved = workbench.candidates.filter((item) => item.status === "APPROVED");
    const candidateId = usable(payload.candidateId);
    const candidate = approved.find((item) => item.candidateId === candidateId) ?? approved[approved.length - 1];
    if (!candidate) return fail(workbench, "DEV_CAMPAIGN_CANDIDATE_REQUIRED");
    if (workbench.campaign && (workbench.campaign.status === "REVIEW" || workbench.campaign.status === "APPROVED" || workbench.campaign.status === "QUEUED")) {
      return fail(workbench, "DEV_CAMPAIGN_ALREADY_OPEN");
    }
    const matched = eligibleAudience(workbench.companies, workbench.audienceQuery);
    if (!matched.length) return fail(workbench, "DEV_CAMPAIGN_RECIPIENT_REQUIRED");
    const recipients: DevRecipient[] = matched.map(({ company, contact }) => ({
      recipientId: newUid("RCP"),
      companyId: company.companyId,
      companyName: company.name,
      contactId: contact.contactId,
      contactValue: contact.value,
      suppression: company.suppression,
      candidateId: candidate.candidateId,
      messageVersion: candidate.version,
    }));
    const campaign: DevCampaign = {
      campaignId: newUid("CMP"),
      candidateId: candidate.candidateId,
      candidateVersion: candidate.version,
      status: "REVIEW",
      audienceQuery: workbench.audienceQuery,
      recipients,
      previewed: true,
      killReason: "",
      version: 1,
      updatedAt: nowIso(),
    };
    return patchFrom(clearError({ ...workbench, campaign }));
  }

  if (actionUid === "DEV-01-ACT-CAMPAIGN-APPROVE") {
    const campaign = workbench.campaign;
    if (!campaign) return fail(workbench, "DEV_CAMPAIGN_REQUIRED");
    if (campaign.status !== "REVIEW") return fail(workbench, "DEV_CAMPAIGN_NOT_REVIEW");
    if (!campaign.previewed || !campaign.recipients.length) return fail(workbench, "DEV_CAMPAIGN_PREVIEW_REQUIRED");
    const candidate = workbench.candidates.find((item) => item.candidateId === campaign.candidateId);
    if (!candidate || candidate.status !== "APPROVED" || candidate.version !== campaign.candidateVersion) {
      return fail(workbench, "DEV_CAMPAIGN_VERSION_STALE");
    }
    if (campaign.recipients.some((item) => item.suppression)) return fail(workbench, "DEV_CAMPAIGN_SUPPRESSED");
    const next: DevCampaign = { ...campaign, status: "APPROVED", version: campaign.version + 1, updatedAt: nowIso() };
    return patchFrom(clearError({ ...workbench, campaign: next }));
  }

  if (actionUid === "DEV-01-ACT-EMAIL-DISPATCH") {
    const campaign = workbench.campaign;
    if (!campaign) return fail(workbench, "DEV_CAMPAIGN_REQUIRED");
    if (campaign.status !== "APPROVED") return fail(workbench, "DEV_DISPATCH_NOT_APPROVED");
    if (!campaign.recipients.length) return fail(workbench, "DEV_CAMPAIGN_PREVIEW_REQUIRED");
    if (campaign.recipients.some((item) => item.suppression)) return fail(workbench, "DEV_CAMPAIGN_SUPPRESSED");
    const candidate = workbench.candidates.find((item) => item.candidateId === campaign.candidateId);
    if (!candidate || candidate.status !== "APPROVED" || candidate.version !== campaign.candidateVersion) {
      return fail(workbench, "DEV_CAMPAIGN_VERSION_STALE");
    }
    const accepted = acceptDeliveryIntent();
    const deliveries: DevDelivery[] = campaign.recipients.map((recipient) => ({
      deliveryId: newUid("DLV"),
      campaignId: campaign.campaignId,
      recipientId: recipient.recipientId,
      companyId: recipient.companyId,
      to: recipient.contactValue,
      cc: 0,
      bcc: 0,
      status: accepted.status,
      result: accepted.result,
      idempotencyKey: `${campaign.campaignId}:${recipient.recipientId}:${campaign.candidateVersion}`,
      version: 1,
    }));
    const next: DevCampaign = { ...campaign, status: "QUEUED", version: campaign.version + 1, updatedAt: nowIso() };
    return patchFrom(clearError({ ...workbench, campaign: next, deliveries }));
  }

  if (actionUid === "DEV-01-ACT-REFRESH") {
    return patchFrom(clearError(workbench));
  }

  if (actionUid === "DEV-01-ACT-KILL-SWITCH") {
    const campaign = workbench.campaign;
    if (!campaign) return fail(workbench, "DEV_KILL_TARGET_REQUIRED");
    if (campaign.status !== "QUEUED" && campaign.status !== "APPROVED") return fail(workbench, "DEV_KILL_NOT_APPLICABLE");
    const reason = usable(payload.reason) || "OPERATOR_STOP";
    const next: DevCampaign = {
      ...campaign,
      status: "STOPPED",
      killReason: reason,
      version: campaign.version + 1,
      updatedAt: nowIso(),
    };
    const deliveries = workbench.deliveries.map((item) =>
      item.campaignId === campaign.campaignId && item.status !== "STOPPED"
        ? { ...item, status: "STOPPED" as const, result: "STOPPED", version: item.version + 1 }
        : item,
    );
    return patchFrom(clearError({ ...workbench, campaign: next, deliveries }));
  }

  void controlUid;
  return {};
}
