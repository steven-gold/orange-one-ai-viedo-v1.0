import { previewSocAction } from "./socActionPreview";
import { bindSocialAdapterForTest } from "./socSharedOwners";
import { SOC_VISIBLE_CONTROLS } from "../server/domain/soc";
import {
  SOC_ACCOUNTS_UID,
  SOC_DISCOVERY_UID,
  SOC_ERROR_UID,
  SOC_KILL_UID,
  SOC_PACKAGE_UID,
  SOC_PLATFORMS_UID,
  SOC_POLICY_UID,
  SOC_QUERY_UID,
  SOC_RECORD_QUERY_UID,
  SOC_REQUESTS_UID,
  SOC_REVEAL_UID,
  SOC_TARGETS_UID,
  parseJson,
  type SocAccount,
  type SocDiscovery,
  type SocKillState,
  type SocPackage,
  type SocPlatform,
  type SocPolicy,
  type SocRequest,
  type SocTarget,
} from "./socState";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
}

{
  assert(SOC_VISIBLE_CONTROLS.length === 26, "SOC stays at 26 visible controls");
  assert(SOC_VISIBLE_CONTROLS.includes("SOC-01-BTN-PUBLISH"), "publish remains a visible control");
  assert(SOC_VISIBLE_CONTROLS.includes("SOC-01-BTN-TARGET-CREATE"), "manual target create is visible");
  assert(SOC_VISIBLE_CONTROLS.includes("SOC-01-BTN-DISCOVERY-STOP"), "discovery stop is visible");
  assert(SOC_VISIBLE_CONTROLS.includes("SOC-01-BTN-RECORD-REPORT"), "record report is visible");
  assert(SOC_VISIBLE_CONTROLS.includes("SOC-01-BTN-TARGET-EXPORT"), "target export is visible");
  assert(SOC_VISIBLE_CONTROLS.includes("SOC-01-BTN-RECORD-EXPORT"), "record export is visible");
}

function store(seed: Record<string, string> = {}): {
  current: (uid: string) => string | null;
  apply: (controlUid: string, actionUid: string, nextValue?: string) => Record<string, string>;
} {
  const values = new Map<string, string>(Object.entries(seed));
  const current = (uid: string) => values.get(uid) ?? null;
  const apply = (controlUid: string, actionUid: string, nextValue?: string) => {
    const patch = previewSocAction(controlUid, actionUid, current, nextValue);
    for (const [uid, value] of Object.entries(patch)) values.set(uid, value);
    return patch;
  };
  return { current, apply };
}

const PLATFORM = {
  platformKey: "linkedin",
  displayName: "LinkedIn",
  enable: "ENABLED",
};

function seedReady(apply: (controlUid: string, actionUid: string, nextValue?: string) => Record<string, string>): void {
  apply("SOC-01-BTN-PLATFORM-CONFIG", "SOC-01-ACT-PLATFORM-CONFIG", JSON.stringify(PLATFORM));
  apply(
    "SOC-01-BTN-ACCOUNT-BIND",
    "SOC-01-ACT-ACCOUNT-BIND",
    JSON.stringify({
      platformKey: "linkedin",
      displayName: "營運帳號",
      loginIdentifier: "ops@example.com",
      authMode: "TOKEN",
      credentialValue: "secret-token-001",
    }),
  );
}

