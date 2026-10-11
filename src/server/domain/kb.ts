export const KB_PERMISSION = "knowledge.read";
export const KB_PAGE_UID = "admin:KB-01";
export const KB_ROUTE = "/admin/knowledge";
export const KB_PROJECTION = "KbWorkbenchProjection";
export const KB_CHAIN = "ADMIN-KB-01-FWC-PAGE-01";

export const KB_VISIBLE_CONTROLS = [
  "CTRL-ADMIN-KB-01-VIEW-OVERVIEW",
  "CTRL-ADMIN-KB-01-VIEW-SOURCE",
  "CTRL-ADMIN-KB-01-VIEW-SEARCH",
  "CTRL-ADMIN-KB-01-VIEW-EXPERIENCE",
  "CTRL-ADMIN-KB-01-VIEW-REVIEW",
  "CTRL-ADMIN-KB-01-ACT-SEARCH",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE",
  "CTRL-ADMIN-KB-01-ACT-INGEST-START",
  "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN",
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE",
  "CTRL-ADMIN-KB-01-ACT-APPROVE",
  "CTRL-ADMIN-KB-01-ACT-RETURN",
  "CTRL-ADMIN-KB-01-ACT-REJECT",
] as const;

export const KB_CONTROL_ACTIONS: Record<string, string> = {
  "CTRL-ADMIN-KB-01-VIEW-OVERVIEW": "getUiProjection",
  "CTRL-ADMIN-KB-01-VIEW-SOURCE": "getUiProjection",
  "CTRL-ADMIN-KB-01-VIEW-SEARCH": "getUiProjection",
  "CTRL-ADMIN-KB-01-VIEW-EXPERIENCE": "getUiProjection",
  "CTRL-ADMIN-KB-01-VIEW-REVIEW": "getUiProjection",
  "CTRL-ADMIN-KB-01-ACT-SEARCH": "searchKnowledge",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-CREATE": "createKnowledgeSource",
  "CTRL-ADMIN-KB-01-ACT-SOURCE-SAVE": "updateKnowledgeSource",
  "CTRL-ADMIN-KB-01-ACT-INGEST-START": "createAcquisitionJob",
  "CTRL-ADMIN-KB-01-ACT-CITATION-OPEN": "getCitation",
  "CTRL-ADMIN-KB-01-ACT-CONTEXT-CREATE": "createContextCandidate",
  "CTRL-ADMIN-KB-01-ACT-REPLAY-OPEN": "getExperienceReplay",
  "CTRL-ADMIN-KB-01-ACT-LEARNING-CREATE": "createLearningCandidate",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-FROM-EXP": "createKnowledgeDraftFromExperience",
  "CTRL-ADMIN-KB-01-ACT-DRAFT-SAVE": "saveKnowledgeDraft",
  "CTRL-ADMIN-KB-01-ACT-APPROVE": "approveKnowledgeDraft",
  "CTRL-ADMIN-KB-01-ACT-RETURN": "returnKnowledgeDraft",
  "CTRL-ADMIN-KB-01-ACT-REJECT": "rejectKnowledgeDraft",
};

export interface KbFieldValue {
  controlUid: string;
  value: string | null;
}

export interface KbReadModel {
  projectionUid: typeof KB_PROJECTION;
  pageUid: typeof KB_PAGE_UID;
  route: typeof KB_ROUTE;
  permission: typeof KB_PERMISSION;
  chainUid: typeof KB_CHAIN;
  authorized: boolean;
  fields: KbFieldValue[];
}
