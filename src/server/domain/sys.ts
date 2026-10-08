export const SYS_PERMISSION = "system.change.propose";
export const SYS_PAGE_UID = "admin:SYS-01";
export const SYS_ROUTE = "/admin/system";
export const SYS_PROJECTION = "SysWorkbenchProjection";
export const SYS_CHAIN = "SYS-01-FWC-PAGE-01";

export const SYS_VISIBLE_CONTROLS = [
  "SYS-01-BTN-SINGLE-AI",
  "SYS-01-BTN-MULTI-AI",
  "SYS-01-BTN-COUNCIL-DISCUSSION",
  "SYS-01-BTN-COUNCIL-PARALLEL",
  "SYS-01-INP-MESSAGE",
  "SYS-01-BTN-ATTACH",
  "SYS-01-BTN-SEND",
  "SYS-01-BTN-STOP",
  "SYS-01-BTN-CANDIDATE-CREATE",
  "SYS-01-BTN-CR-CREATE",
  "SYS-01-BTN-NAV-OPEN",
  "SYS-01-BTN-SANDBOX-TEST",
] as const;

export const SYS_CONTROL_ACTIONS: Record<string, string> = {
  "SYS-01-BTN-SINGLE-AI": "SYS-01-ACT-AI-MODE-SINGLE",
  "SYS-01-BTN-MULTI-AI": "SYS-01-ACT-AI-MODE-MULTI",
  "SYS-01-BTN-COUNCIL-DISCUSSION": "SYS-01-ACT-COUNCIL-MODE-DISCUSSION",
  "SYS-01-BTN-COUNCIL-PARALLEL": "SYS-01-ACT-COUNCIL-MODE-PARALLEL",
  "SYS-01-INP-MESSAGE": "SYS-01-ACT-MESSAGE-DRAFT",
  "SYS-01-BTN-ATTACH": "SYS-01-ACT-CONVERSATION-ATTACH",
  "SYS-01-BTN-SEND": "SYS-01-ACT-CONVERSATION-SEND",
  "SYS-01-BTN-STOP": "SYS-01-ACT-CONVERSATION-STOP",
  "SYS-01-BTN-CANDIDATE-CREATE": "ACT-CANDIDATE-CREATE",
  "SYS-01-BTN-CR-CREATE": "ACT-CR-CREATE",
  "SYS-01-BTN-NAV-OPEN": "ACT-NAV-OPEN",
  "SYS-01-BTN-SANDBOX-TEST": "SYS-01-ACT-SANDBOX-TEST",
};

export interface SysFieldValue {
  controlUid: string;
  value: string | null;
}

export interface SysReadModel {
  projectionUid: typeof SYS_PROJECTION;
  pageUid: typeof SYS_PAGE_UID;
  route: typeof SYS_ROUTE;
  permission: typeof SYS_PERMISSION;
  chainUid: typeof SYS_CHAIN;
  authorized: boolean;
  fields: SysFieldValue[];
}
