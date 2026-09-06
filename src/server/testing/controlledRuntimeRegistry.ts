import {
  createControlledTestMetadata,
  isControlledTestMode,
  type ControlledTestMetadata,
} from "@/domain/testing/controlledTestData";

export type ControlledRuntimeFamily =
  | "CORE"
  | "ASSET"
  | "VIDEO"
  | "EDIT"
  | "QA"
  | "DB"
  | "STRATEGY"
  | "INFO"
  | "SYS"
  | "IAM"
  | "DEV"
  | "SOC"
  | "ERP"
  | "AIAPI"
  | "SG-02"
  | "KB"
  | "CONVERSATION"
  | "CANDIDATE"
  | "DEPARTMENT";

export type ControlledRuntimeRegistration = {
  family: ControlledRuntimeFamily;
  page_uids: readonly string[];
  test_only: true;
};

export const CONTROLLED_RUNTIME_REGISTRY: readonly ControlledRuntimeRegistration[] = [
  { family: "CORE", page_uids: ["CORE-01"], test_only: true },
  { family: "ASSET", page_uids: ["ASSET-01"], test_only: true },
  { family: "VIDEO", page_uids: ["VIDEO-01"], test_only: true },
  { family: "EDIT", page_uids: ["EDIT-01"], test_only: true },
  { family: "QA", page_uids: ["QA-01"], test_only: true },
  { family: "DB", page_uids: ["admin:DB-01"], test_only: true },
  { family: "STRATEGY", page_uids: ["workspace:STR-01"], test_only: true },
  { family: "INFO", page_uids: ["workspace:INFO-01"], test_only: true },
  { family: "SYS", page_uids: ["admin:SYS-01"], test_only: true },
  { family: "IAM", page_uids: ["admin:IAM-01"], test_only: true },
  { family: "DEV", page_uids: ["admin:DEV-01"], test_only: true },
  { family: "SOC", page_uids: ["admin:SOC-01"], test_only: true },
  { family: "ERP", page_uids: ["admin:ERP-01"], test_only: true },
  { family: "AIAPI", page_uids: ["admin:AIAPI-01"], test_only: true },
  { family: "SG-02", page_uids: ["admin:SG-02"], test_only: true },
  { family: "KB", page_uids: ["admin:KB-01"], test_only: true },
  { family: "CONVERSATION", page_uids: ["workspace:STR-01"], test_only: true },
  { family: "CANDIDATE", page_uids: ["workspace:INFO-01", "CORE-01"], test_only: true },
  { family: "DEPARTMENT", page_uids: ["QA-01", "admin:ERP-01"], test_only: true },
];

export function controlledRuntimeRegistration(family: ControlledRuntimeFamily): ControlledRuntimeRegistration | undefined {
  return CONTROLLED_RUNTIME_REGISTRY.find((entry) => entry.family === family);
}

export function controlledRuntimeForPage(pageUid: string): ControlledRuntimeRegistration | undefined {
  return CONTROLLED_RUNTIME_REGISTRY.find((entry) => entry.page_uids.includes(pageUid));
}

export function controlledRuntimeMetadata(scope: string): ControlledTestMetadata | null {
  return isControlledTestMode() ? createControlledTestMetadata(scope) : null;
}

export function isControlledRuntimeRegistered(pageUid: string): boolean {
  return controlledRuntimeForPage(pageUid) !== undefined;
}
