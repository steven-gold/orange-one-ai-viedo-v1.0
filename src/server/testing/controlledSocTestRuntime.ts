import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import type { IamRuntimeRequest } from "@/server/iam/iamRuntime";
import type { InfoRequest } from "@/server/info/infoCommandRuntime";
import type { CandidateDecisionRequest } from "@/server/shared/candidateDecisionRuntime";

const TEST_METADATA = {
  data_classification: "TEST_ONLY",
  synthetic: true,
  test_dataset_id: "TEST-SOC-01",
  test_run_id: "TEST-RUN-SOC-01-CONTROLLED",
  created_for_validation: true,
  production_eligible: false,
} as const;

type PlatformState = "ENABLED" | "DISABLED";
type AccountState = "UNBOUND" | "CONFIGURED" | "BOUND_LOCKED" | "REAUTH_REQUIRED";
type TargetState = "DISCOVERED" | "READY_TO_JOIN" | "MANUAL_ACTION_REQUIRED" | "PENDING_ADMIN_APPROVAL" | "JOINED" | "READY_TO_POST" | "PENDING_EXTERNAL" | "POSTED" | "COOLDOWN" | "UNAVAILABLE";
type ManualActionState = "PENDING" | "COMPLETED";
type DiscoveryJobState = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
type DraftState = "DRAFT" | "REVIEW" | "APPROVED";
type PublishRequestState = "ACCEPTED" | "MANUAL_ACTION_REQUIRED" | "PENDING_EXTERNAL" | "EXTERNAL_OK" | "FAILED";

type TargetPolicy = {
  minimum_interval_hours: number;
  daily_limit: number;
  weekly_limit: number;
  same_content_cooldown_hours: number | null;
  similar_content_cooldown_hours: number | null;
  allowed_time_window: string | null;
  target_rule_notes: string | null;
};

type Platform = {
  platform_key: string; display_name: string; state: PlatformState; health: string;
  policy: string; capability: string; version: number; governed_binding: boolean; high_risk_active: boolean;
};
type Account = {
  account_id: string; platform_key: string; display_name: string; login_identifier: string;
  auth_mode: string; credential_masked: string; state: AccountState; version: number; binding_verified: boolean;
};
type Target = {
  target_id: string; platform_key: string; name: string; state: TargetState; version: number;
  capability_verified: boolean; manual_action_ref: string | null; policy: TargetPolicy;
};
type DiscoveryJob = {
  job_id: string; job_name: string; platform_key: string; target_types: string[]; categories: string[];
  keywords: string[]; market: string | null; language: string | null; minimum_scale: number | null;
  exclude_keywords: string[]; mode: string; state: DiscoveryJobState;
};
type ManualAction = {
  action_id: string; target_ref: string; kind: string; state: ManualActionState; version: number; note: string | null;
};
type ContentDraft = {
  draft_id: string; draft_type: string; title: string; state: DraftState; version: number;
  release_source_ref: string; platform_variants: string; metadata: string; thumbnail: string;
  policy_check: string; approval_state: string;
};
type PublishRequest = {
  request_id: string; target_ref: string; content_package_id: string; channel_account_id: string;
  schedule_at: string | null; content_hash: string | null; content_similarity_key: string | null;
  state: PublishRequestState; version: number;
};
type PostRecord = {
  post_id: string; target_ref: string; request_ref: string; external_state: string; callback_ref: string;
  metrics_ref: string; interactions_ref: string; incident_ref: string; withdrawal_state: string;
};
type AuditEntry = {
  audit_ref: string;
  event: string;
  subject_ref: string;
  correlation_id: string;
  outcome: "SUCCESS" | "DENIED" | "ERROR";
  reason_code?: string;
};

type ControlledState = {
  platform: Platform | null;
  accounts: Account[];
  targets: Target[];
  discovery_jobs: DiscoveryJob[];
  manual_actions: ManualAction[];
  drafts: ContentDraft[];
  publish_requests: PublishRequest[];
  posts: PostRecord[];
  audits: AuditEntry[];
  audit_counter: number;
  idempotency: Map<string, { ok: boolean; status?: number; value?: unknown; reason_code?: string }>;
  entity_counter: number;
};

const state: ControlledState = {
  platform: null,
  accounts: [],
  targets: [],
  discovery_jobs: [],
  manual_actions: [],
  drafts: [],
  publish_requests: [],
  posts: [],
  audits: [],
  audit_counter: 0,
  idempotency: new Map(),
  entity_counter: 0,
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
function textList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
}
function numberValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value.trim());
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

const DEFAULT_POLICY: TargetPolicy = {
  minimum_interval_hours: 24, daily_limit: 3, weekly_limit: 10,
  same_content_cooldown_hours: 48, similar_content_cooldown_hours: 24,
  allowed_time_window: "08:00-22:00", target_rule_notes: "governed posting policy",
};

