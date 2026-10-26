import { applyDiscoveryCollection, previewDevAction } from "./devActionPreview";
import { bindSharedOwnersForTest } from "./devSharedOwners";
import { PUBLIC_JSON_SOURCES, completedRun, failedRun, sourceRecordFrom } from "./sharedAcquisition";
import { DEV_VISIBLE_CONTROLS } from "../server/domain/dev";
import {
  DEV_AUDIENCE_UID,
  DEV_CAMPAIGN_UID,
  DEV_CANDIDATES_UID,
  DEV_COMPANIES_UID,
  DEV_DELIVERIES_UID,
  DEV_JOB_UID,
  DEV_MERGE_UID,
  DEV_PROFILE_UID,
  DEV_SIGNALS_UID,
  parseJson,
  readDevWorkbench,
  type DevCampaign,
  type DevCandidate,
  type DevCompany,
  type DevDelivery,
  type DevJob,
  type DevMergePreview,
  type DevProfile,
  type DevSignal,
} from "./devState";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

{
  assert(DEV_VISIBLE_CONTROLS.length === 22, "DEV stays at 22 visible controls");
  assert(!DEV_VISIBLE_CONTROLS.includes("DEV-01-BTN-PROFILE-SAVE" as (typeof DEV_VISIBLE_CONTROLS)[number]), "TBL10 profile save stays off the visible denominator");
}

function store(seed: Record<string, string> = {}): {
  current: (uid: string) => string | null;
  apply: (controlUid: string, actionUid: string, nextValue?: string) => Record<string, string>;
} {
  const values = new Map<string, string>(Object.entries(seed));
  const current = (uid: string) => values.get(uid) ?? null;
  const apply = (controlUid: string, actionUid: string, nextValue?: string) => {
    const patch = previewDevAction(controlUid, actionUid, current, nextValue);
    for (const [uid, value] of Object.entries(patch)) values.set(uid, value);
    return patch;
  };
  return { current, apply };
}

{
  bindSharedOwnersForTest({ acquisition: true, delivery: true });
  const { current, apply } = store();
  const incomplete = apply("DEV-01-BTN-PROFILE-SAVE", "DEV-01-ACT-PROFILE-SAVE", JSON.stringify({ product: "" }));
  assert(parseJson<{ code: string }>(incomplete["DEV-01-STATE-ERROR"], { code: "" }).code === "DEV_PROFILE_INCOMPLETE", "empty profile is rejected");

  apply(
    "DEV-01-BTN-PROFILE-SAVE",
    "DEV-01-ACT-PROFILE-SAVE",
    JSON.stringify({ product: "影像工作臺", industry: "媒體", keywords: "企業開發", mode: "CONTINUOUS" }),
  );
  const profile = parseJson<DevProfile | null>(current(DEV_PROFILE_UID), null);
  assert(profile?.status === "DRAFT", "saved profile stays draft");
  assert(profile?.product === "影像工作臺", "profile product persists");
  assert(profile?.language === "zh-TW", "profile language defaults to zh-TW");
  assert(profile?.priority === "NORMAL", "profile priority defaults to NORMAL");
  assert(profile?.sourceScope === "ALLOWED", "profile source scope defaults to ALLOWED");

  apply("DEV-01-BTN-DISCOVERY-START", "DEV-01-ACT-DISCOVERY-START");
  const job = parseJson<DevJob | null>(current(DEV_JOB_UID), null);
  assert(job?.status === "RUNNING", "start binds shared acquisition when the owner is available");
  assert(job?.blocker === "", "available acquisition has no blocker");
  assert(parseJson<DevSignal[]>(current(DEV_SIGNALS_UID), []).length === 0, "start never invents signals");

  apply("DEV-01-BTN-DISCOVERY-PAUSE", "DEV-01-ACT-DISCOVERY-PAUSE");
  assert(parseJson<DevJob | null>(current(DEV_JOB_UID), null)?.status === "PAUSED", "pause requires RUNNING");

  apply("DEV-01-BTN-DISCOVERY-RESUME", "DEV-01-ACT-DISCOVERY-RESUME");
  assert(parseJson<DevJob | null>(current(DEV_JOB_UID), null)?.status === "RUNNING", "resume rebinds shared acquisition");

  apply("DEV-01-BTN-DISCOVERY-STOP", "DEV-01-ACT-DISCOVERY-STOP");
  assert(parseJson<DevJob | null>(current(DEV_JOB_UID), null)?.status === "STOPPED", "running job can stop");
}

