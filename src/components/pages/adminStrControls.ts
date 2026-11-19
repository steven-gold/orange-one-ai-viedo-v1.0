export const ADMIN_STR_VISIBLE_CONTROLS = [
  "CTRL-ADMIN-STR-01-VIEW-OVERVIEW",
  "CTRL-ADMIN-STR-01-VIEW-INTELLIGENCE-FACT",
  "CTRL-ADMIN-STR-01-VIEW-PLAYBOOK",
  "CTRL-ADMIN-STR-01-VIEW-OPPORTUNITY",
  "CTRL-ADMIN-STR-01-VIEW-DECISION",
  "CTRL-ADMIN-STR-01-ACT-SEARCH",
  "CTRL-ADMIN-STR-01-ACT-REFRESH",
  "CTRL-ADMIN-STR-01-ACT-NAV-OPEN",
  "CTRL-ADMIN-STR-01-ACT-CONFIGURE",
  "CTRL-ADMIN-STR-01-ACT-APPROVE",
  "CTRL-ADMIN-STR-01-ACT-EXPORT",
  "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE",
  "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT",
] as const;

export const ADMIN_STR_CONTROL_ACTIONS: Record<string, string> = {
  "CTRL-ADMIN-STR-01-VIEW-OVERVIEW": "getUiProjection",
  "CTRL-ADMIN-STR-01-VIEW-INTELLIGENCE-FACT": "getUiProjection",
  "CTRL-ADMIN-STR-01-VIEW-PLAYBOOK": "getUiProjection",
  "CTRL-ADMIN-STR-01-VIEW-OPPORTUNITY": "getUiProjection",
  "CTRL-ADMIN-STR-01-VIEW-DECISION": "getUiProjection",
  "CTRL-ADMIN-STR-01-ACT-SEARCH": "searchProjection",
  "CTRL-ADMIN-STR-01-ACT-REFRESH": "refreshProjection",
  "CTRL-ADMIN-STR-01-ACT-NAV-OPEN": "getUiProjection",
  "CTRL-ADMIN-STR-01-ACT-CONFIGURE": "configureGovernedResource",
  "CTRL-ADMIN-STR-01-ACT-APPROVE": "approveGovernedResource",
  "CTRL-ADMIN-STR-01-ACT-EXPORT": "exportProjection",
  "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE": "saveDraft",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE": "createCandidate",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE": "compareCandidates",
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE": "rejectStrategyCandidate",
  "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT": "adoptAsContextCandidate",
};

export const ADMIN_STR_VIEWS = [
  "STR-CURRENT-VIEW-OVERVIEW",
  "STR-CURRENT-VIEW-INTELLIGENCE-FACT",
  "STR-CURRENT-VIEW-PLAYBOOK",
  "STR-CURRENT-VIEW-OPPORTUNITY",
  "STR-CURRENT-VIEW-DECISION",
] as const;

export type AdminStrView = (typeof ADMIN_STR_VIEWS)[number];

export type AdminStrDrawer = "nav" | "search" | "detail";

export const ADMIN_STR_VIEW_CONTROLS: Record<AdminStrView, string> = {
  "STR-CURRENT-VIEW-OVERVIEW": "CTRL-ADMIN-STR-01-VIEW-OVERVIEW",
  "STR-CURRENT-VIEW-INTELLIGENCE-FACT": "CTRL-ADMIN-STR-01-VIEW-INTELLIGENCE-FACT",
  "STR-CURRENT-VIEW-PLAYBOOK": "CTRL-ADMIN-STR-01-VIEW-PLAYBOOK",
  "STR-CURRENT-VIEW-OPPORTUNITY": "CTRL-ADMIN-STR-01-VIEW-OPPORTUNITY",
  "STR-CURRENT-VIEW-DECISION": "CTRL-ADMIN-STR-01-VIEW-DECISION",
};

export const ADMIN_STR_VIEW_ACTIONS: Record<AdminStrView, readonly string[]> = {
  "STR-CURRENT-VIEW-OVERVIEW": [
    "CTRL-ADMIN-STR-01-ACT-SEARCH",
    "CTRL-ADMIN-STR-01-ACT-REFRESH",
    "CTRL-ADMIN-STR-01-ACT-NAV-OPEN",
  ],
  "STR-CURRENT-VIEW-INTELLIGENCE-FACT": [
    "CTRL-ADMIN-STR-01-ACT-CONFIGURE",
    "CTRL-ADMIN-STR-01-ACT-APPROVE",
    "CTRL-ADMIN-STR-01-ACT-SEARCH",
    "CTRL-ADMIN-STR-01-ACT-EXPORT",
    "CTRL-ADMIN-STR-01-ACT-NAV-OPEN",
  ],
  "STR-CURRENT-VIEW-PLAYBOOK": [
    "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE",
    "CTRL-ADMIN-STR-01-ACT-APPROVE",
    "CTRL-ADMIN-STR-01-ACT-NAV-OPEN",
  ],
  "STR-CURRENT-VIEW-OPPORTUNITY": [
    "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE",
    "CTRL-ADMIN-STR-01-ACT-APPROVE",
    "CTRL-ADMIN-STR-01-ACT-NAV-OPEN",
  ],
  "STR-CURRENT-VIEW-DECISION": [
    "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE",
    "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE",
    "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT",
    "CTRL-ADMIN-STR-01-ACT-NAV-OPEN",
  ],
};

export { ADMIN_STR_STATE_ERROR_UID, ADMIN_STR_STATE_RESOURCE_UID } from "@/server/domain/adminStr";

export interface AdminStrFormField {
  key: string;
  label: string;
  area?: boolean;
  list?: boolean;
}

// Exact registered request schemas per effectful control (labels are the
// contract's registered schema field names).
export const ADMIN_STR_FORM_SCHEMAS: Record<string, readonly AdminStrFormField[]> = {
  "CTRL-ADMIN-STR-01-ACT-SEARCH": [{ key: "query", label: "query" }],
  "CTRL-ADMIN-STR-01-ACT-CONFIGURE": [
    { key: "resource_type", label: "resource_type" },
    { key: "resource_id", label: "resource_id" },
    { key: "config_patch_json", label: "config_patch_json", area: true },
    { key: "reason", label: "reason", area: true },
  ],
  "CTRL-ADMIN-STR-01-ACT-APPROVE": [
    { key: "resource_type", label: "resource_type" },
    { key: "resource_id", label: "resource_id" },
    { key: "rationale", label: "rationale", area: true },
    { key: "expected_resource_version", label: "expected_resource_version" },
  ],
  "CTRL-ADMIN-STR-01-ACT-EXPORT": [{ key: "export_scope", label: "export_scope" }],
  "CTRL-ADMIN-STR-01-ACT-DRAFT-SAVE": [
    { key: "draft_id", label: "draft_id" },
    { key: "playbook_content", label: "playbook_content", area: true },
  ],
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-CREATE": [
    { key: "candidate_title", label: "candidate_title" },
    { key: "candidate_summary", label: "candidate_summary", area: true },
    { key: "source_opportunity", label: "source_opportunity" },
  ],
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-COMPARE": [{ key: "candidate_ids", label: "candidate_ids (comma separated)", list: true }],
  "CTRL-ADMIN-STR-01-ACT-CANDIDATE-DECIDE": [
    { key: "candidate_id", label: "candidate_id" },
    { key: "rationale", label: "rationale", area: true },
  ],
  "CTRL-ADMIN-STR-01-ACT-ADOPT-CONTEXT": [
    { key: "candidate_id", label: "candidate_id" },
    { key: "rationale", label: "rationale", area: true },
  ],
};