function seedFixture() {
  if (state.platform) return;
  state.platform = {
    platform_key: "TEST-SOC-PLATFORM-001", display_name: "Test Governed Platform",
    state: "ENABLED", health: "healthy", policy: "governed posting policy active",
    capability: "posting · page management · target directory", version: 2, governed_binding: true, high_risk_active: true,
  };
  state.accounts.push(
    { account_id: "TEST-SOC-ACCOUNT-001", platform_key: "TEST-SOC-PLATFORM-001", display_name: "Test Channel Account", login_identifier: "user@example.test", auth_mode: "OFFICIAL_OAUTH_OR_TOKEN", credential_masked: "••••••••", state: "BOUND_LOCKED", version: 1, binding_verified: true },
    { account_id: "TEST-SOC-ACCOUNT-002", platform_key: "TEST-SOC-PLATFORM-001", display_name: "Reauth Test Account", login_identifier: "reauth@example.test", auth_mode: "MANUAL_BROWSER_CREDENTIAL", credential_masked: "••••••••", state: "REAUTH_REQUIRED", version: 1, binding_verified: false },
  );
  state.targets.push(
    { target_id: "TEST-SOC-TARGET-001", platform_key: "TEST-SOC-PLATFORM-001", name: "Test Target Community", state: "READY_TO_JOIN", version: 1, capability_verified: true, manual_action_ref: null, policy: { ...DEFAULT_POLICY } },
    { target_id: "TEST-SOC-TARGET-002", platform_key: "TEST-SOC-PLATFORM-001", name: "Test Target Group", state: "JOINED", version: 1, capability_verified: true, manual_action_ref: null, policy: { ...DEFAULT_POLICY } },
    { target_id: "TEST-SOC-TARGET-003", platform_key: "TEST-SOC-PLATFORM-001", name: "Test Target Page", state: "READY_TO_POST", version: 1, capability_verified: true, manual_action_ref: null, policy: { ...DEFAULT_POLICY } },
  );
  state.manual_actions.push(
    { action_id: "TEST-SOC-MANUAL-001", target_ref: "TEST-SOC-TARGET-001", kind: "target_join_verification", state: "PENDING", version: 1, note: "manual verification required before join" },
  );
  state.drafts.push(
    { draft_id: "TEST-SOC-DRAFT-001", draft_type: "content_package", title: "Test content package draft", state: "DRAFT", version: 1, release_source_ref: "TEST-SOC-RELEASE-001", platform_variants: "variant mapping ready", metadata: "title · description · tags set", thumbnail: "thumbnail bound", policy_check: "policy check passed", approval_state: "PENDING_REVIEW" },
    { draft_id: "TEST-SOC-CANDIDATE-001", draft_type: "content_candidate", title: "Test content candidate", state: "REVIEW", version: 2, release_source_ref: "TEST-SOC-RELEASE-001", platform_variants: "variant mapping ready", metadata: "title · description · tags set", thumbnail: "thumbnail bound", policy_check: "policy check passed", approval_state: "UNDER_REVIEW" },
  );
  state.publish_requests.push(
    { request_id: "TEST-SOC-REQ-001", target_ref: "TEST-SOC-TARGET-003", content_package_id: "TEST-SOC-CONTENT-PKG-001", channel_account_id: "TEST-SOC-ACCOUNT-001", schedule_at: "2026-09-01T10:00:00Z", content_hash: "sha256:TEST-CONTENT-HASH", content_similarity_key: "TEST-SIM-KEY-001", state: "PENDING_EXTERNAL", version: 1 },
  );
  state.posts.push(
    { post_id: "TEST-SOC-POST-001", target_ref: "TEST-SOC-TARGET-003", request_ref: "TEST-SOC-REQ-001", external_state: "PENDING_EXTERNAL", callback_ref: "callback recorded", metrics_ref: "metrics collected from recorded callbacks", interactions_ref: "interactions recorded · no synthetic data", incident_ref: "no incidents recorded", withdrawal_state: "read-only · no withdrawal registered" },
  );
}

function appendAudit(entry: Omit<AuditEntry, "audit_ref">): AuditEntry {
  state.audit_counter += 1;
  const full: AuditEntry = { ...entry, audit_ref: `TEST-SOC01-AUDIT-${String(state.audit_counter).padStart(3, "0")}` };
  state.audits = [full, ...state.audits].slice(0, 10);
  return full;
}
function lastAudit(): AuditEntry | null {
  return state.audits[0] ?? null;
}
function nextEntityId(prefix: string): string {
  state.entity_counter += 1;
  return `TEST-SOC-${prefix}-${String(state.entity_counter).padStart(3, "0")}`;
}
function findAccount(id: string | null): Account | null {
  return id ? state.accounts.find(item => item.account_id === id) ?? null : null;
}
function findTarget(id: string | null): Target | null {
  return id ? state.targets.find(item => item.target_id === id) ?? null : null;
}
function findManualAction(id: string | null): ManualAction | null {
  return id ? state.manual_actions.find(item => item.action_id === id) ?? null : null;
}
function findDraft(id: string | null): ContentDraft | null {
  return id ? state.drafts.find(item => item.draft_id === id) ?? null : null;
}
function editableDraft(): ContentDraft | null {
  return state.drafts.find(item => item.state === "DRAFT") ?? null;
}
function reviewCandidate(): ContentDraft | null {
  return state.drafts.find(item => item.state === "REVIEW") ?? null;
}
function approvedCandidate(): ContentDraft | null {
  return state.drafts.find(item => item.state === "APPROVED") ?? null;
}
function joinEligibleTarget(): Target | null {
  return state.targets.find(item => item.state === "DISCOVERED" || item.state === "READY_TO_JOIN") ?? null;
}
function policyEligibleTarget(): Target | null {
  return state.targets.find(item => item.state === "JOINED") ?? null;
}
function publishEligibleTarget(): Target | null {
  return state.targets.find(item => item.state === "READY_TO_POST") ?? null;
}
function pendingManualAction(): ManualAction | null {
  return state.manual_actions.find(item => item.state === "PENDING") ?? null;
}

function gateState(): Record<string, boolean> {
  const platform = state.platform;
  const hasManageableAccount = state.accounts.some(item => item.state === "CONFIGURED" || item.state === "REAUTH_REQUIRED" || item.state === "BOUND_LOCKED");
  return {
    "SOC-01-GATE-PAGE": true,
    "SOC-01-GATE-READ": true,
    "SOC-01-GATE-PLATFORM-CONFIG": Boolean(platform?.governed_binding),
    "SOC-01-GATE-KILL": platform?.state === "ENABLED" && platform?.high_risk_active === true,
    "SOC-01-GATE-ACCOUNT": hasManageableAccount || state.accounts.some(item => item.state === "UNBOUND") || Boolean(platform),
    "SOC-01-GATE-CREDENTIAL": state.accounts.some(item => item.state === "CONFIGURED" || item.state === "REAUTH_REQUIRED" || item.state === "BOUND_LOCKED"),
    "SOC-01-GATE-DISCOVERY": platform?.state === "ENABLED",
    "SOC-01-GATE-TARGET-JOIN": Boolean(joinEligibleTarget()),
    "SOC-01-GATE-MANUAL": Boolean(pendingManualAction()),
    "SOC-01-GATE-CONTENT": Boolean(editableDraft()),
    "SOC-01-GATE-CANDIDATE": Boolean(reviewCandidate()),
    "SOC-01-GATE-POLICY": Boolean(policyEligibleTarget()),
    "SOC-01-GATE-PUBLISH": Boolean(publishEligibleTarget()) && hasManageableAccount && Boolean(approvedCandidate()),
    "SOC-01-GATE-RECORDS": true,
  };
}