{
  bindSharedOwnersForTest({ acquisition: false, delivery: true });
  const { current, apply } = store();
  apply(
    "DEV-01-BTN-PROFILE-SAVE",
    "DEV-01-ACT-PROFILE-SAVE",
    JSON.stringify({ product: "影像工作臺", industry: "媒體", keywords: "企業開發", mode: "SINGLE" }),
  );
  apply("DEV-01-BTN-DISCOVERY-START", "DEV-01-ACT-DISCOVERY-START");
  const job = parseJson<DevJob | null>(current(DEV_JOB_UID), null);
  assert(job?.status === "EXTERNAL_PENDING", "missing acquisition waits externally");
  assert(job?.blocker === "SHARED_ACQUISITION_UNAVAILABLE", "missing acquisition is blocked not faked");
  assert(parseJson<DevSignal[]>(current(DEV_SIGNALS_UID), []).length === 0, "blocked start never invents signals");
  const pause = apply("DEV-01-BTN-DISCOVERY-PAUSE", "DEV-01-ACT-DISCOVERY-PAUSE");
  assert(parseJson<{ code: string }>(pause["DEV-01-STATE-ERROR"], { code: "" }).code === "DEV_JOB_NOT_RUNNING", "pending job cannot pause");
  apply("DEV-01-BTN-DISCOVERY-STOP", "DEV-01-ACT-DISCOVERY-STOP");
  assert(parseJson<DevJob | null>(current(DEV_JOB_UID), null)?.status === "STOPPED", "pending job can stop");
  bindSharedOwnersForTest(null);
}

{
  bindSharedOwnersForTest({ acquisition: true, delivery: true });
  const { current, apply } = store();
  apply(
    "DEV-01-BTN-PROFILE-SAVE",
    "DEV-01-ACT-PROFILE-SAVE",
    JSON.stringify({ product: "影像工作臺", industry: "媒體", keywords: "企業開發", mode: "SINGLE" }),
  );
  apply("DEV-01-BTN-DISCOVERY-START", "DEV-01-ACT-DISCOVERY-START");
  const liveSignal: DevSignal = {
    signalId: "SIG-LIVE",
    companyName: "中華電視股份有限公司",
    intent: "影像工作臺",
    evidence: "臺灣證券交易所上市基本資料 9926 文化創意業",
    freshness: "2026-10-24",
    identityKind: "REGISTRATION",
    identityValue: "TW-03793901",
    match: "resolved",
    opportunity: "OPEN",
    status: "NEW",
    version: 1,
  };
  const patch = applyDiscoveryCollection(current, {
    ok: true,
    source: sourceRecordFrom(PUBLIC_JSON_SOURCES[0], "ACTIVE"),
    run: completedRun(PUBLIC_JSON_SOURCES[0].sourceId, 1),
    signals: [liveSignal],
    items: [],
  });
  assert(parseJson<DevSignal[]>(patch[DEV_SIGNALS_UID], []).length === 1, "collection writes verified signals");
  assert(parseJson<DevJob | null>(patch[DEV_JOB_UID], null)?.status === "RUNNING", "successful collection keeps RUNNING");
  const blocked = applyDiscoveryCollection(current, {
    ok: false,
    source: sourceRecordFrom(PUBLIC_JSON_SOURCES[0], "UNAVAILABLE"),
    run: failedRun(PUBLIC_JSON_SOURCES[0].sourceId, "SHARED_ACQUISITION_UNAVAILABLE"),
    reason: "SHARED_ACQUISITION_UNAVAILABLE",
  });
  assert(parseJson<DevJob | null>(blocked[DEV_JOB_UID], null)?.status === "EXTERNAL_PENDING", "failed collection waits externally");
  assert(parseJson<DevJob | null>(blocked[DEV_JOB_UID], null)?.blocker === "SHARED_ACQUISITION_UNAVAILABLE", "failed collection records blocker");
  bindSharedOwnersForTest(null);
}

