export const SYS_CURRENT_CONTROL_COUNT = 12;
export const SYS_SECTION_COUNT = 8;
export const SYS_AUTHORITY_STATUS = "FINAL_LOCKED" as const;
export const SYS_IMPLEMENTATION_STATUS = "NOT_EXECUTED" as const;

export const SYS_SERVICE_OPERATIONS = ["createCandidate", "createChangeRequest", "runSandboxTest"] as const;
export type SysServiceOperation = (typeof SYS_SERVICE_OPERATIONS)[number];
export type SysAiMode = "SINGLE_AI" | "MULTI_AI";
export type SysCouncilMode = "DISCUSSION" | "PARALLEL";

export type SystemControlAuthorityTrace = {
  control_uid: string;
  action_uid: string;
  gate_uid: string | null;
  permission_uid: string;
  runtime_binding: string | null;
  service_operation: SysServiceOperation | null;
  enabled_in_visual_phase: boolean;
};

export const SYS_CONTROL_REGISTRY: readonly SystemControlAuthorityTrace[] = [
  {
    control_uid: "SYS-01-BTN-SINGLE-AI",
    action_uid: "SYS-01-ACT-AI-MODE-SINGLE",
    gate_uid: "SYS-01-GATE-AI-MODE",
    permission_uid: "system.ai.use",
    runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED",
    service_operation: null,
    enabled_in_visual_phase: true,
  },
  {
    control_uid: "SYS-01-BTN-MULTI-AI",
    action_uid: "SYS-01-ACT-AI-MODE-MULTI",
    gate_uid: "SYS-01-GATE-MULTI-AI",
    permission_uid: "system.ai.use",
    runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED",
    service_operation: null,
    enabled_in_visual_phase: true,
  },
  {
    control_uid: "SYS-01-BTN-COUNCIL-DISCUSSION",
    action_uid: "SYS-01-ACT-COUNCIL-MODE-DISCUSSION",
    gate_uid: "SYS-01-GATE-COUNCIL-MODE",
    permission_uid: "system.ai.use",
    runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED",
    service_operation: null,
    enabled_in_visual_phase: true,
  },
  {
    control_uid: "SYS-01-BTN-COUNCIL-PARALLEL",
    action_uid: "SYS-01-ACT-COUNCIL-MODE-PARALLEL",
    gate_uid: "SYS-01-GATE-COUNCIL-MODE",
    permission_uid: "system.ai.use",
    runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED",
    service_operation: null,
    enabled_in_visual_phase: true,
  },
  {
    control_uid: "SYS-01-INP-MESSAGE",
    action_uid: "SYS-01-ACT-MESSAGE-DRAFT",
    gate_uid: "SYS-01-GATE-CONVERSATION-COMPOSER",
    permission_uid: "system.ai.use",
    runtime_binding: "LOCAL_DRAFT_STATE_ONLY_IN_VISUAL_PHASE",
    service_operation: null,
    enabled_in_visual_phase: true,
  },
  {
    control_uid: "SYS-01-BTN-ATTACH",
    action_uid: "SYS-01-ACT-CONVERSATION-ATTACH",
    gate_uid: "SYS-01-GATE-CONVERSATION-COMPOSER",
    permission_uid: "system.ai.use",
    runtime_binding: "REUSE_ACPOS_AI_CONVERSATION_CORE_ATTACHMENT",
    service_operation: null,
    enabled_in_visual_phase: false,
  },
  {
    control_uid: "SYS-01-BTN-SEND",
    action_uid: "SYS-01-ACT-CONVERSATION-SEND",
    gate_uid: "SYS-01-GATE-CONVERSATION-SEND",
    permission_uid: "system.ai.use",
    runtime_binding: "REUSE_ACPOS_AI_CONVERSATION_CORE_MESSAGE_SUBMIT",
    service_operation: null,
    enabled_in_visual_phase: false,
  },
  {
    control_uid: "SYS-01-BTN-STOP",
    action_uid: "SYS-01-ACT-CONVERSATION-STOP",
    gate_uid: "SYS-01-GATE-CONVERSATION-STOP",
    permission_uid: "system.ai.use",
    runtime_binding: "REUSE_ACPOS_AI_CONVERSATION_CORE_GENERATION_STOP",
    service_operation: null,
    enabled_in_visual_phase: false,
  },
  {
    control_uid: "SYS-01-BTN-CANDIDATE-CREATE",
    action_uid: "ACT-CANDIDATE-CREATE",
    gate_uid: null,
    permission_uid: "system.change.propose",
    runtime_binding: null,
    service_operation: "createCandidate",
    enabled_in_visual_phase: false,
  },
  {
    control_uid: "SYS-01-BTN-CR-CREATE",
    action_uid: "ACT-CR-CREATE",
    gate_uid: null,
    permission_uid: "core.change.create",
    runtime_binding: null,
    service_operation: "createChangeRequest",
    enabled_in_visual_phase: false,
  },
  {
    control_uid: "SYS-01-BTN-NAV-OPEN",
    action_uid: "ACT-NAV-OPEN",
    gate_uid: null,
    permission_uid: "ops.read",
    runtime_binding: null,
    service_operation: null,
    enabled_in_visual_phase: false,
  },
  {
    control_uid: "SYS-01-BTN-SANDBOX-TEST",
    action_uid: "SYS-01-ACT-SANDBOX-TEST",
    gate_uid: null,
    permission_uid: "system.test.execute",
    runtime_binding: null,
    service_operation: "runSandboxTest",
    enabled_in_visual_phase: false,
  },
] as const;

export function getSystemControlTrace(control_uid: string): SystemControlAuthorityTrace {
  const trace = SYS_CONTROL_REGISTRY.find((entry) => entry.control_uid === control_uid);
  if (!trace) throw new Error(`SYS-01 control is not registered in Current Authority: ${control_uid}`);
  return trace;
}

export type SystemContinuityContext = {
  system_change_id: string;
  system_truth: unknown;
  active_change: unknown;
  conversation: unknown;
  decisions: unknown;
  affected_scope: unknown;
  validation: unknown;
  deployment: unknown;
  latest_context_fingerprint: string;
};