function projectionValues(): Record<string, string> {
  const platform = state.platform;
  const accounts = state.accounts.map(item => `${item.account_id} v${item.version} ${item.state === "REAUTH_REQUIRED" ? "REAUTH_REQUIRED" : item.state === "BOUND_LOCKED" ? "BOUND_LOCKED" : item.state}`).join(" | ") || "—";
  const targets = state.targets.map(item => `${item.target_id} ${item.state.replace(/_/g, " ")}`).join(" | ") || "—";
  const policy = policyEligibleTarget() ?? publishEligibleTarget() ?? joinEligibleTarget() ?? state.targets[0] ?? null;
  const policyTarget = policyEligibleTarget() ?? state.targets[0] ?? null;
  const pendingManual = pendingManualAction();
  const editable = editableDraft();
  const candidate = reviewCandidate() ?? approvedCandidate();
  const publishTarget = publishEligibleTarget();
  const boundAccount = state.accounts.find(item => item.state === "BOUND_LOCKED" || item.state === "CONFIGURED") ?? null;
  const last = lastAudit();
  const joinPending = state.targets.filter(item => item.state === "MANUAL_ACTION_REQUIRED" || item.state === "PENDING_ADMIN_APPROVAL").length;

  return {
    "SOC-01-FLD-CONTEXT": `Current workspace · v${platform?.version ?? 1} · governed scope`,
    "SOC-01-FLD-CURRENT-STATE": "資料已載入 · Data loaded",
    "SOC-01-FLD-PLATFORM-LIST": platform ? `${platform.platform_key} · ${platform.state === "ENABLED" ? "enabled" : "disabled"} · ${platform.health}` : "—",
    "SOC-01-FLD-CAPABILITY": platform?.capability ?? "—",
    "SOC-01-FLD-POLICY": platform?.policy ?? "—",
    "SOC-01-FLD-HEALTH": platform?.health ?? "—",
    "SOC-01-FLD-ENABLE-STATE": platform ? (platform.state === "ENABLED" ? "Enabled" : "Disabled") : "—",
    "SOC-01-FLD-ACCOUNT-LIST": accounts,
    "SOC-01-FLD-CREDENTIAL-STATUS": state.accounts.map(item => `${item.account_id} ${item.credential_masked}${item.state === "REAUTH_REQUIRED" ? " · reauth required" : item.binding_verified ? " · verified" : " · pending verification"}`).join(" | ") || "—",
    "SOC-01-FLD-BINDING-VERIFY": state.accounts.some(item => item.binding_verified) ? "verified by service runtime" : "pending service verification",
    "SOC-01-FLD-TARGET-DIRECTORY": targets,
    "SOC-01-FLD-TARGET-CAPABILITY": state.targets.some(item => item.capability_verified) ? "capability verified · join eligible" : "verification pending",
    "SOC-01-FLD-MANUAL-QUEUE": pendingManual ? `${pendingManual.action_id} · ${pendingManual.kind.replace(/_/g, " ")} · pending` : joinPending > 0 ? `${joinPending} manual step pending` : "no manual actions pending",
    "SOC-01-FLD-RELEASE-SOURCE": editable ? `${editable.release_source_ref} · ${editable.draft_type.replace(/_/g, " ")} draft bound` : "—",
    "SOC-01-FLD-PLATFORM-VARIANTS": editable?.platform_variants ?? "—",
    "SOC-01-FLD-METADATA": editable?.metadata ?? "—",
    "SOC-01-FLD-THUMBNAIL": editable?.thumbnail ?? "—",
    "SOC-01-FLD-POLICY-CHECK": editable?.policy_check ?? "—",
    "SOC-01-FLD-APPROVAL": state.drafts.map(item => `${item.draft_id} v${item.version} ${item.state}`).join(" | ") || "—",
    "SOC-01-FLD-VERSION-HISTORY": `${state.drafts.length} content items · versions preserved`,
    "SOC-01-FLD-TARGET-SELECTOR": publishTarget ? `${publishTarget.target_id} · ready to post` : policyTarget ? `${policyTarget.target_id} · ${policyTarget.state.replace(/_/g, " ")}` : "—",
    "SOC-01-FLD-TARGET-CAPABILITY-STATUS": publishTarget ? "ready to post · account bound" : "—",
    "SOC-01-FLD-MIN-INTERVAL": policy ? `${policy.policy.minimum_interval_hours} hours between posts` : "—",
    "SOC-01-FLD-DAILY-LIMIT": policy ? `${policy.policy.daily_limit} posts per day` : "—",
    "SOC-01-FLD-WEEKLY-LIMIT": policy ? `${policy.policy.weekly_limit} posts per week` : "—",
    "SOC-01-FLD-SAME-COOLDOWN": policy?.policy.same_content_cooldown_hours != null ? `${policy.policy.same_content_cooldown_hours} hours for identical content` : "not configured",
    "SOC-01-FLD-SIMILAR-COOLDOWN": policy?.policy.similar_content_cooldown_hours != null ? `${policy.policy.similar_content_cooldown_hours} hours for similar content` : "not configured",
    "SOC-01-FLD-ALLOWED-WINDOW": policy?.policy.allowed_time_window ?? "not configured",
    "SOC-01-FLD-TARGET-RULE-NOTES": policy?.policy.target_rule_notes ?? "—",
    "SOC-01-FLD-CONTENT-PACKAGE": publishTarget ? "TEST-SOC-CONTENT-PKG-001" : "—",
    "SOC-01-FLD-CHANNEL-ACCOUNT": boundAccount ? `${boundAccount.account_id} · bound` : "—",
    "SOC-01-FLD-SCHEDULE-AT": state.publish_requests[0]?.schedule_at ?? "not scheduled",
    "SOC-01-FLD-AUTO-PUBLISH-POLICY": "governed policy · scheduled publish allowed",
    "SOC-01-FLD-HUMAN-APPROVAL-POLICY": "human approval required for company mention",
    "SOC-01-FLD-PUBLISH-QUEUE": `${state.publish_requests.length} request${state.publish_requests.length === 1 ? "" : "s"} · ${state.publish_requests.filter(item => item.state === "PENDING_EXTERNAL").length} pending external`,
    "SOC-01-FLD-MANUAL-ASSIST-QUEUE": "manual assist not required",
    "SOC-01-FLD-POSTS": state.posts.map(item => `${item.post_id} · ${item.external_state.replace(/_/g, " ")}`).join(" | ") || "—",
    "SOC-01-FLD-TARGET-HISTORY": `${state.posts.length} publish record${state.posts.length === 1 ? "" : "s"} · frequency within policy`,
    "SOC-01-FLD-POST-STATUS": state.posts.map(item => `${item.post_id} ${item.external_state.replace(/_/g, " ")}`).join(" | ") || "—",
    "SOC-01-FLD-METRICS": state.posts[0]?.metrics_ref ?? "no recorded metrics",
    "SOC-01-FLD-INTERACTIONS": state.posts[0]?.interactions_ref ?? "no recorded interactions",
    "SOC-01-FLD-MANUAL-HISTORY": `${state.manual_actions.filter(item => item.state === "COMPLETED").length} manual action${state.manual_actions.length === 1 ? "" : "s"} completed`,
    "SOC-01-FLD-CALLBACKS": state.posts[0]?.callback_ref ?? "no callbacks recorded",
    "SOC-01-FLD-INCIDENTS": state.posts[0]?.incident_ref ?? "no incidents recorded",
    "SOC-01-FLD-WITHDRAWAL": state.posts[0]?.withdrawal_state ?? "read-only · no withdrawal registered",
    "SOC-01-FLD-BLOCKERS": state.audits.some(item => item.outcome === "DENIED") ? "A governed action was denied · review audit" : "No blockers · ready to proceed",
    "SOC-01-FLD-CURRENT-AUDIT": last ? `${last.audit_ref} · ${last.event.replace(/\./g, " ")} · ${last.subject_ref} · ${last.outcome}` : "No governance actions yet",
  };
}