{
  const signal: DevSignal = {
    signalId: "SIG-1",
    companyName: "橘一科技",
    intent: "採購",
    evidence: "公開招標公告",
    freshness: "2026-10-23",
    identityKind: "REGISTRATION",
    identityValue: "TW-12345678",
    match: "resolved",
    opportunity: "OPEN",
    status: "NEW",
    version: 1,
    email: "ir@example.com",
    phone: "02-11111111",
  };
  const { current, apply } = store({
    [DEV_SIGNALS_UID]: JSON.stringify([signal, { ...signal, signalId: "SIG-2", companyName: "略過企業", email: undefined }]),
  });
  apply("DEV-01-BTN-SIGNAL-QUALIFY", "DEV-01-ACT-SIGNAL-QUALIFY", JSON.stringify({ signalId: "SIG-1" }));
  const companies = parseJson<DevCompany[]>(current(DEV_COMPANIES_UID), []);
  assert(companies.length === 1, "qualify creates one company");
  assert(companies[0].identityValue === "TW-12345678", "company keeps registration identity");
  assert(companies[0].opportunity.state === "OPEN", "opportunity starts OPEN");
  assert(companies[0].contacts.some((item) => item.type === "EMAIL" && item.value === "ir@example.com"), "qualify copies public email");
  assert(parseJson<DevSignal[]>(current(DEV_SIGNALS_UID), [])[0].status === "QUALIFIED", "signal becomes QUALIFIED");

  apply("DEV-01-BTN-SIGNAL-IGNORE", "DEV-01-ACT-SIGNAL-IGNORE", JSON.stringify({ signalId: "SIG-2" }));
  const ignored = parseJson<DevSignal[]>(current(DEV_SIGNALS_UID), []).find((item) => item.signalId === "SIG-2");
  assert(ignored?.status === "IGNORED", "ignore keeps evidence and marks IGNORED");
  apply("DEV-01-BTN-SIGNAL-IGNORE", "DEV-01-ACT-SIGNAL-IGNORE", JSON.stringify({ signalId: "missing" }));
  assert(parseJson<DevCompany[]>(current(DEV_COMPANIES_UID), []).length === 1, "ignore never creates a company");

  apply("DEV-01-BTN-CANDIDATE-CREATE", "DEV-01-ACT-CANDIDATE-CREATE", JSON.stringify({ companyId: companies[0].companyId }));
  assert(parseJson<DevCandidate[]>(current(DEV_CANDIDATES_UID), [])[0].contactValue === "ir@example.com", "qualify email is enough to create a candidate");
}

{
  const left: DevCompany = {
    companyId: "CO-1",
    name: "橘一科技",
    identityKind: "REGISTRATION",
    identityValue: "TW-12345678",
    aliases: ["橘一"],
    contacts: [{ contactId: "CT-1", type: "EMAIL", value: "a@example.com", source: "WEB", status: "ACTIVE" }],
    opportunity: { opportunityId: "OPP-1", state: "OPEN" },
    suppression: "",
    evidence: "left",
    mergedFrom: [],
    version: 1,
  };
  const right: DevCompany = {
    ...left,
    companyId: "CO-2",
    name: "橘一股份有限公司",
    aliases: ["Orange One"],
    contacts: [{ contactId: "CT-2", type: "PHONE", value: "+8862", source: "WEB", status: "ACTIVE" }],
    evidence: "right",
  };
  const nameOnly: DevCompany = { ...left, companyId: "CO-3", identityKind: "NAME_ONLY", identityValue: "" };
  const { current, apply } = store({ [DEV_COMPANIES_UID]: JSON.stringify([left, right, nameOnly]) });

  const blocked = apply(
    "DEV-01-BTN-MERGE-PREVIEW",
    "DEV-01-ACT-MERGE-PREVIEW",
    JSON.stringify({ companyIds: ["CO-1", "CO-3"] }),
  );
  assert(parseJson<{ code: string }>(blocked["DEV-01-STATE-ERROR"], { code: "" }).code === "DEV_MERGE_NAME_ONLY_BLOCKED", "name-only cannot preview merge");

  apply("DEV-01-BTN-MERGE-PREVIEW", "DEV-01-ACT-MERGE-PREVIEW", JSON.stringify({ companyIds: ["CO-1", "CO-2"] }));
  const preview = parseJson<DevMergePreview | null>(current(DEV_MERGE_UID), null);
  assert(preview?.survivorId === "CO-1", "preview records survivor");

  apply("DEV-01-BTN-MERGE", "DEV-01-ACT-MERGE");
  const companies = parseJson<DevCompany[]>(current(DEV_COMPANIES_UID), []);
  assert(companies.length === 2, "merge keeps survivor and name-only");
  const survivor = companies.find((company) => company.companyId === "CO-1");
  assert(survivor?.aliases.includes("橘一股份有限公司"), "merge keeps aliases");
  assert(survivor?.contacts.length === 2, "merge keeps distinct contacts");
  assert(survivor?.mergedFrom.includes("CO-2"), "merge keeps lineage");
  assert(!current(DEV_MERGE_UID), "merge clears preview");
}

