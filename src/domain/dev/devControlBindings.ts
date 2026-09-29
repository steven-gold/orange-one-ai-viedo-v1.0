export type DevControlBinding = {
  action_uid: string;
  gate_uid: string;
  effect_type: "UI_CONTEXT_STATE" | "REGISTERED_COMMAND" | "HIGH_RISK_REGISTERED_COMMAND";
  runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED" | "SOURCE_REGISTERED_OPERATION";
  permission?: string;
  operation?: string;
  method_path?: string;
};

export const DEV_CONTROL_BINDINGS = {
  "DEV-01-BTN-STAGE-1": { action_uid: "DEV-01-ACT-STAGE-1-SELECT", gate_uid: "DEV-01-GATE-PAGE", effect_type: "UI_CONTEXT_STATE", runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED" },
  "DEV-01-BTN-STAGE-2": { action_uid: "DEV-01-ACT-STAGE-2-SELECT", gate_uid: "DEV-01-GATE-PAGE", effect_type: "UI_CONTEXT_STATE", runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED" },
  "DEV-01-BTN-STAGE-3": { action_uid: "DEV-01-ACT-STAGE-3-SELECT", gate_uid: "DEV-01-GATE-PAGE", effect_type: "UI_CONTEXT_STATE", runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED" },
  "DEV-01-BTN-STAGE-4": { action_uid: "DEV-01-ACT-STAGE-4-SELECT", gate_uid: "DEV-01-GATE-PAGE", effect_type: "UI_CONTEXT_STATE", runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED" },
  "DEV-01-BTN-STAGE-5": { action_uid: "DEV-01-ACT-STAGE-5-SELECT", gate_uid: "DEV-01-GATE-PAGE", effect_type: "UI_CONTEXT_STATE", runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED" },
  "DEV-01-BTN-DISCOVERY-START": { action_uid: "DEV-01-ACT-DISCOVERY-START", gate_uid: "DEV-01-GATE-DISCOVERY-START", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.discovery.configure", operation: "startCompanyDiscovery", method_path: "POST /v1/outreach/discovery-jobs" },
  "DEV-01-BTN-DISCOVERY-PAUSE": { action_uid: "DEV-01-ACT-DISCOVERY-PAUSE", gate_uid: "DEV-01-GATE-DISCOVERY-RUNNING", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.discovery.configure", operation: "pauseCompanyDiscovery", method_path: "POST /v1/outreach/discovery-jobs/{jobId}/pause" },
  "DEV-01-BTN-DISCOVERY-RESUME": { action_uid: "DEV-01-ACT-DISCOVERY-RESUME", gate_uid: "DEV-01-GATE-DISCOVERY-PAUSED", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.discovery.configure", operation: "resumeCompanyDiscovery", method_path: "POST /v1/outreach/discovery-jobs/{jobId}/resume" },
  "DEV-01-BTN-DISCOVERY-STOP": { action_uid: "DEV-01-ACT-DISCOVERY-STOP", gate_uid: "DEV-01-GATE-DISCOVERY-RUNNING", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.discovery.configure", operation: "stopCompanyDiscovery", method_path: "POST /v1/outreach/discovery-jobs/{jobId}/stop" },
  "DEV-01-BTN-DIRECTORY-SEARCH": { action_uid: "DEV-01-ACT-DIRECTORY-SEARCH", gate_uid: "DEV-01-GATE-DIRECTORY-READ", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "projection.search", operation: "searchProjection", method_path: "POST /v1/search" },
  "DEV-01-BTN-MERGE-PREVIEW": { action_uid: "DEV-01-ACT-MERGE-PREVIEW", gate_uid: "DEV-01-GATE-MERGE", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.directory.merge", operation: "previewCompanyMerge", method_path: "POST /v1/outreach/companies/merge-preview" },
  "DEV-01-BTN-MERGE": { action_uid: "DEV-01-ACT-MERGE", gate_uid: "DEV-01-GATE-MERGE-CONFIRM", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.directory.merge", operation: "mergeCompanyCandidate", method_path: "POST /v1/outreach/companies/{companyId}/merge" },
  "DEV-01-BTN-EXPORT": { action_uid: "DEV-01-ACT-EXPORT", gate_uid: "DEV-01-GATE-EXPORT", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "projection.export", operation: "exportProjection", method_path: "POST /v1/exports" },
  "DEV-01-BTN-CANDIDATE-CREATE": { action_uid: "DEV-01-ACT-CANDIDATE-CREATE", gate_uid: "DEV-01-GATE-MESSAGE-WRITE", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "candidate.create", operation: "createCandidate", method_path: "POST /v1/candidates" },
  "DEV-01-BTN-CANDIDATE-DECIDE": { action_uid: "DEV-01-ACT-CANDIDATE-DECIDE", gate_uid: "DEV-01-GATE-MESSAGE-REVIEW", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "candidate.decide", operation: "decideCandidate", method_path: "POST /v1/candidates/{id}/decision" },
  "DEV-01-BTN-CR-CREATE": { action_uid: "DEV-01-ACT-CR-CREATE", gate_uid: "DEV-01-GATE-MESSAGE-REVIEW", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "core.change.create", operation: "createChangeRequest", method_path: "POST /v1/change-requests" },
  "DEV-01-BTN-CAMPAIGN-SEARCH": { action_uid: "DEV-01-ACT-CAMPAIGN-SEARCH", gate_uid: "DEV-01-GATE-CAMPAIGN", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "projection.search", operation: "searchProjection", method_path: "POST /v1/search" },
  "DEV-01-BTN-CAMPAIGN-CREATE": { action_uid: "DEV-01-ACT-CAMPAIGN-CREATE", gate_uid: "DEV-01-GATE-CAMPAIGN", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.batch.create", operation: "createOutreachCampaign", method_path: "POST /v1/outreach/campaigns" },
  "DEV-01-BTN-CAMPAIGN-APPROVE": { action_uid: "DEV-01-ACT-CAMPAIGN-APPROVE", gate_uid: "DEV-01-GATE-CAMPAIGN-APPROVAL", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.batch.approve", operation: "approveOutreachCampaign", method_path: "POST /v1/outreach/campaigns/{campaignId}/approve" },
  "DEV-01-BTN-EMAIL-DISPATCH": { action_uid: "DEV-01-ACT-EMAIL-DISPATCH", gate_uid: "DEV-01-GATE-DISPATCH", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "outreach.send.dispatch", operation: "dispatchOutreachCampaign", method_path: "POST /v1/outreach/campaigns/{campaignId}/dispatch" },
  "DEV-01-BTN-REFRESH": { action_uid: "DEV-01-ACT-REFRESH", gate_uid: "DEV-01-GATE-DELIVERY-READ", effect_type: "REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "projection.refresh", operation: "refreshProjection", method_path: "POST /v1/projections/refresh" },
  "DEV-01-BTN-KILL-SWITCH": { action_uid: "DEV-01-ACT-KILL-SWITCH", gate_uid: "DEV-01-GATE-KILL-SWITCH", effect_type: "HIGH_RISK_REGISTERED_COMMAND", runtime_binding: "SOURCE_REGISTERED_OPERATION", permission: "ops.kill_switch", operation: "setKillSwitch", method_path: "POST /v1/operations/kill-switch" },
} as const satisfies Record<string, DevControlBinding>;

export type DevControlUid = keyof typeof DEV_CONTROL_BINDINGS;
export const DEV_CONTROL_BINDING_COUNT = Object.keys(DEV_CONTROL_BINDINGS).length;
