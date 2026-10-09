export const IAM_VISIBLE_CONTROLS = [
  "IAM-01-CTL-SEARCH",
  "IAM-01-BTN-ADD",
  "IAM-01-BTN-EDIT",
  "IAM-01-CTL-BASIC-DATA",
  "IAM-01-SEL-DEPT-PRESET",
  "IAM-01-CHK-FRONT-ALL",
  "IAM-01-GRP-FRONT-L1",
  "IAM-01-CHK-BACK-ALL",
  "IAM-01-GRP-BACK-L1",
  "IAM-01-BTN-SAVE-DRAFT",
  "IAM-01-BTN-VALIDATE",
  "IAM-01-BTN-PREVIEW",
  "IAM-01-BTN-COMPLETE",
  "IAM-01-BTN-AUDIT",
] as const;

export const IAM_CONTROL_ACTIONS: Record<string, string> = {
  "IAM-01-CTL-SEARCH": "IAM-01-ACT-SEARCH",
  "IAM-01-BTN-ADD": "IAM-01-ACT-OPEN-CREATE",
  "IAM-01-BTN-EDIT": "IAM-01-ACT-OPEN-EDIT",
  "IAM-01-CTL-BASIC-DATA": "IAM-01-ACT-BASIC-DATA-EDIT",
  "IAM-01-SEL-DEPT-PRESET": "IAM-01-ACT-PRESET-APPLY-TO-DRAFT",
  "IAM-01-CHK-FRONT-ALL": "IAM-01-ACT-FRONT-ALL-DRAFT",
  "IAM-01-GRP-FRONT-L1": "IAM-01-ACT-L1-DRAFT-SET",
  "IAM-01-CHK-BACK-ALL": "IAM-01-ACT-BACK-ALL-DRAFT",
  "IAM-01-GRP-BACK-L1": "IAM-01-ACT-L1-DRAFT-SET",
  "IAM-01-BTN-SAVE-DRAFT": "IAM-01-ACT-SAVE-DRAFT",
  "IAM-01-BTN-VALIDATE": "IAM-01-ACT-VALIDATE-DRAFT",
  "IAM-01-BTN-PREVIEW": "IAM-01-ACT-PREVIEW",
  "IAM-01-BTN-COMPLETE": "IAM-01-ACT-COMPLETE",
  "IAM-01-BTN-AUDIT": "IAM-01-ACT-AUDIT-OPEN",
};

export const IAM_FRONT_L1 = [
  "iam.front-01",
  "iam.front-02",
  "iam.front-03",
  "iam.front-04",
  "iam.front-05",
  "iam.front-06",
  "iam.front-07",
  "iam.front-08",
  "iam.front-09",
] as const;

export const IAM_BACK_L1 = [
  "iam.back-01",
  "iam.back-02",
  "iam.back-03",
  "iam.back-04",
  "iam.back-05",
  "iam.back-06",
  "iam.back-07",
  "iam.back-08",
  "iam.back-09",
] as const;

export const IAM_CHAIN_STEPS = [
  "iam.chain-01",
  "iam.chain-02",
  "iam.chain-03",
  "iam.chain-04",
  "iam.chain-05",
  "iam.chain-06",
  "iam.chain-07",
] as const;
