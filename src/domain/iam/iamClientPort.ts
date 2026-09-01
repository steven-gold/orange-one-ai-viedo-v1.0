import { isIamPageState, type IamPageState } from "@/domain/iam/iamRuntimeContract";

export type IamNormalizedProjection = {
  page_state: IamPageState | null;
  values: Readonly<Record<string, string>>;
  gate_state: Readonly<Record<string, boolean>>;
};

export type IamProjectionResolver = {
  resolve: (raw: unknown) => IamNormalizedProjection | Promise<IamNormalizedProjection>;
};

let resolver: IamProjectionResolver | null = null;

export function configureIamProjectionResolver(next: IamProjectionResolver) {
  resolver = next;
}

export function isIamProjectionResolverBound() {
  return resolver !== null;
}

function projectionErrorUid(status?: number) {
  return status === 401 || status === 403 ? "IAM-01-ERR-AUTH-DENIED" : "IAM-01-ERR-UNDEFINED";
}

function projectionStateIsValid(projection: IamNormalizedProjection) {
  return projection.page_state === null || isIamPageState(projection.page_state);
}

export async function readIamProjection(signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/admin%3AIAM-01", {
      method: "GET",
      cache: "no-store",
      signal,
    });
  } catch {
    return {
      ok: false as const,
      error_uid: "IAM-01-ERR-UNDEFINED",
      reason_code: "IAM_PROJECTION_REQUEST_FAILED",
      correlation_id: "unresolved",
    };
  }

  const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
  const raw: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const body = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : null;
    return {
      ok: false as const,
      error_uid: projectionErrorUid(response.status),
      reason_code:
        typeof body?.reason_code === "string" ? body.reason_code : "IAM_PROJECTION_READ_FAILED",
      correlation_id:
        typeof body?.correlation_id === "string" ? body.correlation_id : correlation_id,
    };
  }

  if (!resolver) {
    return {
      ok: false as const,
      error_uid: "IAM-01-ERR-UNDEFINED",
      reason_code: "IAM_PROJECTION_ADAPTER_NOT_BOUND",
      correlation_id,
    };
  }

  try {
    const projection = await resolver.resolve(raw);
    if (!projectionStateIsValid(projection)) {
      return {
        ok: false as const,
        error_uid: "IAM-01-ERR-UNDEFINED",
        reason_code: "IAM_PROJECTION_ADAPTER_REJECTED",
        correlation_id,
      };
    }
    return { ok: true as const, projection, correlation_id };
  } catch {
    return {
      ok: false as const,
      error_uid: "IAM-01-ERR-UNDEFINED",
      reason_code: "IAM_PROJECTION_ADAPTER_REJECTED",
      correlation_id,
    };
  }
}

export type IamClientCommandInput = {
  action_uid: string;
  control_uid: string;
  client_state: unknown;
  projection: IamNormalizedProjection | null;
};

export type IamClientCommandResult =
  | {
      ok: true;
      projection: IamNormalizedProjection;
      client_state?: unknown;
      correlation_id: string;
    }
  | { ok: false; error_uid: string; reason_code: string; correlation_id: string };

export type IamClientCommandAdapter = {
  invoke: (input: IamClientCommandInput) => Promise<IamClientCommandResult>;
};

let commandAdapter: IamClientCommandAdapter | null = null;

export function configureIamClientCommandAdapter(next: IamClientCommandAdapter) {
  commandAdapter = next;
}

export function isIamClientCommandAdapterBound() {
  return commandAdapter !== null;
}

export async function invokeIamClientCommand(
  input: IamClientCommandInput,
): Promise<IamClientCommandResult> {
  if (!commandAdapter) {
    return {
      ok: false,
      error_uid: "IAM-01-ERR-UNDEFINED",
      reason_code: "IAM_CLIENT_COMMAND_RUNTIME_NOT_BOUND",
      correlation_id: "unresolved",
    };
  }
  try {
    const result = await commandAdapter.invoke(input);
    if (result.ok && !projectionStateIsValid(result.projection)) {
      return {
        ok: false,
        error_uid: "IAM-01-ERR-UNDEFINED",
        reason_code: "IAM_CLIENT_COMMAND_ADAPTER_REJECTED",
        correlation_id: result.correlation_id,
      };
    }
    return result;
  } catch {
    return {
      ok: false,
      error_uid: "IAM-01-ERR-UNDEFINED",
      reason_code: "IAM_CLIENT_COMMAND_RUNTIME_FAILED",
      correlation_id: "unresolved",
    };
  }
}
