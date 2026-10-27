import { acceptSocialDiscoveryIntent, acceptSocialPublishIntent, probeSocialAdapter } from "./socSharedOwners";
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
  boundAccountForPlatform,
  highRiskActive,
  newUid,
  nowIso,
  packageApproved,
  packageHash,
  parseSocPayload,
  platformEnabled,
  readSocWorkbench,
  targetReadyToPost,
  usable,
  type SocAccount,
  type SocCandidateDecision,
  type SocDiscovery,
  type SocDiscoveryMode,
  type SocEnableState,
  type SocKillState,
  type SocPackage,
  type SocPlatform,
  type SocPolicy,
  type SocRequest,
  type SocTarget,
  type SocWorkbench,
} from "./socState";

function serialize(value: unknown): string {
  return JSON.stringify(value);
}

function patchFrom(workbench: SocWorkbench, extra: Record<string, string> = {}): Record<string, string> {
  return {
    [SOC_PLATFORMS_UID]: serialize(workbench.platforms),
    [SOC_ACCOUNTS_UID]: serialize(workbench.accounts),
    [SOC_DISCOVERY_UID]: workbench.discovery ? serialize(workbench.discovery) : "",
    [SOC_TARGETS_UID]: serialize(workbench.targets),
    [SOC_PACKAGE_UID]: workbench.content ? serialize(workbench.content) : "",
    [SOC_POLICY_UID]: workbench.policy ? serialize(workbench.policy) : "",
    [SOC_REQUESTS_UID]: serialize(workbench.requests),
    [SOC_QUERY_UID]: workbench.query,
    [SOC_RECORD_QUERY_UID]: workbench.recordQuery,
    [SOC_ERROR_UID]: workbench.error ? serialize(workbench.error) : "",
    [SOC_KILL_UID]: workbench.kill ? serialize(workbench.kill) : "",
    [SOC_REVEAL_UID]: workbench.reveal ? serialize(workbench.reveal) : "",
    ...extra,
  };
}

function fail(workbench: SocWorkbench, code: string): Record<string, string> {
  return patchFrom({ ...workbench, error: { code, at: nowIso() } });
}

function clearError(workbench: SocWorkbench): SocWorkbench {
  return { ...workbench, error: null };
}

function enableFrom(raw: string | undefined, fallback: SocEnableState): SocEnableState {
  return raw === "DISABLED" ? "DISABLED" : raw === "ENABLED" ? "ENABLED" : fallback;
}

function modeFrom(raw: string | undefined, fallback: SocDiscoveryMode): SocDiscoveryMode {
  return raw === "CONTINUOUS" || raw === "SINGLE_RUN" ? raw : fallback;
}

function decisionFrom(raw: string | undefined): SocCandidateDecision | null {
  if (raw === "APPROVE" || raw === "REJECT" || raw === "RETURN") return raw;
  return null;
}

function positiveInt(raw: number | string | undefined, fallback: number): number {
  const value = typeof raw === "number" ? raw : Number(raw);
  if (!Number.isFinite(value) || value <= 0) return fallback;
  return Math.floor(value);
}

function replacePlatform(platforms: SocPlatform[], next: SocPlatform): SocPlatform[] {
  return platforms.some((item) => item.platformKey === next.platformKey)
    ? platforms.map((item) => (item.platformKey === next.platformKey ? next : item))
    : [...platforms, next];
}

function replaceAccount(accounts: SocAccount[], next: SocAccount): SocAccount[] {
  return accounts.some((item) => item.accountId === next.accountId)
    ? accounts.map((item) => (item.accountId === next.accountId ? next : item))
    : [...accounts, next];
}

function replaceTarget(targets: SocTarget[], next: SocTarget): SocTarget[] {
  return targets.map((item) => (item.targetId === next.targetId ? next : item));
}

function replaceRequest(requests: SocRequest[], next: SocRequest): SocRequest[] {
  return requests.map((item) => (item.requestId === next.requestId ? next : item));
}

function maskSecret(value: string): string {
  const text = value.trim();
  if (!text) return "";
  if (text.length <= 4) return "••••";
  return `${text.slice(0, 2)}••••${text.slice(-2)}`;
}

function discoveryReady(payload: {
  platformKey: string;
  targetTypes: string;
  categories: string;
  keywords: string;
}): boolean {
  return Boolean(payload.platformKey && payload.targetTypes && payload.categories && payload.keywords);
}