{
  bindSocialAdapterForTest(null);
  const { current, apply } = store();
  const incomplete = apply("SOC-01-BTN-PLATFORM-CONFIG", "SOC-01-ACT-PLATFORM-CONFIG", JSON.stringify({ platformKey: "" }));
  assert(parseJson<{ code: string }>(incomplete[SOC_ERROR_UID], { code: "" }).code === "SOC_PLATFORM_REQUIRED", "empty platform is rejected");

  apply("SOC-01-BTN-PLATFORM-CONFIG", "SOC-01-ACT-PLATFORM-CONFIG", JSON.stringify(PLATFORM));
  const platform = parseJson<SocPlatform[]>(current(SOC_PLATFORMS_UID), [])[0];
  assert(platform?.platformKey === "linkedin", "registered platform persists");
  assert(platform?.health === "UNKNOWN", "health is never guessed");
  assert(platform?.capability === "REGISTERED", "capability stays registered only");

  const bindFail = apply(
    "SOC-01-BTN-ACCOUNT-BIND",
    "SOC-01-ACT-ACCOUNT-BIND",
    JSON.stringify({ platformKey: "linkedin", displayName: "營運帳號" }),
  );
  assert(parseJson<{ code: string }>(bindFail[SOC_ERROR_UID], { code: "" }).code === "SOC_ACCOUNT_BIND_REQUIRED", "bind requires exact fields");

  apply(
    "SOC-01-BTN-ACCOUNT-BIND",
    "SOC-01-ACT-ACCOUNT-BIND",
    JSON.stringify({
      platformKey: "linkedin",
      displayName: "營運帳號",
      loginIdentifier: "ops@example.com",
      authMode: "TOKEN",
      credentialValue: "secret-token-001",
    }),
  );
  const account = parseJson<SocAccount[]>(current(SOC_ACCOUNTS_UID), [])[0];
  assert(account?.binding === "BOUND_LOCKED", "bind locks the account");
  assert(account?.credentialStatus === "SET", "credential status is set");
  assert(!JSON.stringify(account).includes("secret-token-001"), "raw secret never enters projection");
  assert(account?.credentialMasked.includes("••••"), "credential stays masked");

  const revealFail = apply(
    "SOC-01-BTN-CREDENTIAL-REVEAL",
    "SOC-01-ACT-CREDENTIAL-REVEAL",
    JSON.stringify({ accountId: account.accountId }),
  );
  assert(parseJson<{ code: string }>(revealFail[SOC_ERROR_UID], { code: "" }).code === "SOC_REVEAL_REASON_REQUIRED", "reveal needs a reason");

  apply(
    "SOC-01-BTN-CREDENTIAL-REVEAL",
    "SOC-01-ACT-CREDENTIAL-REVEAL",
    JSON.stringify({ accountId: account.accountId, reason: "審計核對" }),
  );
  assert(parseJson<{ accountId: string }>(current(SOC_REVEAL_UID), { accountId: "" }).accountId === account.accountId, "reveal is audited");
  assert(!JSON.stringify(parseJson<SocAccount[]>(current(SOC_ACCOUNTS_UID), [])).includes("secret-token-001"), "reveal still never stores raw secret");
}

{
  bindSocialAdapterForTest(null);
  const { current, apply } = store();
  seedReady(apply);
  const missing = apply(
    "SOC-01-BTN-TARGET-DISCOVERY",
    "SOC-01-ACT-TARGET-DISCOVERY",
    JSON.stringify({ platformKey: "linkedin", keywords: "媒體" }),
  );
  assert(parseJson<{ code: string }>(missing[SOC_ERROR_UID], { code: "" }).code === "SOC_DISCOVERY_REQUIRED", "discovery requires exact fields");

  apply(
    "SOC-01-BTN-TARGET-DISCOVERY",
    "SOC-01-ACT-TARGET-DISCOVERY",
    JSON.stringify({
      jobName: "媒體社團",
      platformKey: "linkedin",
      targetTypes: "GROUP",
      categories: "媒體",
      keywords: "影像工作臺",
      mode: "SINGLE_RUN",
    }),
  );
  const discovery = parseJson<SocDiscovery | null>(current(SOC_DISCOVERY_UID), null);
  assert(discovery?.status === "EXTERNAL_PENDING", "missing adapter waits externally");
  assert(discovery?.blocker === "SHARED_ADAPTER_UNAVAILABLE", "missing adapter is blocked not faked");
  assert(parseJson<SocTarget[]>(current(SOC_TARGETS_UID), []).length === 0, "blocked discovery never invents targets");
}

{
  bindSocialAdapterForTest(true);
  const { current, apply } = store();
  seedReady(apply);
  apply(
    "SOC-01-BTN-TARGET-DISCOVERY",
    "SOC-01-ACT-TARGET-DISCOVERY",
    JSON.stringify({
      jobName: "媒體社團",
      platformKey: "linkedin",
      targetTypes: "GROUP",
      categories: "媒體",
      keywords: "影像工作臺",
      mode: "CONTINUOUS",
    }),
  );
  const discovery = parseJson<SocDiscovery | null>(current(SOC_DISCOVERY_UID), null);
  assert(discovery?.status === "RUNNING", "available adapter starts discovery");
  assert(discovery?.blocker === "", "available adapter has no blocker");
  assert(parseJson<SocTarget[]>(current(SOC_TARGETS_UID), []).length === 0, "start never invents targets");
  bindSocialAdapterForTest(null);
}

