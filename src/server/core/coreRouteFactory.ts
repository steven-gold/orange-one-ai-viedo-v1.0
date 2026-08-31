import { NextRequest, NextResponse } from "next/server";
import { CORE_ACTION_PORT, CORE_ACTION_UIDS, CORE_PORT_METHOD_PATH, type CoreActionUid, type CorePortUid } from "@/domain/core/coreRuntimeContract";
import { executeCorePort } from "@/server/core/coreRuntime";

type RouteContext = { params: Promise<Record<string, string>> };

function correlationId(request: NextRequest): string {
  const current = request.headers.get("x-correlation-id");
  return current && current.trim() ? current : crypto.randomUUID();
}

function actionUidForPort(request: NextRequest, port_uid: CorePortUid): CoreActionUid | undefined {
  const raw = request.headers.get("x-core-action-uid");
  if (!raw || !CORE_ACTION_UIDS.includes(raw as CoreActionUid)) return undefined;
  const action_uid = raw as CoreActionUid;
  return CORE_ACTION_PORT[action_uid] === port_uid ? action_uid : undefined;
}

function normalizePathParams(port_uid: CorePortUid, params: Record<string, string>): Record<string, string> {
  if (port_uid === "CORE-01-PORT-PROJECT-VALIDATE" && params.id && !params.projectVersionId) {
    return { ...params, projectVersionId: params.id };
  }
  return params;
}

function requiredPathKeys(port_uid: CorePortUid): string[] {
  return (CORE_PORT_METHOD_PATH[port_uid].path.match(/\{[^}]+\}/g) ?? []).map((token) => token.slice(1, -1));
}

function missingPathKey(port_uid: CorePortUid, params: Record<string, string>): string | null {
  for (const key of requiredPathKeys(port_uid)) {
    const value = params[key];
    if (!value || !value.trim()) return key;
  }
  return null;
}

function jsonError(correlation_id: string, status: number, error_uid: string, reason_code: string) {
  return NextResponse.json(
    { error_uid, reason_code, correlation_id },
    { status, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } },
  );
}

async function run(port_uid: CorePortUid, request: NextRequest, context: RouteContext, payload?: unknown) {
  const correlation_id = correlationId(request);
  const rawPathParams = await context.params;
  const path_params = normalizePathParams(port_uid, rawPathParams);
  const missing = missingPathKey(port_uid, path_params);
  if (missing) {
    return jsonError(correlation_id, 400, "CORE-01-ERR-CONTEXT-001", `REQUIRED_PATH_REFERENCE_MISSING:${missing}`);
  }
  const query = Object.fromEntries(request.nextUrl.searchParams.entries());
  const action_uid = actionUidForPort(request, port_uid);
  if (request.headers.has("x-core-action-uid") && !action_uid) {
    return jsonError(correlation_id, 400, "CORE-01-ERR-UNDEFINED-001", "ACTION_PORT_BINDING_MISMATCH");
  }
  const result = await executeCorePort({ port_uid, action_uid, correlation_id, path_params, query, payload });
  if (!result.ok) return jsonError(correlation_id, result.status, result.error_uid, result.reason_code);
  return NextResponse.json(result.value, { status: 200, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } });
}

export function createCoreGetRoute(port_uid: CorePortUid) {
  return async (request: NextRequest, context: RouteContext) => run(port_uid, request, context);
}

export function createCorePostRoute(port_uid: CorePortUid) {
  return async (request: NextRequest, context: RouteContext) => {
    let payload: unknown = null;
    const contentType = request.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      try {
        payload = await request.json();
      } catch {
        const correlation_id = correlationId(request);
        return jsonError(correlation_id, 400, "CORE-01-ERR-CONTEXT-001", "INVALID_JSON_PAYLOAD");
      }
    }
    return run(port_uid, request, context, payload);
  };
}