{
  const company: DevCompany = {
    companyId: "CO-9",
    name: "示範公司",
    identityKind: "REGISTRATION",
    identityValue: "TW-999",
    aliases: [],
    contacts: [],
    opportunity: { opportunityId: "OPP-9", state: "OPEN" },
    suppression: "",
    evidence: "",
    mergedFrom: [],
    version: 1,
  };
  const { current, apply } = store({ [DEV_COMPANIES_UID]: JSON.stringify([company]) });
  const illegal = apply(
    "DEV-01-BTN-OPPORTUNITY-STATE",
    "DEV-01-ACT-OPPORTUNITY-STATE",
    JSON.stringify({ companyId: "CO-9", nextState: "WON" }),
  );
  assert(parseJson<{ code: string }>(illegal["DEV-01-STATE-ERROR"], { code: "" }).code === "DEV_OPPORTUNITY_ILLEGAL", "illegal opportunity jump is blocked");
  apply(
    "DEV-01-BTN-OPPORTUNITY-STATE",
    "DEV-01-ACT-OPPORTUNITY-STATE",
    JSON.stringify({ companyId: "CO-9", nextState: "QUALIFIED" }),
  );
  assert(parseJson<DevCompany[]>(current(DEV_COMPANIES_UID), [])[0].opportunity.state === "QUALIFIED", "legal opportunity transition persists");

  apply(
    "DEV-01-BTN-CONTACT-UPSERT",
    "DEV-01-ACT-CONTACT-UPSERT",
    JSON.stringify({ companyId: "CO-9", contactType: "EMAIL", contactValue: "demo@example.com", contactSource: "MANUAL" }),
  );
  assert(parseJson<DevCompany[]>(current(DEV_COMPANIES_UID), [])[0].contacts[0].value === "demo@example.com", "contact upsert persists");

  apply("DEV-01-BTN-DIRECTORY-SEARCH", "DEV-01-ACT-DIRECTORY-SEARCH", JSON.stringify({ query: "示範" }));
  apply("DEV-01-BTN-EXPORT", "DEV-01-ACT-EXPORT");
  assert(parseJson<{ companyCount: number }>(current("DEV-01-STATE-EXPORT"), { companyCount: 0 }).companyCount === 1, "export uses current query");
  apply("DEV-01-BTN-DIRECTORY-SEARCH", "DEV-01-ACT-DIRECTORY-SEARCH", JSON.stringify({ query: "QUALIFIED" }));
  apply("DEV-01-BTN-EXPORT", "DEV-01-ACT-EXPORT");
  assert(parseJson<{ companyCount: number }>(current("DEV-01-STATE-EXPORT"), { companyCount: 0 }).companyCount === 1, "directory search matches opportunity state");
}

