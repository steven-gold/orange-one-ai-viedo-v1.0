import { NextRequest, NextResponse } from "next/server";
import { DB_READ_OPERATIONS, type DbReadPortUid } from "@/domain/database/dbRuntimeContract";
import { executeDbRead } from "@/server/database/dbReadModelRuntime";

function isDbReadPortUid(value: unknown): value is DbReadPortUid {
  return typeof value === "string" && value in DB_READ_OPERATIONS;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

export async function POST(request: NextRequest) {
  const current = request.headers.get("x-correlation-id");
  const correlation_id = current && current.trim() ? current : crypto.randomUUID();
  const headers = { "x-correlation-id": correlation_id, "cache-control": "no-store" };
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error_uid: "DB-01-ERR-CONTEXT-001", reason_code: "INVALID_JSON_PAYLOAD", correlation_id }, { status: 400, headers });
  }
  const body = asRecord(payload);
  if (!body || !isDbReadPortUid(body.port_uid)) {
    return NextResponse.json({ error_uid: "DB-01-ERR-CONTEXT-001", reason_code: "DB_READ_PORT_UNSUPPORTED", correlation_id }, { status: 400, headers });
  }
  const result = await executeDbRead(body.port_uid, { correlation_id, scope: body.scope, query: body.query });
  if (!result.ok) {
    const status = result.reason_code.includes("PERMISSION") || result.reason_code.includes("DENIED") || result.reason_code === "AUTHORIZATION_EVALUATION_FAILED" || result.reason_code === "IDENTITY_RUNTIME_NOT_BOUND" ? 403 : 503;
    return NextResponse.json({ error_uid: result.error_uid, reason_code: result.reason_code, correlation_id }, { status, headers });
  }
  return NextResponse.json(result.value, { status: 200, headers });
}