export function isControlledSocServerTestMode() {
  return isControlledTestMode();
}

export function readControlledSocTestProjection() {
  seedFixture();
  const account = state.accounts.find(item => item.state === "BOUND_LOCKED" || item.state === "CONFIGURED") ?? state.accounts[0] ?? null;
  const target = publishEligibleTarget() ?? policyEligibleTarget() ?? joinEligibleTarget() ?? state.targets[0] ?? null;
  const manual = pendingManualAction();
  const editable = editableDraft();
  const candidate = reviewCandidate();
  return {
    page_state: "READY",
    values: projectionValues(),
    gate_state: gateState(),
    selected: {
      resource_id: state.platform?.platform_key ?? "",
      resource_version: state.platform ? String(state.platform.version) : "1",
      account_id: account?.account_id ?? "",
      account_version: account ? String(account.version) : "1",
      target_id: target?.target_id ?? "",
      target_version: target ? String(target.version) : "1",
      manual_action_id: manual?.action_id ?? "",
      manual_action_version: manual ? String(manual.version) : "1",
      draft_id: editable?.draft_id ?? "",
      draft_version: editable ? String(editable.version) : "1",
      candidate_id: candidate?.draft_id ?? "",
      candidate_version: candidate ? String(candidate.version) : "1",
      content_package_id: "TEST-SOC-CONTENT-PKG-001",
      channel_account_id: state.accounts.find(item => item.state === "BOUND_LOCKED" || item.state === "CONFIGURED")?.account_id ?? "",
    },
    test_metadata: TEST_METADATA,
  };
}

export type SocCommandOperation =
  | "configureGovernedResource" | "setKillSwitch" | "bindSocialAccount" | "revealSocialCredential"
  | "unbindSocialAccount" | "createSocialTargetDiscovery" | "requestSocialTargetJoin" | "completeSocialManualAction"
  | "saveDraft" | "decideCandidate" | "configureSocialTargetPolicy" | "requestSocialTargetPublish"
  | "searchProjection" | "refreshProjection";

export type SocRuntimeRequest = {
  operation_id: SocCommandOperation;
  correlation_id: string;
  path_params: Record<string, string>;
  payload: unknown;
};

export type SocRuntimeResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; status: number; reason_code: string; correlation_id: string };

type GateFailure = { ok: false; status: number; reason_code: string };

function fail(reason_code: string, status = 403): GateFailure {
  return { ok: false, status, reason_code };
}

function idempotencyGuard(payload: Record<string, unknown>): GateFailure | null {
  if (!text(payload.idempotency_key)) return fail("SOC01_IDEMPOTENCY_KEY_REQUIRED", 400);
  return null;
}
function expectedVersionOf(payload: Record<string, unknown>): number | null {
  const raw = payload.expected_version ?? payload.expected_source_version ?? payload.expected_resource_version;
  if (raw === undefined || raw === null) return null;
  const version = Number(raw);
  return Number.isFinite(version) ? version : -1;
}
function versionGuard(payload: Record<string, unknown>, actual: number | null): GateFailure | null {
  const expected = expectedVersionOf(payload);
  if (expected === null) return fail("SOC01_EXPECTED_VERSION_MISSING", 400);
  if (actual === null || expected !== actual) return fail("SOC01_VERSION_CONFLICT", 409);
  return null;
}