{
  const company: DevCompany = {
    companyId: "CO-M",
    name: "示範公司",
    identityKind: "REGISTRATION",
    identityValue: "TW-111",
    aliases: [],
    contacts: [{ contactId: "CT-M", type: "EMAIL", value: "demo@example.com", source: "MANUAL", status: "ACTIVE" }],
    opportunity: { opportunityId: "OPP-M", state: "QUALIFIED" },
    suppression: "",
    evidence: "公開招標",
    mergedFrom: [],
    version: 1,
  };
  const suppressed: DevCompany = {
    ...company,
    companyId: "CO-S",
    name: "抑制公司",
    contacts: [{ contactId: "CT-S", type: "EMAIL", value: "stop@example.com", source: "MANUAL", status: "ACTIVE" }],
    suppression: "Do Not Contact",
  };
  bindSharedOwnersForTest({ acquisition: true, delivery: true });
  const { current, apply } = store({ [DEV_COMPANIES_UID]: JSON.stringify([company, suppressed]) });

  const noSend = apply("DEV-01-BTN-EMAIL-DISPATCH", "DEV-01-ACT-EMAIL-DISPATCH");
  assert(parseJson<{ code: string }>(noSend["DEV-01-STATE-ERROR"], { code: "" }).code === "DEV_CAMPAIGN_REQUIRED", "message stage never sends");

  apply("DEV-01-BTN-CANDIDATE-CREATE", "DEV-01-ACT-CANDIDATE-CREATE", JSON.stringify({ companyId: "CO-M" }));
  const created = parseJson<DevCandidate[]>(current(DEV_CANDIDATES_UID), [])[0];
  assert(created.status === "REVIEW", "candidate starts in review");
  assert(created.contactValue === "demo@example.com", "candidate binds email contact");

  const blockedCampaign = apply("DEV-01-BTN-CAMPAIGN-CREATE", "DEV-01-ACT-CAMPAIGN-CREATE");
  assert(parseJson<{ code: string }>(blockedCampaign["DEV-01-STATE-ERROR"], { code: "" }).code === "DEV_CAMPAIGN_CANDIDATE_REQUIRED", "campaign needs approved candidate");

  apply("DEV-01-BTN-CANDIDATE-DECIDE", "DEV-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidateId: created.candidateId }));
  assert(parseJson<DevCandidate[]>(current(DEV_CANDIDATES_UID), [])[0].status === "APPROVED", "decide approves candidate");

  apply("DEV-01-BTN-CAMPAIGN-SEARCH", "DEV-01-ACT-CAMPAIGN-SEARCH", JSON.stringify({ audienceQuery: "示範" }));
  apply("DEV-01-BTN-CAMPAIGN-CREATE", "DEV-01-ACT-CAMPAIGN-CREATE");
  const campaign = parseJson<DevCampaign | null>(current(DEV_CAMPAIGN_UID), null);
  assert(campaign?.status === "REVIEW", "campaign starts in review");
  assert(campaign?.previewed === true, "create records recipient preview");
  assert(campaign?.recipients.length === 1, "suppressed company stays out of recipients");
  assert(campaign?.candidateVersion === parseJson<DevCandidate[]>(current(DEV_CANDIDATES_UID), [])[0].version, "campaign binds exact candidate version");

  const earlyDispatch = apply("DEV-01-BTN-EMAIL-DISPATCH", "DEV-01-ACT-EMAIL-DISPATCH");
  assert(parseJson<{ code: string }>(earlyDispatch["DEV-01-STATE-ERROR"], { code: "" }).code === "DEV_DISPATCH_NOT_APPROVED", "approve stays separate from dispatch");

  apply("DEV-01-BTN-CAMPAIGN-APPROVE", "DEV-01-ACT-CAMPAIGN-APPROVE");
  assert(parseJson<DevCampaign | null>(current(DEV_CAMPAIGN_UID), null)?.status === "APPROVED", "approve moves campaign to APPROVED");

  apply("DEV-01-BTN-EMAIL-DISPATCH", "DEV-01-ACT-EMAIL-DISPATCH");
  const queued = parseJson<DevCampaign | null>(current(DEV_CAMPAIGN_UID), null);
  const deliveries = parseJson<DevDelivery[]>(current(DEV_DELIVERIES_UID), []);
  assert(queued?.status === "QUEUED", "dispatch queues approved campaign");
  assert(deliveries.length === 1, "dispatch fans out one delivery per recipient");
  assert(deliveries[0].to === "demo@example.com", "delivery To is exactly one");
  assert(deliveries[0].cc === 0 && deliveries[0].bcc === 0, "delivery forbids CC and BCC");
  assert(deliveries[0].status === "QUEUED", "dispatch queues through shared delivery owner");

  apply("DEV-01-BTN-KILL-SWITCH", "DEV-01-ACT-KILL-SWITCH", JSON.stringify({ reason: "OPERATOR_STOP" }));
  assert(parseJson<DevCampaign | null>(current(DEV_CAMPAIGN_UID), null)?.status === "STOPPED", "kill switch stops queued campaign");
  assert(parseJson<DevDelivery[]>(current(DEV_DELIVERIES_UID), [])[0].status === "STOPPED", "kill switch stops pending deliveries");
  assert(current(DEV_AUDIENCE_UID) === "示範", "audience query persists");
}

{
  bindSharedOwnersForTest({ acquisition: true, delivery: false });
  const company: DevCompany = {
    companyId: "CO-D",
    name: "示範公司",
    identityKind: "REGISTRATION",
    identityValue: "TW-222",
    aliases: [],
    contacts: [{ contactId: "CT-D", type: "EMAIL", value: "demo@example.com", source: "MANUAL", status: "ACTIVE" }],
    opportunity: { opportunityId: "OPP-D", state: "QUALIFIED" },
    suppression: "",
    evidence: "公開招標",
    mergedFrom: [],
    version: 1,
  };
  const { current, apply } = store({ [DEV_COMPANIES_UID]: JSON.stringify([company]) });
  apply("DEV-01-BTN-CANDIDATE-CREATE", "DEV-01-ACT-CANDIDATE-CREATE", JSON.stringify({ companyId: "CO-D" }));
  const candidateId = parseJson<DevCandidate[]>(current(DEV_CANDIDATES_UID), [])[0].candidateId;
  apply("DEV-01-BTN-CANDIDATE-DECIDE", "DEV-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidateId }));
  apply("DEV-01-BTN-CAMPAIGN-CREATE", "DEV-01-ACT-CAMPAIGN-CREATE");
  apply("DEV-01-BTN-CAMPAIGN-APPROVE", "DEV-01-ACT-CAMPAIGN-APPROVE");
  apply("DEV-01-BTN-EMAIL-DISPATCH", "DEV-01-ACT-EMAIL-DISPATCH");
  assert(parseJson<DevDelivery[]>(current(DEV_DELIVERIES_UID), [])[0].status === "EXTERNAL_PENDING", "missing delivery owner waits externally");
  assert(parseJson<DevCampaign | null>(current(DEV_CAMPAIGN_UID), null)?.status === "QUEUED", "campaign still queues the intent");
  bindSharedOwnersForTest(null);
}

{
  bindSharedOwnersForTest(null);
  const company: DevCompany = {
    companyId: "CO-DEFAULT",
    name: "示範公司",
    identityKind: "REGISTRATION",
    identityValue: "TW-333",
    aliases: [],
    contacts: [{ contactId: "CT-DEFAULT", type: "EMAIL", value: "demo@example.com", source: "公開資料", status: "ACTIVE" }],
    opportunity: { opportunityId: "OPP-DEFAULT", state: "QUALIFIED" },
    suppression: "",
    evidence: "公開招標",
    mergedFrom: [],
    version: 1,
  };
  const { current, apply } = store({ [DEV_COMPANIES_UID]: JSON.stringify([company]) });
  apply("DEV-01-BTN-CANDIDATE-CREATE", "DEV-01-ACT-CANDIDATE-CREATE", JSON.stringify({ companyId: "CO-DEFAULT" }));
  const candidateId = parseJson<DevCandidate[]>(current(DEV_CANDIDATES_UID), [])[0].candidateId;
  apply("DEV-01-BTN-CANDIDATE-DECIDE", "DEV-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidateId }));
  apply("DEV-01-BTN-CAMPAIGN-CREATE", "DEV-01-ACT-CAMPAIGN-CREATE");
  apply("DEV-01-BTN-CAMPAIGN-APPROVE", "DEV-01-ACT-CAMPAIGN-APPROVE");
  apply("DEV-01-BTN-EMAIL-DISPATCH", "DEV-01-ACT-EMAIL-DISPATCH");
  assert(parseJson<DevDelivery[]>(current(DEV_DELIVERIES_UID), [])[0].status === "EXTERNAL_PENDING", "production default keeps delivery external pending");
  assert(parseJson<DevDelivery[]>(current(DEV_DELIVERIES_UID), [])[0].result === "EXTERNAL_PENDING", "production default never pretends the mail left");
}

{
  bindSharedOwnersForTest({ acquisition: true, delivery: true });
  const signal: DevSignal = {
    signalId: "SIG-LOOP",
    companyName: "閉環企業",
    intent: "採購",
    evidence: "公開招標公告",
    freshness: "2026-10-23",
    identityKind: "REGISTRATION",
    identityValue: "TW-88888888",
    match: "resolved",
    opportunity: "OPEN",
    status: "NEW",
    version: 1,
  };
  const { current, apply } = store({ [DEV_SIGNALS_UID]: JSON.stringify([signal]) });
  apply(
    "DEV-01-BTN-PROFILE-SAVE",
    "DEV-01-ACT-PROFILE-SAVE",
    JSON.stringify({ product: "影像工作臺", industry: "媒體", keywords: "企業開發", mode: "SINGLE" }),
  );
  apply("DEV-01-BTN-DISCOVERY-START", "DEV-01-ACT-DISCOVERY-START");
  assert(parseJson<DevJob | null>(current(DEV_JOB_UID), null)?.status === "RUNNING", "loop start binds acquisition");
  apply("DEV-01-BTN-SIGNAL-QUALIFY", "DEV-01-ACT-SIGNAL-QUALIFY", JSON.stringify({ signalId: "SIG-LOOP" }));
  const companyId = parseJson<DevCompany[]>(current(DEV_COMPANIES_UID), [])[0].companyId;
  apply(
    "DEV-01-BTN-CONTACT-UPSERT",
    "DEV-01-ACT-CONTACT-UPSERT",
    JSON.stringify({ companyId, contactType: "EMAIL", contactValue: "loop@example.com", contactSource: "MANUAL" }),
  );
  apply("DEV-01-BTN-CANDIDATE-CREATE", "DEV-01-ACT-CANDIDATE-CREATE", JSON.stringify({ companyId }));
  const loopCandidate = parseJson<DevCandidate[]>(current(DEV_CANDIDATES_UID), [])[0];
  apply("DEV-01-BTN-CANDIDATE-DECIDE", "DEV-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ candidateId: loopCandidate.candidateId }));
  apply("DEV-01-BTN-CAMPAIGN-CREATE", "DEV-01-ACT-CAMPAIGN-CREATE");
  apply("DEV-01-BTN-CAMPAIGN-APPROVE", "DEV-01-ACT-CAMPAIGN-APPROVE");
  apply("DEV-01-BTN-EMAIL-DISPATCH", "DEV-01-ACT-EMAIL-DISPATCH");
  assert(parseJson<DevCampaign | null>(current(DEV_CAMPAIGN_UID), null)?.status === "QUEUED", "loop dispatch queues campaign");
  assert(parseJson<DevDelivery[]>(current(DEV_DELIVERIES_UID), [])[0].to === "loop@example.com", "loop delivery keeps one To");
  apply("DEV-01-BTN-KILL-SWITCH", "DEV-01-ACT-KILL-SWITCH", JSON.stringify({ reason: "OPERATOR_STOP" }));
  assert(parseJson<DevCampaign | null>(current(DEV_CAMPAIGN_UID), null)?.status === "STOPPED", "loop kill stops campaign");
  assert(parseJson<DevDelivery[]>(current(DEV_DELIVERIES_UID), [])[0].status === "STOPPED", "loop kill stops delivery");
  bindSharedOwnersForTest(null);
}

{
  bindSharedOwnersForTest({ acquisition: true, delivery: true });
  const { current, apply } = store();
  apply(
    "DEV-01-BTN-PROFILE-SAVE",
    "DEV-01-ACT-PROFILE-SAVE",
    JSON.stringify({
      product: "影像工作臺",
      industry: "媒體",
      keywords: "企業開發",
      language: "en",
      priority: "HIGH",
      sourceScope: "ALLOWED",
      mode: "SINGLE",
    }),
  );
  const profile = parseJson<DevProfile | null>(current(DEV_PROFILE_UID), null);
  assert(profile?.language === "en", "profile language persists");
  assert(profile?.priority === "HIGH", "profile priority persists");
  assert(profile?.sourceScope === "ALLOWED", "profile source scope persists");
  bindSharedOwnersForTest(null);
}

{
  const { current } = store({
    [DEV_PROFILE_UID]: JSON.stringify({
      profileId: "PRF-LEGACY",
      version: 3,
      product: "影像工作臺",
      industry: "媒體",
      market: "",
      keywords: "企業開發",
      exclude: "",
      mode: "SINGLE",
      status: "DRAFT",
    }),
  });
  const legacy = readDevWorkbench(current).profile;
  assert(legacy?.language === "zh-TW", "legacy profile fills language");
  assert(legacy?.priority === "NORMAL", "legacy profile fills priority");
  assert(legacy?.sourceScope === "ALLOWED", "legacy profile fills source scope");
}

console.log("devActionPreview.test.ts PASS");
