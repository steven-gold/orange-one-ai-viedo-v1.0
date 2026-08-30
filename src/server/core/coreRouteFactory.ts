import { NextRequest, NextResponse } from "next/server";
import type { CorePortUid } from "@/domain/core/coreRuntimeContract";
import { executeCorePort } from "@/server/core/coreRuntime";

type RouteContext = { params: Promise<Record<string, string>> };

function correlationId(request: NextRequest): string {
  const current = request.headers.get("x-correlation-id");
  return current && current.trim() ? current : crypto.randomUUID();
}

async function run(port_uid: CorePortUid, request: NextRequest, context: RouteContext, payload?: unknown) {
  const correlation_id = correlationId(request);
  const path_params = await context.params;
  const query = Object.fromEntries(request.nextUrl.searchParams.entries());
  const result = await executeCorePort({ port_uid, correlation_id, path_params, query, payload });
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