export function previewSocAction(
  controlUid: string,
  actionUid: string,
  current: (uid: string) => string | null,
  nextValue?: string,
): Record<string, string> {
  const workbench = readSocWorkbench(current);
  const payload = parseSocPayload(nextValue);

  if (actionUid.startsWith("SOC-01-ACT-STAGE-")) {
    return patchFrom(clearError(workbench));
  }

  if (actionUid === "SOC-01-ACT-PLATFORM-CONFIG") {
    const platformKey = usable(payload.platformKey);
    const displayName = usable(payload.displayName);
    if (!platformKey || !displayName) return fail(workbench, "SOC_PLATFORM_REQUIRED");
    const prior = workbench.platforms.find((item) => item.platformKey === platformKey);
    const next: SocPlatform = {
      platformKey,
      displayName,
      capability: usable(prior?.capability) || "REGISTERED",
      policy: usable(prior?.policy) || "GOVERNED",
      health: usable(prior?.health) || "UNKNOWN",
      enable: enableFrom(payload.enable, prior?.enable ?? "ENABLED"),
      version: (prior?.version ?? 0) + 1,
    };
    return patchFrom(clearError({ ...workbench, platforms: replacePlatform(workbench.platforms, next) }));
  }

  if (actionUid === "SOC-01-ACT-KILL-SWITCH") {
    if (!highRiskActive(workbench)) return fail(workbench, "SOC_KILL_NOT_APPLICABLE");
    const reason = usable(payload.reason) || "OPERATOR_STOP";
    const kill: SocKillState = { active: true, reason, at: nowIso() };
    const requests = workbench.requests.map((item) =>
      item.status === "PENDING_EXTERNAL"
        ? { ...item, status: "STOPPED" as const, external: "STOPPED", callback: reason, version: item.version + 1 }
        : item,
    );
    const discovery =
      workbench.discovery && (workbench.discovery.status === "RUNNING" || workbench.discovery.status === "EXTERNAL_PENDING")
        ? { ...workbench.discovery, status: "STOPPED" as const, blocker: reason, updatedAt: nowIso() }
        : workbench.discovery;
    return patchFrom(clearError({ ...workbench, kill, requests, discovery }));
  }

  if (actionUid === "SOC-01-ACT-ACCOUNT-BIND") {
    const platformKey = usable(payload.platformKey);
    const displayName = usable(payload.displayName);
    const loginIdentifier = usable(payload.loginIdentifier);
    const authMode = usable(payload.authMode);
    const credentialValue = usable(payload.credentialValue);
    if (!platformKey || !displayName || !loginIdentifier || !authMode || !credentialValue) {
      return fail(workbench, "SOC_ACCOUNT_BIND_REQUIRED");
    }
    const platform = workbench.platforms.find((item) => item.platformKey === platformKey);
    if (!platformEnabled(platform)) return fail(workbench, "SOC_PLATFORM_UNAVAILABLE");
    const prior = workbench.accounts.find((item) => item.accountId === usable(payload.accountId)) ?? null;
    const next: SocAccount = {
      accountId: prior?.accountId ?? newUid("ACC"),
      platformKey,
      displayName,
      loginIdentifier,
      authMode,
      binding: "BOUND_LOCKED",
      credentialStatus: "SET",
      credentialMasked: maskSecret(credentialValue),
      version: (prior?.version ?? 0) + 1,
    };
    return patchFrom(clearError({ ...workbench, accounts: replaceAccount(workbench.accounts, next), reveal: null }));
  }

  if (actionUid === "SOC-01-ACT-CREDENTIAL-REVEAL") {
    const accountId = usable(payload.accountId);
    const account = workbench.accounts.find((item) => item.accountId === accountId);
    if (!account) return fail(workbench, "SOC_ACCOUNT_REQUIRED");
    if (account.credentialStatus !== "SET") return fail(workbench, "SOC_CREDENTIAL_NOT_SET");
    const reason = usable(payload.reason);
    if (!reason) return fail(workbench, "SOC_REVEAL_REASON_REQUIRED");
    return patchFrom(
      clearError({
        ...workbench,
        reveal: { accountId, at: nowIso() },
      }),
    );
  }

  if (actionUid === "SOC-01-ACT-ACCOUNT-UNBIND") {
    const accountId = usable(payload.accountId);
    const account = workbench.accounts.find((item) => item.accountId === accountId);
    if (!account) return fail(workbench, "SOC_ACCOUNT_REQUIRED");
    if (account.binding === "UNBOUND") return fail(workbench, "SOC_ACCOUNT_NOT_BOUND");
    const next: SocAccount = {
      ...account,
      binding: "UNBOUND",
      credentialStatus: "NOT_SET",
      credentialMasked: "",
      version: account.version + 1,
    };
    return patchFrom(
      clearError({
        ...workbench,
        accounts: replaceAccount(workbench.accounts, next),
        reveal: workbench.reveal?.accountId === accountId ? null : workbench.reveal,
      }),
    );
  }

  if (actionUid === "SOC-01-ACT-TARGET-DISCOVERY") {
    const platformKey = usable(payload.platformKey);
    const targetTypes = usable(payload.targetTypes);
    const categories = usable(payload.categories);
    const keywords = usable(payload.keywords);
    const jobName = usable(payload.jobName) || keywords || platformKey;
    if (!discoveryReady({ platformKey, targetTypes, categories, keywords })) {
      return fail(workbench, "SOC_DISCOVERY_REQUIRED");
    }
    const platform = workbench.platforms.find((item) => item.platformKey === platformKey);
    if (!platformEnabled(platform)) return fail(workbench, "SOC_PLATFORM_UNAVAILABLE");
    if (workbench.discovery?.status === "RUNNING" || workbench.discovery?.status === "EXTERNAL_PENDING") {
      return fail(workbench, "SOC_DISCOVERY_ALREADY_ACTIVE");
    }
    const accepted = acceptSocialDiscoveryIntent();
    const discovery: SocDiscovery = {
      jobId: newUid("JOB"),
      jobName,
      platformKey,
      targetTypes,
      categories,
      keywords,
      mode: modeFrom(payload.mode, "SINGLE_RUN"),
      status: accepted.status,
      blocker: accepted.blocker,
      version: 1,
      startedAt: nowIso(),
      updatedAt: nowIso(),
    };
    return patchFrom(clearError({ ...workbench, discovery }));
  }

  if (actionUid === "SOC-01-ACT-DISCOVERY-STOP") {
    const discovery = workbench.discovery;
    if (!discovery || (discovery.status !== "RUNNING" && discovery.status !== "EXTERNAL_PENDING")) {
      return fail(workbench, "SOC_DISCOVERY_NOT_ACTIVE");
    }
    const next: SocDiscovery = {
      ...discovery,
      status: "STOPPED",
      blocker: usable(payload.reason) || "OPERATOR_STOP",
      version: discovery.version + 1,
      updatedAt: nowIso(),
    };
    return patchFrom(clearError({ ...workbench, discovery: next }));
  }

  if (actionUid === "SOC-01-ACT-TARGET-CREATE") {
    const platformKey = usable(payload.platformKey);
    const name = usable(payload.name);
    const targetType = usable(payload.targetType);
    if (!platformKey || !name || !targetType) return fail(workbench, "SOC_TARGET_CREATE_REQUIRED");
    const platform = workbench.platforms.find((item) => item.platformKey === platformKey);
    if (!platform || !platformEnabled(platform)) return fail(workbench, "SOC_PLATFORM_UNAVAILABLE");
    const duplicate = workbench.targets.find(
      (item) => item.platformKey === platformKey && item.name === name,
    );
    if (duplicate) return fail(workbench, "SOC_TARGET_DUPLICATE");
    const next: SocTarget = {
      targetId: newUid("TGT"),
      platformKey,
      name,
      targetType,
      capability: platform.capability,
      status: "DISCOVERED",
      signal: "人工新增",
      evidence: "操作員登記",
      version: 1,
    };
    return patchFrom(clearError({ ...workbench, targets: [...workbench.targets, next] }));
  }

  if (actionUid === "SOC-01-ACT-SEARCH") {
    if (controlUid === "SOC-01-INP-RECORD-SEARCH") {
      return patchFrom(clearError({ ...workbench, recordQuery: usable(payload.query) }));
    }
    return patchFrom(clearError({ ...workbench, query: usable(payload.query) }));
  }

  if (actionUid === "SOC-01-ACT-TARGET-JOIN") {
    const targetId = usable(payload.targetId);
    const target = workbench.targets.find((item) => item.targetId === targetId);
    if (!target) return fail(workbench, "SOC_TARGET_REQUIRED");
    if (target.status !== "DISCOVERED" && target.status !== "READY_TO_JOIN") {
      return fail(workbench, "SOC_TARGET_JOIN_ILLEGAL");
    }
    const account = boundAccountForPlatform(workbench.accounts, target.platformKey);
    if (!account) return fail(workbench, "SOC_ACCOUNT_NOT_BOUND");
    const next: SocTarget = { ...target, status: "JOINED", version: target.version + 1 };
    return patchFrom(clearError({ ...workbench, targets: replaceTarget(workbench.targets, next) }));
  }

  if (actionUid === "SOC-01-ACT-MANUAL-COMPLETE") {
    const targetId = usable(payload.targetId);
    const target = workbench.targets.find((item) => item.targetId === targetId);
    if (!target) return fail(workbench, "SOC_TARGET_REQUIRED");
    if (target.status === "MANUAL_ACTION_REQUIRED") {
      const next: SocTarget = { ...target, status: "JOINED", version: target.version + 1 };
      return patchFrom(clearError({ ...workbench, targets: replaceTarget(workbench.targets, next) }));
    }
    if (target.status === "PENDING_EXTERNAL") {
      const nextTarget: SocTarget = { ...target, status: "POSTED", version: target.version + 1 };
      const requests = workbench.requests.map((item) =>
        item.targetId === targetId && item.status === "PENDING_EXTERNAL"
          ? { ...item, status: "POSTED" as const, external: "POSTED" as const, callback: "OPERATOR_COMPLETED", version: item.version + 1 }
          : item,
      );
      return patchFrom(clearError({ ...workbench, targets: replaceTarget(workbench.targets, nextTarget), requests }));
    }
    return fail(workbench, "SOC_MANUAL_NOT_PENDING");
  }

  if (actionUid === "SOC-01-ACT-RECORD-REPORT") {
    const requestId = usable(payload.requestId);
    const request = workbench.requests.find((item) => item.requestId === requestId);
    if (!request) return fail(workbench, "SOC_REQUEST_REQUIRED");
    if (request.status !== "PENDING_EXTERNAL") return fail(workbench, "SOC_REQUEST_NOT_PENDING");
    const metrics = usable(payload.metrics);
    const interaction = usable(payload.interaction);
    if (!metrics || !interaction) return fail(workbench, "SOC_REPORT_REQUIRED");
    const next: SocRequest = {
      ...request,
      status: "POSTED",
      external: "POSTED",
      metrics,
      interaction,
      callback: "OPERATOR_REPORT",
      incident: "",
      version: request.version + 1,
    };
    const target = workbench.targets.find((item) => item.targetId === request.targetId);
    const targets =
      target && target.status === "PENDING_EXTERNAL"
        ? replaceTarget(workbench.targets, { ...target, status: "POSTED", version: target.version + 1 })
        : workbench.targets;
    return patchFrom(clearError({ ...workbench, requests: replaceRequest(workbench.requests, next), targets }));
  }

  if (actionUid === "SOC-01-ACT-CONTENT-SAVE") {
    const releaseSource = usable(payload.releaseSource);
    const platformKey = usable(payload.platformKey) || workbench.content?.platformKey || "";
    const variant = usable(payload.variant);
    if (!releaseSource || !platformKey || !variant) return fail(workbench, "SOC_CONTENT_REQUIRED");
    const platform = workbench.platforms.find((item) => item.platformKey === platformKey);
    if (!platformEnabled(platform)) return fail(workbench, "SOC_PLATFORM_UNAVAILABLE");
    const prior = workbench.content;
    const version = (prior?.version ?? 0) + 1;
    const next: SocPackage = {
      packageId: prior?.packageId ?? newUid("PKG"),
      releaseSource,
      platformKey,
      variant,
      policyCheck: "PASS",
      candidate: "REVIEW",
      hash: packageHash(releaseSource, platformKey, variant, version),
      version,
    };
    return patchFrom(clearError({ ...workbench, content: next }));
  }

  if (actionUid === "SOC-01-ACT-CANDIDATE-DECIDE") {
    const content = workbench.content;
    if (!content) return fail(workbench, "SOC_CONTENT_REQUIRED");
    if (content.candidate !== "REVIEW") return fail(workbench, "SOC_CANDIDATE_NOT_REVIEW");
    const packageId = usable(payload.packageId);
    if (packageId && packageId !== content.packageId) return fail(workbench, "SOC_CANDIDATE_STALE");
    const decision = decisionFrom(payload.decision) ?? "APPROVE";
    const next: SocPackage = {
      ...content,
      candidate: decision === "APPROVE" ? "APPROVED" : decision === "REJECT" ? "REJECTED" : "RETURN",
      version: content.version + 1,
      hash: decision === "APPROVE" ? content.hash : packageHash(content.releaseSource, content.platformKey, content.variant, content.version + 1),
    };
    return patchFrom(clearError({ ...workbench, content: next }));
  }

  if (actionUid === "SOC-01-ACT-POLICY-CONFIG") {
    const targetId = usable(payload.targetId);
    const target = workbench.targets.find((item) => item.targetId === targetId);
    if (!target) return fail(workbench, "SOC_TARGET_REQUIRED");
    const minIntervalHours = positiveInt(payload.minIntervalHours, 0);
    const dailyLimit = positiveInt(payload.dailyLimit, 0);
    const weeklyLimit = positiveInt(payload.weeklyLimit, 0);
    if (!minIntervalHours || !dailyLimit || !weeklyLimit) return fail(workbench, "SOC_POLICY_REQUIRED");
    const prior = workbench.policy?.targetId === targetId ? workbench.policy : null;
    const next: SocPolicy = {
      targetId,
      minIntervalHours,
      dailyLimit,
      weeklyLimit,
      sameCooldownHours: positiveInt(payload.sameCooldownHours, prior?.sameCooldownHours ?? 0),
      similarCooldownHours: positiveInt(payload.similarCooldownHours, prior?.similarCooldownHours ?? 0),
      allowedWindow: usable(payload.allowedWindow) || prior?.allowedWindow || "",
      notes: usable(payload.notes) || prior?.notes || "",
      version: (prior?.version ?? 0) + 1,
    };
    return patchFrom(clearError({ ...workbench, policy: next }));
  }

  if (actionUid === "SOC-01-ACT-PUBLISH-REQUEST") {
    if (workbench.kill?.active) return fail(workbench, "SOC_KILL_ACTIVE");
    const targetId = usable(payload.targetId);
    const target = workbench.targets.find((item) => item.targetId === targetId);
    if (!target) return fail(workbench, "SOC_TARGET_NOT_READY");
    const content = workbench.content;
    const packageId = usable(payload.contentPackageId) || content?.packageId || "";
    if (!packageApproved(content) || content?.packageId !== packageId) return fail(workbench, "SOC_CONTENT_NOT_APPROVED");
    if (content.platformKey !== target.platformKey) return fail(workbench, "SOC_PLATFORM_MISMATCH");
    const accountId = usable(payload.channelAccountId);
    const account = workbench.accounts.find((item) => item.accountId === accountId) ?? boundAccountForPlatform(workbench.accounts, target.platformKey);
    if (!account || account.platformKey !== target.platformKey || account.binding === "UNBOUND") {
      return fail(workbench, "SOC_ACCOUNT_NOT_BOUND");
    }
    const policy = workbench.policy;
    if (!policy || policy.targetId !== target.targetId) return fail(workbench, "SOC_POLICY_REQUIRED");
    const idempotencyKey = `${target.targetId}:${content.packageId}:${content.version}:${account.accountId}`;
    if (workbench.requests.some((item) => item.idempotencyKey === idempotencyKey && item.status === "PENDING_EXTERNAL")) {
      return fail(workbench, "SOC_PUBLISH_DUPLICATE");
    }
    if (!targetReadyToPost(target)) return fail(workbench, "SOC_TARGET_NOT_READY");
    const accepted = acceptSocialPublishIntent();
    const request: SocRequest = {
      requestId: newUid("REQ"),
      targetId: target.targetId,
      accountId: account.accountId,
      packageId: content.packageId,
      packageVersion: content.version,
      packageHash: content.hash,
      status: "PENDING_EXTERNAL",
      external: accepted.external,
      metrics: "",
      interaction: "",
      callback: accepted.callback,
      incident: "",
      idempotencyKey,
      version: 1,
      createdAt: nowIso(),
    };
    const nextTarget: SocTarget = { ...target, status: "PENDING_EXTERNAL", version: target.version + 1 };
    return patchFrom(
      clearError({
        ...workbench,
        requests: [...workbench.requests, request],
        targets: replaceTarget(workbench.targets, nextTarget),
      }),
    );
  }

  if (actionUid === "SOC-01-ACT-TARGET-EXPORT" || actionUid === "SOC-01-ACT-RECORD-EXPORT") {
    return patchFrom(clearError(workbench));
  }

  if (actionUid === "SOC-01-ACT-REFRESH") {
    const discovery = workbench.discovery;
    if (discovery && discovery.status === "EXTERNAL_PENDING") {
      const probe = probeSocialAdapter();
      const next: SocDiscovery = probe.available
        ? { ...discovery, status: "RUNNING", blocker: "", version: discovery.version + 1, updatedAt: nowIso() }
        : { ...discovery, blocker: probe.reason, updatedAt: nowIso() };
      return patchFrom(clearError({ ...workbench, discovery: next }));
    }
    return patchFrom(clearError(workbench));
  }

  if (actionUid === "SOC-01-ACT-DETAIL-OPEN") {
    return patchFrom(clearError(workbench));
  }

  void controlUid;
  return {};
}