function evaluateGates(operation: SocCommandOperation, request: SocRuntimeRequest): GateFailure | null {
  const payload = record(request.payload);
  const pathId = text(request.path_params?.accountId) ?? text(request.path_params?.targetId) ?? text(request.path_params?.actionId) ?? text(request.path_params?.id) ?? null;
  switch (operation) {
    case "configureGovernedResource": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const resourceType = text(payload.resource_type);
      const resourceId = text(payload.resource_id);
      if (!resourceType || !resourceId || payload.config_patch_json === undefined || payload.config_patch_json === null || !text(payload.reason)) return fail("SOC01_REQUIRED_PLATFORM_CONFIG_FIELD_MISSING", 400);
      if (resourceType !== "social_platform") return fail("SOC01_RESOURCE_TYPE_OUT_OF_PAGE_DOMAIN", 400);
      if (!state.platform?.governed_binding) return fail("SOC01_PLATFORM_BINDING_MISSING");
      if (resourceId !== state.platform.platform_key) return fail("SOC01_EXACT_REF_MISMATCH");
      const guard = versionGuard(payload, state.platform.version); if (guard) return guard;
      return null;
    }
    case "setKillSwitch": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      if (!text(payload.reason)) return fail("SOC01_KILL_REASON_REQUIRED", 400);
      if (state.platform?.state !== "ENABLED") return fail("SOC01_KILL_NOT_APPLICABLE");
      return null;
    }
    case "bindSocialAccount": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const authMode = text(payload.auth_mode);
      const validModes = new Set(["OFFICIAL_OAUTH_OR_TOKEN", "MANUAL_BROWSER_CREDENTIAL", "CUSTOM_SECRET"]);
      for (const key of ["platform_key", "display_name", "login_identifier"]) {
        if (!text(payload[key])) return fail("SOC01_REQUIRED_BIND_FIELD_MISSING", 400);
      }
      if (!authMode || !validModes.has(authMode)) return fail("SOC01_BIND_AUTH_MODE_INVALID", 400);
      if (!text(payload.credential_value)) return fail("SOC01_REQUIRED_BIND_FIELD_MISSING", 400);
      if (!state.platform) return fail("SOC01_PLATFORM_BINDING_MISSING");
      if (text(payload.platform_key) !== state.platform.platform_key) return fail("SOC01_EXACT_REF_MISMATCH");
      const accountId = text(request.path_params?.accountId);
      if (!accountId) return fail("SOC01_ACCOUNT_ID_REQUIRED", 400);
      const existing = findAccount(accountId);
      const expected = expectedVersionOf(payload);
      if (expected === null) return fail("SOC01_EXPECTED_VERSION_MISSING", 400);
      if (existing) { if (expected !== existing.version) return fail("SOC01_VERSION_CONFLICT", 409); if (existing.state !== "UNBOUND" && existing.state !== "REAUTH_REQUIRED") return fail("SOC01_ACCOUNT_STATE_GUARD_REJECTED"); } else if (expected !== 0) return fail("SOC01_VERSION_CONFLICT", 409);
      return null;
    }
    case "revealSocialCredential": {
      if (!text(payload.reason)) return fail("SOC01_REVEAL_REASON_REQUIRED", 400);
      const account = findAccount(pathId);
      if (!account) return fail("SOC01_ACCOUNT_NOT_FOUND");
      if (account.state === "UNBOUND") return fail("SOC01_ACCOUNT_UNBOUND");
      return null;
    }
    case "unbindSocialAccount": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const account = findAccount(pathId);
      if (!account) return fail("SOC01_ACCOUNT_NOT_FOUND");
      if (account.state === "UNBOUND") return fail("SOC01_ACCOUNT_ALREADY_UNBOUND");
      const guard = versionGuard(payload, account.version); if (guard) return guard;
      return null;
    }
    case "createSocialTargetDiscovery": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const mode = text(payload.mode);
      if (!mode || !["CONTINUOUS", "SINGLE_RUN"].includes(mode)) return fail("SOC01_DISCOVERY_MODE_INVALID", 400);
      for (const key of ["job_name", "platform_key", "target_types", "categories", "keywords"]) {
        const value = payload[key];
        if (key === "target_types" || key === "categories" || key === "keywords") {
          if (textList(value).length === 0) return fail("SOC01_REQUIRED_DISCOVERY_FIELD_MISSING", 400);
        } else if (!text(value)) {
          return fail("SOC01_REQUIRED_DISCOVERY_FIELD_MISSING", 400);
        }
      }
      if (state.platform?.state !== "ENABLED") return fail("SOC01_PLATFORM_DISABLED");
      const guard = versionGuard(payload, state.platform.version); if (guard) return guard;
      return null;
    }
    case "requestSocialTargetJoin": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const target = findTarget(pathId);
      if (!target) return fail("SOC01_TARGET_NOT_FOUND");
      if (target.state !== "DISCOVERED" && target.state !== "READY_TO_JOIN") return fail("SOC01_TARGET_STATE_GUARD_REJECTED");
      const guard = versionGuard(payload, target.version); if (guard) return guard;
      return null;
    }
    case "completeSocialManualAction": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const action = findManualAction(pathId);
      if (!action) return fail("SOC01_MANUAL_ACTION_NOT_FOUND");
      if (action.state !== "PENDING") return fail("SOC01_MANUAL_ACTION_NOT_PENDING");
      const guard = versionGuard(payload, action.version); if (guard) return guard;
      return null;
    }
    case "saveDraft": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const draftId = text(payload.draft_id) ?? pathId;
      const draft = findDraft(draftId);
      if (!draft) return fail("SOC01_DRAFT_NOT_FOUND");
      const guard = versionGuard(payload, draft.version); if (guard) return guard;
      if (draft.state !== "DRAFT") return fail("SOC01_DRAFT_NOT_EDITABLE");
      return null;
    }
    case "decideCandidate": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const candidate = findDraft(pathId ?? text(payload.candidate_id));
      if (!candidate || candidate.draft_type !== "content_candidate") return fail("SOC01_CANDIDATE_NOT_FOUND");
      const guard = versionGuard(payload, candidate.version); if (guard) return guard;
      if (candidate.state !== "REVIEW") return fail("SOC01_CANDIDATE_STATE_GUARD_REJECTED");
      const decision = text(payload.decision);
      if (!decision || !["APPROVE", "REJECT", "RETURN"].includes(decision)) return fail("SOC01_CANDIDATE_DECISION_INVALID", 400);
      if (!text(payload.rationale)) return fail("SOC01_CANDIDATE_RATIONALE_REQUIRED", 400);
      return null;
    }
    case "configureSocialTargetPolicy": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const target = findTarget(pathId ?? text(payload.target_id));
      if (!target) return fail("SOC01_TARGET_NOT_FOUND");
      if (target.state !== "JOINED") return fail("SOC01_TARGET_NOT_POLICY_ELIGIBLE");
      const guard = versionGuard(payload, target.version); if (guard) return guard;
      for (const key of ["minimum_interval_hours", "daily_limit", "weekly_limit"]) {
        if (numberValue(payload[key]) === null || (numberValue(payload[key]) as number) < 0) return fail("SOC01_REQUIRED_POLICY_FIELD_MISSING", 400);
      }
      return null;
    }
    case "requestSocialTargetPublish": {
      const idem = idempotencyGuard(payload); if (idem) return idem;
      const target = findTarget(pathId ?? text(payload.target_id));
      if (!target) return fail("SOC01_TARGET_NOT_FOUND");
      if (target.state !== "READY_TO_POST") return fail("SOC01_TARGET_NOT_PUBLISH_ELIGIBLE");
      const guard = versionGuard(payload, target.version); if (guard) return guard;
      if (!text(payload.content_package_id) || !text(payload.channel_account_id)) return fail("SOC01_REQUIRED_PUBLISH_FIELD_MISSING", 400);
      const account = findAccount(text(payload.channel_account_id));
      if (!account || (account.state !== "BOUND_LOCKED" && account.state !== "CONFIGURED")) return fail("SOC01_CHANNEL_ACCOUNT_NOT_BOUND");
      if (!approvedCandidate()) return fail("SOC01_CONTENT_NOT_APPROVED");
      return null;
    }
    case "searchProjection": {
      if (!text(payload.query)) return fail("SOC01_SEARCH_QUERY_REQUIRED", 400);
      return null;
    }
    case "refreshProjection":
      return null;
    default:
      return fail("SOC01_UNSUPPORTED_OPERATION", 400);
  }
}

