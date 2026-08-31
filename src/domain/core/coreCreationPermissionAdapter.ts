export type CoreCreationPermissionKind = "PROJECT" | "TOPIC";

export type CoreCreationPermissionContext = {
  kind: CoreCreationPermissionKind;
};

export type CoreCreationPermissionResult =
  | { allowed: true; required_permission_uid: "CORE_PROJECT_WRITE" | "CORE_TOPIC_WRITE" }
  | { allowed: false; reason_code: string; required_permission_uid: "CORE_PROJECT_WRITE" | "CORE_TOPIC_WRITE" };

export type CoreCreationPermissionAdapter = {
  authorizeCreation: (context: CoreCreationPermissionContext & { required_permission_uid: "CORE_PROJECT_WRITE" | "CORE_TOPIC_WRITE" }) => Promise<CoreCreationPermissionResult> | CoreCreationPermissionResult;
};

let adapter: CoreCreationPermissionAdapter | null = null;

export function configureCoreCreationPermissionAdapter(next: CoreCreationPermissionAdapter): void { adapter = next; }
export function isCoreCreationPermissionAdapterBound(): boolean { return adapter !== null; }

function requiredPermission(kind: CoreCreationPermissionKind): "CORE_PROJECT_WRITE" | "CORE_TOPIC_WRITE" {
  return kind === "PROJECT" ? "CORE_PROJECT_WRITE" : "CORE_TOPIC_WRITE";
}

export async function requestCoreCreationPermission(context: CoreCreationPermissionContext): Promise<CoreCreationPermissionResult> {
  const required_permission_uid = requiredPermission(context.kind);
  const current = adapter;
  if (!current) return { allowed: false, reason_code: "IAM_ACCOUNT_PERMISSION_RUNTIME_NOT_BOUND", required_permission_uid };
  try {
    const result = await current.authorizeCreation({ ...context, required_permission_uid });
    if (!result.allowed) return { ...result, required_permission_uid };
    if (result.required_permission_uid !== required_permission_uid) return { allowed: false, reason_code: "REQUIRED_PERMISSION_MISMATCH", required_permission_uid };
    return result;
  } catch {
    return { allowed: false, reason_code: "AUTHORIZATION_EVALUATION_FAILED", required_permission_uid };
  }
}