{
  bindSocialAdapterForTest(null);
  const target: SocTarget = {
    targetId: "TGT-1",
    platformKey: "linkedin",
    name: "媒體社團",
    targetType: "GROUP",
    capability: "GOVERNED",
    status: "READY_TO_JOIN",
    signal: "公開社團",
    evidence: "目錄投影",
    version: 1,
  };
  const { current, apply } = store({ [SOC_TARGETS_UID]: JSON.stringify([target]) });
  seedReady(apply);
  apply("SOC-01-BTN-TARGET-JOIN", "SOC-01-ACT-TARGET-JOIN", JSON.stringify({ targetId: "TGT-1" }));
  assert(parseJson<SocTarget[]>(current(SOC_TARGETS_UID), [])[0].status === "JOINED", "join moves READY_TO_JOIN to JOINED");

  const illegal = apply("SOC-01-BTN-TARGET-JOIN", "SOC-01-ACT-TARGET-JOIN", JSON.stringify({ targetId: "TGT-1" }));
  assert(parseJson<{ code: string }>(illegal[SOC_ERROR_UID], { code: "" }).code === "SOC_TARGET_JOIN_ILLEGAL", "joined target cannot join again");

  const manualTarget: SocTarget = { ...target, targetId: "TGT-2", status: "MANUAL_ACTION_REQUIRED" };
  const store2 = store({
    [SOC_PLATFORMS_UID]: current(SOC_PLATFORMS_UID) ?? "",
    [SOC_ACCOUNTS_UID]: current(SOC_ACCOUNTS_UID) ?? "",
    [SOC_TARGETS_UID]: JSON.stringify([manualTarget]),
  });
  store2.apply("SOC-01-BTN-MANUAL-COMPLETE", "SOC-01-ACT-MANUAL-COMPLETE", JSON.stringify({ targetId: "TGT-2" }));
  assert(parseJson<SocTarget[]>(store2.current(SOC_TARGETS_UID), [])[0].status === "JOINED", "manual complete only from pending");
}

