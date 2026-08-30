import { NextRequest, NextResponse } from "next/server";
import { CORE_ACTION_PORT, CORE_ACTION_UIDS, type CoreActionUid, type CorePortUid } from "@/domain/core/coreRuntimeContract";
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

async function run(port_uid: CorePortUid, request: NextRequest, context: RouteContext, payload?: unknown) {
  const correlation_id = correlationId(request);
  const rawPathParams = await context.params;
  const path_params = normalizePathParams(port_uid, rawPathParams);
  const query = Object.fromEntries(request.nextUrl.searchParams.entries());
  const action_uid = actionUidForPort(request, port_uid);
  if (request.headers.has("x-core-action-uid") && !action_uid) {
    return NextResponse.json(
      { error_uid: "CORE-01-ERR-UNDEFINED-001", reason_code: "ACTION_PORT_BINDING_MISMATCH", correlation_id },
      { status: 400, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } },
    );
  }
  const result = await executeCorePort({ port_uid, action_uid, correlation_id, path_params, query, payload });
  if (!result.ok) return NextResponse.json({ error_uid: result.error_uid, reason_code: result.reason_code, correlation_id }, { status: result.status, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } });
  return NextResponse.json(result.value, { status: 200, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } });
}

export function createCoreGetRoute(port_uid: CorePortUid) {
  return async (request: NextRequest, context: RouteContext) => run(port_uid, request, context);
}

export function createCorePostRoute(port_uid: CorePortUid) {
  return async (request: NextRequest, context: RouteContext) => {
    const payload = await request.json().catch(() => null);
    return run(port_uid, request, context, payload);
  };
}