function executeCommand(operation: SocCommandOperation, request: SocRuntimeRequest): unknown {
  const payload = record(request.payload);
  const pathId = text(request.path_params?.accountId) ?? text(request.path_params?.targetId) ?? text(request.path_params?.actionId) ?? text(request.path_params?.id) ?? null;

  switch (operation) {
    case "configureGovernedResource": {
      const platform = state.platform as Platform;
      const configPatch = record(payload.config_patch_json);
      if (typeof configPatch.enabled === "boolean") platform.state = configPatch.enabled ? "ENABLED" : "DISABLED";
      platform.version += 1;
      appendAudit({ event: "social.platform.configured", subject_ref: platform.platform_key, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { resource_id: platform.platform_key, state: platform.state, version: platform.version, event: "social.platform.configured", test_metadata: TEST_METADATA };
    }
    case "setKillSwitch": {
      const platform = state.platform as Platform;
      platform.state = "DISABLED";
      platform.high_risk_active = false;
      platform.version += 1;
      appendAudit({ event: "social.kill_switch.engaged", subject_ref: platform.platform_key, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { resource_id: platform.platform_key, kill_state: "ENGAGED", version: platform.version, event: "social.kill_switch.engaged", test_metadata: TEST_METADATA };
    }
    case "bindSocialAccount": {
      const account: Account = {
        account_id: pathId as string,
        platform_key: text(payload.platform_key) as string,
        display_name: text(payload.display_name) as string,
        login_identifier: text(payload.login_identifier) as string,
        auth_mode: text(payload.auth_mode) as string,
        credential_masked: "••••••••",
        state: "CONFIGURED",
        version: 1,
        binding_verified: false,
      };
      account.binding_verified = true;
      account.state = "BOUND_LOCKED";
      state.accounts.push(account);
      appendAudit({ event: "social.account.bound", subject_ref: account.account_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { account_id: account.account_id, state: account.state, version: account.version, credential_status: "masked", event: "social.account.bound", test_metadata: TEST_METADATA };
    }
    case "revealSocialCredential": {
      const account = findAccount(pathId) as Account;
      appendAudit({ event: "social.credential.revealed", subject_ref: account.account_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { account_id: account.account_id, credential_masked: account.credential_masked, reveal_note: "masked only · raw secret never rendered", event: "social.credential.revealed", test_metadata: TEST_METADATA };
    }
    case "unbindSocialAccount": {
      const account = findAccount(pathId) as Account;
      account.state = "UNBOUND";
      account.binding_verified = false;
      account.version += 1;
      appendAudit({ event: "social.account.unbound", subject_ref: account.account_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { account_id: account.account_id, state: account.state, version: account.version, event: "social.account.unbound", test_metadata: TEST_METADATA };
    }
    case "createSocialTargetDiscovery": {
      const job: DiscoveryJob = {
        job_id: nextEntityId("DISCOVERY"),
        job_name: text(payload.job_name) as string,
        platform_key: text(payload.platform_key) as string,
        target_types: textList(payload.target_types),
        categories: textList(payload.categories),
        keywords: textList(payload.keywords),
        market: text(payload.market),
        language: text(payload.language),
        minimum_scale: numberValue(payload.minimum_scale),
        exclude_keywords: textList(payload.exclude_keywords),
        mode: text(payload.mode) as string,
        state: "RUNNING",
      };
      state.discovery_jobs.push(job);
      appendAudit({ event: "social.target_discovery.created", subject_ref: job.job_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { job_id: job.job_id, state: job.state, mode: job.mode, event: "social.target_discovery.created", test_metadata: TEST_METADATA };
    }
    case "requestSocialTargetJoin": {
      const target = findTarget(pathId) as Target;
      target.state = "MANUAL_ACTION_REQUIRED";
      target.version += 1;
      const action: ManualAction = {
        action_id: nextEntityId("MANUAL"),
        target_ref: target.target_id,
        kind: "target_join_verification",
        state: "PENDING",
        version: 1,
        note: "manual verification required before join",
      };
      state.manual_actions.push(action);
      target.manual_action_ref = action.action_id;
      appendAudit({ event: "social.target.join_requested", subject_ref: target.target_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { target_id: target.target_id, state: target.state, manual_action_id: action.action_id, event: "social.target.join_requested", test_metadata: TEST_METADATA };
    }
    case "completeSocialManualAction": {
      const action = findManualAction(pathId) as ManualAction;
      action.state = "COMPLETED";
      action.version += 1;
      const target = findTarget(action.target_ref);
      if (target && target.state === "MANUAL_ACTION_REQUIRED") {
        target.state = "JOINED";
        target.version += 1;
      }
      appendAudit({ event: "social.manual_action.completed", subject_ref: action.action_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { action_id: action.action_id, state: action.state, target_id: action.target_ref, event: "social.manual_action.completed", test_metadata: TEST_METADATA };
    }
    case "saveDraft": {
      const draftId = text(payload.draft_id) ?? pathId;
      const draft = findDraft(draftId) as ContentDraft;
      if (text(payload.title)) draft.title = text(payload.title) as string;
      if (text(payload.platform_variants)) draft.platform_variants = text(payload.platform_variants) as string;
      if (text(payload.metadata)) draft.metadata = text(payload.metadata) as string;
      draft.version += 1;
      appendAudit({ event: "social.draft.saved", subject_ref: draft.draft_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { draft_id: draft.draft_id, state: draft.state, version: draft.version, event: "social.draft.saved", test_metadata: TEST_METADATA };
    }
    case "decideCandidate": {
      const candidate = findDraft(pathId ?? text(payload.candidate_id)) as ContentDraft;
      const decision = text(payload.decision) as string;
      if (decision === "APPROVE") {
        candidate.state = "APPROVED";
        candidate.approval_state = "APPROVED";
      } else if (decision === "REJECT") {
        candidate.state = "DRAFT";
        candidate.approval_state = "REJECTED";
      } else {
        candidate.state = "DRAFT";
        candidate.approval_state = "RETURNED";
      }
      candidate.version += 1;
      appendAudit({ event: "social.candidate.decided", subject_ref: candidate.draft_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { candidate_id: candidate.draft_id, state: candidate.state, version: candidate.version, event: "social.candidate.decided", test_metadata: TEST_METADATA };
    }
    case "configureSocialTargetPolicy": {
      const target = findTarget(pathId ?? text(payload.target_id)) as Target;
      target.policy.minimum_interval_hours = numberValue(payload.minimum_interval_hours) as number;
      target.policy.daily_limit = numberValue(payload.daily_limit) as number;
      target.policy.weekly_limit = numberValue(payload.weekly_limit) as number;
      const same = numberValue(payload.same_content_cooldown_hours);
      if (same !== null) target.policy.same_content_cooldown_hours = same;
      const similar = numberValue(payload.similar_content_cooldown_hours);
      if (similar !== null) target.policy.similar_content_cooldown_hours = similar;
      if (text(payload.allowed_time_window)) target.policy.allowed_time_window = text(payload.allowed_time_window);
      if (text(payload.target_rule_notes)) target.policy.target_rule_notes = text(payload.target_rule_notes);
      target.state = "READY_TO_POST";
      target.version += 1;
      appendAudit({ event: "social.target_policy.configured", subject_ref: target.target_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { target_id: target.target_id, state: target.state, version: target.version, event: "social.target_policy.configured", test_metadata: TEST_METADATA };
    }
    case "requestSocialTargetPublish": {
      const target = findTarget(pathId ?? text(payload.target_id)) as Target;
      const requestEntry: PublishRequest = {
        request_id: nextEntityId("REQ"),
        target_ref: target.target_id,
        content_package_id: text(payload.content_package_id) as string,
        channel_account_id: text(payload.channel_account_id) as string,
        schedule_at: text(payload.schedule_at),
        content_hash: text(payload.content_hash),
        content_similarity_key: text(payload.content_similarity_key),
        state: "PENDING_EXTERNAL",
        version: 1,
      };
      state.publish_requests.push(requestEntry);
      const post: PostRecord = {
        post_id: nextEntityId("POST"),
        target_ref: target.target_id,
        request_ref: requestEntry.request_id,
        external_state: "PENDING_EXTERNAL",
        callback_ref: "awaiting external callback",
        metrics_ref: "metrics collected from recorded callbacks",
        interactions_ref: "interactions recorded · no synthetic data",
        incident_ref: "no incidents recorded",
        withdrawal_state: "read-only · no withdrawal registered",
      };
      state.posts.push(post);
      appendAudit({ event: "social.publish.requested", subject_ref: requestEntry.request_id, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { request_id: requestEntry.request_id, state: requestEntry.state, target_id: target.target_id, external_success: false, event: "social.publish.requested", test_metadata: TEST_METADATA };
    }
    case "searchProjection": {
      const query = text(payload.query) as string;
      const needle = query.toLowerCase();
      const accountMatches = state.accounts.filter(item => item.account_id.toLowerCase().includes(needle) || item.display_name.toLowerCase().includes(needle)).map(item => `${item.account_id} ${item.state.replace(/_/g, " ")}`);
      const targetMatches = state.targets.filter(item => item.target_id.toLowerCase().includes(needle) || item.name.toLowerCase().includes(needle)).map(item => `${item.target_id} ${item.state.replace(/_/g, " ")}`);
      const postMatches = state.posts.filter(item => item.post_id.toLowerCase().includes(needle) || item.target_ref.toLowerCase().includes(needle)).map(item => `${item.post_id} ${item.external_state.replace(/_/g, " ")}`);
      return { query, account_matches: accountMatches, target_matches: targetMatches, post_matches: postMatches, test_metadata: TEST_METADATA };
    }
    case "refreshProjection": {
      const ref = `TEST-SOC-REFRESH-${String(state.audit_counter + 1).padStart(3, "0")}`;
      appendAudit({ event: "social.projection.refreshed", subject_ref: ref, correlation_id: request.correlation_id, outcome: "SUCCESS" });
      return { refresh_ref: ref, projection_state: "READY", test_metadata: TEST_METADATA };
    }
    default:
      return { error: "SOC01_UNSUPPORTED_OPERATION", test_metadata: TEST_METADATA };
  }
}

export async function executeControlledSocCommand(request: SocRuntimeRequest): Promise<SocRuntimeResult> {
  if (!isControlledSocServerTestMode()) {
    return { ok: false, status: 503, reason_code: "SOC_TEST_RUNTIME_DISABLED", correlation_id: request.correlation_id };
  }
  const isMutation = request.operation_id !== "searchProjection" && request.operation_id !== "refreshProjection";
  const payload = record(request.payload);
  const idempotencyKey = isMutation ? text(payload.idempotency_key) : null;
  if (isMutation && idempotencyKey) {
    const cached = state.idempotency.get(idempotencyKey);
    if (cached) {
      return cached.ok
        ? { ok: true, value: cached.value, correlation_id: request.correlation_id }
        : { ok: false, status: cached.status ?? 403, reason_code: cached.reason_code as string, correlation_id: request.correlation_id };
    }
  }
  seedFixture();
  const gate = evaluateGates(request.operation_id, request);
  if (gate) {
    if (isMutation && idempotencyKey) {
      state.idempotency.set(idempotencyKey, { ok: false, status: gate.status, reason_code: gate.reason_code });
      appendAudit({ event: `social.gate.denied`, subject_ref: text(record(request.payload).target_id) ?? text(record(request.payload).account_id) ?? text(request.path_params?.targetId) ?? "unresolved", correlation_id: request.correlation_id, outcome: "DENIED", reason_code: gate.reason_code });
    }
    return { ...gate, correlation_id: request.correlation_id };
  }
  const value = executeCommand(request.operation_id, request);
  if (isMutation && idempotencyKey) state.idempotency.set(idempotencyKey, { ok: true, value });
  return { ok: true, value, correlation_id: request.correlation_id };
}

function socIamPayload(request: IamRuntimeRequest): Record<string, unknown> {
  return record(request.payload);
}

function isSocResourceId(id: string | null | undefined): boolean {
  return typeof id === "string" && id.startsWith("TEST-SOC-PLATFORM");
}

export async function executeControlledSocIamCommand(r: IamRuntimeRequest):
  Promise<{ ok: true; value: unknown; correlation_id: string } | { ok: false; reason_code: string; correlation_id: string } | null> {
  if (!isControlledSocServerTestMode()) return null;
  const payload = socIamPayload(r);
  if (r.operation === "configureGovernedResource") {
    const resourceType = text(payload.resource_type);
    const resourceId = text(payload.resource_id) ?? r.resource_id ?? null;
    if (!isSocResourceId(resourceId) && resourceType !== "social_platform") return null;
    const result = await executeControlledSocCommand({
      operation_id: "configureGovernedResource", correlation_id: r.correlation_id,
      path_params: { id: resourceId ?? "TEST-SOC-PLATFORM-001" }, payload: r.payload,
    });
    return result.ok
      ? { ok: true as const, value: result.value, correlation_id: r.correlation_id }
      : { ok: false as const, reason_code: result.reason_code, correlation_id: r.correlation_id };
  }
  if (r.operation === "saveDraft") {
    const draftId = text(payload.draft_id) ?? r.draft_id ?? null;
    const draftType = text(payload.draft_type);
    if (!isSocContentRef(draftId) && !(draftType && draftType.startsWith("content"))) return null;
    const result = await executeControlledSocCommand({
      operation_id: "saveDraft", correlation_id: r.correlation_id,
      path_params: { id: draftId ?? "TEST-SOC-DRAFT-001" }, payload: r.payload,
    });
    return result.ok
      ? { ok: true as const, value: result.value, correlation_id: r.correlation_id }
      : { ok: false as const, reason_code: result.reason_code, correlation_id: r.correlation_id };
  }
  return null;
}

function isSocContentRef(id: string | null | undefined): boolean {
  return typeof id === "string" && (id.startsWith("TEST-SOC-DRAFT") || id.startsWith("TEST-SOC-CANDIDATE"));
}

export async function executeControlledSocInfoCommand(r: InfoRequest):
  Promise<{ ok: true; value: unknown } | { ok: false; status: number; reason_code: string } | null> {
  if (!isControlledSocServerTestMode()) return null;
  const payload = record(r.payload);
  if (text(payload.page_uid) !== "admin:SOC-01") return null;
  if (r.operation_id !== "searchProjection" && r.operation_id !== "refreshProjection") return null;
  const result = await executeControlledSocCommand({ operation_id: r.operation_id, correlation_id: r.correlation_id, path_params: r.path_params, payload: r.payload });
  if (!result.ok) return { ok: false as const, status: result.status, reason_code: result.reason_code };
  return { ok: true as const, value: result.value };
}

export async function executeControlledSocCandidateDecision(r: CandidateDecisionRequest):
  Promise<{ ok: true; value: unknown } | { ok: false; status: number; reason_code: string } | null> {
  if (!isControlledSocServerTestMode()) return null;
  const payload = record(r.payload);
  const candidateId = text(payload.candidate_id) ?? text(payload.candidate_ref) ?? r.candidate_id ?? null;
  if (!isSocContentRef(candidateId)) return null;
  const result = await executeControlledSocCommand({
    operation_id: "decideCandidate", correlation_id: r.correlation_id,
    path_params: { id: candidateId }, payload: r.payload,
  });
  if (!result.ok) return { ok: false as const, status: result.status, reason_code: result.reason_code };
  return { ok: true as const, value: result.value };
}

export function resetControlledSocStateForTest() {
  state.platform = null;
  state.accounts = [];
  state.targets = [];
  state.discovery_jobs = [];
  state.manual_actions = [];
  state.drafts = [];
  state.publish_requests = [];
  state.posts = [];
  state.audits = [];
  state.audit_counter = 0;
  state.idempotency.clear();
  state.entity_counter = 0;
}