{
  bindSocialAdapterForTest(null);
  const { current, apply } = store();
  seedReady(apply);
  const empty = apply("SOC-01-BTN-CONTENT-SAVE", "SOC-01-ACT-CONTENT-SAVE", JSON.stringify({ releaseSource: "" }));
  assert(parseJson<{ code: string }>(empty[SOC_ERROR_UID], { code: "" }).code === "SOC_CONTENT_REQUIRED", "draft needs exact source and variant");

  apply(
    "SOC-01-BTN-CONTENT-SAVE",
    "SOC-01-ACT-CONTENT-SAVE",
    JSON.stringify({ releaseSource: "REL-001", platformKey: "linkedin", variant: "職涯貼文" }),
  );
  const draft = parseJson<SocPackage | null>(current(SOC_PACKAGE_UID), null);
  assert(draft?.candidate === "REVIEW", "save draft enters review");
  assert(draft?.hash.startsWith("pkg-"), "draft seals a hash");
  assert(draft?.policyCheck === "PASS", "saved draft records policy check");

  apply("SOC-01-BTN-CANDIDATE-DECIDE", "SOC-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ packageId: draft?.packageId, decision: "APPROVE" }));
  const approved = parseJson<SocPackage | null>(current(SOC_PACKAGE_UID), null);
  assert(approved?.candidate === "APPROVED", "approve seals the candidate");
  assert(approved?.hash === draft?.hash, "approve keeps the exact hash");
  assert(parseJson<SocRequest[]>(current(SOC_REQUESTS_UID), []).length === 0, "approve never creates a publish request");

  const again = apply("SOC-01-BTN-CANDIDATE-DECIDE", "SOC-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ packageId: approved?.packageId, decision: "APPROVE" }));
  assert(parseJson<{ code: string }>(again[SOC_ERROR_UID], { code: "" }).code === "SOC_CANDIDATE_NOT_REVIEW", "approved candidate cannot be decided again");
}

{
  bindSocialAdapterForTest(null);
  const target: SocTarget = {
    targetId: "TGT-READY",
    platformKey: "linkedin",
    name: "媒體社團",
    targetType: "GROUP",
    capability: "GOVERNED",
    status: "JOINED",
    signal: "公開社團",
    evidence: "目錄投影",
    version: 2,
  };
  const { current, apply } = store({ [SOC_TARGETS_UID]: JSON.stringify([target]) });
  seedReady(apply);
  apply(
    "SOC-01-BTN-CONTENT-SAVE",
    "SOC-01-ACT-CONTENT-SAVE",
    JSON.stringify({ releaseSource: "REL-001", platformKey: "linkedin", variant: "職涯貼文" }),
  );
  const pkg = parseJson<SocPackage | null>(current(SOC_PACKAGE_UID), null);
  apply("SOC-01-BTN-CANDIDATE-DECIDE", "SOC-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ packageId: pkg?.packageId, decision: "APPROVE" }));

  const noPolicy = apply("SOC-01-BTN-PUBLISH", "SOC-01-ACT-PUBLISH-REQUEST", JSON.stringify({ targetId: "TGT-READY" }));
  assert(parseJson<{ code: string }>(noPolicy[SOC_ERROR_UID], { code: "" }).code === "SOC_POLICY_REQUIRED", "publish needs target policy");

  apply(
    "SOC-01-BTN-POLICY-CONFIG",
    "SOC-01-ACT-POLICY-CONFIG",
    JSON.stringify({ targetId: "TGT-READY", minIntervalHours: 24, dailyLimit: 1, weeklyLimit: 3 }),
  );
  const policy = parseJson<SocPolicy | null>(current(SOC_POLICY_UID), null);
  assert(policy?.minIntervalHours === 24, "policy persists exact interval");

  apply("SOC-01-BTN-PUBLISH", "SOC-01-ACT-PUBLISH-REQUEST", JSON.stringify({ targetId: "TGT-READY" }));
  const request = parseJson<SocRequest[]>(current(SOC_REQUESTS_UID), [])[0];
  assert(request?.status === "PENDING_EXTERNAL", "publish request stays locally accepted");
  assert(request?.external === "PENDING_EXTERNAL", "external state is never POSTED without adapter callback");
  assert(request?.callback === "SHARED_ADAPTER_UNAVAILABLE", "missing adapter is recorded honestly");
  assert(parseJson<SocTarget[]>(current(SOC_TARGETS_UID), [])[0].status === "PENDING_EXTERNAL", "target moves to pending external");
  assert(request?.external !== "POSTED", "production default never pretends the post left");

  const duplicate = apply("SOC-01-BTN-PUBLISH", "SOC-01-ACT-PUBLISH-REQUEST", JSON.stringify({ targetId: "TGT-READY" }));
  assert(parseJson<{ code: string }>(duplicate[SOC_ERROR_UID], { code: "" }).code === "SOC_PUBLISH_DUPLICATE", "idempotent pending request is blocked");
}

{
  bindSocialAdapterForTest(true);
  const target: SocTarget = {
    targetId: "TGT-ADAPTER",
    platformKey: "linkedin",
    name: "媒體社團",
    targetType: "GROUP",
    capability: "GOVERNED",
    status: "READY_TO_POST",
    signal: "公開社團",
    evidence: "目錄投影",
    version: 3,
  };
  const { current, apply } = store({ [SOC_TARGETS_UID]: JSON.stringify([target]) });
  seedReady(apply);
  apply(
    "SOC-01-BTN-CONTENT-SAVE",
    "SOC-01-ACT-CONTENT-SAVE",
    JSON.stringify({ releaseSource: "REL-002", platformKey: "linkedin", variant: "原生貼文" }),
  );
  const pkg = parseJson<SocPackage | null>(current(SOC_PACKAGE_UID), null);
  apply("SOC-01-BTN-CANDIDATE-DECIDE", "SOC-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ packageId: pkg?.packageId, decision: "APPROVE" }));
  apply(
    "SOC-01-BTN-POLICY-CONFIG",
    "SOC-01-ACT-POLICY-CONFIG",
    JSON.stringify({ targetId: "TGT-ADAPTER", minIntervalHours: 12, dailyLimit: 2, weeklyLimit: 6 }),
  );
  apply("SOC-01-BTN-PUBLISH", "SOC-01-ACT-PUBLISH-REQUEST", JSON.stringify({ targetId: "TGT-ADAPTER" }));
  const request = parseJson<SocRequest[]>(current(SOC_REQUESTS_UID), [])[0];
  assert(request?.status === "PENDING_EXTERNAL", "adapter acceptance still stays pending external");
  assert(request?.external === "PENDING_EXTERNAL", "available adapter still never marks POSTED");
  assert(request?.callback === "ADAPTER_ACCEPTED", "available adapter records acceptance only");
  bindSocialAdapterForTest(null);
}

{
  bindSocialAdapterForTest(null);
  const { apply } = store();
  const idleKill = apply("SOC-01-BTN-KILL", "SOC-01-ACT-KILL-SWITCH");
  assert(parseJson<{ code: string }>(idleKill[SOC_ERROR_UID], { code: "" }).code === "SOC_KILL_NOT_APPLICABLE", "kill stays off when nothing is high-risk");
}

{
  bindSocialAdapterForTest(null);
  const target: SocTarget = {
    targetId: "TGT-KILL",
    platformKey: "linkedin",
    name: "媒體社團",
    targetType: "GROUP",
    capability: "GOVERNED",
    status: "JOINED",
    signal: "公開社團",
    evidence: "目錄投影",
    version: 1,
  };
  const { current, apply } = store({ [SOC_TARGETS_UID]: JSON.stringify([target]) });
  seedReady(apply);
  apply(
    "SOC-01-BTN-CONTENT-SAVE",
    "SOC-01-ACT-CONTENT-SAVE",
    JSON.stringify({ releaseSource: "REL-KILL", platformKey: "linkedin", variant: "原生貼文" }),
  );
  const pkg = parseJson<SocPackage | null>(current(SOC_PACKAGE_UID), null);
  apply("SOC-01-BTN-CANDIDATE-DECIDE", "SOC-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ packageId: pkg?.packageId, decision: "APPROVE" }));
  apply(
    "SOC-01-BTN-POLICY-CONFIG",
    "SOC-01-ACT-POLICY-CONFIG",
    JSON.stringify({ targetId: "TGT-KILL", minIntervalHours: 24, dailyLimit: 1, weeklyLimit: 3 }),
  );
  apply("SOC-01-BTN-PUBLISH", "SOC-01-ACT-PUBLISH-REQUEST", JSON.stringify({ targetId: "TGT-KILL" }));
  apply("SOC-01-BTN-KILL", "SOC-01-ACT-KILL-SWITCH", JSON.stringify({ reason: "OPERATOR_STOP" }));
  assert(parseJson<SocKillState | null>(current(SOC_KILL_UID), null)?.active === true, "kill records high-risk stop");
  assert(parseJson<SocRequest[]>(current(SOC_REQUESTS_UID), [])[0].status === "STOPPED", "kill stops pending request");
  const afterKill = apply("SOC-01-BTN-PUBLISH", "SOC-01-ACT-PUBLISH-REQUEST", JSON.stringify({ targetId: "TGT-KILL" }));
  assert(parseJson<{ code: string }>(afterKill[SOC_ERROR_UID], { code: "" }).code === "SOC_KILL_ACTIVE", "kill blocks further publish");
}

{
  bindSocialAdapterForTest(null);
  const { current, apply } = store();
  apply("SOC-01-INP-TARGET-SEARCH", "SOC-01-ACT-SEARCH", JSON.stringify({ query: "媒體" }));
  assert(current(SOC_QUERY_UID) === "媒體", "target search persists query");
  apply("SOC-01-INP-RECORD-SEARCH", "SOC-01-ACT-SEARCH", JSON.stringify({ query: "REQ-1" }));
  assert(current(SOC_RECORD_QUERY_UID) === "REQ-1", "record search persists separately");
  apply("SOC-01-BTN-UNBIND-PLACEHOLDER", "SOC-01-ACT-ACCOUNT-UNBIND", JSON.stringify({ accountId: "missing" }));
  assert(parseJson<{ code: string }>(current(SOC_ERROR_UID), { code: "" }).code === "SOC_ACCOUNT_REQUIRED", "unbind needs an exact account");
}

{
  bindSocialAdapterForTest(null);
  const { current, apply } = store();
  seedReady(apply);
  const accountId = parseJson<SocAccount[]>(current(SOC_ACCOUNTS_UID), [])[0].accountId;
  apply("SOC-01-BTN-ACCOUNT-UNBIND", "SOC-01-ACT-ACCOUNT-UNBIND", JSON.stringify({ accountId }));
  const unbound = parseJson<SocAccount[]>(current(SOC_ACCOUNTS_UID), [])[0];
  assert(unbound.binding === "UNBOUND", "unbind clears binding");
  assert(unbound.credentialStatus === "NOT_SET", "unbind clears credential status");
  assert(unbound.credentialMasked === "", "unbind drops masked secret");
}

{
  bindSocialAdapterForTest(null);
  const { current, apply } = store();
  seedReady(apply);
  const stopIdle = apply("SOC-01-BTN-DISCOVERY-STOP", "SOC-01-ACT-DISCOVERY-STOP", JSON.stringify({ reason: "OPERATOR_STOP" }));
  assert(parseJson<{ code: string }>(stopIdle[SOC_ERROR_UID], { code: "" }).code === "SOC_DISCOVERY_NOT_ACTIVE", "stop without job is rejected");

  apply(
    "SOC-01-BTN-TARGET-DISCOVERY",
    "SOC-01-ACT-TARGET-DISCOVERY",
    JSON.stringify({ jobName: "媒體社團", platformKey: "linkedin", targetTypes: "GROUP", categories: "媒體", keywords: "影像工作臺", mode: "SINGLE_RUN" }),
  );
  apply("SOC-01-BTN-DISCOVERY-STOP", "SOC-01-ACT-DISCOVERY-STOP", JSON.stringify({ reason: "OPERATOR_STOP" }));
  const stopped = parseJson<SocDiscovery | null>(current(SOC_DISCOVERY_UID), null);
  assert(stopped?.status === "STOPPED", "operator can stop a pending discovery");
  assert(stopped?.blocker === "OPERATOR_STOP", "stop reason is recorded honestly");
}

{
  bindSocialAdapterForTest(null);
  const { current, apply } = store();
  seedReady(apply);
  const missing = apply("SOC-01-BTN-TARGET-CREATE", "SOC-01-ACT-TARGET-CREATE", JSON.stringify({ platformKey: "linkedin" }));
  assert(parseJson<{ code: string }>(missing[SOC_ERROR_UID], { code: "" }).code === "SOC_TARGET_CREATE_REQUIRED", "manual target needs name and type");

  apply("SOC-01-BTN-TARGET-CREATE", "SOC-01-ACT-TARGET-CREATE", JSON.stringify({ platformKey: "linkedin", name: "攝影後製社", targetType: "GROUP" }));
  const targets = parseJson<SocTarget[]>(current(SOC_TARGETS_UID), []);
  assert(targets[0]?.status === "DISCOVERED", "manual target enters as discovered");
  assert(targets[0]?.signal === "人工新增", "manual target records its signal honestly");
  assert(targets[0]?.targetId.startsWith("TGT-"), "manual target gets an id");

  const duplicate = apply("SOC-01-BTN-TARGET-CREATE", "SOC-01-ACT-TARGET-CREATE", JSON.stringify({ platformKey: "linkedin", name: "攝影後製社", targetType: "GROUP" }));
  assert(parseJson<{ code: string }>(duplicate[SOC_ERROR_UID], { code: "" }).code === "SOC_TARGET_DUPLICATE", "duplicate manual target is blocked");
}

{
  bindSocialAdapterForTest(null);
  const target: SocTarget = {
    targetId: "TGT-REPORT",
    platformKey: "linkedin",
    name: "媒體社團",
    targetType: "GROUP",
    capability: "GOVERNED",
    status: "JOINED",
    signal: "公開社團",
    evidence: "目錄投影",
    version: 1,
  };
  const { current, apply } = store({ [SOC_TARGETS_UID]: JSON.stringify([target]) });
  seedReady(apply);
  apply("SOC-01-BTN-CONTENT-SAVE", "SOC-01-ACT-CONTENT-SAVE", JSON.stringify({ releaseSource: "REL-RPT", platformKey: "linkedin", variant: "原生貼文" }));
  const pkg = parseJson<SocPackage | null>(current(SOC_PACKAGE_UID), null);
  apply("SOC-01-BTN-CANDIDATE-DECIDE", "SOC-01-ACT-CANDIDATE-DECIDE", JSON.stringify({ packageId: pkg?.packageId, decision: "APPROVE" }));
  apply("SOC-01-BTN-POLICY-CONFIG", "SOC-01-ACT-POLICY-CONFIG", JSON.stringify({ targetId: "TGT-REPORT", minIntervalHours: 24, dailyLimit: 1, weeklyLimit: 3 }));
  apply("SOC-01-BTN-PUBLISH", "SOC-01-ACT-PUBLISH-REQUEST", JSON.stringify({ targetId: "TGT-REPORT" }));
  const requestId = parseJson<SocRequest[]>(current(SOC_REQUESTS_UID), [])[0].requestId;

  const noFields = apply("SOC-01-BTN-RECORD-REPORT", "SOC-01-ACT-RECORD-REPORT", JSON.stringify({ requestId }));
  assert(parseJson<{ code: string }>(noFields[SOC_ERROR_UID], { code: "" }).code === "SOC_REPORT_REQUIRED", "report requires metrics and interaction");

  apply("SOC-01-BTN-RECORD-REPORT", "SOC-01-ACT-RECORD-REPORT", JSON.stringify({ requestId, metrics: "48 views", interaction: "3 comments" }));
  const reported = parseJson<SocRequest[]>(current(SOC_REQUESTS_UID), [])[0];
  assert(reported?.status === "POSTED", "operator report marks the request POSTED");
  assert(reported?.external === "POSTED", "reported request records external POSTED");
  assert(reported?.callback === "OPERATOR_REPORT", "operator report is recorded as the callback");
  assert(reported?.metrics === "48 views" && reported?.interaction === "3 comments", "report persists exact metrics and interaction");
  assert(parseJson<SocTarget[]>(current(SOC_TARGETS_UID), [])[0].status === "POSTED", "target moves to POSTED with the request");
}

{
  bindSocialAdapterForTest(null);
  const target: SocTarget = {
    targetId: "TGT-MANUAL",
    platformKey: "linkedin",
    name: "媒體社團",
    targetType: "GROUP",
    capability: "GOVERNED",
    status: "PENDING_EXTERNAL",
    signal: "公開社團",
    evidence: "目錄投影",
    version: 1,
  };
  const request: SocRequest = {
    requestId: "REQ-MANUAL",
    targetId: "TGT-MANUAL",
    accountId: "ACC-1",
    packageId: "PKG-1",
    packageVersion: 1,
    packageHash: "pkg-test",
    status: "PENDING_EXTERNAL",
    external: "PENDING_EXTERNAL",
    callback: "SHARED_ADAPTER_UNAVAILABLE",
    version: 1,
    metrics: "",
    interaction: "",
    incident: "",
    idempotencyKey: "idem-manual-1",
    createdAt: "2026-10-27T00:00:00.000Z",
  };
  const { current, apply } = store({
    [SOC_TARGETS_UID]: JSON.stringify([target]),
    [SOC_REQUESTS_UID]: JSON.stringify([request]),
  });
  seedReady(apply);
  apply("SOC-01-BTN-MANUAL-COMPLETE", "SOC-01-ACT-MANUAL-COMPLETE", JSON.stringify({ targetId: "TGT-MANUAL" }));
  assert(parseJson<SocTarget[]>(current(SOC_TARGETS_UID), [])[0].status === "POSTED", "manual completion from pending external posts the target");
  const req = parseJson<SocRequest[]>(current(SOC_REQUESTS_UID), [])[0];
  assert(req?.status === "POSTED" && req?.callback === "OPERATOR_COMPLETED", "manual completion marks the request POSTED with operator callback");
}

console.log("socActionPreview.test.ts PASS");
