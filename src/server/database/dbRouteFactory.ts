import { NextRequest, NextResponse } from "next/server";
import { DB_PORT_METHOD_PATH, type DbReadPortUid } from "@/domain/database/dbRuntimeContract";
import { executeDbRead } from "@/server/database/dbReadModelRuntime";

type RouteContext = { params: Promise<Record<string, string>> };

function correlationId(request: NextRequest): string {
  const current = request.headers.get("x-correlation-id");
  return current && current.trim() ? current : crypto.randomUUID();
}

function normalizePathParams(params: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(params).map(([key, value]) => [key, value?.trim() ?? ""]));
}

function missingPathKey(port_uid: DbReadPortUid, params: Record<string, string>): string | null {
  for (const token of DB_PORT_METHOD_PATH[port_uid].path.match(/\{[^}]+\}/g) ?? []) {
    const key = token.slice(1, -1);
    if (!params[key]) return key;
  }
  return null;
}

export function createDbGetRoute(port_uid: DbReadPortUid) {
  return async (request: NextRequest, context: RouteContext) => {
    const correlation_id = correlationId(request);
    const path_params = normalizePathParams(await context.params);
    const missing = missingPathKey(port_uid, path_params);
    if (missing) {
      return NextResponse.json(
        { error_uid: "DB-01-ERR-CONTEXT-001", reason_code: `REQUIRED_PATH_REFERENCE_MISSING:${missing}`, correlation_id },
        { status: 400, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } },
      );
    }
    const query = { ...Object.fromEntries(request.nextUrl.searchParams.entries()), ...path_params };
    const result = await executeDbRead(port_uid, { correlation_id, query });
    if (!result.ok) {
      const status = result.error_uid === "DB-01-ERR-PERM-001" ? 403 : result.reason_code === "DB_READ_MODEL_RUNTIME_NOT_BOUND" ? 503 : 503;
      return NextResponse.json(result, { status, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } });
    }
    return NextResponse.json(result.value, { status: 200, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } });
  };
}
